# -*- coding: utf-8 -*-
"""Step 1 Phase A6/A7 v1.4.2 (audit 2026-09-05 #6: archive polish only - torsion-free wording, mock future-source unit test, bibliographic cleanup, environment metadata). v1.4.1: nearest-sufficiency theorem battery replaces the invalid non-nearest test; test renames + expected-geometry asserts; margin columns split; E2/E8 in completeness battery; tz-aware timestamps). Base v1.4: matching sense fix, Planck non-operational, enumeration completeness gate, element_type by invariant projection, boundary tests, final all-true assert).

  v1.3: geometry-based published-search coverage (alpha, theta, matching sense, source-specific domains); exclusion-witness
  search over ALL elements with d<1 (not only the nearest per coset); observational status with 4 categories; CVP
  certification battery (residual + guaranteed-box cross-check + provenance); x0 bridge as equivalence relation;
  E2 exclusion predicate = fixed-point neighbourhoods; boundary battery for reduce_to_cell.

  * certified CVP/SVP: LLL reduction + Gram-Schmidt sphere enumeration (Fincke-Pohst); Babai/width and BFS demoted to
    cross-checks; audit counterexample (E7 LAx=1, L2x=0.9, L2z=0.01) included as a hard test
  * nearest element recorded: coset id, orientation, element type, integer lattice coefficients, translation vector
  * search_covered(element): explicit function + columns; observational status derived from it
  * synthetic tests of the critical branches: coverage_undetermined (E7/E8 improper-nearest), thresholds 0.984/0.986/1.000
  * observer pilots redesigned in family-specific REDUCED physical coordinates with quotient-aware distances;
    primary rows flagged (analysis_role / is_primary_observer / observer_design_version); hard gate: 50 primary rows
  * deterministic canonical reduction reduce_to_cell(x) -> (coset_id, lattice coefficients, u); battery: idempotence,
    orbit equivalence, boundary convention, volume identity
  * CMBtopology x0 convention bridge: registered conversion x0_CT = -r_obs (hypothesis; to be verified numerically in A11)
"""
import os, sys, json, hashlib, datetime, itertools, subprocess
import numpy as np, pandas as pd
OUT = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/colab_sim/runs_step1_phaseA/a6a7_v1.4.2'
CT = sys.argv[2] if len(sys.argv) > 2 else '/tmp/CMBtopology_pinned'
os.makedirs(OUT, exist_ok=True)
L_LSS_MPC = 27649.8; THR_SEARCH = 0.985; THR_GEO = 1.0; EPS_NUM = 1e-9
I3 = np.eye(3)
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def run(c): return subprocess.run(c, capture_output=True, text=True).stdout.strip()
G = {}
G['G_ct_commit'] = (run(['git', '-C', CT, 'rev-parse', 'HEAD']) == '0cc65e34f03df85e92f738686bff0a476132f337')
G['G_ct_clean'] = (run(['git', '-C', CT, 'status', '--porcelain', '--untracked-files=no']) == '')
G['G_ct_origin'] = (run(['git', '-C', CT, 'remote', 'get-url', 'origin']).rstrip('/').removesuffix('.git')
                    == 'https://github.com/CompactCollaboration/CMBtopology')
assert all(G.values()), G
CT_SRC_SHA = {f: sha(os.path.join(CT, 'topology', 'src', f)) for f in ['E1.py', 'E2.py', 'E7.py', 'E8.py', 'config.py']}

# ============================================================ certified lattice routines
def lll(B, delta=0.75):
    """LLL reduction of column basis B (3x3). Returns reduced basis and unimodular U with B_red = B @ U."""
    B = B.astype(float).copy(); n = B.shape[1]; U = np.eye(n, dtype=int)
    def gs(B):
        Q = np.zeros_like(B); mu = np.zeros((n, n))
        for i in range(n):
            v = B[:, i].copy()
            for j in range(i):
                mu[i, j] = B[:, i] @ Q[:, j] / (Q[:, j] @ Q[:, j]); v -= mu[i, j] * Q[:, j]
            Q[:, i] = v
        return Q, mu
    k = 1
    while k < n:
        Q, mu = gs(B)
        for j in range(k - 1, -1, -1):
            q = int(np.round(mu[k, j]))
            if q != 0:
                B[:, k] -= q * B[:, j]; U[:, k] -= q * U[:, j]; Q, mu = gs(B)
        if Q[:, k] @ Q[:, k] >= (delta - mu[k, k - 1] ** 2) * (Q[:, k - 1] @ Q[:, k - 1]): k += 1
        else:
            B[:, [k - 1, k]] = B[:, [k, k - 1]]; U[:, [k - 1, k]] = U[:, [k, k - 1]]; k = max(k - 1, 1)
    return B, U
def cvp_certified(w, B, exclude_zero=False):
    """Certified closest vector: minimise |w + B n| over n in Z^3 (n != 0 if exclude_zero) by sphere enumeration
    on the LLL-reduced basis with Gram-Schmidt bounds (Fincke-Pohst). Returns (dist, n_original_basis, vec)."""
    Br, U = lll(B)
    Q, R = np.linalg.qr(Br)                    # Br = Q R, R upper triangular (GS lengths on the diagonal)
    y = Q.T @ (-w)                             # target in orthonormal frame; minimise |R n - y|  (+ component outside span = 0 in 3D)
    n = Br.shape[1]
    # initial radius: Babai
    c = np.linalg.solve(R, y); n0 = np.round(c); best_r2 = float(np.sum((R @ n0 - y) ** 2)); best_n = n0.copy()
    if exclude_zero and np.all(n0 == 0):
        # SVP: a valid finite initial radius is the shortest reduced-basis vector (nonzero lattice vector)
        j = int(np.argmin(np.linalg.norm(Br, axis=0))); best_n = np.eye(n)[:, j]; best_r2 = float(np.sum((R @ best_n - y) ** 2))
    # enumerate from the last coordinate down (Schnorr-Euchner style, full within radius)
    def rec(i, partial, acc):
        nonlocal best_r2, best_n
        # solve for coordinate i given fixed n_{i+1..}
        rhs = y[i] - sum(R[i, j] * partial[j] for j in range(i + 1, n))
        center = rhs / R[i, i]
        bound = np.sqrt(max(best_r2 - acc, 0.0)) / abs(R[i, i]) + 1e-12
        lo, hi = int(np.floor(center - bound)), int(np.ceil(center + bound))
        # visit candidates ordered by proximity to center for pruning efficiency
        for ni in sorted(range(lo, hi + 1), key=lambda t: abs(t - center)):
            partial[i] = ni
            acc_i = acc + (R[i, i] * ni - rhs) ** 2
            if acc_i > best_r2 + 1e-15: continue
            if i == 0:
                if exclude_zero and all(partial[j] == 0 for j in range(n)): continue
                if acc_i < best_r2 - 1e-15: best_r2 = acc_i; best_n = np.array(partial, float)
            else:
                rec(i - 1, partial, acc_i)
    rec(n - 1, [0] * n, 0.0)
    n_orig = U @ best_n.astype(int)
    vec = B @ n_orig
    CVP_STATS['nodes'] = CVP_STATS.get('nodes', 0) + 1
    return float(np.sqrt(best_r2)), n_orig, vec
