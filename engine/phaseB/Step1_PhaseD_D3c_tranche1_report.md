# Phase D-3c tranche ① 報告（実 bank 12 位置 profile・official gate・plan 固定 script と launcher の起草；合成 bank での試験のみ・正式実行なし）
2026-10-03。Claude 作成。ChatGPT 宛（実行前監査の依頼）。engine `step1_engine 0.97.0`（0.96.0 からの変更は **新 script `d/d3c_profile.py`**（`1af43ebe…`；223 行），**新 notebook `d/MirrorTopology_Step1_D3c_profile_v0.1.ipynb`**（`ccfe621e…`），試験 1 file，設計 v0.1 の F 節追記，tranche ③ 報告書の文言訂正，版表示。**engine module・登録資産・ledger／receipt・生成／検証 script は不変**）。設計受入れ：`Step1_PhaseD_D3b_tranche3_0.96.0_decision.json`（D3c_design ACCEPTED_IN_PRINCIPLE_WITH_IMPLEMENTATION_CONDITIONS・tranche ① GO）。

## 0. 範囲と主張
- **主張するもの**：受入れ済み API だけで，1 family の固定入力（D-2 第 1 波 3 配置／size＋family reference，D-3b 追加 9 配置／size）を formal intake し，ordered UID／K_fit を照合し，family 共有の 5 seed plan を実 UID から 1 回構築し，size input 6 → 全 size 組立て → fingerprint → formal 12 位置 official gate（live 環境）→ gate 後の identity 再確認 → profile record と plan identity の検証付き publication を行う script と launcher。合成小規模 bank での end-to-end 試験と拒否系の試験。
- **主張しないもの**：実 bank での gate 通過・plan の実固定（Colab 実行後の監査で），閾値／label／較正／D-2W／noise，再生成。

## 1. 監査の実装条件への対応
| 条件 | 実装 |
|---|---|
| gate 呼出し（keyword；env 注入なし） | `twelve_official_gate(fm, fn, mode="official"/"smoke", plan_identity=plan_ident, table=table)`；`G_gate_passed` は `passed` かつ `environment_source=="live_collected"` を要求 |
| 実行順 | intake（全供給）→ ordered UID／K_fit → plan 1 回 → size input 6 → 全 size 組立て → fingerprint → gate → identity 再確認 → publication（§2） |
| 同一 plan object・gate 前後の identity | size input 6 と組立て後の `fm.plans is plans`／`fn.plans is plans`／`fit_plans is fplans` を要求；`input_fingerprint` を gate 前後で比較，`verify_plan_identity` を gate 後に両 system で再実行（`G_identity_stable`） |
| E2（第 1 波の unit identity） | `intake_registered_bank` の `info["manifests"]`（eval b0／b1・fit・ref b0／b1・ref fit）を spec v2 の `configurations[cid].d2.units`／`family_reference.units` に照合（formal のみ；不一致は停止） |
| E3（plan の再構築可能性） | `d3c_plan_identity_<F>.json` に identity＋**ordered UID 列（batch 別）**＋K_fit／master_seed／B／B_KDE／seeds／定数の出典／CRN 表・context identity／engine／環境を記録；script 内で ordered UID の tuple から再構築して identity 完全一致と `verify_plan_identity` を要求（`G_plans_fixed`）；試験では別 process での再構築一致・逆順で別 identity |
| E4（定数の出典） | formal：`B=RULES.B`・`B_KDE=official_gate.B_KDE`・`seeds=RULES.seeds`・K_fit は実 bank から（`== N_FIT//M_FIT == FIT_K` を要求）・K0／K1／m＝RULES；self-test は `--selftest-B`／`--selftest-B-KDE` で分離し `D3C_PASS` に昇格しない |
| 資源 | 段階別 RSS（psutil／getrusage）と時間を record に記録；launcher は入力を `/content/stage` に 1 回複製（unique ≈12.3 GB；bytes／配列 SHA の再検証は同一）してから intake（intake の多重 open を Drive でなくローカル disk に向ける）；High-RAM を `vm.total>30 GB` で要求（十分性は保証しない） |
| read-only・publication・fallback | 入力 root と phaseB root を保護（OUT が交差すれば rc 2・何も書かない）；record／plan identity は `_publish_json`（全内容照合）；notebook は record 欠落／不正を fallback False で記録 |
| 評価なし | 閾値・Q／logD・label・較正・D-2W・noise のコードはない |

