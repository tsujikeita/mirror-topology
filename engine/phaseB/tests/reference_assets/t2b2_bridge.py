"""t2b2_bridge v1.2 (2026-08-26c): complex full-m C_q -> frozen-statistic (s+_q, s-_q).

Rules reference: T2b2_decision_rules_frozen_v0.3 Sec.3.1 (six-test battery) + review guards.

Conventions (frozen):
- Complex side: lm_full = [(l,m) for l in (2,3,4) for m in -l..l], C = <a a^H> (Hermitian PSD),
  physical real field => reality condition a_{l,-m} = (-1)^m a_{lm}^*.
- Real side: basis_lm = [(l,0,'c'), (l,1,'c'), (l,1,'s'), ...] matching step0_frozen_Bpm npz;
  x_{l0}=a_{l0}, x_c=(a_{lm}+(-1)^m a_{l,-m})/sqrt2, x_s=i(a_{lm}-(-1)^m a_{l,-m})/sqrt2.
- Alignment (implementation-level freeze, to be ratified in notebook review): the body-frame
  mirror normal y^ is rotated onto the frozen axis d^ = pix2vec(16,1134,ring); the azimuth psi
  about d^ is not fixed by the alignment hypothesis and the common mask breaks the symmetry, so
  s+-_q are reported as the average over N_PSI equally spaced psi with min/max recorded.
- Artifact identity: the scientific-array hash sha256(Bp||Bm) is the source of truth
  (rules v0.3 frozen value 9693b207...); the NPZ file hash is container-dependent and recorded
  as secondary provenance only.
- MC meaning: Gaussian covariance-MC validates the implementation of quadratic MEANS only; the
  physical q-field is non-Gaussian (distribution-level modelling deferred to Step 1+).
"""
import numpy as np
import healpy as hp

LS = (2, 3, 4)
N_PSI = 16          # l<=4: Fourier components up to 8 < 16, so 16-point uniform average is EXACT
RHO_NUM = 1e-6          # absolute numerical floor for rho classification
NOSIG_REL = 1e-9        # no-signal guard: s_tot < NOSIG_REL * max grid s_tot
SMALL_SM_REL = 1e-6     # numerical-small flag for g2max denominators

try:
    from scipy.special import sph_harm_y
    def _Ylm(l, m, th, ph): return sph_harm_y(l, m, th, ph)
except ImportError:
    from scipy.special import sph_harm
    def _Ylm(l, m, th, ph): return sph_harm(m, l, ph, th)


def lm_full(ls=LS):
    return [(l, m) for l in ls for m in range(-l, l + 1)]


def real_basis_lm(ls=LS):
    out = []
    for l in ls:
        out.append((l, 0, 'c'))
        for m in range(1, l + 1):
            out.append((l, m, 'c')); out.append((l, m, 's'))
    return out


def M_matrix(ls=LS):
    """x = M a  (rows: real basis, cols: full-m complex basis)."""
    lmf = lm_full(ls); rb = real_basis_lm(ls)
    idx = {t: a for a, t in enumerate(lmf)}
    M = np.zeros((len(rb), len(lmf)), complex)
    for i, (l, m, cs) in enumerate(rb):
        if m == 0:
            M[i, idx[(l, 0)]] = 1.0
        elif cs == 'c':
            M[i, idx[(l, m)]] = 1 / np.sqrt(2)
            M[i, idx[(l, -m)]] = ((-1) ** m) / np.sqrt(2)
        else:
            M[i, idx[(l, m)]] = 1j / np.sqrt(2)
            M[i, idx[(l, -m)]] = -1j * ((-1) ** m) / np.sqrt(2)
    return M, lmf, rb


def check_reality(C, ls=LS, rtol=1e-10):
    lmf = lm_full(ls); idx = {t: a for a, t in enumerate(lmf)}
    sc = np.abs(C).max(); worst = 0.0
    for (l, m) in lmf:
        for (l2, m2) in lmf:
            d = C[idx[(l, -m)], idx[(l2, -m2)]] - ((-1) ** (m + m2)) * np.conj(C[idx[(l, m)], idx[(l2, m2)]])
            worst = max(worst, abs(d) / sc)
    return worst, worst < rtol


