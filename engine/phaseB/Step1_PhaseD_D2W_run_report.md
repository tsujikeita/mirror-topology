# Phase D4C-0a（D-2W）正式実行の報告 — 9 W₂ case の評価・typed record・復元（commit `f3aec793…`，engine 0.104.0；attempt `20261004T144349Z_cb8bc8e5f7`）
2026-10-05。Claude 作成。ChatGPT 宛（D-2W 正式実行の実行後受入れ監査の依頼）。監査 GO：`D4C0_v3_0.104.0_audit_decision.json`（D2W_RETRY_GO；固定 commit `f3aec79358452a293ccced14efd4f7e3ad240477`・inventory `49976b3e…`；GitHub tree と v3 packet の 2576 file が byte 一致することを Claude 側で確認済み）。失敗 attempt `20261004T102439Z_9bac8f8730`（commit `12980202…`）は別 zip のまま不変に保持（監査 JSON に SHA 固定済み）。

## 1. 回収物（原本のまま）
| file | bytes | SHA-256 |
|---|---|---|
| `d2w_cases_f3aec7935845.zip` | 5,646,698 | `13e222e57d624473eba4fda045d400b34bf9a3fda6623fe74eacb1325a53a72b` |
| `MirrorTopology_Step1_D2W_cases_v0_1_executed_12980202ee11.ipynb`（実行済み notebook；file 名は著者の命名で，内容は commit `f3aec793…` の実行） | — | `3d8a7ff7519e971b8981ff73256c2d975c8a7bc8ab11b7cc876c98a55807e89c`（packet 内では `..._executed_f3aec7935845.ipynb` に改名して同梱；bytes は不変） |
| `MirrorTopology_Step1_D4_pseudo_v0_1_executed_12980202ee11.ipynb`（pseudo の実行済み notebook；監査 §6.6 の求めに応じ提出） | — | `fb7a0d663694eac623a169006d9f0ac21c8a382213655ad357d9fbf938add973` |
| `d4c0_d2w_sandbox_verification.json` | — | Claude sandbox での照合（§3） |

zip の member：lock・final record・stdout／stderr・run `20261004T144349Z_cb8bc8e5f7`（run record・log・`d2w_context_record.json`・`cases/` 9 file（各 ≈3.86 MB；stored evidence を含む））。

## 2. 結果
### 2.1 launcher（`d2w_launcher_final_record_v2`）
- lock：commit `f3aec793…`・inventory `49976b3e…`・script `dcd64283…`・D-2 ledger `07574dfa…`・shared-null asset `cc676867…`・pins `de1794b5…`・engine 0.104.0・3 run root（ledger の run_root＋`/out/d2` と一致）・STAGE_LOCAL True。precheck／prelaunch の live source 観測 2 回とも一致。
- 標準 CPU runtime：RAM total 13.61 GB／available 11.86 GB。staging：27 unit＋registry 3＝303,031,554 bytes，32.9 s。attempt 全体 874.1 s。**`d2w_pass` True**（rc 0・`launcher_fallback` False・`gates_ok` True・`bindings_ok` True・`evidence_ok` True・`failures` []）。
### 2.2 script record（`d2w_run_record_v1`）
- **13 REQUIRED gate すべて True**（`G_env_lock` True：python 3.13.15／numpy 2.1.3／scipy 1.16.3／healpy 1.20.0／camb 2.0.4／pot 0.9.7.post1；BLAS pools OK）。self-test なし・`production_official`。
- 入力解決（v3）：3 family の registry bytes＝ledger `bank_registry_sha256`（E2 `5498697e…`／E7 `6c4db39c…`／E8 `b780e67c…`）・run_id 3 件・W₂ unit 9／family・`resolution_failures` []。matched root は登録 D-1 共分散 27 件（receipt `D1_aa089fa492bc`）。shared-null asset `8348d5f4…`（iso K 6000・replicate bounds）。
- 時間：preflight 11.4 s・intake（27 unit の bytes／配列 SHA 再検証・ledger 照合）44.7 s・**評価 731.0 s（9 case；≈81 s/case）**・publication＋復元 51.1 s；script 合計 838.2 s。RSS：intake 1.44 GB・評価後 1.49 GB・final 1.62 GB；**peak 2.31 GB**（評価中）。
- `G_records_restored` True：published record からの復元が live context と一致。context SHA **`50ec5a54d593d9bc53ce3661292d7dd3cb385369511a3444fda62226e77acb9c`**。
### 2.3 科学的結果（記録のまま；受入れの条件ではない）
| case | state | trigger | B_final | stop reason | q99(2000／5000) |
|---|---|---|---|---|---|
| E2/L1.00 | valid | False | 400 | indicator_unchanged_and_q99_rel_change_below_tol | 0.2229／0.1559 |
| E2/L1.20 | **w2-unresolved** | unknown | 800 | 同上（mixed above/below indicators at B_final） | 0.2299／0.1542 |
| E2/L1.50 | valid | False | 400 | 同上 | 0.2229／0.1559 |
| E7/L1.00 | valid | False | 400 | 同上 | 0.2229／0.1559 |
| E7/L1.20 | **w2-unresolved** | unknown | 600 | 同上（mixed） | 0.2329／0.1533 |
| E7/L1.50 | **w2-unresolved** | unknown | 400 | 同上（mixed） | 0.2229／0.1559 |
| E8/L1.00 | **w2-unresolved** | unknown | 400 | 同上（mixed） | 0.2229／0.1559 |
| E8/L1.20 | valid | False | 400 | 同上 | 0.2229／0.1559 |
| E8/L1.50 | valid | False | 400 | 同上 | 0.2229／0.1559 |

