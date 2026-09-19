# Step 1 Phase B B-2 第35 tranche監査・B-2完了範囲の判定

2026-09-16。対象：`step1_engine 0.39.0`、第35 tranche最終提出ZIP、実装報告、engine spec v0.3追補草案。

## 0. 結論

**R34-A/Bは今回の範囲で承認する。B-2のサンドボックス実装・契約試験・小規模独立referenceの受入れを完了として扱い、B-3のnotebook起草へ進んでよい。今回、新たな必須engine修正は見つからなかった。**

ただし、当初spec v0.1 §B4.2、v0.2 §Bに割り当てられていたColab mock-grid smoke、T10の実bank、T14の正式解像度・Colab条件、T19の実資産/A5 cross-checkまで完了したとは扱わない。これらの未実施・独立確認未完部分を、B-3入口／B-3へ明示移管する追補が必要である。要件は削除せず、未実施をPASSとしない。

したがって本判定は「B-2実装受入・B-3準備GO」であり、「元のB-2受入項目全完了」「ENGINE_VALID」「正式全手順較正完了」「Phase C freeze」ではない。工程の再配置には賛成するが、その変更を文書に残す。新たな科学的条件・閾値を追加する判断ではない。

今回はengine patchを作成しない。文書の訂正と引継ぎ案を `B2_scope_and_B3_handoff_proposal.md` に、SHA inventoryの補助表を `B2_inventory_audit_supplement.json` に用意した。

## 1. 実行結果と監査環境

| 実行 | 結果 |
|---|---|
| 最終提出版の全suite | 810 PASS／外部資産4 SKIP／POT未導入1 FAIL（815件、一括実行） |
| 前回tranche34の22件原本（現moduleに対して独立再実行） | 22/22 PASS |
| 今回の追加12件 | 12/12 PASS |
| 独立数値reference | 下記第4節の検査をPASS |

全suiteは提出sourceを変更せず実行した。POTを必要とするexact W2の純平行移動テストは `ModuleNotFoundError: No module named 'ot'` で停止する。隔離先へのPOT導入を試したが取得できなかった。外部資産4件はA11実npy 1件、legacy integration 3件であり、必要な資産・依存関係がこの監査環境にないためSKIPである。これらを合格・不要・削除対象とは扱わない。

Claude報告の「最終提出bytesで815/815 PASS、17.3分、外部4件を実行」は受領した実行報告として区別する。監査側の独立結果で置き換えたり、同じ実行と称したりしない。

前回22件は今回815件に含まれるため、別種類として加算しない。今回12件は全suiteとは別のpytest実行である。各実行の完全ログ・JUnit XMLを `logs/` に保存した。

環境：Python 3.13.5、NumPy 2.3.5、SciPy 1.17.0、pytest 9.0.2、OpenBLAS各1 thread。環境JSONにはbackend/path/versionを記録。正式Colab lockではない。実CMBのscan、共分散生成、正式規模のPOT null、登録2000 pseudoの全手順較正は実行していない。

## 2. 前回修正・差分・原本の確認

今回の以下3 moduleは、第34 tranche監査の最終候補とbyte一致した。

- `twelve_assets.py`
- `threshold_evaluator.py`
- `integrated_runner.py`

旧提出版からのその他のengine差分はversion更新のみである。density、orchestrator、calibration、CI、precision、W2 shared/context/manifest、twelve_eval、stage12、coordinator、official_gate、formal_runner、archive、checkpoint、performance、rules本文、spec v0.2、tables JSONは旧版とbyte一致した。

前回原本と今回同梱の22件はtest functionのASTが一致し、assertは変更されていない。ただしfixtureはpickle入力からin-process生成を既定とする方式へ変更されている。監査側では、自ら現moduleで旧fixtureと同じ入力構成を生成して一時cacheを作り、前回のテスト原本を無改変で実行した。外部から提供されたpickleを実行したものではなく、最終検査ZIPにもpickleを配布しない。

R34-Aについて、個別memberの再生成成功とasset全体のreceiptが分離されていること、内部整合だけのregistryを拒否すること、exact family/size inventory、SHA、anchorの一致、cache missでの `regenerate=False` 拒否、getの独立copyを確認した。

追加検査では、3番目のmemberの再生成だけを失敗させた。最初の2件が成功していても、cacheとasset receiptは公開されなかった。これは注入試験であり、通常の生成器が失敗したという報告ではない。

warmなmember cacheが存在しても、保存形式から復元したassetはそのままgetできず、全体intakeを要求した。snapshotは元stampを検査し、内容・SHAを保ち、呼出し元の未使用originalを変更しても消費snapshotへ影響しなかった。

R34-Bについて、common evaluatorのregistry照合、runnerの期待asset SHA、snapshot/pin、fingerprint、終了時検査を確認した。誤った期待asset SHAの入力では数値evaluatorに到達しない。前回の「消費memberを別anchorの正当な設計へ差し替える」原本試験も拒否される。

## 3. 固定asset経由の統合・保存の検査

E7の登録格子を別に列挙し、全候補の最大距離と辞書順tie-breakから追加9点を選ぶ独立referenceを実行した。3 surviving sizeすべてで全12点が一致し、最小距離は0.0158以上だった。

