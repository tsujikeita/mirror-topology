# Phase D-3c tranche ② v2 報告（正式 profile 実行記録・plan identity の登録，外側 receipt，consumer 検証 API；R-D3C2-A の改訂；実装受入れの依頼）
2026-10-04。Claude 作成。ChatGPT 宛（tranche ② v2 の受入れ監査の依頼）。engine `step1_engine 0.101.0`（v1＝0.100.0，commit `81f9e630…`：原本保存と ledger／receipt の再導出は PASS，API 受入れは HOLD（R-D3C2-A-ACCEPTANCE-PIN）。0.100.0 からの変更は **`d3c_ledger.py` の pins guard と gate record 検査の厳密化**，試験 4 case 追加，本報告書，addendum，版表示（ledger／receipt の payload は不変）。0.99.0 からの変更は **新 module `step1_engine/d3c_ledger.py`**（module 54），**新登録資産 `registered_assets/d3c/`**（原本 30 file＋ledger／receipt JSON＋receipt md），**pins 3 項目**（`d3c_ledger_sha256`・`d3c_outer_receipt_sha256`・`d3c_acceptance_sha256`），試験 1 file（26 case），本報告書，addendum，版表示。**数値 kernel・既存登録資産・D-3c profile script／notebook は不変；既存 module の変更は `__init__.py` の版表示と `checkpoint.py` の MODULES への `d3c_ledger.py` 登録（source inventory の例外）のみ**）。根拠：`D3c_profile_runs_7a2b1774_acceptance.json`（PASS_WITH_EXPLICIT_SCOPE__TRANCHE2_REGISTRATION_IMPLEMENTATION_GO；§6 の実装条件 1〜4）。

## 0. 範囲と主張
- **主張するもの**：3 family の正式 profile 実行の**原本**（inner archive の member と byte 一致する 7 file／family・実行済 notebook・受入れ文書）を登録し，決定論的 ledger と外側 receipt で pins に束縛し，D-4 較正の consumer が「登録 ordered UID から再構築した plan が受入れ identity を再現すること」「両 system の fingerprint・plan identity・plan object（任意で gate inventory）が受入れ値と一致すること」を検証される API を提供すること。正常系と拒否系の試験。
- **主張しないもの**：D-4 較正の実行・閾値／label／D-2W／noise／ENGINE_VALID・E1 の 12 位置 profile・実 bank の再読込み。

### 0.1 v1 監査（`D3c_tranche2_0.100.0_audit_decision.json`）への対応
| 所見 | 要求 | 対応 | 試験 |
|---|---|---|---|
| **R-D3C2-A-ACCEPTANCE-PIN**（blocking） | `d3c_acceptance_sha256` を registered load／intake の共通経路で検査（不一致・欠落・null を拒否）；受入れ file bytes の検査と再導出は維持；純粋な build は pin から独立でよい | `load_registered_d3c_ledger` の入口で `ctx.pins["d3c_acceptance_sha256"] == PROFILE_ACCEPTANCE["decision_sha256"]` を要求（receipt load と intake はこの loader を経由）。`build_d3c_profile_ledger` は従来どおり受入れ file bytes を module 定数に照合（pin から独立；docstring に明記） | `pins_acceptance_wrong`／`_missing`／`_null`：ledger load・receipt load・intake の 3 経路すべて拒否，build は登録内容と一致；`pins_receipt`（receipt pin 不一致：ledger load は成功，receipt load／intake は拒否）；既存 `pins`（ledger pin）維持 |
| N-D3C2-GATE-SCOPE（非 blocking） | `gate_checked=True` の意味を限定して記述；任意で check の重複禁止・件数・diagnostics 整合 | docstring と本報告書：record 検査のみ（official gate の再実行でも全 diagnostics の意味検証でもない；D-4 は実入力・実環境で live gate を実行する）。検査を強化：code の重複禁止・件数一致・`profile_failures==[]`・`version_mismatch=={}`・`blas_threads_ok`・`rules_binding.ok` | gate 編集 10 種（欠落・失敗・smoke・twelve 欠落・**重複**・**version_mismatch**・**blas**・**rules**・**profile_failures**・**injected 環境**）を拒否 |
| N-D3C2-CHANGE-DESCRIPTION（非 blocking） | 「既存 module 不変」の記述に checkpoint の登録例外を明記 | 冒頭の記述を訂正 | — |

