# ChatGPT最終監査：Step 1 Phase A-10 v1.2.9
## smoke／official成果物・checkpoint・独立再計算
**2026-09-12／Claude伝達用**

## 0. 総合判定

受領した `A10_results.zip` を二重ZIPまで展開し、smoke／officialのprovenance、console log、全checkpoint JSON／NPZ、SHA相互参照、gate inventory、m感度、較正経路、W₂ null配列、float32感度evidenceを独立に検査した。

結論は以下である。

> **A10 v1.2.9 smoke：SMOKE_PASS（54/54）**  
> **A10 v1.2.9 official：A10_VALID（61/61、4 componentすべてTrue）**  
> **A10 engine／m感度／one-point calibration pathway／W₂ pathway：freeze GO**  
> **m=100採用：GO**  
> **ℓ=2–4 float64 primary・S2 float32というrules案：GO**  
> **official再実行：不要**

ただし、A10cは一地点・一系統の較正経路prototypeであり、familywise global calibrationではない。またA10dの3位置はregistered p^(3)ではないmockで、B=200のq99は粗い。したがって、A10のfreezeは「Phase A設計・実装・推定量選択」のfreezeであり、global false-support率や最終W₂ trigger閾値の科学的freezeではない。

---

## 1. 受領物の健全性

```text
A10_results.zip
size    36,488,724 bytes
SHA256  be6b36d0867a65f7aba499c03b930fd476dd27b4b45feb979b72d2e4886681c4
unzip -t  PASS
```

内側のsmoke／official checkpoint ZIPもCRC検査を通過した。

```text
official checkpoint ZIP SHA256
2e3f824109f3d1e0b6c7647f892f5d63a2d2afd1781e0338baa5b3fea7aa66b2

smoke checkpoint ZIP SHA256
c52c7a9dcd473a165259cbdcd7dfd7f8e2f263a883e52c013b136325da9d3edc
```

JSONにduplicate keyはない。console logには`Traceback`、`AssertionError`、`Exception`、`ERROR`、`Warning`はない。

Claudeの独立検算報告は同じ内容の2ファイルが添付されていたが、bytes／SHAは完全同一である。

---

## 2. status・gate・source identity

### smoke

```text
status                  SMOKE_PASS
required gates          54 / 54
component status        4 / 4 True
required false gates    0
```

### official

```text
status                  A10_VALID
required gates          61 / 61
component status        ENGINE_VALID=True
                        M_SENSITIVITY_RESOLVED=True
                        CALIBRATION_PATH_VALID=True
                        W2_PATHWAY_VALID=True
required false gates    0
```

officialのprovenance SHA：

```text
bf5deec02568fa5c6a0ef42dc8d9d66f51278e67a39fe9ca2dc8d1a069f801f7
```

smokeのprovenance SHA：

```text
a2a5fcae64e20f403306cc19e1cebcd15c01ba1894887350223513bc313ac719
```

official notebook identity：

```text
head_copy source-only SHA
731cb898c777d909c1d310e66731dcb78aeb1caefbf1be5582eaf0a3c97eb0a0

live source-only SHA
731cb898c777d909c1d310e66731dcb78aeb1caefbf1be5582eaf0a3c97eb0a0
```

受領したnotebook file SHA：

```text
c11c41413e33754444118401c8c102b69ca430650619d409bef568f94bba1209
```

期待environmentは完全一致した。

```text
Python  3.13.15
NumPy   2.1.3
SciPy   1.16.3
healpy  1.20.0
POT     0.9.7.post1
```

NumPy GEMM poolはOpenBLAS 0.3.27・2 threadsで、他のBLAS poolも2以下だった。

診断gateのFalseは次の2件だけで、いずれも設計どおりrequiredではない。

```text
G_a9_quadrature_hashes
  NumPy版依存のbit hash。数学的Gauss–Legendre exactness等のrequired gateはPASS。

G_m_f32_f64_no_nonantipodal_flip
  float32 sensitivityで非対蹠near-tie flipが実測されたためFalse。
  primaryはfloat64なのでstatusを落とさず、むしろdtype選択の根拠となる。
```

---

## 3. output inventoryとSHA chain

smoke／officialとも、provenanceに登録されたcheckpoint filename集合と実ファイル集合が完全一致した。

officialの11出力について、実bytesのSHA256はprovenanceの`outputs`記録と全て一致した。

```text
a10a_calibration.npz
a10b_cluster_hits.npz
a10b_flip_evidence.npz
a10b_axes.npz
a10b_m_sensitivity.json
a10c_pathway.npz
a10c_pathway.json
a10d_w2.npz
a10d_w2.json
a10d_w2_nsub2000.json
a10d_w2_nsub5000.json
```

checkpoint JSONの内容とprovenanceの対応sectionも完全一致した。

```text
a10b_m_sensitivity.json == provenance.m_sensitivity
a10c_pathway.json       == provenance.calibration_pathway
a10d_w2.json            == provenance.w2
```

---

## 4. smoke→official再現性

smokeのcalibration 20,000標本は、official 200,000標本の先頭20,000と以下の全arrayでbit identicalだった。

