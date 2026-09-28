# -*- coding: utf-8 -*-
"""D-3a registered covariance assets: intake of the REGISTERED formal partition runs (registered_assets/d3) into a sealed, read-only asset object.

What is registered (Step1_PhaseD_D3a_completion_report.md): the 9 formal size-partition runs of the accepted D-3a generator (commit fe7c201e, step1_engine 0.86.0,
d/d3_covgen.py) = E2/E7/E8 x L1.00/L1.20/L1.50, each with its complete out/d3 record (run manifest, registry, PC-1 results, partial evidence, env lock, launcher records,
covariance cache: 21 or 33 NPY files with their generator manifests), the 2 INCOMPLETE attempts (E2/L1.50 and E8/L1.50 on the standard Colab runtime: rc -9 = OOM;
retained, never deleted, metadata only), and the 11 executed notebooks. The ledger (d3a_generation_ledger.json) and the family coverage (d3a_family_coverage.json)
are author-side records; this intake does not trust them: every formal run is RE-VERIFIED through d3_stage.verify_partition_run(require_arrays=True) bound to the
ledger's run-manifest identity, re-aggregated with d3_stage.aggregate_partitions against the CURRENT registered case table / pins, and the result is compared with the
registered coverage. Incomplete attempts are checked to be incomplete (no run manifest, D3_PASS False) and their partial evidence is cross-checked against the completed
run of the same partition (bit-identical covariance identities / rel values = reproduction evidence, recorded in the ledger).

The returned D3aAssets exposes the 81 new base covariances (config_id -> registered file, file/array SHA, PC-1 status) for the D-3b bank stage. PC-1 status is carried
through as recorded and re-derived (PC1_PASS / PC1_FAIL); a PC1_FAIL base is exposed with its status and `require_pc1_pass` refuses it. No physical regeneration and
no PC-1 acceptance is made here (acceptance is the external audit's)."""
from __future__ import annotations
import copy, hashlib, json, os, re
from typing import Dict, Optional
import numpy as np
from .errors import InputContractError
from .d3_stage import verify_partition_run, aggregate_partitions, VerifiedPartition, REQUIRED_ACTIONS

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LEDGER_SCHEMA = "d3a_generation_ledger_v1"
COVERAGE_SCHEMA = "d3a_family_coverage_bundle_v1"
_TOKEN = object()
_HEX = re.compile(r"[0-9a-f]{64}")


def _sha(path: str) -> str:
    with open(path, "rb") as fh: return hashlib.sha256(fh.read()).hexdigest()


def _hex64(v) -> bool:
    return isinstance(v, str) and _HEX.fullmatch(v) is not None


def _load_json(path: str, what: str) -> dict:
    def pairs(items):
        d = {}
        for k, v in items:
            if k in d: raise InputContractError(f"{what}: duplicate JSON key {k}")
            d[k] = v
        return d
    try:
        with open(path, "rb") as fh: b = fh.read()
        v = json.loads(b.decode("utf-8"), object_pairs_hook=pairs, parse_constant=lambda c: (_ for _ in ()).throw(InputContractError(f"{what}: non-finite constant")))
    except (OSError, ValueError, UnicodeDecodeError) as e:
        raise InputContractError(f"{what}: unreadable ({type(e).__name__})")
    if not isinstance(v, dict): raise InputContractError(f"{what}: document must be an object")
    return v


def _safe_rel(root: str, rel: str, what: str) -> str:
    if not isinstance(rel, str) or not rel or os.path.isabs(rel) or ".." in rel.replace("\\", "/").split("/"): raise InputContractError(f"{what}: invalid registered path")
    p = os.path.realpath(os.path.join(root, rel))
    if os.path.commonpath([os.path.realpath(root), p]) != os.path.realpath(root): raise InputContractError(f"{what}: registered path escapes the phaseB root")
    return p


