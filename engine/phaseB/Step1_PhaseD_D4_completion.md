# Phase D-4 完了／引渡し記録（v2）
2026-09-22。Claude作成。v1 に対する ChatGPT 監査（`ChatGPT_audit_Step1_PhaseD_D4completion_D2design_v0.1.md` §2）の文言訂正案を著者判断で採用した版。新しい実行 receipt ではない。

## 1. 完了の意味
D4 tranche 1 v3・tranche 2 v6は、各監査に記載した人工bank・試験用W₂ context・外部source対照の範囲で、実装・接続の受入れを完了した。engine 0.66.0。第1波D-1共分散、Phase C、および既存B各段階の受入れを維持する。

受入れ対象source inventory SHA256：
`c47103e82d1307a34a4106d367fd0780c9321dbae260160bc346d09d0eab30e4`

v6監査書：`ChatGPT_audit_Step1_PhaseD_D4_tranche2_v6.md`
SHA256：`ba0685739d79d99a5364c89ba98e233472bc75ac7dc73dd75ec8d50858381d22`

受入れ済み基盤sourceのhandoff commitは`1db30cd1678d40340cd445204ec97a08590c24d5`（0.54.0）である。0.66.0全体のbytesが0.54.0と同一という意味ではない。数値kernelの継承と、追加・改訂したrunner／reader等の受入れ履歴を分ける。

## 2. 受入れた機能
| 項目 | 受入れ範囲 |
|---|---|
| D4-3 | 登録receiptに束縛してintakeした12位置assetを、再生成せずrunnerで利用する接続。人工bankでgenerator呼出し0回を確認。 |
| D4-5 | 固定D-1 receipt／registry SHA、source-bound spec、loader／bridgeの実path・SHA・実依存、sidecar、幾何、array SHA、PSD、principal rootの検査を持つ共分散受付API。実D-1配列の正常数学経路と、試験用外部sourceによる正常・異常対照を確認。本物の凍結loader全体の監査環境での独立実行とは区別する。 |
| D4-2 | 各pseudoについて、計算済みparent・plan・position source、および必要manifestと、実行した12位置完全Resultをcontent-addressedに保存する接続。 |
| D4-4 | run payload・stage・binding・登録metadataの復元、完全Resultの数値検証、positionとparentの数値対応、状態・完了・eligibility・較正再集計、親sealとの対応を検証。W₂については保存された宣言SHA・trigger等と親子recordの対応を確認する範囲であり、外部W₂実object／resolverの完全な正式再利用受入れや全距離再計算を含めない。 |
| D4-1 | commitment→pseudoのみの較正・封印→開示・targetのみの評価という二段階の接続。officialの全family・固定2000 pseudo・mode・target-first禁止を境界試験で確認。正式規模での実測完了とは区別する。 |

## 3. 受入れの限定
上記はsandboxの人工bank・試験用W₂ context・試験用loader／bridgeによる接続契約、および実D-1配列の代数的変換・根の計算の対照による実装受入れである。本物の凍結外部loaderを要する3件は監査側でSKIPであり、試験用sourceの成功を実loaderの成功へ置き換えない。著者JUnitの全992件の集合照合と、監査側で選択実行した試験を区別する。

正式D-2生成、実bankのcase別W₂、外部W₂／contextの正式再利用受入れ、PC-1物理clone、noise、全family・固定2000 pseudoの正式較正、calibration usable、実観測label、ENGINE_VALIDは含まない。各使用前gateは維持する。commitmentはdriver内の依存順序の記録であり、driver外でtargetを計算していないことの証明ではない。

## 4. 試験の出所
自作`test_position_source_numbers_must_match_verified_parent`はP/hits・swap・N/hits・precisionの4種類。stage変更と未完branchのunknown減少は、監査が再実行した前回原本16件に含まれ、0.66.0で拒否された。「自作4種類＋監査原本でstage／分岐を確認」と記す。

## 5. 監査履歴
tranche 2：v1 HOLD → v2 HOLD → v3 HOLD → v4 HOLD → v5 HOLD → v6 実装・接続受入れPASS。過去のHOLD記録や参考修正の不足を遡及的に書き換えない。

## 6. 次工程
D-2設計監査 → RNG／供給契約確定 → 実装・小規模試験 → 実行前監査 → commit → 分割したColab実行・実行後監査。所要時間・保存容量はD-2のrole／dtype／再開単位と小規模計時に基づいて確定する。本記録で8〜10時間などを保証しない。
