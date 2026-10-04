# -*- coding: utf-8 -*-
"""D4C-0b: the fixed isotropic PSEUDO-OBSERVATION columns of the global false-support calibration (rules §9.2: independent stream, m = 1, fixed n_pseudo = 2000; one shared
ordered pair (T1_p, T2_p), p = 0..1999, consumed by ALL families). Rules:
  * SEPARATE TABLE (d/d4_pseudo_table.json, schema d4_pseudo_table_v1): the registered D-2 CRN table is NOT modified (its validator admits only evaluation / fitting /
    w2_independent / w2_crn). The pseudo table fixes master_seed (the registered 20260912), wave_id 1, purpose 'pseudo' (registry PURPOSE id 400), ONE group (5001), batch 0,
    K = n_pseudo clusters x m = 1 rotation, the float64 selection, the single role 'pseudo_iso' (principal root of the fixed PR3 isotropic covariance = the D-2 ref_matched root),
    the chunk size and the formal rng key rule. KEY NON-OVERLAP: the formal key is (master_seed, wave_id, purpose_id, group, batch, stream); purpose_id 400 is used by no other
    registered scope (evaluation 200 / fitting 300 / w2_independent 600 / w2_crn 700 / calibration 100 / w2_isotropic 800), so the pseudo latent never coincides with any
    evaluation / fitting / W2 / whitening / null stream whatever the group integer; the group 5001 is additionally outside every D-2 table group.
  * GENERATION: d2_rng.generate_from_latent on the frozen LegacyKernel (same D_batch / scan as the banks; the scan does not depend on m), K = n_pseudo, m = 1 -> N = n_pseudo rows;
    the paired columns keep the generation order (pseudo index = cluster index = rotation index); no per-column sorting, no dropping of rows (a non-finite value is a technical
    failure of the generation, never removed).
  * RECORD: column SHAs (T1 / T2 float64, AX / PL int32, cid, UIDs), root SHA, table SHA, kernel / source binding, environment, and the commitment helper of the target is the
    EXISTING calibration_first.commit_target (never re-implemented). The registered loader is bound to constants filled only after the accepted formal generation
    (PSEUDO_REGISTRATION is None until then)."""
from __future__ import annotations
import hashlib, json, os
from typing import Dict, Optional, Tuple
import numpy as np
from .errors import InputContractError
from .rules_config import RULES
from .registry import CRNRegistry, PURPOSE, STREAM
from .d2_rng import generate_from_latent, WAVE_ID, CHUNK_CLUSTERS, _table_sha, uids_for
from .types import ClusterUID

TABLE_SCHEMA = "d4_pseudo_table_v1"; RECORD_SCHEMA = "d4_pseudo_record_v1"
PSEUDO_PURPOSE = "pseudo"; PSEUDO_GROUP = 5001; PSEUDO_ROLE = "pseudo_iso"; PSEUDO_M = 1; PSEUDO_SELECTION = "float64"
PSEUDO_REGISTRATION = None     # bound at the end of the module to the d4c0_registry constants (accepted formal generation 12980202); None would refuse the registered load
_D2_TABLE_GROUP_RANGES = ((1001, 1008), (2001, 2008), (4000, 4999), (40000, 79999))   # evaluation (1000+family code) / fitting (2000+code) / w2_crn (4000+10*code+size) / w2_independent (30000+config_id, config ids 10101..49999) of the registered D-2 table


def _sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
def _asha(a) -> str: return _sha(np.ascontiguousarray(a).tobytes())


def _int(v, name, minimum=0):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)) or v < minimum: raise InputContractError(f"{name} must be a non-bool integer >= {minimum}")
    return int(v)


def build_pseudo_table(master_seed: int = 20260912, wave_id: int = WAVE_ID, group: int = PSEUDO_GROUP, n_pseudo: Optional[int] = None) -> dict:
    """Deterministic pseudo table (no execution-order numbering)."""
    n = RULES.n_pseudo if n_pseudo is None else _int(n_pseudo, "n_pseudo", 1)
    t = dict(schema=TABLE_SCHEMA, master_seed=_int(master_seed, "master_seed"), wave_id=_int(wave_id, "wave_id"), purpose=PSEUDO_PURPOSE, purpose_id=PURPOSE[PSEUDO_PURPOSE], group=_int(group, "group", 1), batch_id=0, n_pseudo=n, m=PSEUDO_M, K=n, selections=[PSEUDO_SELECTION], role=PSEUDO_ROLE,
             root="principal root of the fixed PR3 isotropic covariance (LegacyKernel.psqrt(C_ISO)) == the D-2 ref_matched root", chunk_clusters=CHUNK_CLUSTERS,
             rng_key="(MASTER_SEED, wave_id, purpose_id, crn_group_id, batch_id, stream_id); streams rotation=1 / gaussian=0 (registry.STREAM)", cluster_uid="(wave_id, purpose_id, crn_group_id, batch_id, rotation_index); pseudo index p == rotation_index (m = 1)",
             key_non_overlap="purpose_id 400 is used by no other registered scope (evaluation 200, fitting 300, w2_independent 600, w2_crn 700, calibration 100, w2_isotropic 800); group 5001 lies outside every D-2 CRN table group",
             order="paired (T1_p, T2_p) in generation order; one shared ordered pair per pseudo for ALL families; no per-column sorting; no row removal", scope="rules §9.2: isotropic pseudo observations, independent stream, m = 1, fixed n_pseudo")
    t["table_sha256"] = _table_sha(t); validate_pseudo_table(t); return t


