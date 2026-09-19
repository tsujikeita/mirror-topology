# Step1 rules v1.0 — 採用宣言と凍結 packet の追補（方式 A）
2026-09-19。Claude作成（Phase C packet **final**＝承認済み v0.4 の内容に，v0.4 監査書と v0.3 対照表を証拠として追加；追補・manifest の政策内容は v0.4 から不変，metadata（audits 一覧・inventory・revision 表示）のみ更新）。

## 0. この packet が行うこと・行わないこと
- **行うこと**：`Step1_rules_v1.0_draft4.1.md`（file SHA `5f02c970…`）と `rules_tables_v1.json`（`522751be…`）を **bytes を変えずに** Step1 rules v1.0 として採用する宣言；登録資産（第 1 波 grid manifest・12 位置 asset・共有 W₂ null）と受入れ済み source・監査 receipt を凍結 manifest（`Step1_rules_v1.0_freeze_manifest.json`）に束ねる；研究計画 v0.4／v0.5 の**原文を同梱**して独立照合を求める；工程変更案と未実装機能の使用前 gate を明示する。
- **行わないこと**：本文・数値・predicate の変更（方式 A：本文に追記しない），ENGINE_VALID，完成 production engine の宣言，global 較正，calibration usable，実観測 label の解放，工程変更案の自己承認。

## 1. 本文と tables の binding（方式 A）
`rules_tables_v1.json` は `rules_document.sha256` で本文 bytes を束縛し，`step1_engine.rules_config` は import 時に一致を要求する。したがって本文への追記は tables の再束縛を要する。Phase C は本文・tables の bytes を保ち，登録参照・採用宣言・工程変更案を本追補と凍結 manifest に置く。既存 run manifest・自己試験 record・監査書内の SHA は書き換えない。

## 2. 研究計画原文の照合（記録）
研究計画 v0.4／v0.5 の同梱原文は draft4.1 L4 の完全 SHA と一致し，**2026-09-19 の Phase C 監査（ChatGPT）で全文を対照した**（33 項目の対照表 `audits/ChatGPT_originals_correspondence_2026-09-19.md`；整理項目数であり検定数ではない）。v0.4 は v0.3 からの変更点のみを記した文書であり，今回の照合を**原文 v0.3 自体の独立照合とは呼ばない**（family 集合・support の D 点条件など v0.3 にのみ出典を置く箇所は既往受入れを維持）。Event B，legacy phenotype の非 veto 化，W₂ の標本数（20,000→2,000/5,000）・null（2 標本→disjoint 3 block の max）・停止規則（B=200→最大 1000 の prefix 停止），A6/A11 座標，CRN の key 分離，ESS の撤回，S1 の float32 感度経路は，v0.5 L3–4 の定めるとおり Phase A 実測を反映した**後続の明示的変更**として読む（「すべてが無変更の継承」ではない）。
- 付録 B の「D の CI：未定義」は正確には，**CI を用いる判定は v0.4 §8（上側）・v0.5 定義 4（下側）で既定であり，新規に固定したのは密度推定器・cluster bootstrap・区間計算の手順**である。
- 付録 B の dtype 行（S2 float32 HOLD）は不足で，現在の §5.2／§10.1／§12.5 にある **S1 および全 W₂ bank の paired float32 感度経路**を含む（原文 v0.4 §9／v0.5 L92 は float64 のみ；後続の明示的変更）。
- draft §1.1 の固定軸 trace 式 E[S⁺−S⁻]=tr[(B⁺−B⁻)C]>0 は今回の v0.4 原文には見当たらないため，**今回の 2 原文の直接照合済み項目から外し**，出典を前段研究（Step 0／T1 監査）へ分ける（式の真偽の判定ではない）。付録 B 左欄の「原文から転記」は要約・前段参照を含む。

