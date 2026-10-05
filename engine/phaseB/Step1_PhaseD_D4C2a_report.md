# Step 1 Phase D4C-2a 報告：計測版・pseudo 範囲 sub-partial／再開・固定分母の成功不能証明（engine 0.108.0）

2026-10-05（Claude）。前提：監査 `D4C2_probe_231d37b8_audit_decision.json`（probe 証拠受入れ；正式 4 family partial／combiner／較正受入れ／W₂ 再生成／E1 単独／Phase E はすべて GO なし；GO は **設計・実装・小規模試験**の 3 項目のみ）。設計は `Step1_PhaseD_D4C2a_design_v0.1.md`。**本 packet は Colab 実行を含まず，実行 GO を求めるものでもない**（§6 に実行計画の提案だけを置く）。

## 1. probe 証拠の原本保存と報告書の訂正（監査 §2・§7-C）
- `registered_assets/d4c1/probes/20261005T100239Z_386d63207c/`：probe zip（`538f5e07…`，515,915 B）・実行済み notebook（`72af76c8…`）・資源報告 v1 原本（`9e9ad98f…`；監査入力と byte 同一）・**資源報告 v2**（訂正版）・監査報告 md・監査 decision JSON・監査 evidence zip・`file_map.json`（SHA／bytes／役割；scope＝probe evidence，正式入力・較正受入れ・usable seal と区別；nonce なし）。
- v2 の訂正：Q_matched＝1.0120085663800016／1.0091025254182917／0.9999809485249505，3 行目の帯域幅感度 False（非技術的監査結果），174 h は「上限でも下限でもない」素朴外挿，「ほぼ全件 unknown で usable=False が構造的に決まる」は撤回（W₂ unknown は恒久的 veto ではない；event-ratio で全 size の 12 位置化があり得る；3 件から u≈n は確定しない；全件計算前に正式 usable=False とは報告しない）。
- v2 受入れ監査の原本（`ChatGPT_audit_D4C1_v2_0.107.0.md`・`D4C1_v2_0.107.0_audit_decision.json`）は `registered_assets/d4c1/acceptance/` に保存（前 packet で未同梱だった分）。

## 2. 実装（engine 0.108.0；61 module）
| 項目 | 内容 |
|---|---|
| `step1_engine/profiling.py`（新） | `Profiler`：engine entry point 22 target を参照先の全 module 属性で timing wrapper に差替え（exit で復元）；calls／inclusive／self；segment（＝`evaluate_family_full` 1 回＝1 pseudo）ごとの差分と segment 外（固定費）；任意で cProfile；record `d4c1_profile_record_v1`（科学量なし；「計測時間は本番速度ではない」注記）。**record は不変**（payload SHA 一致を試験）。 |
| `step1_engine/d4c1_partial.py`（変更） | `calibrate_family_partial(..., _rows=(start, stop))`：global 行範囲の評価（archive record は global `pseudo_index`），sub-partial record（schema `family_subpartial_calibration_v1`／kind `family_subpartial_calibration`，`rows`・global／slice 列 identity・`subpartial_dependencies`）。`_rows=None` の挙動・record 内容は不変（既存 D4C-1 試験 19 件通過）。 |
| `step1_engine/d4c1_subpartial.py`（新） | `calibrate_family_subpartial`・`check_subpartial_shape`・`load_subpartial_record`・`verify_subpartial_record`（run reader，global offset）・`combine_family_subpartials`（tiling／共通 identity／gate identity／連結順／manifest key／archive ref 順／provenance／reader 再検証）・`strip_subpartial_provenance`・`plan_row_ranges`・`gate_identity`。 |
| `step1_engine/run_reader.py`（変更） | `verify_run_references(..., pseudo_index_offset=0)`：view の i 番目の status が archive record の global 行 `i+offset` に対応することを検査（既定 0＝従来どおり）。 |
| `step1_engine/infeasibility.py`（新） | `wilson_blocking_count`・`registered_blocking_counts`（2000：81／12）・`exact_hit_rate`・`envelope_screen_family`・`check_screen_record`・`blocking_rows_from_screen`・`blocking_rows_from_statuses`・`infeasibility_certificate`・`check_certificate`（schema `position_envelope_screen_v1`／`calibration_infeasibility_certificate_v1`）。 |
| `step1_engine/checkpoint.py`・`__init__.py`・pins 6 | MODULES に 3 module 追加；版 0.108.0。 |
| `d/d4c1_calibration.py`（変更） | `--row-range A:B`（sub-partial；REQUIRED_SUBPARTIAL 25；`D4C1_SUBPARTIAL_PASS`），`--mode combine-family`（REQUIRED_COMBINE_FAMILY 20；全 sub-partial PASS のときだけ `D4C1_PARTIAL_PASS`；`--mode combine` がそのまま消費），`--instrument`（probe のみ；profile record publication），`--mode screen`（REQUIRED_SCREEN 20；第 1 波のみ；`D4C1_SCREEN_COMPLETE`），`--mode certificate`（REQUIRED_CERTIFICATE 14；env lock 外；`D4C1_CERTIFICATE_COMPLETE`）。既存 mode の REQUIRED・挙動は不変（24／18）。 |
| notebook | partial v0.1 file（内容 v0.3：`ROW_RANGE`・`INSTRUMENT`・`OUT_ROOT`（Drive 出力；入力 run root との交差は従来どおり拒否）；信頼 REQUIRED は `REQUIRED_PARTIAL`／`REQUIRED_SUBPARTIAL` を launch に応じて AST 照合；sub-partial は `D4C1_SUBPARTIAL_PASS` のみで pass），combine v0.1（不変），**combine-family v0.1**（新），**D4C2 screen v0.1**（新）。 |

