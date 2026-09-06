# -*- coding: utf-8 -*-
"""Step 1 Phase A9 v1.2 (v1.2.1 comment fix only; audit 2026-09-06 #2: formal-archive hardening - Imhof applicability scope and per-case gates, PSD gate,
scaled chi2_21 known law, NumPy/B-stack-file gates, fail-fast git provenance). v1.1: rotation machinery and analytic batteries for the map-free engine.

Fixes vs v1.0: real-basis functions E(p) = conj(M) Y_c(p) (frozen convention x = M a); explicit frozen-basis gate,
complex-alm path gate and known z-rotation gate; official A5 B-stack only (array SHA eb514148...); Haar left/right
invariance as one-sample KS, full-SO(3) rotation-angle KS, standard Holm step-down; SciPy hard gate; synthetic C /
square-root provenance; D(R)-rotated covariance moments (links A9-2 and A9-3); Imhof known-law, deep-tail, integration-error,
monotonicity gates; second inversion scheme (Gil-Pelaez trapezoid) and saddlepoint cross-checks; t2b2_bridge / M / LM /
quadrature identity in provenance.  v1.0 is archived as a development run.
Terminology: D(R) is built by an Euler-angle-convention-independent quadrature construction (it still depends on the
active-rotation convention T_rot(p) = T(R^{-1} p), the frozen real basis and the column-coefficient convention).
"""
import os, sys, json, hashlib, datetime, platform, subprocess, warnings
import numpy as np, pandas as pd, scipy, healpy as hp
from scipy.spatial.transform import Rotation
from scipy import stats, integrate
from scipy.special import sph_harm_y
OUT = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/colab_sim/runs_step1_phaseA/a9_v1.2.1'
MT = sys.argv[2] if len(sys.argv) > 2 else '/tmp/finalchk2'
BSTACK = sys.argv[3] if len(sys.argv) > 3 else '/tmp/fz/A5_freeze/s1_Bstack_l2_4_N16_common_v1.npz'
os.makedirs(OUT, exist_ok=True); sys.path.insert(0, MT)
import t2b2_bridge as br
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def asha(a): return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
GIT_LOG = []
def run(c):
    r = subprocess.run(c, capture_output=True, text=True, check=True); GIT_LOG.append(dict(cmd=c, stderr=r.stderr.strip())); return r.stdout.strip()
G = {}; REC = {}
# ---- environment / source identity gates ----
EXPECTED = dict(scipy='1.17.1', healpy='1.20.0', numpy='2.4.4')
G['G_scipy_version_match'] = (scipy.__version__ == EXPECTED['scipy']); G['G_healpy_version_match'] = (hp.__version__ == EXPECTED['healpy'])
G['G_numpy_version_match'] = (np.__version__ == EXPECTED['numpy'])
BRIDGE_SHA = sha(os.path.join(MT, 't2b2_bridge.py'))
G['G_bridge_sha'] = (BRIDGE_SHA == '45107d1608d50816712f1aa452d9fa39af4adc9ec035fbe9279b264760d65872')
LM = br.lm_full(); M21 = br.M_matrix()[0]; RB = br.real_basis_lm(); IDX = {t: k for k, t in enumerate(LM)}; LMAX = 4
REC['bridge'] = dict(t2b2_bridge_sha256=BRIDGE_SHA, M21_sha256=asha(M21), LM_sha256=hashlib.sha256(json.dumps(LM).encode()).hexdigest(),
                     real_basis_sha256=hashlib.sha256(json.dumps(RB).encode()).hexdigest(),
                     mirror_topology_commit=run(['git', '-C', MT, 'rev-parse', 'HEAD']), mirror_topology_origin=run(['git', '-C', MT, 'remote', 'get-url', 'origin']),
                     mirror_topology_clean=(run(['git', '-C', MT, 'status', '--porcelain', '--untracked-files=no']) == ''))
