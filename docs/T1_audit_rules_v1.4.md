# T1_audit_rules v1.4（凍結・2026-08-30）

T1遡及監査版（MirrorTopology_T1_signmap v1.5_audited）のofficial実行を拘束する凍結規則。
本ファイルのSHA256はnotebookのrepo gateで照合される。変更には新版番号と再監査を要する。

## 1. 役割の限定

T1は *retroactively audited low-ℓ full-sky theoretical predictive-engine validation* である。
マスク・前処理・凍結統計を観測と揃えた直接比較はStep 1の仕事であり，T1単独では
「このtopologyが観測をX%で説明する」旨の主張をしない。旧T1_signmap_v0.3は
EXPLORATORY/SUPERSEDEDであり，そのMC数値は正式引用しない。

## 2. 凍結パラメータ

- 依存：CMBtopology commit 0cc65e34f03df85e92f738686bff0a476132f337
  （origin https://github.com/CompactCollaboration/CMBtopology.git・tracked clean必須）。
- 解析点：E7系15点（L1y∈{1.0,0.85,0.7,0.6}×glide{g0,gq,gh}＋LAx0.7/1.3＋tilt）＋
  E8_def・E9_def・E10_def・E8_LCy0.7・E10_LCy0.7の計20点。ℓ=2..4。
- 等方系列：E7全辺L∈{1.4, 2.0, 3.0}。
- MC：NREAL=400（全実現使用）・seed=1000×点index・numpy default_rng単一generator。
- 走査：SCAN_NSIDE=8（±対蹠dedup後384軸・pixel_id<antipode_id規則）。
- 候補軸：線形ホロノミー**閉包群**から抽出（凍結期待値——群位数 E7:2, E8:4, E9:2, E10:4／
  演算子数 E7,E9: refl×1／E8,E10: refl×2+halfturn×1）。鏡映(_R)と半回転(_H)は別統計。

## 3. Hard gates（G00–G26・OFFICIAL=全required成立）

repo層：G00 import identity／G01 mirror-topology HEAD一致（canonical比較）／
G01b canonical origin／G01c pushed／G02 notebook live identity／G03 engine HEAD／
G04 bridge・run HEAD／G05 head_gate API。
依存層：G06a CMBtopology commit／G06b tracked clean（--porcelain -uno空）／
G06c canonical origin／G06d CAMB参照一致（凍結commitのソースから機械抽出した
cosmology・spectrum規約が本規則§4bの凍結値と完全一致）。
エンジン層：G07 M unitarity<1e-12／G08 roundtrip<1e-9／G09 対称性射影（§3b：生違反≤1e-5・射影後≤1e-12・E[S±]影響<1e-6）／G10 二点相関等価<1e-10／
G11 PSD／G12 経験共分散<5%／G13,G14 direct geometry<1e-4／G15 射影恒等式<1e-4／
G16 P(n)=P(−n)<1e-4／G17 tr(BC) vs MC<3σ相当（worst/3σ<1）／G24 seed再現。
データ層：G18 covariance binding（前後集合差＋トークン照合）／G19 再利用SHA照合／
G20 解析点完全一致／G21 regression点完全一致（official時）／G25 適用可能列のみのfinite検査
（構造的NaN＝非適用演算子列は許容）／G25b NPZ全配列finite／G26 出力SHA（CSV・NPZ・
走査方向配列・AXES manifest）記録済み。

## 3b. 入力共分散の対称性（v1.4追加・実データ初回接触を受けた較正）

CMBtopologyの共分散は約17万固有モードの数値積分と転送関数補間で構成されるため，理論上厳密な
2つの対称性——Hermiticity と reality条件 C_{l,−m;l′,−m′}=(−1)^{m+m′} conj(C_{lm;l′m′})——を
積分精度の範囲でしか満たさない（E7実測：5.01e-08）。T2b-2由来の1e-10許容値は解析的に構成した
共分散向けであり，数値積分結果には不適切だった。**閾値を緩めるのではなく**，以下を凍結する：

