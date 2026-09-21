# Step1 Phase D-2 設計 v0.2（第 1 波 bank 生成器；実装前監査 D2-A〜F の反映）
2026-09-22。Claude作成。v0.1 の大枠（最大長 4N₀ の先行生成・強い intake・全 potential 12 位置 bank の較正前固定）は監査で支持；本版は reference・RNG/ID・stratum・W₂ identity と dtype・再開／供給契約・費用の根拠を凍結規則（draft4.1 §4.6–4.7・5.2・6・7.2・9.2・10・12.5）と既存 consumer（`registry.py`・`types.py`・`orchestrator.ConfigBank`・`production.BankSupply`・`w2_shared`）に合わせて明文化する。本文書は設計であり，新しい source・registry・seed 表・receipt・正式 profile を発行しない。**実際の往復数・所要時間は事前保証しない。**

## A. bank と root の対応（D2-A）
評価・fitting とも，各配置 j の **4 role** を明示する：
| role | root | 共有 |
|---|---|---|
| model_matched | S_M,j（D-1 intake の `S_matched`） | 配置別 |
| ref_matched | S_PR3＝固定 C_iso の principal root | family 内・同 purpose／batch／latent の範囲で**同一配列を共有**（重複保存しない） |
| model_native | S_N,j（`S_native`） | 配置別 |
| ref_native | diag(√c_l,j^CT を 5/7/9 成分へ反復)；c_l,j^CT は D-1 の当該配置の実共分散の block trace（`c_ct`） | **配置別**（30 種類；family 共通の 1 本へ置換しない） |
同一 latent の共有と，異なる root による T1/T2 出力の共用は別。native reference の重複排除は root・latent・selection・row 対応の完全一致を確認した場合のみ。fitting は各点・両系統・model/reference，N_fit=200,000，m_fit=100。

## B. RNG と ID（D2-B）
- configuration ID／evaluation ID／system／role／selection と，latent RNG identity を**別表**にする。第 1 波の evaluation ID は既存 `registered_id_map`（matched=config_id，native=config_id+50000）に従う；bank registry は (config_id, system) で保存し，consumer の evaluation ID と混同しない。
- **正式 key**：`(MASTER_SEED, wave_id, purpose_id, crn_group_id, batch_id, stream_id)`（`registry.rng_key`），**正式 ClusterUID**：`(wave_id, purpose_id, crn_group_id, batch_id, rotation_index)`（`types.ClusterUID`）。purpose は既存 `registry.PURPOSE`（evaluation=200・fitting=300 …）を使い，**namespace を新設しない**。
- 同一 family・同一 purpose・同一 batch の全配置・両系統・model/reference・paired selection は同一 latent（同じ crn_group）；**system／role／selection で key を分割しない**（v0.1 の system_code 入り stream は撤回）。fitting は evaluation と別 purpose。W₂ primary は位置ごとに別 group。group 整数表は**事前保存**（`d/d2_crn_table.json`；wave_id・family・purpose → crn_group_id）し，各 family notebook が読む（実行順で採番しない）。D-3 の追加 9 位置は同じ latent 対応を共有し工程名で key を変えない。
- **adapter**：`LegacyKernel.generate` の数値走査・root・回転表現（D(R)）は再利用するが，その旧 seed 配線（`[MASTER_SEED,11,STREAM,*stream_ids]`，GEN_NS）を正式 RNG 表とは呼ばない。D-2 用 adapter `d2_rng.py` が正式 key（上記）から `rotation`／`gaussian` の `Generator` を作って kernel の走査に注入する（kernel の生成 loop を key 注入版として分離；旧 namespace と過去の再現テストは保持）。凍結 tables との差は変更管理として記録。

## C. 統計的 stratum と物理 file（D2-C）
- 各配置・各系統は **4,000,000 行を固定**して供給。consumer（`ConfigBank`）へ渡す論理 batch は 2 つ：`0: rows [0, 1e6)`（10,000 cluster），`1: rows [1e6, 4e6)`（30,000 cluster）。N₀ は batch0 のみ，N₄ は同 prefix＋batch1，bootstrap の stratum 重みは 1/4・3/4。
- 保存は複数 shard file でよいが，**shard 番号と batch_id を分け**，extension の rotation_index を一意に対応（重複・欠落なし）。4 stratum 化はしない（v0.1 の 4 stratum は撤回）。
- 全 4N₀ が存在することは，各閾値・各点を最初から 4N₀ で推定する許可ではない：既存 precision 規則による 1 回拡張，N₀ 点と N₄ 点の共有 prefix，点別 availability，異長 prefix の paired 再抽出，5 seed の共有 plan を維持。