有限な人工入力（全3 size×12 position×matched/native、各配置evaluation 8000行、fitting 8000行、evaluation B=60、fitting B=20）で、従来の再生成経路と固定asset経路を比較した。完全な12位置Result、completion、required manifests、eligible truthのstrict JSON表現が一致した。intake後は生成関数を呼ぶと例外になるようにしても、asset経路は成功した。これはintake後の生成器呼出し0回を示し、初期生成・intake時の再生成まで0回という意味ではない。

正常な値：

- Q_matched = 3.851174112256586
- Qの95%区間 = [3.6651529978321467, 4.103276941666202]
- logD_point = -0.14867145692057981
- precision = pass
- support / strong / unsupported = False

これらは人工bankの実装検査値で、宇宙トポロジーに関する科学的結果ではない。W2は明示的なtest-only平均差統計量であり、正式POTではない。

正常runをArchiveで開き直し、run payload SHA、全source→Transition、12位置の完全Resultを確認した。さらに取得した12位置Resultを既存checkpoint writer/readerへ渡し、保存replicate・density・priorに条件付けたcore意味検証をPASSした。Archiveのbytes検証と、checkpointの意味検証は別の試験である。

全4 family・12 caseについて、targetでは非拡張/E1免除、pseudo[0]だけE7がevent-ratioで拡張し、全3 sizeの12位置入力をasset経由で評価する例も実行した。未実行分岐はなく、full_procedureの分岐flagはTrue、final_label_releasedはFalseだった。合成2 pseudoを正式2000 pseudo較正として扱わない。

任意のsize診断CIが28正常/2TECHだが親familyではCI不要という対照は、親のsupport=Trueを保った。親family自身の必要CIがTECHとなる対照では、eligible truthが全TECH、completion=Falseだった。診断失敗の除外と必要TECHの伝播を区別できている。

## 4. 独立な数値reference

| 検査 | 比較数・最大絶対差 |
|---|---|
| 12位置familyの混合分子・分母 | 両系統×5 seed、2.220446049250313e-16 |
| 同じ結果のlogQ CI端点 | 6.661338147750939e-16 |
| 配置別SciPy KDEからの密度混合 | 0.7/1/1.4の3係数、3.375077994860476e-14 |
| 頻度重みKDEとliteral行複製 | 90ケース、1.8474111129762605e-13 |
| literal cluster-bootstrap logD CI | 10ケース、2.3314683517128287e-15 |
| 不等Nのfamily Q CI | 5 seed、4.440892098500626e-16 |

確率referenceはcluster hitを文字どおり復元抽出し、配置1/36の分子・分母を別々に混合した。密度referenceは各配置へSciPy KDEを当て、その密度を混合した。提出family/CI/KDE helperをoracleとして自己比較したものではない。

この一致は実装同値性の検査であって、bootstrapの厳密な被覆率、実共分散の妥当性、正式false-support率の確認ではない。

## 5. B-2完了の判定と工程変更の明示

### 5.1 承認するもの

第35 trancheのsourceを、監査済み実装基盤として固定し、B-3 notebook起草へ進めてよい。今回R34をもう一巡のengine改訂で直す必要は見つからなかった。単体・契約・小規模数値reference・合成の統合分岐を「B-2実装受入」の範囲として承認する。

### 5.2 まだ完了していない元の受入条件

v0.1 §B4.2はB-2を「sandbox→Colab」とし、E7 1点×2系統・N=2×10^4のmock-grid engine smokeを含めている。v0.2 §BのB-2行もT10実bank、T14正式解像度E2/E8・Colab、T19 A5実資産を挙げている。v0.3草案がこれらを後段へまとめることは工程の変更であり、単に「元仕様不変・B2完了」とだけ記すことはできない。

これらをB-3冒頭のsmoke／B-3実資産受入へ移管する案に賛成する。元要件・現状の根拠・未了部分・移管先・合格記録を表にする。受入条件や科学的規則を緩める移管ではない。

### 5.3 実装待ちと実行待ち

正式12位置profile、pseudo側12位置完全Resultのarchive、較正先行・実観測値封印は「未実装」を含む。単なる本番実行待ちと一括しない。geometry metadata bindingと完全な共分散intake、legacy回帰kernelとPhase D bank生成器も別物である。

外部context/W2参照の再利用検証は、現checkpointのcore条件付き意味検証だけで完了と呼ばない。今回の追加試験はこの未実装機能を仮定してFAILへ数えていないが、完了表Aの「意味検証reader」は確認したscopeを限定して記載する。

正式global較正driverでは、全family、固定2000 pseudo、登録exact-W2資産と12位置profileを明示的に確認する。現runnerのfull_procedureは分岐範囲のflagであって正式使用条件全体のPASSではない。

ENGINE_VALID、rules v1.0 freeze、較正usableの封印、実観測label解放は、今回のB2実装受入から自動的に成立しない。正式版は全family・固定2000 pseudo・同一MC資産・位置分岐を含む同一手順・較正先行工程を別途確認する。

## 6. 完了packetの訂正事項

### 6.1 inventory

