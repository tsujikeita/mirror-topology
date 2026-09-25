# Phase D-3 tranche ②a v3 報告（監査 v2：R-D3T2AV2-A/B/C の反映）
2026-09-26。Claude作成。engine `step1_engine 0.86.0`（版は据置き：自己試験 v3 は最終 script／pins bytes の記録であり，版を変えると pins が変わるため；数値 kernel は 0.54.0 基盤の継承；変更は `d/d3_covgen.py`・`d3_stage.aggregate_partitions`（正式化）・notebook v0.2（fallback record）・テスト・自己試験証拠）。tranche ① v3 は監査で受入れ（tranche ② GO）。本 tranche は ② の前半＝**共分散＋PC-1 生成 script**であり，②b（D-3 covariance receipt／12 位置束縛 intake／正式 12 位置 profile／plan schema の小規模接続）は次。**見込み：実行前監査 1〜2 往復 → family 別 Colab（E2／E7 ≈8 h，E8 ≈11 h；size 分割可）→ 実行後監査（保証ではない）。** **テスト 1329/1329 PASS**（11 chunk・JUnit 同梱 `regression_logs/d3_t2av3_pytest/`；node 集合＝collect・重複 0・failure 0）。

| 成果物 | 内容 |
|---|---|
| `d/d3_covgen.py` | 受入れ済み D-1 v0.3 の契約を継承（A11 cell 4 逐語生成器，preflight＝pins／inventory／script，Phase C member，凍結 loader，A11 freeze／generator cell SHA，登録環境 hard gate，CMBtopology commit／origin／clean／依存，D-1 固定 SHA）に加えて **D-3 束縛**（registry source-bound，`verify_config_map`／`verify_pc1_case_table` で map／case 表を bound 入力と信頼起点付き原典から再導出して pins の SHA と一致；formal 表のみ）。新 27 配置／family の base を生成・intake（幾何 binding・run profile・env fingerprint・array SHA・PSD・matched／native root gate），**PC-1**：case 表の (配置, 必要作用) ごとに clone を x₀_H1 で独立生成，A11 cell 2 の bridge 求積 D(M)（v2 以降：cell 2 の battery 6 gate＋使用 D の直交性 1e-10），rel／rel_off／rel_white，`match=rel<1e-5`，配置 status（全必要作用 match→`PC1_PASS`，いずれか不一致→`PC1_FAIL`，未評価→`PENDING`）；anchor case は D-1 base を固定 SHA で再利用；`--with-h2` で識別用 H2 も。fail-fast（intake 失敗で登録停止・partial registry），fresh OUT，21 gate；`D3_PASS` は formal のみ（v2 以降：`--sizes` の正式 partition も formal＝PASS 可；family coverage は `aggregate_partitions` で合成） |
| `d/d3_pins.json` | 環境・CT・run_config・A11 cell 4 SHA・registry／map／case 表 SHA・PC-1 許容・見込み |
| `d/MirrorTopology_Step1_D3a_covgen_v0.2.ipynb`（v0.1 は撤回） | D-1／D-2 launcher 型（lock・checkout・束縛・pinned CT clone・環境 install＋pre-check・script・final record・監査 zip（.npy は Drive）；`SIZE_FILTER` は `--sizes` の正式 partition；run manifest 欠落時は fallback record） |
| 自己試験（sandbox・実 CMBtopology・E7 30104・env gate のみ skip） | base 255 s → intake PASS；clone 251 s → **PC-1 glide_A rel 8.35e-8（match）**，rel_off 3.3e-7，rel_white 8.7e-8；21 gate 中 env lock 以外 True，`D3_PASS=False`（self-test）。証拠 `regression_logs/d3_selftest_sandbox_E7_30104_*.json`（**正式 PC-1 受入れではない**） |
| `tests/test_d3_covgen.py` | pins の束縛と自己試験証拠の case 表 SHA 束縛；fresh-only・profile 拒否・script 改変での preflight 停止（生成 0）・case 表 pin 改変での d3_inputs 停止（生成 0） |

