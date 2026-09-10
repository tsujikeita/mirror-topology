# ChatGPT最終監査：Step 1 Phase A-8a / A-8b
## A8a v1.1.2 FEATURESTACK_VALID・A8b v1.1.8 BENCHMARK_VALID
**Claude伝達用 / 2026-09-10**

## 0. 総合判定

今回受領した `A8a_results.zip` と `A8b_results.zip` を展開し、ZIP整合性、JSON構文、gate inventory、console log、CSV、manifest、provenance、canonical audit NPZ、timed audit NPZ、index JSON、evidence JSONL、SHA相互参照を独立に検査した。

結論は以下である。

> **A8a v1.1.2 smoke：PASS**  
> **A8a v1.1.2 official：FEATURESTACK_VALID・49/49 gates PASS**  
> **A8a F16 feature stack：科学的freeze GO**  
> **A8b v1.1.8 smoke：SMOKE_PASS・35/35 gates PASS**  
> **A8b v1.1.8 official：BENCHMARK_VALID・35/35 gates PASS**  
> **A8b engineering rules recommendation：採用GO**  
> **A8b再実行：不要**  
> **S2の科学的採用：登録どおりS4／exact validation完了までHOLD**

A8b officialにはS2 float64 winner 1件の`timeout`があるが、これは登録済みのclassified-ineligible outcomeであり、全体の異常終了ではない。float32経路はA8aおよびA8bのcross-dtype batteryを通過し、最終S2 routeはfloat32 selection／float64 evaluationで確定しているため、engineering decisionを無効にしない。

---

## 1. 受領ZIPの健全性

```text
A8a_results.zip
size    130,253 bytes
SHA256  a3e63faf7f747ade9c2896945f4120dfd09536a2843ef533fcade4c18969bb86
unzip -t  PASS

A8b_results.zip
size    16,129,244 bytes
SHA256  e10b6569a54b93f800809dd0261786d4edd710fe00023f2987328f8898041df4
unzip -t  PASS
```

両ZIPともCRC error、破損、展開失敗はない。

JSONについてduplicate keyは検出されず、CSVには意図しない重複列・重複caseはない。console logにTraceback、AssertionError、Exception、ERROR、Warningはない。

---

# 2. A8a v1.1.2

## 2.1 status・gate

### smoke

```text
status                 SMOKE_PASS
FEATURESTACK_VALID     False
gate inventory         exact
required gates         47
true gates             47
false gates            0
validation rows        70
```

### official

```text
status                 FEATURESTACK_VALID
FEATURESTACK_VALID     True
gate inventory         exact
required gates         49
true gates             49
false gates            0
validation rows        1,210
console terminal       STATUS = FEATURESTACK_VALID
```

official notebook identity：

```text
live source-only       7fe775f970c3485add5f7181a2f32e681af1feb369e8181168cb67b418d0285d
origin/main copy       7fe775f970c3485add5f7181a2f32e681af1feb369e8181168cb67b418d0285d
```

smoke provenance chainは、path、SHA、status、全required gates、canonical source、environment fingerprintの全項目でPASSしている。

## 2.2 F16 build

```text
shape                   (3072, 40,755)
float64 size            1.00159488 GB
float32 size            0.50079744 GB
total                    1.50239232 GB
official build time     71.5412 s
low-l block max diff    5.5511e-17
symmetry residual max   1.8052e-17
sampled PSD minimum     5.1312e-16
```

smokeとofficialで、F16 float64／float32のarray SHAおよびfile SHAは完全に同一である。

```text
F16 float64 array SHA
4feac2669642c895e9c1391867b8d0dccd85a0abf3f04fec074ae8ab5af345f6

F16 float32 array SHA
a0281b4fec848623c14b2bef7d0689da6a07083bcb0d8c553075ef0d2094dd9a

F16 float64 file SHA
aca84c5f39e4b35eccfc01c328874fdef053a09084fe689efa0d4e7b2d0728f1

F16 float32 file SHA
9e433de0742c495068facea43509da1104567ecf9b27c8804c96f86c343ec8a9
```

今回のA8a ZIPには1.5 GBの二つの`.npy`本体は入っていないため、ChatGPT側でそのbytesを直接再hashしてはいない。ただしA8b officialは、この四つのfile／array SHAを実際にload前後で再検査し、`G_F16_file_sha`および`G_F16_array_sha_local`を通している。A8a manifestとA8b input chainも一致する。

## 2.3 official validation battery

内訳：

```text
observed maps                         10
fresh isotropic                     1,000
hybrid E7 l2-4 + isotropic l5-16      200
total                               1,210
```

