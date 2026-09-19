# Phase C freeze packet v0.1 実行前・採用方針監査
## 原文v0.4/v0.5の独立対照／登録資産・第1波grid／工程変更と検証器

2026-09-19。Claude伝達用。対象：`Step1_PhaseC_freeze_packet_v0.1.zip`、単独の採用追補・freeze manifest。

## 0. 判断と承認範囲

**方式Aでの採用、登録資産・第1波gridの同一性、受入れ済みsourceの引渡し方針は支持する。既存B-2／B-3-0／B-3-1／B-3-2 A/Bの受入れと、B-3-3の受付コードの受入れを維持する。一方、今回のpacketのまま最終Phase C freeze／tagを確定することは、下記3領域の反映まで保留する。**

| ID | 必須整理 | 性質 |
|---|---|---|
| RC-1 | 原文v0.5のnoise stress testの採用先・変更履歴を明示し、付録B等の出典説明を補足 | 原文対応・採用scope。新たな大規模計算要求ではない |
| RC-2 | 較正先行／archive再利用等の使用前gateを前回補正版へ揃え、BLASの他pool条件もmanifestへ記載 | 既存期限・環境条件の保持 |
| RC-3 | packet inventory・accepted engine・実際の保存gridを検証するようcheckerを補強 | 新しい凍結・再利用の同一性確認。既存数値kernelの変更ではない |

**PC-1は、対象共分散をPhase Dで生成した時点でA11物理検証を実施し、当該共分散／bankを較正を含む正式処理で使う前に必ず受入れる、という条件付きの工程分離として承認する（§5）。物理clone同値性の検証そのものは未了のままである。**

今ここでnoise simulation、12位置全格子、共有null全OT、A/B、A10 officialをやり直す要求はない。今回の参考checkerも、その計算を行わない。Phase Dの実装準備は進められるが、正式な生成・較正・再利用は各使用前gateの受入れに従う。

`ENGINE_VALID`、B-3全体完了、完成したproduction engine、正式global較正、calibration usable、実観測label解放は今回承認しない。規則／設計／受入済み基盤sourceの固定と、未実装機能を含む完成productionの固定を区別する。

## 1. 対象の同一性

外側ZIPは21実ファイル（別に4 directory entry）で、CRC、名前重複、危険path、symlinkに異常なし。単独添付の採用追補・freeze manifestはZIP内の対応ファイルとbyte一致した。

| 対象 | SHA256 |
|---|---|
| `Step1_PhaseC_freeze_packet_v0.1.zip`（734,708 bytes） | `7adc2c56bd83bba7bee437e64e7aed768c24a00068b4dfe6f8169abeb4d9373c` |
| `PACKET_INVENTORY.json` | `63ec9f50750e831840113cc1c3041f785a4978d95637d516dda7cb9c385ce80a` |
| 採用追補 | `2dcf4e6a28d276d823ec0239bd07072e20d757502e06d7b06a015d54eb3077c8` |
| freeze manifest | `cced9eb7e537d651a04d65933473705c2658279260cac042cdf82e4abd9a0e26` |
| 提出checker | `2177b1f31b106e58c5e8082b422dfde92aa1e3f6703cd141f6e6f9aa0a450d91` |

上記は**受領版の識別値**であり、未作成の修正版・最終tagへの承認値ではない。

独立検査で、inventoryに列挙された20ファイルの集合・SHA・サイズを確認し、全件一致した。inventory自身を自己参照から除外する構成は適切である。

accepted sourceは、保持された`files_9.zip`内B-3-3 v2と、前回の検証済み`Step1_PhaseB_B3_3_v2_metadata_patch.zip`を重ねて再構成した。engineは0.54.0、source inventoryは `0ece0a3d1e991d37b7bbc51d15c1a89c0d96d40920f3b79a404cede5bad2943e`で、172項目のSHA照合・current counts検査はPASS。

