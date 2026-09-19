# Phase C freeze packet v0.2 監査
## 前回RC-2/RC-3の閉鎖・noise stress test の移管判断・仕様固定の期限

2026-09-19。Claude伝達用。対象：`Step1_PhaseC_freeze_packet_v0.2.zip`と単独の採用追補・freeze manifest。

## 0. 結論と承認範囲

**前回RC-2（使用前gate・環境metadata）とRC-3（検証器の束縛）は修正を確認し、閉じてよい。RC-1のD-CI／dtype／原文対応説明の補足も受入れる。新しい必須コード修正・数値再計算はない。**

**noise stress testをPhase Eの独立した記述的robustness qualifierへ移す方針に賛成し、二段階の仕様・実行gateを条件として監査上受入れ可能と判断する。** 「実施をPhase Eへ移す」と「未見の正式結果を知ってから仕様を決める」を区別する必要がある。詳細仕様の固定・事前検証は未見の正式full-grid/noise-added結果の生成・閲覧前、実測・結果監査は公開／label解放前とする。

現在のpacketは `AUTHOR_DECISION_PROPOSED` のままで、著者確認を完了した記録ではない。最終採用では、著者の選択と上の二段階gate、今回確認したv0.3 §14の定義、結果の独立した報告方法を追補・manifestへ反映し、最終inventoryを更新する。**この同じ文書整理だけを理由に、新しい大規模Colabや全面数値監査を繰り返す要求はしない。**

B-2、B-3-0、B-3-1、B-3-2 A/B、B-3-3受付コードの既存受入れを維持する。PC-1の工程分離も承認済みの条件どおりである。`ENGINE_VALID`、完成production engine、noise試験の実装・実測・PASS、正式global較正、calibration usable、実観測label解放は本監査で承認・実行していない。最終tagを作成したわけでもない。

| 項目 | 今回の判断 |
|---|---|
| packet/source・登録資産の同一性 | PASS |
| RC-2：較正・再利用の期限、BLAS条件 | 修正承認 |
| RC-3：packet inventory、source、保存gridのchecker | 修正承認 |
| RC-1：D-CI／dtype／trace出典等の説明 | 補足受入れ |
| noiseのscope移管 | 二段階gate・独立報告・著者確認の条件で支持 |
| 現版を何も追記せず最終採用したとの記録 | 行わない。提案statusと仕様固定期限を整える |
| Phase D実装準備 | 継続可。正式使用は各機能の使用前gateに従う |

## 1. 受領物・差分・accepted source

ZIPは23実ファイル（別に4 directory entry）。CRC、重複名、危険path、symlinkの検査に異常なし。単独添付2件はZIP内とbyte一致した。

| 対象 | SHA256 |
|---|---|
| 受領ZIP（756,316 bytes） | `2f3fc2cc19ba83b9e84ec2efa21f468131c1aa09fcb9be721ad51de6f103c641` |
| PACKET_INVENTORY.json | `82bbef9310f10ad0d7567991fc5bc851f8851744222e284544ded4efd69cacef` |
| 採用追補 | `1aedce4d242f6a9a3c5909dd099c739c21108cb8ce83b10d0b960f2d83cf22fe` |
| freeze manifest | `9f4f9e2d6b2c123dd5eb08ae02d9c0d5c2cd8aec5ff125eae340d15450df3e36` |
| checker | `b6de5d5f4e3725b6d201f443f49df8fed8a63c1b386a62563a1986acef047a12` |

前版から変わったのは、追補、freeze manifest、checker、packet inventoryの4件。旧21ファイル中17件はbyte不変で、前回監査書と原文対照表の2件が追加されている。原文v0.4/v0.5、draft4.1、tables、登録資産、既往監査書7本はbyte不変。

accepted engineは `files_9.zip` 内のB-3-3 v2へ、前回受入れたmetadata overlayを適用して再構成した。185実ファイルは前回監査証拠中のaccepted sourceと全件一致し、engine 0.54.0、handoff inventory `0ece0a3d1e991d37b7bbc51d15c1a89c0d96d40920f3b79a404cede5bad2943e` である。同梱read-only source checkerは172/172 SHA一致。

