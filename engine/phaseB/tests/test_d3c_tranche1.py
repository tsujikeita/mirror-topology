# -*- coding: utf-8 -*-
"""D-3c tranche 1 contracts (d/d3c_profile.py + notebook): on synthetic small banks of the generators' self-tests (D-2 first-wave + family reference, D-3b added; real covariance
roots; TEST-ONLY kernel) the profile script performs formal-shaped intake (formal=False in self-test) -> ordered-UID / K_fit checks -> ONE family-shared five-seed plan ->
size inputs -> all-size assembly -> fingerprints -> smoke gate (live environment; keyword plan identity) -> identity re-check -> verified publication; D3C_PASS is never True
in self-test; the published plan identity is reproducible from the recorded ORDERED UIDs in a separate process (all strata / multiplicity SHAs); reversed / altered UIDs give
another identity; refusals: output overlap (rc 2), missing / wrong-size D-3b roots, wrong family inputs, formal mode on non-formal banks (stops at input resolution before
any bank is read); the notebook's final pass requires rc 0 AND D3C_PASS AND gate passed (fallback on a missing / invalid record)."""
import os, sys, json, shutil, subprocess, hashlib, copy
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine.d3_profile import twelve_context, fix_family_plans, verify_plan_identity
from step1_engine.errors import InputContractError
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); MT = os.environ.get('B3_MT', '/home/claude/mt'); PC = os.environ.get('PHASEC_ROOT', '/home/claude/phaseC')
GEN2 = os.path.join(P, 'd', 'd2_bankgen.py'); GEN3 = os.path.join(P, 'd', 'd3_bankgen.py'); PROF = os.path.join(P, 'd', 'd3c_profile.py')
need_ext = pytest.mark.skipif(not (os.path.exists(os.path.join(MT, 't1_engine.py')) and os.path.isdir(PC)), reason='external assets not present')
ENV = dict(os.environ, PIP_BREAK_SYSTEM_PACKAGES='1', OPENBLAS_NUM_THREADS='1'); ST = ('--selftest-scale', '0.001', '--selftest-skip-a10', '--selftest-skip-env-lock')


def _run(args, timeout=200): return subprocess.run([sys.executable, *args], capture_output=True, text=True, env=ENV, timeout=timeout)


def _rec(out, fam='E2'): return json.load(open(os.path.join(out, f'd3c_profile_record_{fam}.json')))