CVP_STATS = {}
def enumerate_within(w, B, radius, exclude_zero=False):
    """All n in Z^3 with |w + B n| <= radius (complete sphere enumeration on the LLL-reduced basis)."""
    Br, U = lll(B); Q, R = np.linalg.qr(Br); y = Q.T @ (-w); n = 3; out = []
    def rec(i, partial, acc):
        rhs = y[i] - sum(R[i, j] * partial[j] for j in range(i + 1, n)); center = rhs / R[i, i]
        bound = np.sqrt(max(radius ** 2 - acc, 0.0)) / abs(R[i, i]) + 1e-12
        for ni in range(int(np.floor(center - bound)), int(np.ceil(center + bound)) + 1):
            partial[i] = ni; acc_i = acc + (R[i, i] * ni - rhs) ** 2
            if acc_i > radius ** 2 + 1e-15: continue
            if i == 0:
                nn = U @ np.array(partial, int)
                if exclude_zero and np.all(nn == 0): continue
                out.append((float(np.sqrt(acc_i)), nn, B @ nn))
            else: rec(i - 1, partial, acc_i)
    rec(n - 1, [0] * n, 0.0)
    return sorted(out, key=lambda z: z[0])
def cvp_certification(w, B, d_ret, n_ret):
    """Independent certification of a returned CVP solution: (1) residual recomputation in the original basis;
    (2) guaranteed-box cross-check: every n with |w+Bn| <= d_ret satisfies |n - c|_2 <= d_ret/sigma_min(B), c=-B^{-1}w;
    enumerate that box completely and compare the minimum."""
    resid = float(np.linalg.norm(w + B @ n_ret)); sv = np.linalg.svd(B, compute_uv=False)
    c = np.linalg.solve(B, -w); rad = d_ret / sv[-1] + 1e-9
    lo = np.floor(c - rad).astype(int); hi = np.ceil(c + rad).astype(int)
    nbox = int(np.prod(hi - lo + 1))
    if nbox > 2_000_000: return dict(residual=resid, residual_ok=abs(resid - d_ret) < 1e-9, box_checked=False, box_size=nbox,
                                     cond=float(sv[0] / sv[-1]), sigma_min=float(sv[-1]))
    best = np.inf
    for n0 in range(lo[0], hi[0] + 1):
        for n1 in range(lo[1], hi[1] + 1):
            for n2 in range(lo[2], hi[2] + 1):
                nn = np.array([n0, n1, n2]);
                if np.all(nn == 0) and np.allclose(w, 0): continue
                best = min(best, np.linalg.norm(w + B @ nn))
    return dict(residual=resid, residual_ok=abs(resid - d_ret) < 1e-9, box_checked=True, box_size=nbox,
                box_min=float(best), box_ok=bool(best >= d_ret - 1e-9), cond=float(sv[0] / sv[-1]), sigma_min=float(sv[-1]))

# ============================================================ crystallographic data
def family_data(fam, L, **shape):
    if fam == 'E1':
        Lx, Ly, Lz = shape.get('Lx', L), shape.get('Ly', L), shape.get('Lz', L)
        lat = np.column_stack([[Lx, 0, 0], [0, Ly, 0], [0, 0, Lz]]).astype(float)
        return dict(lattice=lat, cosets=[('id', I3, np.zeros(3))], cell=lat.copy(), params=dict(Lx=Lx, Ly=Ly, Lz=Lz))
    if fam == 'E2':
        Lx, Ly, Lz = shape.get('Lx', L), shape.get('Ly', L), shape.get('Lz', L)
        TB = np.array([0, 0, Lz]); Rz = np.diag([-1., -1., 1.])
        lat = np.column_stack([[Lx, 0, 0], [0, Ly, 0], 2 * TB]).astype(float)
        return dict(lattice=lat, cosets=[('id', I3, np.zeros(3)), ('halfturn_B', Rz, TB)],
                    cell=np.column_stack([lat[:, 0], lat[:, 1], TB]), params=dict(Lx=Lx, Ly=Ly, Lz=Lz))
    if fam == 'E7':
        LAx, LAy, L1y, L2x, L2z = (shape.get('LAx', L), shape.get('LAy', 0.0), shape.get('L1y', L), shape.get('L2x', 0.0), shape.get('L2z', L))
        MA = np.diag([1., -1., 1.]); vA = np.array([LAx, LAy, 0.])
        lat = np.column_stack([[2 * LAx, 0, 0], [0, L1y, 0], [L2x, 0, L2z]]).astype(float)
        return dict(lattice=lat, cosets=[('id', I3, np.zeros(3)), ('glide_A', MA, vA)],
                    cell=np.column_stack([[LAx, 0, 0], lat[:, 1], lat[:, 2]]).astype(float),
                    params=dict(LAx=LAx, LAy=LAy, L1y=L1y, L2x=L2x, L2z=L2z))
    if fam == 'E8':
        LAx, LAy, LBx, LBz, LCy = (shape.get('LAx', L), shape.get('LAy', 0.0), shape.get('LBx', 0.0), shape.get('LBz', L), shape.get('LCy', L))
        MA = np.diag([1., -1., 1.]); vA = np.array([LAx, LAy, 0.]); MB = np.diag([-1., 1., 1.]); vB = np.array([LBx, 0, LBz])
        lat = np.column_stack([[2 * LAx, 0, 0], [0, LCy, 0], [0, 0, 2 * LBz]]).astype(float)
        return dict(lattice=lat, cosets=[('id', I3, np.zeros(3)), ('glide_A', MA, vA), ('glide_B', MB, vB), ('AB', MA @ MB, MA @ vB + vA)],
                    cell=np.diag([LAx, LCy, LBz]).astype(float), params=dict(LAx=LAx, LAy=LAy, LBx=LBx, LBz=LBz, LCy=LCy))
def element_type(M, t):
    """Classify x -> M x + t using the translation component along the invariant subspace of M:
    proper M != I: P = projector onto ker(M-I) (rotation axis); |P t| = 0 -> rotation, else screw.
    improper with tr M = 1 (reflection): P = projector onto the mirror plane (ker(M-I)); |P t| = 0 -> reflection, else glide."""
    det = np.linalg.det(M)
    if np.allclose(M, I3): return 'translation', True
    U_, S_, Vt = np.linalg.svd(M - I3); ker = Vt[S_ < 1e-9].T          # basis of ker(M - I)
    P = ker @ ker.T if ker.size else np.zeros((3, 3))
    tpar = float(np.linalg.norm(P @ t))
    if det > 0: return ('rotation' if tpar < 1e-9 else 'screw'), True
    if abs(np.trace(M) - 1) < 1e-9: return ('reflection' if tpar < 1e-9 else 'glide_reflection'), False
    return 'rotoinversion', False

