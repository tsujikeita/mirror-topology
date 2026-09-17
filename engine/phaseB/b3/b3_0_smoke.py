# -*- coding: utf-8 -*-
"""B-3-0 smoke v0.3 (pre-execution audits v0.1 R1–R6, v0.2 R02-A/B/C). Registered definitions: matched = model D C_CT D vs reference diag(CVEC); native = model C_CT vs reference diag(c_l,CT expanded).
One generation call per purpose with FOUR roles [S_M, S_I(matched ref), S_N, S_ref(native)] so model and reference share the same latent (R, z) (rules §6.3); fitting purpose likewise;
the isotropic calibration bank for T19 is a separate purpose (never reused as an evaluation reference). Required gates are an exact inventory of bools; the environment lock (live
versions + NumPy-owned OpenBLAS=2 + other pools <= 2) is checked before any generation; --profile accepts only 'smoke'; execution_profile is a machine-readable record;
a healthy smoke requires technical_status == 'ok' (precision-unresolved allowed; numeric TECH is a failure). Evidence: every bank (T1/T2/AX/PL/cid/UIDs), generation calls,
T10 hit tables / plan / both algorithms' outputs, FamilyResult via the checkpoint writer (read back), pins, full logs, run manifest with SHA inventory. Non-zero exit on any failure."""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time, platform, traceback
import numpy as np

