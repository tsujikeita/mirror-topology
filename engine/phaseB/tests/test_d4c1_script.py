# -*- coding: utf-8 -*-
"""D4C-1 connection script and launcher notebooks (engine 0.106.0). (1) The connection path end to end on the generators' small synthetic banks (D-2 E1/E2/E7/E8 at scale
0.001, D-3b E2 x three sizes): partial E2 with the 12-position inputs (registered D-2W context + registered pseudo columns, prefix rows; smoke gates), partials E1/E7/E8,
timing probe, combine of the four, refusals (output policy, inputs, formal mode in the sandbox stops at the environment gate, mismatched partial sets); (2) the in-process
equivalence self-test of the script (--selftest-fixture); (3) notebook structure (anchor before the first write, trusted REQUIRED inventories == the script constants by AST,
no nonce / self-test flag in the launch) and the attempt cells with a mocked child process (lock / live-source binding, record semantics, probe never a pass, stale success).
Never a formal PASS in the sandbox (environment gate)."""
import os, sys, io, re, json, shutil, hashlib, subprocess, contextlib, tempfile, copy
import pytest
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); MT = os.environ.get('B3_MT', '/home/claude/mt'); PC = os.environ.get('PHASEC_ROOT', '/home/claude/phaseC'); sys.path[:0] = [P]
SCRIPT = os.path.join(P, 'd', 'd4c1_calibration.py'); GEN2 = os.path.join(P, 'd', 'd2_bankgen.py'); GEN3 = os.path.join(P, 'd', 'd3_bankgen.py')
NB_P = os.path.join(P, 'd', 'MirrorTopology_Step1_D4C1_partial_v0.1.ipynb'); NB_C = os.path.join(P, 'd', 'MirrorTopology_Step1_D4C1_combine_v0.1.ipynb')
need_ext = pytest.mark.skipif(not (os.path.exists(os.path.join(MT, 't1_engine.py')) and os.path.isdir(PC)), reason='external assets not present')
ENV = dict(os.environ, PIP_BREAK_SYSTEM_PACKAGES='1', OPENBLAS_NUM_THREADS='1'); ST = ('--selftest-scale', '0.001', '--selftest-skip-a10', '--selftest-skip-env-lock')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
FAMS = ('E1', 'E2', 'E7', 'E8'); SIZES = ('L1.00', 'L1.20', 'L1.50')


def _run(args, timeout=900): return subprocess.run([sys.executable, *args], capture_output=True, text=True, env=ENV, timeout=timeout)


def _ast_required(name, script=SCRIPT):
    import ast
    return [list(ast.literal_eval(st.value)) for st in ast.parse(open(script).read()).body if isinstance(st, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in st.targets)][0]


def _commit():
    from step1_engine.calibration_first import commit_target
    return commit_target((200., 1000.), 'selftest-nonce-not-a-secret-0001')


@pytest.fixture(scope='module')
def banks(tmp_path_factory):
    """Synthetic small D-2 (E1 / E2 / E7 / E8) and D-3b (E2, three sizes) banks of the generators' self-tests; generated once per module."""
    if not (os.path.exists(os.path.join(MT, 't1_engine.py')) and os.path.isdir(PC)): pytest.skip('external assets not present')
    root = tmp_path_factory.mktemp('d4c1_banks'); d2 = {}; d3 = {}
    for f in FAMS:
        d2[f] = str(root / f'd2_{f}'); r = _run([GEN2, '--mt', MT, '--phaseb', P, '--phasec', PC, '--out', d2[f], '--family', f, *ST]); assert json.load(open(os.path.join(d2[f], 'd2_run_manifest.json')))['stage'] == 'complete', r.stdout[-500:]
    for s in SIZES:
        d3[s] = str(root / f'd3b_E2_{s}'); r = _run([GEN3, '--mt', MT, '--phaseb', P, '--phasec', PC, '--out', d3[s], '--family', 'E2', '--sizes', s, *ST]); assert json.load(open(os.path.join(d3[s], 'd3_run_manifest.json')))['stage'] == 'complete', r.stdout[-500:]
    return dict(d2=d2, d3=d3, root=str(root))


def _base(C, camp='SELFTEST_CAMPAIGN_01', n=2): return [SCRIPT, '--mt', MT, '--phaseb', P, '--phasec', PC, '--target-commitment', C, '--campaign-id', camp, '--selftest-small', '--selftest-skip-env-lock', '--selftest-n', str(n)]


def _rec(out, tag): return json.load(open(os.path.join(out, f'd4c1_{tag}_run.json')))


@pytest.fixture(scope='module')
def partials(banks, tmp_path_factory):
    """The four self-test partial runs (E2 with the 12-position inputs) + the probe on E1."""
    C = _commit(); out = {}; root = tmp_path_factory.mktemp('parts')
    for f in FAMS:
        o = str(root / f); extra = ['--d3b-root'] if False else []
        args = _base(C) + ['--mode', 'partial', '--family', f, '--d2-root', banks['d2'][f], '--out', o] + ([x for s in SIZES for x in ('--d3b-root', f'{s}={banks["d3"][s]}')] if f == 'E2' else []) + (['--attempt-id', 'TEST_ATTEMPT_1', '--launcher-lock-sha256', 'f' * 64] if f == 'E2' else [])
        r = _run(args); out[f] = dict(dir=o, rc=r.returncode, rec=_rec(o, f'partial_{f}'), stdout=r.stdout[-800:])
    po = str(root / 'probe'); r = _run(_base(C) + ['--mode', 'partial', '--family', 'E1', '--d2-root', banks['d2']['E1'], '--out', po, '--probe-n', '2']); out['probe'] = dict(dir=po, rc=r.returncode, rec=_rec(po, 'probe_E1'))
    return dict(C=C, runs=out, root=str(root))


