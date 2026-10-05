# D4C-1 v2 / engine 0.107.0：実装受入れ・E2 N=3 probe 実行前監査
2026-10-05。Claude伝達・著者保存用。対象は添付ZIPの実bytes。正式global較正・usable・Phase Eの受入れではありません。

## 0. 判定
**PASS_WITH_EXPLICIT_SCOPE__E2_N3_PROBE_ONLY_GO**。前回0.106.0のHOLD 4項目を閉鎖します。追加の必須patchはありません。指定commit/inventoryのE2・登録pseudo先頭3行・High-RAMの資源probeのみ実行GOとします。

既存bank、D-3c profiles/plans、D-2Wおよびpseudo原本の受入れは維持します。再生成・再実行は不要です。全4 familyの正式partial、正式combiner、較正結果・usable、Phase E、D4C-3は本GOに含みません。

## 1. 対象と差分
- 著者提示commit：`231d37b89271793c8cd1b93c3282d2b851f83d3e`。remote Git treeとZIPの全面比較は未実施です。
- ZIP：`phaseB_D4C1_v2_0.107.0.zip`、28,517,256 bytes、SHA256 `5ce358e12b9d4f756e561912066d9c284792038bc57ed90c4b879410c3795775`。
- inventory SHA256：`01f70420b40c556f119ae2c3c126c4ed51808bc5271429093d6cb15cc690b413`。
- ZIPのCRC、重複member、絶対/親path、symlinkを検査して別workに展開しました。
- 新旧とも2,677 files。追加0・削除0・変更45（25 JUnitほかログ・文書を含む）。現ZIPでの登録資産1,904 filesは全bytes不変です。
- engine moduleの差分はarchive.py、d4c1_partial.py、版表示。checkpoint.py、threshold_evaluator.pyと数値kernelは不変です。既存D4C-0/D-3c script/notebookも不変です。
- 6つのpinsはengine_versionだけ0.106.0→0.107.0。外側reportとZIP内の同名reportもbyte一致です。
- 直接inventory照合2,198項目一致。Python 213 filesおよび新notebook 8 code cellsを非実行compileしました。

主要fileの完全SHAはdecision JSONとresults/metadata.jsonに記録しました。

## 2. A1：trusted cacheと返却参照の分離――CLOSED
archive.pyの`_append_entry`がentryをdeepcopyし、`put`/`import_bytes`の返却refと`_entries`の結果も別のdeepcopyです。信頼側と呼出し元のnested metadataが分離されています。

前回のtest_independent_archive_contract.pyを内容変更せず使用しました。immediate/deferred×put/import_bytesの4ケースは、現版では編集refのgetを拒否し、その後の別put/flushでもdisk identityがoriginalのままでPASSでした。旧0.106.0に同じ試験を適用すると4件とも拒否不足でFAILとなります。

独立追加4対照ではnested dictだけでなくlist内dictも編集し、呼出し元のidentity・返却ref・`_entries`をそれぞれ変更しました。正しいoriginal refは解決し、編集refは拒否、再open後も原identityを保持しました。

これは公開metadataとcacheの所有関係の確認です。任意にprivate属性を変更する敵対的Pythonコードへの防御という主張ではありません。

## 3. A2：pending flush前の外部変更検出――CLOSED
archive.py:65付近のflushはpending時に`_load()`を通し、stat identityが違えば上書き前にInputContractErrorを発生させます。正常context exitもこの経路です。

前回の2 instance反例（flush/exit）を変更せず再実行し、両方PASSでした。旧0.106.0では同じ2件がFAILすることも再確認しました。

独立追加3対照（flush/context exit/flush_every）でも、B writerのindex bytesが不変、B refが解決可能であることを確認しました。Aの未index recordは再open後の同一putで再indexできました。

`flush_every`の経路は、次のputの`_find`/`_append_entry`の`_load`で通常の逐次的な変更を検出するものです。「すべてが字面どおりflushを呼ぶ」とは記述しません。確認したのは通常の非敵対的な逐次利用のconflict契約です。stat再照合と実書込みの間の敵対的raceや完全lockingの証明ではありません。

