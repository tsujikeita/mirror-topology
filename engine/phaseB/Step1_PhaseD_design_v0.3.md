# Step1 Phase D 設計 v0.3（工程分割・使用前 gate・D-1 v0.3；実行前監査 RD1・RD12・§6 反映）
2026-09-20。Claude作成。前提：Phase C 凍結（tag `step1-rules-v1.0-freeze` → `50825cc7…`），受入れ済み基盤 source `1db30cd1…`（engine 0.54.0）。本文書は設計と D-1 の起草であり，Phase D の実行・受入れではない。

## 1. 工程分割と使用前 gate（追補 §7／manifest `pre_use_gates` に対応）
| 段階 | 内容 | 主な gate（追補 §7） | 規模・見込み |
|---|---|---|---|
| **D-1** | 第 1 波 30 配置の production 共分散生成（A11 登録手順・pinned CMBtopology）と **production 共分散 intake**（幾何 binding・run profile・環境 fingerprint・array SHA 再計算・reality/PSD・sqrt gate）；A11 official 1 entry の再生成照合 | production 共分散 intake（Phase D 開始時） | Colab 3〜4 h（A11 実測 ~400 s／共分散；sandbox で E1 1 件 278 s） |
| **D-2** | 第 1 波 bank 生成器：配置ごとに matched／native の principal sqrt → legacy kernel で評価 bank（N₀=10⁶・4 role CRN・両 selection）・fitting bank（N_fit=2×10⁵）・W₂ position bank（whitening は登録校正 bank の μ/W）；bank registry（SHA・plan identity・UID）；統合 runner への production 供給（`production.build_family_input`） | Phase D bank 生成器；**正式 12 位置 profile gate**（12 位置 bank の前） | 30 配置 × ~15 min ≈ 8〜10 h（分割・再開可能に設計）；bank は Drive 保管（~2 GB），repository には SHA registry のみ |
| **D-3** | 12 位置段階の共分散（新 9 点 × 3 size × 3 family = 81）と **PC-1 物理 clone 同値性**（A11 R2：C(g r) = D(M) C(r) D(M)ᵀ を新点で検証；隔離 scope）→ 12 位置 bank（正式 12 位置 profile gate 通過後） | PC-1（当該 bank の正式使用前）；正式 12 位置 profile | 共分散 81＋clone partner ≈ 9〜18 h（分割）；bank 81 配置 ≈ 20 h（必要 family のみに限定するかは Phase E の較正設計で確定） |
| **D-4**（engine） | pseudo 側 12 位置完全 Result archive／**較正先行 driver**（実観測 full-grid target を較正封印前に計算しない）／統合 runner の登録 asset 再利用接続／外部 W₂・context 参照の checkpoint 再利用契約 | 各機能の使用前 gate（global 較正前・正式再利用前） | sandbox 実装＋監査（Colab 不要） |

D-1〜D-3 は Colab（起草 → 実行前監査 → commit → 実行 → 実行後監査），D-4 は sandbox。順序は D-1 → D-4（engine）→ D-2 → D-3 を想定（D-2 の bank 供給契約を D-4 の driver と合わせるため）。noise stress test（Phase E robustness）は Phase D に含めない（gate 1 の仕様固定は未見結果の生成前＝D-2 の bank から実観測 target を評価する前に完了させる）。

## 2. D-1 の設計（`d/d1_covgen.py`・`d/d1_pins.json`・`d/MirrorTopology_Step1_D1_covgen_v0.1.ipynb`）
- **生成器**：A11 v1.4.1 cell 4（SHA `ab1fc4dc…`）の `key_of／tag_of／ensure_cov` を逐語再現（E1 は等質のため `x0` を渡さない；他は `x0_CT=−r_obs`）。run_config（l_max=4・TT・[2,4]）・commit・requirements SHA・env fingerprint を tag に含める（A11 同一）。
- **環境**：A11 lock 形式（Python・10 package・requirements SHA・platform・BLAS）で `d1_env_lock.json` を記録し，A11 lock との同一性と差分を保存。同一なら A11 と同じ tag，異なれば D-1 の lock として登録。
- **A11 cross-check**：凍結 A11 official の E7 傾き entry（`cov_E7_061a13f7…`）を再生成し，frozen array との相対 Frobenius 差 ≤ 1e-10 を gate（bit 一致は別記録）。
- **intake（配置ごと）**：`grid_manifest.verify_cov_manifest`（topology／params／x₀／file SHA），run profile・commit・requirements・fingerprint の一致，array SHA 再計算，`t1_engine.load_cov_full`（reality・実基底・対称性），PSD（λ_min > −1e-12 λ_max），matched／native principal sqrt（clip=0・λ_min>0・sym<1e-12・recon<1e-10）。
- **gate（14 code）**：pins／inventory／script 束縛，CMBtopology commit・origin・clean・依存，A11 凍結物 SHA，registry source-bound，Phase C 登録 grid manifest との一致（manifest SHA・registry SHA），A11 cross-check，30 配置生成，全 intake PASS，evidence。
- **出力**：`cov_cache/`（30 npy＋manifest；1 件 ~7 KB），`d1_cov_registry.json`（config_id → tag・file／array SHA・x₀・intake 記録），`d1_env_lock.json`，run manifest。共分散は小さいので **Phase D packet として repository に登録可能**（D-2 の入力）。
- sandbox 自己試験（E1 L1.00 1 配置，cross-check 省略）：13 gate True（cross-check は skip），intake PASS（PSD・λ_min 118・sqrt gate 通過），278 s。

