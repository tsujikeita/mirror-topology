# Step1 Phase D-3 設計 v0.2（12 位置段階；設計監査 D3-A〜D と条項案 A〜F の反映）
2026-09-24。Claude作成。v0.1 の基本方針（旧 3 点を保持して新 81 配置を事前生成し，PC-1 と正式 12 位置 profile を通して利用）は監査で支持。本版は拡張条件・W₂／f32 の範囲・PC-1 の契約・ID／profile／版間供給を，凍結 rules と既存実装の責任分界へ戻して明文化する。設計であり数値を生成しない；実装仕様の凍結と正式実行の GO は別に行う。**往復数・所要時間・容量は保証ではない。**

## A. 拡張条件と全 size mixture（rules §10.2／§10.4(vii)）
- 拡張要求は第 1 波の matched family×size で評価する：**有効な W₂ 条件 OR 精度監査後の event-ratio 条件**（零 hit の登録理由を含む）の三値 OR，**技術 FAIL 優先**。
- いずれかの surviving size で True なら，その **family の全 surviving size** を登録 12 位置へ拡張する（size を選別しない）。
- 現登録（3 size とも surviving）では family mixture の配置重みは **1/36**，size 内診断は 1/12。第 1 波の結果・重み・archive は変更せず，`twelve_eval.assemble_all_sizes` の新しい view で重みを付ける（size 別 Q／CI を平均しない）。必要な全 size が完了するまで family の最終分類を解放しない。
- v0.1 §1 の「trigger が立った family×size」という表現は撤回。

## B. 主経路の W₂ 対象と f32（著者決定）
- 登録主経路の W₂ は **D-2 の 27 位置・9 matched case**（3 位置 max-pairwise；`stage12` の明記どおり 12 位置段階に新しい W₂ trigger を定義しない）。
- **新 81 位置の W₂ bank は D-3 の主経路から外す**（生成しない；CRN 表への 81 group 追加もしない）。12 位置 66 pair の診断を将来行う場合は，目的・pair 集合・統計量・key・予算を独立の amendment として提案する（共有 null の q99 を流用しない）。
- **D-2 W₂ case 受入れ工程（D-2W）**を D-3 と別 tranche として定義：27 raw bank → 登録 μ/W → 9 case の OT 距離・stop／B_final・same-subset 感度（f64／f32 paired）・trigger の再現を，D-4 の `w2_stop`／`positions` と登録 shared null で実行し，実行前監査→Colab→実行後監査で受け入れる。
- f32：新 81 配置の evaluation／fitting は f64 primary，**新しい mandatory f32 subset は追加しない**（既登録の第 1 波 4 配置 subset を維持）。D-2 の f32 受入れを未生成位置へ一般化しない。「12 位置は f64 のみ」という包括表現は用途別に置換（evaluation／fitting：f64；W₂：主経路外）。

## C. PC-1 の契約（数値生成前に固定）
- **原典**：`A11_rules_v1.0.md`（SHA `5c6d9cd3…`）と凍結 A11 v1.4.1 notebook（SHA `791a5abb…`）の R2／R5 相当部分を D-3 tranche ①で全文照合し，式・metric・分母・基底／投影状態（実基底の D(M) か空間 3×3 の M か）・比較方向・閾値・不等号を pins に転記する。**D-1 pins の 1e-10 は同一 A11 共分散の再生成比較の許容であり，PC-1 の物理 clone 比較の許容とは別**——v0.1 の「1e-10 相当」は撤回し，転記までは値を確定しない（rules §3 の match rel<1e-5／discriminate rel>1e-2 とも混同しない）。
- **検証表（case 表）**：新 9 位置 × E2/E7/E8 × 3 size について，base 位置 r・clone 位置 g(r)=Mr+t・用いる g の identity（E8 の複数作用の扱いを含む）・base x₀=−r・clone x₀=−(Mr+t)・共分散の基底・D(M) の構成・比較方向・誤差式を，結果を見る前に固定する。base と clone の共分散は**独立に生成**し（81＋81 呼出し），D·C·Dᵀ を「clone の生成値」として自己整合を検査しない。
- **状態**：`PC1_PENDING`／`PC1_PASS`／`PC1_FAIL` は**資産層**の状態で，PENDING／FAIL の 12 位置資産は正式消費禁止。position-unresolved（位置統計の推定状態）へ変換しない；要求された 12 位置分岐の技術 FAIL は rules §9.2 の技術監査 FAIL として保持し，`derive_outcome` は TECH を返す（UNKNOWN への変換・prior 再正規化・3 位置 fallback をしない）。健全な他 unit の生成継続は実装上の分割として定め，既存 3 位置資産や他 family を一括失効させない。
- **第 1 波 anchor 診断**：新点 PC-1 とは別の case 集合・出典・呼出し数で記録（D-1 の 30 base 共分散は固定 SHA で再利用；clone 側 30 件は追加計算）。A6/A7 の symmetry anchors と件数で取り違えない。

