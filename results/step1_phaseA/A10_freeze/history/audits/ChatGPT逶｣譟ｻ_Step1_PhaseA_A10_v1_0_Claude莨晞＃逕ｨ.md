# ChatGPT監査：Step 1 Phase A-10 v1.0
## W₂推定量・orientation-cluster m感度・global較正経路
**Claude伝達用 / 2026-09-11**

## 0. 総合判定

A10 v1.0は、Pythonコードとしてはかなりよくまとまっており、主要な数値カーネルにも明白な代数ミスは見つからない。全code cellは構文解析・compileを通過し、Claude報告のsmoke／full-scale sandbox実行も、コード構造と計算量から見て十分あり得る。

しかし、**現在のStep 1凍結仕様に対して二つの重大な回帰がある**。

1. A5でfreeze済みのprimary Event B
   \[
   E_B=\{T_1\le T_{1,\mathrm{obs}}\land T_2\le T_{2,\mathrm{obs}}\}
   \]
   ではなく、旧案
   \[
   \{T_1\le T_{1,\mathrm{obs}},\ q_{16}\le T_2\le q_{84}\}
   \]
   を使っている。
2. A8bでfreezeされたproduction scan
   `l24_feature231 / float32 selection / float64 evaluation / chunk=20000 / threads=2`
   ではなく、float64 selection・chunk=10000・thread未固定を使っている。

従って、現報告の：

```text
Q ≈ 1.08–1.11
m=100採用
event-positive cluster数
FWFSR 0/200
```

は、**現在のrules候補へ転記できない**。Event Bとproduction scanへ直して再計算する必要がある。

> **構文・基本実行可能性：PASS**  
> **scan／CRN／cluster bootstrapの数理：PASS**  
> **A9 D(R)との静的整合：PASS方向**  
> **最新Event Bとの整合：FAIL**  
> **A8b production pathとの整合：FAIL**  
> **m感度のformal decision：未完**  
> **global calibration：pathway prototypeのみ**  
> **W₂ estimator kernel：PASS、position trigger設計：未完**  
> **A10 v1.0 official実行：HOLD**  
> **v1.1へ修正後：smoke GO見込み**

---

## 1. 静的検査

```text
notebook cells                 4
code cells                     2
全code cell AST parse          PASS
全code cell py_compile         PASS
gate assignments               19
```

SHA256：

```text
notebook file
a571132b5d899d76af40752db2547d8a80bcc0a769680e35ad23ebc480cec1cc

canonical source-only
593fc9c9cc095f69950082db93ca8237e210eeb97aad703422c346f30a7b9801
```

`Rotation.random(num=..., rng=Generator)`はSciPy 1.16系で正しいAPIである。`ot.emd2`を二乗ユークリッドcostへ適用し平方根を取るW₂関数も、均一重みempirical 2-Wasserstein distanceとして正しい。

ただしfull N=10^6、exact OT n=5000×B=200は本監査環境では再実行していない。Claude報告のfull-scale値は独立再計算ではなく、添付報告に基づく。

---

## 2. 正しく実装されている中心部分

### 2.1 packed quadratic-form scan

上三角feature：

```python
f = X[:, iu0] * X[:, iu1]
```

と、Bの非対角成分を2倍したfeature matrixによって、

\[
f(x)\cdot b_a=x^\mathsf{T}B_a x
\]

を正しく再現する。

ランダム対称B±とランダムXを用いた独立小規模試験では：

```text
全軸S+ feature vs direct      最大約1.1e-14
selected-axis S-             最大約2.7e-15
argmin                       完全一致
```

であった。

### 2.2 CRN生成

同一orientation cluster内でm個の独立zを使い、同一のRとzをmodel／isotropicへ流す：

```text
x_M = D(R) S_M z
x_I = D(R) S_I z
```

という実装は、registered option Bとpaired CRNに整合する。

### 2.3 paired cluster bootstrap

orientation cluster IDを再抽出し、cluster内m個をまとめて保持し、model／isoの対応clusterへ同じbootstrap weightを使う実装は正しい。

### 2.4 現行1次元hit table

旧イベントについて、T1をsortして固定T2-band内のcluster hitを累積する`hit_table`は、brute-force indicatorとの独立小規模比較で完全一致した。

問題はアルゴリズムではなく、**対象イベントが旧定義**であることである。

### 2.5 D(R)

A10の：

```python
Ymat = (M21.conj() @ Yc).real.T
D(R) = YQW @ Ymat(DIRS @ R)
```

はA9 freezeのquadrature D(R)構成と静的に同じである。

ただしA10自身はA9 freeze provenance／script SHAへbindingせず、A9のexplicit-basis・complex-path・known-z-rotation電池も再利用していない。後述のsource-chain補強が必要。

