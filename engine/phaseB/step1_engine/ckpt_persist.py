# -*- coding: utf-8 -*-
"""Generation-based persistence for long-run checkpoints (B-3-2 B; audits R322-A/B/C, R323-A/B/C). NumPy-free (importable before the environment install).
Snapshot contract (R323-A): a checkpoint envelope is accepted only when file name <-> identity.n_sub agree, `done` is a non-bool int within [0, B_max], done == len(values) ==
len(blocks) == len(pairwise) (== len(bounds) when present), the identity carries the required keys and the payload digest matches; several envelopes must share the same identity
except n_sub/kc; the sequential stage plan (n_sub 2000 then 5000) must be respected: a later stage may exist only if every earlier stage is COMPLETE (missing earlier stage -> not
resumable, never silently recomputed). Publishing copies the files to a fresh generation, RE-VERIFIES the copied envelopes and derives the generation manifest (files, SHAs, done,
lock) from the COPIED bytes only; if the source changed during the copy the generation is discarded and the previous one kept. Publishers use per-publisher temporary names and a
directory lock (mkdir-based) so that two publishers never interleave on LATEST; the pointer is switched only to a fully written generation. Restore reads the pointer, re-verifies
the generation (manifest <-> envelopes), checks the lock BEFORE touching the empty staging directory and re-verifies every restored file."""
from __future__ import annotations
import hashlib, json, os, shutil, time, uuid
from typing import Dict, List, Optional
from .errors import InputContractError

# ---- NumPy-free strict JSON with the SAME rules as step1_engine.serialization (this module must be importable before the environment install)
import math as _math
_NF = {"nan": float("nan"), "inf": float("inf"), "-inf": float("-inf")}


def _to_jsonable(o):
    if isinstance(o, dict):
        kinds = {("int" if (isinstance(k, int) and not isinstance(k, bool)) else "str" if isinstance(k, str) else "other") for k in o}
        if "other" in kinds or len(kinds) > 1: raise InputContractError("dict keys must be all-int or all-str for strict serialisation")
        if kinds == {"int"}: return {"__intkeys__": [[int(k), _to_jsonable(v)] for k, v in o.items()]}
        return {str(k): _to_jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [_to_jsonable(v) for v in o]
    if isinstance(o, bool): return bool(o)
    if isinstance(o, int): return int(o)
    if isinstance(o, float):
        if _math.isnan(o): return {"__float__": "nan"}
        if _math.isinf(o): return {"__float__": "inf" if o > 0 else "-inf"}
        return o
    if hasattr(o, "tolist"): return _to_jsonable(o.tolist())
    return o


def _from_jsonable(o):
    if isinstance(o, dict):
        if set(o) == {"__float__"}: return _NF[o["__float__"]]
        if set(o) == {"__intkeys__"}:
            ks = [int(k) for k, _ in o["__intkeys__"]]
            if len(set(ks)) != len(ks): raise InputContractError("duplicate tagged integer key")
            return {int(k): _from_jsonable(v) for k, v in o["__intkeys__"]}
        return {k: _from_jsonable(v) for k, v in o.items()}
    if isinstance(o, list): return [_from_jsonable(v) for v in o]
    return o


def _reject_constant(c): raise InputContractError(f"bare {c} is not allowed in strict JSON")
def _pairs_hook(pairs):
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys): raise InputContractError("duplicate object key in strict JSON")
    return dict(pairs)


class _Ser:
    @staticmethod
    def dumps(o) -> str: return json.dumps(_to_jsonable(o), allow_nan=False, ensure_ascii=False)
    @staticmethod
    def loads(s: str): return _from_jsonable(json.loads(s, parse_constant=_reject_constant, object_pairs_hook=_pairs_hook))
ser = _Ser()

EXPECTED_CKPT = ("null_nsub2000.json", "null_nsub5000.json"); STAGE_ORDER = (2000, 5000); CKPT_SCHEMA = "shared_null_checkpoint_v2"; KEEP = 3
IDENTITY_KEYS = ("schema", "engine_version", "iso", "iso_f32", "m", "master_seed", "n_sub", "distance_kind", "kc", "B_max", "whitening", "provenance")


