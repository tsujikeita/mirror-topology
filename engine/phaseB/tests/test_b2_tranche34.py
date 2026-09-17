# -*- coding: utf-8 -*-
"""B-2 tranche 34: fixed 12-position manifest asset — generate once, intake-verify by regeneration, reuse without regeneration (zero generator calls in the evaluator),
identical results to the regenerating path, tampered / foreign-registry assets rejected, strict-JSON round trip re-verified before use."""
import os, sys, copy
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from step1_engine import stage12, twelve_assets as ta, threshold_evaluator as te
from step1_engine.twelve_assets import build_twelve_assets, verify_twelve_assets, asset_from_dict
from step1_engine.grid_registry import load_registry, registry_from_dict
from step1_engine.errors import InputContractError
from step1_engine import serialization as ser
from test_b2_tranche20 import A7, A6

def test_asset_build_verify_reuse_and_rejections(monkeypatch):
    reg = load_registry(A7, A6); asset = build_twelve_assets(reg, families=['E7']); assert asset.verification['manifests'] == 3 and len(asset.sha256) == 64
    calls = []; orig = stage12.generate_twelve
    monkeypatch.setattr(stage12, 'generate_twelve', lambda *a, **k: (calls.append(a), orig(*a, **k))[1])
    for s in reg.surviving['E7']: m = asset.get('E7', s); assert m.sha256 == asset.manifests['E7'][s].sha256
    assert calls == []                                                                                          # reuse: no regeneration after intake
    m = asset.get('E7', 'L1.00'); assert stage12.verify_twelve_registered(m) and calls == []                    # consumer entry uses the verified set
    with pytest.raises(InputContractError): asset.get('E7', 'L1.00', '0' * 64)
    with pytest.raises(InputContractError): asset.get('E8', 'L1.00')
    d = ser.loads(ser.dumps(asset.as_dict())); a2 = asset_from_dict(d)
    ta._VERIFIED.clear()
    with pytest.raises(InputContractError): a2.get('E7', 'L1.00')                                                # restored asset must be intake-verified before use
    assert verify_twelve_assets(a2, reg, expected_sha256=asset.sha256)['manifests'] == 3 and a2.get('E7', 'L1.20').sha256 == asset.manifests['E7']['L1.20'].sha256
    bad = copy.deepcopy(asset); bad.manifests['E7']['L1.00'].points[5][0] += 1e-4; ta._VERIFIED.clear()
    with pytest.raises(InputContractError): verify_twelve_assets(bad, reg)
    bad2 = copy.deepcopy(asset); bad2.registry_sha256 = '0' * 64
    with pytest.raises(InputContractError): verify_twelve_assets(bad2, reg)
    internal = registry_from_dict(ser.loads(ser.dumps(reg.as_dict())))
    with pytest.raises(InputContractError): build_twelve_assets(internal, families=['E7'])                       # source-bound registry required
    verify_twelve_assets(asset, reg)

def test_evaluator_with_asset_makes_no_generator_calls_and_matches(monkeypatch):
    from fixture32 import base, twelve_from_cases
    b = base(); ti = twelve_from_cases(b['cases']); reg, man = b['reg'], b['man']; asset = build_twelve_assets(reg, families=['E7'])
    views = {k.split('/')[1]: v for k, v in b['cases'].items()}; parent = te.__dict__.get('_dummy')  # noqa
    from step1_engine.integrated_runner import assemble_parent
    pm_, pn_ = assemble_parent(reg, man, 'E7', {s: (v[0], v[1]) for s, v in views.items()})
    r_gen = te.evaluate_family_full(reg, man, 'E7', (pm_, pn_), views, b['ctx'], b['ctx'].context_sha256, 100.0, 550.0, ti, with_diagnostics=False)
    calls = []; orig = stage12.generate_twelve; monkeypatch.setattr(stage12, 'generate_twelve', lambda *a, **k: (calls.append(a), orig(*a, **k))[1]); monkeypatch.setattr(te, 'generate_twelve', stage12.generate_twelve)
    r_asset = te.evaluate_family_full(reg, man, 'E7', (pm_, pn_), views, b['ctx'], b['ctx'].context_sha256, 100.0, 550.0, ti, with_diagnostics=False, twelve_assets=asset)
    assert calls == [] and r_asset.expand_family == r_gen.expand_family and r_asset.required_manifests == r_gen.required_manifests and r_asset.eligible_truths == r_gen.eligible_truths
    if r_gen.twelve is not None: assert ser.dumps(r_asset.twelve['full_result']) == ser.dumps(r_gen.twelve['full_result'])
