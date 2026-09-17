# -*- coding: utf-8 -*-
"""Observer-position W2 trigger path (rules §10) with strict cluster-cardinality contracts and evidence retention.
PositionBank: validated (N,2) rows, m rows per cluster, contiguous cluster ids 0..K-1, N = K*m; exactly three distinct position objects/ids are required.
Subsamples are asserted to contain exactly n_sub rows. w2_exact checks the POT solver termination (log=True metadata + captured warnings), not only finiteness.
Evidence (per-seed cluster subsets and pairwise values, the full maximal null sequence with per-replicate block ids and pairwise values, distance identity,
whitening identity) is returned instead of being reduced to maxima at the function exit."""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Callable, Dict, List, Optional
import math, warnings
import numpy as np
from .errors import InputContractError
from .rules_config import RULES
from .w2_stop import w2_stop, w2_validate, seed_spread
from .position_state import position_state
from .expansion import norm_hits, norm_precision, norm_stage
from .truth import UNKNOWN, TECH


def whitening_from_calibration(T: np.ndarray):
    T = np.asarray(T, float)
    if T.ndim != 2 or T.shape[1] != 2 or not np.all(np.isfinite(T)) or len(T) < 3: raise InputContractError("calibration bank must be a finite (N,2) array")
    mu = T.mean(0); S = np.cov(T.T); L = np.linalg.cholesky(S); W = np.linalg.inv(L)
    if np.abs(W @ S @ W.T - np.eye(2)).max() >= 1e-10: raise InputContractError("G_whitening failed")
    return mu, W


def w2_exact(a: np.ndarray, b: np.ndarray) -> float:
    """Registered production distance: exact 2-D W2 via POT emd2 (uniform weights). Requires a clean solver termination: no warning, result_code (if provided) optimal,
    finite non-negative cost. A finite value with a solver warning is a technical failure, never an 'exact' W2."""
    import ot
    a = np.asarray(a, float); b = np.asarray(b, float)
    if a.ndim != 2 or b.ndim != 2 or a.shape[1] != 2 or b.shape[1] != 2 or not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))): raise InputContractError("W2 inputs must be finite (n,2) arrays")
    Mc = ot.dist(a, b, metric="sqeuclidean")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        out = ot.emd2(np.full(len(a), 1 / len(a)), np.full(len(b), 1 / len(b)), Mc, numItermax=1_000_000, log=True)
    # registered return contract of POT emd2(log=True): [cost, log] with log containing 'warning' and an INTEGER 'result_code' (1 = optimal); anything else is rejected (no fallback)
    if not (isinstance(out, (tuple, list)) and len(out) == 2 and isinstance(out[1], dict)): raise InputContractError("POT emd2(log=True) must return [cost, log]")
    v, lg = out[0], out[1]
    if not {"warning", "result_code"} <= set(lg): raise InputContractError("POT log must contain 'warning' and 'result_code'")
    if caught: raise InputContractError(f"POT solver warning: {[str(w.message) for w in caught]}")
    if lg["warning"]: raise InputContractError(f"POT solver reported: {lg['warning']}")
    rc = lg["result_code"]
    if isinstance(rc, (bool, np.bool_)) or not isinstance(rc, (int, np.integer)) or int(rc) != 1: raise InputContractError(f"POT solver result_code {rc!r} (must be the integer 1 = optimal)")
    if isinstance(v, (list, tuple, np.ndarray)):
        if np.size(v) != 1: raise InputContractError("unexpected POT cost shape")
        v = np.asarray(v, float).ravel()[0]
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, float, np.integer, np.floating)): raise InputContractError("POT cost must be a real number")
    v = float(v)
    if not math.isfinite(v) or v < 0: raise InputContractError("non-finite or negative W2 cost")
    return math.sqrt(v)


DISTANCE_KINDS = {"exact_pot_w2": w2_exact}


