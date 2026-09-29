# Phase D-3 tranche ②b v3 報告（v2 監査 R-D3T2BV2-A/B の反映：公開 view の分離・空 evaluation plan の拒否）
2026-09-29。Claude 作成。ChatGPT 宛。engine `step1_engine 0.91.0`（数値 kernel は 0.54.0 基盤の継承；v2（0.90.0）からの変更は `d3_profile.py` の 2 定義（§0.2）と版表示のみ；v1（0.89.0）からの変更は `d3_profile.py` の 4 領域の補強と `d/d3_bank_spec.json`（context から再導出；payload `d5fda77b…`）・`d/d3_pins.json`（spec v2 SHA 更新）・版表示のみ；receipt（payload `ab545a6f…`）・生成 script・case 表・config map・kernel・登録 run 記録は不変）。v1 は `Step1_PhaseD_D3_tranche2b_0.89.0_decision.json` で「登録内容は整合／新 ②b 正式契約は HOLD」（4 領域）。D-3a 完了 v2（0.88.0）は監査で受入れ PASS（HOLD 解除；`Step1_PhaseD_D3a_completion_v2_0.88.0_decision.json`）。本 tranche は設計 v0.2 §D/E の未了項目（T1-PROFILE・PLAN-FIXATION・bank spec v2）を実装する。**数値は生成しない**（bank・PC-1・較正なし）。**見込み：監査 1〜2 往復（保証ではない）。**

## 0. D-3a v2 監査の非 blocking 指摘への対応
- receipt md の「配列検証付き受入れ pending」：v2 で既に配列受入れ（`…array_acceptance_20260929`）と 0.87.0 監査への参照に更新済み；本版で v2 受入れ（HOLD 解除）を ledger の `external_acceptance` に追記（ledger SHA が変わるため，receipt の `d3a.ledger_sha256` と新点の receipt id `D3A_<ledger12>` はこの ledger に束縛されて再導出）。
- 「親 runtime の状態は結果に入らない」：D-3a 報告書の当該文を「確認した範囲（別 child process・source／環境 gate・保存配列の整合）」に限定する表現へ訂正（数値・記録は不変）。
- 604 file の内訳：`runs/` 593（成功 540＋未完 53）＋実行済 notebook 11＝604 と明記。
- consumer 側の再検証：本 tranche の `intake_twelve_covariance` が消費時に bytes を再検証する（§2）。