def validate_pseudo_table(t: dict) -> None:
    if not isinstance(t, dict) or t.get("schema") != TABLE_SCHEMA: raise InputContractError("pseudo table schema")
    if _table_sha(t) != t.get("table_sha256"): raise InputContractError("pseudo table SHA")
    _int(t.get("master_seed"), "master_seed"); _int(t.get("wave_id"), "wave_id")
    if t.get("purpose") != PSEUDO_PURPOSE or t.get("purpose_id") != PURPOSE[PSEUDO_PURPOSE] or t.get("batch_id") != 0 or t.get("m") != PSEUDO_M or t.get("selections") != [PSEUDO_SELECTION] or t.get("role") != PSEUDO_ROLE: raise InputContractError("pseudo table purpose / batch / m / selection / role")
    n = _int(t.get("n_pseudo"), "n_pseudo", 1)
    if t.get("K") != n or n > 10000: raise InputContractError("pseudo table K must equal n_pseudo (m = 1) within the batch-0 capacity")
    g = _int(t.get("group"), "group", 1)
    if any(lo <= g <= hi for lo, hi in _D2_TABLE_GROUP_RANGES): raise InputContractError("pseudo group integer collides with a D-2 CRN table group range")
    if _int(t.get("chunk_clusters"), "chunk_clusters", 1) != CHUNK_CLUSTERS: raise InputContractError("pseudo chunk size differs from the registered adapter")


def load_pseudo_table(path: str, expected_sha256: Optional[str] = None) -> Tuple[dict, CRNRegistry]:
    t = json.load(open(path)); validate_pseudo_table(t)
    if expected_sha256 is not None and t["table_sha256"] != expected_sha256: raise InputContractError("pseudo table SHA differs from the expected value")
    reg = CRNRegistry(t["master_seed"], {int(t["group"]): dict(purpose=PSEUDO_PURPOSE, wave_id=int(t["wave_id"]), label=json.dumps(dict(wave_id=int(t["wave_id"]), purpose=PSEUDO_PURPOSE), sort_keys=True))})
    return t, reg


def pseudo_rng_keys(t: dict, reg: CRNRegistry) -> dict:
    return {s: list(reg.rng_key(PSEUDO_PURPOSE, int(t["wave_id"]), int(t["group"]), 0, s)) for s in ("rotation", "gaussian")}


def generate_pseudo_columns(kernel, t: dict, reg: CRNRegistry, root_iso: np.ndarray, n: Optional[int] = None) -> dict:
    """K = n clusters (n = n_pseudo formally; a smaller n only in self-test), m = 1, single role, float64: returns the ordered columns and UIDs. Non-finite output is a technical failure."""
    validate_pseudo_table(t); n = int(t["n_pseudo"]) if n is None else _int(n, "n", 1)
    if n > int(t["n_pseudo"]): raise InputContractError("n exceeds the table n_pseudo")
    S = np.asarray(root_iso, float)
    if S.shape != (21, 21) or not np.isfinite(S).all(): raise InputContractError("isotropic root must be a finite (21,21) array")
    out, cid, uids = generate_from_latent(kernel, {PSEUDO_ROLE: S}, reg, PSEUDO_PURPOSE, int(t["group"]), 0, n, selections=(PSEUDO_SELECTION,), m=PSEUDO_M, chunk_clusters=int(t["chunk_clusters"]), wave_id=int(t["wave_id"]))
    d = out[(PSEUDO_ROLE, PSEUDO_SELECTION)]; T1 = np.ascontiguousarray(d["T1"], dtype=np.float64); T2 = np.ascontiguousarray(d["T2"], dtype=np.float64); AX = np.ascontiguousarray(d["AX"], dtype=np.int32); PL = np.ascontiguousarray(d["PL"], dtype=np.int32)
    if T1.shape != (n,) or T2.shape != (n,) or not (np.isfinite(T1).all() and np.isfinite(T2).all()): raise InputContractError("pseudo generation technical failure: shape / non-finite T1 or T2 (no row removal)")
    if not np.array_equal(np.asarray(cid), np.arange(n)) or len(uids) != n or any(u.rotation_index != i or u.batch_id != 0 or u.purpose_id != PURPOSE[PSEUDO_PURPOSE] or u.crn_group_id != int(t["group"]) for i, u in enumerate(uids)): raise InputContractError("pseudo cluster / UID order")
    return dict(T1=T1, T2=T2, AX=AX, PL=PL, cid=np.ascontiguousarray(np.asarray(cid), dtype=np.int64), uids=[list(u.as_tuple()) for u in uids], n=n, root_sha256=_asha(S), rng_keys=pseudo_rng_keys(t, reg))


