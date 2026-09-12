# A10 v1.2.3 実装報告（実行前監査用）— cross-selection policy の重要な設計発見を含む
2026-09-12。Claude作成。ChatGPT宛。同送：`MirrorTopology_Step1_A10_v1.2.3.ipynb`（7 セル・gate inventory 59，required smoke 51／official 57）。

| 項目 | SHA256 |
|---|---|
| notebook file | `b2f180ad57d340bb676860828cea516a1f627371eb4b9e3b5e596dcec3123759` |
| source-only | `c31841f403e67884fd66d69fa781f8c8a5b7281b65ca6b803d76538dc77e6583` |

## 1. BLOCKER 2（乱数 stream）：解消
`GEN_NS`（calibration=100・m_sensitivity=200・pseudo=300・negative_control=400・w2_independent=500・w2_crn=600・w2_isotropic=700）を導入し，全 `generate()` 呼び出しの (namespace, ids, N, m, systems) を provenance `generation_streams.calls` に記録。`G_generation_stream_keys_unique` を required に。smoke の 12 call はすべて一意（calibration `[100,0]` と pseudo `[300,0]` は別 stream）。

## 2. BLOCKER 1（cross-selection policy）：推奨 A を実装して smoke したところ **新しい事実が出た**
推奨 A（plane 同一＋Event B 同一＋連続出力 1e-5 bound）を required にして smoke（8×10⁴ 標本・新 stream）を回した結果，**FAIL**：
| run | flip | antipode | 非対蹠 | T₁ rel@flip | T₂ rel max | Event B mismatch |
|---|---|---|---|---|---|---|
| m10_rep2 iso | 1 | 1 | 0 | 2.7e-7 | 3.6e-6 | 0 |
| m100_rep1 iso | 2 | 1 | **1** | 1.2e-7 | **5.4e-3** | 0 |
| m100_rep2 iso | 1 | 1 | 0 | 3.9e-8 | **7.5e-4** | 0 |
- **antipode flip でも T₂ が最大 7.5e-4 相対で変わる**（B⁻ 行が同一でない antipodal representative；A5 の 292/3072 軸に対応）。前回の 1.7e-6 は氷山の一角で，1e-5 の連続 bound は成立しない。
- **非対蹠の plane への flip が起きる**（標本 8953：AX32=1357 vs AX64=1420，S⁺ の差は 1e-8 相対＝float32 分解能内の near tie；T₂ は 0.5% 変わる）。A8b の「flip は exact antipode のみ」という前提は，10⁴ audit では見えなかったが 8×10⁴ で 1 件出た。
- 頻度は ~5e-5/標本，Event B mismatch は 0/8×10⁴。flip 行の evidence（index・AX32/AX64・antipode 関係・T₁/T₂ 両 path・Event B 両 path）を `a10b_flip_evidence.npz`（＋calibration は `a10a_calibration.npz`）に保存。

**登録した policy**（official 前に固定；A8b の 1e-6 は書き換えない）：production float32 が authoritative，float64 selection は sensitivity path。共通 helper `compare_selection_paths` で
(a) **flip は selected S⁺ の相対差 < `TOL_NEAR_TIE=1e-6`（float32 分解能）の near tie でのみ起きる**（実測：全 flip で 4e-8〜2.7e-7）——これが真の不変量；
(b) **Event B mismatch 率 ≤ `TOL_EVENTB_MISMATCH=1e-5`**（P(E_B)≈4e-3 に対し相対 0.25% 未満；MC 誤差 ±1.5% より 1 桁小さい）；
を required（`G_cal_f32_f64_selection_consistency`・`G_m_f32_f64_selection_consistency_all_runs`），非対蹠 flip の有無は診断 gate `G_m_f32_f64_no_nonantipodal_flip`（smoke で False）。axis は plane-folded label と raw oriented representative の双方を保存し，T₁/T₂ は production path の representative で評価（監査 §4 のとおり）。
**rules への提起**：ℓ2–4 では float64 selection のコストが 1.3 min/10⁶ と無視できるため，「ℓ2–4 は float64 selection を production に，S2 のみ float32」という A8 freeze からの保守的な逸脱を rules 監査で検討する価値がある（A10 は A8b 凍結どおり float32 primary で実行し，float64 を全 run で併走しているので，どちらの結論にも証拠を残せる）。

## 3. その他
`compare_selection_paths` の結果は calibration・4 run × model/iso に保存（`cross_selection`）。provenance に `cross_selection_policy`（authoritative/sensitivity・両許容値・sandbox_discovery・status）。smoke：`SMOKE_PASS`（51/51・4 component True）。

## 4. 先生の作業（GO 後）
0. v1.2.3 を commit・push。1. fresh runtime で smoke。2. fresh runtime・fresh OUT で official（1〜1.5 h）。3. `a10_v1.2.3_{smoke,official}/a10_provenance.json`・`checkpoints/`・セル出力を返送。