## 0.1 v2：監査 R-D3T2B-A〜D の反映（数値生成なし・登録資産不変）
| ID | 指摘 | v2 の対応 |
|---|---|---|
| **A**（plan） | `verify_plan_identity` が record list と actual を `zip` で走査し，末尾欠落・空・header 改変・purpose 300/400 の UID を通す | seeds＝登録 5 を要求；plans／fit_plans の key＝{0..4}；evaluation／fitting の record は**ちょうど 5 件・seed_id 一意**で seed-keyed に全件照合（zip 廃止）；header（family／wave／master_seed／evaluation_group／fitting_group／B／B_KDE）を actual object の plan id（`D3-<family>-eval-s<seed>`）・rng key（[master_seed, wave, **200**, group, batch, seed, stream]／fitting [.., **300**, .., 0, ..]）・replicates・multiplicity 行数・strata UID（purpose 200・group・wave）に照合；`table`／`family` を渡せば CRN 表の group と呼出し側 family にも照合。`fix_family_plans` は UID の purpose≠200・group／wave／batch 不一致を拒否。**接続**：`twelve_official_gate(..., plan_identity, table)` が両系統の plan の**内容**を固定 identity と照合（official では identity 未供給を FAIL；smoke は診断） |
| **B**（profile） | size builder が caller dict の cm／receipt を自己 hash だけで受け入れ，assembly が先頭 matched の identity で全体を再ラベル | **検証済み context**（`TwelveContext`／`twelve_context(root)`：pins→config map を registry／manifest／twelve assets から再導出して一致，receipt を再導出して一致かつ pins の SHA と一致，CRN 表＝D-2 pins，D-2 spec v1＝canonical（`verify_bank_spec_content`）＝D-2 pins，D-2 ledger bytes＝信頼定数 `07574dfa…`）を正式入口の唯一の入力にし，caller dict（自己 hash 済み receipt を含む）は型で拒否。`validate_twelve_grid_identity` は identity の receipt SHA を**検証済み registered receipt**（再導出で登録した cache，無ければ登録 file を再導出）に解決し，map／registry／manifest／twelve-asset の SHA と**全配置の cov_bound entry の完全一致**（file／array SHA・origin＝位置 01–03/04–12・receipt id・PC1_PASS）を要求（origin／receipt id の再ラベル拒否）。`assemble_twelve_family(ctx, family, size_inputs)` は**統合前に**全 size・両系統の 5 つの source identity が context と一致することを要求し，不一致は拒否（先頭値での置換なし）；family identity は context の値 |
| **C**（spec v2） | caller の D-2 spec／ledger を schema と参照文字列だけで受け，N_max 等の内部不整合や unit SHA 改変を転記；map／receipt を縮めた 107 配置を発行 | `build_bank_spec_v2(ctx)` は context のみから導出：D-2 spec は canonical（payload と数値条件を `d2_bank.verify_bank_spec_content` で照合）・CRN 表と定数（N₀／N_max／m／master_seed）一致，ledger bytes＝信頼定数，family reference／旧 27 の unit 行数（N₀／3N₀／N_fit）を照合；対象集合を **E2/E7/E8×3 size×12＝108** の id 集合として再導出・assert（107 は拒否）；batches／shards は登録定数から生成（配置別と global の不整合なし）。`verify_bank_spec_v2(spec, ctx)`，`load_registered_bank_spec_v2(ctx)`（pins の `bank_spec_v2_sha256` と一致＋再導出一致） |
| **D**（consumer） | 認証後に元 path を loader が再読（末尾追記で file SHA が変わっても元 SHA で認証済みと返す） | 捕捉した bytes を隔離 temp file に書き，読み戻して SHA 一致を確認したその path だけを凍結 loader に渡し，読込み後にも snapshot の不変を確認（D-3a `load_bound` と同じ経路）；元 path は認証後に再び開かない。監査の double 試験：末尾追記→loader が読んだ bytes＝認証 bytes；配列置換→snapshot を消費（loader が読んだのは認証 bytes）し，次回 intake は変更 path を拒否 |

監査の 35 対照を `tests/test_audit_d3_t2b_contracts_chatgpt.py` として同梱（path 適応＋「API adaptation」と明記した正常 fixture の適応 5 箇所：context 引数・official gate への plan identity 供給・上流改変を scratch copy の tree で context に与える・validate 自体が拒否し得る・D の「正しい snapshot か安全な拒否」）：提出版 9/35 → v2 **35/35**。著者側 `test_d3_tranche2b.py` 5 件も 4 領域の対照を追加（受入れ済み receipt でない dict の拒否・混在 source の統合前拒否・provenance 再ラベル拒否・plan の全 seed／header／purpose・上流改変 root からの context 拒否・107 配置拒否・snapshot）。D-3a v2 監査の receipt md「pending」文言も更新。

## 0.2 v3：v2 監査（`Step1_PhaseD_D3_tranche2b_v2_0.90.0_decision.json`；R-D3T2B-C/D 閉鎖，A/B の残 2 点）の反映
| ID | 指摘 | v3 の対応 |
|---|---|---|
| **R-D3T2BV2-A** | 5 seed の record が揃っていても，各 evaluation plan の strata／rng_keys／multiplicities を空にし identity を再導出すると `verify_plan_identity` が True | 参考候補を採用：各 seed の型確認直後に `p.strata` が空 dict でないことを要求。加えて**各 stratum が空 list でない**ことも要求（候補より 1 条件強い；1 batch の N₀ 診断・2 batch・縮小 B／B_KDE は従来どおり許容） |
| **R-D3T2BV2-B** | `TwelveContext.registry`／`twelve_assets` が内部 object をそのまま返し，公開 view の編集が検証済み state に波及（単 size の assembly が `full_surviving_scope=True` に変質） | 参考候補を採用：両 property を deepcopy で返す（dict view と同様に全 view が独立）；内部処理は private state を使う。公開 view を編集しても identities・verified・assembly の scope 宣言は不変（試験） |

