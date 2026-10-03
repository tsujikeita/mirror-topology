# Phase D-3c 設計 v0.1：実 bank による 12 位置 profile・official gate・5 seed plan の固定（Colab；配列計算なし・label なし）
2026-10-03。Claude 作成。ChatGPT 宛（設計方針の受入れと tranche ①開始 GO の依頼）。前提：D-3b 外側 receipt（配列検証付き受入れ；`registered_assets/d3b/d3b_outer_receipt.json` payload `7c42bc11…`）・D-2 外側 receipt・tranche ②b（profile／plan schema／spec v2／receipt）・D-3a 登録 intake。本段は **既存の受入れ済み API だけで実 bank を消費して profile を組み立て，gate を通し，plan identity を固定して記録する**段であり，新しい数値 kernel・生成・較正・label・閾値は含まない。

## A. 範囲
| 項目 | 内容 |
|---|---|
| 対象 | family E2／E7／E8（E1 は第 1 波のみ；12 位置段階なし）。各 family：3 size × 12 位置＝36 配置 × 2 system（matched／native）。 |
| 入力（全て固定・再生成なし） | (i) 第 1 波 3 配置／size：D-2 bank（`cfg<id>_b0/b1/fit`）＋D-2 family reference（`ref_<F>_b0/b1/fit`）→ `d2_bank.intake_registered_bank(formal=True)`（roots＝D-1 `intake_registered_covariance`，`cov_manifest`＝D-1 sidecar；canonical spec v1・D-1 receipt 束縛）；(ii) 追加 9 配置／size：D-3b bank → `d3_bank.intake_twelve_bank(formal=True, registered_units)`（roots＝`intake_twelve_covariance`；ledger unit＋**配列受入れ receipt** 束縛；reference は同じ D-2 family reference を ledger identity で再検証）。 |
| 組立て | `build_twelve_size_input(ctx, F, size, system, 12 supplies, plans, fit_plans)` × 3 size × 2 system → `assemble_twelve_family(ctx, F, {size: (fm, fn)})` → (fm, fn, identity：registry／manifest／map／twelve assets／receipt SHA・`full_surviving_scope=True`)。 |
| plan 固定 | `fix_family_plans(table, F, {0: uids_b0, 1: uids_b1}, K_fit=2000, master_seed=20260912, B=RULES.B=2000, B_KDE=2000)`：family evaluation latent の**実 cluster UID**（40 000；全 12 配置・全 size・両 system で同一であることを intake 後に要求）から 5 seed の BootstrapPlan／FittingPlan を一度だけ構築し，identity（`d3_plan_identity_v2`；strata UID SHA・multiplicity SHA・rng key）を記録。同 family の第 1 波・追加配置・両 system で共有。 |
| gate | `twelve_official_gate(fm, fn, "official", plan_identity, table)`（live 環境：登録版 6 種・BLAS pool・rules binding・profile check：m／N₀／N／B／N_fit／B_KDE／fitting bound／grid identity／cov binding／full size scope＋12 位置 check＋plan identity）→ `GateRecord`（passed／required_failures／diagnostics）。`formal_runner.input_fingerprint(fm)`／`(fn)` と `input_snapshot` を記録。 |
| 出力 | `d3c_profile_record_<F>.json`（intake 情報：各 unit の manifest SHA・receipt SHA・root SHA・D-2／D-3b の ledger／receipt identity；UID 集合の SHA；plan identity；gate record 全文；input fingerprint；環境；時間）＋`d3c_plan_identity_<F>.json`。配列は保存しない。 |
| 含まないもの | `run_family_formal`（閾値 t1／t2・label），較正（D-4 driver），D-2W・noise，第 1 波 3 配置の再生成，f32 経路（12 位置 profile は f64）。 |

## B. script と notebook（tranche ①で起草）
- `d/d3c_profile.py`：D-2／D-3b script と同じ preflight（pins／inventory／script SHA・Phase C members・**登録環境 hard gate**（gate が live 版を要求するため CAMB を含む 6 版と pool）・凍結 loader・`twelve_context`・spec v2・`intake_registered_d3b_units`（配列受入れ必須）・D-2 ledger／receipt 束縛・A10 cross-check は不要（生成しない）），入力 root（D-2 run の `out/d2`，D-3b 3 partition の `out/d3b`）の存在と ledger との一致，出力隔離（入力側へ書かない），全内容照合付き publication（`_publish_json`）。self-test flag は `--selftest-small`（合成小規模 bank；formal=False・gate は smoke）のみで，`D3C_PASS` は production_official＋self-test なし＋gate passed のとき。
- `d/MirrorTopology_Step1_D3c_profile_v0.1.ipynb`：lock（commit・inventory・FAMILY・D2_RUN_ROOT・D3B_RUN_ROOTS 3 つ）；**High-RAM CPU runtime**（§D）；1 family 1 run。
- 試験：合成小規模 bank（TEST-ONLY kernel；D-2 形式の旧 3＋D-3b 形式の新 9）で end-to-end（intake→size input→assembly→plan 固定→gate smoke）；plan identity の再現性（同 UID→同 identity，UID 1 つ違い→別 identity）；formal 経路の拒否（非 ledger unit・receipt なし）；出力隔離；notebook 条件。

## C. 受入れ条件（run ごと）
rc 0・stage complete・`D3C_PASS True`・gate `passed=True`（required_failures 空；診断の全 check passed）・両 system の plan identity 一致（同一 object）・identity の `full_surviving_scope=True`・36 配置 × 2 system の cov binding・UID 集合＝D-2 reference と同一・入力 unit の manifest SHA＝ledger（D-2・D-3b）・plan identity file の publication receipt。

