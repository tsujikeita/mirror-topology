# -*- coding: utf-8 -*-
"""D4C-2b registration contracts (step1_engine.d4c2_registry + registered_assets/d4c2 + registered_assets/d4c1/probes/20261006T115712Z_69ece7cef3). The three accepted COMPLETE
count-envelope screens (E2 / E7 / E8, all 2000 registered rows; commit ba51e595 / engine 0.112.0 / Python 3.13.16) and the authenticated fixed-campaign infeasibility certificate
consumed from them, plus the accepted environment bridge probe (commit 39082b64 / 0.110.0), are registered as ORIGINAL bytes (inner launcher archives' members == registered files;
executed notebooks; the result packet / report / file map / author bundle; the certificate consumer outputs and command; acceptance / decision documents; the historical 0.112.0
inventory) and bound deterministically: ledger == re-derivation == committed file == pins; receipt == re-derivation == pins; the module constants equal the acceptance documents
and the 0.112.0 driver's trusted REQUIRED inventories; every record is bound to ITS OWN historical execution epoch (never re-labelled to the registration version). Consumer: the
registered certificate view (usable == True impossible at support / strong for the fixed campaign) never becomes a sealed calibration or a partial. Refusals (audit §6.8):
every registration pin wrong / missing / null; the BYTE layer (any registered original edited: screen / run / final / lock / notebook / archive / certificate / command / rc /
stderr / acceptance / results packet / bridge originals; missing or extra members); and the SEMANTIC layer with the byte layer deliberately bypassed (a gate missing from the
trusted inventory, an old-version source mixed in, family / attempt mixing, N4 removed, a W2 summary edited with its checksum kept, row thresholds / paired columns changed, the
denominator counted as 6000 or a screen duplicated, swapped thresholds, a certificate promoted to a sealed calibration / partial, a non-registered environment, a failed live environment gate,
a probe / self-test / instrumented run, a subset of rows)."""
import os, sys, json, copy, shutil, hashlib, ast
import pytest
sys.path[:0] = [os.path.join(os.path.dirname(__file__), '..'), os.path.dirname(__file__)]
from step1_engine import d4c2_registry as rg
from step1_engine import serialization as ser, __version__
from step1_engine.d3_profile import twelve_context
from step1_engine.checkpoint import MODULES
from step1_engine.errors import InputContractError
from step1_engine.archive import Archive
from step1_engine.calibration_first import load_sealed_record
from step1_engine.d4c1_partial import load_partial_record, load_combined_sealed_record, _check_partial_shape
from step1_engine.d4c1_subpartial import load_subpartial_record, check_subpartial_shape
from test_d4c0_registration import _edit
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); CTX = twelve_context(P); PINS = json.load(open(os.path.join(P, 'd', 'd3_pins.json'))); R = os.path.join(P, 'registered_assets', 'd4c2')
LEDGER = json.load(open(os.path.join(R, 'd4c2_ledger.json'))); RECEIPT = json.load(open(os.path.join(R, 'd4c2_outer_receipt.json')))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
SCR = {F: f"registered_assets/d4c2/{rg.SCREENS[F]['registered_dir']}" for F in rg.FAMILIES}; ATT = {F: rg.SCREENS[F]['attempt'] for F in rg.FAMILIES}
CERT_DIR = 'registered_assets/d4c2/certificate'; CERT_OUT = f"registered_assets/d4c2/{rg.CERTIFICATE['out_dir']}"; BR = f"registered_assets/{rg.BRIDGE['registered_dir']}"


@pytest.fixture(scope='module')
def root(tmp_path_factory):
    """A copy of the tree parts the registration reads (pins / d / registered assets / tests assets); tests edit it and restore through _edit."""
    r = tmp_path_factory.mktemp('reg') / 'phaseB'; (r / 'registered_assets').mkdir(parents=True); shutil.copytree(os.path.join(P, 'd'), r / 'd'); shutil.copytree(os.path.join(P, 'tests', 'assets'), r / 'tests' / 'assets')
    for k in ('d1', 'd2', 'd3', 'd3b', 'd3c', 'd4c0', 'd4c1', 'd4c2'): shutil.copytree(os.path.join(P, 'registered_assets', k), r / 'registered_assets' / k)
    for f in ('b3_2_twelve_assets.json', 'b3_2_shared_null_asset.json'): shutil.copy(os.path.join(P, 'registered_assets', f), r / 'registered_assets')
    return str(r)


def _ctx(root): return twelve_context(root)
def _pins(e, fn):
    for f in ('d/d1_pins.json', 'd/d2_pins.json', 'd/d3_pins.json', 'b3/b3_0_pins.json', 'b3/b3_1_pins.json', 'b3/b3_2_pins.json'):
        if os.path.exists(e.path(f)): e.json(f, fn)


