# Phase D-4 正式較正（global false-support 較正；rules §9）実行設計 v0.1 — 登録 bank・登録 profile・封印 driver の接続と Colab 実行の工程
2026-10-04。Claude 作成。ChatGPT 宛（設計の受入れと tranche 開始 GO の依頼）。前提：D-3c tranche ② v2 受入れ（`D3c_tranche2_v2_0.101.0_audit_decision.json`：登録 API 受入れ・**D4_design_GO=true**・`D4_formal_calibration_execution_GO=false`）。本文書は**実行設計**であり，engine 0.66.0 で受入れ済みの D-4 接続（`Step1_PhaseD_D4_design_v0.1.md`／`Step1_PhaseD_D4_completion.md`：D4-1 較正先行 driver・D4-2 pseudo 側 12 位置 archive・D4-3 登録 asset 再利用・D4-4 参照鎖・D4-5 共分散 intake）を**実 bank で正式に実行する**ための工程を固定する。新しい統計量・閾値・判定規則は導入しない（rules §0.4 の設計変更は含まない；§D.4 の driver 分割は数学的手順を変えない実装拡張として監査に諮る）。

## A. 到達点と主張の範囲
- **到達点**：rules §9.4 の「実観測の full-grid 判定値を封印したまま global 較正・監査 → calibration usable を封印」。すなわち `calibration_first.calibrate_sealed`（mode `official`・全 family・固定 n_pseudo＝2000・12 位置分岐込み）を，受入れ済みの固定入力だけから組み立てた実 bank 入力で実行し，封印 record（calibration summary・usable_support／usable_strong・per-pseudo status・fingerprint・pseudo 列 SHA・target commitment）を登録資産に置く。
- **主張しないもの**：実観測 target の評価（Phase E：`evaluate_sealed_target`・nonce 開示・label 解放），閾値 3／10 や usable 閾値の変更，noise stress（Phase E robustness），E1 の 12 位置 profile，較正値の事前予想。

## B. 入力の棚卸し（受入れ済み／未了）
| 入力 | 状態 | 束縛（消費時に再検査するもの） |
|---|---|---|
| 第 1 波共分散 30 配置（D-1） | 登録済み（`registered_assets/d1/`・receipt） | `production.intake_registered_covariance`（file／array SHA・sidecar・幾何・PSD・root） |
| 第 1 波 bank（D-2；E1／E2／E7／E8 × 3 size × 3 位置；eval b0／b1・fit・family reference・**W₂ raw 27 unit**） | 登録済み（D-2 ledger・outer receipt；配列検証付き） | `d2_bank.intake_registered_bank(formal=True)`（D-1 sidecar・spec v1・ledger unit） |
| 追加 9 位置共分散 81（D-3a）＋PC-1 | 登録済み（`registered_assets/d3/`；receipt） | `d3_profile.intake_twelve_covariance` |
| 追加 9 位置 bank 243 unit（D-3b） | 登録済み（ledger＋配列検証付き outer receipt） | `d3_bank.intake_twelve_bank(formal=True, registered_units)` |
| 12 位置 profile・plan identity（D-3c；E2／E7／E8） | 登録済み（`registered_assets/d3c/`；ledger／receipt／acceptance pins） | `d3c_ledger.intake_registered_d3c_profiles` → `rebuild_registered_plans` → `verify_consumer_family_inputs`（**実 FamilyInput から fingerprint を計算**；低水準の文字列比較だけで代用しない） |
| 12 位置 manifest asset（B-3-2；E2／E7／E8） | 登録済み（`REGISTERED_RECEIPTS["B3_2A_7240c06f255c"]`） | `intake_registered_twelve_assets`（receipt 束縛；再生成なし） |
| 共有 null asset・校正 bank の μ／W（B-3-2） | 登録済み（`registered_assets/b3_2_shared_null_asset.json`） | `W2Context.validate(expected_context_sha256)`（asset SHA） |
| **W₂ case 判定（D-2W）**：9 case（E2／E7／E8 × 3 size；matched primary；native／CRN は診断）の OT 距離・B_final（prefix 規則）・same-subset f32 感度・trigger | **未了**（27 raw W₂ unit は D-2 で生成済み；case 側の OT・停止・trigger は未実行） | 登録 `W2Context`（case ごとの `VerifiedW2Decision`・manifest・shared null 束縛）；receipt で pins に束縛 |
| **pseudo 列**（等方・独立 stream・m＝1・n＝2000；`d2_bank_spec.pseudo_column`） | **未了**（「Phase E 開始時に生成・封印」と規定） | 生成 record（stream key・環境・kernel 束縛）＋列 SHA（T1／T2）；receipt で pins に束縛；driver は `thresholds.pseudo.sha256_T1/T2` に記録 |
| 観測 target（t_target＝(39.67178834527284, 259.3375006282747)；rules §2） | 凍結（公知；rules §0.2） | commitment＝SHA-256(canonical [t1,t2] ∥ nonce)；nonce は先生が選び Phase E まで非公開 |

