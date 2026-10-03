# Phase D-3c 外側 receipt（正式 profile 実行の受入れ）— `d3c_outer_receipt.json`（payload `aca443d02d95af89…`；pins `d3c_outer_receipt_sha256`）
2026-10-03。Claude 作成（著者側 receipt；外部受入れは ChatGPT の記録を参照）。JSON は `step1_engine.d3c_ledger.build_d3c_outer_receipt` による**登録原本からの決定論的再導出**であり，`verify_d3c_outer_receipt` が再導出との完全一致を要求する。ledger `d3c_profile_ledger.json`（payload `8e5cd2dff074fdda…`／file `27a0334fb339e296…`；pins `d3c_ledger_sha256`）も同様に `build_d3c_profile_ledger` の再導出。

## 1. 束縛
| 対象 | identity |
|---|---|
| 実行 source | commit `7a2b17749e88…`（engine 0.99.0・inventory `c0b0333b2f42…`・script `9f243b08a5aa…`・notebook `4ad3ba0ac86f…`・pins `136d238f8489…`・D-3b ledger file `bdaa8aeb9b3e…`／receipt file `ed0fbccba739…`）；実行前 GO `D3c_tranche1_v3_0.99.0_audit_decision.json`（`ef2e7db0a381…`；PASS_WITH_EXPLICIT_SCOPE_AND_LOCKED_EXECUTION_GO） |
| 入力 | D-2 の受入れ済み run（family ごと；`d2_generation_ledger.json`）と D-3b の配列受入れ済み 9 partition（`d3b_generation_ledger.json` payload `a7d2c8c4375c…`・outer receipt `7c42bc112a54…`）；launcher は `/content/stage` に 1 回複製（bytes／配列 SHA の再検証は script 内） |
| 受入れ | `D3c_profile_runs_7a2b1774_acceptance.json`（`de8fa49f40a8…`；16 559 B）／`ChatGPT_audit_D3c_profile_runs_7a2b1774.md`（`426c3361a5d0…`）；入力 packet `D3c_profile_runs_7a2b1774_audit_packet.zip`（`775683fd20ca…`）；**PASS_WITH_EXPLICIT_SCOPE__TRANCHE2_REGISTRATION_IMPLEMENTATION_GO**（AUDITED_COLAB_OFFICIAL_PROFILE_EXECUTION_RECORDS_AND_INDEPENDENTLY_REPRODUCED_PLAN_IDENTITIES：監査側で 3 family の plan identity を正式規模（B 2000・B_KDE 2000・45 配列）で独立再構築） |
| 登録原本 | `registered_assets/d3c/runs/<F>_<attempt>/`（7 file；inner archive `archives/d3c_profile_<F>_7a2b17749e88.zip` の member と byte 一致）・`notebooks/`（実行済 3）・`acceptance/`（受入れ JSON／md・実行前 GO JSON）。**engine／pins の版が変わっても書き換えない**（実行 source は module 定数 `EXECUTION_LOCK`） |

## 2. family ごとの identity
| family | attempt | plan identity | ordered UID SHA | fingerprint matched／native | profile record | plan document | inner archive | peak RSS MB |
|---|---|---|---|---|---|---|---|---|
| E2 | `20261003T083353Z_dc4ddf4f0f` | `86a7db7b4aa31d17…` | `00e8c1c0c3dfebdb…` | `9e4d3dfb9b178ce5…`／`ad872efdc6f84687…` | `a0867c86b05c4c47…` | `d129a51ffadac594…` | `4cd9a8d0f3e6f045…` | 19417 |
| E7 | `20261003T090646Z_106fe1bd17` | `3c28d3eb66042436…` | `8972c1c7c4b61dd2…` | `06634d33e749754e…`／`08a6ddb9bc9dd8b1…` | `86926ff662c7cb22…` | `9bc5975f24875e35…` | `4783fc1f0eac2e83…` | 19466 |
| E8 | `20261003T093536Z_cb05343c01` | `d239ad9d39da8a0d…` | `079eac01371ccfae…` | `8ea1486c3b296e0f…`／`2a5704c44fe96cc2…` | `248616bbb4911237…` | `9bc84ac87b58af51…` | `49b6591d5c8d0228…` | 19427 |

全 family：REQUIRED 18 gate 全 True・official gate（mode official・`live_collected`）passed・profile checks 330／330・twelve checks 14／14・`full_surviving_scope=True`・供給 72（第 1 波 18＋追加 54；manifest＝spec v2／D-3b ledger／family reference）・UID K0 10 000／K1 30 000／m 100／K_fit 2000・B 2000／B_KDE 2000／seeds 5／master_seed 20260912・fingerprint gate 前後一致・plan object 共有・precheck／prelaunch の live source＝lock・stderr 空・退避 record なし。合計：script 2715 s・launcher 4348 s・peak RSS 最大 19466 MB（RAM 54.75 GB）。

## 3. 消費（D-4 較正）の契約
`intake_registered_d3c_profiles(root, ctx)` → `D3cProfiles`（ledger＋receipt＋pins 束縛・D-3b 受入れ receipt の一致を要求）。consumer は `rebuild_registered_plans` で登録 ordered UID から plan を**再構築**し受入れ identity の再現を要求され，`verify_consumer_inputs`／`verify_consumer_family_inputs` で両 system の fingerprint・plan identity・plan object（任意で gate record の inventory）を照合される。PASS flag・attempt id・旧成功 record は identity の代わりにならない。

## 4. 承認していないもの
tranche ② API 自体の受入れ（本 packet の監査で判断）・D-4 較正の実行・閾値／label／較正／D-2W／noise／ENGINE_VALID・E1 の 12 位置 profile・監査側での production NPZ の再読込み・remote Git tree の全面比較。
