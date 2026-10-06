# -*- coding: utf-8 -*-
"""D4C-2a environment bridge comparison script (d/d4c2_bridge_compare.py) against the audit's contract `D4C2a_v3_0.110.0_bridge_comparison_spec.json`: on a SYNTHETIC "new" probe built from
the registered baseline probe (attempt 20261005T100239Z_386d63207c; same 15 per-row records byte for byte; the partial re-bound to THIS tree's source binding and a gate environment
equal to the current registered environment; a new attempt id / run record / profile record) the contract is satisfied (rc 0); every tampering of a contract item (a per-row record's
bytes, a science field of the partial, the gate environment, a producer gate, the profile) is reported and stops (rc 1). No bank execution; the synthetic probe is TEST-ONLY and is
never a bridge result."""
import os, sys, json, hashlib, shutil, subprocess, zipfile, copy
import pytest
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); sys.path[:0] = [P, os.path.join(P, 'tests')]
from step1_engine import serialization as ser, __version__
from step1_engine.archive import Archive
from step1_engine.checkpoint import binding_manifest
from step1_engine.d4c1_partial import _payload_sha, _COMMON_BINDING
from step1_engine.official_gate import EXPECTED_VERS, EXPECTED_VERS_HISTORY, VERSION_KEYS
SCRIPT = os.path.join(P, 'd', 'd4c2_bridge_compare.py'); SPEC = os.path.join(P, 'registered_assets', 'd4c1', 'acceptance', 'd4c2a', 'D4C2a_v3_0.110.0_bridge_comparison_spec.json')
PROBE_DIR = os.path.join(P, 'registered_assets', 'd4c1', 'probes', '20261005T100239Z_386d63207c'); BASE_ZIP = os.path.join(PROBE_DIR, 'd4c1_partial_E2_231d37b89271.zip')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()


def _run(args):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1'); return subprocess.run([sys.executable, SCRIPT] + args, capture_output=True, text=True, env=env)


@pytest.fixture(scope='module')
def probes(tmp_path_factory):
    root = tmp_path_factory.mktemp('bridge'); spec = json.load(open(SPEC)); fmap = json.load(open(os.path.join(PROBE_DIR, 'file_map.json')))
    assert sha(BASE_ZIP) == spec['baseline_zip_sha256'] == fmap['files']['d4c1_partial_E2_231d37b89271.zip']['sha256']                                     # the registered baseline, byte-preserved
    base = root / 'baseline'; base.mkdir()
    with zipfile.ZipFile(BASE_ZIP) as z: z.extractall(str(base))
    brun = str(base / 'run_20261005T100239Z_386d63207c'); rec = ser.loads(open(os.path.join(brun, 'd4c1_probe_E2_record.json'), encoding='utf-8').read()); run = json.load(open(os.path.join(brun, 'd4c1_probe_E2_run.json')))
    assert rec['binding']['partial_sha256'] == spec['baseline_partial_payload'] and rec['engine_version'] == '0.107.0' and rec['gate']['diagnostics']['env']['python'] == '3.13.15'
    # ---- synthetic NEW probe: same science, this tree's source binding, the current registered gate environment, a new attempt
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
    pf = str(nrun / 'd4c1_probe_E2_profile.json'); prof = dict(schema='d4c1_profile_record_v1', instrumentation=dict(cprofile=True), segments=dict(count=3), targets={}, cprofile=dict(by_tottime=[]), scope='TEST-ONLY synthetic profile record'); open(pf, 'w').write(json.dumps(prof))
    inv_path = os.path.join(P, 'B2_completion_inventory.json'); inv = json.load(open(inv_path))
    r = copy.deepcopy(run); r.update(instrument=True, subpartial=False, row_range=None, D4C1_SUBPARTIAL_PASS=False, engine_version=__version__, attempt=dict(attempt_id=att, launcher_lock_sha256='f' * 64), published_evidence={'d4c1_probe_E2_record.json': dict(sha256=sha(rp), bytes=os.path.getsize(rp))},
                                profile_summary=dict(segments=3, missing_targets=[]), profile_record=dict(sha256=sha(pf), bytes=os.path.getsize(pf)), pins_sha256=inv['d_sha256']['d/d3_pins.json'])
    r['source'] = dict(r['source'], inventory_sha256=sha(inv_path), script_sha256=inv['d_sha256']['d/d4c1_calibration.py'], pins_sha256=inv['d_sha256']['d/d3_pins.json'], engine_version=__version__)
    r['env'] = dict(r['env'], **{k: EXPECTED_VERS[k] for k in VERSION_KEYS}); r['env_gate'] = dict(r['env_gate'], expected=dict(r['env_gate']['expected'], **{k: EXPECTED_VERS[k] for k in VERSION_KEYS}))
    r['partial'] = dict(r['partial'], partial_sha256=d['binding']['partial_sha256'], partial_file_sha256=ref.sha256, partial_ref=ref.as_dict())
    open(str(nrun / 'd4c1_probe_E2_run.json'), 'w').write(json.dumps(r))
    # the contract names the fixed source of the REAL bridge probe (engine 0.110.0); the synthetic probe is bound to THIS tree, so the test's copy of the spec names this engine (nothing else changes)
    tspec = str(root / 'spec_for_this_tree.json'); json.dump(dict(spec, new_engine=__version__, test_only_note='copy of the audit spec with new_engine = the engine of this tree (synthetic bridge test)'), open(tspec, 'w'), indent=1)
    return dict(root=str(root), base=str(base), new=str(new), nrun=str(nrun), rec=d, run=r, spec=spec, tspec=tspec)


