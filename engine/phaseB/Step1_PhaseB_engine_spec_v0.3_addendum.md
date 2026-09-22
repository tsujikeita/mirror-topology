# Step1_PhaseB_engine_spec v0.3 追補 — B-2 実装受入 packet（第 35 tranche 監査を反映）
初版：2026-09-16（Claude）。B-3-3 v2整理：2026-09-19。Phase D-1 起草：2026-09-20。以下の現行engineは `step1_engine 0.68.0（数値 kernel は 0.54.0 基盤の継承；D-2 tranche ① v2：RD2T1-A/B 反映）`（数値 kernel は 0.54.0＝受入れ済み基盤 `1db30cd1…` と同一；`d/` の追加のみ）（module／test／fixture／reference／doc の SHA inventory は `B2_completion_inventory.json`＋監査側 `B2_inventory_audit_supplement.json`）。

**B-2受入れ当時の判定ラベル（歴史的記録。現在の状態は§D.0とB-3-3文書を参照）**：`B2_implementation_acceptance=accepted`／`B2_original_Colab_acceptance=pending_explicit_carryover_to_B3`／`B3_notebook_preparation=go`／`ENGINE_VALID=not_evaluated`／`Phase_C_freeze=not_authorized`。規則本文 `Step1_rules_v1.0_draft4.1.md`（SHA `5f02c970…`）・`rules_tables_v1.json`（SHA `522751be…`）・spec v0.2 追補は不変。

## A. B-2 の成果（実装済み・ChatGPT 監査で契約閉鎖）
| 領域 | module | 契約の要点（監査 tranche） |
|---|---|---|
| 規則 binding | rules_config／serialization／truth／errors／types | JSON→golden 定数→predicate 文字列→本文 file SHA の三重 binding，strict JSON，三値 truth（B-1〜7） |
| 統計 core | ci／precision／decision／family／quantity／density／calibration | 境界値分位・fail-closed KDE・区間伝播・quantity adapter・literal 同値・Wilson(c+u)（B-1，B-2 t1–2，t28） |
| 再抽出 | bootstrap_plan／registry／plan_io | 層別 paired plan・FittingPlan identity・保存復元の再生成一致（t5–6，t16–17） |
| 位置／W₂ | positions／w2_stop／w2_manifest／w2_shared／w2_context／position_state | 実行時 identity snapshot・replay 検証・typed decision・共有 null（case 別 B_final／delta）・context 契約（t3–10，t24–27） |
| 12 位置 | observers12／observers12_stream／stage12／coordinator／twelve_eval／twelve_assets | 決定的生成器（2 走査）・canonical manifest・family rule・全 size mixture・固定 asset の intake／reuse（t11–16，t33–35） |
| grid／production | grid_registry／grid_manifest／production／official_gate／formal_runner | 凍結 A6/A7 束縛 registry・30 配置 manifest（A7 と一致）・x₀=−r_obs・cov manifest binding・official hard gate・fingerprint（t17–22） |
| 統合 | threshold_evaluator／integrated_runner／archive／checkpoint | 共通 evaluator（親必要量→位置→coordinator→12 位置→eligible truth）・pseudo 完全性・content-addressed archive・意味検証 reader（t29–34） |
| 回帰 | legacy_kernel／performance | A10 kernel の同一環境 bit 一致・Colab official との 1e-15 一致・性能 unit（t23–25） |

受入テスト（実体，D-2 tranche ① v2）：47 module・82 test file（自作 `test_b*` 28・`test_d*` 6・監査 `test_audit*` 48）・756 test 関数定義・1058 pytest case（parametrize 展開；B-2 受入時は 41／63／619／827）。監査原本の同梱区分：**原本保持**／**path 適応のみ**／**fixture 再生成**（t34・t35：配布しない pickle cache を in-process 生成に置換；assert 不変。t35 の12位置 fixture は `TwelveFixture` による原検査用入力から `twelve_from_cases` による入力へ変更しており、同じ数値標本の再現とは区別する）／**API 追従**（t29：result_ref→diagnostic_ref・injection hook を共通 evaluator へ）／**比較 oracle 訂正**（t28：高 offset KDE の literal 基準）——いずれも監査で承認済みの差分で，テスト緩和ではない。「意味検証 reader」の scope は core（保存 replicate・密度に条件付き）であり，外部 W₂/context 参照・run/coordinator を含む再利用契約の認証ではない。

**inventory の適用範囲**：現提出版の照合には `B2_completion_inventory.json` を用いる。`B2_inventory_audit_supplement.json` と `docs_B2_scope_and_B3_handoff_proposal_ChatGPT.md` は第35 tranche（engine 0.39.0）の監査時点の履歴資料として原bytesを保持し、現版のSHAや件数の代用にはしない。

## B. 元の B-2 受入条件のうち未完了のもの（**明示移管**；要件は削除せず，未実施を PASS にしない）

