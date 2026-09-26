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
Unique covariance requests: 81 new bases + 108 new clones + 36 first-wave clones = 225 generations (27 first-wave bases reused; the 3 E1 covariances are kept but not clone-tested). Generators are extracted from the pinned
CMBtopology source exactly as A11 cell 3 (gens_CT; verbatim copy with the cell SHA recorded)."""
from __future__ import annotations
import copy, hashlib, json, os, re, subprocess
from typing import Dict, List, Optional
import numpy as np
from .errors import InputContractError
from .grid_manifest import FAMILY_CODES, SIZE_CODES, ConfigurationSpec, lift, cache_key as _cache_key, ConfigurationManifest, build_configuration_manifest
from .production import NATIVE_OFFSET, D1_REGISTERED_RECEIPT
from . import serialization as ser

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CT_COMMIT = "0cc65e34f03df85e92f738686bff0a476132f337"
CT_FILES = ("topology/src/E2.py", "topology/src/E7.py", "topology/src/E8.py", "topology/parameter_files/default_E2.py")
A11_RULES_SHA = "5c6d9cd33e9ee2ac1573f0c2c492b5900d7b04edcd1c4eb9cc144081dc56d631"
A11_NOTEBOOK_SHA = "791a5abb74beb2370e036519283ca64ab34a886cc4267147c104c1cd604191a1"
TRUSTED_SOURCES = dict(                                                             # fixed trust anchor for the registered originals (full SHA-256; independent of any packet manifest)
    a11_extract_manifest="95ccecfc7d5ee6c48fccc7b924a0e82cbef1dbffeb2edea0d0840f45519f0547",
    a11_rules=A11_RULES_SHA, a11_notebook=A11_NOTEBOOK_SHA,
    a11_cells={"2": "2827e63e9e46c78fa9a89be3a308e6cf00f1ed786839fe96be6e930117628a27", "3": "468d1a8a902318d9803e1475dd55206051bb641f6a310a0a8846af7e7646bd00", "5": "02a94ea127ff834b6425ac2445c9e879a5f4e021489449d358e1422b117d90e6"},
    ct_manifest="7b623cf9138fee6216135b0f67379ec0d7da1061137bf5c1ed275232a54f7968",
    ct_files={"topology/src/E2.py": "ea13ff16e8a9072c8d6fa2c8a3e64f1b56ef7f6fbe1db2250fd5475b1a703776", "topology/src/E7.py": "34cb0b19b32cca8ef5db4d96f5df9d977517d8eadef9bb6d95c90e687753d84d", "topology/src/E8.py": "3979deca5f06734882cd767c055f89d7dc10d6e89393b5537b9ad963dff76f5d", "topology/parameter_files/default_E2.py": "4d1b0e43f9e8a6026974d7d7c66ef19fdcf6d5c03e1f427542fdd1f89fdda1ed"})
A11_REQUIRED_CELLS = ("2", "3", "5")


def _sha_bytes(b: bytes) -> str: return hashlib.sha256(b).hexdigest()


def _is_int(v): return isinstance(v, int) and not isinstance(v, bool)


def _read_trusted(path: str, expected_sha: str, what: str) -> bytes:
    b = open(path, "rb").read()
    if _sha_bytes(b) != expected_sha: raise InputContractError(f"{what}: bytes differ from the trusted constant SHA")
    return b


def a11_attestation() -> dict:
    """The frozen A11 originals bound to the FIXED trust constants (TRUSTED_SOURCES), not to the packet manifest: the extract manifest, the rules text, the three required cells
    (2/3/5, fixed set) and the FULL frozen notebook (registered copy; SHA 791a5abb…) are each read once, SHA-checked against the constants BEFORE decoding, and the cells are
    re-extracted from the full notebook and compared with the registered extracts. Returns typed copies of the cell text."""
    R = os.path.join(_ROOT, "registered_assets", "a11"); T = TRUSTED_SOURCES
    mb = _read_trusted(os.path.join(R, "a11_extract_manifest.json"), T["a11_extract_manifest"], "A11 extract manifest"); m = json.loads(mb.decode("utf-8"))
    if m.get("rules_sha256") != T["a11_rules"] or m.get("notebook_sha256") != T["a11_notebook"] or set(m.get("cells", {})) != set(A11_REQUIRED_CELLS): raise InputContractError("A11 extract manifest does not name the pinned originals / required cell set")
    rules_b = _read_trusted(os.path.join(R, "A11_rules_v1.0.md"), T["a11_rules"], "A11 rules text")
    nb_b = _read_trusted(os.path.join(R, m.get("notebook_file", "MirrorTopology_Step1_A11_x0bridge_v1.4.1.ipynb")), T["a11_notebook"], "A11 frozen notebook"); nbj = json.loads(nb_b.decode("utf-8"))
    cells = {}
    for i in A11_REQUIRED_CELLS:
        c = m["cells"][i]
        if c.get("source_sha256") != T["a11_cells"][i]: raise InputContractError(f"A11 extract manifest cell {i} SHA differs from the trusted constant")
        b = _read_trusted(os.path.join(R, c["file"]), T["a11_cells"][i], f"A11 cell {i} extract"); txt = b.decode("utf-8")
        if "".join(nbj["cells"][int(i)]["source"]) != txt: raise InputContractError(f"A11 cell {i}: registered extract differs from the full frozen notebook")
        cells[i] = txt
    txt = rules_b.decode("utf-8")
    if "C(g r) = D(M) C(r) D(M)ᵀ" not in txt or "match: rel < 1e-5" not in txt or "discriminate: rel > 1e-2" not in txt: raise InputContractError("A11 rules text lacks the R2/R5 statements")
    if "TOL_MATCH, TOL_DISCR = 1e-5, 1e-2" not in cells["5"] or "def rel(A, B): return float(np.linalg.norm(A - B) / np.linalg.norm(B))" not in cells["5"] or "x0_H1=MCT @ b - TCT" not in cells["3"] or "def D_of(" not in cells["2"]: raise InputContractError("A11 notebook extract lacks the metric / tolerance / clone / D_of statements")
    return dict(rules_sha256=T["a11_rules"], notebook_sha256=T["a11_notebook"], cells=dict(T["a11_cells"]), extract_manifest_sha256=T["a11_extract_manifest"], source="registered_originals_trust_anchored", cell_text=dict(cells))


def ct_source_context(ct_dir: Optional[str] = None) -> dict:
    """Source-bound CMBtopology generator input, anchored to TRUSTED_SOURCES: the registered manifest bytes and every required file are SHA-checked against the constants
    before use. When ct_dir is given, the checkout must additionally be the pinned clean commit and its files must have the SAME constant SHAs (a checkout is never a way to
    substitute other bytes). Returns the verified BYTES that will be parsed."""
    R = os.path.join(_ROOT, "registered_assets", "ct_pinned"); T = TRUSTED_SOURCES
    mb = _read_trusted(os.path.join(R, "ct_source_manifest.json"), T["ct_manifest"], "CT source manifest"); man = json.loads(mb.decode("utf-8"))
    if man.get("commit") != CT_COMMIT or set(man.get("files", {})) != set(CT_FILES) or man["files"] != T["ct_files"] or man.get("git_commit_file_sha") != T["ct_files"]: raise InputContractError("pinned CT source manifest differs from the trusted constants")
    out = dict(commit=CT_COMMIT, files={}, file_sha256=dict(T["ct_files"]))
    if ct_dir is not None:
        run = lambda c: subprocess.run(c, capture_output=True, text=True)
        h = run(["git", "-C", ct_dir, "rev-parse", "HEAD"]); o = run(["git", "-C", ct_dir, "remote", "get-url", "origin"]); st = run(["git", "-C", ct_dir, "status", "--porcelain", "--untracked-files=all"])
        if not (h.returncode == 0 and h.stdout.strip() == CT_COMMIT and o.returncode == 0 and o.stdout.strip().rstrip("/").removesuffix(".git") == man["url"] and st.returncode == 0 and st.stdout.strip() == ""): raise InputContractError("CMBtopology checkout is not the pinned clean commit")
        for f in CT_FILES: out["files"][f] = _read_trusted(os.path.join(ct_dir, f), T["ct_files"][f], f"CMBtopology checkout {f}")
        out["source"] = "pinned_checkout_verified"
    else:
        for f in CT_FILES: out["files"][f] = _read_trusted(os.path.join(R, f), T["ct_files"][f], f"registered CT copy {f}")
        out["source"] = "registered_pinned_copy"
    return out


PC1_CONTRACT = dict(schema="d3_pc1_contract_v1", source=dict(rules="results/step1_phaseA/A11_freeze/A11_rules_v1.0.md", rules_sha256=A11_RULES_SHA, notebook="results/step1_phaseA/A11_freeze/MirrorTopology_Step1_A11_x0bridge_v1.4.1.ipynb", notebook_sha256=A11_NOTEBOOK_SHA, rule_ids=["R2", "R5"], notebook_cells=dict(metric=5, generators=3, D_of=2), registered_copies="registered_assets/a11 (full notebook + rules + cell extracts; trust-anchored SHAs in d3_stage.TRUSTED_SOURCES)"),
                    relation="C(g r) = D(M) C(r) D(M)^T on the frozen real basis (t1_engine.load_cov_full real basis; D(M) from t2b2_bridge quadrature: (YQ*WQ)^T Ymat(DIRS @ M))",
                    base_x0="b = -r_obs (A11 R1 canonical gauge)", clone_x0="x0_H1 = M_CT b - T_CT (registered hypothesis H1; H2 = M_CT b + T_CT is the discriminating alternative, not the clone)",
                    metric="rel(C1, target) = ||C1 - target||_F / ||target||_F, target = D(M) C0 D(M)^T, C0 = base covariance, C1 = INDEPENDENTLY generated clone covariance; diagnostics rel_off (off-diagonal), rel_white (diagonal-whitened)",
                    direction="generated clone C1 compared to the transformed base; never D C0 D^T stored as the clone's generated value", tolerance=dict(match_rel_lt=1e-5, discriminate_rel_gt=1e-2, source="A11 R5: match rel < 1e-5 (TOL_MATCH); discriminate rel > 1e-2 (TOL_DISCR)"),
                    not_used=dict(d1_pins_rel_tolerance=1e-10, reason="same-covariance regeneration tolerance of the D-1 A11 cross-check; not a physical clone tolerance"),
                    basis="both covariances loaded with the frozen t1_engine real-basis transform (21x21 real); M is the spatial 3x3 deck matrix; D(M) is its 21x21 representation", improper_M="valid (A11 R2)",
                    status_semantics=dict(PC1_PENDING="not yet compared (covariances may be ungenerated or generated; no PC-1 evaluation has been made)", PC1_PASS="rel < 1e-5 for every required action of the configuration", PC1_FAIL="any required action rel >= 1e-5 (asset-layer failure; formal consumption forbidden; NOT converted to position-unresolved / UNKNOWN; no prior renormalisation; no 3-position fallback)"))


def _gens_CT_from_source(top: str, p: dict, src: str) -> dict:
    """Body verbatim from A11 v1.4.1 cell 3 (gens_CT) except that the source TEXT is supplied by the verified context instead of being read from a path."""
    src = src.replace("\r", "")
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


def _gens_CT(top: str, p: dict, ctx: dict) -> dict: return _gens_CT_from_source(top, p, ctx["files"][f"topology/src/{top}.py"].decode("utf-8"))


REQUIRED_ACTIONS = dict(E2=["halfturn_B"], E7=["glide_A"], E8=["glide_A", "glide_B"])
E2_DEFAULT_ANGLES = dict(alpha=90.0, beta=90.0, gamma=0.0)


def _e2_defaults_from_ct(ctx: dict) -> dict:
    src = ctx["files"]["topology/parameter_files/default_E2.py"].decode("utf-8"); out = {}
    for k in ("alpha", "beta", "gamma"):
        m = re.search(rf"'{k}'\s*:\s*([0-9.+-]+)", src)
        if not m: raise InputContractError(f"default_E2.py lacks {k}")
        out[k] = float(m.group(1))
    if out != E2_DEFAULT_ANGLES: raise InputContractError("pinned default_E2 angles differ from the transcribed defaults")
    return out


def _bound_inputs(reg, man: ConfigurationManifest, twelve_assets):
    """Typed, mutually bound inputs: source-bound GridRegistry; ConfigurationManifest re-derived from it (as_dict equality); TwelveManifestAsset that passed the receipt-bound
    intake in this process (marker == asset SHA, verification receipt-bound), whole-asset validated against the SAME registry."""
    from .grid_registry import GridRegistry; from .twelve_assets import TwelveManifestAsset, REGISTERED_RECEIPTS
    if not isinstance(reg, GridRegistry) or not str(getattr(reg, "verification_scope", "")).startswith(("constructed_from_verified_assets", "source_bound")): raise InputContractError("registry must be the source-bound GridRegistry")
    if not isinstance(man, ConfigurationManifest): raise InputContractError("manifest type")
    man.validate(); expected = build_configuration_manifest(reg)
    if man.registry_sha256 != reg.registry_sha256 or man.as_dict() != expected.as_dict(): raise InputContractError("manifest is not the derivation of the supplied registry")
    if not isinstance(twelve_assets, TwelveManifestAsset): raise InputContractError("twelve_assets must be the registered TwelveManifestAsset (receipt-bound intake)")
    rc = {k: v for k, v in REGISTERED_RECEIPTS.items() if v["asset_sha256"] == twelve_assets.sha256}
    if not rc or getattr(twelve_assets, "_intake_sha256", None) != twelve_assets.sha256 or not str((twelve_assets.verification or {}).get("intake", "")).startswith("receipt-bound"): raise InputContractError("twelve asset must be a registered asset that passed intake_registered_twelve_assets in this process")
    twelve_assets.validate(reg, twelve_assets.sha256); return next(iter(rc))


def build_twelve_config_map(reg, man: ConfigurationManifest, twelve_assets) -> dict:
    """Explicit mapping for the 12-position stage (source-bound inputs only; see _bound_inputs). Returns an independent copy."""
    receipt = _bound_inputs(reg, man, twelve_assets)
    by_key = {(c.family, c.size_id, c.position_index): c for c in man.configurations}; rows = []; used = set()
    for fam in ("E2", "E7", "E8"):
        for size in sorted(reg.surviving[fam], key=lambda s: SIZE_CODES[s]):
            tm = twelve_assets.get(fam, size, twelve_assets.manifests[fam][size].sha256)
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
                if cid in used: raise InputContractError("config id collision")
                used.add(cid)
                rows.append(dict(config_id=cid, family=fam, size_id=size, position_index=idx, display_suffix=f"{idx + 1:02d}", origin=origin, reduced_coords=q, r_obs=[float(v) for v in r], x0_CT=x0, cache_key=ck, shape_params=p, weight_family=1.0 / 36.0, weight_within_size=1.0 / 12.0, evaluation_ids=dict(matched=cid, native=cid + NATIVE_OFFSET), twelve_manifest_sha256=tm.sha256))
    for c in man.configurations:
        if c.family == "E1": rows.append(dict(config_id=c.config_id, family="E1", size_id=c.size_id, position_index=0, display_suffix="01", origin="first_wave_E1_homogeneous", reduced_coords=[float(v) for v in c.reduced_coords], r_obs=[float(v) for v in c.r_obs], x0_CT=[float(v) for v in c.x0_CT], cache_key=c.cache_key, shape_params=dict(c.shape_params), weight_family=None, weight_within_size=None, evaluation_ids=dict(matched=c.config_id, native=c.config_id + NATIVE_OFFSET), twelve_manifest_sha256=None))
    ids = [r["config_id"] for r in rows]; evs = [(r["config_id"], s) for r in rows for s in ("matched", "native")]; evids = [r["evaluation_ids"][s] for r in rows for s in ("matched", "native")]
    if len(set(ids)) != len(ids) or len(set(evids)) != len(evids) or len(rows) != 111 or len(evids) != 222: raise InputContractError("mapping inventory (111 physical / 222 evaluation ids expected)")
    first_wave_ids = {c.config_id for c in man.configurations}
    if not first_wave_ids <= set(ids) or any(r["origin"].startswith("first_wave") != (r["config_id"] in first_wave_ids) for r in rows): raise InputContractError("first-wave ids must be preserved verbatim")
    m = dict(schema="d3_twelve_config_map_v1", registry_sha256=reg.registry_sha256, first_wave_manifest_sha256=man.manifest_sha256, twelve_assets_sha256=twelve_assets.sha256, twelve_assets_receipt=receipt, n_physical=len(rows), n_new=sum(r["origin"] == "twelve_added" for r in rows), n_evaluation_ids=len(evids), position_index_range=[0, 11], display_suffix_range=["01", "12"], native_offset=NATIVE_OFFSET, configurations=rows)
    m["map_sha256"] = _map_payload_sha(m); return copy.deepcopy(m)


def _map_payload_sha(m: dict) -> str: return hashlib.sha256(json.dumps({k: v for k, v in m.items() if k != "map_sha256"}, sort_keys=True).encode()).hexdigest()


def verify_config_map(cm: dict, reg, man: ConfigurationManifest, twelve_assets) -> dict:
    """A map is accepted only if it EQUALS the map re-derived from the bound inputs (payload SHA + full content); returns an independent, typed copy."""
    if not isinstance(cm, dict) or _map_payload_sha(cm) != cm.get("map_sha256"): raise InputContractError("config map payload SHA")
    canon = build_twelve_config_map(reg, man, twelve_assets)
    if cm != canon: raise InputContractError("config map differs from the map re-derived from the bound registry / manifest / twelve asset")
    for r in canon["configurations"]:
        if not (_is_int(r["config_id"]) and r["family"] in FAMILY_CODES and r["size_id"] in SIZE_CODES and _is_int(r["position_index"]) and 0 <= r["position_index"] <= 11 and len(r["x0_CT"]) == 3 and all(isinstance(v, float) for v in r["x0_CT"]) and r["x0_CT"] == [-float(v) for v in r["r_obs"]] and r["cache_key"] == _cache_key(r["family"], r["shape_params"], r["x0_CT"])): raise InputContractError(f"config map row {r.get('config_id')}: typed content")
    return canon


def _d1_registry_bound(d1_dir: Optional[str]) -> Optional[dict]:
    if d1_dir is None: return None
    p = os.path.join(d1_dir, "d1_cov_registry.json"); b = open(p, "rb").read()
    if _sha_bytes(b) != D1_REGISTERED_RECEIPT["registry_sha256"] or _sha_bytes(open(os.path.join(d1_dir, "d1_receipt.json"), "rb").read()) != D1_REGISTERED_RECEIPT["receipt_file_sha256"]: raise InputContractError("D-1 registry / receipt bytes differ from the trusted constants")
    return json.loads(b.decode("utf-8"))


def build_pc1_case_table(config_map: dict, reg, man: ConfigurationManifest, twelve_assets, ct_dir: Optional[str] = None, d1_dir: Optional[str] = None) -> dict:
    """PC-1 cases for every new configuration and required action of its family, plus the first-wave anchor diagnostics (separate set; base reused by D-1 SHA).
    Inputs are VERIFIED before use: config_map == re-derivation from the bound (reg, man, twelve_assets); generators extracted from the source-bound CT context (pinned
    checkout or registered pinned copies; file SHAs recorded); A11 attestation recorded; D-1 references bound to the trusted receipt/registry and to the SAME config_id
    (draft=True when no D-1 directory is given: anchor cases carry no D-1 reference and the table is not formal). All returned structures are independent snapshots."""
    cm = verify_config_map(config_map, reg, man, twelve_assets); ctx = ct_source_context(ct_dir); att = a11_attestation(); d1 = _d1_registry_bound(d1_dir)      # formal entry: every source is trust-anchored before any extraction
    contract = copy.deepcopy(PC1_CONTRACT); actions = copy.deepcopy(REQUIRED_ACTIONS); e2ang = _e2_defaults_from_ct(ctx)
    cases = []; anchors = []; gens_cache = {}
    for r in cm["configurations"]:
        fam = r["family"]
        if fam == "E1": continue
        p = dict(r["shape_params"])
        if fam == "E2":
            for k, v in e2ang.items(): p.setdefault(k, v)
        key = (fam, json.dumps(p, sort_keys=True))
        if key not in gens_cache: gens_cache[key] = _gens_CT(fam, p, ctx)
        gens = gens_cache[key]; b = np.array(r["x0_CT"], float)
        for act in actions[fam]:
            if act not in gens: raise InputContractError(f"{fam}: required action {act} not found in the pinned CMBtopology source")
            M, T = gens[act]; x0c = (M @ b - T).tolist()
            row = dict(case_id=f"{r['config_id']}:{act}", config_id=r["config_id"], family=fam, size_id=r["size_id"], action=act, M=M.tolist(), T=T.tolist(), base_x0=list(r["x0_CT"]), clone_x0_H1=x0c, alt_x0_H2=(M @ b + T).tolist(), shape_params=copy.deepcopy(r["shape_params"]), generator_params=copy.deepcopy(p), metric="rel_frobenius", tolerance_match_rel_lt=contract["tolerance"]["match_rel_lt"], status="PC1_PENDING")
            if r["origin"] == "twelve_added": cases.append(row)
            else:
                ref = None
                if d1 is not None:
                    e = d1["configurations"].get(str(r["config_id"]))
                    if e is None or e.get("cache_key") != r["cache_key"] or [float(v) for v in e.get("x0_CT", [])] != r["x0_CT"] or e.get("family") != fam: raise InputContractError(f"D-1 registry has no matching entry for configuration {r['config_id']} (same config_id / cache_key / x0 required)")
                    ref = dict(config_id=r["config_id"], cov_file=e["cov_file"], cov_file_sha256=e["cov_file_sha256"], cov_array_sha256=e["cov_array_sha256"], receipt=D1_REGISTERED_RECEIPT["id"])
                anchors.append(dict(row, set="first_wave_anchor_diagnostic", base_reused_from_D1=ref))
    exp_new = sum(len(actions[f]) * sum(1 for r in cm["configurations"] if r["family"] == f and r["origin"] == "twelve_added") for f in actions); exp_anchor = sum(len(actions[f]) * sum(1 for r in cm["configurations"] if r["family"] == f and r["origin"] == "first_wave") for f in actions)
    if len(cases) != exp_new or len(anchors) != exp_anchor or len({c["case_id"] for c in cases + anchors}) != len(cases) + len(anchors): raise InputContractError("case inventory differs from the required set (configurations x required actions)")
    uniq_new_base = len({c["config_id"] for c in cases}); uniq_new_clone = len({(c["config_id"], c["action"]) for c in cases}); uniq_anchor_clone = len({(c["config_id"], c["action"]) for c in anchors})
    t = dict(schema="d3_pc1_case_table_v2", formal=(d1 is not None), draft_note=(None if d1 is not None else "DRAFT: no D-1 directory supplied; anchor cases carry no D-1 reference; not a registrable table"), contract=contract, a11_attestation={k: v for k, v in att.items() if k not in ("cell_text", "source")}, ct_source=dict(commit=ctx["commit"], file_sha256=ctx["file_sha256"]), e2_default_angles=e2ang,
             provenance_route=dict(ct=ctx["source"], a11=att["source"], note="which verified route supplied the bytes; excluded from the payload SHA (the bytes are identical by SHA)"),
             config_map_sha256=cm["map_sha256"], registry_sha256=cm["registry_sha256"], twelve_assets_sha256=cm["twelve_assets_sha256"], required_actions=actions, new_point_cases=cases, first_wave_anchor_cases=anchors,
             counts=dict(new_point_cases=len(cases), first_wave_anchor_cases=len(anchors), unique_covariance_requests=dict(new_bases=uniq_new_base, new_clones=uniq_new_clone, first_wave_clones=uniq_anchor_clone, first_wave_bases_required=len({c["config_id"] for c in anchors}), first_wave_bases_verified_for_reuse=(len({c["config_id"] for c in anchors}) if d1 is not None else 0), total_new_generations=uniq_new_base + uniq_new_clone + uniq_anchor_clone), note="one case per (configuration, required action); E8 has two actions; E1 excluded (homogeneous); first-wave bases: 27 required (E2/E7/E8 anchors), verified for reuse only when the D-1 registry is bound (draft: 0); the 3 E1 D-1 covariances are kept but not clone-tested"))
    t["table_sha256"] = _table_payload_sha(t); return copy.deepcopy(t)


_TABLE_EXCLUDE = ("table_sha256", "provenance_route")


def _table_payload_sha(t: dict) -> str: return hashlib.sha256(json.dumps({k: v for k, v in t.items() if k not in _TABLE_EXCLUDE}, sort_keys=True).encode()).hexdigest()


def verify_pc1_case_table(t: dict, config_map: dict, reg, man, twelve_assets, ct_dir: Optional[str] = None, d1_dir: Optional[str] = None) -> dict:
    """Accepted only if EQUAL (payload SHA + content, provenance route excluded) to the table re-derived from the verified inputs."""
    if not isinstance(t, dict) or _table_payload_sha(t) != t.get("table_sha256"): raise InputContractError("case table payload SHA")
    canon = build_pc1_case_table(config_map, reg, man, twelve_assets, ct_dir, d1_dir)
    if {k: v for k, v in t.items() if k not in _TABLE_EXCLUDE} != {k: v for k, v in canon.items() if k not in _TABLE_EXCLUDE}: raise InputContractError("case table differs from the table re-derived from the verified inputs")
    return canon


REUSE_BINDING_SCHEMA = dict(schema="d3_d2_reuse_binding_v1", purpose="D-3 consumes accepted D-2 first-wave assets as FIXED inputs (never re-generated, never re-labelled as D-3 output)",
    identity_kept_verbatim=["D-2 producer digest", "generator commit 8b5e6102f0088afbf69b10aaa9e90af4a63e07e2", "generation environment fingerprint (E8 retains its own)", "COMPLETE manifest SHA", "sidecar SHA", "NPZ file SHA", "member array SHAs", "root SHA per role", "formal keys (MASTER_SEED, wave 1, purpose, group, batch, stream)", "UID ends and rotation index ranges", "selections"],
    must_match_the_D3_request=["family", "config_id (first-wave ids preserved)", "role -> root SHA (model roots from the D-1 intake of the SAME configuration; ref_matched = PR3 isotropic root; ref_native from the configuration's own c_ct)", "purpose / group / batch / rotation index / row order", "selection set", "n_rows (N0 batch 0; 3N0 batch 1; N_fit; )", "prefix invariance (batch 0 rows are the prefix of the family latent)"],
    view_differences_allowed=["stage (3-position vs 12-position mixture view)", "weights (1/3 or size-conditional -> 1/36 family / 1/12 within size)", "assembly into a 12-position FamilyInput"],
    forbidden=["asserting a new configuration shares a root with an old one", "substituting the family matched reference for a native reference", "re-stamping producer / environment / engine of a reused asset", "relaxing match_request for same-producer caches", "silent generalisation of the D-2 f32 acceptance to new positions"],
    plan_sharing=dict(rule="within each family, old and new configurations of the same system share the five-seed BootstrapPlan / FittingPlan identities and UID order; evaluation and fitting stay separate purposes", fixed="plan identity fixed once before the formal calibration and unchanged through the target evaluation; no threshold-dependent resampling; no unrecorded keys"))


REQUIRED_D3A_GATES = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_phaseC_members", "G_external_loader_sha", "G_a11_freeze_sha", "G_a11_generator_cell_sha", "G_env_lock", "G_ct_commit", "G_ct_origin", "G_ct_clean", "G_ct_dependencies_present",
                       "G_registry_source_bound", "G_config_map_bound", "G_case_table_bound", "G_d1_trusted", "G_bridge_quadrature", "G_all_bases_generated", "G_all_base_intakes_pass", "G_all_cases_evaluated", "G_evidence_saved")


class VerifiedPartition:
    """A D-3a run whose published documents were read from disk ONCE, hashed from the same bytes, matched against the run manifest's published_evidence / output_inventory, and
    semantically bound (source, gates, environment fingerprint recomputation, registry/case identities). Only instances of this class enter aggregate_partitions."""
    __slots__ = ("run_dir", "run_manifest", "registry", "pc1_results", "evidence", "env_lock", "document_sha256", "verified")
    def __init__(self, run_dir, rm, rg, pr, ev, env, shas): self.run_dir, self.run_manifest, self.registry, self.pc1_results, self.evidence, self.env_lock, self.document_sha256, self.verified = run_dir, rm, rg, pr, ev, env, shas, True


def _env_fingerprint_of(env_lock: dict, run_config: dict) -> str:
    return hashlib.sha256(json.dumps(dict(python=env_lock["python"], versions=env_lock["versions"], requirements_sha256=env_lock["requirements_sha256"], platform=env_lock["platform"], blas_lapack=env_lock["blas_lapack"], ct_commit=env_lock["cmbtopology_commit"], run_config=run_config), sort_keys=True).encode()).hexdigest()


def verify_partition_run(run_dir: str, expected_source: dict, expected_case_table_sha256: str, expected_config_map_sha256: str, require_arrays: bool = True, expected_run_manifest_sha256: Optional[str] = None) -> VerifiedPartition:
    """Trusted intake of one D-3a run directory (the script's --out). Reads each published document once; the same bytes are hashed, decoded and compared with the run manifest's
    published_evidence SHAs and, for every entry of output_inventory (documents and, when require_arrays, every covariance .npy), with the actual file bytes. Then: run
    D3_PASS/complete/no failures, required gates, source == expected (4 identities + profile), run_manifest.engine_version == source.engine_version, case-table / config-map
    SHAs == the expected (pins) values in registry and results, env fingerprint RECOMPUTED from the env lock == stored fingerprint in registry/results/env lock, every registry
    entry carries 64-hex file/array SHAs with intake pass, every case carries clone identity with 64-hex SHAs and EVALUATED, configuration_status keys == registry bases +
    anchor configurations of the run. Raises on any mismatch."""
    def rd(name):
        p = os.path.join(run_dir, name)
        if not os.path.exists(p): raise InputContractError(f"run document missing: {name}")
        b = open(p, "rb").read(); return b, hashlib.sha256(b).hexdigest(), json.loads(b.decode("utf-8"))
    _, rm_sha, rm = rd("d3_run_manifest.json")
    if expected_run_manifest_sha256 is not None and rm_sha != expected_run_manifest_sha256: raise InputContractError("run manifest bytes differ from the outer ledger identity")
    if not isinstance(rm, dict) or rm.get("D3_PASS") is not True or rm.get("stage") != "complete" or rm.get("failures") != []: raise InputContractError("run manifest is not a complete formal D3_PASS record")
    pub = ((rm.get("published_evidence") or {}).get("documents")) or {}
    if set(pub) != {"d3_cov_registry.json", "d3_pc1_results.json", "d3_partial_evidence.json", "d3_env_lock.json"} or rm["published_evidence"].get("value_level_readback_ok") is not True: raise InputContractError("run manifest lacks the published-evidence identities")
    docs = {}; shas = {}
    for name in pub:
        b, h, d = rd(name)
        if h != pub[name]["sha256"] or len(b) != pub[name]["bytes"]: raise InputContractError(f"{name}: bytes differ from the published identity")
        docs[name] = d; shas[name] = h
    inv = rm.get("output_inventory") or {}
    if not inv: raise InputContractError("run manifest lacks output_inventory")
    for rel, e in inv.items():
        p = os.path.join(run_dir, rel)
        if rel.endswith(".npy") and not require_arrays: continue
        if not os.path.exists(p): raise InputContractError(f"output missing: {rel}")
        b = open(p, "rb").read()
        if hashlib.sha256(b).hexdigest() != e.get("sha256") or len(b) != e.get("bytes"): raise InputContractError(f"output {rel}: bytes differ from the recorded inventory")
    rg, pr, ev, env = docs["d3_cov_registry.json"], docs["d3_pc1_results.json"], docs["d3_partial_evidence.json"], docs["d3_env_lock.json"]
    gates = rm.get("gates") or {}
    if set(gates) != set(REQUIRED_D3A_GATES) or any(gates.get(g) is not True for g in REQUIRED_D3A_GATES): raise InputContractError("required gates not all True / gate set differs")
    src = rm.get("source") or {}
    if any(src.get(k) != expected_source.get(k) for k in ("engine_version", "inventory_sha256", "script_sha256", "pins_sha256")) or src.get("profile") != "production_official" or rm.get("engine_version") != src.get("engine_version") or rg.get("source") != src or pr.get("source") != src: raise InputContractError("recorded source differs from the expected source / inconsistent across documents")
    sel = rm.get("selection") or {}
    if sel.get("selftest_configs") or sel.get("selftest_skip_anchors"): raise InputContractError("self-test run is not a formal partition")
    fam = rm.get("family")
    if not (fam == rg.get("family") == pr.get("family") == ev.get("family")): raise InputContractError("family differs across documents")
    if rg.get("case_table_sha256") != expected_case_table_sha256 or pr.get("case_table_sha256") != expected_case_table_sha256 or rg.get("config_map_sha256") != expected_config_map_sha256 or pr.get("config_map_sha256") != expected_config_map_sha256: raise InputContractError("case-table / config-map identities differ from the registered pins")
    fp = _env_fingerprint_of(env, rg.get("run_config"))
    if not (fp == env.get("env_fingerprint") == rg.get("env_fingerprint") == pr.get("env_fingerprint")): raise InputContractError("environment fingerprint does not re-derive from the env lock / differs across documents")
    hex64 = lambda v: isinstance(v, str) and len(v) == 64
    for cid, e in (rg.get("configurations") or {}).items():
        if not (isinstance(e, dict) and str(e.get("config_id")) == cid and hex64(e.get("cov_file_sha256")) and hex64(e.get("cov_array_sha256")) and (e.get("intake") or {}).get("pass_") is True and e.get("cov_file") and (e.get("bound_load") or {}).get("file_sha256") == e["cov_file_sha256"]): raise InputContractError(f"registry entry {cid}: incomplete / not passing")
        if require_arrays and (f"{e['cov_file']}" not in inv): raise InputContractError(f"registry entry {cid}: covariance file not in the output inventory")
    for k, v in (pr.get("cases") or {}).items():
        ci = v.get("clone_identity") or {}
        if v.get("evaluation") != "EVALUATED" or not (hex64(ci.get("file_sha256")) and hex64(ci.get("array_sha256")) and ci.get("loader_meta_sha") == ci.get("array_sha256")) or not hex64(v.get("D_sha256")) or not isinstance(v.get("rel"), float): raise InputContractError(f"case {k}: incomplete evaluation identity")
        if require_arrays and v.get("clone_cov_file") not in inv: raise InputContractError(f"case {k}: clone file not in the output inventory")
    if ev.get("status") != "COMPLETE" or set(ev.get("cases") or {}) != set(pr.get("cases") or {}) or set(ev.get("bases") or {}) != set(rg.get("configurations") or {}): raise InputContractError("partial evidence does not correspond to the published results")
    expected_status_keys = set(rg["configurations"]) | {str(v["config_id"]) for v in pr["cases"].values()}
    if set(pr.get("configuration_status") or {}) != expected_status_keys or set(rm.get("pc1_status") or {}) != expected_status_keys or rm["pc1_status"] != pr["configuration_status"]: raise InputContractError("configuration_status keys differ from the run's bases / evaluated configurations")
    shas["d3_run_manifest.json"] = rm_sha; return VerifiedPartition(run_dir, copy.deepcopy(rm), copy.deepcopy(rg), copy.deepcopy(pr), copy.deepcopy(ev), copy.deepcopy(env), shas)


def aggregate_partitions(case_table: dict, family: str, partitions: List[VerifiedPartition], expected_source: dict, expected_case_table_sha256: str) -> dict:
    """FORMAL family-level D-3a coverage from VERIFIED partition runs (verify_partition_run). The case table must equal the registered identity (expected_case_table_sha256 from the
    pins / canonical context), be payload-consistent and formal; every partition's sizes determine the expected new bases and case ids (new-point + anchor of those sizes);
    registry configurations and evaluated cases must equal them; each case: EVALUATED, config/action equal to the table, finite rel, match == (rel < tolerance);
    configuration_status re-derived and compared; partitions disjoint and covering all sizes; union == family required set. A finite PC1_FAIL is carried through. Returns a
    deep copy. Not a PC-1 acceptance; raw dicts are refused (use verify_partition_run)."""
    if _table_payload_sha(case_table) != case_table.get("table_sha256") or case_table.get("formal") is not True or case_table["table_sha256"] != expected_case_table_sha256: raise InputContractError("case table is not the registered formal table")
    req_new_cases = {c["case_id"]: c for c in case_table["new_point_cases"] if c["family"] == family}; req_anc_cases = {c["case_id"]: c for c in case_table["first_wave_anchor_cases"] if c["family"] == family}
    if not req_new_cases: raise InputContractError(f"family {family}: no 12-position cases in the case table (not applicable; no coverage record is issued)")
    if not partitions or any(not isinstance(p, VerifiedPartition) or not p.verified for p in partitions): raise InputContractError("only VerifiedPartition instances (verify_partition_run) enter the formal aggregation")
    for k in ("engine_version", "inventory_sha256", "script_sha256", "pins_sha256"):
        if not isinstance(expected_source.get(k), str) or not expected_source[k]: raise InputContractError(f"expected_source lacks {k}")
    all_sizes = sorted({c["size_id"] for c in req_new_cases.values()}); sizes_seen = []; cases = {}; statuses = {}; bases = set(); tol = case_table["contract"]["tolerance"]["match_rel_lt"]
    for i, p in enumerate(partitions):
        rm, rg, pr = p.run_manifest, p.registry, p.pc1_results; src = rm.get("source") or {}
        if any(src.get(k) != expected_source[k] for k in ("engine_version", "inventory_sha256", "script_sha256", "pins_sha256")): raise InputContractError(f"partition {i}: source differs from the expected source")
        if not (rm.get("family") == rg.get("family") == pr.get("family") == family): raise InputContractError(f"partition {i}: family differs")
        if rg.get("case_table_sha256") != expected_case_table_sha256 or pr.get("case_table_sha256") != expected_case_table_sha256: raise InputContractError(f"partition {i}: case-table SHA differs")
        sel = rm.get("selection") or {}; sz = list(sel.get("sizes") or all_sizes)
        if len(set(sz)) != len(sz) or any(x not in all_sizes for x in sz) or set(sz) & set(sizes_seen): raise InputContractError(f"partition {i}: sizes invalid / duplicate / overlapping")
        sizes_seen += sz
        exp_bases = {str(c["config_id"]) for c in req_new_cases.values() if c["size_id"] in sz}; exp_cases = {k for k, c in {**req_new_cases, **req_anc_cases}.items() if c["size_id"] in sz}
        if set(rg.get("configurations", {})) != exp_bases: raise InputContractError(f"partition {i}: registry configurations differ from the sizes' new bases")
        pcases = pr.get("cases") or {}
        if set(pcases) != exp_cases: raise InputContractError(f"partition {i}: evaluated cases differ from the sizes' required cases")
        derived = {}
        for k, v in pcases.items():
            ref = {**req_new_cases, **req_anc_cases}[k]; rel = v.get("rel")
            if v.get("evaluation") != "EVALUATED" or v.get("config_id") != ref["config_id"] or v.get("action") != ref["action"] or not isinstance(rel, float) or not np.isfinite(rel) or rel < 0 or v.get("match") != (rel < tol) or v.get("tolerance_match_rel_lt") != tol: raise InputContractError(f"partition {i}: case {k} inconsistent (evaluation / identity / rel / match)")
            derived.setdefault(str(ref["config_id"]), []).append(v)
        for cid, rs in derived.items():
            req = REQUIRED_ACTIONS[family]; st = dict(actions_required=req, actions_evaluated=sorted(x["action"] for x in rs), status=("PC1_PASS" if sorted(x["action"] for x in rs) == sorted(req) and all(x["match"] for x in rs) else ("PC1_FAIL" if sorted(x["action"] for x in rs) == sorted(req) else "PC1_PENDING")), max_rel=max(x["rel"] for x in rs))
            if (pr.get("configuration_status") or {}).get(cid) != st: raise InputContractError(f"partition {i}: stored configuration status for {cid} differs from the status re-derived from its cases")
            statuses[cid] = copy.deepcopy(st)
        cases.update(copy.deepcopy(pcases)); bases |= set(rg["configurations"])
    if sorted(sizes_seen) != all_sizes: raise InputContractError(f"partitions do not cover the family sizes: {sorted(sizes_seen)} vs {all_sizes}")
    if set(cases) != set(req_new_cases) | set(req_anc_cases) or bases != {str(c["config_id"]) for c in req_new_cases.values()}: raise InputContractError("union of partitions differs from the family required set")
    return copy.deepcopy(dict(schema="d3a_family_coverage_v3", family=family, sizes=all_sizes, partitions=[dict(run_dir=p.run_dir, document_sha256=p.document_sha256) for p in partitions], expected_source=dict(expected_source), case_table_sha256=expected_case_table_sha256, n_bases=len(bases), n_cases=len(cases), n_new_point_cases=len(req_new_cases), n_anchor_cases=len(req_anc_cases), configuration_status=statuses, n_pc1_pass=sum(v["status"] == "PC1_PASS" for v in statuses.values()), n_pc1_fail=sum(v["status"] == "PC1_FAIL" for v in statuses.values()), family_coverage_complete=True, note="formal coverage aggregation of verified partition runs (documents read once, hashed from the same bytes, bound to published identities and pins); per-configuration PC1 statuses re-derived; not itself a PC-1 acceptance"))
