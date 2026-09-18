# Phase B・B-3-2 v0.5 起草報告（v0.4 実行前監査：R323-B/C 承認・R324-A/B の参考修正を採用）
2026-09-18。Claude作成。engine は `ckpt_persist.py` のみ改訂（監査の参考修正を精査のうえ採用；他 43 module・builder・A/B script・pins は科学的設定不変，`__init__` 0.52.0）。規則本文・spec v0.2・科学的仕様は不変。
**テスト 888/888 PASS**——7 chunk・JUnit XML 同梱（`regression_logs/b3_2_v0.5_pytest/`）；node 集合＝collect 集合・重複 0・failure/error/skip 0。監査の独立試験 20 件を `tests/test_audit_b3_2_v04_independent_chatgpt.py` として同梱（path 適応と notebook 名の v0.5 化のみ），既存 14 件は監査の強化版（1 件：公開前拒否・旧世代保持・LATEST 不変を要求）に差替え。

## 1. 対応
| ID | 内容 |
|---|---|
| R324-A 無効 snapshot の非公開 | `publish_generation` は **publish 前**（`inspect_local` の resumable）と**コピー後**（`stage_state(copied)`）の両方で再開不能なら例外を返し，作成中の世代を破棄して直前の正常世代と LATEST を保持；`verify_generation`／`restore_generation` も無効 stage を拒否。監査の対照（先行 stage 欠落・共通 identity 不一致で 3 回 publish）で元の正常世代・全 bytes・LATEST が不変 |
| R324-B complete の照合 | `verify_generation` が `complete`／`resumable`／`stage_reason` をコピー済み envelope から再導出して field 集合・bool 型まで照合（manifest の `complete` だけの改変を拒否） |
| §7 運用 | notebook v0.5：`.publish.lock` 残存時の運用（旧 publisher の停止確認後に手動整理，または新 `PERSIST_DIR`；無条件削除はしない）を明記；最終 record に **`backup_state`**（publish 回数・失敗数・最終世代・persistent_backup_ok）を数値 script の成功と分けて記録し，`B3_2B_PASS` が Drive 保存成功の証明ではないことを scope に明記；報告書の内外文面を同一に |

## 2. 検証
監査 20 件（前版 17/20）→ 20/20，強化版 14 件 14/14，実セル launcher 4 件，builder／persistence 4 件。sandbox 事情（凍結 A10 セルの pip・PEP 668）は前版と同じ環境変数で対応（code・test 不変）。

## 3. 先生の作業
packet を ChatGPT の実行前監査へ。GO 後：1 回 commit（inventory SHA `857b2f371b856d0dcdda6f87ef96b66fad752636d3599617e0fcb6af887753f4`）→ notebook A v0.2 → notebook B v0.5（`MODE='fresh'`）。
