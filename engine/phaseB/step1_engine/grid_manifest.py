# -*- coding: utf-8 -*-
"""Configuration manifest (rules §4.4–4.7, A11 bridge): every registered first-wave configuration (family x surviving size x observer position) with immutable ids, shape parameters in
L_LSS units (registered equal-length slices, rules §4.2), full-precision reduced coordinates, the frozen A6 lift (s1_phaseA6A7_v1.4.2.py) to r_obs, the canonical bridge x0_CT = -r_obs
(A11 R2) and a covariance cache key (topology, params, x0). The manifest is derived ONLY from a validated registry (registry SHA carried) and cross-checked against the A7 rows
(shape JSON and r_obs_LLSS per primary observer). `verify_cov_manifest` checks that a covariance cache entry (A11 .manifest.json format) belongs to a configuration: exact topology,
parameters and x0 (abs 1e-12), array/file SHA present (and file SHA equal to the file bytes when the .npy is supplied). Nothing here computes covariances."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import csv, hashlib, json, math, os
import numpy as np
from .errors import InputContractError
from .grid_registry import GridRegistry, FAMILIES, ANCHOR_DIM, POSITIONS, size_id, A7_SHA
from . import serialization as ser

LIFT_SOURCE = dict(script="s1_phaseA6A7_v1.4.2.py", frozen_in="results/step1_phaseA/A6A7_freeze/", note="E2 [q0*Lx, q1*Ly, 0.37*2*Lz]; E7 [0.31*LAx, q0*L1y, 0.42*L2z]; E8 [q0*LAx, q1*LCy, 0.42*LBz]; E1 homogeneous r_obs=(0,0,0)")


# Explicit semantic codes preserve the current frozen grid's IDs without using
# the order of a supplied registry list as the meaning of the ID.
SIZE_CODES = {"L1.00": 1, "L1.20": 2, "L1.50": 3}
SIZE_VALUES = {"L1.00": 1.0, "L1.20": 1.2, "L1.50": 1.5}
FAMILY_CODES = {"E1": 1, "E2": 2, "E7": 3, "E8": 4}


def _sha_field(value, label):
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise InputContractError(f"{label}: expected a lowercase 64-hex SHA256")
    return value


def _integer(value, label, minimum=0):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < minimum:
        raise InputContractError(f"{label}: expected an integer >= {minimum}")
    return int(value)


def _number(value, label):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.integer, np.floating)) or not math.isfinite(float(value)):
        raise InputContractError(f"{label}: expected a finite real number")
    return float(value)


def _vector(value, length, label):
    if not isinstance(value, (list, tuple)) or len(value) != length:
        raise InputContractError(f"{label}: expected {length} coordinates")
    return [_number(v, label) for v in value]


def _parameters(value, label):
    if not isinstance(value, dict) or not value or any(not isinstance(k, str) or not k for k in value):
        raise InputContractError(f"{label}: expected a non-empty parameter mapping")
    return {k: _number(v, f"{label}.{k}") for k, v in value.items()}


def _tol(value):
    t = _number(value, "tolerance")
    if t < 0:
        raise InputContractError("tolerance must be non-negative")
    return t


def shape_params(family: str, L: float) -> dict:
    """Registered first-wave equal-length slices (rules §4.2), L in L_LSS units."""
    L = float(L)
    if family == "E1" or family == "E2": return dict(Lx=L, Ly=L, Lz=L)
    if family == "E7": return dict(LAx=L, LAy=0.0, L1y=L, L2x=0.0, L2z=L)
    if family == "E8": return dict(LAx=L, LAy=0.0, LBx=0.0, LBz=L, LCy=L)
    raise InputContractError("unknown family")


def lift(family: str, q: List[float], p: dict) -> List[float]:
    """Frozen A6 lift: reduced coordinates -> covering-space observer r_obs (L_LSS units)."""
    if family == "E1": return [0.0, 0.0, 0.0]
    if family == "E2": return [q[0] * p["Lx"], q[1] * p["Ly"], 0.37 * 2 * p["Lz"]]
    if family == "E7": return [0.31 * p["LAx"], q[0] * p["L1y"], 0.42 * p["L2z"]]
    if family == "E8": return [q[0] * p["LAx"], q[1] * p["LCy"], 0.42 * p["LBz"]]
    raise InputContractError("unknown family")


def cache_key(family: str, params: dict, x0: List[float]) -> str:
    return hashlib.sha256(json.dumps(dict(topology=family, params={k: float(v) for k, v in sorted(params.items())}, x0=[float(v) for v in x0]), sort_keys=True).encode()).hexdigest()


@dataclass
class ConfigurationSpec:
    config_id: int; family: str; size_id: str; L: float; position_index: int; observer_id: int
    shape_params: dict; reduced_coords: List[float]; r_obs: List[float]; x0_CT: List[float]; cache_key: str; circle_status: dict; weight: float
    def as_dict(self): return ser.to_jsonable(asdict(self))

    def validate_geometry(self):
        """Generic metadata schema. Tilted A11 diagnostic specs remain legal.
        This does not establish membership in the frozen first-wave registry.
        """
        _integer(self.config_id, "config_id")
        if self.family not in FAMILIES:
            raise InputContractError("configuration family")
        if not isinstance(self.size_id, str) or not self.size_id.strip():
            raise InputContractError("configuration size_id")
        if _number(self.L, "L") <= 0:
            raise InputContractError("L must be positive")
        _integer(self.position_index, "position_index")
        _integer(self.observer_id, "observer_id")
        p = _parameters(self.shape_params, "shape_params")
        r = _vector(self.r_obs, 3, "r_obs")
        x = _vector(self.x0_CT, 3, "x0_CT")
        if max(abs(a + b) for a, b in zip(r, x)) > 1e-12:
            raise InputContractError("x0_CT must equal -r_obs in the canonical gauge")
        _sha_field(self.cache_key, "geometry cache_key")
        if self.cache_key != cache_key(self.family, p, x):
            raise InputContractError("cache_key does not reproduce from topology/params/x0")
        if _number(self.weight, "weight") < 0:
            raise InputContractError("weight must be non-negative")
        return True


@dataclass
class ConfigurationManifest:
    schema: str; registry_sha256: str; lift_source: dict; configurations: List[ConfigurationSpec]; n_configurations: int; manifest_sha256: str = ""
    def as_dict(self): return ser.to_jsonable(asdict(self))
    def payload_sha(self) -> str:
        d = asdict(self); d.pop("manifest_sha256", None); return hashlib.sha256(json.dumps(ser.to_jsonable(d), sort_keys=True).encode()).hexdigest()
    def by_id(self) -> Dict[int, ConfigurationSpec]:
        self.validate()
        return {c.config_id: c for c in self.configurations}

    def validate(self):
        """Internal first-wave schema, payload, lift, bridge, prior and inventory.
        The registry SHA is a reference, not proof of source authentication.
        Full-precision A6 binding still requires a trusted external registry.
        """
        if self.schema != "configuration_manifest_v1" or self.lift_source != LIFT_SOURCE:
            raise InputContractError("configuration manifest schema/lift metadata")
        _sha_field(self.registry_sha256, "registry_sha256")
        _sha_field(self.manifest_sha256, "manifest_sha256")
        if not isinstance(self.configurations, list) or len(self.configurations) != 30 or _integer(self.n_configurations, "n_configurations") != 30:
            raise InputContractError("first-wave configuration inventory must contain 30 entries")
        seen_ids, seen_rows = set(), set()
        for c in self.configurations:
            if not isinstance(c, ConfigurationSpec):
                raise InputContractError("configuration entry type")
            c.validate_geometry()
            if c.size_id not in SIZE_CODES or c.L != SIZE_VALUES[c.size_id]:
                raise InputContractError("configuration L/size identity")
            npos = POSITIONS[c.family]
            if c.position_index >= npos or c.observer_id != (0 if c.family == "E1" else c.position_index + 1):
                raise InputContractError("configuration observer/position identity")
            expected_id = 10000 * FAMILY_CODES[c.family] + 100 * SIZE_CODES[c.size_id] + c.position_index + 1
            if c.config_id != expected_id or c.config_id in seen_ids:
                raise InputContractError("configuration ID is not the immutable semantic ID")
            seen_ids.add(c.config_id)
            key = (c.family, c.size_id, c.observer_id)
            if key in seen_rows:
                raise InputContractError("duplicate configuration identity")
            seen_rows.add(key)
            q = _vector(c.reduced_coords, ANCHOR_DIM[c.family], "reduced_coords")
            expected_p = shape_params(c.family, c.L)
            if c.shape_params != expected_p:
                raise InputContractError("first-wave equal-length shape differs")
            if max(abs(a-b) for a,b in zip(c.r_obs, lift(c.family, q, expected_p))) > 1e-12:
                raise InputContractError("r_obs does not reproduce from full-precision reduced coordinates")
            if abs(c.weight - 1.0 / (3 * npos)) > 1e-15:
                raise InputContractError("configuration prior differs from size x observer prior")
            expected_status = dict(L=SIZE_VALUES[c.size_id], observational_status="no_nondegenerate_circles",
                                   geometric_status="zero_radius_boundary" if c.size_id == "L1.00" else "no_nondegenerate_circles")
            if c.circle_status != expected_status:
                raise InputContractError("configuration circle metadata differs from the registered first-wave status")
        expected_rows = {(f, s, j) for f in FAMILIES for s in SIZE_CODES for j in ([0] if f == "E1" else [1, 2, 3])}
        if seen_rows != expected_rows:
            raise InputContractError("configuration identity inventory is incomplete")
        if self.manifest_sha256 != self.payload_sha():
            raise InputContractError("configuration manifest payload SHA mismatch")
        return True


def build_configuration_manifest(reg: GridRegistry) -> ConfigurationManifest:
    reg.validate(); specs = []
    for fi, f in enumerate(FAMILIES):
        for si, s in enumerate(reg.surviving[f]):
            L = reg.status[f][s]["L"]; p = shape_params(f, L); npos = POSITIONS[f]
            for j in range(npos):
                q = [] if f == "E1" else [float(v) for v in reg.anchors[f][j]]; r = lift(f, q, p); x0 = [-v for v in r]
                specs.append(ConfigurationSpec(10000 * FAMILY_CODES[f] + 100 * SIZE_CODES[s] + (j + 1), f, s, float(L), j, (0 if f == "E1" else j + 1), p, q, r, x0, cache_key(f, p, x0), dict(reg.status[f][s]), float(reg.size_prior[f][s]) / npos))
    if len(specs) != reg.n_configurations or len({c.config_id for c in specs}) != len(specs): raise InputContractError("configuration inventory does not match the registry")
    man = ConfigurationManifest("configuration_manifest_v1", reg.registry_sha256, dict(LIFT_SOURCE), specs, len(specs)); man.manifest_sha256 = man.payload_sha(); man.validate(); return man


def verify_manifest_against_a7(man: ConfigurationManifest, a7_csv: str, tol: float = 1e-6) -> dict:
    """Cross-check every configuration against the frozen A7 rows (SHA-verified): shape JSON equality and r_obs_LLSS agreement (A7 stores r_obs rounded to 6 decimals)."""
    if not isinstance(man, ConfigurationManifest): raise InputContractError("configuration manifest type")
    man.validate(); tol = _tol(tol)
    data = open(a7_csv, "rb").read()
    if hashlib.sha256(data).hexdigest() != A7_SHA: raise InputContractError("A7 CSV SHA differs from the frozen value")
    import io
    rows = [r for r in csv.DictReader(io.StringIO(data.decode("utf-8"))) if r.get("is_primary_observer") == "True" and r.get("observational_status") == "no_nondegenerate_circles"]
    idx = {(r["family"], size_id(r["L"]), int(r["observer_id"])): r for r in rows}; n = 0
    if len(idx) != len(rows) or set(idx) != {(c.family, c.size_id, c.observer_id) for c in man.configurations}:
        raise InputContractError("configuration inventory differs from all surviving A7 primary rows")
    for c in man.configurations:
        r = idx.get((c.family, c.size_id, c.observer_id))
        if r is None: raise InputContractError(f"configuration {c.config_id} has no A7 row")
        if json.loads(r["shape"]) != c.shape_params: raise InputContractError(f"configuration {c.config_id}: shape differs from A7")
        if max(abs(a - b) for a, b in zip(json.loads(r["r_obs_LLSS"]), c.r_obs)) > tol: raise InputContractError(f"configuration {c.config_id}: r_obs differs from A7")
        if any(r[k] != c.circle_status[k] for k in ("observational_status", "geometric_status")): raise InputContractError(f"configuration {c.config_id}: circle status differs from A7")
        n += 1
    return dict(checked=n, ok=True)


def verify_cov_manifest(spec: ConfigurationSpec, cov_manifest: dict, cov_npy_path: Optional[str] = None, tol: float = 1e-12) -> dict:
    """Check finite GEOMETRY metadata and optionally file bytes.
    Does not verify the array hash, environment/run profile, spectrum transform,
    symmetry, PSD, or the physical covariance. Those require the later intake.
    A matching geometry key is NOT a complete A11 cache execution key.
    """
    if not isinstance(spec, ConfigurationSpec):
        raise InputContractError("configuration spec type")
    spec.validate_geometry(); tol = _tol(tol)
    if not isinstance(cov_manifest, dict) or not isinstance(cov_manifest.get("manifest"), dict):
        raise InputContractError("covariance manifest schema")
    m = cov_manifest["manifest"]
    if m.get("topology") != spec.family:
        raise InputContractError("covariance manifest topology differs from the configuration family")
    params = _parameters(m.get("params"), "covariance params")
    if set(params) != set(spec.shape_params) or any(abs(params[k] - spec.shape_params[k]) > tol for k in spec.shape_params):
        raise InputContractError("covariance manifest parameters differ from the registered shape")
    x0 = _vector(m.get("x0"), 3, "covariance x0")
    if any(abs(a - b) > tol for a, b in zip(x0, spec.x0_CT)):
        raise InputContractError("covariance manifest x0 differs from the configuration's x0_CT = -r_obs")
    for k in ("cov_array_sha256", "cov_file_sha256"):
        _sha_field(cov_manifest.get(k), k)
    if cov_npy_path is not None:
        with open(cov_npy_path, "rb") as fh:
            body = fh.read()
        if hashlib.sha256(body).hexdigest() != cov_manifest["cov_file_sha256"]:
            raise InputContractError("covariance file bytes differ from the manifest file SHA")
    return dict(config_id=spec.config_id, cache_key=spec.cache_key,
                cov_array_sha256=cov_manifest["cov_array_sha256"], bound=True,
                scope="geometry metadata only; optional file SHA; not a complete covariance intake",
                file_sha_verified=cov_npy_path is not None, array_sha_verified=False,
                run_profile_verified=False)
