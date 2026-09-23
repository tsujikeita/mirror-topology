# -*- coding: utf-8 -*-
"""D-2 tranche 3b: W2 position bank generation (purpose w2_independent; per-position group; both paths; matched root only) and its strong intake (identity, root, whitening
identity == registered shared null; a different mu/W identity refused); generation script contracts (preflight order, fresh-only OUT, family selection, registry, reuse-root
re-verification, partial registry on failure)."""
import os, sys, json, subprocess, shutil, hashlib
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from step1_engine.d2_bank import load_bank_spec, generate_w2_position_bank, intake_w2_position_bank, CallInventory, verify_bank_dir, SHARED_NULL, registered_whitening
from step1_engine.d2_rng import load_crn_table
from step1_engine.errors import InputContractError
from test_d2_tranche2 import _Kern, _ctx
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); MT = os.environ.get('B3_MT', '/home/claude/mt'); PC = os.environ.get('PHASEC_ROOT', '/home/claude/phaseC'); SPEC = os.path.join(P, 'd', 'd2_bank_spec.json'); SCRIPT = os.path.join(P, 'd', 'd2_bankgen.py')
need_ext = pytest.mark.skipif(not (os.path.exists(os.path.join(MT, 't1_engine.py')) and os.path.isdir(PC)), reason='external assets not present')

def test_w2_position_bank_generation_and_intake(tmp_path):
    reg, man, t, R, d1 = _ctx(); spec = load_bank_spec(SPEC, table=t); k = _Kern(); inv = CallInventory(); S = np.eye(21) * 1.05
    d = str(tmp_path / 'w2'); m = generate_w2_position_bank(k, R, t, spec, 30101, S, d, inv, scale=0.01, chunk_clusters=5)
    assert m['purpose'] == 'w2_independent' and m['crn_group'] == 60101 and m['n_clusters'] == 20 and m['selections'] == ['float64', 'float32'] and m['roles'] == ['model_matched'] and inv.calls[-1]['key_gaussian'][2] == 600 and verify_bank_dir(d)['manifest_sha256'] == m['manifest_sha256']
    with pytest.raises(InputContractError): generate_w2_position_bank(k, R, t, spec, 10101, S, str(tmp_path / 'e1'), inv, scale=0.01)                      # E1 has no W2 position
    with pytest.raises(InputContractError): generate_w2_position_bank(k, R, t, spec, 30101, S + 2j * np.eye(21), str(tmp_path / 'cx'), inv, scale=0.01)      # complex root refused before conversion
    d2 = str(tmp_path / 'w2b'); generate_w2_position_bank(k, R, t, spec, 30102, S, d2, inv, scale=0.01, chunk_clusters=5)
    z1, z2 = np.load(os.path.join(d, 'cfg30101_w2_s0.npz')), np.load(os.path.join(d2, 'cfg30102_w2_s0.npz')); assert not np.array_equal(z1['model_matched__float64__T1'], z2['model_matched__float64__T1'])   # positions have their own latent
    rw = registered_whitening(); mu, W = rw['mu'], rw['W']                                                                                    # the REGISTERED values (bound by file/payload SHA)
    b64, b32, info = intake_w2_position_bank(30101, d, S, mu, W, dict(SHARED_NULL), formal=False); assert b64.K == 20 and b32.K == 20 and b64.Tw.shape == (2000, 2) and np.allclose(b64.Tw, (np.c_[z1['model_matched__float64__T1'], z1['model_matched__float64__T2']] - mu) @ W.T)
    with pytest.raises(InputContractError): intake_w2_position_bank(30101, d, S, mu, W, dict(SHARED_NULL, asset_sha256='0' * 64), formal=False)               # whitening identity must be the registered one
    with pytest.raises(InputContractError): intake_w2_position_bank(30101, d, S * 1.01, mu, W, dict(SHARED_NULL), formal=False)                               # root mismatch
    with pytest.raises(InputContractError): intake_w2_position_bank(30101, d, S, mu, W, dict(SHARED_NULL), formal=True)                                        # self-test bank not formal
    with pytest.raises(InputContractError): intake_w2_position_bank(30101, d, S, mu, W, dict(SHARED_NULL), formal=None)                                        # strict bool
    for bad_mu, bad_W in ((mu + 1.0, W), (mu, 2 * W), (mu, np.zeros((2, 2))), (mu + 1j, W), (mu, W + 1j)):                                                        # values, not just the identifier, are bound
        with pytest.raises(InputContractError): intake_w2_position_bank(30101, d, S, bad_mu, bad_W, dict(SHARED_NULL), formal=False)

