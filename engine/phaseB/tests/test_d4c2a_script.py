# -*- coding: utf-8 -*-
"""D4C-2a connection-script modes on the generators' small synthetic banks (engine 0.108.0; never a formal PASS in the sandbox): (1) sub-partials (--row-range) of E2 with the
12-position inputs in two ranges -> --mode combine-family -> the family partial equals (content) the single-run self-test partial of E2 and is consumed by --mode combine with the
E1 / E7 / E8 partials; refusals (gap, probe + row range, instrument without probe, bad range, sub-partial through --mode combine); (2) --instrument on the E1 probe (profile record
published; the probe record unchanged); (3) --mode screen on E2 (registered W2 decisions on the synthetic banks; rows; E1 refused) and --mode certificate over the screen +
evaluated records (algebraic statement; never a calibration PASS); (4) the trusted REQUIRED inventories by AST."""
import os, sys, json, hashlib
import pytest
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); sys.path[:0] = [P, os.path.join(P, 'tests')]
from test_d4c1_script import banks, partials, _base, _rec, _run, _ast_required, _commit, SCRIPT, MT, PC, need_ext, FAMS, SIZES, sha

ROWS = (('0:1', (0, 1)), ('1:2', (1, 2)))


@pytest.fixture(scope='module')
def subparts(banks, partials, tmp_path_factory):
    C = partials['C']; root = tmp_path_factory.mktemp('subs'); out = {}
    for arg, (a, b) in ROWS:
        o = str(root / f'E2_{a}_{b}'); args = _base(C) + ['--mode', 'partial', '--family', 'E2', '--d2-root', banks['d2']['E2'], '--out', o, '--row-range', arg] + [x for s in SIZES for x in ('--d3b-root', f'{s}={banks["d3"][s]}')] + ['--attempt-id', f'TEST_SUB_{a}', '--launcher-lock-sha256', 'e' * 64]
        r = _run(args); out[(a, b)] = dict(dir=o, rc=r.returncode, rec=_rec(o, f'subpartial_E2_r{a:04d}_{b:04d}'), stdout=r.stdout[-800:])
    oc = str(root / 'E2_family'); r = _run(_base(C) + ['--mode', 'combine-family', '--family', 'E2', '--out', oc] + [x for (a, b), v in out.items() for x in ('--subpartial', v['dir'])])
    return dict(C=C, runs=out, combine=dict(dir=oc, rc=r.returncode, rec=_rec(oc, 'partial_E2'), stdout=r.stdout[-800:]), root=str(root))


