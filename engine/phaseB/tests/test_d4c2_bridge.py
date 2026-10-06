# -*- coding: utf-8 -*-
"""D4C-2a environment bridge comparison script (d/d4c2_bridge_compare.py) against the audit's contract `D4C2a_v3_0.110.0_bridge_comparison_spec.json` (revised after audit
D4C2a_v4_0.111.0: R-D4BRIDGE-A / B / C, N-D4BRIDGE-ERROR-REPORT): on a SYNTHETIC "new" probe built from the registered baseline probe (attempt 20261005T100239Z_386d63207c; the
same 15 per-row records byte for byte; the partial re-bound to THIS tree's source binding and a gate environment equal to the current registered environment; a structurally
complete launcher lock / final record / profile document and run record of a new attempt) the contract is satisfied (rc 0); every tampering of a contract item — a per-row
record's bytes, a science field, the gate environment, a producer gate, the profile, an extra archive entry, AND the audit's counter-examples (a renamed gate in both inventories,
a reversed inventory, wrong source pins, an attempt id that is not the run directory, a wrong lock with a failure final record, a re-hashed profile with missing targets, a
JSON-false pseudo_index in the index, a failed / injected twelve gate, a null record) — is reported and stops (rc 1 with a report). No bank execution; the synthetic probe is
TEST-ONLY and is never a bridge result."""
import os, sys, json, hashlib, shutil, subprocess, zipfile, copy
import pytest
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); sys.path[:0] = [P, os.path.join(P, 'tests')]
from step1_engine import serialization as ser, __version__
from step1_engine.archive import Archive
from step1_engine.checkpoint import binding_manifest
from step1_engine.d4c1_partial import _payload_sha, _COMMON_BINDING
from step1_engine.official_gate import EXPECTED_VERS, EXPECTED_VERS_HISTORY, VERSION_KEYS
from step1_engine.profiling import TARGETS, SEGMENT_TARGET, PROFILE_SCHEMA
SCRIPT = os.path.join(P, 'd', 'd4c2_bridge_compare.py'); SPEC = os.path.join(P, 'registered_assets', 'd4c1', 'acceptance', 'd4c2a', 'D4C2a_v3_0.110.0_bridge_comparison_spec.json')
PROBE_DIR = os.path.join(P, 'registered_assets', 'd4c1', 'probes', '20261005T100239Z_386d63207c'); BASE_ZIP = os.path.join(PROBE_DIR, 'd4c1_partial_E2_231d37b89271.zip')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
COMMIT = 'f' * 40                                                                                                                                    # TEST-ONLY commit label of the synthetic probe


def _run(args):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1'); return subprocess.run([sys.executable, SCRIPT] + args, capture_output=True, text=True, env=env)


def _publish(path, doc):
    data = json.dumps(doc, indent=1, ensure_ascii=False, default=str).encode('utf-8'); open(path, 'wb').write(data); return hashlib.sha256(data).hexdigest()


def _profile(n_seg=3):
    """A structurally complete profile record exactly as Profiler.report emits it (synthetic times; the producer TARGETS inventory; segments 0..n-1; consistent accounting)."""
    per = []; tot = {k: dict(calls=0, inclusive_seconds=0.0, self_seconds=0.0) for k in TARGETS}
    for i in range(n_seg):
        tg = {k: dict(calls=(1 if k == SEGMENT_TARGET else 2), inclusive_seconds=0.5 + 0.01 * i, self_seconds=0.1 + 0.01 * i) for k in TARGETS}
        per.append(dict(index=i, wall_seconds=10.0 + i, targets=tg))
        for k, v in tg.items():
            for f in tot[k]: tot[k][f] += v[f]
    seg_wall = sum(s['wall_seconds'] for s in per); total = seg_wall + 7.25
    targets = {k: dict(calls=tot[k]['calls'] + (0 if k == SEGMENT_TARGET else 1), inclusive_seconds=tot[k]['inclusive_seconds'] + 0.25, self_seconds=tot[k]['self_seconds'] + 0.05, outside_segments=dict(calls=(0 if k == SEGMENT_TARGET else 1), inclusive_seconds=0.25, self_seconds=0.05)) for k in TARGETS}
    cp = dict(by_cumtime=[dict(function='f', file='x.py', line=1, ncalls=3, primitive_calls=3, tottime=0.1, cumtime=1.0)], by_tottime=[dict(function='f', file='x.py', line=1, ncalls=3, primitive_calls=3, tottime=0.1, cumtime=1.0)], n_functions=1)
    return dict(schema=PROFILE_SCHEMA, engine_version=__version__, instrumentation=dict(wrappers=True, cprofile=True, clock='time.perf_counter (wall)', segment_target=SEGMENT_TARGET, note='TEST-ONLY', accounting='TEST-ONLY'), python=EXPECTED_VERS['python'],
                wall_seconds_total=total, segments=dict(count=n_seg, wall_seconds=seg_wall, per_segment=per, mean_wall_seconds=seg_wall / n_seg), outside_segments_wall_seconds=total - seg_wall, outside_segments_note='TEST-ONLY', targets=targets, missing_targets=[], cprofile=cp, note='TEST-ONLY synthetic profile record (no measurement)')


