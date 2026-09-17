# -*- coding: utf-8 -*-
"""B-1 acceptance tests (rules draft4 / engine spec v0.2). All inputs are synthetic; golden expectations are hand-written (not derived from the implementation)."""
import json, math, os, sys
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine.ci import ci_from_replicates, classify_replicates
from step1_engine.precision import precision_state
from step1_engine.decision import CoreInputs, decide_core, logD_ci_required, UNKNOWN, TECH
from step1_engine.family import mixed_numden, point_P, mixed_log_density, mechanism
from step1_engine.bootstrap_plan import BootstrapPlan, HitTable, resample_hits, literal_resample_hits, stratum_weights_from_tables
from step1_engine.types import ClusterUID, as_uid
from step1_engine.errors import InputContractError
from step1_engine.truth import precision_to_audit
from step1_engine import serialization as ser
from step1_engine.rules_config import RULES, verify_binding
from step1_engine.calibration import any_family_truth, calibrate, wilson_upper
from step1_engine.position_state import position_state, after_twelve_positions
from step1_engine.w2_stop import w2_stop, w2_validate
from step1_engine.observers12 import lattice_1d, greedy_maximin, min_pairwise, dist_euclid, dist_torus_halfturn
from step1_engine.registry import CRNRegistry
RULES_JSON = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'rules_tables_v1.json')))
def seeds5(num, den, mode='Q'): return [ci_from_replicates(num, den, mode=mode, seed_id=s) for s in range(5)]

# ---------------- CI contract (T1–T5 + contract group)
def test_T1_zero_replicates_kept_lower_is_zero():
    den = np.full(2000, 10.0); num = np.full(2000, 200.0); num[:80] = 0.0
    r = ci_from_replicates(num, den, mode='Q')
    assert r.math_state == 'boundary' and r.effective_method == 'inverted_cdf' and r.lower == 0.0 and r.log_lower == -math.inf and r.counts['zero'] == 80
    assert r.upper == pytest.approx(20.0)

def test_T2_inf_replicates_upper_infinite_and_precision_unresolved():
    den = np.full(2000, 10.0); num = np.full(2000, 100.0); den[:100] = 0.0
    r = ci_from_replicates(num, den, mode='Q'); assert r.math_state == 'boundary' and r.upper == math.inf
    s5 = seeds5(num, den); ps = precision_state(s5[0], s5, 10.0, 100, 100); assert ps.state == 'precision-unresolved' and 'non_finite_or_disordered_endpoint' in ps.reasons

def test_T3_mathematical_undefined_envelope_only_arithmetic():
    B = 2000; num = np.full(B, 120.0); den = np.full(B, 10.0); num[0] = 0.0; den[0] = 0.0
    r = ci_from_replicates(num, den, mode='Q'); assert r.math_state == 'undefined_completed' and r.effective_method == 'lower_higher_envelope' and r.counts['undefined'] == 1
    assert r.log_lower == pytest.approx(math.log(12.0)) and r.log_upper == pytest.approx(math.log(12.0))   # one unknown among 1999 identical values does not move the 2.5/97.5 order statistics

def test_T4_single_technical_nan_is_technical_fail_even_if_label_unchanged():
    num = np.concatenate([np.full(1000, 12.0), np.full(999, 13.0), [np.nan]]); den = np.ones(2000)
    r = ci_from_replicates(num, den, mode='Q'); assert r.math_state == 'technical_fail' and r.lower is None and r.counts['technical_invalid'] == 1
    s5 = seeds5(num, den); ps = precision_state(s5[0], s5, 12.5, 100, 100); assert ps.state == 'technical_fail'

def test_T5_mixed_quantile_envelope_covers_finite_completion():
    known = np.concatenate([np.full(1950, -0.001), np.full(49, 0.1)]); num = np.exp(known); den = np.ones(1999)
    num = np.concatenate([num, [0.0]]); den = np.concatenate([den, [0.0]])              # one mathematical undefined slot
    r = ci_from_replicates(num, den, mode='Q'); assert r.log_upper == pytest.approx(0.1)
    finite_completion = np.concatenate([known, [0.2]]); U_lin = np.quantile(finite_completion, 0.975, method='linear'); assert U_lin == pytest.approx(0.0015249999999862214)
    assert r.log_upper >= U_lin - 1e-12 and r.log_lower <= np.quantile(finite_completion, 0.025, method='linear') + 1e-12

