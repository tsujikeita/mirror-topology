# -*- coding: utf-8 -*-
"""B-2 tranche 26: adopted tranche-25 audit fixes (R25-A/B/C); shared W2 context reused identically for the real target, pseudo evaluations and controls."""
import os, sys, copy
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from step1_engine.positions import PositionBank, W2NotEvaluated
from step1_engine.w2_shared import build_shared_null
from step1_engine.w2_context import build_w2_context
from step1_engine.orchestrator import evaluate_threshold, calibrate_pseudo
from step1_engine.errors import InputContractError
from test_b2_tranche3 import cheap_dist, make_positions
from test_b2_tranche4 import make_staged_family
from test_b2_tranche25 import paired

def test_w2_context_shared_across_target_pseudo_and_controls():
    rng = np.random.default_rng(21); pos, iso = make_positions(rng, shifts=(0.0, 0.0, 0.8)); iso32 = paired(iso); pos32 = [paired(p, seed=i + 1) for i, p in enumerate(pos)]
    asset = build_shared_null(iso, 10, 20260914, dist=cheap_dist, iso_f32=iso32, whitening_identity=dict(source='test'))
    ctx = build_w2_context(asset, {'E7/L1.00': dict(positions=pos, positions_f32=pos32)}, 10, 20260914, dist=cheap_dist, whitening_identity=dict(source='test'), expected_asset_sha256=asset.sha256)
    d = ctx.decision_for('E7/L1.00'); assert d.trigger is True and d.check() and ctx.as_dict()['asset_sha256'] == asset.sha256
    with pytest.raises(InputContractError): build_w2_context(asset, {'E7/L1.00': dict(positions=pos, positions_f32=pos32)}, 10, 20260914, dist=cheap_dist, whitening_identity=dict(source='test'), expected_asset_sha256='0' * 64)
    with pytest.raises(InputContractError): ctx.decision_for('E2/L1.00')
    fam = make_staged_family(np.random.default_rng(5)); fams = {'E7': (fam, None)}; pm = {'E7': {100: 1, 101: 2, 102: 3}}; w2 = {'E7': d}
    r_target = evaluate_threshold(fams, 80.0, 400.0, staged=True, position_maps=pm, w2_results=w2)['E7']; assert r_target.position_status['state'] == 'position-sensitive' and r_target.evidence['position']['w2']['trigger'] is True
    summ, truths = calibrate_pseudo(fams, np.array([80.0, 200.0]), np.array([400.0, 900.0]), 'support', staged=True, position_maps=pm, w2_results=w2)   # same typed decisions for every pseudo
    assert summ.n == 2 and '3-position' in summ.reason
    with pytest.raises(InputContractError): calibrate_pseudo(fams, np.array([80.0]), np.array([400.0]), 'support', staged=True, position_maps=pm, w2_results={'E7': dict(trigger=True)})   # raw dict never accepted
    r_ne = evaluate_threshold(fams, 80.0, 400.0, staged=True, position_maps=pm, w2_results={'E7': W2NotEvaluated('control without W2')})['E7']; assert r_ne.position_status['state'] in ('position-unresolved', 'position-sensitive')
