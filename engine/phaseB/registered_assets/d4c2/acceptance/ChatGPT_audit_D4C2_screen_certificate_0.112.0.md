# D4C-2a screen／certificate 正式実行結果の監査（固定0.112.0）
2026-10-08。対象：`D4C2_screen_certificate_0.112.0_results.zip`と提出報告書。

## 1. 判定
**3件のscreenと、認証済み証拠に基づく固定campaignの成功不能certificateを受入れPASSとする。原本登録trancheの起草・実装・試験へGO。追加の必須コード修正および再計算は不要。**
ただし、正式global較正の完了、実測c/u/率、正式`usable=False`の発行、Phase Eや実観測targetの解放は認定しない。登録loader自体の完成も次packetで判断する。

受入れ対象ZIP：SHA-256 `567092dae35b2a9f8ba64ef28af000b680546502b69c890d22af756d309a7cc7`、1,894,673 bytes。
固定producer/consumer：commit `ba51e5951ebb8c16c7106247408c912d86944675`、engine0.112.0、inventory `aa2c11cc01df09fc9cd130a2c0b9aa5af75d1b2acc27f47aef3d5d91d0bb2b77`。
前回GOの実file SHAは `0477d7b2fb546634c3444cb0613aef993d181730e4556cbfc97f6116f5473282`。reportの基準と一致。

## 2. 原本・実行証拠
outer ZIPの15fileと、3 inner ZIPの計21memberを検証。ZIP CRC、重複・絶対path・..・symlinkを検査して監査用directoryへ展開した。提出file_mapの13entryとinner member mapが実fileのSHA/bytesに一致し、外側reportはZIP内reportとbyte同一である。元の教授側bundle自体は未添付なので、その伝送段階は独立認証していない。

3 screenでは、前回GOに指定された設定とlock、lock実SHAとrun attempt/final、finalが参照するrun実SHA、sourceのinventory/script/pins/engine、9登録資産fileのSHA map、precheck/prelaunchの記録、20件の固定REQUIRED、各bool True、正式scope、成功flagと他flag False、終了コード0・fallbackなし・失敗欄空を照合した。保存環境6版とBLAS poolも一致する。現在のColabへ接続した検査ではなく、保存された実行証拠の検査である。

D-2入力は3 runと登録ledgerのrun_id/run_root/commit/registry SHAが一致。全27 configuration×両systemの54供給に含まれるeval/ref/fit manifestをledgerへ直接照合した。D-3cのplan identity/UID identity/定数の保存値が登録profile ledgerと一致し、screenのfingerprintsがrun側のfirst-wave fingerprintsと一致する。実bankからのfingerprint・plan配列の再構築はしていない。

実行済notebook3本は、最初の編集用code cell以外のsourceが承認版と一致。編集値は前回GOの設定と一致し、execution count1～4、error outputなし。表示されたlock（登録資産mapはnotebookの表示仕様で省略）・lock SHA・attemptがrawと一致した。CPU実行のstderr4行は原本のまま保存されている。

## 3. 全行screenの再検証
未改変の`bind_screen_record(formal=True)`を実行した。真正な`TwelveContext`、登録loaderから復元したW2Context、原本NPZから取得したpseudo2000対、登録config idを使用し、各行thresholdとW2要約4field（型込み）の束縛を再確認した。各screenは[0,2000)を一度ずつ完全に覆う。

さらにproductionのscreen計算関数とは別の監査loopで、保存されたhit数から次を再計算した。
- **108,000件**の`P=hits/N`：整数・非bool・0<hits<=N、N0=1,000,000/N4=4,000,000、prefix差分の上限/下限を検査。
- **18,000件**のsize包絡：各3位置×2prefixのmin/max/比/正値性/summaryを再導出。有理数の交差比較でもmax<=2minを確認。
- **144,000通り**の位置別混合prefix選択（各包絡の2³通り）：実際の保存率を用いて、選択された比<=包絡比<=2を確認。
これは元NPZからhit数を再カウントしたものではない。

| family | attempt | 行数 | blocking | 最大包絡比 | 最小P | 全体時間 | peak RSS |
|---|---|---:|---:|---:|---:|---:|---:|
| E2 | `20261007T113430Z_d4d346bde9` | 2,000 | 2,000 | 1.145669291339 | 0.0002005 | 1023.065 s | 8450.9 MB |
| E7 | `20261007T143438Z_a2d3767433` | 2,000 | 2,000 | 1.103682170543 | 0.0002100 | 733.952 s | 8450.6 MB |
| E8 | `20261007T145023Z_6a25812f53` | 2,000 | 2,000 | 1.158505154639 | 0.0001840 | 1053.892 s | 8450.1 MB |

すべてのfamilyで全sizeにW2 Trueはなく、少なくとも1つのunknownがある。count-envelopeの十分条件は全6,000family-rowに成立する。global pseudoは同じ2,000対なので、独立pseudo数または分母を6,000へ増やしてはならない。

