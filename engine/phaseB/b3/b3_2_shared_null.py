# -*- coding: utf-8 -*-
"""B-3-2 part B v0.2 (audit R321-A/B/C): registered-scale shared W2 null asset (rules §10.1). TWO separately generated banks: the CALIBRATION bank (calibration purpose, stream 0,
N_cal=2e5, both selections) supplies the whitening (mu, W = L^-1 from f64) and the A10 official cross-check ONLY; the NULL POOL (w2_isotropic purpose, stream 0, N_null=6e5, 6000 clusters,
both selections) is the registered isotropic pool, whitened with the calibration mu/W on both paths. Exact POT W2; n_sub 2000/5000; B_max=1000; resumable via digest-bound checkpoints
(w2_shared_build v2: identity incl. whitening/provenance, payload digests, recomputed coupling bounds, pre-run bank snapshot). Required gates (exact inventory): binding, environment lock,
frozen assets, calibration == A10 official checkpoint (T1 AND T2 relative < 1e-9 on all compared rows, plane 100%, cid/rows/shape identical; failure stops BEFORE whitening and OT),
whitening, distance registered, pool inventory (N_cal=2e5, N_null=6e5, K=6000, m=100, both paths, distinct purposes), asset validate, evidence. B3_2B_PASS only in --profile assets_official."""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time, platform, traceback
import numpy as np

