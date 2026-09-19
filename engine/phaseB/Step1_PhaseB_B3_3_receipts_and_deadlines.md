# Step1 Phase B・B-3-3 — 受入れ receipt の集約・登録資産・未実装項目の受入期限（Phase C packet 準備）
2026-09-19（v2：監査 R331-A/B/C・§7 反映）。Claude作成。本 packet は，受入れ済み B-3-2 A/B の登録資産と過去の receipt を集約し，固定された 12 位置資産を登録 file SHA／payload SHA で取り込む入口を追加するものである。新しい科学的数値計算は行わないが，**engine の受付実装は変更している**（`twelve_assets.py`：receipt 束縛 intake，監査 R331-A の source-bound ガード適用を含む；`__init__` 0.54.0；各 pins の `engine_version`）。数値 kernel・builder・計算 script・科学的設定値は 0.52.0 から不変。規則本文（draft4.1）・tables JSON・spec v0.2 追補は不変。**現在の source（0.54.0）と，A/B を生成した受入れ済み source（0.52.0，commit `7240c06f…`）は区別して記録する。**

## 1. 受入れ receipt（独立監査による；B-2 は sandbox 実装受入れ，B-3-0／1／2 は Colab 実行後受入れ）
| 工程 | commit（engine） | run ID（UTC） | 出力 | 監査書 | 判定・scope |
|---|---|---|---|---|---|
| B-2 実装受入れ | tranche 35/36 packet（0.39.0→0.40.0）；維持：v0.4 packet（0.43.0，inventory `13c7f89a…`） | — | 815／827 case | `…B2_tranche35.md`／`tranche36.md` | accepted（sandbox 実装；Colab 側受入れは B-3 へ移管） |
| B-3-0 smoke | `7045fc1a17b63755d66671c97882a32d7c2309c7`（0.44.0） | `20260917T092845Z` | `b3_0_out_7045fc1a17b6.zip` `d3386faa…`／notebook `bd423712…` | `…B3_0_Colab_7045fc1a17b6.md` | **PASS**：mock-grid smoke・T10 実 bank・T19/A5・legacy 3 回帰（B-3-0 の規模） |
| B-3-1 official 規模 control | `903458d71e94…`（0.47.0） | `20260917T154350Z` | `b3_1_out_903458d71e94.zip`（133 MB） | `…B3_1_Colab_903458d71e94.md` | **PASS**：negative 確定 False・率 0/200・登録 positive strong（Q=100）・conjunct 電池（strong 7 drop＋support 4 drop；base 2 件は別）・brute-force・A5；1 配置 control profile |
| B-3-2 A 12 位置 asset・circle 幾何 | `7240c06f255cd206ae3e2db6210ce7efd66e1b32`（0.52.0，inventory `857b2f37…`） | `20260918T094339Z`（5.08 h） | `b3_2A_out_7240c06f255c.zip` `ed4e2f10…` | `…B3_2_Colab_7240c06f255c.md` | **PASS**：E2/E7/E8 各 3 size の 12 点を監査が独立再生成し完全一致；108 行すべて surviving；A11 物理 clone は scope 外 |
| B-3-2 B 共有 W₂ null | 同上 | `20260918T152513Z`（7.88 h） | `b3_2B_out_7240c06f255c.zip` `c81bccb9…` | 同上 | **PASS**：校正 2×10⁵（A10 official と **bit 一致**）・null 6×10⁵・n_sub 2000/5000 × 1000 反復；抽出列・分位・exact OT 抜取りを独立照合；Drive 世代の実復元は未検証 |

