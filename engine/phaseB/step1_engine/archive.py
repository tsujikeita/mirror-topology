# -*- coding: utf-8 -*-
"""Content-addressed archive for engine records (rules §13): kind/<sha256>.json + index entries (kind, identity, canonical relative path, byte length, engine version).
Contracts: a record is resolved only through a validated ArchiveRef whose (kind, sha, path, identity) equals its index entry, whose path is the canonical location under the root,
and whose bytes hash to the SHA; index metadata (byte length, path, identity) is checked on every get and in verify_all (duplicates rejected); putting the same bytes under a
conflicting identity is rejected (same identity is idempotent). resolve_transition_archive validates the transition, the reference, the identity chain and the technical-status
correspondence between the archived source and the transition.
Index access (D4C-1; engine 0.106.0): the parsed index is cached in memory and re-read whenever the index file's stat identity (inode, size, mtime_ns, ctime_ns) changes, so a
get/put no longer re-parses the whole index; lookups use a (kind, sha) map. `deferred_index=True` keeps the index in memory and writes it on flush() / context exit / every
`flush_every` puts (record files are still written immediately); the on-disk index bytes are identical to the immediate mode for the same put sequence (tested). A record file
present on disk without an index entry (interrupted deferred run) is simply re-indexed by the next identical put. import_bytes() copies an entry byte-exactly (archive merge).
0.107.0 (audit R-D4C1-A1/A2): the trusted cache owns deep copies of every entry (returned refs and _entries() never alias it; an edited ref is rejected by get and never reaches
the index), and a pending flush / context exit re-checks the index file's stat identity first (external change while pending -> conflict, nothing overwritten)."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib, os, copy
from .errors import InputContractError
from . import serialization as ser
from . import __version__

KINDS = ("family_result", "twelve_manifest", "w2_manifest", "plan_set", "transition", "registry", "three_position_result")


def _is_sha(v) -> bool: return isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)


@dataclass(frozen=True)
class ArchiveRef:
    kind: str; sha256: str; path: str; identity: dict
    def as_dict(self): return asdict(self)
    def validate(self):
        if self.kind not in KINDS: raise InputContractError(f"unknown archive kind {self.kind!r}")
        if not _is_sha(self.sha256): raise InputContractError("ArchiveRef SHA must be 64 lowercase hex characters")
        if not isinstance(self.identity, dict) or any(not isinstance(k, str) for k in self.identity): raise InputContractError("ArchiveRef identity must be a str-keyed dict")
        if self.path != f"{self.kind}/{self.sha256}.json": raise InputContractError("ArchiveRef path must be the canonical location kind/<sha>.json")
        return True


def _entry_valid(e: dict):
    for k in ("kind", "sha256", "path", "identity", "bytes", "engine_version"):
        if k not in e: raise InputContractError(f"index entry lacks {k}")
    ArchiveRef(e["kind"], e["sha256"], e["path"], e["identity"]).validate()
    if isinstance(e["bytes"], bool) or not isinstance(e["bytes"], int) or e["bytes"] <= 0: raise InputContractError("index entry byte length invalid")
    return True


class Archive:
    def __init__(self, root: str, deferred_index: bool = False, flush_every: int = 0):
        self.root = os.path.realpath(root); os.makedirs(self.root, exist_ok=True); self.index_path = os.path.join(self.root, "index.json")
        self._cache = None; self._deferred = bool(deferred_index); self._pending = 0
        if isinstance(flush_every, bool) or not isinstance(flush_every, int) or flush_every < 0: raise InputContractError("flush_every must be a non-negative integer")
        self._flush_every = int(flush_every)
        if not os.path.exists(self.index_path): self._write_index([])

    def __enter__(self): return self
    def __exit__(self, *exc):
        if exc[0] is None: self.flush()
        return False

    @property
    def pending(self) -> int: return self._pending

    def _stat_key(self):
        st = os.stat(self._resolved_path("index.json")); return (st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)

    def flush(self):
        """Deferred mode: write the in-memory index to disk (identical bytes to the immediate mode); no-op when nothing is pending. R-D4C1-A2: before the write the index file on
        disk must still be the one the cache was built from (stat identity); an external change while entries are pending is a conflict and nothing is overwritten (the same
        rule as get). Not a race-proof lock: ordinary, non-hostile sequential use."""
        if self._pending:
            self._load()                                                                                      # raises on an external change of the index while pending
            self._write_index(self._cache[1])
        return self

    def _resolved_path(self, relative_path):
        """Enforce archive confinement after resolving ordinary symbolic links.
        This is not a defence against a hostile concurrent filesystem modifier.
        """
        path = os.path.realpath(os.path.join(self.root, relative_path))
        if os.path.commonpath([self.root, path]) != self.root:
            raise InputContractError("archive path resolves outside the archive root")
        return path

    def _verified_body(self, ref, entry):
        path = self._resolved_path(ref.path)
        if not os.path.isfile(path):
            raise InputContractError("archive reference does not resolve to a regular file")
        with open(path, "rb") as fh:
            body = fh.read()
        if hashlib.sha256(body).hexdigest() != ref.sha256:
            raise InputContractError("archived bytes do not match the reference SHA")
        if len(body) != entry["bytes"]:
            raise InputContractError("archived byte length differs from the index entry")
        return body

    def _write_index(self, entries):
        self._resolved_path("index.json")
        tmp = self._resolved_path("index.json.tmp")
        with open(tmp, "w", encoding="utf-8") as fh: fh.write(ser.dumps(dict(kind="ArchiveIndex", engine_version=__version__, entries=entries))); fh.flush(); os.fsync(fh.fileno())
        os.replace(tmp, self.index_path)
        self._cache = (self._stat_key(), entries, {(e["kind"], e["sha256"]): e for e in entries}); self._pending = 0

    def _parse_index(self):
        idx = ser.loads(open(self._resolved_path("index.json"), encoding="utf-8").read())
        if idx.get("kind") != "ArchiveIndex" or not isinstance(idx.get("entries"), list): raise InputContractError("archive index malformed")
        keys = {}
        for e in idx["entries"]:
            _entry_valid(e); k = (e["kind"], e["sha256"])
            if k in keys: raise InputContractError("archive index contains duplicate entries")
            keys[k] = e
        return idx["entries"], keys

    def _load(self):
        """Validated index entries + (kind, sha) map; parsed from disk whenever the file's stat identity differs from the cached one. Pending deferred entries are never
        discarded: an external change of the index file while entries are pending is a conflict."""
        key = self._stat_key()
        if self._cache is not None and self._cache[0] == key: return self._cache
        if self._pending: raise InputContractError("archive index changed on disk while deferred entries are pending")
        entries, keys = self._parse_index(); self._cache = (key, entries, keys); return self._cache

    def _entries(self): return copy.deepcopy(self._load()[1])                                                # callers never receive the trusted cache objects (R-D4C1-A1)

    def _find(self, kind, sha): return self._load()[2].get((kind, sha))

    def _append_entry(self, entry: dict):
        entry = copy.deepcopy(entry)                                                                            # the trusted cache owns its own deep copy (R-D4C1-A1)
        key, entries, keys = self._load(); entries.append(entry); keys[(entry["kind"], entry["sha256"])] = entry
        if self._deferred:
            self._pending += 1
            if self._flush_every and self._pending >= self._flush_every: self._write_index(entries)
        else: self._write_index(entries)

    def put(self, kind: str, record: dict, identity: dict) -> ArchiveRef:
        if kind not in KINDS: raise InputContractError(f"unknown archive kind {kind!r}")
        body = ser.dumps(record).encode("utf-8"); sha = hashlib.sha256(body).hexdigest(); ident = ser.from_jsonable(ser.to_jsonable(identity)); rel = f"{kind}/{sha}.json"; ref = ArchiveRef(kind, sha, rel, copy.deepcopy(ident)); ref.validate()
        existing = self._find(kind, sha)
        if existing is not None:
            if existing["identity"] != ident: raise InputContractError("archive conflict: the same bytes are already indexed under a different identity (aliases are not supported)")
            if existing["bytes"] != len(body) or existing["path"] != rel: raise InputContractError("archive index entry inconsistent with the record")
            self._verified_body(ref, existing)  # idempotence does not bypass file integrity
            return ref
        path = self._resolved_path(rel); os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path) and not os.path.isfile(path):
            raise InputContractError("archive destination is not a regular file")
        if os.path.exists(path) and open(path, "rb").read() != body: raise InputContractError("archive collision: existing file differs from the record bytes")
        if not os.path.exists(path):
            tmp = self._resolved_path(rel + ".tmp")
            with open(tmp, "wb") as fh: fh.write(body); fh.flush(); os.fsync(fh.fileno())
            os.replace(tmp, path)
        self._append_entry(dict(kind=kind, sha256=sha, path=rel, identity=ident, bytes=len(body), engine_version=__version__)); return ref

    def import_bytes(self, kind: str, sha256: str, identity: dict, body: bytes, engine_version: str) -> ArchiveRef:
        """Byte-exact import of an entry from another archive (merge): the bytes must hash to the given SHA, decode as strict JSON and reproduce the canonical serialisation;
        the entry keeps the SOURCE engine version; the same (kind, sha) under a different identity is a conflict, the same identity is idempotent."""
        if kind not in KINDS: raise InputContractError(f"unknown archive kind {kind!r}")
        if not isinstance(body, (bytes, bytearray)) or hashlib.sha256(body).hexdigest() != sha256: raise InputContractError("imported bytes do not hash to the given SHA")
        if ser.dumps(ser.loads(body.decode("utf-8"))).encode("utf-8") != bytes(body): raise InputContractError("imported bytes are not a canonical archive record")
        if not isinstance(engine_version, str) or not engine_version: raise InputContractError("imported entry requires its source engine version")
        ident = ser.from_jsonable(ser.to_jsonable(identity)); rel = f"{kind}/{sha256}.json"; ref = ArchiveRef(kind, sha256, rel, copy.deepcopy(ident)); ref.validate()
        existing = self._find(kind, sha256)
        if existing is not None:
            if existing["identity"] != ident: raise InputContractError("archive conflict: the same bytes are already indexed under a different identity (aliases are not supported)")
            if existing["bytes"] != len(body) or existing["path"] != rel or existing["engine_version"] != engine_version: raise InputContractError("archive index entry inconsistent with the imported record")
            self._verified_body(ref, existing); return ref
        path = self._resolved_path(rel); os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path) and not os.path.isfile(path): raise InputContractError("archive destination is not a regular file")
        if os.path.exists(path) and open(path, "rb").read() != bytes(body): raise InputContractError("archive collision: existing file differs from the record bytes")
        if not os.path.exists(path):
            tmp = self._resolved_path(rel + ".tmp")
            with open(tmp, "wb") as fh: fh.write(bytes(body)); fh.flush(); os.fsync(fh.fileno())
            os.replace(tmp, path)
        self._append_entry(dict(kind=kind, sha256=sha256, path=rel, identity=ident, bytes=len(body), engine_version=engine_version)); return ref

    def entry_bytes(self, entry: dict) -> bytes:
        """Verified bytes of an index entry (merge source side)."""
        _entry_valid(entry); return self._verified_body(ArchiveRef(entry["kind"], entry["sha256"], entry["path"], entry["identity"]), entry)

    def get(self, ref: ArchiveRef) -> dict:
        if not isinstance(ref, ArchiveRef): raise InputContractError("an ArchiveRef is required")
        ref.validate(); e = self._find(ref.kind, ref.sha256)
        if e is None: raise InputContractError("reference is not listed in the archive index")
        if e["path"] != ref.path or ser.from_jsonable(ser.to_jsonable(e["identity"])) != ser.from_jsonable(ser.to_jsonable(ref.identity)): raise InputContractError("reference path/identity differ from the archive index")
        body = self._verified_body(ref, e)
        return ser.loads(body.decode("utf-8"))

    def verify_all(self) -> dict:
        entries = self._entries()
        for e in entries:
            ref = ArchiveRef(e["kind"], e["sha256"], e["path"], e["identity"])
            self._verified_body(ref, e)
        return dict(entries=len(entries), ok=True)


def merge_archives(dst: Archive, src: Archive) -> dict:
    """Copy every entry of src into dst byte-exactly (verified on both sides; identity conflicts rejected; identical entries idempotent). Returns counts."""
    if not isinstance(dst, Archive) or not isinstance(src, Archive): raise InputContractError("Archive instances required")
    if os.path.realpath(dst.root) == os.path.realpath(src.root): raise InputContractError("merge source and destination are the same archive")
    added = skipped = 0
    for e in src._entries():
        body = src.entry_bytes(e); before = dst._find(e["kind"], e["sha256"]) is not None
        dst.import_bytes(e["kind"], e["sha256"], e["identity"], body, e["engine_version"]); added += 0 if before else 1; skipped += 1 if before else 0
    dst.flush(); return dict(added=added, already_present=skipped, source_entries=added + skipped)


def archive_three_position_result(archive: Archive, result: dict, family: str, size_id: str) -> ArchiveRef:
    if result.get("family") != family or result.get("size_id") != size_id: raise InputContractError("result identity mismatch")
    if (result.get("decision") or {}).get("technical_status") not in ("ok", "technical_fail"): raise InputContractError("result.decision.technical_status must be registered")
    return archive.put("three_position_result", result, dict(family=family, size_id=size_id))


def resolve_transition_archive(archive: Archive, transition, ref: ArchiveRef) -> dict:
    """The archived 3-position source of a StageTransition: transition.validate(), validated reference, identity chain (ref == record == transition) and technical-status correspondence."""
    from .stage12 import StageTransition
    if not isinstance(transition, StageTransition): raise InputContractError("a StageTransition is required")
    transition.validate(); ref.validate()
    if ref.kind != "three_position_result" or ref.sha256 != transition.three_position_result_sha256: raise InputContractError("archive reference does not match the transition's archived result SHA")
    if ref.identity != dict(family=transition.family, size_id=transition.size_id): raise InputContractError("archive reference identity differs from the transition")
    rec = archive.get(ref)
    if rec.get("family") != transition.family or rec.get("size_id") != transition.size_id: raise InputContractError("archived result identity differs from the transition")
    src_tech = (rec.get("decision") or {}).get("technical_status")
    if src_tech != transition.three_technical_status: raise InputContractError(f"archived source technical status {src_tech!r} contradicts the transition's {transition.three_technical_status!r}")
    return rec
