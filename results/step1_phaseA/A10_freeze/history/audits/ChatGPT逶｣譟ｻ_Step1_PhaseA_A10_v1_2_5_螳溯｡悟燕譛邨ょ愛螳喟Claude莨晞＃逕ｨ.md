# ChatGPT監査：Step 1 Phase A-10 v1.2.5
**Claude伝達用 / 2026-09-12 / 実行前最終監査**

## 0. 総合判定

A10 v1.2.5は、v1.2.4監査で指摘した4つの必須事項と3つの強い推奨事項を、コード上でも適切に反映している。

確認した中心修正は次のとおりである。

1. calibrationのfloat32感度は`cal32`対`cal64`を実際に比較する。
2. m runのhelper引数は`sensitivity, primary`の順に統一され、証拠ラベルもdtype非依存名へ修正された。
3. m runのfloat32 sensitivity artifactは`r32 / hM32 / hI32 / f32sel`として正しく保存・表示される。
4. W₂ sensitivityは、OTへ実際に投入したexact cluster subsetごとのpaired RMSから、observed statisticとnull q99の摂動上界を構成する。
5. decision-margin gate
   \[
   |W_{2,\mathrm{obs}}-q_{99}|
   >
   \Delta_{\mathrm{obs}}+\Delta_{q99}
   \]
   をofficial requiredにした。
6. full-pool RMSは任意のsubsampleをboundしないことを明記し、diagnosticへ降格した。
7. ℓ=2–4のfloat64 primaryはA8b officialのfloat64 winner（chunk 2000）、float32 sensitivityはfloat32 winner（chunk 20000）へbindingされた。
8. provenance／comment／出力名はfloat64 primaryへ統一された。
9. A10cのfloat32比較は「float64 primaryのpseudo thresholdsを固定したconditional sensitivity」と明記された。

静的検査と数理監査では、新たな実行停止級・科学的結論無効化級の問題は見つからなかった。

> **A10 v1.2.5 CODE DESIGN：APPROVED**  
> **COMMIT・SMOKE RUN：GO**  
> **SMOKE_PASS後のOFFICIAL RUN：GO**  
> **rules v1.0への転記・A10 freeze：official成果物の独立監査後GO**  
> **事前にv1.2.6を作成する必要：なし**

---

## 1. 独立静的検査

```text
notebook cells                 7
code cells                     5
全code cell AST parse          PASS
全code cell compile            PASS
gate assignments               64（重複なし）
required smoke                 53
required official              60
```

独立SHA256：

```text
notebook file
feaa44eb0eb5c255d1c92090da956d22201d9971c4e4b94887b6c57446e18e06

canonical source-only
ecc8a79c26e5300d7da5c87fef8cf0db8c1b31130b6708df02db955cc5dbac09
```

実装報告の値と一致する。

---

## 2. helper配線・証拠ラベル：PASS

### calibration

現在は：

```python
cal = calo[(0, PRIM)]
cal64 = calo[(0, "float64")]
cal32 = calo[(0, "float32")]

assert (
    cal is cal64
    and cal32 is not cal64
    and cal32["AX"] is not cal64["AX"]
)

CALX, cal_flips = compare_selection_paths(
    cal32,
    cal64,
)
```

となる。

前版の`float64 vs float64`自己比較は解消した。

さらに：

```python
G_cal_sensitivity_wiring
```

は、helperが報告したflip数と、

```python
sum(cal32["AX"] != cal64["AX"])
```

を一致させるため、別配列を比較したことをformalに確認する。

### m run

現在の呼出しは：

```python
compare_selection_paths(
    out[(system, SENS)],
    out[(system, PRIM)],
)
```

であり、helper signature：

```python
compare_selection_paths(
    d_sensitivity,
    d_primary,
)
```

と一致する。

evidenceも：

```text
AX_sensitivity / AX_primary
T1_sensitivity / T1_primary
T2_sensitivity / T2_primary
EB_sensitivity / EB_primary
```

として保存される。

### artifact・console

float32 sensitivityは：

```text
r32
hM32
hI32
f32sel Q
```

となり、前版の逆ラベルは解消した。

---

## 3. ℓ=2–4 float64 primaryとchunk binding：PASS

production specificationは：

```text
route                  l24_feature231
primary selection      float64
evaluation             float64
primary sample chunk   2,000
sensitivity selection  float32
sensitivity chunk      20,000
BLAS threads           2
```

