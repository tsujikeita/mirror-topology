# D4C-2 probe（E2・N＝3）資源報告 v2 — 2026-10-05（監査 D4C2-PROBE の訂正を反映；原本は同 folder の `D4C2_probe_resource_report.md`，SHA `9e9ad98f…`）

対象：監査 `D4C1_v2_0.107.0_audit_decision.json`（PASS_WITH_EXPLICIT_SCOPE__E2_N3_PROBE_ONLY_GO）の `required_run_evidence`。commit `231d37b89271793c8cd1b93c3282d2b851f83d3e`（engine 0.107.0，inventory `01f70420…`，script `834ab646…`，pins `2cd9cf01…`）。
証拠：`d4c1_partial_E2_231d37b89271.zip`（SHA-256 `538f5e07f3c4fae84803d17783ff09a03fef5270cd04b600376e2af891644766`；lock・attempt final record・`run_20261005T100239Z_386d63207c/`（run record・probe record・archive 17 entry・stdout）・stdout／stderr）と実行済み notebook（SHA-256 `72af76c8b161b09eae3815ede13da9416ab5c71a16781e3784fc5c70b4707cd8`）。本報告の数値はすべてこれらの record から読み取ったもので，再計算・再実行はしていません。**v2 の訂正**（監査 `D4C2_probe_231d37b8_audit_decision.json`：D4C2-REPORT-QUANTITIES・D4C2-RESOURCE-EXTRAPOLATION・D4C2-UNKNOWN-NOT-PERMANENT）：§4 の Q_matched と帯域幅感度の転記を原本どおりに直し，§1-2／§5-A の外挿に「上限でも下限でもない」注記を加え，§1-4／§5-B の「ほぼ全件 unknown で usable=False が構造的に決まる」を撤回して監査の解釈（W₂ unknown は恒久的 veto ではない；event-ratio で全 size が 12 位置化し得る；3 件から u≈n は確定しない）に置き換えました。

## 1. 結論（先に）
1. **probe は技術的に clean**：attempt `20261005T100239Z_386d63207c`，lock SHA `9632f840…`，precheck／prelaunch とも HEAD＝`231d37b8…`・clean・inventory／script／pins／登録 ledger 束縛一致。REQUIRED_PARTIAL 24 gate すべて True，`required_all_true=True`，failures／notes 空，exit 0，launcher_fallback False，環境 lock（Python 3.13.15／numpy 2.1.3／scipy 1.16.3／healpy 1.20.0／POT 0.9.7.post1／camb 2.0.4，pool 2）一致。12 位置 official gate は `mode=official, passed=True, environment_source=live_collected`（D-3c binding attempt `20261003T083353Z_dc4ddf4f0f`，plan identity `86a7db7b…`，fingerprint matched `9e4d3dfb…`／native `ad872efd…` 一致）。`probe=True, probe_n=3, gate_mode=smoke` で **`D4C1_PARTIAL_PASS=False`（設計どおり）**。partial record `057ae753…`（archive transition `77252f40…`）は `verify_partial_record` で ok・registered context verified。
2. **時間は現行経路のままでは正式 n＝2000 に届かない見込み**：3 pseudo で 941.7 s，表示平均 **313.9 s／pseudo**。E2 1 family の正式 2000 pseudo を単純外挿すると 2000×313.9 ≈ **6.28×10⁵ s ≈ 174 h（7.3 日）**＋固定費 ≈ 24 分。**この外挿は 3 行平均の素朴な積であり，上限でも下限でもない**（partial 区間にも parent 組立て・fingerprint・gate・保存の固定費が含まれ，他の pseudo では N4 拡張・KDE CI・12 位置分岐が起こり得る；12 位置入力を RAM に置いたことと 12 位置較正を評価したことは別）。Colab の session 上限は公式 FAQ で「通常最大 12 時間，compute unit が十分な Pro+ で最大 24 時間」とされるが保証ではない。D4C-1 の partial は 1 family を 1 process で完走させる設計で pseudo 粒度の中断・再開は持たないため，Colab の 1 session（最大 12〜24 h）には **9〜15 倍以上の高速化か，pseudo 範囲の分割（＝D4C-1 への追加実装と再監査）** のどちらかが必要です。
3. **memory／disk／archive は余裕がある**：peak RSS 16.0 GB（RAM 54.8 GB；12 位置入力 27 配置の intake で到達し，pseudo 評価は +23 MB しか増やさない）。staging 12.33 GB・846 s。archive は 17 entry／2.60 MB（pseudo あたり ≈ 5 entry・≈ 0.86 MB → 2000 pseudo で ≈ 10,000 entry・≈ 1.7 GB／family；`family_result` が 97% を占める）。
4. **unknown の位置づけ（監査で訂正）**：3 pseudo とも eligible truth（support／strong／unsupported）が **unknown（`provisional: position-unresolved`）**。登録 D-2W context（`50ec5a54…`）で **E2/L1.20 の W₂ trigger が `unknown`（w2-unresolved，B_final 800；停止済みで mixed above/below indicator）** と固定されており，3 行の event-ratio（max/min P＝1.0001〜1.0014，閾値 2.0）は発火しなかったため，3 行は position-unresolved → unknown となった。**これは 3 行の結果であって「E2 の全 pseudo が必ず unknown」ではない**：`evaluate_family_full` はいずれかの size で event-ratio が発火すれば全 surviving size を 12 位置段階へ進め，`derive_outcome` は 12 位置の完全評価と local completion が通ればその truth（True／False／unknown）を使う（監査は登録 W₂ context・登録 12 位置 manifest を用いた state-contract 試験でこの分岐を確認）。したがって W₂ unknown は恒久的 veto ではなく，未評価 1,997 行と E7／E8 の分布は 3 件から確定しない。ただし event-ratio が全 size で発火しない pseudo は provisional（unknown）になるため，使用可能性への懸念は深刻であり，**全件計算前に正式 usable=False とは報告しない**（監査 §3）。E7（L1.20・L1.50）・E8（L1.00）も登録 context で unknown。設計 v0.2 §C「unresolved は固定 n で保守的に unknown 集計し，技術的成功でも usable=False になり得る（新 pseudo／seed を引く理由にしない）」は不変。

