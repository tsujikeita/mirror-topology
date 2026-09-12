# A10 v1.2.4 実装報告（実行前監査用）— ℓ2–4 selection を float64 primary へ
2026-09-12。Claude作成。ChatGPT宛。同送：`MirrorTopology_Step1_A10_v1.2.4.ipynb`（7 セル・gate inventory 61，required smoke 52／official 58）。
v1.2.3 監査の**第一推奨を採用**。v1.2.3 は official 未実行のまま superseded。

| 項目 | SHA256 |
|---|---|
| notebook file | `49b37152f4bae8f065dbd7218c4da69929c514b5ea3da66557a33e0b8ef95f4d` |
| source-only | `1db585de5169dbb3baae939e8f49828d182dcb6b55fcc9f079b07f6df4ecd830` |

## 1. 方針：ℓ2–4 は float64 selection を primary，float32（A8b 登録 path）は sensitivity
`PROD = {route: l24_feature231, selection: float64, evaluation: float64, chunk: 20000, threads: 2, primary: float64, sensitivity: float32}` とし，provenance に supersede_note（A8b は性能 benchmark として保持，ℓ2–4 の dtype 推奨のみ A10 の stress evidence で supersede，S2 は float32）を記録。`G_a8b_production_spec_bound` は A8b の route/chunk/threads と **A8b 自身の float32 推奨**を照合する（A8b freeze の内容は変更しない）。calibration・4 m run・pseudo・negative control・W₂ の 3 pool はすべて float64 primary で生成し，float32 は同一 (R,z) で併走。

## 2. float32 sensitivity の component 別 gate（監査 §5 代替案を，primary を切り替えたうえで全部入れた）
- **m run**：`compare_selection_paths`（near-tie 条件・Event B mismatch ≤1e-5・全出力 finite）を required；**Q の直接感度** `|logQ_primary − logQ_f32| ≤ DELTA_Q_SENS=0.01`（事前登録・診断 gate `G_m_Q_f32_sensitivity_bound`）；非対蹠 flip の有無は診断。full AX（両 path・int16）を `a10b_axes.npz` に保存（監査 §7：m run も full archive に）。
- **A10c**：float32 hit table で support 配列・false-support 頻度・hit table 変化セル数・pseudo ごとの |ΔlogQ|・|ΔlogD| を `sensitivity_float32_selection` に保存（診断）。
- **W₂**：OT を二重実行せず，paired whitened 出力の **coupling 上界** ε_j=√mean‖z₆₄−z₃₂‖²（≥W₂(P_j,P_j^{f32})）と三角不等式から pair 差上界 ε_j+ε_k を計算し，**null q99 の 5% 以内**（`W2_EPS_FRAC=0.05`・事前登録）を required（`G_w2_f32_coupling_bound`）。smoke：上界 1e-6 = q99 の 3e-6。
- **旧 `G_f32_selection_plane_equiv_probe` を削除**し，helper の 5 ケース self-test（same→PASS／非対蹠 near-tie＋EB 同一→PASS／T₁ 差 ≥1e-6 の flip→FAIL／EB mismatch 率 >1e-5→FAIL／非有限→FAIL）を required に。
- 小補強：相対差分母を `finfo.tiny` で保護；generation call の **exact 12-call inventory**；非対蹠 flip の plane-folded 角距離を evidence に保存。

## 3. サンドボックス smoke（N=2×10⁴・fresh OUT）
`SMOKE_PASS`（52/52・4 component True・約 1.5 分）。float32 sensitivity：Q 差 0，A10c の support 配列差 0，W₂ 上界 q99 の 3e-6。非対蹠 flip の診断 gate は今回の smoke 標本では False（flip は残るが primary path には影響しない）。

## 4. 透明性（監査 §8）：v1.2.2 の failed-policy smoke evidence と v1.2.3 の実装報告は，v1.2.4 と同じ commit に `results/step1_phaseA/A10_history/` として残すことを提案（先生の commit 時に同梱）。

## 5. 先生の作業（GO 後）
0. v1.2.4 を commit・push（可能なら上記 history も同梱）。1. fresh runtime で smoke。2. fresh runtime・fresh OUT で official（1.5〜2 h；float32 併走で m run が 2 倍）。3. `a10_v1.2.4_{smoke,official}/a10_provenance.json`・`checkpoints/`・セル出力を返送。
