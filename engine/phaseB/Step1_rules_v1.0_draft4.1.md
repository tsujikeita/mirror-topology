# Step1_rules_v1.0_draft4.1 — Step 1 事前登録規則（第 4 稿の表示修正のみ）
2026-09-13。draft4（SHA `72305bbf…`）に対する ChatGPT 監査（draft4／spec v0.1）§3 の表示事項 3 点のみ修正（§15 の表セル・§10.4 の E7 最小距離の出典区別・末尾の承認範囲の表現）。規則内容は draft4 と同一。
Claude起草。第 3 稿（SHA `187fcb1a…`）に対する ChatGPT 監査「閉鎖確認と Phase B 移行」の差分（unsupported の帯域幅監査・技術的 invalid の fail-closed・最悪補完の分位規約・精度計算との接続・W₂ の実装明文化・表示修正）のみを反映した**最小差分版**。全文の再構成は行わない。第 2 稿からの主要修正（CI 境界値・KDE 失敗・CI 依存表の一本化・CV／clip）は第 3 稿のまま。**起草版であり rules v1.0 の凍結ではない**（Phase C は HOLD；Phase B の engine spec と小規模 control へ進む）。
原文照合：研究計画 v0.4（file SHA `0569ae2f9cbd3003d1f08840b43f20c14e8da3e07ca7718743929ee138235371`）・v0.5（file SHA `357e4d7d0325e3284bd3dcf062a4c5e5bf7599b14032e90ab3da6912da5e9f18`）は Claude 側で照合した（ChatGPT 側の独立照合は未了；Phase C packet に原文を同梱する）。

各事項の出典区分：**[継承]**＝凍結成果物から転記／**[明文化]**＝研究計画 v0.3–v0.5 の既存定義の明文化／**[新規]**＝本 draft で初めて固定する設計判断（ChatGPT 判断書に基づく）／**[実測待ち]**＝手順は固定，値は将来の official／**[照合待ち]**＝原文照合が未了。

---

## 0. 位置づけ・事前登録の射程・変更管理

**0.1 位置づけ** **[新規]**：本規則は Step 1「観測された Event B の裾確率が，登録トポロジー模型の予言分布で等方ガウス null より改善されるか」の判定手順を，Phase B（engine）・C（凍結・実行前監査）・D（共分散と bank 生成）・E（official 判定）に先立って固定する。

**0.2 事前登録の射程** **[新規・ChatGPT §8.1]**：観測値（Step 0）と開発用 pilot（A10 の E7_b1_A，Q≈1.3）は既知である。本規則は「一切のモデル結果を見ない事前登録」ではなく，**観測済み現象と開発用 pilot を開示したうえで，これからの full-grid 正式判定手順を前向きに固定する**ものである。新しい MC seed は数値評価の独立性を高めるが，新しい独立 CMB sky を得ることではない。

**0.3 凍結範囲**：定義・判定規則・数値経路・許容値・乱数設計・provenance 要件・監査工程。§15 に「実測値として HOLD できるもの」と「仕様として HOLD してはいけないもの」を分けて列挙する。

**0.4 変更管理** **[継承：A8b v1.1.7／A10 v1.2.6–9 方式＋訂正]**：v1.0 凍結後の変更は (1) **数学的手順を変えない実装修正**（環境依存・underflow 等；A10 v1.2.9 は失敗結果を見てから pdf underflow を直した実装修正）と (2) **target／閾値／判定を変える設計変更**（amendment：親 provenance の SHA・旧新 semantics・理由を binding；結果を見た後の緩和は不可）に分け，**どちらも結果を見た時点・親成果物・影響範囲・新データでの確認の要否を記録**する。superseded 事項は削除せず履歴表に残す。

**0.5 版の系譜**：計画 v0.3（family mixture・離散 prior・p^(3)）→ v0.4（Sol 指摘：符号比較から裾確率へ；N 一回 4 倍拡張；位置拡張；絶対 fit；系統方向分類）→ v0.5（定義 1–4・強化項目）→ Phase A（A5・A6/A7・A8・A9・A10・A11）→ 本 draft。v0.5 との相違は付録 B。

---

## 1. 問い・仮説・判定の論理

**1.1 問い** **[明文化：v0.4]**：**固定軸**では等方ガウス天球でも E[S⁺_a − S⁻_a] = tr[(B⁺_a − B⁻_a)C] > 0 であり，模型平均の符号を見る no-go 論理は採らない（データ依存の argmin 後にも同じ符号が成り立つとは一般化しない）。問いは観測値に対する裾確率の比較である。

**1.2 primary event** **[継承：A5]**：A = {T₁ ≤ T₁,obs}，B = {T₂ ≤ T₂,obs}，**Event B := A ∩ B**。T = (T₁,T₂) は selection-adjusted（§5）。

**1.3 主量** **[継承：A5・A10]**
- support ratio Q_M,s = P_M,s(E_B) / P_I,M,s(E_B)（family M・系統 s；§8 の混合後の比）。
- 密度比 logD_M,s(t_obs) = log f_M,s(t_obs) − log f_I,M,s(t_obs)（§7）。
- **機構分解**（A5 必須）：P_M(E_B) = P_M(A)·P_M(B|A)，Q_joint = Q_T1 × Q_noncomp，Q_T1 = P_M(A)/P_I(A)，Q_noncomp = P_M(B|A)/P_I(B|A)。total = T₁+T₂・ρ = (T₁−T₂)/(T₁+T₂) は機構診断。

**1.4 core decision rule（primary map = PR3_Commander，primary 系統 = PR3-power-matched）** **[明文化：v0.3 §3・v0.4 §8・v0.5 定義 4＝構成案 §1 に復帰]**

機械可読 predicate（表 1）。L_·／U_· は 95% 区間の下端／上端（Q は §7.1，logD は §7.2）。監査は必要量ごとに分ける：`audit_Q_matched`（精度 gate・Q 区間の defined 状態），`audit_Dpoint_matched`（KDE 帯域幅感度・logD 有限），`audit_DCI_matched`（logD CI の全 replicate 成功），`audit_Q_native`（native の精度 gate・Q 区間）。**native に D の計算・監査は要求しない**。

| label | predicate | 必要な CI |
|---|---|---|
| `support_core` | audit_Q_matched ∧ audit_Dpoint_matched ∧ L_Q,matched ≥ 3 ∧ **logD_point,matched > 0** | Q の CI |
| `strong_core` | support_core ∧ audit_DCI_matched ∧ L_Q,matched ≥ 10 ∧ **L_logD,matched > 0** ∧ audit_Q_native ∧ L_Q,native > 1（positive direction） | Q（両系統）・logD の CI |
| `unsupported_core` | audit_Q_matched ∧ **audit_Dpoint_matched** ∧ audit_DCI_matched ∧ U_Q,matched < 1 ∧ U_logD,matched ≤ 0 | Q・logD の CI |
| `inconclusive` | いずれの core にも入らない，または必要な audit が FAIL（**監査失敗は unsupported ではない**；KDE 監査失敗は support 側にも unsupported 側にも対称に inconclusive） | — |