## 2. `d/d3c_profile.py`
| 段階 | 内容 |
|---|---|
| preflight（REQUIRED 18） | `G_pins_loaded`・`G_engine_inventory`・`G_script_sha`・`G_phaseC_members`・**`G_env_lock`**（登録 6 版（CAMB 含む）＝pins＝`official_gate.EXPECTED_VERS`・pool）・`G_external_loader_sha`・`G_twelve_context`・`G_bank_spec_v2`・**`G_d3b_units_accepted`**（`intake_registered_d3b_units`：ledger＋配列受入れ receipt＝pins）・**`G_inputs_resolved`**（D-2 root の registry：family・formal・ledger unit の manifest SHA；D-3b root 3 つ：family／size・formal・ledger partition の manifest SHA・spec v2）→ `G_all_supplies`・`G_uids_ordered`・`G_plans_fixed`・`G_size_inputs`・`G_family_assembled`・`G_gate_passed`・`G_identity_stable`・`G_record_saved` |
| intake | spec v2 の family×size の 108 行を size／position 順に：第 1 波（`reuse_D2_fixed_input`）は `intake_registered_covariance`（D-1；roots）＋D-1 sidecar（genuine）→ `intake_registered_bank(formal)`；追加（`generate_D3b`）は `intake_twelve_covariance` → `intake_twelve_bank(formal, registered_units)`；両 system。供給 72（formal）／24（self-test 1 size）。record に各供給の origin／receipt／cov SHA／manifest／cluster 数／ledger・receipt SHA |
| UID／K_fit | 先頭供給の UID 列を batch 別に分割（K0／K1）し，全供給で **ordered 一致**・batches／m 一致・fitting cid 一致；各 UID の purpose 200／family group／batch／rotation index＝位置；formal は K0＝N₀/m・K1＝(N_max−N₀)/m・K_fit＝N_fit/m_fit＝2000 |
| plan | `fix_family_plans(table, F, {0: uids_b0, 1: uids_b1}, K_fit, master_seed, B, B_KDE)`；identity 検証＋ordered UID tuple からの再構築一致 |
| 組立て・gate | `build_twelve_size_input` × 6 → `assemble_twelve_family`（formal：`full_surviving_scope=True` 要求）→ `input_fingerprint`／`input_snapshot` → gate（official／smoke）→ 再 fingerprint・`verify_plan_identity` |
| 出力 | `d3c_profile_record_<F>.json`（gate record 全文・供給・UID・fingerprint 前後・RSS／時間・identity）・`d3c_plan_identity_<F>.json`（publication receipt を record に束縛）・stdout log。`D3C_PASS`＝production_official∧self-test なし∧REQUIRED 全 True∧rc 0 |

## 3. notebook
lock：commit・inventory・FAMILY・`D2_RUN_ROOT`（`out/d2`）・`D3B_RUN_ROOTS`（3 size の `out/d3b`）・`STAGE_LOCAL`。cell 1：checkout／clean／inventory・script／ledger／receipt の SHA＝inventory・root が D-2 ledger／D-3b ledger の run root と一致・登録環境（CAMB 含む）・RAM 総量 >30 GB。cell 2：staging（任意）→ script（production_official；self-test flag なし）→ record の型検査付き読込み（fallback）→ `profile_pass`＝rc 0∧`D3C_PASS`∧gate passed∧fallback なし。cell 3：zip（record・plan identity・lock・stdout／stderr；配列なし）。

## 4. 試験（`tests/test_d3c_tranche1.py`；8 case）
- end-to-end（外部資産要）：D-2 self-test bank（E2 全 size；scale 0.001）＋D-3b self-test bank（E2 L1.00）→ self-test profile（1 size）：stage complete・`D3C_PASS False`・smoke gate passed（live_collected；plan identity／share／pc1／twelve per size の check passed）・供給 24（旧 6＋新 18）・UID（K0 10／K1 30／K_fit 2）・fingerprint 前後一致・publication receipt・plan file の内容；別 process での plan 再構築一致・逆順で別 identity と `verify_plan_identity` の拒否；拒否系：OUT が入力／phaseB と交差（rc 2・未書込み）・size root 欠落（stage inputs）・formal 経路（sandbox では環境 gate で停止；env skip では非 formal bank が ledger に解決せず stage inputs・供給なし）・他 family／E1・生成後に変更された bank（intake で例外；gate なし）。
- notebook cell 2 の条件 7 case（rc／`D3C_PASS`／gate／fallback；引数に self-test flag が無く `--d3b-root` 3 つ）。
- 全 suite：§5。

## 5. 全 suite
**1595 case（1587＋8）全 pass**，failure／error／skip 0（15 chunk・JUnit `regression_logs/d3c_t1_pytest/j1..15.xml`；case の多重集合＝collect と一致）。

## 6. 提出物・次段
- 実行前監査で確認を求める点：(a) 実装条件 §1 の反映，(b) 入力解決と formal intake の束縛（D-2 ledger unit・D-3b ledger＋receipt），(c) plan 固定の記録形式（ordered UID 列からの再構築），(d) staging（ローカル複製）が検証を弱めないこと，(e) 実行 commit／inventory の固定。GO 後：Colab High-RAM で E2 → E7 → E8（1 family 1 run）→ 実行後監査 → tranche ②（plan identity・gate record・fingerprint の登録）。
