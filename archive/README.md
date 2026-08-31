# archive/ — superseded material (do not cite, do not re-run)

このディレクトリは**監査履歴の保存**のためにあります。ここに置かれたファイルは
**正式引用も再実行もしません**。正本はリポジトリ直下のノートブックと`docs/`の規則ファイル
です（`README.md` §1の表を参照）。

## originals/ — 監査前の原本

遡及監査の対象となった，外部レビューを受ける前のプログラム。何がどう誤っていたかを
第三者が検証できるように保存しています。

| ファイル | 状態 | 主な既知の問題 |
|---|---|---|
| `MirrorTopology_T1_signmap_v0.3.ipynb` | EXPLORATORY / SUPERSEDED | m=0 reality条件のサンプラーバグ（E[S⁺]を約14%過小評価）／鏡映と半回転の混同／最寄り画素反射／sign mapを主判定とする設計／v0.1一致検証のfalse PASS |
| `MirrorTopology_T2a_analytic_v0.1.ipynb` | EXPLORATORY / SUPERSEDED | 軸のHEALPix画素中心への丸め／実空間共分散の共役方向の誤り／等方基準（半回転）の理論値の誤表示／完了検査の欠如 |

ただし T2a v0.1 の閉形式 `harmonic_A`（調和空間での A=E[S⁺]−E[S⁻] の閉じた表式）は
**数学的に正しいことが独立検証され，監査版 v1.3 に継承**されています
（MATHEMATICALLY VERIFIED / RETAINED）。

## superseded/ — レビュー往復中の中間版

外部レビューの各ラウンドで作られ，最終版に置き換えられたノートブック。
どの指摘がどの版で解消されたかを追跡できるように残しています。

- `MirrorTopology_T1_signmap_v1.4_audited.ipynb`, `..._v1.5_audited.ipynb`
  → 正本は `MirrorTopology_T1_signmap_v1.6_audited.ipynb`
- `MirrorTopology_T2a_analytic_v1.1_audited.ipynb`, `..._v1.2_audited.ipynb`
  → 正本は `MirrorTopology_T2a_analytic_v1.3_audited.ipynb`
- `MirrorTopology_T2b2_signmap_v0.6.ipynb` 〜 `v0.8.ipynb`
  → 正本は `MirrorTopology_T2b2_signmap_v0.9.ipynb`

`docs/` に残る旧版の規則ファイル（`T1_audit_rules_v1.3/v1.4`,
`T2a_audit_rules_v1.1/v1.2`, `T2b2_decision_rules_frozen_v0.1/v0.2`）も同様に履歴であり，
現行の凍結規則は各段階の最新版のみです。

## なぜ削除しないのか

遡及監査の主張は「旧版に問題があり，監査版でそれが解消された」というものです。旧版を
削除すると，その主張自体が第三者に検証できなくなります。誤りを含むコードを**誤りを含むまま
保存し，正本と明確に区別する**ことが，この研究の再現性方針です。
