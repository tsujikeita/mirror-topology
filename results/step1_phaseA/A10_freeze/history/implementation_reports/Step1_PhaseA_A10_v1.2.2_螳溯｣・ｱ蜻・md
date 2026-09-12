# A10 v1.2.2 実装報告（実行前監査用）
2026-09-12。Claude作成。ChatGPT宛。同送：`MirrorTopology_Step1_A10_v1.2.2.ipynb`（7 セル・gate inventory 56，required smoke 49／official 55）。
v1.2.1 監査の必須 2 項目＋推奨 4 項目を反映。v1.2.1 は official 未実行のまま superseded（provenance に記録）。

| 項目 | SHA256 |
|---|---|
| notebook file | `0eed680bc433241bd904faf762751cf326e49aeafd1e1c5749088e8ba679ddb8` |
| source-only | `beddbb2db058a1e278adc00839a5f3a39493b76eaa9a3df71263f0128be3ff38` |

## 1. 対応
1. **scan() の非有限 fail-fast（必須 1）**：chunk ごとに selected score・T₁・T₂ の finite を検査し，非有限なら `FloatingPointError`（A8b child と同じ semantics）。gate 追加ではなく `scan()` 自体で例外にし，全 component に一括適用。
2. **positive control inventory（必須 2）**：`G_cal_control_inventory` に QB/DB の finite・DB>0 を追加；`G_cal_positive_control` に QBo/loBo/DBo の finite・`HIo.sum()>0`・`HBo.sum()>0` を追加（inf／underflow の偽 PASS を排除）。
3. A10b の**二重 diff_ci を削除**（`allQ` 後の guard 付き版のみ）。
4. **W₂ checkpoint binding** に `IND/CRN/TwI` 配列 SHA・`platform`・CPU・`THREADS_LIVE` を追加（W₂ に渡す数値配列そのものへ binding）。
5. **m run の f32/f64 sensitivity** に等方側 flip 率・全 flip antipodal・Event B 同一と，両系統の T₁/T₂ 最大相対差を追加；**5 bootstrap seed それぞれの equivalence verdict**（`equivalence_verdict_5_bootstrap_seeds`）を診断として保存（判定は事前登録どおり seed 0）。
6. provenance に `diagnostic_gates` と `gate_policy`（status は required のみで exact；診断 gate は False でも status に影響しない）を明示。

## 2. サンドボックス smoke（N=2×10⁴・fresh OUT・OpenBLAS 2 threads）
`SMOKE_PASS`（49/49・4 component True）。m=10 fallback 経路が smoke で到達（m=100 `precise=False`）。5 seed の equivalence verdict は smoke 規模では全 False（CI が広い）。
**A10 実標本での selected-output 観察**（診断・§11.1）：m10_rep1 で float32/float64 の axis flip 5×10⁻⁵（全件 antipode），T₁ 最大相対差 3.8e-8，**T₂ 最大相対差 1.7e-6**（Event B は同一）。これは antipodal pair が exact implemented tie でない軸（A5 の 292/3072：R 行が対蹠と一致しない軸）で B⁻ 行が僅かに異なるためで，A8b の評価許容 1e-6 を僅かに超える。rules v1.0 の「scientific axis は plane，T₂ は float64 評価」に，antipode flip 時の T₂ 許容（例：1e-5）を明記する材料として報告する。

## 3. 先生の作業（GO 後）
0. v1.2.2 を commit・push。1. fresh runtime で smoke（`A10_MODE='smoke'` セル追加）。2. fresh runtime・fresh OUT で純正 v1.2.2 を Run all（CPU 可・1〜1.5 h）。3. `a10_v1.2.2_{smoke,official}/a10_provenance.json`・`checkpoints/`・セル出力を返送（ChatGPT §10 のとおり smoke の raw provenance も同送）。
