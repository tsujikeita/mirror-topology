# -*- coding: utf-8 -*-
"""D4C-2a environment bridge comparison (audit D4C2a_v3_0.110.0: `D4C2a_v3_0.110.0_bridge_comparison_spec.json`, schema D4C2a_environment_bridge_comparison_spec_v1).

Compares ONE instrumented E2 N=3 probe produced under the amended registered environment (engine 0.110.0, Python 3.13.16: the NEW probe) with the registered baseline probe
(engine 0.107.0, Python 3.13.15, attempt 20261005T100239Z_386d63207c) exactly as the audit contract prescribes:
  * the whole partial payload SHA and the whole archive SHA set are NOT required to match (the partial carries its engine / module and gate-environment provenance);
  * the 15 per-row records (family_result x 3, three_position_result x 9, pseudo_family_plan transition x 3) are mapped by their TYPED identity and global row (family_result and
    the plan transition by pseudo_index; the three three_position_results of a row by the three_position_result_sha256 named per size in that row's plan transition) and must agree
    with the specification's content SHA and bytes EXACTLY, in BOTH probes, with no missing / extra / duplicate row; the registry record must be the specification's registry record;
    the remaining archive entry must be exactly one family_partial_calibration transition (the partial itself: its SHA is allowed to change);
  * required_equal_partial_fields of the two published partial records must be content-equal (canonical serialization);
  * the NEW record is read through its own unmodified reader (load_partial_record + verify_partial_record with the registered identities of the producing tree and
    current_source_binding=True) — therefore this script must be run with --phaseb pointing at the SAME fixed source tree that produced the new probe (its inventory SHA must equal
    the new run record's source.inventory_sha256), and that tree's engine is the one imported here;
  * provenance / environment are verified SEPARATELY: the baseline gate environment must equal the registered history entry (3.13.15 ...), the new gate environment must equal
    the producing tree's EXPECTED_VERS (3.13.16 ...), both gates passed with environment_source live_collected; the new run record is a complete, failure-free probe
    (every gate of its trusted inventory True, D4C1_PARTIAL_PASS False by construction) whose profile record exists with segments == probe_n and no missing targets.
  * the original files are never modified; on ANY mismatch the report says so and the exit code is 1 (no retry, no tolerance: the differences are listed for analysis).
Exit code 0 = every contract item satisfied; 1 = at least one mismatch / refusal (report published either way); 2 = usage error.
This is a comparison of a PROBE: it approves nothing (no screen / certificate / calibration GO, no numerical equivalence beyond the fixed first 3 rows)."""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time, zipfile, tempfile, shutil

SPEC_SCHEMA = "D4C2a_environment_bridge_comparison_spec_v1"
REPORT_SCHEMA = "d4c2_bridge_comparison_report_v1"
SIZES = ("L1.00", "L1.20", "L1.50")


def sha(p: str) -> str: return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _hex64(v) -> bool: return isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)