def test_CI_contract_domain_and_shape():
    with pytest.raises(InputContractError): ci_from_replicates(np.ones(3), np.ones(2), mode='Q')
    with pytest.raises(InputContractError): ci_from_replicates(np.ones(3), np.ones(3), mode='X')
    r = ci_from_replicates(np.array([2.0, 1.0]), np.array([1.0, 1.0]), mode='P'); assert r.math_state == 'technical_fail'   # P>1 is technical invalid, not clipped
    r = ci_from_replicates(np.array([-1.0, 1.0]), np.array([1.0, 1.0]), mode='Q'); assert r.math_state == 'technical_fail'
    r = ci_from_replicates(np.full(100, 1.0), np.full(100, 1.0), mode='P'); assert r.log_upper == 0.0 and r.upper == 1.0
    r = ci_from_replicates(np.full(100, 12.0), np.ones(100), mode='Q'); assert r.log_lower == pytest.approx(math.log(12)) and r.lower == pytest.approx(12.0) and r.effective_method == 'linear_logQ'

def test_CI_all_inf_and_cv_undefined():
    r = ci_from_replicates(np.ones(50), np.zeros(50), mode='Q'); assert r.math_state == 'boundary' and r.lower == math.inf
    s5 = seeds5(np.full(100, 12.0), np.ones(100)); ps = precision_state(s5[0], s5, 12.0, 100, 100); assert ps.state == 'cv_undefined'

def test_serialisation_no_bare_infinity():
    r = ci_from_replicates(np.array([0.0, 1.0]), np.array([1.0, 1.0]), mode='Q'); d = r.as_dict(); json.dumps(d, allow_nan=False); assert d['log_lower'] == {'__float__': '-inf'}

# ---------------- decision predicates (T7–T9, mutants)
def base(**kw):
    d = dict(audit_Q_matched='pass', audit_Dpoint_matched='pass', audit_DCI_matched='pass', audit_Q_native='pass', L_Q_matched=12.0, U_Q_matched=14.0, logD_point_matched=0.5, L_logD_matched=0.1, U_logD_matched=0.9, L_Q_native=1.5, U_Q_native=2.0); d.update(kw); return CoreInputs(**d)

def test_T7_unsupported_not_fired_when_Dpoint_audit_fails():
    d = decide_core(base(audit_Dpoint_matched='fail', L_Q_matched=0.5, U_Q_matched=0.8, U_logD_matched=-0.05, L_logD_matched=-0.3, logD_point_matched=-0.1))
    assert d.unsupported_truth is False and d.display_label == 'inconclusive'
    d2 = decide_core(base(L_Q_matched=0.5, U_Q_matched=0.8, U_logD_matched=-0.05, L_logD_matched=-0.3, logD_point_matched=-0.1)); assert d2.unsupported_truth is True and d2.display_label == 'unsupported'

def test_T8_finite_logD_ci_crossing_zero_blocks_strong_not_support():
    d = decide_core(base(L_logD_matched=-0.1)); assert d.support_truth is True and d.strong_truth is False and d.display_label == 'support' and 'logD_CI_crosses_zero_strong_only' in d.reason_codes

def test_T9_native_D_not_required():
    d = decide_core(base()); assert d.strong_truth is True and d.display_label == 'strong' and d.direction_native == 'positive'
    d = decide_core(base(L_Q_native=0.9, U_Q_native=1.2)); assert d.strong_truth is False and d.support_truth is True and d.direction_native == 'neutral'

def test_decision_three_valued_and_technical_precedence():
    d = decide_core(base(L_Q_matched=1.8, U_Q_matched=2.2)); assert d.support_truth is False and d.display_label == 'inconclusive'      # definite False, not unknown
    d = decide_core(base(audit_Q_matched='unresolved')); assert d.support_truth == UNKNOWN and d.display_label == 'inconclusive'
    d = decide_core(base(audit_Q_matched='technical_fail')); assert d.support_truth == TECH and d.technical_status == 'technical_fail'
    d = decide_core(base(audit_DCI_matched='not_computed_by_registered_short_circuit', L_Q_matched=4.0, U_Q_matched=6.0)); assert d.support_truth is True and d.strong_truth is False   # L_Q < 10: strong definitely False even without the logD CI
    d = decide_core(base(audit_DCI_matched='not_computed_by_registered_short_circuit')); assert d.support_truth is True and d.strong_truth == UNKNOWN and 'logD_CI_not_computed_by_registered_short_circuit' in d.reason_codes
    assert logD_ci_required(12.0, 14.0) and logD_ci_required(0.5, 0.8) and not logD_ci_required(4.0, 6.0)