## C. 工程（tranche）
| tranche | 内容 | 成果物 | 監査 |
|---|---|---|---|
| **D4C-0a：D-2W（W₂ case 受入れ）** | 27 raw W₂ unit → 登録 μ／W で whitening → 9 case の exact 2D W₂（POT）・B＝200…1000 prefix 停止規則・3 seed × 2 n_sub 安定性 gate・same-subset f32 感度・event-ratio は較正側で評価するため含めない → `VerifiedW2Decision`（trigger／unresolved／技術 FAIL）→ `W2Context` の登録（asset・manifest・decision・identity）。script `d/d2w_cases.py`＋notebook（Colab CPU；OT は n_sub 5000 で小さい）。 | `registered_assets/d2w/`（case record・context JSON）・pins `w2_context_sha256` | 実行前監査 → Colab → 実行後監査（受入れ） |
| **D4C-0b：pseudo 列の生成・封印** | 凍結 kernel（`LegacyKernel`・C_iso）で等方 pseudo 観測 2000 件（独立 stream；CRN 表に purpose `pseudo`・group を追加するか，別 master を登録するかは §E.2）；(T₁,p, T₂,p) の f64 列・AX／PL・stream key・環境を record；列 SHA を封印。script `d/d4_pseudo.py`。 | `registered_assets/d4/pseudo/`（NPZ 小・record）・pins `pseudo_columns_sha256` | 実行前監査 → Colab（短時間）→ 実行後監査 |
| **D4C-1：較正 driver の接続 script（sandbox）** | `d/d4_calibrate.py`：preflight（pins／inventory／script・Phase C・登録環境 hard gate・凍結 loader・`TwelveContext`・D-3b units・D-3c profiles・W2Context・pseudo 列・twelve asset receipt）→ 全 family の第 1 波 views（`d2_bank.intake_registered_bank` → `production.build_family_input`（size ごと・両 system）→ `assemble_parent`）＋E2／E7／E8 の twelve inputs（`build_twelve_size_input`×6／family；plan は **`rebuild_registered_plans` で再構築**し `verify_consumer_family_inputs` で両 fingerprint・plan identity・object・UID を照合）→ **live official gate**（第 1 波：`require_official`；12 位置：`twelve_official_gate(mode="official")`；過去の gate record は代用しない）→ `calibrate_sealed(mode="official", commitment, twelve_inputs, twelve_assets(receipt))` → 封印 record の publication（content-addressed archive＋外側 record）；段階別 RSS／時間。self-test（合成小規模 bank・smoke）と拒否系試験。**§D.4 の分割実行**をここで実装する。 | script・notebook・試験・報告書 | 実装受入れ＋実行前監査 |
| **D4C-2：Colab 正式実行** | High-RAM CPU；§D.4 の単位（family ごとの sealed partial → combiner）；各 run の record を zip で回収 | 封印 record（combined）＋family partial record | 実行後監査（calibration usable の受入れ） |
| **D4C-3：封印 record の登録** | 原本登録・決定論的 ledger・pins 束縛（D-3c tranche ② と同型）；Phase E の `evaluate_sealed_target` の入力 | `registered_assets/d4/calibration/` | 実装受入れ |

順序：D4C-0a と D4C-0b は独立（並行可）。D4C-1 は両者の登録後に実行前監査（script は先行して起草可）。Phase E（target 評価・label）は本設計の外。

## D. D4C-1 の設計要点
### D.1 消費の束縛（監査 handoff 4 条件）
1. `intake_registered_d3c_profiles(root, ctx)` → family ごとに `rebuild_registered_plans(profiles, F, table)`（plans／fit_plans＋identity）→ 6 size input を同じ object で組み立て → `verify_consumer_family_inputs(profiles, F, fm, fn, identity, table=table)`（gate record は渡さない：**live gate を別に実行**）。失敗は停止（record に理由）。
2. live official gate：第 1 波は family ごとに `require_official(parent_m, parent_n)`（runner 内でも再実行される），12 位置は `twelve_official_gate(fm, fn, mode="official", plan_identity, table)`；`environment_source=="live_collected"`。
3. 固定性の監視：runner の `fingerprints.at_gate`／`at_end`（第 1 波 case・parent・`twelve:<F>/<size>`）と，script 側で較正前後の `input_fingerprint`・`plans is`／`fit_plans is`・`verify_plan_identity` を再確認；不一致は FAIL record（成功を書かない）。
4. 登録定数：B／B_KDE／seeds／K_fit／N₀／N_max／m／n_pseudo は `RULES`／`official_gate` から取り，引数にしない。

