# D4C-2a：screen（E2／E7／E8・全 2000 行）→ certificate の実行報告（固定 0.112.0）— 2026-10-08

監査 `D4C2_screen_certificate_0.112.0_execution_decision.json`（`GO_FIXED_0112_SCREENS_E2_E7_E8_ALL2000_THEN_AUTHENTICATED_CERTIFICATE_ONLY`；SHA `0477d7b2…`）と settings（SHA `9aff0e64…`）に従って実行した結果の報告。**実行は完了**（screen 3 件とも `D4C1_SCREEN_COMPLETE True`，certificate `D4C1_CERTIFICATE_COMPLETE True`）。科学的な受入れは監査の判断を待つ（本報告は主張しない）。

## 1. 固定 source（監査の指定どおり；変更なし）
commit `ba51e5951ebb8c16c7106247408c912d86944675`・engine 0.112.0・inventory `aa2c11cc01df09fc9cd130a2c0b9aa5af75d1b2acc27f47aef3d5d91d0bb2b77`・driver `814557791d7f…`・screen notebook `ca9c263ac5cc…`・pins `1d03bc5f83d4…`。screen の producer（Colab）と certificate の consumer（著者側）は同じ v5 packet（zip `0f52a66f5365…`）の bytes。監査ファイルと bridge 原本は tree の外に保管し，tree には手を加えていない。

## 2. screen（Colab・High-RAM 54.75 GB・Python 3.13.16；1 family ずつ順に，各 attempt 1 回で完了・失敗 attempt なし）
| family | attempt | D-2 run root | 所要（notebook 全体／script）| peak RSS | n_rows | n_blocking | W₂（登録 decision） | envelope ratio 最大 | 完全被覆 |
|---|---|---|---|---|---|---|---|---|---|
| E2 | `20261007T113430Z_d4d346bde9` | `E2_20260923T092030Z` | 1023 s／888 s（screen 546 s＝0.273 s/行） | 8.45 GB | 2000 | **2000** | L1.00 False・L1.20 unknown・L1.50 False | 1.146 | True |
| E7 | `20261007T143438Z_a2d3767433` | `E7_20260923T125656Z` | 734 s／522 s（screen 339 s＝0.169 s/行） | 8.45 GB | 2000 | **2000** | L1.00 False・L1.20 unknown・L1.50 unknown | 1.104 | True |
| E8 | `20261007T145023Z_6a25812f53` | `E8_20260923T174910Z` | 1054 s／901 s（screen 559 s＝0.279 s/行） | 8.45 GB | 2000 | **2000** | L1.00 unknown・L1.20 False・L1.50 False | 1.159 | True |

各 run：lock（commit `ba51e595…`・engine 0.112.0・inventory `aa2c11cc…`・`row_range None`・`OUT_ROOT=/content/drive/MyDrive/MirrorTopology_D4C2_screen_0_112_0`）；final record stage complete・exit_code 0・fallback False・gates／bindings／evidence ok・failures 空；run record：信頼 inventory 20 gate 全 True・`formal True`・`selftest False`・`probe False`・`instrument False`・`profile production_official`・env `python 3.13.16 / numpy 2.1.3 / scipy 1.16.3 / healpy 1.20.0 / camb 2.0.4 / pot 0.9.7.post1`；screen record：`w2_applicable True`・`complete_coverage True`（全 size・全 position で N0＝1,000,000 と N4＝4,000,000 の両 prefix）・登録 configuration id（E2 201xx／E7 301xx／E8 401xx）・min P ≥ 1.8e-4（hit 0 の位置なし）。実行済み notebook：cell 0 の値は settings と一致・execution count 1〜4・error 出力なし・出力の lock SHA と attempt id が zip の原本と一致。stderr は Colab の CUDA driver 不在のログ 4 行のみ（CPU 実行；bridge probe と同じ）。

**screen の意味**：全 2000 行・全 3 family で envelope（3 position × N0／N4 の exact hit rate の max／min）が 2.0 以下（最大 1.159）かつ全 hit > 0 で，各 family に W₂ unknown の size があり True の size がない → **登録規則の下では各行の eligible truth は unknown（技術失敗が起きれば technical_fail）**：row は blocking。screen が「False」と判定した行はない（screen は十分条件のみ；今回は全行が条件を満たした）。

