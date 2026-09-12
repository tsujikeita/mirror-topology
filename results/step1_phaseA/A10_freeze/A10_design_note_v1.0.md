# Step 1 Phase A-10 設計ノート v1.0：W₂ 推定量・m 感度・global 較正
2026-09-11。Claude作成。研究計画 v0.5（定義3・定義4・§6・強化項目）を，Phase A の実測（A5・A8・A9・A11）を踏まえて
実装可能な形に確定する。**目的は `Step1_rules_v1.0_draft` に転記できる粒度の規則を書くこと**。本ノートは調査段階の文書であり，
ここでの数値は設計根拠として用い，凍結成果物としては扱わない（A1–A3 報告の付記と同じ位置づけ）。

対象は研究計画 v0.5「Phase A 着手」の 7・8・9・10 項：
- **A10-1** W₂ 推定量のベンチマーク（exact vs sliced）と null 設計（定義3）
- **A10-2** orientation cluster 1R:m z の m 感度（§6）
- **A10-3** 判定規則の global 較正（primary-map core rule）の実装設計（定義4）
- **A10-4** exact version の確定（§9・強化項目）

---

## 0. 前提（凍結済み資産との接続）

| 資産 | 用途 |
|---|---|
| A5 凍結 B±-stack（ℓ2–4・3072 軸・array SHA `eb514148…`）・A5 null selection（1000 等方・帯域別 (T₁,T₂)） | ℓ2–4 評価器／等方 null の形状（本ノートの proxy） |
| A8a F16（ℓ≤16 特徴スタック）・A8b ROUTE_DECISION（l24: feature231/f32/ch 20000＝0.66 min/10⁶；S2: s2_feature/f32/ch 1024＝83 min/10⁶） | 走査コストの見積り（§2・§3 の予算） |
| A9 `D_of_R`（凍結実基底上の能動回転の実表現・準同型/直交/直接幾何 gate 済），Haar sampler（`Rotation.random(num, rng)`・KS/Holm 電池）・`psqrt` | orientation の生成と CRN |
| A11 x₀ 橋渡し（x₀_CT = −r_obs・判別述語・cov_cache 39 個） | モデル共分散 C_M(θ, x₀) の生成 |
| Step 0 official（T₁_obs=39.6718，T₂_obs=259.3375；PR3_Commander） | E_sel・Event B・phenotype flag |

記法：T=(T₁,T₂)=(S⁺@argmin, S⁻@argmin)（selection-adjusted）。E_sel = {T₁ ≤ T₁,obs, q₁₆ ≤ T₂ ≤ q₈₄}（分位は等方
selection-adjusted **校正**サンプルから；定義1）。

---

## 1. A10-1：W₂ トリガー（定義3）の実装確定

### 1.1 ベンチマーク（サンドボックス・1 core・3 GB；Colab の上界として扱う）
proxy：A5 null selection の帯域 l16（S2 目標帯域）の (T₁,T₂) 1000 点を whitening し，2D Gaussian KDE から再標本化。
exact 2D W₂ は POT `ot.emd2`（squared Euclidean cost → √），sliced は `ot.sliced_wasserstein_distance`（射影 500・seed 固定）。

| exact W₂ | n=1000 | 2000 | 4000 | 8000 | **n=20000（外挿）** |
|---|---|---|---|---|---|
| 時間 | 0.3 s | 1.1 s | 4.4 s | 18.6 s | **≈121 s**（指数 2.05） |
| cost 行列 | 8 MB | 32 MB | 128 MB | 512 MB | **3.2 GB**（POT 内部コピーを含めると 2–3 倍） |

sliced W₂（n=20000・500 射影）：**5.3 s**。同一標本（n=4000）で exact 0.106 vs sliced 0.031（sliced は 1 次元射影の平均で
あり数値は W₂ と同一尺度ではない；比較は各推定量自身の null 分位に対して行う）。

**null の 99 百分位（同一分布・2 独立標本・B=200）**