@pytest.fixture(scope='module')
def probes(tmp_path_factory):
    root = tmp_path_factory.mktemp('bridge'); spec = json.load(open(SPEC)); fmap = json.load(open(os.path.join(PROBE_DIR, 'file_map.json')))
    assert sha(BASE_ZIP) == spec['baseline_zip_sha256'] == fmap['files']['d4c1_partial_E2_231d37b89271.zip']['sha256']                                     # the registered baseline, byte-preserved
    base = root / 'baseline'; base.mkdir()
    with zipfile.ZipFile(BASE_ZIP) as z: z.extractall(str(base))
    brun = str(base / 'run_20261005T100239Z_386d63207c'); rec = ser.loads(open(os.path.join(brun, 'd4c1_probe_E2_record.json'), encoding='utf-8').read()); run = json.load(open(os.path.join(brun, 'd4c1_probe_E2_run.json')))
    blck = json.load(open(str(base / 'd4c1_partial_lock.json'))); bfin = json.load(open(str(base / 'd4c1_partial_final_record.json')))
    assert rec['binding']['partial_sha256'] == spec['baseline_partial_payload'] and rec['engine_version'] == '0.107.0' and rec['gate']['diagnostics']['env']['python'] == '3.13.15' and blck['schema'] == 'd4c1_partial_launcher_lock_v1' and bfin['schema'] == 'd4c1_partial_launcher_final_record_v1'
    # ---- synthetic NEW probe: same science, this tree's source binding, the current registered gate environment, a new attempt with a complete launcher lock / final record / profile
    att = 'TEST_ONLY_20261006T000000Z_deadbeef00'; new = root / 'new'; nrun = new / f'run_{att}'; nrun.mkdir(parents=True)
    old_ar = Archive(brun + '/archive'); new_ar = Archive(str(nrun / 'archive'))
    for e in old_ar._entries():
        if e['kind'] == 'transition' and e['identity'].get('kind') == 'family_partial_calibration': continue
        new_ar.put(e['kind'], ser.loads(old_ar.entry_bytes(e).decode('utf-8')), e['identity'])
    d = ser.from_jsonable(ser.to_jsonable(rec)); bm = binding_manifest()
    d['engine_version'] = __version__; d['binding'].update({k: bm[k] for k in _COMMON_BINDING}); d['binding']['partial_dependencies']['engine_version'] = __version__; d['binding']['partial_dependencies']['source_binding'] = {k: bm[k] for k in _COMMON_BINDING}
    d['gate']['diagnostics']['env'].update({k: EXPECTED_VERS[k] for k in VERSION_KEYS})
    for k in ('partial_sha256', 'partial_file_sha256', 'partial_ref'): d['binding'].pop(k, None)
    d['binding']['partial_sha256'] = _payload_sha(d)
    ref = new_ar.put('transition', d, dict(kind='family_partial_calibration', family='E2', payload_sha256=d['binding']['partial_sha256'], target_commitment=d['thresholds']['target_commitment']))
    d['binding']['partial_file_sha256'] = ref.sha256; d['binding']['partial_ref'] = ref.as_dict()
    rp = str(nrun / 'd4c1_probe_E2_record.json'); open(rp, 'w', encoding='utf-8').write(ser.dumps(d))
    pf = str(nrun / 'd4c1_probe_E2_profile.json'); prof = _profile(); _publish(pf, prof)
    inv_path = os.path.join(P, 'B2_completion_inventory.json'); inv = json.load(open(inv_path)); tree = dict(inventory_sha256=sha(inv_path), script_sha256=inv['d_sha256']['d/d4c1_calibration.py'], pins_sha256=inv['d_sha256']['d/d3_pins.json'])
    ra = {k: inv['registered_assets_sha256'][k] for k in blck['registered_assets_sha256']}
    lock = dict(blck, commit=COMMIT, inventory_sha256=tree['inventory_sha256'], script_sha256=tree['script_sha256'], inventory_script_sha256=tree['script_sha256'], pins_sha256=tree['pins_sha256'], registered_assets_sha256=ra, engine=__version__, probe_n=3, row_range=None, instrument=True, out_root=None, locked_utc='2026-10-06T00:00:00Z')
    lock_sha = _publish(str(new / 'd4c1_partial_lock.json'), lock)
    r = copy.deepcopy(run); r.update(instrument=True, subpartial=False, row_range=None, D4C1_SUBPARTIAL_PASS=False, engine_version=__version__, attempt=dict(attempt_id=att, launcher_lock_sha256=lock_sha), published_evidence={'d4c1_probe_E2_record.json': dict(sha256=sha(rp), bytes=os.path.getsize(rp))},
             profile_summary=dict(wall_seconds_total=prof['wall_seconds_total'], segments=prof['segments']['count'], segment_wall_seconds=prof['segments']['wall_seconds'], outside_segments_wall_seconds=prof['outside_segments_wall_seconds'], missing_targets=prof['missing_targets']), profile_record=dict(sha256=sha(pf), bytes=os.path.getsize(pf)), pins_sha256=tree['pins_sha256'])
    r['source'] = dict(r['source'], inventory_sha256=tree['inventory_sha256'], script_sha256=tree['script_sha256'], pins_sha256=tree['pins_sha256'], engine_version=__version__)
    r['env'] = dict(r['env'], **{k: EXPECTED_VERS[k] for k in VERSION_KEYS}); r['env_gate'] = dict(r['env_gate'], expected=dict(r['env_gate']['expected'], **{k: EXPECTED_VERS[k] for k in VERSION_KEYS}))
    r['partial'] = dict(r['partial'], partial_sha256=d['binding']['partial_sha256'], partial_file_sha256=ref.sha256, partial_ref=ref.as_dict())
    runp = str(nrun / 'd4c1_probe_E2_run.json'); open(runp, 'w').write(json.dumps(r))
    live = dict(head=COMMIT, clean=True, inventory_sha256=tree['inventory_sha256'], script_sha256=tree['script_sha256'], inventory_script_sha256=tree['script_sha256'], pins_sha256=tree['pins_sha256'], registered_assets_sha256=ra, engine=__version__, checked_utc='2026-10-06T00:00:00Z')
    fin = dict(bfin, attempt_id=att, started_utc='2026-10-06T00:00:00Z', lock_sha256=lock_sha, lock=lock, output_anchor='/content/d4c1_partial_E2', probe=True, subpartial=False, row_range=None, instrument=True, run_dir=f'/content/d4c1_partial_E2/run_{att}', bindings=dict(live_source_precheck=live, live_source_prelaunch=live),
               record_sha256=sha(runp), gates=r['gates'], partial_summary=dict(bfin['partial_summary'], partial_sha256=d['binding']['partial_sha256']), finished_utc='2026-10-06T01:00:00Z')
    _publish(str(new / 'd4c1_partial_final_record.json'), fin)
    # the contract names the fixed source of the REAL bridge probe (engine 0.110.0); the synthetic probe is bound to THIS tree, so the test's copy of the spec names this engine (nothing else changes)
    tspec = str(root / 'spec_for_this_tree.json'); json.dump(dict(spec, new_engine=__version__, test_only_note='copy of the audit spec with new_engine = the engine of this tree (synthetic bridge test)'), open(tspec, 'w'), indent=1)
    return dict(root=str(root), base=str(base), new=str(new), nrun=str(nrun), rec=d, run=r, spec=spec, tspec=tspec, lock=lock, fin=fin)


