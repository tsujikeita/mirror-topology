# -*- coding: utf-8 -*-
"""B-2 tranche 29: adopted tranche-28 KDE fixes; integrated first-wave runner (registry -> production FamilyInputs per case -> gate -> target -> transitions/coordinator ->
pseudo calibration -> archive/run manifest) on synthetic banks with a shared W2 context (E7, all three surviving sizes)."""
import os, sys, copy
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from step1_engine.rules_config import RULES
from step1_engine.grid_registry import load_registry
from step1_engine.production import production_manifest, build_family_input
from step1_engine.w2_shared import build_shared_null
from step1_engine.w2_context import build_w2_context
from step1_engine.integrated_runner import run_first_wave
from step1_engine.archive import Archive
from step1_engine.errors import InputContractError
from test_b2_tranche20 import synthetic_supplies, A7, A6
from test_b2_tranche3 import cheap_dist, make_positions
from test_b2_tranche25 import paired

def test_integrated_first_wave_smoke(tmp_path):
    reg = load_registry(A7, A6); man = production_manifest(reg); sizes = reg.surviving['E7']
    sm, plans, fplans = synthetic_supplies(man, 'E7', 'matched'); sn, _, _ = synthetic_supplies(man, 'E7', 'native'); cases = {}
    rng = np.random.default_rng(29); _, iso = make_positions(rng); iso32 = paired(iso); asset = build_shared_null(iso, 10, 20260916, dist=cheap_dist, iso_f32=iso32, whitening_identity=dict(source='test'))
    w2cases = {}
    for i, s in enumerate(sizes):
        code = i + 1; fm = build_family_input(reg, man, 'E7', 'matched', [x for x in sm if x.config_id // 100 % 100 == code], plans, fplans, size_ids=[s]); fn = build_family_input(reg, man, 'E7', 'native', [x for x in sn if x.config_id // 100 % 100 == code], plans, fplans, size_ids=[s])
        pmap = {c.evaluation_id: j + 1 for j, c in enumerate(fm.configs)}; cases[f'E7/{s}'] = (fm, fn, pmap)
        pos, _ = make_positions(np.random.default_rng(100 + i), shifts=(0.0, 0.0, 0.8 if i == 0 else 0.0)); w2cases[f'E7/{s}'] = dict(positions=pos, positions_f32=[paired(p, seed=j + 1) for j, p in enumerate(pos)])
    ctx = build_w2_context(asset, w2cases, 10, 20260916, dist=cheap_dist, whitening_identity=dict(source='test'), expected_asset_sha256=asset.sha256); snap = ctx.snapshot()
    arc = Archive(str(tmp_path / 'arc')); rm = run_first_wave(reg, man, cases, ctx, snap.context_sha256, (80.0, 400.0), np.array([80.0, 200.0]), np.array([400.0, 900.0]), arc, mode='smoke', twelve_anchors={'E7': reg.anchors['E7']})
    assert set(rm.cases) == {f'E7/{s}' for s in sizes} and rm.final_label_released is False and rm.families['E7']['status'] in ('expansion_registered (all surviving sizes)', 'final at 3 positions', 'provisional / position-unresolved')
    assert set(rm.calibration) == {'support', 'strong'} and rm.calibration['support']['summary']['w2_context']['context_sha256'] == snap.context_sha256 and arc.verify_all()['entries'] >= 5
    for k, c in rm.cases.items(): assert arc.get(type(arc).__dict__ and __import__('step1_engine.archive', fromlist=['ArchiveRef']).ArchiveRef(**c['result_ref']))['family'] == 'E7'
    with pytest.raises(InputContractError): run_first_wave(reg, man, cases, ctx, '0' * 64, (80.0, 400.0), np.array([80.0]), np.array([400.0]), arc, mode='smoke', twelve_anchors={'E7': reg.anchors['E7']})
    with pytest.raises(InputContractError): run_first_wave(reg, man, cases, ctx, snap.context_sha256, (80.0, 400.0), np.array([80.0]), np.array([400.0]), arc, mode='official', twelve_anchors={'E7': reg.anchors['E7']})   # sandbox: official gate refuses
    bad = dict(cases); bad['E7/L1.00'] = (cases['E7/L1.20'][0], cases['E7/L1.20'][1], cases['E7/L1.20'][2])
    with pytest.raises(InputContractError): run_first_wave(reg, man, bad, ctx, snap.context_sha256, (80.0, 400.0), np.array([80.0]), np.array([400.0]), arc, mode='smoke', twelve_anchors={'E7': reg.anchors['E7']})   # case/size identity mismatch
