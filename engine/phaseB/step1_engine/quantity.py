# -*- coding: utf-8 -*-
"""Quantity adapter (rules §7.1/§7.3 -> §1.4): converts a CIResult (+ PrecisionState) into decision-usable values and an audit token WITHOUT losing the CI record.
Mathematical boundary / precision-unresolved  -> audit 'unresolved', numeric endpoints withheld (None) so that no definite False is derived from an unresolved quantity.
Technical failure                              -> audit 'technical_fail'.  Precision pass -> audit 'pass' and finite endpoints (guaranteed by the precision gate)."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional
import math
from .ci import CIResult
from .precision import PrecisionState
from .truth import precision_to_audit
from .errors import InputContractError


@dataclass
class QuantityState:
    name: str; audit: str; lower: Optional[float]; upper: Optional[float]; point: Optional[float]
    ci_math_state: str; ci_method: str; precision_state: Optional[str]; reasons: list

    def as_dict(self):
        from .serialization import to_jsonable
        return to_jsonable(asdict(self))


def ratio_quantity(name: str, ci: CIResult, prec: Optional[PrecisionState], point: Optional[float]) -> QuantityState:
    """Q-type quantity: precision gate decides usability. Endpoints are exposed only when precision passes (then finite by construction)."""
    if ci.value_domain != "Q": raise InputContractError("ratio_quantity expects a Q-domain CI")
    if ci.math_state == "technical_fail": return QuantityState(name, "technical_fail", None, None, None, ci.math_state, ci.effective_method, None, [ci.reason or "technical_fail"])
    if prec is None: raise InputContractError("PrecisionState required for a Q-type quantity")
    aud = precision_to_audit(prec.state)
    if aud != "pass": return QuantityState(name, aud, None, None, None, ci.math_state, ci.effective_method, prec.state, list(prec.reasons))
    if not (math.isfinite(ci.lower) and math.isfinite(ci.upper) and point is not None and math.isfinite(point) and point > 0): raise InputContractError("precision pass with non-finite endpoints/point (internal inconsistency)")
    return QuantityState(name, "pass", ci.lower, ci.upper, float(point), ci.math_state, ci.effective_method, prec.state, [])


def logD_quantity(name: str, point: Optional[float], ci: Optional[CIResult]) -> QuantityState:
    """logD-type quantity (rules §7.2, fail-closed; not configurable): CI (when present) must be a logD-domain CI with every replicate valid.
    Precedence: an existing technical failure of the CI is never overwritten by 'not computed'; then non-finite point -> technical; then short circuit; then pass."""
    if ci is not None:
        if ci.value_domain != "logD": raise InputContractError("logD_quantity expects a logD-domain CI")
        if ci.math_state == "technical_fail" or ci.counts.get("technical_invalid", 0) > 0:
            return QuantityState(name, "technical_fail", None, None, (float(point) if isinstance(point, (int, float)) and math.isfinite(float(point)) else None), ci.math_state, ci.effective_method, None, [ci.reason or "logD CI technical failure (fail-closed)"])
    if point is None: return QuantityState(name, "not_computed_by_registered_short_circuit", None, None, None, "none" if ci is None else ci.math_state, "none" if ci is None else ci.effective_method, None, ["logD point not computed"])
    if not (isinstance(point, (int, float)) and math.isfinite(float(point))): return QuantityState(name, "technical_fail", None, None, None, "none" if ci is None else ci.math_state, "none", None, ["logD point non-finite"])
    if ci is None: return QuantityState(name, "not_computed_by_registered_short_circuit", None, None, float(point), "none", "none", None, ["logD CI not computed (registered short circuit)"])
    if not (math.isfinite(ci.log_lower) and math.isfinite(ci.log_upper)): return QuantityState(name, "technical_fail", None, None, float(point), ci.math_state, ci.effective_method, None, ["logD CI endpoints must be finite"])
    return QuantityState(name, "pass", ci.log_lower, ci.log_upper, float(point), ci.math_state, ci.effective_method, None, [])
