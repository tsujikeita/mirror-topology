# -*- coding: utf-8 -*-
"""D-3 tranche 1 contracts: explicit 12-position mapping (111 physical / 222 evaluation ids; first-wave ids and geometry preserved verbatim; suffix 04..12 for added points; tampered
anchor refused), PC-1 contract transcribed from the frozen A11 originals (rules / notebook SHAs present in the frozen checkout; R5 TOL_MATCH = 1e-5 and the rel metric are the
notebook's; D-1 1e-10 not used), case table (108 new-point cases, 36 first-wave anchor cases, 225 unique generations; E8 two actions; clone x0 = M b - T from the pinned
CMBtopology generators), reuse-binding schema fields."""
import os, sys, json, copy, hashlib
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine.d3_stage import build_twelve_config_map, build_pc1_case_table, PC1_CONTRACT, REUSE_BINDING_SCHEMA, A11_RULES_SHA, A11_NOTEBOOK_SHA, REQUIRED_ACTIONS
from step1_engine.twelve_assets import intake_registered_twelve_assets, TwelveManifestAsset
from step1_engine.grid_registry import load_registry; from step1_engine.grid_manifest import build_configuration_manifest
from step1_engine.errors import InputContractError
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); MT = os.environ.get('B3_MT', '/home/claude/mt'); CT = os.environ.get('CT_PINNED', '/tmp/CMBtopology_pinned')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()

def _ctx():
    reg = load_registry(os.path.join(P, 'tests/assets/a7_circle_geometry.csv'), os.path.join(P, 'tests/assets/a6_observer_design_points.json')); man = build_configuration_manifest(reg)
    from step1_engine import twelve_assets as ta_mod; ta_mod._VERIFIED.clear()
    ta = intake_registered_twelve_assets(os.path.join(P, 'registered_assets/b3_2_twelve_assets.json'), reg, 'B3_2A_7240c06f255c'); return reg, man, ta

def test_mapping_is_explicit_bijective_and_preserves_first_wave():
    reg, man, ta = _ctx(); cm = build_twelve_config_map(reg, man, ta); committed = json.load(open(os.path.join(P, 'd', 'd3_config_map.json')))
    assert cm['map_sha256'] == committed['map_sha256'] and cm['n_physical'] == 111 and cm['n_new'] == 81 and cm['n_evaluation_ids'] == 222
    rows = {r['config_id']: r for r in cm['configurations']}; fw = {c.config_id: c for c in man.configurations}
    for cid, c in fw.items(): assert rows[cid]['origin'].startswith('first_wave') and rows[cid]['x0_CT'] == [float(v) for v in c.x0_CT] and rows[cid]['cache_key'] == c.cache_key and rows[cid]['reduced_coords'] == [float(v) for v in c.reduced_coords]
    assert sorted(r['config_id'] for r in cm['configurations'] if r['family'] == 'E7' and r['size_id'] == 'L1.00') == list(range(30101, 30113)) and rows[30104]['display_suffix'] == '04' and rows[30104]['position_index'] == 3 and rows[30112]['position_index'] == 11
    assert rows[30104]['evaluation_ids'] == dict(matched=30104, native=80104) and rows[30104]['weight_family'] == 1 / 36 and rows[30104]['weight_within_size'] == 1 / 12 and rows[10101]['origin'] == 'first_wave_E1_homogeneous'
    evs = [r['evaluation_ids'][s] for r in cm['configurations'] for s in ('matched', 'native')]; assert len(set(evs)) == 222 and set(evs) & {c.config_id for c in fw.values()} == {c.config_id for c in fw.values()}
    # tampered twelve anchor (position 1 moved) -> the first-wave configuration no longer reproduces -> refused
    bad = copy.deepcopy(ta.as_dict()); man7 = bad['manifests']['E7']['L1.00']; man7['points'][1][0] += 1e-6; man7['anchors'][1][0] += 1e-6
    from step1_engine.stage12 import TwelvePositionManifest
    class Fake:
        sha256 = 'x' * 64
        def __init__(self, d): self.manifests = {f: {s: TwelvePositionManifest(**m) for s, m in ss.items()} for f, ss in d['manifests'].items()}
        def get(self, f, s, sha=None): return self.manifests[f][s]
    with pytest.raises(InputContractError): build_twelve_config_map(reg, man, Fake(bad))

