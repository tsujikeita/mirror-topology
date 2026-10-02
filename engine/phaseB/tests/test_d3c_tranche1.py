# -*- coding: utf-8 -*-
"""D-3c tranche 1 (v2) contracts (d/d3c_profile.py + notebook): on synthetic small banks of the generators' self-tests (D-2 first-wave + family reference, D-3b added; real
covariance roots; TEST-ONLY kernel) the profile script performs formal-shaped intake (formal=False in self-test) -> ordered-UID / K_fit checks -> ONE family-shared five-seed
plan (roundtrip reconstruction released right after its comparison) -> size inputs (each carrying the SAME plan objects) -> all-size assembly -> fingerprints -> smoke gate
(live environment; keyword plan identity) -> identity re-check (content AND exact plan-object identity of both systems and all size inputs) -> verified publication; D3C_PASS
is never True in self-test; the published plan identity is reproducible from the recorded ORDERED UIDs in a separate process; reversed UIDs give another identity.
R-D3C1-C: in-process runs that replace a plan dictionary by a value-equal deepcopy (native / matched; evaluation / fitting; after the gate or inside a size input) are
refused (G_identity_stable / G_size_inputs False), an array change after the gate is refused (content), the normal shared plans pass.
R-D3C1-D: OUT below --phasec / --mt / --phaseb / an input root -> rc 2 and nothing written; a symlink OUT -> rc 2; a pre-existing EMPTY OUT is accepted (record written in it).
R-D3C1-A/B (notebook attempt cell): configuration / live-source mismatch with the lock is refused BEFORE staging / launch; staging copy failure, insufficient disk, launch
failure, missing / invalid / nested-invalid records and result records not bound to this attempt / lock / family all leave a FAIL record of THIS attempt (a previous success
is superseded, never reused); only the fully bound success gives profile_pass."""
import os, sys, json, shutil, subprocess, hashlib, copy, importlib.util, io, contextlib, types
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine.d3_profile import twelve_context, fix_family_plans, verify_plan_identity
from step1_engine.errors import InputContractError
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); MT = os.environ.get('B3_MT', '/home/claude/mt'); PC = os.environ.get('PHASEC_ROOT', '/home/claude/phaseC')
GEN2 = os.path.join(P, 'd', 'd2_bankgen.py'); GEN3 = os.path.join(P, 'd', 'd3_bankgen.py'); PROF = os.path.join(P, 'd', 'd3c_profile.py'); NB = os.path.join(P, 'd', 'MirrorTopology_Step1_D3c_profile_v0.1.ipynb')
need_ext = pytest.mark.skipif(not (os.path.exists(os.path.join(MT, 't1_engine.py')) and os.path.isdir(PC)), reason='external assets not present')
ENV = dict(os.environ, PIP_BREAK_SYSTEM_PACKAGES='1', OPENBLAS_NUM_THREADS='1'); ST = ('--selftest-scale', '0.001', '--selftest-skip-a10', '--selftest-skip-env-lock')
SELF = ('--selftest-small', '--selftest-skip-env-lock', '--selftest-sizes', 'L1.00'); sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()


def _run(args, timeout=200): return subprocess.run([sys.executable, *args], capture_output=True, text=True, env=ENV, timeout=timeout)


def _rec(out, fam='E2'): return json.load(open(os.path.join(out, f'd3c_profile_record_{fam}.json')))


@pytest.fixture(scope='module')
def banks(tmp_path_factory):
    """Synthetic small D-2 (E2) and D-3b (E2 L1.00) banks of the generators' self-tests; generated once per module."""
    if not (os.path.exists(os.path.join(MT, 't1_engine.py')) and os.path.isdir(PC)): pytest.skip('external assets not present')
    root = tmp_path_factory.mktemp('d3c_banks'); d2 = root / 'd2'; d3 = root / 'd3b_L100'
    r = _run([GEN2, '--mt', MT, '--phaseb', P, '--phasec', PC, '--out', str(d2), '--family', 'E2', *ST]); assert json.load(open(d2 / 'd2_run_manifest.json'))['stage'] == 'complete', r.stdout[-500:]
    r = _run([GEN3, '--mt', MT, '--phaseb', P, '--phasec', PC, '--out', str(d3), '--family', 'E2', '--sizes', 'L1.00', *ST]); assert json.load(open(d3 / 'd3_run_manifest.json'))['stage'] == 'complete', r.stdout[-500:]
    return dict(d2=str(d2), d3=str(d3), base=[PROF, '--mt', MT, '--phaseb', P, '--phasec', PC, '--family', 'E2', '--d2-root', str(d2)])