# ============================================================ nearest clone (certified)
def nearest_clone(r, fd):
    """For observer at r: per-coset certified minima of |(M-I)r + v + t|, t in lattice (t != 0 for identity)."""
    recs = []
    for cid, M, v in fd['cosets']:
        w = (M - I3) @ r + v
        d, n, t = cvp_certified(w, fd['lattice'], exclude_zero=(cid == 'id'))
        et, proper = element_type(M, v + t)
        recs.append(dict(coset=cid, proper=proper, d=d, n=[int(x) for x in n], t_total=(v + t).tolist(), type=et))
    d_prop = min(x['d'] for x in recs if x['proper']); impr = [x['d'] for x in recs if not x['proper']]
    d_impr = min(impr) if impr else float('inf')
    near = min(recs, key=lambda x: x['d'])
    return d_prop, d_impr, near, recs
# Published matched-circle searches (registered source domains; to be re-verified against the papers at freeze)
SEARCH_SOURCES = {
    'vaudrevange2012': dict(operational=True, verified=True, alpha_deg=(10.0, 90.0), theta_deg=(11.0, 180.0),
                            senses=('phased', 'anti_phased'), reported_distance_limit=0.985, exact_geometry_from_alpha_min=float(np.cos(np.radians(10.0))),
                            reference='Vaudrevange, Starkman, Cornish, Spergel, PRD 86 (2012) 083526, arXiv:1206.2939 (WMAP7; general geometries; '
                                      'both matching senses; injectivity radius > 0.985 d_LSS for arcs intersecting at > 10 deg)'),
    'planck2013_temperature_backtoback': dict(operational=False, verified=False, alpha_deg=(20.0, 90.0), theta_deg=(180.0 - 1e-6, 180.0),
                            senses=('phased', 'anti_phased'), reference='Planck 2013 XXVI (A&A 571 A26): back-to-back, alpha_min ~20 deg (provisional; '
                                      'mask/orientation caveats; supplementary provenance only until verified against the paper)'),
    'planck2015_polarization_backtoback': dict(operational=False, verified=False, alpha_deg=(15.0, 90.0), theta_deg=(180.0 - 1e-6, 180.0),
                            senses=('phased', 'anti_phased'), reference='Planck 2015 XVIII (A&A 594 A18): back-to-back, alpha_min ~15 deg (provisional; '
                                      'supplementary provenance only until verified)'),
}
OPERATIONAL = [k for k, v in SEARCH_SOURCES.items() if v['operational']]
BOUNDARY_EPS = 1e-9
def circle_geometry(M, t, r):
    """For an element g(x)=Mx+t and observer r: clone displacements a=g(r)-r, b=g^{-1}(r)-r, |a|=|b|=d.
    Circle radius alpha=arccos(d) (LSS diameter = 1), centre separation theta=arccos(a.b/d^2), matching sense by det(M)."""
    a = (M - I3) @ r + t; Mi = np.linalg.inv(M); b = (Mi - I3) @ r - Mi @ t
    d = float(np.linalg.norm(a)); assert abs(np.linalg.norm(b) - d) < 1e-9
    if d >= THR_GEO - EPS_NUM: return d, None, None, None
    alpha = float(np.degrees(np.arccos(min(d, 1.0))))
    theta = float(np.degrees(np.arccos(np.clip(a @ b / d ** 2, -1, 1))))
    sense = 'anti_phased' if np.linalg.det(M) > 0 else 'phased'     # orientation-preserving -> anti-phased circle ordering
    return d, alpha, theta, sense
def covered_by(source, alpha, theta, sense):
    S = SEARCH_SOURCES[source]
    return (S['alpha_deg'][0] <= alpha <= S['alpha_deg'][1] and S['theta_deg'][0] <= theta <= S['theta_deg'][1]
            and sense in S['senses'])
def source_boundary(source, alpha, theta):
    S = SEARCH_SOURCES[source]
    return (min(abs(alpha - S['alpha_deg'][0]), abs(alpha - S['alpha_deg'][1]), abs(theta - S['theta_deg'][0]),
                abs(theta - S['theta_deg'][1])) <= 1e-6)
def witness_search(r, fd):
    """Enumerate ALL group elements with clone distance d < 1 (per coset, complete sphere enumeration of lattice translates),
    compute circle geometry, and return (candidates, exclusion witness or None)."""
    cands = []
    for cid, M, v in fd['cosets']:
        w = (M - I3) @ r + v
        for d, n, t in enumerate_within(w, fd['lattice'], THR_GEO, exclude_zero=(cid == 'id')):
            if d >= THR_GEO - EPS_NUM: continue
            dd, alpha, theta, sense = circle_geometry(M, v + t, r)
            et, proper = element_type(M, v + t)
            cov = {src: covered_by(src, alpha, theta, sense) for src in SEARCH_SOURCES}
            cands.append(dict(coset=cid, d=dd, alpha_deg=alpha, theta_deg=theta, sense=sense, type=et, n=[int(z) for z in n],
                              t_total=[round(float(z), 6) for z in (v + t)], **{f'covered_{k}': bool(val) for k, val in cov.items()},
                              covered_any=any(cov[k] for k in OPERATIONAL),           # operational sources only
                              source_boundary=any(source_boundary(k, alpha, theta) for k in OPERATIONAL)))
    # source-driven: coverage already implies alpha >= 10 deg, i.e. d <= cos(10 deg) (< 0.985); no separate 0.985 test
    excl = [c for c in cands if c['covered_any']]
    witness = min(excl, key=lambda c: (c['d'], c['coset'], tuple(c['n']))) if excl else None   # deterministic tie-break
    return cands, witness
def statuses(recs, cands, witness):
    d_all = min(x['d'] for x in recs)
    geo = ('circles_geometrically_present' if d_all < THR_GEO - EPS_NUM else
           'zero_radius_boundary' if abs(d_all - THR_GEO) <= EPS_NUM else 'no_nondegenerate_circles')
    if witness is not None: obs = 'excluded_by_published_search'
    elif d_all >= THR_GEO - EPS_NUM: obs = 'no_nondegenerate_circles'
    elif any(c['covered_any'] for c in cands): obs = 'not_excluded_by_published_search'
    # NOTE: with the current Vaudrevange2012-only operational configuration this branch is UNREACHABLE
    # (a covered candidate is itself an exclusion witness); kept for future sources with reported distance limits.
    else: obs = 'outside_published_search_domain'
    return d_all, geo, obs

# ============================================================ canonical reduction to the sampling cell
def reduce_to_cell(x, fd):
    """Deterministic: returns (coset_id, lattice_coeffs, u) with u in [0,1)^3 (half-open convention) such that
    x = g^{-1}(cell point) ... concretely finds the unique coset (M,v) and t in lattice with A u = M x + v + t."""
    A = fd['cell']; Ainv = np.linalg.inv(A); LatU = Ainv @ fd['lattice']
    for cid, M, v in fd['cosets']:
        u = Ainv @ (M @ x + v); k = np.floor(np.linalg.solve(LatU, u) + 1e-12); u = u - LatU @ k
        if np.all(u >= -1e-12) and np.all(u < 1 - 1e-12):
            return cid, [int(z) for z in -k], np.clip(u, 0, 1 - 1e-15)
    raise RuntimeError('reduction failed')
