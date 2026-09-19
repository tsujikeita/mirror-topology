# Step 1 研究計画 v0.4（v0.3再監査の4 BLOCKER対応・Phase C凍結候補）
2026-09-02。Claude作成。ChatGPT再監査（2026-09-02・PHASE A GO／PHASE C HOLD・4 BLOCKER）への
対応版。**v0.3からの変更点のみ**を記す。Phase Aは本版と並行して着手する。

---

## 0. 変更一覧

| # | 監査 | v0.4 |
|---|---|---|
| **B1** | T₂,obs中央域外でD_Mを主へ昇格させない | 昇格分岐を**削除**。観測phenotype gate `G_obs_selective` を導入。False なら「selection-adjusted target phenotype not confirmed」でfamily判定は inconclusive。D_M は常に secondary（§1） |
| **B2** | circle-undeterminedをexcludedとして再正規化しない | allowed / excluded / undetermined を区別。undetermined の prior mass は**残す**。undetermined mass を持つ family は partial-coverage・「support status not evaluable」。coverage fraction を報告（§2） |
| **B3** | importance sampling未定義 | 第1版から**IS を除外**：通常MC→事前定義×4拡張→inconclusive。IS は完全仕様付きの別登録拡張へ（§3） |
| **B4** | x₀写像・W₂閾値・拡張後分類 | family固有の生成行列 x₀=A_M(θ)u・CMBtopology規約の確認タスク・whitened W₂と有限サンプルnull百分位による閾値・拡張時は「provisional / position-sensitive」とし12位置完了後に最終分類（§4） |
| 7 | 3/10閾値のglobal較正 | 等方擬似観測で**判定規則全体**を適用し familywise false-support rate を報告（§5） |
| 8 | 絶対的予言適合 | Q_M・P_M(E)・P_iso(E)を必ず併記。「relative preference but poor absolute predictive fit」分類を追加（§5） |
| 9 | cluster水準の精度 | event-positive cluster ≥50・cluster ESS・paired cluster-bootstrap CIの安定（§6） |
| 10 | m=100感度 | 1点で m=10 vs 100 を比較（§6） |
| 11 | SeedSequence整数化 | stream・topology・parameter・observer の永続整数表（§7） |
| 12 | CRN平方根の固定 | principal symmetric square root・固有値順序・clip許容・SHA記録（§7） |
| 13,14 | CIの対称化 | unsupported も D_M 上側CI で定義。matched/native 分類を CI で定義（§8） |
| 15 | float32 | **既定float64のみ**。float32は使わない（argmin安定性検査を不要化）（§9） |
| 16 | SciPy版gate | `assert scipy.__version__ == EXPECTED` をhard gate（§9） |

---

## 1. 観測phenotype gate（B1）

selection-adjusted走査をデータに適用して T_obs=(T₁,obs, T₂,obs) を得た後：

```
G_obs_selective := q₁₆ ≤ T₂,obs ≤ q₈₄
```
（q₁₆・q₈₄は selection-adjusted 等方nullの T₂ から，校正サンプルで事前決定）

- **True**：selection調整後も「低S⁺＋正常S⁻」というStep 0のphenotypeが維持されたと判断し，
  Q_M を primary とする（v0.3 §3の規則どおり）。
- **False**：「**selection-adjusted target phenotype not confirmed**」と結論。family-level判定は
  **inconclusive（target phenotype not confirmed）**。D_M は secondary として報告してよいが
  **primary へ昇格させない**。
- v0.3 §2の「観測がイベント外なら P_M(E_sel) がゼロ近傍」という記述は**誤りとして削除**
  （E_sel はモデル実現の領域であり，観測がその外でも P_M(E_sel) は小さいとは限らない）。
- どちらの分岐でも E_sel の定義・分位・閾値は変更しない。

## 2. 円検出制約：analysis domain と coverage（B2）

用語：「circle constraint prior」ではなく **published circle non-detection に条件付けた analysis
domain**。各登録点のラベル：

| ラベル | 意味 | prior mass の扱い |
|---|---|---|
| allowed | 既存探索の被覆範囲で許容 | support計算に含める |
| excluded | 既存の非検出により観測的に排除 | 条件付き解析では mass 0 |
| undetermined | 適用可能な幾何・制約・実装が未確立 | **mass を残す**（除外・再正規化しない） |

- undetermined mass を持つ family：**partial-coverage result**・「family-level support status
  not evaluable」。allowed 部分だけで Q_M を作って family 判定に使うことは**しない**
  （available subset だけで support を作る選択バイアスを避ける）。
- 各 family で報告：registered prior mass・allowed mass・excluded mass・undetermined mass・
  f_covered = (π(allowed)+π(excluded))/π(registered)。
- allowed 部分の Q_M は「coverage-restricted exploratory value」として表に出すが判定に使わない。
- Phase A の調査で undetermined を減らすことが，判定可能な family を増やす唯一の道。

## 3. Monte Carlo 精度規則（B3：第1版はISなし）

```
通常MC（N=10⁶）
→ 精度gate未達なら 事前定義の拡張1回（N×4）
→ なお未達なら inconclusive（精度未達）
```

importance sampling は第1版から**除外**。導入する場合は**別の事前登録された方法拡張**として，
以下を全て固定してから：提案密度 q(x,R)・重み p/q・走査軸混合提案・有限重み条件・ESS閾値・
重み裾診断・中程度の裾で naive MC と一致すること・被覆/不偏性電池。
（注：単純な平均シフトは E[(x+μ)ᵀB⁺(x+μ)]=tr(B⁺C)+μᵀB⁺μ で S⁺ を**増やす**ため，低S⁺の提案には
ならない。v0.3の記述は不適切だった。）