- **CI 計算条件（短絡・事前登録；本表が唯一の参照先）**：logD の CI は (i) strong 候補（L_Q,matched ≥ 10）と (ii) unsupported 候補（U_Q,matched < 1）で必ず計算する。それ以外は `not_computed_by_registered_short_circuit` と記録（§8.2 の診断表でも同名）。全点の logD 区間を出す診断計算は別予算。**実観測と全 pseudo に同一適用**。
- logD の有限区間が 0 を跨ぐことは strong 不成立の理由であり，support を自動的に否定しない。**数値的な CI 失敗（§7.2：invalid）**と有限区間の 0 跨ぎは区別する。
- 表示 label は strong > support > unsupported > inconclusive の優先（strong と support は同時に真になり得る）。
- 正式 label は core に加えて coverage（§4.3）・precision（§7.3）・calibration usable（§9）・position status（§10）の条件を適用する。
- 第 1 稿は support にも L_logD > 0 を要求していた（厳格化・短絡規則と矛盾）。本稿は構成案・判断書の既承認規則に戻す。
- 系統方向分類 **[明文化：v0.4 §8]**：positive（L_Q > 1）／neutral（区間が 1 を含む）／opposite（U_Q < 1）。

**1.5 補助ラベル** **[新規・ChatGPT §1]**：`low_absolute_event_probability` ⇔ P_M(E_B) の点推定 < 1e-4（v0.4 §5.2 の閾値を Event B に適用）。区間上端も < 1e-4 なら「MC 不確かさを考慮しても小さい」，区間が閾値を跨げば「absolute-label unresolved」。core rule への veto ではなく headline で省略しない。P_M(E_B) ≥ 1e-4 を「模型全体の適合良好」とは読まない。P_M(E_B) は指定 2 変量左下領域の確率であり，一様帰無 p 値でも posterior model probability でもない。

**1.6 mirror-specific mechanism の追加主張** **[継承：A5 §4]**：core support とは別に，mirror-specific mechanism を主張する場合は Q_noncomp の下端 > 1 を要件とする。core rule に Q_noncomp > 1 を追加しない。追加主張に正式ラベルを付ける場合はその多重比較・較正範囲を別に明記する。

**1.7 legacy phenotype diagnostics（SCIENCE_FLAGS・veto ではない）** **[明文化：v0.5 定義 1 → 本稿で legacy 化]**：`p1_obs := P_iso(T₁ ≤ t₁,target)`，`LEGACY_OBS_SPLUS_DEPLETED := p1_obs ≤ 0.05`，`LEGACY_OBS_SMINUS_NORMAL := q₁₆ ≤ t₂,target ≤ q₈₄`，`LEGACY_OBS_TARGET_CONFIRMED := 両者`。
- 旧中央帯 phenotype に関するこれらの値は **legacy diagnostic として保存**し，**Event B に基づく support／strong／unsupported，calibration usable，位置拡張判定を変更しない**。旧 target が未確認だった事実（A10 実測：p1_obs = 0.0149，t₂,target = 259.3 < q₁₆ ≈ 382 → LEGACY_OBS_SMINUS_NORMAL = False）は，A5 で Event B（「低い S⁺ ＋ 増大しない S⁻」）へ変更した履歴として報告する。p1_obs は記述値。別途登録のない新たな veto は導入しない。
- 第 1 稿の「未確認なら family 判定は target phenotype not confirmed」は撤回（付録 C に旧 phenotype-veto を superseded として追記）。

**1.8 robustness qualifier** **[明文化：v0.5 定義 4]**：他 3 マップの同方向は descriptive。較正対象外。

---

## 2. 凍結入力・観測値

**2.1 t_target と S1 の関係（scope）** **[新規・監査 §5]**：本規則の t_target = (39.6717883…, 259.3375006…) は Step 0 で凍結された**歴史的観測 target**（全帯域・歴史的軸選択 1134・合意軸抽出を含む手順の値）である。これは一般に S1（ℓ2–4 で軸選択・評価する登録統計量）を実観測に適用した T_obs,S1 と同一ではない（A5 `a5_data_selection_band.csv`：ℓ2–4 のみの argmin は軸 2062・S⁺ 最小 36.40，軸 1134 での S⁺ 39.67）。本研究の第一段階は，**この固定 target に対する registered S1 surrogate の予測確率比** P_M[S1(Y) ≤ t_target] / P_I[S1(Y) ≤ t_target] を評価する surrogate experiment である。t_target を 36.40 等に置換しない。§9 の pseudo-threshold 較正は **S1 判定アルゴリズムの較正**であり，歴史的全帯域選択・合意軸抽出を含む実観測手順全体の exact false-support 保証とは称さない。実観測手順全体の保証を目的とする場合は pseudo 側で同じ抽出手順を再現するか，S1 を実観測に適用した別 target を新規登録する（本稿では採用しない）。


| 項目 | 値・出典 | 区分 |
|---|---|---|
| 観測値 | T₁,obs = 39.67178834527284，T₂,obs = 259.3375006282747（PR3_Commander；`results/step0_v0.7/step0_official_v0_7.csv` の一意行） | 継承（Step 0 v0.7） |
| 等方共分散 | C_iso = diag(CVEC)（`docs/step0_frozen_Bpm_v1.npz`，array SHA `17d85b41…`；ℓ2–4 で C_ℓ = 1064.7／504.6／286.7 μK²；ℓ-block 一定を gate） | 継承 |
| 評価器 | A5 B±-stack ℓ2–4・Nside 16・common mask・3072 axes（npz `ec2d3eb5…`／array `eb514148…`） | 継承（A5） |
| 実基底 | `t2b2_bridge`（SHA `45107d16…`）の real basis 21 次元・M21；`t1_engine` `87bf8424…`・`t2b2_run` `03c80f21…` | 継承 |
| map-based 参照 | A5 null（1000 synalm・ℓ2–4）：T₁ 中央値 118.5・P(T₁≤obs) 15/1000・P(E_B) 4/1000。engine cross-check gate（§12） | 継承 |
| 教訓 | float 参照値の manifest は正式環境（Colab）で生成；サンドボックス由来の float 参照値は権威を持たない | 継承（A5） |

---

## 3. 座標系・観測者規約・同値構造 **[継承：A6/A7・A11]**

- deck transformation g(x) = Mx + T（special-origin covering 座標）・観測者 r_obs。CMBtopology への橋渡し **x₀_CT = −r_obs**（canonical gauge）；一般同値 (I−M)(x₀_CT + r_obs) = 0 ∀ 生成元。
- clone 関係 C(g r) = D(M) C(r) D(M)ᵀ（改良 M 含む；D は A9 の求積表現）。共分散の x₀ 依存は (I−Hᵀ)x₀ mod Λ のみ。
- 識別述語：`structurally_forced_same` ⇔ (I−Hᵀ)(2T) ∈ Λ ∀H；`candidate_for_discrimination`；`empirically_discriminating`。許容：match rel < 1e-5・discriminate rel > 1e-2。
- 円制約（A7）：第 1 波の全 primary observer 行について nearest deck element・θ_nearest・exclusion witness を凍結（`a7_circle_geometry.csv`，member SHA `47b2d910…`）。閾値 search 0.985／geometric 1.0。

---

## 4. モデル族・grid・観測者設計・共分散系統

**4.1 family** **[新規・ChatGPT §2.1]**：**E1・E2・E7・E8 の 4 族**（v0.3 の登録どおり；E1 もトポロジー模型であり等方 null ではない）。結果によって family を削除しない。

**4.2 第 1 波 grid（一次解析）** **[継承：A6/A7 v1.4.2]**：shape は各 family の等長パラメータ既定 slice（E1: Lx=Ly=Lz=L；E2: 同；E7: LAx=L1y=L2z=L, LAy=L2x=0；E8: LAx=LBz=LCy=L, LAy=LBx=0；基本領域が辺 L の立方体という意味ではない），size L/L_LSS ∈ {0.70, 0.85, 1.00, 1.20, 1.50}。family × size = 20。追加 shape（tilt・aspect）は別の波として別予算化し，一次解析に混ぜない。

