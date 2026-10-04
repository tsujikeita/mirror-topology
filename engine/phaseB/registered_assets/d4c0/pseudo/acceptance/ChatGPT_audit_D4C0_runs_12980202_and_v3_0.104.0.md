# D4C-0 正式結果とv3（0.104.0）の監査
## pseudo受入れPASS／D-2W失敗原本の確認／入力解決修正PASS・再実行GO
2026-10-04。Claude伝達・著者保存用。対象は添付の実bytes。remote Git treeや過去のColabを直接観測した監査ではない。

## 0. 判定
**D4C-0bの正式pseudo NPZと生成証拠を、原本登録へ進める範囲で受け入れる。D4C-0aの旧attemptは失敗として保持する。0.104.0の入力解決修正を受け入れ、固定commit/inventoryでD-2Wのみ再実行GOとする。新しい必須patchはない。**

pseudoは0.103.0のColab原本を用いる。0.104.0での再生成、既存D2 bankの再生成、D3c profileの再実行は不要である。登録loader完成・W2結果・global較正は今回の受入れに含まない。

旧版のregistryにrun_idがないことは、既存登録原本から確認可能であった。前回の実行前監査でこのformal経路の不整合を見落とした。自己試験・launcher試験の成功を正式入力の成功へ広げるべきではなかった。今回、同じ登録原本で旧/new入力段を直接比較した。

## 1. 実体と固定値
|対象|SHA256|
|---|---|
|結果packet|`e9e759a31590a8727af755a50cf2943b9323313e7c62dbadac950bbfd4a97f5b`|
|新source ZIP（16,814,344 bytes）|`df5eb95915a6b794c453eb74dbf30203b2e1fa116e1393ed533932e0c6f688a7`|
|新inventory|`49976b3e24e27ee614c8e31bb2b292554cf550b95a189c96e9cd190fc92df6f2`|
|新D2W script|`dcd64283d87ef0e0b14a68fc0e8a889743db4f66ae6ee0bd0881652bf4ead8e6`|
|旧source ZIP|`55cc4d5e90245bfd09de4d71aaba057e360261da134234e940d8db1557f99395`|
|pseudo inner ZIP（50,138 bytes）|`57c0df458eb013c0450b57d880fdf837dcdb1f8f902a6b8b6350e1fa2d43b826`|
|失敗W2 inner ZIP（5,985 bytes）|`09f9ab0e8ade6c5f0b8cb53c7198bf20e9973618a8146c9647e9b57b9b98b037`|

旧commit `12980202ee111a26c0a608e7e5bba6caed5302ae` / engine0.103.0は前回GO JSONと直接照合した。新commitは著者提示`f3aec79358452a293ccced14efd4f7e3ad240477`であり、remote treeとの全面比較はしていない。

ZIPはCRC・重複・path・symlinkを検査し隔離展開した。結果packetは4file（inner ZIP2つ、著者crosscheck、報告書）である。**実行済notebookは含まれない。** したがって実行済cellと承認notebookの比較は今回未実施である。これを行ったとは主張しない。

## 2. pseudoの独立受入れ確認
attempt `20261004T102334Z_6e681d78a0`。7原本fileのSHAを受入れJSONへ固定した。lock/final/run/log/NPZの対応、前回GOのsource、precheck/prelaunchに記録されたHEAD・clean tree・file SHAを照合した。最終PSEUDO_PASS/pseudo_passはTrue、rc0、fallbackなし、failures空であり、REQUIRED10の名前・順序・厳密bool Trueを固定scriptと照合した。

記録環境はpython3.13.15/NumPy2.1.3/SciPy1.16.3/healpy1.20.0/CAMB2.0.4/POT0.9.7.post1。pinsとEXPECTED_VERSへ照合し、保存されたBLAS情報を既存検査関数で確認した。**これは記録の照合であって、過去の実環境の直接観測ではない。**

NPZ本体を読み、未改変0.103.0の`verify_pseudo_columns`と再計算したcolumn identityで検証した。n=2000、m=1、T1/T2 float64・AX/PL int32・cid int64、UIDは[1,400,5001,0,i]（i=0..1999）である。順序、全有限、pairの対応、全列SHA、file SHA/bytesを確認した。記録されたroot SHAは登録D2 reference COMPLETE.jsonの`root_sha256/ref_matched`と一致した。principal rootを物理kernelから再計算した検査ではない。

正式NPZ: `c62a965b3b649870977d95ba247bf84a9580131109fc8572971e06b98da490f2`（145,444 bytes）

paired identity: `c9f75cdb86c90b0c73409a3e7a015faaef1e5903788358082dde3c21d66a1d15`