## 4. 観測者位置（B4）

### 4.1 写像
x₀ = A_M(θ) u，u ∈ [0,1)³。A_M(θ) は family・パラメータごとの**基本領域生成行列**
（単位立方体を基本領域へ写す体積保存写像）。同じ design points u₁,u₂,u₃ を全 family・全サイズで
共有。Phase A で CMBtopology の x₀ 座標規約・生成子規約・基本領域・対称等価位置を確認し，
A_M(θ) の具体形を rules に固定。対称等価な位置は生成時に検査して回避（座標・seed・方法を記録）。

### 4.2 拡張トリガー
T̃ = Σ_iso^{-1/2}(T − μ_iso)（等方nullで whitening）で (T₁,T₂) を標準化し，3位置間の
2-Wasserstein 距離 W₂ を計算。閾値は**同一分布からの2独立サンプル（同サイズ）間の有限サンプル
W₂ null分布の99百分位**（等方nullで事前計算）。トリガー：W₂ > 閾値 または
max_k P(E_sel)/min_k P(E_sel) > 2。

### 4.3 拡張後の分類
```
3位置の結果 → archive（削除も改変もしない）
トリガー True → family分類 = provisional / position-sensitive
12位置段階（新規登録）完了 → 最終 family-level 分類
```
「第1波判定を変更しない」（v0.3）は撤回し，上記に置換。

## 5. 判定規則の global 較正と絶対的適合

### 5.1 familywise false-support rate
等方擬似観測（official ≥2000）の各々について：pseudo T_obs → 同一 E_sel 定義（分位は校正
サンプルから）→ 全 family の Q_M, D_M → support / strong-support 規則をそのまま適用 →
`any-family false support` を記録。報告：
P_iso(∃M: support rule_M = True) と P_iso(∃M: strong support_M = True)。
3/10 の閾値は変えないが，それが対応する global false-support rate を必ず併記する。

### 5.2 絶対的予言適合
常に Q_M・P_M(E_sel)・P_iso(E_sel) を併記。P_M(E_sel) < 10⁻⁴（事前固定）の場合は
「**relative preference but poor absolute predictive fit**」と分類し，support candidate とは
別ラベルにする。

## 6. cluster 水準の精度と m の感度

- 精度gate（追加）：event-positive orientation cluster 数 ≥ 50 AND cluster ESS ≥ 200 AND
  paired cluster-bootstrap CI が有限かつ安定（bootstrap 再抽出で CI 幅の変動 <20%）。
  個々の z hit 数より cluster-bootstrap CI を優先。
- m の感度：1モデル点（E7・L=1.0・x₀^(1)）で m=10 と m=100 を比較（P(E_sel)・Q_j・CI幅・
  cluster ESS）。差が CI 内なら m=100 を採用，外なら m=10 で全点を再設計（Phase A で決定）。

## 7. 乱数と CRN の固定

- `SeedSequence([MASTER_SEED, wave_id, topology_id, parameter_id, observer_id, batch_id, stream_id])`
  の全要素を**整数**に。永続表：STREAM={gaussian:0, rotation:1, calibration:2, pseudo:3,
  bootstrap:4}・TOPOLOGY={E1:1,…,E10:10}・parameter_id / observer_id は rules の登録表の行番号。
- CRN の平方根：**principal symmetric square root** C^{1/2}=V diag(√λ) Vᵀ（固定実基底）。
  固有値は降順・微小負値の clip 許容 1e-12·λ_max・PSD 許容（T1 と同一）・各点の C^{1/2} の SHA を
  provenance に記録。Cholesky は使わない（固有ベクトル符号・縮退部分空間の回転・順序で
  same-z pairing が変わるため）。

## 8. CI による対称な定義

- unsupported（grid上）：Q_M の95%上側CI < 1 AND **D_M の95%上側CI ≤ 1**
- matched / CT-native の分類（各系統）：support = Q 下側CI > 1／neutral = CI が1を含む／
  opposite = Q 上側CI < 1。strong support の「同方向」はこの CI 分類で判定（点推定ではない）。
- 分類行列（v0.3 §12）はこの CI 分類の組合せで埋める。

## 9. 数値・環境の固定

- **float64 のみ**（float32 は使わない。argmin 安定性検査は不要）。
- `assert scipy.__version__ == EXPECTED_SCIPY_VERSION`（Colab 実環境で確定した版）を hard gate。
  numpy・healpy・camb も同様に exact version gate。

## 10. Phase A（GO・v0.3 §15のまま）に追加する項目
- CMBtopology の x₀ 規約・基本領域・生成行列 A_M(θ) の確認（§4.1）
- W₂ の有限サンプル null（§4.2）の事前計算設計
- m=10/100 比較（§6）
- 判定規則の global 較正の実装設計（§5.1）
- SciPy 版の確定（§9）

## 11. 凍結前チェックリスト（Phase C）
- [ ] B1–B4 の反映を rules 本文で確認
- [ ] Phase A 実測（bridge・歴史復元・x₀規約・円制約調査・ベンチマーク・Haar/moment/Imhof）
- [ ] 円制約ラベル確定後に prior を定義
- [ ] G_obs_selective の分位を校正サンプルから確定（観測 T₂ を見る前）
- [ ] 全 hard gate の一覧と閾値
- [ ] 実行前監査 → commit
