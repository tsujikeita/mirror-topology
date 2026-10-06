# -*- coding: utf-8 -*-
"""D4C-1 contract tests (engine 0.106.0): archive index cache / deferred index / byte-exact merge; the W2 position-id translation of the common evaluator; family partial +
combiner EQUIVALENCE with the single-process calibrate_sealed record on synthetic four-family banks (ratio-only trigger with the 12-position stage, W2-only trigger, non-trigger,
provisional / missing branch without 12-position inputs, required parent technical failure, optional per-size diagnostic failure); Phase E reader (load_combined_sealed_record,
evaluate_sealed_target on the combined seal == on the single-process seal); refusals (partial as sealed input, missing / duplicate / foreign family, other commitment / campaign /
mode / pseudo order / source, edited status, un-merged archive, E1 with 12-position inputs, official scope). Synthetic banks only (tests/fixture32; no physical covariance)."""
import os, sys, copy, json, hashlib, tempfile, time
import numpy as np
import pytest
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); sys.path[:0] = [P, os.path.join(P, 'tests')]
os.environ.setdefault('AUDIT_WORKDIR', tempfile.mkdtemp(prefix='d4c1_fix_'))
from step1_engine import serialization as ser, twelve_assets as ta, threshold_evaluator as te, __version__
from step1_engine.errors import InputContractError
from step1_engine.archive import Archive, ArchiveRef, merge_archives
from step1_engine.calibration_first import calibrate_sealed, commit_target, load_sealed_record, evaluate_sealed_target
from step1_engine.d4c1_partial import (calibrate_family_partial, combine_family_partials, strip_provenance, verify_partial_record, load_combined_sealed_record, load_partial_record, _payload_sha, PARTIAL_KIND, PARTIAL_SCHEMA)
from step1_engine.checkpoint import MODULES, module_shas
from step1_engine.rules_config import RULES
from step1_engine.truth import TECH, UNKNOWN
from step1_engine.w2_context import build_w2_context
from runner_fixture import M, SEED, cheap_dist, WHITE
from audit_fixture30 import diagnostic_cases

sha = lambda b: hashlib.sha256(b).hexdigest()
FAMS = ('E1', 'E2', 'E7', 'E8')


# ------------------------------------------------------------------------------------------------------------------------------------------- archive
def _put_seq(ar, n, tag='probe'):
    return [ar.put('transition', dict(kind='x', tag=tag, payload=list(range(50)), i=i), dict(kind=tag, i=i)) for i in range(n)]


def test_archive_deferred_index_identical_bytes_and_cache_invalidation(tmp_path):
    a1 = Archive(str(tmp_path / 'imm')); r1 = _put_seq(a1, 40)
    with Archive(str(tmp_path / 'def'), deferred_index=True, flush_every=16) as a2:
        r2 = _put_seq(a2, 40); assert a2.pending == 40 - 32 and a2.get(r2[-1])['i'] == 39            # pending entries are visible to get()
    assert a2.pending == 0 and open(a1.index_path, 'rb').read() == open(a2.index_path, 'rb').read() and r1 == r2
    # the cache is invalidated when the index file changes on disk (an external edit is seen by the next get / verify_all)
    idx = ser.loads(open(a1.index_path, encoding='utf-8').read()); idx['entries'][0]['bytes'] = 1; open(a1.index_path, 'w', encoding='utf-8').write(ser.dumps(idx))
    with pytest.raises(InputContractError): a1.get(r1[0])
    # deferred entries pending + external change of the index -> conflict, never silently discarded
    a3 = Archive(str(tmp_path / 'def2'), deferred_index=True); r3 = _put_seq(a3, 3); assert a3.pending == 3
    open(a3.index_path, 'w', encoding='utf-8').write(ser.dumps(dict(kind='ArchiveIndex', engine_version=__version__, entries=[])))
    with pytest.raises(InputContractError): a3.get(r3[0])
    assert isinstance(Archive(str(tmp_path / 'f'), flush_every=0), Archive)
    with pytest.raises(InputContractError): Archive(str(tmp_path / 'g'), flush_every=-1)
    with pytest.raises(InputContractError): Archive(str(tmp_path / 'h'), flush_every=True)


def test_archive_merge_byte_exact_idempotent_and_refusals(tmp_path):
    a = Archive(str(tmp_path / 'a')); ra = _put_seq(a, 5, 'A'); b = Archive(str(tmp_path / 'b')); rb = _put_seq(b, 3, 'B') + _put_seq(b, 2, 'A')     # b shares the first two 'A' records with a
    d = Archive(str(tmp_path / 'd')); m1 = merge_archives(d, a); m2 = merge_archives(d, b)
    assert m1 == dict(added=5, already_present=0, source_entries=5) and m2 == dict(added=3, already_present=2, source_entries=5) and d.verify_all()['entries'] == 8
    assert merge_archives(d, a) == dict(added=0, already_present=5, source_entries=5)                                       # idempotent
    for r in ra + rb: assert d.get(r) == (a.get(r) if r in ra else b.get(r))
    with pytest.raises(InputContractError): merge_archives(d, d)
    # same bytes under another identity -> conflict; wrong SHA / non-canonical bytes / missing engine version refused
    c = Archive(str(tmp_path / 'c')); body = open(os.path.join(a.root, ra[0].path), 'rb').read()
    c.import_bytes('transition', ra[0].sha256, dict(kind='A', i=0), body, '0.0.1')
    with pytest.raises(InputContractError): c.import_bytes('transition', ra[0].sha256, dict(kind='Z', i=0), body, '0.0.1')
    with pytest.raises(InputContractError): c.import_bytes('transition', '0' * 64, dict(kind='A', i=1), body, '0.0.1')
    with pytest.raises(InputContractError): c.import_bytes('transition', sha(body + b' '), dict(kind='A', i=1), body + b' ', '0.0.1')
    with pytest.raises(InputContractError): c.import_bytes('transition', ra[1].sha256, dict(kind='A', i=1), open(os.path.join(a.root, ra[1].path), 'rb').read(), '')
    e = Archive(str(tmp_path / 'e')); src = Archive(str(tmp_path / 'src')); rs = _put_seq(src, 2, 'S'); p = os.path.join(src.root, rs[0].path); raw = open(p, 'rb').read(); open(p, 'wb').write(raw[:-1] + b' ')
    with pytest.raises(InputContractError): merge_archives(e, src)                                                               # a corrupted source record never crosses