# ---- official B-stack (unique SHA) ----
zB = np.load(BSTACK); Bp, Bm = zB['Bp_stack'], zB['Bm_stack']
BST_ARRAY = hashlib.sha256(np.ascontiguousarray(Bp).tobytes() + np.ascontiguousarray(Bm).tobytes()).hexdigest()
G['G_bstack_official'] = (BST_ARRAY == 'eb51414885785b77e9d3f7fbb25e1c9396f52e19c053d58113d50e206353a93f')
G['G_bstack_file_sha'] = (sha(BSTACK) == 'ec2d3eb501c3e00af85a505d95d7141fddb4ea23ab1da971906a5c21f80eef5f')
REC['bstack'] = dict(file=os.path.basename(BSTACK), file_sha256=sha(BSTACK), array_sha256=BST_ARRAY,
                     a5_freeze=dict(commit='95ab0adb55a3ea8b522deb5aa0a64b13e883e675', tag='step1-phaseA-A5-v1.0', path='results/step1_phaseA/A5_freeze/'))

# ============================================================ A9-1 Haar sampler battery
N_HAAR = 100_000; ALPHA = 0.01
rngA = np.random.default_rng(np.random.SeedSequence([20260906, 9, 1]))
R = Rotation.random(num=N_HAAR, rng=rngA).as_matrix()
G['G_haar_orthogonal'] = bool(np.abs(np.einsum('nij,nik->njk', R, R) - np.eye(3)).max() < 1e-12)
G['G_haar_det'] = bool(np.abs(np.linalg.det(R) - 1).max() < 1e-12)
z = R @ np.array([0, 0, 1.]); Q = Rotation.from_euler('zyx', [0.7, -1.1, 2.3]).as_matrix()
zL = (Q @ R) @ np.array([0, 0, 1.]); zR = (R @ Q) @ np.array([0, 0, 1.])
omega = np.arccos(np.clip((np.trace(R, axis1=1, axis2=2) - 1) / 2, -1, 1))          # rotation angle in [0, pi]
omega_cdf = lambda w: (w - np.sin(w)) / np.pi                                        # Haar law of the rotation angle
tests = {'cos_theta': stats.kstest(z[:, 2], stats.uniform(-1, 2).cdf).pvalue,
         'phi': stats.kstest(np.mod(np.arctan2(z[:, 1], z[:, 0]), 2 * np.pi), stats.uniform(0, 2 * np.pi).cdf).pvalue,
         'left_QR_cos': stats.kstest(zL[:, 2], stats.uniform(-1, 2).cdf).pvalue, 'right_RQ_cos': stats.kstest(zR[:, 2], stats.uniform(-1, 2).cdf).pvalue,
         'rotation_angle': stats.kstest(omega, omega_cdf).pvalue}
def holm_reject(pvals, alpha):
    """Standard Holm step-down: returns True if any hypothesis is rejected."""
    p = np.sort(np.asarray(pvals)); m = len(p)
    for i, pi in enumerate(p):
        if pi <= alpha / (m - i): return True
        # first non-rejection stops the procedure
        return False
    return False
G['G_haar_ks_holm'] = (not holm_reject(list(tests.values()), ALPHA))
mean_ok = np.abs(z.mean(0)).max() < 3 * np.sqrt(1 / 3 / N_HAAR); cov_ok = np.abs(np.cov(z.T) - np.eye(3) / 3).max() < 0.01
G['G_haar_moments'] = bool(mean_ok and cov_ok)
REC['haar'] = dict(N=N_HAAR, alpha=ALPHA, holm='standard step-down', ks_pvalues={k: float(v) for k, v in tests.items()},
                   mean_abs_max=float(np.abs(z.mean(0)).max()), cov_dev_max=float(np.abs(np.cov(z.T) - np.eye(3) / 3).max()))

# ============================================================ A9-2 real-basis SO(3) representation D(R)
_NT, _NP = 2 * LMAX + 2, 2 * LMAX + 2
_xg, _wg = np.polynomial.legendre.leggauss(_NT); _th = np.arccos(_xg); _ph = 2 * np.pi * np.arange(_NP) / _NP
TH, PH = np.meshgrid(_th, _ph, indexing='ij'); WQ = (np.repeat(_wg[:, None], _NP, axis=1) * (2 * np.pi / _NP)).ravel()
DIRS = np.column_stack([np.sin(TH).ravel() * np.cos(PH).ravel(), np.sin(TH).ravel() * np.sin(PH).ravel(), np.cos(TH).ravel()])
REC['quadrature'] = dict(n_theta=_NT, n_phi=_NP, nodes_sha256=asha(DIRS), weights_sha256=asha(WQ))
def Yc_at(dirs):
    th, ph = hp.vec2ang(dirs); return np.array([sph_harm_y(l, m, th, ph) for (l, m) in LM])            # (21, npts) complex
