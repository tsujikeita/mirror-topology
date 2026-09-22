# Phase D-2 tranche ① v2 報告（監査 RD2T1-A/B の反映）
2026-09-22。Claude作成。engine `step1_engine 0.68.0`（数値 kernel は 0.54.0 基盤の継承；追加は `d2_rng.py`＝module 47 と `d/d2_crn_table.json`；`LegacyKernel.generate` と旧 seed 配線・旧再現試験は不変）。設計 v0.2（監査で方針受入れ）§A–C と監査 §3–4 の受入れ条件に対応。v1 監査（正常経路＝表・fresh replay・4 role 同一 latent・2 batch・配置別 native root・旧経路との bit 一致は確認）の 2 領域を，監査の参考補強（`d2_rng.py` 1 file）を精査のうえ採用して修正：**RD2T1-A** 生成要求の事前検査（K／m／chunk の正の非 bool 整数，group／wave／batch／config の厳密整数，許可 batch と容量（10,000／30,000 cluster）超過の事前拒否，非空・重複なしの selection，有限な**実数** root——未初期化出力や row／UID 不一致を返さず，数値処理前に拒否）；**RD2T1-B** 表の復元時に payload SHA だけでなく実 scope の標準化内容で重複検査，label／scope／行 wave／表 wave／purpose の整合，canonical な整数 group key（`"01003"` 等を拒否），W₂ の family／size／config 対応と E1 除外，固定 N₀／N_max／m／batch／chunk が adapter 定義と一致，復元前後の group 数保持。表の bytes・group 整数・seed・数値 loop・kernel は不変。監査の独立対照 62 件を `tests/test_audit_d2_tranche1_review_chatgpt.py` として同梱（path と出力先の適応のみ；62/62）。表の識別値：payload SHA `60d9941a…`（`table_sha256`）と file SHA `99b68d8e…` を区別する。**テスト 1058/1058 PASS**（9 chunk・JUnit 同梱 `regression_logs/d2_t1v2_pytest/`；node 集合＝collect・重複 0・failure 0）。本 tranche は表・adapter・契約試験であり，bank 生成器（②）・強い intake と供給（③）は次 tranche。

## 1. 成果物
| 物 | 内容 |
|---|---|
| `d/d2_crn_table.json`（SHA `60d9941a…`，44 group） | scope→`crn_group_id` の**保存表**（実行順で採番しない；生成順を変えても同じ SHA）：evaluation（wave, family）1001–1004，fitting（wave, family）2001–2004，**w2_independent（wave, family, size, config_id）＝27 位置に 1 group ずつ**（30000+config_id），w2_crn（wave, family, size；予約）4021–4043。全 purpose・wave で整数一意；batches `{0:[0,1e6), 1:[1e6,4e6)}`・N₀・N_max・m・chunk を表に固定；MASTER_SEED は登録値 20260912 |
| `d2_rng.load_crn_table` | schema／SHA／scope 重複／w2 位置欄の検査後に `CRNRegistry` を復元（再採番なし）；`group_for` は scope から一意に引く（W₂ は size と config_id を必須） |
| `iter_latent` | **latent replay**：正式 key `(MASTER_SEED, wave, purpose_id, group, batch, stream)` の rotation／gaussian の **新しい Generator** を初期状態から固定 chunk 順に消費（`registry.stream(reuse=True)` の同一 object＝続きの列を「同じ latent」とは扱わない） |
| `generate_from_latent` | 同じ latent block（R・z）を全 root（4 role）・全 selection で走査；`kernel.D_batch`／`kernel.scan` を無変更で使用；ClusterUID（wave, purpose_id, group, batch, rotation_index within batch）を返す |
| `native_reference_root` | ref_native＝diag(√c_l,j^CT を 5/7/9 成分へ反復)；配置の `c_ct`（D-1 intake，full precision）から；ref_matched は固定 C_iso の principal root（family 内共有） |

## 2. 契約試験（`tests/test_d2_tranche1.py` 4 件）
1. **表**：決定性（scope 順を変えても SHA 一致；同梱表と一致），44 group 一意，復元，W₂ の位置別 group（同 family・size の 3 位置が別 group），位置指定なしの W₂ 引きを拒否，重複 scope（stale SHA でも再 stamp でも）を拒否，E1 の W₂ 登録を拒否。
2. **latent**：同 key の replay で R／z 一致；別 purpose（fitting）・別 batch・別 W₂ 位置で別 latent；live generator の続きは同 latent ではなく，key からの再作成が最初の標本と一致。
3. **root／batch／UID**：native 参照の対角構造（5/7/9 反復）と負値拒否；batches の登録値；UID の rotation_index が batch 内；`ConfigBank` の N₀／N₄ view と 3 batch の拒否。
4. **数値経路**：正式 key の latent block を旧 `LegacyKernel.generate` に注入（回転は再直交化なしの同一行列）した出力と `generate_from_latent` が **f64／f32 selection とも T1/T2/AX/PL で bit 一致**；f32 selection でも T1/T2 は float64。

## 3. 未了（tranche ②③・実行前監査）
生成器本体（配置単位の生成・shard 保存・fresh attempt／完成 cache・partial 記録・登録環境と source gate），`intake_registered_bank`（読込み時全再検査）と `BankSupply`／plan schema の固定，f32 必須 subset の ID 固定，W₂ position bank（登録 μ/W），pseudo 列の担当工程，小規模計時による見積り。
