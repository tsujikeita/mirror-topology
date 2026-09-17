# -*- coding: utf-8 -*-
"""B-2 tranche 23: adopted tranche-22 audit fixes; legacy kernel port with two-layer regression — (i) in-environment bit identity against the frozen A10 v1.2.9 notebook kernel
(cells executed from the frozen notebook JSON), (ii) cross-environment agreement with the A10 official calibration checkpoint (Colab) within registered tolerances."""
import os, sys, json, io, contextlib, hashlib
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine.errors import InputContractError
MT = os.environ.get('B3_MT', '/home/claude/mt'); NB = os.environ.get('B3_A10_NB', MT + '/results/step1_phaseA/A10_freeze/MirrorTopology_Step1_A10_v1.2.9.ipynb')
OFFICIAL = os.environ.get('B3_A10_CHECKPOINT', os.path.join(os.path.dirname(__file__), 'reference_assets', 'a10a_calibration_official.npz'))
have_mt = os.path.exists(os.path.join(MT, 'results/step1_phaseA/A5_freeze/s1_Bstack_l2_4_N16_common_v1.npz')) and os.path.exists(os.path.join(MT, 'docs/step0_frozen_Bpm_v1.npz'))
frozen = pytest.mark.skipif(not have_mt, reason='mirror-topology checkout with frozen assets not present (external asset integration test)')

@frozen
def test_legacy_kernel_assets_and_representation_gates():
    from step1_engine.legacy_kernel import LegacyKernel, GEN_NS
    from scipy.spatial.transform import Rotation
    k = LegacyKernel(MT); rg = np.random.default_rng(20260912); Rt = Rotation.random(num=8, rng=rg).as_matrix(); Db = k.D_batch(Rt)
    assert max(np.abs(Db[i] - k.D_of_R(Rt[i])).max() for i in range(8)) < 1e-12 and np.abs(np.einsum('kab,kac->kbc', Db, Db) - np.eye(21)).max() < 1e-10 and np.abs(k.D_of_R(Rt[0] @ Rt[1]) - Db[0] @ Db[1]).max() < 1e-10
    xt = np.random.default_rng(1).standard_normal((5, 21)); d64 = k.scan(xt, 'float64')
    assert max(abs(d64['T1'][i] - min(xt[i] @ k.Bp[a] @ xt[i] for a in range(3072))) / abs(d64['T1'][i]) for i in range(5)) < 1e-12
    S_I, iI = k.psqrt(k.C_ISO); assert iI['clip'] == 0 and iI['recon'] < 1e-10
    out, cid, info = k.generate(2000, 100, (GEN_NS['calibration'], 0), [S_I], ('float64', 'float32')); assert info['K'] == 20 and np.isfinite(out[(0, 'float64')]['T1']).all()