def _all_shared(d): return all(v == dict(plans_is_fixed=True, fit_plans_is_fixed=True) for v in d.values())


@need_ext
def test_profile_script_selftest_end_to_end_and_refusals(banks, tmp_path):
    d2, d3, base = banks['d2'], banks['d3'], banks['base']
    # self-test end to end (one size); attempt / lock echo; plan-object identity recorded for size inputs and both systems before and after the gate; peak RSS per stage
    out = tmp_path / 'prof'; r = _run(base + ['--out', str(out), '--d3b-root', f'L1.00={d3}', *SELF, '--attempt-id', 'TEST_ATTEMPT_1', '--launcher-lock-sha256', 'f' * 64]); m = _rec(out)
    assert r.returncode == 1 and m['stage'] == 'complete' and m['D3C_PASS'] is False and m['selftest'] is True and m['gates']['G_env_lock'] is False and all(m['gates'][g] is True for g in m['required_inventory'] if g != 'G_env_lock')
    assert m['gate']['mode'] == 'smoke' and m['gate']['passed'] is True and m['gate']['diagnostics']['environment_source'] == 'live_collected' and all(c['passed'] for c in m['gate']['diagnostics']['twelve_checks'] if c['code'].endswith(('plan_identity_fixed', 'first_wave_and_added_share_plans', 'pc1_pass_all', 'twelve_per_size')))
    assert len(m['supplies']) == 24 and sum(v['origin'] == 'first_wave_D1' for v in m['supplies'].values()) == 6 and sum(v['origin'] == 'twelve_added_D3a' for v in m['supplies'].values()) == 18 and all(v['n_clusters'] == {'0': 10, '1': 30} for v in m['supplies'].values())
    assert m['uids'] == dict(m['uids'], K0=10, K1=30, m=100, K_fit=2, n_fit=200, evaluation_group=1002, first_uid=[1, 200, 1002, 0, 0], last_uid=[1, 200, 1002, 1, 29]) and m['input_fingerprints_before_gate']['matched'] == m['input_fingerprints_after_gate']['matched'] and m['input_fingerprints_before_gate']['native'] == m['input_fingerprints_after_gate']['native'] and m['input_fingerprints_before_gate']['matched'] != m['input_fingerprints_before_gate']['native']
    assert m['family_identity']['full_surviving_scope'] is False and m['family_identity']['stage'] == 'twelve' and m['publication_stage'] == 'plan_identity_verified' and set(m['stages_rss_mb']) >= {'preflight', 'intake', 'plans', 'size_inputs', 'assembly', 'gate', 'final'} and set(m['stages_peak_rss_mb']) == set(m['stages_rss_mb'])
    poi = m['plan_object_identity']; assert set(poi) == {'size_inputs_before_gate', 'assembled_before_gate', 'size_inputs_after_gate', 'assembled_after_gate'} and set(poi['size_inputs_before_gate']) == {'L1.00/matched', 'L1.00/native'} and set(poi['assembled_after_gate']) == {'family/matched', 'family/native'} and all(_all_shared(poi[k]) for k in poi)
    assert m['attempt'] == dict(attempt_id='TEST_ATTEMPT_1', launcher_lock_sha256='f' * 64) and m['source'] == dict(m['source'], script_sha256=sha(PROF), inventory_sha256=sha(os.path.join(P, 'B2_completion_inventory.json')), engine_version=m['engine_version']) and m['out_preexisting_empty'] is False and set(m['protected_roots']) == {'mt', 'phaseb', 'phasec', 'd2_root', 'd3b_root_L1.00'} and m['roundtrip_plans_peak_rss_mb'] > 0
    pb = open(out / 'd3c_plan_identity_E2.json', 'rb').read(); assert m['published_evidence']['d3c_plan_identity_E2.json'] == dict(sha256=hashlib.sha256(pb).hexdigest(), bytes=len(pb)); pd = json.loads(pb)
    assert pd['identity']['identity_sha256'] == m['plan_identity_sha256'] and pd['formal'] is False and pd['B'] == 20 and pd['B_KDE'] == 25 and pd['seeds'] == 5 and len(pd['ordered_uids']['0']) == 10 and len(pd['ordered_uids']['1']) == 30 and 'SELF-TEST' in pd['constants_source'] and pd['attempt'] == m['attempt'] and pd['source_lock']['script_sha256'] == sha(PROF)
    # plan identity roundtrip in THIS (separate) process from the recorded ordered UIDs; reversed UIDs give another identity
    ctx = twelve_context(P); table = ctx.table
    plans, fplans, ident = fix_family_plans(table, 'E2', {0: [tuple(u) for u in pd['ordered_uids']['0']], 1: [tuple(u) for u in pd['ordered_uids']['1']]}, pd['K_fit'], pd['master_seed'], B=pd['B'], B_KDE=pd['B_KDE'])
    assert ident == pd['identity'] and verify_plan_identity(plans, fplans, pd['identity'], table=table, family='E2')
    plans_rev, fplans_rev, rev = fix_family_plans(table, 'E2', {0: [tuple(u) for u in pd['ordered_uids']['0']][::-1], 1: [tuple(u) for u in pd['ordered_uids']['1']]}, pd['K_fit'], pd['master_seed'], B=pd['B'], B_KDE=pd['B_KDE']); assert rev['identity_sha256'] != ident['identity_sha256']
    with pytest.raises(InputContractError): verify_plan_identity(plans_rev, fplans_rev, pd['identity'], table=table, family='E2')
    # R-D3C1-D: OUT below an input / --phaseb / --phasec / --mt -> rc 2 and NOTHING written; a symlink OUT -> rc 2; a pre-existing EMPTY OUT is accepted and used
    for bad_out in (os.path.join(d2, 'review'), os.path.join(P, 'should_not_exist'), os.path.join(PC, 'should_not_exist'), os.path.join(MT, 'should_not_exist'), os.path.join(d3, 'cfg20104_b0', 'x')):
        assert _run(base + ['--out', bad_out, '--d3b-root', f'L1.00={d3}', *SELF]).returncode == 2 and not os.path.lexists(bad_out), bad_out
    real = tmp_path / 'real_target'; real.mkdir(); link = tmp_path / 'link_out'; os.symlink(real, link); assert _run(base + ['--out', str(link), '--d3b-root', f'L1.00={d3}', *SELF]).returncode == 2 and not os.listdir(real)
    (tmp_path / 'nonempty').mkdir(); (tmp_path / 'nonempty' / 'x').write_text('x'); assert _run(base + ['--out', str(tmp_path / 'nonempty'), '--d3b-root', f'L1.00={d3}', *SELF]).returncode == 2 and os.listdir(tmp_path / 'nonempty') == ['x']
    empty = tmp_path / 'empty_out'; empty.mkdir(); r0 = _run([PROF, '--mt', MT, '--phaseb', P, '--phasec', PC, '--family', 'E1', '--d2-root', d2, '--out', str(empty), '--d3b-root', f'L1.00={d3}', '--selftest-small']); m0 = _rec(empty, 'E1'); assert r0.returncode == 1 and m0['stage'] == 'scope' and m0['out_preexisting_empty'] is True
    # other refusals: missing size root; formal mode on non-formal banks stops at input resolution (no supply read); wrong family; a bank changed after generation
    o2 = tmp_path / 'missing'; r2 = _run(base + ['--out', str(o2), '--d3b-root', f'L1.00={d3}', '--selftest-small', '--selftest-skip-env-lock']); m2 = _rec(o2); assert r2.returncode == 1 and m2['stage'] == 'inputs' and 'supplies' not in m2
    o3 = tmp_path / 'formal'; r3 = _run(base + ['--out', str(o3), '--d3b-root', f'L1.00={d3}', '--d3b-root', f'L1.20={d3}', '--d3b-root', f'L1.50={d3}']); m3 = _rec(o3); assert r3.returncode == 1 and m3['stage'] == 'environment' and 'supplies' not in m3   # env hard gate first (sandbox)
    o4 = tmp_path / 'formal2'; r4 = _run(base + ['--out', str(o4), '--d3b-root', f'L1.00={d3}', '--d3b-root', f'L1.20={d3}', '--d3b-root', f'L1.50={d3}', '--selftest-skip-env-lock']); m4 = _rec(o4); assert r4.returncode == 1 and m4['stage'] == 'inputs' and m4['gates']['G_inputs_resolved'] is False and 'supplies' not in m4
    o5 = tmp_path / 'fam'; r5 = _run([PROF, '--mt', MT, '--phaseb', P, '--phasec', PC, '--family', 'E7', '--d2-root', d2, '--out', str(o5), '--d3b-root', f'L1.00={d3}', *SELF]); m5 = _rec(o5, 'E7'); assert r5.returncode == 1 and m5['stage'] == 'inputs'
    bad = tmp_path / 'bad'; shutil.copytree(d3, bad); f = bad / 'cfg20104_b0' / 'cfg20104_b0_s0.npz'; z = dict(np.load(f)); z['model_native__float64__T1'][0] += 1e-9; np.savez(f, **z)
    o7 = tmp_path / 'badrun'; r7 = _run(base + ['--out', str(o7), '--d3b-root', f'L1.00={bad}', *SELF]); m7 = _rec(o7); assert r7.returncode == 1 and m7['stage'] == 'exception' and m7['D3C_PASS'] is False and 'gate' not in m7