@dataclass
class PositionBank:
    """One observer position: whitened (T1,T2) rows and contiguous cluster ids; exactly m rows per cluster."""
    position_id: int; Tw: np.ndarray; cid: np.ndarray; m: Optional[int] = None
    def __post_init__(self):
        self.Tw = np.asarray(self.Tw, float); self.cid = np.asarray(self.cid)
        if self.Tw.ndim != 2 or self.Tw.shape[1] != 2 or len(self.Tw) == 0 or not np.all(np.isfinite(self.Tw)): raise InputContractError("position bank must be a non-empty finite (N,2) array")
        if self.cid.shape != (len(self.Tw),) or not np.issubdtype(self.cid.dtype, np.integer) or np.any(self.cid < 0): raise InputContractError("cluster ids invalid")
        if not isinstance(self.position_id, (int, np.integer)) or isinstance(self.position_id, bool): raise InputContractError("position_id must be an integer")
        labels, inv = np.unique(self.cid, return_inverse=True); self.cluster_labels = labels.tolist()   # explicit mapping of unique labels -> contiguous 0..K-1 (no empty clusters)
        self.cid = inv.astype(np.int64); counts = np.bincount(self.cid); K = len(counts)
        if len(set(counts.tolist())) != 1: raise InputContractError("every cluster must have the same number of rows m")
        m_actual = int(counts[0])
        if self.m is None: self.m = m_actual
        elif int(self.m) != m_actual: raise InputContractError(f"declared m={self.m} but clusters have {m_actual} rows")
        self._K = K
    @property
    def K(self): return self._K


def bank_identity(b: PositionBank) -> dict:
    """Identity of a position/iso bank as used at distance execution: sizes, whitened rows SHA, contiguous cid SHA, original label map SHA."""
    import hashlib
    return dict(position_id=int(b.position_id), K=int(b.K), m=int(b.m), rows=int(len(b.Tw)), Tw_sha256=hashlib.sha256(np.ascontiguousarray(b.Tw.astype(np.float64)).tobytes()).hexdigest(),
                cid_sha256=hashlib.sha256(np.ascontiguousarray(b.cid.astype(np.int64)).tobytes()).hexdigest(), labels_sha256=hashlib.sha256(str(b.cluster_labels).encode()).hexdigest())


def _take(bank: PositionBank, clusters, n_sub: int):
    rows = bank.Tw[np.isin(bank.cid, clusters)]
    if len(rows) != n_sub: raise InputContractError(f"subsample has {len(rows)} rows, registered n_sub={n_sub}")
    return rows


def _check_positions(positions: List[PositionBank], m: int):
    if len(positions) != 3: raise InputContractError("exactly three observer positions are required")
    if len({id(p) for p in positions}) != 3 or len({p.position_id for p in positions}) != 3: raise InputContractError("three DISTINCT position banks/ids are required")
    for p in positions:
        if not isinstance(p, PositionBank): raise InputContractError("positions must be PositionBank")
        if p.m != m: raise InputContractError(f"position {p.position_id}: bank m={p.m} differs from the registered m={m}")


def _kc(n_sub: int, m: int) -> int:
    if not (isinstance(n_sub, (int, np.integer)) and isinstance(m, (int, np.integer))) or n_sub <= 0 or m <= 0: raise InputContractError("n_sub and m must be positive integers")
    kc = n_sub // m
    if kc * m != n_sub or kc < 2: raise InputContractError("n_sub must be a multiple of m with >= 2 clusters")
    return int(kc)


def _pairs(samples: List[np.ndarray], dist: Callable) -> Dict[str, float]:
    pw = {}
    for a in range(3):
        for b in range(a + 1, 3):
            v = float(dist(samples[a], samples[b]))
            if not math.isfinite(v) or v < 0: raise InputContractError("pairwise W2 must be finite and non-negative")
            pw[f"P{a+1}P{b+1}"] = v
    return pw


def observed_w2max(positions: List[PositionBank], n_sub: int, m: int, seed: int, master_seed: int, dist: Callable = w2_exact) -> dict:
    _check_positions(positions, m); kc = _kc(n_sub, m); rng = np.random.default_rng(np.random.SeedSequence([master_seed, 5, int(n_sub), int(seed)]))
    subsets = {}; S3 = []
    for p in positions:
        if p.K < kc: raise InputContractError(f"position {p.position_id}: fewer clusters ({p.K}) than the subsample needs ({kc})")
        kk = np.sort(rng.choice(p.K, kc, replace=False)); subsets[p.position_id] = kk.tolist(); S3.append(_take(p, kk, n_sub))
    pw = _pairs(S3, dist); return dict(pairwise=pw, W2_max=max(pw.values()), seed=int(seed), n_sub=int(n_sub), clusters_per_sample=kc, subsets=subsets)


