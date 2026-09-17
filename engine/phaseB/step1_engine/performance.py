# -*- coding: utf-8 -*-
"""Performance budget (engine spec B6; rules §6.6): measured UNIT costs in the current environment and registered-profile extrapolations. Every number is an estimate for planning
the Phase D/E budget; nothing here changes a registered quantity. The budget records the environment, so a Colab-official measurement replaces sandbox values (the
extrapolation formula is fixed and stated)."""
from __future__ import annotations
import time, json, platform
import numpy as np
from .rules_config import RULES

PROFILE = dict(n_families=4, evaluations_matched=30, evaluations_native=30, N0=RULES.N0, N_max=RULES.N_max, m=RULES.m, B=RULES.B, seeds=RULES.seeds, n_pseudo=2000, N_fit=200_000, B_KDE=2000, w2_families_sizes=9, w2_solves_per_family_size=6018, n_sub=(2000, 5000))


def measure_kde_unit(N=200_000, reps=3):
    from .density import kde_logpdf_weighted
    rng = np.random.default_rng(0); X = rng.standard_normal((N, 2)) * [40, 200] + [120, 600]; w = np.ones(N); pt = np.array([[39.67, 259.34]])
    t = time.perf_counter()
    for _ in range(reps): kde_logpdf_weighted(X, w, pt)
    return (time.perf_counter() - t) / reps


def measure_kde_batched_unit(N=200_000, B=100):
    """Seconds per replicate for the batched cluster-bootstrap log density at one point (N rows, m=100 clusters) — the accelerated path (opt-in; equivalence-tested)."""
    from .density import kde_logpdf_replicates
    rng = np.random.default_rng(0); m = 100; K = N // m; X = rng.standard_normal((N, 2)) * [40, 200] + [120, 600]; cid = np.repeat(np.arange(K), m)
    M = np.stack([np.bincount(rng.integers(0, K, K), minlength=K) for _ in range(B)]); t = time.perf_counter(); kde_logpdf_replicates(X, cid, np.array([[39.67, 259.34]]), M); return (time.perf_counter() - t) / B


def measure_ot_unit(n, reps=1):
    # Audit candidate: benchmark the registered success-checked wrapper. Missing
    # dependency is unmeasured; an unsuccessful solve is an error, not a timing.
    for name, value in (("n", n), ("reps", reps)):
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value <= 0:
            raise ValueError(f"{name} must be a positive non-bool integer")
    try: import ot
    except ImportError: return None
    from .positions import w2_exact
    rng = np.random.default_rng(1); a = rng.standard_normal((n, 2)); b = rng.standard_normal((n, 2)) + 0.1; t = time.perf_counter()
    for _ in range(reps): w2_exact(a, b)
    return (time.perf_counter() - t) / reps


def measure_e2_pass_unit(rows=400):
    """Seconds for ONE candidate-lattice pass over `rows` lattice rows (10001 columns) with 12 selected points, using the registered E2 distance and exclusion; extrapolated to 10001 rows."""
    from .observers12 import lattice_1d, dist_torus_halfturn
    from .stage12 import _exclusion
    ax = lattice_1d(0.0, 1.0, RULES.grid_resolution)
    if isinstance(rows, (bool, np.bool_)) or not isinstance(rows, (int, np.integer)) or not 1 <= rows <= len(ax):
        raise ValueError("rows must be a non-bool integer in the candidate-axis range")
    sel = np.random.default_rng(2).random((12, 2)); t = time.perf_counter()
    for i0 in range(0, rows, 200):
        a = ax[i0:min(i0 + 200, rows)]; g = np.meshgrid(a, ax, indexing="ij"); blk = _exclusion("E2", np.column_stack([g[0].ravel(), g[1].ravel()])); d = np.full(len(blk), np.inf)
        for p in sel: d = np.minimum(d, dist_torus_halfturn(blk, p))
        d.max()
    return (time.perf_counter() - t) * (len(ax) / rows)


def measure_scan_unit(mt_root: str, n=20_000):
    try:
        from .legacy_kernel import LegacyKernel
        k = LegacyKernel(mt_root); X = np.random.default_rng(3).standard_normal((n, 21)); t = time.perf_counter(); k.scan(X, "float64"); return (time.perf_counter() - t) / n * 1e6
    except Exception as ex: return None


