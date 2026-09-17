# -*- coding: utf-8 -*-
"""B-2 tranche 5: per-system staging, technical precedence over expansion, N4 = 4xN0 contract, position integration, FittingPlan binding, checkpoint write/read re-validation."""
import os, sys, copy, json, tempfile, hashlib
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from step1_engine.rules_config import RULES
from step1_engine.orchestrator import FamilyInput, FittingBank, evaluate_family_staged, evaluate_family, _stage_family
from step1_engine.bootstrap_plan import FittingPlan
from step1_engine.checkpoint import write_family_result, read_family_result, binding_manifest
from step1_engine.errors import InputContractError
from step1_engine.truth import UNKNOWN, TECH
from test_b2_tranche3 import make_family_pair
from test_b2_tranche4 import make_staged_family

def test_fitting_plan_binding():
    fam = make_staged_family(np.random.default_rng(9), n_cfg=1); fb = fam.fitting[100]
    sha = hashlib.sha256(np.ascontiguousarray(fb.X_model).tobytes() + np.ascontiguousarray(fb.X_ref).tobytes() + np.ascontiguousarray(fb.cid).tobytes()).hexdigest()
    plans = {s: FittingPlan.build(f'fit-s{s}', 1, 7, s, fb.K, 30, 20260914, sha) for s in range(RULES.seeds)}
    f2 = FamilyInput(fam.family, fam.configs, fam.plans, fam.fitting, plans); f2.validate(); assert f2.fitting_plan_binding == 'bound'
    r = evaluate_family_staged(f2, None, 80.0, 400.0); assert r.evidence['fitting_plan_binding'] == 'bound'
    other = FittingBank(fb.X_model + 1.0, fb.X_ref, fb.cid)
    with pytest.raises(InputContractError): FamilyInput(fam.family, fam.configs, fam.plans, {100: other}, plans).validate()          # plan bound to a different bank (array SHA)
    bad = copy.deepcopy(plans); bad[1] = plans[0]
    with pytest.raises(InputContractError): FamilyInput(fam.family, fam.configs, fam.plans, fam.fitting, bad).validate()            # seed relabelling
    p = copy.deepcopy(plans[0]); p.rng_key[3] = 99
    with pytest.raises(InputContractError): p.validate()                                                                             # key/identity mismatch
    assert fam.validate() is not None and 'unbound' in fam.fitting_plan_binding                                                       # bare arrays remain test-only

def test_checkpoint_roundtrip_and_rejections(tmp_path):
    fm, fn, _ = make_family_pair(np.random.default_rng(20260914)); r = evaluate_family_staged(fm, fn, 80.0, 400.0)
    p = str(tmp_path / 'fam.json'); sha = write_family_result(r, p, extra=dict(threshold=[80.0, 400.0]))
    payload = read_family_result(p, expected_sha256=sha); assert payload['result']['truths'] == r.truths and payload['binding']['engine_version'] == binding_manifest()['engine_version']
    with pytest.raises(InputContractError): read_family_result(p, expected_sha256='0' * 64)
    raw = json.load(open(p)); raw['binding']['tables_sha256'] = '0' * 64; json.dump(raw, open(str(tmp_path / 'b.json'), 'w'))
    with pytest.raises(InputContractError): read_family_result(str(tmp_path / 'b.json'))                                              # foreign binding
    raw = json.load(open(p)); raw['result']['Q_ci_seed0']['log_lower'] = 0.0; json.dump(raw, open(str(tmp_path / 'c.json'), 'w'))
    with pytest.raises(InputContractError): read_family_result(str(tmp_path / 'c.json'))                                              # stored interval does not reproduce from stored num/den
    raw = json.load(open(p)); raw['binding']['modules']['ci.py'] = '0' * 64; json.dump(raw, open(str(tmp_path / 'd.json'), 'w'))
    with pytest.raises(InputContractError): read_family_result(str(tmp_path / 'd.json'))