def null_max_sequence(iso: PositionBank, n_sub: int, m: int, master_seed: int, dist: Callable = w2_exact, B_max: int = None) -> dict:
    """ONE maximal null sequence: each replicate draws three DISJOINT cluster blocks from the isotropic pool (re-permute when exhausted). Returns values + per-replicate evidence."""
    if not isinstance(iso, PositionBank): raise InputContractError("iso must be a PositionBank")
    if iso.m != m: raise InputContractError(f"isotropic bank m={iso.m} differs from the registered m={m}")
    B_max = RULES.B_levels[-1] if B_max is None else int(B_max); kc = _kc(n_sub, m)
    if iso.K < 3 * kc: raise InputContractError("isotropic pool too small for three disjoint blocks")
    rng = np.random.default_rng(np.random.SeedSequence([master_seed, 5, int(n_sub), 999])); perm = rng.permutation(iso.K); ptr = 0; vals = np.empty(B_max); blocks_ev = []; pw_ev = []
    for b in range(B_max):
        if ptr + 3 * kc > iso.K: perm = rng.permutation(iso.K); ptr = 0
        blocks = [np.sort(perm[ptr + j * kc: ptr + (j + 1) * kc]) for j in range(3)]; ptr += 3 * kc
        if len(set(np.concatenate(blocks).tolist())) != 3 * kc: raise InputContractError("null blocks must be disjoint")
        pw = _pairs([_take(iso, bl, n_sub) for bl in blocks], dist); vals[b] = max(pw.values()); blocks_ev.append([bl.tolist() for bl in blocks]); pw_ev.append(pw)
    return dict(values=vals, blocks=blocks_ev, pairwise=pw_ev, B_max=B_max, n_sub=int(n_sub), clusters_per_block=kc)


def norm_position_probability(k, d: dict) -> dict:
    """PositionProbability contract: P finite in [0,1]; hits non-negative int (NumPy ints ok, bool rejected, fractions rejected); precision in the registered enum; stage in {N0,N4}."""
    if not isinstance(d, dict) or not {"P", "hits", "precision"} <= set(d): raise InputContractError(f"position {k}: P, hits and precision are required")
    stage = d.get("stage", "N4")                                                                         # stage omitted -> declared N-final (the orchestrator always supplies the real stage)
    P = d["P"]
    if isinstance(P, (bool, np.bool_)) or not isinstance(P, (int, float, np.integer, np.floating)) or not math.isfinite(float(P)) or not (0.0 <= float(P) <= 1.0): raise InputContractError(f"position {k}: P must be a finite probability in [0,1]")
    hits = norm_hits(d["hits"], f"position {k} hits"); prec = norm_precision(d["precision"]); Pf = float(P)
    if prec == "pass" and hits == 0: raise InputContractError(f"position {k}: precision 'pass' with zero hits is inconsistent")
    if (Pf == 0.0) != (hits == 0): raise InputContractError(f"position {k}: P and hits disagree about zero events")
    if "N" in d:
        N = norm_hits(d["N"], f"position {k} N")
        if N == 0 or not math.isclose(Pf, hits / N, rel_tol=0, abs_tol=1e-12): raise InputContractError(f"position {k}: P must equal hits/N")
    return dict(P=Pf, hits=hits, precision=prec, stage=norm_stage(stage))


def event_ratio_trigger(P_k: Dict[int, dict]):
    """Registered rule: max/min > 2 after the precision gate, evaluated ONLY on N-final (stage N4, or N0 when the gate passed at N0) results.
    N0 results that did not pass -> unknown (N expansion first; not a position expansion). Zero hits at N-final -> True with expansion_due_to_zero_hits. Technical -> TECH."""
    if len(P_k) != 3: raise InputContractError("three positions required")
    q = {k: norm_position_probability(k, v) for k, v in P_k.items()}
    if any(v["precision"] == "technical_fail" for v in q.values()): return TECH, dict(reason="technical_fail")
    pending = [k for k, v in q.items() if v["stage"] == "N0" and v["precision"] != "pass"]
    if pending: return UNKNOWN, dict(reason="N expansion pending (N0 precision not met); position expansion is evaluated after the single N expansion", pending=pending)
    if any(v["hits"] == 0 for v in q.values()): return True, dict(reason="expansion_due_to_zero_hits", expansion_due_to_zero_hits=True)
    if any(v["precision"] != "pass" for v in q.values()): return UNKNOWN, dict(reason="precision gate not met for a position after N expansion")
    ps = [v["P"] for v in q.values()]
    return bool(max(ps) / min(ps) > 2.0), dict(ratio=max(ps) / min(ps))


