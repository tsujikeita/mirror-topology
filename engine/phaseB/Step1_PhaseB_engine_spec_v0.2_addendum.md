# Step1_PhaseB_engine_spec v0.2 追補 — 入出力契約（R1–R7）と B-1 実装
2026-09-13。Claude作成。v0.1（SHA `1cc4b26b…`）に対する ChatGPT 監査（draft4／spec v0.1）Part II の R1–R7・§13–§15 を反映。v0.1 の module 分割・工程は維持。
規則本文：`Step1_rules_v1.0_draft4.1.md`（表示修正のみ；SHA `5f02c970…`。規則内容は draft4 `72305bbf…` と同一）。

## A. 契約（実装済み・`step1_engine/` に対応）
**R1 CI 型**（`ci.py`）：`CIResult(value_domain∈{Q,P}, log_lower, log_upper, lower, upper, effective_method, math_state, counts, alpha, B, reason)`。log 尺度と native 尺度を別 field に持つ（L_Q ≥ 3 は native `lower` と比較，相対半幅は native，CV は log 幅）。技術 FAIL では端点を返さず `None`＋reason。JSON 化で ±inf は文字列 enum（bare Infinity を使わない）。入力は keyword-only `invalid` mask と `mode`；負 count・P>1・shape 不一致は technical-invalid（clip しない）。CI 層は label を決めない。
**R1 精度層**（`precision.py`）：`PrecisionState(state∈{pass, precision-unresolved, cv_undefined, technical_fail}, rel_halfwidth, width_cv_logQ, positive_clusters, reasons)`。無限端点・Q=0／undefined・非有限幅は PASS にしない；log 幅平均 0 は `cv_undefined`。
**R2 family 入力**（`family.py`）：stats 層が各点の P = hits/N（検証済み整数と N）を作り，family 層が固定 prior で model／reference の P を**別々に混合**（`mixed_numden`），CI 層は混合後の分子・分母（float64 の確率）を受ける。hits の pooling と Q_j の平均を禁止（テストで反例を固定）。密度は `mixed_log_density`（logsumexp）；機構分解は family 混合の P(A∩B)・P(A) から（条件付き分母 0 は undefined flag）。
**R3 三値判定**（`decision.py`）：`CoreDecision(support_truth, strong_truth, unsupported_truth ∈ {True, False, 'unknown', 'technical_fail'}, technical_status, display_label, reason_codes, required_audits, ci_computation_status, direction_native)`。三値 AND は technical_fail > False > unknown > True。監査は `audit_Q_matched／Dpoint／DCI／Q_native` に分離し native は Q のみ。較正 usable は集計後に決め，core 評価へ戻さない（`calibration.py` は truth 列だけを受ける）。
**R4 BootstrapPlan**（`bootstrap_plan.py`）：`BootstrapPlan(plan_id, seed_id, strata{batch→[ClusterUID]}, replicates, multiplicities{batch→(B,K)})`。同じ CRN group の全評価に同一 plan を適用；prefix stratum と extension stratum を別々に復元抽出し，stratum 重みと各点分母を保持；literal 展開 reference（`literal_resample_hits`）と整数和が bit 一致。浮動小数の混合は同一演算順で比較し，それ以外は事前登録許容。
**R5 KDE weights**：B-1 では未実装（B-2）。登録推定器を保つ高速化は「頻度重み式」（μ*・C*=Σc(x−μ*)(x−μ*)ᵀ/(N*−1)・factor=N*^{−1/(d+4)}・logsumexp）のみ許可し，単純 `gaussian_kde(weights=…)` は不可（neff・共分散正規化が literal と異なる）。family 向けには `log_f_model[b,j,t]`／`log_f_reference[b,j,t]` を渡し，混合密度の log 差を replicate ごとに作る。
**R6 W₂ 停止と検証の分離**（`w2_stop.py`）：`w2_stop` は単一最大長 null 列の prefix で B=200→1000 を評価し `StopResult(B_final, stop_reason, trace, null_prefix_id, state)`；`w2-unresolved` は **B_max でも条件未達**の場合のみ。`w2_validate` が 3 seed×2 n_sub の一致（混在 indicator は不合格）・seed spread・selection margin（欠損 bound は 0 にしない）・q99 前値 0 の例外状態を検査。
**R7 orchestrator**：B-2 で `evaluate_threshold(threshold, bank_registry, rules)` を定義（pseudo ごとに N prefix・event-ratio・3→12 分岐を再評価；W₂ 本体は固定 MC 資産として再利用）。B-1 では状態機械（`position_state.py`）のみ。

## B. 受入テスト inventory（工程配属を明示）
| 工程 | テスト ID | 内容 | 状態 |
|---|---|---|---|
| B-1（本提出） | T1–T5, CI contract, serialisation | 境界値分位・envelope・技術 FAIL・domain | **22/22 PASS** |
| B-1 | T7–T9, T16, mutant, three-valued | predicate・conjunct-drop・閾値 ≥3 mutant・unknown→False mutant | PASS |
| B-1 | family mixture（R2 反例）, T10（小規模 stratified vs literal）, T18 | 不等 N・非一様 prior・prefix/extension・UID | PASS |
| B-1 | T11–T13, T15, T17, T20（表 1／1b／2／3／4／5／6） | 状態機械・W₂ 停止／検証・Wilson(c+u)・JSON↔本文 | PASS |
| B-1 | T14（小格子 unit） | E7 greedy：ChatGPT の独立 reference 9 点と一致・順序不変・旧 min_sep fail-fast | PASS |
| B-2 | T10（実 bank）, T14（正式解像度・E2/E8・Colab）, T19（A5 cross-check・実資産）, KDE literal/頻度重み同値性, multi-point integration fixture（2 family・複数配置・3 位置・native 別参照・N₀/4N₀・3→12） | | 未 |
| B-3 | control 電池 official 規模（negative／positive full predicate／conjunct-drop・brute-force）, 12 位置 manifest | | 未 |

T3 は算術（CI 層）と判定（統合）に分割：B-1 は算術のみ。T19 は「すべて合成入力」の例外（Colab）。golden case は手書き（JSON を oracle にしない）。

## C. 保存・binding（§15 対応・B-2 で実装）
`rules_tables_v1.json` の schema／本文 SHA／表 SHA／config 完全 SHA を checkpoint binding に含める；bank metadata（evaluation/ref ID・purpose・group・stratum・prefix・m・unit・axis order）；near-minimizer set は CSR（offsets＋canonical plane ID）；CI は log/native 端点・domain・method・state・reason・plan 参照；W₂ は trace・B_final・null/bound 配列・subset ID・whitening SHA・両 dtype 入力 SHA；NaN/Infinity は enum/null で表現。

## D. 二層の回帰（§14 対応）
legacy regression（A10 と同じ資産・latent・演算順・chunk で scan／evaluation／固定 subset OT を bit 照合）と new-rules reference（KDE-CI・family 混合・境界分位・stratified bootstrap・可変 B 停止を独立 literal に照合）を分け，新規則を A10 の旧挙動に合わせない。