|列|SHA256|
|---|---|
|T1|`6e2669b529440d94a3808061788e3c0100b374075f319127914d4f7725af091d`|
|T2|`1a5588fd8dc3efb6cca7beaf446a3a88ffb9d3ff0b2835a2cf07751f4c3ee3d3`|
|AX|`60d61625987b85fac70befb1ad7a0f89c829b37e115cbccff6613c478616ddc7`|
|PL|`85a035007b2f831c9d4d84a8a9ad70264d5a9300f54d59d23b1f2a03ede343c3`|
|cid|`55f385cf2332d9056aaed6f496e7bebd2df52c6a9547ce2144b309432d4b0290`|
|uids|`cb90d89c16d8d06acc52c7aa5b043eae36c489d23d08037a3652e3ff56bf11ea`|

13の拒否対照では、NPZをコピーしてT1/T2のnextafter 1段階変更、T1/T2入替、全行逆順、T1だけsort、member欠落、float32、NaN、cid/UID/AX変更を検出した。変更後のfile SHAを正しく計算しても、信頼済みcolumn identityとは一致せず拒否した。原本は不変である。

### 環境間再生成の限定
Claudeのcrosscheckは、整数列/UID・root・keyが一致し、T1/T2だけ最終桁が異なると報告する。T1/T2の相違件数1739/1654、max relative約2.1e-15/1.3e-15（最大18 ulp）の数値は**著者の再生成報告**であり、本監査では独立再生成していない。crosscheckのColab側identityを実NPZと照合した。

小差が数学的な誤りや環境差のどちらに由来するかを今回新たに分離したものではない。accepted frozen sourceと正式環境記録・NPZ identityに基づいてColab原本を受け入れる。差の許容幅を使ってsandbox値へ置換したり、新しい値を選び直したりしない。

実測はscript 16.831秒、launcher込み 19.330秒。累積timingsの差で生成2.062秒・保存再検証0.048秒。RSS約1.19 GB/peak約1.32 GB、総RAM約13.61 GBである。W2の所要時間やRAM十分性をこの測定から保証しない。

## 3. D-2W失敗の事実・原因
attempt `20261004T102439Z_9bac8f8730`の6原本fileを確認し、失敗原本のSHAを判定JSONへ固定した。rc1、D2W_PASS/d2w_passともFalse、script stage=inputs、G_d2_inputs_resolved=False、8 preflight gateはTrue、後続gateは未実行のnullである。case/context fileとOT出力はない。

launcher finalのstage=completeは最終記録処理の完了を示すだけで成功ではない。fallback=True/gates_ok=False/evidence_ok=Falseであり、成功に昇格していない。前回受入れた厳密な成功契約が失敗recordを拒否した結果として整合する。

**『bankは一切読まれていない』という表現は、scriptの配列intakeに限定する必要がある。** stagingは既に303,031,554 bytesを31.4秒でコピーしている。script内では共分散intakeやW2配列intake・距離評価の前に止まった、が正確である。script約8.428秒/全体約43.022秒。

旧scriptは`d2reg.get("run_id") == fam_l["run_id"]`を要求していた。登録registry3つにこのkeyはなく、ledgerのrun_idは非空であるためFalseになる。旧scriptの入力段を未変更のまま関数に包み、finish/markの制御hookだけを置き、実登録metadataを与えると同じinputs停止を再現した。

staging/input bytesの破損が失敗を引き起こしたという証拠はない。少なくともこのschema不整合だけで停止は説明・再現される。実bankの全配列の健全性を今回改めて独立に確認したわけではない。

## 4. 0.104.0修正の確認
新`resolve_d2_inputs`は本物のTwelveContextからのD2 ledgerと、登録registryのbyte同一copy、27 unitのCOMPLETEを受け取り、3family/9case/27unitの解決に成功する。同じmetadataで旧入力段は拒否、新入力段はG_d2_inputs_resolved=Trueとなった。

正式経路はregistryのfile SHAをledgerのbank_registry_sha256へ結び、family/formal、unit manifest SHA、元run_root下の登録pathを照合し、要求COMPLETEの存在を確認する。staged物理pathを元Driveの文字列と無理に一致させず、byte identityと元登録pathで履歴runへ結び付ける。既存`assemble_w2_cases`の返却manifest照合・strong directory/array intakeは不変である。

独立19対照で正常、旧/new差、3つのregistry、family/root欠落・取り違え、registry byte変更（JSON意味不変の改行を含む）、symlink、ledger manifest/path/run_root変更、COMPLETE欠落を確認した。さらに、**metadata解決後も、NPZのないunitは実`intake_w2_position_bank(formal=True)`が拒否**した。placeholder rootはdirectory検査より先には使われず、数値root照合・OTはしていない。

全mainの正式経路を未改変で完走した試験ではない。提出のformal-main試験は外部資産依存でSKIPであり、それをPASSとして数えない。今回の独立試験は入力段の実コードとreal loaderの境界までである。

