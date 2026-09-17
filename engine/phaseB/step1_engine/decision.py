# -*- coding: utf-8 -*-
"""Decision predicates (rules §1.4 table 1) with three-valued truth. Audit inputs must be registered audit tokens (use truth.precision_to_audit for PrecisionState);
numeric inputs are None (not available -> unknown) or finite floats; NaN is a technical fail, never unknown."""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Optional, List
import math
import numpy as np
from .truth import UNKNOWN, TECH, audit_truth, and3, norm_audit
from .errors import InputContractError
from .rules_config import RULES


@dataclass
class CoreInputs:
    audit_Q_matched: str; audit_Dpoint_matched: str; audit_DCI_matched: str; audit_Q_native: str
    L_Q_matched: Optional[float] = None; U_Q_matched: Optional[float] = None; logD_point_matched: Optional[float] = None
    L_logD_matched: Optional[float] = None; U_logD_matched: Optional[float] = None; L_Q_native: Optional[float] = None; U_Q_native: Optional[float] = None


@dataclass
class CoreDecision:
    support_truth: object; strong_truth: object; unsupported_truth: object; technical_status: str; display_label: str
    reason_codes: List[str] = field(default_factory=list); required_audits: dict = field(default_factory=dict); ci_computation_status: dict = field(default_factory=dict); direction_native: Optional[str] = None
    def as_dict(self):
        from .serialization import to_jsonable
        return to_jsonable(asdict(self))


def _num(v, name):
    if v is None: return None
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, float, np.integer, np.floating)): raise InputContractError(f"{name} must be a number or None")
    f = float(v)
    if not math.isfinite(f): return TECH                                       # NaN / ±inf are technical failures here (logD CI endpoints must be finite; Q endpoints used for a decision must be finite)
    return f


def validate_inputs(x: CoreInputs) -> dict:
    """Quantity-wise validation before any predicate: finite numbers, interval ordering L <= U, Q endpoints >= 0. Returns validated dict (value / None / TECH)."""
    v = {k: _num(getattr(x, k), k) for k in ("L_Q_matched", "U_Q_matched", "logD_point_matched", "L_logD_matched", "U_logD_matched", "L_Q_native", "U_Q_native")}
    for lo, hi in (("L_Q_matched", "U_Q_matched"), ("L_logD_matched", "U_logD_matched"), ("L_Q_native", "U_Q_native")):
        a, b = v[lo], v[hi]
        if isinstance(a, float) and isinstance(b, float) and a > b: v[lo] = v[hi] = TECH                    # reversed interval -> technical
        if (a is None) != (b is None) and TECH not in (a, b): v[lo] = v[hi] = TECH                          # half-missing interval -> technical
    for k in ("L_Q_matched", "U_Q_matched", "L_Q_native", "U_Q_native"):
        if isinstance(v[k], float) and v[k] < 0: v[k] = TECH                                                 # Q domain is [0, +inf]
    v["_invalid_intervals"] = []
    for lo, hi in (("L_Q_matched", "U_Q_matched"), ("L_logD_matched", "U_logD_matched"), ("L_Q_native", "U_Q_native")):
        if TECH in (v[lo], v[hi]):                                                                            # an interval is ONE quantity: invalidity of either endpoint invalidates the whole interval
            v[lo] = v[hi] = TECH; v["_invalid_intervals"].append(lo.replace("L_", "", 1))
    return v


def _cmp(v, op, thr):
    if v is None: return UNKNOWN
    if v == TECH: return TECH
    return bool(op(v, thr))


def direction(L, U):
    if L is None or U is None or L == TECH or U == TECH: return None
    if L > RULES.native_lower: return "positive"
    if U < 1.0: return "opposite"
    return "neutral"


def decide_core(x: CoreInputs) -> CoreDecision:
    ge, lt, gt, le = (lambda a, b: a >= b), (lambda a, b: a < b), (lambda a, b: a > b), (lambda a, b: a <= b)
    for nm in ("audit_Q_matched", "audit_Dpoint_matched", "audit_DCI_matched", "audit_Q_native"): norm_audit(getattr(x, nm))
    v = validate_inputs(x); LQ, UQ, Dp, LD, UD, LQn, UQn = (v[k] for k in ("L_Q_matched", "U_Q_matched", "logD_point_matched", "L_logD_matched", "U_logD_matched", "L_Q_native", "U_Q_native"))
    aQ, aD, aDCI, aQn = audit_truth(x.audit_Q_matched), audit_truth(x.audit_Dpoint_matched), audit_truth(x.audit_DCI_matched), audit_truth(x.audit_Q_native)
    support = and3(aQ, aD, _cmp(LQ, ge, RULES.Q_support), _cmp(Dp, gt, RULES.logD_point))
    strong = and3(support, aDCI, _cmp(LQ, ge, RULES.Q_strong), _cmp(LD, gt, RULES.logD_lower), aQn, _cmp(LQn, gt, RULES.native_lower))
    unsupported = and3(aQ, aD, aDCI, _cmp(UQ, lt, 1.0), _cmp(UD, le, 0.0))
    tech = TECH in (support, strong, unsupported)
    label = "strong" if strong is True else ("support" if support is True else ("unsupported" if unsupported is True else "inconclusive"))
    reasons = [f"invalid_interval:{q}" for q in v["_invalid_intervals"]]
    if isinstance(LQ, float) and LQ < RULES.Q_support: reasons.append("L_Q_below_support_threshold")
    if isinstance(Dp, float) and Dp <= RULES.logD_point: reasons.append("logD_point_nonpositive")
    if support is True and isinstance(LD, float) and LD <= RULES.logD_lower: reasons.append("logD_CI_crosses_zero_strong_only")
    if x.audit_DCI_matched == "not_computed_by_registered_short_circuit": reasons.append("logD_CI_not_computed_by_registered_short_circuit")
    for nm in ("audit_Q_matched", "audit_Dpoint_matched", "audit_DCI_matched", "audit_Q_native"):
        a = getattr(x, nm)
        if a in ("fail", "technical_fail", "unresolved"): reasons.append(f"{nm}:{a}")
    return CoreDecision(support, strong, unsupported, "technical_fail" if tech else "ok", label, reasons,
                        required_audits=dict(support=["audit_Q_matched", "audit_Dpoint_matched"], strong=["audit_Q_matched", "audit_Dpoint_matched", "audit_DCI_matched", "audit_Q_native"], unsupported=["audit_Q_matched", "audit_Dpoint_matched", "audit_DCI_matched"]),
                        ci_computation_status=dict(logD_CI=x.audit_DCI_matched), direction_native=direction(LQn, UQn))


def logD_ci_required(L_Q_matched, U_Q_matched) -> bool:
    return (L_Q_matched is not None and L_Q_matched >= RULES.Q_strong) or (U_Q_matched is not None and U_Q_matched < 1.0)
