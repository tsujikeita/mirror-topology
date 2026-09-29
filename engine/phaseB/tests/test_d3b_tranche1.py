# -*- coding: utf-8 -*-
"""D-3b tranche 1 contracts (step1_engine.d3_bank): the ADDED-configuration bank generator / verifier / intake bound to the accepted tranche 2b dependency.
(1) generation is refused for first-wave ids (FIXED D-2 inputs), for role sets other than the configuration roles, for an existing output directory (fresh attempt), for
selections that differ from bank spec v2 at scale 1 (sentinel, no large generation), and without a verified TwelveContext; (2) small-scale banks (TEST-ONLY kernel) carry the
v2 identities (table / D-2 spec v1 / spec v2 / receipt / map / seed / wave, position index, origin, covariance identity) and are re-verified by verify_twelve_bank_dir; any
edit of an array, a sidecar or the manifest — and a partial directory — is refused; (3) the numerical path is the D-2 one: on the same latent, the added configuration's arrays
equal a d2_bank generation of the same roots (bit-identical T1/T2/AX/PL/cid) and its cid equals the family reference's; (4) the reference re-use binding refuses a directory
whose manifest is not the D-2 ledger unit recorded in spec v2; (5) intake_twelve_bank (formal=False with test references) assembles a BankSupply whose covariance identity is
the receipt's, which build_twelve_size_input accepts (12 positions) and which refuses wrong roots / wrong configuration / partial batches."""
import os, sys, json, copy, shutil
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine import d3_bank as d3b
from step1_engine import d2_bank as d2b
from step1_engine.d3_bank import generate_twelve_configuration_bank, generate_twelve_fitting_bank, verify_twelve_bank_dir, verify_reused_reference_dir, intake_twelve_bank, CONFIG_ROLES, MANIFEST_SCHEMA, SHARD_SCHEMA
from step1_engine.d2_bank import generate_configuration_bank, generate_fitting_bank, CallInventory, load_bank_spec, _asha
from step1_engine.d2_rng import load_crn_table, native_reference_root, group_for
from step1_engine.d3_profile import twelve_context, load_registered_bank_spec_v2, build_twelve_size_input, fix_family_plans
from step1_engine.production import BankSupply
from step1_engine.errors import InputContractError
from step1_engine.types import ClusterUID
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); TABLE = os.path.join(P, 'd', 'd2_crn_table.json'); SPEC1 = os.path.join(P, 'd', 'd2_bank_spec.json')
CTX = twelve_context(P); T, R = load_crn_table(TABLE); SPEC2 = load_registered_bank_spec_v2(CTX); D2SPEC = load_bank_spec(SPEC1)
SCALE = 0.002                                                                                                            # 20 clusters (batch 0) / 60 (batch 1) / 4 (fitting)


class _Kern:
    """TEST-ONLY kernel (as tests/test_d2_tranche2.py): identity D_batch, linear scan with a fixed axis set."""
    def __init__(self):
        rng = np.random.default_rng(7); self.F = rng.standard_normal((12, 21))
    def D_batch(self, Rs): return np.tile(np.eye(21), (len(Rs), 1, 1))
    def scan(self, X, selection):
        Xs = X if selection == 'float64' else X.astype(np.float32).astype(np.float64); S = Xs @ self.F.T; ax = S.argmin(1).astype(np.int32)
        return dict(T1=S[np.arange(len(X)), ax], T2=S.max(1), AX=ax, PL=(ax % 3).astype(np.int32))


def _roots(cid):
    rng = np.random.default_rng(cid); A = rng.standard_normal((21, 21)); Sm = np.eye(21) + 0.05 * (A + A.T); B = rng.standard_normal((21, 21)); Sn = np.eye(21) * 0.9 + 0.05 * (B + B.T)
    return dict(model_matched=Sm, model_native=Sn, ref_native=native_reference_root(np.array([3.0, 2.0, 1.0]) * (1 + 0.01 * (cid % 12))))


S_ISO = np.eye(21) * 1.3                                                                                                  # test isotropic (ref_matched) root
ADDED = [c for c in sorted(SPEC2['configurations'], key=int) if SPEC2['configurations'][c]['mode'] == 'generate_D3b']; FIRST = [c for c in sorted(SPEC2['configurations'], key=int) if SPEC2['configurations'][c]['mode'] != 'generate_D3b']


