# -*- coding: utf-8 -*-
"""D-2 tranche 1: registered CRN table + adapter from the FORMAL rng key (rules §6.3–6.4, tables table2_crn_dependence) to the frozen numerical scan of LegacyKernel.
Contracts:
  * CRN TABLE (d/d2_crn_table.json): a saved, deterministic map scope -> crn_group_id, never numbered by execution order. Scopes: evaluation (wave, family) — all
    configurations / sizes / both systems / 4 roles / paired selections share the latent; fitting (wave, family) — a different purpose; w2_independent (wave, family, size,
    position; keyed by the immutable config_id) — one group per POSITION, so different positions never share a latent; w2_crn (wave, family, size) — reserved, distinct
    purpose/group. Group integers are unique across purposes and waves; the table is validated on load (CRNRegistry restoration; no renumbering).
  * LATENT REPLAY: the latent of (purpose, wave, group, batch) = the rotation stream and the gaussian stream of the formal key, consumed in FIXED chunk order from the key's
    initial state. Every consumer re-creates the generators from the key (never continues an existing generator), so any configuration / root / role / selection sees the SAME
    R and z blocks; "same Generator object" is not used as "same latent".
  * BATCH / UID: two logical batches — 0: N0 rows (10,000 clusters), 1: extension 3*N0 rows (30,000 clusters); ClusterUID = (wave, purpose_id, group, batch, rotation_index)
    with rotation_index the cluster index WITHIN the batch. Physical shards are a storage choice recorded separately (shard -> global cluster range) and never change UIDs.
  * ROOTS: model_matched = S_M,j; ref_matched = principal root of the fixed PR3 isotropic covariance (shared); model_native = S_N,j; ref_native = diag(sqrt(c_l,j^CT) repeated
    over the 5/7/9 components) from the configuration's own c_ct (D-1 intake). Roots are passed as full-precision arrays (no rounded text).
  * NUMERICAL PATH: generate_from_latent reuses LegacyKernel.D_batch / scan unchanged (same math, same chunk sizes, same selections); the legacy generate() and its seed wiring are
    kept for the Phase A/B reproduction tests. On identical latent + roots the two paths give bit-identical T1/T2/AX/PL (regression test)."""
from __future__ import annotations
import json, hashlib
from typing import Dict, List, Optional, Tuple
import numpy as np
from .errors import InputContractError
from .registry import CRNRegistry, PURPOSE, STREAM
from .types import ClusterUID
from .grid_manifest import FAMILY_CODES, SIZE_CODES

WAVE_ID = 1; N0 = 1_000_000; N_MAX = 4_000_000; M = 100; CHUNK_CLUSTERS = 2000
BATCHES = {0: (0, N0), 1: (N0, N_MAX)}                                   # logical supply (orchestrator.ConfigBank contract)
L_BLOCKS = ((2, 5), (3, 7), (4, 9))                                       # multipole blocks of the 21-dim real basis: l=2 (5), l=3 (7), l=4 (9)



def _d2_int(value, name, minimum=0):
    # Do not silently truncate seed / configuration / batch identifiers.
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < minimum:
        raise InputContractError(f"{name} must be a non-bool integer >= {minimum}")
    return int(value)


