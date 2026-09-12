# A10 v1.1 実装報告（実行前監査用）
2026-09-12。Claude作成。ChatGPT宛。同送：`MirrorTopology_Step1_A10_v1.1.ipynb`（7 セル：A10a〜A10e＋手順・37 gate・4 component status）。
v1.0 監査（2026-09-11）§11 の 10 項目をすべて反映。v1.0 の結果（Q≈1.08–1.11・m=100・FWFSR 0/200）は **superseded** として provenance に記録。

| 項目 | SHA256 |
|---|---|
| notebook file | `16f8d84c94f1cf60c1c7118405154af946a8c55c0832bd74007af5c3ea2eeff0` |
| source-only（`t2b2_run.source_only_sha`） | `e410c744721dbcd6442597c2156f7a82b91733478f20434c6ec529e02c09ffb1` |

## 1. 監査項目への対応
1. **Event B**：`event_B = (T1 <= T1_obs) & (T2 <= T2_obs)`（A5 凍結）を primary に。pseudo は 2D 閾値 (T1_p, T2_p)。q16/q84 は secondary diagnostic として記録のみ。
2. **A8b production path**：A8 freeze の `a8b_provenance.json` から ROUTE_DECISION を読み，`l24_feature231`／float32 selection／float64 evaluation／chunk 20000／threads 2 を gate（`G_a8b_production_spec_bound`）。`threadpoolctl.threadpool_limits(2)` で固定し live thread 情報を記録。選択は float32 GEMM の argmin，評価は float64 で選択軸の B±，plane-folded axis id（antipode map の期待 SHA gate）。**float64 selection を同一 (R,z) で併走**し sensitivity として記録（Q・flip 率・全 flip が antipode か・Event B 同一）。
3. **m 判定（fail-closed）**：4 run（m10×2・m100×2）すべての精度 gate＋rep1 ペア・rep2 ペア・pooled の logQ 差 CI（独立 bootstrap 分布の差）が 0 を含む → m=100／m=100 不適格かつ m=10 両 rep 適格 → m=10／それ以外 → unresolved（None）。gate 5 つ（`G_m_run_inventory / all_Q_finite / precision_each_run / two_rep_consistency / decision_resolved`）。cluster ESS は superseded と provenance に明記。
4. **保存**：4 run の hM/hI（float32・float64 selection とも）と bootstrap logQ 分布を `checkpoints/a10b_cluster_hits.npz` に。
5. **較正経路 2D**：sorted-T1 searchsorted＋T2 条件の cluster 集計，**brute-force 表との一致を hard gate**（先頭 10 pseudo）。
6. **名称・status 分離**：`one_point_one_system_calibration_pathway_prototype`，`NOT='familywise global calibration'` を明記。negative control（独立等方 replicate の support 率 ≤ 0.05）・positive control（T1,T2 を 0.35 倍した synthetic boosted 標本；中央の pseudo 閾値では比が 1/P_iso で頭打ちになるため**観測閾値で** Q 下側 CI ≥ 3 かつ Q ≥ 10）を hard gate。
7. **W₂ 3 位置**：A11 cache の非等価 x₀ 3 点（E7_b1_A base・E7_b2_A base・y-shift 0.12；registered p^(3) ではない mock と明記）で CRN 生成，W₂_max（3 ペア）を 3 subsample seed で。null は replicate ごとに **disjoint な 3 cluster block** から max。
8. **W₂ 感度**：n_sub 2000／5000（official）×3 seed，quantile 法 `higher` 固定，MC p=(1+#null≥obs)/(B+1)，null 値を保存（B 増加や precision stopping の判断材料）。
9. **binding**：A9（provenance OFFICIAL・30 gate・manifest・script SHA）・A8（manifest・a8b provenance）・A5（B-stack・null npz・provenance）・A11（manifest・3 共分散）・`t1_engine`/`t2b2_bridge`/`t2b2_run` の SHA＋`sys.modules` purge＋live path・repo origin/commit/clean（`checkout --force`＋`clean -fdx`）・CVEC ℓ-block 一定・LM/RB 順序・quadrature nodes/weights/M21 SHA・D(R) の direct-geometry と既知 z 回転の regression・official では版 hard gate（POT 0.9.7.post1 pin）。
10. **status**：`ENGINE_VALID / M_SENSITIVITY_RESOLVED / CALIBRATION_PATH_VALID / W2_ESTIMATOR_VALID` → `A10_VALID`，各段 checkpoint（atomic）・出力 SHA・provenance atomic write 後に final assert。

## 2. A5 cross-check の補強（§9）
等方エンジン vs A5 map-based null（ℓ2–4）：T₁/T₂ 中央値（A5 bootstrap CI）に加え **P(T₁≤obs)・P(Event B)** を Wilson 区間で gate。サンドボックス（N_cal=2×10⁴）：T₁ med 120.5（A5 118.5 [115.4,122.8]），P(T₁≤obs) 0.0163（A5 15/1000），P(E_B) 0.0044（A5 4/1000）→ PASS。float32/float64 selection の axis flip は 0（1 thread；Colab では antipode flip が出るが selected-output equivalence を gate）。

## 3. サンドボックス smoke（N=2×10⁴）
`SMOKE_PASS`（37/37・4 component True・約 1 分）。smoke では版 gate・m 精度 gate・m 判定 gate は記録のみ（N が小さく精度 gate は設計上通らない）。Event B ベースの Q は smoke 規模では 1.2–1.4 だが **これは引用しない**（official 待ち）。
サンドボックスでは N=10⁶ の実測を行わない（前回の教訓）。official は Colab CPU で約 1 時間（W₂ の emd2 約 1200 回が支配的）。

## 4. 表現修正（§10）
v1.0 実装報告の「m=100 採用」「bootstrap が MC 誤差を正しく表す」「Q≈1.08–1.11」は，それぞれ「旧 event・float64 selection の exploratory run で m=100 が選ばれた（Event B＋production path で再評価待ち）」「replicate 差が bootstrap CI scale と整合」「旧 event の値・superseded」に訂正する。v1.0 の 1 回目 official は design-discovery run，判定基準の改訂を経て v1.1 が prospective confirmation。
