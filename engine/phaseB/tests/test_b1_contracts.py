# -*- coding: utf-8 -*-
"""Contract regressions from the ChatGPT B-1 audit (§4–§11) — all must pass on the fixed implementation."""
import os, sys, json, math
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine.ci import ci_from_replicates
from step1_engine.precision import precision_state
from step1_engine.decision import CoreInputs, decide_core
from step1_engine.calibration import calibrate, any_family_truth
from step1_engine.family import mixed_numden, mixed_log_density, point_P, mechanism
from step1_engine.bootstrap_plan import BootstrapPlan, HitTable, resample_hits
from step1_engine.types import ClusterUID
from step1_engine.w2_stop import w2_stop, w2_validate
from step1_engine.observers12 import greedy_maximin, lattice_1d, dist_euclid
from step1_engine.position_state import after_twelve_positions
from step1_engine.truth import precision_to_audit, norm_truth
from step1_engine.errors import InputContractError
from step1_engine import serialization as ser

def seeds5(num, den): return [ci_from_replicates(num, den, mode='Q', seed_id=s) for s in range(5)]
def ordinary(): return seeds5(np.linspace(11, 13, 2000), np.ones(2000))
def base(**kw):
    d = dict(audit_Q_matched='pass', audit_Dpoint_matched='pass', audit_DCI_matched='pass', audit_Q_native='pass', L_Q_matched=12., U_Q_matched=14., logD_point_matched=.5, L_logD_matched=.1, U_logD_matched=.9, L_Q_native=1.5, U_Q_native=2.); d.update(kw); return CoreInputs(**d)

# A: truth normalisation and adapter
def test_A1_numpy_bool_equals_builtin():
    a = calibrate([True] * 2000, .05); b = calibrate(np.ones(2000, dtype=bool), .05); assert b.c_true == a.c_true == 2000 and b.usable == a.usable is False
    assert any_family_truth(np.array([True, False])) is True
def test_A2_invalid_tokens_rejected():
    for bad in ([float('nan')] * 3, ['unresolved'] * 3, [None] * 3, [1] * 3, ['precision-unresolved']):
        with pytest.raises(InputContractError): calibrate(bad, .05)
    with pytest.raises(InputContractError): calibrate([False] * 10, .07)                                   # unregistered threshold
    with pytest.raises(InputContractError): calibrate([False] * 10, .05, expected_n=2000)
def test_A3_precision_adapter_preserves_unresolved():
    s5 = ordinary(); p = precision_state(s5[0], s5, 12., 10, 10); assert p.state == 'precision-unresolved'
    with pytest.raises(InputContractError): decide_core(base(audit_Q_matched=p.state))                       # raw precision state is not an audit token
    r = decide_core(base(audit_Q_matched=precision_to_audit(p.state))); assert r.support_truth == 'unknown'
    truths = [False] * 1960 + [r.support_truth] * 40; assert calibrate(truths, .01).wilson_upper_c_plus_u == pytest.approx(0.027118639253, abs=1e-9)
    assert after_twelve_positions({}, 'unknown')['final_classification_available'] == 'unknown'
    with pytest.raises(InputContractError): after_twelve_positions({}, 'maybe')
def test_A_NaN_numeric_input_is_technical():
    r = decide_core(base(L_Q_matched=float('nan'))); assert r.support_truth == 'technical_fail' and r.technical_status == 'technical_fail'
    for kw in (dict(logD_point_matched=math.inf), dict(L_logD_matched=math.inf, U_logD_matched=math.inf), dict(L_Q_matched=12., U_Q_matched=.8), dict(L_logD_matched=.1, U_logD_matched=-.1), dict(L_Q_matched=-2., U_Q_matched=-1., logD_point_matched=-.3, L_logD_matched=-.4, U_logD_matched=-.1), dict(L_Q_matched=12., U_Q_matched=None)):
        assert decide_core(base(**kw)).technical_status == 'technical_fail', kw                               # R1: inf / reversed / negative Q / half-missing intervals are technical
    with pytest.raises(InputContractError): calibrate(np.zeros((1000, 2), dtype=bool), .01, expected_n=2000)   # R2: 2-D truth arrays are never flattened
    with pytest.raises(InputContractError): calibrate([[False, False]] * 3, .05)

