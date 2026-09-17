# -*- coding: utf-8 -*-
"""B-2 tranche 27: W2Context contracts (R26-A/B/C) and formal intake: context snapshot + expected SHA bound at the start of calibration, recorded in every result and in the
summary; missing case / substituted context / raw dict rejected; 2 sizes of one family as separate case keys."""
import os, sys, copy
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from step1_engine.orchestrator import evaluate_threshold, calibrate_pseudo
from step1_engine.w2_context import build_w2_context, decisions_by_family
from step1_engine.errors import InputContractError
from context_fixture import make_context_fixture, KEY_A, KEY_B
from test_b2_tranche4 import make_staged_family

def test_formal_calibration_binds_context_snapshot_and_rejects_substitution():
    asset, cases, ctx = make_context_fixture(); snap = ctx.snapshot(); sha = snap.context_sha256
    famA = make_staged_family(np.random.default_rng(5), group=7); famB = make_staged_family(np.random.default_rng(6), group=8)
    fams = {KEY_A: (famA, None), KEY_B: (famB, None)}; pm = {KEY_A: {100: 1, 101: 2, 102: 3}, KEY_B: {100: 1, 101: 2, 102: 3}}
    res = evaluate_threshold(fams, 80.0, 400.0, staged=True, position_maps=pm, w2_context=snap, expected_context_sha256=sha)
    assert res[KEY_A].evidence['w2_context']['context_sha256'] == sha and res[KEY_A].evidence['position']['w2']['trigger'] is True and res[KEY_B].evidence['position']['w2']['trigger'] is False
    summ, truths = calibrate_pseudo(fams, np.array([80.0, 200.0]), np.array([400.0, 900.0]), 'support', staged=True, position_maps=pm, w2_context=snap, expected_context_sha256=sha)
    assert summ.n == 2 and 'w2_context asset=' in summ.reason and sha[:16] in summ.reason
    with pytest.raises(InputContractError): evaluate_threshold(fams, 80.0, 400.0, staged=True, position_maps=pm, w2_context=snap)                                     # expected SHA required
    with pytest.raises(InputContractError): evaluate_threshold(fams, 80.0, 400.0, staged=True, position_maps=pm, w2_context=snap, expected_context_sha256='0' * 64)
    bad = copy.deepcopy(snap); bad.decisions[KEY_A] = bad.decisions[KEY_B]
    with pytest.raises(InputContractError): evaluate_threshold(fams, 80.0, 400.0, staged=True, position_maps=pm, w2_context=bad, expected_context_sha256=sha)      # substituted decision (valid checksum) rejected
    with pytest.raises(InputContractError): evaluate_threshold({'E2/L1.00': (famA, None)}, 80.0, 400.0, staged=True, position_maps={'E2/L1.00': pm[KEY_A]}, w2_context=snap, expected_context_sha256=sha)   # missing case is an error, not W2NotEvaluated
    with pytest.raises(InputContractError): evaluate_threshold(fams, 80.0, 400.0, staged=True, position_maps=pm, w2_context=snap, expected_context_sha256=sha, w2_results={KEY_A: snap.decisions[KEY_A]})
    byfam = decisions_by_family(snap); assert set(byfam) == {'E7'} and set(byfam['E7']) == {'L1.00', 'L1.50'}
    d = snap.as_dict(); assert set(d['manifests']) == {KEY_A, KEY_B} and all(len(v) == 64 for v in d['manifests'].values()) and d['cases'][KEY_A]['has_result'] is True