---

# 3. 【BLOCKER 1】primary eventがA5 freeze以前の旧案へ戻っている

現コード：

```python
def esel(d):
    return (
        (d[:, 0] <= T1o)
        & (d[:, 1] >= q16)
        & (d[:, 1] <= q84)
    )
```

は、selection-adjusted isotropic T2の中央帯を用いる旧案である。

A5で正式にfreezeされたprimary eventは：

```python
def event_B(d, t1_threshold, t2_threshold):
    return (
        (d[:, 0] <= t1_threshold)
        & (d[:, 1] <= t2_threshold)
    )
```

である。

意味は：

```text
extremely low S+
+
no compensating increase in S-
```

である。

### 影響範囲

以下は全て旧イベントに依存するため、現在のrulesへ持ち越せない。

```text
m=10 / m=100のQ
paired bootstrap CI
event-positive cluster数
m=100採用判定
pseudo calibration hit table
FWFSR 0/200
予備的Q≈1.08–1.11
```

### 必須修正

実観測について：

```python
def event_B_obs(d):
    return (
        (d[:, 0] <= T1o)
        & (d[:, 1] <= T2o)
    )
```

pseudo observation pについて：

```python
E_p = (
    (d[:, 0] <= pseudo_T1[p])
    & (d[:, 1] <= pseudo_T2[p])
)
```

とする。

`q16/q84`はA5 null cross-checkやsecondary diagnosticとして残してよいが、primary eventへ使わない。

---

# 4. 【BLOCKER 2】A8bでfreezeしたproduction scanを使っていない

A8b officialで確定したl2–4 engineering specification：

```text
route             l24_feature231
selection dtype   float32
evaluation        float64
sample chunk      20,000
BLAS threads      2
axis              unoriented plane [n]={n,-n}
```

A10 v1.0：

```text
feature route     使用
selection dtype   float64
evaluation        float64
chunk             10,000
threads           未固定
```

である。

float64はaudited alternateとして有効だが、m感度とglobal calibrationでproduction設定を決めるなら、primary pathと同じ設定を使う必要がある。

### 修正

```python
# selection
x_sel = x64.astype(np.float32)
axis, selection_score = scan_argmin_float32(x_sel)

# evaluation
T1 = x4_64 @ Bp4_64[axis] @ x4_64
T2 = x4_64 @ Bm4_64[axis] @ x4_64
```

- `CHUNK=20000`
- BLAS threads=2
- exact-antipode tieはA8bのselected-output equivalence規則
- float64 selectionをsensitivityとして併記

とする。

A10が意図的にfloat64-onlyのmethodological diagnosticなら、その旨を明記し、mのproduction採用根拠にはしない。

---

# 5. 【BLOCKER 3】m感度のdecision ruleが4 runを十分に使わない

A10は：

```text
m=10  × 2 independent reps
m=100 × 2 independent reps
```

を生成する。

しかし採用判定は実質：

```text
m10 rep1 vs m100 rep1の差
+
m100 rep1/rep2のprecision PASS
```

だけである。

m10 rep2とm100 rep2のcross-m差は採用判定へ入らず、m100が不適格ならm10のprecisionに関係なくm10を採用する。

```python
adopted_m = 100 if (...) else 10
```

は、両方不適格でも10を返す。

### 報告値について

丸め済み報告値からは：

```text
rep1 |ΔlogQ| ≈ 0.0220
rep2 |ΔlogQ| ≈ 0.0218
2-rep平均 |ΔlogQ| ≈ 0.0219
```

であり、m=100という結論自体は頑健そうに見える。ただし旧イベントに対する結果であり、Event Bで取り直す必要がある。

### 推奨decision

簡単な案：

```text
1. m10 rep1/2、m100 rep1/2が全てprecision gateを通る
2. rep1 pairとrep2 pairの双方でm差CIが0を含む
3. 2-rep pooled difference CIも0を含む
→ m=100

m100不適格、m10両rep適格
→ m=10

それ以外
→ unresolved / inconclusive
```

または2 repsを統合したlogQ差のbootstrap分布を直接構築する。

### cluster ESS

旧計画にはcluster ESS≥200があったが、その定義は未確定で、「ESSを使わずpositive-cluster数＋cluster-bootstrap CI精度」を採る案も提示されていた。

A10は後者を暗黙採用している。rulesへ：

```text
cluster ESS requirementはsuperseded
precision gateはpositive cluster数＋CI半幅＋5-seed width CV
```

と明示するか、ESSを実装する必要がある。

### 必須gate

