# -*- coding: utf-8 -*-
"""Resumable builder for the registered-scale SharedNullAsset (B-3-2; audit R321-B). Same extraction rule as positions.null_max_sequence (SeedSequence [master_seed, 5, n_sub, 999];
three disjoint sorted blocks of kc clusters per replicate; re-permute on exhaustion), computed replicate by replicate with versioned, digest-bound checkpoints.
Contracts: (1) the input banks (f64 pool, paired f32 pool) are snapshotted BEFORE the first distance call and re-hashed at every checkpoint and at the end (a bank mutated mid-run is a
technical failure); (2) the checkpoint identity binds pool identities, m, master seed, n_sub, kc, B_max, distance kind AND the whitening identity, the engine version and (when given) the
provenance dict (source/pins/environment); a checkpoint with any other identity is refused, never re-bound; (3) every checkpoint carries a payload digest (values, blocks, pairwise,
bounds) and is re-verified on load: digest, schema, counts, finiteness, non-negativity, pair/max consistency, disjoint blocks in range, and the paired coupling bounds are
RECOMPUTED from the paired pools (cheap) and must equal the stored ones; edited payloads are refused (no re-stamping of edited values); (4) atomic writes; (5) the final asset is
assembled with the SharedNullAsset schema and validated. Resume never falls back to a fresh run silently: a checkpoint that exists must be valid; a missing one starts from 0."""
from __future__ import annotations
import hashlib, json, os, time
from typing import Callable, Optional
import numpy as np
from .errors import InputContractError
from .rules_config import RULES
from .positions import PositionBank, bank_identity, _take, _pairs, _kc, DISTANCE_KINDS, w2_exact, _norm_identity
from .w2_shared import SharedNullAsset
from . import serialization as ser
from . import __version__

CKPT_SCHEMA = "shared_null_checkpoint_v2"; PAIRS = ("P1P2", "P1P3", "P2P3")


def _payload_digest(values, blocks, pairwise, bounds) -> str:
    return hashlib.sha256(ser.dumps(dict(values=values, blocks=blocks, pairwise=pairwise, bounds=bounds)).encode()).hexdigest()


def _bound(iso: PositionBank, iso_f32: PositionBank, blocks) -> float:
    eps = [float(np.sqrt(np.mean(np.sum((iso.Tw[np.isin(iso.cid, bl)] - iso_f32.Tw[np.isin(iso_f32.cid, bl)]) ** 2, axis=1)))) for bl in blocks]
    return max(eps[i] + eps[j] for i in range(3) for j in range(i + 1, 3))


def _identity(iso, iso_f32, m, master_seed, n_sub, dkind, whitening_identity, provenance):
    return _norm_identity(dict(schema=CKPT_SCHEMA, engine_version=__version__, iso=bank_identity(iso), iso_f32=(None if iso_f32 is None else bank_identity(iso_f32)), m=int(m), master_seed=int(master_seed), n_sub=int(n_sub), distance_kind=dkind, kc=_kc(n_sub, m), B_max=RULES.B_levels[-1], whitening=whitening_identity, provenance=provenance))


def _blocks_stream(iso: PositionBank, n_sub: int, m: int, master_seed: int, B_max: int):
    kc = _kc(n_sub, m); rng = np.random.default_rng(np.random.SeedSequence([master_seed, 5, int(n_sub), 999])); perm = rng.permutation(iso.K); ptr = 0
    for b in range(B_max):
        if ptr + 3 * kc > iso.K: perm = rng.permutation(iso.K); ptr = 0
        blocks = [np.sort(perm[ptr + j * kc: ptr + (j + 1) * kc]) for j in range(3)]; ptr += 3 * kc
        if len(set(np.concatenate(blocks).tolist())) != 3 * kc: raise InputContractError("null blocks must be disjoint")
        yield b, blocks


