# Step 1 Phase D — D4C-2b 原本登録 tranche 設計 v0.1（engine 0.113.0）

起草：2026-10-08（Claude）。根拠：監査 `D4C2_screen_certificate_0.112.0_acceptance.json`（決定 `SCREENS_AND_AUTHENTICATED_FIXED_CAMPAIGN_INFEASIBILITY_ACCEPTED__REGISTRATION_DRAFTING_AND_TESTS_GO`，SHA-256 `3b6c839d…`）の `registration_conditions` 9 項目と `GO.originals_repo_registration_tranche_drafting`。本 tranche は **起草・実装・試験・原本保管**のみであり，登録 packet の実装受入れは別途（条件 9）。Phase E／target 解放・規則変更・W₂／pseudo 再生成は含まない。数値 kernel は不変。

## 0. 登録対象（すべて byte 同一で保管；条件 1）
| 区分 | 登録先（`registered_assets/` 以下） | 内容 |
|---|---|---|
| 固定 source epoch | `d4c2/source/B2_completion_inventory_0.112.0.json` | 実行時 inventory（SHA `aa2c11cc…`；commit `ba51e595`；engine 0.112.0）の歴史的写し |
| screen 3 件 | `d4c2/screens/runs/{E2,E7,E8}/`（lock・final・stdout／stderr・`run_<attempt>/{record,run,stdout.log}`），`d4c2/screens/archives/d4c1_screen_<F>_ba51e5951ebb.zip`，`d4c2/screens/notebooks/…_executed_ba51e5951ebb.ipynb`，`d4c2/screens/bundle/d4c1_results.zip` | E2 attempt `20261007T113430Z_d4d346bde9`，E7 `20261007T143438Z_a2d3767433`，E8 `20261007T145023Z_6a25812f53`；各 2000 行・2000 blocking・N0／N4 完全被覆 |
| certificate | `d4c2/certificate/{command.txt,stdout.txt,stderr.txt,rc.txt,out_20261007T152500Z/{d4c1_certificate_record.json,d4c1_certificate_run.json,d4c1_certificate_stdout.log}}` | 内容 SHA `4a249ee6…`；consumer 環境（Python 3.11.15）は metadata として記録（環境 gate 外の専用入口） |
| 提出物 | `d4c2/results/{D4C2_screen_certificate_0.112.0_results.zip, D4C2_screen_certificate_report.md, file_map.json}` | 監査に提出した packet・report（原本 byte 保持；§5(iii) の訂正は別 erratum） |
| 受入れ文書 | `d4c2/acceptance/{ChatGPT_audit_…md, …_acceptance.json, …_audit_evidence.zip, …_execution_decision.json, …_execution_settings.json}` | 実行 GO（`0477d7b2…`）と今回の受入れ（`3b6c839d…`） |
| bridge 原本（既存；維持） | `d4c1/probes/20261006T115712Z_69ece7cef3/`（zip・実行済 ipynb・比較 report JSON・bridge report md・監査 md・bridge 受入れ json・evidence zip・file_map） | producer commit `39082b64`／0.110.0／Python 3.13.16；受入れ `ACCEPTED_WITH_EXPLICIT_SCOPE__FIXED_E2_FIRST3_ENVIRONMENT_BRIDGE`（`325f1ad3…`） |
| 登録文書 | `d4c2/d4c2_ledger.json`，`d4c2/d4c2_outer_receipt.json` | 決定論的再導出（§2） |

監査資料と bridge 原本は実行 campaign 完了まで running source tree の外に保管し，本 tranche で初めて tree に登録する（歴史 byte の保持；旧 record を新版へ再ラベルしない：条件 2）。

## 1. module `step1_engine/d4c2_registry.py`（新規；`checkpoint.MODULES` 登録）
D4C-0 登録 tranche（`d4c0_registry.py`）と同じ型：**定数（受入れ文書・原本から転記）→ byte 層検査 → 意味層検査 → 決定論的 ledger／receipt → pins guard → registered loader**。

