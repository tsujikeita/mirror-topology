# -*- coding: utf-8 -*-
"""B-3-2 builders: resumable shared null == one-shot build_shared_null (bit identity), checkpoint identity refusal, resume equivalence after interruption."""
import os, sys, json
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from step1_engine.w2_shared import build_shared_null
from step1_engine.w2_shared_build import build_shared_null_resumable, null_sequence_resumable
from step1_engine.positions import PositionBank
from step1_engine.errors import InputContractError
from test_b2_tranche3 import cheap_dist, make_positions
from test_b2_tranche25 import paired

def test_resumable_equals_one_shot_and_resumes(tmp_path):
    rng = np.random.default_rng(31); _, iso = make_positions(rng); iso32 = paired(iso)
    one = build_shared_null(iso, 10, 20260918, dist=cheap_dist, iso_f32=iso32, whitening_identity=dict(source='test'))
    res = build_shared_null_resumable(iso, 10, 20260918, str(tmp_path / 'ck'), dist=cheap_dist, iso_f32=iso32, whitening_identity=dict(source='test'), log=lambda *a: None)
    assert res.sha256 == one.sha256 and res.null[2000]['values'] == one.null[2000]['values'] and res.replicate_bounds[5000] == one.replicate_bounds[5000]
    # interrupted run: stop after 30 replicates, then resume -> identical values
    calls = {'n': 0}
    def stopping(a, b):
        calls['n'] += 1
        if calls['n'] > 30 * 3: raise KeyboardInterrupt
        return cheap_dist(a, b)
    stopping.__name__ = cheap_dist.__name__          # same registered distance kind (the interruption is the only difference)
    ck = str(tmp_path / 'ck2' / 'null_nsub2000.json'); os.makedirs(tmp_path / 'ck2')
    with pytest.raises(KeyboardInterrupt): null_sequence_resumable(iso, 2000, 10, 20260918, ck, stopping, iso32, every=10, log=lambda *a: None)
    part = json.load(open(ck)); assert part['done'] == 30 and part['schema'] == 'shared_null_checkpoint_v2' and len(part['payload_digest']) == 64
    e = null_sequence_resumable(iso, 2000, 10, 20260918, ck, cheap_dist, iso32, every=10, log=lambda *a: None); assert e['values'].tolist() == one.null[2000]['values']
    part['identity']['master_seed'] = 1; json.dump(part, open(ck, 'w'))
    with pytest.raises(InputContractError): null_sequence_resumable(iso, 2000, 10, 20260918, ck, cheap_dist, iso32, log=lambda *a: None)

def test_checkpoint_payload_whitening_and_midrun_mutation_are_refused(tmp_path):
    from step1_engine import serialization as ser
    from step1_engine.positions import bank_identity
    rng = np.random.default_rng(32); _, iso = make_positions(rng); iso32 = paired(iso); ck = str(tmp_path / 'c'); os.makedirs(ck)
    first = build_shared_null_resumable(iso, 10, 20260918, ck, dist=cheap_dist, iso_f32=iso32, whitening_identity=dict(source='A'), log=lambda *a: None)
    # (a) zeroed coupling bounds in a completed checkpoint -> refused (digest + recomputation)
    p = os.path.join(ck, 'null_nsub2000.json'); d = ser.loads(open(p).read()); d['bounds'] = [0.0] * d['done']; d['payload_digest'] = __import__('step1_engine.w2_shared_build', fromlist=['_payload_digest'])._payload_digest(d['values'], d['blocks'], d['pairwise'], d['bounds']); open(p, 'w').write(ser.dumps(d))
    with pytest.raises(InputContractError): build_shared_null_resumable(iso, 10, 20260918, ck, dist=cheap_dist, iso_f32=iso32, whitening_identity=dict(source='A'), log=lambda *a: None)
    # (b) scaled values/pairwise (max-consistent) with a stale digest -> refused
    d = ser.loads(open(p).read()); d['bounds'] = first.replicate_bounds[2000]; d['values'] = [2 * v for v in d['values']]; d['pairwise'] = [{k: 2 * v for k, v in q.items()} for q in d['pairwise']]; open(p, 'w').write(ser.dumps(d))
    with pytest.raises(InputContractError): build_shared_null_resumable(iso, 10, 20260918, ck, dist=cheap_dist, iso_f32=iso32, whitening_identity=dict(source='A'), log=lambda *a: None)
    # (c) whitening identity differs -> refused (no re-binding)
    ck2 = str(tmp_path / 'c2'); os.makedirs(ck2); build_shared_null_resumable(iso, 10, 20260918, ck2, dist=cheap_dist, iso_f32=iso32, whitening_identity=dict(source='A'), log=lambda *a: None)
    with pytest.raises(InputContractError): build_shared_null_resumable(iso, 10, 20260918, ck2, dist=cheap_dist, iso_f32=iso32, whitening_identity=dict(source='B'), log=lambda *a: None)
    # (d) bank mutated mid-run -> refused
    ck3 = str(tmp_path / 'c3'); os.makedirs(ck3); calls = []
    def changing(a, b):
        calls.append(1)
        if len(calls) == 1: iso.Tw *= 2
        return cheap_dist(a, b)
    changing.__name__ = cheap_dist.__name__
    with pytest.raises(InputContractError): build_shared_null_resumable(iso, 10, 20260918, ck3, dist=changing, iso_f32=iso32, whitening_identity=dict(source='A'), log=lambda *a: None)
