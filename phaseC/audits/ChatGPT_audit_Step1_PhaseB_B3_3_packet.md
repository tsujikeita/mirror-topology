# Step1 Phase B・B-3-3 packet監査
## engine 0.53.0：receipt集約・登録資産受付・Phase C引渡し条件

2026-09-19（日本時間）。Claude伝達用。対象：`files_8.zip`内の5ファイル。

## 0. 判断

**B-2の実装受入れ、B-3-0・B-3-1・B-3-2 A/Bの実行後受入れPASSを維持する。B-3-3のreceipt集約と登録資産同梱は、下記の限定・文書訂正を伴って受け入れられる。新しい登録資産intakeのsource-bound契約と、Phase C引渡し文書の整合化が済むまで、現packetそのままの最終確定は保留する。Phase Cの準備作業は進めてよい。**

今回、受入れ済み資産の数値誤りを発見したわけではない。全格子再生成や共有null生成、過去のColab runの再実行は求めない。新しい必須コード補強は `twelve_assets.py` の既存ガード呼出し1行であり、その参考候補を提供する。統合runner側の再生成省略は現状の限界を正確に記し、正式にその経路を使う前の接続事項として残すことができる。

| ID | 内容 | このpacketでの扱い |
|---|---|---|
| R331-A | 新intakeにも既存のGridRegistry型・source-bound scopeの検査を適用 | 1行の参考修正を確認後に反映 |
| R331-B | 新intake/get/evaluatorと、再生成が残るrun_first_waveを区別 | 無再生成のscopeを訂正し、統合接続を正式使用前の残件に明記。今回長い再生成は不要 |
| R331-C | 本文↔tablesのSHA、Phase C原文／grid checklist、較正先行の順序・受入期限 | 文書・凍結設計を整合化。数値定数の変更ではない |

`ENGINE_VALID`、B-3全体完了、Phase C科学的freeze、正式全family較正、実観測label解放は今回承認しない。完成していないproduction機能を新しいreceiptで実装済みにしない。

## 1. 受領物・差分の同定

外側ZIPは5 file member、内側packetは181 file member。CRC、重複名、危険path、symlinkに異常なし。外側の報告書・spec追補・twelve_assets.py・新testの4単独ファイルは、内側対応物と全bytes一致した。

| 対象 | SHA256 |
|---|---|
| files_8.zip | `8047bc02d55d145ac9ee168fd1e8c0492b8787a701fb8b75900492deb6c6c0c3` |
| engine_phaseB_for_commit_B3_3.zip | `c99081c7eda9898b6f776162d8fdf50b5b642e3602f8ca8db5c5d378c97796c7` |
| B2_completion_inventory.json | `a334f908c7ada5af3566fe27fc356558a89be49735858ec61b2efb4853cddd10` |
| step1_engine/twelve_assets.py | `a51542bb9000119fd162e85f188dbbe9ccb356c126423602b661d2e3b437d500` |
| tests/test_b3_3_registered_assets.py | `a8855f41ded90c9301883aecd36b62a43a7b09fa09a485e6a2863a8ca2b76603` |
| Step1_PhaseB_B3_3_receipts_and_deadlines.md | `1b4e5834749910fa87268736404c516c3270225262c706ae5004c51e887ad63e` |

上記inventoryは**現受領版の識別値**であり、参考修正を採用した版の実行・freeze用値ではない。

前回承認packet（engine 0.52.0）との比較：

- 44 moduleのうち42はbyte不変。`__init__.py`の0.52.0→0.53.0と、`twelve_assets.py`末尾の登録receipt表／新intake追加が差分。
- 既存70 test fileはbyte不変。新2caseのtestを追加し、71 file・671関数定義・890展開case。
- 数値builder、B-3各計算script、notebook、規則本文、tables、spec v0.2は不変。各pinsの変更はengine_versionだけ。
- checkerは登録資産のSHA欄を追加。独立実行で**169/169 SHA一致、不整合0**。
- 全suiteのcollect-onlyは890件・rc=0・重複0。著者JUnit7本の533/154/95/20/40/36/12件（計890件）と完全に同じnode集合で、failure/error/skipped記録0。**当方で全890件を再実行した記録ではない。**
- 133 Pythonファイルと、b3配下notebookの計24 code cellを構文compileし、エラーなし。
- 過去v0.5の報告・JUnitは今回packetから外れているが、前回の原ZIPに保持されている。履歴の値を書き換えたわけではない。

## 2. 登録資産と過去の受入れ記録

今回の5登録ファイルを、前回提出されたA/Bの元ZIP memberと直接比較し、**全件bytes一致**を確認した。既存監査書の要約だけに依存して照合したのではない。

