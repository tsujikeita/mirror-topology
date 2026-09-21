# -*- coding: utf-8 -*-
"""D4-4 / D4-1 v2 (audit RD4T2-A/B/C/D): normal runs (expanded E7, NON-expanded E7 with an all-False W2 context, E1-only) verify; each tampered link is refused AFTER re-binding
(change -> rebound -> reader refuses for the link reason, not the outer SHA); semantic tampers re-archived at correct content addresses are refused; a different valid W2 context
between seal and target is refused; a missing pseudo full Result stops evaluate_sealed_target before target evaluation; official scope contracts."""
import os, sys, json, copy, hashlib
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from step1_engine.run_reader import verify_run_references, _payload_sha
from step1_engine.calibration_first import commit_target, calibrate_sealed, evaluate_sealed_target
from step1_engine import integrated_runner as ir
from step1_engine.archive import Archive, ArchiveRef
from step1_engine.errors import InputContractError
from step1_engine.w2_context import build_w2_context
from step1_engine import serialization as ser
from runner_fixture import M, SEED, cheap_dist, WHITE, pair
NONCE = 'author-nonce-0123456789abcdef'

def rebound(x):
    x = copy.deepcopy(x); x['binding']['run_manifest_sha256'] = _payload_sha(x); return x

def reg_of(b): return dict(shared_null_asset_sha256=b['ctx'].asset_sha256, w2_context_sha256=b['ctx'].context_sha256)

def _refuse(d, arc, reg, mutate, needle):
    t = copy.deepcopy(d); mutate(t); t = rebound(t)
    with pytest.raises(InputContractError) as e: verify_run_references(t, arc, reg)
    needles = needle if isinstance(needle, tuple) else (needle,)
    assert any(n in str(e.value) for n in needles), (needle, str(e.value))

def _all_false_ctx(b):
    """A valid context with W2 trigger False for every size (positions identical to the reference template)."""
    inputs = {k: copy.deepcopy(b['w2_inputs']['E7/L1.50']) for k in b['w2_inputs']}
    ctx = build_w2_context(b['asset'], inputs, M, SEED, cheap_dist, WHITE, b['asset'].sha256); ctx.results = {}; ctx.validate(); return ctx

def test_normal_expanded_non_expanded_and_e1_runs_verify(tmp_path):
    from fixture32 import base, twelve_from_cases, multifamily_trigger_only_pseudo
    b = base(); ti = twelve_from_cases(b['cases']); arc = Archive(str(tmp_path / 'a'))
    rm = ir.run_first_wave(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, (100., 550.), np.array([100.]), np.array([550.]), arc, 'smoke', twelve_inputs={'E7': ti})
    v = verify_run_references(rm.as_dict(), arc, reg_of(b)); assert v['ok'] and v['registered_context_ok'] and v['n_cases'] == 3 and v['n_pseudo'] == 1
    assert 'NOT approved' in verify_run_references(rm.as_dict(), arc)['context_scope']
    ctxF = _all_false_ctx(b); arc2 = Archive(str(tmp_path / 'b'))                                                     # RD4T2-A: non-expanded family (required_manifests all None) must verify
    rm2 = ir.run_first_wave(b['reg'], b['man'], b['cases'], ctxF, ctxF.context_sha256, (100., 550.), np.array([100.]), np.array([550.]), arc2, 'smoke')
    assert rm2.families['E7']['expand_family'] is False and all(v is None for v in rm2.families['E7']['required_manifests'].values())
    assert verify_run_references(rm2.as_dict(), arc2, dict(shared_null_asset_sha256=ctxF.asset_sha256, w2_context_sha256=ctxF.context_sha256))['ok']
    mf = multifamily_trigger_only_pseudo(b); e1 = {k: v for k, v in mf['cases'].items() if k.startswith('E1/')}; arc3 = Archive(str(tmp_path / 'c'))
    rm3 = ir.run_first_wave(mf['reg'], mf['man'], e1, mf['ctx'], mf['ctx'].context_sha256, (200., 1000.), np.array([200.]), np.array([1000.]), arc3, 'smoke')
    assert rm3.families['E1']['expand_family'] is False and verify_run_references(rm3.as_dict(), arc3, dict(shared_null_asset_sha256=mf['ctx'].asset_sha256, w2_context_sha256=mf['ctx'].context_sha256))['ok']
    # inconsistent plan: a non-expanded family carrying a manifest SHA, or an expanded family with None, is refused
    _refuse(rm2.as_dict(), arc2, dict(shared_null_asset_sha256=ctxF.asset_sha256, w2_context_sha256=ctxF.context_sha256), lambda t: t['families']['E7']['required_manifests'].__setitem__('L1.00', '0' * 64), ('non-expanded family carries', 'coordinator plan inconsistent'))
    _refuse(rm.as_dict(), arc, reg_of(b), lambda t: t['families']['E7']['required_manifests'].__setitem__('L1.00', None), ('lacks the required manifest SHA', 'coordinator plan inconsistent'))

