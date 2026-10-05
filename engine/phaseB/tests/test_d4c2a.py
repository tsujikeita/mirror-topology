# -*- coding: utf-8 -*-
"""D4C-2a contract tests (engine 0.108.0; audit D4C2-probe decision: design / implementation / small tests only — no Colab execution):
  profiling: timing wrappers + cProfile around the engine entry points leave the partial record byte-identical (payload SHA); call counts / segments / outside-segment split;
  sub-partials: row-range sub-partials of one family (separate archives) -> merge -> combine_family_subpartials == single-process calibrate_family_partial (content; archive refs;
      manifest-key first-trigger rule across chunks); the combined partial feeds combine_family_partials unchanged (== calibrate_sealed); per-range reader verification with the
      global row offset; refusals (gap / overlap / duplicate / foreign range / family / commitment / campaign / columns / edited status / sub-partial through the partial readers);
  infeasibility: Wilson blocking counts (n = 2000: 81 / 12 with the audit's bounds); envelope screen on synthetic banks with a W2-unknown size == the evaluator's unknown rows
      (sufficient only: a row failing the screen is undetermined, the evaluator may expand it); exhaustive mixed-prefix control (2^k stage choices never trigger when the envelope
      holds); certificate counting / merging / conflicts / tamper detection; the formal readers reject screens and certificates. Synthetic banks only (tests/fixture32)."""
import os, sys, copy, json, hashlib, itertools, tempfile
import numpy as np
import pytest
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); sys.path[:0] = [P, os.path.join(P, 'tests')]
os.environ.setdefault('AUDIT_WORKDIR', tempfile.mkdtemp(prefix='d4c2a_fix_'))
from step1_engine import serialization as ser, __version__
from step1_engine.errors import InputContractError
from step1_engine.archive import Archive, ArchiveRef, merge_archives
from step1_engine.calibration import wilson_upper
from step1_engine.calibration_first import calibrate_sealed, load_sealed_record
from step1_engine.d4c1_partial import (calibrate_family_partial, combine_family_partials, strip_provenance, verify_partial_record, load_partial_record, _payload_sha, PARTIAL_KIND, PARTIAL_SCHEMA, SUBPARTIAL_KIND, SUBPARTIAL_SCHEMA, load_combined_sealed_record)
from step1_engine.d4c1_subpartial import (calibrate_family_subpartial, combine_family_subpartials, strip_subpartial_provenance, verify_subpartial_record, load_subpartial_record, check_subpartial_shape, plan_row_ranges, gate_identity)
from step1_engine.infeasibility import (wilson_blocking_count, registered_blocking_counts, envelope_screen_family, check_screen_record, blocking_rows_from_screen, blocking_rows_from_statuses, infeasibility_certificate, check_certificate, exact_hit_rate, SCREEN_SCHEMA, CERT_SCHEMA, CERT_KIND)
from step1_engine.profiling import Profiler, TARGETS, summarize, PROFILE_SCHEMA
from step1_engine.positions import VerifiedW2Decision, event_ratio_trigger
from step1_engine.w2_context import W2Context
from step1_engine.threshold_evaluator import evaluate_family_full
from step1_engine.checkpoint import MODULES, module_shas
from step1_engine.rules_config import RULES
from step1_engine.truth import TECH, UNKNOWN
from step1_engine import run_reader
from test_d4c1 import fx, _run_both, _assert_equivalent, _edited, FAMS

sha = lambda b: hashlib.sha256(b).hexdigest()
XS, YS = [80., 200., 80., 150.], [400., 1000., 400., 700.]              # E7 ratio-trigger at rows 0 and 2 (two chunks add the same manifest keys), non-trigger rows 1 and 3


def test_modules_registered_and_version():
    for m in ('d4c1_subpartial.py', 'infeasibility.py', 'profiling.py'): assert m in MODULES
    assert __version__ == '0.108.0' and set(module_shas()) == set(MODULES)
    inv = json.load(open(os.path.join(P, 'B2_completion_inventory.json'))); assert inv['modules'] == module_shas() and inv['engine_version'] == __version__


# ------------------------------------------------------------------------------------------------------------------------------------------- fixtures
def _partial(fx, root, fam, xs, ys, C='c' * 64, campaign=dict(id='test-campaign'), rows=None, ctx=None, **kw):
    m = fx['m']; reg, man = m['reg'], m['man']; a = fx['asset']; ctx = m['ctx'] if ctx is None else ctx; fc = {k: v for k, v in m['cases'].items() if k.startswith(fam + '/')}; tw = {'E7': fx['t12']}.get(fam)
    ar = Archive(root, deferred_index=True)
    if rows is None: p = calibrate_family_partial(reg, man, fam, fc, ctx, ctx.context_sha256, xs, ys, ar, C, mode='smoke', campaign=campaign, twelve_inputs=tw, twelve_assets=a, expected_twelve_assets_sha256=a.sha256, **kw)
    else: p = calibrate_family_subpartial(reg, man, fam, fc, ctx, ctx.context_sha256, xs, ys, ar, C, row_range=rows, mode='smoke', campaign=campaign, twelve_inputs=tw, twelve_assets=a, expected_twelve_assets_sha256=a.sha256, **kw)
    return p, ar


