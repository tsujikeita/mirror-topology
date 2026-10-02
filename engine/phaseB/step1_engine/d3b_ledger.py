# -*- coding: utf-8 -*-
"""D-3b generation ledger (registered_assets/d3b): the nine formal generation runs (E2/E7/E8 x L1.00/L1.20/L1.50; commit 7b09c646, engine 0.93.0) whose run records and
metadata (launcher lock, final record, run manifest, bank registry, 27 completion manifests + 45 sidecars per run, executed notebook) were accepted by the ChatGPT all-9 metadata
acceptance (Step1_PhaseD_D3b_all9_7b09c646b369_metadata_acceptance.json). The ledger is a DETERMINISTIC re-derivation from the registered run records: build_d3b_ledger(root, ctx)
re-reads every record, re-verifies the generation lock constants, the run / final PASS state, the producer digest, the registry identities against the verified TwelveContext,
the registry publication receipt against the registry bytes, every completion manifest's payload SHA, every sidecar's bytes, the NPZ byte counts against the final inventory,
and the required unit set against bank spec v2 (9 added configurations x b0/b1/fit per partition); verify_d3b_ledger requires equality with that re-derivation (an edited
ledger — even with its payload SHA re-stamped — is refused); load_registered_d3b_ledger binds the committed file to the d3 pins (d3b_ledger_sha256).
intake_registered_d3b_units(root, ctx) returns the sealed D3bUnits used by (i) the read-only verifier (expected COMPLETE / NPZ identities per unit) and (ii) the formal path of
d3_bank.intake_twelve_bank (a consumed added-configuration directory must be one of the accepted units: manifest SHA, rows, purpose). The ledger records that the NPZ arrays
were NOT read by the metadata acceptance: array-verified acceptance comes from the read-only verification (d/d3b_verify_banks.py) and is recorded in the outer receipt, never here."""
from __future__ import annotations
import copy, hashlib, json, os
from typing import Dict, Optional
from .errors import InputContractError
from .d3_profile import TwelveContext, _require_ctx, load_registered_bank_spec_v2

LEDGER_SCHEMA = "d3b_generation_ledger_v1"
GENERATION_LOCK = dict(commit="7b09c646b3691260bf06b00055c5b5ad9f8540ca", inventory_sha256="4767847789a01d7f74282adfd7d3e6cfc924000307fcf10abf896c29bce1be5e", engine_version="0.93.0",
                       script_sha256="655939737a30ff9d64531ea8ab19c31c5b0b7bd93c56ff5b1690c171399b70cd", notebook_sha256="8455ba94fbceff21628a2b0625e0accc1a2f719282543cb36028ca9876af45dd",
                       pins_sha256="284ca06a7115b13327be6dba458533702985fa61e3f22a3b0064b52dd1455173", producer_digest="39510da28c19d242142c4d076841c473ba38875c8ea12041ebee2d8f78e44a7d",
                       preexecution_authorization=dict(file="Step1_PhaseD_D3b_tranche1_v2_0.93.0_decision.json", sha256="f1df0788abc08641d8bbfb28e81209c1bfa9756778fc44d478cda953690a4b95", decision="PASS_WITH_EXPLICIT_SCOPE__CONDITIONAL_PREEXECUTION_GO"))
METADATA_ACCEPTANCE = dict(decision_file="Step1_PhaseD_D3b_all9_7b09c646b369_metadata_acceptance.json", decision_sha256="461f75259418db852c4257a1b84ee327fbd718e54203be39696ee0ed85c9d652", audit_md="ChatGPT_audit_Step1_PhaseD_D3b_all9_7b09c646b369.md", audit_md_sha256="6ca3c5902dbaf40abc549eb0f8b26489609b2f43b53ce95ab807b80925a97283",
                           input_zip="bankgen_results.zip", input_zip_sha256="fbe94c55600a15eb43822825b3edead09dafb2af2a57968b43b4daba9d1687b2", decision="PASS_WITH_EXPLICIT_SCOPE", scope="nine completed production generation run records and metadata; NPZ arrays not read (0/405)", date_JST="2026-10-02")
FAMILIES = ("E2", "E7", "E8"); SIZES = ("L1.00", "L1.20", "L1.50"); REQUIRED_GATES = 13
_TOKEN = object()


def _sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()


def _read(p: str) -> bytes:
    if not os.path.isfile(p): raise InputContractError(f"registered D-3b record missing: {p}")
    return open(p, "rb").read()


