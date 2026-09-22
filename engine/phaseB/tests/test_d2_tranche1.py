# -*- coding: utf-8 -*-
"""D-2 tranche 1 contracts (design v0.2 §A–C, audit §3–4): CRN table (deterministic, scope-keyed, W2 per position, unique ids, restoration refuses duplicates/renumbering);
latent replay (same key -> same R/z regardless of configuration/root/role/selection/order; different purpose / position -> different latent; continuing a live generator is NOT
the same latent); roots (native reference per configuration from its own c_ct; matched reference shared); batches / UIDs (two logical batches, rotation index within batch,
ConfigBank N0 / N4 views); numerical path (generate_from_latent == legacy generate bit-for-bit on identical latent+roots)."""
import os, sys, json, copy, hashlib
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from step1_engine import d2_rng as d2
from step1_engine.d2_rng import build_crn_table, load_crn_table, group_for, iter_latent, native_reference_root, generate_from_latent, uids_for, BATCHES
from step1_engine.registry import CRNRegistry, PURPOSE
from step1_engine.errors import InputContractError
from step1_engine.grid_registry import load_registry; from step1_engine.grid_manifest import build_configuration_manifest
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); MT = os.environ.get('B3_MT', '/home/claude/mt'); TABLE = os.path.join(P, 'd', 'd2_crn_table.json')
need_mt = pytest.mark.skipif(not os.path.exists(os.path.join(MT, 't1_engine.py')), reason='frozen checkout not present')

def _w2ids():
    reg = load_registry(os.path.join(P, 'tests/assets/a7_circle_geometry.csv'), os.path.join(P, 'tests/assets/a6_observer_design_points.json')); man = build_configuration_manifest(reg); w2 = {}
    for c in man.configurations:
        if c.family != 'E1': w2.setdefault(c.family, {}).setdefault(c.size_id, []).append(c.config_id)
    return reg, man, w2

def test_crn_table_is_deterministic_scope_keyed_and_restorable(tmp_path):
    reg, man, w2 = _w2ids(); t1 = build_crn_table(20260912, w2); t2 = build_crn_table(20260912, {k: {s: list(reversed(v)) for s, v in vv.items()} for k, vv in reversed(list(w2.items()))})
    assert t1['table_sha256'] == t2['table_sha256'] and json.load(open(TABLE))['table_sha256'] == t1['table_sha256']                   # independent of insertion / execution order; committed table matches
    gids = [int(g) for g in t1['groups']]; assert len(gids) == len(set(gids)) == 4 + 4 + 9 + 27
    t, R = load_crn_table(TABLE, t1['table_sha256']); assert R.export_groups()[1003]['purpose'] == 'evaluation'
    assert group_for(t, 'evaluation', 'E7') == 1003 and group_for(t, 'fitting', 'E7') == 2003 and group_for(t, 'evaluation', 'E7') != group_for(t, 'fitting', 'E7')
    ids = w2['E7']['L1.00']; g = [group_for(t, 'w2_independent', 'E7', 'L1.00', c) for c in ids]; assert len(set(g)) == 3                                     # one group per POSITION
    with pytest.raises(InputContractError): group_for(t, 'w2_independent', 'E7', 'L1.00')                                                                  # position required
    with pytest.raises(InputContractError): group_for(t, 'evaluation', 'E9')
    bad = copy.deepcopy(t); bad['groups']['1003']['label'] = bad['groups']['1004']['label']; bad['groups']['1003']['scope'] = bad['groups']['1004']['scope']; p = tmp_path / 'bad.json'; json.dump(bad, open(p, 'w'))
    with pytest.raises(InputContractError): load_crn_table(str(p))                                                                                          # duplicate scope -> refused (SHA also stale)
    bad2 = copy.deepcopy(t); bad2['groups']['1003']['purpose'] = 'fitting'; bad2['table_sha256'] = d2._table_sha(bad2); json.dump(bad2, open(p, 'w'))
    with pytest.raises(InputContractError): load_crn_table(str(p))                                                                                          # re-stamped but duplicate scope
    with pytest.raises(InputContractError): build_crn_table(1, dict(E1={'L1.00': [10101]}))

def test_latent_replay_and_independence():
    t, R = load_crn_table(TABLE); g = group_for(t, 'evaluation', 'E7')
    a = [(k0, k1, Rs.copy(), Z.copy()) for k0, k1, Rs, Z in iter_latent(R, 'evaluation', g, 0, 6, m=4, chunk_clusters=4)]
    b = [(k0, k1, Rs.copy(), Z.copy()) for k0, k1, Rs, Z in iter_latent(R, 'evaluation', g, 0, 6, m=4, chunk_clusters=4)]
    assert all(np.array_equal(x[2], y[2]) and np.array_equal(x[3], y[3]) for x, y in zip(a, b))                                                            # replay from the key
    c = [(k0, k1, Rs.copy(), Z.copy()) for k0, k1, Rs, Z in iter_latent(R, 'fitting', group_for(t, 'fitting', 'E7'), 0, 6, m=4, chunk_clusters=4)]
    assert not np.array_equal(a[0][2], c[0][2]) and not np.array_equal(a[0][3], c[0][3])                                                                   # different purpose -> different latent
    d = [(k0, k1, Rs.copy(), Z.copy()) for k0, k1, Rs, Z in iter_latent(R, 'evaluation', g, 1, 6, m=4, chunk_clusters=4)]
    assert not np.array_equal(a[0][2], d[0][2])                                                                                                            # different batch -> different latent
    ids = [c_.config_id for c_ in build_configuration_manifest(load_registry(os.path.join(P, 'tests/assets/a7_circle_geometry.csv'), os.path.join(P, 'tests/assets/a6_observer_design_points.json'))).configurations if c_.family == 'E7' and c_.size_id == 'L1.00']
    w = [next(iter_latent(R, 'w2_independent', group_for(t, 'w2_independent', 'E7', 'L1.00', cid), 0, 2, m=4, chunk_clusters=2)) for cid in ids]
    assert not np.array_equal(w[0][3], w[1][3]) and not np.array_equal(w[1][3], w[2][3])                                                                    # W2: different positions -> different latent
    # a continued live generator is NOT the same latent (registry.stream reuse semantics): replay must re-create from the key
    s = R.stream('evaluation', 1, g, 0, 'gaussian'); z1 = s.standard_normal(5); z2 = R.stream('evaluation', 1, g, 0, 'gaussian', reuse=True).standard_normal(5); assert not np.array_equal(z1, z2)
    z3 = np.random.default_rng(np.random.SeedSequence(list(R.rng_key('evaluation', 1, g, 0, 'gaussian')))).standard_normal(5); assert np.array_equal(z1, z3)

