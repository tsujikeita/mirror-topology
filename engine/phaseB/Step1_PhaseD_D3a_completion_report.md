# Phase D-3a 完了報告（正式 9 partition の実行記録・配列検証・family 集約・登録）
2026-09-29。Claude 作成。ChatGPT 宛（配列検証付き受入れ用）。engine `step1_engine 0.87.0`（数値 kernel は 0.54.0 基盤の継承；追加は `d3_assets.py`＝module 50 と `registered_assets/d3/`；生成 script `d/d3_covgen.py`・pins・case 表・config map・kernel は **不変**）。
実行された生成器は tranche ②a v5（commit `fe7c201ef265ddf614ed7d538acd3197eaa331c0`，engine 0.86.0，inventory `2cc5668a…`，script `6db2f9e1…`，pins `7dfc7732…`，notebook `6444a320…`；実行 GO `Step1_PhaseD_D3_tranche2a_v5_decision.json`）。本報告は **PC-1 の受入れではない**（受入れは外部監査）。

## 1. 実行（Colab CPU；先生の Drive `MirrorTopology_D3/`）
| partition | runtime | run_id | 秒 | base | case | max rel | PC1 | NPY |
|---|---|---|---:|---:|---:|---:|---|---:|
| E2/L1.00 | 標準 | 20260926T074141Z | 8872 | 9 | 12 | 4.50e-8 | 12/0 | 21 |
| E2/L1.20 | 標準 | 20260926T135737Z | 9092 | 9 | 12 | 3.30e-8 | 12/0 | 21 |
| E2/L1.50 | **High-RAM** | 20260928T001131Z | 3187 | 9 | 12 | 2.18e-8 | 12/0 | 21 |
| E7/L1.00 | 標準 | 20260926T174854Z | 8650 | 9 | 12 | 8.35e-8 | 12/0 | 21 |
| E7/L1.20 | 標準 | 20260927T020217Z | 8480 | 9 | 12 | 7.36e-8 | 12/0 | 21 |
| E7/L1.50 | 標準 | 20260927T061528Z | 9047 | 9 | 12 | 6.09e-8 | 12/0 | 21 |
| E8/L1.00 | 標準 | 20260927T084859Z | 13812 | 9 | 24 | 8.29e-8 | 12/0 | 33 |
| E8/L1.20 | 標準 | 20260927T124831Z | 14302 | 9 | 24 | 7.28e-8 | 12/0 | 33 |
| E8/L1.50 | **High-RAM** | 20260928T113755Z | 5426 | 9 | 24 | 5.28e-8 | 12/0 | 33 |

