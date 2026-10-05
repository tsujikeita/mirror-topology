# D4C-2 E2・N=3 probe：実行証拠の受入れと、資源・unknown問題への判断
2026-10-05。対象は commit 231d37b89271793c8cd1b93c3282d2b851f83d3e / engine 0.107.0。

## 0. 判定
**probeの実行証拠は、以下の限定付きで受け入れる。正式4 family partial／combinerへのGOは出さない（今回も依頼対象外）。既存の実装・bank・D3c・pseudo・D2Wの受入れは維持する。**

報告書のA（内訳計測後の高速化・pseudo範囲分割）は基本方針を支持する。計測版・分割版の設計、実装、小規模同等性試験へ進んでよいが、新しいColab実行は計測版の固定source／inventory・入力／出力契約を確認してからとする。

Bの「ほぼ全件unknownでusable=Falseが構造的に決まる」は、深刻な実現可能性上の懸念ではあるが、今回の3件から確定した結果ではない。既存コードはevent-ratioで全surviving sizeを12位置化し、旧position-unresolvedを解消できる。W2のunknownは恒久的なvetoではない。

**直ちにB_max延長・W2再実行・E1だけへのscope縮小へ進むことは推奨しない。** 固定規則のままでの計測・分割と併せ、§5の「成功不能証明」の設計を先に検討する。科学的変更を選ぶ場合は別amendmentであり、原本・旧判断を保持する。

## 1. 実際の検査と限定
比較基準は前回GO JSONと、そのSHAで固定された0.107.0 ZIPである。今回のrunを新たに生成したものではない。

- source ZIP: `5ce358e12b9d4f756e561912066d9c284792038bc57ed90c4b879410c3795775`
- source inventory: `01f70420b40c556f119ae2c3c126c4ed51808bc5271429093d6cb15cc690b413`
- probe ZIP: `538f5e07f3c4fae84803d17783ff09a03fef5270cd04b600376e2af891644766`、515,915 bytes
- executed notebook: `72af76c8b161b09eae3815ede13da9416ab5c71a16781e3784fc5c70b4707cd8`、45,257 bytes
- attempt: `20261005T100239Z_386d63207c`
- partial payload: `057ae75355fd7a716aba9d52d5a520275c9c6fd3b57162a4e7d389e327223878`
- 公開probe JSONのfile SHA: `474bf121b1797b912a11f628839c9ae230639d928cf1e7d164e8a27cebde4149`
- archive内partialのfile SHA: `77252f400aa4a6be14ded506fddf3a8bf656a2f85dddf092be3535bb87187a63`。公開文書には自己参照が加わるので上記と区別する。

独立照合173項目成功、inventory 2,198 SHA一致。lock・run・final・attempt・publication・notebookを相互に照合した。記録されたprecheck／prelaunchのHEADとclean、sourceと登録file SHAは固定sourceに一致する。実際に記録された6版とBLAS pool情報も登録条件に合う。24 REQUIREDは承認scriptのASTから取得した一覧に厳密一致して全True。rc=0、例外・failures・fallbackなし、probe=True、n=3、正式PASS=Falseである。

12位置gateはrunに保存されたofficial/passed/live_collectedのsummaryを照合した。実bankでのgateをこちらで再実行したものではなく、保存されていない詳細な全checkを独立確認したとはしない。第1波partialのgateはsmokeであり、この区別を維持する。

72供給のmanifestとcluster数は、受入れ済みD3c E2原本の供給に一致。記録された12位置fingerprintは当該原本のfingerprintに一致。正式bank配列本体を今回読み直し、fingerprintを再計算した検査ではない。NPZで固定されたpseudoの先頭3行は、実際のpartial threshold列に完全一致する。

実行済notebookは編集用cell以外のsourceが承認版と完全一致。編集用cellも元と同じ変数へのliteral assignmentだけであり、commit／inventory／family／N／入力root／stagingは前回GOに一致。commitmentとcampaignはlockに一致。code cellのexecution countは1–4、error outputなし。

