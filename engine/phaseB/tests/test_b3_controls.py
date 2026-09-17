# -*- coding: utf-8 -*-
"""B-3-1 control helpers (audit R31-A..D): independent negative resampling vs literal, unknown not success, rate check counting, conjunct battery with mutant detection,
brute-force oracle against the actual aggregation path with detector self-test."""
import os, sys, math
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine.rules_config import RULES
from step1_engine.controls import independent_Q_ci, negative_decision, negative_rate_check, conjunct_battery, conjunct_cases, bruteforce_check, bruteforce_detector_selftest, row_loop_oracle, _mutants
from step1_engine.bootstrap_plan import BootstrapPlan, HitTable, literal_resample_hits
from step1_engine.types import ClusterUID
from step1_engine.orchestrator import ConfigBank
from step1_engine.decision import CoreInputs, decide_core
from step1_engine.errors import InputContractError
from step1_engine.truth import UNKNOWN, TECH

def test_independent_negative_resampling_equals_literal_and_differs_from_paired():
    K, m, B = 300, 10, 200; uM = [ClusterUID(1, 500, 21, 0, i) for i in range(K)]; uI = [ClusterUID(1, 200, 22, 0, i) for i in range(K)]
    pM = BootstrapPlan.build('negM', 0, {0: uM}, B, 7); pI = BootstrapPlan.build('negI', 0, {0: uI}, B, 7); h = np.arange(K) % 3
    ci, PM, PI = independent_Q_ci(h, h, pM, pI, K * m, K * m, m, uM, uI, 0)
    _, sM = literal_resample_hits(pM, {0: HitTable(uM, h.astype(np.int64), K * m, m)}, {0: 1.0}); _, sI = literal_resample_hits(pI, {0: HitTable(uI, h.astype(np.int64), K * m, m)}, {0: 1.0})
    assert np.allclose(PM, sM[0] / (K * m)) and np.allclose(PI, sI[0] / (K * m)) and not np.array_equal(sM[0], sI[0]) and ci.lower < 1.0 < ci.upper      # audit's counterexample: identical hit rows no longer give a degenerate [1,1] interval
    pSame = BootstrapPlan.build('same', 0, {0: uM}, B, 7)
    with pytest.raises(InputContractError): independent_Q_ci(h, h, pM, pSame, K * m, K * m, m, uM, uM, 0)

def _banks(rng, K, m, scale=1.0, shift=0.0):
    z = rng.standard_normal((K * m, 2)); T = z * [40, 200] * scale + [120, 600] - shift; return dict(T1=T[:, 0], T2=T[:, 1])

def test_negative_decision_unknown_is_not_success_and_definite_false_is():
    rng = np.random.default_rng(3); K, m = 120, 10; uM = [ClusterUID(1, 500, 31, 0, i) for i in range(K)]; uI = [ClusterUID(1, 200, 32, 0, i) for i in range(K)]
    pM = {s: BootstrapPlan.build(f'M{s}', s, {0: uM}, 60, 11) for s in range(5)}; pI = {s: BootstrapPlan.build(f'I{s}', s, {0: uI}, 60, 12) for s in range(5)}
    model, ref = _banks(rng, K, m), _banks(rng, K, m); r = negative_decision(model, ref, uM, uI, pM, pI, m, None, ref, None, None, None, None, 80.0, 400.0)
    assert r['truths']['support'] == UNKNOWN and r['gate'] is False and r['precision']['state'] != 'pass'                                          # small K: unresolved -> not a success
    K2 = 2000; uM2 = [ClusterUID(1, 500, 33, 0, i) for i in range(K2)]; uI2 = [ClusterUID(1, 200, 34, 0, i) for i in range(K2)]
    pM2 = {s: BootstrapPlan.build(f'M2{s}', s, {0: uM2}, 200, 13) for s in range(5)}; pI2 = {s: BootstrapPlan.build(f'I2{s}', s, {0: uI2}, 200, 14) for s in range(5)}
    model2, ref2 = _banks(rng, K2, m), _banks(rng, K2, m); fitM, fitI = _banks(rng, 300, m), _banks(rng, 300, m); cidf = np.repeat(np.arange(300), m)
    r2 = negative_decision(model2, ref2, uM2, uI2, pM2, pI2, m, fitM, fitI, cidf, cidf, None, None, 80.0, 400.0)
    assert r2['truths']['support'] is False and r2['gate'] is True and r2['precision']['state'] == 'pass' and r2['technical_status'] == 'ok'
    assert negative_rate_check([False] * 197 + [UNKNOWN] * 3)['ok'] is True and negative_rate_check([False] * 190 + [UNKNOWN] * 10)['ok'] is False   # Wilson(3,200)=0.0435 <= 0.05 < Wilson(10,200)=0.090
    rc = negative_rate_check([False] * 199 + [TECH]); assert rc['ok'] is False and rc['technical'] == 1
    assert negative_rate_check([False] * 190 + [True] * 10)['ok'] is False

def test_conjunct_battery_registered_passes_and_mutants_are_detected():
    q = dict(L_Q=19.0, U_Q=21.0, logD_point=2.1, L_logD=1.5, U_logD=2.7, L_Qn=10.0, U_Qn=12.0); res = conjunct_battery(q)
    assert res['ok'] and res['registered']['strong_base'] == 'True' and res['registered']['support_base'] == 'True' and all(v for v in res['mutants_detected'].values())
    cs = conjunct_cases(q); assert 'audit_Q_matched_fail' in cs['strong_drops'] and 'logD_point_nonpositive' in cs['support_drops'] and cs['support_drops']['logD_point_nonpositive'] == dict(logD_point_matched=0.0)
    # each mutant alone would pass the battery if its case were missing: show the missing-case weakness explicitly
    mut = _mutants()['logD_point']; assert mut(CoreInputs(**dict(cs['support_base'], logD_point_matched=0.0)))['support'] is True and decide_core(CoreInputs(**dict(cs['support_base'], logD_point_matched=0.0))).support_truth is False

def test_bruteforce_oracle_vs_actual_path_and_detector():
    rng = np.random.default_rng(5); K, m = 200, 10; uids = [ClusterUID(1, 200, 41, 0, i) for i in range(K)]; b = _banks(rng, K, m); r = _banks(rng, K, m)
    cfg = ConfigBank(100, 'E7', 'matched', 1.0, b['T1'], b['T2'], r['T1'], r['T2'], uids, m, {0: (0, K * m)}); plan = BootstrapPlan.build('bf', 0, {0: uids}, 50, 9)
    thr = [(80.0, 400.0), (120.0, 600.0)]; res = bruteforce_check(cfg, thr, plan); assert res['ok'] and all(x['vector_equal'] and x['resampled_sums_equal'] for x in res['rows'])
    assert np.array_equal(row_loop_oracle(b['T1'], b['T2'], m, 80.0, 400.0), cfg.hit_tables(80.0, 400.0, 'model')[0].hits)
    st = bruteforce_detector_selftest(cfg, thr, plan); assert st['ok'] and st['zeroed_detected'] and st['permuted_detected']