@pytest.fixture(scope='module')
def verified(root):
    """One authenticated pass over the copied tree (source / registered context / three screens): reused by the semantic-layer tests."""
    ctx = _ctx(root); src = rg._check_source(root); rc = rg._registered_context(root, ctx); screens = {F: rg._check_screen(root, ctx, F, src, rc) for F in rg.FAMILIES}
    return dict(ctx=ctx, src=src, rc=rc, screens=screens)


# ================================================================================================================================================= deterministic registration
def test_registry_module_registered_and_version():
    assert 'd4c2_registry.py' in MODULES and __version__ == '0.113.0' and len(rg.SCREEN_REQUIRED) == 20 and len(rg.CERT_REQUIRED) == 12


def test_ledger_receipt_deterministic_committed_and_pinned():
    fresh = rg.build_d4c2_ledger(P, CTX); assert fresh == LEDGER and fresh['ledger_sha256'] == PINS['d4c2_ledger_sha256'] == rg._payload_sha(LEDGER, 'ledger_sha256')
    L = rg.load_registered_d4c2_ledger(P, CTX); assert L['ledger_sha256'] == LEDGER['ledger_sha256'] and L['_file_sha256'] == sha(os.path.join(R, 'd4c2_ledger.json'))
    rc = rg.load_registered_d4c2_outer_receipt(P, CTX, L); assert rc['receipt_sha256'] == RECEIPT['receipt_sha256'] == PINS['d4c2_outer_receipt_sha256'] and rg.build_d4c2_outer_receipt(P, CTX, L) == RECEIPT and rc['ledger']['payload_sha256'] == L['ledger_sha256']
    for f in ('d/d1_pins.json', 'd/d2_pins.json', 'd/d3_pins.json', 'b3/b3_0_pins.json', 'b3/b3_1_pins.json', 'b3/b3_2_pins.json'):
        p = json.load(open(os.path.join(P, f))); assert all(p[k] == PINS[k] for k in rg.REGISTRATION_PINS), f
    assert L['source']['commit'] == rg.SOURCE['commit'] == 'ba51e5951ebb8c16c7106247408c912d86944675' and L['source']['engine_version'] == '0.112.0' and L['source']['inventory']['sha256'] == 'aa2c11cc01df09fc9cd130a2c0b9aa5af75d1b2acc27f47aef3d5d91d0bb2b77'
    for F in rg.FAMILIES: assert L['screens'][F]['screen']['n_blocking'] == 2000 and L['screens'][F]['execution_lock']['commit'] == rg.SOURCE['commit'] and L['screens'][F]['environment']['python'] == '3.13.16' and 'blocking_rows' not in L['screens'][F]
    C = L['certificate']; assert C['n'] == 2000 and C['n_rows_proven'] == 2000 and all(C['levels'][l]['usable_true_impossible_by_wilson'] is True and C['levels'][l]['technical_rows'] == 0 and C['levels'][l]['proven_blocking_rows'] == 2000 for l in ('support', 'strong')) and C['levels']['support']['first_blocking_count'] == 81 and C['levels']['strong']['first_blocking_count'] == 12
    assert L['bridge']['attempt'] == '20261006T115712Z_69ece7cef3' and L['bridge']['producer']['engine_version'] == '0.110.0' and L['acceptance']['decision'] == rg.ACCEPTANCE_DECISION and L['acceptance']['execution_decision'] == rg.EXECUTION_DECISION
    assert L['registered_context']['w2_cases']['E2/L1.20']['trigger'] == 'unknown' and L['registered_context']['pseudo']['n'] == 2000 and 'W2 unknown alone is not a sufficient condition' in L['statement']
    V = rg.load_registered_infeasibility_campaign(P, CTX)
    assert V['kind'] == 'calibration_infeasibility_certificate' and V['usable_true_impossible'] == dict(support=True, strong=True) and V['n'] == 2000 and V['certificate_sha256'] == PINS['d4c2_certificate_sha256'] == rg.CERTIFICATE['content_sha256'] and set(V['screens']) == set(rg.FAMILIES) and 'NOT a sealed calibration' in V['scope'] and 'calibration' not in V.get('kind', '').replace('calibration_infeasibility', '')
    for bad in (lambda d: d.update(ledger_sha256='0' * 64), lambda d: d['certificate'].update(n_rows_proven=1999), lambda d: d['screens']['E2']['screen'].update(n_blocking=1999)):
        d = copy.deepcopy(LEDGER); bad(d)
        with pytest.raises(InputContractError): rg.verify_d4c2_ledger(d, P, CTX)
    d = copy.deepcopy(RECEIPT); d['certificate']['levels']['support']['usable_true_impossible_by_wilson'] = False; d['receipt_sha256'] = rg._payload_sha(d, 'receipt_sha256')
    with pytest.raises(InputContractError): rg.verify_d4c2_outer_receipt(d, P, CTX, L)