### 2.1 noise stress test の採用 scope【著者決定：2026-09-19 確定】
研究計画 v0.3 §14 の 1 点診断（E7・L=1.0・第 1 観測点に低 ℓ ノイズ共分散を加えて Q_j の変化を調べる；候補は half-mission 差分または NPIPE sims）と v0.5 L91 の受入れ基準（|Δ log Q_j| < 0.1 ∧ support category 不変 ∧ 判定境界からの margin の 20% 未満；MC CI 比較は併記のみ）を保持し，**実施を Phase E の記述的 robustness qualifier へ移す**。著者（辻氏）は 2026-09-19 にこの移管に同意し，監査の条件を採用した。これは noise 試験を撤回・実施済みとする変更ではない。v0.5 定義 4／draft4.1 §1.8／§9.1 の明示的 robustness は他の成分分離 map の比較であり，noise が自動的にその scope に入っていたとは断定せず，本追補で追加・明文化された移管判断として記録する。
- **原定義と対象**：基準対象は v0.3 の E7・L=1.0・第 1 観測点。現在の A6/A11 座標定義と第 1 波の不変 ID への対応を robustness spec で固定する。旧版の未確定座標や開発用 mock を無条件に流用せず，正式結果が良好だった点への事後的差替えもしない。1 点の検査を全 family・全 size・全位置の頑健性の保証とはしない；対象拡張はその目的・範囲を別に事前固定する。
- **仕様固定の期限（gate 1）**：noise 入力の出典・SHA・共分散／単位／基底・正規化・水準・加算位置，target の扱い，対象点と系統，反復・乱数・再抽出，category と margin の定義，境界／未知／技術失敗の扱い，報告方法を，**未見の正式 full-grid 判定結果または noise-added 結果を生成・閲覧する前**に固定し，実装の人工対照とともに監査する。既知の Step 0 target・開発 pilot の存在は既存 §0.2 どおり開示し「一切のデータを見ていない登録」とは呼ばない。試験結果に応じて条件を緩めない。
- **実施の期限（gate 2）**：固定済み仕様による noise 試験の実測と結果監査は，Phase E で，**実観測結果の公開・label 解放前**に完了する。Phase C で実測することは要求しない。Phase E という工程名を，結果閲覧後の仕様決定を許す理由にしない。
- **判定と scope**：noise-insensitive を付けるには v0.5 の 3 条件をすべて要求し，MC CI 比較は併記に留める。Q_j は点の診断であり family-level の core label とは区別する。category 比較が点診断か family 判定か，margin をどの量・どの境界から測るかは実施前仕様で一意にする。margin=0・Q=0/undefined・精度未達・技術失敗を自動 PASS にしない。
- **報告**：封印済み core 結果と noise 診断を別 field で併記する。科学的 FAIL・未解決・技術的 FAIL・未実施を区別し，FAIL でも core の計算記録を遡及改変せず，頑健な物理解釈を無条件には主張しない。core が支持でも noise-sensitive ならその限定を主要結果と同じ場所へ記載する。noise 診断を選別・閾値調整・prior 変更・較正成功化へ利用しない。追加診断の技術失敗は当該診断の失敗として保持し，core 本体の技術失敗を robustness へ付け替えて免責しない。
- **保証範囲**：core の false-support 較正は元の登録 S1 手順・MC 資産に対する scope を維持し，noise を含む観測過程や歴史的実観測手順全体の保証へ拡張しない。noise 込みの手順を新しい primary へ変える場合は別の設計変更・較正・受入れを要する。
- 研究計画 v0.3 原文（`originals/Step1_research_plan_v0.3.md`；SHA `bac9dbfe7dfb70baa4a6ca5f1d3dc8f24c65641ebf01e3693171a4022c2abfb8`，14,387 bytes；監査が Library で確認した値と一致）を同梱した。§14（L184–189）の逐語：「主判定に用いる 1 モデル点（E7・L=1.0・x₀^(1)）について，低 ℓ ノイズ共分散（CMBanom に含まれる half-mission 差分 or NPIPE sims から推定・利用可能なものを Phase A で確認）を加算し，Q_j の変化を報告。変化が Q_j の CI 内なら『noise-insensitive』，外なら主結論に注記。単一周波数マップは stress test 扱いのまま。」——本追補の採用 scope はこの定義を保持し，判定基準のみ v0.5 L91（効果量・category・margin；MC CI 比較は併記）へ更新する。v0.3 原文全体の照合は，2026-09-19 の Phase C v0.4 監査で全 209 行が対照され（34 項目：`audits/ChatGPT_v03_original_correspondence_2026-09-19.md`），Phase C 採用対象として承認された。監査の補足：**strong の D 下側 CI > 1 は v0.3 §3（L67–68）に既存**であり，v0.5 で初めて導入したものではない（v0.3 の unsupported は D 点値 ≤ 1，v0.4 §8 で D 上側 CI を用いる後続変更）。方式 A のため本文は編集せず，この出典補足は監査書と対照表で保持する。監査が完了したのは全文を読んだ原文対応の監査であり，旧差分文書の全タスク（CRN なし 1 点検算・10 batch 分散 CI・Davies 検算など）を実装・実行済みと認定するものではない。

## 3. 第 1 波 grid manifest（rules §4.7）
`registered/first_wave_configuration_manifest.json`：source-bound registry（凍結 A6/A7 SHA 束縛）から導出した 30 配置——immutable `config_id`（family／size code／観測点），登録 shape params（L_LSS 単位），full-precision reduced coords，凍結 A6 lift → `r_obs`，`x0_CT = −r_obs`，cache key，circle status（observational／geometric），配置 prior（E1 1/3，他 1/9）。凍結 A7 CSV と 30/30 行一致（shape JSON・`r_obs_LLSS`・status）。12 位置 asset はこの manifest の代用ではない（3 位置段階の登録 grid と 12 位置段階の設計を区別）。

