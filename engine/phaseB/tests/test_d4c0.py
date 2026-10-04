# -*- coding: utf-8 -*-
"""D4C-0 contracts (engine step1_engine/w2_cases.py + step1_engine/d4_pseudo.py; scripts d/d2w_cases.py + d/d4_pseudo.py; the two launcher notebooks).
D4C-0b (pseudo; R-D4DESIGN-C): the SEPARATE pseudo table (schema / SHA / purpose 400 / group 5001 / m = 1 / K = n_pseudo) is validated and refused on any deviation
(group inside a D-2 table group range, m != 1, K != n, purpose id, SHA); the registered D-2 CRN table validator still rejects a 'pseudo' purpose (the old table is unchanged);
the formal rng keys never coincide with any key of the registered D-2 table groups (purpose id 400 is unique); generation on the real kernel (self-test prefix n = 50) is
deterministic, a prefix of the full ordered column (n = 20 == first 20 rows of n = 50), paired in generation order, cid == arange, UIDs == the table's ordered UIDs; the
saved NPZ is re-verified and every modification (a value, a row order, the file bytes, the identity) is refused; the script self-test publishes a record bound to the
attempt / lock / source with PSEUDO_PASS False and rc 1 (env lock); the registered loader refuses while PSEUDO_REGISTRATION is None; commit_target is the existing helper.
D4C-0a (D-2W; R-D4DESIGN-A/B): on a SMALL synthetic W2 bank (real kernel, registered matched roots, scale 0.025 -> K = 50 x m = 100) the script self-test (E2/L1.00)
assembles the case with the strong intake (root SHA / whitening values / spec identity), evaluates the exact W2 context, publishes the case + context records, RESTORES the
context from the published record (array-free replay) and requires equality (G_records_restored); the restore refuses a modified result / decision / manifest, a record bound
to another asset, a duplicate / mixed case, a non-formal record under require_formal, and a formal-size claim on a small bank; a technical (non-finite) value in the stored
evidence is refused, never promoted; the scientific outcome (w2-unresolved / unknown) is preserved as such; RegisteredBankIdentity carries the identity exactly and is
immutable; the script refuses OUT inside an input / symlink OUT (rc 2, nothing written), unresolved inputs (G_d2_inputs_resolved False) and the formal path on a non-formal
bank; the registered loader refuses while D2W_REGISTRATION is None. Notebooks: 5 cells, parseable, D-3c v0.3 structure (anchor / ONE verifier twice / initial record /
superseded record / content-verified evidence), and the attempt cell exercised on a fake source with a test-double child (ok / pass_false / rc1 / commit_changed /
script_changed_during_staging / anchor_symlink / evidence_tampered / result_attempt_mismatch)."""
import os, sys, json, shutil, subprocess, hashlib, copy, io, contextlib, re
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine.errors import InputContractError
from step1_engine import d4_pseudo as dp
from step1_engine import w2_cases as wc
from step1_engine.positions import RegisteredBankIdentity, bank_identity, PositionBank
from step1_engine.registry import PURPOSE, STREAM
from step1_engine import serialization as ser
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); MT = os.environ.get('B3_MT', '/home/claude/mt'); PC = os.environ.get('PHASEC_ROOT', '/home/claude/phaseC')
D2W = os.path.join(P, 'd', 'd2w_cases.py'); PSE = os.path.join(P, 'd', 'd4_pseudo.py'); NB_D2W = os.path.join(P, 'd', 'MirrorTopology_Step1_D2W_cases_v0.1.ipynb'); NB_PSE = os.path.join(P, 'd', 'MirrorTopology_Step1_D4_pseudo_v0.1.ipynb')
need_ext = pytest.mark.skipif(not (os.path.exists(os.path.join(MT, 't1_engine.py')) and os.path.isdir(PC)), reason='external assets not present')
ENV = dict(os.environ, PIP_BREAK_SYSTEM_PACKAGES='1', OPENBLAS_NUM_THREADS='1'); sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
PINS = json.load(open(os.path.join(P, 'd', 'd3_pins.json'))); D2PINS = json.load(open(os.path.join(P, 'd', 'd2_pins.json')))


def _run(args, timeout=280): return subprocess.run([sys.executable, *args], capture_output=True, text=True, env=ENV, timeout=timeout)


def _ext_ok(): return os.path.exists(os.path.join(MT, 't1_engine.py')) and os.path.isdir(PC)


# ================================================================================================================================================= D4C-0b: pseudo table
def test_pseudo_table_registered_file_and_refusals():
    t, reg = dp.load_pseudo_table(os.path.join(P, 'd', 'd4_pseudo_table.json'), PINS['d4_pseudo_table_sha256'])
    assert t == dp.build_pseudo_table() and t['n_pseudo'] == 2000 and t['m'] == 1 and t['K'] == 2000 and t['group'] == 5001 and t['purpose_id'] == PURPOSE['pseudo'] == 400 and t['master_seed'] == 20260912 and t['wave_id'] == 1 and t['selections'] == ['float64']
    assert dp.pseudo_rng_keys(t, reg) == dict(rotation=[20260912, 1, 400, 5001, 0, STREAM['rotation']], gaussian=[20260912, 1, 400, 5001, 0, STREAM['gaussian']])
    with pytest.raises(InputContractError): dp.load_pseudo_table(os.path.join(P, 'd', 'd4_pseudo_table.json'), 'f' * 64)
    for mut in [dict(m=2), dict(K=1999), dict(purpose_id=200), dict(purpose='evaluation'), dict(batch_id=1), dict(group=1002), dict(group=4001), dict(group=50101), dict(group=70303), dict(selections=['float64', 'float32']), dict(role='model_matched'), dict(chunk_clusters=1), dict(schema='d2_crn_table_v1')]:
        bad = dict(t, **mut); bad['table_sha256'] = dp._table_sha(bad)
        with pytest.raises(InputContractError): dp.validate_pseudo_table(bad)
    bad = dict(t); bad['n_pseudo'] = 1999   # SHA no longer matches
    with pytest.raises(InputContractError): dp.validate_pseudo_table(bad)
    for g in (1001, 1008, 2001, 2008, 4000, 4999, 40000, 79999):
        with pytest.raises(InputContractError): dp.build_pseudo_table(group=g)
    assert dp.build_pseudo_table(group=5002)['group'] == 5002 and dp.build_pseudo_table(n_pseudo=50)['K'] == 50
    with pytest.raises(InputContractError): dp.build_pseudo_table(n_pseudo=0)
    with pytest.raises(InputContractError): dp.build_pseudo_table(n_pseudo=True)


def test_pseudo_keys_disjoint_from_the_registered_d2_table_and_old_table_unchanged():
    from step1_engine.d2_rng import load_crn_table, _validated_table_groups
    table, reg2 = load_crn_table(os.path.join(P, 'd', 'd2_crn_table.json'), D2PINS['crn_table_sha256'])
    assert table['table_sha256'] == '60d9941ad65e894ae6d0d30707f08a45ac0e0e22ecaf1e33498458d02091dc72' and 'pseudo' not in {g['purpose'] for g in table['groups'].values()}
    t, reg = dp.load_pseudo_table(os.path.join(P, 'd', 'd4_pseudo_table.json'), PINS['d4_pseudo_table_sha256']); pk = {tuple(v) for v in dp.pseudo_rng_keys(t, reg).values()}
    old = set()
    for gid, g in table['groups'].items():
        assert any(lo <= int(gid) <= hi for lo, hi in dp._D2_TABLE_GROUP_RANGES), gid       # every registered group lies inside the refused ranges
        for b in range(int(table['batches']) if isinstance(table.get('batches'), int) else 2):
            for s in STREAM: old.add(tuple(reg2.rng_key(g['purpose'], int(g['wave_id']), int(gid), b, s)))
    assert old and not (pk & old) and all(k[2] == 400 for k in pk) and all(k[2] != 400 for k in old)
    # the OLD validator refuses a 'pseudo' purpose inside the D-2 table (the registered table is not extended)
    ext = copy.deepcopy(table); ext['groups']['5001'] = dict(purpose='pseudo', wave_id=1, label='x')
    with pytest.raises(InputContractError): _validated_table_groups(ext)