@need_ext
def test_subpartial_runs_and_family_combination(subparts, partials):
    from step1_engine import serialization as ser
    from step1_engine.d4c1_subpartial import strip_subpartial_provenance
    C = subparts['C']; REQ = _ast_required('REQUIRED_SUBPARTIAL'); assert len(REQ) == 25 and REQ[:11] == _ast_required('REQUIRED_COMMON') and REQ[11] == 'G_row_range'
    for (a, b), v in subparts['runs'].items():
        m = v['rec']; assert v['rc'] == 1 and m['stage'] == 'complete' and m['failures'] == [] and m['subpartial'] is True and m['row_range'] == [a, b] and m['D4C1_PARTIAL_PASS'] is False and m['D4C1_SUBPARTIAL_PASS'] is False and m['selftest'] is True and m['probe'] is False, v['stdout']
        assert m['required_inventory'] == REQ and all(m['gates'][g] is True for g in REQ if g != 'G_env_lock') and m['gates']['G_env_lock'] is False and m['partial']['n_pseudo'] == b - a and m['partial']['verification']['rows'] == [a, b]
        pib = m['pseudo_identity_bound']; assert pib['record']['n'] == 2 and pib['record']['rows'] == [a, b] and pib['consumed_arrays']['slice']['rows'] == [a, b] and pib['record']['slice_sha256_T1'] == pib['consumed_arrays']['slice']['sha256_T1']
        fn = f'd4c1_subpartial_E2_r{a:04d}_{b:04d}_record.json'; doc = ser.loads(open(os.path.join(v['dir'], fn), encoding='utf-8').read())
        assert doc['schema'] == 'family_subpartial_calibration_v1' and doc['rows']['start'] == a and doc['rows']['stop'] == b and doc['rows']['n_total'] == 2 and doc['thresholds']['pseudo']['rows'] == [a, b] and len(doc['per_pseudo_status']) == b - a and 'rows' not in doc['campaign'] and 'partial_dependencies' not in doc['binding'] and m['published_evidence'] == {fn: dict(sha256=sha(os.path.join(v['dir'], fn)), bytes=os.path.getsize(os.path.join(v['dir'], fn)))}
    c = subparts['combine']; m = c['rec']; REQC = _ast_required('REQUIRED_COMBINE_FAMILY'); assert len(REQC) == 20
    assert c['rc'] == 1 and m['stage'] == 'complete' and m['failures'] == [] and m['mode'] == 'combine-family' and m['family'] == 'E2' and m['D4C1_PARTIAL_PASS'] is False and m['subpartials_all_pass'] is False and m['required_inventory'] == REQC and all(m['gates'][g] is True for g in REQC if g != 'G_env_lock'), (c['stdout'], m['failures'])
    assert m['rows'] == dict(n=2, ranges=[[0, 1], [1, 2]]) and len(m['subpartials']) == 2 and all(v['ok'] for v in m['subpartials_verification']) and m['partial']['n_pseudo'] == 2 and m['partial']['subpartials'] == [[0, 1], [1, 2]] and m['partial']['verification']['ok']
    comb = ser.loads(open(os.path.join(c['dir'], 'd4c1_partial_E2_record.json'), encoding='utf-8').read()); single = ser.loads(open(os.path.join(partials['runs']['E2']['dir'], 'd4c1_partial_E2_record.json'), encoding='utf-8').read())
    assert comb['schema'] == 'family_partial_calibration_v1' and comb['binding']['subpartials']['ranges'] == [[0, 1], [1, 2]]
    # content equality with the single-run self-test partial of E2 apart from the gate (live environment snapshot per run)
    a_, b_ = strip_subpartial_provenance(comb), strip_subpartial_provenance(single)
    for d in (a_, b_): d['gate'] = None
    assert ser.dumps(a_) == ser.dumps(b_), [k for k in a_ if ser.dumps(a_[k]) != ser.dumps(b_[k])]
    assert comb['per_pseudo_status'] == single['per_pseudo_status'] and comb['archive_refs'] == single['archive_refs']


