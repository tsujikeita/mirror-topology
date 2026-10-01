# Phase D-3b tranche ② 報告（9 run の生成 ledger 登録・read-only 検証器の起草；正式検証の実行前監査依頼）
2026-10-02。Claude 作成。ChatGPT 宛。engine `step1_engine 0.94.0`（数値 kernel は 0.54.0 基盤の継承；0.93.0 からの変更は **新 module `step1_engine/d3b_ledger.py`**（module 53），**`d3_bank.intake_twelve_bank` の formal 経路に ledger 束縛を追加**（引数 `registered_units`；他の定義は不変），**新 script `d/d3b_verify_banks.py`**，**新 notebook `d/MirrorTopology_Step1_D3b_verify_v0.1.ipynb`**，**登録資産 `registered_assets/d3b/`**（9 run の metadata 720 file＋ledger），`d/d3_pins.json` に `d3b_ledger_sha256` を追加，試験 1 file，版表示。生成 script・生成 notebook・receipt・spec v2・config map・CRN 表・D-2 spec v1・D-1／D-2／D-3a 登録資産・既存 kernel は**不変**）。

## 0. 範囲と主張
- 前提：9 run（commit `7b09c646…`，engine 0.93.0）は `Step1_PhaseD_D3b_all9_7b09c646b369_metadata_acceptance.json`（SHA `461f7525…`）で **実行記録・metadata の範囲で PASS_WITH_EXPLICIT_SCOPE**（NPZ 配列の読込み 0/405；`next_steps.allowed`＝ledger への外側記録と read-only 検証器の実装／監査）。
- **主張するもの**：(i) 9 run の受入れ済み記録を repository に登録し，そこから決定論的に再導出される生成 ledger（unit 243・期待 NPZ identity 405）を pins に束縛した；(ii) 保存 bank を Drive 上で読取り専用に検証する検証器（D-2 verifier v0.2 の構造；ledger への accepted-run binding・検証 source 束縛・出力隔離）と partition 単位の Colab notebook を起草し，合成 bank での試験と登録記録への binding 試験を行った；(iii) formal な bank intake は ledger の unit でなければ拒否する。
- **主張しないもの**：405 NPZ の数値受入れ（本 tranche の検証器を Colab で実行し監査を受けてから，外側 receipt に記録），実 bank での 12 位置 profile／official gate・plan 固定・較正・label・D-2W・noise。

## 1. 登録資産 `registered_assets/d3b/`（720 file＋ledger）
| 物 | 内容 |
|---|---|
| `runs/<FAMILY>_<SIZE>_<run id>/out/` × 9 | 各 run の監査 zip の全 metadata（79 file：`launcher_lock.json`・`d3b_final_record.json`・`launcher_script_stdout/stderr.txt`・`d3b/d3_run_manifest.json`・`d3b/d3_bank_registry.json`・`d3b/d3_bankgen_stdout.log`・27 `COMPLETE.json`・45 sidecar）。**NPZ は登録しない**（Drive 保持；ledger は NPZ の存在を拒否） |
| `notebooks/` × 9 | 実行済み notebook（SHA を ledger に記録） |
| `d3b_generation_ledger.json`（file `bdaa8aeb…`，payload **`a7d2c8c4…`**＝pins `d3b_ledger_sha256`） | §2 |

run id：E2 `010656Z`／`054800Z`／`080141Z`，E7 `101421Z`／`163102Z`／`191817Z`，E8 `213708Z`／`20261001T004059Z`／`20261001T132201Z`（script 秒 7825〜9759，計 74586 s）。

