# Phase D-3 tranche ① v3 報告（監査 v2：R-D3T1V2-A/B/C/D の反映）
2026-09-25。Claude作成。engine `step1_engine 0.84.0`（数値 kernel は 0.54.0 基盤の継承；追加は `d3_stage.py`＝module 49 と `d/d3_*.json` 4 file；D-1 receipt・first-wave spec・CRN 表・D-2 資産は不変）。設計 v0.2 は監査で方針受入れ（tranche ①開始 GO）。本 tranche は監査の `pending_implementation_and_preuse_conditions` の T1-PC1／T1-CASECOUNT／T1-MAPPING／T1-REUSE を具体化する；T1-PROFILE（正式 12 位置 profile と covariance intake）と PLAN-FIXATION の小規模試験は tranche ②へ。数値は生成しない。**見込み：監査 1〜2 往復（保証ではない）。** **テスト 1326/1326 PASS**（11 chunk・JUnit 同梱 `regression_logs/d3_t1v3_pytest/`；node 集合＝collect・重複 0・failure 0）。

| 成果物 | 内容 | 試験（`tests/test_d3_tranche1.py`） |
|---|---|---|
| **T1-MAPPING** `d3_stage.build_twelve_config_map` → `d/d3_config_map.json`（payload SHA `da1e68bc…`；v2 で `twelve_assets_receipt` 欄を追加，行内容は不変） | 登録 12 位置 asset（receipt 束縛 intake）の position 0〜2 が第 1 波 spec（reduced coords・r_obs・x₀_CT・cache_key・config_id）を**完全再現**することを要求し，position 3〜11 に suffix 04〜12（例 E7/L1.00：30104〜30112；native +50000）。E1 は第 1 波 3 配置のまま。111 physical／222 evaluation id の全単射（(config_id, system)⇄evaluation_id），第 1 波 id 保存，position index 0〜11 と表示 suffix 01〜12 を両記，重み 1/36（family）・1/12（size 内）を記録 | 111／81／222，第 1 波の幾何・id 保存，suffix と index，E1 の扱い，評価 id の一意性；**anchor を 1e-6 動かした asset は拒否** |
| **T1-PC1** `PC1_CONTRACT` → `d/d3_pc1_contract.json` | 凍結 A11 原典から転記：`A11_rules_v1.0.md`（SHA `5c6d9cd3…`）R2／R5 と v1.4.1 notebook（SHA `791a5abb…`）cell 5（metric）・cell 3（生成元・clone x₀）・cell 2（D_of）。関係 C(g r)=D(M)C(r)D(M)ᵀ（実基底），base x₀=−r_obs，clone x₀_H1=M_CT b − T_CT（H2=M b + T は識別用の別仮説），metric rel(C1,target)=‖C1−D C0 Dᵀ‖_F/‖target‖_F（rel_off／rel_white は診断），**許容 match rel<1e-5（R5 TOL_MATCH）**・discriminate rel>1e-2，比較方向（独立生成した clone と変換 base），D(M)=(YQ·WQ)ᵀYmat(DIRS·M)（bridge），improper M 可。D-1 pins の 1e-10 は**使用しない**と明記。状態 PC1_PENDING／PASS／FAIL は資産層（FAIL＝正式消費禁止；position-unresolved／UNKNOWN へ変換しない） | 原典 file の SHA 一致，R2 の式・R5 の値・notebook の `rel` 定義／`TOL_MATCH, TOL_DISCR = 1e-5, 1e-2`／`target = D_of(M) @ C0 @ D_of(M).T`／`x0_H1=MCT @ b - TCT` の原文存在，契約値の一致 |
| **T1-CASECOUNT** `build_pc1_case_table` → `d/d3_pc1_case_table.json` | 生成元は pinned CMBtopology source から A11 cell 3 の `gens_CT` を逐語再現して抽出（E2 halfturn_B；E7 glide_A；**E8 glide_A＋glide_B の 2 作用**；E2 の角度は登録 shape に無いため CMBtopology 既定 90/90/0 を明示転記）。case＝(配置, 必要作用)：**新点 108**（27＋27＋54），**第 1 波 anchor 診断 36**（別集合；base は D-1 の固定 SHA で再利用）。独立生成数：新 base 81＋新 clone 108＋第 1 波 clone 36＝**225**（「192」は撤回）。各 case に M・T・base x₀・clone x₀_H1・alt x₀_H2・shape／generator params・metric・許容・status を記録 | 件数，clone／alt の式（M b∓T），det M＝±1，E8 の 2 作用，E1 除外，anchor case の D-1 SHA 束縛 |
| **T1-REUSE** `REUSE_BINDING_SCHEMA` → `d/d3_d2_reuse_binding_schema.json` | 不変で保持する identity（producer digest・生成 commit・環境 fingerprint（E8 独自）・COMPLETE／sidecar／file／member SHA・role 別 root SHA・formal key・UID・selection），D-3 要求と一致させる項目（family・config・role→root・purpose／group／batch／rotation／row 順・selection・行数・prefix 不変），許す view 差（stage・重み・12 位置 FamilyInput），禁止事項（新配置と旧 root の同一視・native 参照の family 参照代用・producer 再 stamp・`match_request` の緩和・f32 受入れの一般化），plan 共有（family 内 旧／新配置の 5 seed plan identity と UID 順の共有；較正前に固定し target まで不変） | schema の field と文言 |

