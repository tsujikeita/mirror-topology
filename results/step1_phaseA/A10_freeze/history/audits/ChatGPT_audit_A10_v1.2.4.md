# ChatGPT監査：Step 1 Phase A-10 v1.2.4
**Claude伝達用 / 2026-09-12 / 実行前監査**

## 0. 総合判定

A10 v1.2.4は、v1.2.3監査の第一推奨であった、

```text
ℓ=2–4 selection    float64 primary
ℓ=2–4 evaluation   float64
S2 selection       float32のまま
```

という方針を、主解析経路について正しく採用している。A8b freezeを性能benchmarkとして保持し、dtype推薦だけをA10の広いstress evidenceによってsupersedeする整理も妥当である。

また、乱数stream namespace、Event B、m判定、二次元pseudo threshold、3-position W₂、A9/A11 binding、atomic archiveなど、これまでに確定した中心設計は維持されている。

しかし、現行sourceには二つの明確なformal blockerがある。

1. **calibrationのfloat32感度gateが、float64を自分自身と比較しており空洞化している。**
2. **W₂のrequired coupling gateが、実際にOTへ投入する部分標本の上界になっておらず、さらに「decision insensitive」を保証しない。**

加えて、m runのhelper引数・NPZ key・console labelが逆転／誤記され、provenance内にv1.2.3の「float32 authoritative／float64は未採用」という文言が残っている。

> **A10 v1.2.4 primary science core：PASS**  
> **ℓ2–4 float64 primaryへの変更：APPROVED**  
> **random-stream／Event B／m／calibration／W₂本体：概ねPASS**  
> **calibration sensitivity gate：FAIL（自己比較）**  
> **W₂ sensitivity required gate：FAIL（部分標本をboundしない）**  
> **provenance／evidence labels：要修正**  
> **現行v1.2.4 formal smoke／official：HOLD**  
> **短いv1.2.5修正後：SMOKE → OFFICIAL GO見込み**

primaryのfloat64結果そのものを否定する問題ではない。修正対象はfloat32 sensitivityの配線・証拠鎖とW₂ sensitivity gateであり、Event B、m decision、calibration、OT solverを作り直す必要はない。

---

## 1. 独立静的検査

```text
notebook cells                 7
code cells                     5
全code cell AST parse          PASS
全code cell compile            PASS
gate assignments               61（全て一意）
required smoke                 52
required official              58
```

独立SHA256：

```text
notebook file
49b37152f4bae8f065dbd7218c4da69929c514b5ea3da66557a33e0b8ef95f4d

canonical source-only
1db585de5169dbb3baae939e8f49828d182dcb6b55fcc9f079b07f6df4ecd830

implementation report
1a43a5a56ba6ffa940145b797943583577f2c76c6bdfc2a67910f8d937c24bca
```

notebook fileとsource-onlyは実装報告の値と一致した。

---

## 2. float64 primaryへの切替：中心経路はPASS

`PROD`は現在、

```text
route             l24_feature231
selection dtype   float64
evaluation dtype  float64
sample chunk      20000
threads           2
primary           float64
sensitivity       float32
```

である。

calibration、4 m run、W₂のprimary poolは`PRIM='float64'`を使い、m decision、pseudo calibration、W₂の正式値はfloat64 selectionに基づく。従ってv1.2.3で問題となった、非対蹠near-tieやantipodal representative差がprimary resultへ混入する問題は、設計上回避されている。

A8bのfloat32推薦自体を改変せず、

```text
A8b = performance benchmarkとして有効
A10 = wider stress evidenceによりl2–4 dtypeだけ保守的にf64へ変更
S2  = f32を維持
```

とする履歴も妥当である。

---

# 3. 【BLOCKER 1】calibration sensitivity gateがfloat64同士の自己比較

現code：

```python
cal = calo[(0, PRIM)]
cal64 = calo[(0, 'float64')]
cal32 = calo[(0, 'float32')]
```

現在`PRIM == 'float64'`なので、

```python
cal is cal64
```

である。

ところがgateは：

```python
CALX, cal_flips = compare_selection_paths(cal64, cal)
```