def _inprocess(monkeypatch, banks, out, mutate_gate=None, mutate_size_input=None):
    """Run the profile script's main() in this process (self-test flags) with the gate / size-input builder wrapped by TEST-ONLY mutators (R-D3C1-C probes)."""
    import step1_engine.d3_profile as dp
    spec = importlib.util.spec_from_file_location('d3c_profile_under_test', PROF); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    real_gate, real_build = dp.twelve_official_gate, dp.build_twelve_size_input
    def gate(fm, fn, **kw):
        g = real_gate(fm, fn, **kw)
        if mutate_gate: mutate_gate(fm, fn)
        return g
    def build(ctx, fam, s, system, sup, plans, fplans):
        f = real_build(ctx, fam, s, system, sup, plans, fplans)
        if mutate_size_input: mutate_size_input(f, system, plans, fplans)
        return f
    monkeypatch.setattr(dp, 'twelve_official_gate', gate); monkeypatch.setattr(dp, 'build_twelve_size_input', build)
    monkeypatch.setattr(sys, 'argv', [PROF] + banks['base'][1:] + ['--out', str(out), '--d3b-root', f"L1.00={banks['d3']}", *SELF])
    with contextlib.redirect_stdout(io.StringIO()): rc = mod.main()
    return rc, _rec(out)


