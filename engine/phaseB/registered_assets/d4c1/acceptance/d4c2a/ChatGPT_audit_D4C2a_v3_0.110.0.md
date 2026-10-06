# D4C-2a v3 / 0.110.0：環境移行・前回HOLDの再確認
2026-10-06。対象は提出ZIPの実bytes。著者提示commitのremote tree全面比較は未実施。

## 0. 判定

**環境更新の方針を条件付きで支持し、下記の修正した比較契約による、固定0.110.0・E2・先頭3行・High-RAMの計測／環境比較probeだけをGOとする。** 環境変更の数値再現性を受入れ済みとはしない。全体実装受入れ、screen、certificate、正式partial／combiner／usable／Phase EはHOLD。

最新の比較基準は `D4C2a_v2_0.109.0_audit_decision.json` である。今回の報告は0.108.0への対応を再掲しているが、0.109.0で残したC1/C2/D1は未修正である。別々の工程として扱い、certificateの修正待ちを理由に環境の比較試験まで止める必要はない。

旧bank、pseudo、D-2W、D-3cと既存probeの受入れ・原本は維持する。再生成・再実行を要求しない。旧0.108.0のGOは旧sourceへ付したものなので、環境の不一致を無視して続行する根拠にはしない。

## 1. 実体と差分

- 提出ZIP：29,802,369 bytes、SHA256 `3ae56bf1d4911e0955b312e5b44335d9a3398d5dab0b654d713e4fce7e677646`。
- 著者提示commit：`39082b641d8621989ae69a273f4e88e0c59673ba`。
- inventory：`7df1fb5948eb2c0c0d379a37afa93c0f1dbc0bba77c01c49d6be60665d9bb1ba`。
- inventoryの全2,219項目を直接再hashし一致。登録資産1,914fileは0.109.0と全bytes不変。
- 報告書・設計書・amendmentの外側添付はZIP内の同名文書とbyte一致。
- sourceは2,728file。主要変更はofficial_gate.py、d3c_ledger.py、d4c0_registry.py、版表示、6pinsの環境／履歴、試験と文書。
- **d/d4c1_calibration.pyは0.109.0とbyte同一**：`815516358ccbcb1b5d9c09fecd06583aeb6ea5a0725664bba9bf1d5378282bf6`。
- **step1_engine/infeasibility.pyもbyte同一**：`6e80dde84416365dc0173845376ce4a38fd28ccf9b3d45b4a8bbe7854c6ff67b`。
- partial notebook：`e2808bcda46b36dbbe1876381c9ca6eb98bfad76c51614bd0ac9edd21d011d81`。content v0.3、ファイル名はv0.1。

## 2. 画面にある2つの停止を区別する

最初の画面は、実環境が返したPython文字列3.13.16と登録3.13.15の不一致をpreflightが検出したもの。示された位置では科学計算へ進まず、これ自体はbank破損の証拠ではない。

2枚目はPython3.12のsite-packagesにあるNumPy内部のImportErrorである。画面だけでは、混在したモジュール／インストール状態なのか、特定の依存関係なのかは断定できない。NumPy2.1.3の公式release notesはPython3.10–3.13をsupport範囲とする。したがって「Python3.12だからNumPy2.1.3は動かない／必ず壊れる」は根拠にならない。ImportErrorを解消しても、Python3.12は本研究の旧3.13.15／新3.13.16のどちらにも一致しない。

Colab公式のpast runtime FAQでは2026.07はPython3.12.13と記載される。今回試した過去runtimeが登録環境の代替にならなかったことは説明できるが、スクリーンショットから全ての再現手段の不存在までは証明しない。「今回利用できたruntimeでは旧環境を再現できなかった」という範囲で記録する。新規実行は、新しい既定runtimeを使い、汚染した3.12 sessionで再インストールやgate迂回を繰り返さない。

外部の確認資料（2026-10-06取得）：
- Colab公式：`https://research.google.com/colaboratory/runtime-version-faq.html`
- NumPy2.1.3公式release notes：`https://numpy.org/doc/stable/release/2.1.3-notes.html`
- NumPy公式troubleshooting：`https://numpy.org/doc/stable/user/troubleshooting-importerror.html`

## 3. 0.109.0で残した3項目は、今回も開いている

### C1：信頼済みREQUIREDへの比較ではない

`d/d4c1_calibration.py:604`のrun_okは、受領recordのrequired_inventoryとgatesを相互比較する。mode別の固定REQUIRED定数への照合ではない。

前回の独立probeをそのまま新sourceへ適用した。実登録W₂／pseudo／gridを使うが、countとproducer runは監査専用の人工fixtureであり、実bankの証明ではない。

正常な人工fixtureは受理される。gate Falseを残すと拒否される一方、当該gateを両一覧から削除、G_env_lockだけの1項目化、両一覧への余剰追加は受理される。empty attempt、誤pins SHA、誤profileも受理される。したがって前回のC1は未解消。