@need_ext
def test_profile_script_selftest_end_to_end_and_refusals(tmp_path):
    d2 = tmp_path / 'd2'; r = _run([GEN2, '--mt', MT, '--phaseb', P, '--phasec', PC, '--out', str(d2), '--family', 'E2', *ST]); assert json.load(open(d2 / 'd2_run_manifest.json'))['stage'] == 'complete', r.stdout[-500:]
    d3 = tmp_path / 'd3b_L100'; r = _run([GEN3, '--mt', MT, '--phaseb', P, '--phasec', PC, '--out', str(d3), '--family', 'E2', '--sizes', 'L1.00', *ST]); assert json.load(open(d3 / 'd3_run_manifest.json'))['stage'] == 'complete', r.stdout[-500:]
    base = [PROF, '--mt', MT, '--phaseb', P, '--phasec', PC, '--family', 'E2', '--d2-root', str(d2)]
    # self-test end to end (one size)
    out = tmp_path / 'prof'; r = _run(base + ['--out', str(out), '--d3b-root', f'L1.00={d3}', '--selftest-small', '--selftest-skip-env-lock', '--selftest-sizes', 'L1.00']); m = _rec(out)
    assert r.returncode == 1 and m['stage'] == 'complete' and m['D3C_PASS'] is False and m['selftest'] is True and m['gates']['G_env_lock'] is False and all(m['gates'][g] is True for g in m['required_inventory'] if g != 'G_env_lock')
    assert m['gate']['mode'] == 'smoke' and m['gate']['passed'] is True and m['gate']['diagnostics']['environment_source'] == 'live_collected' and all(c['passed'] for c in m['gate']['diagnostics']['twelve_checks'] if c['code'].endswith(('plan_identity_fixed', 'first_wave_and_added_share_plans', 'pc1_pass_all', 'twelve_per_size')))
    assert len(m['supplies']) == 24 and sum(v['origin'] == 'first_wave_D1' for v in m['supplies'].values()) == 6 and sum(v['origin'] == 'twelve_added_D3a' for v in m['supplies'].values()) == 18 and all(v['n_clusters'] == {'0': 10, '1': 30} for v in m['supplies'].values())
    assert m['uids'] == dict(m['uids'], K0=10, K1=30, m=100, K_fit=2, n_fit=200, evaluation_group=1002, first_uid=[1, 200, 1002, 0, 0], last_uid=[1, 200, 1002, 1, 29]) and m['input_fingerprints_before_gate']['matched'] == m['input_fingerprints_after_gate']['matched'] and m['input_fingerprints_before_gate']['native'] == m['input_fingerprints_after_gate']['native'] and m['input_fingerprints_before_gate']['matched'] != m['input_fingerprints_before_gate']['native']
    assert m['family_identity']['full_surviving_scope'] is False and m['family_identity']['stage'] == 'twelve' and m['publication_stage'] == 'plan_identity_verified' and set(m['stages_rss_mb']) >= {'preflight', 'intake', 'plans', 'gate', 'final'}
    pb = open(out / 'd3c_plan_identity_E2.json', 'rb').read(); assert m['published_evidence']['d3c_plan_identity_E2.json'] == dict(sha256=hashlib.sha256(pb).hexdigest(), bytes=len(pb)); pd = json.loads(pb)
    assert pd['identity']['identity_sha256'] == m['plan_identity_sha256'] and pd['formal'] is False and pd['B'] == 20 and pd['B_KDE'] == 25 and pd['seeds'] == 5 and len(pd['ordered_uids']['0']) == 10 and len(pd['ordered_uids']['1']) == 30 and 'SELF-TEST' in pd['constants_source']
    # plan identity roundtrip in THIS (separate) process from the recorded ordered UIDs; reversed / altered UIDs give another identity
    ctx = twelve_context(P); table = ctx.table
    plans, fplans, ident = fix_family_plans(table, 'E2', {0: [tuple(u) for u in pd['ordered_uids']['0']], 1: [tuple(u) for u in pd['ordered_uids']['1']]}, pd['K_fit'], pd['master_seed'], B=pd['B'], B_KDE=pd['B_KDE'])
    assert ident == pd['identity'] and verify_plan_identity(plans, fplans, pd['identity'], table=table, family='E2') and all(p.multiplicities_sha256 if hasattr(p, 'multiplicities_sha256') else True for p in fplans.values())
    plans_rev, fplans_rev, rev = fix_family_plans(table, 'E2', {0: [tuple(u) for u in pd['ordered_uids']['0']][::-1], 1: [tuple(u) for u in pd['ordered_uids']['1']]}, pd['K_fit'], pd['master_seed'], B=pd['B'], B_KDE=pd['B_KDE']); assert rev['identity_sha256'] != ident['identity_sha256']
    with pytest.raises(InputContractError): verify_plan_identity(plans_rev, fplans_rev, pd['identity'], table=table, family='E2')                                        # reversed order: another identity
    # refusals: output overlap with an input (rc 2, nothing written); missing size root; formal mode on non-formal banks stops at input resolution (no supply read); wrong family
    assert _run(base + ['--out', str(d2 / 'review'), '--d3b-root', f'L1.00={d3}', '--selftest-small', '--selftest-skip-env-lock', '--selftest-sizes', 'L1.00']).returncode == 2 and not (d2 / 'review').exists()
    assert _run(base + ['--out', str(P / 'x') if False else os.path.join(P, 'should_not_exist'), '--d3b-root', f'L1.00={d3}', '--selftest-small', '--selftest-skip-env-lock', '--selftest-sizes', 'L1.00']).returncode == 2 and not os.path.exists(os.path.join(P, 'should_not_exist'))
    o2 = tmp_path / 'missing'; r2 = _run(base + ['--out', str(o2), '--d3b-root', f'L1.00={d3}', '--selftest-small', '--selftest-skip-env-lock']); m2 = _rec(o2); assert r2.returncode == 1 and m2['stage'] == 'inputs' and 'supplies' not in m2
    o3 = tmp_path / 'formal'; r3 = _run(base + ['--out', str(o3), '--d3b-root', f'L1.00={d3}', '--d3b-root', f'L1.20={d3}', '--d3b-root', f'L1.50={d3}']); m3 = _rec(o3); assert r3.returncode == 1 and m3['stage'] == 'environment' and 'supplies' not in m3   # env hard gate first (sandbox)
    o4 = tmp_path / 'formal2'; r4 = _run(base + ['--out', str(o4), '--d3b-root', f'L1.00={d3}', '--d3b-root', f'L1.20={d3}', '--d3b-root', f'L1.50={d3}', '--selftest-skip-env-lock']); m4 = _rec(o4); assert r4.returncode == 1 and m4['stage'] == 'inputs' and m4['gates']['G_inputs_resolved'] is False and 'supplies' not in m4   # non-formal banks never resolve as the accepted runs
    o5 = tmp_path / 'fam'; r5 = _run([PROF, '--mt', MT, '--phaseb', P, '--phasec', PC, '--family', 'E7', '--d2-root', str(d2), '--out', str(o5), '--d3b-root', f'L1.00={d3}', '--selftest-small', '--selftest-skip-env-lock', '--selftest-sizes', 'L1.00']); m5 = _rec(o5, 'E7'); assert r5.returncode == 1 and m5['stage'] == 'inputs'
    o6 = tmp_path / 'e1'; r6 = _run([PROF, '--mt', MT, '--phaseb', P, '--phasec', PC, '--family', 'E1', '--d2-root', str(d2), '--out', str(o6), '--d3b-root', f'L1.00={d3}', '--selftest-small']); assert r6.returncode == 1 and _rec(o6, 'E1')['stage'] == 'scope'
    # a bank changed after generation is refused by the intake (exception stage; no PASS); inputs untouched otherwise
    bad = tmp_path / 'bad'; shutil.copytree(d3, bad); f = bad / 'cfg20104_b0' / 'cfg20104_b0_s0.npz'; z = dict(np.load(f)); z['model_native__float64__T1'][0] += 1e-9; np.savez(f, **z)
    o7 = tmp_path / 'badrun'; r7 = _run(base + ['--out', str(o7), '--d3b-root', f'L1.00={bad}', '--selftest-small', '--selftest-skip-env-lock', '--selftest-sizes', 'L1.00']); m7 = _rec(o7); assert r7.returncode == 1 and m7['stage'] == 'exception' and m7['D3C_PASS'] is False and 'gate' not in m7