@need_ext
def test_partial_script_selftest_end_to_end(partials):
    C = partials['C']; REQ = _ast_required('REQUIRED_PARTIAL'); assert len(REQ) == 24 and REQ[:11] == _ast_required('REQUIRED_COMMON')
    for f in FAMS:
        m = partials['runs'][f]['rec']; o = partials['runs'][f]['dir']
        assert partials['runs'][f]['rc'] == 1 and m['stage'] == 'complete' and m['failures'] == [] and m['D4C1_PARTIAL_PASS'] is False and m['selftest'] is True and m['formal'] is False and m['probe'] is False and m['mode'] == 'partial' and m['family'] == f, partials['runs'][f]['stdout']
        assert m['required_inventory'] == REQ and sorted(m['gates']) == sorted(REQ) and m['gates']['G_env_lock'] is False and all(m['gates'][g] is True for g in REQ if g != 'G_env_lock'), m['gates']
        assert m['target_commitment'] == C and m['campaign_id'] == 'SELFTEST_CAMPAIGN_01' and m['w2_context']['context_sha256'] == json.load(open(os.path.join(P, 'd', 'd3_pins.json')))['d2w_context_sha256'] and m['pseudo']['n'] == 2000 and m['pseudo']['identity']['paired_sha256'] == json.load(open(os.path.join(P, 'd', 'd3_pins.json')))['pseudo_paired_sha256']
        pr = m['partial']; assert pr['n_pseudo'] == 2 and pr['gate_mode'] == 'smoke' and pr['verification']['ok'] is True and pr['verification']['registered_context_ok'] is True and pr['verification']['family'] == f and pr['archive_entries'] > 0
        pib = m['pseudo_identity_bound']; assert pib['record']['n'] == 2 and pib['record']['sha256_T1'] == pib['consumed_arrays']['sha256_T1'] and pib['registered']['n'] == 2000 and pib['record']['sha256_T1'] != pib['registered']['T1_sha256']     # prefix rows: bound to the consumed arrays; the registered full-column identity is only required in a formal run
        fn = f'd4c1_partial_{f}_record.json'; fp = os.path.join(o, fn); assert m['published_evidence'] == {fn: dict(sha256=sha(fp), bytes=os.path.getsize(fp))} and os.path.isfile(os.path.join(o, 'archive', 'index.json'))
        from step1_engine import serialization as ser
        doc = ser.loads(open(fp, encoding='utf-8').read()); assert doc['schema'] == 'family_partial_calibration_v1' and doc['family'] == f and doc['mode'] == 'smoke' and doc['thresholds']['target_commitment'] == C and doc['thresholds']['pseudo']['n'] == 2 and 'calibration' not in doc and doc['campaign']['id'] == 'SELFTEST_CAMPAIGN_01__SELFTEST' and doc['campaign']['formal'] is False and doc['binding']['partial_sha256'] == pr['partial_sha256']
        assert set(m['stages_peak_rss_mb']) >= {'preflight', 'first_wave_intake', 'plans', 'first_wave_views', 'partial', 'verify', 'final'} and m['timings']['seconds_per_pseudo'] > 0
        assert m['plan_objects']['stable_after'] is True and m['plan_objects']['first_wave_shared'] is True and m['plan_objects']['script_views_same_objects_after'] is True and doc['plan_objects']['stable_after'] is True and (f == 'E2') == (m['plan_objects']['twelve_shares_first_wave'] is True) == (m['plan_objects']['twelve_present'] is True)
        if f == 'E2':
            assert m['attempt'] == dict(attempt_id='TEST_ATTEMPT_1', launcher_lock_sha256='f' * 64) and m['twelve']['gate'] == dict(mode='smoke', passed=True, required_failures=[], environment_source='live_collected') and m['twelve']['d3c_binding'] == dict(family='E2', note='SELF-TEST: no D-3c binding') and len(m['supplies']) == 2 * (9 + 27) and all(f'twelve:E2/{s}' in doc['fingerprints']['at_gate'] for s in SIZES)
            assert m['plan_identity']['source'].startswith('SELF-TEST') and m['plan_identity']['B'] == 20 and m['inputs']['d3b'][SIZES[0]]['selftest'] is True and m['uids']['K0'] == 10 and m['uids']['K1'] == 30
        elif f == 'E1': assert m['twelve'] == dict(note='E1: observer-homogeneous; no 12-position stage') and len(m['supplies']) == 6 and not any(k.startswith('twelve:') for k in doc['fingerprints']['at_gate'])
        else: assert m['twelve'] == dict(note='SELF-TEST: 12-position inputs not supplied') and m['notes'] and len(m['supplies']) == 18
    # probe: first N registered rows, smoke mode, separate file names, campaign suffix, never a pass
    pm = partials['runs']['probe']['rec']; po = partials['runs']['probe']['dir']
    assert pm['probe'] is True and pm['probe_n'] == 2 and pm['D4C1_PARTIAL_PASS'] is False and pm['stage'] == 'complete' and os.path.isfile(os.path.join(po, 'd4c1_probe_E1_record.json')) and pm['partial']['n_pseudo'] == 2 and pm['timings']['seconds_per_pseudo'] > 0
    from step1_engine import serialization as ser
    pdoc = ser.loads(open(os.path.join(po, 'd4c1_probe_E1_record.json'), encoding='utf-8').read()); assert pdoc['campaign']['id'].endswith('__PROBE') and pdoc['campaign']['probe'] is True and pdoc['mode'] == 'smoke'


@need_ext
def test_combine_script_selftest_and_refusals(partials, tmp_path):
    C = partials['C']; runs = partials['runs']; REQ = _ast_required('REQUIRED_COMBINE'); assert len(REQ) == 18
    parts = [x for f in FAMS for x in ('--partial', f'{f}={runs[f]["dir"]}')]
    o = str(tmp_path / 'combine'); r = _run(_base(C) + ['--mode', 'combine', '--out', o] + parts); m = _rec(o, 'combine')
    assert r.returncode == 1 and m['stage'] == 'complete' and m['failures'] == [] and m['D4C1_COMBINE_PASS'] is False and m['required_inventory'] == REQ and all(m['gates'][g] is True for g in REQ if g != 'G_env_lock') and m['gates']['G_env_lock'] is False, (r.stdout[-800:], m['failures'])
    assert set(m['partials']) == set(FAMS) and all(m['merge'][f]['source_entries'] > 0 for f in FAMS) and all(m['partials_verification'][f]['ok'] for f in FAMS)
    s = m['sealed']; assert s['branch_completeness']['all_registered_families'] is True and set(s['calibration']) == {'support', 'strong'} and s['calibration']['support']['n'] == 2 and s['calibration']['support']['threshold'] == 0.05 and s['calibration']['strong']['threshold'] == 0.01 and 'NOT an approval' in s['scope']
    from step1_engine import serialization as ser
    from step1_engine.archive import Archive
    from step1_engine.d4c1_partial import load_combined_sealed_record
    doc = ser.loads(open(os.path.join(o, 'd4c1_sealed_calibration.json'), encoding='utf-8').read()); comb = doc['binding']['combiner']
    assert doc['binding']['run_manifest_sha256'] == s['run_manifest_sha256'] and sorted(comb['partials']) == list(FAMS) and all(comb['partials'][f]['partial_sha256'] == runs[f]['rec']['partial']['partial_sha256'] for f in FAMS) and doc['thresholds']['target_commitment'] == C and doc['final_label_released'] is False and not doc['families']
    d = load_combined_sealed_record(Archive(os.path.join(o, 'archive')), doc['binding']['run_manifest_ref']); assert d['_verification']['ok'] and d['_verification']['combined']
    # refusals: three partials; a probe in place of a partial; another campaign / commitment; the output below an input (rc 2, nothing written)
    for name, extra, expect_stage in [('three', [x for f in FAMS[:3] for x in ('--partial', f'{f}={runs[f]["dir"]}')], 'inputs'), ('probe', [x for f in FAMS for x in ('--partial', f'{f}={runs["probe"]["dir"] if f == "E1" else runs[f]["dir"]}')], 'inputs')]:
        oo = str(tmp_path / name); rr = _run(_base(C) + ['--mode', 'combine', '--out', oo] + extra); mm = _rec(oo, 'combine'); assert rr.returncode == 1 and mm['stage'] == expect_stage and mm['gates']['G_partials_loaded'] is False and 'sealed' not in mm, name
    oo = str(tmp_path / 'camp'); rr = _run(_base(C, camp='ANOTHER_CAMPAIGN') + ['--mode', 'combine', '--out', oo] + parts); mm = _rec(oo, 'combine'); assert mm['stage'] == 'inputs' and any('campaign' in x for x in mm['failures'])
    oo = str(tmp_path / 'commit'); rr = _run(_base('0' * 64) + ['--mode', 'combine', '--out', oo] + parts); mm = _rec(oo, 'combine'); assert mm['stage'] == 'inputs'
    bad = os.path.join(runs['E1']['dir'], 'x_out'); assert _run(_base(C) + ['--mode', 'combine', '--out', bad] + parts).returncode == 2 and not os.path.lexists(bad)


