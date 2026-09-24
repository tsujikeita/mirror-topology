# Phase D-2 生成 ledger（4 family 完了；監査で受入れ）と read-only 検証器 v0.2（監査 RV-1/2/3 の反映）
2026-09-24。Claude作成。engine `step1_engine 0.80.0`（数値 kernel は 0.54.0 基盤の継承；変更は `d/d2_verify_banks.py`・`d/MirrorTopology_Step1_D2_verify_v0.1.ipynb` の追加と `registered_assets/d2/` の登録；生成 script・bank 関数・CRN 表・spec は 0.78.0（commit `8b5e6102…`）と同一）。

## 1. 生成 run の記録（`registered_assets/d2/d2_generation_ledger.json`）
| family | run id | 配置 | directory | NPZ（GB） | script 秒 | A10 max rel | 環境 fingerprint | 監査 |
|---|---|---|---|---|---|---|---|---|
| E1 | 20260923T063210Z | 3 | 12 | 20（1.24） | 3,822 | 0.0 | a99b9015… | metadata 受入れ |
| E2 | 20260923T092030Z | 9 | 39 | 59（3.36） | 8,593 | 0.0 | a99b9015… | metadata 受入れ |
| E7 | 20260923T125656Z | 9 | 39 | 59（3.36） | 9,190 | 0.0 | a99b9015… | metadata 受入れ |
| E8 | 20260923T174910Z | 9 | 39 | 59（3.36） | 9,267 | 0.0 | 8130927a… | metadata 受入れ |
合計：30 配置・27 W₂ 位置・129 directory（全て新規生成・再利用 0）・197 NPZ・11.3 GB・30,872 s（8.58 h）。source lock：commit `8b5e6102f0088afbf69b10aaa9e90af4a63e07e2`，inventory `3523d233…`，producer digest 4 family 共通 `9ed095c5…`。各 family の final record・registry・run manifest・launcher lock・全 COMPLETE／sidecar（NPZ 以外）を `registered_assets/d2/<family>/` に登録（4.2 MB）。
E8 の環境 fingerprint は BLAS pool の列挙順と OpenCV 付随 library の path の差（必須版・thread 上限は同一）で他 3 family と異なる。監査の指示どおり**両 identity を保持し，alias や互換免除は発行しない**（exact-fingerprint の reuse 検査は記載どおり適用）。

## 2. 未了（受入れ JSON の `not_completed` を踏襲）
NPZ 実配列の独立数値受入れ（file／member SHA・shape・有限性・T1/T2/AX/PL/cid），生成時 model root の数値比較，必須 f32 感度（near-tie・Event B mismatch・axis/plane flip）の実測受入れ，実 case W₂（whitening／OT／stop／B_final／trigger）と外部 context の正式再利用，正式 bank 資産の外側 receipt と固定 plan，D-3・PC-1，noise，正式較正・usable・label・ENGINE_VALID。

