# -*- coding: utf-8 -*-
"""D-3 tranche 2b: 108-position covariance receipt, consumption-time covariance intake, the FORMAL 12-position profile (grid identity + gate), plan fixation and bank spec v2.

RECEIPT (`registered_assets/d3/d3_covariance_receipt.json`, schema d3_covariance_receipt_v1): one entry per 12-position configuration of E2/E7/E8 (3 sizes x 12 = 36 per
family, 108 in all), bound to the registered config map (da1e68bc...), the registered twelve assets, the D-1 registered receipt (first-wave anchors, positions 01-03: 27
covariances reused by fixed SHA) and the D-3a registered assets (positions 04-12: 81 covariances registered by ledger/coverage). Every entry carries the covariance file /
raw-array identity, geometry (x0_CT, cache_key), origin, and the PC-1 status re-derived from the D-3a coverage (anchors: anchor-diagnostic status; new points: configuration
status). `consumption_allowed` is True only for PC1_PASS. E1 keeps its 3 first-wave configurations (no 12-position stage; not in this receipt).
INTAKE (`intake_twelve_covariance`): consumption-time re-verification (the receipt / ledger snapshots do not make the filesystem immutable): receipt re-derived and compared,
file bytes and raw-array SHA recomputed, frozen loader (t1_engine / t2b2_bridge verified by SHA) applied, real-basis symmetry / PSD, matched and native principal roots with
the registered hard gate — the same contract as the D-1 intake (production.intake_registered_covariance, to which anchors are delegated).
PROFILE: `build_twelve_size_input` -> FamilyInput of exactly 12 configurations of one family/size/system, weight 1/12, evaluation ids from the config map, and a TWELVE grid
identity (stage="twelve"; superset of the first-wave identity fields so that the existing official gate applies: sizes / size_weights / evaluation_to_config / cache_keys /
cov_bound / id_map_rule + config_map_sha256 / twelve_assets_sha256 / position_index / covariance_receipt_sha256). `assemble_twelve_family` -> the all-size FamilyInput per
system (weight = registered size prior x 1/12 = 1/36 for 3 surviving sizes) through twelve_eval.assemble_all_sizes, with the family identity attached.
`twelve_official_gate` = official_gate (registered N0 / N_max / m / B / B_KDE / N_fit / bank-plan UID order / environment) + 12-position requirements (stage, 12 per size,
full surviving-size scope, every configuration covariance-bound to the receipt with PC1_PASS, matched/native pairing, plan identity shared by first-wave and added
configurations of the family). PLAN FIXATION (`fix_family_plans`): the five-seed BootstrapPlan / FittingPlan of a family are built ONCE from the bank cluster UIDs with the
formal keys (MASTER_SEED, wave 1, purpose, family group, batch, seed, stream) and are shared by old and new configurations of the same family (same family latent);
their identity (plan ids, rng keys, multiplicity SHAs) is recorded and must be unchanged until the target evaluation. BANK SPEC v2 (`build_bank_spec_v2`, d/d3_bank_spec.json):
the generation request of D-3b — 81 new configurations (f64 only, family evaluation / fitting latent, batches 0/1, roles from the D-3 intake, covariance from the receipt,
NO W2 position bank, NO new f32 subset) and the 27 first-wave configurations + family references consumed as FIXED D-2 assets (ledger identities; never regenerated).
Nothing here generates banks or PC-1 numbers; consumption of a PC1_FAIL / PENDING covariance is refused (asset layer)."""
from __future__ import annotations
import copy, hashlib, io, json, os, shutil, tempfile
from dataclasses import replace
from typing import Dict, List, Optional, Tuple
import numpy as np
from .errors import InputContractError
from .grid_manifest import FAMILY_CODES, SIZE_CODES
from .production import NATIVE_OFFSET, SYSTEMS, BankSupply, D1_REGISTERED_RECEIPT, _GRID_FIELDS, _verified_frozen_loader, intake_registered_covariance
from .orchestrator import ConfigBank, FamilyInput
from .bootstrap_plan import BootstrapPlan, FittingPlan, bank_sha256, BOOTSTRAP_STREAM
from .registry import PURPOSE
from .types import as_uid
from .rules_config import RULES
from .d3_assets import intake_registered_d3a_assets
from .d3_stage import _map_payload_sha

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RECEIPT_SCHEMA = "d3_covariance_receipt_v1"
BANK_SPEC_V2_SCHEMA = "d3_bank_spec_v2"
TWELVE_FAMILIES = ("E2", "E7", "E8")
N_POS = 12
TWELVE_GRID_FIELDS = _GRID_FIELDS | {"stage", "config_map_sha256", "twelve_assets_sha256", "position_index", "covariance_receipt_sha256"}
# trusted D-2 ledger identity (accepted D-2 generation ledger; outer receipt registered_assets/d2/d2_outer_receipt.json ledger.ledger_file_sha256)
D2_REGISTERED_LEDGER = dict(commit="19106efb7338094666b5723fc177aa0a190f6359", engine_version="0.79.0", ledger_file_sha256="07574dfa58dcabdf42955b8cc90cd7adf8fa581ae8075587e540c68f07263555")
_VERIFIED_RECEIPTS: Dict[str, dict] = {}     # receipt payload SHA -> receipt verified by re-derivation from the registered inputs (populated only by verify_d3_covariance_receipt)
_CTX_TOKEN = object()
PLAN_SCHEMA_V2 = dict(schema="d3_plan_schema_v2", bootstrap=dict(seeds=RULES.seeds, B=RULES.B, purpose="evaluation", key="(MASTER_SEED, wave 1, purpose_id, family evaluation group, batch, seed_id, BOOTSTRAP_STREAM)", strata="batch 0 = N0 prefix clusters; batch 1 = extension clusters; UID order = family latent order"),
                      fitting=dict(seeds=RULES.seeds, purpose_id=FittingPlan.PURPOSE_ID, key="(MASTER_SEED, wave 1, 300, family fitting group, 0, seed_id, BOOTSTRAP_STREAM)", K="N_fit / m_fit clusters"),
                      sharing="within a family, first-wave (D-2) and added (D-3b) configurations of both systems share the SAME plan objects / identities (same family latent => identical cluster UIDs); evaluation and fitting stay separate purposes",
                      fixation="built once at the start of the formal calibration from the bank UIDs; identity (plan ids, rng keys, multiplicity SHAs) recorded and unchanged through the target evaluation; never per threshold; no unrecorded keys")


def _sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
def _fsha(p: str) -> str:
    with open(p, "rb") as fh: return _sha(fh.read())
def _hex64(v) -> bool: return isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)
def _int(v, what):
    if isinstance(v, bool) or not isinstance(v, (int, np.integer)): raise InputContractError(f"{what} must be an integer")
    return int(v)
def _payload_sha(doc: dict, key: str) -> str: return _sha(json.dumps({k: v for k, v in doc.items() if k != key}, sort_keys=True, allow_nan=False).encode())
def _json(path: str, what: str) -> dict:
    try:
        with open(path, "rb") as fh: v = json.loads(fh.read().decode("utf-8"), parse_constant=lambda c: (_ for _ in ()).throw(InputContractError(f"{what}: non-finite constant")))
    except (OSError, ValueError) as e: raise InputContractError(f"{what}: unreadable ({type(e).__name__})")
    if not isinstance(v, dict): raise InputContractError(f"{what}: object expected")
    return v


# ------------------------------------------------------------------------------------------------------------------------------------ receipt
def _bound_config_map(root: str) -> Tuple[dict, dict]:
    pins = _json(os.path.join(root, "d", "d3_pins.json"), "d3 pins"); cm = _json(os.path.join(root, "d", "d3_config_map.json"), "config map")
    if _map_payload_sha(cm) != cm.get("map_sha256") or cm["map_sha256"] != pins.get("config_map_sha256"): raise InputContractError("config map differs from the registered pins")
    return pins, cm


