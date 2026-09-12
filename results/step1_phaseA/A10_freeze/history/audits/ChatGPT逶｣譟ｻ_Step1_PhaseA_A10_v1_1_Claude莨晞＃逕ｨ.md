# ChatGPT監査：Step 1 Phase A-10 v1.1
**Claude伝達用 / 2026-09-11**

## 0. 総合判定

A10 v1.1は、v1.0で見つかった二大回帰を概念上は正しく修正している。

- primary eventをA5凍結のEvent Bへ戻した
- pseudo-data較正を二次元閾値 `(T1_pseudo, T2_pseudo)` にした
- A8bのproduction recommendationを読み込む
- m=10×2・m=100×2、fail-closed decision、component statusを導入
- one-point calibration pathwayとfamilywise global calibrationを区別
- W₂を3 observer positionsのmax-pairwiseへ拡張
- A5/A8/A9/A11のfreeze artifactへ多数のSHA bindingを追加
- v1.0の結果をsupersededとして透明に保存する

ただし、現行sourceにはofficial結果を変え得る実質的な問題が残る。

> **Event B定義：PASS**  
> **2D pseudo threshold：PASS**  
> **D(R)・quadratic scanの数学：PASS**  
> **A8b production pathのexact reproduction：FAIL**  
> **m=10 fallback logic：FAIL**  
> **m practical equivalence criterion：未成立**  
> **calibration lower-CI：FAIL（zero numeratorを捨てる）**  
> **positive-control full support path：未検査**  
> **W₂ solver/pathway：PASS**  
> **W₂ nullを用いたMC pのcalibration：不一致**  
> **W₂ stability gate：不足**  
> **source／basis／atomic archive：一部未完**  
> **A10 v1.1 smoke／official：HOLD**  
> **v1.2へ修正後：smoke GO見込み**

数値カーネル全体の作り直しは不要である。主な修正箇所はscanのfloat32丸め順、m decision gate、calibration bootstrap、W₂ inferential semantics、provenanceである。

---

## 1. 静的検査

```text
notebook cells                 7
code cells                     5
全code cell AST parse          PASS
全code cell compile            PASS

notebook file SHA256
16f8d84c94f1cf60c1c7118405154af946a8c55c0832bd74007af5c3ea2eeff0

canonical source-only SHA256
e410c744721dbcd6442597c2156f7a82b91733478f20434c6ec529e02c09ffb1
```

実装報告のSHAと一致する。

gate assignmentは39件である。

```text
smoke required    37
official required 39
```

従って実装報告の「37 gate」はsmokeについては正しいが、officialは39/39と表記する必要がある。

---

## 2. 正しく改善された部分

### 2.1 Event B

```python
event_B = (
    (T1 <= T1_obs)
    & (T2 <= T2_obs)
)
```

をprimary eventとして使う。旧q16–q84 central bandはsecondary diagnosticだけになった。

### 2.2 pseudo threshold

各pseudo observationについて、

```python
(T1 <= T1_pseudo[p])
&
(T2 <= T2_pseudo[p])
```

を用いる`hit_table_2d()`へ修正されている。小規模な独立試験でbrute-force indicator tableと完全一致した。

### 2.3 quadratic form

packed upper-triangle featureとoff-diagonal 2倍のB featureは、数学的に`x.T @ B @ x`を正しく再現する。selected-axis T2もdirect quadratic formと一致する。

### 2.4 orientation cluster

1 rotation : m Gaussian realizations、model/isotropic間のcommon random numbers、orientation-cluster単位のpaired bootstrapという骨格は妥当である。

### 2.5 status separation

```text
ENGINE_VALID
M_SENSITIVITY_RESOLVED
CALIBRATION_PATH_VALID
W2_ESTIMATOR_VALID
```

を分け、最後に`A10_VALID`へ統合する方向はよい。

---

# 3. 【BLOCKER 1】A8b production pathをexactには再現していない

A8bでfreezeされたfloat32 selectionは、

```text
x64
→ x32 = x64.astype(float32)
→ feature = x32_i * x32_j  （float32 multiplication）
→ float32 GEMM
```

である。

A10 v1.1は、

```python
f64 = x64_i * x64_j       # float64 multiplication
score = f64.astype(float32) @ F32
```

である。

一般に、

```python
(x64_i * x64_j).astype(float32)
```

と、

```python
x64_i.astype(float32) * x64_j.astype(float32)
```

は同じではない。

### 独立小規模試験

10,000×21の標準正規sampleでは、2,310,000 packed entries中：

