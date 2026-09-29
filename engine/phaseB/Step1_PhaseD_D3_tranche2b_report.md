# Phase D-3 tranche ②b 報告（108 位置 covariance receipt・消費時 intake・正式 12 位置 profile・plan 固定・bank spec v2）
2026-09-29。Claude 作成。ChatGPT 宛。engine `step1_engine 0.89.0`（数値 kernel は 0.54.0 基盤の継承；追加は `d3_profile.py`＝module 51，`registered_assets/d3/d3_covariance_receipt.json`，`d/d3_bank_spec.json`；`production.validate_grid_identity` に stage="twelve" の dispatch 1 分岐を追加（第 1 波 schema の検査は不変），`d/d3_pins.json` に receipt／spec v2 の SHA を追加）。D-3a 完了 v2（0.88.0）は監査で受入れ PASS（HOLD 解除；`Step1_PhaseD_D3a_completion_v2_0.88.0_decision.json`）。本 tranche は設計 v0.2 §D/E の未了項目（T1-PROFILE・PLAN-FIXATION・bank spec v2）を実装する。**数値は生成しない**（bank・PC-1・較正なし）。**見込み：監査 1〜2 往復（保証ではない）。**

## 0. D-3a v2 監査の非 blocking 指摘への対応
- receipt md の「配列検証付き受入れ pending」：v2 で既に配列受入れ（`…array_acceptance_20260929`）と 0.87.0 監査への参照に更新済み；本版で v2 受入れ（HOLD 解除）を ledger の `external_acceptance` に追記（ledger SHA が変わるため，receipt の `d3a.ledger_sha256` と新点の receipt id `D3A_<ledger12>` はこの ledger に束縛されて再導出）。
- 「親 runtime の状態は結果に入らない」：D-3a 報告書の当該文を「確認した範囲（別 child process・source／環境 gate・保存配列の整合）」に限定する表現へ訂正（数値・記録は不変）。
- 604 file の内訳：`runs/` 593（成功 540＋未完 53）＋実行済 notebook 11＝604 と明記。
- consumer 側の再検証：本 tranche の `intake_twelve_covariance` が消費時に bytes を再検証する（§2）。

## 1. 108 位置 covariance receipt（`registered_assets/d3/d3_covariance_receipt.json`；SHA `01387df2…`，payload `ab545a6f…`）
| 項目 | 内容 |
|---|---|
| 範囲 | E2/E7/E8 × 3 size × 12 位置＝**108 配置**。E1 は第 1 波 3 配置のまま（12 位置段階なし；`e1_first_wave_only`） |
| 束縛 | 登録 config map（`da1e68bc…`；pins と一致を要求），registry・第 1 波 manifest・twelve assets の SHA，case 表 SHA，D-1 登録 receipt の定数（receipt file／registry SHA・凍結 loader SHA），D-3a の ledger／coverage SHA（`intake_registered_d3a_assets` で毎回再検証） |
| 各 entry | config_id・family・size・position_index／suffix・origin・x₀_CT・cache_key・shape・evaluation ids・重み（1/36・1/12）・**source**（`first_wave_D1`＝位置 01–03 の 27 件は D-1 の固定 SHA を再利用／`twelve_added_D3a`＝位置 04–12 の 81 件は D-3a 登録 file）・登録 file path・file／array SHA・PC-1 status（coverage の `configuration_status` から再導出；anchor は anchor 診断 case，新点は新点 case）・`consumption_allowed`（PC1_PASS のみ True） |
| 現状 | positions 108，reused 27，added 81，PC1_PASS 108，FAIL 0，consumption_allowed 108 |
| 検証 | `verify_d3_covariance_receipt`：payload SHA ＋ **登録入力からの再導出との完全一致**（entry の status／flag／SHA を変えて payload SHA を打ち直しても拒否）。`load_registered_receipt(root, expected_sha)` |