@pytest.mark.parametrize('deferred', [False, True])
@pytest.mark.parametrize('via', ['put', 'import_bytes'])
def test_archive_identity_isolation_edited_ref_rejected(tmp_path, deferred, via):
    """R-D4C1-A1: the returned ArchiveRef.identity never aliases the trusted cache: an edited ref (top level AND nested) is rejected by get, the original ref still resolves, and a
    later put / flush writes the ORIGINAL identity to disk."""
    ar = Archive(str(tmp_path / 'a'), deferred_index=deferred); ident = {'kind': 'original', 'nested': {'n': 1}}
    if via == 'put': ref = ar.put('transition', {'x': 1}, ident)
    else:
        src = Archive(str(tmp_path / 'src')); r0 = src.put('transition', {'x': 1}, ident); body = open(os.path.join(src.root, r0.path), 'rb').read(); ref = ar.import_bytes('transition', r0.sha256, ident, body, '0.0.1')
    orig = ArchiveRef(ref.kind, ref.sha256, ref.path, {'kind': 'original', 'nested': {'n': 1}})
    ident['kind'] = 'caller-edited'                                                                               # the caller's own dict is not the cache either
    ref.identity['kind'] = 'modified'; ref.identity['nested']['n'] = 2
    with pytest.raises(InputContractError, match='identity differ'): ar.get(ref)
    assert ar.get(orig) == {'x': 1}
    ar.put('transition', {'x': 2}, {'kind': 'other'}); ar.flush()
    on_disk = ser.loads(open(ar.index_path, encoding='utf-8').read())['entries']; assert on_disk[0]['identity'] == {'kind': 'original', 'nested': {'n': 1}} and len(on_disk) == 2
    ents = ar._entries(); ents[0]['identity']['kind'] = 'x'; assert ar.get(orig) == {'x': 1} and ar.verify_all()['ok']                  # _entries() hands out copies
    with pytest.raises(InputContractError): ar.get(ref)


def test_archive_flush_conflict_detected_before_overwrite(tmp_path):
    """R-D4C1-A2: with entries pending, an external change of the index (a second Archive object writing a valid entry) is a conflict at flush / normal context exit as well as at
    get; nothing is overwritten and the external entry stays resolvable."""
    root = str(tmp_path / 'r'); A = Archive(root, deferred_index=True); ra = A.put('transition', {'a': 1}, {'k': 'A'}); assert A.pending == 1
    B = Archive(root); rb = B.put('transition', {'b': 1}, {'k': 'B'})
    with pytest.raises(InputContractError, match='pending'): A.flush()
    with pytest.raises(InputContractError, match='pending'):
        with A: pass
    with pytest.raises(InputContractError, match='pending'): A.get(ra)
    C = Archive(root); assert C.get(rb) == {'b': 1} and len(C._entries()) == 1
    with pytest.raises(InputContractError): C.get(ra)                                                              # A's record file exists but is not indexed (re-indexed by an identical put)
    assert C.put('transition', {'a': 1}, {'k': 'A'}) == ra and C.get(ra) == {'a': 1} and len(C._entries()) == 2
    # the automatic flush_every path is covered by the same guard: pending entries + external change -> conflict at the next put
    D = Archive(str(tmp_path / 'd'), deferred_index=True, flush_every=2); D.put('transition', {'d': 1}, {'k': 'D'}); Archive(str(tmp_path / 'd')).put('transition', {'e': 1}, {'k': 'E'})
    with pytest.raises(InputContractError, match='pending'): D.put('transition', {'d': 2}, {'k': 'D2'})


def test_module_registered_and_version():
    assert 'd4c1_partial.py' in MODULES and __version__ == '0.110.0' and set(module_shas()) == set(MODULES)
    inv = json.load(open(os.path.join(P, 'B2_completion_inventory.json'))); assert inv['modules'] == module_shas() and inv['engine_version'] == __version__


# ------------------------------------------------------------------------------------------------------------------------------------------- fixtures
@pytest.fixture(scope='module')
def fx():
    from fixture32 import base, multifamily_trigger_only_pseudo, twelve_from_cases
    b = base(); m = multifamily_trigger_only_pseudo(b); t12 = twelve_from_cases(b['cases'])
    return dict(b=b, m=m, t12=t12, asset=ta.build_twelve_assets(m['reg'], ['E7']))


def _ctx_with(b, m, spec_of):
    """A four-family W2 context whose non-E1 cases take the given base spec per key (default: E7/L1.50 = non-trigger)."""
    specs = {k: copy.deepcopy(b['w2_inputs'][spec_of(k)]) for k in m['cases'] if not k.startswith('E1/')}
    ctx = build_w2_context(b['asset'], specs, M, SEED, cheap_dist, WHITE, b['asset'].sha256); ctx.results = {}; ctx.validate(); return ctx


