# Phase D4C-0 報告書（v2）— D-2W（9 W₂ case）と pseudo 列（n＝2000）の実装・自己試験（engine 0.103.0；launcher v0.2：R-D4C0-A／B の改訂）
2026-10-04。Claude 作成。ChatGPT 宛（D4C-0a／0b の実装受入れ監査と，正式実行（Colab）の実行前監査の依頼；v2）。v1（engine 0.102.0，commit `6c5e6024…`，zip `3a2f4406…`）は `D4C0_0.102.0_audit_decision.json`：**HOLD_FOR_LAUNCHER_CONTRACT_CORRECTIONS**（R-D4C0-A-LAUNCHER-RESULT-CONTRACT・R-D4C0-B-PREFLIGHT-OUTPUT-ANCHOR；新 module の主要接続は確認済み，既存 D-3c 受入れ維持）。**v2 の変更は notebook 2 本（attempt cell と preflight cell）と試験 `tests/test_d4c0.py`（45 → 97 case），本報告書，addendum，版表示（0.103.0）のみ**——engine module・script・pseudo 表・pins の値（版以外）・登録資産は 0.102.0 と byte 同一（`w2_cases.py` `d8e6e8da…`・`d4_pseudo.py` `d3336b3b…`・`positions.py` `b1f073ff…`・`d/d2w_cases.py` `6e379a30…`・`d/d4_pseudo.py` `a6e0772a…`・`d/d4_pseudo_table.json` `31fc50c3…`）。

## 0. 監査 R-D4C0-A／B への対応（§0.1〜0.2）と非 blocking 事項の確認（§0.3）
### 0.1 R-D4C0-A（成功 record の semantic 契約）
両 notebook の attempt cell（cell 3）の record 検査を次のとおり閉じた（`d2w_pass`／`pseudo_pass` は rc 0 ∧ 下記すべて）。
- **shape**（`launcher_fallback`）：schema 厳密一致（`d2w_run_record_v1`／`d4_pseudo_record_v1`）・`stage=='complete'`・`failures==[]`・`selftest is False`・`profile=='production_official'`・`required_inventory` list・`required_all_true` bool・`gates` dict・`source` dict・（D-2W）`context.cases` dict と `published_evidence` dict・（pseudo）`columns.identity`／`columns.file`／`pseudo_table`／`generation` dict。
- **gates**（新 flag `gates_ok`）：**信頼済み REQUIRED inventory**＝notebook 定数（D-2W 13 名／pseudo 10 名）であり，加えて lock に束縛した script file（SHA を lock と live source で照合済み）の `REQUIRED` 定数を AST（`ast.literal_eval`）で抽出して notebook 定数との一致を要求（不一致なら gates_ok False；試験 `script_required_changed`）。record の `gates` の key 集合＝REQUIRED，`required_inventory`＝REQUIRED，全 gate `is True`，`required_all_true is True`。record 自身の inventory を正解にしない。
- **evidence**（`evidence_ok`）：D-2W は **canonical 9 case（`CANON` 定数：E2／E7／E8 × L1.00／L1.20／L1.50）** を固定し，`context.cases` の key 集合＝CANON，`published_evidence` の file 集合＝CANON から導出した 9 case file＋context record（返却 cases から導かない；E1／8 case を拒否）。各 file は SHA／bytes の内容照合に加えて **semantic 束縛**：case record は schema `d2w_case_record_v1`・key・family／size・`inputs.formal is True`・manifest／result SHA と decision（trigger／state／B_final）が run record の case 要約と一致；context record は schema・context／asset SHA・`n_cases==9`・`case_records` の key 集合＝CANON と各 manifest／result SHA の一致。これにより **re-hash した改変**（file と published SHA を整合させた改変）も拒否される（試験 `rehashed_case_evidence`／`rehashed_context_evidence`／`case_summary_mismatch`）。pseudo は NPZ の SHA／bytes・`columns.identity` n＝2000／m＝1・`generation.n==2000`・UID 端点 [1,400,5001,0,0]／[1,400,5001,0,1999]・`pseudo_table.table_sha256`＝lock・`n_pseudo==2000`／`m==1`。
- 科学的 w2-unresolved は成功条件に含めない（試験 `unresolved_ok`：9 case すべて trigger unknown／w2-unresolved で `d2w_pass` True）。
- 試験：監査の 13 反例（false／missing／empty gates・exception stage・non-empty failures・wrong schema・wrong case set）に extra gate・required_inventory 不一致・required_all_true False・selftest True・script の REQUIRED 変更・re-hash 3 種・anchor 内の所有外 file を加え，D-2W 36 case／pseudo 29 case の attempt cell 試験（正常 fixture は実 script の REQUIRED を AST で取得）。
### 0.2 R-D4C0-B（preflight の出力先検査順序）
両 notebook の preflight cell（cell 2）に `_safe_output_anchor(path, protected)` を置き，**最初の `os.makedirs`／lock publication より前**に呼ぶ：最終 component が symlink でない（realpath 照合）・保護 root（source checkout・Phase C・stage root・`/content/drive`・（D-2W）3 入力 root）との交差なし・存在する場合は実 directory で **launcher 所有の entry（lock・final record・superseded record・`run_<attempt>`・stdout／stderr）だけ**を含み symlink entry なし。拒否時は例外で停止し，拒否先にも他にも何も書かない（FAIL record も書かない）。attempt cell は **同じ関数**で lock の anchor を再検査（lock 値と現在値の両方の保護 root）。試験：preflight 開始前からの symlink（入力 directory へ：symlink 先の member／bytes 不変・lock 不在）・入力／source／Phase C／stage 配下・file・所有外 file・symlink entry の拒否と，新規／空／所有 entry のみの既存 directory の許容（D-2W 11 case・pseudo 9 case）。
### 0.3 非 blocking 事項
- §5.1（replay と登録認証の区別）：了解。`restore_w2_context` の context payload は manifest／result／decision から成り，inputs／constants header の認証は登録 tranche（原本 case／context／run／lock を acceptance・receipt・pins に束縛；`expected_context_sha256` は record の自己申告でなく pins から）で行う。設計 v0.2 §C の登録行に同旨。
- §5.2（loader stub）：了解。`D2W_REGISTRATION`／`PSEUDO_REGISTRATION` の充填だけでは成功経路にならないことを認識しており，登録 tranche で loader 本体（原本認証・pins 検査）と拒否試験を実装する。本 packet で登録 API の受入れを求めない。
- §5.3：本報告書の self-test は rc 1（env gate のみ False）・正式 PASS False の限定付き機能試験であり，時間／RSS は著者計測（独立再現なし）。標準 CPU の資源十分性・正式 9 case の時間は認定対象外。


