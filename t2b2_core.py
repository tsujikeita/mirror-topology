"""T2b-2 core v0.3: E7 twisted eigenmodes (full Bieberbach BC), covariances, quadratic sky projection.
Units: lengths in chi_* (comoving radius of LSS) = 1.
v0.2 changes (2026-08-24, session 2):
  - integer lattice coordinates for all wavevectors (exact dedup keys, no float rounding)
  - memory-lean two-pass pair engine sized for production grids
  - sky_cov_q_multi: several transfer functions share one mode/pair/unique-K construction
  - re-verified: V1/V3/V4/V5/V7 battery + regression against session-1 CSV
v0.3 change (2026-08-26): composite K=0 modes explicitly zeroed for l>0 (full-transfer interp
  would otherwise clamp to the q-grid minimum; SW was safe since j_l(0)=0 for l>0).

E7 (rectangular lattice) generators:
  g_A: x -> M_A x + T_A,  M_A = diag(1,-1,1), T_A = (LAx, LAy, 0);  g_A^2 = t_(2LAx,0,0)
  t1 : y -> y + L1y ; t2 : z -> z + L2z ;  H1 = Z(g_A) + Z(t2) + Z2(t1)
Real characters sigma=(sA,s1,s2). Twisted dual lattice:
  kx = pi*nx/LAx ; ky = 2pi(my+ay)/L1y, ay=(1-s1)/4 ; kz = 2pi(mz+az)/L2z, az=(1-s2)/4.
ky>0 orbit-pair: psi = [e^{ik.x} + sA e^{-i(Mk).T_A} e^{i(Mk).x}]/sqrt2 (e^{2i kx LAx}=1 auto).
ky=0 (s1=+1 only): single wave, parity selection (-1)^nx = sA.
P(k) = k^-3 (scale-invariant baseline; amplitude irrelevant for signs and rho).
Integer coords: mode wave = ints (nx, my, mz) with ky = sy*(my + twy/2), twy=(1-s1)/2 in {0,1}.
Composite (quadratic) wave = ints summed; K_y = sy*(iy + twy) etc. (untwisted lattice).
"""
import numpy as np
from scipy.special import spherical_jn
try:
    from scipy.special import sph_harm_y
    def Ylm(l, m, theta_pol, phi_az):
        return sph_harm_y(l, m, theta_pol, phi_az)
except ImportError:
    from scipy.special import sph_harm
    def Ylm(l, m, theta_pol, phi_az):
        return sph_harm(m, l, phi_az, theta_pol)

TOL = 1e-9