def _run_both(fx, root, cases, ctx, xs, ys, twelve_inputs, C='c' * 64, campaign=dict(id='test-campaign'), mode='smoke', asset=None, single_kw=None):
    """single-process sealed calibration + one partial per family (separate deferred archives) -> merge -> combine; returns everything."""
    reg, man = fx['m']['reg'], fx['m']['man']; asset = fx['asset'] if asset is None else asset
    A1 = Archive(os.path.join(root, 'single'), deferred_index=True); single = calibrate_sealed(reg, man, cases, ctx, ctx.context_sha256, xs, ys, A1, C, twelve_inputs=twelve_inputs, twelve_assets=asset, expected_twelve_assets_sha256=asset.sha256, require_all_families=True, **(single_kw or {})); A1.flush()
    parts = {}
    for fam in reg.surviving:
        ar = Archive(os.path.join(root, f'part_{fam}'), deferred_index=True); fc = {k: v for k, v in cases.items() if k.startswith(fam + '/')}
        parts[fam] = (calibrate_family_partial(reg, man, fam, fc, ctx, ctx.context_sha256, xs, ys, ar, C, mode=mode, campaign=campaign, twelve_inputs=(twelve_inputs or {}).get(fam), twelve_assets=asset, expected_twelve_assets_sha256=asset.sha256), ar)
    AC = Archive(os.path.join(root, 'combined'), deferred_index=True)
    for fam, (p, ar) in parts.items(): merge_archives(AC, ar)
    comb = combine_family_partials(reg, man, [p.as_dict() for p, _ in parts.values()], AC); AC.flush()
    return dict(single=single, A1=A1, parts=parts, AC=AC, comb=comb, reg=reg, man=man, C=C)


def _assert_equivalent(r):
    s1, s2 = strip_provenance(r['single'].as_dict()), strip_provenance(r['comb'].as_dict())
    assert ser.dumps(s1) == ser.dumps(s2), [k for k in s1 if ser.dumps(s1[k]) != ser.dumps(s2[k])]
    assert r['single'].calibration == r['comb'].calibration and r['single'].per_pseudo_family_status == r['comb'].per_pseudo_family_status and r['single'].branch_completeness == r['comb'].branch_completeness and r['single'].archive_refs == r['comb'].archive_refs
    assert r['single'].binding['run_manifest_sha256'] != r['comb'].binding['run_manifest_sha256'] and set(r['comb'].binding['combiner']['partials']) == set(FAMS)      # provenance is the only difference
    # the combined seal passes the Phase E reader with the registered-context check and every partial re-verifies on the merged archive
    d = load_combined_sealed_record(r['AC'], r['comb'].binding['run_manifest_ref'], registered=dict(shared_null_asset_sha256=r['comb'].w2_asset_sha256, w2_context_sha256=r['comb'].w2_context_sha256, registry_sha256=r['reg'].registry_sha256, twelve_assets_sha256=r['comb'].binding['twelve_assets_sha256']))
    assert d['_verification']['ok'] and d['_verification']['registered_context_ok'] and d['_verification']['combined'] and d['_sha256'] == r['comb'].binding['run_manifest_sha256']
    for fam, (p, ar) in r['parts'].items():
        v = verify_partial_record(p.as_dict(), r['AC']); assert v['ok'] and v['family'] == fam and v['n_pseudo'] == len(p.per_pseudo_status)
        assert 'calibration' not in p.as_dict() and p.schema == PARTIAL_SCHEMA and p.kind == PARTIAL_KIND and p.fingerprints['at_gate'] == p.fingerprints['at_end'] and len(p.per_pseudo_diagnostics) == len(p.per_pseudo_status) == len(p.per_pseudo_manifest_keys)
        assert load_partial_record(r['AC'], p.binding['partial_ref'])['binding']['partial_sha256'] == p.binding['partial_sha256'] == _payload_sha(p.as_dict())
    assert r['AC'].verify_all()['ok']


@pytest.fixture(scope='module')
def std(fx, tmp_path_factory):
    """ratio-only trigger (E7 at pseudo 0; 12-position inputs supplied -> evaluated), non-trigger pseudos, E1 eligible at 3; three pseudo pairs."""
    root = str(tmp_path_factory.mktemp('std')); m = fx['m']
    return _run_both(fx, root, m['cases'], m['ctx'], [80., 200., 150.], [400., 1000., 700.], {'E7': fx['t12']})


def test_equivalence_ratio_trigger_with_twelve_stage(std):
    _assert_equivalent(std); r = std
    st = r['comb'].per_pseudo_family_status
    assert st[0]['E7']['expand_family'] and st[0]['E7']['twelve']['evaluated'] and not st[1]['E7']['expand_family'] and st[0]['E1']['eligibility'].startswith('eligible: E1')
    assert r['comb'].branch_completeness == dict(all_registered_families=True, missing_branches=[], note=r['single'].branch_completeness['note']) and all(r['comb'].calibration[l]['full_procedure'] for l in ('support', 'strong'))
    assert r['comb'].calibration['support']['summary']['n'] == 3 and r['comb'].calibration['support']['summary']['threshold'] == RULES.usable_support and r['comb'].calibration['strong']['summary']['threshold'] == RULES.usable_strong
    assert any('twelve_manifest:E7/' in k for k in r['comb'].archive_refs) and r['parts']['E7'][0].per_pseudo_manifest_keys[0] and r['parts']['E7'][0].per_pseudo_manifest_keys[1] == []
    # the diagnostics kept apart from the eligible truths; any_case re-derived from them
    assert set(r['parts']['E7'][0].per_pseudo_diagnostics[0]) == set(r['reg'].surviving['E7']) and r['comb'].calibration['support']['any_case_core_diagnostic']['truths'] == r['single'].calibration['support']['any_case_core_diagnostic']['truths']


@pytest.fixture(scope='module')
def real_commit(fx, tmp_path_factory):
    """same inputs as std but with a REAL commitment so the Phase E target stage can be exercised on both seals (two pseudo pairs)."""
    root = str(tmp_path_factory.mktemp('rc')); m = fx['m']; nonce = 'phase-e-test-nonce-0001'; t = (200., 1000.)
    r = _run_both(fx, root, m['cases'], m['ctx'], [80., 200.], [400., 1000.], {'E7': fx['t12']}, C=commit_target(t, nonce)); r.update(nonce=nonce, t=t, cases=m['cases'], ctx=m['ctx'], root=root); return r