CSVから独立に再計算した結果：

```text
max all-axis relative residual f64    1.7706589e-7
max all-axis relative residual f32    1.3135191e-6

argmin f64 vs reference               1,210 / 1,210
argmin f32 vs reference               1,210 / 1,210
argmin f32 vs f64                     1,210 / 1,210

Event B mismatch f64                  0
Event B mismatch f32                  0

near-tie count                        1,151
antipode exact-tie fraction           0.942975
runner-up is antipode fraction        0.996694
R-row equal fraction                  0.934711

f32 axis mismatch count               0
max plane-folded separation           1.4788e-6 deg
```

provenanceに保存された全指標と一致した。

smokeの70 rowsは、official CSV内の同名70 samplesと全35列で一致した。従ってsmokeからofficialへのsample reproductionも確認できる。

### float32 eligibility

```text
float32_eligible_for_event_outputs    True
float32_eligible_for_axis_outputs     True
float32_eligible_for_rules            True
```

A8aにおいて、float32 selectionとfloat64 evaluationをproduction engineering候補にする根拠は成立している。

## 2.4 A8a判定

> **FEATURESTACK_VALIDを承認する。**  
> F16の科学的・数値的freezeはGOである。

ただし、今回のZIPは監査用の軽量packetであり、self-contained freeze bundleではない。最終freezeには少なくとも以下を含める。

```text
MirrorTopology_Step1_A8a_featurestack_v1.1.2.ipynb
a8a_env_lock.json
smoke／official provenance
smoke／official validation CSV
smoke／official manifest
smoke／official console log
F16 float64 .npy
F16 float32 .npy
freeze manifest（relative path / size / SHA256）
```

今回のA8a ZIPでは、**smoke console log**と**F16二ファイル**が欠けている。これは今回のscience判定を否定しないが、formal archiveでは補完すること。

---

# 3. A8b v1.1.8

## 3.1 status・gate

### smoke

```text
status                 SMOKE_PASS
RUN_PASS               True
SMOKE_PASS             True
BENCHMARK_VALID        False
gate inventory         exact
required gates         35
true gates             35
false gates            0
console terminal       STATUS = SMOKE_PASS
```

### official

```text
status                 BENCHMARK_VALID
RUN_PASS               True
SMOKE_PASS             False
BENCHMARK_VALID        True
gate inventory         exact
required gates         35
true gates             35
false gates            0
console terminal       STATUS = BENCHMARK_VALID
```

official notebook identity：

```text
live source-only       e2b33af9da22079f47012587441c7db163735989c9b5d6ccbde6ad2978b3f0df
origin/main copy       e2b33af9da22079f47012587441c7db163735989c9b5d6ccbde6ad2978b3f0df
```

A8bが参照したA8a official provenance SHA：

```text
04fc829e3de1a0043028bc9265f1a6991aa113d47b66985e1b0b3d2005ee9750
```

は、今回のA8a ZIP内のofficial provenance実bytesと一致した。

## 3.2 output SHA chain

smoke／officialの次の全出力について、実bytesのSHAはprovenance `outputs`と一致した。

```text
a8b_benchmark_cpu.csv
a8b_benchmark_gpu.csv
a8b_attempts_evidence.jsonl
a8b_audit_vectors.npz
a8b_timed_audit_vectors.npz
a8b_timed_audit_index.json
```

officialのtimed NPZはZIP内で：

```text
a8b_timed_audit_vectors (1).npz
```

というupload/download由来らしいsuffix付き名称になっているが、内容SHA：

```text
9c362781836c3b7f79f652998164b04b92545058aac60c812648dd439008b108
```

はprovenance記録と完全一致する。freeze前にcanonical名：

```text
a8b_timed_audit_vectors.npz
```

へ戻すこと。再実行やprovenance変更は不要である。

## 3.3 inventory・attempts

```text
official registered attempts      63
status ok                         62
status timeout                     1
unclassified                       0
timed audit archived configs      62
canonical audit route/dtype groups 7
```

timed indexの62 configとNPZの248 arrays（62×4）は一対一対応し、全`n_audit=10,000`、argmin SHA、route、dtype、stage、chunk、axis blockが整合する。

登録pilotからfinalist、finalistからwinnerを、登録済み`top-K + safe-choice`規則で独立に再構成したところ、provenanceの全16 finalist・全6 winnerと完全一致した。

## 3.4 independent recomputation of tie-equivalence gates

officialのcanonical audit NPZおよび全timed audit NPZを用い、HEALPix RING Nside=16のantipode mapを独立構成して、`selected_output_equiv`を全62 timed configへ再適用した。

