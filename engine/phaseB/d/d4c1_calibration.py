# -*- coding: utf-8 -*-
"""Phase D4C-1: connection script of the formal global false-support calibration (rules §9.4) — family partial / combiner (design v0.2 §F; audit R-D4DESIGN-A/D/E/F/G).
MODES
  --mode partial --family F   ONE family (E1 / E2 / E7 / E8): preflight (pins / inventory / script binding; Phase C members; registered environment HARD gate; frozen loader;
      verified TwelveContext; registered D4C-0 W2 context and pseudo columns through the registered loaders (pins / acceptance bound); registered twelve asset (B-3-2 receipt);
      registered D-3b units (array acceptance) and D-3c profiles; inputs resolved against the D-2 / D-3b ledgers) -> formal intake of the family's first-wave D-2 banks (3 sizes x
      3 positions x 2 systems; E1: 3 sizes x 1 position) and, for a non-E1 family, of the 12-position banks (D-2 reuse + D-3b added; D-3c registered plans rebuilt from the
      registered ordered UIDs, assembled 12-position inputs bound to the accepted D-3c fingerprints, live twelve_official_gate with keyword plan identity / table) -> per-size
      first-wave views (registered id map / size prior; position map = configuration suffix) -> step1_engine.d4c1_partial.calibrate_family_partial(mode='official', campaign,
      target commitment, registered W2 context SHA, registered pseudo columns, 12-position inputs + registered asset) -> publication of the partial record + archive ->
      verify_partial_record over the published archive (position sources / plans / 12-position Results / per-pseudo eligibility re-derived) -> pseudo identity re-bound
      (the columns actually consumed: record SHA == registered column constants). NO aggregation, no usable, no label.
  --mode combine --partial F=DIR (x4)   byte-exact merge of the four partial archives, each published partial record re-read from its archive (payload SHA), verified, then
      step1_engine.d4c1_partial.combine_family_partials (common identity / family identity / per-pseudo any-family truth / Wilson on the fixed n / run-reader verification)
      -> sealed calibration record + archive -> load_combined_sealed_record round trip. Partials of different campaigns / commitments / pseudo columns / sources are rejected.
  --probe-n N (with --mode partial)   formal intake + official gate, but only the first N registered pseudo rows: a TIMING / RESOURCE probe for the Colab budget (never a
      formal record; probe=True; separate file names).
  --selftest-small   synthetic four-family banks (tests/fixture32; smoke gate; small n): four partials in separate archives -> merge -> combine -> single-process
      calibrate_sealed on the same inputs -> content equality (strip_provenance); refusals; never D4C1_PASS.
D4C-2a (engine 0.108.0; audit D4C2-probe: design / implementation / small tests GO, Colab execution NOT granted by that decision):
  --mode partial --row-range A:B   a SUB-partial: the same formal intake / plans / views / 12-position inputs / official gate, then step1_engine.d4c1_subpartial.calibrate_family_subpartial
      on the GLOBAL rows [A, B) of the registered pseudo columns (schema family_subpartial_calibration_v1; archived per-row records carry the global pseudo_index); publication of
      the sub-partial record + archive; verify_subpartial_record (run reader with the row offset); pseudo identity re-bound (global column SHAs == registered constants, slice SHAs
      == the slice consumed). Flag D4C1_SUBPARTIAL_PASS (never D4C1_PARTIAL_PASS). Every sub-partial is a durable unit: a lost runtime loses at most the open range.
  --mode combine-family --family F --subpartial DIR (xN)   byte-exact merge of the sub-partial archives; every published sub-partial record re-read from its archive and verified;
      step1_engine.d4c1_subpartial.combine_family_subpartials (ranges tile [0, n) exactly once; common identity; content identical to the single-process family partial apart from
      binding['subpartials']) -> the family partial record + archive published under the family-partial file names, so --mode combine consumes it unchanged. D4C1_PARTIAL_PASS
      requires every sub-partial run to carry D4C1_SUBPARTIAL_PASS (formal).
  --instrument (with --probe-n)   the probe partial runs under step1_engine.profiling.Profiler (timing wrappers + cProfile; the record is unchanged): d4c1_probe_<F>_profile.json.
  --mode screen --family F [--row-range A:B]   formal first-wave intake / plans / views only (no 12-position inputs), registered W2 decisions -> step1_engine.infeasibility.
      envelope_screen_family: the sufficient count-envelope screen (exact matched hit rates over the three positions x N0 / N4, max/min <= 2, positivity; W2 unknown in >= 1 size and no
      W2 True) -> rows whose eligible truth cannot be False (blocking); published as d4c1_screen_<F>[_rA_B]_record.json. Not a calibration; no bootstrap / KDE; E1 refused.
  --mode certificate --screen DIR (xN) [--evaluated DIR (xN)]   step1_engine.infeasibility.infeasibility_certificate over the verified screen records (+ evaluated per-pseudo statuses of
      published partial / sub-partial records): proven blocking rows vs the first Wilson blocking count of the fixed n (2000: support 81 / strong 12) -> usable == True impossible
      (algebraic; no c / u / rate; no statement on the unevaluated rows). Published as d4c1_certificate_record.json; never a PASS flag of a calibration.
The target is never read here: --target-commitment is the 64-hex commitment (calibration_first.commit_target(t_target, nonce)); the nonce stays private. The partial must not
be used as a sealed calibration (load_sealed_record rejects it). OUTPUT is a non-existent or EMPTY real directory disjoint from every input / source root (read-only inputs).
D4C1_PARTIAL_PASS / D4C1_COMBINE_PASS require production_official, no self-test / probe flag, all REQUIRED gates True and rc 0; the scientific outcome is not a PASS condition."""
from __future__ import annotations
import os
for _k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"): os.environ.setdefault(_k, "2")
import argparse, copy, hashlib, json, sys, time, traceback, resource
import numpy as np

REQUIRED_COMMON = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_phaseC_members", "G_env_lock", "G_external_loader_sha", "G_twelve_context", "G_w2_context_registered", "G_pseudo_registered", "G_twelve_asset_registered", "G_commitment_form")
REQUIRED_PARTIAL = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_phaseC_members", "G_env_lock", "G_external_loader_sha", "G_twelve_context", "G_w2_context_registered", "G_pseudo_registered", "G_twelve_asset_registered", "G_commitment_form",
                    "G_d3b_units_accepted", "G_inputs_resolved", "G_first_wave_supplies", "G_plans_fixed", "G_first_wave_views", "G_twelve_inputs", "G_twelve_gate", "G_partial_computed", "G_plan_objects_stable", "G_partial_published", "G_partial_verified", "G_pseudo_identity_bound", "G_record_saved")
REQUIRED_COMBINE = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_phaseC_members", "G_env_lock", "G_external_loader_sha", "G_twelve_context", "G_w2_context_registered", "G_pseudo_registered", "G_twelve_asset_registered", "G_commitment_form",
                    "G_partials_loaded", "G_archives_merged", "G_partials_verified", "G_combined", "G_sealed_published", "G_sealed_loaded", "G_record_saved")
REQUIRED_SUBPARTIAL = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_phaseC_members", "G_env_lock", "G_external_loader_sha", "G_twelve_context", "G_w2_context_registered", "G_pseudo_registered", "G_twelve_asset_registered", "G_commitment_form", "G_row_range",
                       "G_d3b_units_accepted", "G_inputs_resolved", "G_first_wave_supplies", "G_plans_fixed", "G_first_wave_views", "G_twelve_inputs", "G_twelve_gate", "G_partial_computed", "G_plan_objects_stable", "G_partial_published", "G_partial_verified", "G_pseudo_identity_bound", "G_record_saved")
REQUIRED_COMBINE_FAMILY = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_phaseC_members", "G_env_lock", "G_external_loader_sha", "G_twelve_context", "G_w2_context_registered", "G_pseudo_registered", "G_twelve_asset_registered", "G_commitment_form",
                           "G_subpartials_loaded", "G_archives_merged", "G_subpartials_verified", "G_rows_tiled", "G_family_combined", "G_partial_published", "G_partial_verified", "G_pseudo_identity_bound", "G_record_saved")
REQUIRED_SCREEN = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_phaseC_members", "G_env_lock", "G_external_loader_sha", "G_twelve_context", "G_w2_context_registered", "G_pseudo_registered", "G_twelve_asset_registered", "G_commitment_form",
                   "G_inputs_resolved", "G_first_wave_supplies", "G_plans_fixed", "G_first_wave_views", "G_row_range", "G_screen_computed", "G_screen_published", "G_pseudo_identity_bound", "G_record_saved")
REQUIRED_CERTIFICATE = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_phaseC_members", "G_external_loader_sha", "G_twelve_context", "G_w2_context_registered", "G_pseudo_registered", "G_twelve_asset_registered", "G_commitment_form",
                        "G_sources_loaded", "G_certificate_computed", "G_certificate_published", "G_record_saved")
assert REQUIRED_PARTIAL[:len(REQUIRED_COMMON)] == REQUIRED_COMMON == REQUIRED_COMBINE[:len(REQUIRED_COMMON)] == REQUIRED_SUBPARTIAL[:len(REQUIRED_COMMON)] == REQUIRED_COMBINE_FAMILY[:len(REQUIRED_COMMON)] == REQUIRED_SCREEN[:len(REQUIRED_COMMON)]
assert REQUIRED_SUBPARTIAL == REQUIRED_COMMON + ("G_row_range",) + REQUIRED_PARTIAL[len(REQUIRED_COMMON):] and REQUIRED_CERTIFICATE[:10] == tuple(k for k in REQUIRED_COMMON if k != "G_env_lock")
REQUIRED_SELFTEST = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_selftest_fixture", "G_selftest_partials", "G_selftest_merge", "G_selftest_combined", "G_selftest_single", "G_selftest_equivalence", "G_selftest_refusals", "G_record_saved")
FAMILIES = ("E1", "E2", "E7", "E8"); TWELVE_FAMILIES = ("E2", "E7", "E8"); SIZES = ("L1.00", "L1.20", "L1.50"); TWELVE_RECEIPT = "B3_2A_7240c06f255c"


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def _hex64(v): return isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)
def _peak_rss_mb(): return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024.0 / 1e6)


def _rss_mb():
    try:
        import psutil; return float(psutil.Process().memory_info().rss / 1e6)
    except Exception: return _peak_rss_mb()


def _publish_json(path, document):
    snapshot = copy.deepcopy(document); options = dict(indent=1, ensure_ascii=False, default=str, allow_nan=False)
    expected = json.dumps(snapshot, **options).encode("utf-8"); tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(snapshot, fh, **options); fh.flush(); os.fsync(fh.fileno())
        if open(tmp, "rb").read() != expected: raise RuntimeError("JSON publication differs from the computed snapshot: " + path)
        os.replace(tmp, path)
        if open(path, "rb").read() != expected: raise RuntimeError("published JSON differs from the computed snapshot: " + path)
        return dict(sha256=hashlib.sha256(expected).hexdigest(), bytes=len(expected))
    finally:
        if os.path.exists(tmp):
            try: os.remove(tmp)
            except OSError: pass


def _json_snapshot(path):
    data = open(path, "rb").read()
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return data, json.loads(data, object_pairs_hook=pairs, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def _strip_self(d, keys):
    """A record without its self-referencing binding entries (the archived copy is written before they exist)."""
    d = copy.deepcopy(d); d["binding"] = {k: v for k, v in d["binding"].items() if k not in keys}; return d


def _publish_record(path, obj):
    """Publish an engine record (serialization.dumps canonical bytes) and verify the bytes written."""
    from step1_engine import serialization as ser
    body = ser.dumps(obj).encode("utf-8"); tmp = path + ".tmp"
    with open(tmp, "wb") as fh: fh.write(body); fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, path)
    if open(path, "rb").read() != body: raise RuntimeError("record publication differs from the computed bytes: " + path)
    return dict(sha256=hashlib.sha256(body).hexdigest(), bytes=len(body))