def cell_battery(fd, n=3000, seed=1):
    rng = np.random.default_rng(seed); A = fd['cell']
    V_cell = abs(np.linalg.det(A)); V_lat = abs(np.linalg.det(fd['lattice']))
    out = dict(volume_identity=bool(abs(V_cell * len(fd['cosets']) - V_lat) < 1e-12 * V_lat))
    X = rng.random((n, 3)) * 6 - 3
    idem = orbit = 0
    for x in X:
        cid, k, u = reduce_to_cell(x, fd); x_cell = A @ u
        cid2, k2, u2 = reduce_to_cell(x_cell, fd)
        idem += (cid2 == 'id' and np.allclose(u2, u, atol=1e-9))
        # orbit equivalence: every group image of x reduces to the same u
        ok = True
        for cid3, M, v in fd['cosets']:
            for m in itertools.product((-1, 0, 1), repeat=3):
                y = M @ x + v + fd['lattice'] @ np.array(m)
                _, _, u3 = reduce_to_cell(y, fd)
                if not np.allclose(u3, u, atol=1e-9): ok = False; break
            if not ok: break
        orbit += ok
    # systematic boundary points: faces, edges, corners of the cell at +-eps
    eps = 1e-7; bpts = []
    for corner in itertools.product((0.0, 1.0), repeat=3):
        for sgn in itertools.product((-eps, eps), repeat=3):
            bpts.append(A @ (np.array(corner) + np.array(sgn)))
    for u in itertools.product((0.0, 0.5, 1.0), repeat=3):
        if 0.5 in u: bpts.append(A @ (np.array(u) + eps)); bpts.append(A @ (np.array(u) - eps))
    b_ok = 0
    for x in bpts:
        cid, k, u = reduce_to_cell(x, fd); reps = 0
        for cid3, M, v in fd['cosets']:
            for m in itertools.product((-2, -1, 0, 1, 2), repeat=3):     # +-2: coset translations can require two lattice shifts
                y = M @ x + v + fd['lattice'] @ np.array(m); uu = np.linalg.inv(A) @ y
                reps += bool(np.all(uu >= -1e-12) and np.all(uu < 1 - 1e-12))
        cid2, _, u2 = reduce_to_cell(A @ u, fd)
        b_ok += (reps == 1 and cid2 == 'id' and np.allclose(u2, u, atol=1e-9))
    out.update(idempotence_frac=idem / n, orbit_equivalence_frac=orbit / n, boundary_points=len(bpts), boundary_ok_frac=b_ok / len(bpts),
               boundary_convention='u in [0,1)^3 half-open; A u = M x + v + t; coset priority = registered coset order')
    return out

# ============================================================ observer pilots in reduced physical coordinates
SEED = [20260905, 7]
def reduced_coords(fam, r, p):
    if fam == 'E1': return []
    if fam == 'E2':   # torus (x/Lx, y/Ly) modulo half-turn (p -> -p)
        return [float((r[0] / p['Lx']) % 1), float((r[1] / p['Ly']) % 1)]
    if fam == 'E7':   # eta_y = dist(y, (L1y/2) Z) / L1y in [0, 1/4]
        yy = r[1] / p['L1y']; return [float(min(abs(yy - 0.5 * k) for k in range(-3, 4)))]
    if fam == 'E8':   # eta_x = dist(x, LAx Z)/LAx in [0,1/2]; eta_y = dist(y, (LCy/2) Z)/LCy in [0,1/4]
        xx = r[0] / p['LAx']; yy = r[1] / p['LCy']
        return [float(min(abs(xx - k) for k in range(-3, 4))), float(min(abs(yy - 0.5 * k) for k in range(-3, 4)))]
def quotient_dist(fam, a, b):
    a, b = np.array(a), np.array(b)
    if fam == 'E2':
        return min(np.linalg.norm(a - s * b + np.array(nn)) for s in (1, -1) for nn in itertools.product((-1, 0, 1), repeat=2))
    return float(np.linalg.norm(a - b))
E2_FIXED_POINTS = [(0., 0.), (0., .5), (.5, 0.), (.5, .5)]     # half-turn fixed points on the (x/Lx, y/Ly) torus
PILOT = {'E2': dict(dim=2, box=[(0.0, 1.0), (0.0, 1.0)], min_sep=0.15,
                    exclude=lambda q: min(np.linalg.norm(np.array(q) - np.array(fp) + np.array(sh)) for fp in E2_FIXED_POINTS
                                          for sh in itertools.product((-1, 0, 1), repeat=2)) < 0.05,
                    exclude_text='reject if within 0.05 (torus distance) of a half-turn fixed point (0,0),(0,1/2),(1/2,0),(1/2,1/2)'),
         'E7': dict(dim=1, box=[(0.02, 0.23)], min_sep=0.06, exclude=lambda q: False, exclude_text='none (box excludes glide planes eta=0 and midpoint eta=1/4)'),
         'E8': dict(dim=2, box=[(0.03, 0.47), (0.02, 0.23)], min_sep=0.12, exclude=lambda q: False, exclude_text='none (box excludes reflection planes and midpoints)')}
def design(fam, k=3):
    rng = np.random.default_rng(np.random.SeedSequence(SEED + [{'E2': 2, 'E7': 7, 'E8': 8}[fam]])); spec = PILOT[fam]; pts = []
    while len(pts) < k:
        q = [lo + (hi - lo) * rng.random() for lo, hi in spec['box']]
        if spec['exclude'](q): continue
        if any(quotient_dist(fam, q, p) < spec['min_sep'] for p in pts): continue
        pts.append(q)
    return pts
def lift(fam, q, fd, rng):
    """Map reduced coordinates to a generic covering-space point r (irrelevant coordinates drawn generically)."""
    p = fd['params']
    if fam == 'E2': return np.array([q[0] * p['Lx'], q[1] * p['Ly'], 0.37 * 2 * p['Lz']])
    if fam == 'E7': return np.array([0.31 * p['LAx'], q[0] * p['L1y'], 0.42 * p['L2z']])
    if fam == 'E8': return np.array([q[0] * p['LAx'], q[1] * p['LCy'], 0.42 * p['LBz']])
PILOTS = {fam: design(fam) for fam in ['E2', 'E7', 'E8']}
ANCHORS = {'E2': {'half_turn_axis': [0.0, 0.0]}, 'E7': {'glide_plane': [0.0], 'midpoint_symmetry': [0.25]},
           'E8': {'reflection_plane_A': [0.25, 0.0], 'reflection_plane_B': [0.0, 0.12], 'plane_intersection': [0.0, 0.0]}}

