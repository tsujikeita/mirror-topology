# -*- coding: utf-8 -*-
"""D-2 tranche 3a: fitting-purpose generation (same replay contract; fitting group; batch 0; float64; validated-then-published) and the STRONG bank intake assembling BankSupply
from completed caches (all directories re-verified; roots == caller's; reference on the same latent; fitting paired; formal required) -> build_family_input -> ConfigBank
N0 / N4 views. Refusals: wrong configuration dir, root mismatch, missing batch, non-paired fitting, self-test bank under formal, tampered shard."""
import os, sys, json, copy, hashlib, shutil
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from step1_engine import d2_bank as db
from step1_engine.d2_bank import load_bank_spec, generate_configuration_bank, generate_fitting_bank, intake_registered_bank, CallInventory, verify_bank_dir
from step1_engine.d2_rng import load_crn_table, native_reference_root
from step1_engine.errors import InputContractError
from test_d2_tranche2 import _Kern, _ctx
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); D1 = os.path.join(P, 'registered_assets', 'd1'); TABLE = os.path.join(P, 'd', 'd2_crn_table.json'); SPEC = os.path.join(P, 'd', 'd2_bank_spec.json')
SC = 0.002; SCF = 0.005

def _cov(cid):
    reg = json.load(open(os.path.join(D1, 'd1_cov_registry.json'))); return json.load(open(os.path.join(D1, reg['configurations'][str(cid)]['cov_file'] + '.manifest.json')))

def _build(tmp_path, k, R, t, spec, cid, roots, ref_root, inv):
    dirs = {}
    for b in (0, 1):
        dirs[('eval', b)] = str(tmp_path / f'cfg{cid}_b{b}'); generate_configuration_bank(k, R, t, spec, cid, roots, b, dirs[('eval', b)], inv, ('float64',), scale=SC, chunk_clusters=7)
        dirs[('ref', b)] = str(tmp_path / f'ref_b{b}'); generate_configuration_bank(k, R, t, spec, None, dict(ref_matched=ref_root), b, dirs[('ref', b)], inv, ('float64',), scale=SC, chunk_clusters=7, family='E7')
    dirs['fit'] = str(tmp_path / f'cfg{cid}_fit'); generate_fitting_bank(k, R, t, spec, cid, roots, dirs['fit'], inv, scale=SCF, chunk_clusters=5)
    dirs['ref_fit'] = str(tmp_path / 'ref_fit'); generate_fitting_bank(k, R, t, spec, None, dict(ref_matched=ref_root), dirs['ref_fit'], inv, scale=SCF, chunk_clusters=5, family='E7')
    return dirs