@need_ext
def test_family_combination_feeds_combine_and_refusals(subparts, partials, tmp_path):
    C = subparts['C']; runs = partials['runs']; parts = [x for f in FAMS for x in ('--partial', f'{f}={subparts["combine"]["dir"] if f == "E2" else runs[f]["dir"]}')]
    o = str(tmp_path / 'combine'); r = _run(_base(C) + ['--mode', 'combine', '--out', o] + parts); m = _rec(o, 'combine')
    assert r.returncode == 1 and m['stage'] == 'complete' and m['failures'] == [] and m['D4C1_COMBINE_PASS'] is False and all(m['gates'][g] is True for g in m['required_inventory'] if g != 'G_env_lock') and m['sealed']['calibration']['support']['n'] == 2, (r.stdout[-800:], m['failures'])
    assert m['partials']['E2']['dir'] == subparts['combine']['dir']
    # refusals: one range only (gap); a sub-partial directory given to --mode combine; probe + row range; instrument without probe; malformed ranges
    s = subparts['runs']; oo = str(tmp_path / 'gap'); rr = _run(_base(C) + ['--mode', 'combine-family', '--family', 'E2', '--out', oo, '--subpartial', s[(0, 1)]['dir']]); mm = _rec(oo, 'partial_E2')
    assert rr.returncode == 1 and mm['stage'] == 'rows' and mm['gates']['G_rows_tiled'] is False and 'partial' not in mm
    oo = str(tmp_path / 'dup'); rr = _run(_base(C) + ['--mode', 'combine-family', '--family', 'E2', '--out', oo, '--subpartial', s[(0, 1)]['dir'], '--subpartial', s[(0, 1)]['dir'], '--subpartial', s[(1, 2)]['dir']]); mm = _rec(oo, 'partial_E2'); assert mm['stage'] == 'rows' and mm['gates']['G_rows_tiled'] is False
    oo = str(tmp_path / 'camp'); rr = _run(_base(C, camp='ANOTHER_CAMPAIGN') + ['--mode', 'combine-family', '--family', 'E2', '--out', oo, '--subpartial', s[(0, 1)]['dir'], '--subpartial', s[(1, 2)]['dir']]); mm = _rec(oo, 'partial_E2'); assert mm['stage'] == 'inputs' and mm['gates']['G_subpartials_loaded'] is False
    oo = str(tmp_path / 'subcomb'); rr = _run(_base(C) + ['--mode', 'combine', '--out', oo] + [x for f in FAMS for x in ('--partial', f'{f}={s[(0, 1)]["dir"] if f == "E2" else runs[f]["dir"]}')]); mm = _rec(oo, 'combine'); assert mm['stage'] == 'inputs' and mm['gates']['G_partials_loaded'] is False
    for extra in (['--probe-n', '1', '--row-range', '0:1'], ['--instrument'], ['--row-range', '1:1'], ['--row-range', 'a:b'], ['--row-range', '2'], ['--row-range', '-1:1']):
        oo = str(tmp_path / ('bad' + str(len(os.listdir(tmp_path))))); rr = _run(_base(C) + ['--mode', 'partial', '--family', 'E1', '--d2-root', runs['E1']['dir'], '--out', oo] + extra); assert rr.returncode == 2 and not os.path.lexists(oo), extra
    oo = str(tmp_path / 'beyond'); rr = _run(_base(C) + ['--mode', 'partial', '--family', 'E1', '--d2-root', partials['runs']['E1']['rec']['inputs']['d2']['root'], '--out', oo, '--row-range', '1:5']); mm = _rec(oo, 'subpartial_E1_r0001_0005'); assert rr.returncode == 1 and mm['stage'] == 'rows' and 'exceeds' in mm['failures'][0]


@need_ext
def test_instrumented_probe_publishes_profile_and_leaves_the_record(banks, partials, tmp_path):
    from step1_engine import serialization as ser
    C = partials['C']; o = str(tmp_path / 'iprobe'); r = _run(_base(C) + ['--mode', 'partial', '--family', 'E1', '--d2-root', banks['d2']['E1'], '--out', o, '--probe-n', '2', '--instrument']); m = _rec(o, 'probe_E1')
    assert r.returncode == 1 and m['stage'] == 'complete' and m['failures'] == [] and m['instrument'] is True and m['probe'] is True and m['D4C1_PARTIAL_PASS'] is False and m['D4C1_SUBPARTIAL_PASS'] is False, r.stdout[-800:]
    pf = os.path.join(o, 'd4c1_probe_E1_profile.json'); prof = json.load(open(pf)); assert m['profile_record'] == dict(sha256=sha(pf), bytes=os.path.getsize(pf)) and prof['schema'] == 'd4c1_profile_record_v1' and prof['instrumentation']['cprofile'] is True and prof['segments']['count'] == 2 and prof['targets']['orchestrator._family_Q']['calls'] > 0 and prof['cprofile']['by_tottime']
    assert m['profile_summary']['segments'] == 2 and m['profile_summary']['missing_targets'] == [] and 'profile:' in r.stdout
    # the probe record is the same content as the uninstrumented probe of the fixture (same rows, same banks): payload SHA equality apart from the live gate
    from step1_engine.d4c1_subpartial import strip_subpartial_provenance
    a = ser.loads(open(os.path.join(o, 'd4c1_probe_E1_record.json'), encoding='utf-8').read()); b = ser.loads(open(os.path.join(partials['runs']['probe']['dir'], 'd4c1_probe_E1_record.json'), encoding='utf-8').read())
    a, b = strip_subpartial_provenance(a), strip_subpartial_provenance(b); a['gate'] = b['gate'] = None
    assert ser.dumps(a) == ser.dumps(b), [k for k in a if ser.dumps(a[k]) != ser.dumps(b[k])]


