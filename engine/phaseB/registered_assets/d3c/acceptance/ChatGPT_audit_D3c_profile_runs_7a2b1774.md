# D-3c 正式profile（engine 0.99.0、E2 → E7 → E8）実行後監査
## 正式profile実行記録・plan identityを受入れ、tranche②の登録実装へGO
2026-10-03（JST）。Claudeへの引渡し・著者保存用。対象は添付結果packetの実bytesと、前回GOを付したsource ZIPである。

## 0. 判定
**PASS_WITH_EXPLICIT_SCOPE__TRANCHE2_REGISTRATION_IMPLEMENTATION_GO。** 3 familyの正式profile実行結果と、固定plan identity・復元可能性を受け入れる。今回確認した範囲で、新しい必須patch、profile再実行、既存bank再生成、受入れ済みD3b配列検証の再実行は不要である。

GOはtranche②の登録・receipt・consumer検証APIの実装と試験へ付す。登録自体はまだ完成しておらず、新APIの受入れやD-4の正式較正、閾値・label・noise・D2W・ENGINE_VALIDの承認ではない。

## 1. 受入れ実体
- 結果packet：`D3c_profile_runs_7a2b1774_audit_packet.zip`、428,182 bytes、SHA256 `775683fd20ca3d3295cca0a287c7b6b5a7fb2f142aa52072355c619c7c0008b0`。
- 実行sourceの比較基準：`phaseB_D3c_tranche1_v3_0.99.0.zip`、15,945,925 bytes、SHA256 `2f6a89b9d8145168e6d25dfa8487199ebcec6c4a51aa96328aba47f4b57fad22`。
- 記録された実行commit：`7a2b17749e88074834bf5bebe3ebd8ac8af5dd29`。
- inventory：`c0b0333b2f4250f1498c04b30090a1449d8135983264052bf602941852e580a9`。
- script：`9f243b08a5aa8ba0cc3ded42343fb8d99717dc4bd50ebf26a7cc9a519221638d`。
- 未実行notebook：`4ad3ba0ac86ff20508aa4bd32784449f5824c5fff2c19712f7c6eb464d7ff54a`。
- 前回GO判定JSON：SHA256 `ef2e7db0a381a0d6278cc6361b16e76eff37e4927beb75a89390b6f2f4bdce93`。

| family | 内側ZIP bytes | 内側ZIP SHA256 |
|---|---:|---|
| E2 | 128,233 | `4cd9a8d0f3e6f045bc8900fdd3086cab215b82ccef0a4478b029333d94d38ee4` |
| E7 | 128,230 | `4783fc1f0eac2e83410cb3262b98535bae9321d8d3759223dbcff132ead99c8e` |
| E8 | 128,226 | `49b6591d5c8d0228e6356232d69dce8d15d380c683b387dc890b1f4eb5a65a81` |

3内側ZIPはそれぞれ7実file、1 run directory／1 attemptで、退避された旧成功recordや別familyのattemptは混在しない。CRC、重複member、絶対path・親path・symlinkを検査し、family別の隔離directoryへ展開した。reportの内外bytesも一致する。これは提出物の範囲の試行数であり、未提出の履歴の不存在を立証するものではない。別の元まとめZIP `d3c_profile_results.zip` 自体は未添付のため、そのbytes同一性は主張しない。

## 2. 独立に確認した実行証拠
### 2.1 lock、source、attempt、notebook
前回GOの完全commit／inventory／script／notebook値を比較基準とした。3runともlockのsource file SHAは手元の承認済み実bytesと一致する。final内lock全文は独立lock fileと一致し、その実file SHA、attempt ID、family、profile／planのsourceとpublicationが同じrunへ結び付く。

precheck／prelaunchの両観測はHEADが指定commit、clean=True、inventory／script／inventory内script／ledger／receipt／pins／engineがlockと一致する。時刻はlock→attempt→precheck→prelaunch→終了の順に整合し、3runはE2→E7→E8の順で重ならない。記録されたHEADを当時こちらで直接観測した、又はremote Git tree全体をclone比較した、という意味ではない。

