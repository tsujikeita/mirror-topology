# Step1 Phase B・B-3-0 Colab実行後監査
## v0.5／commit 7045fc1a17b6／run 20260917T092845Z

2026-09-17。Claude伝達用。

## 0. 判定

**今回のColab実行を、B-3-0 smokeの範囲で受入れPASSとする。B-2の実装受入れを維持する。新しい必須修正、候補patch、このB-3-0の再実行は要求しない。B-3-1の起草・実行前監査へ進んでよい。**

前回はv0.5 harness修正後の「再実行前GO」であった。今回は実行済みnotebookと`RUN/out/`の提出物を照合し、保存bankからT10・T19・Q・KDEを再計算したうえでの**B-3-0実行後の受入れ**である。

この受入れをB-3全体完了、`ENGINE_VALID`、rules v1.0/Phase Cの科学的freeze、正式2000 pseudo較正、実観測の科学的label解放へ拡張しない。B-3-1の新notebookは別途実行前監査を受ける。

## 1. 受領物・版の対応

| 対象 | SHA256 |
|---|---|
| `b3_0_out_7045fc1a17b6(1).zip` | `d3386faa98cb58ef06801944bba86f159ef9d895032053348b6501c164dc03a0` |
| 実行済みnotebook | `bd423712f4cef22ddda03ca01fdf508ea3efa03f3b50ec216dae3640c3f81e6e` |
| ZIP内`b3_0_final_record.json` | `db365a2fa2639747e5db96832a7d645d0fdc5ec35e0e34c32172285a4d09898f` |
| ZIP内`smoke/b3_0_run_manifest.json` | `fc13421278bf901992dc0925bf638787451e230451007342f8748ba937386a51` |
| 検証対象inventory | `f0dd1eab49216f82fffa10c1ed6d5f555a1a3ea4fadc6f6e5b85a99c544bd7a7` |

記録されたcommitは`7045fc1a17b63755d66671c97882a32d7c2309c7`、engineは`0.44.0`、run directoryは`/content/b3_0_runs/20260917T092845Z`である。

比較sourceは、前回の`Step1_PhaseB_B3_0_v0.5_audit_evidence.zip`に保持されたv0.5 sourceを用いた。今回記録された41 moduleのSHAは、保持sourceの実ファイルSHA、承認済みinventory、checkpoint bindingと全件一致する。pinsの内容・SHA、smoke scriptのSHA、rules・tablesのSHAも一致する。これは保持sourceと今回の保存記録の照合であり、この監査でremote commitを新たにcloneしたという主張ではない。

notebookは、外側launcherのcommit・inventory設定を除いて、前回承認templateの既存セルsourceがすべて一致する。追加は**最終判定後のZIP作成・ダウンロードセル1個だけ**である。既存判定セルの変更、必須testの削除、許容値変更はない。codeセルの保存実行番号は1〜7で、notebookにerror outputはない。追加セルの表示したZIPサイズ8,158,674 bytesは受領ZIPと一致する。

## 2. 保存物の整合性

| 検査 | 結果 |
|---|---|
| ZIP CRC、重複名、パス検査 | 異常なし |
| ZIP内のファイル数 | 17（ほかに`smoke/`ディレクトリエントリ1） |
| final recordの出力inventory | 15/15で実ファイルのSHA・byte数・集合が一致 |
| return listのファイル集合・SHA・byte数 | 同じ15/15で一致 |
| return listが参照するfinal record SHA | 一致 |
| smoke manifest内部の出力inventory | 6/6で実ファイルのSHA・byte数・集合が一致 |
| launcher、run manifest、final recordの対応 | commit／version／pins／inventory／profileが整合 |
| 3つのstderrファイル | すべて空 |
| 監査処理による受領出力変更 | 0件 |

15ファイルという数は、final recordとreturn list自身を除外する登録設計どおりである。`b3_0_mock_family_result.json`が今回のcheckpointであり、別名のcheckpointが欠落しているわけではない。

## 3. Colab実行の受入れ条件

| 必須事項 | 今回の提出記録 |
|---|---|
| script終了コード | 0 |
| required gate | **固定16項目すべてTrue** |
| script stage／failures | `complete`／`[]` |
| pytest collection終了コード | 0 |
| pytest実行終了コード | 0 |
| 収集・実行・成功node | **39／39／39**、同一集合 |
| failure／error／SKIP／重複testcase | 0 |
| 最終`B3_0_PASS` | **True**、合成式の再判定もTrue |

pytest stdoutだけでなく、JUnitのtestcaseと`failure/error/skipped`子要素を確認した。期待集合は前回承認時の39 nodeとも一致する。単にpytestが終了コード0を返したことだけで合格とはしていない。

外部資産を使う以下3件も、今回のColabのJUnitでは実行・成功している。

- `test_legacy_kernel_assets_and_representation_gates`
- `test_legacy_kernel_bit_identical_to_frozen_notebook_cell`
- `test_legacy_kernel_cross_environment_agreement_with_a10_official`

