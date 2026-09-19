# Step1 Phase B・B-2 第36 tranche 監査書

対象：`step1_engine 0.40.0`／B-2実装受入packet。監査日：2026-09-16。

## 0. 判定

**B-2実装受入を維持し、B-3-0 notebookの起草へ進んでよい。今回の差分について、新たな必須engine修正は見つからない。**

残る訂正は文書・packetの整合性である。現提出版を説明するv0.3追補に第35 trancheの版番号・件数が残っている。また、今回同梱した監査テストのfixtureは単なるpath変更ではないため、変更分類を正確に記載する。これらはB-3-0初稿と併せて反映でき、engine改訂だけの再提出を要求するものではない。検証対象commitを確定する前には、採用した文書bytesとinventoryのSHAを一致させる。

| 判定項目 | 今回の判断 |
|---|---|
| `B2_implementation_acceptance` | accepted（実装・サンドボックス検証の範囲） |
| `B2_original_Colab_acceptance` | pending_explicit_carryover_to_B3 |
| `B3_notebook_preparation` | go |
| `ENGINE_VALID` | not_evaluated |
| `Phase_C_freeze` | not_authorized |

この判定は正式Colabの受入、実共分散、登録規模のexact-OT共有null、2000 pseudoの正式全手順較正、科学的freezeの承認ではない。

## 1. 対象と実行範囲

今回の3添付とZIP内の実体を確認した。単独添付のv0.3追補とZIP内の同名文書はbyte一致し、報告書も単独添付とZIP内でbyte一致した。したがって、追補の旧値は単独添付だけの取り違えではなく、ZIP内にも同じ状態で存在する。

| 添付 | SHA256 |
|---|---|
| `Step1_PhaseB_B2_tranche36.zip` | `5604fd2163fb934d3fdf11436768821d0f0a8da336fabc51683196f5992d3411` |
| `Step1_PhaseB_B2_tranche36_report.md` | `c70e7646d4952e0b0b139970b070ddcf9fe0f11a077f2a070ec93eade034e397` |
| `Step1_PhaseB_engine_spec_v0.3_addendum(1).md` | `625b9e4545c0094a438832ef1c723990947e952b08458599feb5b750795cf0bc` |

監査環境はPython 3.13.5、NumPy 2.3.5、SciPy 1.17.0、pytest 9.0.2。NumPyとSciPyのOpenBLASはいずれも1 threadである。POT、healpy、CAMB等は当環境に未導入。正式Colab lockとは異なる。

今回は、前回ZIPとのbyte差分、全current SHA inventory、最終提出sourceの全suite、前回12テスト原本の独立実行、12位置のliteral reference、文書の移管表・性能算術を検査した。過去の全ての独立実験を再実施したという意味ではない。新しい性能測定、実CMB scan、共分散生成、E2正式asset生成は行っていない。

## 2. engineと既存テストは変更されていない

第35 trancheとの比較では、41 module中40 moduleがbyte一致した。唯一の差分は`step1_engine/__init__.py`の次の1行である。

```diff
-__version__ = "0.39.0"
+__version__ = "0.40.0"
```

既存62 test fileと既存12 fixture/support fileはbyte一致した。新規追加は`tests/test_audit_b2_tranche35_chatgpt.py`の1 fileであり、12 test functionを持つ。rules本文、spec v0.2追補、tables JSON、性能JSONも前回とbyte一致した。

全suite後、ZIPに元から含まれていた全file memberを再照合し、**変更0件**であった。提出engine・テスト・fixture・規則は編集していない。

## 3. current inventoryは正しい。追補の現在値を更新する

`B2_completion_inventory.json`の以下130記録について、実ファイルSHAと一致した。

| 分類 | 照合件数 | 結果 |
|---|---:|---|
| module | 41 | 全一致 |
| test | 63 | 全一致 |
| fixture/support | 12 | 全一致 |
| asset/reference/log | 10 | 全一致 |
| 規則・spec等の文書 | 4 | 全一致 |
| 合計 | **130** | **全一致** |

test・fixtureの集合も実体と一致した。assets欄の10件は、tests/assets・tests/reference_assetsの7 fileとregression_logsの3 fileを含む。これはinventoryに列挙された130項目の検査であり、ZIP内の全履歴・一時cacheをcurrent inventoryが含むという主張ではない。

ところがv0.3追補の冒頭と「受入テスト（実体）」の行は第35 trancheの値である。報告書とcurrent inventoryは現版の正しい値を記載している。