# ================================================================================================================================================= D4C-0b: generation
@pytest.fixture(scope='module')
def kernel_root():
    if not _ext_ok(): pytest.skip('external assets not present')
    from step1_engine.legacy_kernel import LegacyKernel
    k = LegacyKernel(MT); S, _ = k.psqrt(k.C_ISO); return k, S


@need_ext
def test_pseudo_generation_deterministic_prefix_paired_saved_verified_and_refusals(kernel_root, tmp_path):
    k, S = kernel_root; t, reg = dp.load_pseudo_table(os.path.join(P, 'd', 'd4_pseudo_table.json'), PINS['d4_pseudo_table_sha256'])
    a = dp.generate_pseudo_columns(k, t, reg, S, n=50); b = dp.generate_pseudo_columns(k, t, reg, S, n=50); c = dp.generate_pseudo_columns(k, t, reg, S, n=20)
    assert a['n'] == 50 and a['T1'].shape == (50,) and a['T1'].dtype == np.float64 and a['AX'].dtype == np.int32 and np.array_equal(a['cid'], np.arange(50)) and a['uids'][0] == [1, 400, 5001, 0, 0] and a['uids'][-1] == [1, 400, 5001, 0, 49]
    assert all(np.array_equal(a[x], b[x]) for x in ('T1', 'T2', 'AX', 'PL', 'cid')) and a['uids'] == b['uids']
    assert all(np.array_equal(a[x][:20], c[x]) for x in ('T1', 'T2', 'AX', 'PL')) and a['uids'][:20] == c['uids']          # prefix stability (ordered column)
    assert dp.column_identity(a) == dp.column_identity(b) and dp.column_identity(a) != dp.column_identity(c) and a['rng_keys'] == dp.pseudo_rng_keys(t, reg) and a['root_sha256'] == hashlib.sha256(np.ascontiguousarray(S).tobytes()).hexdigest()
    assert np.isfinite(a['T1']).all() and np.isfinite(a['T2']).all() and a['T1'].min() > 0 and a['T2'].min() > 0 and not np.array_equal(np.sort(a['T1']), a['T1'])     # generation order kept (not sorted)
    ident = dp.column_identity(a); assert ident['paired_sha256'] == hashlib.sha256(np.ascontiguousarray(np.c_[a['T1'], a['T2']]).tobytes()).hexdigest()
    with pytest.raises(InputContractError): dp.generate_pseudo_columns(k, t, reg, S, n=2001)
    with pytest.raises(InputContractError): dp.generate_pseudo_columns(k, t, reg, S[:20, :20], n=5)
    with pytest.raises(InputContractError): dp.generate_pseudo_columns(k, t, reg, S * np.nan, n=5)
    p = str(tmp_path / 'cols.npz'); fid = dp.save_pseudo_columns(p, a); assert fid == dict(file='cols.npz', sha256=sha(p), bytes=os.path.getsize(p))
    back = dp.verify_pseudo_columns(p, ident, t, fid); assert np.array_equal(back['T1'], a['T1']) and np.array_equal(back['T2'], a['T2']) and back['uids'] == a['uids'] and dp.column_identity(back) == ident
    with pytest.raises(InputContractError): dp.verify_pseudo_columns(p, ident, t, dict(fid, sha256='0' * 64))
    with pytest.raises(InputContractError): dp.verify_pseudo_columns(p, dict(ident, T1_sha256='0' * 64), t, fid)
    with pytest.raises(InputContractError): dp.verify_pseudo_columns(p, dict(ident, n=49), t, fid)
    for mut in ('value', 'swap', 'reorder', 'member', 'uid'):
        m = copy.deepcopy(a); q = str(tmp_path / f'{mut}.npz')
        if mut == 'value': m['T1'] = m['T1'].copy(); m['T1'][3] += 1e-9
        if mut == 'swap': m['T1'], m['T2'] = m['T2'], m['T1']
        if mut == 'reorder': m['T1'] = m['T1'][::-1].copy(); m['T2'] = m['T2'][::-1].copy()
        if mut == 'uid': m['uids'] = [list(u) for u in m['uids']]; m['uids'][0][4] = 1
        if mut == 'member':
            np.savez(q, T1=m['T1'], T2=m['T2'], AX=m['AX'], PL=m['PL'], cid=m['cid'])
        else: dp.save_pseudo_columns(q, m)
        with pytest.raises(InputContractError): dp.verify_pseudo_columns(q, ident, t)
    # non-finite stored value is refused (technical failure never promoted), exact dtype required
    m = copy.deepcopy(a); m['T2'] = m['T2'].copy(); m['T2'][0] = np.inf; q = str(tmp_path / 'inf.npz'); dp.save_pseudo_columns(q, m)
    with pytest.raises(InputContractError): dp.verify_pseudo_columns(q, dp.column_identity(m), t)
    m = copy.deepcopy(a); m['T1'] = m['T1'].astype(np.float32); q = str(tmp_path / 'f32.npz'); dp.save_pseudo_columns(q, m)
    with pytest.raises(InputContractError): dp.verify_pseudo_columns(q, ident, t)
    with pytest.raises(InputContractError): dp.load_registered_pseudo_columns(P, None)
    # the target commitment is the EXISTING helper (never re-implemented here)
    from step1_engine.calibration_first import commit_target
    assert 'commit_target' not in dir(dp) and commit_target((39.67178834527284, 259.3375006282747), 'TEST_ONLY_NONCE_0123456789abcdef') == hashlib.sha256((json.dumps([39.67178834527284, 259.3375006282747]) + '|TEST_ONLY_NONCE_0123456789abcdef').encode()).hexdigest()
    with pytest.raises(InputContractError): commit_target((39.67178834527284, 259.3375006282747), 'short')