特に前回は、2番目のテストがDrive mount時のカーネル取得で停止していた。今回は同テストもPASSであり、凍結A10のSHAとreference gateを検査した上で、float64/float32のscan・generateの比較まで通過したことに対応する。比較条件はv0.5 sourceで維持されている。

**上記39件のPASSは提出されたColab実行証拠の評価であり、当方が今回サンドボックスで39件の実資産testを新たに完走したという意味ではない。** JUnitは成功時の各数値差を個別保存しないので、特定の最大差値をこの記録から新たに断定しない。

## 4. 環境・入力・実行範囲

保存された実測環境はPython 3.13.15／NumPy 2.1.3／SciPy 1.16.3／healpy 1.20.0／POT 0.9.7.post1／CAMB 2.0.4で、登録pinsと一致する。NumPy所有OpenBLAS poolは2 thread、他poolは2・2・1で、記録された条件を満たす。

targetは登録済み`(39.67178834527284, 259.3375006282747)`で、Step0 SHA・PR3_Commander一意行との一致が記録されている。4つの平方根についてclip=0、最小固有値>0、対称性・再構成誤差のhard条件も記録上満たす。これらの生の外部資産や平方根配列は今回のZIPに含まれないため、物理共分散の生成・loadを当方で新たに再実行したとは扱わない。

profileは`kind=test, mode=smoke`、N=20,000、m=100、B=200、Nfit=20,000、Bkde=200である。**検査用E7一配置×2系統であり、登録first-waveの全配置・全prior混合ではない。** 主mock評価はprefixの20,000行のみ。T10専用検査では追加60,000行と合わせた80,000行の層別再抽出を扱う。

保存bankは13群×T1/T2/AX/PLと4つのcid、計56配列で、期待したshape・dtype・有限性・値域・cluster配列の対応を確認した。全11 plan（multiplicity行列12個）の乱数keyから再抽出indexとmultiplicityを独立に作り直し、保存値と完全一致した。全planのSHA、行和、UIDも照合した。

## 5. 保存bankからの独立数値照合

独立側では、engineの`resample_hits`、CI helper、weighted KDE helperを使わず、保存T1/T2と乱数keyから計算した。その後、別枠で承認済みengineのreaderとevaluatorも実行した。以下の微小差はこの保存値照合の数値差であり、新しい科学的許容閾値の導入ではない。

### 5.1 T10：prefixとextension

| role | prefix 20,000行のhit | extension 60,000行のhit |
|---|---:|---:|
| model matched | 87 | 340 |
| reference matched | 65 | 234 |

生のT1/T2から各clusterのhit数を再集計し、乱数keyから得たindexでliteralに再抽出した。hit表・再抽出整数和は完全一致。共有prefixはT10とevaluation seed 0の双方で一致し、prefix/extension重み1/4・3/4と分母20,000／80,000も一致する。

prefix-only確率の最大差は0。全80,000行の確率は、独立側で`(prefix_sum + extension_sum)/80000`と直接計算し、保存された層別式・literal式との差はいずれも最大`8.673617379884035e-19`であった。整数和の不一致ではない。

### 5.2 T19：A5の登録参照区間との照合

| 量 | 今回の独立再計算 | 既存pinsの参照区間 | 判定 |
|---|---:|---|---|
| T1中央値 | 120.88004597547014 | [115.42416000366211, 122.77178955078125] | 内側 |
| T2中央値 | 610.8350437026952 | [571.3977973937988, 617.9871261596679] | 内側 |
| P(T1≤target) | 275/20000 = 0.01375 | [0.0091109787688965, 0.02460097702042674] | 内側 |
| P(Event B) | 70/20000 = 0.0035 | [0.0015565881296028053, 0.01023955634772571] | 内側 |

4値ともrun manifestに保存された値を再現した。独立再計算したのは今回の等方calibration bankの要約であり、比較先A5の物理nullを新規生成したわけではない。参照区間は前回承認済みpinsの値を用いている。

### 5.3 Q・5 seedの区間・精度

| 量 | matched | native |
|---|---:|---:|
| model/reference hit | 87 / 65 | 434 / 349 |
| Q点推定 | 1.3384615384615384 | 1.2435530085959885 |
| seed 0の95%区間 | [1.144613600789806, 1.6532343398856477] | [1.1481082104702427, 1.3356335985752468] |
| event-positive cluster数 M/I | 72 / 54 | 177 / 171 |
| 区間相対半幅 | 0.19000200023695238 | 0.07539903277493827 |
| 5 seed logQ幅CV | 0.06094335076638062 | 0.047537266153326735 |

両系統×5 seedのnum/den配列は完全一致。family・configuration両方のCIを再計算し、端点の最大差はmatchedで0、nativeで`2.220446049250313e-16`。保存されたprecision passの値と判定を再現した。このsmoke一配置でのprecision passを全grid・正式規模の精度保証へ一般化しない。