# ============================================================ main grid (wave 1 benchmark slice)
SIZES = [0.7, 0.85, 1.0, 1.2, 1.5]
rows = []; fam_rec = {}
def add_row(fam, L, fd, kind, oid, r, q, primary, version):
    d_prop, d_impr, near, recs = nearest_clone(r, fd)
    cands, wit = witness_search(r, fd)
    d_all, geo, obs = statuses(recs, cands, wit)
    M_near = [c for c in fd['cosets'] if c[0] == near['coset']][0][1]
    dn, an, tn, sn = circle_geometry(M_near, np.array(near['t_total']), r)
    rows.append(dict(family=fam, L=L, shape=json.dumps(fd['params']), kind=kind, observer_id=oid,
                     analysis_role=('primary_observer' if primary else ('symmetry_anchor' if kind.startswith('anchor') else 'archived_pilot')),
                     is_primary_observer=bool(primary), observer_design_version=version,
                     reduced_coords=json.dumps(q), r_obs_LLSS=np.round(r, 6).tolist(),
                     d_clone=d_all, d_clone_proper=d_prop, d_clone_improper=d_impr,
                     nearest_coset=near['coset'], nearest_orientation=('preserving' if near['proper'] else 'reversing'),
                     nearest_element_type=near['type'], nearest_lattice_coefficients=json.dumps(near['n']),
                     nearest_total_translation=json.dumps([round(x, 6) for x in near['t_total']]),
                     nearest_alpha_deg=an, nearest_theta_deg=tn, nearest_sense=sn,
                     nearest_element_search_covered=(any(covered_by(src, an, tn, sn) for src in OPERATIONAL) if an is not None else False),
                     n_candidates_d_lt_1=len(cands), n_covered_candidates=int(sum(c['covered_any'] for c in cands)),
                     exclusion_witness_exists=(wit is not None),
                     exclusion_witness_coset=(wit['coset'] if wit else None), exclusion_witness_sense=(wit['sense'] if wit else None),
                     exclusion_witness_element_type=(wit['type'] if wit else None),
                     exclusion_witness_lattice_coefficients=(json.dumps(wit['n']) if wit else None),
                     exclusion_witness_translation=(json.dumps(wit['t_total']) if wit else None),
                     exclusion_witness_d=(wit['d'] if wit else None), exclusion_witness_alpha_deg=(wit['alpha_deg'] if wit else None),
                     exclusion_witness_theta_deg=(wit['theta_deg'] if wit else None),
                     exclusion_witness_search=(','.join(k for k in OPERATIONAL if wit[f'covered_{k}']) if wit else None),
                     exclusion_witness_source_boundary=(wit['source_boundary'] if wit else None),
                     reported_0p985_margin=d_all - THR_SEARCH, operational_distance_margin=d_all - float(np.cos(np.radians(10.0))),
                     operational_alpha_margin_deg=(an - 10.0 if an is not None else None), geometry_margin=d_all - THR_GEO,
                     threshold_boundary=bool(abs(d_all - float(np.cos(np.radians(10.0)))) <= EPS_NUM or abs(d_all - THR_GEO) <= EPS_NUM),
                     geometric_status=geo, observational_status=obs))
rng0 = np.random.default_rng(0)
for fam in ['E1', 'E2', 'E7', 'E8']:
    for L in SIZES:
        fd = family_data(fam, L)
        fam_rec[f'{fam}_L{L}'] = dict(params=fd['params'], lattice=fd['lattice'].tolist(),
                                      cosets=[dict(id=c, M=M.tolist(), v=v.tolist()) for c, M, v in fd['cosets']],
                                      sampling_cell_A=fd['cell'].tolist(), cell_volume=float(abs(np.linalg.det(fd['cell']))),
                                      cell_battery=(cell_battery(fd) if L in (1.0, 0.7) else None))
        if fam == 'E1':
            add_row(fam, L, fd, 'observer', 0, np.zeros(3), [], True, 'none(homogeneous)')
        else:
            for k, q in enumerate(PILOTS[fam]):
                add_row(fam, L, fd, 'observer', k + 1, lift(fam, q, fd, rng0), q, True, 'pilot_v2_reduced')
            for nm, q in ANCHORS[fam].items():
                add_row(fam, L, fd, f'anchor:{nm}', -1, lift(fam, q, fd, rng0), q, False, 'anchor')
df = pd.DataFrame(rows)
prim = df[df.is_primary_observer]
G['G_primary_rows_50'] = (len(prim) == 50)
assert G['G_primary_rows_50'], len(prim)

# ============================================================ critical-branch synthetic tests
tests = []
def T(name, fam, L, r, expect_obs, expect_geo=None, exp_nearest=None, exp_witness=None, exp_sense=None, **shape):
    fd = family_data(fam, L, **shape); d_prop, d_impr, near, recs = nearest_clone(r, fd); cands, wit = witness_search(r, fd)
    d_all, geo, obs = statuses(recs, cands, wit)
    ok_geom = ((exp_nearest is None or near['coset'] == exp_nearest) and (exp_witness is None or (wit or {}).get('coset') == exp_witness)
               and (exp_sense is None or (wit or {}).get('sense') == exp_sense))
    tests.append(dict(test=name, family=fam, shape=json.dumps(fd['params']), r=np.round(r, 4).tolist(), d_proper=d_prop, d_improper=d_impr,
                      nearest=near['coset'], type=near['type'], n_cands=len(cands),
                      witness=(f"{wit['coset']} d={wit['d']:.4f} a={wit['alpha_deg']:.1f} th={wit['theta_deg']:.1f} {wit['sense']}" if wit else None),
                      observational_status=obs, geometric_status=geo, expected=expect_obs,
                      expected_nearest=exp_nearest, expected_witness=exp_witness, expected_sense=exp_sense,
                      pass_obs=(obs == expect_obs), pass_geo=(expect_geo is None or geo == expect_geo), pass_geometry_asserts=ok_geom))
