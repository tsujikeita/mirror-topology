# mirror-topology

Audited, reproducible analysis code for a study of mirror (reflection) symmetry statistics in
the CMB and their relation to compact-flat topologies (Theme T).

Every analysis in this repository has passed an independent pre-run audit and an independent
post-run recomputation of its outputs. Each frozen stage is identified by a **git tag** and a
**provenance JSON** that records the exact commit, file hashes, dependency versions and the
result of every hard gate.

---

## 1. Frozen stages

| Stage | Canonical notebook | Rules | Tag | Status |
|---|---|---|---|---|
| **T1** — low-ℓ predictive engine validation | `MirrorTopology_T1_signmap_v1.6_audited.ipynb` | `docs/T1_audit_rules_v1.5.md` | `t1-audit-v1.0` | **FROZEN** |
| **T2a** — harmonic closed form & multipole decomposition | `MirrorTopology_T2a_analytic_v1.3_audited.ipynb` | `docs/T2a_audit_rules_v1.3.md` | `t2a-audit-v1.0` | **FROZEN** |
| **T2b-2** — twisted-channel sign map (production grid) | `MirrorTopology_T2b2_signmap_v0.9.ipynb` | `docs/T2b2_decision_rules_frozen_v0.3.md` | — | production complete |
| **Step 0** — frozen observational values | `MirrorTopology_Step0_observed_values_v0.6.ipynb` | — | — | see §6 |

Shared, frozen library code (do not edit; referenced by hash from the notebooks above):

- `t1_engine.py` — audited low-ℓ engine (sampler, exact parity operators, symmetry projection)
- `t2b2_bridge.py`, `t2b2_run.py`, `t2b2_core.py` — real-basis transform, git gate, T2b-2 logic

## 2. Results

Frozen outputs live under `results/<stage>/` together with the full execution log:

- `results/t1_audit_v1.0/` — `t1_audited_results.csv`, `t1_audited_realizations.npz`,
  `t1_audited_provenance.json`, Colab log
- `results/t2a_audit_v1.0/` — `t2a_analytic_audited.csv`, `t2a_pixelization_study.csv`,
  `t2a_provenance.json`, Colab log

Each provenance JSON contains the notebook's **source-only SHA256** (a hash of the code cells
alone, invariant under editor whitespace normalisation and output autosave), so any third party
can verify that the published code is exactly what produced the published numbers.

## 3. Reproducing a frozen stage

```bash
git clone https://github.com/tsujikeita/mirror-topology.git
cd mirror-topology
git checkout t2a-audit-v1.0        # or t1-audit-v1.0
```

Open the canonical notebook of that stage in Google Colab (or Jupyter) and run all cells
without editing them. The notebook will:

1. verify that it is running from a clean, pushed, public commit whose HEAD source matches the
   live notebook (`REPO_GATE`);
2. pin every dependency by commit hash (e.g. CMBtopology `0cc65e34…`) and re-clone it into an
   ephemeral directory;
3. verify every input by SHA256 before use;
4. run its analytic self-tests **before** touching real data;
5. refuse to declare itself `OFFICIAL` unless all hard gates pass.

If a gate fails, the notebook stops. That is by design: several real defects in this project
were caught this way, and none of them were caught by inspecting outputs.

## 4. Audit trail

- `docs/*_audit_rules_*.md` — the frozen decision rules for each stage. Thresholds are fixed
  *before* results are seen and are never relaxed afterwards.
- `docs/gate_design_notes_v1.0.md` — how the reproducibility gates were designed, and the
  concrete failure modes that motivated each one.
- `archive/` — superseded intermediate versions and the pre-audit originals, retained so that
  the audit history can be inspected. **Nothing in `archive/` should be cited or re-run.**

## 5. Scope of the current results

T1 and T2a are **full-sky, deterministic theoretical diagnostics**. They characterise the
predictions of compact-flat topologies for reflection-parity statistics at fixed holonomy axes.
They are *not* a direct comparison with observation: matching the observed selectively low S⁺
with a near-normal S⁻ requires the same mask, preprocessing, frozen statistic and scan rule to
be applied to both model and data, which is the subject of the next stage (Step 1).

In particular, the descriptive result that E[S⁺] > E[S⁻] holds for all 28 fixed holonomy
operators examined is **not** used to accept or reject any model.

## 6. Open item

The Step 0 notebook tracked here is `v0.6`, while the frozen Step 0 observational artefacts
were produced by `v0.7`. The v0.7 notebook and its artefacts should be added under
`results/step0_v0.7/` so that Step 0 reaches the same archival standard as T1 and T2a.

## 7. License

See `LICENSE`.

---

## 日本語版（要約）

CMBの鏡映対称性統計とコンパクト平坦トポロジーの関係を調べる研究（テーマT）の，**監査済み・
追試可能な解析コード**一式です。各解析は実行前の独立監査と，実行後の成果物の独立再計算を
通過しています。凍結された各段階は**gitタグ**と**provenance JSON**（commit・全ファイルの
ハッシュ・依存バージョン・全ゲートの判定結果を記録）で特定できます。

- **正本**はリポジトリ直下のノートブックと`docs/`の規則ファイル（§1の表）。
- **成果物**は`results/`（実行ログ込み）。
- **`archive/`は監査履歴の保存**であり，引用・再実行の対象ではありません。
- 追試は§3の手順（タグをcheckout→ノートブックを編集せず全実行）。ゲートが停止したら，
  それは設計どおりの動作です。
- T1・T2aは**全天の決定論的な理論診断**であり，観測との直接比較ではありません（Step 1の課題）。