```text
不一致             838,132
不一致率           36.28%
最大絶対差         1.907e-6
```

であった。

さらに二つのpositive-semidefinite axis matricesを用いる合成例で、二つの丸め順がraw argminを入れ替え得ることも確認した。

従って現在の`G_a8b_production_spec_bound`は、provenance中のroute名・dtype・chunkを確認するだけで、実際のkernel identityを保証しない。

### 修正

```python
x32 = Xc.astype(np.float32)
f32 = x32[:, iu0] * x32[:, iu1]
Ssel = f32 @ FBp32
axis = Ssel.argmin(axis=1)
```

とする。

評価はA8bと同じfloat64 quadratic formへ揃える。

```python
T1 = np.einsum(
    "ni,nij,nj->n",
    Xc,
    Bp[axis],
    Xc,
    optimize=True,
)

T2 = np.einsum(
    "ni,nij,nj->n",
    Xc,
    Bm[axis],
    Xc,
    optimize=True,
)
```

packed float64 evaluationを残す場合も、A8b evaluationとのregression gateを追加する。

```text
G_a8b_kernel_exact_regression
```

をrequiredにする。

---

# 4. 【BLOCKER 2】m=10 fallbackがgate構成上は成立しない

decision codeは、

```text
m100 precision FAIL
m10  precision PASS
→ adopted_m = 10
```

を許す。

しかしofficialのrequired gateには、

```python
G_m_precision_each_run = all(
    m10 rep1/rep2,
    m100 rep1/rep2,
)
```

が入る。

従って：

```text
m100 FAIL
m10 PASS
adopted_m = 10
G_m_decision_resolved = True
G_m_precision_each_run = False
M_SENSITIVITY_RESOLVED = False
```

となる。

つまり、文書上のfallback branchは実際には`A10_VALID`になれない。

### 修正

全run precisionはdiagnosticとして残し、policy gateを別に作る。

```python
G_m_precision_policy = bool(
    (
        adopted == 100
        and m10_ok
        and m100_ok
    )
    or
    (
        adopted == 10
        and m10_ok
        and not m100_ok
    )
)
```

official requiredは、

```text
G_m_precision_policy
G_m_decision_resolved
```

とする。

---

# 5. 【STATISTICAL BLOCKER】CIが0を含むことはequivalenceの証明ではない

現在のm=100採用規則は、

```text
m100 − m10 のlogQ difference CIが0を含む
```

ことを要求する。

これは、

> 差を検出できなかった

ことを意味するが、

> m=100とm=10が実用上十分近い

ことを意味しない。

幅の広いCIほど0を含みやすく、precision gateが20%相対半幅まで許すため、実用上無視できない差が残る場合でもm=100を採用し得る。

### 推奨

official前にpractical equivalence margin `delta_m`を固定する。

例えばQの10%差を許容する場合：

```python
DELTA_M = np.log(1.10)
```

とし、rep1、rep2、pooledのdifference CIすべてについて、

```python
ci_low >= -DELTA_M
and
ci_high <= DELTA_M
```

を要求する。

10%という値は例であり、scientific／engineering上許容する差から事前に決める。

現行規則を維持するなら、結論は「m=100はcurrent precisionでstatistically distinguishableではなかった」と表現し、「m-insensitive」「equivalent」とは表現しない。

この点は前回ChatGPT監査も一段不足していた。

---

# 6. 【BLOCKER 3】calibration lower CIがzero-numerator bootstrapを捨てる

現行code：

```python
Qb = np.where(
    (SI > 0) & (SM > 0),
    SM / SI,
    np.nan,
)
```

は、bootstrap replicateでmodel numerator `SM=0`となった場合、本来のratio `Q=0`をNaNにしてquantileから除外する。

希少事象のlower confidence boundでは、zero numeratorは重要なlower-tail evidenceである。これを捨てるとlower CIを上方へ偏らせ、`lo >= 3`の偽supportを生み得る。

### 合成試験

100 clusters中、model hitが1 clusterだけ、isotropic hitが全clusterにある例：

```text
bootstrapでSM=0       36.64%
正しい2.5% quantile   0.00
現行nan除外quantile   0.01
```

### 修正

```python
Qb = np.full_like(SM, np.nan, dtype=float)

den_ok = SI > 0
Qb[den_ok] = SM[den_ok] / SI[den_ok]   # SM=0を0として保持

Qb[(SI == 0) & (SM > 0)] = np.inf
# SM=SI=0だけundefined
```

pseudoごとに、

```text
valid bootstrap fraction
denominator-zero fraction
both-zero fraction
```