c10 = float(np.cos(np.radians(10.0)))
T('E7_improper_nearest_on_glide_plane', 'E7', 1.0, np.array([0.31, 0.0, 0.5]), 'excluded_by_published_search', exp_nearest='glide_A', exp_witness='glide_A', exp_sense='phased', LAx=0.8, L1y=1.2, L2z=1.2)
T('E7_improper_nearest_off_plane', 'E7', 1.0, np.array([0.31, 0.05, 0.5]), 'excluded_by_published_search', exp_nearest='glide_A', exp_witness='glide_A', exp_sense='phased', LAx=0.8, L1y=1.2, L2z=1.2)
T('E8_improper_nearest_on_plane', 'E8', 1.0, np.array([0.3, 0.0, 0.5]), 'excluded_by_published_search', exp_nearest='glide_A', exp_witness='glide_A', exp_sense='phased', LAx=0.8, LCy=1.2, LBz=1.2)
T('E7_improper_nearest_proper_also_covered', 'E7', 1.0, np.array([0.31, 0.3, 0.5]), 'excluded_by_published_search', exp_nearest='glide_A', exp_witness='glide_A', exp_sense='phased', LAx=0.8, L1y=0.9, L2z=1.2)   # renamed from E7_proper_wins
T('E7_proper_nearest', 'E7', 1.0, np.array([0.31, 0.3, 0.5]), 'excluded_by_published_search', exp_nearest='id', exp_witness='id', exp_sense='anti_phased', LAx=0.8, L1y=0.7, L2z=1.2)             # proper translation 0.7 is nearest
T('threshold_0.984', 'E1', 0.984, np.zeros(3), 'excluded_by_published_search', 'circles_geometrically_present', exp_nearest='id', exp_witness='id', exp_sense='anti_phased')
T('threshold_0.986', 'E1', 0.986, np.zeros(3), 'outside_published_search_domain', 'circles_geometrically_present', exp_nearest='id', exp_witness=None)
T('threshold_1.000', 'E1', 1.000, np.zeros(3), 'no_nondegenerate_circles', 'zero_radius_boundary', exp_nearest='id', exp_witness=None)
T('E2_halfturn_on_axis_small_Lz', 'E2', 1.0, np.array([0.0, 0.0, 0.3]), 'excluded_by_published_search', exp_nearest='halfturn_B', exp_witness='halfturn_B', exp_sense='anti_phased', Lx=1.2, Ly=1.2, Lz=0.9)
T('outside_domain_alpha_lt_10', 'E1', 0.990, np.zeros(3), 'outside_published_search_domain', 'circles_geometrically_present', exp_nearest='id', exp_witness=None)
T('nonidentity_coset_witness_needed', 'E2', 1.0, np.array([0.45, 0.0, 0.2]), 'excluded_by_published_search', exp_nearest='halfturn_B', exp_witness='halfturn_B', exp_sense='anti_phased', Lx=1.3, Ly=1.3, Lz=0.7)
T('threshold_cos10_minus', 'E1', c10 - 1e-9, np.zeros(3), 'excluded_by_published_search', exp_nearest='id', exp_witness='id', exp_sense='anti_phased')
T('threshold_cos10_exact', 'E1', c10, np.zeros(3), 'excluded_by_published_search', exp_nearest='id', exp_witness='id', exp_sense='anti_phased')
T('threshold_cos10_plus', 'E1', c10 + 1e-9, np.zeros(3), 'outside_published_search_domain', exp_nearest='id', exp_witness=None)
tdf = pd.DataFrame(tests)
# Nearest-sufficiency theorem for the Vaudrevange2012-only configuration (audit #5 §6):
#   for the global nearest element g with |g r - r| = d and centre separation theta,  |g^2 r - r| = 2 d sin(theta/2);
#   theta < 60 deg would give a closer clone (contradiction), hence theta_nearest >= 60 deg >= 11 deg.  Therefore:
#   d_nearest <= cos10 -> nearest itself is a covered witness;  d_nearest > cos10 -> every element has alpha < 10 deg.
#   => nearest-element classification == all-element classification.  Verified numerically below.
suff_rows = []; rng3 = np.random.default_rng(23)
suff_cases = [('E7', dict(LAx=0.8, L1y=1.2, L2z=1.2)), ('E2', dict(Lx=1.3, Ly=1.3, Lz=0.7)), ('E7', dict(LAx=1.0, L2x=0.9, L2z=0.01))] + \
             [('E7', dict(LAx=rng3.uniform(0.3, 1.2), L1y=rng3.uniform(0.3, 1.2), L2x=rng3.uniform(-0.8, 0.8), L2z=rng3.uniform(0.1, 1.2))) for _ in range(40)] + \
             [('E2', dict(Lx=rng3.uniform(0.3, 1.3), Ly=rng3.uniform(0.3, 1.3), Lz=rng3.uniform(0.2, 1.3))) for _ in range(30)] + \
             [('E8', dict(LAx=rng3.uniform(0.3, 1.2), LCy=rng3.uniform(0.3, 1.2), LBz=rng3.uniform(0.3, 1.2))) for _ in range(30)]
for fam_s, shp in suff_cases:
    fdx = family_data(fam_s, 1.0, **shp); r = rng3.uniform(0, 1, 3) * 0.5
    d_prop, d_impr, near, recs = nearest_clone(r, fdx); cands, wit = witness_search(r, fdx)
    M_near = [c for c in fdx['cosets'] if c[0] == near['coset']][0][1]
    dn, an, tn, sn = circle_geometry(M_near, np.array(near['t_total']), r)
    g2 = float(np.linalg.norm((M_near @ M_near - I3) @ r + M_near @ np.array(near['t_total']) + np.array(near['t_total'])))
    ident_ok = (tn is None) or abs(g2 - 2 * dn * np.sin(np.radians(tn) / 2)) < 1e-9
    near_class = ('excluded' if (an is not None and covered_by('vaudrevange2012', an, tn, sn)) else ('no_circles' if dn >= THR_GEO - EPS_NUM else 'outside'))
    all_class = {'excluded_by_published_search': 'excluded', 'no_nondegenerate_circles': 'no_circles', 'outside_published_search_domain': 'outside',
                 'not_excluded_by_published_search': 'not_excluded'}[statuses(recs, cands, wit)[2]]
    suff_rows.append(dict(family=fam_s, shape=json.dumps(fdx['params']), d_nearest=dn, theta_nearest=tn, g2_identity_ok=ident_ok,
                          theta_ge_60=(tn is None or tn >= 60.0 - 1e-6), nearest_class=near_class, all_element_class=all_class, agree=(near_class == all_class)))
suff = pd.DataFrame(suff_rows)
G['G_vaudrevange2012_nearest_suffices'] = bool(suff.agree.all() and suff.theta_ge_60.all() and suff.g2_identity_ok.all())
# future-source unit test (non-operational): back-to-back-only sources can need a non-nearest witness
MOCK_BACKTOBACK_SOURCE = dict(alpha_deg=(20.0, 90.0), theta_deg=(180.0 - 1e-6, 180.0), senses=('phased', 'anti_phased'))   # synthetic, not Planck
def _mock_covered(alpha, theta, sense):
    S = MOCK_BACKTOBACK_SOURCE
    return S['alpha_deg'][0] <= alpha <= S['alpha_deg'][1] and S['theta_deg'][0] <= theta <= S['theta_deg'][1] and sense in S['senses']
FUTURE_SOURCE_NONNEAREST = dict(mock_source=MOCK_BACKTOBACK_SOURCE,
                                nearest=dict(alpha=30.0, theta=120.0, covered=_mock_covered(30.0, 120.0, 'anti_phased')),
                                farther=dict(alpha=25.0, theta=180.0, covered=_mock_covered(25.0, 180.0, 'anti_phased')),
                                note='engine-capability unit test with a synthetic back-to-back-only mock source: all-element witness search is '
                                     'retained because such sources can require a non-nearest witness (not used in classification; not a Planck claim)')
G['G_mock_backtoback_nonnearest_unit'] = (FUTURE_SOURCE_NONNEAREST['nearest']['covered'] is False and FUTURE_SOURCE_NONNEAREST['farther']['covered'] is True)
# unit tests: matching-sense mapping and theta boundary of the operational source
_glide = np.diag([1., -1., 1.]); _trans = I3
G['G_matching_sense_mapping'] = (circle_geometry(_trans, np.array([0.8, 0, 0]), np.zeros(3))[3] == 'anti_phased'
                                 and circle_geometry(_glide, np.array([0.8, 0, 0]), np.zeros(3))[3] == 'phased')
