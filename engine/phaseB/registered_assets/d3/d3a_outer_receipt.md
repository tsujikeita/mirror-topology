# D-3a outer receipt（著者側；外部受入れは ChatGPT を参照）
2026-09-29。Claude 作成。PC-1 の受入れではない（受入れは外部監査）。

生成器：commit `fe7c201ef265ddf614ed7d538acd3197eaa331c0`（engine 0.86.0，inventory `2cc5668a6768…`，script `6db2f9e11635…`，pins `7dfc77329c4f…`，notebook `6444a32022a7…`）。実行前 GO：Step1_PhaseD_D3_tranche2a_v5_decision.json (ChatGPT GO for execution of commit fe7c201e)。
ledger：`registered_assets/d3/d3a_generation_ledger.json`（`26bf552fdf41…`），coverage：`8a55452dbbbf…`。

| partition | runtime | run_id | 秒 | base | PC-1 case | max rel | configuration PC1_PASS/FAIL | NPY |
|---|---|---|---:|---:|---:|---:|---|---:|
| E2/L1.00 | standard | 20260926T074141Z | 8872 | 9 | 12 | 4.50e-08 | 12/0 | 21 |
| E2/L1.20 | standard | 20260926T135737Z | 9092 | 9 | 12 | 3.30e-08 | 12/0 | 21 |
| E2/L1.50 | high_memory | 20260928T001131Z | 3187 | 9 | 12 | 2.18e-08 | 12/0 | 21 |
| E7/L1.00 | standard | 20260926T174854Z | 8650 | 9 | 12 | 8.35e-08 | 12/0 | 21 |
| E7/L1.20 | standard | 20260927T020217Z | 8480 | 9 | 12 | 7.36e-08 | 12/0 | 21 |
| E7/L1.50 | standard | 20260927T061528Z | 9047 | 9 | 12 | 6.09e-08 | 12/0 | 21 |
| E8/L1.00 | standard | 20260927T084859Z | 13812 | 9 | 24 | 8.29e-08 | 12/0 | 33 |
| E8/L1.20 | standard | 20260927T124831Z | 14302 | 9 | 24 | 7.28e-08 | 12/0 | 33 |
| E8/L1.50 | high_memory | 20260928T113755Z | 5426 | 9 | 24 | 5.28e-08 | 12/0 | 33 |

合計：family 3・partition 9・base 81・case 144（新規 108・anchor 36）・PC1_PASS 108・PC1_FAIL 0。

未完 attempt（削除せず保持）：
- `d3_E2_L1.50_fe7c201ef265_audit_INCOMPLETE_rc-9`：E2/L1.50，標準 runtime で rc −9（OOM は著者側の推定；kernel の OOM 記録・peak RSS はない）；完走 run `d3_E2_L1.50_fe7c201ef265_audit_High_Memory` が partial evidence 9 件を bit 同一に再現。
- `d3_E8_L1.50_fe7c201ef265_audit_INCOMPLETE_rc-9`：E8/L1.50，標準 runtime で rc −9（OOM は著者側の推定；kernel の OOM 記録・peak RSS はない）；完走 run `d3_E8_L1.50_fe7c201ef265_audit_High_Memory` が partial evidence 30 件を bit 同一に再現。

著者側検証：
- verify_partition_run(require_arrays=True, expected_run_manifest_sha256=<ledger>) x 9 (all pass)
- aggregate_partitions x 3 families (coverage complete, arrays verified, ledger bound)
- mapping-free independent PC-1 recomputation from the 225 NPY files (144 unordered matched pairs = all cases; max rel 8.35e-8; no unmatched file)
- executed notebooks: only the parameter cell differs from d/MirrorTopology_Step1_D3a_covgen_v0.2.ipynb (11/11)
- incomplete attempts reproduced bit-identically by the completed High-RAM runs (39 covariance identities, 21 rel values)

外部：metadata 受入れ＝E2/L1.00（2026-09-26）および全 9 partition（`Step1_PhaseD_D3_all9_fe7c201ef265_metadata_acceptance.json`，2026-09-29，PASS_WITH_EXPLICIT_SCOPE；run manifest SHA 9 件・notebook SHA・環境 fingerprint は本 ledger と一致；NPY 読込み 0/225）；配列検証付き受入れ＝`Step1_PhaseD_D3a_array_acceptance_20260929.json`（2026-09-29，範囲付き PASS：225 配列・144 case の PC-1 独立再計算・3 family の配列付き集約）；0.87.0 packet＝`Step1_PhaseD_D3a_completion_0.87.0_decision.json`（データ・履歴受入れ／新 intake HOLD）；0.88.0 v2＝`Step1_PhaseD_D3a_completion_v2_0.88.0_decision.json`（HOLD 解除・登録 intake 受入れ PASS；commit `861ea95c…`）。

本 receipt が主張しないこと：PC-1 acceptance (external)；12-position covariance receipt / plan-schema binding (tranche 2b)；D-3b bank generation。
