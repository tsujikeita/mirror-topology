# B-2実装受入とB-3への引継ぎ — v0.3追補への追記文案

対象：Step1 engine 0.39.0（tranche35）。本書は監査側の工程整理案であり、提出された規則・module・テストを変更したものではない。

## 1. 受入れの範囲

B-2のうち、サンドボックスでの実装・契約試験・独立な小規模数値reference・合成入力での統合検査を「B-2実装受入」として完了する。第34 trancheのR34-A/Bは第35 trancheで閉鎖したものとして扱う。これは当初specに含まれたColab受入試験、ENGINE_VALID、正式全手順較正、Phase Cの凍結を完了したという記録ではない。

本工程区分を採用する場合、v0.1 §B4.2およびv0.2 §BのB-2行に残るColab・実資産検査を、下表のとおりB-3入口／B-3へ明示的に移管する。要件を削除したり、未実施をPASSへ変更したりしない。科学的な閾値・prior・乱数・推定器・分岐規則は不変である。

| 要件 | 今回の根拠 | 移管先・完了条件 |
|---|---|---|
| 数値helper・型・状態・strict JSON・固定資産のintake/reuse | サンドボックスの原本テスト・追加試験・独立reference | B-2実装受入で承認。以降のsource変更は再試験と履歴を保持 |
| v0.1 §B4.2のColab mock-grid engine smoke（E7、両系統、N=2×10^4） | 今回は未実施 | B-3-0。検証対象commit、実測環境、必要gate、出力SHA、ログを保存 |
| v0.2 T10の実bank/prefix-extension検査 | 合成入力で層別／literal同値性は確認済み。Colab実bankの当該受入は未完 | B-3-0/1。UID・prefix/extensionの再抽出を実bankで照合 |
| T19/A5 cross-checkとlegacy実資産回帰 | Claude環境の回帰PASS報告あり。監査側の外部integrationはSKIP | B-3-0/1。同一環境のlegacy比較とA5 map-based nullとの比較を区別して記録 |
| T14のE2/E8正式解像度・Colab条件 | E7の独立reference、E2の小格子等は確認済み。E2正式asset/runtimeは未完 | B-3-2。正式格子を生成・再生成照合し、座標と完全SHAを保存 |
| v0.1 §B4.3のofficial control、ENGINE_VALID | helperのpredicate/異常系試験とは別。正式profile・実環境でのcontrolは未実施 | B-3-1。negative、positive full predicate、conjunct-drop、brute-force、A5、finite inventoryの必要gate |
| 新規12位置のcircle coverage・clone・prior検査 | 設計manifestの整合性だけから物理的検査は認定しない | B-3/Phase C前。新規9点にも実施し、旧3点の件数を転記しない |

## 2. 「未実装」と「未実行」を分ける

以下は完了した実装の実行待ちではない。個別に実装・受入条件を設ける。

| 項目 | 実装・受入れの期限 |
|---|---|
| 正式12位置profileのgate | 正式12位置入力を受け入れる前。第一波profileを流用して合格扱いしない |
| pseudo側12位置の完全Resultのarchive | 正式全手順較正の成果物を受け入れる前。要約・SHAだけと完全な再現証拠を区別 |
| rules §9.4の較正先行・実観測full-grid値の封印 | 実観測full-gridを評価・解放する前。現target-first runnerは合成開発用の限定を維持 |
| production共分散の完全intake／Phase D bank生成器 | 実bankの正式作成・再利用前。geometry metadata matcherおよびlegacy回帰kernelと区別 |
| checkpointの外部W2/context参照、run/coordinatorを含む再利用契約 | その記録を正式判定へ再利用する前。現readerのcore条件付き検証を全参照の認証と呼ばない |

E2正式生成・runtime、既存legacy integrationの再実行、環境lockでの一括実行は「実装済み経路の未実行／受入未完」として別欄に記録する。

## 3. 次のnotebookの構成

B-3-0を小規模smoke、B-3-1をofficial規模control、B-3-2を正式共有nullと12位置assetの生成・検証、B-3-3をPhase C packet準備とする。段階ごとにrequired/diagnostic gateと失敗時の停止位置を定める。

現在作るcommitは「B-3検証対象を固定するcommit」である。ENGINE_VALIDやrules v1.0の科学的freezeとは区別する。実行後に修正した場合は旧source・失敗ログ・変更理由・新SHAを残し、対象となる試験を再実行する。

正式なglobal較正のdriverでは、全family、n_pseudo=2000、登録exact-W2の資産、該当する12位置profileを必須条件として確認する。現runnerのfull_procedureは分岐の実行範囲を示すflagであり、これらや封印工程の一括合格を意味しない。

1点controlを使う場合は、control用execution profileを明示する。productionの全surviving-size条件を緩めたり、1点controlの結果を全family較正として記録したりしない。小規模smokeとofficial-size controlで変える実行規模、変えてはいけない科学的定数を分ける。

## 4. inventoryと試験履歴の訂正

提出実体は41 module、62 test file、607 test function定義、815 pytest実行caseである。ファイル名別の内訳はtest_b*が23 file、test_audit*が39 file。parametrize等により関数定義数と実行case数は異なる。

提出B2_completion_inventory.jsonのmodule SHAとtest関数数は実体と一致する。ただしtestsの値は関数数であり、test file SHAではない。testsとfixture/reference資産のSHAを追加し、収集済みnodeid、環境、実行結果、SKIP理由を結び付ける。

「全原本無改変／pathのみ変更」という一括表記を避ける。原本保持、path適応、fixture再生成、API追従、比較oracle訂正を区別し、既承認の差分を残す。例えばtranche34の22件はassert不変だがfixtureがin-process生成へ変わっている。tranche29の参照先・injection hook、tranche28の高offset KDE oracleなどの既承認変更も別分類にする。

## 5. 記録用の判定案（新規の工程管理ラベルであり、既存engineのfield名ではない）

```json
{
  "B2_implementation_acceptance": "accepted",
  "B2_original_Colab_acceptance": "pending_explicit_carryover_to_B3",
  "B3_notebook_preparation": "go",
  "ENGINE_VALID": "not_evaluated",
  "Phase_C_freeze": "not_authorized_by_this_audit"
}
```

## 6. 性能表の表記訂正

今回のJSONのOT単位時間から、共有null+全observedは4.4442632866時間となる。v0.3追補の「約6.9時間」は旧値として訂正する。KDEのbatched値はopt-inの性能値であり、既定per_replicateの切替承認ではない。E2の185.77秒は部分行の測定から全passへ外挿した値である。

12位置stage・そのper_size_diagnostic、第一波case診断、Qの5-seed bootstrap、bank生成、保存・intake等は、予算へ含めた範囲と含めない範囲を明示する。現在の統合runnerはwith_diagnostics=Trueで呼ぶので、helperのwith_diagnostics=Falseの省略効果を、そのまま統合runnerの実測に算入しない。

## 出典

- Step1_PhaseB_engine_spec_v0.1.md §B4–B5
- Step1_PhaseB_engine_spec_v0.2_addendum.md §B–D
- Step1_rules_v1.0_draft4.1.md §9.2–9.4、§10.4、§12–14
- Step1_PhaseB_engine_spec_v0.3_addendum.md（提出草案）
- tranche35 report、B2_completion_inventory.json、最終提出sourceと監査側実行記録