## 2. `step1_engine/d3b_ledger.py`（`3df27661…`；190 行）
| 定義 | 内容 |
|---|---|
| `GENERATION_LOCK`／`METADATA_ACCEPTANCE` | 信頼定数：生成 commit `7b09c646…`・inventory `47678477…`・engine 0.93.0・script `65593973…`・notebook `8455ba94…`・pins `284ca06a…`・producer digest `39510da2…`・実行前 GO decision（`f1df0788…`）；metadata 受入れ decision（`461f7525…`）・監査 md（`6ca3c590…`）・入力 zip（`fbe94c55…`） |
| `build_d3b_ledger(root, ctx)` | 検証済み `TwelveContext`（root 一致を要求）と登録 spec v2 のもとで 9 partition を再導出：launcher lock＝生成 lock（commit／inventory／engine／pins／spec v2／receipt）・scope（family／size 1 つ・reuse／D2 ref なし・run id）；run manifest＝complete／`D3B_PASS`／failures 空／**REQUIRED 13 全 True**／`G_d2_reference_dirs` None；final record＝`D3B_PASS`／rc 0／fallback なし；producer＝定数（digest・script・inventory・engine・profile production_official／scale 1／self-test なし）；publication receipt＝registry bytes；registry header／identity（表・spec v1・spec v2・receipt・map・registry SHA＝context）；scope＝spec v2 の generate 9／fixed 3・required 27・ledger 順・call 27；covariance intake 9＝spec v2（file／array SHA・PC1_PASS・origin）；各 unit：directory record（新規・formal・path）・COMPLETE の payload SHA＝registry・manifest identity（schema／id／family／origin／position／formal／scale／roles／selections）・束縛（spec v2／receipt／表／spec v1／map／root SHA＝intake）・purpose／batch／行数（N₀／3N₀／N_fit）・各 sidecar（bytes SHA＝manifest・file SHA・producer digest・covariance＝spec v2）・NPZ byte 数＝final inventory（SHA null）・NPZ 不在；final inventory の metadata SHA 6 種＝実 bytes；総計（配置 81・unit 243・NPZ 405・27,217,472,580 B・producer digest 1 種）。各 partition に record SHA 7 種＋notebook SHA・gate・A10 rel・**raw environment fingerprint（不変）と順序非依存の環境 identity**（§4）・環境版・秒・unit 27（manifest SHA・行／cluster・group・root SHA・covariance identity・NPZ {file：SHA・bytes・rows・array SHA 13}） |
| `verify_d3b_ledger(doc, root, ctx)`／`load_registered_d3b_ledger(root, ctx)` | payload SHA＋**再導出との完全一致**（編集は再 stamp しても拒否）；登録 file は pins の `d3b_ledger_sha256` に束縛 |
| `intake_registered_d3b_units(root, ctx)` → `D3bUnits` | sealed（factory 以外の構築拒否・不変・view は deepcopy）：`unit(name)`（243）・`partition_of(cid)`・`require_unit_manifest(name, manifest_sha, n_rows, purpose)`（受入れ済み unit でなければ拒否） |
| 文書 field | `array_acceptance.status="PENDING"`（配列受入れは read-only 検証後に外側 receipt へ；ledger には書かない）・`environment_note`・`parent_runtime_note`（監査 §2 の限定を転記）・`external_acceptance` |

`d3_bank.intake_twelve_bank(..., formal=True, registered_units=None)`：formal は `D3bUnits` を要求し，消費する 3 directory（b0／b1／fit）の manifest SHA／行数／purpose が ledger の unit と一致しなければ拒否（context に対して再検証が通るだけの小規模 bank は登録 bank ではない；試験）。返値 info に `d3b_ledger_sha256`。formal=False（self-test）は不変。