**remote commit `1db30cd1678d40340cd445204ec97a08590c24d5` を今回再cloneしたという確認ではない。** 既存受入れ済みファイルと、宣言されたinventoryとの対応を確認した。最終commit/tagは実際のrepositoryで記録する。

## 2. RC-2/RC-3と資産の独立確認

### 2.1 使用前期限・PC-1・環境条件

採用追補§7とmanifestのpre_use_gatesは、pseudo側完全archiveを正式global較正前、較正先行driverを正式global較正の開始前、外部context等の再利用を較正を含む最初の正式再利用前へ統一した。environment_lockにはNumPy OpenBLAS=2と他pool<=2が揃っている。実行環境の新版に変更する修正ではない。

PC-1は、工程分離の承認と物理検証pendingを別に記録し、新9点×全該当size、旧anchorから成功を転記しない、既存A11式／許容値を保持する、較正を含む正式使用前に受入れる、技術失敗でprior massを削除・再正規化しない、という条件を保持している。

### 2.2 checkerの採用・再試験

提出checkerは、前回提供した参考checkerと全bytes一致した。実際に実行し、packet 22項目、accepted source 172項目、本文/tables binding、保存registry/gridの復元とA6/A7からの再構築、資産／receipt／監査書の照合を通過した。

前回の15対照の入力変更・期待値を保ち、現在のpacket/sourceへ再適用した。**正常1件は受理、不整合14件はすべて拒否**した。

| TEST-ONLY対照の要点 | 今回 |
|---|---|
| 追補／期限を編集、inventory据置 | 拒否 |
| packet inventory欠落 | 拒否 |
| engine module／source inventoryの変更 | import前に拒否 |
| 保存gridのweightを変更しfile SHAだけ更新 | 内容契約違反として拒否 |
| 保存grid payload／registry不一致 | 拒否 |
| 共有null宣言B_maxだけ変更 | 拒否 |
| 本文／監査書の変更、未登録追加file | 拒否 |
| outer inventoryとhandoff commitの相違 | 拒否 |
| 原文v0.5を編集し局所SHAも更新 | 固定した原文SHAと異なり拒否 |

別に外側SHAの3対照を実行した。正しいSHAはPASS、誤ったSHAは拒否、指定なしは内部整合性のみPASSで `outer_inventory_pinned=False` となる。これらは同じ境界の複数条件であり、18種類の独立した科学的検証を主張しない。

### 2.3 保存grid・過去資産との対応

保存registryをsource-bound復元し、保存configuration manifest自体をdeserialize・validateした。A6/A7からの再構築と全体が一致した。E1=3、E2/E7/E8=各9、計30配置。各familyのweight和1、x0_CT=-r_obs、A7全30行との照合を確認。

12位置JSON、幾何CSV、共有nullJSONは、保持している元のA/B出力ZIP内のmemberとbyte一致。receiptは前回のmetadata補正版と一致。監査書9本は対応する保持原本と一致した。今回、外部poolからの全OT、12位置の全格子、幾何CSVの外部探索を再実行したという意味ではない。

## 3. 今回の新しい原文確認：v0.3 §14

現在の追補は「v0.3の原文照合後にnoise仕様を固定する」としている。今回、Libraryで **`Step1_研究計画_v0.3_ChatGPT確認用.md`** を発見し、全文を取得したうえでnoise/robustnessに関する節を現在の採用案と対照した。

- bytes：14,387。
- SHA256：`bac9dbfe7dfb70baa4a6ca5f1d3dc8f24c65641ebf01e3693171a4022c2abfb8`。
- §14（原ファイルL184–189）の対象は **E7、L=1.0、第1観測点の1点**。
- 低ℓnoise covarianceを加算し、Q_jの変化を報告する。候補はhalf-mission差分またはNPIPE simsで、入手可能性はPhase Aで確認する計画。
- 元の判定はMC CI内ならnoise-insensitive、外なら主結論へ注記。
- v0.5 L91はこの判定を効果量・category・marginの3条件へ更新し、MC CI比較を併記へ下げた。