def test_T16_strong_positive_control_full_predicate_and_conjunct_drop():
    assert decide_core(base()).strong_truth is True
    for kw in (dict(L_Q_matched=9.9), dict(L_logD_matched=-0.01), dict(L_Q_native=0.99, U_Q_native=1.5), dict(audit_Q_native='fail'), dict(audit_DCI_matched='fail'), dict(logD_point_matched=0.0)):
        assert decide_core(base(**kw)).strong_truth is not True, kw

def test_mutant_threshold_and_unknown_to_false_are_detected():
    assert RULES_JSON['table1_decision_predicates']['thresholds']['Q_support'] == 3.0 and RULES_JSON['table1_decision_predicates']['thresholds']['Q_strong'] == 10.0
    d = decide_core(base(L_Q_matched=3.0, U_Q_matched=3.5)); assert d.support_truth is True                 # threshold is >= 3 (a mutant '> 3' would fail here)
    assert any_family_truth([False, UNKNOWN]) == UNKNOWN                                                     # a mutant collapsing unknown to False would return False
    assert any_family_truth(np.array([True, False])) is True and calibrate(np.ones(2000, dtype=bool), 0.05).c_true == 2000   # NumPy bool == Python bool

# ---------------- family mixture (R2)
def test_family_mixture_unequal_N_and_prior():
    N = np.array([100, 400]); hM = np.array([8, 8]); hI = np.array([2, 16]); w = np.array([0.5, 0.5])
    PM, PI = point_P(hM, N), point_P(hI, N); num, den = mixed_numden(PM[None, :], PI[None, :], w); Q = float(num[0] / den[0])
    assert Q == pytest.approx(1.6666666666666667)
    assert Q != pytest.approx(16 / 18) and Q != pytest.approx((4 + 0.5) / 2)                                   # pooled hits and averaged Q are both wrong
    with pytest.raises(ValueError): mixed_numden(PM[None, :], PI[None, :], np.array([0.6, 0.6]))
    lf = mixed_log_density(np.log(np.array([[0.2, 0.05]])), w); assert lf[0] == pytest.approx(math.log(0.125))
    mech = mechanism(np.array([0.004]), np.array([0.02]), np.array([0.003]), np.array([0.015])); assert mech['Q_joint'][0] == pytest.approx(mech['Q_T1'][0] * mech['Q_noncomp'][0])
    mech0 = mechanism(np.array([0.0]), np.array([0.0]), np.array([0.003]), np.array([0.015])); assert mech0['undefined_conditional']

