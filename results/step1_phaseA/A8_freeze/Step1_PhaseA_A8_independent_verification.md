# Step 1 Phase A-8 成果物の独立検算報告（A8a v1.1.2 official・A8b v1.1.8 smoke/official）
2026-09-11。Claude作成。ChatGPT宛（official 出力監査用）。対象：先生から受領した `A8a_results.zip`・`A8b_results.zip`。

## 0. 結論
- **A8a v1.1.2 official：`FEATURESTACK_VALID`**（inventory exact・False gate なし・flags event/axis/rules すべて True）。
- **A8b v1.1.8 smoke：`SMOKE_PASS`（35/35）**，**official：`BENCHMARK_VALID`（35/35・inventory exact）**。official は純正 notebook
  （live == origin/main == source-only `e2b33af9…`＝実行前監査で承認した bytes）で実行された。
- freeze 成果物（timed audit NPZ・index・canonical audit NPZ）**のみ**から，chunk/audit 等価性・float64 raw exact・exact-antipode flip・
  cross-route/dtype を独立再計算し，provenance の全 gate 値・flip 数（3995）と**一致**。非対蹠 flip **0**。
- 実行環境は **CPU-only**（GPU なし・2 threads・13.6 GB）。GPU optional route は未計測（`gpu_status=unavailable`，設計どおり classified）。
- **1 件の timeout**：S2 float64 winner（N=2×10⁵・3 repeats）が登録 TIMEOUT 3600 s を超過。登録規則上 `timeout` は benchmark 失敗ではなく，
  production 決定（float32）にも影響しないが，float64 S2 の実測は finalist N=10⁵ 止まり（後述）。

## 1. SHA 鎖
| 項目 | 確認 |
|---|---|
| A8b smoke/official の `inputs.a8a_provenance_sha256` | 受領 A8a official `a8a_provenance.json` の SHA と**一致** |
| A8b `inputs.manifest_sha256` | A8a provenance 記録値 ＝ 受領 manifest ファイルの SHA と**一致** |
| A8b official `notebook_identity` | live `e2b33af9…` ＝ head_copy `e2b33af9…`（origin/main `856c3c84`）＝ 実行前監査の source-only SHA |
| A8b smoke `notebook_identity` | live `55bef908…`（`A8_MODE='smoke'` セル追加のため相違・設計どおり），head_copy `e2b33af9…` |
| A8b `outputs`（6 ファイル SHA） | smoke・official とも受領 bytes と**全一致**。official の timed NPZ はダウンロード時に `a8b_timed_audit_vectors (1).npz` と改名されているが bytes は同一（Drive 上の原本名は正規） |
| amendment binding | `G_parent_failed_smoke_binding`・`G_parent_failed_smoke_artifacts` True，報告書 SHA `950bea6c…` 一致 |
| CPU child SHA | `4cfd7c09…`（v1.1.6 以来不変） |

## 2. freeze 成果物のみからの独立再計算（healpy で antipode map を独立構成・SHA `11efe112…` 一致）
| | smoke | official |
|---|---|---|
| timed config 数（audit subset 付き） | 31 | 62 |
| 全 timed config が canonical audit child と selected-output equivalent | ✔ 31/31 | ✔ 62/62 |
| float64 raw argmin exact（全 float64 config） | ✔ | ✔ |
| float32 flip occurrences（provenance 記録値） | 38（38） | 3995（3995） |
| 非対蹠 flip | 0 | 0 |
| float32 max selection score rel | 7.4e-7 | 2.1e-6 |
| float32 max T₁/T₂ rel | 0.0 / 0.0 | 0.0 / 0.0 |
| unique flipped samples by route（AUDIT_N=10⁴） | — | l24_direct 156・l24_feature 141・s2 1381 |
| cross-route/dtype 5 比較 | 全 PASS（provenance 一致） | 全 PASS（provenance 一致） |
| raw oriented-axis margin min/median（全 route/dtype） | 0.0 / 0.0 | 0.0 / 0.0 |
| Event B indicator | 縮退（全 True・provenance に明記） | 縮退（同左） |

S2 float32 では audit 標本の 13.8% で raw pixel index が対蹠へ入れ替わる（ℓ2–4 では 1.4%）。すべて同一 plane・score 差 ≤2.1e-6・
float64 T₁/T₂ 厳密同一——amendment の前提どおり。

## 3. ROUTE_DECISION（official・登録規則で一意に確定）
| | ℓ2–4 | S2（CPU baseline） |
|---|---|---|
| route / selection dtype | `l24_feature231` / **float32** | `s2_feature` / **float32** |
| sample_chunk / axis_block / threads | 20000 / – / 2 | 1024 / 3072 / 2 |
| 実測 N | **10⁶（measured）** | 2×10⁵（→10⁶ は線形外挿；linearity ok・projected 83 min > 予算 40 min のため optional 1e6 未計測） |
| production 時間 / 10⁶ 標本 | **0.66 min**（scan 0.58） | **83.1 min**（scan 83.0） |
| peak increment / setup | +0.33 GB / 0.07 GB | +1.02 GB（run +0.72）/ 1.05 GB |
| fallback tiers | ch 10000・5000・2000 | (1024,512)・(512,512)・(512,3072) |
| production_device | – | **cpu**（optional_gpu = None） |

dtype 規則：A8a `float32_eligible_for_rules` ∧ 当該 route の f32-vs-f64 cross-check PASS → 全 route float32。evaluation は float64（A5 凍結）。
参考（float64 に戻す場合）：ℓ2–4 feature231 float64 ch 2000 = 1.28 min/10⁶（N=10⁶ 実測）；S2 float64 = 166–174 min/10⁶（finalist N=10⁵ 実測のみ）。

## 4. 正直に申告する 2 点
1. **GPU 未計測**：official が CPU runtime で実行されたため，GPU strict-fp32 route の採用可否は判定されていない（`G_gpu_classified` は
   `unavailable` で PASS）。CPU baseline は required，GPU は optional という登録どおり，rules v1.0 の起草に支障はない。GPU 加速を将来
   使う場合は，GPU runtime での別 official（または GPU 専用の追補 version）が必要。
2. **S2 float64 winner の timeout**：N=2×10⁵ × (warm-up＋3 repeats) ≈ 0.01 s/標本 × 6×10⁵ ≈ 100 min ＞ TIMEOUT 60 min。
   登録上 `timeout` は「ineligible であって失敗ではない」扱いで gate は設計どおり PASS。ただし rules v1.0 には「S2 float64 fallback の
   実測は finalist N=10⁵ まで」と明記すべき。TIMEOUT=3600 s は notebook 定数（source-only SHA に含まれる）だが provenance `registered`
   に明示記録されていない——記録上の軽微な不足として申告する。

## 5. 提案する次段
1. 本報告＋7 出力ファイル（smoke・official）＋console log を ChatGPT の official 出力監査へ。
2. GO 後：`results/step1_phaseA/A8_freeze/` に A8a official・A8b smoke/official の成果物と freeze manifest（A5/A11 と同形式・LF 正規化
   log hash・archive commit）を作り，tag（例 `a8-freeze-v1.0`）。
3. A10（W₂・global 較正の設計）→ `Step1_rules_v1.0_draft` 起草（§3 の ROUTE_DECISION と §4 の 2 点，amendment の axis_reproducibility
   文言（ChatGPT §8.1 の修正版）を転記）。