| 登録ファイル | file SHA256 | 元出力との一致 |
|---|---|---|
| b3_2_twelve_assets.json | `be6860ba2ffbdd798d8a300b2268281bbade1d2b7f33b5b0748dc550ef90d557` | 一致 |
| b3_2_twelve_geometry.csv | `c0f0bf0eb7ca3fadee70d2437443e926bed65ac5a89685b7a2c712a7dffab641` | 一致 |
| b3_2_shared_null_asset.json | `cc67686744f513e3123de2fb8353d79491d4b1deaff2b8d9ecb5f93d0f95afb4` | 一致 |
| b3_2A_final_record_7240c06f255c.json | `34cb3c8825e7b332e1e796e914f1219ad9c2bfd83b036553898b19a46b943058` | 一致 |
| b3_2B_final_record_7240c06f255c.json | `233ac3461e655b94e40458b2016f0a517362174bd694671e3eeb6673a8d81b69` | 一致 |

packet外参照の `b3_2_pools.npz` も、前回B出力ZIP memberの実bytesからSHA `451f8bc5446c03956ba5598b326532584805488326b0623b009c5e7dc530c987` と42,573,325 bytesを確認した。今回このpoolから全W2を再計算したのではない。

新規提出test2件を独立実行し2/2 PASS。登録12位置のfile/payload/registry/構造、共有nullのpayload・n_sub集合・各1000反復・m=100・K=6000・exact_pot_w2を検査する範囲で成功した。共有nullの `validate()` 単体を、既存のlive pool/W・case入力照合を代行する正式再利用入口とは扱わない。

receipt表のB-3-2 A/B scopeは概ね前回受入れと一致する。A11物理clone、case別B_final/trigger、実Drive復元を未了と分けている点は維持してよい。B-3-2の合格を取り消す新事実はない。

## 3. 登録receiptで再生成を省く方針

既に全格子の独立再生成と出力同一性の監査を受けた固定assetについて、登録file SHA・payload SHA・registry対応・member構造を照合し、過去の受入れを根拠に再利用する方針は妥当である。この方針のためにE2全格子や6000 pairのOTを毎回実行する必要はない。

実assetを読み、新しいintake→9 memberのget→snapshotで、generatorを呼ばないことを確認した。返却memberは独立copyであり、編集しても元assetは変わらない。元assetのpoint変更はgetで拒否される。普通の `asset_from_dict` は、温まったmember cacheがあってもwhole-asset receiptを自動発行しない。未知receipt、同じJSONを別の整形で保存したfile、verification表示の変更などはfile SHAで拒否される。

遅い段階の構造検査を意図的に失敗させる対照でも、部分的な `_VERIFIED` 登録は生じなかった。receiptはコードに登録された過去の検証根拠であり、暗号署名ではない。今回、監査書を毎回ネットワーク取得したり第三者署名を検証したりする新要件は課していない。

## 4. R331-A：新intakeが既存source-boundガードを呼ばない

対象：`step1_engine/twelve_assets.py` L139–156、とくにL144。

現行は新しい入口で `reg.validate()` のみを呼ぶ。一方、従来の `verify_twelve_assets` と `build_twelve_assets` は `_registry(reg)` を使い、GridRegistryの型・構造・SHAに加えsource-bound verification scopeを要求する。

正規 `load_registry` で作ったregistryを一度serializeし、正規 `registry_from_dict` で戻した。座標・payload SHAは一切変更していない。この復元のscopeは `internally_consistent; source_binding_not_verified` である。

| 処理 | 現提出版 |
|---|---|
| 既存 `_registry(internal)` | 拒否 |
| 新intakeへ同じinternal registryを渡す | **受理しreceiptを発行** |
| 戻ったasset.get | 成功 |
| 後続asset.snapshot(internal) | source-boundでないとして拒否 |

GridRegistryではない簡易objectでも、validate methodと必要な属性だけを持たせると新intakeは通る。これを型契約の別対照として確認した。

**本件は、改変された12位置や異なるregistry payloadを受け入れた実証ではない。** 登録file SHAとregistry payload SHAの一致は引き続き効いている。しかし、新入口が「source-boundを要求する」という既存のAPI契約と一致せず、成功直後の後続入口で拒否される不整合がある。

参考修正は1行：

```diff
- a = asset_from_dict(json.loads(b.decode("utf-8"))); reg.validate()
+ a = asset_from_dict(json.loads(b.decode("utf-8"))); _registry(reg)
```