@need_ext
def test_screen_and_certificate_modes(banks, partials, subparts, tmp_path):
    from step1_engine import serialization as ser
    from step1_engine.infeasibility import check_screen_record, check_certificate
    C = partials['C']; REQS = _ast_required('REQUIRED_SCREEN'); REQC = _ast_required('REQUIRED_CERTIFICATE'); assert len(REQS) == 20 and len(REQC) == 14 and 'G_env_lock' not in REQC and REQS[:11] == _ast_required('REQUIRED_COMMON')
    o = str(tmp_path / 'screen'); r = _run(_base(C) + ['--mode', 'screen', '--family', 'E2', '--d2-root', banks['d2']['E2'], '--out', o, '--row-range', '0:2']); m = _rec(o, 'screen_E2_r0000_0002')
    assert r.returncode == 1 and m['stage'] == 'complete' and m['failures'] == [] and m['mode'] == 'screen' and m['D4C1_SCREEN_COMPLETE'] is False and m['D4C1_PARTIAL_PASS'] is False and m['required_inventory'] == REQS and all(m['gates'][g] is True for g in REQS if g != 'G_env_lock'), (r.stdout[-800:], m['failures'])
    sc = m['screen']; assert sc['n_rows'] == 2 and sc['rows'] == [0, 2] and set(sc['w2']) == set(SIZES) and sc['stages_covered'] == ['N0', 'N4'] and 'twelve' not in m and m['timings']['seconds_per_row'] > 0
    fn = 'd4c1_screen_E2_r0000_0002_record.json'; doc = ser.loads(open(os.path.join(o, fn), encoding='utf-8').read()); assert check_screen_record(doc)['ok'] and doc['pseudo']['n'] == 2000 and doc['rows'] == [0, 1] and doc['campaign']['screen'] is True and doc['target_commitment'] == C and m['published_evidence'] == {fn: dict(sha256=sha(os.path.join(o, fn)), bytes=os.path.getsize(os.path.join(o, fn)))}
    assert sc['w2_applicable'] == doc['w2_applicable'] == ((not any(v['trigger'] is True for v in doc['w2'].values())) and any(v['trigger'] == 'unknown' for v in doc['w2'].values()))
    # E1 refused; D-3b roots refused for the screen; the registered rows bound
    oo = str(tmp_path / 'e1'); rr = _run(_base(C) + ['--mode', 'screen', '--family', 'E1', '--d2-root', banks['d2']['E1'], '--out', oo]); mm = _rec(oo, 'screen_E1'); assert rr.returncode == 1 and mm['stage'] == 'scope'
    oo = str(tmp_path / 'd3b'); rr = _run(_base(C) + ['--mode', 'screen', '--family', 'E2', '--d2-root', banks['d2']['E2'], '--out', oo] + [x for s in SIZES for x in ('--d3b-root', f'{s}={banks["d3"][s]}')]); mm = _rec(oo, 'screen_E2'); assert mm['stage'] == 'inputs' and mm['gates']['G_inputs_resolved'] is False
    # certificate over the screen + the evaluated E2 family partial (from sub-partials) + the E1 partial; the self-test columns are the first --selftest-n rows for the evaluated records -> n mismatch refused; screen-only accepted
    oc = str(tmp_path / 'cert'); rc = _run(_base(C) + ['--mode', 'certificate', '--out', oc, '--screen', o]); mc = _rec(oc, 'certificate')
    assert rc.returncode == 0 and mc['stage'] == 'complete' and mc['failures'] == [] and mc['D4C1_CERTIFICATE_COMPLETE'] is False and mc['D4C1_PARTIAL_PASS'] is False and mc['required_inventory'] == REQC and all(mc['gates'][g] is True for g in REQC), (rc.stdout[-800:], mc['failures'])      # rc 0: the environment lock is not a certificate gate; COMPLETE stays False in a self-test
    cert = ser.loads(open(os.path.join(oc, 'd4c1_certificate_record.json'), encoding='utf-8').read()); assert check_certificate(cert)['ok'] and cert['n'] == 2000 and mc['certificate']['registered_blocking_counts']['support']['first_blocking_count'] == 81 and mc['certificate']['registered_blocking_counts']['strong']['first_blocking_count'] == 12
    assert cert['levels']['support']['proven_blocking_rows'] == doc['n_blocking'] == len(cert['rows']) and cert['levels']['support']['usable_true_impossible_by_wilson'] is False and cert['levels']['strong']['usable_true_impossible_by_wilson'] is False and 'NOT a calibration' in mc['certificate']['scope']
    oe = str(tmp_path / 'cert_ev'); re_ = _run(_base(C) + ['--mode', 'certificate', '--out', oe, '--screen', o, '--evaluated', subparts['combine']['dir']]); me = _rec(oe, 'certificate'); assert me['stage'] == 'inputs' and me['gates']['G_sources_loaded'] is False and any('columns' in x for x in me['failures'])
    oo = str(tmp_path / 'cert_none'); rr = _run(_base(C) + ['--mode', 'certificate', '--out', oo]); mm = _rec(oo, 'certificate'); assert mm['stage'] == 'inputs'
    oo = str(tmp_path / 'cert_camp'); rr = _run(_base(C, camp='ANOTHER_CAMPAIGN') + ['--mode', 'certificate', '--out', oo, '--screen', o]); mm = _rec(oo, 'certificate'); assert mm['stage'] == 'inputs'


