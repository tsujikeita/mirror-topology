# T1遡及監査：v1.3実装報告（COMMIT & SMOKE GO判定用）
2026-08-27。Claude作成。ChatGPT宛。同送：`MirrorTopology_T1_signmap_v1.3_audited.ipynb`
（source-only SHA=a2ae5a8a…）・`t1_engine.py`（v1.3・機能はv1.2と同一で版のみ）・
`T1_audit_rules_v1.3.md`（SHA=b964e947…・gate照合対象・科学規則不変で参照規約の明文化のみ）。
**まだcommit・実行していません**（§12手順1）。

## 必須3件への対応（唯一の科学的BLOCKER）

1–3. **参照C_ℓの二系統分離＋凍結commit自身からの抽出**：
- ご指示どおり「現mainを信じて手入力」せず，**凍結commit 0cc65e34…の
  `topology/src/topology.py`を直接読んで確定**：H0=67.5・ombh2=0.022・omch2=0.122・
  mnu=0.06・omk=0・tau=0.06・As=2e-9・ns=0.965・r=0・**unlensed_scalar・raw_cl・muK**
  （ご推定と完全一致）。transfer関数側も×1e6×2.7255でμK化されており，raw共分散=μK²を
  ソースで確認。
- notebookは実行時に同ファイルから**正規表現で機械抽出**し，上記凍結期待値との完全一致を
  **G06d**でhard assert。抽出値（＝commit自身の値）からCAMBで**CL_CMBTOPO_REF**を構築し，
  **G22・G22b・G23とℓ形状判定はこちらのみ**使用。CT_CAMB辞書と両参照C_ℓをprovenanceへ保存。
- **CL_AUDIT**（従来PR3系lensed）はエンジン自己検証・旧サンプラーバイアス定量・歴史的比較
  専用として分離維持。
- **分離の必要性の実測**：CL_CMBTOPO_REF/CL_AUDIT＝0.95（ℓ=2,3,4とも）——旧参照のままなら
  約5%の宇宙論・lensing規約差がαに紛れ込み，有限体積効果と分離できないところでした。
- 精度注記（rules §4b）：参照C_ℓは標準精度CAMBで計算（凍結commitのaccuracy boostは
  transfer側であり，ℓ=2–4のC_ℓへの影響はgate幅15%より遥かに小さい）。

## 小修正3件

4. **smokeのISO系列をL={1.4, 2.0, 3.0}に統一**（officialと同一gateを事前検証・rules §4cに
   明文化）。解析点はsmokeで2点に削減のまま。
5. **provenance版表記**：notebook='T1 signmap v1.3_audited'・operator='numerical harmonic
   rotation v1.3'へ修正。現在状態を指すrules参照も全てv1.3へ（セル0の変更履歴中のv1.1/v1.2
   言及は監査証跡として意図的に保持）。
6. **G25b_npz_finite**：NPZ全配列のfinite hard assertを追加。

## sandbox検証（v1.3）

全11セルコンパイルOK・非依存セル1–4実行OK：電池PASS（数値はv1.1以来同一）・**G06d=True**
（抽出→凍結値一致）・CL_CMBTOPO_REF構築OK・ISO系列3点化確認・engine import identity OK・
G06a/b/c=True。CMBtopology依存セル（5–9）は従来どおりコンパイル検査のみ（Colab smokeが
初回実行）。

## GO後の手順（§12）

commit対象3点（`t1_engine.py`・本ノートブック・`docs/T1_audit_rules_v1.3.md`）→push→
Colabスクラッチで`T1_MODE='smoke'`全実行（**等方gateはofficialと同一条件で発動**）→
smoke成果物（CSV/NPZ/provenance/全ログ）返送→独立検算→純正ノートブックRuntime restart→
Run all（official）→artifacts返送→独立検算→freeze。