G['G_theta_boundary'] = (covered_by('vaudrevange2012', 30.0, 11.0 - 1e-6, 'phased') is False and covered_by('vaudrevange2012', 30.0, 11.0, 'phased') is True
                         and covered_by('vaudrevange2012', 30.0, 11.0 + 1e-6, 'anti_phased') is True and source_boundary('vaudrevange2012', 30.0, 11.0))
G['G_search_sources_verified'] = all(SEARCH_SOURCES[k]['verified'] for k in OPERATIONAL)
G['G_critical_branch_tests'] = bool(tdf.pass_obs.all() and tdf.pass_geo.all() and tdf.pass_geometry_asserts.all())
# certified CVP vs Babai/width and BFS on the audit counterexample (strongly tilted E7)
fd_ce = family_data('E7', 1.0, LAx=1.0, L2x=0.9, L2z=0.01)
d_cert, n_cert, v_cert = cvp_certified(np.zeros(3), fd_ce['lattice'], exclude_zero=True)
def babai_width(w, B, width, exclude_zero):
    c = np.linalg.solve(B, -w); c0 = np.round(c); best = np.inf
    for dlt in itertools.product(range(-width, width + 1), repeat=3):
        n = c0 + np.array(dlt)
        if exclude_zero and np.all(n == 0): continue
        best = min(best, np.linalg.norm(w + B @ n))
    return best
d_w2 = babai_width(np.zeros(3), fd_ce['lattice'], 2, True); d_w4 = babai_width(np.zeros(3), fd_ce['lattice'], 4, True)
brute = min(np.linalg.norm(fd_ce['lattice'] @ np.array(n)) for n in itertools.product(range(-60, 61), repeat=3) if n != (0, 0, 0))
CE = dict(shape=fd_ce['params'], certified=d_cert, certified_n=[int(x) for x in n_cert], babai_w2=d_w2, babai_w4=d_w4, brute_force_pm60=brute,
          audit_value=0.13453624047073684)
G['G_cvp_counterexample'] = bool(abs(d_cert - brute) < 1e-12 and abs(d_cert - CE['audit_value']) < 1e-9)
# CVP certification battery on random tilted shapes: residual recomputation + guaranteed-box complete cross-check
rng = np.random.default_rng(3); cert_rows = []
for i in range(200):
    fd_r = family_data('E7', 1.0, LAx=rng.uniform(0.3, 1.5), L1y=rng.uniform(0.3, 1.5), L2x=rng.uniform(-1.0, 1.0), L2z=rng.uniform(0.05, 1.5))
    w = rng.uniform(-1, 1, 3)
    d1, n1, _ = cvp_certified(w, fd_r['lattice'])
    c = cvp_certification(w, fd_r['lattice'], d1, n1)
    cert_rows.append(dict(case=i, d=d1, **c))
cert = pd.DataFrame(cert_rows)
# enumerate_within completeness: compare the d<1 candidate set with a complete guaranteed-box scan (|n-c|_2 <= 1/sigma_min)
def box_candidates(w, B, radius):
    sv = np.linalg.svd(B, compute_uv=False); c = np.linalg.solve(B, -w); rad = radius / sv[-1] + 1e-9
    lo = np.floor(c - rad).astype(int); hi = np.ceil(c + rad).astype(int); out = set()
    for n0 in range(lo[0], hi[0] + 1):
        for n1 in range(lo[1], hi[1] + 1):
            for n2 in range(lo[2], hi[2] + 1):
                nn = (n0, n1, n2)
                if np.linalg.norm(w + B @ np.array(nn)) < radius - EPS_NUM: out.add(nn)
    return out
comp_rows = []; rng2 = np.random.default_rng(11)
shapes = [family_data('E7', 1.0, LAx=0.8, L1y=1.2, L2z=1.2), family_data('E2', 1.0, Lx=1.3, Ly=1.3, Lz=0.7), fd_ce] + \
         [family_data('E7', 1.0, LAx=rng2.uniform(0.3, 1.2), L1y=rng2.uniform(0.3, 1.2), L2x=rng2.uniform(-0.8, 0.8), L2z=rng2.uniform(0.1, 1.2)) for _ in range(40)] + \
         [family_data('E2', 1.0, Lx=rng2.uniform(0.3, 1.3), Ly=rng2.uniform(0.3, 1.3), Lz=rng2.uniform(0.2, 1.3)) for _ in range(30)] + \
         [family_data('E8', 1.0, LAx=rng2.uniform(0.3, 1.2), LCy=rng2.uniform(0.3, 1.2), LBz=rng2.uniform(0.3, 1.2)) for _ in range(30)]
for i, fdx in enumerate(shapes):
    r = rng2.uniform(0, 1, 3) * 0.5
    for cid, M, v in fdx['cosets']:
        w = (M - I3) @ r + v
        enum = enumerate_within(w, fdx['lattice'], THR_GEO, exclude_zero=(cid == 'id'))
        S1 = {tuple(int(z) for z in n) for d, n, t in enum if d < THR_GEO - EPS_NUM}
        S2 = box_candidates(w, fdx['lattice'], THR_GEO) - ({(0, 0, 0)} if cid == 'id' else set())
        resid = max([abs(d - np.linalg.norm(w + fdx['lattice'] @ n)) for d, n, t in enum], default=0.0)
        comp_rows.append(dict(shape=i, coset=cid, n_enum=len(S1), n_box=len(S2), equal=(S1 == S2), no_duplicates=(len(S1) == len([1 for d, n, t in enum if d < THR_GEO - EPS_NUM])),
                              max_residual=float(resid), set_hash=hashlib.sha256(json.dumps(sorted(S1)).encode()).hexdigest()[:16]))
comp = pd.DataFrame(comp_rows)
G['G_enumerate_within_complete'] = bool(comp.equal.all() and comp.no_duplicates.all() and comp.max_residual.max() < 1e-9)
G['G_cvp_residual'] = bool(cert.residual_ok.all())
G['G_cvp_guaranteed_box'] = bool(cert[cert.box_checked].box_ok.all()) and int((~cert.box_checked).sum()) == 0
cert_ce = cvp_certification(np.zeros(3), fd_ce['lattice'], d_cert, n_cert); CE['certification'] = cert_ce
G['G_cell_battery'] = all(v['cell_battery']['volume_identity'] and v['cell_battery']['idempotence_frac'] == 1.0
                          and v['cell_battery']['orbit_equivalence_frac'] == 1.0 and v['cell_battery']['boundary_ok_frac'] == 1.0
                          for v in fam_rec.values() if v['cell_battery'])
# pilot separation gate in reduced coordinates
SEP = {fam: dict(points=PILOTS[fam], min_pairwise=float(min(quotient_dist(fam, a, b) for a, b in itertools.combinations(PILOTS[fam], 2))),
                 required=PILOT[fam]['min_sep']) for fam in PILOTS}
G['G_pilot_separation'] = all(v['min_pairwise'] >= v['required'] for v in SEP.values())