- 9 partition すべて `D3_PASS`（21 required gate 全 True・failures 空・`stage=complete`）；base **81** の D-1 契約 intake 全 PASS；PC-1 **144 case**（新規 108・anchor 36）全 match（閾値 1e-5；最大 8.35e-8）；`PC1_FAIL` 0。1 base ≈ 420 s，1 clone ≈ 420–470 s（CMBtopology 前処理が支配的）。
- **未完 attempt 2 件（削除せず登録）**：E2/L1.50（`20260926T163437Z`）・E8/L1.50（`20260927T164804Z`）は標準 runtime で **rc −9（OOM）**。原因は clone 位置（|x₀| が大きい）の CMBtopology 前処理メモリで，コード変更なしに High-RAM runtime で完走。partial evidence（E2: base 9／E8: base 9＋case 21＝共分散 39 本の file/array SHA と rel 21 値）は **完走 run と bit 同一**（環境 fingerprint も同一）——別 session での再現性の証拠として ledger に記録し，登録 intake が再検査する。
- 実行済 notebook 11 本：`d/MirrorTopology_Step1_D3a_covgen_v0.2.ipynb` と **parameter cell（REPO_COMMIT・EXPECTED_INVENTORY_SHA256・FAMILY・SIZE_FILTER）以外は同一**（cell 単位 diff で確認）。selftest flag・環境 gate 迂回・出力書換えなし（許可書条件）。
- **外部受入れ（metadata）**：`Step1_PhaseD_D3_all9_fe7c201ef265_metadata_acceptance.json`／`ChatGPT_audit_Step1_PhaseD_D3_all9_fe7c201ef265.md`（2026-09-29；`PASS_WITH_EXPLICIT_SCOPE`；NPY 読込み 0/225）。監査が固定した 9 run manifest SHA・notebook SHA・環境 fingerprint `bcfae7ed…`・NPY 記録 bytes 1,616,400・script 秒合計 80868.49 は本 packet の ledger と**全一致**（照合済み）。監査の「次工程」（225 NPY を partition/run 別 folder で提出）には，登録 copy（`registered_assets/d3/runs/<partition>/d3/cov_cache`）に加え，要求された layout `D3a_covariances/<FAMILY>_<SIZE>_<RUN_ID>/cov_cache/*.npy` の提出 zip（index CSV 付き）で応える。
- **監査が未受領とした未完 attempt の実記録**：本 packet の `registered_assets/d3/runs/*_INCOMPLETE_rc-9/` に launcher stderr（rc −9）・final record（`RECORD_MISSING_OR_INVALID`）・partial evidence・生成 manifest を登録（run_id：E2 `20260926T163437Z`，E8 `20260927T164804Z`）。kernel の OOM 記録・peak RSS は Colab 側に残っておらず提出できないため，原因は「標準 runtime での rc −9 が 2 partition で再現し，コード無変更・同一 fingerprint の High-RAM で完走」という観測事実の範囲で申告する。
- **notebook の実行番号（監査 §4 の指摘）**：6 本（E2/L1.20・E2/L1.50・E7/L1.00・E7/L1.50・E8/L1.00・E8/L1.20）は親 Colab session を partition 間で再利用したため実行番号が 1 から始まっていない（同一 session で順に別 partition を起動）。計算は notebook から `sys.executable` の**別 child process**で，run ごとに fresh checkout・fresh OUT・child 内の環境／source gate を通っており，親 runtime の状態は結果に入らない。監査どおり再実行は不要とするが，**D-3b 以降は run ごとに fresh runtime** を手順に固定する。環境 fingerprint は RAM 容量・hardware を含まない（監査の `hardware_equivalence_not_claimed` と同じ立場）。

## 2. 著者側の検証（受入れ記録で「未実施」だった 3 項目）
| 項目 | 方法 | 結果 |
|---|---|---|
| 配列検証付き partition intake | `verify_partition_run(run, source, case_table_sha, config_map_sha, require_arrays=True, expected_run_manifest_sha256=<ledger>)` | 9/9 通過（output_inventory 47／71 件の bytes・SHA 全一致；NPY の raw array SHA が registry／results／bound_load と一致） |
| family 集約 | `aggregate_partitions` | E2・E7・E8 の 3 family とも `family_coverage_complete=True, arrays_verified=True, outer_ledger_bound=True`；base 27×3，case 36／36／72，PC1_PASS 36×3，FAIL 0 |
| 物理 PC-1 の独立再計算 | **mapping-free**：registry・manifest を読まず，登録 NPY 225 本を凍結 loader で実基底へ変換し，全ペア × 全 action で rel(C₁, D(M)C₀D(M)ᵀ) < 1e-5 を総当たり（anchor base は `registered_assets/d1`） | 一致ペア **ちょうど 144 組**（新規 108＋anchor 36；E2/E7 は各ファイル次数 1，E8 は base 次数 2），孤立ファイル 0，最大 rel 8.35e-8；全 225 本が有限・対称・PSD |

