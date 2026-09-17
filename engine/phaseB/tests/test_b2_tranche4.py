# -*- coding: utf-8 -*-
"""B-2 tranche 4: staged evaluation (N0 -> single 4N0 expansion), position probabilities from real per-config results, evidence retention on the W2 path, solver gate."""
import os, sys, copy, math, types, warnings
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine.rules_config import RULES
from step1_engine.orchestrator import ConfigBank, FittingBank, FamilyInput, evaluate_family, evaluate_family_staged, evaluate_threshold, position_probabilities, calibrate_pseudo
from step1_engine.expansion import family_expansion_plan
from step1_engine.positions import PositionBank, w2_trigger, position_decision_unverified as position_decision, w2_exact
from step1_engine.bootstrap_plan import BootstrapPlan
from step1_engine.types import ClusterUID
from step1_engine.errors import InputContractError
from step1_engine.truth import UNKNOWN, TECH
from step1_engine import serialization as ser
sys.path.insert(0, os.path.dirname(__file__)); from test_b2_tranche3 import make_family_pair, cheap_dist, make_positions

def make_staged_family(rng, K0=200, m=10, shift=np.array([0.9, 0.8]), K_fit=1500, m_fit=10, B=200, group=7, n_cfg=3):
    """Three configurations (observer positions of one shape) sharing one latent; small N0 so that the gate fails at N0 and passes after the registered 4x extension."""
    Kmax = 4 * K0; z = rng.standard_normal((Kmax * m, 2)); uids = [ClusterUID(1, 200, group, 0, i) for i in range(K0)] + [ClusterUID(1, 200, group, 1, i) for i in range(3 * K0)]
    cfgs = []
    for j in range(n_cfg):
        Tref = z * [40, 200] + [120, 600]; Tmod = (z - shift * (1.0 + 0.02 * j)) * [40, 200] + [120, 600]
        cfgs.append(ConfigBank(100 + j, 'E7', 'matched', 1.0 / n_cfg, Tmod[:, 0], Tmod[:, 1], Tref[:, 0], Tref[:, 1], uids, m, {0: (0, K0 * m), 1: (K0 * m, Kmax * m)}))
    plans = {s: BootstrapPlan.build(f'E7-g{group}-s{s}', s, {0: uids[:K0], 1: uids[K0:]}, B, 20260914) for s in range(RULES.seeds)}
    zf = rng.standard_normal((K_fit * m_fit, 2)); cidf = np.repeat(np.arange(K_fit), m_fit)
    fit = {c.evaluation_id: FittingBank((zf - shift * (1.0 + 0.02 * j)) * [40, 200] + [120, 600], zf * [40, 200] + [120, 600], cidf) for j, c in enumerate(cfgs)}
    fplans = {s: np.stack([np.bincount(rng.integers(0, K_fit, K_fit), minlength=K_fit) for _ in range(30)]) for s in range(RULES.seeds)}
    return FamilyInput('E7', cfgs, plans, fit, fplans)

def test_staged_evaluation_expands_once_and_records_stages():
    fam = make_staged_family(np.random.default_rng(1)); thr = (80.0, 400.0)
    r0 = evaluate_family(fam._replace(configs=[c.at_stage('N0') for c in fam.configs]) if hasattr(fam, '_replace') else FamilyInput(fam.family, [c.at_stage('N0') for c in fam.configs], fam.plans, fam.fitting, fam.fit_plans), None, *thr)
    assert all(d['stage'] == 'N0' and d['N'] == 2000 for d in r0.per_config.values()) and r0.precision['state'] != 'pass'                 # N0 prefix: 2000 rows, gate unmet
    plan0 = family_expansion_plan(r0.per_config, 'N0', expected_ids=[100, 101, 102]); assert plan0['family_status'] == 'expansion_pending'
    r = evaluate_family_staged(fam, None, *thr)
    ex = r.evidence['expansion']['matched']; assert ex['plan']['family_status'] == 'expansion_pending' and set(ex['stages'].values()) == {'N4'} and ex['kde'] == 'not_evaluated_in_N_selection'
    assert all(d['stage'] == 'N4' and d['N'] == 8000 for d in r.per_config.values()) and r.precision['state'] == 'pass' and r.truths['support'] is True
    assert r.evidence['expansion']['native'] is None and 'per-system' in r.evidence['expansion']['rule']
    with pytest.raises(InputContractError): fam.configs[0].at_stage('N8')

