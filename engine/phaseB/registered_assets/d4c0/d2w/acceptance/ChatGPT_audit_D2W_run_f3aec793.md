# D-2W正式実行 f3aec793 / engine 0.104.0：実行後受入れ監査
2026-10-05（JST）。Claude伝達・著者保存用。対象は添付原本と既に受入れ済みの固定source。監査側で新しい正式bankやOTを生成する作業ではない。

## 0. 判定
**PASS_WITH_EXPLICIT_SCOPE。D-2W正式実行（attempt `20261004T144349Z_cb8bc8e5f7`）を受け入れ、pseudoとW₂の原本登録・receipt/pins・registered loaderの起草と試験へGOを出す。新しい必須patchはない。**

科学的結果は5 caseのvalid/Falseと4 caseのw2-unresolved/unknownをそのまま固定する。unknown解消目的の再実行やseed・条件変更を要求しない。D-2W再実行、既存bank再生成、pseudo再生成、D-3c再実行は不要。

今回の受入れは、登録API完成や正式global較正、target/label、noise、partial/combiner、ENGINE_VALIDの承認ではない。以前のpseudo受入れJSONは変更せず、新しく届いた実行済notebookの確認を補足する。

## 1. 原本と固定値
| 対象 | bytes | SHA256 |
|---|---:|---|
| 今回outer packet | 5,676,775 | `a153d8300bf9d1f126e065f6717e6fb017c0cdec68620451a142e04af29e2af6` |
| 成功inner ZIP | 5,646,698 | `13e222e57d624473eba4fda045d400b34bf9a3fda6623fe74eacb1325a53a72b` |
| 固定source ZIP 0.104.0 | 16,814,344 | `df5eb95915a6b794c453eb74dbf30203b2e1fa116e1393ed533932e0c6f688a7` |
| 実行済D-2W notebook | 38,708 | `3d8a7ff7519e971b8981ff73256c2d975c8a7bc8ab11b7cc876c98a55807e89c` |
| 実行済pseudo notebook | 29,797 | `fb7a0d663694eac623a169006d9f0ac21c8a382213655ad357d9fbf938add973` |

実行commit：`f3aec79358452a293ccced14efd4f7e3ad240477`。
Inventory：`49976b3e24e27ee614c8e31bb2b292554cf550b95a189c96e9cd190fc92df6f2`。
Context：`50ec5a54d593d9bc53ce3661292d7dd3cb385369511a3444fda62226e77acb9c`。
本受入れJSON：`D4C0_D2W_f3aec793_acceptance.json`、file SHA `c9506e0b17f7ef17c3d1168e0acabdbba0195748060ca531b8c22305dbbd922a`。

ZIPのCRC、重複member、絶対/親path、symlinkを検査して隔離展開した。今回outerは5file、innerは16file（lock/final/stdout/stderr/run record/script log/contextと9 case）。原本memberごとの完全SHA/bytesは受入れJSONに保存した。内外の報告書はbyte一致する。

過去の比較基準は、この会話で受領/発行した実fileである。前回GO、pseudo受入れ、0.104.0 source ZIP、0.103.0 ZIP、旧pseudo ZIP・失敗ZIPも再使用した。今回の自己照合JSONの成功フラグだけを根拠にしていない。

## 2. source・環境・attempt・publication
記録/source/notebookの独立照合は**633項目成功**。具体的には次を確認した。

- lockのcommit/inventory/script/pins/D-2 ledger/shared-null asset/engineを、前回GOと固定sourceの実bytesへ照合。
- precheckとprelaunchの両観測のHEAD/clean/source hash/engineをlockへ照合。staging後の観測が残り、実引数は3つのstaged rootを使用する。
- attempt/lock SHAをscript record、final record、出力path、stdoutへ照合。self-test引数なし、production_official、rc=0、failuresなし、fallbackなし、正常schema/stage。
- scriptのASTからREQUIREDを取得し、保存13名前集合・順序、全値の厳密なTrue、required_all_trueとfinalへの転記一致を検査。
- 登録6版をpinsおよびofficial EXPECTED_VERSへ照合。保存BLAS情報を既存pool検査にも通した。これは保存された環境情報の検査で、監査環境がその登録環境であるとは主張しない。
- D-1 frozen loader SHA、TwelveContextのidentity、shared-null file/payload/whitening identityを固定sourceへ照合。
- published evidenceはcanonical9 case＋contextの10fileとexact set一致し、実bytes/SHAが一致。run summary/context summary/typed decisionのtrigger/state/B_final/manifest/result/checksumが対応する。
- stderrは空で、launcher stdoutにscript logが含まれ、D2W_PASS=Trueを記録。提出innerには当該attemptだけで、退避成功等の混入はない。

**記録された実HEADと過去の環境を、直接remoteから独立観測したという意味ではない。** remote Git tree全体の新規取得・比較は行っていない。

## 3. formal入力の束縛
3 familyのregistry実fileのSHA＝登録ledgerのbank_registry_sha256＝実行recordである。family/formal、元run id/root、各9unitを確認した。

