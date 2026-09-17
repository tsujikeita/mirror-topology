# -*- coding: utf-8 -*-
"""Three-valued truth and audit-state normalisation (rules §1.4, §9.2). Python bool and NumPy bool are the same truth; strings are restricted to the
registered tokens; anything else (None, NaN, ints, unknown strings) is an input-contract error — never a silent False."""
from __future__ import annotations
import math
import numpy as np
from .errors import InputContractError

UNKNOWN, TECH = "unknown", "technical_fail"
AUDIT_STATES = ("pass", "fail", "unresolved", "technical_fail", "not_computed_by_registered_short_circuit")


def norm_truth(v):
    if isinstance(v, (bool, np.bool_)): return bool(v)
    if isinstance(v, str) and v in (UNKNOWN, TECH): return v
    raise InputContractError(f"invalid truth value {v!r} (allowed: bool, numpy bool, 'unknown', 'technical_fail')")


def norm_truths(seq):
    """Strict 1-D truth sequence (one entry per pseudo / per family). Multi-dimensional inputs are rejected (never flattened)."""
    if isinstance(seq, np.ndarray):
        if seq.ndim != 1: raise InputContractError(f"truth sequence must be 1-D (got shape {seq.shape}); aggregate families per row with any_family_truth first")
        seq = list(seq)
    elif isinstance(seq, (list, tuple)):
        if any(isinstance(v, (list, tuple, np.ndarray)) for v in seq): raise InputContractError("nested truth sequences are not allowed")
    else: raise InputContractError("truth sequence must be a list/tuple/1-D array")
    return [norm_truth(v) for v in seq]


def norm_audit(a) -> str:
    if isinstance(a, str) and a in AUDIT_STATES: return a
    raise InputContractError(f"invalid audit state {a!r}; use the adapter (precision_to_audit) for PrecisionState")


def audit_truth(a: str):
    a = norm_audit(a)
    return True if a == "pass" else (TECH if a == "technical_fail" else (UNKNOWN if a in ("unresolved", "not_computed_by_registered_short_circuit") else False))


def precision_to_audit(state: str) -> str:
    """Adapter PrecisionState.state -> audit state: pass->pass; precision-unresolved / cv_undefined -> unresolved; technical_fail -> technical_fail."""
    m = {"pass": "pass", "precision-unresolved": "unresolved", "cv_undefined": "unresolved", "technical_fail": "technical_fail"}
    if state not in m: raise InputContractError(f"unknown precision state {state!r}")
    return m[state]


def and3(*vals):
    """Three-valued AND: technical_fail > False > unknown > True."""
    vals = [norm_truth(v) for v in vals]
    if any(v == TECH for v in vals): return TECH
    if any(v is False for v in vals): return False
    if any(v == UNKNOWN for v in vals): return UNKNOWN
    return True


def is_finite_number(x) -> bool:
    return isinstance(x, (int, float, np.integer, np.floating)) and not isinstance(x, (bool, np.bool_)) and math.isfinite(float(x))
