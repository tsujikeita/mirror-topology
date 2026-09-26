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
    rm = json.load(open(os.path.join(P, 'regression_logs', 'd3_selftest_v4_sandbox_E7_30104_run_manifest.json'))); pr = json.load(open(os.path.join(P, 'regression_logs', 'd3_selftest_v4_sandbox_E7_30104_pc1_results.json'))); ev = json.load(open(os.path.join(P, 'regression_logs', 'd3_selftest_v4_sandbox_E7_30104_partial_evidence.json')))
    assert rm['D3_PASS'] is False and rm['stage'] == 'complete' and rm['gates']['G_env_lock'] is False and set(rm['gates']) == set(rm['required_inventory']) and len(rm['gates']) == 21 and rm['n_bases'] == 1
    assert rm['partition'] == dict(sizes=['L1.00'], new_point_cases=1, anchor_cases=0, required_new_point_cases_family=27, required_anchor_cases_family=9) and rm['selection']['selftest_configs'] == [30104] and rm['selection']['selftest_skip_anchors'] is True   # self-test scope (anchors omitted by flag); formal partitions include anchors
    c = pr['cases']['30104:glide_A']; assert c['evaluation'] == 'EVALUATED' and c['match'] is True and c['rel'] < 1e-5 and c['clone_identity']['loader_meta_sha'] == c['clone_identity']['array_sha256'] and c['D_orthogonality'] < 1e-10 and c['base_from'] == 'generated_here'
    assert all(pr['representation']['gates'].values()) and set(pr['representation']['gates']) == {'G_quadrature_orthonormal', 'G_real_basis_bridge', 'G_D_orthogonal_all_used', 'G_D_direct_geometry_complex_path', 'G_D_homomorphism', 'G_reflection_D_analytic'} and pr['case_table_sha256'] == ct['table_sha256']
    assert rm['source']['script_sha256'] == sha(SCRIPT) and rm['source']['pins_sha256'] == sha(os.path.join(P, 'd', 'd3_pins.json')) and rm['source']['engine_version'] == json.load(open(os.path.join(P, 'B2_completion_inventory.json')))['engine_version'] and rm['published_evidence']['value_level_readback_ok'] is True and set(rm['published_evidence']['documents']) == {'d3_cov_registry.json', 'd3_pc1_results.json', 'd3_partial_evidence.json', 'd3_env_lock.json'}   # record of the FINAL script / pins bytes (inventory itself changes with reports/tests)
    # the self-test evidence is an intake-able run snapshot except for its self-test selection (refused as a formal partition)
    import tempfile, shutil as _sh; d = os.path.join(tempfile.mkdtemp(), 'run'); os.makedirs(os.path.join(d, 'cov_cache'))
    for f in ('run_manifest', 'pc1_results', 'partial_evidence', 'cov_registry', 'env_lock'): _sh.copy(os.path.join(P, 'regression_logs', f'd3_selftest_v4_sandbox_E7_30104_{f}.json'), os.path.join(d, f'd3_{f}.json'))
    from step1_engine.d3_stage import verify_partition_run
    with pytest.raises(InputContractError): verify_partition_run(d, dict(rm['source']), ct['table_sha256'], cm['map_sha256'], require_arrays=False)
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

def test_formal_aggregation_refuses_raw_dicts():
    """The formal aggregator accepts only VerifiedPartition instances produced by verify_partition_run (see tests/test_d3_partition_intake.py for the intake / aggregation contracts)."""
    ct = json.load(open(os.path.join(P, 'd', 'd3_pc1_case_table.json'))); src = dict(engine_version='0.86.0', inventory_sha256='i' * 64, script_sha256='s' * 64, pins_sha256='p' * 64)
    raw = dict(run_manifest=dict(D3_PASS=True, stage='complete', failures=[]), registry={}, pc1_results={})
    with pytest.raises(InputContractError): aggregate_partitions(ct, 'E7', [raw], src, ct['table_sha256'])
    with pytest.raises(InputContractError): aggregate_partitions(ct, 'E7', [], src, ct['table_sha256'])
    with pytest.raises(InputContractError): aggregate_partitions(ct, 'E1', [], src, ct['table_sha256'])
