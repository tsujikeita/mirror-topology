# ChatGPT監査：Step 1 Phase A-10 v1.2.3
**Claude伝達用 / 2026-09-12 / 実行前監査**

## 0. 総合判定

A10 v1.2.3は、v1.2.2監査で指摘した乱数stream衝突を正しく解消している。また、sandboxで発見されたfloat32／float64 selection差を隠さず、non-antipodal near-tieまで含めてevidenceを保存する方向も妥当である。

独立検査では：

```text
notebook cells                 7
code cells                     5
全code cell AST parse          PASS
全code cell compile            PASS
gate assignments               59
required smoke                 51
required official              57
```

SHA256：

```text
notebook file
b2f180ad57d340bb676860828cea516a1f627371eb4b9e3b5e596dcec3123759

canonical source-only
c31841f403e67884fd66d69fa781f8c8a5b7281b65ca6b803d76538dc77e6583

implementation report
4f928dbd3d51d8764b23ac7168e3e36f564b8dd5363237085cb0d6753fa3e783
```

しかし、現在のv1.2.3を最終official sourceとして承認するには、cross-selection policyの適用範囲をもう一段閉じる必要がある。

> **random-stream namespace：PASS**  
> **Event B用cross-selection gate：概念上PASS**  
> **sandboxの新発見の透明性：PASS**  
> **旧exact-antipode probe：新policyと矛盾**  
> **A10c calibrationのcontinuous／pseudo-threshold感度：未検証**  
> **A10d W2のfloat32／float64 selection感度：未検証**  
> **l2–4 production selection policy：未確定**  
> **現行v1.2.3 formal smoke／official：HOLD**  
> **推奨：l2–4をfloat64 primaryへ切替えるv1.2.4、またはf32を維持する場合のcomponent別感度gateを追加**

根本的なEvent B、m、calibration、W2、D(R)設計の作り直しは不要である。

---

## 1. 乱数stream修正：PASS

v1.2.3はgeneration purposeを：

```text
calibration       100
m_sensitivity     200
pseudo            300
negative_control  400
w2_independent    500
w2_crn            600
w2_isotropic      700
```

へ分ける。

実際のgeneration callは：

```text
calibration       (100, 0)
m runs            (200, 10, 1/2), (200, 100, 1/2)
pseudo            (300, 0)
negative control  (400, adopted_m)
W2 positions      (500, 0/1/2)
W2 CRN            (600, 0)
W2 isotropic      (700, 0)
```

であり、計12 callのIDは全て一意である。

現在のSeedSequence式を独立に再構成し、calibrationとpseudoのrotation／Gaussian streamが異なることも確認した。v1.2.2のprefix重複は解消している。

`G_generation_stream_keys_unique`もrequiredである。

### 軽微な補強

現在のgateは「実行されたcall同士が一意」であることを確認するが、期待する12 callが全て存在するかをexact inventoryでは確認しない。

最大限のhardeningを望むなら、modeごとの期待call key集合も固定する。

---

## 2. sandboxで得られた新事実の解釈

報告された8×10^4標本では：

```text
exact-antipode flip
non-antipodal plane flip
T2差 最大 5.4e-3 relative
Event B mismatch 0
```

が観測された。

これは、A8bの10^4 auditで見えた「exact-antipode flipのみ」という経験則が、より広いphysical-distribution stress sampleでは一般化しなかったことを意味する。

ただし、non-antipodal例：

```text
AX32 = 1357
AX64 = 1420
```

についてHEALPix RING Nside=16のpixel centerを独立計算すると、plane-folded角距離は約：

```text
3.6859 degrees
```

である。従って、報告された唯一のnon-antipodal例は任意に遠いplaneではなく、grid-neighbour scaleのnear-degenerate minimumである。

この発見は数値カーネルの破綻ではない。float32とfloat64が、非常に近いS+を持つ別candidateを選んだ結果である。

---

## 3. 現在のcross-selection helper

v1.2.3はfloat32 productionをauthoritativeとし、float64をsensitivity pathにする。

required conditionは：

```text
flip時のfloat64-evaluated T1差 < 1e-6
Event B mismatch fraction <= 1e-5
```

である。

このpolicyは、A10bのprimary quantityである固定観測閾値Event Bとsupport ratio Qのengineering stabilityを守るものとしては理解可能である。

また、model／isotropic、m10／m100、rep1／rep2の全8 datasetへ同一helperを適用し、flip行をNPZへ保存する点は良い。