# ------------------------------------------------------------------------------------------------------------------------------------------- notebooks (D4C-2a)
import io, re, json as _json, contextlib, shutil
from test_d4c1_script import _cells, _fake_source, _roots, _ns, _lock_src, NB_P, NB_C
NB_CF = os.path.join(P, 'd', 'MirrorTopology_Step1_D4C1_combine_family_v0.1.ipynb'); NB_S = os.path.join(P, 'd', 'MirrorTopology_Step1_D4C2_screen_v0.1.ipynb')


@pytest.mark.parametrize('nb,req_name,n_req,title', [(NB_CF, 'REQUIRED_COMBINE_FAMILY', 20, 'Phase D4C-2a：sub-partial から'), (NB_S, 'REQUIRED_SCREEN', 20, 'Phase D4C-2a：**count-envelope screen**')])
def test_new_notebook_structure_and_trusted_inventory(nb, req_name, n_req, title):
    md, c0, c1, c2, c3 = _cells(nb); assert md.startswith('# MirrorTopology Step 1 — ' + title)
    assert c1.index('# OUTPUT-ANCHOR') < c1.index('def _safe_output_anchor') < c1.index('os.makedirs(OUT') < c1.index('# LOCK-BUILD') < c1.index('_publish(LOCK_PATH') and c1.count('os.makedirs') == 1 and 'OUT=_safe_output_anchor(OUT, _protected_roots())' in c1
    assert "ANCHOR=lock['out']" in c2 and '_safe_output_anchor(ANCHOR' in c2 and c2.index('_safe_output_anchor(ANCHOR') < c2.index('_publish(FIN, REC)') and c2.index("_verify_locked_state('precheck')") < c2.index("REC['stage']='staging'") < c2.index("_verify_locked_state('prelaunch')") < c2.index('subprocess.run(')
    req = _ast_required(req_name); expected = 'REQUIRED_EXPECTED=' + _json.dumps(req).replace(' ', '').replace('"', "'"); assert len(req) == n_req and expected in c2 and f"t.id=='{req_name}'" in c2
    assert 'nonce' not in c2.lower().replace('the nonce is never entered here', '') and '--selftest' not in c2 and "'--profile','production_official'" in c2 and 'is NOT a condition' in c2 and 'is not a JSON object' in c2 and c2.index('if doc_ok and not isinstance(doc, dict)') < c2.index('if doc_ok and isinstance(doc, dict)')
    assert 'OUT_ROOT = None' in c0 and "([] if OUT_ROOT else ['/content/drive'])" in c1
    if nb == NB_CF: assert "'--mode','combine-family'" in c2 and "r.get('D4C1_SUBPARTIAL_PASS') is True" in c1 and 'tile rows 0..2000' in c1 and "('provenance', prov.get('schema')=='d4c1_subpartial_combiner_v1'" in c2 and "d4c1_partial_{FAM}_record.json" in c2 and "from_subpartials" in c3
    else: assert "'--mode','screen'" in c2 and "FAMILY in ('E2','E7','E8')" in c1 and "('schema', doc.get('schema')=='position_envelope_screen_v1')" in c2 and "'--d3b-root'" not in c2 and 'd4c1_screen_' in c3 and "('D4C1_PARTIAL_PASS', v.get('D4C1_PARTIAL_PASS') is False)" in c2


