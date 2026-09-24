# -*- coding: utf-8 -*-
"""D-3 tranche 1: explicit 12-position configuration mapping, PC-1 contract transcribed from the frozen A11 originals, PC-1 / first-wave clone case table, and the D-2 -> D-3
reuse-binding schema. No covariance, bank or PC-1 number is produced here.
MAPPING (design v0.2 §D): for every registered twelve manifest (E2/E7/E8 x 3 sizes; receipt-bound intake), positions 0..2 are the frozen first-wave anchors and MUST reproduce
the first-wave ConfigurationSpec (reduced coords, r_obs, x0_CT, cache_key) exactly; positions 3..11 are the registered added points and receive config_id = 10000*family +
100*size + (position_index + 1), i.e. suffixes 04..12. E1 keeps its 3 first-wave configurations (no 12-position stage). Evaluation ids follow registered_id_map's rule:
matched = config_id, native = config_id + NATIVE_OFFSET. The map is a bijection (physical config_id, system) <-> evaluation_id over 222 ids, disjoint from nothing (first-wave
ids are preserved verbatim). Consumer position indices are 0..11; display suffixes 01..12.
PC-1 CONTRACT (design v0.2 §C): transcribed from A11_rules_v1.0.md R2/R5 and the frozen A11 v1.4.1 notebook cell 5 (metric) / cell 3 (generators, clone x0):
   relation C(g r) = D(M) C(r) D(M)^T on the frozen real basis; base x0 = b = -r_obs; clone (registered hypothesis H1) x0_H1 = M_CT b - T_CT; metric rel(C1, target) =
   ||C1 - target||_F / ||target||_F with target = D(M) C0 D(M)^T (also rel_off, rel_white as diagnostics); tolerance match rel < 1e-5 (R5 TOL_MATCH); comparison direction:
   independently generated clone covariance C1 versus the transformed base; D(M) = (YQ*WQ)^T Ymat(DIRS @ M) from the A9 quadrature bridge (t2b2_bridge, E = conj(M21)*Y_c).
   The 1e-10 of the D-1 pins is the same-covariance regeneration tolerance and is NOT used here.
CASE TABLE: one case per (new configuration, required generator of its family): E2 halfturn_B; E7 glide_A; E8 glide_A AND glide_B (two actions) -> 27 + 27 + 54 = 108 new-point
cases; first-wave anchor diagnostics (E2 9, E7 9, E8 18 = 36 cases; E1 excluded: homogeneous) recorded as a separate set reusing the D-1 base covariances by fixed SHA.
Unique covariance requests: 81 new bases + 108 new clones + 36 first-wave clones = 225 generations (30 first-wave bases reused). Generators are extracted from the pinned
CMBtopology source exactly as A11 cell 3 (gens_CT; verbatim copy with the cell SHA recorded)."""
from __future__ import annotations
import hashlib, json, os, re
from typing import Dict, List, Optional
import numpy as np
from .errors import InputContractError
from .grid_manifest import FAMILY_CODES, SIZE_CODES, ConfigurationSpec, lift, cache_key as _cache_key, ConfigurationManifest
from .production import NATIVE_OFFSET
from . import serialization as ser

