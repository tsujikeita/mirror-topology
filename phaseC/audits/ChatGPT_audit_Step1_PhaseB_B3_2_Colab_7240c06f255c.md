# Step1 Phase B・B-3-2 A/B Colab実行後監査
## A v0.2／B v0.5・engine 0.52.0・commit 7240c06f255c

2026-09-19（日本時間）。Claude伝達用。

## 0. 判定と射程

**今回提出されたA側の正式12位置asset・circle幾何記録、およびB側の登録規模共有W₂ null生成を、それぞれの実行scopeで受入れPASSとする。新しい必須修正、参考patch、A/Bの再実行は要求しない。B-2実装受入れ、B-3-0 smoke、B-3-1 official規模controlの受入れを維持する。**

この判断は、実行済みnotebookとRUN/outの同一性、承認済みsourceとの照合、保存配列・抽出計画・座標の独立再計算、距離の限定的な独立exact再計算に基づく。Trueの画面表示だけによる受入れではない。

| 範囲 | 判定 |
|---|---|
| B-3-2A：登録E2/E7/E8の12位置asset、重み、提出circle幾何記録 | 受入れPASS |
| B-3-2B：校正20万行・独立null60万行、n_sub 2000/5000・各1000反復の共有null | 受入れPASS |
| Google Drive上のgeneration実体・LATEST・実復元 | 今回未取得・未検証。提出logの成功記録とは区別 |
| 新位置のA11物理共分散変換・clone同値性 | 今回のA実行scope外 |
| observed側のcase別W₂、停止B_final、位置拡張trigger | 今回のB実行scope外 |
| B-3全体完了・ENGINE_VALID・Phase C/rules v1.0科学的freeze | 今回の承認ではない |
| 全family・2000 pseudoの正式global較正・実観測label解放 | 未実施・未承認 |

次は既存spec v0.3追補§CのB-3-3に沿い、受入れreceiptと未実装項目の受入期限を集約し、Phase C packet準備へ進んでよい。各機能の「正式使用前」という既存受入期限を後ろ倒しにしない。

## 1. 受領物と同一性

全実行のcommitは `7240c06f255cd206ae3e2db6210ce7efd66e1b32`。

| 受領物 | bytes | SHA256 |
|---|---:|---|
| A実行済みnotebook | 14,135 | `c3547a90f08957c229a8615bfe0d57c6a640c054136d2bb735d481aac46b3fbd` |
| B実行済みnotebook | 26,061 | `4c643c540aea161f726c616f16e014f1b10c9af5d04d9b7aeff39a703ea1bff3` |
| `b3_2A_out_7240c06f255c.zip` | 12,215 | `ed4e2f10b43f071e78de034046afd4face39beda9ac5bcf5063f3937565f2739` |
| `b3_2B_out_7240c06f255c.zip` | 43,767,239 | `c81bccb92476c6bce33d43573f4851bff1cb74446109a2df126264651769e01f` |

各ファイルの完全なSHA・byte数一覧は、機械可読の `input_identity.json` に保持する。

照合sourceは、前回承認した `files_7.zip` 内の `engine_phaseB_for_commit_B3_2_v0.5.zip`（SHA `1ff043795613b7ec1bc098a2164aa067965e8a9b54d6f712e75ad263f90b9a60`）である。

- inventory SHA：`857b2f371b856d0dcdda6f87ef96b66fad752636d3599617e0fcb6af887753f4`
- pins SHA：`b7b44f3bc7f7c5539eea7d825521beaaa03b2ccccb949e9818411ebc3379636e`
- engine：0.52.0、44 module。
- 保持sourceに対するpacket checker：162/162 SHA一致、不整合0。
- 両runのmodule SHA一覧、pins、launcher inventoryと保持sourceは一致。
- 両notebookの全既存セルsourceは、外側launcher設定以外、承認templateと一致。未承認の計算・判定セル差分はない。
- 今回remote commitを再cloneしたという意味ではなく、保持sourceと提出記録の同一性の照合である。

A notebookは実行番号が全てnullだが、source・保存stdout・run manifest・final record・出力SHAは対応する。実行番号を根拠に実行順を証明したとはしない。Bの番号は1～6で、fresh一回のattemptである。両方ともerror outputはない。

