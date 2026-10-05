# D4C-0 登録 tranche / engine 0.105.0：原本登録・ledger／receipt・registered loader 受入れ監査

2026-10-05（JST）。Claude伝達・著者保存用。対象は添付の登録packet。正式較正の実行結果ではない。

## 0. 判定

**PASS_WITH_EXPLICIT_SCOPE — 原本登録、ledger／receiptの再導出とpins束縛、W₂／pseudoのregistered loaderを実装受入れとする。新しい必須コード修正はない。**

前回受け入れたpseudo生成（0.103.0）とD-2W成功実行（0.104.0）は、原本・科学的結果ともそのまま維持する。失敗attemptは別の失敗履歴として保持する。bank、pseudo、D-2W、D-3c profileの再生成・再実行は要求しない。

D4C-1（接続script、専用family partial、combiner）の起草・実装・試験へ進んでよい。**D4C-1の完成受入れ、正式global較正、usable、Phase E／target評価、label、noise、ENGINE_VALIDのGOは含めない。**

本監査は添付bytesに付す。提示されたremote Git commitのtreeを全面取得・比較した監査ではない。

## 1. 受入れ実体

| 対象 | SHA-256 |
|---|---|
| phaseB_D4C0_reg_0.105.0.zip（28,369,767 bytes） | `6b1e367d45d2977bd904dc7fbc634dd9fb32fbbda88adc68ddb43bc1fa5ff937` |
| B2_completion_inventory.json | `8f0ee2552d45bcf53cd0df1ba837fde47914154a6137633c232a67df986c0d3d` |
| step1_engine/d4c0_registry.py | `246680a664159d801ec15f10680862e48bd1615c02abed02c2193f64d0ae24a9` |
| d4c0_ledger payload | `8c0d39f98401718e8e63128b8802e614fc99701a5564b0b1ab75489422241452` |
| d4c0_outer_receipt payload | `d6926b94dcb1bede33019bb222b094575a1d15b17e7dfc912056512e25a29056` |

著者提示commit：`86015f0f6b77bf6c0111b4faf20a5b3dc402c300`。engine 0.105.0。現source 2,642 file、前版0.104.0は2,576 file。

ZIPのCRC、重複member、絶対path／親path／backslash、symlink memberを確認して隔離展開した。外側reportはpacket内の同名文書とbyte一致。inventoryのSHA項目2,189件が一致し、公式checkerも成功した。Python 209 fileと両notebookのcode cell計8件を、実行せずcompileした。

## 2. 前回原本との直接比較

比較基準は新module定数や新ledgerだけではない。過去に提出された次の原本を別に読み、照合した。

- `D4C0_runs_12980202_audit_packet.zip`：pseudo成功ZIP、旧D-2W失敗ZIP。
- `D2W_run_f3aec793_audit_packet.zip`：D-2W成功ZIP、実行済notebook2本。
- 当会話の元のpseudo／D-2W受入れJSON、監査報告、修正版GO JSON。

| 登録された原本 | 直接比較 |
|---|---|
| pseudo成功inner ZIP、7 member | 元ZIPとbyte一致、member集合一致、全member byte一致 |
| D-2W成功inner ZIP、16 member | 同上 |
| D-2W失敗inner ZIP、6 member | 同上。失敗のまま別directoryに保持 |
| 実行済notebook2本 | 前回提出の原本とbyte一致 |
| 受入れ関連文書5本 | 当会話の元fileとbyte一致 |

登録原本は **39 file**（inner ZIP3＋member29＋notebook2＋受入れ関連5）。これにledger JSON／receipt JSON／receipt MDを加え、`registered_assets/d4c0/`は **42 file** である。全39原本のpathとSHAを判定JSONに保存した。

従来の登録資産 **1,860 file** は全件不変。新規追加以外に原本の削除はない。pseudoの実行lockは0.103.0／12980202、D-2W成功lockは0.104.0／f3aec793であり、現在の0.105.0へ書き換えていない。