@pytest.mark.skipif(not os.path.exists(os.path.join(MT, 'results/step1_phaseA/A11_freeze/A11_rules_v1.0.md')), reason='frozen A11 originals not present')
def test_pc1_contract_transcribed_from_frozen_originals():
    rules = os.path.join(MT, 'results/step1_phaseA/A11_freeze/A11_rules_v1.0.md'); nb = os.path.join(MT, 'results/step1_phaseA/A11_freeze/MirrorTopology_Step1_A11_x0bridge_v1.4.1.ipynb')
    assert sha(rules) == A11_RULES_SHA and sha(nb) == A11_NOTEBOOK_SHA
    txt = open(rules).read(); assert 'C(g r) = D(M) C(r) D(M)ᵀ' in txt and 'match: rel < 1e-5' in txt and 'discriminate: rel > 1e-2' in txt
    cells = json.load(open(nb))['cells']; c5 = ''.join(cells[5]['source']); c3 = ''.join(cells[3]['source'])
    assert 'def rel(A, B): return float(np.linalg.norm(A - B) / np.linalg.norm(B))' in c5 and 'TOL_MATCH, TOL_DISCR = 1e-5, 1e-2' in c5 and 'target = D_of(c[\'M\']) @ C0 @ D_of(c[\'M\']).T' in c5 and 'x0_H1=MCT @ b - TCT' in c3
    assert PC1_CONTRACT['tolerance']['match_rel_lt'] == 1e-5 and PC1_CONTRACT['tolerance']['discriminate_rel_gt'] == 1e-2 and PC1_CONTRACT['not_used']['d1_pins_rel_tolerance'] == 1e-10 and 'PC1_FAIL' in PC1_CONTRACT['status_semantics']
    assert json.load(open(os.path.join(P, 'd', 'd3_pc1_contract.json')))['tolerance'] == PC1_CONTRACT['tolerance']

@pytest.mark.skipif(not os.path.exists(os.path.join(CT, 'topology/src/E7.py')), reason='pinned CMBtopology not present')
def test_case_table_counts_and_clone_positions():
    reg, man, ta = _ctx(); cm = build_twelve_config_map(reg, man, ta); d1 = json.load(open(os.path.join(P, 'registered_assets/d1/d1_cov_registry.json'))); ct = build_pc1_case_table(cm, CT, d1)
    assert ct['counts']['new_point_cases'] == 108 and ct['counts']['first_wave_anchor_cases'] == 36 and ct['counts']['unique_covariance_requests'] == dict(new_bases=81, new_clones=108, first_wave_clones=36, first_wave_bases_reused=27, total_new_generations=225)
    assert ct['table_sha256'] == json.load(open(os.path.join(P, 'd', 'd3_pc1_case_table.json')))['table_sha256'] and REQUIRED_ACTIONS['E8'] == ['glide_A', 'glide_B']
    for c in ct['new_point_cases'] + ct['first_wave_anchor_cases']:
        M, T, b = np.array(c['M']), np.array(c['T']), np.array(c['base_x0']); assert np.allclose(M @ b - T, c['clone_x0_H1']) and np.allclose(M @ b + T, c['alt_x0_H2']) and abs(abs(np.linalg.det(M)) - 1) < 1e-12 and c['status'] == 'PC1_PENDING' and c['tolerance_match_rel_lt'] == 1e-5
    e8 = [c for c in ct['new_point_cases'] if c['config_id'] == 40104]; assert sorted(c['action'] for c in e8) == ['glide_A', 'glide_B'] and not any(c['family'] == 'E1' for c in ct['new_point_cases'])
    a = ct['first_wave_anchor_cases'][0]; assert a['set'] == 'first_wave_anchor_diagnostic' and a['base_reused_from_D1']['cov_file_sha256'] == d1['configurations'][str(a['config_id'])]['cov_file_sha256']

def test_reuse_binding_schema_fields():
    s = json.load(open(os.path.join(P, 'd', 'd3_d2_reuse_binding_schema.json'))); assert s == REUSE_BINDING_SCHEMA
    for k in ('identity_kept_verbatim', 'must_match_the_D3_request', 'view_differences_allowed', 'forbidden', 'plan_sharing'): assert k in s
    assert any('8b5e6102' in x for x in s['identity_kept_verbatim']) and any('f32' in x for x in s['forbidden']) and 'unchanged through the target evaluation' in s['plan_sharing']['fixed']