である。

A8b official CPU CSVから、route=`l24_feature231`かつstage=`winner`のrowをselection dtype別に読み、次をrequired gateにする。

```text
float64 winner chunk = 2,000
float32 winner chunk = 20,000
両winner N           = 1,000,000
```

したがって、dtypeだけでなくchunkもA8bの各dtype benchmark結果へbindingされている。

A8b freezeは性能benchmarkとして保持され、final ruleではA10の広いstress evidenceに基づいてℓ=2–4のdtype recommendationだけをfloat64へ変更する。S2はfloat32のままである。

---

## 4. cross-selection helper self-test：PASS

実際のhelperに対して、次のケースを検査する。

```text
same axis・same outputs                         PASS
non-antipodal near-tie・Event B同一             PASS
flip＋T1差が登録値以上                          FAIL
Event B mismatch率が登録値超過                  FAIL
非有限output                                     FAIL
不良alternativeの自己比較                       flip 0（検出不能）
```

最後のnegative caseとcalibration alias assertを組み合わせることで、自己比較による偽PASSを防ぐ。

相対差の分母は`finfo(float).tiny`で保護される。

---

## 5. W₂ exact-subset coupling bound：数学的にPASS

### 5.1 exact subsetのpaired RMS

observer position \(j\)について、OTへ実際に投入する同一cluster subset上で、

\[
\epsilon_j
=
\sqrt{
\frac1n
\sum_{i\in A_j}
\left\|
z^{64}_{i,j}-z^{32}_{i,j}
\right\|^2
}
\]

を計算する。

同じindex同士を結ぶcouplingはempirical transport planとして許されるため、

\[
W_2(P_j^{64},P_j^{32})
\le \epsilon_j
\]

が成立する。

### 5.2 observer pairのW₂差

triangle inequalityから、

\[
\left|
W_2(P_j^{64},P_k^{64})
-
W_2(P_j^{32},P_k^{32})
\right|
\le
\epsilon_j+\epsilon_k
\]

である。

3 pairの最大値についても、

\[
\left|
W_{2,\max}^{64}
-
W_{2,\max}^{32}
\right|
\le
\max_{j<k}(\epsilon_j+\epsilon_k)
\]

が成立する。

コードは各observed seedについて、この右辺を：

```text
W2max_perturbation_bound
```

として保存する。

### 5.3 null q99の摂動

null replicate \(b\)ごとに、

\[
|N_b^{64}-N_b^{32}|
\le \delta_b
\]

を計算し、

\[
\Delta_{q99}
=
\max_b\delta_b
\]

とする。

empirical order statisticはsup normに関して1-Lipschitzなので、

\[
|q_{99}^{64}-q_{99}^{32}|
\le \Delta_{q99}
\]

が成立する。

### 5.4 decision-margin gate

従って、

\[
|W_{2,\mathrm{obs}}^{64}-q_{99}^{64}|
>
\Delta_{\mathrm{obs}}+\Delta_{q99}
\]

なら、float32 sensitivity pathへ変更してもabove／below q99の符号は変わらない。

現在の：

```text
G_w2_selection_decision_margin
```

は、全n_sub・全observed seedについてこの条件を要求し、official requiredに含まれる。

これは前版のfull-pool RMS gateとは異なり、実際のOT subsetと実際のnull replicateに対応した数学的に妥当なgateである。

### 5.5 full-pool RMS

full empirical pool上のRMSは：

```text
G_w2_full_pool_selection_rms_small
```

としてdiagnosticに残るが、

> 任意のsubsampleをboundしない

と明記され、official statusには影響しない。

この位置づけは正しい。

---

## 6. W₂ checkpoint・resume

W₂ checkpointは現在：

```text
notebook source
live source
package versions
thread設定
platform／CPU
全frozen asset SHA
primary W₂ input arrays
whitening
covariance roots
config／seed／m／mode／n_sub
```

へbindingされる。

fresh OUTからのsmoke／officialでは問題ない。

### 非blockerの追加hardening

selection-sensitivity boundsもcheckpoint内へ入るため、最大限の厳密性を求めるなら、binding payloadへ：

```text
IND32 SHA
CRN32 SHA
TwI32 SHA
```

も追加するとよい。

現状でもnotebook source、versions、platform、thread情報、primary arraysへbindingされ、fresh OUTを要求するため、実行前blockerとはしない。

---

