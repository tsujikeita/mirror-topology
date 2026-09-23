# -*- coding: utf-8 -*-
"""D-2 tranche 2: bank SPECIFICATION (fixed before generation) + configuration bank GENERATOR (sharded, sidecar-bound, fresh-attempt / completed-cache, call inventory).
Specification (build_bank_spec -> d/d2_bank_spec.json, deterministic from the source-bound registry, the CRN table and the accepted D-1 registry):
  * per configuration: family / size / observer, evaluation IDs per registered_id_map (matched = config_id, native = config_id + 50000), the 3 configuration-specific roles
    (model_matched, model_native, ref_native) with their root SOURCE (D-1 covariance receipt: cov file / array SHA; ref_native from the configuration's own c_ct),
    the shared family role ref_matched (root of the fixed PR3 isotropic covariance), the evaluation CRN group / fitting group of the family, the two logical batches with
    cluster / row / rotation-index ranges, the physical shard plan (batch 0 = 1 shard of N0 rows; batch 1 = 3 shards of N0 rows each; shard -> global cluster range), the
    selections (float64 primary; float32 for the REQUIRED sensitivity subset only), and the fitting bank (purpose fitting, N_fit = 200,000, m = 100, batch 0 only).
  * required float32 subset (rules §12.5): per family and per system ONE configuration at N0 — the first observer of the smallest surviving size — fixed by immutable config_id;
    whole-range float32 is NOT part of the first wave (recorded as an author decision; may be added later as a separately scoped diagnostic).
  * W2 primary positions: the 27 immutable config_ids (E2/E7/E8), N_W2 = 200,000, m = 100, both paths (f64 / paired f32), whitening bound to the registered shared-null identity
    (asset payload SHA + pools npz file SHA); case-level stop / B_final / trigger remain a pre-use gate.
  * plan schema: BootstrapPlan / FittingPlan keys are the formal bootstrap keys (seeds = RULES.seeds, B = RULES.B, B_KDE = RULES.B_KDE), built once at the start of the formal
    calibration from the bank UIDs and kept identical until the target; NOT generated per threshold and NOT generated here.
  * pseudo column: purpose pseudo, n = RULES.n_pseudo, m = 1, generated and sealed by the Phase E driver set-up step (outside D-2).
Generator (generate_configuration_bank): for one configuration (or the family reference) and one batch, scans the roles on the family's evaluation latent (d2_rng.generate_from_latent),
writes each shard as an atomic .npz (T1/T2/AX/PL per role x selection + cid) with a sidecar (identity, ranges, UIDs, root SHAs, cov SHA, table SHA, array SHAs, environment) and,
after the last shard, a completion manifest; a CALL INVENTORY records the formal keys, replayed cluster range, roles, selections and table SHA of every generation call (the adapter
re-creates generators, so registry.creations / kernel.calls are not the record). Output directories are fresh per attempt; a completed cache is reused only after full
re-verification (arrays + sidecars + manifest), never by sidecar SHA alone; partial outputs are never published as complete."""
from __future__ import annotations
import copy, hashlib, json, os, time
from typing import Dict, List, Optional
import numpy as np
from .errors import InputContractError
from .rules_config import RULES
from .official_gate import B_KDE as _B_KDE, N_FIT as _N_FIT, M_FIT as _M_FIT
from .grid_manifest import FAMILY_CODES, SIZE_CODES, SIZE_VALUES, ConfigurationManifest
from .production import registered_id_map, NATIVE_OFFSET
from . import d2_rng
from .d2_rng import BATCHES, N0, N_MAX, M, group_for, uids_for, generate_from_latent, native_reference_root, iter_latent
from . import serialization as ser

N_FIT = int(_N_FIT); M_FIT = int(_M_FIT); N_W2 = 200_000; M_W2 = 100; SHARD_ROWS = N0
SHARED_NULL = dict(asset_sha256="8348d5f4733ae5a37e39f4aa88109626e5caab312b55bd108be7ec9e5daff3ba", file_sha256="cc67686744f513e3123de2fb8353d79491d4b1deaff2b8d9ecb5f93d0f95afb4", pools_npz_file_sha256="451f8bc5446c03956ba5598b326532584805488326b0623b009c5e7dc530c987", pools_npz_bytes=42573325)


def _sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
def _asha(a) -> str: return _sha(np.ascontiguousarray(a).tobytes())


