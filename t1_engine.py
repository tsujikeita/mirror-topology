"""t1_engine v1.6 (2026-08-30b): audited low-l predictive engine for compact-flat topologies.

v1.1 (pre-run re-audit, 4 BLOCKERs fixed):
  B1: O_axis is now labelled a NUMERICAL HARMONIC ROTATION and is validated by DIRECT-GEOMETRY
      tests (reflection p'=p-2(n.p)n and half-turn p'=2(n.p)n-p compared pointwise against the
      operator action on random band-limited skies) plus projector identities
      (P^2=P, PePo=0, Pe+Po=I, P(n)=P(-n)); only after these hard tests do we call it
      effectively exact for l<=4.
  B2: the empty round-trip placeholder is DELETED and replaced by real tests:
      T1-A2 complex<->real round trip x -> healpy alm -> x' (max|x-x'| hard assert) and
      T1-A3 two-point equality (reconstruct complex covariance M^H C_real M == input).
  B3/B4 live in the notebook (covariance binding, engine path); engine adds split hashes
      support and an eigen-based sampler (Cholesky+jitter retired): significant negative
      eigenvalue -> FAIL; rounding-level negatives clipped to 0; provenance gets
      lambda_min_raw / clip / effective rank.
Statistic convention: S+- = (1/4pi) * integral ((T +- T o R)/2)^2 dOmega; in an orthonormal
real basis S+ + S- = sum_i x_i^2 / (4pi), axis-independent.
v1.5 (first contact with real CMBtopology covariances): the exact-symmetry tolerances
inherited from t2b2 (rtol 1e-10, appropriate for analytically constructed covariances) are
far tighter than the numerical-integration accuracy of CMBtopology's covariance pipeline
(~1e-7 relative; observed 5.0e-8 on E7). Instead of loosening a pass/fail threshold, the
covariance is now explicitly PROJECTED onto the subspace that satisfies the exact symmetries
required by the theory (Hermiticity and the reality condition
C_{l,-m;l',-m'} = (-1)^(m+m') conj(C_{lm;l'm'})); the size of the removed component is
recorded and capped, the post-projection residual is required to be at machine precision, and the raw
violation is hard-capped at a calibration ceiling frozen after the first numerical-covariance
contact and before any inspection of scientific outputs. The impact of the projection on the
science outputs E[S+-] is measured directly and capped as well.
v1.3: no functional change from v1.2 (version bump for the v1.3 audit set; the isotropic
reference C_l convention fix lives in the notebook: engine_selftest takes CL as an argument
and is convention-agnostic).
v1.2: scan direction grid now removes the antipodal duplicates completely (equatorial
z=0 pixels previously appeared as both n and -n although P(n)=P(-n)); exactly one axis is
kept per +-pair via the HEALPix antipode rule pixel_id < antipode_id (verified: keep count
= npix/2, no self-antipodal pixels at nside 4/8).
Role: retroactively audited low-l FULL-SKY theoretical predictive-engine validation.
NOT a direct observational model comparison (that is Step 1: same mask/preprocessing/frozen
statistic as the observation).
"""
import numpy as np
import healpy as hp
import hashlib
import t2b2_bridge as br

LS = (2, 3, 4)
NDIM = 21
# Calibration ceiling for RAW symmetry violations of numerically integrated covariances.
# Frozen after the first numerical-covariance validation failure (reality_raw = 5.01e-8 on the
# first E7 point) and BEFORE any inspection of scientific T1 outputs. It is a corruption
# detector, not a claim about typical pipeline accuracy.
RAW_SYMMETRY_CEILING = 1e-5
# Frozen ceilings on the SIZE of the projection (the real safety gate on the correction).
CORRECTION_MAX_CEILING = 1e-6
CORRECTION_FRO_CEILING = 1e-6
# Machine-precision tolerance for the algebraic identities (not a sensitivity threshold).
IDENTITY_TOL = 1e-12
FOURPI = 4.0 * np.pi


# ---------- basis / unitarity ----------
def M_unitary_check(tol=1e-12):
    M, lmf, rb = br.M_matrix(LS)
    err = float(np.abs(M @ M.conj().T - np.eye(NDIM)).max())
    return err, err < tol


