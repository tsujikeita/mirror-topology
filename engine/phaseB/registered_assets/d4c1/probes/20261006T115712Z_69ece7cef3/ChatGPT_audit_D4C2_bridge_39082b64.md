# D4C-2a：実 bridge probe の受入れと、固定0.112.0 screen → certificate の実行判断

2026-10-07（JST）

## 結論

**固定0.110.0／commit `39082b641d8621989ae69a273f4e88e0c59673ba` のE2・登録pseudo先頭3行の数値bridgeを、事前固定した比較契約の範囲で受入れPASSとする。** Python 3.13.15から3.13.16への環境amendment v0.3について、当該bridgeの受入れ条件が満たされた。

**既に監査した0.112.0／commit `ba51e5951ebb8c16c7106247408c912d86944675` に固定し、E2 → E7 → E8の各2,000行のscreenと、その3つの成功screenを認証して読むcertificateへの実行GOを発行する。** 詳細は別紙 `D4C2_screen_certificate_0.112.0_execution_decision.json`。実行結果の科学的受入れは別である。

追加の必須patch、bridge再実行、既存bank／pseudo／D-2W／D-3cの再生成・再実行は要求しない。正式partial／sub-partial／global combiner／usable／Phase E／実観測targetの実行・承認は含めない。

## 1. 今回の入力と差替え

最新版として `D4C2_bridge_probe_report(1).md`（SHA `265e218d08c5c117a0f5d2b1c7fa9f88f4212a89a82a34dc7b563ff5794f4b9f`、7,730 bytes）を使用した。旧版の「notebook未受領」は、この報告では実行済notebookのSHA・bytes・出力記録へ置換されている。

その他の再送3ファイルは、それぞれ前の添付とbyte同一であることを直接比較した。報告の差替えを、科学的raw結果の改変として扱わない。旧MDは履歴のまま保持する。

| 原本 | SHA-256 | bytes |
|---|---|---:|
| 新bridge ZIP | d5bb91b103fa33c6e1ae3764e47aa4e3e2ae3e0326fb4966c0cad52978329ded | 523671 |
| 実行済notebook | 88ac16fb64074d9995be82ab964a07e6e313b363cc1dba8af9678da06be691a8 | 49671 |
| 著者比較report JSON | cf72b217eec1624fee40aafea8f5cfaf71c460c03a315cca0918b9e9c14b1bef | 19756 |

ZIPは26ファイル。lock／final／outer stdout・stderr、attempt directoryのrun／partial／profile／log、archive index＋17 entryを含む。CRC・path安全性・重複pathなしを確認。全memberのSHAとbytesを `results/new_run_file_map.json` と受入れJSONに固定した。

## 2. 比較器を実raw結果へ再適用

受入れ済み比較器（0.112.0）を外側から使用し、`--phaseb`には元v3 ZIPから展開した未改変0.110.0 treeを指定した。spec・baselineも元の固定bytesを使用し、`--expected-commit`を完全値で明示した。producer treeへ比較器をコピーしたり、0.112.0のreaderで代用したりしていない。

| 対象 | SHA-256 |
|---|---|
| 比較器 `d/d4c2_bridge_compare.py` | ca545b61c8b867ec2c36210a77012b2a93b125a2cd04d193e4b8e68ce93fc605 |
| producer ZIP 0.110.0 | 3ae56bf1d4911e0955b312e5b44335d9a3398d5dab0b654d713e4fce7e677646 |
| producer inventory | 7df1fb5948eb2c0c0d379a37afa93c0f1dbc0bba77c01c49d6be60665d9bb1ba |
| 元比較spec | a9cb9ab9b622cb0d929006eac01a957003a5eeffef990a40de8c6338a0981373 |
| baseline ZIP | 538f5e07f3c4fae84803d17783ff09a03fef5270cd04b600376e2af891644766 |

**独立再実行はrc0・36/36成功・不一致0。** 著者の比較JSONとも、実行時刻・ローカルpathを除いた意味内容が一致した（科学的SHA値は別の直接比較でも検査）。0.110.0自身の `load_partial_record`／`verify_partial_record(registered=…, current_source_binding=True)` が成功し、publishedとarchivedが一致した。

新しい空workへ展開して同じ実ZIPを与えた再実行でも36/36成功。再実行回数を検査件数へ二重加算していない。

## 3. 数値bridgeとして受け入れる内容

