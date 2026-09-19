# Step1 Phase B・B-3-1 Colab実行後監査
## v0.3／engine 0.47.0／commit 903458d71e94／run 20260917T154350Z

2026-09-18（日本時間）。Claude伝達用。

## 0. 判定

**今回のColab実行を、B-3-1のofficial規模control profileの範囲で受入れPASSとする。B-2の実装受入れとB-3-0 Colab smoke受入れPASSを維持する。新しい必須修正、候補patch、今回のB-3-1の再実行は要求しない。B-3-2の起草・実行前監査へ進んでよい。**

今回確認したのは、実行済みnotebook、RUN/out全体、承認済みsourceとの対応、および保存bankからの独立数値再計算である。画面上のTrueだけに基づく判定ではない。

**本受入れは、B-3全体の完了、ENGINE_VALID、Phase C/rules v1.0の科学的freeze、全family・2000 pseudoの正式global較正、実観測の科学的label解放を承認するものではない。** 1配置のcontrolと本番の全surviving-size familyは区別する。

## 1. 受領物とsourceの同一性

| 対象 | SHA256 |
|---|---|
| `b3_1_out_903458d71e94.zip`（133,229,666 bytes） | `5b8269d42f9bd6e5681ed4144ac2a967aab2d67f819ad8d766be827c40db8f91` |
| 実行済みnotebook（13,473 bytes） | `628f1eb7daae2ed6270cd63a7b39745cb8ecf2562e165a9f607ed0be235d9d79` |
| `b3_1_final_record.json` | `cd22fb9081ba5f4b29486a229d5c3d0afe5d4e6721b07c9f52bd7ade8b525263` |
| `control/b3_1_run_manifest.json` | `91de0001967c78ae29458f075b5cdd34d9d68aad879b4f7d9b60dabc5872cf35` |
| 承認済みinventory | `639809b165fba6478d9bb7e82ce435fa8b3391a5c9bf7bfa921ef7c7a2717d43` |
| `b3_1_control.py` | `d62a77502ad6efdc8bb65df8b8bcb44d66a390c884eaf0a0ad885dd3f9db4eeb` |
| `b3_1_pins.json` | `1b63906cd472c9dc18c474e11d455bb4d9b23b3359d314c1a54d79c131d056d4` |

commitは`903458d71e9478e409ecba9273375cdac8d92d4f`、runは`/content/b3_1_runs/20260917T154350Z`。run IDはUTC表記で、日本時間では2026年9月18日00:43:50開始に対応する。

前回受領`files_2.zip`内の承認済みpacketを展開し、実ファイルの42 module・script・pins・inventoryを、今回のmanifestおよび3 checkpointのbindingと照合した。source packet checkerは141/141 SHA一致、failures 0。これは保持sourceと提出された実行記録の照合であり、この監査でremote commitをcloneし直したとの主張ではない。

notebookの既存cell sourceは、外側launcherの設定cellを除き承認済みtemplateと全件一致。設定cellのcommit・inventory・launcher IDは保存lockと一致する。code cellの実行番号は1,2,3,4,5,7であり、最後の7はZIP作成・ダウンロードcellである。計算・最終判定cellにerror outputやsource変更はない。ZIP cellが表示する133,229,666 bytesは受領ZIPの実サイズと一致する。

## 2. 保存物と実行状態

| 確認項目 | 結果 |
|---|---|
| ZIP CRC・重複名・パス・symlink | 異常なし |
| ZIP内実ファイル | 12（ほかに`control/`のdirectory entry 1） |
| final recordの出力inventory | 10/10、実ファイル集合・SHA・byte数一致 |
| return listの出力inventory | 同じ10/10で一致 |
| return list→final SHA | 一致 |
| control manifestの出力inventory | 6/6で集合・SHA・byte数一致 |
| script終了コード | 0 |
| required gate | 承認済み固定21項目すべて厳密なTrue |
| script stage／failures | `complete`／`[]` |
| final `B3_1_PASS` | True、現在のscript終了コードとの合成も正しい |
| launcher script stderr | 空 |
| 監査終了時の受領出力・source・元ZIP/notebookの変更 | すべて0件 |

3つのFamilyResult checkpointは`main`、`positive_registered`、`positive_mock_diagnostic`である。negative固定targetと200 pseudoの結果はrun manifest内に保存される現設計であり、`result_negative.json`の欠落ではない。

