# Phase D4C-0 登録 tranche 報告書 — pseudo 列と D-2W context の原本登録・ledger／receipt・pins・registered loader（engine 0.105.0）
2026-10-05。Claude 作成（件数と pins 層の記述を 0.106.0 で訂正：監査 `ChatGPT_audit_D4C0_registration_0.105.0.md` §8 の非 blocking 2 件；内容は不変）。ChatGPT 宛（登録 API の実装受入れ監査の依頼）。前提：`D4C0_pseudo_12980202_acceptance.json`（`08efa1d1…`）と `D4C0_D2W_f3aec793_acceptance.json`（`c9506e0b…`；registration_drafting_and_tests_GO）。engine `step1_engine 0.105.0`（0.104.0 からの変更：**新 module `d4c0_registry.py`（MODULES 57）**，`w2_cases.py`／`d4_pseudo.py` の **loader 本体の接続と `D2W_REGISTRATION`／`PSEUDO_REGISTRATION` の充填**（stub の無条件 raise を除去；他は不変），**新登録資産 `registered_assets/d4c0/`**（原本 39 file＋派生 3 file（ledger／receipt JSON・receipt md）＝42 file；監査 N-D4C0REG-ORIGINAL-FILE-COUNT で訂正：初版の「原本 40」は誤記），**pins 7 項目**，試験 1 file（8 関数・53 case），本報告書，addendum，版表示。数値 kernel・既存登録資産・script／notebook は不変）。

## 1. 登録原本（byte 同一；監査の受入れ JSON の file map と一致することを ledger が要求）
| 区分 | 内容 |
|---|---|
| `registered_assets/d4c0/pseudo/` | `archives/d4_pseudo_12980202ee11.zip`（`57c0df45…`）；`runs/20261004T102334Z_6e681d78a0/`（7 member：lock・final record・stdout／stderr・`run_<a>/{d4_pseudo_record.json, d4_pseudo_columns.npz (c62a965b…), d4_pseudo_stdout.log}`）；`notebooks/…_executed_12980202ee11.ipynb`（`fb7a0d66…`）；`acceptance/`（受入れ JSON `08efa1d1…`＋補足 2 file） |
| `registered_assets/d4c0/d2w/` | `archives/d2w_cases_f3aec7935845.zip`（`13e222e5…`）；`runs/20261004T144349Z_cb8bc8e5f7/`（16 member：lock・final record・stdout／stderr・`run_<a>/{d2w_run_record.json, d2w_context_record.json, d2w_stdout.log, cases/ 9 file}`）；`notebooks/…_executed_f3aec7935845.ipynb`（`3d8a7ff7…`；bytes は著者提出のまま，file 名のみ実行 commit に合わせた）；`acceptance/`（受入れ JSON `c9506e0b…`＋監査 md） |
| 失敗 attempt（別建て） | `archives/d2w_cases_12980202ee11_FAILED.zip`（`09f9ab0e…`）と `failed_attempts/20261004T102439Z_9bac8f8730/`（6 member）；ledger は「失敗（stage inputs・success False）」であることと受入れ JSON の `previous_failure` との一致を要求し，success source として使えない（final／lock を成功 run に差し替える試験で拒否） |

