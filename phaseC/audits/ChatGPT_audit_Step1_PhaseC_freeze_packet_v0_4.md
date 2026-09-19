# Phase C freeze packet v0.4 監査
## 研究計画v0.3の原文対照・noise著者採用記録・RC閉鎖状態の維持

2026-09-19。Claude伝達用。対象：今回受領した`files_10.zip`内のPhase C packet **v0.4**。
研究計画の原文 **v0.3** と、今回のpacket版 **v0.4** は別の版番号である。

## 0. 結論・承認範囲

**今回のpacketを、規則・登録設計／資産・受入れ済み基盤sourceのPhase C採用対象として承認する。新しい必須コード修正、数値再実行、再提出だけを目的とする改訂は要求しない。**

- v0.3原文の全209行を読み、§14と現在の本文がv0.3へ直接出典を置く事項を対照した。原文の継承、後続の明示的変更、今回個別の実装完了を判定していない旧補助診断を分けて記録する。
- noiseをPhase Eの独立した記述的robustness qualifierへ移す**著者確定の記録**を追補とmanifestの両方に確認した。仕様を未見結果前に固定するgate 1と、公開前に実測・結果監査するgate 2が揃っている。この記録のscopeで採用を受け入れる。
- RC-1の原文対応・noise採用先の整理を今回の記録で閉じる。RC-2の使用前期限・環境条件、RC-3のcheckerの束縛は維持されている。
- PC-1は既に受入れた工程分離と使用前条件のまま。物理共分散clone検証そのものはpendingである。

**B-2、B-3-0、B-3-1、B-3-2 A/B、B-3-3受付コードの既存受入れは維持する。** 今回の承認は`ENGINE_VALID`、B-3全体の一括完了、完成production engine、noise仕様・実装・実測の受入れ、noise-insensitive、正式global較正、calibration usable、実観測label解放ではない。

今回の監査はrepositoryへ書込みをしていない。**実際の最終commit／tag作成・remote commitの確認は未実施**であり、その実施記録は別途残す。以下の完全SHAに対応する受領bytesが承認対象となる。

## 1. 対象の同一性

| 対象 | bytes | SHA256 |
|---|---:|---|
| `files_10.zip` | 788074 | `5b5e3c7ec822c2970fe1f5f8b35022e27ba802383f316a15c72bcfb98e86c8ed` |
| 内側 `Step1_PhaseC_freeze_packet_v0.4.zip` | 778651 | `3beaf98286a3c8dd3f099052fd2743a14d8acab60cec758ad627354b9ca3c28c` |
| `PACKET_INVENTORY.json` | 3991 | `7bf6bfc3a395cd945595cd8675f5756337c75706013710861bb0553dd86c075d` |
| 採用追補 | 14181 | `8598ee96bce2d3718985b42c6129d0efb384db0d5447f4d49f6767647360db84` |
| freeze manifest | 12992 | `8910bf6ba3af5dc0c14f65fdd065c2df841b38e5358462c6c39a17f7c316c156` |
| `verify_phaseC_packet.py` | — | `d3c228151cfa571891c87c383e63be5f379a48f497d0078229db9588599a7d41` |
| 新しく同梱された研究計画v0.3原文 | 14387 | `bac9dbfe7dfb70baa4a6ca5f1d3dc8f24c65641ebf01e3693171a4022c2abfb8` |

外側は3 file member。単独添付の追補・manifestは内側とbyte一致。内側は26実ファイルで、inventory自身以外の25項目について集合・SHA・バイト数が一致した。ZIP CRC、名前重複、危険path、symlinkに異常なし。

前回受領したPhase C v0.2と比較し、既存23件中19件はbyte不変。変更は追補・manifest・checker・inventoryの4件、新規はv0.3原文・前回v0.2監査書・noise方針文案の3件である。v0.4/v0.5原文、draft4.1/tables、登録数値資産、既往監査書は不変。

accepted sourceは、前回監査証拠に保持されたengine 0.54.0を不変で使用した。185実ファイルが以前の証拠ZIPと全bytes一致し、handoff inventory `0ece0a3d1e991d37b7bbc51d15c1a89c0d96d40920f3b79a404cede5bad2943e` に対して172項目のSHA検査を通過した。