| 推定量 / n | iid | 1R:100z（cluster 分散比 f=0.1） | 1R:100z（f=0.3） |
|---|---|---|---|
| exact，n=2000（B=200） | q99 = 0.215（median 0.164） | **0.324** | **0.597** |
| **exact，n=5000**（B=100／50） | q99 = 0.143（median 0.112） | **0.213** | —（未計測） |
| sliced，n=20000（B=30・参照） | q99 = 0.032（median 0.022） | — | — |

**検出力（whitened 単位の平均シフト δ；iid null q99 を閾値・20 反復）**

| δ | 0.1 | 0.2 | 0.3 |
|---|---|---|---|
| exact n=5000 | 0.55 | 1.00 | 1.00 |

（時間：exact n=5000 は ≈4–5 s／ペア（KDE 生成込み）。cluster 構造下では null 幅が広がる分だけ検出力は下がるので，
本番の検出力は cluster null で再評価する。）

### 1.2 結論と確定規則
1. **exact 2D W₂ を n_sub=20 000 で用いる案は採用しない**。時間は許容（≈2 min／ペア・3 ペア＋null B=200 ⇒ 200×2 min ≈ 7 h）
   だが，**null 200 反復を含めた総時間と 3.2 GB×(2–3) のメモリ**が Colab 標準 runtime（13 GB）で余裕がない。
2. **確定：exact 2D W₂・n_sub = 5 000**（cost 200 MB・≈4–5 s／ペア；null B=200 で ≈15–20 min）。iid null で whitened 0.2σ の
   平均シフトを検出力 1.0，0.1σ を 0.55 で検出する（表）。sliced は補助診断として併記
   （射影 500・seed 固定）。n_sub を 20 000 から 5 000 に下げても検出対象（位置間の分布差）は cluster 構造で決まる
   （§1.1 の null 表：cluster 効果が支配的）ため，標本数より **cluster 数**が実効的な情報量を決める。
3. **null は clustering を必ず再現する**（v0.5 のとおり）。上表のとおり 1R:100z の cluster 効果で q99 が 1.5–2.8 倍動く。
   null は「同一等方分布・同一 (R, z) 階層構造・同一 n_sub・同一 whitening・同一推定量」で作り，**W₂ の値は cluster 単位で
   部分標本化する**（n_sub/m 個の cluster を無作為抽出し，その cluster の全 z を保持）。
4. **集約は max pairwise**（3 位置・3 ペア），閾値は null の 99 百分位。トリガー＝`W₂_max > q99` **または**
   `max_k P_k(E_sel) / min_k P_k(E_sel) > 2`（後者は各 P_k が精度 gate 通過後のみ；hit 0 なら trigger=True）。
5. whitening の μ_iso・Σ_iso は等方 **校正**サンプル（stream `calibration`）から。評価サンプルとは分離。
6. provenance：POT 版・`numItermax`・cost metric・n_sub・cluster 部分標本の seed・B_null・q99・各ペアの W₂・sliced 併記値。
   **hard gate**：`ot.emd2` の収束フラグ（`log=True` の `warning` 無し）・W₂ が有限・null 200 反復すべて有限。

---

## 2. A10-2：orientation cluster 1R:m z の m 感度（§6）

### 2.1 何を決めるか
CRN の単位は「1 つの Haar 回転 R を m 個の Gaussian 標本 z で共有」（option B）。m が大きいほど回転生成・D(R) 適用・
走査のコストは下がるが，cluster 内相関で **実効標本数（cluster 数）**が減る。v0.5 の規則：1 モデル点で m=10 と m=100 を比較し，
差が CI 内なら m=100，外なら m=10。

### 2.2 実装（A10 ノートブック・ℓ2–4 評価器で実施）
- モデル点：**E7・`E7_b1_A`（A11 target case・LAx=1.0, LAy=0.3, L1y=1.0, L2x=0.0, L2z=1.0）・x₀⁽¹⁾**。共分散は A11 cov_cache
  の該当エントリ（manifest で topology/params/x₀ を照合・array SHA gate）。