従って、「v0.4/v0.5の差分本文に定義がない」は正しいが、「原定義が未確認なので対象を自由に決めてよい」わけではない。基準1点と共分散加算という旧定義を出発点にし、A6/A11の現行座標・IDへの対応を明示する。現gridのE7/L1.00/observer_id=1はconfig_id=30101だが、この対応を採用する判断・系統・対象を最終noise仕様に記録し、古い数値座標や開発用mockと同一だと推定しない。

**v0.3を今回の受領packetへ既に同梱していたとはしない。** 監査の追加参照として取得し、証拠ZIPに不変の原本とSHAを保存する。v0.3自体もv0.2からの差分であり、全旧版の要件を今回遡及的に再承認したという意味ではない。

## 4. noiseの移管案に対する判断

### 4.1 scopeを分けることには賛成

元のv0.3 §14は1点の感度を報告し、影響があれば結論に注記する構成である。一方、現在のcoreは固定S1 surrogate、登録family/prior、Q/logD、較正usableという明示された判定である。この第一段階のcoreを維持し、noiseを独立した感度診断として併記する構成は整合的である。

ただし、draft4.1 §1.8の直接の対象は「他3mapの同方向」であり、§9.1の較正scopeとの類推だけでnoise移管が既承認だったとはしない。**今回、元のnoise要件のscope・工程を明示的に採用する判断**である。

coreの計算・較正を変えないことと、noiseが物理的に結果へ影響しないことは別である。後者は未測定であり、移管しただけでnoise-insensitiveにならない。

### 4.2 現記述の重要な補足：実施を遅らせても、仕様は結果前に固定

現在の「label解放前に実装・監査」だけでは、full-grid結果を計算・閲覧した後、公開前にnoise水準や対象・marginを決めても文言上は間に合ってしまう。

要求する区別は以下の2つである。

1. **仕様固定・事前検証**：未見の正式full-grid結果またはnoise-added結果を生成・閲覧する前に、noise入力・水準・対象・target・反復／乱数・category・margin・異常時処理・報告方法を固定し監査する。既知のStep0 targetと開発pilotを隠して「完全blind」とは記録しない。
2. **実測・結果監査**：Phase Eで、公開／label解放前に完了する。試験で不合格だったことと、試験自体が未実施・技術失敗であることを区別する。

これはnoise計算をPhase Cへ前倒しする要求ではない。core freezeでは移管方針とこのgateを固定し、詳細noise仕様を後に固定する場合にも、その期限が未見結果の前であることを保証する。現在の提案statusを著者確認なしに完了へ変えない。

### 4.3 原基準・点scope・結果の扱い

noise-insensitiveの判定は、v0.5の3条件（|Δ log Q_j|<0.1、category不変、変化がmarginの20%未満）のANDを保持する。MC CI内かどうかだけでは判定しない。

Q_jは点の診断で、正式なfamily coreはQ_Mである。categoryが何を比較するか、marginをどの判定量・境界から測るかを事前に明示する。margin=0、Q=0/undefined、精度未達、技術失敗を自動的に安定PASSにしない。これらの詳細は今packetに定義されていないため、本監査で勝手に補完・確定しない。

原基準の1点を残すなら、その点でのrobustnessとして報告する。全family・全size・全位置が頑健であるという表現へ一般化しない。正式結果で支持が大きい点への事後的差替えをしない。対象の拡張は前向きな仕様で登録できるが、今回すべての点への大規模noise試験を新たに要求するものではない。

結果は例えば `core_result` と `noise_robustness_result` を分ける。core supportでもnoise-sensitiveなら、主要結果と同じ場所でその限定を報告する。noise失敗を理由に封印済みcoreの数値・label・calibration usableを遡及改変せず、同時に「noiseに頑健な物理的証拠」とは無条件に説明しない。

未知・未実施・技術失敗はPASSと区別し、結果監査前に頑健性を付与しない。noise追加がcore本体の真の実装異常を発見した場合、その異常を「較正外」で免責することもない。

