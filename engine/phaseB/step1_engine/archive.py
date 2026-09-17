# -*- coding: utf-8 -*-
"""Content-addressed archive for engine records (rules §13): kind/<sha256>.json + index entries (kind, identity, canonical relative path, byte length, engine version).
Contracts: a record is resolved only through a validated ArchiveRef whose (kind, sha, path, identity) equals its index entry, whose path is the canonical location under the root,
and whose bytes hash to the SHA; index metadata (byte length, path, identity) is checked on every get and in verify_all (duplicates rejected); putting the same bytes under a
conflicting identity is rejected (same identity is idempotent). resolve_transition_archive validates the transition, the reference, the identity chain and the technical-status
correspondence between the archived source and the transition."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib, os
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
    def __init__(self, root: str):
        self.root = os.path.realpath(root); os.makedirs(self.root, exist_ok=True); self.index_path = os.path.join(self.root, "index.json")
        if not os.path.exists(self.index_path): self._write_index([])

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

    def _entries(self):
        idx = ser.loads(open(self._resolved_path("index.json"), encoding="utf-8").read())
        if idx.get("kind") != "ArchiveIndex" or not isinstance(idx.get("entries"), list): raise InputContractError("archive index malformed")
        keys = set()
        for e in idx["entries"]:
            _entry_valid(e); k = (e["kind"], e["sha256"])
            if k in keys: raise InputContractError("archive index contains duplicate entries")
            keys.add(k)
        return idx["entries"]

    def _find(self, kind, sha):
        for e in self._entries():
            if e["kind"] == kind and e["sha256"] == sha: return e
        return None

    def put(self, kind: str, record: dict, identity: dict) -> ArchiveRef:
        if kind not in KINDS: raise InputContractError(f"unknown archive kind {kind!r}")
        body = ser.dumps(record).encode("utf-8"); sha = hashlib.sha256(body).hexdigest(); ident = ser.from_jsonable(ser.to_jsonable(identity)); rel = f"{kind}/{sha}.json"; ref = ArchiveRef(kind, sha, rel, ident); ref.validate()
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
        entries = self._entries(); entries.append(dict(kind=kind, sha256=sha, path=rel, identity=ident, bytes=len(body), engine_version=__version__)); self._write_index(entries); return ref

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
