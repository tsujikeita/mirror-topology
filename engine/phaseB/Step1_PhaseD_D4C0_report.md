# Phase D4C-0 報告書 — D-2W（9 W₂ case）と pseudo 列（n＝2000）の実装・自己試験（engine 0.102.0）
2026-10-04。Claude 作成。ChatGPT 宛（D4C-0a／0b の実装受入れ監査と，正式実行（Colab）の実行前監査の依頼）。前提：`D4_calibration_design_v0.1_audit_decision.json`（ACCEPTED_IN_PRINCIPLE_WITH_IMPLEMENTATION_CONDITIONS；D4C-0a／0b 起草・小規模試験 GO；R-D4DESIGN-A〜G）。engine `step1_engine 0.102.0`（0.101.0 からの変更：**新 module 2（`w2_cases.py`・`d4_pseudo.py`；MODULES 56）**，**`positions.py` に `RegisteredBankIdentity`（identity のみの stand-in）と `bank_identity` の dispatch を追加**（既存の PositionBank 経路は不変），**新 script 2（`d/d2w_cases.py`・`d/d4_pseudo.py`），新表 `d/d4_pseudo_table.json`，pins 1 項目（`d4_pseudo_table_sha256`），notebook 2 本，試験 1 file（13 関数・45 case），設計 v0.2，本報告書，addendum，版表示**。数値 kernel・既存登録資産・既存 script／notebook・D-2 CRN 表は不変）。

## 1. 実装の要約と監査条件の対応
| 条件 | 実装 |
|---|---|
| R-D4DESIGN-A（API・D-2 束縛） | D4C-0a の intake は `intake_w2_position_bank` の返却 `manifest_sha256` を登録 D-2 ledger の `cfg<id>_w2` unit に照合（`assemble_w2_cases(registered_units=…)`；script の formal path は加えて `d2_bank_registry.json` の family／formal／run_id を ledger に照合）。gate の keyword 呼出し・`target_commitment`・E1 別扱いは設計 v0.2 §B／§F.1 に固定（D4C-1）。 |
| R-D4DESIGN-B（D-2W の登録・復元） | 27 raw unit（primary のみ）→ 登録 whitening 値（`registered_whitening`）→ 9 case（`case_plan`：observer 1..3）→ `build_w2_context`（登録 shared-null asset；exact POT；既存 W₂ 数学を変更しない）→ typed record（manifest・stored evidence・decision・入力 identity）→ **`restore_w2_context`（配列なし replay：`RegisteredBankIdentity` stand-in＋`verified_w2_for_decision`）で published record から復元し live と一致を REQUIRED gate**。拒否試験 §3。登録 loader は `D2W_REGISTRATION=None` で拒否。技術 FAIL（例外）と w2-unresolved を区別して保存。 |
| R-D4DESIGN-C（pseudo 別表・順序） | `d/d4_pseudo_table.json`（purpose 400・group 5001・m 1・K 2000）；D-2 表不変（validator の拒否を試験）；key 非重複を D-2 表 44 group × 2 batch × 全 stream に対して試験；全 family 共通の順序付き対；sort／行除去なし；非有限は技術 FAIL；`commit_target` は既存 helper（式を試験で確認；nonce は launcher に渡さない）。 |
| R-D4DESIGN-D／E／F | D4C-1 の仕様として設計 v0.2 §F に固定（本 packet に実装なし）。E1 3 配置・条件付き算術（8.16／29.38／13.44 GB）・時間は実測の方針を反映。 |
| R-D4DESIGN-G（launcher） | notebook 2 本は D-3c v0.3 規約を継承（anchor・1 検査関数を staging 前と起動直前に 2 回・attempt 別 initial 非成功 record・旧 record の退避・semantic record 検査・**published evidence の内容照合**（D-2W：9 case record＋context record の SHA／bytes；pseudo：NPZ の SHA／bytes と n＝2000・m＝1））。 |

## 2. 自己試験の実測（sandbox；CPU）
| 項目 | 値 |
|---|---|
| pseudo self-test（`d/d4_pseudo.py --selftest-n 50 --selftest-skip-env-lock`） | rc 1（env lock のみ False；他 9 gate True；PSEUDO_PASS False＝self-test）；3.1 s；peak RSS 302 MB；列 identity は別 process 実行と一致（paired SHA `e3b17aad…`；前 session の smoke と同一） |
| D-2W self-test（合成 W₂ bank：E2/L1.00 の 3 unit，実 kernel・登録 matched root・scale 0.025 → K＝50 × m＝100；`--selftest-small --selftest-cases E2/L1.00`） | rc 1（env lock のみ False；他 12 gate True：`G_d2_inputs_resolved`・`G_cases_assembled`・`G_context_built`・`G_records_restored` を含む）；合計 54.5 s（intake 3.7 s・評価 45.5 s・復元 2.3 s）；peak RSS 1,298 MB；結果 trigger unknown／w2-unresolved／B_final 400（K＝50 の合成 bank の科学的結果であり，PASS の条件ではない） |
| 復元 | published case record（3.86 MB；stored evidence を含む）から `restore_w2_context` 1.5〜2.3 s；context SHA・decision・checksum が live と一致 |