既存source-bound factoryまたは `registry_from_dict_bound` からの正常入力は通る。基準を緩めず、既にある検査を新入口にも適用する修正である。参考版では上記2対照とも拒否し、新規17件＋著者新規2件は19/19 PASS。

## 5. R331-B：統合runnerでは再生成が残る

対象：`integrated_runner.py` L111–115 → `twelve_assets.py` L103–114。

`run_first_wave` は、渡されたassetが新receipt intakeを済ませていても `verify_twelve_assets` を無条件に呼ぶ。その関数は全9 memberで `verify_twelve` を実行し、`stage12.generate_twelve` に入る。今回のappendだけでrunner経由の再生成は省かれない。

実際の既存有限人工fixture（本物のregistry/ConfigurationManifest/検証済みW2Context）を構成し、実登録assetを新intakeで受け入れてからrunnerへ渡した。重い処理に入る直前だけをsentinelへ置換すると、**E2/L1.00の再生成入口へ到達**した。正式全格子をそこで実行したわけではない。

一方、同じfixtureで `evaluate_family_full` へ直接渡す経路はgenerator呼出しなしで動き、再生成したE7を使う経路とfull twelve Result・required manifests・eligible truthsが一致した。

従って、「新intake/get/snapshot/evaluatorは再生成不要」は支持できるが、「統合runnerでも反復しない」は現在のsourceでは支持できない。B-3-3の残件表へこの接続と正式使用前の期限を明記すれば、今ここで未完成production runner全体を実装する要求にはしない。

将来接続する際も、期待asset SHA、whole-asset receipt、source-bound registry、独立snapshot、使用終了時のpayload再確認を維持する。単に全検査を省略したり、未登録assetを `regenerate=False` で通したりしない。今回の参考patchはrunnerを変更しておらず、接続試験のうち一つはこの既知の限界を確認するcharacterization testである。

## 6. R331-C：Phase C checklistと工程順序を整合させる

### 6.1 本文へ追記するなら、参照JSONの本文SHAは不変ではいられない

提出報告L36は「draft4.1→v1.0、本文へ登録参照追記、rules_tables_v1.json不変」を同時に予定する。しかし、現JSONの `rules_document.name/sha256` と `rules_config.verify_binding` は本文のfile bytesを束縛する。

一時folderで現本文とJSONをコピーし、現 `verify_binding` の正常通過を確認した後、本文末尾に数値定数を変えないコメントだけを追加した。JSONを据え置くと `ValueError: rules document bytes do not match rules_document.sha256` で拒否された。**未作成のPhase C packetが既に失敗したという報告ではなく、予定する組合せが既存のbindingと両立しないことの確認**である。

(1) 現本文・JSONのbytesは保ち登録参照を別追補／凍結manifestへ置く、または (2) 最終本文の名・SHAとJSON・inventoryを更新し、数値／predicate不変のメタデータ改訂として記録する。どちらかに統一する。過去の生成recordのSHAを新しい版へ書き戻さない。

### 6.2 Phase Cに必要な原文とgridをchecklistに残す

現draft4.1の冒頭と末尾は、研究計画v0.4/v0.5原文をPhase C packetへ同梱して照合することを明記している。今回の§4構成案にはこの項目がない。第1波gridのfull precision座標・単位・lift・immutable ID・status・prior・完全SHAも、12位置assetとは別に明示する。

この小さなB-3-3 packetへ今すぐ全てを重複同梱する要求ではない。Phase Cの既存要件をchecklistから落とさず、最終段階で原文・manifest・取得先を照合するという要件である。現packet中に原文照合まで完了した証拠はない。

### 6.3 「統合runner official実行→較正先行の封印」の順を直す

提出報告L40の矢印は、未改訂のtarget-first runnerを先にofficial実行してから封印するようにも読める。現runnerはL151でtargetを評価し、その後L180でpseudoを評価するため、その意味で実行してはならない。

rules §9.4の順序を維持する：正式使用前の各機能実装・受入れ → MC資産固定 → **実観測full-grid判定値を計算しない較正先行driverで較正・監査** → calibration usable封印 → 実観測full-grid評価／Phase E解放。

新しい較正・封印driverの受入れは、実観測値を見せる前だけでなく、それを先に計算してしまう正式実行の前である。共有nullの完成とcase別B_final/triggerの受入れも区別し、後者の正式消費前にgateを満たす。

### 6.4 物理cloneの期限は、旧表との対応を明示する

旧B-2移管表には「新9点circle/clone/prior：B-3/Phase C前」、今回L30には「A11物理共分散変換・clone：Phase Dの12位置共分散生成時」とある。幾何nearest-cloneと物理共分散cloneを分ける意図は理解できるが、そのまま「期限を後ろ倒しにしていない表」とは読み切れない。