## 2.1 D-1 v0.2 の契約（監査 RD1-A/B/C）
- **RD1-A 環境 hard gate**：rules §12.1 の版（Python 3.13.15／NumPy 2.1.3／SciPy 1.16.3／healpy 1.20.0／POT 0.9.7.post1／CAMB 2.0.4）と pool（NumPy 所有 OpenBLAS=2・他 ≤2）を **生成 process 内で live に検査**（`official_gate.current_env`／`_blas_check`；thread 環境変数は numpy import 前に設定，threadpoolctl controller を保持）。A11 形式 fingerprint と lock 差分は metadata として別記録（platform・補助 package の同一性は hard 項目にしない）。
- **RD1-B 信頼済み入力**：Phase C `PACKET_INVENTORY` を読み **全 member の SHA・サイズ・集合**を照合；保存 grid を **deserialize→`validate()`→payload SHA** で検査し A6/A7 再構築と `as_dict` まで一致を要求；凍結 `t1_engine`／`t2b2_bridge` の SHA を pins に置き import 元 file を照合；A11 生成 cell を凍結 notebook から抽出して完全 SHA を pins と照合し run manifest に完全値を記録；A11 比較先（manifest／npy／raw array）の SHA を pins（b3_1 pins と同値）で検証してから再生成。いずれも長い生成の前。
- **RD1-C 停止・保全**：最初の intake 失敗で **stop**（失敗 config と理由・途中 registry を保存し非 0 終了）；OUT は **fresh-only**（非空なら log／record に触れる前に拒否）。
- **RD12-A/B/C（v0.3；監査の参考修正を採用）**：Git 各照会の終了コード・stdout・stderr を記録し不成功なら生成前に停止（空 stdout を clean と扱わない）；配置単位の例外処理で完了済み intake・失敗 config／段階・例外を partial registry に保存して非 0 終了（`intake_exception`；正常 False と技術例外を状態で区別）；保存 grid の意味検証を A11 再生成より前に移動（不合格なら生成 0 件）。
- 固有テスト `tests/test_d1_contracts.py`（7 件：fresh-only・環境 gate 停止・Phase C member 改変拒否・保存 grid 改変拒否・生成 cell SHA と AST 対応・比較先 pins・fail-fast 契約）。
- 受入れ済み base（0.54.0・`1db30cd1…`）と D-1 差分（0.57.0）の検査は分ける：checker は現 inventory（d_sha256 を含む）を検査し，凍結 base の同一性は Phase C receipt／handoff commit で保持する。

## 2.2 D-2／D-3／D-4 の設計条件（監査 §6；実装前に明文化する事項）
- **family-wide CRN 表**（§6.1）：evaluation は family 内の全配置・両系統・model/reference が同じ latent を共有；fitting は別 purpose で family 内共有；W₂ primary は位置ごと独立で f64/f32 のみ paired。D-2 実装前に `evaluation_id`・`crn_group_id`・purpose・batch・stream・cluster_uid の表を固定し，凍結 `LegacyKernel.generate` の Phase A/B 用 seed 配線を登録 RNG 表そのものとは扱わない（数値走査の再利用と乱数 adapter の受入れを分ける）。
- **最大長 bank**（§6.2）：正式較正では総 N_max=4×10⁶ までの適応を再現する固定 bank（batch0 の共有 prefix・追加 3N₀ の別 stratum・点ごとの availability・chunk／再開で不変の乱数対応・fitting との独立）。N₀ のみの状態を「正式較正へ渡せる bank 一式」と呼ばない；容量・時間見積りは仕様確定後に更新。
- **12 位置 bank の供給方式**（§6.3）：12 位置分岐は実観測だけでなく全 pseudo に同一手順で適用し，trigger した family は全 surviving size が対象。実観測 full-grid を見て family を選ぶ較正はしない。全 potential bank の事前固定か，許される遅延生成（要求分岐の再現と固定 MC 資産への条件付けを欠かさない）かを D-4／正式較正前に明示；規則変更なら amendment。
- **D-4 の unit 試験と実 bank 消費の分離**（§6.4）：「Colab 不要」は実装・単体試験に限る。case 別 W₂（実 bank・共有 null 照合・B_final・same-prefix f32・trigger）・外部 checkpoint 再利用は較正・判定で初めて消費する前に受入れ。D-2 は cov registry の `pass_` を読むだけでなく，読込み時に file／array SHA・configuration・run_profile・source／環境・数値契約を再確認する intake 入口を持つ（`production.build_family_input` の geometry-only 検査を代用にしない）。
- **PC-1・第 1 波 anchor 診断・noise**（§6.5）：PC-1 は新 9 点×全該当 size を旧 anchor の成功を転記せず検証；第 1 波 anchor の物理 clone 診断は D-3 で PC-1 と別に記録（diagnostic の名で免責しない）；noise は Phase E（gate 1 は未見結果の生成前）。

## 3. 表現の限定
D-1 は共分散の生成と技術的 intake であり，模型の観測整合・PC-1 物理 clone・bank 生成・較正を含まない。A11 の convention（x₀_CT=−r_obs）は A11 rules R1 の登録に依拠し，第 1 波配置での clone 関係の再検証は D-3 の PC-1 と同じ手順を第 1 波 anchor に適用する診断として D-3 で扱う（監査の要否判断を求める）。
