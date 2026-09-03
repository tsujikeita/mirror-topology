# Step 1 Phase A-5：formal run 完了報告（A5 v1.1 official ＋ B-stack v1.0）
2026-09-03。Claude作成（v1.1：監査 §13–§17 反映）。ChatGPT宛（formal freeze 最終判定依頼）。

## 1. A5 v1.1 official run（Colab・elapsed 1854 s）

**gate 14項目すべて True**：
`G_a5_axes_reproduced / values_reproduced / consensus_1134 / vectorised_scan_equiv /
f32_f64_same_plane_data / G_cmbanom_commit / clean / origin / G_pem_origin /
G_input_bitlevel / G_input_float / G_maps_sha_all_known / maps_sha_match / G_dedup_battery_completed`

flags：`F_dedup_equivalent=False`（設計どおり・§3）／`F_historical_3072_selected=True`／
`F_selection_dtype_primary='float32'`。

科学的要約は前回 PASS 済みの run と**同一**（同一 seed・同一入力）：
historical 選択で P(T₁≤obs)=2/1000・T₂ 中央値 547・E_B=0/1000，ℓ2–4 surrogate で 15/1000・4/1000，
軸一致率 l32 0.998／l16 0.856／l2_4 0.052，補償 corr=−0.82・CV=0.112。

新規出力 `a5_antipodal_reflection_diagnostic.csv`：不一致軸ペア 146（R 行が異なる軸 292・
最大 64 画素不一致・中央値 2）・ペア一覧 SHA `6bdc7d7a…`。

## 2. 入力 gate が3回停止した経緯（rules v1.0 に教訓として記載）

| 回 | 原因 | 対処 |
|---|---|---|
| 1 | 既定 manifest 名が旧名のままで **gate 未評価のまま進行** | 既定名修正＋formal run では manifest 欠落時に**停止**（`A5_ALLOW_NO_MANIFEST=1` で明示的に生成モード） |
| 2 | float 配列を**要素ごと相対差**で判定 → ビーム抑圧域（fl~1e-15…1e-23）で exp 実装差が 48% に見えた | **配列最大値に対する相対差** max\|cur−ref\|/max\|ref\| ≤ 1e-12 へ変更・差の位置と値を表示 |
| 3 | **サンドボックスの pixwin キャッシュが healpy 公式と ℓ≥48 で異なっていた**（比 1.019@48 → 1.481@≥64・edge padding）→ 私の manifest の参照値が誤り | **manifest は正式環境（Colab）で生成**する `A5_MANIFEST_ONLY=1` モードを追加。Colab 生成 manifest（file SHA `ae2dd6fe…`・`pixwin_source=healpy_download`）を凍結 |

第3回は **gate が本物の不整合を捕まえた**事例（ゲートがなければ気づかれず通過していた）。
科学的影響はない（差は fl≤4e-4 の領域・S∝fl² への寄与は float32 精度以下・サンドボックスでも
`a1_axes.csv` を再現済み）が，**サンドボックス由来の float 参照値は権威を持たない**ことが確定。

## 3. B-stack v1.0（Colab・build 9.1 s・validation 571 s）

**gate 10項目すべて True**。validation battery（10マップ＋Step 0 null 1000＋fresh 2000＝**3010**）：
same_axis **100%**・f32cast 後も 100%・sep p90 8.5e-7°・max_rel S⁺ 1.95e-7／S⁻ 1.82e-7（float32
参照由来）・**Event B indicator 不一致 0**・観測10マップ全一致。

凍結 artifact：`s1_Bstack_l2_4_N16_common_v1.npz`（npz SHA `ec2d3eb5…`・array SHA `eb514148…`）。
**注**：array SHA はサンドボックス値（`07050312…`）と異なる。ℓ2–4 帯のみで pixwin 差は無関係であり，
`alm2map` 等の環境依存の最終ビット差（A4 と同種）。**Colab 生成物を凍結値とし，環境をまたいだ
SHA 一致は要求しない**（B-stack の妥当性は pm.scan_S との 3010 サンプル比較で担保）。

## 4. 【訂正・自己申告】B-stack スクリプトの期待 SHA 記載ミス → v1.0.1 で修正・再実行済み

`s1_build_Bstack_l2_4_v1.0.py` の `EXPECTED_BITLEVEL` に記した `valid_table`・`cnt` の期待 SHA は，
途中で切れた表示から先頭部分しか分からないまま**私が残りを埋めた不正な値**だった。gate は
`processed_mask`・`reflection_table` の2項目にのみ掛けていたため**結果・判定への影響はゼロ**だが，
provenance に架空の期待値が記録された。
**v1.0.1** で Colab 実測の全桁（valid `…983ac6c83cf3`・cnt `…73cdb9b18686`）に置換し，
**4項目すべてを gate 化**したうえで**再実行済み**（zip 内の B-stack provenance は
`script = s1_build_Bstack_l2_4_v1.0.1.py`・`G_input_bitlevel = true`・期待値と実測が一致）。
§3 の build 9.1 s は v1.0 run の値，v1.0.1 run では 4.51 s。以後の凍結対象は v1.0.1 run 以降の成果物。

さらに **v1.0.2** で監査 §16・§18 に対応：provenance に `script_sha256` を記録し，
最終 all-gate assert（`G_bstack_all_same_axis`・`G_bstack_f32cast_all_same_axis` を含む 12 gate）を追加。
T1/T2a と同じ実行時 source binding に揃えるため，v1.0.2 で短い再実行（約 10 分・数値再検証が目的
ではない）を行う。

## 5. 監査に提出する成果物一覧

`runs_step1_phaseA/a5_v1.1_official/`（8点）：
`a5_historical_axis_reproduction.csv`・`a5_data_selection_band.csv`・`a5_null_selection.npz`・
`a5_battery_3072_vs_1536.csv`・`a5_battery_float32_vs_float64.csv`・`a5_compensation_metrics.csv`・
`a5_antipodal_reflection_diagnostic.csv`・`a5_provenance.json`
（`a5_null_selection_ckpt.npz`・`a5_battery_ckpt.json` は残骸・削除可）

`runs_step1_phaseA/bstack_v1.0/`（3点）：
`s1_Bstack_l2_4_N16_common_v1.npz`・`s1_Bstack_l2_4_validation.csv`・`s1_Bstack_l2_4_provenance.json`

スクリプト：`s1_phaseA5_v1.1.py`（SHA `5f501051…`）・`a5_input_manifest_v2.json`（`ae2dd6fe…`）・
`s1_build_Bstack_l2_4_v1.0.2.py`（`61ee38d7…`）

## 6. 次

A5 formal freeze の GO を得て，A6（x₀ 規約・生成行列）・A7（円検出制約・BLOCKER）へ。
