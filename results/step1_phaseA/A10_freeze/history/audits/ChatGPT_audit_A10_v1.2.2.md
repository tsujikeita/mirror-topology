# ChatGPT監査：Step 1 Phase A-10 v1.2.2
**Claude伝達用 / 2026-09-12 / 実行前監査**

## 0. 総合判定

A10 v1.2.2は、v1.2.1監査で求めた二つの必須修正を正しく実装している。

- `scan()`はselected score・T1・T2の非有限値でfail-fastする。
- positive-control inventoryは`QB`・`loB`・`DB`のfiniteおよび`DB>0`を検査し、observed positive controlも`QBo`・`loBo`・`DBo`・分子・分母を検査する。
- 二重`diff_ci`は削除された。
- W2 checkpointは実際の`IND`・`CRN`・`TwI`、platform、CPU、live thread情報へ追加bindingされた。
- 5 bootstrap seedのequivalence verdictと、model／isotropic双方のf32/f64 sensitivityが保存される。
- required gateとdiagnostic gateの区別がprovenanceへ明記された。

静的検査、SHA検査、v1.2.1との差分、A8b frozen kernelとの照合では、これらの修正はPASSである。

しかし、今回のsandbox smokeが新たに発見した事実に対して、現行sourceのgate semanticsがまだ閉じていない。また、random-stream registryに実際の衝突がある。

> **A10 v1.2.2 core numerical design：PASS**  
> **v1.2.1必須修正2件：PASS**  
> **f32/f64 Event B・continuous-output policy：未確定**  
> **calibration／pseudo random streams：衝突あり**  
> **現行v1.2.2 formal smoke／official：HOLD**  
> **短いv1.2.3修正後：SMOKE GO見込み**  
> **Event B、m判定、calibration、W2の根本的再設計：不要**

---

## 1. 独立静的検査

```text
notebook cells                 7
code cells                     5
全code cell AST parse          PASS
全code cell compile            PASS
gate assignments               56
required smoke                 49
required official              55
```

独立SHA：

```text
notebook file SHA256
0eed680bc433241bd904faf762751cf326e49aeafd1e1c5749088e8ba679ddb8

canonical source-only SHA256
beddbb2db058a1e278adc00839a5f3a39493b76eaa9a3df71263f0128be3ff38
```

実装報告と一致する。

---

## 2. v1.2.1監査の必須2項目：PASS

### 2.1 scan non-finite fail-fast

各chunkで：

```python
Sp = f @ Fp.T
ax = Sp.argmin(1)
sel = Sp[np.arange(len(x)), ax]

t1 = ...
t2 = ...

if not (
    np.isfinite(sel).all()
    and np.isfinite(t1).all()
    and np.isfinite(t2).all()
):
    raise FloatingPointError(...)
```

となる。

NaNがEvent BのFalseとして静かに集計される経路は閉じた。A8b childのfail-fast semanticsと整合する。

### 2.2 positive control inventory

現在の`G_cal_control_inventory`はpositive pseudo-controlについて：

```text
len(QB)=len(loB)=len(DB)=N_PSEUDO
QB finite
loB finite
DB finite
DB > 0
```

を要求する。

observed positive controlも：

```text
QBo finite
loBo finite
DBo finite
HIo.sum() > 0
HBo.sum() > 0
lower CI >= 3
Q >= 10
D > 1
```

を要求する。

v1.2.1のinf／NaNによる偽PASS経路は閉じた。

---

# 3. 【BLOCKER 1】sandboxで観測したT2差と、現行gateが整合しない

実装報告は、m10_rep1で：

```text
f32/f64 raw-axis flip fraction   5e-5
全flip                           exact antipode
T1最大相対差                     3.8e-8
T2最大相対差                     1.7e-6
Event B                          identical
```

と報告する。

このT2差は、A8bで用いた`TOL_EVAL=1e-6`を僅かに超える。

一方、A10のrequired engine gate：

```python
G_cal_f32_f64_selected_output_equiv = (
    same_or_antipode
    and allclose(T1, T1_f64, rtol=1e-6)
    and allclose(T2, T2_f64, rtol=1e-6)
)
```

は現在も`1e-6`のままである。

### 実行上の問題

報告された`1.7e-6`型の差がofficial calibration sampleに一つでも現れれば、A10aは`ENGINE_VALID=False`で停止する。

sandbox smokeが通ったのは：

