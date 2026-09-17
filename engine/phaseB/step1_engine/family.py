# -*- coding: utf-8 -*-
"""Family aggregation (rules §8.1) with input validation. Mix probabilities with fixed prior weights per replicate, THEN take the ratio."""
from __future__ import annotations
import numpy as np
from .errors import InputContractError


def _weights(w, J):
    w = np.asarray(w, float)
    if w.ndim != 1 or len(w) != J or not np.all(np.isfinite(w)) or np.any(w < 0) or not np.isclose(w.sum(), 1.0, rtol=0, atol=1e-12): raise InputContractError("prior weights must be finite, non-negative, length J and sum to 1 (atol 1e-12)")
    return w


def _probs(P, name):
    P = np.asarray(P, float)
    if P.ndim != 2 or not np.all(np.isfinite(P)) or np.any(P < 0) or np.any(P > 1): raise InputContractError(f"{name} must be a finite 2-D array of probabilities in [0,1]")
    return P


def point_P(hits, N):
    h = np.asarray(hits); N = np.asarray(N)
    if not np.issubdtype(h.dtype, np.integer) or not np.issubdtype(N.dtype, np.integer): raise InputContractError("hits and N must be integer arrays")
    if h.shape != N.shape or np.any(N <= 0) or np.any(h < 0) or np.any(h > N): raise InputContractError("invalid hits/N")
    return h.astype(float) / N.astype(float)


def mixed_numden(P_model, P_ref, weights):
    P_model, P_ref = _probs(P_model, "P_model"), _probs(P_ref, "P_ref")
    if P_model.shape != P_ref.shape: raise InputContractError("shape mismatch")
    w = _weights(weights, P_model.shape[1]); return P_model @ w, P_ref @ w


def mixed_log_density(logf, weights):
    logf = np.asarray(logf, float)
    if logf.ndim != 2 or np.any(np.isnan(logf)) or np.any(logf == np.inf): raise InputContractError("log densities must be finite or -inf")
    w = _weights(weights, logf.shape[1]); lw = np.where(w > 0, np.log(np.where(w > 0, w, 1.0)), -np.inf)
    a = logf + lw; m = np.max(a, axis=-1, keepdims=True)
    with np.errstate(invalid="ignore"):
        out = (m + np.log(np.sum(np.exp(a - m), axis=-1, keepdims=True)))[..., 0]
    return np.where(np.isfinite(m[..., 0]), out, -np.inf)


def mechanism(PAB_model, PA_model, PAB_ref, PA_ref):
    arrs = [np.asarray(x, float) for x in (PAB_model, PA_model, PAB_ref, PA_ref)]
    for a in arrs:
        if not np.all(np.isfinite(a)) or np.any(a < 0) or np.any(a > 1): raise InputContractError("probabilities must be finite in [0,1]")
    if np.any(arrs[0] > arrs[1] + 1e-15) or np.any(arrs[2] > arrs[3] + 1e-15): raise InputContractError("P(A∩B) cannot exceed P(A)")
    PABm, PAm, PABr, PAr = arrs
    with np.errstate(divide="ignore", invalid="ignore"):
        Q_joint = PABm / PABr; Q_T1 = PAm / PAr
        condM = np.where(PAm > 0, PABm / np.where(PAm > 0, PAm, 1), np.nan); condI = np.where(PAr > 0, PABr / np.where(PAr > 0, PAr, 1), np.nan); Q_noncomp = condM / condI
    return dict(Q_joint=Q_joint, Q_T1=Q_T1, Q_noncomp=Q_noncomp, undefined_conditional=bool(np.any(~np.isfinite(condM)) or np.any(~np.isfinite(condI)) or np.any(condI == 0)))