宣言されたhandoff commitは`1db30cd1678d40340cd445204ec97a08590c24d5`であるが、今回このremote commitを取得して照合したとの主張ではない。以前に受入れた実ファイルと、宣言inventoryとの同一性の確認である。

## 2. v0.3原文の照合

### 2.1 原本と照合範囲

今回の`originals/Step1_research_plan_v0.3.md`は、前回Libraryで取得した`Step1_研究計画_v0.3_ChatGPT確認用.md`と全bytes一致する。前回はnoise関連節を中心に対応付けたが、今回は全209行と、現行の直接出典表示を対照した。

独立対照表を`v03_original_correspondence.md`および`evidence/v03_correspondence.json`へ34項目で保存した。34は整理単位であって、34種類の科学的検定や実装試験ではない。行番号は原ファイルの物理行である。

### 2.2 v0.3に直接出典を置く事項

| 現在の記述 | 原文の対応 | 判定 |
|---|---|---|
| §0.5：family mixture・離散prior・p^(3) | v0.3 §3、§4、§5 | 骨格を直接確認。具体値・イベント・座標は後続採用を区別 |
| §4.1／付録B：E1/E2/E7/E8の四族 | v0.3 §3 L57 | 直接一致 |
| §1.4／付録B：supportはD点推定>1 | v0.3 §3 L66 | L_Q>=3、logD点値>0、auditを直接確認 |
| §8.1：family混合してから比を取る | v0.3 §3 L59–60 | 原則一致。現行はnativeの点依存referenceまで一般化 |
| §10.4：第一波判定固定の撤回履歴 | v0.3 §5 L94–96 → v0.4 §4.3 | 旧「第一波判定は変更しない」を原文で確認し、後続撤回と対応 |
| noiseの原対象・加算・報告 | v0.3 §14 L184–189 | 1点の低ell共分散加算診断を確認 |

「原文に根拠がある」と「その後一切変えていない」を混同しない。例えば、原文のE7 shapeはLAy=L2x=Lを含むが、現在の採用sliceはA6/A7によりLAy=L2x=0である。旧共通uとx0も現在のfamily固有reduced座標・凍結liftとは同一ではない。今回のnoiseの基準点を、旧数値座標や開発用mockから無条件に転記しないという追補は適切である。

### 2.3 DのCIの出典をさらに明確にする

**strongでD下側CI>1を使う条件は、v0.3 §3 L67–68に既に存在する。** 従ってその判定条件をv0.5で初めて導入したとは記さない。v0.3のunsupportedはD点値<=1で、v0.4 §8にD上側CIを使う後続変更がある。

追補が「D CIを用いる判定は既定で、後から推定器・cluster bootstrap・区間計算法を固定した」と説明する方向は正しい。今回追加で確認した、より早い下側CIの出典を本監査・対照表へ記録する。これだけを理由に方式Aの本文を編集する必要はない。

### 2.4 noise §14の対応

原文はE7・L=1.0・第1観測点の1点へ、低ellノイズ共分散を加算しQ_jの変化を報告する。候補としてhalf-mission差分またはNPIPE simulationsを挙げ、利用可能性を確認する計画である。元のMC CIだけによる判定は、v0.5 L91の3条件ANDへ更新され、MC CI比較は併記となる。

追補の引用部分は空白・改行・引用符を整えた再掲であり、literalな文字列全体の一致ではない。しかし、体裁の正規化後には一致し、対象・候補・加算・Q_j・旧判定の意味の相違はない。真の原文は同梱bytesと完全SHAで保持されるため、この「逐語」という体裁上の用語だけで再提出は要求しない。

### 2.5 「原文照合完了」の意味の限定

v0.3自体はv0.2からの差分文書である。今回v0.2以前を通読したわけではなく、未同梱の参照先の内容を一般知識から補完していない。

原文にはCRNなし1点検算、10batch間分散CIの併記、Davies検算などもあるが、今回それぞれの実施証拠・全変更履歴を確定したとはしない。negative独立bootstrapや5-seed CI、現在のImhof–Gil–Pelaezを、その個別検査の実施証拠へ読み替えない。**今回完了したのは全文を読んだ原文対応の監査であり、旧差分文書の全タスクを実装・実行済みと認定する監査ではない。**

