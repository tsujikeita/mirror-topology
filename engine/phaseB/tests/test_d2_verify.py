# -*- coding: utf-8 -*-
"""D-2 read-only verifier v0.2 contracts (audit RV-1/2/3): test-mode normal path on a full synthetic family; accepted mode refuses synthetic banks, empty / partial / wrong-family
registries and real accepted metadata whose records differ; verifier source binding (edited module bytes refused); output isolation (run root, bank child, symlink alias,
non-empty out refused; inputs unchanged); partial scan is not a full success; f32 registered rule (relative near-tie vs absolute proxy; Event B mismatch recorded);
cid correspondence model<->reference actually compared."""
import os, sys, json, subprocess, shutil, hashlib, copy
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); MT = os.environ.get('B3_MT', '/home/claude/mt'); PC = os.environ.get('PHASEC_ROOT', '/home/claude/phaseC'); SCRIPT = os.path.join(P, 'd', 'd2_verify_banks.py')
need_ext = pytest.mark.skipif(not (os.path.exists(os.path.join(MT, 't1_engine.py')) and os.path.isdir(PC)), reason='external assets not present')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
ENV = dict(os.environ, PIP_BREAK_SYSTEM_PACKAGES='1', OPENBLAS_NUM_THREADS='1')

def snap(root): return {os.path.relpath(os.path.join(d, f), root): sha(os.path.join(d, f)) for d, _, fs in os.walk(root) for f in fs}

def make_run(tmp_path, configs='30101'):
    run = str(tmp_path / 'run'); r = subprocess.run([sys.executable, os.path.join(P, 'd', 'd2_bankgen.py'), '--mt', MT, '--phaseb', P, '--phasec', PC, '--out', f'{run}/d2', '--family', 'E7', '--selftest-scale', '0.003', '--selftest-skip-env-lock', '--selftest-skip-a10'] + (['--selftest-configs', configs] if configs else []), capture_output=True, text=True, env=ENV, timeout=290)
    m = json.load(open(f'{run}/d2/d2_run_manifest.json')); assert m['stage'] == 'complete', m['failures']
    inv = {}
    for d, _, fs in os.walk(run):
        for f in fs: p = os.path.join(d, f); rel = os.path.relpath(p, run); inv[rel] = dict(sha256=(None if f.endswith('.npz') else sha(p)), bytes=os.path.getsize(p))
    json.dump(dict(D2_PASS=False, family='E7', stages=dict(directories=m['directories']), output_inventory=inv), open(f'{run}/d2_final_record.json', 'w'), indent=1); return run

def call(run, out, *extra, phaseb=P, script=SCRIPT):
    r = subprocess.run([sys.executable, script, '--phaseb', phaseb, '--run-root', run, '--out', str(out), *extra], capture_output=True, text=True, env=ENV, timeout=290)
    rep = None
    for d, _, fs in os.walk(str(out)) if os.path.isdir(str(out)) else []:
        for f in fs:
            if f.startswith('d2_verify_') and f.endswith('.json') and not os.path.islink(os.path.join(d, f)): rep = json.load(open(os.path.join(d, f)))
    return r.returncode, rep, r

def rebind(run, name, edit):
    """Edit arrays of one unit and re-stamp NPZ / sidecar / COMPLETE / registry so that the directory is self-consistent (test-only)."""
    d = os.path.join(run, 'd2', name); man = json.load(open(os.path.join(d, 'COMPLETE.json'))); import io
    for sh in man['shards']:
        fp = os.path.join(d, sh['file']); z = dict(np.load(fp)); edit(z); buf = io.BytesIO(); np.savez(buf, **z); data = buf.getvalue(); open(fp, 'wb').write(data)
        sp = os.path.join(d, sh['sidecar']); side = json.load(open(sp)); side['array_sha256'] = {k: hashlib.sha256(np.ascontiguousarray(v).tobytes()).hexdigest() for k, v in z.items()}; side['file_sha256'] = hashlib.sha256(data).hexdigest(); side['bytes'] = len(data); json.dump(side, open(sp, 'w'), indent=1)
        sh['file_sha256'] = side['file_sha256']; sh['sidecar_sha256'] = sha(sp)
    man['manifest_sha256'] = hashlib.sha256(json.dumps({k: v for k, v in man.items() if k != 'manifest_sha256'}, sort_keys=True).encode()).hexdigest(); json.dump(man, open(os.path.join(d, 'COMPLETE.json'), 'w'), indent=1)
    rg = json.load(open(os.path.join(run, 'd2', 'd2_bank_registry.json'))); rg['directories'][name]['manifest_sha256'] = man['manifest_sha256']; json.dump(rg, open(os.path.join(run, 'd2', 'd2_bank_registry.json'), 'w'), indent=1)
    fr = json.load(open(os.path.join(run, 'd2_final_record.json')))
    for sh in man['shards']: fr['output_inventory'][os.path.relpath(os.path.join(d, sh['file']), run)]['bytes'] = os.path.getsize(os.path.join(d, sh['file']))
    json.dump(fr, open(os.path.join(run, 'd2_final_record.json'), 'w'), indent=1)

