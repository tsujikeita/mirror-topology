# -*- coding: utf-8 -*-
"""Legacy kernel port of the A10 v1.2.9 (frozen: tag step1-phaseA-A10-freeze-v1.0) generation/scan path: quadrature D(R) representation (A9/A11 construction), A8b scan kernel
(float64 primary chunk 2000 / float32 sensitivity chunk 20000; packed products in the selection dtype; float64 einsum evaluation at the selected axis; plane-folded axis),
principal symmetric sqrt, PR3-power matching, and the 1R:m z generator with the A10 stream registry (MASTER_SEED 20260912, namespaces). Assets are loaded from a mirror-topology
checkout at the frozen A8 commit and SHA-gated. Purpose: two-layer regression (spec D) — legacy: bit-identical outputs against the frozen notebook kernel in the same environment;
cross-environment: agreement with the A10 official calibration checkpoint within a registered tolerance. It is NOT the Phase D bank generator (that is registered separately)."""
from __future__ import annotations
import hashlib, json, os, sys
import numpy as np
from .errors import InputContractError

MASTER_SEED = 20260912; STREAM = dict(gaussian=0, rotation=1, calibration=2, pseudo=3, bootstrap=4, w2=5)
GEN_NS = dict(calibration=100, m_sensitivity=200, pseudo=300, negative_control=400, w2_independent=500, w2_crn=600, w2_isotropic=700)
CHUNK_BY_SEL = dict(float64=2000, float32=20000); LBLK = [(slice(0, 5), 2), (slice(5, 12), 3), (slice(12, 21), 4)]
ASSET_SHA = dict(bstack="ec2d3eb501c3e00af85a505d95d7141fddb4ea23ab1da971906a5c21f80eef5f", bstack_array="eb51414885785b77e9d3f7fbb25e1c9396f52e19c053d58113d50e206353a93f", cvec_array="17d85b41ee0665d88418ebf8dee794d0da0a6f219053e983ec9b0501d763c8c6", antipode="11efe112b8f388b851b5218fa1287aafa3e32ce359f98cccb7c6649d79cc599a")


# Source identity is separate from orthogonality. An orthogonal basis change
# can preserve numerical D(R) gates while disagreeing with the frozen B-stack.
BRIDGE_SHA = "45107d1608d50816712f1aa452d9fa39af4adc9ec035fbe9279b264760d65872"
BASIS_SHA = {
    "M21": "c488cc7070a2d391e8ceeea08c87643d1f1552515990fb135652c4599c6101e8",
    "LM": "4d5f9471cc92c9fc76d27237fbe0bf43acb0aec3c30fccd78b7ea9cb5c4a153c",
    "RB": "e278e7ec89765483c31b205325035f47fc57f9a3951c0feb34934a9e5b4aa10b",
}

def _legacy_int(value, name, minimum=0):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < minimum:
        raise InputContractError(f"{name} must be a non-bool integer >= {minimum}")
    return int(value)

def _load_frozen_bridge(root):
    import types
    path = os.path.join(os.path.realpath(os.fspath(root)), "t2b2_bridge.py")
    with open(path, "rb") as fh:
        body = fh.read()
    if hashlib.sha256(body).hexdigest() != BRIDGE_SHA:
        raise InputContractError("legacy bridge source SHA mismatch")
    # Execute exactly the verified bytes, from the requested root. Do not use
    # an unrelated module earlier in sys.path and do not purge caller modules.
    mod = types.ModuleType("_step1_frozen_legacy_bridge")
    mod.__file__ = path
    exec(compile(body, path, "exec"), mod.__dict__)
    return mod


def _fsha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(8 << 20), b""): h.update(b)
    return h.hexdigest()


def asha(a): return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