## 3. 実行後検証器 v0.2（監査 RV-1/2/3；`d/d2_verify_banks.py`・`d/MirrorTopology_Step1_D2_verify_v0.2.ipynb`）
監査は ledger と 4 family の履歴登録を受入れ，検証器 v0.1 を HOLD（自己整合の可変 registry から成功を返す，出力先が入力と交差しても書く，f32 は絶対差 proxy）。v0.2 の契約：
| ID | 対応 |
|---|---|
| RV-1 | **`--mode accepted`（既定）**：RUN_ROOT の family の final／registry／run manifest／launcher の SHA を ledger の固定 record と照合し，unit 集合を **正規 spec から再導出**（reference b0/b1/fit＋全配置 b0/b1/fit(+w2)）して ledger の unit（manifest SHA）と registry の両方に一致を要求；run record は complete・D2_PASS・formal。いずれも配列走査前。空／部分／別 family／manifest SHA 改変の registry は拒否；同梱の実 E7 metadata に NPZ が無ければ 39 unit すべて FAIL（成功を返さない）。**検証 source**（engine 版・inventory・script・module digest）を inventory に束縛して `verifier_source` に，生成 source（0.78.0・commit・run id・fingerprint・producer）を `generator_source` に，検証環境を `verification_environment` に別記録（module 1 行変更＋inventory 不変は `verifier_source` 段階で拒否）。`--mode test` は人工 bank 用で `accepted_run_binding=False`・`verification_scope='test'` を明示。`--max-dirs` は正整数のみで `coverage_complete=False`・`verification_scope=*_partial`・checked／unchecked 一覧，exit 0 は complete かつ all_ok のみ。cid 対応は同 (purpose, batch) の **reference と各配置の cid 配列の等価性**として記録（R/z の同一性の証明とは呼ばない；W₂ は位置別 latent のため対象外），N₀＋3N₀ の行数構造も照合 |
| RV-2 | `--out` は realpath で run root／全参照 bank と交差しないこと（等しい・子・親を拒否），fresh（存在しないか空の実 directory；symlink 不可），出力 file は `O_EXCL|O_NOFOLLOW` で新規作成（既存 file／symlink alias は書込み前に拒否）。入力は一切書かない（試験で file 集合・SHA 不変を確認） |
| RV-3 | 登録規則（rules §5.2／§12.5）で評価：flip 行（AX 相違）のうち **選択 S⁺（T1）の相対差 <1e-6** を near-tie（絶対差 proxy は診断欄へ），**Event B**＝(T1≤T1,obs)∧(T2≤T2,obs)（凍結 target 39.6717883…／259.3375006…）の path 間 mismatch 率と登録上限 1e-5，flip evidence（行・両 path の AX／PL／T1／T2／Event B・antipode 関係・A5 軸 vector からの plane 角）を保存；`f32_registered_gate` は **候補評価**（`CANDIDATE_EVALUATED`／`NOT_EVALUATED`）で，`all_ok`（integrity）とは別 field；正式受入れは監査の判断。`--near-tie-eps` は廃止 |

試験 `tests/test_d2_verify.py`（3 件）：全 family synthetic の test mode 正常（39 unit・cid 対応・入力不変），accepted mode の synthetic 拒否・空／欠落／別 family registry の拒否・実 E7 metadata（NPZ なし）の全 unit FAIL・実 metadata の整合改変拒否；出力隔離（run root・bank 子・alias・非空・負の max-dirs）と partial の区別，module 改変の source 拒否；f32 の相対規則（監査の 2 例：base 1000／Δ5e-4 → 全 flip near-tie，base 0.01／Δ5e-7 → near-tie 0）・Event B mismatch 1.0 の記録（integrity とは独立）・reference 規模違いの cid 検知。

## 3b. 旧 §3（v0.1）
Drive 上の family 出力を受入れ済み commit の engine で読取り専用に検証し，小さな JSON を出す：全 directory の `verify_bank_dir`（bytes・identity・member 集合・dtype・有限性・cid・範囲・UID・key），**NPZ file SHA の再計算**と registry／final record の照合，role×selection の配列統計（mean／std／min／max・AX／PL histogram），必須 f32 subset（batch 0）と W₂ bank の paired 感度——凍結 kernel では f32 は **selection（argmin）にのみ**影響し T1/T2 は選ばれた軸で f64 評価されるため，指標は axis／plane flip 率・flip 行の |ΔT|・near-tie 数——，同 latent 不変量（batch ごとの cid 構造）。Drive は変更しない。sandbox 自己試験（E7 30101・scale 0.003・実 kernel）：7 directory 全 ok，W₂ 600 行で flip 0。見込み：family あたり 10〜20 min（保証ではない）。

**テスト 1272/1272 PASS**（10 chunk・JUnit 同梱 `regression_logs/d2_verify_v02_pytest/`；node 集合＝collect・重複 0・failure 0）。

先生の作業：本 packet を commit（ledger と検証 notebook の登録）→ ChatGPT へ「D-2 生成 ledger と実行後検証 notebook の事前確認」→ GO 後に E1→E2→E7→E8 の順で検証 notebook を実行（各 family の `RUN_ROOT` を指定；出力は数百 KB の zip）→ 4 family の検証 zip を ChatGPT の配列数値監査へ。