## 2. 消費時 intake `intake_twelve_covariance(config_id, root, mt_root)`
- receipt を再導出して照合 → entry の `consumption_allowed`／`PC1_PASS` を要求（FAIL／PENDING は拒否；E1 と未知 id も拒否）。
- anchor（`first_wave_D1`）：D-1 の `intake_registered_covariance`（trusted receipt／registry 定数・source-bound spec・sidecar・array SHA・凍結 loader・PSD・principal root hard gate）に委譲し，返った file／array SHA・cache_key が receipt と一致することを要求。
- 新点（`twelve_added_D3a`）：`intake_registered_d3a_assets(...).require_pc1_pass(cid)` の identity と receipt の一致 → 登録 file の **bytes を読み直して** file SHA・raw array SHA（21×21）を再計算 → 凍結 `t1_engine`／`t2b2_bridge`（`_verified_frozen_loader`）で実基底へ → 対称／PSD → `LegacyKernel` の matched／native principal root hard gate（clip 0・λ_min>0・sym<1e-12・recon<1e-10）。返値は D-1 intake と同じ構造（C_real・C_matched・c_ct・S_matched・S_native・roots_info・eig・loader identity）＋ receipt／origin／PC-1 status。
- 監査 v2 の consumer requirement（「凍結 metadata snapshot は filesystem を不変にしない」）に対応：登録後に NPY の 1 byte を変えた copy は消費時に拒否（試験）。

## 3. 正式 12 位置 profile
| 物 | 内容 |
|---|---|
| **twelve grid identity**（`validate_twelve_grid_identity`） | 第 1 波 identity の field 集合の**上位集合**（`stage="twelve"`・`config_map_sha256`・`twelve_assets_sha256`・`position_index`・`covariance_receipt_sha256` を追加）。`production.validate_grid_identity` は `stage=="twelve"` のときだけこの検査へ dispatch（第 1 波 dict は従来どおり；12 個の id を第 1 波 schema に入れると従来どおり拒否）。要求：family ∈ {E2,E7,E8}，size ごとに **12 配置**（suffix 01–12）の id 規則（native +50000），position の全単射，等 size prior，cache_key，**全配置の covariance binding**（receipt の file／array SHA・origin・receipt id・`PC1_PASS`・`consumption_allowed`），weight＝size 重み／12 |
| `build_twelve_size_input(cm, receipt, family, size, system, supplies, plans, fit_plans)` | ちょうど 12 の `BankSupply`（重複・system 不一致・欠落を拒否）；各 supply の `cov_manifest` の file／array SHA が receipt entry と一致（bank がその共分散から生成された束縛）；receipt が PC1_FAIL の配置は拒否；重み 1/12；`FamilyInput.validate()` を通す |
| `assemble_twelve_family(cm, reg, family, size_inputs, twelve_assets)` | 各 size view が同じ map／receipt の twelve identity であること，登録 twelve manifest（`TwelveManifestAsset.get`）の SHA が config map の記録と一致することを要求 → `twelve_eval.assemble_all_sizes`（plan 共有・重み＝登録 size prior × 1/12＝**1/36**）→ family identity を付与（全 size の cov_bound／position を統合）。size 部分集合は組み立て可能だが `full_surviving_scope=False` |
| `twelve_official_gate(fm, fn, mode)` | 既存 `official_gate`（登録 N₀／N_max／m／B／B_KDE／N_fit・bank と plan の UID 順・環境）＋ 12 位置要件：stage・size ごと 12・全配置 PC1_PASS 束縛・全 surviving size（official）・**第 1 波と新点が同じ plan（同一 latent の UID 順）を共有**（official）・matched／native が同じ receipt／map／配置集合。返値は `GateRecord`（`twelve_checks` を diagnostics に） |

小規模試験（TEST-ONLY 合成 bank，実 config map／receipt／registry／twelve assets 上）：E2 の 3 size × 2 系統 → size view 12 配置・全 size 36 配置・重み 1/36・identity 全 field；smoke gate PASS；official gate は登録規模の検査（N₀・m）でのみ FAIL し 12 位置検査は全 PASS；単 size は `full_surviving_scope=False` で official FAIL。拒否：11 supply・重複・系統不一致・supply の共分散 identity 不一致・PC1_FAIL の receipt・weight 改変・stage 偽装・partial native・family 不一致。

## 4. plan 固定（`PLAN_SCHEMA_V2`・`fix_family_plans`・`verify_plan_identity`）
family の bank cluster UID（family evaluation latent の順）から 5 seed の `BootstrapPlan`（key＝(MASTER_SEED, wave 1, purpose, family evaluation group, batch, seed, stream)）と `FittingPlan`（fitting group，K＝N_fit/m_fit）を**一度**構築し，identity（plan id・rng key・strata UID SHA・multiplicity SHA）を記録。同じ UID からの再構築は同一（決定性）；別 family の latent 上の UID・別 master seed は拒否／identity 不一致で拒否。**第 1 波（D-2）と新点（D-3b）は同じ family latent → 同じ UID 順 → 同一 plan object を共有**（試験：E7/L1.00 の 3 旧＋9 新配置が plan の strata と同じ UID 列）。較正開始時に固定し target まで不変（threshold ごとの再標本化なし）。