A11_RULES_SHA = "5c6d9cd33e9ee2ac1573f0c2c492b5900d7b04edcd1c4eb9cc144081dc56d631"
A11_NOTEBOOK_SHA = "791a5abb74beb2370e036519283ca64ab34a886cc4267147c104c1cd604191a1"
PC1_CONTRACT = dict(schema="d3_pc1_contract_v1", source=dict(rules="results/step1_phaseA/A11_freeze/A11_rules_v1.0.md", rules_sha256=A11_RULES_SHA, notebook="results/step1_phaseA/A11_freeze/MirrorTopology_Step1_A11_x0bridge_v1.4.1.ipynb", notebook_sha256=A11_NOTEBOOK_SHA, rule_ids=["R2", "R5"], notebook_cells=dict(metric=5, generators=3, D_of=2)),
                    relation="C(g r) = D(M) C(r) D(M)^T on the frozen real basis (t1_engine.load_cov_full real basis; D(M) from t2b2_bridge quadrature: (YQ*WQ)^T Ymat(DIRS @ M))",
                    base_x0="b = -r_obs (A11 R1 canonical gauge)", clone_x0="x0_H1 = M_CT b - T_CT (registered hypothesis H1; H2 = M_CT b + T_CT is the discriminating alternative, not the clone)",
                    metric="rel(C1, target) = ||C1 - target||_F / ||target||_F, target = D(M) C0 D(M)^T, C0 = base covariance, C1 = INDEPENDENTLY generated clone covariance; diagnostics rel_off (off-diagonal), rel_white (diagonal-whitened)",
                    direction="generated clone C1 compared to the transformed base; never D C0 D^T stored as the clone's generated value", tolerance=dict(match_rel_lt=1e-5, discriminate_rel_gt=1e-2, source="A11 R5: match rel < 1e-5 (TOL_MATCH); discriminate rel > 1e-2 (TOL_DISCR)"),
                    not_used=dict(d1_pins_rel_tolerance=1e-10, reason="same-covariance regeneration tolerance of the D-1 A11 cross-check; not a physical clone tolerance"),
                    basis="both covariances loaded with the frozen t1_engine real-basis transform (21x21 real); M is the spatial 3x3 deck matrix; D(M) is its 21x21 representation", improper_M="valid (A11 R2)",
                    status_semantics=dict(PC1_PENDING="asset generated / not yet compared", PC1_PASS="rel < 1e-5 for every required action of the configuration", PC1_FAIL="any required action rel >= 1e-5 (asset-layer failure; formal consumption forbidden; NOT converted to position-unresolved / UNKNOWN; no prior renormalisation; no 3-position fallback)"))


def _gens_CT(top: str, p: dict, ct_dir: str) -> dict:
    """Verbatim from A11 v1.4.1 cell 3 (gens_CT): generators of the pinned CMBtopology source, independent of A6."""
    src = open(os.path.join(ct_dir, "topology", "src", f"{top}.py")).read().replace("\r", "")
    out = {}
    if top in ("E7", "E8"):
        Ms = {m.group(1): np.array(eval(m.group(2), {"np": np}), float) for m in re.finditer(r"M_([A-Z])\s*=\s*(np\.diag\(\[[^\]]*\]\))", src)}
        Ts = {}
        for m in re.finditer(r"T_([A-Z])\s*=\s*np\.array\(\[([^\]]*)\]\)", src):
            Ts[m.group(1)] = np.array(eval("[" + m.group(2) + "]", {**{k: float(v) for k, v in p.items()}}), float)
        for k in Ms: out[f"glide_{k}"] = (Ms[k], Ts[k])
    else:
        m = re.search(r"T_B\s*=\s*L_z\s*\*\s*np\.array\(\[([^\]]*)\]\)", src); assert m, "E2 T_B not found"
        from math import cos, sin, pi
        beta, gamma = p["beta"] * pi / 180, p["gamma"] * pi / 180
        T_B = p["Lz"] * np.array(eval("[" + m.group(1) + "]", {"cos": cos, "sin": sin, "beta": beta, "gamma": gamma}), float)
        assert re.search(r"2\*1j\*\(k_x\*x0\[0\]\s*\+\s*k_y\*x0\[1\]\)", src), "E2 half-turn phase pattern not found"
        out["halfturn_B"] = (np.diag([-1., -1., 1.]), T_B)
    return out


REQUIRED_ACTIONS = dict(E2=["halfturn_B"], E7=["glide_A"], E8=["glide_A", "glide_B"])