def _sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _payload_digest(values, blocks, pairwise, bounds) -> str: return hashlib.sha256(ser.dumps(dict(values=values, blocks=blocks, pairwise=pairwise, bounds=bounds)).encode()).hexdigest()


def _is_int(v): return isinstance(v, int) and not isinstance(v, bool)


def verify_checkpoint_file(path: str, expected_identity: Optional[dict] = None) -> dict:
    """Structural / state verification of one envelope (name<->n_sub, done<->payload counts, identity keys, digest). Returns dict(done, n_sub, complete, identity, B_max)."""
    name = os.path.basename(path)
    try: d = ser.loads(open(path).read())
    except Exception as ex: raise InputContractError(f"checkpoint {name} unreadable: {ex!r}")
    if not isinstance(d, dict) or d.get("schema") != CKPT_SCHEMA: raise InputContractError(f"{name}: not a {CKPT_SCHEMA} envelope")
    idn = d.get("identity")
    if not isinstance(idn, dict) or any(k not in idn for k in IDENTITY_KEYS): raise InputContractError(f"{name}: identity lacks required keys")
    n_sub, B_max, kc = idn.get("n_sub"), idn.get("B_max"), idn.get("kc")
    if not (_is_int(n_sub) and _is_int(B_max) and _is_int(kc) and B_max > 0): raise InputContractError(f"{name}: identity n_sub/B_max/kc must be integers")
    if name != f"null_nsub{n_sub}.json": raise InputContractError(f"{name}: file name does not match identity.n_sub={n_sub}")
    done = d.get("done")
    if not (_is_int(done) and 0 <= done <= B_max): raise InputContractError(f"{name}: done must be an integer in [0, B_max]")
    vals, blocks, pw, bounds = d.get("values"), d.get("blocks"), d.get("pairwise"), d.get("bounds")
    if not (isinstance(vals, list) and isinstance(blocks, list) and isinstance(pw, list) and len(vals) == len(blocks) == len(pw) == done): raise InputContractError(f"{name}: done={done} does not match payload counts")
    if bounds is not None and not (isinstance(bounds, list) and len(bounds) == done): raise InputContractError(f"{name}: bounds count does not match done")
    if d.get("payload_digest") != _payload_digest(vals, blocks, pw, bounds): raise InputContractError(f"{name}: payload digest mismatch")
    if expected_identity is not None and idn != expected_identity: raise InputContractError(f"{name}: identity differs")
    return dict(done=done, n_sub=n_sub, complete=(done == B_max), identity=idn, B_max=B_max, sha256=_sha(path), bytes=os.path.getsize(path))


def _common_identity_ok(infos: Dict[str, dict]) -> bool:
    ids = [{k: v for k, v in i["identity"].items() if k not in ("n_sub", "kc")} for i in infos.values()]
    return all(x == ids[0] for x in ids)


def stage_state(infos: Dict[str, dict]) -> dict:
    """Sequential stage plan: stage i may be present only if all earlier stages are complete. Returns dict(valid, reason, stages)."""
    present = {int(i["n_sub"]): i for i in infos.values()}; stages = {}
    for j, n in enumerate(STAGE_ORDER):
        stages[str(n)] = ("absent" if n not in present else ("complete" if present[n]["complete"] else f"partial:{present[n]['done']}"))   # str keys (JSON-stable)
    for j, n in enumerate(STAGE_ORDER):
        if n in present:
            missing = [k for k in STAGE_ORDER[:j] if k not in present or not present[k]["complete"]]
            if missing: return dict(valid=False, reason=f"stage n_sub={n} present but earlier stage(s) {missing} not complete (missing or partial)", stages=stages)
    if len(infos) > 1 and not _common_identity_ok(infos): return dict(valid=False, reason="checkpoints do not share a common identity", stages=stages)
    return dict(valid=True, reason=None, stages=stages)