def _gen_cfg(tmp, cid, k, inv, tag=''):
    roots = _roots(cid); d = {}
    for b in (0, 1): d[b] = str(tmp / f'cfg{cid}{tag}_b{b}'); generate_twelve_configuration_bank(k, R, CTX, cid, roots, b, d[b], inv, ('float64',), scale=SCALE, chunk_clusters=7)
    df = str(tmp / f'cfg{cid}{tag}_fit'); generate_twelve_fitting_bank(k, R, CTX, cid, roots, df, inv, scale=SCALE, chunk_clusters=7); return roots, d, df


def _gen_ref(tmp, fam, k, inv):
    d = {}
    for b in (0, 1): d[b] = str(tmp / f'ref_{fam}_b{b}'); generate_configuration_bank(k, R, T, D2SPEC, None, dict(ref_matched=S_ISO), b, d[b], inv, ('float64',), scale=SCALE, chunk_clusters=7, family=fam)
    df = str(tmp / f'ref_{fam}_fit'); generate_fitting_bank(k, R, T, D2SPEC, None, dict(ref_matched=S_ISO), df, inv, scale=SCALE, chunk_clusters=7, family=fam); return d, df


def test_scope_counts_and_refusals(tmp_path):
    assert len(ADDED) == 81 and len(FIRST) == 27 and all(int(c) >= 20104 for c in ADDED) and all(int(c) % 100 <= 3 for c in FIRST)
    k = _Kern(); inv = CallInventory(); roots = _roots(20104)
    with pytest.raises(InputContractError): generate_twelve_configuration_bank(k, R, CTX, 20101, roots, 0, str(tmp_path / 'fw'), inv, ('float64',), scale=SCALE)            # first-wave id: FIXED D-2 input, never regenerated
    with pytest.raises(InputContractError): generate_twelve_fitting_bank(k, R, CTX, 20101, roots, str(tmp_path / 'fwf'), inv, scale=SCALE)
    with pytest.raises(InputContractError): generate_twelve_configuration_bank(k, R, CTX, 10104, roots, 0, str(tmp_path / 'e1'), inv, ('float64',), scale=SCALE)            # E1 is not in spec v2
    with pytest.raises(InputContractError): generate_twelve_configuration_bank(k, R, CTX, 20104, dict(roots, ref_matched=S_ISO), 0, str(tmp_path / 'r4'), inv, ('float64',), scale=SCALE)   # roles restricted
    with pytest.raises(InputContractError): generate_twelve_configuration_bank(k, R, CTX, 20104, dict(ref_matched=S_ISO), 0, str(tmp_path / 'r1'), inv, ('float64',), scale=SCALE)
    with pytest.raises(InputContractError): generate_twelve_configuration_bank(k, R, CTX, 20104, roots, 2, str(tmp_path / 'b2'), inv, ('float64',), scale=SCALE)             # batch
    with pytest.raises(InputContractError): generate_twelve_configuration_bank(k, R, CTX, 20104, roots, 0, str(tmp_path / 'sc'), inv, ('float64',), scale=0)                 # scale
    with pytest.raises(InputContractError): generate_twelve_configuration_bank(k, R, CTX, 20104, roots, 1, str(tmp_path / 'u'), inv, ('float64',), scale=0.00014)            # cluster count not an exact shard split
    for notctx in (dict(CTX._d), SPEC2, None):
        with pytest.raises(InputContractError): generate_twelve_configuration_bank(k, R, notctx, 20104, roots, 0, str(tmp_path / 'nc'), inv, ('float64',), scale=SCALE)     # verified context required
    # formal scope sentinel (no large generation): float64 reaches the adapter; float32 at scale 1 is refused (spec v2: f64 only); wrong registry seed refused before numerics
    calls = []
    class Reached(Exception): pass
    orig = d3b.generate_from_latent; d3b.generate_from_latent = lambda *a, **kw: (calls.append(1), (_ for _ in ()).throw(Reached()))
    try:
        with pytest.raises(Reached): generate_twelve_configuration_bank(k, R, CTX, 20104, roots, 1, str(tmp_path / 'f1'), inv, ('float64',), scale=1.0)
        with pytest.raises(Reached): generate_twelve_fitting_bank(k, R, CTX, 20104, roots, str(tmp_path / 'f1f'), inv, scale=1.0)
        with pytest.raises(InputContractError): generate_twelve_configuration_bank(k, R, CTX, 20104, roots, 1, str(tmp_path / 'f2'), inv, ('float64', 'float32'), scale=1.0)
        with pytest.raises(InputContractError): generate_twelve_configuration_bank(k, R, CTX, 20104, roots, 0, str(tmp_path / 'f3'), inv, ('float32',), scale=1.0)
        from step1_engine.registry import CRNRegistry
        with pytest.raises(InputContractError): generate_twelve_configuration_bank(k, CRNRegistry(T['master_seed'] + 1, R.export_groups()), CTX, 20104, roots, 0, str(tmp_path / 'f4'), inv, ('float64',), scale=1.0)
    finally: d3b.generate_from_latent = orig
    assert len(calls) == 2 and not any((tmp_path / n).exists() for n in ('f1', 'f1f', 'f2', 'f3', 'f4'))