def test_constants_equal_acceptance_documents_originals_and_the_0112_driver():
    acc = json.load(open(os.path.join(R, 'acceptance', rg.ACCEPTANCE_FILE))); dec = json.load(open(os.path.join(R, 'acceptance', rg.DECISION_FILE)))
    assert sha(os.path.join(R, 'acceptance', rg.ACCEPTANCE_FILE)) == rg.ACCEPTANCE[rg.ACCEPTANCE_FILE]['sha256'] == PINS['d4c2_acceptance_sha256'] and sha(os.path.join(R, 'acceptance', rg.DECISION_FILE)) == PINS['d4c2_execution_decision_sha256']
    assert acc['decision'] == rg.ACCEPTANCE_DECISION and dec['decision'] == rg.EXECUTION_DECISION and acc['subject']['execution_source']['inventory']['sha256'] == rg.SOURCE['inventory']['sha256'] == sha(os.path.join(R, 'source', rg.SOURCE['inventory']['file']))
    for F in rg.FAMILIES:
        a = acc['accepted_screens'][F]; C = rg.SCREENS[F]
        assert a['attempt'] == C['attempt'] and a['screen_content_sha256'] == C['screen']['content_sha256'] and a['screen_file']['sha256'] == C['screen']['sha256'] and a['run_file']['sha256'] == C['run_file_sha256'] and a['lock_file']['sha256'] == C['execution_lock']['lock_file_sha256'] and a['final_file']['sha256'] == C['final_file_sha256'] and a['inner_zip']['sha256'] == C['archive']['sha256'] and a['notebook']['sha256'] == C['executed_notebook']['sha256'] and a['n_blocking'] == C['screen']['n_blocking'] == 2000
        for rel, v in acc['inner_files'].items():
            if rel.startswith(F + '/'): assert C['files'][rel[3:]] == v and sha(os.path.join(P, SCR[F], rel[3:])) == v['sha256']
    assert acc['accepted_certificate']['file']['sha256'] == rg.CERTIFICATE['record_file']['sha256'] and acc['accepted_certificate']['content_sha256'] == rg.CERTIFICATE['content_sha256'] == PINS['d4c2_certificate_sha256'] == json.load(open(os.path.join(P, CERT_OUT, 'd4c1_certificate_record.json')))['binding']['certificate_sha256']
    assert acc['subject']['results_archive']['sha256'] == rg.RESULTS['archive']['sha256'] and acc['raw_files']['D4C2_screen_certificate_report.md']['sha256'] == rg.RESULTS['report']['sha256'] and acc['raw_files']['file_map.json']['sha256'] == rg.RESULTS['file_map']['sha256']
    # the trusted REQUIRED inventories: the registered constants == the 0.112.0 driver (byte-identical in this tree) by AST
    tree = ast.parse(open(os.path.join(P, 'd', 'd4c1_calibration.py'), encoding='utf-8').read()); req = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id in ('REQUIRED_SCREEN', 'REQUIRED_CERTIFICATE')}
    assert sha(os.path.join(P, 'd', 'd4c1_calibration.py')) == rg.SOURCE['script_sha256'] and tuple(req['REQUIRED_SCREEN']) == rg.SCREEN_REQUIRED and tuple(req['REQUIRED_CERTIFICATE']) == rg.CERT_REQUIRED
    # the bridge originals == the bridge acceptance
    bacc = json.load(open(os.path.join(P, BR, rg.BRIDGE_ACCEPTANCE_FILE))); assert sha(os.path.join(P, BR, rg.BRIDGE_ACCEPTANCE_FILE)) == PINS['d4c2_bridge_acceptance_sha256'] and bacc['decision'] == rg.BRIDGE['acceptance_decision'] and bacc['attempt'] == rg.BRIDGE['attempt']
    for n, v in bacc['original_inputs'].items(): assert rg.BRIDGE['files'][n.replace('(1)', '')]['sha256'] == v['sha256'] == sha(os.path.join(P, BR, n.replace('(1)', '')))
    assert json.load(open(os.path.join(P, BR, 'd4c2_bridge_report_20261006T115712Z_69ece7cef3.json')))['result'] == 'BRIDGE_CONTRACT_SATISFIED'


# ================================================================================================================================================= pins guards
@pytest.mark.parametrize('pin', list(rg.REGISTRATION_PINS))
@pytest.mark.parametrize('how', ['wrong', 'missing', 'null'])
def test_registration_pins_guard_every_load(root, pin, how):
    with _edit(root) as e:
        def fn(p):
            if how == 'wrong': p[pin] = 'f' * 64
            elif how == 'missing': p.pop(pin)
            else: p[pin] = None
        _pins(e, fn); ctx = _ctx(root)
        for f in (rg.load_registered_d4c2_ledger, rg.load_registered_d4c2_outer_receipt, rg.load_registered_infeasibility_campaign):
            with pytest.raises(InputContractError): f(root, ctx)


