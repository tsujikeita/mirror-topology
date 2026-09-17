# -*- coding: utf-8 -*-
"""B-2 tranche 16: adopted tranche-15 audit fixes (plan content sharing, no coercion, adapter no-relabel, archive identity), BootstrapPlan/FittingPlan save/restore with regeneration check."""
import os, sys, copy, json
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from step1_engine.rules_config import RULES
from step1_engine.bootstrap_plan import BootstrapPlan, FittingPlan
from step1_engine.plan_io import write_plans, read_plans, plan_to_dict, plan_from_dict
from step1_engine.types import ClusterUID
from step1_engine.errors import InputContractError
from step1_engine import serialization as ser
from step1_engine.twelve_eval import evaluate_twelve_family_mixture, assemble_all_sizes
from test_b2_tranche14 import TwelveFixture

def test_plan_save_restore_and_regeneration_check(tmp_path):
    uids = [ClusterUID(1, 200, 11, 0, i) for i in range(30)] + [ClusterUID(1, 200, 11, 1, i) for i in range(90)]
    bp = BootstrapPlan.build('e-s0', 0, {0: uids[:30], 1: uids[30:]}, 40, 140028); fp = FittingPlan.build('fit-s0', 1, 21, 0, 50, 20, 140029)
    p = str(tmp_path / 'plans.json'); sha = write_plans(dict(eval=bp, fit=fp), p); got = read_plans(p, sha)
    assert np.array_equal(got['eval'].multiplicities[1], bp.multiplicities[1]) and got['eval'].strata == bp.strata and got['fit'].multiplicities_sha256 == fp.multiplicities_sha256 and got['fit'].rng_key == fp.rng_key
    with pytest.raises(InputContractError): read_plans(p, '0' * 64)
    def mutate(fn, f):
        raw = ser.loads(open(p).read()); f(raw); open(str(tmp_path / fn), 'w').write(ser.dumps(raw))
    def m1(raw): raw['plans']['eval']['multiplicities'][0][3][0] += 1; raw['plans']['eval']['multiplicities'][0][3][1] -= 1
    mutate('edit.json', m1)
    with pytest.raises(InputContractError): read_plans(str(tmp_path / 'edit.json'))                                 # row sum preserved but not the deterministic function of the key
    mutate('key.json', lambda raw: raw['plans']['fit']['rng_key'].__setitem__(3, 22))
    with pytest.raises(InputContractError): read_plans(str(tmp_path / 'key.json'))                                  # identity/key mismatch
    mutate('seed.json', lambda raw: raw['plans']['eval'].__setitem__('seed_id', 1))
    with pytest.raises(InputContractError): read_plans(str(tmp_path / 'seed.json'))

def test_family_mixture_has_explicit_release_flag_and_plan_sharing_is_content_based():
    fx = TwelveFixture(); sw = {s: .5 for s in fx.sizes}
    g = evaluate_twelve_family_mixture(fx.inputs, fx.manifests, fx.maps, sw, 100., 550., staged=False, native_position_ids=fx.nmaps); assert g['final_label_released'] is False
    # a restored copy (equal content, different objects) is accepted; a different plan with the same id is rejected
    from dataclasses import replace
    restored = {k: plan_from_dict(plan_to_dict(v)) for k, v in fx.plans.items()}
    fm, fn = fx.inputs['L1.20']; alt = dict(fx.inputs); alt['L1.20'] = (replace(fm, plans=restored), replace(fn, plans=restored))
    assert assemble_all_sizes(alt, fx.manifests, fx.maps, sw, fx.nmaps)[2]['n_configs'] == 24
    other = {k: BootstrapPlan.build(f'fam-s{k}', k, {0: fx.uids}, 60, 999) for k in range(5)}; alt2 = dict(fx.inputs); alt2['L1.20'] = (replace(fm, plans=other), replace(fn, plans=other))
    with pytest.raises(InputContractError): assemble_all_sizes(alt2, fx.manifests, fx.maps, sw, fx.nmaps)