archiveは17 entry・2,595,293 bytes、index 5,650 bytes、合計2,600,943 bytes。全entryを実際のArchive readerで読み、SHA・identityを検査した。`verify_partial_record(..., current_source_binding=True)`は認証済み登録hashを渡して成功。メモリ上で改変してpayload SHAを更新した6対照（unknown→False、threshold、行欠落、context、plan summary、末尾fingerprint）を全て拒否した。

W2のregistered loaderを実行し、保存position記録9件の判定を再導出して一致した。物理bank、exact POT、bootstrap全plan、Colab環境、real targetは再実行していない。全1,899件のpytestも今回再実行していない。独立state controlsの件数をpytest件数に混ぜない。

元source2,677 fileとrun原本25 fileのbytes不変を確認。別の空workでも3監査scriptが終了コード0で再現し、原本不変を確認した。

## 2. 報告書の記述訂正
### 実測・外挿
script 1,548.036秒、attempt 2,397.4秒、staging 845.9秒、partial区間約941.7秒、表示平均313.886秒/pseudo、peak RSS 16,030.7 MB。3件とも12位置評価なし、N拡張なし、logD CIは未計算。資源probeとして有用である。

約174時間は `313.886*2000/3600` の単純外挿であり、正式runの確定予測ではない。partial区間にもparent組立て・fingerprint・gate・保存などの固定費があり、他のpseudoではN4、KDE CI、12位置分岐が発生し得る。したがってこの数字は上限でも下限でもない。12位置入力をRAMへ置いたことと、12位置較正を評価したことを区別する。archive約1.7GBの外挿も現在の非拡張経路だけを基にしている。

Colab公式FAQ（2026-10-05確認、https://research.google.com/colaboratory/faq.html）は通常最大12時間、十分なcompute unitsがあるPro+で最大24時間と説明するが、runtimeや資源は可変で保証ではない。一般のHigh-RAMを24時間保証としない。

### 科学的数量の転記
報告のQ_matched「約1.004–1.009」は原本と不一致。正しくは以下である。

| pseudo index | Q_matched | logD point | family Q rel_halfwidth | bandwidth sensitivity pass |
|---|---:|---:|---:|---|
| 0 | 1.0120085663800016 | -0.03133162894140007 | 0.0010406167403652828 | True |
| 1 | 1.0091025254182917 | -0.027138603247285786 | 0.0009483806671959942 | True |
| 2 | 0.9999809485249505 | -0.00009683230512180785 | 0.00048632894054919973 | False |

3件目は帯域幅変更でlogDの符号が変わりsensitivity=Falseである。これはrecordの非技術的な監査結果であり、process FAILやW2 unknownの原因へ読み替えない。core truthsがFalse、eligible truthsがunknownという結論は不変。原本は変更せず、報告書だけを訂正する。

## 3. unknownの位置づけ：重大な懸念だが恒久的vetoではない
`threshold_evaluator.evaluate_family_full`は、各sizeのW2とevent-ratioを組み合わせ、いずれかのsizeがposition-sensitiveなら全surviving sizeを12位置へ進める。`coordinator.family_completion`は、元がprovisional_unresolvedだったsizeもfamily ruleで拡張して完了を検査する。`derive_outcome`は12位置の完全評価とlocal completionが成功すればそのtruthを使用する。

実登録W2 context・実登録12位置manifestを使うstate-contract試験で、L1.20のW2 unknownを保持したまま、L1.00の**合成**確率を[0.2,0.6,0.2]としてratioを発火させた。元関数は3size全ての拡張を要求し、local-completion fixtureが通ればeligible False／True／unknownのそれぞれを返した。required technical failはTECHのまま。この試験は分岐の反例であり、実bankでこの確率や12位置truthが生じたと主張するものではない。

従って「W2 unknownがあるから全pseudoが必ずunknown」は成立しない。しかし、実際のratioが全sizeで発火しないpseudoはprovisionalになるため、使用可能性への懸念は深刻である。未評価1,997行とE7／E8の分布を今回の3件から確定しない。

core Falseをeligible Falseとして流用する修正は認めない。旧3位置の支持がなかったことは、必要な位置状態を解決したことではない。E1のTrueもglobalのc+uを減らさない。unknownがTrueへ移るだけで、最悪側で1件と数えることは同じである。unknownの多さによる不合格は、実際の誤支持率が高いことや宇宙トポロジーを否定したことと同義ではない。