def test_phase_e_target_with_real_commitment(real_commit, fx):
    r = real_commit; _assert_equivalent(r); reg, man = r['reg'], r['man']; a = fx['asset']
    kw = dict(twelve_inputs={'E7': fx['t12']}, twelve_assets=a, expected_twelve_assets_sha256=a.sha256, require_all_families=True)
    T1 = evaluate_sealed_target(reg, man, r['cases'], r['ctx'], r['ctx'].context_sha256, r['t'], r['nonce'], [80., 200.], [400., 1000.], r['A1'], r['single'].binding['run_manifest_ref'], **kw)
    T2 = evaluate_sealed_target(reg, man, r['cases'], r['ctx'], r['ctx'].context_sha256, r['t'], r['nonce'], [80., 200.], [400., 1000.], r['AC'], r['comb'].binding['run_manifest_ref'], **kw)
    d1, d2 = ser.from_jsonable(T1.as_dict()), ser.from_jsonable(T2.as_dict())
    for d in (d1, d2):
        d['binding'] = {k: v for k, v in d['binding'].items() if k not in ('sealed_calibration', 'order_record', 'run_manifest_sha256', 'run_manifest_file_sha256', 'run_manifest_ref')}
    assert ser.dumps(d1) == ser.dumps(d2) and T1.families == T2.families and T1.cases == T2.cases and T1.calibration == T2.calibration and T2.binding['sealed_calibration']['sha256'] == r['comb'].binding['run_manifest_sha256'] and T2.binding['order_record']['commitment'] == r['C']
    # wrong nonce / a partial as the sealed reference are refused before any target evaluation
    with pytest.raises(InputContractError): evaluate_sealed_target(reg, man, r['cases'], r['ctx'], r['ctx'].context_sha256, r['t'], 'wrong-nonce-0000000000', [80., 200.], [400., 1000.], r['AC'], r['comb'].binding['run_manifest_ref'], **kw)
    with pytest.raises(InputContractError): evaluate_sealed_target(reg, man, r['cases'], r['ctx'], r['ctx'].context_sha256, r['t'], r['nonce'], [80., 200.], [400., 1000.], r['AC'], r['parts']['E7'][0].binding['partial_ref'], **kw)
    with pytest.raises(InputContractError): load_sealed_record(r['AC'], r['parts']['E2'][0].binding['partial_ref'])
    with pytest.raises(InputContractError): load_combined_sealed_record(r['A1'], r['single'].binding['run_manifest_ref'])      # a single-process seal carries no combiner provenance


@pytest.fixture(scope='module')
def w2only(fx, tmp_path_factory):
    """E7/L1.00 takes the base W2 spec whose decision is trigger True (W2-only branch), the other cases the non-trigger spec; 12-position inputs supplied."""
    b, m = fx['b'], fx['m']; ctx = _ctx_with(b, m, lambda k: 'E7/L1.00' if k == 'E7/L1.00' else 'E7/L1.50'); assert ctx.decisions['E7/L1.00'].trigger is True
    return _run_both(fx, str(tmp_path_factory.mktemp('w2only')), m['cases'], ctx, [200.], [1000.], {'E7': fx['t12']})


def test_equivalence_w2_only_trigger(w2only):
    r = w2only; _assert_equivalent(r)
    st = r['comb'].per_pseudo_family_status[0]['E7']; assert st['expand_family'] and st['twelve']['evaluated']


def test_equivalence_missing_branch_without_twelve_inputs(fx, tmp_path):
    """ratio-only trigger (E7, pseudo 0) WITHOUT 12-position inputs: provisional unknown, missing branch, full_procedure False — identical in both paths (smoke mode only)."""
    m = fx['m']; r = _run_both(fx, str(tmp_path), m['cases'], m['ctx'], [80., 200.], [400., 1000.], None); _assert_equivalent(r)
    assert r['comb'].branch_completeness['missing_branches'] == [dict(where='pseudo[0]', family='E7', reason='triggered 12-position stage not evaluated')] and not r['comb'].calibration['support']['full_procedure']
    assert r['comb'].per_pseudo_family_status[0]['E7']['eligible_truths']['support'] == UNKNOWN and r['comb'].calibration['support']['summary']['u_unknown'] >= 1


def test_equivalence_required_parent_technical_failure(fx, tmp_path):
    """E7 replaced by the diagnostic fixture with ALL sizes needing a CI (required parent technical failure): TECH propagates to the aggregation (no usable value) in both paths."""
    from fixture32 import twelve_from_cases
    m = fx['m']; cases = dict(m['cases']); d = diagnostic_cases(m['reg'], m['man'], True); cases.update(d); t12 = twelve_from_cases(d)
    r = _run_both(fx, str(tmp_path), cases, m['ctx'], [80.], [400.], {'E7': t12}); _assert_equivalent(r)
    assert set(r['comb'].per_pseudo_family_status[0]['E7']['eligible_truths'].values()) == {TECH} and r['comb'].calibration['support']['summary']['status'] == 'technical_fail' and r['comb'].calibration['support']['summary']['usable'] == TECH


def test_equivalence_optional_diagnostic_failure_not_a_veto(fx, tmp_path):
    """E7 replaced by the diagnostic fixture whose per-size standalone diagnostic fails while the required parent is fine: eligible truths stay informative; identical in both paths."""
    from fixture32 import twelve_from_cases
    m = fx['m']; cases = dict(m['cases']); d = diagnostic_cases(m['reg'], m['man'], False); cases.update(d); t12 = twelve_from_cases(d)
    r = _run_both(fx, str(tmp_path), cases, m['ctx'], [80.], [400.], {'E7': t12}); _assert_equivalent(r)
    st = r['comb'].per_pseudo_family_status[0]['E7']; assert not st['core_technical'] and st['eligible_truths']['support'] is not TECH
    assert r['comb'].calibration['support']['summary']['technical_fail'] == 0 and any(v == TECH for dg in r['parts']['E7'][0].per_pseudo_diagnostics[0].values() for v in dg.values())