### 3.1 完全一致

事前のspecで固定された15件について、型付きidentity・pseudo行と参照関係による対応、file content SHA、bytesが一致する。

- family_result：3件。
- three_position_result：9件（各pseudo×3 size）。
- pseudo_family_plan transition：3件。

直接のbyte比較でも新旧15件が一致した。registry entryも同一で、archiveは一意な17件。残る1件はpartial全体のtransitionであり、新provenanceによりSHAが変わる。

partialの19個の `required_equal_partial_fields` と、不変の入力dependenciesも一致した。登録pseudo NPZ本体を読み、閾値T1／T2が元の先頭3対と一致することも別途確認した（再生成ではない）。

全3行のcore truthはFalse、eligible truthはsupport／strong／unsupportedいずれもunknown、12位置評価は0。科学的unknownは旧結果と同じであり、bridgeの不一致・技術FAILではない。これを理由に再試行・W₂の再生成・Falseへの昇格を行わない。

### 3.2 全体SHAの差は予定されたprovenanceの差

旧partial payload：`057ae75355fd7a716aba9d52d5a520275c9c6fd3b57162a4e7d389e327223878`

新partial payload：`774951eacb3e60e8408f582fc194847ba66191c095ee4a9a026922305680a322`

新partial archive file：`32e7a96e7b7f36575c03bc2d308112569951b2d362e13a9e141b88688e375505`

engine0.107→0.110、module SHA、Python3.13.15→3.13.16の記録が変わるので全体SHAを同じにすることは要求しない。各原本をそれぞれのsource／epochへ検証したうえで科学的内容を比較した。旧metadataへ書き戻す変更はしない。

### 3.3 範囲

これは**固定E2先頭3行で実際に通った数値経路のbridge**である。未発火のN4適応、KDE-CI、12位置の数値評価、全2,000行、E7/E8全体の環境間同等性を証明しない。次のscreen実行GOは、この限定bridgeに加え、既に受け入れたscreen実装・固定入力・各新runのHARD gatesを根拠とする新しい工程判断である。

## 4. 実行証拠・notebook・入力metadata

対象attempt：`20261006T115712Z_69ece7cef3`。

- 固定producer scriptから抽出した24 REQUIREDと、runの一覧・gate集合が一致し、全値が厳密なTrue。
- rc0、stage complete、failures空、fallbackなし。probe／instrument True、正式PASSはFalseのまま。
- lock、run、final、attempt directory、publication、precheck／prelaunchの記録が同じproducer commit／inventory／script／pinsに一致。
- 記録された環境はPython3.13.16・NumPy2.1.3・SciPy1.16.3・healpy1.20.0・CAMB2.0.4・POT0.9.7.post1。旧gateは履歴3.13.15へ、new gateはcurrent3.13.16へ照合。BLAS pool記録も規則を満たす。
- run.twelve.gateはofficial／passed／required_failures空／live_collected。実bank gateの全計算を監査環境で再実行したわけではない。
- 72供給（18 first-wave＋54 added）のmanifest、reference、cluster数を元D-2／D-3b ledgerに直接照合。入力rootも登録runと一致。NPZ本体の全読込みは実行していない。
- 実行済notebookは編集用最初のcode cell以外、markdownを含め承認sourceと一致。編集cellは承認値へのliteral assignmentのみ。実行count1,2,3,4、error outputなし。出力lock全文、lock SHA、child stdout末尾3,000文字、attempt・status、ZIPサイズがrawと一致。
- **stderrは空ではない。** ログ初期化とCUDA driver不在・GPUを使わない旨の4行が残っている。CPU実行・rc0・required gate成功と矛盾しない。finalのstderr_tailにも一致し、消去・空扱いはしていない。

## 5. 計測結果の解釈

| 項目 | 記録値 |
|---|---:|
| attempt全体 | 3742.718秒 |
| staging | 530.4秒／12,329,718,617 bytes |
| script | 約3208.7秒 |
| 計測対象partial | 2598.457秒 |
| evaluate_family_full 3 segment | 合計786.608秒 |
| segment別 | 269.026／258.885／258.696秒（丸めは元JSON参照） |
| segment外 | 1811.850秒 |
| peak RSS | 16052.8 MB（十進：約16.05 GB） |

profile本文は22 target、segment index0..2、missing_targets空、cProfile表とreceipt・run要約の対応が正常。new sourceの計測器を新規に較正したという主張ではない。

