# -*- coding: utf-8 -*-
"""B-3-1 official-scale control battery v0.3 (pre-execution audits R31-A..D, R32-A..C). Control profile: ONE configuration (the pinned A11 mock E7 covariance) x two systems at the
registered N0=1e6, m=100, B=2000, N_fit=2e5, B_KDE=2000 (kind='control'; NOT the production full surviving-size family; official_gate's production scope is not claimed).
Required gates (exact inventory): environment lock BEFORE generation; pins/inventory/script binding; frozen assets; mock covariance binding; sqrt hard gates; shared latent per purpose
(exact call inventory); finite banks; A5 cross-check (N=2e5 isotropic bank); NEGATIVE control with INDEPENDENT numerator/denominator resampling (own CRN group, own fitting bank/plans):
fixed target requires technical ok AND definite False for support and strong (unknown never counts), and the registered false-support rate over n independent isotropic pseudo thresholds
(Wilson(c+u,n) <= 0.05; each evaluation's technical_status is propagated as TECH; any TECH fails); POSITIVE REGISTERED control (rules §9.3 / A10c: isotropic reference scaled by 0.35 in
T1,T2, same clusters, both systems) with strong full predicate and precision pass; the 0.6 mock-model fixture is a DIAGNOSTIC (its scientific label is not a gate; its technical status is
still part of the finite/checkpoint gates); CONJUNCT battery (registered decider: bases True with technical ok, every single-condition drop a DEFINITE False with technical ok; one-conjunct-
removed mutant deciders detected); BRUTE-FORCE against the ACTUAL path (pure-Python row-loop oracle vs ConfigBank.hit_tables, and the real resample_hits vs literal resampling of the oracle
tables; skipped comparisons are failures; detector self-test with zeroed / cluster-permuted aggregations and a zeroed resampler); finite results; checkpoint round trip; evidence saved.
Evidence: all banks, plan identities (rng keys + multiplicity SHAs; seed-0 multiplicities), FamilyResult checkpoints, per-pseudo negative rows with rate_truth, logs, run manifest.
Non-zero exit on any failure; B3_1_PASS only in --profile control_official without self-test flags."""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time, platform, traceback
import numpy as np

