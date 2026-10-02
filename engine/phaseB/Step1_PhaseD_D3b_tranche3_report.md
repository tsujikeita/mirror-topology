# Phase D-3b tranche ③ 報告（配列検証付き受入れの外側 receipt 登録・formal 消費の受入れ束縛；D-3c 設計 v0.1 の同時提出）（v1.1：冒頭の「検証 script 不変」を監査の非 blocking 注記どおり訂正）
2026-10-03。Claude 作成。ChatGPT 宛。engine `step1_engine 0.96.0`（0.95.0 からの変更は `step1_engine/d3b_ledger.py`（外側 receipt の builder／verifier／loader と `D3bUnits` の受入れ view を追加；ledger 側の定義は不変），`step1_engine/d3_bank.py`（formal intake が配列受入れを要求），`d/d3b_verify_banks.py`（ledger-only view を明示：検証器は自身の結果に依存しない），登録資産 `registered_assets/d3b/verify*`（9 partition の検証記録 45 file＋実行済 notebook 9）と `d3b_outer_receipt.{json,md}`，`d/d3_pins.json` に `d3b_outer_receipt_sha256`，試験 1 file，設計文書 `Step1_PhaseD_D3c_design_v0.1.md`，版表示。**生成 ledger・生成 script・notebook・kernel・receipt・spec v2・D-1／D-2／D-3a 登録資産は不変；検証 script は factory 呼出しに `require_array_acceptance=False` を加えた 1 箇所のみ変更**）。

## 0. 範囲と主張
- 前提：read-only 検証 9 partition は `Step1_PhaseD_D3b_readonly_269c6d56fb75_acceptance.json`（SHA `424a5471…`）で **PASS_WITH_EXPLICIT_SCOPE（AUDITED_COLAB_FULL_ARRAY_INTEGRITY_RESULTS）**；`next_steps.allowed`＝外側 receipt への記録（9 report／final／lock／notebook／zip の SHA と ledger を束縛）と実 bank profile／plan 固定の準備。
- **主張するもの**：(i) 9 partition の検証記録を登録し，そこから決定論的に再導出される外側 receipt を pins に束縛した；(ii) 追加 81 配置の bank を **formal 入力として消費する経路**（`intake_twelve_bank(formal=True)`）は「ledger の unit」かつ「配列受入れ receipt が ledger に束縛されている」ときだけ開く；(iii) 次段（実 bank profile・gate・plan 固定）の設計 v0.1 を提示する。
- **主張しないもの**：実 bank での profile／gate の結果・plan の実固定・較正・label。

## 1. 登録資産（`registered_assets/d3b/`）
| 物 | 内容 |
|---|---|
| `verify/<partition>/`（9 × 5 file） | `report/d3b_verify_<F>_<S>.json`・`verify_lock.json`・`verify_final_record.json`・`verify_stdout.txt`・`verify_stderr.txt`（各結果 zip の全 file；監査が固定した SHA と一致） |
| `verify_notebooks/` × 9 | 実行済み検証 notebook |
| `d3b_outer_receipt.json`（payload **`7c42bc11…`**＝pins `d3b_outer_receipt_sha256`）／`.md` | §2 |

## 2. `d3b_ledger.py` の追加（`VERIFICATION_LOCK`／`ARRAY_ACCEPTANCE` 定数・`build_d3b_outer_receipt`／`verify_d3b_outer_receipt`／`load_registered_d3b_outer_receipt`）
`build_d3b_outer_receipt(root, ctx)`：登録 ledger（pins＋再導出）を読み，partition ごとに検証記録を再読して束縛：lock＝検証 lock 定数（commit `269c6d56…`・engine 0.95.0・inventory `008e125c…`・script `dc57de8b…`）・ledger payload・family／size／run root／run id・D2_REF_ROOT 指定；final＝`verify_pass`／rc 0／fallback なし／lock 同一；report＝accepted mode・complete・`accepted_full`・binding／coverage／all_ok・failures／unchecked 空・cid／構造 OK・verifier source bound（engine／inventory／script／**module digest `f0a4ee17…`**）・generator source＝生成 lock（commit・run id・producer digest・raw fingerprint）・relocation なし・stderr 0 byte；unit 27＝ledger（ok・配列検証・manifest SHA・行数・purpose・config）；**各 NPZ の実測 file SHA／bytes＝ledger の期待値**（manifest／ledger／inventory 一致 flag）；cid（n＝行数・単調・一意数＝cluster 数）；T1／T2 全有限；role×selection 集合；D-2 reference 3 unit＝spec v2 の ledger identity；cid correspondence 27 件（partition 内同一・reference 同一）；NPZ 総計。記録：report／lock／final／stdout／stderr／notebook の SHA・D-2 reference の manifest／shard identity・検証環境（CAMB null）・順序非依存の環境 identity（9 run で 1 値）。`array_acceptance`＝監査の decision／md／入力 zip の SHA と範囲・不承認事項。`verify_*` は payload SHA＋再導出完全一致，`load_registered_*` は pins 束縛。**生成 ledger は書き換えない**（`array_acceptance=PENDING` は生成時の記録として保持；receipt が後続の受入れを示す）。

`intake_registered_d3b_units(root, ctx, require_array_acceptance=True)`：既定で receipt を要求し，ledger に束縛されていることを確認して `array_accepted=True` の sealed view を返す；`False` は ledger-only view（検証器用；`array_accepted=False`）。`d3_bank.intake_twelve_bank(formal=True)` は `array_accepted` を要求（info に `d3b_receipt_sha256`）。

## 3. 試験
- `tests/test_d3b_tranche3.py`（3 件）：receipt の決定論・登録 file＝再導出・pins・総計・partition 内容・ledger 不変；receipt 編集 6 種（再 stamp 含む）の拒否；登録検証記録の編集 8 種（report の flag／NPZ SHA／cid／D-2・lock commit・final・stderr・notebook 欠落）の再導出拒否・pins 不一致の拒否；units の受入れ view（両モード）・sealed；formal intake が ledger-only view を拒否・非 unit を拒否。
- 既存試験は不変で全 pass（検証器 test mode は ledger-only view で動作）。全 suite：§5。

## 4. D-3c 設計 v0.1（`Step1_PhaseD_D3c_design_v0.1.md`）
実 bank の formal intake（D-2 旧 3＋D-3b 新 9／size）→ 12 位置 size input → 全 size 組立て → family 単位の 5 seed plan 固定（実 UID）→ `twelve_official_gate`（official；live 環境）→ 記録。High-RAM Colab・1 family 1 run・配列は保存しない。設計の受入れと tranche ①（script・notebook・合成試験）開始の GO を求める（§E の確認点 4 つ）。

## 5. 全 suite
**1587 case（1584＋3）全 pass**，failure／error／skip 0（14 chunk・JUnit `regression_logs/d3b_t3_pytest/j1..14.xml`；case の多重集合＝collect と一致）。

## 6. 提出物・次段
- 監査に求めるもの：(a) 外側 receipt の再導出束縛（9 partition の記録・ledger・検証 lock・監査 decision の SHA）と「生成 ledger 不変・receipt が受入れを示す」構造の受入れ，(b) formal 消費の受入れ束縛（`intake_twelve_bank(formal=True)` が receipt を要求）の受入れ，(c) **D-3c 設計 v0.1 の受入れと tranche ①（script・notebook・合成試験）開始の GO**。
- GO 後：D-3c tranche ①を起草 → 実行前監査 → Colab（High-RAM；family ごと 3 run）→ 実行後監査 → plan identity・gate record の登録（D-3c tranche ②）。