## 3. noise方針の著者確定記録

追補§2.1には「著者（辻氏）は2026-09-19に移管へ同意し、監査条件を採用した」とある。manifestも以下のように区別している。

| field／事項 | 現在の記録 |
|---|---|
| policy_status | `AUDIT_ACCEPTABLE_WITH_PRE_SPECIFICATION_GATE` |
| author_adoption_status | `CONFIRMED_BY_AUTHOR_2026-09-19` |
| implementation_status | `NOT_IMPLEMENTED_OR_NOT_YET_ACCEPTED` |
| execution_status | `NOT_RUN` |
| scope | core/support/strong・較正とは別のdescriptive noise robustness qualifier |
| gate 1 | 未見の正式full-grid／noise-added結果の生成・閲覧前に仕様固定・事前検証・監査 |
| gate 2 | Phase Eで実測・結果監査を完了し、公開／label解放前に併記 |

**本文と機械可読記録は整合しており、前回の著者確認待ちという記録上の残件は解消している。** これはユーザーが提出した採用記録としての受入れである。manifestが参照する別のClaude会話そのものを、当方が取得・認証したわけではない。署名等の追加提出を本監査の必須要件にはしていない。

基準1点のscope、現在のA6/A11・immutable IDへの対応を詳細specで固定すること、良好な結果を見てから対象を差し替えないこと、3条件AND、categoryとmarginの一意な定義、境界／未知／技術失敗を自動PASSにしないことを保持している。

報告もcoreとnoiseを別fieldで保持し、noise-sensitiveの場合の限定を主要結果のそばに記載する。失敗を理由に封印済みcore数値・較正・priorを改変せず、同時にnoiseに頑健だとも主張しない。真のcore実装異常を「robustness外」として免責しない条件も維持されている。

**著者の方針確定と、noise詳細仕様・実装・実測・PASSは別である。** 現packetにはnoise入力の実取得やcategory/marginの最終定義はなく、使用前gateへ明示的に残る。このgateを満たすまで未見の正式full-grid/noise-added結果へ進まない。Phase Cで新たなnoise計算を要求するものではない。

## 4. RC閉鎖状態とPC-1の維持

### RC-1

既に受け入れたD-CI・dtype・trace出典説明を維持し、今回v0.3原文を同梱して直接対照した。noise採用先、著者の確定記録、二段階gateと独立報告も揃った。**採用方針・原文対応として閉鎖**する。noiseの実測statusは未了のままである。

### RC-2

前回の非noise使用前gate8件はmanifestで完全に同じ内容である。pseudo完全archiveは正式global較正前、較正先行driverは較正開始前、外部context等は較正を含む最初の正式再利用前。環境metadataもNumPy-owned OpenBLAS=2、他pool<=2を保持する。

§9は各機能をそれぞれの使用前期限までに受け入れる形へ整理され、Phase Eでのnoise実測をcore較正より前に一律要求する矛盾はない。noise仕様だけは未見結果前に固定する。

### RC-3

checkerの変更は`PLAN_SHA`へv0.3の固定SHAを追加したことだけである。そのentryを除いた構文木は前回checkerと一致し、検査を弱めた実行文差分はない。実行結果は§5のとおり。

### PC-1

前回と同じ「工程分離承認・物理検証pending」。新9位置×該当全size、既存A11式／許容値、較正を含む正式使用前の受入れ、未検証点・prior massを削除しない条件を保持。今回物理cloneの数値検査を行ったとは扱わない。

## 5. 今回の技術検査

| 検査 | 独立実行・照合結果 |
|---|---|
| packet inventory | 25項目、file集合／SHA／sizeすべて一致 |
| accepted source checker | 172項目一致、engine 0.54.0 |
| 同梱v0.3原文 | 14,387 bytes・SHA・以前のLibrary原本と一致 |
| 第1波保存grid | 実payloadを復元・検証し、source-bound再構築と全体一致。30配置、各family重み和1、A7 30/30 |
| 既往登録資産・receipt | 元の受入れ済みA/B出力・B-3-3補正とbyte一致 |
| 既往監査・文案 | 11ファイルが保持原本とbyte一致 |
| 前回15対照＋v0.3新3対照 | 18/18期待動作：正常1件受理、不整合17件拒否 |
| 外側inventory SHAの3対照 | 正しいSHAでPASS、誤SHAで拒否、無指定は内部整合性のみPASS |
| 終了時の原本保全 | 外側3、内側26、accepted source185ファイルすべて不変 |