def basis_matrix(pts):
    """(npts, 21): real orthonormal basis functions evaluated at unit vectors pts."""
    rb = br.real_basis_lm(LS)
    th, ph = hp.vec2ang(np.asarray(pts, float))
    B = np.empty((len(th), NDIM))
    for j, (l, m, cs) in enumerate(rb):
        Y = br._Ylm(l, m, th, ph)
        B[:, j] = (Y.real if m == 0 else (np.sqrt(2) * Y.real if cs == 'c'
                                          else np.sqrt(2) * Y.imag))
    return B


# ---------- axis frame and parity operators (numerical harmonic rotation) ----------
def frame_to_axis(nvec):
    n = np.asarray(nvec, float); n = n / np.linalg.norm(n)
    ref = np.array([1.0, 0.0, 0.0]) if abs(n[2]) > 0.9 else np.array([0.0, 0.0, 1.0])
    e1 = np.cross(ref, n); e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    return np.stack([e1, e2, n], axis=1)


def O_axis(nvec, nside_fit=32, lmax_fit=8, tol=3e-6):
    """Orthogonal 21x21 numerical harmonic rotation: x_frame = O x_galactic, frame z || nvec.
    Orthogonality is asserted here; geometric correctness is established by
    validate_operator_geometry (direct-coordinate hard tests)."""
    R3 = frame_to_axis(nvec)
    rb = br.real_basis_lm(LS)
    npix = hp.nside2npix(nside_fit)
    V = np.array(hp.pix2vec(nside_fit, np.arange(npix))).T
    Vg = V @ R3.T
    th, ph = hp.vec2ang(Vg)
    O = np.zeros((NDIM, NDIM))
    for j, (l, m, cs) in enumerate(rb):
        Y = br._Ylm(l, m, th, ph)
        T = (Y.real if m == 0 else (np.sqrt(2) * Y.real if cs == 'c' else np.sqrt(2) * Y.imag))
        alm = hp.map2alm(T, lmax=lmax_fit, iter=3)
        for i, (li, mi, csi) in enumerate(rb):
            a = alm[hp.Alm.getidx(lmax_fit, li, mi)]
            O[i, j] = (a.real if mi == 0 else (np.sqrt(2) * a.real if csi == 'c'
                                               else -np.sqrt(2) * a.imag))
    err = float(np.abs(O.T @ O - np.eye(NDIM)).max())
    if err >= tol:
        raise RuntimeError(f'O_axis orthogonality FAIL: {err:.2e}')
    return O


def parity_signs(op):
    rb = br.real_basis_lm(LS)
    if op == 'refl':
        return np.array([(-1) ** (l + m) for (l, m, cs) in rb], float)
    if op == 'halfturn':
        return np.array([(-1) ** m for (l, m, cs) in rb], float)
    raise ValueError(op)


def operator_matrix(nvec, op):
    """21x21 galactic-basis matrix U with (U x) the coefficients of T o R."""
    O = O_axis(nvec)
    return O.T @ np.diag(parity_signs(op)) @ O


def projectors(nvec, op):
    O = O_axis(nvec)
    s = parity_signs(op)
    De = np.diag((s > 0).astype(float)); Do = np.diag((s < 0).astype(float))
    return O.T @ De @ O, O.T @ Do @ O


def exp_S(C_real, nvec, op):
    Pe, Po = projectors(nvec, op)
    return float(np.sum(Pe * C_real) / FOURPI), float(np.sum(Po * C_real) / FOURPI)


# ---------- direct-geometry validation (BLOCKER 1) ----------
def reflect_pts(pts, n):
    pts = np.asarray(pts, float); n = np.asarray(n, float) / np.linalg.norm(n)
    return pts - 2.0 * (pts @ n)[:, None] * n[None, :]


def halfturn_pts(pts, n):
    pts = np.asarray(pts, float); n = np.asarray(n, float) / np.linalg.norm(n)
    return 2.0 * (pts @ n)[:, None] * n[None, :] - pts


def validate_operator_geometry(nvec, op, nsky=4, npts=400, seed=0, tol=1e-4):
    """Direct-coordinate hard test: for random band-limited skies x, compare
    T_op(p) = (U x) . B(p)  against  T(R p) = x . B(R p)  pointwise."""
    rng = np.random.default_rng(seed)
    U = operator_matrix(nvec, op)
    pts = rng.standard_normal((npts, 3)); pts /= np.linalg.norm(pts, axis=1)[:, None]
    Rp = reflect_pts(pts, nvec) if op == 'refl' else halfturn_pts(pts, nvec)
    B_p, B_Rp = basis_matrix(pts), basis_matrix(Rp)
    worst = 0.0
    for _ in range(nsky):
        x = rng.standard_normal(NDIM)
        T_op = B_p @ (U @ x)
        T_dir = B_Rp @ x
        scale = max(float(np.abs(T_dir).max()), 1e-30)
        worst = max(worst, float(np.abs(T_op - T_dir).max() / scale))
    if worst >= tol:
        raise RuntimeError(f'direct-geometry FAIL ({op}): rel err {worst:.2e}')
    return worst


