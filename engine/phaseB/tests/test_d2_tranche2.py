# -*- coding: utf-8 -*-
"""D-2 tranche 2 contracts: bank spec (deterministic, bound to registry / CRN table / D-1 registry; required f32 subset; plan schema; pseudo owner; W2 identity), generator
(fresh attempt only; shards + sidecars + completion manifest; call inventory carries formal keys; rotation index within batch; N0 prefix bit-identical to a batch-0 generation;
roles restricted; scale<1 marked non-formal), cache verification (bytes / arrays / ranges / dtypes; partial directory refused; tampered array or sidecar refused)."""
import os, sys, json, copy, hashlib, shutil
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from step1_engine import d2_bank as db
from step1_engine.d2_bank import build_bank_spec, load_bank_spec, generate_configuration_bank, verify_bank_dir, CallInventory, shard_plan
from step1_engine.d2_rng import load_crn_table, native_reference_root
from step1_engine.errors import InputContractError
from step1_engine.grid_registry import load_registry; from step1_engine.grid_manifest import build_configuration_manifest
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); MT = os.environ.get('B3_MT', '/home/claude/mt'); TABLE = os.path.join(P, 'd', 'd2_crn_table.json'); SPEC = os.path.join(P, 'd', 'd2_bank_spec.json')
need_mt = pytest.mark.skipif(not os.path.exists(os.path.join(MT, 't1_engine.py')), reason='frozen checkout not present')

def _ctx():
    reg = load_registry(os.path.join(P, 'tests/assets/a7_circle_geometry.csv'), os.path.join(P, 'tests/assets/a6_observer_design_points.json')); man = build_configuration_manifest(reg)
    t, R = load_crn_table(TABLE); d1 = json.load(open(os.path.join(P, 'registered_assets/d1/d1_cov_registry.json'))); d1['_sha256'] = hashlib.sha256(open(os.path.join(P, 'registered_assets/d1/d1_cov_registry.json'), 'rb').read()).hexdigest()
    return reg, man, t, R, d1

def test_spec_is_deterministic_and_bound():
    reg, man, t, R, d1 = _ctx(); s1 = build_bank_spec(man, t, d1, 20260912); s2 = load_bank_spec(SPEC); assert s1['spec_sha256'] == s2['spec_sha256']
    assert s1['crn_table_sha256'] == t['table_sha256'] and s1['registry_sha256'] == reg.registry_sha256 and s1['d1_registry_sha256'] == d1['_sha256'] and s1['N0'] == 1_000_000 and s1['N_max'] == 4_000_000
    c = s1['configurations']['30101']; assert c['evaluation_ids'] == dict(matched=30101, native=80101) and c['crn'] == dict(evaluation_group=1003, fitting_group=2003, wave_id=1) and c['selections']['required_f32_subset'] is True and c['selections']['evaluation'] == {'0': ['float64', 'float32'], '1': ['float64']}
    assert s1['configurations']['30102']['selections']['evaluation'] == {'0': ['float64'], '1': ['float64']} and s1['family_reference']['E7']['selections'] == {'0': ['float64', 'float32'], '1': ['float64']} and s1['required_f32_subset'] == {'E1': dict(matched=10101, native=60101, config_id=10101, N='N0 (batch 0 only)'), 'E2': dict(matched=20101, native=70101, config_id=20101, N='N0 (batch 0 only)'), 'E7': dict(matched=30101, native=80101, config_id=30101, N='N0 (batch 0 only)'), 'E8': dict(matched=40101, native=90101, config_id=40101, N='N0 (batch 0 only)')}
    assert c['w2_primary']['group'] == 60101 and s1['configurations']['10101']['w2_primary'] is None and c['w2_primary']['whitening']['asset_sha256'].startswith('8348d5f4') and c['covariance']['cov_array_sha256'] == d1['configurations']['30101']['cov_array_sha256']
    assert s1['plan_schema']['bootstrap'] == dict(seeds=5, B=2000, B_KDE=2000, key=s1['plan_schema']['bootstrap']['key'], fixed=s1['plan_schema']['bootstrap']['fixed']) and s1['pseudo_column']['n'] == 2000 and s1['pseudo_column']['m'] == 1
    assert [sh['batch_id'] for sh in shard_plan()] == [0, 1, 1, 1] and shard_plan()[2]['rotation_index'] == [10000, 20000] and shard_plan()[3]['clusters'] == [30000, 40000]
    with pytest.raises(InputContractError): build_bank_spec(man, t, d1, 1)
    bad = copy.deepcopy(d1); bad['configurations']['30101']['x0_CT'][0] += 1e-6
    with pytest.raises(InputContractError): build_bank_spec(man, t, bad, 20260912)
    with pytest.raises(InputContractError): load_bank_spec(SPEC, '0' * 64)
    # generation-entry binding: a live registry with a different master seed under the unchanged table/spec is refused before any numerics
    from step1_engine.registry import CRNRegistry; from step1_engine.d2_bank import bind_generation_inputs
    with pytest.raises(InputContractError): bind_generation_inputs(CRNRegistry(20260913, R.export_groups()), t, s2)
    bind_generation_inputs(R, t, s2)