### 1.1 定数
- `SOURCE`：固定 epoch（commit `ba51e5951ebb…`，engine `0.112.0`，inventory file／SHA，script `d/d4c1_calibration.py` SHA `81455779…`，pins SHA）。
- `SCREENS[F]`：attempt，登録 dir，member 別 SHA／bytes，inner archive，実行済 notebook，`execution_lock`（lock file SHA・commit・`registered_assets_sha256` map 等），`screen`（内容 SHA・file SHA／bytes・`n_blocking`・`w2` 要約・`config_ids`・registry／manifest／W₂ context SHA・pseudo identity・`ratio_bound_max`・`min_P`），run／final file SHA，D-2 run id／registry SHA。
- `CERTIFICATE`：member，内容 SHA，record file，run file SHA，n＝2000，閾値，`n_rows_admitted`／`n_rows_proven`，levels（support 81／strong 12・proven 2000・technical 0），campaign／commitment，`sources`（3 screen の typed identity），`consumer_environment`，command SHA。
- `RESULTS`，`ACCEPTANCE`（5 文書），`BRIDGE`（member・producer・受入れ決定・new partial payload）。
- `SCREEN_REQUIRED`（20）／`CERT_REQUIRED`（12）：0.112.0 driver の `REQUIRED_SCREEN`／`REQUIRED_CERTIFICATE` を AST で抽出した定数（試験で driver と等値を検査）。`FLAGS`：script の成功 flag 集合。
- `REGISTRATION_PINS`＝(`d4c2_ledger_sha256`, `d4c2_outer_receipt_sha256`, `d4c2_acceptance_sha256`, `d4c2_execution_decision_sha256`, `d4c2_certificate_sha256`, `d4c2_bridge_acceptance_sha256`)。

### 1.2 byte 層（条件 1・4）
`_check_files`（登録 dir の member 全件：SHA／bytes 一致・欠落なし・**余分なし**），`_check_archive`（inner zip の SHA／bytes と member 名＝登録 file），`_check_doc`（notebook・packet・report・受入れ文書の SHA／bytes）。`_check_source`：歴史的 inventory の写しの SHA と内容（engine・commit・module SHA map・registered_assets SHA map）。

### 1.3 意味層（条件 2・4・5・6）
- `_registered_context`：D4C-0 loader による登録 W₂ decision 全文・pseudo 列（T1／T2 paired identity），tests/assets の grid registry／manifest，`ctx.d2_spec` の configuration id。
- `_check_screen(root, ctx, F, src, rc)`：lock（schema・commit／engine／inventory／script／pins＝SOURCE・family・全範囲・campaign／commitment・`registered_assets_sha256`＝歴史 inventory・D-2 run root＝登録 D-2 ledger）→ final（この attempt・lock 同一・complete／exit 0／fallback なし／gates ok・precheck／prelaunch の live source＝SOURCE・record SHA＝run bytes）→ run record（mode screen・formal・probe／selftest／instrument なし・`required_inventory`＝`SCREEN_REQUIRED` 完全一致・全 gate True・成功 flag・attempt／lock 束縛・source＝SOURCE・登録環境（`recorded_environment_registered`：現行または登録履歴）・published evidence＝screen record bytes・D-2 入力＝登録 ledger・screen 要約）→ screen record 本体（provenance＝歴史 module SHA；`bind_screen_record` により登録 W₂ decision から再導出した要約との typed 等値・paired 列・grid・config id・campaign；rows＝[0,2000) 正確に 1 回；W₂ 前提（True なし・unknown ≥1）；blocking 行＝全行・条件付き status `unknown_or_technical`；包絡統計＝定数・max ≤ 2.0・min_P ＞ 0）。
- `_check_certificate(root, src, screens, rc)`：command（`--mode certificate`・`--screen`×3・commitment／campaign・禁止 option なし）・rc＝0・stderr 空 → run record（mode certificate・formal・`CERT_REQUIRED`・source＝SOURCE・published evidence・consumer 環境 metadata＝定数・環境 gate 不一致の記録）→ record（`check_certificate` の純粋算術 checker **と**，認証済み screen からの独立再導出 `aggregate_rows`／`_levels_from_rows`／`infeasibility_certificate` の等値；sources＝3 screen の typed identity・順序；global 行 1 回計数；technical 0；usable＝True 不能＝True）。算術 checker と証拠認証の分離（条件 4）。
- `_check_acceptance`／`_check_bridge`：受入れ文書の内容（決定・subject・accepted_screens／certificate の identity）＝定数＝原本；bridge 原本＝bridge 受入れ文書の `original_inputs`・比較結果 `BRIDGE_CONTRACT_SATISFIED`。

