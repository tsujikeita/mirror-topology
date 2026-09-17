# -*- coding: utf-8 -*-
"""Precision gate (rules §7.3) as a state. Input contract: exactly the registered seed inventory (seed_ids 0..seeds-1, seed 0 formal), all in value domain 'Q'
with the same alpha/B; any seed technical_fail -> technical_fail; non-finite endpoints / Q<=0 / undefined -> precision-unresolved; zero mean log width -> cv_undefined."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional, Sequence
import math
import numpy as np
from .ci import CIResult
from .errors import InputContractError
from .rules_config import RULES


@dataclass
class PrecisionState:
    state: str; rel_halfwidth: Optional[float]; width_cv_logQ: Optional[float]; positive_clusters_model: int; positive_clusters_ref: int; reasons: list
    def as_dict(self):
        from .serialization import to_jsonable
        return to_jsonable(asdict(self))


def _int_count(x, name):
    if isinstance(x, (bool, np.bool_)) or not isinstance(x, (int, np.integer)) or int(x) < 0: raise InputContractError(f"{name} must be a non-negative integer")
    return int(x)


def precision_state(ci_seed0: CIResult, ci_seeds: Sequence[CIResult], Q_point: Optional[float], pos_clusters_model, pos_clusters_ref) -> PrecisionState:
    pm, pr = _int_count(pos_clusters_model, "positive_clusters_model"), _int_count(pos_clusters_ref, "positive_clusters_ref")
    seeds = list(ci_seeds)
    if len(seeds) != RULES.seeds: raise InputContractError(f"exactly {RULES.seeds} seed CIs required (got {len(seeds)})")
    ids = [c.seed_id for c in seeds]
    if any(i is not None for i in ids) and ids != list(range(RULES.seeds)): raise InputContractError(f"seed inventory must be {list(range(RULES.seeds))} in order (got {ids}); positional lists must leave seed_id unset on all entries")
    if ci_seed0 is not seeds[RULES.formal_seed] and ci_seed0.as_dict() != seeds[RULES.formal_seed].as_dict(): raise InputContractError("ci_seed0 must be the formal seed-0 result")
    for c in seeds:
        if c.value_domain != "Q": raise InputContractError("precision gate applies to Q-domain CIs only")
    if any(c.math_state == "technical_fail" for c in seeds):                      # technical failure in ANY seed dominates every other check
        return PrecisionState("technical_fail", None, None, pm, pr, ["technical_fail_in_seed_inventory"])
    for c in seeds:
        if c.alpha != seeds[0].alpha or c.B != seeds[0].B: raise InputContractError("seed CIs must share alpha and B")
    reasons = []
    if pm < RULES.positive_clusters_min: reasons.append("positive_clusters_model<min")
    if pr < RULES.positive_clusters_min: reasons.append("positive_clusters_ref<min")
    L, U = ci_seed0.lower, ci_seed0.upper
    qp_ok = Q_point is not None and isinstance(Q_point, (int, float, np.floating, np.integer)) and math.isfinite(float(Q_point)) and float(Q_point) > 0
    if not qp_ok: reasons.append("point_estimate_not_finite_positive")
    if L is None or U is None or not (math.isfinite(L) and math.isfinite(U)) or not (L <= U): reasons.append("non_finite_or_disordered_endpoint")
    rel = None
    if qp_ok and L is not None and U is not None and math.isfinite(L) and math.isfinite(U):
        rel = (U - L) / (2.0 * float(Q_point))
        if rel > RULES.rel_halfwidth_max: reasons.append("rel_halfwidth>max")
    widths = [c.log_upper - c.log_lower for c in seeds]
    if not all(math.isfinite(w) for w in widths):
        reasons.append("non_finite_width_in_seeds"); cv = None
    else:
        w = np.asarray(widths, float); m = float(w.mean())
        if m == 0: return PrecisionState("cv_undefined", rel, None, pm, pr, reasons + ["mean_log_width_zero"])
        cv = float(w.std(ddof=0) / m)
        if cv >= RULES.width_cv_max: reasons.append("width_cv>=max")
    return PrecisionState("pass" if not reasons else "precision-unresolved", rel, cv, pm, pr, reasons)
