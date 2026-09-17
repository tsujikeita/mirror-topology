# -*- coding: utf-8 -*-
"""Global false-support calibration aggregation (rules §9.2, table 5). Truth values are normalised (Python/NumPy bool, 'unknown', 'technical_fail'; anything else
is rejected). Technical failures invalidate the calibration (no value). 'usable' is decided after aggregation and is never fed back into the core evaluation."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Sequence, Optional
import math
from .truth import UNKNOWN, TECH, norm_truths
from .errors import InputContractError
from .rules_config import RULES


def any_family_truth(truths: Sequence[object]):
    t = norm_truths(truths)
    if not t: raise InputContractError("empty family truth list")
    if any(v == TECH for v in t): return TECH
    if any(v is True for v in t): return True
    if any(v == UNKNOWN for v in t): return UNKNOWN
    return False


def wilson_upper(k: int, n: int, z: float = 1.959964) -> float:
    p = k / n; c = (p + z * z / (2 * n)) / (1 + z * z / n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n); return c + h


@dataclass
class CalibrationSummary:
    n: int; c_true: int; u_unknown: int; technical_fail: int
    rate_lower: Optional[float]; rate_upper: Optional[float]; wilson_upper_c_plus_u: Optional[float]; threshold: float; usable: object; status: str; reason: Optional[str] = None
    w2_context: Optional[dict] = None  # full structured reference; not a claim of full family/12-position calibration
    def as_dict(self):
        from .serialization import to_jsonable
        return to_jsonable(asdict(self))


def calibrate(per_pseudo_truth: Sequence[object], threshold: float, expected_n: Optional[int] = None) -> CalibrationSummary:
    t = norm_truths(per_pseudo_truth); n = len(t)
    if threshold not in (RULES.usable_support, RULES.usable_strong): raise InputContractError("threshold must be the registered support or strong usable threshold")
    if expected_n is not None and n != expected_n: raise InputContractError(f"pseudo inventory {n} != expected {expected_n}")
    c = sum(1 for v in t if v is True); u = sum(1 for v in t if v == UNKNOWN); tf = sum(1 for v in t if v == TECH)
    if n == 0 or tf > 0: return CalibrationSummary(n, c, u, tf, None, None, None, threshold, TECH, "technical_fail", "empty" if n == 0 else "technical failures present")
    wu = wilson_upper(c + u, n)
    return CalibrationSummary(n, c, u, 0, c / n, (c + u) / n, wu, threshold, bool(wu <= threshold), "ok")
