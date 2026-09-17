# -*- coding: utf-8 -*-
"""B-2 tranche 3: expansion decision (table 4), W2 position path (with an injectable cheap distance), two-system shared-latent fixture, position state integration."""
import os, sys, math, copy
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine.rules_config import RULES
from step1_engine.expansion import expansion_decision, family_expansion_plan
from step1_engine.positions import PositionBank, observed_w2max, null_max_sequence, w2_trigger, position_decision_unverified as position_decision, event_ratio_trigger, whitening_from_calibration, w2_exact
from step1_engine.orchestrator import ConfigBank, FittingBank, FamilyInput, evaluate_family
from step1_engine.bootstrap_plan import BootstrapPlan
from step1_engine.types import ClusterUID
from step1_engine.errors import InputContractError
from step1_engine.truth import UNKNOWN, TECH

# ---------- table 4
def test_expansion_once_precision_only():
    assert expansion_decision(1, 'N0', 'pass', 50, 40).action == 'keep'
    assert expansion_decision(1, 'N0', 'precision-unresolved', 5, 3).action == 'expand_to_4N0'
    assert expansion_decision(1, 'N4', 'precision-unresolved', 5, 3).action == 'precision-unresolved'
    d = expansion_decision(1, 'N4', 'precision-unresolved', 0, 3); assert d.action == 'precision-unresolved' and 'zero hits' in d.reason
    assert expansion_decision(1, 'N0', 'technical_fail', 0, 0).action == 'technical_fail'
    with pytest.raises(InputContractError): expansion_decision(1, 'N8', 'pass', 1, 1)
    plan = family_expansion_plan({100: dict(precision=dict(state='pass'), hits_M=50, hits_I=40), 101: dict(precision=dict(state='precision-unresolved'), hits_M=4, hits_I=2)}, 'N0')
    assert plan['family_status'] == 'expansion_pending' and plan['actions'][100]['action'] == 'keep' and plan['actions'][101]['action'] == 'expand_to_4N0'
    assert family_expansion_plan({100: dict(precision=dict(state='precision-unresolved'), hits_M=4, hits_I=2)}, 'N4')['family_status'] == 'precision-unresolved'

# ---------- W2 path with a cheap injectable distance (orchestration test; the registered production distance is exact OT)
def cheap_dist(a, b): return float(abs(a.mean(0) - b.mean(0)).max())

def make_positions(rng, K=600, m=10, shifts=(0.0, 0.0, 0.0), scale=1.0):
    banks = []
    for i, s in enumerate(shifts):
        Tw = rng.standard_normal((K * m, 2)) * scale + s; banks.append(PositionBank(i + 1, Tw, np.repeat(np.arange(K), m)))
    iso = PositionBank(0, rng.standard_normal((3000 * m, 2)) * scale, np.repeat(np.arange(3000), m)); return banks, iso

def test_w2_path_no_trigger_and_trigger():
    rng = np.random.default_rng(1); pos, iso = make_positions(rng)
    r = w2_trigger(pos, iso, 10, 20260914, dist=cheap_dist, obs_bounds={n: {s: 0.0 for s in RULES.seed_ids} for n in RULES.n_subs}, delta_q99_bound={n: 0.0 for n in RULES.n_subs})
    assert r['stop']['state'] in ('stopped', 'w2-unresolved') and r['validation']['state'] in ('valid', 'w2-unresolved')
    if r['validation']['state'] == 'valid': assert r['trigger'] is False
    pos2, iso2 = make_positions(np.random.default_rng(2), shifts=(0.0, 0.0, 0.8))
    r2 = w2_trigger(pos2, iso2, 10, 20260914, dist=cheap_dist, obs_bounds={n: {s: 0.0 for s in RULES.seed_ids} for n in RULES.n_subs}, delta_q99_bound={n: 0.0 for n in RULES.n_subs})
    assert r2['validation']['state'] == 'valid' and r2['trigger'] is True
    r3 = w2_trigger(pos2, iso2, 10, 20260914, dist=cheap_dist); assert r3['trigger'] == UNKNOWN and 'not supplied' in r3['validation']['reason']   # missing bounds never default to 0

def test_w2_path_contracts():
    rng = np.random.default_rng(3); pos, iso = make_positions(rng)
    with pytest.raises(InputContractError): observed_w2max(pos[:2], 2000, 10, 0, 1, cheap_dist)
    with pytest.raises(InputContractError): observed_w2max(pos, 2001, 10, 0, 1, cheap_dist)
    with pytest.raises(InputContractError): null_max_sequence(PositionBank(0, rng.standard_normal((100, 2)), np.repeat(np.arange(10), 10)), 2000, 10, 1, cheap_dist)
    nm = null_max_sequence(iso, 2000, 10, 1, cheap_dist, B_max=3); assert nm['values'].shape == (3,) and len(nm['blocks']) == 3 and all(len(set(sum(b, []))) == 3 * 200 for b in nm['blocks'])   # disjoint blocks, evidence returned
    with pytest.raises(InputContractError): observed_w2max([pos[0], pos[0], pos[0]], 2000, 10, 0, 1, cheap_dist)    # three distinct positions required
    with pytest.raises(InputContractError): observed_w2max(pos, 2000, 100, 0, 1, cheap_dist)                          # declared m disagrees with the banks' m
    with pytest.raises(InputContractError): PositionBank(1, np.array([[np.nan, 0.0]]), np.array([0]))
    mu, W = whitening_from_calibration(rng.standard_normal((5000, 2)) * [40, 200] + [120, 600]); assert np.abs(W @ np.cov((rng.standard_normal((5, 2))).T) @ W.T).shape == (2, 2)
    a = rng.standard_normal((50, 2)); b = a + 0.3; assert w2_exact(a, b) == pytest.approx(0.3 * math.sqrt(2), rel=1e-6)                         # exact OT on a pure translation