**今回、宣言されたhandoff commit `1db30cd1678d40340cd445204ec97a08590c24d5`をremoteからcloneして照合したわけではない。** 確認したのは、当該commitに対応すると記載されたinventoryと、以前の受入れ済み実ファイルとの一致である。最終commit／tag時には実体とこの内容の対応を記録する。

## 2. 方式A・原文・数値資産・第1波gridで確認できたこと

### 2.1 方式Aのbody/tables binding

`Step1_rules_v1.0_draft4.1.md`はSHA `5f02c970eb39f9b3e7f7b17b48eb2d3daa16434517cf4442bac339f5ab719615`、tablesは `522751be134aa3ff4fdf33c6be0d7397fb7bd3c89a6c67e26a67bd32dceeb0b4`。受入れ済みengineのコピーとbyte一致し、実`verify_binding()`も成功した。本文内の当時の「draft／HOLD」や原文照合未了という記述を遡及的に書き換えず、現在の採用状態と対照結果を外側追補へ記録する方式は妥当。

### 2.2 原文2件

| 原文 | 行数 | SHA256 |
|---|---:|---|
| v0.4 | 158 | `0569ae2f9cbd3003d1f08840b43f20c14e8da3e07ca7718743929ee138235371` |
| v0.5 | 107 | `357e4d7d0325e3284bd3dcf062a4c5e5bf7599b14032e90ab3da6912da5e9f18` |

いずれもdraft4.1 L4の完全SHAと一致する。全文を対照し、33項目の手動対照表を`originals_correspondence.md/json`へ保存した。33は整理項目数であり、33個の科学的検定ではない。

### 2.3 第1波grid

保存された`grid_registry.json`をsource-boundの復元関数へ通し、保存された`first_wave_configuration_manifest.json`自体をdeserialize・validateしたうえで、凍結A6/A7から再構築したmanifestと比較した。

- E1は3配置、E2/E7/E8は各9配置、計30。各familyのprior合計1。
- Lは1.00／1.20／1.50、config_idは30個で重複なし。
- full-precision reduced座標、shape、凍結liftによるr_obs、x0_CT=-r_obs、cache key、circle status、weightが再構築結果と一致。
- 既存A7との照合は30/30、ok=True。
- registry payload SHA `ba48214585c50348a9f43ef82ba33c3b7fcb982ebc89d0ba38985969c48ec851`。
- configuration payload SHA `75e85b6d8bca15e1cd7e2048bea7f6bb02a1d0d22dfa02422e802ecfea2d90a1`。

これは**第1波の登録metadataの再構築**であり、12位置の巨大格子探索や物理共分散生成を行ったという意味ではない。

### 2.4 資産・receipt・監査書

12位置JSON・108行の幾何CSV・共有W2 null JSONを、前回受入れたA/B出力ZIPの元memberと比較して全bytes一致。receipt JSONは前回metadata patch内の完成値とbyte一致。外部参照poolのSHAと42,573,325 bytesも元B出力ZIPから再確認した。監査書7本も保持された過去の実ファイルと全bytes一致する。

共有null・12位置の構造／payload／宣言identityも照合。今回の資産同一性検査を、全6000距離や108行の外部幾何を新たに計算した結果とは扱わない。control ZIP等はreceiptを介した完全SHA参照があるため、manifestの当該行にSHAを重複記載していないことだけを理由に未束縛とは判定しない。実装の便宜上はreceipt_refを明示するとよい。

## 3. RC-1：原文対照の結果と、採用前に明示する項目

### 3.1 多くの変更は、現在の本文で既に明示されている

原文のphenotype-vetoからlegacy diagnosticへの変更、中央帯からEvent Bへの変更、W2のn_sub=20,000から2,000/5,000、2標本nullからdisjoint3blockのmax、B=200から最大1000のprefix停止、A6/A11座標、CRNのkey分離、ESSの撤回等は現在の本文に説明されている。今回、これらを旧計画へ戻す要求はない。

v0.5自体がL3–4で「以後の変更はPhase A実測を反映したrules draftへ記す」としており、現行規則がv0.5と違うこと自体を一律不適合とはしない。一方、出典表示があることと、すべてが原文どおりであることも区別する。