差分は追加20/変更13/削除0。定義単位では新resolver追加とmainの呼出し変更のみ。数値module、W2/pseudo notebook、pseudo script/表、1860登録資産は不変。6pinsはengine_versionだけ0.103.0→0.104.0である。

非blocking文書整理：最新報告§1のR-D4DESIGN-A行には旧『registryのfamily/formal/run_idを照合』が残る。registry bytes/ledger manifest/pathへ変更した説明と揃えればよい。報告書だけの再提出は不要。

## 5. 検査実績
|区分|結果|
|---|---|
|packet checker|2143 SHA一致|
|非実行compile|207 Python / notebook code 8セル|
|著者JUnit|18file・1772case・failure/error/skip 0|
|現source collect|1772件、checkout pathを含む2parameterのみ正規化して多重集合一致|
|未改変の提出pytest独立実行|113 PASS / 7 SKIP / failure,error 0|
|実行記録・NPZ照合|191明示check成功|
|入力解決・intake境界|19対照成功|
|NPZ改変拒否|13対照成功|

113 PASSはD4C0の92件と既往W2 context契約21件である。7 SKIPには新formal-main試験1件を含む外部資産依存が含まれる。全1772件の独立実行ではない。check数とpytest数を合算してpytest全PASSとはしない。

別の空workでも選択pytest、実行記録、resolver/NPZ対照、staticを再実行して同じ結果とsource不変を確認した。全工程を1回で起動した監査wrapperは45秒のtool制限で途中停止したため、残りを分割commandで実行した。失敗した正式runの数に含めず、重複試験数も加算しない。

初回監査harnessでは登録loader定数のfield名を誤参照してKeyErrorとなり訂正した。JUnit parserはtests/の補完と2件のparameter path正規化を訂正した。いずれも監査側コードの訂正であり提出sourceの欠陥ではない。

## 6. 再実行GOと登録条件
D-2Wのみ、次の固定値で再実行する。

```python
REPO_COMMIT = "f3aec79358452a293ccced14efd4f7e3ad240477"
EXPECTED_INVENTORY_SHA256 = "49976b3e24e27ee614c8e31bb2b292554cf550b95a189c96e9cd190fc92df6f2"
```

notebookは`d/MirrorTopology_Step1_D2W_cases_v0.1.ipynb`（内容v0.2、不変）。E2/E7/E8の元入力rootは失敗lockと同じで、STAGE_LOCAL=True、1run/9case、self-test flagなし、登録seed/定数/環境gateを維持する。古い失敗ZIPを保持し、今回は新attemptを作る。旧lockと混ぜないため新しいOUTを推奨する。

標準CPU/RAMは既存launcherのhard条件に従うが、9caseの完走・必要時間・十分性は保証していない。今回の修正はW2結果が生じる前の結果非依存の入力契約修正であり、旧attempt・原因・旧新sourceの履歴を残す。accepted pseudoは再生成しない。

1. Preserve the seven pseudo-run files, inner ZIP and original run/source/lock/environment as executed at 0.103.0. Do not replace the formal NPZ with sandbox-generated values.
2. Register the exact NPZ file and all column/paired identities, ordered UID, pseudo table, source lock, final/run records, logs, this acceptance and their full-byte SHA through receipt and pins.
3. Implement the actual registered loader and negative tests; REGISTRATION constants alone do not activate current stubs.
4. Keep the failed W2 attempt immutable and separate from the retry; preserve its source version, cause, stage and archive identity.
5. W2 and pseudo may have different historical execution commits. Validate each against its own accepted execution lock; do not rewrite historical locks to a common newer version.
6. Retain and provide executed notebooks at registration where available; they were not included in this results packet. No pseudo regeneration is required to supply documentation.
7. Do not use these acceptances as a GO for formal global calibration, target evaluation, labels, noise or ENGINE_VALID.

## 7. 未実施・保全
未実施：remote Git tree全面比較、過去Colabの直接環境確認、実行済notebookのcell比較、凍結kernelによる独立pseudo生成、正式W2 bank27unitの配列検証と9case exact POT、登録loader完成、正式較正/partial/combiner/usable/target。

current2576/previous2556の元fileと原ZIP、回収inner/outer原本は全bytes不変である。初回の監査importで作ったprevious内pyc18件は削除し、元のmember集合へ戻した。Drive接続・書込み、正式原本の修正はない。

## 8. 再現
付属`code/reproduce.py`にcurrent/previous/results ZIP、previous decision、存在しないoutを指定する。安全展開→checker→collect→選択pytest→run照合→resolver/NPZ対照→static→保全の順で実行する。ネットワークや正式bankの取得は行わない。監査環境: Python 3.13.5 / NumPy 2.3.5 / SciPy 1.17.0。これは登録Colab環境の再現ではない。