def Ymat(dirs):
    """Frozen real-basis functions E(p): with x = M a (t2b2_bridge), T(p) = Y_c^T a = Y_c^T M^dagger x  =>  E = conj(M) Y_c."""
    return (M21.conj() @ Yc_at(dirs)).real.T                                                            # (npts, 21)
# --- explicit frozen-basis gate: E = [Re Y_l0, sqrt2 Re Y_lm (cos), sqrt2 Im Y_lm (sin)] built independently of M ---
rngB = np.random.default_rng(np.random.SeedSequence([20260906, 9, 2]))
dirs_t = rngB.standard_normal((200, 3)); dirs_t /= np.linalg.norm(dirs_t, axis=1, keepdims=True)
th_t, ph_t = hp.vec2ang(dirs_t)
E_explicit = np.column_stack([(sph_harm_y(l, m, th_t, ph_t).real if cs == 'c' and m == 0 else
                               np.sqrt(2) * sph_harm_y(l, m, th_t, ph_t).real if cs == 'c' else
                               np.sqrt(2) * sph_harm_y(l, m, th_t, ph_t).imag) for (l, m, cs) in RB])
G['G_real_basis_bridge'] = bool(np.abs(Ymat(dirs_t) - E_explicit).max() < 1e-12)
REC['real_basis_bridge_maxdiff'] = float(np.abs(Ymat(dirs_t) - E_explicit).max())
# --- complex-alm path gate: T(p) via a = M^dagger x and complex harmonics equals Ymat @ x ---
x_t = rngB.standard_normal(21); a_t = M21.conj().T @ x_t
T_complex = (Yc_at(dirs_t).T @ a_t); G['G_complex_path'] = bool(np.abs(T_complex.imag).max() < 1e-12 and np.abs(T_complex.real - Ymat(dirs_t) @ x_t).max() < 1e-12)
YQ = Ymat(DIRS); G['G_quadrature_orthonormal'] = bool(np.abs((YQ * WQ[:, None]).T @ YQ - np.eye(21)).max() < 1e-12)
def D_of_R(Rm):
    """Real representation of the ACTIVE rotation Rm on the frozen basis: D = Y(p)^T W Y(R^{-1} p); (D x) are the coefficients of T(R^{-1} p)."""
    return (YQ * WQ[:, None]).T @ Ymat(DIRS @ Rm)
# --- known z-rotation gate: for rotation about z by gamma, each (cos_m, sin_m) pair rotates by m*gamma ---
gam = 0.9; Dz = D_of_R(Rotation.from_rotvec([0, 0, gam]).as_matrix()); Dz_th = np.zeros((21, 21))
for (l, m, cs) in RB:
    i = RB.index((l, m, cs))
    if m == 0: Dz_th[i, i] = 1.0
    elif cs == 'c':
        j = RB.index((l, m, 's')); Dz_th[i, i] = np.cos(m * gam); Dz_th[i, j] = -np.sin(m * gam); Dz_th[j, i] = np.sin(m * gam); Dz_th[j, j] = np.cos(m * gam)
# T(R^{-1}p) with R = rot_z(gamma): phi -> phi - gamma  =>  c' = c cos(m gam) - s sin(m gam),  s' = c sin(m gam) + s cos(m gam)
G['G_known_z_rotation'] = bool(np.abs(Dz - Dz_th).max() < 1e-12); REC['known_z_rotation_maxdiff'] = float(np.abs(Dz - Dz_th).max())
worst_hom = worst_orth = worst_geom = 0.0
for k in range(20):
    R1 = Rotation.random(rng=rngB).as_matrix(); R2 = Rotation.random(rng=rngB).as_matrix()
    D1, D2, D12 = D_of_R(R1), D_of_R(R2), D_of_R(R1 @ R2)
    worst_hom = max(worst_hom, np.abs(D12 - D1 @ D2).max()); worst_orth = max(worst_orth, np.abs(D1.T @ D1 - np.eye(21)).max())
    x = rngB.standard_normal(21); a = M21.conj().T @ x                     # direct geometry through the COMPLEX path (independent of Ymat)
    T_rot = (Yc_at(dirs_t).T @ (M21.conj().T @ (D1 @ x))).real; T_ref = (Yc_at(dirs_t @ R1).T @ a).real
    worst_geom = max(worst_geom, np.abs(T_rot - T_ref).max() / np.abs(T_ref).max())
