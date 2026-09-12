# ChatGPT監査：Step 1 Phase A-10 v1.2
**Claude伝達用 / 2026-09-11**

## 0. 総合判定

A10 v1.2は、v1.1監査で指摘した主要な科学的・実装上の回帰をほぼすべて適切に修正している。

特に次はPASSである。

- A5凍結Event Bの復元
- pseudo observationごとの二次元閾値
- A8bと同じfloat32 selection丸め順＋float64 evaluation
- m=10／100のpractical-equivalence設計
- 3 observer positionsのmax-pairwise W₂
- independent-stream primaryとCRN diagnosticの分離
- A5／A8／A9／A11へのSHA binding
- live notebook／BLAS thread hard gate
- atomic NPZ／JSON
- component別statusとfinal assert

しかし、現行sourceのままofficialへ進めるには、短いながら重要な残件がある。

1. m=10 fallbackは、`G_m_two_rep_consistency`と`G_m_all_Q_finite`が全mへ無条件適用されるため、m=100側の不調時に依然として塞がれ得る。
2. W₂ resume checkpointのbindingに、実行notebook source、environment、whitening、covariance rootsが含まれず、source変更後のstale checkpointを受理し得る。
3. calibration negative controlのbootstrap valid fraction／finite inventoryがhard gateされず、undefinedなnegative controlでも「support率0」としてPASSし得る。
4. W₂は`W2_max`だけをfinite検査し、個々のpairwise W₂のNaNを隠し得る。

> **A10 v1.2 SCIENCE／ENGINE CORE：PASS**  
> **v1.1監査の主要15項目：大部分PASS**  
> **現行v1.2 OFFICIAL：HOLD**  
> **短いv1.2.1またはv1.3修正後：SMOKE GO**  
> **D(R)、quadratic scan、Event B、W₂設計の根本的作り直し：不要**

---

## 1. 静的検査

```text
notebook cells                 7
code cells                     5
全code cell AST parse          PASS
全code cell compile            PASS
gate inventory                 54
required smoke                 48
required official              53
```

独立SHA：

```text
notebook file SHA256
93b15891dd8104cb8b987ef9efa167fbb234f714e20d43ff365f8b630f614565

canonical source-only SHA256
35cad3de9c3e6380e5db3ca25967f2a224a4cb878db802ba57848f527950a27d
```

実装報告の値と一致する。

---

# 2. 正しく修正された部分

## 2.1 A8b production kernel

A10 v1.2は、

```text
x64
→ x32 = x64.astype(float32)
→ x32_i × x32_jをfloat32で生成
→ float32 GEMM
→ argmin
→ 元のx64とfloat64 B±でT1／T2評価
```

を実装している。

凍結A8b v1.1.8のCPU child sourceを別に抽出して比較したところ、`cast`、`packed_into`、`l24_feature231` selection、`eval64`の演算順は一致した。

3072個のPSD axis matrixを用いる小規模試験でも、A10 scanとA8b formulaについて、float32／float64 selectionの双方でargmin・T1・T2が一致した。

## 2.2 Event Bとpseudo threshold

primary eventは、

```text
T1 <= T1_obs
AND
T2 <= T2_obs
```

へ戻っている。

`hit_table_2d()`もpseudo observationごとに、

```text
T1 <= T1_pseudo[p]
AND
T2 <= T2_pseudo[p]
```

を数える。v1.0のcentral band回帰は解消した。

## 2.3 bootstrap分子0

calibrationの`q_lower_ci()`は、

```text
分母>0・分子=0       Q=0
分母=0・分子>0       Q=+inf
分母=0・分子=0       undefined
```

を正しく区別する。

100 cluster中1 clusterだけmodel hitを持つ合成例で、現コードの2.5% lower quantileは正しく0となった。

## 2.4 matched covariance／square root／basis

3 observer positionsすべてについて、

```text
PR3 power matching
raw lambda_min > 0
clip = 0
sqrt symmetry
sqrt reconstruction
```

を検査する。

A9 provenanceのM21／LM／real-basis／quadrature nodes／weightsへのbinding、A11 complex covarianceからreal covarianceへの変換gateも実装されている。

## 2.5 W₂ pathway

primaryは3位置ごとに独立`(R,z)` streamを使い、CRN版をsecondary diagnosticへ分けた。3 pairのmaxを統計量とし、n_sub 2000／5000、3 subsample seeds、decision consistency、seed spreadをofficial gateにしている。

これはv1.1より明確に改善している。

---

# 3. 【BLOCKER 1】m=10 fallbackがなお一部塞がれる

現decisionは、

```text
m=100が不適格／非等価
m=10が適格
→ m=10を採用
```

を意図する。

`G_m_precision_policy`はこの意図どおりに直った。

しかし`REQ_B`には、

```python
G_m_two_rep_consistency
```

が無条件に入る。このgateはm=10だけでなくm=100のreplicate consistencyも同時に要求する。

### 合成反例

```text
m10：2 repとも精密・consistent
m100：impreciseかつrep間でinconsistent
```

なら、

```text
adopted_m                 10
G_m_precision_policy      True
G_m_two_rep_consistency   False
M_SENSITIVITY_RESOLVED    False
```