## 2. 時間（累積 timings の差分；script 内，秒）
| stage | 累積 | 区間 | 備考 |
|---|---:|---:|---|
| preflight | 33.2 | 33.2 | pins・inventory・script SHA・環境 lock・loader SHA |
| first_wave_intake | 94.6 | 61.4 | 第 1 波 9 配置（20101〜20303）各 6〜8 s |
| plans | 113.2 | 18.6 | 登録 UID から plan 再構築＋`verify_consumer_family_inputs` |
| first_wave_views | 177.0 | 63.8 | 両 system の size view（matched／native） |
| twelve_inputs | 522.7 | 345.7 | 12 位置入力 27 配置（各 6〜8 s ≈ 190 s）＋組立・fingerprint |
| twelve_gate | 606.2 | 83.5 | `twelve_official_gate(mode='official')`，live 環境収集 |
| partial | 1547.9 | **941.7** | 3 pseudo → **313.9 s／pseudo**（`timings.seconds_per_pseudo`） |
| verify | 1548.0 | 0.17 | `verify_partial_record` |
| script 合計 | 1548.0 | | |

外側（notebook cell 2）：`seconds_total` 2397.4 s（10:02:39Z → 10:42:37Z）＝ precheck＋staging 845.9 s＋script 1548.0 s＋≈ 3.5 s。
固定費（staging＋intake〜gate）≈ 1452 s ≈ 24 分は family あたり 1 回。pseudo 1 件の内訳（hit table・Q bootstrap B＝2000×5 seed×2 system・KDE B_KDE＝2000・3 size の position 分岐・archive put）は **本 probe では計測されていません**（record は stage 粒度のみ；設計 F.4 が求める単位計測は未実施）。

## 3. memory・disk・archive
| 項目 | 値 |
|---|---|
| RAM（cell 1） | total 54.75 GB，available 52.64 GB |
| current RSS（stage 末） | preflight 1.24 → intake 4.18 → plans 7.55 → views 7.57 → twelve_inputs 15.35 → gate 15.36 → partial 15.38 GB |
| peak RSS | **16.03 GB**（twelve_inputs で到達；以後不変） |
| pseudo 評価の RSS 増分 | +23 MB（3 pseudo 合計） |
| staging | d2 30 unit（`cfg*_w2` 複製なし）＋d3b 3 partition，**12,329,718,617 byte**，845.9 s；disk 219.9 → 195.2 GB |
| archive | **17 entry，2,595,293 byte**：family_result 3（2,525,438 B）・three_position_result 9（13,861 B）・transition 4（plan 3＋partial 1；51,794 B）・registry 1（4,200 B）・index 5,650 B |
| 外挿（2000 pseudo／family） | ≈ 10,004 entry・≈ 1.7 GB（family_result が支配；deferred index でも index.json は ≈ 3 MB） |