def _norm_identity(x):
    from . import serialization as _ser
    return _ser.from_jsonable(_ser.to_jsonable(x))


def w2_trigger(positions: List[PositionBank], iso: PositionBank, m: int, master_seed: int, dist: Callable = w2_exact, null_prefix_id: str = "null", obs_bounds=None, delta_q99_bound=None, whitening_identity: Optional[dict] = None) -> dict:
    """Full W2 path for one family x size. The execution-time input snapshot (bank identities, m, master seed, distance kind, normalised whitening, bounds) is taken BEFORE the first
    distance call; at the end the live identities are re-hashed and must equal the snapshot (a bank mutated during the run is a technical failure). Evidence retained: observed
    subsets/pairwise per (n_sub, seed), full maximal null sequences with block ids and pairwise values. Selection bounds are required for validation (never 0 by default).
    Note: the maximal null sequence is computed in full (B_max) before the stop rule; no runtime saving from early stopping is claimed."""
    _check_positions(positions, m)
    if not isinstance(iso, PositionBank): raise InputContractError("iso must be a PositionBank")
    dkind = next((k for k, f in DISTANCE_KINDS.items() if f is dist), "injected_test_callable:" + getattr(dist, "__name__", "unknown"))
    snapshot = _norm_identity(dict(positions=[bank_identity(p) for p in positions], iso=bank_identity(iso), m=int(m), master_seed=int(master_seed), distance_kind=dkind, whitening=whitening_identity))
    bounds = _norm_identity(dict(obs_bounds=obs_bounds, delta_q99_bound=delta_q99_bound))
    obs_ev = {n: {s: observed_w2max(positions, n, m, s, master_seed, dist) for s in RULES.seed_ids} for n in RULES.n_subs}
    observed = {n: {s: obs_ev[n][s]["W2_max"] for s in RULES.seed_ids} for n in RULES.n_subs}
    null_ev = {n: null_max_sequence(iso, n, m, master_seed, dist) for n in RULES.n_subs}; null = {n: null_ev[n]["values"] for n in RULES.n_subs}
    end_identity = _norm_identity(dict(positions=[bank_identity(p) for p in positions], iso=bank_identity(iso)))
    if end_identity["positions"] != snapshot["positions"] or end_identity["iso"] != snapshot["iso"]: raise InputContractError("input bank identity changed during the W2 run (technical failure; results discarded)")
    stop = w2_stop(null, observed, null_prefix_id); spread = max(seed_spread(observed[n]) for n in observed)
    evidence = dict(inputs=snapshot, distance_kind=dkind, whitening=snapshot["whitening"], observed=obs_ev, null={n: dict(values=null_ev[n]["values"].tolist(), blocks=null_ev[n]["blocks"], pairwise=null_ev[n]["pairwise"], B_max=null_ev[n]["B_max"]) for n in null_ev}, bounds=bounds, m=int(m), master_seed=int(master_seed))
    ob, dq = bounds["obs_bounds"], bounds["delta_q99_bound"]
    if ob is None or dq is None:
        return dict(stop=stop.as_dict(), observed=observed, validation=dict(state="w2-unresolved", reason="selection bounds not supplied (not treated as 0)"), trigger=UNKNOWN, spread=spread, evidence=evidence)
    val = w2_validate(stop, spread, ob, dq, observed); trig = val["trigger"] if val["state"] == "valid" else UNKNOWN
    return dict(stop=stop.as_dict(), observed=observed, validation=val, trigger=trig, spread=spread, null_q99={n: float(np.quantile(null[n][:stop.B_final], 0.99, method=RULES.quantile_method)) for n in null}, evidence=evidence)