しかし、このpolicyが保証するのは：

> **fixed observed-threshold Event Bがfloat32／float64 selection間で十分安定すること**

である。

次は保証しない。

```text
unique mirror-plane axis
continuous T1/T2 distribution
pseudo-threshold calibration result
W2 distribution distance
```

この適用範囲を曖昧にしたまま`A10_VALID`へ統合しない方がよい。

---

## 4. 【FORMAL BLOCKER 1】旧いexact-antipode probeがrequiredに残る

`REQ_A`には依然として：

```python
G_f32_selection_plane_equiv_probe
```

が入る。

このgateは固定5標本について：

```text
axisはsameまたはexact antipode
T1/T2はrtol=1e-6
```

を要求する。

これはv1.2.3の新policy：

```text
non-antipodal near-tieも許容
T2のcontinuous boundは要求しない
Event B mismatch率で判定
```

と意味が矛盾する。

固定5標本がたまたま問題を含まないためsandboxでは通るが、別BLAS／hardwareで近接tieが現れれば、新policy上は許容されるcaseを旧gateが停止させ得る。

### 修正

旧gateをrequiredから外すか、`compare_selection_paths`そのもののself-testへ置換する。

最低限：

```text
1. same axis + same outputs                   PASS
2. non-antipodal but T1-near-tie + EB same   PASS（現在のpolicy）
3. flip with T1 difference >=1e-6            FAIL
4. EB mismatch rate >1e-5                    FAIL
5. non-finite selected output                 FAIL
```

をhelperへ直接掛ける。

---

## 5. 【METHODOLOGICAL BLOCKER 2】Event B gateはW2を検証しない

A10d W2はcontinuous `(T1,T2)` 分布を使用する。

しかしW2 pool生成は：

```text
float32 selectionのみ
```

であり、float64 selectionを併走しない。

今回sandboxは、Event Bが全件一致しても、T2が最大0.5%変わるcaseを実際に発見した。従って：

```text
Event B mismatch = 0
```

から：

```text
W2はselection precisionに不変
```

とは結論できない。

実装報告の「float64を全runで併走」は、実際にはcalibrationと4つのm runについてであり、W2 primary／CRN／nullには当てはまらない。

### 最も簡潔な解決：l2–4はfloat64 selectionをprimaryにする

Claude自身が提起しているように、l2–4のfloat64 selectionは約1.3分／10^6であり、A10全体のW2計算時間に比べれば小さい。

従ってrules v1.0では：

```text
l2–4 selection   float64
l2–4 evaluation  float64
S2 selection     float32
S2 evaluation    float64
```

と分けるのが最も保守的である。

A8b freezeは「性能benchmarkとしてのf32推奨」を保持したまま、A10の広いphysical stress evidenceに基づき、final rulesでl2–4だけf64へsupersedeできる。

この選択なら：

- non-antipodal selection ambiguityをprimary pathから除ける
- pseudo-threshold calibrationの感度問題を除ける
- W2のcontinuous-output感度問題を除ける
- Event B mismatch toleranceという新しい近似規則に依存しない
- 追加計算コストは小さい

ため、今回の監査ではこの方針を第一推奨とする。

### float32 primaryを維持する場合

少なくとも次を追加する。

1. **Qの直接感度gate**  
   4 m runについて`abs(logQ_f32-logQ_f64)`を事前登録幅以内にする。Event B mismatch率だけでなく、最終ratioへ直接gateを掛ける。

2. **one-point calibration sensitivity**  
   float64 selectionでもmodel／iso hit tableを作り、false-support frequency・Q lower CI・D／support arrayへの影響を保存する。

3. **W2 sensitivity**  
   次のいずれか：
   - same subsampleでfloat64-selection W2も計算し、decision一致を要求
   - paired outputsからcoupling upper boundを計算する

   同一latent sampleのwhitened outputsを`z32_i,z64_i`として：

   ```text
   eps_j = sqrt(mean(||z32_i-z64_i||^2))
   ```

   は`W2(P32_j,P64_j)`の上界である。triangle inequalityにより、position pairのW2差は`eps_j+eps_k`以下となる。この上界をq99／observed marginに対して十分小さいことをgateすれば、OTを二重実行せずに検証できる。

4. **axis semantics**  
   non-antipodal near-tieがあるrunでは、float32とfloat64でunique planeが一致するとは主張しない。axis inferenceにはfloat64またはnear-minimizer setを用いる。

---

## 6. A10c pseudo-threshold calibrationへの影響

