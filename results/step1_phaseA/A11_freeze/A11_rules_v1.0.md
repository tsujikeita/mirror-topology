# A11 rules v1.0 — CMBtopology x₀ convention bridge (registered; frozen with tag step1-phaseA-A11-freeze-v1.0)
Established by MirrorTopology_Step1_A11_x0bridge_v1.4.1.ipynb (origin/main 104d5912, source-only SHA c1f3a362…), official run 2026-09-07 (STATUS=OFFICIAL, 47/47 gates).

## R1. Observer convention
A6 convention: deck transformations g(x) = M x + T in special-origin covering coordinates; observer at r_obs.
CMBtopology parameter x0 (units L_LSS): **x0_CT = −r_obs** (canonical gauge). General equivalence: (I − M)(x0_CT + r_obs) = 0 for every generator M.
Established for E2 (half-turn), E7 (glide), E8 (two glides) with LAy≠0 / LBx≠0 shapes; Step 1 passes A6 pilot observer positions (reduced coordinates, pilot v2) to CMBtopology as x0 = −r_obs.

## R2. Clone relation (verified to ~8e-8 relative Frobenius, 5 structurally identifiable cases)
C(g r) = D(M) C(r) D(M)ᵀ, where D(M) is the A9 Euler-angle-convention-independent quadrature representation on the frozen real basis (t2b2_bridge, E = conj(M21)·Y_c), active convention: (D x) are the coefficients of T(M⁻¹p). Valid for improper M.

## R3. Observer dependence of the covariance
C depends on x0 only through (I − Hᵀ) x0 mod Λ for every holonomy element H (relative phase of the eigenmode components; overall phases cancel in ξξ†). Consequences (all verified ≤ 1e-15): invariance under lattice translations (all basis vectors), invariance under kernel-direction shifts (E7: x,z; E8: z; E2: z), E7 covariance y-period = L1y/2 (prospective prediction A: 6e-16).

## R4. Identifiability predicate (supersedes the v1.3.1 predicate 2T ∈ Λ, kept as SUPERSEDED_DIAGNOSTIC)
For a generator (M,T): H1/H2 images differ by 2T. `structurally_forced_same` iff (I − Hᵀ)(2T) ∈ Λ for all holonomy H; otherwise `candidate_for_discrimination`; `empirically_discriminating` from data. Predicate computed on the A6 route and the CT-source route and required to agree. Prospective prediction B (E7tilt LAy=0.30: candidate) confirmed: rel_H1 = 8e-8, rel_H2 = 0.21.

## R5. Tolerances and gates (fixed)
match: rel < 1e-5; discriminate: rel > 1e-2; forced-same equality: rel_H1_vs_H2 < 1e-5. Candidate cases: H1 match ∧ rel_H2 > 1e-2 ∧ separation > 1e-2. Forced-same cases: both match ∧ equality.

## R6. Environment and provenance
CMBtopology 0cc65e34 (pinned, reset --hard, clean incl. untracked, requirements.txt pinned, run in tag-specific scratch); mirror-topology dependency commit efa23136 (t1_engine 87bf8424…, t2b2_bridge 45107d16…, t2b2_run 03c80f21…, A6 artifact 661ed0b0…); environment lock a11_env_lock_v2 (Python 3.13.15, numpy 2.1.3, scipy 1.16.3, healpy 1.20.0, camb 2.0.4, numba 0.61.2, quaternionic 1.0.17, spherical 1.1.4, pandas 2.2.3, matplotlib 3.10.0, tqdm 4.67.3; x86_64; scipy-openblas); env fingerprint in every cache key. Covariance intake through t1_engine.load_cov_full (symmetry projection, PSD, two-point gates). Smoke → lock → official evidence chain (G_smoke_provenance_chain).

## R7. History (not relabelled)
v1.3.1 official (2026-09-07): 41 required gates, 40 True, G_convention_H1 False → status FAILED / conclusion UNRESOLVED, kept as is (v1.3.1_FAILED/). Cause: wrong identifiability predicate. 35 covariances reused in v1.4.1 after byte-level verification (parent provenance 381620f1…, CSV 1095b5d8…).

## R8. Scope
Establishes the observer-coordinate convention and observer-equivalence structure for the registered E2/E7/E8 shapes, observers and generators. It is not a statement about the observational viability of any topology model.
