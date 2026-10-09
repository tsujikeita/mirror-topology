# D4C-2a v5 / engine 0.112.0 — bridge比較器v2の実装受入れ監査
2026-10-07。Claude引渡し・著者保存用。

## 0. 判定
**bridge比較script v2を、固定0.110.0のE2・先頭3行probeを前回の原本specと比較する用途で、実装受入れPASSとする。R-D4BRIDGE-A／B／Cを閉鎖する。追加の必須patchはない。**
これは実装の受入れであり、実際のPython3.13.16における数値bridgeの受入れではない。実bridge原本は今回未提出。screen／certificate、正式partial／combiner／global較正、usable、Phase EのGOは発行しない。ユーザーの最新依頼も、実bridgeを別途提出し、その後に実行GOを求める順序である。
0.110.0に付した固定probeのGOと、前回受け入れたC1／C2／D1・history guard・環境amendmentの方針は維持する。比較器の監査を理由とするprobeの再実行、bank／pseudo／D-2W／D-3cの再生成・再実行は不要。

## 1. 対象bytesと差分
- 著者提示commit：`ba51e5951ebb8c16c7106247408c912d86944675`。remote treeとの全面比較は未実施。
- ZIP：`phaseB_D4C2a_v5_0.112.0.zip`、31,212,377 bytes、SHA256 `0f52a66f53656fd0e686d2ff9a095724e3f834bcd1db26259509005ca323b62c`。
- inventory：`aa2c11cc01df09fc9cd130a2c0b9aa5af75d1b2acc27f47aef3d5d91d0bb2b77`。
- 比較器：`ca545b61c8b867ec2c36210a77012b2a93b125a2cd04d193e4b8e68ce93fc605`。
- source：2,749 files、inventory SHA項目2,237件すべて一致。Python220 files・対象notebook12 code cellsを非実行compile。
- 外側の報告書・設計v0.4・amendment v0.3は内側同名文書とbyte一致。
- 前版0.111.0との差分で、engine moduleの変更は`__init__.py`の版表示だけ。`d/d4c1_calibration.py`、`infeasibility.py`、`profiling.py`、`official_gate.py`、既存notebookは不変。6 pinsはengine_versionのみ変更。
- 旧registered_assets 1,923 filesのうち1,922はbyte不変。変更1件は監査文書追加に伴う`registered_assets/d4c1/acceptance/d4c2a/file_map.json`。前回監査原本3件が追加され、現在1,926 files。科学的な登録原本の変更はない。追加された前回MD／JSON／証拠ZIPは、この会話の元fileとbyte一致。

## 2. A：producer provenance
比較器がimportするengine／readerは`--phaseb`で指定したproducer tree。driverの`REQUIRED_PARTIAL`をASTで抽出し、24の名前・順序、gate key集合、全値`is True`を要求する。
sourceのinventory／script／pins／engineとtop-level metadataを実file・inventoryへ照合し、run directory・attempt、lock bytes、final、precheck／prelaunch、live twelve gate、publicationを検査する。比較器そのものの0.112.0を生成版0.110.0へ取り違えない。
独立対照では、runを変更した後にfinalのrecord_sha256とgatesも更新した。これにより、単なる古いouter hashの検出ではなく、狙ったsemantic guardが拒否することを確認した。gate改名、順序逆転、整数1、source pins不一致、attempt不一致、再接続した別commit lock、失敗final、dirty precheck、別assetのprelaunch、failed／injected twelve gateをすべて拒否。
`--expected-commit`は実装上任意引数だが、本受入れ用途では必ず固定40hexを明示する。加えて、使うproducer treeは元ZIP／既知inventoryへ独立照合してから渡す。任意の自己整合したtreeが、外部Git commitと同一だと本scriptだけで証明されるわけではない。

## 3. B：typed identity
script自身の再帰的な`teq`でbool／int／floatを区別する。両archiveでfamily_result・planをglobal row、position recordをそのrowのplanが名指すsize別SHAへ対応づけ、15件のidentity／kind／bytes／SHAを固定specへ照合する。registryと集約partialの2件を含めて17件・unique SHA集合を確認する。
独立対照では、科学的recordのbytesを一切変えず、indexのpseudo_index 0をfalseまたは0.0に変更。own readerだけは通るが、比較器はper_row_records_exact_in_both_probesで拒否した。したがって追加した型検査そのものの有効性が確認できる。
全partialのSHA一致は要求しない。科学的15recordと指定fieldは一致、source／環境／engineの新しい由来は別に正しく検証する契約を維持。