## 2. 実行と出力inventory

| 確認 | A | B |
|---|---:|---:|
| script終了コード | 0 | 0 |
| 必須gate：source上の固定集合との照合 | 13/13 True | 11/11 True |
| stage／failures | complete／空 | complete／空 |
| 最終PASS再判定 | True | True |
| ZIP内実ファイル数 | 10 | 13 |
| final recordの出力一覧・SHA・byte数 | 8/8一致 | 11/11一致 |
| return list→final SHAと同じ出力一覧 | 一致 | 一致 |
| script内部の出力inventory | 3/3一致 | 3/3一致 |
| launcher stderr | 空 | 空 |

Bのcheckpoint2本はfinalの11件に含まれる。script内部一覧はnullディレクトリ直下の3ファイルを扱うため、その一覧にcheckpointの子ディレクトリがないことを欠落とは扱わない。Aの空の作業ディレクトリも、ファイルの欠落を示すものではない。

環境記録はPython 3.13.15／NumPy 2.1.3／SciPy 1.16.3／healpy 1.20.0／POT 0.9.7.post1／CAMB 2.0.4でpinsと一致。NumPy OpenBLASは2 thread、他のpoolは2・2・1で登録条件を満たす。

Aの外部checkout recordは、CMBtopologyの期待origin・commit `0cc65e34f03df85e92f738686bff0a476132f337`、clean=True、凍結A7 script SHAと対応する。ここでは記録とsourceの対応を検査し、実CMBtopologyを新たに実行していない。

## 3. A：登録12位置の独立再生成

### 3.1 全格子を使う独立oracle

保持sourceのA6/A7資産からsource-bound registryを復元した。registry SHAは `ba48214585c50348a9f43ef82ba33c3b7fcb982ebc89d0ba38985969c48ec851`。

独立比較側ではproductionのselectorを呼ばず、登録格子上の最近点距離場を保持して逐次更新する別実装を用いた。格子分解能、box、E2のhalf-turn商空間距離、exclusion、既存3 anchor、距離単位のtie許容1e-12と辞書順を維持した。E2/E7/E8を各一回再生成し、各familyの3 sizeのreduced座標へ照合した。

| family | exclusion前の全格子候補数 | exclusion後 | 保存された12点との比較 | 最小点間距離／登録min_sep |
|---|---:|---:|---|---|
| E2 | 100,020,001 | 96,874,650 | 全点完全一致・3 size一致 | 0.17664580908791794／0.05 |
| E7 | 2,101 | 2,101 | 全点完全一致・3 size一致 | 0.01579999999999998／0.015 |
| E8 | 9,246,501 | 9,246,501 | 全点完全一致・3 size一致 | 0.10117066824088548／0.04 |

最小距離も最終12点の66 pairから独立に計算して一致した。元の3 anchor、追加9点、各位置の重み1/12を保持する。監査用の距離場実装はproductionの演算経路の変更提案でも、productionを高速化して再実行する要求でもない。監査計算の時間をColabの正式runtime見積りへ転用しない。

全体asset SHA：`1d05e6b3afc86f8da94765cebe128f2b291bc523c10599dcb6e54ff7be01d89c`。

全9個のsize別manifest SHA、registry参照、全体asset SHA、run manifestの参照を照合した。既存readerの構造・canonical SHA検査も成功している。独立oracleと、source readerによる検査の範囲は区別する。

### 3.2 幾何CSV・anchor・重み

- 3 family × 3 surviving size × 12位置＝108行。key重複0、欠落0。
- 既存anchorは27行、追加位置は81行。全108行のreduced座標・observer ID・size・重みがassetと対応する。
- 物理座標表示は、登録liftから得たfull precision座標を小数6桁に丸めた値と一致する。丸めたCSVを正式入力へ逆輸入する手順は採らない。
- 既存27 anchorについて、凍結A7参照のd_clone／proper／improper距離、status、reduced座標を照合し一致した。
- 各family×sizeの重み和1。size重み1/3と組み合わせる場合は各配置1/36。連続一様priorを積分したという意味ではない。
- 108行のobservational_statusは `no_nondegenerate_circles`。
- L=1.00の36行はgeometric_status=`zero_radius_boundary`。L=1.20/1.50の72行は `no_nondegenerate_circles`。境界と非境界を混同していない。
- d_cloneは各sizeのLに対応し、d<1候補数は0、exclusion_witness_exists=Falseで記録されている。