REQUIRED = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_env_lock", "G_assets_sha", "G_cov_manifest_binding", "G_cov_array_sha", "G_sqrt_hard", "G_roles_shared_latent", "G_finite_banks",
            "G_iso_engine_matches_A5_null", "G_negative_fixed_target", "G_negative_support_rate", "G_positive_registered_full_predicate", "G_positive_registered_precision_pass", "G_conjunct_battery", "G_brute_force_actual_path", "G_brute_force_detector", "G_finite_results", "G_checkpoint_roundtrip", "G_evidence_saved")


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def asha(a): return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mt", required=True); ap.add_argument("--phaseb", required=True); ap.add_argument("--out", required=True); ap.add_argument("--pins", default=None)
    ap.add_argument("--profile", default="control_official"); ap.add_argument("--selftest-no-env-lock", action="store_true"); ap.add_argument("--selftest-scale", type=float, default=1.0, help="sandbox self-test only: scale N/Nfit (never issues B3_1_PASS)")
    ap.add_argument("--unbound-pins-test-scope", action="store_true"); a = ap.parse_args(); t0 = time.time()
    if os.path.exists(a.out) and os.listdir(a.out): print("OUT must be a fresh (empty) directory", file=sys.stderr); return 2
    os.makedirs(a.out, exist_ok=True); log = open(os.path.join(a.out, "b3_1_control_stdout.log"), "w"); G = {k: None for k in REQUIRED}; R = dict(stage="init", failures=[], timings={})
    def note(*s): m = " ".join(str(x) for x in s); print(m); log.write(m + "\n"); log.flush()
    def _jsonable(o):
        try:
            from step1_engine import serialization as ser; return ser.to_jsonable(o)
        except Exception:
            def conv(x):
                if isinstance(x, dict): return {str(k): conv(v) for k, v in x.items()}
                if isinstance(x, (list, tuple)): return [conv(v) for v in x]
                if isinstance(x, float) and (x != x or x in (float("inf"), float("-inf"))): return str(x)
                if hasattr(x, "tolist"): return conv(x.tolist())
                return x if isinstance(x, (str, int, float, bool)) or x is None else repr(x)
            return conv(o)
    selftest = a.selftest_no_env_lock or a.selftest_scale != 1.0 or a.unbound_pins_test_scope
    def finish(code, stage="final"):
        R["stage"] = stage; R["gates"] = G; R["required_inventory"] = list(REQUIRED); R["required_all_true"] = all(G.get(k) is True for k in REQUIRED)
        R["B3_1_PASS"] = bool(R["required_all_true"] and a.profile == "control_official" and not selftest and code == 0); R["seconds"] = time.time() - t0
        note("B3_1_PASS =", R["B3_1_PASS"], "| stage:", stage, "| gates:", json.dumps(G)); log.close()
        R["output_inventory"] = {f: dict(sha256=sha(os.path.join(a.out, f)), bytes=os.path.getsize(os.path.join(a.out, f))) for f in sorted(os.listdir(a.out)) if f != "b3_1_run_manifest.json"}
        body = json.dumps(_jsonable(R), indent=1, ensure_ascii=False); tmp = os.path.join(a.out, "b3_1_run_manifest.json.tmp")
        with open(tmp, "w") as fh: fh.write(body); fh.flush(); os.fsync(fh.fileno())
        os.replace(tmp, os.path.join(a.out, "b3_1_run_manifest.json")); print("run manifest written; B3_1_PASS =", R["B3_1_PASS"]); return code
    try:
        if a.profile != "control_official": R["failures"].append("profile must be 'control_official'"); return finish(1)
        sys.path.insert(0, a.phaseb); sys.path.insert(0, a.mt)
        pins_path = a.pins or os.path.join(a.phaseb, "b3", "b3_1_pins.json"); pins = json.load(open(pins_path)); R["pins"] = pins; R["pins_sha256"] = sha(pins_path)
        inv0 = json.load(open(os.path.join(a.phaseb, "B2_completion_inventory.json"))); pins_bound = inv0.get("b3_sha256", {}).get("b3/b3_1_pins.json") == R["pins_sha256"]
        if not pins_bound and not a.unbound_pins_test_scope: R["failures"].append("pins file is not the inventory-bound science pins"); G["G_pins_loaded"] = False; return finish(1, "preflight")
        G["G_pins_loaded"] = bool(pins.get("schema") == "b3_1_pins_v1" and "repo" not in pins and pins_bound)
        P = dict(pins["control_profile"]); N, m, B, Nfit, Bkde = int(P["N"] * a.selftest_scale), P["m"], P["B"], int(P["Nfit"] * a.selftest_scale), P["Bkde"]; K, Kf = N // m, Nfit // m
        R["execution_profile"] = dict(kind=("test" if selftest else "control"), mode="control_official", N=N, m=m, B=B, Nfit=Nfit, Bkde=Bkde, statistics_scope=P["scope"], selftest_scale=a.selftest_scale)
        from step1_engine import __version__; from step1_engine.checkpoint import module_shas, write_family_result, read_family_result; from step1_engine.official_gate import current_env, _blas_check
        inv = inv0; ms = module_shas(); G["G_engine_inventory"] = (inv["modules"] == ms and inv["engine_version"] == __version__ == pins["engine_version"]); R["engine_version"] = __version__; R["inventory_sha256"] = sha(os.path.join(a.phaseb, "B2_completion_inventory.json"))
        me = os.path.abspath(__file__); G["G_script_sha"] = (inv.get("b3_sha256", {}).get("b3/b3_1_control.py") == sha(me)); R["script_sha256"] = sha(me)
        if not (G["G_pins_loaded"] and G["G_engine_inventory"] and G["G_script_sha"]): R["failures"].append("preflight: pins/inventory/script binding failed"); return finish(1, "preflight")
        env = current_env(); R["env"] = env; R["platform"] = platform.platform(); ex = pins["environment"]; vers_ok = all(env.get(k) == ex[k] for k in ("python", "numpy", "scipy", "healpy", "pot"))
        try:
            import camb; camb_ok = camb.__version__ == ex["camb"]; env["camb"] = camb.__version__
        except Exception: camb_ok = False; env["camb"] = None
        blas_ok = bool(_blas_check(env.get("blas_threads"))); R["blas_check"] = dict(ok=blas_ok, pools=env.get("blas_threads")); G["G_env_lock"] = bool(vers_ok and camb_ok and blas_ok)
        if not G["G_env_lock"] and not a.selftest_no_env_lock: R["failures"].append("environment lock failed"); return finish(1, "environment")
        A = pins["assets"]; G["G_assets_sha"] = all(sha(os.path.join(a.mt, A[k])) == A[k + "_sha256"] for k in ("a5_bstack", "step0_bpm", "t1_engine", "t2b2_bridge"))
        if not G["G_assets_sha"]: R["failures"].append("frozen asset SHA mismatch"); return finish(1, "assets")
        from step1_engine.legacy_kernel import LegacyKernel, GEN_NS, LBLK; k = LegacyKernel(a.mt); t1, t2 = float(pins["target"]["T1_obs"]), float(pins["target"]["T2_obs"]); R["target_used"] = [t1, t2]
        mc = pins["mock_cov"]; mp = os.path.join(a.mt, mc["manifest"]); npy = os.path.join(a.mt, mc["npy"]); man = json.load(open(mp))
        from step1_engine.grid_manifest import verify_cov_manifest, ConfigurationSpec, cache_key
        spec = ConfigurationSpec(0, mc["topology"], "mock", 1.0, 0, 1, mc["params"], [], [-v for v in mc["x0"]], mc["x0"], cache_key(mc["topology"], mc["params"], mc["x0"]), dict(observational_status="mock", geometric_status="mock"), 1.0)
        cb = verify_cov_manifest(spec, man, npy); G["G_cov_manifest_binding"] = bool(cb["bound"] and cb["file_sha_verified"] and sha(mp) == mc["manifest_sha256"] and man["cov_array_sha256"] == mc["cov_array_sha256"])
        import t1_engine as te; Mx, C_real, meta = te.load_cov_full(npy); G["G_cov_array_sha"] = (meta.get("cov_array_sha256") == mc["cov_array_sha256"])
        C_M, c_ct = k.matched(C_real); C_RN = np.diag(np.concatenate([np.repeat(c_ct[i], 2 * l + 1) for i, (b, l) in enumerate(LBLK)]))
        S_M, iM = k.psqrt(C_M); S_I, iI = k.psqrt(k.C_ISO); S_N, iN = k.psqrt(C_real); S_RN, iRN = k.psqrt(C_RN)
        G["G_sqrt_hard"] = all(v["clip"] == 0 and v["lambda_min"] > 0 and v["sym"] < 1e-12 and v["recon"] < 1e-10 for v in (iM, iI, iN, iRN)); R["sqrt"] = dict(matched=iM, matched_ref=iI, native=iN, native_ref=iRN, c_ct=c_ct.tolist())
        if not (G["G_cov_manifest_binding"] and G["G_cov_array_sha"] and G["G_sqrt_hard"]): R["failures"].append("frozen input / root gates failed before generation"); return finish(1, "roots")
        ROLES = ["model_matched", "ref_matched", "model_native", "ref_native"]; roots = [S_M, S_I, S_N, S_RN]
        # ---- generation (one call per purpose; 4 roles share the latent): evaluation N, fitting Nfit, isotropic calibration 2e5*scale, negative-control model N (independent stream)
        tt = time.time(); ev, cid, _ = k.generate(N, m, (GEN_NS["m_sensitivity"], 0), roots, ("float64",)); R["timings"]["generate_eval_4roles"] = time.time() - tt
        tt = time.time(); fit, cidf, _ = k.generate(Nfit, m, (GEN_NS["pseudo"], 7), roots, ("float64",)); R["timings"]["generate_fit_4roles"] = time.time() - tt
        Ncal = int(pins["controls"]["a5_cross_check"]["calibration_N"] * a.selftest_scale); tt = time.time(); iso, cidi, _ = k.generate(Ncal, m, (GEN_NS["calibration"], 0), [S_I], ("float64",)); R["timings"]["generate_iso_cal"] = time.time() - tt
        tt = time.time(); neg, cidn, _ = k.generate(N, m, (GEN_NS["negative_control"], 0), [S_I], ("float64",)); negf, cidnf, _ = k.generate(Nfit, m, (GEN_NS["negative_control"], 1), [S_I], ("float64",)); R["timings"]["generate_negative"] = time.time() - tt
        n_neg = int(pins["controls"]["negative"]["n_pseudo"]); tt = time.time(); psd, cidp, _ = k.generate(n_neg, 1, (GEN_NS["pseudo"], 9), [S_I], ("float64",)); R["timings"]["generate_pseudo_thresholds"] = time.time() - tt   # independent isotropic pseudo observations (m=1)
        expected_calls = [dict(ids=[GEN_NS["m_sensitivity"], 0], N=N, m=m, systems=4), dict(ids=[GEN_NS["pseudo"], 7], N=Nfit, m=m, systems=4), dict(ids=[GEN_NS["calibration"], 0], N=Ncal, m=m, systems=1), dict(ids=[GEN_NS["negative_control"], 0], N=N, m=m, systems=1), dict(ids=[GEN_NS["negative_control"], 1], N=Nfit, m=m, systems=1), dict(ids=[GEN_NS["pseudo"], 9], N=n_neg, m=1, systems=1)]
        G["G_roles_shared_latent"] = bool(k.calls == expected_calls); R["generation_calls"] = k.calls
        banks = {f"eval_{r}": ev[(i, "float64")] for i, r in enumerate(ROLES)} | {f"fit_{r}": fit[(i, "float64")] for i, r in enumerate(ROLES)} | {"iso_calibration": iso[(0, "float64")], "negative_model": neg[(0, "float64")], "fit_negative_model": negf[(0, "float64")], "pseudo_thresholds": psd[(0, "float64")]}
        G["G_finite_banks"] = all(np.isfinite(d[key]).all() for d in banks.values() for key in ("T1", "T2"))
        np.savez_compressed(os.path.join(a.out, "b3_1_banks.npz"), **{f"{n}_{key}": d[key] for n, d in banks.items() for key in ("T1", "T2", "AX", "PL")}, cid_eval=cid, cid_fit=cidf, cid_iso=cidi, cid_neg=cidn, cid_negfit=cidnf, cid_pseudo=cidp); R["bank_sha256"] = {n: dict(T1=asha(d["T1"]), T2=asha(d["T2"])) for n, d in banks.items()}
        # ---- A5 cross-check
        A5 = pins["a5_reference"]; dI = banks["iso_calibration"]; med1, med2 = float(np.median(dI["T1"])), float(np.median(dI["T2"])); p1 = float(np.mean(dI["T1"] <= t1)); pB = float(np.mean((dI["T1"] <= t1) & (dI["T2"] <= t2)))
        chk = dict(T1_med=A5["T1_med_CI"][0] <= med1 <= A5["T1_med_CI"][1], T2_med=A5["T2_med_CI"][0] <= med2 <= A5["T2_med_CI"][1], P_T1=A5["P_T1_le_obs_wilson"][0] <= p1 <= A5["P_T1_le_obs_wilson"][1], P_EB=A5["P_eventB_wilson"][0] <= pB <= A5["P_eventB_wilson"][1])
        R["A5"] = dict(T1_median=med1, T2_median=med2, P_T1_le_obs=p1, P_eventB=pB, n=Ncal, checks=chk, provenance_sha_ok=(sha(os.path.join(a.mt, A5["source"])) == A5["provenance_sha256"])); G["G_iso_engine_matches_A5_null"] = bool(R["A5"]["provenance_sha_ok"] and all(chk.values()))
        # ---- plans (registered B and B_KDE; identities + seed-0 multiplicities saved; all multiplicity SHAs recorded)
        from step1_engine.bootstrap_plan import BootstrapPlan, FittingPlan, HitTable, bank_sha256; from step1_engine.types import ClusterUID
        uids = [ClusterUID(1, 200, 1, 0, i) for i in range(K)]; uidsN = [ClusterUID(1, 500, 2, 0, i) for i in range(K)]; tt = time.time()
        plans = {s: BootstrapPlan.build(f"b31-s{s}", s, {0: uids}, B, 20260912) for s in range(5)}; plansN = {s: BootstrapPlan.build(f"b31-neg-s{s}", s, {0: uidsN}, B, 20260912) for s in range(5)}   # independent CRN group for the negative model
        fplans = {s: FittingPlan.build(f"b31-fit{s}", 1, 1, s, Kf, Bkde, 20260913) for s in range(5)}; fplansN = {s: FittingPlan.build(f"b31-negfit{s}", 1, 2, s, Kf, Bkde, 20260913) for s in range(5)}; R["timings"]["plans"] = time.time() - tt
        pid = lambda pp: {s: dict(plan_id=p.plan_id, rng_keys=p.rng_keys, multiplicity_sha256={b: asha(np.asarray(mm, np.int64)) for b, mm in p.multiplicities.items()}, B=p.replicates, K=K) for s, p in pp.items()}
        R["plans"] = dict(evaluation=pid(plans), negative_model=pid(plansN), fitting={s: dict(plan_id=p.plan_id, rng_key=p.rng_key, multiplicities_sha256=p.multiplicities_sha256, B=int(p.multiplicities.shape[0]), K=p.K) for s, p in fplans.items()}, fitting_negative={s: dict(plan_id=p.plan_id, rng_key=p.rng_key, multiplicities_sha256=p.multiplicities_sha256) for s, p in fplansN.items()}, note="deterministic from rng keys; seed-0 multiplicities saved, others regenerable; negative model uses its own CRN group (independent numerator/denominator)")
        np.savez_compressed(os.path.join(a.out, "b3_1_plans_seed0.npz"), eval_mult=np.asarray(plans[0].multiplicities[0], np.int16), neg_mult=np.asarray(plansN[0].multiplicities[0], np.int16), fit_mult=np.asarray(fplans[0].multiplicities, np.int16), negfit_mult=np.asarray(fplansN[0].multiplicities, np.int16))
        from step1_engine.orchestrator import ConfigBank, FittingBank, FamilyInput, evaluate_family
        def fb(mr, rr): return FittingBank(np.c_[banks[f"fit_{mr}"]["T1"], banks[f"fit_{mr}"]["T2"]], np.c_[banks[f"fit_{rr}"]["T1"], banks[f"fit_{rr}"]["T2"]], cidf)
        def family(name, eid, system, T1m, T2m, T1r, T2r, fbank): return FamilyInput("E7", [ConfigBank(eid, "E7", system, 1.0, T1m, T2m, T1r, T2r, uids, m, {0: (0, N)})], plans, {eid: fbank}, fplans, True, {eid: bank_sha256(fbank.X_model, fbank.X_ref, fbank.cid)})
        em, er, nm, nr = banks["eval_model_matched"], banks["eval_ref_matched"], banks["eval_model_native"], banks["eval_ref_native"]; fbM, fbN = fb("model_matched", "ref_matched"), fb("model_native", "ref_native")
        results = {}
        # ---- main (diagnostic) evaluation at the official control profile
        tt = time.time(); r_main = evaluate_family(family("main", 100, "matched", em["T1"], em["T2"], er["T1"], er["T2"], fbM), family("main", 50100, "native", nm["T1"], nm["T2"], nr["T1"], nr["T2"], fbN), t1, t2); R["timings"]["eval_main"] = time.time() - tt; results["main"] = r_main
        # ---- NEGATIVE control (R31-A): isotropic model from an independent stream vs the isotropic reference; INDEPENDENT numerator/denominator plans; fixed target (definite False required)
        from step1_engine.controls import negative_decision, negative_rate_check, conjunct_battery, bruteforce_check, bruteforce_detector_selftest
        from step1_engine.truth import TECH
        ng = banks["negative_model"]; nf = banks["fit_negative_model"]; fr = banks["fit_ref_matched"]
        tt = time.time(); r_negf = negative_decision(ng, er, uidsN, uids, plansN, plans, m, nf, fr, cidnf, cidf, fplansN, fplans, t1, t2); R["timings"]["negative_fixed_target"] = time.time() - tt
        G["G_negative_fixed_target"] = bool(r_negf["gate"]); R["negative_fixed_target"] = r_negf
        # registered false-support rate (rules §9.3): n independent isotropic pseudo thresholds; unknown counted on the upper side; technical fails
        pt = banks["pseudo_thresholds"]; neg_truths = []; neg_rows = []; tt = time.time()
        for i in range(n_neg):
            ri = negative_decision(ng, er, uidsN, uids, plansN, plans, m, nf, fr, cidnf, cidf, fplansN, fplans, float(pt["T1"][i]), float(pt["T2"][i])); neg_truths.append(ri["truths"]["support"] if ri["technical_status"] == "ok" else TECH); neg_rows.append(dict(i=i, thr=[float(pt["T1"][i]), float(pt["T2"][i])], support=str(ri["truths"]["support"]), technical=ri["technical_status"], rate_truth=str(neg_truths[-1]), Q=ri["Q_point"], precision=ri["precision"]["state"], hits=ri["hits"]))
        R["timings"]["negative_rate"] = time.time() - tt; rate = negative_rate_check(neg_truths); G["G_negative_support_rate"] = bool(rate["ok"]); R["negative_rate"] = dict(rate, rows=neg_rows, scope="one configuration x n_pseudo independent isotropic pseudo thresholds (control profile); not the production global calibration")
        # ---- POSITIVE controls: REGISTERED (rules §9.3 / A10c): isotropic reference scaled by 0.35 in T1,T2 (same clusters, paired), both systems; the 0.6 mock-model fixture is a separate DIAGNOSTIC
        bt = pins["controls"]["positive_registered"]["boost"]; assert bt == {"T1": 0.35, "T2": 0.35}
        def boosted_family(name, eid, system, ref_bank, fit_ref_bank, eid_off):
            fbb = FittingBank(np.c_[fit_ref_bank["T1"] * bt["T1"], fit_ref_bank["T2"] * bt["T2"]], np.c_[fit_ref_bank["T1"], fit_ref_bank["T2"]], cidf)
            return family(name, eid + eid_off, system, ref_bank["T1"] * bt["T1"], ref_bank["T2"] * bt["T2"], ref_bank["T1"], ref_bank["T2"], fbb)
        tt = time.time(); r_pos = evaluate_family(boosted_family("pos", 300, "matched", er, banks["fit_ref_matched"], 0), boosted_family("pos", 300, "native", nr, banks["fit_ref_native"], 50000), t1, t2); R["timings"]["eval_positive_registered"] = time.time() - tt; results["positive_registered"] = r_pos
        G["G_positive_registered_full_predicate"] = bool(r_pos.truths["strong"] is True and r_pos.decision["technical_status"] == "ok"); G["G_positive_registered_precision_pass"] = bool(r_pos.precision["state"] == "pass")
        bd = pins["controls"]["positive_mock_diagnostic"]["boost"]; fbPM = FittingBank(np.c_[banks["fit_model_matched"]["T1"] * bd["T1"], banks["fit_model_matched"]["T2"] * bd["T2"]], fbM.X_ref, cidf); fbPN = FittingBank(np.c_[banks["fit_model_native"]["T1"] * bd["T1"], banks["fit_model_native"]["T2"] * bd["T2"]], fbN.X_ref, cidf)
        tt = time.time(); r_diag = evaluate_family(family("posdiag", 400, "matched", em["T1"] * bd["T1"], em["T2"] * bd["T2"], er["T1"], er["T2"], fbPM), family("posdiag", 50400, "native", nm["T1"] * bd["T1"], nm["T2"] * bd["T2"], nr["T1"], nr["T2"], fbPN), t1, t2); R["timings"]["eval_positive_mock_diagnostic"] = time.time() - tt; results["positive_mock_diagnostic"] = r_diag
        for name, r in results.items(): R[f"result_{name}"] = dict(Q_point=r.Q_point, precision=r.precision["state"], native_Q=(r.native or {}).get("Q_point"), native_precision=((r.native or {}).get("precision") or {}).get("state"), logD_point=(r.logD or {}).get("point"), logD_sens_pass=(r.logD or {}).get("sensitivity_pass"), logD_ci=(r.logD or {}).get("ci"), label=r.decision["display_label"], technical_status=r.decision["technical_status"], truths=r.truths, reasons=r.decision["reason_codes"])
        # ---- CONJUNCT battery (R31-D) on the registered positive's actual quantities, with mutant-decider detection
        q = r_pos.evidence["quantities"]; qQ, qD, qN = q["Q_matched"], q["logD_matched"], q["Q_native"]
        cq = dict(L_Q=qQ["lower"], U_Q=qQ["upper"], logD_point=qD["point"], L_logD=qD["lower"], U_logD=qD["upper"], L_Qn=qN["lower"], U_Qn=qN["upper"])
        if any(v is None for v in cq.values()): G["G_conjunct_battery"] = False; R["conjunct_battery"] = dict(ok=False, reason="registered positive did not yield all strong quantities", quantities=cq)
        else: cb_ = conjunct_battery(cq); G["G_conjunct_battery"] = bool(cb_["ok"]); R["conjunct_battery"] = dict(cb_, quantities=cq)
        # ---- BRUTE-FORCE (R31-C): row-loop oracle vs the ACTUAL aggregation path (ConfigBank.hit_tables -> HitTable -> literal resampling sums) + detector self-test
        qs = [0.005, 0.01, 0.02, 0.05, 0.1]; thr = [(t1, t2)] + [(float(np.quantile(dI["T1"], qq)), float(np.quantile(dI["T2"], qq))) for qq in qs]
        cfg_main = ConfigBank(100, "E7", "matched", 1.0, em["T1"], em["T2"], er["T1"], er["T2"], uids, m, {0: (0, N)}); cfg_nat = ConfigBank(50100, "E7", "native", 1.0, nm["T1"], nm["T2"], nr["T1"], nr["T2"], uids, m, {0: (0, N)})
        small = BootstrapPlan.build("b31-bf", 0, {0: uids}, 20, 20260914); tt = time.time(); bfm = bruteforce_check(cfg_main, thr, small); bfn = bruteforce_check(cfg_nat, thr, small); det = bruteforce_detector_selftest(cfg_main, thr[:2], small); R["timings"]["brute_force"] = time.time() - tt
        G["G_brute_force_actual_path"] = bool(bfm["ok"] and bfn["ok"]); G["G_brute_force_detector"] = bool(det["ok"]); R["brute_force"] = dict(matched=bfm, native=bfn, detector=det, note="oracle = pure-Python row loop per cluster; compared with ConfigBank.hit_tables (uids, hits, N) and literal resampling sums")
        # ---- finite inventory + checkpoints
        from step1_engine import serialization as ser
        fin = True; cps = {}
        for name, r in results.items():
            d = ser.from_jsonable(r.as_dict()); tagged = json.dumps(ser.to_jsonable(d)).count('"__float__"'); R.setdefault("nonfinite_tagged_floats", {})[name] = tagged; fin &= (tagged == 0)   # to_jsonable tags every non-finite float; none may appear in a healthy control result
            cp = os.path.join(a.out, f"b3_1_result_{name}.json"); csha = write_family_result(r, cp, extra=dict(b3_1=name)); back = read_family_result(cp, csha); cps[name] = dict(sha256=csha, verified=str(back.get("verified", "")).startswith("verified") or str(back.get("verified", "")).startswith("technical"))
            R[f"result_{name}"]["Q_ci_seed0"] = d["Q_ci_seed0"]
        G["G_finite_results"] = bool(fin and all(r.decision["technical_status"] == "ok" for r in results.values())); G["G_checkpoint_roundtrip"] = all(v["verified"] for v in cps.values()); R["checkpoints"] = cps
        G["G_evidence_saved"] = all(os.path.exists(os.path.join(a.out, f)) for f in ("b3_1_banks.npz", "b3_1_plans_seed0.npz", "b3_1_result_main.json", "b3_1_result_positive_registered.json", "b3_1_result_positive_mock_diagnostic.json")); R["module_sha256"] = ms
        return finish(0 if all(G[kk] is True for kk in REQUIRED) else 1, "complete")
    except Exception as ex:
        R["failures"].append("exception: " + repr(ex)); R["traceback"] = traceback.format_exc(); note(R["traceback"]); return finish(1, "exception")


if __name__ == "__main__": sys.exit(main())
