# -*- coding: utf-8 -*-
"""D4-1 calibration-first driver: sealed calibration without target -> reveal -> target evaluation; commitment / nonce / record / input mismatches refused; calibration copied
verbatim (not recomputed); order record with the sealed parent; numbers identical to the development (target-first) runner on the same inputs."""
import os, sys, json, hashlib
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from step1_engine.calibration_first import commit_target, calibrate_sealed, evaluate_sealed_target, load_sealed_record
from step1_engine import integrated_runner as ir
from step1_engine.archive import Archive, ArchiveRef
from step1_engine.errors import InputContractError
from step1_engine import serialization as ser

def test_sealed_calibration_then_target(tmp_path):
    from fixture32 import base; b = base(); arc = Archive(str(tmp_path / 'a')); T = (80.0, 400.0); nonce = 'author-nonce-0123456789abcdef'; c = commit_target(T, nonce)
    sealed = calibrate_sealed(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, np.array([80., 200.]), np.array([400., 900.]), arc, c)
    assert sealed.thresholds['target'] is None and sealed.thresholds['target_commitment'] == c and 'support' in sealed.calibration and sealed.families == {} and sealed.cases == {}
    ref = sealed.binding['run_manifest_ref']; rec = load_sealed_record(arc, ref); assert rec['_sha256'] == sealed.binding['run_manifest_sha256']
    with pytest.raises(InputContractError): evaluate_sealed_target(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, T, 'wrong-nonce-0123456789abcdef', np.array([80., 200.]), np.array([400., 900.]), arc, ref)
    with pytest.raises(InputContractError): evaluate_sealed_target(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, (81.0, 400.0), nonce, np.array([80., 200.]), np.array([400., 900.]), arc, ref)     # different target than committed
    with pytest.raises(InputContractError): evaluate_sealed_target(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, T, nonce, np.array([80.]), np.array([400.]), arc, ref)               # different pseudo set
    rm = evaluate_sealed_target(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, T, nonce, np.array([80., 200.]), np.array([400., 900.]), arc, ref)
    assert rm.binding['order_record']['sealed_calibration_sha256'] == rec['_sha256'] and rm.binding['sealed_calibration']['copied'].startswith('calibration') and rm.calibration == sealed.calibration and rm.per_pseudo_family_status == sealed.per_pseudo_family_status
    dev = ir.run_first_wave(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, T, np.array([80., 200.]), np.array([400., 900.]), Archive(str(tmp_path / 'dev')), 'smoke')
    for lvl in ('support', 'strong'):                                                                                                                    # numbers identical; only the branch-accounting prose differs (target-side accounting lives in the target run)
        assert dev.calibration[lvl]['truths'] == rm.calibration[lvl]['truths'] and {k: v for k, v in dev.calibration[lvl]['summary'].items() if k not in ('reason',)} == {k: v for k, v in rm.calibration[lvl]['summary'].items() if k not in ('reason',)} and dev.calibration[lvl]['core_only'] == rm.calibration[lvl]['core_only']
    assert {k: v['truths'] for k, v in dev.cases.items()} == {k: v['truths'] for k, v in rm.cases.items()} and dev.families['E7']['eligible_truths'] == rm.families['E7']['eligible_truths'] and 'full_procedure_including_target' in rm.branch_completeness
    # tampered sealed record (edited calibration truths with stale payload SHA) is refused
    d = ser.from_jsonable(arc.get(ArchiveRef(**ref))); d['calibration']['support']['truths'][0] = True; p = tmp_path / 'bad.json'; p.write_text(ser.dumps(d))
    bad_ref = dict(ref); bad_ref['path'] = str(p)
    with pytest.raises(InputContractError): load_sealed_record(arc, bad_ref)
    # a mutated bank after sealing is refused at the target stage (fingerprints)
    b['cases']['E7/L1.00'][0].configs[0].T1_model -= 5.0
    with pytest.raises(InputContractError): evaluate_sealed_target(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, T, nonce, np.array([80., 200.]), np.array([400., 900.]), arc, ref)

def test_private_stage_arguments_are_guarded(tmp_path):
    from fixture32 import base; b = base()
    with pytest.raises(InputContractError): ir.run_first_wave(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, (80., 400.), np.array([80.]), np.array([400.]), Archive(str(tmp_path / 'x')), 'smoke', _stage='calibrate_sealed', _commitment='0' * 64)   # target must not be supplied
    with pytest.raises(InputContractError): ir.run_first_wave(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, (80., 400.), np.array([80.]), np.array([400.]), Archive(str(tmp_path / 'y')), 'smoke', _stage='sealed_target')
    with pytest.raises(InputContractError): commit_target((80., 400.), 'short')