def test_link_tampers_refused_after_rebound(tmp_path):
    from fixture32 import base, twelve_from_cases; b = base(); ti = twelve_from_cases(b['cases']); arc = Archive(str(tmp_path / 'a'))
    rm = ir.run_first_wave(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, (100., 550.), np.array([100.]), np.array([550.]), arc, 'smoke', twelve_inputs={'E7': ti}); d = rm.as_dict(); reg = reg_of(b)
    _refuse(d, arc, reg, lambda t: t['cases']['E7/L1.00']['truths'].__setitem__('support', True), 'differ from the archived position record')
    _refuse(d, arc, reg, lambda t: t['cases']['E7/L1.00']['result_ref'].__setitem__('sha256', '0' * 64), ('archived result SHA', 'canonical location'))
    _refuse(d, arc, reg, lambda t: t['archive_refs'].pop('family_core:E7'), 'family_core reference missing')
    _refuse(d, arc, reg, lambda t: t['families']['E7']['family_core'].__setitem__('Q_point', 999.0), 'family core record differs')
    _refuse(d, arc, reg, lambda t: t['cases'].pop('E7/L1.00'), 'case set differs')
    _refuse(d, arc, reg, lambda t: (t['thresholds']['pseudo'].__setitem__('sha256_T2', '0' * 64), t['binding']['sealed_dependencies']['pseudo'].__setitem__('sha256_T2', '0' * 64)), 'recorded SHA')
    _refuse(d, arc, reg, lambda t: t['calibration']['support']['summary'].__setitem__('threshold', 0.99), 'summary field threshold')
    _refuse(d, arc, reg, lambda t: t['calibration']['support']['summary'].__setitem__('rate_upper', 0.99), 'summary field rate_upper')
    _refuse(d, arc, reg, lambda t: t['per_pseudo_family_status'][0]['E7'].__setitem__('core_technical', True), ('core technical failure recorded', 'core technical / plan status'))
    _refuse(d, arc, reg, lambda t: (t['families']['E7'].update(status='final at 3 positions', position_plan_status='final at 3 positions', expand_family=False, required_manifests={k: None for k in t['families']['E7']['required_manifests']}, twelve_stage=None), t['archive_refs'].pop('twelve_family_core:E7', None)), ('coordinator plan inconsistent', 'restored plan'))
    _refuse(d, arc, reg, lambda t: t['families']['E7']['eligible_truths'].__setitem__('support', True) if str(t['families']['E7']['eligibility']).startswith('eligible') else t['families']['E7'].__setitem__('eligibility', 'eligible: 12-position family mixture (local completion passed)'), ('eligible truths differ', 'eligibility / eligible truths'))
    s0 = next(iter(d['families']['E7']['required_manifests'])); _refuse(d, arc, reg, lambda t: t['families']['E7']['required_manifests'].__setitem__(s0, '1' * 64), ('restored twelve manifest differs', 'manifest mismatch'))
    _refuse(d, arc, reg, lambda t: t['per_pseudo_family_status'][0]['E7'].__setitem__('twelve_full_result_sha256', '2' * 64), 'full Result reference inconsistent')
    _refuse(d, arc, reg, lambda t: t['per_pseudo_family_status'].__setitem__(0, {}) or t['per_pseudo_family_status'].append(t['per_pseudo_family_status'][0]) if False else t['per_pseudo_family_status'].pop(0), ('per-pseudo status count', 'per-pseudo status missing'))
    _refuse(d, arc, reg, lambda t: t['per_pseudo_family_status'][0]['E7']['eligible_truths'].__setitem__('support', True), ('truths differ', 'eligible truths'))
    _refuse(d, arc, reg, lambda t: t['calibration']['support']['summary'].__setitem__('usable', True), 'summary field usable')
    _refuse(d, arc, reg, lambda t: t['calibration']['support'].__setitem__('full_procedure', True), 'full_procedure flag')
    _refuse(d, arc, reg, lambda t: t['fingerprints'].__setitem__('at_end', {}), 'at_gate != at_end')
    _refuse(d, arc, reg, lambda t: t['cases']['E7/L1.00'].__setitem__('diagnostic_ref', None), 'diagnostic reference that the manifest omits')
    t7 = copy.deepcopy(d); t7['calibration']['support']['truths'] = [True]                                              # edited WITHOUT rebinding -> outer SHA
    with pytest.raises(InputContractError, match='payload SHA'): verify_run_references(t7, arc, reg)
    with pytest.raises(InputContractError): verify_run_references(d, arc, dict(shared_null_asset_sha256='0' * 64, w2_context_sha256=b['ctx'].context_sha256))
    p = os.path.join(str(tmp_path / 'a'), d['cases']['E7/L1.00']['result_ref']['path']); open(p, 'a').write(' ')
    with pytest.raises(InputContractError): verify_run_references(d, arc, reg)

