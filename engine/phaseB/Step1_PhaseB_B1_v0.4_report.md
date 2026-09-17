# Phase B・B-1 v0.4 実装報告（B-2 開始時の最初の変更）
2026-09-13。Claude作成。ChatGPT 監査「B-1 v0.3」（2026-09-13）の §3（区間伝播）を正式反映し，B-2 intake として明示延期されていた §5（first-stop 検査・rng key/UID 全要素照合・重複 key）と §6（表 1 の厳密 schema）も同じ変更に含めた。規則本文（draft4.1）・spec 追補・科学的仕様は不変。`__version__='0.4.0'`。
**テスト：84/84 PASS**——`test_b1.py` 22・`test_b1_contracts.py` 14・ChatGPT 原本 22（v0.1 監査）・14（v0.2 監査）・**8（v0.3 監査の重点；前回 7/8 → 8/8）・4（v0.3 監査の B-2 intake pending；0/4 → 4/4）**。ChatGPT 原本はいずれもテストロジック無改変・ROOT 行のみ配置に合わせて変更。環境：Python 3.12／NumPy 2.4（サンドボックス）。

## 1. 対応
| ID | 内容 | 実装 | negative test |
|---|---|---|---|
| §3 区間伝播 | 区間は一つの量：片端が非有限／支持域違反／逆転／片側欠損なら**両端を TECH**にし，その区間を必要とする predicate へ伝播（無関係な量の support は否定しない） | `decision.validate_inputs`（監査差分と同じ 3 行）＋`reason_codes` に `invalid_interval:<Q_matched|logD_matched|Q_native>` を保存 | 監査の 5 変形（native 上端 NaN／+inf・matched 上端 NaN・DCI 上端 NaN・unsupported 候補で DCI 下端 NaN）：必要 predicate が True にならず technical_status='technical_fail'；U_Q_native=NaN で support は True のまま strong は TECH |
| §5.1 first stop | `StopResult.validate`：全隣接水準で停止条件を評価し，**最初に成立した水準が最終行**であること（skip も早期停止も拒否），`stop_reason` が state の登録文字列と一致 | `STOP_REASONS` 登録・`met_at(i)` の全走査 | 400 で成立する履歴を 800 まで延ばした復元物・未登録 stop_reason を拒否 |
| §5.2 key/UID | `BootstrapPlan.validate`：rng key の (wave, purpose, group, batch, seed, stream) が stratum UID と全要素一致，key 要素は整数，UID は同一 wave/purpose/group | — | key の group だけを 888 に変更 → 拒否 |
| §5.3 重複 key | `serialization.loads`：object の重複 key と `__intkeys__` の重複整数 key を拒否（`object_pairs_hook`） | — | `{"audit":"fail","audit":"pass"}` |
| §6 表 1 schema | `rules_config._check_predicates`：label ごとに**登録 term 多重集合と完全一致**（閾値は数値欄から描画），未知・欠落・余分・重複 term と未登録の数値表記（`3e1`）を拒否；display_priority も照合。無制限 eval なし | import 時の `verify_binding` に含まれる | 監査の 3 例（conjunct 削除・`3e1`・空 AND）＋重複・余分 term を検出 |

## 2. 変更なし（監査で PASS 確認）
R2・R3・設定変更 3 例・格子端点・保存往復・950 reference の算術。

## 3. B-2 で閉じる残り（監査 §4・§5 の一部）
- **数学的境界値の adapter**：CIResult（math_state・counts・端点）を保持したまま，判定に使える値（有限）と監査状態（precision-unresolved→unknown）へ明示変換する層。数学的境界→精度未解決→unknown と，技術 NaN→technical_fail を混同しない。精度未解決の量から得た数値比較の False を確実 False と扱わない（表 3／表 5 の contract を orchestrator で実装）。
- 完全 checkpoint binding（本文 file SHA・JSON 完全 SHA・module SHA・null 列 SHA・q99 再計算），KDE literal／頻度重み reference，`evaluate_threshold`，multi-family fixture，official profile 検査，E2/E8 正式生成，legacy／new-rules 二層回帰。
