# ---- 3. 二経路の生成子：A6 凍結 artifact（AST 抽出） vs pinned CMBtopology ソース（抽出） ----
_a6src = open(A6_SCRIPT).read(); _fn = [n for n in ast.parse(_a6src).body if isinstance(n, ast.FunctionDef) and n.name == 'family_data'][0]
_ns = {'np': np, 'I3': I3}; exec(ast.get_source_segment(_a6src, _fn), _ns); family_data_A6 = _ns['family_data']
def gens_A6(top, p):
    fd = family_data_A6(top, 1.0, **{k: v for k, v in p.items() if k not in ('alpha', 'beta', 'gamma')}) if top != 'E2' else family_data_A6('E2', 1.0, Lx=p['Lx'], Ly=p['Ly'], Lz=p['Lz'])
    return {cid: (M, v) for cid, M, v in fd['cosets'] if cid != 'id'}, fd['lattice']
def gens_CT(top, p):
    """CMBtopology side, extracted from the pinned source files (independent of A6)."""
    src = open(os.path.join(CT_DIR, 'topology', 'src', f'{top}.py')).read().replace('\r', '')
    out = {}
    if top in ('E7', 'E8'):
        Ms = {m.group(1): np.array(eval(m.group(2), {'np': np}), float) for m in re.finditer(r'M_([A-Z])\s*=\s*(np\.diag\(\[[^\]]*\]\))', src)}
        Ts = {}
        for m in re.finditer(r'T_([A-Z])\s*=\s*np\.array\(\[([^\]]*)\]\)', src):
            Ts[m.group(1)] = np.array(eval('[' + m.group(2) + ']', {**{k: float(v) for k, v in p.items()}}), float)
        for k in Ms: out[f'glide_{k}'] = (Ms[k], Ts[k])
    else:
        m = re.search(r'T_B\s*=\s*L_z\s*\*\s*np\.array\(\[([^\]]*)\]\)', src); assert m, 'E2 T_B not found'
        from math import cos, sin, pi
        beta, gamma = p['beta'] * pi / 180, p['gamma'] * pi / 180
        T_B = p['Lz'] * np.array(eval('[' + m.group(1) + ']', {'cos': cos, 'sin': sin, 'beta': beta, 'gamma': gamma}), float)
        # half-turn: phase factor exp(2i(k_x x0_x + k_y x0_y)) exp(i k.T_B) = exp(-i k.(M x0 - T_B)) with M = diag(-1,-1,1)
        assert re.search(r'2\*1j\*\(k_x\*x0\[0\]\s*\+\s*k_y\*x0\[1\]\)', src), 'E2 half-turn phase pattern not found'
        out['halfturn_B'] = (np.diag([-1., -1., 1.]), T_B)
    return out