を保存し、valid fractionのhard gateを設ける。

---

# 7. calibration positive controlはfull support pathを検査していない

正式supportは、

```text
Q lower CI >= 3
AND
D > 1
```

である。

しかしpositive-control gateは、

```python
loBo >= 3
and
QBo >= 10
```

だけで、density ratio `D` branchを検査しない。

density-ratioコードの分子・分母が逆でも、positive gateはPASSし得る。

### 修正

observed thresholdsで、

```python
D_bo = (
    kB([[T1_obs], [T2_obs]])
    /
    kI([[T1_obs], [T2_obs]])
)
```

を計算し、

```text
Q lower CI >= 3
Q >= 10
D_bo > 1
```

を要求する。

さらにmain pathwayについて：

```text
Qp / lower CI / Dpのfinite・valid inventory
n_pseudo exact
support array length exact
```

をhard gateにする。現在はinvalid valuesがFalse扱いとなり、false-support frequencyを人工的に小さく見せ得る。

negative controlは独立isotropic sampleなので、paired weightsをそのまま共有するより、numerator／denominatorを独立にbootstrapする方が明瞭である。

---

# 8. officialでmがunresolvedでもA10c/A10dがm=100で続行する

現行code：

```python
m_use = (
    adopted_m
    if adopted_m is not None
    else 100
)
```

である。

officialでm decisionがunresolvedでも、その後のcalibrationと重いW₂をm=100で実行し、最後にだけFAILEDになる。

### 修正

```python
if A10_MODE == "official":
    assert STATUS["M_SENSITIVITY_RESOLVED"]
    assert M_DECISION["adopted_m"] is not None
    m_use = M_DECISION["adopted_m"]
else:
    m_use = M_DECISION["adopted_m"] or 100
```

fail-closedを計算資源の面でも実現する。

---

# 9. W₂ pathway：solverは正しいが、nullとMC pの意味が揃っていない

observed W₂は、3 observer positionsに対して**同じlatent `(R,z)` cluster subset**を用いるCRN estimatorである。

nullは、isotropic poolから**三つのdisjoint cluster blocks**を取るindependent-sample estimatorである。

従ってobserved statisticとnull statisticは、同じsampling mechanismではない。

等分布の場合：

```text
CRNで同じdrawを両側に使うW₂      0に近い／同一なら0
独立sample間のempirical W₂        正のfinite-sample noise
```

となる。

このnullはconservative scale referenceとしては使えるが、

```python
(1 + #null >= observed) / (B + 1)
```

をexactなMonte Carlo p-valueとは呼べない。

### 二つの選択肢

**推奨primary inferential path**

```text
observer position 1/2/3も独立(R,z) streams
nullも独立3 samples
→ sampling mechanismを一致
→ MC pをcalibrated referenceとして扱える
```

**secondary diagnostic**

```text
CRN 3-position W₂
→ variance-reduced point diagnostic
→ independent nullに対する値はconservative reference
→ exact MC pとは呼ばない
```

両方保存するのが最も明瞭である。

またnull replicateは有限poolを再利用するため互いに独立ではない。これもexact MC pという表現を弱める理由になる。

---

# 10. W₂ “sensitivity”は記録されるだけでgateされない

v1.1は、

```text
n_sub = 2000 / 5000
3 subsample seeds
B_null = 200
```

を記録する。

しかし`W2_ESTIMATOR_VALID`が要求するのは、

```text
solver warningなし
null finite
n_sub key inventory
```

だけである。

次がどれほど不安定でもPASSする。

```text
3 seed間のW2_max
n_sub 2000 vs 5000
q99
above/below q99 decision
MC exceedance fraction
```

### 必須補強

少なくとも：

```text
G_w2_observed_finite
G_w2_pair_seed_inventory
G_w2_null_length_exact
G_w2_all_three_pairs
G_w2_position_sqrt_all_valid
```

を追加する。

A10の目的がestimator選択なら、official前にstability criterionも固定する。

例：

```text
3 seedのdecisionが一致
n_sub 2000/5000でdecisionが一致
W2_maxのrelative spreadが登録値以下
```

thresholdは結果を見る前に決める。

B=200の99% quantileは上位2値付近だけで決まるため、final threshold freezeには粗い。Phase A pathwayでは許容できるが、`W2_ESTIMATOR_VALID`ではなく`W2_PATHWAY_VALID`と呼ぶ方が正確である。

---

# 11. P2/P3 covarianceのmatched-power／sqrt gateがない

`G_matched_power`と`G_sqrt_hard`は、m sensitivityで使うP1とisotropicだけを検査する。