正常のimmediate/deferred index bytes一致、mergeのbyte同一性・冪等性・旧archive/registryの28回帰も通過しました。

## 4. B：published JSONの型――CLOSED
両notebookのattempt cellはJSON parseの直後にobjectを要求します。正常dictの内容検査、file SHA/bytes、attempt/source/commitment/identity束縛は維持しています。

前回の14シナリオを再実行：正常object2件は成功、rehashedなnull/空list/非空list/string/numberの10件は拒否、空dict2件も拒否しました。非dictはevidence_ok=False・最終pass=Falseです。

notebook cellは未変更で、成功子processのfixtureのpublished documentとそのfile hash/bytesだけを変更しました。Git応答と子processはTEST-ONLYです。本物の正式scriptが不正recordを生成した試験ではありません。

監査harnessは最初、旧fixtureの文字列`data = json.dumps(doc).encode()`を探して停止しました。新fixtureのserialization式へ置換位置だけを合わせて再試験しました。初回logを残しています。これは監査harnessの適応で、提出コードのFAILではありません。fixtureの正常系assertは故障注入後に意図どおり失敗するため、監査側は保存されたfinal recordを独立に検査しています。

## 5. C：live plan objectの保持――CLOSED
`d4c1_partial.py:97–118`で第1波size views・組立parent・12位置size viewsの両systemについてplan/fit_plansのidを取得します。162–166行付近で第1波共有・12位置内共有、official時の第1波/12位置共有を要求し、204–207行付近で最後のpseudo後にinventory一致を要求します。内容fingerprintとpseudo hashも維持されています。

前回の独立probeをそのまま再使用：正常E1は発行・reader成功、matched parentのfit_plans/plans deepcopy置換は拒否、bank実値変更はfingerprintで拒否しました。

追加12対照ではparent・第1波size view・12位置size view × matched/native × plans/fit_plansを、元のevaluator返却直後にdeepcopyへ置換しました。全12件が`plan objects were replaced`で停止し、family partial recordは未発行でした。これは実際の合成FamilyInputと元evaluatorを使ったsmoke試験です。requiredなper-pseudo中間evidenceが既にarchiveに残る場合まで「何も書かない」とは主張しません。

script d/d4c1_calibration.py:342–348付近にも固定plans/fplansへの`is`再照合が追加され、REQUIRED_PARTIALは24件です。notebookのAST抽出済みtrusted inventoryにも一致します。scriptの生成器small-bank end-to-endは外部資産欠落で今回SKIPだったため、このscript全体の動的再現を独立PASSとはしていません。

`plan_objects`はprocess内の検査結果summaryであり、永続的なPython object IDそのものではありません。異なるprocessを跨ぐ同一性は登録plan/input hashesとsource束縛で確認します。smoke合成fixtureは12位置内で同一だが第1波とは異なるpairを許容する一方、official非E1は同一pair必須、scriptの正式入力probeでも固定pairを照合する構成です。

## 6. 同等性と既存受入れ範囲
提出の合成5 variant（ratio trigger、W2-only trigger、12位置欠落、required parent技術FAIL、任意診断FAIL）とsynthetic target reader試験を再実行して通過しました。

canonical bytes比較は`strip_provenance`後です。除去されるのはcombiner provenanceと、それに依存する3つの自己参照fieldであり、封印ファイル全体のSHA同一という意味ではありません。partial単体をglobal sealにしないこと、固定pseudo順序と全4familyの集約契約は維持されています。

0.106.0で範囲を限定して確認したW2 position map/mixtureの丸め処理は不変です。今回のPASSからexact POT再計算・正式bankの再読込み・全環境の誤差上界を推論しません。

## 7. 実行実績
| 検査 | 結果 |
|---|---:|
| 新規提出2 file | 70 PASS / 4 SKIP（74 collect） |
| 既存archive/registry | 28 PASS |
| 前回と同じ独立archive契約 | 6 PASS |
| 独立pytest計（上記3群） | 104 PASS / 4 SKIP / failure・error 0 |
| 著者JUnit | 25 file、1,899 case、failure/error/skip 0 |
| 現source collect | 1,899、notebook絶対path4件を正規化後に多重集合一致 |
| 独立notebook文書対照 | 14 scenario |
| 前回独立plan対照 | 4 scenario |
| 追加archive対照 / plan置換対照 | 7 / 12 scenario |

