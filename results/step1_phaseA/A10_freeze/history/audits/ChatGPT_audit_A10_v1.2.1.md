# ChatGPT監査：Step 1 Phase A-10 v1.2.1
**Claude伝達用 / 2026-09-12 / 実行前監査**

## 0. 総合判定

A10 v1.2.1は、v1.2監査で残っていた主要問題をほぼすべて正しく解消している。

確認できた主な改善は次のとおりである。

- mごとのfinite／precise／consistent／usableを分け、m=100が不適格でもm=10へfallbackできる
- W₂ checkpointをnotebook source、versions、threads、asset SHA、whitening、covariance rootsへbindingする
- negative controlのbootstrap valid fractionとfinite inventoryをrequiredにする
- W₂の個別3 pairに非有限値があれば停止し、全pair finite gateをrequiredにする
- `finite_pool_exceedance`という限定的な名称へ修正する
- checkpoint出力名をexact inventory化する
- 5 bootstrap seedのlogQ分布を保存する
- 日付と返送pathをv1.2.1へ修正する

静的検査と小規模合成試験では、前回の4 blockerが解消されていることを確認した。

ただし、現行sourceには二つの小さいが実在するformal false-pass pathが残る。

1. A10の`scan()`は、A8b childにあったselected score／T1／T2の非有限検査を省いている。NaNはEvent Bで自動的にFalseになるため、少数の非有限値がm判定を静かに下方へ偏らせ得る。
2. `G_cal_control_inventory`は、positive pseudo-controlについて長さと`loB`のfiniteしか検査せず、`QB`／`DB`のfinite・`DB>0`を検査しない。実装報告の「positiveもfinite・D>0」という説明とコードが一致しない。observed positive controlも`QBo=inf`／`DBo=inf`を許容する。

> **A10 v1.2.1 core design：APPROVED**  
> **前回4 blocker：PASS**  
> **現行sourceの正式official：HOLD（短い二修正を推奨）**  
> **推奨version：v1.2.2**  
> **v1.2.2後：SMOKE → OFFICIAL GO見込み**  
> **D(R)、Event B、m設計、W₂設計の根本的やり直し：不要**

現行v1.2.1は高い確率で正常実行する。しかし、上記二点は一行～数行で閉じられ、修正後はsource-only SHAが変わるため、現在のColab smokeを先に行うより、先に修正する方が証拠鎖・作業効率の両面でよい。

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
b4d7aa0d99f12b2d0eaa5d2cb888d6715dc707387f37a1fd434716622e6a5741

canonical source-only SHA256
952314c5c04cfb5b53b2fbe025db2127d707b79393352f936ed21e3c40c9dd09
```

実装報告の値と一致した。

---

## 2. 前回BLOCKER 1：m policyは解消

v1.2.1は、各mについて：

```text
finite
precise
consistent
usable = finite ∧ precise ∧ consistent
```

を別々に計算する。

decisionは：

```text
m10 usable ∧ m100 usable ∧ equivalence
    → m=100

m10 usable ∧ (m100 unusable ∨ equivalence未成立)
    → m=10

m10 unusable
    → unresolved
```

である。

official requiredは：

```text
G_m_run_inventory
G_m10_usable
G_m_decision_policy
G_m_decision_resolved
```

であり、`G_m100_usable=False`は診断として保存されるが、m=10採用時にはofficialを塞がない。

合成分岐試験：

```text
m10=True, m100=False, equivalence=False
→ adopted=10
→ policy=True

m10=True, m100=True, equivalence=False
→ adopted=10
→ policy=True

m10=True, m100=True, equivalence=True
→ adopted=100
→ policy=True

