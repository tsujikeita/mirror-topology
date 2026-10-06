# D4C-2a / engine 0.108.0 実装・実行境界監査
2026-10-06（JST）。添付実bytesについての監査。著者提示commit `4668b2e5cb645ff830db4bb6bb181d0c8ac3f960`。

## 0. 判定
**部分受入れ。計測版E2・先頭3 pseudo・High-RAMのprobeのみGO。screen→certificateはHOLD。**
Profilerの正常経路と分割の合成同等性を確認した。新しい証明経路は下記A〜Dの修正を要する。sub-partialの正式実行、family内・全familyの正式combiner、usable、Phase EのGOは発行しない。既存bank・D-3c・pseudo・D-2Wの受入れは維持し、再生成・再実行を要求しない。

## 1. 対象と保全
- ZIP：29,774,881 bytes、`a0fab34aa540b87bf927d9bd0fcb50f1bdc92e4695149ec91bfdaec4738b4b45`。
- inventory：`0702f6f9458f9922720a088d9ad47b596067276e91825d202469497fdc11d423`。
- 2,217 SHA項目を直接照合し全一致。Python218file、新規・変更notebook12code cellを非実行compileした。
- 前版0.107.0との差分は追加49・変更18・削除0。旧登録1,904fileは全bytes不変。
- probe ZIP・実行済notebook・旧報告・訂正報告・監査MD/JSON/evidenceの7原本を、この会話の元fileに直接照合して全一致。
- 新source2,726file・旧source2,677fileは監査後も不変。fresh source2,726fileも不変。
- remote Git treeとの全面比較はしていない。実行GOは上記添付bytesとinventoryに付す。

## 2. 正常系の確認
未改変pytest98件を実行：**90 PASS / 8 SKIP / failure・error 0**。
内訳：test_d4c2a.py 11PASS、test_d4c2a_script.py 9PASS/4SKIP、test_d4c1.py 19PASS、test_d4c1_script.py 51PASS/4SKIP。
分割は合成4行・2通りのtiling（chunk境界を跨ぐtrigger）で、一括family partialとprovenance・自己参照を除いたcanonical内容が一致。global pseudo_index、列とslice identity、archive refの内容と順序、family内結合→全family結合→単一calibrate_sealed比較、gap/duplicate/overlap等の拒否も通った。正式bankでの数値比較ではない。
計測有無の合成partialはpayload SHA一致。22targetのcall計測、segment、12位置branch帰属、正常exitでの復元が通った。実bankのhotspotや高速化率を測ったものではない。
8SKIPは生成器・frozen資産を要するscript end-to-end/拒否経路。代替probeの成功でPASSへ置き換えない。
著者JUnit29本は1,923case、failure/error/skip0。current collect1,923と、bare module名とnotebook絶対path表記を正規化した多重集合が一致。全1,923件を独立再実行したわけではない。

## 3. R-D4C2A-A：screenのgate集合がscriptとnotebookで不一致（blocking）
`d/d4c1_calibration.py:275`の共通準備は`G_d3b_units_accepted`をGへ追加する。しかしREQUIRED_SCREENは20件で、その名前を含まない。成功したscreen runは21keyとなり、notebookの厳密なkey集合検査に落ちる。
独立probeは、固定scriptからAST抽出した実際の代入をGへ適用し、未改変screen notebookのanchor/attempt cellへ渡した。20keyの正常fixtureは成功、scriptの21keyでは`gates_ok=False`。bindings/evidenceはTrue、停止理由は余剰gateだけだった。正常のstageあり/なし、欠落gate、非object文書、context不一致、source変更も併試験した（7 scenario）。Gitと子processはTEST-ONLY、実bankは計算していない。
修正：この検査をrequiredへ正式に追加してscript/notebook/AST期待値を揃えるか、不要なら診断領域へ分離する。厳密なgate集合照合を外す修正はしない。実際のscreen run形をnotebookへ受け渡す試験を追加する。

