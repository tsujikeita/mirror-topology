# Step 1 Phase A-10 final report — W₂ estimator, orientation-cluster m, calibration pathway
2026-09-12. Claude. Freeze package: `results/step1_phaseA/A10_freeze/`.

## 1. Outcome
| Item | Value |
|---|---|
| Canonical notebook | `MirrorTopology_Step1_A10_v1.2.9.ipynb` (source-only SHA256 `731cb898…`, file `c11c4141…`) |
| smoke | `SMOKE_PASS` 54/54 |
| official | **`A10_VALID` 61/61**, 4 components True (`ENGINE_VALID`, `M_SENSITIVITY_RESOLVED`, `CALIBRATION_PATH_VALID`, `W2_PATHWAY_VALID`) |
| Environment | Python 3.13.15 / NumPy 2.1.3 / SciPy 1.16.3 / healpy 1.20.0 / POT 0.9.7.post1 / OpenBLAS 0.3.27 (2 threads) |
| Dependency commit | `mirror-topology@1bdd9ea8` (A8 freeze) |
| Audit | ChatGPT official audit 2026-09-12: freeze GO; independent recomputation of engine, m decision, calibration pathway, W₂ nulls |

## 2. Frozen design results (rules v1.0 inputs; see `A10_rules_v1.0.md`)
- **m = 100** (practical equivalence to m=10 within Δ_m = log 1.10, 5/5 bootstrap seeds).
- **ℓ2–4 selection dtype = float64** (supersedes the A8b float32 recommendation for ℓ2–4 on stress evidence; chunk 2000 = A8b float64 winner). S2 keeps float32 with explicit near-minimizer / plane-folded axis semantics.
- Calibration implementation: 2D pseudo thresholds, no-rescan hit tables, paired cluster bootstrap with zero-numerator retention, log-density ratio (`logpdf`).
- W₂ estimator: whitened exact 2D W₂, 3-position max-pairwise, independent-stream primary with disjoint-block null, CRN diagnostic, pre-registered stability gates, exact-subset selection-path bound.

## 3. Measured (official, E7_b1_A x₀⁽¹⁾, PR3-power-matched, Event B)
- Engine vs A5 map-based null: T₁ median 120.4 (A5 118.5, CI [115.4, 122.8]); P(T₁≤obs) 0.0149 (A5 0.0150); P(Event B) 0.0037 (A5 0.0040).
- Q (support ratio) = 1.35 / 1.30 (m=10 reps), 1.33 / 1.30 (m=100 reps), CI half-width ≈ 0.04. Preliminary one-point observation, not a verdict.
- float32 selection sensitivity: 69,426 raw-axis flips in 8×10⁶ samples (0.87%), 32 non-antipodal (plane-folded angle up to 85°, T₂ up to 14%), Event B mismatch 0, Q identical.
- One-point calibration pathway: false support 0/200 (Wilson upper 0.019); negative control 0/200; positive control at observed thresholds Q=97.9, lower CI 95.0, logD 2.87.
- W₂ (mock positions): n_sub=5000 W₂_max 0.135–0.153 vs null q99 0.165 (below, all seeds and both n_sub); selection-path decision margin holds.

## 4. Scope limits recorded
A10c is a one-point, one-system pathway prototype (not familywise global calibration). A10d positions are a mock set (not the registered p^(3)); B=200 q99 is coarse; exceedance is a finite-pool estimate. Neither the global false-support rate nor the final W₂ trigger threshold is frozen here.

## 5. History
v1.0 (superseded results) → v1.1–v1.2.4 (audit-driven redesign, never run officially) → v1.2.5 (pre-run audit PASS) → v1.2.6/7/8 (Colab environment fixes: healpy pin, NumPy-version-independent quadrature gate, BLAS-pool thread gate) → v1.2.8 official FAILED only on `G_cal_control_inventory` (KDE pdf underflow; kept in `history/`) → **v1.2.9**. Implementation reports, all audits and all notebook versions are in `history/`.

## 6. Package contents
`MirrorTopology_Step1_A10_v1.2.9.ipynb`, `A10_rules_v1.0.md`, `A10_design_note_v1.0.md` + `a10_w2_benchmark.json` (sandbox design evidence), `Step1_PhaseA_A10_v1.2.9_independent_verification.md` (corrected), `ChatGPT_audit_A10_v1.2.9_A10_VALID_FREEZE_GO.md`, `A10_v1.2.9_received_artifacts_SHA256.txt`, `smoke/` and `official/` (provenance, 11 checkpoint files, console log), `history/` (v1.2.8 FAILED provenance + checkpoints, implementation reports, audits, notebooks v1.0–v1.2.8, version history), `build_freeze_manifest.py`, `freeze_manifest.json`. Console logs are LF-normalised (CRLF hashes of the submitted files are in the received-artifact list).