def test_small_banks_identities_verification_and_edit_refusal(tmp_path):
    k = _Kern(); inv = CallInventory(); cid = 20104; c = SPEC2['configurations'][str(cid)]
    roots, d, df = _gen_cfg(tmp_path, cid, k, inv)
    with pytest.raises(InputContractError): generate_twelve_configuration_bank(k, R, CTX, cid, roots, 0, d[0], inv, ('float64',), scale=SCALE)                                # fresh attempt
    m0 = verify_twelve_bank_dir(d[0], CTX); m1 = verify_twelve_bank_dir(d[1], CTX, sorted(CONFIG_ROLES)); mf = verify_twelve_bank_dir(df, CTX)
    assert m0['schema'] == MANIFEST_SCHEMA and m0['n_clusters'] == 20 and m1['n_clusters'] == 60 and len(m1['shards']) == 3 and mf['n_clusters'] == 4 and mf['purpose'] == 'fitting' and all(m['formal'] is False and m['scale'] == SCALE for m in (m0, m1, mf))
    ident = CTX.identities
    for m in (m0, m1, mf):
        assert m['origin'] == 'twelve_added' and m['position_index'] == c['position_index'] == 3 and m['evaluation_ids'] == c['evaluation_ids'] and m['roles'] == sorted(CONFIG_ROLES) and m['selections'] == ['float64']
        assert m['table_sha256'] == T['table_sha256'] and m['spec_v1_sha256'] == D2SPEC['spec_sha256'] and m['spec_v2_sha256'] == SPEC2['spec_sha256'] and m['covariance_receipt_sha256'] == ident['covariance_receipt_sha256'] and m['config_map_sha256'] == ident['config_map_sha256'] and m['master_seed'] == T['master_seed'] and m['wave_id'] == 1
        assert len(m['calls']) == 1 and m['calls'][0]['key_rotation'][:4] == [T['master_seed'], 1, 200 if m['purpose'] == 'evaluation' else 300, m['crn_group']]
    assert m0['crn_group'] == c['crn']['evaluation_group'] == group_for(T, 'evaluation', 'E2') and mf['crn_group'] == c['crn']['fitting_group'] == group_for(T, 'fitting', 'E2')
    side = json.load(open(os.path.join(d[1], m1['shards'][2]['sidecar']))); assert side['schema'] == SHARD_SCHEMA and side['rotation_index'] == [40, 60] and side['uids'] == [[1, 200, m1['crn_group'], 1, 40], [1, 200, m1['crn_group'], 1, 59]] and side['covariance'] == c['covariance'] and side['global_clusters'] == [10040, 10060]
    # the D-2 verifier does not accept a D-3 bank (schema) and the D-3 verifier does not accept a D-2 bank
    with pytest.raises(InputContractError): d2b.verify_bank_dir(d[0])
    rd, rf = _gen_ref(tmp_path, 'E2', k, inv)
    with pytest.raises(InputContractError): verify_twelve_bank_dir(rd[0], CTX)
    # edits refused: array, sidecar (restamped), manifest (restamped), missing shard
    for edit in ('array', 'sidecar', 'manifest', 'partial'):
        e = str(tmp_path / f'edit_{edit}'); shutil.copytree(d[1], e); man = json.load(open(os.path.join(e, 'COMPLETE.json'))); sh = man['shards'][1]
        if edit == 'array':
            z = dict(np.load(os.path.join(e, sh['file']))); z['model_matched__float64__T1'] = z['model_matched__float64__T1'] + 1e-9; np.savez(os.path.join(e, sh['file']), **z)
        elif edit == 'sidecar':
            s = json.load(open(os.path.join(e, sh['sidecar']))); s['position_index'] = 4; open(os.path.join(e, sh['sidecar']), 'w').write(json.dumps(s, indent=1))
        elif edit == 'manifest':
            man['position_index'] = 4; man['manifest_sha256'] = d2b._sha(json.dumps({k_: v for k_, v in man.items() if k_ != 'manifest_sha256'}, sort_keys=True).encode()); open(os.path.join(e, 'COMPLETE.json'), 'w').write(json.dumps(man, indent=1))
        else: os.remove(os.path.join(e, sh['file']))
        with pytest.raises(InputContractError): verify_twelve_bank_dir(e, CTX)
    inc = str(tmp_path / 'incomplete'); shutil.copytree(d[0], inc); os.remove(os.path.join(inc, 'COMPLETE.json'))
    with pytest.raises(InputContractError): verify_twelve_bank_dir(inc, CTX)
    # a manifest re-stamped to another configuration's identity (same family) is refused: the sidecars / arrays carry the original position
    e2 = str(tmp_path / 'cid_swap'); shutil.copytree(d[0], e2); man = json.load(open(os.path.join(e2, 'COMPLETE.json'))); man['config_id'] = 20105; man['evaluation_ids'] = SPEC2['configurations']['20105']['evaluation_ids']; man['position_index'] = 4
    man['manifest_sha256'] = d2b._sha(json.dumps({k_: v for k_, v in man.items() if k_ != 'manifest_sha256'}, sort_keys=True).encode()); open(os.path.join(e2, 'COMPLETE.json'), 'w').write(json.dumps(man, indent=1))
    with pytest.raises(InputContractError): verify_twelve_bank_dir(e2, CTX)


