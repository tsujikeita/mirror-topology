# A8b amendment v1.1.7：tie-equivalence gate の訂正（v1.1.5 smoke FAILED → v1.1.7 amended rule）
2026-09-10。Claude作成。ChatGPT 監査（2026-09-10「smoke失敗分析・v1.1.6 gate訂正」）を反映。
**この文書は Drive の `runs_step1_phaseA/A8b_amendment_v1.1.7.md` に置き，v1.1.7 の provenance が
その SHA256 を `amendment.amendment_report_sha256` として記録する（`G_parent_failed_smoke_binding`）。**

## 1. 経緯（証拠鎖）
1. **v1.1.5 Colab smoke**（2 threads・OpenBLAS 0.3.27）：31 config すべて `ok`，timing・memory・thread・A8a chain・GPU probe は正常。
   失敗 gate は `G_chunk_invariance`・`G_audit_matches_timed` の 2 つのみ。**status=FAILED のまま保存**
   （`runs_step1_phaseA/a8b_v1.1.5_smoke/a8b_provenance.json`，SHA256 `ad92387f5bd9cdcd7e6a393688704503660539d1abdb44d7962be4398a418a40`）。
2. 内訳：float64 selection は全 route・全 chunk で raw argmin まで bit 同一（差 0.0）。float32 selection のみ raw argmin が一部
   chunk で入れ替わり，selection score 差 2.8e-7〜7.4e-7（float32 分解能），T₁/T₂ 差 0.0，f32-vs-f64 の不一致箇所の raw margin は
   すべて 0.0（厳密同点）。audit child の margin は全 route で min=median=0。
3. 解釈（ChatGPT 監査で「基本的に妥当」と評価）：反射面法線 n と −n は同じ unoriented plane。3072 軸 grid の対蹠ペアの多く
   （A5：2780/3072）が同一の reflection/B 行を持ち数学的に同点。float32 GEMM の blocking（chunk・thread 依存）で同点の
   first-occurrence が入れ替わる。バグではなく，raw axis representation の非一意性。
4. **v1.1.6（撤回）**：margin-aware gate を実装したが，**plane equivalence を hard gate しておらず**（raw margin は対蹠重複で
   ほぼ常に 0 のため，対蹠でない遠い別軸への flip も通り得た），失敗分析書の合成試験は notebook の述語に対するものではなかった。
   float64 側まで不要に緩和し，chunk gate の reference axis（最初の pilot config）と margin source（winner audit）が食い違っていた。
   v1.1.6 は smoke・official とも**実行していない**。
5. **v1.1.7（本 amendment）**：下記の新 gate 意味を**結果を見る前に固定**し，新規 commit → 新規 smoke → 新規 official を行う。

## 2. gate 意味の変更
| | 旧（v1.1.5） | 新（v1.1.7） |
|---|---|---|
| 再現対象 | oriented HEALPix pixel index の完全一致 | **unoriented mirror plane [n]={n,−n} ＋ selected outputs** |
| float64 selection | raw argmin exact | **raw argmin exact（不変）**＋ score 1e-9・T₁/T₂ 1e-6・Event B indicator 同一 |
| float32 selection | raw argmin exact | 軸は same または **exact antipode かつ reference raw margin < 1e-4**；score 1e-4・**float64 T₁/T₂ 1e-6**・**Event B indicator 同一** |
| 適用範囲 | chunk 不変性・audit 照合（cross-route は別実装） | **共通 helper `selected_output_equiv`** を chunk 不変性・audit 照合・direct vs feature・f32 vs f64・GPU vs CPU の全比較で共有 |
| reference | chunk gate：最初の pilot config／margin：winner audit | **untimed audit child に統一**（reference axis・raw margin・selected outputs が同一計算から来る） |

閾値（1e-4／1e-9／1e-6）・staged 設計・選択規則・route/chunk の winner 決定・数値カーネル・memory/checkpoint 設計は不変。
緩和は「float32・exact antipode・厳密同点（margin < 1e-4）・float64 出力同一・Event B 同一」に限定される。
非対蹠の neighbor plane flip は許容しない（必要になれば plane-folded separation・distinct-plane margin を用いる別の事前登録が要る）。

## 3. v1.1.7 の追加 required gate
- `G_plane_equivalence_gate_selftest`：実際の helper に対する 6 合成ケース——(1) f32・exact antipode・margin 0・出力同一 → PASS／
  (2) f32・遠い非対蹠軸・margin 0・出力同一 → FAIL／(3) f32・exact antipode だが T₁ 差 > TOL_EVAL → FAIL／
  (4) f32・exact antipode だが margin ≥ 選択許容 → FAIL／(5) f64・antipode flip → FAIL（raw exact）／(6) 軸同一だが Event B indicator 変化 → FAIL。
- `G_float64_raw_argmin_exact`：float64 selection は全 chunk で raw argmin 完全一致（測定値として provenance にも記録）。
- `G_antipode_map_involution`：`ANTIPODE[ANTIPODE]==arange(3072)` かつ不動点なし。antipode map の SHA256 を provenance へ。
- `G_eventB_thresholds_bound`：Event B 閾値（T₁_obs=39.67178834527284，T₂_obs=259.3375006282747）を pinned repo の
  Step 0 official CSV（PR3_Commander）から読み，A8a の定数と一致することを要求。indicator は `T1 <= T1_obs and T2 <= T2_obs`。
- `G_parent_failed_smoke_binding`：親 FAILED smoke の path・SHA256・notebook 名・false gate 集合（`G_audit_matches_timed`,`G_chunk_invariance`），
  本文書の SHA256，旧/新 gate 意味を provenance の `amendment` に記録し，一致を要求。
- provenance の再現性記述は固定文字列ではなく実測値から生成（`selection_reproducibility.measured`：`float64_raw_argmin_exact`・
  `float32_flip_count`・`float32_all_flips_antipodal`・`float32_max_selection_score_rel`・`float32_max_T1_rel`・`float32_max_T2_rel`・
  `eventB_identical_all`）。margin は `raw_oriented_axis_margin`（winner のみ除外・対蹠 duplicate は除外しない・厳密対蹠同点で 0）と定義を明記。
- `RULES_RECOMMENDATION.axis_reproducibility`（scientific_axis・raw_pixel_index の非可搬性・selection_configuration・evaluation_dtype・statement）を追加。

## 4. rules v1.0 への転記文言（ChatGPT 推奨をそのまま採用）
S2 の axis selection は，登録済み route・selection dtype・sample chunk・axis block・BLAS thread 数で行う。float32 では，数学的に同一の
対蹠 axis pair が厳密同点となる場合，raw HEALPix pixel index は演算 blocking 間で入れ替わり得る。従って科学的 axis 出力は
unoriented mirror-plane class [n]={n,−n} として報告する。T₁，T₂ および Event B の評価は，選択された plane において凍結 float64
B-stack で行う。float64 selection は登録 chunk 間で raw axis index の完全再現を要求する。
「production chunk/thread を凍結すれば raw index も普遍的に再現する」とは書かない（CPU・BLAS・hardware が変われば raw tie-break は
変わり得る。portable な出力は canonical plane と float64 selected outputs）。