@pytest.fixture(scope='module')
def subs(fx, tmp_path_factory):
    """E7 (12-position family): single-process partial over 4 rows vs sub-partials [0,1) [1,2) [2,4) in separate archives, and the coarser tiling [0,2) [2,4)."""
    root = str(tmp_path_factory.mktemp('subs')); single, A1 = _partial(fx, os.path.join(root, 'single'), 'E7', XS, YS)
    parts = {r: _partial(fx, os.path.join(root, f'sub_{r[0]}_{r[1]}'), 'E7', XS, YS, rows=r) for r in ((0, 1), (1, 2), (2, 4))}
    coarse = {r: _partial(fx, os.path.join(root, f'c_{r[0]}_{r[1]}'), 'E7', XS, YS, rows=r) for r in ((0, 2), (2, 4))}
    AC = Archive(os.path.join(root, 'combined'), deferred_index=True)
    for p, ar in parts.values(): merge_archives(AC, ar)
    comb = combine_family_subpartials(fx['m']['reg'], fx['m']['man'], [p.as_dict() for p, _ in parts.values()], AC); AC.flush()
    AC2 = Archive(os.path.join(root, 'combined2'), deferred_index=True)
    for p, ar in coarse.values(): merge_archives(AC2, ar)
    comb2 = combine_family_subpartials(fx['m']['reg'], fx['m']['man'], [p.as_dict() for p, _ in reversed(list(coarse.values()))], AC2); AC2.flush()      # unsorted input order
    return dict(root=root, single=single, A1=A1, parts=parts, coarse=coarse, AC=AC, comb=comb, AC2=AC2, comb2=comb2)


# ------------------------------------------------------------------------------------------------------------------------------------------- sub-partials
def test_subpartial_records_shape_and_global_identity(subs):
    s = subs; n = len(XS); g1, g2 = s['single'].thresholds['pseudo']['sha256_T1'], s['single'].thresholds['pseudo']['sha256_T2']
    for (a, b), (p, ar) in s['parts'].items():
        d = p.as_dict(); check_subpartial_shape(d)
        assert p.schema == SUBPARTIAL_SCHEMA and p.kind == SUBPARTIAL_KIND and p.rows == dict(start=a, stop=b, n_total=n, n_rows=b - a, global_sha256_T1=g1, global_sha256_T2=g2, slice_sha256_T1=p.rows['slice_sha256_T1'], slice_sha256_T2=p.rows['slice_sha256_T2'])
        assert d['thresholds']['pseudo']['n'] == n and d['thresholds']['pseudo']['T1'] == XS[a:b] and d['thresholds']['pseudo']['rows'] == [a, b] and len(p.per_pseudo_status) == b - a and 'partial_dependencies' not in p.binding and p.binding['subpartial_dependencies']['rows'] == [a, b]
        # the archived per-row records carry the GLOBAL pseudo index; the slice threshold is the global row's pair
        for i, st in enumerate(p.per_pseudo_status):
            par = ar.get(ArchiveRef(**st['parent_ref'])); assert par['evidence']['pseudo_index'] == a + i and par['evidence']['threshold'] == [XS[a + i], YS[a + i]]
            assert ArchiveRef(**st['plan_ref']).identity['pseudo_index'] == a + i
        # the sub-partial resolves and re-verifies on its own archive (global row offset) and on the merged archive
        ld = load_subpartial_record(ar, p.binding['partial_ref']); assert ld['binding']['partial_sha256'] == p.binding['partial_sha256'] == _payload_sha(d)
        for arch in (ar, s['AC']):
            v = verify_subpartial_record(d, arch); assert v['ok'] and v['rows'] == [a, b] and v['n_rows'] == b - a and v['family'] == 'E7'
        # a sub-partial is not a family partial: the partial readers / the family combiner refuse it
        with pytest.raises(InputContractError): load_partial_record(ar, p.binding['partial_ref'])
        with pytest.raises(InputContractError): verify_partial_record(d, ar)
        with pytest.raises(InputContractError): load_sealed_record(ar, p.binding['partial_ref'])
    # the per-row records of the single-process run and of the sub-partials are the SAME content-addressed entries
    assert {e['sha256'] for e in s['A1']._entries()} == {e['sha256'] for e in s['AC']._entries()} - {ArchiveRef(**s['comb'].binding['partial_ref']).sha256} - {ArchiveRef(**p.binding['partial_ref']).sha256 for p, _ in s['parts'].values()} | {ArchiveRef(**s['single'].binding['partial_ref']).sha256}