def to_real(C, ls=LS, rtol=1e-10):
    M, lmf, rb = M_matrix(ls)
    Cr = M @ C @ M.conj().T
    im = float(np.abs(Cr.imag).max() / max(np.abs(Cr).max(), 1e-300))
    Cr = Cr.real
    asym = float(np.abs(Cr - Cr.T).max() / max(np.abs(Cr).max(), 1e-300))
    return Cr, dict(imag_rel=im, asym_rel=asym, ok=(im < rtol and asym < rtol))


def twopoint_check(C, Cr, ls=LS, npairs=50, seed=0, rtol=1e-10):
    """Independent mode-placement test: two-point function agreement complex vs real side."""
    rng = np.random.default_rng(seed)
    lmf = lm_full(ls); rb = real_basis_lm(ls)
    th = np.arccos(rng.uniform(-1, 1, 2 * npairs)); ph = rng.uniform(0, 2 * np.pi, 2 * npairs)
    Yc = np.array([[_Ylm(l, m, t, p) for (t, p) in zip(th, ph)] for (l, m) in lmf])   # (21, 2n)
    # real basis functions e_i(n) evaluated at the same points
    E = np.zeros((len(rb), 2 * npairs))
    for i, (l, m, cs) in enumerate(rb):
        Y = np.array([_Ylm(l, m, t, p) for (t, p) in zip(th, ph)])
        E[i] = (Y.real if m == 0 else (np.sqrt(2) * Y.real if cs == 'c' else np.sqrt(2) * Y.imag))
    worst = 0.0
    for k in range(npairs):
        a, b = k, npairs + k
        tc = float(np.real(Yc[:, a].conj() @ C.T @ Yc[:, b]))   # sum_ab C_ab Y_a(n) Y_b*(n') -> real part
        tc2 = float(np.real(np.einsum('a,ab,b->', Yc[:, a], C, np.conj(Yc[:, b]))))
        tr_ = float(E[:, a] @ Cr @ E[:, b])
        sc = max(abs(tc2), np.abs(Cr).max())
        worst = max(worst, abs(tc2 - tr_) / sc)
    return worst, worst < rtol


def frozen_axis_vec():
    return np.array(hp.pix2vec(16, 1134))


def rotation_frames(n_psi=N_PSI):
    d = frozen_axis_vec()
    ref = np.array([0.0, 0.0, 1.0])
    e1_0 = np.cross(ref, d); e1_0 /= np.linalg.norm(e1_0)
    e3_0 = np.cross(e1_0, d)
    R3s = []
    for k in range(n_psi):
        psi = 2 * np.pi * k / n_psi
        e1 = np.cos(psi) * e1_0 + np.sin(psi) * e3_0
        e3 = np.cross(e1, d)
        R3s.append(np.stack([e1, d, e3], axis=1))   # columns: images of x^_body, y^_body, z^_body
    return R3s


def rotation_O(R3, nside_fit=32, lmax_fit=8, tol=3e-6):
    """Orthogonal 21x21: coefficients of rotated real-basis fields. Self-validating."""
    rb = real_basis_lm()
    npix = hp.nside2npix(nside_fit)
    V = np.array(hp.pix2vec(nside_fit, np.arange(npix))).T
    Vb = V @ R3                      # body-frame coordinates of pixel directions (R3^{-1} n = R3^T n)
    thb, phb = hp.vec2ang(Vb)
    O = np.zeros((len(rb), len(rb)))
    almL = {}
    for j, (l, m, cs) in enumerate(rb):
        Y = _Ylm(l, m, thb, phb)
        T = (Y.real if m == 0 else (np.sqrt(2) * Y.real if cs == 'c' else np.sqrt(2) * Y.imag))
        alm = hp.map2alm(T, lmax=lmax_fit, iter=3)
        for i, (li, mi, csi) in enumerate(rb):
            a = alm[hp.Alm.getidx(lmax_fit, li, mi)]
            O[i, j] = (a.real if mi == 0 else (np.sqrt(2) * a.real if csi == 'c' else -np.sqrt(2) * a.imag))
    err = float(np.abs(O.T @ O - np.eye(len(rb))).max())
    return O, err, err < tol