class D3aAssets:
    """Sealed result of intake_registered_d3a_assets. Public views are deep copies; construction outside the factory is refused."""
    __slots__ = ("_payload", "_seal")

    def __init__(self, record: dict, *, _token=None):
        if _token is not _TOKEN: raise InputContractError("D3aAssets must be created by intake_registered_d3a_assets")
        object.__setattr__(self, "_payload", json.dumps(record, sort_keys=True, allow_nan=False, ensure_ascii=False).encode("utf-8"))
        object.__setattr__(self, "_seal", _TOKEN)

    def __setattr__(self, n, v): raise AttributeError("D3aAssets is immutable")
    def __delattr__(self, n): raise AttributeError("D3aAssets is immutable")
    def _view(self, n): return json.loads(self._payload.decode("utf-8"))[n]

    @property
    def verified(self): return self._seal is _TOKEN
    @property
    def source_lock(self): return self._view("source_lock")
    @property
    def ledger_sha256(self): return self._view("ledger_sha256")
    @property
    def coverage_sha256(self): return self._view("coverage_sha256")
    @property
    def coverage(self): return self._view("coverage")
    @property
    def formal_runs(self): return self._view("formal_runs")
    @property
    def incomplete_attempts(self): return self._view("incomplete_attempts")
    @property
    def reproduction_crosscheck(self): return self._view("reproduction_crosscheck")
    @property
    def base_covariances(self): return self._view("base_covariances")
    @property
    def pc1_status(self): return self._view("pc1_status")
    @property
    def n_pc1_fail(self): return sum(v["status"] == "PC1_FAIL" for v in self._view("pc1_status").values())

    def require_pc1_pass(self, config_id: int) -> dict:
        """Registered base covariance reference of a 12-position configuration whose PC-1 status is PC1_PASS; anything else is refused (asset-layer failure, never a fallback)."""
        key = str(config_id)
        if type(config_id) is not int or key not in self._view("base_covariances"): raise InputContractError(f"config {config_id}: not a registered D-3a base covariance")
        st = self._view("pc1_status")[key]
        if st["status"] != "PC1_PASS": raise InputContractError(f"config {config_id}: PC-1 status {st['status']} (formal consumption forbidden)")
        return self._view("base_covariances")[key]


def _expected_source(lock: dict) -> dict:
    for k in ("commit", "engine_version", "inventory_sha256", "script_sha256", "pins_sha256"):
        if not isinstance(lock.get(k), str) or not lock[k]: raise InputContractError(f"ledger source_lock lacks {k}")
    if not re.fullmatch(r"[0-9a-f]{40}", lock["commit"]): raise InputContractError("ledger source_lock.commit is not a 40-hex commit")
    return dict(engine_version=lock["engine_version"], inventory_sha256=lock["inventory_sha256"], script_sha256=lock["script_sha256"], pins_sha256=lock["pins_sha256"])


def _coverage_key(cov: dict) -> dict:
    """Coverage with environment-specific run paths removed (comparison key)."""
    c = copy.deepcopy(cov)
    for p in c.get("partitions", []): p.pop("run_dir", None)
    return c