### 3.2 noise stress testの採用先が確認できない

v0.5の強化項目L91は、noise stress testについて、次を指定する。

```
|Δ log Q_j| < 0.1
AND support category不変
AND 判定境界からのmarginの20%未満
MC CI比較は併記のみ
```

採用draft4.1、tables、今回の採用追補、freeze manifest／pre_use_gatesを照合したが、対応する引継ぎ先や撤回・置換履歴は見つからなかった。KDEの帯域幅感度やfloat32 selectionの検査は、noise stress testと同じ定義ではない。

これは**研究全体でどこにも実装されていないと断定するものではない**。今回の最終採用文書が、原文のこの要求をどう扱うのか確認できないという指摘である。noise testを今回実行する要求ではないが、以下を採用前に記録する。

- 維持するなら適用scope、入力noise／水準とmargin等を固定する場所、実装／受入れの使用前期限。
- 別scopeへ移すなら移管先、理由、core／較正との関係と承認。
- 廃止／置換するなら旧新の意味、理由、既知結果との関係と判断根拠。

**監査側でnoise要件を不要と決めたり、未確認の試験を完了扱いにしたりはしていない。** 方針を明記するまで原文対応を一括完了とはしない。

### 3.3 DのCIとdtypeの出典説明

付録B L335は原計画のDのCIを「未定義」とする。しかしv0.4 L134はDの上側CI、v0.5 L78–79はDの下側CIをpredicateへ明示している。正確には、**CIを使う判定は既定、具体的な密度推定器・bootstrap・区間計算法が未固定**であった、と区別する。

付録B L334のdtype説明はS2 float32(HOLD)だけでは不足し、現在の§5.2／§10.1／§12.5にあるS1およびW2のpaired float32感度も含む。原文v0.4 §9／v0.5 L92はfloat64のみであり、現在の感度経路は後続の明示的な変更である。

どちらも現在の数値推定器やdtype方針を変更する要求ではなく、原文対応を正しく説明する訂正である。方式Aなので原文bytesは保ち、補足を採用追補に置ける。

### 3.4 照合範囲の限定

v0.4は変更点のみで、v0.3原文は今回同梱されていない。従ってfamily集合やsupportのD点条件など、v0.3にのみ出典を置く箇所の逐語照合は今回の2原文だけでは完了しない。これらの既往受入れは維持し、今回新たにv0.3原文も確認したとは記録しない。

同様に§1.1の固定軸trace式と正の符号は、このv0.4本文には見つからない。式の真偽を今回否定／証明するのではなく、出典を前段研究・監査へ分ける事項である。付録Bの「左欄は原文から転記」も、要約・前段参照を含むことを明確にする。

## 4. RC-2：使用前gateと環境metadata

採用追補§9の較正先行順序は適切であるが、§7／manifestのdeadlineは前回B-3-3補正版より遅く読める表現へ戻っている。

| 項目 | 受領Phase C | 揃えるべき使用前条件 |
|---|---|---|
| pseudo完全Result archive | before Phase E calibration | 全手順の正式global較正を実行する前。12位置分岐を含む |
| calibration-first driver | before any official observed-target run | **正式global較正を開始する前にdriverを実装・受入れ**。実観測full-gridを先に計算しない |
| external W2/context/run record再利用 | before Phase E archive reuse | **較正を含む最初の正式再利用前**。Phase名によって後回しにしない |

前回の `ChatGPT_audit_Step1_PhaseB_B3_3_v2.md` §4.3・metadata patchに既にある補正の継承であり、新しい工程要件ではない。現packetで誤った順序の実行が起きたことを示したものでもない。

freeze manifestのenvironment_lockはNumPy-owned OpenBLAS=2だけを記し、本文§12.1／既存pinsの**他pool<=2**が欠ける。数値package版を変えず、その条件も明記する。現在のColab実測が不合格になったという指摘ではない。