def build_d3_covariance_receipt(phaseb_root: Optional[str] = None) -> dict:
    """108-position covariance receipt from the registered inputs only (config map, D-1 receipt/registry, D-3a ledger/coverage via the registered intake). Deterministic."""
    root = os.path.abspath(phaseb_root or _ROOT); pins, cm = _bound_config_map(root); RC = D1_REGISTERED_RECEIPT
    d1 = os.path.join(root, "registered_assets", "d1"); rpath, gpath = os.path.join(d1, "d1_receipt.json"), os.path.join(d1, "d1_cov_registry.json")
    if _fsha(rpath) != RC["receipt_file_sha256"] or _fsha(gpath) != RC["registry_sha256"]: raise InputContractError("D-1 receipt / registry bytes differ from the trusted constants")
    reg1 = _json(gpath, "D-1 registry"); rc = _json(rpath, "D-1 receipt")
    assets = intake_registered_d3a_assets(root)
    positions = {}; e1 = []
    for r in cm["configurations"]:
        cid = _int(r["config_id"], "config_id"); fam = r["family"]
        if fam == "E1": e1.append(cid); continue
        if fam not in TWELVE_FAMILIES: raise InputContractError(f"config {cid}: unknown family")
        base = dict(config_id=cid, family=fam, size_id=r["size_id"], position_index=_int(r["position_index"], "position_index"), display_suffix=r["display_suffix"], origin=r["origin"], x0_CT=[float(v) for v in r["x0_CT"]], cache_key=r["cache_key"], shape_params=dict(r["shape_params"]), evaluation_ids=dict(r["evaluation_ids"]), weight_family=float(r["weight_family"]), weight_within_size=float(r["weight_within_size"]))
        status = assets.coverage[fam]["configuration_status"].get(str(cid))
        if not isinstance(status, dict) or status.get("status") not in ("PC1_PASS", "PC1_FAIL", "PC1_PENDING"): raise InputContractError(f"config {cid}: PC-1 status missing from the registered coverage")
        if r["origin"] == "first_wave":
            c = reg1["configurations"].get(str(cid))
            if c is None or c["cache_key"] != r["cache_key"] or [float(v) for v in c["x0_CT"]] != base["x0_CT"] or c["family"] != fam or c["size_id"] != r["size_id"]: raise InputContractError(f"config {cid}: D-1 registry entry differs from the config map")
            fname = os.path.basename(c["cov_file"])
            if rc["registered"]["files"].get(fname) != c["cov_file_sha256"]: raise InputContractError(f"config {cid}: D-1 receipt does not list the covariance file identity")
            base.update(source="first_wave_D1", receipt=RC["id"], registered_file="registered_assets/d1/" + c["cov_file"], cov_file_sha256=c["cov_file_sha256"], cov_array_sha256=c["cov_array_sha256"], pc1_status=status["status"], pc1_role="first_wave_anchor_diagnostic", pc1_actions=list(status.get("actions_evaluated") or []), pc1_max_rel=status.get("max_rel"))
        elif r["origin"] == "twelve_added":
            b = assets.base_covariances.get(str(cid))
            if b is None or b["family"] != fam or b["size_id"] != r["size_id"] or [float(v) for v in b["x0_CT"]] != base["x0_CT"]: raise InputContractError(f"config {cid}: D-3a registered base differs from the config map")
            base.update(source="twelve_added_D3a", receipt="D3A_" + assets.ledger_sha256[:12], registered_file=b["registered_file"], cov_file_sha256=b["cov_file_sha256"], cov_array_sha256=b["cov_array_sha256"], pc1_status=status["status"], pc1_role="new_point", pc1_actions=list(status.get("actions_evaluated") or []), pc1_max_rel=status.get("max_rel"))
        else: raise InputContractError(f"config {cid}: unknown origin {r['origin']!r}")
        base["consumption_allowed"] = base["pc1_status"] == "PC1_PASS"; positions[str(cid)] = base
    if len(positions) != 108 or len(e1) != 3: raise InputContractError(f"receipt must cover 108 twelve-position configurations (+3 E1 first-wave): got {len(positions)} / {len(e1)}")
    doc = dict(schema=RECEIPT_SCHEMA, config_map_sha256=cm["map_sha256"], registry_sha256=cm["registry_sha256"], first_wave_manifest_sha256=cm["first_wave_manifest_sha256"], twelve_assets_sha256=cm["twelve_assets_sha256"], case_table_sha256=pins["case_table_sha256"],
               d1=dict(receipt_id=RC["id"], receipt_file_sha256=RC["receipt_file_sha256"], registry_sha256=RC["registry_sha256"], frozen_loaders=dict(RC["frozen_loaders"])),
               d3a=dict(ledger_sha256=assets.ledger_sha256, coverage_sha256=assets.coverage_sha256, generation_commit=assets.source_lock["commit"], generation_engine=assets.source_lock["engine_version"]),
               counts=dict(positions=len(positions), first_wave_reused=sum(v["source"] == "first_wave_D1" for v in positions.values()), twelve_added=sum(v["source"] == "twelve_added_D3a" for v in positions.values()), pc1_pass=sum(v["pc1_status"] == "PC1_PASS" for v in positions.values()), pc1_fail=sum(v["pc1_status"] == "PC1_FAIL" for v in positions.values()), consumption_allowed=sum(v["consumption_allowed"] for v in positions.values())),
               e1_first_wave_only=sorted(e1), positions=positions, note="asset-layer receipt: PC1_PASS re-derived from the registered D-3a coverage; consumption re-verifies bytes (intake_twelve_covariance); not a physical acceptance")
    doc["receipt_sha256"] = _payload_sha(doc, "receipt_sha256"); return copy.deepcopy(doc)


def verify_d3_covariance_receipt(doc: dict, phaseb_root: Optional[str] = None) -> dict:
    """Accepted only if it EQUALS the receipt re-derived from the registered inputs (payload SHA + full content)."""
    if not isinstance(doc, dict) or doc.get("schema") != RECEIPT_SCHEMA or _payload_sha(doc, "receipt_sha256") != doc.get("receipt_sha256"): raise InputContractError("covariance receipt schema / payload SHA")
    fresh = build_d3_covariance_receipt(phaseb_root)
    if fresh != doc: raise InputContractError("covariance receipt differs from the re-derivation from the registered inputs")
    _VERIFIED_RECEIPTS[fresh["receipt_sha256"]] = copy.deepcopy(fresh); return fresh


def load_registered_receipt(phaseb_root: Optional[str] = None, expected_sha256: Optional[str] = None) -> dict:
    root = os.path.abspath(phaseb_root or _ROOT); p = os.path.join(root, "registered_assets", "d3", "d3_covariance_receipt.json")
    doc = _json(p, "registered covariance receipt")
    if expected_sha256 is not None and doc.get("receipt_sha256") != expected_sha256: raise InputContractError("registered covariance receipt identity differs")
    return verify_d3_covariance_receipt(doc, root)