- 等方基準：同じ ℓ2–4 実基底の等方共分散 C_iso（Step 0/A5 の fiducial C_ℓ から diag；A9-3 の解析 2 次モーメント電池と同じ構成）。
- 生成：`z ~ N(0, I₂₁)`（stream `gaussian`），`x_M = D(R) C_M^{1/2} z`，`x_iso = D(R) C_iso^{1/2} z`（**同一 (R, z)**＝CRN）。
  C^{1/2} は principal symmetric square root（強化項目の hard gate：‖S−Sᵀ‖/‖S‖<1e-12・‖SSᵀ−C‖/‖C‖<1e-10）。
- 走査：3072 軸 B⁺-stack で argmin（first occurrence）→ T₁,T₂（float64・ℓ2–4）。
- 総標本 N = 10⁶ を固定し，**m=10（10⁵ cluster）と m=100（10⁴ cluster）**で同一 N。
- 出力：P_M(E_sel)・P_iso(E_sel)・Q_j = P_M/P_iso・**paired cluster bootstrap**（cluster index を再抽出・model/iso は paired・
  B=2000）の 95% CI・event-positive cluster 数・CI 安定性（bootstrap seed 5 回・CI 幅の CV）。
- 判定（事前固定）：|log Q_j(m=100) − log Q_j(m=10)| が **m=10 の CI 半幅以内** かつ m=100 が精度 gate（event-positive cluster
  ≥ 50・相対半幅 ≤ 20%）を通過 → **m=100 を採用**。どちらかが満たされなければ m=10。
- 併せて記録：z あたりの生成コスト（D(R) 生成は m で割られる）。A8b の走査コスト（0.66 min/10⁶）と合わせて Step 1 本番の
  総予算（点数 × 3 位置 × N）を rules に書く。

### 2.3 予算の見積り（A8b 実測から）
ℓ2–4 走査は 0.66 min/10⁶ なので，m 感度試験（2 条件 × model/iso × 10⁶）は走査だけなら **≈3 min**。支配的なのは D(R) の
生成（quadrature 構成・21×21）：m=10 では 10⁵ 個の R（A9 実測から 1 個 ≈ ms 級 ⇒ 数分），m=100 では 10⁴ 個。
いずれも Colab で 1 時間以内。S2（ℓ≤16）での m 感度は行わない（S2 は S4 完了まで HOLD；ℓ2–4 の結論を S2 にも適用し，
S2 採用時に再検証を登録する）。

---

## 3. A10-3：global false-support 較正（定義4）の実装設計

### 3.1 較正の対象と構造
- 対象：**PR3_Commander の primary-map core decision rule のみ**。
  support：Q_M の 95% 下側 CI ≥ 3 AND log D_M > 0 AND estimator audit PASS／strong：下側 CI ≥ 10 AND D_M 下側 CI > 1 AND
  matched/CT-native が CI 分類で同方向。robustness（他 3 マップ）は descriptive qualifier（較正対象外）。
- 擬似観測：等方 selection-adjusted **評価**サンプルから n_pseudo 個（smoke 200／official ≥ 2000；stream `pseudo`，
  校正サンプル・fitting サンプルと独立）。各 pseudo T_obs について，同一の E_sel 定義（分位は校正サンプルから固定；
  **T₁ 閾値だけが pseudo ごとに変わる**）で全 family の Q_M, D_M と CI を計算し，support/strong を判定。
- 報告：`FWFSR_support = P_iso(∃M: support_M)`，`FWFSR_strong = P_iso(∃M: strong_M)` と Wilson 95% 上側 CI。
  合格：support usable ⇔ 上側 CI ≤ 0.05；strong usable ⇔ 上側 CI ≤ 0.01。FAIL 時はラベル不使用・`descriptive / calibration-failed`。