def test_event_ratio_and_position_state():
    P = {1: dict(P=0.004, precision='pass', hits=40, stage='N4'), 2: dict(P=0.010, precision='pass', hits=100, stage='N4'), 3: dict(P=0.005, precision='pass', hits=50, stage='N4')}
    t, info = event_ratio_trigger(P); assert t is True and info['ratio'] == pytest.approx(2.5)
    P2 = copy.deepcopy(P); P2[2]['P'] = 0.006; assert event_ratio_trigger(P2)[0] is False
    P3 = copy.deepcopy(P); P3[2]['precision'] = 'precision-unresolved'; assert event_ratio_trigger(P3)[0] == UNKNOWN
    P4 = copy.deepcopy(P); P4[2]['hits'] = 0; P4[2]['P'] = 0.0; P4[2]['precision'] = 'precision-unresolved'; t4, i4 = event_ratio_trigger(P4); assert t4 is True and i4.get('expansion_due_to_zero_hits')   # zero hits at N-final
    P0 = copy.deepcopy(P4); P0[2]['stage'] = 'N0'; assert event_ratio_trigger(P0)[0] == UNKNOWN                            # zero hits at N0: N expansion first
    for bad in (np.nan, np.inf, -0.01, 1.1):
        Pb = copy.deepcopy(P); Pb[2]['P'] = bad
        with pytest.raises(InputContractError): event_ratio_trigger(Pb)
    Pf = copy.deepcopy(P); Pf[2]['hits'] = 0.9
    with pytest.raises(InputContractError): event_ratio_trigger(Pf)
    P5 = copy.deepcopy(P); P5[1]['precision'] = 'technical_fail'; assert event_ratio_trigger(P5)[0] == TECH
    st = position_decision(dict(trigger=UNKNOWN), P); assert st['state'] == 'position-sensitive' and st['expand']
    st2 = position_decision(dict(trigger=False), P2); assert st2['state'] == 'not-expanded'
    st3 = position_decision(dict(trigger=UNKNOWN), P3); assert st3['state'] == 'position-unresolved'
    st4 = position_decision(dict(trigger=True), P5); assert st4['state'] == 'technical_fail'
    st5 = position_decision(dict(trigger=UNKNOWN), P4); assert st5['expansion_due_to_zero_hits'] is True

# ---------- two-system shared-latent fixture (rules §6.3: evaluation latent shared by all configurations AND both systems of a family)
def make_family_pair(rng, K=1000, m=10, shift=np.array([0.9, 0.8]), K_fit=2000, m_fit=10, B=200, group=1):
    z = rng.standard_normal((K * m, 2)); uids = [ClusterUID(1, 200, group, 0, i) for i in range(K)]; zf = rng.standard_normal((K_fit * m_fit, 2)); cidf = np.repeat(np.arange(K_fit), m_fit)
    def bank(system, eid, ref_scale, mod_shift):
        Tref = z * [40, 200] * ref_scale + [120, 600]; Tmod = (z - mod_shift) * [40, 200] * ref_scale + [120, 600]
        return ConfigBank(eid, 'E7', system, 1.0, Tmod[:, 0], Tmod[:, 1], Tref[:, 0], Tref[:, 1], uids, m, {0: (0, K * m)})
    plans = {s: BootstrapPlan.build(f'E7-g{group}-s{s}', s, {0: uids}, B, 20260914) for s in range(RULES.seeds)}
    fplans = {s: np.stack([np.bincount(rng.integers(0, K_fit, K_fit), minlength=K_fit) for _ in range(30)]) for s in range(RULES.seeds)}
    def fit(ref_scale, mod_shift): return FittingBank((zf - mod_shift) * [40, 200] * ref_scale + [120, 600], zf * [40, 200] * ref_scale + [120, 600], cidf)
    matched = FamilyInput('E7', [bank('matched', 100, 1.0, shift)], plans, {100: fit(1.0, shift)}, fplans)
    native = FamilyInput('E7', [bank('native', 150, 0.9, shift * 0.8)], plans, {150: fit(0.9, shift * 0.8)}, fplans)         # native reference transform differs (scale 0.9), latent identical
    return matched, native, z

def test_two_system_shared_latent_fixture():
    rng = np.random.default_rng(20260914); matched, native, z = make_family_pair(rng)
    cm, cn = matched.configs[0], native.configs[0]
    assert cm.cluster_uids == cn.cluster_uids and matched.plans[0] is native.plans[0]                                          # same evaluation latent UIDs and the same bootstrap plans across systems
    assert np.allclose((cn.T1_ref - 120) / 0.9, cm.T1_ref - 120) and np.allclose((cn.T2_ref - 600) / 0.9, cm.T2_ref - 600)     # references are different transforms of the SAME latent
    r = evaluate_family(matched, native, 80.0, 400.0); assert r.precision['state'] == 'pass' and r.native is not None and r.native['precision']['state'] in ('pass', 'precision-unresolved')
    assert r.truths['support'] is True
