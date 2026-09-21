# Phase D-4 完了／引渡し記録（実装・接続の受入れ範囲と未了の使用前 gate）
2026-09-22。Claude作成。engine `step1_engine 0.66.0`（数値 kernel は受入れ済み基盤 0.54.0＝handoff commit `1db30cd1…` と同一）。

## 1. 受入れ済みの範囲（監査：tranche 1 v3・tranche 2 v6）
| 項目 | 実装 | 受入れの性質 |
|---|---|---|
| D4-3 統合 runner の登録 asset 再利用 | `run_first_wave(..., twelve_assets_receipt=)`：receipt 束縛 intake を通過した登録 asset を再生成なしで使用（生成器 0 回） | 実装・接続（人工 bank） |
| D4-5 production 共分散 intake 入口 | `production.intake_registered_covariance`：D-1 receipt／registry の**固定 SHA**・source-bound spec・凍結 loader／bridge の実 path＋SHA・sidecar・幾何・array SHA・PSD・principal root を読込み時に全再検査 | 実装・接続（実 D-1 配列で正常経路） |
| D4-2 pseudo 側完全 archive | 各 pseudo の 12 位置 Result＋parent・plan・position source・manifest を content-addressed に保存 | 実装・接続 |
| D4-4 外部参照の再利用契約 | `run_reader.verify_run_references`：run manifest の payload・stage schema・二重 source binding・registry／12 位置 manifest の復元検証・family／12 位置／pseudo／case 診断 record の共通数値 validator・coordinator 復元・**position source と検証済み parent の数値対応**・完了／eligibility／較正の再導出・登録 W₂ context・sealed order record | 実装・接続（人工 bank・試験用 W₂ context） |
| D4-1 較正先行 driver | `calibration_first`：commitment→封印較正（target なし）→開示→target 評価；依存 snapshot の全項目一致・封印 record の鎖検証を target 評価前に実施；official は driver 経由のみ（全 family＋固定 2000 pseudo） | 実装・接続 |

**受入れの限定**：上記は sandbox の人工 bank・試験用 W₂ context・凍結 loader を用いた**接続契約**の受入れであり，正式 D-2 生成，実 bank の case 別 W₂（stop／B_final／trigger），外部 W₂／context の正式再利用受入れ，PC-1 物理 clone，noise，全 family・固定 2000 pseudo の正式較正，calibration usable，実観測 label 解放，ENGINE_VALID は含まない（追補 §7 の使用前 gate のまま）。

## 2. 試験の出所（監査 v6 §6 の訂正）
`test_position_source_numbers_must_match_verified_parent`（自作）は P/hits・swap・N/hits・precision の **4 種類**の対照を含む。stage 変更と「未完 branch の unknown 減少」の分岐対照は，監査が独立に再実行した**前回原本 16 件**に含まれ，今回 source で正常に拒否された。したがって「自作回帰 4 種類＋監査原本で stage／分岐を含めて確認」が正確な整理である（前版報告の「6 種を再現」は訂正）。

## 3. 監査履歴（tranche 2）
v1 HOLD（RD4T2-A/B/C/D）→ v2 HOLD（R2V2-A/B/C）→ v3 HOLD（R2V3-A/B）→ v4 HOLD（R2V4-A/B/C；参考修正採用）→ v5 HOLD（R2V5-A；参考修正にも残っていた漏れ）→ **v6 受入れ PASS**。各版の inventory SHA：`9e395c60…`／`b0316b9f…`／`f7f76efb…`／`31e4d587…`／`73cc3818…`／`c47103e8…`。

## 4. 次工程
D-2（第 1 波 bank 生成器）の設計 v0.1 を別文書に起草（`Step1_PhaseD_D2_design_v0.1.md`）。実行前監査 → commit → Colab（8〜10 h・分割・再開可能）→ 実行後監査。