def test_subpartial_combination_equals_single_process_partial(subs):
    s = subs
    for comb in (s['comb'], s['comb2']):
        a, b = strip_subpartial_provenance(s['single'].as_dict()), strip_subpartial_provenance(comb.as_dict())
        assert ser.dumps(a) == ser.dumps(b), [k for k in a if ser.dumps(a[k]) != ser.dumps(b[k])]
        assert comb.schema == PARTIAL_SCHEMA and comb.kind == PARTIAL_KIND and comb.rows is None and 'rows' not in comb.as_dict() and comb.binding['subpartials']['n'] == len(XS)
        assert comb.archive_refs == s['single'].archive_refs and list(comb.archive_refs) == list(s['single'].archive_refs)          # same refs in the same insertion order (manifests first, registry last)
        assert comb.per_pseudo_manifest_keys == s['single'].per_pseudo_manifest_keys and comb.per_pseudo_manifest_keys[0] and comb.per_pseudo_manifest_keys[2] == comb.per_pseudo_manifest_keys[0] and comb.per_pseudo_manifest_keys[1] == [] and s['parts'][(2, 4)][0].per_pseudo_manifest_keys[0]   # rows 0 and 2 trigger (chunk 3 archived the manifests itself); the refs are inserted once, at row 0
        assert comb.binding['partial_sha256'] != s['single'].binding['partial_sha256']                                               # provenance is the only difference
    assert s['comb'].binding['subpartials']['ranges'] == [[0, 1], [1, 2], [2, 4]] and s['comb2'].binding['subpartials']['ranges'] == [[0, 2], [2, 4]]
    # the combined partial passes the family-partial readers on the merged archive and is a valid input of the family combiner
    for comb, AC in ((s['comb'], s['AC']), (s['comb2'], s['AC2'])):
        v = verify_partial_record(comb.as_dict(), AC); assert v['ok'] and v['n_pseudo'] == len(XS)
        assert load_partial_record(AC, comb.binding['partial_ref'])['binding']['partial_sha256'] == comb.binding['partial_sha256']


def test_subpartial_combined_feeds_family_combiner_equals_sealed(subs, fx, tmp_path):
    """E7 from sub-partials + E1 / E2 / E8 single partials -> combine_family_partials == single-process calibrate_sealed (strip_provenance)."""
    s = subs; m = fx['m']; reg, man = m['reg'], m['man']; a = fx['asset']; root = str(tmp_path)
    AC = Archive(os.path.join(root, 'all'), deferred_index=True); merge_archives(AC, s['AC']); parts = {'E7': s['comb']}
    for fam in ('E1', 'E2', 'E8'):
        p, ar = _partial(fx, os.path.join(root, f'p_{fam}'), fam, XS, YS); merge_archives(AC, ar); parts[fam] = p
    comb = combine_family_partials(reg, man, [parts[f].as_dict() for f in FAMS], AC); AC.flush()
    A1 = Archive(os.path.join(root, 'single'), deferred_index=True); single = calibrate_sealed(reg, man, m['cases'], m['ctx'], m['ctx'].context_sha256, XS, YS, A1, 'c' * 64, twelve_inputs={'E7': fx['t12']}, twelve_assets=a, expected_twelve_assets_sha256=a.sha256, require_all_families=True); A1.flush()
    s1, s2 = strip_provenance(single.as_dict()), strip_provenance(comb.as_dict()); assert ser.dumps(s1) == ser.dumps(s2), [k for k in s1 if ser.dumps(s1[k]) != ser.dumps(s2[k])]
    assert comb.binding['combiner']['partials']['E7']['partial_sha256'] == s['comb'].binding['partial_sha256'] and comb.calibration['support']['summary']['n'] == len(XS)
    d = load_combined_sealed_record(AC, comb.binding['run_manifest_ref']); assert d['_verification']['ok'] and d['_verification']['combined']