# ---------------- bootstrap plan (T10 small reference, T18)
def test_T10_stratified_resampling_matches_literal_and_preserves_weights():
    U0 = [ClusterUID(1, 200, 7, 0, i) for i in range(6)]; U1 = [ClusterUID(1, 200, 7, 1, i) for i in range(18)]
    plan = BootstrapPlan.build('p', 3, {0: U0, 1: U1}, B=50, master_seed=20260913)
    tA = {0: HitTable(U0, np.array([1, 0, 2, 0, 1, 0]), 600, 100)}                                          # point A: prefix only
    tB = {0: HitTable(U0, np.array([1, 0, 2, 0, 1, 0]), 600, 100), 1: HitTable(U1, np.arange(18) % 3, 1800, 100)}   # point B: prefix + extension
    PA, sA = resample_hits(plan, tA, {0: 1.0}); PA_l, sA_l = literal_resample_hits(plan, tA, {0: 1.0}); assert np.array_equal(sA[0], sA_l[0]) and np.allclose(PA, PA_l)
    PB, sB = resample_hits(plan, tB, {0: 0.25, 1: 0.75}); PB_l, sB_l = literal_resample_hits(plan, tB, {0: 0.25, 1: 0.75}); assert np.array_equal(sB[0], sB_l[0]) and np.array_equal(sB[1], sB_l[1]) and np.allclose(PB, PB_l)
    assert np.array_equal(sA[0], sB[0]) and sA[0].dtype == np.int64                                          # shared prefix stratum: SAME multiplicities for both points
    with pytest.raises(InputContractError): resample_hits(plan, tB, {0: 0.5, 1: 0.75})
    with pytest.raises(InputContractError): resample_hits(plan, tB, {0: -0.5, 1: 1.5})
    with pytest.raises(InputContractError): resample_hits(plan, tB, {0: 0.5, 1: 0.5})                         # sums to 1 but not the sample-count fractions (600/2400, 1800/2400)
    PBd, _ = resample_hits(plan, tB); assert np.allclose(PBd, PB) and stratum_weights_from_tables(tB) == {0: 0.25, 1: 0.75}   # derived weights
    with pytest.raises(InputContractError): resample_hits(plan, {0: HitTable(U0[::-1], np.array([1, 0, 2, 0, 1, 0]), 600, 100)}, {0: 1.0})   # reordered UIDs
    other = [ClusterUID(1, 200, 8, 0, i) for i in range(6)]
    with pytest.raises(InputContractError): resample_hits(plan, {0: HitTable(other, np.array([1, 0, 2, 0, 1, 0]), 600, 100)}, {0: 1.0})       # other group, same length
    with pytest.raises(InputContractError): HitTable(U0, np.array([-1, 0, 2, 0, 1, 0]), 600, 100)
    with pytest.raises(InputContractError): HitTable(U0 * 1 + [U0[0]], np.zeros(7, int), 700, 100)
    with pytest.raises(InputContractError): BootstrapPlan.build('dup', 0, {0: [U0[0]] * 6}, 5, 1)
    with pytest.raises(InputContractError): BootstrapPlan.build('badbatch', 0, {9: U0}, 5, 1)
    p_eval = BootstrapPlan.build('e', 0, {0: [ClusterUID(1, 200, 1, 0, i) for i in range(6)]}, 50, 20260913); p_neg = BootstrapPlan.build('n', 0, {0: [ClusterUID(1, 500, 2, 0, i) for i in range(6)]}, 50, 20260913)
    assert not np.array_equal(p_eval.multiplicities[0], p_neg.multiplicities[0])                             # different purpose/group -> independent
    p_same = BootstrapPlan.build('e2', 0, {0: [ClusterUID(1, 200, 1, 0, i) for i in range(6)]}, 50, 20260913); assert np.array_equal(p_eval.multiplicities[0], p_same.multiplicities[0])   # same group -> shared

def test_T18_crn_keys_fanout():
    reg = CRNRegistry(20260913); g = reg.new_group('evaluation', 1, 'E7 family'); g2 = reg.new_group('fitting', 1, 'E7 family fitting')
    st = reg.stream('evaluation', 1, g, 0, 'gaussian'); a = st.standard_normal(5)
    with pytest.raises(InputContractError): reg.stream('evaluation', 1, g, 0, 'gaussian')                     # second creation refused: fan out
    assert reg.stream('evaluation', 1, g, 0, 'gaussian', reuse=True) is st and reg.inventory_unique()
    assert reg.rng_key('evaluation', 1, g, 0, 'gaussian') == reg.rng_key('evaluation', 1, g, 0, 'gaussian')   # evaluation_id absent from the key
    assert reg.cluster_uid(1, 'evaluation', g, 0, 0) != reg.cluster_uid(1, 'fitting', g2, 0, 0)
    uids = [reg.cluster_uid(1, 'evaluation', g, 0, i) for i in range(3)]; p = BootstrapPlan.build('e', 0, {0: uids}, 20, 20260913)     # registry UID composes with the plan directly
    assert np.isfinite(resample_hits(p, {0: HitTable(uids, np.array([1, 2, 3]), 300, 100)})[0]).all() and as_uid((1, 200, g, 0, 0)) == uids[0]
    with pytest.raises(InputContractError): reg.rng_key('fitting', 1, g, 0, 'gaussian')
    reg2 = CRNRegistry(20260913, groups=reg.export_groups()); assert reg2.rng_key('evaluation', 1, g, 0, 'gaussian') == reg.rng_key('evaluation', 1, g, 0, 'gaussian')   # restored registry, no renumbering

# ---------------- calibration aggregation (T17)
def test_T17_wilson_c_plus_u():
    truths = [False] * 1960 + [UNKNOWN] * 40; s = calibrate(truths, 0.05)
    assert s.c_true == 0 and s.u_unknown == 40 and s.wilson_upper_c_plus_u == pytest.approx(0.027118639188737373) and s.usable is True and s.rate_lower == 0 and s.rate_upper == 0.02
    s2 = calibrate([False] * 1999 + [TECH], 0.05); assert s2.status == 'technical_fail' and s2.usable == TECH and s2.wilson_upper_c_plus_u is None
    json.dumps(s2.as_dict(), allow_nan=False)
    assert wilson_upper(0, 2000) == pytest.approx(0.0019170472812529342)
    assert any_family_truth([True, UNKNOWN]) is True and any_family_truth([False, False]) is False and any_family_truth([UNKNOWN, TECH]) == TECH

