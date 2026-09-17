# -*- coding: utf-8 -*-
"""Block-wise (streamed) greedy maximin for large lattices (E2: 10001 x 10001 candidates): identical selection rule as observers12.greedy_maximin (max of the minimum distance to the
selected set; ties within TIE_TOL resolved lexicographically; fail-fast on min_sep) but the candidate set is regenerated row-block by row-block at every step, so no full
candidate array or distance vector is materialised. Equivalence with the in-memory generator is tested on a small 2-D lattice."""
from __future__ import annotations
import numpy as np
from .errors import InputContractError
from .observers12 import TIE_TOL, lattice_1d, dist_torus_halfturn, dist_euclid, min_pairwise


def _blocks_2d(ax0: np.ndarray, ax1: np.ndarray, rows_per_block: int):
    for i0 in range(0, len(ax0), rows_per_block):
        a = ax0[i0:i0 + rows_per_block]; g = np.meshgrid(a, ax1, indexing="ij"); yield np.column_stack([g[0].ravel(), g[1].ravel()])


def greedy_maximin_streamed(ax0: np.ndarray, ax1: np.ndarray, anchors: np.ndarray, n_add: int, min_sep: float, dist, exclusion=None, rows_per_block: int = 200):
    """Audit candidate: two passes per step, both using the same global maximum.
    This preserves TIE_TOL semantics without retaining a full distance vector.
    Formal E2 runtime is not measured by the small-grid contract tests.
    """
    axes = [np.asarray(ax, float) for ax in (ax0, ax1)]
    if any(ax.ndim != 1 or not ax.size or not np.all(np.isfinite(ax)) or len(np.unique(ax)) != len(ax) for ax in axes):
        raise InputContractError("axes must be nonempty finite unique 1-D arrays")
    for name, val, lower in (("n_add", n_add, 0), ("rows_per_block", rows_per_block, 1)):
        if isinstance(val, (bool, np.bool_)) or not isinstance(val, (int, np.integer)) or val < lower:
            raise InputContractError(f"{name} must be an integer >= {lower}")
    if not np.isfinite(min_sep) or min_sep < 0:
        raise InputContractError("min_sep must be finite and nonnegative")
    A = np.asarray(anchors, float)
    if A.ndim != 2 or A.shape[1] != 2 or len(A) == 0 or not np.all(np.isfinite(A)):
        raise InputContractError("finite nonempty (n,2) anchors required")
    if len({tuple(a) for a in A}) != len(A):
        raise InputContractError("anchors must be unique")
    lo = np.array([a.min() for a in axes]); hi = np.array([a.max() for a in axes])
    if np.any(A < lo - 1e-12) or np.any(A > hi + 1e-12):
        raise InputContractError("anchor outside candidate box")
    def checked_distance(P, x):
        val = np.asarray(dist(P, x), float)
        if val.shape != (len(P),) or not np.all(np.isfinite(val)) or np.any(val < 0):
            raise InputContractError("distance must be finite nonnegative with one value per candidate")
        return val
    for i in range(len(A)):
        for j in range(i + 1, len(A)):
            if checked_distance(A[j:j+1], A[i])[0] < min_sep:
                raise InputContractError("anchors violate min_sep")
    sel = [a.copy() for a in A]
    def blocks_with_scores():
        for blk in _blocks_2d(*axes, int(rows_per_block)):
            if exclusion is not None: blk = np.asarray(exclusion(blk), float)
            if blk.ndim != 2 or blk.shape[1] != 2 or not np.all(np.isfinite(blk)):
                raise InputContractError("excluded candidate block shape/finiteness")
            if not len(blk): continue
            d = np.full(len(blk), np.inf)
            for point in sel: d = np.minimum(d, checked_distance(blk, point))
            yield blk, d
    for _ in range(int(n_add)):
        global_max = -np.inf
        for blk, d in blocks_with_scores(): global_max = max(global_max, float(d.max()))
        if not np.isfinite(global_max) or global_max < min_sep:
            raise RuntimeError("no candidate at registered separation")
        # Second pass: never discard a candidate on the basis of a block-local max.
        pick = None
        for blk, d in blocks_with_scores():
            ties = np.flatnonzero(d >= global_max - TIE_TOL)
            if len(ties):
                local = min(tuple(blk[i]) for i in ties)
                if pick is None or local < pick: pick = local
        if pick is None: raise RuntimeError("no candidate at global near-maximum")
        sel.append(np.asarray(pick, float))
    out = np.asarray(sel)
    if len(out) != len(A)+n_add or len({tuple(p) for p in out}) != len(out) or min_pairwise(out, dist) < min_sep:
        raise RuntimeError("post-check failed")
    return out
