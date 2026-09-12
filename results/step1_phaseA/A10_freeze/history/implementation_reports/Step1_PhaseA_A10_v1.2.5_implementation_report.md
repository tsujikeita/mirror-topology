# A10 v1.2.5 実装報告（実行前監査用）
2026-09-12。Claude作成。ChatGPT宛。同送：`MirrorTopology_Step1_A10_v1.2.5.ipynb`（7 セル・gate inventory 64，required smoke 53／official 60）。
v1.2.4 監査 §12 の必須 4 項目＋強く推奨 3 項目をすべて反映。v1.2.4 は official 未実行のまま superseded。

| 項目 | SHA256 |
|---|---|
| notebook file | `feaa44eb0eb5c255d1c92090da956d22201d9971c4e4b94887b6c57446e18e06` |
| source-only | `ecc8a79c26e5300d7da5c87fef8cf0db8c1b31130b6708df02db955cc5dbac09` |

## 1. 必須修正
1. **helper 配線（BLOCKER 1/1b）**：`compare_selection_paths(d_sensitivity, d_primary)` に改名，evidence label を `AX_sensitivity/AX_primary`・`T1_sensitivity/T1_primary` 等の dtype 非依存名に。calibration は **`(cal32, cal64)`**，m run は **`(out[SENS], out[PRIM])`**。preflight に alias assert（`cal is cal64 and cal32 is not cal64 and cal32['AX'] is not cal64['AX']`）と，配線そのものの gate `G_cal_sensitivity_wiring`（gate が比較した flip 数 == `sum(cal32.AX != cal64.AX)`）を required に追加。self-test は実呼び出しと同じ (alt, reference) 順に統一し，「不良な alternative の自己比較は flip 0 を返す（自己比較では検出不能）」negative case を追加。
2. **名称**：`r64/hM64/hI64/f64sel` → `r32/hM32/hI32/f32sel`（NPZ key・console・provenance）。
3. **W₂ 感度（BLOCKER 2）**：修正案 B。OT に投入した **exact cluster subset** ごとに paired RMS ε を計算し，observed の各 seed について W₂_max 摂動上界 max_pairs(ε_j+ε_k)，null の各 replicate について同様の上界 → `delta_q99_bound = max_replicates`。**decision margin gate** `|W₂_max − q99| > observed_bound + delta_q99_bound`（seed・n_sub ごと）を official required（`G_w2_selection_decision_margin`）。full-pool RMS は `G_w2_full_pool_selection_rms_small` として診断に降格し「任意の subsample を bound しない」と注記。
4. **provenance／コメント**：`scan()` の default 削除（明示指定を強制），production コメント・W₂ 冒頭（finite-pool exceedance）・positive control（0.35）・`cross_selection_policy.status`（float64 primary を v1.2.4 で prospective に採用；A8b は性能 benchmark と sensitivity path；S2 は float32）を f64 primary に統一。

## 2. 強く推奨
5. **chunk の binding**：A8b CPU CSV の `l24_feature231` winner を dtype 別に読み，**float64 primary は chunk 2000**（76.7 s/10⁶・+0.099 GB），float32 sensitivity は chunk 20000（39.3 s/10⁶）。`G_a8b_chunk_binding`（両 winner の chunk と N=10⁶ を照合）を required に。「dtype と chunk の両方を A8b の f64 winner に合わせた」ことで，supersede は dtype 推奨のみ。
6. A10c の float32 感度は「**primary の pseudo threshold を固定した conditional sensitivity**」と provenance に明記。
7. self-test の順序統一と自己比較 negative case（上記 1）。

## 3. サンドボックス smoke（N=2×10⁴・fresh OUT）
`SMOKE_PASS`（53/53・4 component True）。calibration の cross-selection は今度こそ f32 vs f64 を比較（n=20000・配線 gate True）。W₂：exact subsample の observed bound ≤1.9e-6・`delta_q99_bound`=0，decision margin は全 seed・全 n_sub で成立。chunk binding True（2000／20000）。

## 4. 先生の作業（GO 後）
0. v1.2.5 を commit・push（v1.2.2〜v1.2.4 の実装報告を `results/step1_phaseA/A10_history/` に同梱）。1. fresh runtime で smoke。2. fresh runtime・fresh OUT で official（float64 primary は chunk 2000 で約 1.3 min/10⁶；全体 1.5〜2 h）。3. `a10_v1.2.5_{smoke,official}/a10_provenance.json`・`checkpoints/`・セル出力を返送。