同梱 `d3_profile.py`（`e5a29131…`）は参考候補 `3f26a5b6…` と **2 定義を除く全定義の AST が同一**：`verify_plan_identity`（空 stratum list の拒否を 1 条件追加）と `assemble_twelve_family`（内部処理が deepcopy された公開 view ではなく private state を読む；契約は同一で，公開 view の編集は波及しない）。監査の新 28 対照を `tests/test_audit_d3_t2bv2_closing_chatgpt.py` として同梱（path 適応のみ）：提出版 22/28 → v3 **28/28**；前回 35 対照 35/35，著者側 5 件（A/B の対照を追加）通過。生成 script・receipt（`ab545a6f…`）・spec v2（`d5fda77b…`）・登録 run・共分散は不変。

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

## 3. 正式 12 位置 profile（v2：全入口が `TwelveContext` を要求）
| 物 | 内容 |
|---|---|
| **twelve grid identity**（`validate_twelve_grid_identity`） | 第 1 波 identity の field 集合の**上位集合**（`stage="twelve"`・`config_map_sha256`・`twelve_assets_sha256`・`position_index`・`covariance_receipt_sha256` を追加）。`production.validate_grid_identity` は `stage=="twelve"` のときだけこの検査へ dispatch（第 1 波 dict は従来どおり；12 個の id を第 1 波 schema に入れると従来どおり拒否）。要求：family ∈ {E2,E7,E8}，size ごとに **12 配置**（suffix 01–12）の id 規則（native +50000），position の全単射，等 size prior，cache_key，**全配置の covariance binding**（receipt の file／array SHA・origin・receipt id・`PC1_PASS`・`consumption_allowed`），weight＝size 重み／12 |
| `build_twelve_size_input(ctx, family, size, system, supplies, plans, fit_plans)` | ちょうど 12 の `BankSupply`（重複・system 不一致・欠落を拒否）；各 supply の `cov_manifest` の file／array SHA が receipt entry と一致（bank がその共分散から生成された束縛）；receipt が PC1_FAIL の配置は拒否；重み 1/12；`FamilyInput.validate()` を通す |
| `assemble_twelve_family(ctx, family, size_inputs)` | 各 size view が同じ map／receipt の twelve identity であること，登録 twelve manifest（`TwelveManifestAsset.get`）の SHA が config map の記録と一致することを要求 → `twelve_eval.assemble_all_sizes`（plan 共有・重み＝登録 size prior × 1/12＝**1/36**）→ family identity を付与（全 size の cov_bound／position を統合）。size 部分集合は組み立て可能だが `full_surviving_scope=False` |
| `twelve_official_gate(fm, fn, mode, plan_identity=None, table=None)` | 既存 `official_gate`（登録 N₀／N_max／m／B／B_KDE／N_fit・bank と plan の UID 順・環境）＋ 12 位置要件：stage・size ごと 12・全配置 PC1_PASS 束縛・全 surviving size（official）・**第 1 波と新点が同じ plan（同一 latent の UID 順）を共有**（official）・matched／native が同じ receipt／map／配置集合。返値は `GateRecord`（`twelve_checks` を diagnostics に） |

小規模試験（TEST-ONLY 合成 bank，実 config map／receipt／registry／twelve assets 上）：E2 の 3 size × 2 系統 → size view 12 配置・全 size 36 配置・重み 1/36・identity 全 field；smoke gate PASS；official gate は登録規模の検査（N₀・m）でのみ FAIL し 12 位置検査は全 PASS；単 size は `full_surviving_scope=False` で official FAIL。拒否：11 supply・重複・系統不一致・supply の共分散 identity 不一致・PC1_FAIL の receipt・weight 改変・stage 偽装・partial native・family 不一致。

