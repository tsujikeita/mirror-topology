# Phase D4C-2b 登録 tranche 報告書 — screen 3 件・固定 campaign 成功不能 certificate・bridge 原本の登録，ledger／receipt・pins・registered loader（engine 0.113.0）
2026-10-08。Claude 作成。ChatGPT 宛（**登録 packet の実装受入れ**監査の依頼；監査 `D4C2_screen_certificate_0.112.0_acceptance.json`（`3b6c839d…`）の `registration_conditions` 1〜9 への対応表を §6 に置く）。前提：実行 GO `D4C2_screen_certificate_0.112.0_execution_decision.json`（`0477d7b2…`）・post-run 受入れ（上記）・bridge 受入れ `D4C2_bridge_0.110.0_acceptance.json`（`325f1ad3…`）。本 tranche は起草・実装・試験・原本保管であり，Phase E／target 解放・規則変更・W₂／pseudo 再生成・正式 global 較正・usable＝False の測定は含まない（条件 9）。数値 kernel・既存の registered loader（D4C-0）・screen／certificate の checker（`infeasibility.py`）は不変。設計：`Step1_PhaseD_D4C2b_registration_design_v0.1.md`。

## 1. 登録原本（byte 同一；§0 表の全 46 file＋bridge 8 file；SHA は ledger と受入れ JSON の file map に一致）
| 区分 | 内容 |
|---|---|
| `registered_assets/d4c2/source/` | `B2_completion_inventory_0.112.0.json`（`aa2c11cc…`；実行 epoch の inventory の歴史的写し；commit `ba51e5951ebb…`） |
| `registered_assets/d4c2/screens/runs/<F>/` | E2 attempt `20261007T113430Z_d4d346bde9`，E7 `20261007T143438Z_a2d3767433`，E8 `20261007T145023Z_6a25812f53`：各 7 member（lock・final record・stdout／stderr・`run_<a>/{d4c1_screen_<F>_record.json, d4c1_screen_<F>_run.json, d4c1_screen_<F>_stdout.log}`） |
| `registered_assets/d4c2/screens/{archives,notebooks,bundle}/` | inner launcher archive `d4c1_screen_<F>_ba51e5951ebb.zip`（member＝登録 run file）；実行済 notebook `MirrorTopology_Step1_D4C2_screen_v0_1_<F>_executed_ba51e5951ebb.ipynb`；著者 bundle `d4c1_results.zip`（`270f5dfa…`） |
| `registered_assets/d4c2/certificate/` | `command.txt`・`stdout.txt`・`stderr.txt`（空）・`rc.txt`（`rc=0`）・`out_20261007T152500Z/{d4c1_certificate_record.json (0c910b32…; 内容 SHA 4a249ee6…), d4c1_certificate_run.json, d4c1_certificate_stdout.log}` |
| `registered_assets/d4c2/results/` | 提出 packet `D4C2_screen_certificate_0.112.0_results.zip`（`567092da…`）・`D4C2_screen_certificate_report.md`（`b9a96cec…`；§5(iii) は byte 保持し erratum で訂正）・`file_map.json`（`628bc316…`） |
| `registered_assets/d4c2/acceptance/` | 監査 md・受入れ JSON（`3b6c839d…`）・audit evidence zip・実行 decision（`0477d7b2…`）・execution settings |
| `registered_assets/d4c1/probes/20261006T115712Z_69ece7cef3/`（既存；維持） | bridge probe の zip・実行済 ipynb・比較 report JSON（`BRIDGE_CONTRACT_SATISFIED`）・bridge report md・監査 md・bridge 受入れ JSON・evidence zip・file_map |
| 登録文書 | `registered_assets/d4c2/d4c2_ledger.json`（payload SHA `aaeb91e1bbdda73e969d564c54eb0c0d7cf75c33bc6a3b8de39ad35e867e7fc1`）・`d4c2_outer_receipt.json`（`614261413751cdd8c2692ea5f2d4e0d87d10999253641ea625593a71e91bc2a5`） |