def _unpack(src: str, work: str, tag: str) -> dict:
    """A probe is given as the launcher zip (byte-preserved) or as its unpacked directory. Returns dict(root, zip_sha256, run_dir, record, run, archive)."""
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
    return dict(root=root, zip_sha256=zsha, run_dir=rd, attempt=runs[0][len("run_"):], record_file=os.path.join(rd, recs[0]), run_file=os.path.join(rd, rr[0]), archive=os.path.join(rd, "archive"), profile_file=os.path.join(rd, recs[0].replace("_record.json", "_profile.json")))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--phaseb", required=True, help="the FIXED source tree that produced the NEW probe (its step1_engine is imported; its inventory must equal the new run record's source.inventory_sha256)")
    ap.add_argument("--spec", required=True, help="the audit's bridge comparison specification JSON"); ap.add_argument("--baseline", required=True, help="baseline probe: launcher zip or unpacked directory"); ap.add_argument("--new", required=True, help="new probe: launcher zip or unpacked directory")
    ap.add_argument("--out", required=True, help="report JSON path (must not exist)")
    a = ap.parse_args()
    if os.path.lexists(a.out): print("--out must not exist", file=sys.stderr); return 2
    for p in (a.phaseb, a.spec, a.baseline, a.new):
        if not os.path.exists(p): print(f"missing: {p}", file=sys.stderr); return 2
    phaseb = os.path.realpath(a.phaseb); sys.path.insert(0, phaseb)
    from step1_engine import serialization as ser, __version__
    from step1_engine.archive import Archive
    from step1_engine.checkpoint import module_shas
    from step1_engine.d4c1_partial import load_partial_record, verify_partial_record, PARTIAL_SCHEMA
    from step1_engine.official_gate import EXPECTED_VERS, EXPECTED_VERS_HISTORY, VERSION_KEYS
    from step1_engine.d3_profile import twelve_context
    from step1_engine.d4c0_registry import load_registered_w2_context
    from step1_engine.grid_registry import load_registry
    from step1_engine.twelve_assets import intake_registered_twelve_assets
    R = dict(schema=REPORT_SCHEMA, spec=dict(file=os.path.realpath(a.spec), sha256=sha(a.spec)), phaseb=phaseb, engine_version=__version__, started_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), checks={}, mismatches=[], notes=[],
             scope="comparison of ONE instrumented E2 N=3 probe against the registered baseline probe under the audit's bridge contract; approves no screen / certificate / calibration and proves no equivalence beyond the fixed first 3 rows; originals untouched")
    def chk(name, ok, detail=None):
        R["checks"][name] = dict(ok=bool(ok), **({} if detail is None else dict(detail=detail)))
        if not ok: R["mismatches"].append(name)
        return bool(ok)
    work = tempfile.mkdtemp(prefix="d4c2_bridge_")
    try:
        spec = json.load(open(a.spec)); chk("spec_schema", spec.get("schema") == SPEC_SCHEMA and spec.get("whole_partial_sha_must_match") is False and spec.get("whole_archive_sha_set_must_match") is False and spec.get("raw_originals_must_be_preserved") is True)
        reqs = spec.get("required_exact_per_row_records") or []; chk("spec_record_count", len(reqs) == 15)
        try: B = _unpack(a.baseline, work, "baseline"); N = _unpack(a.new, work, "new")
        except Exception as ex: chk("probes_unpacked", False, repr(ex)); return _finish(R, a.out, 1)
        chk("probes_unpacked", True, dict(baseline_attempt=B["attempt"], new_attempt=N["attempt"]))
        chk("baseline_zip_sha256", B["zip_sha256"] is None or B["zip_sha256"] == spec.get("baseline_zip_sha256"), dict(zip_sha256=B["zip_sha256"], expected=spec.get("baseline_zip_sha256"), note="checked only when the baseline is given as the zip"))
        chk("distinct_attempts", B["attempt"] != N["attempt"] and B["root"] != N["root"])
        recB = ser.loads(open(B["record_file"], encoding="utf-8").read()); recN = ser.loads(open(N["record_file"], encoding="utf-8").read()); runB = json.load(open(B["run_file"])); runN = json.load(open(N["run_file"]))
        chk("baseline_partial_payload", recB.get("binding", {}).get("partial_sha256") == spec.get("baseline_partial_payload"), dict(payload=recB.get("binding", {}).get("partial_sha256")))
        chk("records_are_family_partials", recB.get("schema") == PARTIAL_SCHEMA == recN.get("schema") and recB.get("family") == recN.get("family") == "E2" and len(recB.get("per_pseudo_status") or []) == len(recN.get("per_pseudo_status") or []) == 3)
        R["new_partial_payload"] = recN.get("binding", {}).get("partial_sha256"); R["notes"].append("whole partial payload SHA and whole archive SHA set are NOT contract items (provenance differs by design): recorded, not compared")
        # ---- the producing tree is the fixed source of the NEW probe
        inv_path = os.path.join(phaseb, "B2_completion_inventory.json"); inv = json.load(open(inv_path)); ms = module_shas()
        chk("new_source_is_this_tree", (runN.get("source") or {}).get("inventory_sha256") == sha(inv_path) and inv.get("modules") == ms and inv.get("engine_version") == __version__ == (runN.get("source") or {}).get("engine_version") == recN.get("engine_version") == spec.get("new_engine") and (runN.get("source") or {}).get("script_sha256") == inv.get("d_sha256", {}).get("d/d4c1_calibration.py"),
            dict(tree_inventory=sha(inv_path), new_run_inventory=(runN.get("source") or {}).get("inventory_sha256"), engine=__version__))
        chk("new_binding_names_this_tree", (recN.get("binding") or {}).get("modules") == ms and (recN.get("binding") or {}).get("engine_version") == __version__)
        # ---- the NEW run record: complete, failure-free probe, every gate of the trusted inventory True, no PASS, no self-test, instrumented profile
        gN = runN.get("gates") or {}; reqN = runN.get("required_inventory") or []
        chk("new_run_complete_probe", runN.get("schema") == "d4c1_run_record_v1" and runN.get("mode") == "partial" and runN.get("stage") == "complete" and runN.get("failures") == [] and runN.get("probe") is True and runN.get("probe_n") == 3 and runN.get("instrument") is True and runN.get("selftest") is False and runN.get("formal") is True
            and runN.get("D4C1_PARTIAL_PASS") is False and runN.get("D4C1_SUBPARTIAL_PASS") is False and runN.get("subpartial") is False and runN.get("row_range") is None and runN.get("profile") == "production_official" and runN.get("family") == "E2",
            dict(stage=runN.get("stage"), failures=runN.get("failures"), probe=runN.get("probe"), probe_n=runN.get("probe_n"), instrument=runN.get("instrument"), partial_pass=runN.get("D4C1_PARTIAL_PASS")))
        chk("new_run_gates_all_true", isinstance(reqN, list) and len(reqN) == 24 and sorted(gN) == sorted(reqN) and all(gN.get(k) is True for k in reqN) and runN.get("required_all_true") is True and "G_env_lock" in reqN, dict(n=len(reqN), false=[k for k in reqN if gN.get(k) is not True]))
        chk("new_run_campaign_commitment", runN.get("campaign_id") == runB.get("campaign_id") and runN.get("target_commitment") == runB.get("target_commitment") and _hex64(runN.get("target_commitment")) and isinstance((runN.get("attempt") or {}).get("attempt_id"), str) and _hex64((runN.get("attempt") or {}).get("launcher_lock_sha256")))
        chk("new_run_publication", (runN.get("published_evidence") or {}).get(os.path.basename(N["record_file"])) == dict(sha256=sha(N["record_file"]), bytes=os.path.getsize(N["record_file"])) and (runN.get("partial") or {}).get("partial_sha256") == recN["binding"]["partial_sha256"])
        prof = json.load(open(N["profile_file"])) if os.path.isfile(N["profile_file"]) else None
        chk("new_profile_record", isinstance(prof, dict) and prof.get("schema") == "d4c1_profile_record_v1" and (prof.get("segments") or {}).get("count") == 3 and (runN.get("profile_summary") or {}).get("missing_targets") == [] and (runN.get("profile_summary") or {}).get("segments") == 3 and runN.get("profile_record") == dict(sha256=sha(N["profile_file"]), bytes=os.path.getsize(N["profile_file"])),
            dict(present=prof is not None, segments=(prof or {}).get("segments", {}).get("count") if prof else None, missing_targets=(runN.get("profile_summary") or {}).get("missing_targets")))
        # ---- environments: each gate valid in its own epoch (NOT whole gate equality)
        envB = ((recB.get("gate") or {}).get("diagnostics") or {}).get("env") or {}; envN = ((recN.get("gate") or {}).get("diagnostics") or {}).get("env") or {}
        hist = [{k: h[k] for k in VERSION_KEYS} for h in EXPECTED_VERS_HISTORY]; cur = {k: EXPECTED_VERS[k] for k in VERSION_KEYS}
        chk("baseline_env_is_registered_history", {k: envB.get(k) for k in VERSION_KEYS} in hist and envB.get("python") == spec.get("old_python") and (recB.get("gate") or {}).get("passed") is True and (recB.get("gate") or {}).get("required_failures") == [] and (recB.get("gate") or {}).get("diagnostics", {}).get("environment_source") == "live_collected", dict(env={k: envB.get(k) for k in VERSION_KEYS}))
        chk("new_env_is_registered_current", {k: envN.get(k) for k in VERSION_KEYS} == cur and envN.get("python") == spec.get("new_python") and (recN.get("gate") or {}).get("passed") is True and (recN.get("gate") or {}).get("required_failures") == [] and (recN.get("gate") or {}).get("diagnostics", {}).get("environment_source") == "live_collected"
            and {k: (runN.get("env") or {}).get(k) for k in VERSION_KEYS} == cur and (runN.get("env_gate") or {}).get("versions_ok") is True and (runN.get("env_gate") or {}).get("pools_ok") is True, dict(env={k: envN.get(k) for k in VERSION_KEYS}))
        chk("new_blas_pools_rule", all(isinstance(t.get("n"), int) and t["n"] <= 2 for t in (envN.get("blas_threads") or [])) and any(t.get("owner") == "numpy" and t.get("n") == 2 for t in (envN.get("blas_threads") or [])), dict(blas_threads=[(t.get("owner"), t.get("n")) for t in (envN.get("blas_threads") or [])]))
        # ---- required_equal_partial_fields (content equality under the canonical serialization)
        fields = spec.get("required_equal_partial_fields") or []; diff = [f for f in fields if ser.dumps(recB.get(f)) != ser.dumps(recN.get(f))]
        chk("required_equal_partial_fields", bool(fields) and not diff and all(f in recB and f in recN for f in fields), dict(fields=fields, differing=diff))
        R["partial_provenance_differences"] = dict(engine_version=(recB.get("engine_version"), recN.get("engine_version")), gate_env_python=(envB.get("python"), envN.get("python")), binding_modules_equal=(recB.get("binding") or {}).get("modules") == (recN.get("binding") or {}).get("modules"), payload=(recB["binding"]["partial_sha256"], recN["binding"]["partial_sha256"]))
        # ---- the 15 per-row records by typed identity and global row, in BOTH archives
        def index_of(P):
            idx = json.load(open(os.path.join(P["archive"], "index.json"))); ents = idx["entries"]
            return idx, ents, {(e["kind"], e["sha256"]): e for e in ents}
        idxB, entsB, byB = index_of(B); idxN, entsN, byN = index_of(N)
        chk("archive_entry_counts", len(entsB) == len(entsN) == 17 and len(byB) == len(byN) == 17 and idxN.get("engine_version") == __version__, dict(baseline=len(entsB), new=len(entsN)))
        # group the spec records per row: family_result(row) / three three_position_results (in size order L1.00, L1.20, L1.50) / transition(row)
        rows = {}; cursor = None
        for e in reqs:
            if e["kind"] == "family_result": cursor = e["row"]; rows.setdefault(cursor, {})["family_result"] = e
            elif e["kind"] == "transition": rows.setdefault(e["row"], {})["transition"] = e
            elif e["kind"] == "three_position_result": rows.setdefault(cursor, {}).setdefault("three", {})[e["identity"]["size_id"]] = e
        chk("spec_rows_grouped", sorted(rows) == [0, 1, 2] and all(set(rows[r]) == {"family_result", "three", "transition"} and set(rows[r]["three"]) == set(SIZES) and rows[r]["family_result"]["identity"].get("pseudo_index") == r and rows[r]["transition"]["identity"].get("pseudo_index") == r for r in rows))
        def file_sha_bytes(P, e): fp = os.path.join(P["archive"], e["path"]); return (sha(fp), os.path.getsize(fp)) if os.path.isfile(fp) else (None, None)
        def resolve(P, rec, ents, by, r):
            """The row's records by typed identity: family_result by (family, stage, pseudo_index); plan transition by (kind, family, pseudo_index); the three_position_results by the SHAs
            that the plan transition names per size; the partial's per_pseudo_status[r].parent_ref must name the same family_result."""
            fr = [e for e in ents if e["kind"] == "family_result" and e["identity"].get("family") == "E2" and e["identity"].get("pseudo_index") == r]
            tr = [e for e in ents if e["kind"] == "transition" and e["identity"].get("kind") == "pseudo_family_plan" and e["identity"].get("family") == "E2" and e["identity"].get("pseudo_index") == r]
            if len(fr) != 1 or len(tr) != 1: return dict(error=f"row {r}: family_result {len(fr)} / plan transition {len(tr)} entries (exactly one each required)")
            plan = ser.loads(open(os.path.join(P["archive"], tr[0]["path"]), encoding="utf-8").read()); three = {}
            for s in SIZES:
                h = ((plan.get("transitions") or {}).get(s) or {}).get("three_position_result_sha256"); ent = by.get(("three_position_result", h))
                if ent is None or ent["identity"] != dict(family="E2", size_id=s): return dict(error=f"row {r} {s}: three_position_result named by the plan transition not in the archive index with the typed identity")
                three[s] = ent
            pr = (rec["per_pseudo_status"][r].get("parent_ref") or {})
            if pr.get("sha256") != fr[0]["sha256"] or pr.get("kind") != "family_result": return dict(error=f"row {r}: per_pseudo_status parent_ref does not name the family_result of this row")
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
                    ok = (e_got["sha256"] == e_spec["sha256"] == fsha and e_got.get("bytes") == e_spec["bytes"] == fbytes and e_got["kind"] == e_spec["kind"])
                    rr[name] = dict(ok=ok, expected=e_spec["sha256"], index=e_got["sha256"], file=fsha, bytes=(e_spec["bytes"], e_got.get("bytes"), fbytes)); ok_rows &= ok
                row_report[tag] = rr
            per_row[str(r)] = row_report
        R["per_row"] = per_row; chk("per_row_records_exact_in_both_probes", ok_rows)
        # content equality of the 15 archived documents (the content SHA is the archive's canonical-bytes hash; equal SHA + equal file bytes = identical records)
        # no extra / missing / duplicate: the remaining entries are exactly the registry and ONE family_partial_calibration transition
        spec_shas = {e["sha256"] for e in reqs}; regs = [o for o in spec.get("other_archive_records") or [] if o["kind"] == "registry"]
        def others(ents): return [e for e in ents if e["sha256"] not in spec_shas]
        oB, oN = others(entsB), others(entsN)
        def others_ok(o, P, allow_partial_sha=None):
            reg = [e for e in o if e["kind"] == "registry"]; part = [e for e in o if e["kind"] == "transition" and e["identity"].get("kind") == "family_partial_calibration"]
            return len(o) == 2 and len(reg) == 1 and len(part) == 1 and len(regs) == 1 and reg[0]["sha256"] == regs[0]["sha256"] == file_sha_bytes(P, reg[0])[0] and part[0]["sha256"] == file_sha_bytes(P, part[0])[0] and (allow_partial_sha is None or part[0]["sha256"] == allow_partial_sha)
        chk("baseline_other_entries", others_ok(oB, B, next((o["sha256"] for o in spec.get("other_archive_records") or [] if o["kind"] == "transition"), None)), dict(entries=[(e["kind"], e["sha256"]) for e in oB]))
        chk("new_other_entries_registry_and_one_partial", others_ok(oN, N), dict(entries=[(e["kind"], e["sha256"]) for e in oN], note="the partial transition SHA is allowed to differ (provenance)"))
        try: chk("archives_verify", Archive(B["archive"]).verify_all()["ok"] and Archive(N["archive"]).verify_all()["ok"])
        except Exception as ex: chk("archives_verify", False, repr(ex))
        # ---- the NEW record through its own unmodified reader with the registered identities of the producing tree and the CURRENT source binding
        try:
            import re
            TWELVE_RECEIPT = re.search(r'TWELVE_RECEIPT = "([^"]+)"', open(os.path.join(phaseb, "d", "d4c1_calibration.py"), encoding="utf-8").read()).group(1)       # the producing driver's registered receipt label
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
        # ---- invariant science / input dependency fields of the binding must equal the baseline (modules / engine / rules tables may differ by the fixed source)
        depB = (recB.get("binding") or {}).get("partial_dependencies") or {}; depN = (recN.get("binding") or {}).get("partial_dependencies") or {}
        inv_keys = [k for k in ("mode", "registry_sha256", "manifest_sha256", "w2_context_sha256", "w2_asset_sha256", "twelve_assets_sha256", "target_commitment", "pseudo_n", "pseudo_sha256_T1", "pseudo_sha256_T2") if k in depB or k in depN]
        chk("binding_invariant_dependencies_equal", bool(inv_keys) and all(ser.dumps(depB.get(k)) == ser.dumps(depN.get(k)) for k in inv_keys), dict(keys=inv_keys, differing=[k for k in inv_keys if ser.dumps(depB.get(k)) != ser.dumps(depN.get(k))]))
        chk("originals_untouched", B["zip_sha256"] is None or sha(a.baseline) == B["zip_sha256"])
        return _finish(R, a.out, 0 if not R["mismatches"] else 1)
    finally: shutil.rmtree(work, ignore_errors=True)


def _finish(R: dict, out: str, code: int) -> int:
    R["result"] = ("BRIDGE_CONTRACT_SATISFIED" if code == 0 else "MISMATCH_OR_REFUSAL__STOP_FOR_ANALYSIS"); R["exit_code"] = code; R["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    R["n_checks"] = len(R["checks"]); R["n_failed"] = len(R["mismatches"])
    os.makedirs(os.path.dirname(os.path.realpath(out)) or ".", exist_ok=True); json.dump(R, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
    print(f"{R['result']}: {R['n_checks'] - R['n_failed']}/{R['n_checks']} checks ok" + ("" if code == 0 else "; failed: " + ", ".join(R["mismatches"]))); return code


if __name__ == "__main__": sys.exit(main())
