# Step1 Phase B・B-3-3 packet v2 監査
## engine 0.54.0：受付ガード閉鎖・引渡し方針の確認・receipt／期限表記の訂正候補

2026-09-19（日本時間）。Claude伝達用。対象：今回の`files_9.zip`内5ファイル。

## 0. 結論と承認範囲

**R331-Aのsource-bound受付修正を承認する。R331-Bの統合runnerに残る再生成の区別、R331-Cの方式A・原文／grid checklist・較正先行順序・物理cloneの工程分担案は、今回の引渡し方針として受け入れられる。新しい必須Python修正はない。B-2・B-3-0・B-3-1・B-3-2 A/Bの受入れは維持する。**

ただし、受領版の機械可読receiptには短縮SHA／短縮commitと未収録の出力識別情報が残る。「完全commit・SHAまで完成」とする報告を、そのまま事実とは認定しない。§3の較正・再利用期限も、正しい§4.3の依存順序へ揃える。

**残る整合化は文書・JSONだけである。本監査で実ファイルから補完した5ファイルのメタデータ訂正候補を作成し、候補overlayの全172 SHAとreceiptの実ファイル照合を確認した。その候補の適用内容を確認・採用した状態でB-3-3引渡しを確定し、Phase C packet準備へ進んでよい。新たなColab数値実行や同じ数値試験の全面再実行は要求しない。**

この判断はB-3全体完了、ENGINE_VALID、完成production engine、Phase C/rules v1.0科学的freeze、正式全family較正、実観測label解放の承認ではない。物理cloneの工程変更案の最終確認もPhase Cに残る。

| 対象 | 判断 |
|---|---|
| 提出0.54.0の受付実装 | 受入れ承認。R331-A閉鎖 |
| 再利用scope・Phase C準備方針 | 受入れ。runner未接続等の未実装状態を維持 |
| 提出JSONを「完全な機械可読receipt」と呼ぶこと | まだ不可。短縮値等を補完 |
| 本監査のメタデータ訂正候補 | 同一性・参照関係を検証済み。採用後の引渡し確定可 |
| 過去の受入れ済み数値run／資産 | 維持。再実行不要 |
| Phase Cの科学的freeze／正式production使用 | 本監査では未承認 |

## 1. 入力・変更の同定

外側は5 file member、内側packetは185 file member。CRC・重複・危険path・symlink検査に異常なし。外側の報告書・receipt文書・spec追補・receipt JSONは内側の対応物と全件byte一致した。

| 入力 | SHA256 |
|---|---|
| files_9.zip | `98a755dd90350c598ed9c39d820dbd1178733db17f6d61b7c5569618cee71124` |
| engine_phaseB_for_commit_B3_3_v2.zip | `0901a38f7d4d85cd25bd1e327bdecff2d671bb027e1d4e54bde508095bdd5380` |
| 受領inventory | `20a90c59d449ed8c2ab365a8ce00b0e355a0cad058be07d7944d7df1f8797d9c` |
| twelve_assets.py | `550781567142579fc8cb6a4a690afa7b3831fdcc7b51745b39f365a71eb6cc8e` |
| 受領b3_3_receipts.json | `0f597f77d368bcac18d231ccd579d51fe8dbaa8c70f04a8fe448fa2b0c9f46bf` |

前回受領0.53.0との比較：

- 44 module中42はbyte不変。`twelve_assets.py`の`reg.validate()`→`_registry(reg)`の1行と、`__init__.py`の0.53.0→0.54.0が変更点。
- `twelve_assets.py`は前回参考修正と全bytes一致。
- 既存71 test fileはbyte不変。監査原本17 caseと接続2 caseを2 fileとして追加し、73 file・688 test関数・909展開case。
- 採用17/2試験は原本と全関数本体のASTが一致。差はROOT既定値と一時出力先の初期化のみ。fixture・assert・故障注入は不変。
- 数値builder、B-3計算script、notebook、規則本文、tables JSON、spec v0.2追補はbyte不変。3つのpinsはengine_versionのみ変更。
- 同梱checkerの独立実行：**172/172 SHA一致、不整合0**。数値・内容の正しさをchecksumだけで証明したとは扱わない。
- 135 Python sourceとb3配下24 code cellを構文compileしエラー0。
- 著者JUnit7本の件数531/154/95/39/40/36/14、計909。独立collect-onlyの909 node集合と完全一致し、重複・failure/error/skipped記録0。**全909件を当方でも実行したのではない。**
- 最後に受領185 memberのbytes・集合を照合し、変更・欠落・新規追加0。

## 2. R331-A：新受付のsource-bound契約――閉鎖

前回の原本`test_b33_receipt_review.py`をsource無変更で今回packageに適用し、**17/17 PASS**。

内部整合のみの`registry_from_dict`で復元したregistry、GridRegistryでない簡易objectを、新intakeは拒否する。正規のsource-bound factoryおよび`registry_from_dict_bound`の出力は受理される。