## 3. certificate（consumer：著者側 sandbox，同じ 0.112.0 bytes；Colab 不要）
- 実行：`certificate/command.txt`（`--phaseb <0.112.0 tree> --mode certificate --screen <E2 run dir> --screen <E7 run dir> --screen <E8 run dir> --target-commitment 9efa1b8d… --campaign-id D4C2_9efa1b8d82fe --out <fresh>`；`--mt`／`--phasec`／`--probe-n`／`--instrument`／self-test／`--evaluated` なし）。rc 0；stderr 空。
- 消費環境（metadata として記録；gate ではない）：Python 3.11.15・numpy 2.4.4・scipy 1.17.1・healpy 1.20.0・camb 2.0.4・pot 0.9.7.post1（`env_gate.matches_registered False`：設計どおり certificate は登録計算環境を要求しない）。
- run record：REQUIRED 12 gate 全 True・`D4C1_CERTIFICATE_COMPLETE True`・`selftest False`・`formal True`・`source_scope` = formal sources only；sources：screen E2／E7／E8（各 [0, 2000)・n_blocking 2000・complete_coverage True・formal True・attempt と screen SHA／file SHA を記録）。source 認証（C1）・W₂ 要約の完全束縛（C2）・False 行の保持（D1）は v4 で受入れ済みの実装。
- certificate record（schema `calibration_infeasibility_certificate_v1`；content SHA `4a249ee06929b514bfc2f60881ab1c5073518b30c1c2e3667b26621327066557`；file SHA `0c910b32…`・2,871,232 bytes）：n＝2000（固定分母）・thresholds `{support: 0.05, strong: 0.01}`・`n_rows_admitted 2000`・`n_rows_proven 2000`。

| level | threshold | first_blocking_count | proven_blocking_rows | technical_rows | possibly_technical_rows | retained_false_rows | **usable == True impossible (Wilson)** |
|---|---|---|---|---|---|---|---|
| support | 0.05 | 81 | 2000 | 0 | 2000 | 0 | **True** |
| strong | 0.01 | 12 | 2000 | 0 | 2000 | 0 | **True** |

各 row：3 family とも `unknown_or_technical`（screen 由来）→ aggregate `unknown_or_technical`・blocking True・technical False・possibly_technical True（同一 global row は 1 回だけ計数）。

**certificate の意味（監査の解釈枠のとおり）**：固定分母 n＝2000 で，証明済み blocking 行（2000 行）だけで Wilson 上限が閾値を超えるため，**残りの行をどう補完しても usable == True は不可能**（support・strong とも）。各行の状態は「unknown，ただし評価で技術失敗が起きれば technical_fail」という条件付きであり，c／u／実測率・全件の技術成功・正式な usable == False・sealed 較正の完了・Phase E の解放を主張しない。E1 を False として除外した global 較正は行っていない。

## 4. 原本（byte 保存）
`file_map.json` に全 file と zip member の SHA／bytes。screens/：E2／E7／E8 の launcher zip（lock・final・run_<attempt>/{run record, screen record, stdout}・outer stdout／stderr）と実行済み notebook 3 本（著者の bundle `d4c1_results.zip`（SHA `270f5dfa…`）から byte のまま）。certificate/：`out_20261007T152500Z/`（run record・certificate record・stdout log）・`command.txt`・`stdout.txt`・`stderr.txt`（空）・`rc.txt`。

## 5. 依頼
(i) screen 3 件と certificate の **実行結果の受入れ**（原本一式の照合），(ii) 受入れ後，監査の指示（「同一 source の screen／certificate 完了後，履歴を保った登録 tranche で追加」）に従い，bridge probe の原本・screen／certificate の原本・各監査ファイルを repo に保管する登録 tranche（新 commit；科学的 record の書換えなし）を作る許可，(iii) この certificate の結果が Theme T（Step 1）の no-go 論旨にどう位置づくか（W₂ unknown の size が各 family にある限り global 較正は usable に到達できない，という固定分母の代数的事実）についての監査の見解。
