# -*- coding: utf-8 -*-
"""D-3 covariance / PC-1 generation script contracts v2 (no physical generation in tests): fresh-only OUT; profile refusal; preflight / D-3 input binding stop before generation;
invalid / empty selections refused; the partition aggregator (anchor coverage, disjointness, self-test exclusion, case-set equality); the sandbox self-test evidence bound to the
committed case table (v0.85 script: base intake PASS, PC-1 rel 8.35e-8, representation battery gates, bound clone identity, partial evidence COMPLETE)."""
import os, sys, json, subprocess, shutil, hashlib, copy
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine.d3_stage import aggregate_partitions
from step1_engine.errors import InputContractError
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); MT = os.environ.get('B3_MT', '/home/claude/mt'); PC = os.environ.get('PHASEC_ROOT', '/home/claude/phaseC'); CT = os.environ.get('CT_PINNED', '/tmp/CMBtopology_pinned'); SCRIPT = os.path.join(P, 'd', 'd3_covgen.py')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest(); ENV = dict(os.environ, PIP_BREAK_SYSTEM_PACKAGES='1', OPENBLAS_NUM_THREADS='1')
need_ext = pytest.mark.skipif(not (os.path.exists(os.path.join(MT, 't1_engine.py')) and os.path.isdir(PC)), reason='external assets not present')

def run(out, *extra, phaseb=P, script=SCRIPT, ct=CT):
    return subprocess.run([sys.executable, script, '--mt', MT, '--phaseb', phaseb, '--phasec', PC, '--ct', ct, '--out', out, '--family', 'E7', *extra], capture_output=True, text=True, env=ENV, timeout=200)

def test_pins_bound_and_selftest_evidence():
    pins = json.load(open(os.path.join(P, 'd', 'd3_pins.json'))); cm = json.load(open(os.path.join(P, 'd', 'd3_config_map.json'))); ct = json.load(open(os.path.join(P, 'd', 'd3_pc1_case_table.json'))); inv = json.load(open(os.path.join(P, 'B2_completion_inventory.json')))
    assert pins['schema'] == 'd3_pins_v1' and pins['config_map_sha256'] == cm['map_sha256'] and pins['case_table_sha256'] == ct['table_sha256'] and pins['pc1_tolerance'] == ct['contract']['tolerance'] and inv['d_sha256']['d/d3_covgen.py'] == sha(SCRIPT)
    rm = json.load(open(os.path.join(P, 'regression_logs', 'd3_selftest_v3_sandbox_E7_30104_run_manifest.json'))); pr = json.load(open(os.path.join(P, 'regression_logs', 'd3_selftest_v3_sandbox_E7_30104_pc1_results.json'))); ev = json.load(open(os.path.join(P, 'regression_logs', 'd3_selftest_v3_sandbox_E7_30104_partial_evidence.json')))
    assert rm['D3_PASS'] is False and rm['stage'] == 'complete' and rm['gates']['G_env_lock'] is False and set(rm['gates']) == set(rm['required_inventory']) and len(rm['gates']) == 21 and rm['n_bases'] == 1
    assert rm['partition'] == dict(sizes=['L1.00'], new_point_cases=1, anchor_cases=0, required_new_point_cases_family=27, required_anchor_cases_family=9) and rm['selection']['selftest_configs'] == [30104] and rm['selection']['selftest_skip_anchors'] is True   # self-test scope (anchors omitted by flag); formal partitions include anchors
    c = pr['cases']['30104:glide_A']; assert c['evaluation'] == 'EVALUATED' and c['match'] is True and c['rel'] < 1e-5 and c['clone_identity']['loader_meta_sha'] == c['clone_identity']['array_sha256'] and c['D_orthogonality'] < 1e-10 and c['base_from'] == 'generated_here'
    assert all(pr['representation']['gates'].values()) and set(pr['representation']['gates']) == {'G_quadrature_orthonormal', 'G_real_basis_bridge', 'G_D_orthogonal_all_used', 'G_D_direct_geometry_complex_path', 'G_D_homomorphism', 'G_reflection_D_analytic'} and pr['case_table_sha256'] == ct['table_sha256']
    assert rm['source']['script_sha256'] == sha(SCRIPT) and rm['source']['pins_sha256'] == sha(os.path.join(P, 'd', 'd3_pins.json')) and rm['source']['engine_version'] == json.load(open(os.path.join(P, 'B2_completion_inventory.json')))['engine_version'] and rm['published_evidence']['value_level_readback_ok'] is True   # record of the FINAL script / pins bytes (inventory itself changes with reports/tests)
    assert ev['status'] == 'COMPLETE' and set(ev['cases']) == set(pr['cases']) and all(pr['cases'][k]['evaluation'] == 'EVALUATED' for k in pr['cases']) and rm['pc1_status']['30104']['status'] == 'PC1_PASS'

