# Step1 Phase D-2 設計 v0.1（第 1 波 bank 生成器・bank registry・production 供給）
2026-09-22。Claude作成。前提：D-1 登録共分散（30 配置；receipt `D1_aa089fa492bc`），D-4 の intake 入口（`intake_registered_covariance`）と driver（`calibration_first`），Phase C 追補 §7 の使用前 gate，Phase D 設計 v0.3 §2.2（family-wide CRN・最大長 bank・12 位置供給・強い intake）。本文書は設計であり，実装・実行・受入れではない。**見込み：設計監査 1 往復 → 実装 2〜3 tranche → Colab 1 回（8〜10 h）。**

## 1. 生成対象と規模（rules §6・§7・§10）
| bank | 対象 | 規模 | 用途 |
|---|---|---|---|
| 評価 bank（matched／native） | 30 配置（E1 3・E2 9・E7 9・E8 9）× 2 系統 | **N_max = 4N₀ = 4×10⁶ 行**を最初から生成（batch0＝N₀=10⁶ の共有 prefix＋追加 3N₀ の別 stratum；m=100，cluster UID＝family-wide CRN 表；両 selection f64/f32） | Q・P(E_sel)・event ratio・precision の適応（N₀→4N₀ は同 prefix で「一度だけ」；rules §6.5） |
| 参照 bank（等方） | family ごと 1 本（配置と同じ CRN 表；系統ごとに等方 root） | 4N₀ 行・両 selection | 分母（reference）；model と paired |
| fitting bank | 配置ごと（model・reference；別 purpose） | N_fit = 2×10⁵ | KDE（logD）；評価と独立 stream |
| W₂ position bank | family×size×3 位置（第 1 波） | 各 N_W2 = 2×10⁵（校正 μ/W で whitening；f64/f32 paired） | case 別 W₂（stop／B_final／trigger）；共有 null は登録済み |
容量（f64）：評価 30×2 系統×4×10⁶×(T1,T2,AX,PL) ≈ 30×2×4e6×(8+8+4+4) B ≈ 5.8 GB（＋f32 2.9 GB）；参照 4 family×2 系統×4e6×24 B ≈ 0.8 GB；fitting・W₂ ≈ 0.5 GB。**合計 ≈ 10 GB → Drive 保管**，repository には registry（SHA・plan identity・UID 表・生成 profile）のみ。
時間：B-3-1 実測（1 配置 2 系統 N₀ で ≈15 min 生成）から，4N₀×30 配置 ≈ **30 h**。→ **分割必須**：family 単位の 4 notebook（E1 3 h・E2/E7/E8 各 9 h）または配置単位の再開可能 launcher。

## 2. family-wide CRN 表（設計 v0.3 §2.2；実装前に固定）
- `evaluation_id`（grid manifest の config_id）と `crn_group_id`（family×system×purpose）を分離。**評価 bank**は family 内の全配置・両系統・model/reference が同じ latent（回転 R・z）を共有（`GEN_NS.calibration`… ではなく **新 purpose `evaluation`**（namespace を `GEN_NS` に追加：`evaluation=800`，`fitting=900`；既存 namespace は不変）；stream = (namespace, family_code, system_code, batch)）。
- **fitting bank** は purpose `fitting` で family 内共有，評価と独立。
- **W₂ primary** は既登録 `w2_independent`／`w2_isotropic` の規約（位置ごと独立，f64/f32 のみ paired）。
- 凍結 `LegacyKernel.generate` の seed 配線（`rng_for("rotation"/"gaussian", *stream_ids)`）を**登録 RNG 表そのもの**とし，表を `d/d2_crn_table.json` に明文化（purpose・family・system・batch・stratum → stream_ids）。監査で表と生成呼出しの一致を検査できる形（`k.calls` の記録）。
- cluster UID = `(family_code, batch, stratum, cluster_index)` の整数化；batch0（prefix）と追加 stratum（batch 1..3）を区別；chunk／再開で不変。

## 3. 生成器（`d/d2_bankgen.py`）
1. **preflight**（D-1 と同型）：pins／inventory／script 束縛；Phase C member 照合；登録 registry と grid manifest の復元検証；D-1 receipt／registry の固定 SHA；凍結 loader／bridge の実 path＋SHA（`_verified_frozen_loader`）；登録環境 hard gate（rules §12.1）；登録校正 bank（μ/W）の再生成と A10 checkpoint 照合（W₂ whitening 用）。
2. 配置ごと：`intake_registered_covariance`（再検査済み roots S_M・S_N）→ 評価 bank（両系統・両 selection・4 stratum）→ fitting bank → 保存（npz；配置ごとに SHA・sidecar：config_id・system・purpose・stream_ids・N・m・UID 範囲・selection・root SHA・cov SHA・env fingerprint）。
3. family ごと：参照 bank（等方 root；family の CRN 表）→ W₂ position bank（3 位置；校正 μ/W）。
4. **bank registry**（`d2_bank_registry.json`）：配置／family → file SHA・array SHA・sidecar・plan identity（bootstrap plan の rng key・multiplicity SHA は評価時に生成するため registry には UID 表のみ）。
5. **検証**（生成 process 内）：有限性；T1/T2 の cluster 構造（cid 単調）；paired f32 の |Δ| 分布；batch0 が N₀ 単独生成と bit 一致（CRN prefix 不変の証明；1 配置で実施）；model と reference の latent 共有（同一 stream で root のみ差替えた再生成との bit 一致；1 配置）；A5 cross-check（等方 bank 2×10⁵ の T 統計が A5 null と一致；既存 B-3 の検査を流用）。
6. fail-fast・fresh-only・Git 終了コード・partial registry（D-1 の契約を踏襲）；再開は配置単位（生成済み配置の sidecar SHA を再検証して skip；改変は拒否）。

## 4. 供給契約（D-2 → 統合 runner／driver）
- `production.intake_registered_bank(config_id, system, registry, bank_dir, receipt)`：D-2 receipt の固定 SHA・registry entry・file／array SHA・sidecar（stream・N・m・UID・root SHA・cov SHA・env）・grid spec との対応を読込み時に再検査 → `BankSupply` を返す（`build_family_input` の geometry-only 検査を代用しない）。
- 4N₀ の適応は評価側（`orchestrator`）が「N₀ prefix→4N₀ 全体」を同じ bank から読む形で行い，bank は固定資産（点ごとの availability は bank の完全性で保証）。
- **12 位置 bank**：D-3 で共分散 81 件＋PC-1 の後に同じ生成器で（family-wide CRN 表は 12 位置を含む形で最初から定義；第 1 波の latent を共有）。全 potential bank の事前固定（遅延生成はしない）を提案。

## 5. 使用前 gate との対応
production 共分散 intake（D4-5 で実装）→ bank 生成器（本 D-2）→ 正式 12 位置 profile gate（D-3 前）→ pseudo 完全 archive・較正先行 driver（D-4 で実装）→ 外部参照再利用（D-4 で実装）→ case 別 W₂ の実 bank 実行（D-2 の W₂ bank で初めて実行；較正・判定で使う前に受入れ）→ noise（Phase E）。

## 6. 表現の限定
本文書は設計であり数値を生成しない。容量・時間は B-3-1／D-1 の実測からの外挿。CRN 表の namespace 追加は engine 変更（`GEN_NS`）を伴うため，実装 tranche で監査対象とする（既存 namespace の意味は変えない）。