## 5. bank spec v2（`d/d3_bank_spec.json`；SHA `e0b406cf…`，payload `a886c02f…`）
`build_bank_spec_v2(cm, table, receipt, d2_spec_v1, d2_ledger)`：108 配置。**generate_D3b 81**（位置 04–12）：role（matched／native root は `intake_twelve_covariance`，ref_native は c_ct），共有 ref_matched は D-2 family reference の再利用，family evaluation／fitting group（wave 1），batches／shards は v1 と同一，**selections f64 のみ（両 batch；新 f32 subset なし）**，fitting N_fit/m_fit，**w2_primary None**（設計 §B：主経路外，CRN group 追加なし）。**reuse_D2_fixed_input 27**（位置 01–03）：D-2 spec v1 entry の SHA・selections・f32 subset・**ledger の unit identity**（b0／b1／fit の manifest SHA・行数，W₂ unit）・run id・producer digest；binding は `d3_d2_reuse_binding_v1`。family_reference：D-2 の ref b0／b1／fit unit identity。合計 generation unit 243・evaluation 行 3.24×10⁸・fitting 行 1.62×10⁷（≈27 GB，容量は見積り）。`verify_bank_spec_v2` は再導出との完全一致（w2 追加・f32 追加・配置削除を拒否；D-2 spec の表 SHA 不一致を拒否）。receipt が FAIL を持つ場合は spec にそのまま status を載せ，消費は intake で拒否する（隠さない）。

## 6. 試験（`tests/test_d3_tranche2b.py` 5 件）
receipt（決定性・登録一致・108 の id 集合・全 file の byte 束縛・改変 5 種の拒否・pins 不一致／登録 NPY 改変時の構築拒否）；消費時 intake（新点・anchor の通過，E1／未知／非整数の拒否，FAIL receipt の拒否，登録後の byte 改変の拒否，mt_root 必須；凍結 checkout 必要）；profile（§3）；plan 固定（§4）；bank spec v2（§5）。既存の第 1 波経路（`build_family_input`・`official_gate`・D-2 tranche ③a・監査 t20／t21）は不変で通過。

## 6.1 全 suite
51 module・104 test file・913 test 関数・**1415 pytest case 全通過**（11 chunk の JUnit を集合照合：node 集合＝collect・重複 0・failure/skip 0；`regression_logs/d3_t2b_pytest/`）。初回 chunk 1 は `test_consumption_time_intake` が同 chunk 内の凍結 A10 notebook 試験（`test_b2_tranche23`）が session に残す別 path の `t1_engine` module を引き継ぎ，凍結 loader の「置換拒否」契約で 1 件 FAIL（契約どおりの拒否；数値の問題ではない）。test 側で stale module を外す harness 隔離（`monkeypatch.delitem`；`test_d4_intake` と同じ扱い）を入れて chunk 1 を再実行し 830/830（両方の記録を `chunks_stdout.txt` に保持）。`verify_b2_packet.py` PASS。

## 7. 未了・限定
- 本 tranche は receipt／intake／profile／plan／spec の**契約と小規模試験**であり，12 位置 bank の生成（D-3b）・正式 12 位置 profile の**実 bank による**受入れ・較正・PC-1 の物理受入れ・D-2W・noise・Phase E を含まない。監査の `not_approved`（108 位置 receipt／profile／plan の承認・D-3b GO）は本 packet の監査で判断される。
- `intake_twelve_covariance` は PC-1 status を**運ぶ**だけで再評価しない（再評価は D-3a の外側受入れ）。
- 次：D-3b 生成 script（`d/d3_bankgen.py`：spec v2 の generate 81 を family 別 Colab で；ref／旧 27 は D-2 の accepted bank を `intake_registered_bank` で固定入力として読む）→ 実行前監査 → Colab（≈27 GB，CPU；run ごとに fresh runtime）→ read-only 検証 → 実 bank での `twelve_official_gate`。