| 元要件 | 今回の根拠 | 移管先・完了条件 |
|---|---|---|
| v0.1 §B4.2 の Colab mock-grid engine smoke（E7・両系統・N=2×10⁴） | 未実施 | **B-3-0**：検証対象 commit・実測環境・必要 gate・出力 SHA・ログ |
| v0.2 T10 の実 bank／prefix-extension 検査 | 合成入力で層別／literal 同値は確認 | **B-3-0/1**：実 bank で UID・prefix/extension 再抽出を照合 |
| T19／A5 cross-check・legacy 実資産回帰 | Claude 環境で PASS 報告；監査側は SKIP | **B-3-0/1**：同一環境 legacy 比較と A5 map-based null 比較を区別して記録 |
| T14 の E2/E8 正式解像度・Colab 条件 | E7 独立 reference・E2 小格子は確認 | **B-3-2**：正式格子を生成・再生成照合し座標と完全 SHA を保存 |
| v0.1 §B4.3 の official control・ENGINE_VALID | helper の predicate／異常系のみ | **B-3-1**：negative・positive full predicate・conjunct-drop・brute-force・A5・finite inventory の必要 gate |
| 新規 12 位置の circle coverage・clone・prior 検査 | 設計 manifest の整合性のみ | **B-3/Phase C 前**：新規 9 点にも実施（旧 3 点の件数を転記しない） |

## B'. 「未実装」と「未実行」の区別（B-3／Phase C／D の受入範囲と混同しない）——**旧時点（B-2 受入れ時）の記述**；現在の状態は §D.0 と `Step1_PhaseB_B3_3_receipts_and_deadlines.md` に一本化
1. 実 bank・実共分散での評価。W₂ について：共有 null／context／統合 control は test-only 距離・人工 pool（POT を呼ぶ純平行移動 unit と性能 unit は Claude 側 POT 環境で実行）；登録規模の共有 null の正式生成と実 bank での全体試験は未実施。
2. **未実装**：正式 12 位置 profile の gate（第 1 波 profile を流用して合格扱いしない）；pseudo 側 12 位置完全 Result の archive（要約・SHA と完全な再現証拠を区別）；rules §9.4 の較正先行・実観測 full-grid 値の封印（現 target-first runner は合成開発用）；production 共分散の完全 intake／Phase D bank 生成器（geometry matcher・legacy 回帰 kernel と別物）；checkpoint の外部 W₂/context 参照・run/coordinator を含む再利用契約。
3. E2 正式 1e-4 格子の asset 生成と runtime 実測。
4. official 規模の性能実測（sandbox 単位計測のみ）。監査 §6.2 の訂正値：t2000=0.565 s・t5000=4.63 s で共有 null＋全 observed **4.44 h**（旧記載 6.9 h は撤回）；KDE 全 matched-family CI per_replicate 1.18 h／opt-in batched 0.26 h；2,000 pseudo 単純全 CI batched 516 h・点感度 7.1 h（短絡・fit 再利用・12 位置 stage・診断・Q bootstrap・bank 生成・I/O は未計上）；E2 185.8 s は部分行からの外挿（正式 asset の完走実測ではない）。安定化 batched の unit は Claude 側測定で監査側未再測；既定 backend は per_replicate。統合 runner は `with_diagnostics=True` で呼ぶため helper の省略効果を算入しない。
5. 環境 lock（Colab official）での一括実行と ENGINE_VALID（B-3）。

未実装項目の個別受入期限は、同梱 `docs_B2_scope_and_B3_handoff_proposal_ChatGPT.md` §2 の表を継承する。B-3-3で記録を集約することは、各機能の正式使用前という受入期限を後ろ倒しにするものではない。

## C. B-3 の構成（監査 §7 の引継ぎどおり）
- **B-3-0**（小規模 smoke・Colab）：検証対象 commit（module/test/fixture SHA・依存環境・外部 asset 期待 SHA を固定）；元 B-2 の mock-grid smoke（E7 1 点×2 系統・N=2×10⁴・実資産・legacy kernel）；T10 実 bank；T19 A5 cross-check。
- **B-3-1**（official 規模 control）：negative・positive full predicate・conjunct-drop・brute-force・finite inventory・A5 cross-check を機械用 required gate で集約；1 点 control は control 用 profile を明示（production の全 surviving-size 条件を緩めない）。
- **B-3-2**（正式資産）：共有 null（exact OT・n_sub 2000/5000・B_max=1000）・E2/E7/E8 正式 12 位置 asset の生成・照合・保存；新規 9 点の circle coverage／clone／prior 受入。
- **B-3-3**：未実装項目（B'）の受入期限を明記して Phase C packet へ。現 commit は「B-3 検証対象を固定する commit」であり ENGINE_VALID・rules v1.0 の科学的 freeze と同義ではない。

## D. 受入れ receipt と更新履歴

