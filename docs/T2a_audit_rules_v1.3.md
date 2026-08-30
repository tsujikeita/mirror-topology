# T2a_audit_rules v1.3（凍結・2026-08-31）

T2a監査版（MirrorTopology_T2a_analytic v1.3_audited）のofficial実行を拘束する凍結規則。
本ファイルのSHA256はnotebookのrepo gateで照合される。変更には新版番号と再監査を要する。

## 1. 役割の限定

T2aは *Harmonic closed-form validation and multipole decomposition of fixed-holonomy parity
expectations*（固定ホロノミー軸における鏡映パリティ期待値の閉形式検証と多重極分解）である。

- **決定論的解析層のみ**。MCサンプリングを行わない（T1 v1.6 officialで解析期待値とMCの整合は
  全固定演算子について検証済み）。
- 共分散の再生成を行わない。T1 official（commit f55515b3…）の凍結成果物を入力とする。
- 観測との直接モデル比較ではない（それはStep 1）。結論は「**検査した固定ホロノミー演算子の
  平均では E[S⁺]>E[S⁻] である**」までとし，モデルの棄却・採択には用いない。
- 旧`MirrorTopology_T2a_analytic_v0.1.ipynb`は **EXPLORATORY / SUPERSEDED**。その
  `exact_ES`・MC自己検証・`A_over_dE`数値は正式引用しない。ただし閉形式`harmonic_A`は
  **MATHEMATICALLY VERIFIED / RETAINED**。

## 2. 入力の凍結（T1 official由来）

- T1 production commit `f55515b3bb5223044f4c3bada3aaa8dc62dee359`。
- T1 provenance の `status == 'OFFICIAL'`・全gate true。
- T1 `t1_audited_results.csv` SHA256 = `3ebc26416faa29585f3c75a4ddc43ff2aa15866af252042a6bcdcb600aa264cf`
- T1 `t1_audited_realizations.npz` SHA256 = `749946c6aad261fc854320c5b8fceb6792baf28a80e726d729aa0f9c263cb5b8`
- T1 `t1_audited_provenance.json` SHA256 = `f3b2748ba1d87c81a0213abda215949e909af431cdef1fb372e1a767972baf0d`
  （**T1 provenance自体を凍結**：以降の共分散SHA等はこの確定済みprovenanceからのみ読む）
- T1 official凍結コード（現ファイル＝凍結値＝T1 provenance記録値の**三重一致**を要求）：
  `t1_engine.py`=`87bf8424073af021264b12fe312ab5255b71008bdd5fe874d164d48daf034dc8`／
  `t2b2_bridge.py`=`45107d1608d50816712f1aa452d9fa39af4adc9ec035fbe9279b264760d65872`／
  `t2b2_run.py`=`03c80f2136a8ff7ffb1077749895811ef95dd9d779c7996891d89e75545ff8db`
- 共分散：T1がキャッシュした `cov_<tag>.npy`。各点で **raw file SHA・raw array SHA・
  projected complex SHA・projected real SHA** がT1 provenance記録値と一致すること。
- 解析点 **20点**・適用可能な固定演算子 **28個**（E7/E9はA_R，E8/E10はA_R・B_R・AB_H）。
- 依存：CMBtopology commit `0cc65e34f03df85e92f738686bff0a476132f337`（軸再導出のみに使用・
  ephemeral clone・tracked clean）。再導出したAXESのmanifest SHAがT1 provenanceの
  `axes_manifest_sha256`＝凍結値`2b02ff89c8b1fe727244b7620e508e2ff3b0dc78160a2b7fa4e79c5ded106442`
  と**三重一致**すること。canonical originも照合する。
- エンジン：凍結済み `t1_engine.py`（v1.6）。**新規エンジンを作らない**。

## 3. 計算内容

各(点, 演算子)につき，射影済み複素共分散 M（t1_engine.load_cov_fullの出力）から：

