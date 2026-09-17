# -*- coding: utf-8 -*-
"""Boundary-aware bootstrap CI helper (rules §7.1, table 1b). Value domain is separate from decision state: this module never decides labels.
Log arithmetic uses log(num) - log(den) (no premature ratio; no replacement of underflowed ratios). Counts are recomputed after final classification and sum to B."""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict
import math
import numpy as np
from .errors import InputContractError
from .rules_config import RULES

REPLICATE_STATES = ("finite_positive", "zero", "inf", "undefined", "technical_invalid")


@dataclass
class CIResult:
    value_domain: str
    log_lower: Optional[float]; log_upper: Optional[float]; lower: Optional[float]; upper: Optional[float]
    effective_method: str; math_state: str
    counts: Dict[str, int] = field(default_factory=dict); alpha: float = RULES.alpha; B: int = 0; reason: Optional[str] = None; seed_id: Optional[int] = None

    def as_dict(self):
        from .serialization import to_jsonable
        return to_jsonable(asdict(self))


def _check_inputs(num, den, invalid, mode):
    if mode not in ("Q", "P"): raise InputContractError("mode must be 'Q' or 'P'")
    num = np.asarray(num, dtype=float); den = np.asarray(den, dtype=float)
    if num.ndim != 1 or den.ndim != 1 or num.shape != den.shape: raise InputContractError("num/den must be 1-D arrays of equal length")
    inv = np.zeros(num.shape, dtype=bool) if invalid is None else np.asarray(invalid, dtype=bool)
    if inv.shape != num.shape: raise InputContractError("invalid mask shape mismatch")
    return num, den, inv


def classify_replicates(num, den, invalid, mode: str = "Q") -> np.ndarray:
    st = np.empty(num.shape, dtype=object)
    bad = invalid | ~np.isfinite(num) | ~np.isfinite(den) | (num < 0) | (den < 0)
    if mode == "P": bad = bad | (num > den)                                      # includes den==0 & num>0: probability > 1 is not a valid boundary value
    st[bad] = "technical_invalid"; ok = ~bad
    st[ok & (den > 0) & (num > 0)] = "finite_positive"; st[ok & (den > 0) & (num == 0)] = "zero"; st[ok & (den == 0) & (num > 0)] = "inf"; st[ok & (den == 0) & (num == 0)] = "undefined"
    return st


def ci_from_replicates(num, den, *, invalid=None, alpha: float = None, mode: str = "Q", seed_id: Optional[int] = None) -> CIResult:
    """Rules §7.1 (a)(b)(c) — see table 1b. Any technical-invalid replicate -> technical_fail (no endpoints, no imputation)."""
    alpha = RULES.alpha if alpha is None else float(alpha)
    num, den, inv = _check_inputs(num, den, invalid, mode); B = int(num.size)
    if B == 0: return CIResult(mode, None, None, None, None, "none", "technical_fail", {s: 0 for s in REPLICATE_STATES}, alpha, 0, "empty", seed_id)
    st = classify_replicates(num, den, inv, mode); counts = {s: int(np.sum(st == s)) for s in REPLICATE_STATES}
    assert sum(counts.values()) == B
    if counts["technical_invalid"] > 0:
        return CIResult(mode, None, None, None, None, "none", "technical_fail", counts, alpha, B, "technical-invalid replicate(s) present; no imputation of technical failures", seed_id)
    logv = np.full(B, np.nan)
    fp = st == "finite_positive"; logv[fp] = np.log(num[fp]) - np.log(den[fp])   # exact log arithmetic (no ratio underflow)
    logv[st == "zero"] = -np.inf; logv[st == "inf"] = np.inf
    lo_q, hi_q = alpha / 2, 1 - alpha / 2
    if counts["undefined"] == 0 and counts["zero"] == 0 and counts["inf"] == 0:
        L, U = float(np.quantile(logv, lo_q, method="linear")), float(np.quantile(logv, hi_q, method="linear")); method, state = "linear_logQ", "finite"
    elif counts["undefined"] == 0:
        srt = np.sort(logv); L = float(srt[max(int(math.ceil(lo_q * B)) - 1, 0)]); U = float(srt[int(math.ceil(hi_q * B)) - 1]); method, state = "inverted_cdf", "boundary"
    else:
        known = logv[st != "undefined"]; u = counts["undefined"]
        y_minus = np.sort(np.concatenate([known, np.full(u, -np.inf)])); y_plus = np.sort(np.concatenate([known, np.full(u, np.inf)]))
        L = float(y_minus[int(math.floor((B - 1) * lo_q))]); U = float(y_plus[int(math.ceil((B - 1) * hi_q))]); method, state = "lower_higher_envelope", "undefined_completed"
    if mode == "P": U = min(U, 0.0)
    if not (L <= U): raise InputContractError("CI endpoint ordering violated (internal)")
    with np.errstate(over="ignore"):
        return CIResult(mode, L, U, float(np.exp(L)), float(np.exp(U)), method, state, counts, alpha, B, None, seed_id)   # exp overflow -> +inf is the intended extended value