def intake_registered_d3a_assets(phaseb_root: Optional[str] = None, expected_ledger_sha256: Optional[str] = None) -> D3aAssets:
    """Re-verify the registered D-3a runs and return the sealed asset object (see module docstring). Every failure raises InputContractError; nothing is repaired or skipped."""
    root = os.path.abspath(phaseb_root or _ROOT)
    ledger_path = os.path.join(root, "registered_assets", "d3", "d3a_generation_ledger.json"); cov_path = os.path.join(root, "registered_assets", "d3", "d3a_family_coverage.json")
    ledger = _load_json(ledger_path, "D-3a ledger"); ledger_sha = _sha(ledger_path)
    if expected_ledger_sha256 is not None and ledger_sha != expected_ledger_sha256: raise InputContractError("D-3a ledger bytes differ from the expected identity")
    if ledger.get("schema") != LEDGER_SCHEMA: raise InputContractError("D-3a ledger schema differs")
    lock = ledger.get("source_lock") or {}; src = _expected_source(lock)
    pins = _load_json(os.path.join(root, "d", "d3_pins.json"), "d3 pins"); table = _load_json(os.path.join(root, "d", "d3_pc1_case_table.json"), "case table")
    ct_sha, cm_sha = ledger.get("case_table_sha256"), ledger.get("config_map_sha256")
    if not _hex64(ct_sha) or not _hex64(cm_sha) or pins.get("case_table_sha256") != ct_sha or pins.get("config_map_sha256") != cm_sha or table.get("table_sha256") != ct_sha:
        raise InputContractError("ledger case-table / config-map identities differ from the current registered pins / table")
    registered_cov = _load_json(cov_path, "D-3a coverage"); cov_sha = _sha(cov_path)
    if registered_cov.get("schema") != COVERAGE_SCHEMA or ledger.get("coverage_sha256") != cov_sha: raise InputContractError("registered coverage schema / identity differs from the ledger")
    runs = ledger.get("formal_runs")
    if not isinstance(runs, dict) or not runs: raise InputContractError("ledger lists no formal runs")
    by_family: Dict[str, list] = {}; seen = set(); run_records = {}
    for name, rec in runs.items():
        if not isinstance(rec, dict): raise InputContractError(f"run {name}: invalid ledger record")
        fam, sizes = rec.get("family"), rec.get("sizes")
        if fam not in REQUIRED_ACTIONS or fam == "E1" or not isinstance(sizes, list) or len(sizes) != 1: raise InputContractError(f"run {name}: family / size partition invalid")
        if (fam, sizes[0]) in seen: raise InputContractError(f"run {name}: duplicate partition {fam}/{sizes[0]}")
        seen.add((fam, sizes[0]))
        if not _hex64(rec.get("run_manifest_sha256")): raise InputContractError(f"run {name}: missing run-manifest identity")
        rd = _safe_rel(root, rec.get("registered_dir"), f"run {name}")
        p = verify_partition_run(rd, src, ct_sha, cm_sha, require_arrays=True, expected_run_manifest_sha256=rec["run_manifest_sha256"])
        if p.run_manifest.get("family") != fam or list(p.run_manifest.get("selection", {}).get("sizes") or []) != sizes: raise InputContractError(f"run {name}: family / sizes differ from the ledger")
        if rec.get("document_sha256") != p.document_sha256: raise InputContractError(f"run {name}: published-document identities differ from the ledger")
        for extra, fname in (("final_record_sha256", "d3_final_record.json"), ("launcher_lock_sha256", "launcher_lock.json")):
            fp = os.path.join(os.path.dirname(rd), fname)
            if not _hex64(rec.get(extra)) or not os.path.isfile(fp) or _sha(fp) != rec[extra]: raise InputContractError(f"run {name}: {fname} identity differs from the ledger")
        fr = _load_json(os.path.join(os.path.dirname(rd), "d3_final_record.json"), f"run {name} final record"); ll = _load_json(os.path.join(os.path.dirname(rd), "launcher_lock.json"), f"run {name} launcher lock")
        if fr.get("D3_PASS") is not True or (fr.get("launcher") or {}) != ll or ll.get("commit") != lock["commit"] or ll.get("inventory_sha256") != src["inventory_sha256"] or ll.get("pins_sha256") != src["pins_sha256"] or ll.get("engine_version") != src["engine_version"] or ll.get("family") != fam or ll.get("size_filter") != sizes[0] or ll.get("with_h2") is not False:
            raise InputContractError(f"run {name}: final record / launcher lock not bound to the ledger source lock")
        by_family.setdefault(fam, []).append(p); run_records[name] = dict(family=fam, sizes=sizes, registered_dir=rec["registered_dir"], run_manifest_sha256=rec["run_manifest_sha256"], runtime=rec.get("runtime"), seconds=p.run_manifest.get("seconds"), drive_run_dir=ll.get("run_dir"))
    coverage = {}
    for fam in sorted(by_family):
        cov = aggregate_partitions(table, fam, by_family[fam], src, ct_sha)
        reg = (registered_cov.get("coverage") or {}).get(fam)
        if not isinstance(reg, dict) or _coverage_key(reg) != _coverage_key(cov): raise InputContractError(f"family {fam}: re-aggregated coverage differs from the registered coverage")
        if cov.get("family_coverage_complete") is not True or cov.get("arrays_verified") is not True or cov.get("outer_ledger_bound") is not True: raise InputContractError(f"family {fam}: coverage incomplete")
        coverage[fam] = cov
    if set(coverage) != {"E2", "E7", "E8"} or set(registered_cov.get("coverage") or {}) != set(coverage): raise InputContractError("registered coverage does not span exactly E2/E7/E8")
    # incomplete attempts: must be incomplete, retained, and reproduced by the completed partition run
    inc = ledger.get("incomplete_attempts")
    if not isinstance(inc, dict): raise InputContractError("ledger lacks incomplete_attempts (may be empty)")
    crosscheck = {}
    for name, rec in inc.items():
        d = _safe_rel(root, rec.get("registered_dir"), f"attempt {name}")
        if os.path.exists(os.path.join(d, "d3", "d3_run_manifest.json")): raise InputContractError(f"attempt {name}: has a run manifest; not an incomplete attempt")
        fr = _load_json(os.path.join(d, "d3_final_record.json"), f"attempt {name} final record")
        if fr.get("D3_PASS") is not False or (fr.get("stages") or {}).get("script_returncode") != rec.get("script_returncode"): raise InputContractError(f"attempt {name}: final record differs from the ledger")
        comp = rec.get("completed_by")
        if comp not in run_records or run_records[comp]["family"] != rec.get("family") or run_records[comp]["sizes"] != rec.get("sizes"): raise InputContractError(f"attempt {name}: completed_by does not name the completed partition run")
        pe = _load_json(os.path.join(d, "d3", "d3_partial_evidence.json"), f"attempt {name} partial evidence")
        comp_p = next(p for p in by_family[rec["family"]] if list(p.run_manifest["selection"]["sizes"]) == rec["sizes"])
        rg = comp_p.registry["configurations"]; pr = comp_p.pc1_results["cases"]
        pb, pc = pe.get("bases") or {}, pe.get("cases") or {}
        if not set(pb) <= set(rg) or not set(pc) <= set(pr): raise InputContractError(f"attempt {name}: partial evidence names unknown bases / cases")
        same_b = all(pb[k].get("cov_file_sha256") == rg[k]["cov_file_sha256"] and pb[k].get("cov_array_sha256") == rg[k]["cov_array_sha256"] for k in pb)
        same_c = all(pc[k].get("rel") == pr[k]["rel"] and (pc[k].get("clone_identity") or {}).get("array_sha256") == pr[k]["clone_identity"]["array_sha256"] for k in pc)
        if not (same_b and same_c): raise InputContractError(f"attempt {name}: partial evidence is NOT reproduced by the completed run (covariance identities / rel differ)")
        crosscheck[name] = dict(completed_by=comp, partial_bases_reproduced=len(pb), partial_cases_reproduced=len(pc), script_returncode=rec.get("script_returncode"), runtime=rec.get("runtime"))
        if rec.get("reproduction") != crosscheck[name]["partial_bases_reproduced"] + crosscheck[name]["partial_cases_reproduced"]: raise InputContractError(f"attempt {name}: ledger reproduction count differs")
    # base covariance references (81 new bases) and PC-1 status
    bases, status = {}, {}
    for fam, parts in by_family.items():
        for p in parts:
            rel_dir = os.path.relpath(p.run_dir, root).replace("\\", "/")
            for cid, e in p.registry["configurations"].items():
                if cid in bases: raise InputContractError(f"config {cid}: registered twice")
                cov_rel = rel_dir + "/" + e["cov_file"]
                fp = _safe_rel(root, cov_rel, f"config {cid}")
                b = open(fp, "rb").read()
                if hashlib.sha256(b).hexdigest() != e["cov_file_sha256"]: raise InputContractError(f"config {cid}: registered covariance bytes differ")
                import io
                arr = np.load(io.BytesIO(b), allow_pickle=False)
                if hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest() != e["cov_array_sha256"]: raise InputContractError(f"config {cid}: registered covariance array differs")
                bases[cid] = dict(config_id=int(cid), family=fam, size_id=e.get("size_id"), registered_file=cov_rel, cov_file_sha256=e["cov_file_sha256"], cov_array_sha256=e["cov_array_sha256"], x0_CT=e.get("x0_CT"), run=rel_dir)
                status[cid] = copy.deepcopy(coverage[fam]["configuration_status"][cid])
    if len(bases) != 81 or set(status) != set(bases): raise InputContractError(f"registered base covariances: {len(bases)} != 81")
    return D3aAssets(dict(source_lock=dict(lock), ledger_sha256=ledger_sha, coverage_sha256=cov_sha, coverage=coverage, formal_runs=run_records, incomplete_attempts={k: dict(v) for k, v in inc.items()}, reproduction_crosscheck=crosscheck, base_covariances=bases, pc1_status=status), _token=_TOKEN)