m10=False
→ adopted=None
→ policy=False
```

となった。

実装報告のsandbox smokeでも、m=100がprecision不適格、m=10がusableで、m=10 fallbackが成立したとされる。この分岐は現在のコードと整合する。

### 軽微な整理

cell A10bには`diff_ci`／`d1,d2,dpci`の計算が二重に残っている。

最初の計算は`allQ`を確認する前に走り、直後にguard付きの同じ計算で上書きされる。m100 Qがundefinedの場合、最初の`nanquantile`はall-NaN warningを発生させ得るが、global warning suppressionで隠れる。

最初の：

```python
def diff_ci(...):
...
d1, d2 = ...
dp = ...
dpci = ...
```

を削除し、`allQ`後のguard付き版だけを残すことを推奨する。結果は変わらない。

---

## 3. 前回BLOCKER 2：W₂ checkpoint bindingは解消

payloadには現在：

```text
NB_HEAD
NB_LIVE
versions
threads
全asset SHA
CFG
seed
adopted m
production spec
frozen asset commit
mu_c SHA
Sih SHA
S_POS SHA
S_I SHA
mode
n_sub
```

が入る。

checkpointはbinding hashだけでなくpayload自身も保存し、resume時に両方を照合する。

従って、notebook source、whitening、covariance rootsが変わった旧checkpointをcurrent resultとして再利用するv1.2の穴は閉じた。

### 強く推奨する追加binding

現payloadはpackage versionと登録thread数を含むが、次は含まない。

```text
platform / CPU model
actual THREADS_LIVE
BLAS implementation・version
今回生成したIND／CRN／TwIのarray SHA
```

fresh OUTから中断なく実行する場合は問題にならない。しかしColab切断後に別hardware／BLAS runtimeでresumeする正式用途では、A8bで確認されたfloat32 tie-breakのenvironment依存を考慮した方がよい。

最も強い方法は、W₂ input生成後に：

```python
IND_sha  = [asha(x) for x in IND]
CRN_sha  = [asha(x) for x in CRN]
TwI_sha  = asha(TwI)
```

をpayloadへ入れることである。これならplatform名に依存せず、W₂へ実際に渡す数値配列そのものへcheckpointがbindingされる。

これはfresh uninterrupted officialのscience blockerではないが、resumeをformalに安全にする強いhardeningである。

---

## 4. 前回BLOCKER 3：negative controlは解消

v1.2.1では：

```text
FRN.valid >= 0.95
QN finite
loN finite
DN finite
DN > 0
length = N_PSEUDO
```

がrequiredになる。

合成例として：

```text
FRN.valid = 0
loN = NaN
QN = NaN
DN = NaN
```

を与えると、`G_cal_negative_control`単体はsupport率0としてTrueになり得るが、

```text
G_cal_bootstrap_valid_fraction = False
G_cal_control_inventory        = False
```

となり、`CALIBRATION_PATH_VALID`は正しくFalseになる。

前回の「negative controlが計算不能でも偽support 0としてPASSする」経路は閉じた。

---

## 5. 前回FORMAL GAP：W₂全pair finiteは解消

`w2_exact()`は結果が非有限なら`FloatingPointError`を送出する。

さらに：

```text
null replicateの各3 pairを即時finite assert
primary independentの全seed・全3 pair
CRN diagnosticの全seed・全3 pair
```

を`G_w2_all_pair_values_finite`で検査する。

したがって：

```python
max([1.0, np.nan, 2.0]) == 2.0
```

のように、`W2_max`だけが有限となって一つのNaN pairを隠す経路は閉じた。

---

# 6. 【必須修正1】production scanに非有限outputのfail-fastがない

凍結A8b childは、各chunkで少なくとも：

```text
selected score
T1
T2
```

が有限であることを検査していた。

A10 v1.2.1の`scan()`は：

```python
Sp = f @ Fp.T
ax = Sp.argmin(1)
T1 = eval64(...)
T2 = eval64(...)
```

を行うが、finite checkがない。

### なぜ問題か

NumPy比較では：

```python
np.nan <= threshold
```

はFalseである。

従って、仮に百万標本のうち少数でT1／T2がNaNになっても：

```text
Event B = False
```

として静かに集計される。

その結果：

- P_M／P_I
- Q
- bootstrap CI
- m adoption
- calibration hit table

を小さく偏らせ得る。

m gateはpoint Qとhit countsを検査するが、raw T1／T2が全件finiteであることは検査しないため、この経路はformalには通り得る。

### 修正

```python
Sp = f @ Fp.T
ax = Sp.argmin(1).astype(np.int32)
sel = Sp[np.arange(len(x)), ax]

t1 = np.einsum(...)
t2 = np.einsum(...)

if not (
    np.isfinite(sel).all()
    and np.isfinite(t1).all()
    and np.isfinite(t2).all()
):
    raise FloatingPointError(
        "non-finite selection/evaluation output"
    )
```

としてから出力配列へ代入する。

これによりA8b production childのfail-fast semanticsまで再現できる。

追加のgateを作るより、`scan()`自体で例外にする方が全componentへ一括適用される。

---

# 7. 【必須修正2】positive-control inventoryが報告書どおりになっていない

実装報告は`G_cal_control_inventory`について、negativeおよびpositive controlの：

```text
length
finite
D > 0
```

を確認すると説明する。

しかし実際のpositive側は：

```python
len(QB) == len(loB) == len(DB) == N_PSEUDO
and np.all(np.isfinite(loB))
```

までしか検査しない。

次は検査されない。

```text
QB finite
DB finite
DB > 0
```

### 合成false-pass

```text
QN、loN、DN = 全て正常
QB           = 全てNaN
loB          = 全て1.0
DB           = 全てNaN
```

でも、現在の`G_cal_control_inventory=True`となる。

またobserved positive-control gateは：

```python
loBo finite
loBo >= 3
QBo >= 10
DBo > 1
```

なので、`QBo=inf`または`DBo=inf`でもPASSする。

### 修正

```python
GATES["G_cal_control_inventory"] = bool(
    len(QN) == len(loN) == len(DN)
        == CFG["N_PSEUDO"]
    and np.all(np.isfinite(QN))
    and np.all(np.isfinite(loN))
    and np.all(np.isfinite(DN))
    and np.all(DN > 0)

    and len(QB) == len(loB) == len(DB)
        == CFG["N_PSEUDO"]
    and np.all(np.isfinite(QB))
    and np.all(np.isfinite(loB))
    and np.all(np.isfinite(DB))
    and np.all(DB > 0)
)