SUB_CASES = ['sub_ok', 'sub_pass_false', 'sub_schema_partial', 'sub_rows_mismatch', 'sub_partial_pass_only', 'sub_global_identity_mismatch', 'sub_drive_out_root']


@pytest.mark.parametrize('case', SUB_CASES)
def test_partial_notebook_subpartial_attempt_cell(tmp_path, case):
    """the v0.3 partial launcher with ROW_RANGE: the launch carries --row-range, the trusted inventory is REQUIRED_SUBPARTIAL (25), the published document must be a sub-partial record
    over the global columns, and only D4C1_SUBPARTIAL_PASS passes (D4C1_PARTIAL_PASS alone never does)."""
    lock_src, c2 = _lock_src(NB_P); commit = 'a' * 40; mt, pb, RA = _fake_source(tmp_path / 'scratch'); out = tmp_path / 'out'; out.mkdir(); d2, d3 = _roots(tmp_path); RR = (0, 500)
    ns = _ns(tmp_path, commit, mt, pb, RA, out, d2, d3, False, row_range=RR, out_root=('/content/drive/MyDrive/MirrorTopology_D4C2' if case == 'sub_drive_out_root' else None)); REQ = _ast_required('REQUIRED_SUBPARTIAL'); REQP = _ast_required('REQUIRED_PARTIAL')
    with contextlib.redirect_stdout(io.StringIO()): exec(compile(lock_src, 'nb_anchor', 'exec'), ns)
    lock = ns['lock']; assert lock['row_range'] == [0, 500] and lock['instrument'] is False and lock['probe_n'] is None and (lock['out_root'] is not None) == (case == 'sub_drive_out_root')
    if case == 'sub_drive_out_root': assert '/content/drive' not in ns['_protected_roots']() and d2 in ns['_protected_roots']()
    else: assert '/content/drive' in ns['_protected_roots']()
    calls = []
    def check_output(args, **kw): return (commit if 'rev-parse' in args else '') + '\n'
    def run(args, **kw):
        calls.append(list(args)); run_dir = args[args.index('--out') + 1]; att = args[args.index('--attempt-id') + 1]; lk = args[args.index('--launcher-lock-sha256') + 1]; os.makedirs(os.path.join(run_dir, 'archive')); open(os.path.join(run_dir, 'archive', 'index.json'), 'w').write('{}')
        tag = 'subpartial_E2_r0000_0500'; n_rows = 500; fps = {'E2': {}, **{f'E2/{s}': {} for s in SIZES}, **{f'twelve:E2/{s}': {} for s in SIZES}}
        sub_schema = case != 'sub_schema_partial'; rows = [0, 500] if case != 'sub_rows_mismatch' else [0, 400]
        doc = dict(schema=('family_subpartial_calibration_v1' if sub_schema else 'family_partial_calibration_v1'), kind=('family_subpartial_calibration' if sub_schema else 'family_partial_calibration'), engine_version=lock['engine'], mode='official', family='E2', w2_context_sha256='c' * 64,
                   thresholds=dict(target=None, target_commitment=lock['target_commitment'], pseudo=dict(n=2000, sha256_T1=('x' * 64 if case == 'sub_global_identity_mismatch' else 't' * 64), sha256_T2='u' * 64, rows=rows, T1=[0.0] * n_rows, T2=[0.0] * n_rows)), rows=dict(start=rows[0], stop=rows[1], n_total=2000, n_rows=rows[1] - rows[0]),
                   per_pseudo_status=[dict(family='E2')] * n_rows, fingerprints=dict(at_gate=fps, at_end=fps), gate=dict(mode='official', passed=True), binding=dict(partial_sha256='s' * 64, subpartial_dependencies={}), campaign=dict(id=lock['campaign_id']), plan_objects=dict(first_wave_shared=True, twelve_shared=True, twelve_present=True, twelve_shares_first_wave=True, stable_after=True))
        fn = f'd4c1_{tag}_record.json'; data = _json.dumps(doc).encode(); open(os.path.join(run_dir, fn), 'wb').write(data); pe = {fn: dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))}
        rec = dict(schema='d4c1_run_record_v1', mode='partial', family='E2', stage='complete', failures=[], selftest=False, formal=True, probe=False, probe_n=None, subpartial=True, row_range=[0, 500], instrument=False, profile='production_official', attempt=dict(attempt_id=att, launcher_lock_sha256=lk),
                   source=dict(script_sha256=lock['script_sha256'], inventory_sha256=lock['inventory_sha256'], pins_sha256=lock['pins_sha256'], engine_version=lock['engine']), target_commitment=lock['target_commitment'], campaign_id=lock['campaign_id'], gates={k: True for k in REQ}, required_inventory=list(REQ), required_all_true=True, seconds=1.5, stages_rss_mb=dict(final=1.0), stages_peak_rss_mb=dict(final=1.0), timings={},
                   partial=dict(partial_sha256='s' * 64, n_pseudo=n_rows, verification=dict(ok=True, registered_context_ok=True, rows=[0, 500]), eligibility_counts={}, expanded=0, twelve_evaluated=0, archive_entries=1), pseudo=dict(n=2000, identity=dict(T1_sha256='t' * 64, T2_sha256='u' * 64, paired_sha256='p' * 64)), w2_context=dict(context_sha256='c' * 64), published_evidence=pe,
                   D4C1_PARTIAL_PASS=(case == 'sub_partial_pass_only'), D4C1_SUBPARTIAL_PASS=(case not in ('sub_pass_false', 'sub_partial_pass_only')))
        open(os.path.join(run_dir, f'd4c1_{tag}_run.json'), 'w').write(_json.dumps(rec))
        class R: returncode = 0; stdout = 'TEST'; stderr = ''
        return R()
    ns['subprocess'] = type('SP', (), dict(check_output=staticmethod(check_output), run=staticmethod(run)))
    with contextlib.redirect_stdout(io.StringIO()): exec(compile(c2, 'nb_attempt', 'exec'), ns)
    fin = _json.load(open(out / 'd4c1_partial_final_record.json')); a = calls[0]
    assert fin['subpartial'] is True and fin['row_range'] == [0, 500] and a[a.index('--row-range') + 1] == '0:500' and '--probe-n' not in a and '--instrument' not in a and a.count('--d3b-root') == 3 and len(REQ) == 25 and len(REQP) == 24
    if case in ('sub_ok', 'sub_drive_out_root'): assert fin['partial_pass'] is True and fin['failures'] == [] and fin['D4C1_SUBPARTIAL_PASS'] is True and fin['D4C1_PARTIAL_PASS'] is False and fin['evidence_ok'] is True and fin['gates_ok'] is True and fin['bindings_ok'] is True
    else:
        assert fin['partial_pass'] is False, case
        if case == 'sub_pass_false': assert fin['failures'] == [] and fin['evidence_ok'] is True
        if case == 'sub_partial_pass_only': assert fin['failures'] == [] and fin['D4C1_PARTIAL_PASS'] is True and fin['D4C1_SUBPARTIAL_PASS'] is False          # a family-partial flag on a sub-partial launch never passes the sub-partial launcher
        if case in ('sub_schema_partial', 'sub_rows_mismatch', 'sub_global_identity_mismatch'): assert fin['evidence_ok'] is False and fin['gates_ok'] is True and fin['bindings_ok'] is True, fin['failures']
