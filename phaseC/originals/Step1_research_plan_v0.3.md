# Step 1 研究計画 v0.3（v0.2再監査への対応・Phase C前の凍結候補）
2026-09-02。Claude作成。ChatGPT再監査（2026-09-02・PHASE A CONDITIONAL GO／v0.3 BEFORE
PHASE C）への全面対応版。**v0.2からの変更点のみ**を記す（変更のない節はv0.2のまま有効）。

---

## 0. v0.2→v0.3 変更一覧（監査§24の10項目＋即時修正＋推奨）

| # | 監査 | v0.3 |
|---|---|---|
| 即時 | §2 `Rotation.random(seed)`はAPI誤り | **実環境で確認**：`Rotation.random(123)`は**123個の回転を返す**（seedではない）。正：`Rotation.random(num=N, rng=np.random.default_rng(seed))`。SciPy版・API・seed・N_HAARをrulesに固定（§1） |
| 1 | 主統計と判定規則のねじれ | **family-level prior-integrated event ratio Q_M を主評価量**，密度比 D_M を secondary とし，判定規則を Q_M の95%下側CIで定義（§3） |
| 2 | family-level積分 | 正式判定はfamily単位。点ごとのR_jは exploratory（§3） |
| 3 | 離散/連続priorの混在 | **離散prior（第1波）**を採用し台形則を削除。各トポロジーの「L」の物理的意味を固定（§4） |
| 4 | x₀ 3点 | p^(3)の明示式・無次元座標u₁..u₃をサイズ間で共有・対称等価回避・**拡張規則**を事前登録（§5） |
| 5 | 「conservative」の名称 | **registered all-axis surrogate**に改名。保守性は検証されるまで主張しない（§6） |
| 6 | 円検出制約 | トポロジー別に幾何量を記録・非可向多様体は専用扱い・**Phase Aの調査タスク＆BLOCKER**（§7） |
| 7 | MC精度停止 | 最小ヒット数・相対CI幅・事前定義した拡張・importance sampling／inconclusive（§8） |
| 8 | n_pseudo | smoke 200／**official ≥2000またはprecision stopping**・fitting sampleと独立化（§8） |
| 9 | CRN/bootstrap単位 | orientation再利用方針を**option B（1R : m z）**に決定（benchmark根拠）・paired cluster bootstrap（§9） |
| 10 | 計算予算 | **Phase Aベンチマーク実施済み**：231次元対称特徴でN=10⁶×1536軸=約0.7分/点（§10） |
| 推奨 | SeedSequence | namespaced seed・stream分離（§9） |
| 推奨 | Haar電池の効果量 | KS p値＋平均/共分散の許容差・Holm補正・固定α（§11） |
| 推奨 | 解析的2次モーメント電池 | E,Var,Covのtr公式 vs MC・Imhof＋Davies（§11） |
| 推奨 | 名称・分類 | physical-unscaled→**CT-native-unscaled**・matched×native分類行列（§12） |
| 推奨 | robustness「同方向」定義 | sign(log Q_M)で定義・記述的ラベルのみ（§13） |
| 推奨 | noise stress test | 1点で実施（§14） |
| 条件 | E_sel の分位 | selection-adjusted等方T₂から・校正/評価サンプル分離・再定義禁止・CI必須（§2） |

---

## 1. Haar サンプラーの仕様（即時修正・rules固定）

```python
from scipy.spatial.transform import Rotation
import numpy as np
rng  = np.random.default_rng(seed_from_SeedSequence)      # §9のstream 'rotation'
rots = Rotation.random(num=N_HAAR, rng=rng)               # ← 位置引数はseedではなく個数
```
- SciPy **1.17.1**（Colab実環境の版はPhase Aで確認して固定）。`rng=`キーワード（旧版は`random_state=`）
- N_HAAR：§9のoption Bで決定（初期値10⁴）
- 実装後にHaar電池（§11）を通すまで使用しない