def inspect_local(ckpt_dir: str) -> dict:
    """Verified expected checkpoints + sequential stage validity. Unrelated files are listed and never a resume basis."""
    present, others = {}, []
    for f in sorted(os.listdir(ckpt_dir)) if os.path.isdir(ckpt_dir) else []:
        if f in EXPECTED_CKPT: present[f] = verify_checkpoint_file(os.path.join(ckpt_dir, f))
        elif not f.endswith(".part") and not f.endswith(".tmp"): others.append(f)
    st = stage_state(present) if present else dict(valid=False, reason="no expected checkpoint", stages={n: "absent" for n in STAGE_ORDER})
    return dict(present=present, unrelated=others, resumable=bool(present and st["valid"]), stage_state=st)


class _DirLock:
    def __init__(self, root: str, timeout: float = 600.0): self.p = os.path.join(root, ".publish.lock"); self.timeout = timeout
    def __enter__(self):
        t0 = time.time()
        while True:
            try: os.mkdir(self.p); open(os.path.join(self.p, "owner"), "w").write(f"{os.getpid()} {uuid.uuid4().hex}"); return self
            except FileExistsError:
                if time.time() - t0 > self.timeout: raise InputContractError("publish lock held too long (another publisher may be stuck)")
                time.sleep(0.05)
    def __exit__(self, *a): shutil.rmtree(self.p, ignore_errors=True)


def publish_generation(ckpt_dir: str, persist_run_root: str, lock: dict, note=print) -> Optional[str]:
    """Publish a consistent snapshot of the local checkpoints as a new immutable generation. Progress/identity are derived from the COPIED files; a source that changed during the
    copy discards this generation (previous kept). Serialized by a directory lock; pointer file names are per publisher."""
    os.makedirs(persist_run_root, exist_ok=True); tag = uuid.uuid4().hex[:8]
    with _DirLock(persist_run_root):
        pre = inspect_local(ckpt_dir)
        if not pre["present"]: return None
        if not pre["resumable"]:
            raise InputContractError(f"snapshot is not resumable; previous generation retained: {pre['stage_state']['reason']}")
        gen = os.path.join(persist_run_root, f"gen_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}_{time.time_ns():020d}_{tag}")   # monotone name (retention prunes the oldest)
        if os.path.exists(gen): raise InputContractError("generation directory already exists")
        os.makedirs(gen)
        try:
            copied = {}
            for f in sorted(pre["present"]):
                src = os.path.join(ckpt_dir, f); s0 = _sha(src); tmp = os.path.join(gen, f + ".part"); shutil.copyfile(src, tmp)
                if _sha(tmp) != s0: raise InputContractError(f"copy verification failed for {f}")
                os.replace(tmp, os.path.join(gen, f)); copied[f] = verify_checkpoint_file(os.path.join(gen, f))
                if _sha(src) != s0: raise InputContractError(f"source {f} changed during the copy (generation discarded; retry later)")
            st = stage_state(copied)
            if not st["valid"]:
                raise InputContractError(f"copied snapshot is not resumable; previous generation retained: {st['reason']}")
            manifest = dict(schema="ckpt_generation_v1", files={f: dict(sha256=i["sha256"], bytes=i["bytes"]) for f, i in copied.items()}, done={f: i["done"] for f, i in copied.items()}, complete={f: i["complete"] for f, i in copied.items()}, stage_state=st["stages"], resumable=bool(st["valid"]), stage_reason=st["reason"], lock=lock, unrelated_ignored=pre["unrelated"], published_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), publisher=tag)
            mtmp = os.path.join(gen, f"generation_manifest.json.{tag}.part"); open(mtmp, "w").write(json.dumps(manifest, indent=1)); os.replace(mtmp, os.path.join(gen, "generation_manifest.json"))
            verify_generation(gen)                                                                   # re-verify the finished generation before publishing the pointer
            ptmp = os.path.join(persist_run_root, f"LATEST.{tag}.part"); open(ptmp, "w").write(os.path.basename(gen)); os.replace(ptmp, os.path.join(persist_run_root, "LATEST"))
        except Exception as ex:
            shutil.rmtree(gen, ignore_errors=True); note(f"publish failed (previous generation kept): {ex!r}"); raise
        gens = sorted(g for g in os.listdir(persist_run_root) if g.startswith("gen_") and os.path.exists(os.path.join(persist_run_root, g, "generation_manifest.json")))
        for g in gens[:-KEEP]:
            if g != os.path.basename(gen): shutil.rmtree(os.path.join(persist_run_root, g), ignore_errors=True)
    return gen