## 5. PC-1：物理clone検証の工程分離についての判断

この計画は新9位置の物理共分散をPhase Dで生成する。その時点で当該共分散のA11変換・clone同値性を検証する順序は合理的であり、以下の条件で**工程分離を承認**する。

- 幾何nearest-clone／circle／priorは既存B-3-2Aの受入れとして保持。物理共分散の同値性と混同しない。
- 検証対象は新9位置×該当する全surviving size。旧anchorの成功を新点の成功へ転記しない。既存A11の式・許容値・identity契約を保持する。
- 対象共分散の生成時に検査し、較正を含め当該共分散／bankを正式に使う前に受入れる。検査に数値生成が必要なら検証用scopeで行い、未検証値を正式出力へ流用しない。
- 技術失敗・未検証を無視して点やprior massを削除しない。source・環境・共分散／変換・出力SHAと結果を保存する。

manifestには工程判断の承認と、**物理検証自体のpending**を別field／statusで残す。Phase Cを通ったからPC-1の物理gateもPASS、という移管は認めない。

## 6. RC-3：現checkerのPASSと、検証範囲のずれ

### 6.1 現checkerの正常run

提出`verify_phaseC_packet.py`は、今回の無変更packetと再構成したaccepted engineで`passed=true`となった。独立検査でも実際のファイル・gridに不整合は見つかっていない。

ただし現checkerには、次の検証がない。

1. `PACKET_INVENTORY.json`を読み込まないため、採用追補、freeze manifestの政策field、checker自身等の一覧束縛を検査しない。
2. 引数のengineについて、宣言されたhandoff inventoryのSHA・各module・engine版を確認する前にimportする。
3. 保存されたregistry／configuration manifest自体を復元・validateせず、新たに再構築したgridだけを検査する。file SHAが更新されても保存payloadとの対応を検査しない。

### 6.2 隔離copyでの具体的な対照

全15ケースを別processで実行し、元packetとaccepted sourceは変更していない。

| TEST-ONLY対照 | 提出checker | 参考checker |
|---|---|---|
| 無変更packet | PASS | PASS |
| 採用追補のbytesを変更、既存inventoryは据置 | **PASS** | 拒否 |
| PACKET_INVENTORYを削除 | **PASS** | 拒否 |
| freeze内のdeadlineを変更、inventory据置 | **PASS** | 拒否 |
| engineの__init__.pyにコメント追加、期待sourceSHAは据置 | **PASS** | 拒否 |
| engine inventoryに改行追加、期待inventorySHAは据置 | **PASS** | 拒否 |
| 保存gridの最初のweightを1/3→0.123、fileSHA等だけ更新 | **PASS** | prior契約違反として拒否 |
| 保存gridの内部payloadSHAだけ無効化、fileSHA等を更新 | **PASS** | 拒否 |
| 保存registryのanchorを変更、fileSHA等を更新 | **PASS** | 拒否 |
| 共有nullの宣言B_maxだけ1000→2、inventoryを更新 | **PASS** | 拒否 |
| rules本文のbytesを変更 | 拒否 | 拒否 |
| 監査書のbytesを変更 | 拒否 | 拒否 |
| 未登録の追加file | **PASS** | 拒否 |
| 外側inventoryとfreezeのhandoff commitを不一致にする | **PASS** | 拒否 |
| 原文v0.5を変更してmanifest内のexpected/fileSHA等も更新 | **PASS** | draftに固定済みの原文SHAと異なり拒否 |

保存gridの対照では、file SHAとpacket inventoryは変更後bytesへ正しく更新した一方、内部意味／payloadとsourceの対応は不整合のままにした。**すべての記録を悪意を持って再署名する攻撃への耐性を要求した試験ではない。** SHA一覧と、読込んだ実内容の検査を区別するための対照である。

原版は正常1件と既存の拒否2件を含む3/15で期待動作、参考版は15/15で期待動作となった。同じ3つの検証境界を複数条件で確認しており、12種類の独立した科学的欠陥や通常実行の失敗率と数えない。