**4.3 円制約による conditional analysis** **[明文化：v0.4 §2・v0.5 定義 2＋継承 A7]**：ラベルは allowed／excluded／undetermined の 3 値（undetermined の mass は残し，除外・再正規化しない；undetermined を持つ family は partial-coverage・「support status not evaluable」；f_covered を報告）。第 1 波では undetermined は存在しない。L = 0.70, 0.85 は `excluded_by_published_search`（Vaudrevange 2012 の 0.985 閾値；anti_phased・θ=180°），L = 1.00, 1.20, 1.50 は observational_status `no_nondegenerate_circles`（surviving）。ただし L = 1.00 の geometric_status は `zero_radius_boundary`（L > 1 の非境界幾何と同一視せず両列を保持）。**s_M = 0.6**（surviving mass）を必ず併記し，Q に掛けない。undetermined mass はない（第 1 波）。

| family | size×observer 行 | excluded | surviving |
|---|---|---|---|
| E1 | 5 | 2 | 3 |
| E2 / E7 / E8 | 各 15 | 各 6 | 各 9 |
| 合計 | 50 | 20 | **30** |

**4.4 観測者設計 p^(3)** **[新規・ChatGPT §2.3＝A6 凍結 `pilot_v2_reduced` の明示採用]**：E2・E7・E8 それぞれ 3 点（`a6_observer_design_points.json`，member SHA `a5ea1ae6…`，seed sequence [20260905, 7]）に**等重み 1/3**。E1 は homogeneous（観測者 1 点）。正式入力は JSON の full-precision reduced 座標と凍結 lift 関数（`s1_phaseA6A7_v1.4.2.py`：E2 `[q0·Lx, q1·Ly, 0.37·2·Lz]`，E7 `[0.31·LAx, q0·L1y, 0.42·L2z]`，E8 `[q0·LAx, q1·LCy, 0.42·LBz]`；略記 (0.31, 0.37, 0.42) を物理座標に直接代入しない）から生成し，A11 の x₀_CT = −r_obs を適用する。CSV の表示用丸め座標は再入力しない。これは**既定 3 位置上の離散予測分布**であり「連続一様 prior の積分」とは呼ばない。A10 の W₂ mock 位置・A11 の convention 検査用 base 位置を p^(3) に代用しない。symmetry anchors（30 行）は prior に含めない。
- reduced 座標（E2：(x/Lx, y/Ly) mod 1，half-turn 同一視；E7：η_y = dist(y,(L1y/2)Z)/L1y ∈ [0,1/4]；E8：η_x, η_y）と選択規則（box・min_sep・exclusion）は JSON のとおり。

**4.5 prior 重み** **[新規・ChatGPT §6]**：surviving size 3 点に各 1/3，E2/E7/E8 の 3 位置に各 1/3 → 各配置 w = 1/9；E1 の各 size は 1/3。**評価件数：30 配置 × 2 系統 = 60 model 評価**（+ 対応 reference）。clone を計算上まとめる場合も prior mass は同値類で加算保持し，重複排除と重み変更を混同しない。

**4.6 共分散系統** **[継承：T2b-2・A10]**：**PR3-power-matched**（primary：c_ℓ^CT = tr(C^CT_ℓℓ)/(2ℓ+1)，D_ℓ = √(C_ℓ^PR3/c_ℓ^CT) I，C_matched = D C^CT D；等方参照 diag(CVEC)）／**CT-native-unscaled**（secondary：等方参照 diag(c_ℓ^CT)，点ごとに異なる）。intake は `t1_engine.load_cov_full`（対称性射影・PSD・two-point gate・cov/array SHA）。CMBtopology pin `0cc65e34`・requirements pin・clean scratch **[継承：A11 R6]**。共分散 cache key に環境 fingerprint・shape・x₀・系統を含める。

**4.7 immutable ID** **[明文化：v0.5 強化項目]**：`family_id`・`shape_id`・`observer_id`・`system_id` は登録点ごとの不変整数（表の行番号は使わない）。Phase C で全座標・単位・shape・circle label・重みを manifest として固定する。

---

## 5. 統計量・評価器・axis semantics

**5.1 統計量** **[継承：A5・A8]**：S⁺_a = xᵀB⁺_a x（a = 3072 axes），選択 a* = argmin_a S⁺_a（first occurrence），T₁ = S⁺_{a*}，T₂ = S⁻_{a*} = xᵀB⁻_{a*}x。

**5.2 ℓ2–4（S1 surrogate＝Step 1 主評価器）** **[継承：A10 supersede]**：route `l24_feature231`・**selection float64・evaluation float64**・chunk 2000（A8b float64 winner）・BLAS threads 2。float32 selection は sensitivity path（cross-selection gate：flip は selected S⁺ の相対差 < 1e-6 の near tie でのみ／Event B mismatch 率 ≤ 1e-5）。A8b の float32 推奨は性能 benchmark として有効。

**5.3 S2（hybrid ℓ≤16・A8a F16）** **[HOLD]**：selection float32／evaluation float64／chunk 1024・axis block 3072。**S4／exact validation gate まで科学的採用しない**。

**5.4 axis semantics** **[新規・A8b amendment＋A10 発見]**：scientific axis は unoriented plane [n] = {n, −n} と near-minimizer set で報告する。near-minimizer set の定義（固定）：float64 score S⁺_a（3072 軸）について {a : S⁺_a ≤ S⁺_min·(1 + 1e-6)}（相対許容 1e-6・plane-folded で重複排除・集合の大きさと要素を保存）。**一次評価は raw argmin 代表で行い**，集合から都合のよい T₂ を選び直す手順は導入しない。raw oriented index は float32 では blocking／BLAS／hardware 依存で，exact antipode だけでなく遠い非対蹠 plane（A10 official：85°）へも移り得る。T₂ は選択 representative の float64 B⁻ 行に依存する量（antipodal representative の B⁻ 行は同一でない場合がある：A5 292/3072 軸）。float64 primary では raw index の chunk 間完全再現を要求する。

**5.5 二次量** **[継承：A5]**：Q_T1・Q_noncomp・total・ρ を必ず報告（§1.3）。旧 T₂ 中央帯 q₁₆–q₈₄ は付録の履歴・記述的診断のみ（代替 primary にも救済判定にも使わない）。

---

## 6. 標本生成・乱数設計・計算予算

**6.1 生成** **[継承：A9・A10・A11]**：z ~ N(0, I₂₁)，x = D(R)·S·z，S = principal symmetric sqrt（‖S−Sᵀ‖_F/‖S‖_F < 1e-12，‖SSᵀ−C‖_F/‖C‖_F < 1e-10；provenance に λ_min・clip・SHA）。**official 受理条件（A10 継承）：clip = 0 かつ λ_min_raw > 0**。§6.4 の clip 許容 1e-12·λ_max は診断・異常検出のための閾値であり，実際に clipping した根の official 受理を許可するものではない（許可するなら新規変更）。D(R) は凍結実基底上の求積表現（直交性 1e-10・準同型 1e-10・直接幾何 1e-10・既知 z 回転；bit-hash は gate にしない）。

**6.2 orientation cluster** **[継承：A10]**：**1R : m z，m = 100**（Δ_m = log 1.10 の practical equivalence・5 seed 等価・4 run 精度 gate 通過）。m=100 の実測は E7 1 点・matched の設計電池であり全点での精度保証ではない（各評価で精度 gate を検査）。

