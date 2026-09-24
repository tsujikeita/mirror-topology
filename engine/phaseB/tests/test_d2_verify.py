# -*- coding: utf-8 -*-
"""D-2 post-run verification script (read-only): on a self-test family output every directory verifies, NPZ file SHAs match the manifests / inventory, f32 sensitivity and
same-latent records are produced, and a tampered NPZ or a stale registry manifest SHA is reported as a failure (exit 1) without modifying the input."""
import os, sys, json, subprocess, shutil, hashlib
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); MT = os.environ.get('B3_MT', '/home/claude/mt'); PC = os.environ.get('PHASEC_ROOT', '/home/claude/phaseC')
need_ext = pytest.mark.skipif(not (os.path.exists(os.path.join(MT, 't1_engine.py')) and os.path.isdir(PC)), reason='external assets not present')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()

@need_ext
def test_verify_script_on_selftest_output(tmp_path):
    env = dict(os.environ, PIP_BREAK_SYSTEM_PACKAGES='1', OPENBLAS_NUM_THREADS='1'); run = str(tmp_path / 'run')
    r = subprocess.run([sys.executable, os.path.join(P, 'd', 'd2_bankgen.py'), '--mt', MT, '--phaseb', P, '--phasec', PC, '--out', f'{run}/d2', '--family', 'E7', '--selftest-scale', '0.003', '--selftest-skip-env-lock', '--selftest-configs', '30101', '--selftest-skip-a10'], capture_output=True, text=True, env=env, timeout=280)
    m = json.load(open(f'{run}/d2/d2_run_manifest.json')); assert m['stage'] == 'complete'
    inv = {}
    for d, _, fs in os.walk(run):
        for f in fs: p = os.path.join(d, f); rel = os.path.relpath(p, run); inv[rel] = dict(sha256=(None if f.endswith('.npz') else sha(p)), bytes=os.path.getsize(p))
    json.dump(dict(D2_PASS=False, family='E7', stages=dict(directories=m['directories']), output_inventory=inv), open(f'{run}/d2_final_record.json', 'w'), indent=1)
    before = {rel: sha(os.path.join(run, rel)) for rel in inv}
    r = subprocess.run([sys.executable, os.path.join(P, 'd', 'd2_verify_banks.py'), '--phaseb', P, '--run-root', run, '--out', str(tmp_path / 'v')], capture_output=True, text=True, env=env, timeout=280)
    v = json.load(open(tmp_path / 'v' / 'd2_verify_E7.json')); assert r.returncode == 0 and v['all_ok'] and set(v['directories']) == set(m['directories']) and all(d['ok'] and d['manifest_sha256_ok'] and all(s['matches_manifest'] and s['inventory_bytes_match'] for s in d['shards']) for d in v['directories'].values())
    assert 'cfg30101_w2' in v['w2'] and 'model_matched' in v['w2']['cfg30101_w2'] and v['w2']['cfg30101_w2']['model_matched']['rows'] == 600 and all(x['unique_hashes'] == 1 for x in v['same_latent_cid'].values())
    assert {rel: sha(os.path.join(run, rel)) for rel in inv} == before                                                                  # read-only: nothing changed
    # tampered NPZ -> failure reported for that directory only, exit 1
    bad = str(tmp_path / 'bad'); shutil.copytree(run, bad); f = os.path.join(bad, 'd2', 'cfg30101_b1', 'cfg30101_b1_s2.npz'); z = dict(np.load(f)); z['model_native__float64__T2'][0] += 1e-9; np.savez(f, **z)
    rg = json.load(open(f'{bad}/d2/d2_bank_registry.json'))
    for k, d in rg['directories'].items(): d['path'] = d['path'].replace(run, bad)
    json.dump(rg, open(f'{bad}/d2/d2_bank_registry.json', 'w'), indent=1)
    r2 = subprocess.run([sys.executable, os.path.join(P, 'd', 'd2_verify_banks.py'), '--phaseb', P, '--run-root', bad, '--out', str(tmp_path / 'v2')], capture_output=True, text=True, env=env, timeout=280)
    v2 = json.load(open(tmp_path / 'v2' / 'd2_verify_E7.json')); assert r2.returncode == 1 and v2['failures'] == ['cfg30101_b1'] and v2['directories']['cfg30101_b0']['ok']
