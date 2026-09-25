# Phase D-3 tranche ②a 報告（12 位置 base 共分散＋PC-1 生成 script・family 別 notebook・自己試験）
2026-09-25。Claude作成。engine `step1_engine 0.85.0`（数値 kernel は 0.54.0 基盤の継承；追加は `d/d3_covgen.py`・`d/d3_pins.json`・notebook・テスト；engine module は不変）。tranche ① v3 は監査で受入れ（tranche ② GO）。本 tranche は ② の前半＝**共分散＋PC-1 生成 script**であり，②b（D-3 covariance receipt／12 位置束縛 intake／正式 12 位置 profile／plan schema の小規模接続）は次。**見込み：実行前監査 1〜2 往復 → family 別 Colab（E2／E7 ≈8 h，E8 ≈11 h；size 分割可）→ 実行後監査（保証ではない）。** **テスト 1328/1328 PASS**（11 chunk・JUnit 同梱 `regression_logs/d3_t2a_pytest/`；node 集合＝collect・重複 0・failure 0）。

| 成果物 | 内容 |
|---|---|
| `d/d3_covgen.py` | 受入れ済み D-1 v0.3 の契約を継承（A11 cell 4 逐語生成器，preflight＝pins／inventory／script，Phase C member，凍結 loader，A11 freeze／generator cell SHA，登録環境 hard gate，CMBtopology commit／origin／clean／依存，D-1 固定 SHA）に加えて **D-3 束縛**（registry source-bound，`verify_config_map`／`verify_pc1_case_table` で map／case 表を bound 入力と信頼起点付き原典から再導出して pins の SHA と一致；formal 表のみ）。新 27 配置／family の base を生成・intake（幾何 binding・run profile・env fingerprint・array SHA・PSD・matched／native root gate），**PC-1**：case 表の (配置, 必要作用) ごとに clone を x₀_H1 で独立生成，A11 cell 2 の bridge 求積 D(M)（直交性 gate 1e-12），rel／rel_off／rel_white，`match=rel<1e-5`，配置 status（全必要作用 match→`PC1_PASS`，いずれか不一致→`PC1_FAIL`，未評価→`PENDING`）；anchor case は D-1 base を固定 SHA で再利用；`--with-h2` で識別用 H2 も。fail-fast（intake 失敗で登録停止・partial registry），fresh OUT，21 gate；`D3_PASS` は formal のみ（size 分割 run は filter のため `False`，family PASS は ledger で合成） |
| `d/d3_pins.json` | 環境・CT・run_config・A11 cell 4 SHA・registry／map／case 表 SHA・PC-1 許容・見込み |
| `d/MirrorTopology_Step1_D3a_covgen_v0.1.ipynb` | D-1／D-2 launcher 型（lock・checkout・束縛・pinned CT clone・環境 install＋pre-check・script・final record・監査 zip（.npy は Drive）；`SIZE_FILTER` で size 分割） |
| 自己試験（sandbox・実 CMBtopology・E7 30104・env gate のみ skip） | base 255 s → intake PASS；clone 251 s → **PC-1 glide_A rel 8.35e-8（match）**，rel_off 3.3e-7，rel_white 8.7e-8；21 gate 中 env lock 以外 True，`D3_PASS=False`（self-test）。証拠 `regression_logs/d3_selftest_sandbox_E7_30104_*.json`（**正式 PC-1 受入れではない**） |
| `tests/test_d3_covgen.py` | pins の束縛と自己試験証拠の case 表 SHA 束縛；fresh-only・profile 拒否・script 改変での preflight 停止（生成 0）・case 表 pin 改変での d3_inputs 停止（生成 0） |

限定：正式生成・PC-1 の物理 PASS・12 位置 profile・bank・plan 固定は含まない。E2／E7／E8 の実行順は監査の指示に従う。