def column_identity(cols: dict) -> dict:
    return dict(n=int(cols["n"]), m=PSEUDO_M, T1_sha256=_asha(cols["T1"]), T2_sha256=_asha(cols["T2"]), AX_sha256=_asha(cols["AX"]), PL_sha256=_asha(cols["PL"]), cid_sha256=_asha(cols["cid"]), uids_sha256=_sha(json.dumps(cols["uids"]).encode()), dtype=dict(T1="float64", T2="float64", AX="int32", PL="int32", cid="int64"),
                paired_sha256=_sha(np.ascontiguousarray(np.c_[cols["T1"], cols["T2"]]).tobytes()), first_uid=cols["uids"][0], last_uid=cols["uids"][-1])


def save_pseudo_columns(path: str, cols: dict) -> dict:
    """Write the NPZ (T1, T2, AX, PL, cid, uids) and return its file identity."""
    import io
    buf = io.BytesIO(); np.savez(buf, T1=cols["T1"], T2=cols["T2"], AX=cols["AX"], PL=cols["PL"], cid=cols["cid"], uids=np.asarray(cols["uids"], dtype=np.int64)); data = buf.getvalue()
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh: fh.write(data); fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, path)
    if open(path, "rb").read() != data: raise InputContractError("pseudo NPZ publication differs from the computed bytes")
    return dict(file=os.path.basename(path), sha256=_sha(data), bytes=len(data))


def verify_pseudo_columns(path: str, identity: dict, t: dict, expected_file: Optional[dict] = None) -> dict:
    """Re-read the NPZ and require: file identity (if given), exact column SHAs, shapes (n,), finiteness, cid == arange(n), UIDs == the table's ordered UIDs; returns the columns."""
    validate_pseudo_table(t); b = open(path, "rb").read()
    if expected_file is not None and (_sha(b) != expected_file.get("sha256") or len(b) != expected_file.get("bytes")): raise InputContractError("pseudo NPZ file identity")
    import io
    z = np.load(io.BytesIO(b)); n = int(identity["n"])
    if set(z.files) != {"T1", "T2", "AX", "PL", "cid", "uids"}: raise InputContractError("pseudo NPZ member set")
    T1, T2, AX, PL, cid, uids = (z[k] for k in ("T1", "T2", "AX", "PL", "cid", "uids"))
    if T1.dtype != np.float64 or T2.dtype != np.float64 or AX.dtype != np.int32 or PL.dtype != np.int32 or cid.dtype != np.int64 or T1.shape != (n,) or T2.shape != (n,) or AX.shape != (n,) or PL.shape != (n,) or cid.shape != (n,) or uids.shape != (n, 5): raise InputContractError("pseudo NPZ dtype / shape")
    if not (np.isfinite(T1).all() and np.isfinite(T2).all()) or not np.array_equal(cid, np.arange(n)): raise InputContractError("pseudo NPZ finiteness / cid order")
    want = [list(u.as_tuple()) for u in uids_for(PSEUDO_PURPOSE, int(t["group"]), 0, int(t["wave_id"]))[:n]]
    if uids.tolist() != want: raise InputContractError("pseudo NPZ UIDs differ from the table's ordered UIDs")
    cols = dict(T1=T1, T2=T2, AX=AX, PL=PL, cid=cid, uids=uids.tolist(), n=n)
    if column_identity(cols) != dict(identity): raise InputContractError("pseudo column identity differs from the record")
    return cols


def load_registered_pseudo_columns(phaseb_root: str, ctx):
    """Formal registered load (D4C-0 registration tranche): the body lives in d4c0_registry.load_registered_pseudo_columns — pins (acceptance / paired / NPZ / ledger / receipt)
    and the ORIGINAL NPZ bytes are authenticated and the columns re-verified against the registered CONSTANT identity (never a regenerated or tolerance-equivalent array).
    PSEUDO_REGISTRATION mirrors the registration constants; a None value (pre-registration) is refused."""
    if PSEUDO_REGISTRATION is None: raise InputContractError("pseudo columns are not registered yet")
    from .d4c0_registry import load_registered_pseudo_columns as _load
    return _load(phaseb_root, ctx)


def _registration_constants():
    from .d4c0_registry import PSEUDO
    return dict(attempt=PSEUDO["attempt"], commit=PSEUDO["execution_lock"]["commit"], engine_version=PSEUDO["execution_lock"]["engine_version"], paired_sha256=PSEUDO["columns"]["paired_sha256"], npz_sha256=PSEUDO["npz"]["sha256"], acceptance_sha256=PSEUDO["acceptance"]["sha256"], archive_sha256=PSEUDO["archive"]["sha256"], executed_notebook_sha256=PSEUDO["executed_notebook"]["sha256"])


PSEUDO_REGISTRATION = _registration_constants()