def projector_identity_check(nvec, op, tol=1e-4):
    Pe, Po = projectors(nvec, op)
    Pe2, Po2 = projectors(-np.asarray(nvec, float), op)
    errs = dict(idem_e=float(np.abs(Pe @ Pe - Pe).max()),
                idem_o=float(np.abs(Po @ Po - Po).max()),
                cross=float(np.abs(Pe @ Po).max()),
                complete=float(np.abs(Pe + Po - np.eye(NDIM)).max()),
                antipodal=float(max(np.abs(Pe - Pe2).max(), np.abs(Po - Po2).max())))
    ok = all(v < tol for v in errs.values())
    if not ok:
        raise RuntimeError(f'projector identities FAIL: {errs}')
    return errs


# ---------- eigen-based sampler (review §9) ----------
def eigen_factor(C_real, neg_tol_rel=1e-8):
    """(F, info): F with F F^T = C (negatives clipped at rounding level); FAIL if a
    significant negative eigenvalue exists."""
    lam, V = np.linalg.eigh(C_real)
    lmax = max(float(lam.max()), 1e-300)
    lam_min_raw = float(lam.min())
    if lam_min_raw < -neg_tol_rel * lmax:
        raise RuntimeError(f'covariance not PSD: lam_min/lam_max={lam_min_raw/lmax:.2e}')
    lam_cl = np.clip(lam, 0.0, None)
    info = dict(lambda_min_raw=lam_min_raw, lambda_max=lmax,
                lambda_clip_max=float((lam_cl - lam).max()),
                effective_rank=int((lam_cl > 1e-12 * lmax).sum()))
    return V * np.sqrt(lam_cl)[None, :], info


def sample_real(C_real, nreal, seed=0, return_info=False):
    """x ~ N(0, C_real) via eigen factor. Deterministic single-generator seed recipe."""
    F, info = eigen_factor(C_real)
    rng = np.random.default_rng(seed)
    x = rng.standard_normal((nreal, NDIM)) @ F.T
    return (x, info) if return_info else x


# ---------- healpy conversion and round trip (BLOCKER 2) ----------
def x_to_healpy_alm(x, lmax=None):
    lmax = lmax or max(LS)
    M, lmf, rb = br.M_matrix(LS)
    a_full = x @ np.conj(M)                       # a = M^H x
    idx = {t: k for k, t in enumerate(lmf)}
    out = np.zeros((x.shape[0], hp.Alm.getsize(lmax)), complex)
    for (l, m) in lmf:
        if m >= 0:
            out[:, hp.Alm.getidx(lmax, l, m)] = a_full[:, idx[(l, m)]]
    return out


def x_from_healpy_alm(alm, lmax=None, imag_tol=1e-10):
    """Inverse: healpy m>=0 alm -> full-m (reality) -> x = M a. Hard-asserts realness."""
    lmax = lmax or max(LS)
    M, lmf, rb = br.M_matrix(LS)
    idx = {t: k for k, t in enumerate(lmf)}
    a_full = np.zeros((alm.shape[0], NDIM), complex)
    for (l, m) in lmf:
        if m >= 0:
            a_full[:, idx[(l, m)]] = alm[:, hp.Alm.getidx(lmax, l, m)]
        else:
            a_full[:, idx[(l, m)]] = ((-1) ** m) * np.conj(alm[:, hp.Alm.getidx(lmax, l, -m)])
    x = a_full @ M.T
    scale = max(float(np.abs(x).max()), 1e-30)
    im = float(np.abs(x.imag).max() / scale)
    if im >= imag_tol:
        raise RuntimeError(f'round-trip realness FAIL: {im:.2e}')
    return x.real


def roundtrip_check(C_real, nreal=64, seed=5):
    x = sample_real(C_real, nreal, seed=seed)
    x2 = x_from_healpy_alm(x_to_healpy_alm(x))
    return float(np.abs(x - x2).max() / max(np.abs(x).max(), 1e-30))


