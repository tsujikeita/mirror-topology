# -*- coding: utf-8 -*-
"""D-3 tranche 1 v2 contracts (audit R-D3T1-A/B/C): source-bound inputs for the mapping (registry / manifest re-derivation / receipt-intaken twelve asset; edits refused), map
verification (payload + content equality), case table built only from a verified map + source-bound CT context (pinned checkout OR registered pinned copies, same table) + A11
attestation + D-1 same-config binding (draft without D-1 is non-formal); public return values are snapshots (edits do not propagate to the contract, actions, or inputs); the
ported gens_CT equals the A11 cell-3 function (AST) except for the source-text argument; TEST-ONLY CT sources are refused by the source binding."""
import os, sys, json, copy, hashlib, ast, shutil
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine import d3_stage as d3
from step1_engine.d3_stage import build_twelve_config_map, build_pc1_case_table, verify_config_map, verify_pc1_case_table, PC1_CONTRACT, REQUIRED_ACTIONS, REUSE_BINDING_SCHEMA, a11_attestation, ct_source_context, A11_RULES_SHA, A11_NOTEBOOK_SHA, TRUSTED_SOURCES
from step1_engine.twelve_assets import intake_registered_twelve_assets, TwelveManifestAsset, build_twelve_assets
from step1_engine.grid_registry import load_registry, registry_from_dict; from step1_engine.grid_manifest import build_configuration_manifest
from step1_engine.errors import InputContractError
from step1_engine import serialization as ser
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); CT = os.environ.get('CT_PINNED', '/tmp/CMBtopology_pinned'); D1 = os.path.join(P, 'registered_assets', 'd1')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()

def _ctx():
    reg = load_registry(os.path.join(P, 'tests/assets/a7_circle_geometry.csv'), os.path.join(P, 'tests/assets/a6_observer_design_points.json')); man = build_configuration_manifest(reg)
    from step1_engine import twelve_assets as ta_mod; ta_mod._VERIFIED.clear()
    return reg, man, intake_registered_twelve_assets(os.path.join(P, 'registered_assets/b3_2_twelve_assets.json'), reg, 'B3_2A_7240c06f255c')

def test_mapping_bound_inputs_and_verification():
    reg, man, ta = _ctx(); cm = build_twelve_config_map(reg, man, ta); committed = json.load(open(os.path.join(P, 'd', 'd3_config_map.json')))
    assert cm['map_sha256'] == committed['map_sha256'] and cm == committed and cm['n_physical'] == 111 and cm['n_new'] == 81 and cm['n_evaluation_ids'] == 222 and cm['twelve_assets_receipt'] == 'B3_2A_7240c06f255c'
    rows = {r['config_id']: r for r in cm['configurations']}
    for c in man.configurations: assert rows[c.config_id]['x0_CT'] == [float(v) for v in c.x0_CT] and rows[c.config_id]['cache_key'] == c.cache_key and rows[c.config_id]['origin'].startswith('first_wave')
    assert sorted(r['config_id'] for r in cm['configurations'] if r['family'] == 'E7' and r['size_id'] == 'L1.00') == list(range(30101, 30113)) and rows[30104]['display_suffix'] == '04' and rows[30104]['evaluation_ids'] == dict(matched=30104, native=80104)
    assert verify_config_map(committed, reg, man, ta) == cm
    # (B) inputs must be mutually bound: internal-only registry, manifest with another registry sha, unregistered asset object, edited twelve asset -> refused
    internal = registry_from_dict(ser.loads(ser.dumps(reg.as_dict())))
    with pytest.raises(InputContractError): build_twelve_config_map(internal, man, ta)
    from step1_engine.grid_manifest import ConfigurationManifest, ConfigurationSpec
    d = ser.from_jsonable(man.as_dict()); d['registry_sha256'] = '0' * 64; m2 = ConfigurationManifest(schema=d['schema'], registry_sha256=d['registry_sha256'], lift_source=d['lift_source'], configurations=[ConfigurationSpec(**c) for c in d['configurations']], n_configurations=d['n_configurations'], manifest_sha256=''); m2.manifest_sha256 = m2.payload_sha()
    with pytest.raises(InputContractError): build_twelve_config_map(reg, m2, ta)
    fresh = build_twelve_assets(reg, families=['E7']); fresh._intake_sha256 = None                                                                                  # E7 only: cheap to regenerate
    with pytest.raises(InputContractError): build_twelve_config_map(reg, man, fresh)                                                                              # not receipt-intaken
    class Fake:
        sha256 = ta.sha256; manifests = ta.manifests; verification = ta.verification; _intake_sha256 = ta.sha256
        def get(self, f, s, sha=None): return self.manifests[f][s]
    with pytest.raises(InputContractError): build_twelve_config_map(reg, man, Fake())                                                                             # duck-typed object refused
    bad = copy.deepcopy(committed); bad['configurations'][40]['x0_CT'][0] += 1e-6
    with pytest.raises(InputContractError): verify_config_map(bad, reg, man, ta)                                                                                    # payload stale
    bad['map_sha256'] = d3._map_payload_sha(bad)
    with pytest.raises(InputContractError): verify_config_map(bad, reg, man, ta)                                                                                    # re-stamped but not the derivation
    bad2 = copy.deepcopy(committed); bad2['configurations'].pop(40); bad2['map_sha256'] = d3._map_payload_sha(bad2)
    with pytest.raises(InputContractError): verify_config_map(bad2, reg, man, ta)