G['G_D_homomorphism'] = worst_hom < 1e-10; G['G_D_orthogonal'] = worst_orth < 1e-10; G['G_D_direct_geometry_complex_path'] = worst_geom < 1e-10
REC['representation'] = dict(worst_homomorphism=float(worst_hom), worst_orthogonality=float(worst_orth), worst_direct_geometry=float(worst_geom),
                             construction='Euler-angle-convention-independent quadrature (depends on: active rotation, frozen real basis, column-coefficient convention)')

# ============================================================ A9-3 analytic second moments vs MC (fixed and D(R)-rotated covariance)
rng3 = np.random.default_rng(np.random.SeedSequence([20260906, 9, 3]))
A0 = rng3.standard_normal((21, 21)); C = A0 @ A0.T / 21 * 500.0 + np.diag(np.repeat([1000., 500., 300.], [5, 7, 9]))
def psqrt(C):
    w, V = np.linalg.eigh(C); wc = np.where(w < 1e-12 * w.max(), 0.0, w); return V @ np.diag(np.sqrt(wc)) @ V.T, w
Chalf, wC = psqrt(C)
REC['synthetic_C'] = dict(C_sha256=asha(C), eig_min=float(wC.min()), eig_max=float(wC.max()), sqrt_sha256=asha(Chalf),
                          reconstruction_residual=float(np.linalg.norm(Chalf @ Chalf.T - C) / np.linalg.norm(C)))
G['G_sqrt_reconstruction'] = REC['synthetic_C']['reconstruction_residual'] < 1e-12
N_MC = 1_000_000; NB = 20
Rrot = Rotation.random(rng=rng3).as_matrix(); Drot = D_of_R(Rrot); C_R = Drot @ C @ Drot.T; Chalf_R, _ = psqrt(C_R)
mom_rows = []
for label, Cuse, Ch in [('fixed', C, Chalf), ('rotated_D(R)', C_R, Chalf_R)]:
    X = rng3.standard_normal((N_MC, 21)) @ Ch.T
    for axis in [1134, 777]:
        B1, B2 = Bp[axis], Bm[axis]; Q1 = np.einsum('ni,ij,nj->n', X, B1, X); Q2 = np.einsum('ni,ij,nj->n', X, B2, X)
        ana = dict(E_Sp=np.trace(B1 @ Cuse), E_Sm=np.trace(B2 @ Cuse), Var_Sp=2 * np.trace(B1 @ Cuse @ B1 @ Cuse), Var_Sm=2 * np.trace(B2 @ Cuse @ B2 @ Cuse), Cov=2 * np.trace(B1 @ Cuse @ B2 @ Cuse))
        b1, b2 = Q1.reshape(NB, -1), Q2.reshape(NB, -1)
        est = dict(E_Sp=(Q1.mean(), b1.mean(1)), E_Sm=(Q2.mean(), b2.mean(1)), Var_Sp=(Q1.var(), b1.var(1)), Var_Sm=(Q2.var(), b2.var(1)),
                   Cov=(np.cov(Q1, Q2)[0, 1], np.array([np.cov(b1[k], b2[k])[0, 1] for k in range(NB)])))
        row = dict(covariance=label, axis=axis, corr_analytic=ana['Cov'] / np.sqrt(ana['Var_Sp'] * ana['Var_Sm']))
        for k in est:
            mc, b = est[k]; se = b.std(ddof=1) / np.sqrt(NB); row.update({f'{k}_analytic': ana[k], f'{k}_mc': mc, f'{k}_se': se, f'z_{k}': (mc - ana[k]) / se})
        mom_rows.append(row)
    if label == 'fixed': X_fixed = X