となる。

つまり「m100が不安定なので安全側のm10へfallback」というpolicyが、m100 inconsistency gateによって停止する。

同様に`G_m_all_Q_finite`も4 runすべてへ無条件適用されるため、m100側のQがundefinedなら、m10が十分良好でもfallbackできない。

## 修正案

mごとのusable statusを分ける。

```python
m10_finite = all(
    MS[f"m10_rep{r}"]["logQ"] is not None
    for r in REPS
)

m100_finite = all(
    MS[f"m100_rep{r}"]["logQ"] is not None
    for r in REPS
)

m10_consistent = ...
m100_consistent = ...

m10_usable = m10_finite and m10_ok and m10_consistent
m100_usable = m100_finite and m100_ok and m100_consistent

if m10_usable and m100_usable and equiv:
    adopted = 100
elif m10_usable:
    adopted = 10
else:
    adopted = None
```

required gateも、

```text
G_m10_usable
G_m_decision_policy
G_m_decision_resolved
```

へpolicy-awareにする。

m100のfinite／precision／consistencyは診断として必ず保存し、m=100を採用するときだけrequiredにする。

---

# 4. practical-equivalence margin 10%の位置づけ

`DELTA_M = log(1.10)`をofficial前に固定したこと自体は良い。

ただし10%は数学から自動的に決まる値ではなく、科学的・engineering上の許容誤差である。rules v1.0 draftでは、少なくとも次を一文で説明する。

> orientation clusteringをm=100へ粗くしても、support ratio Qのmultiplicative discrepancyが10%以内なら、Phase AのMonte Carlo設計差として許容する。

Q=3／10というdecision threshold近傍でも10%差は判定を変え得るため、将来のfull gridでは、threshold crossingを起こさないことも併記するとさらに安全である。

これはcode blockerではないが、「pre-registered」の根拠として明文化が必要である。

---

# 5. 【BLOCKER 2】W₂ checkpoint bindingがsource／numerical inputsを固定しない

現checkpoint bindingは、

```text
CFG
MASTER_SEED
m
MT_COMMIT
PROD
mode
```

から作られる。

しかし`MT_COMMIT`はA8 freeze asset commitであり、実行中のA10 v1.2 notebook commit／source-only SHAではない。

従って、A10 notebookを変更しても、次が同じならbindingは変わらない。

```text
CFG
seed
adopted m
A8 asset commit
production metadata
mode
```

古い`a10d_w2_nsub*.json`が同じOUT directoryに残っていると、新sourceのofficial runがそれをresumeし得る。

さらにbindingには、

```text
Python／NumPy／POT／BLAS
NB_HEAD／NB_LIVE
asset SHA
mu_c／Sih whitening
S_POS square-root matrices
```

も含まれない。

特にwhiteningまたはcovariance-root codeが変わった場合、旧W₂をcurrent resultとして再利用し得る。

## 修正案

```python
W2_BIND_PAYLOAD = dict(
    notebook_source=NB_HEAD,
    live_source=NB_LIVE,
    versions=VERS,
    threads=THREADS,
    asset_sha=ASSET_SHA,
    config=CFG,
    seed=MASTER_SEED,
    adopted_m=m_w2,
    production=PROD,
    mu_c_sha=asha(mu_c),
    Sih_sha=asha(Sih),
    S_POS_sha=[asha(S) for S in S_POS],
    mode=A10_MODE,
)

BIND = hashlib.sha256(
    json.dumps(
        W2_BIND_PAYLOAD,
        sort_keys=True,
    ).encode()
).hexdigest()
```

checkpointにはhashだけでなくpayloadも保存し、resume時に両方を比較する。

また初回official前には`a10_v1.2_official/`をfresh directoryにする。source修正後はversionまたはOUT名を変える。

---

# 6. 【BLOCKER 3】negative controlのinvalid bootstrapがgateされない

main、positive pseudo、positive observedについてはvalid fractionを検査する。

しかしnegative controlの`FRN`は、

```python
G_cal_bootstrap_valid_fraction
```

に含まれない。

またnegative controlの`QN`、`loN`、`DN`に対するfinite／length inventoryもない。

### 合成反例

```text
FRN.valid = 0
loN       = NaN
```

なら、

```python
neg_support = (loN >= 3) & (...)
```

はFalseになり、

```text
negative support rate = 0
G_cal_negative_control = True
```

となる。

すなわちnegative controlが計算不能でも、「偽supportなし」としてPASSし得る。

## 修正案

```python
GATES["G_cal_bootstrap_valid_fraction"] = bool(
    np.all(FR["valid"] >= 0.95)
    and np.all(FRN["valid"] >= 0.95)
    and np.all(FRB["valid"] >= 0.95)
    and FRBo["valid"][0] >= 0.95
)

GATES["G_cal_control_inventory"] = bool(
    len(QN) == len(loN) == len(DN) == CFG["N_PSEUDO"]
    and np.all(np.isfinite(QN))
    and np.all(np.isfinite(loN))
    and np.all(np.isfinite(DN))
    and np.all(DN > 0)
)
```