@need_ext
def test_partial_script_refusals(banks, tmp_path):
    C = _commit(); d2 = banks['d2']; d3 = banks['d3']; base = _base(C)
    # output policy: OUT below an input / source / phase C / mt -> rc 2 and nothing written; symlink OUT; non-empty OUT
    for bad in (os.path.join(d2['E2'], 'review'), os.path.join(P, 'should_not_exist'), os.path.join(PC, 'should_not_exist'), os.path.join(MT, 'should_not_exist')):
        assert _run(base + ['--mode', 'partial', '--family', 'E2', '--d2-root', d2['E2'], '--out', bad]).returncode == 2 and not os.path.lexists(bad), bad
    real = tmp_path / 'real'; real.mkdir(); link = tmp_path / 'link'; os.symlink(real, link); assert _run(base + ['--mode', 'partial', '--family', 'E1', '--d2-root', d2['E1'], '--out', str(link)]).returncode == 2 and not os.listdir(real)
    (tmp_path / 'ne').mkdir(); (tmp_path / 'ne' / 'x').write_text('x'); assert _run(base + ['--mode', 'partial', '--family', 'E1', '--d2-root', d2['E1'], '--out', str(tmp_path / 'ne')]).returncode == 2 and os.listdir(tmp_path / 'ne') == ['x']
    # E1 with D-3b roots; a twelve family with two sizes; wrong family root; missing commitment / short campaign; unknown family
    o = str(tmp_path / 'e1d3b'); _run(base + ['--mode', 'partial', '--family', 'E1', '--d2-root', d2['E1'], '--d3b-root', f'L1.00={d3["L1.00"]}', '--out', o]); m = _rec(o, 'partial_E1'); assert m['stage'] == 'inputs' and m['gates']['G_inputs_resolved'] is False and 'supplies' not in m
    o = str(tmp_path / 'two'); _run(base + ['--mode', 'partial', '--family', 'E2', '--d2-root', d2['E2'], '--d3b-root', f'L1.00={d3["L1.00"]}', '--d3b-root', f'L1.20={d3["L1.20"]}', '--out', o]); m = _rec(o, 'partial_E2'); assert m['stage'] == 'inputs' and 'supplies' not in m
    o = str(tmp_path / 'wrongfam'); _run(base + ['--mode', 'partial', '--family', 'E7', '--d2-root', d2['E2'], '--out', o]); m = _rec(o, 'partial_E7'); assert m['stage'] == 'inputs' and m['gates']['G_inputs_resolved'] is False
    o = str(tmp_path / 'nocommit'); _run([SCRIPT, '--mt', MT, '--phaseb', P, '--phasec', PC, '--campaign-id', 'SELFTEST_CAMPAIGN_01', '--selftest-small', '--selftest-skip-env-lock', '--mode', 'partial', '--family', 'E1', '--d2-root', d2['E1'], '--out', o]); m = _rec(o, 'partial_E1'); assert m['stage'] == 'trusted_inputs' and m['gates']['G_commitment_form'] is False
    o = str(tmp_path / 'shortcamp'); _run(_base(C, camp='short') + ['--mode', 'partial', '--family', 'E1', '--d2-root', d2['E1'], '--out', o]); m = _rec(o, 'partial_E1'); assert m['stage'] == 'trusted_inputs' and m['gates']['G_commitment_form'] is False
    o = str(tmp_path / 'e9'); _run(base + ['--mode', 'partial', '--family', 'E9', '--d2-root', d2['E1'], '--out', o]); m = _rec(o, 'partial_E9'); assert m['stage'] == 'scope'
    # FORMAL mode in the sandbox: the registered environment HARD gate stops the run before any input is read (never a formal record here); probe outside 1..n-1
    o = str(tmp_path / 'formal'); r = _run([SCRIPT, '--mt', MT, '--phaseb', P, '--phasec', PC, '--target-commitment', C, '--campaign-id', 'FORMAL_CAMPAIGN_01', '--mode', 'partial', '--family', 'E1', '--d2-root', d2['E1'], '--out', o]); m = _rec(o, 'partial_E1')
    assert r.returncode == 1 and m['stage'] == 'environment' and m['selftest'] is False and m['formal'] is True and m['gates']['G_env_lock'] is False and 'supplies' not in m and m['D4C1_PARTIAL_PASS'] is False
    o = str(tmp_path / 'probe0'); _run(base + ['--mode', 'partial', '--family', 'E1', '--d2-root', d2['E1'], '--out', o, '--probe-n', '0']); m = _rec(o, 'probe_E1'); assert m['stage'] == 'probe' and 'partial' not in m
    o = str(tmp_path / 'probebig'); _run(base + ['--mode', 'partial', '--family', 'E1', '--d2-root', d2['E1'], '--out', o, '--probe-n', '2000']); m = _rec(o, 'probe_E1'); assert m['stage'] == 'probe'