@need_ext
def test_pseudo_script_selftest_record_bound_and_refusals(tmp_path):
    base = [PSE, '--mt', MT, '--phaseb', P, '--phasec', PC]
    out = tmp_path / 'p1'; r = _run(base + ['--out', str(out), '--selftest-n', '50', '--selftest-skip-env-lock', '--attempt-id', 'TEST_ATTEMPT_P', '--launcher-lock-sha256', 'e' * 64]); m = json.load(open(out / 'd4_pseudo_record.json'))
    assert r.returncode == 1 and m['stage'] == 'complete' and m['PSEUDO_PASS'] is False and m['selftest'] is True and m['gates']['G_env_lock'] is False and all(m['gates'][g] is True for g in m['required_inventory'] if g != 'G_env_lock') and m['failures'] == []
    assert m['attempt'] == dict(attempt_id='TEST_ATTEMPT_P', launcher_lock_sha256='e' * 64) and m['source'] == dict(m['source'], script_sha256=sha(PSE), inventory_sha256=sha(os.path.join(P, 'B2_completion_inventory.json')), pins_sha256=sha(os.path.join(P, 'd', 'd3_pins.json')), engine_version=m['engine_version'])
    assert m['pseudo_table']['table_sha256'] == PINS['d4_pseudo_table_sha256'] and m['pseudo_table']['rng_keys'] == m['generation']['rng_keys'] == dict(rotation=[20260912, 1, 400, 5001, 0, 1], gaussian=[20260912, 1, 400, 5001, 0, 0]) and m['generation']['n'] == 50 and m['generation']['m'] == 1
    ident = m['columns']['identity']; fe = m['columns']['file']; fp = out / fe['file']; assert fe == dict(file='d4_pseudo_columns.npz', sha256=sha(fp), bytes=os.path.getsize(fp)) and ident['n'] == 50 and ident['m'] == 1 and ident['first_uid'] == [1, 400, 5001, 0, 0] and ident['last_uid'] == [1, 400, 5001, 0, 49]
    t, _ = dp.load_pseudo_table(os.path.join(P, 'd', 'd4_pseudo_table.json')); cols = dp.verify_pseudo_columns(str(fp), ident, t, fe)
    # second run: identical columns (determinism across processes); the sandbox smoke of the prior session had the same paired SHA
    out2 = tmp_path / 'p2'; _run(base + ['--out', str(out2), '--selftest-n', '50', '--selftest-skip-env-lock']); m2 = json.load(open(out2 / 'd4_pseudo_record.json'))
    assert m2['columns']['identity'] == ident and m2['columns']['file']['sha256'] == fe['sha256'] and m2['attempt'] == dict(attempt_id=None, launcher_lock_sha256=None)
    assert set(m['stages_rss_mb']) == {'preflight', 'generation', 'verification', 'final'} and set(m['stages_peak_rss_mb']) == set(m['stages_rss_mb'])
    # refusals: OUT inside the source / phasec / a symlink -> rc 2 and nothing written; non-empty OUT -> rc 2; wrong profile -> rc 1 with record
    for bad in (os.path.join(P, 'd', 'x_out'), os.path.join(PC, 'x_out'), os.path.join(MT, 'x_out')):
        r = _run(base + ['--out', bad, '--selftest-n', '5', '--selftest-skip-env-lock']); assert r.returncode == 2 and not os.path.exists(bad)
    link = tmp_path / 'link'; tgt = tmp_path / 'tgt'; tgt.mkdir(); os.symlink(tgt, link); r = _run(base + ['--out', str(link), '--selftest-n', '5', '--selftest-skip-env-lock']); assert r.returncode == 2 and os.listdir(tgt) == []
    r = _run(base + ['--out', str(out), '--selftest-n', '5', '--selftest-skip-env-lock']); assert r.returncode == 2
    o3 = tmp_path / 'p3'; r = _run(base + ['--out', str(o3), '--selftest-n', '5', '--selftest-skip-env-lock', '--profile', 'other']); assert r.returncode == 1 and json.load(open(o3 / 'd4_pseudo_record.json'))['PSEUDO_PASS'] is False


# ================================================================================================================================================= D4C-0a: W2 cases
@pytest.fixture(scope='module')
def w2_small(tmp_path_factory, kernel_root):
    """A small synthetic W2 bank for E2/L1.00 (cfg20101/20102/20103_w2; real kernel; registered matched roots; scale 0.025 -> K = 50 x m = 100) and the script self-test run on it."""
    k, _ = kernel_root; root = tmp_path_factory.mktemp('d2w'); bank = root / 'bank'; bank.mkdir()
    from step1_engine.d2_rng import load_crn_table
    from step1_engine.d2_bank import load_bank_spec, generate_w2_position_bank, CallInventory
    from step1_engine.d3_profile import twelve_context
    from step1_engine.production import intake_registered_covariance
    from step1_engine.grid_registry import load_registry
    table, R = load_crn_table(os.path.join(P, 'd', 'd2_crn_table.json'), D2PINS['crn_table_sha256']); spec = load_bank_spec(os.path.join(P, 'd', 'd2_bank_spec.json'), D2PINS['bank_spec_sha256'], table)
    reg = load_registry(os.path.join(P, 'tests/assets/a7_circle_geometry.csv'), os.path.join(P, 'tests/assets/a6_observer_design_points.json')); plan = wc.case_plan(twelve_context(P).table); roots = {}
    for cid in plan['E2/L1.00']['config_ids']:
        cov = intake_registered_covariance(cid, reg, os.path.join(P, 'registered_assets', 'd1'), MT); roots[cid] = cov['S_matched']
        generate_w2_position_bank(k, R, table, spec, cid, cov['S_matched'], str(bank / f'cfg{cid}_w2'), CallInventory(), scale=0.025)
    out = root / 'run'; base = [D2W, '--mt', MT, '--phaseb', P, '--phasec', PC, '--d2-root', f'E2={bank}']
    r = _run(base + ['--out', str(out), '--selftest-small', '--selftest-skip-env-lock', '--selftest-cases', 'E2/L1.00', '--attempt-id', 'TEST_ATTEMPT_W', '--launcher-lock-sha256', 'd' * 64])
    return dict(bank=str(bank), out=str(out), base=base, rc=r.returncode, stdout=r.stdout, table=table, roots=roots, plan=plan)


def test_case_plan_is_the_nine_first_wave_cases():
    from step1_engine.d3_profile import twelve_context
    plan = wc.case_plan(twelve_context(P).table)
    assert set(plan) == {f'{f}/{s}' for f in wc.FAMILIES for s in wc.SIZES} and plan['E2/L1.00'] == dict(family='E2', size_id='L1.00', config_ids=[20101, 20102, 20103], observer_ids=[1, 2, 3], groups=[50101, 50102, 50103])
    assert all(v['config_ids'] == sorted(v['config_ids']) and v['groups'] == [30000 + c for c in v['config_ids']] and v['observer_ids'] == [1, 2, 3] for v in plan.values()) and len({c for v in plan.values() for c in v['config_ids']}) == 27
    asset = wc.registered_shared_null_asset(P); assert asset.sha256 == wc.SHARED_NULL['asset_sha256'] and int(asset.identity['m']) == 100 and int(asset.identity['master_seed']) == 20260912
    with pytest.raises(InputContractError): wc.load_registered_w2_context(P, None)
    assert wc.D2W_REGISTRATION is None and dp.PSEUDO_REGISTRATION is None


def test_registered_bank_identity_contract():
    idn = dict(position_id=20101, K=50, m=100, rows=5000, Tw_sha256='a' * 64, cid_sha256='b' * 64, labels_sha256='c' * 64)
    r = RegisteredBankIdentity(idn); assert r.identity() == idn and bank_identity(r) == idn and r.position_id == 20101 and r.K == 50 and r.m == 100
    with pytest.raises(AttributeError): r.K = 3
    for bad in (dict(idn, rows=4999), dict(idn, K=True), dict(idn, Tw_sha256='x' * 64), {k: v for k, v in idn.items() if k != 'rows'}, dict(idn, extra=1), dict(idn, m=0), 'x'):
        with pytest.raises(InputContractError): RegisteredBankIdentity(bad)
    with pytest.raises(InputContractError): bank_identity(idn)       # a plain dict is not a bank
    rng = np.random.default_rng(0); b = PositionBank(7, rng.standard_normal((20, 2)), np.repeat(np.arange(10), 2)); bi = bank_identity(b); assert RegisteredBankIdentity(bi).identity() == bi
    from step1_engine.positions import w2_exact
    with pytest.raises(Exception): w2_exact(r, r)       # no arrays: never usable for a distance execution