def _json(p: str):
    b = _read(p)
    try: return b, json.loads(b.decode("utf-8"), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
    except ValueError as ex: raise InputContractError(f"registered D-3b record is not finite JSON: {p}") from ex


def _payload_sha(doc: dict) -> str: return _sha(json.dumps({k: v for k, v in doc.items() if k != "ledger_sha256"}, sort_keys=True, allow_nan=False, ensure_ascii=False).encode("utf-8"))


def _env_identity(env: dict) -> str:
    """Order-independent identity of the recorded numerical environment (versions + the SET of BLAS pools); recorded next to the raw fingerprint, never replacing it."""
    e = copy.deepcopy(env); e["blas_threads"] = sorted((json.dumps(x, sort_keys=True) for x in e.get("blas_threads") or []))
    return _sha(json.dumps(e, sort_keys=True, default=str).encode())


def build_d3b_ledger(phaseb_root: str, ctx: TwelveContext) -> dict:
    """Deterministic ledger of the nine registered runs (see module docstring). Raises on any inconsistency; never repairs a record."""
    ctx = _require_ctx(ctx); root = os.path.abspath(phaseb_root); runs = os.path.join(root, "registered_assets", "d3b", "runs")
    if os.path.realpath(root) != os.path.realpath(ctx.root): raise InputContractError("the registered D-3b records must be read from the root of the verified context")
    nbdir = os.path.join(root, "registered_assets", "d3b", "notebooks")
    spec2 = load_registered_bank_spec_v2(ctx); ident = ctx.identities
    if not os.path.isdir(runs): raise InputContractError("registered_assets/d3b/runs missing")
    dirs = sorted(os.listdir(runs)); parts = {}; seen_cfg = set(); digests = set(); tot = dict(partitions=0, configurations=0, directories=0, npz_files=0, npz_bytes=0, seconds=0.0, calls=0)
    for fam in FAMILIES:
        for sz in SIZES:
            cands = [d for d in dirs if d.startswith(f"{fam}_{sz}_")]
            if len(cands) != 1: raise InputContractError(f"partition {fam}/{sz}: expected exactly one registered run directory, found {cands}")
            run_dir = cands[0]; run_id = run_dir[len(f"{fam}_{sz}_"):]; out = os.path.join(runs, run_dir, "out")
            lkb, lk = _json(os.path.join(out, "launcher_lock.json")); frb, fr = _json(os.path.join(out, "d3b_final_record.json")); rmb, rm = _json(os.path.join(out, "d3b", "d3_run_manifest.json")); rgb, rg = _json(os.path.join(out, "d3b", "d3_bank_registry.json"))
            so = _read(os.path.join(out, "launcher_script_stdout.txt")); se = _read(os.path.join(out, "launcher_script_stderr.txt")); lg = _read(os.path.join(out, "d3b", "d3_bankgen_stdout.log"))
            nbp = os.path.join(nbdir, f"MirrorTopology_Step1_D3b_bankgen_v0_1_{fam}_{sz}_executed_7b09c646b369.ipynb"); nbb = _read(nbp)
            # generation lock
            if lk.get("commit") != GENERATION_LOCK["commit"] or lk.get("inventory_sha256") != GENERATION_LOCK["inventory_sha256"] or lk.get("engine_version") != GENERATION_LOCK["engine_version"] or lk.get("pins_sha256") != GENERATION_LOCK["pins_sha256"] or lk.get("spec_v2_sha256") != ident_spec2(spec2) or lk.get("covariance_receipt_sha256") != ident["covariance_receipt_sha256"]: raise InputContractError(f"{run_dir}: launcher lock differs from the accepted generation lock")
            if lk.get("family") != fam or lk.get("sizes") != [sz] or lk.get("reuse_root") is not None or lk.get("d2_ref_root") is not None or lk.get("run_dir", "").split("_")[-1] != run_id: raise InputContractError(f"{run_dir}: launcher lock scope / run id")
            # run state
            if rm.get("D3B_PASS") is not True or rm.get("stage") != "complete" or rm.get("failures") != [] or fr.get("D3B_PASS") is not True or fr["stages"].get("script_returncode") != 0 or fr["stages"].get("launcher_fallback") is not False: raise InputContractError(f"{run_dir}: run / final record is not a complete D3B_PASS")
            req = rm.get("required_inventory") or []
            if len(req) != REQUIRED_GATES or any(rm["gates"].get(k) is not True for k in req) or rm["gates"].get("G_d2_reference_dirs") is not None: raise InputContractError(f"{run_dir}: REQUIRED gates")
            pr = rm["producer"]
            if pr.get("digest") != GENERATION_LOCK["producer_digest"] or pr.get("script_sha256") != GENERATION_LOCK["script_sha256"] or pr.get("inventory_sha256") != GENERATION_LOCK["inventory_sha256"] or pr.get("engine_version") != GENERATION_LOCK["engine_version"] or pr.get("profile") != dict(profile="production_official", scale=1.0, selftest=False, skip_env_lock=False, skip_a10=False, configs=None): raise InputContractError(f"{run_dir}: producer binding differs from the accepted generation source")
            digests.add(pr["digest"])
            if rm.get("publication_stage") != "bank_registry_verified" or rm.get("published_evidence", {}).get("d3_bank_registry.json") != dict(sha256=_sha(rgb), bytes=len(rgb)): raise InputContractError(f"{run_dir}: registry publication receipt differs from the registry bytes")
            # registry identities == verified context; scope == spec v2
            if rg.get("schema") != "d3_bank_registry_v1" or rg.get("formal") is not True or rg.get("family") != fam or rg.get("sizes") != [sz] or rg.get("scale") != 1.0: raise InputContractError(f"{run_dir}: registry header")
            if rg.get("table_sha256") != ident["crn_table_sha256"] or rg.get("spec_v1_sha256") != ident["d2_spec_sha256"] or rg.get("spec_v2_sha256") != spec2["spec_sha256"] or rg.get("covariance_receipt_sha256") != ident["covariance_receipt_sha256"] or rg.get("config_map_sha256") != ident["config_map_sha256"] or rg.get("registry_sha256") != ident["registry_sha256"]: raise InputContractError(f"{run_dir}: registry identities differ from the verified context")
            cfgs = sorted(c["config_id"] for c in spec2["configurations"].values() if c["family"] == fam and c["size_id"] == sz and c["mode"] == "generate_D3b"); fixed = sorted(c["config_id"] for c in spec2["configurations"].values() if c["family"] == fam and c["size_id"] == sz and c["mode"] != "generate_D3b")
            required = [f"cfg{c}_{x}" for c in cfgs for x in ("b0", "b1", "fit")]
            if len(cfgs) != 9 or rg.get("scope", {}).get("generate") != cfgs or rg["scope"].get("fixed_first_wave") != fixed or sorted(rg.get("required_requests") or []) != sorted(required) or set(rg.get("directories") or {}) != set(required) or len(rg.get("calls") or []) != 27 or [e["name"] for e in rg.get("ledger") or []] != required: raise InputContractError(f"{run_dir}: unit scope differs from bank spec v2")
            if sorted(int(k) for k in rg.get("covariance_intake") or {}) != cfgs or any(rg["covariance_intake"][str(c)]["cov_array_sha256"] != spec2["configurations"][str(c)]["covariance"]["cov_array_sha256"] or rg["covariance_intake"][str(c)]["cov_file_sha256"] != spec2["configurations"][str(c)]["covariance"]["cov_file_sha256"] or rg["covariance_intake"][str(c)]["pc1_status"] != "PC1_PASS" or rg["covariance_intake"][str(c)]["origin"] != "twelve_added_D3a" for c in cfgs): raise InputContractError(f"{run_dir}: covariance intake identities differ from bank spec v2")
            inv_files = fr.get("output_inventory") or {}; units = {}; npz_n = 0; npz_b = 0; logical_out = lk["run_dir"] + "/out"
            for name in required:
                d = rg["directories"][name]; cid = int(name[3:].split("_")[0]); c = spec2["configurations"][str(cid)]; ci = rg["covariance_intake"][str(cid)]
                if d.get("reused") is not False or d.get("formal") is not True or not d["path"].startswith(logical_out + "/d3b/" + name): raise InputContractError(f"{run_dir}/{name}: directory record (reuse / formal / path)")
                mb, man = _json(os.path.join(out, "d3b", name, "COMPLETE.json")); body = {k: v for k, v in man.items() if k != "manifest_sha256"}
                if _sha(json.dumps(body, sort_keys=True).encode()) != man.get("manifest_sha256") or man["manifest_sha256"] != d["manifest_sha256"]: raise InputContractError(f"{run_dir}/{name}: completion manifest SHA")
                if man.get("schema") != "d3_bank_manifest_v1" or man.get("config_id") != cid or man.get("family") != fam or man.get("origin") != "twelve_added" or man.get("position_index") != c["position_index"] or man.get("formal") is not True or man.get("scale") != 1.0 or man.get("complete") is not True or man.get("roles") != ["model_matched", "model_native", "ref_native"] or man.get("selections") != ["float64"]: raise InputContractError(f"{run_dir}/{name}: manifest identity")
                if man.get("spec_v2_sha256") != spec2["spec_sha256"] or man.get("covariance_receipt_sha256") != ident["covariance_receipt_sha256"] or man.get("table_sha256") != ident["crn_table_sha256"] or man.get("spec_v1_sha256") != ident["d2_spec_sha256"] or man.get("config_map_sha256") != ident["config_map_sha256"] or man.get("root_sha256") != rg["covariance_intake"][str(cid)]["root_sha256"]: raise InputContractError(f"{run_dir}/{name}: manifest binding")
                purpose, batch = ("fitting", 0) if name.endswith("_fit") else ("evaluation", int(name[-1])); want_rows = 200_000 if purpose == "fitting" else (1_000_000 if batch == 0 else 3_000_000)
                if man.get("purpose") != purpose or man.get("batch_id") != batch or man.get("n_rows") != want_rows or d["n_rows"] != want_rows or d["n_clusters"] != man["n_clusters"] or d["purpose"] != purpose: raise InputContractError(f"{run_dir}/{name}: purpose / batch / rows")
                npz = {}
                for sh in man["shards"]:
                    sb = _read(os.path.join(out, "d3b", name, sh["sidecar"])); side = json.loads(sb)
                    if _sha(sb) != sh["sidecar_sha256"] or side.get("file_sha256") != sh["file_sha256"] or side["environment"]["producer"]["digest"] != pr["digest"] or side.get("covariance") != c["covariance"]: raise InputContractError(f"{run_dir}/{name}: sidecar {sh['sidecar']}")
                    rel = f"d3b/{name}/{sh['file']}"; ib = inv_files.get(rel)
                    if not isinstance(ib, dict) or ib.get("sha256") is not None or ib.get("bytes") != side["bytes"]: raise InputContractError(f"{run_dir}/{name}: NPZ byte count {rel} differs between sidecar and final inventory")
                    if os.path.exists(os.path.join(out, "d3b", name, sh["file"])): raise InputContractError(f"{run_dir}/{name}: NPZ arrays must not be registered in the repository")
                    npz[sh["file"]] = dict(sha256=sh["file_sha256"], bytes=side["bytes"], rows=sh["rows"], array_sha256=dict(side["array_sha256"]))
                    npz_n += 1; npz_b += side["bytes"]
                units[name] = dict(config_id=cid, position_index=c["position_index"], purpose=purpose, batch_id=batch, path=d["path"], manifest_sha256=man["manifest_sha256"], n_rows=man["n_rows"], n_clusters=man["n_clusters"], crn_group=man["crn_group"], root_sha256=dict(man["root_sha256"]), covariance=dict(cov_file_sha256=ci["cov_file_sha256"], cov_array_sha256=ci["cov_array_sha256"], receipt=ci["receipt"]), npz=npz, seconds=d["seconds"])
            if len(units) != 27 or npz_n != 45: raise InputContractError(f"{run_dir}: unit / NPZ counts")
            # final inventory covers the metadata files of this record set (SHA for non-NPZ)
            for rel in ("launcher_lock.json", "launcher_script_stdout.txt", "launcher_script_stderr.txt", "d3b/d3_run_manifest.json", "d3b/d3_bank_registry.json", "d3b/d3_bankgen_stdout.log"):
                if inv_files.get(rel, {}).get("sha256") != _sha(_read(os.path.join(out, rel))): raise InputContractError(f"{run_dir}: final inventory SHA differs for {rel}")
            seen_cfg |= set(cfgs)
            parts[f"{fam}_{sz}"] = dict(family=fam, size_id=sz, run_id=run_id, run_dir=lk["run_dir"], run_root=logical_out, registered_dir=f"registered_assets/d3b/runs/{run_dir}", configuration_ids=cfgs, fixed_first_wave_ids=fixed,
                                       records=dict(launcher_lock_sha256=_sha(lkb), final_record_sha256=_sha(frb), run_manifest_sha256=_sha(rmb), bank_registry_sha256=_sha(rgb), script_stdout_sha256=_sha(so), script_stderr_sha256=_sha(se), script_log_sha256=_sha(lg), executed_notebook=dict(file=os.path.basename(nbp), sha256=_sha(nbb), bytes=len(nbb))),
                                       gates={k: rm["gates"][k] for k in req}, a10_max_rel=rm["a10_cross_check"]["max_rel"], environment_fingerprint=rg["environment"]["fingerprint"], environment_identity_order_independent=_env_identity(rm["env"]), environment=dict(python=rm["env"]["python"], numpy=rm["env"]["numpy"], scipy=rm["env"]["scipy"], healpy=rm["env"]["healpy"], pot=rm["env"]["pot"], camb=rm["env"]["camb"]),
                                       producer_digest=pr["digest"], script_seconds=rm["seconds"], directories=27, npz_files=npz_n, npz_bytes=npz_b, drive_free_bytes_at_start=lk["drive_free_bytes"], units=units)
            tot["partitions"] += 1; tot["configurations"] += len(cfgs); tot["directories"] += 27; tot["npz_files"] += npz_n; tot["npz_bytes"] += npz_b; tot["seconds"] += rm["seconds"]; tot["calls"] += len(rg["calls"])
    if len(seen_cfg) != 81 or len(digests) != 1 or tot["directories"] != 243 or tot["npz_files"] != 405: raise InputContractError("ledger totals")
    env_ids = {p["environment_identity_order_independent"] for p in parts.values()}
    doc = dict(schema=LEDGER_SCHEMA, source_lock=copy.deepcopy(GENERATION_LOCK), context_identities=dict(ident), bank_spec_v2_sha256=spec2["spec_sha256"], partitions=parts, totals=tot,
               environment_note=dict(raw_fingerprints=sorted({p["environment_fingerprint"] for p in parts.values()}), order_independent_identities=sorted(env_ids), statement="the nine raw environment fingerprints differ only by the enumeration ORDER of the BLAS pool list (4 pools; identical libraries / versions / thread counts); raw values are retained unchanged; the order-independent identity is recorded for comparison only and does not waive the exact-fingerprint requirement of cache reuse"),
               parent_runtime_note="eight executed notebooks start at an execution count other than 1 and print 'Drive already mounted' (one parent Colab runtime reused across runs); each run used a fresh named attempt directory and a separate child process with identical accepted source / profile and a passing live preflight; recorded as a limitation, not a cause for regeneration (metadata acceptance §2)",
               external_acceptance=copy.deepcopy(METADATA_ACCEPTANCE), array_acceptance=dict(status="PENDING", statement="NPZ arrays were not read by the metadata acceptance (0/405); array-verified acceptance is established by the read-only verification (d/d3b_verify_banks.py) and recorded in the outer receipt, never in this ledger"),
               scope="Generation records and metadata of the nine D-3b partition runs (Drive outputs: 243 directories, 405 NPZ, 27.217 GB). NOT: numerical acceptance of the NPZ arrays, read-only verification, formal bank supply / 12-position profile, fixed plans, D-2W, noise, calibration, labels, ENGINE_VALID.")
    doc["ledger_sha256"] = _payload_sha(doc); return doc


def ident_spec2(spec2: dict) -> str: return spec2["spec_sha256"]


def verify_d3b_ledger(doc: dict, phaseb_root: str, ctx: TwelveContext) -> dict:
    """The document must equal its re-derivation from the registered run records (payload SHA + full content); returns a deep copy."""
    if not isinstance(doc, dict) or doc.get("schema") != LEDGER_SCHEMA: raise InputContractError("D-3b ledger schema")
    if doc.get("ledger_sha256") != _payload_sha(doc): raise InputContractError("D-3b ledger payload SHA")
    fresh = build_d3b_ledger(phaseb_root, ctx)
    if doc != fresh: raise InputContractError("D-3b ledger differs from its re-derivation from the registered run records")
    return copy.deepcopy(fresh)


def load_registered_d3b_ledger(phaseb_root: str, ctx: TwelveContext) -> dict:
    """The committed registered_assets/d3b/d3b_generation_ledger.json: payload identity == d3 pins (d3b_ledger_sha256) and content == re-derivation."""
    ctx = _require_ctx(ctx); root = os.path.abspath(phaseb_root)
    if os.path.realpath(root) != os.path.realpath(ctx.root): raise InputContractError("the registered D-3b ledger must be read from the root of the verified context")
    b, doc = _json(os.path.join(root, "registered_assets", "d3b", "d3b_generation_ledger.json"))
    if doc.get("ledger_sha256") != ctx._d["pins"].get("d3b_ledger_sha256"): raise InputContractError("registered D-3b ledger identity differs from the pins")
    out = verify_d3b_ledger(doc, root, ctx); out["_file_sha256"] = _sha(b); return out


class D3bUnits:
    """Sealed, verified view of the accepted D-3b units (243) and their expected NPZ identities (405). Public views are deep copies; construction only by intake_registered_d3b_units."""
    __slots__ = ("_d", "_seal")

    def __init__(self, d: dict, *, _token=None):
        if _token is not _TOKEN: raise InputContractError("D3bUnits must be created by intake_registered_d3b_units()")
        object.__setattr__(self, "_d", d); object.__setattr__(self, "_seal", _TOKEN)

    def __setattr__(self, n, v): raise AttributeError("D3bUnits is immutable")
    def __delattr__(self, n): raise AttributeError("D3bUnits is immutable")
    @property
    def verified(self): return self._seal is _TOKEN
    @property
    def ledger_sha256(self): return self._d["ledger"]["ledger_sha256"]
    @property
    def ledger_file_sha256(self): return self._d["ledger"]["_file_sha256"]
    @property
    def array_accepted(self): return self._d.get("receipt") is not None
    @property
    def outer_receipt(self): return copy.deepcopy(self._d.get("receipt"))
    @property
    def receipt_sha256(self): return None if self._d.get("receipt") is None else self._d["receipt"]["receipt_sha256"]
    @property
    def source_lock(self): return copy.deepcopy(self._d["ledger"]["source_lock"])
    @property
    def partitions(self): return copy.deepcopy(self._d["ledger"]["partitions"])
    @property
    def unit_names(self): return sorted(self._d["units"])
    def unit(self, name: str) -> dict:
        if name not in self._d["units"]: raise InputContractError(f"{name}: not an accepted D-3b unit")
        return copy.deepcopy(self._d["units"][name])
    def partition_of(self, config_id: int) -> dict:
        for k, p in self._d["ledger"]["partitions"].items():
            if config_id in p["configuration_ids"]: return copy.deepcopy(dict(p, key=k))
        raise InputContractError(f"config {config_id}: not an accepted D-3b configuration")
    def require_unit_manifest(self, name: str, manifest_sha256: str, n_rows: int, purpose: str) -> dict:
        """The consumed directory must be the accepted unit: manifest SHA / rows / purpose equal the ledger record."""
        u = self.unit(name)
        if u["manifest_sha256"] != manifest_sha256 or u["n_rows"] != n_rows or u["purpose"] != purpose: raise InputContractError(f"{name}: directory is not the accepted D-3b unit recorded in the ledger")
        return u


def intake_registered_d3b_units(phaseb_root: str, ctx: TwelveContext, require_array_acceptance: bool = True) -> D3bUnits:
    """Sealed units of the accepted generation ledger. With require_array_acceptance (default) the registered outer receipt (array-verified acceptance) must exist, verify and
    bind to this ledger; the returned view then reports array_accepted=True (required by the formal path of d3_bank.intake_twelve_bank). require_array_acceptance=False yields
    the ledger-only view (array_accepted=False) used by the read-only verifier itself, which must not depend on its own outcome."""
    ledger = load_registered_d3b_ledger(phaseb_root, ctx); units = {}; receipt = None
    if require_array_acceptance:
        receipt = load_registered_d3b_outer_receipt(phaseb_root, ctx)
        if receipt["generation"]["ledger_payload_sha256"] != ledger["ledger_sha256"] or receipt["generation"]["ledger_file_sha256"] != ledger["_file_sha256"]: raise InputContractError("outer receipt is not bound to the registered ledger")
    for key, p in ledger["partitions"].items():
        for name, u in p["units"].items():
            if name in units: raise InputContractError(f"{name}: duplicate unit across partitions")
            units[name] = dict(u, partition=key, run_id=p["run_id"])
    if len(units) != 243: raise InputContractError("accepted unit count")
    return D3bUnits(dict(ledger=ledger, units=units, receipt=receipt), _token=_TOKEN)


# ------------------------------------------------------------------------------------------------------------------------------------ outer receipt (array acceptance)
RECEIPT_SCHEMA = "d3b_outer_receipt_v1"
VERIFICATION_LOCK = dict(commit="269c6d56fb7588b21472ddea0618df3f88a6cd75", engine_version="0.95.0", inventory_sha256="008e125c50d2215c5dc3f5a4831f368c7feca856dc3a3819614770afc1abe7ff", script_sha256="dc57de8ba8c2a15a4ab531d8be02cc1ecbd1c28e9912b23dead915f632a780a1",
                         notebook_sha256="5a556682d2dff84abfdcb21314cb4d43f8271386b384c0dcf96cdf6df831a7ca", modules_digest="f0a4ee17bf82cf1a517f898ea3fede9486964ef63ef0e704ba8c63fa6d874df8",
                         preexecution_authorization=dict(file="Step1_PhaseD_D3b_tranche2_v2_0.95.0_decision.json", sha256="48a0d3b14768f5a06958a1b8d97f4e22d3b684e5ab2701a6cd9d9f78cec2db9a", decision="PASS_WITH_EXPLICIT_SCOPE / GO_CONDITIONAL_ON_EXACT_LOCK_AND_EXISTING_CHECKS"))
ARRAY_ACCEPTANCE = dict(decision_file="Step1_PhaseD_D3b_readonly_269c6d56fb75_acceptance.json", decision_sha256="424a547127276a2f0e8e8170b67573621f6f4583632d1b98a7627b1a4a558ee3", audit_md="ChatGPT_audit_Step1_PhaseD_D3b_readonly_269c6d56fb75.md", audit_md_sha256="237c68c612038fd94ddea363f26ba6805e993dfa5c7a62256780be3768870616",
                        input_zip="d3b_verify_results.zip", input_zip_sha256="80596237ff33d2283a6762174100a71ff448ec714ee39d59a260ad5110afd7c1", decision="PASS_WITH_EXPLICIT_SCOPE", acceptance_kind="AUDITED_COLAB_FULL_ARRAY_INTEGRITY_RESULTS", date_JST="2026-10-02",
                        scope="nine accepted-full read-only verification runs: 243 units / 405 NPZ file SHA and bytes == ledger expectations, every array SHA == sidecar (verify_twelve_bank_dir), finiteness / dtype / cid / ranges / UIDs / keys, cid equality across each partition and with the fixed D-2 family reference (3 units re-verified through the reuse binding); the auditor read no production NPZ (0/405) and recomputed no statistics",
                        not_approved=["independent rehash of the 405 production NPZ by the auditor", "raw latent R/z or generation-root comparison", "real-bank twelve-position official profile / gate", "fixed BootstrapPlan / FittingPlan identities", "D-2W / noise / calibration / usable / observed labels / ENGINE_VALID"])
_VERIFY_FILES = ("verify_lock.json", "verify_final_record.json", "verify_stdout.txt", "verify_stderr.txt")


def build_d3b_outer_receipt(phaseb_root: str, ctx: TwelveContext) -> dict:
    """Deterministic outer receipt of the array-verified acceptance: for each of the nine partitions the registered read-only verification record (report / lock / final / stdout /
    stderr / executed notebook under registered_assets/d3b/verify*) is re-read and bound to the verification lock constants, to the generation ledger (partition run id / run
    root / unit manifest SHAs / NPZ file SHA + bytes), and to the acceptance conditions (accepted_full, binding, coverage, all_ok, no failures, cid correspondence incl. the D-2
    reference, structure, verifier source bound). Records every file's SHA. The generation ledger itself is never rewritten (array_acceptance stays PENDING there)."""
    ctx = _require_ctx(ctx); root = os.path.abspath(phaseb_root)
    if os.path.realpath(root) != os.path.realpath(ctx.root): raise InputContractError("the registered D-3b receipt must be read from the root of the verified context")
    ledger = load_registered_d3b_ledger(root, ctx); vroot = os.path.join(root, "registered_assets", "d3b", "verify"); nbdir = os.path.join(root, "registered_assets", "d3b", "verify_notebooks"); spec2 = load_registered_bank_spec_v2(ctx)
    parts = {}; tot = dict(partitions=0, units=0, npz_files=0, npz_bytes=0, seconds=0.0); env_ids = set()
    for key, P in ledger["partitions"].items():
        fam, sz = P["family"], P["size_id"]; d = os.path.join(vroot, key)
        rb, rep = _json(os.path.join(d, "report", f"d3b_verify_{fam}_{sz}.json")); lkb, lk = _json(os.path.join(d, "verify_lock.json")); fnb, fn = _json(os.path.join(d, "verify_final_record.json")); so = _read(os.path.join(d, "verify_stdout.txt")); se = _read(os.path.join(d, "verify_stderr.txt"))
        nbp = os.path.join(nbdir, f"MirrorTopology_Step1_D3b_verify_v0_1_{fam}_{sz}_executed_269c6d56fb75.ipynb"); nbb = _read(nbp)
        VL = VERIFICATION_LOCK
        if lk.get("commit") != VL["commit"] or lk.get("inventory_sha256") != VL["inventory_sha256"] or lk.get("script_sha256") != VL["script_sha256"] or lk.get("engine") != VL["engine_version"] or lk.get("ledger_sha256") != ledger["ledger_sha256"] or lk.get("family") != fam or lk.get("size") != sz or lk.get("run_root") != P["run_root"] or lk.get("run_id") != P["run_id"] or not lk.get("d2_ref_root"): raise InputContractError(f"{key}: verification lock")
        if fn.get("verify_pass") is not True or fn.get("exit_code") != 0 or fn.get("launcher_fallback") is not False or fn.get("lock") != lk: raise InputContractError(f"{key}: verification final record")
        vs = rep.get("verifier_source") or {}
        if rep.get("schema") != "d3b_postrun_verification_v1" or rep.get("mode") != "accepted" or rep.get("stage") != "complete" or rep.get("exit_code") != 0 or rep.get("verification_scope") != "accepted_full" or rep.get("accepted_run_binding") is not True or rep.get("coverage_complete") is not True or rep.get("all_ok") is not True or rep.get("failures") != [] or rep.get("unchecked_units") != [] or rep.get("cid_correspondence_ok") is not True or rep.get("n0_plus_3n0_structure_ok") is not True: raise InputContractError(f"{key}: verification report flags")
        if vs.get("source_bound") is not True or vs.get("ledger_bound") is not True or vs.get("engine") != VL["engine_version"] or vs.get("inventory_sha256") != VL["inventory_sha256"] or vs.get("script_sha256") != VL["script_sha256"] or vs.get("modules_digest") != VL["modules_digest"] or rep.get("d3b_ledger_sha256") != ledger["ledger_sha256"]: raise InputContractError(f"{key}: verifier source")
        gs = rep.get("generator_source") or {}
        if gs.get("commit") != GENERATION_LOCK["commit"] or gs.get("run_id") != P["run_id"] or gs.get("producer_digest") != P["producer_digest"] or gs.get("environment_fingerprint") != P["environment_fingerprint"] or rep.get("run_root") != P["run_root"] or rep.get("path_map") != {} or rep.get("family") != fam or rep.get("size_id") != sz or len(se) != 0: raise InputContractError(f"{key}: generator binding / relocation / stderr")
        units = rep.get("units") or {}
        if set(units) != set(P["units"]) or rep.get("checked_units") != list(P["units"]): raise InputContractError(f"{key}: unit set")
        n_npz = 0; n_bytes = 0
        for name, u in units.items():
            E = P["units"][name]
            if u.get("ok") is not True or u.get("arrays_verified_against_sidecar") is not True or u.get("manifest_sha256_ok") is not True or u.get("formal") is not True or u.get("manifest_sha256") != E["manifest_sha256"] or u.get("n_rows") != E["n_rows"] or u.get("purpose") != E["purpose"] or u.get("config_id") != E["config_id"]: raise InputContractError(f"{key}/{name}: unit record")
            shards = u.get("shards") or []
            if {s["file"] for s in shards} != set(E["npz"]): raise InputContractError(f"{key}/{name}: NPZ set")
            for s in shards:
                e = E["npz"][s["file"]]
                if s.get("file_sha256") != e["sha256"] or s.get("bytes") != e["bytes"] or s.get("matches_manifest") is not True or s.get("matches_ledger") is not True or s.get("inventory_bytes_match") is not True: raise InputContractError(f"{key}/{name}/{s['file']}: measured NPZ identity differs from the ledger")
                n_npz += 1; n_bytes += s["bytes"]
            cid = u.get("cid") or {}
            if cid.get("n") != E["n_rows"] or cid.get("monotone") is not True or cid.get("unique") != E["n_clusters"]: raise InputContractError(f"{key}/{name}: cid record")
            for role, a in (u.get("arrays") or {}).items():
                if a["T1"]["n"] != E["n_rows"] or a["T1"]["finite"] != E["n_rows"] or a["T2"]["finite"] != E["n_rows"]: raise InputContractError(f"{key}/{name}/{role}: finiteness")
            if set(u.get("arrays") or {}) != {"model_matched__float64", "model_native__float64", "ref_native__float64"}: raise InputContractError(f"{key}/{name}: role x selection set")
        d2 = rep.get("d2_reference") or {}; fr = spec2["family_reference"][fam]["units"]
        if d2.get("verified") is not True or set(d2.get("units") or {}) != set(fr) or any(d2["units"][u]["manifest_sha256"] != fr[u]["manifest_sha256"] or d2["units"][u]["n_rows"] != fr[u]["n_rows"] for u in fr): raise InputContractError(f"{key}: D-2 reference binding")
        corr = rep.get("cid_correspondence") or {}
        if len(corr) != 27 or any(not (c.get("equal_across_partition") is True and c.get("reference_present") is True and c.get("equal_to_d2_reference") is True) for c in corr.values()): raise InputContractError(f"{key}: cid correspondence")
        if n_npz != 45 or n_bytes != P["npz_bytes"]: raise InputContractError(f"{key}: NPZ totals")
        env_ids.add(_env_identity(rep["verification_environment"]))
        parts[key] = dict(family=fam, size_id=sz, generation_run_id=P["run_id"], run_root=P["run_root"], d2_ref_root=lk["d2_ref_root"], units=27, npz_files=n_npz, npz_bytes=n_bytes, seconds=rep["seconds"], all_ok=True, accepted_run_binding=True, coverage_complete=True, cid_correspondence_ok=True, d2_reference_verified=True,
                          d2_reference_units={u: dict(manifest_sha256=d2["units"][u]["manifest_sha256"], n_rows=d2["units"][u]["n_rows"], shards=d2["units"][u]["shards"]) for u in sorted(d2["units"])},
                          records=dict(report_sha256=_sha(rb), lock_sha256=_sha(lkb), final_sha256=_sha(fnb), stdout_sha256=_sha(so), stderr_sha256=_sha(se), executed_notebook=dict(file=os.path.basename(nbp), sha256=_sha(nbb), bytes=len(nbb)), registered_dir=f"registered_assets/d3b/verify/{key}"),
                          verification_environment=dict(python=rep["verification_environment"].get("python"), numpy=rep["verification_environment"].get("numpy"), scipy=rep["verification_environment"].get("scipy"), healpy=rep["verification_environment"].get("healpy"), pot=rep["verification_environment"].get("pot"), camb=rep["verification_environment"].get("camb")))
        tot["partitions"] += 1; tot["units"] += 27; tot["npz_files"] += n_npz; tot["npz_bytes"] += n_bytes; tot["seconds"] += rep["seconds"]
    if tot != dict(partitions=9, units=243, npz_files=405, npz_bytes=ledger["totals"]["npz_bytes"], seconds=tot["seconds"]): raise InputContractError("receipt totals")
    doc = dict(schema=RECEIPT_SCHEMA, generation=dict(ledger_payload_sha256=ledger["ledger_sha256"], ledger_file_sha256=ledger["_file_sha256"], source_lock=copy.deepcopy(GENERATION_LOCK), metadata_acceptance=copy.deepcopy(METADATA_ACCEPTANCE), ledger_array_acceptance_field="PENDING (generation-time record; never rewritten)"),
               verification=dict(copy.deepcopy(VERIFICATION_LOCK), environment_identity_order_independent=sorted(env_ids), camb_note="the read-only verifier neither installs nor requires CAMB; the verification environment is recorded separately from the generation environment"),
               array_acceptance=copy.deepcopy(ARRAY_ACCEPTANCE), partitions=parts, totals=tot,
               statement="ACCEPTED (scoped): the 405 NPZ of the 81 added configurations were read in full on Colab by the accepted verifier at the verification lock and found identical to the registered expectations (file SHA / bytes / every array SHA / structure / cid correspondence incl. the fixed D-2 family reference); the acceptance is the auditor's scoped acceptance of these records, not an independent re-read. Consumption of the added banks as FORMAL inputs (d3_bank.intake_twelve_bank formal=True) is therefore allowed through the registered units; everything scientific downstream (real-bank profile / gate, plan fixation, calibration, labels) remains separately gated.")
    doc["receipt_sha256"] = _sha(json.dumps({k: v for k, v in doc.items() if k != "receipt_sha256"}, sort_keys=True, allow_nan=False, ensure_ascii=False).encode("utf-8")); return doc


def verify_d3b_outer_receipt(doc: dict, phaseb_root: str, ctx: TwelveContext) -> dict:
    if not isinstance(doc, dict) or doc.get("schema") != RECEIPT_SCHEMA: raise InputContractError("D-3b outer receipt schema")
    if doc.get("receipt_sha256") != _sha(json.dumps({k: v for k, v in doc.items() if k != "receipt_sha256"}, sort_keys=True, allow_nan=False, ensure_ascii=False).encode("utf-8")): raise InputContractError("D-3b outer receipt payload SHA")
    fresh = build_d3b_outer_receipt(phaseb_root, ctx)
    if doc != fresh: raise InputContractError("D-3b outer receipt differs from its re-derivation from the registered verification records")
    return copy.deepcopy(fresh)


def load_registered_d3b_outer_receipt(phaseb_root: str, ctx: TwelveContext) -> dict:
    """The committed registered_assets/d3b/d3b_outer_receipt.json: payload identity == d3 pins (d3b_outer_receipt_sha256) and content == re-derivation."""
    ctx = _require_ctx(ctx); root = os.path.abspath(phaseb_root)
    if os.path.realpath(root) != os.path.realpath(ctx.root): raise InputContractError("the registered D-3b receipt must be read from the root of the verified context")
    b, doc = _json(os.path.join(root, "registered_assets", "d3b", "d3b_outer_receipt.json"))
    if doc.get("receipt_sha256") != ctx._d["pins"].get("d3b_outer_receipt_sha256"): raise InputContractError("registered D-3b outer receipt identity differs from the pins")
    out = verify_d3b_outer_receipt(doc, root, ctx); out["_file_sha256"] = _sha(b); return out
