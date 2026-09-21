# Step1 Phase D-4 設計 v0.1（engine 接続：較正先行 driver・pseudo 完全 archive・登録 asset 再利用・外部参照再利用契約）
2026-09-20。Claude作成。前提：D-1 受入れ PASS（commit `aa089fa4…`，run `20260920T081931Z`；30 共分散を `registered_assets/d1/` に登録）。D-4 は sandbox 実装＋監査で，Colab 実行を含まない。各機能の受入れは「初めて使う前」の gate（Phase C 追補 §7）であり，D-4 の合格を production 機能の完成と呼ばない。

## 1. 項目と契約
| # | 機能 | 契約（要点） | 受入れ試験 |
|---|---|---|---|
| D4-1 | **較正先行 driver**（rules §9.4） | 2 段階の run：(1) `calibrate_sealed`：観測 target を**受け取らず**，target の commitment（SHA-256(target bytes ∥ nonce)）だけを記録して pseudo 較正（全 family・固定 2000 pseudo・12 位置分岐込み）を実行し，較正 record（truths・summary・usable 判定・入力 fingerprint・pseudo 列 SHA・commitment）を封印（content-addressed）；(2) `evaluate_sealed_target`：封印 record の SHA と commitment の一致（nonce と target の開示）を検査してから初めて観測 target を評価。record の順序は archive の親子参照で固定；(1) 完了前に target を評価する経路を持たない | commitment 不一致・record 欠落・順序違反の拒否；同じ入力で (1)→(2) と直接 target 評価の数値が一致（比較は試験内のみ） |
| D4-2 | **pseudo 側 12 位置完全 Result archive** | 各 pseudo の `evaluate_family_full` で 12 位置 stage が評価された場合，family ごとの完全 12 位置 Result（36 配置・CI・evidence）を content-addressed archive に保存し，per-pseudo status に参照を持たせる；要約と完全記録を区別 | 保存参照から復元した Result が再評価と strict-JSON 一致；欠落時は `full_procedure=False` |
| D4-3 | **統合 runner の登録 asset 再利用** | `run_first_wave`／`calibrate_sealed` は `twelve_assets`＋receipt id を受け，`intake_registered_twelve_assets`（file／asset SHA・source-bound registry・構造検査）で intake（再生成なし）；期待 asset SHA・whole-asset receipt・独立 snapshot・終了時 payload 再確認を維持；未登録 asset の `regenerate=False` 通過を禁止 | 生成器呼出し 0 回；改変 asset・別 registry の拒否；再生成経路との結果一致 |
| D4-4 | **外部参照の再利用契約**（checkpoint／archive reader） | archive の run manifest から source→diagnostic→parent→12 位置 Result の参照鎖を解決し，W₂ context／共有 null asset の SHA を登録資産と照合，run／coordinator record の整合（transition ⇄ source SHA・plan identity・入力 fingerprint）を検証してから再利用；検証済み scope を record に明記 | 参照鎖の 1 箇所改変で拒否；登録 null asset と異なる context の拒否 |
| D4-5 | **D-2 向け production 共分散 intake 入口** | `production.intake_registered_covariance(config_id, receipt)`：`registered_assets/d1/` の file／array SHA・sidecar（topology／params／x₀／run_config／commit／env）・grid spec との幾何 binding・PSD・principal sqrt を**読込み時に再検査**（`pass_` を信頼しない）；roots（S_M・S_N）と c_ct を返す | 改変 npy／sidecar／別配置への取り違えの拒止；D-1 registry と receipt の照合 |

## 2. 依存と順序
D4-3・D4-5 → D4-2 → D4-4 → D4-1（driver は他 4 つを使う）。各項目に ChatGPT 契約試験を受け，全 5 項目が閉じた時点で「D-4 完了 packet」（engine spec v0.3 追補への追記）とし，D-2（bank 生成器）の起草へ進む。

## 3. 表現の限定
D-4 の受入れは engine の接続契約であり，登録 bank（未生成）・実観測値・較正結果を含まない。較正先行 driver の commitment＋archive 親子参照は，**検証済み driver 内の依存順序を検査するための記録**であり，driver 外で target 計算が行われなかったことや実時間順序を hash だけで証明するものではない（既知の Step 0 target を秘匿したとも主張しない；rules §0.2）。「順序の証明」はこの限定で用いる。

## 4. tranche 1 v2（監査 RD4T1-A/B/C/D）
D4-5 の intake は，(A) 受入れ済み D-1 の **receipt file SHA と registry SHA を登録定数**として持ち，ローカル SHA 値を使う前に bytes を照合（自己整合改変は拒否）；(B) 凍結 `t1_engine`／`t2b2_bridge` を **実 path＋file SHA で使用前に検証**し，同名の既ロード module が別 file なら拒否（使用 source を返値に記録）；(C) 配置 spec は**呼出し側から受け取らず**，source-bound registry（production context）から厳密整数 id で導出し，registry entry と全項目照合。D4-3 は receipt 指定で asset なしの組合せを入口で拒否。