結果：

```text
all timed configs pass                62 / 62

float64 raw-axis flip occurrences      0
float32 flip occurrences           3,995
all float32 flips exact antipode       True

max selection-score rel difference
among float32 timed comparisons        2.1162663e-6

max float64 T1 relative difference     0
max float64 T2 relative difference     0
Event B indicator mismatch             0
```

route別：

```text
l24_direct_einsum / float32
  flip occurrences                     441
  unique flipped samples               156

l24_feature231 / float32
  flip occurrences                     320
  unique flipped samples               141

s2_feature / float32
  flip occurrences                   3,234
  unique flipped samples             1,381
```

全flipはexact antipodal partnerであり、非対蹠flipは0。provenanceの`selection_reproducibility`と一致した。

選ばれたproduction winner自体は、official canonical auditに対して：

```text
l24 feature f32 / chunk 20000          raw flip 0
S2 f32 / chunk 1024 / axis block 3072 raw flip 0
```

であった。ただしraw tie-breakのhardware portabilityは保証せず、科学的axisはunoriented plane `[n]={n,-n}`として扱う方針を維持する。

## 3.5 cross-route／cross-dtype

独立再計算値：

```text
l24 direct vs feature / float64
  raw argmin agreement                  1.0000
  selection rel                         2.3585e-15
  T1/T2 rel                             0 / 0

l24 direct vs feature / float32
  raw argmin agreement                  0.9844
  all flips antipodal                   True
  selection rel                         1.6000e-6
  T1/T2 rel                             0 / 0

l24 direct f32 vs f64
  raw argmin agreement                  0.9898
  all flips antipodal                   True
  selection rel                         1.9084e-6
  T1/T2 rel                             0 / 0

l24 feature f32 vs f64
  raw argmin agreement                  0.9920
  all flips antipodal                   True
  selection rel                         1.7251e-6
  T1/T2 rel                             0 / 0

S2 feature f32 vs f64
  raw argmin agreement                  0.9916
  all flips antipodal                   True
  selection rel                         6.7396e-7
  T1/T2 rel                             0 / 0
```

全て登録閾値内であり、provenanceと数値単位で一致した。

Event B indicatorはA8bのunit-variance benchmark drawsでは全Trueで縮退している。A8bはthreshold bindingとindicator equalityを確認するが、物理振幅sampleに対するfloat32 Event B適格性はA8a officialから継承する、というprovenanceの限定は正しい。

---

# 4. A8b official engineering result

## 4.1 l2–4 scan

正式recommendation：

```text
route                   l24_feature231
selection dtype         float32
evaluation dtype        float64
sample chunk            20,000
BLAS threads            2
measured N              1,000,000
production time         0.655132 min / 1e6
scan-only time          0.578647 min / 1e6
end-to-end time         0.661643 min / 1e6
peak RSS increment      0.332759 GB
```

比較対象の`l24_direct_einsum / float32 / chunk 2000`：

```text
production time         1.053079 min / 1e6
peak RSS increment      0.066056 GB
```

feature routeはdirect routeより：

```text
speedup                  1.607×
time reduction           37.79%
```

であり、5% tie bandを十分超えて速い。feature winnerの3-repeat rangeは約8.71%と他routeより大きいが、directとの差は約38%であるためroute選択は覆らない。

fallback：

```text
chunk 10,000
chunk 5,000
chunk 2,000
```

## 4.2 S2 scan

正式recommendation：

```text
route                   s2_feature
selection dtype         float32
evaluation dtype        float64
sample chunk            1,024
axis block              3,072
BLAS threads            2
measured N              200,000
production estimate     83.083739 min / 1e6
scan-only estimate      82.988072 min / 1e6
end-to-end estimate     83.220182 min / 1e6
peak RSS increment      1.020473 GB
production device       CPU
GPU route               unavailable
```

この83.08分は**N=200,000からの線形外挿**であり、N=1,000,000の実測ではない。per-sample timeは：

```text
pilot       0.00487168 s
finalist    0.00494223 s
winner      0.00498502 s
max/min     1.02327
```

で、登録線形性基準1.2を十分満たす。

しかし予測時間：

```text
4,985.0 s = 83.08 min
```

が登録budget：

```text
2,400 s = 40 min
```

を超えるため、optional CPU N=1,000,000は登録規則どおり実行されなかった。

winnerの3-repeat rangeは約0.184%で、時間推定は安定している。

fallback：

```text
(chunk 1024, axis block 512)
(chunk 512,  axis block 512)
(chunk 512,  axis block 3072)
```

## 4.3 S2 float64 winner timeout

