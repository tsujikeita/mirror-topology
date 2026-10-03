# -*- coding: utf-8 -*-
"""D-3c tranche 2 contracts (step1_engine.d3c_ledger + registered_assets/d3c): the three accepted formal profile runs are registered as ORIGINAL bytes (inner archives'
members == registered files; executed notebooks; acceptance documents) and bound deterministically: ledger == re-derivation == committed file == pins; outer receipt == re-derivation
== pins, bound to the ledger payload + file SHA, the acceptance constants + file bytes and the per-family identities; per-family identities (attempt / plan identity / ordered UID
SHA / fingerprints / record SHAs) equal the acceptance document; REQUIRED gate inventory == the profile script. Edits of any registered original (record flags, gate inventory,
fingerprints, family mix, plan document UIDs / constants, lock commit, final record, self-test flags, stderr, extra attempt files, missing family, archive, notebook, acceptance
document) are refused by the re-derivation; re-stamped ledger / receipt edits are refused; a pins change refuses the load (build still equals the registered content).
Consumer API: the plans are REBUILT from the registered ordered UIDs at the registered constants and must reproduce the accepted identity (E2, full scale); consumer inputs are
accepted only with both accepted fingerprints, the accepted plan identity and plans reproducing it (and, if given, an official passed gate with the accepted check inventory);
wrong fingerprints / identity / plans / gate / family / unverified view / unshared plans / foreign UIDs are refused."""
import os, sys, json, copy, shutil, hashlib, re, zipfile, types
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine import d3c_ledger as dl
from step1_engine.d3c_ledger import build_d3c_profile_ledger, verify_d3c_profile_ledger, load_registered_d3c_ledger, build_d3c_outer_receipt, verify_d3c_outer_receipt, load_registered_d3c_outer_receipt, intake_registered_d3c_profiles, rebuild_registered_plans, verify_consumer_inputs, verify_consumer_family_inputs, D3cProfiles, EXECUTION_LOCK, PROFILE_ACCEPTANCE, ATTEMPTS, INNER_ARCHIVES, EXECUTED_NOTEBOOKS, REQUIRED_GATES
from step1_engine.d3_profile import twelve_context, fix_family_plans, verify_plan_identity, _payload_sha as plan_sha
from step1_engine.checkpoint import MODULES
from step1_engine.errors import InputContractError
from step1_engine.types import ClusterUID
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); CTX = twelve_context(P); PINS = json.load(open(os.path.join(P, 'd', 'd3_pins.json'))); D3C = os.path.join(P, 'registered_assets', 'd3c')
LEDGER = json.load(open(os.path.join(D3C, 'd3c_profile_ledger.json'))); RECEIPT = json.load(open(os.path.join(D3C, 'd3c_outer_receipt.json'))); ACC = json.load(open(os.path.join(D3C, 'acceptance', PROFILE_ACCEPTANCE['decision_file'])))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()


def _copy_root(tmp_path):
    r = tmp_path / 'phaseB'; (r / 'registered_assets').mkdir(parents=True); shutil.copytree(os.path.join(P, 'd'), r / 'd'); shutil.copytree(os.path.join(P, 'tests', 'assets'), r / 'tests' / 'assets')
    for k in ('d1', 'd2', 'd3', 'd3b', 'd3c'): shutil.copytree(os.path.join(P, 'registered_assets', k), r / 'registered_assets' / k)
    shutil.copy(os.path.join(P, 'registered_assets', 'b3_2_twelve_assets.json'), r / 'registered_assets'); return str(r)


def _restamp(doc, key):
    d = copy.deepcopy(doc); d[key] = dl._payload_sha(d, key); return d


def _rewrite(path, fn):
    doc = json.load(open(path)); fn(doc); open(path, 'w').write(json.dumps(doc, indent=1, ensure_ascii=False))


