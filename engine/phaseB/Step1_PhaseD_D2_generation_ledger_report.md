# Phase D-2 生成 ledger（4 family 完了）と実行後検証の準備
2026-09-24。Claude作成。engine `step1_engine 0.79.0`（数値 kernel は 0.54.0 基盤の継承；変更は `d/d2_verify_banks.py`・`d/MirrorTopology_Step1_D2_verify_v0.1.ipynb` の追加と `registered_assets/d2/` の登録；生成 script・bank 関数・CRN 表・spec は 0.78.0（commit `8b5e6102…`）と同一）。

## 1. 生成 run の記録（`registered_assets/d2/d2_generation_ledger.json`）
| family | run id | 配置 | directory | NPZ（GB） | script 秒 | A10 max rel | 環境 fingerprint | 監査 |
|---|---|---|---|---|---|---|---|---|
| E1 | 20260923T063210Z | 3 | 12 | 20（1.24） | 3,822 | 0.0 | a99b9015… | metadata 受入れ |
| E2 | 20260923T092030Z | 9 | 39 | 59（3.36） | 8,593 | 0.0 | a99b9015… | metadata 受入れ |
| E7 | 20260923T125656Z | 9 | 39 | 59（3.36） | 9,190 | 0.0 | a99b9015… | metadata 受入れ |
| E8 | 20260923T174910Z | 9 | 39 | 59（3.36） | 9,267 | 0.0 | 8130927a… | metadata 受入れ |
合計：30 配置・27 W₂ 位置・129 directory（全て新規生成・再利用 0）・197 NPZ・11.3 GB・30,872 s（8.58 h）。source lock：commit `8b5e6102f0088afbf69b10aaa9e90af4a63e07e2`，inventory `3523d233…`，producer digest 4 family 共通 `9ed095c5…`。各 family の final record・registry・run manifest・launcher lock・全 COMPLETE／sidecar（NPZ 以外）を `registered_assets/d2/<family>/` に登録（4.2 MB）。
E8 の環境 fingerprint は BLAS pool の列挙順と OpenCV 付随 library の path の差（必須版・thread 上限は同一）で他 3 family と異なる。監査の指示どおり**両 identity を保持し，alias や互換免除は発行しない**（exact-fingerprint の reuse 検査は記載どおり適用）。

## 2. 未了（受入れ JSON の `not_completed` を踏襲）
NPZ 実配列の独立数値受入れ（file／member SHA・shape・有限性・T1/T2/AX/PL/cid），生成時 model root の数値比較，必須 f32 感度（near-tie・Event B mismatch・axis/plane flip）の実測受入れ，実 case W₂（whitening／OT／stop／B_final／trigger）と外部 context の正式再利用，正式 bank 資産の外側 receipt と固定 plan，D-3・PC-1，noise，正式較正・usable・label・ENGINE_VALID。

## 3. 実行後検証（read-only；`d/d2_verify_banks.py`・`d/MirrorTopology_Step1_D2_verify_v0.1.ipynb`）
Drive 上の family 出力を受入れ済み commit の engine で読取り専用に検証し，小さな JSON を出す：全 directory の `verify_bank_dir`（bytes・identity・member 集合・dtype・有限性・cid・範囲・UID・key），**NPZ file SHA の再計算**と registry／final record の照合，role×selection の配列統計（mean／std／min／max・AX／PL histogram），必須 f32 subset（batch 0）と W₂ bank の paired 感度——凍結 kernel では f32 は **selection（argmin）にのみ**影響し T1/T2 は選ばれた軸で f64 評価されるため，指標は axis／plane flip 率・flip 行の |ΔT|・near-tie 数——，同 latent 不変量（batch ごとの cid 構造）。Drive は変更しない。sandbox 自己試験（E7 30101・scale 0.003・実 kernel）：7 directory 全 ok，W₂ 600 行で flip 0。見込み：family あたり 10〜20 min（保証ではない）。

**テスト 1270/1270 PASS**（9 chunk・JUnit 同梱 `regression_logs/d2_ledger_pytest/`；node 集合＝collect・重複 0・failure 0；sandbox 初期化後に pinned CMBtopology `0cc65e34` と依存を再導入して実行）。追加テスト `tests/test_d2_verify.py`（検証 script の契約：全 directory 検証・NPZ SHA 照合・f32／同 latent 記録・入力不変・改変 NPZ の directory 単位失敗と exit 1）。

先生の作業：本 packet を commit（ledger と検証 notebook の登録）→ ChatGPT へ「D-2 生成 ledger と実行後検証 notebook の事前確認」→ GO 後に E1→E2→E7→E8 の順で検証 notebook を実行（各 family の `RUN_ROOT` を指定；出力は数百 KB の zip）→ 4 family の検証 zip を ChatGPT の配列数値監査へ。