@need_ext
@pytest.mark.parametrize('case', ['native_fit_copy_after_gate', 'matched_plans_copy_after_gate', 'native_plans_copy_after_gate', 'matched_fit_copy_after_gate', 'size_input_native_fit_copy', 'size_input_matched_plans_copy', 'array_changed_after_gate', 'normal'])
def test_profile_plan_object_identity_guards(banks, tmp_path, monkeypatch, case):
    out = tmp_path / case; mg = ms = None
    if case == 'native_fit_copy_after_gate': mg = lambda fm, fn: setattr(fn, 'fit_plans', copy.deepcopy(fn.fit_plans))          # the audit's probe: value-equal copy, another object
    elif case == 'matched_plans_copy_after_gate': mg = lambda fm, fn: setattr(fm, 'plans', copy.deepcopy(fm.plans))
    elif case == 'native_plans_copy_after_gate': mg = lambda fm, fn: setattr(fn, 'plans', copy.deepcopy(fn.plans))
    elif case == 'matched_fit_copy_after_gate': mg = lambda fm, fn: setattr(fm, 'fit_plans', copy.deepcopy(fm.fit_plans))
    elif case == 'array_changed_after_gate': mg = lambda fm, fn: fm.configs[0].T1_model.__setitem__(0, fm.configs[0].T1_model[0] + 1.0)
    elif case == 'size_input_native_fit_copy': ms = lambda f, system, plans, fplans: setattr(f, 'fit_plans', copy.deepcopy(fplans)) if system == 'native' else None
    elif case == 'size_input_matched_plans_copy': ms = lambda f, system, plans, fplans: setattr(f, 'plans', copy.deepcopy(plans)) if system == 'matched' else None
    rc, m = _inprocess(monkeypatch, banks, out, mg, ms); G = m['gates']; poi = m.get('plan_object_identity', {})
    assert rc == 1 and m['D3C_PASS'] is False
    if case == 'normal': assert m['stage'] == 'complete' and G['G_identity_stable'] is True and G['G_size_inputs'] is True and all(_all_shared(poi[k]) for k in poi) and m['failures'] == []
    elif case.startswith('size_input'):
        assert m['stage'] == 'size_inputs' and G['G_size_inputs'] is False and G['G_family_assembled'] is None and 'gate' not in m and set(poi) == {'size_inputs'}
        sysname, key = ('native', 'fit_plans_is_fixed') if 'fit' in case else ('matched', 'plans_is_fixed'); assert poi['size_inputs'][f'L1.00/{sysname}'][key] is False and _all_shared({k: v for k, v in poi['size_inputs'].items() if k != f'L1.00/{sysname}'})
    else:
        assert m['stage'] == 'complete' and G['G_gate_passed'] is True and G['G_identity_stable'] is False and 'input / plan identity changed across the gate' in m['failures'] and _all_shared(poi['size_inputs_before_gate']) and _all_shared(poi['assembled_before_gate'])
        if case == 'array_changed_after_gate': assert _all_shared(poi['assembled_after_gate']) and m['input_fingerprints_after_gate']['matched'] != m['input_fingerprints_before_gate']['matched'] and not any('plan objects replaced' in f for f in m['failures'])
        else:
            sysname = 'native' if case.startswith('native') else 'matched'; key = 'fit_plans_is_fixed' if '_fit_' in case else 'plans_is_fixed'
            assert poi['assembled_after_gate'][f'family/{sysname}'][key] is False and _all_shared({k: v for k, v in poi['assembled_after_gate'].items() if k != f'family/{sysname}'}) and _all_shared(poi['size_inputs_after_gate']) and any('plan objects replaced' in f for f in m['failures']) and m['input_fingerprints_after_gate'] == dict(matched=m['input_fingerprints_before_gate']['matched'], native=m['input_fingerprints_before_gate']['native'])