@need_ext
def test_script_stops_before_generation_on_binding_failures_and_invalid_selection(tmp_path):
    o = tmp_path / 'o'; o.mkdir(); (o / 'x').write_text('x'); assert run(str(o)).returncode == 2
    r = run(str(tmp_path / 'p'), '--profile', 'other'); assert r.returncode == 1 and json.load(open(tmp_path / 'p' / 'd3_run_manifest.json'))['failures'] == ['profile']
    pb2 = str(tmp_path / 'pb'); shutil.copytree(P, pb2, ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache', 'regression_logs', 'registered_assets/d2')); open(os.path.join(pb2, 'd', 'd3_covgen.py'), 'a').write('\n# comment\n')
    r = run(str(tmp_path / 'q'), '--selftest-skip-env-lock', phaseb=pb2, script=os.path.join(pb2, 'd', 'd3_covgen.py')); m = json.load(open(tmp_path / 'q' / 'd3_run_manifest.json')); assert r.returncode == 1 and m['stage'] == 'preflight' and not os.listdir(tmp_path / 'q' / 'cov_cache')
    pb3 = str(tmp_path / 'pb3'); shutil.copytree(P, pb3, ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache', 'regression_logs', 'registered_assets/d2')); pp = os.path.join(pb3, 'd', 'd3_pins.json'); pins = json.load(open(pp)); pins['case_table_sha256'] = '0' * 64; json.dump(pins, open(pp, 'w'), indent=1)
    ip = os.path.join(pb3, 'B2_completion_inventory.json'); inv = json.load(open(ip)); inv['d_sha256']['d/d3_pins.json'] = sha(pp); json.dump(inv, open(ip, 'w'), indent=1)
    r = run(str(tmp_path / 's'), '--selftest-skip-env-lock', '--selftest-configs', '30104', phaseb=pb3, script=os.path.join(pb3, 'd', 'd3_covgen.py')); m = json.load(open(tmp_path / 's' / 'd3_run_manifest.json')); assert r.returncode == 1 and m['stage'] == 'd3_inputs' and not os.listdir(tmp_path / 's' / 'cov_cache')
    # invalid / empty selections are refused before generation (exit 2)
    for extra in (['--selftest-configs', '99999'], ['--selftest-configs', '30104,99999'], ['--sizes', 'L9.99'], ['--sizes', ''], ['--sizes', 'L1.00,L1.00']):
        d = tmp_path / ('sel_' + hashlib.sha1(str(extra).encode()).hexdigest()[:6]); r = run(str(d), '--selftest-skip-env-lock', *extra); m = json.load(open(d / 'd3_run_manifest.json')); assert r.returncode == 2 and m['stage'] == 'selection' and not os.listdir(d / 'cov_cache')

def _fake_run(ct, family, sizes, selftest=False, drop_case=None, extra_case=None, pass_=True, src=None, gates_ok=True, env='e' * 64, mut=None):
    new = [c for c in ct['new_point_cases'] if c['family'] == family and (sizes is None or c['size_id'] in sizes)]; anc = [c for c in ct['first_wave_anchor_cases'] if c['family'] == family and (sizes is None or c['size_id'] in sizes)]
    tol = ct['contract']['tolerance']['match_rel_lt']
    cases = {c['case_id']: dict(case_id=c['case_id'], config_id=c['config_id'], action=c['action'], evaluation='EVALUATED', match=True, rel=1e-8, tolerance_match_rel_lt=tol) for c in new + anc}
    if drop_case: cases.pop(drop_case)
    if extra_case: cases[extra_case] = dict(case_id=extra_case, config_id=30199, action='glide_A', evaluation='EVALUATED', match=True, rel=1e-8, tolerance_match_rel_lt=tol)
    from step1_engine.d3_stage import REQUIRED_ACTIONS, REQUIRED_D3A_GATES
    status = {}
    for c in new:
        rs = [v for v in cases.values() if v.get('config_id') == c['config_id']]; status[str(c['config_id'])] = dict(actions_required=REQUIRED_ACTIONS[family], actions_evaluated=sorted(x['action'] for x in rs), status=('PC1_PASS' if sorted(x['action'] for x in rs) == sorted(REQUIRED_ACTIONS[family]) and all(x['match'] for x in rs) else 'PC1_PENDING'), max_rel=max(x['rel'] for x in rs) if rs else None)
    for c in anc:
        rs = [v for v in cases.values() if v.get('config_id') == c['config_id']]
        if rs: status[str(c['config_id'])] = dict(actions_required=REQUIRED_ACTIONS[family], actions_evaluated=sorted(x['action'] for x in rs), status=('PC1_PASS' if sorted(x['action'] for x in rs) == sorted(REQUIRED_ACTIONS[family]) and all(x['match'] for x in rs) else 'PC1_PENDING'), max_rel=max(x['rel'] for x in rs))
    src = src or SRC; bases = {str(c['config_id']): {} for c in new}
    rr = dict(run_manifest=dict(D3_PASS=pass_, stage='complete', failures=[], family=family, gates={g: (True if gates_ok else (g != 'G_env_lock')) for g in REQUIRED_D3A_GATES}, source=dict(src, profile='production_official'), selection=dict(sizes=sizes, selftest_configs=([30104] if selftest else None), selftest_skip_anchors=False), env_lock=dict(env_fingerprint=env)),
              registry=dict(family=family, case_table_sha256=ct['table_sha256'], env_fingerprint=env, configurations=bases), pc1_results=dict(family=family, case_table_sha256=ct['table_sha256'], cases=cases, configuration_status=status))
    if mut: mut(rr)
    return rr

SRC = dict(engine_version='0.86.0', inventory_sha256='i' * 64, script_sha256='s' * 64, pins_sha256='p' * 64)

def test_partition_aggregator_formal():
    ct = json.load(open(os.path.join(P, 'd', 'd3_pc1_case_table.json'))); runs = lambda **kw: [_fake_run(ct, 'E7', ['L1.00'], **kw), _fake_run(ct, 'E7', ['L1.20']), _fake_run(ct, 'E7', ['L1.50'])]
    agg = aggregate_partitions(ct, 'E7', runs(), SRC); assert agg['family_coverage_complete'] and agg['n_cases'] == 36 and agg['n_anchor_cases'] == 9 and agg['n_bases'] == 27 and agg['partitions'] == 3 and agg['n_pc1_pass'] == 36
    assert aggregate_partitions(ct, 'E8', [_fake_run(ct, 'E8', None)], SRC)['n_cases'] == 72
    # detached output
    r3 = runs(); agg = aggregate_partitions(ct, 'E7', r3, SRC); agg['configuration_status']['30104']['status'] = 'X'; assert r3[0]['pc1_results']['configuration_status']['30104']['status'] == 'PC1_PASS'
    # finite PC1_FAIL carried through (coverage complete, status FAIL, summary re-derived consistently)
    def fail_mut(rr):
        v = rr['pc1_results']['cases']['30104:glide_A']; v['rel'] = 1.0; v['match'] = False; rr['pc1_results']['configuration_status']['30104'].update(status='PC1_FAIL', max_rel=1.0)
    agg = aggregate_partitions(ct, 'E7', runs(mut=fail_mut), SRC); assert agg['n_pc1_fail'] == 1 and agg['configuration_status']['30104']['status'] == 'PC1_FAIL'
    bad = {
        'size_missing': lambda: [_fake_run(ct, 'E7', ['L1.00']), _fake_run(ct, 'E7', ['L1.20'])],
        'overlap': lambda: [_fake_run(ct, 'E7', ['L1.00']), _fake_run(ct, 'E7', ['L1.00', 'L1.20']), _fake_run(ct, 'E7', ['L1.50'])],
        'anchor_missing': lambda: runs(drop_case='30101:glide_A'), 'selftest': lambda: runs(selftest=True), 'not_pass': lambda: runs(pass_=False), 'extra_case': lambda: [_fake_run(ct, 'E7', None, extra_case='30199:glide_A')],
        'other_source': lambda: runs(src=dict(SRC, engine_version='0.85.0')), 'gate_false': lambda: runs(gates_ok=False), 'env_mismatch': lambda: runs(mut=lambda rr: rr['registry'].update(env_fingerprint='f' * 64)),
        'family_swap': lambda: runs(mut=lambda rr: rr['run_manifest'].update(family='E8')), 'table_sha': lambda: runs(mut=lambda rr: rr['pc1_results'].update(case_table_sha256='0' * 64)),
        'empty_status': lambda: runs(mut=lambda rr: rr['pc1_results'].update(configuration_status={})), 'stale_summary': lambda: runs(mut=lambda rr: rr['pc1_results']['cases']['30104:glide_A'].update(rel=1.0, match=False)),
        'nan_rel': lambda: runs(mut=lambda rr: rr['pc1_results']['cases']['30104:glide_A'].update(rel=float('nan'))), 'wrong_config': lambda: runs(mut=lambda rr: rr['pc1_results']['cases']['30104:glide_A'].update(config_id=30105)),
        'moved_case': lambda: (lambda a, b: (a['pc1_results']['cases'].__setitem__('30201:glide_A', b['pc1_results']['cases'].pop('30201:glide_A')), [a, b, _fake_run(ct, 'E7', ['L1.50'])])[1])(_fake_run(ct, 'E7', ['L1.00']), _fake_run(ct, 'E7', ['L1.20'])),
        'dup_size': lambda: [_fake_run(ct, 'E7', ['L1.00', 'L1.00']), _fake_run(ct, 'E7', ['L1.20']), _fake_run(ct, 'E7', ['L1.50'])], 'no_runs': lambda: [],
    }
    for name, mk in bad.items():
        with pytest.raises(InputContractError): aggregate_partitions(ct, 'E7', mk(), SRC)
    with pytest.raises(InputContractError): aggregate_partitions(ct, 'E1', [], SRC)                                                                                         # not applicable, never complete
    t2 = copy.deepcopy(ct); t2['formal'] = False; t2['table_sha256'] = __import__('step1_engine.d3_stage', fromlist=['_table_payload_sha'])._table_payload_sha(t2)
    with pytest.raises(InputContractError): aggregate_partitions(t2, 'E7', runs(), SRC)