def _report(out): return json.load(open(out))


def _args(probes, new, out, spec=None, commit=COMMIT): return ['--phaseb', P, '--spec', spec or probes['tspec'], '--baseline', BASE_ZIP, '--new', new, '--out', out] + (['--expected-commit', commit] if commit else [])


def test_bridge_contract_satisfied_on_the_synthetic_new_probe(probes, tmp_path):
    out = str(tmp_path / 'ok.json'); r = _run(_args(probes, probes['new'], out))
    rep = _report(out); assert r.returncode == 0 and rep['result'] == 'BRIDGE_CONTRACT_SATISFIED' and rep['mismatches'] == [] and rep['n_failed'] == 0 and rep['schema'] == 'd4c2_bridge_comparison_report_v2', (r.stdout, r.stderr, rep.get('mismatches'), {k: v for k, v in rep['checks'].items() if not v['ok']})
    c = rep['checks']; assert all(c[k]['ok'] for k in ('baseline_zip_sha256', 'per_row_records_exact_in_both_probes', 'required_equal_partial_fields', 'new_record_own_reader_current_source_binding', 'new_env_is_registered_current', 'baseline_env_is_registered_history', 'new_run_trusted_inventory', 'new_lock_binds_this_tree', 'new_final_record_complete', 'new_final_live_source_precheck_prelaunch', 'new_profile_document', 'new_run_twelve_gate_live', 'new_run_attempt_is_directory'))
    assert c['new_run_trusted_inventory']['detail']['required_inventory_equals_producer_constant'] and c['new_lock_binds_this_tree']['detail']['commit'] == COMMIT and c['new_profile_document']['detail']['summary_equals_document']
    assert rep['partial_provenance_differences']['payload'][0] != rep['partial_provenance_differences']['payload'][1] and rep['partial_provenance_differences']['gate_env_python'] == ['3.13.15', EXPECTED_VERS['python']] and rep['new_partial_payload'] != probes['spec']['baseline_partial_payload']
    assert sorted(rep['per_row']) == ['0', '1', '2'] and all(all(v['ok'] for v in rep['per_row'][r_][tag].values()) for r_ in rep['per_row'] for tag in ('baseline', 'new')) and 'approves no screen' in rep['scope']
    assert sha(BASE_ZIP) == probes['spec']['baseline_zip_sha256'] and rep['checks']['originals_untouched']['ok']
    # without --expected-commit the lock commit is recorded (and must still equal the live pre-check / pre-launch heads)
    o2 = str(tmp_path / 'nocommit.json'); assert _run(_args(probes, probes['new'], o2, commit=None)).returncode == 0 and _report(o2)['expected_commit'] is None
    o3 = str(tmp_path / 'othercommit.json'); r3 = _run(_args(probes, probes['new'], o3, commit='0' * 40)); assert r3.returncode == 1 and _report(o3)['mismatches'] == ['new_lock_binds_this_tree']
    # usage refusals
    assert _run(_args(probes, probes['new'], out)).returncode == 2                                                                                                      # report exists
    assert _run(_args(probes, str(tmp_path / 'nowhere'), str(tmp_path / 'x.json'))).returncode == 2
    assert _run(_args(probes, probes['new'], str(tmp_path / 'y.json'), commit='nothex')).returncode == 2
    r4 = _run(_args(probes, probes['new'], str(tmp_path / 'spec_engine.json'), spec=SPEC)); rep4 = _report(str(tmp_path / 'spec_engine.json'))
    assert r4.returncode == 1 and rep4['mismatches'] == ['tree_self_consistent'] and rep4['checks']['per_row_records_exact_in_both_probes']['ok'], rep4['mismatches']                  # the audit's spec pins engine 0.110.0: this tree is not that fixed source
    r2 = _run(_args(probes, BASE_ZIP, str(tmp_path / 'same.json'), commit=None)); rep2 = _report(str(tmp_path / 'same.json'))
    assert r2.returncode == 1 and 'distinct_attempts' in rep2['mismatches'] and 'new_env_is_registered_current' in rep2['mismatches'] and 'new_run_source_is_this_tree' in rep2['mismatches']        # the baseline itself is not a bridge probe