# ================================================================================================================================================= the BYTE layer: every registered original is immutable
BYTE_EDITS = ['screen_record_byte', 'screen_run_gate_false', 'screen_run_gate_removed', 'screen_final_exit_code', 'screen_lock_commit', 'screen_notebook_byte', 'screen_archive_byte', 'screen_file_missing', 'screen_file_extra', 'screen_mixed_family_run_dir',
              'certificate_record_byte', 'certificate_run_flag', 'certificate_command_edit', 'certificate_rc_nonzero', 'certificate_stderr_nonempty', 'acceptance_edit', 'decision_edit', 'results_packet_byte', 'report_byte', 'bundle_byte', 'source_inventory_byte', 'bridge_zip_byte', 'bridge_acceptance_edit', 'bridge_report_edit', 'ledger_restamped', 'receipt_restamped']


@pytest.mark.parametrize('case', BYTE_EDITS)
def test_edited_originals_are_refused(root, case):
    F = 'E7'; A = ATT[F]; run = f'{SCR[F]}/run_{A}/d4c1_screen_{F}_run.json'; rec = f'{SCR[F]}/run_{A}/d4c1_screen_{F}_record.json'
    with _edit(root) as e:
        if case == 'screen_record_byte': e.write(rec, open(e.path(rec), 'rb').read() + b' ')
        if case == 'screen_run_gate_false': e.json(run, lambda d: d['gates'].update(G_screen_computed=False))
        if case == 'screen_run_gate_removed': e.json(run, lambda d: (d['gates'].pop('G_env_lock'), d['required_inventory'].remove('G_env_lock')))
        if case == 'screen_final_exit_code': e.json(f'{SCR[F]}/d4c1_screen_final_record.json', lambda d: d.update(exit_code=1))
        if case == 'screen_lock_commit': e.json(f'{SCR[F]}/d4c1_screen_lock.json', lambda d: d.update(commit='0' * 40))
        if case == 'screen_notebook_byte': p = f"registered_assets/d4c2/screens/notebooks/{rg.SCREENS[F]['executed_notebook']['file']}"; e.write(p, open(e.path(p), 'rb').read() + b'\n')
        if case == 'screen_archive_byte': p = f"registered_assets/d4c2/screens/archives/{rg.SCREENS[F]['archive']['file']}"; e.write(p, open(e.path(p), 'rb').read() + b'\0')
        if case == 'screen_file_missing': e.remove(f'{SCR[F]}/run_{A}/d4c1_screen_{F}_stdout.log')
        if case == 'screen_file_extra': e.write(f'{SCR[F]}/run_{A}/extra.json', '{}')
        if case == 'screen_mixed_family_run_dir':
            src = os.path.join(root, SCR['E8'], f'run_{ATT["E8"]}'); e.write(f'{SCR[F]}/run_{ATT["E8"]}/d4c1_screen_E8_run.json', open(os.path.join(src, 'd4c1_screen_E8_run.json'), 'rb').read())
        if case == 'certificate_record_byte': e.write(f'{CERT_OUT}/d4c1_certificate_record.json', open(e.path(f'{CERT_OUT}/d4c1_certificate_record.json'), 'rb').read() + b' ')
        if case == 'certificate_run_flag': e.json(f'{CERT_OUT}/d4c1_certificate_run.json', lambda d: d.update(D4C1_CERTIFICATE_COMPLETE=False))
        if case == 'certificate_command_edit': e.write(f'{CERT_DIR}/command.txt', open(e.path(f'{CERT_DIR}/command.txt')).read().replace('--mode certificate', '--mode certificate --selftest-small'))
        if case == 'certificate_rc_nonzero': e.write(f'{CERT_DIR}/rc.txt', 'rc=1\n')
        if case == 'certificate_stderr_nonempty': e.write(f'{CERT_DIR}/stderr.txt', 'Traceback')
        if case == 'acceptance_edit': e.json(f'registered_assets/d4c2/acceptance/{rg.ACCEPTANCE_FILE}', lambda d: d['GO'].update(formal_usable_false_measured=True))
        if case == 'decision_edit': e.json(f'registered_assets/d4c2/acceptance/{rg.DECISION_FILE}', lambda d: d['GO'].update(formal_partial_or_subpartial_execution=True))
        if case == 'results_packet_byte': p = f"registered_assets/d4c2/results/{rg.RESULTS['archive']['file']}"; e.write(p, open(e.path(p), 'rb').read() + b'\0')
        if case == 'report_byte': p = 'registered_assets/d4c2/results/D4C2_screen_certificate_report.md'; e.write(p, open(e.path(p), 'rb').read() + b'\n')
        if case == 'bundle_byte': p = 'registered_assets/d4c2/screens/bundle/d4c1_results.zip'; e.write(p, open(e.path(p), 'rb').read() + b'\0')
        if case == 'source_inventory_byte': e.json(f"registered_assets/d4c2/source/{rg.SOURCE['inventory']['file']}", lambda d: d.update(engine_version='0.113.0'))
        if case == 'bridge_zip_byte': p = f'{BR}/d4c1_partial_E2_39082b641d86.zip'; e.write(p, open(e.path(p), 'rb').read() + b'\0')
        if case == 'bridge_acceptance_edit': e.json(f'{BR}/{rg.BRIDGE_ACCEPTANCE_FILE}', lambda d: d['GO'].update(formal_full_calibration_acceptance=True))
        if case == 'bridge_report_edit': e.json(f'{BR}/d4c2_bridge_report_20261006T115712Z_69ece7cef3.json', lambda d: d.update(mismatches=['x'], n_failed=1))
        if case == 'ledger_restamped':
            def fn(d): d['certificate']['levels']['support']['proven_blocking_rows'] = 80; d['ledger_sha256'] = rg._payload_sha(d, 'ledger_sha256')
            e.json('registered_assets/d4c2/d4c2_ledger.json', fn); _pins(e, lambda p: p.update(d4c2_ledger_sha256=rg._payload_sha(json.load(open(e.path('registered_assets/d4c2/d4c2_ledger.json'))), 'ledger_sha256')))
        if case == 'receipt_restamped':
            def fn(d): d['certificate']['levels']['strong']['usable_true_impossible_by_wilson'] = False; d['receipt_sha256'] = rg._payload_sha(d, 'receipt_sha256')
            e.json('registered_assets/d4c2/d4c2_outer_receipt.json', fn); _pins(e, lambda p: p.update(d4c2_outer_receipt_sha256=rg._payload_sha(json.load(open(e.path('registered_assets/d4c2/d4c2_outer_receipt.json'))), 'receipt_sha256')))
        ctx = _ctx(root)
        with pytest.raises(InputContractError): rg.load_registered_infeasibility_campaign(root, ctx)
    assert sha(os.path.join(root, 'registered_assets/d4c2/d4c2_ledger.json')) == sha(os.path.join(R, 'd4c2_ledger.json')) and rg._require_registration_pins(_ctx(root), root)['d4c2_ledger_sha256'] == LEDGER['ledger_sha256']           # restored (bytes + pins; the full load is exercised once above)