## 4. B_maxだけを延ばしても今回の4件は解消しない
4件はB_final=800/600/400/400で**停止済み**であり、後段validationがmixed above/below indicatorsとしてunknownを返している。B_max到達・停止未達ではない。

保存observedとnullを用いて元の`w2_stop`を呼び直し、さらに監査process内だけでB_levelsの上限を2,000へ拡張し、旧1,000値の後へ極端に大きい有限値を追加するcounterfactualを試した。9caseすべてで停止recordが同一であった。旧prefixと最初の停止規則が同じなら、既に停止した後のtailは参照されないためである。公式assetの変更・再登録を行った試験ではない。

B増加、観測側subsample増加、seed間合意条件変更、unknown→12位置fallbackは別の変更である。後者を検討するなら、W2の元unknownを改ざんせず、unknown時のactionを一律に12位置へ進める**新しい方針**として登録する。既存12位置bankは再利用候補だが、新branchの費用と全手順の較正が必要で、統計的に自動で安全になるとはしない。

この段階ではW2の結果と3pseudoの結果を既に見ている。target未解放でも「結果を一切見ない変更」ではない。amendmentに閲覧済み情報・動機・旧新semantics・資産再利用・独立検証列の要否・新campaignを記録する。現行原本を破棄・上書きしたり、seedを引き直して通過を狙ったりしない。

## 5. 追加提案：固定分母の成功不能証明（未実装・設計GOのみ）
全2,000件を最後まで計算するか、直ちに規則変更するか、の二択にしなくてよい。

あるpseudo行について、少なくとも1 familyの最終eligibleがTrueまたはunknownと確定し、残りfamilyの非技術的結果がどうなってもglobalがFalseにはならないなら、その行はglobalのc+uに必ず1を加える。他familyが技術FAILなら正式なusable自体が成立しない。

固定n=2,000の登録Wilson式を使うと、supportは81行、strongは12行で、残りを全部Falseとする最も有利な補完でも上端が閾値を超える。

| 水準 | 閾値 | 最初のblocking数 | 直前のWilson上端 | blocking数のWilson上端 |
|---|---:|---:|---:|---:|
| support | .05 | 81 | .04950693664126962（80件） | .050056823219945756 |
| strong | .01 | 12 | .009822062795201926（11件） | .010458448381508351 |

今回の3件を同一手続のblocking証拠として利用できると仮定しても、最も有利な補完の上端は .004401032589829253で、どちらの不能証明にも達しない。probe3件を正式partialへ昇格させる判断ではない。

### 重いbootstrap／KDEを回さずにblocking行を証明できる十分条件
次は本監査の追加設計提案であり、現行runnerに実装済みではない。

familyにW2 unknownが少なくとも1sizeあり、W2 Trueがないとする。pseudo p、size s、position j、Nの選択b∈{N0,Nmax}に対する実bankの正確なhit率を P(s,j,b;p) とする。全surviving sizeで全率が正で、

    max_{j,b} P(s,j,b;p) <= 2 * min_{j,b} P(s,j,b;p)

なら、positionごとにN0/Nmaxの選択が異なってもevent-ratio>2は発生しない。precision通過ならratio False、精度未達ならunknown、技術異常ならTECHであり、zero-hit triggerもない。どのsizeも12位置を発火できず、既存W2 unknownを含むfamilyはeligible unknownまたはTECHになる。この性質から当該行を成功不能証明に利用できる。

**同じNを選ぶ場合だけを検査するのでは不足**する。max/minは全position・両prefixの包絡で取る。入力hash・正確な閾値比較・Nmaxの最大長bank・case集合・W2 pinsへ束縛し、元実装と同じfloat64のH/Nと閾値比較を再現し、境界は外向きの保守的判定か実際のfloat値の厳密比較で扱う。整数比だけの判定と元float条件の食違いを放置しない。これは十分条件にすぎず、失敗した行をFalseや非blockingと決めない。必要なら通常評価へ戻す。

