# -*- coding: utf-8 -*-
"""B-2 tranche 19: adopted tranche-18 audit fixes; configuration manifest (registry -> 30 configurations with lift / x0_CT / cache keys) cross-checked against the frozen A7 rows;
covariance-cache manifest binding (A11 format) with real frozen A11 cache entries where available."""
import os, sys, copy, json, glob
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine.grid_registry import load_registry
from step1_engine.grid_manifest import build_configuration_manifest, verify_manifest_against_a7, verify_cov_manifest, ConfigurationManifest, ConfigurationSpec, lift, shape_params, cache_key
from step1_engine.errors import InputContractError
from step1_engine import serialization as ser
ASSETS = os.path.join(os.path.dirname(__file__), 'assets'); A7 = os.path.join(ASSETS, 'a7_circle_geometry.csv'); A6 = os.path.join(ASSETS, 'a6_observer_design_points.json')

def test_configuration_manifest_matches_frozen_a7():
    reg = load_registry(A7, A6); man = build_configuration_manifest(reg)
    assert man.n_configurations == 30 and len({c.config_id for c in man.configurations}) == 30 and man.registry_sha256 == reg.registry_sha256
    assert verify_manifest_against_a7(man, A7)['checked'] == 30                                              # shape JSON, r_obs_LLSS and circle status agree row by row with A7
    c = next(x for x in man.configurations if x.family == 'E7' and x.size_id == 'L1.00' and x.position_index == 0)
    assert c.x0_CT == [-v for v in c.r_obs] and c.r_obs == [0.31, 0.11278702805018147, 0.42] and c.shape_params == dict(LAx=1.0, LAy=0.0, L1y=1.0, L2x=0.0, L2z=1.0) and abs(c.weight - 1 / 9) < 1e-15
    e1 = [x for x in man.configurations if x.family == 'E1']; assert len(e1) == 3 and all(x.r_obs == [0.0, 0.0, 0.0] and abs(x.weight - 1 / 3) < 1e-15 for x in e1)
    d = ser.loads(ser.dumps(man.as_dict())); man2 = ConfigurationManifest(d['schema'], d['registry_sha256'], d['lift_source'], [ConfigurationSpec(**s) for s in d['configurations']], d['n_configurations'], d['manifest_sha256'])
    assert man2.payload_sha() == man.manifest_sha256
    bad = copy.deepcopy(man); bad.configurations[5].r_obs[1] += 1e-3
    with pytest.raises(InputContractError): verify_manifest_against_a7(bad, A7)

def test_cov_manifest_binding_synthetic_and_frozen_a11():
    reg = load_registry(A7, A6); man = build_configuration_manifest(reg); c = next(x for x in man.configurations if x.family == 'E7' and x.size_id == 'L1.00' and x.position_index == 0)
    good = dict(manifest=dict(topology='E7', params=c.shape_params, x0=c.x0_CT), cov_array_sha256='a' * 64, cov_file_sha256='b' * 64); assert verify_cov_manifest(c, good)['bound']
    for mut in (lambda m: m['manifest'].__setitem__('topology', 'E8'), lambda m: m['manifest']['params'].__setitem__('LAy', 0.3), lambda m: m['manifest'].__setitem__('x0', [0.31, 0.21, 0.42]), lambda m: m.pop('cov_array_sha256')):
        m = copy.deepcopy(good); mut(m)
        with pytest.raises(InputContractError): verify_cov_manifest(c, m)
    # portable fixture: frozen A11 cache metadata (tilted E7, several x0) does NOT belong to any first-wave configuration; a diagnostic spec built from the entry itself binds
    fx = json.load(open(os.path.join(ASSETS, 'a11_cov_manifests_fixture.json')))
    for e in fx['entries']:
        a11 = e['manifest']
        with pytest.raises(InputContractError): verify_cov_manifest(c, a11)
        topo = a11['manifest']['topology']; spec = ConfigurationSpec(0, topo, 'tilt', 1.0, 0, 1, a11['manifest']['params'], [], [-v for v in a11['manifest']['x0']], a11['manifest']['x0'], cache_key(topo, a11['manifest']['params'], a11['manifest']['x0']), {}, 0.0)
        v = verify_cov_manifest(spec, a11); assert v['bound'] and v['array_sha_verified'] is False and v['file_sha_verified'] is False

@pytest.mark.skipif(not glob.glob('/home/claude/mt/results/step1_phaseA/A11_freeze/official/cov_cache/*.npy'), reason='frozen A11 .npy arrays not present (external asset integration test)')
def test_cov_manifest_binding_with_frozen_a11_arrays():
    m = sorted(glob.glob('/home/claude/mt/results/step1_phaseA/A11_freeze/official/cov_cache/*.manifest.json'))[0]; a11 = json.load(open(m)); npy = m.replace('.manifest.json', ''); topo = a11['manifest']['topology']
    spec = ConfigurationSpec(0, topo, 'tilt', 1.0, 0, 1, a11['manifest']['params'], [], [-v for v in a11['manifest']['x0']], a11['manifest']['x0'], cache_key(topo, a11['manifest']['params'], a11['manifest']['x0']), {}, 0.0)
    assert verify_cov_manifest(spec, a11, npy)['file_sha_verified'] is True