# ---------------- position state machine (T11–T13)
def test_T11_T12_T13_position_states():
    assert position_state(UNKNOWN, True)['expand'] is True                                                   # T11: W2 unresolved, ratio True (tech ok) -> expand
    assert position_state(True, TECH)['state'] == 'technical_fail'                                            # T12: technical FAIL has precedence
    assert position_state(False, False)['state'] == 'not-expanded' and position_state(False, UNKNOWN)['state'] == 'position-unresolved'
    r = position_state(UNKNOWN, True, zero_hit_expansion=True); assert r['expansion_due_to_zero_hits'] is True
    a = after_twelve_positions({'state': 'position-unresolved'}, new_stage_core_ok=False); assert a['old_position_status'] == 'resolved_by_registered_expansion' and a['final_classification_available'] is False   # T13

# ---------------- W2 stop (T15)
def test_T15_w2_stop_rule():
    null = {2000: np.full(1000, 0.20), 5000: np.full(1000, 0.15)}; obs = {2000: {0: 0.1, 1: 0.1, 2: 0.1}, 5000: {0: 0.1, 1: 0.1, 2: 0.1}}
    s = w2_stop(null, obs, 'prefix-A'); assert s.B_final == 400 and s.state == 'stopped' and s.trace[0]['B'] == 200 and s.trace[1]['B'] == 400
    seq = np.array([0.951] * 200 + [0.99] * 200 + [0.951] * 200 + [0.923] * 200 + [0.9] * 200); null2 = {2000: seq.copy(), 5000: seq.copy()}
    obs2 = {2000: {0: 0.95, 1: 0.95, 2: 0.95}, 5000: {0: 0.95, 1: 0.95, 2: 0.95}}; assert w2_stop(null2, obs2, 'p').B_final == 400
    blocks = [np.concatenate([[top, top], np.full(198, 0.2)]) for top in (1.0, 0.95, 0.85, 0.75, 0.65)]; bad = {2000: np.concatenate(blocks), 5000: np.full(1000, 0.15)}
    s3 = w2_stop(bad, obs, 'p'); assert s3.state == 'w2-unresolved' and s3.stop_reason.startswith('B_max')
    ob = {n: {i: 1e-6 for i in range(3)} for n in null}; dq = {2000: 1e-3, 5000: 1e-3}
    v = w2_validate(s, 0.0, ob, dq, obs); assert v['state'] == 'valid' and v['trigger'] is False
    with pytest.raises(InputContractError): w2_validate(s, 0.0, {2000: {0: 1e-6, 1: 1e-6}}, dq, obs)              # missing bound is not 0
    with pytest.raises(InputContractError): w2_validate(s, 0.0, ob, dq, {n: {i: 0.3 for i in range(3)} for n in obs})   # observed changed after stop
    with pytest.raises(InputContractError): w2_validate(s, np.nan, ob, dq, obs)
    with pytest.raises(InputContractError): w2_validate(s, 0.0, {n: {i: -1.0 for i in range(3)} for n in null}, dq, obs)
    with pytest.raises(InputContractError): w2_stop({2000: np.full(1000, 0.2)}, {2000: {0: 0.1}}, 'incomplete')
    with pytest.raises(InputContractError): w2_stop(null, {n: {i: np.inf for i in range(3)} for n in null}, 'inf')
    with pytest.raises(InputContractError): w2_stop({2000: np.full(999, 0.2), 5000: np.full(1000, 0.15)}, obs, 'p')
    mixed_obs = {2000: {0: 0.25, 1: 0.1, 2: 0.1}, 5000: {0: 0.1, 1: 0.1, 2: 0.1}}; sm = w2_stop(null, mixed_obs, 'p')
    vm = w2_validate(sm, 1.5, {n: {i: 0.0 for i in range(3)} for n in null}, {2000: 0.0, 5000: 0.0}, mixed_obs); assert vm['state'] == 'w2-unresolved' and 'mixed' in vm['reason']
    d = ser.loads(ser.dumps(s.as_dict())); assert d['trace'][1]['q99'][2000] == 0.2                              # int keys and floats survive the strict-JSON round trip

