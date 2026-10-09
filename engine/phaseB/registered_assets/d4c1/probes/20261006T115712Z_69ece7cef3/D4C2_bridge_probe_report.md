# D4C-2a 環境 bridge probe（固定 0.110.0・E2・N＝3・Python 3.13.16）：照合報告 — 2026-10-07

監査 `D4C2a_v3_0.110.0_audit_decision.json`（固定 0.110.0 の bridge probe のみ GO）と `D4C2a_v5_0.112.0_audit_decision.json`（比較 script v2 の実装受入れ；§6 の実施条件）に従い，著者が実行した probe の原本を **受入れ済みの比較 script v2** で読んだ結果を報告する。**結果：契約充足（`BRIDGE_CONTRACT_SATISFIED`，36 check すべて True，rc 0）**。これは監査の確認を待つ報告であり，rc 0 だけで数値 bridge の受入れに代えるものではない（監査 §7）。

## 1. 原本（byte 保存；上書きなし）
| file | SHA-256 | bytes |
|---|---|---|
| `d4c1_partial_E2_39082b641d86.zip`（launcher の zip：lock・final record・`run_20261006T115712Z_69ece7cef3/`（run record・probe record・profile・archive 17 entry・stdout）） | `d5bb91b103fa33c6e1ae3764e47aa4e3e2ae3e0326fb4966c0cad52978329ded` | 523,671 |
| 内 `d4c1_partial_lock.json` | `7555adf9a8f6f80d3ec84618b74884d102d91b351f293e9c1061b350210994ae` | — |
| 内 `d4c1_partial_final_record.json` | `09c36b9e082d4f27d354b7858ea4ab4937b2998a01722d484f9cd4e033df7458` | — |
| 内 `d4c1_probe_E2_run.json` | `c35e5426e1b00847439d4b54886107f0b177cb2829a6710263d42a33b69a0264` | — |
| 内 `d4c1_probe_E2_record.json`（partial record；payload `774951eacb3e60e8408f582fc194847ba66191c095ee4a9a026922305680a322`） | `4cbc3e3fe05bdccba7c8a94a7b37277f5a35639b17919e723de41abc4be194a9` | — |
| 内 `d4c1_probe_E2_profile.json` | `dbb41e6358c45e3ae49b1c218b41901daa57c0617bd036a6f4467f32a2959b08` | — |
| `MirrorTopology_Step1_D4C1_partial_v0_1_executed_39082b641d86.ipynb`（実行済み launcher notebook v0.3；cell 0 の値は監査 `probe_execution_settings` と同一；出力に lock SHA `7555adf9…`・attempt `20261006T115712Z_69ece7cef3`・rc 0・`partial_pass False`（probe）が記録） | `88ac16fb64074d9995be82ab964a07e6e313b363cc1dba8af9678da06be691a8` | 49,671 |

attempt `20261006T115712Z_69ece7cef3`（2026-10-06 11:57:12Z → 12:59:35Z，3742.7 s；High-RAM：RAM 54.75 GB）。lock：commit `39082b641d8621989ae69a273f4e88e0c59673ba`・engine 0.110.0・inventory `7df1fb59…`・family E2・probe_n 3・instrument True・row_range None・campaign `D4C2_9efa1b8d82fe`・commitment `9efa1b8d…`。final：stage complete・exit_code 0・launcher_fallback False・gates／bindings／evidence ok・failures 空；precheck／prelaunch の head＝`39082b64…`・clean。run record：24 gate 全 True・probe True・`D4C1_PARTIAL_PASS` False（設計どおり）・env `python 3.13.16 / numpy 2.1.3 / scipy 1.16.3 / healpy 1.20.0 / camb 2.0.4 / pot 0.9.7.post1`・twelve gate official／passed／live_collected。

