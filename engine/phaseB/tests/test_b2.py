# -*- coding: utf-8 -*-
"""B-2 first tranche: quantity adapter, KDE literal/frequency-weight equivalence, fail-closed logD, orchestrator multi-family integration (synthetic banks)."""
import os, sys, math, json
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine.rules_config import RULES
from step1_engine.ci import ci_from_replicates, CIResult
from step1_engine.precision import precision_state
from step1_engine.quantity import ratio_quantity, logD_quantity
from step1_engine.density import kde_logpdf_weighted, kde_logpdf_literal, logD_with_ci, logD_at, check_multiplicities
from step1_engine.bootstrap_plan import BootstrapPlan
from step1_engine.types import ClusterUID
from step1_engine.orchestrator import ConfigBank, FittingBank, FamilyInput, evaluate_threshold, calibrate_pseudo
from step1_engine.decision import CoreInputs, decide_core
from step1_engine.errors import InputContractError
from step1_engine.truth import UNKNOWN, TECH

def seeds5(num, den): return [ci_from_replicates(num, den, mode='Q', seed_id=s) for s in range(5)]

# ---------- quantity adapter (audit §4): boundary -> unresolved -> unknown, never a definite False
def test_quantity_boundary_is_unknown_not_false():
    num = np.full(2000, 1.0); den = np.full(2000, 1.0); den[:100] = 0.0                              # boundary +inf replicates -> precision-unresolved
    s5 = seeds5(num, den); p = precision_state(s5[0], s5, 1.0, 100, 100); q = ratio_quantity('Q_matched', s5[0], p, 1.0)
    assert q.audit == 'unresolved' and q.lower is None and q.ci_math_state == 'boundary'
    d = decide_core(CoreInputs(q.audit, 'pass', 'not_computed_by_registered_short_circuit', 'pass', q.lower, q.upper, 0.5, None, None, 1.5, 2.0))
    assert d.support_truth == UNKNOWN and d.unsupported_truth == UNKNOWN and d.technical_status == 'ok'        # not False, not technical
    bad = ci_from_replicates([np.nan], [1.0], seed_id=0); qt = ratio_quantity('Q', bad, None, None); assert qt.audit == 'technical_fail'
    s5 = seeds5(np.linspace(11, 13, 2000), np.ones(2000)); p = precision_state(s5[0], s5, 12.0, 100, 100); q = ratio_quantity('Q', s5[0], p, 12.0); assert q.audit == 'pass' and math.isfinite(q.lower)
    with pytest.raises(InputContractError): ratio_quantity('Q', s5[0], None, 12.0)

def test_logD_quantity_fail_closed_and_short_circuit():
    assert logD_quantity('D', None, None).audit == 'not_computed_by_registered_short_circuit'
    assert logD_quantity('D', 0.3, None).audit == 'not_computed_by_registered_short_circuit' and logD_quantity('D', 0.3, None).point == 0.3
    assert logD_quantity('D', math.inf, None).audit == 'technical_fail'
    bad = CIResult('logD', None, None, None, None, 'none', 'technical_fail', dict(technical_invalid=1), 0.05, 2000, 'x', 0); assert logD_quantity('D', 0.3, bad).audit == 'technical_fail'
    ok = CIResult('logD', 0.1, 0.9, None, None, 'linear_logD', 'finite', dict(finite=2000, technical_invalid=0), 0.05, 2000, None, 0); assert logD_quantity('D', 0.3, ok).audit == 'pass'

# ---------- KDE: frequency-weight == literal (R5), bandwidth scaling, fail-closed replicate
def test_kde_weighted_equals_literal():
    rng = np.random.default_rng(0); K, m = 150, 20; X = rng.normal(size=(K * m, 2)) * [40, 200] + [120, 600]; cid = np.repeat(np.arange(K), m)
    pts = np.array([[39.67, 259.34], [120, 600], [300, 1200]])
    for _ in range(3):
        mult = np.bincount(rng.integers(0, K, K), minlength=K)
        for fs in (1.0, 0.7, 1.4):
            a = kde_logpdf_weighted(X, mult[cid].astype(float), pts, fs); b = kde_logpdf_literal(X, mult[cid], pts, fs); assert np.allclose(a, b, rtol=0, atol=1e-10)
    assert np.allclose(kde_logpdf_weighted(X, np.ones(K * m), pts), kde_logpdf_literal(X, np.ones(K * m, int), pts), atol=1e-10)

