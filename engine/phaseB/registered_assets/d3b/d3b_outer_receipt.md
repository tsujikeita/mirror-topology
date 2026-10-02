# Phase D-3b 外側 receipt（配列検証付き受入れ）— `d3b_outer_receipt.json`（payload `7c42bc112a541336…`；pins `d3b_outer_receipt_sha256`）
2026-10-03。Claude 作成（著者側 receipt；外部受入れは ChatGPT の記録を参照）。JSON は `step1_engine.d3b_ledger.build_d3b_outer_receipt` による**登録記録からの決定論的再導出**であり，`verify_d3b_outer_receipt` が再導出との完全一致を要求する。

## 1. 束縛
| 対象 | identity |
|---|---|
| 生成 | commit `7b09c646b369…`（engine 0.93.0・inventory `4767847789a0…`・producer digest `39510da28c19…`）；ledger payload `a7d2c8c4375c…`／file `bdaa8aeb9b3e…`（**不変**；ledger 内の `array_acceptance` は生成時の記録 PENDING のまま） |
| metadata 受入れ | `Step1_PhaseD_D3b_all9_7b09c646b369_metadata_acceptance.json`（`461f75259418…`；PASS_WITH_EXPLICIT_SCOPE） |
| 検証 | commit `269c6d56fb75…`（engine 0.95.0・inventory `008e125c50d2…`・script `dc57de8ba8c2…`・notebook `5a556682d2df…`・module digest `f0a4ee17bf82…`）；実行前 GO `Step1_PhaseD_D3b_tranche2_v2_0.95.0_decision.json`（`48a0d3b14768…`） |
| 配列受入れ | `Step1_PhaseD_D3b_readonly_269c6d56fb75_acceptance.json`（`424a54712727…`）／`ChatGPT_audit_Step1_PhaseD_D3b_readonly_269c6d56fb75.md`（`237c68c61203…`）；入力 `d3b_verify_results.zip`（`80596237ff33…`）；**PASS_WITH_EXPLICIT_SCOPE（AUDITED_COLAB_FULL_ARRAY_INTEGRITY_RESULTS）** |

## 2. 9 partition（登録記録 `registered_assets/d3b/verify/<partition>/`・`verify_notebooks/`）
| partition | 生成 run id | unit / NPZ | 検証秒 | report SHA | final SHA | 実行済 notebook |
|---|---|---|---|---|---|---|
| E2_L1.00 | `20260930T010656Z` | 27 / 45 | 226 s | `e7064b4a1111…` | `46904a17019e…` | `2b7cae964d93…` |
| E2_L1.20 | `20260930T054800Z` | 27 / 45 | 294 s | `9b9a8adca0e9…` | `b4aad41a981b…` | `3dc89732f90a…` |
| E2_L1.50 | `20260930T080141Z` | 27 / 45 | 151 s | `a19715a1ea75…` | `838bc367572b…` | `d3d7f8974fbc…` |
| E7_L1.00 | `20260930T101421Z` | 27 / 45 | 289 s | `0fe53491989c…` | `02bef9f8f797…` | `8c06a69659ab…` |
| E7_L1.20 | `20260930T163102Z` | 27 / 45 | 280 s | `42ccc4dc2e55…` | `2f5bfe10cc46…` | `b84008791d31…` |
| E7_L1.50 | `20260930T191817Z` | 27 / 45 | 205 s | `92876ca788db…` | `15aef3b4d35a…` | `945d809b193c…` |
| E8_L1.00 | `20260930T213708Z` | 27 / 45 | 242 s | `9d6f3501db65…` | `fac56a94788b…` | `0711e7ef9daa…` |
| E8_L1.20 | `20261001T004059Z` | 27 / 45 | 148 s | `0593cbc014f2…` | `cc115752e392…` | `c4c6cc2dc96a…` |
| E8_L1.50 | `20261001T132201Z` | 27 / 45 | 193 s | `81fc9f363a01…` | `4f2f398b679e…` | `980cfe1c3004…` |

全 partition：accepted_full・accepted-run binding・coverage complete・all_ok・failures 空・**405 NPZ の実測 file SHA／bytes＝ledger**・全配列 SHA＝sidecar（`verify_twelve_bank_dir`）・cid 単調／一意数＝cluster 数・T1／T2 全て有限・partition 内 9 配置の cid 同一・**D-2 family reference（3 unit，ledger identity で再検証）との cid 同一**・N₀＋3N₀／N_fit 構造・verifier source／ledger bound。検証環境：Python 3.13.15・numpy 2.1.3・scipy 1.16.3・healpy 1.20.0・pot 0.9.7.post1（CAMB は不要・未記録）；順序非依存の環境 identity は 9 run で 1 値。計 243 unit・405 NPZ・27,217,472,580 B・2028 s。

## 3. 範囲
ACCEPTED (scoped): the 405 NPZ of the 81 added configurations were read in full on Colab by the accepted verifier at the verification lock and found identical to the registered expectations (file SHA / bytes / every array SHA / structure / cid correspondence incl. the fixed D-2 family reference); the acceptance is the auditor's scoped acceptance of these records, not an independent re-read. Consumption of the added banks as FORMAL inputs (d3_bank.intake_twelve_bank formal=True) is therefore allowed through the registered units; everything scientific downstream (real-bank profile / gate, plan fixation, calibration, labels) remains separately gated.

**不承認（受入れ文書の記載どおり）**：independent rehash of the 405 production NPZ by the auditor；raw latent R/z or generation-root comparison；real-bank twelve-position official profile / gate；fixed BootstrapPlan / FittingPlan identities；D-2W / noise / calibration / usable / observed labels / ENGINE_VALID。