def resolve_d2_family_root(d2_root, fam, d2l):
    """The accepted D-2 run of ONE family: registry bytes == ledger bank_registry_sha256; family / formal; every first-wave unit (b0 / b1 / fit of the configurations and the
    family reference) of the ledger with the same manifest SHA and its registered path under the ledger run root; COMPLETE.json present. Returns (ok, info, reasons)."""
    reasons = []; root = os.path.realpath(d2_root); rp = os.path.join(root, "d2_bank_registry.json"); fam_l = (d2l.get("families") or {}).get(fam)
    if fam_l is None: return False, {}, [f"{fam}: family not in the registered D-2 ledger"]
    if not os.path.isdir(root): return False, {}, [f"{fam}: D-2 root is not a directory"]
    if not os.path.isfile(rp) or os.path.islink(rp): return False, {}, [f"{fam}: d2_bank_registry.json missing"]
    if sha(rp) != (fam_l.get("records") or {}).get("bank_registry_sha256"): return False, {}, [f"{fam}: d2_bank_registry.json bytes differ from the registered run record"]
    _, d2reg = _json_snapshot(rp)
    if d2reg.get("family") != fam or d2reg.get("formal") is not True: reasons.append(f"{fam}: registry family / formal flag")
    units = {u: v for u, v in fam_l["units"].items() if not u.endswith("_w2")}; dirs = d2reg.get("directories") or {}
    for u, v in units.items():
        e = dirs.get(u) or {}
        if e.get("manifest_sha256") != v["manifest_sha256"]: reasons.append(f"{fam}: {u} manifest SHA differs from the ledger unit")
        if not (isinstance(e.get("path"), str) and e["path"].rstrip("/") == v["path"].rstrip("/") and e["path"].startswith(fam_l["run_root"].rstrip("/") + "/")): reasons.append(f"{fam}: {u} registered path is not under the ledger run root")
        if not os.path.isfile(os.path.join(root, u, "COMPLETE.json")): reasons.append(f"{fam}: {u}/COMPLETE.json missing")
    return (not reasons), dict(root=root, run_id=fam_l["run_id"], run_root=fam_l["run_root"], commit=fam_l["commit"], registry_sha256=sha(rp), units=sorted(units)), reasons


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mt", required=True); ap.add_argument("--phaseb", required=True); ap.add_argument("--phasec", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--mode", choices=("partial", "combine", "combine-family", "screen", "certificate"), default="partial"); ap.add_argument("--family", default=None)
    ap.add_argument("--row-range", default=None, help="partial: A:B -> a SUB-partial over the global rows [A, B) of the registered pseudo columns (D4C-2a); screen: the rows to screen (default all)")
    ap.add_argument("--subpartial", action="append", default=[], help="combine-family: the published output directory of one sub-partial run of this family (one entry per range)")
    ap.add_argument("--screen", action="append", default=[], help="certificate: the published output directory of one screen run"); ap.add_argument("--evaluated", action="append", default=[], help="certificate: the published output directory of a partial / sub-partial run (evaluated per-pseudo statuses)")
    ap.add_argument("--instrument", action="store_true", help="probe only: run the partial under step1_engine.profiling.Profiler (wrappers + cProfile) and publish the profile record")
    ap.add_argument("--d2-root", default=None, help="partial: the accepted D-2 run of this family (its out/d2 directory)"); ap.add_argument("--d3b-root", action="append", default=[], help="partial (non-E1): SIZE=PATH, the accepted D-3b partition run's out/d3b directory of that size (three entries)")
    ap.add_argument("--partial", action="append", default=[], help="combine: FAMILY=DIR, the published output directory of that family's partial run (four entries)")
    ap.add_argument("--target-commitment", default=None, help="64-hex commitment of the observed target (calibration_first.commit_target); the nonce is never given here"); ap.add_argument("--campaign-id", default=None, help="campaign identity shared by the four partials and the combination")
    ap.add_argument("--profile", default="production_official"); ap.add_argument("--probe-n", type=int, default=None, help="partial: timing / resource probe on the first N registered pseudo rows (never a formal record)")
    ap.add_argument("--selftest-small", action="store_true", help="connection path on the generators' small synthetic banks (formal=False intakes; smoke gates; first --selftest-n registered pseudo rows); never PASS"); ap.add_argument("--selftest-fixture", action="store_true", help="in-process equivalence self-test on the synthetic four-family fixture (tests/fixture32); never PASS"); ap.add_argument("--selftest-skip-env-lock", action="store_true"); ap.add_argument("--selftest-n", type=int, default=3); ap.add_argument("--selftest-B", type=int, default=20); ap.add_argument("--selftest-B-KDE", type=int, default=25)
    ap.add_argument("--attempt-id", default=None); ap.add_argument("--launcher-lock-sha256", default=None)
    a = ap.parse_args(); t0 = time.time(); selftest = a.selftest_small or a.selftest_skip_env_lock or a.selftest_fixture; formal = not a.selftest_small; probe = a.probe_n is not None
    rows = None
    if a.row_range is not None:
        try:
            ra, rb = a.row_range.split(":"); rows = (int(ra), int(rb))
            if not (0 <= rows[0] < rows[1]): raise ValueError
        except ValueError: print("--row-range must be A:B with 0 <= A < B", file=sys.stderr); return 2
    if a.instrument and not probe: print("--instrument requires --probe-n (measurement runs are never formal records)", file=sys.stderr); return 2
    if rows is not None and probe: print("--row-range and --probe-n are exclusive", file=sys.stderr); return 2
    subpartial = (a.mode == "partial" and rows is not None)
    if os.path.islink(a.out): print("OUT must not be a symbolic link", file=sys.stderr); return 2
    out = os.path.realpath(a.out); out_exists = os.path.lexists(out)
    if out_exists and (not os.path.isdir(out) or os.listdir(out)): print("OUT must be a fresh (non-existent or empty) real directory", file=sys.stderr); return 2
    def inside(p, q): p, q = os.path.realpath(p), os.path.realpath(q); return p == q or p.startswith(q.rstrip(os.sep) + os.sep)
    d3b_roots = {}; partial_dirs = {}
    for x in a.d3b_root:
        if "=" not in x: print("--d3b-root must be SIZE=PATH", file=sys.stderr); return 2
        s, p = x.split("=", 1); d3b_roots[s] = p
    for x in a.partial:
        if "=" not in x: print("--partial must be FAMILY=DIR", file=sys.stderr); return 2
        f, p = x.split("=", 1); partial_dirs[f] = p
    aux_dirs = {f"subpartial_{i}": p for i, p in enumerate(a.subpartial)}; aux_dirs.update({f"screen_{i}": p for i, p in enumerate(a.screen)}); aux_dirs.update({f"evaluated_{i}": p for i, p in enumerate(a.evaluated)})
    protected = dict(mt=a.mt, phaseb=a.phaseb, phasec=a.phasec, **({"d2_root": a.d2_root} if a.d2_root else {}), **{f"d3b_root_{s}": p for s, p in d3b_roots.items()}, **{f"partial_{f}": p for f, p in partial_dirs.items()}, **aux_dirs)
    clash = [k for k, p in protected.items() if inside(out, p) or inside(p, out)]
    if clash: print("output must be disjoint from the inputs and the source roots (" + ", ".join(clash) + ")", file=sys.stderr); return 2
    if not out_exists: os.makedirs(out)
    REQUIRED = REQUIRED_SELFTEST if a.selftest_fixture else {"combine": REQUIRED_COMBINE, "combine-family": REQUIRED_COMBINE_FAMILY, "screen": REQUIRED_SCREEN, "certificate": REQUIRED_CERTIFICATE}.get(a.mode, REQUIRED_SUBPARTIAL if subpartial else REQUIRED_PARTIAL)
    rtag = (f"_r{rows[0]:04d}_{rows[1]:04d}" if rows is not None else "")
    tag = "selftest" if a.selftest_fixture else {"combine": "combine", "combine-family": f"partial_{a.family}", "screen": f"screen_{a.family}{rtag}", "certificate": "certificate"}.get(a.mode, (("probe_" if probe else ("subpartial_" if subpartial else "partial_")) + str(a.family) + (rtag if subpartial else "")))
    log = open(os.path.join(out, f"d4c1_{tag}_stdout.log"), "w"); G = {k: None for k in REQUIRED}
    R = dict(schema="d4c1_run_record_v1", mode=("selftest" if a.selftest_fixture else a.mode), family=a.family, stage="init", failures=[], notes=[], selftest=bool(selftest), formal=bool(formal), probe=bool(probe), probe_n=a.probe_n, profile=a.profile, out=out, out_preexisting_empty=bool(out_exists),
             subpartial=bool(subpartial), row_range=(list(rows) if rows is not None else None), instrument=bool(a.instrument),
             protected_roots={k: os.path.realpath(p) for k, p in protected.items()}, attempt=dict(attempt_id=a.attempt_id, launcher_lock_sha256=a.launcher_lock_sha256), campaign_id=a.campaign_id, target_commitment=a.target_commitment, stages_rss_mb={}, stages_peak_rss_mb={}, timings={})
    def note(*s):
        m = " ".join(str(x) for x in s); print(m, flush=True)
        try: log.write(m + "\n"); log.flush()
        except ValueError: pass
    def mark(stage): R["stages_rss_mb"][stage] = round(_rss_mb(), 1); R["stages_peak_rss_mb"][stage] = round(_peak_rss_mb(), 1); R["timings"][stage] = round(time.time() - t0, 3)
    def finish(code, stage="final"):
        R["stage"] = stage; R["gates"] = G; R["required_inventory"] = list(REQUIRED); R["required_all_true"] = all(G.get(k) is True for k in REQUIRED); ok = bool(R["required_all_true"] and a.profile == "production_official" and not selftest and not probe and code == 0)
        R["D4C1_PARTIAL_PASS"] = bool(ok and ((a.mode == "partial" and not subpartial) or (a.mode == "combine-family" and R.get("subpartials_all_pass") is True))); R["D4C1_COMBINE_PASS"] = bool(ok and a.mode == "combine"); R["D4C1_SUBPARTIAL_PASS"] = bool(ok and subpartial)
        R["D4C1_SCREEN_COMPLETE"] = bool(R["required_all_true"] and a.mode == "screen" and code == 0 and not selftest); R["D4C1_CERTIFICATE_COMPLETE"] = bool(R["required_all_true"] and a.mode == "certificate" and code == 0 and not selftest); R["seconds"] = time.time() - t0; mark("final")
        note("run finalization | stage:", stage, "| gates:", json.dumps(G)); log.close()
        try: _publish_json(os.path.join(out, f"d4c1_{tag}_run.json"), R)
        except Exception as write_error: print("run record could not be published/verified; no PASS: " + repr(write_error), file=sys.stderr); return 1
        print("run record published and verified; D4C1_PARTIAL_PASS =", R["D4C1_PARTIAL_PASS"], "D4C1_COMBINE_PASS =", R["D4C1_COMBINE_PASS"], "D4C1_SUBPARTIAL_PASS =", R["D4C1_SUBPARTIAL_PASS"]); return code
    try:
        if a.profile != "production_official": R["failures"].append("profile"); return finish(1)
        sys.path.insert(0, a.phaseb)
        pins_path = os.path.join(a.phaseb, "d", "d3_pins.json"); pins = json.load(open(pins_path)); R["pins_sha256"] = sha(pins_path); inv_path = os.path.join(a.phaseb, "B2_completion_inventory.json"); inv0 = json.load(open(inv_path))
        G["G_pins_loaded"] = bool(pins.get("schema") == "d3_pins_v1" and inv0.get("d_sha256", {}).get("d/d3_pins.json") == R["pins_sha256"])
        from step1_engine import __version__; from step1_engine.checkpoint import module_shas
        G["G_engine_inventory"] = (inv0["modules"] == module_shas() and inv0["engine_version"] == __version__ == pins["engine_version"]); me = os.path.abspath(__file__); G["G_script_sha"] = (inv0.get("d_sha256", {}).get("d/d4c1_calibration.py") == sha(me)); R["engine_version"] = __version__
        R["source"] = dict(script_sha256=sha(me), inventory_sha256=sha(inv_path), pins_sha256=R["pins_sha256"], engine_version=__version__, phaseb=os.path.realpath(a.phaseb), mt=os.path.realpath(a.mt))
        if not (G["G_pins_loaded"] and G["G_engine_inventory"] and G["G_script_sha"]): R["failures"].append("preflight binding failed"); return finish(1, "preflight")
        from step1_engine import serialization as ser
        from step1_engine.archive import Archive, ArchiveRef, merge_archives
        from step1_engine.d4c1_partial import calibrate_family_partial, combine_family_partials, verify_partial_record, load_partial_record, load_combined_sealed_record, strip_provenance, PARTIAL_KIND
        from step1_engine.d4c1_subpartial import calibrate_family_subpartial, combine_family_subpartials, verify_subpartial_record, load_subpartial_record
        from step1_engine.calibration_first import calibrate_sealed, load_sealed_record, commit_target
        from step1_engine.errors import InputContractError
        if a.selftest_fixture: return _selftest(a, out, R, G, note, mark, finish, ser, Archive, merge_archives, calibrate_family_partial, combine_family_partials, verify_partial_record, load_sealed_record, calibrate_sealed, commit_target, strip_provenance, InputContractError)
        # ---- Phase C members, registered environment HARD gate, frozen loader, context
        pc = json.load(open(os.path.join(a.phasec, "PACKET_INVENTORY.json"))); members = {}
        for d, _, fs in os.walk(a.phasec):
            for f in fs:
                rel = os.path.relpath(os.path.join(d, f), a.phasec)
                if rel != "PACKET_INVENTORY.json" and "__pycache__" not in rel: members[rel] = dict(sha256=sha(os.path.join(d, f)), bytes=os.path.getsize(os.path.join(d, f)))
        G["G_phaseC_members"] = bool(sha(os.path.join(a.phasec, "PACKET_INVENTORY.json")) == pins["phaseC_inventory_sha256"] and set(members) == set(pc["files"]) and all(members[k] == dict(sha256=v["sha256"], bytes=v["bytes"]) for k, v in pc["files"].items()))
        from step1_engine.official_gate import current_env, _blas_check, EXPECTED_VERS, B_KDE as REG_B_KDE, N_FIT as REG_N_FIT, M_FIT as REG_M_FIT
        from step1_engine.rules_config import RULES
        env = current_env(); ex = pins["environment"]
        try:
            import camb as _camb; env["camb"] = _camb.__version__
        except Exception: env["camb"] = None
        vers_ok = all(env.get(k) == ex[k] for k in ("python", "numpy", "scipy", "healpy", "pot", "camb")) and all(env.get(k) == v for k, v in EXPECTED_VERS.items()); blas_ok = bool(_blas_check(env.get("blas_threads")))
        try:
            import threadpoolctl; TPC = threadpoolctl.threadpool_limits(limits=2)
        except Exception: TPC = None
        G["G_env_lock"] = bool(vers_ok and blas_ok); R["env"] = env; R["env_gate"] = dict(versions_ok=vers_ok, pools_ok=blas_ok, expected=ex)
        if not G["G_env_lock"] and not a.selftest_skip_env_lock: R["failures"].append("registered environment gate failed"); return finish(1, "environment")
        from step1_engine.production import D1_REGISTERED_RECEIPT, _verified_frozen_loader, intake_registered_covariance, build_family_input
        try: t1_, loader_id = _verified_frozen_loader(a.mt, D1_REGISTERED_RECEIPT["frozen_loaders"]); G["G_external_loader_sha"] = True; R["loader"] = loader_id
        except Exception as ex_: G["G_external_loader_sha"] = False; R["loader_error"] = repr(ex_)
        from step1_engine.d3_profile import twelve_context, load_registered_bank_spec_v2, intake_twelve_covariance, build_twelve_size_input, assemble_twelve_family, twelve_official_gate, fix_family_plans, verify_plan_identity
        from step1_engine.d4c0_registry import load_registered_w2_context, load_registered_pseudo_columns
        from step1_engine.twelve_assets import intake_registered_twelve_assets
        from step1_engine.grid_registry import load_registry
        from step1_engine.grid_manifest import build_configuration_manifest
        ctx = twelve_context(a.phaseb); ident = ctx.identities; G["G_twelve_context"] = bool(ctx.verified and ident["config_map_sha256"] == pins["config_map_sha256"] and ident["covariance_receipt_sha256"] == pins["covariance_receipt_sha256"]); R["context_identities"] = dict(ident); table = ctx.table; master_seed = table["master_seed"]
        reg = load_registry(os.path.join(a.phaseb, "tests/assets/a7_circle_geometry.csv"), os.path.join(a.phaseb, "tests/assets/a6_observer_design_points.json")); man = build_configuration_manifest(reg)
        try:
            w2ctx, w2view = load_registered_w2_context(a.phaseb, ctx); G["G_w2_context_registered"] = bool(w2ctx.context_sha256 == pins["d2w_context_sha256"] == w2view["context_sha256"] and sorted(w2ctx.decisions) == sorted(f"{f}/{s}" for f in TWELVE_FAMILIES for s in SIZES))
            R["w2_context"] = dict(context_sha256=w2ctx.context_sha256, asset_sha256=w2ctx.asset_sha256, attempt=w2view["attempt"], cases=w2view["cases"], ledger_sha256=w2view["ledger_sha256"], receipt_sha256=w2view["receipt_sha256"], acceptance_sha256=w2view["acceptance_sha256"])
        except Exception as ex_: G["G_w2_context_registered"] = False; R["w2_context_error"] = repr(ex_)
        try:
            cols = load_registered_pseudo_columns(a.phaseb, ctx); idn = cols["identity"]
            G["G_pseudo_registered"] = bool(cols["n"] == RULES.n_pseudo and idn["paired_sha256"] == pins["pseudo_paired_sha256"] and idn["T1_sha256"] == hashlib.sha256(np.ascontiguousarray(np.asarray(cols["T1"], np.float64)).tobytes()).hexdigest() and idn["T2_sha256"] == hashlib.sha256(np.ascontiguousarray(np.asarray(cols["T2"], np.float64)).tobytes()).hexdigest())
            R["pseudo"] = dict(n=cols["n"], identity=idn, attempt=cols["view"]["attempt"], ledger_sha256=cols["view"]["ledger_sha256"], receipt_sha256=cols["view"]["receipt_sha256"], acceptance_sha256=cols["view"]["acceptance_sha256"], order=cols["view"]["order"])
        except Exception as ex_: G["G_pseudo_registered"] = False; R["pseudo_error"] = repr(ex_)
        try:
            tasset = intake_registered_twelve_assets(os.path.join(a.phaseb, "registered_assets", "b3_2_twelve_assets.json"), reg, TWELVE_RECEIPT); G["G_twelve_asset_registered"] = bool(tasset.sha256 == ident["twelve_assets_sha256"]); R["twelve_asset"] = dict(receipt=TWELVE_RECEIPT, sha256=tasset.sha256)
        except Exception as ex_: G["G_twelve_asset_registered"] = False; R["twelve_asset_error"] = repr(ex_)
        G["G_commitment_form"] = bool(_hex64(a.target_commitment) and isinstance(a.campaign_id, str) and len(a.campaign_id) >= 8)
        if not all(G[k] for k in REQUIRED_COMMON if k != "G_env_lock"): R["failures"].append("trusted-input binding failed"); return finish(1, "trusted_inputs")
        registered = dict(shared_null_asset_sha256=w2ctx.asset_sha256, w2_context_sha256=w2ctx.context_sha256, registry_sha256=reg.registry_sha256, twelve_assets_sha256=tasset.sha256)
        campaign = dict(id=a.campaign_id + ("" if formal else "__SELFTEST"), target_commitment=a.target_commitment, w2_context_sha256=w2ctx.context_sha256, pseudo_paired_sha256=idn["paired_sha256"], n_pseudo=cols["n"], formal=bool(formal), execution_policy="one family per partial run (Colab High-RAM); official gate live per run; combine in the same source binding")
        mark("preflight")
        if a.mode == "combine": return _combine(a, out, R, G, note, mark, finish, reg, man, registered, campaign, cols, formal, Archive, ArchiveRef, merge_archives, load_partial_record, verify_partial_record, combine_family_partials, load_combined_sealed_record, _publish_record, ser)
        if a.mode == "combine-family": return _combine_family(a, out, R, G, note, mark, finish, reg, man, registered, campaign, cols, formal, Archive, ArchiveRef, merge_archives, load_subpartial_record, verify_subpartial_record, combine_family_subpartials, load_partial_record, verify_partial_record, _publish_record, ser)
        if a.mode == "certificate": return _certificate(a, out, R, G, note, mark, finish, cols, formal, _publish_record, ser)
        # ================================================================================================================================================ partial
        fam = a.family
        if fam not in FAMILIES: R["failures"].append("family"); return finish(1, "scope")
        if a.d2_root is None: R["failures"].append("--d2-root required"); return finish(1, "inputs")
        from step1_engine.d3b_ledger import intake_registered_d3b_units
        from step1_engine.d3c_ledger import intake_registered_d3c_profiles, rebuild_registered_plans, verify_consumer_family_inputs
        from step1_engine.d2_rng import native_reference_root, group_for
        from step1_engine.d2_bank import intake_registered_bank, FIT_K
        from step1_engine.d3_bank import intake_twelve_bank
        from step1_engine.formal_runner import input_fingerprint
        from step1_engine.legacy_kernel import LegacyKernel
        twelve = fam in TWELVE_FAMILIES
        U = P3c = None
        try:
            if twelve and formal: U = intake_registered_d3b_units(a.phaseb, ctx); P3c = intake_registered_d3c_profiles(a.phaseb, ctx)
            G["G_d3b_units_accepted"] = bool((not twelve) or (not formal) or (U.verified and U.array_accepted is True and U.receipt_sha256 == pins.get("d3b_outer_receipt_sha256") and P3c.verified))
            if twelve and formal: R["d3b"] = dict(ledger_sha256=U.ledger_sha256, receipt_sha256=U.receipt_sha256); R["d3c"] = dict(ledger_sha256=P3c.ledger_sha256, receipt_sha256=P3c.receipt_sha256)
            elif twelve: R["d3b"] = dict(note="SELF-TEST: synthetic D-3b banks (no registered unit / D-3c binding)")
        except Exception as ex_: G["G_d3b_units_accepted"] = False; R["d3b_error"] = repr(ex_)
        if not G["G_d3b_units_accepted"]: R["failures"].append("registered D-3b units / D-3c profiles not accepted"); return finish(1, "trusted_inputs")
        spec2 = load_registered_bank_spec_v2(ctx) if twelve else None; d2s = ctx.d2_spec; d2l = ctx.d2_ledger; B_sel, Bk_sel = (RULES.B, REG_B_KDE) if formal else (a.selftest_B, a.selftest_B_KDE)
        if formal: ok_in, d2info, reasons = resolve_d2_family_root(a.d2_root, fam, d2l)
        else:
            d2info = dict(root=os.path.realpath(a.d2_root), selftest=True); reasons = []; ok_in = os.path.isfile(os.path.join(d2info["root"], "d2_bank_registry.json"))
            if ok_in: _, d2reg = _json_snapshot(os.path.join(d2info["root"], "d2_bank_registry.json")); ok_in = d2reg.get("family") == fam
            if not ok_in: reasons.append(f"{fam}: self-test D-2 root does not hold this family's registry")
        R["inputs"] = dict(d2=d2info, d3b={}, resolution_failures=reasons)
        twelve_inputs_supplied = (bool(d3b_roots) or formal) and a.mode != "screen"
        if a.mode == "screen" and d3b_roots: reasons.append("the screen takes no D-3b roots (first-wave views only)"); ok_in = False
        if twelve and not twelve_inputs_supplied and a.mode != "screen": R["notes"].append("SELF-TEST without D-3b roots: no 12-position inputs (an expanded pseudo stays provisional / unknown); never allowed in a formal run")
        if twelve and twelve_inputs_supplied:
            if set(d3b_roots) != set(SIZES): reasons.append("--d3b-root must give exactly the three sizes"); ok_in = False
            else:
                for s, p in d3b_roots.items():
                    p = os.path.realpath(p); rp = os.path.join(p, "d3_bank_registry.json")
                    if not os.path.isfile(rp): reasons.append(f"{s}: d3_bank_registry.json missing"); ok_in = False; continue
                    _, d3reg = _json_snapshot(rp)
                    if formal:
                        Pt = U.partitions[f"{fam}_{s}"]; okp = d3reg.get("family") == fam and d3reg.get("sizes") == [s] and d3reg.get("formal") is True and all(d3reg["directories"][u]["manifest_sha256"] == Pt["units"][u]["manifest_sha256"] for u in Pt["units"]) and d3reg.get("spec_v2_sha256") == spec2["spec_sha256"]
                        R["inputs"]["d3b"][s] = dict(root=p, run_id=Pt["run_id"], run_root=Pt["run_root"])
                    else: okp = d3reg.get("family") == fam and d3reg.get("sizes") == [s] and d3reg.get("spec_v2_sha256") == spec2["spec_sha256"]; R["inputs"]["d3b"][s] = dict(root=p, selftest=True)
                    if not okp: reasons.append(f"{s}: D-3b registry does not resolve to the accepted partition"); ok_in = False
        elif d3b_roots: reasons.append("E1 takes no D-3b roots"); ok_in = False
        G["G_inputs_resolved"] = bool(ok_in)
        if not ok_in: R["failures"].append("inputs do not resolve to the accepted runs: " + "; ".join(reasons)); return finish(1, "inputs")
        # ---- first-wave intake (D-2 fixed inputs; read-only) and, for a twelve family, the added 12-position banks
        d1dir = os.path.join(a.phaseb, "registered_assets", "d1"); d1reg = json.load(open(os.path.join(d1dir, "d1_cov_registry.json"))); k = LegacyKernel(a.mt); S_I, _ = k.psqrt(k.C_ISO)
        d2_root = d2info["root"]; ref_dirs = {b: os.path.join(d2_root, f"ref_{fam}_b{b}") for b in (0, 1)}; ref_fit = os.path.join(d2_root, f"ref_{fam}_fit")
        fw_rows = sorted((c for c in d2s["configurations"].values() if c["family"] == fam), key=lambda c: c["config_id"]); fw = {s: {"matched": [], "native": []} for s in SIZES}; R["supplies"] = {}; n_sup = 0
        for c in fw_rows:
            cid = c["config_id"]; s = c["size_id"]; tt = time.time()
            cov = intake_registered_covariance(cid, reg, d1dir, a.mt); covm = json.load(open(os.path.join(d1dir, d1reg["configurations"][str(cid)]["cov_file"] + ".manifest.json")))
            roots = dict(model_matched=cov["S_matched"], model_native=cov["S_native"], ref_native=native_reference_root(cov["c_ct"]), ref_matched=S_I)
            eval_dirs = {b: os.path.join(d2_root, f"cfg{cid}_b{b}") for b in (0, 1)}; fit_dir = os.path.join(d2_root, f"cfg{cid}_fit"); want = d2l["families"][fam]["units"]
            for system in ("matched", "native"):
                sup, info = intake_registered_bank(cid, system, eval_dirs, ref_dirs, fit_dir, ref_fit, roots, covm, table, formal=formal)
                if formal:
                    got = dict(cfg_b0=info["manifests"]["eval"][0], cfg_b1=info["manifests"]["eval"][1], cfg_fit=info["manifests"]["fit"], ref_b0=info["manifests"]["ref"][0], ref_b1=info["manifests"]["ref"][1], ref_fit=info["manifests"]["ref_fit"])
                    exp = dict(cfg_b0=want[f"cfg{cid}_b0"]["manifest_sha256"], cfg_b1=want[f"cfg{cid}_b1"]["manifest_sha256"], cfg_fit=want[f"cfg{cid}_fit"]["manifest_sha256"], ref_b0=want[f"ref_{fam}_b0"]["manifest_sha256"], ref_b1=want[f"ref_{fam}_b1"]["manifest_sha256"], ref_fit=want[f"ref_{fam}_fit"]["manifest_sha256"])
                    if got != exp: raise RuntimeError(f"config {cid}/{system}: D-2 units are not the registered ledger units")
                fw[s][system].append(sup); R["supplies"][f"{cid}/{system}"] = dict(origin="first_wave_D1", receipt=cov["receipt"], cov_file_sha256=cov["cov_file_sha256"], cov_array_sha256=cov["cov_array_sha256"], manifests=info["manifests"], n_clusters=info["n_clusters"], fitting_clusters=info["fitting_clusters"]); n_sup += 1
            note(f"  first-wave intake {cid} ({s}) {time.time()-tt:.0f}s rss {_rss_mb():.0f} MB")
        npos = 1 if fam == "E1" else 3
        G["G_first_wave_supplies"] = bool(n_sup == 2 * npos * len(SIZES) and all(len(fw[s][sy]) == npos for s in SIZES for sy in ("matched", "native"))); mark("first_wave_intake")
        if not G["G_first_wave_supplies"]: R["failures"].append("first-wave supply count"); return finish(1, "intake")
        first = fw[SIZES[0]]["matched"][0]; uids = list(first.cluster_uids); m = first.m; b0 = first.batches[0]; b1 = first.batches[1]; K0, K1 = (b0[1] - b0[0]) // m, (b1[1] - b1[0]) // m; uids_b0, uids_b1 = uids[:K0], uids[K0:K0 + K1]; K_fit = int(first.fitting.cid.max()) + 1; n_fit = int(len(first.fitting.cid)); g_eval = group_for(table, "evaluation", fam)
        ok_u = (len(uids) == K0 + K1 and all(u.batch_id == 0 and u.purpose_id == 200 and u.crn_group_id == g_eval and u.rotation_index == i for i, u in enumerate(uids_b0)) and all(u.batch_id == 1 and u.purpose_id == 200 and u.crn_group_id == g_eval and u.rotation_index == i for i, u in enumerate(uids_b1)))
        for s in SIZES:
            for sy in ("matched", "native"):
                for sup in fw[s][sy]: ok_u &= (list(sup.cluster_uids) == uids and sup.batches == first.batches and sup.m == m and int(sup.fitting.cid.max()) + 1 == K_fit and len(sup.fitting.cid) == n_fit and np.array_equal(sup.fitting.cid, first.fitting.cid))
        if formal: ok_u &= (K0 == RULES.N0 // RULES.m and K1 == (RULES.N_max - RULES.N0) // RULES.m and m == RULES.m and K_fit == REG_N_FIT // REG_M_FIT == FIT_K and n_fit == REG_N_FIT)
        R["uids"] = dict(K0=K0, K1=K1, m=m, K_fit=K_fit, n_fit=n_fit, evaluation_group=g_eval, ordered_uid_sha256=hashlib.sha256(json.dumps([list(u.as_tuple()) for u in uids]).encode()).hexdigest())
        # ---- plans: twelve families from the REGISTERED D-3c ordered UIDs (rebuilt; identity == accepted); E1 from its D-2 bank UIDs with the registered constants
        if twelve and formal:
            plans, fplans, plan_ident = rebuild_registered_plans(P3c, fam, table); ou = P3c.ordered_uids(fam)
            ok_p = ok_u and ([tuple(u.as_tuple()) for u in uids_b0] == ou[0] and [tuple(u.as_tuple()) for u in uids_b1] == ou[1]); src = "registered D-3c profile (rebuilt from the registered ordered UIDs)"
        else:
            plans, fplans, plan_ident = fix_family_plans(table, fam, {0: uids_b0, 1: uids_b1}, K_fit, master_seed, B=B_sel, B_KDE=Bk_sel); ok_p = ok_u and verify_plan_identity(plans, fplans, plan_ident, table=table, family=fam) and plan_ident["B"] == B_sel and plan_ident["B_KDE"] == Bk_sel and plan_ident["seeds"] == RULES.seeds
            src = ("E1: fix_family_plans over the registered D-2 E1 bank UIDs with the registered constants (not a D-3c profile)" if formal else "SELF-TEST: fix_family_plans over the synthetic bank UIDs with small B / B_KDE (never formal)")
        G["G_plans_fixed"] = bool(ok_p); R["plan_identity"] = dict(identity_sha256=plan_ident["identity_sha256"], B=plan_ident["B"], B_KDE=plan_ident["B_KDE"], seeds=plan_ident["seeds"], source=src); mark("plans")
        if not ok_p: R["failures"].append("ordered UIDs / plans"); return finish(1, "plans")
        # ---- per-size first-wave views (registered id map / size prior; the SAME plan objects); position map = configuration suffix
        cases = {}
        for s in SIZES:
            fm_s = build_family_input(reg, man, fam, "matched", fw[s]["matched"], plans, fplans, size_ids=[s]); fn_s = build_family_input(reg, man, fam, "native", fw[s]["native"], plans, fplans, size_ids=[s])
            pmap = {c.evaluation_id: int(fm_s.grid_identity["evaluation_to_config"][c.evaluation_id]) % 100 for c in fm_s.configs}
            if sorted(pmap.values()) != list(range(1, npos + 1)): raise RuntimeError(f"{fam}/{s}: position map is not the configuration suffix 1..{npos}")
            cases[f"{fam}/{s}"] = (fm_s, fn_s, pmap)
        G["G_first_wave_views"] = bool(len(cases) == 3 and all(len(v[0].configs) == npos and len(v[1].configs) == npos and v[0].plans is plans and v[1].plans is plans and v[0].fit_plans is fplans and v[1].fit_plans is fplans for v in cases.values()))
        R["first_wave_fingerprints"] = {k: dict(matched=input_fingerprint(v[0]), native=input_fingerprint(v[1]), position_map=repr(sorted(v[2].items()))) for k, v in cases.items()}; mark("first_wave_views")
        if not G["G_first_wave_views"]: R["failures"].append("first-wave views"); return finish(1, "views")
        if a.mode == "screen": return _screen(a, out, R, G, note, mark, finish, reg, man, fam, cases, w2ctx, cols, idn, rows, formal, _publish_record, ser)
        # ---- 12-position inputs of a twelve family: D-2 reuse supplies + D-3b added banks; size inputs; assembled family bound to the accepted D-3c fingerprints; live twelve gate
        twelve_inputs = None
        if twelve and twelve_inputs_supplied:
            rows12 = sorted((c for c in spec2["configurations"].values() if c["family"] == fam), key=lambda c: (c["size_id"], c["position_index"])); sup12 = {s: {"matched": [], "native": []} for s in SIZES}
            for c in rows12:
                cid = c["config_id"]; s = c["size_id"]
                if c["mode"] == "reuse_D2_fixed_input":
                    for system in ("matched", "native"):
                        sup = next(q for q in fw[s][system] if q.config_id == cid); sup12[s][system].append(sup)     # the SAME supply objects as the first-wave views (arrays shared)
                else:
                    tt = time.time(); cov = intake_twelve_covariance(cid, a.phaseb, a.mt); roots = dict(model_matched=cov["S_matched"], model_native=cov["S_native"], ref_native=native_reference_root(cov["c_ct"]), ref_matched=S_I)
                    root3b = os.path.realpath(d3b_roots[s]); eval_dirs = {b: os.path.join(root3b, f"cfg{cid}_b{b}") for b in (0, 1)}; fit_dir = os.path.join(root3b, f"cfg{cid}_fit")
                    for system in ("matched", "native"):
                        sup, info = intake_twelve_bank(cid, system, eval_dirs, ref_dirs, fit_dir, ref_fit, roots, ctx, formal=formal, registered_units=(U if formal else None))
                        if list(sup.cluster_uids) != uids or sup.batches != first.batches or not np.array_equal(sup.fitting.cid, first.fitting.cid): raise RuntimeError(f"config {cid}/{system}: added bank is not on the family latent / fitting structure")
                        sup12[s][system].append(sup); R["supplies"][f"{cid}/{system}"] = dict(origin=cov["origin"], receipt=cov["receipt"], receipt_d3=cov["receipt_d3"], cov_file_sha256=cov["cov_file_sha256"], cov_array_sha256=cov["cov_array_sha256"], manifests=info["manifests"], n_clusters=info["n_clusters"], fitting_clusters=info["fitting_clusters"], d3b_ledger_sha256=info.get("d3b_ledger_sha256"))
                    note(f"  twelve intake {cid} ({s} position {c['position_index']}) {time.time()-tt:.0f}s rss {_rss_mb():.0f} MB")
            size_inputs = {s: (build_twelve_size_input(ctx, fam, s, "matched", sup12[s]["matched"], plans, fplans), build_twelve_size_input(ctx, fam, s, "native", sup12[s]["native"], plans, fplans)) for s in SIZES}
            fm12, fn12, fam_ident = assemble_twelve_family(ctx, fam, size_inputs)
            bind3c = verify_consumer_family_inputs(P3c, fam, fm12, fn12, plan_ident, table=table) if formal else dict(family=fam, note="SELF-TEST: no D-3c binding")   # formal: accepted D-3c fingerprints (both systems) + registered ordered UIDs + plan identity
            twelve_inputs = dict(size_inputs=size_inputs, position_ids={s: dict(size_inputs[s][0].grid_identity["position_index"]) for s in SIZES}, native_position_ids={s: dict(size_inputs[s][1].grid_identity["position_index"]) for s in SIZES})
            G["G_twelve_inputs"] = bool(all(len(size_inputs[s][0].configs) == 12 and len(size_inputs[s][1].configs) == 12 for s in SIZES) and fam_ident.get("full_surviving_scope") is True and bind3c["family"] == fam)
            R["twelve"] = dict(d3c_binding=bind3c, family_identity_keys=sorted(fam_ident), assembled_fingerprints=dict(matched=input_fingerprint(fm12), native=input_fingerprint(fn12))); mark("twelve_inputs")
            if not G["G_twelve_inputs"]: R["failures"].append("12-position inputs"); return finish(1, "twelve_inputs")
            gate12 = twelve_official_gate(fm12, fn12, mode=("official" if formal and not a.selftest_skip_env_lock else "smoke"), plan_identity=plan_ident, table=table)
            G["G_twelve_gate"] = bool(gate12.passed and gate12.diagnostics.get("environment_source") == "live_collected" and input_fingerprint(fm12) == R["twelve"]["assembled_fingerprints"]["matched"] and input_fingerprint(fn12) == R["twelve"]["assembled_fingerprints"]["native"])
            R["twelve"]["gate"] = dict(mode=gate12.mode, passed=bool(gate12.passed), required_failures=list(gate12.required_failures), environment_source=gate12.diagnostics.get("environment_source")); del fm12, fn12; mark("twelve_gate")
            if not G["G_twelve_gate"]: R["failures"].append("twelve official gate: " + "; ".join(gate12.required_failures[:5])); return finish(1, "twelve_gate")
        else: G["G_twelve_inputs"] = True; G["G_twelve_gate"] = True; R["twelve"] = dict(note=("E1: observer-homogeneous; no 12-position stage" if not twelve else "SELF-TEST: 12-position inputs not supplied"))
        # ---- the partial (official; the first-wave gate is live inside the engine entry); probe: first N rows only (never formal)
        T1, T2 = np.asarray(cols["T1"], np.float64), np.asarray(cols["T2"], np.float64); mode = "official" if (formal and not probe and not a.selftest_skip_env_lock) else "smoke"
        if probe:
            if not (isinstance(a.probe_n, int) and 1 <= a.probe_n < cols["n"]): R["failures"].append("--probe-n must be in 1..n-1"); return finish(1, "probe")
            T1, T2 = T1[:a.probe_n].copy(), T2[:a.probe_n].copy(); campaign = dict(campaign, id=campaign["id"] + "__PROBE", probe=True, n_rows=a.probe_n)
        elif not formal: T1, T2 = T1[:max(1, a.selftest_n)].copy(), T2[:max(1, a.selftest_n)].copy(); campaign = dict(campaign, n_rows=len(T1))
        archive = Archive(os.path.join(out, "archive"), deferred_index=True, flush_every=2000); tt = time.time(); n_rows = len(T1)
        if subpartial:
            if not formal: R["notes"].append("SELF-TEST: the row range addresses the first --selftest-n registered rows (the self-test columns); formal sub-partials address the full registered columns")
            G["G_row_range"] = bool(rows[1] <= len(T1) and (not formal or len(T1) == cols["n"] == RULES.n_pseudo))
            if not G["G_row_range"]: R["failures"].append(f"--row-range {rows[0]}:{rows[1]} exceeds the columns ({len(T1)} rows)"); return finish(1, "rows")
            n_rows = rows[1] - rows[0]                                                                                       # the campaign identity stays IDENTICAL across the sub-partials (the range lives in rows / subpartial_dependencies)
            rec = calibrate_family_subpartial(reg, man, fam, cases, w2ctx, w2ctx.context_sha256, T1, T2, archive, a.target_commitment, row_range=rows, mode=mode, campaign=campaign, twelve_inputs=twelve_inputs, twelve_assets=tasset, expected_twelve_assets_sha256=tasset.sha256, twelve_assets_receipt=TWELVE_RECEIPT)
        elif a.instrument:
            from step1_engine.profiling import Profiler, summarize
            with Profiler(cprofile=True) as prof:
                rec = calibrate_family_partial(reg, man, fam, cases, w2ctx, w2ctx.context_sha256, T1, T2, archive, a.target_commitment, mode=mode, campaign=campaign, twelve_inputs=twelve_inputs, twelve_assets=tasset, expected_twelve_assets_sha256=tasset.sha256, twelve_assets_receipt=TWELVE_RECEIPT)
            prof_rec = prof.report(note=f"probe {fam} n={len(T1)}; instrumented wall time is NOT the production speed")
            for line in summarize(prof_rec): note("  profile:", line)
            R["profile_record"] = _publish_json(os.path.join(out, f"d4c1_{tag}_profile.json"), prof_rec); R["profile_summary"] = dict(wall_seconds_total=prof_rec["wall_seconds_total"], segments=prof_rec["segments"]["count"], segment_wall_seconds=prof_rec["segments"]["wall_seconds"], outside_segments_wall_seconds=prof_rec["outside_segments_wall_seconds"], missing_targets=prof_rec["missing_targets"])
        else:
            rec = calibrate_family_partial(reg, man, fam, cases, w2ctx, w2ctx.context_sha256, T1, T2, archive, a.target_commitment, mode=mode, campaign=campaign, twelve_inputs=twelve_inputs, twelve_assets=tasset, expected_twelve_assets_sha256=tasset.sha256, twelve_assets_receipt=TWELVE_RECEIPT)
        R["timings"]["partial_seconds"] = round(time.time() - tt, 1); R["timings"]["seconds_per_pseudo"] = round((time.time() - tt) / max(1, n_rows), 3); mark("partial")
        G["G_partial_computed"] = bool(rec.family == fam and rec.mode == mode and len(rec.per_pseudo_status) == n_rows and rec.fingerprints["at_gate"] == rec.fingerprints["at_end"] and rec.gate.get("passed") is True and ((rec.rows == dict(start=rows[0], stop=rows[1], n_total=len(T1), n_rows=n_rows, global_sha256_T1=rec.rows["global_sha256_T1"], global_sha256_T2=rec.rows["global_sha256_T2"], slice_sha256_T1=rec.rows["slice_sha256_T1"], slice_sha256_T2=rec.rows["slice_sha256_T2"])) if subpartial else (rec.rows is None)))
        # R-D4C1-C: the live plan OBJECTS are the fixed dictionaries after the calibration as well (first-wave views, both systems; 12-position views, both systems) — the engine records the
        # same-object check before the gate / after the last pseudo (rec.plan_objects); the script re-checks against ITS fixed plan objects at the publication boundary
        same_after = all(v[0].plans is plans and v[1].plans is plans and v[0].fit_plans is fplans and v[1].fit_plans is fplans for v in cases.values()) and (twelve_inputs is None or all(p_.plans is plans and p_.fit_plans is fplans for pair in twelve_inputs["size_inputs"].values() for p_ in pair))
        G["G_plan_objects_stable"] = bool(same_after and rec.plan_objects.get("stable_after") is True and rec.plan_objects.get("first_wave_shared") is True and (twelve_inputs is None or rec.plan_objects.get("twelve_shares_first_wave") is True))
        R["plan_objects"] = dict(rec.plan_objects, script_views_same_objects_after=bool(same_after))
        R["partial"] = dict(partial_sha256=rec.binding["partial_sha256"], partial_file_sha256=rec.binding["partial_file_sha256"], partial_ref=rec.binding["partial_ref"], gate_mode=rec.gate.get("mode"), n_pseudo=len(rec.per_pseudo_status), archive_entries=archive.verify_all()["entries"],
                            eligibility_counts={lvl: {str(v): sum(1 for s in rec.per_pseudo_status if str(s["eligible_truths"][lvl]) == str(v)) for v in ("True", "False", "unknown", "technical_fail")} for lvl in ("support", "strong")}, expanded=sum(1 for s in rec.per_pseudo_status if s["expand_family"]), twelve_evaluated=sum(1 for s in rec.per_pseudo_status if s["twelve"] is not None))
        note("  partial:", json.dumps(R["partial"]["eligibility_counts"]), "expanded", R["partial"]["expanded"], "twelve evaluated", R["partial"]["twelve_evaluated"])
        pub = _publish_record(os.path.join(out, f"d4c1_{tag}_record.json"), rec.as_dict()); R["published_evidence"] = {f"d4c1_{tag}_record.json": pub}
        back = ser.loads(open(os.path.join(out, f"d4c1_{tag}_record.json"), encoding="utf-8").read()); _load = load_subpartial_record if subpartial else load_partial_record; arch_rec = _load(Archive(os.path.join(out, "archive")), rec.binding["partial_ref"])
        G["G_partial_published"] = bool(_strip_self(back, ("partial_file_sha256", "partial_ref")) == _strip_self(arch_rec, ("partial_file_sha256", "partial_ref")) and back["binding"]["partial_sha256"] == rec.binding["partial_sha256"] == arch_rec["binding"]["partial_sha256"])
        v = (verify_subpartial_record if subpartial else verify_partial_record)(back, Archive(os.path.join(out, "archive")), registered=registered, current_source_binding=True); G["G_partial_verified"] = bool(v["ok"] and v["registered_context_ok"] and v["family"] == fam and ((v.get("rows") == list(rows)) if subpartial else True)); R["partial"]["verification"] = v; mark("verify")
        tp = back["thresholds"]["pseudo"]; consumed = dict(sha256_T1=hashlib.sha256(np.ascontiguousarray(T1).tobytes()).hexdigest(), sha256_T2=hashlib.sha256(np.ascontiguousarray(T2).tobytes()).hexdigest())
        bound_consumed = tp["sha256_T1"] == consumed["sha256_T1"] and tp["sha256_T2"] == consumed["sha256_T2"]; bound_registered = tp["sha256_T1"] == idn["T1_sha256"] and tp["sha256_T2"] == idn["T2_sha256"] and tp["n"] == cols["n"]
        if subpartial:
            sl = dict(sha256_T1=hashlib.sha256(np.ascontiguousarray(T1[rows[0]:rows[1]]).tobytes()).hexdigest(), sha256_T2=hashlib.sha256(np.ascontiguousarray(T2[rows[0]:rows[1]]).tobytes()).hexdigest())
            bound_consumed = bound_consumed and tp["slice_sha256_T1"] == sl["sha256_T1"] and tp["slice_sha256_T2"] == sl["sha256_T2"] and tp["rows"] == list(rows) and tp["T1"] == [float(x) for x in T1[rows[0]:rows[1]]] and tp["T2"] == [float(x) for x in T2[rows[0]:rows[1]]]; consumed["slice"] = dict(sl, rows=list(rows))
        G["G_pseudo_identity_bound"] = bool(bound_consumed and (bound_registered or probe or not formal))
        R["pseudo_identity_bound"] = dict(record=dict(n=tp["n"], sha256_T1=tp["sha256_T1"], sha256_T2=tp["sha256_T2"], **({"rows": tp["rows"], "slice_sha256_T1": tp["slice_sha256_T1"], "slice_sha256_T2": tp["slice_sha256_T2"]} if subpartial else {})), consumed_arrays=consumed, registered=dict(T1_sha256=idn["T1_sha256"], T2_sha256=idn["T2_sha256"], n=cols["n"]), note="the columns actually consumed are re-hashed after the run and bound to the registered constants (not only the loader's success)")
        G["G_record_saved"] = True
        return finish(0 if all(G[kk] is True for kk in REQUIRED) else 1, "complete")
    except Exception as ex:
        R["failures"].append("exception: " + repr(ex)); R["traceback"] = traceback.format_exc(); note(R["traceback"]); return finish(1, "exception")


def _combine(a, out, R, G, note, mark, finish, reg, man, registered, campaign, cols, formal, Archive, ArchiveRef, merge_archives, load_partial_record, verify_partial_record, combine_family_partials, load_combined_sealed_record, publish_record, ser):
    dirs = {}
    for x in a.partial:
        f, p = x.split("=", 1); dirs[f] = os.path.realpath(p)
    if sorted(dirs) != sorted(FAMILIES): G["G_partials_loaded"] = False; R["failures"].append(f"--partial must give exactly {list(FAMILIES)}"); return finish(1, "inputs")
    recs = {}; runs = {}; ok = True
    for fam, d in dirs.items():
        rp = os.path.join(d, f"d4c1_partial_{fam}_record.json"); rr = os.path.join(d, f"d4c1_partial_{fam}_run.json"); ar = os.path.join(d, "archive")
        if not (os.path.isfile(rp) and os.path.isfile(rr) and os.path.isdir(ar)): R["failures"].append(f"{fam}: partial record / run record / archive missing in {d}"); ok = False; continue
        rec = ser.loads(open(rp, encoding="utf-8").read()); run = json.load(open(rr)); recs[fam] = rec; runs[fam] = dict(dir=d, record_sha256=sha(rp), run_sha256=sha(rr), attempt=run.get("attempt"), D4C1_PARTIAL_PASS=run.get("D4C1_PARTIAL_PASS"), probe=run.get("probe"), selftest=run.get("selftest"), source=run.get("source"), campaign_id=run.get("campaign_id"), target_commitment=run.get("target_commitment"))
        good = (run.get("D4C1_PARTIAL_PASS") is True and not run.get("selftest")) if formal else (run.get("stage") == "complete" and run.get("failures") == [] and run.get("selftest") is True and run.get("formal") is False and all((run.get("gates") or {}).get(k) is True for k in (run.get("required_inventory") or []) if k != "G_env_lock"))
        if not good or run.get("probe") or rec.get("family") != fam or run.get("family") != fam: R["failures"].append(f"{fam}: not a {'PASSed formal' if formal else 'complete self-test'} partial run of this family"); ok = False
        if run.get("campaign_id") != a.campaign_id or run.get("target_commitment") != a.target_commitment or rec["thresholds"]["target_commitment"] != a.target_commitment: R["failures"].append(f"{fam}: campaign / commitment differ from this combination"); ok = False
    G["G_partials_loaded"] = bool(ok); R["partials"] = runs
    if not ok: return finish(1, "inputs")
    archive = Archive(os.path.join(out, "archive"), deferred_index=True); merged = {}
    for fam in FAMILIES: merged[fam] = merge_archives(archive, Archive(os.path.join(dirs[fam], "archive")))
    archive.flush(); R["merge"] = merged; G["G_archives_merged"] = bool(all(m["source_entries"] > 0 for m in merged.values()) and archive.verify_all()["ok"]); mark("merge")
    if not G["G_archives_merged"]: R["failures"].append("archive merge"); return finish(1, "merge")
    ver = {}; ok = True
    for fam in FAMILIES:
        try:
            ar_rec = load_partial_record(archive, recs[fam]["binding"]["partial_ref"])
            if _strip_self(ar_rec, ("partial_file_sha256", "partial_ref")) != _strip_self(recs[fam], ("partial_file_sha256", "partial_ref")) or ar_rec["binding"]["partial_sha256"] != recs[fam]["binding"]["partial_sha256"]: raise RuntimeError("published partial record differs from its archived copy")
            ver[fam] = verify_partial_record(recs[fam], archive, registered=registered, current_source_binding=True); ok &= bool(ver[fam]["ok"] and ver[fam]["registered_context_ok"])
        except Exception as ex_: ver[fam] = dict(ok=False, error=repr(ex_)); ok = False
    G["G_partials_verified"] = bool(ok); R["partials_verification"] = ver; mark("verify_partials")
    if not ok: R["failures"].append("partial verification"); return finish(1, "verify_partials")
    tt = time.time(); rm = combine_family_partials(reg, man, [recs[f] for f in FAMILIES], archive, registered=registered, verify_references=True); R["timings"]["combine_seconds"] = round(time.time() - tt, 1); mark("combine")
    comb = rm.binding["combiner"]
    cols_ok = (rm.thresholds["pseudo"]["n"] == cols["n"] and rm.thresholds["pseudo"]["sha256_T1"] == cols["identity"]["T1_sha256"] and rm.thresholds["pseudo"]["sha256_T2"] == cols["identity"]["T2_sha256"]) if formal else (rm.thresholds["pseudo"]["T1"] == [float(v) for v in cols["T1"][:rm.thresholds["pseudo"]["n"]]])
    G["G_combined"] = bool(rm.mode == ("official" if formal else "smoke") and sorted(comb["partials"]) == sorted(FAMILIES) and all(comb["partials"][f]["partial_sha256"] == recs[f]["binding"]["partial_sha256"] for f in FAMILIES) and cols_ok and comb["campaign"]["id"] == campaign["id"] and comb["campaign"]["target_commitment"] == campaign["target_commitment"])
    R["sealed"] = dict(run_manifest_sha256=rm.binding["run_manifest_sha256"], run_manifest_file_sha256=rm.binding["run_manifest_file_sha256"], run_manifest_ref=rm.binding["run_manifest_ref"], branch_completeness=rm.branch_completeness,
                       calibration={lvl: {k: v for k, v in rm.calibration[lvl]["summary"].items() if k not in ("reason", "w2_context")} for lvl in ("support", "strong")}, full_procedure={lvl: rm.calibration[lvl]["full_procedure"] for lvl in ("support", "strong")}, scope="recorded as computed; usable is the registered Wilson comparison and is NOT an approval of the calibration (post-run audit / registration pending)")
    note("  combined:", json.dumps(R["sealed"]["calibration"]))
    pub = publish_record(os.path.join(out, "d4c1_sealed_calibration.json"), rm.as_dict()); R["published_evidence"] = {"d4c1_sealed_calibration.json": pub}
    back = ser.loads(open(os.path.join(out, "d4c1_sealed_calibration.json"), encoding="utf-8").read()); arch_rec = archive.get(ArchiveRef(**rm.binding["run_manifest_ref"]))
    G["G_sealed_published"] = bool(back["binding"]["run_manifest_sha256"] == rm.binding["run_manifest_sha256"] == arch_rec["binding"]["run_manifest_sha256"] and _strip_self(back, ("run_manifest_file_sha256", "run_manifest_ref")) == _strip_self(arch_rec, ("run_manifest_file_sha256", "run_manifest_ref")))
    try: d = load_combined_sealed_record(Archive(os.path.join(out, "archive")), rm.binding["run_manifest_ref"], registered=registered); G["G_sealed_loaded"] = bool(d["_verification"]["ok"] and d["_verification"]["registered_context_ok"] and d["_sha256"] == rm.binding["run_manifest_sha256"])
    except Exception as ex_: G["G_sealed_loaded"] = False; R["sealed_load_error"] = repr(ex_)
    mark("sealed_loaded"); G["G_record_saved"] = True
    return finish(0 if all(G[kk] is True for kk in (REQUIRED_COMBINE)) else 1, "complete")


def _combine_family(a, out, R, G, note, mark, finish, reg, man, registered, campaign, cols, formal, Archive, ArchiveRef, merge_archives, load_subpartial_record, verify_subpartial_record, combine_family_subpartials, load_partial_record, verify_partial_record, publish_record, ser):
    """D4C-2a: the sub-partial runs of ONE family -> merged archive -> every sub-partial re-read from its archive + verified -> combine_family_subpartials -> the family partial published
    under the family-partial file names (consumed unchanged by --mode combine)."""
    fam = a.family
    if fam not in FAMILIES or not a.subpartial: G["G_subpartials_loaded"] = False; R["failures"].append("--family and at least one --subpartial required"); return finish(1, "inputs")
    recs = []; runs = []; ok = True; all_pass = True
    for d in [os.path.realpath(p) for p in a.subpartial]:
        rp = [f for f in sorted(os.listdir(d)) if f.startswith(f"d4c1_subpartial_{fam}_r") and f.endswith("_record.json")] if os.path.isdir(d) else []
        rr = [f for f in sorted(os.listdir(d)) if f.startswith(f"d4c1_subpartial_{fam}_r") and f.endswith("_run.json")] if os.path.isdir(d) else []
        if len(rp) != 1 or len(rr) != 1 or not os.path.isdir(os.path.join(d, "archive")): R["failures"].append(f"{d}: exactly one sub-partial record / run record and an archive are required"); ok = False; continue
        rec = ser.loads(open(os.path.join(d, rp[0]), encoding="utf-8").read()); run = json.load(open(os.path.join(d, rr[0])))
        info = dict(dir=d, record=rp[0], record_sha256=sha(os.path.join(d, rp[0])), run_sha256=sha(os.path.join(d, rr[0])), attempt=run.get("attempt"), rows=run.get("row_range"), D4C1_SUBPARTIAL_PASS=run.get("D4C1_SUBPARTIAL_PASS"), probe=run.get("probe"), selftest=run.get("selftest"), source=run.get("source"), campaign_id=run.get("campaign_id"), target_commitment=run.get("target_commitment")); runs.append(info)
        good = (run.get("D4C1_SUBPARTIAL_PASS") is True and not run.get("selftest")) if formal else (run.get("stage") == "complete" and run.get("failures") == [] and run.get("selftest") is True and run.get("formal") is False and run.get("subpartial") is True and all((run.get("gates") or {}).get(k) is True for k in (run.get("required_inventory") or []) if k != "G_env_lock"))
        all_pass &= bool(run.get("D4C1_SUBPARTIAL_PASS") is True)
        if not good or run.get("probe") or rec.get("family") != fam or run.get("family") != fam or rec.get("kind") != "family_subpartial_calibration" or (rec.get("rows") or {}).get("start") != (run.get("row_range") or [None])[0] or (rec.get("rows") or {}).get("stop") != (run.get("row_range") or [None, None])[1]: R["failures"].append(f"{d}: not a {'PASSed formal' if formal else 'complete self-test'} sub-partial run of {fam}"); ok = False
        if run.get("campaign_id") != a.campaign_id or run.get("target_commitment") != a.target_commitment or rec["thresholds"]["target_commitment"] != a.target_commitment: R["failures"].append(f"{d}: campaign / commitment differ from this combination"); ok = False
        if run.get("source") and R.get("source") and (run["source"].get("inventory_sha256") != R["source"]["inventory_sha256"] or run["source"].get("script_sha256") != R["source"]["script_sha256"]): R["failures"].append(f"{d}: sub-partial run bound to another source / script"); ok = False
        recs.append(rec)
    G["G_subpartials_loaded"] = bool(ok and recs); R["subpartials"] = runs; R["subpartials_all_pass"] = bool(all_pass and formal)
    if not G["G_subpartials_loaded"]: return finish(1, "inputs")
    archive = Archive(os.path.join(out, "archive"), deferred_index=True); merged = []
    for info in runs: merged.append(dict(dir=info["dir"], **merge_archives(archive, Archive(os.path.join(info["dir"], "archive")))))
    archive.flush(); R["merge"] = merged; G["G_archives_merged"] = bool(all(m["source_entries"] > 0 for m in merged) and archive.verify_all()["ok"]); mark("merge")
    if not G["G_archives_merged"]: R["failures"].append("archive merge"); return finish(1, "merge")
    ver = []; ok = True
    for rec in recs:
        try:
            ar_rec = load_subpartial_record(archive, rec["binding"]["partial_ref"])
            if _strip_self(ar_rec, ("partial_file_sha256", "partial_ref")) != _strip_self(rec, ("partial_file_sha256", "partial_ref")) or ar_rec["binding"]["partial_sha256"] != rec["binding"]["partial_sha256"]: raise RuntimeError("published sub-partial record differs from its archived copy")
            v = verify_subpartial_record(rec, archive, registered=registered, current_source_binding=True); ver.append(v); ok &= bool(v["ok"] and v["registered_context_ok"] and v["family"] == fam)
        except Exception as ex_: ver.append(dict(ok=False, rows=(rec.get("rows") or {}).get("start"), error=repr(ex_))); ok = False
    G["G_subpartials_verified"] = bool(ok); R["subpartials_verification"] = ver; mark("verify_subpartials")
    if not ok: R["failures"].append("sub-partial verification"); return finish(1, "verify_subpartials")
    ranges = sorted((r["rows"]["start"], r["rows"]["stop"]) for r in recs); n = recs[0]["thresholds"]["pseudo"]["n"]; tiled = (ranges[0][0] == 0 and ranges[-1][1] == n and all(ranges[i][1] == ranges[i + 1][0] for i in range(len(ranges) - 1)) and len(set(ranges)) == len(ranges))
    G["G_rows_tiled"] = bool(tiled and (n == cols["n"] if formal else True)); R["rows"] = dict(n=n, ranges=[list(r) for r in ranges])
    if not G["G_rows_tiled"]: R["failures"].append(f"sub-partial ranges do not tile [0, {n}) exactly once: {ranges}"); return finish(1, "rows")
    tt = time.time(); rec = combine_family_subpartials(reg, man, recs, archive, registered=registered, verify_references=True); R["timings"]["combine_family_seconds"] = round(time.time() - tt, 1); mark("combine_family")
    prov = rec.binding["subpartials"]
    G["G_family_combined"] = bool(rec.family == fam and rec.mode == ("official" if formal else "smoke") and prov["ranges"] == [list(r) for r in ranges] and len(rec.per_pseudo_status) == n and all(p["partial_sha256"] == r["binding"]["partial_sha256"] for p, r in zip(prov["subpartials"], sorted(recs, key=lambda r: r["rows"]["start"]))) and rec.campaign["id"] == campaign["id"] and rec.campaign["target_commitment"] == campaign["target_commitment"])
    R["partial"] = dict(partial_sha256=rec.binding["partial_sha256"], partial_file_sha256=rec.binding["partial_file_sha256"], partial_ref=rec.binding["partial_ref"], gate_mode=rec.gate.get("mode"), n_pseudo=len(rec.per_pseudo_status), archive_entries=archive.verify_all()["entries"], subpartials=prov["ranges"],
                        eligibility_counts={lvl: {str(v): sum(1 for s_ in rec.per_pseudo_status if str(s_["eligible_truths"][lvl]) == str(v)) for v in ("True", "False", "unknown", "technical_fail")} for lvl in ("support", "strong")}, expanded=sum(1 for s_ in rec.per_pseudo_status if s_["expand_family"]), twelve_evaluated=sum(1 for s_ in rec.per_pseudo_status if s_["twelve"] is not None))
    note("  family partial from sub-partials:", json.dumps(R["partial"]["eligibility_counts"]), "expanded", R["partial"]["expanded"], "twelve evaluated", R["partial"]["twelve_evaluated"])
    pub = publish_record(os.path.join(out, f"d4c1_partial_{fam}_record.json"), rec.as_dict()); R["published_evidence"] = {f"d4c1_partial_{fam}_record.json": pub}
    back = ser.loads(open(os.path.join(out, f"d4c1_partial_{fam}_record.json"), encoding="utf-8").read()); arch_rec = load_partial_record(Archive(os.path.join(out, "archive")), rec.binding["partial_ref"])
    G["G_partial_published"] = bool(_strip_self(back, ("partial_file_sha256", "partial_ref")) == _strip_self(arch_rec, ("partial_file_sha256", "partial_ref")) and back["binding"]["partial_sha256"] == rec.binding["partial_sha256"] == arch_rec["binding"]["partial_sha256"])
    v = verify_partial_record(back, Archive(os.path.join(out, "archive")), registered=registered, current_source_binding=True); G["G_partial_verified"] = bool(v["ok"] and v["registered_context_ok"] and v["family"] == fam and v["n_pseudo"] == n); R["partial"]["verification"] = v; mark("verify")
    tp = back["thresholds"]["pseudo"]; idn = cols["identity"]
    G["G_pseudo_identity_bound"] = bool((tp["n"] == cols["n"] and tp["sha256_T1"] == idn["T1_sha256"] and tp["sha256_T2"] == idn["T2_sha256"]) if formal else (tp["T1"] == [float(x) for x in cols["T1"][:tp["n"]]] and tp["T2"] == [float(x) for x in cols["T2"][:tp["n"]]]))
    R["pseudo_identity_bound"] = dict(record=dict(n=tp["n"], sha256_T1=tp["sha256_T1"], sha256_T2=tp["sha256_T2"]), registered=dict(T1_sha256=idn["T1_sha256"], T2_sha256=idn["T2_sha256"], n=cols["n"]))
    G["G_record_saved"] = True
    return finish(0 if all(G[kk] is True for kk in REQUIRED_COMBINE_FAMILY) else 1, "complete")


def _screen(a, out, R, G, note, mark, finish, reg, man, fam, cases, w2ctx, cols, idn, rows, formal, publish_record, ser):
    """D4C-2a: the sufficient count-envelope screen of ONE non-E1 family over the registered pseudo rows (first-wave views only; registered W2 decisions)."""
    from step1_engine.infeasibility import envelope_screen_family, check_screen_record, blocking_rows_from_screen
    if fam == "E1": R["failures"].append("E1 is position-branch exempt: no screen"); G["G_row_range"] = False; return finish(1, "scope")
    T1, T2 = np.asarray(cols["T1"], np.float64), np.asarray(cols["T2"], np.float64); n = len(T1)
    if rows is not None and rows[1] > n: R["failures"].append("--row-range exceeds the registered columns"); G["G_row_range"] = False; return finish(1, "rows")
    sel = list(range(*rows)) if rows is not None else (list(range(n)) if formal else list(range(min(n, max(1, a.selftest_n))))); G["G_row_range"] = bool(sel and sel[-1] < n)
    dec = {k: w2ctx.decision_for(k, w2ctx.context_sha256) for k in cases}; campaign = dict(id=a.campaign_id + ("" if formal else "__SELFTEST"), screen=True, rows=[sel[0], sel[-1] + 1], formal=bool(formal))
    tt = time.time(); scr = envelope_screen_family(reg, man, fam, cases, dec, w2ctx.context_sha256, T1, T2, rows=sel, campaign=campaign, target_commitment=a.target_commitment); R["timings"]["screen_seconds"] = round(time.time() - tt, 1); R["timings"]["seconds_per_row"] = round((time.time() - tt) / max(1, len(sel)), 4); mark("screen")
    chk = check_screen_record(scr); G["G_screen_computed"] = bool(chk["ok"] and scr["family"] == fam and scr["rows"] == sel and scr["w2_context_sha256"] == w2ctx.context_sha256)
    R["screen"] = dict(n_rows=scr["n_rows"], n_blocking=scr["n_blocking"], w2_applicable=scr["w2_applicable"], w2={s_: dict(trigger=v["trigger"], validation_state=v["validation_state"]) for s_, v in scr["w2"].items()}, screen_sha256=scr["binding"]["screen_sha256"], rows=[sel[0], sel[-1] + 1],
                       ratio_bound_max={s_: max(x["sizes"][s_]["ratio_bound"] or float("inf") for x in scr["results"]) for s_ in scr["sizes"]}, stages_covered=sorted({st for x in scr["results"] for v in x["sizes"].values() for st in v["stages_covered"]}))
    note("  screen:", json.dumps(dict(n_rows=scr["n_rows"], n_blocking=scr["n_blocking"], w2_applicable=scr["w2_applicable"])))
    tag = f"screen_{fam}" + (f"_r{rows[0]:04d}_{rows[1]:04d}" if rows is not None else "")
    pub = publish_record(os.path.join(out, f"d4c1_{tag}_record.json"), scr); R["published_evidence"] = {f"d4c1_{tag}_record.json": pub}
    back = ser.loads(open(os.path.join(out, f"d4c1_{tag}_record.json"), encoding="utf-8").read()); G["G_screen_published"] = bool(check_screen_record(back)["ok"] and back["binding"]["screen_sha256"] == scr["binding"]["screen_sha256"] and len(blocking_rows_from_screen(back)) == scr["n_blocking"])
    G["G_pseudo_identity_bound"] = bool(back["pseudo"]["n"] == cols["n"] and back["pseudo"]["sha256_T1"] == idn["T1_sha256"] and back["pseudo"]["sha256_T2"] == idn["T2_sha256"]); R["pseudo_identity_bound"] = dict(record=back["pseudo"], registered=dict(T1_sha256=idn["T1_sha256"], T2_sha256=idn["T2_sha256"], n=cols["n"]))
    G["G_record_saved"] = True
    return finish(0 if all(G[kk] is True for kk in REQUIRED_SCREEN) else 1, "complete")


def _certificate(a, out, R, G, note, mark, finish, cols, formal, publish_record, ser):
    """D4C-2a: the fixed-denominator infeasibility certificate over verified screen records (+ evaluated statuses of published partial / sub-partial records)."""
    from step1_engine.infeasibility import check_screen_record, blocking_rows_from_screen, blocking_rows_from_statuses, infeasibility_certificate, check_certificate, registered_blocking_counts
    from step1_engine.rules_config import RULES
    idn = cols["identity"]; n = cols["n"]; maps = []; sources = []; ok = bool(a.screen or a.evaluated)
    for d in [os.path.realpath(p) for p in a.screen]:
        fs = [f for f in sorted(os.listdir(d)) if f.startswith("d4c1_screen_") and f.endswith("_record.json")] if os.path.isdir(d) else []; rr = [f for f in sorted(os.listdir(d)) if f.startswith("d4c1_screen_") and f.endswith("_run.json")] if os.path.isdir(d) else []
        if len(fs) != 1 or len(rr) != 1: R["failures"].append(f"{d}: exactly one screen record / run record required"); ok = False; continue
        scr = ser.loads(open(os.path.join(d, fs[0]), encoding="utf-8").read()); run = json.load(open(os.path.join(d, rr[0])))
        try: chk = check_screen_record(scr)
        except Exception as ex_: R["failures"].append(f"{d}: screen record not verified: {ex_!r}"); ok = False; continue
        good = (run.get("D4C1_SCREEN_COMPLETE") is True) if formal else (run.get("stage") == "complete" and run.get("failures") == [] and run.get("mode") == "screen")
        if not good or scr["pseudo"]["n"] != n or (formal and (scr["pseudo"]["sha256_T1"] != idn["T1_sha256"] or scr["pseudo"]["sha256_T2"] != idn["T2_sha256"])) or scr.get("target_commitment") != a.target_commitment or run.get("campaign_id") != a.campaign_id: R["failures"].append(f"{d}: screen run / columns / commitment / campaign do not match"); ok = False; continue
        maps.append(blocking_rows_from_screen(scr)); sources.append(dict(kind="screen", dir=d, file=fs[0], sha256=sha(os.path.join(d, fs[0])), screen_sha256=scr["binding"]["screen_sha256"], family=scr["family"], rows=[scr["rows"][0], scr["rows"][-1] + 1] if scr["rows"] else None, n_blocking=chk["n_blocking"]))
    for d in [os.path.realpath(p) for p in a.evaluated]:
        fs = [f for f in sorted(os.listdir(d)) if (f.startswith("d4c1_partial_") or f.startswith("d4c1_subpartial_")) and f.endswith("_record.json")] if os.path.isdir(d) else []; rr = [f for f in sorted(os.listdir(d)) if (f.startswith("d4c1_partial_") or f.startswith("d4c1_subpartial_")) and f.endswith("_run.json")] if os.path.isdir(d) else []
        if len(fs) != 1 or len(rr) != 1: R["failures"].append(f"{d}: exactly one partial / sub-partial record / run record required"); ok = False; continue
        rec = ser.loads(open(os.path.join(d, fs[0]), encoding="utf-8").read()); run = json.load(open(os.path.join(d, rr[0]))); ps = rec.get("thresholds", {}).get("pseudo", {})
        good = ((run.get("D4C1_PARTIAL_PASS") is True or run.get("D4C1_SUBPARTIAL_PASS") is True) and not run.get("selftest")) if formal else (run.get("stage") == "complete" and run.get("failures") == [])
        if not good or run.get("probe") or ps.get("n") != n or (formal and (ps.get("sha256_T1") != idn["T1_sha256"] or ps.get("sha256_T2") != idn["T2_sha256"])) or rec["thresholds"].get("target_commitment") != a.target_commitment or run.get("campaign_id") != a.campaign_id: R["failures"].append(f"{d}: evaluated run / columns / commitment / campaign do not match"); ok = False; continue
        start = (rec.get("rows") or {}).get("start", 0)
        maps.append(blocking_rows_from_statuses(rec["family"], rec["per_pseudo_status"], int(start), rec["binding"]["partial_sha256"])); sources.append(dict(kind="evaluated", dir=d, file=fs[0], sha256=sha(os.path.join(d, fs[0])), partial_sha256=rec["binding"]["partial_sha256"], family=rec["family"], rows=[start, start + len(rec["per_pseudo_status"])]))
    G["G_sources_loaded"] = bool(ok and maps); R["sources"] = sources
    if not G["G_sources_loaded"]: R["failures"].append("no verified sources"); return finish(1, "inputs")
    cert = infeasibility_certificate(n, maps, pseudo_identity=dict(n=n, sha256_T1=idn["T1_sha256"], sha256_T2=idn["T2_sha256"]), campaign=dict(id=a.campaign_id + ("" if formal else "__SELFTEST"), formal=bool(formal)), target_commitment=a.target_commitment, sources=sources); mark("certificate")
    chk = check_certificate(cert); G["G_certificate_computed"] = bool(chk["ok"] and cert["n"] == n and (n == RULES.n_pseudo if formal else True))
    R["certificate"] = dict(n=n, registered_blocking_counts=registered_blocking_counts(n), levels={lvl: {k: v for k, v in cert["levels"][lvl].items() if k != "statement"} for lvl in ("support", "strong")}, n_rows_proven=cert["n_rows_proven"], certificate_sha256=cert["binding"]["certificate_sha256"],
                            scope="algebraic fixed-denominator statement over proven rows; NOT a calibration, NOT usable == False, no claim on unevaluated rows")
    note("  certificate:", json.dumps({lvl: dict(proven=cert["levels"][lvl]["proven_blocking_rows"], first_blocking=cert["levels"][lvl]["first_blocking_count"], impossible=cert["levels"][lvl]["usable_true_impossible_by_wilson"]) for lvl in ("support", "strong")}))
    pub = publish_record(os.path.join(out, "d4c1_certificate_record.json"), cert); R["published_evidence"] = {"d4c1_certificate_record.json": pub}
    back = ser.loads(open(os.path.join(out, "d4c1_certificate_record.json"), encoding="utf-8").read()); G["G_certificate_published"] = bool(check_certificate(back)["ok"] and back["binding"]["certificate_sha256"] == cert["binding"]["certificate_sha256"])
    G["G_record_saved"] = True
    return finish(0 if all(G[kk] is True for kk in REQUIRED_CERTIFICATE) else 1, "complete")


def _selftest(a, out, R, G, note, mark, finish, ser, Archive, merge_archives, calibrate_family_partial, combine_family_partials, verify_partial_record, load_sealed_record, calibrate_sealed, commit_target, strip_provenance, InputContractError):
    """Synthetic four-family banks (tests/fixture32; no physical covariance): four partials (smoke gate) in separate archives -> merge -> combine -> single-process
    calibrate_sealed on the same inputs -> content equality; refusals (partial as sealed input; foreign commitment / pseudo order / missing family)."""
    sys.path.insert(0, os.path.join(a.phaseb, "tests")); os.environ.setdefault("AUDIT_WORKDIR", os.path.join(out, "fixture_cache")); os.makedirs(os.environ["AUDIT_WORKDIR"], exist_ok=True)
    from fixture32 import base, multifamily_trigger_only_pseudo, twelve_from_cases
    from step1_engine import twelve_assets as ta
    tt = time.time(); b = base(); mfx = multifamily_trigger_only_pseudo(b); t12 = twelve_from_cases(b["cases"]); reg, man, cases, ctx = mfx["reg"], mfx["man"], mfx["cases"], mfx["ctx"]; asset = ta.build_twelve_assets(reg, ["E7"])
    n = max(1, int(a.selftest_n)); xs = [80., 200., 150., 120., 90.][:n] + [100.] * max(0, n - 5); ys = [400., 1000., 700., 600., 450.][:n] + [500.] * max(0, n - 5)
    C = commit_target((200., 1000.), "selftest-nonce-not-a-secret-0001"); twelve_inputs = {"E7": t12}
    G["G_selftest_fixture"] = bool(sorted(reg.surviving) == list(FAMILIES) and len(cases) == 12 and ctx.validate()); R["selftest"] = dict(n=n, fixture_seconds=round(time.time() - tt, 1), commitment=C, families=list(reg.surviving)); mark("fixture")
    parts = {}; per = {}
    for fam in reg.surviving:
        tt = time.time(); ar = Archive(os.path.join(out, f"part_{fam}", "archive"), deferred_index=True); fc = {k: v for k, v in cases.items() if k.startswith(fam + "/")}
        p = calibrate_family_partial(reg, man, fam, fc, ctx, ctx.context_sha256, xs, ys, ar, C, mode="smoke", campaign=dict(id="selftest"), twelve_inputs=twelve_inputs.get(fam), twelve_assets=asset, expected_twelve_assets_sha256=asset.sha256)
        _publish_record(os.path.join(out, f"part_{fam}", f"d4c1_partial_{fam}_record.json"), p.as_dict()); parts[fam] = (p, ar); per[fam] = dict(seconds=round(time.time() - tt, 1), seconds_per_pseudo=round((time.time() - tt) / n, 2), peak_rss_mb=round(_peak_rss_mb(), 1), entries=ar.verify_all()["entries"], eligibility=[s["eligible_truths"] for s in p.per_pseudo_status])
        note(f"  partial {fam}: {per[fam]['seconds']}s, {per[fam]['entries']} archive entries")
    G["G_selftest_partials"] = bool(len(parts) == 4 and all(p.family == f and p.mode == "smoke" and len(p.per_pseudo_status) == n for f, (p, _) in parts.items())); R["selftest"]["partials"] = per; mark("partials")
    AC = Archive(os.path.join(out, "combined", "archive"), deferred_index=True); merged = {f: merge_archives(AC, ar) for f, (_, ar) in parts.items()}; AC.flush()
    ver = {f: verify_partial_record(p.as_dict(), AC) for f, (p, _) in parts.items()}
    G["G_selftest_merge"] = bool(AC.verify_all()["ok"] and all(v["ok"] for v in ver.values())); R["selftest"]["merge"] = merged; mark("merge")
    tt = time.time(); comb = combine_family_partials(reg, man, [p.as_dict() for p, _ in parts.values()], AC); R["selftest"]["combine_seconds"] = round(time.time() - tt, 1)
    _publish_record(os.path.join(out, "combined", "d4c1_sealed_calibration.json"), comb.as_dict())
    G["G_selftest_combined"] = bool(comb.branch_completeness["all_registered_families"] and sorted(comb.binding["combiner"]["partials"]) == list(FAMILIES)); mark("combine")
    tt = time.time(); A1 = Archive(os.path.join(out, "single", "archive"), deferred_index=True); single = calibrate_sealed(reg, man, cases, ctx, ctx.context_sha256, xs, ys, A1, C, twelve_inputs=twelve_inputs, twelve_assets=asset, expected_twelve_assets_sha256=asset.sha256, require_all_families=True); A1.flush()
    R["selftest"]["single_seconds"] = round(time.time() - tt, 1); G["G_selftest_single"] = bool(single.thresholds["target_commitment"] == C and len(single.per_pseudo_family_status) == n); mark("single")
    s1, s2 = ser.dumps(strip_provenance(single.as_dict())), ser.dumps(strip_provenance(comb.as_dict()))
    G["G_selftest_equivalence"] = bool(s1 == s2 and single.calibration == comb.calibration and single.per_pseudo_family_status == comb.per_pseudo_family_status and single.branch_completeness == comb.branch_completeness and sorted(single.archive_refs) == sorted(comb.archive_refs))
    R["selftest"]["equivalence"] = dict(content_equal=(s1 == s2), single_payload_sha256=single.binding["run_manifest_sha256"], combined_payload_sha256=comb.binding["run_manifest_sha256"], calibration=comb.calibration["support"]["summary"], note="payload SHAs differ only by binding.combiner (provenance); stripped content identical")
    ref = {}
    def refuse(name, fn):
        try: fn(); ref[name] = "ACCEPTED (BAD)"
        except InputContractError as ex: ref[name] = "refused: " + str(ex)[:120]
    refuse("partial_as_sealed_record", lambda: load_sealed_record(AC, parts["E7"][0].binding["partial_ref"]))
    refuse("missing_family", lambda: combine_family_partials(reg, man, [p.as_dict() for f, (p, _) in parts.items() if f != "E8"], AC, verify_references=False))
    refuse("duplicate_family", lambda: combine_family_partials(reg, man, [p.as_dict() for p, _ in parts.values()] + [parts["E2"][0].as_dict()], AC, verify_references=False))
    def other_commitment():
        d = ser.from_jsonable(ser.to_jsonable(parts["E1"][0].as_dict())); d["thresholds"]["target_commitment"] = "0" * 64; d["binding"]["partial_dependencies"]["target_commitment"] = "0" * 64
        from step1_engine.d4c1_partial import _payload_sha; d["binding"]["partial_sha256"] = _payload_sha(d)
        combine_family_partials(reg, man, [d] + [p.as_dict() for f, (p, _) in parts.items() if f != "E1"], AC, verify_references=False)
    refuse("other_commitment", other_commitment)
    def reordered_pseudo():
        d = ser.from_jsonable(ser.to_jsonable(parts["E2"][0].as_dict())); d["thresholds"]["pseudo"]["T1"] = d["thresholds"]["pseudo"]["T1"][::-1]; d["thresholds"]["pseudo"]["T2"] = d["thresholds"]["pseudo"]["T2"][::-1]
        combine_family_partials(reg, man, [d] + [p.as_dict() for f, (p, _) in parts.items() if f != "E2"], AC, verify_references=False)
    refuse("reordered_pseudo_columns", reordered_pseudo)
    G["G_selftest_refusals"] = bool(all(v.startswith("refused") for v in ref.values()) and len(ref) == 5); R["selftest"]["refusals"] = ref; mark("refusals")
    G["G_record_saved"] = True
    return finish(0 if all(G[k] is True for k in REQUIRED_SELFTEST) else 1, "complete")


if __name__ == "__main__": sys.exit(main())