## 3. `d/d3b_verify_banks.py`（`1cf62a44…`；180 行）と notebook（`29d32a04…`）
D-2 `d2_verify_banks.py` v0.2 の構造（RV-1／1.5／2）を partition 単位・D-3b 束縛に移したもの。f32／W₂ 経路はない（D-3b は f64 のみ）。
| 段階 | 内容 |
|---|---|
| 出力隔離 | `--out` は realpath・run root／参照 bank と交差しない fresh directory；全出力 O_EXCL；入力は書かない。JSON は捕捉 bytes から decode（重複 key・非有限拒否） |
| 検証 source | module SHA map＝inventory＝版・script SHA＝inventory・**登録 ledger bytes＝inventory**；`verifier_source`（生成 source と別記録）・`verification_environment` |
| context／ledger | `twelve_context`・登録 spec v2・`intake_registered_d3b_units`（pins＋再導出）；registry の family／size から partition を決定，必要 unit 27＝spec v2 |
| accepted-run binding | final／registry／run manifest／lock の **実 bytes SHA＝ledger の record**；complete／`D3B_PASS`／formal；unit 集合＝ledger＝spec v2；registry の manifest SHA＝ledger。不一致は配列を読む前に停止（stage binding）。relocated run は論理 run root→RUN_ROOT を自動 map（名前は受入れ記録のまま） |
| 任意 `--d2-ref-root` | D-2 family reference 3 unit を `verify_reused_reference_dir`（ledger identity）で再検証し cid を取得；非 ledger は配列前に停止 |
| unit ごと | `verify_twelve_bank_dir(path, ctx)`（manifest／identity／call key／全 shard の bytes＝sidecar＝manifest／member／dtype／有限／cid 構造／範囲／UID／**全配列 SHA＝sidecar**）＋ manifest SHA＝ledger＋ NPZ file SHA／bytes＝**ledger の期待値**＝final inventory の byte 数＋配列統計（T1／T2／AX／PL）＋cid hash |
| 横断 | partition 内 9 配置の cid が (purpose, batch) ごとに同一（同 family latent）；D-2 reference との cid 同一（指定時）；N₀＋3N₀／N_fit 構造。`--max-dirs` は partial（exit 0 にならない）。`all_ok`＝file／member／array integrity |
| notebook | lock cell：commit・inventory・FAMILY・SIZE・RUN_ROOT（Drive の partition `out/`）・`D2_REF_ROOT`（任意）。cell 1 で script／ledger の SHA＝inventory，RUN_ROOT が ledger の run dir と一致；cell 2 で accepted mode 実行（report 読込みは型検査付き；欠落／不正は fallback False）；`verify_pass`＝rc 0 ∧ all_ok ∧ coverage ∧ binding ∧ fallback なし；cell 3 で zip |

## 4. 監査 all9 の指摘への対応
- **environment fingerprint 7 通り**：ledger は raw 値を partition ごとに不変のまま記録し，順序非依存の環境 identity（BLAS pool の集合）を**併記**（9 run で 1 値 `51d5dd3a…`）。再利用の完全一致要件は免除しない（`d3_bankgen.py` 不変）。
- **親 runtime**：8 notebook が execution count 1 以外で開始（1 つの親 runtime を再利用）。ledger の `parent_runtime_note` に監査の限定（別 attempt／別 child process／同一 source・profile・live preflight 通過；再生成の理由にしない）を転記。
- **容量**：記録値 27,217,472,580 B（NPZ container overhead 3,636 B／file）を ledger 総計に記録。
- tranche ① 報告書の非 blocking 注記（§2／§3 見出しの旧 SHA・件数）は v2.1 として訂正。

## 5. 試験
- `tests/test_d3b_tranche2.py`（11 case；外部資産がなければ 1 skip）：ledger の決定論・登録 file＝再導出・pins 一致・総計・partition 内容；ledger 編集 5 種（再 stamp 含む）の拒否；登録記録の編集 6 種（COMPLETE 再 stamp・sidecar・run manifest gate・registry manifest SHA・NPZ 混入・lock commit）の再導出拒否；pins 不一致の拒否；別 root の context 拒否；`D3bUnits` の lookup／拒否／sealed；formal intake の ledger 束縛（登録 units 必須・非 unit 拒否・self-test 経路不変）；検証器 test mode（合成 27 unit 全 ok・cid 同一・partial は exit 1・出力交差拒否・改変配列検出）；accepted mode（登録記録への binding 成功・relocated map・NPZ 不在で unit FAIL；registry／lock／final の改変は binding 停止）；非 ledger D-2 reference の停止；notebook の `verify_pass` 条件 8 case。
- 全 suite：**1544 case（1533＋11）全 pass**，failure／error／skip 0（13 chunk・JUnit `regression_logs/d3b_t2_pytest/j1..13.xml`；case の多重集合＝collect と一致）。

## 6. 提出物・次段
- 実行前監査で確認を求める点：(a) ledger の再導出束縛と NPZ 期待値の網羅（405），(b) 検証器の accepted-run binding・出力隔離・配列検証の経路（`verify_twelve_bank_dir` の全配列 SHA），(c) formal intake の ledger 束縛，(d) 検証 commit／inventory の固定。GO 後：Colab で 9 partition を 1 つずつ read-only 検証（CPU；1 partition ≈10〜20 min の見込み；`D2_REF_ROOT` に D-2 run の `out/d2` を与えて reference との cid 同一も確認）→ 監査 → 外側 receipt（配列受入れ）→ 実 bank での profile／gate・plan 固定。