def intake_twelve_covariance(config_id, phaseb_root: Optional[str] = None, mt_root: Optional[str] = None, receipt: Optional[dict] = None) -> dict:
    """Consumption-time intake of a 12-position covariance (E2/E7/E8). Anchors are delegated to the D-1 intake; added points are re-verified against the receipt + registered
    D-3a assets: bytes, raw array SHA, frozen loader, real-basis symmetry / PSD, matched / native principal roots (hard gate). PC1_FAIL / PENDING is refused."""
    root = os.path.abspath(phaseb_root or _ROOT); cid = _int(config_id, "config_id")
    doc = verify_d3_covariance_receipt(receipt, root) if receipt is not None else load_registered_receipt(root)
    e = doc["positions"].get(str(cid))
    if e is None: raise InputContractError(f"config {cid}: not a 12-position covariance of the receipt")
    if e["consumption_allowed"] is not True or e["pc1_status"] != "PC1_PASS": raise InputContractError(f"config {cid}: PC-1 status {e['pc1_status']} (formal consumption forbidden)")
    if mt_root is None: raise InputContractError("mt_root (frozen loader checkout) is required")
    if e["source"] == "first_wave_D1":
        from .grid_registry import load_registry
        reg = load_registry(os.path.join(root, "tests", "assets", "a7_circle_geometry.csv"), os.path.join(root, "tests", "assets", "a6_observer_design_points.json"))
        out = intake_registered_covariance(cid, reg, os.path.join(root, "registered_assets", "d1"), mt_root)
        if out["cov_file_sha256"] != e["cov_file_sha256"] or out["cov_array_sha256"] != e["cov_array_sha256"] or out["cache_key"] != e["cache_key"]: raise InputContractError(f"config {cid}: D-1 intake identity differs from the receipt")
        out.update(receipt_d3=doc["receipt_sha256"], position_index=e["position_index"], origin=e["source"], pc1_status=e["pc1_status"]); return out
    assets = intake_registered_d3a_assets(root); b = assets.require_pc1_pass(cid)
    if b["cov_file_sha256"] != e["cov_file_sha256"] or b["cov_array_sha256"] != e["cov_array_sha256"] or b["registered_file"] != e["registered_file"]: raise InputContractError(f"config {cid}: registered D-3a identity differs from the receipt")
    p = os.path.join(root, e["registered_file"]); raw = open(p, "rb").read(); fsha = _sha(raw)
    if fsha != e["cov_file_sha256"]: raise InputContractError(f"config {cid}: covariance bytes differ from the receipt")
    arr = np.load(io.BytesIO(raw), allow_pickle=False); asha = _sha(np.ascontiguousarray(arr).tobytes())
    if asha != e["cov_array_sha256"] or arr.shape != (21, 21): raise InputContractError(f"config {cid}: raw array SHA / shape differ from the receipt")
    t1, loader_id = _verified_frozen_loader(mt_root, D1_REGISTERED_RECEIPT["frozen_loaders"]); from .legacy_kernel import LegacyKernel
    # The loader consumes the SAME bytes that were authenticated: the captured snapshot is written to an isolated file, re-read and re-hashed, and only that path is loaded
    # (the original path is never re-opened after authentication; the filesystem is not assumed immutable).
    tmpd = tempfile.mkdtemp(prefix="d3_cov_snapshot_")
    try:
        tp = os.path.join(tmpd, os.path.basename(p))
        with open(tp, "wb") as fh: fh.write(raw); fh.flush(); os.fsync(fh.fileno())
        with open(tp, "rb") as fh: back = fh.read()
        if _sha(back) != fsha: raise InputContractError("snapshot write-back differs from the authenticated bytes")
        Mx, Cr, meta = t1.load_cov_full(tp, 4)
        with open(tp, "rb") as fh: after = fh.read()
        if _sha(after) != fsha: raise InputContractError("snapshot changed while the loader read it")
    finally: shutil.rmtree(tmpd, ignore_errors=True)
    if meta.get("cov_array_sha256") != asha: raise InputContractError("loader array SHA differs")
    ev = np.linalg.eigvalsh((Cr + Cr.T) / 2)
    if not (np.isfinite(Cr).all() and np.abs(Cr - Cr.T).max() < 1e-12 * max(1.0, np.abs(Cr).max()) and ev.min() > -1e-12 * ev.max()): raise InputContractError("real-basis covariance not symmetric / PSD")
    k = LegacyKernel(mt_root); C_M, c_ct = k.matched(Cr); S_M, iM = k.psqrt(C_M); S_N, iN = k.psqrt(Cr)
    for name, info in (("matched", iM), ("native", iN)):
        if not (info["clip"] == 0 and info["lambda_min"] > 0 and info["sym"] < 1e-12 and info["recon"] < 1e-10): raise InputContractError(f"principal root hard gate failed ({name}): {info}")
    return dict(config_id=cid, family=e["family"], size_id=e["size_id"], position_index=e["position_index"], cache_key=e["cache_key"], x0_CT=list(e["x0_CT"]), cov_file_sha256=fsha, cov_array_sha256=asha, receipt=e["receipt"], receipt_d3=doc["receipt_sha256"], origin=e["source"], pc1_status=e["pc1_status"],
                trusted_anchors=dict(ledger_sha256=assets.ledger_sha256, coverage_sha256=assets.coverage_sha256), loader=loader_id, C_real=Cr, C_matched=C_M, c_ct=c_ct, S_matched=S_M, S_native=S_N, roots_info=dict(matched=iM, native=iN), eig=dict(min=float(ev.min()), max=float(ev.max())),
                scope="re-verified at load (receipt re-derived, registered D-3a assets re-verified, bytes / raw array SHA, frozen loader, symmetry / PSD, principal roots); PC-1 status carried, not re-evaluated")


# ------------------------------------------------------------------------------------------------------------------------------------ verified context
class TwelveContext:
    """Sealed, verified context of the formal 12-position profile: registered pins; config map EQUAL to its re-derivation from the source-bound registry / first-wave manifest /
    receipt-bound twelve assets; covariance receipt EQUAL to its re-derivation and equal to the pins identity; CRN table (payload SHA == D-2 pins); canonical D-2 bank spec v1
    (equal to its re-derivation, == D-2 pins); D-2 generation ledger bytes == trusted accepted identity. Created only by twelve_context(); views are deep copies."""
    __slots__ = ("_d", "_seal")
    def __init__(self, d, *, _token=None):
        if _token is not _CTX_TOKEN: raise InputContractError("TwelveContext must be created by twelve_context()")
        object.__setattr__(self, "_d", d); object.__setattr__(self, "_seal", _CTX_TOKEN)
    def __setattr__(self, n, v): raise AttributeError("TwelveContext is immutable")
    @property
    def verified(self): return self._seal is _CTX_TOKEN
    @property
    def root(self): return self._d["root"]
    @property
    def pins(self): return copy.deepcopy(self._d["pins"])
    @property
    def config_map(self): return copy.deepcopy(self._d["config_map"])
    @property
    def receipt(self): return copy.deepcopy(self._d["receipt"])
    @property
    def table(self): return copy.deepcopy(self._d["table"])
    @property
    def d2_spec(self): return copy.deepcopy(self._d["d2_spec"])
    @property
    def d2_ledger(self): return copy.deepcopy(self._d["d2_ledger"])
    @property
    def registry(self): return self._d["registry"]
    @property
    def twelve_assets(self): return self._d["twelve_assets"]
    @property
    def identities(self): return dict(registry_sha256=self._d["config_map"]["registry_sha256"], manifest_sha256=self._d["config_map"]["first_wave_manifest_sha256"], config_map_sha256=self._d["config_map"]["map_sha256"], twelve_assets_sha256=self._d["config_map"]["twelve_assets_sha256"], covariance_receipt_sha256=self._d["receipt"]["receipt_sha256"], crn_table_sha256=self._d["table"]["table_sha256"], d2_spec_sha256=self._d["d2_spec"]["spec_sha256"], d2_ledger_file_sha256=self._d["d2_ledger_sha256"])