## 1. 実装条件への対応（acceptance §6／`registration_conditions`）
| 条件 | 実装 | 試験 |
|---|---|---|
| 1. 原本をそのまま登録；版が変わっても実行 source／path／環境／時刻を書き換えない | `registered_assets/d3c/runs/<F>_<attempt>/`（profile_lock・final record・launcher stdout／stderr・`run_<attempt>/`{profile record・plan identity・script log}＝先生の Colab 出力の原本 bytes），`archives/`（inner zip 3；SHA `4cd9a8d0…`／`4783fc1f…`／`49b6591d…`），`notebooks/`（実行済 3），`acceptance/`（受入れ JSON `de8fa49f…`・md `426c3361…`・実行前 GO JSON `ef2e7db0…`）。実行 source は module 定数 `EXECUTION_LOCK`（commit `7a2b1774…`・engine 0.99.0・inventory `c0b0333b…`・script `9f243b08…`・notebook `4ad3ba0a…`・当時の pins／D-3b ledger file／receipt file SHA）であり，現在の tree の file とは比較しない（pins は本版で変わる） | ledger 試験：inner archive の member 集合＝登録 7 file・各 member の SHA＝登録 file＝ledger；archive 1 byte 変更・notebook 欠落・受入れ JSON 編集・attempt 混在（別 family の attempt id）・退避 record の混入・family 欠落は再導出が拒否 |
| 2. 受入れと receipt の結合；自己申告 PASS／未信頼 hash だけでは受け入れない | `build_d3c_profile_ledger(root, ctx)`：原本を再読込みし，lock＝`EXECUTION_LOCK`＋登録 D-2／D-3b run，final record＝当該 attempt（profile_pass／rc 0／D3C_PASS／gate／fallback なし／bindings／plan file ok／退避なし）＋precheck／prelaunch の live source＝lock＋staged 引数（self-test flag なし），profile record＝REQUIRED 18 名前集合全 True・source＝lock・環境＝pins＋`EXPECTED_VERS`・context identity＝`TwelveContext`・D-3b ledger／receipt＝pins・入力 run＝ledger・**72 供給の manifest＝spec v2／D-3b ledger／family reference**・UID 定数＝RULES／official_gate・fingerprint 前後一致・plan object 4 群共有・family identity（36・full scope）・official gate（mode official・live_collected・330 check 名前集合・14 twelve check 集合・全 passed・rules binding verified）；plan document＝header 定数・attempt／source 束縛・identity payload SHA・ordered UID 40 000 の構造（batch／purpose／group／rotation 順）・UID SHA＝record・publication receipt；受入れ JSON の file bytes＝定数 SHA かつその family 項目（attempt・archive SHA・7 file SHA・notebook SHA・plan identity・UID SHA・fingerprint・record／lock SHA・独立再構築 True）＝再導出。`verify_d3c_profile_ledger` は再導出との完全一致（re-stamp も拒否），`load_registered_d3c_ledger` は pins `d3c_ledger_sha256` と **`d3c_acceptance_sha256`**（v2）。`build_d3c_outer_receipt`：ledger payload＋file SHA・受入れ定数＋file bytes・family identity・pins binding（D-3b・config map・covariance receipt・spec v2）→ `receipt_sha256`＝pins `d3c_outer_receipt_sha256`；pins `d3c_acceptance_sha256`＝受入れ JSON SHA | 決定論（2 回の build 一致＝committed file＝pins），ledger／receipt の 7＋4 種の編集（re-stamp 含む）拒否，登録原本の 24 種の編集拒否（§3），pins 変更で load 拒否（build は登録内容と一致） |
| 3. consumer の入力 identity 検査 | `intake_registered_d3c_profiles(root, ctx)` → sealed `D3cProfiles`（ledger＋receipt＋pins 束縛・D-3b outer receipt＝登録）；`plan_identity(F)`／`ordered_uids(F)`（登録 plan document の bytes＝ledger を要求）／`input_fingerprints(F)`／`gate_record(F)`（原本 record から抽出した gate 全文；ledger の `gate` は原本と同一）／`constants(F)`；`rebuild_registered_plans(profiles, F, table)`：登録 ordered UID・登録定数（B／B_KDE／K_fit／master_seed；CRN 表 SHA 一致を要求）で `fix_family_plans` → identity 完全一致＋`verify_plan_identity`；`verify_consumer_inputs(profiles, F, fingerprints, plans, fit_plans, plan_identity, table, gate=None)`：両 fingerprint＝受入れ値・plan identity 文書＝受入れ値・plan object が受入れ identity を再現・（gate 指定時）official／passed／required_failures 空／live_collected／check 名前集合＝受入れ record；`verify_consumer_family_inputs(profiles, F, fm, fn, ...)`：family・両 system の plan object 共有・全配置の cluster UID＝登録 ordered UID → `input_fingerprint` で fingerprint を計算して上記へ | E2 の正式規模再構築（20〜25 s・peak ≈4.3 GB）＝受入れ identity＝受入れ JSON；正常 binding record；拒否：fingerprint 入替え／改変・他 family の identity・re-seal した identity（B 1999）・seed 入替え plans・gate の check 欠落／失敗／smoke／twelve 欠落・E1・未検証 view（dict）・CRN 表不一致；FamilyInput 形：他 family・plan 非共有・UID 逆順・FamilyInput でない double（fingerprint で拒否）・片 system 欠落 |
| 4. 正常・拒否試験の提出 | `tests/test_d3c_tranche2.py`（26 case） | §3 |