実際のmoduleは41で、提出inventoryの全SHAが実体と一致した。checkpointのMODULES一覧もこの41件と一致する。test fileは62、test function定義は607で、提出inventoryの関数数と一致した。ファイル名区分ではtest_b*が23、test_audit*が39である。815はparametrize等を展開したpytest case数であり、607と競合する数ではない。

v0.3 §Aの「自作26 file、監査27 file」は今回の実体へ修正する。B2_completion_inventory.jsonのtests欄は関数数であり、testのSHAを保存していない。「module／testのSHA inventory」と記すなら、test・fixture・参照資産のfile SHAを追加する。監査側で補助inventoryを作成した。

「全原本を無改変またはpathのみ変更」という総括も訂正する。第34 trancheはassert不変だがfixture生成が変更されている。過去には既承認のAPI追従（case result_ref→diagnostic_ref、共通evaluatorへのinjection hook）と、KDE高offsetのoracle訂正、FittingPlan fixtureへの適応もある。原本そのまま／配置適応／fixture適応／API追従／oracle訂正を分け、承認済み差分を保存する。これらを未承認なテスト緩和とみなしているわけではない。

### 6.2 性能

受領したunit costによる13行の算術はすべて一致した。ただしv0.3の共有W2「約6.9時間」は旧値である。

今回のunit：t2000=0.565002918秒、t5000=4.627904525秒。

(3000+81)×(t2000+t5000)/3600 = **4.444263286634188時間**。

KDE全matched-family CIはper_replicate約1.175947時間、opt-in batched約0.258227時間。2000 pseudoの単純全CIはbatched約516.454969時間、点・感度約7.055683時間が別行である。これは短絡率・fit再利用・12位置stage・診断・Q bootstrap・bank生成・I/Oを一括した本番所要時間ではない。

E2の185.770986秒は部分行の測定から1 passへ外挿した値であり、正式E2 assetを完走した実測ではない。生成外挿は約0.928855時間で、再intake検証や複数size分は別計上となる。

安定化batchedの新unit値はClaude側測定であり、今回監査側で再測定していない。既定backendはper_replicateのまま。12位置のper_size_diagnosticは現在も計算され、予算表は12位置stage自体を除外している。with_diagnostics=Falseによる第一波診断の省略が可能なhelperと、with_diagnostics=Trueで呼ぶ現統合runnerを区別する。

### 6.3 実行範囲の表現

「全W2検査がtest-only」は、共有null/context/統合controlの範囲へ限定する。POTを呼ぶ純平行移動unit testや性能unitは存在し、Claude側ではPOT環境で実行されたと報告されている。一方、登録規模の共有nullを正式生成し実bankへ用いる全体試験が未実施という限定は維持する。

## 7. B-3への具体的な引継ぎ

1. B-3-0で検証対象commit・module/test/fixture SHA、依存環境、外部asset期待SHAを固定し、元B-2のColab mock-grid smokeとT10/T19の実資産検査を実施する。
2. B-3 official-size controlでnegative、positive full predicate、conjunct-drop、brute-force、finite inventory、A5 cross-checkを機械用required gateで集約する。1点controlはcontrol用profileを明示し、productionの全surviving-size条件を無条件に緩和しない。
3. shared null正式生成とE2/E7/E8正式12位置assetを生成・照合・保存する。新規9点のcircle coverage／clone／priorの受入れを計画に明記する。v0.1 §B4.3とrules §10.4で要求されており、asset SHA確認だけでは代替しない。
4. 未実装項目の受入期限を明記してPhase C packetへ進む。現在のcommitは検証対象固定であり、ENGINE_VALIDや最終科学仕様のfreezeと同義ではない。

これはA10 official全体を再実行せよという要求ではない。必要なのは、今回のengineに対する未実施の受入とcontrolである。科学的な閾値・prior・KDE推定器を変更する必要は、今回の監査結果からはない。

## 8. 添付検査資料

- `logs/`: 全suite、前回22原本、今回12件、独立reference、POT導入試行。
- `diffs/`: 最終候補とのbyte一致、旧版からの変更、原本fixtureの差分、数値core不変のSHA。
- `tests/`: 今回12件と実行した前回22原本。
- `reference/`: fixture生成script、独立数値reference、正常Result、4 family分岐・TECH対照。
- `archives/`: 正常12位置runと全4 family runの実際の保存record。
- `B2_inventory_audit_supplement.json`: module/test/fixture/reference/docの補助SHA inventory。
- `B2_scope_and_B3_handoff_proposal.md`: v0.3への追記・工程移管案。

全試験は添付の合成入力で実施した。原本engineは変更せず、engine patchも含まない。数値失敗例の注入と、正常なfinite入力の試験はテストdocstring・ログで区別している。

## 出典と根拠の区別

提出報告・v0.3の記述はClaude側の主張として読み、実際に確認した事項は差分、実行ログ、計算referenceで判断した。工程の元の根拠はv0.1 §B4–B5、v0.2 §B–D、rules §9–10・§12–14である。文書のhashは補助inventoryに保存した。外部libraryの最新仕様や公開科学文献を使って規則を補完・変更したものではない。