def complex_real_twopoint_check(Mx, C_real):
    """Reconstruct the complex covariance from the real one: M^H C_real M == Mx."""
    M, lmf, rb = br.M_matrix(LS)
    Mx_rt = M.conj().T @ C_real.astype(complex) @ M
    return float(np.abs(Mx_rt - Mx).max() / max(np.abs(Mx).max(), 1e-30))


# ---------- per-axis statistics and scan ----------
def stats_at_axis(x, nvec, op):
    Pe, Po = projectors(nvec, op)
    Sp = np.einsum('ri,ij,rj->r', x, Pe, x, optimize=True) / FOURPI
    Sm = np.einsum('ri,ij,rj->r', x, Po, x, optimize=True) / FOURPI
    A = Sp - Sm
    return Sp, Sm, A, A / (Sp + Sm)


def scan_projectors(scan_nside=8, op='refl'):
    """Even-projector stack over a complete antipodal-deduplicated axis set: exactly one of
    each +-n pair is kept (pixel_id < antipode_id), so len(Vdirs) == npix/2 unique axes."""
    npix = hp.nside2npix(scan_nside)
    V = np.array(hp.pix2vec(scan_nside, np.arange(npix))).T
    ant = hp.vec2pix(scan_nside, -V[:, 0], -V[:, 1], -V[:, 2])
    keep = np.where(np.arange(npix) < ant)[0]
    assert len(keep) == npix // 2, (len(keep), npix)
    Pes = np.empty((len(keep), NDIM, NDIM))
    for k, p in enumerate(keep):
        Pes[k], _ = projectors(V[p], op)
    return V[keep], Pes


def scan_argmin_Splus(x, Vdirs, Pes):
    """n* = argmin_n S+(n) per realization; (S+,S-,A,rho) AT n*; min S- separate diagnostic.
    NOTE (review 2026-08-27 §12): because S+ + S- is axis-independent, S- at n* is
    scan-ELEVATED by construction; comparison with the observation requires applying the
    same scan rule to the observation side (Step 1), not this raw number."""
    tot = np.einsum('ri,ri->r', x, x) / FOURPI
    Sp_all = np.einsum('ri,kij,rj->rk', x, Pes, x, optimize=True) / FOURPI
    kstar = np.argmin(Sp_all, axis=1)
    Sp = Sp_all[np.arange(len(x)), kstar]
    Sm = tot - Sp
    ksm = np.argmax(Sp_all, axis=1)
    return dict(argmin_Splus=Vdirs[kstar], Splus_at=Sp, Sminus_at=Sm,
                A_at=Sp - Sm, rho_at=(Sp - Sm) / tot,
                min_Sminus=tot - Sp_all[np.arange(len(x)), ksm], argmin_Sminus=Vdirs[ksm])


# ---------- covariance intake ----------
def enforce_symmetries(Mx, ls=LS):
    """Project a numerically computed covariance onto the physically exact subspace.

    Two exact symmetries hold analytically for a real Gaussian temperature field:
      (a) Hermiticity  C = C^dagger
      (b) reality      C_{l,-m; l',-m'} = (-1)^(m+m') conj(C_{lm; l'm'})
    A numerically integrated covariance satisfies them only to integration accuracy. The
    orthogonal projection is the average of C with its symmetry image; the removed component
    is returned as a diagnostic (it is NOT discarded silently).
    """
    lmf = br.lm_full(ls)
    idx = {t: a for a, t in enumerate(lmf)}
    scale = max(float(np.abs(Mx).max()), 1e-300)
    C = 0.5 * (Mx + Mx.conj().T)                       # (a)
    R = np.empty_like(C)
    for (l, m) in lmf:
        for (l2, m2) in lmf:
            R[idx[(l, m)], idx[(l2, m2)]] = ((-1) ** (m + m2)) * np.conj(
                C[idx[(l, -m)], idx[(l2, -m2)]])
    Csym = 0.5 * (C + R)                               # (b)
    info = dict(herm_raw=float(np.abs(Mx - Mx.conj().T).max() / scale),
                reality_raw=float(br.check_reality(Mx, ls)[0]),
                herm_post=float(np.abs(Csym - Csym.conj().T).max() / scale),
                reality_post=float(br.check_reality(Csym, ls)[0]),
                correction_max_rel=float(np.abs(Csym - Mx).max() / scale),
                correction_fro_rel=float(np.linalg.norm(Csym - Mx)
                                         / max(np.linalg.norm(Mx), 1e-300)))
    return Csym, info