CASES = {
    # audit D4C2a_v4 counter-examples (R-D4BRIDGE-A / B / C, N-D4BRIDGE-ERROR-REPORT)
    'required_gate_renamed': ['new_run_trusted_inventory'], 'required_order_reversed': ['new_run_trusted_inventory'], 'source_pins_wrong': ['new_run_source_is_this_tree'], 'attempt_does_not_match_directory': ['new_run_attempt_is_directory'],
    'bad_lock_and_failure_final': ['new_lock_binds_this_tree', 'new_final_record_complete', 'new_final_live_source_precheck_prelaunch'], 'profile_rehashed_missing_targets': ['new_profile_document'], 'typed_index_bool': ['per_row_records_exact_in_both_probes'],
    'twelve_gate_injected_top_level': ['new_run_twelve_gate_live'], 'twelve_gate_failed': ['new_run_twelve_gate_live'], 'malformed_record_null': ['documents_are_objects'],
    # own cases
    'row_record_bytes': ['per_row_records_exact_in_both_probes', 'archives_verify'], 'science_field': ['required_equal_partial_fields'], 'gate_env_old': ['new_env_is_registered_current'], 'producer_gate_false': ['new_run_trusted_inventory'],
    'profile_missing': ['new_profile_document'], 'profile_summary_disagrees': ['new_profile_document'], 'profile_segment_count': ['new_profile_document'], 'profile_target_dropped': ['new_profile_document'], 'extra_archive_entry': ['archive_entry_counts', 'new_other_entries_registry_and_one_partial'],
    'lock_missing': ['unexpected_error'], 'final_precheck_dirty': ['new_final_live_source_precheck_prelaunch'], 'lock_registered_asset_sha': ['new_lock_binds_this_tree'], 'index_identity_float': ['per_row_records_exact_in_both_probes'], 'parent_ref_identity_float': ['per_row_records_exact_in_both_probes'],
}


