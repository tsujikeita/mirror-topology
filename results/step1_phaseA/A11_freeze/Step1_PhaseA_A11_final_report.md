# Step 1 Phase A-11：最終報告（v1.4.1 official・BLOCKER 解除候補）
2026-09-08。Claude作成。ChatGPT宛（最終監査・freeze 判定依頼）。
成果物：`a11_v1.4.1_official/`（CSV・provenance・console log・cov_cache 39）・`a11_v1.4.1_smoke/`（CSV・provenance・log）・`a11_env_lock.json`・
notebook `MirrorTopology_Step1_A11_x0bridge_v1.4.1.ipynb`（origin/main `104d5912`・source-only SHA `c1f3a362…`）。

## 1. 結果：**STATUS = OFFICIAL・47/47 gate（exact inventory）・結論 x0_CT = −r_obs（H1）**

| case | 分類（全ホロノミー述語） | rel_H1 | rel_H2 | rel_H1_vs_H2 | 判定 |
|---|---|---:|---:|---:|---|
| E7_b1_A（LAy=0.3） | candidate | 7.99e-8 | 0.200 | 0.205 | H1 |
| E7_b2_A（別観測者） | candidate | 7.78e-8 | 0.206 | 0.203 | H1 |
| E8_b1_A（glide_A） | candidate | 7.55e-8 | 0.205 | 0.211 | H1 |
| E8_b1_B（glide_B） | candidate | 8.05e-8 | 0.225 | 0.222 | H1 |
| **E7tilt3_b1_A（LAy=0.30・L2x=0.5）＝予測 B** | candidate | **7.96e-8** | **0.214** | **0.220** | **H1（前向き的中）** |
| E7tilt_b1_A（LAy=0.25） | forced_same | 8.07e-8 | 8.07e-8 | 5.3e-16 | 両方一致（予測どおり） |
| E2_b1_B（halfturn） | forced_same | 4.52e-8 | 4.52e-8 | 5.5e-16 | 両方一致 |

**前向き予測 A**（E7 LAy=0.3・観測者 y+L1y/2 → 共分散不変，登録基準 rel<1e-5）：**5.97e-16**。
格子並進 12 本・kernel 方向 5 本：max rel **1.05e-15**。y 依存対照：0.247。
親 cache（v1.3.1 official・status=FAILED のまま保存・provenance SHA `381620f1…`）から **35 個を byte 検証して import**，新規 4 個生成。
smoke 証拠鎖（provenance SHA・status・全 gate・canonical notebook SHA・環境 fingerprint）ok。環境：Python 3.13.15／numpy 2.1.3／scipy 1.16.3／
healpy 1.20.0／camb 2.0.4／numba 0.61.2／quaternionic 1.0.17／spherical 1.1.4（lock 一致）。

## 2. 登録事項（rules v1.0 へ転記）
1. **x0_CT = −r_obs**（canonical gauge）。一般同値 (I−M)(x0_CT + r_obs)=0。クローン関係 C(g r)=D(M)C(r)D(M)ᵀ（D は A9 の求積構成・active 規約）。
2. **共分散の観測者依存性は (I−Hᵀ)x₀ mod Λ（全ホロノミー元 H）を通してのみ**。帰結：kernel 方向に不変（E7 は y₀ のみ・E8 は (x₀,y₀)），
   E7 の共分散の y 周期は L1y/2（A6 縮約座標と整合）。
3. 判別可能性述語（v1.3.1 の 2T∈Λ は SUPERSEDED_DIAGNOSTIC）。
4. Step 1 のモデル共分散生成では，A6 の観測者位置 r_obs（pilot v2・縮約座標）を x0_CT = −r_obs で CMBtopology に渡す。

## 3. 履歴（透明性）
v1.3.1 official は 41 gate 中 40 True・`G_convention_H1` のみ False（UNRESOLVED）で **FAILED として保存**。原因は判別述語の理論的誤り
（観測者位置の格子同値を使っていた）。訂正述語は 5/5 を遡及的に説明し，v1.4.1 で前向き予測 A・B を事前登録して**両方的中**。

## 4. freeze 手順（提案）
`results/step1_phaseA/A11_freeze/` に notebook・official/（CSV・provenance・log・cov_cache/）・smoke/（CSV・provenance・log）・`a11_env_lock.json`・
本報告・v1.3.1 の FAILED provenance/CSV（履歴として）・freeze manifest を収め，タグ `step1-phaseA-A11-v1.0`。