となる。

これは、

```text
float64 vs float64
```

の自己比較であり、`cal32`を一度も使っていない。

従って：

```text
G_cal_f32_f64_selection_consistency
```

は、float32がどれほど異なっていても原則PASSする。`cal_flips`も常に空になり、`a10a_calibration.npz`のflip evidenceは意図した証拠にならない。

実装報告の「calibrationでfloat32を同一(R,z)で併走し、一致gateを掛ける」という説明と、実際のrequired gateが一致していない。

### 必須修正

現helperのsignatureを維持するなら：

```python
CALX, cal_flips = compare_selection_paths(
    cal32,
    cal64,
)
```

とする。

さらにpreflightで：

```python
assert cal is cal64
assert cal32 is not cal64
```

を入れると、将来のprimary切替時にも同じalias bugを発見しやすい。

---

# 4. 【BLOCKER 1b】m runではhelper引数が逆で、evidence labelも反転

helperは：

```python
def compare_selection_paths(d32, d64):
```

であり、返却evidenceも：

```text
AX32 = d32
AX64 = d64
T1_32 / T1_64
T2_32 / T2_64
```

と命名されている。

しかしm runでは：

```python
compare_selection_paths(
    out[(s_, PRIM)],
    out[(s_, SENS)],
)
```

すなわち：

```text
第1引数 = float64 primary
第2引数 = float32 sensitivity
```

であり、signatureと逆である。

このため：

- `AX32`にfloat64 axisが入る
- `AX64`にfloat32 axisが入る
- relative differenceの分母が意図と逆になる
- flip evidenceのlabelが逆になる
- threshold境界では`consistency`判定自体が変わり得る

### 必須修正

```python
compare_selection_paths(
    out[(s_, SENS)],
    out[(s_, PRIM)],
)
```

とする。

より安全なのはhelperを：

```python
def compare_selection_paths(d_sensitivity, d_primary):
```

へ改名し、evidenceも：

```text
AX_sensitivity / AX_primary
T1_sensitivity / T1_primary
T2_sensitivity / T2_primary
```

とすることである。こうすれば将来dtypeを再変更しても、32／64というlabelが意味と逆転しない。

synthetic self-testも、実際の呼出し順と同じ：

```python
compare_selection_paths(alt, reference)
```

へ統一する。

---

## 5. m artifactの名称がfloat32／float64で逆

m runではsensitivity pathを：

```python
r64, hM64, hI64
```

と命名しているが、実体は`SENS='float32'`である。

consoleにも：

```text
f64sel Q=...
```

と表示するが、実際にはfloat32 selectionのQである。

`a10b_cluster_hits.npz`にも：

```text
hM64
hI64
```

というkeyでfloat32 hit countsが保存される。

これはprimary数値を変えないが、formal archiveとして重大なlabel errorである。

### 修正

```text
r32
hM32
hI32
f32sel Q
```

へ変更する。

旧名称を残す必要がある場合は、manifestに「legacy misnomer」と書くのではなく、official前なので正しいkeyへ変更した方がよい。

---

# 6. 【BLOCKER 2】W₂のfull-pool RMSは、実際のsubsample W₂の上界ではない

現codeはpool全体について：

```python
eps_j = sqrt(
    mean(||z64_i - z32_i||^2)
)
```

を計算する。

同じ全empirical pool同士については、paired couplingにより：

```text
W₂(P_full^64, P_full^32) <= eps_full
```

は正しい。

しかし実際のobserved W₂とnull W₂は、pool全体ではなくrandom cluster subsetから計算される。

full-pool RMSは、任意のsubsetのpaired RMSを上から抑えない。

### 合成反例

```text
100 samples中99 samplesは差0
1 sampleだけ差10
```

なら：

```text
full-pool eps = 1
その1 sampleだけを選ぶsubset eps = 10
```

となる。

従って現在の：

```text
G_w2_f32_coupling_bound
```

は、実際にOTへ投入した各subsampleのW₂差を保証しない。null側の`2*eps_iso`にも同じ問題がある。

---

# 7. 5% of q99だけでは「decision insensitive」を保証しない