# ------------------------------------------------------------------------------------------------------------------------------------------- refusals
def _edited(p, fn):
    d = ser.from_jsonable(ser.to_jsonable(p.as_dict())); fn(d); d['binding']['partial_sha256'] = _payload_sha(d); return d


def test_combiner_refusals(std):
    r = std; reg, man, AC = r['reg'], r['man'], r['AC']; P = {f: p.as_dict() for f, (p, _) in r['parts'].items()}; others = lambda f: [P[g] for g in FAMS if g != f]
    for bad, msg in [([P[f] for f in FAMS if f != 'E8'], 'missing'), ([P[f] for f in FAMS] + [P['E2']], 'duplicate'), ([], 'no partials')]:
        with pytest.raises(InputContractError, match=msg): combine_family_partials(reg, man, bad, AC, verify_references=False)
    def other_commit(d): d['thresholds']['target_commitment'] = '0' * 64; d['binding']['partial_dependencies']['target_commitment'] = '0' * 64
    def other_campaign(d): d['campaign'] = dict(id='another'); d['binding']['partial_dependencies']['campaign'] = dict(id='another')
    def reorder(d): d['thresholds']['pseudo']['T1'] = d['thresholds']['pseudo']['T1'][::-1]; d['thresholds']['pseudo']['T2'] = d['thresholds']['pseudo']['T2'][::-1]
    def reorder_rehash(d):
        reorder(d); a = np.asarray(d['thresholds']['pseudo']['T1'], float); b = np.asarray(d['thresholds']['pseudo']['T2'], float)
        d['thresholds']['pseudo']['sha256_T1'] = sha(np.ascontiguousarray(a).tobytes()); d['thresholds']['pseudo']['sha256_T2'] = sha(np.ascontiguousarray(b).tobytes()); d['binding']['partial_dependencies']['pseudo'] = dict(n=len(a), sha256_T1=d['thresholds']['pseudo']['sha256_T1'], sha256_T2=d['thresholds']['pseudo']['sha256_T2'])
    def other_mode(d): d['mode'] = 'official'; d['binding']['partial_dependencies']['mode'] = 'official'
    def other_ctx(d): d['w2_context_sha256'] = '1' * 64; d['binding']['partial_dependencies']['w2_context_sha256'] = '1' * 64
    def other_source(d): d['binding']['modules'] = dict(d['binding']['modules'], **{'archive.py': '2' * 64}); d['binding']['partial_dependencies']['source_binding']['modules'] = d['binding']['modules']
    def other_family_field(d): d['family'] = 'E8'
    def other_sizes(d): d['sizes'] = d['sizes'][:2]
    def truth_promoted(d): d['per_pseudo_status'][0]['eligible_truths']['support'] = True
    def twelve_asset_dropped(d): d['binding']['twelve_assets_sha256'] = None; d['binding']['partial_dependencies']['twelve_assets_sha256'] = None
    for fn, msg in [(other_commit, 'common identity'), (other_campaign, 'common identity'), (reorder, 'pseudo columns differ'), (reorder_rehash, 'common identity'), (other_mode, 'common identity'), (other_ctx, 'common identity'), (other_source, 'common identity'), (other_sizes, 'sizes differ'), (twelve_asset_dropped, 'common identity')]:
        with pytest.raises(InputContractError, match=msg): combine_family_partials(reg, man, [_edited(r['parts']['E2'][0], fn)] + others('E2'), AC, verify_references=False)
    with pytest.raises(InputContractError): combine_family_partials(reg, man, [_edited(r['parts']['E2'][0], other_family_field)] + others('E2'), AC, verify_references=False)           # family / dependencies disagree
    # a promoted eligible truth (unknown/False -> True) passes the shape but is caught by the run-reader re-derivation of the combined record and by verify_partial_record
    bad = _edited(r['parts']['E2'][0], truth_promoted)
    with pytest.raises(InputContractError): combine_family_partials(reg, man, [bad] + others('E2'), AC, verify_references=True)
    with pytest.raises(InputContractError): verify_partial_record(bad, AC)
    # a byte-edited status without re-stamp -> payload SHA mismatch; a partial whose records are not in the archive (un-merged) -> reader failure
    d = ser.from_jsonable(ser.to_jsonable(P['E7'])); d['per_pseudo_status'][0]['plan_status'] = 'x'
    with pytest.raises(InputContractError, match='payload SHA'): combine_family_partials(reg, man, [d] + others('E7'), AC, verify_references=False)
    with pytest.raises(InputContractError): combine_family_partials(reg, man, [P[f] for f in FAMS], Archive(tempfile.mkdtemp()), verify_references=True)
    # the combined record's provenance must resolve: a sealed record re-stamped with a foreign partial SHA is refused by the Phase E reader
    with pytest.raises(InputContractError): load_combined_sealed_record(AC, r['parts']['E1'][0].binding['partial_ref'])
    # official-mode combination guards (all four partials re-stamped as official): the fixed n_pseudo, the campaign dict, the 12-position fingerprints and the official gate mode are required
    def officialise(d): d['mode'] = 'official'; d['binding']['partial_dependencies']['mode'] = 'official'; d['gate']['mode'] = 'official'
    offs = [_edited(p, officialise) for p, _ in r['parts'].values()]
    with pytest.raises(InputContractError, match='n_pseudo'): combine_family_partials(reg, man, offs, AC, verify_references=False)
    import step1_engine.d4c1_partial as dp
    RULES_ORIG = dp.RULES
    class _R:
        n_pseudo = len(offs[0]['thresholds']['pseudo']['T1']); usable_support = dp.RULES.usable_support; usable_strong = dp.RULES.usable_strong
    dp.RULES = _R
    try:
        def no_campaign(d): d['campaign'] = None; d['binding']['partial_dependencies']['campaign'] = None
        with pytest.raises(InputContractError, match='campaign'): combine_family_partials(reg, man, [_edited(p, lambda d: (officialise(d), no_campaign(d))) for p, _ in r['parts'].values()], AC, verify_references=False)
        def drop_twelve(d): d['fingerprints']['at_gate'] = {k: v for k, v in d['fingerprints']['at_gate'].items() if not k.startswith('twelve:')}; d['fingerprints']['at_end'] = dict(d['fingerprints']['at_gate']); d['binding']['partial_dependencies']['fingerprints_at_gate'] = dict(d['fingerprints']['at_gate'])
        with pytest.raises(InputContractError, match='lacks the 12-position inputs'): combine_family_partials(reg, man, [_edited(p, lambda d: (officialise(d), drop_twelve(d) if d['family'] == 'E7' else None)) for p, _ in r['parts'].values()], AC, verify_references=False)
        def smoke_gate(d): d['gate']['mode'] = 'smoke'
        with pytest.raises(InputContractError, match='gate mode'): combine_family_partials(reg, man, [_edited(p, lambda d: (officialise(d), smoke_gate(d) if d['family'] == 'E1' else None)) for p, _ in r['parts'].values()], AC, verify_references=False)
    finally: dp.RULES = RULES_ORIG