def test_subpartial_refusals(subs, fx):
    s = subs; m = fx['m']; reg, man = m['reg'], m['man']; AC = s['AC']; D = {r: p.as_dict() for r, (p, _) in s['parts'].items()}; E = lambda r, fn: _edited(s['parts'][r][0], fn)
    ok = lambda subs_, **kw: combine_family_subpartials(reg, man, subs_, AC, verify_references=False, **kw)
    with pytest.raises(InputContractError, match='gap'): ok([D[(0, 1)], D[(2, 4)]])
    with pytest.raises(InputContractError, match='missing'): ok([D[(0, 1)], D[(1, 2)]])
    with pytest.raises(InputContractError, match='duplicate'): ok([D[(0, 1)], D[(0, 1)], D[(1, 2)], D[(2, 4)]])
    with pytest.raises(InputContractError, match='overlap'): ok([D[(0, 1)], D[(1, 2)], s['coarse'][(0, 2)][0].as_dict(), D[(2, 4)]])
    with pytest.raises(InputContractError, match='no sub-partials'): ok([])
    with pytest.raises(InputContractError): ok([s['single'].as_dict(), D[(1, 2)], D[(2, 4)]])                                                   # a family partial is not a sub-partial
    def other_commit(d): d['thresholds']['target_commitment'] = '0' * 64; d['binding']['subpartial_dependencies']['target_commitment'] = '0' * 64
    def other_campaign(d): d['campaign'] = dict(id='another'); d['binding']['subpartial_dependencies']['campaign'] = dict(id='another')
    def other_mode(d): d['mode'] = 'official'; d['binding']['subpartial_dependencies']['mode'] = 'official'
    def other_ctx(d): d['w2_context_sha256'] = '1' * 64; d['binding']['subpartial_dependencies']['w2_context_sha256'] = '1' * 64
    def other_source(d): d['binding']['modules'] = dict(d['binding']['modules'], **{'archive.py': '2' * 64}); d['binding']['subpartial_dependencies']['source_binding']['modules'] = d['binding']['modules']
    def other_gate(d): d['gate']['mode'] = 'official'
    def other_fp(d): d['fingerprints']['at_gate']['E7']['matched'] = '3' * 64; d['fingerprints']['at_end']['E7']['matched'] = '3' * 64; d['binding']['subpartial_dependencies']['fingerprints_at_gate'] = d['fingerprints']['at_gate']
    def other_plan_objects(d): d['plan_objects']['n_objects'] = 99
    for fn in (other_commit, other_campaign, other_mode, other_ctx, other_source, other_gate, other_fp, other_plan_objects):
        with pytest.raises(InputContractError, match='common identity'): ok([E((0, 1), fn), D[(1, 2)], D[(2, 4)]])
    # the global column identity must agree between chunks and with the concatenated slices
    def other_global(d): d['thresholds']['pseudo']['sha256_T1'] = '4' * 64; d['rows']['global_sha256_T1'] = '4' * 64; d['binding']['subpartial_dependencies']['pseudo']['sha256_T1'] = '4' * 64
    with pytest.raises(InputContractError, match='common identity'): ok([E((0, 1), other_global), D[(1, 2)], D[(2, 4)]])
    def all_other_global(d): other_global(d)
    with pytest.raises(InputContractError, match='re-hash'): ok([E(r, all_other_global) for r in ((0, 1), (1, 2), (2, 4))])
    # a slice edited in place (value changed, slice SHA re-stamped) -> the concatenation no longer re-hashes to the global columns
    def edit_slice(d):
        d['thresholds']['pseudo']['T1'][0] = 81.; a = np.asarray(d['thresholds']['pseudo']['T1'], float); h = sha(np.ascontiguousarray(a).tobytes()); d['thresholds']['pseudo']['slice_sha256_T1'] = h; d['rows']['slice_sha256_T1'] = h; d['binding']['subpartial_dependencies']['slice_sha256_T1'] = h
    with pytest.raises(InputContractError, match='re-hash'): ok([E((0, 1), edit_slice), D[(1, 2)], D[(2, 4)]])
    # an edited status without re-stamp -> payload SHA; a promoted truth with re-stamp -> caught by the reader re-derivation (combined record verification) and by verify_subpartial_record
    d = ser.from_jsonable(ser.to_jsonable(D[(1, 2)])); d['per_pseudo_status'][0]['plan_status'] = 'x'
    with pytest.raises(InputContractError, match='payload SHA'): ok([D[(0, 1)], d, D[(2, 4)]])
    def promote(d): d['per_pseudo_status'][0]['eligible_truths']['support'] = True
    bad = E((1, 2), promote)
    with pytest.raises(InputContractError): combine_family_subpartials(reg, man, [D[(0, 1)], bad, D[(2, 4)]], AC, verify_references=True)
    with pytest.raises(InputContractError): verify_subpartial_record(bad, AC)
    # malformed row ranges / rows outside the columns / official scope on a short column set
    fc = {k: v for k, v in m['cases'].items() if k.startswith('E7/')}; ctx = m['ctx']; a_ = fx['asset']
    for rr in ((1, 1), (2, 1), (0, 5), (-1, 2), (True, 2), (0, 2.0), (0,)):
        with pytest.raises(InputContractError): calibrate_family_subpartial(reg, man, 'E7', fc, ctx, ctx.context_sha256, XS, YS, Archive(os.path.join(s['root'], 'x')), 'c' * 64, row_range=rr, mode='smoke', campaign=dict(id='t'), twelve_inputs=fx['t12'], twelve_assets=a_, expected_twelve_assets_sha256=a_.sha256)
    with pytest.raises(InputContractError, match='n_pseudo'): calibrate_family_subpartial(reg, man, 'E7', fc, ctx, ctx.context_sha256, XS, YS, Archive(os.path.join(s['root'], 'y')), 'c' * 64, row_range=(0, 2), mode='official', campaign=dict(id='t'), twelve_inputs=fx['t12'], twelve_assets=a_, expected_twelve_assets_sha256=a_.sha256)
    with pytest.raises(InputContractError, match='different source binding'): ok([E(r, lambda d: d.update(engine_version='0.0.0')) for r in ((0, 1), (1, 2), (2, 4))])
    assert plan_row_ranges(2000, 500) == [(0, 500), (500, 1000), (1000, 1500), (1500, 2000)] and plan_row_ranges(5, 2) == [(0, 2), (2, 4), (4, 5)]
    for bad_ in ((0, 1), (2000, 0), (True, 5), (5, 2.0)):
        with pytest.raises(InputContractError): plan_row_ranges(*bad_)
    for off in (-1, True, 1.0):
        with pytest.raises(InputContractError): run_reader.verify_run_references(s['single'].as_dict(), AC, pseudo_index_offset=off)