# B: five-seed inventory
def test_B_seed_inventory():
    s5 = ordinary()
    with pytest.raises(InputContractError): precision_state(s5[0], [], 12., 100, 100)
    with pytest.raises(InputContractError): precision_state(s5[0], s5[:1], 12., 100, 100)
    with pytest.raises(InputContractError): precision_state(s5[0], s5[::-1], 12., 100, 100)                 # wrong seed order
    bad = ci_from_replicates([np.nan], [1.], seed_id=4); assert precision_state(s5[0], s5[:4] + [bad], 12., 100, 100).state == 'technical_fail'
    with pytest.raises(InputContractError): precision_state(s5[0], s5, 12., float('nan'), 100)
    p5 = [ci_from_replicates(np.full(100, .5), np.ones(100), mode='P', seed_id=s) for s in range(5)]
    with pytest.raises(InputContractError): precision_state(p5[0], p5, .5, 100, 100)                        # Q-domain only
    assert precision_state(s5[0], s5, 12., 100, 100).state == 'pass'

# C: bootstrap independence / UID join (see test_b1 T10 for shared/independent groups)
def test_C_hit_table_validation():
    U = [ClusterUID(1, 200, 1, 0, i) for i in range(6)]; p = BootstrapPlan.build('p', 0, {0: U}, 5, 1)
    with pytest.raises(InputContractError): HitTable(U, -np.ones(6, dtype=int), 600, 100)                     # negative hits rejected at table construction
    ok = resample_hits(p, {0: HitTable(U, np.ones(6, dtype=int), 600, 100)}, {0: 1.})[0]; assert np.all(ok == 1 / 100)   # same table with valid hits passes (paired positive/negative)
    with pytest.raises(InputContractError): HitTable(U, np.array([0.5] * 6), 600, 100)
    with pytest.raises(InputContractError): HitTable(U, np.zeros(6, int), 601, 100)

# D: W2 inventory / finiteness / binding
def test_D_w2_contracts():
    null = {2000: np.full(1000, .2), 5000: np.full(1000, .15)}; obs = {n: {i: .1 for i in range(3)} for n in null}; s = w2_stop(null, obs, 'f')
    with pytest.raises(InputContractError): w2_stop({2000: np.full(1000, .2)}, {2000: {0: .1}}, 'incomplete')
    with pytest.raises(InputContractError): w2_stop(null, {n: {i: np.inf for i in range(3)} for n in null}, 'inf')
    ob = {n: {i: 0. for i in range(3)} for n in null}; dq = {n: 0. for n in null}
    with pytest.raises(InputContractError): w2_validate(s, np.nan, ob, dq, obs)
    with pytest.raises(InputContractError): w2_validate(s, 0., ob, dq, {n: {i: .3 for i in range(3)} for n in obs})
    with pytest.raises(InputContractError): w2_validate(s, 0., ob, {2000: -1., 5000: 0.}, obs)
    with pytest.raises(InputContractError): w2_validate(s, 0., {}, {}, {})
    import copy
    for mut in ('drop_first', 'q99_inf', 'rel_change'):
        st = copy.deepcopy(s)
        if mut == 'drop_first': st.trace = st.trace[1:]
        elif mut == 'q99_inf': st.trace[-1]['q99'][2000] = np.inf
        else: st.trace[-1]['relative_change'] = 0.5
        with pytest.raises(InputContractError): w2_validate(st, 0., ob, dq, obs)                              # corrupted stored trace rejected at intake
    st = copy.deepcopy(s); st.state = 'technical_fail'
    with pytest.raises(InputContractError): w2_validate(st, 0., ob, dq, obs)
    z0 = {n: {i: (0.0 if i == 0 else .1) for i in range(3)} for n in null}; sz = w2_stop(null, z0, 'z'); assert w2_validate(sz, np.inf, ob, dq, z0)['reason'].startswith('seed_spread_undefined')
    with pytest.raises(InputContractError): ser.loads('{"a": NaN}')
    with pytest.raises(InputContractError): ser.dumps({1: 'a', '1': 'b'})
    assert w2_validate(s, 0., ob, dq, obs)['state'] == 'valid'
    null0 = {2000: np.zeros(1000), 5000: np.zeros(1000)}; s0 = w2_stop(null0, {n: {i: .1 for i in range(3)} for n in null0}, 'z'); assert s0.trace[1]['relative_change_state'] == 'q99_prev_zero' and s0.state == 'w2-unresolved'
    json.dumps(s0.as_dict(), allow_nan=False)

# E: CI / family input domains
def test_E1_P_positive_over_zero_is_technical():
    r = ci_from_replicates(np.ones(2000), np.zeros(2000), mode='P'); assert r.math_state == 'technical_fail'