## 1. 実装の要約と監査条件の対応
| 条件 | 実装 |
|---|---|
| R-D4DESIGN-A（API・D-2 束縛） | D4C-0a の intake は `intake_w2_position_bank` の返却 `manifest_sha256` を登録 D-2 ledger の `cfg<id>_w2` unit に照合（`assemble_w2_cases(registered_units=…)`；script の formal path は加えて `d2_bank_registry.json` の family／formal／run_id を ledger に照合）。gate の keyword 呼出し・`target_commitment`・E1 別扱いは設計 v0.2 §B／§F.1 に固定（D4C-1）。 |
| R-D4DESIGN-B（D-2W の登録・復元） | 27 raw unit（primary のみ）→ 登録 whitening 値（`registered_whitening`）→ 9 case（`case_plan`：observer 1..3）→ `build_w2_context`（登録 shared-null asset；exact POT；既存 W₂ 数学を変更しない）→ typed record（manifest・stored evidence・decision・入力 identity）→ **`restore_w2_context`（配列なし replay：`RegisteredBankIdentity` stand-in＋`verified_w2_for_decision`）で published record から復元し live と一致を REQUIRED gate**。拒否試験 §3。登録 loader は `D2W_REGISTRATION=None` で拒否。技術 FAIL（例外）と w2-unresolved を区別して保存。 |
| R-D4DESIGN-C（pseudo 別表・順序） | `d/d4_pseudo_table.json`（purpose 400・group 5001・m 1・K 2000）；D-2 表不変（validator の拒否を試験）；key 非重複を D-2 表 44 group × 2 batch × 全 stream に対して試験；全 family 共通の順序付き対；sort／行除去なし；非有限は技術 FAIL；`commit_target` は既存 helper（式を試験で確認；nonce は launcher に渡さない）。 |
| R-D4DESIGN-D／E／F | D4C-1 の仕様として設計 v0.2 §F に固定（本 packet に実装なし）。E1 3 配置・条件付き算術（8.16／29.38／13.44 GB）・時間は実測の方針を反映。 |
| R-D4DESIGN-G（launcher） | notebook 2 本（v0.2）は D-3c v0.3 規約を継承（anchor・1 検査関数を staging 前と起動直前に 2 回・attempt 別 initial 非成功 record・旧 record の退避）に加え，**preflight の出力先検査（最初の書込み前）**，**信頼済み REQUIRED inventory・canonical 9 case・semantic 束縛付き evidence 照合**（§0.1〜0.2）。 |

## 2. 自己試験の実測（sandbox；CPU）
| 項目 | 値 |
|---|---|
| pseudo self-test（`d/d4_pseudo.py --selftest-n 50 --selftest-skip-env-lock`） | rc 1（env lock のみ False；他 9 gate True；PSEUDO_PASS False＝self-test）；3.1 s；peak RSS 302 MB；列 identity は別 process 実行と一致（paired SHA `e3b17aad…`；前 session の smoke と同一） |
| D-2W self-test（合成 W₂ bank：E2/L1.00 の 3 unit，実 kernel・登録 matched root・scale 0.025 → K＝50 × m＝100；`--selftest-small --selftest-cases E2/L1.00`） | rc 1（env lock のみ False；他 12 gate True：`G_d2_inputs_resolved`・`G_cases_assembled`・`G_context_built`・`G_records_restored` を含む）；合計 54.5 s（intake 3.7 s・評価 45.5 s・復元 2.3 s）；peak RSS 1,298 MB；結果 trigger unknown／w2-unresolved／B_final 400（K＝50 の合成 bank の科学的結果であり，PASS の条件ではない） |
| 復元 | published case record（3.86 MB；stored evidence を含む）から `restore_w2_context` 1.5〜2.3 s；context SHA・decision・checksum が live と一致 |

