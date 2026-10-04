# -*- coding: utf-8 -*-
"""D4C-0 registration contracts (step1_engine.d4c0_registry + registered_assets/d4c0; the bodies behind w2_cases.load_registered_w2_context and
d4_pseudo.load_registered_pseudo_columns). The accepted formal pseudo generation (attempt 20261004T102334Z, commit 12980202 / 0.103.0) and the accepted formal D-2W run
(attempt 20261004T144349Z, commit f3aec793 / 0.104.0) are registered as ORIGINAL bytes (inner archives' members == registered files; executed notebooks; acceptance documents)
and bound deterministically: ledger == re-derivation == committed file == pins; receipt == re-derivation == pins; the module constants equal the acceptance documents; each run is
bound to ITS OWN execution lock; the failed D-2W attempt is registered separately as failure history. Consumer loaders: the registered W2 context is RESTORED from the
authenticated original case records with expected_context_sha256 from the authenticated pins and every decision equal to the registered constant (the four unknowns stay
unknown); the registered pseudo columns are the ORIGINAL NPZ re-verified against the constant identity. Refusals: every registration pin wrong / missing / null (ledger,
receipt and both loaders); edits of any registered original (case record bytes, re-hashed decision promotion unknown -> False, context record, run record gates / flags,
final record success flag, lock commit, missing / extra / mixed case files, archive bytes, notebook bytes, acceptance document, failed-attempt record promoted to success,
failed attempt substituted for the success run, NPZ nextafter / row order / dtype change); re-stamped ledger / receipt edits; a wrong expected context pin; a small-bank
(self-test) record substituted for a formal one."""
import os, sys, json, copy, shutil, hashlib, io, zipfile
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine import d4c0_registry as rg
from step1_engine import w2_cases as wc, d4_pseudo as dp
from step1_engine.d3_profile import twelve_context
from step1_engine.checkpoint import MODULES
from step1_engine.errors import InputContractError
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); CTX = twelve_context(P); PINS = json.load(open(os.path.join(P, 'd', 'd3_pins.json'))); R = os.path.join(P, 'registered_assets', 'd4c0')
LEDGER = json.load(open(os.path.join(R, 'd4c0_ledger.json'))); RECEIPT = json.load(open(os.path.join(R, 'd4c0_outer_receipt.json')))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
D2W_RUN = os.path.join('registered_assets', 'd4c0', rg.D2W['registered_dir']); PSE_RUN = os.path.join('registered_assets', 'd4c0', rg.PSEUDO['registered_dir']); FAIL_RUN = os.path.join('registered_assets', 'd4c0', rg.D2W['failed_attempt']['registered_dir'])


@pytest.fixture(scope='module')
def root(tmp_path_factory):
    """A copy of the tree parts the registration reads (pins / d / registered assets); tests edit it and restore through _edit."""
    r = tmp_path_factory.mktemp('reg') / 'phaseB'; (r / 'registered_assets').mkdir(parents=True); shutil.copytree(os.path.join(P, 'd'), r / 'd'); shutil.copytree(os.path.join(P, 'tests', 'assets'), r / 'tests' / 'assets')
    for k in ('d1', 'd2', 'd3', 'd3b', 'd3c', 'd4c0'): shutil.copytree(os.path.join(P, 'registered_assets', k), r / 'registered_assets' / k)
    for f in ('b3_2_twelve_assets.json', 'b3_2_shared_null_asset.json'): shutil.copy(os.path.join(P, 'registered_assets', f), r / 'registered_assets')
    return str(r)


class _edit:
    """Temporarily replace / remove / add files under the copied root; everything restored on exit."""
    def __init__(self, root): self.root = root; self.saved = {}; self.added = []
    def __enter__(self): return self
    def path(self, rel): return os.path.join(self.root, rel)
    def write(self, rel, data):
        p = self.path(rel)
        if rel not in self.saved: self.saved[rel] = open(p, 'rb').read() if os.path.exists(p) else None
        if isinstance(data, str): data = data.encode()
        os.makedirs(os.path.dirname(p), exist_ok=True); open(p, 'wb').write(data)
    def json(self, rel, fn):
        d = json.load(open(self.path(rel))); fn(d); self.write(rel, json.dumps(d, indent=1, ensure_ascii=False))
    def remove(self, rel):
        p = self.path(rel); self.saved.setdefault(rel, open(p, 'rb').read()); os.remove(p)
    def __exit__(self, *a):
        for rel, b in self.saved.items():
            p = self.path(rel)
            if b is None:
                if os.path.exists(p): os.remove(p)
            else: os.makedirs(os.path.dirname(p), exist_ok=True); open(p, 'wb').write(b)