## 4. certificateの独立再実行
未改変0.112.0の`d/d4c1_calibration.py --mode certificate`を新しいCLI processで実行し、3つの実run directoryを渡した。env-skip/selftest/stand-in/--evaluatedは使用していない。rc0、12gate True、`D4C1_CERTIFICATE_COMPLETE=True`で完了した。

新しいローカルpathを使うため、`sources[].dir`とそれに依存するcontent SHAは原本と異なる。それ以外のcertificate内容・入力参照metadataは一致した。別に、各sourceのfile SHA・run SHA・attempt・publication・登録bindingを認証したうえで原本の出典metadataを維持して再導出すると、**元certificate文書とcanonical bytesまで完全一致**した。

受入れcontent SHA：`4a249ee06929b514bfc2f60881ab1c5073518b30c1c2e3667b26621327066557`。
受入れfile SHA：`0c910b32243e1c2305ad9dfcdc0e6ca06de37397164eeaf79554c554fe20920b`（2,871,232 bytes）。

| level | 閾値 | 最小blocking件数 | 確認したglobal blocking | known TECH | possibly TECH | 成功不能 |
|---|---:|---:|---:|---:|---:|---|
| support | 0.05 | 81 | 2,000 | 0 | 2,000 | True |
| strong | 0.01 | 12 | 2,000 | 0 | 2,000 | True |

Wilson式は別の監査式でも境界81/12を確認した（演算の括り方による最終bit差はあり、境界結論は同じ）。`WilsonUpper(2000,2000)=1`も一致する。

## 5. no-goの論理と射程
### 5.1 正しく主張できること
固定されたbank・W2判定・pseudo2000対・grid・判定規則に条件付けた**calibration-usability no-go**である。
各行でscreenが証明するのは`unknown_or_technical`であって、正式な評価完了statusではない。全required評価が非技術的に完了するなら各screened familyのeligible truthはunknown。E1がTrueならglobalはTrue、E1がFalse/unknownならglobalはunknownで、いずれもc+uへ1を加える。E1または他のrequired経路にTECHがあればglobal較正は技術的無効でusable=Trueを発行できない。

よって、非技術的完了の場合は**条件付きでc+u=2000**、保守的上端1が両閾値を超える。技術FAILを含む完了でもusable=Trueは得られない。これは全行の正式c/u/率を実測したという主張ではない。

今回、E2/E7/E8の**いずれか1familyだけの証拠でも2,000global行を覆う**ことを再導出した。3familyは互いに同じ行の補強証拠であり、6,000試行の較正ではない。E1をFalseとして省略する仮定も不要である。

### 5.2 報告書§5の括弧書きには訂正が必要
「W2 unknownのsizeが各familyにある限りglobal較正はusableに到達できない」という省略は強すぎる。**unknownの存在だけでは、event-ratioのTrueから全sizeを12位置化して未決を解消する経路を排除できない。**
今回成立した理由は、(i)unknownあり・W2 Trueなし、(ii)登録全2000行で全size/position/N0/N4の正値包絡<=2、(iii)固定された位置拡張・eligible/TECH集約規則、の組合せである。報告書§2・§3の説明はこの範囲を保っている。原本reportは変更せず、登録時に別erratumを追加する。これはコード・実行結果の受入れをHOLDにする指摘ではない。

### 5.3 何のno-goではないか
Theme Tの物理的問い（観測Event Bの裾確率をトポロジー模型が等方模型より改善するか）そのものに対する否定証明ではない。今回targetを評価しておらず、観測でのQ/logD、模型のsupported/unsupported、トポロジーによる説明不能は示していない。すべての将来pseudo集合、別bank、別W2手続、強制12位置fallback、別統計量に一般化しない。真のfalse-support率が100%であるとの推定でもない。

論文向けの記述案：
> 本研究で固定したMonte Carlo資産、観測者位置の判定規則および2,000組の等方擬似観測に対し、E2・E7・E8の全行で、3位置とN0/Nmax両prefixにわたる正の事象確率の包絡比が2以下であることを確認した。各familyに登録済みW2未決caseが存在し、W2による拡張の確定Trueがないことと合わせ、各行は既定の適格性判定ではunknown、またはrequired計算失敗時にはtechnical_failとなる。したがって固定分母による保守的なany-family較正はsupport/strongのいずれでもusable=Trueへ到達できないことを、全行のQ/KDE評価を完走することなく証明した。この結果は当該登録手続の較正可用性に関する成功不能証明であり、宇宙のトポロジー一般や観測異常のトポロジー起源を否定するものではない。