前回15対照では、追補・期限を変えてinventory据置、欠落inventory、変更source、保存gridの不正weight/payload、registry変更、共有null宣言Bmax変更、本文／監査書変更、追加file、handoff不一致、v0.5原文の局所hash付替え等を再適用した。

新しい3対照は、(a) v0.3原文を変更してmanifest内expected/file SHA・inventoryを合わせてもgolden SHAで拒否、(b) 原文欠落、(c) manifestからv0.3 entryを削除してinventoryを更新、である。すべて隔離copyで実施した。新3対照を含む18は同じ検証境界への入力条件数であり、18の独立した科学的実験ではない。

正常baseline・外側SHA対照は一部同じ検査を繰り返しているため、件数を足して独立した科学的検証数へ水増ししない。今回、著者の全909件pytestを再実行していない。

## 6. 最終記録・次工程

受領packetを変更せず検証する際の外側inventory値：

```
7bf6bfc3a395cd945595cd8675f5756337c75706013710861bb0553dd86c075d
```

例（`PHASEB`は上記handoff inventoryと一致する受入れ済みengineの場所）：

```bash
python phaseC/verify_phaseC_packet.py phaseC "$PHASEB" \
  --expected-inventory-sha256 \
  7bf6bfc3a395cd945595cd8675f5756337c75706013710861bb0553dd86c075d
```

今回のmanifest内の`full_correspondence: REQUESTED`は**提出時点**の記録として正しい。今回の監査と対照表をその後の完了証拠として別に保存すればよく、過去の監査書を「当時から確認済み」へ書き換えない。新監査をpacketへ同梱するなど内容を変更する場合は、最終ファイル集合からinventoryを更新する。そのmetadata整理だけで数値再実行や全面監査をもう一巡求めるものではない。

実際のPhase C commit／tagを作成したら、その識別値と最終packet/inventory SHAを記録する。過去の数値生成commit、accepted baseのhandoff commit、今回のPhase C保存commitを混同しない。

**Phase Cの採用・freeze手続へ進んでよい。** Phase Dの実装準備は継続できるが、正式bank生成・較正・再利用・実観測評価は各使用前gateを満たしてから行う。

## 7. 未実施事項・限界

監査環境：Python 3.13.5／NumPy 2.3.5／SciPy 1.17.0、計算processのBLAS/OMP/MKLは1 thread。登録Colab環境とは異なる。新しいpackage導入はない。

未実施：新Colab・実Drive、noise入力データの取得／利用可能性確認、noise詳細specの実装受入れ・stress実測、A11物理clone、物理共分散・sky/bank生成、12位置全格子、全6000 OT、全909 pytest、正式global較正、remote handoff再clone、別Claude会話の独立認証、repositoryへのcommit/tag作成。

**最終判断：今回の3重点事項は、記録されたscopeで受入れ。Phase C採用対象の承認。新しい必須修正・大規模再実行なし。既存PASSを維持し、未実装・未実測・未解放のgateはそのまま残す。**

### 主な根拠

- `submitted/packet/phaseC/`：受領した原文v0.3/v0.4/v0.5、draft4.1/tables、採用追補、freeze manifest、登録資産、checksum checker。
- `v03_original_correspondence.md`、`evidence/v03_correspondence.json`：今回の全文対照。
- `evidence/identity_and_policy.json`、`source_check.json`、`checker_baseline.json`、`checker_regression.json`、`outer_binding.json`、`final_integrity.json`。
- `scripts/`：同一性検査、隔離copyの拒否試験、外側SHA対照、原本保全検査。
- `prior/accepted_source/engine/phaseB/`：不変で使用した受入れ済みsource。`prior/historical/`：前回取得したv0.3原本。