@need_ext
def test_d2w_script_selftest_end_to_end_records_restore_and_outcome_preserved(w2_small):
    out = w2_small['out']; m = json.load(open(os.path.join(out, 'd2w_run_record.json')))
    assert w2_small['rc'] == 1 and m['stage'] == 'complete' and m['D2W_PASS'] is False and m['selftest'] is True and m['gates']['G_env_lock'] is False and all(m['gates'][g] is True for g in m['required_inventory'] if g != 'G_env_lock') and m['failures'] == [], (m['failures'], w2_small['stdout'][-800:])
    assert m['attempt'] == dict(attempt_id='TEST_ATTEMPT_W', launcher_lock_sha256='d' * 64) and m['source'] == dict(m['source'], script_sha256=sha(D2W), inventory_sha256=sha(os.path.join(P, 'B2_completion_inventory.json')), engine_version=m['engine_version']) and set(m['protected_roots']) == {'mt', 'phaseb', 'phasec', 'd2_root_E2'}
    assert m['inputs']['cases'] == ['E2/L1.00'] and set(m['covariances']) == {'20101', '20102', '20103'} and m['shared_null']['asset_sha256'] == wc.SHARED_NULL['asset_sha256'] and m['shared_null']['m'] == 100 and m['shared_null']['iso_K'] == 6000 and m['shared_null']['replicate_bounds'] is True
    c = m['context']['cases']['E2/L1.00']; assert c['trigger'] in ('unknown', True, False) and c['validation_state'] in ('w2-unresolved', 'w2-validated') and c['B_final'] in (200, 400, 600, 800, 1000)
    pe = m['published_evidence']; assert set(pe) == {'d2w_case_E2_L1.00.json', 'd2w_context_record.json'}
    cp = os.path.join(out, 'cases', 'd2w_case_E2_L1.00.json'); xp = os.path.join(out, 'd2w_context_record.json'); assert pe['d2w_case_E2_L1.00.json'] == dict(sha256=sha(cp), bytes=os.path.getsize(cp)) and pe['d2w_context_record.json'] == dict(sha256=sha(xp), bytes=os.path.getsize(xp))
    rec = json.load(open(cp)); xr = json.load(open(xp))
    assert rec['schema'] == wc.CASE_SCHEMA and rec['key'] == 'E2/L1.00' and rec['inputs']['formal'] is False and rec['inputs']['config_ids'] == [20101, 20102, 20103] and set(rec['inputs']['units']) == {'cfg20101_w2', 'cfg20102_w2', 'cfg20103_w2'} and rec['inputs']['whitening']['identity'] == dict(wc.SHARED_NULL)
    u = rec['inputs']['units']['cfg20101_w2']; assert u['bank_identity_f64']['K'] == 50 and u['bank_identity_f64']['rows'] == 5000 and u['bank_identity_f32']['Tw_sha256'] != u['bank_identity_f64']['Tw_sha256'] and u['bank_identity_f32']['cid_sha256'] == u['bank_identity_f64']['cid_sha256'] and u['root_matched_sha256'] == hashlib.sha256(np.ascontiguousarray(w2_small['roots'][20101]).tobytes()).hexdigest()
    assert rec['decision'] == dict(rec['decision'], trigger=c['trigger'], validation_state=c['validation_state'], B_final=c['B_final']) and rec['constants'] == dict(m=100, n_subs=[2000, 5000], seed_ids=[0, 1, 2], B_levels=[200, 400, 600, 800, 1000], first_comparison=[200, 400], rel_tol=0.05, seed_spread_max=0.25, quantile_method='higher')
    assert xr['schema'] == wc.CONTEXT_SCHEMA and xr['context_sha256'] == m['context']['context_sha256'] and xr['n_cases'] == 1 and xr['case_records']['E2/L1.00']['manifest_sha256'] == rec['manifest_sha256'] and xr['shared_null'] == dict(wc.SHARED_NULL)
    # restore in THIS process from the published record (array-free replay): identical context SHA and decision; scientific outcome preserved exactly
    asset = wc.registered_shared_null_asset(P); ctx = wc.restore_w2_context([rec], asset, expected_context_sha256=m['context']['context_sha256'], require_formal=False)
    d = ctx.decisions['E2/L1.00']; assert ctx.context_sha256 == m['context']['context_sha256'] and d.trigger == c['trigger'] and d.validation_state == c['validation_state'] and int(d.B_final) == c['B_final'] and d.checksum == rec['decision']['checksum'] and ctx.scope == wc.SCOPE_TRUSTED
    ctx2 = wc.restore_w2_context([rec], asset, require_formal=False); assert ctx2.context_sha256 == ctx.context_sha256 and wc.context_record(ctx2, {'E2/L1.00': rec})['case_records'] == xr['case_records']


def _restore(rec, expected=None, require_formal=False):
    return wc.restore_w2_context([rec], wc.registered_shared_null_asset(P), expected_context_sha256=expected, require_formal=require_formal)


@need_ext
def test_d2w_restore_refusals(w2_small):
    rec = json.load(open(os.path.join(w2_small['out'], 'cases', 'd2w_case_E2_L1.00.json'))); m = json.load(open(os.path.join(w2_small['out'], 'd2w_run_record.json'))); csha = m['context']['context_sha256']
    with pytest.raises(InputContractError): _restore(rec, expected='0' * 64)
    with pytest.raises(InputContractError): _restore(rec, require_formal=True)                   # not a formal record (inputs.formal False)
    with pytest.raises(InputContractError): _restore(dict(rec, inputs=dict(rec['inputs'], formal=True)), require_formal=True)     # formal claim on a small bank: K x m != 200000
    with pytest.raises(InputContractError): _restore(dict(rec, asset_sha256='1' * 64))
    with pytest.raises(InputContractError): _restore(dict(rec, schema='other'))
    with pytest.raises(InputContractError): _restore(dict(rec, family='E7'))
    with pytest.raises(InputContractError): _restore(dict(rec, key='E7/L1.00'))
    with pytest.raises(InputContractError): wc.restore_w2_context([rec, rec], wc.registered_shared_null_asset(P), require_formal=False)      # duplicate
    with pytest.raises(InputContractError): wc.restore_w2_context([], wc.registered_shared_null_asset(P))
    # stored decision tampered (promotion of unresolved -> validated / trigger) is refused
    for mut in (dict(validation_state='w2-validated'), dict(trigger=True), dict(trigger=False), dict(B_final=1000), dict(checksum='0' * 64)):
        with pytest.raises(InputContractError): _restore(dict(rec, decision=dict(rec['decision'], **mut)))
    # manifest tampered / SHA mismatch; result tampered (content SHA) / non-finite stored value (technical) refused
    man = copy.deepcopy(rec['manifest']); man['stop']['B_final'] = 1000 if man['stop'].get('B_final') != 1000 else 800
    with pytest.raises(InputContractError): _restore(dict(rec, manifest=man))
    with pytest.raises(InputContractError): _restore(dict(rec, manifest_sha256='2' * 64))
    with pytest.raises(InputContractError): _restore(dict(rec, result_sha256='3' * 64))
    res = copy.deepcopy(rec['result']); res['stop']['B_final'] = 200 if res['stop']['B_final'] != 200 else 400
    with pytest.raises(InputContractError): _restore(dict(rec, result=res))
    res = ser.from_jsonable(copy.deepcopy(rec['result'])); snap = res['evidence']['inputs']['positions']; snap[0]['K'] = 51; snap[0]['rows'] = 5100
    bad = dict(rec, result=ser.to_jsonable(res)); bad['result_sha256'] = wc._result_sha(res)
    with pytest.raises(InputContractError): _restore(bad)                                         # evidence bank identity changed -> manifest/identity mismatch
    # a non-finite observed value injected into the stored evidence (with a consistent content SHA) is a technical refusal, never a promoted outcome
    res = ser.from_jsonable(copy.deepcopy(rec['result'])); ev = res['evidence']; injected = False
    def poison(x):
        nonlocal injected
        if injected: return x
        if isinstance(x, dict):
            for k in list(x):
                if isinstance(x[k], (list, dict)): poison(x[k])
                elif isinstance(x[k], float) and not injected and k not in ('rel_tol',): x[k] = float('nan'); injected = True; return x
        elif isinstance(x, list):
            for i, v in enumerate(x):
                if isinstance(v, (list, dict)): poison(v)
                elif isinstance(v, float) and not injected: x[i] = float('nan'); injected = True; return x
        return x
    poison(ev.get('observed') if isinstance(ev.get('observed'), (dict, list)) else ev)
    if injected:
        bad = dict(rec, result=ser.to_jsonable(res)); bad['result_sha256'] = wc._result_sha(res)
        with pytest.raises(Exception): _restore(bad)
    # a mixed list (one valid, one tampered) is refused as a whole
    with pytest.raises(InputContractError): wc.restore_w2_context([rec, dict(rec, key='E2/L1.20', size_id='L1.20', manifest_sha256='4' * 64)], wc.registered_shared_null_asset(P), require_formal=False)


