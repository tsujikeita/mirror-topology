# -*- coding: utf-8 -*-
"""External family x size / observer registry (rules §4, table 3 coverage), derived ONLY from the frozen A6/A7 assets (file SHA bound).
Two distinct intakes: (a) `load_registry` builds from the SHA-verified assets and stamps the payload SHA; (b) `registry_from_dict` restores an external record and requires
its 64-hex payload SHA plus a full structural/semantic validation (family set, size sets, uniqueness, surviving == status-derived set, L <-> size id, configuration count re-derived,
anchor dimension/finiteness/E1 exception, schema, design metadata). Restoration verifies INTERNAL consistency only; `registry_from_dict_bound` additionally re-derives the registry
from the SHA-verified assets and requires payload equality (source binding). The registry is the only supplier of expected surviving sizes, size priors and anchors."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List
import csv, hashlib, json, math, io
import numpy as np
from .errors import InputContractError
from . import serialization as ser

SCHEMA = "grid_registry_v1"; FAMILIES = ("E1", "E2", "E7", "E8"); SURVIVING = "no_nondegenerate_circles"; EXCLUDED = "excluded_by_published_search"
GEOMETRIC = {"circles_geometrically_present", "zero_radius_boundary", "no_nondegenerate_circles"}
A6_SHA = "a5ea1ae69fe7a899af0f3cada0deca2abd9e04a49a10cf131f6c522857a35109"; A7_SHA = "47b2d910a00bcb1ecdbf644291dbe9e9507ea69162aa3ebc74df3fa02acb085e"
ANCHOR_DIM = {"E1": 0, "E2": 2, "E7": 1, "E8": 2}; POSITIONS = {"E1": 1, "E2": 3, "E7": 3, "E8": 3}
DESIGN_KEYS = ("version", "seed_sequence", "lift_rule")


def _fsha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _verified_bytes(path, expected_sha, label):
    """Hash and parse ONE captured byte buffer, not two reads of a live path."""
    with open(path, "rb") as fh:
        data = fh.read()
    if hashlib.sha256(data).hexdigest() != expected_sha:
        raise InputContractError(f"{label} SHA differs from the frozen value")
    return data


def size_id(L: float) -> str: return f"L{float(L):.2f}"


def _is_sha(v) -> bool: return isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)


@dataclass
class GridRegistry:
    schema: str; a6_sha256: str; a7_sha256: str
    sizes: Dict[str, List[str]]; status: Dict[str, Dict[str, dict]]; surviving: Dict[str, List[str]]; size_prior: Dict[str, Dict[str, float]]; anchors: Dict[str, List[List[float]]]
    observer_design: dict; n_configurations: int; registry_sha256: str = ""; verification_scope: str = "constructed_from_verified_assets"

    def as_dict(self): return ser.to_jsonable(asdict(self))

    def payload_sha(self) -> str:
        d = asdict(self); d.pop("registry_sha256", None); d.pop("verification_scope", None); return hashlib.sha256(json.dumps(ser.to_jsonable(d), sort_keys=True).encode()).hexdigest()

    def validate(self, require_sha: bool = True) -> bool:
        if self.schema != SCHEMA: raise InputContractError(f"unregistered registry schema {self.schema!r}")
        if self.a6_sha256 != A6_SHA or self.a7_sha256 != A7_SHA: raise InputContractError("registry is not bound to the frozen A6/A7 assets")
        for name in ("sizes", "status", "surviving", "size_prior", "anchors"):
            m = getattr(self, name)
            if not isinstance(m, dict) or set(m) != set(FAMILIES): raise InputContractError(f"{name}: family set must be exactly {FAMILIES}")
        if not isinstance(self.observer_design, dict) or set(self.observer_design) != set(DESIGN_KEYS): raise InputContractError("observer_design metadata inventory")
        for key in ("version", "lift_rule"):
            value = self.observer_design[key]
            if not isinstance(value, str) or not value.strip():
                raise InputContractError(f"observer_design.{key} must be a non-empty str")
        seeds = self.observer_design["seed_sequence"]
        if (not isinstance(seeds, list) or not seeds or
                any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in seeds)):
            raise InputContractError("observer_design.seed_sequence must contain non-negative integers")
        n_conf = 0
        for f in FAMILIES:
            sz = self.sizes[f]
            if not isinstance(sz, list) or not sz or len(set(sz)) != len(sz) or not all(isinstance(s, str) and s for s in sz): raise InputContractError(f"{f}: registered sizes must be a non-empty unique list")
            st = self.status[f]
            if not isinstance(st, dict) or set(st) != set(sz): raise InputContractError(f"{f}: status table must cover exactly the registered sizes")
            for s, rec in st.items():
                if not isinstance(rec, dict) or set(rec) != {"L", "observational_status", "geometric_status"}: raise InputContractError(f"{f}/{s}: status record inventory")
                L = rec["L"]
                if isinstance(L, bool) or not isinstance(L, (int, float)) or not math.isfinite(float(L)) or float(L) <= 0 or size_id(L) != s: raise InputContractError(f"{f}/{s}: L does not correspond to the size id")
                if rec["observational_status"] not in (SURVIVING, EXCLUDED) or rec["geometric_status"] not in GEOMETRIC: raise InputContractError(f"{f}/{s}: unregistered status")
                if rec["observational_status"] == EXCLUDED and rec["geometric_status"] != "circles_geometrically_present": raise InputContractError(f"{f}/{s}: excluded size must have circles geometrically present")
                if rec["observational_status"] == SURVIVING and rec["geometric_status"] == "circles_geometrically_present": raise InputContractError(f"{f}/{s}: surviving size cannot have circles geometrically present")
            derived = [s for s in sz if st[s]["observational_status"] == SURVIVING]
            if list(self.surviving[f]) != derived: raise InputContractError(f"{f}: surviving list must equal the status-derived set {derived}")
            if not derived: raise InputContractError(f"{f}: no surviving size")
            sp = self.size_prior[f]
            if not isinstance(sp, dict) or set(sp) != set(derived): raise InputContractError(f"{f}: size prior must cover exactly the surviving sizes")
            w = np.array([sp[s] for s in derived], float)
            if not np.all(np.isfinite(w)) or not np.allclose(w, 1.0 / len(derived), rtol=0, atol=1e-15): raise InputContractError(f"{f}: size prior must be equal over surviving sizes")
            A = self.anchors[f]
            if not isinstance(A, list): raise InputContractError(f"{f}: anchors must be a list")
            if f == "E1":
                if A: raise InputContractError("E1 is observer-homogeneous (no anchors)")
            else:
                if len(A) != 3 or any(not isinstance(p, list) or len(p) != ANCHOR_DIM[f] or not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x)) for x in p) for p in A): raise InputContractError(f"{f}: exactly 3 finite anchors of dimension {ANCHOR_DIM[f]} required")
                if len({tuple(p) for p in A}) != 3: raise InputContractError(f"{f}: anchors must be distinct")
            n_conf += len(derived) * POSITIONS[f]
        if not isinstance(self.n_configurations, int) or isinstance(self.n_configurations, bool) or self.n_configurations != n_conf: raise InputContractError(f"n_configurations must equal the re-derived count {n_conf}")
        if require_sha:
            if not _is_sha(self.registry_sha256): raise InputContractError("restored registry requires its 64-hex payload SHA")
            if self.registry_sha256 != self.payload_sha(): raise InputContractError("registry SHA does not match its payload")
        return True


def load_registry(a7_csv: str, a6_json: str) -> GridRegistry:
    """Build the registry from the frozen assets; refuses files whose SHA differs from the frozen values."""
    a7_bytes = _verified_bytes(a7_csv, A7_SHA, "A7 circle geometry CSV")
    a6_bytes = _verified_bytes(a6_json, A6_SHA, "A6 observer design JSON")
    rows = [r for r in csv.DictReader(io.StringIO(a7_bytes.decode("utf-8")))
            if r.get("is_primary_observer") == "True"]
    sizes, status = {f: [] for f in FAMILIES}, {f: {} for f in FAMILIES}
    for r in rows:
        f = r["family"]
        if f not in FAMILIES: raise InputContractError(f"unregistered family in A7: {f}")
        s = size_id(r["L"])
        if s not in sizes[f]: sizes[f].append(s); status[f][s] = dict(L=float(r["L"]), observational_status=r["observational_status"], geometric_status=r["geometric_status"])
        elif status[f][s] != dict(L=float(r["L"]), observational_status=r["observational_status"], geometric_status=r["geometric_status"]): raise InputContractError(f"{f}/{s}: inconsistent status across observer rows")
    surviving = {f: [s for s in sizes[f] if status[f][s]["observational_status"] == SURVIVING] for f in FAMILIES}
    prior = {f: {s: 1.0 / len(surviving[f]) for s in surviving[f]} for f in FAMILIES}
    j = json.loads(a6_bytes.decode("utf-8")); anchors = {f: (j["points"][f]["points"] if f in j["points"] else []) for f in FAMILIES}
    n_conf = sum(len(surviving[f]) * POSITIONS[f] for f in FAMILIES)
    reg = GridRegistry(SCHEMA, A6_SHA, A7_SHA, sizes, status, surviving, prior, anchors, {k: j[k] for k in DESIGN_KEYS}, n_conf)
    reg.validate(require_sha=False); reg.registry_sha256 = reg.payload_sha(); reg.verification_scope = "constructed_from_verified_assets"; reg.validate(); return reg


def registry_from_dict(d: dict) -> GridRegistry:
    """Restore an external record: full structural validation + mandatory payload SHA. Scope: internally consistent; source binding NOT verified (use registry_from_dict_bound)."""
    d = ser.from_jsonable(d)
    if not isinstance(d, dict): raise InputContractError("registry record must be a dict")
    fields = {"schema", "a6_sha256", "a7_sha256", "sizes", "status", "surviving", "size_prior", "anchors", "observer_design", "n_configurations", "registry_sha256"}
    if not fields <= set(d): raise InputContractError(f"registry record lacks {sorted(fields - set(d))}")
    extras = set(d) - fields - {"verification_scope"}
    if extras:
        raise InputContractError(f"registry record has unregistered fields {sorted(extras)}")
    d = {k: d[k] for k in fields}
    reg = GridRegistry(**d); reg.validate(require_sha=True); reg.verification_scope = "internally_consistent; source_binding_not_verified"; return reg


def registry_from_dict_bound(d: dict, a7_csv: str, a6_json: str) -> GridRegistry:
    """Restore AND bind to the frozen assets: re-derive from the SHA-verified A6/A7 files and require payload equality."""
    reg = registry_from_dict(d); fresh = load_registry(a7_csv, a6_json)
    if reg.payload_sha() != fresh.payload_sha() or reg.registry_sha256 != fresh.registry_sha256: raise InputContractError("restored registry differs from the registry re-derived from the frozen assets")
    reg.verification_scope = "source_bound (re-derived from SHA-verified A6/A7)"; return reg