class E7Twisted:
    def __init__(self, LAx, L1y, L2z, LAy, sA, s1, s2, kcut):
        self.p = dict(LAx=LAx, L1y=L1y, L2z=L2z, LAy=LAy, sA=sA, s1=s1, s2=s2, kcut=kcut)
        self.TA = np.array([LAx, LAy, 0.0])
        self.twy = 0 if s1 == 1 else 1
        self.twz = 0 if s2 == 1 else 1
        self.sx = np.pi / LAx; self.sy = 2 * np.pi / L1y; self.sz = 2 * np.pi / L2z
        self._build_reps()
        self._realify()

    # ---- integer <-> float wavevectors (mode lattice: y-shift twy/2, z-shift twz/2) ----
    def _kfloat(self, iQ):
        K = np.empty(np.shape(iQ), float)
        iQ = np.asarray(iQ)
        K[..., 0] = self.sx * iQ[..., 0]
        K[..., 1] = self.sy * (iQ[..., 1] + 0.5 * self.twy)
        K[..., 2] = self.sz * (iQ[..., 2] + 0.5 * self.twz)
        return K

    def _ineg(self, t):    # integer rep of -k on the mode lattice
        return (-t[0], -t[1] - self.twy, -t[2] - self.twz)

    def _imir(self, t):    # integer rep of M_A k (flip y)
        return (t[0], -t[1] - self.twy, t[2])

    # ---------- twisted-mode construction ----------
    def _build_reps(self):
        kcut, sA = self.p['kcut'], self.p['sA']
        nxm = int(np.floor(kcut / self.sx)) + 1
        nym = int(np.floor(kcut / self.sy)) + 2
        nzm = int(np.floor(kcut / self.sz)) + 2
        reps = {}
        for nx in range(-nxm, nxm + 1):
            kx = self.sx * nx
            for my in range(-nym, nym + 1):
                ky = self.sy * (my + 0.5 * self.twy)
                if ky < -TOL:
                    continue                      # orbit representative: ky>0 or ky==0
                for mz in range(-nzm, nzm + 1):
                    kz = self.sz * (mz + 0.5 * self.twz)
                    kn = np.sqrt(kx * kx + ky * ky + kz * kz)
                    if kn > kcut or kn < TOL:
                        continue
                    t = (nx, my, mz)
                    if abs(ky) < TOL:             # single-wave sector (needs s1=+1)
                        if (-1) ** nx != sA:
                            continue              # parity selection e^{i kx LAx} = sA
                        reps[t] = dict(waves=[(t, 1.0 + 0j)], kmag=kn, kind='s')
                    else:                         # orbit pair {k, M_A k}
                        tm = self._imir(t)
                        Mk = self._kfloat(np.array(tm, float)[None, :])[0]
                        c2 = sA * np.exp(-1j * (Mk @ self.TA))
                        reps[t] = dict(waves=[(t, 1 / np.sqrt(2) + 0j), (tm, c2 / np.sqrt(2))],
                                       kmag=kn, kind='p')
        self.reps = reps

    def _closed(self, waves, coef_map):
        """conjugate-closed dict {int3: coeff} for real combo a*psi + b*conj(psi)."""
        a, b = coef_map
        d = {}
        for t, c in waves:
            for tt, cc in ((t, a * c), (self._ineg(t), b * np.conj(c))):
                d[tt] = d.get(tt, 0j) + cc
        return d

    def _realify(self):
        consumed, modes = set(), []
        for key, rep in self.reps.items():
            if key in consumed:
                continue
            nx, my, mz = key
            pkey = self._imir(self._ineg(key))    # conjugate orbit representative (ky>=0)
            if pkey == key:
                # self-conjugate orbit spans ONE real dimension when psi* prop psi:
                # Gram-Schmidt over Re/Im candidates keeps only independent ones.
                kept = []
                for cm in [(0.5, 0.5), (-0.5j, 0.5j)]:
                    d = self._closed(rep['waves'], cm)
                    for kd in kept:
                        ip = sum(v * np.conj(kd[q]) for q, v in d.items() if q in kd)
                        for q in d:
                            if q in kd:
                                d[q] -= ip * kd[q]
                    n2 = sum(abs(v) ** 2 for v in d.values())
                    if n2 > 1e-10:
                        s = 1 / np.sqrt(n2)
                        dn = {q: v * s for q, v in d.items()}
                        kept.append(dn)
                        modes.append(dict(d=dn, kmag=rep['kmag']))
                consumed.add(key)
            else:
                assert pkey in self.reps, f"conjugate partner missing for {key}"
                for cm in [(1 / np.sqrt(2), 1 / np.sqrt(2)), (-1j / np.sqrt(2), 1j / np.sqrt(2))]:
                    d = self._closed(rep['waves'], cm)
                    n2 = sum(abs(v) ** 2 for v in d.values())
                    s = 1 / np.sqrt(n2)
                    modes.append(dict(d={q: v * s for q, v in d.items()}, kmag=rep['kmag']))
                consumed.add(key); consumed.add(pkey)
        W = max(len(m['d']) for m in modes)
        N = len(modes)
        iQ = np.zeros((N, W, 3), np.int64); D = np.zeros((N, W), complex); nw = np.zeros(N, int)
        for i, m in enumerate(modes):
            for j, (t, v) in enumerate(m['d'].items()):
                iQ[i, j] = t; D[i, j] = v
            nw[i] = len(m['d'])
        self.iQ, self.D, self.nwav = iQ, D, nw
        self.Q = self._kfloat(iQ)                 # floats derived exactly from ints
        self.kmag = np.array([m['kmag'] for m in modes])
        self.P = self.kmag ** -3.0
        self.N = N

    # ---------- evaluations ----------
    def eval_modes(self, X):
        ph = np.exp(1j * np.einsum('pc,nwc->pnw', X, self.Q))
        U = np.einsum('pnw,nw->pn', ph, self.D)
        assert np.abs(U.imag).max() < 1e-9 * max(1.0, np.abs(U.real).max())
        return U.real

    def Cphi_modes(self, X, Y):
        UX, UY = self.eval_modes(X), self.eval_modes(Y)
        return np.einsum('pn,qn,n->pq', UX, UY, self.P)

    def Cphi_pairs(self, X, Y):
        UX, UY = self.eval_modes(X), self.eval_modes(Y)
        return np.einsum('pn,pn,n->p', UX, UY, self.P)

    def Cphi_image(self, X, Y):
        """independent construction: direct + glide-image sum over the FULL shifted lattice."""
        p = self.p; sA = p['sA']; kcut = p['kcut']
        nxm = int(np.floor(kcut / self.sx)) + 1
        nym = int(np.floor(kcut / self.sy)) + 2
        nzm = int(np.floor(kcut / self.sz)) + 2
        ks = []
        for nx in range(-nxm, nxm + 1):
            for my in range(-nym, nym + 1):
                for mz in range(-nzm, nzm + 1):
                    k = np.array([self.sx * nx, self.sy * (my + 0.5 * self.twy),
                                  self.sz * (mz + 0.5 * self.twz)])
                    kn = np.linalg.norm(k)
                    if TOL < kn <= kcut:
                        ks.append(k)
        K = np.array(ks); P = np.linalg.norm(K, axis=1) ** -3.0
        MK = K * np.array([1.0, -1.0, 1.0])
        phg = np.exp(-1j * MK @ self.TA)
        E_x_k = np.exp(1j * X @ K.T); E_y_k = np.exp(-1j * Y @ K.T)
        E_x_Mk = np.exp(1j * X @ MK.T)
        direct = np.einsum('pk,qk,k->pq', E_x_k, E_y_k, P)
        image = np.einsum('pk,qk,k->pq', E_x_Mk * phg[None, :], E_y_k, P) * sA
        C = 0.5 * (direct + image)
        assert np.abs(C.imag).max() < 1e-8 * max(1.0, np.abs(C.real).max())
        return C.real

    def var_profile(self, ys):
        X = np.zeros((len(ys), 3)); X[:, 1] = ys
        return self.Cphi_pairs(X, X)

    def deck_check(self, nrand=40, seed=0):
        rng = np.random.default_rng(seed)
        p = self.p
        MA = np.array([1.0, -1.0, 1.0])
        def gA(x): return MA * x + self.TA
        def t1(x): return x + np.array([0, p['L1y'], 0])
        def t2(x): return x + np.array([0, 0, p['L2z']])
        words = [([gA], p['sA']), ([t1], p['s1']), ([t2], p['s2']),
                 ([gA, gA], 1), ([gA, t1], p['sA'] * p['s1']),
                 ([t1, t2, gA], p['s1'] * p['s2'] * p['sA']),
                 ([gA, t2, gA, t1], p['s1'] * p['s2'])]
        X = rng.uniform(-2, 2, size=(nrand, 3))
        worst = 0.0
        for maps, chi in words:
            GX = X.copy()
            for mp in maps[::-1]:
                GX = np.array([mp(x) for x in GX])
            U, GU = self.eval_modes(X), self.eval_modes(GX)
            worst = max(worst, np.abs(GU - chi * U).max())
        return worst

    def gram(self):
        G = np.zeros((self.N, self.N))
        dicts = []
        for i in range(self.N):
            dicts.append({tuple(self.iQ[i, j]): self.D[i, j] for j in range(self.nwav[i])})
        for i in range(self.N):
            for j in range(i, self.N):
                s = 0j
                for q, v in dicts[i].items():
                    mq = self._ineg(q)
                    if mq in dicts[j]:
                        s += v * dicts[j][mq]
                G[i, j] = G[j, i] = s.real
        return G

    def sample(self, X, nsamp, rng):
        U = self.eval_modes(X)
        g = rng.standard_normal((self.N, nsamp))
        return U @ (np.sqrt(self.P)[:, None] * g)

    # ---------- quadratic field -> sky (multi-transfer engine) ----------
    def sky_cov_q_multi(self, Fls, ls, chunk=4000):
        """C^{T,q}[(lm),(l'm')] for each transfer in Fls, sharing one construction.
        C = 2 sum_{n<=m} w P_n P_m S[u_n u_m] (x) S*[u_n u_m];  S via plane-wave products.
        Composite K=0 waves contribute only to l=0 (Kn_safe trick keeps that exact)."""
        lm = [(l, m) for l in ls for m in range(-l, l + 1)]
        nlm = len(lm)
        iu, ju = np.triu_indices(self.N)
        w = np.where(iu == ju, 1.0, 2.0)
        PPw = 2.0 * w * self.P[iu] * self.P[ju]
        Wp = self.iQ.shape[1]; W2 = Wp * Wp; NP = len(iu)
        B = np.int64(8192); OFF = np.int64(4096)
        # pass 1: packed integer keys of all composite wavevectors
        packs = np.empty(NP * W2, np.int64)
        for s0 in range(0, NP, chunk):
            sl = slice(s0, min(s0 + chunk, NP))
            iK = (self.iQ[iu[sl]][:, :, None, :] + self.iQ[ju[sl]][:, None, :, :]).reshape(-1, 3)
            packs[sl.start * W2: sl.stop * W2] = ((iK[:, 0] + OFF)
                                                  + (iK[:, 1] + OFF) * B
                                                  + (iK[:, 2] + OFF) * B * B)
        uniq, inv = np.unique(packs, return_inverse=True)
        del packs
        iz = uniq // (B * B) - OFF
        r = uniq % (B * B)
        iy = r // B - OFF
        ix = r % B - OFF
        # composite (untwisted) lattice: shifts double to integers twy, twz
        Kx = self.sx * ix.astype(float)
        Ky = self.sy * (iy.astype(float) + self.twy)
        Kz = self.sz * (iz.astype(float) + self.twz)
        Kn = np.sqrt(Kx * Kx + Ky * Ky + Kz * Kz)
        Kn_safe = np.maximum(Kn, 1e-12)
        th = np.arccos(np.clip(Kz / Kn_safe, -1, 1))
        ph = np.arctan2(Ky, Kx)
        zK = (Kn == 0)   # v0.3: composite K=0 contributes only to l=0; enforce exactly
        Ftabs = []
        for Fl in Fls:
            Ftab = np.zeros((nlm, len(uniq)), complex)
            for a, (l, m) in enumerate(lm):
                Ftab[a] = 4 * np.pi * (1j ** l) * Fl(l, Kn_safe) * np.conj(Ylm(l, m, th, ph))
                if l > 0:
                    Ftab[a][zK] = 0.0
            Ftabs.append(Ftab)
        Cs = [np.zeros((nlm, nlm), complex) for _ in Fls]
        # pass 2: gather + contract per chunk (cc rebuilt on the fly; memory-lean)
        for s0 in range(0, NP, chunk):
            sl = slice(s0, min(s0 + chunk, NP))
            nc = sl.stop - sl.start
            cc = (self.D[iu[sl]][:, :, None] * self.D[ju[sl]][:, None, :]).reshape(nc, W2)
            gi = inv[sl.start * W2: sl.stop * W2]
            for f, Ftab in enumerate(Ftabs):
                F_g = Ftab[:, gi].reshape(nlm, nc, W2)
                S = np.einsum('apw,pw->ap', F_g, cc)
                Cs[f] += (S * PPw[sl][None, :]) @ S.conj().T
        return Cs, lm

    def sky_cov_q(self, Fl, ls, chunk=4000, verbose=False):
        Cs, lm = self.sky_cov_q_multi([Fl], ls, chunk=chunk)
        return Cs[0], lm

    def A_refl_y(self, C, lm, ls):
        idx = {t: a for a, t in enumerate(lm)}
        out = {}
        for l in ls:
            s = 0j
            for m in range(-l, l + 1):
                s += (-1) ** m * C[idx[(l, m)], idx[(l, -m)]]
            out[l] = s.real / (4 * np.pi)
        return out

def F_SW(l, K, chi=1.0):
    return spherical_jn(l, K * chi) / 5.0

def band_stats(M, C, lm, band=(2, 3, 4)):
    """A_l per l, band sum, trace, rho for one covariance block."""
    A = M.A_refl_y(C, lm, list(band))
    idx = {t: a for a, t in enumerate(lm)}
    Tr = sum(C[idx[(l, m)], idx[(l, m)]].real for l in band for m in range(-l, l + 1))
    Ab = sum(A[l] for l in band)
    return A, Ab, Tr, 4 * np.pi * Ab / Tr

def extrapolate_k3(kcuts, vals):
    """least-squares fit v(k) = v_inf + c*k^-3; returns (v_inf, c, rms)."""
    x = np.asarray(kcuts, float) ** -3.0
    y = np.asarray(vals, float)
    Amat = np.stack([np.ones_like(x), x], 1)
    coef, *_ = np.linalg.lstsq(Amat, y, rcond=None)
    rms = float(np.sqrt(np.mean((Amat @ coef - y) ** 2)))
    return float(coef[0]), float(coef[1]), rms