**6.3 CRN group と評価 ID の分離** **[新規・監査 §4]**
- `evaluation_id`：family／shape／observer／system を完全に識別する不変整数（§4.7）。
- `crn_group_id`：同じ latent (R, z) を使う対象の集合を識別する。
- `rng_key = (MASTER_SEED, wave_id, purpose_id, crn_group_id, batch_id, stream_id)`（すべて整数）。**evaluation_id は rng_key に入れない**（入れると点ごとに乱数が変わり CRN にならない）。
- `cluster_uid = (wave_id, purpose_id, crn_group_id, batch_id, rotation_index)`（row index ではない）。`crn_group_id` は registry で**全 purpose・全 wave を通して大域的に一意**とし，join 時に同一 latent であることを manifest で確認する（推測で修復しない）。
- 依存構造表（表 2）：

| 用途（purpose） | 同じ latent を使う範囲（crn_group） | 他用途との関係 |
|---|---|---|
| Q の evaluation | 登録 family 内の全配置・両系統・model/reference | fitting／calibration／pseudo と独立 |
| KDE fitting bank | 登録 family 内の対応 model/reference・両系統 | evaluation 等と独立 |
| W₂ independent primary | **各 position が独立**（family 共有の例外） | 対応する f64/f32 の同一標本比較のみ paired |
| W₂ CRN diagnostic | 明示した 3 position で共通 | primary W₂ とは別 purpose |
| calibration bank（whitening・p1_obs） | 等方のみ | 全用途と独立 |
| pseudo observation | pseudo 間は m=1・独立 | evaluation／fitting／whitening と独立 |
| negative control | 比較対象 reference と独立 | 独立 bootstrap を適用 |

**6.4 乱数 registry** **[明文化：v0.4 §7＋継承：A10＋修正]**：永続整数表 STREAM・TOPOLOGY・PURPOSE（calibration・evaluation・fitting・pseudo・negative_control・w2_independent・w2_crn・w2_isotropic）と exact call inventory gate。C^{1/2} は principal symmetric square root S = V√Λ Vᵀ（固有値降順・clip 許容 1e-12·λ_max）。**Cholesky を使わない理由（訂正）**：任意の因子 A で AAᵀ = C なら周辺分布は同じだが，同じ z を複数模型に渡すときの CRN coupling は A に依存する。因子を principal symmetric sqrt に統一して coupling を固定する（S は厳密算術では固有ベクトルの符号・縮退固有空間内の基底変更に不変）。

**6.5 N と拡張** **[新規・ChatGPT §4＝v0.4 §3 の継承]**：**N₀ = 10⁶（cluster 10⁴）**を各「family × shape × observer × 系統」の model 実現数とする（対応 reference・fitting・calibration・pseudo bank は別勘定）。精度 gate（§7.3）未達のときのみ**総 N = 4×10⁶ へ一度だけ拡張**（追加ではなく総数）。それでも未達なら `precision-unresolved`（topology unsupported とは区別；family prior から削除・再正規化しない）。拡張条件は精度のみ（Q が閾値を超えるまで反復しない）。importance sampling は登録しない。適応後の percentile 区間は逐次停止下の厳密 95% 被覆を主張せず，誤判定は最終手順込みの global 較正（§9）で検査する。
- **異なる prefix 長の paired bootstrap** **[新規・監査 §4]**：family 内で点 A が N₀・点 B が 4N₀ のとき，共通なのは最初の prefix（batch 0）のみ。登録案（案 2）：点別拡張を維持し，共有 prefix と追加 batch の availability を `cluster_uid` で記録，**共有 prefix と追加部分を別 stratum として再抽出**（各 stratum 内で cluster を復元抽出・stratum 重み（例 1/4・3/4）と各点の分母を保つ；追加 batch を複数の拡張点が共有するならその中も paired；元々独立の追加 bank を row 番号で結ばない）。案 1（family の evaluation group 全体を 4N₀ に拡張）は予算増を伴う仕様変更として保留。**Phase B の小規模 reference（literal 展開）で依存構造を検査してから確定**（未検証のまま凍結しない）。
- **零 hit の順序** **[新規・監査 §7.2]**：N 拡張を先に適用し，残る零 hit を推定上の未解決（precision-unresolved）とする。W₂ トリガー（§10.2）で零 hit 位置により True となる場合は `expansion_due_to_zero_hits` と記録し，零 hit だけから position dependence が証明されたとしない（全位置零なら 0/0 は未定義）。

**6.6 予算** **[継承：A8]**：ℓ2–4 float64 chunk 2000 ≈ 1.3 min/10⁶（Colab 2 threads）。初期 60 評価＋対応 reference ≤ 120 走査単位 → 純走査 ≈ 156 min（共分散生成・回転・bootstrap・KDE・W₂・I/O は別）。4 倍拡張・12 位置拡張・full-grid 較正・S4 は別予算。

---

## 7. 予言分布・推定量・精度 gate

**7.1 P と Q** **[継承：A10＋新規補強（境界値・最悪補完）]**：P_M,j,s(E_B) = 標本平均；cluster 集計表 h_M,j,s(k)・h_I,j,s(k)（cluster k の hit 数）を保存。Q の区間：paired orientation-cluster bootstrap（cluster ID を復元抽出・cluster 内 100 z は保持・model/reference は paired・B = 2000・2.5/97.5 percentile）。replicate の状態（表 1b・機械可読）：

| 状態 | 扱い |
|---|---|
| 分母 > 0・分子 > 0 | finite positive ratio |
| 分母 > 0・分子 = 0 | **有効な境界値 Q = 0（logQ = −inf）**。除外しない |
| 分母 = 0・分子 > 0 | **有効な拡張値 Q = +inf**。除外しない |
| 両 0 | undefined。未知 slot として件数を記録 |
| NaN 等の数値失敗 | 技術的 invalid（意味上の 0/inf とは別）。件数を記録 |

`defined_fraction`（有効値の割合）と `finite_fraction` を混同しない。**分位の定義**：(a) 通常ケース（全 replicate が有限正）：logQ 配列に NumPy 既定 `linear` で 2.5/97.5 分位を取り，指数で Q 空間に戻す。(b) 境界値（0／+inf）を含むケース：拡張実数上の**順序統計量（`inverted_cdf`）**で端点を取る（±inf を含む補間を行わない；`isfinite(logQ)` で行を捨てない）。(c) **数学的 undefined（有限・検証済み hit 数から生じる 0/0）の slot がある場合のみ最悪補完**：y₋ = sort(未知 logQ を −inf で補完)，y₊ = sort(+inf で補完)，**L = y₋[floor((B−1)·0.025)]，U = y₊[ceil((B−1)·0.975)]**（NumPy の `lower`／`higher` に相当；補間しない。完成配列に対する linear と inverted_cdf の両方を外側から包絡する）。補完で label が変わる場合は `CI-boundary-unresolved`（比較対象は有限値のみの label ではなく，保守的端点と必要な precision 条件から決めた状態）。**技術的 invalid（NaN・破損・実装例外）は補完による受理の対象とせず `audit_Q = FAIL`**（1 slot でも；label が変わらなくても）。global 較正では §9.2 の技術監査 FAIL。残った有限値だけから有利な区間を作らない。同じ規約を補助確率 P・Q_T1・Q_noncomp の CI にも適用（Q_noncomp の条件付き分母 0 は undefined；**P の支持域は [0,1]：logP 上の未知上限は 0 とし確率の上端を +inf にしない**）。
**精度計算との接続**：無限端点・非有限幅・点推定 Q=0／undefined は精度条件を PASS にせず状態を保存；log 幅の平均が 0 で CV が 0/0 なら例外状態を明示（NaN の比較に任せない）。CI ごとに effective quantile method・境界値数・undefined 数・technical-invalid 数を保存。
**CI 相対半幅** := (exp(U) − exp(L))/(2Q)（Q 空間；A10 継承）。**5-seed CV** := **logQ 空間の CI 幅**（U − L）の std（ddof=0）/mean（seed 0–4；A10 `CI_width_CV_5seeds` を継承。Q 空間の幅 CV とは代数的に異なる）。正式区間は seed 0。