@need_ext
def test_d2w_script_refusals(w2_small, tmp_path):
    bank, base = w2_small['bank'], w2_small['base']; ST = ['--selftest-small', '--selftest-skip-env-lock', '--selftest-cases', 'E2/L1.00']
    # OUT contract: inside an input / the source / phasec / symlink / non-empty -> rc 2, nothing written in the inputs
    before = sorted(os.listdir(bank))
    for bad in (os.path.join(bank, 'x_out'), os.path.join(P, 'd', 'x_out'), os.path.join(PC, 'x_out')):
        r = _run(base + ['--out', bad, *ST]); assert r.returncode == 2 and not os.path.exists(bad)
    link = tmp_path / 'link'; tgt = tmp_path / 'tgt'; tgt.mkdir(); os.symlink(tgt, link); r = _run(base + ['--out', str(link), *ST]); assert r.returncode == 2 and os.listdir(tgt) == []
    r = _run(base + ['--out', w2_small['out'], *ST]); assert r.returncode == 2 and sorted(os.listdir(bank)) == before
    # inputs unresolved: a family root missing for the requested case; a case key outside the plan; a root without the units; the formal path on a non-formal (small) bank
    o = tmp_path / 'u1'; r = _run([D2W, '--mt', MT, '--phaseb', P, '--phasec', PC, '--d2-root', f'E7={bank}', '--out', str(o), *ST]); m = json.load(open(o / 'd2w_run_record.json')); assert r.returncode == 1 and m['gates']['G_d2_inputs_resolved'] is False and m['stage'] == 'inputs' and m['D2W_PASS'] is False
    o = tmp_path / 'u2'; r = _run(base + ['--out', str(o), '--selftest-small', '--selftest-skip-env-lock', '--selftest-cases', 'E2/L9.99']); m = json.load(open(o / 'd2w_run_record.json')); assert r.returncode == 1 and m['stage'] == 'inputs' and m['gates']['G_d2_inputs_resolved'] is None
    empty = tmp_path / 'empty_root'; empty.mkdir(); o = tmp_path / 'u3'; r = _run([D2W, '--mt', MT, '--phaseb', P, '--phasec', PC, '--d2-root', f'E2={empty}', '--out', str(o), *ST]); m = json.load(open(o / 'd2w_run_record.json')); assert r.returncode == 1 and m['gates']['G_d2_inputs_resolved'] is False
    o = tmp_path / 'u4'; r = _run(base + ['--out', str(o), '--selftest-skip-env-lock', '--selftest-cases', 'E2/L1.00']); m = json.load(open(o / 'd2w_run_record.json'))      # no --selftest-small: formal intake on K = 50 refused
    assert r.returncode == 1 and m['D2W_PASS'] is False and m['gates']['G_cases_assembled'] is not True and (m['stage'] in ('inputs', 'exception', 'intake')) and not os.path.exists(o / 'd2w_context_record.json')
    o = tmp_path / 'u5'; r = _run(base + ['--out', str(o), *ST, '--profile', 'other']); assert r.returncode == 1 and json.load(open(o / 'd2w_run_record.json'))['D2W_PASS'] is False
    # a tampered unit (one byte of the NPZ) is refused by the strong intake (G_cases_assembled False / exception), never evaluated
    tb = tmp_path / 'tampered'; shutil.copytree(bank, tb); f = tb / 'cfg20102_w2' / 'cfg20102_w2_s0.npz'; b = bytearray(open(f, 'rb').read()); b[-1] ^= 1; open(f, 'wb').write(b)
    o = tmp_path / 'u6'; r = _run([D2W, '--mt', MT, '--phaseb', P, '--phasec', PC, '--d2-root', f'E2={tb}', '--out', str(o), *ST]); m = json.load(open(o / 'd2w_run_record.json')); assert r.returncode == 1 and m['gates']['G_context_built'] is None and 'evaluation_seconds' not in m['timings']


@need_ext
def test_d2w_assemble_binds_registered_units_and_roots(w2_small):
    """assemble_w2_cases: the registered-units path binds every unit's manifest SHA to the ledger unit (mismatch refused); a wrong matched root is refused by the intake; a missing root / family is refused."""
    bank, table, roots = w2_small['bank'], w2_small['table'], w2_small['roots']
    cases, infos = wc.assemble_w2_cases({'E2': bank}, roots, table, formal=False, families=('E2',), sizes=('L1.00',))
    assert set(cases) == {'E2/L1.00'} and len(cases['E2/L1.00']['positions']) == 3 and cases['E2/L1.00']['size_id'] == 'L1.00' and infos['E2/L1.00']['formal'] is False and [p.position_id for p in cases['E2/L1.00']['positions']] == [20101, 20102, 20103]
    units = {u: dict(manifest_sha256=v['manifest_sha256']) for u, v in infos['E2/L1.00']['units'].items()}
    c2, i2 = wc.assemble_w2_cases({'E2': bank}, roots, table, formal=False, registered_units=units, families=('E2',), sizes=('L1.00',)); assert i2['E2/L1.00']['units'] == infos['E2/L1.00']['units']
    with pytest.raises(InputContractError): wc.assemble_w2_cases({'E2': bank}, roots, table, formal=False, registered_units=dict(units, cfg20102_w2=dict(manifest_sha256='0' * 64)), families=('E2',), sizes=('L1.00',))
    with pytest.raises(InputContractError): wc.assemble_w2_cases({'E2': bank}, roots, table, formal=False, registered_units={k: v for k, v in units.items() if k != 'cfg20103_w2'}, families=('E2',), sizes=('L1.00',))
    with pytest.raises(InputContractError): wc.assemble_w2_cases({'E2': bank}, {**roots, 20101: roots[20102]}, table, formal=False, families=('E2',), sizes=('L1.00',))
    with pytest.raises(InputContractError): wc.assemble_w2_cases({'E2': bank}, {k: v for k, v in roots.items() if k != 20101}, table, formal=False, families=('E2',), sizes=('L1.00',))
    with pytest.raises(InputContractError): wc.assemble_w2_cases({'E7': bank}, roots, table, formal=False, families=('E2',), sizes=('L1.00',))
    with pytest.raises(InputContractError): wc.assemble_w2_cases({'E2': bank}, roots, table, formal=True, families=('E2',), sizes=('L1.00',))        # formal intake refuses the small bank
    with pytest.raises(InputContractError): wc.assemble_w2_cases({'E2': bank}, roots, table, formal=False, families=('E2',), sizes=('L1.20',))      # units of L1.20 absent


