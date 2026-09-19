# Step 1 研究計画 v0.5（設計凍結候補・残る4定義の確定）
2026-09-02。Claude作成。ChatGPT再監査（v0.4・PHASE A UNCONDITIONAL GO／PHASE C: 4 DEFINITIONS
PENDING）への対応。**本版で設計文書の往復を終え，Phase Aへ移行する**。以後の変更は Phase A の
実測を反映した `Step1_rules_v1.0_draft` に直接書き，実行前監査に出す。

---

## 定義1：観測phenotypeの確認（science flag・audit gateと分離）

selection-adjusted 等方null（校正サンプル）から，データ走査結果を見る前に固定：

```
p1_obs              := P_iso(T₁ ≤ T₁,obs)
OBS_SPLUS_DEPLETED  := p1_obs ≤ α_dep            （α_dep = 0.05・Step 0の凍結軸条件付きp≤1e-3との
                                                   連続性はrulesに注記。値は結果を見る前に固定）
OBS_SMINUS_NORMAL   := q₁₆ ≤ T₂,obs ≤ q₈₄
OBS_TARGET_CONFIRMED:= OBS_SPLUS_DEPLETED AND OBS_SMINUS_NORMAL
```

- これらは **SCIENCE_FLAGS**（観測された科学的結果）であり，`G_` 接頭辞の **audit gate**
  （コード・provenance・数値の妥当性）とは別空間に置く。provenance にも別キーで記録。
- **OFFICIAL=True と OBS_TARGET_CONFIRMED は独立**。phenotype が確認されなくても official run は
  完全に有効で，科学的結論が「selection-adjusted target phenotype not confirmed」になるだけ。
- p1_obs が大きい場合は，それ自体が重要な結果（固定軸では極端に低く見えたS⁺が，選択調整後は
  異常でない）として主報告に含める。
- OBS_TARGET_CONFIRMED=False のとき，family-level 判定は inconclusive（target phenotype not
  confirmed），D_M は secondary のまま（v0.4 §1）。

## 定義2：円制約後の prior 正規化（第1版＝conditional analysis）

登録時 prior π₀(j|M)，allowed 集合 A_M。第1版は **published circle non-detection に条件付けた
conditional analysis**：

```
w_cond(j|M) = π₀(j|M)·1[j∈A_M] / Σ_k π₀(k|M)·1[k∈A_M]      （allowed 内で再正規化）
s_M         = Σ_j π₀(j|M)·1[j∈A_M]                        （surviving mass・別報告）
```

- 解釈：Q_M は「円非検出を生き残った domain 内での Step 1 比較」，s_M は「登録 prior mass のうち
  円制約を生き残った割合」。両方を必ず併記。
- **undetermined mass を持つ family**：A_M が確定しないため w_cond を定義しない。
  「family-level support status not evaluable（partial coverage）」と報告し，
  f_covered を併記（v0.4 §2）。
- **Q_mix**：いずれかの family に undetermined mass があれば，判定可能 family だけで再平均
  **しない**。`full mixture = not evaluable` とし，参考値を出す場合は
  「partial-coverage exploratory mixture」と明記。
- excluded mass を 0 として含める joint evidence（円検出尤度×Step 1 予言尤度）は第1版では
  行わない。行うなら別設計として登録。

## 定義3：W₂ トリガーの計算法

- **集約**：3位置の3ペアについて W₂ を計算し，**max pairwise** を用いる。
- **推定量**：固定サイズ部分サンプル（n_sub=20,000／位置・seed固定・stream `calibration`）の
  **exact 2D W₂**（POT `ot.emd2`・許容誤差固定）。sliced/Sinkhorn は使わない
  （exact が n_sub=2×10⁴ で計算可能なことを Phase A でベンチマーク。不可なら sliced Wasserstein
  に切替え，射影数 500・seed 固定を rules に記載）。
- **whitening**：T̃ = Σ_iso^{-1/2}(T−μ_iso)。Σ_iso・μ_iso は等方 selection-adjusted 校正サンプルから。
- **null**：同一分布（等方）からの2独立サンプルで，**同じサンプルサイズ・同じ orientation
  clustering（1R:100z）・同じ部分サンプリング・同じ推定量・同じ whitening** により W₂ の有限
  サンプル null を作り，99百分位を閾値とする（B_null=200 反復）。