## 2. selective-depletion event（条件付き承認への対応）

E_sel = { T₁ ≤ T₁,obs ,  q₁₆ ≤ T₂ ≤ q₈₄ }

- **q₁₆・q₈₄は，同一のselection-adjusted走査を施した等方nullの T₂ = S⁻@argmin(S⁺) から取る**
  （固定pix1134のS⁻ null分位は使わない）
- **校正サンプル**（分位決定用・seed stream `calibration`）と**評価サンプル**（P_iso(E_sel)用）を分離
- 観測のT₂が中央域外でも定義を変更しない（その場合はP_M(E_sel)がゼロ近傍となり，
  「イベント定義は観測を含まない」と報告し，密度比D_Mへ主判定の重心を移すことをrulesに事前記載）
- イベント比には必ずCI（§8・§9）

## 3. 主評価量と判定規則の一致（家族単位）

各トポロジー族 M（E1, E2, E7, E8）について：

- **Q_M = Σ_{j∈M} w_{j|M} P_j(E_sel) / P_iso(E_sel)**  ——主評価量（イベント比・prior積分）
- **D_M = Σ_{j∈M} w_{j|M} p̂_j(T_obs) / p̂_iso(T_obs)** ——secondary（密度比・KDE監査付き）
- 点ごとの R_j・Q_j は exploratory（表には出すが判定に使わない）
- 任意で equal-family-prior mixture Q_mix = mean_M Q_M を併記

判定（実データを見る前に固定）：
```
support candidate        : Q_M の95%下側CI ≥ 3  AND  D_M が同方向（log D_M > 0）  AND  estimator audit PASS
strong support candidate : Q_M の95%下側CI ≥ 10 AND  D_M の95%下側CI > 1        AND  robustness許容（§13）
                           AND  matched/CT-native の両系統で同方向（§12）
post-selection cond. fit : 固定軸条件付きで支持・走査で不支持
unsupported (grid上)     : Q_M の95%上側CI < 1  AND  D_M ≤ 1  （allowed点で構成した family）
inconclusive             : 上記いずれでもない／estimator audit FAIL／精度gate未達
```
主張範囲：registered grid・registered observer configurations 上の言明に限定。

## 4. サイズ prior（離散に確定）と「L」の定義

- **離散prior**：登録サイズ5点 {0.7, 0.85, 1.0, 1.2, 1.5}×L_LSS の各点に，allowed点のみで正規化した
  一様重み（family内）。台形則は**使わない**。連続priorは第2波以降で別途登録。
- 「L」の物理的意味（rules固定・CMBtopologyの規約に従う）：各族の**既定セルの全辺を一様に
  スケール**する係数。E1：L_x=L_y=L_z=L。E2：同上（半回転軸=z）。E7：LAx=LAy=L1y=L2z=L，
  L2x=L（既定形状・glide既定値）。E8：LAx=LBz=LCy=L，LAy=LBx=0。単位は L_LSS（CMBtopologyの
  距離規約で L_LSS を定義し，数値をrulesに記載）。
- family prior：4族に等重み。within-family prior と family prior を分離して記録。

## 5. 観測者位置（第1波pilot）

第1波の予言分布は
p^(3)(T | M, θ) = (1/3) Σ_{k=1}^{3} ∫ p(T | θ, x₀^(k), R, M) dR
と定義し，**連続周辺化とは呼ばない**。

- x₀^(k) = u_k ⊙ (基本領域の辺長)：**無次元座標 u₁,u₂,u₃ を全サイズ・全族で共有**
  （Phase Aで固定seedから一様生成し，対称等価な位置を避けるよう検査してrulesに座標を列挙）
- E1は等質なので x₀ 非依存（1点）
- **拡張規則（事前登録）**：ある(族,θ)で3位置間の P(E_sel) の max/min > 2，または (T₁,T₂)分布の
  2-Wasserstein距離が事前閾値（等方null分布のスケールの10%）を超える場合，次段階で12位置へ拡張
  （新段階として登録・第1波の判定は変更しない）