@pytest.mark.parametrize('rc,rec', [(0, 'ok'), (0, 'pass_false'), (1, 'ok'), (0, 'gate_false'), (-9, 'missing'), (0, 'invalid'), (0, 'list')])
def test_profile_notebook_final_pass_requires_all(tmp_path, monkeypatch, rc, rec):
    import types, io, contextlib
    out = tmp_path / 'out'; (out / 'run').mkdir(parents=True)
    base = dict(D3C_PASS=True, stage='complete', gate=dict(passed=True, required_failures=[]), failures=[], stages_rss_mb={}, seconds=1.0)
    if rec == 'pass_false': base['D3C_PASS'] = False
    elif rec == 'gate_false': base['gate']['passed'] = False
    if rec in ('ok', 'pass_false', 'gate_false'): (out / 'run' / 'd3c_profile_record_E2.json').write_text(json.dumps(base))
    elif rec != 'missing': (out / 'run' / 'd3c_profile_record_E2.json').write_text({'invalid': '{', 'list': '[]'}[rec])
    import subprocess as _sp; monkeypatch.setattr(_sp, 'run', lambda *a, **k: types.SimpleNamespace(returncode=rc, stdout='TEST_ONLY', stderr=''))
    nb = json.load(open(os.path.join(P, 'd', 'MirrorTopology_Step1_D3c_profile_v0.1.ipynb'))); src = ''.join(nb['cells'][3]['source'])
    ns = dict(sys=sys, os=os, json=json, time=__import__('time'), shutil=shutil, subprocess=_sp, OUT=str(out), SCRIPT='TEST_ONLY', MT='TEST_ONLY', PHASEB=P, PHASEC='TEST_ONLY', FAMILY='E2', D2_RUN_ROOT='TEST_ONLY', D3B_RUN_ROOTS={'L1.00': 'a', 'L1.20': 'b', 'L1.50': 'c'}, STAGE_LOCAL=False, lock={})
    with contextlib.redirect_stdout(io.StringIO()): exec(compile(src, 'nb_cell3', 'exec'), ns)
    fin = json.load(open(out / 'profile_final_record.json')); expect = (rc == 0 and rec == 'ok')
    assert ns['profile_pass'] is expect and fin['profile_pass'] is expect and fin['launcher_fallback'] is (rec in ('missing', 'invalid', 'list')) and (out / 'profile_stdout.txt').exists() and ns['args'][ns['args'].index('--profile') + 1] == 'production_official' and '--selftest-small' not in ns['args'] and ns['args'].count('--d3b-root') == 3