## 2. 登録資産（Phase C packet の登録表；`registered_assets/` に同梱・receipt 束縛）
| 資産 | file SHA256 | 内容 SHA256 | intake |
|---|---|---|---|
| `b3_2_twelve_assets.json`（E2/E7/E8 × 3 size の 12 位置 manifest） | `be6860ba2ffbdd798d8a300b2268281bbade1d2b7f33b5b0748dc550ef90d557` | asset `1d05e6b3afc86f8da94765cebe128f2b291bc523c10599dcb6e54ff7be01d89c`（E2 L1.00 `fa229fbb…`，E7 L1.00 `2353449e…`，E8 L1.00 `2819142c…` ほか計 9） | `twelve_assets.intake_registered_twelve_assets(…, 'B3_2A_7240c06f255c')`：file SHA・asset SHA・**source-bound registry（`_registry`）**・構造検査。**再生成省略の scope**：この intake と `get`／`snapshot`，および `evaluate_family_full` へ渡す経路では再生成を省略できる（根拠は B-3-2A 受入れ；この呼出しで再実行したとは記録しない）。**現 `run_first_wave` は入口で `verify_twelve_assets`（全 manifest 再生成）を呼ぶため，統合 runner からの再生成除去は未接続**——正式再利用前の残件（§3）。既存の再生成検査入口は残す |
| `b3_2_twelve_geometry.csv`（108 行の circle 幾何） | `c0f0bf0eb7ca3fadee70d2437443e926bed65ac5a89685b7a2c712a7dffab641` | — | 既存 27 anchor は凍結 A7 と一致；新 81 行は承認 script の出力（A11 物理 clone 検査は別） |
| `b3_2_shared_null_asset.json`（共有 W₂ null） | `cc67686744f513e3123de2fb8353d79491d4b1deaff2b8d9ecb5f93d0f95afb4` | asset `8348d5f4733ae5a37e39f4aa88109626e5caab312b55bd108be7ec9e5daff3ba` | `SharedNullAsset.validate`（payload SHA；identity：iso K=6000・m=100・exact_pot_w2・master 20260912） |
| null pool／校正 bank（`b3_2_pools.npz`，43 MB） | `451f8bc5446c03956ba5598b326532584805488326b0623b009c5e7dc530c987` | 校正 bank は A10 official checkpoint と bit 一致 | 出力 zip に保持（packet 外；SHA で参照） |
記録値（診断）：q99（全 1000 反復）n=2000 0.2329・n=5000 0.1533；replicate bound の最大 0.0035／0.0025。**共有 null の `q99_full` を全 case の final q99 として流用しない**（case 別 B_final の q99 は case の停止規則で決まる）。`SharedNullAsset.validate` 単体は payload 整合の検査であり，live pool／W／case 入力照合を代行する正式再利用入口ではない。

機械可読 receipt：`registered_assets/b3_3_receipts.json`。本監査側訂正候補では、B-3-0／1／2のcommit・出力file/member SHAを実ファイルから完全値で補完し、監査書のfile SHAを付した。B-2のcommitは未確認のためnullと理由を保持し、packetによる初回受入れと0.43.0での後続維持を区別する（新しい計算・過去recordの書換えは行わない）。

## 3. 未実装項目と受入期限（監査 §10；期限は「正式使用前」を後ろ倒しにしない）
| 項目 | 現状 | 受入期限（gate） |
|---|---|---|
| 正式 12 位置 profile の gate（第 1 波 profile の流用禁止） | 未実装 | Phase D の 12 位置 bank 生成前（12 位置 stage の official 評価に先立つ） |
| pseudo 側 12 位置完全 Result の archive（要約と再現証拠の区別） | 未実装 | 正式全手順較正の実行前。完全なResultと再現証拠の保存・復元を確認する（工程の呼称にかかわらず較正受入れに先立つ） |
| 較正先行・実観測 full-grid 値の封印（rules §9.4） | 未実装（現 runner は target-first；合成開発用） | 実観測full-grid判定値を先に計算しないdriverの受入れと封印を、正式global較正の実行前に完了する。較正・監査→usable封印→Phase Eの実観測評価・解放の順（§4.3と同一） |
| production 共分散の完全 intake（run profile・array SHA 再計算・PSD）／Phase D bank 生成器 | 未実装（geometry matcher と legacy 回帰 kernel のみ） | Phase D 開始時 |
| checkpoint の外部 W₂／context 参照・run/coordinator を含む再利用契約 | 未実装 | 較正を含め、その記録・外部参照を正式に初めて再利用する前（Phase Eより前に再利用する場合も同じ） |
| 統合 runner（`run_first_wave`）の登録 asset 再利用接続（期待 asset SHA・whole-asset receipt・source-bound registry・独立 snapshot・終了時 payload 再確認を維持したまま `verify_twelve_assets` の無条件再生成を置換） | 未接続（evaluator 経路は再生成なし） | 統合 runner の正式再利用前 |
| 新 12 位置の A11 物理共分散変換・clone 同値性 | 未実施 | **工程変更として明記**：旧移管表の「新 9 点 circle coverage／clone／prior：B-3／Phase C 前」のうち，幾何 nearest-clone・circle status・prior は B-3-2A で受入れ済み；**物理共分散の同値性**は当該共分散が Phase D で初めて生成されるため Phase D の 12 位置共分散生成時（当該 bank の正式使用前）を gate とする。この分担は Phase C で確認を受ける（本文書だけで既承認とはしない） |
| observed 側 case 別 W₂（stop・B_final・trigger）の実 bank 実行 | 未実施 | これらの決定を較正・判定で初めて使う前（共有 null の完成とは区別） |
| Drive 世代からの実復元 | 未検証（B は fresh 完走） | 次に再開が必要になった実行で記録 |
| E2 資産・共有 null の runtime（A 5.1 h・B 7.9 h） | 実測済み（見積り超過） | Phase C 運用資料に実測として記載 |