## 4. C：profile本文とエラーreport
profile本文のschema、producer engine／Python、wrappers／cprofile、missing_targets、producer TARGETS、3segment・integer index0..2、segment wallとtotal／outside、target call会計、segment-target calls3、cProfile表の存在を検査し、run summary／receiptへ結び付ける。
独立対照ではprofileを改変しfile SHA／bytes、run、finalのrecord SHAを更新したうえで、missing target、cprofile=False、target欠落、boolのsegment index、calls不整合、profile欠落を拒否。良好なrun summaryだけを残す方法でも通らない。
追加のformat対照では、0.110.0の本物のProfiler.reportを、TEST-ONLYの軽いsegment関数3回に対して実行。22target中20targetが未呼出しでも正常に比較器を通ることを確認した。実監査Pythonは3.13.5で、fixtureのprofile Python欄だけを登録値へ設定した。この対照はschemaの互換性検査であり、科学計算・Colab・Python3.13.16の性能測定ではない。
null partialはdocuments_are_objects、lock欠落はunexpected_errorとしてrc1とreport JSONが残る。保存不能やOS killまでreport発行を保証する主張ではない。

## 5. 独立実行
| 群 | 結果 |
|---|---|
| 提出bridge試験 | 25 PASS（正常1・parameterized改変24。正常test内にusage等の追加対照あり） |
| D4C-2a module／script | 22 PASS／7 SKIP |
| D4C-0登録・D-3c登録 | 82 PASS／SKIPなし |
| 未改変pytest合計 | **129 PASS／7 SKIP／failure・error 0** |
| 新比較器＋未改変0.110＋元specの独立fixture | 正常1件36checkすべてTrue、追加改変21件すべてrc1＋report |
| producer Profilerのformat対照 | rc0、36check成功（TEST-ONLY） |
| 別空work・ZIP入力での再照合 | rc0、36check成功・producer source不変 |

7 SKIPは外部資産が必要なscript試験で、実screen-run→notebookの3条件も含む。代替probeの成功でSKIPをPASSへ置き換えない。D-3cの正式規模plan再構築consumer1件は明示的に除外。
著者JUnit30本は1,953caseでfailure／error／skipなし。現在のpytest collect1,953件と多重集合一致。JUnitのbare module名をtests/file.pyへ変換し、6つのnotebook絶対path付きparameterのcheckout rootを正規化した。**全1,953件をこちらで実行したわけではない。**
独立cross-tree fixtureは、既存baseline科学recordを再利用し、producer metadataだけを合成したもの。正常36checkは数値bridgeの実証ではない。追加対照をpytest件数へ加算しない。freshでは正常ZIP comparisonのみを繰り返し、全pytest再実行とはしない。

## 6. 比較の実施条件
比較器：0.112.0の本ZIP内script、別の場所から実行。
producer：**0.110.0**、commit `39082b641d8621989ae69a273f4e88e0c59673ba`、inventory `7df1fb5948eb2c0c0d379a37afa93c0f1dbc0bba77c01c49d6be60665d9bb1ba`。
spec：この会話で固定済みのJSON、SHA `a9cb9ab9b622cb0d929006eac01a957003a5eeffef990a40de8c6338a0981373`。
baseline：元ZIP、SHA `538f5e07f3c4fae84803d17783ff09a03fef5270cd04b600376e2af891644766`。
`--expected-commit`を明示、fresh CLI processを使用、reportは入力／source tree外の新規pathに保存する。原本を上書きしない。
使用例はcode/use_comparator.shを参照。これは既存データのread-only比較であり、新しい科学計算の実行GOではない。

## 7. 次の提出と境界
実際の0.110.0 probeのraw結果ZIP、実行済notebook、lock／final／run、profile、その原本を本比較器で読んだreport JSONを一組として提出する。rc0も単独では監査受入れに置き換わらず、rawと照合する。rc1なら差分を保存し停止、再試行での一致探索や事後的許容幅導入はしない。
数値bridgeの結果を受け入れた後、screen E2／E7／E8とcertificateを同じ修正版sourceへ固定して実行GOを別途判断する。今回そこまでのGOは求められておらず、発行しない。
数値再現の射程は同じ先頭3行に限り、未発火のN4、KDE-CI、12位置数値経路、全2,000行の同等性を証明したことにはならない。

## 8. 保全と限定
現在source2,749、前版2,744、producer2,728ファイルが監査前後で全bytes不変。外側原本と登録された監査原本・specの一致も確認。
監査環境はresults/environment.json。正式bankの読込み、巨大plan再構築、exact POT、実際の新Python bridge、実screen/certificate、全family較正、target評価、remote Git tree比較は未実施。
初回のmetadata harnessはtest/fixture basenameをsource rootから解決したため、監査側のpath prefixをtests/へ訂正した。pytest名のcheckout prefixも明示的に正規化した。提出物の不一致としては数えない。最終実検査は2,237件一致・collect多重集合一致。