`G_cal_control_inventory`を`REQ_C`へ加える。

---

# 7. 【FORMAL GAP】W₂の個別pair値をfinite検査していない

`G_w2_observed_finite`が見るのは`W2_max`だけである。

Pythonの`max`は、NaNが途中の要素にある場合、他のfinite値を返すことがある。

合成例：

```python
max([1.0, np.nan, 2.0]) == 2.0
```

従って、例えばP1P3がNaNでもW2_maxがfiniteとなり、現gateが通り得る。

## 修正案

`w2_exact`または`pairs3`でfail-fastする。

```python
def w2_exact(a, b):
    ...
    out = float(np.sqrt(v))
    if not np.isfinite(out):
        raise FloatingPointError(
            "non-finite W2"
        )
    return out, warning
```

加えて、

```python
GATES["G_w2_all_pair_values_finite"] = all(
    np.isfinite(list(
        W2[k][path]["observed"][seed]["pairwise"].values()
    )).all()
    for ...
)
```

をrequiredへ入れる。

null側も各replicateの3 pairをその場でfinite assertする。

---

# 8. W₂ MC pの表現

primary observedと各null replicateは、1 replicate内では独立3 sampleという構造へそろった。この修正は妥当である。

ただし200 null replicateは、一つの有限isotropic poolを再shuffleして繰り返し利用する。このためnull statistics同士は独立ではなく、observed statisticを含むB+1個のexact exchangeabilityも成立しない。

従って、

```text
MC p
```

は、Phase Aでは、

```text
finite-pool Monte Carlo exceedance estimate
```

または、

```text
empirical null exceedance fraction with +1 correction
```

と呼ぶ方が正確である。

現コードもB=200 q99が粗くfinal thresholdではないと明記しているため、この点は実行停止blockerとはしない。最終trigger freezeでは、独立null tripletsまたはprecision stoppingへ進む必要がある。

---

# 9. W₂ stability gate：概ねPASS、二つ補強

次は適切である。

```text
3 subsample seedsのdecision一致
n_sub 2000／5000のdecision一致
W2_max seed spread <= 0.25
```

補強：

1. 個別3 pairのfinite gateを追加する。
2. checkpoint bindingをsource／whiteningへ結ぶ。

なお`emd_warnings`はn_sub間で累積保存される。warningが0なら影響しないが、checkpoint resume時にdouble-countし得るため、`warn_nsub`と`warn_total`を分ける方が明瞭である。

---

# 10. archive／provenance上の軽微な点

## 10.1 output directory exact inventory

final `outputs`はCKPT directory内の全fileをhashする。過去のstale fileが残っていても含まれる。

expected filename inventoryを固定するか、fresh OUTを要求する。

## 10.2 m bootstrap 5-seed evidence

`CI_width_CV_5seeds`は5個のbootstrap distributionから計算するが、NPZへ保存するのは各runのfirst bootstrap distributionだけである。

cluster hitsとseedから再生成可能だが、formal archiveでは5 distributionsまたは5 CI widthsを保存すると再監査しやすい。

## 10.3 文書上のパス

最終markdownは返送先を、

```text
a10_v1.1_{smoke,official}/
```

と書いている。

正しくは、

```text
a10_v1.2_{smoke,official}/
```

である。

## 10.4 日付

notebook／実装報告の見出しは`2026-09-13`だが、本監査時点は`2026-09-11`である。

practical-equivalence margin等を「official前の事前登録」と位置づけるため、見出しは実際の作成日／commit日に直し、Git commit時刻をsource of truthにする。

---

# 11. 推奨するv1.2.1の最短修正

1. mごとのfinite／precision／consistencyを分けたpolicy gate
2. W₂ checkpoint bindingへNB source・environment・asset・whitening・S_POS SHAを追加
3. negative controlのvalid fraction／finite inventory gate
4. W₂全pair finite assert／gate
5. 最終markdownのv1.1 pathをv1.2へ修正
6. 見出し日を実際の日付へ修正

追加で望ましいもの：

- 10% equivalence marginの科学的説明
- finite-pool MC exceedanceという用語
- exact CKPT output inventory
- 5 bootstrap-seed evidenceの保存

---

## 12. 最終判断

A10 v1.2は、v1.0／v1.1に比べて大幅に完成へ近づいた。

Event B、A8b exact kernel、2D pseudo threshold、practical-equivalence、3-position W₂、A9/A11 bindingの中心設計は承認できる。

しかし、m fallbackのpolicy contradiction、stale W₂ checkpoint、negative-control invalid passはofficial resultを誤って承認し得るため、現行sourceのまま長時間officialを実行することにはGOを出さない。

> **A10 v1.2 CORE：APPROVED**  
> **現行v1.2 OFFICIAL：HOLD**  
> **v1.2.1短修正後：SMOKE → OFFICIAL GO見込み**  
> **研究設計の根本的やり直し：不要**

full frozen assetsを用いるColab officialは本監査環境では実行していない。監査範囲は全source、compile、gate inventory、凍結A8b childとのコード比較、small synthetic regression、m policy、bootstrap、W₂ checkpoint／finite logicである。
