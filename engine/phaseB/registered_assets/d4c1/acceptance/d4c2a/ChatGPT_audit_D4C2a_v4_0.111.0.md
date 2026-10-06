# D4C-2a v4 / 0.111.0 監査
## C1・C2・D1・履歴guard受入れ／新bridge比較器は修正待ち／実行GOは保留
2026-10-06。Claude引渡し用。対象は添付packetの実bytesであり、remote Git treeの認証ではない。

## 0. 判定と範囲
前回のcertificateに対するC1/C2/D1とhistory pin guardは、今回の実装・独立検査の範囲で受入れPASSとする。環境amendment v0.2の文書・比較契約は、前回の条件を反映しており受け入れる。

ただし、新しい `d/d4c2_bridge_compare.py` は契約全体の成立を宣言するには検査不足があり、比較器の実装受入れはHOLDとする。実際の0.110.0 bridge probeの新結果も今回未提出なので、数値bridge受入れとscreen→certificateの実行GOは未発行。

既存bank・D3c・pseudo・D2Wの受入れは維持。今回の指摘のために、それらや0.110.0のbridge probeを再実行する必要はない。比較器を修正し、同じ原本を再読込みすればよい。0.110.0の固定probe GOは維持し、0.111.0へ移さない。

## 1. 実体
- commit（著者提示）：`59b0e7b8bd01ccde1d3be92745aa8144e36e146c`
- ZIP：`phaseB_D4C2a_v4_0.111.0.zip`、30,684,188 bytes
- ZIP SHA：`56f0f4252c9753e00d43ef00bd33760a9a7215e5d3bc4931cfd57d479bef3aa1`
- inventory SHA：`9bd99e271aaa5d762410cd2e73f7be07f2c35932583baa8b7232df2b92944293`
- ZIPの重複member、絶対/親path、symlink、CRCを検査して隔離展開した。
- inventory内の2,232 file SHAを照合し不一致なし。Python220file／notebook12code cellを非実行compile。
- 前版0.110.0の登録資産1,914fileは全bytes不変。以前の受入れ文書の登録8fileは、この会話の元ファイルとbyte一致。
- 定義単位のdriver差分は `_certificate` のみ。数値kernel、第1波screen計算、partial実行、notebookは不変。`infeasibility.py`はtyped比較とFalse保持・計数等、`official_gate.py`は履歴guardが変わる。

## 2. C1：信頼済みREQUIREDへの照合（閉鎖）
`_certificate.trusted_inventory/run_ok`はmode別の固定定数を使う。受領した一覧を正解として使わなくなった。gate集合・厳密なTrue・profile・source及びtop-level pins/engine・attempt・probe/instrument・相互排他的flagの検査を確認。

独立検査は、前回の人工count/source fixtureを、今回の正常producer形式へ適応したもの。登録W2/pseudo/gridは本物だがcountは人工であり、実bankの証明ではない。正常1件を先に確認し、gate削除・envのみ・余剰・順序・整数1、失敗stage、空attempt、誤pins/profile等23改変をすべて拒否した。

さらに提出の関数本体をASTでそのまま取り出し、4mode各1正常＋16不正＝68呼出しが期待どおり。これは外側契約試験であって、4modeの正式bank end-to-endではない。

実CLI `--mode certificate` もPhaseC/mt/env skipなしで、登録loaderと12gateを通過しrc0となった（同じTEST-ONLY人工screenに対する動作確認）。正式なblocking行が81件あるという結果ではない。

## 3. C2：W2 summary（閉鎖）
`bind_screen_record(w2_decisions=...)`は認証済みcontextから`w2_triggers`で再導出し、`typed_equal`で完全比較する。期待checksumを維持したB_final800→400、trigger False→unknown、validation_state変更、B_final800→800.0を再stampしても今回拒否された。N4欠落・threshold改変・config不一致・stale publicationも拒否。

W2原本及び4unknownは変更されていない。old結論を都合よくFalseへ替える修正ではない。

## 4. D1：False証拠（閉鎖）
新しい `evaluated_rows_from_statuses` が全行を保持し、矛盾検査と計数を分けている。

