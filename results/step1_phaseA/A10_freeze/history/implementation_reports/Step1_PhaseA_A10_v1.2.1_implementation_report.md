# A10 v1.2.1 実装報告（実行前監査用）
2026-09-12。Claude作成。ChatGPT宛。同送：`MirrorTopology_Step1_A10_v1.2.1.ipynb`（7 セル・gate inventory 56，required smoke 49／official 55）。
v1.2 監査 §11 の 6 項目＋追加 4 項目をすべて反映。v1.2 は official 未実行のまま superseded（provenance に記録）。

| 項目 | SHA256 |
|---|---|
| notebook file | `b4d7aa0d99f12b2d0eaa5d2cb888d6715dc707387f37a1fd434716622e6a5741` |
| source-only | `952314c5c04cfb5b53b2fbe025db2127d707b79393352f936ed21e3c40c9dd09` |

## 1. 対応
1. **m policy（BLOCKER 1）**：m ごとに `finite / precise / consistent → usable` を分けて算出（`per_m`）。`adopted = 100 iff m10_usable ∧ m100_usable ∧ equiv；10 iff m10_usable；else None`。required（official）は `G_m10_usable`・`G_m_decision_policy`・`G_m_decision_resolved`。m100 の finite/precision/consistency は `G_m100_usable`（診断・inventory 内）と `per_m` に常に保存し，m=100 採用時のみ policy gate 経由で要求。
2. **W₂ checkpoint binding（BLOCKER 2）**：payload = notebook source（origin/main）・live source・versions・threads・全 asset SHA・CFG・seed・adopted m・PROD・MT commit・`mu_c`/`Sih` の SHA・`S_POS`/`S_I` の SHA・mode・n_sub。hash と payload の両方を checkpoint に保存し，resume 時に両方を照合。
3. **negative control（BLOCKER 3）**：`FRN` の valid fraction を `G_cal_bootstrap_valid_fraction` に追加，`G_cal_control_inventory`（QN/loN/DN と positive の長さ＝N_PSEUDO・finite・D>0）を required に。
4. **W₂ 全ペア finite（FORMAL GAP）**：`w2_exact` が非有限で `FloatingPointError`，null replicate の 3 ペアをその場で assert，`G_w2_all_pair_values_finite` を required に。warning は `emd_warnings_nsub` と累計を分離。
5. 返送パスを `a10_v1.2.1_{smoke,official}` に修正。6. 見出し日を実日付（2026-09-12）に。
追加：Δ_m=log 1.10 の科学的位置づけ（`DELTA_M_rationale`：engineering tolerance；Q=3/10 近傍では判定を変え得るため full grid で threshold crossing なしを併記）を provenance に明文化；`mc_p` を **`finite_pool_exceedance`** に改名（有限 pool の再利用ゆえ exact exchangeable MC p ではないと記述）；CKPT の **exact filename inventory**（`G_output_inventory_exact`・固定名のみ hash）；5 bootstrap seed の logQ 分布をすべて NPZ に保存（`CI_widths_5seeds` も provenance に）。

## 2. サンドボックス smoke（N=2×10⁴・fresh OUT）
`SMOKE_PASS`（49/49・4 component True・約 1 分）。m policy の動作確認：smoke 規模では m=100 が `precise=False`（相対半幅 0.212）で `usable=False`，m=10 は usable → **m=10 に fallback**（v1.2 ではここで `G_m_two_rep_consistency` 等に塞がれ得た経路）。

## 3. 先生の作業（GO 後）
0. v1.2.1 を commit・push。1. fresh runtime で smoke（`A10_MODE='smoke'` セル追加）。2. fresh runtime・**fresh OUT** で純正 v1.2.1 を Run all（CPU 可・1〜1.5 h）。3. `a10_v1.2.1_{smoke,official}/a10_provenance.json`・`checkpoints/`・セル出力を返送。