正常な実登録assetのintake→全9 memberのget→snapshotではgenerator呼出しなし。返したmemberは独立copy。変更されたlive asset、未知receipt、同じJSONの異なるfile bytes、verification表示の変更は拒否し、後段検査で失敗する対照でも部分的な_VERIFIED登録は発行しない。

この確認は既存登録資産の受付・再利用契約であり、E2/E8全格子を今回再実行したという意味ではない。

## 3. R331-B：再生成省略のscope――文書訂正を確認

改訂文書§2と§3は、intake/get/snapshot/`evaluate_family_full`と、再生成の残る`run_first_wave`を区別している。

前回原本の接続2件を再実行：**2/2 PASS**。実際の既存registry/manifest/W2Contextを持つ有限人工fixtureを使用し、evaluatorでは登録asset経由の12位置Result・required manifest・eligible truthが従来経路と一致し、generator呼出しなし。

一方、統合runnerは依然としてE2/L1.00の再生成入口に入ることを、重い処理直前のsentinelで確認した。これは既知の制約のcharacterizationであり、runner最適化が完成した証拠ではない。現在の文書はその接続を正式再利用前の残件に明記しており妥当。今ここでrunner全体を書き換える要求はしない。

## 4. R331-C：Phase Cの構成・順序――主要修正を受入れ

### 4.1 方式Aとchecklist

draft4.1本文・参照JSONのbytesを保持し、v1.0採用宣言・資産参照・工程変更を別manifest/追補へ置く**方式A**が明示された。現本文／tablesの`verify_binding`は正常。本文だけ追記すると既存bindingで拒否される原本対照も維持している。

研究計画v0.4/v0.5原文と完全SHA、第一波gridのfull-precision座標・単位・lift・immutable ID・status・prior・完全SHA、計算時sourceと現sourceの区別、packet外資産の取得・検証方法がchecklistへ追加された。原文はこのpacketには同梱されておらず、**今回その原文照合を新たに済ませたとは扱わない**。Phase Cの作業として残す。

### 4.2 較正先行と物理clone

§4.3は、現target-first runnerを先にofficial実行する運用を明示的に否定し、実観測full-grid判定値を計算しないdriverの受入れ→MC資産固定→較正・監査→usable封印→Phase E実観測評価という順序へ訂正されている。この方針を受入れる。

幾何nearest-clone/circle/priorは受入済み、A11物理共分散のclone同値性は未実施と分け、後者をPhase Dの共分散生成時・正式使用前へ移す案を**工程変更としてPhase Cで確認する**と明記した。この記述は前回要求に沿う。本文書だけでその延期が既承認になったとはしない。

### 4.3 同じ文書の期限表にも依存順序を反映する

受領§3の較正先行行はなお「Phase Eの実観測評価前（較正packetの凍結時）」、外部参照再利用行は「Phase Eのarchive再利用前」である。§4.3が正しいため直ちに誤実行した証拠ではないが、実務用の表だけを読んでも期限を誤らないよう、**正式較正の実行前／較正を含む最初の正式再利用前**へ揃える。候補ではpseudo完全archive行も同じ書式に整理した。工程名を新しく変更する提案ではない。

## 5. 新しい機械可読receipt：完全値の補完が残る

報告書は`registered_assets/b3_3_receipts.json`を完全commit・SHAの表と説明するが、実ファイルは次の状態。

| 行／field | 受領値・状態 | 必要な訂正 |
|---|---|---|
| B-3-0 out_zip_sha256 | `d3386faa`（8桁） | 元ZIPから64桁へ |
| B-3-0 executed_notebook_sha256 | `bd423712`（8桁） | 元notebookから64桁へ |
| B-3-1 source_commit | `903458d71e94`（12桁） | 保存launcherの40桁へ |
| B-3-1 outputs | ZIP名のみ | ZIP/notebook/final/run manifestのSHAを補完 |
| audits | 監査書名のみ | 候補では実監査書file SHAも対応付け |

B-3-0のnoteは「監査記録が短縮値」とするが、既存監査書には完全値があり、元のZIP/notebookも保持されている。今回その実bytesからSHAを再計算した。B-3-1も元final recordのlauncher.commitを読み、元監査の完全値と対応させた。

B-3-2 A/Bの既存完全値は正しい。5つの登録資産／final recordを元の受入れ済みA/B出力ZIPから直接読み、全件byte一致を再確認した。packet外poolのSHA/サイズも元ZIPと一致。全W2や位置計算を再実行したのではない。

**B-2のsource_commit=nullは、他の短縮commitと同一の誤りとして扱わない。** B-2はpacketの受入れであり、今回参照した記録からcommitを新たに特定していない。候補ではnullの理由を明記し、初回0.39/0.40の受入れと後続維持0.43のinventoryを区別した。推測のcommitを埋めていない。

新receipt JSONは現在の数値intakeの権威そのものではない。intakeのcode-pinned asset/file SHAは正しいままであり、JSONの短縮値が今回の登録座標やnull値を破損させたという実証ではない。最終的な機械可読引渡し情報を正確にする修正である。

## 6. 文書・JSONだけの訂正候補と検証

`metadata_candidate/engine/phaseB/`の変更は5ファイル：