@need_ext
def test_script_selftest_fixture_equivalence(tmp_path):
    o = str(tmp_path / 'fx'); r = _run([SCRIPT, '--mt', MT, '--phaseb', P, '--phasec', PC, '--out', o, '--selftest-fixture', '--selftest-n', '2'], timeout=1200); m = _rec(o, 'selftest')
    assert r.returncode == 0 and m['stage'] == 'complete' and m['D4C1_PARTIAL_PASS'] is False and m['D4C1_COMBINE_PASS'] is False and m['mode'] == 'selftest' and all(m['gates'][g] is True for g in m['required_inventory']), (r.stdout[-800:], m['failures'])
    s = m['selftest']; assert s['equivalence']['content_equal'] is True and s['equivalence']['single_payload_sha256'] != s['equivalence']['combined_payload_sha256'] and set(s['partials']) == set(FAMS) and all(v.startswith('refused') for v in s['refusals'].values()) and len(s['refusals']) == 5 and s['n'] == 2
    assert os.path.isfile(os.path.join(o, 'combined', 'd4c1_sealed_calibration.json')) and all(os.path.isfile(os.path.join(o, f'part_{f}', f'd4c1_partial_{f}_record.json')) for f in FAMS)


# ------------------------------------------------------------------------------------------------------------------------------------------- notebooks
def _cells(path):
    nb = json.load(open(path)); return [''.join(c['source']) for c in nb['cells']]


@pytest.mark.parametrize('nb,req_name,n_req', [(NB_P, 'REQUIRED_PARTIAL', 24), (NB_C, 'REQUIRED_COMBINE', 18)])
def test_notebook_structure_and_trusted_inventory(nb, req_name, n_req):
    md, c0, c1, c2, c3 = _cells(nb); assert md.startswith('# MirrorTopology Step 1 — Phase D4C-1')
    # R-D4C0-B: the output policy runs BEFORE the first mkdir / lock publication; one makedirs; the attempt cell takes the anchor from the LOCK and re-validates it with the same function
    assert c1.index('# OUTPUT-ANCHOR') < c1.index('def _safe_output_anchor') < c1.index('os.makedirs(OUT') < c1.index('# LOCK-BUILD') < c1.index('_publish(LOCK_PATH') and c1.count('os.makedirs') == 1 and 'OUT=_safe_output_anchor(OUT, _protected_roots())' in c1
    assert "ANCHOR=lock['out']" in c2 and '_safe_output_anchor(ANCHOR' in c2 and c2.index('_safe_output_anchor(ANCHOR') < c2.index('_publish(FIN, REC)') and "_verify_locked_state('precheck')" in c2 and "_verify_locked_state('prelaunch')" in c2 and c2.index("_verify_locked_state('precheck')") < c2.index("REC['stage']='staging'") < c2.index("_verify_locked_state('prelaunch')") < c2.index('subprocess.run(')
    # the trusted REQUIRED inventory of the notebook equals the script constant (extracted by AST from the lock-bound script at run time as well)
    req = _ast_required(req_name); expected = ('REQUIRED_EXPECTED_PARTIAL=' if nb == NB_P else 'REQUIRED_EXPECTED=') + json.dumps(req).replace(' ', '').replace('"', "'"); assert len(req) == n_req and expected in c2 and (f"t.id=='{req_name}'" in c2 or (nb == NB_P and "t.id==REQ_NAME" in c2 and "REQ_NAME='REQUIRED_SUBPARTIAL' if SUB else 'REQUIRED_PARTIAL'" in c2))
    if nb == NB_P: assert 'REQUIRED_EXPECTED_SUBPARTIAL=' + json.dumps(_ast_required('REQUIRED_SUBPARTIAL')).replace(' ', '').replace('"', "'") in c2 and 'ROW_RANGE = None' in c0 and 'INSTRUMENT = False' in c0 and 'OUT_ROOT = None' in c0 and "'--row-range'" in c2 and "'--instrument'" in c2
    # no nonce, no self-test flag, no probe in the formal launch (probe only when PROBE), formal profile; the scientific outcome is not a pass condition
    assert 'nonce' not in c2.lower().replace('the nonce is never entered here', '') and '--selftest' not in c2 and "'--profile','production_official'" in c2 and 'is NOT a condition' in c2
    assert 'is not a JSON object' in c2 and 'if doc_ok and not isinstance(doc, dict)' in c2 and c2.index('if doc_ok and not isinstance(doc, dict)') < c2.index('if doc_ok and isinstance(doc, dict)')      # R-D4C1-B
    if nb == NB_P:
        assert "TARGET_COMMITMENT = '<64-hex commitment" in c0 and 'PROBE_N = None' in c0 and "'--probe-n'" in c2 and 'not PROBE' in c2 and "'--target-commitment',TARGET_COMMITMENT,'--campaign-id',CAMPAIGN_ID" in c2 and 'cfg\\d+_(b0|b1|fit)' in c2 and "'--d3b-root'" in c2 and 'vm.total>(40e9' in c1 and "d4c1_partial_{lock" in c3
        assert "('pseudo_identity', PROBE or (pp.get('sha256_T1')==idn.get('T1_sha256')" in c2 and "doc.get('w2_context_sha256')==pins['d2w_context_sha256']" in c2 and "('no_aggregation', 'calibration' not in doc" in c2
    else:
        assert 'PARTIAL_RUN_DIRS' in c0 and "r.get('D4C1_PARTIAL_PASS') is True" in c1 and "partial_records={f: sha(f\"{p}/d4c1_partial_{f}_record.json\")" in c2 and "('provenance', sorted(cp)==['E1','E2','E7','E8']" in c2 and "pp.get('n')==2000" in c2 and "d4c1_combine_{REPO_COMMIT" in c3


# ---- attempt-cell simulation (mocked child process) for the partial launcher
def _fake_source(root):
    pb = root / 'engine' / 'phaseB'; (pb / 'd').mkdir(parents=True); (root / 'phaseC').mkdir()
    shutil.copy(SCRIPT, pb / 'd' / 'd4c1_calibration.py'); (pb / 'd' / 'd3_pins.json').write_text(json.dumps(dict(schema='d3_pins_v1', d2w_context_sha256='c' * 64, pseudo_paired_sha256='p' * 64)))
    RA = {}
    for k in ('registered_assets/d2/d2_generation_ledger.json', 'registered_assets/d3b/d3b_generation_ledger.json', 'registered_assets/d3b/d3b_outer_receipt.json', 'registered_assets/d3c/d3c_profile_ledger.json', 'registered_assets/d3c/d3c_outer_receipt.json', 'registered_assets/d4c0/d4c0_ledger.json', 'registered_assets/d4c0/d4c0_outer_receipt.json', 'registered_assets/b3_2_twelve_assets.json', 'registered_assets/b3_2_shared_null_asset.json'):
        p = pb / k; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(dict(TEST_ONLY=k))); RA[k] = str(p)
    inv = dict(engine_version='0.0.0-TEST', d_sha256={'d/d4c1_calibration.py': sha(pb / 'd' / 'd4c1_calibration.py'), 'd/d3_pins.json': sha(pb / 'd' / 'd3_pins.json')}, registered_assets_sha256={k: sha(p) for k, p in RA.items()})
    (pb / 'B2_completion_inventory.json').write_text(json.dumps(inv)); return str(root), str(pb), RA