## 3. ledger／receiptの再導出と7 pins

### 3.1 正常再導出

提出試験を未改変で実行し、`build_d4c0_ledger`の決定論的再導出、committed ledgerとの一致、payload SHA、`verify`／registered loadを確認した。receiptも原本からの再導出とcommitted JSONに一致し、ledgerのpayload SHAとfile SHAの双方へ結び付いている。監査側probeでもこの二重の対応を確認した。

原本fileの完全なSHA／bytesを先に要求するため、case recordの付随情報まで含めて認証される。復元できるmanifest／resultだけを根拠に原本全体を認証したことにはしていない。

lock／final／run recordは当該attempt、正式scope、正確なREQUIRED inventoryとbool True、環境記録、precheck／prelaunchへ結び付く。D-2W入力metadataは既存D-2 ledgerへの束縛を保持し、成功と失敗の原本は混在させない。受入れJSONの実bytesと内容は信頼した定数へ照合する。

ledgerとreceiptに登録版0.105.0を新たな実行版として記録しないことを、提出試験と独立probeで確認した。

### 3.2 pins検査

7項目は以下である。

| pin | 固定値 |
|---|---|
| d4c0_ledger_sha256 | `8c0d39f98401718e8e63128b8802e614fc99701a5564b0b1ab75489422241452` |
| d4c0_outer_receipt_sha256 | `d6926b94dcb1bede33019bb222b094575a1d15b17e7dfc912056512e25a29056` |
| d2w_acceptance_sha256 | `c9506e0b17f7ef17c3d1168e0acabdbba0195748060ca531b8c22305dbbd922a` |
| pseudo_acceptance_sha256 | `08efa1d19b29303425125aed71f96f0f27765c03234b36164f98ba4631cbee5b` |
| d2w_context_sha256 | `50ec5a54d593d9bc53ce3661292d7dd3cb385369511a3444fda62226e77acb9c` |
| pseudo_paired_sha256 | `c9f75cdb86c90b0c73409a3e7a015faaef1e5903788358082dde3c21d66a1d15` |
| pseudo_npz_sha256 | `c62a965b3b649870977d95ba247bf84a9580131109fc8572971e06b98da490f2` |

新規試験の7 pin×wrong／missing／null＝21 caseは全PASS。registryの両consumer loaderと、w2_cases／d4_pseudoの公開wrapperでも拒否を確認している。未信頼context、別rootの指定については監査側12対照でも拒否された。

**層の区別**：共通guardはacceptance2件・context・paired・NPZの5項目を定数と比較し、ledger／receiptの2項目は存在・形式を検査する。値の照合は対応するregistered loadで行う。このため、64文字だが誤ったreceipt pinだけを与えた場合、ledger-only loadは成功し得る。一方、receipt loadと両consumer loadは拒否する。この分担は提出試験にも明示されており、消費経路に未検査のpinは残っていない。全7値をledger-only loadが検査すると表現しない。

純粋なledger builderと、pinsを検査するregistered loaderも区別する。外側receipt builderはregistered ledger loadを通るので、「すべてのbuilderが全pinsから独立」とはしない。

## 4. registered loaderの実動作

### 4.1 W₂

両入口（registry／w2_cases wrapper）を実行し、正式原本9 caseを復元した。consumerの最終読込みでは、認証した同じbytesをparseしている。実際に`restore_w2_context`へ渡す引数を観測したところ、expected contextは上記認証済みpin、`require_formal=True`、case数9であった。

復元結果はcontext SHAと全9 decisionが受入れ定数と一致。5件はvalid／False、次の4件はunknownのままである。

| case | state | trigger | B_final |
|---|---|---|---:|
| E2/L1.20 | w2-unresolved | unknown | 800 |
| E7/L1.20 | w2-unresolved | unknown | 600 |
| E7/L1.50 | w2-unresolved | unknown | 400 |
| E8/L1.00 | w2-unresolved | unknown | 400 |