def test_staged_without_extension_becomes_unresolved_not_deleted():
    fam = make_staged_family(np.random.default_rng(2)); c = fam.configs[1]
    noext = ConfigBank(c.evaluation_id, c.family, c.system, c.weight, c.T1_model[:2000], c.T2_model[:2000], c.T1_ref[:2000], c.T2_ref[:2000], c.cluster_uids[:200], c.m, {0: (0, 2000)})
    fam2 = FamilyInput(fam.family, [fam.configs[0], noext, fam.configs[2]], fam.plans, fam.fitting, fam.fit_plans)
    r = evaluate_family_staged(fam2, None, 80.0, 400.0)
    assert r.per_config[101]['stage'] == 'N0' and 'no extension registered' in r.per_config[101].get('stage_note', '') and r.precision['state'] == 'precision-unresolved'
    with pytest.raises(InputContractError): ConfigBank(c.evaluation_id, c.family, c.system, c.weight, c.T1_model[:4000], c.T2_model[:4000], c.T1_ref[:4000], c.T2_ref[:4000], c.cluster_uids[:400], c.m, {0: (0, 2000), 1: (2000, 4000)})   # 2x is not the registered expansion
    assert set(r.per_config) == {100, 101, 102} and r.evidence['matched']['prior'] == [1 / 3] * 3                                          # retained, not deleted or renormalised
    assert r.truths['support'] == UNKNOWN

def test_position_probabilities_and_decision_from_real_results():
    fam = make_staged_family(np.random.default_rng(3)); r = evaluate_family_staged(fam, None, 80.0, 400.0)
    P = position_probabilities(r, {100: 1, 101: 2, 102: 3}); assert set(P) == {1, 2, 3} and all(v['stage'] == 'N4' and isinstance(v['hits'], int) for v in P.values())
    st = position_decision(dict(trigger=False), P); assert st['state'] in ('not-expanded', 'position-sensitive', 'position-unresolved') and st['ratio_trigger'] is not TECH
    r0 = evaluate_family(FamilyInput(fam.family, [c.at_stage('N0') for c in fam.configs], fam.plans, fam.fitting, fam.fit_plans), None, 80.0, 400.0)
    P0 = position_probabilities(r0, {100: 1, 101: 2, 102: 3}); st0 = position_decision(dict(trigger=False), P0); assert st0['state'] != 'position-sensitive' and st0['ratio_trigger'] == UNKNOWN   # N0 unresolved: no position expansion yet

def test_w2_evidence_retained_and_strict_json():
    rng = np.random.default_rng(4); pos, iso = make_positions(rng, shifts=(0.0, 0.0, 0.8))
    r = w2_trigger(pos, iso, 10, 20260914, dist=cheap_dist, obs_bounds={n: {s: 0.0 for s in RULES.seed_ids} for n in RULES.n_subs}, delta_q99_bound={n: 0.0 for n in RULES.n_subs}, whitening_identity=dict(source='test'))
    ev = r['evidence']; assert ev['distance_kind'].startswith('injected_test_callable') and set(ev['observed']) == set(RULES.n_subs)
    for n in RULES.n_subs:
        assert len(ev['null'][n]['values']) == RULES.B_levels[-1] and len(ev['null'][n]['blocks']) == RULES.B_levels[-1] and set(ev['null'][n]['pairwise'][0]) == {'P1P2', 'P1P3', 'P2P3'}
        for s in RULES.seed_ids: assert set(ev['observed'][n][s]['subsets']) == {1, 2, 3} and len(ev['observed'][n][s]['subsets'][1]) == n // 10
    d = ser.loads(ser.dumps(r)); assert d['trigger'] is True and d['evidence']['null'][2000]['values'][:3] == ev['null'][2000]['values'][:3]
    from step1_engine.positions import DISTANCE_KINDS
    assert DISTANCE_KINDS['exact_pot_w2'] is w2_exact

