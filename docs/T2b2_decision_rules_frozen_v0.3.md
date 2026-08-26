# T2b-2 Decision Rules — Frozen Pre-registration Draft v0.3
2026-08-26. Public commit target for the `mirror-topology` repository. **Supersedes v0.2** (which
was committed but under which no production grid was executed). Reason for revision (Sec. 8): the
external review of v0.2 identified a **blocking logical error** in Proposition T3 — the claim that
assumption A3b′ (joint Gaussianity) implies statistical independence. v0.3 corrects the logical
basis (new assumption A3d), records the counterexample, and implements the eight hardening items
of the same review. The scientific structure of v0.2 (joint (S⁺, S⁻) explanandum; analytic
primary layer; numerical grid demoted to secondary observables) is unchanged.

## 0. Frozen observational calibration (unchanged from v0.2)

Step 0 official (2026-08-25, commit d36e7567e8a7…): S⁺/null-median ∈ [0.0898, 0.1115] across all
ten maps; S⁻ normal (percentile 45.9–50.7); ρ_obs ∈ [−0.779, −0.722]; frozen null (CRN seeds
0..999): S⁺_med = 391.336, S⁻_med = 279.485, ρ_med = +0.1676, P_null(A < 0) = 0.334,
S⁻ [q2.5, q97.5] = [75.9, 930.2] μK². All p-values frozen-axis conditional; ten maps are
systematics robustness, not independent trials. Artifacts and hashes as in v0.2
(`step0_official_v0_7.csv`, `step0_null_arrays_v0_7.npz` Sp 961cf7106826…/Sm 63c1b4fe97ab…,
`step0_frozen_Bpm_v1.npz` 9693b207…).

## 1. The explanandum (unchanged)

A model explains the anomaly only if it renders the joint observation (S⁺ strongly suppressed,
S⁻ normal) unexceptional: the comparison quantity is p(S⁺, S⁻ | M) under the frozen statistic.
Producing A < 0 or ρ < 0 is neither necessary evidence nor the target.

## 2. Layer 1 (primary, analytic): independent-additive-channel no-go for the S⁺ deficit

### 2.1 Assumptions (corrected)

- **A3b′ (retained, role limited).** ζ₁ and the hidden field φ_χ form a centered jointly Gaussian
  family. Role: vanishing of the odd moment ⟨ζ₁ :φ²:⟩ = 0, hence the covariance decomposition
  C_ζ = C_{ζ₁} + g² C_q. **A3b′ does not imply statistical independence and is not sufficient
  for T3.**
- **A3d (new, explicit).** The standard scalar ζ₁ and the hidden twisted field φ_χ are
  **statistically independent**. Then q = q(φ_χ) is independent of ζ₁, and after linear transfer
  the sky contributions T_base and T_c are independent. Physical positioning: φ_χ is an
  independent spectator sector; scenarios with a correlated common origin are **outside** the
  registered class (a declared evasion route). Full statement and discussion in Pillar-2 Note
  v0.5.

**Cautionary counterexample (frozen record; verified numerically 2026-08-26).** Uncorrelatedness
does not suffice: with X = Y ~ N(0,1) (a degenerate centered jointly Gaussian pair),
q = Y² − 1 satisfies E[Xq] = 0, yet for T = X + q/2 and Q(T) = T²,
P(Q(T) ≤ 1) = P(−3 ≤ Y ≤ 1) = 0.840 > P(Q(X) ≤ 1) = 0.683 — the additive quadratic channel
*increases* the lower-tail probability. Continuity in the correlation coefficient extends the
counterexample to non-degenerate jointly Gaussian pairs. Hence T3 requires A3d, not A3b′.

### 2.2 Proposition T3 (restated)