# ================================================================================================================================================= the SEMANTIC layer (byte layer bypassed)
def _note(layer, case, exc):
    if os.environ.get('D4C2_REG_NOTE'): open(os.environ['D4C2_REG_NOTE'], 'a').write(f'{layer}\t{case}\t{exc}\n')


def _restamp_screen(d):
    body = {k: v for k, v in d.items() if k != 'binding'}; d['binding']['screen_sha256'] = hashlib.sha256(ser.dumps(ser.from_jsonable(ser.to_jsonable(body))).encode()).hexdigest(); return d


class _bypass:
    """Bypass the byte layer: file / archive / doc constants are re-stamped from the (edited) tree and the run / final records are re-chained, so that ONLY the semantic checks remain."""
    def __init__(self, root, monkeypatch, F=None):
        self.root, self.mp, self.F = root, monkeypatch, F
    def __enter__(self):
        mp, root = self.mp, self.root
        mp.setattr(rg, '_check_files', lambda base, expected, key: {rel: dict(sha256=hashlib.sha256(open(os.path.join(dp, f), 'rb').read()).hexdigest(), bytes=os.path.getsize(os.path.join(dp, f))) for dp, _, fs in os.walk(base) for f in fs for rel in [os.path.relpath(os.path.join(dp, f), base).replace(os.sep, '/')]})
        mp.setattr(rg, '_check_archive', lambda path, const, members, key: dict(file=os.path.basename(path), sha256=const['sha256'], bytes=const['bytes'], members=len(members)))
        mp.setattr(rg, '_check_doc', lambda path, const, key: dict(file=os.path.basename(path), sha256=const['sha256'], bytes=const['bytes']))
        return self
    def rechain(self, F):
        """Re-chain lock -> run (attempt lock SHA, published evidence, screen summary SHA) -> final (lock, record_sha256) and the constants for family F after an edit."""
        root = self.root; base = os.path.join(root, SCR[F]); A = ATT[F]; rp = os.path.join(base, f'run_{A}', f'd4c1_screen_{F}_record.json'); runp = os.path.join(base, f'run_{A}', f'd4c1_screen_{F}_run.json'); finp = os.path.join(base, 'd4c1_screen_final_record.json'); lockp = os.path.join(base, 'd4c1_screen_lock.json')
        doc = ser.loads(open(rp, encoding='utf-8').read()); lock = json.load(open(lockp)); lsha = sha(lockp)
        run = json.load(open(runp)); run['attempt']['launcher_lock_sha256'] = lsha; run['published_evidence'] = {f'd4c1_screen_{F}_record.json': dict(sha256=sha(rp), bytes=os.path.getsize(rp))}; run['screen'].update(screen_sha256=doc['binding']['screen_sha256'], n_blocking=doc['n_blocking'], n_rows=doc['n_rows'], rows=([doc['rows'][0], doc['rows'][-1] + 1] if doc['rows'] else None), ratio_bound_max={s: max(x['sizes'][s]['ratio_bound'] for x in doc['results']) for s in doc['sizes']}); open(runp, 'w').write(json.dumps(run))
        fin = json.load(open(finp)); fin.update(lock=lock, lock_sha256=lsha, record_sha256=sha(runp), gates=run['gates']); open(finp, 'w').write(json.dumps(fin))
        C = copy.deepcopy(rg.SCREENS[F]); C['execution_lock']['lock_file_sha256'] = lsha; C['run_file_sha256'] = sha(runp); C['final_file_sha256'] = sha(finp); C['screen'].update(sha256=sha(rp), bytes=os.path.getsize(rp), content_sha256=doc['binding']['screen_sha256'], n_blocking=doc['n_blocking'], ratio_bound_max=run['screen']['ratio_bound_max'], min_P=min(x['sizes'][s]['min_P'] for x in doc['results'] for s in doc['sizes']), w2=doc['w2'], config_ids=doc['config_ids'], pseudo=doc['pseudo'])
        for rel in list(C['files']): C['files'][rel] = dict(sha256=sha(os.path.join(base, rel)), bytes=os.path.getsize(os.path.join(base, rel)))
        S = dict(rg.SCREENS); S[F] = C; self.mp.setattr(rg, 'SCREENS', S)
    def rechain_certificate(self, sync_sources=True):
        root = self.root; out = os.path.join(root, CERT_OUT); rp = os.path.join(out, 'd4c1_certificate_record.json'); runp = os.path.join(out, 'd4c1_certificate_run.json')
        cert = ser.loads(open(rp, encoding='utf-8').read()); body = {k: v for k, v in cert.items() if k != 'binding'}; cert['binding']['certificate_sha256'] = hashlib.sha256(ser.dumps(ser.from_jsonable(ser.to_jsonable(body))).encode()).hexdigest(); open(rp, 'w', encoding='utf-8').write(ser.dumps(cert))
        run = json.load(open(runp)); run['published_evidence'] = {'d4c1_certificate_record.json': dict(sha256=sha(rp), bytes=os.path.getsize(rp))}; run['sources'] = cert['sources'] if sync_sources else run['sources']; open(runp, 'w').write(json.dumps(run))
        C = copy.deepcopy(rg.CERTIFICATE); C['content_sha256'] = cert['binding']['certificate_sha256']; C['record_file'].update(sha256=sha(rp), bytes=os.path.getsize(rp)); C['run_file_sha256'] = sha(runp); C['n'] = cert['n']; C['thresholds'] = cert['thresholds']; C['n_rows_admitted'] = cert.get('n_rows_admitted'); C['n_rows_proven'] = cert.get('n_rows_proven'); C['command_file_sha256'] = hashlib.sha256(open(os.path.join(root, CERT_DIR, 'command.txt'), 'rb').read()).hexdigest()
        for rel in list(C['files']): C['files'][rel] = dict(sha256=sha(os.path.join(root, CERT_DIR, rel)), bytes=os.path.getsize(os.path.join(root, CERT_DIR, rel)))
        self.mp.setattr(rg, 'CERTIFICATE', C)
    def __exit__(self, *a): return False


