# Phase B・B-3-0 smoke v0.4 起草報告（v0.3 実行前監査 R03-A/B の反映）
2026-09-17。Claude作成。engine 41 module・科学 pins・`b3_0_smoke.py` の計算部は不変（script は docstring の版表示のみ v0.3 に更新；`__version__` は `0.43.0` のまま）。監査提供の候補 notebook（2 セル差分）を精査のうえ採用。

## 1. 対応
| ID | 内容 |
|---|---|
| R03-A pytest の名前空間 | collect-only と本実行の双方に `--rootdir PHASEB` を指定（node 名が `tests/...` 形式で期待集合と一致）；収集 stdout/stderr を保存し **collection returncode==0 を必須**；JUnit の成功判定を `failure/error/skipped` 子要素の有無で行う（system-out／properties は不合格の証拠にしない）；testcase 数と期待集合数の一致を要求（重複を set で隠さない）。本環境（実資産あり）で notebook セルの論理を実行し **期待 39・実行 39・成功 39・collection rc 0** を確認 |
| R03-B 最終 PASS | `script_ok = (rc.returncode == 0 and rm.get('B3_0_PASS') is True)` と pytest_ok の合成で最終 PASS；script returncode・保存 record の passed・collection rc を final record に個別保存（stale の成功 record が今回の失敗を上書きしない）；早期失敗 record（execution_profile 欠落）でも KeyError なく False と理由を保存 |
| 表示 | script docstring の版表示を v0.3 に更新 |

inventory（`b3_sha256`）を notebook の新 bytes で更新；packet checker 133 項目一致・failures 0。sandbox 自己試験は前版と同じ（`G_env_lock` のみ False・stage complete）。

## 2. 先生の作業
1. packet を ChatGPT の実行前受入れへ。
2. GO 後：`phaseB/` を `engine/phaseB/` として **1 回 commit** → commit C と inventory SHA を notebook cell 0 に記入 → Colab 実行 → `RUN/out/` を監査へ。