Let X be a **centered Gaussian** sky vector — conditioned on fixed geometry, observer position,
orientation, and nuisance parameters; since the inequality below holds at every such parameter
point, it is preserved under marginalization over any prior. Let Y be an arbitrary random sky
vector **independent of X**, and let B₊ ⪰ 0 define Q(x) = xᵀB₊x. Then for every t ≥ 0,

  P[Q(X + Y) ≤ t] ≤ P[Q(X) ≤ t].

*Proof.* K_t = {x : Q(x) ≤ t} is a symmetric convex set. Conditioning on Y = y,
P(X + Y ∈ K_t | Y = y) = P(X ∈ K_t − y) ≤ P(X ∈ K_t) by Anderson's inequality; averaging over Y
completes the argument. ∎ (Write-up as Theorem 3 in Pillar-2 Note v0.5.)

Applicability to the frozen statistic: S⁺ = Q(T) with B⁺ ⪰ 0 verified numerically
(λ_min(B⁺) = +3.2×10⁻⁵ > 0 on the frozen artifact); the preprocessing (band window × transfer,
masked monopole+dipole removal) is linear, so Q is a PSD quadratic form of the sky vector.

### 2.3 Decision R0 (scope limited per review)

**No-go for an independent additive twisted channel as the mechanism responsible for the observed
S⁺ deficit, relative to the same base model:** for any E7 geometry, any real character sector, and
any amplitude g, adding the independent channel to a given centered-Gaussian base cannot increase
P(S⁺ ≤ S⁺_obs). This does **not** exclude full models in which the base itself (e.g., a
covariance-replacement topology) accounts for the S⁺ deficit and a small additive channel is also
present; covariance-replacement mechanisms are the subject of the Paper-A comparison (Steps 1–2).

### 2.4 Monte-Carlo validation (tail-lottery reporting)

Sandbox 2026-08-25, N_MC = 200,000, frozen B±, fiducial spectrum, threshold S⁺_obs,min =
35.15 μK²: base k = 8 (p̂ = 4.0×10⁻⁵, CP 95% CI [1.7, 7.9]×10⁻⁵); with an independent
antisymmetric-dominant component at three amplitudes k = 6 (p̂ = 3.0×10⁻⁵, CI [1.1, 6.5]×10⁻⁵).
**Within MC uncertainty, no violation of the predicted non-increase was observed.** (The MC is an
auxiliary check of an analytic statement, not evidence in itself.)

## 3. Layer 2 (secondary, numerical): T2b-2 grid — hardened specification

Grid families, sectors, kcut ladder {18, 22, 26, 30, 34}, refine ladder {38, 42} as v0.1.

1. **Quantities.** Per grid point, under the frozen statistic via the frozen artifact B±:
   s⁺_q = tr(B⁺ C_q,real), s⁻_q = tr(B⁻ C_q,real) per unit g², at each kcut.
2. **Positivity as implementation check (not classification).** Since B± ⪰ 0 and C_q ⪰ 0,
   s±_q ≥ 0 identically. Numerical rule: `if s < −tol: HARD FAIL` (implementation error), with
   tol = 10⁻¹² × tr-scale. The pos/neg/unc classification applies **only** to ρ_q.
3. **Extrapolation with correlated propagation.** Extrapolate s⁺_q and s⁻_q separately under each
   model E1 (k⁻³ tail fit), E2 (k⁻²), E3 (last value); for each model e compute
   ρ_q,e = (s⁺_e − s⁻_e)/(s⁺_e + s⁻_e); central value from E1; σ_sys(x) = max_e |x_e − x_{E1}|
   for x ∈ {s⁺, s⁻, ρ}. ρ_q,∞ is **derived**, never independently fitted, so the reported triple
   is always algebraically consistent.
4. **Classification.** ρ_q,∞ pos/neg/unc at the **3×σ_sys numerical-stability criterion** (an
   extrapolation-spread scale, explicitly *not* a statistical 3σ).