```text
G_m_run_inventory
G_m_all_Q_finite
G_m_precision_each_run
G_m_decision_resolved
G_m_two_rep_consistency
```

を追加する。

現在の19 gateにはm感度の成否が一つも入っていないため、m decisionが壊れていても`A10_VALID`になり得る。

### 保存

現在のNPZはrep1のhM/hIしか保存しない。4 run全ての：

```text
hM
hI
cluster ids／m
bootstrap seed recipe
Q／CI
```

を保存する。

---

# 6. 【BLOCKER 4】A10-3はglobal calibrationではなくone-point pathway prototype

現在は：

```text
topology point   E7_b1_A 1点
system           matched 1系統
pseudo           200
rule             Q lower CI >=3 AND point KDE D>1
```

である。

これは計算経路のprototypeとしては有用だが、familywise global calibrationではない。

正式global calibrationは：

```text
全registered family
全required points／systems
family-level prior integration
current Event B
full primary-map core decision rule
official n_pseudo >= 2000またはprecision stopping
```

を必要とする。

### pseudo eventの誤り

Event Bではpseudoごとに：

```text
pseudo T1obs
pseudo T2obs
```

の両方を使う。現コードはpseudo T1だけを使い、T2は固定q16–q84 bandであるため、現在の較正規則とは一致しない。

### 命名

現在の：

```text
FWFSR_support
```

は、

```text
one_point_one_system_false_support_frequency
```

または：

```text
calibration_pathway_diagnostic
```

へ改名する。

### positive control

報告された0/200は、Q≈1.1の点でsupport threshold 3へ届かないため当然に近い。

計算経路を検証するには：

```text
null negative control     → support 0に近い
synthetic boosted control → supportが発動
brute-force event table   → optimized tableと一致
```

をhard gateにする。

### density ratio

現コードはKDE Dのpoint estimateだけを使う。最終rulesのmirror-specific mechanism claimは`Q_noncomp lower CI >1`を要求する。A10-3をfull ruleへ近づけるなら、Event B decompositionとCIを実装する。

---

# 7. W₂：カーネルは正しいが、実際のposition triggerを閉じていない

## 7.1 正しい部分

- isotropic calibration sampleからmean／covarianceを作りwhitening
- orientation cluster単位でsubsample
- equal-size empirical distributions
- squared Euclidean cost
- unregularized OT costの平方根

は妥当。

## 7.2 現在測っているもの

```text
W2(model, isotropic)
```

の1組である。

Step 1で必要な位置依存triggerは、3 observer positions間の3 pairについて、例えば：

\[
W_{2,\max}
=
\max_{k<k'}W_2(P_k,P_{k'})
\]

を使う設計である。

従って現在の`model_vs_iso_exceeds_q99`はposition triggerではなく、**W₂ solver／scale diagnostic**である。

## 7.3 nullもmax-pairwiseに合わせる

実triggerがmax pairwiseなら、null replicateごとに同一分布から3 sampleを生成し：

```text
W12
W13
W23
max(W12,W13,W23)
```

のnull distributionを作る必要がある。

## 7.4 B_NULL=200の99％点

200 replicateの99％点は上位ほぼ2標本で決まるため、thresholdとして不安定である。

最低限：

```text
quantile methodを固定（例 method="higher"）
Monte Carlo p = (1 + #null >= observed)/(B+1)
B／n_sub／subsample seed sensitivity
```

を保存する。

final trigger thresholdにはB増加またはprecision stoppingを推奨する。

## 7.5 null pool

第2 isotropic poolは`4*n_sub`だけで、B=200の各null replicateが同じ小さなcluster poolを何度も再利用する。

pathway testとしては可だが、final finite-sample nullでは：

```text
独立に十分大きい2～3 pools
または
replicateごとのfresh／disjoint cluster blocks
```

を使う方がよい。

## 7.6 n_sub

`n_sub=5000`を1点でしか試していない。W₂推定量をfreezeする前に：

```text
n_sub 2000 / 5000
複数subsample seed
```

程度の安定性確認を行う。

## 7.7 報告値

```text
W2(model,iso)=0.137
null q99=0.149
```

はexploratory diagnosticに限定する。actual 3-position trigger、B安定性、n_sub安定性を通すまでは「triggerなし」と確定しない。

---

# 8. provenance／source identity

A10はPhase A調査ノートであるためA11ほど重い証拠鎖は必須でないが、mとW₂をrulesへ転記するなら現状は弱い。

## 現在の不足

```text
repo canonical origin gateなし
clean tree gateなし
hard reset／cleanなし
t1_engine SHAなし
t2b2_run SHA／live pathなし
A9 freeze provenance bindingなし
live notebook source SHAなし
SciPy／NumPy／healpy versionはwarningのみ
POT version未pin
BLAS／thread未固定
A5 null file SHAなし
Mx basis vs M21 gateなし
CVECのl-block constancy gateなし
output SHAなし
atomic writeなし
final assertなし
smoke→official区別／chainなし
```