### 3.2 計算量の削減（**再走査なし**）
pseudo ごとに全 family の走査をやり直すと 2000 × (点数) × 10⁶ となり不可能。しかし，E_sel の pseudo 依存部分は **T₁ の閾値
だけ**であり，各モデル点・等方の (T₁,T₂) 標本は固定なので：
- 各点の (T₁, T₂, cluster_id) を 1 回だけ生成・保存（本番走査の副産物）。
- pseudo T_obs ごとに `E_sel(pseudo) = {T₁ ≤ T₁,pseudo, q₁₆ ≤ T₂ ≤ q₈₄}` を **indicator の再評価**（ソート済み T₁ に対する
  searchsorted）で得る ⇒ P_j(E_sel) の 2000 通りは O(N log N) ではなく O(N) 級。
- Q_M の CI は paired cluster bootstrap（B=2000）を pseudo ごとに再計算すると 2000×2000×点数で重い ⇒ **cluster 単位の
  indicator 集計表**（cluster ごとの hit 数）を T₁ 閾値の grid（pseudo T₁ の 2000 値のソート）上で累積し，bootstrap は
  cluster 集計表の再抽出で行う（1 pseudo あたり数十 ms）。
- D_M（密度比）は KDE の評価点が変わるだけなので同じ KDE を再評価。

### 3.3 事前固定する事項
- n_pseudo（≥2000）・B（2000）・Wilson CI・pseudo の stream と seed 表・T₁ 閾値のみが動くこと（q₁₆/q₈₄ 固定）。
- pseudo は **評価サンプル**から取り，校正サンプル（分位・whitening）と fitting サンプル（KDE）から分離。
- 較正は **モデル結果を見る前**に完了・封印（provenance に pseudo 結果の SHA）。
- 「較正対象は core rule のみ」「robustness は descriptive」を rules 本文に明記。

---

## 4. A10-4：exact version（強化項目）
Colab 実環境で確定した版（A8a/A8b/A11 の official）：**Python 3.13.15・NumPy 2.1.3・SciPy 1.16.3・healpy 1.20.0・pandas 2.2.3・
CAMB 2.0.4・POT（A10 ノートブックで確定）**。rules v1.0 では `assert __version__ == EXPECTED` を hard gate とし，
numba・spherical・quaternionic・BLAS backend・platform・`pip freeze` は archive。
（注：A9 の sandbox 版は SciPy 1.17.1／NumPy 2.4.4 で，Colab とは異なる。official 系列は Colab 版で統一する。）

---

## 5. Phase A → rules v1.0 draft への転記（A10 分）
| rules 項目 | 確定値 |
|---|---|
| W₂ 推定量 | exact 2D W₂（POT emd2）・n_sub=5000・cluster 単位部分標本・whitening（校正サンプル）・max pairwise・null B=200・q99・sliced 併記 |
| 拡張トリガー | W₂_max > q99 OR event-ratio > 2（精度 gate 後・hit 0 は True） |
| CRN 単位 | 1R : m z，m は A10-2 の実測で 10/100 を確定（判定規則 §2.2） |
| 精度 gate | event-positive cluster ≥ 50 AND cluster-bootstrap 相対半幅 ≤ 20% AND CI 幅 CV < 0.2（5 seed） |
| global 較正 | primary-map core rule・n_pseudo ≥ 2000・indicator 再評価法・Wilson 上側 CI ≤ 0.05/0.01・FAIL 時の挙動 |
| exact version | §4 |

## 6. 次の作業
1. **A10 ノートブック**（サンドボックス→Colab）：A10-2 の m 感度（E7_b1_A・x₀⁽¹⁾・ℓ2–4・N=10⁶・m=10/100）と A10-3 の
   indicator 再評価法の実装検証（小規模 pseudo 200 で FWFSR の算出経路を通す）。POT 版の確定。
2. 結果を本ノート v1.1 に追記 → ChatGPT 共有 → `Step1_rules_v1.0_draft` 起草（Phase C）。