def test_subpartial_wrong_family_and_registry(subs, fx, tmp_path):
    s = subs; m = fx['m']; reg, man = m['reg'], m['man']
    p2, _ = _partial(fx, str(tmp_path / 'e2'), 'E2', XS, YS, rows=(0, 1)); D = {r: p.as_dict() for r, (p, _) in s['parts'].items()}
    with pytest.raises(InputContractError, match='common identity'): combine_family_subpartials(reg, man, [p2.as_dict(), D[(1, 2)], D[(2, 4)]], s['AC'], verify_references=False)
    def foreign(d): d['family'] = 'E9'; d['binding']['subpartial_dependencies']['families'] = ['E9']; d['binding']['subpartial_dependencies']['family'] = 'E9'
    for st in D[(0, 1)]['per_pseudo_status']: pass
    d = ser.from_jsonable(ser.to_jsonable(D[(0, 1)])); foreign(d)
    for st in d['per_pseudo_status']: st['family'] = 'E9'
    d['binding']['partial_sha256'] = _payload_sha(d)
    with pytest.raises(InputContractError): combine_family_subpartials(reg, man, [d], s['AC'], verify_references=False)


# ------------------------------------------------------------------------------------------------------------------------------------------- profiling
def test_profiler_leaves_the_record_identical_and_measures_segments(fx, tmp_path):
    p0, _ = _partial(fx, str(tmp_path / 'plain'), 'E7', XS[:2], YS[:2])
    with Profiler(cprofile=True, top_n=10) as prof:
        p1, _ = _partial(fx, str(tmp_path / 'prof'), 'E7', XS[:2], YS[:2])
    rec = prof.report(note='test')
    assert strip_subpartial_provenance(p0.as_dict()) == strip_subpartial_provenance(p1.as_dict()) and p0.binding['partial_sha256'] == p1.binding['partial_sha256']     # instrumentation changes nothing
    assert rec['schema'] == PROFILE_SCHEMA and rec['instrumentation'] == dict(wrappers=True, cprofile=True, clock='time.perf_counter (wall)', segment_target='threshold_evaluator.evaluate_family_full', note=rec['instrumentation']['note'])
    assert rec['segments']['count'] == 2 and len(rec['segments']['per_segment']) == 2 and rec['segments']['wall_seconds'] <= rec['wall_seconds_total'] and rec['outside_segments_wall_seconds'] >= 0
    T = rec['targets']
    for k in ('orchestrator._family_Q', 'orchestrator.ConfigBank.hit_tables', 'bootstrap_plan.resample_hits', 'orchestrator.evaluate_family', 'orchestrator._stage_selection', 'positions.position_decision', 'archive.Archive.put', 'formal_runner.input_fingerprint', 'threshold_evaluator.evaluate_family_full'):
        assert T[k]['calls'] > 0 and T[k]['inclusive_seconds'] >= T[k]['self_seconds'] >= 0, k
    assert T['threshold_evaluator.evaluate_family_full']['calls'] == 2 and T['threshold_evaluator.evaluate_family_full']['outside_segments']['calls'] == 0
    assert T['formal_runner.input_fingerprint']['outside_segments']['calls'] > 0 and T['archive.Archive.put']['outside_segments']['calls'] > 0            # fixed costs sit outside the per-row segments
    assert T['twelve_eval.evaluate_twelve_family_mixture']['calls'] == 1 and rec['segments']['per_segment'][0]['targets']['twelve_eval.evaluate_twelve_family_mixture']['calls'] == 1       # row 0 expands
    seg_q = sum(sg['targets'].get('orchestrator._family_Q', {}).get('calls', 0) for sg in rec['segments']['per_segment']); assert seg_q == T['orchestrator._family_Q']['calls'] - T['orchestrator._family_Q']['outside_segments']['calls']
    assert rec['cprofile'] and rec['cprofile']['by_cumtime'] and rec['cprofile']['by_tottime'] and len(rec['cprofile']['by_cumtime']) <= 10 and rec['missing_targets'] == []
    assert any(l.startswith('total ') for l in summarize(rec)) and 'orchestrator._family_Q' in ' '.join(summarize(rec))
    # the originals are restored on exit; nested / re-entrant use and early report are refused
    import step1_engine.orchestrator as orch, step1_engine.d4c1_partial as d4p
    assert not hasattr(orch._family_Q, '__profiler_target__') and not hasattr(d4p.evaluate_family_full, '__profiler_target__') and d4p.evaluate_family_full is evaluate_family_full
    with pytest.raises(InputContractError): prof.__enter__()
    pr = Profiler()
    with pytest.raises(InputContractError): pr.report()
    with pr: pass
    assert pr.report()['segments']['count'] == 0 and pr.report()['targets']['orchestrator._family_Q']['calls'] == 0
    for bad in (dict(cprofile=1), dict(top_n=0), dict(top_n=True)):
        with pytest.raises(InputContractError): Profiler(**bad)
    with pytest.raises(InputContractError): summarize(dict(schema='x'))