1. **閉形式** A_closed（T2aの科学的中核・旧v0.1から継承）
   - refl_y: (1/4π)Σ(−1)^m C_{ℓm,ℓ−m}／refl_x: (1/4π)Σ C_{ℓm,ℓ−m}
   - halfturn_z: (1/4π)Σ(−1)^m C_{ℓm,ℓm}／refl_z: (1/4π)Σ(−1)^{ℓ+m} C_{ℓm,ℓm}
   - 軸が座標軸でない場合は閉形式を適用せず，**一般式へ委譲して明示フラグを立てる**
     （黙ってNaNにしない）。
2. **一般式** A_trace = tr(U·C_real)/4π（U=t1_engineの反射／半回転演算子行列・任意軸で有効）。
3. **多重極分解** A_ℓ（ℓ=2,3,4）：反射・回転はℓを混ぜないので A = A₂+A₃+A₄。
   signed fractional contribution frac_signed_ℓ = A_ℓ/A（負値や>1を取りうるため「割合」とは
   呼ばない）・dominant_ℓ = argmax|A_ℓ|。
4. T1 CSVの `ESp_*`, `ESm_*` から T1_dE = ESp−ESm。

## 4. Hard gates（OFFICIAL = 全required成立）

repo層：G00 import identity／G01 repo HEAD／G01b canonical origin／G01c pushed／
G02 notebook live identity／G03 engine HEAD／G04 bridge・run HEAD／G05 head_gate API。
T1入力層：G_T1_commit／G_T1_status_OFFICIAL／G_T1_gates_all_true／**G_T1_provenance_sha**／
G_T1_csv_sha／G_T1_npz_sha／**G_T1_engine_sha・G_T1_bridge_sha・G_T1_run_sha**（三重一致）。
依存層：G_ct_commit／G_ct_clean／**G_ct_origin**／G_axes_manifest（凍結値＋T1 provenanceと
三重一致）／
G_axes_expected（E7,E9: refl×1／E8,E10: refl×2+halfturn×1・群位数 2/4/2/4）。
共分散層：G_cov_raw_sha／G_cov_projected_sha／G_cov_real_projected_sha／
G_cov_symmetry（t1_engineのG09a–d相当をload_cov_full内で再適用）。
完全性：G_points_20（期待tag集合と完全一致）／G_operators_28（期待(点,演算子)集合と完全一致）。
解析：**G_closed_vs_T1**（|A_closed − T1_dE| / (ESp+ESm) < 1e-10・全28演算子）／
**G_l_decomp_sum**（|ΣA_ℓ − A_closed| / (ESp+ESm) < 1e-12・全28）／
G_trace_vs_closed（同スケールで < 1e-10）／**G_l_decomp_vs_trace**：座標軸の全演算子で
max_ℓ |A_ℓ^closed − A_ℓ^trace|/(ESp+ESm) < 1e-10（**各A_ℓを2経路で独立照合**——T2aの新規数値
そのものの検証であり，総和一致だけでは不十分）。
自己検証（実データ参照前に実行）：G_iso_reflection_identity（A=ΣC_ℓ/4π）／
G_iso_halfturn_identity（**A=Σ(−1)^ℓ C_ℓ/4π**——旧v0.1はここを ΣC_ℓ/4π と誤表示）／
G_general_axis_consistency（一般軸で閉形式非適用時の一般式とt1_engine期待値の一致）。
出力：G_all_finite（主解析CSV）／**G_pixel_study_finite**（分離研究CSV——`A_over_estimate`等の新列にNaN/infが混入したままofficial化するfalse-PASSを防ぐ。`A_over_estimate`計算前に`estimate != 0`の定義域checkも行う）／G_output_hashes。

**しきい値は実結果を見てから緩めない**。不合格時は原因を特定し，再監査を経て版を上げる。

## 5. 誤差源の分離研究（T2a固有の記録）

旧v0.1の `A_over_dE ≈ 1.08` の由来を**5経路**で分離して記録する。凍結対象：
`PIXEL_STUDY_TAG = 'E7_L1y1.0_g0'`／ホロノミー軸 = AXES['E7'][('refl','M_A')]／
一般軸 = [0.3, −0.5, 0.8]/‖·‖（post-hocに変更しない）。nside ∈ {8,16}（smoke）・{8,16,32}
（official）。