GATES["G_cal_positive_control"] = bool(
    np.isfinite(QBo[0])
    and np.isfinite(loBo[0])
    and np.isfinite(DBo)
    and HIo.sum() > 0
    and loBo[0] >= 3
    and QBo[0] >= 10
    and DBo > 1
)
```

とする。

現実のobserved Event B denominatorは十分大きいと予想されるが、positive controlはまさにsupport pathの実装を検査するものなので、infinity／underflowによる偽PASSを明示的に排除すべきである。

---

# 8. W₂ finite-pool表現：PASS

v1.2.1は`mc_p`を：

```text
finite_pool_exceedance
```

へ改名し、一つの有限isotropic poolをre-permuteして使うためexact exchangeable Monte Carlo p-valueではないことを記録する。

この限定は適切である。

各null replicate内部では三つのcluster blockがdisjointであり、primary observedも三位置ごとに独立streamを使う。replicate間でfinite poolを再利用するため、最終threshold freezeではB増加・fresh null triplets・precision stoppingが必要だが、Phase A pathwayとしては現在の位置づけでよい。

---

# 9. gate inventory・status：PASS

独立に抽出したgateは56件である。

```text
REQ_A          34
REQ_B smoke     1
REQ_B official  4
REQ_C           6
REQ_D smoke     6
REQ_D official  9
final           2
```

従って：

```text
smoke    34 + 1 + 6 + 6 + 2 = 49
official 34 + 4 + 6 + 9 + 2 = 55
```

であり、実装報告と一致する。

`G_m100_usable`はinventoryには含まれるが、m=10採用時にはrequiredではない。したがって、全56 diagnostic gatesがTrueでなくても、required 49／55のexact statusが成立する設計である。この点はprovenanceに明示しておくこと。

---

# 10. smokeの位置づけ

実装報告はsandbox smokeで：

```text
SMOKE_PASS 49/49
m100 precise=False
m10 usable
adopted m=10
```

と報告する。

コード上、このfallback経路は現在本当に到達可能である。

ただし、今回添付されたのはnotebookと実装報告であり、sandbox smokeのraw provenance／checkpoints／console logは添付されていない。そのため、49/49という実行結果自体は本監査ではbytesから独立再集計していない。

---

# 11. 非blockerの推奨

## 11.1 A10固有のf32/f64 sensitivity

m runではmodel側について：

```text
axis flip fraction
all flips antipodal
Event B identical
```

を保存する。

isotropic側とT1／T2最大差も保存すると、A8a／A8bの一般的なvalidationに加え、A10の実際の100万標本でもselected-output equivalenceを確認できる。

## 11.2 bootstrap equivalenceの5-seed感度

precisionは5 bootstrap seedのCI-width CVを使う一方、m10対m100のequivalence CIはseed0のdistributionだけを使う。

固定seedのprospective ruleとしては再現可能であるが、official結果が±log(1.10)境界に近い場合、5 seed全てでequivalence verdictが同じかをdiagnosticに追加するとよい。

## 11.3 W₂ checkpointの細粒度

checkpointはn_sub単位である。B=200 nullの途中で切断すると、そのn_sub全体を再計算する。

null replicate block単位のcheckpointは科学的に必須ではないが、Colab切断対策として有用である。

---

# 12. 最終判断

A10 v1.2.1は、前回指摘した主要blockerを正しく修正している。とくに：

```text
m=10 fallback
negative-control fail-closed
W₂ source／whitening binding
全pair finite
finite-pool exceedance表現
exact output inventory
```

はPASSである。

一方、officialを正式なrules v1.0 draftの根拠にするなら：

1. scan outputのfinite fail-fast
2. positive-controlのfull finite／D>0 inventory

という二つの短い修正を先に入れるべきである。

> **A10 v1.2.1 CORE：APPROVED**  
> **現行sourceの正式official：HOLD**  
> **v1.2.2へ二点修正後：SMOKE → OFFICIAL GO**  
> **研究設計の根本的変更：不要**

full frozen assetsを用いるColab officialは本監査環境では実行していない。監査範囲は、notebook全source、source-only SHA、compile、gate inventory、m policy合成分岐、negative-control合成反例、W₂ checkpoint／pair finite logic、positive-control false-pass counterexampleである。