特に、Pythonは既import moduleを`sys.modules`から再利用するため、fresh runtime指示だけでなくmodule purge＋live file SHAが望ましい。

## A9の再利用

A9ではHaar、frozen real-basis bridge、D(R)、direct complex geometryまで30 gateでfreeze済みである。

A10では：

```text
A9 freeze manifest SHA
A9 provenance OFFICIAL／all gates
quadrature nodes／weights SHA
M21／LM／real-basis SHA
D(R) reference outputs
```

へbindingし、A10独自のD gateはregression testとする。

## environment

期待versionとの差はwarningではなく、少なくともofficialではhard gateにする。POTもexact versionをpinする。

## outputs

```text
ENGINE_VALID
M_SENSITIVITY_RESOLVED
CALIBRATION_PATH_VALID
W2_ESTIMATOR_VALID
```

を分け、最終：

```text
A10_VALID = all required component statuses
```

とする。

provenanceをatomic writeした後にfinal assertを行う。

---

# 9. A5 cross-checkの補強

現在の`G_iso_engine_matches_A5_null`はT1／T2 medianだけをbootstrap CIと比較する。

A10の中心はtail eventであるため、少なくとも：

```text
P(T1 <= T1obs)
P(Event B)
T1/T2 selected-output distribution diagnostic
```

も比較する。

A5 N=1000はdesign-discovery sampleなので厳密一致を求めず、binomial／bootstrap uncertainty内をgateにする。

---

# 10. 実装報告の表現修正

## 10.1 m=100

現在は：

> m=100採用

ではなく：

> 旧central-band eventとfloat64 selectionに基づくexploratory runではm=100が選ばれた。Event B＋A8b production pathで再評価待ち。

とする。

## 10.2 bootstrap

> bootstrapがMC誤差を正しく表す

は2 independent repsだけでは強すぎる。

> replicate差がbootstrap CI scaleと整合した

が安全。

## 10.3 first official

ruleを一度full result後に変更しているため、そのrunはdesign-discovery runとして保存する。

```text
discovery run
→ criterion amendment
→ fresh prospective confirmation
```

へ分ける。

## 10.4 Q≈1.08–1.11

旧event結果であるため、current Event Bに対する科学的観察としては撤回／supersededと記載する。

---

# 11. 推奨v1.1の最短構成

1. **Event Bへ置換**
2. **A8b frozen l24 production pathを使用**
3. m decisionを2-rep・fail-closed化
4. 4 run全cluster countsを保存
5. calibration pathwayをEvent Bの2D pseudo thresholdsへ修正
6. one-point pathwayとglobal calibrationを名称・statusで分離
7. W₂を3-position max-pairwise mock／nullへ拡張
8. W₂ B／n_sub sensitivityまたはMC p-valueを追加
9. A9 freeze、A8b rules、A5 freezeへSHA binding
10. component status、atomic outputs、final assert

長時間計算を一つの巨大cellへ置かず：

```text
A10a engine/preflight
A10b m sensitivity
A10c calibration pathway
A10d W2 estimator
A10e provenance
```

に分け、各段階をbinding付きcheckpointへ保存する。

---

## 12. 最終判定

| 項目 | 判定 |
|---|---|
| Python syntax | PASS |
| SciPy Rotation API | PASS |
| packed scan algebra | PASS |
| CRN orientation generator | PASS |
| paired cluster bootstrap | PASS |
| current 1D hit-table algebra | PASS |
| quadrature D(R) static relation to A9 | PASS方向 |
| latest Event B | **FAIL** |
| A8b production scan | **FAIL** |
| m=100 formal adoption | **未確定** |
| one-point calibration path | prototypeとして可 |
| true global calibration | 未実装 |
| exact empirical W₂ solver | PASS |
| 3-position W₂ trigger | 未実装 |
| W₂ q99 freeze | B=200では不足 |
| source/provenance | 要hardening |
| A10 v1.0 smoke | 旧仕様のruntime testに留まる |
| A10 v1.0 official | **HOLD** |
| v1.1修正後 | smoke GO見込み |

### 一言でまとめると

> **A10 v1.0は「走らないコード」ではない。むしろ数値カーネルはよくできている。**  
> ただし、新しいチャットまたは古い設計文脈から作られた可能性が高く、A5 Event BとA8b production specificationが巻き戻っている。  
> この二点を直さず得たm=100・Q・calibration結果をStep 1 rulesへ採用してはならない。