# ================================================================================================================================================= notebooks
@pytest.mark.parametrize('nb_path,script,lock_name,fin_name,pass_key,rec_key', [(NB_D2W, 'd2w_cases.py', 'd2w_lock.json', 'd2w_final_record.json', 'D2W_PASS', 'd2w_run_record.json'), (NB_PSE, 'd4_pseudo.py', 'd4_pseudo_lock.json', 'd4_pseudo_final_record.json', 'PSEUDO_PASS', 'd4_pseudo_record.json')])
def test_notebooks_structure(nb_path, script, lock_name, fin_name, pass_key, rec_key):
    import ast
    nb = json.load(open(nb_path)); assert len(nb['cells']) == 5 and nb['cells'][0]['cell_type'] == 'markdown' and all(c['cell_type'] == 'code' and c['outputs'] == [] for c in nb['cells'][1:])
    c1, c2, c3, c4 = (''.join(nb['cells'][i]['source']) for i in (1, 2, 3, 4))
    for c in (c1, c2, c3, c4): ast.parse(c)
    assert 'REPO_COMMIT' in c1 and 'EXPECTED_INVENTORY_SHA256' in c1 and ('--selftest' not in c1 + c2 + c3) and "v.get('selftest') is False" in c3
    assert f"d/{script}" in c2 and '# LOCK-BUILD' in c2 and f"'{lock_name}'" in c2.replace('/', "'") or f"/{lock_name}" in c2
    assert "ANCHOR=lock['out']" in c3 and c3.count("_verify_locked_state('precheck')") == 1 and c3.count("_verify_locked_state('prelaunch')") == 1 and 'superseded_final_record_before_' in c3 and fin_name in c3 and pass_key in c3 and rec_key in c3 and "'--attempt-id',ATTEMPT,'--launcher-lock-sha256',LOCK_SHA256" in c3
    assert "'--profile','production_official'" in c3 and 'evidence_ok' in c3 and ('sha(fp)==' in c3) and 'rev-parse' in c3 and 'status' in c3
    if script == 'd2w_cases.py': assert "D2_RUN_ROOTS" in c1 and 'd2_generation_ledger.json' in c2 and 'b3_2_shared_null_asset.json' in c2 and "'--d2-root'" in c3 and 'cfg\\d+_w2' in c3 and 'len(cases)!=9' in c3
    else: assert 'd4_pseudo_table.json' in c2 and "d4_pseudo_table_sha256" in c2 and "idn.get('n')==2000" in c3 and 'd4_pseudo_columns.npz' in c3 and 'STAGE' not in c1


NB_CASES = ['ok', 'staged_ok', 'retry_after_old_success', 'pass_false', 'rc1', 'missing_record', 'commit_changed', 'script_changed', 'root_changed', 'lock_file_changed', 'script_changed_during_staging', 'anchor_symlink', 'evidence_tampered', 'evidence_missing', 'fewer_cases', 'result_attempt_mismatch', 'result_source_mismatch', 'launch_failure', 'disk_insufficient']
NO_LAUNCH = {'commit_changed', 'script_changed', 'root_changed', 'lock_file_changed', 'script_changed_during_staging', 'disk_insufficient'}
STAGED = {'staged_ok', 'script_changed_during_staging', 'disk_insufficient'}


def _fake_source_d2w(root):
    pb = root / 'engine' / 'phaseB'; (pb / 'd').mkdir(parents=True); (pb / 'registered_assets' / 'd2').mkdir(parents=True); (root / 'phaseC').mkdir()
    (pb / 'd' / 'd2w_cases.py').write_text('# TEST_ONLY script stand-in\n'); (pb / 'd' / 'd3_pins.json').write_text(json.dumps(dict(schema='d3_pins_v1')))
    (pb / 'registered_assets' / 'd2' / 'd2_generation_ledger.json').write_text(json.dumps(dict(families={}))); (pb / 'registered_assets' / 'b3_2_shared_null_asset.json').write_text('{}')
    inv = dict(engine_version='0.0.0-TEST', d_sha256={'d/d2w_cases.py': sha(pb / 'd' / 'd2w_cases.py'), 'd/d3_pins.json': sha(pb / 'd' / 'd3_pins.json')}, registered_assets_sha256={'registered_assets/d2/d2_generation_ledger.json': sha(pb / 'registered_assets' / 'd2' / 'd2_generation_ledger.json'), 'registered_assets/b3_2_shared_null_asset.json': sha(pb / 'registered_assets' / 'b3_2_shared_null_asset.json')})
    (pb / 'B2_completion_inventory.json').write_text(json.dumps(inv)); return str(root), str(pb)