REQUIRED = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_env_lock", "G_assets_sha", "G_cov_manifest_binding", "G_cov_array_sha", "G_sqrt_hard", "G_roles_shared_latent", "G_finite_banks",
            "G_iso_engine_matches_A5_null", "G_T10_stratified_equals_literal", "G_T10_prefix_extension_contrast", "G_evaluation_ok", "G_checkpoint_roundtrip", "G_evidence_saved")


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def asha(a): return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mt", required=True); ap.add_argument("--phaseb", required=True); ap.add_argument("--out", required=True); ap.add_argument("--pins", default=None)
    ap.add_argument("--profile", default="smoke"); ap.add_argument("--selftest-no-env-lock", action="store_true", help="sandbox self-test: records G_env_lock=False and never issues B3_0_PASS")
    ap.add_argument("--unbound-pins-test-scope", action="store_true", help="allow a pins file that is not bound to the inventory (test scope only; never issues B3_0_PASS)")
    a = ap.parse_args(); t0 = time.time()
    if os.path.exists(a.out) and os.listdir(a.out): print("OUT must be a fresh (empty) directory", file=sys.stderr); return 2
    os.makedirs(a.out, exist_ok=True); log = open(os.path.join(a.out, "b3_0_smoke_stdout.log"), "w"); G = {k: None for k in REQUIRED}; R = dict(stage="init", failures=[]); rec = {}
    def note(*s): m = " ".join(str(x) for x in s); print(m); log.write(m + "\n"); log.flush()
    def _jsonable(o):
        try:
            from step1_engine import serialization as ser; return ser.to_jsonable(o)
        except Exception:                                                                                    # early failure before the engine is importable: stdlib-only record
            def conv(x):
                if isinstance(x, dict): return {str(k): conv(v) for k, v in x.items()}
                if isinstance(x, (list, tuple)): return [conv(v) for v in x]
                if isinstance(x, float) and (x != x or x in (float("inf"), float("-inf"))): return str(x)
                if hasattr(x, "tolist"): return conv(x.tolist())
                return x if isinstance(x, (str, int, float, bool)) or x is None else repr(x)
            return conv(o)
    def finish(code, stage="final"):
        R["stage"] = stage; R["gates"] = G; R["required_inventory"] = list(REQUIRED); R["required_all_true"] = all(G.get(k) is True for k in REQUIRED)
        R["B3_0_PASS"] = bool(R["required_all_true"] and a.profile == "smoke" and not a.selftest_no_env_lock and not a.unbound_pins_test_scope and code == 0); R["seconds"] = time.time() - t0
        note("B3_0_PASS =", R["B3_0_PASS"], "| stage:", stage, "| gates:", json.dumps(G)); log.close()          # the log is CLOSED before it is hashed; nothing is appended afterwards
        R["output_inventory"] = {f: dict(sha256=sha(os.path.join(a.out, f)), bytes=os.path.getsize(os.path.join(a.out, f))) for f in sorted(os.listdir(a.out)) if f != "b3_0_run_manifest.json"}
        body = json.dumps(_jsonable(R), indent=1, ensure_ascii=False); tmp = os.path.join(a.out, "b3_0_run_manifest.json.tmp")
        with open(tmp, "w") as fh: fh.write(body); fh.flush(); os.fsync(fh.fileno())
        os.replace(tmp, os.path.join(a.out, "b3_0_run_manifest.json")); print("run manifest written; B3_0_PASS =", R["B3_0_PASS"]); return code
    try:
        if a.profile != "smoke": R["failures"].append("profile must be 'smoke' (B-3-0 is smoke-only)"); return finish(1)
        sys.path.insert(0, a.phaseb); sys.path.insert(0, a.mt)
        pins_path = a.pins or os.path.join(a.phaseb, "b3", "b3_0_pins.json"); pins = json.load(open(pins_path)); R["pins"] = pins; R["pins_sha256"] = sha(pins_path)
        inv0 = json.load(open(os.path.join(a.phaseb, "B2_completion_inventory.json"))); pins_bound = inv0.get("b3_sha256", {}).get("b3/b3_0_pins.json") == R["pins_sha256"]
        if not pins_bound and not a.unbound_pins_test_scope: R["failures"].append("pins file is not the inventory-bound science pins (use --unbound-pins-test-scope for experiments; never a formal run)"); G["G_pins_loaded"] = False; return finish(1, "preflight")
        G["G_pins_loaded"] = bool(pins.get("schema") == "b3_0_pins_v1" and "repo" not in pins and pins_bound); R["pins_binding"] = "inventory-bound" if pins_bound else "UNBOUND test scope"
        R["execution_profile"] = dict(dict(pins["smoke_profile"]), kind="test", mode="smoke", statistics_scope="single configuration, both systems, N0 only; diagnostics; no label")
        from step1_engine import __version__; from step1_engine.checkpoint import module_shas, write_family_result, read_family_result; from step1_engine.official_gate import current_env, _blas_check
        inv = json.load(open(os.path.join(a.phaseb, "B2_completion_inventory.json"))); ms = module_shas()
        G["G_engine_inventory"] = (inv["modules"] == ms and inv["engine_version"] == __version__ == pins["engine_version"]); R["engine_version"] = __version__; R["inventory_sha256"] = sha(os.path.join(a.phaseb, "B2_completion_inventory.json"))
        me = os.path.abspath(__file__); G["G_script_sha"] = (inv.get("b3_sha256", {}).get("b3/b3_0_smoke.py") == sha(me)); R["script_sha256"] = sha(me)
        if not (G["G_pins_loaded"] and G["G_engine_inventory"] and G["G_script_sha"]): R["failures"].append("preflight: pins/inventory/script binding failed"); return finish(1, "preflight")
        # ---- environment lock BEFORE any generation
        env = current_env(); R["env"] = env; R["platform"] = platform.platform(); ex = pins["environment"]; vers_ok = all(env.get(k) == ex[k] for k in ("python", "numpy", "scipy", "healpy", "pot"))
        try:
            import camb; camb_ok = camb.__version__ == ex["camb"]; env["camb"] = camb.__version__
        except Exception: camb_ok = False; env["camb"] = None
        blas_ok = bool(_blas_check(env.get("blas_threads"))); R["blas_check"] = dict(ok=blas_ok, pools=env.get("blas_threads")); G["G_env_lock"] = bool(vers_ok and camb_ok and blas_ok)
        if not G["G_env_lock"] and not a.selftest_no_env_lock: R["failures"].append(f"environment lock failed: versions_ok={vers_ok} camb_ok={camb_ok} blas_ok={blas_ok}"); return finish(1, "environment")
        # ---- assets pinned
        A = pins["assets"]; asset_ok = all(sha(os.path.join(a.mt, A[k])) == A[k + "_sha256"] for k in ("a5_bstack", "step0_bpm", "t1_engine", "t2b2_bridge")); G["G_assets_sha"] = asset_ok
        if not asset_ok: R["failures"].append("frozen asset SHA mismatch"); return finish(1, "assets")
        from step1_engine.legacy_kernel import LegacyKernel, GEN_NS, LBLK; k = LegacyKernel(a.mt)
        t1, t2 = float(pins["target"]["T1_obs"]), float(pins["target"]["T2_obs"]); R["target_used"] = [t1, t2]; tg = pins["target"]
        if tg.get("step0_csv"):                                                                            # source check of the target against the SHA-verified Step0 unique row (recorded scope)
            import csv as _csv; p0 = os.path.join(a.mt, tg["step0_csv"]); ok0 = sha(p0) == tg["step0_csv_sha256"]; rows = list(_csv.DictReader(open(p0))); pr3 = [r for r in rows if r.get("map") == "PR3_Commander"]
            hit = len(pr3) == 1 and abs(float(pr3[0]["Splus"]) - t1) < 1e-12 and abs(float(pr3[0]["Sminus"]) - t2) < 1e-12; R["target_source_check"] = dict(step0_sha_ok=ok0, rows=len(rows), pr3_commander_rows=len(pr3), target_equals_unique_row=bool(hit), scope="registered value compared with the SHA-verified Step0 v0.7 unique PR3_Commander row (Splus, Sminus)")
            if not (ok0 and hit): R["failures"].append("target does not match the SHA-verified Step0 unique row"); return finish(1, "target")
        else: R["target_source_check"] = dict(scope="registered value transcribed from rules draft4.1 §2.1; Step0 CSV not read")
        # ---- mock covariance pinned (manifest/file/array SHA)
        mc = pins["mock_cov"]; mp = os.path.join(a.mt, mc["manifest"]); npy = os.path.join(a.mt, mc["npy"]); man = json.load(open(mp))
        from step1_engine.grid_manifest import verify_cov_manifest, ConfigurationSpec, cache_key
        spec = ConfigurationSpec(0, mc["topology"], "mock", 1.0, 0, 1, mc["params"], [], [-v for v in mc["x0"]], mc["x0"], cache_key(mc["topology"], mc["params"], mc["x0"]), dict(observational_status="mock", geometric_status="mock"), 1.0)
        cb = verify_cov_manifest(spec, man, npy); G["G_cov_manifest_binding"] = bool(cb["bound"] and cb["file_sha_verified"] and sha(mp) == mc["manifest_sha256"] and man["cov_file_sha256"] == mc["cov_file_sha256"] and man["cov_array_sha256"] == mc["cov_array_sha256"])
        import t1_engine as te; Mx, C_real, meta = te.load_cov_full(npy)
        if "cov_array_sha256" not in meta: R["failures"].append("loader did not return cov_array_sha256"); G["G_cov_array_sha"] = False; return finish(1)
        G["G_cov_array_sha"] = (meta["cov_array_sha256"] == mc["cov_array_sha256"])
        # ---- roots: matched model, matched ref (PR3 iso), native model, native ref (CT block power)
        C_M, c_ct = k.matched(C_real); C_ref_native = np.diag(np.concatenate([np.repeat(c_ct[i], 2 * l + 1) for i, (b, l) in enumerate(LBLK)]))
        S_M, iM = k.psqrt(C_M); S_I, iI = k.psqrt(k.C_ISO); S_N, iN = k.psqrt(C_real); S_RN, iRN = k.psqrt(C_ref_native)
        G["G_sqrt_hard"] = all(v["clip"] == 0 and v["lambda_min"] > 0 and v["sym"] < 1e-12 and v["recon"] < 1e-10 for v in (iM, iI, iN, iRN)); R["sqrt"] = dict(matched=iM, matched_ref=iI, native=iN, native_ref=iRN, c_ct=c_ct.tolist(), pr3=k.c_pr3.tolist())
        if not (G["G_cov_manifest_binding"] and G["G_cov_array_sha"] and G["G_sqrt_hard"]): R["failures"].append("frozen input / root gates failed before generation"); return finish(1, "roots")
        ROLES = ["model_matched", "ref_matched", "model_native", "ref_native"]; roots = [S_M, S_I, S_N, S_RN]
        P = pins["smoke_profile"]; N, m, B, Nfit, Bkde = P["N"], P["m"], P["B"], P["Nfit"], P["Bkde"]; K = N // m; Kf = Nfit // m
        # ---- ONE generation call per purpose with four roles (shared latent); extension = batch 1 of the same purpose (stream id 1)
        ev, cid, _ = k.generate(N, m, (GEN_NS["m_sensitivity"], 0), roots, ("float64",)); ext, cide, _ = k.generate(3 * N, m, (GEN_NS["m_sensitivity"], 1), roots, ("float64",))
        fit, cidf, _ = k.generate(Nfit, m, (GEN_NS["pseudo"], 7), roots, ("float64",)); iso, cidi, _ = k.generate(N, m, (GEN_NS["calibration"], 0), [S_I], ("float64",))
        R["generation_calls"] = k.calls; R["roles"] = {r: i for i, r in enumerate(ROLES)}
        banks = {f"eval_{r}": ev[(i, "float64")] for i, r in enumerate(ROLES)} | {f"ext_{r}": ext[(i, "float64")] for i, r in enumerate(ROLES)} | {f"fit_{r}": fit[(i, "float64")] for i, r in enumerate(ROLES)} | {"iso_calibration": iso[(0, "float64")]}
        G["G_finite_banks"] = all(np.isfinite(d[key]).all() for d in banks.values() for key in ("T1", "T2"))
        # shared-latent witness: the same (R, z) drives all four roles -> the isotropic-scaling contrast: model_native vs ref_native differ only by the root
        expected_calls = [dict(ids=[GEN_NS["m_sensitivity"], 0], N=N, m=m, systems=4), dict(ids=[GEN_NS["m_sensitivity"], 1], N=3 * N, m=m, systems=4), dict(ids=[GEN_NS["pseudo"], 7], N=Nfit, m=m, systems=4), dict(ids=[GEN_NS["calibration"], 0], N=N, m=m, systems=1)]
        G["G_roles_shared_latent"] = bool(k.calls == expected_calls); R["expected_generation_calls"] = expected_calls
        np.savez_compressed(os.path.join(a.out, "b3_0_banks.npz"), **{f"{n}_{key}": d[key] for n, d in banks.items() for key in ("T1", "T2", "AX", "PL")}, cid_eval=cid, cid_ext=cide, cid_fit=cidf, cid_iso=cidi)
        # ---- T19 vs frozen A5 reference (pinned values + provenance SHA)
        A5 = pins["a5_reference"]; G_prov = sha(os.path.join(a.mt, A5["source"])) == A5["provenance_sha256"]; dI = banks["iso_calibration"]
        med1, med2 = float(np.median(dI["T1"])), float(np.median(dI["T2"])); p1 = float(np.mean(dI["T1"] <= t1)); pB = float(np.mean((dI["T1"] <= t1) & (dI["T2"] <= t2)))
        chk = dict(T1_med=A5["T1_med_CI"][0] <= med1 <= A5["T1_med_CI"][1], T2_med=A5["T2_med_CI"][0] <= med2 <= A5["T2_med_CI"][1], P_T1=A5["P_T1_le_obs_wilson"][0] <= p1 <= A5["P_T1_le_obs_wilson"][1], P_EB=A5["P_eventB_wilson"][0] <= pB <= A5["P_eventB_wilson"][1])
        R["T19"] = dict(T1_median=med1, T2_median=med2, P_T1_le_obs=p1, P_eventB=pB, n=int(N), checks=chk, provenance_sha_ok=G_prov); G["G_iso_engine_matches_A5_null"] = bool(G_prov and all(chk.values()))
        # ---- T10: paired plan, prefix-only point vs prefix+extension point, model/reference, stratified vs literal (bit), weights & denominators recorded
        from step1_engine.bootstrap_plan import BootstrapPlan, FittingPlan, HitTable, resample_hits, literal_resample_hits, bank_sha256, stratum_weights_from_tables
        from step1_engine.types import ClusterUID; from step1_engine.plan_io import write_plans
        uids0 = [ClusterUID(1, 200, 1, 0, i) for i in range(K)]; uids1 = [ClusterUID(1, 200, 1, 1, i) for i in range(3 * K)]; plan = BootstrapPlan.build("b30-s0", 0, {0: uids0, 1: uids1}, B, 20260912)
        def hits(d, n): return ((d["T1"] <= t1) & (d["T2"] <= t2)).reshape(n, m).sum(1).astype(np.int64)
        t10 = {}; ok_all = True
        for role in ("model_matched", "ref_matched"):
            h0, h1 = hits(banks[f"eval_{role}"], K), hits(banks[f"ext_{role}"], 3 * K); tabA = {0: HitTable(uids0, h0, N, m)}; tabB = {0: HitTable(uids0, h0, N, m), 1: HitTable(uids1, h1, 3 * N, m)}
            PA, sA = resample_hits(plan, tabA); PAl, sAl = literal_resample_hits(plan, tabA); PB, sB = resample_hits(plan, tabB); PBl, sBl = literal_resample_hits(plan, tabB)
            eq = np.array_equal(sA[0], sAl[0]) and np.array_equal(sB[0], sBl[0]) and np.array_equal(sB[1], sBl[1]) and np.allclose(PA, PAl, rtol=0, atol=1e-15) and np.allclose(PB, PBl, rtol=0, atol=1e-15) and np.array_equal(sA[0], sB[0])
            ok_all &= eq; t10[role] = dict(hits_prefix=int(h0.sum()), hits_ext=int(h1.sum()), weights_prefix_only=stratum_weights_from_tables(tabA), weights_prefix_ext=stratum_weights_from_tables(tabB), denominators=dict(N0=N, N4=4 * N), shared_prefix_sums_identical=bool(np.array_equal(sA[0], sB[0])), stratified_equals_literal=bool(eq))
            np.savez_compressed(os.path.join(a.out, f"b3_0_T10_{role}.npz"), hits_prefix=h0, hits_ext=h1, P_prefix_only=PA, P_prefix_ext=PB, sums_prefix=sA[0], sums_ext=sB[1], P_prefix_only_literal=PAl, P_prefix_ext_literal=PBl)
        G["G_T10_stratified_equals_literal"] = bool(ok_all); G["G_T10_prefix_extension_contrast"] = bool(all(v["shared_prefix_sums_identical"] for v in t10.values())); R["T10"] = t10
        plans = {s: BootstrapPlan.build(f"b30-s{s}", s, {0: uids0}, B, 20260912) for s in range(5)}; fplans = {s: FittingPlan.build(f"b30-fit{s}", 1, 1, s, Kf, Bkde, 20260913) for s in range(5)}
        write_plans(dict(T10_plan=plan, **{f"eval_s{s}": p for s, p in plans.items()}, **{f"fit_s{s}": p for s, p in fplans.items()}), os.path.join(a.out, "b3_0_plans.json"))
        # ---- evaluation: single-configuration family (weight 1); matched (model D C D vs diag CVEC) + native (model C vs diag c_ct)
        from step1_engine.orchestrator import ConfigBank, FittingBank, FamilyInput, evaluate_family
        def fb(mr, rr): return FittingBank(np.c_[banks[f"fit_{mr}"]["T1"], banks[f"fit_{mr}"]["T2"]], np.c_[banks[f"fit_{rr}"]["T1"], banks[f"fit_{rr}"]["T2"]], cidf)
        fbM, fbN = fb("model_matched", "ref_matched"), fb("model_native", "ref_native"); em, en = banks["eval_model_matched"], banks["eval_ref_matched"]; nm, nr = banks["eval_model_native"], banks["eval_ref_native"]
        cfgM = ConfigBank(100, "E7", "matched", 1.0, em["T1"], em["T2"], en["T1"], en["T2"], uids0, m, {0: (0, N)}); cfgN = ConfigBank(50100, "E7", "native", 1.0, nm["T1"], nm["T2"], nr["T1"], nr["T2"], uids0, m, {0: (0, N)})
        famM = FamilyInput("E7", [cfgM], plans, {100: fbM}, fplans, True, {100: bank_sha256(fbM.X_model, fbM.X_ref, fbM.cid)}); famN = FamilyInput("E7", [cfgN], plans, {50100: fbN}, fplans, True, {50100: bank_sha256(fbN.X_model, fbN.X_ref, fbN.cid)})
        r = evaluate_family(famM, famN, t1, t2); rr = r.as_dict()
        G["G_evaluation_ok"] = bool(r.decision["technical_status"] == "ok"); R["mock_eval"] = dict(Q_point=r.Q_point, precision=r.precision["state"], native_Q=(r.native or {}).get("Q_point"), native_precision=((r.native or {}).get("precision") or {}).get("state"), logD_point=(r.logD or {}).get("point"), label=r.decision["display_label"], technical_status=r.decision["technical_status"], truths=r.truths, note="diagnostic only (mock covariance, one configuration); precision-unresolved is acceptable at smoke N; numeric TECH is a smoke failure")
        cp = os.path.join(a.out, "b3_0_mock_family_result.json"); csha = write_family_result(r, cp, extra=dict(b3_0="smoke diagnostic (not a gated formal run)")); back = read_family_result(cp, csha); G["G_checkpoint_roundtrip"] = bool(str(back.get("verified", "")).startswith("verified"))
        G["G_evidence_saved"] = all(os.path.exists(os.path.join(a.out, f)) for f in ("b3_0_banks.npz", "b3_0_plans.json", "b3_0_T10_model_matched.npz", "b3_0_T10_ref_matched.npz", "b3_0_mock_family_result.json")); R["module_sha256"] = ms
        return finish(0 if all(G[k] is True for k in REQUIRED) else 1, "complete")
    except Exception as ex:
        R["failures"].append("exception: " + repr(ex)); R["traceback"] = traceback.format_exc(); note(R["traceback"]); return finish(1, "exception")


if __name__ == "__main__": sys.exit(main())