1. `registered_assets/b3_3_receipts.json`：既存の実ファイルから完全SHA・commit・監査書SHAを補完。B-2は未確認理由を明記。
2. `Step1_PhaseB_B3_3_receipts_and_deadlines.md`：receipt説明と期限表を§4.3へ揃える。
3. `Step1_PhaseB_engine_spec_v0.3_addendum.md`：初版日付／現版、当時の状態、旧「現版0.40.0」の表示を整理。歴史的表を削除しない。
4. `B2_completion_inventory.json`：変更した現行文書2件とreceiptのSHAのみ再束縛。
5. `Step1_PhaseB_B3_3_v2_report.md`：候補での補完範囲と候補inventoryを明記。

**Python source、全test、notebook、pins、draft4.1/tables、数値asset、過去のrun/log/checkpoint/監査書は変更していない。engine 0.54.0を維持。** 候補は原提出物とは別directoryに作成し、監査側の文書訂正候補であると明記した。

候補を原packetに重ねたread-only checkerは**172/172一致**。別の確認scriptで、各receiptの出力ZIP・notebook・final/run manifest・launcher・監査書SHAを改めて読み直し、一致を確認した。元の短縮SHAから文字列を推定したものではない。候補でも元本文とtablesのbindingは正常。

| 識別値 | SHA256 |
|---|---|
| 受領v2 inventory | `20a90c59d449ed8c2ab365a8ce00b0e355a0cad058be07d7944d7df1f8797d9c` |
| 文書訂正候補を適用したinventory | `0ece0a3d1e991d37b7bbc51d15c1a89c0d96d40920f3b79a404cede5bad2943e` |

候補をそのまま採用する場合には後者を使う。さらに独自編集した場合には、その最終bytesから更新する。旧run recordや過去のaccepted sourceのSHAを新しい値へ書き戻さない。未作成のcommit値はここには書かず、実際のcommit後に記録する。

## 7. 実行した試験と限界

| 検査 | 当方の独立実行 |
|---|---|
| 前回の契約試験原本 | **17/17 PASS** |
| 前回の接続試験原本 | **2/2 PASS** |
| 提出新規2件＋採用された原本19件 | **21/21 PASS** |
| 既存asset回帰（選択18件） | **18/18 PASS**、対象外4件は明示deselect |
| 全suite | **909件の収集のみ**。著者JUnitと集合一致 |
| 受領packet／候補packet SHA | **ともに172/172一致** |
| 元A/B出力と登録ファイル5件 | **全bytes一致** |
| 候補receiptの完全値と元実ファイル | **一致** |

原本19件と同梱19件は同じ試験で、別の科学的検証38種類とは数えない。runner再生成と本文だけの追記拒否は現状制約を確認するcharacterizationで、未実装機能の完成証明ではない。

監査環境：Python 3.13.5／NumPy 2.3.5／SciPy 1.17.0／pytest 9.0.2。試験processはBLAS/OMP/MKL 1 thread、pytest plugin自動読込み無効。POT・healpy・CAMB未導入。追加インストールなし。登録Colab環境ではない。

未実施：新Colab、実Drive、全909件の独立実行、全格子再生成、物理共分散/sky/bank生成、6000 pairのOT再計算、正式較正、Phase Cで要求される研究計画原文の新規照合。

## 8. 次工程

今回のcodeと引渡し方針は受入れる。文書/JSON候補を確認・採用してB-3-3を引渡し記録として確定し、Phase C packetの作成へ進めてよい。採用候補自体の同一性検査は本監査で完了しており、その同じ文書訂正だけのために、新しい大規模Colabや全面コード監査を一巡させる要求はしない。

Phase Cでは、方式Aの採用宣言と完全manifest、原文照合、第一波grid、外部大規模資産の所在/再検証、工程変更案、各未実装機能の使用前gateを確認する。今回のB-3-3受入れを、完成production engineやENGINE_VALIDの一括承認へ拡張しない。

**最終判断：R331-A閉鎖、B-3-3実装と主要引渡し方針は承認。残る文書・receiptの完全値補完は本監査の検証済み候補で対応可能。過去の受入れと資産は維持、数値再実行不要。**

### 証拠

- `evidence/comparison.json`, `changes.diff`, `input_identity.json`, `packet_check.json`, `author_junit_comparison.json`, `final_members.json`。
- `evidence/original17/`, `original_connection2/`, `submitted21/`, `legacy18/`, `collection/`：コマンド・ログ・JUnit。
- `evidence/assets_same_as_accepted_output.json`, `submitted_receipt_completeness.json`, `receipt_identity_sources.json`。
- `evidence/metadata_candidate_changes.json`, `metadata_candidate_packet_check.json`, `metadata_candidate_identity_check.json`。
- `metadata_candidate/`：5ファイル、差分、README。`prior_evidence/tests/`：前回原本2ファイル。
- 新規検証コード：`setup_review.py`, `compare.py`, `run_checks.py`, `metadata_checks.py`, `build_metadata_candidate.py`, `check_receipt_candidate.py`。