## v2（監査 ①：正常 mapping・保存 case 表の内部代数は確認；3 領域を修正）
| ID | 対応 |
|---|---|
| R-D3T1-A | **A11 原典の登録**：`registered_assets/a11/`（凍結 rules 全文＝SHA `5c6d9cd3…`，notebook cell 2／3／5 の source 抜粋と抽出 manifest；notebook SHA `791a5abb…`）を packet に同梱し，`a11_attestation()` が抜粋 bytes の SHA・原典側 SHA（凍結 checkout があれば notebook から再照合）・R2／R5・metric／TOL_MATCH／clone 式の原文存在を検査。**CT source の認証**：`registered_assets/ct_pinned/`（pinned commit `0cc65e34` の E2／E7／E8／default_E2 の copy；manifest の SHA は git blob と一致）を同梱し，`ct_source_context()` が pinned checkout（commit／origin／clean＋file SHA）または登録 copy（file SHA）から**検証済み bytes**を返す；`_gens_CT_from_source` はその bytes から抽出（A11 cell 3 の `gens_CT` と AST 一致；source の受取りだけが相違），E2 の角度既定値は default_E2.py から読んで転記値と照合。case 表に `a11_attestation`・`ct_source.file_sha256`・`e2_default_angles` を記録。TEST-ONLY の改変 source dir（E8 の T_B×2）は source binding で拒否 |
| R-D3T1-B | mapping 入口 `_bound_inputs`：source-bound `GridRegistry` 型，manifest＝registry からの再導出（as_dict 一致），`TwelveManifestAsset` 型で receipt 束縛 intake 済み（marker＋verification）かつ同 registry で whole-asset validate；duck-typed object・内部整合のみの registry・別 registry SHA の manifest・未 intake asset を拒否。`verify_config_map`：payload SHA＋**束縛入力からの再導出との完全一致**＋型付き行検査。case 表は `verify_config_map` 済みの map からのみ構築し，(配置×必要作用) の必要全集合と一致しなければ拒否（空／削除／重複／再 stamp を拒否）；`verify_pc1_case_table` は再導出との完全一致。**D-1 参照**は trusted receipt／registry SHA で読み，**同 config_id・cache_key・x₀** の entry のみ（30102 の entry を 30101 に写した registry は拒否）；D-1 なしは `formal=False` の draft（anchor case に参照なし・別 SHA） |
| R-D3T1-C | 契約・必要作用・入力 map・返値を **deepcopy snapshot** に分離：返値の tolerance／actions／base_x₀／shape 編集が次回構築・module 定数・入力 map に波及しない |
| 小事項 | docstring の「30 base 再利用」→27（E1 3 件は保管のみ），`PC1_PENDING` を「未比較（未生成も含む）」に，`used.add` を独立行に |

pinned checkout 経路と登録 copy 経路で**同一 table**（`provenance_route` は payload 外）。

## v3（監査 v2：R-D3T1-C 閉鎖・正式入力／D-1 同配置の照合確認・A11 rules 本文確認；残件 4 領域）
| ID | 対応 |
|---|---|
| R-D3T1V2-A（信頼起点） | `d3_stage.TRUSTED_SOURCES` に **固定の完全 SHA 一覧**（A11 抽出 manifest・rules・完全 notebook・cell 2/3/5・CT manifest・CT 4 file）を持ち，`a11_attestation()`／`ct_source_context()` は**内側 manifest の自己申告ではなく定数**へ照合する（manifest bytes を先に定数で検査してから decode；member も定数で検査；必要 cell 集合 2/3/5 は定数）。監査の「member＋内側 manifest の同時変更」（E8 の T_B×2）と「cell 2 の manifest 削除／D_of 改変／rel 追加」は，別 root の copy を別 module として読み込む試験で拒否を確認 |
| R-D3T1V2-B（notebook 系譜） | **完全 A11 notebook**（SHA `791a5abb…`，44.9 KB）を `registered_assets/a11/` に同梱し，attestation は完全 notebook の実 SHA を定数で検査したうえで cell 2/3/5 を**再抽出**して登録抜粋と一致を要求（route 表示は `registered_originals_trust_anchored`；「frozen_notebook_reverified」の分岐は廃止） |
| R-D3T1V2-C（draft 件数） | `first_wave_bases_required=27` と `first_wave_bases_verified_for_reuse`（D-1 あり 27／draft 0）に分離；予定生成 225 は別保持 |
| R-D3T1V2-D（表示） | mapping の SHA 表示を現 payload に更新（上記） |

正式 case 表 payload SHA：`5f335e75e1e3…`（両 route で同一）。pinned checkout 経路は commit／origin／clean に加えて file bytes が**同じ定数**であることを要求する（checkout を別 bytes の代替経路にしない）。

限定：本 tranche は写像・契約・表・schema と小規模試験であり，共分散・clone・bank・PC-1 の数値，正式 12 位置 profile（tranche ②）・実装消費（tranche ③）・正式 Colab の GO を含まない。

先生の作業：本 packet（報告書・`d3_stage.py`・`d/d3_*.json`・テスト）を ChatGPT の監査へ。閉鎖後，tranche ②（D-3 covariance receipt／12 位置束縛 intake／正式 12 位置 profile／plan schema の小規模試験，共分散＋PC-1 生成 script の起草）へ。