def shard_plan() -> List[dict]:
    """Physical shards: batch 0 -> one shard; batch 1 -> three shards of N0 rows; shard index is a storage label, batch_id / rotation_index are the statistical identity."""
    plan = [dict(shard=0, batch_id=0, rows=[0, N0], clusters=[0, N0 // M], rotation_index=[0, N0 // M])]
    for i in range(3):
        r0 = N0 + i * SHARD_ROWS; plan.append(dict(shard=i + 1, batch_id=1, rows=[r0, r0 + SHARD_ROWS], clusters=[r0 // M, (r0 + SHARD_ROWS) // M], rotation_index=[i * (SHARD_ROWS // M), (i + 1) * (SHARD_ROWS // M)]))
    return plan


def build_bank_spec(man: ConfigurationManifest, table: dict, d1_registry: dict, master_seed: int) -> dict:
    man.validate(); idm = registered_id_map(man); cfgs = {}
    if table.get("master_seed") != master_seed: raise InputContractError("CRN table master seed differs")
    fams = sorted({c.family for c in man.configurations}, key=lambda f: FAMILY_CODES[f]); required_f32 = {}
    for fam in fams:
        cs = [c for c in man.configurations if c.family == fam]; smallest = min(cs, key=lambda c: (SIZE_VALUES[c.size_id], c.observer_id))
        required_f32[fam] = dict(matched=smallest.config_id, native=smallest.config_id + NATIVE_OFFSET, config_id=smallest.config_id, N="N0 (batch 0 only)")
    for c in man.configurations:
        d1 = d1_registry["configurations"].get(str(c.config_id))
        if d1 is None or d1["cache_key"] != c.cache_key or [float(v) for v in d1["x0_CT"]] != [float(v) for v in c.x0_CT]: raise InputContractError(f"D-1 registry entry missing / differs for config {c.config_id}")
        fam = c.family; f32 = c.config_id == required_f32[fam]["config_id"]
        cfgs[str(c.config_id)] = dict(config_id=c.config_id, family=fam, size_id=c.size_id, observer_id=c.observer_id, cache_key=c.cache_key, weight=c.weight,
            evaluation_ids=dict(matched=idm.matched[c.config_id], native=idm.native[c.config_id]),
            roles=dict(model_matched=dict(root="S_matched (principal root of the matched covariance)", source="D-1 intake"), model_native=dict(root="S_native (principal root of the native real-basis covariance)", source="D-1 intake"), ref_native=dict(root="diag(sqrt(c_l^CT) x 5/7/9) from this configuration's c_ct", source="D-1 intake (c_ct)")),
            shared_role=dict(ref_matched="family reference bank (root of the fixed PR3 isotropic covariance), same latent"),
            covariance=dict(cov_file=d1["cov_file"], cov_file_sha256=d1["cov_file_sha256"], cov_array_sha256=d1["cov_array_sha256"], intake_receipt="D1_aa089fa492bc"),
            crn=dict(evaluation_group=group_for(table, "evaluation", fam), fitting_group=group_for(table, "fitting", fam), wave_id=table["wave_id"]),
            batches={str(k): dict(rows=list(v), clusters=[v[0] // M, v[1] // M], rotation_index=[0, (v[1] - v[0]) // M]) for k, v in BATCHES.items()}, shards=shard_plan(),
            selections=dict(evaluation={"0": (["float64", "float32"] if f32 else ["float64"]), "1": ["float64"]}, required_f32_subset=f32, note="float32 only on batch 0 of the required subset (author decision: N0-only sensitivity); batch 1 is float64 for every configuration"),
            fitting=dict(purpose="fitting", N=N_FIT, m=M_FIT, batch_id=0, roles=["model_matched", "ref_matched", "model_native", "ref_native"], selections=["float64"]),
            w2_primary=(None if fam == "E1" else dict(group=group_for(table, "w2_independent", fam, c.size_id, c.config_id), N=N_W2, m=M_W2, paths=["float64", "float32"], whitening=SHARED_NULL)))
    fam_ref = {fam: dict(selections={"0": (["float64", "float32"] if any(v["config_id"] // 10000 == FAMILY_CODES[fam] for v in [required_f32[fam]]) else ["float64"]), "1": ["float64"]}, group=group_for(table, "evaluation", fam), role="ref_matched", note="family reference (PR3 isotropic root) on the family evaluation latent; paired float32 path only where a required-subset configuration of the family needs it (batch 0)") for fam in fams}
    spec = dict(schema="d2_bank_spec_v1", master_seed=int(master_seed), family_reference=fam_ref, wave_id=table["wave_id"], crn_table_sha256=table["table_sha256"], registry_sha256=man.registry_sha256, manifest_sha256=man.manifest_sha256, d1_registry_sha256=d1_registry.get("_sha256"), N0=N0, N_max=N_MAX, m=M, shard_rows=SHARD_ROWS,
                plan_schema=dict(bootstrap=dict(seeds=RULES.seeds, B=RULES.B, B_KDE=int(_B_KDE), key="formal bootstrap key (MASTER_SEED, wave, purpose, group, batch, seed_id, stream)", fixed="once at the start of the formal calibration from the bank UIDs; identical until the target; never per threshold; not generated by D-2"), fitting=dict(N=N_FIT, m=M_FIT, binding="per-configuration fitting bank SHA (FamilyInput.fitting_bindings)")),
                required_f32_subset=required_f32, whole_range_f32="NOT part of the first wave (author decision; separately scoped diagnostic if added)", pseudo_column=dict(purpose="pseudo", n=RULES.n_pseudo, m=1, owner="Phase E driver set-up (calibrate_sealed input); generated and sealed before the formal calibration; outside D-2"),
                w2=dict(primary_positions=27, families=["E2", "E7", "E8"], N=N_W2, m=M_W2, paths=["float64", "float32"], whitening=SHARED_NULL, case_level="stop / B_final / trigger remain a pre-use gate"),
                call_inventory="every generation call records (purpose, group, batch, key_rotation, key_gaussian, cluster range, roles, selections, chunk, table SHA)",
                configurations=cfgs)
    spec["spec_sha256"] = _sha(json.dumps({k: v for k, v in spec.items() if k != "spec_sha256"}, sort_keys=True).encode())
    # Public builder results must not expose SHARED_NULL or other caller inputs.
    return copy.deepcopy(spec)


def _is_int(v): return isinstance(v, int) and not isinstance(v, bool)


_CANON = {}


def canonical_context(table: Optional[dict] = None) -> dict:
    """Trusted sources of the first-wave bank specification: the source-bound GridRegistry / ConfigurationManifest (packet assets, SHA-verified by load_registry), the accepted
    D-1 registry (bytes bound to production.D1_REGISTERED_RECEIPT.registry_sha256) and the committed CRN table (payload-verified). The canonical spec is re-derived from them;
    a spec is accepted only if it EQUALS the canonical one (content, not just its own hash).
    Returned objects are detached snapshots; callers cannot edit the private reference."""
    import os
    from .grid_registry import load_registry; from .grid_manifest import build_configuration_manifest; from .production import D1_REGISTERED_RECEIPT
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if table is None:
        from .d2_rng import load_crn_table
        table, _ = load_crn_table(os.path.join(root, "d", "d2_crn_table.json"))
    # Capture and validate the input even on a cache hit. Neither caller-owned
    # tables nor returned snapshots may alias the private verification reference.
    table = copy.deepcopy(table)
    d2_rng._validated_table_groups(table)
    if d2_rng._table_sha(table) != table.get("table_sha256"):
        raise InputContractError("CRN table schema / payload SHA")
    key = table["table_sha256"]
    if key not in _CANON:
        reg = load_registry(os.path.join(root, "tests", "assets", "a7_circle_geometry.csv"), os.path.join(root, "tests", "assets", "a6_observer_design_points.json")); man = build_configuration_manifest(reg)
        p1 = os.path.join(root, "registered_assets", "d1", "d1_cov_registry.json"); b = open(p1, "rb").read()
        if _sha(b) != D1_REGISTERED_RECEIPT["registry_sha256"]: raise InputContractError("packet D-1 registry differs from the accepted registry SHA")
        d1 = json.loads(b.decode("utf-8")); d1["_sha256"] = D1_REGISTERED_RECEIPT["registry_sha256"]
        _CANON[key] = dict(table=table, registry=reg, manifest=man, d1_registry=d1, spec=build_bank_spec(man, table, d1, table["master_seed"]))
    return copy.deepcopy(_CANON[key])


def verify_bank_spec_content(s: dict, table: Optional[dict] = None) -> None:
    """Semantic verification of a bank spec dict: self hash, registered constants, CRN table binding, AND equality with the canonical spec re-derived from the trusted sources
    (source-bound manifest, accepted D-1 registry, CRN table). A self-consistent but different spec (other id set, prior, cache key, cross-configuration covariance, missing
    source binding, fitting/plan/W2 inconsistencies) is refused. Raises on the first inconsistency."""
    body = {k: v for k, v in s.items() if k != "spec_sha256"}
    if s.get("schema") != "d2_bank_spec_v1" or _sha(json.dumps(body, sort_keys=True).encode()) != s.get("spec_sha256"): raise InputContractError("bank spec schema / payload SHA")
    for k in ("registry_sha256", "manifest_sha256", "d1_registry_sha256", "crn_table_sha256"):
        if not (isinstance(s.get(k), str) and len(s[k]) == 64): raise InputContractError(f"bank spec lacks the source binding field {k}")
    ctx = canonical_context(table); canon = ctx["spec"]
    if table is None: table = ctx["table"]
    if s.get("crn_table_sha256") != table["table_sha256"]: raise InputContractError("bank spec is not bound to the supplied / committed CRN table")
    if s.get("registry_sha256") != ctx["registry"].registry_sha256 or s.get("manifest_sha256") != ctx["manifest"].manifest_sha256 or s.get("d1_registry_sha256") != ctx["d1_registry"]["_sha256"]: raise InputContractError("bank spec source bindings differ from the trusted sources")
    if s != canon:
        diff = [k for k in set(s) | set(canon) if s.get(k) != canon.get(k)]
        if "configurations" in diff:
            cd = [c for c in set(s.get("configurations") or {}) | set(canon["configurations"]) if (s.get("configurations") or {}).get(c) != canon["configurations"].get(c)]; diff = [d for d in diff if d != "configurations"] + [f"configurations:{c}" for c in sorted(cd)]
        raise InputContractError(f"bank spec differs from the canonical specification re-derived from the trusted sources: {sorted(diff)[:6]}")
    if s.get("N0") != N0 or s.get("N_max") != N_MAX or s.get("m") != M or s.get("shard_rows") != SHARD_ROWS or s.get("wave_id") != d2_rng.WAVE_ID or not _is_int(s.get("master_seed")): raise InputContractError("bank spec constants")
    if table is not None and (s.get("crn_table_sha256") != table.get("table_sha256") or s.get("master_seed") != table.get("master_seed") or s.get("wave_id") != table.get("wave_id")): raise InputContractError("bank spec is not bound to the supplied CRN table")
    cfgs = s.get("configurations") or {}
    if len(cfgs) != 30: raise InputContractError("bank spec must hold the 30 first-wave configurations")
    fam_of = {v: k for k, v in FAMILY_CODES.items()}; size_of = {v: k for k, v in SIZE_CODES.items()}; seen = set(); fams_seen = set()
    for key, c in cfgs.items():
        cid = c.get("config_id")
        if not _is_int(cid) or str(cid) != key or cid in seen: raise InputContractError(f"config key / id / duplicate: {key}")
        seen.add(cid); fc, sc, ob = cid // 10000, (cid // 100) % 100, cid % 100
        if fc not in fam_of or c.get("family") != fam_of[fc] or sc not in size_of or c.get("size_id") != size_of[sc] or c.get("observer_id") != (0 if fam_of[fc] == "E1" else ob): raise InputContractError(f"config {cid}: family / size / observer differ from the immutable id")   # id = 10000*family + 100*size + (position+1); observer_id is 0 for E1, position+1 otherwise
        fam = c["family"]; fams_seen.add(fam)
        if c.get("evaluation_ids") != dict(matched=cid, native=cid + NATIVE_OFFSET): raise InputContractError(f"config {cid}: evaluation ids")
        if sorted(c.get("roles") or {}) != ["model_matched", "model_native", "ref_native"] or "ref_matched" not in (c.get("shared_role") or {}): raise InputContractError(f"config {cid}: roles")
        cov = c.get("covariance") or {}
        if not all(isinstance(cov.get(k), str) and len(cov.get(k)) == 64 for k in ("cov_file_sha256", "cov_array_sha256")) or cov.get("intake_receipt") != "D1_aa089fa492bc": raise InputContractError(f"config {cid}: covariance source")
        crn = c.get("crn") or {}
        exp_e = group_for(table, "evaluation", fam) if table is not None else 1000 + FAMILY_CODES[fam]; exp_f = group_for(table, "fitting", fam) if table is not None else 2000 + FAMILY_CODES[fam]
        if crn.get("evaluation_group") != exp_e or crn.get("fitting_group") != exp_f or crn.get("wave_id") != s["wave_id"]: raise InputContractError(f"config {cid}: CRN groups")
        if c.get("batches") != {str(k): dict(rows=list(v), clusters=[v[0] // M, v[1] // M], rotation_index=[0, (v[1] - v[0]) // M]) for k, v in BATCHES.items()}: raise InputContractError(f"config {cid}: batches")
        if c.get("shards") != shard_plan(): raise InputContractError(f"config {cid}: shard plan")
        sel = c.get("selections") or {}; req = bool(sel.get("required_f32_subset"))
        if sel.get("evaluation") != {"0": (["float64", "float32"] if req else ["float64"]), "1": ["float64"]}: raise InputContractError(f"config {cid}: per-batch selections")
        if req != (s.get("required_f32_subset", {}).get(fam, {}).get("config_id") == cid): raise InputContractError(f"config {cid}: required subset flag")
        fit = c.get("fitting") or {}
        if fit.get("purpose") != "fitting" or fit.get("N") != N_FIT or fit.get("m") != M_FIT or fit.get("batch_id") != 0 or fit.get("selections") != ["float64"]: raise InputContractError(f"config {cid}: fitting")
        w2 = c.get("w2_primary")
        if fam == "E1":
            if w2 is not None: raise InputContractError("E1 has no W2 primary position")
        else:
            exp_g = group_for(table, "w2_independent", fam, c["size_id"], cid) if table is not None else 30000 + cid
            if not isinstance(w2, dict) or w2.get("group") != exp_g or w2.get("N") != N_W2 or w2.get("m") != M_W2 or w2.get("paths") != ["float64", "float32"] or w2.get("whitening") != SHARED_NULL: raise InputContractError(f"config {cid}: W2 primary")
    if fams_seen != set(FAMILY_CODES): raise InputContractError("bank spec must cover all registered families")
    rf = s.get("required_f32_subset") or {}
    if set(rf) != set(FAMILY_CODES): raise InputContractError("required f32 subset must name one configuration per family")
    for fam, v in rf.items():
        cid = v.get("config_id"); c = cfgs.get(str(cid))
        if c is None or c["family"] != fam or v.get("matched") != cid or v.get("native") != cid + NATIVE_OFFSET: raise InputContractError(f"required subset {fam}")
        others = [x for x in cfgs.values() if x["family"] == fam]; smallest = min(others, key=lambda x: (SIZE_VALUES[x["size_id"]], x["observer_id"]))
        if smallest["config_id"] != cid: raise InputContractError(f"required subset {fam}: must be the first observer of the smallest surviving size")
    fr = s.get("family_reference") or {}
    if set(fr) != set(FAMILY_CODES) or any(fr[f].get("group") != (group_for(table, "evaluation", f) if table is not None else 1000 + FAMILY_CODES[f]) or fr[f].get("selections") != {"0": ["float64", "float32"], "1": ["float64"]} or fr[f].get("role") != "ref_matched" for f in fr): raise InputContractError("family reference selections / groups")
    ps = s.get("pseudo_column") or {}
    if ps.get("n") != RULES.n_pseudo or ps.get("m") != 1 or ps.get("purpose") != "pseudo": raise InputContractError("pseudo column registration")
    pb = (s.get("plan_schema") or {}).get("bootstrap") or {}
    if pb.get("seeds") != RULES.seeds or pb.get("B") != RULES.B or pb.get("B_KDE") != int(_B_KDE): raise InputContractError("plan schema constants")
    w2s = s.get("w2") or {}
    if w2s.get("primary_positions") != 27 or w2s.get("families") != ["E2", "E7", "E8"] or w2s.get("whitening") != SHARED_NULL: raise InputContractError("W2 registration")


def load_bank_spec(path: str, expected_sha256: Optional[str] = None, table: Optional[dict] = None) -> dict:
    s = json.load(open(path))
    if expected_sha256 is not None and s.get("spec_sha256") != expected_sha256: raise InputContractError("bank spec SHA differs from the expected value")
    verify_bank_spec_content(s, table); return s


def bind_generation_inputs(registry, table: dict, spec: dict) -> None:
    """Generation-entry binding (before any numerical work): spec content + spec->table, table restoration == live registry (master seed, groups), actual keys carry the table seed."""
    verify_bank_spec_content(spec, table)
    from .d2_rng import _table_sha
    if _table_sha(table) != table.get("table_sha256"): raise InputContractError("CRN table payload SHA")
    if getattr(registry, "master_seed", None) != table["master_seed"]: raise InputContractError("live CRNRegistry master seed differs from the CRN table")
    live = registry.export_groups(); want = {int(g): dict(purpose=v["purpose"], wave_id=v["wave_id"], label=v["label"]) for g, v in table["groups"].items()}
    if live != want: raise InputContractError("live CRNRegistry groups differ from the CRN table")
    g0 = next(iter(want)); k = registry.rng_key(want[g0]["purpose"], table["wave_id"], g0, 0, "gaussian")
    if k[0] != table["master_seed"] or k[1] != table["wave_id"] or k[3] != g0: raise InputContractError("live registry key does not carry the table seed / wave / group")


class CallInventory:
    def __init__(self): self.calls = []
    def record(self, registry, purpose, group, batch_id, k0, k1, roles, selections, chunk, table_sha, wave_id=d2_rng.WAVE_ID):
        self.calls.append(dict(purpose=purpose, group=int(group), batch_id=int(batch_id), key_rotation=list(registry.rng_key(purpose, wave_id, group, batch_id, "rotation")), key_gaussian=list(registry.rng_key(purpose, wave_id, group, batch_id, "gaussian")), clusters=[int(k0), int(k1)], roles=list(roles), selections=list(selections), chunk_clusters=int(chunk), table_sha256=table_sha, t=time.time()))


def _atomic_write(path: str, data: bytes):
    tmp = path + ".part"
    with open(tmp, "wb") as fh: fh.write(data); fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, path)


EXPECTED_MEMBERS = ("T1", "T2", "AX", "PL")


def expected_member_set(roles, selections) -> set:
    return {"cid"} | {f"{r}__{sel}__{kk}" for r in roles for sel in selections for kk in EXPECTED_MEMBERS}


def generate_configuration_bank(kernel, registry, table: dict, spec: dict, config_id: Optional[int], roots: Dict[str, np.ndarray], batch_id: int, out_dir: str, inventory: CallInventory, selections=("float64",), scale: float = 1.0, chunk_clusters: int = d2_rng.CHUNK_CLUSTERS, env: Optional[dict] = None, family: Optional[str] = None) -> dict:
    """Generate ONE batch of ONE configuration (config_id) or of the family reference (config_id=None, roots={'ref_matched': S_PR3}, family=...) into out_dir (fresh attempt).
    Binding before numerics: spec content + spec->table + live registry (seed / groups / keys). Per-batch selections come from the spec (formal: must equal; scale<1 self-test may
    use a subset). Cluster allocation is exact per shard or refused. Every shard is validated in memory (member set, shapes, dtypes, finiteness, cid structure) before it is
    written; COMPLETE.json is published only after the shared validator has re-verified the whole directory against the candidate manifest."""
    if os.path.exists(out_dir): raise InputContractError("fresh-attempt contract: output directory must not exist")
    if not (isinstance(scale, (int, float)) and not isinstance(scale, bool) and 0 < scale <= 1): raise InputContractError("scale")
    if batch_id not in BATCHES: raise InputContractError("batch_id")
    bind_generation_inputs(registry, table, spec)
    if config_id is None:
        if family not in FAMILY_CODES: raise InputContractError("family required for the reference bank"); 
        fam = family; spec_sel = spec["family_reference"][fam]["selections"][str(batch_id)]; expected_roles = ("ref_matched",)
    else:
        if not _is_int(config_id) or str(config_id) not in spec["configurations"]: raise InputContractError("config_id not in the spec")
        c = spec["configurations"][str(config_id)]; fam = c["family"]; spec_sel = c["selections"]["evaluation"][str(batch_id)]; expected_roles = ("model_matched", "model_native", "ref_native")
        if family is not None and family != fam: raise InputContractError("family argument contradicts the configuration")
    sel = list(selections)
    if not sel or len(set(sel)) != len(sel) or any(x not in ("float64", "float32") for x in sel): raise InputContractError("selections")
    if scale == 1.0 and sel != spec_sel: raise InputContractError(f"selections {sel} differ from the specification for batch {batch_id}: {spec_sel}")
    # scale < 1 (self-test, formal=False) may use any valid selection set; it is never a formal bank and its sidecars/manifest carry formal=False
    if tuple(sorted(roots)) != tuple(sorted(expected_roles)): raise InputContractError(f"roles must be exactly {expected_roles}")
    group = group_for(table, "evaluation", fam); K_full = (BATCHES[batch_id][1] - BATCHES[batch_id][0]) // M; shards = [sh for sh in shard_plan() if sh["batch_id"] == batch_id]
    K = K_full if scale == 1.0 else int(round(K_full * scale))
    if K < 1 or K % len(shards) != 0: raise InputContractError(f"unsupported cluster count {K} for {len(shards)} shard(s): the batch must split exactly (choose another scale)")
    K_shard = K // len(shards); offset_rows = BATCHES[batch_id][0]; offset_clusters = offset_rows // M
    root_sha = {r: _asha(np.asarray(S, float)) for r, S in roots.items()}; inventory.record(registry, "evaluation", group, batch_id, 0, K, sorted(roots), sel, chunk_clusters, table["table_sha256"])
    out, cid, uids = generate_from_latent(kernel, roots, registry, "evaluation", group, batch_id, K, tuple(sel), m=M, chunk_clusters=chunk_clusters)
    members = expected_member_set(sorted(roots), sel)
    os.makedirs(out_dir); written = []
    for i, sh in enumerate(shards):
        k0, k1 = i * K_shard, (i + 1) * K_shard; r0, r1 = k0 * M, k1 * M; arrays = {"cid": np.ascontiguousarray(cid[r0:r1])}
        for (role, s_), d in out.items():
            for kk in EXPECTED_MEMBERS: arrays[f"{role}__{s_}__{kk}"] = np.ascontiguousarray(d[kk][r0:r1])
        _check_arrays(arrays, members, r1 - r0, k0, k1)                                                       # in-memory validation BEFORE writing
        import io; buf = io.BytesIO(); np.savez(buf, **arrays); data = buf.getvalue(); fname = f"{'ref' if config_id is None else 'cfg' + str(config_id)}_b{batch_id}_s{sh['shard']}.npz"; p = os.path.join(out_dir, fname); _atomic_write(p, data)
        side = dict(schema="d2_bank_shard_v1", family=fam, config_id=config_id, kind=("family_reference" if config_id is None else "configuration"), evaluation_ids=(None if config_id is None else spec["configurations"][str(config_id)]["evaluation_ids"]), purpose="evaluation", crn_group=group, wave_id=table["wave_id"], batch_id=batch_id, shard=sh["shard"],
                    rows=[r0, r1], clusters=[k0, k1], rotation_index=[k0, k1], global_rows=[offset_rows + r0, offset_rows + r1], global_clusters=[offset_clusters + k0, offset_clusters + k1], uids=[list(uids[k0].as_tuple()), list(uids[k1 - 1].as_tuple())], m=M, roles=sorted(roots), root_sha256=root_sha, selections=sel,
                    array_sha256={k: _asha(v) for k, v in arrays.items()}, file_sha256=_sha(data), bytes=len(data), table_sha256=table["table_sha256"], spec_sha256=spec["spec_sha256"], scale=scale, formal=(scale == 1.0), environment=env or {}, dtype=dict(T1="float64", T2="float64", AX="int32", PL="int32"))
        if config_id is not None: side["covariance"] = spec["configurations"][str(config_id)]["covariance"]
        _atomic_write(p + ".sidecar.json", json.dumps(side, indent=1).encode()); written.append(dict(file=fname, sidecar=fname + ".sidecar.json", file_sha256=side["file_sha256"], sidecar_sha256=_sha(open(p + ".sidecar.json", "rb").read()), rows=[r0, r1]))
    manifest = dict(schema="d2_bank_manifest_v1", family=fam, config_id=config_id, evaluation_ids=(None if config_id is None else spec["configurations"][str(config_id)]["evaluation_ids"]), purpose="evaluation", crn_group=group, wave_id=table["wave_id"], batch_id=batch_id, shards=written, roles=sorted(roots), root_sha256=root_sha, selections=sel, n_rows=K * M, n_clusters=K, m=M, complete=True, scale=scale, formal=(scale == 1.0), table_sha256=table["table_sha256"], spec_sha256=spec["spec_sha256"], master_seed=table["master_seed"], calls=inventory.calls[-1:])
    manifest["manifest_sha256"] = _sha(json.dumps({k: v for k, v in manifest.items() if k != "manifest_sha256"}, sort_keys=True).encode())
    _verify_bank_contents(out_dir, manifest, expected_roles=sorted(roots))                                        # shared validator on the candidate manifest + written shards BEFORE publication
    _atomic_write(os.path.join(out_dir, "COMPLETE.json"), json.dumps(manifest, indent=1).encode()); return manifest


def _check_arrays(arrays: dict, members: set, n: int, k0: int, k1: int, m: int = M) -> None:
    if set(arrays) != members: raise InputContractError(f"member set differs from roles x selections: missing {sorted(members - set(arrays))} extra {sorted(set(arrays) - members)}")
    cid = arrays["cid"]
    if cid.ndim != 1 or len(cid) != n or not np.issubdtype(cid.dtype, np.integer) or not np.array_equal(cid, np.repeat(np.arange(k0, k1), m)): raise InputContractError("cid must be the integer cluster index repeated m times in order")
    for k, v in arrays.items():
        if k == "cid": continue
        if v.ndim != 1 or len(v) != n: raise InputContractError(f"{k}: one-dimensional with {n} rows required")
        if k.endswith("__T1") or k.endswith("__T2"):
            if v.dtype != np.float64 or not np.isfinite(v).all(): raise InputContractError(f"{k}: float64 and finite required")
        elif v.dtype != np.int32: raise InputContractError(f"{k}: int32 required")


def _verify_bank_contents(out_dir: str, man: dict, expected_roles=None) -> None:
    """Shared writer/reader validator. Order: (1) the generation REQUEST schema of the manifest (selections, scale/formal, K derived from batch+scale, identity against the canonical
    spec / CRN table, full 6-element keys, chunk) -> (2) derived member set -> (3) every shard: bytes, sidecar<->manifest identity, ranges, UIDs, arrays."""
    from .registry import PURPOSE, STREAM
    body = {k: v for k, v in man.items() if k != "manifest_sha256"}
    if man.get("schema") != "d2_bank_manifest_v1" or _sha(json.dumps(body, sort_keys=True).encode()) != man.get("manifest_sha256") or man.get("complete") is not True: raise InputContractError("bank manifest schema / SHA / completeness")
    roles, sels = man.get("roles"), man.get("selections")
    if not (isinstance(sels, list) and sels and len(set(sels)) == len(sels) and all(x in ("float64", "float32") for x in sels)): raise InputContractError("manifest selections must be a non-empty list of distinct registered selections")
    if not (isinstance(roles, list) and roles and len(set(roles)) == len(roles)): raise InputContractError("manifest roles")
    if expected_roles is not None and sorted(roles) != sorted(expected_roles): raise InputContractError("bank roles differ")
    scale = man.get("scale")
    if not (isinstance(scale, (int, float)) and not isinstance(scale, bool) and np.isfinite(scale) and 0 < scale <= 1) or not isinstance(man.get("formal"), bool) or man["formal"] != (scale == 1.0): raise InputContractError("manifest scale / formal flag")
    purpose = man.get("purpose")
    if purpose not in ("evaluation", "fitting", "w2_independent") or man.get("batch_id") not in BATCHES or man.get("m") != (M if purpose == "evaluation" else (M_FIT if purpose == "fitting" else M_W2)): raise InputContractError("manifest constants")
    batch_id = man["batch_id"]
    if purpose == "evaluation":
        K_full = (BATCHES[batch_id][1] - BATCHES[batch_id][0]) // M; n_sh = len([sh for sh in shard_plan() if sh["batch_id"] == batch_id]); mm = M
    elif purpose == "fitting":
        if batch_id != 0 or sels != ["float64"]: raise InputContractError("fitting banks are batch 0 / float64 only")
        K_full = FIT_K; n_sh = 1; mm = M_FIT
    else:
        if batch_id != 0 or sels != ["float64", "float32"] or roles != ["model_matched"]: raise InputContractError("W2 position banks are batch 0 / both paths / matched model root only")
        K_full = N_W2 // M_W2; n_sh = 1; mm = M_W2
    K_req = K_full if scale == 1.0 else int(round(K_full * scale))
    if not _is_int(man.get("n_clusters")) or man["n_clusters"] != K_req or K_req < 1 or K_req % n_sh != 0 or man.get("n_rows") != K_req * mm: raise InputContractError(f"manifest cluster count {man.get('n_clusters')} does not follow from purpose {purpose} / batch {batch_id} / scale {scale} (expected {K_req})")
    # identity against the canonical specification / CRN table (trusted sources)
    ctx = canonical_context(); spec = ctx["spec"]; table = ctx["table"]
    if man.get("table_sha256") != table["table_sha256"] or man.get("spec_sha256") != spec["spec_sha256"] or man.get("master_seed") != table["master_seed"] or man.get("wave_id") != table["wave_id"]: raise InputContractError("manifest table / spec / seed / wave identity differs from the trusted sources")
    kind_cfg = man.get("config_id") is not None
    if kind_cfg:
        cid_ = man["config_id"]; c = spec["configurations"].get(str(cid_)) if _is_int(cid_) else None
        exp_roles = ["model_matched"] if purpose == "w2_independent" else ["model_matched", "model_native", "ref_native"]
        exp_group = (c["w2_primary"] or {}).get("group") if purpose == "w2_independent" else c["crn"]["evaluation_group" if purpose == "evaluation" else "fitting_group"]
        if c is None or man.get("family") != c["family"] or man.get("evaluation_ids") != c["evaluation_ids"] or roles != exp_roles or exp_group is None or man.get("crn_group") != exp_group: raise InputContractError("manifest configuration identity / roles / group differ from the canonical specification")
        if man["formal"] and purpose == "evaluation" and sels != c["selections"]["evaluation"][str(batch_id)]: raise InputContractError("formal manifest selections differ from the specification for this configuration / batch")
        cov_ref = c["covariance"]
    else:
        fam = man.get("family")
        if fam not in spec["family_reference"] or man.get("evaluation_ids") is not None or roles != ["ref_matched"] or man.get("crn_group") != (spec["family_reference"][fam]["group"] if purpose == "evaluation" else group_for(table, "fitting", fam)): raise InputContractError("manifest reference identity / roles / group differ from the canonical specification")
        if man["formal"] and purpose == "evaluation" and sels != spec["family_reference"][fam]["selections"][str(batch_id)]: raise InputContractError("formal reference selections differ from the specification for this batch")
        cov_ref = None
    if not isinstance(man.get("root_sha256"), dict) or set(man["root_sha256"]) != set(roles) or any(not (isinstance(v, str) and len(v) == 64) for v in man["root_sha256"].values()): raise InputContractError("manifest root SHA table")
    calls = man.get("calls") or []
    if len(calls) != 1: raise InputContractError("manifest must carry exactly one generation call")
    c = calls[0]
    if c.get("purpose") != purpose or c.get("group") != man.get("crn_group") or c.get("batch_id") != man["batch_id"] or c.get("clusters") != [0, man["n_clusters"]] or sorted(c.get("roles") or []) != roles or list(c.get("selections") or []) != sels or c.get("table_sha256") != man.get("table_sha256"): raise InputContractError("generation call differs from the manifest identity")
    for key, stream in (("key_rotation", "rotation"), ("key_gaussian", "gaussian")):
        k = c.get(key); want = [man.get("master_seed"), man.get("wave_id"), PURPOSE[purpose], man["crn_group"], man["batch_id"], STREAM[stream]]
        if not (isinstance(k, list) and len(k) == 6 and all(_is_int(x) for x in k) and k == want): raise InputContractError(f"generation call {key} differs from the manifest identity (all six elements incl. stream id)")
    if not _is_int(c.get("chunk_clusters")) or c["chunk_clusters"] < 1: raise InputContractError("generation call chunk must be a positive integer")
    members = expected_member_set(roles, sels); r_expect = 0; k_expect = 0; shards = man.get("shards") or []
    plan = [sh for sh in shard_plan() if sh["batch_id"] == man["batch_id"]] if purpose == "evaluation" else [dict(shard=0, batch_id=0)]
    if purpose == "w2_independent" and not kind_cfg: raise InputContractError("W2 position banks are configuration banks")
    if len(shards) != len(plan): raise InputContractError("shard count differs from the plan")
    for sh, pl in zip(shards, plan):
        p = os.path.join(out_dir, sh["file"]); sp = os.path.join(out_dir, sh["sidecar"])
        if not (os.path.exists(p) and os.path.exists(sp)) or _sha(open(p, "rb").read()) != sh["file_sha256"] or _sha(open(sp, "rb").read()) != sh["sidecar_sha256"]: raise InputContractError(f"shard {sh['file']}: bytes differ from the manifest")
        side = json.load(open(sp))
        for k in ("schema", "family", "config_id", "evaluation_ids", "purpose", "crn_group", "wave_id", "batch_id", "roles", "selections", "table_sha256", "spec_sha256", "scale", "formal", "root_sha256"):
            mk = "d2_bank_shard_v1" if k == "schema" else man.get(k)
            if side.get(k) != mk: raise InputContractError(f"shard {sh['file']}: sidecar field {k} differs from the manifest")
        if side.get("kind") != ("configuration" if kind_cfg else "family_reference") or side.get("dtype") != dict(T1="float64", T2="float64", AX="int32", PL="int32"): raise InputContractError(f"shard {sh['file']}: sidecar kind / dtype declaration")
        if kind_cfg and side.get("covariance") != cov_ref: raise InputContractError(f"shard {sh['file']}: sidecar covariance metadata differs from the canonical D-1 entry of this configuration")
        if not kind_cfg and "covariance" in side: raise InputContractError(f"shard {sh['file']}: reference shard carries covariance metadata")
        if side.get("shard") != pl["shard"] or side.get("m") != mm or side.get("file_sha256") != sh["file_sha256"] or side.get("rows") != sh["rows"]: raise InputContractError(f"shard {sh['file']}: shard identity")
        r0, r1 = side["rows"]; k0, k1 = side["clusters"]
        if r0 != r_expect or k0 != k_expect or r1 - r0 != (k1 - k0) * mm or k1 <= k0 or side.get("rotation_index") != [k0, k1]: raise InputContractError(f"shard {sh['file']}: ranges not contiguous / consistent")
        off_r, off_k = (BATCHES[man["batch_id"]][0], BATCHES[man["batch_id"]][0] // M) if purpose == "evaluation" else (0, 0)
        if side.get("global_rows") != [off_r + r0, off_r + r1] or side.get("global_clusters") != [off_k + k0, off_k + k1]: raise InputContractError(f"shard {sh['file']}: global ranges")
        exp_u0 = [man["wave_id"], PURPOSE[purpose], man["crn_group"], man["batch_id"], k0]; exp_u1 = exp_u0[:4] + [k1 - 1]
        if side.get("uids") != [exp_u0, exp_u1]: raise InputContractError(f"shard {sh['file']}: UID ends differ from the batch / rotation range")
        if set(side.get("array_sha256") or {}) != members: raise InputContractError(f"shard {sh['file']}: sidecar member set")
        with np.load(p, allow_pickle=False) as z:
            if set(z.files) != members: raise InputContractError(f"shard {sh['file']}: NPZ member set")
            arrays = {k: z[k] for k in z.files}
        _check_arrays(arrays, members, r1 - r0, k0, k1, mm)
        for k, s_ in side["array_sha256"].items():
            if _asha(arrays[k]) != s_: raise InputContractError(f"shard {sh['file']}: array {k} differs from its sidecar")
        r_expect, k_expect = r1, k1
    if r_expect != man["n_rows"] or k_expect != man["n_clusters"]: raise InputContractError("shards do not cover the manifest rows / clusters")


def verify_bank_dir(out_dir: str, expected_roles=None) -> dict:
    """Full re-verification of a COMPLETED bank directory (the ONLY route to reuse a cache): manifest SHA / schema / completeness, every shard's file + sidecar bytes, exact member
    set, 1-D shapes and dtypes, finiteness, cid structure, contiguous local + global ranges, UID ends, sidecar<->manifest identity, generation call <-> manifest identity.
    A partial directory has no COMPLETE.json and is refused."""
    mp = os.path.join(out_dir, "COMPLETE.json")
    if not os.path.exists(mp): raise InputContractError("bank directory is not complete (no completion manifest)")
    man = json.load(open(mp)); _verify_bank_contents(out_dir, man, expected_roles); return man


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# D-2 tranche 3a: fitting-purpose generation (same latent replay contract, purpose 'fitting', batch 0, N_fit rows) and the STRONG bank intake that assembles the consumer
# BankSupply from completed evaluation / reference / fitting cache directories. Nothing here trusts a sidecar alone: every directory is re-verified with verify_bank_dir
# (bytes, arrays, ranges, identity) and, in addition, cross-checked against the canonical spec / CRN table / D-1 roots supplied by the caller.
FIT_K = N_FIT // M_FIT


def generate_fitting_bank(kernel, registry, table: dict, spec: dict, config_id: Optional[int], roots: Dict[str, np.ndarray], out_dir: str, inventory: CallInventory, scale: float = 1.0, chunk_clusters: int = d2_rng.CHUNK_CLUSTERS, env: Optional[dict] = None, family: Optional[str] = None) -> dict:
    """Fitting bank for one configuration (roles model_matched / model_native / ref_native) or the family reference (ref_matched): purpose 'fitting', group = the family fitting group,
    batch 0, K = N_fit / m clusters, selection float64 only, one shard. Same fresh-attempt / in-memory validation / validate-then-publish contract as the evaluation generator."""
    if os.path.exists(out_dir): raise InputContractError("fresh-attempt contract: output directory must not exist")
    if not (isinstance(scale, (int, float)) and not isinstance(scale, bool) and 0 < scale <= 1): raise InputContractError("scale")
    bind_generation_inputs(registry, table, spec)
    if config_id is None:
        if family not in FAMILY_CODES: raise InputContractError("family required for the reference fitting bank")
        fam = family; expected_roles = ("ref_matched",)
    else:
        if not _is_int(config_id) or str(config_id) not in spec["configurations"]: raise InputContractError("config_id not in the spec")
        fam = spec["configurations"][str(config_id)]["family"]; expected_roles = ("model_matched", "model_native", "ref_native")
        if family is not None and family != fam:
            raise InputContractError("family argument differs from the fitting configuration")
    if tuple(sorted(roots)) != tuple(sorted(expected_roles)): raise InputContractError(f"roles must be exactly {expected_roles}")
    group = group_for(table, "fitting", fam); K = FIT_K if scale == 1.0 else int(round(FIT_K * scale))
    if K < 1: raise InputContractError("cluster count")
    root_sha = {r: _asha(np.asarray(S, float)) for r, S in roots.items()}; inventory.record(registry, "fitting", group, 0, 0, K, sorted(roots), ["float64"], chunk_clusters, table["table_sha256"])
    out, cid, uids = generate_from_latent(kernel, roots, registry, "fitting", group, 0, K, ("float64",), m=M_FIT, chunk_clusters=chunk_clusters)
    members = expected_member_set(sorted(roots), ["float64"]); arrays = {"cid": np.ascontiguousarray(cid)}
    for (role, s_), d in out.items():
        for kk in EXPECTED_MEMBERS: arrays[f"{role}__{s_}__{kk}"] = np.ascontiguousarray(d[kk])
    _check_arrays(arrays, members, K * M_FIT, 0, K, M_FIT)
    os.makedirs(out_dir); import io; buf = io.BytesIO(); np.savez(buf, **arrays); data = buf.getvalue(); fname = f"{'ref' if config_id is None else 'cfg' + str(config_id)}_fit_s0.npz"; p = os.path.join(out_dir, fname); _atomic_write(p, data)
    side = dict(schema="d2_bank_shard_v1", family=fam, config_id=config_id, kind=("family_reference" if config_id is None else "configuration"), evaluation_ids=(None if config_id is None else spec["configurations"][str(config_id)]["evaluation_ids"]), purpose="fitting", crn_group=group, wave_id=table["wave_id"], batch_id=0, shard=0, rows=[0, K * M_FIT], clusters=[0, K], rotation_index=[0, K], global_rows=[0, K * M_FIT], global_clusters=[0, K], uids=[list(uids[0].as_tuple()), list(uids[K - 1].as_tuple())], m=M_FIT, roles=sorted(roots), root_sha256=root_sha, selections=["float64"], array_sha256={k: _asha(v) for k, v in arrays.items()}, file_sha256=_sha(data), bytes=len(data), table_sha256=table["table_sha256"], spec_sha256=spec["spec_sha256"], scale=scale, formal=(scale == 1.0), environment=env or {}, dtype=dict(T1="float64", T2="float64", AX="int32", PL="int32"))
    if config_id is not None: side["covariance"] = spec["configurations"][str(config_id)]["covariance"]
    _atomic_write(p + ".sidecar.json", json.dumps(side, indent=1).encode())
    manifest = dict(schema="d2_bank_manifest_v1", family=fam, config_id=config_id, evaluation_ids=side["evaluation_ids"], purpose="fitting", crn_group=group, wave_id=table["wave_id"], batch_id=0, shards=[dict(file=fname, sidecar=fname + ".sidecar.json", file_sha256=side["file_sha256"], sidecar_sha256=_sha(open(p + ".sidecar.json", "rb").read()), rows=[0, K * M_FIT])], roles=sorted(roots), root_sha256=root_sha, selections=["float64"], n_rows=K * M_FIT, n_clusters=K, m=M_FIT, complete=True, scale=scale, formal=(scale == 1.0), table_sha256=table["table_sha256"], spec_sha256=spec["spec_sha256"], master_seed=table["master_seed"], calls=inventory.calls[-1:])
    manifest["manifest_sha256"] = _sha(json.dumps({k: v for k, v in manifest.items() if k != "manifest_sha256"}, sort_keys=True).encode())
    _verify_bank_contents(out_dir, manifest, expected_roles=sorted(roots)); _atomic_write(os.path.join(out_dir, "COMPLETE.json"), json.dumps(manifest, indent=1).encode()); return manifest


def _load_role(dir_: str, man: dict, role: str, sel: str = "float64") -> dict:
    parts = {kk: [] for kk in EXPECTED_MEMBERS}; cids = []
    # Consume the exact bytes whose digest is bound to the verified manifest.
    # Reopening a pathname after verification must not substitute different data.
    import io
    for sh in man["shards"]:
        with open(os.path.join(dir_, sh["file"]), "rb") as fh:
            data = fh.read()
        if _sha(data) != sh["file_sha256"]:
            raise InputContractError(f"shard {sh['file']}: bytes changed before consumption")
        with np.load(io.BytesIO(data), allow_pickle=False) as z:
            for kk in EXPECTED_MEMBERS: parts[kk].append(z[f"{role}__{sel}__{kk}"])
            cids.append(z["cid"])
    return dict({kk: np.concatenate(v) for kk, v in parts.items()}, cid=np.concatenate(cids))


def _verified_d1_bank_sidecar(config_id: int, ctx: dict, supplied: dict) -> dict:
    """Bind the supplied sidecar to this configuration's accepted D-1 metadata.
    This validates metadata only; it does not regenerate physical roots or grant
    a new D-2 production receipt. The latter remain wrapper/pre-use gates.
    """
    from .production import D1_REGISTERED_RECEIPT
    if not isinstance(supplied, dict):
        raise InputContractError("cov_manifest must be a D-1 sidecar dictionary")
    snapshot = copy.deepcopy(supplied)
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "registered_assets", "d1"))
    with open(os.path.join(base, "d1_receipt.json"), "rb") as fh:
        receipt_bytes = fh.read()
    if _sha(receipt_bytes) != D1_REGISTERED_RECEIPT["receipt_file_sha256"]:
        raise InputContractError("D-1 receipt bytes differ from the registered receipt")
    receipt = json.loads(receipt_bytes)
    cov_file = ctx["d1_registry"]["configurations"][str(config_id)]["cov_file"]
    side_file = cov_file + ".manifest.json"
    expected = receipt["registered"]["files"].get(os.path.basename(side_file))
    with open(os.path.join(base, side_file), "rb") as fh:
        side_bytes = fh.read()
    if expected is None or _sha(side_bytes) != expected:
        raise InputContractError("D-1 sidecar bytes differ from the accepted receipt")
    genuine = json.loads(side_bytes)
    # Canonical JSON compares complete metadata while permitting dictionary order
    # and original JSON whitespace to differ. No caller field is repaired silently.
    try:
        equal = (json.dumps(snapshot, sort_keys=True, allow_nan=False)
                 == json.dumps(genuine, sort_keys=True, allow_nan=False))
    except (TypeError, ValueError) as ex:
        raise InputContractError("cov_manifest is not finite JSON metadata") from ex
    if not equal:
        raise InputContractError("cov_manifest differs from this configuration's accepted D-1 sidecar")
    return snapshot


def intake_registered_bank(config_id: int, system: str, eval_dirs: Dict[int, str], ref_dirs: Dict[int, str], fit_dir: str, ref_fit_dir: str, roots: Dict[str, np.ndarray], cov_manifest: dict, table: Optional[dict] = None, formal: bool = True):
    """STRONG intake: assemble the consumer BankSupply of (config_id, system) from completed cache directories — evaluation batches {0: dir, 1: dir} of the configuration,
    the family reference batches {0: dir, 1: dir}, the configuration fitting dir and the reference fitting dir. Every directory is re-verified (verify_bank_dir: bytes / arrays /
    ranges / identity against the canonical spec and CRN table) and cross-checked: same family / group / table / spec, root SHAs equal the CALLER's roots (D-1 intake for the
    configuration, PR3 isotropic root for the reference), batch coverage exact ({0,1}), reference and configuration on the same latent (identical cid / row counts per batch),
    fitting banks paired (same K, same cluster ids), formal flags as required. Returns BankSupply with T1/T2 model/ref (concatenated batch 0 then batch 1), cluster UIDs
    (formal ClusterUID per cluster), batches = {0:(0,N0),1:(N0,N_max)} (or the scaled equivalents), FittingBank(model X, ref X, cid). The stored pass/formal flags are never
    the acceptance: everything is recomputed here."""
    from .production import BankSupply; from .orchestrator import FittingBank; from .registry import CRNRegistry
    if system not in ("matched", "native"): raise InputContractError("system")
    if not isinstance(formal, (bool, np.bool_)):
        raise InputContractError("formal must be a boolean")
    formal = bool(formal)
    required_roots = ("model_matched", "model_native", "ref_native", "ref_matched")
    if not isinstance(roots, dict) or any(r not in roots for r in required_roots):
        raise InputContractError("caller must supply the four roots (D-1 intake + PR3 isotropic)")
    want = {}
    for r in required_roots:
        a = np.asarray(roots[r])
        if a.shape != (21, 21) or a.dtype.kind not in "iuf" or not np.isfinite(a).all():
            raise InputContractError(f"root {r}: expected a finite real numeric 21x21 matrix")
        a = np.array(a, dtype=np.float64, order="C", copy=True)
        if not np.isfinite(a).all():
            raise InputContractError(f"root {r}: not representable as finite float64")
        want[r] = _asha(a)
    ctx = canonical_context(table); spec = ctx["spec"]; tab = ctx["table"]
    if not _is_int(config_id) or str(config_id) not in spec["configurations"]: raise InputContractError("config_id")
    c = spec["configurations"][str(config_id)]; fam = c["family"]; model_role = f"model_{system}"; ref_role = "ref_native" if system == "native" else "ref_matched"
    cov_manifest = _verified_d1_bank_sidecar(config_id, ctx, cov_manifest)
    if cov_manifest.get("cov_file_sha256") != c["covariance"]["cov_file_sha256"] or cov_manifest.get("cov_array_sha256") != c["covariance"]["cov_array_sha256"]:
        raise InputContractError("D-1 sidecar and canonical specification have different covariance hashes")
    if set(eval_dirs) != {0, 1} or set(ref_dirs) != {0, 1}: raise InputContractError("evaluation / reference batches {0, 1} are both required")
    mans = {b: verify_bank_dir(eval_dirs[b], ("model_matched", "model_native", "ref_native")) for b in (0, 1)}; rmans = {b: verify_bank_dir(ref_dirs[b], ("ref_matched",)) for b in (0, 1)}
    fman = verify_bank_dir(fit_dir, ("model_matched", "model_native", "ref_native")); rfman = verify_bank_dir(ref_fit_dir, ("ref_matched",))
    for b in (0, 1):
        for m_, kind in ((mans[b], "evaluation"), (rmans[b], "reference")):
            if m_["batch_id"] != b or m_["purpose"] != "evaluation" or m_["family"] != fam or m_["crn_group"] != c["crn"]["evaluation_group"] or m_["table_sha256"] != tab["table_sha256"] or m_["spec_sha256"] != spec["spec_sha256"]: raise InputContractError(f"{kind} batch {b}: identity differs from the configuration / canonical sources")
            if formal and not m_["formal"]: raise InputContractError(f"{kind} batch {b}: not a formal bank")
        if mans[b]["config_id"] != config_id: raise InputContractError("evaluation directory belongs to another configuration")
        if mans[b]["n_clusters"] != rmans[b]["n_clusters"] or mans[b]["scale"] != rmans[b]["scale"]: raise InputContractError(f"batch {b}: reference and configuration banks are not on the same latent range")
    if (mans[1]["n_clusters"] != 3 * mans[0]["n_clusters"]
            or mans[1]["n_rows"] != 3 * mans[0]["n_rows"]
            or mans[1]["scale"] != mans[0]["scale"]):
        raise InputContractError("evaluation batches must be one common-scale N0 prefix plus a 3*N0 extension")
    for m_, kind in ((fman, "fitting"), (rfman, "reference fitting")):
        if m_["purpose"] != "fitting" or m_["family"] != fam or m_["crn_group"] != c["crn"]["fitting_group"] or m_["table_sha256"] != tab["table_sha256"] or m_["spec_sha256"] != spec["spec_sha256"] or (formal and not m_["formal"]): raise InputContractError(f"{kind}: identity / formal")
    if fman["config_id"] != config_id or fman["n_clusters"] != rfman["n_clusters"]: raise InputContractError("fitting banks are not paired for this configuration")
    for m_ in (mans[0], mans[1], fman):
        if any(m_["root_sha256"][r] != want[r] for r in ("model_matched", "model_native", "ref_native")): raise InputContractError("stored configuration roots differ from the caller's D-1 roots")
    for m_ in (rmans[0], rmans[1], rfman):
        if m_["root_sha256"]["ref_matched"] != want["ref_matched"]: raise InputContractError("stored reference root differs from the caller's isotropic root")
    # assemble
    T1m, T2m, T1r, T2r, uids, batches = [], [], [], [], [], {}; off = 0
    for b in (0, 1):
        em = _load_role(eval_dirs[b], mans[b], model_role); rr = _load_role(ref_dirs[b], rmans[b], "ref_matched") if system == "matched" else _load_role(eval_dirs[b], mans[b], "ref_native")
        if not np.array_equal(em["cid"], rr["cid"]): raise InputContractError(f"batch {b}: model / reference cluster structure differ")
        n = len(em["cid"]); T1m.append(em["T1"]); T2m.append(em["T2"]); T1r.append(rr["T1"]); T2r.append(rr["T2"]); batches[b] = (off, off + n); off += n
        K = mans[b]["n_clusters"]; uids += [CRNRegistry.cluster_uid(tab["wave_id"], "evaluation", c["crn"]["evaluation_group"], b, i) for i in range(K)]
    fm = _load_role(fit_dir, fman, model_role); fr = _load_role(ref_fit_dir, rfman, "ref_matched") if system == "matched" else _load_role(fit_dir, fman, "ref_native")
    if not np.array_equal(fm["cid"], fr["cid"]): raise InputContractError("fitting model / reference cluster structure differ")
    fit = FittingBank(np.c_[fm["T1"], fm["T2"]], np.c_[fr["T1"], fr["T2"]], fm["cid"].astype(np.int64))
    supply = BankSupply(config_id, system, np.concatenate(T1m), np.concatenate(T2m), np.concatenate(T1r), np.concatenate(T2r), uids, M, batches, fit, cov_manifest=copy.deepcopy(cov_manifest))
    return supply, dict(scope="strong intake: directories re-verified (bytes/arrays/ranges/identity), roots == caller's D-1 / isotropic roots, reference on the same latent, fitting paired; formal=%s" % formal, batches=batches, n_clusters={b: mans[b]["n_clusters"] for b in (0, 1)}, fitting_clusters=fman["n_clusters"], manifests=dict(eval={b: mans[b]["manifest_sha256"] for b in (0, 1)}, ref={b: rmans[b]["manifest_sha256"] for b in (0, 1)}, fit=fman["manifest_sha256"], ref_fit=rfman["manifest_sha256"]))


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# D-2 tranche 3b: W2 primary position banks (purpose w2_independent; one CRN group per immutable position; N_W2 = 200,000 rows; m = 100; paired float64 / float32 paths;
# the role is the configuration's matched model root only). Raw T1/T2 (both selections) are stored; whitening with the registered shared-null mu / W is applied at the W2 intake
# (never a different W), so the bank identity does not depend on any whitening object. Same fresh-attempt / in-memory validation / validate-then-publish contract.
W2_K = N_W2 // M_W2


def generate_w2_position_bank(kernel, registry, table: dict, spec: dict, config_id: int, root_matched: np.ndarray, out_dir: str, inventory: CallInventory, scale: float = 1.0, chunk_clusters: int = d2_rng.CHUNK_CLUSTERS, env: Optional[dict] = None) -> dict:
    if os.path.exists(out_dir): raise InputContractError("fresh-attempt contract: output directory must not exist")
    if not (isinstance(scale, (int, float)) and not isinstance(scale, bool) and np.isfinite(scale) and 0 < scale <= 1): raise InputContractError("scale")
    bind_generation_inputs(registry, table, spec)
    if not _is_int(config_id) or str(config_id) not in spec["configurations"]: raise InputContractError("config_id not in the spec")
    c = spec["configurations"][str(config_id)]; fam = c["family"]
    if c.get("w2_primary") is None: raise InputContractError(f"config {config_id} ({fam}) has no W2 primary position")
    a = np.asarray(root_matched)
    if a.shape != (21, 21) or not np.issubdtype(a.dtype, np.number) or np.iscomplexobj(a) or not np.isfinite(a).all(): raise InputContractError("root must be a finite real numeric (21,21) array")
    S = np.asarray(a, float)
    if not np.isfinite(S).all(): raise InputContractError("root not finite after conversion")
    group = c["w2_primary"]["group"]; sel = ["float64", "float32"]; K = W2_K if scale == 1.0 else int(round(W2_K * scale))
    if K < 1: raise InputContractError("cluster count")
    roots = dict(model_matched=S); root_sha = {r: _asha(v) for r, v in roots.items()}; inventory.record(registry, "w2_independent", group, 0, 0, K, sorted(roots), sel, chunk_clusters, table["table_sha256"])
    out, cid, uids = generate_from_latent(kernel, roots, registry, "w2_independent", group, 0, K, tuple(sel), m=M_W2, chunk_clusters=chunk_clusters)
    members = expected_member_set(sorted(roots), sel); arrays = {"cid": np.ascontiguousarray(cid)}
    for (role, s_), d in out.items():
        for kk in EXPECTED_MEMBERS: arrays[f"{role}__{s_}__{kk}"] = np.ascontiguousarray(d[kk])
    _check_arrays(arrays, members, K * M_W2, 0, K, M_W2)
    os.makedirs(out_dir); import io; buf = io.BytesIO(); np.savez(buf, **arrays); data = buf.getvalue(); fname = f"cfg{config_id}_w2_s0.npz"; p = os.path.join(out_dir, fname); _atomic_write(p, data)
    side = dict(schema="d2_bank_shard_v1", family=fam, config_id=config_id, kind="configuration", evaluation_ids=c["evaluation_ids"], purpose="w2_independent", crn_group=group, wave_id=table["wave_id"], batch_id=0, shard=0, rows=[0, K * M_W2], clusters=[0, K], rotation_index=[0, K], global_rows=[0, K * M_W2], global_clusters=[0, K], uids=[list(uids[0].as_tuple()), list(uids[K - 1].as_tuple())], m=M_W2, roles=sorted(roots), root_sha256=root_sha, selections=sel, array_sha256={k: _asha(v) for k, v in arrays.items()}, file_sha256=_sha(data), bytes=len(data), table_sha256=table["table_sha256"], spec_sha256=spec["spec_sha256"], scale=scale, formal=(scale == 1.0), environment=env or {}, dtype=dict(T1="float64", T2="float64", AX="int32", PL="int32"), covariance=c["covariance"], whitening="applied at the W2 intake with the registered shared-null mu / W (identity in spec.w2.whitening); raw T stored here")
    _atomic_write(p + ".sidecar.json", json.dumps(side, indent=1).encode())
    manifest = dict(schema="d2_bank_manifest_v1", family=fam, config_id=config_id, evaluation_ids=c["evaluation_ids"], purpose="w2_independent", crn_group=group, wave_id=table["wave_id"], batch_id=0, shards=[dict(file=fname, sidecar=fname + ".sidecar.json", file_sha256=side["file_sha256"], sidecar_sha256=_sha(open(p + ".sidecar.json", "rb").read()), rows=[0, K * M_W2])], roles=sorted(roots), root_sha256=root_sha, selections=sel, n_rows=K * M_W2, n_clusters=K, m=M_W2, complete=True, scale=scale, formal=(scale == 1.0), table_sha256=table["table_sha256"], spec_sha256=spec["spec_sha256"], master_seed=table["master_seed"], calls=inventory.calls[-1:])
    manifest["manifest_sha256"] = _sha(json.dumps({k: v for k, v in manifest.items() if k != "manifest_sha256"}, sort_keys=True).encode())
    _verify_bank_contents(out_dir, manifest, expected_roles=sorted(roots)); _atomic_write(os.path.join(out_dir, "COMPLETE.json"), json.dumps(manifest, indent=1).encode()); return manifest


def registered_whitening() -> dict:
    """The registered shared-null whitening (mu, W) read from registered_assets/b3_2_shared_null_asset.json with its bytes bound to SHARED_NULL.file_sha256 and its payload SHA to
    SHARED_NULL.asset_sha256; returns an independent copy (mu (2,), W (2,2), float64) plus the identity and array SHAs."""
    import os
    from .w2_shared import SharedNullAsset
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")); p = os.path.join(root, "registered_assets", "b3_2_shared_null_asset.json"); b = open(p, "rb").read()
    if _sha(b) != SHARED_NULL["file_sha256"]: raise InputContractError("registered shared-null asset file differs from SHARED_NULL.file_sha256")
    asset = SharedNullAsset(**ser.loads(b.decode("utf-8"))); asset.validate()
    if asset.sha256 != SHARED_NULL["asset_sha256"] or asset.payload_sha() != SHARED_NULL["asset_sha256"]: raise InputContractError("registered shared-null asset payload differs from SHARED_NULL.asset_sha256")
    w = asset.identity["whitening"]; mu = np.array(w["mu"], dtype=np.float64); W = np.array(w["W"], dtype=np.float64)
    if mu.shape != (2,) or W.shape != (2, 2) or not np.isfinite(mu).all() or not np.isfinite(W).all(): raise InputContractError("registered whitening shape / finiteness")
    return dict(mu=mu, W=W, identity=dict(SHARED_NULL), mu_sha256=_asha(mu), W_sha256=_asha(W))


def intake_w2_position_bank(config_id: int, dir_: str, root_matched: np.ndarray, mu: np.ndarray, W: np.ndarray, whitening_identity: dict, table: Optional[dict] = None, formal: bool = True):
    """Strong intake of a W2 position bank: directory re-verified, identity against the canonical spec (position group, config, roles, selections), root SHA == caller's
    matched root, whitening identity == the registered shared-null identity of the spec (mu / W are applied here; a different W is refused by identity, not by closeness).
    Returns (PositionBank f64, PositionBank f32-path, info)."""
    from .positions import PositionBank
    if not isinstance(formal, bool): raise InputContractError("formal must be a bool")
    ctx = canonical_context(table); spec = ctx["spec"]
    if not _is_int(config_id) or str(config_id) not in spec["configurations"] or spec["configurations"][str(config_id)].get("w2_primary") is None: raise InputContractError("config_id has no W2 primary position")
    c = spec["configurations"][str(config_id)]; man = verify_bank_dir(dir_, ("model_matched",))
    if man["purpose"] != "w2_independent" or man["config_id"] != config_id or man["crn_group"] != c["w2_primary"]["group"] or man["selections"] != ["float64", "float32"] or (formal and not man["formal"]): raise InputContractError("W2 bank identity / formal")
    S = np.asarray(root_matched)
    if S.shape != (21, 21) or not np.isrealobj(S) or not np.isfinite(S).all() or man["root_sha256"]["model_matched"] != _asha(np.asarray(S, float)): raise InputContractError("stored W2 root differs from the caller's matched root")
    if whitening_identity != c["w2_primary"]["whitening"] or whitening_identity != SHARED_NULL: raise InputContractError("whitening identity differs from the registered shared-null identity")
    # the caller's mu / W must be the registered VALUES (not just the identifier): real numeric, finite, exact equality with the registered snapshot; the snapshot is what is applied
    ma, Wa = np.asarray(mu), np.asarray(W)
    for name, a_, shp in (("mu", ma, (2,)), ("W", Wa, (2, 2))):
        if a_.shape != shp or a_.dtype.kind not in "iuf" or not np.isfinite(a_).all(): raise InputContractError(f"whitening {name}: real numeric finite array of shape {shp} required")
    regw = registered_whitening()
    if not (np.array_equal(np.asarray(ma, float), regw["mu"]) and np.array_equal(np.asarray(Wa, float), regw["W"])): raise InputContractError("whitening mu / W differ from the registered shared-null values (identity alone is not the binding)")
    mu = regw["mu"]; W = regw["W"]
    d64 = _load_role(dir_, man, "model_matched", "float64"); d32 = _load_role(dir_, man, "model_matched", "float32")
    if not np.array_equal(d64["cid"], d32["cid"]): raise InputContractError("paired paths differ in cluster structure")
    Tw64 = (np.c_[d64["T1"], d64["T2"]] - mu) @ W.T; Tw32 = (np.c_[d32["T1"], d32["T2"]] - mu) @ W.T; cid = d64["cid"].astype(np.int64)
    return PositionBank(config_id, Tw64, cid), PositionBank(config_id, Tw32, cid), dict(manifest_sha256=man["manifest_sha256"], n_clusters=man["n_clusters"], whitening=dict(mu_sha256=regw["mu_sha256"], W_sha256=regw["W_sha256"], identity=regw["identity"]), scope="raw T re-verified from the cache; whitened with the registered shared-null mu/W VALUES (bound by file/payload SHA); case-level stop/B_final/trigger remain a pre-use gate")