def _roots(tmp_path, fam='E2'):
    d2 = tmp_path / 'in_d2'; (d2 / 'cfg20101_b0').mkdir(parents=True); (d2 / 'cfg20101_w2').mkdir(); (d2 / f'ref_{fam}_fit').mkdir(); (d2 / 'd2_bank_registry.json').write_text('{}'); (d2 / 'cfg20101_b0' / 'a.npz').write_bytes(b'\0' * 1000); (d2 / 'cfg20101_w2' / 'w.npz').write_bytes(b'\0' * 7000); (d2 / f'ref_{fam}_fit' / 'r.npz').write_bytes(b'\0' * 500)
    d3 = {}
    for s in SIZES: p = tmp_path / f'in_d3b_{s}'; (p / 'cfg20104_b0').mkdir(parents=True); (p / 'd3_bank_registry.json').write_text('{}'); (p / 'cfg20104_b0' / 'b.npz').write_bytes(b'\0' * 300); d3[s] = str(p)
    return str(d2), d3


def _ns(tmp_path, commit, mt, pb, RA, out, d2, d3, staged, fam='E2', probe=None, row_range=None, instrument=False, out_root=None):
    inv = json.load(open(f'{pb}/B2_completion_inventory.json'))
    return dict(sys=sys, os=os, json=json, hashlib=hashlib, shutil=shutil, time=__import__('time'), re=re, sha=sha, REPO_COMMIT=commit, FAMILY=fam, D2_RUN_ROOT=d2, D3B_RUN_ROOTS=dict(d3), TARGET_COMMITMENT='a' * 64, CAMPAIGN_ID='TEST_CAMPAIGN_01', PROBE_N=probe, ROW_RANGE=row_range, INSTRUMENT=instrument, OUT_ROOT=out_root, SUB=(row_range is not None), RTAG=(f'_r{row_range[0]:04d}_{row_range[1]:04d}' if row_range else ''), STAGE_LOCAL=staged, STAGE_ROOT=str(tmp_path / 'stage'), MT=mt, PHASEB=pb, PHASEC=f'{mt}/phaseC', SCRIPT=f'{pb}/d/d4c1_calibration.py', INV=f'{pb}/B2_completion_inventory.json', PINS=f'{pb}/d/d3_pins.json', RA=dict(RA), RA_SHA={k: sha(p) for k, p in RA.items()}, inv=inv, pins=json.load(open(f'{pb}/d/d3_pins.json')), OUT=str(out), RAM_INFO=dict(total_bytes=1))


def _lock_src(nb_path):
    md, c0, c1, c2, c3 = _cells(nb_path); return c1[c1.index('# OUTPUT-ANCHOR'):], c2


PRE_CASES = ['symlink_before_preflight', 'out_inside_input', 'out_inside_source', 'out_inside_stage', 'out_is_file', 'out_with_foreign_file', 'out_new_ok', 'out_owned_ok']


@pytest.mark.parametrize('case', PRE_CASES)
def test_partial_preflight_output_policy_refuses_before_any_write(tmp_path, case):
    commit = 'a' * 40; mt, pb, RA = _fake_source(tmp_path / 'scratch'); d2, d3 = _roots(tmp_path); lock_src, _ = _lock_src(NB_P); out = tmp_path / 'out'; target = None
    if case == 'symlink_before_preflight': target = tmp_path / 'tgt'; target.mkdir(); (target / 'sentinel.npz').write_bytes(b'S'); os.symlink(target, out)
    if case == 'out_inside_input': out = tmp_path / 'in_d2' / 'x_out'
    if case == 'out_inside_source': out = os.path.join(pb, 'd', 'x_out')
    if case == 'out_inside_stage': out = tmp_path / 'stage' / 'x_out'
    if case == 'out_is_file': out.write_text('file')
    if case == 'out_with_foreign_file': out.mkdir(); (out / 'foreign.npz').write_bytes(b'F')
    if case == 'out_owned_ok': out.mkdir(); (out / 'd4c1_partial_lock.json').write_text('{}'); (out / 'd4c1_partial_final_record.json').write_text('{}'); (out / 'run_20260101T000000Z_0123456789').mkdir()
    ns = _ns(tmp_path, commit, mt, pb, RA, out, d2, d3, False)
    with contextlib.redirect_stdout(io.StringIO()):
        if case.endswith('_ok'): exec(compile(lock_src, 'nb_anchor', 'exec'), ns); assert os.path.isfile(ns['LOCK_PATH']) and sha(ns['LOCK_PATH']) == ns['LOCK_SHA256'] and ns['lock']['schema'] == 'd4c1_partial_launcher_lock_v1' and ns['lock']['target_commitment'] == 'a' * 64; return
        with pytest.raises(RuntimeError, match='unsafe output'): exec(compile(lock_src, 'nb_anchor', 'exec'), ns)
    assert 'LOCK_PATH' not in ns and 'lock' not in ns
    if case in ('out_inside_input', 'out_inside_source', 'out_inside_stage'): assert not os.path.exists(out)
    if case == 'symlink_before_preflight': assert os.listdir(target) == ['sentinel.npz']
    if case == 'out_is_file': assert out.read_text() == 'file'


NB_CASES = ['ok', 'staged_ok', 'probe_never_pass', 'retry_after_old_success', 'pass_false', 'rc1', 'missing_record', 'commit_changed', 'script_changed', 'lock_file_changed', 'root_changed', 'script_changed_during_staging', 'anchor_foreign_file', 'evidence_tampered', 'evidence_unbound_family', 'evidence_no_aggregation', 'evidence_plan_objects_unstable', 'pseudo_identity_mismatch', 'commitment_mismatch', 'selftest_true', 'false_required_gate', 'required_inventory_mismatch', 'script_required_changed', 'launch_failure', 'disk_insufficient', 'result_attempt_mismatch', 'doc_null', 'doc_empty_list', 'doc_list', 'doc_string', 'doc_number', 'doc_empty_dict']
DOC_CASES = {'doc_null': 'null', 'doc_empty_list': '[]', 'doc_list': '[{"schema": "family_partial_calibration_v1"}]', 'doc_string': '"family_partial_calibration_v1"', 'doc_number': '1', 'doc_empty_dict': '{}'}
NO_LAUNCH = {'commit_changed', 'script_changed', 'lock_file_changed', 'root_changed', 'script_changed_during_staging', 'disk_insufficient'}
STAGED = {'staged_ok', 'script_changed_during_staging', 'disk_insufficient'}