## 4. Phase C packet の構成（案；監査 R331-C を反映）
### 4.1 本文と tables の binding（方式 A を採用；混在させない）
現 `rules_tables_v1.json` は `rules_document.name/sha256` で本文 file bytes を束縛し，`rules_config.verify_binding` がその一致を要求する。したがって「本文に追記しつつ JSON 不変」は成立しない。Phase C は **方式 A**：draft4.1 本文と参照 JSON の bytes を保ち，登録資産表・receipt・「v1.0 として採用する」宣言・工程変更（§3 の clone 分担）を**別の凍結 manifest／追補**に記録する（本文 SHA を変えない）。過去の run manifest 内の旧 SHA・自己試験 record は書き換えない。
### 4.2 checklist（既存要件を落とさない）
- 採用本文と tables の整合した binding（方式 A）と，差分の科学的意味の区分（本文・数値・predicate 不変）。
- 研究計画 v0.4 原文（SHA `0569ae2f9cbd3003d1f08840b43f20c14e8da3e07ca7718743929ee138235371`）と v0.5 原文（SHA `357e4d7d0325e3284bd3dcf062a4c5e5bf7599b14032e90ab3da6912da5e9f18`）の同梱と，draft4.1 冒頭／末尾が要求する原文照合。
- 第 1 波 grid の full-precision 座標・単位・lift・immutable ID・circle status・prior・完全 SHA（`grid_manifest` の configuration manifest）；12 位置 asset を全 grid manifest の代用にしない。
- 受入れ済み source の commit／inventory（A/B 生成時 `7240c06f…`／`857b2f37…`）と現 source（本 packet）の区別，監査書・受入れ scope。
- 登録 12 位置・幾何 CSV・共有 null の file／payload SHA，A/B final record の完全 SHA（§2，`b3_3_receipts.json`）。
- packet 外資産（pool／校正 bank・checkpoint・run manifest・出力 zip）の所在・member SHA・取得と再検証の方法（大きい bank は同梱しない）。
- 未実装項目の機能別受入期限（§3）と，「受入れ済み基盤 source の固定」と「未実装機能を含む production engine の凍結」の区別（現 engine を完成済み production engine と呼ばない）。
### 4.3 Phase C 以降の依存順序（rules §9.4 を維持）
1. 正式使用前の各機能（production 共分散 intake／bank 生成器／正式 12 位置 profile／pseudo 完全 archive／外部参照再利用／統合 runner の登録 asset 接続）の実装・監査。
2. 固定 MC 資産・全 family・固定 2000 pseudo・12 位置分岐・完全 archive の契約確認と，**実観測の full-grid target を計算しない較正先行 driver** の受入れ（現 target-first runner を先に official 実行して封印する運用は採らない）。
3. bank 等の固定 → 実観測 full-grid 判定値を封印した状態で global 較正・監査 → calibration usable の封印 → Phase E の実観測 full-grid 評価・解放。
4. case 別 W₂ の stop／B_final／trigger は，較正・判定で初めて使う前に受入れる。
## 5. 表現の限定
B-3-3 は文書と receipt 束縛の登録であり，新しい科学的数値計算・科学的判断を含まない（engine の受付実装は変更している）。ENGINE_VALID・Phase C の科学的 freeze・global 較正・label 解放は本文書の承認範囲外（ChatGPT の監査で判断）。

> 監査側メタデータ訂正候補（2026-09-19）：上記receiptの完全値と§3の期限表記を補完した。受付関数・数値source・本文／tables・登録資産は提出v2のまま。物理cloneの工程分担はPhase Cで確認する提案のままであり、本候補で自動承認していない。