W₂で用いるP2／P3については、

```python
psqrt(matched(C_CT[k])[0])[0]
```

としてdiagnosticを捨てる。

### 修正

3位置すべてについて：

```text
matched l-block power
raw minimum eigenvalue
clip count
sqrt symmetry
reconstruction residual
```

を保存し、hard gateにする。

`G_cov_positions_distinct`も現在は「最大pair差 > 1e-6」である。3位置triggerなら、

```text
全3 pairのcovariance difference > threshold
```

またはA11のobserver-equivalence predicateで非等価であることを要求する。

---

# 12. 実装報告が主張するbindingの一部がコードにない

実装報告は、

```text
Mx basis vs M21
quadrature nodes/weights/M21 SHA binding
```

を挙げる。

しかし`load_C()`で得た`Mx`は破棄され、比較gateがない。

またA10側のquadrature hashは`DIAG`へ記録するだけで、A9 provenance中のexpected hashと比較しない。

### 修正

```python
G_cov_basis_matches_M21 = ...
```

を追加する。

A9 provenanceの：

```text
M21 SHA
LM SHA
real-basis SHA
quadrature node SHA
quadrature weight SHA
```

を読み、A10 current arraysと完全一致させる。

---

# 13. notebook identityとthread数は記録のみ

- `NB_HEAD`は取得するがlive notebook sourceと比較しない。
- `THREADS_LIVE`は記録するが、全対象BLAS poolが2 threadsかをgateしない。

rules draftへ数値を転記するrunなら、officialで：

```text
G_notebook_live_source
G_threads_live_registered
```

をrequiredにする。

source-only SHAは今回：

```text
e410c744721dbcd6442597c2156f7a82b91733478f20434c6ec529e02c09ffb1
```

である。修正後は新SHAをcommitし、その値へbindingする。

---

# 14. NPZ checkpointはatomicではない

JSONはtmp→fsync→replaceでatomicである。

一方、次のNPZは直接保存する。

```text
a10a_calibration.npz
a10b_cluster_hits.npz
a10c_pathway.npz
a10d_w2.npz
```

実装報告の「各段checkpoint atomic」は、現codeには当てはまらない。

### 修正

```python
def atomic_npz(path, **arrays):
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        np.savez_compressed(fh, **arrays)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
```

を使う。

W₂は最長componentなので、n_sub／null replicate block単位のresumeもあると安全である。

---

# 15. 推奨v1.2の最短修正順

1. A8b exact float32 product orderへ修正
2. float64 evaluationをA8b kernelへ揃える
3. m fallback precision-policy gateを修正
4. practical equivalence marginを事前登録
5. official unresolved mをA10c前にfail-fast
6. calibration bootstrapでzero numeratorを0として保持
7. denominator-zero／valid fraction gate
8. positive controlでD branchも検査
9. main calibration finite／inventory gate
10. 3 position全てのmatched-power／sqrt gate
11. W₂ primaryのsampling mechanismをnullと一致、またはCRN pathをconservative diagnosticへ改名
12. W₂ observed／pair／seed／B／stability gate
13. Mx／A9 quadrature hash binding
14. live notebook／thread hard gate
15. atomic NPZとofficial gate数表記修正

---

## 16. 最終判断

A10 v1.1は、v1.0より大幅に改善されている。Event B、2D pseudo threshold、one-point pathwayの限定、3-position max-pairwise W₂、component statusという方向は承認できる。

しかし、現在のままでは：

- freeze済みA8b kernelと違うfloat32丸め順でmを選ぶ
- m=10 fallbackが論理上通らない
- zero-numerator bootstrapを捨ててsupport lower CIを上方偏向させる
- W₂のobserved/null sampling mechanismが異なるのにMC pと呼ぶ
- W₂ stabilityを判定せず`W2_ESTIMATOR_VALID`になる
- 実装報告にあるbasis／quadrature bindingが一部存在しない

ため、official resultsをrules v1.0 draftへ転記できない。

> **A10 v1.1 CORE DESIGN：大幅改善・概ねPASS**  
> **現行sourceのSMOKE／OFFICIAL：HOLD**  
> **A10 v1.2へ修正後：SMOKE GO見込み**  
> **根本的な研究設計やD(R)／quadratic engineの作り直し：不要**

full frozen assetsを用いたColab smoke／officialは本監査環境では実行していない。監査範囲は全notebook source、compile、gate inventory、A8b exact route比較、small-scale quadratic／hit-table／bootstrap counterexamples、およびstatistical／provenance logicである。