## D. W₂ と float32（D2-D）
- W₂ primary の第 1 波対象は E2/E7/E8 × 3 size × 3 位置＝27 位置，matched の 9 case（E1 対象外）。native 診断／CRN 診断は出力有無・工程・key を primary と区別して記す。
- **whitening identity**：登録 shared null の identity（μ/W・校正配列 SHA・null pool SHA `451f8bc5…`・purpose）へ束縛し，全 case・両 selection に**同じ保存 μ/W** を使う。校正 bank の再生成と A10 照合は独立検算として記録し，近いだけの別 W を古い null へ代入しない。
- **selection=f32 でも T1/T2 の評価・保存は float64**（AX/PL は int32）。rules §12.5 の必須 evaluation subset（各 family・各系統 1 配置・N₀）を不変 ID で先に固定；全 W₂ は paired 両 path。全配置 4N₀ の f32 併走は**追加診断**として scope・容量・計時を別記し，必須 subset の救済／置換に使わない。near-tie・Event B mismatch・axis/plane evidence は登録条件で検査し，|Δ| 分布だけを受入れ基準にしない。

## E. 保存・再開（D2-E）
- **fresh-only** は「attempt の出力先は新規」に限定し，完成 bank cache の再利用は別契約：run lock・生成 profile・RNG 表・source／environment・入力 root・全必要 file／array／sidecar の同一性（sidecar だけでなく実 npz member 配列）を確認してから再利用。
- 配置単位の再開：未完成配置は同じ key から再生成；完成配置の不変 file は上書きせず新 attempt で生成；部分書込みは complete manifest で確定する前に publish しない；子作業失敗を持つ partial registry を全 30 配置完了として扱わない。途中 shard からの再開は行わない（kernel が呼出しごとに seed から開始するため，短い generate の連結はしない）。初回の実 Drive 復元を記録。

## F. 供給と正式使用前（D2-F）
- `BankSupply`（model/reference 配列・cluster_uids・m・2 batch 区間・FittingBank・cov manifest）と `BootstrapPlan`／`FittingPlan` の対応 schema を先に固定。bootstrap multiplicity は生成時に作らないが，5 seed・key・B・B_KDE・UID 順・fitting binding を固定し，較正開始前に実 plan identity を確定して target まで不変（threshold ごとに選び直さない）。
- `production.intake_registered_bank(config_id, system, registry, bank_dir, receipt)`：**D-2 receipt の固定 SHA は実行後監査で registry が確定してから外側 receipt に束縛**（生成前の自己参照や自己承認を作らない；smoke／partial を正式へ昇格させない）。読込み時に file／array／sidecar／source／environment／RNG 表／config／role／selection／root／cov／N／m／UID／row 範囲／完成状態を再検査。
- D-3 の追加 81 共分散＋PC-1，正式 12 位置 profile gate は別に残る；全 potential 12 位置 bank を正式較正前に固定（実観測で family を選別しない）。固定 2000・m=1 の pseudo 列は D-2 と別工程（D-4 driver の入力として Phase E 開始時に生成・封印；設計は D-2 実装 tranche ①で明記）。外部 W₂ 実 object／context の正式 reuse と case 側 B_final／trigger は未了 gate。noise は仕様固定を未見結果の生成／閲覧前，実測を公開／label 解放前（D-2 で前倒ししない）。

## G. 計時・容量と実装順（D2-F）
- 容量（現行 dtype：T1/T2 f64・AX/PL int32＝24 B/行）：model 評価 60 本×4e6×24 B＝5.76 GB（f64 selection），f32 selection 追加で ＋5.76；matched ref 4 本＋native ref 30 本・両 path ＝6.53；fitting ≈0.30 → 非圧縮 ≈18.3 GB（＋W₂・UID・一時 file・backup は別）。圧縮率と peak RAM は実測。f32 を必須 subset に限定すれば大きく削減（scope を先に決める）。
- 計時：B-3-1 実 run の `generate_eval_4roles` 167.6 s（N₀・4 role・f64），`generate_fit_4roles` 33.6 s。単純外挿（旧 f64 評価のみ）で 4×30×167.6 s ≈ 5.6 h だが，adapter・f32・参照共有・W₂・保存／転送／再検査・RAM を含まない。**仕様確定後に小規模生成を role／path／I/O 別に計時して外挿**し，総計算時間と 1 job の経過時間を区別する。
- 実装 tranche（保証ではない）：① RNG 表・root/reference・UID/stratum/API の固定と小規模契約試験；② generator・保存・fresh/resume・環境／source gate；③ 強い bank intake と既存 consumer への供給・N₀/N₄ 混在回帰。その後に実行前監査と分割 Colab 実行。

## H. 表現の限定
本文書は設計であり数値を生成しない。数値 kernel は 0.54.0 基盤の継承であり engine 全体の bytes 同一性を意味しない（完全な source 識別は inventory）。
