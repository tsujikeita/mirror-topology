# Step1 Phase D-3 設計 v0.1（12 位置段階：追加 9 位置の共分散・PC-1 物理 clone 検証・12 位置 bank）
2026-09-24。Claude作成。前提：D-2 第 1 波 bank の integrity／f32 受入れ（外側 receipt `registered_assets/d2/d2_outer_receipt.json`），D-1 の 30 共分散，D-4 の driver／reader，Phase C 追補 §7 の使用前 gate（正式 12 位置 profile・PC-1）。本文書は設計であり数値を生成しない。**見込み：設計監査 1 往復 → 実装 2〜3 tranche → Colab 2 系統（共分散 ≈18 h・bank ≈26 h；分割）。**

## 1. 目的と規則上の位置
第 1 波（3 位置）で W₂ trigger が立った family×size は，登録 12 位置 manifest（B-3-2 A の `b3_2_twelve_assets.json`；family×size ごとの 12 観測位置＝第 1 波 3 点＋新 9 点）に拡張して family mixture を再評価する（rules §10）。較正は実観測と全 pseudo に同一手順で適用するため，**全 potential 12 位置 bank を正式較正前に固定**する（設計 v0.3 §2.2；実観測で family を選別しない）。対象：E2／E7／E8 × 3 size × 新 9 位置 ＝ **81 配置**（E1 は等質で対象外）。

## 2. 工程
| 段階 | 内容 | gate | 規模 |
|---|---|---|---|
| **D-3a 共分散** | 81 配置の production 共分散を D-1 と同じ登録生成器（A11 手順・pinned CMBtopology・x₀_CT=−r_obs）で生成し，D-1 と同じ intake（幾何 binding・run profile・環境・array SHA・PSD・root gate）；配置 ID は 12 位置 manifest の evaluation ID 規約（`registered_id_map` の 12 位置分岐）に従う | production 共分散 intake（既存） | 81 × ≈400 s ≈ 9 h（family 別 3 notebook） |
| **D-3a′ PC-1** | 新 9 位置 × 各 family×size について，A11 R2 の物理 clone 関係 C(g·r) = D(M) C(r) D(M)ᵀ を**新点で**検証：clone partner の共分散を別途生成し（81 件），登録 bridge（`t2b2_bridge`）の D(M) で照合（相対 Frobenius ≤ 登録許容；A11 と同じ判定）。旧 anchor の成功を転記しない。第 1 波 anchor（30 配置）の同診断も併記（設計 v0.3 §2.2） | **PC-1**（12 位置 bank の正式使用前） | 81 × ≈400 s ≈ 9 h |
| **D-3b 12 位置 bank** | 81 配置の評価 bank（4N₀・3 role・family latent 共有：evaluation group は family 単位なので第 1 波と同じ latent），fitting，W₂ position bank（81 位置；位置別 group を CRN 表に追加＝表 v2）；family reference は第 1 波のものを再利用（同 latent）；bank spec を 12 位置 wave として拡張（`wave_id` は同一，config_id 集合の拡張） | 正式 12 位置 profile gate・bank 生成器（既存） | 81 × ≈19 min ≈ 26 h（family×size の 9 notebook，各 ≈3 h） |
| **D-3c 検証** | D-2 と同じ read-only 検証器（accepted mode；ledger を 12 位置 run で拡張），f32 必須 subset は 12 位置には設けない（第 1 波の 4 配置で受入れ済み；12 位置は f64 のみ）——著者決定として明記し監査に諮る | — | family あたり ≈10 min |

## 3. 固定事項（実装前に確定）
- **CRN 表 v2**：w2_independent group を 81 位置分追加（30000+config_id；config_id は 12 位置 manifest の ID），evaluation／fitting group は不変（family 単位）。表 v1 の group は再採番しない（v1 の payload SHA を v2 に記録）。
- **bank spec v2**：configurations を 111（30＋81）に拡張，shard／batch／role／selection の規則は同一；必須 f32 subset は第 1 波の 4 配置のまま。
- **evaluation ID**：`registered_id_map` の 12 位置 ID（matched／native）を spec に記録し，第 1 波 ID と衝突しないことを検査。
- **PC-1 判定**：A11 R2 の許容（rel Frobenius ≤ 1e-10 相当）を pins に固定；不合格 size は「12 位置 bank を正式使用しない」（family 全体の technical_fail ではなく，当該 size の 12 位置分岐を position-unresolved 扱い——監査に諮る）。
- **容量**：81 配置 × ≈290 MB ≈ 24 GB（Drive 2 TB で問題なし）。

## 4. 表現の限定
D-3 は資産の生成と検証であり，較正・判定を含まない。12 位置 bank の生成は「trigger が立ったら使う」ための事前固定であり，全 family で 12 位置評価が行われることを意味しない。