幾何・circle・priorは受入済み、物理共分散の同値性は未実施、とscopeを分解し、物理部分をDへ移すなら旧要件・移管理由・新たな使用前gateを明記した工程変更としてPhase Cで確認する。**今回その延期を既承認と認定せず、同時に今すぐ物理clone計算を追加する要求ともしていない。**

現engineを凍結する場合も、「受入れ済みの基盤sourceの固定」と、未実装機能を含む「完成したproduction engineの凍結」を区別する。

## 7. 表示上の訂正（同じ文書整理で対応）

- receipt表の「いずれもColab実行後」はB-2行には当てはまらない。B-2はsandbox実装、B-3-0/1/2はColab実行後と記す。
- B-3-1のconjunct「7/7」はstrongのdropのみ。supportの4 dropと基準2件を別に示すと既存監査記録に対応する。
- 「pins不変」「receipt追加のみ」は、科学的設定不変／engine版更新／新API追加という範囲に限定する。source bytesが全て不変ではない。
- specの歴史表§Bはそのまま残せるが、§B'も旧時点の記述であることを明記し、現在の状態はD.0とB-3-3表へ一本化する。冒頭の旧版日付・現版0.40.0等も現在値と履歴を区別する。
- Phase Cの機械可読receiptには完全なcommit・監査書名・SHAを置く。短縮SHAやB3_2Aという文字列だけを過去の承認範囲の代用にしない。現在のcode-pinned asset/file SHAは既存出力と一致している。

## 8. 独立実行・限界

| 検査 | 提出版 | 参考版 |
|---|---|---|
| 著者新規registered-assets2件 | 2/2 PASS | 下記19件に含む |
| 当方の新規契約17件 | **15 PASS／2 FAIL** | 同17＋著者2＝**19/19 PASS** |
| 既存asset回帰（選択18件、4件は明示deselect） | 18/18 PASS | 18/18 PASS |
| 実fixtureによるevaluator／runner接続2件 | 2/2 PASS | 2/2 PASS |
| 全suite | 収集890件と著者JUnitの集合照合のみ | 全体は未実行 |

2 FAILはR331-Aの同じ入口契約を二つの角度から検査したものであり、通常実行の失敗率でも、2件の科学的数値誤りでもない。参考版の3群は別々のコマンドで実行した。接続の1件とdocument-bindingの1件は現状・制約を確認する試験であり、そのPASSをrunner最適化やPhase C freezeの完成証拠に数えない。

監査環境：Python 3.13.5、NumPy 2.3.5、SciPy 1.17.0、pytest 9.0.2。試験processはBLAS/OMP 1 thread。POT、healpy、CAMBは未導入。登録Colab環境ではない。

未実施：新Colab実行、全890件の独立実行、E2/E8全格子再生成、物理CMB/共分散/sky生成、6000 pairのOT再計算、実Drive検証、正式較正、Phase C原文の新規照合。前回監査の数値確認を今回新たに再実行したとは主張しない。

## 9. 引継ぎ

参考helperの1行を検討・採用し、必要な回帰testとmetadataを最終bytesへ更新する。R331-Bの統合再利用scopeと、R331-Cの文書構成・順序・受入期限を同じpacketで整える。具体的な文案は参考ZIP内 `B3_3_document_corrections_ChatGPT.md` に置く。

**これは新しい大規模Colabサイクルではなく、受入れ済み資産を正しく引き渡すための小さな実装修正と文書整理である。** 既存A/B成果物・raw log・自己試験recordを変更しない。更新後のpacket整合性を確認してB-3-3を最終確定し、Phase Cの凍結判断は別途行う。

### 根拠ファイル

- 受領 `Step1_PhaseB_B3_3_receipts_and_deadlines.md`、spec v0.3追補、twelve_assets.py、新test。
- 保持 `Step1_PhaseB_B3_2_Colab_7240c06f255c` 監査書と、受領A/B出力ZIP。
- 同梱 `docs_B2_scope_and_B3_handoff_proposal_ChatGPT.md` §1–3、rules draft4.1冒頭／§9.4／末尾。
- evidence/comparison.json、packet_check.json、changes.diff、independent/probes.json、各pytest log/XML、final_members.json。
- tests/test_b33_receipt_review.py、test_b33_connection.py、scripts/verify_packet.py。

**最終判断：既存受入れと資産同一性は維持・確認済み。登録receipt再利用の方針を支持。新入口の1行と引渡し文書を整合化してpacketを確定する。A/Bの再実行要求なし。**