def latest_generation(persist_run_root: str) -> Optional[str]:
    p = os.path.join(persist_run_root, "LATEST")
    if not os.path.exists(p): return None
    g = os.path.join(persist_run_root, open(p).read().strip()); return g if os.path.exists(os.path.join(g, "generation_manifest.json")) else None


def verify_generation(gen: str) -> dict:
    """Manifest <-> envelopes: file set, SHA/bytes, done/complete per file re-derived from the envelopes, stage validity."""
    man = json.load(open(os.path.join(gen, "generation_manifest.json")))
    if man.get("schema") != "ckpt_generation_v1" or not man.get("files"): raise InputContractError("generation manifest invalid")
    infos = {}
    for f, e in man["files"].items():
        p = os.path.join(gen, f)
        if f not in EXPECTED_CKPT or not os.path.exists(p) or _sha(p) != e["sha256"] or os.path.getsize(p) != e["bytes"]: raise InputContractError(f"generation file {f} missing or differs from its manifest")
        infos[f] = verify_checkpoint_file(p)
    if set(os.path.basename(x) for x in os.listdir(gen) if x in EXPECTED_CKPT) != set(man["files"]): raise InputContractError("generation directory file set differs from its manifest")
    if man.get("done") != {f: i["done"] for f, i in infos.items()}: raise InputContractError("generation manifest done counts differ from the copied envelopes")
    expected_complete = {f: i["complete"] for f, i in infos.items()}
    completed = man.get("complete")
    if not isinstance(completed, dict) or completed != expected_complete or any(type(v) is not bool for v in completed.values()):
        raise InputContractError("generation manifest complete flags differ from the copied envelopes")
    st = stage_state(infos)
    if not st["valid"]:
        raise InputContractError(f"generation is not resumable: {st['reason']}")
    if man.get("resumable") is not True or man.get("stage_state") != st["stages"] or man.get("stage_reason") != st["reason"]:
        raise InputContractError("generation manifest stage state differs from the envelopes")
    return man


def restore_generation(persist_run_root: str, staging_ckpt_dir: str, expected_lock: dict, gen: Optional[str] = None) -> dict:
    gen = gen or latest_generation(persist_run_root)
    if gen is None: raise InputContractError("no complete generation to restore")
    man = verify_generation(gen)
    for k in ("commit", "inventory_sha256", "launcher_id", "pins_sha256"):
        if man["lock"].get(k) != expected_lock.get(k): raise InputContractError(f"generation lock '{k}' differs from the current launcher (refusing before touching the staging directory)")
    if os.path.exists(staging_ckpt_dir) and os.listdir(staging_ckpt_dir): raise InputContractError("staging checkpoint directory must be empty (no merge into an existing run)")
    os.makedirs(staging_ckpt_dir, exist_ok=True)
    for f, e in man["files"].items():
        tmp = os.path.join(staging_ckpt_dir, f + ".part"); shutil.copyfile(os.path.join(gen, f), tmp)
        if _sha(tmp) != e["sha256"]: raise InputContractError(f"restore verification failed for {f}")
        os.replace(tmp, os.path.join(staging_ckpt_dir, f))
    info = inspect_local(staging_ckpt_dir)
    return dict(generation=os.path.basename(gen), done=man["done"], present=list(info["present"]), partial_state={f: v["done"] for f, v in info["present"].items()}, stage_state=info["stage_state"]["stages"], resumable=bool(info["resumable"]), stage_reason=info["stage_state"]["reason"])