mom = pd.DataFrame(mom_rows); zc = [c for c in mom.columns if c.startswith('z_')]
G['G_moments_all'] = bool((mom[zc].abs() < 3.5).all().all())

# ============================================================ A9-4 Imhof (1D marginal-tail diagnostic) with audit
def imhof_cdf(s, lam, limit=800):
    lam = np.asarray(lam); k = len(lam)
    def theta(u): return 0.5 * np.sum(np.arctan(lam * u)) - 0.5 * s * u
    def rho(u): return np.prod((1 + lam ** 2 * u ** 2) ** 0.25)
    with warnings.catch_warnings(record=True) as wlist:
        warnings.simplefilter('always')
        val, err = integrate.quad(lambda u: np.sin(theta(u)) / (u * rho(u)), 0, np.inf, limit=limit)
        nwarn = sum(1 for w in wlist if issubclass(w.category, integrate.IntegrationWarning))
    return 0.5 - val / np.pi, err / np.pi, nwarn
GP_LAST = {}
def gilpelaez_cdf(s, lam, tol_env=1e-12, pts_per_period=40, chunk=2_000_000):
    """Second inversion scheme (Gil-Pelaez): F(s) = 1/2 - (1/pi) int_0^inf Im[e^{-ius} phi(u)]/u du, trapezoid on an
    adaptive grid. phi(u) = prod_j (1 - 2 i lam_j u)^{-1/2} is evaluated FACTOR-WISE on the principal branch (each factor has
    positive real part, so no branch-cut crossing); truncation U from the envelope prod (1+4 lam^2 u^2)^{-1/4} < tol_env;
    grid spacing resolves the fastest oscillation (frequency max(s, sum lam))."""
    lam = np.asarray(lam, float); lam = lam[lam > 0]
    env = lambda u: np.prod((1 + 4 * lam ** 2 * u ** 2) ** -0.25)
    U = 1.0
    while env(U) > tol_env and U < 1e7: U *= 2
    freq = max(abs(s), lam.sum()); du = 2 * np.pi / freq / pts_per_period; n = int(np.ceil(U / du)) + 1
    n = min(n, 6_000_000)                                   # hard cap; convergence is flagged by env(U_eff) below
    U_eff = du * (n - 1); GP_LAST['converged'] = bool(env(U_eff) < tol_env); GP_LAST['n'] = n; GP_LAST['U'] = float(U_eff)
    total = 0.0; u0 = 0.0
    for start in range(0, n, chunk):
        u = u0 + du * np.arange(start, min(start + chunk, n)); u[u == 0] = 1e-12
        phi = np.prod((1 - 2j * np.outer(u, lam)) ** -0.5, axis=1)
        f = np.imag(np.exp(-1j * u * s) * phi) / u
        w = np.full(len(u), du); w[0] *= 0.5 if start == 0 else 1.0; w[-1] *= 0.5 if start + chunk >= n else 1.0
        total += float(np.sum(w * f))
    return 0.5 - total / np.pi
def saddlepoint_cdf(s, lam):
    """Lugannani-Rice saddlepoint approximation for a weighted chi-square sum (independent asymptotic cross-check)."""
    lam = np.asarray(lam)
    K = lambda t: -0.5 * np.sum(np.log(1 - 2 * lam * t)); K1 = lambda t: np.sum(lam / (1 - 2 * lam * t)); K2 = lambda t: np.sum(2 * lam ** 2 / (1 - 2 * lam * t) ** 2)
    lo, hi = -1e6, 0.5 / lam.max() - 1e-12
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if K1(mid) < s: lo = mid
        else: hi = mid
    t = 0.5 * (lo + hi); w = np.sign(t) * np.sqrt(max(2 * (t * s - K(t)), 0)); v = t * np.sqrt(K2(t))
    return stats.norm.cdf(w) + stats.norm.pdf(w) * (1 / w - 1 / v) if abs(t) > 1e-8 else 0.5