def test_logD_ci_fail_closed_on_singular_replicate():
    rng = np.random.default_rng(1); K, m = 40, 10; X = rng.normal(size=(K * m, 2)); cid = np.repeat(np.arange(K), m); Y = X + 0.2
    plans = np.stack([np.bincount(rng.integers(0, K, K), minlength=K) for _ in range(20)])
    r = logD_with_ci(X, cid, Y, cid, np.array([0.0, 0.0]), plans, plans); assert r.ci.math_state == 'finite' and r.n_failed == 0
    Xs = X.copy(); Xs[cid == 0] = Xs[cid == 0][0]                                                     # cluster 0 degenerate: a replicate made only of cluster 0 is singular
    deg = plans.copy(); deg[3] = 0; deg[3, 0] = K
    r2 = logD_with_ci(Xs, cid, Y, cid, np.array([0.0, 0.0]), deg, deg); assert r2.n_failed == 1 and r2.ci.math_state == 'technical_fail' and r2.ci.log_lower is None and r2.ci.counts['technical_invalid'] == 1 and r2.invalid_mask.sum() == 1
    for bad in (np.nan, -1.0, 0.5):
        M = plans.astype(float); M[2, int(np.flatnonzero(M[2] > 0)[0])] = bad
        with pytest.raises(InputContractError): logD_with_ci(X, cid, Y, cid, np.array([0.0, 0.0]), M, plans)              # invalid multiplicities are rejected, never dropped
    with pytest.raises(InputContractError): logD_with_ci(X, np.where(np.arange(K * m) == 0, -1, cid), Y, cid, np.array([0.0, 0.0]), plans, plans)

# ---------- orchestrator multi-family integration fixture
def make_family(name, group, n_cfg, K, m, shift, rng, weights=None, prefix_only_cfg=None, native=False, B=200, K_fit=60, m_fit=10, shifts=None):
    """CRN-faithful synthetic family: ONE maximal latent draw z (K_max clusters) for the family's CRN group; every configuration/system is a transformation of the SAME latent
    (reference = z, model = z - shift_j); configurations with N0 only use the shared prefix (batch 0); the extension batch is the same latent for every extended configuration.
    Fitting banks use an independent latent (separate purpose namespace) shared within the family."""
    K_max = 4 * K; z = rng.standard_normal((K_max * m, 2)); purpose = 201 if native else 200
    uids_all = [ClusterUID(1, purpose, group, 0, i) for i in range(K)] + [ClusterUID(1, purpose, group, 1, i) for i in range(3 * K)]
    cfgs = []
    for j in range(n_cfg):
        sj = shift if shifts is None else shifts[j]; ext = prefix_only_cfg is not None and j != prefix_only_cfg
        n = K_max * m if ext else K * m; zz = z[:n]; Tref = zz * [40, 200] + [120, 600]; Tmod = (zz - sj) * [40, 200] + [120, 600]
        uids = uids_all if ext else uids_all[:K]; batches = {0: (0, K * m), 1: (K * m, n)} if ext else {0: (0, n)}
        cfgs.append(ConfigBank(100 * group + j, name, 'native' if native else 'matched', 1.0 / n_cfg if weights is None else weights[j], Tmod[:, 0], Tmod[:, 1], Tref[:, 0], Tref[:, 1], uids, m, batches))
    strata = {0: uids_all[:K]} | ({1: uids_all[K:]} if any(len(c.batches) == 2 for c in cfgs) else {})
    plans = {s: BootstrapPlan.build(f'{name}-g{group}-s{s}', s, strata, B, 20260914) for s in range(RULES.seeds)}
    zf = rng.standard_normal((K_fit * m_fit, 2)); fit = {}
    for j, c in enumerate(cfgs):
        sj = shift if shifts is None else shifts[j]; fit[c.evaluation_id] = FittingBank((zf - sj) * [40, 200] + [120, 600], zf * [40, 200] + [120, 600], np.repeat(np.arange(K_fit), m_fit))
    fplans = {s: np.stack([np.bincount(rng.integers(0, K_fit, K_fit), minlength=K_fit) for _ in range(30)]) for s in range(RULES.seeds)}
    return FamilyInput(name, cfgs, plans, fit, fplans)

def build_fixture(K=1000, m=10, shift=np.array([0.9, 0.8]), rng=None, K_fit=2000, m_fit=10):
    rng = rng or np.random.default_rng(20260914)
    A = make_family('E7', 1, 2, K, m, shift, rng, prefix_only_cfg=0, K_fit=K_fit, m_fit=m_fit); An = make_family('E7', 2, 2, K, m, shift * 0.8, rng, prefix_only_cfg=0, native=True, K_fit=K_fit, m_fit=m_fit)
    Bf = make_family('E2', 3, 1, K, m, np.array([0.05, 0.05]), rng, K_fit=K_fit, m_fit=m_fit); Bn = make_family('E2', 4, 1, K, m, np.array([0.05, 0.05]), rng, native=True, K_fit=K_fit, m_fit=m_fit)
    return {'E7': (A, An), 'E2': (Bf, Bn)}
