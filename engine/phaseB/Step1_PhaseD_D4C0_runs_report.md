# Phase D4C-0 正式実行の報告（commit `12980202…`，engine 0.103.0）— D4C-0b 完了（PSEUDO_PASS）／D4C-0a 失敗（入力解決の script 不具合）と修正（engine 0.104.0）
2026-10-04。Claude 作成。ChatGPT 宛（D4C-0b 正式生成の実行後受入れ監査と，D4C-0a の失敗 attempt の記録・修正 packet（v3，0.104.0）の実行前再監査の依頼）。監査 GO：`D4C0_v2_0.103.0_audit_decision.json`。実行 source：commit `12980202ee111a26c0a608e7e5bba6caed5302ae`（engine 0.103.0；inventory `f04e739d…`；GitHub tree と監査 packet の 2556 file が byte 一致することを Claude 側で確認）。

## 1. 回収物（著者の Colab から；原本のまま）
| zip | bytes | SHA-256 | 内容 |
|---|---|---|---|
| `d4_pseudo_12980202ee11.zip` | 50,138 | `57c0df458eb013c0450b57d880fdf837dcdb1f8f902a6b8b6350e1fa2d43b826` | lock・final record・run `20261004T102334Z_6e681d78a0`（record・`d4_pseudo_columns.npz` 145,444 bytes・log）・stdout／stderr |
| `d2w_cases_12980202ee11.zip` | 5,985 | `09f9ab0e8ade6c5f0b8cb53c7198bf20e9973618a8146c9647e9b57b9b98b037` | lock・final record・run `20261004T102439Z_9bac8f8730`（run record・log；**case record なし**）・stdout／stderr |
| `d4c0_pseudo_sandbox_crosscheck.json` | — | 同梱 | Claude sandbox での pseudo 列の再生成比較（§2.3） |

## 2. D4C-0b（pseudo 列）：PSEUDO_PASS＝True・`pseudo_pass`＝True
### 2.1 launcher（final record `d4_pseudo_launcher_final_record_v2`）
- lock：commit `12980202…`・inventory `f04e739d…`・script `a6e0772a…`・table SHA `88f5659e…`・engine 0.103.0（precheck／prelaunch の live source とも一致：`bindings` に 2 回の観測）。
- 標準 CPU runtime：RAM total 13.61 GB／available 11.93 GB。attempt 全体 19.3 s；`launcher_fallback` False・`gates_ok` True・`bindings_ok` True・`evidence_ok` True・`failures` []・rc 0。
### 2.2 script record（`d4_pseudo_record_v1`）
- 10 REQUIRED gate すべて True（`G_env_lock` True：python 3.13.15／numpy 2.1.3／scipy 1.16.3／healpy 1.20.0／camb 2.0.4／pot 0.9.7.post1；BLAS pools OK）。self-test なし・`production_official`。
- pseudo 表 `88f5659e…`（pins 一致）；rng keys rotation [20260912,1,400,5001,0,1]／gaussian […,0]；root SHA `390dbfac…`（`LegacyKernel.psqrt(C_ISO)`）。
- 生成 n＝2000・m＝1；列 identity：T1 `6e2669b5…`，T2 `1a5588fd…`，AX `60d61625…`，PL `85a03500…`，cid `55f385cf…`，uids `cb90d89c…`，**paired `c9f75cdb…`**；UID 端点 [1,400,5001,0,0]／[1,400,5001,0,1999]；file `d4_pseudo_columns.npz` SHA `c62a965b…`（145,444 bytes）。script 内の再読込み検証 `G_columns_verified` True。
- 時間：preflight 14.7 s・生成 2.1 s・検証 0.05 s（合計 16.8 s）；RSS 1.19 GB／peak 1.32 GB。
- 値域（記録）：T1 ∈ [18.86, 523.33]，T2 ∈ [119.17, 2376.54]；全有限。
### 2.3 Claude sandbox での照合（`d4c0_pseudo_sandbox_crosscheck.json`）
- 回収 NPZ を sandbox で `verify_pseudo_columns`（record の identity・file identity・表）に通し **一致**（n＝2000）。
- sandbox（登録環境ではない：python 3.13／numpy 2.x 別版；env gate は False）で同じ凍結 kernel・表・root から 2000 列を再生成して比較：**AX／PL／cid／UID は完全一致，root SHA・rng keys 一致；T1／T2 は 1739／1654 要素が最終桁で相違（max rel 2.1e-15／1.3e-15，≤18 ulp）**。これは `regression_logs/legacy_cross_environment_summary.json`（Colab official → sandbox：max rel 2.7e-15／1.9e-15，AX／PL 一致 1.0）と同じ水準の環境差であり，**正式列は登録環境（Colab）の NPZ**（SHA で封印）。sandbox の値を正式値とはしない。
- 主張の範囲：技術的成功（生成・封印・束縛）。較正の入力としての受入れ（登録）は本報告の監査後。