def test_two_system_staged_and_technical_precedence(monkeypatch):
    fm, fn, _ = make_family_pair(np.random.default_rng(20260914)); r = evaluate_family_staged(fm, fn, 80.0, 400.0)
    assert r.native is not None and r.evidence['expansion']['native'] is not None and r.evidence['expansion']['matched']['kde'] == 'not_evaluated_in_N_selection'
    import step1_engine.orchestrator as o
    fam = make_staged_family(np.random.default_rng(1)); calls = []
    orig = o._family_Q
    def q_tech(*a, **k):
        calls.append(1); Q, cis, prec, per, w, ev = orig(*a, **k)
        if len(calls) == 1:
            from step1_engine.precision import PrecisionState; prec = PrecisionState('technical_fail', None, None, 0, 0, ['injected']); per[100]['precision']['state'] = 'technical_fail'
        return Q, cis, prec, per, w, ev
    monkeypatch.setattr(o, '_family_Q', q_tech); r2 = o.evaluate_family_staged(fam, None, 80.0, 400.0)
    assert 'fail-closed' in ' '.join(r2.notes) and set(r2.evidence['expansion']['matched']['stages'].values()) == {'N0'}                 # Q-layer technical failure at N0: no expansion
    assert r2.decision['technical_status'] == 'technical_fail' and r2.truths == dict(support=TECH, strong=TECH, unsupported=TECH) and len(calls) == 1   # explicit failed result, no re-evaluation

def test_tranche7_extended_Q_roundtrip_and_failed_record_schema(tmp_path):
    fm, fn, _ = make_family_pair(np.random.default_rng(20260914))
    for fa in (fm, fn):
        for c in fa.configs: c.T1_ref = np.full_like(c.T1_ref, 1000.0); c.T2_ref = np.full_like(c.T2_ref, 1000.0)
    r = evaluate_family(fm, fn, 80.0, 400.0); assert r.Q_point is None and r.evidence['matched']['Q_point_math_state'] == 'positive_infinite' and r.truths['support'] == UNKNOWN
    p = str(tmp_path / 'inf.json'); sha = write_family_result(r, p); got = read_family_result(p, sha); assert got['verified'].startswith('verified') and got['result']['truths'] == r.truths
    import step1_engine.orchestrator as o
    from unittest.mock import patch
    from step1_engine.precision import PrecisionState
    fm2, fn2, _ = make_family_pair(np.random.default_rng(20260914)); orig = o._family_Q; calls = []
    def fail_once(f, *a, **k):
        calls.append(1); Q, cis, prec, per, w, ev = orig(f, *a, **k)
        if len(calls) == 1: prec = PrecisionState('technical_fail', None, None, 0, 0, ['inj']); per[next(iter(per))]['precision']['state'] = 'technical_fail'
        return Q, cis, prec, per, w, ev
    with patch.object(o, '_family_Q', fail_once): fr = o.evaluate_family_staged(fm2, fn2, 80.0, 400.0)
    assert fr.evidence['failed_record']['kind'] == 'N_selection_technical_failure' and fr.position_status['state'] == 'position_not_evaluated_due_to_N_selection_failure'
    p2 = str(tmp_path / 'fail.json'); sha2 = write_family_result(fr, p2); assert read_family_result(p2, sha2)['verified'].startswith('technical_fail_record')
    bad = copy.deepcopy(fr); bad.truths = dict(support=True, strong=True, unsupported=False); bad.decision.update(technical_status='ok', display_label='strong', support_truth=True, strong_truth=True, unsupported_truth=False)
    p3 = str(tmp_path / 'bad.json'); sha3 = write_family_result(bad, p3)
    with pytest.raises(InputContractError): read_family_result(p3, sha3)
    raw = json.load(open(p)); raw['binding']['execution_profile']['kind'] = 'registered-size'; json.dump(raw, open(str(tmp_path / 'ep.json'), 'w'))
    with pytest.raises(InputContractError): read_family_result(str(tmp_path / 'ep.json'))                                            # execution profile must describe the stored result