- required gateが検査したcalibration streamでは当該flipが出なかった
- 差が出たm10_rep1 sensitivityはdiagnosticであり、required gateではない

ためである。

従って「smoke 49/49」は、この新現象を解決したことを意味しない。

### formal false-pass側の問題

m10／m100の4 runでは、次を記録するだけでrequiredにしない。

```text
all flips antipodal
Event B identical
max T1/T2 difference
```

従ってofficial sampleで：

```text
non-antipodal flip
または
Event B mismatch
```

が生じても、primary Q／m decisionは計算され、A10_VALIDになり得る。

これは、float32 routeをA10のproduction pathとして採用する証拠鎖として弱い。

---

## 4. plane-folded axisとT1/T2の意味を分ける必要がある

今回の観測は重要である。

幾何学的には`n`と`-n`は同じmirror planeである。しかしnearest-pixel reflection＋maskの実装では、一部antipodal pairのR行が同一ではない。そのため：

```text
plane-folded axisは同一
しかしraw selected axisのB-行が違い
T2が僅かに変わる
```

ことがある。

従って、次の二文を同一視してはいけない。

1. scientific axis labelはunoriented plane `[n]={n,-n}`
2. T1/T2はplane classだけで一意に決まる

現実装で正しいのは：

> **axisの幾何学的報告はplane-foldedにするが、T1/T2はfloat32 scanが返したraw oriented pixel representativeのfloat64 B±行で評価する。**

raw axisを捨ててPLだけ保存すると、T2を完全には再構成できない場合がある。

---

## 5. 推奨するcross-selection policy

A8bのhistorical freezeを黙って`1e-6 → 1e-5`へ書き換えるべきではない。A10 smokeで新しいphysical-distribution stress caseが見つかった、と透明に扱う。

### 推奨A：A10固有のprospective amendment

v1.2.3で、例えば：

```python
TOL_CROSS_SELECTION_CONT = 1e-5
```

を**official前に**固定し、理由を：

```text
pixelized antipodal representativesのB-差に対する
A10-specific engineering sensitivity bound
```

と明記する。

次を共通helperにする。

```python
def compare_selection_paths(d32, d64):
    same_plane = (
        (d32["AX"] == d64["AX"])
        | (d32["AX"] == ANTIPODE[d64["AX"]])
    )

    eb_same = np.array_equal(
        event_B(d32["T1"], d32["T2"]),
        event_B(d64["T1"], d64["T2"]),
    )

    t1_rel = ...
    t2_rel = ...

    return {
        "same_plane": bool(np.all(same_plane)),
        "eventB_identical": bool(eb_same),
        "T1_rel": t1_rel,
        "T2_rel": t2_rel,
        "continuous_bound": (
            t1_rel < TOL_CROSS_SELECTION_CONT
            and t2_rel < TOL_CROSS_SELECTION_CONT
        ),
    }
```

required gate：

```text
G_cal_f32_f64_plane_event_equiv
G_m_f32_f64_plane_event_equiv_all_runs
G_m_f32_f64_continuous_bound_all_runs
```

最低限、Event B一致は全4 m run・model／isotropic双方でrequiredにする。

### 推奨B：numeric toleranceをscience gateにしない場合

production float32 pathを唯一のauthoritative pathとし、f64はsensitivity diagnosticと明記する。

その場合も：

```text
全flip same or exact antipode
Event B exact
```

はrequiredとし、T1/T2差はdiagnosticとして保存する。

W2はcontinuous statisticなので、別途小さなf32-vs-f64 W2 sensitivityを保存するか、production path固定の結果であることを明記する。

### 推奨しない方法

```text
実装報告に「例：1e-5」と書くだけ
```

では不十分である。

現行codeは1e-6のrequired gateを保持し、m runsはnon-requiredだからである。

---

# 6. 【BLOCKER 2】calibrationとpseudo observationが同一乱数streamを使う

random generatorは：

```python
rr = rng_for("rotation", *stream_ids)
rz = rng_for("gaussian", *stream_ids)
```

で作られる。

ところが：

```python
# A10a calibration
generate(..., stream_ids=(0,), ...)

# A10c pseudo observations
generate(..., stream_ids=(0,), ...)
```

であり、完全に同じSeedSequenceを使う。

`STREAM`辞書には`calibration`と`pseudo`が別に定義されているが、`generate()`のrotation／Gaussian generationでは両namespaceを使っていない。

### 独立確認

同じcurrent codeのSeedSequenceで確認すると：