| route | 軸 | 反射先 | 共役 | 測るもの |
|---|---|---|---|---|
| A_exact_harmonic | 真 | — | — | 基準（厳密） |
| B_true_axis_exact_R | 真 | **厳密座標**（vec2pixしない） | 正 | 球面求積誤差のみ |
| C_true_axis_snapped_R | 真 | 最寄り画素 | 正 | ＋反射先の画素サンプリング誤差 |
| D_rounded_axis_correct_conj | 画素中心へ丸め | 最寄り画素 | 正 | ＋軸量子化誤差 |
| E_v01_historic | 画素中心へ丸め | 最寄り画素 | **旧（誤）** | ＋共役方向の誤り＝旧v0.1 |

**誤差の帰属**：B−A＝球面求積／C−B＝反射先スナップ／D−C＝軸量子化／E−D＝共役方向の誤り。
これは**凍結した診断経路に沿った逐次分解**（sequential decomposition along the frozen
diagnostic path）であり，各成分が数学的に直交・一意な分解であるという意味ではない。
またroute Eは**共通の監査済み（射影済み）共分散に旧v0.1のアルゴリズム選択を適用した再構成**
（historical algorithm reconstruction on a common audited covariance）であり，旧v0.1の
raw入力のバイト単位再現ではない。

**比率の向きの明示（v1.2）**：旧v0.1が報告した量は A_over_dE = A/dE である。本研究の
`estimate_over_A` = dE/A はその**逆数**なので直接比較してはならない。成果物には
`A_over_estimate = A_exact/estimate` を併記し，**route Eのそれが旧 A_over_dE と直接比較できる
量**であることを明記する。

**実測（v1.1 smoke・実E7共分散・PIXEL_STUDY_TAG）**：ホロノミー軸で A/E＝1.0894（nside=8）・
1.0209（nside=16）。前者は旧v0.1の「≈1.08」を再現する。ただし **E−D の増分は実質ゼロ**
（≲4e-11）であり，**この実共分散では共役方向の誤りは対称性によってほぼ隠れる**。
したがって旧≈1.08の実データ上の主因は**軸量子化**である。一方，合成の一般非等方共分散では
共役方向の誤りが一般に大きな誤差を生みうる（監査時実測：一般軸で厳密8.198に対し13.678）。
両者は矛盾しない——**model-dependentな隠蔽**である。補助診断として共分散のŷ反射不変性
（‖M−U M Uᵀ‖_F/‖M‖_F）を記録するが，gateにはしない。

**post-hoc変更の禁止**：実データ結果を見た後で PIXEL_STUDY_TAG・軸・nside集合を，
共役誤りが大きく出る対象へ変更しない（selection biasとなるため）。v1.1の凍結値を維持する。

## 6. 出力

`t2a_analytic_audited.csv`（1演算子1行）：tag・topology・operator・axis_x/y/z・kind・
T1_ESp・T1_ESm・T1_dE・A_closed・A_trace・closed_minus_T1・rel_error・A_l2・A_l3・A_l4・
frac_signed_l2・frac_signed_l3・frac_signed_l4・dominant_l・cov_raw_sha・cov_projected_sha・
cov_real_projected_sha。
`t2a_pixelization_study.csv`（§5の5経路×nside×2ケース）。
`t2a_provenance.json`（T1 commit・T1 provenance/CSV/NPZ SHA（期待値と実測）・
T1 engine/bridge/run 期待SHA・notebook SHA・rules SHA・軸manifest SHA・入力共分散SHA・
pixel_study_tag/axis/general_axis・l_decomp_vs_trace_max_error・出力SHA・
全gate個別boolean・OFFICIAL）。

## 7. 実行順序（宣言と実装の一致）

合成自己検証は**実データ（T1 CSV）を読み込む前**に実行する。セル順：設定→repo/engine gate→
数学層→合成自己検証→T1成果物検証→AXES→主解析→判定→分離研究→provenance。
smokeの対象点は`['E7_L1y1.0_g0', 'E10_def']`に固定（E7＝単一反射・E10＝反射2＋半回転を
1回で通す）。
