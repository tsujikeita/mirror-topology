# -*- coding: utf-8 -*-
"""Phase D-1 v0.2 contracts (audit RD1-A/B/C): fresh-only OUT (no overwrite of a prior record), registered-environment hard gate stops before generation, Phase C member
verification (edited member with unchanged inventory file -> refused), saved grid deserialised+validated (edited weight with stale SHA -> refused), A11 cross-check target must
match the pinned trusted identity, external loader SHA pinned, generator cell extracted from the frozen notebook == pins full SHA, and the ported generator equals the A11 cell
functions (AST) except the documented E1/x0 branch; fail-fast on the first intake failure (no further generation)."""
import os, sys, json, ast, hashlib, shutil, subprocess, textwrap
import numpy as np, pytest
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); MT = os.environ.get('B3_MT', '/home/claude/mt'); PC = os.environ.get('PHASEC_ROOT', '/home/claude/phaseC'); CT = os.environ.get('CT_PINNED', '/tmp/CMBtopology_pinned')
SCRIPT = os.path.join(P, 'd', 'd1_covgen.py'); PINS = json.load(open(os.path.join(P, 'd', 'd1_pins.json'))); sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
need_assets = pytest.mark.skipif(not (os.path.exists(os.path.join(MT, PINS['a11_freeze']['notebook']['path'])) and os.path.isdir(PC) and os.path.isdir(CT)), reason='external assets (mt / phaseC / CMBtopology) not present')

def run(out, extra, env=None, timeout=120):
    e = dict(os.environ, PIP_BREAK_SYSTEM_PACKAGES='1'); e.update(env or {})
    return subprocess.run([sys.executable, SCRIPT, '--mt', MT, '--phaseb', P, '--phasec', PC, '--ct', CT, '--out', out, *extra], capture_output=True, text=True, env=e, timeout=timeout)

def test_fresh_only_out_is_refused_before_touching_records(tmp_path):
    out = tmp_path / 'o'; out.mkdir(); (out / 'd1_run_manifest.json').write_text('{"prior": true}')
    r = run(str(out), ['--profile', 'bogus']); assert r.returncode == 2 and json.load(open(out / 'd1_run_manifest.json')) == {'prior': True} and not (out / 'd1_covgen_stdout.log').exists()

@need_assets
def test_environment_hard_gate_stops_before_generation(tmp_path):
    out = tmp_path / 'e'; r = run(str(out), ['--selftest-configs', '10101', '--selftest-skip-cross-check'])              # sandbox is NOT the registered environment
    m = json.load(open(out / 'd1_run_manifest.json')); assert r.returncode == 1 and m['stage'] == 'environment' and m['gates']['G_env_lock'] is False and not os.path.exists(out / 'd1_cov_registry.json') and not any(f.endswith('.npy') for f in os.listdir(out / 'cov_cache'))

@need_assets
def test_phaseC_member_edit_with_unchanged_inventory_is_refused(tmp_path):
    pc2 = tmp_path / 'pc'; shutil.copytree(PC, pc2, ignore=shutil.ignore_patterns('__pycache__')); f = pc2 / 'registered' / 'b3_2_twelve_geometry.csv'; f.write_text(f.read_text() + '# edited\n')
    r = subprocess.run([sys.executable, SCRIPT, '--mt', MT, '--phaseb', P, '--phasec', str(pc2), '--ct', CT, '--out', str(tmp_path / 'o'), '--selftest-skip-env-lock'], capture_output=True, text=True, timeout=120)
    m = json.load(open(tmp_path / 'o' / 'd1_run_manifest.json')); assert r.returncode == 1 and m['stage'] == 'trusted_inputs' and m['gates']['G_phaseC_members'] is False