**7.2 logD** **[新規・ChatGPT §5：Phase B で実装・検証する推定器仕様]**
- fitting bank（評価 bank と独立 stream・cluster_uid で独立性を担保）：**N_fit = 2×10⁵・m_fit = 100（独立 cluster 2000）**を各点・各系統・model/reference に。座標は raw (T₁, T₂)（μK² 単位；前処理なし。密度比は共通可逆 affine 変換で Jacobian が相殺され不変だが，密度そのものは Jacobian で変わる）。**帯域幅 `bw_method='scott'` に固定**（係数 n_eff^{−1/6}）。log 密度は `logpdf`。
- **帯域幅感度電池（推定量監査）**：係数 ×0.7・×1.4 で logD を再計算し，符号不変かつ |ΔlogD| < 0.1 なら PASS；符号が変われば `kde-sensitive`（strong は inconclusive，support の logD_point は不採用→inconclusive）。
- CI：fitting bank の orientation cluster を復元抽出（cluster 内は独立再抽出しない），同じ CRN を共有する model/reference・両系統に共通の cluster 抽出，各 replicate で登録 KDE 手順を再適用，**B_KDE = 2000**，L_logD = q_0.025(logD*)・U_logD = q_0.975(logD*)。strong の「D 下側 CI > 1」は L_logD > 0。
- family 判定用は各 replicate で点の密度を prior 重みで混合（logsumexp）してから logD_M,s を取る（§8）。
- weights による高速化を使う場合は literal resampling との一致を小規模で検証。**KDE 失敗（fail-closed・§9.2 と統一）**：必要な replicate が数値的に失敗（特異・logD 非有限）した場合，その replicate を削除して CI を承認しない。当該 CI を invalid（`audit_DCI = FAIL`）とし，strong／unsupported の CI 依存判定は評価不能。global 較正では技術監査 FAIL。同じ登録標本・同じ乱数による決定的な再計算で解消することは可能だが，別の乱数 replicate に差し替えて成功分だけ採らない（欠測率 5% 以下でも 2.5% 尾部は保証されないため，valid fraction は診断にとどめる）。
- 帯域幅感度 gate は **符号不変 ∧ |ΔlogD| < 0.1 の両方**を要求（符号のみ同じで Δ=0.2 は不合格）。gate は各点と family mixture の logD の**両方**に掛け，科学的 family 判定は混合後の量を使う（必要な点の数値失敗を重み 0 で捨てない）。KDE audit 不合格は support 側にも unsupported 側にも inconclusive。
- `gaussian_kde` の n_eff は等重みでは行数 N_fit（= 2×10⁵）であり cluster 数 2000 ではない（Scott に cluster-aware ESS は入らない；実装どおりの n_eff を登録）。別 seed の fitting bank での再計算は再現性／MC 感度検査であり別推定法ではない（別推定法を要求する場合は具体名と基準を固定）。密度比は共通可逆 affine 変換で不変だが密度自体は Jacobian で変わる。
- 計算量：全 pseudo × 全 B の素朴実装は 10¹¹ 級の kernel 項評価になり得る。Phase B で短絡・batch 化・literal reference との同値性を測ってから全体時間を見積もる。
- 短絡：logD CI の計算要否は **§1.4 の CI 依存表にのみ従う**（strong 候補と unsupported 候補；未計算理由を保存）。

**7.3 精度 gate** **[継承：A10＝v0.5 第三案]**：点ごと：event-positive cluster ≥ 50（model・reference とも）∧ Q の CI 相対半幅 ≤ 0.20 ∧ 5-seed CI 幅 CV < 0.2。cluster ESS は superseded。**family-level 精度**：family 混合の Q_M,s についても同じ相対半幅・CV 条件を要求し，family 内に precision-unresolved の点があれば family は precision-unresolved（削除・再正規化しない）。

**7.4 零 hit** **[新規・ChatGPT §1]**：全 hit = 0 の [0,0] 区間を確率 0 の証明に使わない。cluster-aware 上限が検証されるまで零 hit は precision-unresolved。

---

## 8. family 単位の集約・報告

**8.1 統一式** **[明文化：v0.3 §3＋ChatGPT §6]**：family M・系統 s・配置 j・固定重み w_j：
P_M,s(E_B) = Σ_j w_j P_M,j,s(E_B)，P_I,M,s(E_B) = Σ_j w_j P_I,j,s(E_B)，Q_M,s = P_M,s / P_I,M,s；
f_M,s = Σ_j w_j f_M,j,s，f_I,M,s = Σ_j w_j f_I,j,s（logsumexp），logD_M,s = log f_M,s − log f_I,M,s。
機構分解も family mixture の P(A∩B) と P(A) から条件付き確率を作る（点ごとの Q_noncomp を平均しない；分母 0 は undefined）。
matched は等方参照が共通なので分母を共通化できるが，CT-native は点ごとに参照が異なるため **Q_j の単純平均を一般式にしない**。bootstrap は各 replicate で「混合 → 比 → 区間」（CI 端点を平均しない）。max・採択点割合・logD 平均は採用しない。

**8.2 point-level 診断表**：全 60 評価の Q・logD・Q_T1・Q_noncomp・区間・精度 gate・hit 数・cluster 数を表に（短絡で未計算の logD 区間は `not_computed_by_registered_short_circuit`；埋める追加計算は別予算）。点の local rule 充足だけで family support と呼ばない。最終 summary／label には §2.1 の surrogate scope を一文併記する。

**8.3 label 使用条件**：support／strong は §9 の較正が usable の場合のみ label として使用。不能なら「descriptive / calibration-failed」。E_B 確率が小さい点の補助ラベル（§1.5）を併記。

**8.4 位置感度**：§10 のトリガーが発動した family は `position-sensitive / provisional` とし，登録済み 12 位置設計の完了まで最終分類を出さない。3 位置判定は保存。

---

## 9. global false-support 較正

**9.1 対象** **[明文化：v0.5 定義 4]**：PR3_Commander の primary-map core rule（support／strong）。robustness は較正外。

**9.2 手順** **[継承：A10c 実装／新規：全 family 化]**：等方 pseudo 観測（独立 stream・m = 1）**固定長 n_pseudo = 2000**。pseudo ごとに 2D 閾値 (T₁,p, T₂,p) で全 family・両系統の Q・logD・support／strong を再評価（再走査なし：sorted-T₁ 集計表＋共有 cluster 再抽出行列＋log-KDE；brute-force 一致 gate）。N₀→N_max の適応規則を再現できるよう最大長 bank を用意し prefix を使う。FWFSR_support / FWFSR_strong（any-family）と Wilson 95% 区間。**usable ⇔ 上側 CI ≤ 0.05（support）／≤ 0.01（strong）**。**評価不能 pseudo の集計（固定）** **[新規・監査 §6]**：
- 技術的 invalid（NaN・KDE failure・壊れた stream・欠落 artifact）→ 当該較正の**技術監査 FAIL**（値を出さない）。
- 推定上の unresolved（最大 N でも精度未達等）→ pseudo p ごと・support／strong それぞれに：いずれかの family が確実に True → Y_lower = Y_upper = 1；全 family 確実に False → 0/0；True は無いが未解決 family がある → Y_lower = 0, Y_upper = 1。n = 2000 固定で既知 True c 件・unknown u 件なら経験率は [c/n, (c+u)/n]。**usable 判定は保守的に WilsonUpper(c + u, n) ≤ 閾値**（unknown を 0 扱いしない・分母を減らさない）。
- `calibration_usable_support` と `calibration_usable_strong` を分離。一方のみ通過なら，その水準の label のみ使用し，strong label は両方通過を要求。
- 逐次停止（「上端が閾値以下になるまで追加」）は採用しない（採用するなら confidence sequence 等を別登録）。
- **scope**：較正は固定された MC 資産（最大長 evaluation／fitting bank・KDE 設定・bootstrap 乱数・W₂ null）に条件付けられた保証であり，bank 自体を再生成したときのばらつきを含まない。