このloaderは保存済みevidenceからの正式replayであり、exact OTや元bankの配列読込みを再実行するものではない。監査側の追加正常試験では、生成／OT入口を「呼べば失敗する」sentinelへ置いたままloaderが成功することを確認した。これはscopeの確認であって、OT計算の独立成功を数えたものではない。

### 4.2 pseudo

registry／公開wrapperを通して原本NPZを読み、T1／T2／AX／PL／cidの全配列とdtype、2,000行のUIDが元NPZと一致することを確認した。UIDは `[1,400,5001,0,i]`、i=0…1999。paired SHAを再計算して固定値と一致した。

NPZ file identityは145,444 bytes、上表のc62a965b…である。同じ値の配列から別の圧縮方式で作ったNPZも、原本bytesと違えば拒否した。環境間の許容差や再生成した列を正式列へ差し替える経路ではない。

### 4.3 返却objectと原本の分離

返却viewの編集はmodule定数と復元済みcontextへ伝播しない。返却pseudo配列・UID・identityを編集しても、登録NPZとmodule定数は不変であり、次のloadは元の列を返すことを確認した。

ただし、**返却されたNumPy配列が永続的にimmutableであるとは認定しない**。D4C-1では、較正が実際に使う列のidentity・順序を監視し、編集された返却objectを、過去のload成功だけで認証し続けない。既存の入力固定条件を維持するための注意で、新しいblockingではない。

W2Contextの保持resultを変更したりdecisionを除去した場合は、実際のvalidate／decision_forの入口で拒否されることも確認した。

## 5. 原本改変・読込み境界の独立対照

提出の26 caseの原本編集拒否試験は全PASS。case/context/run/final/lock/archive/notebook/acceptance、失敗attemptの成功への差替え、NPZの値・順序・dtype、ledger／receiptの再stamp等を検査している。これらは信頼済み原本bytesへの束縛を含む拒否である。未知の任意攻撃をすべて網羅するものではない。

監査側の追加45項目では、正常loadと上記の返却object分離に加え、次を確認した。

- context payload自身には含まれないcaseの`inputs.units`／`constants.m`／bank UIDの付随情報を編集した場合、正式原本bytesの不一致として両consumerが拒否する。
- 最終fileをsymlinkに差し替える場合を拒否する。
- W₂ consumerが正しい原本bytesを捕捉した直後に、そのpathのbytesを変更する試験では、今回の返却contextは先に認証したsnapshotに一致する。次回loadは変更されたpathを拒否する。

最後の試験は一つのcaseの最終read境界を確認したものである。全tree全fileを一度だけ読む、あるいは全工程に原子的なsnapshotがあると認定したわけではない。故障注入はprivate copyまたはprocess内だけで行い、提出原本は変更しない。

## 6. 差分と前回条件1〜11の対応

数値kernel、生成／評価script、両notebook、pseudo表とD-2 CRN表は前版と不変。`w2_cases.py`／`d4_pseudo.py`の定義単位の差分は、loader本体と登録定数の取得helperである。`checkpoint.py`には新moduleのsource inventory登録、`__init__.py`には版表示の変更がある。旧test_d4c0の未登録stubに対するassertも、登録後の状態へ更新されている。

| 前回条件 | 今回の確認 |
|---|---|
| 1–2 原本とpseudo追補notebook | 前回packet／当会話原本へ直接比較し全39file一致 |
| 3–4 実行版の分離・旧失敗の保持 | 歴史lock保持、失敗6member＋ZIP別保持、代用を拒否 |
| 5 ledger／receipt | 原本再導出、committedとの一致、完全内容検証 |
| 6 各pin・実loader | 7項目×3異常をconsumerで拒否、stubは実loadへ置換 |
| 7 W₂原本認証・正式replay | 9caseを定数bytesで認証後、expected pin・formalで復元 |
| 8 pseudo原本 | exact NPZ、n/m/dtypes、全UID・paired順序を照合 |
| 9 正常／拒否試験 | 提出53case全PASS、追加45対照も成功 |
| 10 unknownのscope | 4件を維持、W₂ branchとして後段へ渡す |
| 11 次段を分離 | 今回は登録API。D4C-1完成・正式較正は未承認 |

