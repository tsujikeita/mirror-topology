# Phase B・B-3-1 control 電池 v0.3 起草報告（v0.2 実行前監査 R32-A/B/C・§8 の反映）
2026-09-17。Claude作成。engine 42 module のうち数値 kernel は不変（変更は `controls.py`（参考修正採用）・`__init__` 版 0.47.0）。規則本文・spec v0.2・科学的仕様は不変。**テスト 846/846 PASS**（最終 bytes 一括実行；監査の受入試験 15 件を `tests/test_audit_b3_1_v02_chatgpt.py` として同梱：path 適応のみ）。packet checker 140+ 項目一致・failures 0。

## 1. 対応（監査の参考修正 2 ファイルを精査のうえ採用）
| ID | 内容 |
|---|---|
| R32-A 率検査への TECH 伝播 | 各 pseudo の `rate_truth = support if technical_status=='ok' else TECH` を率集計へ渡し，元の support・technical_status・rate_truth を行ごとに記録（KDE CI の技術失敗を含む評価は技術行として不合格） |
| R32-B 実 resampler との照合 | 実 table 側は **`resample_hits`**，oracle 側は `literal_resample_hits` で再抽出整数和と確率を照合；plan の cluster 数不一致などで比較を省略した場合は合格にしない（gate False）；detector self-test に「全 0 を返す resampler」を追加 |
| R32-C conjunct の確定 False | drop case は **`is False` かつ technical_status=='ok'** を要求（unknown／TECH は不合格）；base 2 件の technical_status も確認；mutant 検知の比較先は登録判定器の確定 False |
| §8.1 docstring | script 冒頭を現実装（独立 negative・率検査の TECH 伝播・登録 0.35・実経路 brute-force・確定 False）に一致させた |
| §8.2 追補 | B-3-0 受入れ receipt（監査書名・run ID）と B-3-1 v0.2／v0.3 の履歴を追補 §D に追記（B 表の歴史的記述は保持） |
| §8.3 | 自己試験 manifest は最終 bytes（0.47.0）で再生成して同梱 |
| §8.4 診断の位置付け | 0.6 mock fixture は「科学的 label は gate にしないが，技術異常（非有限・technical_fail・checkpoint 失敗）は全体を止める」方針を docstring に明記 |
| §8.5 | negative の logD 短絡は support 率の評価に限定（unsupported を含む全 core 判定の再現ではない）と明記 |

## 2. sandbox 自己試験（scale 0.1；PASS は発行しない）
21 gate のうち `G_env_lock` のみ False（48 s）。率検査：n=200・c=0・u=0・technical=0（各行に rate_truth を記録）；brute-force：実経路一致・detector（zeroed／permuted／zeroed resampler）検知；conjunct 電池 ok；登録 positive strong。

## 3. 先生の作業
packet を ChatGPT の実行前受入れへ。GO 後は前回と同じ手順で commit（inventory SHA は監査後に確定）→ Colab 実行（見込み 20〜40 分）→ 出力 zip と実行済み notebook を監査へ。
