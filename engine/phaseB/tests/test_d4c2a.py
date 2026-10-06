# -*- coding: utf-8 -*-
"""D4C-2a contract tests (engine 0.111.0 = D4C-2a v4 after audits R-D4C2A-A/B/C/D, C1/C2/D1 and N-D4ENV-HISTORY-PIN-COMPLETENESS; audit D4C2-probe decision: design / implementation / small tests only — no Colab execution):
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
from step1_engine.infeasibility import (wilson_blocking_count, registered_blocking_counts, envelope_screen_family, check_screen_record, bind_screen_record, blocking_rows_from_screen, evaluated_rows_from_statuses, evaluated_rows_from_record, typed_equal, w2_triggers, infeasibility_certificate, check_certificate, aggregate_rows, exact_hit_rate, SCREEN_SCHEMA, CERT_SCHEMA, CERT_KIND)
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
    assert __version__ == '0.111.0' and set(module_shas()) == set(MODULES)
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
    assert rec['schema'] == PROFILE_SCHEMA and {k: rec['instrumentation'][k] for k in ('wrappers', 'cprofile', 'clock', 'segment_target')} == dict(wrappers=True, cprofile=True, clock='time.perf_counter (wall)', segment_target='threshold_evaluator.evaluate_family_full') and 'per-row persistence' in rec['instrumentation']['accounting'] and 'per-row' in rec['outside_segments_note']
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
    # N-D4C2A-PROFILER-ENTER-CLEANUP: an alias mismatch during __enter__ (a binding site holding a different object) raises and leaves NO wrapper installed
    import step1_engine.bootstrap_plan as bp
    orig_rh = orch.resample_hits; orch.resample_hits = lambda *a, **k: orig_rh(*a, **k)                      # orchestrator's alias no longer IS bootstrap_plan.resample_hits
    try:
        bad_prof = Profiler(targets={'orchestrator._family_Q': TARGETS['orchestrator._family_Q'], 'bootstrap_plan.resample_hits': TARGETS['bootstrap_plan.resample_hits']})
        with pytest.raises(InputContractError, match='different objects'): bad_prof.__enter__()
        assert not hasattr(orch._family_Q, '__profiler_target__') and not hasattr(bp.resample_hits, '__profiler_target__') and bad_prof._installed == [] and not bad_prof._active
    finally: orch.resample_hits = orig_rh


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
        assert check_screen_record(scr) == dict(ok=True, family=fam, n_rows=4, n_blocking=sum(expect_block), w2_applicable=True, complete_coverage=False, formal=False) and scr['complete_coverage'] is False and scr['stages_required'] == ['N0', 'N4']
        with pytest.raises(InputContractError, match='both prefixes'): check_screen_record(scr, formal=True)                                                                      # single-batch synthetic banks: never a FORMAL proof
        with pytest.raises(InputContractError): blocking_rows_from_screen(scr, formal=True)
        for x in scr['results']:
            for s_, v in x['sizes'].items(): assert set(v['positions']) == {'1', '2', '3'} and v['stages_covered'] == ['N0'] and v['complete_coverage'] is False and all(p_['bank_stages'] == ['N0'] for p_ in v['positions'].values()) and all(r['P'] == r['hits'] / r['N'] for p_ in v['positions'].values() for r in p_['stages'].values())
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
        bs = blocking_rows_from_screen(scr); be = evaluated_rows_from_statuses(fam, p.per_pseudo_status, 0, p.binding['partial_sha256'])
        assert set(bs) == {i for i, b in enumerate(expect_block) if b} and all(be[i]['status'] == dict(support='unknown', strong='unknown') for i in bs) and set(be) == {0, 1, 2, 3}          # R-D4C2A-D1: EVERY evaluated row is retained (False rows included)
        cert = infeasibility_certificate(4, [bs, be], pseudo_identity=dict(n=4, sha256_T1=scr['pseudo']['sha256_T1'], sha256_T2=scr['pseudo']['sha256_T2']), campaign=dict(id='t'), target_commitment='c' * 64, sources=[dict(kind='screen', sha256=scr['binding']['screen_sha256'])])
        L = cert['levels']['support']; assert L['first_blocking_count'] == wilson_blocking_count(4, 0.05) == 0 and L['proven_blocking_rows'] >= sum(expect_block) and L['usable_true_impossible_by_wilson'] and check_certificate(cert)['ok']
        assert all(cert['rows'][str(i)]['families'][fam]['support'] == 'unknown' and cert['rows'][str(i)]['levels']['support'] == dict(aggregate='unknown', blocking=True, technical=False, possibly_technical=False) for i in bs)      # screen + evaluated of the SAME family merge to the stronger-typed status
        # evaluated admission through the readers: the published record and its archive; a restamped unknown -> True is rejected by the reader re-derivation
        pid = dict(n=4, sha256_T1=scr['pseudo']['sha256_T1'], sha256_T2=scr['pseudo']['sha256_T2']); regd = dict(shared_null_asset_sha256=p.w2_asset_sha256, w2_context_sha256=p.w2_context_sha256, registry_sha256=reg.registry_sha256, twelve_assets_sha256=p.binding['twelve_assets_sha256'])
        with pytest.raises(InputContractError, match='registered context'): evaluated_rows_from_record(p.as_dict(), ar, registered=None, pseudo_identity=pid, family=fam)                      # the registered identities are required
        res = evaluated_rows_from_record(p.as_dict(), ar, registered=regd, pseudo_identity=pid, family=fam); assert res['rows'] == be and res['row_range'] == [0, 4] and res['partial_sha256'] == p.binding['partial_sha256'] and res['verification']['ok'] and res['n_rows'] == 4 and res['n_blocking_rows'] + res['n_false_rows'] == 4
        if fam == 'E7':                                                                                                                                                                  # expanded rows carry their evaluated eligible truths; a False/False row is retained, and a screen claim on it would contradict
            fl = [i for i, ev_ in be.items() if ev_['status'] == dict(support='False', strong='False')]
            assert res['n_false_rows'] == len(fl)
            for i in fl:
                with pytest.raises(InputContractError, match='conflicting'): infeasibility_certificate(4, [{i: dict(kind='screen', family='E7', status=dict(support='unknown_or_technical', strong='unknown_or_technical'), source_sha256='3' * 64)}, be], pseudo_identity=pid)
        with pytest.raises(InputContractError): evaluated_rows_from_record(_edited(p, lambda d: d['per_pseudo_status'][1]['eligible_truths'].update(support=True)), ar, registered=regd, pseudo_identity=pid)
        with pytest.raises(InputContractError, match='archived copy'): evaluated_rows_from_record(_edited(p, lambda d: d['per_pseudo_status'][1].update(eligibility='x')), ar, registered=regd, pseudo_identity=pid)
        with pytest.raises(InputContractError, match='schema'): evaluated_rows_from_record(dict(p.as_dict(), schema='THIS_IS_NOT_A_PARTIAL'), ar, registered=regd, pseudo_identity=pid)
        with pytest.raises(InputContractError): evaluated_rows_from_record(p.as_dict(), Archive(str(tmp_path / f'empty_{fam}')), registered=regd, pseudo_identity=pid)                          # no archive -> the reference does not resolve
        with pytest.raises(InputContractError, match='columns'): evaluated_rows_from_record(p.as_dict(), ar, registered=regd, pseudo_identity=dict(pid, sha256_T1='9' * 64))
        with pytest.raises(InputContractError, match='family'): evaluated_rows_from_record(p.as_dict(), ar, registered=regd, pseudo_identity=pid, family='E8')
        with pytest.raises(InputContractError): evaluated_rows_from_record(p.as_dict(), ar, registered=dict(regd, w2_context_sha256='8' * 64), pseudo_identity=pid)
    # not applicable: a size with W2 True, or no unknown size; E1 refused; rows / inputs validation
    fc = {k: v for k, v in m['cases'].items() if k.startswith('E2/')}; dec = {k: ctx.decision_for(k, ctx.context_sha256) for k in fc}
    scr = envelope_screen_family(reg, man, 'E2', fc, dict(dec, **{'E2/L1.00': _true()}), ctx.context_sha256, XS, YS, rows=[1, 3]); assert not scr['w2_applicable'] and scr['n_blocking'] == 0 and scr['rows'] == [1, 3] and check_screen_record(scr)['ok']
    orig = m['ctx'].__class__.decision_for; monkeypatch.undo()
    dec0 = {k: ctx.decision_for(k, ctx.context_sha256) for k in fc}; scr0 = envelope_screen_family(reg, man, 'E2', fc, dec0, ctx.context_sha256, XS, YS); assert not scr0['w2_applicable'] and scr0['n_blocking'] == 0
    with pytest.raises(InputContractError, match='E1'): envelope_screen_family(reg, man, 'E1', {k: v for k, v in m['cases'].items() if k.startswith('E1/')}, {}, ctx.context_sha256, XS, YS)
    with pytest.raises(InputContractError): envelope_screen_family(reg, man, 'E2', fc, dec0, ctx.context_sha256, XS, YS, rows=[3, 1])
    for bad_rows in ([True, 2], ['1'], [1.0], '01', [0, 0]):
        with pytest.raises(InputContractError): envelope_screen_family(reg, man, 'E2', fc, dec0, ctx.context_sha256, XS, YS, rows=bad_rows)
    # binding to the registered identities (registry / manifest, W2 context + decision checksums, columns + exact row thresholds, configuration ids); here with the fixture's N values
    cids = {k.split('/')[1]: sorted(c.evaluation_id for c in v[0].configs) for k, v in fc.items()}; pid0 = dict(n=4, sha256_T1=scr0['pseudo']['sha256_T1'], sha256_T2=scr0['pseudo']['sha256_T2'])
    bind = lambda d, **kw: bind_screen_record(d, **dict(dict(registry_sha256=reg.registry_sha256, manifest_sha256=man.manifest_sha256, w2_context_sha256=ctx.context_sha256, w2_decisions=dec0, pseudo_identity=pid0, T1=XS, T2=YS, config_ids=cids, family='E2'), **kw))
    with pytest.raises(InputContractError, match='both prefixes'): bind(scr0)                                                                                                     # N0-only banks: no formal binding at all
    for kw in (dict(registry_sha256='1' * 64), dict(w2_context_sha256='2' * 64), dict(w2_decisions=dict(dec0, **{'E2/L1.20': _unknown()})), dict(w2_decisions={}), dict(pseudo_identity=dict(pid0, n=5)), dict(T1=[80., 200., 80., 151.]), dict(config_ids=dict(cids, **{'L1.00': [1, 2, 3]})), dict(family='E7'), dict(campaign_id='other')):
        with pytest.raises(InputContractError): bind(scr0, **kw)
    with pytest.raises(InputContractError): envelope_screen_family(reg, man, 'E2', fc, dec0, ctx.context_sha256, XS, YS, rows=[0, 4])
    with pytest.raises(InputContractError): envelope_screen_family(reg, man, 'E2', {k: v for k, v in fc.items() if not k.endswith('L1.50')}, dec0, ctx.context_sha256, XS, YS)
    with pytest.raises(InputContractError): envelope_screen_family(reg, man, 'E2', fc, {k: dict(trigger=False) for k in fc}, ctx.context_sha256, XS, YS)
    # tamper detection of a screen record
    for fn in (lambda d: d['results'][0].update(blocking=True), lambda d: d['results'][0]['sizes']['L1.00']['positions']['1']['stages']['N0'].update(P=0.5), lambda d: d.update(n_blocking=3), lambda d: d['w2']['L1.20'].update(trigger=UNKNOWN), lambda d: d['results'][0]['sizes']['L1.00']['positions']['1'].update(bank_stages=['N0', 'N4']), lambda d: d.update(complete_coverage=True)):
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
    pid = dict(n=2000, sha256_T1='1' * 64, sha256_T2='2' * 64); scr = lambda rows, fam='E2': {r: dict(kind='screen', family=fam, status=dict(support='unknown_or_technical', strong='unknown_or_technical'), source_sha256='3' * 64) for r in rows}
    ev = lambda rows, sup, strg, fam='E7': {r: dict(kind='evaluated', family=fam, status=dict(support=sup, strong=strg), source_sha256='4' * 64) for r in rows}
    c = infeasibility_certificate(2000, [scr(range(0, 80))], pseudo_identity=pid); L = c['levels']
    assert not L['support']['usable_true_impossible_by_wilson'] and L['strong']['usable_true_impossible_by_wilson'] and L['support']['proven_blocking_rows'] == 80 and L['support']['possibly_technical_rows'] == 80 and L['strong']['first_blocking_count'] == 12 and c['n_rows_proven'] == 80 and c['thresholds'] == dict(support=0.05, strong=0.01)
    c = infeasibility_certificate(2000, [scr(range(0, 80)), ev([1999], 'True', 'False')], pseudo_identity=pid); assert c['levels']['support']['usable_true_impossible_by_wilson'] and c['levels']['support']['proven_blocking_rows'] == 81 and c['levels']['strong']['proven_blocking_rows'] == 80
    # R-D4C2A-D: different families on the same row COMBINE (any-family rule) and the row counts once; the screen's unknown_or_technical keeps its conditional meaning next to another family's True
    c = infeasibility_certificate(2000, [scr([5]), ev([5], 'True', 'True')], pseudo_identity=pid); r5 = c['rows']['5']
    assert r5['families'] == {'E2': dict(support='unknown_or_technical', strong='unknown_or_technical'), 'E7': dict(support='True', strong='True')} and r5['levels']['support'] == dict(aggregate='True', blocking=True, technical=False, possibly_technical=True) and c['levels']['support']['proven_blocking_rows'] == 1 and c['levels']['support']['aggregate_counts']['True'] == 1
    c = infeasibility_certificate(2000, [ev([5], 'True', 'True', 'E2'), ev([5], 'technical_fail', 'technical_fail', 'E7')], pseudo_identity=pid); r5 = c['rows']['5']
    assert r5['levels']['support'] == dict(aggregate='technical_fail', blocking=True, technical=True, possibly_technical=False) and c['levels']['support']['technical_rows'] == 1 and c['levels']['support']['proven_blocking_rows'] == 1 and c['levels']['support']['technical_rows_present']
    c = infeasibility_certificate(2000, [ev([5], 'unknown', 'unknown', 'E2'), ev([5], 'True', 'False', 'E7'), ev([5], 'False', 'False', 'E1')], pseudo_identity=pid); r5 = c['rows']['5']
    assert r5['levels'] == dict(support=dict(aggregate='True', blocking=True, technical=False, possibly_technical=False), strong=dict(aggregate='unknown', blocking=True, technical=False, possibly_technical=False)) and len(r5['evidence']) == 3 and c['n_rows_proven'] == 1
    c = infeasibility_certificate(2000, [ev([7], 'technical_fail', 'technical_fail')], pseudo_identity=pid); assert c['levels']['support']['proven_blocking_rows'] == 0 and c['levels']['support']['technical_rows'] == 1       # a technical row is not c + u: counted apart (usable has no value)
    # the SAME family's proofs of a row must agree (a screen's unknown_or_technical is refined by an evaluated unknown / technical_fail; a True contradicts a screen's unknown-or-technical)
    c = infeasibility_certificate(2000, [scr([5]), ev([5], 'unknown', 'unknown', 'E2')], pseudo_identity=pid); assert c['rows']['5']['families']['E2'] == dict(support='unknown', strong='unknown') and len(c['rows']['5']['evidence']) == 2
    c = infeasibility_certificate(2000, [scr([5]), ev([5], 'technical_fail', 'technical_fail', 'E2')], pseudo_identity=pid); assert c['rows']['5']['families']['E2']['support'] == 'technical_fail'
    with pytest.raises(InputContractError, match='conflicting'): infeasibility_certificate(2000, [ev([5], 'True', 'True'), ev([5], 'unknown', 'True')], pseudo_identity=pid)
    with pytest.raises(InputContractError, match='conflicting'): infeasibility_certificate(2000, [scr([5]), ev([5], 'True', 'unknown', 'E2')], pseudo_identity=pid)
    with pytest.raises(InputContractError, match='conflicting'): infeasibility_certificate(2000, [ev([5], 'False', 'True', 'E2'), ev([5], 'unknown', 'True', 'E2')], pseudo_identity=pid)
    # exact registered level -> threshold mapping (a swap is rejected in the constructor and by the checker)
    for bad_thr in (dict(support=0.01, strong=0.05), dict(support=0.1, strong=0.01), dict(strong=0.01, support=0.05), dict(support=0.05), dict(support=0.05, strong=0.01, other=0.1)):
        with pytest.raises(InputContractError, match='registered mapping'): infeasibility_certificate(2000, [scr([1])], pseudo_identity=pid, thresholds=bad_thr)
    assert infeasibility_certificate(2000, [scr([1])], pseudo_identity=pid, thresholds=dict(support=RULES.usable_support, strong=RULES.usable_strong))['thresholds'] == dict(support=0.05, strong=0.01)
    with pytest.raises(InputContractError, match='outside'): infeasibility_certificate(2000, [scr([2000])], pseudo_identity=pid)
    with pytest.raises(InputContractError): infeasibility_certificate(2000, [scr([1])], pseudo_identity=dict(pid, n=1999))
    with pytest.raises(InputContractError): infeasibility_certificate(2000, [{1: dict(kind='guess', family='E2', status=dict(support='True', strong='True'))}], pseudo_identity=pid)
    with pytest.raises(InputContractError): infeasibility_certificate(2000, [{1: dict(kind='screen', family='E2', status=dict(support='True', strong='True'))}], pseudo_identity=pid)              # a screen proves unknown_or_technical only
    with pytest.raises(InputContractError): infeasibility_certificate(2000, [{1: dict(kind='evaluated', family='', status=dict(support='True', strong='True'))}], pseudo_identity=pid)
    with pytest.raises(InputContractError): evaluated_rows_from_statuses('E7', [dict(family='E7', eligible_truths=dict(support='maybe', strong=False))], 0, '4' * 64)
    assert aggregate_rows({3: {'E2': dict(support='False', strong='False')}})[3]['support'] == dict(aggregate='False', blocking=False, technical=False, possibly_technical=False)
    # R-D4C2A-D1: evaluated False rows are RETAINED (admitted, reconciled, never counted): a False/False row alone proves nothing; the same family's screen claim on it is a contradiction; another family's True still blocks
    c = infeasibility_certificate(2000, [ev([6], 'False', 'False', 'E2')], pseudo_identity=pid); assert c['n_rows_admitted'] == 1 and c['n_rows_proven'] == 0 and c['rows']['6']['levels']['support'] == dict(aggregate='False', blocking=False, technical=False, possibly_technical=False) and c['levels']['support']['proven_blocking_rows'] == 0 and c['levels']['support']['retained_false_rows'] == 1 and c['levels']['support']['aggregate_counts']['False'] == 1 and check_certificate(c) == dict(ok=True, n=2000, levels=dict(support=False, strong=False), n_rows_admitted=1, n_rows_proven=0, technical_rows=dict(support=0, strong=0))
    with pytest.raises(InputContractError, match='conflicting'): infeasibility_certificate(2000, [scr([6]), ev([6], 'False', 'False', 'E2')], pseudo_identity=pid)
    with pytest.raises(InputContractError, match='conflicting'): infeasibility_certificate(2000, [ev([6], 'False', 'False', 'E2'), ev([6], 'unknown', 'False', 'E2')], pseudo_identity=pid)
    c = infeasibility_certificate(2000, [ev([6], 'False', 'False', 'E2'), ev([6], 'True', 'False', 'E7'), scr([6], 'E8')], pseudo_identity=pid); assert c['n_rows_admitted'] == c['n_rows_proven'] == 1 and c['rows']['6']['levels']['support']['blocking'] and c['rows']['6']['levels']['strong'] == dict(aggregate='unknown_or_technical', blocking=True, technical=False, possibly_technical=True) and c['levels']['strong']['retained_false_rows'] == 0
    s_ = evaluated_rows_from_statuses('E2', [dict(family='E2', eligible_truths=dict(support=False, strong=False), eligibility='e')], 10, '4' * 64); assert s_ == {10: dict(kind='evaluated', family='E2', status=dict(support='False', strong='False'), source_sha256='4' * 64, eligibility='e')}
    d = ser.from_jsonable(ser.to_jsonable(infeasibility_certificate(2000, [ev([6], 'False', 'False', 'E2'), scr([7])], pseudo_identity=pid))); assert d['n_rows_admitted'] == 2 and d['n_rows_proven'] == 1
    d.update(n_rows_proven=2); d['binding']['certificate_sha256'] = hashlib.sha256(ser.dumps({k: v for k, v in d.items() if k != 'binding'}).encode()).hexdigest()                                   # re-stamped: the count re-derivation refuses it
    with pytest.raises(InputContractError, match='n_rows_proven'): check_certificate(d)
    # typed equality (R-D4C2A-C2): bool is not int, int is not float, str is not bool
    assert typed_equal(dict(a=True, b=400, c='unknown', d=[1, 2]), dict(a=True, b=400, c='unknown', d=[1, 2])) and not typed_equal(dict(a=True), dict(a=1)) and not typed_equal(dict(b=400), dict(b=400.0)) and not typed_equal(dict(c='True'), dict(c=True)) and not typed_equal([1], [1, 2]) and not typed_equal(dict(a=1), dict(a=1, b=2))
    c = infeasibility_certificate(2000, [scr([5]), ev([5], 'unknown', 'unknown'), ev([6], 'False', 'True', 'E1'), ev([7], 'technical_fail', 'technical_fail')], pseudo_identity=pid); assert check_certificate(c)['ok'] and c['schema'] == CERT_SCHEMA and c['kind'] == CERT_KIND
    for fn in (lambda d: d['levels']['support'].update(usable_true_impossible_by_wilson=True), lambda d: d['rows'].pop('5'), lambda d: d['rows']['5']['families']['E7'].update(support='True'), lambda d: d['rows']['5']['levels']['support'].update(blocking=False), lambda d: d.update(thresholds=dict(support=0.01, strong=0.05)), lambda d: d['levels']['support'].update(threshold=0.01), lambda d: d['levels']['support'].update(technical_rows=5)):
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


# ------------------------------------------------------------------------------------------------------------------------------------------- environment amendment v0.1
def test_registered_environment_history_and_live_gate():
    """Step1_PhaseD_environment_amendment_v0.1.md: new executions are gated on EXPECTED_VERS (Python 3.13.16) only; REGISTERED runs recorded under the registered history (3.13.15) stay
    accepted by the registered loaders; any other environment is rejected; the pins carry the same current environment and history as the engine."""
    from step1_engine import official_gate as og
    assert og.EXPECTED_VERS['python'] == '3.13.16' and og.EXPECTED_VERS_HISTORY[0]['python'] == '3.13.15' and all(og.EXPECTED_VERS_HISTORY[0][k] == og.EXPECTED_VERS[k] for k in og.VERSION_KEYS if k != 'python')
    for f in ('d/d1_pins.json', 'd/d2_pins.json', 'd/d3_pins.json', 'b3/b3_0_pins.json', 'b3/b3_1_pins.json', 'b3/b3_2_pins.json'):
        pins = json.load(open(os.path.join(P, f))); envs = og.registered_environments(pins)
        assert pins['environment']['python'] == '3.13.16' and len(pins['environment_history']) == 1 and pins['environment_history'][0]['python'] == '3.13.15' and 'amendment' in pins['environment_history'][0]
        assert envs == [{k: og.EXPECTED_VERS[k] for k in og.VERSION_KEYS}, {k: og.EXPECTED_VERS_HISTORY[0][k] for k in og.VERSION_KEYS}]
        old = dict(envs[1]); assert og.recorded_environment_registered(old, pins) and og.recorded_environment_registered(envs[0], pins)
        assert not og.recorded_environment_registered(dict(old, python='3.13.14'), pins) and not og.recorded_environment_registered(dict(old, numpy='2.1.4'), pins) and not og.recorded_environment_registered({}, pins)
        bad = ser.from_jsonable(ser.to_jsonable(pins)); bad['environment']['python'] = '3.13.15'
        with pytest.raises(InputContractError): og.registered_environments(bad)
        bad = ser.from_jsonable(ser.to_jsonable(pins)); bad['environment_history'][0]['python'] = '3.13.14'
        with pytest.raises(InputContractError): og.registered_environments(bad)
        # N-D4ENV-HISTORY-PIN-COMPLETENESS: when pins are given the history field is REQUIRED and authenticated: missing / null / empty / extra entry / edited label / missing or empty amendment name /
        # a non-string version / an environment missing a version key are all refused, by registered_environments and hence by recorded_environment_registered (the registered loaders)
        def mut(fn):
            d = ser.from_jsonable(ser.to_jsonable(pins)); fn(d); return d
        for fn in (lambda d: d.pop('environment_history'), lambda d: d.update(environment_history=None), lambda d: d.update(environment_history=[]), lambda d: d['environment_history'].append(dict(d['environment_history'][0])),
                   lambda d: d['environment_history'][0].update(registered_until='edited label'), lambda d: d['environment_history'][0].pop('registered_until'), lambda d: d['environment_history'][0].pop('amendment'), lambda d: d['environment_history'][0].update(amendment=''),
                   lambda d: d['environment_history'][0].update(extra='x'), lambda d: d['environment_history'][0].update(numpy=2.1), lambda d: d['environment'].pop('numpy'), lambda d: d.pop('environment'), lambda d: d.update(environment_history='3.13.15'), lambda d: d.update(environment_history=[None])):
            bad = mut(fn)
            with pytest.raises(InputContractError): og.registered_environments(bad)
            with pytest.raises(InputContractError): og.recorded_environment_registered(old, bad)
        assert og.HISTORY_ENTRY_KEYS == og.VERSION_KEYS + ('registered_until',) and og.PINS_HISTORY_EXTRA_KEYS == ('amendment',) and set(pins['environment_history'][0]) == set(og.HISTORY_ENTRY_KEYS) | {'amendment'}
        with pytest.raises(InputContractError): og.registered_environments('not pins')
    # the LIVE official gate (new executions) rejects the historical 3.13.15 and accepts only 3.13.16 (symbolic: an injected snapshot on the fixture pair is a pure gate test)
    from test_b2_tranche21 import build_pair
    reg, man, fm, fn, sm, plans, fplans = build_pair()
    ok_env = dict(og.EXPECTED_VERS, blas_threads=[dict(api='blas', n=2)])
    g_now = og.official_gate(fm, fn, 'official', env=ok_env); g_old = og.official_gate(fm, fn, 'official', env=dict(ok_env, python='3.13.15'))
    assert not any('environment versions' in m for m in g_now.required_failures) and any('environment versions' in m for m in g_old.required_failures) and g_old.diagnostics['version_mismatch'] == {'python': ('3.13.15', '3.13.16')}


def test_screen_w2_summary_binding_requires_the_full_registered_decision():
    """R-D4C2A-C2: on a formally shaped synthetic screen record (invented counts; the REAL registered W2 context / columns / grid; no bank execution) bind_screen_record derives the
    full per-size W2 summary {trigger, validation_state, B_final, checksum} from the replay-verified decisions and requires exact typed equality: a registered checksum paired with
    another B_final / trigger / validation_state (record re-stamped) is refused, as is a wrong checksum or a missing decision."""
    from step1_engine.d3_profile import twelve_context
    from step1_engine.d4c0_registry import load_registered_w2_context, load_registered_pseudo_columns
    from step1_engine.grid_registry import load_registry
    from step1_engine.grid_manifest import build_configuration_manifest
    from step1_engine.infeasibility import blocking_rows_from_screen as _brs
    from step1_engine.checkpoint import binding_manifest
    P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    ctx = twelve_context(P); w2, view = load_registered_w2_context(P, ctx); cols = load_registered_pseudo_columns(P, ctx)
    reg = load_registry(os.path.join(P, 'tests/assets/a7_circle_geometry.csv'), os.path.join(P, 'tests/assets/a6_observer_design_points.json')); man = build_configuration_manifest(reg)
    pid = dict(n=cols['n'], sha256_T1=cols['identity']['T1_sha256'], sha256_T2=cols['identity']['T2_sha256'])
    cfg = {}
    for c in ctx.d2_spec['configurations'].values(): cfg.setdefault(c['family'], {}).setdefault(c['size_id'], []).append(c['config_id'])
    cids = {k: sorted(v) for k, v in cfg['E2'].items()}; sizes = sorted(cids); dec = {k: w2.decision_for(k, w2.context_sha256) for k in w2.decisions}; trig = w2_triggers('E2', sizes, dec)
    appl = (not any(v['trigger'] is True for v in trig.values())) and any(v['trigger'] == UNKNOWN for v in trig.values())
    def stamp(d): d['binding']['screen_sha256'] = hashlib.sha256(ser.dumps({k: v for k, v in d.items() if k != 'binding'}).encode()).hexdigest(); return d
    rows = [0, 1]; results = []
    for i in rows:
        ss = {}
        for s_ in sizes:
            pos = {str(cid % 100): dict(evaluation_id=cid, bank_stages=['N0', 'N4'], stages={st: dict(hits=N // 2, N=N, P=0.5) for st, N in (('N0', RULES.N0), ('N4', RULES.N_max))}) for cid in cids[s_]}
            ss[s_] = dict(positions=pos, min_P=0.5, max_P=0.5, ratio_bound=1.0, all_positive=True, ok=True, complete_coverage=True, stages_covered=['N0', 'N4'])
        results.append(dict(row=i, threshold=[float(cols['T1'][i]), float(cols['T2'][i])], sizes=ss, blocking=bool(appl), complete_coverage=True, reason='TEST-ONLY invented counts'))
    scr = stamp(dict(schema=SCREEN_SCHEMA, engine_version=__version__, family='E2', sizes=sizes, registry_sha256=reg.registry_sha256, manifest_sha256=man.manifest_sha256, w2_context_sha256=w2.context_sha256, w2=trig, w2_applicable=appl, pseudo=pid, rows=rows, n_rows=2, n_blocking=sum(1 for x in results if x['blocking']),
                          complete_coverage=True, stages_required=['N0', 'N4'], registered=dict(N0=RULES.N0, N_max=RULES.N_max), config_ids=cids, fingerprints={}, results=results, campaign=dict(id='TEST_ONLY_CAMPAIGN', screen=True, formal=True, rows=[0, 2]), target_commitment='c' * 64, rule=dict(test_only='invented counts'), binding=binding_manifest()))
    scr = ser.from_jsonable(ser.to_jsonable(scr))                                                                                                                                              # the JSON round trip of a published record (typed: bool / int / str)
    bind = lambda d, **kw: bind_screen_record(d, **dict(dict(registry_sha256=reg.registry_sha256, manifest_sha256=man.manifest_sha256, w2_context_sha256=w2.context_sha256, w2_decisions=dec, pseudo_identity=pid, T1=cols['T1'], T2=cols['T2'], config_ids=cids, family='E2', campaign_id='TEST_ONLY_CAMPAIGN', target_commitment='c' * 64), **kw))
    assert bind(scr)['bound'] and check_screen_record(scr, formal=True)['ok'] and len(_brs(scr, formal=True)) == scr['n_blocking']
    def tampered(fn):
        d = ser.from_jsonable(ser.to_jsonable(scr)); fn(d); return stamp(d)
    for fn in (lambda d: d['w2'][sizes[1]].update(B_final=d['w2'][sizes[1]]['B_final'] + 1), lambda d: d['w2'][sizes[1]].update(validation_state='TAMPERED'), lambda d: d['w2'][sizes[0]].update(checksum='0' * 64), lambda d: d['w2'][sizes[1]].update(B_final=float(d['w2'][sizes[1]]['B_final'])),
               lambda d: d['w2'].pop(sizes[2]), lambda d: d['w2'][sizes[0]].update(extra=1)):
        with pytest.raises(InputContractError): bind(tampered(fn))
    t = tampered(lambda d: d['w2'][sizes[1]].update(B_final=d['w2'][sizes[1]]['B_final'] + 1)); assert check_screen_record(t, formal=True)['ok']                                               # internally consistent and re-stamped: only the binding to the registered decisions refuses it
    with pytest.raises(InputContractError, match='W2 summary'): bind(t)
    with pytest.raises(InputContractError): bind(scr, w2_decisions={k: v for k, v in dec.items() if k != 'E2/' + sizes[0]})
    with pytest.raises(InputContractError): bind(scr, w2_decisions=dict(dec, **{'E2/' + sizes[1]: dec['E2/' + sizes[0]]}))
    with pytest.raises(InputContractError): bind(scr, w2_decisions={k: v.checksum for k, v in dec.items()})