## D. 新配置・ID・profile（実装 tranche ①で登録）
- 登録 12 位置 asset（座標・重み・生成規則・SHA）は ID 表を持たないため，**明示 mapping を登録**する：既存 family／size code を保持し，末尾 01〜03（旧 3 点，D-1／D-2 と座標・reduced_coords・x₀・cache_key が一致することを照合）を維持，新 9 点へ **04〜12** を 12 位置 manifest の position index 順に割当（例 E7/L1.00：30104〜30112；native は +50000）。111 physical ID・222 evaluation ID が全単射・非衝突・旧参照保存であることを試験で固定。
- D-3 専用の **covariance receipt／schema**（登録 12 位置 asset の座標と physical output に束縛），12 位置束縛の intake，**正式 12 位置 profile**（全 size×12 配置・prior・両系統・2 batch・fitting・5 seed plan・scope の対応を小規模試験で確認），bank spec v2 を追加する。**D-1 固定 receipt・first-wave canonical spec は削除／上書きしない**（新配置を通すために緩めない）。正式 12 位置 profile の受入れは 12 位置 bank 生成の**前**。

## E. D-2 資産の再利用（versioned reuse binding）
- family matched reference・旧 27 配置の model／native-reference／evaluation／fitting は，元 receipt／COMPLETE／sidecar／file／member SHA を保持して再利用する（再計算しない）。新 81 点の native reference は各配置の c_ct から作る。
- **D-2→D-3 binding 契約**：元 producer（0.78.0・commit・table／spec・environment fingerprint・root・UID）を保持し，D-3 で許す差（stage／weight の view）と必ず一致させる数値入力条件（root SHA・formal key・UID・prefix・selection・row 順）を明示する。`match_request` の現 producer 一致要求はそのまま（旧 cache を新 source で生成したと表示しない）；D-3 は「旧資産を固定入力として消費する」別経路として実装する。E8 の別 fingerprint も保持。
- evaluation／fitting の wave_id=1 と group／key は不変。表 v2 を作る場合も v1 の全行と payload／file identity を保存。5 seed BootstrapPlan／FittingPlan の identity と UID 順は旧／新入力で共有し，raw RNG 配列の再現確認と group 番号の一致を区別する。

## F. 検証・見積り・実行順
- 順序：D-3 metadata 受領／監査 → 外側 ledger／receipt 固定 → read-only 検証（数値検証を経ていない ledger が自身の PASS を発行する循環を作らない）。D-2 の accepted mode は first-wave scope のため，12 位置への一般化を別に実装・監査する。
- 容量（現保存形式）：新 1 配置あたり evaluation 320 MB＋fitting 16 MB → 新 81 点 **≈27.2 GB**（十進；NPZ header・JSON・roots・一時 file・RAM・backup は別計上；旧 bank 11.3 GB と併存）。
- 実装 tranche：**①** mapping／profile／PC-1 契約（原典転記）／D-2 reuse schema，**②** 共分散生成と PC-1・記録（Colab：base 81＋clone 81＋第 1 波 clone 30），**③** bank 生成と read-only 検証・consumer／plan 接続（Colab：81 配置）。正式実行の GO と実行後／科学的使用の受入れはそれぞれ別。所要時間は新生成器の小規模計時後に更新。

## G. 表現の限定
D-3 は資産の生成と検証であり，較正・判定を含まない。12 位置 bank の事前固定は全 family で 12 位置評価が行われることを意味しない。