SEMANTIC_SCREEN = ['gate_missing_from_trusted_inventory', 'gate_false_everywhere_consistent', 'old_version_source_mixed', 'probe_run', 'selftest_run', 'instrumented_run', 'family_mixed_record', 'N4_removed', 'w2_summary_edited_checksum_kept', 'w2_true_premise', 'row_threshold_changed', 'paired_columns_changed', 'rows_subset', 'rows_duplicated_6000',
                   'environment_not_registered', 'env_gate_not_ok', 'd2_input_other_run', 'final_fallback', 'precheck_dirty', 'commit_relabelled_to_registration_version']


@pytest.mark.parametrize('case', SEMANTIC_SCREEN)
def test_semantic_screen_refusals_with_byte_layer_bypassed(root, verified, monkeypatch, case):
    F = 'E2'; A = ATT[F]; base = os.path.join(root, SCR[F]); rp = os.path.join(base, f'run_{A}', f'd4c1_screen_{F}_record.json'); runp = os.path.join(base, f'run_{A}', f'd4c1_screen_{F}_run.json'); finp = os.path.join(base, 'd4c1_screen_final_record.json'); lockp = os.path.join(base, 'd4c1_screen_lock.json')
    def edit_json(p, fn, canonical=False):
        d = ser.loads(open(p, encoding='utf-8').read()) if canonical else json.load(open(p)); fn(d); open(p, 'w', encoding='utf-8').write(ser.dumps(_restamp_screen(d)) if canonical else json.dumps(d))
    with _edit(root) as e, _bypass(root, monkeypatch) as b:
        for p in (rp, runp, finp, lockp): e.saved[os.path.relpath(p, root)] = open(p, 'rb').read()
        if case == 'gate_missing_from_trusted_inventory': edit_json(runp, lambda d: (d['gates'].pop('G_env_lock'), d['required_inventory'].remove('G_env_lock')))
        if case == 'gate_false_everywhere_consistent': edit_json(runp, lambda d: (d['gates'].update(G_env_lock=False), d.update(required_all_true=False)))
        if case == 'old_version_source_mixed': edit_json(runp, lambda d: (d['source'].update(inventory_sha256='7df1fb5948eb2c0c0d379a37afa93c0f1dbc0bba77c01c49d6be60665d9bb1ba', engine_version='0.110.0'), d.update(engine_version='0.110.0')))
        if case == 'probe_run': edit_json(runp, lambda d: d.update(probe=True, probe_n=3))
        if case == 'selftest_run': edit_json(runp, lambda d: d.update(selftest=True, formal=False))
        if case == 'instrumented_run': edit_json(runp, lambda d: d.update(instrument=True))
        if case == 'family_mixed_record': edit_json(rp, lambda d: d.update(family='E7'), canonical=True)
        if case == 'N4_removed':
            def drop(d):
                for x in d['results']:
                    for sz in x['sizes'].values():
                        for p_ in sz['positions'].values(): p_['stages'].pop('N4'); p_['bank_stages'] = ['N0']
                        vals = [r['P'] for p_ in sz['positions'].values() for r in p_['stages'].values()]; sz['min_P'], sz['max_P'] = min(vals), max(vals); sz['ratio_bound'] = max(vals) / min(vals); sz['ok'] = bool(sz['all_positive'] and sz['ratio_bound'] <= 2.0); sz['complete_coverage'] = False; sz['stages_covered'] = ['N0']
                    x['blocking'] = bool(d['w2_applicable'] and all(sz['ok'] for sz in x['sizes'].values())); x['complete_coverage'] = False
                d['n_blocking'] = sum(1 for x in d['results'] if x['blocking']); d['complete_coverage'] = False
            edit_json(rp, drop, canonical=True)
        if case == 'w2_summary_edited_checksum_kept': edit_json(rp, lambda d: d['w2']['L1.20'].update(B_final=d['w2']['L1.20']['B_final'] + 1), canonical=True)
        if case == 'w2_true_premise': edit_json(rp, lambda d: (d['w2']['L1.00'].update(trigger=True, validation_state='valid'), d.update(w2_applicable=False, n_blocking=0), [x.update(blocking=False) for x in d['results']]), canonical=True)
        if case == 'row_threshold_changed': edit_json(rp, lambda d: d['results'][5]['threshold'].__setitem__(0, d['results'][5]['threshold'][0] + 1.0), canonical=True)
        if case == 'paired_columns_changed': edit_json(rp, lambda d: d['pseudo'].update(sha256_T1='9' * 64), canonical=True)
        if case == 'rows_subset': edit_json(rp, lambda d: (d['rows'].pop(), d['results'].pop(), d.update(n_rows=1999, n_blocking=sum(1 for x in d['results'] if x['blocking']))), canonical=True)
        if case == 'rows_duplicated_6000': edit_json(rp, lambda d: (d['rows'].extend(d['rows']), d['results'].extend(copy.deepcopy(d['results'])), d.update(n_rows=4000, n_blocking=4000)), canonical=True)
        if case == 'environment_not_registered': edit_json(runp, lambda d: d['env'].update(python='3.13.14'))
        if case == 'env_gate_not_ok': edit_json(runp, lambda d: d['env_gate'].update(versions_ok=False))      # the live environment gate of the producer reported not ok (screens carry no separate twelve gate: the env gate + registered-environment check are the live gate)
        if case == 'd2_input_other_run': edit_json(runp, lambda d: d['inputs']['d2'].update(run_id='20260923T125656Z'))
        if case == 'final_fallback': edit_json(finp, lambda d: d.update(launcher_fallback=True))
        if case == 'precheck_dirty': edit_json(finp, lambda d: d['bindings']['live_source_precheck'].update(clean=False))
        if case == 'commit_relabelled_to_registration_version': edit_json(lockp, lambda d: d.update(engine='0.113.0'))
        b.rechain(F)
        with pytest.raises(InputContractError) as ei: rg._check_screen(root, verified['ctx'], F, verified['src'], verified['rc'])
        _note('screen', case, ei.value)
    monkeypatch.undo()                                                                                                                                                                  # constants back before the restored tree is re-checked
    assert rg._check_screen(root, verified['ctx'], F, verified['src'], verified['rc'])['screen']['n_blocking'] == 2000                                                                  # restored