def test_ledger_and_receipt_deterministic_registered_and_bound():
    L = build_d3c_profile_ledger(P, CTX); assert L == LEDGER == build_d3c_profile_ledger(P, CTX) and L['ledger_sha256'] == PINS['d3c_ledger_sha256'] and verify_d3c_profile_ledger(LEDGER, P, CTX) == LEDGER
    reg = load_registered_d3c_ledger(P, CTX); assert reg['_file_sha256'] == sha(os.path.join(D3C, 'd3c_profile_ledger.json')) and reg['ledger_sha256'] == L['ledger_sha256']
    R = build_d3c_outer_receipt(P, CTX); assert R == RECEIPT == build_d3c_outer_receipt(P, CTX) and R['receipt_sha256'] == PINS['d3c_outer_receipt_sha256'] and verify_d3c_outer_receipt(RECEIPT, P, CTX) == RECEIPT
    rr = load_registered_d3c_outer_receipt(P, CTX); assert rr['_file_sha256'] == sha(os.path.join(D3C, 'd3c_outer_receipt.json')) and R['ledger'] == dict(payload_sha256=L['ledger_sha256'], file_sha256=reg['_file_sha256'], schema='d3c_profile_ledger_v1')
    assert L['execution_lock'] == EXECUTION_LOCK and L['acceptance'] == PROFILE_ACCEPTANCE and PINS['d3c_acceptance_sha256'] == PROFILE_ACCEPTANCE['decision_sha256'] == L['acceptance_files']['decision']['sha256'] == sha(os.path.join(D3C, 'acceptance', PROFILE_ACCEPTANCE['decision_file']))
    assert list(L['families']) == ['E2', 'E7', 'E8'] and L['totals'] == dict(L['totals'], families=3, attempts=3, supplies=216, profile_checks=990, twelve_checks=42) and 19000 < L['totals']['peak_rss_mb_max'] < 20000 and L['registered_d3b'] == dict(ledger_payload_sha256=PINS['d3b_ledger_sha256'], ledger_file_sha256=L['registered_d3b']['ledger_file_sha256'], outer_receipt_sha256=PINS['d3b_outer_receipt_sha256'])
    src = open(os.path.join(P, 'd', 'd3c_profile.py'), encoding='utf-8').read(); assert tuple(re.findall(r'"(G_[a-zA-Z0-9_]+)"', src.split('REQUIRED = (', 1)[1].split(')', 1)[0])) == REQUIRED_GATES and 'd3c_ledger.py' in MODULES
    for fam, e in L['families'].items():
        A = ACC['families'][fam]; assert e['attempt_id'] == ATTEMPTS[fam] == A['attempt_id'] and e['plan_identity']['identity_sha256'] == A['plan_identity_sha256'] and e['ordered_uid_sha256'] == A['ordered_uid_sha256'] and {k: e['input_fingerprints'][k] for k in ('matched', 'native')} == A['input_fingerprints'] and e['inner_archive'] == INNER_ARCHIVES[fam] and e['executed_notebook'] == EXECUTED_NOTEBOOKS[fam]
        assert {k: v['sha256'] for k, v in e['records'].items()} == {k: v['sha256'] for k, v in A['archive']['files'].items()} and e['required_gates'] == {g: True for g in REQUIRED_GATES} and e['gate']['mode'] == 'official' and e['gate']['passed'] is True and len(e['gate']['diagnostics']['checks']) == 330 and len(e['gate']['diagnostics']['twelve_checks']) == 14
        assert e['constants'] == dict(e['constants'], B=2000, B_KDE=2000, seeds=5, K_fit=2000, master_seed=20260912, K0=10000, K1=30000, m=100, n_fit=200000) and e['n_uids'] == dict(batch0=10000, batch1=30000) and e['supplies'] == dict(e['supplies'], n=72, first_wave=18, added=54) and e['family_identity']['full_surviving_scope'] is True
        assert e['live_source']['precheck']['head'] == e['live_source']['prelaunch']['head'] == EXECUTION_LOCK['commit'] and e['environment'] == dict(python='3.13.15', numpy='2.1.3', scipy='1.16.3', healpy='1.20.0', camb='2.0.4', pot='0.9.7.post1')
        with zipfile.ZipFile(os.path.join(D3C, 'archives', INNER_ARCHIVES[fam]['file'])) as z: assert {i.filename for i in z.infolist() if not i.is_dir()} == set(e['records']) and all(hashlib.sha256(z.read(n)).hexdigest() == e['records'][n]['sha256'] == sha(os.path.join(D3C, 'runs', f'{fam}_{e["attempt_id"]}', n)) for n in e['records'])
        assert R['families'][fam] == dict(attempt_id=e['attempt_id'], plan_identity_sha256=e['plan_identity']['identity_sha256'], ordered_uid_sha256=e['ordered_uid_sha256'], input_fingerprints={k: e['input_fingerprints'][k] for k in ('matched', 'native')}, lock_sha256=e['lock_sha256'], profile_record_sha256=e['profile_record_sha256'], plan_document_sha256=e['plan_document']['sha256'], inner_archive_sha256=e['inner_archive']['sha256'], executed_notebook_sha256=e['executed_notebook']['sha256'], gate_passed=True, gate_mode='official', registered_dir=e['registered_dir'])
    # document edits are refused even when re-stamped; non-context callers refused
    for edit in ('family_sha', 'drop_family', 'acceptance', 'lock', 'totals', 'statement', 'gate'):
        bad = copy.deepcopy(LEDGER)
        if edit == 'family_sha': bad['families']['E7']['profile_record_sha256'] = '0' * 64
        elif edit == 'drop_family': bad['families'].pop('E8')
        elif edit == 'acceptance': bad['acceptance']['decision'] = 'PASS'
        elif edit == 'lock': bad['execution_lock']['commit'] = 'a' * 40
        elif edit == 'totals': bad['totals']['supplies'] = 215
        elif edit == 'gate': bad['families']['E2']['gate']['passed'] = False
        else: bad['statement'] = 'x'
        with pytest.raises(InputContractError): verify_d3c_profile_ledger(bad, P, CTX)
        with pytest.raises(InputContractError): verify_d3c_profile_ledger(_restamp(bad, 'ledger_sha256'), P, CTX)
    for edit in ('family', 'ledger', 'acceptance_files', 'pins_binding'):
        bad = copy.deepcopy(RECEIPT)
        if edit == 'family': bad['families']['E2']['plan_identity_sha256'] = '0' * 64
        elif edit == 'ledger': bad['ledger']['payload_sha256'] = '0' * 64
        elif edit == 'acceptance_files': bad['acceptance_files']['decision']['sha256'] = '0' * 64
        else: bad['pins_binding']['d3b_outer_receipt_sha256'] = '0' * 64
        with pytest.raises(InputContractError): verify_d3c_outer_receipt(bad, P, CTX)
        with pytest.raises(InputContractError): verify_d3c_outer_receipt(_restamp(bad, 'receipt_sha256'), P, CTX)
    for notctx in (dict(CTX._d), None, LEDGER):
        with pytest.raises(InputContractError): build_d3c_profile_ledger(P, notctx)
        with pytest.raises(InputContractError): intake_registered_d3c_profiles(P, notctx)
    with pytest.raises(InputContractError): D3cProfiles(dict(ledger=LEDGER, receipt=RECEIPT, root=P))