## 2. ledger／receipt／pins（`step1_engine/d4c2_registry.py`；`checkpoint.MODULES` に登録，62 module）
- **定数**：`SOURCE`（固定 epoch）・`SCREENS[F]`（attempt・execution lock・member SHA／bytes・archive・notebook・screen 要約：内容 SHA・`n_blocking` 2000・W₂ 要約・config id・registry／manifest／W₂ context SHA・pseudo identity・`ratio_bound_max`（E2 1.146／E7 1.104／E8 1.159）・`min_P`）・`CERTIFICATE`（内容 SHA・levels：support 81／strong 12・proven 2000・technical 0・possibly_technical 2000・usable＝True 不能＝True・sources＝3 screen の typed identity・consumer 環境 metadata・command SHA）・`RESULTS`・`ACCEPTANCE`・`BRIDGE`・`SCREEN_REQUIRED`（20；0.112.0 driver の `REQUIRED_SCREEN`）・`CERT_REQUIRED`（12）。
- **`build_d4c2_ledger(root, ctx)`**：決定論的再導出（約 36 s；screen 1 件 ≈ 4 s＋certificate の再導出）。byte 層（member 全件 SHA／bytes・欠落／余分拒否・archive member＝登録 file・notebook／packet／report／受入れ文書）→ lock（歴史 epoch：commit／engine／inventory／script／pins・family・全範囲・campaign／commitment・`registered_assets_sha256`＝歴史 inventory・D-2 run root＝登録 D-2 ledger）→ final（この attempt・complete／exit 0／fallback なし・precheck／prelaunch の live source＝epoch・record SHA＝run bytes）→ run record（mode／formal／非 probe／非 selftest／非 instrument・`required_inventory`＝`SCREEN_REQUIRED` と全 gate True・source／attempt／lock 束縛・登録環境（現行または登録履歴 3.13.16）・published evidence＝screen record・D-2 入力＝登録 ledger・要約）→ screen record（provenance＝歴史 module SHA・`bind_screen_record` による登録 W₂ decision 全文からの再導出要約との typed 等値・paired 列・grid・config id・rows＝[0,2000) 正確に 1 回・W₂ 前提（True なし・unknown ≥1）・blocking 行＝全行で条件付き status・包絡 ≤ 2.0）→ certificate（command／rc／stderr・run record・純粋算術 `check_certificate` **と** 認証済み screen からの独立再導出 `aggregate_rows`／`_levels_from_rows`／`infeasibility_certificate` の等値・sources＝3 screen の順序付き identity・global 行 1 回計数）→ 受入れ文書＝定数＝原本 → bridge 原本＝bridge 受入れの `original_inputs`。
- **receipt**：ledger payload SHA・受入れ identity・levels・screens・`pins_binding`。
- **pins（6；6 file 共通）**：`d4c2_ledger_sha256`・`d4c2_outer_receipt_sha256`・`d4c2_acceptance_sha256`（`3b6c839d…`）・`d4c2_execution_decision_sha256`（`0477d7b2…`）・`d4c2_certificate_sha256`（`4a249ee6…`）・`d4c2_bridge_acceptance_sha256`（`325f1ad3…`）。`_require_registration_pins` は 6 pin の存在・定数との等値に加え **committed ledger／receipt の identity＝pins** を全 loader の入口で要求（wrong／missing／null をどの loader でも拒否）。
- **履歴の不変**：ledger は screen／certificate を 0.112.0／`ba51e595`，bridge を 0.110.0／`39082b64` の lock に束縛し，登録版 0.113.0 を record に書かない。lock／record／certificate の `engine` を 0.113.0 に書換えた tree は拒否（試験 `commit_relabelled_to_registration_version`・`engine_relabelled`・`source_inventory_byte`）。

## 3. registered loader（条件 4〜6）
- `load_registered_d4c2_ledger(root, ctx)`／`load_registered_d4c2_outer_receipt(root, ctx, ledger=None)`：pins guard → committed file の identity＝pin → 再導出との typed 等値。
- `load_registered_infeasibility_campaign(root, ctx)`：ledger＋receipt → certificate 原本 bytes（定数 SHA／bytes）→ `check_certificate` → `kind=calibration_infeasibility_certificate` の **view**（levels・`usable_true_impossible={support: True, strong: True}`・screens・source・scope 文）。sealed calibration／partial／sub-partial へ昇格しない：`load_sealed_record`／`load_partial_record`／`load_subpartial_record`／`load_combined_sealed_record`・shape checker は登録 certificate を kind／schema で拒否（試験 `test_registered_certificate_is_never_promoted`）。全 campaign load ≈ 31 s。
- 専用経路（条件 5）：現 source（0.113.0）の条件を課さず，認証済み歴史 source（`registered_assets/d4c2/source/` の inventory 写し＋lock の `registered_assets_sha256`）と受入れ identity を根拠とする。