def _validated_table_groups(t):
    """Validate content, separately from the outer expected payload digest.

    This is the first-wave schema, not a new source authentication mechanism.
    An official caller still binds the table to its externally expected digest.
    """
    if not isinstance(t, dict) or t.get("schema") != "d2_crn_table_v1":
        raise InputContractError("CRN table schema")
    _d2_int(t.get("master_seed"), "master_seed")
    wave = _d2_int(t.get("wave_id"), "wave_id")
    for field, expected in (("N0", N0), ("N_max", N_MAX), ("m", M), ("chunk_clusters", CHUNK_CLUSTERS)):
        if _d2_int(t.get(field), field, 1) != expected:
            raise InputContractError(f"CRN table {field} disagrees with the registered adapter")
    expected_batches = {str(k): list(v) for k, v in BATCHES.items()}
    if t.get("batches") != expected_batches:
        raise InputContractError("CRN table batches disagree with the registered adapter")
    for limits in t["batches"].values():
        for value in limits: _d2_int(value, "batch row limit")
    if not isinstance(t.get("groups"), dict) or not t["groups"]:
        raise InputContractError("CRN table requires a nonempty group map")
    restored = {}; seen_scopes = set()
    allowed = {"evaluation", "fitting", "w2_independent", "w2_crn"}
    for text_gid, row in t["groups"].items():
        if (not isinstance(text_gid, str) or not text_gid.isdecimal()
                or str(int(text_gid)) != text_gid or int(text_gid) <= 0):
            raise InputContractError("CRN table group key must be a canonical positive integer string")
        gid = int(text_gid)
        if gid in restored or not isinstance(row, dict):
            raise InputContractError("CRN table duplicate group or invalid group row")
        purpose = row.get("purpose")
        if purpose not in allowed or _d2_int(row.get("wave_id"), "group wave_id") != wave:
            raise InputContractError("CRN table group purpose/wave mismatch")
        sc = row.get("scope")
        if not isinstance(sc, dict): raise InputContractError("CRN table scope must be an object")
        if _d2_int(sc.get("wave_id"), "scope wave_id") != wave or sc.get("family") not in FAMILY_CODES:
            raise InputContractError("CRN table scope wave/family mismatch")
        keys = {"wave_id", "family"}
        if purpose.startswith("w2_"):
            keys.add("size_id")
            if sc["family"] == "E1" or sc.get("size_id") not in SIZE_CODES:
                raise InputContractError("CRN table W2 family/size mismatch")
        if purpose == "w2_independent":
            keys.add("config_id")
            cid = _d2_int(sc.get("config_id"), "config_id", 1)
            base = 10000 * FAMILY_CODES[sc["family"]] + 100 * SIZE_CODES[sc["size_id"]]
            if cid not in {base + 1, base + 2, base + 3}:
                raise InputContractError("CRN table first-wave W2 config_id does not match family/size/position")
        elif purpose == "w2_crn":
            keys.add("reserved")
            if sc.get("reserved") is not True: raise InputContractError("W2 CRN entry must be explicitly reserved")
        if set(sc) != keys: raise InputContractError("CRN table unexpected or missing scope fields")
        label = json.dumps(sc, sort_keys=True)
        if row.get("label") != label: raise InputContractError("CRN table label does not describe its actual scope")
        key = (purpose, label)
        if key in seen_scopes: raise InputContractError("CRN table duplicate actual scope")
        seen_scopes.add(key)
        restored[gid] = dict(purpose=purpose, wave_id=wave, label=label)
    return restored


def _generation_contract(registry, purpose, group, batch_id, K, m, chunk_clusters, wave_id):
    if not isinstance(registry, CRNRegistry): raise InputContractError("CRNRegistry required")
    group = _d2_int(group, "crn_group_id", 1)
    batch_id = _d2_int(batch_id, "batch_id")
    wave_id = _d2_int(wave_id, "wave_id")
    K = _d2_int(K, "K", 1); m = _d2_int(m, "m", 1)
    chunk_clusters = _d2_int(chunk_clusters, "chunk_clusters", 1)
    k0, k1 = cluster_range(batch_id)
    if K > k1 - k0:
        raise InputContractError("K exceeds the declared batch cluster capacity; do not truncate UIDs")
    # Validate both keys before allocating outputs or performing numerical work.
    registry.rng_key(purpose, wave_id, group, batch_id, "rotation")
    registry.rng_key(purpose, wave_id, group, batch_id, "gaussian")
    return group, batch_id, K, m, chunk_clusters, wave_id