### D.0 独立監査による受入れ receipt（履歴表 §B は当時の記述として保持；現在の状態はここ）
| 工程 | 検証対象 commit（engine） | run | 監査書 | 判定 |
|---|---|---|---|---|
| B-2 実装受入れ | 初回受入れ：tranche 35/36 packet（0.39.0→0.40.0）；後続維持：B-3-0 準備時の packet v0.4（0.43.0，inventory `13c7f89a…`） | — | `ChatGPT_audit_Step1_PhaseB_B2_tranche35.md`／`tranche36.md` | accepted（sandbox 実装の範囲） |
| B-3-0 Colab smoke | `7045fc1a…`（0.44.0） | `20260917T092845Z` | `ChatGPT_audit_Step1_PhaseB_B3_0_Colab_7045fc1a17b6.md` | **PASS**（mock-grid smoke・T10 実 bank・T19/A5・legacy 3 回帰を B-3-0 の規模で完了） |
| B-3-1 official 規模 control | `903458d7…`（0.47.0） | `20260917T154350Z` | `ChatGPT_audit_Step1_PhaseB_B3_1_Colab_903458d71e94.md` | **PASS**（1 配置 control profile；ENGINE_VALID・production 較正ではない） |
| B-3-2 A（12 位置 asset・circle 幾何） | `7240c06f…`（0.52.0，inventory `857b2f37…`） | `20260918T094339Z` | `ChatGPT_audit_Step1_PhaseB_B3_2_Colab_7240c06f255c.md` | **PASS**（監査が 12 点を独立再生成し完全一致；A11 物理 clone は scope 外） |
| B-3-2 B（共有 W₂ null） | `7240c06f…`（0.52.0） | `20260918T152513Z` | 同上 | **PASS**（校正 bank は A10 official と bit 一致；Drive 世代の実復元は未検証） |
| B-3-3 receipt 集約・登録資産・受入期限 | handoff commit `1db30cd1…`（0.54.0，inventory `0ece0a3d…`） | — | `ChatGPT_audit_Step1_PhaseB_B3_3_v2.md` | 引渡し確定（監査候補 overlay 適用） |
| Phase C（rules v1.0 freeze） | `50825cc7…`・tag `step1-rules-v1.0-freeze` | — | `ChatGPT_audit_Step1_PhaseC_freeze_packet_v0_4.md`；outer receipt | 採用対象として承認・保存済み |
| Phase D-1（第 1 波 30 配置の production 共分散） | `aa089fa492bc094492d1a425c7a91bb7bfa4a150`（0.57.0，inventory `9c7e37af…`） | `20260920T081931Z`（3.30 h） | `ChatGPT_audit_Step1_PhaseD_D1_Colab_aa089fa492bc.md` | **PASS**（30 共分散＋intake；A11 entry 再生成 rel 1.3e-20；`registered_assets/d1/` に登録・receipt `d1_receipt.json`） |
| Phase D-4 tranche 1（D4-2/3/5） | 0.60.0 | — | `ChatGPT_audit_Step1_PhaseD_D4_tranche1_v3.md` | **実装・接続として受入れ**（RD4T1-A/B/C/D 閉鎖） |
| Phase D-4 tranche 2（D4-4 参照鎖・D4-1 較正先行 driver） | 0.66.0（v6） | — | `ChatGPT_audit_Step1_PhaseD_D4_tranche2_v6.md` | **実装・接続として受入れ PASS**（R2V3-A・R2V4-A/B/C・R2V5-A 閉鎖）；完了記録 `Step1_PhaseD_D4_completion.md` v2（監査 §2 の文言訂正を採用） |
| Phase D-2（第 1 波 bank 生成器） | 設計 v0.2（監査で方針受入れ）；tranche ① v2（0.68.0） | — | `ChatGPT_audit_Step1_PhaseD_D4completion_D2design_v0.2.md`／`Step1_PhaseD_D2_tranche1_report.md` | ① v1 の正常経路は監査で確認，RD2T1-A（入力検査）／B（表の内容検証）を v2 で採用（閉鎖確認待ち）；② 生成器・③ intake／供給は次 |

### D.1 更新履歴（tranche 35／36 以降）
- tranche 36：第 35 tranche 監査の inventory・provenance・性能・実行範囲の訂正と B-3 移管表を反映（本版）。監査の受入試験 12 件を同梱。
第 34 tranche 監査 R34-A/B の候補 patch（twelve_assets／threshold_evaluator／integrated_runner）を採用：asset 全体の validate と receipt（source-bound registry・exact inventory・member identity／anchor・asset SHA），atomic cache publication（失敗した intake から verified set へ登録しない），`regenerate=False` の cache miss 拒否，evaluator の asset↔registry 照合，runner の asset snapshot／pin と終了時の whole-asset 検査，期待 asset SHA の省略可能引数。

> 監査側メタデータ訂正候補（2026-09-19）：初版日付と現在版、B-2当時の状態を区別した。現在の機能別期限はB-3-3文書§3／§4.3による。旧表・過去の受入れ記録の意味は変更しない。

- Phase D-1 起草（0.55.0）：`Step1_PhaseD_design_v0.3.md`・`d/`（A11 登録生成器の逐語再現＋production 共分散 intake）。