## 3. 成果物（本版で追加）
| 物 | 内容 |
|---|---|
| `registered_assets/d3/runs/<partition>/` | 9 正式 run の完全記録（`d3/` の run manifest・registry・PC-1 results・partial evidence・env lock・stdout log・**cov_cache（NPY＋生成 manifest）**，launcher lock，final record，launcher stdout/stderr）と 2 未完 attempt（`…_INCOMPLETE_rc-9`；metadata のみ，`scratch` 除外）。合計 5.0 MB・604 file |
| `registered_assets/d3/notebooks/` | 実行済 notebook 11 本（SHA を ledger に記録） |
| `registered_assets/d3/d3a_generation_ledger.json` | source lock・partition 別（run_id・Drive path・runtime・秒・manifest／document／final record／launcher lock の SHA・gate・PC-1 集計）・未完 attempt（rc・原因・完走 run・再現件数）・notebook SHA・coverage SHA・外部受入れ参照 |
| `registered_assets/d3/d3a_family_coverage.json` | `aggregate_partitions` の出力 3 family（`d3a_family_coverage_v3`；run_dir は登録相対 path） |
| `registered_assets/d3/d3a_outer_receipt.{json,md}` | 著者側 receipt（主張しない事項：PC-1 受入れ・12 位置 receipt／plan schema・D-3b） |
| `step1_engine/d3_assets.py`（module 50） | `intake_registered_d3a_assets(phaseb_root, expected_ledger_sha256=None) → D3aAssets`：ledger／coverage を **信用せず**，9 run を `verify_partition_run(require_arrays=True)` で ledger の manifest SHA に束縛して再検証 → `aggregate_partitions` で再集約 → 登録 coverage と比較（run path 除去）→ final record／launcher lock を source lock に束縛 → 未完 attempt が未完であること（manifest なし・D3_PASS False・rc 一致）と partial evidence の完走 run による再現を検査 → 81 base の登録 file bytes／raw array SHA を再計算 → 現行 pins の case 表／config map SHA と ledger の一致。返す `D3aAssets` は封印（factory 外生成拒否・immutable・view は複製）；`require_pc1_pass(config_id)` は PC1_PASS の base のみ返し，anchor（D-1）・非整数・未知・FAIL を拒否 |
| `tests/test_d3a_registered_intake.py`（3 件） | (1) 登録 intake の通過と露出（81 base の id 集合・bytes／array SHA・PC1 status・未完 attempt 再現 39 件・封印）；(2) 改変拒否 11 種（cov 1 byte・manifest 書換え・ledger SHA 追従・coverage 改変・coverage identity 陳腐化・pins 不一致・run 除去・未完 attempt の昇格・partial evidence 改変・launcher lock commit・source lock 欠落）；(3) 登録配列のみからの mapping-free PC-1 再計算（144 組・孤立 0；`B3_MT` の凍結 checkout が必要，無ければ skip） |

## 3.1 全 suite
50 module・102 test file・899 test 関数・**1389 pytest case 全通過**（JUnit は ledger の `external_acceptance` 欄へ全 9 監査の参照を追記する前の tree で取得；その後の変更は ledger／receipt／報告書の記述のみで，ledger を読む 2 test file（`test_d3a_registered_intake`・`test_d3_covgen`）は追記後に再実行して通過）（11 chunk の JUnit を集合照合：node 集合＝collect・重複 0・failure/skip 0；`regression_logs/d3a_completion_pytest/`）。sandbox の初回 chunk 1 は CMBtopology 依存（tqdm／pandas）未導入による環境 gate 失敗 1 件で，導入後の再実行で 804/804（コード変更なし；`chunks_stdout.txt` に両方を記録）。`verify_b2_packet.py` PASS。

## 4. 監査への依頼事項
1. **配列検証付き受入れ**：本 packet の `registered_assets/d3` のみで `intake_registered_d3a_assets` が通ること（外部資産不要），および監査側独自の配列検証・PC-1 再計算（§2 の mapping-free 法は script `tests/test_d3a_registered_intake.py::test_registered_arrays_mapping_free_pc1_recomputation` に同梱；凍結 `t1_engine`／`t2b2_bridge` が必要）。
2. 全 9 partition 受入れ記録の `explicit_flags`（`new_NPY_arrays_verified`・`PC1_norm_recomputed`・`formal_array_verified_aggregation_issued`・`failed_attempt_cause_verified`）と E2/L1.00 記録の scope 項目 `local_new_covariance_file_array_verification`・`local_physical_pc1_recomputation_from_base_clone_arrays`・`full_array_verified_partition_or_family_aggregation` の閉鎖可否。
3. 未完 attempt の扱い（保持＋再現記録）と High-RAM runtime 使用（コード無変更・環境 fingerprint 同一）の受入れ可否。

## 5. 未了（tranche ②b 以降）
12 位置束縛の D-3 covariance receipt（D-1 の 27 anchor＋D-3a の 81 base＝108 位置）／正式 12 位置 profile／plan schema（BankSupply・BootstrapPlan・FittingPlan の D-2→D-3 reuse binding）→ D-3b（81 配置の bank 生成；≈27 GB・CPU）→ D-2W・noise・Phase E。
