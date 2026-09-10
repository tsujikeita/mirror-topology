# A8 freeze procedure（先生向け・2026-09-11）
1. このフォルダを `mirror-topology/results/step1_phaseA/A8_freeze/` に置く。
2. Drive `mirror_topology/runs_step1_phaseA/a8_env_lock.json` を **`A8_freeze/a8_env_lock.json`** にコピー（SHA256 は `f62ec935…` のはず）。
   任意：A8a smoke の console log があれば `a8a/smoke/Console_log_of_smoke_A8a_featurestack_v1.1.2.txt` として追加。
3. `cd results/step1_phaseA && python A8_freeze/build_freeze_manifest.py A8_freeze`
   → `cross-checks: N/N PASS` と `written … freeze_manifest.json` が出る（欠落・不整合なら停止し，manifest は書かれない）。
4. README の Frozen stages 表に下の行を追加。
5. `git add results/step1_phaseA/A8_freeze README.md && git commit -m "Freeze Step 1 Phase A-8 v1.0 (A8a v1.1.2 FEATURESTACK_VALID, A8b v1.1.8 BENCHMARK_VALID)"`
6. `git tag -a step1-phaseA-A8-freeze-v1.0 -m "Step 1 Phase A-8 freeze v1.0" && git push origin main --tags`
7. `git ls-remote origin refs/tags/step1-phaseA-A8-freeze-v1.0^{}` の出力（archive commit）を私に送る。

README 追加行：
| **Step 1 A8** — hybrid ℓ≤16 feature stack (A8a) & scan benchmark (A8b) | `results/step1_phaseA/A8_freeze/MirrorTopology_Step1_A8a_featurestack_v1.1.2.ipynb`, `…A8b_scan_benchmark_v1.1.8.ipynb` | `results/step1_phaseA/A8_freeze/A8_rules_v1.0.md` | `step1-phaseA-A8-freeze-v1.0` | **FROZEN** (engineering; S2 scientific adoption HOLD) |