@dataclass(frozen=True)
class VerifiedW2Decision:
    """Replay-verified W2 decision (issued only by w2_manifest.verified_w2_for_decision). Scalar frozen fields with a content checksum; the consumer re-checks the checksum
    and the trigger/state consistency, so a changed object is rejected at intake."""
    trigger: object; validation_state: str; validation_reason: Optional[str]; B_final: int; observed_hash: str; distance_kind: str; scope: str; checksum: str

    @staticmethod
    def _digest(trigger, validation_state, validation_reason, B_final, observed_hash, distance_kind, scope) -> str:
        import hashlib, json
        return hashlib.sha256(json.dumps([str(trigger), validation_state, validation_reason, int(B_final), observed_hash, distance_kind, scope], sort_keys=True).encode()).hexdigest()

    @staticmethod
    def _check_schema(trigger, validation_state, validation_reason, B_final):
        # Content integrity is checked separately; a checksum does not validate types.
        if not isinstance(validation_state, str) or validation_state not in ("valid", "w2-unresolved"):
            raise InputContractError("VerifiedW2Decision requires a registered replay validation state")
        if isinstance(B_final, (bool, np.bool_)) or not isinstance(B_final, (int, np.integer)) or int(B_final) not in RULES.B_levels:
            raise InputContractError("VerifiedW2Decision B_final must be a registered integer level")
        if validation_reason is not None and not isinstance(validation_reason, str):
            raise InputContractError("VerifiedW2Decision reason must be str or None")
        if validation_state == "valid":
            if not isinstance(trigger, (bool, np.bool_)):
                raise InputContractError("valid validation requires a boolean trigger (not 0/1)")
        elif not isinstance(trigger, str) or trigger != UNKNOWN:
            raise InputContractError("w2-unresolved validation requires trigger=unknown")

    @classmethod
    def issue(cls, trigger, validation: dict, B_final: int, observed_hash: str, distance_kind: str, scope: str):
        if not isinstance(validation, dict):
            raise InputContractError("validation must be a replay result dict")
        st = validation.get("state"); rs = validation.get("reason")
        cls._check_schema(trigger, st, rs, B_final)
        if st == "valid":
            vt = validation.get("trigger")
            if not isinstance(vt, (bool, np.bool_)) or bool(vt) != bool(trigger):
                raise InputContractError("trigger must agree with the replay validation trigger")
            trigger = bool(trigger)
        elif "trigger" in validation and validation["trigger"] != UNKNOWN:
            raise InputContractError("unresolved validation has an inconsistent trigger")
        B_final = int(B_final)
        return cls(trigger, st, rs, B_final, observed_hash, distance_kind, scope, cls._digest(trigger, st, rs, B_final, observed_hash, distance_kind, scope))

    def check(self):
        # Reject malformed restored/reconstructed values BEFORE the lossy int conversion in _digest.
        self._check_schema(self.trigger, self.validation_state, self.validation_reason, self.B_final)
        if self.checksum != self._digest(self.trigger, self.validation_state, self.validation_reason, self.B_final, self.observed_hash, self.distance_kind, self.scope):
            raise InputContractError("VerifiedW2Decision content does not match its checksum")
        return True


@dataclass(frozen=True)
class W2NotEvaluated:
    """Explicit marker: no W2 assets were evaluated for this family x size (position status stays unresolved on the W2 branch)."""
    reason: str


def position_decision(w2, P_k: Dict[int, dict], tech_fail: bool = False) -> dict:
    """Production entry: accepts ONLY a VerifiedW2Decision (replay-verified, checksum re-checked) or an explicit W2NotEvaluated marker. Raw dicts are rejected."""
    if isinstance(w2, VerifiedW2Decision): w2.check(); w2_t = w2.trigger; w2_info = dict(validation_state=w2.validation_state, B_final=w2.B_final, observed_hash=w2.observed_hash, distance_kind=w2.distance_kind)
    elif isinstance(w2, W2NotEvaluated): w2_t = UNKNOWN; w2_info = dict(validation_state="not_evaluated", reason=w2.reason)
    else: raise InputContractError("position_decision requires a VerifiedW2Decision or an explicit W2NotEvaluated marker (raw dicts are not accepted)")
    ratio_t, info = event_ratio_trigger(P_k)
    st = position_state(w2_t, ratio_t, tech_fail=tech_fail, zero_hit_expansion=bool(info.get("expansion_due_to_zero_hits", False)))
    st.update(w2_trigger=w2_t, ratio_trigger=ratio_t, ratio_info=info, w2_input=w2_info); return st


def position_decision_unverified(w2_dict: dict, P_k: Dict[int, dict], tech_fail: bool = False) -> dict:
    """TEST-ONLY wrapper for the low-level three-valued OR: takes a raw trigger dict. Never used by the production entry; the returned dict is tagged."""
    ratio_t, info = event_ratio_trigger(P_k); w2_t = w2_dict["trigger"]
    st = position_state(w2_t, ratio_t, tech_fail=tech_fail, zero_hit_expansion=bool(info.get("expansion_due_to_zero_hits", False)))
    st.update(w2_trigger=w2_t, ratio_trigger=ratio_t, ratio_info=info, w2_input=dict(validation_state="UNVERIFIED_TEST_ONLY")); return st
