# Step 1 Phase A-6 / A-7 報告 v1.4.2（formal archive 仕上げ・監査 2026-09-05 #6 への対応）
2026-09-05。Claude作成。ChatGPT宛。**科学的内容は v1.4.1 から不変**（SCIENTIFIC FREEZE: GO 済み）。
成果物：`s1_phaseA6A7_v1.4.2.py`＋`a6a7_v1.4.2/`（**7 hashed outputs＋provenance＝8 files**）。16 gate すべて True・OFFICIAL。

## 監査 §13–§19 の小整理への対応

| # | 指摘 | 対応 |
|---|---|---|
| §6 | 定理文に torsion-free 仮定 | provenance の定理文を「For a non-trivial global nearest deck transformation g in a **torsion-free Bieberbach group** (so g² is not the identity), \|g²r−r\|=\|a−b\|=2d·sin(θ/2) …」に改訂 |
| §13–14 | future-source unit test が未検証の実在ソース定義に依存 | **synthetic mock source**（α 20–90°・θ=180°・両 sense）に置換し gate 名を `G_mock_backtoback_nonnearest_unit` に。Planck は operational=False・verified=False のまま provenance 情報のみ |
| §15 | file count | 「7 hashed outputs＋provenance＝8 files」と表記 |
| §16 | expected_sense | `threshold_cos10_minus/exact` に `anti_phased` を明示。no-witness 試験は空欄（適用不能） |
| §17 | 書誌 | COMPACT I：arXiv:2211.02603v4・JCAP 01 (2023) 030・DOI 10.1088/1475-7516/2023/01/030／COMPACT IIb：arXiv:2510.05030v1（誌名未確認のため保留）／Vaudrevange 2012：arXiv:1206.2939・PRD 86 083526 |
| §18 | environment metadata | Python・NumPy・pandas・platform・BLAS/LAPACK（numpy build dependencies）を provenance に記録 |

## 不変事項（v1.4.1 と同一）
第1波 50 点（L≤0.85 excluded＝純並進・anti_phased・θ=180°／L≥1.0 no_nondegenerate_circles）・s_M=0.6・
臨界試験 14・CVP 認証 200・列挙完全性 266・定理電池 103（θ_nearest 最小 61.6°）・観測者 pilot v2・
x₀ 橋渡し（A11 BLOCKER・A6/A7 の freeze とは両立）。

## freeze 手順
`A6A7_freeze/` に script・8 出力・本報告・ログ・`build_A5_freeze_manifest.py` で生成した manifest を収め，
`results/step1_phaseA/A6A7_freeze/` へ commit・タグ `step1-phaseA-A6A7-v1.0`。