## 3. D4C-0a（D-2W）：失敗（`d2w_pass` False；D2W_PASS False）— 原因は script の入力解決の不具合（著者側の実装誤り）
### 3.1 事実
- launcher：lock（commit／inventory／script `6e379a30…`／D-2 ledger／shared-null asset／pins）OK；precheck／prelaunch OK；staging：3 run の `d2_bank_registry.json`＋`cfg*_w2` 27 unit＝303,031,554 bytes を 31.4 s で複製；子 process 起動；rc 1；final record は `launcher_fallback` True・`gates_ok` False・`evidence_ok` False（**失敗 record；成功に昇格していない**）。attempt 全体 43.0 s。RAM total 13.61 GB／available 11.87 GB。
- script record：preflight 8 gate True（env lock True，twelve context・shared null OK），**`G_d2_inputs_resolved` False** → stage `inputs`，`failures` ["inputs do not resolve to the accepted D-2 runs / W2 units"]；**bank は 1 byte も読まれず，W₂ は評価されていない**（timings は final 8.4 s のみ）。record の `inputs.d2_roots` は 3 family の run_id／run_root／w2_units 9 を ledger から正しく引けている。
### 3.2 原因（Claude の解析；再現済み）
`d/d2w_cases.py`（v1／v2）の formal path は `d2reg.get("run_id") == fam_l["run_id"]` を要求していたが，**登録 D-2 run の `d2_bank_registry.json` は `run_id` key を持たない**（run id は ledger の `run_root` と record に由来する）。したがって formal path は常に False になる。self-test path（合成 bank；registry なし）はこの比較を通らないため，sandbox の自己試験では検出されなかった（監査 §5.3 の「self-test は限定付き機能試験」のとおり）。Drive の入力・ledger・環境・staging に問題はない。
### 3.3 修正（engine 0.104.0；v3 packet）
- `resolve_d2_inputs(d2_roots, d2l, plan, keys, selftest)` を script の独立関数に分離（数学・W₂ 経路・module は不変；変更は `d/d2w_cases.py` のみ）。formal path の束縛：root の `d2_bank_registry.json` の **bytes が登録 run record と同一**（file SHA＝ledger `families[F].records.bank_registry_sha256`；`registered_assets/d2/<F>/d2/d2_bank_registry.json` と byte 同一）・registry の family／formal・**ledger の全 `_w2` unit（9／family）の manifest SHA と登録 path（run_root 配下＝run id の束縛）**・要求 case の unit に `COMPLETE.json`。理由を run record（`inputs.resolution_failures`）と failure 文言に残す。旧版より束縛は強くなる（registry bytes 同一を要求）。
- 試験（`tests/test_d4c0.py` +2 関数）：登録 registry の原本 copy（3 family）を置いた fake root で resolve が True（27 unit・run_id 3 件）になること，registry が `run_id` を持たないこと，byte 改変・family 入替・unit 欠落・root 欠落・ledger unit の manifest／path／run_root 不一致・family 不足の拒否（理由文言まで）；**formal branch の in-process 実行**（TEST-ONLY の環境 stand-in で preflight を通し，登録 registry で `G_d2_inputs_resolved` True → NPZ のない unit を strong intake が拒否：評価なし・rc 1）。
### 3.4 再実行の扱い（rules §0.4・監査 R-D4DESIGN-E）
失敗 attempt `20261004T102439Z_9bac8f8730` の原本（lock・final record・run record・log）は保持し本 packet に同梱。結果を見た時点：script が入力段で停止し科学的結果は一切生成されていないため，修正は **結果非依存の実装修正**（入力束縛の誤り；数理不変）。再実行は修正 commit の実行前再監査の後，同じ入力 root・同じ notebook（v0.2）で行う（seed・定数・条件の変更なし）。

## 4. 依頼
1. D4C-0b 正式生成（§2）の実行後受入れ（`PSEUDO_PASS`・列 identity・環境・sandbox 照合の範囲）。
2. D4C-0a 失敗 attempt の記録（§3.1）と修正（§3.3；v3 packet 0.104.0）の実行前再監査，GO なら D-2W の再実行（1 run・3 family・9 case）。
3. 受入れ後：登録 tranche（pseudo 列・D-2W の原本登録，`PSEUDO_REGISTRATION`／`D2W_REGISTRATION`，pins，registered loader 本体と拒否試験）。