# ------------------------------------------------------------------------------------------------------------------------------------------- infeasibility
def test_wilson_blocking_counts_match_the_audit():
    r = registered_blocking_counts(2000)
    assert r['support'] == dict(threshold=0.05, first_blocking_count=81, previous_upper=0.04950693664126962, blocking_upper=0.050056823219945756)
    assert r['strong'] == dict(threshold=0.01, first_blocking_count=12, previous_upper=0.009822062795201926, blocking_upper=0.010458448381508351)
    assert wilson_upper(3, 2000) == 0.004401032589829253 and wilson_blocking_count(2000, 0.05) == 81 and wilson_blocking_count(2000, 0.01) == 12 and wilson_blocking_count(10, 0.05) == 0 and wilson_blocking_count(400, 0.05) == 12
    for bad in ((0, 0.05), (2000, 1.0), (2000, 0), (True, 0.05)):
        with pytest.raises(InputContractError): wilson_blocking_count(*bad)


def _unknown(): return VerifiedW2Decision.issue(UNKNOWN, dict(state='w2-unresolved', reason='test: mixed indicators'), 1000, 'a' * 64, 'cheap_dist', 'test')
def _true(): return VerifiedW2Decision.issue(True, dict(state='valid', trigger=True), 400, 'b' * 64, 'cheap_dist', 'test')


def _patched_ctx(monkeypatch, ctx, overrides):
    orig = W2Context.decision_for
    def dec(self, key, expected=None):
        if key in overrides: self.validate(expected); return overrides[key]
        return orig(self, key, expected)
    monkeypatch.setattr(W2Context, 'decision_for', dec)


def test_envelope_screen_matches_the_evaluator_on_synthetic_banks(fx, monkeypatch, tmp_path):
    """E2: identical-position models (ratios ~1) with E2/L1.20 forced W2-unknown -> every row screens blocking and the evaluator gives unknown; E7 (ratio > 2 at rows 0 / 2) with
    E7/L1.20 forced unknown -> rows 0 / 2 fail the screen (undetermined) while the evaluator expands them (12-position eligibility), rows 1 / 3 screen blocking == evaluator unknown."""
    m = fx['m']; reg, man, ctx = m['reg'], m['man'], m['ctx']; a = fx['asset']; _patched_ctx(monkeypatch, ctx, {'E2/L1.20': _unknown(), 'E7/L1.20': _unknown()})
    for fam, expect_block in (('E2', [True] * 4), ('E7', [False, True, False, True])):
        fc = {k: v for k, v in m['cases'].items() if k.startswith(fam + '/')}; dec = {k: ctx.decision_for(k, ctx.context_sha256) for k in fc}
        scr = envelope_screen_family(reg, man, fam, fc, dec, ctx.context_sha256, XS, YS, campaign=dict(id='t'), target_commitment='c' * 64)
        assert scr['schema'] == SCREEN_SCHEMA and scr['w2_applicable'] and scr['w2'][f'L1.20']['trigger'] == UNKNOWN and [x['blocking'] for x in scr['results']] == expect_block and scr['n_blocking'] == sum(expect_block) and scr['rows'] == [0, 1, 2, 3]
        assert check_screen_record(scr) == dict(ok=True, family=fam, n_rows=4, n_blocking=sum(expect_block), w2_applicable=True)
        for x in scr['results']:
            for s_, v in x['sizes'].items(): assert set(v['positions']) == {'1', '2', '3'} and v['stages_covered'] == ['N0'] and all(r['P'] == r['hits'] / r['N'] for p_ in v['positions'].values() for r in p_['stages'].values())
        p, ar = _partial(fx, str(tmp_path / f'p_{fam}'), fam, XS, YS)
        for i, st in enumerate(p.per_pseudo_status):
            if expect_block[i]: assert st['eligible_truths'] == dict(support=UNKNOWN, strong=UNKNOWN, unsupported=UNKNOWN) and st['eligibility'] == 'provisional: position-unresolved'
            else: assert st['expand_family'] and st['twelve'] is not None and 'position-unresolved' not in st['eligibility']                                          # undetermined by the screen; the evaluator expands (12-position stage decides)
        # the exact hit rates of the screen are the evaluator's P_model at the chosen stage
        for i, st in enumerate(p.per_pseudo_status):
            par = ar.get(ArchiveRef(**st['parent_ref'])); per = ser.from_jsonable(par)['per_config']
            for s_, (fm, fn, pmap) in fc.items():
                for c in fm.configs: assert per[c.evaluation_id]['P_model'] == scr['results'][i]['sizes'][s_.split('/')[1]]['positions'][str(pmap[c.evaluation_id])]['stages'][per[c.evaluation_id]['stage']]['P']
        # the blocking rows feed the certificate; evaluated statuses give the same rows (and E7's expanded rows contribute per their eligible truths)
        bs = blocking_rows_from_screen(scr); be = blocking_rows_from_statuses(fam, p.per_pseudo_status, 0, p.binding['partial_sha256'])
        assert set(bs) == {i for i, b in enumerate(expect_block) if b} and all(be[i]['status'] == dict(support='unknown', strong='unknown') for i in bs)
        cert = infeasibility_certificate(4, [bs, be], pseudo_identity=dict(n=4, sha256_T1=scr['pseudo']['sha256_T1'], sha256_T2=scr['pseudo']['sha256_T2']), campaign=dict(id='t'), target_commitment='c' * 64, sources=[dict(kind='screen', sha256=scr['binding']['screen_sha256'])])
        L = cert['levels']['support']; assert L['first_blocking_count'] == wilson_blocking_count(4, 0.05) == 0 and L['proven_blocking_rows'] >= sum(expect_block) and L['usable_true_impossible_by_wilson'] and check_certificate(cert)['ok']
        assert all(cert['rows'][str(i)]['status']['support'] == 'unknown' for i in bs)                                                                                 # screen + evaluated merge to the stronger-typed status
    # not applicable: a size with W2 True, or no unknown size; E1 refused; rows / inputs validation
    fc = {k: v for k, v in m['cases'].items() if k.startswith('E2/')}; dec = {k: ctx.decision_for(k, ctx.context_sha256) for k in fc}
    scr = envelope_screen_family(reg, man, 'E2', fc, dict(dec, **{'E2/L1.00': _true()}), ctx.context_sha256, XS, YS, rows=[1, 3]); assert not scr['w2_applicable'] and scr['n_blocking'] == 0 and scr['rows'] == [1, 3] and check_screen_record(scr)['ok']
    orig = m['ctx'].__class__.decision_for; monkeypatch.undo()
    dec0 = {k: ctx.decision_for(k, ctx.context_sha256) for k in fc}; scr0 = envelope_screen_family(reg, man, 'E2', fc, dec0, ctx.context_sha256, XS, YS); assert not scr0['w2_applicable'] and scr0['n_blocking'] == 0
    with pytest.raises(InputContractError, match='E1'): envelope_screen_family(reg, man, 'E1', {k: v for k, v in m['cases'].items() if k.startswith('E1/')}, {}, ctx.context_sha256, XS, YS)
    with pytest.raises(InputContractError): envelope_screen_family(reg, man, 'E2', fc, dec0, ctx.context_sha256, XS, YS, rows=[3, 1])
    with pytest.raises(InputContractError): envelope_screen_family(reg, man, 'E2', fc, dec0, ctx.context_sha256, XS, YS, rows=[0, 4])
    with pytest.raises(InputContractError): envelope_screen_family(reg, man, 'E2', {k: v for k, v in fc.items() if not k.endswith('L1.50')}, dec0, ctx.context_sha256, XS, YS)
    with pytest.raises(InputContractError): envelope_screen_family(reg, man, 'E2', fc, {k: dict(trigger=False) for k in fc}, ctx.context_sha256, XS, YS)
    # tamper detection of a screen record
    for fn in (lambda d: d['results'][0].update(blocking=True), lambda d: d['results'][0]['sizes']['L1.00']['positions']['1']['stages']['N0'].update(P=0.5), lambda d: d.update(n_blocking=3), lambda d: d['w2']['L1.20'].update(trigger=UNKNOWN)):
        d = ser.from_jsonable(ser.to_jsonable(scr0)); fn(d)
        with pytest.raises(InputContractError): check_screen_record(d)


