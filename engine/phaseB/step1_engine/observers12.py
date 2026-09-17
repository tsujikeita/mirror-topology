# -*- coding: utf-8 -*-
"""Deterministic 12-position generator (rules §10.4): closed lattice candidates (box endpoints must lie on the grid), validated anchors (unique, finite, in box,
pairwise >= min_sep), greedy maximin with TIE_TOL-lexicographic tie-break, fail-fast, and a post-check of the final set."""
from __future__ import annotations
import numpy as np
from .errors import InputContractError
from .rules_config import RULES

TIE_TOL = RULES.tie_tol


def lattice_1d(lo: float, hi: float, res: float = None) -> np.ndarray:
    res = RULES.grid_resolution if res is None else float(res)
    if not (np.isfinite(lo) and np.isfinite(hi) and np.isfinite(res) and res > 0 and lo <= hi): raise InputContractError("lattice: lo/hi must be finite with lo <= hi and res > 0")
    i0, i1 = lo / res, hi / res
    if not (np.isclose(i0, round(i0), rtol=0, atol=1e-9) and np.isclose(i1, round(i1), rtol=0, atol=1e-9)): raise InputContractError("box endpoints must lie on the grid")
    return np.arange(int(round(i0)), int(round(i1)) + 1) * res


def _check_anchors(anchors, cand, min_sep, dist):
    A = np.asarray(anchors, float)
    if A.ndim != 2 or not np.all(np.isfinite(A)): raise InputContractError("anchors must be a finite 2-D array")
    if len({tuple(a) for a in A}) != len(A): raise InputContractError("anchors must be unique")
    lo, hi = cand.min(axis=0), cand.max(axis=0)
    if np.any(A < lo - 1e-12) or np.any(A > hi + 1e-12): raise InputContractError("anchor outside the candidate box")
    for i in range(len(A)):
        for j in range(i + 1, len(A)):
            if dist(A[j:j + 1], A[i])[0] < min_sep: raise InputContractError("anchors violate min_sep")
    return A


def greedy_maximin(candidates, anchors, n_add: int, min_sep: float, dist):
    cand = np.asarray(candidates, float)
    if cand.ndim != 2 or not np.all(np.isfinite(cand)): raise InputContractError("candidates must be a finite 2-D array")
    A = _check_anchors(anchors, cand, min_sep, dist); sel = [a for a in A]; best = np.full(len(cand), np.inf)
    for a in sel: best = np.minimum(best, dist(cand, a))
    for step in range(n_add):
        bmax = best.max()
        if not np.isfinite(bmax) or bmax < min_sep: raise RuntimeError(f"step {step + 1}: no candidate at distance >= min_sep ({bmax:.4g} < {min_sep}) — fail-fast")
        ties = np.flatnonzero(best >= bmax - TIE_TOL); pick = min(ties, key=lambda i: tuple(cand[i]))
        sel.append(cand[pick]); best = np.minimum(best, dist(cand, cand[pick]))
    out = np.array(sel)
    if len(out) != len(A) + n_add or len({tuple(p) for p in out}) != len(out): raise RuntimeError("post-check: anchor loss or duplicate point")
    if min_pairwise(out, dist) < min_sep: raise RuntimeError("post-check: min_sep violated")
    return out


def min_pairwise(points, dist) -> float:
    pts = np.asarray(points, float); m = np.inf
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)): m = min(m, float(dist(pts[j:j + 1], pts[i])[0]))
    return m


def dist_euclid(P, x): return np.linalg.norm(np.asarray(P, float) - np.asarray(x, float), axis=-1)


def dist_torus_halfturn(P, x):
    P = np.asarray(P, float); x = np.asarray(x, float); best = np.full(len(P), np.inf)
    for sgn in (1.0, -1.0):
        d = (P - sgn * x) % 1.0; d = np.minimum(d, 1.0 - d); best = np.minimum(best, np.linalg.norm(d, axis=-1))
    return best