実行済みnotebookのcode cell 1〜3は承認済みnotebookと文字列完全一致。cell 0はASTから代入値を読み、指定commit・inventory・family・入力root・staging設定と、余分な実行文がないことを検査した。各notebookには4code cellの実行、同じlock／attemptの出力、出力ZIPの名前・byte数がある。

### 2.2 formal入力への束縛
当方で登録済みTwelveContext、bank spec v2、array-accepted D3bUnits、rules bindingを既存factoryから再導出した。D3bUnitsは生成ledgerだけのviewではなく、外側配列受入れreceipt付きである。

各familyの供給は36配置×matched/native＝72で、旧D2の18供給と追加D3bの54供給が揃う。3family合計216供給について、eval b0/b1・fitとreference b0/b1・ref fitのmanifestをspec v2／登録ledger／family referenceへ照合した。共分散receipt、file/array SHA、PC1_PASS／consumption_allowedとの結合も確認した。UID数、fitting cluster数、同じcontext/sourceの保持も一致する。これはNPZが今回添付されたという意味ではなく、正式intakeの実行記録を既存の登録identityへ独立照合したものである。

元Drive入力rootはD2・D3bの受入れ済みrunへ解決し、script引数とrecordは `/content/stage/d2` と3sizeのlocal stagingを消費している。引数全体を照合し、self-test引数の混入や定数の縮小はない。

### 2.3 REQUIRED gates・official gate・環境
3familyそれぞれで、REQUIREDの名前集合18項目と全True、rc=0、selftest=False、production_official、D3C_PASS=True、失敗list空、launcher_fallback=False、bindings_ok=True、plan_identity_file_ok=Trueが一致した。

official gateはmode=official、environment_source=live_collected、passed=True、required_failures空。profile checksは名前・required_modesの集合まで330件、twelve checksは同14件をsourceの定義と照合し、欠落・重複・置換なく全passed=Trueである。**これらは1032件の独立bank計算を実行したという意味ではなく、記録された検査項目の全件照合である。**

記録された環境はPython 3.13.15／NumPy 2.1.3／SciPy 1.16.3／healpy 1.20.0／CAMB 2.0.4／POT 0.9.7.post1で、pinsとofficial_gate.EXPECTED_VERSに一致する。BLASの記録に既存predicateを再適用し、NumPy OpenBLAS 2 thread、他pool 1〜2の条件も通る。当方の監査環境をこの登録環境へ置き換えたわけではない。

### 2.4 fingerprint、object共有、publication
6つのsize inputと両assembled systemについて、evaluation／fitting planのobject共有がgate前後の両方で記録されている。全3size、各12配置、family prior、twelve manifest identityは登録内容に一致する。

matched/nativeの6つのinput fingerprintは各runのgate前後で完全一致する。snapshot digestも記録されるが、元bank配列・完全snapshotは未添付であるため、当方でinput_fingerprintを配列から再計算したとの主張はしない。objectの`is`も、当時のobjectを現在直接検査したのではなく、実行された監査済みsourceと記録の整合として受け入れる。

plan documentの実SHA・bytesはprofileのpublication receiptと一致し、profileの実SHAはfinalと一致する。plan内部identity payload SHAも再計算した。stdoutはscript log全文に、log close後の `profile record published and verified; D3C_PASS = True` の1行を加えたものと厳密に一致する。この末尾行はsource通りであり、異常差分ではない。stderrは3件とも0 bytesである。

## 3. planの独立再構築（正式規模）
### 3.1 照合した内容
実plan documentのordered UIDを使い、batch 0=10,000、batch 1=30,000、B=2,000、B_KDE=2,000、K_fit=2,000、seed 0〜4、master_seed=20260912のまま再構築した。120,000個のUIDについてwave／purpose／family group／batch／rotation indexの順序を全件検査した。

1familyあたり、evaluationは5seed×2batchの10配列、fittingは5配列。3familyの**全45配列**で、dtype `<i8`、shape、multiplicity SHAが記録に一致した。全identity文書とidentity SHA、元の`verify_plan_identity`の検査も全familyで通った。

