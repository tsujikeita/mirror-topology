# -*- coding: utf-8 -*-
"""D-3 covariance / PC-1 generation script contracts (no physical generation in tests): fresh-only OUT; profile refusal; preflight binding stops before any generation when the
script/pins/inventory disagree; D-3 input binding (config map / case table pins) checked before generation; the sandbox self-test evidence (E7 30104: base intake PASS,
PC-1 glide_A rel 8.35e-8 match) is bound to the committed case table."""
import os, sys, json, subprocess, shutil, hashlib
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); MT = os.environ.get('B3_MT', '/home/claude/mt'); PC = os.environ.get('PHASEC_ROOT', '/home/claude/phaseC'); CT = os.environ.get('CT_PINNED', '/tmp/CMBtopology_pinned'); SCRIPT = os.path.join(P, 'd', 'd3_covgen.py')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest(); ENV = dict(os.environ, PIP_BREAK_SYSTEM_PACKAGES='1', OPENBLAS_NUM_THREADS='1')
need_ext = pytest.mark.skipif(not (os.path.exists(os.path.join(MT, 't1_engine.py')) and os.path.isdir(PC)), reason='external assets not present')

def run(out, *extra, phaseb=P, script=SCRIPT, ct=CT):
    return subprocess.run([sys.executable, script, '--mt', MT, '--phaseb', phaseb, '--phasec', PC, '--ct', ct, '--out', out, '--family', 'E7', *extra], capture_output=True, text=True, env=ENV, timeout=200)

def test_pins_bound_and_selftest_evidence():
    pins = json.load(open(os.path.join(P, 'd', 'd3_pins.json'))); cm = json.load(open(os.path.join(P, 'd', 'd3_config_map.json'))); ct = json.load(open(os.path.join(P, 'd', 'd3_pc1_case_table.json'))); inv = json.load(open(os.path.join(P, 'B2_completion_inventory.json')))
    assert pins['schema'] == 'd3_pins_v1' and pins['config_map_sha256'] == cm['map_sha256'] and pins['case_table_sha256'] == ct['table_sha256'] and pins['registry_sha256'] == cm['registry_sha256'] and pins['pc1_tolerance'] == ct['contract']['tolerance'] and pins['families'] == ['E2', 'E7', 'E8']
    assert inv['d_sha256']['d/d3_pins.json'] == sha(os.path.join(P, 'd', 'd3_pins.json')) and inv['d_sha256']['d/d3_covgen.py'] == sha(SCRIPT)
    rm = json.load(open(os.path.join(P, 'regression_logs', 'd3_selftest_sandbox_E7_30104_run_manifest.json'))); pr = json.load(open(os.path.join(P, 'regression_logs', 'd3_selftest_sandbox_E7_30104_pc1_results.json')))
    assert rm['D3_PASS'] is False and rm['stage'] == 'complete' and rm['gates']['G_env_lock'] is False and rm['gates']['G_case_table_bound'] is True and rm['n_bases'] == 1 and rm['n_cases'] == 1
    c = pr['cases']['30104:glide_A']; assert c['match'] is True and c['rel'] < 1e-5 and c['base_from'] == 'generated_here' and pr['case_table_sha256'] == ct['table_sha256'] and rm['pc1_status']['30104']['status'] == 'PC1_PASS'
    assert pr['contract']['tolerance'] == ct['contract']['tolerance']                                                                      # self-test only: not a formal PC-1 acceptance

@need_ext
def test_script_stops_before_generation_on_binding_failures(tmp_path):
    o = tmp_path / 'o'; o.mkdir(); (o / 'x').write_text('x'); assert run(str(o)).returncode == 2                                                # fresh-only OUT
    r = run(str(tmp_path / 'p'), '--profile', 'other'); assert r.returncode == 1 and json.load(open(tmp_path / 'p' / 'd3_run_manifest.json'))['failures'] == ['profile']
    # script bytes changed with the inventory unchanged -> preflight stops (no CT / no generation)
    pb2 = str(tmp_path / 'pb'); shutil.copytree(P, pb2, ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache', 'regression_logs', 'registered_assets/d2')); open(os.path.join(pb2, 'd', 'd3_covgen.py'), 'a').write('\n# comment\n')
    r = run(str(tmp_path / 'q'), '--selftest-skip-env-lock', phaseb=pb2, script=os.path.join(pb2, 'd', 'd3_covgen.py')); m = json.load(open(tmp_path / 'q' / 'd3_run_manifest.json')); assert r.returncode == 1 and m['stage'] == 'preflight' and m['gates']['G_script_sha'] is False and not os.listdir(tmp_path / 'q' / 'cov_cache')
    # case table pin changed (inventory re-stamped) -> D-3 input binding stops before generation
    pb3 = str(tmp_path / 'pb3'); shutil.copytree(P, pb3, ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache', 'regression_logs', 'registered_assets/d2')); pp = os.path.join(pb3, 'd', 'd3_pins.json'); pins = json.load(open(pp)); pins['case_table_sha256'] = '0' * 64; json.dump(pins, open(pp, 'w'), indent=1)
    ip = os.path.join(pb3, 'B2_completion_inventory.json'); inv = json.load(open(ip)); inv['d_sha256']['d/d3_pins.json'] = sha(pp); json.dump(inv, open(ip, 'w'), indent=1)
    r = run(str(tmp_path / 's'), '--selftest-skip-env-lock', '--selftest-configs', '30104', phaseb=pb3, script=os.path.join(pb3, 'd', 'd3_covgen.py')); m = json.load(open(tmp_path / 's' / 'd3_run_manifest.json')); assert r.returncode == 1 and m['stage'] == 'd3_inputs' and m['gates']['G_case_table_bound'] is False and not os.listdir(tmp_path / 's' / 'cov_cache')