修正は、producerのmode/schemaごとの信頼定数を選び、req自体とgate集合の完全一致・全値is Trueを要求すること。profile、source pins、attempt/lock、該当する成功flagの契約も合わせて閉じる。既存publication/readerの検査は残す。

### C2：checksumと要約内容が一致しているとは限らない

`infeasibility.py:185`のbind_screen_recordはchecksum文字列を照合するが、trigger/state/B_finalの全内容へ束縛しない。正しいchecksumのまま、E2/L1.20のB_finalを800→400、またはE2/L1.00のFalseをunknownに変更し、screen/publication/summaryを再hashしても受理された。checksum自体の不一致は拒否される。

認証済みW2Contextの実decisionから必要な要約を導出し、保存要約と型を含めて一致させる。元W₂判定やbankは変更しない。

### D1：Falseを数えないことと、証拠を捨てることは別

`infeasibility.py:215–230`のstatus変換は、support/strongが両Falseの行を消す。直接渡すと拒否できる「同familyのscreen unknown_or_technicalとevaluated False」の矛盾が、実際のadmission順では見えなくなる。

今回実行した未改変試験が生成した合成E2 partial/archiveを既存readerで認証した。4行とも両Falseの正常recordから返るrowsは空だった。この後に同family同rowの人工screenを渡すと受理された。実bankの矛盾が見つかったという意味ではなく、反対証拠を失うcontractの再現である。

全statusを同family/row/levelの整合検査まで保持し、その後blockingを計数する。別familyのFalseは両立し、False自体は件数へ加えない。

**A/Bが以前閉鎖された判断は維持する。今回のC1/C2/D1は新しい要求ではなく、直前の判断に残した要求である。** 正式screenを先に作ると修正後certificateの同一source条件と衝突するため、一連のscreen→certificateは修正版に揃えてから行う。

## 4. 新旧環境を分離する方針と、実際に確認した範囲

現提出の6pinsでは、currentは3.13.16、historyは3.13.15で、他5版は不変だった。旧registered-assetsの原本bytesは不変。

新sourceの実APIを使い、D3cProfilesの登録intake、D-2Wの正式context復元（9decision）、pseudoの原本NPZ読込みを実行し成功した。旧環境を記録した原本を、新環境で生成したことに書き換えず消費できる経路である。これらは新Python3.13.16での数値再計算ではない。

小規模FamilyInputに注入した環境snapshotを使う対照では、3.13.16だけがversion mismatchなしとなり、3.13.15/14はlive gateのversion検査で不一致になった。注入snapshotはTEST-ONLYであり、syntheticのbankサイズやBLAS要件も違うため、gate全体はPASSしていない。Colabのlive gateを再現したという意味ではない。

### 履歴欄についての限定・改善

registered_environments(pins)はhistoryがmissing/nullのとき、検査を飛ばしてengine定数の履歴を採用する。空list／誤版は拒否するが、missing/nullでは実コピーtreeから作り直したTwelveContextのD3c intakeも成功した。amendmentラベルも、比較対象は6つの版だけなので、ラベルのみの変更は通る。

これは任意の旧環境の認証や、新runを3.13.15で実行する迂回を示すものではない。engine whitelistと原本SHA認証は維持される。**今回の固定packetは実際に正しいhistoryを持ち、inventoryに束縛されるため、限定probeはこの点では止めない。** ただし汎用APIの「pins履歴と完全一致」の説明には不足がある。次版ではpins指定時にhistoryを必須にしてmissing/null拒否を追加し、履歴ラベルの扱いを明記するのが適切である。

## 5. amendmentの「旧partial payload SHA一致」は受入れ条件にできない

提案§4.1の全体SHA一致は、そのまま採用しない。旧record自身を読むと、payloadにはengine_version、binding.modules/source_binding、gate.diagnostics.env、登録expected versionsが含まれている。

旧payload `057ae75355fd7a716aba9d52d5a520275c9c6fd3b57162a4e7d389e327223878` は元関数で再計算して一致した。そのコピーで、数値・入力identity・全per-row recordを変えず、top-level engineだけ0.110.0へ変更するとpayloadは `08a9d66e705f408248aeac91c009f4e48c7f90c52225cac845d94645b1d7bdfa`、記録されたPythonだけ3.13.16へ変更すると `bb805c7918a487bde1fddc865affd01c8d55a06804f7b5e185eb193f11b72a9f` となった。

これは**metadataだけを変えたin-memory対照**で、新環境での数値実行ではない。しかし新しい由来を正しく記録する限り全体bytesが変わるため、全体SHAの不一致を数値再現性の失敗と同一視できない。旧値に書き換えて合わせる処理はしない。

### 本監査で採る比較契約（新結果を見る前に固定）