仮にsubsetごとの真の上界が得られても：

```text
bound <= 0.05 * q99
```

だけでは、above／below q99判定の不変性は保証されない。

例えば：

```text
q99              = 1.000
observed W₂      = 0.990
selection bound  = 0.040
```

ならboundはq99の5%未満であるが、alternate selectionでobservedが1.030へ動けば判定は反転し得る。null q99自身もselection pathで動き得る。

従って、現在のコメント：

```text
for the W2 decision to be insensitive
```

および実装報告の「pair差上界をq99の5%以内にgate」は、数学的には過剰な主張である。

### 修正案A：f64 primaryなのでdiagnosticへ降格

もっとも簡潔である。

```text
G_w2_full_pool_selection_rms_small
```

へ改名し、requiredから外す。

表現は：

> full empirical poolsにおけるpaired-coupling RMSがnull q99 scaleに比べて小さいというengineering diagnostic。個別subsampleのdecision invarianceを証明しない。

とする。

primaryはfloat64なので、これでA10の正式W₂結果は損なわれない。

### 修正案B：実際のsubsampleごとにrigorous bound

OTへ使うexact cluster subsetについて、同じsubsetの：

```python
eps_subset = sqrt(
    mean(||z64 - z32||^2)
)
```

を計算する。

各observed pairについて：

```text
|W₂64(j,k) - W₂32(j,k)|
<= eps_j_subset + eps_k_subset
```

を保存する。

null replicateについても、三つのexact blocksごとにepsを計算し、replicateの`W2_max` perturbation boundを保存する。

全null replicateの最大boundを`delta_q99_bound`とすれば、empirical q99 shiftもその値以下に抑えられる。

判定不変性を要求するなら、各observed seedについて：

```python
abs(W2max64 - q99_64) \
    > observed_bound + delta_q99_bound
```

をrequiredにする。

これはOTを二重実行せずに実装できる。

---

## 8. A10cのfloat32 sensitivityは「primary pseudo thresholds固定」の条件付き診断

A10cではpseudo thresholdsをfloat64 primaryだけで生成する。

float32 sensitivityは：

```text
同じfloat64 pseudo thresholds
＋float32-selected model／isotropic hit tables
```

を比較する。

従って現在のdiagnosticが測るのは：

> primary threshold setを固定したとき、model／isotropic側だけをfloat32 selectionへ変えた影響

である。

これは有用なconditional sensitivityであり、f64 primary analysisには十分である。

ただし実装報告の：

> calibration・4 m run・pseudo・negative control・W₂の3 poolはすべてfloat64 primaryで生成し、float32は同一(R,z)で併走

は、pseudoとnegative controlについては文字どおりには正しくない。

### 選択肢

- 報告書を「calibration・m run・W₂ poolsでf32を併走。A10cはprimary pseudo thresholds固定のconditional sensitivity」と修正する。
- full alternate pipeline sensitivityが必要なら、pseudoも`(PRIM,SENS)`で生成し、f32 pseudo thresholdsを用いたsupport arrayまで比較する。

現在f64 primaryを正式経路とする限り、前者で十分であり、これはprimary blockerではない。

---

# 9. provenance／コメントにv1.2.3の方針が残る

v1.2.4はf64 primaryを採用したが、code内には次が残る。

```text
production scan (A8b frozen): float32 selection
Production float32 selection is authoritative
Rule-level alternative (float64 selection for l2-4) is left/deferred
```

最終provenanceの`cross_selection_policy.status`も：

```text
float64 selection ... deferred to the rules audit
```

と書く。

これはv1.2.4の実際の`PROD`および実装報告と正面から矛盾する。

### 必須修正

例えば：

```text
primary float64 selection for l2–4 was adopted prospectively in v1.2.4 before the official run; A8b's float32 result remains a valid performance benchmark and sensitivity path; S2 remains float32.
```

へ置換する。

併せて：

- `scan(X, selection='float32')`のdefaultを`float64`へ変更、またはdefaultを削除して明示指定を強制
- cell 1のproductionコメントをf64 primaryへ修正
- W₂ cell冒頭の「calibrated MC p」をfinite-pool exceedanceへ修正
- positive-controlコメントの`0.5`を実コードの`0.35`へ修正

