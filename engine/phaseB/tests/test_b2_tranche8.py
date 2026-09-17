# -*- coding: utf-8 -*-
"""B-2 tranche 8: W2 family x size manifest (bind / verify / drift), fitting plan identity in evidence, adopted audit fixes (point precision, KDE inventory, coverage_ok)."""
import os, sys, copy, hashlib
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from step1_engine.rules_config import RULES
from step1_engine.positions import PositionBank, w2_trigger
from step1_engine.w2_manifest import build_w2_manifest, verify_w2_manifest, W2Manifest
from step1_engine.orchestrator import FamilyInput, evaluate_family
from step1_engine.bootstrap_plan import FittingPlan, bank_sha256
from step1_engine.errors import InputContractError
from step1_engine import serialization as ser
from test_b2_tranche3 import make_positions, cheap_dist
from test_b2_tranche4 import make_staged_family

def w2res(seed=4, shifts=(0.0, 0.0, 0.8)):
    rng = np.random.default_rng(seed); pos, iso = make_positions(rng, shifts=shifts)
    r = w2_trigger(pos, iso, 10, 20260914, dist=cheap_dist, obs_bounds={n: {s: 0.0 for s in RULES.seed_ids} for n in RULES.n_subs}, delta_q99_bound={n: 0.0 for n in RULES.n_subs}, whitening_identity=dict(source='test'))
    return pos, iso, r

def test_w2_manifest_build_verify_and_drift():
    pos, iso, r = w2res(); man = build_w2_manifest('E7', 'L1.00', pos, iso, r)
    v = verify_w2_manifest(man, pos, iso, r); assert v['verified'] and v['registered_distance'] is False and man.distance_kind.startswith('injected_test_callable')
    d = ser.loads(ser.dumps(man.as_dict())); man2 = W2Manifest(**d); assert verify_w2_manifest(man2, pos, iso, r)['verified']                  # strict JSON round trip
    with pytest.raises(InputContractError): verify_w2_manifest(man, pos, iso, r, require_registered_distance=True)                         # injected distance is not the registered production distance
    p2 = [PositionBank(p.position_id, p.Tw + 1e-9, p.cid) for p in pos]
    with pytest.raises(InputContractError): verify_w2_manifest(man, p2, iso, r)                                                             # bank drift
    r2 = copy.deepcopy(r); r2['evidence']['null'][2000]['values'][5] += 1e-6
    with pytest.raises(InputContractError): verify_w2_manifest(man, pos, iso, r2)                                                           # null sequence drift
    r3 = copy.deepcopy(r); r3['validation'] = dict(state='valid', trigger=False)
    with pytest.raises(InputContractError): verify_w2_manifest(man, pos, iso, r3)                                                           # validation record drift
    m3 = copy.deepcopy(man); m3.q99_at_B_final[2000] += 1e-6
    with pytest.raises(InputContractError): verify_w2_manifest(m3, pos, iso, r)
    with pytest.raises(InputContractError): build_w2_manifest('E7', 'L1.00', pos, iso, dict(stop=r['stop'], validation=r['validation']))  # no evidence -> cannot bind

def test_fitting_plan_identity_in_evidence():
    f = make_staged_family(np.random.default_rng(9), n_cfg=2); K = next(iter(f.fitting.values())).K
    f.fit_plans = {s: FittingPlan.build(f'fit{s}', 1, 7, s, K, 30, 20260914) for s in range(5)}; f.fitting_bindings = {e: bank_sha256(x.X_model, x.X_ref, x.cid) for e, x in f.fitting.items()}
    r = evaluate_family(f, None, 80.0, 400.0); ev = r.evidence
    assert ev['fitting_plan_binding'] == 'bound' and len(ev['fitting_plans']) == 5 and all(p['seed_id'] == i and p['crn_group_id'] == 7 and len(p['multiplicities_sha256']) == 64 for i, p in enumerate(ev['fitting_plans']))
    assert ev['fitting_bindings'] == f.fitting_bindings and ev['fitting_bank_sha256'] == f.fitting_bindings and ev['coverage_ok'] is True

def test_tranche9_verified_typed_result_feeds_position_decision():
    from step1_engine.w2_manifest import verified_w2_for_decision
    from step1_engine.positions import position_decision, VerifiedW2Decision
    pos, iso, r = w2res(); man = build_w2_manifest('E7', 'L1.00', pos, iso, r); v = verified_w2_for_decision(man, pos, iso, r)
    assert isinstance(v, VerifiedW2Decision) and v.trigger is True and v.check()
    P = {1: dict(P=.2, hits=20, N=100, precision='pass', stage='N4'), 2: dict(P=.25, hits=25, N=100, precision='pass', stage='N4'), 3: dict(P=.2, hits=20, N=100, precision='pass', stage='N4')}
    assert position_decision(v, P)['state'] == 'position-sensitive'
    bad = copy.deepcopy(r); bad['trigger'] = False
    with pytest.raises(InputContractError): verified_w2_for_decision(man, pos, iso, bad)                                                   # unverified raw dict is never consumed
    assert 'inputs' in r['evidence'] and r['evidence']['inputs']['distance_kind'].startswith('injected_test_callable')
    with pytest.raises(InputContractError): position_decision(dict(trigger=True, verified=True), P)                                          # self-declared 'verified' dict is not accepted
    forged = VerifiedW2Decision(False, v.validation_state, v.validation_reason, v.B_final, v.observed_hash, v.distance_kind, v.scope, v.checksum)
    with pytest.raises(InputContractError): position_decision(forged, P)                                                                      # content/checksum mismatch rejected at intake
    assert man.validation is not r['validation'] and man.bounds is not r['evidence']['bounds']                                            # manifest is an independent snapshot (no mutable alias)