def twelve_context(phaseb_root: Optional[str] = None) -> TwelveContext:
    from .grid_registry import load_registry
    from .grid_manifest import build_configuration_manifest
    from .twelve_assets import intake_registered_twelve_assets
    from .d3_stage import verify_config_map
    from .d2_rng import load_crn_table
    from . import d2_bank
    root = os.path.abspath(phaseb_root or _ROOT); pins, cm = _bound_config_map(root)
    reg = load_registry(os.path.join(root, "tests", "assets", "a7_circle_geometry.csv"), os.path.join(root, "tests", "assets", "a6_observer_design_points.json")); man = build_configuration_manifest(reg)
    ta = intake_registered_twelve_assets(os.path.join(root, "registered_assets", "b3_2_twelve_assets.json"), reg, "B3_2A_7240c06f255c")
    cm = verify_config_map(cm, reg, man, ta)
    if cm["registry_sha256"] != reg.registry_sha256 or cm["first_wave_manifest_sha256"] != man.manifest_sha256 or pins.get("registry_sha256") != reg.registry_sha256: raise InputContractError("config map / pins are not bound to the source-bound registry")
    if not _hex64(pins.get("covariance_receipt_sha256")): raise InputContractError("d3 pins lack the covariance receipt identity")
    rc = load_registered_receipt(root, pins["covariance_receipt_sha256"])
    if rc["config_map_sha256"] != cm["map_sha256"] or rc["registry_sha256"] != reg.registry_sha256 or rc["twelve_assets_sha256"] != cm["twelve_assets_sha256"]: raise InputContractError("covariance receipt is not bound to the verified config map")
    d2p = _json(os.path.join(root, "d", "d2_pins.json"), "d2 pins")
    table, _ = load_crn_table(os.path.join(root, "d", "d2_crn_table.json"), d2p.get("crn_table_sha256"))
    d2s = d2_bank.load_bank_spec(os.path.join(root, "d", "d2_bank_spec.json"), d2p.get("bank_spec_sha256"), table)
    lp = os.path.join(root, "registered_assets", "d2", "d2_generation_ledger.json"); lb = open(lp, "rb").read()
    if _sha(lb) != D2_REGISTERED_LEDGER["ledger_file_sha256"]: raise InputContractError("D-2 generation ledger bytes differ from the trusted accepted identity")
    d2l = json.loads(lb.decode("utf-8"))
    if d2l.get("schema") != "d2_generation_ledger_v1" or d2l.get("source_lock", {}).get("commit") != "8b5e6102f0088afbf69b10aaa9e90af4a63e07e2": raise InputContractError("D-2 ledger schema / source lock")
    if d2s["crn_table_sha256"] != table["table_sha256"] or d2s["registry_sha256"] != reg.registry_sha256 or d2s["manifest_sha256"] != man.manifest_sha256: raise InputContractError("D-2 bank spec is not bound to the same table / registry / manifest")
    return TwelveContext(dict(root=root, pins=pins, config_map=cm, receipt=rc, table=table, d2_spec=d2s, d2_ledger=d2l, d2_ledger_sha256=_sha(lb), registry=reg, twelve_assets=ta), _token=_CTX_TOKEN)


def _require_ctx(ctx) -> TwelveContext:
    if not isinstance(ctx, TwelveContext) or not ctx.verified: raise InputContractError("a verified TwelveContext (twelve_context()) is required for the formal 12-position profile")
    return ctx


# ------------------------------------------------------------------------------------------------------------------------------------ profile
def _verified_receipt(sha: str) -> dict:
    """The receipt behind a grid identity must be a VERIFIED registered receipt (re-derived from the registered inputs), never a caller dict."""
    if not _hex64(sha): raise InputContractError("covariance receipt identity")
    rc = _VERIFIED_RECEIPTS.get(sha)
    if rc is None:
        try: rc = load_registered_receipt(_ROOT, sha)
        except InputContractError: raise InputContractError("covariance receipt identity is not a verified registered receipt")
    return rc


def validate_twelve_grid_identity(gi, family, system, evaluation_ids, prior=None):
    """12-position grid identity: exact field inventory; bound to a VERIFIED registered receipt (map / registry / twelve-asset identities must equal the receipt's); 12 configurations
    per size (suffix 01-12), evaluation ids by the registered rule, position bijection, equal size prior; EVERY configuration's covariance binding EQUAL to the receipt entry
    (file / array SHA, origin by position, receipt id, PC1_PASS, consumption allowed); weights = size weight / 12."""
    if not isinstance(gi, dict) or set(gi) != TWELVE_GRID_FIELDS or gi.get("stage") != "twelve": raise InputContractError("twelve grid identity field inventory")
    if family not in TWELVE_FAMILIES or system not in SYSTEMS or gi["family"] != family or gi["system"] != system: raise InputContractError("twelve grid identity family/system mismatch")
    for k in ("registry_sha256", "manifest_sha256", "config_map_sha256", "twelve_assets_sha256", "covariance_receipt_sha256"):
        if not _hex64(gi[k]): raise InputContractError(f"twelve grid identity {k}")
    rc = _verified_receipt(gi["covariance_receipt_sha256"])
    if gi["config_map_sha256"] != rc["config_map_sha256"] or gi["registry_sha256"] != rc["registry_sha256"] or gi["manifest_sha256"] != rc["first_wave_manifest_sha256"] or gi["twelve_assets_sha256"] != rc["twelve_assets_sha256"]: raise InputContractError("twelve grid identity source identities differ from the verified receipt")
    sizes = gi["sizes"]
    if not isinstance(sizes, list) or not sizes or len(set(sizes)) != len(sizes) or not set(sizes) <= set(SIZE_CODES): raise InputContractError("twelve grid identity size inventory")
    sw = gi["size_weights"]
    if not isinstance(sw, dict) or set(sw) != set(sizes) or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) or abs(float(v) - 1 / len(sizes)) > 1e-15 for v in sw.values()): raise InputContractError("twelve grid identity size weights differ from the registered equal prior")
    offset = 0 if system == "matched" else NATIVE_OFFSET
    conf_to_size = {10000 * FAMILY_CODES[family] + 100 * SIZE_CODES[z] + p + 1: z for z in sizes for p in range(N_POS)}
    expected = {cid + offset: cid for cid in conf_to_size}
    ids = [_int(v, "evaluation id") for v in evaluation_ids]
    mp = gi["evaluation_to_config"]
    if not isinstance(mp, dict) or {_int(k, "evaluation id"): _int(v, "config id") for k, v in mp.items()} != expected or len(set(ids)) != len(ids) or set(ids) != set(expected): raise InputContractError("twelve grid identity mapping does not describe the evaluated configurations")
    if gi["id_map_rule"] != f"matched=config_id; native=config_id+{NATIVE_OFFSET}": raise InputContractError("twelve grid identity id rule mismatch")
    pi = gi["position_index"]
    if not isinstance(pi, dict) or set(pi) != set(expected) or any(_int(v, "position index") != (expected[e] % 100) - 1 for e, v in pi.items()): raise InputContractError("twelve grid identity position index differs from the id suffix rule")
    keys = gi["cache_keys"]
    if not isinstance(keys, dict) or set(keys) != set(expected) or any(not _hex64(v) for v in keys.values()): raise InputContractError("twelve grid identity cache-key inventory")
    cb = gi["cov_bound"]
    if not isinstance(cb, dict) or set(cb) != set(expected): raise InputContractError("twelve profile requires the covariance binding of EVERY configuration")
    for e, v in cb.items():
        cid = expected[e]; ent = rc["positions"].get(str(cid))
        if ent is None or v != _cov_binding(ent) or keys[e] != ent["cache_key"] or ent["position_index"] != pi[e]: raise InputContractError(f"twelve grid identity covariance binding of {e} differs from the verified receipt entry")
        if ent["source"] != ("first_wave_D1" if pi[e] < 3 else "twelve_added_D3a") or (ent["source"] == "first_wave_D1" and ent["receipt"] != D1_REGISTERED_RECEIPT["id"]) or v["pc1_status"] != "PC1_PASS" or v["consumption_allowed"] is not True: raise InputContractError(f"twelve grid identity covariance binding of {e} invalid / not PC1_PASS")
    if prior is not None:
        arr = np.asarray(prior, float); want = np.asarray([sw[conf_to_size[expected[e]]] / N_POS for e in ids])
        if arr.shape != want.shape or not np.all(np.isfinite(arr)) or not np.allclose(arr, want, rtol=0, atol=1e-15): raise InputContractError("twelve grid identity does not reproduce the actual numerical prior")
    return True