def E7_shape(LAx=1.0, LAy=0.3, L1y=1.0, L2x=0.0, L2z=1.0): return dict(LAx=LAx, LAy=LAy, L1y=L1y, L2x=L2x, L2z=L2z)
def E8_shape(LAx=1.0, LAy=0.3, LBx=0.2, LBz=1.0, LCy=1.0): return dict(LAx=LAx, LAy=LAy, LBx=LBx, LBz=LBz, LCy=LCy)
def E2_shape(Lx=1.0, Ly=1.0, Lz=1.0): return dict(Lx=Lx, Ly=Ly, Lz=Lz, alpha=90.0, beta=90.0, gamma=0.0)
b1 = np.array([0.31, 0.21, 0.42]); b2 = np.array([0.13, 0.44, 0.27]); p7, p7t, p8, p2 = E7_shape(), E7_shape(LAy=0.25, L2x=0.5), E8_shape(), E2_shape(); p7t3 = E7_shape(LAy=0.3, L2x=0.5)
CASES = []; bind_M = bind_T = 0.0
for cid, top, p, b, g in [('E7_b1_A', 'E7', p7, b1, 'glide_A'), ('E7_b2_A', 'E7', p7, b2, 'glide_A'), ('E7tilt_b1_A', 'E7', p7t, b1, 'glide_A'),
                          ('E8_b1_A', 'E8', p8, b1, 'glide_A'), ('E8_b1_B', 'E8', p8, b1, 'glide_B'), ('E2_b1_B', 'E2', p2, b1, 'halfturn_B'),
                          ('E7tilt3_b1_A', 'E7', p7t3, b1, 'glide_A')]:   # v1.4 new prediction (b): LAy=0.3 -> (I-M)2T=(0,1.2,0) not in Lambda -> discriminating
    gA6, LamA6 = gens_A6(top, p); MA6, TA6 = gA6[g]; MCT, TCT = gens_CT(top, p)[g]
    bind_M = max(bind_M, np.abs(MA6 - MCT).max()); bind_T = max(bind_T, np.abs(TA6 - TCT).max())
    r = -b; dA6 = (MA6 - I3) @ r + TA6; dCT = (I3 - MCT) @ b + TCT                 # two independent sources
    U_, S_, Vt = np.linalg.svd(MA6 - I3); ker = Vt[S_ < 1e-9].T; Ppar = ker @ ker.T if ker.size else np.zeros((3, 3)); Pperp = I3 - Ppar
    def in_lattice(v, Lam, atol=1e-9):
        coeff = np.linalg.solve(Lam, v); return bool(np.allclose(coeff, np.rint(coeff), atol=atol, rtol=0.0))
    delta_x0 = (MCT @ b + TCT) - (MCT @ b - TCT)                                   # = 2 T_CT
    HOL_A6 = [I3] + [Mh for Mh, _ in gA6.values()]; HOL_CT = [I3] + [Mh for Mh, _ in gens_CT(top, p).values()]
    forced_A6 = all(in_lattice((I3 - H.T) @ delta_x0, LamA6) for H in HOL_A6)     # covariance depends on x0 via (I-H^T)x0 mod Lambda for every holonomy element
    forced_CT = all(in_lattice((I3 - H.T) @ (2 * TA6), LamA6) for H in HOL_CT)    # same predicate with CT-extracted holonomy matrices (lattice from A6)
    old_2T_in_lattice = in_lattice(2 * TA6, LamA6)                                 # v1.3.1 predicate: SUPERSEDED_DIAGNOSTIC
    CASES.append(dict(case=cid, topology=top, shape=p, base=b, gen=g, M=MA6, T=TA6, lattice=LamA6, structurally_forced_same=forced_A6, structurally_forced_same_CT=forced_CT,
                      candidate_for_discrimination=(not forced_A6), old_predicate_2T_in_Lambda_SUPERSEDED_DIAGNOSTIC=old_2T_in_lattice, x0_H1=MCT @ b - TCT, x0_H2=MCT @ b + TCT,
                      dpar_err=float(np.abs(Ppar @ (dA6 - dCT)).max()), dperp_err=float(np.abs(Pperp @ (dA6 - dCT)).max()), dpar_norm=float(np.linalg.norm(Ppar @ dA6)), dperp_norm=float(np.linalg.norm(Pperp @ dA6))))