## 4. R-D4C2A-B：certificateの「環境gate外」が実装されていない（blocking）
REQUIRED_CERTIFICATEからG_env_lockを除いているが、mainの229行で、modeに無関係に環境不一致ならreturnする。certificate分岐は259行で、その後である。
提出mainの該当IfをASTでそのまま実行し、mode=certificate、環境不一致、skipなしではrc1/environmentになることを確認した。`--selftest-skip-env-lock`で進めてもselftest=Trueになるため正式COMPLETEにはならない。さらに現在の共通preflightはPhase Cとfrozen loaderを通るため、単にREQUIREDから項目を消しただけでは代数検証の独立性は得られない。
修正：certificate用の入口を分け、実際に必要な登録identity・入力証拠・source/定数の認証と、消費側環境の記録を行う。screen/partialの登録環境HARD gateは維持する。正式経路にself-test skipを使わない。別環境でのcertificate正常系と、同環境でscreen/partialが依然拒否される対照を追加する。

## 5. R-D4C2A-C：certificateが未検証の証拠を受理する（blocking）
### 5.1 evaluated入力
`_certificate`（548〜579行）はper_pseudo_statusを直接数える。`load_partial_record`/`verify_partial_record`やsubpartial版を呼ばず、archiveの存在、正しいschema、payload、参照鎖を要求していない。
正式列identityを使った明示的なTEST-ONLY fixtureでは、schema=THIS_IS_NOT_A_PARTIAL、archiveなし、任意の81unknown行、runはstage=exception/failures非空でも成功flagだけTrueなら、helperがG_sources_loaded=True、rc0で両levelの成功不能を返した。これはpreflight後のhelper境界試験であって、正式CLI/Colab実行が成功した証拠ではない。
より実体的な対照として、今回の合成試験が生成した実partialを読み、unknown→Trueとpayload SHAだけを変更した。元のreaderは参照先からの再導出不一致で拒否したが、certificate helperは受理した（smoke n=4の対照）。
### 5.2 screen入力
screenは内部checksumと算術を調べるが、runのpublished_evidence SHA/bytesやrun summaryとの一致、REQUIRED gates、source、正式scope等を検証しない。`D4C1_SCREEN_COMPLETE=True`と列identity/campaign等の少数項目だけで受理する。
### 5.3 screenの十分条件の完全性
`check_screen_record`（135〜167行）は記録内に存在するstageだけを走査する。正式な3position×N0/N4の全被覆を必須にしていない。
合成count対照（N0:P=.1、N4:P=.5）では包絡比5でblocking=False。同じrecordからN4を削除し、summaryを比1へ更新しchecksumを再計算すると、checkerがblocking=Trueを受理した。この形式を81行にし、旧publication SHAや失敗run情報を残しても、certificate helperが両levelの成功不能を作った。実bankからのscreenや物理的判定の反例ではなく、不完全な証明記録を拒否すべき入力境界の反例である。
修正：
- 認証対象のrun/record/lock/source/attempt/campaign/列identityとpublication SHA/bytesを照合し、正式かつ正常な信頼済みREQUIRED inventoryを要求する。
- evaluatedは実archiveと既存reader（registered/current-source相当の正しい実行source認証）を通してからeligible truthを使う。
- screenは登録family/size/config/position対応、正式N0/N4の完全被覆、hits/N/P、実pseudoの該当行threshold、登録W2 decision/checksum/contextを照合する。screenの自己申告context SHAだけで決めない。
- certificateのcheckerが何を検証するかを明確にし、証拠認証と純代数の内部整合を分離する。証拠の不明・欠落をunknownの科学結果へ読み替えない。
- 全recordを敵対者が自己整合的に偽造した場合の暗号的真正性まで要求する話ではない。既存workflowと同じ、固定source・受入れidentity・実行証拠・参照鎖の検証をこの新consumerでも維持する。

