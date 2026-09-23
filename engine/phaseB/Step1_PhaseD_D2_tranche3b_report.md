# Phase D-2 tranche ③b v4 報告（監査 v3：RD2T3BV3-A＝同一 snapshot による要求照合と出力後照合）
2026-09-23。Claude作成。engine `step1_engine 0.78.0`（数値 kernel は 0.54.0 基盤の継承；変更は `d2_bank.py` の W₂ wrapper／intake と validator の purpose 拡張，`d/d2_bankgen.py`・`d/d2_pins.json`・notebook の追加）。③a v2 は監査で実装受入れ PASS。本 tranche は D-2 の**最後の実装 tranche**で，次は実行前監査 → commit → family 別 Colab 実行 → 実行後監査。**見込み：監査 1〜2 往復（保証ではない）。** **テスト 1269/1269 PASS**（9 chunk・JUnit 同梱 `regression_logs/d2_t3bv4_pytest/`；node 集合＝collect・重複 0・failure 0）。

| 実装 | 契約 | 試験 |
|---|---|---|
| `generate_w2_position_bank`／`intake_w2_position_bank` | purpose w2_independent（id 600），位置別 group（30000+config_id），N_W2=200,000・m=100・K=2000，両 path（f64／paired f32），matched model root のみ（複素／非 21×21 は変換前に拒否）；raw T を保存し，**whitening は intake で登録 shared null の μ/W を identity 照合のうえ適用**（近い別 W は identity で拒否）；`PositionBank` f64/f32 を返す；`formal` strict bool | `tests/test_d2_tranche3b.py`：生成・再検証・位置別 latent の相違・E1 拒否・複素 root 拒否；intake の識別（whitening identity・root・formal・bool） |
| `d/d2_bankgen.py`（family 単位 script） | preflight＝pins／inventory／script 束縛，Phase C member，**登録環境 hard gate**（rules §12.1；live），D-1 receipt／registry の固定 SHA，凍結 loader（実 path＋SHA），CRN 表／spec（committed payload SHA＋正規再導出），live registry 束縛，登録校正 bank の A10 official 照合（whitening identity の出典）。family reference（batch 0/1＋fitting）→ 配置ごとに `intake_registered_covariance`（読込み再検査）→ roots → 評価 batch 0（必須 subset は f32 併走）／batch 1・fitting・W₂（E2/E7/E8）。出力は fresh dir；`--reuse-root` の完成 dir は `verify_bank_dir` 全再検査後に再利用（改変は失敗・partial registry）；fail-fast；`d2_bank_registry.json`（directory ごとの manifest SHA・rows・formal・call inventory・環境）。D2_PASS は formal のみ；外側 receipt は監査後 | script 契約：fresh-only OUT，環境 gate で生成前停止（sandbox），self-test 完走（7 directory・call 7 件・全 dir 再検証），reuse-root の再利用と改変拒否 |
| `d/MirrorTopology_Step1_D2_bankgen_v0.1.ipynb` | D-1 launcher 型：cell 0 lock（commit・inventory SHA・FAMILY・DRIVE_DIR・REUSE_ROOT），scratch checkout と束縛，登録環境 install＋pre-check，script 実行（出力は Drive），final record（npz は Drive に残し SHA は registry／manifest で），監査用 zip | — |
| 計時・容量（sandbox 1 thread・実 kernel・scale 0.02） | 172,000 行 15.5 s ≈ 11,000 行/s → formal 外挿 **≈9 min／配置**（3 role×4×10⁶＋fitting＋W₂），**≈3 min／family reference** → 30 配置 ≈4.5 h＋α；Colab 2 thread で family 別 notebook：E2/E7/E8 各 ≈1.4 h，E1 ≈0.5 h（保証ではない）。容量 ≈288 MB／配置（f64）＋f32 subset 4 配置 → 1 family ≈2.7 GB，全体 ≈10 GB（Drive） | 実測は `regression_logs/d2_selftest_timing_sandbox_E7_30101.json` |

## v2（監査 ③b：正常経路＝W₂ 27 位置・登録 μ/W 読込み・script 通常経路・notebook 合成は確認；4 領域を修正）
| ID | 対応 |
|---|---|
| RD2T3B-A | `registered_whitening()`：登録 shared null asset を file SHA（`cc676867…`）＋payload SHA（`8348d5f4…`；`SharedNullAsset.validate`）で読み，`identity.whitening` の μ/W を独立 copy で返す。`intake_w2_position_bank` は caller の μ/W を変換前に実数 numeric・shape・有限性で検査し，**登録値との exact 一致**を要求（μ+1・2W・零 W・複素 μ／W を拒否），適用は登録 snapshot；返却 info に μ/W の配列 SHA。自作テストの正常例を登録値へ変更（任意 μ=[1,2] の例は削除） |
| RD2T3B-B | script の `reuse_or_generate` に **expected request**（family／config／kind／purpose／group／wave／batch／roles／selections／K／N／m／scale／formal／root SHA／covariance／表・spec SHA／seed／環境 fingerprint／engine）を明示し，`verify_bank_dir` 後に manifest と全 sidecar を照合（不一致は理由付きで失敗し partial registry；directory 名を認証に使わない）。必要 request 集合に対する **ledger**（new_generation／verified_reuse）から `G_all_configurations` と registry の `formal` を導出（n_done を根拠にしない）。小規模 cache を official request へ持ち込む→n_clusters 不一致で拒否；配置／purpose／batch／root／scale／生成環境の取り違え→拒否；同 request の完全 reuse→new call 0 で complete |
| RD2T3B-C | 凍結 A10 参照 NPZ の bytes を **inventory `assets_sha256` の完全 SHA** に照合してから同じ bytes を復号（不一致は数値生成前に停止；参照は不変） |
| RD2T3B-D | 再利用 directory の COMPLETE／sidecar を `OUT/audit_dependencies/<name>/` へ copy（notebook の返却 zip に含まれる）；registry に `calls`（新規生成）と `calls_reused`（再利用元の call record）・`ledger`・`required_requests` を分離記録 |