# ---------------- 12-position generator (T14 small-grid unit)
def test_T14_E7_greedy_matches_audit_reference_and_is_order_invariant():
    anchors = np.array([[0.11278702805018147], [0.04504442885635738], [0.17608175443077442]]); cand = lattice_1d(0.02, 0.23, 1e-4)[:, None]
    sel = greedy_maximin(cand, anchors, 9, 0.015, dist_euclid); added = [round(float(x[0]), 4) for x in sel[3:]]
    assert added == [0.23, 0.0789, 0.1444, 0.203, 0.02, 0.062, 0.0958, 0.1286, 0.1602]                          # ChatGPT independent reference (draft3 audit JSON)
    assert min_pairwise(sel, dist_euclid) == pytest.approx(0.0158, abs=1e-12) and len(sel) == 12
    sel_rev = greedy_maximin(cand[::-1].copy(), anchors, 9, 0.015, dist_euclid); assert np.allclose(np.sort(sel[:, 0]), np.sort(sel_rev[:, 0]))
    with pytest.raises(RuntimeError): greedy_maximin(cand, anchors, 9, 0.06, dist_euclid)                       # old min_sep is infeasible -> fail-fast
    with pytest.raises(InputContractError): greedy_maximin(cand, np.array([[0.04], [0.04], [0.18]]), 9, 0.015, dist_euclid)   # duplicate anchors rejected
    with pytest.raises(InputContractError): lattice_1d(0.02, 0.23001, 1e-4)
    with pytest.raises(InputContractError): lattice_1d(0.02, 0.230001)
    P = np.array([[0.1, 0.1], [0.9, 0.9]]); assert dist_torus_halfturn(P, np.array([0.1, 0.1]))[1] == pytest.approx(0.0)   # (0.9,0.9) ~ (-0.1,-0.1) ~ (0.1,0.1)... sign+shift quotient

# ---------------- rules tables ↔ implementation (T20)
def test_T20_rules_tables_consistency():
    t = RULES_JSON['table1_decision_predicates']; assert 'audit_Dpoint_matched' in t['unsupported_core']['and'] and t['display_priority'][0] == 'strong'
    assert RULES_JSON['table1b_replicate_states']['quantile_methods'] == {'finite': 'linear on logQ', 'boundary': 'inverted_cdf (order statistic on extended reals)', 'undefined_completed': 'lower on -inf-completed, higher on +inf-completed'}
    assert RULES_JSON['table2_crn_dependence']['evaluation_id_in_rng_key'] is False and RULES_JSON['table4_expansion']['N_max'] == 4 * RULES_JSON['table4_expansion']['N0']
    assert RULES_JSON['table5_calibration_aggregation']['per_pseudo']['no_true_some_unknown'] == [0, 1] and RULES_JSON['table6_position_trigger']['precedence'][0] == 'technical_fail'
    assert RULES_JSON['w2_stop']['first_comparison'] == [200, 400] and RULES_JSON['observers12']['min_sep']['E7'] == 0.015
    assert RULES_JSON['table3_eligibility']['calibration']['strong_label_requires_both'] is True
    assert verify_binding()['ok'] and RULES.rules_document_sha256 == RULES_JSON['rules_document']['sha256']
    # a single-field JSON edit must be detected by the binding check (rules are loaded from JSON, then compared with the documented golden constants)
    import copy, tempfile, importlib, step1_engine.rules_config as rc
    j = copy.deepcopy(RULES_JSON); j['table3_eligibility']['precision']['rel_halfwidth_max'] = 0.01
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as fh: json.dump(j, fh); p = fh.name
    with pytest.raises(ValueError): rc.verify_binding(rc._load(p), require_document=False)
    j2 = copy.deepcopy(RULES_JSON); j2['table1_decision_predicates']['support_core']['and'][2] = 'L_Q_matched >= 30'
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as fh: json.dump(j2, fh); p2 = fh.name
    with pytest.raises(ValueError): rc.verify_binding(rc._load(p2), require_document=False)                 # predicate string vs threshold mismatch
    j3 = copy.deepcopy(RULES_JSON); j3['rules_document']['sha256'] = '0' * 64
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, dir=os.path.join(os.path.dirname(__file__), '..')) as fh: json.dump(j3, fh); p3 = fh.name
    with pytest.raises(ValueError): rc.verify_binding(rc._load(p3))                                          # document bytes vs recorded SHA
    os.remove(p3)
