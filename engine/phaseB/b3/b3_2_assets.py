# -*- coding: utf-8 -*-
"""B-3-2 part A: registered 12-position assets (E2/E7/E8, source-bound registry; E2 at the formal 1e-4 lattice) + circle-geometry acceptance of the 9 new points per family x
surviving size with the FROZEN A7 procedure (script prefix executed against the pinned CMBtopology checkout; identical code to the 3 frozen anchors). Required gates: pins/inventory/script
binding, environment lock, frozen assets (A6/A7 SHA, A7 script SHA, CMBtopology commit), asset intake (regeneration) and SHA, geometry: first 3 points reproduce the frozen A7 primary rows
(d_clone, geometric/observational status) exactly, all 12 points carry the registered surviving observational status, prior 1/12; evidence: assets JSON (SHA), geometry CSV (SHA), run manifest.
No label; no covariance; B3_2A_PASS only in --profile assets_official."""
from __future__ import annotations
import argparse, csv, hashlib, io, contextlib, json, os, subprocess, sys, time, platform, traceback
import numpy as np

REQUIRED = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_env_lock", "G_assets_sha", "G_a7_script_sha", "G_cmbtopology_commit", "G_registry_source_bound", "G_twelve_assets_intake", "G_geometry_anchor_reproduction", "G_geometry_all_points_surviving", "G_prior_weights", "G_evidence_saved")


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mt", required=True); ap.add_argument("--phaseb", required=True); ap.add_argument("--out", required=True); ap.add_argument("--ct", required=True, help="pinned CMBtopology checkout"); ap.add_argument("--profile", default="assets_official")
    ap.add_argument("--selftest-no-env-lock", action="store_true"); ap.add_argument("--selftest-families", default=None, help="sandbox: comma list (e.g. E7,E8) to skip the formal E2 lattice; never issues PASS"); a = ap.parse_args(); t0 = time.time()
    if os.path.exists(a.out) and os.listdir(a.out): print("OUT must be a fresh (empty) directory", file=sys.stderr); return 2
    os.makedirs(a.out, exist_ok=True); log = open(os.path.join(a.out, "b3_2_assets_stdout.log"), "w"); G = {k: None for k in REQUIRED}; R = dict(stage="init", failures=[], timings={})
    def note(*s):
        m = " ".join(str(x) for x in s); print(m, flush=True)
        try: log.write(m + "\n"); log.flush()
        except ValueError: pass                                                                       # log already closed (finish); stdout keeps the message
    selftest = a.selftest_no_env_lock or a.selftest_families is not None
    def finish(code, stage="final"):
        R["stage"] = stage; R["gates"] = G; R["required_inventory"] = list(REQUIRED); R["required_all_true"] = all(G.get(k) is True for k in REQUIRED); R["B3_2A_PASS"] = bool(R["required_all_true"] and a.profile == "assets_official" and not selftest and code == 0); R["seconds"] = time.time() - t0
        note("B3_2A_PASS =", R["B3_2A_PASS"], "| stage:", stage, "| gates:", json.dumps(G)); log.close()
        R["output_inventory"] = {f: dict(sha256=sha(os.path.join(a.out, f)), bytes=os.path.getsize(os.path.join(a.out, f))) for f in sorted(os.listdir(a.out)) if f != "b3_2_assets_run_manifest.json" and os.path.isfile(os.path.join(a.out, f))}
        body = json.dumps(R, indent=1, ensure_ascii=False, default=str); tmp = os.path.join(a.out, "b3_2_assets_run_manifest.json.tmp"); open(tmp, "w").write(body); os.replace(tmp, os.path.join(a.out, "b3_2_assets_run_manifest.json")); print("run manifest written; B3_2A_PASS =", R["B3_2A_PASS"]); return code
    try:
        if a.profile != "assets_official": R["failures"].append("profile must be 'assets_official'"); return finish(1)
        sys.path.insert(0, a.phaseb); sys.path.insert(0, a.mt)
        pins_path = os.path.join(a.phaseb, "b3", "b3_2_pins.json"); pins = json.load(open(pins_path)); R["pins_sha256"] = sha(pins_path); inv = json.load(open(os.path.join(a.phaseb, "B2_completion_inventory.json")))
        G["G_pins_loaded"] = bool(pins.get("schema") == "b3_2_pins_v1" and "repo" not in pins and inv.get("b3_sha256", {}).get("b3/b3_2_pins.json") == R["pins_sha256"])
        from step1_engine import __version__; from step1_engine.checkpoint import module_shas; from step1_engine.official_gate import current_env, _blas_check
        ms = module_shas(); G["G_engine_inventory"] = (inv["modules"] == ms and inv["engine_version"] == __version__ == pins["engine_version"]); me = os.path.abspath(__file__); G["G_script_sha"] = (inv.get("b3_sha256", {}).get("b3/b3_2_assets.py") == sha(me)); R["engine_version"] = __version__
        if not (G["G_pins_loaded"] and G["G_engine_inventory"] and G["G_script_sha"]): R["failures"].append("preflight binding failed"); return finish(1, "preflight")
        env = current_env(); ex = pins["environment"]; vers_ok = all(env.get(k) == ex[k] for k in ("python", "numpy", "scipy", "healpy", "pot"))
        try:
            import camb; camb_ok = camb.__version__ == ex["camb"]
        except Exception: camb_ok = False
        G["G_env_lock"] = bool(vers_ok and camb_ok and bool(_blas_check(env.get("blas_threads")))); R["env"] = env
        if not G["G_env_lock"] and not a.selftest_no_env_lock: R["failures"].append("environment lock failed"); return finish(1, "environment")
        A = pins["assets"]; G["G_assets_sha"] = all(sha(os.path.join(a.mt, A[k])) == A[k + "_sha256"] for k in ("a5_bstack", "step0_bpm", "t1_engine", "t2b2_bridge"))
        a7 = pins["a7_script"]; a7p = os.path.join(a.mt, a7["path"]); G["G_a7_script_sha"] = (sha(a7p) == a7["sha256"])
        head = subprocess.run(["git", "-C", a.ct, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(); G["G_cmbtopology_commit"] = (head == a7["cmbtopology_commit"]); R["cmbtopology_head"] = head
        if not (G["G_assets_sha"] and G["G_a7_script_sha"] and G["G_cmbtopology_commit"]): R["failures"].append("frozen inputs mismatch"); return finish(1, "assets")
        # ---- registry (source-bound) and twelve assets
        from step1_engine.grid_registry import load_registry; from step1_engine.twelve_assets import build_twelve_assets
        A7 = os.path.join(a.phaseb, "tests/assets/a7_circle_geometry.csv"); A6 = os.path.join(a.phaseb, "tests/assets/a6_observer_design_points.json"); reg = load_registry(A7, A6); G["G_registry_source_bound"] = reg.verification_scope.startswith("constructed_from_verified_assets") or reg.verification_scope.startswith("source_bound"); R["registry_sha256"] = reg.registry_sha256
        fams = pins["twelve_assets"]["families"] if a.selftest_families is None else a.selftest_families.split(",")
        tt = time.time(); asset = build_twelve_assets(reg, families=fams); R["timings"]["twelve_assets_build_and_intake"] = time.time() - tt; G["G_twelve_assets_intake"] = bool(asset.verification.get("intake") == "regeneration-verified" and asset.verification.get("manifests") == 3 * len(fams))
        open(os.path.join(a.out, "b3_2_twelve_assets.json"), "w").write(json.dumps(asset.as_dict(), indent=1)); R["twelve_assets"] = dict(sha256=asset.sha256, families=fams, manifests={f: {s: m.sha256 for s, m in asset.manifests[f].items()} for f in fams}, generator=asset.generator)
        # ---- frozen A7 procedure as a prefix (pinned CMBtopology), applied to all 12 points of every surviving size
        src = open(a7p).read(); cut = src.find("rng0 = np.random.default_rng(0)\nfor fam in ['E1', 'E2', 'E7', 'E8']:"); assert cut > 0
        argv0 = sys.argv; sys.argv = ["a7", os.path.join(a.out, "a7_prefix_scratch"), a.ct]; ns = {}
        with contextlib.redirect_stdout(io.StringIO()): exec(compile(src[:cut], "a7_prefix", "exec"), ns)
        sys.argv = argv0; rng0 = np.random.default_rng(0); tt = time.time()
        frozen = [r for r in csv.DictReader(open(A7)) if r["is_primary_observer"] == "True"]; fz = {(r["family"], float(r["L"]), int(r["observer_id"])): r for r in frozen}
        anchor_ok, all_surv, prior_ok, rows_out = True, True, True, []
        for fam in fams:
            for s in reg.surviving[fam]:
                L = reg.status[fam][s]["L"]; fd = ns["family_data"](fam, L); man = asset.get(fam, s); ns["rows"] = []
                for j, q in enumerate(man.points):
                    r = ns["lift"](fam, q, fd, rng0); ns["add_row"](fam, L, fd, "observer12", j, r, q, True, "twelve_v1")
                for j, row in enumerate(ns["rows"]):
                    row = dict(row); row["size_id"] = s; row["point_index"] = j; row["is_frozen_anchor"] = j < 3; row["prior_weight"] = man.weights[j]; rows_out.append(row)
                    if j < 3:
                        f = fz[(fam, L, j + 1)]; same = (abs(float(f["d_clone"]) - float(row["d_clone"])) < 1e-12 and f["observational_status"] == row["observational_status"] and f["geometric_status"] == row["geometric_status"] and json.loads(f["reduced_coords"]) == man.points[j])
                        if not same: R.setdefault("anchor_mismatches", []).append(dict(family=fam, size=s, j=j, frozen=dict(d=f["d_clone"], obs=f["observational_status"], geo=f["geometric_status"], q=f["reduced_coords"]), new=dict(d=row["d_clone"], obs=row["observational_status"], geo=row["geometric_status"], q=man.points[j])))
                        anchor_ok &= same
                    all_surv &= (row["observational_status"] == "no_nondegenerate_circles"); prior_ok &= abs(man.weights[j] - 1 / 12) < 1e-15
        R["timings"]["geometry"] = time.time() - tt
        keys = ["family", "size_id", "L", "point_index", "is_frozen_anchor", "observer_id", "reduced_coords", "r_obs_LLSS", "d_clone", "d_clone_proper", "d_clone_improper", "nearest_coset", "nearest_element_type", "nearest_alpha_deg", "nearest_theta_deg", "n_candidates_d_lt_1", "exclusion_witness_exists", "geometric_status", "observational_status", "prior_weight", "shape"]
        with open(os.path.join(a.out, "b3_2_twelve_geometry.csv"), "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys); w.writeheader()
            for row in rows_out: w.writerow({k: (json.dumps(row[k]) if isinstance(row[k], (list, dict)) else row[k]) for k in keys})
        G["G_geometry_anchor_reproduction"] = bool(anchor_ok); G["G_geometry_all_points_surviving"] = bool(all_surv); G["G_prior_weights"] = bool(prior_ok)
        R["geometry_summary"] = {f: {s: dict(n=sum(1 for r in rows_out if r["family"] == f and r["size_id"] == s), statuses=sorted({r["observational_status"] for r in rows_out if r["family"] == f and r["size_id"] == s}), min_d_clone=min(r["d_clone"] for r in rows_out if r["family"] == f and r["size_id"] == s)) for s in reg.surviving[f]} for f in fams}
        G["G_evidence_saved"] = all(os.path.exists(os.path.join(a.out, f)) for f in ("b3_2_twelve_assets.json", "b3_2_twelve_geometry.csv")); R["module_sha256"] = ms
        return finish(0 if all(G[k] is True for k in REQUIRED) else 1, "complete")
    except Exception as ex:
        R["failures"].append("exception: " + repr(ex)); R["traceback"] = traceback.format_exc(); note(R["traceback"]); return finish(1, "exception")


if __name__ == "__main__": sys.exit(main())