## 3. 試験
- `tests/test_d4c2a.py`（11 関数）：module 登録／版；sub-partial record の形と global identity（archive record の global index・自 archive／merged archive での reader 検証・partial reader による拒否）；**結合＝単一 process partial の内容同一**（2 通りの tiling；trigger が 2 chunk に跨る列；archive ref 同一・同順）；結合 partial → `combine_family_partials` ＝ `calibrate_sealed`（provenance 除く）；拒否（gap／missing／duplicate／overlap／空／family partial 混入／commitment・campaign・mode・context・source・gate・fingerprint・plan object・global identity の差／slice 編集／無 re-stamp 編集／昇格 truth（reader 再導出）／不正 range／official の n／別 source 版／`plan_row_ranges`／offset の型）；別 family・外部 family；Profiler（record 不変・segment・固定費・12 位置の segment 帰属・復元・単回使用・引数検査）；Wilson 計数（監査値一致）；合成 bank の screen＝evaluator（E2 全行 blocking⇔unknown，E7 発火行は未判定で evaluator が拡張，非発火行は blocking⇔unknown；P＝`P_model`）・不適用条件・E1 拒否・入力検査・改竄検出；混合 prefix 全探索（60 乱数例＋手作り例：同一 N だけでは不十分）；certificate の計数／統合／矛盾／改竄／reader 拒否。
- `tests/test_d4c2a_script.py`（6 関数・13 case）：生成器 small bank で E2 sub-partial 2 range → combine-family（＝単一 self-test partial の内容同一，gate 除く）→ 4 family combine；拒否（gap・duplicate・campaign・sub-partial を combine へ・probe＋range・instrument 単独・不正 range・列超過）；`--instrument` probe（profile record publication；probe record は非計測 probe と内容同一，gate 除く）；`--mode screen`（E2；rows；E1 拒否；D-3b 拒否；列束縛）と `--mode certificate`（screen のみ受理；列不一致の evaluated 拒否；campaign 拒否）；notebook 構造（combine-family・screen）；partial notebook の sub-partial attempt cell（mock 子 process：`--row-range` 伝達・REQUIRED 25・sub-partial 文書の束縛・`D4C1_PARTIAL_PASS` だけでは pass しない・Drive `OUT_ROOT` の保護 root）。
- 既存：`tests/test_d4c1.py` 19・`tests/test_d4c1_script.py` 55（notebook v0.3 への追従：namespace・REQUIRED 定数名・文書 binding）。全 suite の JUnit は `regression_logs/d4c2a_pytest/`（§5）。

## 4. 主張しないこと
高速化係数（計測器だけ；hot spot は実測後）；screen の実 bank での blocking 行数（未実行；81／12 行が得られるとは断定しない）；正式 usable の値；12 位置分岐の時間；sub-partial の Colab 上の挙動（notebook は contract test のみ）。

## 5. 全 suite
29 chunk（`regression_logs/d4c2a_pytest/j1..j29.xml`・`chunks_stdout.txt`；A：chunk 1〜19，B：chunk 20〜29（26〜29 が D4C-2a）），JUnit の multiset＝`pytest --collect-only` の 1923 node id（欠落・余剰なし），fail／error／skip 0（`test_log.txt`）。sandbox 環境（Python 3.11・numpy 等の版）は登録環境と異なるため，script 試験はすべて `--selftest-skip-env-lock` の self-test であり，PASS flag は出ない（設計どおり）。

## 6. 実行計画の提案（別途 GO）
1. 計測 probe（E2・N＝3・`INSTRUMENT=True`・commit 固定）。2. screen（E2／E7／E8・全行）→ certificate（どこでも）。3. 証明成立なら原登録の完走／不能証明での終了／明示 amendment の選択を監査へ；不成立なら sub-partial 計画（Drive `OUT_ROOT`，chunk 250〜500 行）と同等性試験付き高速化 tranche。