集計：valid（trigger False）5 case・w2-unresolved（trigger unknown）4 case・技術 FAIL 0。unresolved は rules §10 の安定性条件（n_sub 2000／5000 × 3 seed の indicator 混在）未達による推定上の未決であり，技術 FAIL ではない（D-4 較正では unknown として保守的に扱う；R-D4DESIGN-E）。**unresolved を理由とする再実行・seed／条件変更は行わない**。q99 の値が複数 case で同一なのは shared null の同じ prefix（B_final 400）を共有するためで，observed 側（manifest の observed_hash・stored evidence）は case ごとに異なる。

## 3. Claude sandbox での照合（`d4c0_d2w_sandbox_verification.json`）
- zip 整合性（CRC）・path 安全性；published evidence 10 file の SHA／bytes 一致；**27 unit の manifest SHA＝登録 D-2 ledger unit**；全 bank identity が formal（K 2000・m 100・rows 200,000；f32 も 200,000）；registry SHA＝ledger；context record の束縛。
- **formal 復元**（`restore_w2_context(require_formal=True)`；配列なし・exact OT 再実行なし）：context SHA 一致・9 decision（trigger／state／B_final／checksum）一致（10.5 s）。
- 実行済み notebook：cell 0 以外の全 cell の source が承認 notebook（SHA `5a5260cf…`／`40f9b7e5…`）と同一；cell 0 の差分は lock 値（commit・inventory SHA）のみ。出力は本報告の数値と一致。
- 主張の範囲：技術的成功（intake 束縛・評価・publication・復元）。較正入力としての受入れ（登録）は本監査後。exact OT の独立再実行は sandbox では行っていない（登録環境ではない）。

## 4. 依頼
1. D-2W 正式実行（attempt `20261004T144349Z_cb8bc8e5f7`）の実行後受入れ（原本 SHA の固定；科学的結果は記録のまま）。
2. 受入れ後：**登録 tranche**——pseudo（commit `12980202…`・acceptance `08efa1d1…`）と D-2W（commit `f3aec793…`）の原本登録（`registered_assets/d4/pseudo/`・`registered_assets/d2w/`：各 attempt の lock／final／run record／log／NPZ／case・context record／acceptance／実行済み notebook；失敗 attempt `20261004T102439Z` は別建て），`PSEUDO_REGISTRATION`／`D2W_REGISTRATION` の充填，pins（4 項目），**registered loader の本体**（原本 bytes の SHA 認証・pins 照合・acceptance 束縛；`restore_w2_context` の `expected_context_sha256` は pins から）と拒否試験。各 attempt はそれぞれの execution lock で検証し，履歴 lock を書き換えない。