## 2. ledger／receipt／pins（`step1_engine/d4c0_registry.py`）
- **定数**：`PSEUDO`／`D2W`（attempt・execution lock（各 run 固有の commit／engine／inventory／script／pins／lock SHA）・archive・全 member の SHA／bytes・notebook・acceptance・列 identity／NPZ・9 case の file／manifest／result SHA と decision（trigger／state／B_final／observed_hash）・context SHA・failed attempt）。すべて受入れ原本から生成（手打ちなし）。
- **`build_d4c0_ledger(root, ctx)`**：決定論的再導出——member 集合＝定数（余分・欠落・symlink 拒否）・archive member＝登録 file・lock／final／run record の束縛（schema・attempt・lock SHA・精確な REQUIRED 集合と全 `is True`・`required_all_true`・self-test なし・正式 profile・precheck／prelaunch の live source＝lock・環境＝登録環境）・D-2W の入力束縛（registry SHA＝ledger・27 unit manifest＝ledger・K 2000／m 100／rows 200000・canonical 9 case・run 要約＝case record＝context record＝定数）・pseudo の NPZ を **定数 identity** で `verify_pseudo_columns`（record の自己申告でない）・受入れ JSON の内容（decision・file map・識別子）＝定数。`verify_d4c0_ledger` は再導出との完全一致，`load_registered_d4c0_ledger` は pins guard（§2 末尾）＋payload SHA＝pin。
- **receipt**：ledger（payload＋file SHA）・両 run の identity・9 case の decision・pins_binding を束ね，`load_registered_d4c0_outer_receipt` は pin 一致＋再導出一致。
- **pins（7）**：`d4c0_ledger_sha256`（`8c0d39f9…`）・`d4c0_outer_receipt_sha256`（`d6926b94…`）・`d2w_acceptance_sha256`（`c9506e0b…`）・`pseudo_acceptance_sha256`（`08efa1d1…`）・`d2w_context_sha256`（`50ec5a54…`）・`pseudo_paired_sha256`（`c9f75cdb…`）・`pseudo_npz_sha256`（`c62a965b…`）。`_require_registration_pins` が全 pin の存在と定数との一致を要求（ledger pin は ledger load で，receipt pin は receipt load で値を照合；すべての消費 load は両者を通る）。**層の区別（監査 SCOPE-PIN-LAYERS）**：共通 guard が値まで照合するのは acceptance 2 件・context・paired・NPZ の 5 項目で，ledger／receipt の 2 項目は存在・形式のみ；値の照合は対応する registered load（ledger load／receipt load）で行う。よって 64 文字だが誤った receipt pin だけを与えた場合，ledger-only load は成功し得る（receipt load と両 consumer load は拒否）。「7 項目すべてを ledger-only load が値検査する」とは言わない。
- **履歴の不変**：ledger／receipt は登録版（0.105.0）を記録しない（試験で確認）；pseudo は 0.103.0／`12980202`，D-2W は 0.104.0／`f3aec793` の lock に束縛。

## 3. registered loader（監査条件 6〜8）
- `load_registered_w2_context(root, ctx)`：ledger＋receipt（pins guard）→ 9 原本 case record の bytes 認証（定数 SHA／bytes）→ shared-null asset＝実行 asset → `restore_w2_context(records, asset, expected_context_sha256=pins['d2w_context_sha256'], require_formal=True)`（stored evidence の replay；exact OT 再実行なし）→ canonical 9 key・context SHA＝定数・各 decision（trigger／state／B_final／observed_hash／distance_kind）＝定数。4 case の unknown はそのまま（view の scope に「W₂ branch only；D-4 で event-ratio と 12 位置完了と組み合わせる」を明記）。sandbox 12.9 s。
- `load_registered_pseudo_columns(root, ctx)`：ledger＋receipt → 原本 NPZ bytes＝pin → `verify_pseudo_columns` を定数 identity・登録 pseudo 表で → paired SHA＝pin → 列（T1／T2 f64・AX／PL i32・cid・uids・n 2000）と view。再生成・許容幅同等は不可（bytes 認証）。
- `w2_cases.load_registered_w2_context`／`d4_pseudo.load_registered_pseudo_columns` は上記へ委譲；`D2W_REGISTRATION`／`PSEUDO_REGISTRATION` は registry 定数の写し（None なら拒否）。

## 4. 試験（`tests/test_d4c0_registration.py`：8 関数・53 case；copy した tree 上で原本を編集し，終了時に復元）
- 決定論・committed file・pins 一致；module 登録；定数＝受入れ JSON＝原本＝archive member（3 archive）；REGISTRATION 定数の写し；ledger／receipt に登録版なし。
- loader 正常：W₂ context の復元（context SHA・9 decision＝定数・unknown 4 件保持・view）と wrapper 経由の一致；pseudo 列＝原本 NPZ の配列（再生成でない）・identity・paired SHA＝pin。
- **pins guard**：7 pin × {wrong, missing, null}＝21 case で ledger／receipt／両 loader（registry と wrapper）を拒否（build は pin 非依存）；誤った `d2w_context_sha256` は復元前に拒否。
- **原本編集の拒否（26 case）**：case record の byte 変更・unknown→False の rehash 昇格・case 欠落／余分／小 bank 混在・context record 編集・run record の gate False／self-test flag・final record の pass flag・lock commit・archive byte・notebook byte・受入れ JSON 編集・失敗 attempt の success 化・失敗 attempt の差替え・NPZ の nextafter／逆順／dtype・pseudo record identity・pseudo lock commit・pseudo 受入れ編集・pseudo notebook／archive byte・ledger／receipt の re-stamp・ledger payload 編集。
- 復元契約：self-test 形 record（formal False）・別 asset・重複の拒否；単一 case の context は登録 9 case context と一致しない。

## 5. 限定
登録と loader の受入れを求める。正式 global 較正（D4C-1：partial／combiner・target commitment・usable）・Phase E・noise・ENGINE_VALID は含まない。exact OT・bank 配列の再読込みは行っていない（受入れ済み実行証拠の bytes 認証と replay）。