GATES['G_a6_ct_M_binding'] = bool(bind_M < 1e-12); GATES['G_a6_ct_T_binding'] = bool(bind_T < 1e-12)
GATES['G_displacement_parallel_independent'] = bool(all(c['dpar_err'] < 1e-12 for c in CASES)); GATES['G_displacement_perpendicular_independent'] = bool(all(c['dperp_err'] < 1e-12 for c in CASES))
GATES['G_displacement_components_excited'] = bool(all(c['dpar_norm'] > 1e-6 and c['dperp_norm'] > 1e-6 for c in CASES))
GATES['G_predicate_A6_CT_binding'] = bool(all(c['structurally_forced_same'] == c['structurally_forced_same_CT'] for c in CASES))
assert all(GATES[k] for k in ['G_a6_ct_M_binding', 'G_a6_ct_T_binding', 'G_displacement_parallel_independent', 'G_displacement_perpendicular_independent', 'G_displacement_components_excited', 'G_predicate_A6_CT_binding']), (bind_M, bind_T)
def lat_of(top, p): return gens_A6(top, p)[1]
INV = []
for top, p, nm in [('E7', p7, 'E7'), ('E7', p7t, 'E7tilt'), ('E8', p8, 'E8'), ('E2', p2, 'E2')]:
    L = lat_of(top, p)
    for j in range(3): INV.append(dict(case=f'{nm}_b1_lat{j}', topology=top, shape=p, base=b1, x0=b1 + L[:, j], kind=f'{nm}_lattice_translation'))
INV += [dict(case='E7_b1_xshift', topology='E7', shape=p7, base=b1, x0=b1 + np.array([0.2, 0., 0.]), kind='E7_invariant_plane_shift'),
        dict(case='E7_b1_zshift', topology='E7', shape=p7, base=b1, x0=b1 + np.array([0., 0., 0.15]), kind='E7_invariant_plane_shift'),
        dict(case='E7tilt_b1_xshift', topology='E7', shape=p7t, base=b1, x0=b1 + np.array([0.2, 0., 0.]), kind='E7tilt_invariant_plane_shift'),
        dict(case='E8_b1_zshift', topology='E8', shape=p8, base=b1, x0=b1 + np.array([0., 0., 0.15]), kind='E8_kernel_shift'),
        dict(case='E2_b1_zshift', topology='E2', shape=p2, base=b1, x0=b1 + np.array([0., 0., 0.15]), kind='E2_kernel_shift'),
        dict(case='E7_b1_yshift', topology='E7', shape=p7, base=b1, x0=b1 + np.array([0., 0.12, 0.]), kind='y_dependence_control'),
        dict(case='E7_b1_y_half_period', topology='E7', shape=p7, base=b1, x0=b1 + np.array([0., 0.5 * p7['L1y'], 0.]), kind='E7_covariance_half_period')]   # v1.4 new prediction (a): (I-M)t=(0,L1y,0) in Lambda -> invariant
EXPECTED = dict(candidates={'E7_b1_A', 'E7_b2_A', 'E8_b1_A', 'E8_b1_B', 'E7tilt3_b1_A'}, forced_same={'E2_b1_B', 'E7tilt_b1_A'}, lat_cases={f'{nm}_b1_lat{j}' for nm in ['E7', 'E7tilt', 'E8', 'E2'] for j in range(3)},
                kernel_cases={'E7_b1_xshift', 'E7_b1_zshift', 'E7tilt_b1_xshift', 'E8_b1_zshift', 'E2_b1_zshift'}, ctrl={'E7_b1_yshift'}, half_period={'E7_b1_y_half_period'}, n_rows=26, n_unique_cov=39)
if A11_MODE == 'smoke':
    CASES = [c for c in CASES if c['case'] == 'E7_b1_A']; INV = []; EXPECTED = dict(candidates={'E7_b1_A'}, forced_same=set(), lat_cases=set(), kernel_cases=set(), ctrl=set(), half_period=set(), n_rows=1, n_unique_cov=3)
print('binding: M', f'{bind_M:.1e}', 'T', f'{bind_T:.1e}', '| displacement gates:', GATES['G_displacement_parallel_independent'], GATES['G_displacement_perpendicular_independent'])
for c in CASES: print(f"  {c['case']:13s} forced_same={c['structurally_forced_same']} (old 2T-in-Lambda={c['old_predicate_2T_in_Lambda_SUPERSEDED_DIAGNOSTIC']}) x0_H1={np.round(c['x0_H1'],3).tolist()} x0_H2={np.round(c['x0_H2'],3).tolist()}")