27 W₂ unitについて、recordのmanifest SHA＝D-2 ledger unit＝登録COMPLETE.json、登録path＝元run_root下の該当unit、K=2000/m=100/rows=200000/formal/purpose/group/selectionsを照合。matched root SHAはCOMPLETE.jsonと一致し、D-1共分散27件のfile/array SHAとreceiptも登録metadataと一致する。

各unitのf64/f32 bank identity（計54）とstored evidence内の実行snapshotを照合した。cidの規則的な並びのSHAは、bankの科学配列を使わず別計算して一致を確認した。

**正式27unitのNPZ配列本体は今回結果packetに含まれず、当方で全配列を再読込み/再hashした検査ではない。** 受入れ済みsourceによる消費時の配列検査と、今回の入力identity・実行記録の対応を受け入れる範囲である。

## 4. formal復元と、保存値からの独立算術
承認済みsourceの`registered_shared_null_asset`でfile/payloadを検査し、未改変の`restore_w2_context(..., require_formal=True, expected_context_sha256=固定値)`で9 caseを復元した。`context_record`を再発行すると、保存context文書**全体**と一致した。manifest/result/9つのtyped decision/checksumとcontextが整合する。最初の復元計測は約6.75秒、監査環境はPython 3.13.5 / NumPy 2.3.5である。

さらにproductionのstop/validation関数を呼ばない別算術で、**393項目**を確認した。具体的には保存pairwiseから54 observed maxima、同じseed keyから162 observed subset vector、shared-nullの2,000 replicateのblock集合とpairwise最大値、整数順位によるhigherのq99、最初に停止条件を満たすBとtrace、seed spread、selection margin、最終state/triggerを検査した。

これは**保存された距離とboundを前提に、その後の手順を独立再計算したもの**である。exact POTの距離、whitened bank、f32 selection差/boundそのものを実配列から独立計測したわけではない。原本の距離・boundの認証は、固定source/元入力/実行証拠と本受入れへ依存する。

## 5. 科学的結果の固定
| case | state | trigger | B_final | q99(2000 / 5000) |
|---|---|---|---:|---|
| E2/L1.00 | valid | False | 400 | 0.2228809251 / 0.1559494867 |
| E2/L1.20 | w2-unresolved | unknown | 800 | 0.2298707482 / 0.1541943106 |
| E2/L1.50 | valid | False | 400 | 0.2228809251 / 0.1559494867 |
| E7/L1.00 | valid | False | 400 | 0.2228809251 / 0.1559494867 |
| E7/L1.20 | w2-unresolved | unknown | 600 | 0.2329460745 / 0.1532576819 |
| E7/L1.50 | w2-unresolved | unknown | 400 | 0.2228809251 / 0.1559494867 |
| E8/L1.00 | w2-unresolved | unknown | 400 | 0.2228809251 / 0.1559494867 |
| E8/L1.20 | valid | False | 400 | 0.2228809251 / 0.1559494867 |
| E8/L1.50 | valid | False | 400 | 0.2228809251 / 0.1559494867 |

9 caseともB-prefixのstop stateは`stopped`である。4 caseはB_max枯渇でなく、B_finalにおけるn_sub×3seedのabove/below indicatorが混在し、その後の安定性検査がw2-unresolvedとなる。5 caseのFalseも4 caseのunknownも改変しない。observed_hashは9件すべて異なり、q99の共有は同一shared-null prefixに由来する。

**Falseは「トポロジーunsupported」ではない。unknownも「すべてのpseudoが必ずunknown」ではない。** ここで固定したのはW₂ branchであり、D4のevent-ratio branchとの3値OR、必要な12位置段階、eligible truthの既存規則を適用する。推定上の未決をFalseとして捨てたり、技術FAILに付け替えたり、seedを変えて再試行したりしない。

## 6. 拒否系・回帰試験
実原本のcopyに対する**18改変対照はすべてInputContractErrorで拒否**された。正常な全9case・同じformal経路を先に成功確認してから実施した。

schema、非formal、別asset、family、重複/欠落case、別expected context、False→True、unknown→False、B_final、decision checksum、manifest SHAを変更した対照を含む。またresult SHAを正しく更新したpair distance、subset順序、bankのK/rows、null値、selection bound欠落、NaN距離も拒否した。subset順序の対照はcanonical subsetの意味検査だけでなく、固定expected contextへの不一致によって拒否されることをlogで区別した。

既存W₂ contextの未改変pytest：**21 PASS、failure/error/skip 0**。本監査で全1,772件を再実行したわけではない。source checkerは**2143 SHA項目一致**であり、科学計算や実行ログ真正性をそれだけで保証するものではない。

監査ハーネスでは、初期のtuple/list正規化とmetadata key参照を修正した後、633項目を最初から成功確認した。18改変を1呼出しにまとめた初回は実行時間上限で停止し、6件×3区間に分けて全18件を再実行した。これらを提出実装のFAILと数えていない。production sourceへのpatchや環境gate注入は行っていない。