## 3. 試験（`tests/test_d4c0.py`：14 関数・97 case；全 suite は `test_log.txt`）
- pseudo 表：登録 file と `build_pseudo_table()` の一致・rng key・SHA 不一致／m／K／purpose／batch／group 衝突（1002・4001・50101・70303）／selection／role／chunk／schema の拒否；D-2 表の全 44 group が拒否範囲内・key 非交差・旧 validator の purpose `pseudo` 拒否。
- 生成（実 kernel）：決定論・prefix 安定（n 20 ⊂ n 50）・順序保持（非 sort）・cid／UID・root SHA・paired SHA；n＞2000／root 形状／NaN root の拒否；保存→再検証；改変（値 1e-9・列入替・逆順・member 欠落・UID・非有限・f32 dtype・file identity・identity の n）の拒否；登録 loader 拒否；`commit_target` の式と nonce 長。
- pseudo script：self-test record の束縛（attempt／lock／source／table SHA／rng keys）・列 file identity・再実行一致；OUT が source／phaseC／mt 配下・symlink・非空 → rc 2 で未書込み；profile 不正 → rc 1。
- D-2W：`case_plan` 9 case（27 config；group＝30000＋cid）；`RegisteredBankIdentity` の契約（exact schema・immutable・`bank_identity` dispatch・距離実行不可）；script end-to-end（§2）：record の束縛・covariance receipt・shared-null identity・published evidence の SHA／bytes・case record の inputs（unit manifest・f64／f32 bank identity・matched root SHA・whitening identity・constants）・context record；本 process での復元一致。
- 復元の拒否：context SHA 不一致・非 formal（require_formal）・formal 主張の小 bank（K·m≠200000）・別 asset・schema／family／key・重複・空・decision 改変（validated 化・trigger True／False 化・B_final・checksum）・manifest 改変／SHA・result 改変／SHA・evidence の bank identity 改変・非有限注入（技術）・混在 list。
- script の拒否：OUT 契約（入力配下・source・phaseC・symlink・非空）・family root 欠落／空／case key 不正（`G_d2_inputs_resolved` False）・**formal path on 小 bank（`--selftest-small` なし）は intake で拒否（評価されない）**・改変 NPZ（1 byte）は intake で拒否（評価されない）・profile 不正。
- `assemble_w2_cases`：registered_units の manifest 照合（不一致・欠落の拒否）・誤 root・root 欠落・family 不一致・formal on 小 bank・size の unit 欠落の拒否。
- notebook（v0.2）：構造（5 cell・parse・`--selftest` 不在・出力検査が makedirs より前・REQUIRED 定数＝script の AST 抽出・canonical case 定数）；preflight 出力検査 20 case（§0.2）；attempt cell の exec 試験 D-2W 36 case／pseudo 29 case（§0.1；ok／staged_ok／旧成功の退避／unresolved_ok／pass_false／rc1／record 欠落／commit・script・root・lock・table 変更／staging 中の script 変更／anchor symlink・所有外 file／evidence 改変・欠落・8 case・E1 置換・re-hash 3 種／attempt・source・table 不一致／起動失敗／容量不足／13 反例＋拡張）。

## 4. 正式実行の手順（実行前監査後）
- **D4C-0b（先に実行可；短時間）**：`d/MirrorTopology_Step1_D4_pseudo_v0.1.ipynb`（標準 CPU；cell 0 に commit と inventory SHA）→ zip（lock・attempt record・`d4_pseudo_record.json`・`d4_pseudo_columns.npz`（≈100 KB）・stdout／stderr）。
- **D4C-0a（1 run・3 family・9 case）**：`d/MirrorTopology_Step1_D2W_cases_v0.1.ipynb`（標準 CPU；cell 0 に commit・inventory SHA・E2／E7／E8 の `out/d2`）→ zip（lock・attempt record・run record・9 case record（各 ≈4 MB）・context record・stdout／stderr；≈40 MB）。見込み時間 ≈10 分（§2 の solve 単価から；保証しない）。
- 受入れ後：原本登録（`registered_assets/d2w/`・`registered_assets/d4/pseudo/`），`D2W_REGISTRATION`／`PSEUDO_REGISTRATION` 充填，pins 4 項目追加，registered loader 有効化と試験（D4C-0 tranche ②）。

## 5. 限定
本 packet は実装と小規模 self-test であり，実 bank の 9 case exact OT・正式 n＝2000 の生成・Colab 資源の実測・登録 loader の有効化・family partial／combiner・較正値・usable・Phase E は含まない。合成 W₂ bank（K＝50）の w2-unresolved は小規模 bank の性質であり，実 bank の結果を予断しない。