def build_crn_table(master_seed: int, w2_config_ids: Dict[str, Dict[str, List[int]]], families=("E1", "E2", "E7", "E8"), wave_id: int = WAVE_ID) -> dict:
    """Deterministic table. w2_config_ids: family -> size_id -> list of immutable config_ids (the W2 primary positions; E1 excluded)."""
    master_seed = _d2_int(master_seed, "master_seed")
    wave_id = _d2_int(wave_id, "wave_id")
    groups = {}
    def put(gid, purpose, scope):
        if gid in groups: raise InputContractError(f"duplicate crn_group_id {gid}")
        groups[gid] = dict(purpose=purpose, wave_id=int(wave_id), label=json.dumps(scope, sort_keys=True), scope=scope)
    for fam in families:
        fc = FAMILY_CODES[fam]
        put(1000 + fc, "evaluation", dict(wave_id=wave_id, family=fam))
        put(2000 + fc, "fitting", dict(wave_id=wave_id, family=fam))
    for fam, sizes in w2_config_ids.items():
        if fam == "E1": raise InputContractError("E1 has no W2 primary positions")
        for size_id, ids in sizes.items():
            if size_id not in SIZE_CODES: raise InputContractError("unknown size id")
            put(4000 + FAMILY_CODES[fam] * 10 + SIZE_CODES[size_id], "w2_crn", dict(wave_id=wave_id, family=fam, size_id=size_id, reserved=True))
            for cid in ids:
                cid = _d2_int(cid, "config_id", 1); put(30000 + cid, "w2_independent", dict(wave_id=wave_id, family=fam, size_id=size_id, config_id=cid))
    table = dict(schema="d2_crn_table_v1", master_seed=int(master_seed), wave_id=int(wave_id), batches={str(k): list(v) for k, v in BATCHES.items()}, N0=N0, N_max=N_MAX, m=M, chunk_clusters=CHUNK_CLUSTERS,
                 rng_key="(MASTER_SEED, wave_id, purpose_id, crn_group_id, batch_id, stream_id)", cluster_uid="(wave_id, purpose_id, crn_group_id, batch_id, rotation_index within batch)",
                 groups={str(g): v for g, v in sorted(groups.items())}, rule="group integers are fixed by scope, never by execution order; evaluation/fitting share by family (all configurations, both systems, 4 roles, paired selections); w2_independent: one group per position (config_id)")
    table["table_sha256"] = _table_sha(table); _validated_table_groups(table); return table


def _table_sha(table: dict) -> str:
    body = {k: v for k, v in table.items() if k != "table_sha256"}; return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def load_crn_table(path: str, expected_sha256: Optional[str] = None) -> Tuple[dict, CRNRegistry]:
    t = json.load(open(path))
    if t.get("schema") != "d2_crn_table_v1" or _table_sha(t) != t.get("table_sha256"): raise InputContractError("CRN table schema / SHA")
    if expected_sha256 is not None and t["table_sha256"] != expected_sha256: raise InputContractError("CRN table SHA differs from the expected value")
    groups = _validated_table_groups(t)
    reg = CRNRegistry(t["master_seed"], groups); return t, reg


def group_for(table: dict, purpose: str, family: str, size_id: Optional[str] = None, config_id: Optional[int] = None) -> int:
    _validated_table_groups(table)
    if _table_sha(table) != table.get("table_sha256"): raise InputContractError("CRN table payload changed")
    want = dict(wave_id=table["wave_id"], family=family)
    if purpose == "w2_independent":
        if size_id is None or config_id is None or isinstance(config_id, bool): raise InputContractError("w2_independent group requires size_id and the immutable config_id (position)")
        want.update(size_id=size_id, config_id=_d2_int(config_id, "config_id", 1))
    if purpose == "w2_crn": want.update(size_id=size_id, reserved=True)
    hits = [int(g) for g, v in table["groups"].items() if v["purpose"] == purpose and v["scope"] == want]
    if len(hits) != 1: raise InputContractError(f"CRN table: no unique group for {purpose} {want}")
    return hits[0]


def cluster_range(batch_id: int) -> Tuple[int, int]:
    batch_id = _d2_int(batch_id, "batch_id")
    if batch_id not in BATCHES: raise InputContractError("batch_id must be 0 or 1")
    s, e = BATCHES[batch_id]; return s // M, e // M


def uids_for(purpose: str, group: int, batch_id: int, wave_id: int = WAVE_ID) -> List[ClusterUID]:
    wave_id = _d2_int(wave_id, "wave_id"); group = _d2_int(group, "crn_group_id", 1)
    if purpose not in PURPOSE: raise InputContractError("unknown purpose")
    k0, k1 = cluster_range(batch_id); return [CRNRegistry.cluster_uid(wave_id, purpose, group, batch_id, i) for i in range(k1 - k0)]