# ---------------------------------------------------------------------------------------------------------------------------------------------------- notebook attempt cell
LAUNCH_CASES = ['ok', 'staged_ok', 'retry_after_old_success', 'pass_false', 'gate_false', 'rc1', 'missing', 'invalid_json', 'list_record', 'nested_gate_list', 'seconds_str', 'stages_rss_missing',
                'family_changed', 'root_changed', 'stage_local_changed', 'commit_changed', 'dirty_tree', 'inventory_changed', 'script_changed', 'lock_file_changed',
                'result_family_mismatch', 'result_source_mismatch', 'result_attempt_mismatch', 'result_lock_mismatch', 'plan_file_missing', 'plan_file_unbound',
                'copy_failure', 'copy_failure_after_old_success', 'disk_insufficient', 'launch_failure', 'stage_root_inside_input']
NO_LAUNCH = {'family_changed', 'root_changed', 'stage_local_changed', 'commit_changed', 'dirty_tree', 'inventory_changed', 'script_changed', 'lock_file_changed', 'copy_failure', 'copy_failure_after_old_success', 'disk_insufficient', 'stage_root_inside_input'}
STAGED = {'staged_ok', 'copy_failure', 'copy_failure_after_old_success', 'disk_insufficient', 'stage_root_inside_input'}


