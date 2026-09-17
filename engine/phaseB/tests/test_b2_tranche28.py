# -*- coding: utf-8 -*-
"""B-2 tranche 28: adopted tranche-27 audit fixes; batched KDE bootstrap (fit reuse) — equivalence with the per-replicate reference path on the family logD CI and on raw log densities."""
import os, sys, copy, time
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
import step1_engine.orchestrator as o
from step1_engine.density import kde_logpdf_replicates, kde_logpdf_weighted, kde_logpdf_literal
from step1_engine.errors import InputContractError
from test_b2_tranche14 import TwelveFixture

def test_batched_replicates_equal_literal_and_weighted():
    rng = np.random.default_rng(3); K, m = 300, 10; X = rng.standard_normal((K * m, 2)) * [40, 200] + [120, 600]; cid = np.repeat(np.arange(K), m)
    M = np.stack([np.bincount(rng.integers(0, K, K), minlength=K) for _ in range(40)]); pts = np.array([[39.67, 259.34], [80.0, 400.0], [120.0, 600.0]])
    a = kde_logpdf_replicates(X, cid, pts, M)
    for r in range(40):
        w = M[r][cid]; b = kde_logpdf_literal(X, w, pts); c = kde_logpdf_weighted(X, w.astype(float), pts)
        assert np.allclose(a[r], b, rtol=1e-9, atol=1e-9) and np.allclose(a[r], c, rtol=1e-9, atol=1e-9)
    assert np.allclose(kde_logpdf_replicates(X, cid, pts, M, factor_scale=0.7)[5], kde_logpdf_literal(X, M[5][cid], pts, 0.7), rtol=1e-9)
    bad = M.copy(); bad[3] = 0; bad[3, 0] = K
    Xs = X.copy(); Xs[cid == 0] = Xs[cid == 0][0]
    with pytest.raises(InputContractError): kde_logpdf_replicates(Xs, cid, pts, bad)                                    # singular replicate is a KDE failure, not a number
    with pytest.raises(InputContractError): kde_logpdf_replicates(X, cid, pts, M.astype(float) + 0.5)

def test_family_logD_ci_batched_equals_per_replicate_reference():
    fx = TwelveFixture(sizes=('L1.00',), K=120, Kf=300, B=40); fm, fn = fx.inputs['L1.00']; w = np.array([c.weight for c in fm.configs]); t = np.array([100.0, 550.0])
    o.KDE_CI_BACKEND = 'per_replicate'; ref = o._family_logD(fm, t, w, True)
    try:
        o.KDE_CI_BACKEND = 'batched'; bat = o._family_logD(fm, t, w, True)
        # non-finite component density inside a batched replicate is not hidden by the mixture (same contract as the per-replicate path)
        from unittest.mock import patch
        import step1_engine.density as dens; orig = dens.kde_logpdf_replicates
        def fail_one(X, cid, pts, M, factor_scale=1.0, chunk=128):
            out = orig(X, cid, pts, M, factor_scale, chunk); out[2, 0] = -np.inf; return out
        with patch.object(dens, 'kde_logpdf_replicates', side_effect=fail_one):
            inj = o._family_logD(fm, t, w, True)
        assert inj[1].math_state == 'technical_fail' and int(inj[1].counts['technical_invalid']) >= 1 and inj[4]['invalid_mask'][2] is True
    finally: o.KDE_CI_BACKEND = 'per_replicate'
    assert ref[1].math_state == bat[1].math_state == 'finite' and abs(ref[1].log_lower - bat[1].log_lower) < 1e-9 and abs(ref[1].log_upper - bat[1].log_upper) < 1e-9
    assert np.allclose(ref[4]['replicate_values'], bat[4]['replicate_values'], rtol=1e-9, atol=1e-9) and ref[0] == bat[0] and ref[3] == bat[3]
