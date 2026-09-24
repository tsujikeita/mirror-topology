# Step1 Phase D-2 — 外側 receipt（第 1 波 bank 資産：生成・登録・read-only 検証の受入れ範囲）
2026-09-24。Claude作成（著者側記録；外部受入れは参照の監査書）。

| 項目 | 値 |
|---|---|
| 生成 source | commit `8b5e6102…`（engine 0.78.0，inventory `3523d233…`）；実行前 GO `ChatGPT_D2_preexecution_GO_8b5e6102f008.md` |
| 生成 run | E1 `20260923T063210Z`／E2 `092030Z`／E7 `125656Z`／E8 `174910Z`；30 配置・129 unit・197 NPZ・11.3 GB・8.58 h；各 family の metadata 受入れ JSON |
| ledger | commit `19106ef…`（0.79.0，inventory `2243c1df…`）；`registered_assets/d2/d2_generation_ledger.json`（SHA `07574dfa…`） |
| 検証器 | commit `dfe98c5f…`（0.81.0，inventory `cac41514…`）；script `d3a348c6…`・notebook `338c6f9b…`；実装受入れ `ChatGPT_audit_Step1_PhaseD_D2_readonly_verifier_v0.3.md` |
| read-only 検証（Colab） | 4 family とも `accepted_full`・`all_ok`・`coverage_complete`・binding True；129 unit・197 NPZ の file SHA が固定 ledger と一致，member／dtype／有限性／cid 検証；43 paired path・2,140 万行で **near-tie 違反 0・Event B mismatch 0**（相対差最大 9.0e-7；flip 183,698 件のうち antipodal 183,619）；監査は全 flip evidence を独立再計算し幾何を HEALPix 中心座標で検算（cos 差 5.7e-16） |
| 外部受入れ | `ChatGPT_audit_Step1_PhaseD_D2_readonly_Colab_dfe98c5f37c6.md`（SHA `bea4dc07fe509115…`）：**PASS_WITH_EXPLICIT_SCOPE** |
| 受入れ範囲 | 4 family の完全 coverage の integrity 検証 run，固定 ledger⇄NPZ file hash の対応，Colab での member／dtype／有限性／cid 検証結果，全 flip evidence，保存 paired path に対する登録 near-tie／Event B 規則 |
| 承認しないもの | 197 NPZ の監査環境での独立 rehash／統計再計算，生成時 model root の数値比較，全 near-minimizer 集合の再構築，raw W₂ → case OT／stop／B_final／trigger と外部 context の正式再利用，shared-null pool の新規検証，正式 BankSupply／BootstrapPlan／FittingPlan 束縛と全用途の bank 資産承認，D-3・PC-1，noise，正式較正・usable，実観測 label・support/strong・ENGINE_VALID；f32 を primary にすることの許可，他の閾値／将来の抽出／他 hardware への一般化 |
| 保管 | bank NPZ は Drive の 4 run root（削除しない）；検証 zip 4 本（SHA は receipt JSON）と実行済み notebook は著者保管 |