def test_same_numerical_path_as_d2_and_same_latent_as_reference(tmp_path):
    """The D-3b generator is the D-2 numerical path under a different binding: the same roots through d2_bank.generate_configuration_bank (spec v1, config 20101 of the same
    family E2 — used here only as a spec-v1 carrier for the roots; nothing is registered) give bit-identical arrays; the family reference shares the cid structure."""
    k = _Kern(); inv = CallInventory(); cid = 20104; roots, d, df = _gen_cfg(tmp_path, cid, k, inv)
    d2d = str(tmp_path / 'd2_20101_b0'); generate_configuration_bank(k, R, T, D2SPEC, 20101, roots, 0, d2d, inv, ('float64',), scale=SCALE, chunk_clusters=7)
    za = np.load(os.path.join(d[0], 'cfg20104_b0_s0.npz')); zb = np.load(os.path.join(d2d, 'cfg20101_b0_s0.npz'))
    assert set(za.files) == set(zb.files) and all(np.array_equal(za[n], zb[n]) for n in za.files)
    d2f = str(tmp_path / 'd2_20101_fit'); generate_fitting_bank(k, R, T, D2SPEC, 20101, roots, d2f, inv, scale=SCALE, chunk_clusters=7)
    fa = np.load(os.path.join(df, 'cfg20104_fit_s0.npz')); fb = np.load(os.path.join(d2f, 'cfg20101_fit_s0.npz')); assert all(np.array_equal(fa[n], fb[n]) for n in fa.files)
    # different chunking -> same bytes (chunk is a storage / memory label, not an identity)
    d_alt = str(tmp_path / 'cfg20104_alt_b0'); generate_twelve_configuration_bank(k, R, CTX, cid, roots, 0, d_alt, inv, ('float64',), scale=SCALE, chunk_clusters=3)
    assert open(os.path.join(d_alt, 'cfg20104_b0_s0.npz'), 'rb').read() == open(os.path.join(d[0], 'cfg20104_b0_s0.npz'), 'rb').read()
    # family reference (D-2 generator, ref_matched) on the same latent: identical cid; with the reference root as the matched root the T arrays coincide
    rd, rf = _gen_ref(tmp_path, 'E2', k, inv); zr = np.load(os.path.join(rd[0], 'ref_b0_s0.npz')); assert np.array_equal(zr['cid'], za['cid'])
    d_iso = str(tmp_path / 'cfg20104_iso_b0'); generate_twelve_configuration_bank(k, R, CTX, cid, dict(roots, model_matched=S_ISO), 0, d_iso, inv, ('float64',), scale=SCALE, chunk_clusters=7); zi = np.load(os.path.join(d_iso, 'cfg20104_b0_s0.npz'))
    assert np.array_equal(zi['model_matched__float64__T1'], zr['ref_matched__float64__T1']) and np.array_equal(zi['model_matched__float64__T2'], zr['ref_matched__float64__T2'])
    # batch-0 rows are the prefix of the family latent: the batch-1 rotation index restarts at 0 within batch 1 (D-2 convention), UIDs are batch-keyed
    m1 = verify_twelve_bank_dir(d[1], CTX); assert json.load(open(os.path.join(d[1], m1['shards'][0]['sidecar'])))['uids'][0] == [1, 200, m1['crn_group'], 1, 0]