@pytest.mark.parametrize('case', NB_CASES)
def test_partial_notebook_attempt_cell_binds_lock_and_records_failures(tmp_path, case):
    lock_src, c2 = _lock_src(NB_P); commit = 'a' * 40; mt, pb, RA = _fake_source(tmp_path / 'scratch'); out = tmp_path / 'out'; out.mkdir(); d2, d3 = _roots(tmp_path); staged = case in STAGED; probe = 3 if case == 'probe_never_pass' else None
    if case == 'script_required_changed': s = open(f'{pb}/d/d4c1_calibration.py').read(); assert '"G_pseudo_identity_bound", "G_record_saved")' in s; open(f'{pb}/d/d4c1_calibration.py', 'w').write(s.replace('"G_pseudo_identity_bound", "G_record_saved")', '"G_record_saved")', 1)); inv = json.load(open(f'{pb}/B2_completion_inventory.json')); inv['d_sha256']['d/d4c1_calibration.py'] = sha(f'{pb}/d/d4c1_calibration.py'); open(f'{pb}/B2_completion_inventory.json', 'w').write(json.dumps(inv))
    ns = _ns(tmp_path, commit, mt, pb, RA, out, d2, d3, staged, probe=probe); REQ = _ast_required('REQUIRED_PARTIAL', f'{pb}/d/d4c1_calibration.py')
    with contextlib.redirect_stdout(io.StringIO()): exec(compile(lock_src, 'nb_anchor', 'exec'), ns)
    lock = ns['lock']; lock_sha = ns['LOCK_SHA256']; assert lock['probe_n'] == probe and lock['family'] == 'E2'
    old = dict(schema='TEST_ONLY_old', partial_pass=True, stage='complete', attempt_id='OLD_ATTEMPT')
    if case == 'retry_after_old_success': (out / 'd4c1_partial_final_record.json').write_text(json.dumps(old))
    if case == 'root_changed': ns['D2_RUN_ROOT'] = str(tmp_path / 'other'); os.makedirs(ns['D2_RUN_ROOT'])
    if case == 'script_changed': open(ns['SCRIPT'], 'a').write('# changed after the lock\n')
    if case == 'lock_file_changed': open(ns['LOCK_PATH'], 'a').write('\n')
    if case == 'anchor_foreign_file': (out / 'foreign.bin').write_bytes(b'F')
    git = dict(head=('b' * 40 if case == 'commit_changed' else commit)); n_copies = [0]; calls = []
    def copytree(src, dst, **kw):
        r = shutil.copytree(src, dst, **kw); n_copies[0] += 1
        if n_copies[0] == 2 and case == 'script_changed_during_staging': open(ns['SCRIPT'], 'a').write('# changed during staging\n')
        return r
    def check_output(args, **kw): return (git['head'] if 'rev-parse' in args else '') + '\n'
    def run(args, **kw):
        calls.append(list(args))
        if case == 'launch_failure': raise OSError('TEST_ONLY cannot start subprocess')
        run_dir = args[args.index('--out') + 1]; att = args[args.index('--attempt-id') + 1]; lk = args[args.index('--launcher-lock-sha256') + 1]; os.makedirs(os.path.join(run_dir, 'archive')); open(os.path.join(run_dir, 'archive', 'index.json'), 'w').write('{}')
        tag = ('probe_' if probe else 'partial_') + 'E2'; n_rows = probe or 2000; mode = 'smoke' if probe else 'official'
        fps = {'E2': {}, **{f'E2/{s}': {} for s in SIZES}, **{f'twelve:E2/{s}': {} for s in SIZES}}
        doc = dict(schema='family_partial_calibration_v1', kind='family_partial_calibration', engine_version=lock['engine'], mode=mode, family=('E7' if case == 'evidence_unbound_family' else 'E2'), w2_context_sha256='c' * 64, thresholds=dict(target=None, target_commitment=('b' * 64 if case == 'commitment_mismatch' else lock['target_commitment']), pseudo=dict(n=n_rows, sha256_T1=('x' * 64 if case == 'pseudo_identity_mismatch' else 't' * 64), sha256_T2='u' * 64)),
                   per_pseudo_status=[dict(family='E2')] * n_rows, fingerprints=dict(at_gate=fps, at_end=fps), gate=dict(mode=mode, passed=True), binding=dict(partial_sha256='s' * 64, partial_dependencies={}), campaign=dict(id=lock['campaign_id'] + ('__PROBE' if probe else '')), plan_objects=dict(first_wave_shared=True, twelve_shared=True, twelve_present=True, twelve_shares_first_wave=(case != 'evidence_plan_objects_unstable'), stable_after=True))
        if case == 'evidence_no_aggregation': doc['calibration'] = {}
        fn = f'd4c1_{tag}_record.json'; data = (DOC_CASES[case].encode() if case in DOC_CASES else json.dumps(doc).encode()); open(os.path.join(run_dir, fn), 'wb').write(data); pe = {fn: dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))}      # R-D4C1-B: correctly re-hashed non-object documents
        if case == 'evidence_tampered': open(os.path.join(run_dir, fn), 'ab').write(b' ')
        gates = {k: True for k in REQ}
        if case == 'false_required_gate': gates['G_partial_verified'] = False
        rec = dict(schema='d4c1_run_record_v1', mode='partial', family='E2', stage='complete', failures=[], selftest=(case == 'selftest_true'), formal=True, probe=bool(probe), probe_n=probe, subpartial=False, row_range=None, instrument=False, D4C1_SUBPARTIAL_PASS=False, profile='production_official', attempt=dict(attempt_id=('OTHER' if case == 'result_attempt_mismatch' else att), launcher_lock_sha256=lk),
                   source=dict(script_sha256=lock['script_sha256'], inventory_sha256=lock['inventory_sha256'], pins_sha256=lock['pins_sha256'], engine_version=lock['engine']), target_commitment=lock['target_commitment'], campaign_id=lock['campaign_id'], gates=gates, required_inventory=(REQ[:-1] if case == 'required_inventory_mismatch' else list(REQ)), required_all_true=(case != 'false_required_gate'), seconds=1.5, stages_rss_mb=dict(final=1.0), stages_peak_rss_mb=dict(final=1.0), timings={},
                   partial=dict(partial_sha256='s' * 64, n_pseudo=n_rows, verification=dict(ok=True, registered_context_ok=True), eligibility_counts={}, expanded=0, twelve_evaluated=0, archive_entries=1), pseudo=dict(n=2000, identity=dict(T1_sha256='t' * 64, T2_sha256='u' * 64, paired_sha256='p' * 64)), w2_context=dict(context_sha256='c' * 64), published_evidence=pe, D4C1_PARTIAL_PASS=(case != 'pass_false' and not probe))
        if case != 'missing_record': open(os.path.join(run_dir, f'd4c1_{tag}_run.json'), 'w').write(json.dumps(rec))
        class R: returncode = 1 if case == 'rc1' else 0; stdout = 'TEST'; stderr = ''
        return R()
    ns['subprocess'] = type('SP', (), dict(check_output=staticmethod(check_output), run=staticmethod(run)))
    ns['shutil'] = type('SH', (), dict(copytree=staticmethod(copytree), copy2=staticmethod(shutil.copy2), rmtree=staticmethod(shutil.rmtree), disk_usage=staticmethod(lambda p: type('DU', (), dict(free=(0 if case == 'disk_insufficient' else 10**12)))())))
    buf = io.StringIO()
    if case == 'anchor_foreign_file':
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()), pytest.raises(RuntimeError): exec(compile(c2, 'nb_attempt', 'exec'), ns)
        assert sorted(os.listdir(out)) == ['d4c1_partial_lock.json', 'foreign.bin'] and calls == []; return
    with contextlib.redirect_stdout(buf): exec(compile(c2, 'nb_attempt', 'exec'), ns)
    fin = json.load(open(out / 'd4c1_partial_final_record.json')); assert fin['schema'] == 'd4c1_partial_launcher_final_record_v1' and fin['lock_sha256'] == lock_sha and fin['attempt_id'] == ns['ATTEMPT'] and fin['output_anchor'] == str(out) and fin['probe'] is bool(probe)
    if case in NO_LAUNCH: assert calls == [] and fin['partial_pass'] is False and fin['failures'] and fin['exception']; return
    if case == 'launch_failure': assert fin['partial_pass'] is False and fin['stage'] == 'launch'; return
    a = calls[0]; assert len(calls) == 1 and a[1] == ns['SCRIPT'] and '--selftest-small' not in a and '--selftest-skip-env-lock' not in a and a[a.index('--attempt-id') + 1] == ns['ATTEMPT'] and a[a.index('--family') + 1] == 'E2' and a[a.index('--target-commitment') + 1] == 'a' * 64 and a[a.index('--campaign-id') + 1] == 'TEST_CAMPAIGN_01' and a.count('--d3b-root') == 3 and (('--probe-n' in a) is bool(probe))
    if staged: assert a[a.index('--d2-root') + 1] == str(tmp_path / 'stage' / 'd2') and not os.path.exists(tmp_path / 'stage' / 'd2' / 'cfg20101_w2') and os.path.exists(tmp_path / 'stage' / 'd2' / 'cfg20101_b0') and os.path.exists(tmp_path / 'stage' / 'd3b_L1.00' / 'cfg20104_b0') and fin['staging']['input_bytes'] == 1000 + 500 + 2 + 3 * (300 + 2) and fin['staging']['d2_units'] == 2
    else: assert a[a.index('--d2-root') + 1] == d2
    if case in ('ok', 'staged_ok', 'retry_after_old_success'):
        assert fin['partial_pass'] is True and fin['failures'] == [] and fin['D4C1_PARTIAL_PASS'] is True and fin['gates_ok'] is True and fin['bindings_ok'] is True and fin['evidence_ok'] is True and fin['launcher_fallback'] is False and set(fin['bindings']) == {'live_source_precheck', 'live_source_prelaunch'} and fin['bindings']['live_source_precheck']['registered_assets_sha256'] == lock['registered_assets_sha256']
        if case == 'retry_after_old_success': assert json.load(open(fin['superseded_previous_record'])) == old and fin['attempt_id'] != 'OLD_ATTEMPT'
        return
    assert fin['partial_pass'] is False, case
    if case == 'probe_never_pass': assert fin['D4C1_PARTIAL_PASS'] is False and fin['failures'] == [] and fin['evidence_ok'] is True and fin['gates_ok'] is True
    if case == 'pass_false': assert fin['D4C1_PARTIAL_PASS'] is False and fin['failures'] == []
    if case == 'rc1': assert fin['exit_code'] == 1 and fin['gates_ok'] is True
    if case == 'missing_record': assert fin['launcher_fallback'] is True and fin['gates_ok'] is None
    if case == 'selftest_true': assert fin['launcher_fallback'] is True and any('selftest' in f for f in fin['failures'])
    if case in ('false_required_gate', 'required_inventory_mismatch', 'script_required_changed'): assert fin['gates_ok'] is False and fin['launcher_fallback'] is False
    if case == 'result_attempt_mismatch': assert fin['bindings_ok'] is False and any('attempt_id' in f for f in fin['failures'])
    if case in ('evidence_tampered', 'evidence_unbound_family', 'evidence_no_aggregation', 'evidence_plan_objects_unstable', 'pseudo_identity_mismatch', 'commitment_mismatch') or case in DOC_CASES: assert fin['evidence_ok'] is False and fin['gates_ok'] is True and fin['bindings_ok'] is True and fin['D4C1_PARTIAL_PASS'] is True, fin['failures']
    if case in DOC_CASES and case != 'doc_empty_dict': assert any('not a JSON object' in f for f in fin['failures']), fin['failures']