## 2. 照合の実施条件（監査 v5 §6 どおり）
- 比較 script：v5 packet の `d/d4c2_bridge_compare.py`（SHA `ca545b61c8b867ec2c36210a77012b2a93b125a2cd04d193e4b8e68ce93fc605`；0.112.0 tree 内の bytes）を **別の場所から** fresh CLI process で実行。
- producer tree（`--phaseb`）：v3 packet zip（SHA `3ae56bf1d4911e0955b312e5b44335d9a3398d5dab0b654d713e4fce7e677646`）から展開した**未改変の 0.110.0 tree**（inventory `7df1fb5948eb2c0c0d379a37afa93c0f1dbc0bba77c01c49d6be60665d9bb1ba`）；その engine／reader を import。
- spec：`D4C2a_v3_0.110.0_bridge_comparison_spec.json`（SHA `a9cb9ab9b622cb0d929006eac01a957003a5eeffef990a40de8c6338a0981373`；書換えなし）。
- baseline：登録 probe の元 zip（SHA `538f5e07f3c4fae84803d17783ff09a03fef5270cd04b600376e2af891644766`）。
- `--expected-commit 39082b641d8621989ae69a273f4e88e0c59673ba` を明示。
- 報告 JSON：`d4c2_bridge_report_20261006T115712Z_69ece7cef3.json`（schema `d4c2_bridge_comparison_report_v2`；SHA `cf72b217eec1624fee40aafea8f5cfaf71c460c03a315cca0918b9e9c14b1bef`；入力・source tree の外の新規 path）。

## 3. 結果
**`BRIDGE_CONTRACT_SATISFIED`：36/36 check True，不一致なし，rc 0。**
- **per-row record 15 件**（family_result 3・three_position_result 9・pseudo_family_plan transition 3）：typed identity と global row で対応づけ，content SHA と bytes が spec と**完全一致**（両 probe；欠落・余剰・重複なし）。registry record 同一（`4010a332…`）。残る 1 entry＝partial 自身の transition（新 `32e7a96e…`；許容される provenance 差）。archive 17 entry・一意。
- **`required_equal_partial_fields`（19 field）**：内容一致（差分 0）。
- **provenance の差（期待どおり）**：engine 0.107.0 → 0.110.0，gate 環境の Python 3.13.15 → 3.13.16，`binding.modules` は異なる，payload SHA `057ae753…` → `774951ea…`（科学 field は不変）。
- **新 record の自身 reader**（0.110.0 の `load_partial_record`＋`verify_partial_record(registered identity, current_source_binding=True)`）：ok・registered_context_ok；published＝archived。
- **producer provenance**：AST `REQUIRED_PARTIAL`（24）と一致・全 True；source／pins／script／engine＝tree；lock／final／precheck／prelaunch／attempt／twelve gate／publication すべて一致。
- **環境**：baseline gate 環境＝登録履歴（3.13.15），新 gate 環境＝現行登録環境（3.13.16），双方 live_collected・passed；BLAS pool 規則充足。
- **profile 文書**：schema・producer TARGETS（22）・segments 3（index 0..2）・missing_targets 空・会計整合・cProfile 表；run summary／receipt と一致。

科学的内容（参考；baseline と同一）：3 行とも eligible truths `unknown`（support／strong／unsupported），core truths False，expand なし（12 位置評価 0），plan status「provisional / position-unresolved」（E2/L1.20 の登録 W₂ decision unknown による）。

## 4. 資源計測（計測付き；**本番速度ではない**：wrapper と cProfile の overhead を含む）
- 全体 3742.7 s（staging 530.4 s・12.33 GB；script 3208.7 s：preflight 24 s・first-wave intake 53 s・plans 20 s・views 64 s・twelve inputs 363 s・twelve gate 86 s・partial 2598.5 s）。peak RSS 16.05 GB（baseline 16.03 GB）。
- profile：segments（`evaluate_family_full` 3 回）計 786.6 s（1 行あたり 269.0／258.9／258.7 s；baseline の非計測 313.9 s/pseudo とは条件が違うため比較しない），**segment 外 1811.8 s**（固定費＋行別保存）。segment 外の内訳で目立つのは `formal_runner.input_fingerprint`（42 回・inclusive 1752.5 s・self 737.6 s）と，その下で呼ばれる `serialization.to_jsonable`（3.07 億回・self 1221.7 s）：**固定費の大半は入力 fingerprint（view の canonical 直列化）**で，行数に比例しない。1 行あたりの評価そのものは `bootstrap_plan.resample_hits`（2160 回・496 s）と `orchestrator._family_Q`（48 回）が主。
- これは計測の事実であり，設計変更の提案や性能の主張ではない（監査の注意：計測時間を production speedup と解釈しない）。固定費の構造（fingerprint 支配）は，sub-partial の chunk 設計を議論する際の材料として報告するにとどめる。

## 5. 主張しないこと
数値 bridge の受入れは監査が原本と照合して判断する。本結果は固定の先頭 3 行（E2）の環境 bridge のみを扱い，未発火の N4／KDE-CI／12 位置の数値経路，全 2000 行の同等性，screen／certificate／正式較正／Phase E を承認するものではない。不一致があれば停止する手順であったが，不一致は生じなかった（再試行なし・許容誤差なし）。