合成count fixtureに対する2^9=512通りの混合N選択で、元event_ratio_triggerが全てFalseになることを確認した。blockingのTrue/unknownと他3familyの4値の組合せ128通りでglobalがFalseにならないことも確認した。実bankの全2,000行のscreenは未実施であり、81行／12行を得られるとは断定しない。

### 出力・停止のscope
成功不能証明は「正式calibrationを完了してusable=Falseを得たrecord」とは別のkind/schemaとする。全n=2,000という分母を変えず、未評価行を仮定上全Falseに補完した**代数的な不能証明**である。観測済みm行を分母にしてWilsonを再計算し、通るまで追加する方式ではない。未評価行のc/u/rate、全件技術成功、元partialの完了を捏造しない。未評価のrequired技術FAILも別途あり得る。

正式reader・combinerがこの証明をfull calibration sealとして受け付けないこと、false/unknown/TECHの混同や重複行を拒否することを設計・試験する。この設計だけのGOであり、未提出のscreen scriptを実行するGOではない。

## 6. A：計測・高速化・再開の実装条件
まず同じE2・同じ先頭1–3行・同じbankとplanに対する計測版を起草する。parent組立て、fingerprint、plan validation、hit count/table、Q再抽出とCI、N選択とfinal再評価、per-size診断、KDE point/CI/sensitivity、12位置、archive/readerを区別し、呼出し回数・self/cumulative timeを記録する。profiling overheadを本番速度と混ぜない。

source上の具体的な再利用候補は、`_family_Q`が5seedのループ内で同じc/threshold/roleの`hit_tables`を繰り返し呼ぶ部分、N0選択とN0の最終評価、parentとper-size診断間の同じ構成点の再抽出、family/plan検査・hashである。今回はそれぞれの正式実測内訳はなく、支配項とは断定しない。3行ともlogD CIを実行していないので、KDE bootstrap高速化だけを先に採用してこの941.7秒が解消すると想定しない。

cache keyに実配列identity・閾値bit pattern・config/system/role・prefix・UID/plan/seed・dtype/sourceを含め、認証snapshotと返却objectを分離し、旧版との出力・状態・境界・拒否の同等性を確認する。閾値を丸めた近似reuse、bootstrap削減、任意診断の無断削除、gate省略で速度を得ない。

高速化と別に、deterministicなpseudo-range sub-partial／family combinerを設計する。global row indexと全列SHA／slice SHA、重複・欠落・range overlap、source／campaign／plan／W2一致、数値的failureと中断の区別、durable checkpointと再開後の再検証を要求する。固定1..2000の集合を変えず、chunk順で乱数やsummaryが変わらないことを検証する。部分結果はglobalまたはfamily完了を名乗らない。runtime消失に備えた保存先はbank/sourceと分離する。

## 7. (a)(b)(c)とCへの回答
- (a) 原登録を基準として維持する方針は支持。ただし現状の174時間外挿のまま全件を投入する決定はせず、計測・再開設計と不能証明候補を先に評価する。全件計算前に正式usable=Falseとは報告しない。
- (b) B_maxだけの延長は今回の原因に対応しない。新しいfallback等のamendmentは別途検討可。原本・閲覧済み結果の開示、pseudo/targetに同じ規則、新たな較正／独立確認の方針を必須にする。
- (c) E1だけは診断・別scopeとして扱うことは可能だが、元の4-family global較正の代用にならない。E2/E7/E8を都合よくFalseとして取り除かない。現時点でE1の正式実行GOは追加しない。
- C: probe ZIP・実行済notebook・報告書・本判断とfile mapを、例えば`registered_assets/d4c1/probes/<attempt>/`へ原本byteのまま保存することを勧める。これはprobe evidenceで、正式入力・calibration acceptance・usable sealから区別する。repo外で固定保管する場合も同じhash mapを保持する。nonceは追加しない。

**推奨順序：原本固定・報告訂正 → 計測版と成功不能screenの仕様 → 小規模同等性／拒否試験と実行前監査 → 実bankでの限定計測・screen → 原登録の完走、不能証明での終了、または明示amendmentの選択。** 研究全体や過去の受入れを差し戻す判断ではないが、実装のtechnical PASSを科学的usableの保証へ広げない。