## v2（監査 ②a：正常な全 family 経路・契約固定・helper 一致・有限 PC1_FAIL の run 完了は確認；5 領域を修正）
| ID | 対応 |
|---|---|
| R-D3T2A-A | `load_bound`：PC-1 に渡す全 covariance（base・anchor base・clone・H2）を **file を一度だけ読み**，同じ bytes で file SHA・raw array SHA・凍結 loader の返却 metadata（array identity）を照合し，実基底行列の 21×21・実・有限・対称・PSD を検査してから比較へ。primary norm の有限性と正値も検査。**技術異常は `evaluation="TECHNICAL_FAILURE"` として case に記録し run を停止**（有限な rel≥1e-5 の `PC1_FAIL` は従来どおり run 完了）。rel_off／rel_white の分母 0 は null＋理由。監査の「保存後の npy 追記／置換」「loader 返却 SHA 不一致」「NaN／Inf／誤 shape／零／複素」はすべて技術失敗として拒否（有限 FAIL と混同しない） |
| R-D3T2A-B | A11 cell 2 の**表現 battery を逐語接続**（Gram 1e-12・real-basis bridge 1e-12・使用 M 集合の直交性／direct geometry／homomorphism 1e-10・解析的 reflection 1e-12）を `G_bridge_quadrature` に；PC-1 で実際に使う各作用の D(M) を runtime で直交性検査（1e-10）し SHA を記録（`used_D`）；求積 node／weight・M21・LM・RB の SHA を保存 |
| R-D3T2A-C | unit ごとに atomic な `d3_partial_evidence.json`（bases／cases／failed／status）を更新；生成器・loader・数値の例外時も完了集合と失敗 unit の identity（config／action／request）を保存し，`d3_cov_registry.json`／`d3_pc1_results.json` を PARTIAL として書く；`G_evidence_saved` は存在ではなく内容対応（registry⇄計算集合，evidence COMPLETE） |
| R-D3T2A-D | `--sizes` を**正式 partition**として `--selftest-configs` から分離：当該 size の新配置と**旧 anchor case を含む**（E2／E7 12 case，E8 24 case）；空／無効な選択は前段で exit 2；`d3_stage.aggregate_partitions`（同 case 表・同 family・disjoint partition・全 size 被覆・評価 case 集合＝必要集合・base 集合一致・self-test／非 PASS run の排除）で family coverage を合成；notebook v0.2 は `--sizes` を使う。`--selftest-skip-anchors` は self-test 専用 flag（formal では不可） |
| R-D3T2A-E | required 21 gate に固定（余分 key を除去）；自己試験の出所を版で区別（旧 0.84 record は削除し，v2＝0.85 script の record を登録） |

自己試験 v2（sandbox・実 CMBtopology・E7 30104・env gate skip・anchor 省略 flag）：battery 6 gate PASS，base 280 s → intake PASS（bound load 一致），clone 275 s → **PC-1 glide_A rel 8.35e-8（EVALUATED・match）**，`d3_partial_evidence` COMPLETE，21 gate 中 env lock 以外 True。証拠 `regression_logs/d3_selftest_v2_sandbox_E7_30104_*.json`（**正式 PC-1 受入れではない**；base／clone の npy は未添付）。試験 3 件：pins／証拠束縛（gate 集合 21・partition／selection 記録・bound clone identity・battery gate），binding 失敗と無効選択の生成前停止，aggregator の受入れ／拒否（size 未被覆・重複・anchor 欠落・self-test・非 PASS・余分 case）。

## v3（監査 v2：v2 の改善は確認；3 領域を修正）
| ID | 対応 |
|---|---|
| R-D3T2AV2-A | 公開する registry／PC-1 結果／partial evidence／env lock を**読み戻して計算 snapshot と値レベルで照合**（全内容；表現 battery・status・fingerprint・case 表 SHA の相互対応を含む）してから `G_evidence_saved`，bytes SHA を `published_evidence` に記録（監査の rel 0.5／SHA 0×64／partial 改変の 3 対照は不一致として失敗）。`save_partial` は書込み後に読み戻し比較し，保存例外は **unit identity と段階**を run record・stderr に残して `save_failure` で停止（失敗 unit を `failed` に記録）。notebook v0.2 は run manifest 欠落／破損時に rc・理由・stderr を持つ **False の fallback record** で最終 zip まで進む |
| R-D3T2AV2-B | `aggregate_partitions` を正式入口に：case 表 payload SHA と formal，`expected_source`（engine 版・inventory・script・pins SHA）と各 run の記録 `source`／profile の一致，**required 21 gate 全 True**（集合固定），self-test 選択の排除，family の run／registry／PC-1 間一致，case 表 SHA・環境 fingerprint の一致，**partition ごとに size から期待 base／case 集合を導出**して照合（移し替えを拒否），各 case の evaluation／config／action／有限 rel／match＝rel<tol／tol，configuration_status の**再導出照合**（stale summary を拒否），disjoint と全 size 被覆，返値 deep copy（入力へ波及しない）。E1／空 run は不適用として拒否。監査の 13 対照＋moved case・重複 size・source 差・gate False をテストで拒否；有限 PC1_FAIL は coverage 完了・FAIL 継承 |
| R-D3T2AV2-C | H2 の差 norm が非有限なら `rel_H2=None`・`h2_status="INVALID_DIAGNOSTIC"`・理由付き（H1 不変；無標識の Infinity／positive discrimination を出さない） |
| selector | `--sizes` の重複・`--selftest-configs` の未知 ID 混在を生成前に exit 2 |

run manifest に `source`（engine 版・inventory・script・pins SHA・profile）を記録。**自己試験 v3**（sandbox・実 CMBtopology・E7 30104・env gate skip・anchor 省略 flag）は**最終 script（SHA `1a82f413…`）と pins bytes の記録**：battery 6 gate PASS，base 287 s → intake PASS，clone 283 s → PC-1 rel 8.35e-8（EVALUATED），`published_evidence.value_level_readback_ok=True`。証拠 `regression_logs/d3_selftest_v3_sandbox_E7_30104_*.json`（正式受入れではない；npy 未添付）。

限定：正式生成・PC-1 の物理 PASS・12 位置 profile・bank・plan 固定は含まない。E2／E7／E8 の実行順は監査の指示に従う。