THR = (80.0, 400.0)   # registered-style tail thresholds for the synthetic fixture (P_ref ~ 2.5%)

def test_fixture_is_crn_faithful():
    fam = build_fixture()['E7'][0]; c0, c1 = fam.configs
    assert np.array_equal(c0.T1_ref, c1.T1_ref[:len(c0.T1_ref)]) and np.array_equal(c0.T2_ref, c1.T2_ref[:len(c0.T2_ref)])   # same latent, same reference transform on the shared prefix
    assert c0.cluster_uids == c1.cluster_uids[:len(c0.cluster_uids)]    # same UIDs and same prefix latent
    assert len(c1.batches) == 2 and fam.plans[0].strata[1][0].batch_id == 1

def test_integration_supported_family_and_null_family():
    fam = build_fixture(); res = evaluate_threshold(fam, *THR)
    r7, r2 = res['E7'], res['E2']
    assert r7.Q_point > 3 and r7.precision['state'] == 'pass' and r7.decision['display_label'] in ('support', 'strong') and r7.truths['support'] is True
    assert r2.decision['display_label'] in ('inconclusive', 'unsupported') and r2.truths['support'] in (False, UNKNOWN)
    strong = build_fixture(shift=np.array([1.4, 1.3])); rs = evaluate_threshold(strong, *THR)['E7']
    assert rs.Q_ci_seed0['lower'] >= 10 and 'logD_CI=computed' in rs.notes and rs.logD['ci'] is not None and rs.decision['display_label'] in ('strong', 'support')   # §1.4 dependency: CI computed for a strong candidate
    for r in res.values(): json.dumps(r.as_dict(), allow_nan=False)                                       # strict JSON for archive
    assert set(r7.per_config) == {100, 101} and r7.per_config[101]['ci_seed0']['B'] == 200 and r7.native is not None and r7.native['precision']['state'] in ('pass', 'precision-unresolved')
    assert r7.evidence['matched']['prior'] == [0.5, 0.5] and len(r7.evidence['cis_all_seeds']) == 5 and set(r7.logD['per_point_audits']) == {100, 101}

def test_integration_precision_unresolved_gives_unknown_not_false():
    fam = build_fixture(K=150, m=10); r = evaluate_threshold(fam, *THR)['E7']                                # small bank: positive clusters < 50 -> precision-unresolved while the KDE point audit passes
    assert r.precision['state'] == 'precision-unresolved' and r.logD['sensitivity_pass'] and r.truths['support'] == UNKNOWN and r.truths['unsupported'] == UNKNOWN   # unresolved -> unknown, never a definite False

def test_integration_technical_bank_is_rejected():
    fam = build_fixture(); c = fam['E7'][0].configs[0]; T = c.T1_model.copy(); T[5] = np.nan
    import copy
    f = copy.deepcopy(fam['E7'][0]); f.configs[0].weight = 1.0
    with pytest.raises(InputContractError): evaluate_threshold({'E7': (f, None)}, *THR)                                     # prior sums to 1.5: never renormalised
    with pytest.raises(InputContractError): ConfigBank(c.evaluation_id, c.family, c.system, c.weight, T, c.T2_model, c.T1_ref, c.T2_ref, c.cluster_uids, c.m, c.batches)

def test_integration_short_circuit_recorded_and_pseudo_calibration():
    fam = build_fixture(); res = evaluate_threshold(fam, *THR)                                             # Q ~ 8: L_Q < 10 and U_Q > 1 -> logD CI not required
    assert any('not_computed_by_registered_short_circuit' in n for n in res['E7'].notes) and res['E7'].decision['ci_computation_status']['logD_CI'] == 'not_computed_by_registered_short_circuit'
    rng = np.random.default_rng(5); pT1 = rng.normal(120, 40, 6); pT2 = rng.normal(600, 200, 6)            # small pseudo battery (path check only)
    summ, truths = calibrate_pseudo(fam, pT1, pT2, 'support'); assert summ.n == 6 and summ.status == 'ok' and all(t in (True, False, UNKNOWN) for t in truths)
    summ_s, _ = calibrate_pseudo(fam, pT1, pT2, 'strong'); assert summ_s.threshold == RULES.usable_strong