1. **明示的射影**：読み込み時に共分散を上記2対称性を厳密に満たす部分空間へ直交射影する
   （対称化像との平均）。除去した成分は`correction_max_rel`・`correction_fro_rel`として
   全点でprovenanceに記録する（黙って捨てない）。
2. **生違反の上限**：射影前のherm_raw・reality_rawが **1e-5**（RAW_SYMMETRY_CEILING）を
   超える場合はhard FAIL（数値精度ではなくパイプライン異常とみなす）。
3. **射影後**：herm_post・reality_postが1e-12未満であることをhard assert。
4. **科学出力への影響**：射影が E[S±] を変える相対量を全解析軸で測定し，**1e-6**
   （PROJECTION_IMPACT_CEILING）未満をhard assert（サンドボックス実測：2e-16）。
5. covarianceファイル自体は改変しない（file SHAは生成物のまま・射影は読み込み時のみ）。

## 4a. 参照C_ℓの二系統分離

- **CL_AUDIT**：PR3系CAMB設定（H0=67.36・lensed_scalar・μK²）。用途はエンジン自己検証・
  旧v0.3サンプラーバイアス定量・歴史的比較のみ。
- **CL_CMBTOPO_REF**：**凍結CMBtopology commit（0cc65e34…）のソースから機械抽出した設定**
  で構築（§4b）。G22・G22b・G23および等方系列のℓ形状判定は必ずこちらを使う。

## 4b. 凍結CAMB参照（commit 0cc65e34… topology/src/topology.py から抽出・G06dで照合）

H0=67.5・ombh2=0.022・omch2=0.122・mnu=0.06・omk=0・tau=0.06・As=2e-9・ns=0.965・r=0・
spectrum=unlensed_scalar・raw_cl=True・CMB_unit=muK。
注記：参照C_ℓは標準精度のCAMBで計算する（凍結commitはtransfer関数側にaccuracy boostを
使うが，ℓ=2–4のC_ℓへの影響はgate幅15%より遥かに小さい）。

## 4c. 等方収束gate（sanity convergence gate）

厳密な等方極限の証明ではなく健全性収束検査として運用する。最終L（=3.0）で：
- G22 形状：d_iso=‖C−αC_iso‖_F/‖αC_iso‖_F < 0.25 かつ offdiag_frac<0.05 かつ
  ℓ形状rel∈[0.85,1.15]。
- G22b 絶対振幅：|α−1| < 0.15（α=Frobenius最良一致スケール・C_iso=CL_CMBTOPO_REF対角・μK²）。
- G23 配向：orientation spread < 0.02。
- 収束系列（L依存の減少傾向）は記録のみとし，hard条件にしない。
- **smokeでも等方系列はofficialと同一のL集合（1.4, 2.0, 3.0）を実行**し，同一gateを
  事前検証する（解析点はsmokeで削減してよい）。

**事前ルール**：最終Lで不合格の場合，thresholdは緩めず，より大きいL（5.0）を系列に追加して
再判定する。G22bについて，全Lで安定した定数α≠1が観測された場合は単位規約の相違を示すため，
gate調整ではなく，宣言された単位換算としてofficial実行**前**に文書化・全体適用し再監査を受ける。

## 5. 分布の用途制限

distribution_status = PILOT_DISTRIBUTION_ONLY / NOT_FOR_TAIL_PVALUES。
NREAL=400はpilot分布・実装検証用であり，tail確率・最終尤度には使用しない。
主値は解析期待値 E[S±]=Σ(射影対角)/4π。

## 6. 出力

t1_audited_results.csv（wide・演算子接尾辞_R/_H・argmin S⁺同一軸のS⁻・min S⁻別診断列）・
t1_audited_realizations.npz（per-realization raw (S⁺,S⁻,A,ρ)全実現）・
t1_audited_provenance.json（G01–G26個別boolean・全SHA・versions・seeds）。