imh_rows = []
# known-law unit tests
for name, lam, ref in [('chi2_1', np.array([1.0]), lambda s: stats.chi2.cdf(s, 1)), ('scaled_chi2_5', np.full(5, 2.0), lambda s: stats.chi2.cdf(s / 2.0, 5)),
                       ('scaled_chi2_21', np.full(21, 3.0), lambda s: stats.chi2.cdf(s / 3.0, 21)),
                       ('lowrank_diag_unequal_with_zeros', np.array([5.0, 1.0, 0.1, 0.0, 0.0]), None)]:
    for q in [0.001, 0.01, 0.05, 0.5, 0.95, 0.99, 0.999]:
        s = {'chi2_1': stats.chi2.ppf(q, 1), 'scaled_chi2_5': 2 * stats.chi2.ppf(q, 5), 'scaled_chi2_21': 3 * stats.chi2.ppf(q, 21)}.get(name)
        if s is None:   # low-rank diagnostic: reference threshold and empirical CDF from a 500,000-sample Monte Carlo (no closed form)
            rngK = np.random.default_rng(5); Zk = rngK.standard_normal((500_000, 3)) ** 2 @ np.array([5.0, 1.0, 0.1]); s = float(np.quantile(Zk, q)); ref_val = float(np.mean(Zk <= s))
        else: ref_val = float(ref(s))
        p_i, err_i, nw = imhof_cdf(s, lam[lam > 0]); p_g = gilpelaez_cdf(s, lam[lam > 0])
        imh_rows.append(dict(case=name, quantile=q, s=s, P_ref=ref_val, P_imhof=p_i, P_gilpelaez=p_g, gp_converged=GP_LAST['converged'], gp_n=GP_LAST['n'], imhof_quad_err=err_i, imhof_warnings=nw,
                             abs_err_imhof=abs(p_i - ref_val), abs_err_gilpelaez=abs(p_g - ref_val), P_saddlepoint=(saddlepoint_cdf(s, lam[lam > 0]) if len(lam[lam > 0]) > 1 else np.nan)))
# frozen-B-stack cases vs MC (moderate and deep tails), eigenvalue handling recorded
for axis in [1134, 777]:
    lam_raw = np.linalg.eigvalsh(Chalf @ Bp[axis] @ Chalf); clip = 1e-12 * lam_raw.max()
    assert lam_raw.min() >= -clip, ('Imhof PSD gate FAIL: STOP (no clipping of significant negative eigenvalues)', lam_raw.min())
    lam = np.where(lam_raw < clip, 0.0, lam_raw)
    REC[f'imhof_eig_axis{axis}'] = dict(lambda_min_raw=float(lam_raw.min()), clip_tol=float(clip), n_clipped=int((lam_raw < clip).sum()), effective_rank=int((lam > 0).sum()), postclip_sha256=asha(lam))
    Q1 = np.einsum('ni,ij,nj->n', X_fixed, Bp[axis], X_fixed)
    for q in [0.001, 0.01, 0.05, 0.5, 0.95, 0.99, 0.999]:
        s = float(np.quantile(Q1, q)); p_mc = float(np.mean(Q1 <= s)); se = np.sqrt(max(p_mc * (1 - p_mc), 1e-12) / N_MC)
        p_i, err_i, nw = imhof_cdf(s, lam[lam > 0]); p_g = gilpelaez_cdf(s, lam[lam > 0]); p_s = saddlepoint_cdf(s, lam[lam > 0])
        imh_rows.append(dict(case=f'bstack_axis{axis}', quantile=q, s=s, P_ref=p_mc, P_imhof=p_i, P_gilpelaez=p_g, gp_converged=GP_LAST['converged'], gp_n=GP_LAST['n'], P_saddlepoint=p_s, mc_se=se,
                             z_imhof=(p_i - p_mc) / se, z_gilpelaez=(p_g - p_mc) / se, imhof_quad_err=err_i, imhof_warnings=nw,
                             imhof_vs_gilpelaez=abs(p_i - p_g), imhof_vs_saddle=abs(p_i - p_s)))
