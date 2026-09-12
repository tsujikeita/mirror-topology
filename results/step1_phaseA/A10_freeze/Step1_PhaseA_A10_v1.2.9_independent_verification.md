# Step 1 Phase A-10 v1.2.9 成果物の独立検算報告（smoke／official）— 訂正版
2026-09-12（初版）／同日訂正（§5・§5b）。Claude作成。ChatGPT宛（official 出力監査用）。対象：先生から受領した `A10_results.zip`（smoke／official の provenance・checkpoints・console log）。

## 0. 結論
- **smoke：`SMOKE_PASS`（54/54）**，**official：`A10_VALID`（61/61・4 component 全 True）**。official は純正 notebook（live == origin/main == source-only `731cb898…`＝納品 v1.2.9）で，期待版（Python 3.13.15・NumPy 2.1.3・SciPy 1.16.3・healpy 1.20.0・POT 0.9.7.post1）と完全一致，NumPy 同梱 OpenBLAS 0.3.27 が 2 threads。11 出力ファイルの SHA は provenance 記録と全一致。generation call は 12 個で一意。
- 診断 gate の False は `G_a9_quadrature_hashes`（NumPy 版依存の bit hash・設計どおり）と `G_m_f32_f64_no_nonantipodal_flip`（後述の発見）のみ。
- **m 判定：m=100 採用**（両 m とも usable，差 CI がすべて ±log1.10 内，5 bootstrap seed すべてで等価成立）。
- W₂ pathway：3 位置 mock の W₂_max は n_sub=2000／5000 とも null q99 を下回り，3 seed・両 n_sub で判定一致，selection-path の decision margin 成立。
- 較正経路（one-point prototype）：false-support 0/200（Wilson 上側 0.019），negative control 0/200，positive control（観測閾値）Q=97.9・下側 CI 95.0・logD=2.87 で発動。

## 1. Engine（A10a）
| 量 | A10 official（N_cal=2×10⁵） | A5 map-based null（n=1000） |
|---|---|---|
| T₁ 中央値 | 120.4 | 118.5（bootstrap 95% CI [115.4, 122.8]） |
| P(T₁ ≤ obs) | 0.0149 | 0.0150（Wilson [0.0091, 0.0246]） |
| P(Event B) | 0.0037 | 0.0040（Wilson [0.0016, 0.0102]） |
map-free の等方エンジン（float64 primary・chunk 2000）が A5 の map-based null を三つの量で再現。calibration の f32 sensitivity：flip 1726/2×10⁵（全 antipode），T₂ 差最大 2.1e-3，Event B mismatch 0。

## 2. m 感度（A10b・E7_b1_A x₀⁽¹⁾・PR3-power-matched・Event B）
| run | Q | 95% CI | 相対半幅 | ev⁺ clusters M/I | P_M | P_I |
|---|---|---|---|---|---|---|
| m10_rep1 | 1.3465 | [1.3085, 1.3833] | 0.028 | 4808/3591 | 0.00492 | 0.00365 |
| m10_rep2 | 1.2994 | [1.2658, 1.3371] | 0.027 | 4705/3624 | 0.00481 | 0.00370 |
| m100_rep1 | 1.3305 | [1.2927, 1.3662] | 0.028 | 3915/3111 | 0.00493 | 0.00370 |
| m100_rep2 | 1.3044 | [1.2684, 1.3405] | 0.028 | 3861/3089 | 0.00487 | 0.00373 |
- 差 CI：rep1 [−0.050, 0.028]・rep2 [−0.036, 0.043]・pooled [−0.033, 0.024]（すべて ±0.0953 内）。反復間 |ΔlogQ|：m=10 0.036・m=100 0.020（bootstrap SE と整合）。
- 独立再計算：保存 cluster 集計表から Q と paired cluster bootstrap CI を再構成 → m10_rep1 Q=1.3465，logCI [0.267, 0.324]（provenance [0.269, 0.324]）；m100_rep1 Q=1.3305，logCI [0.260, 0.313]（provenance [0.257, 0.312]）。一致。
- **予備的な科学的観察（1 点・設計判定には使わない）**：E7_b1_A の ℓ2–4・matched 系統で Event B の support ratio は **Q ≈ 1.30–1.35（CI ±0.04）**。「support」閾値 3 には遠い。
- **float32 sensitivity（重要な設計 evidence）**：Colab 2 threads では flip が **≈8.7×10⁻³/標本**（8.6k–8.9k/10⁶；サンドボックス 1 thread の 5×10⁻⁵ の 170 倍），**非対蹠 flip 32/8×10⁶**，うち plane-folded 角距離が **59°・85°**の遠い plane への flip が 2 件（S⁺ は 1e-7 相対で同点，T₂ は 10–14% 変わる）。Event B mismatch は 0，Q は両 path で同一（hits 同一）。→ ℓ2–4 の float64 primary 採用の妥当性を実データで裏づけ。S2（float32 維持）の rules では「axis は near-minimizer set／plane-folded で報告し，T₂ は選択 representative 依存」を明記する必要。