## 4. plan 固定（`PLAN_SCHEMA_V2`・`fix_family_plans`・`verify_plan_identity`）
family の bank cluster UID（family evaluation latent の順）から 5 seed の `BootstrapPlan`（key＝(MASTER_SEED, wave 1, purpose, family evaluation group, batch, seed, stream)）と `FittingPlan`（fitting group，K＝N_fit/m_fit）を**一度**構築し，identity（plan id・rng key・strata UID SHA・multiplicity SHA）を記録。同じ UID からの再構築は同一（決定性）；別 family の latent 上の UID・別 master seed は拒否／identity 不一致で拒否。**第 1 波（D-2）と新点（D-3b）は同じ family latent → 同じ UID 順 → 同一 plan object を共有**（試験：E7/L1.00 の 3 旧＋9 新配置が plan の strata と同じ UID 列）。較正開始時に固定し target まで不変（threshold ごとの再標本化なし）。

## 5. bank spec v2（`d/d3_bank_spec.json`；payload `d5fda77b…`）
`build_bank_spec_v2(ctx)`（v2：検証済み context のみ）：108 配置。**generate_D3b 81**（位置 04–12）：role（matched／native root は `intake_twelve_covariance`，ref_native は c_ct），共有 ref_matched は D-2 family reference の再利用，family evaluation／fitting group（wave 1），batches／shards は v1 と同一，**selections f64 のみ（両 batch；新 f32 subset なし）**，fitting N_fit/m_fit，**w2_primary None**（設計 §B：主経路外，CRN group 追加なし）。**reuse_D2_fixed_input 27**（位置 01–03）：D-2 spec v1 entry の SHA・selections・f32 subset・**ledger の unit identity**（b0／b1／fit の manifest SHA・行数，W₂ unit）・run id・producer digest；binding は `d3_d2_reuse_binding_v1`。family_reference：D-2 の ref b0／b1／fit unit identity。合計 generation unit 243・evaluation 行 3.24×10⁸・fitting 行 1.62×10⁷（≈27 GB，容量は見積り）。`verify_bank_spec_v2` は再導出との完全一致（w2 追加・f32 追加・配置削除を拒否；D-2 spec の表 SHA 不一致を拒否）。receipt が FAIL を持つ場合は spec にそのまま status を載せ，消費は intake で拒否する（隠さない）。

## 6. 試験（`tests/test_d3_tranche2b.py` 5 件＋監査 35 対照）
receipt（決定性・登録一致・108 の id 集合・全 file の byte 束縛・改変 5 種の拒否・pins 不一致／登録 NPY 改変時の構築拒否）；消費時 intake（新点・anchor の通過，E1／未知／非整数の拒否，FAIL receipt の拒否，登録後の byte 改変の拒否，mt_root 必須；凍結 checkout 必要）；profile（§3）；plan 固定（§4）；bank spec v2（§5）。既存の第 1 波経路（`build_family_input`・`official_gate`・D-2 tranche ③a・監査 t20／t21）は不変で通過。

## 6.1 全 suite
51 module・106 test file・944 test 関数・**1478 pytest case 全通過**（11 chunk の JUnit を集合照合：node 集合＝collect・重複 0・failure/skip 0；`regression_logs/d3_t2bv3_pytest/`；v1／v2 の記録も保持）。`verify_b2_packet.py` PASS。

## 7. 未了・限定
- 本 tranche は receipt／intake／profile／plan／spec の**契約と小規模試験**であり，12 位置 bank の生成（D-3b）・正式 12 位置 profile の**実 bank による**受入れ・較正・PC-1 の物理受入れ・D-2W・noise・Phase E を含まない。監査の `not_approved`（108 位置 receipt／profile／plan の承認・D-3b GO）は本 packet の監査で判断される。
- `intake_twelve_covariance` は PC-1 status を**運ぶ**だけで再評価しない（再評価は D-3a の外側受入れ）。
- 次：D-3b 生成 script（`d/d3_bankgen.py`：spec v2 の generate 81 を family 別 Colab で；ref／旧 27 は D-2 の accepted bank を `intake_registered_bank` で固定入力として読む）→ 実行前監査 → Colab（≈27 GB，CPU；run ごとに fresh runtime）→ read-only 検証 → 実 bank での `twelve_official_gate`。