@pytest.mark.skipif(not (have_mt and os.path.exists(NB)), reason='frozen A10 notebook not present (external asset integration test)')
def test_legacy_kernel_bit_identical_to_frozen_notebook_cell():
    """Execute the frozen A10 v1.2.9 A10a cell up to the generator definition (assets + representation + scan + generate) in this environment and compare with the port."""
    from step1_engine.legacy_kernel import LegacyKernel, GEN_NS
    nb_bytes = open(NB, 'rb').read()
    assert hashlib.sha256(nb_bytes).hexdigest() == 'c11c41413e33754444118401c8c102b69ca430650619d409bef568f94bba1209', 'frozen A10 notebook file identity mismatch'
    nb = json.loads(nb_bytes); src = ''.join(nb['cells'][1]['source']); cut = src.find("CFG = dict(smoke=")
    assert cut > 0, 'A10a extraction boundary not found' 
    ns = {'A10_MODE': 'smoke'}; os.environ['A10_BASE'] = '/tmp/a10w/base'; os.environ['A10_WORK'] = '/tmp/a10w'
    with contextlib.redirect_stdout(io.StringIO()): exec(compile(src[:cut], 'a10a', 'exec'), ns)                      # frozen notebook code (smoke mode; repo pinned at the A8 commit)
    required_reference_gates = (
        'G_live_modules', 'G_asset_file_sha', 'G_bstack_array_sha', 'G_cvec_sha',
        'G_basis_order', 'G_a9_basis_hashes', 'G_quadrature_orthonormal',
        'G_quadrature_gauss_legendre_exact', 'G_D_batch_matches_single',
        'G_D_orthogonal', 'G_D_homomorphism', 'G_D_direct_geometry',
        'G_D_known_z_rotation', 'G_antipode_map', 'G_a8b_kernel_exact_regression',
        'G_scan_vs_direct', 'G_sqrt_hard')
    assert all(ns['GATES'].get(g) for g in required_reference_gates), {g: ns['GATES'].get(g) for g in required_reference_gates}
    k = LegacyKernel(MT); S_I = k.psqrt(k.C_ISO)[0]; assert np.array_equal(S_I, ns['S_I'])
    xt = np.random.default_rng(7).standard_normal((4100, 21))
    for sel in ('float64', 'float32'):
        a = k.scan(xt, sel); b = ns['scan'](xt, sel)
        assert np.array_equal(a['AX'], b['AX']) and np.array_equal(a['T1'], b['T1']) and np.array_equal(a['T2'], b['T2']) and np.array_equal(a['PL'], b['PL'])   # bit-identical scan
    o1, c1, _ = k.generate(4000, 100, (GEN_NS['pseudo'], 0), [S_I], ('float64', 'float32')); o2, c2, _ = ns['generate'](4000, 100, (ns['GEN_NS']['pseudo'], 0), [ns['S_I']], ('float64', 'float32'))
    assert np.array_equal(c1, c2)
    assert all(np.array_equal(o1[key][field], o2[key][field]) for key in o1 for field in ('T1', 'T2', 'AX', 'PL'))

@pytest.mark.skipif(not (have_mt and os.path.exists(OFFICIAL)), reason='A10 official checkpoint not present (external asset integration test)')
def test_legacy_kernel_cross_environment_agreement_with_a10_official():
    """Regenerate the first 20 000 rows of the A10 official calibration bank (Colab) here and compare: T1/T2 within 1e-9 relative on plane-identical rows; flip rate recorded."""
    from step1_engine.legacy_kernel import LegacyKernel, GEN_NS
    reference_bytes = open(OFFICIAL, 'rb').read()
    assert hashlib.sha256(reference_bytes).hexdigest() == '6a8c87889ec1d7a5d35336a3cdc30f9537376f2b3878ac9d1ee12cc34319c5df', 'frozen A10 calibration checkpoint identity mismatch'
    k = LegacyKernel(MT); S_I = k.psqrt(k.C_ISO)[0]; z = np.load(io.BytesIO(reference_bytes), allow_pickle=False); n = 20000
    out, cid, _ = k.generate(n, 100, (GEN_NS['calibration'], 0), [S_I], ('float64',)); d = out[(0, 'float64')]
    # Candidate acceptance strengthens the engineering regression to the
    # reported 20,000-row baseline; it does NOT relax a scientific threshold.
    assert np.array_equal(cid, z['cid'][:n])
    for field in ('T1', 'T2', 'AX', 'PL'):
        assert d[field].shape == (n,) and np.isfinite(d[field]).all(), field
    assert np.array_equal(d['AX'], z['AX'][:n]), 'primary raw-axis mismatch'
    assert np.array_equal(d['PL'], z['PL'][:n]), 'primary plane mismatch'
    for field in ('T1', 'T2'):
        ref = z[field][:n]
        assert np.isfinite(ref).all() and np.all(ref != 0)
        rel = np.abs(d[field]-ref)/np.abs(ref)
        assert rel.max() < 1e-9, (field, rel.max())