REQUIRED = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_env_lock", "G_assets_sha", "G_calibration_bank_matches_a10", "G_pool_inventory", "G_whitening", "G_distance_registered", "G_shared_null_valid", "G_evidence_saved")


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def asha(a): return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mt", required=True); ap.add_argument("--phaseb", required=True); ap.add_argument("--out", required=True); ap.add_argument("--profile", default="assets_official")
    ap.add_argument("--selftest-no-env-lock", action="store_true"); ap.add_argument("--selftest-cheap-distance", action="store_true", help="sandbox: test-only distance instead of POT (never issues PASS)"); ap.add_argument("--selftest-scale", type=float, default=1.0)
    a = ap.parse_args(); t0 = time.time(); os.makedirs(a.out, exist_ok=True)
    log = open(os.path.join(a.out, "b3_2_shared_null_stdout.log"), "a"); G = {k: None for k in REQUIRED}; R = dict(stage="init", failures=[], timings={})
    def note(*s):
        m = " ".join(str(x) for x in s); print(m, flush=True)
        try: log.write(m + "\n"); log.flush()
        except ValueError: pass
    selftest = a.selftest_no_env_lock or a.selftest_cheap_distance or a.selftest_scale != 1.0
    def finish(code, stage="final"):
        R["stage"] = stage; R["gates"] = G; R["required_inventory"] = list(REQUIRED); R["required_all_true"] = all(G.get(k) is True for k in REQUIRED); R["B3_2B_PASS"] = bool(R["required_all_true"] and a.profile == "assets_official" and not selftest and code == 0); R["seconds"] = time.time() - t0
        note("B3_2B_PASS =", R["B3_2B_PASS"], "| stage:", stage, "| gates:", json.dumps(G)); log.close()
        R["output_inventory"] = {f: dict(sha256=sha(os.path.join(a.out, f)), bytes=os.path.getsize(os.path.join(a.out, f))) for f in sorted(os.listdir(a.out)) if f != "b3_2_shared_null_run_manifest.json" and os.path.isfile(os.path.join(a.out, f))}
        body = json.dumps(R, indent=1, ensure_ascii=False, default=str); tmp = os.path.join(a.out, "b3_2_shared_null_run_manifest.json.tmp"); open(tmp, "w").write(body); os.replace(tmp, os.path.join(a.out, "b3_2_shared_null_run_manifest.json")); print("run manifest written; B3_2B_PASS =", R["B3_2B_PASS"]); return code
    try:
        if a.profile != "assets_official": R["failures"].append("profile must be 'assets_official'"); return finish(1)
        sys.path.insert(0, a.phaseb); sys.path.insert(0, a.mt)
        pins_path = os.path.join(a.phaseb, "b3", "b3_2_pins.json"); pins = json.load(open(pins_path)); R["pins_sha256"] = sha(pins_path); inv = json.load(open(os.path.join(a.phaseb, "B2_completion_inventory.json")))
        G["G_pins_loaded"] = bool(pins.get("schema") == "b3_2_pins_v1" and inv.get("b3_sha256", {}).get("b3/b3_2_pins.json") == R["pins_sha256"])
        from step1_engine import __version__; from step1_engine.checkpoint import module_shas; from step1_engine.official_gate import current_env, _blas_check
        ms = module_shas(); G["G_engine_inventory"] = (inv["modules"] == ms and inv["engine_version"] == __version__ == pins["engine_version"]); me = os.path.abspath(__file__); G["G_script_sha"] = (inv.get("b3_sha256", {}).get("b3/b3_2_shared_null.py") == sha(me)); R["engine_version"] = __version__
        if not (G["G_pins_loaded"] and G["G_engine_inventory"] and G["G_script_sha"]): R["failures"].append("preflight binding failed"); return finish(1, "preflight")
        env = current_env(); ex = pins["environment"]; vers_ok = all(env.get(k) == ex[k] for k in ("python", "numpy", "scipy", "healpy", "pot"))
        try:
            import camb; camb_ok = camb.__version__ == ex["camb"]
        except Exception: camb_ok = False
        G["G_env_lock"] = bool(vers_ok and camb_ok and bool(_blas_check(env.get("blas_threads")))); R["env"] = env
        if not G["G_env_lock"] and not a.selftest_no_env_lock: R["failures"].append("environment lock failed"); return finish(1, "environment")
        A = pins["assets"]; G["G_assets_sha"] = all(sha(os.path.join(a.mt, A[k])) == A[k + "_sha256"] for k in ("a5_bstack", "step0_bpm", "t1_engine", "t2b2_bridge"))
        if not G["G_assets_sha"]: R["failures"].append("frozen asset SHA mismatch"); return finish(1, "assets")
        # ---- calibration bank (whitening + A10 cross-check ONLY), both selections
        from step1_engine.legacy_kernel import LegacyKernel, GEN_NS; k = LegacyKernel(a.mt); S_I, iI = k.psqrt(k.C_ISO); C = pins["shared_null"]["calibration"]; N = int(C["N"] * a.selftest_scale); m = C["m"]
        tt = time.time(); out, cid, _ = k.generate(N, m, (GEN_NS[C["purpose"]], C["stream"]), [S_I], tuple(C["selections"])); R["timings"]["calibration_generate"] = time.time() - tt; d64, d32 = out[(0, "float64")], out[(0, "float32")]
        # registered A10 cross-check gate: T1 AND T2 relative error, plane identity, cid/rows/shape identity on the compared prefix; stop before whitening / OT on failure
        ref = os.path.join(a.phaseb, "tests", "reference_assets", "a10a_calibration_official.npz"); ok_ref = sha(ref) == pins["a10_frozen"]["calibration_checkpoint_sha256"]; z = np.load(ref); n = min(N, len(z["T1"])); tol = float(pins["shared_null"]["a10_cross_check"]["tolerance"])
        rel1 = float(np.max(np.abs(d64["T1"][:n] - z["T1"][:n]) / np.abs(z["T1"][:n]))); rel2 = float(np.max(np.abs(d64["T2"][:n] - z["T2"][:n]) / np.abs(z["T2"][:n]))); pl = float(np.mean(d64["PL"][:n] == z["PL"][:n]))
        shp = (d64["T1"].shape == (N,) and d64["T2"].shape == (N,) and cid.shape == (N,) and z["cid"][:n].shape == cid[:n].shape and z["T1"].dtype == d64["T1"].dtype); cid_ok = bool(np.array_equal(cid[:n], z["cid"][:n]))
        bit = ok_ref and np.array_equal(d64["T1"][:n], z["T1"][:n]) and np.array_equal(d64["T2"][:n], z["T2"][:n]) and np.array_equal(d64["AX"][:n], z["AX"][:n]) and cid_ok
        R["calibration_vs_a10"] = dict(rows_compared=int(n), reference_rows=int(len(z["T1"])), bit_identical=bool(bit), max_rel_T1=rel1, max_rel_T2=rel2, plane_agreement=pl, cid_identical=cid_ok, shapes_ok=bool(shp), checkpoint_sha_ok=bool(ok_ref), tolerance=tol, scope="prefix of min(N_cal, reference rows); the formal N_cal is fixed by the pins")
        G["G_calibration_bank_matches_a10"] = bool(ok_ref and shp and cid_ok and pl == 1.0 and rel1 < tol and rel2 < tol and n == min(N, len(z["T1"])))
        if not G["G_calibration_bank_matches_a10"]: R["failures"].append("calibration bank does not reproduce the frozen A10 official checkpoint (T1/T2/plane/cid)"); return finish(1, "a10_cross_check")
        # ---- null pool: SEPARATE generation (registered purpose w2_isotropic, 3 x N_W2 rows, 6000 clusters), both selections
        P = pins["shared_null"]["null_pool"]; Nn = int(P["N"] * a.selftest_scale); tt = time.time(); outn, cidn, _ = k.generate(Nn, m, (GEN_NS[P["purpose"]], P["stream"]), [S_I], tuple(P["selections"])); R["timings"]["null_pool_generate"] = time.time() - tt; n64, n32 = outn[(0, "float64")], outn[(0, "float32")]
        G["G_pool_inventory"] = bool(N == int(C["N"] * a.selftest_scale) and Nn == int(P["N"] * a.selftest_scale) and Nn // m == int(P["K"] * a.selftest_scale) and m == 100 and C["purpose"] != P["purpose"] and GEN_NS[C["purpose"]] != GEN_NS[P["purpose"]] and len(k.calls) == 2 and set(C["selections"]) == set(P["selections"]) == {"float64", "float32"} and np.isfinite(n64["T1"]).all() and np.isfinite(n64["T2"]).all() and np.isfinite(n32["T1"]).all() and np.isfinite(n32["T2"]).all())
        R["pool_inventory"] = dict(N_cal=N, N_null=Nn, K_null=Nn // m, m=m, purposes=dict(calibration=C["purpose"], null=P["purpose"]), generation_calls=k.calls, selftest_scale=a.selftest_scale)
        # ---- whitening from the CALIBRATION bank, applied to both null-pool paths
        from step1_engine.positions import whitening_from_calibration, PositionBank, w2_exact, DISTANCE_KINDS; from step1_engine.w2_shared_build import build_shared_null_resumable
        T64 = np.c_[d64["T1"], d64["T2"]]; mu, W = whitening_from_calibration(T64); G["G_whitening"] = True
        Tw64 = (np.c_[n64["T1"], n64["T2"]] - mu) @ W.T; Tw32 = (np.c_[n32["T1"], n32["T2"]] - mu) @ W.T; iso = PositionBank(0, Tw64, cidn); iso32 = PositionBank(0, Tw32, cidn)
        wid = dict(source="calibration bank f64 (calibration purpose, stream 0)", N_cal=int(N), mu=mu.tolist(), W=W.tolist(), calibration_sha256=dict(T1=asha(d64["T1"]), T2=asha(d64["T2"]), T1_f32=asha(d32["T1"]), T2_f32=asha(d32["T2"])), null_pool_sha256=dict(T1=asha(n64["T1"]), T2=asha(n64["T2"]), T1_f32=asha(n32["T1"]), T2_f32=asha(n32["T2"])), null_pool=dict(purpose=P["purpose"], stream=P["stream"], N=int(Nn), K=int(Nn // m)))
        prov = dict(engine_version=__version__, inventory_sha256=sha(os.path.join(a.phaseb, "B2_completion_inventory.json")), pins_sha256=R["pins_sha256"], script_sha256=sha(me), rules_binding=json.load(open(os.path.join(a.phaseb, "B2_completion_inventory.json"))).get("documents_sha256"), env=dict(python=env.get("python"), numpy=env.get("numpy"), scipy=env.get("scipy"), pot=env.get("pot")), profile=("selftest" if selftest else "assets_official"))
        if a.selftest_cheap_distance:
            def cheap_dist(A_, B_): return float(abs(A_.mean(0) - B_.mean(0)).sum())
            dist = cheap_dist
        else: dist = w2_exact
        G["G_distance_registered"] = (dist is w2_exact) or a.selftest_cheap_distance; R["distance_kind"] = next((kk for kk, f in DISTANCE_KINDS.items() if f is dist), "injected_test_callable")
        np.savez_compressed(os.path.join(a.out, "b3_2_pools.npz"), cal_T1=d64["T1"], cal_T2=d64["T2"], cal_T1_f32=d32["T1"], cal_T2_f32=d32["T2"], cal_cid=cid, null_T1=n64["T1"], null_T2=n64["T2"], null_T1_f32=n32["T1"], null_T2_f32=n32["T2"], null_cid=cidn, null_Tw64=Tw64, null_Tw32=Tw32, mu=mu, W=W)
        # ---- resumable build (checkpoints in OUT/ckpt)
        rec = {}; tt = time.time(); asset = build_shared_null_resumable(iso, m, int(pins["shared_null"]["master_seed"]), os.path.join(a.out, "ckpt"), dist=dist, iso_f32=iso32, whitening_identity=wid, log=note, provenance=prov, record=rec); R["timings"]["shared_null_build"] = time.time() - tt; R["build_record"] = rec
        G["G_shared_null_valid"] = bool(asset.validate()); open(os.path.join(a.out, "b3_2_shared_null_asset.json"), "w").write(json.dumps(asset.as_dict(), indent=1))
        from step1_engine.rules_config import RULES
        R["shared_null"] = dict(sha256=asset.sha256, identity=asset.identity, q99_full={n: float(np.quantile(np.asarray(asset.null[n]["values"]), 0.99, method=RULES.quantile_method)) for n in asset.null}, values_summary={n: dict(mean=float(np.mean(asset.null[n]["values"])), max=float(np.max(asset.null[n]["values"]))) for n in asset.null}, bounds_max={n: float(np.max(asset.replicate_bounds[n])) for n in asset.replicate_bounds})
        G["G_evidence_saved"] = all(os.path.exists(os.path.join(a.out, f)) for f in ("b3_2_shared_null_asset.json", "b3_2_pools.npz")); R["module_sha256"] = ms
        return finish(0 if all(G[kk] is True for kk in REQUIRED) else 1, "complete")
    except Exception as ex:
        R["failures"].append("exception: " + repr(ex)); R["traceback"] = traceback.format_exc(); note(R["traceback"]); return finish(1, "exception")


if __name__ == "__main__": sys.exit(main())