@pytest.mark.skipif(not os.path.exists(os.path.join(P, 'registered_assets', 'a11', 'A11_rules_v1.0.md')), reason='registered A11 extract missing')
def test_a11_attestation_and_ported_gens_ct():
    att = a11_attestation(); assert att['rules_sha256'] == A11_RULES_SHA and att['notebook_sha256'] == A11_NOTEBOOK_SHA and set(att['cells']) == {'2', '3', '5'} and att['source'] == 'registered_originals_trust_anchored' and att['extract_manifest_sha256'] == TRUSTED_SOURCES['a11_extract_manifest']
    full = json.load(open(os.path.join(P, 'registered_assets', 'a11', 'MirrorTopology_Step1_A11_x0bridge_v1.4.1.ipynb')))
    assert all(''.join(full['cells'][int(i)]['source']) == att['cell_text'][i] for i in ('2', '3', '5')) and sha(os.path.join(P, 'registered_assets', 'a11', 'MirrorTopology_Step1_A11_x0bridge_v1.4.1.ipynb')) == A11_NOTEBOOK_SHA   # cells re-extracted from the FULL frozen notebook
    c3 = att['cell_text']['3']; orig = [n for n in ast.parse(c3).body if isinstance(n, ast.FunctionDef) and n.name == 'gens_CT'][0]
    ported = [n for n in ast.parse(open(os.path.join(P, 'step1_engine', 'd3_stage.py')).read()).body if isinstance(n, ast.FunctionDef) and n.name == '_gens_CT_from_source'][0]
    # identical bodies except the first statement (path read vs supplied text): compare the statements after the source assignment
    first = 1 if isinstance(orig.body[0], ast.Expr) else 0; ob = [ast.dump(x) for x in orig.body[first + 1:]]; pb = [ast.dump(x) for x in ported.body[2:]]; assert ob == pb and 'open(' in ast.get_source_segment(c3, orig.body[first])
    assert PC1_CONTRACT['tolerance'] == dict(match_rel_lt=1e-5, discriminate_rel_gt=1e-2, source=PC1_CONTRACT['tolerance']['source']) and 'not yet compared' in PC1_CONTRACT['status_semantics']['PC1_PENDING']
    ctx = ct_source_context(None); assert ctx['source'] == 'registered_pinned_copy' and ctx['commit'] == d3.CT_COMMIT and set(ctx['files']) == set(d3.CT_FILES) and ctx['file_sha256'] == TRUSTED_SOURCES['ct_files']
    # trust anchor: a jointly modified (member + inner manifest) registered copy is refused because the constants, not the manifest, are the reference
    import tempfile, shutil as _sh; root2 = os.path.join(tempfile.mkdtemp(), 'copy'); _sh.copytree(P, root2, ignore=_sh.ignore_patterns('__pycache__', '.pytest_cache', 'regression_logs', 'tests', 'registered_assets/d2', 'registered_assets/d1')); sys.path.insert(0, root2)
    e8 = os.path.join(root2, 'registered_assets', 'ct_pinned', 'topology', 'src', 'E8.py'); src = open(e8).read().replace('T_B = np.array([LBx, 0, LBz])', 'T_B = np.array([2*LBx, 0, 2*LBz])'); assert src != open(e8).read(); open(e8, 'w').write(src)
    mp = os.path.join(root2, 'registered_assets', 'ct_pinned', 'ct_source_manifest.json'); mm = json.load(open(mp)); mm['files']['topology/src/E8.py'] = sha(e8); mm['git_commit_file_sha']['topology/src/E8.py'] = sha(e8); json.dump(mm, open(mp, 'w'), indent=1)
    import importlib.util; spec_ = importlib.util.spec_from_file_location('d3_stage_copy', os.path.join(root2, 'step1_engine', 'd3_stage.py'), submodule_search_locations=None)
    mod_src = open(os.path.join(root2, 'step1_engine', 'd3_stage.py')).read().replace('_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))', f'_ROOT = {root2!r}'); ns = {}; import types; m2 = types.ModuleType('step1_engine.d3_stage_copy'); m2.__file__ = os.path.join(root2, 'step1_engine', 'd3_stage.py'); m2.__package__ = 'step1_engine'; exec(compile(mod_src, m2.__file__, 'exec'), m2.__dict__)
    with pytest.raises(InputContractError): m2.ct_source_context(None)
    # A11: dropping a required cell from the inner manifest, altering D_of, or appending a second rel() are refused by the constants / full-notebook re-extraction
    ap = os.path.join(root2, 'registered_assets', 'a11'); am = json.load(open(os.path.join(ap, 'a11_extract_manifest.json'))); am2 = copy.deepcopy(am); am2['cells'].pop('2'); json.dump(am2, open(os.path.join(ap, 'a11_extract_manifest.json'), 'w'), indent=1)
    with pytest.raises(InputContractError): m2.a11_attestation()
    json.dump(am, open(os.path.join(ap, 'a11_extract_manifest.json'), 'w'), indent=1); c2p = os.path.join(ap, 'A11_v1.4.1_cell2.py'); c2 = open(c2p).read(); open(c2p, 'w').write(c2.replace('def D_of(', 'def D_of_(') + '\ndef D_of(M): return np.eye(21)\n'); am3 = copy.deepcopy(am); am3['cells']['2']['source_sha256'] = sha(c2p); json.dump(am3, open(os.path.join(ap, 'a11_extract_manifest.json'), 'w'), indent=1)
    with pytest.raises(InputContractError): m2.a11_attestation()
    open(c2p, 'w').write(c2); json.dump(am, open(os.path.join(ap, 'a11_extract_manifest.json'), 'w'), indent=1); c5p = os.path.join(ap, 'A11_v1.4.1_cell5.py'); c5 = open(c5p).read(); open(c5p, 'w').write(c5 + '\ndef rel(A,B): return 0.0\n'); am4 = copy.deepcopy(am); am4['cells']['5']['source_sha256'] = sha(c5p); json.dump(am4, open(os.path.join(ap, 'a11_extract_manifest.json'), 'w'), indent=1)
    with pytest.raises(InputContractError): m2.a11_attestation()
    # a TEST-ONLY tampered source directory is refused by the source binding (not a real CT change)
    import tempfile; t = tempfile.mkdtemp(); shutil.copytree(os.path.join(P, 'registered_assets', 'ct_pinned', 'topology'), os.path.join(t, 'topology')); open(os.path.join(t, 'topology', 'src', 'E8.py'), 'a').write('\n# T_B = 2*T_B\n')
    with pytest.raises(InputContractError): ct_source_context(t)