**9.3 control** **[継承：A10c＋新規]**：negative（独立等方 replicate・独立 bootstrap；support 率 ≤ 0.05），positive（T₁,T₂ を 0.35 倍した synthetic boosted；観測閾値で support_core と **strong_core の full predicate**（L_Q ≥ 10・L_logD > 0・native positive）を通すこと），**各 conjunct を一つずつ落とした negative unit test**（例：native opposite・L_logD ≤ 0・L_Q < 10 で strong が False になること），CI 省略時の状態記録，brute-force 一致，valid fraction，finite inventory。A10 の既存 control 通過をもって新しい strong-CI 実装が検証済みとしない。

**9.4 工程** **[新規・ChatGPT §7]**：rules draft → Phase B engine と control 電池 → Phase C 仕様・grid 凍結 → Phase D 共分散・bank 生成 → **実観測の full-grid 判定値を封印したまま global 較正・監査 → calibration usable を封印 → Phase E で実観測判定を解放**。既存 cache を使う場合も grid／bank の identity と依存関係を明示。FAIL 時は閾値 3/10 を変更せず label 不使用。

**9.5 実測値** **[HOLD]**：A10c（one-point・one-system・n=200：0/200）は prototype であり較正値ではない。

---

## 10. 観測者位置の拡張トリガー（W₂）

**10.1 推定量** **[継承：A10d＋固定]**：校正 bank（等方・matched 系統・N_cal = 2×10⁵・m = 100）で whitening（Σ_cal = LLᵀ，W = L^{−1}，T̃ = W(T − μ_cal)；gate `G_whitening`: ‖WΣ_calWᵀ − I‖_max < 1e-10；W は対称な Σ^{−1/2} ではないが共通直交変換の差のみで，全 pool・両 path に同じ W を適用すれば距離は同一）した (T₁,T₂) の exact 2D W₂（POT `emd2`・sqeuclidean・√・uniform weights）。**n_sub は標本数**（2000 と 5000；cluster 単位で採るため cluster 数は 20 と 50）。3 位置 max-pairwise。primary は位置ごとに独立 (R,z) stream（各位置 pool N_W2 = 2×10⁵）；null は等方 pool（3×N_W2・総 cluster 6000）から replicate ごとに disjoint な 3 cluster block の max（pool 枯渇時は再置換）。CRN 版は `CRN diagnostic`（一般に保守的とは主張しない）。quantile 法 `higher`。exceedance は finite-pool exceedance estimate。**トリガーは matched 系統・family × size 単位**で評価し（native は診断），family はいずれかの size で True なら position-sensitive。**E1 は observer-homogeneous のため対象外**。
- **B_null の規則（固定・engineering stability rule）**：全 B は同一の最大長 null 列（B_max = 1000）の prefix（B 増加時に先頭を再 seed しない）。B = 200, 400, 600, 800, 1000 を順に評価し，**最初の比較は B=200 vs 400**。停止 ⇔ 3 seed × 2 n_sub の above/below indicator vector が前水準と同一 ∧ **n_sub = 2000・5000 の両方**で |q₉₉(B) − q₉₉(B−200)| / q₉₉(B−200) < 0.05（最大相対変化で判定）。B_max で未達なら `w2-unresolved`。5% は q₉₉ の統計誤差 5% の保証ではない。
- **selection 感度の scope（固定）**：B_final は **float64 primary のみで決定**し，float32 感度は同じ B_final・同じ prefix・同じ subset・同じ W で評価する（exact-subset coupling bound は同一 B の条件付き判定不変性を意味する）。float32 で停止規則を選び直した別アルゴリズムの不変性は主張しない。
- **W₂ 用 bank は f64 primary と f32 sensitivity の両 path で生成**（§12.5 の subset 規則の例外；OT に投入する subset の paired 出力が bound に必要；コストは小）。

**10.2 トリガー** **[明文化：v0.5 定義 3＋状態表]**：W₂_max > q₉₉ **または** max_k P_k(E_B) / min_k P_k(E_B) > 2（各 P_k が精度 gate 通過後；N 拡張後に hit 0 の位置が残れば True とし `expansion_due_to_zero_hits` を記録）。**3 値 OR の状態表（表 6）**：

| W₂ trigger | event-ratio trigger | 結果 |
|---|---|---|
| True（有効） | 任意 | 拡張（position-sensitive） |
| 任意 | True（有効） | 拡張 |
| False | False | 非拡張 |
| unresolved / False | unresolved / False（True 無し） | `position-unresolved`（family provisional） |
| 技術監査 FAIL | — | OR で打ち消さない：技術監査 FAIL |

実装順序：技術 FAIL を最優先 → 有効 True → 両 False → 残る unresolved（技術 FAIL は両 branch で同じ扱い）。零 hit による拡張は ratio を inf に置くのではなく，別の登録理由 `expansion_due_to_zero_hits` として保存。12 位置段階の完了が解消するのは 3 位置段階の **position status のみ**（新 12 位置の coverage・Q 精度・KDE 監査・技術 FAIL は免除しない；3 位置結果は archive）。

**10.3 安定性 gate と未収束の状態** **[継承：A10d＋固定]**：3 subsample seed の判定一致・n_sub 2000/5000 の判定一致・W₂_max の seed 間 spread ≤ 0.25・selection-path の decision margin（exact-subset coupling bound；**未測定の bound を 0 として PASS にしない**）。いずれか不成立 → `w2-unresolved`（family は provisional 扱い；unsupported と混同しない）。null replicate ごとの bound 配列を保存。等方 null の q₉₉ は登録 isotropic reference に対する有限標本 scale であり，全トポロジー分布での 1% 検定とは限らない。位置拡張を含む最終 support は global 較正（§9）で同一手順を再現する。