## 3. 較正経路（A10c・one-point prototype・m=100・n_pseudo=200）
false-support 0/200（Wilson 上側 0.019），Q_pseudo 中央値 1.05，bootstrap valid fraction 1.0。negative control（独立等方・独立 bootstrap）0/200，Q 中央値 1.000。positive control（T₁,T₂×0.35）：観測閾値で Q=97.9・下側 CI 95.0・logD=2.87（pseudo では中央域で比が 1/P_iso に頭打ち，最小 logD −772＝v1.2.8 で pdf が underflow した箇所）。f32 conditional sensitivity：support 配列差 0，hit table 変化 7/16 セル，|ΔlogQ| ≤ 1.7e-4。

## 4. W₂ pathway（A10d・3 位置 mock・float64 primary・cluster 単位 subsample・B=200）
| n_sub | primary W₂_max（3 seed） | null q99／q95／median | finite-pool exceedance | CRN 診断 | δ_q99 bound |
|---|---|---|---|---|---|
| 2000 | 0.224 / 0.212 / 0.201 | 0.236 / 0.217 / 0.182 | 0.015 / 0.075 / 0.179 | 0.132 / 0.149 / 0.131 | 3.5e-3 |
| 5000 | 0.135 / 0.153 / 0.149 | 0.165 / 0.144 / 0.127 | 0.209 / 0.020 / 0.030 | 0.102 / 0.097 / 0.109 | 2.2e-3 |
- 判定：全 seed・両 n_sub で **q99 未満**（一致），seed spread ≤ 0.25，selection-path の decision margin 成立（observed bound ≤ 1.3e-6）。null 配列から q99 を再計算し一致。
- 解釈：3 位置 mock（E7_b1_A・E7_b2_A・y-shift 0.12）の (T₁,T₂) 分布差は，n_sub=5000・99% では検出されない（95% 付近）。W₂ 推定量と null 構成（disjoint 3 block）は動作し，n_sub 2000→5000 で null q99 が 0.236→0.165 と縮む一方 observed も縮む（有限標本の床）。最終 trigger 閾値は登録 p^(3) と B 増加／precision stopping で確定する（provenance の caveat どおり）。

## 5. 時間（console log 実測・2026-09-12 訂正）
m run 137–216 s（4 run 合計 ≈700 s），W₂ pool 生成 126 s，W₂ null n_sub=2000 337 s（5.6 分）・n_sub=5000 2581 s（43 分）。主要計算の合計 ≈63 分＋setup。
（初版で「12 分／97 分・全体 2 時間」と書いたのは console の累積表示の読み違い。）

## 5b. bootstrap 再計算の注記
§2 の「独立再計算」は cluster 集計表から**新しい乱数**で paired cluster bootstrap を引き直したもので，provenance の CI とは MC 誤差の範囲で近い（logCI 端点差 ≤ 0.003）。freeze 成果物に保存された 5 seed の bootstrap 分布そのものから再計算すると provenance の CI と bit 一致する（ChatGPT 監査 §6・§9 で確認）。

## 6. 提案する次段
1. 本報告＋成果物を ChatGPT の official 出力監査へ。
2. GO 後：`results/step1_phaseA/A10_freeze/`（notebook v1.2.9・smoke／official provenance・checkpoints・console log・実装報告 v1.2.5–v1.2.9・監査・A10_history・freeze manifest）→ tag `step1-phaseA-A10-freeze-v1.0`。
3. A10 設計ノート v1.1（実測値を転記）→ `Step1_rules_v1.0_draft`（W₂ 推定量・m=100・較正の再走査なし実装・ℓ2–4 float64 selection／S2 float32・axis semantics・exact version）。