A10cはpseudoごとに異なる `(T1_p,T2_p)` をthresholdに使う。

現在のcross-selection helperが比較するEvent Bは固定観測閾値：

```text
T1 <= T1_obs
T2 <= T2_obs
```

だけである。

従って固定Event Bでmismatch 0でも、typical distribution内の200 pseudo thresholdsでは、T2の0.5%差によりhit membershipが変わる可能性がある。

float32 primaryを定義として採用するなら計算自体は一意であるが、float64 sensitivity pathを数値正確性の裏付けとして使うなら、A10cの最終support outputまで比較しなければならない。

この点も、l2–4をfloat64 primaryへする方が簡潔である。

---

## 7. reportの「AXとPLを保存」の範囲

calibration artifactはfull：

```text
AX
PL
AX_f64sel
flip evidence
```

を保存する。

一方、4つのm runについて`a10b_cluster_hits.npz`へ保存されるのはcluster hitとbootstrapであり、full AX／PL arraysではない。`a10b_flip_evidence.npz`にはflip行だけが保存される。

従って実装報告の：

> raw oriented representativeとplane-folded labelの双方を保存

は、全m sampleについてのfull archiveという意味では正確でない。

次のどちらかにする。

- 報告文を「calibrationはfull保存、m runは全flip evidenceを保存」へ限定
- axis distributionを後で利用するなら、m runのfull AX／PLも圧縮保存

これはEvent B／m decisionの正否を変えるblockerではない。

---

## 8. sandbox smokeの位置づけ

実装報告は`SMOKE_PASS 51/51`を記録する。

今回添付されたのはnotebookと実装報告であり、sandbox smokeのraw provenance、flip NPZ、console logは添付されていない。そのため：

```text
51/51という実行結果
4件のflip raw values
```

はreport由来であり、本監査ではbytesから独立再集計していない。

またv1.2.3 policyは、その4件を見て定義されたため、同じsandbox dataでの51/51はretrospective consistency checkである。新しいofficial runが最初のprospective testになる。

透明性のため：

```text
v1.2.2 failed-policy sandbox report／flip evidence
v1.2.3 implementation report
notebook source SHA
```

を同じcommitまたはfreeze historyへ残すことを推奨する。

---

## 9. 実行を止めない小補強

### 9.1 relative denominator

```python
abs(T1_32-T1_64)/abs(T1_64)
```

は、形式上はzero denominatorを持ち得る。

```python
scale = np.maximum(
    np.abs(T1_64),
    np.finfo(float).tiny,
)
```

へする。

### 9.2 generation stream exact inventory

uniqueだけでなく、modeごとのexpected 12-call inventoryもgateするとsource driftを検出しやすい。

### 9.3 non-antipodal例の記述

報告された1357↔1420はplane-folded約3.69°で、Nside=16のgrid-neighbour scaleである。この点をprovenanceへ保存すると、「異なるplaneだがnearby」と理解しやすい。

ただしcurrent helperはangular distanceを制限しない。axisをscientific outputとして用いる場合は、角距離またはnear-minimizer setを別に登録する。

---

## 10. 最終判断

A10 v1.2.3は、乱数streamを正しく分離し、A8bの狭いauditでは見えなかったcross-selection ambiguityを発見・記録した価値の高いdesign-discovery notebookである。

コードは構文上正しく、現在のpolicyどおりなら動く可能性が高い。

しかし、現行sourceには：

1. 新policyと矛盾する旧`G_f32_selection_plane_equiv_probe`がrequiredに残る
2. Event B向けのcross-selection gateを、continuous W2／pseudo-threshold calibrationの妥当性へ接続していない
3. l2–4をfloat32 primaryに残すかfloat64へ変更するかがrules上未決定

という問題がある。

従って：

> **A10 v1.2.3 CODE CORE：APPROVED**  
> **random stream fix：PASS**  
> **current Event B cross-selection policy：限定付きPASS**  
> **現行v1.2.3 formal official：HOLD**  
> **第一推奨：l2–4 selectionをfloat64 primaryへ変更し、S2だけfloat32を維持するv1.2.4**  
> **代替：float32を維持し、A10c／W2 component別の感度gateを追加するv1.2.4**  
> **その後SMOKE → OFFICIAL：GO見込み**

A8bのbenchmark／freeze自体を無効にする必要はない。A8bは性能結果として保持し、最終rulesのl2–4 dtype recommendationだけをA10の広いstress evidenceによりsupersedeするのが最も自然である。
