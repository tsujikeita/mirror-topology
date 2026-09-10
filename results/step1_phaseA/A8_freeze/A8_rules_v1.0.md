# A8 engineering rules v1.0（Step 1 rules v1.0 への転記文）
2026-09-11。出典：A8a v1.1.2 official（`FEATURESTACK_VALID`）・A8b v1.1.8 official（`BENCHMARK_VALID`）・ChatGPT 最終監査（2026-09-10）§6。
本書は **engineering** 規則である。S2（hybrid ℓ≤16 選択）の**科学的採用は S4／exact validation gate 完了まで HOLD**（従来登録のまま）。

## R1. 選択と評価の dtype（A5 凍結仕様の再確認）
- selection：float32（A8a `float32_eligible_for_rules=True` ∧ A8b の当該 route の f32-vs-f64 selected-output equivalence PASS）。
- evaluation：**float64**（凍結 ℓ2–4 B-stack，`s1_Bstack_l2_4_N16_common_v1.npz`）。T₁・T₂・Event B は選択された plane で float64 評価。
- Event B indicator：`T1 <= T1_obs and T2 <= T2_obs`，`T1_obs = 39.67178834527284`，`T2_obs = 259.3375006282747`（Step 0 official v0.7・PR3_Commander）。

## R2. ℓ2–4 走査（S1 selection surrogate）
| 項目 | 値 |
|---|---|
| route | `l24_feature231`（231 packed features × 3072 axes GEMM） |
| selection / evaluation dtype | float32 / float64 |
| sample_chunk | 20000 |
| BLAS threads（登録） | 2（= affinity） |
| 実測 | N=10⁶：production 0.655 min／10⁶（scan 0.579・end-to-end 0.662），peak RSS +0.33 GB |
| fallback tiers | chunk 10000 → 5000 → 2000 |

## R3. S2 走査（hybrid ℓ≤16 feature stack・CPU baseline）
| 項目 | 値 |
|---|---|
| route | `s2_feature`（40755 packed features × F16 stack，resident copy） |
| selection / evaluation dtype | float32 / float64 |
| sample_chunk / axis_block | 1024 / 3072 |
| BLAS threads（登録） | 2 |
| 推定 | **83.08 min／10⁶**（N=2×10⁵ 実測からの線形外挿；per-sample 比 pilot/finalist/winner max/min = 1.023 < 1.2）。10⁶ 実測は予算 40 min 超過のため未実施 |
| memory | peak RSS +1.02 GB（run +0.72 GB，setup 1.05 GB＝F16 float32 resident） |
| fallback tiers | (1024, 512) → (512, 512) → (512, 3072) |
| production device | **CPU**。GPU は unavailable のため未計測（採用推奨なし）。GPU を使う場合は GPU runtime での別 benchmark が必要 |
| float64 fallback | `s2_feature`/float64 は finalist N=10⁵ までの実測（166–174 min／10⁶）。**N=2×10⁵ winner の実測値は存在しない**（登録 TIMEOUT 3600 s 超過・classified `timeout`） |

## R4. 軸の再現性（amendment v1.1.7 の semantics）
- 科学的 axis 出力は **unoriented mirror plane class `[n] = {n, −n}`**。
- float32 selection では，exact-antipodal な 2 軸が exact または selection tolerance（1e-4）内で数値的に未解決の tie となり，
  **selection score・float64 T₁/T₂・Event B indicator が一致する場合にのみ**，同一 selected output として扱う。それ以外の軸差は不一致。
  （「全 antipodal pair が identical reflection row で exact tie」とは一般化しない。）
- float64 selection は登録 chunk 間で raw axis index の完全再現を要求する。
- raw HEALPix pixel index は，exact tie では float32 blocking・BLAS・hardware 間で portable ではない。production の chunk/thread を
  凍結しても raw index の普遍的再現は保証しない。portable な出力は canonical plane と float64 selected outputs。
- 監査量：official audit（N=10⁴）で float32 flip は l24_direct 156・l24_feature 141・s2 1381 標本（unique），全件 exact antipode，
  selection score 差 ≤2.1e-6，T₁/T₂ 差 0。

## R5. 環境 binding
絶対時間・最適 chunk は official 環境（Intel Xeon 2.20 GHz・2 threads・OpenBLAS 0.3.27・Python 3.13.15・NumPy 2.1.3・13.6 GB）に
bind された engineering 値。他の CPU/BLAS/thread/GPU では普遍値として扱わず，性能値を転用する際は environment fingerprint を併記する。
成功 config の最大 memory ratio（peak increment / available）= 0.167（上限 0.65）。swap 増加 0。

## R6. 入力の凍結値
- F16 feature stack（A8a）：float64 file `aca84c5f…`／array `4feac266…`，float32 file `9e433de0…`／array `a0281b4f…`（shape 3072×40755）。
- A8a official provenance `04fc829e…`，manifest `d89f5801…`，env lock `f62ec935…`。
- A5 B-stack npz：A8a manifest `inputs.bstack_file` の値（A8b `G_a5_bstack_file_sha` で再検査済）。