def load_cov_full(path, lmax=4):
    """CMBtopology full-m complex covariance + validation. Returns (Mx, C_real, meta) with
    split hashes: cov_file_sha256 (file bytes) and cov_array_sha256 (array data)."""
    with open(path, 'rb') as fh:
        fbytes = fh.read()
    Mx = np.load(path)
    lm = [(l, m) for l in range(2, lmax + 1) for m in range(-l, l + 1)]
    assert Mx.shape == (len(lm), len(lm)), (Mx.shape, len(lm))
    Csym, sym = enforce_symmetries(Mx, LS)
    if sym['herm_raw'] > RAW_SYMMETRY_CEILING or sym['reality_raw'] > RAW_SYMMETRY_CEILING:
        raise RuntimeError('raw symmetry violation above frozen calibration ceiling '
                           f'{RAW_SYMMETRY_CEILING:.0e}: {sym}')
    if sym['herm_post'] > IDENTITY_TOL or sym['reality_post'] > IDENTITY_TOL:
        raise RuntimeError(f'projection did not restore exact symmetries: {sym}')
    if (sym['correction_max_rel'] > CORRECTION_MAX_CEILING
            or sym['correction_fro_rel'] > CORRECTION_FRO_CEILING):
        raise RuntimeError('symmetry correction above frozen ceiling '
                           f'({CORRECTION_MAX_CEILING:.0e}/{CORRECTION_FRO_CEILING:.0e}): {sym}')
    qmi = quadratic_mean_identity(Mx, Csym)
    if qmi > IDENTITY_TOL:
        raise RuntimeError(f'quadratic-mean identity FAIL: {qmi:.2e}')
    Cr, info = br.to_real(Csym)
    if not info['ok']:
        raise RuntimeError(f'real transform FAIL: {info}')
    _, eig_info = eigen_factor(Cr)                      # PSD hard gate
    tp = complex_real_twopoint_check(Csym, Cr)
    if tp > 1e-10:
        raise RuntimeError(f'two-point complex vs real FAIL: {tp:.2e}')
    return Csym, Cr, dict(
        symmetry=sym, quadratic_mean_identity=qmi, twopoint=tp, eig=eig_info,
        real_transform=info,
        cov_file_sha256=hashlib.sha256(fbytes).hexdigest(),
        cov_array_sha256=hashlib.sha256(Mx.tobytes()).hexdigest(),
        cov_projected_array_sha256=hashlib.sha256(
            np.ascontiguousarray(Csym).tobytes()).hexdigest(),
        real_cov_projected_sha256=hashlib.sha256(
            np.ascontiguousarray(Cr).tobytes()).hexdigest())


def load_cov_full_from_matrix(Mx, lmax=4):
    wr, okr = br.check_reality(Mx)
    assert okr, wr
    Cr, info = br.to_real(Mx)
    assert info['ok']
    return Mx, Cr, dict(reality=wr)


def quadratic_mean_identity(Mx_raw, Csym):
    """Verify C_real_projected == (C_real_raw + C_real_raw^T)/2 (relative max error).

    Because E[Q] = tr(P C_real) for any real symmetric P, this identity is exactly the
    statement that the projection preserves the mean of EVERY real symmetric quadratic
    statistic - for every reflection and half-turn projector, at every axis, without having
    to test them one by one.
    """
    M = br.M_matrix(LS)[0]
    Cr_raw = np.real(M @ Mx_raw @ M.conj().T)
    Cr_sym, _ = br.to_real(Csym)
    target = 0.5 * (Cr_raw + Cr_raw.T)
    return float(np.abs(Cr_sym - target).max() / max(np.abs(Cr_sym).max(), 1e-300))


def ESpm_identity_check(Mx, Csym, axes, ops=('refl', 'halfturn')):
    """IMPLEMENTATION CONSISTENCY ONLY (not a sensitivity test): E[S+-] before/after the
    projection must agree to machine precision, which follows algebraically from
    quadratic_mean_identity. A non-zero result signals a coding error, not a physical effect."""
    M = br.M_matrix(LS)[0]
    Cr_raw = np.real(M @ Mx @ M.conj().T)
    Cr_sym, _ = br.to_real(Csym)
    worst = 0.0
    for nvec in axes:
        for op in ops:
            a = exp_S(Cr_raw, nvec, op)
            b = exp_S(Cr_sym, nvec, op)
            for u, v in zip(a, b):
                worst = max(worst, abs(u - v) / max(abs(v), 1e-300))
    return float(worst)