def build_twelve_config_map(reg, man: ConfigurationManifest, twelve_assets) -> dict:
    """Explicit mapping for the 12-position stage. reg: source-bound registry; man: first-wave manifest; twelve_assets: receipt-intaken TwelveManifestAsset."""
    man.validate(); by_key = {(c.family, c.size_id, c.position_index): c for c in man.configurations}; rows = []; used = set()
    for fam in ("E2", "E7", "E8"):
        for size in sorted(reg.surviving[fam], key=lambda s: SIZE_CODES[s]):
            tm = twelve_assets.get(fam, size, None) if hasattr(twelve_assets, "get") else twelve_assets.manifests[fam][size]
            pts = [list(map(float, p)) for p in tm.points]
            if len(pts) != 12: raise InputContractError(f"{fam}/{size}: twelve manifest must have 12 points")
            p = dict(by_key[(fam, size, 0)].shape_params)
            for idx, q in enumerate(pts):
                cid = 10000 * FAMILY_CODES[fam] + 100 * SIZE_CODES[size] + (idx + 1)
                r = lift(fam, q, p); x0 = [-float(v) for v in r]; ck = _cache_key(fam, p, x0)
                if idx < 3:                                                                   # frozen first-wave anchor: must reproduce the first-wave spec exactly
                    fw = by_key[(fam, size, idx)]
                    if fw.config_id != cid or [float(v) for v in fw.reduced_coords] != q or [float(v) for v in fw.x0_CT] != x0 or fw.cache_key != ck: raise InputContractError(f"{fam}/{size} position {idx}: twelve anchor does not reproduce the first-wave configuration {fw.config_id}")
                    origin = "first_wave"
                else: origin = "twelve_added"
                if cid in used: raise InputContractError("config id collision"); used.add(cid)
                rows.append(dict(config_id=cid, family=fam, size_id=size, position_index=idx, display_suffix=f"{idx + 1:02d}", origin=origin, reduced_coords=q, r_obs=[float(v) for v in r], x0_CT=x0, cache_key=ck, shape_params=p, weight_family=1.0 / 36.0, weight_within_size=1.0 / 12.0, evaluation_ids=dict(matched=cid, native=cid + NATIVE_OFFSET), twelve_manifest_sha256=tm.sha256))
    for c in man.configurations:
        if c.family == "E1": rows.append(dict(config_id=c.config_id, family="E1", size_id=c.size_id, position_index=0, display_suffix="01", origin="first_wave_E1_homogeneous", reduced_coords=[float(v) for v in c.reduced_coords], r_obs=[float(v) for v in c.r_obs], x0_CT=[float(v) for v in c.x0_CT], cache_key=c.cache_key, shape_params=dict(c.shape_params), weight_family=None, weight_within_size=None, evaluation_ids=dict(matched=c.config_id, native=c.config_id + NATIVE_OFFSET), twelve_manifest_sha256=None))
    ids = [r["config_id"] for r in rows]; evs = [(r["config_id"], s) for r in rows for s in ("matched", "native")]; evids = [r["evaluation_ids"][s] for r in rows for s in ("matched", "native")]
    if len(set(ids)) != len(ids) or len(set(evids)) != len(evids) or len(rows) != 111 or len(evids) != 222: raise InputContractError("mapping inventory (111 physical / 222 evaluation ids expected)")
    first_wave_ids = {c.config_id for c in man.configurations}
    if not first_wave_ids <= set(ids) or any(r["origin"].startswith("first_wave") != (r["config_id"] in first_wave_ids) for r in rows): raise InputContractError("first-wave ids must be preserved verbatim")
    m = dict(schema="d3_twelve_config_map_v1", registry_sha256=reg.registry_sha256, first_wave_manifest_sha256=man.manifest_sha256, twelve_assets_sha256=twelve_assets.sha256, n_physical=len(rows), n_new=sum(r["origin"] == "twelve_added" for r in rows), n_evaluation_ids=len(evids), position_index_range=[0, 11], display_suffix_range=["01", "12"], native_offset=NATIVE_OFFSET, configurations=rows)
    m["map_sha256"] = hashlib.sha256(json.dumps({k: v for k, v in m.items() if k != "map_sha256"}, sort_keys=True).encode()).hexdigest(); return m


