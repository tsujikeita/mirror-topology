# Phase B・B-3-0 第 1 回 Colab 実行の結果と v0.5（harness 1 箇所修正）
2026-09-17。Claude作成。

## 1. 第 1 回 Colab 実行（commit `27c3b022…`，run `20260917T042949Z`）
| 段階 | 結果 |
|---|---|
| launcher lock・checkout・inventory／pins／script／test SHA | すべて一致 |
| 環境 lock | **OK**（Python 3.13.15／NumPy 2.1.3／SciPy 1.16.3／healpy 1.20.0／POT 0.9.7.post1／CAMB 2.0.4） |
| smoke script | **16/16 gate True・script B3_0_PASS=True**（T19：等方 engine vs A5 null 4 条件内；T10：層別＝literal bit 一致・prefix/extension 対照；mock 評価 technical ok；checkpoint 往復） |
| 実資産 pytest（39 node） | **38 passed / 1 failed**：`test_legacy_kernel_bit_identical_to_frozen_notebook_cell` |
| 最終 B3_0_PASS | **false**（pytest 不合格による合成；設計どおり） |

失敗原因：凍結 A10 notebook の A10a セル prefix は実行環境を `os.path.exists('/content')` で Colab と判定し `google.colab.drive.mount` を呼ぶ。pytest の subprocess には IPython kernel がないため `google/colab/_ipython.py` の `get_ipython().kernel` で `AttributeError`。**engine の数値・凍結 kernel との不一致ではなく，対話セルの prefix を headless で実行したことによる環境 artefact**（sandbox には `/content` が無いので顕在化しなかった）。bit 一致の比較自体（scan／generate）には到達していない。

## 2. v0.5 の修正（test harness 1 箇所のみ；engine・pins・script・notebook は不変）
`tests/test_b2_tranche23.py`：`/content` が存在し**かつ live kernel が無い**場合に限り，`google.colab.drive.mount` を no-op stub に置換して凍結 prefix を実行（凍結セルの bytes は不変で SHA を assert；置換の有無を `_HARNESS_DRIVE_MOUNT_STUBBED` として namespace に記録）。mount は bit 一致の比較に無関係（資産は pinned repo clone から読む）。sandbox（`/content` なし）では stub は入らず 3/3 PASS。
- `__version__` 0.44.0，pins の `engine_version` と inventory を更新（inventory SHA **`f0dd1eab49216f82fffa10c1ed6d5f555a1a3ea4fadc6f6e5b85a99c544bd7a7`**）。packet checker failures 0。
- 第 1 回実行済み notebook を `regression_logs/` に保存（run manifest 等の `RUN/out/` 一式は先生の Colab 側にあります）。

## 3. 先生の作業
1. 本 packet（zip・報告書・第 1 回実行済み notebook）を ChatGPT へ：第 1 回実行の評価と v0.5 harness 修正の実行前受入れ。
2. GO 後：新しい `engine_phaseB_for_commit.zip` を展開して **commit（C'）**→ notebook cell 0 の `REPO_COMMIT` を新 commit に，`EXPECTED_INVENTORY_SHA256` を `f0dd1eab…` に書き換え → Colab で再実行（新 run directory が作られます）→ `RUN/out/` と実行済み notebook を監査へ。