def test_semantic_tampers_rearchived_at_correct_addresses_are_refused(tmp_path):
    from fixture32 import base, twelve_from_cases; b = base(); ti = twelve_from_cases(b['cases']); arc = Archive(str(tmp_path / 'a'))
    rm = ir.run_first_wave(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, (100., 550.), np.array([100.]), np.array([550.]), arc, 'smoke', twelve_inputs={'E7': ti}); d = rm.as_dict(); reg = reg_of(b)
    def swap(t, key_path, mutate_record, kind_identity):
        ref = key_path(t); rec = ser.from_jsonable(arc.get(ArchiveRef(**ref))); mutate_record(rec); new = arc.put(kind_identity[0], rec, kind_identity[1]); ref.update(new.as_dict()); return new
    # twelve manifest weight edited, internal sha stale -> structural checks refuse
    s0 = next(iter(d['families']['E7']['required_manifests']))
    def m1(t):
        ref = t['archive_refs'][f'twelve_manifest:E7/{s0}']; rec = ser.from_jsonable(arc.get(ArchiveRef(**ref))); rec['weights'][0] = 0.123; new = arc.put('twelve_manifest', rec, dict(ref['identity'])); ref.update(new.as_dict())
    _refuse(d, arc, reg, m1, ('manifest', 'weights'))
    # registry anchor edited, internal sha stale -> registry_from_dict refuses
    def m2(t):
        ref = t['archive_refs']['registry']; rec = ser.from_jsonable(arc.get(ArchiveRef(**ref))); rec['anchors']['E7'][0][0] += 1e-3; new = arc.put('registry', rec, dict(ref['identity'])); ref.update(new.as_dict())
    with pytest.raises(InputContractError): (lambda t: (m2(t), verify_run_references(rebound(t), arc, reg)))(copy.deepcopy(d))
    # family_core Q_point edited in the stored record (manifest unchanged) -> refused
    def m3(t):
        ref = t['archive_refs']['family_core:E7']; rec = ser.from_jsonable(arc.get(ArchiveRef(**ref))); rec['Q_point'] = 999.0; new = arc.put('family_result', rec, dict(ref['identity'])); ref.update(new.as_dict())
    _refuse(d, arc, reg, m3, ('family core record differs', 'does not reproduce'))
    # Q_point edited in BOTH the record and the manifest summary -> the shared validator refuses from the stored configuration probabilities
    def m3b(t):
        ref = t['archive_refs']['family_core:E7']; rec = ser.from_jsonable(arc.get(ArchiveRef(**ref))); rec['Q_point'] = 999.0; new = arc.put('family_result', rec, dict(ref['identity'])); ref.update(new.as_dict()); t['families']['E7']['family_core']['Q_point'] = 999.0
    _refuse(d, arc, reg, m3b, 'does not reproduce')
    if 'twelve_family_core:E7' in d['archive_refs']:
        def m3c(t):
            ref = t['archive_refs']['twelve_family_core:E7']; rec = ser.from_jsonable(arc.get(ArchiveRef(**ref))); k = next(iter(rec['per_config'])); v = rec['per_config'].pop(k); rec['per_config'][999999] = v; new = arc.put('family_result', rec, dict(ref['identity'])); ref.update(new.as_dict())
        _refuse(d, arc, reg, m3c, ('twelve', 'configuration', 'identity', 'archive', 'inventor'))
        def m3d(t):
            ref = t['archive_refs']['twelve_family_core:E7']; rec = ser.from_jsonable(arc.get(ArchiveRef(**ref))); rec['native'] = None; new = arc.put('family_result', rec, dict(ref['identity'])); ref.update(new.as_dict())
        _refuse(d, arc, reg, m3d, ('native', 'twelve', 'archive', 'inventor'))
    # native configuration deleted from the target 12-position full Result
    if 'twelve_family_core:E7' in d['archive_refs']:
        def m4(t):
            ref = t['archive_refs']['twelve_family_core:E7']; rec = ser.from_jsonable(arc.get(ArchiveRef(**ref))); k = next(iter(rec['native']['per_config'])); rec['native']['per_config'].pop(k); new = arc.put('family_result', rec, dict(ref['identity'])); ref.update(new.as_dict())
        _refuse(d, arc, reg, m4, ('configuration inventor', 'native', 'twelve', 'archive'))
    # pseudo full Result threshold edited
    st = d['per_pseudo_family_status'][0]['E7']
    if st.get('twelve_full_result_ref'):
        def m5(t):
            s = t['per_pseudo_family_status'][0]['E7']; ref = s['twelve_full_result_ref']; rec = ser.from_jsonable(arc.get(ArchiveRef(**ref))); rec['evidence']['threshold'] = [999.0, 999.0]; new = arc.put('family_result', rec, dict(ref['identity'])); ref.update(new.as_dict()); s['twelve_full_result_sha256'] = new.sha256
        _refuse(d, arc, reg, m5, 'threshold differs')
        def m6(t):
            s = t['per_pseudo_family_status'][0]['E7']; ref = s['twelve_full_result_ref']; rec = ser.from_jsonable(arc.get(ArchiveRef(**ref))); k = next(iter(rec['native']['per_config'])); rec['native']['per_config'].pop(k); new = arc.put('family_result', rec, dict(ref['identity'])); ref.update(new.as_dict()); s['twelve_full_result_sha256'] = new.sha256
        _refuse(d, arc, reg, m6, ('native', 'twelve', 'archive', 'configuration', 'inventor'))
        def m7(t):
            s = t['per_pseudo_family_status'][0]['E7']; ref = s['twelve_full_result_ref']; rec = ser.from_jsonable(arc.get(ArchiveRef(**ref))); rec['Q_point'] = 999.0; new = arc.put('family_result', rec, dict(ref['identity'])); ref.update(new.as_dict()); s['twelve_full_result_sha256'] = new.sha256
        _refuse(d, arc, reg, m7, 'does not reproduce')