**限定：今回、新9点について外部A7/CMBtopologyによるnearest-clone探索を独立に再実行したわけではない。** 上記の幾何部分は、承認済みscriptが出力した全行の整合性、既存27 anchorとの一致、pinnedな外部実行記録に基づく受入れである。E2のimproper距離のinfは凍結参照にもある値で、今回の保存行との一致を確認した。これを新たな数値故障として数えてはいない。

A11の物理共分散変換・clone同値性はA notebookにもscope外と明記されている。今回のnearest-clone幾何の受入れで、その別検査まで完了したとはしない。

## 4. B：校正・null入力とwhitening

### 4.1 入力契約

実配列14本の集合・shape・dtype・有限性を照合した。T1/T2は非負、cidは100行ずつの連続clusterである。

| bank | 行数 | cluster数 | 生成purpose/stream |
|---|---:|---:|---|
| whitening校正 | 200,000 | 2,000 | calibration：100／0 |
| 独立null pool | 600,000 | 6,000 | w2_isotropic：700／0 |

両bankともfloat64 primary／paired float32 selectionが保存されている。`*_f32`はselection pathを表す命名であり、保存T1/T2自体がfloat32でなければならないという契約ではない（評価はfloat64）。実際の保存dtypeはfloat64である。

生成call一覧、selftest_scale=1.0、exact_pot_w2、assets_officialのprovenance、環境、source/pins/inventory/rulesの参照は整合する。別purposeによる生成を、同じ校正bankの再利用へ置き換えていない。

### 4.2 凍結A10との比較

保持sourceに同梱されたA10校正参照のSHA `6a8c87889ec1d7a5d35336a3cdc30f9537376f2b3878ac9d1ee12cc34319c5df` を照合した。

**保存された校正20万行のT1・T2・cidは、凍結参照と全行完全一致**した。これはraw skyの再生成ではなく、今回の保存配列と凍結配列の直接照合である。AX/PLは今回のpool NPZに保存されていないため、対応するruntimeのbit/plane gateを当方が別途全行再計算したとはしない。

### 4.3 whitening再計算

保存校正T1/T2からμと標本共分散を再計算し、Cholesky whiteningを構成した。

- μ＝[129.8130295852835, 668.6041141597252]。保存値との差0。
- Wの保存値との差：最大2.0816681711721685e-17。
- 保存Wに対するmax|WΣWᵀ−I|＝2.220446049250313e-15。登録1e-10を満たす。
- 同じ保存μ・Wをnullの両pathへ適用した結果は、保存Tw64/Tw32と一致（検査許容1e-13）。
- 校正／nullの各配列SHA、whitening identity、PositionBankのSHAとasset identityも一致。

## 5. B：全抽出列・誤差上界・分位の独立照合

### 5.1 全2000反復を照合

n_sub＝2000/5000の両方で1000反復を保存している。m＝100なので、それぞれ1 block当たり20/50 clusterを使用する。

保存値を利用してブロックを逆算するのではなく、登録key `[20260912, 5, n_sub, 999]` から6000 clusterのpermutationを再生成し、枯渇時の再置換を含め全抽出列を照合した。

- 全2000反復の3 blockが完全一致。
- 各反復内の3 blockはdisjoint。範囲・cluster数・row数も一致。
- 保存された全6000 pair値は有限・非負で、各反復の最大値とvalues列が一致。
- paired Tw64/Tw32と各subsetから、反復ごとのcoupling boundを全2000件再計算。保存値との差は最大0。
- boundが0の反復を一律に未測定とは扱わない。該当subsetの実paired差から計算した結果が0であることを確認している。

### 5.2 q99_full

| n_sub | B_max | q99_full（higher） | 全列の最大coupling bound |
|---|---:|---:|---:|
| 2000 | 1000 | 0.2329460744636862 | 0.003499239220584561 |
| 5000 | 1000 | 0.15325768187329825 | 0.0024509872056402513 |