def test_reference_reuse_binding_and_intake(tmp_path):
    k = _Kern(); inv = CallInventory(); fam = 'E2'; rd, rf = _gen_ref(tmp_path, fam, k, inv)
    # formal binding: the D-2 verifier accepts the small reference, but it is NOT the ledger unit recorded in spec v2 -> refused as a fixed input
    assert d2b.verify_bank_dir(rd[0], ('ref_matched',))['n_clusters'] == 20
    for unit, dd in (('ref_E2_b0', rd[0]), ('ref_E2_b1', rd[1]), ('ref_E2_fit', rf)):
        with pytest.raises(InputContractError): verify_reused_reference_dir(dd, CTX, fam, unit)
    with pytest.raises(InputContractError): verify_reused_reference_dir(rd[0], CTX, 'E1', 'ref_E1_b0')
    with pytest.raises(InputContractError): verify_reused_reference_dir(rd[0], CTX, fam, 'cfg20104_b0')
    assert {u: SPEC2['family_reference'][fam]['units'][u]['n_rows'] for u in ('ref_E2_b0', 'ref_E2_b1', 'ref_E2_fit')} == dict(ref_E2_b0=1000000, ref_E2_b1=3000000, ref_E2_fit=200000)
    # intake of all 12 positions of E2 / L1.00 (3 first-wave positions are FIXED D-2 inputs and are not generated here: the size input is exercised with 12 added-style supplies
    # by generating the 9 added positions and re-labelling nothing — instead, the 12 supplies are the 9 added ones of L1.00 plus the 3 added ones of L1.20 re-checked below)
    added_L100 = [int(c) for c in ADDED if SPEC2['configurations'][c]['family'] == fam and SPEC2['configurations'][c]['size_id'] == 'L1.00']; assert len(added_L100) == 9
    sup = {}; info = {}
    for cid in added_L100[:2]:
        roots, d, df = _gen_cfg(tmp_path, cid, k, inv); full = dict(roots, ref_matched=S_ISO)
        for system in ('matched', 'native'):
            s, i = intake_twelve_bank(cid, system, d, rd, df, rf, full, CTX, formal=False); sup[(cid, system)] = s; info[(cid, system)] = i
            e = CTX.receipt['positions'][str(cid)]
            assert isinstance(s, BankSupply) and s.config_id == cid and s.system == system and s.cov_manifest['cov_array_sha256'] == e['cov_array_sha256'] and s.cov_manifest['cov_file_sha256'] == e['cov_file_sha256'] and s.cov_manifest['pc1_status'] == 'PC1_PASS' and s.cov_manifest['covariance_receipt_sha256'] == CTX.identities['covariance_receipt_sha256']
            assert s.batches == {0: (0, 2000), 1: (2000, 8000)} and len(s.cluster_uids) == 80 and s.cluster_uids[20] == ClusterUID(1, 200, group_for(T, 'evaluation', fam), 1, 0) and s.m == 100 and len(s.T1_model) == 8000 and s.fitting.cid.max() == 3
            assert i['n_clusters'] == {0: 20, 1: 60} and i['fitting_clusters'] == 4
        # native system consumes the configuration's own ref_native; matched consumes the family reference
        zm = np.load(os.path.join(d[0], f'cfg{cid}_b0_s0.npz')); zr = np.load(os.path.join(rd[0], 'ref_b0_s0.npz'))
        assert np.array_equal(sup[(cid, 'native')].T1_ref[:2000], zm['ref_native__float64__T1']) and np.array_equal(sup[(cid, 'matched')].T1_ref[:2000], zr['ref_matched__float64__T1']) and np.array_equal(sup[(cid, 'native')].T1_model[:2000], zm['model_native__float64__T1'])
        # refusals: formal requested on non-formal banks; wrong roots; other configuration; missing batch; three roots only; wrong reference family
        with pytest.raises(InputContractError): intake_twelve_bank(cid, 'matched', d, rd, df, rf, full, CTX, formal=True)
        with pytest.raises(InputContractError): intake_twelve_bank(cid, 'matched', d, rd, df, rf, dict(full, model_matched=np.eye(21)), CTX, formal=False)
        with pytest.raises(InputContractError): intake_twelve_bank(cid, 'matched', d, rd, df, rf, dict(full, ref_matched=np.eye(21)), CTX, formal=False)
        with pytest.raises(InputContractError): intake_twelve_bank(cid + 1, 'matched', d, rd, df, rf, full, CTX, formal=False)
        with pytest.raises(InputContractError): intake_twelve_bank(cid, 'matched', {0: d[0]}, rd, df, rf, full, CTX, formal=False)
        with pytest.raises(InputContractError): intake_twelve_bank(cid, 'matched', d, rd, df, rf, roots, CTX, formal=False)
        with pytest.raises(InputContractError): intake_twelve_bank(cid, 'both', d, rd, df, rf, full, CTX, formal=False)
        with pytest.raises(InputContractError): intake_twelve_bank(cid, 'matched', d, rd, df, rf, full, dict(CTX._d), formal=False)
    rd7, rf7 = _gen_ref(tmp_path, 'E7', k, inv)
    with pytest.raises(InputContractError): intake_twelve_bank(added_L100[0], 'matched', {0: str(tmp_path / f'cfg{added_L100[0]}_b0'), 1: str(tmp_path / f'cfg{added_L100[0]}_b1')}, rd7, str(tmp_path / f'cfg{added_L100[0]}_fit'), rf7, dict(_roots(added_L100[0]), ref_matched=S_ISO), CTX, formal=False)
    # the intake output feeds the accepted 12-position size input: 12 supplies (2 real intakes + 10 synthetic on the same latent / receipt identities) are accepted; 11 refused
    g = group_for(T, 'evaluation', fam); uids = sup[(added_L100[0], 'matched')].cluster_uids; plans, fplans, ident = fix_family_plans(T, fam, {0: uids[:20], 1: uids[20:]}, 4, T['master_seed'], B=20, B_KDE=25)
    def synth(cid):
        e = CTX.receipt['positions'][str(cid)]; base = sup[(added_L100[0], 'matched')]
        return BankSupply(cid, 'matched', base.T1_model + 0.01 * e['position_index'], base.T2_model, base.T1_ref, base.T2_ref, list(base.cluster_uids), base.m, dict(base.batches), base.fitting, dict(cov_file_sha256=e['cov_file_sha256'], cov_array_sha256=e['cov_array_sha256']), None)
    all12 = [r['config_id'] for r in CTX.config_map['configurations'] if r['family'] == fam and r['size_id'] == 'L1.00']; assert len(all12) == 12
    supplies = [sup[(c_, 'matched')] if (c_, 'matched') in sup else synth(c_) for c_ in all12]
    fi = build_twelve_size_input(CTX, fam, 'L1.00', 'matched', supplies, plans, fplans); assert len(fi.configs) == 12 and abs(sum(c_.weight for c_ in fi.configs) - 1) < 1e-12
    with pytest.raises(InputContractError): build_twelve_size_input(CTX, fam, 'L1.00', 'matched', supplies[:11], plans, fplans)
