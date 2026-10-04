# Phase D4C-0 外側 receipt（pseudo 列と D-2W 9 case の正式実行の受入れ）— `d4c0_outer_receipt.json`（payload `d6926b94dcb1bede…`；pins `d4c0_outer_receipt_sha256`）
2026-10-05。Claude 作成（著者側 receipt；外部受入れは ChatGPT の記録を参照）。JSON は `step1_engine.d4c0_registry.build_d4c0_outer_receipt` による**登録原本からの決定論的再導出**であり，`verify_d4c0_outer_receipt` が再導出との完全一致を要求する。ledger `d4c0_ledger.json`（payload `8c0d39f98401718e…`／file `f018f77b4bc89c2d…`；pins `d4c0_ledger_sha256`）も同様に `build_d4c0_ledger` の再導出。

## 1. 束縛（2 つの run はそれぞれ自身の execution lock に束縛；登録版（engine 0.105.0）の値は原本に書き込まない）
| 対象 | identity |
|---|---|
| **pseudo（D4C-0b）** attempt `20261004T102334Z_6e681d78a0` | commit `12980202ee11…`・engine 0.103.0・inventory `f04e739d79bb…`・script `a6e0772ae62c…`・pseudo 表 file `31fc50c310be…`／table `88f5659e1cc3…`・pins `a3d90b81745b…`・lock `4b31d9efa65d…`；inner zip `57c0df458eb0…`（7 member）；実行済み notebook `fb7a0d663694…`；NPZ `c62a965b3b64…`（145,444 bytes）；列 identity paired `c9f75cdb86c9…`（T1 `6e2669b52944…`・T2 `1a5588fd8dc3…`・AX `60d61625987b…`・PL `85a035007b2f…`・cid `55f385cf2332…`・uids `cb90d89c16d8…`）；root `390dbfaca62d…`；rng keys (20260912,1,400,5001,0,{1,0}) |
| **D-2W（D4C-0a）** attempt `20261004T144349Z_cb8bc8e5f7` | commit `f3aec7935845…`・engine 0.104.0・inventory `49976b3e24e2…`・script `dcd64283d87e…`・D-2 ledger file `07574dfa58dc…`・shared-null asset file `cc67686744f5…`・pins `de1794b592c1…`・lock `9f01508a898f…`；inner zip `13e222e57d62…`（16 member）；実行済み notebook `3d8a7ff7519e…`；context `50ec5a54d593…`；9 case（manifest／result SHA・decision は ledger 定数）；27 unit の manifest＝登録 D-2 ledger；3 family の registry bytes＝ledger `bank_registry_sha256` |
| 失敗 attempt（別建て・不変） | `20261004T102439Z_9bac8f8730`（commit `12980202…`，engine 0.103.0；stage `inputs`；zip `09f9ab0e8ade…`，6 member）——success source としては決して使わない |
| 受入れ | pseudo：`D4C0_pseudo_12980202_acceptance.json`（`08efa1d19b29…`；PASS_WITH_EXPLICIT_SCOPE__PSEUDO_ORIGINAL_COLUMNS_ACCEPTED_FOR_REGISTRATION；pins `pseudo_acceptance_sha256`）＋補足（`ChatGPT_audit_D4C0_runs_12980202_and_v3_0.104.0.md`・`D4C0_v3_0.104.0_audit_decision.json`）；D-2W：`D4C0_D2W_f3aec793_acceptance.json`（`c9506e0b17f7…`；PASS_WITH_EXPLICIT_SCOPE__D2W_FORMAL_RUN_ACCEPTED__REGISTRATION_DRAFTING_AND_TESTS_GO；pins `d2w_acceptance_sha256`）＋`ChatGPT_audit_D2W_run_f3aec793.md` |
| pins（`d/d3_pins.json`） | `d4c0_ledger_sha256`・`d4c0_outer_receipt_sha256`・`d2w_acceptance_sha256`・`pseudo_acceptance_sha256`・`d2w_context_sha256`・`pseudo_paired_sha256`・`pseudo_npz_sha256`（登録 load はすべての pin の存在と定数との一致を要求；wrong／missing／null は拒否） |

## 2. 科学的結果（記録のまま；受入れの条件ではない）
valid（trigger False）：E2/L1.00・E2/L1.50・E7/L1.00・E8/L1.20・E8/L1.50；w2-unresolved（trigger unknown）：E2/L1.20（B_final 800）・E7/L1.20（600）・E7/L1.50（400）・E8/L1.00（400）；技術 FAIL 0。unknown は W₂ branch の未決であり，技術 FAIL でも False でもない。D-4 は pseudo ごとの event-ratio branch と登録 12 位置段階の完了と組み合わせて eligible truth を作る（W₂ の状態だけで pseudo 行を無条件に mark／破棄しない）。

## 3. 消費 API
- `w2_cases.load_registered_w2_context(root, ctx)` → `d4c0_registry.load_registered_w2_context`：pins guard → ledger／receipt の再導出一致 → 9 原本 case record の bytes 認証 → `restore_w2_context(expected_context_sha256=pins['d2w_context_sha256'], require_formal=True)`（stored evidence の replay；exact OT 再実行なし）→ 9 decision＝定数。
- `d4_pseudo.load_registered_pseudo_columns(root, ctx)` → `d4c0_registry.load_registered_pseudo_columns`：pins guard → 原本 NPZ bytes 認証（`pseudo_npz_sha256`）→ `verify_pseudo_columns` を定数 identity・登録 pseudo 表で実行 → paired SHA＝pin。再生成値・許容幅同等物は受け入れない。

## 4. 資源の記録（当該実行の実測；一般化しない）
pseudo：script 16.8 s・launcher 19.3 s・peak RSS 1.32 GB（RAM 13.6 GB）。D-2W：script 838.2 s（評価 731.0 s）・launcher 874.1 s・peak RSS 2.31 GB・staging 303,031,554 bytes。

## 5. 範囲
本 receipt は登録原本の受入れ（監査の実行後受入れ 2 件）の記録であり，正式 global 較正・usable・target・label・noise・partial／combiner・ENGINE_VALID の承認ではない。