### 5.4 次段への意味
同じ原登録の下でusable=Trueを得る目的だけの重い較正完走は、この証明により不要と判断できる。一方、実測c/uや別の科学的量を得たい目的まで否定する証明ではない。手続を変更して再検討する場合は、閲覧済みW2/probe/screen/certificateを開示した別amendmentで扱う。今回のGOはその変更や再生成を許可しない。

## 6. 登録tranche条件
1. 原本ZIP・全member・実行済notebook・command/stdout/stderr/rc・提出report・file_mapと今回の受入れをbyte同一で登録する。既存bridge原本とその別受入れも維持する。
2. 成功screen 3件とcertificateは0.112.0の実行source・pins・path・時刻・各attemptへ固定する。登録時にengine/inventoryが上がっても旧recordを新版へ再ラベルしない。
3. ledger/receiptは原本と今回の受入れ文書から決定論的に再導出し、受入れ文書自身を含むpinsを入口で要求する（wrong/missing/nullの拒否）。
4. certificateの純粋な算術checkerと証拠認証を分離する。登録loaderは原本bytes、producer lock/final/run、信頼済みREQUIRED、source、publication、W2 decision全文、paired列、行被覆を認証する。
5. 登録loaderは保存evidenceから再導出する。将来の新版で厳密な現source条件を一律に外さず、認証済み履歴sourceと今回の受入れidentityを根拠とする専用経路にする。
6. screen/certificateをsealed_calibrationや正式partialとして登録・消費しない。unknown_or_technical、technical_rows=0の限定、global rowの一度だけの計数を維持する。
7. 科学的結論は固定資産・固定2000行・固定判定手続の成功不能に限定する。W2 unknownだけを十分条件としない。原本reportの強すぎる括弧書きは別erratumで訂正する。
8. 拒否試験：原本改変、gate欠落、旧版混在、family/attempt混在、N4欠落、W2 checksum保持の要約改変、行/threshold/paired列変更、2000を6000とする二重計数、閾値入替え、不能証明のsealed昇格を拒否する。
9. 登録packetの実装受入れは別途。今回のGOは起草・実装・試験/原本保管であり、Phase Eやtarget解放、規則変更・W2/pseudo再生成の許可ではない。

## 7. 検査実績・限定
- 直接照合：**470項目、失敗0**。inventory **2,237 SHA**（別計数）。
- 全保存率108,000、包絡18,000、混合prefix144,000の算術確認。これらもpytest件数ではない。
- 未改変certificate CLIの実rawからの再発行：rc0。原本由来metadataを固定した再導出は元documentとbyte同一。
- 実原本のコピーに対する改変対照**17件すべて拒否**。screen7件/certificate4件/producer predicate6件。最後の6件は固定sourceのASTをそのまま実行するpost-preflight境界試験であり、各々の全CLIを起動した件数ではない。
- 既存の選択pytest **5 PASS、FAIL/ERROR/SKIP0**。全1,953件の再実行ではない。
- 提出source **2,749file**、結果outer展開 **15file**、inner展開 **21file**は全bytes不変。差替え・生成は監査用出力のみ。
- 監査harness初版には返却tupleの取り扱いとnotebookの表示形式の2誤りがあり、監査コードだけを修正した。元のstderrも証拠に保存。producer不具合や提出試験FAILには数えない。
- 正式D-2 bankのNPZ本体は結果packetに含まれず、当方はhit数を実配列から再走査・再測定していない。保存された108000件のhit/N/Pからの算術確認である。
- 実bankのinput_fingerprint、巨大bootstrap planの再生成、物理kernel、exact POT、KDE/12位置の正式較正は未実行。
- 過去Colabの実HEAD/環境の直接観測、remote Git treeの全面照合は未実施。記録された観測値と固定sourceの実bytesを比較した。
- 全1953 pytestは再実行していない。選択した既存5件のみ全PASS。追加の17改変対照と470項目の直接照合はpytest件数ではない。
- 元の教授側bundle d4c1_results.zipは未添付。そこからの転写経路とbundle SHA自体は独立検証していない。添付された3 inner ZIP・3 notebookの実bytesは直接固定・照合した。
- fresh workではcertificate CLIのrc0と科学的内容一致を確認したが、その後の一括監査は180秒のtool制限で中断。完全なfresh監査再現とは数えない。
- 当方のcertificate再実行環境はPython3.13.5/NumPy2.3.5/SciPy1.17.0。healpy/POT/CAMBは未導入でmetadataはnull。専用certificate入口は数値生成環境HARD gateを要求しない設計であり、skip flagやstand-inは使用していない。

## 8. 再現
証拠ZIPの`code/reproduce.py --inputs <原本添付のdirectory> --work <新規directory>`を使用する。必要なsource ZIP・結果ZIP・前回GO JSON・今回reportのSHAを確認し、別workへ安全に展開して、未改変certificate CLI、直接照合、拒否対照を実行する。正式bank不要。長時間の再現は通常の端末で実施し、時間制限による中断を成功に読み替えない。