def _ctx(root): return twelve_context(root)


def _pins(e, fn): e.json('d/d3_pins.json', fn)


# ================================================================================================================================================= registered content
def test_ledger_receipt_deterministic_committed_and_pinned():
    L = rg.build_d4c0_ledger(P, CTX); assert L == LEDGER == rg.build_d4c0_ledger(P, CTX) and L['ledger_sha256'] == PINS['d4c0_ledger_sha256'] and rg.verify_d4c0_ledger(LEDGER, P, CTX) == LEDGER
    Lr = rg.load_registered_d4c0_ledger(P, CTX); assert {k: v for k, v in Lr.items() if k != '_file_sha256'} == LEDGER and Lr['_file_sha256'] == sha(os.path.join(R, 'd4c0_ledger.json'))
    Rc = rg.build_d4c0_outer_receipt(P, CTX); assert Rc == RECEIPT and Rc['receipt_sha256'] == PINS['d4c0_outer_receipt_sha256'] and rg.verify_d4c0_outer_receipt(RECEIPT, P, CTX) == RECEIPT and Rc['ledger'] == dict(payload_sha256=L['ledger_sha256'], file_sha256=Lr['_file_sha256'], schema=rg.LEDGER_SCHEMA)
    assert 'd4c0_registry.py' in MODULES and L['d2w']['units_bound'] == 27 and L['d2w']['summary'] == dict(valid_false=['E2/L1.00', 'E2/L1.50', 'E7/L1.00', 'E8/L1.20', 'E8/L1.50'], unresolved_unknown=['E2/L1.20', 'E7/L1.20', 'E7/L1.50', 'E8/L1.00'], technical_failures=0)
    # the two runs keep their own historical execution locks (different commits / engine versions); the registration version is not written into them
    assert L['pseudo']['execution_lock']['commit'] == '12980202ee111a26c0a608e7e5bba6caed5302ae' and L['pseudo']['execution_lock']['engine_version'] == '0.103.0' and L['d2w']['execution_lock']['commit'] == 'f3aec79358452a293ccced14efd4f7e3ad240477' and L['d2w']['execution_lock']['engine_version'] == '0.104.0' and L['d2w']['failed_attempt']['execution_commit'] == '12980202ee111a26c0a608e7e5bba6caed5302ae' and L['d2w']['failed_attempt']['success'] is False
    for k, v in PINS.items(): assert '0.105.0' not in json.dumps(L) or k  # the ledger carries no registration-version stamp
    assert '0.105.0' not in json.dumps(L) and '0.105.0' not in json.dumps(Rc)
    assert set(rg.REGISTRATION_PINS) <= set(PINS) and PINS['d2w_acceptance_sha256'] == rg.D2W['acceptance']['sha256'] == 'c9506e0b17f7ef17c3d1168e0acabdbba0195748060ca531b8c22305dbbd922a' and PINS['pseudo_acceptance_sha256'] == rg.PSEUDO['acceptance']['sha256'] == '08efa1d19b29303425125aed71f96f0f27765c03234b36164f98ba4631cbee5b'
    assert PINS['d2w_context_sha256'] == rg.D2W['context_sha256'] == '50ec5a54d593d9bc53ce3661292d7dd3cb385369511a3444fda62226e77acb9c' and PINS['pseudo_paired_sha256'] == rg.PSEUDO['columns']['paired_sha256'] == 'c9f75cdb86c90b0c73409a3e7a015faaef1e5903788358082dde3c21d66a1d15' and PINS['pseudo_npz_sha256'] == rg.PSEUDO['npz']['sha256'] == 'c62a965b3b649870977d95ba247bf84a9580131109fc8572971e06b98da490f2'


