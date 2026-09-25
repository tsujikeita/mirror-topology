# ---- 2. D(M)（A9 と同一の求積構成）＋ A11 で使う全 M の gate ----
LM = br.lm_full(); M21 = br.M_matrix()[0]; RB = br.real_basis_lm()
_NT = _NP = 2 * LMAX + 2
_xg, _wg = np.polynomial.legendre.leggauss(_NT); _th = np.arccos(_xg); _ph = 2 * np.pi * np.arange(_NP) / _NP
TH, PH = np.meshgrid(_th, _ph, indexing='ij'); WQ = (np.repeat(_wg[:, None], _NP, axis=1) * (2 * np.pi / _NP)).ravel()
DIRS = np.column_stack([np.sin(TH).ravel() * np.cos(PH).ravel(), np.sin(TH).ravel() * np.sin(PH).ravel(), np.cos(TH).ravel()])
def asha(a): return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def Yc_at(dirs):
    th, ph = hp.vec2ang(dirs); return np.array([sph_harm_y(l, m, th, ph) for (l, m) in LM])
def Ymat(dirs): return (M21.conj() @ Yc_at(dirs)).real.T
YQ = Ymat(DIRS)
def D_of(Mm): return (YQ * WQ[:, None]).T @ Ymat(DIRS @ Mm)
GATES['G_quadrature_orthonormal'] = bool(np.abs((YQ * WQ[:, None]).T @ YQ - np.eye(21)).max() < 1e-12)
rng = np.random.default_rng(20260907); dirs_t = rng.standard_normal((100, 3)); dirs_t /= np.linalg.norm(dirs_t, axis=1, keepdims=True); th_t, ph_t = hp.vec2ang(dirs_t)
E_explicit = np.column_stack([(sph_harm_y(l, m, th_t, ph_t).real if (cs == 'c' and m == 0) else np.sqrt(2) * sph_harm_y(l, m, th_t, ph_t).real if cs == 'c' else np.sqrt(2) * sph_harm_y(l, m, th_t, ph_t).imag) for (l, m, cs) in RB])
GATES['G_real_basis_bridge'] = bool(np.abs(Ymat(dirs_t) - E_explicit).max() < 1e-12)
I3 = np.eye(3); MA = np.diag([1., -1., 1.]); MB = np.diag([-1., 1., 1.]); RZ = np.diag([-1., -1., 1.])
from scipy.spatial.transform import Rotation
Rr1, Rr2 = Rotation.random(rng=rng).as_matrix(), Rotation.random(rng=rng).as_matrix()
worst_orth = worst_geom = 0.0
for Mm in [MA, MB, MA @ MB, RZ, Rr1, Rr2]:
    D = D_of(Mm); worst_orth = max(worst_orth, np.abs(D.T @ D - np.eye(21)).max())
    x = rng.standard_normal(21); a = M21.conj().T @ x
    worst_geom = max(worst_geom, np.abs((Yc_at(dirs_t).T @ (M21.conj().T @ (D @ x))).real - (Yc_at(dirs_t @ Mm).T @ a).real).max() / np.abs((Yc_at(dirs_t @ Mm).T @ a).real).max())
hom = max(np.abs(D_of(MA @ MB) - D_of(MA) @ D_of(MB)).max(), np.abs(D_of(Rr1 @ Rr2) - D_of(Rr1) @ D_of(Rr2)).max(), np.abs(D_of(MA @ Rr1) - D_of(MA) @ D_of(Rr1)).max())
Dy_th = np.diag([(-1.0 if cs == 's' else 1.0) for (l, m, cs) in RB]); Dz_th = np.diag([(-1.0) ** (l + m) for (l, m, cs) in RB])
GATES['G_D_orthogonal_all_used'] = bool(worst_orth < 1e-10); GATES['G_D_direct_geometry_complex_path'] = bool(worst_geom < 1e-10); GATES['G_D_homomorphism'] = bool(hom < 1e-10)
GATES['G_reflection_D_analytic'] = bool(np.abs(D_of(MA) - Dy_th).max() < 1e-12 and np.abs(D_of(np.diag([1., 1., -1.])) - Dz_th).max() < 1e-12)
assert all(GATES[k] for k in ['G_quadrature_orthonormal', 'G_real_basis_bridge', 'G_D_orthogonal_all_used', 'G_D_direct_geometry_complex_path', 'G_D_homomorphism', 'G_reflection_D_analytic']), GATES
DIAG['representation'] = dict(worst_orthogonality=float(worst_orth), worst_direct_geometry=float(worst_geom), worst_homomorphism=float(hom), quadrature_nodes_sha256=asha(DIRS), quadrature_weights_sha256=asha(WQ), M21_sha256=asha(M21),
                              LM_sha256=hashlib.sha256(json.dumps(LM).encode()).hexdigest(), RB_sha256=hashlib.sha256(json.dumps(RB).encode()).hexdigest())
print('D(M) gates OK')