def s_pm_point(C_complex, Bp, Bm, Os, tol_neg_rel=1e-12, tol_psd=1e-10):
    """Per grid point hard gates (rules v0.3 + final review C): reality, real symmetry,
    finiteness, PSD eigenvalues; then psi-set s+-; HARD FAIL on any violation."""
    wr, okr = check_reality(C_complex)
    Cr, info = to_real(C_complex)
    if not (okr and info['ok']):
        raise RuntimeError(f'HARD FAIL: reality/real-symmetry violated (worst={wr:.2e}, {info})')
    if not np.isfinite(Cr).all():
        raise RuntimeError('HARD FAIL: non-finite covariance at grid point')
    _ev = np.linalg.eigvalsh(Cr)
    if _ev.min() < -tol_psd * max(_ev.max(), 1e-300):
        raise RuntimeError(f'HARD FAIL: non-PSD covariance (lmin/lmax={_ev.min()/_ev.max():.2e})')
    sc = max(float(np.trace(Bp) + np.trace(Bm)) * float(np.trace(Cr)) / Cr.shape[0], 1e-300)
    sps, sms = [], []
    for O in Os:
        Crot = O @ Cr @ O.T
        sp = float(np.sum(Bp * Crot)); sm = float(np.sum(Bm * Crot))
        if sp < -tol_neg_rel * sc or sm < -tol_neg_rel * sc:
            raise RuntimeError(f'HARD FAIL: negative s± (implementation error): sp={sp}, sm={sm}, scale={sc}')
        sps.append(max(sp, 0.0)); sms.append(max(sm, 0.0))
    sps = np.array(sps); sms = np.array(sms)
    rpsi = (sps - sms) / np.maximum(sps + sms, 1e-300)
    return dict(splus=float(sps.mean()), sminus=float(sms.mean()),
                splus_min=float(sps.min()), splus_max=float(sps.max()),
                sminus_min=float(sms.min()), sminus_max=float(sms.max()),
                rho_psi_mean=float(rpsi.mean()), rho_psi_min=float(rpsi.min()),
                rho_psi_max=float(rpsi.max()), frac_rho_psi_neg=float(np.mean(rpsi < 0)),
                reality_worst=wr, real_ok=bool(okr and info['ok']))


def classify_rho(rho, sig_sys, rho_num=RHO_NUM):
    thr = max(3.0 * sig_sys, rho_num)
    if rho < -thr:
        return 'neg'
    if rho > thr:
        return 'pos'
    return 'unc'


def g2max_of(sminus_inf, dSmax, small_rel_scale):
    if sminus_inf <= 0:
        return np.inf, 'not_constrained_by_Sminus_budget'
    flag = 'numerical_small_sminus' if sminus_inf < SMALL_SM_REL * small_rel_scale else ''
    return dSmax / sminus_inf, flag


def direct_complex_check(C, Cr, Bp, Bm, rtol=1e-10):
    """Rules v0.3 Sec.3.1 test 4 (literal form): complex-basis quadratic expectation
    tr((M^H B M) C) must equal tr(B C_real) for both B+ and B-."""
    M, _, _ = M_matrix()
    out = {}
    for name, B in [('Bp', Bp), ('Bm', Bm)]:
        tc = float(np.real(np.trace((M.conj().T @ B @ M) @ C)))
        tr_ = float(np.trace(B @ Cr))
        out[name] = abs(tc - tr_) / max(abs(tr_), 1e-300)
    return out, all(v < rtol for v in out.values())