def test_envelope_bound_covers_every_mixed_prefix_choice():
    """synthetic counts: when the envelope over positions x prefixes satisfies max/min <= 2, no choice of N0 / N4 per position triggers; when it does not, some choice triggers (so the
    screen is sufficient, not necessary)."""
    rng = np.random.default_rng(5); n_ok = n_bad = 0
    for trial in range(60):
        N0, N4 = 1000, 4000; H = {j: {'N0': int(rng.integers(300, 700)), 'N4': int(rng.integers(1200, 2800))} for j in (1, 2, 3)}
        vals = [H[j][st] / (N0 if st == 'N0' else N4) for j in H for st in H[j]]; env_ok = max(vals) / min(vals) <= 2.0
        trig = []
        for choice in itertools.product(('N0', 'N4'), repeat=3):
            P_k = {j: dict(P=H[j][st] / (N0 if st == 'N0' else N4), hits=H[j][st], N=(N0 if st == 'N0' else N4), precision='pass', stage=st) for j, st in zip((1, 2, 3), choice)}
            t, info = event_ratio_trigger(P_k); trig.append(t)
        if env_ok: assert not any(t is True for t in trig); n_ok += 1
        else: n_bad += 1
    assert n_ok > 5 and n_bad > 5
    # a hand-made envelope violation where every SAME-prefix choice is fine but a mixed choice triggers (checking same-N only would be insufficient)
    H = {1: {'N0': 300, 'N4': 2000}, 2: {'N0': 300, 'N4': 2000}, 3: {'N0': 300, 'N4': 2000}}; N = {'N0': 1000, 'N4': 4000}
    same = [event_ratio_trigger({j: dict(P=H[j][st] / N[st], hits=H[j][st], N=N[st], precision='pass', stage=st) for j in (1, 2, 3)})[0] for st in ('N0', 'N4')]
    mixed = event_ratio_trigger({1: dict(P=0.3, hits=300, N=1000, precision='pass', stage='N0'), 2: dict(P=0.5, hits=2000, N=4000, precision='pass', stage='N4'), 3: dict(P=0.3, hits=300, N=1000, precision='pass', stage='N0')})[0]
    assert same == [False, False] and mixed is False and (0.5 / 0.3) <= 2.0
    H = {1: {'N0': 200, 'N4': 2000}, 2: {'N0': 200, 'N4': 2000}, 3: {'N0': 200, 'N4': 2000}}
    mixed2 = event_ratio_trigger({1: dict(P=0.2, hits=200, N=1000, precision='pass', stage='N0'), 2: dict(P=0.5, hits=2000, N=4000, precision='pass', stage='N4'), 3: dict(P=0.2, hits=200, N=1000, precision='pass', stage='N0')})[0]
    assert mixed2 is True and max(0.2, 0.5) / min(0.2, 0.5) > 2.0


