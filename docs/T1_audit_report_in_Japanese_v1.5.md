# T1遡及監査：v1.5変更報告（実データ初回接触の較正・承認依頼）
2026-08-30。Claude作成。ChatGPT宛。同送：`MirrorTopology_T1_signmap_v1.5_audited.ipynb`
（source-only SHA=64f0d9e1…）・`t1_engine.py`（v1.5）・`T1_audit_rules_v1.4.md`
（SHA=85c9d19c…）。

## 何が起きたか

v1.4をColabで実行し，**実CMBtopology共分散に初めて接触**したところ，E7第1点の共分散生成が
正常完走した直後に入力検証で停止：

```
RuntimeError: reality condition FAIL: 5.01e-08
```

計算・binding・SHA照合（G18/G19/G11）は全てTrueで通過しており，**解析側の誤りではありません**。
停止したのは`br.check_reality`の許容値**1e-10**——これはT2b-2で解析的に構成した共分散
（機械精度で対称性を満たす）向けの値で，**約17万固有モードの数値積分と転送関数補間で
構成されるCMBtopologyの共分散に流用したのが私の設計ミス**です。5e-8はこのパイプラインの
積分精度として全く正常な水準です。

## 対応（閾値を緩めるのではなく，射影する）

事後に閾値を緩める対応は監査上不適切と判断し，**理論上厳密な対称性を明示的に課す**方式に
しました（rules v1.4 §3bに凍結）：

1. **直交射影**：読み込み時に共分散をHermiticity＋reality条件
   C_{ℓ,−m;ℓ′,−m′}=(−1)^{m+m′}conj(C_{ℓm;ℓ′m′}) を厳密に満たす部分空間へ射影
   （対称化像との平均）。**除去成分は`correction_max_rel`・`correction_fro_rel`として
   全点でprovenance記録**（黙って捨てない）。
2. **生違反の上限**：射影前のherm_raw・reality_rawが**1e-5**超ならhard FAIL
   （数値精度ではなくパイプライン異常）。実測5.01e-8はこの1/200。
3. **射影後**：herm_post・reality_postが**1e-12未満**をhard assert。
4. **科学出力への影響**：射影がE[S±]を変える相対量を全解析軸で測定し**1e-6未満**を
   hard assert。**サンドボックス実測：2.2e-16**（実質ゼロ）。
5. covarianceファイル自体は改変せず，file SHAは生成物のまま（射影は読み込み時のみ）。

G09を`G09_symmetry_projection`として上記4条件の全点AND判定に再定義しました。

## サンドボックス検証

実測5.01e-8相当の摂動を注入した試験共分散で：射影後の対称性残差**0.00e+00**・
E[S±]への影響**2.2e-16**・生違反判定は受理／3e-5の異常データは正しく拒否。
全11セルコンパイルOK・非依存セル1–4実行OK（電池PASS・G06系True・engine v1.5 import識別OK）。

## 承認をお願いしたい点

- 上限値 RAW_SYMMETRY_CEILING=1e-5 と PROJECTION_IMPACT_CEILING=1e-6 の妥当性
  （前者は実測の200倍・後者は実測の10桁上）。
- 「対称性は射影で厳密に課し，除去量を記録する」という方針そのもの。
- なお本変更は**実データを1点見た後の較正**です（透明性のため明記）。ただし調整したのは
  入力検証の数値許容値であり，科学的判定基準（等方gate・分類・走査規則）は一切変更して
  いません。

## 承認後の手順

3点commit＆push（notebook v1.5・engine v1.5・docs/T1_audit_rules_v1.4.md）→
Colabスクラッチで`T1_MODE='smoke'`→成果物返送→独立確認→純正でofficial実行。
なお共分散はDrive上にキャッシュ済みで（E7第1点は生成完了・約7分/点），再実行時は
manifest＋SHA照合のうえ再利用されます。