**10.4 3→12 位置** **[明文化：v0.4 §4.2–4.3＋新規]**
- v0.4 §4.3 の工程をそのまま採用：**3 位置の結果は archive（削除も改変もしない）→ トリガー True の family は `provisional / position-sensitive` → 12 位置段階（新規登録）完了後に最終 family-level 分類**。v0.3 の「第 1 波判定を変更しない」は v0.4 で撤回済み。
- v0.4 §4.2 の閾値定義（同一分布からの 2 独立サンプル間の有限サンプル W₂ null の 99 百分位）は，A10 で **3 位置 max-pairwise に対応する null（disjoint 3 block の max）**に精密化した（付録 B）。トリガーの 2 条件（W₂ と event-ratio > 2）は v0.4 のまま。
- v0.4 §4.1 の写像 x₀ = A_M(θ)u（単位立方体→基本領域）は，A6 の family 固有 reduced 座標（pilot_v2_reduced）＋A11 の canonical bridge x₀_CT = −r_obs に **置換**された（対称等価位置の回避は reduced 座標の box・exclusion で実現）。
- **12 位置設計そのものは v0.4 に無い（「新規登録」とだけ規定）**。本稿の登録案 **[新規・結果非依存に固定]**：(i) **nested**——既存 3 点を保持し 9 点を追加；(ii) 生成規則は A6 と同じ reduced 座標系・同じ box・**新しい分離条件**（旧 min_sep は 12 点に対して幾何的に不可能：E7 box 幅 0.21 に対し 11×0.06 = 0.66 必要，旧規則で最大 4 点）——E7 min_sep = 0.015・E2 min_sep = 0.05・E8 min_sep = 0.04（既存 3 点との距離にも適用），**決定的生成器**：候補集合は reduced 座標の格子（分解能 1e-4・box 内・exclusion 適用），距離は A6 と同じ（E2 は商空間距離），旧 3 点を固定 anchor とし，greedy maximin（各 step で既選点集合からの最小距離を最大化する候補を追加・tie は辞書順で先）を 9 step，乱数は用いない（辞書順 tie-break を守れば候補順は結果に影響しないため，seed [20260913, 12] は順序不変性のテスト用に留める）；min_sep 違反・候補枯渇・旧 anchor 消失は fail-fast（成功するまで seed や閾値を変える手順は加えない）；E2 の閉格子は exclusion 前 10⁸ 候補・E8 は 9×10⁶ 候補なので全距離行列を作らず block ごとの最短距離更新で同じ argmax・tie-break を実装；生成 script と完全 SHA・full-precision 座標・重み・再実行同一性を Phase C で凍結；追加 9 点にも A7 の circle coverage と A11 の clone／weight 検査を適用（旧 3 点の件数を転記しない）；実現可能性は E7 について確認済み（ChatGPT 監査 draft2：配置例の最小距離 0.0169；draft3 監査：本稿の greedy 規則の 1 次元 reference で最小距離 0.0158・旧 3 点保持・候補順反転で同一）；(iii) 重み等重み 1/12（連続一様 prior の積分とは主張しない）；(iv) 12 位置段階の判定は §8.1 の混合を 12 点で行い 3 位置結果と併記（3 位置結果は archive）；(v) global 較正（§9）に 12 位置段階の手順を含める；(vi) E1 は対象外；(vii) **拡張の範囲**：family がいずれかの size でトリガーされたら，当該 family の**全 surviving size** を 12 位置に拡張（各配置重み (1/3)·(1/12) = 1/36；全 3 非均質 family が拡張された場合は E1 を含め 111 配置・2 系統 222 評価＝予算算術）。

**10.5 実測値** **[HOLD]**：registered p^(3) での W₂ と最終 q₉₉（B 増加・precision stopping）。A10d の mock 結果（q₉₉ 未満）は推定量の動作確認である。

---

## 11. 独立診断 **[継承：A9]**
Imhof–Gil–Pelaez は「固定向き・固定軸の S⁺ 周辺裾」の独立診断で，per-case 適用性 gate（PSD・rank・積分誤差 < 1e-8・GP 収束・Imhof–GP < 1e-6・単調・[0,1]）を通る場合のみ用いる。axis 選択・joint (T₁,T₂)・Event B・Q_noncomp は MC 依存のまま。モーメント電池・鞍点法は診断。Haar 電池（KS／Holm）で回転 stream を検査。

---

## 12. 計算環境・数値方針・gate 設計原則

**12.1 exact version（hard gate）** **[継承：A8・A10・A11]**：Python 3.13.15・NumPy 2.1.3・SciPy 1.16.3・healpy 1.20.0・CAMB 2.0.4・POT 0.9.7.post1。archive：pandas 2.2.3・numba・spherical・quaternionic・BLAS/LAPACK backend・platform・`pip freeze`。BLAS：NumPy 同梱 OpenBLAS の pool = 2，他 pool ≤ 2。

**12.2 SHA の原則** **[新規・ChatGPT §8.3]**：凍結ファイル（浮動小数を含む）は必ず file SHA と array SHA で同一性検査。**別環境で再生成する浮動小数配列**（求積節点・三角関数出力）は byte 一致ではなく数学的 gate（Gauss–Legendre 厳密性・直交性・準同型）。M21 は凍結基底の実際の dtype／規約に従って SHA 検査（整数構成物と一括扱いしない）。antipode map（int32）は SHA。

**12.3 fail-fast**：非有限出力・repo clean／commit／origin・live notebook source・module purge＋live path・出力 inventory exact・乱数 call inventory exact。checkpoint は source・環境・入力配列に binding。

**12.4 engine cross-check** **[継承：A10]**：map-free 等方 engine が A5 map-based null を再現（T₁/T₂ 中央値が A5 bootstrap 95% CI 内，P(T₁≤obs)・P(E_B) が Wilson 区間内）。

**12.5 float32 sensitivity の記録**：ℓ2–4 の evaluation bank では登録 subset（各 family・各系統 1 点・N₀）で float32 併走し flip evidence（index・両 axis・antipode 関係・plane 角・T₁/T₂・Event B）を保存。**W₂ 用 bank は例外として全位置・null pool を両 path で生成**（§10.1；exact-subset bound の required 入力）。既測の m=100・float32 差を未検証の全 shape・S2 に一般化しない。

---

## 13. Provenance・監査工程

**13.1 工程** **[継承：全 freeze]**：ChatGPT 実行前監査（notebook file／source-only SHA）→ commit → fresh runtime smoke（`MODE='smoke'` セル追加）→ fresh runtime・fresh OUT official（純正 notebook；live source == origin/main を hard gate）→ 独立再計算（ChatGPT・Claude：freeze 成果物のみから）→ freeze（manifest v2・annotated tag・LF 正規化 log・受領 SHA 一覧・history 同梱・ASCII ファイル名）。

**13.2 provenance 必須項目**：status・required／diagnostic gate の区別と `gate_policy`・component status・出力 SHA・superseded 履歴・amendment binding・generation stream calls・環境・notebook identity・SCIENCE_FLAGS（audit gate と別キー）。

**13.3 命名**：`runs_step1_phase<X>/<stage>_v<ver>_{smoke,official}/`，tag `step1-phase<X>-<stage>-freeze-v1.0`。

**13.4 封印**：Phase E の実観測判定は，較正 usable の封印（§9.4）後に解放。

---

## 14. Phase B engine への要求事項（別文書 `Step1_PhaseB_engine_spec` に分離可）
- 入力：§4 の grid manifest（immutable ID・full-precision 座標・重み・circle label・系統），§2 の凍結資産，§6 の乱数 registry。
- 計算：各評価で (T₁,T₂,cluster_id,AX,PL)×N₀（拡張時 4N₀）；Event B 集計表 h(k)；Q_T1・Q_noncomp・total・ρ；Q の cluster bootstrap（B=2000・5 seed）；fitting bank と log-KDE・logD の cluster bootstrap（B_KDE=2000）；family 混合（§8）；W₂ 3 位置（§10）；較正用の pseudo 集計（§9）と control 電池。
- 保存（**freeze 成果物のみから再計算できる水準**）：evaluation／fitting bank 本体（T₁・T₂・cluster_uid・AX・PL；immutable path と完全 SHA）・集計表・flip evidence・bootstrap 分布（5 seed）と共有再抽出 group／weights／seed・logD replicate・pseudo thresholds・点別適応 prefix 長・W₂ 投入 index と paired f64/f32 出力・null 配列＋bound 配列・checkpoint（stage 別・binding）。
- Phase B 完了条件：control 電池（negative／positive／brute-force）と A5 cross-check の PASS，engine の smoke／official が mock grid で `ENGINE_VALID`。

