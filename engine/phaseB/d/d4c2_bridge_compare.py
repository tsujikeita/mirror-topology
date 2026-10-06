# -*- coding: utf-8 -*-
"""D4C-2a environment bridge comparison (audit D4C2a_v3_0.110.0: `D4C2a_v3_0.110.0_bridge_comparison_spec.json`, schema D4C2a_environment_bridge_comparison_spec_v1;
revised after audit D4C2a_v4_0.111.0: R-D4BRIDGE-A producer provenance / R-D4BRIDGE-B typed index identity / R-D4BRIDGE-C profile document / N-D4BRIDGE-ERROR-REPORT).

Compares ONE instrumented E2 N=3 probe produced under the amended registered environment (the NEW probe: engine 0.110.0, Python 3.13.16, launched by the partial notebook
v0.3) with the registered baseline probe (engine 0.107.0, Python 3.13.15, attempt 20261005T100239Z_386d63207c) exactly as the audit contract prescribes:
  * the whole partial payload SHA and the whole archive SHA set are NOT required to match (the partial carries its engine / module and gate-environment provenance);
  * the 15 per-row records (family_result x 3, three_position_result x 9, pseudo_family_plan transition x 3) are mapped by their TYPED identity and global row — the archive
    index entry's complete identity must equal the specification's identity under a type-strict recursive comparison (bool is never an int; a global row is an int), family_result
    and the plan transition by pseudo_index, the three three_position_results of a row by the three_position_result_sha256 that the row's plan transition names per size — and
    must agree with the specification's content SHA and bytes EXACTLY, in BOTH probes, with no missing / extra / duplicate row; the registry record is the specification's
    registry record; the remaining entry is exactly one family_partial_calibration transition (the partial itself: its SHA is allowed to change);
  * required_equal_partial_fields of the two published partial records are content-equal (canonical serialization);
  * the NEW probe's PRODUCER PROVENANCE is authenticated against the fixed producer tree given as --phaseb (the tree that produced it; its step1_engine is the one imported here):
    the run record's trusted inventory is the producer driver's REQUIRED_PARTIAL extracted by AST (exact names and order, every gate True), the run record's source / pins / script /
    engine bind to that tree's actual files and inventory, the launcher lock (bytes hashed into the run record's attempt and the final record) binds the same tree, the registered
    asset SHAs, the family / probe / instrument / campaign / commitment settings, the final record is a complete, failure-free, non-fallback exit-0 launch of this attempt whose
    pre-check / pre-launch live source bindings name the lock's commit and inventory with a clean tree, the attempt id is the run directory, and the official twelve gate and the
    first-wave gate were live-collected passes;
  * the profile DOCUMENT is validated semantically (schema / producer target inventory / wrappers + cProfile on / segments == probe_n with per-segment indices / no missing
    targets / per-target accounting) and reconciled with the run record's profile summary and receipt (SHA / bytes);
  * the NEW record is read through its own unmodified reader (load_partial_record + verify_partial_record with the registered identities of the producing tree and
    current_source_binding=True);
  * environments are verified SEPARATELY: the baseline gate environment equals the registered history entry (3.13.15 ...), the new gate environment equals the producing tree's
    EXPECTED_VERS (3.13.16 ...), both gates passed with environment_source live_collected;
  * the original files are never modified; on ANY mismatch the report says so and the exit code is 1 (no retry, no tolerance: the differences are listed for analysis); an
    unexpected exception is also published as a failure report (exit 1) where the report path is writable.
Exit code 0 = every contract item satisfied; 1 = at least one mismatch / refusal (report published either way); 2 = usage error.
This is a comparison of a PROBE: it approves nothing (no screen / certificate / calibration GO, no numerical equivalence beyond the fixed first 3 rows)."""
from __future__ import annotations
import argparse, ast, hashlib, json, os, sys, time, traceback, zipfile, tempfile, shutil

SPEC_SCHEMA = "D4C2a_environment_bridge_comparison_spec_v1"
REPORT_SCHEMA = "d4c2_bridge_comparison_report_v2"
SIZES = ("L1.00", "L1.20", "L1.50")
LOCK_SCHEMA = "d4c1_partial_launcher_lock_v1"; FINAL_SCHEMA = "d4c1_partial_launcher_final_record_v1"; RUN_SCHEMA = "d4c1_run_record_v1"
REL_TOL = 1e-9                                                                        # float bookkeeping identities of the profile (sums of wall times): NOT a scientific tolerance


def sha(p: str) -> str: return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _hex64(v) -> bool: return isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)


def _is_row(v) -> bool: return isinstance(v, int) and not isinstance(v, bool)


def teq(a, b) -> bool:
    """Type-strict recursive equality of JSON values (local to the comparator: it must work with the 0.110.0 producer tree): same Python type at every node (bool is not int, int is
    not float, str is not bool), same dict keys, same list length, equal leaves."""
    if type(a) is not type(b): return False
    if isinstance(a, dict): return set(a) == set(b) and all(teq(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)): return len(a) == len(b) and all(teq(x, y) for x, y in zip(a, b))
    return a == b


def _close(a, b) -> bool: return isinstance(a, float) and isinstance(b, float) and abs(a - b) <= REL_TOL * max(1.0, abs(a), abs(b))


