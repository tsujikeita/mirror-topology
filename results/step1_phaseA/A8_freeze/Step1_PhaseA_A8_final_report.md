# Step 1 Phase A-8 final report — feature stack (A8a) and scan benchmark (A8b)
2026-09-11. Claude. Freeze package: `results/step1_phaseA/A8_freeze/`.

## 1. Outcome
| Sub-stage | Canonical notebook (source-only SHA256) | Official status | Gates |
|---|---|---|---|
| A8a v1.1.2 — hybrid ℓ≤16 feature stack F16 | `MirrorTopology_Step1_A8a_featurestack_v1.1.2.ipynb` (`7fe775f9…`) | `FEATURESTACK_VALID` | 49/49 (smoke 47/47) |
| A8b v1.1.8 — staged scan benchmark | `MirrorTopology_Step1_A8b_scan_benchmark_v1.1.8.ipynb` (`e2b33af9…`) | `BENCHMARK_VALID` | 35/35 (smoke 35/35) |

Both stages passed an independent pre-run audit (ChatGPT) and an independent post-run recomputation from the frozen artifacts
(ChatGPT and Claude, separately). Engineering rules for Step 1 rules v1.0 are in `A8_rules_v1.0.md`.

## 2. A8a (feature stack)
- F16 = packed upper-triangular quadratic-form features (40 755) for the S⁺ statistic on all 3072 axes, ℓ=2…16, common mask, Nside 16;
  float64 (1.00 GB) and float32 (0.50 GB). Low-ℓ block reproduces the A5 B-stack to 5.6e-17; symmetry residual 1.8e-17; sampled PSD ≥ 5.1e-16.
- Validation battery (1 210 samples: 10 observed maps, 1 000 fresh isotropic, 200 hybrid E7): argmin agreement f64/f32/reference 1210/1210;
  Event B mismatch 0; f32 axis mismatch 0 (max plane-folded separation 1.5e-6 deg). Flags `float32_eligible_for_{event,axis}_outputs` = True.
- The two `.npy` files are **not** in git (size); they are bound by file and array SHA256 in `a8a/official/…manifest.json` and re-verified by A8b
  (`G_F16_file_sha`, `G_F16_array_sha_local`). See `F16_EXTERNAL_ARTIFACTS.md`.

## 3. A8b (scan benchmark)
- Registered adaptive staged design (pilot → finalist → winner, safe tie-break), isolated subprocesses, selection dtype / evaluation float64
  separation, memory/thread telemetry, untimed audit children, checkpoint binding to the environment.
- **Amendment history (kept, not overwritten):** the v1.1.5 smoke FAILED on `G_chunk_invariance`/`G_audit_matches_timed` because raw HEALPix
  argmin identity was required while float32 selection swaps exactly-tied antipodal axes (same mirror plane) between GEMM blockings.
  v1.1.6 (withdrawn, never run) relaxed the gate without hard-gating plane equivalence. v1.1.7 introduced the shared predicate
  `selected_output_equiv` (float64 raw-exact; float32 only exact antipode at raw margin < tol; selection score, float64 T₁/T₂, Event B
  indicator must agree), synthetic self-tests and the amendment binding; v1.1.8 added archival hardening (report expected SHA, parent raw
  artifacts, timed audit vectors, antipode expected SHA, preflight). Evidence chain: `a8b/v1.1.5_smoke_FAILED/` → `A8b_amendment_v1.1.7.md`
  (SHA `950bea6c…`, bound by `G_parent_failed_smoke_binding`) → `a8b/smoke/` → `a8b/official/`.
- Official result (CPU-only Colab runtime, 2 threads): ℓ2–4 `l24_feature231`/float32/chunk 20000 = 0.655 min per 10⁶ samples (measured at 10⁶);
  S2 `s2_feature`/float32/chunk 1024/axis block 3072 = 83.1 min per 10⁶ (linear extrapolation from 2×10⁵), peak RSS +1.02 GB.
  All 62 timed configs are selected-output-equivalent to the canonical audit children; float64 raw argmin exact; 3 995 float32 flip occurrences,
  all exact antipodes, T₁/T₂ identical. GPU route not benchmarked (runtime without GPU). One classified `timeout` (S2 float64 winner).

## 4. Limitations recorded
- A8b's Event B comparison is degenerate on unit-variance benchmark draws (all True); physical-amplitude Event B eligibility for float32 is inherited
  from A8a (`G_F16_f32_eventB`).
- Absolute timings and optimal chunks are bound to the official environment fingerprint (see `A8_rules_v1.0.md` §R5).
- S2 scientific adoption remains HOLD until the S4 / exact validation gate.

## 5. Package contents
Notebooks, amendment report, audits (`ChatGPT_audit_…`, `Step1_PhaseA_A8_independent_verification.md`, received-artifact SHA list),
`a8_env_lock.json`, `a8a/{smoke,official}/` (provenance, validation CSV, manifest, console log), `a8b/v1.1.5_smoke_FAILED/`,
`a8b/{smoke,official}/` (7 outputs + console log), `F16_EXTERNAL_ARTIFACTS.md`, `build_freeze_manifest.py`, `freeze_manifest.json`.
Console logs are LF-normalised (git would do so on commit); the CRLF hashes of the submitted files are in `A8a_A8b_received_artifacts_SHA256.txt`.