def budget(mt_root: str = None, unit: dict = None) -> dict:
    """Lifecycle budget table (audit tranche 24 §5–6). Unit costs are measured here unless `unit` is supplied (e.g. a Colab-official measurement). Every row states its formula;
    single-target vs 2000-pseudo scopes, KDE point/sensitivity vs CI, shared vs recomputed W2 null, scan N0 / worst-case 4N0 are separated. Nothing is an upper bound guarantee."""
    u = unit or dict(kde=measure_kde_unit(), kde_batched=measure_kde_batched_unit(), ot2=measure_ot_unit(2000), ot5=measure_ot_unit(5000), e2=measure_e2_pass_unit(), scan=(None if mt_root is None else measure_scan_unit(mt_root)))
    P = PROFILE; evals_m = P["evaluations_matched"]; K = P["B_KDE"]; ot2, ot5 = u["ot2"], u["ot5"]; kde = u["kde"]; H = 3600.0
    def h(x): return None if x is None else x / H
    # KDE: matched configurations only (native D is not a core requirement); per configuration: 6 point/sensitivity calls (+6 mixture recomputation in the current implementation); CI: 2*B_KDE calls per configuration when required
    kde_point = kde * evals_m * 12; kde_ci_all = kde * evals_m * 2 * K; kde_ci_all_batched = (u.get("kde_batched") or kde) * evals_m * 2 * K
    # W2: per n_sub, null = 3000 solves (B_max=1000 x 3 pairs), observed per case = 9 solves (3 seeds x 3 pairs); 9 family-size cases
    w2 = None if (ot2 is None or ot5 is None) else dict(null_recomputed_9_cases_hours=h(9 * 3000 * (ot2 + ot5) + 9 * 9 * (ot2 + ot5)), shared_null_only_hours=h(3000 * (ot2 + ot5)), observed_9_cases_hours=h(81 * (ot2 + ot5)), shared_null_plus_observed_hours=h((3000 + 81) * (ot2 + ot5)), solves_shared_plus_observed=2 * (3000 + 81))
    rows = dict(
        single_target=dict(kde_point_and_sensitivity_hours=h(kde_point), kde_ci_all_matched_families_hours=h(kde_ci_all), kde_ci_all_matched_families_hours_batched=h(kde_ci_all_batched), note="CI only for strong/unsupported candidates under the registered short circuit; upper row assumes CI for all"),
        pseudo_2000_naive=dict(kde_point_and_sensitivity_hours=h(kde_point * P["n_pseudo"]), kde_ci_all_matched_families_hours=h(kde_ci_all * P["n_pseudo"]), kde_ci_all_matched_families_hours_batched=h(kde_ci_all_batched * P["n_pseudo"]), note="naive repetition; batched evaluation / KDE-fit reuse not credited until implemented"),
        w2_primary_exact_ot=w2, e2_generation=dict(full_lattice_pass_seconds_extrapolated=u["e2"], generation_hours_extrapolated=h(u["e2"] * 2 * 9), note="12-point unit on the first rows, extrapolated; 2 passes x 9 steps; verify re-runs not included"),
        scan=dict(N0_hours=h(None if u["scan"] is None else u["scan"] * evals_m * 2 * 2), worst_case_4N0_hours=h(None if u["scan"] is None else u["scan"] * evals_m * 2 * 2 * 4), note="60 evaluations x 2 roles (model/reference)"),
        not_included=["Q 5-seed bootstrap", "N adaptation logistics", "plan generation/save/restore", "control batteries", "bank generation (covariance intake, rotations)", "CRN diagnostic W2", "coupling bounds, SHA, I/O, re-verification", "12-position stage"])
    return dict(profile=P, unit_costs=dict(kde_logpdf_2e5_rows_seconds=kde, kde_batched_seconds_per_replicate=u.get("kde_batched"), emd2_n2000_seconds=ot2, emd2_n5000_seconds=ot5, e2_full_lattice_pass_seconds=u["e2"], scan_f64_seconds_per_1e6=u["scan"]), lifecycle=rows,
                formulas=dict(kde_point="kde_unit * 30 matched configs * 12 calls", kde_ci="kde_unit * 30 * 2 * B_KDE", w2_shared="(3000 + 81) * (t2000 + t5000)", w2_recomputed="9 * (3000 + 9) * (t2000 + t5000)", e2="pass_unit * 2 * 9", scan="scan_unit * 60 * 2 [* 4]"),
                environment=dict(python=platform.python_version(), numpy=np.__version__, platform=platform.platform()), note="planning estimates in THIS environment (single-thread); Colab-official measurements replace the unit costs; the formulas stay")
