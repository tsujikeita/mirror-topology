# -*- coding: utf-8 -*-
"""Density ratio logD (rules §7.2): 2-D Gaussian KDE with bw_method='scott' (SciPy semantics), log-density via logsumexp; cluster bootstrap with registered multiplicities;
bandwidth sensitivity battery (x0.7 / x1.4: sign unchanged AND |delta| < 0.1); fail-closed replicate handling with a single invalid mask (unique replicate count).
LITERAL (row expansion + scipy.stats.gaussian_kde) and FREQUENCY-WEIGHT (mu*, C*, factor from integer multiplicities) implementations must agree (rules R5).
All numeric inputs are validated at entry: no NaN/negative/non-integer multiplicity is ever 'dropped as a non-selected row'."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional, Dict
import math
import numpy as np
from scipy.stats import gaussian_kde
from scipy.special import logsumexp
from .errors import InputContractError
from .ci import CIResult
from .rules_config import RULES

D = 2
SENS_FACTORS = (0.7, 1.4); SENS_MAX_ABS_DELTA = 0.1; IMPLS = ("weighted", "literal")


def scott_factor(n: int) -> float: return float(n) ** (-1.0 / (D + 4))


def check_bank(X, cid, K: Optional[int] = None):
    X = np.asarray(X, float); cid = np.asarray(cid)
    if X.ndim != 2 or X.shape[1] != D or not np.all(np.isfinite(X)): raise InputContractError("fitting bank must be a finite (N,2) array")
    if cid.shape != (X.shape[0],) or not np.issubdtype(cid.dtype, np.integer): raise InputContractError("cluster ids must be an integer (N,) array")
    if np.any(cid < 0): raise InputContractError("cluster ids must be non-negative")
    Kc = int(cid.max()) + 1 if len(cid) else 0
    if K is not None and Kc > K: raise InputContractError("cluster id out of range for the plan")
    return X, cid


def check_multiplicities(M, K: int, name="plan multiplicities") -> np.ndarray:
    M = np.asarray(M)
    if M.ndim != 2 or M.shape[1] != K: raise InputContractError(f"{name} must be (B, K={K})")
    Mf = M.astype(float)
    if not np.all(np.isfinite(Mf)) or np.any(Mf < 0) or not np.all(Mf == np.round(Mf)): raise InputContractError(f"{name} must be finite non-negative integers")
    if not np.all(Mf.sum(axis=1) == K): raise InputContractError(f"{name}: every replicate must resample exactly K={K} clusters")
    return Mf.astype(np.int64)


def _check_scale(factor_scale) -> float:
    if not (isinstance(factor_scale, (int, float)) and math.isfinite(float(factor_scale)) and float(factor_scale) > 0): raise InputContractError("factor_scale must be a finite positive number")
    return float(factor_scale)


def _check_weights_rows(w) -> np.ndarray:
    w = np.asarray(w, float)
    if w.ndim != 1 or not np.all(np.isfinite(w)) or np.any(w < 0) or not np.all(w == np.round(w)): raise InputContractError("row multiplicities must be finite non-negative integers (no NaN/negative/fractional)")
    return w


def kde_logpdf_weighted(X: np.ndarray, mult_rows: np.ndarray, pts: np.ndarray, factor_scale: float = 1.0) -> np.ndarray:
    fs = _check_scale(factor_scale); X = np.asarray(X, float); w = _check_weights_rows(mult_rows)
    if w.shape != (X.shape[0],): raise InputContractError("row multiplicities must match the bank rows")
    keep = w > 0; X = X[keep]; w = w[keep]; Ns = w.sum()
    if Ns <= D: raise InputContractError("too few effective rows for a KDE")
    mu = (w[:, None] * X).sum(0) / Ns; Xc = X - mu; C = (Xc.T * w) @ Xc / (Ns - 1.0)
    f = scott_factor(int(round(Ns))) * fs; H = C * f * f
    try: Lc = np.linalg.cholesky(H)
    except np.linalg.LinAlgError: raise InputContractError("singular kernel covariance (KDE failure)")
    pts = np.atleast_2d(np.asarray(pts, float)); out = np.empty(len(pts))
    logdet = 2.0 * np.log(np.diag(Lc)).sum(); norm = -np.log(Ns) - 0.5 * (D * np.log(2 * np.pi) + logdet); logw = np.log(w)
    for i, p in enumerate(pts):
        z = np.linalg.solve(Lc, (p - X).T); out[i] = logsumexp(logw - 0.5 * np.sum(z * z, axis=0)) + norm
    return out


def kde_logpdf_literal(X: np.ndarray, mult_rows: np.ndarray, pts: np.ndarray, factor_scale: float = 1.0) -> np.ndarray:
    fs = _check_scale(factor_scale); w = _check_weights_rows(mult_rows); Xe = np.repeat(np.asarray(X, float), w.astype(int), axis=0)
    k = gaussian_kde(Xe.T, bw_method="scott") if fs == 1.0 else gaussian_kde(Xe.T, bw_method=lambda kde: scott_factor(kde.n) * fs)
    return k.logpdf(np.atleast_2d(np.asarray(pts, float)).T)


def sensitivity_audit(point: float, sens: Dict[str, float]) -> dict:
    """Registered bandwidth audit: sign unchanged AND |delta| < 0.1 for every factor. Non-finite values are a technical failure (not a bandwidth fail)."""
    vals = [point] + list(sens.values())
    if not all(isinstance(v, (int, float)) and math.isfinite(float(v)) for v in vals): return dict(state="technical_fail", pass_=False, reason="non-finite logD in the sensitivity battery")
    ok = all(np.sign(v) == np.sign(point) and abs(v - point) < SENS_MAX_ABS_DELTA for v in sens.values())     # point==0 with all sens==0 passes (sign(0)==sign(0))
    return dict(state="pass" if ok else "fail", pass_=bool(ok), reason=None if ok else "sign change or |delta| >= 0.1")


@dataclass
class LogDResult:
    point: float; ci: Optional[CIResult]; sensitivity: Dict[str, float]; sensitivity_audit: dict; sensitivity_pass: bool; n_replicates: int; n_failed: int; method: str
    replicate_values: Optional[np.ndarray] = None; invalid_mask: Optional[np.ndarray] = None; failure_reasons: Optional[dict] = None
    def as_dict(self):
        from .serialization import to_jsonable
        d = asdict(self); d["replicate_values"] = None if self.replicate_values is None else self.replicate_values.tolist(); d["invalid_mask"] = None if self.invalid_mask is None else self.invalid_mask.tolist(); return to_jsonable(d)


def check_threshold(t_eval) -> np.ndarray:
    """Single logD evaluation point: exactly one finite 2-D threshold (shape (2,)). A 1-coordinate input is never broadcast; multiple points are never truncated to the first."""
    t = np.asarray(t_eval, float)
    if t.shape != (2,) or not np.all(np.isfinite(t)): raise InputContractError("one finite 2-D threshold (shape (2,)) is required for a single logD evaluation")
    return t


def logD_at(XM, cidM, XI, cidI, t_eval, multM=None, multI=None, impl="weighted", factor_scale=1.0) -> float:
    if impl not in IMPLS: raise InputContractError("impl must be 'weighted' or 'literal'")
    t_eval = check_threshold(t_eval)
    XM, cidM = check_bank(XM, cidM); XI, cidI = check_bank(XI, cidI)
    wM = np.ones(len(XM)) if multM is None else _check_weights_rows(np.asarray(multM, float))[cidM]; wI = np.ones(len(XI)) if multI is None else _check_weights_rows(np.asarray(multI, float))[cidI]
    fn = kde_logpdf_weighted if impl == "weighted" else kde_logpdf_literal
    return float(fn(XM, wM, t_eval, factor_scale)[0] - fn(XI, wI, t_eval, factor_scale)[0])


def logD_with_ci(XM, cidM, XI, cidI, t_eval, plan_mult_M, plan_mult_I, impl="weighted", seed_id: int = 0) -> LogDResult:
    """plan_mult_*: (B, K) integer multiplicities (validated: finite, non-negative, integer, row sums K). Fail-closed: any invalid replicate -> CI technical_fail (unique count)."""
    if impl not in IMPLS: raise InputContractError("impl must be 'weighted' or 'literal'")
    t_eval = check_threshold(t_eval); XM, cidM = check_bank(XM, cidM); XI, cidI = check_bank(XI, cidI); KM = int(cidM.max()) + 1; KI = int(cidI.max()) + 1
    MM = check_multiplicities(plan_mult_M, KM, "model plan"); MI = check_multiplicities(plan_mult_I, KI, "reference plan"); B = MM.shape[0]
    if MI.shape[0] != B: raise InputContractError("model/reference plans must have the same number of replicates")
    point = logD_at(XM, cidM, XI, cidI, t_eval, impl=impl); sens = {f"x{fs}": logD_at(XM, cidM, XI, cidI, t_eval, impl=impl, factor_scale=fs) for fs in SENS_FACTORS}; aud = sensitivity_audit(point, sens)
    vals = np.full(B, np.nan); invalid = np.zeros(B, dtype=bool); reasons = dict(exception=0, non_finite=0)
    for b in range(B):
        try:
            v = logD_at(XM, cidM, XI, cidI, t_eval, MM[b], MI[b], impl=impl)
            if not math.isfinite(v): invalid[b] = True; reasons["non_finite"] += 1
            else: vals[b] = v
        except InputContractError: invalid[b] = True; reasons["exception"] += 1
    n_fail = int(invalid.sum())
    if n_fail > 0:
        ci = CIResult("logD", None, None, None, None, "none", "technical_fail", dict(finite=int(B - n_fail), technical_invalid=n_fail), RULES.alpha, B, "KDE replicate failure (fail-closed)", seed_id)
    else:
        ci = CIResult("logD", float(np.quantile(vals, RULES.alpha / 2, method="linear")), float(np.quantile(vals, 1 - RULES.alpha / 2, method="linear")), None, None, "linear_logD", "finite", dict(finite=B, technical_invalid=0), RULES.alpha, B, None, seed_id)
    return LogDResult(point, ci, sens, aud, aud["pass_"], B, n_fail, impl, vals, invalid, reasons)


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Batched cluster-bootstrap log-density (engine spec B6 / audit tranche 24 §6): identical estimator to the per-replicate frequency-weight formulation (same mu*, C*, factor,
# same log-sum-exp over rows with integer cluster multiplicities), computed for many replicates at once from row-level quadratic terms and cluster-level sums.
# Equivalence with the literal per-replicate path is a registered acceptance test (tolerance 1e-9 relative); nothing changes in the estimator.
def kde_logpdf_replicates(X: np.ndarray, cid: np.ndarray, pts: np.ndarray, M: np.ndarray,
                          factor_scale: float = 1.0, chunk: int = 128,
                          row_chunk: int = 8192) -> np.ndarray:
    """Audit candidate: the same frequency-weight KDE, with stable central moments.

    Return (B,P) log densities. Both replica and sample-row workspace are bounded.
    No jitter, clipping, replacement draw, or removal of failed replicates is used.
    This public array API raises on a failed replicate; the family caller can replay
    the *same* registered multiplicities with its reference path to localize failures.
    """
    def positive_int(name, value):
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value <= 0:
            raise InputContractError(f"{name} must be a positive non-bool integer")
        return int(value)
    chunk = positive_int("chunk", chunk); row_chunk = positive_int("row_chunk", row_chunk)
    raw_X = np.asarray(X); raw_pts = np.asarray(pts); raw_M = np.asarray(M)
    if raw_X.dtype.kind not in "iuf" or raw_pts.dtype.kind not in "iuf":
        raise InputContractError("KDE bank and points must contain real numeric coordinates")
    X, cid = check_bank(X, cid)
    if X.shape[0] <= D:
        raise InputContractError("too few bank rows for a KDE")
    K = int(cid.max()) + 1
    if not np.array_equal(np.unique(cid), np.arange(K)):
        raise InputContractError("KDE cluster labels must cover 0..K-1 without holes")
    if raw_M.dtype.kind not in "iuf" or raw_M.ndim != 2 or raw_M.shape[0] == 0:
        raise InputContractError("KDE multiplicities must be a non-empty numeric (B,K) array")
    M = check_multiplicities(M, K)
    if isinstance(factor_scale, (bool, np.bool_)):
        raise InputContractError("factor_scale must be a positive real number, not bool")
    fs = _check_scale(float(factor_scale)) if isinstance(factor_scale, (int, float, np.integer, np.floating)) else _check_scale(factor_scale)
    pts = np.asarray(pts, dtype=float)
    if pts.shape == (2,): pts = pts[None, :]
    if pts.ndim != 2 or pts.shape[1] != D or pts.shape[0] == 0 or not np.all(np.isfinite(pts)):
        raise InputContractError("KDE evaluation points must be finite (2,) or non-empty (P,2)")
    B, P = len(M), len(pts)
    out = np.full((B, P), np.nan)

    # An internal common translation improves accumulation, without changing the
    # raw-coordinate KDE, bandwidth rule, or density's units/Jacobian.
    origin = X[0].copy()
    Y = X - origin
    cnt = np.bincount(cid, minlength=K).astype(float)
    S = np.column_stack([np.bincount(cid, weights=Y[:, a], minlength=K) for a in range(D)])
    mean_k = S / cnt[:, None]
    residual = Y - mean_k[cid]
    # Within-cluster scatter is centered before squaring (no raw-moment subtraction).
    within = np.column_stack([
        np.bincount(cid, weights=residual[:, a] * residual[:, b], minlength=K)
        for a, b in ((0, 0), (0, 1), (1, 1))
    ])
    if not np.all(np.isfinite(within)) or not np.all(np.isfinite(mean_k)):
        raise InputContractError("non-finite cluster central moments (KDE failure)")
    for b0 in range(0, B, chunk):
        Mb = M[b0:b0 + chunk].astype(float)
        nb = len(Mb); row_counts = Mb * cnt[None, :]; Ns = row_counts.sum(axis=1)
        if np.any(Ns <= D) or not np.all(np.isfinite(Ns)):
            raise InputContractError("too few effective rows in a KDE replicate")
        mu = (row_counts @ mean_k) / Ns[:, None]
        # Law of total centered scatter: sum M_k [S_k + n_k (mean_k-mu)^2].
        d0 = mean_k[None, :, 0] - mu[:, None, 0]
        d1 = mean_k[None, :, 1] - mu[:, None, 1]
        ss = Mb @ within
        ss[:, 0] += np.sum(row_counts * d0 * d0, axis=1)
        ss[:, 1] += np.sum(row_counts * d0 * d1, axis=1)
        ss[:, 2] += np.sum(row_counts * d1 * d1, axis=1)
        f2 = (Ns ** (-1.0 / (D + 4)) * fs) ** 2
        H = np.empty((nb, 2, 2))
        H[:, 0, 0] = ss[:, 0] / (Ns - 1) * f2
        H[:, 0, 1] = H[:, 1, 0] = ss[:, 1] / (Ns - 1) * f2
        H[:, 1, 1] = ss[:, 2] / (Ns - 1) * f2
        if not np.all(np.isfinite(H)):
            raise InputContractError("non-finite kernel covariance in a replicate (KDE failure)")
        try:
            L = np.linalg.cholesky(H)
        except np.linalg.LinAlgError as ex:
            raise InputContractError("singular kernel covariance in a replicate (KDE failure)") from ex
        norm = -np.log(Ns) - np.log(2 * np.pi) - np.log(L[:, 0, 0]) - np.log(L[:, 1, 1])
        # Mean/covariance is computed once per replicate chunk and reused for P points.
        for p_idx, t in enumerate(pts):
            accum = np.full(nb, -np.inf)
            for r0 in range(0, len(X), row_chunk):
                sl = slice(r0, min(r0 + row_chunk, len(X)))
                U = t - X[sl]
                z0 = U[:, 0, None] / L[None, :, 0, 0]
                z1 = (U[:, 1, None] - z0 * L[None, :, 1, 0]) / L[None, :, 1, 1]
                np.square(z0, out=z0); np.square(z1, out=z1)
                z0 += z1; del z1
                z0 *= -0.5
                weights = Mb[:, cid[sl]].T
                logw = np.full(weights.shape, -np.inf)
                np.log(weights, out=logw, where=weights > 0)
                z0 += logw
                # Zero-weight rows are -inf BEFORE stabilization. They cannot set
                # the maximum and cause a spurious underflow of selected rows.
                accum = np.logaddexp(accum, logsumexp(z0, axis=0))
            vals = accum + norm
            if not np.all(np.isfinite(vals)):
                raise InputContractError("non-finite KDE replicate log density")
            out[b0:b0 + nb, p_idx] = vals
    return out