def _report(out): return json.load(open(out))


def test_bridge_contract_satisfied_on_the_synthetic_new_probe(probes, tmp_path):
    out = str(tmp_path / 'ok.json'); r = _run(['--phaseb', P, '--spec', probes['tspec'], '--baseline', BASE_ZIP, '--new', probes['new'], '--out', out])
    rep = _report(out); assert r.returncode == 0 and rep['result'] == 'BRIDGE_CONTRACT_SATISFIED' and rep['mismatches'] == [] and rep['n_failed'] == 0, (r.stdout, r.stderr, rep.get('mismatches'), {k: v for k, v in rep['checks'].items() if not v['ok']})
    c = rep['checks']; assert c['baseline_zip_sha256']['ok'] and c['per_row_records_exact_in_both_probes']['ok'] and c['required_equal_partial_fields']['ok'] and c['new_record_own_reader_current_source_binding']['ok'] and c['new_env_is_registered_current']['ok'] and c['baseline_env_is_registered_history']['ok']
    assert rep['partial_provenance_differences']['payload'][0] != rep['partial_provenance_differences']['payload'][1] and rep['partial_provenance_differences']['gate_env_python'] == ['3.13.15', EXPECTED_VERS['python']] and rep['new_partial_payload'] != probes['spec']['baseline_partial_payload']
    assert sorted(rep['per_row']) == ['0', '1', '2'] and all(all(v['ok'] for v in rep['per_row'][r_][tag].values()) for r_ in rep['per_row'] for tag in ('baseline', 'new')) and 'approves no screen' in rep['scope']
    assert sha(BASE_ZIP) == probes['spec']['baseline_zip_sha256'] and rep['checks']['originals_untouched']['ok']
    # usage refusals
    assert _run(['--phaseb', P, '--spec', probes['tspec'], '--baseline', BASE_ZIP, '--new', probes['new'], '--out', out]).returncode == 2                                           # report exists
    assert _run(['--phaseb', P, '--spec', probes['tspec'], '--baseline', BASE_ZIP, '--new', str(tmp_path / 'nowhere'), '--out', str(tmp_path / 'x.json')]).returncode == 2
    r3 = _run(['--phaseb', P, '--spec', SPEC, '--baseline', BASE_ZIP, '--new', probes['new'], '--out', str(tmp_path / 'spec_engine.json')]); rep3 = _report(str(tmp_path / 'spec_engine.json'))
    assert r3.returncode == 1 and rep3['mismatches'] == ['new_source_is_this_tree'] and rep3['checks']['per_row_records_exact_in_both_probes']['ok'], rep3['mismatches']                      # the audit's spec pins engine 0.110.0: this tree is not that fixed source
    r2 = _run(['--phaseb', P, '--spec', probes['tspec'], '--baseline', BASE_ZIP, '--new', BASE_ZIP, '--out', str(tmp_path / 'same.json')]); rep2 = _report(str(tmp_path / 'same.json'))
    assert r2.returncode == 1 and 'distinct_attempts' in rep2['mismatches'] and 'new_env_is_registered_current' in rep2['mismatches'] and 'new_source_is_this_tree' in rep2['mismatches']          # the baseline itself is not a bridge probe