@need_ext
def test_test_mode_normal_and_accepted_mode_bindings(tmp_path):
    run = make_run(tmp_path, configs=None); before = snap(run)
    rc, rep, r = call(run, tmp_path / 'v', '--mode', 'test'); assert rc == 0 and rep['all_ok'] and rep['coverage_complete'] and rep['accepted_run_binding'] is False and rep['verification_scope'] == 'test' and set(rep['units']) == set(rep['required_units']) and len(rep['required_units']) == 39
    assert rep['cid_correspondence_ok'] and all(v['cid_equal'] for v in rep['cid_correspondence'].values()) and rep['n0_plus_3n0_structure_ok'] and rep['verifier_source']['source_bound'] and rep['verifier_source']['ledger_bound'] and rep['generator_source']['engine'] == rep['verifier_source']['engine']
    assert rep['f32_registered_gate']['status'] == 'CANDIDATE_EVALUATED' and 'cfg30101_w2' in rep['f32_sensitivity'] and snap(run) == before
    rc, rep, _ = call(run, tmp_path / 'acc'); assert rc == 1 and rep['stage'] == 'binding' and rep['accepted_run_binding'] is None and 'units' not in rep                       # synthetic run is not an accepted run
    # empty registry -> refused (both modes); wrong family / omitted unit -> refused before arrays
    for change, needle in (('empty', 'unit set differs'), ('omit', 'unit set differs'), ('family', 'unknown family')):
        bad = str(tmp_path / f'bad_{change}'); shutil.copytree(run, bad); rg = json.load(open(f'{bad}/d2/d2_bank_registry.json'))
        if change == 'empty': rg['directories'] = {}
        if change == 'omit': rg['directories'].pop('cfg30101_w2')
        if change == 'family': rg['family'] = 'E9'
        json.dump(rg, open(f'{bad}/d2/d2_bank_registry.json', 'w'))
        rc, rep, _ = call(bad, tmp_path / f'o_{change}', '--mode', 'test'); assert rc == 1 and 'units' not in rep and any(needle in f for f in rep['failures'])
    # real accepted E7 metadata (registered copy) with no NPZ: binding passes (records identical), every unit fails on missing arrays -> not all_ok
    real = str(tmp_path / 'realE7'); shutil.copytree(os.path.join(P, 'registered_assets', 'd2', 'E7'), real)
    rc, rep, _ = call(real, tmp_path / 'o_real'); assert rc == 1 and rep['accepted_run_binding'] is True and rep['all_ok'] is False and len(rep['failures']) == 39
    # real E7 metadata with a coherent local edit of the registry (manifest SHA changed) -> refused at binding by the ledger
    bad = str(tmp_path / 'realE7b'); shutil.copytree(os.path.join(P, 'registered_assets', 'd2', 'E7'), bad); rg = json.load(open(f'{bad}/d2/d2_bank_registry.json')); rg['directories']['cfg30101_b0']['manifest_sha256'] = '0' * 64; json.dump(rg, open(f'{bad}/d2/d2_bank_registry.json', 'w'), indent=1)
    rc, rep, _ = call(bad, tmp_path / 'o_realb'); assert rc == 1 and rep['stage'] == 'binding'