## 4. 登録資産（`registered/`；SHA は凍結 manifest）
| 資産 | 用途 | intake |
|---|---|---|
| 12 位置 asset（E2/E7/E8 × 3 size） | 12 位置段階の設計（rules §10.4） | receipt 束縛 intake（再生成の証明は B-3-2A run と監査） |
| 12 位置 circle 幾何 CSV（108 行） | 新 9 点の幾何 status・prior | 幾何のみ（物理共分散の clone 同値は PC-1） |
| 共有 W₂ null asset | rules §10.1 の等方 null（n_sub 2000／5000・B_max 1000） | `SharedNullAsset.validate`＋正式 intake（w2_manifest／w2_context）；case 別 stop／B_final／trigger は資産に含まれない |
| 大規模資産（pool・control bank・checkpoint） | 再検証用 | packet 外（著者保管）；SHA で参照，使用前に再検証 |

## 5. 受入れ済み source と現 source
数値を生成した source（B-3-0 `7045fc1a…`／B-3-1 `903458d7…`／B-3-2 `7240c06f…`）と，引渡し確定 commit **`1db30cd1678d40340cd445204ec97a08590c24d5`**（inventory `0ece0a3d…`，engine 0.54.0）を区別して記録する。引渡し commit は「受入れ済み基盤 source の固定」であり，未実装機能（§7）を含む production engine の凍結ではない。

## 6. 工程変更 PC-1（監査で条件付き承認；物理検証は pending）
**PC-1**：新 9 観測点の A11 物理共分散 clone 同値性——移管表では「B-3／Phase C 前」だったが，該当共分散は Phase D で初めて生成されるため，Phase D の共分散生成時に検証し，**当該共分散／bank を較正を含む正式処理で使う前に必ず受入れる**工程分離として，2026-09-19 の Phase C 監査で**承認**された（履歴上の記述は削除しない）。条件：(1) 幾何 nearest-clone／circle／prior は B-3-2A の受入れ範囲として保持し物理同値と混同しない；(2) 対象は新 9 位置×該当する全 surviving size；旧 anchor の成功を新点へ転記しない；既存 A11 の式・許容値・identity 契約を保持；(3) 検証に数値生成が要る場合は隔離した検証用 scope で行い未検証値を正式出力へ流用しない；(4) 技術失敗・未検証を無視して点や prior mass を削除・再正規化しない；(5) source・環境・共分散／変換・出力 SHA と結果を保存する。manifest の status：`APPROVED_SCHEDULING_SPLIT_WITH_PRE_USE_GATE; PHYSICAL_VALIDATION_PENDING`。Phase C 通過を PC-1 の物理 gate の PASS へ移管しない。

## 7. 未実装機能の使用前 gate（B-3-3 v2 補正版と同一；Phase 名ではなく「何を初めて使う前か」で定義）
| 機能 | 使用前 gate |
|---|---|
| 正式 12 位置 profile gate | Phase D の 12 位置 bank 生成前 |
| pseudo 側完全 Result archive | **全手順の正式 global 較正（12 位置分岐を含む）を実行する前** |
| 較正先行 driver | **正式 global 較正を開始する前に実装・受入れ**；calibration usable の封印前に実観測 full-grid target を計算しない |
| production 共分散 intake（run profile・array SHA 再計算・PSD）と Phase D bank 生成器 | Phase D 開始時 |
| 外部 W₂／context／run／coordinator record の再利用 | **較正を含む最初の正式再利用前**（Phase D か E かの名称で後回しにしない） |
| 統合 runner の登録 asset 再利用接続 | 統合 runner の正式再利用前 |
| case 別 W₂ の stop／B_final／trigger（実 bank） | 較正・判定で初めて使う前 |
| Drive 世代の実復元 | 初回の実 resume 時に記録 |
| noise 仕様・実装の事前検証（§2.1 gate 1） | 未見の正式 full-grid 結果／noise-added 結果の生成・閲覧前 |
| noise 実測・結果監査（§2.1 gate 2） | Phase E，実観測結果の公開・label 解放前 |

## 8. 検証
`verify_phaseC_packet.py`（監査提供の参考 checker を採用；read-only）：`PACKET_INVENTORY.json` の実読込みによる file 集合／SHA／サイズの照合，accepted engine の inventory（172 項目）と版の照合を import 前に実施，保存 registry／configuration manifest 自体の復元・validate と source-bound 再構築との比較，登録資産・receipt・監査書の SHA 照合，`--expected-inventory-sha256` による外側 receipt との束縛。科学的妥当性・noise 方針・工程承認・remote commit の真正性・物理計算の完了は自動承認しない。

## 9. Phase D／E への入口（各機能を各使用前期限までに受入れる）
1. core に必要な機能（§7）の実装と監査 → 2. 固定 MC 資産・全 family・固定 2000 pseudo・12 位置分岐・完全 archive の契約確認と較正先行 driver の受入れ；**noise 仕様は未見結果を生成する段階より前に確定**（gate 1） → 3. bank 固定 → 実観測値封印下の global 較正・監査 → usable 封印 → 4. Phase E の実観測 full-grid 評価 → 固定仕様の robustness 試験（noise）と結果監査 → 一緒に公開・解放。noise 実測を較正より前に終える記載にはしない。