def ast_required_partial(driver_path: str) -> list:
    """The trusted REQUIRED_PARTIAL of the PRODUCER driver, read from its source by AST (never from the run record)."""
    tree = ast.parse(open(driver_path, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "REQUIRED_PARTIAL" for t in node.targets):
            val = ast.literal_eval(node.value)
            if not isinstance(val, tuple) or not all(isinstance(x, str) for x in val): raise ValueError("REQUIRED_PARTIAL is not a tuple of names")
            return list(val)
    raise ValueError("REQUIRED_PARTIAL not found in the producer driver")


def _unpack(src: str, work: str, tag: str) -> dict:
    """A probe is given as the launcher zip (byte-preserved) or as its unpacked directory (the launcher's output anchor: lock, final record, run_<attempt>/, stdout / stderr)."""
    if os.path.isfile(src) and src.lower().endswith(".zip"):
        root = os.path.join(work, tag); os.makedirs(root)
        with zipfile.ZipFile(src) as z:
            for n in z.namelist():
                if n.startswith("/") or ".." in n.split("/"): raise ValueError(f"{src}: unsafe member {n!r}")
            z.extractall(root)
        zsha = sha(src)
    elif os.path.isdir(src): root, zsha = os.path.realpath(src), None
    else: raise ValueError(f"{src}: not a zip file or a directory")
    runs = sorted(d for d in os.listdir(root) if d.startswith("run_") and os.path.isdir(os.path.join(root, d)))
    if len(runs) != 1: raise ValueError(f"{src}: exactly one run_* directory expected, found {runs}")
    rd = os.path.join(root, runs[0]); recs = sorted(f for f in os.listdir(rd) if f.startswith("d4c1_probe_") and f.endswith("_record.json")); rr = sorted(f for f in os.listdir(rd) if f.startswith("d4c1_probe_") and f.endswith("_run.json"))
    if len(recs) != 1 or len(rr) != 1: raise ValueError(f"{src}: exactly one probe record / run record pair expected")
    return dict(root=root, zip_sha256=zsha, run_dir=rd, attempt=runs[0][len("run_"):], record_file=os.path.join(rd, recs[0]), run_file=os.path.join(rd, rr[0]), archive=os.path.join(rd, "archive"),
                profile_file=os.path.join(rd, recs[0].replace("_record.json", "_profile.json")), lock_file=os.path.join(root, "d4c1_partial_lock.json"), final_file=os.path.join(root, "d4c1_partial_final_record.json"))


def _load_json(path: str):
    if not os.path.isfile(path): raise ValueError(f"missing file: {path}")
    return json.load(open(path, encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--phaseb", required=True, help="the FIXED producer tree of the NEW probe (its step1_engine is imported; its inventory must equal the new run record's / lock's inventory SHA)")
    ap.add_argument("--spec", required=True, help="the audit's bridge comparison specification JSON"); ap.add_argument("--baseline", required=True, help="baseline probe: launcher zip or unpacked directory"); ap.add_argument("--new", required=True, help="new probe: launcher zip or unpacked directory")
    ap.add_argument("--expected-commit", default=None, help="the fixed producer commit of the audit GO (40 hex); the new lock and the live pre-check / pre-launch heads must name it")
    ap.add_argument("--out", required=True, help="report JSON path (must not exist)")
    a = ap.parse_args()
    if os.path.lexists(a.out): print("--out must not exist", file=sys.stderr); return 2
    for p in (a.phaseb, a.spec, a.baseline, a.new):
        if not os.path.exists(p): print(f"missing: {p}", file=sys.stderr); return 2
    if a.expected_commit is not None and not (isinstance(a.expected_commit, str) and len(a.expected_commit) == 40 and all(c in "0123456789abcdef" for c in a.expected_commit)): print("--expected-commit must be 40 hex", file=sys.stderr); return 2
    R = dict(schema=REPORT_SCHEMA, spec=dict(file=os.path.realpath(a.spec), sha256=sha(a.spec)), phaseb=os.path.realpath(a.phaseb), expected_commit=a.expected_commit, started_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), checks={}, mismatches=[], notes=[],
             scope="comparison of ONE instrumented E2 N=3 probe against the registered baseline probe under the audit's bridge contract; approves no screen / certificate / calibration and proves no equivalence beyond the fixed first 3 rows; originals untouched")
    work = tempfile.mkdtemp(prefix="d4c2_bridge_")
    try:
        try: return _compare(a, R, work)
        except Exception as ex:                                                                                         # N-D4BRIDGE-ERROR-REPORT: an ordinary parsing / contract / reader exception is a published failure
            R["checks"]["unexpected_error"] = dict(ok=False, detail=repr(ex), traceback=traceback.format_exc()); R["mismatches"].append("unexpected_error"); return _finish(R, a.out, 1)
    finally: shutil.rmtree(work, ignore_errors=True)


def _compare(a, R: dict, work: str) -> int:
    phaseb = os.path.realpath(a.phaseb); sys.path.insert(0, phaseb)
    from step1_engine import serialization as ser, __version__
    from step1_engine.archive import Archive
    from step1_engine.checkpoint import module_shas
    from step1_engine.d4c1_partial import load_partial_record, verify_partial_record, PARTIAL_SCHEMA
    from step1_engine.official_gate import EXPECTED_VERS, EXPECTED_VERS_HISTORY, VERSION_KEYS
    from step1_engine.profiling import TARGETS, SEGMENT_TARGET, PROFILE_SCHEMA
    from step1_engine.d3_profile import twelve_context
    from step1_engine.d4c0_registry import load_registered_w2_context
    from step1_engine.grid_registry import load_registry
    from step1_engine.twelve_assets import intake_registered_twelve_assets
    R["engine_version"] = __version__
    def chk(name, ok, detail=None):
        R["checks"][name] = dict(ok=bool(ok), **({} if detail is None else dict(detail=detail)))
        if not ok: R["mismatches"].append(name)
        return bool(ok)
    spec = _load_json(a.spec); chk("spec_schema", spec.get("schema") == SPEC_SCHEMA and spec.get("whole_partial_sha_must_match") is False and spec.get("whole_archive_sha_set_must_match") is False and spec.get("raw_originals_must_be_preserved") is True)
    reqs = spec.get("required_exact_per_row_records") or []; chk("spec_record_count", len(reqs) == 15)
    try: B = _unpack(a.baseline, work, "baseline"); N = _unpack(a.new, work, "new")
    except Exception as ex: chk("probes_unpacked", False, repr(ex)); return _finish(R, a.out, 1)
    chk("probes_unpacked", True, dict(baseline_attempt=B["attempt"], new_attempt=N["attempt"]))
    chk("baseline_zip_sha256", B["zip_sha256"] is None or B["zip_sha256"] == spec.get("baseline_zip_sha256"), dict(zip_sha256=B["zip_sha256"], expected=spec.get("baseline_zip_sha256"), note="checked only when the baseline is given as the zip"))
    chk("distinct_attempts", B["attempt"] != N["attempt"] and B["root"] != N["root"])
    recB = ser.loads(open(B["record_file"], encoding="utf-8").read()); recN = ser.loads(open(N["record_file"], encoding="utf-8").read()); runB = _load_json(B["run_file"]); runN = _load_json(N["run_file"])
    if not all(isinstance(x, dict) for x in (recB, recN, runB, runN)): chk("documents_are_objects", False, "a probe record / run record is not a JSON object"); return _finish(R, a.out, 1)
    chk("documents_are_objects", True)
    chk("baseline_partial_payload", recB.get("binding", {}).get("partial_sha256") == spec.get("baseline_partial_payload"), dict(payload=recB.get("binding", {}).get("partial_sha256")))
    chk("records_are_family_partials", recB.get("schema") == PARTIAL_SCHEMA == recN.get("schema") and recB.get("family") == recN.get("family") == "E2" and len(recB.get("per_pseudo_status") or []) == len(recN.get("per_pseudo_status") or []) == 3)
    R["new_partial_payload"] = recN.get("binding", {}).get("partial_sha256"); R["notes"].append("whole partial payload SHA and whole archive SHA set are NOT contract items (provenance differs by design): recorded, not compared")
    # ------------------------------------------------------------------------------------------------------ R-D4BRIDGE-A: the producing tree and the producer run's provenance
    inv_path = os.path.join(phaseb, "B2_completion_inventory.json"); inv = _load_json(inv_path); inv_sha = sha(inv_path); ms = module_shas()
    drv = os.path.join(phaseb, "d", "d4c1_calibration.py"); pins_path = os.path.join(phaseb, "d", "d3_pins.json"); pins = _load_json(pins_path)
    tree = dict(inventory_sha256=inv_sha, script_sha256=sha(drv), pins_sha256=sha(pins_path), engine=__version__)
    chk("tree_self_consistent", inv.get("modules") == ms and inv.get("engine_version") == __version__ == pins.get("engine_version") and inv.get("d_sha256", {}).get("d/d4c1_calibration.py") == tree["script_sha256"] and inv.get("d_sha256", {}).get("d/d3_pins.json") == tree["pins_sha256"] and __version__ == spec.get("new_engine"),
        dict(tree=tree, spec_new_engine=spec.get("new_engine")))
    srcN = runN.get("source") if isinstance(runN.get("source"), dict) else {}
    chk("new_run_source_is_this_tree", all(srcN.get(k) == tree[k] for k in ("inventory_sha256", "script_sha256", "pins_sha256")) and srcN.get("engine_version") == __version__ and runN.get("pins_sha256") == tree["pins_sha256"] and runN.get("engine_version") == __version__ and recN.get("engine_version") == __version__,
        dict(run_source={k: srcN.get(k) for k in ("inventory_sha256", "script_sha256", "pins_sha256", "engine_version")}, run_pins_sha256=runN.get("pins_sha256")))
    chk("new_binding_names_this_tree", (recN.get("binding") or {}).get("modules") == ms and (recN.get("binding") or {}).get("engine_version") == __version__ and ((recN.get("binding") or {}).get("partial_dependencies") or {}).get("engine_version") == __version__)
    try: REQ = ast_required_partial(drv); chk("producer_required_partial_extracted", len(REQ) == 24 and "G_env_lock" in REQ and "G_twelve_gate" in REQ and len(set(REQ)) == 24, dict(n=len(REQ)))
    except Exception as ex: REQ = None; chk("producer_required_partial_extracted", False, repr(ex))
    gN = runN.get("gates") if isinstance(runN.get("gates"), dict) else {}; reqN = runN.get("required_inventory")
    chk("new_run_trusted_inventory", REQ is not None and teq(reqN, REQ) and sorted(gN) == sorted(REQ) and all(gN.get(k) is True for k in REQ) and runN.get("required_all_true") is True,
        dict(required_inventory_equals_producer_constant=(REQ is not None and teq(reqN, REQ)), gate_keys_equal=(REQ is not None and sorted(gN) == sorted(REQ)), not_true=[k for k in (REQ or []) if gN.get(k) is not True]))
    attN = runN.get("attempt") if isinstance(runN.get("attempt"), dict) else {}
    chk("new_run_complete_probe", runN.get("schema") == RUN_SCHEMA and runN.get("mode") == "partial" and runN.get("stage") == "complete" and runN.get("failures") == [] and runN.get("probe") is True and runN.get("probe_n") == 3 and runN.get("instrument") is True and runN.get("selftest") is False and runN.get("formal") is True
        and runN.get("D4C1_PARTIAL_PASS") is False and runN.get("D4C1_SUBPARTIAL_PASS") is False and runN.get("D4C1_COMBINE_PASS") is False and runN.get("subpartial") is False and runN.get("row_range") is None and runN.get("profile") == "production_official" and runN.get("family") == "E2",
        dict(stage=runN.get("stage"), failures=runN.get("failures"), probe=runN.get("probe"), probe_n=runN.get("probe_n"), instrument=runN.get("instrument"), partial_pass=runN.get("D4C1_PARTIAL_PASS")))
    chk("new_run_attempt_is_directory", isinstance(attN.get("attempt_id"), str) and attN.get("attempt_id") == N["attempt"] and _hex64(attN.get("launcher_lock_sha256")), dict(attempt_id=attN.get("attempt_id"), directory=N["attempt"]))
    chk("new_run_campaign_commitment", runN.get("campaign_id") == runB.get("campaign_id") and runN.get("target_commitment") == runB.get("target_commitment") and _hex64(runN.get("target_commitment")) and (recN.get("campaign") or {}).get("id") == runN.get("campaign_id") + "__PROBE" and (recN.get("thresholds") or {}).get("target_commitment") == runN.get("target_commitment"))
    chk("new_run_publication", (runN.get("published_evidence") or {}).get(os.path.basename(N["record_file"])) == dict(sha256=sha(N["record_file"]), bytes=os.path.getsize(N["record_file"])) and (runN.get("partial") or {}).get("partial_sha256") == recN["binding"]["partial_sha256"] and set(runN.get("published_evidence") or {}) == {os.path.basename(N["record_file"])})
    tw = runN.get("twelve") if isinstance(runN.get("twelve"), dict) else {}
    chk("new_run_twelve_gate_live", "twelve_gate" not in runN and teq(tw.get("gate"), dict(mode="official", passed=True, required_failures=[], environment_source="live_collected")) and isinstance(tw.get("d3c_binding"), dict) and tw["d3c_binding"].get("family") == "E2" and teq(tw.get("assembled_fingerprints"), tw["d3c_binding"].get("input_fingerprints")),
        dict(gate=tw.get("gate"), injected_top_level_key=("twelve_gate" in runN)))
    # the launcher lock and the final record of THIS attempt (the new probe only; the baseline's launcher records are registered evidence already audited)
    lockN = _load_json(N["lock_file"]); finN = _load_json(N["final_file"]); lock_sha = sha(N["lock_file"])
    if not (isinstance(lockN, dict) and isinstance(finN, dict)): chk("new_lock_final_are_objects", False); return _finish(R, a.out, 1)
    chk("new_lock_final_are_objects", True)
    lockB = _load_json(B["lock_file"]); ra_keys = sorted((lockB.get("registered_assets_sha256") or {}) if isinstance(lockB, dict) else {})
    ra_ok = isinstance(lockN.get("registered_assets_sha256"), dict) and sorted(lockN["registered_assets_sha256"]) == ra_keys and all(lockN["registered_assets_sha256"].get(k) == (inv.get("registered_assets_sha256") or {}).get(k) for k in ra_keys) and len(ra_keys) >= 9
    chk("new_lock_binds_this_tree", lockN.get("schema") == LOCK_SCHEMA and lock_sha == attN.get("launcher_lock_sha256") and lockN.get("inventory_sha256") == tree["inventory_sha256"] and lockN.get("script_sha256") == lockN.get("inventory_script_sha256") == tree["script_sha256"] and lockN.get("pins_sha256") == tree["pins_sha256"] and lockN.get("engine") == __version__ and ra_ok
        and lockN.get("family") == "E2" and lockN.get("probe_n") == 3 and lockN.get("instrument") is True and lockN.get("row_range") is None and lockN.get("out_root") is None and lockN.get("target_commitment") == runN.get("target_commitment") and lockN.get("campaign_id") == runN.get("campaign_id") and len(str(lockN.get("commit"))) == 40
        and (a.expected_commit is None or lockN.get("commit") == a.expected_commit),
        dict(lock_sha256=lock_sha, attempt_lock=attN.get("launcher_lock_sha256"), commit=lockN.get("commit"), expected_commit=a.expected_commit, registered_assets_keys=len(ra_keys), registered_assets_bound=ra_ok))
    bind = finN.get("bindings") if isinstance(finN.get("bindings"), dict) else {}
    def live_ok(b):
        return isinstance(b, dict) and b.get("head") == lockN.get("commit") and b.get("clean") is True and b.get("inventory_sha256") == tree["inventory_sha256"] and b.get("script_sha256") == b.get("inventory_script_sha256") == tree["script_sha256"] and b.get("pins_sha256") == tree["pins_sha256"] and b.get("engine") == __version__ and b.get("registered_assets_sha256") == lockN.get("registered_assets_sha256")
    chk("new_final_record_complete", finN.get("schema") == FINAL_SCHEMA and finN.get("attempt_id") == N["attempt"] and finN.get("lock_sha256") == lock_sha and teq(finN.get("lock"), lockN) and finN.get("stage") == "complete" and finN.get("exit_code") == 0 and finN.get("launcher_fallback") is False and finN.get("gates_ok") is True and finN.get("bindings_ok") is True and finN.get("evidence_ok") is True
        and finN.get("failures") == [] and finN.get("exception") is None and finN.get("probe") is True and finN.get("partial_pass") is False and finN.get("D4C1_PARTIAL_PASS") is False and finN.get("instrument") is True and finN.get("subpartial") is False and finN.get("row_range") is None
        and finN.get("record_sha256") == sha(N["run_file"]) and finN.get("record_stage") == "complete" and finN.get("record_failures") == [] and teq(finN.get("gates"), gN) and (finN.get("partial_summary") or {}).get("partial_sha256") == recN["binding"]["partial_sha256"] and (finN.get("partial_summary") or {}).get("n_pseudo") == 3 and (finN.get("partial_summary") or {}).get("archive_entries") == 17
        and os.path.basename(str(finN.get("run_dir"))) == "run_" + N["attempt"] and isinstance((finN.get("ram") or {}).get("total_bytes"), int) and finN["ram"]["total_bytes"] > 40_000_000_000,
        dict(stage=finN.get("stage"), exit_code=finN.get("exit_code"), launcher_fallback=finN.get("launcher_fallback"), failures=finN.get("failures"), record_sha256_matches_run_record=(finN.get("record_sha256") == sha(N["run_file"])), ram_total_bytes=(finN.get("ram") or {}).get("total_bytes")))
    chk("new_final_live_source_precheck_prelaunch", live_ok(bind.get("live_source_precheck")) and live_ok(bind.get("live_source_prelaunch")), dict(precheck_head=(bind.get("live_source_precheck") or {}).get("head"), prelaunch_head=(bind.get("live_source_prelaunch") or {}).get("head"), lock_commit=lockN.get("commit")))
    # ------------------------------------------------------------------------------------------------------ R-D4BRIDGE-C: the profile document (semantic), reconciled with the run summary / receipt
    prof = _load_json(N["profile_file"]) if os.path.isfile(N["profile_file"]) else None
    def profile_ok(p):
        if not isinstance(p, dict) or p.get("schema") != PROFILE_SCHEMA or p.get("engine_version") != __version__ or p.get("python") != spec.get("new_python"): return False, "schema / engine / python"
        ins = p.get("instrumentation")
        if not (isinstance(ins, dict) and ins.get("wrappers") is True and ins.get("cprofile") is True and ins.get("segment_target") == SEGMENT_TARGET): return False, "instrumentation flags"
        if not teq(p.get("missing_targets"), []): return False, "missing_targets"
        tg = p.get("targets")
        if not (isinstance(tg, dict) and set(tg) == set(TARGETS)): return False, "target inventory differs from the producer TARGETS"
        seg = p.get("segments")
        if not (isinstance(seg, dict) and seg.get("count") == 3 and isinstance(seg.get("per_segment"), list) and len(seg["per_segment"]) == 3 and [s.get("index") for s in seg["per_segment"]] == [0, 1, 2] and all(_is_row(s.get("index")) for s in seg["per_segment"])): return False, "segments count / indices"
        for s in seg["per_segment"]:
            if not (isinstance(s.get("wall_seconds"), float) and s["wall_seconds"] >= 0 and isinstance(s.get("targets"), dict) and set(s["targets"]) <= set(TARGETS)): return False, "per-segment shape"
        if not _close(seg.get("wall_seconds"), float(sum(s["wall_seconds"] for s in seg["per_segment"]))) or not _close(seg.get("mean_wall_seconds"), seg["wall_seconds"] / 3): return False, "segment wall bookkeeping"
        if not (isinstance(p.get("wall_seconds_total"), float) and _close(p.get("outside_segments_wall_seconds"), p["wall_seconds_total"] - seg["wall_seconds"])): return False, "outside bookkeeping"
        for k, v in tg.items():
            inside_calls = sum((s["targets"].get(k) or {}).get("calls", 0) for s in seg["per_segment"]); o = v.get("outside_segments") or {}
            if not (_is_row(v.get("calls")) and v["calls"] >= 0 and isinstance(v.get("inclusive_seconds"), float) and isinstance(v.get("self_seconds"), float) and _is_row(o.get("calls")) and v["calls"] == inside_calls + o["calls"]): return False, f"target accounting {k}"
        if tg[SEGMENT_TARGET]["calls"] != 3: return False, "segment target calls != probe_n"
        cp = p.get("cprofile")
        if not (isinstance(cp, dict) and isinstance(cp.get("by_cumtime"), list) and isinstance(cp.get("by_tottime"), list) and cp["by_cumtime"] and cp["by_tottime"] and _is_row(cp.get("n_functions")) and cp["n_functions"] > 0): return False, "cProfile table"
        return True, "ok"
    pok, why = profile_ok(prof) if prof is not None else (False, "profile file missing")
    summ = dict(wall_seconds_total=prof["wall_seconds_total"], segments=prof["segments"]["count"], segment_wall_seconds=prof["segments"]["wall_seconds"], outside_segments_wall_seconds=prof["outside_segments_wall_seconds"], missing_targets=prof["missing_targets"]) if pok else None
    chk("new_profile_document", pok and teq(runN.get("profile_summary"), summ) and runN.get("profile_record") == dict(sha256=sha(N["profile_file"]), bytes=os.path.getsize(N["profile_file"])),
        dict(document=why, summary_equals_document=(pok and teq(runN.get("profile_summary"), summ)), receipt_matches_file=(os.path.isfile(N["profile_file"]) and runN.get("profile_record") == dict(sha256=sha(N["profile_file"]), bytes=os.path.getsize(N["profile_file"])))))
    # ------------------------------------------------------------------------------------------------------ environments: each gate valid in its own epoch (NOT whole gate equality)
    envB = ((recB.get("gate") or {}).get("diagnostics") or {}).get("env") or {}; envN = ((recN.get("gate") or {}).get("diagnostics") or {}).get("env") or {}
    hist = [{k: h[k] for k in VERSION_KEYS} for h in EXPECTED_VERS_HISTORY]; cur = {k: EXPECTED_VERS[k] for k in VERSION_KEYS}
    chk("baseline_env_is_registered_history", {k: envB.get(k) for k in VERSION_KEYS} in hist and envB.get("python") == spec.get("old_python") and (recB.get("gate") or {}).get("passed") is True and (recB.get("gate") or {}).get("required_failures") == [] and (recB.get("gate") or {}).get("diagnostics", {}).get("environment_source") == "live_collected", dict(env={k: envB.get(k) for k in VERSION_KEYS}))
    chk("new_env_is_registered_current", {k: envN.get(k) for k in VERSION_KEYS} == cur and envN.get("python") == spec.get("new_python") == pins["environment"]["python"] and (recN.get("gate") or {}).get("passed") is True and (recN.get("gate") or {}).get("required_failures") == [] and (recN.get("gate") or {}).get("diagnostics", {}).get("environment_source") == "live_collected"
        and {k: (runN.get("env") or {}).get(k) for k in VERSION_KEYS} == cur and (runN.get("env_gate") or {}).get("versions_ok") is True and (runN.get("env_gate") or {}).get("pools_ok") is True and {k: ((runN.get("env_gate") or {}).get("expected") or {}).get(k) for k in VERSION_KEYS} == cur, dict(env={k: envN.get(k) for k in VERSION_KEYS}))
    chk("new_blas_pools_rule", all(isinstance(t.get("n"), int) and t["n"] <= 2 for t in (envN.get("blas_threads") or [])) and any(t.get("owner") == "numpy" and t.get("n") == 2 for t in (envN.get("blas_threads") or [])), dict(blas_threads=[(t.get("owner"), t.get("n")) for t in (envN.get("blas_threads") or [])]))
    # ------------------------------------------------------------------------------------------------------ required_equal_partial_fields (content equality under the canonical serialization)
    fields = spec.get("required_equal_partial_fields") or []; diff = [f for f in fields if ser.dumps(recB.get(f)) != ser.dumps(recN.get(f))]
    chk("required_equal_partial_fields", bool(fields) and not diff and all(f in recB and f in recN for f in fields), dict(fields=fields, differing=diff))
    R["partial_provenance_differences"] = dict(engine_version=(recB.get("engine_version"), recN.get("engine_version")), gate_env_python=(envB.get("python"), envN.get("python")), binding_modules_equal=(recB.get("binding") or {}).get("modules") == (recN.get("binding") or {}).get("modules"), payload=(recB["binding"]["partial_sha256"], recN["binding"]["partial_sha256"]))
    # ------------------------------------------------------------------------------------------------------ R-D4BRIDGE-B: the 15 per-row records by TYPED identity and global row, in BOTH archives
    def index_of(P):
        idx = _load_json(os.path.join(P["archive"], "index.json")); ents = idx["entries"]
        if not all(isinstance(e, dict) and isinstance(e.get("identity"), dict) and isinstance(e.get("kind"), str) and _hex64(e.get("sha256")) and e.get("path") == f"{e.get('kind')}/{e.get('sha256')}.json" and _is_row(e.get("bytes")) for e in ents): raise ValueError("archive index entry malformed")
        return idx, ents, {(e["kind"], e["sha256"]): e for e in ents}
    idxB, entsB, byB = index_of(B); idxN, entsN, byN = index_of(N)
    chk("archive_entry_counts", len(entsB) == len(entsN) == 17 and len(byB) == len(byN) == 17 and idxN.get("engine_version") == __version__ and len({e["sha256"] for e in entsN}) == 17 and len({e["sha256"] for e in entsB}) == 17, dict(baseline=len(entsB), new=len(entsN)))
    rows = {}; cursor = None
    for e in reqs:
        if e["kind"] == "family_result": cursor = e["row"]; rows.setdefault(cursor, {})["family_result"] = e
        elif e["kind"] == "transition": rows.setdefault(e["row"], {})["transition"] = e
        elif e["kind"] == "three_position_result": rows.setdefault(cursor, {}).setdefault("three", {})[e["identity"]["size_id"]] = e
    chk("spec_rows_grouped", sorted(rows) == [0, 1, 2] and all(_is_row(r) and set(rows[r]) == {"family_result", "three", "transition"} and set(rows[r]["three"]) == set(SIZES) and teq(rows[r]["family_result"]["identity"], dict(family="E2", stage="3-position family mixture (pseudo)", pseudo_index=r)) and teq(rows[r]["transition"]["identity"], dict(kind="pseudo_family_plan", family="E2", pseudo_index=r))
                                                            and all(teq(rows[r]["three"][s]["identity"], dict(family="E2", size_id=s)) for s in SIZES) for r in rows))
    def file_sha_bytes(P, e): fp = os.path.join(P["archive"], e["path"]); return (sha(fp), os.path.getsize(fp)) if os.path.isfile(fp) else (None, None)
    def resolve(P, rec, ents, by, r):
        """The row's records by TYPED identity: family_result by {family, stage, pseudo_index=r}, the plan transition by {kind, family, pseudo_index=r} (type-strict: the row is an int, never a
        bool); the three_position_results by the SHAs the plan transition names per size, each indexed under exactly {family, size_id}; the partial's per_pseudo_status[r].parent_ref names the
        family_result with the same typed identity."""
        fr = [e for e in ents if e["kind"] == "family_result" and teq(e["identity"], rows[r]["family_result"]["identity"])]
        tr = [e for e in ents if e["kind"] == "transition" and teq(e["identity"], rows[r]["transition"]["identity"])]
        if len(fr) != 1 or len(tr) != 1: return dict(error=f"row {r}: family_result {len(fr)} / plan transition {len(tr)} entries with the typed identity (exactly one each required)")
        plan = ser.loads(open(os.path.join(P["archive"], tr[0]["path"]), encoding="utf-8").read())
        if not (isinstance(plan, dict) and plan.get("kind") == "pseudo_family_plan" and plan.get("family") == "E2" and teq(plan.get("pseudo_index"), r)): return dict(error=f"row {r}: plan transition document identity")
        three = {}
        for s in SIZES:
            h = ((plan.get("transitions") or {}).get(s) or {}).get("three_position_result_sha256"); ent = by.get(("three_position_result", h))
            if ent is None or not teq(ent["identity"], rows[r]["three"][s]["identity"]): return dict(error=f"row {r} {s}: three_position_result named by the plan transition not in the archive index with the typed identity")
            three[s] = ent
        pr = (rec["per_pseudo_status"][r].get("parent_ref") or {})
        if pr.get("sha256") != fr[0]["sha256"] or pr.get("kind") != "family_result" or not teq(pr.get("identity"), fr[0]["identity"]) or pr.get("path") != fr[0]["path"]: return dict(error=f"row {r}: per_pseudo_status parent_ref does not name the family_result of this row (typed)")
        return dict(family_result=fr[0], transition=tr[0], three=three)
    per_row = {}; ok_rows = True
    for r in sorted(rows):
        got = {"baseline": resolve(B, recB, entsB, byB, r), "new": resolve(N, recN, entsN, byN, r)}; row_report = {}
        for tag, P in (("baseline", B), ("new", N)):
            g = got[tag]
            if "error" in g: row_report[tag] = g; ok_rows = False; continue
            items = [("family_result", rows[r]["family_result"], g["family_result"]), ("transition", rows[r]["transition"], g["transition"])] + [(f"three_position_result/{s}", rows[r]["three"][s], g["three"][s]) for s in SIZES]
            rr = {}
            for name, e_spec, e_got in items:
                fsha, fbytes = file_sha_bytes(P, e_got)
                ok = (e_got["sha256"] == e_spec["sha256"] == fsha and teq(e_got.get("bytes"), e_spec["bytes"]) and e_spec["bytes"] == fbytes and e_got["kind"] == e_spec["kind"] and teq(e_got["identity"], e_spec["identity"]))
                rr[name] = dict(ok=ok, expected=e_spec["sha256"], index=e_got["sha256"], file=fsha, bytes=(e_spec["bytes"], e_got.get("bytes"), fbytes)); ok_rows &= ok
            row_report[tag] = rr
        per_row[str(r)] = row_report
    R["per_row"] = per_row; chk("per_row_records_exact_in_both_probes", ok_rows)
    spec_shas = {e["sha256"] for e in reqs}; regs = [o for o in spec.get("other_archive_records") or [] if o["kind"] == "registry"]
    def others(ents): return [e for e in ents if e["sha256"] not in spec_shas]
    oB, oN = others(entsB), others(entsN)
    def others_ok(o, P, rec, allow_partial_sha=None):
        reg = [e for e in o if e["kind"] == "registry"]; part = [e for e in o if e["kind"] == "transition" and e["identity"].get("kind") == "family_partial_calibration"]
        if not (len(o) == 2 and len(reg) == 1 and len(part) == 1 and len(regs) == 1): return False
        p = part[0]
        return (reg[0]["sha256"] == regs[0]["sha256"] == file_sha_bytes(P, reg[0])[0] and teq(reg[0]["identity"], (rec.get("archive_refs") or {}).get("registry", {}).get("identity")) and p["sha256"] == file_sha_bytes(P, p)[0]
                and teq(p["identity"], dict(kind="family_partial_calibration", family="E2", payload_sha256=rec["binding"]["partial_sha256"], target_commitment=rec["thresholds"]["target_commitment"])) and p["sha256"] == rec["binding"].get("partial_file_sha256") and (allow_partial_sha is None or p["sha256"] == allow_partial_sha))
    chk("baseline_other_entries", others_ok(oB, B, recB, next((o["sha256"] for o in spec.get("other_archive_records") or [] if o["kind"] == "transition"), None)), dict(entries=[(e["kind"], e["sha256"]) for e in oB]))
    chk("new_other_entries_registry_and_one_partial", others_ok(oN, N, recN), dict(entries=[(e["kind"], e["sha256"]) for e in oN], note="the partial transition SHA is allowed to differ (provenance)"))
    try: chk("archives_verify", Archive(B["archive"]).verify_all()["ok"] and Archive(N["archive"]).verify_all()["ok"])
    except Exception as ex: chk("archives_verify", False, repr(ex))
    # ------------------------------------------------------------------------------------------------------ the NEW record through its own unmodified reader (registered identities of the producing tree; CURRENT source binding)
    try:
        import re
        TWELVE_RECEIPT = re.search(r'TWELVE_RECEIPT = "([^"]+)"', open(drv, encoding="utf-8").read()).group(1)                                   # the producing driver's registered receipt label
        ctx = twelve_context(phaseb); w2ctx, w2view = load_registered_w2_context(phaseb, ctx)
        reg = load_registry(os.path.join(phaseb, "tests/assets/a7_circle_geometry.csv"), os.path.join(phaseb, "tests/assets/a6_observer_design_points.json"))
        tasset = intake_registered_twelve_assets(os.path.join(phaseb, "registered_assets", "b3_2_twelve_assets.json"), reg, TWELVE_RECEIPT)
        registered = dict(shared_null_asset_sha256=w2ctx.asset_sha256, w2_context_sha256=w2ctx.context_sha256, registry_sha256=reg.registry_sha256, twelve_assets_sha256=tasset.sha256)
        arN = Archive(N["archive"]); archived = load_partial_record(arN, recN["binding"]["partial_ref"])
        strip = lambda d: {**d, "binding": {k: v for k, v in d["binding"].items() if k not in ("partial_file_sha256", "partial_ref")}}
        same = ser.dumps(strip(ser.from_jsonable(ser.to_jsonable(recN)))) == ser.dumps(strip(archived)) and archived["binding"]["partial_sha256"] == recN["binding"]["partial_sha256"]
        v = verify_partial_record(archived, arN, registered=registered, current_source_binding=True)
        chk("new_record_own_reader_current_source_binding", bool(same and v.get("ok") and v.get("registered_context_ok")), dict(published_equals_archived=same, verification={k: v.get(k) for k in ("ok", "family", "n_pseudo", "partial_sha256", "context_scope", "registered_context_ok")}))
        R["new_reader_verification"] = v
    except Exception as ex: chk("new_record_own_reader_current_source_binding", False, repr(ex))
    depB = (recB.get("binding") or {}).get("partial_dependencies") or {}; depN = (recN.get("binding") or {}).get("partial_dependencies") or {}
    inv_keys = [k for k in ("mode", "registry_sha256", "manifest_sha256", "w2_context_sha256", "w2_asset_sha256", "twelve_assets_sha256", "twelve_assets_intake", "families", "sizes", "require_all_families", "pseudo") if k in depB or k in depN]
    chk("binding_invariant_dependencies_equal", bool(inv_keys) and all(ser.dumps(depB.get(k)) == ser.dumps(depN.get(k)) for k in inv_keys), dict(keys=inv_keys, differing=[k for k in inv_keys if ser.dumps(depB.get(k)) != ser.dumps(depN.get(k))]))
    chk("originals_untouched", B["zip_sha256"] is None or sha(a.baseline) == B["zip_sha256"])
    return _finish(R, a.out, 0 if not R["mismatches"] else 1)


def _finish(R: dict, out: str, code: int) -> int:
    R["result"] = ("BRIDGE_CONTRACT_SATISFIED" if code == 0 else "MISMATCH_OR_REFUSAL__STOP_FOR_ANALYSIS"); R["exit_code"] = code; R["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    R["n_checks"] = len(R["checks"]); R["n_failed"] = len(R["mismatches"])
    os.makedirs(os.path.dirname(os.path.realpath(out)) or ".", exist_ok=True); json.dump(R, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
    print(f"{R['result']}: {R['n_checks'] - R['n_failed']}/{R['n_checks']} checks ok" + ("" if code == 0 else "; failed: " + ", ".join(R["mismatches"]))); return code


if __name__ == "__main__": sys.exit(main())