def test_E2_counts_disjoint():
    r = ci_from_replicates([2., .5], [1., 1.], mode='P'); assert sum(r.counts.values()) == r.B == 2 and r.counts['technical_invalid'] == 1
def test_E3_log_arithmetic_no_underflow_replacement():
    r = ci_from_replicates(np.full(2000, 1e-300), np.full(2000, 1e100)); assert r.log_lower == pytest.approx(math.log(1e-300) - math.log(1e100)) and r.math_state == 'finite'
    r2 = ci_from_replicates(np.full(2000, 1e300), np.full(2000, 1e-100)); assert r2.math_state == 'finite' and math.isfinite(r2.log_lower)
def test_E5_family_validation():
    with pytest.raises(InputContractError): mixed_log_density(np.log([[2., 4.]]), np.array([-1., 2.]))
    with pytest.raises(InputContractError): mixed_numden(np.array([[.5, np.nan]]), np.array([[.5, .5]]), np.array([.5, .5]))
    with pytest.raises(InputContractError): mixed_numden(np.array([[.5, .5]]), np.array([[.5, .5]]), np.array([.500005, .5]))   # rtol=0
    with pytest.raises(InputContractError): point_P(np.array([1.5, 2]), np.array([10, 10]))
    with pytest.raises(InputContractError): point_P(np.array([1, 2]), np.array([np.inf, 10]).astype(float))
    with pytest.raises(InputContractError): mechanism([.5], [.4], [.1], [.2])
    assert mixed_log_density(np.array([[-np.inf, -np.inf]]), np.array([.5, .5]))[0] == -np.inf

# serialisation round trips
def test_strict_json_roundtrip_all_results():
    objs = [ci_from_replicates(np.linspace(11, 13, 100), np.ones(100)), ci_from_replicates(np.r_[np.zeros(5), np.ones(95)], np.ones(100)), ci_from_replicates(np.r_[np.zeros(1), np.ones(99)], np.r_[np.zeros(1), np.ones(99)]),
            ci_from_replicates([np.nan], [1.]), calibrate([False] * 1999 + ['technical_fail'], .05), calibrate([False] * 1960 + ['unknown'] * 40, .05), decide_core(base())]
    for o in objs:
        s = ser.dumps(o.as_dict()); d = ser.loads(s); assert json.loads(s) is not None
        for k, v in o.as_dict().items():
            if isinstance(v, dict) and set(v) == {'__float__'}: assert math.isnan(d[k]) if v['__float__'] == 'nan' else d[k] == float(v['__float__'])
    z = ci_from_replicates(np.r_[np.zeros(5), np.ones(95)], np.ones(100)); d = ser.loads(ser.dumps(z.as_dict())); assert d['log_lower'] == -math.inf and d['lower'] == 0.0

def test_observer_anchor_and_lattice_contracts():
    cand = lattice_1d(.02, .23)[:, None]
    with pytest.raises(InputContractError): greedy_maximin(cand, np.array([[.04], [.04], [.18]]), 9, .015, dist_euclid)
    with pytest.raises(InputContractError): greedy_maximin(cand, np.array([[.04], [.041], [.18]]), 9, .015, dist_euclid)   # anchors closer than min_sep
    with pytest.raises(InputContractError): greedy_maximin(cand, np.array([[.5]]), 3, .015, dist_euclid)                  # outside box


def test_config_schema_strictness_and_interval_reason_codes():
    import copy, json, tempfile, os
    import step1_engine.rules_config as rc
    J = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'rules_tables_v1.json')))
    def bad(mut):
        j = copy.deepcopy(J); mut(j)
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as fh: json.dump(j, fh); p = fh.name
        with pytest.raises(ValueError): rc.verify_binding(rc._load(p), require_document=False)
    bad(lambda j: j['table1_decision_predicates']['unsupported_core']['and'].remove('audit_Dpoint_matched'))       # removed conjunct
    bad(lambda j: j['table1_decision_predicates']['support_core']['and'].__setitem__(2, 'L_Q_matched >= 3e1'))     # unregistered numeric spelling
    bad(lambda j: j['table1_decision_predicates']['support_core'].__setitem__('and', []))                          # empty AND
    bad(lambda j: j['table1_decision_predicates']['support_core']['and'].append('audit_Q_matched'))                # duplicate term
    bad(lambda j: j['table1_decision_predicates']['strong_core']['and'].append('L_Q_matched >= 3'))               # extra term
    r = decide_core(base(U_Q_native=math.nan)); assert r.strong_truth == 'technical_fail' and 'invalid_interval:Q_native' in r.reason_codes and r.support_truth is True
