# -*- coding: utf-8 -*-
"""W2 null stopping rule (rules §10.1) and stability/selection validation (§10.3) with input-inventory contracts. The stop result binds the observed values
(hash) so that validation cannot be run on different observed inputs; the validator recomputes the indicator vector from the observed values it receives."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List
import hashlib, json, math
import numpy as np
from .errors import InputContractError
from .rules_config import RULES


def q99_higher(x): return float(np.quantile(np.asarray(x, float), 0.99, method=RULES.quantile_method))


def _obs_hash(observed): return hashlib.sha256(json.dumps({int(n): {int(s): float(v) for s, v in sorted(d.items())} for n, d in sorted(observed.items())}, sort_keys=True).encode()).hexdigest()


def _check_inventory(null_max: Dict[int, np.ndarray], observed: Dict[int, Dict[int, float]]):
    if set(int(k) for k in null_max) != set(RULES.n_subs): raise InputContractError(f"null n_sub inventory must be {RULES.n_subs}")
    if set(int(k) for k in observed) != set(RULES.n_subs): raise InputContractError("observed n_sub inventory mismatch")
    for n in RULES.n_subs:
        arr = np.asarray(null_max[n], float)
        if arr.ndim != 1 or len(arr) < RULES.B_levels[-1]: raise InputContractError(f"null sequence for n_sub={n} must have length >= B_max")
        if not np.all(np.isfinite(arr[:RULES.B_levels[-1]])) or np.any(arr[:RULES.B_levels[-1]] < 0): raise InputContractError("null values must be finite and non-negative")
        if set(int(s) for s in observed[n]) != set(RULES.seed_ids): raise InputContractError(f"observed seed inventory for n_sub={n} must be {RULES.seed_ids}")
        for s, v in observed[n].items():
            if not (isinstance(v, (int, float, np.floating, np.integer)) and math.isfinite(float(v)) and float(v) >= 0): raise InputContractError("observed W2 must be finite and non-negative")


STOP_STATES = ("stopped", "w2-unresolved")
STOP_REASONS = {"stopped": "indicator_unchanged_and_q99_rel_change_below_tol", "w2-unresolved": "B_max_reached_without_meeting_stop_condition"}


@dataclass
class StopResult:
    B_final: int; stop_reason: str; trace: List[dict]; null_prefix_id: str; state: str; observed_hash: str; observed: dict
    def as_dict(self):
        from .serialization import to_jsonable
        return to_jsonable(asdict(self))

    def validate(self):
        """Intake validation of a (possibly restored) stop result: state enum, trace = prefix of B_levels, finite non-negative q99, indicator inventory and values recomputed
        from the stored observed, relative changes recomputed from the trace, B_final/stop_reason consistent with the stop condition, observed hash consistent."""
        if self.state not in STOP_STATES: raise InputContractError(f"stop state must be one of {STOP_STATES}")
        obs = {int(k): {int(s): float(v) for s, v in d.items()} for k, d in self.observed.items()}
        if set(obs) != set(RULES.n_subs) or any(set(obs[n]) != set(RULES.seed_ids) for n in obs): raise InputContractError("stored observed inventory invalid")
        if _obs_hash(obs) != self.observed_hash: raise InputContractError("stored observed does not match observed_hash")
        Bs = [int(e["B"]) for e in self.trace]
        if not Bs or tuple(Bs) != RULES.B_levels[:len(Bs)]: raise InputContractError("trace must be a prefix of the registered B levels")
        prev = None
        for e in self.trace:
            q = {int(k): float(v) for k, v in e["q99"].items()}
            if set(q) != set(RULES.n_subs) or any(not (math.isfinite(v) and v >= 0) for v in q.values()): raise InputContractError("trace q99 must be finite and non-negative for every n_sub")
            ind = tuple(tuple(x) for x in e["indicator"])
            if ind != _indicator(obs, q): raise InputContractError("trace indicator does not match recomputation from observed/q99")
            if prev is not None:
                rels = [math.inf if prev[n] == 0 else abs(q[n] - prev[n]) / prev[n] for n in q]; rel = max(rels); st = "q99_prev_zero" if any(prev[n] == 0 for n in q) else "ok"
                if e.get("relative_change_state") != st or (st == "ok" and not math.isclose(float(e["relative_change"]), rel, rel_tol=1e-12, abs_tol=1e-15)): raise InputContractError("trace relative change does not match recomputation")
            elif e.get("relative_change") is not None: raise InputContractError("first trace level must have no relative change")
            prev = q
        last = self.trace[-1]
        if self.B_final != int(last["B"]): raise InputContractError("B_final must equal the last trace level")
        if self.stop_reason != STOP_REASONS.get(self.state): raise InputContractError("stop_reason does not match the registered reason for this state")
        def met_at(i):
            if i == 0: return False
            e, p = self.trace[i], self.trace[i - 1]
            return (tuple(tuple(x) for x in e["indicator"]) == tuple(tuple(x) for x in p["indicator"]) and e.get("relative_change_state") == "ok" and float(e["relative_change"]) < RULES.rel_tol)
        first = next((i for i in range(len(self.trace)) if met_at(i)), None)
        if self.state == "stopped" and first != len(self.trace) - 1: raise InputContractError("state 'stopped': the FIRST level meeting the stop condition must be the last trace row (no skipped stop, no early stop)")
        if self.state == "w2-unresolved" and (first is not None or self.B_final != RULES.B_levels[-1]): raise InputContractError("state 'w2-unresolved' requires B_max reached with the stop condition never met")
        return True


def _indicator(observed, q):
    return tuple((int(n), int(s), bool(float(observed[n][s]) > q[n])) for n in sorted(observed) for s in sorted(observed[n]))


def w2_stop(null_max: Dict[int, np.ndarray], observed: Dict[int, Dict[int, float]], null_prefix_id: str) -> StopResult:
    _check_inventory(null_max, observed); null_max = {int(k): np.asarray(v, float) for k, v in null_max.items()}; observed = {int(k): {int(s): float(v) for s, v in d.items()} for k, d in observed.items()}
    trace = []; prev = None
    for B in RULES.B_levels:
        q = {n: q99_higher(null_max[n][:B]) for n in null_max}; ind = _indicator(observed, q); rel = None; rel_state = "first_level"
        if prev is not None:
            rels = []; rel_state = "ok"
            for n in q:
                if prev["q99"][n] == 0: rel_state = "q99_prev_zero"; rels.append(math.inf)
                else: rels.append(abs(q[n] - prev["q99"][n]) / prev["q99"][n])
            rel = max(rels)
        entry = dict(B=B, q99=q, indicator=ind, relative_change=rel, relative_change_state=rel_state); trace.append(entry)
        if prev is not None and ind == prev["indicator"] and rel_state == "ok" and rel < RULES.rel_tol:
            return StopResult(B, "indicator_unchanged_and_q99_rel_change_below_tol", trace, null_prefix_id, "stopped", _obs_hash(observed), observed)
        prev = entry
    return StopResult(RULES.B_levels[-1], "B_max_reached_without_meeting_stop_condition", trace, null_prefix_id, "w2-unresolved", _obs_hash(observed), observed)


def seed_spread(observed_n: Dict[int, float]) -> float:
    v = [float(observed_n[s]) for s in sorted(observed_n)]
    if min(v) <= 0: return math.inf
    return max(v) / min(v) - 1.0


def w2_validate(stop: StopResult, seed_spread_max, obs_bounds: Dict[int, Dict[int, float]], delta_q99_bound: Dict[int, float], observed: Dict[int, Dict[int, float]]) -> dict:
    """Stability + selection-margin validation at B_final. Recomputes the indicator from `observed` (which must hash-match the stop input), recomputes the seed spread,
    and requires finite, non-negative bounds for every (n_sub, seed). Missing bounds are never treated as 0. Technical/contract problems raise InputContractError."""
    stop.validate()
    observed = {int(k): {int(s): float(v) for s, v in d.items()} for k, d in observed.items()}
    if set(observed) != set(RULES.n_subs) or any(set(observed[n]) != set(RULES.seed_ids) for n in observed): raise InputContractError("observed inventory mismatch")
    if _obs_hash(observed) != stop.observed_hash: raise InputContractError("observed values differ from those used at stop time (binding violation)")
    recomputed = max(seed_spread(observed[n]) for n in observed)
    if not (isinstance(seed_spread_max, (int, float, np.floating)) and (math.isinf(float(seed_spread_max)) or (math.isfinite(float(seed_spread_max)) and float(seed_spread_max) >= 0))): raise InputContractError("seed_spread_max must be non-negative (inf only when an observed value is 0)")
    if not (math.isinf(recomputed) and math.isinf(float(seed_spread_max))) and not math.isclose(recomputed, float(seed_spread_max), rel_tol=1e-9, abs_tol=1e-12): raise InputContractError("seed_spread_max does not match the spread recomputed from observed")
    for n in RULES.n_subs:
        if n not in obs_bounds or set(obs_bounds[n]) != set(RULES.seed_ids) or n not in delta_q99_bound: raise InputContractError("selection bound inventory incomplete (missing bounds are not treated as 0)")
        for s in RULES.seed_ids:
            v = obs_bounds[n][s]
            if not (isinstance(v, (int, float, np.floating)) and math.isfinite(float(v)) and float(v) >= 0): raise InputContractError("observed bound must be finite and non-negative")
        if not (math.isfinite(float(delta_q99_bound[n])) and float(delta_q99_bound[n]) >= 0): raise InputContractError("delta_q99_bound must be finite and non-negative")
    if stop.state != "stopped": return dict(state="w2-unresolved", reason=stop.stop_reason)
    last = stop.trace[-1]
    if _indicator(observed, last["q99"]) != tuple(tuple(x) for x in last["indicator"]): raise InputContractError("indicator recomputation mismatch")
    inds = [b for (_, _, b) in last["indicator"]]
    if len(set(inds)) != 1: return dict(state="w2-unresolved", reason="mixed above/below indicators at B_final")
    if math.isinf(recomputed): return dict(state="w2-unresolved", reason="seed_spread_undefined (an observed W2 is 0)")
    if recomputed > RULES.seed_spread_max: return dict(state="w2-unresolved", reason="seed spread above registered limit")
    for n in observed:
        for s in observed[n]:
            if not abs(observed[n][s] - last["q99"][n]) > float(obs_bounds[n][s]) + float(delta_q99_bound[n]): return dict(state="w2-unresolved", reason="selection decision margin not met at B_final")
    return dict(state="valid", trigger=bool(inds[0]), B_final=stop.B_final, observed_hash=stop.observed_hash)