def _cov_binding(entry: dict) -> dict:
    return dict(config_id=int(entry["config_id"]), cache_key=entry["cache_key"], bound=True, cov_file_sha256=entry["cov_file_sha256"], cov_array_sha256=entry["cov_array_sha256"], receipt=entry["receipt"], origin=entry["source"], pc1_status=entry["pc1_status"], consumption_allowed=bool(entry["consumption_allowed"]))


def build_twelve_size_input(ctx: TwelveContext, family: str, size_id: str, system: str, supplies: List[BankSupply], plans: Dict[int, BootstrapPlan], fit_plans: dict) -> FamilyInput:
    """FamilyInput of ONE family / ONE size / ONE system from exactly 12 bank supplies whose covariance identity equals the VERIFIED receipt entry (PC1_PASS required); weight 1/12.
    The config map / receipt come from the verified context only (a caller dict, even with a recomputed payload SHA, is never a registered receipt)."""
    ctx = _require_ctx(ctx); config_map = ctx._d["config_map"]; receipt = ctx._d["receipt"]
    if family not in TWELVE_FAMILIES or system not in SYSTEMS: raise InputContractError("family / system")
    rows = {int(r["config_id"]): r for r in config_map["configurations"] if r["family"] == family and r["size_id"] == size_id}
    if len(rows) != N_POS: raise InputContractError(f"config map lists {len(rows)} configurations for {family}/{size_id} (12 required)")
    if not isinstance(supplies, (list, tuple)) or len(supplies) != N_POS or any(not isinstance(s, BankSupply) for s in supplies): raise InputContractError("exactly 12 BankSupply objects are required")
    got = {}
    for s in supplies:
        cid = _int(s.config_id, "supply config_id")
        if cid in got: raise InputContractError("duplicate supply configuration")
        if s.system != system: raise InputContractError(f"supply {cid} is for system {s.system}, requested {system}")
        got[cid] = s
    if set(got) != set(rows): raise InputContractError(f"bank supply inventory must equal the 12-position inventory {sorted(rows)}")
    cfgs, fit, bind, e2c, keys, cov, pidx = [], {}, {}, {}, {}, {}, {}
    for cid, r in sorted(rows.items()):
        s = got[cid]; e = receipt["positions"].get(str(cid))
        if e is None or e["cache_key"] != r["cache_key"] or [float(v) for v in e["x0_CT"]] != [float(v) for v in r["x0_CT"]] or e["position_index"] != r["position_index"]: raise InputContractError(f"config {cid}: receipt entry differs from the config map")
        if e["consumption_allowed"] is not True or e["pc1_status"] != "PC1_PASS": raise InputContractError(f"config {cid}: PC-1 status {e['pc1_status']} (formal consumption forbidden)")
        cm_ = s.cov_manifest
        if not isinstance(cm_, dict) or cm_.get("cov_array_sha256") != e["cov_array_sha256"] or cm_.get("cov_file_sha256") != e["cov_file_sha256"]: raise InputContractError(f"config {cid}: bank supply covariance identity differs from the receipt")
        eid = int(r["evaluation_ids"][system])
        if eid != (cid if system == "matched" else cid + NATIVE_OFFSET): raise InputContractError(f"config {cid}: evaluation id rule")
        cfgs.append(ConfigBank(eid, family, system, 1.0 / N_POS, s.T1_model, s.T2_model, s.T1_ref, s.T2_ref, s.cluster_uids, s.m, s.batches)); fit[eid] = s.fitting; bind[eid] = bank_sha256(s.fitting.X_model, s.fitting.X_ref, s.fitting.cid)
        e2c[eid] = cid; keys[eid] = r["cache_key"]; cov[eid] = _cov_binding(e); pidx[eid] = int(r["position_index"])
    ident = dict(stage="twelve", registry_sha256=config_map["registry_sha256"], manifest_sha256=config_map["first_wave_manifest_sha256"], config_map_sha256=config_map["map_sha256"], twelve_assets_sha256=config_map["twelve_assets_sha256"], covariance_receipt_sha256=receipt["receipt_sha256"],
                 family=family, system=system, sizes=[size_id], size_weights={size_id: 1.0}, evaluation_to_config=e2c, cache_keys=keys, cov_bound=cov, position_index=pidx, id_map_rule=f"matched=config_id; native=config_id+{NATIVE_OFFSET}")
    fam = FamilyInput(family, cfgs, plans, fit, fit_plans, True, bind, ident); fam.validate(); return fam


_SOURCE_KEYS = ("registry_sha256", "manifest_sha256", "config_map_sha256", "twelve_assets_sha256", "covariance_receipt_sha256")


def assemble_twelve_family(ctx: TwelveContext, family: str, size_inputs: Dict[str, Tuple[FamilyInput, Optional[FamilyInput]]]) -> Tuple[FamilyInput, Optional[FamilyInput], dict]:
    """All-size 12-position FamilyInput per system. BEFORE assembly every size / system view must carry the SAME source identities as the verified context (no value is taken
    from the first input or repaired); then twelve_eval.assemble_all_sizes (registered size prior x 1/12; shared plans) and the family identity from the context."""
    ctx = _require_ctx(ctx); config_map = ctx._d["config_map"]; reg = ctx.registry; twelve_assets = ctx.twelve_assets; want = {k: ctx.identities[k] for k in _SOURCE_KEYS}
    from .twelve_eval import assemble_all_sizes
    if family not in TWELVE_FAMILIES: raise InputContractError("family")
    sizes = list(size_inputs)
    if not sizes or any(s not in reg.surviving[family] for s in sizes): raise InputContractError("sizes must be surviving sizes of the registry")
    manifests, pm, npm = {}, {}, {}
    for s, (fm, fn) in size_inputs.items():
        if not isinstance(fm, FamilyInput): raise InputContractError(f"{family}/{s}: matched input missing")
        for label, f in (("matched", fm), ("native", fn)):
            if f is None: continue
            f.validate(); gi = f.grid_identity
            if gi is None or gi.get("stage") != "twelve" or gi["family"] != family or list(gi["sizes"]) != [s] or gi["system"] != label: raise InputContractError(f"{family}/{s}/{label}: size view is not a twelve identity of this family / size / system")
            diff = [k for k in _SOURCE_KEYS if gi[k] != want[k]]
            if diff: raise InputContractError(f"{family}/{s}/{label}: source identities differ from the verified context: {diff}")
        manifests[s] = twelve_assets.get(family, s); pm[s] = dict(fm.grid_identity["position_index"])
        if fn is not None: npm[s] = dict(fn.grid_identity["position_index"])
        if manifests[s].sha256 != next(r["twelve_manifest_sha256"] for r in config_map["configurations"] if r["family"] == family and r["size_id"] == s): raise InputContractError(f"{family}/{s}: twelve manifest differs from the config map")
    prior = {s: reg.size_prior[family][s] for s in sizes}; tot = sum(prior.values())
    if len(sizes) != len(reg.surviving[family]): prior = {s: w / tot for s, w in prior.items()}
    fm, fn, identity = assemble_all_sizes(size_inputs, manifests, pm, prior, npm if npm else None, expected_sizes=sizes)
    out = []
    for f in (fm, fn):
        if f is None: out.append(None); continue
        e2c, keys, cov, pidx = {}, {}, {}, {}
        for s in sizes:
            v = size_inputs[s][0 if f.configs[0].system == "matched" else 1]; gi = v.grid_identity
            e2c.update(gi["evaluation_to_config"]); keys.update(gi["cache_keys"]); cov.update(gi["cov_bound"]); pidx.update(gi["position_index"])
        ident = dict(stage="twelve", **want, family=family, system=f.configs[0].system, sizes=sizes, size_weights=prior, evaluation_to_config=e2c, cache_keys=keys, cov_bound=cov, position_index=pidx, id_map_rule=f"matched=config_id; native=config_id+{NATIVE_OFFSET}")
        g = replace(f, grid_identity=ident); g.validate(); out.append(g)
    identity = dict(identity, stage="twelve", size_weights=prior, **want, full_surviving_scope=len(sizes) == len(reg.surviving[family]))
    return out[0], out[1], identity