```text
T1 / T2
AX / plane label / cluster id
T1・T2・AXのfloat32-selection sensitivity path
```

4つのm runについても、smokeの20,000標本のaxis arraysはofficialの先頭20,000とbit identicalであり、cluster hit arraysもofficialの先頭cluster部分と一致した。

これは、modeによる縮小以外に乱数列・数値経路が変わっていないことの強い確認である。

---

## 5. A10a engine

official calibration NPZから独立に再計算した。

```text
N                         200,000
T1 median                 120.4342200
T2 median                 609.2605731
P(T1 <= observed)         0.014875
P(Event B)                0.003665
T2 q16 / q84              381.9753 / 952.4910
```

A5 map-based null：

```text
T1 median                 118.460
bootstrap 95% CI          [115.424, 122.772]

T2 median                 593.000
bootstrap 95% CI          [571.398, 617.987]

P(T1 <= observed)         0.0150
Wilson 95%                [0.00911, 0.02460]

P(Event B)                0.0040
Wilson 95%                [0.00156, 0.01024]
```

A10 map-free engineの値は全てA5の対応範囲内である。

calibrationのfloat32 sensitivity：

```text
axis flips                1,726 / 200,000 = 0.00863
全flip                    exact antipode
Event B mismatch          0
max T1 relative diff      6.55e-7
max T2 relative diff      2.11e-3
```

保存されたflip index・axis・T1/T2・Event B evidenceはfull arraysと一致した。

> **ENGINE_VALIDを承認する。**

---

## 6. A10b m感度

cluster hit arraysから独立にQを再計算し、保存済みbootstrap seed0分布からCIを再計算した。

| run | Q | 95% CI | Event-positive clusters M/I |
|---|---:|---:|---:|
| m10_rep1 | 1.346480 | [1.308472, 1.383255] | 4808 / 3591 |
| m10_rep2 | 1.299406 | [1.265767, 1.337057] | 4705 / 3624 |
| m100_rep1 | 1.330454 | [1.292717, 1.366152] | 3915 / 3111 |
| m100_rep2 | 1.304394 | [1.268404, 1.340496] | 3861 / 3089 |

provenanceと完全一致した。

5 bootstrap seedそれぞれについて、m100−m10のdifference CIを再計算した。rep1、rep2、pooledの全CIが、全5 seedで事前登録幅：

```text
±log(1.10) = ±0.09531018
```

の内側に収まった。

seed0のCI：

```text
rep1    [-0.050141,  0.028152]
rep2    [-0.036160,  0.042972]
pooled  [-0.032743,  0.024417]
```

従って：

```text
m=10 usable     True
m=100 usable    True
practical equivalence  True
5-seed verdict         [True, True, True, True, True]
adopted m              100
```

は妥当である。

### float32 sensitivity evidence

全8,000,000標本を横断すると：

```text
raw axis flip occurrences     69,426
exact antipode                69,394
non-antipodal                 32
Event B mismatch              0
Q difference                 0（4 run全て）
```

非対蹠flipの最大plane-folded角距離：

```text
84.98 degrees
```

次点：

```text
59.42 degrees
```

対応するT2相対差は約14.2%・11.5%だったが、Event Bは不変だった。

これは、ℓ=2–4をfloat64 primaryへ変更した判断を実データで強く支持する。一方、S2でfloat32を維持するrulesでは、raw axisを一意な物理推定値とみなさず、near-minimizer／plane-folded semanticsとselected representative依存のT2を明記する必要がある。

> **m=100採用を承認する。**

---

## 7. A10c one-point calibration pathway

NPZからsupportを独立に再構成した。

```text
support = (Q lower CI >= 3) AND (logD > 0)
```

結果：

```text
main false support           0 / 200
Wilson upper 95%             0.018845
negative control support     0 / 200
positive pseudo support      30 / 200 = 0.15
Q_pseudo median              1.051195
negative Q median            0.999853
```

positive control・observed threshold：

```text
Q                            97.9114
Q lower CI                   94.9703
logD                         2.86709
D                            17.5858
```

全main／negative／positive logD arrayはfiniteであり、positive pseudo logDの最小値は：

```text
-771.735
```

だった。これはv1.2.8でordinary pdfが0へunderflowした領域であり、v1.2.9のlogpdf差への変更が意図どおり機能している。

float32 conditional sensitivity：

```text
support array mismatch       0
changed hit-table cells      model 7 / isotropic 16
max |delta logQ|             1.67e-4
max |delta logD|             5.70e-6
```

> **CALIBRATION_PATH_VALIDを承認する。**

ただし、この結果は：

```text
one point
one system
n_pseudo = 200
```

のpathway prototypeである。familywise global calibration、全family prior integration、最終false-support保証ではない。

---

## 8. A10d W₂ pathway

official null arraysから、method=`higher`のq99、q95、median、maxを独立再計算し、JSONと一致した。

### n_sub = 2,000