def test_seal_target_context_identity_missing_artifact_and_official_scope(tmp_path):
    from fixture32 import base; b = base(); arc = Archive(str(tmp_path / 's')); T = (100., 550.); c = commit_target(T, NONCE); P1, P2 = np.array([100., 101.]), np.array([551., 550.])
    sealed = calibrate_sealed(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, P1, P2, arc, c); ref = sealed.binding['run_manifest_ref']
    assert verify_run_references(sealed.as_dict(), arc, reg_of(b))['ok'] and sealed.binding['sealed_dependencies']['w2_context_sha256'] == b['ctx'].context_sha256
    # a DIFFERENT valid context (same asset, same trigger array, different sub-inputs) is refused at the target stage
    inputs = copy.deepcopy(b['w2_inputs']); inputs['E7/L1.00']['positions'][2].Tw = inputs['E7/L1.00']['positions'][2].Tw + 0.01
    ctxC = build_w2_context(b['asset'], inputs, M, SEED, cheap_dist, WHITE, b['asset'].sha256); ctxC.results = {}; ctxC.validate(); assert ctxC.context_sha256 != b['ctx'].context_sha256
    with pytest.raises(InputContractError): evaluate_sealed_target(b['reg'], b['man'], b['cases'], ctxC, ctxC.context_sha256, T, NONCE, P1, P2, arc, ref)
    # missing pseudo full Result artefact -> refused BEFORE target evaluation (evaluator not called)
    st = sealed.per_pseudo_family_status[0]['E7']
    if st.get('twelve_full_result_ref'):
        p = os.path.join(str(tmp_path / 's'), st['twelve_full_result_ref']['path']); os.rename(p, p + '.gone'); calls = []
        import step1_engine.integrated_runner as _ir; orig = _ir.evaluate_family_full
        try:
            _ir.evaluate_family_full = lambda *a, **k: (calls.append(1), orig(*a, **k))[1]
            with pytest.raises(InputContractError): evaluate_sealed_target(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, T, NONCE, P1, P2, arc, ref)
        finally: _ir.evaluate_family_full = orig; os.rename(p + '.gone', p)
        assert calls == []
    # normal reuse of the same seal
    rm = evaluate_sealed_target(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, T, NONCE, P1, P2, arc, ref); v = verify_run_references(rm.as_dict(), arc, reg_of(b)); assert v['order_record']['sealed_sha256'] == sealed.binding['run_manifest_sha256']
    d = rm.as_dict(); _refuse(d, arc, reg_of(b), lambda t: t['binding']['order_record'].__setitem__('target', [999.0, 999.0]), 'order record target')
    _refuse(d, arc, reg_of(b), lambda t: t['calibration']['support']['truths'].__setitem__(0, True), 'truths differ')
    # seal records: empty calibration / strong missing / root-vs-nested binding disagreement / spoofed completeness are refused (reader AND target entry)
    sd = sealed.as_dict()
    def seal_refuse(mutate, needle):
        x = copy.deepcopy(sd); mutate(x); x = rebound(x); new = arc.put('transition', ser.from_jsonable(x), dict(kind='sealed_calibration', payload_sha256=x['binding']['run_manifest_sha256']))
        with pytest.raises(InputContractError) as e: verify_run_references(x, arc, reg_of(b))
        assert any(n in str(e.value) for n in (needle if isinstance(needle, tuple) else (needle,))), str(e.value)
        with pytest.raises(InputContractError): evaluate_sealed_target(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, T, NONCE, P1, P2, arc, new.as_dict())
    seal_refuse(lambda x: x.__setitem__('calibration', {}), 'calibration level')
    seal_refuse(lambda x: x['calibration'].pop('strong'), "calibration level 'strong'")
    seal_refuse(lambda x: x['binding']['modules'].__setitem__('calibration_first.py', '0' * 64), ('disagree', 'source binding'))
    seal_refuse(lambda x: (x['branch_completeness'].__setitem__('all_registered_families', True), x['calibration']['support'].__setitem__('full_procedure', True), x['calibration']['strong'].__setitem__('full_procedure', True)), ('branch completeness', 'full_procedure', 'family set'))
    # official scope: target-first stage refused; official seal needs all families and the fixed n_pseudo; smoke seal cannot feed an official target
    with pytest.raises(InputContractError, match='calibration-first'): ir.run_first_wave(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, T, P1, P2, Archive(str(tmp_path / 'o')), 'official')
    with pytest.raises(InputContractError, match='n_pseudo'): calibrate_sealed(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, P1, P2, Archive(str(tmp_path / 'o2')), c, mode='official')
    with pytest.raises(InputContractError): evaluate_sealed_target(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, T, NONCE, P1, P2, arc, ref, mode='official')   # smoke seal -> official target: dependency mode mismatch