# ============================================================ outputs
df.to_csv(os.path.join(OUT, 'a7_circle_geometry.csv'), index=False)
tdf.to_csv(os.path.join(OUT, 'a7_critical_branch_tests.csv'), index=False)
json.dump(dict(L_LSS_Mpc=L_LSS_MPC, thresholds=dict(search=THR_SEARCH, geometric=THR_GEO, eps_num=EPS_NUM), families=fam_rec,
               cvp=dict(method='LLL + Gram-Schmidt complete sphere enumeration (Fincke-Pohst), float64', counterexample=CE,
                        certification_battery=dict(n=200, residual_all_ok=bool(cert.residual_ok.all()), box_all_checked=int(cert.box_checked.sum()),
                                                   box_all_ok=bool(cert[cert.box_checked].box_ok.all()), max_cond=float(cert['cond'].max())),
                        name='complete sphere enumeration in float64 with independent certification battery')),
          open(os.path.join(OUT, 'a6_generators.json'), 'w'), indent=1)
json.dump(dict(version='pilot_v2_reduced', label='generic interior pilot in family-specific reduced physical coordinates (NOT a uniform prior; '
                        'representative pilot, not a marginalization)', seed_sequence=SEED,
               reduced_coordinates={'E2': '(x/Lx mod 1, y/Ly mod 1) modulo half-turn p->-p; quotient distance min over sign and integer shifts',
                                    'E7': 'eta_y = dist(y, (L1y/2)Z)/L1y in [0,1/4] (glide planes at y=0 and y=L1y/2)',
                                    'E8': 'eta_x = dist(x, LAx Z)/LAx in [0,1/2]; eta_y = dist(y, (LCy/2)Z)/LCy in [0,1/4]'},
               selection_rule={f: dict(box=PILOT[f]['box'], min_sep=PILOT[f]['min_sep'], exclude=PILOT[f]['exclude_text'],
                                       min_sep_meaning='anti-duplication design constraint (not a coverage guarantee)') for f in PILOT},
               pilot_quality={f: dict(maximin=SEP[f]['min_pairwise']) for f in PILOT},
               points=SEP, anchors=ANCHORS, lift_rule='irrelevant coordinates fixed at generic fractions (0.31, 0.37, 0.42)',
               archived=dict(pilot_v1='a6a7_v1.1 (unit-cube design; superseded)')),
          open(os.path.join(OUT, 'a6_observer_design_points.json'), 'w'), indent=1)
bridge = dict(general_equivalence='(I - M)(x0_CT + r_obs) = 0  for every generator M', canonical_gauge='x0_CT = -r_obs (registered choice)',
              kernel_freedom='E7 reflection: plane-parallel components; E2 half-turn: axis direction; E8: per-plane',
              derivation=('A6 convention: g(x)=Mx+v, observer at r, clone displacement g(r)-r=(M-I)r+v. '
              'CMBtopology/Part IIb convention: g(x)=M(x-x0)+T+x0, observer at the origin, clone displacement (I-M)x0+T. '
              'With the same (M,T=v) the two agree iff (I-M)(x0_CT + r_obs) = 0; x0_CT = -r_obs is the canonical gauge.'),
              status='REGISTERED - BLOCKER until A11 numerical verification (several families/observers/shapes: r_obs -> canonical x0_CT -> '
                     'CMBtopology generator/covariance vs A6 displacement; compare perpendicular and normal components and the covariance)',
              symbols=dict(r_obs='observer location in special-origin covering coordinates (A6)', x0_CT='CMBtopology generator-origin parameter'))
cert.to_csv(os.path.join(OUT, 'a7_cvp_certification_battery.csv'), index=False)
comp.to_csv(os.path.join(OUT, 'a7_enumeration_completeness_battery.csv'), index=False)
suff.to_csv(os.path.join(OUT, 'a7_nearest_sufficiency_battery.csv'), index=False)
prov = dict(script=os.path.basename(__file__), script_sha256=sha(os.path.abspath(__file__)),
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(), date=str(datetime.date.today()),
            nearest_sufficiency_theorem='For a non-trivial global nearest deck transformation g in a torsion-free Bieberbach group (so g^2 is not the identity), '
                                        '|g^2 r - r| = |a - b| = 2 d sin(theta/2); theta < 60 deg would give a closer clone, hence theta_nearest >= 60 deg. '
                                        'Under the Vaudrevange2012-only operational configuration (alpha>=10, theta>=11, both senses) nearest-element and '
                                        'all-element classifications coincide (verified numerically: a7_nearest_sufficiency_battery.csv)',
            future_source_nonnearest_unit=FUTURE_SOURCE_NONNEAREST, thresholds_note=dict(reported_0p985='published rounded distance limit', operational=f'd <= cos(10 deg) = {c10:.9f}'),
            cmbtopology=dict(commit='0cc65e34f03df85e92f738686bff0a476132f337', src_sha=CT_SRC_SHA),
            references={'COMPACT_I': dict(arxiv='2211.02603v4', journal='JCAP 01 (2023) 030', doi='10.1088/1475-7516/2023/01/030'),
                        'COMPACT_IIb': dict(arxiv='2510.05030v1', journal='(journal citation not yet confirmed)'),
                        'COMPACT_Ib': dict(status='in preparation (cited as such in arXiv:2606.24886, 2026-06)'),
                        'Vaudrevange2012': dict(arxiv='1206.2939', journal='PRD 86 (2012) 083526')},
            x0_bridge=bridge, search_sources=SEARCH_SOURCES, gates=G,
            outputs={f: sha(os.path.join(OUT, f)) for f in ['a7_circle_geometry.csv', 'a7_critical_branch_tests.csv', 'a7_cvp_certification_battery.csv', 'a7_enumeration_completeness_battery.csv', 'a7_nearest_sufficiency_battery.csv', 'a6_generators.json', 'a6_observer_design_points.json']},
            versions=dict(python=sys.version.split()[0], numpy=np.__version__, pandas=pd.__version__, platform=__import__('platform').platform(),
                          blas_lapack=str({k: v for k, v in np.show_config(mode='dicts').get('Build Dependencies', {}).items() if k in ('blas', 'lapack')})))
OFFICIAL = all(v is True for v in G.values()); prov['OFFICIAL'] = OFFICIAL
json.dump(prov, open(os.path.join(OUT, 'a6a7_provenance.json'), 'w'), indent=1)
print('gates:', G)
assert OFFICIAL, G
print('counterexample:', {k: (round(v, 6) if isinstance(v, float) else v) for k, v in CE.items()})
print(prim.groupby(['family', 'L']).observational_status.first().unstack().to_string())
print(tdf[['test', 'd_proper', 'd_improper', 'witness', 'observational_status', 'pass_obs', 'pass_geo']].to_string(index=False, float_format=lambda v: f'{v:.4f}'))
print('pilots (reduced):', {f: [[round(x, 4) for x in p] for p in v['points']] for f, v in SEP.items()}, {f: round(v['min_pairwise'], 4) for f, v in SEP.items()})
print('saved to', OUT)
