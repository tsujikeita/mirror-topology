# A10 freeze procedure（先生向け・2026-09-12）
1. このフォルダを `mirror-topology/results/step1_phaseA/A10_freeze/` に置く（今回は追加ファイル不要：全成果物同梱）。
2. `cd results/step1_phaseA/A10_freeze` → `python build_freeze_manifest.py` → `cross-checks: 12/12 PASS` と `written … freeze_manifest.json`。
3. README の Frozen stages 表に下の 1 行を追加。
4. `git add results/step1_phaseA/A10_freeze README.md && git commit -m "Freeze Step 1 Phase A-10 v1.0 (A10 v1.2.9 A10_VALID 61/61; m=100; l2-4 float64 selection)"`
5. `git tag -a step1-phaseA-A10-freeze-v1.0 -m "Step 1 Phase A-10 freeze v1.0" && git push origin main --tags`（前回どおり 408 が出たら `http.postBuffer` 設定済みなら通るはず。合計 70 MB）。
6. push 成功の表示（`main -> main` と `[new tag]`）を送っていただければ，こちらで GitHub 側の commit hash を確認します。

README 追加行：
| **Step 1 A10** — W₂ estimator, orientation-cluster m, calibration pathway | `results/step1_phaseA/A10_freeze/MirrorTopology_Step1_A10_v1.2.9.ipynb` | `results/step1_phaseA/A10_freeze/A10_rules_v1.0.md` | `step1-phaseA-A10-freeze-v1.0` | **FROZEN** (design/estimator; global calibration & final W₂ threshold not frozen) |
