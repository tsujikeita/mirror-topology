# Step 1 登録環境 amendment v0.1：Python 3.13.15 → 3.13.16（rules §0.4 の記録）— 2026-10-06

## 1. 事象（trigger）
2026-10-06 08:23 JST，監査 GO（`D4C2a_0.108.0_audit_decision.json`：計測付き probe E2・N＝3，commit `4668b2e5…`）の実行で，partial launcher v0.3 の preflight（cell 1）が **環境 lock（launcher pre-check）で停止**した：`environment lock failed (launcher pre-check): {'python': ('3.13.16', '3.13.15')}`。Colab の既定 runtime image が 2026-10-05（probe 実行：Python 3.13.15）以後に更新され Python **3.13.16** になった。Colab の「ランタイム バージョンを変更」で選べる唯一の代替「2026 年 7 月」は **Python 3.12** 系で，pins の numpy 2.1.3 を導入すると numpy 本体が壊れる（`ImportError: cannot import name '_center' from 'numpy._core.umath'`）ため，登録環境 3.13.15 を Colab 上で再現する手段はない。Python 3.13.15 と 3.13.16 は同一 minor の patch release（バグ修正）である。launcher は設計どおり停止しており（hard gate；notebook・source は無改変），self-test skip 等の迂回は行っていない。

## 2. 変更（本 amendment；engine 0.110.0）
| 対象 | 変更 |
|---|---|
| `step1_engine/official_gate.py` `EXPECTED_VERS.python` | `"3.13.15"` → `"3.13.16"` |
| `d/d1_pins.json`・`d/d2_pins.json`・`d/d3_pins.json`・`b3/b3_0_pins.json`・`b3/b3_1_pins.json`・`b3/b3_2_pins.json` の `environment.python` | `"3.13.15"` → `"3.13.16"`（launcher の pre-check と script の hard gate が参照） |

| `step1_engine/official_gate.py` `EXPECTED_VERS_HISTORY`・`registered_environments()`・`recorded_environment_registered()`（新） | 登録履歴（3.13.15 の環境；`registered_until` に本 amendment を記録）。**登録済み run の record** を読む loader（`d3c_ledger.intake_registered_d3c_profiles`・`d4c0_registry.load_registered_w2_context`／`load_registered_pseudo_columns`）は，record の環境が **現行 EXPECTED_VERS または登録履歴のいずれか**に一致することを要求する（従来は現行 pins のみ；amendment 後に登録資産が読めなくなるのを防ぐ）。**新しい実行**の gate（`official_gate`・launcher pre-check・script の `G_env_lock`）は現行 EXPECTED_VERS との厳密一致のみ。 |
| pins 6 file の `environment_history` | engine の `EXPECTED_VERS_HISTORY` と同内容（loader が pins と engine の一致を検査；不一致は拒否） |

**変えないもの**：numpy 2.1.3・scipy 1.16.3・healpy 1.20.0・POT 0.9.7.post1・camb 2.0.4・BLAS pool 規則；環境 gate の**規則そのもの**（厳密一致・hard gate・self-test skip の禁止）；すべての登録資産（bank・pseudo 列・W₂ context・D-3c profile・twelve asset・ledger／receipt；受入れ済み run の record に記録された `python: 3.13.15` は履歴としてそのまま）；A11 の env lock（履歴；gate では metadata）。数値 kernel・script・notebook の logic は不変。

## 3. 性質（rules §0.4）
- 種別：**実装環境の patch 版更新**（interpreter のバグ修正 release）。科学的設計・統計規則・閾値・seed・plan・入力の変更ではない。
- 閲覧済み情報の開示：本 amendment の時点で，登録 D-2W W₂ context の 9 case 判定（4 case unknown）と，probe（E2・先頭 3 行・3.13.15）の record（core truths False・eligible unknown・Q_matched 等）を著者と監査が閲覧済みである。amendment は結果に依存しない（環境が利用不能になったことだけが動機）。
- 旧版の保持：3.13.15 で生成・受入れた資産と record は原本のまま。新旧 semantics：gate が受け入れる Python の文字列が 1 つ置き換わるだけ。

## 4. 受入れ条件（監査へ提案）
1. **再現同一性**：commit（本 amendment を含む）で計測付き probe（E2・N＝3・`INSTRUMENT=True`）を 3.13.16 で実行し，published partial record の **payload SHA が登録 probe（3.13.15，`057ae75355fd7a716aba9d52d5a520275c9c6fd3b57162a4e7d389e327223878`）と一致**し，archive の per-row record（family_result 3・three_position_result 9・transition 4）の content SHA 集合が一致すること（`registered_assets/d4c1/probes/20261005T100239Z_386d63207c/` の原本と照合）。一致しなければ本 amendment は不成立とし，差分を報告して停止する（結果を見ての再試行はしない）。
2. 新しい実行の環境 gate は 3.13.16 を**厳密一致**で要求する（旧 3.13.15 の runtime が戻っても，その run は gate で止まる＝二重登録を避ける）；登録済み run（3.13.15）の record は履歴として受け入れ，それ以外の環境（例 3.13.14・別 numpy）は拒否する（`tests/test_d4c2a.py::test_registered_environment_history_and_live_gate`）。
3. 本 amendment 後に生成・受入れる record は `python: 3.13.16` を記録する；受入れ済み資産の再生成・再実行は要求しない（intake は bytes／配列 SHA を再検証する）。

## 5. 試験
既存の環境 gate 試験は `EXPECTED_VERS` を記号的に参照し（`tests/test_b2_tranche21.py`・`test_audit_b2_tranche21_chatgpt.py`・`gate_fixture.py`・`test_d4c0.py`），登録 run の ledger に記録された `3.13.15` を検査する試験（`test_d3b_tranche2.py`・`test_d3c_tranche2.py`・`test_d3_partition_intake.py`・`test_audit_d1_v02_independent_chatgpt.py`）は履歴 record を検査するため不変。全 suite は packet の `regression_logs/` を参照。