def test_certificate_counting_conflicts_and_readers(tmp_path):
    pid = dict(n=2000, sha256_T1='1' * 64, sha256_T2='2' * 64); scr = lambda rows: {r: dict(kind='screen', family='E2', status=dict(support='unknown_or_technical', strong='unknown_or_technical'), source_sha256='3' * 64) for r in rows}
    ev = lambda rows, sup, strg, fam='E7': {r: dict(kind='evaluated', family=fam, status=dict(support=sup, strong=strg), source_sha256='4' * 64) for r in rows}
    c = infeasibility_certificate(2000, [scr(range(0, 80))], pseudo_identity=pid); L = c['levels']
    assert not L['support']['usable_true_impossible_by_wilson'] and L['strong']['usable_true_impossible_by_wilson'] and L['support']['proven_blocking_rows'] == 80 and L['strong']['first_blocking_count'] == 12 and c['n_rows_proven'] == 80
    c = infeasibility_certificate(2000, [scr(range(0, 80)), ev([1999], 'True', 'False')], pseudo_identity=pid); assert c['levels']['support']['usable_true_impossible_by_wilson'] and c['levels']['support']['proven_blocking_rows'] == 81 and c['levels']['strong']['proven_blocking_rows'] == 80
    # the same row from two sources merges to the stronger-typed status; a False at one level does not count at that level; technical rows are counted apart
    c = infeasibility_certificate(2000, [scr([5]), ev([5], 'unknown', 'unknown'), ev([6], 'False', 'True', 'E1'), ev([7], 'technical_fail', 'technical_fail')], pseudo_identity=pid)
    assert c['rows']['5']['status'] == dict(support='unknown', strong='unknown') and len(c['rows']['5']['evidence']) == 2 and c['levels']['support']['counts'] == {'True': 0, 'unknown': 1, 'unknown_or_technical': 0, 'technical_fail': 1} and c['levels']['strong']['counts']['True'] == 1 and c['levels']['support']['technical_rows_present']
    assert check_certificate(c)['ok'] and c['schema'] == CERT_SCHEMA and c['kind'] == CERT_KIND
    with pytest.raises(InputContractError, match='conflicting'): infeasibility_certificate(2000, [ev([5], 'True', 'True'), ev([5], 'unknown', 'True')], pseudo_identity=pid)
    with pytest.raises(InputContractError, match='conflicting'): infeasibility_certificate(2000, [scr([5]), ev([5], 'True', 'unknown')], pseudo_identity=pid)
    with pytest.raises(InputContractError, match='outside'): infeasibility_certificate(2000, [scr([2000])], pseudo_identity=pid)
    with pytest.raises(InputContractError): infeasibility_certificate(2000, [scr([1])], pseudo_identity=dict(pid, n=1999))
    with pytest.raises(InputContractError): infeasibility_certificate(2000, [scr([1])], pseudo_identity=pid, thresholds=dict(support=0.1, strong=0.01))
    with pytest.raises(InputContractError): infeasibility_certificate(2000, [{1: dict(kind='guess', family='E2', status=dict(support='True', strong='True'))}], pseudo_identity=pid)
    with pytest.raises(InputContractError): blocking_rows_from_statuses('E7', [dict(family='E7', eligible_truths=dict(support='maybe', strong=False))], 0, '4' * 64)
    for fn in (lambda d: d['levels']['support'].update(usable_true_impossible_by_wilson=True), lambda d: d['rows'].pop('5'), lambda d: d['rows']['5']['status'].update(support='True')):
        d = ser.from_jsonable(ser.to_jsonable(c)); fn(d)
        with pytest.raises(InputContractError): check_certificate(d)
    # archived as a transition record under its own kind, the formal readers reject it
    ar = Archive(str(tmp_path / 'ar')); ref = ar.put('transition', ser.from_jsonable(ser.to_jsonable(c)), dict(kind=CERT_KIND, certificate_sha256=c['binding']['certificate_sha256']))
    with pytest.raises(InputContractError): load_sealed_record(ar, ref.as_dict())
    with pytest.raises(InputContractError): load_partial_record(ar, ref.as_dict())
    with pytest.raises(InputContractError): load_subpartial_record(ar, ref.as_dict())
    from step1_engine.d4c1_partial import _check_partial_shape
    with pytest.raises(InputContractError): _check_partial_shape(ser.from_jsonable(ser.to_jsonable(c)))
    with pytest.raises(InputContractError): check_subpartial_shape(ser.from_jsonable(ser.to_jsonable(c)))