@need_ext
def test_generation_script_contracts(tmp_path):
    env = dict(os.environ, PIP_BREAK_SYSTEM_PACKAGES='1', OPENBLAS_NUM_THREADS='1')
    def run(out, *extra): return subprocess.run([sys.executable, SCRIPT, '--mt', MT, '--phaseb', P, '--phasec', PC, '--out', out, '--family', 'E7', *extra], capture_output=True, text=True, env=env, timeout=280)
    o = tmp_path / 'o'; o.mkdir(); (o / 'x').write_text('x'); assert run(str(o)).returncode == 2                                                                   # fresh-only OUT
    r = run(str(tmp_path / 'env'), '--selftest-scale', '0.001', '--selftest-configs', '30101', '--selftest-skip-a10'); m = json.load(open(tmp_path / 'env' / 'd2_run_manifest.json'))
    assert r.returncode == 1 and m['stage'] == 'environment' and m['directories'] == {}                                                                            # env hard gate stops before generation (sandbox)
    r = run(str(tmp_path / 'ok'), '--selftest-scale', '0.001', '--selftest-configs', '30101', '--selftest-skip-a10', '--selftest-skip-env-lock'); m = json.load(open(tmp_path / 'ok' / 'd2_run_manifest.json'))
    assert m['stage'] == 'complete' and m['D2_PASS'] is False and m['gates']['G_all_configurations'] is True and r.returncode == 1                    # env gate False (sandbox) -> exit 1 even when the self-test completes; never D2_PASS and set(m['directories']) == {'ref_E7_b0', 'ref_E7_b1', 'ref_E7_fit', 'cfg30101_b0', 'cfg30101_b1', 'cfg30101_fit', 'cfg30101_w2'}
    assert set(m['directories']) == {'ref_E7_b0', 'ref_E7_b1', 'ref_E7_fit', 'cfg30101_b0', 'cfg30101_b1', 'cfg30101_fit', 'cfg30101_w2'}
    regj = json.load(open(tmp_path / 'ok' / 'd2_bank_registry.json')); assert regj['formal'] is False and len(regj['calls']) == 7 and all(c['key_gaussian'][0] == 20260912 for c in regj['calls']) and len(regj['ledger']) == 7 and set(regj['required_requests']) == set(m['directories'])
    for name, v in m['directories'].items(): assert verify_bank_dir(v['path'])['manifest_sha256'] == v['manifest_sha256']
    # reuse-root: completed directories are re-verified and reused (no regeneration), a tampered one is refused (script fails, partial registry saved)
    r2 = run(str(tmp_path / 'reuse'), '--selftest-scale', '0.001', '--selftest-configs', '30101', '--selftest-skip-a10', '--selftest-skip-env-lock', '--reuse-root', str(tmp_path / 'ok')); m2 = json.load(open(tmp_path / 'reuse' / 'd2_run_manifest.json'))
    assert m2['stage'] == 'complete' and all(v['reused'] for v in m2['directories'].values()) and m2['directories']['cfg30101_b0']['manifest_sha256'] == m['directories']['cfg30101_b0']['manifest_sha256']
    assert all(os.path.exists(os.path.join(v['dependency_metadata'], 'COMPLETE.json')) for v in m2['directories'].values()) and json.load(open(tmp_path / 'reuse' / 'd2_bank_registry.json'))['calls'] == []   # RD2T3B-D: reused metadata copied under OUT; new calls empty, reused calls referenced
    # RD2T3B-B: a valid cache of ANOTHER request (config / purpose / batch / scale) is refused with a reason, not silently accepted
    for name, src in (('cfg30101_b0', 'cfg30101_b1'), ('cfg30101_b0', 'cfg30101_fit')):
        mm = tmp_path / ('mm_' + src); shutil.copytree(tmp_path / 'ok', mm); shutil.rmtree(mm / name); shutil.copytree(mm / src, mm / name)
        r4 = run(str(tmp_path / ('o_' + src)), '--selftest-scale', '0.001', '--selftest-configs', '30101', '--selftest-skip-a10', '--selftest-skip-env-lock', '--reuse-root', str(mm)); m4 = json.load(open(tmp_path / ('o_' + src) / 'd2_run_manifest.json')); assert m4['stage'] != 'complete' and 'differs from the current request' in json.dumps(m4)
    r5 = run(str(tmp_path / 'o_scale'), '--selftest-scale', '0.002', '--selftest-configs', '30101', '--selftest-skip-a10', '--selftest-skip-env-lock', '--reuse-root', str(tmp_path / 'ok')); m5 = json.load(open(tmp_path / 'o_scale' / 'd2_run_manifest.json')); assert m5['stage'] != 'complete'
    bad = tmp_path / 'bad'; shutil.copytree(tmp_path / 'ok', bad); f = bad / 'cfg30101_b1' / 'cfg30101_b1_s2.npz'; z = dict(np.load(f)); z['model_native__float64__T1'][0] += 1e-9; np.savez(f, **z)
    r3 = run(str(tmp_path / 'reuse_bad'), '--selftest-scale', '0.001', '--selftest-configs', '30101', '--selftest-skip-a10', '--selftest-skip-env-lock', '--reuse-root', str(bad)); m3 = json.load(open(tmp_path / 'reuse_bad' / 'd2_run_manifest.json'))
    assert r3.returncode == 1 and m3['stage'] == 'exception' and json.load(open(tmp_path / 'reuse_bad' / 'd2_bank_registry.json'))['status'] == 'PARTIAL_AFTER_FAILURE'