`input_fingerprint`の42呼出しはすべてsegment外にあり、inclusive1752.461秒。source上も14個のFamilyInputを調べる `fps_all()` がloop外で3回呼ばれている。この42呼出し部分は、固定したview集合ではpseudo行数に直接比例しない。

ただし、segment外には行毎のarchive保存もあり、全体を固定費とは呼ばない。自作wrapperのself／inclusiveとcProfileのtottime／cumtimeは異なる会計であり、再帰・入れ子のinclusiveは重複する。たとえばto_jsonableの自作wrapper self約1221.7秒を、input_fingerprintのinclusiveへ単純に加算しない。

各row側ではresample_hitsの2160呼出し・約496秒、_family_Qの48呼出しが記録されている。一方、hit_tablesは3024呼出し・約37.2秒。この計測runでは優先調査対象を絞れるが、wrapper／cProfileが3億回規模の再帰呼出しへ入るoverheadを含む。非計測baselineの313.9秒／pseudoとの比を性能向上・劣化や正式予算の倍率として使わない。

**今は高速化patchを同時に入れず、固定0.112.0のscreenを先に進めてよい。** screenはhit-countの十分条件を調べる別経路であり、各行のQ bootstrap／KDE／12位置全評価を実行する正式較正ではない。screen自身の全2000行の所要時間・RAMはまだ未実測で、今回のbridge時間から保証しない。

## 6. screen → certificate：実行sourceの固定

新しくコードを修正する必要はない。前回受入れたv5 packetをそのまま実行対象とする。

```
REPO_COMMIT = "ba51e5951ebb8c16c7106247408c912d86944675"
EXPECTED_INVENTORY_SHA256 = "aa2c11cc01df09fc9cd130a2c0b9aa5af75d1b2acc27f47aef3d5d91d0bb2b77"
```

較正driver SHA：`814557791d7f295fbb981c20806c7374ddf7ae19148380c41c004afef3e597b0`

screen notebook：`d/MirrorTopology_Step1_D4C2_screen_v0.1.ipynb`

notebook SHA：`ca9c263ac5cc6ab398eb948c443404af310d0d89a2aae55cef4760dc5a5f6acb`

pins `d/d3_pins.json` SHA：`1d03bc5f83d41a2bf75d817cf7d6b9d29caf856740a4f87dc9e8d303a7e172d2`

**bridge producerは0.110.0のまま保持し、screen/certificate producer・consumerは0.112.0で揃える。** sourceを一つに見せかけるため過去recordを書き換えない。今回の受入れ文書を実行中のtreeへ加えてinventoryを変えない。まずrepo外で本判断を固定し、同一sourceのscreen/certificate完了後、履歴を保った登録trancheで追加する。

### 6.1 screen

E2 → E7 → E8、各1 run・登録全2000行 `[0,2000)`・元のpaired順序。ROW_RANGE=None、STAGE_LOCAL=True。High-RAM CPUを安全側の運用として勧める（notebookの>10GBは最低条件であり十分性保証ではない）。同じscratch／stage pathを共有するので並列起動しない。

| family | D2_RUN_ROOT |
|---|---|
| E2 | `/content/drive/MyDrive/MirrorTopology_D2/E2_20260923T092030Z/out/d2` |
| E7 | `/content/drive/MyDrive/MirrorTopology_D2/E7_20260923T125656Z/out/d2` |
| E8 | `/content/drive/MyDrive/MirrorTopology_D2/E8_20260923T174910Z/out/d2` |

全3 size×3位置、N0=1,000,000／Nmax=4,000,000の元bankを使用する。D-3b rootsや12位置bankをscreenへ追加しない。新規出力先の例は `OUT_ROOT=/content/drive/MyDrive/MirrorTopology_D4C2_screen_0_112_0`。familyを替えるごとにpreflightからやり直し、lockを作る。

成功条件は20 REQUIRED全True、正式scope・selftestなし・正常完了、`D4C1_SCREEN_COMPLETE=True`。blocking行の多寡は成功条件にしない。未判定行をFalseにしない。入力／環境／source等の不一致・技術FAILは失敗attemptとして保持し、seed・条件を変えて科学的に都合のよい結果へ引き直さない。

lock、final、run、screen record、stdout/stderr、実行済notebook、元ZIPを保持する。

