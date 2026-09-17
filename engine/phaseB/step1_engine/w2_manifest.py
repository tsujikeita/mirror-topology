# -*- coding: utf-8 -*-
"""W2 asset manifest for one family x size (rules §10; engine spec C). build_w2_manifest binds ONLY when the live banks equal the identity snapshot recorded by w2_trigger at
distance execution (no re-binding of an old result to other banks; distance kind / whitening / m / master seed come from the execution snapshot, never from the caller).
The manifest is an independent deep-copied snapshot with exact inventories. verify_w2_manifest REPLAYS the decision from stored evidence without re-running the distance:
stored pairwise values -> observed maxima and null maxima (must equal stored values) -> w2_stop -> stored trace/B_final/hash -> seed spread -> w2_validate with the stored bounds ->
derived trigger; every copy carried by the result (observed, stop, null_q99, validation, trigger, whitening, master_seed, m, distance kind) must agree. It returns a TYPED verified
decision (trigger/validation/B_final) that consumers must use instead of the raw result dict."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import copy, hashlib, math
import numpy as np
from .errors import InputContractError
from .rules_config import RULES
from .positions import PositionBank, DISTANCE_KINDS, bank_identity, VerifiedW2Decision
from .w2_stop import StopResult, w2_stop, w2_validate, seed_spread
from . import serialization as ser
from .truth import UNKNOWN

PAIRS = ("P1P2", "P1P3", "P2P3")


def _asha(a) -> str: return hashlib.sha256(np.ascontiguousarray(np.asarray(a, float)).tobytes()).hexdigest()


def _norm(d): return ser.from_jsonable(ser.to_jsonable(copy.deepcopy(d)))


@dataclass
class W2Manifest:
    family: str; size_id: str; m: int; master_seed: int; distance_kind: str; whitening: Optional[dict]
    positions: List[dict]; iso: dict; null_prefix_id: str; null_sha256: Dict[int, str]; null_B_max: Dict[int, int]; observed_hash: str; stop: dict; validation: dict; bounds: dict; q99_at_B_final: Dict[int, float]
    execution_inputs: Optional[dict] = None; shared_null_sha256: Optional[str] = None
    def as_dict(self): return ser.to_jsonable(asdict(self))
    def payload_sha(self) -> str:
        """Canonical SHA of the whole manifest record (strict JSON, sorted keys)."""
        return hashlib.sha256(ser.dumps(dict(sorted(ser.from_jsonable(self.as_dict()).items()))).encode()).hexdigest()


class SharedNullAssetRef:
    """Marker wrapper: bind/verify a shared-null result against the SharedNullAsset object (never against a live iso bank)."""
    def __init__(self, asset): self.asset = asset


def _check_inputs_snapshot_shared(ev: dict, positions: List[PositionBank], asset):
    inp = ev.get("inputs")
    if not inp: raise InputContractError("w2_result evidence lacks the execution-time input snapshot (cannot bind)")
    if [bank_identity(p) for p in positions] != inp["positions"]: raise InputContractError("live position banks differ from the banks used at distance execution")
    if inp.get("shared_null_sha256") != asset.sha256: raise InputContractError("snapshot shared null SHA differs from the asset")
    for n in RULES.n_subs:
        if _norm(ev["null"][n]) != _norm(asset.null[n]): raise InputContractError("result null evidence differs from the shared asset")
    idn = asset.identity
    for k in ("m", "master_seed", "distance_kind"):
        if _norm(ev[k]) != _norm(idn[k]) or _norm(inp.get(k)) != _norm(idn[k]): raise InputContractError(f"evidence/snapshot.{k} differs from the shared asset identity")
    if _norm(ev.get("whitening")) != _norm(idn["whitening"]) or _norm(inp.get("whitening")) != _norm(idn["whitening"]): raise InputContractError("whitening identity differs from the shared asset")
    return dict(inp, iso=idn["iso"], m=idn["m"], master_seed=idn["master_seed"], distance_kind=idn["distance_kind"], whitening=idn["whitening"])


def _check_inputs_snapshot(ev: dict, positions: List[PositionBank], iso: PositionBank):
    inp = ev.get("inputs")
    if not inp: raise InputContractError("w2_result evidence lacks the execution-time input snapshot (cannot bind)")
    if [bank_identity(p) for p in positions] != inp["positions"]: raise InputContractError("live position banks differ from the banks used at distance execution (old result cannot be bound to other banks)")
    if bank_identity(iso) != inp["iso"]: raise InputContractError("live isotropic bank differs from the bank used at distance execution")
    for k in ("m", "master_seed", "distance_kind", "whitening"):
        if k in ev and _norm(ev[k]) != _norm(inp[k]): raise InputContractError(f"evidence.{k} differs from the execution snapshot")
    return inp


def build_w2_manifest(family: str, size_id: str, positions: List[PositionBank], iso: PositionBank, w2_result: dict) -> W2Manifest:
    ev = w2_result.get("evidence")
    if not ev: raise InputContractError("w2_result without evidence cannot be bound")
    if len(positions) != 3 or len({p.position_id for p in positions}) != 3: raise InputContractError("three distinct positions required")
    shared = ev.get("shared_null_sha256")
    if shared is not None:
        if iso is not None and not isinstance(iso, SharedNullAssetRef): raise InputContractError("a shared-null result must be bound with the SharedNullAsset (pass SharedNullAssetRef), not a live iso bank")
        if iso is None or iso.asset.sha256 != shared: raise InputContractError("shared null asset differs from the one recorded in the result")
        iso.asset.validate(); inp = _check_inputs_snapshot_shared(ev, positions, iso.asset)
    else: inp = _check_inputs_snapshot(ev, positions, iso)
    if set(int(n) for n in ev["null"]) != set(RULES.n_subs): raise InputContractError("null evidence inventory must be exactly the registered n_sub set")
    stop = _norm(w2_result["stop"])
    null_sha = {int(n): _asha(ev["null"][n]["values"]) for n in ev["null"]}; null_B = {int(n): int(ev["null"][n]["B_max"]) for n in ev["null"]}
    q99 = {int(n): float(np.quantile(np.asarray(ev["null"][n]["values"], float)[:int(stop["B_final"])], 0.99, method=RULES.quantile_method)) for n in ev["null"]}
    if "null_q99" in w2_result and (set(int(k) for k in w2_result["null_q99"]) != set(q99) or any(not math.isclose(q99[n], float(w2_result["null_q99"][n]), rel_tol=1e-12) for n in q99)): raise InputContractError("null_q99 in the result does not reproduce from the stored null values")
    inp = _norm(inp)
    man = W2Manifest(family, size_id, int(inp["m"]), int(inp["master_seed"]), inp["distance_kind"], inp["whitening"], copy.deepcopy(inp["positions"]), copy.deepcopy(inp["iso"]), stop["null_prefix_id"], null_sha, null_B,
                     stop["observed_hash"], stop, _norm(w2_result["validation"]), _norm(ev.get("bounds") or {}), q99, execution_inputs=inp, shared_null_sha256=shared)
    verify_w2_manifest(man, positions, iso, w2_result)                                                   # a manifest that cannot be replayed is never issued
    return man


def _replay_observed(ev: dict, positions_K: Dict[int, int], m: int) -> Dict[int, Dict[int, float]]:
    obs = {}; positions_ids = set(positions_K)
    if set(int(n) for n in ev["observed"]) != set(RULES.n_subs): raise InputContractError("observed evidence inventory must be the registered n_sub set")
    for n in RULES.n_subs:
        block = ev["observed"][n]
        if set(int(s) for s in block) != set(RULES.seed_ids): raise InputContractError(f"observed seed inventory for n_sub={n} must be {RULES.seed_ids}")
        obs[n] = {}
        for s in RULES.seed_ids:
            d = block[s]; pw = d["pairwise"]
            if set(pw) != set(PAIRS): raise InputContractError("observed pair set must be {P1P2,P1P3,P2P3}")
            vals = [float(pw[k]) for k in PAIRS]
            if not all(math.isfinite(v) and v >= 0 for v in vals): raise InputContractError("observed pairwise values must be finite and non-negative")
            if not math.isclose(max(vals), float(d["W2_max"]), rel_tol=0, abs_tol=0): raise InputContractError("stored observed W2_max does not equal the max of the stored pairwise values")
            subs = d["subsets"]; kc = n // m
            if set(int(k) for k in subs) != positions_ids: raise InputContractError("observed subsets must cover exactly the position ids of the banks")
            for pid, idx in subs.items():
                a = np.asarray(idx)
                if a.ndim != 1 or len(a) != kc or a.dtype.kind not in "iu" or len(set(a.tolist())) != kc or np.any(a < 0) or np.any(a >= positions_K[int(pid)]): raise InputContractError("observed subset must be kc unique cluster indices within 0..K-1 of that live bank")
            if int(d.get("clusters_per_sample", kc)) != kc or int(d.get("n_sub", n)) != n: raise InputContractError("observed subsample cardinality does not match n_sub/m")
            obs[n][s] = float(d["W2_max"])
    return obs


def _replay_null(ev: dict, m: int, iso_K: int) -> Dict[int, np.ndarray]:
    null = {}
    for n in RULES.n_subs:
        e = ev["null"][n]; vals = np.asarray(e["values"], float); kc = n // m
        if vals.ndim != 1 or len(vals) != RULES.B_levels[-1] or int(e["B_max"]) != RULES.B_levels[-1]: raise InputContractError("null sequence must be 1-D with length B_max (registered)")
        if not np.all(np.isfinite(vals)) or np.any(vals < 0): raise InputContractError("null values must be finite and non-negative")
        if len(e["blocks"]) != len(vals) or len(e["pairwise"]) != len(vals): raise InputContractError("null blocks/pairwise inventory must match the sequence length")
        for b in range(len(vals)):
            blocks = [np.asarray(x) for x in e["blocks"][b]]
            if len(blocks) != 3 or any(bl.ndim != 1 or len(bl) != kc or bl.dtype.kind not in "iu" or np.any(bl < 0) or np.any(bl >= iso_K) for bl in blocks): raise InputContractError("null block shape/range invalid")
            if len(set(np.concatenate(blocks).tolist())) != 3 * kc: raise InputContractError(f"null replicate {b}: blocks are not disjoint")
            pw = e["pairwise"][b]
            if set(pw) != set(PAIRS): raise InputContractError("null pair set must be {P1P2,P1P3,P2P3}")
            pv = [float(pw[k]) for k in PAIRS]
            if not all(math.isfinite(v) and v >= 0 for v in pv) or not math.isclose(max(pv), float(vals[b]), rel_tol=0, abs_tol=0): raise InputContractError(f"null replicate {b}: stored max does not equal the max of the stored pairwise values")
        null[n] = vals
    return null


def _check_bounds(bounds: dict):
    ob, dq = bounds.get("obs_bounds"), bounds.get("delta_q99_bound")
    if ob is None or dq is None: return None, None
    if set(int(k) for k in ob) != set(RULES.n_subs) or set(int(k) for k in dq) != set(RULES.n_subs): raise InputContractError("selection bound inventory must be the registered n_sub set (empty dicts are not bounds)")
    for n in RULES.n_subs:
        if set(int(s) for s in ob[n]) != set(RULES.seed_ids): raise InputContractError("observed bound seed inventory incomplete")
        for s in RULES.seed_ids:
            v = float(ob[n][s])
            if not (math.isfinite(v) and v >= 0): raise InputContractError("observed bound must be finite and non-negative")
        if not (math.isfinite(float(dq[n])) and float(dq[n]) >= 0): raise InputContractError("delta_q99_bound must be finite and non-negative")
    return {int(n): {int(s): float(v) for s, v in ob[n].items()} for n in ob}, {int(n): float(v) for n, v in dq.items()}


def verify_w2_manifest(man: W2Manifest, positions: List[PositionBank], iso: PositionBank, w2_result: dict, require_registered_distance: bool = False) -> dict:
    """Replay the whole decision from stored evidence and require agreement of manifest, result copies and live banks. Returns the typed verified decision."""
    if len(positions) != 3: raise InputContractError("three positions required")
    ev = w2_result.get("evidence") or {}
    if man.shared_null_sha256 is not None or ev.get("shared_null_sha256") is not None:
        if not isinstance(iso, SharedNullAssetRef) or iso.asset.sha256 != man.shared_null_sha256 or ev.get("shared_null_sha256") != man.shared_null_sha256: raise InputContractError("shared-null manifest must be verified against its SharedNullAsset")
        iso.asset.validate(); inp = _check_inputs_snapshot_shared(ev, positions, iso.asset); iso_K = int(iso.asset.identity["iso"]["K"])
    else: inp = _check_inputs_snapshot(ev, positions, iso); iso_K = iso.K
    if man.execution_inputs != _norm(inp): raise InputContractError("manifest execution snapshot differs from the result's execution snapshot")
    if man.positions != inp["positions"] or _norm(man.iso) != _norm(inp["iso"]) or man.m != int(inp["m"]) or man.master_seed != int(inp["master_seed"]) or man.distance_kind != inp["distance_kind"] or _norm(man.whitening) != _norm(inp["whitening"]):
        raise InputContractError("manifest identity (banks/m/master_seed/distance kind/whitening) differs from the execution snapshot")
    if len({p["position_id"] for p in man.positions}) != 3: raise InputContractError("manifest positions are not distinct")
    if require_registered_distance:
        if man.m != RULES.m: raise InputContractError(f"manifest m={man.m} differs from the registered m={RULES.m}")
        if man.distance_kind not in DISTANCE_KINDS: raise InputContractError(f"distance kind {man.distance_kind!r} is not the registered production distance")
    # exact inventories
    if set(int(k) for k in man.null_sha256) != set(RULES.n_subs) or set(int(k) for k in man.null_B_max) != set(RULES.n_subs) or set(int(k) for k in man.q99_at_B_final) != set(RULES.n_subs): raise InputContractError("manifest null inventory must be the registered n_sub set")
    if set(int(k) for k in ev.get("null", {})) != set(RULES.n_subs): raise InputContractError("evidence null inventory must be the registered n_sub set")
    # replay observed / null from stored pair values
    obs = _replay_observed(ev, {p.position_id: p.K for p in positions}, man.m); null = _replay_null(ev, man.m, iso_K)
    for n in RULES.n_subs:
        if _asha(null[n]) != man.null_sha256[n] or int(man.null_B_max[n]) != len(null[n]): raise InputContractError(f"null sequence for n_sub={n} does not match the manifest")
    if _norm(w2_result.get("observed")) != _norm(obs): raise InputContractError("result.observed does not equal the observed maxima replayed from the stored pairwise values")
    # replay the stop rule
    st_rep = w2_stop(null, obs, man.null_prefix_id); st_man = _norm(man.stop); st_res = _norm(w2_result.get("stop"))
    if st_rep.as_dict() != ser.to_jsonable(st_man): raise InputContractError("replayed stop result differs from the manifest stop (trace/B_final/prefix/observed)")
    if ser.to_jsonable(st_res) != ser.to_jsonable(st_man): raise InputContractError("result.stop differs from the manifest stop")
    StopResult(**{k: st_man[k] for k in ("B_final", "stop_reason", "trace", "null_prefix_id", "state", "observed_hash", "observed")}).validate()
    if st_rep.observed_hash != man.observed_hash: raise InputContractError("observed hash differs from the manifest")
    for n in RULES.n_subs:
        q = float(np.quantile(null[n][:st_rep.B_final], 0.99, method=RULES.quantile_method))
        if not math.isclose(q, float(man.q99_at_B_final[n]), rel_tol=1e-12): raise InputContractError(f"q99 at B_final for n_sub={n} does not reproduce")
    if "null_q99" in w2_result and (set(int(k) for k in w2_result["null_q99"]) != set(RULES.n_subs) or any(not math.isclose(float(w2_result["null_q99"][n]), float(man.q99_at_B_final[n]), rel_tol=1e-12) for n in RULES.n_subs)): raise InputContractError("result.null_q99 differs from the replayed q99")
    # replay validation from stored bounds
    if _norm(ev.get("bounds") or {}) != _norm(man.bounds): raise InputContractError("result bounds differ from the manifest bounds")
    ob, dq = _check_bounds(_norm(man.bounds)); spread = max(seed_spread(obs[n]) for n in obs)
    # A shared result must derive its quantile bound from the referenced asset,
    # not merely agree with a second copy of the result's own summary.
    if isinstance(iso, SharedNullAssetRef):
        rb = iso.asset.replicate_bounds
        stored_dq = _norm(man.bounds).get("delta_q99_bound")
        if rb is None:
            if stored_dq is not None:
                raise InputContractError("shared asset has no measured bound; a case cannot invent one")
        elif stored_dq is not None:
            if not isinstance(stored_dq, dict) or set(stored_dq) != set(RULES.n_subs):
                raise InputContractError("shared prefix bound inventory mismatch")
            for n in RULES.n_subs:
                expected = float(np.max(np.asarray(rb[n], float)[:st_rep.B_final]))
                actual = stored_dq[n]
                if isinstance(actual, (bool, np.bool_)) or not isinstance(actual, (float, int, np.floating, np.integer)) or not math.isfinite(float(actual)) or float(actual) != expected:
                    raise InputContractError("case quantile bound does not reproduce from the shared asset at its B_final")
        elif man.bounds.get("obs_bounds") is not None:
            raise InputContractError("available shared prefix bound missing from case result")
    missing_reason = "selection bounds not supplied (not treated as 0)"
    if isinstance(iso, SharedNullAssetRef):
        from .w2_shared import MISSING_BOUNDS_REASON
        missing_reason = MISSING_BOUNDS_REASON
    val_rep = dict(state="w2-unresolved", reason=missing_reason) if ob is None else w2_validate(st_rep, spread, ob, dq, obs)
    if _norm(val_rep) != _norm(man.validation): raise InputContractError("replayed validation differs from the manifest validation")
    if _norm(w2_result.get("validation")) != _norm(man.validation): raise InputContractError("result.validation differs from the manifest validation")
    trig = val_rep["trigger"] if val_rep["state"] == "valid" else UNKNOWN
    if w2_result.get("trigger") != trig: raise InputContractError("result.trigger differs from the trigger derived from the replayed validation")
    return dict(verified=True, scope="replay of stop/validation/trigger from stored pairwise values, blocks, subsets and bounds; live bank identity == execution snapshot; distance execution not re-run",
                distance_kind=man.distance_kind, registered_distance=(man.distance_kind in DISTANCE_KINDS), trigger=trig, validation=copy.deepcopy(val_rep), B_final=st_rep.B_final, observed_hash=st_rep.observed_hash)


def verified_w2_for_decision(man: W2Manifest, positions, iso, w2_result: dict, require_registered_distance: bool = False) -> VerifiedW2Decision:
    """Typed, frozen, checksummed input for position_decision: only the replay-verified trigger/validation are exposed (the raw result dict is never reused)."""
    v = verify_w2_manifest(man, positions, iso, w2_result, require_registered_distance)
    return VerifiedW2Decision.issue(v["trigger"], v["validation"], v["B_final"], v["observed_hash"], man.distance_kind, v["scope"])