---

## 15. HOLD／未決の区別と機械可読表
機械可読表（凍結前に合成ケースで文章と一致を確認）：表 1 decision predicate（§1.4）・表 1b replicate 状態（§7.1）・表 2 CRN 依存（§6.3）・表 3 eligibility（coverage §4.3・precision §7.3・calibration §9・position §10）・表 4 expansion（§6.5：N₀→4N₀・prefix・零 hit）・表 5 較正集計（§9.2：Y_lower/Y_upper・Wilson(c+u)）・表 6 トリガー状態（§10.2）。付録 A の短縮 SHA は表示用であり，Phase C packet の機械可読 manifest には完全 tag／commit／file・member SHA・shape・単位・lift を置く。

| 実測値として HOLD 可 | 仕様として v1.0 凍結前に閉じる（本 draft の §） |
|---|---|
| full-grid global false-support 率の値（§9.5） | family 集合・shape/size・全座標・prior 重み（§4） |
| registered p^(3) の W₂ と最終 q₉₉（§10.5） | N₀・N_max・拡張条件・精度未達の扱い（§6.5） |
| S2 の科学的採用（§5.3） | Q／logD／CI の推定器・B・帯域幅・fitting bank（§7） |
| | 3→12 位置：生成器は §10.4 で固定・manifest 生成は Phase C |
| | 異なる prefix 長の stratified paired bootstrap の検証（§6.5：Phase B 小規模 reference） |
| | UID namespace・CRN group registry（§6.3） |
|  | pseudo 数・停止規則・較正合格条件（§9） |
|  | W₂ null の生成／再利用・B・quantile 規則・未収束時の処置（§10） |

---

## 付録 A. 凍結資産一覧
| stage | tag | commit | 主要 SHA |
|---|---|---|---|
| A5（B-stack・null・Event B） | step1-phaseA-A5… | — | npz `ec2d3eb5…`／array `eb514148…` |
| A6/A7（観測者・円制約） | step1-phaseA-A6A7-v1.0 | — | observer JSON `a5ea1ae6…`・circle CSV `47b2d910…` |
| A9（回転・Haar・Imhof） | step1-phaseA-A9… | — | script `2905c036…`・provenance `09c03219…` |
| A11（x₀ 橋渡し） | step1-phaseA-A11-freeze-v1.0 | 104d5912 | notebook source-only `c1f3a362…`・env lock v2 |
| A8（特徴スタック・走査 benchmark） | step1-phaseA-A8-freeze-v1.0 | 1bdd9ea8 | manifest `3384c9c5…`・F16 `aca84c5f…`/`9e433de0…` |
| A10（W₂・m・較正経路） | step1-phaseA-A10-freeze-v1.0 | 57119546（名前正規化 a321114） | notebook file `c11c4141…`・source-only `731cb898…` |

## 付録 B. 研究計画 v0.4／v0.5 との相違表（原文：v0.4 file SHA `0569ae2f…`・v0.5 file SHA `357e4d7d…`；左欄は原文から転記）
| 項目 | v0.5 | 本 draft | 区分 |
|---|---|---|---|
| primary event | E_sel（T₁ ≤ obs ∧ q₁₆ ≤ T₂ ≤ q₈₄） | Event B（T₁ ≤ obs ∧ T₂ ≤ obs） | 変更（A5 凍結で置換） |
| W₂ 推定量 | exact・n_sub = 20000／不可なら sliced | exact・n_sub = 2000／5000・cluster 単位・独立 stream primary | 変更（A10 実測：メモリ 3.2 GB×，cluster 効果が null を支配） |
| W₂ null | 同一 clustering（1R:100z）の 2 独立サンプル | disjoint 3 block の max・finite-pool exceedance | 明文化＋変更 |
| cluster 精度 | ESS 不使用・positive cluster ≥ 50・相対半幅 ≤ 20%・CV < 0.2 | 同 | 継承 |
| m | 10/100 を 1 点で感度 | m = 100（Δ_m = log 1.10・5 seed） | 継承（判定基準を明文化） |
| dtype | float64 のみ（v0.4 §9） | ℓ2–4 float64 selection／S2 float32（HOLD） | 明文化＋A8 の性能 route |
| D の CI | 未定義 | log-KDE の cluster bootstrap B=2000 | 新規 |
| 較正 | 定義 4（core rule・0.05/0.01・FAIL 時） | 同＋固定長 2000・invalid 別記録・工程順序 | 継承＋新規 |
| family | （v0.3：E1/E2/E7/E8） | 4 族維持 | 明文化 |
| p^(3) | u₁..u₃ を Phase A で生成 | A6 pilot_v2_reduced の等重み 3 点 | 明文化（A6 凍結の採用） |
| 絶対 fit | v0.4 §5.2：P(E_sel) < 1e-4 | Event B に適用・補助ラベル | 明文化＋変更 |
| phenotype gate | v0.4 §1 `G_obs_selective`／v0.5 定義 1 SCIENCE_FLAGS（未確認なら family 判定 inconclusive） | legacy diagnostic（veto なし） | 変更（A5 の Event B 採用と整合） |
| support の D 条件 | v0.3 §3：logD 点推定 > 0（構成案どおり） | 同 | 継承（第 1 稿の厳格化を撤回） |
| W₂ null の B | v0.5 定義 3：B_null=200 | 200 → 最大 1000・停止条件 | 明文化＋新規 |
| x₀ 写像 | v0.4 §4.1：x₀ = A_M(θ)u（単位立方体→基本領域） | A6 reduced 座標 pilot_v2＋A11 x₀_CT = −r_obs | 変更（A6/A11 凍結で置換） |
| 12 位置段階 | v0.4 §4.3：新規登録（設計未定） | 工程は継承；設計は Phase C までに固定（§10.4） | 継承＋新規 |
| unsupported | v0.4 §8：Q 上側 CI < 1 ∧ D 上側 CI ≤ 1 | 同（logD 上側 ≤ 0） | 明文化 |
| IS | v0.4 §3：第 1 版から除外 | 同 | 明文化 |

## 付録 C. superseded 事項
旧 phenotype veto（`G_obs_selective`・OBS_TARGET_CONFIRMED による family 判定停止）／中央帯 E_sel／cluster ESS／ℓ2–4 float32 推奨／「flip は exact antipode のみ」仮定／W₂ n_sub 20000／A10 v1.0 の結果（Q≈1.08–1.11・FWFSR 0/200）／A11 v1.3.1 の識別述語 2T ∈ Λ／A8b v1.1.5 の raw-argmin 完全一致 gate。

## 付録 D. 用語
Event B・support ratio Q・Q_T1／Q_noncomp・CRN・orientation cluster（1R:m z）・plane-folded axis・near-minimizer set・finite-pool exceedance・practical equivalence margin・SCIENCE_FLAGS／audit gate・matched／CT-native。

---

## 次の作業
1. 本稿は Phase B 引渡し版。「Phase B GO」（ChatGPT 監査 draft3・2026-09-13）は B-1 の helper 開発開始の承認であり，engine の全実装・smoke／official の承認ではない。
2. `Step1_PhaseB_engine_spec` を起草：表 1／1b／2／6 の実装，境界値分位 helper と最悪補完の unit test，KDE fail-closed，stratified prefix bootstrap の literal reference，W₂ 停止規則と same-prefix 感度，12 位置生成器，control 電池（strong full predicate・conjunct-drop）。
3. Phase B の control 電池 PASS → Phase C（12 位置 manifest・完全 SHA manifest・v0.4/v0.5 原文同梱）で v1.0 を凍結。
