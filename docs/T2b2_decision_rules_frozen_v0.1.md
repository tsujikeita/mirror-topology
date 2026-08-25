# T2b-2 Decision Rules — Frozen Pre-registration Draft v0.1
2026-08-25. Public commit target for the `mirror-topology` repository (Theme T, Pillar 2, Stage III:
post-transfer sign of the quadratic twisted-sector imprint). This document supersedes the internal
Japanese draft of 2026-08-24; the notebook `MirrorTopology_T2b2_signmap_v0.1.ipynb` writes an
equivalent machine-readable record (`t2b2_decision_rules_v0_1.json`, including the SHA-256 of the
analysis core) to the run directory. Following the tail-lottery protocol, this document and the
notebook are to be committed **before** the production grid is executed.

## 0. Scope and context

This registration fixes, in advance, how the production parameter grid will be evaluated when
asking: *can the mirror asymmetry sourced by a quadratic (self-paired) twisted-sector scalar on the
non-orientable flat manifold E7 acquire the observed sign after full CMB transfer?* Local
(Sachs–Wolfe, all-multipole) positivity is protected by the no-imprint theorem of Pillar-2 Note
v0.4; the band-limited statistic (l = 2–4) and the post-transfer statistic are not, which is why
this numerical map exists.

Conventions. Lengths are in units of chi_* (comoving radius of the last-scattering sphere) = 1.
The observer sits at the origin; the frozen mirror is the y = 0 plane through the observer.
E7 generators: the glide reflection g_A: x -> M_A x + T_A with M_A = diag(1,-1,1),
T_A = (L_Ax, L_Ay, 0), g_A^2 = t_(2L_Ax,0,0), plus translations t_1 = (0, L_1y, 0) and
t_2 = (0, 0, L_2z); H_1(E7) = Z + Z + Z_2. Twisted sectors are labeled by real characters
sigma = (sigma_A, sigma_1, sigma_2) in {+-1}^3, excluding the trivial sector.

**Sign convention: A > 0 is the mirror-symmetric side (the direction produced by all ordinary
scalars in Pillar 1); A < 0 is the observed-sign side.**

## 1. Primary statistic (the only quantity used for the decisions)

For each grid point (geometry, sigma):

- **A_band,inf** — the internal-cutoff-extrapolated value (Sec. 3) of the band sum (l = 2–4) of the
  y-mirror statistic A = (1/4pi) * sum_{l,m} (-1)^m C_{lm, l,-m}, computed with the **full transfer
  function** (CAMB scalar temperature source: SW + ISW + Doppler + acoustic).
- rho_band = 4pi * A_band / Tr_band, with Tr_band = sum_{l,m in band} C_{lm,lm}, is a
  normalization-invariant reference quantity used for maps and figures, not for decisions.

