# T2b-2 Decision Rules — Frozen Pre-registration Draft v0.2
2026-08-25. Public commit target for the `mirror-topology` repository. **Supersedes v0.1** under the
change policy: v0.1's production grid was never executed; this recalibration was completed and
frozen **before any grid execution**, using the officially completed Step 0 observational
calibration (2026-08-25) and the external-review recommendation to base decisions on the joint
(S⁺, S⁻) structure. Reason for revision logged in Sec. 8.

## 0. What changed and why (summary)

Step 0 established, with a fully reproduced frozen pipeline (commit d36e7567e8a7…, exact per-map
S⁺ reproduction at machine precision, per-realization frozen-null regeneration with bit-level
cross-environment agreement), that the observed anomaly is a **selective depletion of mirror-even
power**: S⁺/null-median ∈ [0.0898, 0.1115] across all ten maps, while **S⁻ is normal**
(percentile 45.9–50.7 in the frozen null; ρ_obs ∈ [−0.779, −0.722]; null: S⁺_med = 391.336,
S⁻_med = 279.485, ρ_med = +0.1676, P_null(A<0) = 0.334; all values frozen-axis conditional).
Consequently, "A < 0" alone carries no evidential weight, and v0.1's primary decision — the sign
of the twisted channel's band asymmetry — is the wrong primary target. v0.2 restructures the
Stage-III decision into an analytic primary layer and a recalibrated numerical secondary layer.

Frozen calibration artifacts: `step0_official_v0_7.csv`, `step0_provenance_v0_7.json`,
`step0_null_arrays_v0_7.npz` (Sp2_4 SHA-256 961cf7106826…, Sm2_4 63c1b4fe97ab…),
`step0_gateA_permap_v0_7.csv`.

## 1. The explanandum (frozen)

A model explains the anomaly only if it makes the **joint** observation
(S⁺ strongly suppressed, S⁻ normal) unexceptional; formally, the Step-1/2 comparison quantity is
the joint predictive distribution p(S⁺, S⁻ | M) evaluated at the frozen observed values, under the
frozen statistic (config N16_Splanck_Kcommon_mdON_harm, axis pix 1134 at Nside 16 RING).
Producing A < 0 or ρ < 0 is neither necessary evidence nor the target.

## 2. Layer 1 (primary, analytic): additive-channel no-go for the S⁺ deficit

**Proposition T3 (to be proven as Theorem 3 in Pillar-2 Note v0.5).** Let the sky temperature be
T = T_base + T_c, where T_base is Gaussian (ΛCDM, or any Gaussian topological model) and T_c is an
**independent** additive component (in the registered class this is the twisted-sector quadratic
channel: assumption A3b′ gives ζ₁ ⟂ φ, hence ζ₁ ⟂ q, hence full independence of the sky
contributions under linear transfer). Let S⁺ = Q(T) with Q a positive-semidefinite quadratic form
of the map (the frozen statistic is of this type: band window × transfer, monopole+dipole removal
under the mask — all linear — followed by a mean of squares; verified numerically:
λ_min(B⁺) = +3.2×10⁻⁵ > 0). Then, since {T : Q(T) ≤ t} is a symmetric convex set, **Anderson's
inequality** gives, for every t and every realization of T_c,
P(Q(T_base + T_c) ≤ t) ≤ P(Q(T_base) ≤ t).

**Decision R0 (frozen).** Within the registered class — any E7 geometry, any real character
sector, any coupling amplitude g — the additive twisted channel **cannot increase**
P(S⁺ ≤ S⁺_obs) and therefore cannot alleviate the primary anomaly. Stage III's primary verdict is
this analytic no-go; it does not depend on the numerical grid.

Validation recorded before freezing (2026-08-25 sandbox): Monte-Carlo demonstration with the
frozen B± and the fiducial spectrum — base P(S⁺ ≤ 35.15 μK²) = 4×10⁻⁵; adding an
antisymmetric-dominant independent component at increasing amplitudes yields 3×10⁻⁵ at all
amplitudes (non-increase), while ΔE[S⁻] grows linearly (+30/+59/+118 μK²).

Assumptions and evasions: T3 requires (i) independence (violated by cross-correlated multi-field
constructions, which are outside the registered no-go class per Pillar-2 Note v0.4), (ii) Gaussian
base, (iii) PSD quadratic statistic. Covariance-replacement mechanisms (standard topological
correlations, which modify C rather than add a component) are **not** constrained by T3; they are
the subject of the Paper-A comparison (Steps 1–2) via p(S⁺, S⁻ | M).

## 3. Layer 2 (secondary, numerical): recalibrated T2b-2 grid

The grid (unchanged geometry/sector definition and kcut ladders from v0.1) no longer adjudicates
an explanation claim. Its frozen purpose is to **quantify the channel's secondary observables**
under the frozen statistic:

- Per grid point, using the frozen quadratic forms B± (artifact `step0_frozen_Bpm_v1.npz`,
  SHA-256 9693b207…; built by polarization identity from the frozen statistic on the 21-dimensional
  real sky-harmonic basis ℓ = 2–4; PSD verified; tr(B±C_fid) agrees with the frozen-null ensemble
  means within Monte-Carlo standard error):
  **s⁺_q = tr(B⁺ C_q,sky)**, **s⁻_q = tr(B⁻ C_q,sky)** per unit g², and
  ρ_q^frozen = (s⁺_q − s⁻_q)/(s⁺_q + s⁻_q), where C_q,sky is the channel's full-transfer sky
  covariance (ℓ = 2–4 block) from the T2b-2 pipeline. Implementation note (required before
  execution): the grid notebook is updated to v0.2 to (a) load B±, (b) convert its complex-(ℓm)
  covariance block to the B± real basis with a trace-preservation check, and (c) record
  (s⁺_q, s⁻_q, ρ_q^frozen) per grid point alongside the legacy harmonic outputs.
- Extrapolation and uncertainty exactly as v0.1 (E1: k⁻³ fit; E2: k⁻²; E3: last value;
  σ_sys = max spread; classification pos/neg/unc at 3σ_sys), applied to s⁺_q, s⁻_q, and
  ρ_q^frozen.
- **Amplitude bound (frozen, first order):** the S⁻-normality of the data caps the channel's
  admissible mean addition: g² s⁻_q ≤ ΔS⁻_max ≡ S⁻_obs,min − q2.5(null S⁻) = 259.34 − 75.9 =
  **183.4 μK²** (0.66 × null S⁻ median). This first-order shifted-mean rule is superseded, with a
  version bump, if the Step-1 exact shifted-distribution treatment differs materially.
- **R1′ (Stage-III no-go, full form):** T3 assumptions verified for the registered class (they
  hold by construction) AND the grid completes with all points quantified. Note the grid cannot
  overturn R0 within the class; R1′ records that the secondary observables were mapped.
- **R2′ (maximally-mimicking regime, replaces v0.1's discovery rule):** at least two adjacent grid
  points (same sector, adjacent sweep values in one family) classified neg for ρ_q^frozen beyond
  3σ_sys, surviving the refine ladder and one V7-type real-space cross-check. R2′ identifies the
  regime in which the channel most closely mimics the anomaly's derived statistics; **it is
  explicitly not an explanation claim** (excluded by R0 for the primary observable, and bounded by
  the ΔS⁻_max rule for the derived ones). Isolated neg/unc points remain candidates per v0.1.

## 4. Statistics, p-values, and labeling (frozen)

All p-values and percentiles referencing the frozen null are **frozen-axis conditional**; the ten
maps constitute systematics robustness, not independent trials (no p-multiplication). Tail
probabilities follow the floor rules (k = 0 reported as p ≤ 1/N with the ensemble size stated;
Clopper–Pearson 95% intervals recorded).

## 5. Retained from v0.1 (unchanged)

Grid families S1–S5 and the seven real character sectors; kcut ladder {18, 22, 26, 30, 34} and
refine ladder {38, 42}; the E1/E2/E3 extrapolation machinery and σ_sys definition; the candidate
protocol for isolated points; units (χ_* = 1) and sign conventions (A > 0 mirror-even side).

## 6. Findings known before this freeze (declared to avoid post-hoc bias)

(1) Pilot T2b-2 (21 points, kcut ≤ 27): all harmonic A_band > 0 for SW and full transfer;
transfer erosion ρ_full < ρ_SW throughout; A₂ < 0 across the (0.6, 1.2, 1.2) cell under full
transfer; A₃ < 0 in two sectors at L_Ay = 0.3 (SW). (2) Step 0 official values as listed in
Sec. 0. (3) Proposition T3 and its MC validation, identified and recorded **before** any
production-grid execution. (4) The frozen B± artifact and its validation numbers.

## 7. Scope and limitations

E7 grid only (E8–E10 registered extension); real characters; single-field self-quadratic channel;
P(k) = k⁻³ baseline; T3's assumptions as stated in Sec. 2. The fiducial spectrum for the frozen
null is the PR3 best-fit theory C_ℓ file (SHA-256 recorded in Step-0 provenance), removing the
earlier CAMB-fiducial [TODO-verify].

## 8. Change log and hardening

v0.1 → v0.2 (2026-08-25): recalibrated on completed Step 0; primary decision moved from the sign
of the harmonic band asymmetry to the analytic no-go T3 for the S⁺ deficit; numerical grid
re-purposed to secondary observables under the frozen statistic with the ΔS⁻_max amplitude rule;
observed/null calibration values and artifacts frozen with hashes. The v0.1 grid was never
executed, so no results informed this revision beyond the declared pilot.

Future official reruns additionally harden (per external review): official-notebook SHA-256 and
S⁻-extension code hash in provenance as gate inputs; cross-environment bit-level null match,
processed-mask hash, and CMBanom commit as hard conditions; "clean tree" reported as *tracked
working tree clean*.