def twelve_official_gate(fam_matched: FamilyInput, fam_native: Optional[FamilyInput], mode: str = "official", env=None, plan_identity: Optional[dict] = None, table: Optional[dict] = None):
    """official_gate (registered bank/plan/environment profile) + the 12-position requirements + (official) the plans' CONTENT equal to the fixed plan identity. Returns a GateRecord
    whose diagnostics carry the additional checks."""
    from .official_gate import official_gate, GateRecord
    g = official_gate(fam_matched, fam_native, mode, env); checks = []
    def add(code, ok, msg, official_only=False): checks.append(dict(code=code, passed=bool(ok), message=msg, required_modes=(["official"] if official_only else ["smoke", "official"])))
    for label, f in (("matched", fam_matched), ("native", fam_native)):
        if f is None: continue
        gi = f.grid_identity or {}
        add(f"{label}/stage_twelve", gi.get("stage") == "twelve", f"{label}: not a twelve-stage identity")
        per = {}
        for c in f.configs: per.setdefault((gi.get("evaluation_to_config") or {}).get(c.evaluation_id, 0) // 100 % 100, []).append(c)
        add(f"{label}/twelve_per_size", all(len(v) == N_POS for v in per.values()) and len(per) == len(gi.get("sizes", [])), f"{label}: each size must contribute exactly 12 configurations")
        cb = gi.get("cov_bound") or {}
        add(f"{label}/pc1_pass_all", set(cb) == {c.evaluation_id for c in f.configs} and all(v.get("pc1_status") == "PC1_PASS" and v.get("consumption_allowed") is True for v in cb.values()), f"{label}: every configuration must be covariance-bound with PC1_PASS")
        add(f"{label}/full_surviving_scope", len(gi.get("sizes", [])) == len(SIZE_CODES), f"{label}: all surviving sizes required for the formal 12-position profile", True)
        origins = {v.get("origin") for v in cb.values()}
        add(f"{label}/first_wave_and_added_share_plans", origins == {"first_wave_D1", "twelve_added_D3a"} and all(c.cluster_uids[s // c.m:e // c.m] == p.strata[b] for c in f.configs for b, (s, e) in c.batches.items() for p in f.plans.values()), f"{label}: first-wave and added configurations must share the family plans (same latent UID order)", True)
        if plan_identity is not None:
            try: verify_plan_identity(f.plans, f.fit_plans, plan_identity, table=table, family=f.family); ok, msg = True, ""
            except InputContractError as ex: ok, msg = False, str(ex)
            add(f"{label}/plan_identity_fixed", ok, f"{label}: plans differ from the fixed identity: {msg}")
        else: add(f"{label}/plan_identity_fixed", False, f"{label}: no fixed plan identity supplied (official profile requires the recorded five-seed identity)", True)
    if fam_native is not None:
        gm, gn = fam_matched.grid_identity or {}, fam_native.grid_identity or {}
        add("pair/sources", all(gm.get(k) == gn.get(k) for k in _SOURCE_KEYS), "matched/native bound to different receipts / maps / registries")
        add("pair/positions", {gm["evaluation_to_config"].get(e) for e in gm.get("position_index", {})} == {gn["evaluation_to_config"].get(e) for e in gn.get("position_index", {})}, "matched/native cover different configurations")
    failures = list(g.required_failures) + [c["message"] for c in checks if not c["passed"] and mode in c["required_modes"]]
    diag = dict(g.diagnostics); diag["twelve_checks"] = checks; diag["scope"] = "formal 12-position family input / profile preflight (bank / plan / environment profile + 12-position binding + fixed plan identity); not covariance PSD, PC-1 physics, calibration or label release"
    return GateRecord(mode, not failures, failures, diag)


# ------------------------------------------------------------------------------------------------------------------------------------ plans
def fix_family_plans(table: dict, family: str, uids_by_batch: Dict[int, list], K_fit: int, master_seed: int, B: Optional[int] = None, B_KDE: Optional[int] = None) -> Tuple[Dict[int, BootstrapPlan], Dict[int, FittingPlan], dict]:
    """Five-seed evaluation / fitting plans of a family from the bank cluster UIDs (family EVALUATION latent order: purpose 200, family evaluation group, table wave); identity
    recorded. Shared by first-wave and added configurations."""
    from .d2_rng import group_for
    if family not in FAMILY_CODES: raise InputContractError("family")
    B = RULES.B if B is None else _int(B, "B"); Bk = int(_B_KDE()) if B_KDE is None else _int(B_KDE, "B_KDE")
    g_eval, g_fit, wave = group_for(table, "evaluation", family), group_for(table, "fitting", family), _int(table.get("wave_id"), "wave_id")
    if not isinstance(uids_by_batch, dict) or not uids_by_batch: raise InputContractError("uids_by_batch")
    for b, uids in uids_by_batch.items():
        for u in uids:
            u = as_uid(u)
            if u.purpose_id != PURPOSE["evaluation"] or u.crn_group_id != g_eval or u.wave_id != wave or u.batch_id != _int(b, "batch"): raise InputContractError("bank UIDs are not on the family evaluation latent (purpose 200 / family evaluation group / table wave / batch)")
    plans = {s: BootstrapPlan.build(f"D3-{family}-eval-s{s}", s, uids_by_batch, B, master_seed) for s in range(RULES.seeds)}
    fplans = {s: FittingPlan.build(f"D3-{family}-fit-s{s}", wave, g_fit, s, _int(K_fit, "K_fit"), Bk, master_seed) for s in range(RULES.seeds)}
    ident = dict(schema=PLAN_SCHEMA_V2["schema"], family=family, wave_id=wave, evaluation_group=g_eval, fitting_group=g_fit, master_seed=int(master_seed), B=B, B_KDE=Bk, seeds=RULES.seeds,
                 evaluation=[dict(plan_id=p.plan_id, seed_id=p.seed_id, rng_keys={str(b): list(k) for b, k in p.rng_keys.items()}, strata_uid_sha256={str(b): _sha(json.dumps([list(as_uid(u).as_tuple()) for u in p.strata[b]]).encode()) for b in p.strata}, multiplicity_sha256={str(b): _sha(np.ascontiguousarray(p.multiplicities[b]).tobytes()) for b in p.multiplicities}) for s, p in sorted(plans.items())],
                 fitting=[dict(plan_id=p.plan_id, seed_id=p.seed_id, rng_key=list(p.rng_key), K=p.K, multiplicity_sha256=p.multiplicities_sha256) for s, p in sorted(fplans.items())])
    ident["identity_sha256"] = _payload_sha(ident, "identity_sha256"); return plans, fplans, ident


def _B_KDE():
    from .official_gate import B_KDE
    return B_KDE


def verify_plan_identity(plans: Dict[int, BootstrapPlan], fit_plans: Dict[int, FittingPlan], identity: dict, table: Optional[dict] = None, family: Optional[str] = None) -> bool:
    """The supplied plan objects must reproduce the recorded identity EXACTLY: registered seed inventory (exactly RULES.seeds records per purpose, each seed once, keyed by seed_id,
    no zip truncation), header (family / wave / master_seed / groups / B / B_KDE) against the actual objects' plan ids, rng keys and shapes, evaluation keys purpose 200 and fitting
    keys purpose 300 on the recorded groups, strata UID order and multiplicity SHAs; optionally the groups against the CRN table and the family against the caller."""
    from .d2_rng import group_for
    if not isinstance(identity, dict) or identity.get("schema") != PLAN_SCHEMA_V2["schema"] or _payload_sha(identity, "identity_sha256") != identity.get("identity_sha256"): raise InputContractError("plan identity payload")
    for k in ("family", "wave_id", "evaluation_group", "fitting_group", "master_seed", "B", "B_KDE", "seeds"):
        if k not in identity: raise InputContractError(f"plan identity lacks {k}")
    fam = identity["family"]
    if fam not in FAMILY_CODES or (family is not None and fam != family): raise InputContractError("plan identity family")
    if identity["seeds"] != RULES.seeds: raise InputContractError(f"plan identity seeds {identity['seeds']} != registered {RULES.seeds}")
    seeds = set(range(RULES.seeds))
    if not isinstance(plans, dict) or not isinstance(fit_plans, dict) or set(plans) != seeds or set(fit_plans) != seeds: raise InputContractError("plan seed inventory (exactly the registered seeds 0..4 for evaluation and fitting)")
    wave, g_eval, g_fit, ms, B, Bk = (_int(identity[k], k) for k in ("wave_id", "evaluation_group", "fitting_group", "master_seed", "B", "B_KDE"))
    if table is not None and (g_eval != group_for(table, "evaluation", fam) or g_fit != group_for(table, "fitting", fam) or wave != table.get("wave_id")): raise InputContractError("plan identity groups / wave differ from the CRN table")
    def by_seed(records, what):
        if not isinstance(records, list) or len(records) != RULES.seeds: raise InputContractError(f"plan identity {what}: exactly {RULES.seeds} records required")
        out = {}
        for r in records:
            s = _int(r.get("seed_id"), f"{what} seed_id")
            if s in out or s not in seeds: raise InputContractError(f"plan identity {what}: seed inventory")
            out[s] = r
        return out
    ev, ft = by_seed(identity["evaluation"], "evaluation"), by_seed(identity["fitting"], "fitting")
    for s in sorted(seeds):
        p, rec = plans[s], ev[s]
        if not isinstance(p, BootstrapPlan): raise InputContractError("evaluation plan type")
        p.validate()
        if p.seed_id != s or p.plan_id != rec["plan_id"] or p.plan_id != f"D3-{fam}-eval-s{s}" or p.replicates != B: raise InputContractError(f"evaluation plan seed {s}: id / replicates differ from the fixed identity")
        keys = {str(b): list(k) for b, k in p.rng_keys.items()}
        if keys != rec["rng_keys"] or set(keys) != set(rec["strata_uid_sha256"]) or set(keys) != set(rec["multiplicity_sha256"]): raise InputContractError(f"evaluation plan seed {s}: rng keys / batch inventory differ from the fixed identity")
        for b, k in p.rng_keys.items():
            if list(k) != [ms, wave, PURPOSE["evaluation"], g_eval, int(b), s, BOOTSTRAP_STREAM]: raise InputContractError(f"evaluation plan seed {s} batch {b}: key differs from the identity header (master seed / wave / purpose 200 / group / batch / seed / stream)")
            if any(as_uid(u).purpose_id != PURPOSE["evaluation"] or as_uid(u).crn_group_id != g_eval or as_uid(u).wave_id != wave for u in p.strata[b]): raise InputContractError(f"evaluation plan seed {s} batch {b}: strata UIDs are not on the family evaluation latent")
        if {str(b): _sha(np.ascontiguousarray(p.multiplicities[b]).tobytes()) for b in p.multiplicities} != rec["multiplicity_sha256"] or {str(b): _sha(json.dumps([list(as_uid(u).as_tuple()) for u in p.strata[b]]).encode()) for b in p.strata} != rec["strata_uid_sha256"]: raise InputContractError(f"evaluation plan seed {s}: strata / multiplicities differ from the fixed identity")
        q, rec = fit_plans[s], ft[s]
        if not isinstance(q, FittingPlan): raise InputContractError("fitting plan type")
        q.validate()
        if q.seed_id != s or q.plan_id != rec["plan_id"] or q.plan_id != f"D3-{fam}-fit-s{s}" or list(q.rng_key) != rec["rng_key"] or list(q.rng_key) != [ms, wave, FittingPlan.PURPOSE_ID, g_fit, 0, s, BOOTSTRAP_STREAM] or q.K != rec["K"] or q.multiplicities_sha256 != rec["multiplicity_sha256"] or q.crn_group_id != g_fit or q.wave_id != wave or np.asarray(q.multiplicities).shape[0] != Bk:
            raise InputContractError(f"fitting plan seed {s} differs from the fixed identity / header")
    return True


# ------------------------------------------------------------------------------------------------------------------------------------ bank spec v2
def build_bank_spec_v2(ctx: TwelveContext) -> dict:
    """D-3b generation request + D-2 reuse binding for the 108 twelve-position configurations, derived ONLY from the verified context (canonical config map / receipt, CRN table
    == D-2 pins, canonical D-2 bank spec v1 == D-2 pins, D-2 ledger bytes == trusted identity). The scope (E2/E7/E8 x 3 sizes x 12 = 108; 81 generate / 27 reuse) is re-derived
    and asserted, batches / shards / row totals come from the registered D-2 constants. E1 stays first-wave / D-2. Deterministic; payload SHA."""
    from .d2_rng import group_for
    from . import d2_bank as d2
    ctx = _require_ctx(ctx); config_map, table, receipt, d2_spec, d2_ledger = ctx._d["config_map"], ctx._d["table"], ctx._d["receipt"], ctx._d["d2_spec"], ctx._d["d2_ledger"]
    N0, NMAX, M = _int(d2_spec["N0"], "N0"), _int(d2_spec["N_max"], "N_max"), _int(d2_spec["m"], "m")
    if (N0, NMAX, M) != (d2.N0, d2.N_MAX, d2.M) or d2_spec["shard_rows"] != d2.SHARD_ROWS or table["N0"] != N0 or table["N_max"] != NMAX or table["m"] != M or d2_spec["master_seed"] != table["master_seed"]: raise InputContractError("D-2 spec / CRN table constants differ from the registered constants")
    batches = {"0": dict(rows=[0, N0], clusters=[0, N0 // M], rotation_index=[0, N0 // M]), "1": dict(rows=[N0, NMAX], clusters=[N0 // M, NMAX // M], rotation_index=[0, (NMAX - N0) // M])}
    cfgs = {}; fam_ref = {}
    for fam in TWELVE_FAMILIES:
        units = d2_ledger["families"][fam]["units"]
        fam_ref[fam] = dict(source="D-2 accepted family reference bank (FIXED input; reuse binding d3_d2_reuse_binding_v1)", group=group_for(table, "evaluation", fam), role="ref_matched", d2_run_id=d2_ledger["families"][fam]["run_id"], d2_producer_digest=d2_ledger["families"][fam]["producer_digest"], environment_fingerprint=d2_ledger["families"][fam]["environment_fingerprint"],
                            units={k: dict(manifest_sha256=units[k]["manifest_sha256"], n_rows=units[k]["n_rows"], purpose=units[k]["purpose"]) for k in (f"ref_{fam}_b0", f"ref_{fam}_b1", f"ref_{fam}_fit") if k in units})
        if len(fam_ref[fam]["units"]) != 3 or fam_ref[fam]["units"][f"ref_{fam}_b0"]["n_rows"] != N0 or fam_ref[fam]["units"][f"ref_{fam}_b1"]["n_rows"] != NMAX - N0 or fam_ref[fam]["units"][f"ref_{fam}_fit"]["n_rows"] != d2.N_FIT: raise InputContractError(f"family {fam}: D-2 reference units incomplete / rows differ in the ledger")
    expected_ids = {10000 * FAMILY_CODES[f] + 100 * SIZE_CODES[z] + p + 1 for f in TWELVE_FAMILIES for z in SIZE_CODES for p in range(N_POS)}
    rows = {int(r["config_id"]): r for r in config_map["configurations"] if r["family"] != "E1"}
    if set(rows) != expected_ids or set(receipt["positions"]) != {str(c) for c in expected_ids}: raise InputContractError("config map / receipt do not span exactly the 108 twelve-position configurations")
    for cid, r in sorted(rows.items()):
        fam = r["family"]; e = receipt["positions"][str(cid)]
        if e["cache_key"] != r["cache_key"] or e["position_index"] != r["position_index"]: raise InputContractError(f"config {cid}: receipt / map entry mismatch")
        common = dict(config_id=cid, family=fam, size_id=r["size_id"], position_index=r["position_index"], display_suffix=r["display_suffix"], cache_key=r["cache_key"], x0_CT=[float(v) for v in r["x0_CT"]], weight_family=r["weight_family"], weight_within_size=r["weight_within_size"], evaluation_ids=dict(r["evaluation_ids"]),
                      covariance=dict(registered_file=e["registered_file"], cov_file_sha256=e["cov_file_sha256"], cov_array_sha256=e["cov_array_sha256"], receipt=e["receipt"], pc1_status=e["pc1_status"], consumption_allowed=e["consumption_allowed"]), crn=dict(evaluation_group=group_for(table, "evaluation", fam), fitting_group=group_for(table, "fitting", fam), wave_id=table["wave_id"]))
        if r["origin"] == "first_wave":
            if r["position_index"] > 2 or e["source"] != "first_wave_D1": raise InputContractError(f"config {cid}: first-wave origin / position mismatch")
            v1 = d2_spec["configurations"].get(str(cid)); units = d2_ledger["families"][fam]["units"]
            if v1 is None or v1["cache_key"] != r["cache_key"] or v1["covariance"]["cov_array_sha256"] != e["cov_array_sha256"]: raise InputContractError(f"config {cid}: D-2 spec entry missing / differs from the receipt")
            keys = [f"cfg{cid}_b0", f"cfg{cid}_b1", f"cfg{cid}_fit"]
            if any(k not in units for k in keys) or units[keys[0]]["n_rows"] != N0 or units[keys[1]]["n_rows"] != NMAX - N0 or units[keys[2]]["n_rows"] != d2.N_FIT: raise InputContractError(f"config {cid}: D-2 ledger units incomplete / rows differ")
            cfgs[str(cid)] = dict(common, mode="reuse_D2_fixed_input", d2=dict(spec_entry_sha256=_sha(json.dumps(v1, sort_keys=True).encode()), selections=v1["selections"], required_f32_subset=v1["selections"]["required_f32_subset"], units={k: dict(manifest_sha256=units[k]["manifest_sha256"], n_rows=units[k]["n_rows"], purpose=units[k]["purpose"]) for k in keys}, w2_primary_unit=(dict(manifest_sha256=units[f"cfg{cid}_w2"]["manifest_sha256"]) if f"cfg{cid}_w2" in units else None), run_id=d2_ledger["families"][fam]["run_id"], producer_digest=d2_ledger["families"][fam]["producer_digest"]),
                                  binding="d3_d2_reuse_binding_v1: identity kept verbatim; roles / roots / groups / batches / selections must match; view differences only (stage, weights)")
        elif r["origin"] == "twelve_added":
            if r["position_index"] < 3 or e["source"] != "twelve_added_D3a": raise InputContractError(f"config {cid}: added origin / position mismatch")
            cfgs[str(cid)] = dict(common, mode="generate_D3b", roles=dict(model_matched=dict(root="S_matched (principal root of the matched covariance)", source="intake_twelve_covariance"), model_native=dict(root="S_native (principal root of the native real-basis covariance)", source="intake_twelve_covariance"), ref_native=dict(root="diag(sqrt(c_l^CT) x 5/7/9) from this configuration's c_ct", source="intake_twelve_covariance (c_ct)")),
                                  shared_role=dict(ref_matched="family reference bank of D-2 (reused; same latent)"), batches=copy.deepcopy(batches), shards=d2.shard_plan(),
                                  selections=dict(evaluation={"0": ["float64"], "1": ["float64"]}, required_f32_subset=False, note="f64 only; no new mandatory f32 subset (design v0.2 B); the D-2 f32 acceptance is not generalised"),
                                  fitting=dict(purpose="fitting", N=d2.N_FIT, m=d2.M_FIT, batch_id=0, roles=["model_matched", "ref_matched", "model_native", "ref_native"], selections=["float64"]), w2_primary=None, w2_note="outside the D-3 main path (design v0.2 B): no W2 position bank, no CRN group")
        else: raise InputContractError(f"config {cid}: unknown origin")
    n_gen = sum(v["mode"] == "generate_D3b" for v in cfgs.values()); n_reuse = len(cfgs) - n_gen
    if (len(cfgs), n_gen, n_reuse) != (108, 81, 27): raise InputContractError(f"scope differs from 108 / 81 / 27: {len(cfgs)} / {n_gen} / {n_reuse}")
    spec = dict(schema=BANK_SPEC_V2_SCHEMA, inherits="d2_bank_spec_v1 " + d2_spec["spec_sha256"], master_seed=d2_spec["master_seed"], wave_id=table["wave_id"], crn_table_sha256=table["table_sha256"], registry_sha256=config_map["registry_sha256"], first_wave_manifest_sha256=config_map["first_wave_manifest_sha256"], config_map_sha256=config_map["map_sha256"], covariance_receipt_sha256=receipt["receipt_sha256"],
                d2_ledger_commit=d2_ledger["source_lock"]["commit"], d2_ledger_file_sha256=ctx._d["d2_ledger_sha256"], N0=N0, N_max=NMAX, m=M, shard_rows=d2_spec["shard_rows"], plan_schema=PLAN_SCHEMA_V2, family_reference=fam_ref, e1_first_wave_only=sorted(int(r["config_id"]) for r in config_map["configurations"] if r["family"] == "E1"),
                counts=dict(configurations=len(cfgs), generate=n_gen, reuse=n_reuse, generation_units=n_gen * 3, generation_rows_evaluation=n_gen * NMAX, generation_rows_fitting=n_gen * d2.N_FIT), estimate="~336 MB per new configuration in the D-2 storage format -> ~27 GB for 81 (decimal; excludes headers, JSON, roots, temp files)",
                configurations=cfgs)
    spec["spec_sha256"] = _payload_sha(spec, "spec_sha256"); return copy.deepcopy(spec)


def verify_bank_spec_v2(spec: dict, ctx: TwelveContext) -> dict:
    """Accepted only if it EQUALS the spec re-derived from the verified context (payload SHA + full content)."""
    ctx = _require_ctx(ctx)
    if not isinstance(spec, dict) or spec.get("schema") != BANK_SPEC_V2_SCHEMA or _payload_sha(spec, "spec_sha256") != spec.get("spec_sha256"): raise InputContractError("bank spec v2 payload SHA")
    fresh = build_bank_spec_v2(ctx)
    if fresh != spec: raise InputContractError("bank spec v2 differs from the re-derivation from the verified context")
    return fresh


def load_registered_bank_spec_v2(ctx: TwelveContext) -> dict:
    """The committed d/d3_bank_spec.json: bytes' payload identity must equal the pins' bank_spec_v2_sha256 and the content must equal the re-derivation."""
    ctx = _require_ctx(ctx); doc = _json(os.path.join(ctx.root, "d", "d3_bank_spec.json"), "registered bank spec v2")
    if doc.get("spec_sha256") != ctx._d["pins"].get("bank_spec_v2_sha256"): raise InputContractError("registered bank spec v2 identity differs from the pins")
    return verify_bank_spec_v2(doc, ctx)