def _verify_checkpoint(prev: dict, ident: dict, iso: PositionBank, iso_f32: Optional[PositionBank], n_sub: int, m: int, B_max: int) -> dict:
    """Full re-verification of a stored checkpoint (payload digest + schema + numerics + recomputed coupling bounds). Returns the verified state."""
    if not isinstance(prev, dict) or prev.get("schema") != CKPT_SCHEMA: raise InputContractError("checkpoint schema is not the registered one (old/unbound checkpoints are refused)")
    if prev.get("identity") != ident: raise InputContractError("checkpoint identity differs from the current build (refusing to resume / re-bind)")
    done = prev.get("done"); vals, blocks, pw, bounds = prev.get("values"), prev.get("blocks"), prev.get("pairwise"), prev.get("bounds")
    if not (isinstance(done, int) and not isinstance(done, bool) and 0 <= done <= B_max): raise InputContractError("checkpoint 'done' invalid")
    if not (isinstance(vals, list) and isinstance(blocks, list) and isinstance(pw, list) and len(vals) == len(blocks) == len(pw) == done): raise InputContractError("checkpoint inventory inconsistent")
    if prev.get("payload_digest") != _payload_digest(vals, blocks, pw, bounds): raise InputContractError("checkpoint payload digest mismatch (edited or corrupted payload)")
    kc = _kc(n_sub, m)
    for b in range(done):
        v = vals[b]; bl = blocks[b]; p = pw[b]
        if not (isinstance(v, (int, float)) and not isinstance(v, bool) and np.isfinite(v) and v >= 0): raise InputContractError(f"replicate {b}: value not finite/non-negative")
        if not (isinstance(bl, list) and len(bl) == 3 and all(isinstance(x, list) and len(x) == kc for x in bl)): raise InputContractError(f"replicate {b}: block shape")
        flat = [int(i) for x in bl for i in x]
        if any((isinstance(i, bool)) for x in bl for i in x) or len(set(flat)) != 3 * kc or min(flat) < 0 or max(flat) >= iso.K: raise InputContractError(f"replicate {b}: blocks not disjoint / out of range")
        if not (isinstance(p, dict) and set(p) == set(PAIRS)) or any(not (isinstance(p[k], (int, float)) and np.isfinite(p[k]) and p[k] >= 0) for k in PAIRS) or max(float(p[k]) for k in PAIRS) != float(v): raise InputContractError(f"replicate {b}: pairwise/max inconsistency")
    if iso_f32 is not None:
        if not (isinstance(bounds, list) and len(bounds) == done): raise InputContractError("checkpoint bounds inventory")
        for b in range(done):
            rb = _bound(iso, iso_f32, [np.asarray(x, int) for x in blocks[b]])
            if not (isinstance(bounds[b], (int, float)) and np.isfinite(bounds[b]) and abs(float(bounds[b]) - rb) <= 1e-15 * max(1.0, rb)): raise InputContractError(f"replicate {b}: stored coupling bound differs from the value recomputed from the paired pools")
    elif bounds is not None: raise InputContractError("checkpoint carries bounds but no paired pool is supplied")
    return prev