Model: a single real twisted scalar field on E7 with real character sigma; scale-invariant weights
P(k) = k^-3; locally normal-ordered quadratic composite q(x) = phi(x)^2 - <phi(x)^2> (the variance
is position-dependent in twisted sectors); adiabatic sourcing zeta ⊃ g * q with joint Gaussianity
(assumption A3b' of Pillar-2 Note v0.4). Decisions are independent of the coupling g, since
A is proportional to g^2 > 0.

## 2. Parameter grid (frozen)

Sweep families (units chi_* = 1), each crossed with the 7 nontrivial real character sectors:

- S1scale: isotropic dilation s * (L_Ax, L_1y, L_2z) = s * (0.6, 1.2, 1.2), s in {0.75, 1.0, 1.25, 1.5}, L_Ay = 0.
- S2LAx: glide period L_Ax in {0.3, 0.45, 0.6, 0.75, 0.9}, with (L_1y, L_2z) = (1.2, 1.2), L_Ay = 0.
- S3L1y: y-compactness L_1y in {0.6, 0.8, 1.0, 1.2, 1.4}, with L_Ax = 0.6, L_2z = 1.2, L_Ay = 0.
- S4G1f / S4G2f: glide offset L_Ay = f * L_1y, f in {0.125, 0.25, 0.375, 0.5}, on anchors
  (0.6, 1.2, 1.2) and (0.6, 0.7, 1.2).
- S5aniso: cells (0.6, 1.2, 0.6), (0.6, 0.6, 1.2), (0.9, 0.7, 1.2), L_Ay = 0.

Internal-cutoff ladder: kcut in {18, 22, 26, 30, 34}. Refinement ladder: {38, 42}.

## 3. Extrapolation and classification (frozen)

For each quantity v in {A_2, A_3, A_4, A_band, Tr} at each grid point and transfer:

- E1 = least-squares fit v(k) = v_inf + c * k^-3 over the ladder (primary estimate);
- E2 = the same with k^-2;
- E3 = the value at the largest available kcut.
- Systematic: sigma_sys = max(|E1 - E2|, |E1 - E3|, rms of the E1 fit).
- Classification: **pos** if E1 - 3*sigma_sys > 0 and E2 > 0 and E3 > 0;
  **neg** if E1 + 3*sigma_sys < 0 and E2 < 0 and E3 < 0; otherwise **unc**.

Rationale: sandbox measurements show that over the accessible ladder the effective convergence
exponent can deviate from the asymptotic k^-3 expectation (free-exponent fits sometimes prefer
p ≈ 1.5–2), so sign decisions absorb the extrapolation-model spread as a systematic rather than
trusting a single model.

## 4. Decisions (frozen)

- **R1 (no-go upheld):** every full-transfer grid point is classified pos for A_band.
- **R2 (sign flip found):** at least two *adjacent* grid points (same sector, adjacent sweep values
  within one sweep family) are classified neg for A_band, AND the neg classification survives the
  refinement ladder {38, 42}, AND at least one of these points passes an independent V7-type
  cross-check (direct real-space sphere quadrature of the Sachs–Wolfe composite covariance against
  the harmonic-space pipeline at a reduced kcut).
- An isolated neg, and any unc, is a **candidate only**: extend the ladder, refine the geometry
  locally, and rerun independently before any claim. Candidates alone do not establish R2.

## 5. Secondary outcomes (recorded, not used for decisions)

Per-multipole signs and classes of A_2,inf, A_3,inf, A_4,inf; the geometry dependence of rho_inf
(quantifying transfer erosion); and the corresponding Sachs–Wolfe-limit tables.

## 6. Findings already known before freezing (declared to avoid post-hoc bias)

From the pilot scan (21 points, kcut <= 27, session of 2026-08-24), the following are **known**:

1. A_band > 0 in all pilot rows, for both the SW limit and full transfer (the no-go side).
2. rho_full < rho_SW in all pilot rows (transfer erosion, often by a factor ~2).
3. A_2 < 0 across all seven sectors of the (0.6, 1.2, 1.2) cell under full transfer
   (robust under extrapolation for the (-1,-1,+1)-type sector; extrapolation-model-dependent for
   (+1,-1,+1)).
4. A_3 < 0 in two sectors of the L_Ay = 0.3 cell in the SW limit.

Accordingly, the existence of negative per-multipole values is **not** a discovery claim of this
registration; the only discovery claim available here is the band-level flip R2.

## 7. Frozen inputs and change policy

- Analysis core: `t2b2_core.py` v0.2 (integer-lattice wavevector bookkeeping; verification battery:
  deck-condition words at 2e-14, dual-construction covariance agreement at 1e-15, Gram identity at
  machine precision, end-to-end harmonic-vs-quadrature ratio 1.000000). Its SHA-256 is recorded in
  the JSON at run time.
- Fiducial cosmology: H0 = 67.36, omega_b h^2 = 0.02237, omega_c h^2 = 0.1200, tau = 0.0544,
  A_s = 2.1e-9, n_s = 0.9649. **[TODO-verify: to be cross-checked against the program's frozen
  fiducial (Tier-B bridge to the Stage-I assets); if it differs, bump the version and rerun.]**
  Signs and rho are invariant under the overall normalization of the transfer function.
- Grid, ladders, extrapolation models, and thresholds: as specified above.
- Any change bumps the version number with the reason logged in the repository. Threshold changes
  after inspecting production results are not permitted.

## 8. Known limitations of scope

E7 only (E8–E10 require the four-element holonomy orbit and are a registered extension, not part of
this grid); real characters only (continuous Wilson lines excluded); P(k) = k^-3 baseline (spectral
tilt robustness is a planned secondary study); single-field self-quadratic channel as delimited by
Pillar-2 Note v0.4 (multi-field cross-quadratic channels are outside the no-go and outside this
registration).