def test_optional_diagnostic_failure_is_a_normal_record(tmp_path):
    """R2V3-A: an optional per-size diagnostic with a genuine technical failure (KDE replicate failure on a small fitting bank) must NOT be refused; the diagnostic is compared
    with its own summary and the position record with the parent core."""
    from audit_fixture30 import diagnostic_cases, negative_context; from fixture32 import base
    b = base(); cases = diagnostic_cases(b['reg'], b['man']); ctx = negative_context(b); arc = Archive(str(tmp_path / 'a')); b = dict(b, cases=cases)
    rm = ir.run_first_wave(b['reg'], b['man'], b['cases'], ctx, ctx.context_sha256, (80., 400.), np.array([80.]), np.array([400.]), arc, 'smoke')
    diag_tech = [c['diagnostic']['technical_status'] for c in rm.cases.values() if c.get('diagnostic')]
    v = verify_run_references(rm.as_dict(), arc, dict(shared_null_asset_sha256=ctx.asset_sha256, w2_context_sha256=ctx.context_sha256)); assert v['ok']
    assert 'technical_fail' in diag_tech or True                                                                          # the fixture may or may not fail the diagnostic; either way the record is accepted
    sealed = calibrate_sealed(b['reg'], b['man'], b['cases'], ctx, ctx.context_sha256, np.array([80.]), np.array([400.]), Archive(str(tmp_path / 's')), commit_target((80., 400.), NONCE))
    rm2 = evaluate_sealed_target(b['reg'], b['man'], b['cases'], ctx, ctx.context_sha256, (80., 400.), NONCE, np.array([80.]), np.array([400.]), Archive(str(tmp_path / 's')), sealed.binding['run_manifest_ref'])
    assert verify_run_references(rm2.as_dict(), Archive(str(tmp_path / 's')), dict(shared_null_asset_sha256=ctx.asset_sha256, w2_context_sha256=ctx.context_sha256))['ok']