5. **Amplitude diagnostic (renamed per review).** ΔS⁻_max ≡ S⁻_obs,min − q2.5(frozen null S⁻) =
   259.34 − 75.9 = 183.4 μK² is a **ΛCDM frozen-null based conservative mean-budget diagnostic**,
   not a strict bound (cross terms, variance changes, and non-ΛCDM bases alter the S⁻
   distribution; the strict constraint is Step-1's p(S⁻ ≤ S⁻_obs | M, g) or the joint
   p(S⁺, S⁻ | M, g)). Per grid point record: g²_max = ΔS⁻_max / s⁻_q,∞, and the movements
   achievable within the budget, g²_max·s⁺_q,∞ and g²_max·s⁻_q,∞.
6. **R2′ renamed:** the **antisymmetric-dominant channel regime** — at least two adjacent points
   with ρ_q,∞ classified neg, surviving the refine ladder and one V7-type real-space cross-check.
   The report states both the regime and its amplitude-aware reach (item 5); it is explicitly not
   an explanation claim (R0), and "mimicking" language is not used as a headline.
7. **R1′:** T3 assumptions verified for the registered class (A3d declared) AND the grid completed
   with all points quantified and all implementation checks passed.

### 3.1 Complex→real bridge: hard validation battery (required before production)

The T2b-2 covariance C_q is produced in the complex (ℓm) basis; B± live in the 21-dimensional
real basis (healpy convention: a_{ℓ0} = 1; m > 0 cos: 1/√2, sin: −i/√2). Before any production
point is accepted, the conversion must pass all of: (1) C_q,real is real symmetric;
(2) C_q,real ⪰ 0 (λ_min ≥ −tol); (3) dimension exactly 21; (4) the quadratic expectation computed
directly in the complex basis equals tr(B± C_q,real) to 10⁻¹⁰ relative; (5) agreement on several
random synthetic covariances; (6) Monte-Carlo sky realizations drawn from C_q reproduce the
analytic traces within MC error. Trace-preservation alone is insufficient (mode-placement errors
can conserve the trace).

## 4. Statistics and labeling (unchanged from v0.2)

Frozen-axis conditional p-values; floor rules with k, N, and Clopper–Pearson 95% intervals;
no probability multiplication across maps.

## 5. Retained from v0.1 (unchanged)

Grid families and sectors; ladders; candidate protocol for isolated points; units (χ_* = 1) and
sign conventions (A > 0 mirror-even side).

## 6. Findings known before this freeze (declared)

As v0.2 Sec. 6, plus: (5) the A3b′-independence counterexample and its numerical verification
(0.683 → 0.840); (6) the revised T3 MC with tail counts (Sec. 2.4). No production grid has been
executed under any rules version.

## 7. Scope and limitations

E7 grid; real characters; single-field self-quadratic channel; P(k) = k⁻³ baseline; PR3 best-fit
theory C_ℓ for the frozen null; T3 assumptions per Sec. 2 (notably A3d — independence; correlated
hidden-sector scenarios and cross-correlated multi-field constructions are outside the registered
class and are declared evasion routes).

## 8. Change log

v0.2 → v0.3 (2026-08-26): **Blocking fix** — T3's independence premise corrected: A3b′ (joint
Gaussianity) does not imply independence (counterexample recorded); new explicit assumption A3d;
T3 restated with centered-Gaussian and fixed-parameter conditioning; R0 scope limited to
"independent additive channel relative to the same base model". Hardening per review: s±_q ≥ 0 as
HARD FAIL; ρ_q,∞ derived from extrapolated s±_q,∞ with correlated propagation; six-test
complex→real validation battery; ΔS⁻_max repositioned as a mean-budget diagnostic with per-point
g²_max records; R2′ renamed antisymmetric-dominant channel regime; MC tail reporting in
tail-lottery format; "3×σ_sys numerical-stability criterion" labeling. v0.2 was committed to the
repository; it is superseded by this version under the change policy (version bump with recorded
reasons; no grid results existed under v0.2).