実行profile：`kind=control, mode=control_official, selftest_scale=1.0`、N=1,000,000、m=100、B=2,000、Nfit=200,000、Bkde=2,000。自己試験scaleの結果を正式規模に読み替えたものではない。

記録された環境：Python 3.13.15／NumPy 2.1.3／SciPy 1.16.3／healpy 1.20.0／POT 0.9.7.post1／CAMB 2.0.4。pinsおよびlauncherと一致。NumPy所有OpenBLASは2 thread、他poolは2・2・1で、登録された条件を満たす。

保存されたscript実行時間は574.457秒（約9分34秒）。これはscript内の時間であり、clone・pip・最終ZIP転送を含む全作業時間ではない。

## 3. bank、plan、再抽出依存の検証

bankは12群のT1/T2/AX/PLと6つのcid、計54配列。期待集合、shape、dtype、有限性、非負性、AX/PL値域、cidの全並びを検査した。T1/T2の各array SHAもmanifestと一致する。evaluation・negative modelは各100万行、fitting・等方校正は各20万行、pseudo閾値は200行（m=1）。

generation callは、登録された6 callのids/N/m/systemsと完全一致する。negative生成stream、evaluation/fitting/pseudoの分離は記録されたkeyとsourceにより照合した。ここで物理skyを新規生成して同じlatentまで再計算したわけではない。

再抽出planはevaluation、negative model、fitting、negative fittingの4群×5 seed＝20。**全20個の乱数keyから再抽出indexとmultiplicityを独立再生成し、int64表現のSHAが全件一致**した。保存されたseed 0の4行列はint16だが、値・shape・整数条件を確認し、int64へ戻したSHAも一致する。

negativeのmodelとreferenceは異なるkey・異なるmultiplicityである。分子と分母に同じ再抽出を適用する前々版の問題は、今回の実データ経路に戻っていない。

## 4. A5 cross-check：保存bankから再計算

| 指標 | 独立再計算値 | 登録済み比較区間 |
|---|---:|---|
| T1中央値 | 120.43422003041243 | [115.42416000366211, 122.77178955078125] |
| T2中央値 | 609.2605731158183 | [571.3977973937988, 617.9871261596679] |
| P(T1≤target) | 2,975/200,000 = 0.014875 | [0.0091109787688965, 0.02460097702042674] |
| P(Event B) | 733/200,000 = 0.003665 | [0.0015565881296028053, 0.01023955634772571] |

4値とも保存値を再現し、登録区間内にある。再計算したのは今回の等方bankの要約であり、比較先A5の物理nullや参照区間を新規生成したわけではない。

外部の凍結資産・共分散・平方根の生配列はRUN/outにはない。したがって、これらについては承認source/pinsとの対応とColabが記録したgate・数値条件の照合であり、当方で元の共分散を再loadして根を生成したとの主張はしない。

## 5. Q・精度とnegative controlの独立再計算

### 5.1 3結果×2系統×5 seed

raw T1/T2からcluster hitを作り直し、独立再生成したmultiplicityで再抽出した。比較側でengineの`resample_hits`、CI helper、precision helperは使っていない。

| 結果／系統 | model/reference hit | Q | seed 0の95%区間（保存値） |
|---|---:|---:|---|
| main／matched | 4,690 / 3,623 | 1.2945073143803478 | [1.2608326855214456, 1.328791426760343] |
| main／native | 21,906 / 18,032 | 1.2148402839396628 | [1.2004823550779016, 1.2291821457912235] |
| 登録positive／matched | 362,371 / 3,623 | 100.019597019045 | [96.87024680752575, 103.201807739903] |
| 登録positive／native | 653,159 / 18,032 | 36.22221606033718 | [35.69455401933224, 36.74595814685643] |
| mock追加診断／matched | 63,626 / 3,623 | 17.561689207838807 | [17.016910977811808, 18.106604011566873] |
| mock追加診断／native | 189,399 / 18,032 | 10.503493788819878 | [10.35785442410065, 10.644352572689547] |

全6系統の各5 seedについて、保存された再抽出分子・分母確率配列は完全一致。区間端点の最大差は9.95×10^-14。event-positive cluster数・相対半幅・logQ幅の5-seed CVを再計算し、全6系統のprecision passを再現した。これらの差は独立計算の丸め差であり、科学的閾値や判定条件の変更ではない。