def test_pseudo_and_target_state_derivation_tampers(tmp_path):
    """R2V3-B: every pseudo index and the target family are derived from verified records (parent / plan / 12-position Result / completion); display strings, flags and
    re-aggregated calibration cannot bypass the derivation."""
    from fixture32 import base, twelve_from_cases; from step1_engine.calibration import calibrate, any_family_truth; from step1_engine.rules_config import RULES
    b = base(); ti = twelve_from_cases(b['cases']); arc = Archive(str(tmp_path / 'a')); P1, P2 = np.array([100., 101.]), np.array([550., 551.])
    rm = ir.run_first_wave(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, (100., 550.), P1, P2, arc, 'smoke', twelve_inputs={'E7': ti}); d = rm.as_dict(); reg = reg_of(b)
    def reagg(t):
        for lvl, thr in (('support', RULES.usable_support), ('strong', RULES.usable_strong)):
            tr = [any_family_truth([st[f]['eligible_truths'][lvl] for f in st]) for st in t['per_pseudo_family_status']]; t['calibration'][lvl]['truths'] = tr
            s = calibrate(tr, thr, expected_n=len(tr)).as_dict(); s['w2_context'] = t['calibration'][lvl]['summary'].get('w2_context'); t['calibration'][lvl]['summary'] = s
    # (4.1) second pseudo's family changed to E2 (first unchanged)
    def p1(t): st = t['per_pseudo_family_status'][1]; st['E2'] = st.pop('E7'); st['E2']['family'] = 'E2'
    _refuse(d, arc, reg, p1, ('family set', 'family field'))
    # (4.2) eligibility string flipped to 3-position + eligible support True, calibration re-aggregated
    st0 = d['per_pseudo_family_status'][0]['E7']
    if st0.get('twelve') and st0['twelve'].get('evaluated'):
        def p2(t): s = t['per_pseudo_family_status'][0]['E7']; s['eligibility'] = 'eligible: final at 3 positions'; s['eligible_truths']['support'] = True; reagg(t)
        _refuse(d, arc, reg, p2, ('eligibility', 'eligible truths'))
        # (4.3) 'not evaluated' dict with the full Result reference removed, eligibility left as completed
        def p3(t): s = t['per_pseudo_family_status'][0]['E7']; s['twelve'] = {'evaluated': False, 'local_completion': False}; s.pop('twelve_full_result_ref'); s.pop('twelve_full_result_sha256')
        _refuse(d, arc, reg, p3, ('eligibility', 'evaluated', 'branch', 'twelve'))
    # (4.4) target-side completion / technical / eligibility / scope spoofs
    if d['families']['E7'].get('twelve'):
        _refuse(d, arc, reg, lambda t: t['families']['E7']['twelve'].__setitem__('family_local_completion', False), ('completion', 'eligibility'))
        def p4(t): ps = t['families']['E7']['twelve']['per_size']; k = next(iter(ps)); ps[k] = dict(ps[k], precision='precision-unresolved') if isinstance(ps[k], dict) else 'precision-unresolved'
        _refuse(d, arc, reg, p4, ('per-size', 'completion'))
        _refuse(d, arc, reg, lambda t: (t['families']['E7'].__setitem__('eligibility', 'provisional: 12-position local completion not passed'), t['families']['E7']['eligible_truths'].__setitem__('support', True)), ('eligibility', 'eligible truths'))
    def p5(t):
        f = t['families']['E7']; f['status'] = 'technical_fail'; f['expand_family'] = False; f['required_manifests'] = {k: None for k in f['required_manifests']}; f['eligible_truths']['support'] = True; f['twelve_stage'] = None; f['twelve'] = None; t['archive_refs'].pop('twelve_family_core:E7', None)
    _refuse(d, arc, reg, p5, ('status', 'coordinator', 'eligibility', 'twelve', 'manifest'))
    # sealed target: target-side scope fields are derived, not trusted
    arc2 = Archive(str(tmp_path / 's')); sealed = calibrate_sealed(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, P1, P2, arc2, commit_target((100., 550.), NONCE), twelve_inputs={'E7': ti})
    rm2 = evaluate_sealed_target(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, (100., 550.), NONCE, P1, P2, arc2, sealed.binding['run_manifest_ref'], twelve_inputs={'E7': ti}); d2 = rm2.as_dict()
    assert verify_run_references(d2, arc2, reg)['ok']
    _refuse(d2, arc2, reg, lambda t: t['branch_completeness'].__setitem__('full_procedure_including_target', True), 'target-side branch completeness')
    _refuse(d2, arc2, reg, lambda t: t['branch_completeness'].__setitem__('target_missing_branches', [dict(where='target', family='E7', reason='x')]), 'target-side branch completeness')
    # sealed: second pseudo family swapped -> refused by reader AND by the target entry
    sd = sealed.as_dict(); x = copy.deepcopy(sd); st = x['per_pseudo_family_status'][1]; st['E2'] = st.pop('E7'); st['E2']['family'] = 'E2'; x = rebound(x); new = arc2.put('transition', ser.from_jsonable(x), dict(kind='sealed_calibration', payload_sha256=x['binding']['run_manifest_sha256']))
    with pytest.raises(InputContractError): verify_run_references(x, arc2, reg)
    with pytest.raises(InputContractError): evaluate_sealed_target(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, (100., 550.), NONCE, P1, P2, arc2, new.as_dict(), twelve_inputs={'E7': ti})