## 7. A10c sensitivityの範囲：明確化PASS

A10cのfloat32 sensitivityは：

```text
float64 primaryで生成したpseudo thresholdsを固定
＋
model／isotropicのselected outputsだけをfloat32 pathへ変更
```

するconditional sensitivityである。

provenanceにはこの範囲が明記されている。

したがって、これは「完全なalternate float32 pipeline」ではないが、float64 primary analysisに対するselection-path sensitivityとして妥当である。

---

## 8. gate inventory・status semantics：PASS

```text
diagnostic gates                         64
required smoke                           53
required official                        60
```

である。

statusはrequired gatesだけでexactに決まり、例えば：

```text
G_m100_usable
G_m_Q_f32_sensitivity_bound
G_m_f32_f64_no_nonantipodal_flip
G_w2_full_pool_selection_rms_small
```

などのdiagnosticがFalseでも、registered primary decisionに影響しない限りstatusは変わらない。

一方、次はrequiredである。

```text
calibration f32/f64 wiring
全m runのcross-selection consistency
m decision policy
calibration controls
W₂ solver／inventory
W₂ official stability
W₂ exact-subset decision margin
output inventory
random-stream exact inventory
gate inventory exactness
```

設計は整合している。

---

## 9. 実行を止めない軽微な修正候補

### 9.1 古いコメント

code commentに次が残る。

```text
A10b header:
"float64 selection sensitivity"
```

実際はfloat64 primary／float32 sensitivityである。

またpositive-controlの古いcommentに：

```text
T1 scaled by 0.5
```

が残るが、実コードはT1・T2とも0.35倍である。

正式provenanceと数値処理は正しいため、実行前blockerではない。commit前にcommentだけ直すとよい。

### 9.2 sandbox smokeの独立監査

実装報告は：

```text
SMOKE_PASS
53 / 53
4 component True
```

とする。

今回添付されたのはnotebookと実装報告であり、sandbox smokeのraw provenance、checkpoints、console logは添付されていない。

従って53/53という実行結果自体は、今回の監査ではbytesから独立再集計していない。fresh runtimeで取得するformal smokeが最初の正式確認になる。

### 9.3 runtime

officialでm=10が採用された場合、100,000 orientation clustersに対するdense bootstrap／pseudo hit-table処理が重く、1.5〜2時間という見積りを超える可能性がある。

これは科学的・数値的blockerではないが、Colab切断へ備えてfresh OUT、十分なRAM、成果物の段階保存を維持する。

---

## 10. 実行手順

1. v1.2.5 notebookをcommit・pushする。
2. 可能なら実行前に二つの古いcommentだけ直す。ただし直すならsource SHAが変わるため、修正版をcommitしてから実行する。
3. fresh runtimeで`A10_MODE="smoke"`を設定しRun allする。
4. 末尾が：

```text
STATUS = SMOKE_PASS
required gates = 53 / 53
4 component status = True
```

であることを確認する。
5. 別のfresh runtime・fresh OUTで、追加セルのない純正notebookをofficial Run allする。
6. 末尾が：

```text
STATUS = A10_VALID
required gates = 60 / 60
```

であることを確認する。
7. 次を監査へ提出する。

```text
a10_provenance.json
checkpoints/ 全体
全セルのconsole log
```

特に確認対象：

```text
m decisionと5-bootstrap-seed verdict
float32 sensitivity evidence
A10c controls／conditional sensitivity
W₂ null values
exact-subset observed bounds
delta_q99_bound
decision_margin_ok_per_seed
output SHA
```

---

## 11. 最終判断

v1.2.5では、v1.2.4に残った：

```text
calibration自己比較
m helper引数逆転
dtype label逆転
full-pool boundの誤用
旧float32-primary provenance
chunk未binding
```

が解消した。

primaryのfloat64 Event B、m sensitivity、one-point calibration、3-position W₂の中心経路にも、新たな重大な問題は見つからない。

> **A10 v1.2.5：実行前監査PASS**  
> **SMOKE RUN：GO**  
> **SMOKE_PASS後のOFFICIAL RUN：GO**  
> **v1.2.6を先に作る必要：なし**  
> **rules v1.0／A10 freeze：official成果物の独立監査後に確定**

full frozen assetsを用いるColab officialは本監査環境では実行していない。最終的な`A10_VALID`、adopted m、calibration pathway結果、W₂ pathway判定は、official成果物を監査した後に確定する。
