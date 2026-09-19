# Phase C v0.2：noise stress test の移管方針と追記案
2026-09-19。ChatGPT監査意見・Claude伝達用。**著者の採用決定を代行した完成packetではない。**

## 1. 判断

**Phase E の独立した記述的 robustness qualifier へ移す方針に賛成する。** 実施時期の移管は認められるが、仕様確定を未見の正式結果を知った後まで延期しない。core support/strong、calibration usable、registered target／prior／既存資産を、この追加診断の成績に応じて変えない。

前回の検証器・期限・PC-1の修正は確認済み。新しい数値コードや大規模計算をPhase Cへ前倒しする要求ではない。最終採用時には、下記の二段階の期限と結果の扱いを追補・manifestへ揃え、著者確認を記録する。

## 2. 今回新たに確認した原文

Libraryの `Step1_研究計画_v0.3_ChatGPT確認用.md` を新たに取得した。

- SHA256：`bac9dbfe7dfb70baa4a6ca5f1d3dc8f24c65641ebf01e3693171a4022c2abfb8`
- bytes：14,387。
- §14（原ファイルL184–189）は、**E7・L=1.0・x₀^(1)の1点**に、低ℓノイズ共分散を加えてQ_jの変化を調べる診断を規定する。候補はhalf-mission差分またはNPIPE simsで、入手可能性を確認する計画である。CI外の変化は主結論に注記する。
- 後続v0.5 L91は、CIだけによる判定を、`|Δ log Q_j| < 0.1 AND category不変 AND 変化が判定境界marginの20%未満`へ更新し、MC CI比較を併記に限定する。
- v0.5定義4とdraft4.1 §1.8／§9.1の明示的robustnessは、他の成分分離mapの比較である。noiseが自動的にこのscopeへ入っていたと断定せず、**今回の追加・明文化された移管判断**として記録する。

このファイル自体もv0.2からの差分である。今回、v0.1/v0.2を含む全旧版の要件を独立に監査し直したわけではない。v0.3のnoise関連§14、関連するrobustness／判定／未決事項を現在の提案と照合した。

## 3. 追補§2.1への差替え文案

> **noise stress testの採用scope**：研究計画v0.3 §14の1点診断とv0.5 L91の受入れ基準を保持し、実施をPhase Eの記述的robustness qualifierへ移す方針とする。監査上は下記条件付きで受入れ可能であり、著者の採用決定を記録して確定する。これはnoise試験を撤回・実施済みとする変更ではない。
>
> **原定義と対象**：基準対象はv0.3のE7・L=1.0・第1観測点である。現在のA6/A11による座標定義と第1波の不変IDへの対応を、robustness specで固定する。旧版の未確定座標や開発用mockを無条件に流用せず、正式結果が良好だった点への事後的差替えもしない。1点の検査を全family・全size・全位置の頑健性の保証とはしない。対象拡張はその目的・範囲を別に事前固定する。
>
> **仕様固定の期限**：noise入力の出典・SHA・共分散／単位／基底・正規化・水準・加算位置、targetの扱い、対象点と系統、反復・乱数・再抽出、categoryとmarginの定義、境界／未知／技術失敗の扱い、報告方法を、**未見の正式full-grid判定結果またはnoise-added結果を生成・閲覧する前**に固定し、実装の人工対照とともに監査する。既知のStep0 target・開発pilotが存在することは既存§0.2どおり開示し、「一切のデータを見ていない登録」とは呼ばない。試験結果に応じて条件を緩めない。
>
> **実施の期限**：固定済み仕様によるnoise試験の実測と結果監査は、Phase Eで、**実観測結果の公開・label解放前**に完了する。noise試験をPhase Cで実測することは要求しない。Phase Eという工程名を、結果閲覧後の仕様決定を許す理由にしない。
>
> **判定とscope**：noise-insensitiveを付けるにはv0.5の3条件をすべて要求し、MC CI比較は併記に留める。Q_jは点の診断であり、family-levelのcore labelとは区別する。category比較が点診断かfamily判定か、marginをどの量・どの境界から測るかは実施前仕様で一意にする。margin=0、Q=0/undefined、精度未達、技術失敗を自動PASSにしない。
>
> **報告**：封印済みcore結果とnoise診断を別fieldで併記する。試験の科学的FAIL、未解決、技術的FAIL、未実施を区別し、FAILでもcoreの計算記録を遡及改変せず、頑健な物理解釈を無条件には主張しない。coreが支持でもnoise-sensitiveなら、その限定を主要結果と同じ場所へ記載する。noise診断を選別・閾値調整・prior変更・較正成功化へ利用しない。追加診断の技術失敗は当該診断の失敗として保持し、core本体で起きた技術失敗をrobustnessへ付け替えて免責しない。
>
> **保証範囲**：coreのfalse-support較正は元の登録S1手順・MC資産に対するscopeを維持し、noiseを含む観測過程や歴史的実観測手順全体の保証へ拡張しない。noise込みの手順を新しいprimaryへ変える場合は、別の設計変更・較正・受入れを要する。

## 4. §7／§9との整合

§7のnoise行を二つの期限に分ける。

| 項目 | gate |
|---|---|
| noise仕様・実装の事前検証 | 未見の正式full-grid結果／noise-added結果の生成・閲覧前 |
| noise実測・結果監査 | Phase E、実観測結果の公開・label解放前 |

§9は「各機能を各使用前期限までに受入れる」とし、noise実測まで較正より前に終えることを要求する記載にはしない。coreに必要な機能の受入れ→MC資産固定→較正・監査→usable封印→実観測full-grid評価→固定仕様のrobustness試験と結果監査→一緒に公開、という順序である。noise仕様は、その未見結果を生成する段階より前に確定済みとする。

## 5. manifestのfield案（未採用・schemaの自動更新ではない）

```json
{
  "policy_status": "AUDIT_ACCEPTABLE_WITH_PRE_SPECIFICATION_GATE",
  "author_adoption_status": "AWAITING_AUTHOR_CONFIRMATION",
  "implementation_status": "NOT_IMPLEMENTED_OR_NOT_YET_ACCEPTED",
  "execution_status": "NOT_RUN",
  "scope": "descriptive_noise_robustness_qualifier_outside_core_and_calibration",
  "source_basis": [
    "Step1 research plan v0.3 section 14: one-point additive low-ell noise test",
    "Step1 research plan v0.5 line 91: effect-size/category/margin criteria"
  ],
  "specification_gate": "freeze and audit before generating or inspecting previously unseen official full-grid or noise-added outcomes",
  "execution_gate": "complete execution and result audit in Phase E before observational result/label release",
  "scope_limit": "one registered E7 point; no automatic claim for all families/positions/sizes",
  "effect_on_core": "no retroactive change to sealed core labels, calibration usable, thresholds, target, priors or accepted assets",
  "failure_reporting": "report sensitive, unresolved, technical failure and not-run separately; do not confer noise-insensitive on failure"
}
```

著者が採用したらauthor側statusのみを事実に合わせて更新する。監査意見から著者決定を推測して埋めない。noise仕様の詳細値は本提案で勝手に確定していない。

## 6. 最終整形

この案は追補・manifestへ反映するための文案であり、同梱すれば自動承認する追加規則ファイルではない。採用後の最終bytesで `PACKET_INVENTORY.json` を更新し、外側receiptのSHAでcheckerを実行する。元本文・tables・accepted engine・数値資産・過去監査書のSHAを書き戻さない。最終tag／commitは実際に作ったものを記録する。
