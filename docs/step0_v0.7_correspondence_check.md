# Step 0 v0.7：ノートブックと成果物の**事後的**対応検証メモ（v1.3）
2026-08-31。Claude作成。ChatGPTレビュー3回（wording refinement／filename-check fix／
source-only SHA定義の明確化）を反映。検証対象は`results/step0_v0.7/`に収めた5ファイル。

**この文書が主張すること／しないこと**：本メモは *retrospective attribution*（事後的な帰属）
の記録であり，暗号学的証明ではない。

| 判定対象 | 本検証で言えること |
|---|---|
| ノートブックとprovenanceの構造的対応 | **非常に強く支持される** |
| ノートブックと4成果物の事後的な対応付け | **高い蓋然性で支持される** |
| 2026-08-25の実行時にこのソースが走ったこと | **証明できない** |
| T1・T2aのような実行時の暗号学的binding | **存在しない** |

## 1. なぜこの検証が必要か

Step 0はT1・T2aで用いたgit gateの導入**以前**に実行された。そのprovenance JSONは，依存
リポジトリの凍結commit・入力マップ・マスク・C_ℓのSHA256・全条件の判定結果を記録している
一方で，**ノートブック自身のハッシュを記録していない**。したがって「この成果物はこの
プログラムが生んだ」という対応は，実行時に固定されていない。本メモはその対応を事後の
内容照合によって帰属した記録である。

## 2. 検証対象ファイル

| ファイル | SHA256 |
|---|---|
| `MirrorTopology_Step0_official_v0.7.ipynb` | source-only `860eceb2e0d92aea73dd65ab61564a6c7398322b9985933a9eff192926bc1773` |
| `step0_official_v0_7.csv` | `6ed885d10a6455995b342152e71cd14f79c87b84ff6fb9539b3ebd4f61e551cb` |
| `step0_gateA_permap_v0_7.csv` | `47c2642c5a9c9702914501a4aa61a91b94ec16afe77d6c83c645cad547df4a1f` |
| `step0_null_arrays_v0_7.npz` | `adc8c70869f66a1445c109c7b17e94c76ae7a11a0d17371d91b40ee119b16a62` |
| `step0_provenance_v0_7.json` | `26aec3c9ad4c62229061b8c457931536254eaabb090c6c110531e563ab0c6d04` |

**source-only SHAの定義**（`t2b2_run.source_only_sha`と同一）：notebookの**全セル**について
`cell_type`と`source`のみを取り出し，sourceをcanonical form——CRLF/CR→LF・各行末空白除去・
末尾空行除去——に正規化したうえで`json.dumps(..., sort_keys=True, ensure_ascii=False)`で
JSON化し，そのSHA256を計算したもの。**outputs・execution_count・セルmetadata・notebook
metadataは含まない**。markdownセルも対象に含まれるため，これは「コードのみのハッシュ」では
なく「実行出力等を除いたnotebookソース全体のハッシュ」である（アーカイブ用途では
その方が強い）。

**このsource-only SHAの位置づけ**：これは2026-08-25の実行時ソースを証明するものではなく，
**2026-08-31の事後監査で対応付けたノートブックを以後固定するため**のハッシュである。

## 3. 照合1：凍結commitの一致（補助証拠）

provenanceが記録する3つの依存commitが，ノートブックのソースに**40桁フルで**出現する。

| provenanceのキー | 値 | ノートブック内に出現 |
|---|---|---|
| `commit_step0` | `d36e7567e8a7869c…` | ✔ |
| `commit_predreg` | `63aa853f176837a6…` | ✔ |
| `cmbanom_commit` | `aaf8137427d54ce4…` | ✔ |

同じpipeline configurationを意図したノートブックであることを強く支持するが，実行時の
ノートブック同一性の証明ではない。

## 4. 照合2：成果物の保存処理の一致（補助証拠）

4成果物の保存処理は**複数のコードセルに分かれて**存在する。

| 成果物 | 保存箇所 | コード上の形 |
|---|---|---|
| `step0_gateA_permap_v0_7.csv` | cell 4 | リテラル：`gate.to_csv(os.path.join(OUT,'step0_gateA_permap_v0_7.csv'), …)` |
| `step0_null_arrays_v0_7.npz` | cell 6 | リテラル：`np.savez(os.path.join(OUT,'step0_null_arrays_v0_7.npz'), …)` |
| `step0_official_v0_7.csv` | cell 8 | f-string：`f'step0_official_v0_7{tag}.csv'` |
| `step0_provenance_v0_7.json` | cell 8 | f-string：`f'step0_provenance_v0_7{tag}.json'` |

