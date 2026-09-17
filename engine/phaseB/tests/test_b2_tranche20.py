# -*- coding: utf-8 -*-
"""B-2 tranche 20: adopted tranche-19 audit fixes (manifest/spec validation, NaN-safe cov metadata); production wrapper carrying registry/manifest identity into evaluation evidence."""
import os, sys, copy, json
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine.rules_config import RULES
from step1_engine.grid_registry import load_registry, registry_from_dict
from step1_engine.grid_manifest import build_configuration_manifest
from step1_engine.production import production_manifest, registered_id_map, build_family_input, BankSupply, NATIVE_OFFSET
from step1_engine.orchestrator import FittingBank, evaluate_family
from step1_engine.bootstrap_plan import BootstrapPlan, FittingPlan
from step1_engine.types import ClusterUID
from step1_engine.checkpoint import write_family_result, read_family_result
from step1_engine.errors import InputContractError
from step1_engine import serialization as ser
ASSETS = os.path.join(os.path.dirname(__file__), 'assets'); A7 = os.path.join(ASSETS, 'a7_circle_geometry.csv'); A6 = os.path.join(ASSETS, 'a6_observer_design_points.json')

def synthetic_supplies(man, family, system, K=150, m=10, Kf=300, mf=10, seed=140030):
    """One family latent for every configuration/system (CRN), transformed per configuration; native reference scaled."""
    specs = [c for c in man.configurations if c.family == family]; z = np.random.default_rng(seed).standard_normal((K * m, 2)); zf = np.random.default_rng(seed + 1).standard_normal((Kf * mf, 2))
    uids = [ClusterUID(1, 200, 31, 0, i) for i in range(K)]; cidf = np.repeat(np.arange(Kf), mf); out = []
    for j, c in enumerate(specs):
        scale = 1.0 if system == 'matched' else 0.9; unit = np.array([40, 200]) * scale; loc = np.array([120, 600]); sh = np.array([0.7, 0.6]) * (1 + 0.02 * j)
        out.append(BankSupply(c.config_id, system, ((z - sh) * unit + loc)[:, 0], ((z - sh) * unit + loc)[:, 1], (z * unit + loc)[:, 0], (z * unit + loc)[:, 1], uids, m, {0: (0, K * m)}, FittingBank((zf - sh) * unit + loc, zf * unit + loc, cidf),
                              cov_manifest=dict(manifest=dict(topology=c.family, params=c.shape_params, x0=c.x0_CT), cov_array_sha256='a' * 64, cov_file_sha256='b' * 64)))
    plans = {s: BootstrapPlan.build(f'{family}-s{s}', s, {0: uids}, 40, seed + 2) for s in range(RULES.seeds)}; fplans = {s: FittingPlan.build(f'{family}-fit{s}', 1, 41, s, Kf, 15, seed + 3) for s in range(RULES.seeds)}
    return out, plans, fplans

def test_production_wrapper_carries_identity_into_evidence(tmp_path):
    reg = load_registry(A7, A6); man = production_manifest(reg); idm = registered_id_map(man); assert idm.validate(man)
    sm, plans, fplans = synthetic_supplies(man, 'E7', 'matched'); sn, _, _ = synthetic_supplies(man, 'E7', 'native')
    fm = build_family_input(reg, man, 'E7', 'matched', sm, plans, fplans); fn = build_family_input(reg, man, 'E7', 'native', sn, plans, fplans)
    assert len(fm.configs) == 9 and abs(sum(c.weight for c in fm.configs) - 1) < 1e-12 and fm.fitting_plan_binding == 'bound' and fm.grid_identity['manifest_sha256'] == man.manifest_sha256
    assert {c.evaluation_id for c in fn.configs} == {c.evaluation_id + NATIVE_OFFSET for c in fm.configs} and set(fm.grid_identity['cov_bound']) == {c.evaluation_id for c in fm.configs}
    r = evaluate_family(fm, fn, 80.0, 400.0); gi = r.evidence['grid_identity']; assert gi['registry_sha256'] == reg.registry_sha256 and gi['evaluation_to_config'][30101] == 30101 and gi['cache_keys'][30101] == next(c.cache_key for c in man.configurations if c.config_id == 30101)
    p = str(tmp_path / 'r.json'); sha = write_family_result(r, p); got = read_family_result(p, sha); assert got['result']['evidence']['grid_identity']['manifest_sha256'] == man.manifest_sha256 and got['verified'].startswith('verified')
    # size subset: registered size prior conditioned on the selected sizes (recorded), not ad hoc
    f2 = build_family_input(reg, man, 'E7', 'matched', [s for s in sm if s.config_id // 100 % 100 in (1, 2)], plans, fplans, size_ids=['L1.00', 'L1.20']); assert set(f2.grid_identity['sizes']) == {'L1.00', 'L1.20'} and abs(sum(c.weight for c in f2.configs) - 1) < 1e-12
    with pytest.raises(InputContractError): build_family_input(reg, man, 'E7', 'matched', sm[:-1], plans, fplans)                     # inventory
    with pytest.raises(InputContractError): build_family_input(reg, man, 'E7', 'native', sm, plans, fplans)                          # system mismatch
    bad = copy.deepcopy(sm); bad[0].cov_manifest['manifest']['x0'] = [0.0, 0.0, 0.0]
    with pytest.raises(InputContractError): build_family_input(reg, man, 'E7', 'matched', bad, plans, fplans)                        # covariance metadata not of this configuration
    d = ser.loads(ser.dumps(reg.as_dict())); internal = registry_from_dict(d)
    with pytest.raises(InputContractError): production_manifest(internal)                                                             # production requires a source-bound registry
    with pytest.raises(InputContractError): build_family_input(reg, man, 'E7', 'matched', sm, plans, fplans, size_ids=['L0.85'])