## 6. 選択調整の名称（改名）

歴史的軸選択手順（Phase A §5.2で復元）を完全再現できた場合のみ「exact historical selection
correction」。それ以外は **registered all-axis surrogate**（all-axis selection-adjusted surrogate
analysis）と呼び，「conservative」は次の両方が確認された場合に限って用いる：
(a) 歴史的探索が同一マップ・帯・統計・前処理での軸部分集合であったこと，(b) シミュレーションで
surrogateが歴史的手順より P(E_sel) を系統的に小さくする（または同等）こと。

## 7. 円検出制約（トポロジー別・Phase AのBLOCKER）

各モデル点に記録：多様体パラメータ・x₀・**最近接クローン距離（x₀依存）**・injectivity半径／
最短ループ長・円の開き角・円中心間角距離・Planck探索の被覆（開き角範囲・相関閾値）との対応・
適用した出典/実装・allowed/excluded。

- **E7/E8は非可向**：可向多様体用の閾値・コードを流用しない。非可向ホロノミー（glide reflection等）
  の円対を専用に扱う。
- Phase Aの調査タスク：各族について計算法と出典を確定。**確定できない族は「circle status
  undetermined」とし，support prior から除外して報告のみ**（判定に入れない）。
- allowed/excluded ラベルの確定前に prior を定義しない（§3・§4の重みはラベル確定後）。

## 8. Monte Carlo 精度規則

- **イベント推定の精度gate**：event hits ≥ 100 AND 相対CI半幅 ≤ 20%（P_iso(E_sel)・P_j(E_sel)とも）
- 未達時：(1) 事前定義した拡張（サンプル数×4，1回のみ），(2) なお未達なら importance sampling
  （提案分布：T₁方向へシフトした等方分布・rulesに記載）または **inconclusive**
- **max-R 較正**：smoke n_pseudo=200／**official n_pseudo ≥ 2000 または precision stopping**
  （P_iso(max R ≥ obs) の95%CI半幅 ≤ 0.01 AND 超過数 ≥ 50）。密度推定の fitting sample と
  pseudo-data は独立 stream から生成

## 9. 乱数・再利用・bootstrap（確定）

- **Seed**：`np.random.SeedSequence([MASTER_SEED, wave_id, topology_id, parameter_id, observer_id,
  batch_id, stream_id])`。stream_id ∈ {gaussian, rotation, calibration, pseudo, bootstrap}
- **orientation再利用：option B**（1つのRに m=100 個の独立 z）。N=10⁶ に対し N_HAAR=10⁴。
  根拠：D(R)構築（21×21 Wigner表現）が回転ごとのコストを支配し，231次元特徴法では x への
  回転適用は無視できるため。cluster = R。
- **CRN**：等方とモデルで同一 (z_i, R_i) を使用。CIは **paired cluster bootstrap**（sample ID
  (z,R) をペアで再抽出・cluster=R・B=1000）。family積分・max-R でも sample ID を共有クラスタとして
  扱う。CRNなしの検算を1点で実施。
- バッチ：10バッチ×10⁵（各バッチは異なる R 集合）。バッチ間分散による CI を bootstrap CI と併記

## 10. 計算予算（Phase Aベンチマーク・サンドボックス実測）

**231次元対称特徴法**：f(x)=vech(xxᵀ)（非対角は2倍重み），b_a=vech(B_a) として
S_a = f(x)·b_a。走査は行列積 (N×231)·(231×A)。実測（CPU BLAS・A=1536）：N=2×10⁴で0.78秒
→ **N=10⁶で約0.7分/モデル点**。直接計算との差 0。
- S⁺のみ全軸で計算→argmin保存→S⁻は選択軸のみ（(N×231)·(231×1)相当）
- chunk=2×10⁴ でメモリ常時 <1GB（S⁺配列246MB/chunk）
- float32 vs float64 の電池（相対差 <1e-6 なら float32 許容・既定は float64）
- 50点×2系統（matched/native）×走査 ≈ 70分＋共分散生成6時間 → **共分散生成が律速のまま**
- Colab実環境（GPU有無）でのpeak memory・N=10⁴/10⁵/10⁶の再ベンチマークをPhase A冒頭に置く

