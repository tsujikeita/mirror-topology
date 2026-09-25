# ---- 5. 橋渡し検証 ----
def rel(A, B): return float(np.linalg.norm(A - B) / np.linalg.norm(B))
def rel_off(A, B): o = lambda X: X - np.diag(np.diag(X)); return float(np.linalg.norm(o(A) - o(B)) / max(np.linalg.norm(o(B)), 1e-300))
def rel_white(A, B):
    d = np.diag(B); assert np.all(d > 0), 'white metric: non-positive diagonal'; s = 1 / np.sqrt(d); return float(np.linalg.norm((A - B) * np.outer(s, s)) / np.linalg.norm(B * np.outer(s, s)))
TOL_MATCH, TOL_DISCR = 1e-5, 1e-2; rows = []
for c in CASES:
    C0 = get(c['topology'], c['shape'], c['base']); target = D_of(c['M']) @ C0 @ D_of(c['M']).T; C1 = get(c['topology'], c['shape'], c['x0_H1'])
    C2 = get(c['topology'], c['shape'], c['x0_H2']) if A11_MODE == 'official' else None
    row = dict(case=c['case'], topology=c['topology'], gen=c['gen'], structurally_forced_same=c['structurally_forced_same'], candidate_for_discrimination=c['candidate_for_discrimination'],
               old_predicate_2T_in_Lambda_SUPERSEDED_DIAGNOSTIC=c['old_predicate_2T_in_Lambda_SUPERSEDED_DIAGNOSTIC'], rel_H1=rel(C1, target), off_H1=rel_off(C1, target), white_H1=rel_white(C1, target),
               rel_H2=(rel(C2, target) if C2 is not None else np.nan), off_H2=(rel_off(C2, target) if C2 is not None else np.nan), white_H2=(rel_white(C2, target) if C2 is not None else np.nan),
               rel_H1_vs_H2=(rel(C1, C2) if C2 is not None else np.nan), base_tag=tag_of(c['topology'], c['shape'], c['base'])[:20], H1_tag=tag_of(c['topology'], c['shape'], c['x0_H1'])[:20],
               H2_tag=(tag_of(c['topology'], c['shape'], c['x0_H2'])[:20] if C2 is not None else None))
    row['empirically_discriminating'] = (row['rel_H1_vs_H2'] > TOL_DISCR) if C2 is not None else None
    row['match_over_separation_H1'] = (row['rel_H1'] / max(row['rel_H1_vs_H2'], 1e-300)) if C2 is not None else np.nan
    rows.append(row)
for c in INV:
    C0 = get(c['topology'], c['shape'], c['base']); C1 = get(c['topology'], c['shape'], c['x0'])
    rows.append(dict(case=c['case'], topology=c['topology'], gen=c['kind'], structurally_forced_same=None, candidate_for_discrimination=None, old_predicate_2T_in_Lambda_SUPERSEDED_DIAGNOSTIC=None, rel_H1=rel(C1, C0), off_H1=rel_off(C1, C0), white_H1=rel_white(C1, C0), rel_H2=np.nan, off_H2=np.nan, white_H2=np.nan,
                     rel_H1_vs_H2=np.nan, empirically_discriminating=None, match_over_separation_H1=np.nan, base_tag=tag_of(c['topology'], c['shape'], c['base'])[:20], H1_tag=tag_of(c['topology'], c['shape'], c['x0'])[:20], H2_tag=None))
df = pd.DataFrame(rows); df['H1_match'] = df.rel_H1 < TOL_MATCH; df['H2_match'] = df.rel_H2 < TOL_MATCH
disc = df[df.candidate_for_discrimination.eq(True)]; nond = df[df.structurally_forced_same.eq(True)]; lat = df[df.gen.str.endswith('lattice_translation')]
kern = df[df.gen.str.endswith(('invariant_plane_shift', 'kernel_shift'))]; ctrl = df[df.gen.eq('y_dependence_control')]; halfp = df[df.gen.eq('E7_covariance_half_period')]
GATES['G_case_inventory'] = bool(set(disc.case) == EXPECTED['candidates'] and set(nond.case) == EXPECTED['forced_same'] and set(lat.case) == EXPECTED['lat_cases'] and set(kern.case) == EXPECTED['kernel_cases'] and set(ctrl.case) == EXPECTED['ctrl'] and set(halfp.case) == EXPECTED['half_period'] and len(df) == EXPECTED['n_rows'])
assert GATES['G_case_inventory'], (set(disc.case), set(nond.case), set(lat.case), set(kern.case), set(ctrl.case), set(halfp.case), len(df))
if A11_MODE == 'official':
    H1m, H2m = disc.H1_match.eq(True).all(), disc.H2_match.eq(True).all(); H1f, H2f = (disc.rel_H1 > TOL_DISCR).all(), (disc.rel_H2 > TOL_DISCR).all(); sep = disc.empirically_discriminating.eq(True).all()
    G_H1 = bool(H1m and H2f and sep); G_H2 = bool(H2m and H1f and sep)
    CONVENTION = 'x0_CT = -r_obs (H1, registered canonical gauge)' if G_H1 else 'x0_CT = +r_obs (H2)' if G_H2 else 'UNRESOLVED'
    TOL_EQUAL = 1e-5
    GATES['G_convention_H1'] = G_H1
    GATES['G_forced_same_both_match'] = bool(nond.H1_match.eq(True).all() and nond.H2_match.eq(True).all() and (nond.rel_H1_vs_H2 < TOL_EQUAL).all())   # structurally forced same
    GATES['G_forced_same_implies_not_discriminating'] = bool(nond.empirically_discriminating.eq(False).all())                                      # necessary direction of the predicate
    GATES['G_candidates_empirically_discriminating'] = bool(disc.empirically_discriminating.eq(True).all())                                        # registered expectation for these candidate cases (incl. prediction B)
    GATES['G_E7_covariance_half_period'] = bool(halfp.H1_match.eq(True).all() and len(halfp) == 1)                                             # new prediction (a)
    for nm in ['E7', 'E7tilt', 'E8', 'E2']:
        sub = lat[lat.gen.eq(f'{nm}_lattice_translation')]; GATES[f'G_{nm}_lattice_translation_invariance_all_basis'] = bool(sub.H1_match.eq(True).all() and len(sub) == 3)
    for nm in ['E7_invariant_plane_shift', 'E7tilt_invariant_plane_shift', 'E8_kernel_shift', 'E2_kernel_shift']:
        sub = kern[kern.gen.eq(nm)]; GATES[f'G_{nm}'] = bool(sub.H1_match.eq(True).all() and len(sub) >= 1)
    GATES['G_y_dependence_control'] = bool((ctrl.rel_H1 > TOL_DISCR).all() and len(ctrl) == 1)
else:
    CONVENTION = 'smoke (H1 only): ' + ('H1 match' if bool(disc.H1_match.eq(True).all()) else 'H1 mismatch'); GATES['G_smoke_H1_match'] = bool(disc.H1_match.eq(True).all())
print(df[['case', 'gen', 'structurally_forced_same', 'rel_H1', 'rel_H2', 'rel_H1_vs_H2', 'white_H1', 'H1_match', 'H2_match', 'empirically_discriminating']].to_string(index=False, float_format=lambda v: f'{v:.2e}'))
print('\n判定:', CONVENTION)