## 4. 試験（`tests/test_d4c2_registration.py`：8 関数・78 case；copy した tree 上で原本を編集し，終了時に復元；chunk 31 ≈ 17 分）
- 決定論：ledger＝再導出＝committed＝pins；receipt 同；module 登録・版；定数＝受入れ JSON（accepted_screens／certificate／inner_files／raw_files）＝原本＝0.112.0 driver の `REQUIRED_SCREEN`／`REQUIRED_CERTIFICATE`（AST）；bridge 原本＝bridge 受入れ；view の内容と scope。
- **pins guard**：6 pin × {wrong, missing, null}＝18 case で 3 loader を拒否。
- **byte 層（26 case）**：screen record byte・run gate False／欠落・final exit code・lock commit・notebook／archive byte・member 欠落／余分・family 混在 run dir；certificate record byte・run flag・command 改変（self-test option）・rc≠0・stderr 非空；受入れ／decision 改変；packet／report／bundle byte；歴史 inventory の新版再ラベル；bridge zip／受入れ／report 改変；ledger／receipt の再刻印（pins も合わせて書換え）。
- **意味層（byte 層を monkeypatch で迂回し lock→run→final を再連鎖；30 case）**：screen 20——信頼 inventory からの gate 欠落・gate False（一貫して）・旧版 source 混在・probe／selftest／instrument・family 混在・N4 欠落・W₂ checksum 保持の要約改変・W₂ True 前提・行 threshold／paired 列変更・行 subset・行重複（6000 化）・未登録環境・環境 gate 不成立・D-2 入力別 run・final fallback・precheck dirty・lock の新版再ラベル；certificate 10——分母 6000・screen の 4 重複・閾値入替え・levels 改変・technical 行主張・attempt 混在・engine 再ラベル・evaluated source 混入・consumer の gate 迂回 flag・proven 二重。各 case の拒否箇所は意図した検査（run record の信頼 REQUIRED・`bind_screen_record`・N0／N4 被覆・W₂ 要約・登録環境・再導出等値 など）であることを exception 文で確認した（env `D4C2_REG_NOTE` で記録可能；既定では無記録）。
- 昇格拒否：4 reader＋2 shape checker。

## 5. 科学的 scope（条件 7；ledger `statement`・view `scope`・erratum v0.1）
固定 bank・登録 W₂ context（family ごとに unknown ≥1・True なし）・登録 2000 組・grid・0.112.0 判定 semantics・実証済み全行包絡 ≤ 2.0 に**条件付けた**較正可用性（usable＝True 到達）の成功不能である。Theme T の物理的 no-go ではなく，usable＝False でも実測 c／u でもない。6000 family-row は同一 2000 global 行の補強証拠であり 6000 試行ではない。W₂ unknown のみでは十分条件ではない。原本 report §5(iii) の括弧書きは `Step1_PhaseD_D4C2_screen_certificate_report_erratum_v0.1.md` で訂正（原本 byte は保持）。

## 6. 監査の登録条件への対応
| 条件 | 対応 |
|---|---|
| 1 原本 byte 登録・bridge 維持 | §1；ledger の byte 層；bridge 原本と別受入れ（`d4c1/probes/20261006T…`）を維持し ledger `bridge` に束縛 |
| 2 0.112.0 epoch への固定・再ラベル禁止 | `SOURCE`／lock／final／run／record の epoch 束縛；再ラベル拒否試験 3 件 |
| 3 決定論的 ledger／receipt・受入れ文書を含む pins | §2；pins 6（受入れ・decision・certificate・bridge 受入れ・ledger・receipt）；wrong／missing／null 18 case |
| 4 算術 checker と証拠認証の分離 | `check_certificate`（純粋算術）＋`_check_certificate`（bytes・lock／final／run・信頼 REQUIRED・source・publication・W₂ decision 全文・paired 列・行被覆・独立再導出） |
| 5 保存 evidence からの再導出・専用経路 | §3 |
| 6 sealed／partial へ昇格しない；unknown_or_technical・technical 0・1 回計数 | view のみ；昇格拒否試験；再導出で `technical_rows=0`・`proven 2000`・global 行 1 回 |
| 7 scope 限定・erratum | §5 |
| 8 拒否試験 | §4（原本改変 26・gate 欠落・旧版混在・family／attempt 混在・N4 欠落・W₂ checksum 保持改変・行／threshold／paired 列変更・6000 二重計数・閾値入替え・sealed 昇格） |
| 9 登録 packet の実装受入れは別途 | 本報告が依頼対象；`GO.registration_loader_implementation_acceptance` は false のまま |

## 7. 変更一覧（0.112.0 → 0.113.0）
- 新規：`step1_engine/d4c2_registry.py`，`tests/test_d4c2_registration.py`，`registered_assets/d4c2/`（46 file），本報告・設計 v0.1・erratum v0.1。
- 変更：`step1_engine/__init__.py`（0.113.0），`checkpoint.MODULES`（＋`d4c2_registry.py`），pins 6 file（engine_version＋6 key），`tests/test_d4c2a.py`／`tests/test_d4c1.py`（版 assert），`B2_completion_inventory.json`，`Step1_PhaseB_engine_spec_v0.3_addendum.md`，regression logs。
- 不変：数値 kernel・`infeasibility.py`・`d4c0_registry.py`・script `d/d4c1_calibration.py`・notebook・`d/d4c2_bridge_compare.py`。

## 8. 限定
登録 loader は認証のみを行い，較正の完了・target 評価・labels・noise の解放を与えない。bridge 原本の受入れ scope（fixed E2 first-3 environment bridge）は不変。本 tranche の受入れは登録 packet（commit bytes）に結び付き，改訂 commit は受入れを継承しない。