EDITS = ['record_pass', 'record_gate_check_dropped', 'record_gate_mode', 'record_fingerprint_after', 'record_family', 'record_selftest', 'record_supply_manifest', 'record_context', 'plan_uid_swap', 'plan_B', 'plan_attempt', 'lock_commit', 'lock_root', 'final_pass', 'final_attempt', 'final_prelaunch_head', 'final_args_selftest', 'stderr', 'extra_superseded', 'missing_family', 'archive', 'notebook_missing', 'acceptance_edit', 'pins']


@pytest.mark.parametrize('edit', EDITS)
def test_registered_original_edits_refused(tmp_path, edit):
    root = _copy_root(tmp_path); fam = 'E7'; att = ATTEMPTS[fam]; d = os.path.join(root, 'registered_assets', 'd3c', 'runs', f'{fam}_{att}'); run = os.path.join(d, f'run_{att}')
    rp, pp, lp, fp = os.path.join(run, f'd3c_profile_record_{fam}.json'), os.path.join(run, f'd3c_plan_identity_{fam}.json'), os.path.join(d, 'profile_lock.json'), os.path.join(d, 'profile_final_record.json')
    if edit == 'record_pass': _rewrite(rp, lambda r: r.update(D3C_PASS=False))
    elif edit == 'record_gate_check_dropped': _rewrite(rp, lambda r: r['gate']['diagnostics']['checks'].pop())
    elif edit == 'record_gate_mode': _rewrite(rp, lambda r: r['gate'].update(mode='smoke'))
    elif edit == 'record_fingerprint_after': _rewrite(rp, lambda r: r['input_fingerprints_after_gate'].update(native='0' * 64))
    elif edit == 'record_family': _rewrite(rp, lambda r: r.update(family='E2'))
    elif edit == 'record_selftest': _rewrite(rp, lambda r: r.update(selftest=True))
    elif edit == 'record_supply_manifest': _rewrite(rp, lambda r: r['supplies'][sorted(r['supplies'])[0]]['manifests'].update(fit='0' * 64))
    elif edit == 'record_context': _rewrite(rp, lambda r: r['context_identities'].update(config_map_sha256='0' * 64))
    elif edit == 'plan_uid_swap':
        def f(p): u = p['ordered_uids']['1']; u[0], u[1] = u[1], u[0]
        _rewrite(pp, f)
    elif edit == 'plan_B': _rewrite(pp, lambda p: p.update(B=1999))
    elif edit == 'plan_attempt': _rewrite(pp, lambda p: p['attempt'].update(attempt_id=ATTEMPTS['E2']))
    elif edit == 'lock_commit': _rewrite(lp, lambda l: l.update(commit='b' * 40))
    elif edit == 'lock_root': _rewrite(lp, lambda l: l.update(d2_run_root=l['d2_run_root'].replace('E7', 'E2')))
    elif edit == 'final_pass': _rewrite(fp, lambda f: f.update(profile_pass=False))
    elif edit == 'final_attempt': _rewrite(fp, lambda f: f.update(attempt_id=ATTEMPTS['E8']))
    elif edit == 'final_prelaunch_head': _rewrite(fp, lambda f: f['bindings']['live_source_prelaunch'].update(head='c' * 40))
    elif edit == 'final_args_selftest': _rewrite(fp, lambda f: f['args'].append('--selftest-small'))
    elif edit == 'stderr': open(os.path.join(d, f'profile_stderr_{att}.txt'), 'w').write('Traceback')
    elif edit == 'extra_superseded': open(os.path.join(d, f'superseded_final_record_before_{att}.json'), 'w').write('{}')
    elif edit == 'missing_family': shutil.rmtree(os.path.join(root, 'registered_assets', 'd3c', 'runs', f'E8_{ATTEMPTS["E8"]}'))
    elif edit == 'archive':
        ap = os.path.join(root, 'registered_assets', 'd3c', 'archives', INNER_ARCHIVES[fam]['file']); b = bytearray(open(ap, 'rb').read()); b[-1] ^= 1; open(ap, 'wb').write(bytes(b))
    elif edit == 'notebook_missing': os.remove(os.path.join(root, 'registered_assets', 'd3c', 'notebooks', EXECUTED_NOTEBOOKS[fam]['file']))
    elif edit == 'acceptance_edit': _rewrite(os.path.join(root, 'registered_assets', 'd3c', 'acceptance', PROFILE_ACCEPTANCE['decision_file']), lambda a: a['families']['E7'].update(plan_identity_sha256='0' * 64))
    else: _rewrite(os.path.join(root, 'd', 'd3_pins.json'), lambda p: p.update(d3c_ledger_sha256='0' * 64))
    cx = twelve_context(root)
    if edit == 'pins':
        assert build_d3c_profile_ledger(root, cx) == LEDGER
        with pytest.raises(InputContractError): load_registered_d3c_ledger(root, cx)
    else:
        with pytest.raises(InputContractError): build_d3c_profile_ledger(root, cx)
        with pytest.raises(InputContractError): load_registered_d3c_ledger(root, cx)
    with pytest.raises(InputContractError): intake_registered_d3c_profiles(root, cx)
    with pytest.raises(InputContractError): build_d3c_profile_ledger(root, CTX)        # the context must be the one verified at this root
    assert build_d3c_profile_ledger(P, CTX) == LEDGER                                   # the registered root is untouched