未改変の提出試験が生成した実合成E2 partial/archived Resultを新readerで認証し、4行すべてFalseから n_rows=4, n_false_rows=4, n_blocking_rows=0、行0..3をすべて保持した。同family同rowのscreen unknown_or_technicalを加えると拒否、別familyなら両立して1行だけblockingとして計数した。restampしたeligible truthはarchive不一致で拒否。

4値×4familyの256組合せは既存any_family_truthに一致。閾値swapはconstructor/checkerで拒否。登録固定n=2000の81/12境界も維持。

## 5. 履歴guard・amendment v0.2（受入れ）
`registered_environments(pins)`はhistory欠落/null/非list/件数違い、6版・registered_until・key集合・非空amendmentを検査する。独立14種類×2関数＝28呼出しで拒否。amendment名のみ別の非空metadataへ替えると許容され、文書の契約と一致。

登録D4C0/D3cの82回帰pytestはPASS。大きなplan再構築1件は意図的に除外。旧履歴を読む検査であり、新Python3.13.16での数値計算ではない。

amendmentの修正は、全体SHA一致を要求せず、15科学的per-row recordと指定内容を一致させ、source/環境を別々に検証する前回契約に沿う。実数値bridgeは結果未提出で未了。

## 6. 新bridge比較器：既に機能している範囲
0.111.0の比較scriptを外側に置き、`--phaseb`には元ZIPから展開した未改変0.110.0を指定し、前回の比較specそのものを渡した。著者のfixture生成手順を0.110.0に適応したTEST-ONLY『新probe』は、15科学recordをbaselineから保ったままsource/provenanceだけを組み立てたもの。この入力で旧producerのown reader/current_source_bindingまで通ることを確認した。

これは本物の新runや環境間の数値一致の証拠ではない。比較scriptがproducerと違う版に置かれても、指定した旧treeのreaderを利用できることの確認である。

著者のbridge7pytest（現在treeの合成fixture）はすべてPASSした。欠損科学file、変更科学field、古い環境、False gate、profile欠落、余剰archiveを拒否する既存機能はある。

しかし、以下の未検査項目がある。

## 7. R-D4BRIDGE-A-PRODUCER-PROVENANCE（必須修正）
場所：`d/d4c2_bridge_compare.py:92–113`及び`_unpack`。

`new_run_gates_all_true`は len(req)==24 と受領req/gatesの相互一致だけで、producer scriptの固定REQUIRED_PARTIALと比較しない。`G_inputs_resolved`を双方で架空名に置換しても、24件のままならrc0/BRIDGE_CONTRACT_SATISFIEDとなった。受領一覧の逆順も通る（この対照は報告するが、主要な問題は信頼済み名称の未照合である）。

同じ合成fixtureの独立変更で、次も契約成立と表示した。
- source.pins_sha256を不一致にする。
- attempt_idをrun directoryと異なる値へ替える。
- outer lockを別commit、不正inventoryにし、finalをexit1/fallback/失敗prelaunchにする。
- run.twelve_gateをpassed=False、injected_test_snapshot、required failureありにする。

比較器はouter lock/final/precheck/prelaunchを読まない。生成treeのreaderはpartialそのものの参照鎖を検証するが、producer run全体のこれらの状態を代わりに認証しない。前回のcertificate C1は閉じており、これは新scriptに独立して存在する同種の不足。

修正：承認されたproducer treeのREQUIRED_PARTIALをAST等で取得し完全照合。実pins/script/inventoryとrun/lock/finalを結び、attemptとdirectory、正常rc/fallback/失敗空、precheck/prelaunchの固定source、live official twelve gateを検証する。新旧原本のepochを混同しない。bridge比較器をproducer treeへコピーしてsourceを書き換えず、外側から実行する。

## 8. R-D4BRIDGE-B-TYPED-INDEX-IDENTITY（必須修正）
場所：同script `resolve` とper-row照合（132–159行付近）。

新archiveのfamily_result indexでpseudo_indexの整数0だけをJSON falseへ変更した。科学recordのbytesは変えない。比較器はrc0/契約成立とし、own readerも成功した。