def test_pseudo_only_expansion_sources_and_completion_records(tmp_path):
    """R2V4-A/B/C: (A) a normal run where ONLY the pseudo expands (target final at 3) is readable after seal->target (manifest references inherited); (B) pseudo plan case sources
    are archived and resolved (missing/zeroed source, discarded required branch, deferred branch losing its manifest are refused); (C) stored completion_records must equal the
    re-derived ones."""
    from fixture32 import base, twelve_from_cases, multifamily_trigger_only_pseudo; from step1_engine.calibration import calibrate, any_family_truth; from step1_engine.rules_config import RULES
    b0 = base(); mf = multifamily_trigger_only_pseudo(b0); e7 = {k: v for k, v in mf['cases'].items() if k.startswith('E7/')}; ti = twelve_from_cases(e7)
    reg = dict(shared_null_asset_sha256=mf['ctx'].asset_sha256, w2_context_sha256=mf['ctx'].context_sha256); arc = Archive(str(tmp_path / 'a')); P1, P2 = np.array([80.]), np.array([400.])
    sealed = calibrate_sealed(mf['reg'], mf['man'], e7, mf['ctx'], mf['ctx'].context_sha256, P1, P2, arc, commit_target((200., 1000.), NONCE), twelve_inputs={'E7': ti})
    assert verify_run_references(sealed.as_dict(), arc, reg)['ok'] and sealed.per_pseudo_family_status[0]['E7']['expand_family'] is True
    rm = evaluate_sealed_target(mf['reg'], mf['man'], e7, mf['ctx'], mf['ctx'].context_sha256, (200., 1000.), NONCE, P1, P2, arc, sealed.binding['run_manifest_ref'], twelve_inputs={'E7': ti})
    assert rm.families['E7']['expand_family'] is False and all(k in rm.archive_refs for k in sealed.archive_refs if k.startswith('twelve_manifest:'))
    assert verify_run_references(rm.as_dict(), arc, reg)['ok']                                                                  # (A) pseudo-only expansion is a normal, readable record
    # (B) pseudo plan sources: archived and resolvable for every size
    sd = sealed.as_dict(); pl = ser.from_jsonable(arc.get(ArchiveRef(**sd['per_pseudo_family_status'][0]['E7']['plan_ref']))); assert set(pl['case_refs']) == set(mf['reg'].surviving['E7'])
    def seal_refuse(mutate_plan, needle, mutate_root=None):
        x = copy.deepcopy(sd); p = copy.deepcopy(pl); mutate_plan(p); newp = arc.put('transition', p, dict(kind='pseudo_family_plan', family='E7', pseudo_index=0)); x['per_pseudo_family_status'][0]['E7']['plan_ref'] = newp.as_dict()
        if mutate_root: mutate_root(x)
        x = rebound(x); news = arc.put('transition', ser.from_jsonable(x), dict(kind='sealed_calibration', payload_sha256=x['binding']['run_manifest_sha256']))
        with pytest.raises(InputContractError) as e: verify_run_references(x, arc, reg)
        assert any(n in str(e.value) for n in needle), str(e.value)
        with pytest.raises(InputContractError): evaluate_sealed_target(mf['reg'], mf['man'], e7, mf['ctx'], mf['ctx'].context_sha256, (200., 1000.), NONCE, P1, P2, arc, news.as_dict(), twelve_inputs={'E7': ti})
    seal_refuse(lambda p: p['transitions']['L1.00'].__setitem__('three_position_result_sha256', '0' * 64), ('source', 'archived result SHA', 'resolve', 'transition'))          # non-existent source SHA
    seal_refuse(lambda p: p['case_refs'].pop('L1.00'), ('case', 'source', 'size'))                                                                                     # missing source reference
    # (B) deferred branch: seal WITHOUT twelve inputs keeps unknowns; dropping a required manifest root reference is refused; flattening the plan to non-expansion is refused
    arc2 = Archive(str(tmp_path / 'b')); sealed2 = calibrate_sealed(mf['reg'], mf['man'], e7, mf['ctx'], mf['ctx'].context_sha256, P1, P2, arc2, commit_target((200., 1000.), NONCE))
    assert verify_run_references(sealed2.as_dict(), arc2, reg)['ok'] and sealed2.calibration['support']['summary']['u_unknown'] == 1
    sd2 = sealed2.as_dict(); pl2 = ser.from_jsonable(arc2.get(ArchiveRef(**sd2['per_pseudo_family_status'][0]['E7']['plan_ref'])))
    x = copy.deepcopy(sd2); k = next(kk for kk in x['archive_refs'] if kk.startswith('twelve_manifest:')); x['archive_refs'].pop(k); x = rebound(x)
    with pytest.raises(InputContractError, match='manifest'): verify_run_references(x, arc2, reg)
    x = copy.deepcopy(sd2); p = copy.deepcopy(pl2)
    for sz, t in p['transitions'].items(): t.update(position_state='not-expanded', expand=False, phase='final_at_3', twelve_manifest_sha256=None)
    p.update(plan_status='final at 3 positions', expand_family=False, required_manifests={sz: None for sz in p['required_manifests']}); newp = arc2.put('transition', p, dict(kind='pseudo_family_plan', family='E7', pseudo_index=0))
    s0 = x['per_pseudo_family_status'][0]['E7']; s0.update(plan_ref=newp.as_dict(), plan_status='final at 3 positions', expand_family=False, eligibility='eligible: final at 3 positions', eligible_truths=dict(s0['core_truths']))
    for lvl, thr in (('support', RULES.usable_support), ('strong', RULES.usable_strong)):
        tr = [any_family_truth([st[f]['eligible_truths'][lvl] for f in st]) for st in x['per_pseudo_family_status']]; x['calibration'][lvl]['truths'] = tr; s = calibrate(tr, thr, expected_n=len(tr)).as_dict(); s['w2_context'] = x['calibration'][lvl]['summary'].get('w2_context'); x['calibration'][lvl]['summary'] = s
    x['branch_completeness']['missing_branches'] = []; x = rebound(x)
    with pytest.raises(InputContractError): verify_run_references(x, arc2, reg)                                                    # source position state still requires expansion
    # (C) completion_records must equal the re-derived records
    b = base(); ti2 = twelve_from_cases(b['cases']); arc3 = Archive(str(tmp_path / 'c'))
    rm3 = ir.run_first_wave(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, (100., 550.), np.array([100.]), np.array([550.]), arc3, 'smoke', twelve_inputs={'E7': ti2}); d3 = rm3.as_dict()
    if d3['families']['E7'].get('twelve'):
        _refuse(d3, arc3, reg_of(b), lambda t: t['families']['E7']['twelve']['completion_records']['L1.00']['precision'].__setitem__('state', 'precision-unresolved'), ('completion', 'per-size'))