def test_case_table_verified_inputs_snapshots_and_d1_binding():
    reg, man, ta = _ctx(); cm = build_twelve_config_map(reg, man, ta)
    ct = build_pc1_case_table(cm, reg, man, ta, None, D1); committed = json.load(open(os.path.join(P, 'd', 'd3_pc1_case_table.json')))
    assert ct['table_sha256'] == committed['table_sha256'] and ct['formal'] is True and ct['counts']['unique_covariance_requests']['total_new_generations'] == 225 and ct['counts']['new_point_cases'] == 108 and ct['ct_source']['file_sha256'] == json.load(open(os.path.join(P, 'registered_assets', 'ct_pinned', 'ct_source_manifest.json')))['files']
    if os.path.exists(os.path.join(CT, 'topology/src/E7.py')): assert build_pc1_case_table(cm, reg, man, ta, CT, D1)['table_sha256'] == ct['table_sha256']                  # pinned checkout route == registered copy route
    assert verify_pc1_case_table(committed, cm, reg, man, ta, None, D1)['table_sha256'] == ct['table_sha256']
    for c in ct['new_point_cases'] + ct['first_wave_anchor_cases']:
        M, T, b = np.array(c['M']), np.array(c['T']), np.array(c['base_x0']); assert np.allclose(M @ b - T, c['clone_x0_H1']) and abs(abs(np.linalg.det(M)) - 1) < 1e-12 and c['status'] == 'PC1_PENDING'
    # (C) public return values are snapshots
    ct['contract']['tolerance']['match_rel_lt'] = 0.25; ct['required_actions']['E8'].pop(); ct['new_point_cases'][0]['base_x0'][0] = 999.0; ct['new_point_cases'][0]['shape_params']['LAx'] = 9.0
    ct2 = build_pc1_case_table(cm, reg, man, ta, None, D1); assert ct2['table_sha256'] == committed['table_sha256'] and PC1_CONTRACT['tolerance']['match_rel_lt'] == 1e-5 and REQUIRED_ACTIONS['E8'] == ['glide_A', 'glide_B'] and cm['configurations'][0]['x0_CT'][0] != 999.0
    # (B) case table refuses unverified / edited maps (stale or re-stamped), and a tampered case table
    bad = copy.deepcopy(cm); bad['configurations'] = []
    with pytest.raises(InputContractError): build_pc1_case_table(bad, reg, man, ta, None, D1)
    bad = copy.deepcopy(cm); bad['configurations'].append(copy.deepcopy(bad['configurations'][40])); bad['map_sha256'] = d3._map_payload_sha(bad)
    with pytest.raises(InputContractError): build_pc1_case_table(bad, reg, man, ta, None, D1)
    t2 = copy.deepcopy(committed); t2['new_point_cases'][0]['tolerance_match_rel_lt'] = 0.25; t2['table_sha256'] = d3._table_payload_sha(t2)
    with pytest.raises(InputContractError): verify_pc1_case_table(t2, cm, reg, man, ta, None, D1)
    # (B) D-1 binding: draft without D-1 is non-formal; swapped D-1 entry (30101 <- 30102) refused; registry bytes differing from the trusted SHA refused
    draft = build_pc1_case_table(cm, reg, man, ta, None, None); assert draft['formal'] is False and draft['first_wave_anchor_cases'][0]['base_reused_from_D1'] is None and draft['table_sha256'] != ct['table_sha256']
    assert draft['counts']['unique_covariance_requests']['first_wave_bases_required'] == 27 and draft['counts']['unique_covariance_requests']['first_wave_bases_verified_for_reuse'] == 0 and ct['counts']['unique_covariance_requests']['first_wave_bases_verified_for_reuse'] == 27 and draft['counts']['unique_covariance_requests']['total_new_generations'] == 225
    import tempfile; d = tempfile.mkdtemp(); shutil.copytree(D1, d, dirs_exist_ok=True); rg = json.load(open(os.path.join(d, 'd1_cov_registry.json'))); rg['configurations']['30101'] = copy.deepcopy(rg['configurations']['30102']); rg['configurations']['30101']['config_id'] = 30101; json.dump(rg, open(os.path.join(d, 'd1_cov_registry.json'), 'w'), indent=1)
    with pytest.raises(InputContractError): build_pc1_case_table(cm, reg, man, ta, None, d)

def test_reuse_binding_schema_fields():
    s = json.load(open(os.path.join(P, 'd', 'd3_d2_reuse_binding_schema.json'))); assert s == REUSE_BINDING_SCHEMA
    for k in ('identity_kept_verbatim', 'must_match_the_D3_request', 'view_differences_allowed', 'forbidden', 'plan_sharing'): assert k in s