## 6. R-D4C2A-D：family集約とlevel別閾値（blocking）
### 6.1 異なるfamilyの違いは矛盾ではない
現在はrowだけで証拠を統合し、familyをキーにしていない。E2のunknownとE7のTrue、E2のTrueとE7のTECHが、conflicting proven statusesとして拒否される。これらは別familyとして両立する。元のany-family契約ではTrue/unknown/TECHを所定の優先で扱う。
同一(row,family,level)の証拠同士をまず整合させ、その後rowごとに全familyからblockingを合成する。同一familyにおける矛盾は引き続き拒否し、同じglobal行を二重計数しない。screenのunknown_or_technicalは「技術FAILがなければunknown、TECHならusable自体が成立しない」という限定を保つ。別familyのTrueを理由にTECHの可能性を消さない。
### 6.2 閾値の値集合ではなく、名前と値の対応を固定する
197行は値が(.05,.01)のいずれかかしか見ない。`thresholds={support:.01,strong:.05}`が受理され、12行でsupport不能とする。現在のCLI defaultは正しいため、通常のdefault出力が逆になっているという指摘ではない。public APIが「登録閾値しか受け付けない」という契約を満たしていない。
`{support:RULES.usable_support,strong:RULES.usable_strong}`との完全一致をconstructor/checker両方で要求する。level内thresholdとtop-level mapping、technical件数/flag、算術statementも再導出へ一致させる。

## 7. 計測probeへの限定GO
対象：`d/MirrorTopology_Step1_D4C1_partial_v0.1.ipynb`（内容v0.3）。
```python
REPO_COMMIT = '4668b2e5cb645ff830db4bb6bb181d0c8ac3f960'
EXPECTED_INVENTORY_SHA256 = '0702f6f9458f9922720a088d9ad47b596067276e91825d202469497fdc11d423'
FAMILY = 'E2'
PROBE_N = 3
ROW_RANGE = None
INSTRUMENT = True
STAGE_LOCAL = True
```
完全な入力root、既存commitment/campaignは`results/execution_settings.json`。nonceは含めない。
正式intake/12位置live gate等の検査を維持し、最初の3対の順序・定数を変えない。probeは正式PASSへ昇格しない。新しい実行済notebook、lock、run/final record、全archive、stdout/stderr、profile JSONとそのreceiptを保存する。profileのsegment=3、missing_targets=[]を実行後に確認する。
A〜Dはこのpartial計測経路では実行しないため、今回の限定GOと分ける。sourceを修正して新commitになれば本GOを自動流用しない。High-RAMの最低条件は十分性保証ではない。

## 8. 非blockingの注意
- outside_segmentsをすべて固定費と呼ばない。evaluate_family_fullの後の行別archive putはsegment外である。TEST-ONLYの軽量evaluatorでN1/N3を通すと、segment外putが1/3回と増えた。計測自体は有用であり、今回のGOでは「segment外処理」として読み、別途固定/反復保存を区別する。inclusive時間を足し合わせてtotalとしない。
- Profiler.__enter__途中でalias不一致が生じると、既設置のinactive wrapperが残る。entry例外時のrollbackを推奨。default inventoryの正常経路は通っており、今回の固定probeを止める理由にはしていない。
- envelope_screen_familyのrowsはintへ変換してからboolを調べるため、public APIの型検査は変換前に行うのがよい。CLIのrow-rangeは別途検査される。
- 報告冒頭の「実行GOを求めない」は現在の依頼と不一致。本判断は現在の依頼に従う。
- chunk250〜500はまだ実行承認しない。前回313.9sの素朴な掛算だけでも約21.8/43.6hであり、安全なchunkの実測ではない。計測後に行数を決める。

## 9. 限定・再現
正式bank配列のintake、全2000行screen、正式較正、Colab登録環境、remote Git、実targetは未実施。不能証明の成立行数やusableを今回認定しない。
独立probe：screen notebook7scenario、certificate境界9scenario、実合成partialのreader対照、mode guard・profiling会計/cleanup。これらはpytest件数ではなく、正常と拒否不足を区別してJSONに保存した。
別の空sourceで独立境界3scriptを再実行し、同じ結果を得た。全選択pytestをfreshでも再実行したという主張ではない。
証拠ZIPのcode、results、logsを参照。`code/reproduce.py`は固定ZIPからの再現入口。今回の結論は、不能証明の数学的提案の撤回ではなく、その根拠を検証するconsumerと実行境界の補修要求である。