def test_consumer_api_rebuild_and_refusals():
    Pr = intake_registered_d3c_profiles(P, CTX); table = CTX.table; fam = 'E2'; E = Pr.family(fam)
    assert Pr.verified and Pr.accepted and Pr.families == ('E2', 'E7', 'E8') and Pr.ledger_sha256 == PINS['d3c_ledger_sha256'] and Pr.receipt_sha256 == PINS['d3c_outer_receipt_sha256'] and Pr.execution_lock == EXECUTION_LOCK and Pr.attempt_id('E8') == ATTEMPTS['E8']
    with pytest.raises(AttributeError): Pr.accepted = False
    for bad in ('E1', 'E9', ''):
        with pytest.raises(InputContractError): Pr.family(bad)
    ou = Pr.ordered_uids(fam); assert len(ou[0]) == 10000 and len(ou[1]) == 30000 and ou[0][0] == (1, 200, 1002, 0, 0) and ou[1][-1] == (1, 200, 1002, 1, 29999)
    v = Pr.gate_record(fam); v['passed'] = False; assert Pr.gate_record(fam)['passed'] is True and Pr.input_fingerprints(fam) == {k: E['input_fingerprints'][k] for k in ('matched', 'native')}
    # the consumer's plans are REBUILT from the registered ordered UIDs at full scale and must reproduce the accepted identity
    plans, fplans, ident = rebuild_registered_plans(Pr, fam, table); assert ident == Pr.plan_identity(fam) == E['plan_identity'] and ident['identity_sha256'] == ACC['families'][fam]['plan_identity_sha256'] and set(plans) == set(fplans) == {0, 1, 2, 3, 4}
    fpr = Pr.input_fingerprints(fam); rec = verify_consumer_inputs(Pr, fam, fpr, plans, fplans, ident, table=table, gate=Pr.gate_record(fam))
    assert rec == dict(family=fam, attempt_id=ATTEMPTS[fam], plan_identity_sha256=ident['identity_sha256'], input_fingerprints=fpr, ledger_sha256=Pr.ledger_sha256, receipt_sha256=Pr.receipt_sha256, gate_checked=True) and verify_consumer_inputs(Pr, fam, fpr, plans, fplans, ident)['gate_checked'] is False
    # refusals: wrong / swapped fingerprints, another family's identity, a re-sealed identity, plans with seeds swapped, a gate with a dropped check / not passed / smoke, family E1, unverified view
    with pytest.raises(InputContractError): verify_consumer_inputs(Pr, fam, dict(matched=fpr['native'], native=fpr['matched']), plans, fplans, ident)
    with pytest.raises(InputContractError): verify_consumer_inputs(Pr, fam, dict(matched=fpr['matched'], native='0' * 64), plans, fplans, ident)
    with pytest.raises(InputContractError): verify_consumer_inputs(Pr, fam, fpr, plans, fplans, Pr.plan_identity('E7'))
    alt = copy.deepcopy(ident); alt['B'] = 1999; alt['identity_sha256'] = plan_sha(alt, 'identity_sha256')
    with pytest.raises(InputContractError): verify_consumer_inputs(Pr, fam, fpr, plans, fplans, alt)
    swapped = {0: plans[1], 1: plans[0], 2: plans[2], 3: plans[3], 4: plans[4]}
    with pytest.raises(InputContractError): verify_consumer_inputs(Pr, fam, fpr, swapped, fplans, ident)
    for g_edit in ('drop', 'fail', 'smoke', 'twelve_drop'):
        g = Pr.gate_record(fam)
        if g_edit == 'drop': g['diagnostics']['checks'].pop()
        elif g_edit == 'fail': g['diagnostics']['checks'][0]['passed'] = False
        elif g_edit == 'smoke': g['mode'] = 'smoke'
        else: g['diagnostics']['twelve_checks'].pop()
        with pytest.raises(InputContractError): verify_consumer_inputs(Pr, fam, fpr, plans, fplans, ident, gate=g)
    with pytest.raises(InputContractError): verify_consumer_inputs(Pr, 'E1', fpr, plans, fplans, ident)
    with pytest.raises(InputContractError): verify_consumer_inputs(dict(Pr._d), fam, fpr, plans, fplans, ident)
    with pytest.raises(InputContractError): rebuild_registered_plans(Pr, fam, dict(table, master_seed=1))
    with pytest.raises(InputContractError): rebuild_registered_plans(Pr, 'E1', table)
    # FamilyInput form: wrong family / unshared plans / foreign UIDs are refused before any fingerprint; a double carrying the registered UIDs is refused at the fingerprint (not a FamilyInput)
    uids = [ClusterUID(*u) for u in ou[0] + ou[1]]; cfg = types.SimpleNamespace(evaluation_id=40101, system='matched', cluster_uids=uids, m=100, batches={0: (0, 1000000), 1: (1000000, 4000000)})
    fm = types.SimpleNamespace(family=fam, plans=plans, fit_plans=fplans, configs=[cfg]); fn = types.SimpleNamespace(family=fam, plans=plans, fit_plans=fplans, configs=[cfg])
    with pytest.raises(InputContractError): verify_consumer_family_inputs(Pr, 'E7', fm, fn, ident, table=table)
    with pytest.raises(InputContractError): verify_consumer_family_inputs(Pr, fam, fm, types.SimpleNamespace(family=fam, plans=dict(plans), fit_plans=fplans, configs=[cfg]), ident, table=table)
    rev = types.SimpleNamespace(evaluation_id=40101, system='native', cluster_uids=uids[:10000] + uids[10000:][::-1], m=100, batches=cfg.batches)
    with pytest.raises(InputContractError): verify_consumer_family_inputs(Pr, fam, fm, types.SimpleNamespace(family=fam, plans=plans, fit_plans=fplans, configs=[rev]), ident, table=table)
    with pytest.raises(InputContractError): verify_consumer_family_inputs(Pr, fam, fm, fn, ident, table=table)
    with pytest.raises(InputContractError): verify_consumer_family_inputs(Pr, fam, fm, None, ident, table=table)