### 5.2 固定targetのnegative

独立等方model/referenceのhitは3,648／3,623、Q=1.0069003588186587、95%区間=[0.9635242934397261, 1.0530241581961322]。positive cluster数は3,094／3,021、相対半幅0.0444433、5-seed幅CV0.0245801でprecision pass。

support／strongは確定False、technical_status=ok、gate=Trueを再現した。今回のnegative専用経路ではQ条件でsupport不成立を確定できるため、logDを計算しない理由を保存している。logDの未計算を正の値として補ったものではない。この経路をunsupportedも含むproduction全判定の再現と称さない。

### 5.3 200 pseudoのnegative率

200行すべてについて、保存されたpseudoのT1/T2、行番号、raw hit、Q、precision、support、technical、rate_truthを照合した。5 seedの全区間も再計算し、全件precision passでQ下端<3となることを確認した。Q下端の範囲は約[0.94238, 0.99914]であり、今回はどの行にもpositiveなlogDの評価を要しない。

| 指標 | 結果 |
|---|---:|
| 固定pseudo数 | 200 |
| support True | 0 |
| unknown | 0 |
| technical failure | 0 |
| Wilson上端（c+u、登録z=1.959964） | 0.018845326668962936 |
| 閾値 | 0.05 |
| negative率gate | PASS |

**これは一配置controlの200 pseudo検査であり、全family・2000 pseudoの正式global較正ではない。** 0/200を「誤支持確率が厳密に0」と解釈しない。記録されたbank・再抽出設定に条件付いたcontrolの合格である。

## 6. KDE・positive full predicateの独立再計算

fitting bankをSciPy `gaussian_kde`へ直接渡し、Scott帯域幅と係数0.7/1.4で再計算した。3結果×3条件の最大絶対差は2.11×10^-12。符号不変かつ変化幅<0.1という感度条件も維持された。

さらに、登録positiveと0.6 mock追加診断の**全2000 replicateずつ**について、同じcluster multiplicityを使い、20万行をliteralに複製したSciPy KDEで再計算した。比較側でengineのweighted/batched density helperは使っていない。

同じreference fitの共有には、KDEの共通スケーリング恒等式 `f_(sX)(t)=f_X(t/s)/s²` を使った。固定された8 replicateでは、実際にsXを作って再fitする経路も照合した。抽出標本・帯域幅・target・有効replicate集合は変更していない。

| 指標 | 登録positive（reference×0.35） | 追加診断（mock model×0.6） |
|---|---:|---:|
| 保存logD点推定 | 2.898555111039297 | 2.1419891945123233 |
| 保存logD 95%区間 | [2.8503167159342584, 2.9448767140172065] | [2.098047260015009, 2.1865167833758106] |
| 独立再計算の区間 | [2.8503167159329155, 2.944876714015718] | [2.098047260013813, 2.186516783374703] |
| replicate数／有限数 | 2000／2000 | 2000／2000 |
| replicate値の最大差 | 1.93×10^-12 | 1.47×10^-12 |
| 区間端点の最大差 | 1.49×10^-12 | 1.20×10^-12 |

いずれも区間下端>0を再現。失敗replicateの除外・別乱数への差し替えはない。2列は同じ再抽出planを共有するため、「4000個の独立した実験」を意味しない。

登録positiveのmatched Q区間下端≥10、logD点推定>0、logD区間下端>0、native Q区間下端>1、両系統の精度および必要監査を満たし、**strong full predicateの成功を確認した**。

**このstrongは人工positive fixtureの検出成功であり、宇宙トポロジーE7の正式支持ではない。** 0.6倍は登録0.35倍とは別の追加診断であり、そのscientific label自体を必須gateへ昇格させない。

## 7. conjunct、brute-force、checkpoint

### 7.1 conjunct

保存positiveの数量から、承認済み`conjunct_battery`を再実行し、保存recordと完全一致した。正常なsupport/strong基準2件はTrue、strongの7 drop・supportの4 dropは確定Falseで、すべてtechnical_status=ok。条件省略mutant6種の検知も再現した。

### 7.2 brute-force