- **イベント比トリガー**（max_k P_k / min_k P_k > 2）は各 P_k(E_sel) が精度 gate を通過した後
  のみ評価。いずれかの P_k が 0（hit なし）の場合は **trigger=True**（保守側）。

## 定義4：global false-support 較正の合否と robustness の扱い

- **較正対象**：**PR3_Commander の primary-map core decision rule のみ**（他マップの robustness
  条件は較正に含めない）。
- **合格基準**（事前固定）：
  ```
  support label usable        : familywise false-support rate の95%上側CI ≤ 0.05
  strong-support label usable : familywise false-support rate の95%上側CI ≤ 0.01
  ```
- **較正 FAIL 時**：閾値は結果後に変更しない。該当ラベルを**使用せず**，分類は
  「descriptive / calibration-failed」とする。閾値を見直す場合は **モデル結果を見る前に**
  新しい rules 版として登録し直す。
- **robustness**：PR3 成分分離4本の「同方向」は **descriptive robustness qualifier** とし，
  strong-support の formal 条件から外す（4マップ相関 pseudo-data ensemble を作らない限り
  較正できないため）。strong support の formal 条件は：Q_M 下側CI ≥ 10 AND D_M 下側CI > 1 AND
  matched/CT-native が CI 分類で同方向。robustness は結果表のラベルとして併記。

## 強化項目（rules v1.0 draft に組み込む）

| 項目 | 確定内容 |
|---|---|
| cluster bootstrap の単位 | orientation cluster index を再抽出。cluster 内 100 z はまとめて保持。model/iso の対応 cluster は paired で保持。family 内全点・max-R でも同一 cluster ID を共有 |
| cluster 精度指標 | ESS を使わず，**event-positive cluster 数 ≥ 50 AND cluster-bootstrap CI 精度**（相対半幅 ≤ 20%）で gate（第三案） |
| CI 安定性の定義 | bootstrap seed を変えて 5 回再実行，CI 幅の変動係数 < 0.2 |
| immutable ID | parameter_id・observer_id は登録点ごとに**明示的な不変整数**を付与（表の行番号は使わない） |
| 平方根の hard gate | ‖S−Sᵀ‖_F/‖S‖_F < 1e-12，‖SSᵀ−C‖_F/‖C‖_F < 1e-10。provenance に λ_min_raw・clip 量・post-clip C の SHA・S の SHA・残差 |
| environment manifest | hard gate：Python・NumPy・SciPy・healpy・CAMB の exact version。archive：numba・spherical・quaternionic・BLAS/LAPACK backend・platform・`pip freeze` |
| noise stress test の判定 | 効果量基準：\|Δ log Q_j\| < 0.1 AND support category 不変 AND 判定境界からの margin の 20% 未満。MC CI との比較は併記のみ |
| float64 のみ・exact version gate | v0.4 §9 のまま |

## Phase A 着手（順序・v0.3 §15＋v0.4 §10 の統合）

1. 二次形式 bridge 電池（A3a/b/c・G_data_link・全軸 random-vector・±dedup・タイ規則）
2. 歴史的軸選択手順の復元（plane-excised-mirror 履歴）→ exact / surrogate の判定
3. CMBtopology の x₀ 規約・基本領域・生成行列 A_M(θ)・対称等価位置の確認 → u₁..u₃ 生成
4. **円検出制約の族別計算法調査**（E7/E8 非可向を含む）→ allowed/excluded/undetermined
5. 全軸走査の Colab 実環境ベンチマーク（float64・chunk・peak memory）
6. Haar 電池・2次モーメント電池・Imhof/Davies
7. W₂ 推定量のベンチマーク（exact vs sliced）と null 設計
8. m=10/100 感度（1点）
9. 判定規則 global 較正の実装設計（primary-map core rule）
10. SciPy 等の exact version 確定

Phase A の実測を添えて **`Step1_rules_v1.0_draft`** を作成 → 実行前監査 → commit → smoke → official。