| family | identity SHA256 |
|---|---|
| E2 | `86a7db7b4aa31d172cf402785072adbd2ff2beefce964d9cf6a1cd3948c81d3e` |
| E7 | `3c28d3eb66042436ebf1788e3ed23a1f2fd593f0d305bed40299540c8f610e61` |
| E8 | `d239ad9d39da8a0d73aa32f4a65826f39a47631b1244b699ae81482e6c2bb59d` |

| family | full-scale配列SHA | 拒否対照 | 再構築・検証の監査側秒数 |
|---|---:|---:|---:|
| E2 | 15/15 | 5/5 | 37.090 |
| E7 | 15/15 | 5/5 | 37.038 |
| E8 | 15/15 | 5/5 | 34.231 |

拒否対照は、B変更、multiplicity SHA変更、seed記録削除（以上はidentityのpayloadを再sealして検査）、family取り違え、実planのUID順序逆転の5種類×3family。いずれも既存検証APIが拒否した。正常objectへ戻した後の再検証も成功している。

### 3.2 監査側の保持方式と失敗試行を区別する
最初に`fix_family_plans`を全seed一括保持で実行したE2試行はexit 137で終了した。監査containerのcgroup上限は4,294,967,296 bytes（4 GiB）、直後にoom_kill=1を確認した。**これは今回の監査側の制約であって、提出されたColab実行の失敗ではない。** 途中の90秒制限で終了した試行も完成結果には含めない。

完成した独立再構築は、承認済みsourceを変更せず、同じ`BootstrapPlan.build`／`FittingPlan.build`をseed単位に呼び、正式規模の配列を監査用local NPYへ保存してread-only memory mapで保持した。全seedが揃った状態で元の`verify_plan_identity`をそのまま呼ぶ。identityの集約式はsourceと同じで、実ordered UID全件を用いたsmall-Bの直接`fix_family_plans`との一致を別の方法対照として確認した。**small-B対照を正式規模45配列の結果に代用してはいない。** B／B_KDEやUID数は正式規模再構築では一切減らしていない。

当方の環境はPython 3.13.5／NumPy 2.3.5、Linux/glibc2.41で、正式Colab環境の再現ではない。この環境でも今回の全identityが一致したという観測であり、将来の任意の版での再現保証ではない。原本のproduction sourceや出力fileには変更を加えていない。

## 4. 資源と時間の評価
| family | attempt | staging秒 | script秒 | launcher合計秒 | final RSS GB | peak RSS GB |
|---|---|---:|---:|---:|---:|---:|
| E2 | `20261003T083353Z_dc4ddf4f0f` | 481.7 | 1125.118 | 1609.926 | 15.2536 | 19.4171 |
| E7 | `20261003T090646Z_106fe1bd17` | 487.9 | 1099.657 | 1590.449 | 15.3222 | 19.4659 |
| E8 | `20261003T093536Z_cb05343c01` | 655.5 | 489.738 | 1147.853 | 15.2850 | 19.4274 |

RAM totalは54,750,404,608 bytes＝約54.750 GB＝約50.99 GiB。今回の3runでは記録されたprocess peakは19.417〜19.466 GBで完了している。reportの「51 GB」は約51 GiBと表現するか、54.8十進GBに統一するとよい。RSSはscript processの値であり、RAM全体の全process・cache・OSの合算peakではない。将来のHigh-RAM割当てや別保持方式・別段階の十分性を保証しない。

`timings`はscript開始からの累積秒である。差分を取った値は以下。

| family | preflight | intake区間 | plans区間 | size inputs | assembly | gate到達区間 | final到達区間 |
|---|---:|---:|---:|---:|---:|---:|---:|
| E2 | 13.304 | 601.453 | 78.859 | 11.955 | 37.606 | 229.729 | 152.213 |
| E7 | 11.947 | 591.051 | 76.981 | 10.753 | 34.567 | 225.061 | 149.297 |
| E8 | 9.798 | 237.838 | 39.389 | 6.026 | 18.439 | 106.855 | 71.393 |

