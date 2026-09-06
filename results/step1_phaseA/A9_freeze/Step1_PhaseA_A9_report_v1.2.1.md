# Step 1 Phase A-9 報告 v1.2.1（v1.2＋コメント修正のみ・CSV は v1.2 と byte 同一・監査 2026-09-06 #2 への対応）
2026-09-06。Claude作成。ChatGPT宛。成果物：`s1_phaseA9_v1.2.1.py`＋`a9_v1.2.1/`（2 hashed outputs＋provenance＝3 files）。
**30 gate すべて True・OFFICIAL**。回転機構（Haar・実基底 bridge・D(R)・モーメント）は v1.1 から不変（SCIENTIFIC FREEZE: GO 済み）。

## 監査 §24 の 11 項目への対応

| # | 対応 |
|---|---|
| 1 報告値 | Imhof–Gil–Pelaez 最大差 **1.292e-9**・MC との max\|z\| **1.6533**・モーメント max\|z\| **2.0487**・鞍点法との裾相対差最大 **4.79%** |
| 2 分類 | `unequal_with_zeros` を known-law から **低 rank 診断**（`lowrank_diag_unequal_with_zeros`）へ移動 |
| 3 低 rank caveat | 「現行の無限区間振動型反転は，effective rank が十分低い／特性関数の減衰が遅い場合に不安定になりうる（χ²₁ と rank-3 零固有値診断で観測）。登録済み rank-21 ケースは全 gate 通過」と provenance に明記 |
| 4 `G_imhof_psd` | λ_min_raw ≥ −clip_tol を hard gate。**通らなければ clip せず STOP**（assert） |
| 5 per-case 適用性 gate | 各ケースで PSD・rank 記録・警告 0・積分誤差 <1e-8・GP 収束・Imhof–GP <1e-6・単調・[0,1] を要求（`G_imhof_per_case_applicability`）。rules に登録する形式で provenance に保存 |
| 6 scaled χ²₂₁ | 実 rank と同じ 21 で known-law を追加：全 7 分位で Imhof 誤差 <1e-7（警告 0）・GP <1e-6・収束 |
| 7 `G_numpy_version_match` | 2.4.4（サンドボックス）で hard gate |
| 8 `G_bstack_file_sha` | npz file SHA `ec2d3eb5…` を hard gate（array SHA と併用） |
| 9 git fail-fast | `subprocess.run(check=True)`・stderr を `git_calls` として保存 |
| 10 再実行 | 同 seed（[20260906, 9, k]）で再実行 |
| 11 freeze manifest | 汎用生成器で `A9_freeze/` を作成（同送） |

## Imhof の正式スコープ（rules v1.0 に転記）
「固定向き・固定軸の S⁺ 周辺裾の独立診断」であり，**per-case 適用性 gate を通る場合に限り**用いる。向き混合・軸選択の最小・joint (T₁,T₂)・Event B・Q_noncomp は MC 依存のまま。Gil–Pelaez は独立の数値反転経路（同じ特性関数），Lugannani–Rice は漸近診断。

## 教訓（設計ノートへ）
basis / convention 電池は，凍結規約から独立に構成した参照経路（明示基底・複素経路・既知回転）を必須とする。