@need_ext
def test_output_isolation_partial_scan_and_verifier_source(tmp_path):
    run = make_run(tmp_path, configs=None); before = snap(run)
    rc, _, r = call(run, run, '--mode', 'test'); assert rc == 2 and snap(run) == before                                                                                # out == run root
    rc, _, r = call(run, os.path.join(run, 'd2', 'cfg30101_b0'), '--mode', 'test'); assert rc == 2 and snap(run) == before                                                # out inside a bank
    o = tmp_path / 'alias'; o.mkdir(); os.symlink(os.path.join(run, 'd2', 'cfg30101_b0', 'cfg30101_b0_s0.npz'), str(o / 'd2_verify_E7.json'))
    rc, _, r = call(run, o, '--mode', 'test'); assert rc == 2 and snap(run) == before                                                                                # non-empty / alias out refused before any write
    rc, rep, _ = call(run, tmp_path / 'p', '--mode', 'test', '--max-dirs', '2'); assert rc == 1 and rep['coverage_complete'] is False and rep['verification_scope'] == 'test_partial' and len(rep['checked_units']) == 2 and len(rep['unchecked_units']) == 37
    rc, _, r = call(run, tmp_path / 'p2', '--mode', 'test', '--max-dirs', '-1'); assert rc == 2
    # verifier source: an edited module with an unchanged inventory is refused before any bank is read
    pb2 = str(tmp_path / 'pb'); shutil.copytree(P, pb2, ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache', 'regression_logs', 'registered_assets/d1')); open(os.path.join(pb2, 'step1_engine', 'd2_bank.py'), 'a').write('\n# comment only\n')
    rc, rep, _ = call(run, tmp_path / 'vs', '--mode', 'test', phaseb=pb2, script=os.path.join(pb2, 'd', 'd2_verify_banks.py')); assert rc == 1 and rep['stage'] == 'verifier_source' and 'units' not in rep

@need_ext
def test_f32_registered_rule_and_cid_pairing(tmp_path):
    run = make_run(tmp_path, configs=None)
    # (a) large base, tiny absolute difference but relative < 1e-6: every flip is a near-tie under the registered rule; (b) small base: relative >= 1e-6 -> not near-tie
    for case, (base, delta, expect_near) in {'a': (1000.0, 5e-4, True), 'b': (0.01, 5e-7, False)}.items():
        r2 = str(tmp_path / f'run_{case}'); shutil.copytree(run, r2); rg = json.load(open(f'{r2}/d2/d2_bank_registry.json'))
        for k, d in rg['directories'].items(): d['path'] = d['path'].replace(run, r2)
        json.dump(rg, open(f'{r2}/d2/d2_bank_registry.json', 'w'), indent=1)
        def edit(z, base=base, delta=delta):
            n = len(z['cid']); z['model_matched__float64__T1'][:] = base; z['model_matched__float32__T1'][:] = base + delta; z['model_matched__float64__AX'][:] = 0; z['model_matched__float32__AX'][:] = 5
        rebind(r2, 'cfg30101_w2', edit)
        rc, rep, _ = call(r2, tmp_path / f'v_{case}', '--mode', 'test'); s = rep['f32_sensitivity']['cfg30101_w2']['model_matched']
        assert s['flips'] == 600 and (s['near_tie_flips_rel_lt_1e6'] == 600) == expect_near and (s['flips_rel_ge_1e6'] == 0) == expect_near and s['passes_registered_rule'] == (expect_near and s['event_B_mismatch_rate'] <= 1e-5)
        assert s['flip_evidence'][0]['AX'] == [0, 5] and 'plane_angle_deg' in s['flip_evidence'][0] and 'antipode' in s['flip_evidence'][0]
    # Event B mismatch: T1 straddles the frozen target across the two paths, T2 below the target -> mismatch rate 1.0 recorded, rule fails
    r3 = str(tmp_path / 'run_eb'); shutil.copytree(run, r3); rg = json.load(open(f'{r3}/d2/d2_bank_registry.json'))
    for k, d in rg['directories'].items(): d['path'] = d['path'].replace(run, r3)
    json.dump(rg, open(f'{r3}/d2/d2_bank_registry.json', 'w'), indent=1)
    def edit_eb(z):
        z['model_matched__float64__T1'][:] = 39.67178834527284 - 1e-8; z['model_matched__float32__T1'][:] = 39.67178834527284 + 1e-8; z['model_matched__float64__T2'][:] = 100.0; z['model_matched__float32__T2'][:] = 100.0
    rebind(r3, 'cfg30101_w2', edit_eb); rc, rep, _ = call(r3, tmp_path / 'v_eb', '--mode', 'test'); s = rep['f32_sensitivity']['cfg30101_w2']['model_matched']
    assert s['event_B_mismatch_rate'] == 1.0 and s['passes_registered_rule'] is False and rep['f32_registered_gate']['all_pairs_pass_registered_rule'] is False and rep['all_ok']   # integrity vs f32 gate are separate
    # cid pairing: a reference generated at a different size than the configuration is detected
    r4 = str(tmp_path / 'run_cid'); shutil.copytree(run, r4); rg = json.load(open(f'{r4}/d2/d2_bank_registry.json'))
    for k, d in rg['directories'].items(): d['path'] = d['path'].replace(run, r4)
    json.dump(rg, open(f'{r4}/d2/d2_bank_registry.json', 'w'), indent=1)
    def edit_cid(z):
        for k in list(z): z[k] = z[k][: len(z[k]) // 2] if k != 'cid' else z[k][: len(z[k]) // 2]
    rebind(r4, 'ref_E7_b0', edit_cid); rc, rep, _ = call(r4, tmp_path / 'v_cid', '--mode', 'test'); assert rc == 1 and (rep['cid_correspondence_ok'] is False or not rep['units']['ref_E7_b0']['ok'])