### 6.3 参考checker

`reference_patch/verify_phaseC_packet.py`は、20のpacket entry、172のsource entry、実保存registry/grid、rules binding、12位置memberと共有null宣言、receipt／監査参照を検査する。最終の外側receiptから得た `--expected-inventory-sha256` も受け付ける。指定なしでは内部整合性のみで、外側の真正な承認を作り出すものではない。

参考checkerだけを置換してinventoryの対応1項目を更新した**tool-only候補**でも正常検査を実行した。正しい外側inventoryではPASS、誤った外側SHAでは拒否。参考checker SHAは `b6de5d5f4e3725b6d201f443f49df8fed8a63c1b386a62563a1986acef047a12`、tool-only候補inventoryは `b46ce3923d92dd786af184e9db41e8e192877bf95f0dbeaeb746bd754bb5ac1f`。

**この候補は政策文書をまだ修正していない。従って、このPASSや候補SHAを最終freeze承認へ転用しない。** checkerは科学的方針、noiseの採否、PC-1完了、current Colab環境、remote commitを自動承認しない。

## 7. 実施範囲と限界

実施：原文2件・draft・政策文書の全文対照、20 packet entry／172 source entryのSHA検証、既往監査7本と登録資産の元出力比較、第1波30配置の保存payload復元とsource-bound再構築、既存資産reader、15のchecker対照、参考checker-only overlayでの外側SHA2対照。

今回の独立identity scriptは46個のassertionを行ったが、同一データへの粒度を分けた確認であり、46の独立した科学的実験ではない。

未実施：新Colab実行、実Drive検証、原文v0.3全文、Phase Aの全監査再実行、新しいnoise stress test、A11物理clone同値、12位置の全格子、物理sky／bank生成、6000 pairのOT、909件全suite、正式global較正、label解放、remote handoff commitの再clone。

参考checkerの最初のbaseline試行では、当方が12位置memberのkeyを `manifest_sha256` と誤って参照した。実schemaの `sha256` へ参考コードだけを修正して再実行した。提出assetの異常ではなく、当方のharness修正である。初回結果は`candidate_baseline_initial.json`に保持した。

## 8. 最短の引渡し

原文対応の採用判断とRC-2を採用追補／manifestへ反映し、PC-1の工程承認と検証pendingを分ける。参考checkerを採用する場合は最終checkerも同梱し、全最終ファイルのinventoryを更新する。原文・draft/tables・既存engine・数値資産・過去のrun/監査は変更しない。

一覧自身のSHAや最終ZIP SHAは外側receiptに置き、自己参照を作らない。新しいPhase C packetのcommit／tagと、数値を生成した過去commitを区別する。形式上のchecksum PASSと、原文／工程の監査承認を別記録とする。

**最終判定：既存受入れと方式A・登録資産・第1波gridは維持／確認済み。PC-1の工程分離は使用前gate付きで承認。現v0.1の最終freezeは、原文noise要件の扱い、使用前期限・環境metadata、検証器の束縛を整えてから確定する。新しい大規模計算の要求なし。**

終了時に、提出21ファイルとaccepted source185ファイルを元のZIP／metadata overlayへ再照合した。変更・欠落・新規追加はすべて0件であった。

### 主要証拠

- `originals_correspondence.md`、`evidence/originals_correspondence.json`：33項目の手動対照と原文行番号。
- `evidence/identity_and_grid.json`／log、`source_packet_check.json`：20/172項目、元資産・receipt・監査、実grid再構築。
- `evidence/submitted_verifier.log`、`verifier_probes.json`／log：15の正常／異常対照。
- `evidence/reference_overlay.json`／log：checkerのみ置換した候補の2対照。
- `reference_patch/`：参考checker、政策訂正要件と文案。
- `scripts/`：実施した検査コード。`submitted/phaseC/`：受領原本。`prior/handoff/engine/phaseB/`：過去の受入れsourceとmetadata patchを重ねた参照。