SEMANTIC_CERT = ['denominator_6000', 'screen_duplicated_as_fourth_source', 'threshold_swap', 'levels_edited', 'technical_rows_claimed', 'source_attempt_mixed', 'engine_relabelled', 'run_evaluated_source', 'consumer_env_skip_flag', 'n_rows_proven_double']


@pytest.mark.parametrize('case', SEMANTIC_CERT)
def test_semantic_certificate_refusals_with_byte_layer_bypassed(root, verified, monkeypatch, case):
    out = os.path.join(root, CERT_OUT); rp = os.path.join(out, 'd4c1_certificate_record.json'); runp = os.path.join(out, 'd4c1_certificate_run.json'); cmdp = os.path.join(root, CERT_DIR, 'command.txt')
    def edit_rec(fn):
        d = ser.loads(open(rp, encoding='utf-8').read()); fn(d); open(rp, 'w', encoding='utf-8').write(ser.dumps(d))
    def edit_run(fn):
        d = json.load(open(runp)); fn(d); open(runp, 'w').write(json.dumps(d))
    with _edit(root) as e, _bypass(root, monkeypatch) as b:
        for p in (rp, runp, cmdp): e.saved[os.path.relpath(p, root)] = open(p, 'rb').read()
        if case == 'denominator_6000': edit_rec(lambda d: (d.update(n=6000), d['pseudo'].update(n=6000)))
        if case == 'screen_duplicated_as_fourth_source': edit_rec(lambda d: d['sources'].append(copy.deepcopy(d['sources'][0])))
        if case == 'threshold_swap': edit_rec(lambda d: d.update(thresholds=dict(support=0.01, strong=0.05)))
        if case == 'levels_edited': edit_rec(lambda d: d['levels']['support'].update(proven_blocking_rows=1999))
        if case == 'technical_rows_claimed': edit_rec(lambda d: (d['rows']['7']['families']['E2'].update(support='technical_fail'), d['rows']['7']['levels']['support'].update(aggregate='technical_fail', technical=True)))
        if case == 'source_attempt_mixed': edit_rec(lambda d: d['sources'][0]['attempt'].update(attempt_id=ATT['E7']))
        if case == 'engine_relabelled': edit_rec(lambda d: (d.update(engine_version='0.113.0'), d['binding'].update(engine_version='0.113.0')))
        if case == 'run_evaluated_source': edit_run(lambda d: d['sources'].append(dict(kind='evaluated', family='E2', rows=[0, 3])))
        if case == 'consumer_env_skip_flag': open(cmdp, 'w').write(open(cmdp).read().replace('--mode certificate', '--mode certificate --selftest-skip-env-lock'))
        if case == 'n_rows_proven_double': edit_rec(lambda d: d.update(n_rows_proven=4000))
        b.rechain_certificate(sync_sources=(case != 'run_evaluated_source'))
        with pytest.raises(InputContractError) as ei: rg._check_certificate(root, verified['src'], verified['screens'], verified['rc'])
        _note('certificate', case, ei.value)
    monkeypatch.undo()
    assert rg._check_certificate(root, verified['src'], verified['screens'], verified['rc'])['n_rows_proven'] == 2000                                                                   # restored


# ================================================================================================================================================= never a sealed calibration / partial
def test_registered_certificate_is_never_promoted(tmp_path):
    cert = ser.loads(open(os.path.join(P, CERT_OUT, 'd4c1_certificate_record.json'), encoding='utf-8').read()); ar = Archive(str(tmp_path / 'ar'))
    ref = ar.put('transition', cert, dict(kind='calibration_infeasibility_certificate', certificate_sha256=cert['binding']['certificate_sha256']))
    for loader in (load_sealed_record, load_partial_record, load_subpartial_record):
        with pytest.raises(InputContractError): loader(ar, ref.as_dict())
    with pytest.raises(InputContractError): load_combined_sealed_record(ar, ref.as_dict())
    with pytest.raises(InputContractError): _check_partial_shape(cert)
    with pytest.raises(InputContractError): check_subpartial_shape(cert)
    V = rg.load_registered_infeasibility_campaign(P, CTX); assert 'calibration' not in {k for k in V if k not in ('kind',)} and 'per_pseudo_family_status' not in V and 'families' not in V and V['levels']['support']['proven_blocking_rows'] == 2000