def test_constants_equal_acceptance_documents_and_originals():
    acc_p = json.load(open(os.path.join(R, 'pseudo', 'acceptance', rg.PSEUDO['acceptance']['file']))); acc_d = json.load(open(os.path.join(R, 'd2w', 'acceptance', rg.D2W['acceptance']['file'])))
    assert sha(os.path.join(R, 'pseudo', 'acceptance', rg.PSEUDO['acceptance']['file'])) == rg.PSEUDO['acceptance']['sha256'] and sha(os.path.join(R, 'd2w', 'acceptance', rg.D2W['acceptance']['file'])) == rg.D2W['acceptance']['sha256']
    assert acc_p['subject']['files'] == {k: v['sha256'] for k, v in rg.PSEUDO['files'].items()} and acc_p['subject']['columns'] == rg.PSEUDO['columns'] and acc_p['subject']['npz'] == rg.PSEUDO['npz'] and acc_p['subject']['execution_lock']['commit'] == rg.PSEUDO['execution_lock']['commit']
    assert {k: v['sha256'] for k, v in acc_d['subject']['files'].items()} == {k: v['sha256'] for k, v in rg.D2W['files'].items()} and acc_d['subject']['context_sha256'] == rg.D2W['context_sha256'] and acc_d['previous_failure']['files'] == {k: v['sha256'] for k, v in rg.D2W['failed_attempt']['files'].items()}
    for k, c in rg.D2W['cases'].items(): a = acc_d['subject']['cases'][k]; assert a['file_identity']['sha256'] == c['file_sha256'] and a['decision']['trigger'] == c['trigger'] and a['decision']['validation_state'] == c['validation_state'] and a['decision']['B_final'] == c['B_final']
    # registered members == constants == archive members (both runs and the failed attempt)
    for base, const, arc in ((PSE_RUN, rg.PSEUDO['files'], os.path.join(R, 'pseudo', 'archives', rg.PSEUDO['archive']['file'])), (D2W_RUN, rg.D2W['files'], os.path.join(R, 'd2w', 'archives', rg.D2W['archive']['file'])), (FAIL_RUN, rg.D2W['failed_attempt']['files'], os.path.join(R, 'd2w', 'archives', rg.D2W['failed_attempt']['archive']['file']))):
        found = {}
        for dp_, _, fs in os.walk(os.path.join(P, base)):
            for f in fs: p = os.path.join(dp_, f); found[os.path.relpath(p, os.path.join(P, base)).replace(os.sep, '/')] = dict(sha256=sha(p), bytes=os.path.getsize(p))
        z = zipfile.ZipFile(arc); members = {i.filename: dict(sha256=hashlib.sha256(z.read(i.filename)).hexdigest(), bytes=i.file_size) for i in z.infolist() if not i.is_dir()}
        assert found == const == members
    assert wc.D2W_REGISTRATION == dict(attempt=rg.D2W['attempt'], commit=rg.D2W['execution_lock']['commit'], engine_version='0.104.0', context_sha256=rg.D2W['context_sha256'], acceptance_sha256=rg.D2W['acceptance']['sha256'], archive_sha256=rg.D2W['archive']['sha256'], executed_notebook_sha256=rg.D2W['executed_notebook']['sha256'])
    assert dp.PSEUDO_REGISTRATION['paired_sha256'] == rg.PSEUDO['columns']['paired_sha256'] and dp.PSEUDO_REGISTRATION['engine_version'] == '0.103.0'


# ================================================================================================================================================= consumer loaders
def test_registered_w2_context_restored_with_exact_decisions():
    w2ctx, view = wc.load_registered_w2_context(P, CTX)
    assert w2ctx.context_sha256 == rg.D2W['context_sha256'] == view['context_sha256'] and sorted(w2ctx.decisions) == sorted(rg.CANON_CASES) and w2ctx.scope == wc.SCOPE_TRUSTED and w2ctx.asset_sha256 == rg.D2W['asset_sha256']
    for k, c in rg.D2W['cases'].items():
        d = w2ctx.decisions[k]; assert d.trigger == c['trigger'] and d.validation_state == c['validation_state'] and int(d.B_final) == c['B_final'] and d.observed_hash == c['observed_hash'] and d.distance_kind == 'exact_pot_w2'
    assert [k for k in rg.CANON_CASES if w2ctx.decisions[k].trigger == 'unknown'] == ['E2/L1.20', 'E7/L1.20', 'E7/L1.50', 'E8/L1.00'] and all(w2ctx.decisions[k].trigger is False for k in ('E2/L1.00', 'E2/L1.50', 'E7/L1.00', 'E8/L1.20', 'E8/L1.50'))
    assert view['execution_lock']['commit'] == 'f3aec79358452a293ccced14efd4f7e3ad240477' and view['ledger_sha256'] == PINS['d4c0_ledger_sha256'] and view['receipt_sha256'] == PINS['d4c0_outer_receipt_sha256'] and view['acceptance_sha256'] == PINS['d2w_acceptance_sha256'] and 'W2 branch only' in view['scope']
    w2b, _ = rg.load_registered_w2_context(P, CTX); assert w2b.context_sha256 == w2ctx.context_sha256 and all(w2b.decisions[k] == w2ctx.decisions[k] for k in rg.CANON_CASES)