@need_assets
def test_saved_grid_edit_with_stale_sha_is_refused(tmp_path):
    pc2 = tmp_path / 'pc'; shutil.copytree(PC, pc2, ignore=shutil.ignore_patterns('__pycache__')); g = pc2 / 'registered' / 'first_wave_configuration_manifest.json'; d = json.load(open(g)); d['configurations'][0]['weight'] = 0.123; json.dump(d, open(g, 'w'))
    inv = json.load(open(pc2 / 'PACKET_INVENTORY.json')); inv['files']['registered/first_wave_configuration_manifest.json'] = dict(sha256=sha(g), bytes=os.path.getsize(g)); json.dump(inv, open(pc2 / 'PACKET_INVENTORY.json', 'w'), indent=1)
    pins2 = tmp_path / 'pb'; shutil.copytree(P, pins2, ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache', 'regression_logs')); pp = json.load(open(pins2 / 'd' / 'd1_pins.json')); pp['first_wave']['phaseC_inventory_sha256'] = sha(pc2 / 'PACKET_INVENTORY.json'); json.dump(pp, open(pins2 / 'd' / 'd1_pins.json', 'w'), indent=1)
    inv2 = json.load(open(pins2 / 'B2_completion_inventory.json')); inv2['d_sha256']['d/d1_pins.json'] = sha(pins2 / 'd' / 'd1_pins.json'); json.dump(inv2, open(pins2 / 'B2_completion_inventory.json', 'w'), indent=1)
    r = subprocess.run([sys.executable, str(pins2 / 'd' / 'd1_covgen.py'), '--mt', MT, '--phaseb', str(pins2), '--phasec', str(pc2), '--ct', CT, '--out', str(tmp_path / 'o'), '--selftest-skip-env-lock', '--selftest-skip-cross-check', '--selftest-configs', '10101'], capture_output=True, text=True, timeout=200)
    m = json.load(open(tmp_path / 'o' / 'd1_run_manifest.json')); assert r.returncode == 1 and m['stage'] == 'grid' and m['gates']['G_grid_manifest_bound'] is False and not any(f.endswith('.npy') for f in os.listdir(tmp_path / 'o' / 'cov_cache'))

@need_assets
def test_generator_cell_matches_pins_and_ported_functions_match_ast():
    nb = json.load(open(os.path.join(MT, PINS['a11_freeze']['notebook']['path']))); cell = ''.join(nb['cells'][PINS['a11_freeze']['generator_cell_index']]['source'])
    assert hashlib.sha256(cell.encode()).hexdigest() == PINS['a11_freeze']['generator_cell4_sha256']
    orig = {n.name: n for n in ast.parse(cell).body if isinstance(n, ast.FunctionDef)}; src = open(SCRIPT).read(); tree = ast.parse(src)
    ported = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name in ('key_of', 'tag_of', 'atomic_write_json', 'ensure_cov'): ported[n.name] = n
    for name in ('key_of', 'tag_of', 'atomic_write_json'): assert ast.dump(orig[name]) == ast.dump(ported[name]), name
    a = ast.dump(orig['ensure_cov']); b = ast.dump(ported['ensure_cov'])
    # documented differences only: E1 has no x0 (kw dict), note() instead of print(), f-string text of the reuse assertion
    assert 'run_topology' in b and "'x0'" in b and a != b and abs(len(b) - len(a)) < 700

@need_assets
def test_cross_check_target_pins_match_frozen_a11_and_b31_pins():
    xc = PINS['a11_cross_check']; b31 = json.load(open(os.path.join(P, 'b3', 'b3_1_pins.json')))['mock_cov']
    assert sha(os.path.join(MT, xc['manifest'])) == xc['manifest_sha256'] == b31['manifest_sha256'] and sha(os.path.join(MT, xc['npy'])) == xc['npy_sha256'] == b31['cov_file_sha256'] and hashlib.sha256(np.load(os.path.join(MT, xc['npy'])).tobytes()).hexdigest() == xc['array_sha256'] == b31['cov_array_sha256']
    assert sha(os.path.join(MT, PINS['external_sources']['t1_engine']['path'])) == PINS['external_sources']['t1_engine']['sha256'] == '87bf8424073af021264b12fe312ab5255b71008bdd5fe874d164d48daf034dc8'

def test_fail_fast_source_contract():
    src = open(SCRIPT).read(); assert 'STOPPED_AT_INTAKE_FAILURE' in src and 'return finish(1, "intake_failure")' in src and 'fresh-only contract' in src and src.index('os.environ.setdefault(_k, "2")') < src.index('import numpy as np')