## 4. 分岐・verify
- `expanded=0, twelve_evaluated=0`：**12 位置分岐は 1 件も発火せず，その時間・RSS は未計測**。9 件の three_position_result：L1.00／L1.50 は `not-expanded`（W₂ False・ratio False，`both False`），L1.20 は 3 pseudo とも `position-unresolved`（W₂ `unknown`，ratio False，`no valid True; at least one unresolved`）。ratio（max/min P）は 1.00001〜1.00144（閾値 2.0）。precision は 9 件すべて pass（rel_halfwidth ≈ 5×10⁻⁴，positive clusters 10000／10000）。
- 各 pseudo の core（原本の値；v1 の「Q_matched ≈ 1.004〜1.009」は転記誤り）：

| pseudo index | threshold (T1, T2) | Q_matched | logD point | family Q rel_halfwidth | 帯域幅感度 pass |
|---|---|---:|---:|---:|---|
| 0 | (184.44830863995733, 570.5380033417513) | 1.0120085663800016 | −0.03133162894140007 | 0.0010406167403652828 | True |
| 1 | (180.3266829122338, 616.3273246948814) | 1.0091025254182917 | −0.027138603247285786 | 0.0009483806671959942 | True |
| 2 | (176.5814867363503, 1108.3319662045828) | 0.9999809485249505 | −0.00009683230512180785 | 0.00048632894054919973 | **False** |

  logD CI は 3 行とも登録 short circuit で未計算（logD point ≤ 0），`display_label=inconclusive`，core truths すべて False，technical False。3 行目は帯域幅変更（×0.7／×1.4）で logD の符号が変わり sensitivity_pass=False だが，これは record の非技術的な監査結果であり process FAIL や W₂ unknown の原因ではない（core False・eligible unknown の結論は不変）。expansion は両 system とも N0 段階で precision 通過（N 拡張なし）。
- verify 区間 0.17 s，`G_partial_verified=True`，`G_pseudo_identity_bound=True`（pseudo identity `paired_sha256 c9f75cdb…`，n＝2000 の先頭 3 行），`G_plan_objects_stable=True`。

## 5. 正式 4 partial の GO に関わる論点（判断は監査に委ねます）
A. **時間**：現行経路で E2 は単純外挿 ≈ 174 h／family（上限でも下限でもない）。E7・E8 も同規模（9 配置＋27 配置）と見込まれ，E1 は 12 位置入力がないため安価と思われますが未計測。Colab 1 session に収めるには（i）評価経路の高速化（設計 F.4 の候補：sorted-T₁ 事前集計・hit table の cache・KDE 再利用；同等性試験後にのみ採用）と／または（ii）pseudo 範囲 sub-partial と family 内 combine の追加（D4C-1 への実装追加・再監査）が必要です。いずれも新 commit と監査を要します。まず **単位計測（profile）probe**（同じ E2 staged 入力・N＝1〜3・非正式・cProfile／stage 内 timer を record に残す）で pseudo 1 件の内訳を取ってから高速化対象を決めるのが設計 F.4 に沿うと考えます。
B. **unknown の構造（監査の判断）**：§1-4 のとおり「ほぼ全件 unknown で usable=False が決まる」は撤回。監査の方針：(a) 原登録を基準に維持（支持）。ただし 174 h の外挿のまま全件投入せず，計測・再開設計と **固定分母の成功不能証明**（監査 §5：少なくとも 1 family の最終 eligible が True／unknown と確定した行は global の c+u に必ず 1 を加える；n＝2000 固定の登録 Wilson 式では support 81 行・strong 12 行で，残りを全部 False と補完しても上端が閾値を超える；bootstrap／KDE を回さない十分条件＝全 position × 両 prefix（N0／N4）の正確 hit 率の包絡で max/min ≤ 2 かつ全率＞0）を先に評価する。(b) B_max 延長は今回の 4 件（B_final 800／600／400／400 で停止済み，mixed indicator）の原因に対応しない（監査が null tail を伸ばした counterfactual で停止 record 不変を確認）；unknown→12 位置 fallback 等は **別 amendment**（閲覧済み情報・動機・新旧 semantics・資産再利用・独立検証列・新 campaign を記録；原本は保持）。(c) E1 のみは診断・別 scope として可だが 4-family global 較正の代用にならない（E1 の正式 GO も追加なし）。
C. **probe の記録**：本 probe の zip・notebook は `registered_assets/d4c1/acceptance/` 相当（probe evidence）として次 packet に収めるか，監査証拠として repo 外に保管するか，指示をお願いします（nonce は含まれていません；commitment `9efa1b8d…`・campaign `D4C2_9efa1b8d82fe` は公開可）。

## 6. 監査条件（§5 of the probe instructions）の遵守
PROBE_N＝3・FAMILY＝E2・commit／inventory は GO と同一；notebook／script 無改変（lock の script SHA＝inventory の script SHA＝`834ab646…`）；結果を見ての seed・閾値・pseudo 行の変更なし；nonce 不記載。