def test_solver_gate_rejects_warning_and_nonoptimal(monkeypatch):
    fake = types.ModuleType('ot'); fake.dist = lambda a, b, metric: np.zeros((len(a), len(b)))
    def emd_warn(*a, **k): warnings.warn('injected', UserWarning); return [4.0, dict(warning='non-optimal', result_code=3)]
    fake.emd2 = emd_warn; monkeypatch.setitem(sys.modules, 'ot', fake)
    with pytest.raises(InputContractError): w2_exact(np.zeros((3, 2)), np.ones((3, 2)))
    fake.emd2 = lambda *a, **k: [4.0, dict(warning=None, result_code=3)]
    with pytest.raises(InputContractError): w2_exact(np.zeros((3, 2)), np.ones((3, 2)))                  # non-optimal result_code without a warning
    fake.emd2 = lambda *a, **k: [np.nan, dict(warning=None, result_code=1)]
    with pytest.raises(InputContractError): w2_exact(np.zeros((3, 2)), np.ones((3, 2)))
    fake.emd2 = lambda *a, **k: [4.0, dict(warning=None, result_code=1)]
    assert w2_exact(np.zeros((3, 2)), np.ones((3, 2))) == 2.0
    for bad in (lambda *a, **k: 4.0, lambda *a, **k: [4.0, {}], lambda *a, **k: [4.0, dict(warning=None, result_code=1.9)], lambda *a, **k: [4.0, dict(warning=None, result_code=True)]):
        fake.emd2 = bad
        with pytest.raises(InputContractError): w2_exact(np.zeros((3, 2)), np.ones((3, 2)))                    # missing/malformed solver metadata is never 'optimal'

def test_staged_threshold_and_pseudo_path():
    fam = make_staged_family(np.random.default_rng(5)); fams = {'E7': (fam, None)}
    res = evaluate_threshold(fams, 80.0, 400.0, staged=True); assert res['E7'].per_config[100]['stage'] == 'N4' and res['E7'].position_status['state'] == 'not-integrated'
    summ, truths = calibrate_pseudo(fams, np.array([80.0, 200.0]), np.array([400.0, 900.0]), 'support', staged=True); assert summ.n == 2 and summ.status == 'ok' and 'core-only' in summ.reason
    pm = {'E7': {100: 1, 101: 2, 102: 3}}; res2 = evaluate_threshold(fams, 80.0, 400.0, staged=True, position_maps=pm)                     # position status integrated into the staged entry (W2 assets absent -> unresolved)
    assert res2['E7'].position_status['state'] in ('position-unresolved', 'position-sensitive') and res2['E7'].evidence['position']['w2']['reason'] == 'W2 assets not supplied'
    from step1_engine.positions import W2NotEvaluated
    summ2, _ = calibrate_pseudo(fams, np.array([80.0]), np.array([400.0]), 'support', staged=True, position_maps=pm, w2_results={'E7': W2NotEvaluated('test')}); assert '3-position' in summ2.reason
    with pytest.raises(InputContractError): evaluate_threshold(fams, 80.0, 400.0, staged=True, position_maps=pm, w2_results={'E7': dict(trigger=False)})   # raw dict rejected at the production entry
    from step1_engine.positions import norm_position_probability
    with pytest.raises(InputContractError): norm_position_probability(1, dict(P=0.1, hits=0, precision='pass', stage='N4'))
    with pytest.raises(InputContractError): norm_position_probability(1, dict(P=0.0, hits=3, precision='precision-unresolved', stage='N4'))
    with pytest.raises(InputContractError): norm_position_probability(1, dict(P=0.5, hits=3, N=10, precision='pass', stage='N4'))