### 5.4 KDE・logD

保存fitting bankをSciPyの`gaussian_kde`へ直接渡し、Scott帯域幅と係数0.7・1.4で再計算した。engineのweighted KDE helperはこの独立比較側では使っていない。

| 帯域幅係数 | 保存logD | 独立再計算との差の絶対値 |
|---|---:|---:|
| 1.0 | 0.21853832661647843 | 2.3092638912203256e-14 |
| 0.7 | 0.26848667878199173 | 3.197442310920451e-14 |
| 1.4 | 0.1742150556586779 | 4.973799150320701e-14 |

符号不変かつ変化幅<0.1の両条件を再現した。Qの区間下端が10未満、上端が1以上のためlogD CIは登録短絡規則により未計算であり、欠測エラーではない。fitting planの再生成一致は確認したが、不要なlogD CIを新たに計算する作業は行っていない。

### 5.5 checkpointと同じengineによる再評価

承認済みengineの`read_plans`で11 planを復元し、`read_family_result`で保存checkpointを再検証できた。readerのscopeは`core, conditional on stored replicate values/densities; position: not-integrated; gate: none`である。

さらに保存bankと復元planから同じengineの`evaluate_family`を再実行した。FamilyResult全体で構造・状態の相違はなく、数値scalar 4,371箇所の最大差は`1.7763568394002505e-15`。これは上記の独立推定量照合とは別の、保存物からの同一実装replayである。

## 6. `inconclusive`を実行失敗と混同しない

今回のmock resultは`technical_status=ok`、`display_label=inconclusive`で、support／strong／unsupportedはすべてFalseである。Qの95%区間下端は約1.145で、supportの下端条件3を満たさない。logD>0だけでsupportにはならない。一方、Q区間上端は1を超えるのでunsupportedの条件でもない。

これは正常な診断結果であり、B-3-0の技術的PASSと矛盾しない。mock covariance・一配置・test profileの結果を「E7模型族が支持された／否定された」「宇宙トポロジーが分かった」とは記載しない。今回の前進は、登録環境と実資産を使ったsmokeの検証経路が完走し、保存結果を再計算できたことである。

## 7. 受入れ範囲・次工程

既存spec v0.3追補のB/C節に沿い、B-2から移管されたColab mock-grid smoke、T10実bank、T19/A5および3 legacy回帰について、**B-3-0の規模・scopeで完了した**と記録してよい。B-3-1にも存在するofficial規模条件まで自動的に完了させない。

次はB-3-1のofficial規模controlの起草・実行前監査である。既存specが要求するnegative、positive full predicate、conjunct-drop、brute-force、finite inventory、A5 cross-checkなどを、そのcontrol用profileで受け入れる。productionの全surviving-size条件を緩める代替にしない。

B-3-2の登録規模exact-OT共有null、正式12位置assetと新9点のcircle/clone/prior、B-3-3で整理する未実装事項・受入期限、Phase C freeze・正式global較正・label解放は残る。今回の合格を理由に旧規則や科学的閾値を変更せず、A10 official全体やB-2を全面的にやり直す必要もない。

成果は今回のcommit、run ID、出力SHA、実行済みnotebookと結び付けて保持する。初回falseの履歴は上書きしない。

## 8. この監査で実施したこと／していないこと

実施：源コードと保存identityの照合、ZIP/JUnit/全出力inventoryの検査、56配列の契約検査、11 planの乱数key再生成、T10/T19/Q/KDEの保存bankからの独立計算、同一engine reader・FamilyResult replay。

現在の監査環境はPython 3.13.5／NumPy 2.3.5／SciPy 1.17.0、BLAS 1 threadで、登録Colab環境そのものではない。環境差を無視してColab lockの合格を当方環境へ移したのではない。

未実施：新しいColab実行、実物理共分散の生成・外部凍結資産からの全sky再生成、39件legacy実資産testの当方での再実行、B-2全827件suite、official規模W2/OT、正式12位置実行、2000 pseudo全手順較正。

監査script内の整合性assertionは118、数値replay assertionは118で、不一致0。ただしこれは同一データへの粒度を分けた確認数であり、236種類の独立した科学的検証を実証したという意味ではない。

### 主な根拠

- 受領ZIPの`launcher_lock.json`、`b3_0_final_record.json`、`b3_0_return_list.json`、`pytest_b3_0.xml`と全log。
- `smoke/b3_0_run_manifest.json`、`b3_0_banks.npz`、`b3_0_T10_*.npz`、`b3_0_plans.json`、`b3_0_mock_family_result.json`。
- 今回の`evidence/integrity_and_scope.json`、`numerical_replay.json`、`acceptance_receipt.json`、`same_engine_replayed_result.json`。
- 今回の`scripts/verify_received.py`、`replay_saved_banks.py`。

**最終判定：B-3-0 Colab smoke受入れPASS。追加必須修正なし。B-3-1準備へGO。**