def _fake_source(root):
    """A fake checkout tree with the files the launcher binds (inventory, script, pins, ledger, receipt, d2 ledger)."""
    pb = root / 'engine' / 'phaseB'; (pb / 'd').mkdir(parents=True); (pb / 'registered_assets' / 'd3b').mkdir(parents=True); (pb / 'registered_assets' / 'd2').mkdir(); (root / 'phaseC').mkdir()
    (pb / 'd' / 'd3c_profile.py').write_text('# TEST_ONLY script stand-in\n'); (pb / 'd' / 'd3_pins.json').write_text(json.dumps(dict(schema='d3_pins_v1')))
    (pb / 'registered_assets' / 'd3b' / 'd3b_generation_ledger.json').write_text(json.dumps(dict(ledger_sha256='L' * 64, partitions={}))); (pb / 'registered_assets' / 'd3b' / 'd3b_outer_receipt.json').write_text(json.dumps(dict(receipt_sha256='R' * 64)))
    (pb / 'registered_assets' / 'd2' / 'd2_generation_ledger.json').write_text(json.dumps(dict(families={})))
    inv = dict(engine_version='0.0.0-TEST', d_sha256={'d/d3c_profile.py': sha(pb / 'd' / 'd3c_profile.py'), 'd/d3_pins.json': sha(pb / 'd' / 'd3_pins.json')}, registered_assets_sha256={'registered_assets/d3b/d3b_generation_ledger.json': sha(pb / 'registered_assets' / 'd3b' / 'd3b_generation_ledger.json'), 'registered_assets/d3b/d3b_outer_receipt.json': sha(pb / 'registered_assets' / 'd3b' / 'd3b_outer_receipt.json')})
    (pb / 'B2_completion_inventory.json').write_text(json.dumps(inv)); return str(root), str(pb)