後者2つは`tag = '' if OFFICIAL else '_SANITY_ONLY'`で構成され，official実行時は`tag=''`と
なるため，それぞれ`step0_official_v0_7.csv`・`step0_provenance_v0_7.json`に解決される。
**したがって最後の2つは，リテラルの完全なファイル名としてはソース中に存在しない。**
（v1.1では誤って「4つとも cell 8 にリテラルで現れる」と記述していた。§10の検証コードも
それに合わせて修正した。）

これらは単独では補助証拠だが，他の構造的・数値的証拠と組み合わせると対応判断を補強する。
なお，成果物ファイル名に`_SANITY_ONLY`が付いていないことは，保存時に`OFFICIAL`が真で
あったことと整合する。

## 5. 照合3（中心的な対応証拠）：provenance schema 20キーの完全一致

provenance JSONのトップレベル20キーと，保存セルで`prov`に代入されるキー集合を
**AST（構文木）で抽出して集合比較**した結果，**両者は完全一致**した（コードのみ・JSONのみ
ともに空集合）。文字列検索ではなく構文解析による比較なので，コメントや別変数への偶然の
出現では成立しない。

```
axis, cl_file_sha256, cmbanom_commit, commit_note, commit_predreg, commit_step0, conds,
config, frozen_stat_calls, fsky, map_sha256, mask_source_sha256, notebook, null, official,
p_label, processed_mask_sha256, src_sha256, timestamp, versions
```

該当コードは

```python
CONDS = dict(commit_exact=..., clean_tree=CLEAN, src_sha_match=..., frozen_stat_used=...,
             mask_source_sha=MASK_OK, cl_file_sha=CL_OK, input_maps_sha=...,
             gateA_permap=GATEA, gateB_null_median=GATEB)
OFFICIAL = all(CONDS.values())
prov = dict(notebook='Step0 v0.7 official', timestamp=..., versions=VER, commit_step0=COMMIT, ...)
```

`axis`・`fsky`・`frozen_stat_calls`・`p_label`・`commit_note`などの特徴的なキーの組まで完全に
一致していることは，**当該ノートブックとprovenanceが同一の実装系列に属することを強く支持
する**。ただしこれ単独では，実行時のソース同一性を示すものではない。

## 6. 照合4：成果物の構造と数値内容の一致（補助証拠）

`step0_official_v0_7.csv`は10マップ×17列。PR3_Commander行は
S⁺/null中央値 = 0.101375・S⁻/null中央値 = 0.927913・ρ = −0.734645 で，凍結記録の範囲
（S⁺/med ∈ [0.090, 0.111]・S⁻/med ∈ [0.928, 1.012]・ρ_obs ∈ [−0.779, −0.722]）に入る。
`step0_gateA_permap_v0_7.csv`は50行（10マップ×5帯）でPASS列を持ち，
`step0_null_arrays_v0_7.npz`は帯別のSp/Sm各1000実現を格納。ノートブックのGate A・Gate B
セルの設計と一致する。provenanceの自己申告は`"notebook": "Step0 v0.7 official"`，
タイムスタンプは`2026-08-25 13:12:52`。ノートブック冒頭の表題は「Step 0 公式実行ノートブック
v0.7（正式完了用）」。

## 7. 結論

本対応判断は，provenance schema 20キーの完全一致のみを根拠とするものではない。**凍結commit・
出力ファイル名・特徴的なprovenance schema・成果物の形状と数値内容・ノートブックの自己申告名の
一致という複数の独立な整合証拠を総合した retrospective attribution** である。

これらに基づき，`MirrorTopology_Step0_official_v0.7.ipynb`が4つのStep 0成果物を生成した
プログラムであったと**高い蓋然性で判断する**。

## 8. 限界

本対応は実行時に暗号学的に固定されたものではなく，保存後のノートブックと成果物に対する
事後的な内容照合によるものである。したがって，現在保存されているノートブックが実行時の
ソースと byte-for-byte または source-only hash レベルで同一であったことは**証明できない**。
特に，今回照合したcommit値・出力名・provenance schema・数値内容等を保つような実行後編集の
可能性は排除できない。

一方，本メモに記録したSHA256により，**本事後照合の時点（2026-08-31）以降**の保存ファイルの
同一性は検証可能であり，第三者は§10の手順で同じ retrospective consistency checks を独立に
再現できる。固定参照点として，本メモを含むcommitに注釈付きタグ`step0-v0.7-correspondence-v1.3`を作成し
リモートへpushする（**タグが実際に作成・pushされて初めて固定参照点として成立する**）。

