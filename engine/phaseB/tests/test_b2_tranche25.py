# -*- coding: utf-8 -*-
"""B-2 tranche 25: shared W2 null asset — cold vs cache equivalence (values/blocks/bounds/stop/trigger), case-dependent B_final on the same null, identity mismatch rejection,
manifest binding against the asset (not a live iso bank), corrected lifecycle budget."""
import os, sys, copy, json
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from step1_engine.rules_config import RULES
from step1_engine.positions import PositionBank, w2_trigger
from step1_engine.w2_shared import build_shared_null, w2_trigger_shared, delta_q99_bound_from_prefix, SharedNullAsset
from step1_engine.w2_manifest import build_w2_manifest, verify_w2_manifest, SharedNullAssetRef, verified_w2_for_decision
from step1_engine.w2_stop import w2_stop
from step1_engine.errors import InputContractError
from step1_engine import serialization as ser
from test_b2_tranche3 import cheap_dist, make_positions

def paired(bank, eps=1e-6, seed=0):
    rng = np.random.default_rng(seed); return PositionBank(bank.position_id, bank.Tw + eps * rng.standard_normal(bank.Tw.shape), bank.cid.copy())

def test_shared_null_cold_equals_cache_and_case_dependent_B_final():
    rng = np.random.default_rng(11); pos, iso = make_positions(rng, shifts=(0.0, 0.0, 0.8)); iso32 = paired(iso); pos32 = [paired(p, seed=i + 1) for i, p in enumerate(pos)]
    asset = build_shared_null(iso, 10, 20260914, dist=cheap_dist, iso_f32=iso32, whitening_identity=dict(source='test')); assert asset.validate() and asset.replicate_bounds is not None
    cold = w2_trigger(pos, iso, 10, 20260914, dist=cheap_dist, obs_bounds=None, delta_q99_bound=None, whitening_identity=dict(source='test'))     # legacy path (recomputes the null)
    for n in RULES.n_subs: assert cold['evidence']['null'][n]['values'] == asset.null[n]['values'] and cold['evidence']['null'][n]['blocks'] == asset.null[n]['blocks']   # same asset when recomputed
    shared = w2_trigger_shared(pos, asset, 10, 20260914, dist=cheap_dist, case_id='E7/L1.00', whitening_identity=dict(source='test'), positions_f32=pos32)
    assert shared['stop']['B_final'] == cold['stop']['B_final'] and shared['observed'] == cold['observed'] and shared['validation']['state'] == 'valid' and shared['trigger'] is True
    assert shared['evidence']['bounds']['delta_q99_bound'][2000] == delta_q99_bound_from_prefix(asset, 2000, shared['stop']['B_final'])
    # a different case on the SAME null asset can stop at a different B_final (registered stop rule depends on the observed indicator vector)
    pos2, _ = make_positions(np.random.default_rng(12), shifts=(0.0, 0.0, 0.0)); s2 = w2_trigger_shared(pos2, asset, 10, 20260914, dist=cheap_dist, case_id='E2/L1.00', whitening_identity=dict(source='test'))
    assert s2['validation']['state'] == 'w2-unresolved' and 'not available' in s2['validation']['reason']            # no observed bounds supplied -> unresolved, not 0
    vals = {n: np.asarray(asset.null[n]['values']) for n in RULES.n_subs}; qA = w2_stop(vals, shared['observed'], 'x').B_final; qB = w2_stop(vals, s2['observed'], 'x').B_final
    assert (qA, qB) == (shared['stop']['B_final'], s2['stop']['B_final'])
    # identity mismatches are rejected
    other = build_shared_null(iso, 10, 999, dist=cheap_dist, iso_f32=iso32, whitening_identity=dict(source='test'))
    with pytest.raises(InputContractError): w2_trigger_shared(pos, other, 10, 20260914, dist=cheap_dist, whitening_identity=dict(source='test'))          # other master seed
    with pytest.raises(InputContractError): w2_trigger_shared(pos, asset, 10, 20260914, dist=cheap_dist, whitening_identity=dict(source='OTHER'))         # other whitening
    with pytest.raises(InputContractError): w2_trigger_shared(pos, asset, 100, 20260914, dist=cheap_dist, whitening_identity=dict(source='test'))         # other m
    bad = copy.deepcopy(asset); bad.null[2000]['values'][0] += 1e-6
    with pytest.raises(InputContractError): bad.validate()
    bad2 = copy.deepcopy(asset); bad2.null[2000]['pairwise'][0]['P1P2'] = bad2.null[2000]['values'][0] + 1.0
    with pytest.raises(InputContractError): bad2.validate()
    d = ser.loads(ser.dumps(asset.as_dict())); assert SharedNullAsset(**d).validate()

def test_shared_manifest_binding_against_asset_not_live_iso():
    rng = np.random.default_rng(11); pos, iso = make_positions(rng, shifts=(0.0, 0.0, 0.8)); iso32 = paired(iso); pos32 = [paired(p, seed=i + 1) for i, p in enumerate(pos)]
    asset = build_shared_null(iso, 10, 20260914, dist=cheap_dist, iso_f32=iso32, whitening_identity=dict(source='test'))
    r = w2_trigger_shared(pos, asset, 10, 20260914, dist=cheap_dist, case_id='E7/L1.00', whitening_identity=dict(source='test'), positions_f32=pos32)
    man = build_w2_manifest('E7', 'L1.00', pos, SharedNullAssetRef(asset), r); assert man.shared_null_sha256 == asset.sha256
    v = verify_w2_manifest(man, pos, SharedNullAssetRef(asset), r); assert v['verified'] and v['trigger'] is True
    dec = verified_w2_for_decision(man, pos, SharedNullAssetRef(asset), r); assert dec.trigger is True and dec.check()
    with pytest.raises(InputContractError): build_w2_manifest('E7', 'L1.00', pos, iso, r)                                                                # live iso bank cannot bind a shared-null result
    other = build_shared_null(iso, 10, 999, dist=cheap_dist, whitening_identity=dict(source='test'))
    with pytest.raises(InputContractError): verify_w2_manifest(man, pos, SharedNullAssetRef(other), r)
    r2 = copy.deepcopy(r); r2['evidence']['null'][5000]['values'][3] += 1e-6
    with pytest.raises(InputContractError): verify_w2_manifest(man, pos, SharedNullAssetRef(asset), r2)