COMBINE_DOC_CASES = {'doc_null': 'null', 'doc_list': '[1]', 'doc_string': '"sealed_calibration"', 'doc_number': '0', 'doc_empty_dict': '{}'}


@pytest.mark.parametrize('case', ['ok', 'provenance_mismatch', 'partial_record_changed_after_lock', 'pass_false'] + sorted(COMBINE_DOC_CASES))
def test_combine_notebook_attempt_cell(tmp_path, case):
    md, c0, c1, c2, c3 = _cells(NB_C); lock_src = c1[c1.index('# OUTPUT-ANCHOR'):]; commit = 'a' * 40; mt, pb, RA = _fake_source(tmp_path / 'scratch'); out = tmp_path / 'out'; out.mkdir(); REQ = _ast_required('REQUIRED_COMBINE')
    dirs = {}; runs = {}
    for f in FAMS:
        d = tmp_path / f'p_{f}'; (d / 'archive').mkdir(parents=True); (d / 'archive' / 'index.json').write_text('{}'); (d / f'd4c1_partial_{f}_record.json').write_text(json.dumps(dict(family=f))); (d / f'd4c1_partial_{f}_run.json').write_text(json.dumps(dict(D4C1_PARTIAL_PASS=True, family=f, probe=False, selftest=False, target_commitment='a' * 64, campaign_id='TEST_CAMPAIGN_01', partial=dict(partial_sha256=f * 64), attempt={}, source={})))
        dirs[f] = str(d); runs[f] = dict(dir=str(d), run_sha256=sha(d / f'd4c1_partial_{f}_run.json'), record_sha256=sha(d / f'd4c1_partial_{f}_record.json'), partial_sha256=f * 64, attempt={}, source={})
    ns = dict(sys=sys, os=os, json=json, hashlib=hashlib, shutil=shutil, time=__import__('time'), re=re, sha=sha, REPO_COMMIT=commit, PARTIAL_RUN_DIRS=dirs, PARTIAL_RUNS=runs, TARGET_COMMITMENT='a' * 64, CAMPAIGN_ID='TEST_CAMPAIGN_01', STAGE_LOCAL=False, STAGE_ROOT=str(tmp_path / 'stage'), MT=mt, PHASEB=pb, PHASEC=f'{mt}/phaseC', SCRIPT=f'{pb}/d/d4c1_calibration.py', INV=f'{pb}/B2_completion_inventory.json', PINS=f'{pb}/d/d3_pins.json', RA=dict(RA), RA_SHA={k: sha(p) for k, p in RA.items()}, inv=json.load(open(f'{pb}/B2_completion_inventory.json')), pins=json.load(open(f'{pb}/d/d3_pins.json')), OUT=str(out), RAM_INFO=dict(total_bytes=1))
    with contextlib.redirect_stdout(io.StringIO()): exec(compile(lock_src, 'nb_anchor', 'exec'), ns)
    lock = ns['lock']; assert lock['schema'] == 'd4c1_combine_launcher_lock_v1' and lock['partial_runs'] == runs
    if case == 'partial_record_changed_after_lock': open(os.path.join(dirs['E7'], 'd4c1_partial_E7_record.json'), 'a').write(' ')
    calls = []
    def check_output(args, **kw): return (commit if 'rev-parse' in args else '') + '\n'
    def run(args, **kw):
        calls.append(list(args)); run_dir = args[args.index('--out') + 1]; att = args[args.index('--attempt-id') + 1]; lk = args[args.index('--launcher-lock-sha256') + 1]; os.makedirs(os.path.join(run_dir, 'archive')); open(os.path.join(run_dir, 'archive', 'index.json'), 'w').write('{}')
        prov = {f: dict(partial_sha256=(('z' * 64) if (case == 'provenance_mismatch' and f == 'E8') else f * 64)) for f in FAMS}
        doc = dict(mode='official', engine_version=lock['engine'], thresholds=dict(target=None, target_commitment='a' * 64, pseudo=dict(n=2000, sha256_T1='t' * 64, sha256_T2='u' * 64)), per_pseudo_family_status=[{}] * 2000, w2_context_sha256='c' * 64, binding=dict(run_manifest_sha256='m' * 64, run_manifest_ref=dict(identity=dict(kind='sealed_calibration')), combiner=dict(partials=prov, campaign=dict(id='TEST_CAMPAIGN_01'), target_commitment='a' * 64), sealed_dependencies=dict(families=list(FAMS), require_all_families=True)),
                   branch_completeness=dict(all_registered_families=True), calibration={l: dict(summary=dict(n=2000, threshold=(0.05 if l == 'support' else 0.01))) for l in ('support', 'strong')}, final_label_released=False, families={}, cases={})
        data = (COMBINE_DOC_CASES[case].encode() if case in COMBINE_DOC_CASES else json.dumps(doc).encode()); open(os.path.join(run_dir, 'd4c1_sealed_calibration.json'), 'wb').write(data)
        rec = dict(schema='d4c1_run_record_v1', mode='combine', stage='complete', failures=[], selftest=False, formal=True, probe=False, profile='production_official', attempt=dict(attempt_id=att, launcher_lock_sha256=lk), source=dict(script_sha256=lock['script_sha256'], inventory_sha256=lock['inventory_sha256'], pins_sha256=lock['pins_sha256'], engine_version=lock['engine']), target_commitment='a' * 64, campaign_id='TEST_CAMPAIGN_01',
                   gates={k: True for k in REQ}, required_inventory=list(REQ), required_all_true=True, seconds=1.0, timings={}, sealed=dict(run_manifest_sha256='m' * 64), partials={f: dict(record_sha256=runs[f]['record_sha256'], D4C1_PARTIAL_PASS=True) for f in FAMS}, pseudo=dict(n=2000, identity=dict(T1_sha256='t' * 64, T2_sha256='u' * 64, paired_sha256='p' * 64)), w2_context=dict(context_sha256='c' * 64), published_evidence={'d4c1_sealed_calibration.json': dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))}, D4C1_COMBINE_PASS=(case != 'pass_false'))
        open(os.path.join(run_dir, 'd4c1_combine_run.json'), 'w').write(json.dumps(rec))
        class R: returncode = 0; stdout = 'TEST'; stderr = ''
        return R()
    ns['subprocess'] = type('SP', (), dict(check_output=staticmethod(check_output), run=staticmethod(run)))
    with contextlib.redirect_stdout(io.StringIO()): exec(compile(c2, 'nb_attempt', 'exec'), ns)
    fin = json.load(open(out / 'd4c1_combine_final_record.json')); assert fin['schema'] == 'd4c1_combine_launcher_final_record_v1' and fin['attempt_id'] == ns['ATTEMPT']
    if case == 'partial_record_changed_after_lock': assert calls == [] and fin['combine_pass'] is False and 'partial_records' in fin['failures'][0]; return
    a = calls[0]; assert a.count('--partial') == 4 and a[a.index('--mode') + 1] == 'combine' and '--selftest-small' not in a
    if case == 'ok': assert fin['combine_pass'] is True and fin['failures'] == [] and fin['evidence_ok'] is True and fin['bindings_ok'] is True
    if case == 'provenance_mismatch': assert fin['combine_pass'] is False and fin['evidence_ok'] is False and any('provenance' in f for f in fin['failures'])
    if case == 'pass_false': assert fin['combine_pass'] is False and fin['D4C1_COMBINE_PASS'] is False and fin['failures'] == []
    if case in COMBINE_DOC_CASES: assert fin['combine_pass'] is False and fin['evidence_ok'] is False and fin['bindings_ok'] is True and (case == 'doc_empty_dict' or any('not a JSON object' in f for f in fin['failures'])), fin['failures']
