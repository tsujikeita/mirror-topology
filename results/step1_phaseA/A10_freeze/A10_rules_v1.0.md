# A10 rules v1.0（Step 1 rules v1.0 への転記文）
2026-09-12。出典：A10 v1.2.9 official（`A10_VALID` 61/61）・ChatGPT 最終監査（2026-09-12）§10。本書は Phase A の**設計・実装・推定量選択**の凍結であり，
global false-support 率や最終 W₂ trigger 閾値の科学的凍結ではない。

## R1. orientation clustering（CRN 単位）
- **1R : m z，m = 100**。根拠：E7_b1_A x₀⁽¹⁾・PR3-power-matched・Event B・N=10⁶ で m=10／100 各 2 反復；Q の差 CI（rep1・rep2・pooled）がすべて
  事前登録 practical-equivalence margin **Δ_m = log 1.10** 内，5 bootstrap seed すべてで等価，全 run が精度 gate（event-positive cluster ≥ 50・CI 相対半幅 ≤ 0.20・5-seed 幅 CV < 0.2）通過。
- Δ_m は engineering tolerance（Q の multiplicative discrepancy 10% を Phase A の MC 設計差として許容）。Q=3／10 の判定閾値近傍では 10% 差が判定を変え得るため，
  full grid では「m の選択による threshold crossing が無い」ことを併記する。cluster ESS 要件は superseded。

## R2. ℓ2–4 走査（selection／evaluation）
| 項目 | 値 |
|---|---|
| route | `l24_feature231`（A8b） |
| **selection dtype** | **float64**（A8 freeze の float32 推奨を A10 の stress evidence で supersede；A8b benchmark は性能結果として有効） |
| evaluation dtype | float64（凍結 ℓ2–4 B-stack） |
| sample_chunk | 2000（A8b official CPU の float64 winner；76.7 s／10⁶・+0.099 GB） |
| BLAS threads | 2（NumPy 同梱 OpenBLAS の pool を 2 に，他 pool ≤ 2） |
| 根拠 | float32 selection では Colab 2 threads で raw-axis flip 8.7×10⁻³/標本，非対蹠 flip 32/8×10⁶（plane-folded 角距離最大 85°・T₂ 差最大 14%）。Event B・Q は不変だが，axis と T₂ の一意性を primary path から除くため float64 を採用（コスト 1.3 min/10⁶） |

## R3. S2 走査（ℓ≤16・A8b 登録どおり float32 selection を維持）
- selection float32／evaluation float64／chunk 1024・axis block 3072／threads 2（A8 rules R3）。
- **axis semantics を明記**：float32 selection の raw axis は，S⁺ が float32 分解能内で同点の候補間（exact antipode だけでなく，稀に遠い非対蹠 plane）で
  blocking・BLAS・hardware により入れ替わる。scientific axis 出力は **plane-folded label と near-minimizer set**で報告し，T₂ は選択された representative の
  float64 B⁻ 行に依存する量として扱う（antipodal representative の B⁻ 行は同一でない場合がある）。Event B と Q の安定性は A10 の cross-selection gate
  （flip は selected S⁺ の相対差 < 1e-6 の near tie でのみ，Event B mismatch 率 ≤ 1e-5）で担保する。S2 の科学的採用は S4／exact validation gate まで HOLD。

## R4. global false-support 較正の実装（再走査なし）
- primary event：Event B = {T₁ ≤ T₁,obs ∧ T₂ ≤ T₂,obs}（A5 凍結）。pseudo 観測ごとに **2D 閾値** (T₁,p, T₂,p)。
- 各 family 点の (T₁,T₂,cluster_id) を 1 回保存し，pseudo ごとに sorted-T₁ searchsorted＋T₂ 条件で cluster 集計表を作る（brute-force 一致 gate）。
- Q の CI：paired cluster bootstrap（B=2000・cluster 再抽出行列を全 pseudo で共有）。分子 0 は Q=0 として保持，分母 0 かつ分子>0 は +inf，両 0 のみ除外，valid fraction ≥ 0.95 を gate。
- D：2D Gaussian KDE の **log 密度差**（`logpdf`；遠い尾部で pdf が underflow するため）。support = (Q 下側 CI ≥ 3) ∧ (logD > 0)。
- 必須 control：negative（独立等方 replicate・独立 bootstrap）support 率 ≤ 0.05；positive（T₁,T₂ を 0.35 倍した synthetic boosted 標本）は**観測閾値で** Q 下側 CI ≥ 3・Q ≥ 10・logD > 0。
- A10c は **one-point・one-system の pathway prototype**（false-support 0/200・Wilson 上側 0.019）であり，familywise global calibration（全 family・両系統・
  family prior 統合・n_pseudo ≥ 2000 または precision stopping）は Phase B/C の engine で行う。

## R5. W₂ 位置拡張トリガー
- 推定量：校正サンプルで whitening した (T₁,T₂) の exact 2D W₂（POT `emd2`・sqeuclidean・√），uniform weights，**cluster 単位 subsample**。
- 統計量：3 観測位置の **max pairwise W₂**。primary は位置ごとに独立 (R,z) stream；null は等方 pool から replicate ごとに disjoint な 3 cluster block の max。
  CRN 版（同一 (R,z)）は conservative diagnostic。閾値は quantile 法 `higher`；exceedance は finite-pool exceedance estimate（exact exchangeable MC p ではない）。
- 安定性（事前登録）：3 subsample seed の判定一致・n_sub 2000／5000 の判定一致・W₂_max の seed 間 spread ≤ 0.25・selection-path の decision margin
  （exact-subset coupling bound）。
- A10 実測（3 位置 mock：E7_b1_A base・E7_b2_A base・y-shift 0.12；registered p^(3) ではない）：n_sub=5000 で W₂_max 0.135–0.153 vs null q99 0.165（未発動）。
  **最終 trigger 閾値は registered p^(3)・B 増加または precision stopping で確定**（B=200 の q99 は粗い）。将来版では null replicate ごとの selection bound 配列も保存する。

## R6. exact version（Colab official）
Python 3.13.15・NumPy 2.1.3・SciPy 1.16.3・healpy 1.20.0・pandas 2.2.3・POT 0.9.7.post1・OpenBLAS 0.3.27（NumPy 同梱）。bit-level hash（求積節点等）は
NumPy 版依存のため gate にせず，数学的 gate（Gauss–Legendre 厳密性・D(R) の直交性／準同型／直接幾何／既知 z 回転）で担保する。