## 9. 遡って修正しない理由

現在のgate体系でStep 0を再実行すれば，**その新しいrunについては**ノートブックのハッシュを
含む強いprovenanceを作成できる。しかしそれによって，既存のStep 0成果物と2026-08-25の実行時
ソースとの対応を遡及的に暗号学的に証明できるわけではない。また，凍結済み成果物を新runの
成果物で置換することは避けるべきであり，historical provenanceを後付けで作り直すことも
すべきでない。したがって既存成果物は変更せず，本メモによる retrospective attribution と
その限界を明示する方針を採る。

（検証目的の再実行それ自体は問題ではない。将来 *retrospective reproduction* として別runを
行う場合は，成果物を別ディレクトリに置き，凍結runとは明確に区別すること。）

## 10. 第三者による再検証手順

```bash
git clone https://github.com/tsujikeita/mirror-topology.git
cd mirror-topology
git checkout step0-v0.7-correspondence-v1.3      # 事後監査時点の固定参照
cd results/step0_v0.7
sha256sum step0_*.csv step0_*.npz step0_*.json   # §2の表と照合
python - <<'EOF'
import ast, json, hashlib

NB = 'MirrorTopology_Step0_official_v0.7.ipynb'
nb = json.load(open(NB))
prov = json.load(open('step0_provenance_v0_7.json'))
code_src = '\n'.join(''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code')
save = ''.join(nb['cells'][8]['source'])

# 照合1：凍結commitがソースに完全一致で現れるか
print('commits:', all(prov[k] in code_src for k in
                      ['commit_step0', 'commit_predreg', 'cmbanom_commit']))

# 照合2：保存処理（リテラル2件＋f-stringテンプレート2件＋officialタグ）
checks = {
    'gateA_csv':          'step0_gateA_permap_v0_7.csv' in code_src,
    'null_npz':           'step0_null_arrays_v0_7.npz' in code_src,
    'main_csv_template':  'step0_official_v0_7{tag}.csv' in code_src,
    'prov_template':      'step0_provenance_v0_7{tag}.json' in code_src,
    'official_tag_empty': "tag = '' if OFFICIAL else '_SANITY_ONLY'" in code_src,
}
print('artifact save paths consistent:', all(checks.values()), checks)

# 照合3：provのキー集合をASTで抽出し，JSONのキー集合と厳密比較
code_keys = set()
for node in ast.walk(ast.parse(save)):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == 'prov':
                v = node.value
                if isinstance(v, ast.Call):
                    code_keys |= {kw.arg for kw in v.keywords if kw.arg}
                elif isinstance(v, ast.Dict):
                    code_keys |= {k.value for k in v.keys if isinstance(k, ast.Constant)}
            if (isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name)
                    and t.value.id == 'prov' and isinstance(t.slice, ast.Constant)):
                code_keys.add(t.slice.value)
print('provenance key sets identical:', code_keys == set(prov.keys()),
      '| n =', len(code_keys))

# 照合4：notebookのsource-only SHAが§2の記録値と一致するか
def canon(src):
    text = ''.join(src) if not isinstance(src, str) else src
    lines = [l.rstrip() for l in text.replace('\r\n', '\n').replace('\r', '\n').split('\n')]
    while lines and lines[-1] == '':
        lines.pop()
    return '\n'.join(lines)
canon_cells = [dict(cell_type=c['cell_type'], source=canon(c['source'])) for c in nb['cells']]
sha = hashlib.sha256(json.dumps(canon_cells, sort_keys=True,
                                ensure_ascii=False).encode()).hexdigest()
print('notebook source-only SHA matches §2:',
      sha == '860eceb2e0d92aea73dd65ab61564a6c7398322b9985933a9eff192926bc1773')
EOF
```

期待される出力（監査時に実測確認済み）：

```
commits: True
artifact save paths consistent: True {...すべてTrue...}
provenance key sets identical: True | n = 20
notebook source-only SHA matches §2: True
```

**照合4が証明すること**：第三者がcheckoutしたノートブックが，2026-08-31の事後監査で
対応付けたノートブックと**同一ソースである**こと。2026-08-25の実行時ソースそのもので
あったことではない（§8）。

## 11. 適用範囲

本メモが扱うのは *which notebook produced these artifacts?* というprovenance attribution
のみである。Step 0の科学的妥当性——CSV内部整合性・旧S⁺の再現・null実現ごとの一致・
S⁻/A/ρの計算——は別途の監査で確認済みであり，**notebook-artifact bindingがT1・T2aほど
強くないことは，Step 0の科学計算自体に問題があることを意味しない。**