独立に列をsortし、`ceil(0.99*(B−1))`の順序統計量を取得して保存値と一致した。B＝200/400/600/800/1000の各prefixのq99とbound最大値も再計算し、証拠に保存した。

**これらはB=1000全列の要約であり、全caseに共通の最終停止B_finalや最終q99の採用を承認するものではない。** case別のobserved値、indicator vector、停止履歴、感度判定を別途適用する。nullが完成したことだけでposition-sensitive／non-sensitive、support／unsupportedなどの科学的labelを出さない。

共有assetのpayload SHA：`8348d5f4733ae5a37e39f4aa88109626e5caab312b55bd108be7ec9e5daff3ba`。

## 6. 距離の独立exact抜き取り再計算

保存POT値とは別実装として、平方ユークリッド距離行列をSciPyの `linear_sum_assignment` で最小費用割当し、割当費用をnで割って平方根を取った。同数n・等重みの経験分布では、輸送行列をn倍すると二重確率行列になり、線形目的の最適値は置換行列で達成できるため、この割当解は同じ離散W₂のexact解を与える。これはsliced-W₂や平均差による近似ではない。「exact」は離散最適化の意味であり、浮動小数演算が厳密な実数算術であるという意味ではない。

SciPy公式manualの `scipy.optimize.linear_sum_assignment` は、費用行列に対する最小総費用の完全割当と返値からの費用計算を説明する。監査runtimeはSciPy 1.17.0で、POTは用いていない。

抜き取り規則は、各n_subの先頭・末尾・full q99に対応する反復。q99の反復番号は全列から導出して選び、無作為sampleとは主張しない。各反復の3 pairすべてを元のn_subのまま再計算した。

| n_sub | 再計算した反復番号（0始まり） | pair数 |
|---|---|---:|
| 2000 | 0、339（q99）、999 | 9 |
| 5000 | 0、411（q99）、999 | 9 |

**18 pair全件で一致し、最大絶対差は3.0531133177191805e-16。** 各選択反復の最大pair値も一致した。比較用の1e-12は監査側の数値同値性検査許容であり、登録された科学的閾値・停止規則を変更したものではない。

全6000 pairを独立exact再計算したとは主張しない。全列について行ったのは、SHA・有限性・pair/max関係・block列・bound・分位・checkpointの照合である。

## 7. checkpointと保存状態

### 7.1 完成checkpoint

n_sub2000/5000両方のcheckpointについて、version付きschema、done=1000、payload digest、配列件数、共有identity、source・環境・whitening・両bankの参照を照合した。values/blocks/pairwise/boundsは共有assetと一致する。

| checkpoint | SHA256 |
|---|---|
| null_nsub2000.json | `e542895b07e0b0176574d1ad2891dbf685804d6fb7a27f8c7d3a527368458234` |
| null_nsub5000.json | `1fbc1fca4bffc07cb51c2ed54e045b88df2817bfa47a0a87f248f8324649c141` |

さらに今回の実Colab checkpointをそのまま用い、隔離したローカルフォルダへgeneration publish→verify→restoreを実行した。両stageはcomplete、復元bytesは元のcheckpointと完全一致。元の受領checkpointは変更していない。これはローカル復元の実行であり、Driveのgenerationを取得して復元した試験ではない。

### 7.2 Drive保存の記録と限界

- recordのpublishes：463。
- logを読み分けると、checkpoint作成前の `published None` が3回、実generation pathを返した記録が460回。
- failure記録0、最終generation pathあり、worker joined=True、persistent_backup_ok=True。
- 463は保存世代数ではなく、例外なく返ったpublish呼出し数である。460も累積path記録数であり、保持世代数ではない。

最後のpath：
`/content/drive/MyDrive/mirror_topology_b3_2B/20260918T152513Z/gen_20260918T231842Z_01789773522896801043_3d2ef3d0`

**今回の出力ZIPにはDrive側のgeneration manifest実体、LATEST、保持世代一式はない。従って、Drive上の現在の実保存や復元成功を独立検証したとはしない。** この範囲限定は、数値生成の受入れを取り消す理由ではない。既承認設計どおり、backup状態とB3_2B_PASSを分けて扱う。