def test_partial_entry_refusals(fx, tmp_path):
    reg, man, m = fx['m']['reg'], fx['m']['man'], fx['m']; cases = m['cases']; ctx = m['ctx']; a = fx['asset']; e7 = {k: v for k, v in cases.items() if k.startswith('E7/')}; e1 = {k: v for k, v in cases.items() if k.startswith('E1/')}
    ar = Archive(str(tmp_path / 'a')); kw = dict(twelve_assets=a, expected_twelve_assets_sha256=a.sha256)
    with pytest.raises(InputContractError, match='commitment'): calibrate_family_partial(reg, man, 'E7', e7, ctx, ctx.context_sha256, [80.], [400.], ar, 'zz', mode='smoke', **kw)
    with pytest.raises(InputContractError, match='exactly one family'): calibrate_family_partial(reg, man, 'E7', dict(e7, **e1), ctx, ctx.context_sha256, [80.], [400.], ar, 'c' * 64, mode='smoke', **kw)
    with pytest.raises(InputContractError, match='surviving sizes'): calibrate_family_partial(reg, man, 'E7', {k: v for k, v in e7.items() if k != 'E7/L1.50'}, ctx, ctx.context_sha256, [80.], [400.], ar, 'c' * 64, mode='smoke', **kw)
    with pytest.raises(InputContractError, match='E1 is observer-homogeneous'): calibrate_family_partial(reg, man, 'E1', e1, ctx, ctx.context_sha256, [80.], [400.], ar, 'c' * 64, mode='smoke', twelve_inputs=fx['t12'], **kw)
    with pytest.raises(InputContractError, match='not a registered family'): calibrate_family_partial(reg, man, 'E9', e7, ctx, ctx.context_sha256, [80.], [400.], ar, 'c' * 64, mode='smoke', **kw)
    with pytest.raises(InputContractError, match='mode'): calibrate_family_partial(reg, man, 'E7', e7, ctx, ctx.context_sha256, [80.], [400.], ar, 'c' * 64, mode='formal', **kw)
    with pytest.raises(InputContractError, match='campaign'): calibrate_family_partial(reg, man, 'E7', e7, ctx, ctx.context_sha256, [80.], [400.], ar, 'c' * 64, mode='smoke', campaign='x', **kw)
    with pytest.raises(InputContractError, match='n_pseudo'): calibrate_family_partial(reg, man, 'E7', e7, ctx, ctx.context_sha256, [80.], [400.], ar, 'c' * 64, mode='official', campaign=dict(id='c'), twelve_inputs=fx['t12'], twelve_assets_receipt='B3_2A_7240c06f255c', **kw)
    with pytest.raises(InputContractError, match='campaign'): calibrate_family_partial(reg, man, 'E7', e7, ctx, ctx.context_sha256, [80.] * RULES.n_pseudo, [400.] * RULES.n_pseudo, ar, 'c' * 64, mode='official', twelve_inputs=fx['t12'], **kw)
    with pytest.raises(InputContractError, match='12-position inputs'): calibrate_family_partial(reg, man, 'E7', e7, ctx, ctx.context_sha256, [80.] * RULES.n_pseudo, [400.] * RULES.n_pseudo, ar, 'c' * 64, mode='official', campaign=dict(id='c'), **kw)
    with pytest.raises(InputContractError, match='twelve-position asset'): calibrate_family_partial(reg, man, 'E7', e7, ctx, ctx.context_sha256, [80.] * RULES.n_pseudo, [400.] * RULES.n_pseudo, ar, 'c' * 64, mode='official', campaign=dict(id='c'), twelve_inputs=fx['t12'])
    with pytest.raises(InputContractError, match='twelve_inputs must cover'): calibrate_family_partial(reg, man, 'E7', e7, ctx, ctx.context_sha256, [80.], [400.], ar, 'c' * 64, mode='smoke', twelve_inputs=dict(size_inputs={'L1.00': fx['t12']['size_inputs']['L1.00']}, position_ids={'L1.00': fx['t12']['position_ids']['L1.00']}), **kw)
    with pytest.raises(InputContractError): calibrate_family_partial(reg, man, 'E7', e7, ctx, '0' * 64, [80.], [400.], ar, 'c' * 64, mode='smoke', **kw)                                           # wrong expected context SHA
    with pytest.raises(InputContractError): calibrate_family_partial(reg, man, 'E7', e7, ctx, ctx.context_sha256, [80.], [400.], ar, 'c' * 64, mode='smoke', twelve_assets=a, expected_twelve_assets_sha256='0' * 64)
    with pytest.raises(InputContractError): calibrate_family_partial(reg, man, 'E7', e7, ctx, ctx.context_sha256, [80.], [400.], ar, 'c' * 64, mode='smoke', expected_twelve_assets_sha256=a.sha256)     # expected SHA without an asset
    assert not os.path.exists(os.path.join(ar.root, 'transition'))                                                                                                                                          # nothing archived by refused entries