唯一のtimeout：

```text
route        s2_feature
dtype        float64
N            200,000
chunk        1,024
axis block   3,072
repeats      3
timeout      3,600 s
```

float64 finalistの最速実測は、N=100,000で約998.4秒／repeatである。線形予測ではN=200,000の3 repeatだけで約5,991秒（約99.8分）となるため、60分timeout超過は予測可能である。

これは：

- hidden exceptionではない
- `timeout`として分類・保存されている
- registered inventoryに含まれる
- f64 pilot／finalistは正常
- f32-vs-f64 selected-output equivalenceはPASS
- production routeはf32

ため、A8bのengineering recommendationを無効にしない。

ただし「S2 f64のN=200,000 winner実測値」は存在しない、と明記すること。

---

# 5. 実行環境と適用範囲

official CPU environment：

```text
CPU                 Intel Xeon 2.20 GHz
logical / affinity  2 / 2
OpenBLAS            0.3.27
Python              3.13.15
NumPy               2.1.3
RAM                 13.61 GB
GPU                 none
```

全成功configの最大memory ratioは、`peak increment / available RAM ≈ 0.1674`であり、登録上限0.65より十分小さい。swap increaseは全件0。

今回の絶対時間・optimal chunkはこのenvironmentへbindingされたengineering resultである。別CPU、別BLAS、別thread数、GPU環境ではabsolute timeやoptimal chunkを普遍値として扱わない。scientific outputは同じだが、性能値を移植する際はenvironment fingerprintを併記する。

---

# 6. freeze／rules判定

## 6.1 A8a

> **Scientific feature-stack freeze：GO**

ただし完全bundleへF16二ファイル、A8a env lock、smoke console log、notebookを追加すること。

## 6.2 A8b

> **Engineering benchmark freeze：GO**  
> **rules v1.0へのroute／dtype／chunk／memory転記：GO**

転記事項：

```text
l2–4:
  route            l24_feature231
  selection dtype  float32
  evaluation       float64
  chunk            20,000
  threads          2

S2:
  route            s2_feature
  selection dtype  float32
  evaluation       float64
  chunk            1,024
  axis block       3,072
  threads          2
  CPU estimate     83.08 min / 1e6
  GPU              not benchmarked (unavailable)
```

axis reproduction：

```text
scientific axis    unoriented mirror plane [n]={n,-n}
raw HEALPix index  exact antipodal tiesではfloat32 blocking／hardware間でportableでない
float64            registered chunk間でraw index exact
```

rules文は、実際のhard gateに合わせて：

> exact-antipodal axesがexactまたはselection tolerance内で数値的に未解決のtieとなり、selection score、float64 T1/T2、Event B indicatorが一致する場合にのみ同一selected outputとして扱う

とする。「全antipodal pairがidentical reflection rowでexact tie」と一般化しないこと。

## 6.3 A8b final archive

現行A8b ZIPは結果監査packetとして十分だが、self-contained freeze bundleには次も含める。

```text
MirrorTopology_Step1_A8b_scan_benchmark_v1.1.8.ipynb
A8b_amendment_v1.1.7.md
parent a8b_v1.1.5_smoke/
  a8b_provenance.json
  a8b_audit_vectors.npz
  a8b_attempts_evidence.jsonl
A8a official provenance／manifestまたはそのfreezeへの参照
A8b smoke／officialの全7 outputs
A8b smoke／official console logs
freeze manifest（relative path / size / SHA256）
```

`a8b_timed_audit_vectors (1).npz`はcanonical名へ戻す。

---

## 7. 最終判定表

| 項目 | 判定 |
|---|---|
| A8a ZIP integrity | PASS |
| A8a smoke | PASS |
| A8a official 49/49 | PASS |
| A8a 1,210-sample validation | PASS |
| A8a float32 event/axis eligibility | PASS |
| A8a F16 freeze | **GO** |
| A8b ZIP integrity | PASS |
| A8b smoke 35/35 | PASS |
| A8b official 35/35 | PASS |
| A8b output SHA chain | PASS |
| timed audit archive | PASS |
| float64 raw-axis exactness | PASS |
| float32 exact-antipode equivalence | PASS |
| chunk／route／dtype invariance | PASS |
| adaptive finalist／winner selection | PASS |
| l2–4 engineering recommendation | **GO** |
| S2 CPU engineering recommendation | **GO** |
| GPU recommendation | なし（unavailable） |
| A8b rerun | **不要** |
| rules v1.0 engineering freeze | **GO** |
| S2 scientific adoption | **HOLD：S4／exact validation待ち** |