### 1.4 ledger／receipt／pins（条件 3）
- `build_d4c2_ledger(root, ctx)`：上記を全件実行し決定論的 ledger（source・module SHA・screens・certificate・acceptance・bridge・registered_context・statement・`ledger_sha256`）。`verify_d4c2_ledger`：再導出と typed 等値。
- `build_d4c2_outer_receipt(root, ctx, ledger=None)`／`verify_d4c2_outer_receipt`：ledger payload SHA・受入れ identity・levels・`pins_binding`。
- `_require_registration_pins(ctx, root)`：6 pin の存在・形式・定数との等値（wrong／missing／null 拒否）に加え，**committed ledger／receipt の identity＝pins** を全 loader の入口で要求。
- `load_registered_d4c2_ledger`／`load_registered_d4c2_outer_receipt`／`load_registered_infeasibility_campaign`：pins guard → 原本 byte → 再導出等値。consumer 向け view は `kind=calibration_infeasibility_certificate`・levels・`usable_true_impossible`・screens・scope 文のみを返し，sealed calibration／partial へ**昇格しない**（条件 6；`load_sealed_record`／`load_partial_record`／`load_subpartial_record` は kind／schema で拒否）。

### 1.5 専用経路（条件 5）
登録 loader は現 source（0.113.0）の条件を screen／certificate に課さず，**認証済み歴史 source（0.112.0 epoch）と受入れ identity** を根拠に検証する。歴史 inventory の写しは `registered_assets/d4c2/source/` に保管し，lock の `registered_assets_sha256` と typed 等値で照合する。

## 2. pins（6 file：`d/d1,d2,d3_pins.json`・`b3/b3_0,1,2_pins.json`）
`engine_version` 0.113.0 と上記 6 key。値：acceptance `3b6c839d…`・decision `0477d7b2…`・certificate `4a249ee6…`・bridge acceptance `325f1ad3…`・ledger `aaeb91e1…`・receipt `61426141…`。

## 3. 科学的 scope（条件 7）
ledger `statement` と view `scope` は監査 §5.3 の文言に固定：固定 bank・登録 W₂ context（family ごとに unknown ≥1・True なし）・登録 2000 組・grid・0.112.0 semantics・全行包絡 ≤ 2.0 に**条件付けた**較正可用性の成功不能であり，Theme T の物理的 no-go・usable＝False・実測 c／u ではない；6000 family-row は同一 2000 global 行の補強であり 6000 試行ではない；W₂ unknown のみでは十分条件ではない。原本 report §5(iii) は byte 保持し，`Step1_PhaseD_D4C2_screen_certificate_report_erratum_v0.1.md` で訂正。

## 4. 拒否試験（条件 8；`tests/test_d4c2_registration.py`）
1. pins guard：6 pin × wrong／missing／null × 3 loader。
2. byte 層 26 case：screen record／run gate False・欠落／final exit code／lock commit／notebook／archive／member 欠落・余分／family 混在 run dir；certificate record／run flag／command 改変（self-test option）／rc≠0／stderr 非空；受入れ・decision 改変；results packet／report／bundle；歴史 inventory 改変（新版再ラベル）；bridge zip／受入れ／report 改変；ledger／receipt の再刻印（pins も合わせて書換え）。
3. 意味層（byte 層を monkeypatch で迂回し lock→run→final を再連鎖）：screen 19 case（信頼 inventory からの gate 欠落・gate False・旧版 source 混在・probe／selftest／instrument・family 混在・N4 欠落・W₂ checksum 保持の要約改変・W₂ True 前提・行 threshold／paired 列変更・行 subset・行重複（6000 化）・未登録環境・D-2 入力別 run・final fallback・precheck dirty・lock の新版再ラベル）；certificate 10 case（分母 6000・screen の 4 重複・閾値入替え・levels 改変・technical 行主張・attempt 混在・engine 再ラベル・evaluated source 混入・consumer の gate 迂回 flag・proven 二重）。
4. 昇格拒否：登録 certificate を `load_sealed_record`／`load_partial_record`／`load_subpartial_record`／`load_combined_sealed_record`／shape checker が拒否。
5. 決定論：ledger＝再導出＝committed＝pins；receipt 同；定数＝受入れ文書＝原本＝0.112.0 driver の REQUIRED（AST）。