@pytest.mark.parametrize('case', NB_CASES)
def test_d2w_notebook_attempt_cell_binds_lock_and_records_failures(tmp_path, case):
    nb = json.load(open(NB_D2W)); c2 = ''.join(nb['cells'][2]['source']); c3 = ''.join(nb['cells'][3]['source']); lock_src = c2[c2.index('# LOCK-BUILD'):]
    commit = 'a' * 40; mt, pb = _fake_source_d2w(tmp_path / 'scratch'); out = tmp_path / 'out'; out.mkdir(); roots = {}
    for f in ('E2', 'E7', 'E8'):
        d = tmp_path / f'in_{f}'; (d / 'cfg20101_w2').mkdir(parents=True); (d / 'cfg20101_b0').mkdir(); (d / 'd2_bank_registry.json').write_text('{}'); (d / 'cfg20101_w2' / 'blob.npz').write_bytes(b'\0' * 1000); (d / 'cfg20101_b0' / 'big.npz').write_bytes(b'\0' * 5000); roots[f] = str(d)
    staged = case in STAGED
    ns = dict(sys=sys, os=os, json=json, hashlib=hashlib, shutil=shutil, time=__import__('time'), re=re, sha=sha, REPO_COMMIT=commit, D2_RUN_ROOTS=dict(roots), STAGE_LOCAL=staged, STAGE_ROOT=str(tmp_path / 'stage'), MT=mt, PHASEB=pb, PHASEC=f'{mt}/phaseC', SCRIPT=f'{pb}/d/d2w_cases.py', INV=f'{pb}/B2_completion_inventory.json',
              LEDGER=f'{pb}/registered_assets/d2/d2_generation_ledger.json', ASSET=f'{pb}/registered_assets/b3_2_shared_null_asset.json', PINS=f'{pb}/d/d3_pins.json', OUT=str(out), RAM_INFO=dict(total_bytes=1))
    ns['inv'] = json.load(open(ns['INV']))
    with contextlib.redirect_stdout(io.StringIO()): exec(compile(lock_src, 'nb_cell2_lock', 'exec'), ns)
    lock = ns['lock']; lock_sha = ns['LOCK_SHA256']; assert sha(ns['LOCK_PATH']) == lock_sha and lock['stage_local'] is staged and lock['schema'] == 'd2w_launcher_lock_v1'
    old = dict(schema='TEST_ONLY_old', d2w_pass=True, stage='complete', attempt_id='OLD_ATTEMPT')
    if case == 'retry_after_old_success': (out / 'd2w_final_record.json').write_text(json.dumps(old))
    if case == 'root_changed': ns['D2_RUN_ROOTS'] = dict(roots, E7=str(tmp_path / 'other')); os.makedirs(ns['D2_RUN_ROOTS']['E7'])
    if case == 'script_changed': open(ns['SCRIPT'], 'a').write('# changed after the lock\n')
    if case == 'lock_file_changed': open(ns['LOCK_PATH'], 'a').write('\n')
    if case == 'anchor_symlink': link_target = tmp_path / 'anchor_target'; shutil.move(str(out), str(link_target)); os.symlink(link_target, out)
    git = dict(head=('b' * 40 if case == 'commit_changed' else commit), dirty='')
    n_copies = [0]
    def copytree_then_mutate(src, dst, **kw):
        r = shutil.copytree(src, dst, **kw); n_copies[0] += 1
        if n_copies[0] == 3 and case == 'script_changed_during_staging': open(ns['SCRIPT'], 'a').write('# changed during staging\n')
        return r
    calls = []
    def check_output(args, **kw): return (git['head'] if 'rev-parse' in args else git['dirty']) + '\n'
    def run(args, **kw):
        calls.append(list(args))
        if case == 'launch_failure': raise OSError('TEST_ONLY cannot start subprocess')
        run_dir = args[args.index('--out') + 1]; att = args[args.index('--attempt-id') + 1]; lk = args[args.index('--launcher-lock-sha256') + 1]; os.makedirs(os.path.join(run_dir, 'cases'))
        keys = [f'{f}/{s}' for f in ('E2', 'E7', 'E8') for s in ('L1.00', 'L1.20', 'L1.50')]
        if case == 'fewer_cases': keys = keys[:8]
        pe = {}; cases = {}
        for k in keys:
            fn = f"d2w_case_{k.replace('/', '_')}.json"; data = json.dumps(dict(schema='TEST_ONLY_case', key=k)).encode(); open(os.path.join(run_dir, 'cases', fn), 'wb').write(data); pe[fn] = dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)); cases[k] = dict(trigger='unknown', validation_state='w2-unresolved', B_final=400, manifest_sha256='m' * 64, result_sha256='r' * 64)
        data = json.dumps(dict(schema='TEST_ONLY_context')).encode(); open(os.path.join(run_dir, 'd2w_context_record.json'), 'wb').write(data); pe['d2w_context_record.json'] = dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
        if case == 'evidence_tampered': open(os.path.join(run_dir, 'cases', 'd2w_case_E7_L1.20.json'), 'ab').write(b' ')
        if case == 'evidence_missing': os.remove(os.path.join(run_dir, 'd2w_context_record.json'))
        rec = dict(schema='d2w_run_record_v1', stage='complete', failures=[], selftest=False, profile='production_official', attempt=dict(attempt_id=('OTHER' if case == 'result_attempt_mismatch' else att), launcher_lock_sha256=lk), source=dict(script_sha256=('0' * 64 if case == 'result_source_mismatch' else lock['script_sha256']), inventory_sha256=lock['inventory_sha256'], pins_sha256=lock['pins_sha256'], engine_version=lock['engine']),
                   gates={'G_x': True}, stages_rss_mb=dict(final=1.0), stages_peak_rss_mb=dict(final=1.0), seconds=1.5, context=dict(context_sha256='c' * 64, asset_sha256='s' * 64, cases=cases), published_evidence=pe, D2W_PASS=(case != 'pass_false'))
        if case != 'missing_record': open(os.path.join(run_dir, 'd2w_run_record.json'), 'w').write(json.dumps(rec))
        class R: returncode = 1 if case == 'rc1' else 0; stdout = 'TEST'; stderr = ''
        return R()
    ns['subprocess'] = type('SP', (), dict(check_output=staticmethod(check_output), run=staticmethod(run)))
    ns['shutil'] = type('SH', (), dict(copytree=staticmethod(copytree_then_mutate), copy2=staticmethod(shutil.copy2), rmtree=staticmethod(shutil.rmtree), disk_usage=staticmethod(lambda p: type('DU', (), dict(free=(0 if case == 'disk_insufficient' else 10**12)))())))
    buf = io.StringIO()
    if case == 'anchor_symlink':
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()), pytest.raises(RuntimeError): exec(compile(c3, 'nb_cell3', 'exec'), ns)
        assert not os.path.exists(link_target / 'd2w_final_record.json') and sorted(os.listdir(link_target)) == ['d2w_lock.json'] and calls == []; return
    with contextlib.redirect_stdout(buf): exec(compile(c3, 'nb_cell3', 'exec'), ns)
    fin = json.load(open(out / 'd2w_final_record.json')); assert fin['schema'] == 'd2w_launcher_final_record_v1' and fin['lock_sha256'] == lock_sha and fin['attempt_id'] == ns['ATTEMPT'] and fin['output_anchor'] == str(out)
    if case in NO_LAUNCH: assert calls == [] and fin['d2w_pass'] is False and fin['failures'] and fin['exception']; return
    if case == 'launch_failure': assert fin['d2w_pass'] is False and fin['stage'] == 'launch'; return
    assert len(calls) == 1 and calls[0][1] == ns['SCRIPT'] and '--selftest-small' not in calls[0] and calls[0][calls[0].index('--attempt-id') + 1] == ns['ATTEMPT'] and sorted(x.split('=')[0] for x in calls[0] if '=' in x and x.split('=')[0] in ('E2', 'E7', 'E8')) == ['E2', 'E7', 'E8']
    if staged: assert all(x.split('=', 1)[1].startswith(str(tmp_path / 'stage')) for x in calls[0] if x.startswith(('E2=', 'E7=', 'E8='))) and fin['staging']['units'] == dict(E2=1, E7=1, E8=1) and fin['staging']['input_bytes'] == 3 * (1000 + 2) and not os.path.exists(tmp_path / 'stage' / 'd2_E2' / 'cfg20101_b0')
    else: assert all(x.split('=', 1)[1] == roots[x[:2]] for x in calls[0] if x.startswith(('E2=', 'E7=', 'E8=')))
    if case in ('ok', 'staged_ok', 'retry_after_old_success'):
        assert fin['d2w_pass'] is True and fin['failures'] == [] and fin['D2W_PASS'] is True and fin['bindings_ok'] is True and fin['evidence_ok'] is True and fin['launcher_fallback'] is False and len(fin['case_outcomes']) == 9 and set(fin['bindings']) == {'live_source_precheck', 'live_source_prelaunch'}
        if case == 'retry_after_old_success': assert json.load(open(fin['superseded_previous_record'])) == old and fin['attempt_id'] != 'OLD_ATTEMPT'
        return
    assert fin['d2w_pass'] is False
    if case == 'pass_false': assert fin['D2W_PASS'] is False and fin['failures'] == []
    if case == 'rc1': assert fin['exit_code'] == 1 and fin['D2W_PASS'] is True
    if case == 'missing_record': assert fin['launcher_fallback'] is True and fin['bindings_ok'] is None
    if case in ('evidence_tampered', 'evidence_missing', 'fewer_cases'): assert fin['evidence_ok'] is False and fin['bindings_ok'] is True
    if case in ('result_attempt_mismatch', 'result_source_mismatch'): assert fin['bindings_ok'] is False and fin['evidence_ok'] is True


PSE_CASES = ['ok', 'retry_after_old_success', 'pass_false', 'rc1', 'missing_record', 'commit_changed', 'table_changed', 'lock_file_changed', 'anchor_symlink', 'columns_tampered', 'columns_small_n', 'result_attempt_mismatch', 'table_sha_mismatch', 'launch_failure']