# ------------------------------------------------------------------------------------------------------------------------------------------- W2 position-id translation
def test_w2_position_map_translation(fx):
    m, b = fx['m'], fx['b']; ctx = m['ctx']; fm, fn, pmap = m['cases']['E7/L1.00']
    assert te._w2_position_map(ctx, 'E7/L1.00', fm, pmap) == pmap                                                                                  # synthetic manifests: identity (positions 1..3)
    # registered-style manifest positions (configuration ids): translated through the grid identity; suffix rule enforced
    import dataclasses
    class _W:
        def __init__(self, positions): self.manifests = {'E7/L1.00': type('M', (), dict(positions=positions))()}
    e2c = fm.grid_identity['evaluation_to_config']; cfg_pos = [dict(position_id=int(e2c[e])) for e in pmap]
    got = te._w2_position_map(_W(cfg_pos), 'E7/L1.00', fm, pmap); assert got == {e: int(e2c[e]) for e in pmap} and all(got[e] % 100 == pmap[e] for e in pmap)
    with pytest.raises(InputContractError, match='do not correspond'): te._w2_position_map(_W([dict(position_id=int(e2c[e]) + 1) for e in pmap]), 'E7/L1.00', fm, pmap)
    with pytest.raises(InputContractError, match='do not correspond'): te._w2_position_map(_W(cfg_pos), 'E7/L1.00', fm, {e: 4 - v for e, v in pmap.items()})     # wrong observer positions
    g = dataclasses.replace(fm, grid_identity=None)
    with pytest.raises(InputContractError, match='no grid identity'): te._w2_position_map(_W(cfg_pos), 'E7/L1.00', g, pmap)
    # the REGISTERED D-2W context (position_id == config id) is consumable by the evaluator only through this translation (one case, registered loader; sizes must match the registry)
    from step1_engine.d3_profile import twelve_context
    from step1_engine.d4c0_registry import load_registered_w2_context
    try: w2, _ = load_registered_w2_context(P, twelve_context(P))
    except Exception: pytest.skip('registered D4C-0 assets not loadable here')
    pos = {int(p['position_id']) for p in w2.manifests['E7/L1.00'].positions}; assert pos == {int(e2c[e]) for e in pmap} and pos != set(pmap.values())
    with pytest.raises(InputContractError): te._w2_position_map(w2, 'E7/L1.00', g, pmap)
    want = {e: int(e2c[e]) for e in pmap}; assert te._w2_position_map(w2, 'E7/L1.00', fm, pmap) == want


# ------------------------------------------------------------------------------------------------------------------------------------------- verifier mixture margin
def test_verifier_mixture_rounding_margin(w2only):
    """checkpoint._verify_Q_side (engine 0.106.0): the W2-only variant's native 12-position mixture holds a replicate num of 1.0000000000000002 (P @ w rounding); the reader accepts
    it within MIXTURE_TOL (8 ulp) — the combined / single records above were verified with it — while a value beyond the margin, a negative mixture, or a per-configuration
    probability above 1 are still refused."""
    from step1_engine.checkpoint import verify_family_result_dict, MIXTURE_TOL
    import glob
    found = None
    for p in glob.glob(os.path.join(w2only['A1'].root, 'family_result', '*.json')):
        d = ser.loads(open(p, encoding='utf-8').read())
        for side in (d, d.get('native') or {}):
            for s_, v in ((side.get('evidence') or {}).get('per_seed') or {}).items():
                a = np.asarray(v['num'], float)
                if a.size and a.max() > 1.0: found = (d, side is not d, s_, int(np.argmax(a)), float(a.max()))
    assert found is not None, 'the W2-only variant is expected to hold a mixture replicate above 1 by rounding'
    d, native, s_, j, val = found; assert 1.0 < val <= 1.0 + MIXTURE_TOL and verify_family_result_dict(d).startswith('verified')
    def side_of(e): return e['native'] if native else e
    e2 = ser.from_jsonable(ser.to_jsonable(d)); side_of(e2)['evidence']['per_seed'][s_]['num'][j] = 1.0 + 1e-12
    with pytest.raises(InputContractError, match='probability domain'): verify_family_result_dict(e2)
    e3 = ser.from_jsonable(ser.to_jsonable(d)); side_of(e3)['evidence']['per_seed'][s_]['den'][0] = -2 * MIXTURE_TOL
    with pytest.raises(InputContractError, match='probability domain'): verify_family_result_dict(e3)
    e4 = ser.from_jsonable(ser.to_jsonable(d)); k = next(iter(e4['per_config'])); e4['per_config'][k]['P_model'] = float(np.nextafter(1.0, 2.0))
    with pytest.raises(InputContractError): verify_family_result_dict(e4)                                                                    # per-configuration probabilities: no margin
    assert 0 < MIXTURE_TOL < 1e-14