```text
observed W2_max          0.224125 / 0.212249 / 0.200544
null q99                 0.236419
null q95                 0.216483
null median              0.182183
finite-pool exceedance   0.01493 / 0.07463 / 0.17910
decision above q99       False / False / False
delta_q99 bound          0.003495
decision margin residual 0.00880 / 0.02067 / 0.03238
```

### n_sub = 5,000

```text
observed W2_max          0.134808 / 0.152710 / 0.148731
null q99                 0.164714
null q95                 0.143655
null median              0.127262
finite-pool exceedance   0.20896 / 0.01990 / 0.02985
decision above q99       False / False / False
delta_q99 bound          0.002242
decision margin residual 0.02766 / 0.00976 / 0.01374
```

全3 seed・両n_subでq99未満という判定が一致する。seed spreadは：

```text
n_sub 2000   0.1176
n_sub 5000   0.1328
```

で、事前登録上限0.25以内である。

全pairwise W₂はfinite、POT warningは0、null lengthは各200だった。

> **W2_PATHWAY_VALIDを承認する。**

ただし：

- 3位置はregistered p^(3)ではなくmockである。
- B=200の99%点は粗い。
- finite-pool exceedanceはexact exchangeable Monte Carlo p-valueではない。
- 最終trigger thresholdはB増加またはprecision stoppingを要する。

したがって、「3位置差が科学的に存在しない」ではなく、「このmock／このPhase A設定では99% triggerが発動せず、推定量・null構成が動作した」と解釈する。

### archive上の小さな制限

各null replicateのselection perturbation bound配列そのものは保存されず、`delta_q99_bound`とmedianだけが保存されている。required gateはsource／seed／input bindingの下で再現可能だが、凍結packetだけから`max(null_bound)`を直接再集計することはできない。

これは今回のGOを妨げないが、将来版ではper-replicate null bound arrayもNPZへ保存すると第三者監査性がさらに高まる。

---

## 9. Claude独立検算報告の評価

Claude報告の科学的・数値的な主要結論は、raw成果物と整合する。

特に以下は正しい。

```text
smoke 54/54
official 61/61
m=100採用
one-point false support 0/200
negative control 0/200
positive control発動
W2は全seed・両n_subでq99未満
float32で32件の非対蹠flip
```

軽微な修正点：

### 計算時間

報告は：

```text
W2 n_sub=2000 約12分
W2 n_sub=5000 約97分
official全体 約2時間
```

としているが、consoleの実測は：

```text
n_sub=2000  337 s  = 5.6分
n_sub=5000  2581 s = 43.0分
W2 pool生成 125.5 s
4 m runs合計 約700 s
```

である。主要計算の合計は約63分＋setupであり、少なくともconsole記録上は12分／97分ではない。これは結果の正しさに影響しないが、最終報告では訂正する。

### bootstrap独立再計算

Claude報告の「独立bootstrap再構成」はprovenanceと近いが僅かな差を持つ。一方、freeze成果物に保存された5 seed bootstrap arraysからの再計算は、provenanceのCIとbit-levelで一致した。この点を最終報告では明確にするとよい。

---

## 10. freeze／rules判定

### A10 freeze

> **GO**

freeze bundleには以下を含める。

```text
MirrorTopology_Step1_A10_v1.2.9.ipynb
smoke/
  a10_provenance.json
  checkpoints/
  console log
official/
  a10_provenance.json
  checkpoints/
  console log
v1.2.8 FAILED provenance／console（履歴）
v1.2.5–v1.2.9 implementation reports
Claude independent report
ChatGPT official audit
freeze_manifest.json（relative path / size / SHA256）
```

### rules v1.0 draftへ転記可能

```text
orientation cluster m      100
ℓ=2–4 selection            float64
ℓ=2–4 evaluation           float64
ℓ=2–4 feature route        l24_feature231
float64 chunk              2,000
S2 selection               float32
S2 evaluation              float64
calibration implementation 2D pseudo thresholds、再走査なしhit table、
                           paired cluster bootstrap、log-density ratio
W2 estimator               whitened 2D exact W2、3-position max-pairwise、
                           independent-stream primary、CRN diagnostic
```

ただしrules文には明記する。

```text
A10cはone-point pathway prototypeでありfamilywise global calibrationではない。
A10dの3位置はmockでありregistered p^(3)ではない。
W2 B=200のq99は最終閾値ではない。
float32 axisは遠い非対蹠near-tieへ移ることがあるため、
axis semanticsとrepresentative-dependent T2を明示する。
```

---

## 11. 最終判定

| 項目 | 判定 |
|---|---|
| ZIP／inner ZIP integrity | PASS |
| JSON duplicate key | なし |
| smoke status | PASS |
| official status | **A10_VALID** |
| official required gates | **61 / 61** |
| 4 component status | 全True |
| source／environment binding | PASS |
| output inventory／SHA | PASS |
| smoke→official prefix reproduction | PASS |
| engine vs A5 | PASS |
| m decision | **m=100 GO** |
| calibration pathway | PASS（one-point prototype） |
| W2 pathway | PASS（mock／coarse threshold caveat） |
| rerun | **不要** |
| A10 Phase A freeze | **GO** |
| final global calibration／W2 threshold | **未freeze** |