保存された等方bankからtarget＋5分位閾値を再構成した。2系統×model/reference×6閾値＝24組について、実`ConfigBank.hit_tables`、実`resample_hits`と、別のraw行選択・cluster別bincount・乱数indexによる直接加算を照合した。cluster hit・UID・N・再抽出後整数和・確率が一致した。

この比較専用planのBはsourceどおり20であり、主QのB=2000とは区別する。runtime comparatorと2種類の集計故障detectorの再実行も保存値と一致した。

前回監査の限定は維持する。runtime detectorはzeroed/permuted **hit集計**の2変異であり、zeroed resamplerの第三変異が今回のruntimeへ追加されたという意味ではない。実resamplerの故障検知は前回の独立pytestで確認済みで、今回は正常な実resampler出力を保存bankから照合した。

### 7.3 checkpoint

承認済みengineの`read_family_result`により3 checkpointを再検証した。module/rules/profile binding、保存値に条件付いたQ・密度・decisionの意味検証が通った。matched fitting bankのSHAもraw配列から再構成し、各checkpointのbindingと一致した。

readerのscopeは `core, conditional on stored replicate values/densities; position: not-integrated; gate: none`。外部W₂/contextや全productionの再利用契約を認証したものではない。今回は全`evaluate_family`をもう一度同一engineで実行するのではなく、独立数値再計算とreader・control helperの再実行を分けて行った。

## 8. mainのinconclusiveと、次工程

mainのQ≈1.2945、95%区間下端≈1.2608はsupport閾値3に届かず、logD>0だけでsupportにはならない。正常な`inconclusive`でありB3_1_PASS=Trueと矛盾しない。unsupportedの条件でもない。

B-3-1のofficial規模control受入れを、本commit・run ID・各SHAと結び付けて記録する。B-3-0の既存receiptも維持する。過去の失敗や自己試験recordを上書きしない。

**次は既存specのB-3-2**：登録規模exact-OT共有null、E2/E7/E8正式12位置assetの生成・照合・保存、新規9点のcircle coverage／clone／prior受入れの起草・実行前監査である。これらの実行を無条件に承認するのではなく、次の提出を検査する工程へ進める。

B-3-3で整理する未実装事項の受入期限、Phase C、正式global較正、label封印・解放も残る。既存文書の「B-3-0未実施」等の歴史表は、履歴として保持し現在の受入れ状態を別途追記する。文書整理だけのために今回の計算を再実行しない。

## 9. 実施範囲・限界・監査成果物

当方環境はPython 3.13.5／NumPy 2.3.5／SciPy 1.17.0、BLAS/OMP 1 thread。登録Colabではない。新たなColab起動、元の物理共分散load・sky再生成、全846 pytest、formal W₂/OT・12位置、全familyの2000 pseudo較正は行っていない。B-3-1 notebookには承認設計どおりpytest段階を追加していない。

検査コードは、整合性245、plan/Q/negative1765、reader/control84のassertionを通過した。ただし同一データを細かく照合した件数であり、2094種類の独立した科学的条件を立証したという意味ではない。KDEは別途全2000×2列を数値照合した。

監査側のKDE再計算は分割実行した。途中の監査プロセスにresource中断があり、同じ標本を用いて分割再実行したが、採用した完了chunkは[0,100)、[100,1000)、[1000,1500)、[1500,2000)で、全indexに重複・欠落なし。これは提出Colabの失敗ではない。また初期のWilson照合ではunrounded zを使ったが、sourceの登録定数1.959964に合わせて比較し直した。どちらも上端は0.05を十分下回り、提出物・判定閾値を変更していない。

証拠ZIPには、承認済みsource、出力の軽量record、再計算コード、照合結果、全KDE再計算配列、機械可読receiptを含む。受領した大型bank/plan NPZと元の出力ZIPは重複同梱しない。再実行方法はREADME参照。

主な証拠：`evidence/integrity.json`、`plans_Q_negative.json`、`negative_independent_replicate_intervals.npz`、`kde_summary.json`、`kde_independent_all_2000.npz`、`readers_brute_conjunct.json`、`accepted_packet_check.json`、`final_members.json`、`acceptance_receipt.json`。

**最終判定：B-3-1 official規模control受入れPASS。追加必須修正・今回runの再実行は不要。B-3-2の起草・実行前監査へGO。**