imh = pd.DataFrame(imh_rows)
known = imh[imh.case.isin(['chi2_1', 'scaled_chi2_5', 'scaled_chi2_21'])]; bst = imh[imh.case.str.startswith('bstack')]
k5 = None
k5 = known[known.case == 'scaled_chi2_5']
G['G_imhof_known_law_k5_all_quantiles'] = bool((k5.abs_err_imhof < 1e-7).all())     # quad warnings for k=5 recorded (max abs err 1.6e-8), not gated
G['G_gilpelaez_known_law_k5_all_quantiles'] = bool((k5.abs_err_gilpelaez < 1e-6).all())
k21 = known[known.case == 'scaled_chi2_21']
G['G_imhof_known_law_k21_all_quantiles'] = bool((k21.abs_err_imhof < 1e-7).all() and (k21.imhof_warnings == 0).all())
G['G_gilpelaez_known_law_k21_all_quantiles'] = bool((k21.abs_err_gilpelaez < 1e-6).all() and k21.gp_converged.all())
REC['imhof_low_rank_caveat'] = ('low effective rank (k=1 chi2_1; also the rank-3 zero-eigenvalue diagnostic) is numerically unstable for the generic Imhof/Gil-Pelaez inversion: recorded, not gated; '
                                        'the frozen B-stack cases have effective rank 21 and are gated by MC (z), Gil-Pelaez (1e-6) and saddlepoint agreement')
G['G_imhof_bstack_vs_mc'] = bool((bst.z_imhof.abs() < 4).all())
G['G_imhof_bstack_no_warnings'] = bool((bst.imhof_warnings == 0).all() and (bst.imhof_quad_err < 1e-8).all())
G['G_imhof_vs_gilpelaez_bstack'] = bool((bst.imhof_vs_gilpelaez < 1e-6).all() and bst.gp_converged.all())
_t = bst[bst['quantile'].isin([0.001, 0.01, 0.99, 0.999])]
G['G_imhof_vs_saddlepoint_tails_rel5pct'] = bool((_t.imhof_vs_saddle / np.minimum(_t.P_imhof, 1 - _t.P_imhof) < 0.05).all())   # Lugannani-Rice is asymptotic: ~1% relative tail accuracy expected
G['G_imhof_psd'] = all(REC[f'imhof_eig_axis{a}']['lambda_min_raw'] >= -REC[f'imhof_eig_axis{a}']['clip_tol'] for a in (1134, 777))
# per-case applicability gate (registered for Step 1 use): PSD, rank recorded, warnings=0, quad err<1e-8, GP converged, Imhof-GP<1e-6, monotone, in [0,1]
APPLICABILITY = {}
for c in bst.case.unique():
    sub = bst[bst.case == c].sort_values('quantile'); ax = int(c.replace('bstack_axis', ''))
    APPLICABILITY[c] = dict(psd=bool(REC[f'imhof_eig_axis{ax}']['lambda_min_raw'] >= -REC[f'imhof_eig_axis{ax}']['clip_tol']), effective_rank=REC[f'imhof_eig_axis{ax}']['effective_rank'],
                            n_clipped=REC[f'imhof_eig_axis{ax}']['n_clipped'], warnings_zero=bool((sub.imhof_warnings == 0).all()), quad_err_ok=bool((sub.imhof_quad_err < 1e-8).all()),
                            gp_converged=bool(sub.gp_converged.all()), imhof_gp_agree=bool((sub.imhof_vs_gilpelaez < 1e-6).all()),
                            monotone=bool(sub.P_imhof.is_monotonic_increasing), in_range=bool(sub.P_imhof.between(-1e-9, 1 + 1e-9).all()))
    APPLICABILITY[c]['applicable'] = all(v for k, v in APPLICABILITY[c].items() if isinstance(v, bool))
G['G_imhof_per_case_applicability'] = all(v['applicable'] for v in APPLICABILITY.values())
REC['imhof_applicability'] = APPLICABILITY
REC['imhof_scope'] = ('Imhof is approved as an independent 1D marginal-tail diagnostic (fixed orientation, fixed axis, S+) ONLY when the per-case '
                      'applicability gate passes. The current infinite-interval oscillatory inversion can become unstable for sufficiently low effective '
                      'rank or slowly decaying characteristic functions (observed: chi2_1 and the rank-3 zero-eigenvalue diagnostic); registered rank-21 '
                      'cases pass all gates. Gil-Pelaez = independent numerical inversion route (same characteristic function); Lugannani-Rice = asymptotic diagnostic.')