1. 旧・新の原本、全体payload/file SHA、source lockをそれぞれ保持・検証する。新recordは新sourceに対してcurrent_source_binding=Trueでreader成功を要求する。
2. **family_result 3、three_position_result 9、pseudo_family_plan transition 3の計15fileは、global row/size/typed identityで対応させ、canonical bytes/content SHAの完全一致を要求する。** 余剰・欠落・重複を認めない。
3. 旧archiveの4個目のtransitionはpartial全体そのもの。これはper-rowではなく、新engine・gate・source bindingを含むため全体SHA一致対象から分ける。registry自体は引続き同一であることを確認する。
4. partialの全threshold/順序、fingerprints、registered input identities、per-pseudo status/diagnostics/manifests、campaign、commitment、plan object検査summary、scope等は一致させる。具体的なfield名と15fileの固定SHAは別紙JSONに保存した。
5. 新engine/modulesと新env等、変更を認めるprovenanceは、単に消すのでなく新commit/inventory/pins/live gateへ検証する。科学量や入力まで無差別に除外するgeneric stripは使わない。
6. 数値・status・input/plan等の不一致なら原本を保持し停止して差分を報告する。結果を見て許容幅を選んだり、同じSHAになるまで引き直したりしない。

この契約は原提案の全体SHA条件を置き換える。実装fileを変更する必要はない。比較は3行の実測範囲であり、未発火の12位置・N4・KDE-CIや全2000行の数値不変を保証しない。

## 6. 限定probeの固定条件

```python
REPO_COMMIT = "39082b641d8621989ae69a273f4e88e0c59673ba"
EXPECTED_INVENTORY_SHA256 = "7df1fb5948eb2c0c0d379a37afa93c0f1dbc0bba77c01c49d6be60665d9bb1ba"
FAMILY = "E2"
PROBE_N = 3
ROW_RANGE = None
INSTRUMENT = True
STAGE_LOCAL = True
```

notebookは `d/MirrorTopology_Step1_D4C1_partial_v0.1.ipynb`（内容v0.3）。旧GOと同じ登録入力root・commitment/campaignを使い、nonceは渡さない。完全設定はevidence内の `results/execution_settings.json`。

新しい既定High-RAM runtimeで、実Python3.13.16、他5版とBLAS・source・intake・planの全検査を満たすこと。skip/偽装は不可。容量条件は完走保証ではない。precheck/prelaunchの2観測、lock、run/final、全24gate、official twelve gate live_collected、profile JSON+receipt、cProfile、archive/index、stdout/stderr、実行済notebookを回収する。probeなので正式PASS=Falseを維持する。source/inventoryを変えた版への自動GOはない。

旧15での環境不一致と3.12のImportErrorは、失敗したpreflightの履歴として保存する。新attemptを過去の失敗と混ぜず、旧probeやpseudoを上書き・再生成しない。

## 7. 試験実績と限定

| 項目 | 今回の実績 |
|---|---:|
| 新D4C2aの未改変試験 | 21 PASS / 7 SKIP |
| D4C0登録＋D3c登録の未改変回帰（full-plan consumerを除外） | 82 PASS / 0 SKIP |
| 合計 | **103 PASS / 7 SKIP / failure・error 0** |
| 意図的除外 | D3c full-plan consumer 1件 |
| 著者JUnit | 29file / 1927case / failure・error・skip 0 |
| 現source collect | 1927件、表記正規化後JUnitと多重集合一致 |
| 非実行compile | Python218file / notebook12cell |
| inventory | 2219 SHA一致 |
| 旧certificate境界 | 18シナリオ（人工baseline1、拒否9、不適切な受理8） |
| 独立環境対照 | 19項目（正常・方針境界・history欠落対照を区別） |
| whole-hash metadata対照 | 2件 |

著者suite全1927件を独立実行したわけではない。7SKIPは外部資産依存のscript試験。新sourceで旧probeの科学的計算を行ったわけでもない。source2,728file、前版2,727file、登録資産1,914fileは不変。

freshなcopyでも代数境界とhash比較の2scriptを再実行し一致した。選択pytest全体とcertificate18件をfreshでも再実行したとはしない。

環境監査harnessは最初、VerifiedW2Decisionに存在しないas_dictを呼び、復元後の要約作成でエラーになった。公開属性の明示取得へ直し、一連の対照を再実行して成功した。初回logも保持し、提出コードのFAILには数えていない。

未実施：Python3.13.16/Colabの実runtime、physical bankのintake、bootstrap再構築、exact POT、実screen2000行、実データによるcertificate、正式較正、target解放、remote tree全面比較。TEST-ONLY証拠から発行した人工certificateを、実bankの成功不能証明として使わない。

## 8. 次の引渡し

Claudeは0.109.0のC1/C2/D1を基準に修正する。環境amendment文書は、全体SHA一致から上記の科学的内容とprovenanceの分離へ訂正する。history欄の必須性と、NumPy 2.1.3とPython3.12の非互換／旧runtime不存在という強い記述も整理する。

**今回実行してよいのは固定0.110.0の環境比較・計測probeだけ。screen/certificateのGOや、環境移行の数値的完了認定はまだ発行しない。** 比較probeの結果を原本のまま確認し、certificate修正版は別途監査する。