# ------------------------------------------------------------------------------------------------------------------------------------------- plan object stability (R-D4C1-C)
def test_partial_plan_object_stability(fx, tmp_path, monkeypatch):
    """The partial requires the SAME plan objects (`is`) on every first-wave view and parent before the gate and after the last pseudo; a content-identical deepcopy swapped in
    after the evaluator returns (parent fit_plans / plans, a size view's plans, a 12-position view's plans) is rejected although the fingerprints would still agree; an actual
    bank value change is rejected by the fingerprints; the normal run records the sharing summary."""
    import copy as _copy, step1_engine.d4c1_partial as dp
    reg, man, m = fx['m']['reg'], fx['m']['man'], fx['m']; ctx = m['ctx']; a = fx['asset']; e7 = {k: v for k, v in m['cases'].items() if k.startswith('E7/')}; e1 = {k: v for k, v in m['cases'].items() if k.startswith('E1/')}
    kw = dict(mode='smoke', twelve_assets=a, expected_twelve_assets_sha256=a.sha256)
    p = calibrate_family_partial(reg, man, 'E1', e1, ctx, ctx.context_sha256, [80.], [400.], Archive(str(tmp_path / 'ok')), 'c' * 64, **kw)
    assert p.plan_objects['first_wave_shared'] and p.plan_objects['stable_after'] and p.plan_objects['twelve_present'] is False and p.plan_objects['n_objects'] == 8
    p7 = calibrate_family_partial(reg, man, 'E7', e7, ctx, ctx.context_sha256, [80.], [400.], Archive(str(tmp_path / 'ok7')), 'c' * 64, twelve_inputs=fx['t12'], **kw)
    assert p7.plan_objects['twelve_shared'] and p7.plan_objects['twelve_present'] and p7.plan_objects['twelve_shares_first_wave'] is False and p7.plan_objects['n_objects'] == 14      # the synthetic 12-position views carry other (shared) plan objects: allowed in smoke, refused in official
    orig = dp.evaluate_family_full
    def swapper(what):
        def w(reg_, man_, fam_, parent, views, *args, **kw_):
            out = orig(reg_, man_, fam_, parent, views, *args, **kw_)
            if what == 'parent_fit_plans': parent[0].fit_plans = _copy.deepcopy(parent[0].fit_plans)
            if what == 'parent_plans': parent[0].plans = _copy.deepcopy(parent[0].plans)
            if what == 'view_plans': views['L1.20'][1].plans = _copy.deepcopy(views['L1.20'][1].plans)
            if what == 'twelve_plans': args[4]['size_inputs']['L1.00'][0].plans = _copy.deepcopy(args[4]['size_inputs']['L1.00'][0].plans)      # args: (w2, expected, x, y, twelve_inputs)
            return out
        return w
    for what in ('parent_fit_plans', 'parent_plans', 'view_plans'):
        cases = {k: (_copy.copy(v[0]), _copy.copy(v[1]), v[2]) for k, v in e1.items()}                                                  # fresh FamilyInput shells sharing the fixed plan dicts
        monkeypatch.setattr(dp, 'evaluate_family_full', swapper(what)); ar = Archive(str(tmp_path / what))
        with pytest.raises(InputContractError, match='plan objects were replaced'): calibrate_family_partial(reg, man, 'E1', cases, ctx, ctx.context_sha256, [80.], [400.], ar, 'c' * 64, **kw)
        assert not any(e['identity'].get('kind') == PARTIAL_KIND for e in ar._entries())                                                   # per-pseudo evidence may exist; no partial record is issued
    t12 = dict(fx['t12']); t12['size_inputs'] = {s_: (_copy.copy(pair[0]), _copy.copy(pair[1])) for s_, pair in fx['t12']['size_inputs'].items()}
    monkeypatch.setattr(dp, 'evaluate_family_full', swapper('twelve_plans'))
    with pytest.raises(InputContractError, match='plan objects were replaced'): calibrate_family_partial(reg, man, 'E7', e7, ctx, ctx.context_sha256, [80.], [400.], Archive(str(tmp_path / 'tw')), 'c' * 64, twelve_inputs=t12, **kw)
    monkeypatch.setattr(dp, 'evaluate_family_full', orig)
    # before the gate: views that do not share one plan object pair are refused; a copied bank value is refused by the fingerprints after the run
    bad = dict(e1); fm, fn, pm = bad['E1/L1.50']; bad['E1/L1.50'] = (_copy.copy(fm), fn, pm); bad['E1/L1.50'][0].plans = _copy.deepcopy(fm.plans)
    with pytest.raises(InputContractError, match='SAME evaluation / fitting plan objects'): calibrate_family_partial(reg, man, 'E1', bad, ctx, ctx.context_sha256, [80.], [400.], Archive(str(tmp_path / 'ns')), 'c' * 64, **kw)
    def mutate(reg_, man_, fam_, parent, views, *args, **kw_):
        out = orig(reg_, man_, fam_, parent, views, *args, **kw_); views['L1.00'][0].configs[0].T1_model[0] += 1.0; return out
    monkeypatch.setattr(dp, 'evaluate_family_full', mutate)
    with pytest.raises(InputContractError, match='inputs changed'): calibrate_family_partial(reg, man, 'E1', {k: (_copy.copy(v[0]), _copy.copy(v[1]), v[2]) for k, v in e1.items()}, ctx, ctx.context_sha256, [80.], [400.], Archive(str(tmp_path / 'mut')), 'c' * 64, **kw)
    monkeypatch.setattr(dp, 'evaluate_family_full', orig); e1['E1/L1.00'][0].configs[0].T1_model[0] -= 1.0                                 # restore the shared fixture array
    # a partial whose plan-object record was edited is refused by the shape check / combiner
    d = ser.from_jsonable(ser.to_jsonable(p.as_dict())); d['plan_objects']['stable_after'] = False; d['binding']['partial_sha256'] = _payload_sha(d)
    with pytest.raises(InputContractError, match='plan-object'): verify_partial_record(d, Archive(str(tmp_path / 'ok')))