| 項目 | 追補の現記載 | 今回の実体 |
|---|---:|---:|
| engine version | 0.39.0 | **0.40.0** |
| module | 41 | 41 |
| test file | 62 | **63** |
| `test_b*` file | 23 | 23 |
| `test_audit*` file | 39 | **40** |
| test function定義 | 607 | **619** |
| pytest case | 815 | **827** |

SHAが一致することと、文書の記述が最新であることは別である。現在は旧記述を含む文書bytesに対して、正しいSHAが付いている。

第35 tranche受入時点の数を残す意図なら履歴欄と明記して残せるが、現提出版欄には0.40.0と827件等を表示する。

### 履歴資料は変更しない

同梱の`B2_inventory_audit_supplement.json`と`docs_B2_scope_and_B3_handoff_proposal_ChatGPT.md`は、前回監査資料とbyte一致した。前者の0.39.0・旧SHA、後者の旧件数は**第35 tranche時点の履歴**として正当であり、上書きしない。

現版の検証は`B2_completion_inventory.json`、過去の監査受入の根拠は上記履歴、という役割を追補で明示するのがよい。報告書の引継ぎ文書名も、ZIP内の実名`docs_B2_scope_and_B3_handoff_proposal_ChatGPT.md`へ揃える。

## 4. テストの独立実行結果

### 4.1 最終提出sourceの全suite

```text
822 passed
4 skipped
1 failed
合計827件
```

時間は881.27秒。元のassert、受入閾値、test selectionは変更していない。pytestのcache書込みだけを無効化し、生成物は一時領域へ保存した。

FAILは`tests/test_b2_tranche3.py::test_w2_path_contracts`の`ModuleNotFoundError: No module named 'ot'`。この環境でPOTを必要とする分岐を実行できなかった結果であり、提出コードの数値不良を示す結果ではない。ただしPASSに振り替えない。

4 SKIPは次の外部integrationである。

- A11の凍結npy配列。
- mirror-topologyの凍結資産checkout。
- 凍結A10 notebook。
- テストの期待pathに置いたA10 official checkpoint。

最後の項目は、そのテストの期待pathにないためのSKIPである。ファイル名が似た別場所のrecordへ差し替えて実行したとは扱わない。

Claude側の同梱`test_log.txt`には、827個の一意なnodeidのPASSED記録と、`827 passed in 970.06s`がある。監査側が実行したcase集合とも一致する。これは**受領ログの内容確認**であって、監査側の822/4/1を827 PASSと表示する根拠ではない。

### 4.2 前回12テスト原本

前回の`test_tranche35_acceptance.py`を無改変で使用し、前回の`build_audit_fixture.py`からcurrent module上で元の合成入力を再生成した。結果は**12/12 PASS**（96.34秒）。pickleは当監査中に生成した一時cacheであり、外部から未知のpickleを読み込んでいない。

この12件は同梱suiteにも対応するので、827件に別種の12件として加算しない。

### 4.3 今回のfixtureはpathだけの変更ではない

AST比較では、今回同梱版の12 test functionと全assertが原本と一致した。変更されたfunctionは`fixtures()`のみである。

ただし原検査用12位置入力は、別scriptで`TwelveFixture(sizes=..., K=800, Kf=800, B=60)`として作っていた。今回の同梱版は`base()`と`twelve_from_cases(b['cases'])`で作るため、**単に同じ数値標本を別pathから読む変更ではない**。分布・標本数・ID等の異なる合成入力を用いて、同じ接続契約を試す適応である。

したがって報告書の「path適応のみ」は、「test本体・assertは不変、fixture再生成と配置適応」に変更する。今回、元のfixtureでも全12件がPASSすることを別途確認したため、この分類訂正はengine受入の撤回理由ではない。

## 5. B-3への移管は、今回の記載で受け入れてよい

v0.1 §B4.2のColab mock-grid smoke、v0.2のT10実bank・T19/A5・T14正式格子、B-3のofficial control、新規9点のcircle coverage/clone/priorが、移管表に残されている。受入条件を削除したり、未実施をPASSとする記載にはなっていない。

「未実装」と「未実行」の区別、geometry matcherと共分散完全intakeの区別、checkpoint readerのcore条件付き検証と外部参照再利用の区別も、追補に明記された。