class _Kern:
    """TEST-ONLY kernel: linear scan with a fixed axis set (deterministic, cheap); same signature as LegacyKernel.D_batch / scan."""
    def __init__(self):
        rng = np.random.default_rng(7); self.F = rng.standard_normal((12, 21))
    def D_batch(self, Rs): return np.tile(np.eye(21), (len(Rs), 1, 1))
    def scan(self, X, selection):
        Xs = X if selection == 'float64' else X.astype(np.float32).astype(np.float64); S = Xs @ self.F.T; ax = S.argmin(1).astype(np.int32)
        return dict(T1=S[np.arange(len(X)), ax], T2=S.max(1), AX=ax, PL=(ax % 3).astype(np.int32))

def test_generator_shards_inventory_prefix_and_cache_verification(tmp_path):
    reg, man, t, R, d1 = _ctx(); spec = load_bank_spec(SPEC); k = _Kern(); inv = CallInventory()
    roots = dict(model_matched=np.eye(21) * 1.1, model_native=np.eye(21) * 0.9, ref_native=native_reference_root(np.array([3.0, 2.0, 1.0])))
    d0 = str(tmp_path / 'cfg30101_b0'); m0 = generate_configuration_bank(k, R, t, spec, 30101, roots, 0, d0, inv, ('float64', 'float32'), scale=0.002, chunk_clusters=7)
    assert m0['n_clusters'] == 20 and len(m0['shards']) == 1 and m0['formal'] is False and inv.calls[-1]['key_rotation'] == [20260912, 1, 200, 1003, 0, 1] and inv.calls[-1]['clusters'] == [0, 20]
    v = verify_bank_dir(d0, ('model_matched', 'model_native', 'ref_native')); assert v['manifest_sha256'] == m0['manifest_sha256']
    side = json.load(open(os.path.join(d0, m0['shards'][0]['sidecar']))); assert side['uids'][0] == [1, 200, 1003, 0, 0] and side['uids'][1] == [1, 200, 1003, 0, 19] and side['evaluation_ids'] == dict(matched=30101, native=80101) and side['dtype']['T1'] == 'float64'
    with pytest.raises(InputContractError): generate_configuration_bank(k, R, t, spec, 30101, roots, 0, d0, inv, ('float64', 'float32'), scale=0.002)              # fresh attempt: existing dir refused
    with pytest.raises(InputContractError): generate_configuration_bank(k, R, t, spec, 30101, dict(roots, ref_matched=np.eye(21)), 0, str(tmp_path / 'x'), inv, ('float64',), scale=0.002)   # roles restricted
    # formal scope boundary (sentinel; no large generation): batch1 float64-only reaches the adapter, batch1 float32 is refused, batch0 both paths reaches for the required subset
    import step1_engine.d2_bank as _db; calls = []
    class Reached(Exception): pass
    orig = _db.generate_from_latent; _db.generate_from_latent = lambda *a, **kw: (calls.append(1), (_ for _ in ()).throw(Reached()))
    try:
        with pytest.raises(Reached): generate_configuration_bank(k, R, t, spec, 30101, roots, 1, str(tmp_path / 'f1'), inv, ('float64',), scale=1.0)
        with pytest.raises(InputContractError): generate_configuration_bank(k, R, t, spec, 30101, roots, 1, str(tmp_path / 'f2'), inv, ('float64', 'float32'), scale=1.0)
        with pytest.raises(Reached): generate_configuration_bank(k, R, t, spec, 30101, roots, 0, str(tmp_path / 'f3'), inv, ('float64', 'float32'), scale=1.0)
        with pytest.raises(InputContractError): generate_configuration_bank(k, R, t, spec, 30102, roots, 0, str(tmp_path / 'f4'), inv, ('float64', 'float32'), scale=1.0)
    finally: _db.generate_from_latent = orig
    assert len(calls) == 2
    with pytest.raises(InputContractError): generate_configuration_bank(k, R, t, spec, 30101, roots, 1, str(tmp_path / 'u'), inv, ('float64',), scale=0.00014)   # unsupported cluster count (not an exact shard split)
    with pytest.raises(InputContractError): generate_configuration_bank(k, R, t, spec, None, dict(ref_matched=np.eye(21)), 0, str(tmp_path / 'y'), inv, ('float64',), scale=0.002)         # reference needs family
    # batch 1 generation (3 shards at scale) with rotation index within batch; the family reference on the same latent
    d1b = str(tmp_path / 'cfg30101_b1'); m1 = generate_configuration_bank(k, R, t, spec, 30101, roots, 1, d1b, inv, ('float64',), scale=0.002, chunk_clusters=7)
    assert m1['n_clusters'] == 60 and len(m1['shards']) == 3 and json.load(open(os.path.join(d1b, m1['shards'][2]['sidecar'])))['rotation_index'] == [40, 60] and verify_bank_dir(d1b)['n_rows'] == 6000
    dr = str(tmp_path / 'ref_E7_b0'); mr = generate_configuration_bank(k, R, t, spec, None, dict(ref_matched=np.eye(21)), 0, dr, inv, ('float64',), scale=0.002, chunk_clusters=7, family='E7'); assert mr['roles'] == ['ref_matched']
    # same latent for configuration and reference: with identical roots the outputs coincide (model_matched root == ref root here) -> T arrays equal
    zc = np.load(os.path.join(d0, m0['shards'][0]['file'])); dr2 = str(tmp_path / 'ref_same'); generate_configuration_bank(k, R, t, spec, None, dict(ref_matched=np.eye(21) * 1.1), 0, dr2, inv, ('float64',), scale=0.002, chunk_clusters=7, family='E7'); zr = np.load(os.path.join(dr2, 'ref_b0_s0.npz'))
    assert np.array_equal(zc['model_matched__float64__T1'], zr['ref_matched__float64__T1']) and np.array_equal(zc['cid'], zr['cid'])
    # N0 prefix invariance: a shorter batch-0 generation is a prefix of a longer one (replay from the key, chunk-independent)
    d_short = str(tmp_path / 'short'); generate_configuration_bank(k, R, t, spec, 30101, roots, 0, d_short, inv, ('float64',), scale=0.001, chunk_clusters=3); zs = np.load(os.path.join(d_short, 'cfg30101_b0_s0.npz'))
    assert np.array_equal(zs['model_native__float64__T1'], zc['model_native__float64__T1'][:len(zs['cid'])])
    # cache verification refusals: tampered array, tampered sidecar, missing completion manifest
    dt = str(tmp_path / 'tampered'); shutil.copytree(d0, dt); f = os.path.join(dt, m0['shards'][0]['file']); z = dict(np.load(f)); z['model_matched__float64__T1'][0] += 1e-9; np.savez(f, **z)
    with pytest.raises(InputContractError): verify_bank_dir(dt)
    ds = str(tmp_path / 'sidecar'); shutil.copytree(d0, ds); sp = os.path.join(ds, m0['shards'][0]['sidecar']); s = json.load(open(sp)); s['rows'] = [0, 1999]; json.dump(s, open(sp, 'w'))
    with pytest.raises(InputContractError): verify_bank_dir(ds)
    dp = str(tmp_path / 'partial'); shutil.copytree(d0, dp); os.remove(os.path.join(dp, 'COMPLETE.json'))
    with pytest.raises(InputContractError): verify_bank_dir(dp)