def test_roots_batches_uids():
    r = native_reference_root(np.array([647.6315815470759, 398.58994290027334, 242.66566022968925])); assert r.shape == (21, 21) and np.allclose(np.diag(r)[:5], np.sqrt(647.6315815470759)) and np.allclose(np.diag(r)[12:], np.sqrt(242.66566022968925)) and np.count_nonzero(r - np.diag(np.diag(r))) == 0
    with pytest.raises(InputContractError): native_reference_root(np.array([1.0, -1.0, 2.0]))
    assert BATCHES == {0: (0, 1_000_000), 1: (1_000_000, 4_000_000)}
    u0 = uids_for('evaluation', 1003, 0)[:3]; u1 = uids_for('evaluation', 1003, 1)[:3]; assert u0[0].as_tuple() == (1, PURPOSE['evaluation'], 1003, 0, 0) and u1[0].as_tuple()[3:] == (1, 0) and len(uids_for('evaluation', 1003, 1)) == 30000
    from step1_engine.orchestrator import ConfigBank
    N0, N4, m = 100, 400, 10; t, R = load_crn_table(TABLE); K = N4 // m; uids = [CRNRegistry.cluster_uid(1, 'evaluation', 1003, 0, i) for i in range(N0 // m)] + [CRNRegistry.cluster_uid(1, 'evaluation', 1003, 1, i) for i in range(K - N0 // m)]
    rng = np.random.default_rng(0); bank = ConfigBank(30101, 'E7', 'matched', 1 / 9, rng.standard_normal(N4), rng.standard_normal(N4), rng.standard_normal(N4), rng.standard_normal(N4), uids, m, {0: (0, N0), 1: (N0, N4)}); assert bank.has_extension and bank.N0 == N0 and bank.at_stage('N0').batches == {0: (0, N0)} and bank.at_stage('N4').batches == {0: (0, N0), 1: (N0, N4)}
    assert len(set(u.as_tuple() for u in uids)) == K
    with pytest.raises(InputContractError): ConfigBank(30101, 'E7', 'matched', 1 / 9, rng.standard_normal(N4), rng.standard_normal(N4), rng.standard_normal(N4), rng.standard_normal(N4), uids, m, {0: (0, N0), 1: (N0, 200), 2: (200, N4)})

@need_mt
def test_new_path_equals_legacy_generate_on_identical_latent(monkeypatch):
    """generate_from_latent must reproduce LegacyKernel.generate bit-for-bit when fed the same R/z blocks and roots (numerical path unchanged)."""
    from step1_engine.legacy_kernel import LegacyKernel, GEN_NS
    k = LegacyKernel(MT); S_I, _ = k.psqrt(k.C_ISO); K, m = 6, 5
    t, R = load_crn_table(TABLE); g = group_for(t, 'evaluation', 'E7')
    # capture the latent blocks of the formal key and feed them to the legacy path through its rng_for hook
    blocks = list(iter_latent(R, 'evaluation', g, 0, K, m=m, chunk_clusters=4)); it = iter(blocks)
    class FakeR:
        def __init__(self, arrs): self.arrs = list(arrs); self.i = 0
    import scipy.spatial.transform as sst
    Rs_all = np.concatenate([b[2] for b in blocks]); Z_all = np.concatenate([b[3] for b in blocks]); state = dict(r=0, z=0)
    orig_random = sst.Rotation.random
    class FakeRot:
        def __init__(self, M): self.M = M
        def as_matrix(self): return self.M
    def fake_random(num, rng=None, **kw):
        out = FakeRot(Rs_all[state['r']:state['r'] + num].copy()); state['r'] += num; return out                                                # exact matrices (no re-orthonormalisation)
    class FakeGauss:
        def standard_normal(self, shape): n = shape[0]; z = Z_all[state['z']:state['z'] + n]; state['z'] += n; return z
    monkeypatch.setattr(sst.Rotation, 'random', staticmethod(fake_random)); monkeypatch.setattr(LegacyKernel, 'rng_for', staticmethod(lambda stream, *ids: FakeGauss()))
    out_old, cid_old, _ = k.generate(K * m, m, (GEN_NS['calibration'], 0), [S_I], ('float64', 'float32'), chunk_clusters=4)
    monkeypatch.undo()
    out_new, cid_new, uids = generate_from_latent(k, dict(ref_matched=S_I), R, 'evaluation', g, 0, K, ('float64', 'float32'), m=m, chunk_clusters=4)
    for sel in ('float64', 'float32'):
        for kk in ('T1', 'T2', 'AX', 'PL'): assert np.array_equal(out_old[(0, sel)][kk], out_new[('ref_matched', sel)][kk]), (sel, kk)
    assert np.array_equal(cid_old, cid_new) and len(uids) == K and out_new[('ref_matched', 'float32')]['T1'].dtype == np.float64
