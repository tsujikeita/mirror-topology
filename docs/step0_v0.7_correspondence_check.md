# Step 0 v0.7：ノートブックと成果物の対応検証メモ
2026-08-31。Claude作成。検証対象は`results/step0_v0.7/`に収めた5ファイル。

## 1. なぜこの検証が必要か

Step 0はT1・T2aで用いたgit gateの導入**以前**に実行された。そのprovenance JSONは，依存
リポジトリの凍結commit・入力マップ・マスク・C_ℓのSHA256・全条件の判定結果を記録している
一方で，**ノートブック自身のハッシュを記録していない**。したがって「この成果物はこの
プログラムが生んだ」という対応は，実行時に暗号学的に固定されていない。

本メモは，その対応を**事後の内容照合**によって確立した記録である。T1・T2aのように
実行時ハッシュで保証されたものではないことを明示しておく。

## 2. 検証対象ファイル

| ファイル | SHA256 |
|---|---|
| `MirrorTopology_Step0_official_v0.7.ipynb` | source-only `860eceb2e0d92aea73dd65ab61564a6c7398322b9985933a9eff192926bc1773` |
| `step0_official_v0_7.csv` | `6ed885d10a6455995b342152e71cd14f79c87b84ff6fb9539b3ebd4f61e551cb` |
| `step0_gateA_permap_v0_7.csv` | `47c2642c5a9c9702914501a4aa61a91b94ec16afe77d6c83c645cad547df4a1f` |
| `step0_null_arrays_v0_7.npz` | `adc8c70869f66a1445c109c7b17e94c76ae7a11a0d17371d91b40ee119b16a62` |
| `step0_provenance_v0_7.json` | `26aec3c9ad4c62229061b8c457931536254eaabb090c6c110531e563ab0c6d04` |

（source-only SHAは`t2b2_run.source_only_sha`と同一定義：コードセルの内容のみを
canonical form——CR除去・行末空白除去・末尾空行除去——でハッシュしたもの。実行出力や
編集環境の整形に対して不変。）

## 3. 照合1：凍結commitの一致

provenanceが記録する3つの依存commitが，ノートブックのソースに**40桁フルで**出現する。

| provenanceのキー | 値 | ノートブック内に出現 |
|---|---|---|
| `commit_step0` | `d36e7567e8a7869c…` | ✔ |
| `commit_predreg` | `63aa853f176837a6…` | ✔ |
| `cmbanom_commit` | `aaf8137427d54ce4…` | ✔ |

## 4. 照合2：出力ファイル名の一致

4つの成果物ファイル名がすべて，ノートブックの保存セル（cell 8）のコードに現れる：
`step0_official_v0_7.csv`・`step0_gateA_permap_v0_7.csv`・`step0_null_arrays_v0_7.npz`・
`step0_provenance_v0_7.json`。

## 5. 照合3（決定的）：provenance全キーの生成箇所

provenance JSONの**20キーすべて**が，同じ保存セルのコードで生成されている：

```
notebook, timestamp, versions, commit_step0, commit_predreg, commit_note, cmbanom_commit,
src_sha256, map_sha256, mask_source_sha256, processed_mask_sha256, cl_file_sha256,
axis, config, fsky, null, frozen_stat_calls, conds, official, p_label
```

未対応キーは**ゼロ**。該当コードは

```python
CONDS = dict(commit_exact=..., clean_tree=CLEAN, src_sha_match=..., frozen_stat_used=...,
             mask_source_sha=MASK_OK, cl_file_sha=CL_OK, input_maps_sha=...,
             gateA_permap=GATEA, gateB_null_median=GATEB)
OFFICIAL = all(CONDS.values())
prov = dict(notebook='Step0 v0.7 official', timestamp=..., versions=VER, commit_step0=COMMIT, ...)
```

`axis`・`fsky`・`frozen_stat_calls`・`p_label`のような特徴的なキーの組が偶然一致することは
考えにくく，これをもって対応が確立したと判断する。

## 6. 照合4：内容の整合

`step0_official_v0_7.csv`は10マップ×17列。PR3_Commander行は
S⁺/null中央値 = 0.101375・S⁻/null中央値 = 0.927913・ρ = −0.734645 で，凍結記録の値
（S⁺/med ∈ [0.090, 0.111]・S⁻/med ∈ [0.928, 1.012]・ρ_obs ∈ [−0.779, −0.722]）の範囲に入る。
`step0_gateA_permap_v0_7.csv`は50行（10マップ×5帯）でPASS列を持ち，
`step0_null_arrays_v0_7.npz`は帯別のSp/Sm各1000実現を格納。ノートブックのGate A・Gate B
セルの設計と一致する。

またprovenanceの自己申告は`"notebook": "Step0 v0.7 official"`，タイムスタンプは
`2026-08-25 13:12:52`。ノートブック冒頭の表題は「Step 0 公式実行ノートブック v0.7
（正式完了用）」。

## 7. 結論と限界

**結論**：`MirrorTopology_Step0_official_v0.7.ipynb`が4つのStep 0成果物を生成した
プログラムであると判断する。

**限界**：この対応は実行時に固定されたものではなく，事後の内容照合による。ノートブックが
実行後に編集されていた場合，本検証はそれを検出できない（provenanceにノートブックの
ハッシュがないため）。ただし成果物とノートブックを同一ディレクトリに置いたので，第三者は
同じ照合を独立に再現できる。

**遡って修正しない理由**：Step 0を今のgate体系で再実行すれば実行時ハッシュを得られるが，
それは「凍結済みの観測値を作り直す」ことになり，事前登録の原則に反する。凍結値はそのまま
とし，本メモで対応の根拠と限界を明示する方針を採る。

## 8. 第三者による再検証手順

```bash
git clone https://github.com/tsujikeita/mirror-topology.git
cd mirror-topology/results/step0_v0.7
sha256sum step0_*.csv step0_*.npz step0_*.json        # §2の表と照合
python - <<'EOF'
import json
nb = json.load(open('MirrorTopology_Step0_official_v0.7.ipynb'))
src = '\n'.join(''.join(c['source']) for c in nb['cells'])
prov = json.load(open('step0_provenance_v0_7.json'))
print('commits:', all(prov[k] in src for k in
                      ['commit_step0','commit_predreg','cmbanom_commit']))
save = ''.join(nb['cells'][8]['source'])
print('all provenance keys generated:', all(f"{k}=" in save or f"'{k}'" in save for k in prov))
EOF
```