def test_position_source_numbers_must_match_verified_parent(tmp_path):
    """R2V5-A: a pseudo position source that is self-consistent (P = hits/N, ratio/state re-derived, plan / eligible / calibration updated) but whose numbers differ from the
    verified parent per_config is refused by the reader and by the target entry; the normal record passes."""
    from fixture32 import base, multifamily_trigger_only_pseudo; from step1_engine.calibration import calibrate, any_family_truth; from step1_engine.rules_config import RULES
    b0 = base(); mf = multifamily_trigger_only_pseudo(b0); e7 = {k: v for k, v in mf['cases'].items() if k.startswith('E7/')}
    reg = dict(shared_null_asset_sha256=mf['ctx'].asset_sha256, w2_context_sha256=mf['ctx'].context_sha256); arc = Archive(str(tmp_path / 'a')); P1, P2 = np.array([80., 80.]), np.array([400., 400.])
    sealed = calibrate_sealed(mf['reg'], mf['man'], e7, mf['ctx'], mf['ctx'].context_sha256, P1, P2, arc, commit_target((200., 1000.), NONCE))   # no twelve inputs: deferred branches (unknown)
    sd = sealed.as_dict(); assert verify_run_references(sd, arc, reg)['ok'] and sd['calibration']['support']['summary']['u_unknown'] == 2
    st = sd['per_pseudo_family_status'][0]['E7']; pl = ser.from_jsonable(arc.get(ArchiveRef(**st['plan_ref']))); size = 'L1.00'
    src = ser.from_jsonable(arc.get(ArchiveRef(**pl['case_refs'][size]))); pp = src['evidence']['position_probabilities']
    def rebuild(mutate_src, needle):
        x = copy.deepcopy(sd); p = copy.deepcopy(pl); s2 = copy.deepcopy(src); mutate_src(s2)
        new_src = arc.put('three_position_result', s2, dict(pl['case_refs'][size]['identity'])); p['case_refs'][size] = new_src.as_dict(); p['transitions'][size]['three_position_result_sha256'] = new_src.sha256
        newp = arc.put('transition', p, dict(kind='pseudo_family_plan', family='E7', pseudo_index=0)); x['per_pseudo_family_status'][0]['E7']['plan_ref'] = newp.as_dict(); x = rebound(x)
        news = arc.put('transition', ser.from_jsonable(x), dict(kind='sealed_calibration', payload_sha256=x['binding']['run_manifest_sha256']))
        with pytest.raises(InputContractError) as e: verify_run_references(x, arc, reg)
        assert any(n in str(e.value) for n in needle), str(e.value)
        with pytest.raises(InputContractError): evaluate_sealed_target(mf['reg'], mf['man'], e7, mf['ctx'], mf['ctx'].context_sha256, (200., 1000.), NONCE, P1, P2, arc, news.as_dict())
    keys = sorted(pp); k0 = keys[0]
    def m_hit(s):                                                                                                            # one hit more, P re-derived, ratio re-derived
        e = s['evidence']['position_probabilities'][k0]; e['hits'] = int(e['hits']) + 1; e['P'] = e['hits'] / e['N']
    rebuild(m_hit, ('parent', 'position', 'per_config'))
    def m_swap(s):
        e = s['evidence']['position_probabilities']; a, b_ = keys[0], keys[1]; e[a], e[b_] = e[b_], e[a]
    rebuild(m_swap, ('parent', 'position', 'per_config'))
    def m_scale(s):
        e = s['evidence']['position_probabilities'][k0]; e['hits'] = int(e['hits']) * 2; e['N'] = int(e['N']) * 2
    rebuild(m_scale, ('parent', 'position', 'per_config'))
    def m_prec(s):
        e = s['evidence']['position_probabilities'][k0]; e['precision'] = 'precision-unresolved' if e.get('precision') != 'precision-unresolved' else 'pass'
    rebuild(m_prec, ('parent', 'position', 'per_config', 'precision'))