「gate到達区間」にはgate前のfingerprint/snapshot計算も含み、「final到達区間」にはgate後のfingerprint／identity再確認・plan publicationも含まれるため、gate関数だけの純計算時間ではない。E8が高速だった観測は確認できるが、cacheの寄与は計測から分離されておらず、plansやgate到達区間も短くなっている。cacheは仮説として記載し、単独原因として断定しない。これらは非blockingの記載整理である。

stagingのinput_bytesはfamilyごと約12.431 GB、空きdiskは約219.966 GBから195.091 GBへ変化している。差分約24.876 GBをそのまま論理input容量や実read通信量と同一視しない。記録された容量検査は全runで通る。

## 5. 検査件数と限定
- 独立照合：**3,359項目、失敗0**。このうち承認済みsource inventoryのSHA項目は2,095。pytest件数とは別である。
- 独立正式規模plan再構築：**45配列のSHA一致、3つの全identity一致、既存APIで全seed検証成功**。
- planの異常対照：15件すべて期待どおり拒否。
- 記録の異常対照：6件すべて期待どおり拒否。prelaunch HEAD、供給manifest、gate項目名、injected環境、gate後fingerprint、ordered UID入替え。必要なprofile/plan publication SHAを更新したコピーでも、単なるarchive bytes差分ではなく指定したsemantic検査が拒否することを確認した。
- 提出source **2,435fileすべて原本ZIPと不変**。追加source fileなし。fault injectionはコピーのみ。

初回の監査harnessはsourceのfield名、stdout末尾行の期待、結果file名変数の扱いを修正して全体を再実行した。これらは監査側の実装・期待値の訂正であり、提出物のFAILには数えない。初期log／途中失敗logも証拠へ保持する。著者の`claude_checks/`の結果を当方の成功件数に転記したものではない。

今回、全1,643 pytest suiteの再実行はしていない。前回の実行前受入れを維持したうえで、今回は正式runの新しい証拠とplan復元を対象とした。

## 6. tranche②へ渡す実装条件
1. **原本をそのまま登録する。** 3familyのprofile／plan／lock／final／stdout・stderr／実行済みnotebookと、原本ZIPのSHAを保存する。新しい登録engineやpinsの版になっても、0.99.0の実行recordのsource・path・環境・時刻を書き換えない。
2. **受入れとreceiptを結び付ける。** 本acceptance JSONのSHAと原本document SHAを固定し、全内容から決定的に外側receiptを再導出して新d3_pinsへ束縛する。自己申告PASSや、未信頼documentから再計算したhashだけでは受け入れない。
3. **consumerの入力identityを検査する。** E2/E7/E8、accepted attempt、両systemのfingerprint、ordered UID、B/B_KDE/seed/master/group、context/spec/ledger/array-acceptance receipt、plan identityを照合する。登録gateの独立fileを作る場合は、元profileのgateと全文一致を要求する。fingerprint要約も元profileからの導出である。
4. **正常・拒否試験を提出する。** 欠落、改変、family・attempt混在、古いlock、selftest/smoke、gateの欠落・置換、UID順序変更、plan不一致を拒否し、正式の較正consumerへ混入させない。登録APIの実装受入れは次packetで行う。

E1を新たに12位置profileへ含めるGOではない。E1と既往D2/D3a/D3b等の受入れは元の範囲を維持する。今回は新しい較正結果、labelや物理的結論を承認しない。

## 7. 再現と同梱物
`code/reproduce.py`は、指定SHAのsource ZIP・結果packet・前回GO・外側reportを新しいworkへ安全展開し、証拠照合、3familyの順次plan再構築、任意指定のmetadata異常対照を実行する。Colab notebookを実行せず、production NPZも取得しない。source ZIPは16 MBの原添付を別途与える。証拠ZIPには元結果packetと前回GO/report、実行した監査code、結果JSON、log、各原本のidentityを含める。

今回記載した構成commandはすべて完了した。portable reproducerの構文とhelpは確認したが、そのorchestratorを別の空workで最初から最後までもう一度実行したとは主張しない。

**最終判断：D-3c正式profileの3runとplan固定・復元を受入れPASS。tranche②の登録実装へGO。今回の指摘を理由とする再生成・正式profileの再実行は不要。**