## 7. 実行済notebookと、過去受入れの補完
D-2W/pseudoとも5cell（markdown1＋code4）。**編集用の最初のcode cell以外は承認sourceと完全一致**し、編集cellもAST比較でcommitとinventoryの2値以外は同一だった。execution_countは1..4、error outputなし。preflightの出力lock全文とSHA、attempt、script stdout、成功flag、ZIPサイズが各原本runと一致する。

D-2W notebookの元の著者file名に旧commitが入っていた点は命名上の事項であり、同梱版の内容/lock/出力は0.104.0の成功attemptに一致する。file SHAを保存し、renameを内容更新と扱わない。

pseudoは**0.103.0当時のZIP内notebook**と比較し、既存の受入れNPZも再検証した。旧受入れJSON `08efa1d19b29303425125aed71f96f0f27765c03234b36164f98ba4631cbee5b` と7fileはbyte不変で、今回のnotebookは追補証拠である。旧受入れJSONのlimitationsを後から書き換えない。

旧失敗W₂ ZIP `09f9ab0e8ade6c5f0b8cb53c7198bf20e9973618a8146c9647e9b57b9b98b037` と6fileも前回受入れ値に一致する。これは以前の添付から確認した原本であり、今回outerに旧失敗ZIPが同梱されているという主張ではない。

## 8. 資源の実測記録
- RAM total 13.606 GB（報告の約13.61 GB）、標準CPU。
- staging 303,031,554 bytes、32.9秒。
- script preflight 11.378秒、intake差分44.724秒、9case評価約731.010秒、publication/復元差分51.063秒。
- script合計838.176秒、attempt全体874.132秒（約14分34秒）。
- peak RSS 2,310.6 MB（約2.311 GB）、final RSS 1,615.9 MB。

時間の`timings`は累積値と`evaluation_seconds`を混在させているため、段階時間は差分で記した。これらは今回の測定であり、将来のColabやD4較正の十分性・所要時間を一般化しない。

## 9. 登録trancheへの実装条件
1. Register the exact successful inner ZIP, its 16 members, both executed notebooks and this acceptance. Preserve complete file bytes, not only the W2 context payload.

2. Retain the earlier pseudo acceptance 08efa1d19b29303425125aed71f96f0f27765c03234b36164f98ba4631cbee5b unchanged. The newly supplied pseudo notebook is supplementary evidence, not a replacement acceptance or a reason to regenerate columns.

3. Bind each run to its own historical execution lock: pseudo at 12980202ee111a26c0a608e7e5bba6caed5302ae / 0.103.0, successful W2 at f3aec79358452a293ccced14efd4f7e3ad240477 / 0.104.0. Do not rewrite source versions, timestamps, paths or old pins to the new registration version.

4. Retain failed W2 attempt 20261004T102439Z_9bac8f8730 and its original archive separately as failure history; never use it as successful W2 evidence.

5. Build deterministic ledger/receipt from accepted original bytes and bind acceptance, full-file identities, source locks, canonical case set, context SHA, unit manifests, covariance/shared-null/whitening identities, and pseudo column identity to registration constants and pins.

6. Implement actual load_registered_w2_context and load_registered_pseudo_columns bodies, not only fill REGISTRATION constants. Require all relevant pins including acceptance pins, rejecting missing/null/mismatch before returning an accepted view.

7. Authenticate full case/run/context/lock document bytes before replay. Obtain expected_context_sha256 from authenticated pins; do not use an editable record as its own trust anchor. Require the canonical nine case keys and preserve all 9 exact decisions.

8. For pseudo, authenticate the exact original NPZ plus dtype, count, m, ordered paired rows, UID and column/paired SHAs. Do not replace it by cross-environment regeneration or a tolerance-based equivalent.

9. Add normal roundtrip and negative tests for file alteration, rehash/reseal contradiction, missing/duplicate/mixed case, scientific unknown promotion, different asset, insufficient/formal-test bank, wrong execution/attempt, missing/null/wrong pins, failed attempt substitution and pseudo row/column changes.

10. Preserve W2 unknown as W2 branch uncertainty, not technical failure or false. D4 must combine it with per-pseudo event-ratio and registered 12-position completion before producing eligible truth; do not unconditionally mark or discard pseudo rows based on W2 state alone.

11. Present the registration/API implementation packet for review. This acceptance does not authorize formal global calibration, target release, labels, noise, partial/combiner acceptance or ENGINE_VALID.

## 10. 原本保全・再現
監査後もsource2,576file、今回outer5file/inner16file、以前のpseudo7file/失敗6fileのmember集合と全SHAが不変。故障注入はmemoryのcopyに限定した。pyc/pytest cacheの書込みを抑止した。

Evidence ZIPは`code/`、`results/`、`logs/`とREADMEを含む。`code/reproduce.py --inputs ORIGINAL_DIR --work EMPTY_DIR`で再現する。source ZIPやbankをevidenceへ再梱包せず、原本を入力として指定する。初回に必要な依存はPython、NumPy、SciPy、pytest、psutil等の既存source依存で、登録Colab環境を自動インストールするscriptではない。

**最終判断：今回のD-2W成功原本と9判定を受入れ、原本登録・registered loaderの起草/試験へGO。正式global較正・target評価は未承認。**