def build_pc1_case_table(config_map: dict, ct_dir: str, d1_registry: Optional[dict] = None) -> dict:
    """PC-1 cases for every new configuration and required action of its family; first-wave anchor diagnostics as a separate set (base reused by D-1 SHA)."""
    cases = []; anchors = []; gens_cache = {}
    for r in config_map["configurations"]:
        fam = r["family"]
        if fam == "E1": continue
        p = dict(r["shape_params"])
        if fam == "E2":                                                                        # registered E2 shapes carry no angles: CMBtopology defaults (parameter_files/default_E2.py) are used by the generator; transcribed here explicitly
            p.setdefault("alpha", 90.0); p.setdefault("beta", 90.0); p.setdefault("gamma", 0.0)
        key = (fam, json.dumps(p, sort_keys=True))
        if key not in gens_cache: gens_cache[key] = _gens_CT(fam, p, ct_dir)
        gens = gens_cache[key]; b = np.array(r["x0_CT"], float)
        for act in REQUIRED_ACTIONS[fam]:
            M, T = gens[act]; x0c = (M @ b - T).tolist()
            row = dict(case_id=f"{r['config_id']}:{act}", config_id=r["config_id"], family=fam, size_id=r["size_id"], action=act, M=M.tolist(), T=T.tolist(), base_x0=r["x0_CT"], clone_x0_H1=x0c, alt_x0_H2=(M @ b + T).tolist(), shape_params=r["shape_params"], generator_params=p, metric="rel_frobenius", tolerance_match_rel_lt=PC1_CONTRACT["tolerance"]["match_rel_lt"], status="PC1_PENDING")
            if r["origin"] == "twelve_added": cases.append(row)
            else:
                d1 = None if d1_registry is None else d1_registry["configurations"].get(str(r["config_id"]))
                anchors.append(dict(row, set="first_wave_anchor_diagnostic", base_reused_from_D1=(None if d1 is None else dict(cov_file=d1["cov_file"], cov_file_sha256=d1["cov_file_sha256"], cov_array_sha256=d1["cov_array_sha256"]))))
    uniq_new_base = len({c["config_id"] for c in cases}); uniq_new_clone = len({(c["config_id"], c["action"]) for c in cases}); uniq_anchor_clone = len({(c["config_id"], c["action"]) for c in anchors})
    t = dict(schema="d3_pc1_case_table_v1", contract=PC1_CONTRACT, config_map_sha256=config_map["map_sha256"], required_actions=REQUIRED_ACTIONS, new_point_cases=cases, first_wave_anchor_cases=anchors,
             counts=dict(new_point_cases=len(cases), first_wave_anchor_cases=len(anchors), unique_covariance_requests=dict(new_bases=uniq_new_base, new_clones=uniq_new_clone, first_wave_clones=uniq_anchor_clone, first_wave_bases_reused=len({c["config_id"] for c in anchors}), total_new_generations=uniq_new_base + uniq_new_clone + uniq_anchor_clone), note="one case per (configuration, required action); E8 has two actions; E1 excluded (homogeneous)"))
    t["table_sha256"] = hashlib.sha256(json.dumps({k: v for k, v in t.items() if k != "table_sha256"}, sort_keys=True).encode()).hexdigest(); return t


REUSE_BINDING_SCHEMA = dict(schema="d3_d2_reuse_binding_v1", purpose="D-3 consumes accepted D-2 first-wave assets as FIXED inputs (never re-generated, never re-labelled as D-3 output)",
    identity_kept_verbatim=["D-2 producer digest", "generator commit 8b5e6102f0088afbf69b10aaa9e90af4a63e07e2", "generation environment fingerprint (E8 retains its own)", "COMPLETE manifest SHA", "sidecar SHA", "NPZ file SHA", "member array SHAs", "root SHA per role", "formal keys (MASTER_SEED, wave 1, purpose, group, batch, stream)", "UID ends and rotation index ranges", "selections"],
    must_match_the_D3_request=["family", "config_id (first-wave ids preserved)", "role -> root SHA (model roots from the D-1 intake of the SAME configuration; ref_matched = PR3 isotropic root; ref_native from the configuration's own c_ct)", "purpose / group / batch / rotation index / row order", "selection set", "n_rows (N0 batch 0; 3N0 batch 1; N_fit; )", "prefix invariance (batch 0 rows are the prefix of the family latent)"],
    view_differences_allowed=["stage (3-position vs 12-position mixture view)", "weights (1/3 or size-conditional -> 1/36 family / 1/12 within size)", "assembly into a 12-position FamilyInput"],
    forbidden=["asserting a new configuration shares a root with an old one", "substituting the family matched reference for a native reference", "re-stamping producer / environment / engine of a reused asset", "relaxing match_request for same-producer caches", "silent generalisation of the D-2 f32 acceptance to new positions"],
    plan_sharing=dict(rule="within each family, old and new configurations of the same system share the five-seed BootstrapPlan / FittingPlan identities and UID order; evaluation and fitting stay separate purposes", fixed="plan identity fixed once before the formal calibration and unchanged through the target evaluation; no threshold-dependent resampling; no unrecorded keys"))