### D.2 commitment と封印
- 先生が nonce（≥16 文字；乱数）を手元で生成し **cell 0 に入力しない**（launcher は commitment の 64 hex のみを受け取る；`commit_target(t_target, nonce)` は先生のローカルで計算するか，notebook の別 cell で計算して値だけを残す）。commitment は封印 record に記録され，Phase E で nonce と target を開示して照合する。rules §0.2 のとおり target は公知であり，commitment は driver 内の依存順序の記録である（完了記録 §3 の限定を維持）。
- 封印 record：`RunManifest`（stage `calibrate_sealed`）を content-addressed archive に保存し，その SHA・ref・pseudo 列 SHA・dependencies（registry／manifest／W2 context／twelve asset／families／sizes）・fingerprints を外側 record に写す。

### D.3 出力
`d4_calibration_record.json`（REQUIRED gate・intake 束縛・gate record（family ごと）・fingerprint 前後・calibration summary（support／strong の c／u／n・Wilson 上端・usable）・per-pseudo status の集計（valid／unresolved／技術 FAIL 件数）・12 位置分岐の件数（family 別）・RSS／時間）＋archive（pseudo 側 12 位置完全 Result を含む；容量は実測）。技術 FAIL が 1 件でもあれば較正は FAIL（値を出さない；rules §9.2）。

### D.4 資源と分割（監査に諮る）
- 保持 payload の算術：第 1 波 view（4 family × 3 size × 3 位置 × 2 system × 128 MB ＋ fitting）≈ **9.4 GB**；12 位置入力（E2／E7／E8 × 36 配置 × 2 system × 128 MB）≈ **27.6 GB**＋multiplicity 3 family × 3.36 GB ≈ 10.1 GB → 単一 process で全 family・全 12 位置入力を同時保持すると **≈47 GB＋一時領域**となり，High-RAM 54.75 GB（D-3c 実測 peak 19.4 GB／family）では不足する可能性が高い。
- 提案 **(a) family 分割**：`calibrate_sealed` を family 単位の sealed partial record（同じ commitment・同じ pseudo 列 SHA・同じ dependencies；family の per-pseudo truth／status・12 位置分岐・full Result archive）に分け，combiner が全 family の partial（E1／E2／E7／E8）を照合（commitment・pseudo SHA・dependencies・source・環境の一致，family 集合＝登録全 family）して FWFSR（any-family）と Wilson 上端・usable を計算する。per-pseudo の集約規則（rules §9.2 表 5：True→1／全 False→0／unresolved→[0,1]）は family 独立の truth から決まるため，分割は数学的手順を変えない。合成 bank で単一 process 結果との完全一致を試験する。1 run の peak は D-3c と同程度（≈20 GB）＋pseudo 評価の一時領域。
- 代替 **(b) 単一 run**：`np.load(mmap_mode)` が使える形式へ bank を再保存する必要があり（NPZ は memmap 不可），登録 bytes と別の派生物を増やすため採らない。
- 時間：pseudo 2000 × family の truth 評価（sorted-T₁ 表・再抽出行列・KDE；再走査なし）と 12 位置分岐（trigger した family・pseudo のみ）の所要は **D4C-1 の self-test と D-3c 実測から外挿**して実行前監査で示す（本設計では保証しない）。

## E. 監査に確認を求める点
1. **D4C-0a／0b を較正の前提として独立 tranche にすること**（D-2W の case 判定と pseudo 列の封印を較正 run に混ぜない）。
2. **pseudo 列の乱数**：CRN 表（`d2_crn_table.json`，master_seed 20260912）に purpose `pseudo` の group を**表を更新して追加**する（表 SHA が変わるため D-2／D-3 の plan identity が参照する `crn_table_sha256` との整合を，旧表 SHA の記録として保持）か，pseudo 専用の別 master／表を登録するか。推奨：**別表**（`d/d4_pseudo_table.json`）とし既存表を不変に保つ。
3. **§D.4 (a) family 分割**の採用（driver の拡張は接続受入れの対象；amendment ではない）。
4. event-ratio trigger（P_k の比 > 2・zero-hit 規則）は pseudo ごとに runner 内で評価され，W₂ trigger は bank 固有（pseudo 非依存）として D-2W の登録判定を用いること。
5. 技術 FAIL（NaN・KDE failure 等）1 件で較正 FAIL とし，再試行は原因記録と amendment 無しの実装修正に限ること（rules §9.2・§0.4）。

## F. 限定
本設計は工程と束縛の固定であり，較正値・usable の可否・label を予断しない。D4C-1 の sandbox 試験は合成 bank の smoke であり，実 bank の official 経路は Colab 実行と実行後監査で初めて確認される。