永続世代はcheckpointとmanifest/lockを扱う機能で、全poolや全RUN/outを保存するものではない。今回の両ZIPと実行済みnotebookをそのまま最終成果物として保持する。

## 8. 実測runtimeと履歴

| 実行 | run ID（UTC） | 日本時間の開始 | script全体の実測 |
|---|---|---|---:|
| A | 20260918T094339Z | 2026-09-18 18:43:39 | 18,304.33秒、約5.08時間 |
| B | 20260918T152513Z | 2026-09-19 00:25:13 | 28,373.24秒、約7.88時間 |

Aのbuild+intakeは18,290.95秒、Bのshared_null_buildは28,243.50秒。B notebookの2.5～4時間という事前見積りより実測は長かった。今後の運用資料にはこのrun・環境に対応する実測として記録する。別環境の所要時間をこの値で保証せず、見積り超過だけを理由に再実行しない。

旧のreceipt／自己試験recordは書き換えず、今回のA/Bの実行後receiptを追加する。AとBを完了したという意味を、A11物理cloneやobserved側のcase判定まで拡張しない。

## 9. 実施したこと／していないこと

実施：両ZIPのCRC・path・同一性検査、保持sourceの162項目checker、44module・pins・notebook source照合、全output inventory、A全格子の独立oracle、108幾何行・27anchor照合、14配列・A10 T1/T2/cid・whitening照合、全2000反復の抽出とbound・分位の再計算、18 pairの独立exact割当、asset/checkpoint検証、実checkpointからのローカルpublish/restore、backup log照合。

監査環境：Python 3.13.5／NumPy 2.3.5／SciPy 1.17.0、計算processのBLAS/OMPを1 threadに設定。登録Colab環境ではない。POT、healpy、CAMBは未導入。sourceは変えず、浮動小数の再計算には数学的同値性を検査した。

未実施：新Colab起動、物理共分散・skyの新規生成、全6000 pairの独立OT再実行、外部A7/CMBtopologyによる108行の幾何再計算、実Drive読込み・復元、全888 pytestの今回の再実行、正式全family較正、科学的label解放。

当方の監査コードを初めて適用した際、snapshot返値の`complete`の参照先と、幾何statusの予想文字列に当方側の誤りがあり、それぞれ実schema・凍結参照の語彙に合わせて修正した。提出ファイルや受入条件を変更したものではなく、これらをユーザーコードの失敗として数えない。最終コードは全チェックを通過している。

最終SHA照合では、受領Aの10ファイル、Bの13ファイル、保持sourceの175ファイルについて、変更・欠落・新規追加0を確認した。assertionの粒度を独立した科学的検証数へ水増ししない。

## 10. 引継ぎ

**A/BそれぞれのB-3-2実行後受入れPASS。新たな必須修正・再実行なし。B-3-3の残件／受入期限／receipt集約へ進んでよい。**

今回の共有nullを後続へ渡すときは、file SHAとpayload SHA、校正とnullの配列identity、full B_max列・block・boundを保持する。観測caseの停止規則は各caseで評価し、このq99_fullを無条件に全caseのfinal値へコピーしない。

Phase C packet準備時には、正式12位置profile、pseudo側の完全Result archive、較正先行と実観測値の封印、production共分散のintake／bank生成器、外部context／checkpoint再利用など、既存移管表の機能ごとの期限を明示する。今回の正式資産生成成功で未実装機能まで実装済みにしない。

### 証拠ファイル

- `evidence/input_identity.json`, `integrity.json`, `packet_check.json`, `final_members.json`
- `A_full_grid_replay.json`, `A_records.json`, `A_minimum_distances.json`
- `B_replay.json`, `exact_sample_summary.json`, `exact_sample_*.json`
- `local_checkpoint_restore.json`, `environment.json`, `acceptance_receipt.json`
- `scripts/`：使用した独立再計算・整合性検査コード。`source/`：承認済みsourceを不変で保持。
- 大きい `null/b3_2_pools.npz` は証拠ZIPへ重複同梱しない。再計算時は受領B ZIPを `inputs/B/` へ展開する。
