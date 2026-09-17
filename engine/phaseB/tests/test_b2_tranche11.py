# -*- coding: utf-8 -*-
"""B-2 tranche 11: VerifiedW2Decision schema (adopted audit fix), 12-position stage: registered generator manifest, determinism, transition record, after_twelve semantics."""
import os, sys, copy, json
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from step1_engine.rules_config import RULES
from step1_engine.stage12 import generate_twelve, verify_twelve, transition_after_three, after_twelve, TwelvePositionManifest
from step1_engine.positions import VerifiedW2Decision, position_decision
from step1_engine.errors import InputContractError
from step1_engine.truth import UNKNOWN
from step1_engine import serialization as ser
E7_ANCHORS = np.array([[0.11278702805018147], [0.04504442885635738], [0.17608175443077442]])   # frozen A6 pilot_v2_reduced (full precision)

def test_verified_w2_schema():
    ok = VerifiedW2Decision.issue(True, dict(state='valid', trigger=True), 400, 'h', 'exact_pot_w2', 's'); assert ok.check()
    for bad in [dict(trigger=1, validation=dict(state='valid', trigger=True), B=400), dict(trigger=False, validation=dict(state='valid', trigger=True), B=400), dict(trigger=UNKNOWN, validation=dict(state='technical_fail'), B=400),
                dict(trigger=True, validation=dict(state='valid', trigger=True), B=400.5), dict(trigger=True, validation=dict(state='valid', trigger=True), B='400'), dict(trigger=True, validation=dict(state='valid', trigger=True), B=401)]:
        with pytest.raises(InputContractError): VerifiedW2Decision.issue(bad['trigger'], bad['validation'], bad['B'], 'h', 'k', 's')
    from dataclasses import replace
    with pytest.raises(InputContractError): replace(ok, B_final=400.5).check()

def test_twelve_generator_e7_matches_reference_and_is_deterministic():
    m = generate_twelve('E7', 'L1.00', E7_ANCHORS); assert len(m.points) == 12 and m.points[:3] == E7_ANCHORS.tolist() and m.min_pairwise >= RULES.min_sep['E7'] and abs(sum(m.weights) - 1) < 1e-12
    assert [round(p[0], 4) for p in m.added] == [0.23, 0.0789, 0.1444, 0.203, 0.02, 0.062, 0.0958, 0.1286, 0.1602]                       # ChatGPT independent reference (draft3 audit)
    assert verify_twelve(m) and generate_twelve('E7', 'L1.00', E7_ANCHORS).sha256 == m.sha256
    d = ser.loads(ser.dumps(m.as_dict())); assert verify_twelve(TwelvePositionManifest(**d))
    bad = copy.deepcopy(m); bad.points[5][0] += 1e-4
    with pytest.raises(InputContractError): verify_twelve(bad)
    with pytest.raises(InputContractError): generate_twelve('E1', 'L1.00', E7_ANCHORS)
    with pytest.raises(InputContractError): generate_twelve('E7', 'L1.00', E7_ANCHORS[:2])

def test_twelve_generator_e8_small_grid_feasible():
    m = generate_twelve('E8', 'L1.00', np.array([[0.21609142351830096, 0.1388778490467109], [0.10991624390681737, 0.06676051199330066], [0.4225612190131215, 0.125548183938205]]))
    assert len(m.points) == 12 and m.min_pairwise >= RULES.min_sep['E8'] and m.generator['distance'] == 'euclid'

def test_transition_and_after_twelve():
    three = dict(family='E7', size_id='L1.00', truths=dict(support=True, strong=False, unsupported=False), decision=dict(technical_status='ok'), precision=dict(state='pass'), evidence=dict(coverage_ok=True)); m = generate_twelve('E7', 'L1.00', E7_ANCHORS)
    t = transition_after_three('E7', 'L1.00', three, dict(state='position-sensitive', expand=True), m); assert t.status.startswith('provisional') and t.twelve_manifest_sha256 == m.sha256 and len(t.three_position_result_sha256) == 64
    with pytest.raises(InputContractError): transition_after_three('E7', 'L1.00', three, dict(state='position-sensitive', expand=True), None)
    assert transition_after_three('E7', 'L1.00', three, dict(state='not-expanded', expand=False), None).status == 'final at 3 positions'
    assert transition_after_three('E7', 'L1.00', three, dict(state='position-unresolved', expand=False), None).status == 'provisional / position-unresolved'
    assert transition_after_three('E7', 'L1.00', three, dict(state='technical_fail', expand=False), None).status == 'technical_fail'
    r12 = dict(family='E7', size_id='L1.00', evidence=dict(stage='12-position', coverage_ok=True, twelve_manifest_sha256=m.sha256), decision=dict(technical_status='ok'), precision=dict(state='pass')); a = after_twelve(t, r12, 'not-expanded'); assert a['final_classification_available'] is True and a['old_position_status'] == 'resolved_by_registered_expansion' and 'NOT verified' in a['scope']
    r12b = copy.deepcopy(r12); r12b['precision']['state'] = 'precision-unresolved'; assert after_twelve(t, r12b, 'not-expanded')['final_classification_available'] is False
    r12c = copy.deepcopy(r12); r12c['evidence']['coverage_ok'] = False; assert after_twelve(t, r12c, 'not-expanded')['final_classification_available'] is False
    assert after_twelve(t, r12, 'technical_fail')['final_classification_available'] is False and after_twelve(t, r12, 'technical_fail')['new_stage_technical'] is True
    with pytest.raises(InputContractError): after_twelve(t, dict(r12, evidence=dict(stage='3', coverage_ok=True, twelve_manifest_sha256=m.sha256)), 'not-expanded')
    with pytest.raises(InputContractError): after_twelve(t, r12, 'typo')
    with pytest.raises(InputContractError): transition_after_three('E8', 'L1.00', dict(three, family='E8'), dict(state='position-sensitive', expand=True), m)   # manifest identity mismatch
    tf = transition_after_three('E7', 'L1.00', three, dict(state='not-expanded', expand=False), None)
    with pytest.raises(InputContractError): after_twelve(tf, r12, 'not-expanded')
    bad = copy.deepcopy(m); bad.added = [[-999.0]] * 9
    with pytest.raises(InputContractError): verify_twelve(bad)
