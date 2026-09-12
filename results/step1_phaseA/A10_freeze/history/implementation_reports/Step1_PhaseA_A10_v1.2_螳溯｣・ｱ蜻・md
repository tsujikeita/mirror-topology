# A10 v1.2 実装報告（実行前監査用）
2026-09-13。Claude作成。ChatGPT宛。同送：`MirrorTopology_Step1_A10_v1.2.ipynb`（7 セル・gate inventory 54，required smoke 48／official 53）。
v1.1 監査（2026-09-11）§15 の 15 項目をすべて反映。v1.1 は official 未実行のまま superseded（provenance に記録）。

| 項目 | SHA256 |
|---|---|
| notebook file | `93b15891dd8104cb8b987ef9efa167fbb234f714e20d43ff365f8b630f614565` |
| source-only | `35cad3de9c3e6380e5db3ca25967f2a224a4cb878db802ba57848f527950a27d` |

## 1. 対応一覧（監査 §15 の順）
1. **float32 丸め順**：`x64 → astype(float32) → packed_into（float32 積）→ float32 GEMM（Fp は float32 化した B から fvec）→ argmin`。A8b child と同一。
2. **float64 評価**：A8b の `eval64` と同じ `einsum('ni,nij,nj->n', x64, Bp[axis], x64)`。**`G_a8b_kernel_exact_regression`**：A8b child の `cast / packed_into / select(l24_feature231) / eval64` を凍結 child ソースから逐語的に inline 再実装し，2000 標本で argmin・T₁・T₂ が **bit 同一**（float32・float64 両 selection）を required に。
3. **m fallback**：`G_m_precision_policy = (adopted==100 ∧ m10_ok ∧ m100_ok ∧ equiv) ∨ (adopted==10 ∧ m10_ok ∧ (¬m100_ok ∨ ¬equiv))` を required（official）に，`G_m_precision_each_run` は診断（inventory 内・非 required）。
4. **practical equivalence**：**Δ_m = log(1.10) を事前登録**。rep1・rep2・pooled の差 CI がすべて [−Δ_m, +Δ_m] 内 → m=100；m=10 両 rep 適格かつ（m=100 不適格 ∨ 等価未成立）→ **m=10**；それ以外 unresolved。「CI が 0 を含む」は等価と扱わず，`zero_in_all_CIs` は記録のみ。provenance の `reason` に判定理由。
5. **fail-fast**：official では A10b 末尾で `M_SENSITIVITY_RESOLVED` と `adopted_m is not None` を assert（unresolved で較正・W₂ を走らせない）。
6. **bootstrap 分子 0**：Q=0 として保持，分母 0 かつ分子>0 は +inf，両 0 のみ除外。
7. **valid fraction**：pseudo ごとの valid／den_zero／num_zero／both_zero を記録，`G_cal_bootstrap_valid_fraction`（≥0.95・main・positive・observed）を required に。
8. **positive control**：観測閾値で Q 下側 CI ≥ 3 ∧ Q ≥ 10 ∧ **D > 1**（D 分岐も検査）。smoke：Q=100・下側 CI 81・D=16.5。
9. **main inventory**：`G_cal_main_inventory`（n_pseudo 厳密・配列長・Q/lower CI/D の finite・D>0）。negative control は分子・分母を**独立** bootstrap。
10. **3 位置**：matched-power・raw λ_min>0・clip=0・sqrt 対称性・再構成残差を 3 位置すべてで gate；`G_cov_positions_distinct` は全 3 ペアの共分散差 > 1e-6。
11. **W₂ の sampling mechanism**：**primary = 3 位置を独立 (R,z) stream で生成**（null＝等方 pool の disjoint 3 block と同一機構）→ MC p を calibrated reference として記録。CRN 版は `diagnostic_crn`（conservative exceedance；exact MC p とは呼ばない）として併記。
12. **W₂ gate**：`observed_finite / pair_seed_inventory / null_length_exact` を required；**安定性 gate を事前登録**（3 seed の above/below q99 判定一致・n_sub 2000/5000 の判定一致・W₂_max の seed 間 spread ≤ 0.25）——official で required（smoke は記録のみ）。component 名を `W2_PATHWAY_VALID` に，B=200 の粗さを caveat として記録。
13. **binding**：A9 provenance の M21/LM/real-basis SHA（`G_a9_basis_hashes`）と quadrature nodes/weights SHA・n_theta/n_phi（`G_a9_quadrature_hashes`）に完全一致；`G_cov_basis_matches_M21`（`Re(M21·Csym·M21ᴴ) == C_real`，`t2b2_bridge.to_real` と同式）。
14. **official hard gate**：`G_notebook_live_source`（`tr.live_notebook_source_sha() == origin/main の source-only SHA`）・`G_threads_live_registered`（全 BLAS pool が 2）。
15. **atomic NPZ**（tmp→fsync→replace）・official required 数の明記（provenance `required_gate_count`）。加えて W₂ の n_sub 単位 checkpoint に **config/seed/commit の binding** を付け，不一致の stale checkpoint は無視。

## 2. サンドボックス smoke（N=2×10⁴・fresh OUT）
`SMOKE_PASS`（48/48・4 component True・約 1 分）。`G_a8b_kernel_exact_regression` PASS（丸め順修正の検証）。
m 判定（smoke 規模）：差 CI が ±Δ_m を超えるため **m=10**（`equivalence_established=False`・`zero_in_all_CIs=True`）——smoke では N が小さく CI が広いための当然の結果で，official の判定は N=10⁶ で行う。
W₂（smoke）：primary（独立 stream）の W₂_max は CRN 版より大きく（0.21–0.24 vs 0.14–0.15），null q99 前後に分布——3 位置 mock が非等価であることと整合。official の安定性 gate は，観測値が閾値近傍なら FAIL し得る（fail-closed 設計；その場合は n_sub/B を上げた再実行を登録する）。

## 3. 先生の作業（GO 後）
0. v1.2 を **commit・push**（official は live source と origin/main の一致を hard gate）。1. fresh runtime で smoke（`A10_MODE='smoke'` セル追加）。2. fresh runtime で純正 v1.2 を Run all（CPU 可・1〜1.5 h）。3. `a10_v1.2_{smoke,official}/a10_provenance.json`・`checkpoints/`・セル出力を返送。