## 11. 検証電池の追加

- **Haar電池**：RᵀR=I・det=+1（全サンプル・1e-12）／ẑ像の平均（|mean|<3σ_N）・共分散
  （‖Σ−I/3‖_max<0.01）／cosθ・φ のKS（α=0.01・Holm補正）／左右不変性／実調和表現の準同型性
  D(QR)=D(Q)D(R)（1e-10）／direct-geometry点別検証（T1 B1/B2型・1e-10）。
  **p値と効果量の両方**を固定（大Nでの過敏さ対策）。
- **解析的2次モーメント電池**（固定Ω）：E[Q]=tr(BC)・Var=2tr(BCBC)・Cov=2tr(B_iCB_jC) vs MC
  （n=10⁶で3σ以内・S⁺,S⁻,S⁺S⁻共分散）。
- **半解析ベンチマーク**：P(S⁺≤s|Ω) を Imhof 法で計算（3向き×3点），1点で Davies 法とも照合。
- **二次形式bridge**（v0.2 §5.1のまま）：B対称・PSD・A3a/b/c・G_data_link・全軸random-vector・
  ±dedup・タイ規則。

## 12. 名称と分類行列

- `physical-unscaled` → **`CT-native-unscaled`**（pinned CMBtopologyのnative宇宙論による予測。
  PR3宇宙論での物理再計算ではない）
- `PR3-power-matched` は morphology-only covariance experiment（**主解析**）

| matched | CT-native | 解釈 |
|---|---|---|
| support | support | strongest candidate |
| support | neutral | morphology-only candidate |
| support | opposite | model-definition sensitive |
| unsupported | support | native power-difference driven |
| unsupported | unsupported | registered design unsupported |

strong support は両系統同方向を要件とする（§3）。

## 13. robustness の定義

「同方向」= sign(log Q_M) の一致（PR3成分分離4本中3本以上）。マップは独立sky realizationでは
ないため binomial evidence とせず，**記述的ラベルのみ**。不一致は平均化せず表で報告。
PR4・単一周波数はv0.2 §9の役割のまま。

## 14. ノイズ stress test（1点）

主判定に用いる1モデル点（E7・L=1.0・x₀^(1)）について，低ℓノイズ共分散（CMBanomに含まれる
half-mission差分 or NPIPE simsから推定・利用可能なものを Phase A で確認）を加算し，Q_j の変化を
報告。変化が Q_j の CI 内なら「noise-insensitive」，外なら主結論に注記。単一周波数マップは
stress test 扱いのまま。

## 15. Phase A の作業項目（確定・順序）

1. `Rotation.random` API修正とSciPy版固定（済：仕様§1）
2. 二次形式bridge電池（A3a/b/c・G_data_link・全軸battery）
3. 歴史的軸選択手順の復元（plane-excised-mirror履歴）
4. 観測者位置の無次元座標 u₁..u₃ の生成と対称等価検査
5. **円検出制約の計算法調査（族別・非可向を含む）**——BLOCKER
6. 全軸走査ベンチマーク（Colab実環境・§10の再実測）
7. 独立null較正/評価サンプルの設計
8. Haar電池・2次モーメント電池・Imhof/Davies

Phase Aの実測を添えて **v1.0規則を凍結 → 実行前監査（Phase C）**。

## 16. 未決事項（Phase Aで確定・rulesへ）
- 円検出制約の族別計算法（§7）
- ノイズ共分散の入手可能性（§14）
- 歴史的手順の復元可否と surrogate の保守性検証（§6）
- Colab実環境での計算予算とfloat32可否（§10）
- L_LSS の数値と CMBtopology 距離規約（§4）