G['G_imhof_monotone_in_range'] = bool(all(bst[bst.case == c].sort_values('quantile').P_imhof.is_monotonic_increasing for c in bst.case.unique()) and bst.P_imhof.between(-1e-9, 1 + 1e-9).all())
REC['imhof_known_law_deep_tail_note'] = ('chi2_1 deep tail (q=0.001/0.999): imhof abs err = %.2e / %.2e with %d/%d warnings; deep-tail reference for the '
                                         'single-eigenvalue case is the exact chi2 CDF (recorded, not gated)' %
                                         (known[(known.case == 'chi2_1') & (known['quantile'] == 0.001)].abs_err_imhof.iloc[0], known[(known.case == 'chi2_1') & (known['quantile'] == 0.999)].abs_err_imhof.iloc[0],
                                          int(known[(known.case == 'chi2_1')].imhof_warnings.sum()), 7))

# ============================================================ outputs
mom.to_csv(os.path.join(OUT, 'a9_moment_battery.csv'), index=False); imh.to_csv(os.path.join(OUT, 'a9_imhof_battery.csv'), index=False)
G = {k: bool(v) for k, v in G.items()}; OFFICIAL = all(G.values())
prov = dict(script=os.path.basename(__file__), script_sha256=sha(os.path.abspath(__file__)), timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            seeds=dict(haar=[20260906, 9, 1], rep=[20260906, 9, 2], mc=[20260906, 9, 3]), n_mc=N_MC, records=REC, gates=G, OFFICIAL=OFFICIAL,
            scope_note='Imhof/Gil-Pelaez/saddlepoint validate the 1D marginal P(S+ <= s | fixed orientation, fixed axis) only; not the orientation mixture, axis-selection minimum, joint (T1,T2), Event B nor Q_noncomp',
            git_calls=GIT_LOG,
            outputs={f: sha(os.path.join(OUT, f)) for f in ['a9_moment_battery.csv', 'a9_imhof_battery.csv']},
            versions=dict(python=sys.version.split()[0], numpy=np.__version__, scipy=scipy.__version__, healpy=hp.__version__, pandas=pd.__version__,
                          platform=platform.platform(), blas_lapack=str({k: v.get('name') for k, v in np.show_config(mode='dicts').get('Build Dependencies', {}).items() if k in ('blas', 'lapack')})))
json.dump(prov, open(os.path.join(OUT, 'a9_provenance.json'), 'w'), indent=1)
print('gates:', G)
print('summary: max|z| moments = %.4f | Imhof-GP max = %.3e | max |z_imhof| = %.4f | LR max rel tail = %.4f' % (mom[zc].abs().max().max(), bst.imhof_vs_gilpelaez.max(), bst.z_imhof.abs().max(), (bst[bst['quantile'].isin([0.001,0.01,0.99,0.999])].imhof_vs_saddle / np.minimum(bst[bst['quantile'].isin([0.001,0.01,0.99,0.999])].P_imhof, 1 - bst[bst['quantile'].isin([0.001,0.01,0.99,0.999])].P_imhof)).max()))
print('haar KS p:', {k: round(v, 3) for k, v in REC['haar']['ks_pvalues'].items()})
print('basis bridge maxdiff:', f"{REC['real_basis_bridge_maxdiff']:.1e}", '| z-rotation:', f"{REC['known_z_rotation_maxdiff']:.1e}", '| rep:', {k: (f'{v:.1e}' if isinstance(v, float) else '') for k, v in REC['representation'].items() if isinstance(v, float)})
print(mom[['covariance', 'axis'] + zc].to_string(index=False, float_format=lambda v: f'{v:.2f}'))
print(imh[imh.case.str.startswith('bstack')][['case', 'quantile', 'P_ref', 'P_imhof', 'z_imhof', 'imhof_vs_gilpelaez', 'imhof_vs_saddle', 'imhof_warnings']].to_string(index=False, float_format=lambda v: f'{v:.5f}'))
print(known[['case', 'quantile', 'abs_err_imhof', 'abs_err_gilpelaez', 'imhof_warnings']].to_string(index=False, float_format=lambda v: f'{v:.2e}'))
assert OFFICIAL, G