## 2. 登録資産と識別子
| 対象 | identity |
|---|---|
| ledger `registered_assets/d3c/d3c_profile_ledger.json` | payload `8e5cd2dff074fdda…`（pins `d3c_ledger_sha256`） |
| receipt `registered_assets/d3c/d3c_outer_receipt.json`／`.md` | payload `aca443d02d95af89…`（pins `d3c_outer_receipt_sha256`） |
| 受入れ JSON | `de8fa49f40a897ee…`（pins `d3c_acceptance_sha256`） |
| plan identity | E2 `86a7db7b4aa31d17…`・E7 `3c28d3eb66042436…`・E8 `d239ad9d39da8a0d…`（受入れ JSON と一致） |
| 合計 | 供給 216・profile checks 990・twelve checks 42・script 2715 s・launcher 4348 s・peak RSS 最大 19 466 MB |

## 3. 試験（`tests/test_d3c_tranche2.py`；30 case）
- `test_ledger_and_receipt_deterministic_registered_and_bound`：§1 の 2 と，REQUIRED_GATES 定数＝`d/d3c_profile.py` の `REQUIRED`，`d3c_ledger.py` が `checkpoint.MODULES` に含まれる，family ごとの identity＝受入れ JSON，inner archive の member＝登録 file。
- `test_registered_original_edits_refused[28]`（複製 root）：pins の acceptance 不一致／欠落／null・receipt pin（§0.1），record の D3C_PASS／gate check 欠落／gate mode／gate 後 fingerprint／family／selftest／供給 manifest／context identity，plan document の UID 入替え／B／attempt，lock の commit／入力 root，final の profile_pass／attempt／prelaunch HEAD／self-test 引数，stderr，退避 record の混入，family 欠落，archive，notebook 欠落，受入れ JSON 編集，ledger pin。各 case で build／ledger load／receipt load／intake の拒否（pins case は build 一致＋load／intake 拒否）と，元の root の ledger が不変であることを確認。
- `test_consumer_api_rebuild_and_refusals`：§1 の 3（gate record 編集 10 種を含む）。
- 全 suite：§4。

## 4. 全 suite
**1673 case（1643＋30）全 pass**，failure／error／skip 0（17 chunk・JUnit `regression_logs/d3c_t2v2_pytest/j1..17.xml`；case の多重集合＝collect と一致；chunk 17＝`tests/test_d3c_tranche2.py`）。

## 5. 次段
受入れ後：D-4（較正）の設計で，`D3cProfiles` を較正 driver の入力 gate に接続（較正前に `rebuild_registered_plans`＋`verify_consumer_family_inputs` を通過した family input のみ較正に進む；較正中も plan identity／fingerprint を target まで不変に保つ監視）。閾値／label／D-2W／noise はその後の段。