def _fake_source_pse(root):
    pb = root / 'engine' / 'phaseB'; (pb / 'd').mkdir(parents=True); (root / 'phaseC').mkdir()
    (pb / 'd' / 'd4_pseudo.py').write_text('# TEST_ONLY script stand-in\n'); (pb / 'd' / 'd3_pins.json').write_text(json.dumps(dict(schema='d3_pins_v1', d4_pseudo_table_sha256='t' * 64))); (pb / 'd' / 'd4_pseudo_table.json').write_text(json.dumps(dict(table_sha256='t' * 64, n_pseudo=2000, m=1)))
    inv = dict(engine_version='0.0.0-TEST', d_sha256={'d/d4_pseudo.py': sha(pb / 'd' / 'd4_pseudo.py'), 'd/d3_pins.json': sha(pb / 'd' / 'd3_pins.json'), 'd/d4_pseudo_table.json': sha(pb / 'd' / 'd4_pseudo_table.json')})
    (pb / 'B2_completion_inventory.json').write_text(json.dumps(inv)); return str(root), str(pb)


@pytest.mark.parametrize('case', PSE_CASES)
def test_pseudo_notebook_attempt_cell_binds_lock_and_records_failures(tmp_path, case):
    nb = json.load(open(NB_PSE)); c2 = ''.join(nb['cells'][2]['source']); c3 = ''.join(nb['cells'][3]['source']); lock_src = c2[c2.index('# LOCK-BUILD'):]
    commit = 'a' * 40; mt, pb = _fake_source_pse(tmp_path / 'scratch'); out = tmp_path / 'out'; out.mkdir()
    ns = dict(sys=sys, os=os, json=json, hashlib=hashlib, shutil=shutil, time=__import__('time'), re=re, sha=sha, REPO_COMMIT=commit, MT=mt, PHASEB=pb, PHASEC=f'{mt}/phaseC', SCRIPT=f'{pb}/d/d4_pseudo.py', INV=f'{pb}/B2_completion_inventory.json', TABLE=f'{pb}/d/d4_pseudo_table.json', PINS=f'{pb}/d/d3_pins.json', OUT=str(out), RAM_INFO=dict(total_bytes=1))
    ns['inv'] = json.load(open(ns['INV'])); ns['table'] = json.load(open(ns['TABLE']))
    with contextlib.redirect_stdout(io.StringIO()): exec(compile(lock_src, 'nb_cell2_lock', 'exec'), ns)
    lock = ns['lock']; lock_sha = ns['LOCK_SHA256']; assert sha(ns['LOCK_PATH']) == lock_sha and lock['schema'] == 'd4_pseudo_launcher_lock_v1' and lock['table_sha256'] == 't' * 64
    old = dict(schema='TEST_ONLY_old', pseudo_pass=True, stage='complete', attempt_id='OLD_ATTEMPT')
    if case == 'retry_after_old_success': (out / 'd4_pseudo_final_record.json').write_text(json.dumps(old))
    if case == 'table_changed': open(ns['TABLE'], 'a').write('\n')
    if case == 'lock_file_changed': open(ns['LOCK_PATH'], 'a').write('\n')
    if case == 'anchor_symlink': link_target = tmp_path / 'anchor_target'; shutil.move(str(out), str(link_target)); os.symlink(link_target, out)
    git = dict(head=('b' * 40 if case == 'commit_changed' else commit), dirty=''); calls = []
    def check_output(args, **kw): return (git['head'] if 'rev-parse' in args else git['dirty']) + '\n'
    def run(args, **kw):
        calls.append(list(args))
        if case == 'launch_failure': raise OSError('TEST_ONLY cannot start subprocess')
        run_dir = args[args.index('--out') + 1]; att = args[args.index('--attempt-id') + 1]; lk = args[args.index('--launcher-lock-sha256') + 1]; os.makedirs(run_dir)
        data = b'TEST_ONLY_NPZ'; open(os.path.join(run_dir, 'd4_pseudo_columns.npz'), 'wb').write(data); fe = dict(file='d4_pseudo_columns.npz', sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
        if case == 'columns_tampered': open(os.path.join(run_dir, 'd4_pseudo_columns.npz'), 'ab').write(b' ')
        idn = dict(n=(50 if case == 'columns_small_n' else 2000), m=1, paired_sha256='p' * 64)
        rec = dict(schema='d4_pseudo_record_v1', stage='complete', failures=[], selftest=False, profile='production_official', attempt=dict(attempt_id=('OTHER' if case == 'result_attempt_mismatch' else att), launcher_lock_sha256=lk), source=dict(script_sha256=lock['script_sha256'], inventory_sha256=lock['inventory_sha256'], pins_sha256=lock['pins_sha256'], engine_version=lock['engine']),
                   gates={'G_x': True}, stages_rss_mb=dict(final=1.0), stages_peak_rss_mb=dict(final=1.0), seconds=1.5, pseudo_table=dict(table_sha256=('u' * 64 if case == 'table_sha_mismatch' else 't' * 64)), columns=dict(identity=idn, file=fe), PSEUDO_PASS=(case != 'pass_false'))
        if case != 'missing_record': open(os.path.join(run_dir, 'd4_pseudo_record.json'), 'w').write(json.dumps(rec))
        class R: returncode = 1 if case == 'rc1' else 0; stdout = 'TEST'; stderr = ''
        return R()
    ns['subprocess'] = type('SP', (), dict(check_output=staticmethod(check_output), run=staticmethod(run)))
    buf = io.StringIO()
    if case == 'anchor_symlink':
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()), pytest.raises(RuntimeError): exec(compile(c3, 'nb_cell3', 'exec'), ns)
        assert sorted(os.listdir(link_target)) == ['d4_pseudo_lock.json'] and calls == []; return
    with contextlib.redirect_stdout(buf): exec(compile(c3, 'nb_cell3', 'exec'), ns)
    fin = json.load(open(out / 'd4_pseudo_final_record.json')); assert fin['schema'] == 'd4_pseudo_launcher_final_record_v1' and fin['lock_sha256'] == lock_sha and fin['attempt_id'] == ns['ATTEMPT']
    if case in ('commit_changed', 'table_changed', 'lock_file_changed'): assert calls == [] and fin['pseudo_pass'] is False and fin['exception']; return
    if case == 'launch_failure': assert fin['pseudo_pass'] is False and fin['stage'] == 'launch'; return
    assert len(calls) == 1 and '--selftest-n' not in calls[0] and calls[0][calls[0].index('--attempt-id') + 1] == ns['ATTEMPT'] and set(fin['bindings']) == {'live_source_precheck', 'live_source_prelaunch'}
    if case in ('ok', 'retry_after_old_success'):
        assert fin['pseudo_pass'] is True and fin['failures'] == [] and fin['bindings_ok'] is True and fin['evidence_ok'] is True and fin['columns_identity']['n'] == 2000
        if case == 'retry_after_old_success': assert json.load(open(fin['superseded_previous_record'])) == old
        return
    assert fin['pseudo_pass'] is False
    if case == 'pass_false': assert fin['PSEUDO_PASS'] is False and fin['failures'] == []
    if case == 'rc1': assert fin['exit_code'] == 1
    if case == 'missing_record': assert fin['launcher_fallback'] is True
    if case in ('columns_tampered', 'columns_small_n'): assert fin['evidence_ok'] is False and fin['bindings_ok'] is True
    if case in ('result_attempt_mismatch', 'table_sha_mismatch'): assert fin['bindings_ok'] is False