Pythonでは False==0 であり、値の比較だけではtyped identityの契約を満たさない。specにある完全identity・kind・row/sizeを型付きで比較し、global rowは整数かつboolでないことを要求する。欠落/余剰/重複を合わせて確認。helperは比較器自身へ置く等、0.110.0に存在しない0.111.0の新関数へ依存しない方法を採る。

これは数値結果や行の計算が実際に変わったという試験ではなく、specが要求するtyped metadataを認証していないことの確認。

## 9. R-D4BRIDGE-C-PROFILE-DOCUMENT（必須修正）
場所：同script104–106行。

profile本文を missing_targets=[TEST_MISSING_TARGET], instrumentation.cprofile=False に変更し、正しい新file SHA/bytesへrun.profile_recordを更新した。run.profile_summaryにはmissing_targets=[]、segments=3を残す。今回もrc0/契約成立となった。

実装がmissing_targetsを読むのはrun summaryだけで、profile本文のcoverage/設定と照合しないため。profile本文自身のmissing_targets、wrappers/cProfile、producerのtarget inventory、per_segmentの数・index・countと要約の一致を検査する。既存のfile hash/bytes照合は維持。正常fixtureも完全なprofile構造で作る。

## 10. エラーreport（併修推奨）
partialをJSON nullにするとrc1だが未処理AttributeErrorとなりreport JSONがない。通常のparse/contract/reader例外は安全な保存先へ不一致reportを発行するよう補強を勧める。OS強制終了まで記録保証するものではない。成功の誤受理とは異なる診断性の問題。

## 11. 実行の扱い
1. 固定0.110.0で進行中/完了したbridgeは、元のGOに従って保存する。今回の比較器の問題で科学計算を繰り返さない。
2. 比較器だけを直し、同じ新旧ZIP・元spec・生成treeで再検証する。15recordのSHA/bytes一致や比較条件を緩めない。
3. raw結果、実行済notebook、lock/final、profile、比較reportを実行後監査へ提出する。比較scriptのrc0だけで数値bridge受入れとはしない。
4. screen/certificateは、数値bridgeの確認と修正版source固定の後に実行可否を判断する。現certificateはproducer/current同一sourceを要求するため、修正前のscreenを先行生成して新版のconsumerへ無理に渡さない。
5. 完了certificateも固定nの成功不能に関する別scopeであり、正式較正完了、c/u/rate、usable=False、PhaseE解放を意味しない。

## 12. 実行実績と限定
- 提出新規3file：29PASS/7SKIP。うちbridge7件はPASS。
- 登録回帰2file：82PASS、大規模plan consumer1件は明示除外。
- 合計111PASS/7SKIP、FAIL/ERROR0。全1,935件を再実行したわけではない。
- 著者JUnit30本：1,935件、failure/error/skip0。現在sourceのcollect1,935と多重集合一致。module表記と絶対notebook path6件を正規化した。
- 追加certificate境界24シナリオ（人工正常1、改変拒否23）＋実CLI。68producer関数対照、28history呼出し、256truth組合せ、実合成4False行のreader対照。
- bridge独立11シナリオ：旧producerでの合成基準、上記不正受理、正常なgateFalse拒否、nullでのreport欠落など。追加probeをpytest件数へ混ぜない。
- fresh workではguard/algebraの2scriptのみ再実行して一致。全選択pytestや全bridge対照のfresh再実行ではない。
- 原本：新source2,744、前版2,728、fresh2,744 fileは変更なし。
- 監査環境：Python3.13.5 / NumPy2.3.5 / SciPy1.17.0 / pytest9.0.2、4GiB制限。登録Colab環境ではない。
- 未実施：実Python3.13.16のbridge計算、正式bank intake/再fingerprint、exact POT、実2,000screen、実certificate結論、正式較正、実観測target、remote Git tree照合。

## 13. 再現資料
付属code/results/logsに実行内容を保存。source ZIPと元比較specはユーザー原本を利用する。bridge fixtureはbaselineの科学recordから作成したTEST-ONLYデータで、実環境bridge成功として登録しない。失敗注入はコピー上のみ。