class LegacyKernel:
    def __init__(self, mt_root: str):
        import healpy as hp
        from scipy.special import sph_harm_y
        self.hp, self.sph = hp, sph_harm_y
        br = _load_frozen_bridge(mt_root)
        self.RB = br.real_basis_lm(); self.LM = br.lm_full(); self.M21 = br.M_matrix()[0]
        got_basis = dict(M21=asha(self.M21),
                         LM=hashlib.sha256(json.dumps(self.LM).encode()).hexdigest(),
                         RB=hashlib.sha256(json.dumps(self.RB).encode()).hexdigest())
        if got_basis != BASIS_SHA:
            raise InputContractError("legacy real/complex basis identity mismatch")
        bp = os.path.join(mt_root, "results/step1_phaseA/A5_freeze/s1_Bstack_l2_4_N16_common_v1.npz")
        if _fsha(bp) != ASSET_SHA["bstack"]: raise InputContractError("A5 B-stack file SHA mismatch")
        z = np.load(bp); self.Bp, self.Bm = np.asarray(z["Bp_stack"], np.float64), np.asarray(z["Bm_stack"], np.float64)
        if hashlib.sha256(np.ascontiguousarray(self.Bp).tobytes() + np.ascontiguousarray(self.Bm).tobytes()).hexdigest() != ASSET_SHA["bstack_array"]: raise InputContractError("A5 B-stack array SHA mismatch")
        z0 = np.load(os.path.join(mt_root, "docs/step0_frozen_Bpm_v1.npz"), allow_pickle=True); self.CVEC = np.asarray(z0["CVEC"], np.float64)
        if asha(self.CVEC) != ASSET_SHA["cvec_array"]: raise InputContractError("CVEC SHA mismatch")
        self.C_ISO = np.diag(self.CVEC); self.c_pr3 = self.CVEC[[0, 5, 12]]
        # quadrature representation (A9/A11 construction, mathematical gates)
        LMAX = 4; self.NT = self.NP = 2 * LMAX + 2; xg, wg = np.polynomial.legendre.leggauss(self.NT); th = np.arccos(xg); ph = 2 * np.pi * np.arange(self.NP) / self.NP
        TH, PH = np.meshgrid(th, ph, indexing="ij"); self.WQ = (np.repeat(wg[:, None], self.NP, axis=1) * (2 * np.pi / self.NP)).ravel()
        self.DIRS = np.column_stack([np.sin(TH).ravel() * np.cos(PH).ravel(), np.sin(TH).ravel() * np.sin(PH).ravel(), np.cos(TH).ravel()])
        YQ = self.Ymat(self.DIRS); self.YQW = (YQ * self.WQ[:, None]).T
        if np.abs(self.YQW @ YQ - np.eye(21)).max() >= 1e-12: raise InputContractError("quadrature not orthonormal")
        P = np.polynomial.legendre.Legendre
        if not all(abs(np.sum(wg * P.basis(k)(xg)) - (2.0 if k == 0 else 0.0)) < 1e-12 for k in range(2 * self.NT)): raise InputContractError("Gauss-Legendre exactness")
        # scan features
        self.iu = np.triu_indices(21); self.off = (self.iu[0] != self.iu[1])
        Bp32 = self.Bp.astype(np.float32); self.Fp32 = np.array([self.fvec(Bp32[a]) for a in range(3072)], dtype=np.float32); self.Fp64 = np.array([self.fvec(self.Bp[a]) for a in range(3072)], dtype=np.float64)
        vec = np.array(hp.pix2vec(16, np.arange(3072))).T; self.ANTIPODE = hp.vec2pix(16, -vec[:, 0], -vec[:, 1], -vec[:, 2]); self.PLANE = np.minimum(np.arange(3072), self.ANTIPODE)
        if asha(self.ANTIPODE.astype(np.int32)) != ASSET_SHA["antipode"]: raise InputContractError("antipode map SHA mismatch")
        self.calls = []

    # ---- representation
    def Yc_at(self, dirs):
        th, ph = self.hp.vec2ang(dirs); return np.array([self.sph(l, m, th, ph) for (l, m) in self.LM])
    def Ymat(self, dirs): return (self.M21.conj() @ self.Yc_at(dirs)).real.T
    def D_of_R(self, Rm): return self.YQW @ self.Ymat(self.DIRS @ Rm)
    def D_batch(self, Rs):
        Pp = np.einsum("qj,kji->kqi", self.DIRS, Rs); th, ph = self.hp.vec2ang(Pp.reshape(-1, 3)); Y = np.array([self.sph(l, m, th, ph) for (l, m) in self.LM]).reshape(21, len(Rs), -1)
        Yr = np.einsum("ab,bkq->kqa", self.M21.conj(), Y).real; return np.einsum("aq,kqb->kab", self.YQW, Yr)

    # ---- covariance helpers
    def matched(self, C):
        c_ct = np.array([np.trace(C[b, b]) / (2 * l + 1) for b, l in LBLK]); Dm = np.diag(np.concatenate([np.repeat(np.sqrt(self.c_pr3[i] / c_ct[i]), 2 * l + 1) for i, (b, l) in enumerate(LBLK)])); return Dm @ C @ Dm, c_ct
    @staticmethod
    def psqrt(C):
        w, V = np.linalg.eigh(C); wc = np.where(w < 1e-12 * w.max(), 0.0, w); S = V @ np.diag(np.sqrt(wc)) @ V.T
        return S, dict(lambda_min=float(w.min()), clip=int(np.sum(w < 1e-12 * w.max())), sym=float(np.linalg.norm(S - S.T) / np.linalg.norm(S)), recon=float(np.linalg.norm(S @ S.T - C) / np.linalg.norm(C)))

    # ---- scan (A8b kernel)
    def fvec(self, B): v = B[self.iu].copy(); v[self.off] *= 2.0; return v
    @staticmethod
    def packed_into(x, out):
        k = 0; d = x.shape[1]
        for i in range(d):
            w = d - i; np.multiply(x[:, i:i + 1], x[:, i:], out=out[:, k:k + w]); k += w
        return out
    def scan(self, X, selection):
        n = len(X); T1 = np.empty(n); T2 = np.empty(n); AX = np.empty(n, np.int32); dt = np.float32 if selection == "float32" else np.float64; Fp = self.Fp32 if selection == "float32" else self.Fp64; CHUNK = CHUNK_BY_SEL[selection]
        for a in range(0, n, CHUNK):
            x64 = X[a:a + CHUNK]; x = x64 if dt == np.float64 else x64.astype(np.float32); f = self.packed_into(x, np.empty((len(x), len(self.iu[0])), dt)); Sp = f @ Fp.T; ax = Sp.argmin(1).astype(np.int32); sel = Sp[np.arange(len(x)), ax]
            t1 = np.einsum("ni,nij,nj->n", x64, self.Bp[ax], x64, optimize=True); t2 = np.einsum("ni,nij,nj->n", x64, self.Bm[ax], x64, optimize=True)
            if not (np.isfinite(sel).all() and np.isfinite(t1).all() and np.isfinite(t2).all()): raise InputContractError("non-finite selection/evaluation output")
            AX[a:a + CHUNK] = ax; T1[a:a + CHUNK] = t1; T2[a:a + CHUNK] = t2
        return dict(T1=T1, T2=T2, AX=AX, PL=self.PLANE[AX])

    # ---- generator (A10 streams)
    @staticmethod
    def rng_for(stream, *ids):
        if stream not in STREAM:
            raise InputContractError("unregistered legacy stream")
        key_ids = [_legacy_int(i, "stream identity") for i in ids]
        return np.random.default_rng(np.random.SeedSequence([MASTER_SEED, 11, STREAM[stream], *key_ids]))
    def generate(self, N, m, stream_ids, S_list, selections=("float64",), chunk_clusters=2000):
        from scipy.spatial.transform import Rotation
        N = _legacy_int(N, "N", 1)
        m = _legacy_int(m, "m", 1)
        chunk_clusters = _legacy_int(chunk_clusters, "chunk_clusters", 1)
        if not isinstance(stream_ids, (tuple, list)) or not stream_ids:
            raise InputContractError("nonempty legacy stream identity required")
        stream_ids = tuple(_legacy_int(i, "stream identity") for i in stream_ids)
        if stream_ids[0] not in GEN_NS.values(): raise InputContractError("unregistered stream namespace")
        if not isinstance(selections, (tuple, list)) or not selections or len(set(selections)) != len(selections) or any(x not in CHUNK_BY_SEL for x in selections):
            raise InputContractError("nonempty unique registered selection paths required")
        if not isinstance(S_list, (tuple, list)) or not S_list:
            raise InputContractError("nonempty root list required")
        for S in S_list:
            a = np.asarray(S)
            if a.shape != (21, 21) or a.dtype.kind not in "fiu" or not np.isfinite(a).all():
                raise InputContractError("legacy roots must be finite real (21,21) matrices")
        if N % m:
            raise InputContractError("N must be a multiple of m")
        self.calls.append(dict(ids=[int(i) for i in stream_ids], N=int(N), m=int(m), systems=len(S_list)))
        K = N // m
        if K * m != N: raise InputContractError("N must be a multiple of m")
        rr = self.rng_for("rotation", *stream_ids); rz = self.rng_for("gaussian", *stream_ids); cid = np.repeat(np.arange(K), m)
        out = {(s, sel): dict(T1=np.empty(N), T2=np.empty(N), AX=np.empty(N, np.int32), PL=np.empty(N, np.int32)) for s in range(len(S_list)) for sel in selections}
        for k0 in range(0, K, chunk_clusters):
            k1 = min(K, k0 + chunk_clusters); Rs = Rotation.random(num=k1 - k0, rng=rr).as_matrix(); Ds = self.D_batch(Rs); Z = rz.standard_normal((k1 - k0, m, 21)); sl = slice(k0 * m, k1 * m)
            for s, S in enumerate(S_list):
                X = np.einsum("kab,kmb->kma", Ds @ S, Z).reshape(-1, 21)
                for sel in selections:
                    d = self.scan(X, sel)
                    for kk in ("T1", "T2", "AX", "PL"): out[(s, sel)][kk][sl] = d[kk]
        return out, cid, dict(K=K, m=m)