@pytest.mark.parametrize('case', ['row_record_bytes', 'science_field', 'gate_env_old', 'producer_gate_false', 'profile_missing', 'extra_archive_entry'])
def test_bridge_mismatches_are_reported_and_stop(probes, tmp_path, case):
    new = str(tmp_path / 'new'); shutil.copytree(probes['new'], new); nrun = os.path.join(new, os.path.basename(probes['nrun'])); rp = os.path.join(nrun, 'd4c1_probe_E2_record.json'); runp = os.path.join(nrun, 'd4c1_probe_E2_run.json')
    expect = {'row_record_bytes': ['per_row_records_exact_in_both_probes', 'archives_verify'], 'science_field': ['required_equal_partial_fields'], 'gate_env_old': ['new_env_is_registered_current'], 'producer_gate_false': ['new_run_gates_all_true'], 'profile_missing': ['new_profile_record'], 'extra_archive_entry': ['archive_entry_counts', 'new_other_entries_registry_and_one_partial']}[case]
    if case == 'row_record_bytes':
        e = probes['spec']['required_exact_per_row_records'][1]; fp = os.path.join(nrun, 'archive', 'three_position_result', e['sha256'] + '.json'); b = open(fp, 'rb').read(); open(fp, 'wb').write(b.replace(b'"family": "E2"', b'"family": "E2 "', 1))
    elif case == 'science_field':
        d = ser.loads(open(rp, encoding='utf-8').read()); d['per_pseudo_status'][0]['eligible_truths']['support'] = True; open(rp, 'w', encoding='utf-8').write(ser.dumps(d))
    elif case == 'gate_env_old':
        d = ser.loads(open(rp, encoding='utf-8').read()); d['gate']['diagnostics']['env']['python'] = EXPECTED_VERS_HISTORY[0]['python']; open(rp, 'w', encoding='utf-8').write(ser.dumps(d))
    elif case == 'producer_gate_false':
        r = json.load(open(runp)); r['gates']['G_env_lock'] = False; open(runp, 'w').write(json.dumps(r))
    elif case == 'profile_missing': os.remove(os.path.join(nrun, 'd4c1_probe_E2_profile.json'))
    elif case == 'extra_archive_entry': Archive(os.path.join(nrun, 'archive')).put('transition', dict(kind='pseudo_family_plan', family='E2', pseudo_index=3, note='TEST-ONLY extra'), dict(kind='pseudo_family_plan', family='E2', pseudo_index=3))
    out = str(tmp_path / 'rep.json'); r = _run(['--phaseb', P, '--spec', probes['tspec'], '--baseline', BASE_ZIP, '--new', new, '--out', out]); rep = _report(out)
    assert r.returncode == 1 and rep['result'] == 'MISMATCH_OR_REFUSAL__STOP_FOR_ANALYSIS' and all(x in rep['mismatches'] for x in expect), (case, rep['mismatches'])
    assert rep['checks']['baseline_env_is_registered_history']['ok'] and rep['checks']['baseline_partial_payload']['ok']