を行う。

---

## 10. f64 primaryのchunk 20000は明示的に再選択した方がよい

以前提出されたA8b official CPU CSVを再確認した。

```text
l24_feature231 / float64 / winner
  chunk               2000
  N                   1,000,000
  production time     76.658 s / 10^6
  peak increment      0.099 GB
```

A8bのsafe-choice ruleは「最大throughputの5%以内なら小さいchunk」を選ぶため、f64 routeではchunk 2000が正式winnerであった。

v1.2.4は、f32 winnerのchunk 20000をそのままf64 primaryへ使う。

これは数値的な誤りではない。A8bではf64のchunk-invarianceも確認済みであり、chunk 20000も測定済み・eligibleである。ただし：

- 「dtypeだけsupersede」と言うなら、chunkは意図的な新選択であることを記録する
- またはf64 benchmark winnerのchunk 2000を採用する
- chunk 20000を使うなら、A8b CPU CSVの該当f64 measurementへhard bindingし、speed／memory rationaleを保存する

方がよい。

これはprimary science blockerではないが、rules v1.0へ転記するengineering値としては整理が必要である。

---

## 11. sandbox smokeの扱い

実装報告は：

```text
SMOKE_PASS 52/52
4 component True
```

とする。

しかし今回添付されたのはnotebookと実装報告であり、raw smoke provenance／checkpoints／console logはないため、実行結果自体は独立再集計していない。

さらに：

- calibration sensitivity gateはf64自己比較
- W₂ coupling gateは実際のsubsample boundではない

ため、報告された52/52は「意図した全sensitivityを検証した52/52」ではない。

primary f64経路が動くことのsmoke evidenceとしては有用だが、formal confirmationには修正版のnew smokeが必要である。

---

## 12. v1.2.5の最短修正

### 必須

1. helper呼出しを統一

```python
CALX, cal_flips = compare_selection_paths(cal32, cal64)

compare_selection_paths(
    out[(s_, SENS)],
    out[(s_, PRIM)],
)
```

2. `r64/hM64/hI64/f64sel`を`r32/hM32/hI32/f32sel`へ修正

3. W₂ coupling gateを：
   - full-pool diagnosticへ降格、または
   - exact subsample bound＋decision margin gateへ変更

4. provenance／commentsをf64 primary policyへ更新

### 強く推奨

5. f64 chunkを2000へするか、chunk 20000をf64 measurementへbindingして理由を記録

6. A10c sensitivityがprimary pseudo thresholds固定のconditional analysisであることを明記

7. helper self-testへ、実際のf32／f64 argument orderと「自己比較では異常を検出できない」negative caseを追加

---

## 13. 最終判断

A10 v1.2.4の最も重要な設計判断、すなわち：

```text
ℓ2–4はfloat64 primary
S2はfloat32を維持
A8b freezeは性能benchmarkとして保持
```

は承認できる。

primaryのEvent B、m sensitivity、one-point calibration、3-position W₂の数値経路にも、新たな根本的誤りは見つからなかった。

しかしformal sensitivity／archiveについて：

- calibration gateがf64自己比較
- m helperの引数・evidence labelsが逆
- W₂ full-pool RMSをsubsample decision boundと誤って扱う
- provenanceが旧f32-primary方針を記述する

ため、現sourceをそのままofficial artifactへすることにはGOを出せない。

> **A10 v1.2.4 PRIMARY CORE：APPROVED**  
> **現行v1.2.4 formal run：HOLD**  
> **v1.2.5へ短修正後：SMOKE → OFFICIAL GO**  
> **研究設計／D(R)／Event B／m／calibration／OT solverの根本的変更：不要**

full frozen assetsを用いるColab officialは本監査環境では実行していない。監査範囲はnotebook全source、canonical SHA、compile、gate inventory、v1.2.3との差分、helper配線、以前提出されたA8b CPU CSV、W₂ coupling boundの数学的counterexample、provenance semanticsである。