## 7. 試験実績

| 群 | 実績 |
|---|---|
| 提出された新規registration試験 | **53 PASS、0 SKIP** |
| 既存D4C-0＋D-2 snapshot/context契約試験 | **113 PASS、7 SKIP** |
| 既存W₂ context契約試験 | **21 PASS、0 SKIP** |
| 未改変pytest独立実行の合計 | **187 PASS、7 SKIP、failure/error 0** |
| 追加の監査側loader／snapshot等 | **45項目成功** |
| 原本・metadata直接照合 | **50項目成功（39原本の対応を含む）** |
| 公式packet checker／独立inventory計算 | **2,189 SHA項目一致** |
| 著者JUnit 19 file | **1,825 case、failure/error/skip 0** |
| sourceからのcollect | **1,825件、明示的path正規化後にJUnitと多重集合一致** |

著者の全1,825件を当方で独立再実行したわけではない。7件のSKIPは外部資産依存（凍結kernelを使う生成／script／formal-main等）であり、登録53件はskipなし。既存W₂ contextの21件は契約試験であり、今回の正式bankによるexact POTではない。

collectとJUnitの差は、notebookの絶対pathをparameterに含む2件のcheckout rootである。比較ではそのprefixのみを明示的に正規化した。未加工の文字列の完全一致とは表現しない。

監査環境：Python 3.13.5、NumPy 2.3.5、SciPy 1.17.0、pytest 9.0.2、Linux/glibc 2.41。登録Colab環境を再現したものではない。

## 8. 非blockingの文書整理

報告書冒頭の「原本40 file＋ledger／receipt JSON＋receipt md」は、現在の登録treeと直接比較では **原本39 file＋派生文書3 file＝42 file** である。必須原本の欠落はなく、件数表記を次の文書更新で揃えればよい。この件だけの再提出は不要。

またpins拒否の説明では§3.2のledger-onlyとreceipt/consumerの分担を維持し、7項目すべてをledger-onlyで値検査すると拡大解釈しない。

## 9. 未実施・受入れの限界

正式W₂ raw bankの再読込み、exact POT・selection boundの再計算、凍結kernelによるpseudo再生成、Colab runtimeの再現、remote Git treeの全面比較は未実施。今回の正式replayとNPZ読込みは、**受入れ済み原本を新しい登録APIが正しく認証・消費できること**の確認である。

返却objectの将来の未監視変更まで、load時点の成功で認証し続けるものではない。D4C-1では認証したidentityを実際の較正入力へ結び付け、前後の不変性を検査する。

## 10. 再現・保全・次段

付属`code/reproduce.py`は、指定した入力directoryから固定source ZIP2本を安全展開し、原本照合、checker、collect、提出53件、関連134 PASS／7 SKIP、追加probe、source不変検査を行う。生成・OT・Driveへのアクセスは行わない。必要な元packet／acceptance類の一覧はREADMEに記載する。

初回のmetadata検査harnessに、fixture pathの誤記とZIP directory entryの数え方の誤りがあった。どちらも監査側harnessを訂正し、全metadata検査を再実行した。初回logも証拠ZIPに残す。提出コードのFAILや修正要求として数えていない。

**最終判断：登録APIを受入れPASSとし、D4C-1の接続実装・専用partial／combiner・同等性／拒否試験へ進んでよい。新たな実行のやり直しは不要。正式global較正は次の実装・実行前監査を経て判断する。**

### fresh再現と保全の完了

別の空workで`reproduce.py`を実行し、8段階すべて終了コード0、同じ187 PASS／7 SKIP、追加45項目とmetadata50項目の成功を確認した。現source2,642 fileは初回・freshの双方で実行前後byte不変。freshは同じ試験の再実行であり、件数は二重加算しない。