## 3. 試験（`tests/test_d4c0.py`：13 関数・45 case；全 suite は `test_log.txt`）
- pseudo 表：登録 file と `build_pseudo_table()` の一致・rng key・SHA 不一致／m／K／purpose／batch／group 衝突（1002・4001・50101・70303）／selection／role／chunk／schema の拒否；D-2 表の全 44 group が拒否範囲内・key 非交差・旧 validator の purpose `pseudo` 拒否。
- 生成（実 kernel）：決定論・prefix 安定（n 20 ⊂ n 50）・順序保持（非 sort）・cid／UID・root SHA・paired SHA；n＞2000／root 形状／NaN root の拒否；保存→再検証；改変（値 1e-9・列入替・逆順・member 欠落・UID・非有限・f32 dtype・file identity・identity の n）の拒否；登録 loader 拒否；`commit_target` の式と nonce 長。
- pseudo script：self-test record の束縛（attempt／lock／source／table SHA／rng keys）・列 file identity・再実行一致；OUT が source／phaseC／mt 配下・symlink・非空 → rc 2 で未書込み；profile 不正 → rc 1。
- D-2W：`case_plan` 9 case（27 config；group＝30000＋cid）；`RegisteredBankIdentity` の契約（exact schema・immutable・`bank_identity` dispatch・距離実行不可）；script end-to-end（§2）：record の束縛・covariance receipt・shared-null identity・published evidence の SHA／bytes・case record の inputs（unit manifest・f64／f32 bank identity・matched root SHA・whitening identity・constants）・context record；本 process での復元一致。
- 復元の拒否：context SHA 不一致・非 formal（require_formal）・formal 主張の小 bank（K·m≠200000）・別 asset・schema／family／key・重複・空・decision 改変（validated 化・trigger True／False 化・B_final・checksum）・manifest 改変／SHA・result 改変／SHA・evidence の bank identity 改変・非有限注入（技術）・混在 list。
- script の拒否：OUT 契約（入力配下・source・phaseC・symlink・非空）・family root 欠落／空／case key 不正（`G_d2_inputs_resolved` False）・**formal path on 小 bank（`--selftest-small` なし）は intake で拒否（評価されない）**・改変 NPZ（1 byte）は intake で拒否（評価されない）・profile 不正。
- `assemble_w2_cases`：registered_units の manifest 照合（不一致・欠落の拒否）・誤 root・root 欠落・family 不一致・formal on 小 bank・size の unit 欠落の拒否。
- notebook：構造（5 cell・parse・`--selftest` 不在・D-3c v0.3 規約の要素）と attempt cell の exec 試験（D-2W 19 case：ok／staged_ok（registry＋`cfg*_w2` のみ複製，`_b0` は複製しない）／旧成功の退避／pass_false／rc1／record 欠落／commit・script・root・lock 変更／staging 中の script 変更（子 process なし）／anchor symlink（未書込み）／evidence 改変・欠落・8 case／attempt・source 不一致／起動失敗／容量不足；pseudo 14 case：同様＋table 変更・NPZ 改変・n＝50・table SHA 不一致）。

## 4. 正式実行の手順（実行前監査後）
- **D4C-0b（先に実行可；短時間）**：`d/MirrorTopology_Step1_D4_pseudo_v0.1.ipynb`（標準 CPU；cell 0 に commit と inventory SHA）→ zip（lock・attempt record・`d4_pseudo_record.json`・`d4_pseudo_columns.npz`（≈100 KB）・stdout／stderr）。
- **D4C-0a（1 run・3 family・9 case）**：`d/MirrorTopology_Step1_D2W_cases_v0.1.ipynb`（標準 CPU；cell 0 に commit・inventory SHA・E2／E7／E8 の `out/d2`）→ zip（lock・attempt record・run record・9 case record（各 ≈4 MB）・context record・stdout／stderr；≈40 MB）。見込み時間 ≈10 分（§2 の solve 単価から；保証しない）。
- 受入れ後：原本登録（`registered_assets/d2w/`・`registered_assets/d4/pseudo/`），`D2W_REGISTRATION`／`PSEUDO_REGISTRATION` 充填，pins 4 項目追加，registered loader 有効化と試験（D4C-0 tranche ②）。

## 5. 限定
本 packet は実装と小規模 self-test であり，実 bank の 9 case exact OT・正式 n＝2000 の生成・Colab 資源の実測・登録 loader の有効化・family partial／combiner・較正値・usable・Phase E は含まない。合成 W₂ bank（K＝50）の w2-unresolved は小規模 bank の性質であり，実 bank の結果を予断しない。