@pytest.mark.parametrize('case', sorted(CASES))
def test_bridge_mismatches_are_reported_and_stop(probes, tmp_path, case):
    new = str(tmp_path / 'new'); shutil.copytree(probes['new'], new); nrun = os.path.join(new, os.path.basename(probes['nrun'])); rp = os.path.join(nrun, 'd4c1_probe_E2_record.json'); runp = os.path.join(nrun, 'd4c1_probe_E2_run.json'); pf = os.path.join(nrun, 'd4c1_probe_E2_profile.json')
    lockp = os.path.join(new, 'd4c1_partial_lock.json'); finp = os.path.join(new, 'd4c1_partial_final_record.json'); idxp = os.path.join(nrun, 'archive', 'index.json')
    def edit_run(fn):
        r = json.load(open(runp)); fn(r); open(runp, 'w').write(json.dumps(r))
    def edit_rec(fn):
        d = ser.loads(open(rp, encoding='utf-8').read()); fn(d); open(rp, 'w', encoding='utf-8').write(ser.dumps(d))
    def edit_idx(fn):
        d = json.load(open(idxp)); fn(d); open(idxp, 'w').write(json.dumps(d))
    def rehash_profile(fn):
        d = json.load(open(pf)); fn(d); _publish(pf, d); edit_run(lambda r: r.update(profile_record=dict(sha256=sha(pf), bytes=os.path.getsize(pf))))
    if case == 'required_gate_renamed': edit_run(lambda r: (r['required_inventory'].__setitem__(r['required_inventory'].index('G_inputs_resolved'), 'TEST_FAKE_GATE'), r['gates'].update(TEST_FAKE_GATE=r['gates'].pop('G_inputs_resolved'))))
    elif case == 'required_order_reversed': edit_run(lambda r: r['required_inventory'].reverse())
    elif case == 'source_pins_wrong': edit_run(lambda r: r['source'].update(pins_sha256='0' * 64))
    elif case == 'attempt_does_not_match_directory': edit_run(lambda r: r['attempt'].update(attempt_id='DIFFERENT_ATTEMPT'))
    elif case == 'bad_lock_and_failure_final':
        open(lockp, 'w').write(json.dumps(dict(commit='WRONG_COMMIT', inventory_sha256='0' * 64))); open(finp, 'w').write(json.dumps(dict(exit_code=1, launcher_fallback=True, failures=['TEST_FAILURE'], bindings=dict(live_source_prelaunch=dict(head='WRONG_COMMIT', clean=False)))))
    elif case == 'profile_rehashed_missing_targets': rehash_profile(lambda d: (d.update(missing_targets=['TEST_MISSING_TARGET']), d.update(instrumentation={'cprofile': False})))
    elif case == 'typed_index_bool': edit_idx(lambda d: [e['identity'].update(pseudo_index=False) for e in d['entries'] if e['kind'] == 'family_result' and e['identity'].get('pseudo_index') == 0])
    elif case == 'twelve_gate_injected_top_level': edit_run(lambda r: r.update(twelve_gate=dict(mode='official', passed=False, required_failures=['TEST_REQUIRED_FAILURE'], diagnostics=dict(environment_source='injected_test_snapshot'))))
    elif case == 'twelve_gate_failed': edit_run(lambda r: r['twelve']['gate'].update(passed=False, required_failures=['TEST_REQUIRED_FAILURE']))
    elif case == 'malformed_record_null': open(rp, 'w').write('null')
    elif case == 'row_record_bytes':
        e = probes['spec']['required_exact_per_row_records'][1]; fp = os.path.join(nrun, 'archive', 'three_position_result', e['sha256'] + '.json'); b = open(fp, 'rb').read(); open(fp, 'wb').write(b.replace(b'"family": "E2"', b'"family": "E2 "', 1))
    elif case == 'science_field': edit_rec(lambda d: d['per_pseudo_status'][0]['eligible_truths'].update(support=True))
    elif case == 'gate_env_old': edit_rec(lambda d: d['gate']['diagnostics']['env'].update(python=EXPECTED_VERS_HISTORY[0]['python']))
    elif case == 'producer_gate_false': edit_run(lambda r: r['gates'].update(G_env_lock=False))
    elif case == 'profile_missing': os.remove(pf)
    elif case == 'profile_summary_disagrees': edit_run(lambda r: r['profile_summary'].update(segments=2))
    elif case == 'profile_segment_count': rehash_profile(lambda d: (d['segments']['per_segment'].pop(), d['segments'].update(count=2, wall_seconds=sum(s['wall_seconds'] for s in d['segments']['per_segment']))))
    elif case == 'profile_target_dropped': rehash_profile(lambda d: d['targets'].pop(sorted(d['targets'])[0]))
    elif case == 'extra_archive_entry': Archive(os.path.join(nrun, 'archive')).put('transition', dict(kind='pseudo_family_plan', family='E2', pseudo_index=3, note='TEST-ONLY extra'), dict(kind='pseudo_family_plan', family='E2', pseudo_index=3))
    elif case == 'lock_missing': os.remove(lockp)
    elif case == 'final_precheck_dirty':
        f = json.load(open(finp)); f['bindings']['live_source_precheck']['clean'] = False; open(finp, 'w').write(json.dumps(f))
    elif case == 'lock_registered_asset_sha':
        l = json.load(open(lockp)); k = sorted(l['registered_assets_sha256'])[0]; l['registered_assets_sha256'][k] = '0' * 64; open(lockp, 'w').write(json.dumps(l))
        edit_run(lambda r: r['attempt'].update(launcher_lock_sha256=sha(lockp))); f = json.load(open(finp)); f['lock_sha256'] = sha(lockp); f['lock'] = l; open(finp, 'w').write(json.dumps(f))
    elif case == 'index_identity_float': edit_idx(lambda d: [e['identity'].update(pseudo_index=1.0) for e in d['entries'] if e['kind'] == 'transition' and e['identity'].get('pseudo_index') == 1])        # 1.0 == 1 in Python; the typed identity refuses it
    elif case == 'parent_ref_identity_float': edit_rec(lambda d: d['per_pseudo_status'][2]['parent_ref']['identity'].update(pseudo_index=2.0))
    out = str(tmp_path / 'rep.json'); r = _run(_args(probes, new, out)); rep = _report(out)
    assert r.returncode == 1 and rep['result'] == 'MISMATCH_OR_REFUSAL__STOP_FOR_ANALYSIS' and all(x in rep['mismatches'] for x in CASES[case]), (case, rep['mismatches'], {k: v for k, v in rep['checks'].items() if not v['ok']})
    if case not in ('malformed_record_null', 'lock_missing'): assert rep['checks']['baseline_env_is_registered_history']['ok'] and rep['checks']['baseline_partial_payload']['ok']
    if case == 'science_field': assert 'new_record_own_reader_current_source_binding' in rep['mismatches']
    if case == 'typed_index_bool': assert rep['per_row']['0']['new'].get('error', '').startswith('row 0')