def test_registered_pseudo_columns_are_the_original_npz():
    cols = dp.load_registered_pseudo_columns(P, CTX)
    assert cols['n'] == 2000 and cols['identity'] == rg.PSEUDO['columns'] and cols['T1'].dtype == np.float64 and cols['T1'].shape == (2000,) and cols['uids'][0] == [1, 400, 5001, 0, 0] and cols['uids'][-1] == [1, 400, 5001, 0, 1999] and np.array_equal(cols['cid'], np.arange(2000))
    z = np.load(os.path.join(P, PSE_RUN, f"run_{rg.PSEUDO['attempt']}", 'd4_pseudo_columns.npz')); assert all(np.array_equal(z[k], cols[k]) for k in ('T1', 'T2', 'AX', 'PL', 'cid'))      # bytes of the original, not a regeneration
    assert cols['view']['execution_lock']['commit'] == '12980202ee111a26c0a608e7e5bba6caed5302ae' and cols['view']['npz'] == rg.PSEUDO['npz'] and cols['view']['acceptance_sha256'] == PINS['pseudo_acceptance_sha256'] and 'generation order' in cols['view']['order']
    assert hashlib.sha256(np.ascontiguousarray(np.c_[cols['T1'], cols['T2']]).tobytes()).hexdigest() == PINS['pseudo_paired_sha256']


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
        assert rg.build_d4c0_ledger(root, ctx)['ledger_sha256'] == LEDGER['ledger_sha256']                       # the deterministic build does not depend on the pins
        loaders = [rg.load_registered_d4c0_ledger, rg.load_registered_d4c0_outer_receipt, rg.load_registered_w2_context, rg.load_registered_pseudo_columns, wc.load_registered_w2_context, dp.load_registered_pseudo_columns]
        if pin == 'd4c0_outer_receipt_sha256' and how == 'wrong': assert rg.load_registered_d4c0_ledger(root, ctx)['ledger_sha256'] == LEDGER['ledger_sha256']; loaders.remove(rg.load_registered_d4c0_ledger)      # the ledger load requires the receipt pin to be PRESENT; its value is bound at the receipt load (every consumer load goes through it)
        for f in loaders:
            with pytest.raises(InputContractError): f(root, ctx)
    assert rg.load_registered_d4c0_ledger(root, _ctx(root))['ledger_sha256'] == LEDGER['ledger_sha256']          # restored


def test_wrong_expected_context_pin_refuses_before_any_promotion(root):
    with _edit(root) as e:
        _pins(e, lambda p: p.__setitem__('d2w_context_sha256', rg.D2W['context_sha256'][:-1] + ('0' if rg.D2W['context_sha256'][-1] != '0' else '1')))
        with pytest.raises(InputContractError): rg.load_registered_w2_context(root, _ctx(root))


# ================================================================================================================================================= edits of registered originals
A = rg.D2W['attempt']; PA = rg.PSEUDO['attempt']; FA = rg.D2W['failed_attempt']['attempt']
CASE = f'{D2W_RUN}/run_{A}/cases/d2w_case_E2_L1.20.json'
EDITS = ['case_byte', 'case_promote_unknown_rehashed', 'case_missing', 'case_extra', 'case_mixed_small_bank', 'context_record', 'run_gate_false', 'run_pass_flag', 'final_pass_flag', 'lock_commit', 'archive_byte', 'notebook_byte', 'acceptance_edit', 'failed_promoted', 'failed_substituted',
         'pseudo_npz_nextafter', 'pseudo_npz_reorder', 'pseudo_npz_dtype', 'pseudo_record_identity', 'pseudo_lock_commit', 'pseudo_acceptance_edit', 'pseudo_notebook_byte', 'pseudo_archive_byte', 'ledger_restamped', 'receipt_restamped', 'ledger_payload_edit']