### 4.4 較正の意味

独立した記述的診断だけを追加して元のcoreを変えないなら、現在のcore較正アルゴリズムを改訂する必要はない。しかし、その較正の保証をnoiseを含む観測過程全体や、歴史的軸選択の全手順へ拡張してはならない。draft4.1 §2.1/§9の限定を維持する。

noiseを正式primaryへ組み込み、target／分布／採択・分類規則を変更する場合は、別の設計変更・較正を要する。今回の方針はその変更を行わない。

## 5. 文書の仕上げと最終freeze

`Step1_PhaseC_noise_policy_recommendation.md` に、§2.1の差替え案、二段階gate、manifest field案を示した。これは著者判断待ちの文案であり、受領packetを変更した完成overlayではない。

最終採用時は、次を揃える。

- 今回のv0.3 noise関連節の照合と原本SHAを外側の採用記録へ追加する。前回監査が未取得だったという歴史を遡及改変しない。
- policyの監査判断と著者の採用判断、仕様実装、試験実行、試験成績を別statusにする。
- noise仕様の固定期限と、実測／結果監査の期限を分ける。
- §9の「§7の各機能の実装と監査→…」は、それぞれの使用前期限という意味へ整理し、Phase E noise実測までcore較正前に一律要求する記載にしない。
- 本文・tables・engine・数値資産・過去のrun/監査は変更せず、最終追補／manifest等のbytesでpacket inventoryを更新する。新しい外側receiptでcheckerを通す。

**今回受領したinventory `82bbef93…` はこの提案状態のpacketの識別値であり、未作成の最終採用版のSHAではない。** 著者確認と上記文言を反映すれば、規則／登録資産／受入済み基盤sourceのPhase C採用を確定してよいという判断である。未実装production機能の完成や実測noise PASSを宣言するものではない。

## 6. 実施した検査と限界

| 検査 | 今回の実行 |
|---|---|
| ZIP/単独添付/packet identity | 23実ファイル・22 inventory項目、すべて一致 |
| accepted source checker | 172項目一致、0.54.0 |
| saved gridの復元＋source-bound再構築 | 30配置・A7全30行一致 |
| 旧資産／receipt／監査書のbyte比較 | 一致 |
| 前回15入力対照を現在checkerへ適用 | 15/15期待動作（正常1／拒否14） |
| 外側SHAの3対照 | 正しいSHAでPASS、誤SHA拒否、指定なしは内部整合性のみ |
| noise原定義の追加照合 | Library取得のv0.3 §14等をv0.5/current案へ対照 |

15は包装・検証境界の入力条件数で、科学的実験の数ではない。今回の主要な追加作業は政策判断と登録情報の監査である。

監査環境：Python 3.13.5、NumPy 2.3.5、SciPy 1.17.0、検査processのBLAS/OMP/MKLを1 threadに設定。登録Colab環境そのものではない。packageの新規インストールなし。

**未実施**：新Colab、実Drive、noiseデータの取得・利用可能性／仕様確定／stress試験、A11物理clone、新しいsky／bank生成、12位置全格子、全OT、全909件pytest、正式較正、remote handoff commitの再clone、最終commit/tag作成、著者の採用操作。

受領packet23ファイルとaccepted source185ファイルは終了時に原本／前回受入れsourceへ再照合し、変更・欠落・追加0である。原文や過去の監査結果を新たな結果へ書き換えていない。

## 7. 最終判断

**技術面の改訂は受入れ。noise stress testのPhase E記述的qualifierへの移管は、仕様を未見結果の前に固定し、原1点scope・v0.5基準・独立した結果報告を保持する条件で支持する。最終著者確認とそのgateを採用文書に反映してPhase Cを確定する。過去の数値計算の再実行は不要。**

主な証拠：`evidence/identity_and_grid.json`、`source_check.json`、`comparison.json`、`checker_baseline.json`、`verifier_probes.json`、`outer_binding.json`、`final_integrity.json`、`scripts/`、今回取得のv0.3原本。checker/sourceは受領／既受入れのまま保持している。