@pytest.mark.parametrize('case', LAUNCH_CASES)
def test_profile_notebook_attempt_cell_binds_lock_and_records_failures(tmp_path, case):
    nb = json.load(open(NB)); c2 = ''.join(nb['cells'][2]['source']); c3 = ''.join(nb['cells'][3]['source']); lock_src = c2[c2.index('# LOCK-BUILD'):]
    commit = 'a' * 40; mt, pb = _fake_source(tmp_path / 'scratch'); out = tmp_path / 'out'; out.mkdir(); d2 = tmp_path / 'in_d2'; d2.mkdir(); (d2 / 'd2_bank_registry.json').write_text('{}')
    d3 = {s: str(tmp_path / f'in_{s}') for s in ('L1.00', 'L1.20', 'L1.50')}
    for p in d3.values(): os.makedirs(p); open(os.path.join(p, 'd3_bank_registry.json'), 'w').write('{}'); open(os.path.join(p, 'blob.bin'), 'wb').write(b'\0' * 1000)
    staged = case in STAGED; stage_root = str(tmp_path / 'stage') if case != 'stage_root_inside_input' else os.path.join(d3['L1.00'], 'stage')
    ns = dict(sys=sys, os=os, json=json, hashlib=hashlib, shutil=shutil, time=__import__('time'), re=__import__('re'), sha=sha, REPO_COMMIT=commit, FAMILY='E2', D2_RUN_ROOT=str(d2), D3B_RUN_ROOTS=dict(d3), STAGE_LOCAL=staged, STAGE_ROOT=stage_root,
              MT=mt, PHASEB=pb, PHASEC=f'{mt}/phaseC', SCRIPT=f'{pb}/d/d3c_profile.py', INV=f'{pb}/B2_completion_inventory.json', LEDGER=f'{pb}/registered_assets/d3b/d3b_generation_ledger.json', RECEIPT=f'{pb}/registered_assets/d3b/d3b_outer_receipt.json', PINS=f'{pb}/d/d3_pins.json', OUT=str(out), RAM_INFO=dict(total_bytes=1))
    ns['inv'] = json.load(open(ns['INV'])); ns['ledger'] = json.load(open(ns['LEDGER']))
    with contextlib.redirect_stdout(io.StringIO()): exec(compile(lock_src, 'nb_cell2_lock', 'exec'), ns)
    lock = ns['lock']; lock_sha = ns['LOCK_SHA256']; assert sha(ns['LOCK_PATH']) == lock_sha and lock['family'] == 'E2' and lock['stage_local'] is staged
    # ---- state changes AFTER the lock (configuration / live source) and the previous attempt's record
    old = dict(schema='TEST_ONLY_old', profile_pass=True, stage='complete', attempt_id='OLD_ATTEMPT')
    if case in ('retry_after_old_success', 'copy_failure_after_old_success'): (out / 'profile_final_record.json').write_text(json.dumps(old))
    if case == 'family_changed': ns['FAMILY'] = 'E7'
    if case == 'root_changed': ns['D2_RUN_ROOT'] = str(tmp_path / 'other_d2'); os.makedirs(ns['D2_RUN_ROOT'])
    if case == 'stage_local_changed': ns['STAGE_LOCAL'] = True
    if case == 'inventory_changed': inv = json.load(open(ns['INV'])); inv['engine_version'] = '0.0.1-TEST'; open(ns['INV'], 'w').write(json.dumps(inv))
    if case == 'script_changed': open(ns['SCRIPT'], 'a').write('# changed after the lock\n')
    if case == 'lock_file_changed': open(ns['LOCK_PATH'], 'a').write('\n')
    head = 'b' * 40 if case == 'commit_changed' else commit; dirty = ' M x' if case == 'dirty_tree' else ''
    # ---- the child process (TEST DOUBLE: writes a record shaped like the script's, bound to the attempt / lock it was given, except where the case breaks the binding)
    calls = []
    def check_output(args, **kw): return (head if 'rev-parse' in args else dirty) + '\n'
    def run(args, **kw):
        calls.append(list(args))
        if case == 'launch_failure': raise OSError('TEST_ONLY cannot start subprocess')
        run_dir = args[args.index('--out') + 1]; fam = args[args.index('--family') + 1]; att = args[args.index('--attempt-id') + 1]; lk = args[args.index('--launcher-lock-sha256') + 1]; os.makedirs(run_dir)
        rec_fam = 'E7' if case == 'result_family_mismatch' else fam; rp = os.path.join(run_dir, f'd3c_profile_record_{fam}.json'); pp = os.path.join(run_dir, f'd3c_plan_identity_{fam}.json')
        plan = dict(schema='d3c_plan_identity_record_v2', family=fam, formal=True, selftest=False, identity=dict(identity_sha256='I' * 64), attempt=dict(attempt_id=('X' if case == 'plan_file_unbound' else att), launcher_lock_sha256=lk), source_lock=dict(script_sha256=sha(ns['SCRIPT']), inventory_sha256=sha(ns['INV'])))
        if case != 'plan_file_missing': open(pp, 'w').write(json.dumps(plan))
        v = dict(schema='d3c_profile_record_v2', D3C_PASS=(case != 'pass_false'), stage='complete', family=rec_fam, gates={'G_x': True}, gate=dict(passed=(case != 'gate_false'), required_failures=[]), failures=[], stages_rss_mb={'final': 1.0}, stages_peak_rss_mb={'final': 1.0}, seconds=1.0, selftest=False, profile='production_official',
                 attempt=dict(attempt_id=('X' if case == 'result_attempt_mismatch' else att), launcher_lock_sha256=('0' * 64 if case == 'result_lock_mismatch' else lk)),
                 source=dict(script_sha256=('0' * 64 if case == 'result_source_mismatch' else sha(ns['SCRIPT'])), inventory_sha256=sha(ns['INV']), pins_sha256=sha(ns['PINS']), engine_version=json.load(open(ns['INV']))['engine_version']), plan_identity_sha256='I' * 64,
                 published_evidence=({f'd3c_plan_identity_{fam}.json': dict(sha256=sha(pp), bytes=os.path.getsize(pp))} if os.path.exists(pp) else {}))
        if case == 'nested_gate_list': v['gate'] = ['not a gate dictionary']
        if case == 'seconds_str': v['seconds'] = 'bad'
        if case == 'stages_rss_missing': del v['stages_rss_mb']
        if case == 'missing': pass
        elif case == 'invalid_json': open(rp, 'w').write('{')
        elif case == 'list_record': open(rp, 'w').write('[]')
        else: open(rp, 'w').write(json.dumps(v))
        return types.SimpleNamespace(returncode=(1 if case == 'rc1' else 0), stdout='TEST_ONLY', stderr='')
    ns['subprocess'] = types.SimpleNamespace(run=run, check_output=check_output)
    if case in ('copy_failure', 'copy_failure_after_old_success'):
        def fail_copy(*a, **k): raise OSError(28, 'TEST_ONLY No space left on device')
        ns['shutil'] = types.SimpleNamespace(rmtree=shutil.rmtree, copytree=fail_copy, disk_usage=shutil.disk_usage)
    if case == 'disk_insufficient': ns['shutil'] = types.SimpleNamespace(rmtree=shutil.rmtree, copytree=shutil.copytree, disk_usage=lambda p: types.SimpleNamespace(free=10))
    with contextlib.redirect_stdout(io.StringIO()): exec(compile(c3, 'nb_cell3_attempt', 'exec'), ns)        # the attempt cell never raises: every failure becomes a FAIL record
    fin = json.load(open(out / 'profile_final_record.json')); att = ns['ATTEMPT']; expect = case in ('ok', 'staged_ok', 'retry_after_old_success')
    assert fin['schema'] == 'd3c_launcher_final_record_v2' and fin['attempt_id'] == att and fin['lock_sha256'] == lock_sha and fin['lock'] == lock and fin['profile_pass'] is expect and ns['profile_pass'] is expect and fin['seconds_total'] is not None and fin['finished_utc']
    assert fin['run_dir'] == f'{out}/run_{att}' and (len(calls) == (0 if case in NO_LAUNCH else 1))
    if case in NO_LAUNCH: assert fin['exit_code'] is None and fin['D3C_PASS'] is None and fin['exception'] and fin['failures']
    if case in ('family_changed', 'root_changed', 'stage_local_changed'): assert fin['stage'] == 'config_check' and 'configuration differs from the lock' in fin['failures'][0]
    if case in ('commit_changed', 'dirty_tree', 'inventory_changed', 'script_changed'): assert fin['stage'] == 'source_check' and 'live source differs' in fin['failures'][0] and fin['bindings']['live_source']
    if case == 'lock_file_changed': assert fin['stage'] == 'config_check' and 'lock file on disk' in fin['failures'][0]
    if case in ('copy_failure', 'copy_failure_after_old_success', 'disk_insufficient', 'stage_root_inside_input'): assert fin['stage'] == 'staging' and ('No space left' in fin['exception'] if case.startswith('copy') else True) and ('insufficient local disk' in fin['failures'][0] if case == 'disk_insufficient' else True) and ('STAGE_ROOT must be disjoint' in fin['failures'][0] if case == 'stage_root_inside_input' else True)
    if case == 'launch_failure': assert fin['stage'] == 'launch' and fin['exit_code'] is None and 'cannot start subprocess' in fin['exception'] and fin['args'][fin['args'].index('--attempt-id') + 1] == att
    if case in ('retry_after_old_success', 'copy_failure_after_old_success'):
        sup = out / f'superseded_final_record_before_{att}.json'; assert fin['superseded_previous_record'] == str(sup) and json.load(open(sup)) == old and fin['attempt_id'] != 'OLD_ATTEMPT' and fin.get('TEST_ONLY_old_record') is None
    if case not in NO_LAUNCH and case != 'launch_failure':
        a = calls[0]; assert fin['stage'] == 'complete' and a[a.index('--attempt-id') + 1] == att and a[a.index('--launcher-lock-sha256') + 1] == lock_sha and a[a.index('--profile') + 1] == 'production_official' and '--selftest-small' not in a and a.count('--d3b-root') == 3 and a[a.index('--family') + 1] == 'E2' and a[a.index('--out') + 1] == fin['run_dir']
        assert fin['launcher_fallback'] is (case in ('missing', 'invalid_json', 'list_record', 'nested_gate_list', 'seconds_str', 'stages_rss_missing')) and fin['exit_code'] == (1 if case == 'rc1' else 0)
        if case == 'staged_ok': assert a[a.index('--d2-root') + 1] == f'{stage_root}/d2' and os.path.isfile(f'{stage_root}/d3b_L1.00/blob.bin') and fin['staged_inputs']['d2'] == f'{stage_root}/d2' and fin['staging']['input_bytes'] == 3000 + os.path.getsize(d2 / 'd2_bank_registry.json') + 3 * 2
        if case in ('result_family_mismatch', 'result_source_mismatch', 'result_attempt_mismatch', 'result_lock_mismatch', 'plan_file_missing', 'plan_file_unbound'): assert fin['bindings_ok'] is False and fin['D3C_PASS'] is True and fin['gate_passed'] is True and any('not bound' in f for f in fin['failures'])
        if case in ('ok', 'staged_ok', 'retry_after_old_success'): assert fin['bindings_ok'] is True and fin['plan_identity_file_ok'] is True and fin['failures'] == [] and fin['record_sha256'] == sha(f"{fin['run_dir']}/d3c_profile_record_E2.json") and fin['stages_peak_rss_mb'] == {'final': 1.0}
        if case in ('pass_false', 'gate_false', 'rc1'): assert fin['bindings_ok'] is True and fin['failures'] == []