def test_fitting_generation_and_strong_intake_to_family_input(tmp_path):
    reg, man, t, R, d1 = _ctx(); spec = load_bank_spec(SPEC, table=t); k = _Kern(); inv = CallInventory()
    roots = dict(model_matched=np.eye(21) * 1.1, model_native=np.eye(21) * 0.9, ref_native=native_reference_root(np.array([3.0, 2.0, 1.0]))); ref_root = np.eye(21)
    dirs = _build(tmp_path, k, R, t, spec, 30101, roots, ref_root, inv)
    fm = verify_bank_dir(dirs['fit']); assert fm['purpose'] == 'fitting' and fm['crn_group'] == 2003 and fm['n_clusters'] == 10 and fm['calls'][0]['key_gaussian'][2] == 300 and fm['selections'] == ['float64']
    with pytest.raises(InputContractError): generate_fitting_bank(k, R, t, spec, 30101, roots, dirs['fit'], inv, scale=SCF)                                     # fresh attempt
    # fitting latent differs from the evaluation latent of the same family (different purpose)
    zf = np.load(os.path.join(dirs['fit'], 'cfg30101_fit_s0.npz')); ze = np.load(os.path.join(dirs[('eval', 0)], 'cfg30101_b0_s0.npz'))
    assert not np.array_equal(zf['model_matched__float64__T1'][:1000], ze['model_matched__float64__T1'][:1000])
    all_roots = dict(roots, ref_matched=ref_root)
    for system in ('matched', 'native'):
        supply, info = intake_registered_bank(30101, system, {0: dirs[('eval', 0)], 1: dirs[('eval', 1)]}, {0: dirs[('ref', 0)], 1: dirs[('ref', 1)]}, dirs['fit'], dirs['ref_fit'], all_roots, _cov(30101), formal=False)
        assert supply.config_id == 30101 and supply.system == system and supply.batches == {0: (0, 2000), 1: (2000, 8000)} and len(supply.cluster_uids) == 80 and supply.fitting.K == 10 and supply.m == 100
        assert supply.cluster_uids[0].as_tuple() == (1, 200, 1003, 0, 0) and supply.cluster_uids[20].as_tuple() == (1, 200, 1003, 1, 0) and info['n_clusters'] == {0: 20, 1: 60}
        if system == 'matched': assert np.array_equal(supply.T1_ref[:2000], np.load(os.path.join(dirs[('ref', 0)], 'ref_b0_s0.npz'))['ref_matched__float64__T1'])
        else: assert np.array_equal(supply.T1_ref[:2000], ze['ref_native__float64__T1'])
    # consumer assembly: build all three positions of E7/L1.00 (positions share the family latent and the reference), formal plans from the bank UIDs -> FamilyInput -> N0/N4 views
    from step1_engine.production import build_family_input; from step1_engine.bootstrap_plan import BootstrapPlan, FittingPlan
    sup = []; more = {}
    for cid in (30102, 30103):
        rr = dict(model_matched=np.eye(21) * (1.1 + 0.01 * (cid - 30101)), model_native=np.eye(21) * 0.9, ref_native=native_reference_root(np.array([3.0, 2.0, 1.0])))
        for b in (0, 1): generate_configuration_bank(k, R, t, spec, cid, rr, b, str(tmp_path / f'cfg{cid}_b{b}'), inv, ('float64',), scale=SC, chunk_clusters=7)
        generate_fitting_bank(k, R, t, spec, cid, rr, str(tmp_path / f'cfg{cid}_fit'), inv, scale=SCF, chunk_clusters=5); more[cid] = rr
    for cid in (30101, 30102, 30103):
        rr = dict(more.get(cid, roots), ref_matched=ref_root); s_, _ = intake_registered_bank(cid, 'matched', {0: str(tmp_path / f'cfg{cid}_b0'), 1: str(tmp_path / f'cfg{cid}_b1')}, {0: dirs[('ref', 0)], 1: dirs[('ref', 1)]}, str(tmp_path / f'cfg{cid}_fit'), dirs['ref_fit'], rr, _cov(cid), formal=False); sup.append(s_)
    uids = sup[0].cluster_uids; ep = {s: BootstrapPlan.build(f'd2-E7-{s}', s, {0: uids[:20], 1: uids[20:]}, 40, 882211) for s in range(5)}
    fp = {s: FittingPlan.build(f'd2-fit-{s}', 1, 41, s, 10, 40, 882212) for s in range(5)}
    fi = build_family_input(reg, man, 'E7', 'matched', sup, ep, fp, size_ids=['L1.00'])
    cb = fi.configs[0]; assert cb.batches == {0: (0, 2000), 1: (2000, 8000)} and cb.at_stage('N0').batches == {0: (0, 2000)} and cb.at_stage('N4').N0 == 2000 and len(fi.configs) == 3
    with pytest.raises(InputContractError): intake_registered_bank(30101, 'matched', {0: dirs[('eval', 0)], 1: dirs[('eval', 1)]}, {0: dirs[('ref', 0)], 1: dirs[('ref', 1)]}, dirs['fit'], dirs['ref_fit'], all_roots, _cov(30102), formal=False)   # another configuration's covariance sidecar
    # refusals
    with pytest.raises(InputContractError): intake_registered_bank(30101, 'matched', {0: dirs[('eval', 0)], 1: dirs[('eval', 1)]}, {0: dirs[('ref', 0)], 1: dirs[('ref', 1)]}, dirs['fit'], dirs['ref_fit'], all_roots, _cov(30101), formal=True)      # self-test banks are not formal
    with pytest.raises(InputContractError): intake_registered_bank(30101, 'matched', {0: dirs[('eval', 0)]}, {0: dirs[('ref', 0)], 1: dirs[('ref', 1)]}, dirs['fit'], dirs['ref_fit'], all_roots, _cov(30101), formal=False)                          # missing batch
    bad = dict(all_roots, model_matched=np.eye(21) * 1.2)
    with pytest.raises(InputContractError): intake_registered_bank(30101, 'matched', {0: dirs[('eval', 0)], 1: dirs[('eval', 1)]}, {0: dirs[('ref', 0)], 1: dirs[('ref', 1)]}, dirs['fit'], dirs['ref_fit'], bad, _cov(30101), formal=False)              # root mismatch
    with pytest.raises(InputContractError): intake_registered_bank(30102, 'matched', {0: dirs[('eval', 0)], 1: dirs[('eval', 1)]}, {0: dirs[('ref', 0)], 1: dirs[('ref', 1)]}, dirs['fit'], dirs['ref_fit'], all_roots, _cov(30102), formal=False)        # dirs belong to 30101
    d_fit2 = str(tmp_path / 'fit_other'); generate_fitting_bank(k, R, t, spec, 30101, roots, d_fit2, inv, scale=0.01, chunk_clusters=5)
    with pytest.raises(InputContractError): intake_registered_bank(30101, 'matched', {0: dirs[('eval', 0)], 1: dirs[('eval', 1)]}, {0: dirs[('ref', 0)], 1: dirs[('ref', 1)]}, d_fit2, dirs['ref_fit'], all_roots, _cov(30101), formal=False)              # fitting not paired (different K)
    dt = str(tmp_path / 'tam'); shutil.copytree(dirs[('eval', 1)], dt); f = os.path.join(dt, 'cfg30101_b1_s2.npz'); z = dict(np.load(f)); z['model_matched__float64__T2'][3] += 1e-9; np.savez(f, **z)
    with pytest.raises(InputContractError): intake_registered_bank(30101, 'matched', {0: dirs[('eval', 0)], 1: dt}, {0: dirs[('ref', 0)], 1: dirs[('ref', 1)]}, dirs['fit'], dirs['ref_fit'], all_roots, _cov(30101), formal=False)