# ---------- audit evidence: v0.3 sampler, verbatim ----------
def sample_alms_v03_LEGACY(Mx, lm, nreal, seed0=0, jitter=1e-9):
    """VERBATIM copy of the superseded v0.3 sampler (m=0 reality bug). Kept ONLY to quantify
    the legacy bias in the difference table. Never used for results."""
    lmax = max(l for l, _ in lm)
    A = np.linalg.cholesky(Mx + jitter * np.abs(np.diag(Mx)).max() * np.eye(len(lm)))
    out = np.zeros((nreal, hp.Alm.getsize(lmax)), complex)
    for r in range(nreal):
        rng = np.random.default_rng(seed0 + r)
        z = (rng.normal(size=len(lm)) + 1j * rng.normal(size=len(lm))) / np.sqrt(2)
        v = A @ z
        for i, (l, m) in enumerate(lm):
            if m >= 0:
                out[r, hp.Alm.getidx(lmax, l, m)] += v[i] / np.sqrt(2 if m > 0 else 1)
            else:
                out[r, hp.Alm.getidx(lmax, l, -m)] += ((-1) ** m) * np.conj(v[i]) / np.sqrt(2)
    return out


# ---------- named test battery (review §5 / §17) ----------
def engine_selftest(CL, nmc=40000, seed=11):
    """T1-A1..A6 sampler/basis tests + T1-B1..B3 operator geometry tests. (report, ok)."""
    rep = {}
    err, okA1 = M_unitary_check(); rep['A1_M_unitarity'] = err
    lmf = br.lm_full(LS)
    C_iso_c = np.diag(np.array([CL[l] for (l, m) in lmf]).astype(complex))
    _, C_iso, _ = load_cov_full_from_matrix(C_iso_c)
    rep['A2_roundtrip'] = roundtrip_check(C_iso)
    rep['A3_twopoint'] = complex_real_twopoint_check(C_iso_c, C_iso)
    x = sample_real(C_iso, nmc, seed=seed)
    rep['A4_emp_cov_rel'] = float(np.abs(x.T @ x / nmc - C_iso).max() / np.abs(C_iso).max())
    rng = np.random.default_rng(seed + 1)
    worst = 0.0
    for _ in range(3):
        n = rng.standard_normal(3); n /= np.linalg.norm(n)
        for op in ('refl', 'halfturn'):
            Ep, Em = exp_S(C_iso, n, op)
            Sp, Sm, _, _ = stats_at_axis(x, n, op)
            worst = max(worst,
                        abs(Sp.mean() - Ep) / max(3 * Sp.std() / np.sqrt(nmc), 1e-30),
                        abs(Sm.mean() - Em) / max(3 * Sm.std() / np.sqrt(nmc), 1e-30))
    rep['A5_trBC_vs_MC_over3sigma'] = float(worst)
    rep['A6_seed_repro'] = bool(np.array_equal(sample_real(C_iso, 5, seed=7),
                                               sample_real(C_iso, 5, seed=7)))
    g_worst = {'refl': 0.0, 'halfturn': 0.0}
    pid_worst = 0.0
    for t in range(3):
        n = rng.standard_normal(3); n /= np.linalg.norm(n)
        for op in ('refl', 'halfturn'):
            g_worst[op] = max(g_worst[op], validate_operator_geometry(n, op, seed=100 + t))
            pid_worst = max(pid_worst, max(projector_identity_check(n, op).values()))
    rep['B1_geom_refl'] = g_worst['refl']
    rep['B2_geom_halfturn'] = g_worst['halfturn']
    rep['B3_projector_ids'] = pid_worst
    vals = []
    for _ in range(6):
        n = rng.standard_normal(3); n /= np.linalg.norm(n)
        vals.append(exp_S(C_iso, n, 'refl'))
    vals = np.array(vals)
    rep['iso_orientation_spread_rel'] = float(np.ptp(vals, axis=0).max() / vals.mean())
    ok = (okA1 and rep['A2_roundtrip'] < 1e-9 and rep['A3_twopoint'] < 1e-10
          and rep['A4_emp_cov_rel'] < 0.05 and rep['A5_trBC_vs_MC_over3sigma'] < 1.0
          and rep['A6_seed_repro'] and rep['B1_geom_refl'] < 1e-4
          and rep['B2_geom_halfturn'] < 1e-4 and rep['B3_projector_ids'] < 1e-4
          and rep['iso_orientation_spread_rel'] < 1e-4)
    return rep, bool(ok)