### 6.2 certificate

3つの成功screenが正しいfamily・全2000行・同じ0.112.0 source／campaign／commitmentであることを確認してから、同じsourceの専用CLIへ渡す。`--screen`は各outer出力folderではなく、run／screen recordがある**実際の `run_<attempt>` directory**を指定する。

```
python "$PHASEB/d/d4c1_calibration.py" \
  --phaseb "$PHASEB" --mode certificate \
  --screen "$E2_RUN_DIR" --screen "$E7_RUN_DIR" --screen "$E8_RUN_DIR" \
  --target-commitment 9efa1b8d82fec2e23ac685d24dbaece7932e29955c94fc5a2955ba793c70b326 \
  --campaign-id D4C2_9efa1b8d82fe \
  --out "$FRESH_CERTIFICATE_OUT"
```

`PHASEB`は上の0.112.0 tree。3つのRUN_DIRと新しい出力先のみ、実生成pathに合わせる。`--mt`／`--phasec`／`--probe-n`／`--instrument`／self-test flagsは付けない。今回のGOでは`--evaluated`を使わず、旧bridge・probeを正式証拠へ昇格させない。certificateは登録計算環境のHARD gateを要求せず、消費環境をmetadataとして記録するが、source／証拠／登録identityの検査は維持する。

12 REQUIRED全True・rc0・`D4C1_CERTIFICATE_COMPLETE=True`は**証明文書の作成処理の完了**であって、不能証明が成立したという意味とは別。不能証明がTrueなら、固定分母2000で残りを最も有利に補完してもusable=Trueは不可能という範囲。c／u／実測率／全件技術成功／正式usable=False／sealed較正完了を主張しない。不能証明がFalseなら、この十分条件では決着しないだけで、usable=Trueとは言わない。

support81・strong12のblocking境界と、同じglobal行を重複計数しないこと、TECH／possibly_technicalの区別を維持する。E1をFalseとして除外したglobal較正は行わない。実screen/certificateの結論は、raw結果を回収した後に別途受入れ判断する。

## 7. 今回の検査実績・限定

- 受入れ済み比較器の実rawへの独立再実行：36/36成功。
- 独立のraw・notebook・source・metadata等：272/272成功。
- source inventory直接再hash：producer2219、pipeline2237、全一致。
- 実行済notebook：承認されたliteral設定と非編集cellのsourceを検証。出力のlock・stdout末尾・attempt・ZIP sizeも照合。
- 実runコピーへの改変対照4件：REQUIRED名入替、profile missingの再hash、indexのbool化、科学的record bytes変更をすべて拒否。前2件は外側のrun/final hashを整合させたうえでsemantic検査により拒否。
- 0.112.0の未改変selected pytest：5 PASS、0 FAIL／ERROR／SKIP、8 deselected。Wilson境界・混合prefix・certificate集約・履歴環境・W₂ summary。全1953 suiteは再実行していない。
- fresh work再現：同じ実ZIPで36比較・272直接照合成功（件数二重加算なし）。
- 保全：producer2728・pipeline2749・新run26・旧run25ファイル全bytes不変。

初期の独立harnessのschema/path修正、batch対照実行のtool時間制限と個別継続は `results/audit_process_notes.md` に記録。これらを提出scriptのFAILや本番再試行として数えない。

**未実施**：正式bank配列の全再読込み・実fingerprint再生成、巨大plan再構築、物理kernel、exact POT／f32 bound、監査環境でのColab/Python3.13.16再現、過去runtimeの直接観測、remote Git tree全面比較、実2000行screen、実データcertificate、正式較正、実観測target。

受入れは、固定source、認証した登録入力identity、原本実行証拠、own reader、事前固定した15件の完全一致を根拠とする。次段の実行GOは、これを全経路の一般的同等性証明と読み替えるものではない。

## 引渡しファイル

- `D4C2_bridge_39082b64_acceptance.json`：数値bridgeの受入れ、原本全member SHA、15科学record、限定。
- `D4C2_screen_certificate_0.112.0_execution_decision.json`：固定sourceと実行GO／非GO、停止条件。
- `D4C2_screen_certificate_0.112.0_execution_settings.json`：family別の完全入力rootとnotebook設定。
- `D4C2_bridge_39082b64_audit_evidence.zip`：再現code・独立比較JSON・直接照合・refusal／pytest結果・file map・保全記録。