def null_sequence_resumable(iso: PositionBank, n_sub: int, m: int, master_seed: int, ckpt_path: str, dist: Callable = w2_exact, iso_f32: Optional[PositionBank] = None, every: int = 25, log=print, whitening_identity=None, provenance=None) -> dict:
    B_max = RULES.B_levels[-1]; dkind = next((k for k, f in DISTANCE_KINDS.items() if f is dist), "injected_test_callable:" + getattr(dist, "__name__", "unknown"))
    if iso_f32 is not None and (iso_f32.K != iso.K or iso_f32.m != iso.m or not np.array_equal(iso_f32.cid, iso.cid) or iso_f32.cluster_labels != iso.cluster_labels): raise InputContractError("paired f32 pool must share the cluster structure and labels")
    ident = _identity(iso, iso_f32, m, master_seed, n_sub, dkind, whitening_identity, provenance); snap = dict(iso=bank_identity(iso), iso_f32=(None if iso_f32 is None else bank_identity(iso_f32)))
    state = dict(schema=CKPT_SCHEMA, identity=ident, done=0, values=[], blocks=[], pairwise=[], bounds=([] if iso_f32 is not None else None), payload_digest=_payload_digest([], [], [], ([] if iso_f32 is not None else None)))
    if os.path.exists(ckpt_path):
        state = _verify_checkpoint(ser.loads(open(ckpt_path).read()), ident, iso, iso_f32, n_sub, m, B_max); log(f"resuming n_sub={n_sub} from verified checkpoint at replicate {state['done']}/{B_max}")
    def check_banks():
        if dict(iso=bank_identity(iso), iso_f32=(None if iso_f32 is None else bank_identity(iso_f32))) != snap: raise InputContractError("input pool changed during the null build (technical failure; results discarded)")
    def save():
        state["payload_digest"] = _payload_digest(state["values"], state["blocks"], state["pairwise"], state["bounds"]); tmp = ckpt_path + ".tmp"
        with open(tmp, "w") as fh: fh.write(ser.dumps(state)); fh.flush(); os.fsync(fh.fileno())
        os.replace(tmp, ckpt_path)
    t0 = time.time()
    for b, blocks in _blocks_stream(iso, n_sub, m, master_seed, B_max):
        if b < state["done"]:
            if state["blocks"][b] != [bl.tolist() for bl in blocks]: raise InputContractError(f"replayed blocks differ from the checkpoint at replicate {b}")
            continue
        pw = _pairs([_take(iso, bl, n_sub) for bl in blocks], dist); check_banks()
        state["values"].append(float(max(pw.values()))); state["blocks"].append([bl.tolist() for bl in blocks]); state["pairwise"].append({k: float(v) for k, v in pw.items()})
        if iso_f32 is not None: state["bounds"].append(_bound(iso, iso_f32, blocks))
        state["done"] = b + 1
        if state["done"] % every == 0 or state["done"] == B_max: save(); log(f"n_sub={n_sub}: {state['done']}/{B_max} replicates ({time.time() - t0:.0f}s since (re)start)")
    check_banks(); return dict(values=np.asarray(state["values"], float), blocks=state["blocks"], pairwise=state["pairwise"], B_max=B_max, bounds=state["bounds"], checkpoint_digest=state["payload_digest"])


def build_shared_null_resumable(iso: PositionBank, m: int, master_seed: int, ckpt_dir: str, dist: Callable = w2_exact, iso_f32: Optional[PositionBank] = None, whitening_identity: Optional[dict] = None, log=print, provenance: Optional[dict] = None, record: Optional[dict] = None) -> SharedNullAsset:
    """record (optional dict) receives the build provenance (checkpoint digests, provenance, engine version) — kept OUTSIDE the asset identity so the registered SharedNullAsset schema is unchanged."""
    os.makedirs(ckpt_dir, exist_ok=True)
    if not isinstance(iso, PositionBank) or iso.m != m: raise InputContractError("iso bank must be a PositionBank with the registered m")
    dkind = next((k for k, f in DISTANCE_KINDS.items() if f is dist), "injected_test_callable:" + getattr(dist, "__name__", "unknown")); null, bounds, digests = {}, ({} if iso_f32 is not None else None), {}
    snap = dict(iso=bank_identity(iso), iso_f32=(None if iso_f32 is None else bank_identity(iso_f32))); wid = _norm_identity(whitening_identity); prov = _norm_identity(provenance)
    for n in RULES.n_subs:
        e = null_sequence_resumable(iso, n, m, master_seed, os.path.join(ckpt_dir, f"null_nsub{n}.json"), dist, iso_f32, log=log, whitening_identity=wid, provenance=prov)
        null[n] = dict(values=e["values"].tolist(), blocks=e["blocks"], pairwise=e["pairwise"], B_max=e["B_max"]); digests[n] = e["checkpoint_digest"]
        if iso_f32 is not None: bounds[n] = e["bounds"]
    if dict(iso=bank_identity(iso), iso_f32=(None if iso_f32 is None else bank_identity(iso_f32))) != snap: raise InputContractError("input pool changed during the null build")
    ident = _norm_identity(dict(iso=snap["iso"], iso_f32=snap["iso_f32"], whitening=wid, m=int(m), master_seed=int(master_seed), n_subs=list(RULES.n_subs), B_max=RULES.B_levels[-1], rng_key_rule="[master_seed, 5, n_sub, 999]; re-permute on exhaustion", distance_kind=dkind))
    a = SharedNullAsset(ident, null, bounds); a.sha256 = a.payload_sha(); a.validate()
    if record is not None: record.update(dict(asset_sha256=a.sha256, checkpoint_digests=digests, provenance=prov, engine_version=__version__, checkpoint_schema=CKPT_SCHEMA))
    return a