```text
pseudoの最初のrotation群
=
calibrationの最初のrotation群

pseudo Gaussian stream
=
calibration Gaussian streamのprefix
```

である。

具体的に、smoke設定では：

```python
array_equal(R_calibration[:50], R_pseudo) == True
```

となった。

### 影響

pseudo thresholdsはm-sensitivity bankとは独立なので、one-point ratioを直接自己参照する致命的リークではない。

しかし：

- pseudo observationsが「独立stream」という設計になっていない
- W2 whiteningに使うcalibration sampleとpseudo sampleが乱数レベルで重なる
- provenanceのstream registryと実生成が一致しない

ため、formalなPhase A notebookとして修正すべきである。

### 修正

purpose namespaceを明示する。

```python
GEN_NS = {
    "calibration": 100,
    "m_sensitivity": 200,
    "pseudo": 300,
    "negative_control": 400,
    "w2_independent": 500,
    "w2_crn": 600,
    "w2_isotropic": 700,
}
```

例：

```python
generate(..., (GEN_NS["calibration"], 0), ...)
generate(..., (GEN_NS["pseudo"], 0), ...)
generate(..., (GEN_NS["m_sensitivity"], m, rep), ...)
```

次をpreflight gateにする。

```text
G_generation_stream_keys_unique
```

全generation callのpurpose＋ID tupleをprovenanceへ保存する。

単にpseudoへ`STREAM["pseudo"]`を付ける場合、現行W2の`(3,0)`等と衝突し得るため、全callを一つのnamespace registryで管理する方が安全である。

---

# 7. mismatch evidenceを保存する

今回の1件は、rules v1.0のaxis semanticsを決める重要なdesign-discovery evidenceである。

summary最大値だけでなく、各run／systemについて：

```text
sample index
AX_float32
AX_float64
antipode relation
T1_float32 / T1_float64
T2_float32 / T2_float64
Event B indicators
```

を、flipした行だけcompact NPZへ保存することを推奨する。

これにより：

- 全flipがexact antipodeか
- 1.7e-6がどのaxis pairで生じたか
- Bp／Bm row differenceとの対応
- officialでのworst case

を第三者が再計算できる。

---

# 8. 5-bootstrap-seed equivalence verdict

5 seedのverdictを保存したことは良い。

seed 0をdecision seedとして固定することは再現可能である。しかしofficialで：

```text
seed0=True
他seedにFalseがある
```

場合、m=100のpractical equivalenceはMonte Carlo境界に近い。

これは実行前blockerとはしないが、official監査では：

```text
equivalence_verdict_5_bootstrap_seeds
```

を必ず確認する。

混在した場合は「安定してequivalent」とfreezeせず、B_BOOT増加または保守的m=10を検討する。

---

# 9. そのほかの確認

### PASS

- positive control finite／D>0
- scan non-finite fail-fast
- W2 checkpoint array-level binding
- W2全pair finite
- m=10 fallback
- required／diagnostic gate区別
- output exact inventory
- source-only SHA
- code compile

### 非blocker注意

- positive pseudo-controlのKDE `DB>0`は、極端なtailでunderflow 0となればofficialをfail-closedにする。これは偽PASSではないが、失敗時は「control failure」ではなくdensity-underflowかを診断する。
- smokeの49/49は実装報告のみで、raw smoke provenance／console logは今回未添付。実行結果自体の独立監査は次回。
- raw axisとplane-folded axisの双方をrules／archiveへ残す。

---

## 10. 最終判断

A10 v1.2.2は、v1.2.1の二つの必須修正を正しく閉じた。中心数値設計は承認できる。

しかし、今回のsandbox smoke自身が：

```text
T2 relative difference = 1.7e-6
```

という、現行`1e-6` selected-output gateを超える現象を発見している。現状ではその現象はdiagnosticに留まり、official m resultのEvent B一致をhard gateしない。

加えて、calibration sampleとpseudo observationが同一rotation／Gaussian streamを使用する。

従って：

> **A10 v1.2.2 CORE：APPROVED**  
> **現行v1.2.2のformal smoke／official：HOLD**  
> **v1.2.3でcross-selection policy＋stream namespaceを修正**  
> **その後SMOKE → OFFICIAL：GO見込み**  
> **研究設計の根本変更：不要**

今回のsource変更でsource-only SHAが変わるため、v1.2.2を先にformal smokeするより、短いv1.2.3を先に作る方が証拠鎖と作業効率の両面でよい。