未改変の提出pytestだけなら98 PASS/4 SKIPで、独立契約6件は著者suite外です。追加probe件数はpytest件数ではありません。旧0.106.0における6 FAILも現版の失敗には数えません。

4 SKIPの正確な理由はresults/test_summary.jsonに保存しました。凍結外部資産を必要とするscript end-to-endの4件です。全1,899件を独立に実行したわけではありません。

別の空workではquick再現だけを実行：独立archive6件、旧回帰28件、文書14、plan4、旧版の期待FAIL6を再現し、source2,677file不変を確認しました。新規提出74件全体と追加19対照をfresh workでも繰返したという主張ではありません。件数は重複加算しません。

監査環境はPython 3.13.5、NumPy2.3.5、SciPy1.17.0、pytest9.0.2。登録Colab環境ではありません。source pyc/pytest cacheを抑止し、故障注入は一時archive/fixtureのみで行いました。新旧各2,677 source filesと両ZIPのbytes不変を確認しました。

## 8. E2 N=3 probeのGO条件
```python
REPO_COMMIT = "231d37b89271793c8cd1b93c3282d2b851f83d3e"
EXPECTED_INVENTORY_SHA256 = "01f70420b40c556f119ae2c3c126c4ed51808bc5271429093d6cb15cc690b413"
FAMILY = "E2"
PROBE_N = 3
STAGE_LOCAL = True
```
使用notebookは`d/MirrorTopology_Step1_D4C1_partial_v0.1.ipynb`（内容v0.2）。入力rootの完全な設定はresults/execution_settings.jsonに登録ledgerから導出して保存しました。commitmentとcampaignは著者の固定値を使い、nonceはnotebook/source/log/この監査へ渡しません。

1. 新版commit/inventoryに固定し、High-RAM CPUでE2だけ、登録pseudo先頭3行だけを順序どおり消費します。formal intake・D-3c binding・12位置official gateは維持し、3行の評価はsmokeのprobeです。`PROBE_N=None`への変更を本GOに含めません。
2. source/環境/intake/plan/publicationの検査を外さず、不一致・OOM・中断はattemptとして保存します。正常probeでもD4C1_PARTIAL_PASS/partial_passはFalseです。
3. stage時間、partial時間、reader再検証時間、current/peak RSS、RAM/空きdisk、archive entry数・bytes、12位置分岐数を回収します。最後のverify区間等は累積timingsの差分も用います。
4. 3行の平均には固定費が含まれます。12位置branchを踏まなければその評価時間/peakは未測定です。E2の3行から他familyや2,000行の十分性を保証しません。科学的結果でseed/pseudo順/閾値を変えません。
5. lock、precheck/prelaunch、当該attemptのrun/final、stdout/stderr、probe partial JSON、full archive/index、実行済notebookを回収して資源監査へ提出します。正式4 partialとcombineは、その後に別途GOを判断します。

High-RAMの>40GB検査は最低条件であり、実割当て・完走保証ではありません。今回remote treeを取得していないため、実行時に指定HEAD/inventory/source SHAが一致しなければ停止してください。

## 9. 非blockingの記載整理
v2冒頭表の24 gateという記載は正しい一方、継承された§3/§4に23 gate・56 caseなど旧版の数が残っています。現行は24 REQUIRED_PARTIAL、74 new-file casesです。旧版説明として残す箇所と現版の値を次の文書更新で区別してください。これだけの再提出は不要です。

## 10. 未実施と最終範囲
未実施：正式bank NPZ intake/fingerprint再計算、実Colab/登録環境のlive gate、実bankのper-pseudo計測、2,000 pseudo正式較正、remote Git tree比較、実target評価/nonce開示、usable/label/PhaseE/noise/ENGINE_VALID。

**結論：HOLD4項目を閉鎖し、0.107.0実装を本監査範囲で受入れます。E2 N=3 probeのみGO。正式partial/combine/較正受入れは未承認です。**