## D. 容量・時間（見込み；保証ではない）
- RAM：1 supply＝T1／T2 × model／ref × 4×10⁶ × 8 B＝128 MB（＋fitting 6.4 MB）→ 36 配置 × 2 system ≈ **9.5 GB** を FamilyInput が保持（`assemble_all_sizes` の連結で一時的に 2 倍程度）→ **High-RAM runtime（51 GB）を要求**；通常 RAM（12.7 GB）では不可。
- 読込み：D-3b 27 unit（3.0 GB）× 3 size＋D-2 9 配置＋reference（≈3.4 GB）＝ ≈12.5 GB／family → Drive から 15〜30 min（read-only 検証の実測 2.5〜5 min／3 GB から外挿）。intake の再検証（bytes SHA・配列 SHA）を含む。
- 1 family 1 run × 3 run。

## E. 監査に確認を求める点
1. plan 固定を **family 単位**（family evaluation group の latent；第 1 波・追加・両 system で共有）とすること（tranche ②b の `fix_family_plans` の設計どおり）。
2. 第 1 波 3 配置の供給は D-2 `intake_registered_bank`（D-1 sidecar・spec v1）経由とし，12 位置 size input の receipt 照合（file／array SHA）はその cov_manifest で満たすこと（受入れ済み `test_audit_d3b_t1` の old3＋new9 統合試験と同じ経路）。
3. gate 通過後の記録（plan identity・input fingerprint）を「較正前に固定し target まで不変」の identity として登録資産に置く段（tranche ②）を，実行後監査の後に分けること。
4. B／B_KDE＝2000・seeds 5・K_fit 2000 は rules／official_gate の登録値から取り，script 引数にしない。

## F. v0.1.1 追記（監査 `Step1_PhaseD_D3b_tranche3_0.96.0_decision.json`：設計受入れ＋実装条件；tranche ①で反映）
- gate 呼出しは keyword：`twelve_official_gate(fm, fn, mode="official", plan_identity=plan_identity, table=table)`（第 4 位置引数は env；正式 script は env を注入せず `environment_source="live_collected"` を要求）。本文 A の呼出し例はこの形に読み替える。
- 実行順：formal intake（全供給）→ **ordered** UID（batch 別 10 000＋30 000・rotation index 順）／K_fit 照合 → family で 1 回の plan 構築 → size input 6 → 全 size 組立て → fingerprint → gate → gate 後の identity 再確認 → publication。
- E2：第 1 波の供給は `intake_registered_bank` の返す unit manifest（b0／b1／fit・reference）を spec v2 の `configurations[cid].d2.units`／`family_reference.units` に照合する（wrapper の接続条件）。
- E3：plan identity は hash だけでなく **ordered UID 列・key・定数・source／環境** を記録し，別 process での再構築が全 strata／multiplicity SHA を再現することを要求する。
- E4：B／B_KDE／seeds／N_fit／m_fit は登録定数（`rules_config.RULES`・`official_gate`）から取り，実 K_fit＝N_fit／m_fit を確認；self-test の値は分離し `D3C_PASS` に昇格しない。
- 資源：保持 payload の算術は **13.152 GB**（評価 T 9.216＋fitting 0.576＋評価 multiplicity 3.2＋fitting multiplicity 0.16）；全 size 組立ては配列を共有する view（連結しない）。intake は同じ NPZ を複数回開く（D-3b 配置 2〜3 回，D-2 配置 3〜4 回，reference 3〜2 回：size 加重 open 量 ≈95.5 GB／family）ため，launcher は入力を **ローカル disk に 1 回複製**（unique ≈12.3 GB）してから読む（検証は同一：bytes／配列 SHA）。51 GB High-RAM の十分性は保証せず，段階別 RSS を記録する。
- 「配列計算なし」は「新しい物理共分散・MC bank の生成なし」に限定（root 再検証・hash・bootstrap multiplicity 構築は本段でも行う）。

## G. v0.1.2 追記（監査 `D3c_tranche1_0.97.0_audit_decision.json`：R-D3C1-A〜E；tranche ① v2 で反映）
- 資源（R-E）：plan identity の roundtrip 再構築（ordered UID からの `fix_family_plans` 再実行）は，照合の間だけ追加の multiplicity（評価 5×2000×40 000×8 B＝3.2 GB＋fitting 5×2000×2000×8 B＝0.16 GB＝**3.36 GB**）を保持する → 算術上の一時 peak は **16.512 GB**（13.152＋3.36）；照合直後に解放し，以後は 13.152 GB に戻る。script は段階別 RSS に加えて `ru_maxrss` の peak を記録する（実測は Colab 実行の record で示す；51 GB の十分性は保証しない）。
- plan object（R-C）：size input 6 本と組立て後の両 system が `fix_family_plans` の返した**同一 dictionary object**（評価 plans・fitting plans とも `is`）を持つことを gate 前後で要求する（内容 identity の検証と併置；値が同一の別 object は拒否）。
- 出力契約（R-D）：`--mt`／`--phaseb`／`--phasec`／入力 root を出力作成前に保護（realpath の包含）；指定 OUT が symlink なら拒否；既存の空 directory は受け入れる。
- launcher（R-A／B；v0.1.3 で v2 監査の launch-boundary／output-anchor を反映）：1 attempt＝**lock の出力先（anchor）の先行検証（不合格なら何も書かない）**→ attempt ID＋initial 非成功 record（anchor にのみ）→ 実行設定と live source（HEAD・file SHA）の lock 再照合 → staging（容量検査）→ **同じ再照合を起動の直前にもう一度** → 起動（attempt ID と lock SHA を script に渡す）→ record の semantic 検証と lock／attempt への束縛（plan document の pins も）→ final record。前回の final record は退避し，今回の証拠にしない。peak RSS は `ru_maxrss`×1024／1e6（十進 MB）。