def _npz_edit(e, fn):
    p = e.path(f'{PSE_RUN}/run_{PA}/d4_pseudo_columns.npz'); z = np.load(p); d = {k: z[k] for k in z.files}; fn(d); buf = io.BytesIO(); np.savez(buf, **d); e.write(f'{PSE_RUN}/run_{PA}/d4_pseudo_columns.npz', buf.getvalue())


@pytest.mark.parametrize('case', EDITS)
def test_edited_originals_are_refused(root, case):
    with _edit(root) as e:
        if case == 'case_byte': e.write(CASE, open(e.path(CASE), 'rb').read() + b' ')
        if case == 'case_promote_unknown_rehashed':
            def fn(d): d['decision']['validation_state'] = 'valid'; d['decision']['trigger'] = False; d['decision']['validation_reason'] = None
            e.json(CASE, fn)
        if case == 'case_missing': e.remove(CASE)
        if case == 'case_extra': e.write(f'{D2W_RUN}/run_{A}/cases/d2w_case_E1_L1.50.json', '{}')
        if case == 'case_mixed_small_bank':
            def fn(d):
                for u in d['inputs']['units'].values(): u['bank_identity_f64']['K'] = 50; u['bank_identity_f64']['rows'] = 5000
            e.json(CASE, fn)
        if case == 'context_record': e.json(f'{D2W_RUN}/run_{A}/d2w_context_record.json', lambda d: d['case_records']['E2/L1.20'].__setitem__('trigger', False))
        if case == 'run_gate_false': e.json(f'{D2W_RUN}/run_{A}/d2w_run_record.json', lambda d: d['gates'].__setitem__('G_records_restored', False))
        if case == 'run_pass_flag': e.json(f'{D2W_RUN}/run_{A}/d2w_run_record.json', lambda d: d.__setitem__('selftest', True))
        if case == 'final_pass_flag': e.json(f'{D2W_RUN}/d2w_final_record.json', lambda d: d.__setitem__('d2w_pass', False))
        if case == 'lock_commit': e.json(f'{D2W_RUN}/d2w_lock.json', lambda d: d.__setitem__('commit', '0' * 40))
        if case == 'archive_byte': p = f"registered_assets/d4c0/d2w/archives/{rg.D2W['archive']['file']}"; e.write(p, open(e.path(p), 'rb').read() + b'\0')
        if case == 'notebook_byte': p = f"registered_assets/d4c0/d2w/notebooks/{rg.D2W['executed_notebook']['file']}"; e.write(p, open(e.path(p), 'rb').read() + b'\n')
        if case == 'acceptance_edit': e.json(f"registered_assets/d4c0/d2w/acceptance/{rg.D2W['acceptance']['file']}", lambda d: d['subject']['cases']['E2/L1.20']['decision'].__setitem__('trigger', False))
        if case == 'failed_promoted': e.json(f'{FAIL_RUN}/d2w_final_record.json', lambda d: d.__setitem__('d2w_pass', True))
        if case == 'failed_substituted':
            for f in ('d2w_final_record.json', 'd2w_lock.json'): e.write(f'{D2W_RUN}/{f}', open(e.path(f'{FAIL_RUN}/{f}'), 'rb').read())
        if case == 'pseudo_npz_nextafter': _npz_edit(e, lambda d: d['T1'].__setitem__(7, np.nextafter(d['T1'][7], np.inf)))
        if case == 'pseudo_npz_reorder': _npz_edit(e, lambda d: (d.__setitem__('T1', d['T1'][::-1].copy()), d.__setitem__('T2', d['T2'][::-1].copy())))
        if case == 'pseudo_npz_dtype': _npz_edit(e, lambda d: d.__setitem__('T2', d['T2'].astype(np.float32)))
        if case == 'pseudo_record_identity': e.json(f'{PSE_RUN}/run_{PA}/d4_pseudo_record.json', lambda d: d['columns']['identity'].__setitem__('n', 1999))
        if case == 'pseudo_lock_commit': e.json(f'{PSE_RUN}/d4_pseudo_lock.json', lambda d: d.__setitem__('commit', rg.D2W['execution_lock']['commit']))
        if case == 'pseudo_acceptance_edit': e.json(f"registered_assets/d4c0/pseudo/acceptance/{rg.PSEUDO['acceptance']['file']}", lambda d: d['subject']['columns'].__setitem__('paired_sha256', 'a' * 64))
        if case == 'pseudo_notebook_byte': p = f"registered_assets/d4c0/pseudo/notebooks/{rg.PSEUDO['executed_notebook']['file']}"; e.write(p, open(e.path(p), 'rb').read() + b'\n')
        if case == 'pseudo_archive_byte': p = f"registered_assets/d4c0/pseudo/archives/{rg.PSEUDO['archive']['file']}"; e.write(p, open(e.path(p), 'rb').read() + b'\0')
        if case == 'ledger_restamped':
            d = copy.deepcopy(LEDGER); d['d2w']['summary']['technical_failures'] = 1; d['ledger_sha256'] = rg._payload_sha(d, 'ledger_sha256'); e.write('registered_assets/d4c0/d4c0_ledger.json', json.dumps(d)); _pins(e, lambda p: p.__setitem__('d4c0_ledger_sha256', d['ledger_sha256']))
        if case == 'receipt_restamped':
            d = copy.deepcopy(RECEIPT); d['d2w']['cases']['E2/L1.20']['trigger'] = False; d['receipt_sha256'] = rg._payload_sha(d, 'receipt_sha256'); e.write('registered_assets/d4c0/d4c0_outer_receipt.json', json.dumps(d)); _pins(e, lambda p: p.__setitem__('d4c0_outer_receipt_sha256', d['receipt_sha256']))
        if case == 'ledger_payload_edit': e.json('registered_assets/d4c0/d4c0_ledger.json', lambda d: d['d2w']['cases']['E2/L1.20'].__setitem__('trigger', False))
        ctx = _ctx(root)
        if case not in ('ledger_restamped', 'receipt_restamped', 'ledger_payload_edit'):
            with pytest.raises(InputContractError): rg.build_d4c0_ledger(root, ctx)
        if case != 'receipt_restamped':
            with pytest.raises(InputContractError): rg.load_registered_d4c0_ledger(root, ctx)
        else: assert rg.load_registered_d4c0_ledger(root, ctx)['ledger_sha256'] == LEDGER['ledger_sha256']      # the ledger is untouched; the re-stamped receipt is refused by its re-derivation
        if case != 'ledger_payload_edit':
            with pytest.raises(InputContractError): rg.load_registered_d4c0_outer_receipt(root, ctx)
        with pytest.raises(InputContractError): rg.load_registered_w2_context(root, ctx)
        with pytest.raises(InputContractError): rg.load_registered_pseudo_columns(root, ctx)
    assert rg.build_d4c0_ledger(root, _ctx(root)) == LEDGER                                                     # restored: the copy is the registered content again


def test_restore_refuses_small_bank_record_and_mixed_families():
    """Direct contract of the restoration used by the loader: a self-test-shaped record (K x m != 200000) or a record of another asset is refused under require_formal."""
    rec = json.load(open(os.path.join(P, D2W_RUN, f'run_{A}', 'cases', 'd2w_case_E2_L1.00.json'))); asset = wc.registered_shared_null_asset(P)
    small = copy.deepcopy(rec); small['inputs']['formal'] = False
    with pytest.raises(InputContractError): wc.restore_w2_context([small], asset, expected_context_sha256=None, require_formal=True)
    other = copy.deepcopy(rec); other['asset_sha256'] = 'b' * 64
    with pytest.raises(InputContractError): wc.restore_w2_context([other], asset, require_formal=True)
    with pytest.raises(InputContractError): wc.restore_w2_context([rec, rec], asset, require_formal=True)
    one = wc.restore_w2_context([rec], asset, require_formal=True); assert one.decisions['E2/L1.00'].trigger is False and one.context_sha256 != rg.D2W['context_sha256']      # a single-case context is NOT the registered nine-case context
    with pytest.raises(InputContractError): wc.restore_w2_context([rec], asset, expected_context_sha256=rg.D2W['context_sha256'], require_formal=True)