監査の 29 対照を `tests/test_audit_d2_tranche3b_review_chatgpt.py` として同梱（path と出力先の適応のみ；提出時 15/29 → **29/29**）。

## v3（監査 ③b v2：A／C 閉鎖，B／D の残件；`d/d2_bankgen.py` のみ変更）
| ID | 対応 |
|---|---|
| RD2T3B-B（残件） | **producer binding**：数値生成前に，実 module SHA map（`module_shas()`）・生成 script SHA・pins SHA・source inventory SHA・CRN 表／spec SHA・engine 版・生成 profile（profile／scale／selftest／skip flag／configs）・生成前 gate 結果を固定して digest し，`env_rec.producer` として**全 shard の sidecar** に保存。reuse では sidecar の producer と**現 producer の exact 一致**（modules／script／pins／inventory／表／spec／版）と profile 一致を要求；formal では生成前 gate 全 True も要求。同一版文字列・別 module SHA の producer（監査の別 process 対照：d2_rng の T1×1.125）を拒否；producer record のない cache は formal では拒否，self-test では ledger に注記して再利用（正式成果物へ昇格させない）。元 family の全体 PASS は要求せず，完成 unit の再利用（混合・partial 再開）は維持 |
| RD2T3B-D（残件） | reuse の依存 metadata は **検証前に捕捉した bytes**（COMPLETE と全 sidecar）を用い，`verify_bank_dir` の返値 manifest SHA・shard の sidecar SHA と照合してから，その**同じ bytes** を `audit_dependencies/` に書き出し（path から再読しない；書出し後に再照合）。検証直後に元 metadata を改変する監査対照では，変更前の検証済み snapshot が出力される（変更後 metadata を旧 identity で渡さない） |

監査の追加 22 対照（提出時 19/22 → **22/22**）を `tests/test_audit_d2_tranche3b_v2_review_chatgpt.py` として同梱（import 元の適応のみ）；前回 29 件・自作 2 件も PASS。

## v4（監査 ③b v3：前回 29＋22 対照は全 PASS；A／C 閉鎖維持；残件 1 領域を参考補強で採用）
| ID | 対応 |
|---|---|
| RD2T3BV3-A | `reuse_or_generate` で，**検証前に捕捉した同じ metadata snapshot**（COMPLETE bytes と全 sidecar bytes）を `verify_bank_dir` の返値 manifest に束縛し，**request／producer の照合もその snapshot に対して**行う（`match_request` が元 path の sidecar を再読していた箇所を除去）。出力後は COMPLETE と**全 sidecar** の書出し bytes を捕捉 SHA へ再照合し，失敗した unit は ledger に成功追加しない。監査の順序制御対照（別 source cache の検証直後に sidecar の producer を現 source へ置換／削除）は「検証済み snapshot の producer＝別 source」として拒否され，監査へ出力される metadata も検証したものと同一 |

監査の参考補強（`d/d2_bankgen.py` 1 file；候補 SHA `6ef80914…`）を精査のうえ採用。数値 kernel・生成関数・CRN 表・spec・root 式・規模・selection・判定規則は不変。監査の 18 対照（提出時 15/18 → **18/18**）を `tests/test_audit_d2_tranche3b_v3_snapshot_chatgpt.py` として同梱（import 元と probe 出力先の適応のみ）；前回 29＋22 件・自作 2 件も PASS。

計時の出所（監査 §7.2）：同梱 `regression_logs/d2_selftest_timing_sandbox_E7_30101.json` は **engine 0.74.0・旧 pins の自己試験**（D2_PASS=False・環境 gate False）の履歴であり，現 release の正式計時ではない。7 directory の生成時間合計 15.5 s／script 全体 18.0 s／172,000 行。正式計時は実行後の Colab record で置き換える。§5.2／12.5 の必須 f32 subset・near-tie・Event B mismatch・axis/plane evidence の**実測受入れは未了**（両 path の生成のみ）：生成後検証器は D-3／Phase E の前に別 tranche で提出し，それまで完了表示にしない。

未了（実行前監査後）：外側 receipt（source commit・inventory・監査 ID）の束縛，実 Drive 復元の記録，PC-1／noise／正式較正の各 gate。

先生の作業：本 packet（報告書・commit 用 zip・`d2_bank.py`・`d2_bankgen.py`・`d2_pins.json`・notebook・テスト）を ChatGPT の実行前監査へ。GO 後：commit → family 順（E1→E2→E7→E8）に Colab 実行。