B-3-3まで未実装項目の期限自体を無指定にするのではなく、既に同梱された監査側引継ぎ表§2を参照して期限を維持するのがよい。具体的には、正式12位置profileを受け入れる前、正式較正成果物を受け入れる前、実観測full-gridを評価・解放する前、実bankを正式生成・再利用する前、外部参照付き記録を正式判定へ再利用する前、という期限である。これは前回の期限を新しい文書へ接続するもので、新しい科学的条件の追加ではない。

B-3-0 notebook自体は今回ZIPに存在しない。今回のGOは、その**起草**へのGOであり、まだ提出されていないnotebookのRun allの承認ではない。

検証対象commit・module/test/fixture/asset SHAを固定し、まずE7 1点×2系統・N=2×10^4のmock-grid、T10、T19を実施する段階へ進める。1点controlにはcontrol用profileを明示し、productionの全surviving-size条件を緩和して通さない。

## 6. 性能の訂正と、対象を限定した数値再検算

性能JSONは前回と同一である。受領unit costを代入した算術を再計算し、以下と一致した。時間の再測定は行っていない。

| 項目 | 今回確認した外挿値 |
|---|---:|
| 共通null＋全9 caseのobserved | 4.4442632866時間 |
| 1 target・全matched familyのKDE CI、reference | 1.1759471111時間 |
| 同、opt-in batched | 0.2582274847時間 |
| 2000 pseudo・素朴全CI・batched | 516.4549693333時間 |
| 2000 pseudoの点・感度 | 7.0556826667時間 |
| E2 2走査×9 step外挿 | 0.9288549308時間 |

既定は`per_replicate`のままであり、これらはColabでの実測保証でも、未計上の12位置stage・診断・bank生成・I/Oを含む全計算時間でもない。

さらに、current engineから新たに得た正常12位置Resultについて、元のcluster hitをliteralに復元抽出して各配置1/36で混合し、配置別SciPy KDEから混合密度を求める独立referenceを再実行した。

| 比較 | 最大絶対差 |
|---|---:|
| 12位置familyの混合確率、両系統×5 seed | 2.2204460493e-16 |
| logQ CI端点、両系統×5 seed | 6.6613381478e-16 |
| logD点・帯域幅0.7/1/1.4 | 3.3750779949e-14 |

人工bankとtest-only W₂による実装検査である。今回、過去の90件KDE等を含む全独立実験を新たに再実行したと主張しない。全suiteに含まれる検査と、この対象を限定した独立referenceを区別する。

## 7. 文書のみの訂正候補

`document_patch/`に、追補、報告書、現在版inventory、および差分を置いた。

- 現在版番号と現在件数を実体に一致させる。
- fixture変更分類を正確にする。
- 履歴資料をcurrent inventoryの代用にしない旨を明記する。
- 同梱ファイル名、既存受入期限への参照、番号の欠番を整理する。
- 採用候補の追補bytesに対して`documents_sha256`の一項目だけを更新する。

**engine、test、fixture、規則本文は変更していない。** candidateをcurrent packetに重ねた130項目のSHA照合と文書整合性検査はPASSした。これは文書checkerの結果であり、候補overlay後に827件全suiteをもう一度実行したという記録ではない。

歴史的監査資料はそのまま保持する。独自に文面を編集した場合は、その最終bytesから文書SHAを再生成する。`verify_b2_packet.py`は今後のpacket出力前にも使えるread-only補助検査である。ただしテスト実行、ログの真正性検証、外部物理資産のintake、freeze判断を代行しない。

## 8. 結論

**B-2サンドボックス実装受入を維持し、B-3-0 notebookの起草へGO。今回、新たな必須engine修正はない。**

現在の追補に残る旧版番号・旧件数とfixture変更分類を整え、B-3-0初稿とともに提出すればよい。文書訂正だけのためにengineを再改訂し、B-2の数値手順をもう一巡作り直す必要はない。

正式なColab受入、ENGINE_VALID、全手順較正、Phase C freezeの判断は、記載された引継ぎ条件を満たしてから行う。科学的閾値、prior、KDE推定器、A10 official全体の再実行を、今回の監査結果により変更・要求するものではない。

### 主な出典・再現資料

- 提出報告書第36 tranche：版番号、テスト報告、移管表、inventory訂正、B-3計画。
- 提出spec v0.3：冒頭・受入テスト行、§B・B'・C。
- 元spec v0.1 §B4–B5、v0.2 §B–D。
- 同梱 `docs_B2_scope_and_B3_handoff_proposal_ChatGPT.md` §2：未実装項目の既存受入期限。
- `checks/packet_check.json`、`checks/final_test_summary.json`、pytest log/XML、前回原本比較diff、独立reference。