def iter_latent(registry: CRNRegistry, purpose: str, group: int, batch_id: int, K: int, m: int = M, chunk_clusters: int = CHUNK_CLUSTERS, wave_id: int = WAVE_ID):
    """Yield (k0, k1, Rs, Z) for clusters [0, K) of the batch, in fixed chunk order, from FRESH generators of the formal key (replay contract: never continues a live stream)."""
    group, batch_id, K, m, chunk_clusters, wave_id = _generation_contract(registry, purpose, group, batch_id, K, m, chunk_clusters, wave_id)
    from scipy.spatial.transform import Rotation
    key_r = registry.rng_key(purpose, wave_id, group, batch_id, "rotation"); key_g = registry.rng_key(purpose, wave_id, group, batch_id, "gaussian")
    rr = np.random.default_rng(np.random.SeedSequence(list(key_r))); rz = np.random.default_rng(np.random.SeedSequence(list(key_g)))
    for k0 in range(0, K, chunk_clusters):
        k1 = min(K, k0 + chunk_clusters); Rs = Rotation.random(num=k1 - k0, rng=rr).as_matrix(); Z = rz.standard_normal((k1 - k0, m, 21)); yield k0, k1, Rs, Z


def native_reference_root(c_ct: np.ndarray) -> np.ndarray:
    """ref_native root: diag(sqrt(c_l^CT) repeated over the 5/7/9 components) from the configuration's own block-trace c_ct (full precision)."""
    raw = np.asarray(c_ct)
    if raw.dtype.kind not in "fiu": raise InputContractError("c_ct must be real numeric values")
    c = np.asarray(raw, float)
    if c.shape != (3,) or not np.isfinite(c).all() or (c <= 0).any(): raise InputContractError("c_ct must be three positive finite values")
    return np.diag(np.concatenate([np.full(n, np.sqrt(c[i])) for i, (l, n) in enumerate(L_BLOCKS)]))


def generate_from_latent(kernel, roots: Dict[str, np.ndarray], registry: CRNRegistry, purpose: str, group: int, batch_id: int, K: int, selections=("float64",), m: int = M, chunk_clusters: int = CHUNK_CLUSTERS, wave_id: int = WAVE_ID):
    """Scan every root (role) on the SAME latent blocks; returns (out[(role, sel)] -> dict(T1,T2,AX,PL), cid, uids). Uses kernel.D_batch / kernel.scan unchanged."""
    from .legacy_kernel import CHUNK_BY_SEL
    group, batch_id, K, m, chunk_clusters, wave_id = _generation_contract(registry, purpose, group, batch_id, K, m, chunk_clusters, wave_id)
    if not isinstance(roots, dict) or not roots:
        raise InputContractError("nonempty root mapping required")
    for S in roots.values():
        a = np.asarray(S)
        if a.shape != (21, 21) or a.dtype.kind not in "fiu" or not np.isfinite(a).all():
            raise InputContractError("roots must be finite real (21,21) arrays")
    if not isinstance(selections, (tuple, list)) or not selections or any(s not in CHUNK_BY_SEL for s in selections) or len(set(selections)) != len(selections): raise InputContractError("nonempty unique registered selections required")
    N = K * m; out = {(r, s): dict(T1=np.empty(N), T2=np.empty(N), AX=np.empty(N, np.int32), PL=np.empty(N, np.int32)) for r in roots for s in selections}; cid = np.repeat(np.arange(K), m)
    for k0, k1, Rs, Z in iter_latent(registry, purpose, group, batch_id, K, m, chunk_clusters, wave_id):
        Ds = kernel.D_batch(Rs); sl = slice(k0 * m, k1 * m)
        for r, S in roots.items():
            X = np.einsum("kab,kmb->kma", Ds @ np.asarray(S, float), Z).reshape(-1, 21)
            for s in selections:
                d = kernel.scan(X, s)
                for kk in ("T1", "T2", "AX", "PL"): out[(r, s)][kk][sl] = d[kk]
    return out, cid, uids_for(purpose, group, batch_id, wave_id)[:K]
