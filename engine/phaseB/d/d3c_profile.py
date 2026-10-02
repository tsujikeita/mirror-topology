# -*- coding: utf-8 -*-
"""Phase D-3c tranche 1: real-bank 12-position profile of ONE family (E2 / E7 / E8) — formal bank intake of the fixed D-2 (first-wave 3 per size + family reference) and D-3b
(added 9 per size) banks, ordered-UID / K_fit checks, ONE family-shared five-seed plan construction (registered B / B_KDE / seeds; real cluster UIDs), six size inputs (3 sizes x 2
systems), all-size assembly, input fingerprints, the formal 12-position official gate (live environment; keyword plan_identity / table), identity re-check after the gate, and the
verified publication of the profile record + plan identity. NO threshold / Q / logD evaluation, labels, calibration, D-2W, noise, generation or re-stamping (design
Step1_PhaseD_D3c_design_v0.1.md + audit implementation conditions of Step1_PhaseD_D3b_tranche3_0.96.0_decision.json).
Preflight (before any bank is read): d3 pins / inventory / script binding; Phase C members; registered numerical environment HARD gate (the official gate requires the live
registered versions incl. CAMB and the BLAS pools); frozen loader; verified TwelveContext; bank spec v2; registered D-3b units WITH array acceptance (outer receipt); D-2 ledger /
receipt binding through the context; input roots resolved against the ledgers (D-2 run of this family; the three D-3b partitions of this family; formal: run ids == ledgers).
INPUTS are read-only (realpath-resolved, protected from the output); OUTPUT is a fresh directory; every JSON is published through the verified whole-document helper.
--selftest-small: synthetic small banks of the generators' self-tests (formal=False intakes; smoke gate; small B / B_KDE); never D3C_PASS."""
from __future__ import annotations
import os
for _k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"): os.environ.setdefault(_k, "2")
import argparse, copy, hashlib, json, sys, time, traceback, resource
import numpy as np

REQUIRED = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_phaseC_members", "G_env_lock", "G_external_loader_sha", "G_twelve_context", "G_bank_spec_v2", "G_d3b_units_accepted", "G_inputs_resolved", "G_all_supplies", "G_uids_ordered", "G_plans_fixed", "G_size_inputs", "G_family_assembled", "G_gate_passed", "G_identity_stable", "G_record_saved")
SIZES = ("L1.00", "L1.20", "L1.50"); FAMILIES = ("E2", "E7", "E8")


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _rss_mb():
    try:
        import psutil; return float(psutil.Process().memory_info().rss / 1e6)
    except Exception: return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e3)


def _publish_json(path, document):
    """Publish a whole immutable JSON snapshot; verify exactly the bytes written (same contract as d3_bankgen._publish_json)."""
    snapshot = copy.deepcopy(document); options = dict(indent=1, ensure_ascii=False, default=str, allow_nan=False)
    expected = json.dumps(snapshot, **options).encode("utf-8"); tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(snapshot, fh, **options); fh.flush(); os.fsync(fh.fileno())
        with open(tmp, "rb") as fh: written = fh.read()
        if written != expected: raise RuntimeError("JSON publication differs from the computed snapshot: " + path)
        os.replace(tmp, path)
        with open(path, "rb") as fh: published = fh.read()
        if published != expected: raise RuntimeError("published JSON differs from the computed snapshot: " + path)
        return dict(sha256=hashlib.sha256(published).hexdigest(), bytes=len(published))
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


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mt", required=True); ap.add_argument("--phaseb", required=True); ap.add_argument("--phasec", required=True); ap.add_argument("--out", required=True); ap.add_argument("--family", required=True)
    ap.add_argument("--d2-root", required=True, help="the accepted D-2 run of this family: its out/d2 directory (ref_<F>_b0/b1/fit and cfg<id>_b0/b1/fit of the first-wave configurations)")
    ap.add_argument("--d3b-root", action="append", default=[], help="SIZE=PATH: the accepted D-3b partition run's out/d3b directory for that size (three entries for the formal profile)")
    ap.add_argument("--profile", default="production_official")
    ap.add_argument("--selftest-small", action="store_true", help="synthetic small banks (formal=False intakes, smoke gate, small B / B_KDE); never D3C_PASS"); ap.add_argument("--selftest-skip-env-lock", action="store_true"); ap.add_argument("--selftest-sizes", default=None, help="self-test only: subset of sizes")
    ap.add_argument("--selftest-B", type=int, default=20); ap.add_argument("--selftest-B-KDE", type=int, default=25)
    a = ap.parse_args(); t0 = time.time(); selftest = a.selftest_small or a.selftest_skip_env_lock or a.selftest_sizes is not None
    out = os.path.realpath(a.out)
    if os.path.lexists(out) and (not os.path.isdir(out) or os.path.islink(out) or os.listdir(out)): print("OUT must be a fresh (non-existent or empty) real directory", file=sys.stderr); return 2
    def inside(p, q): p, q = os.path.realpath(p), os.path.realpath(q); return p == q or p.startswith(q.rstrip(os.sep) + os.sep)
    d3b_roots = {}
    for x in a.d3b_root:
        if "=" not in x: print("--d3b-root must be SIZE=PATH", file=sys.stderr); return 2
        s, p = x.split("=", 1); d3b_roots[s] = p
    protected = [os.path.abspath(a.phaseb), os.path.abspath(a.d2_root)] + [os.path.abspath(p) for p in d3b_roots.values()]
    if any(inside(out, p) or inside(p, out) for p in protected): print("output must be disjoint from the inputs and the source", file=sys.stderr); return 2
    os.makedirs(out); log = open(os.path.join(out, "d3c_profile_stdout.log"), "w"); G = {k: None for k in REQUIRED}
    R = dict(schema="d3c_profile_record_v1", stage="init", family=a.family, failures=[], notes=[], selftest=bool(selftest), profile=a.profile, out=out, stages_rss_mb={}, timings={})
    def note(*s):
        m = " ".join(str(x) for x in s); print(m, flush=True)
        try: log.write(m + "\n"); log.flush()
        except ValueError: pass
    def mark(stage): R["stages_rss_mb"][stage] = round(_rss_mb(), 1); R["timings"][stage] = round(time.time() - t0, 3)
    def finish(code, stage="final"):
        R["stage"] = stage; R["gates"] = G; R["required_inventory"] = list(REQUIRED); R["required_all_true"] = all(G.get(k) is True for k in REQUIRED); R["D3C_PASS"] = bool(R["required_all_true"] and a.profile == "production_official" and not selftest and code == 0); R["seconds"] = time.time() - t0; mark("final")
        note("run finalization | stage:", stage, "| gates:", json.dumps(G)); log.close()
        try: _publish_json(os.path.join(out, f"d3c_profile_record_{a.family}.json"), R)
        except Exception as write_error: print("profile record could not be published/verified; no PASS: " + repr(write_error), file=sys.stderr); return 1
        print("profile record published and verified; D3C_PASS =", R["D3C_PASS"]); return code
    try:
        if a.profile != "production_official": R["failures"].append("profile"); return finish(1)
        if a.family not in FAMILIES: R["failures"].append("family (E1 has no 12-position profile)"); return finish(1, "scope")
        sys.path.insert(0, a.phaseb)
        pins_path = os.path.join(a.phaseb, "d", "d3_pins.json"); pins = json.load(open(pins_path)); R["pins_sha256"] = sha(pins_path); inv_path = os.path.join(a.phaseb, "B2_completion_inventory.json"); inv0 = json.load(open(inv_path))
        G["G_pins_loaded"] = bool(pins.get("schema") == "d3_pins_v1" and inv0.get("d_sha256", {}).get("d/d3_pins.json") == R["pins_sha256"])
        from step1_engine import __version__; from step1_engine.checkpoint import module_shas
        G["G_engine_inventory"] = (inv0["modules"] == module_shas() and inv0["engine_version"] == __version__ == pins["engine_version"]); me = os.path.abspath(__file__); G["G_script_sha"] = (inv0.get("d_sha256", {}).get("d/d3c_profile.py") == sha(me)); R["engine_version"] = __version__
        if not (G["G_pins_loaded"] and G["G_engine_inventory"] and G["G_script_sha"]): R["failures"].append("preflight binding failed"); return finish(1, "preflight")
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
        from step1_engine.production import D1_REGISTERED_RECEIPT, _verified_frozen_loader, intake_registered_covariance, BankSupply
        try: t1, loader_id = _verified_frozen_loader(a.mt, D1_REGISTERED_RECEIPT["frozen_loaders"]); G["G_external_loader_sha"] = True; R["loader"] = loader_id
        except Exception as ex_: G["G_external_loader_sha"] = False; R["loader_error"] = repr(ex_)
        from step1_engine.d3_profile import twelve_context, load_registered_bank_spec_v2, intake_twelve_covariance, build_twelve_size_input, assemble_twelve_family, twelve_official_gate, fix_family_plans, verify_plan_identity
        from step1_engine.d3b_ledger import intake_registered_d3b_units
        from step1_engine.d2_rng import load_crn_table, native_reference_root, group_for
        from step1_engine.d2_bank import intake_registered_bank, FIT_K
        from step1_engine.d3_bank import intake_twelve_bank
        from step1_engine.formal_runner import input_fingerprint, input_snapshot
        from step1_engine.grid_registry import load_registry
        from step1_engine.legacy_kernel import LegacyKernel
        ctx = twelve_context(a.phaseb); ident = ctx.identities; G["G_twelve_context"] = bool(ctx.verified and ident["config_map_sha256"] == pins["config_map_sha256"] and ident["covariance_receipt_sha256"] == pins["covariance_receipt_sha256"]); R["context_identities"] = dict(ident)
        spec2 = load_registered_bank_spec_v2(ctx); G["G_bank_spec_v2"] = bool(spec2["spec_sha256"] == pins["bank_spec_v2_sha256"]); table = ctx.table; master_seed = table["master_seed"]
        try: U = intake_registered_d3b_units(a.phaseb, ctx); G["G_d3b_units_accepted"] = bool(U.verified and U.array_accepted is True and U.receipt_sha256 == pins.get("d3b_outer_receipt_sha256")); R["d3b"] = dict(ledger_sha256=U.ledger_sha256, receipt_sha256=U.receipt_sha256, generation_lock=U.source_lock)
        except Exception as ex_: G["G_d3b_units_accepted"] = False; R["d3b_error"] = repr(ex_)
        if not (G["G_phaseC_members"] and G["G_external_loader_sha"] and G["G_twelve_context"] and G["G_bank_spec_v2"] and G["G_d3b_units_accepted"]): R["failures"].append("trusted-input binding failed"); return finish(1, "trusted_inputs")
        # ---- inputs resolved against the ledgers
        fam = a.family; sizes = SIZES if a.selftest_sizes is None else tuple(s.strip() for s in a.selftest_sizes.split(","))
        if any(s not in SIZES for s in sizes) or len(set(sizes)) != len(sizes) or set(d3b_roots) != set(sizes): R["failures"].append(f"--d3b-root must give exactly the sizes {sizes}"); return finish(1, "inputs")
        d2l = ctx.d2_ledger; d2fam = d2l["families"][fam]; d2_root = os.path.realpath(a.d2_root); d3b_phys = {s: os.path.realpath(p) for s, p in d3b_roots.items()}
        ok_in = os.path.isfile(os.path.join(d2_root, "d2_bank_registry.json")) and all(os.path.isfile(os.path.join(p, "d3_bank_registry.json")) for p in d3b_phys.values())
        R["inputs"] = dict(d2_root=d2_root, d3b_roots=d3b_phys, d2_ledger=dict(run_id=d2fam["run_id"], run_root=d2fam["run_root"], commit=d2fam["commit"]), d3b_partitions={})
        if ok_in:
            _, d2reg = _json_snapshot(os.path.join(d2_root, "d2_bank_registry.json")); ok_in &= (d2reg.get("family") == fam) and (selftest or d2reg.get("formal") is True)
            if not selftest: ok_in &= all(d2reg["directories"][u]["manifest_sha256"] == d2fam["units"][u]["manifest_sha256"] for u in d2fam["units"] if u in d2reg["directories"]) and set(d2fam["units"]) <= set(d2reg["directories"])
            for s, p in d3b_phys.items():
                _, d3reg = _json_snapshot(os.path.join(p, "d3_bank_registry.json")); ok_in &= (d3reg.get("family") == fam and d3reg.get("sizes") == [s]) and (selftest or d3reg.get("formal") is True)
                if not selftest:
                    P = U.partitions[f"{fam}_{s}"]; ok_in &= all(d3reg["directories"][u]["manifest_sha256"] == P["units"][u]["manifest_sha256"] for u in P["units"]) and d3reg.get("spec_v2_sha256") == spec2["spec_sha256"]; R["inputs"]["d3b_partitions"][s] = dict(run_id=P["run_id"], run_root=P["run_root"])
        G["G_inputs_resolved"] = bool(ok_in)
        if not ok_in: R["failures"].append("inputs do not resolve to the accepted D-2 run / D-3b partitions of this family"); return finish(1, "inputs")
        mark("preflight")
        # ---- formal intake of every bank (fixed inputs; read-only)
        reg = load_registry(os.path.join(a.phaseb, "tests/assets/a7_circle_geometry.csv"), os.path.join(a.phaseb, "tests/assets/a6_observer_design_points.json")); d1dir = os.path.join(a.phaseb, "registered_assets", "d1"); d1reg = json.load(open(os.path.join(d1dir, "d1_cov_registry.json")))
        k = LegacyKernel(a.mt); S_I, _ = k.psqrt(k.C_ISO); formal = not a.selftest_small
        ref_dirs = {b: os.path.join(d2_root, f"ref_{fam}_b{b}") for b in (0, 1)}; ref_fit = os.path.join(d2_root, f"ref_{fam}_fit"); fr_units = spec2["family_reference"][fam]["units"]
        supplies = {s: {"matched": [], "native": []} for s in sizes}; R["supplies"] = {}; n_sup = 0
        rows = sorted((c for c in spec2["configurations"].values() if c["family"] == fam and c["size_id"] in sizes), key=lambda c: (c["size_id"], c["position_index"]))
        for c in rows:
            cid = c["config_id"]; s = c["size_id"]; tt = time.time()
            if c["mode"] == "reuse_D2_fixed_input":
                cov = intake_registered_covariance(cid, reg, d1dir, a.mt); covm = json.load(open(os.path.join(d1dir, d1reg["configurations"][str(cid)]["cov_file"] + ".manifest.json")))
                roots = dict(model_matched=cov["S_matched"], model_native=cov["S_native"], ref_native=native_reference_root(cov["c_ct"]), ref_matched=S_I)
                eval_dirs = {b: os.path.join(d2_root, f"cfg{cid}_b{b}") for b in (0, 1)}; fit_dir = os.path.join(d2_root, f"cfg{cid}_fit"); rec = dict(origin="first_wave_D1", receipt=cov["receipt"], cov_file_sha256=cov["cov_file_sha256"], cov_array_sha256=cov["cov_array_sha256"])
                for system in ("matched", "native"):
                    sup, info = intake_registered_bank(cid, system, eval_dirs, {0: ref_dirs[0], 1: ref_dirs[1]}, fit_dir, ref_fit, roots, covm, table, formal=formal)
                    if formal:   # E2: the returned unit identities must be the D-2 ledger units recorded in bank spec v2
                        want = c["d2"]["units"]; got = dict(cfg_b0=info["manifests"]["eval"][0], cfg_b1=info["manifests"]["eval"][1], cfg_fit=info["manifests"]["fit"])
                        if got["cfg_b0"] != want[f"cfg{cid}_b0"]["manifest_sha256"] or got["cfg_b1"] != want[f"cfg{cid}_b1"]["manifest_sha256"] or got["cfg_fit"] != want[f"cfg{cid}_fit"]["manifest_sha256"]: raise RuntimeError(f"config {cid}: D-2 bank units are not the fixed units of bank spec v2")
                        if info["manifests"]["ref"][0] != fr_units[f"ref_{fam}_b0"]["manifest_sha256"] or info["manifests"]["ref"][1] != fr_units[f"ref_{fam}_b1"]["manifest_sha256"] or info["manifests"]["ref_fit"] != fr_units[f"ref_{fam}_fit"]["manifest_sha256"]: raise RuntimeError(f"config {cid}: D-2 reference units are not the fixed family reference of bank spec v2")
                    supplies[s][system].append(sup); R["supplies"][f"{cid}/{system}"] = dict(rec, manifests=info["manifests"], n_clusters=info["n_clusters"], fitting_clusters=info["fitting_clusters"]); n_sup += 1
            else:
                cov = intake_twelve_covariance(cid, a.phaseb, a.mt); roots = dict(model_matched=cov["S_matched"], model_native=cov["S_native"], ref_native=native_reference_root(cov["c_ct"]), ref_matched=S_I)
                root3b = d3b_phys[s]; eval_dirs = {b: os.path.join(root3b, f"cfg{cid}_b{b}") for b in (0, 1)}; fit_dir = os.path.join(root3b, f"cfg{cid}_fit"); rec = dict(origin=cov["origin"], receipt=cov["receipt"], receipt_d3=cov["receipt_d3"], cov_file_sha256=cov["cov_file_sha256"], cov_array_sha256=cov["cov_array_sha256"])
                for system in ("matched", "native"):
                    sup, info = intake_twelve_bank(cid, system, eval_dirs, {0: ref_dirs[0], 1: ref_dirs[1]}, fit_dir, ref_fit, roots, ctx, formal=formal, registered_units=(U if formal else None))
                    supplies[s][system].append(sup); R["supplies"][f"{cid}/{system}"] = dict(rec, manifests=info["manifests"], n_clusters=info["n_clusters"], fitting_clusters=info["fitting_clusters"], d3b_ledger_sha256=info.get("d3b_ledger_sha256"), d3b_receipt_sha256=info.get("d3b_receipt_sha256")); n_sup += 1
            note(f"  intake {cid} ({s} position {c['position_index']}, {c['mode']}) {time.time()-tt:.0f}s rss {_rss_mb():.0f} MB")
        G["G_all_supplies"] = bool(n_sup == 24 * len(sizes) and all(len(supplies[s][sy]) == 12 for s in sizes for sy in ("matched", "native"))); mark("intake")
        if not G["G_all_supplies"]: R["failures"].append("supply count"); return finish(1, "intake")
        # ---- ordered UIDs (batch-specific) and K_fit across ALL supplies; registered constants
        first = supplies[sizes[0]]["matched"][0]; uids = list(first.cluster_uids); m = first.m; b0 = first.batches[0]; b1 = first.batches[1]; K0, K1 = (b0[1] - b0[0]) // m, (b1[1] - b1[0]) // m
        uids_b0, uids_b1 = uids[:K0], uids[K0:K0 + K1]; g_eval = group_for(table, "evaluation", fam)
        K_fit = int(first.fitting.cid.max()) + 1; n_fit = int(len(first.fitting.cid))
        ok_u = (len(uids) == K0 + K1 and all(u.batch_id == 0 and u.purpose_id == 200 and u.crn_group_id == g_eval and u.rotation_index == i for i, u in enumerate(uids_b0)) and all(u.batch_id == 1 and u.purpose_id == 200 and u.crn_group_id == g_eval and u.rotation_index == i for i, u in enumerate(uids_b1)))
        for s in sizes:
            for sy in ("matched", "native"):
                for sup in supplies[s][sy]: ok_u &= (list(sup.cluster_uids) == uids and sup.batches == first.batches and sup.m == m and int(sup.fitting.cid.max()) + 1 == K_fit and len(sup.fitting.cid) == n_fit and np.array_equal(sup.fitting.cid, first.fitting.cid))
        if formal: ok_u &= (K0 == RULES.N0 // RULES.m and K1 == (RULES.N_max - RULES.N0) // RULES.m and m == RULES.m and K_fit == REG_N_FIT // REG_M_FIT == FIT_K and n_fit == REG_N_FIT)
        G["G_uids_ordered"] = bool(ok_u); uid_sha = hashlib.sha256(json.dumps([list(u.as_tuple()) for u in uids]).encode()).hexdigest()
        R["uids"] = dict(K0=K0, K1=K1, m=m, K_fit=K_fit, n_fit=n_fit, evaluation_group=g_eval, ordered_uid_sha256=uid_sha, first_uid=list(uids[0].as_tuple()), last_uid=list(uids[-1].as_tuple()))
        if not ok_u: R["failures"].append("cluster UIDs / batches / K_fit are not identical and ordered across all supplies (or differ from the registered constants)"); return finish(1, "uids")
        # ---- ONE family-shared five-seed plan (registered constants; small B only in self-test)
        B, Bk = (RULES.B, REG_B_KDE) if formal else (a.selftest_B, a.selftest_B_KDE)
        plans, fplans, plan_ident = fix_family_plans(table, fam, {0: uids_b0, 1: uids_b1}, K_fit, master_seed, B=B, B_KDE=Bk)
        ok_p = verify_plan_identity(plans, fplans, plan_ident, table=table, family=fam) and plan_ident["B"] == B and plan_ident["B_KDE"] == Bk and plan_ident["seeds"] == RULES.seeds and plan_ident["master_seed"] == master_seed
        # roundtrip: the identity must be reproducible from the recorded ORDERED UIDs alone
        plans_r, fplans_r, ident_r = fix_family_plans(table, fam, {0: [tuple(u.as_tuple()) for u in uids_b0], 1: [tuple(u.as_tuple()) for u in uids_b1]}, K_fit, master_seed, B=B, B_KDE=Bk); ok_p &= (ident_r == plan_ident) and verify_plan_identity(plans_r, fplans_r, plan_ident, table=table, family=fam)
        G["G_plans_fixed"] = bool(ok_p); mark("plans")
        plan_doc = dict(schema="d3c_plan_identity_record_v1", family=fam, identity=plan_ident, ordered_uids={"0": [list(u.as_tuple()) for u in uids_b0], "1": [list(u.as_tuple()) for u in uids_b1]}, K_fit=K_fit, master_seed=master_seed, B=B, B_KDE=Bk, seeds=RULES.seeds, constants_source=("registered (rules_config.RULES / official_gate)" if formal else "SELF-TEST values (never formal)"),
                        reconstruction="fix_family_plans(table, family, {0: ordered_uids['0'], 1: ordered_uids['1']}, K_fit, master_seed, B, B_KDE) reproduces identity (all strata / multiplicity SHAs)", crn_table_sha256=table["table_sha256"], context_identities=dict(ident), engine_version=__version__, formal=formal, selftest=bool(selftest), source_lock=dict(commit_binding="see launcher lock", script_sha256=sha(me), inventory_sha256=sha(inv_path)), environment=dict(python=env.get("python"), numpy=env.get("numpy"), scipy=env.get("scipy")))
        if not ok_p: R["failures"].append("plan identity not reproducible / registered constants"); return finish(1, "plans")
        # ---- six size inputs, all-size assembly
        size_inputs = {}
        for s in sizes:
            fm_s = build_twelve_size_input(ctx, fam, s, "matched", supplies[s]["matched"], plans, fplans); fn_s = build_twelve_size_input(ctx, fam, s, "native", supplies[s]["native"], plans, fplans); size_inputs[s] = (fm_s, fn_s)
        G["G_size_inputs"] = bool(len(size_inputs) == len(sizes) and all(len(f.configs) == 12 for pair in size_inputs.values() for f in pair)); mark("size_inputs")
        fm, fn, fam_ident = assemble_twelve_family(ctx, fam, size_inputs); G["G_family_assembled"] = bool(len(fm.configs) == 12 * len(sizes) and len(fn.configs) == 12 * len(sizes) and fm.plans is plans and fn.plans is plans and (fam_ident.get("full_surviving_scope") is True or not formal)); R["family_identity"] = fam_ident; mark("assembly")
        fp_m0, fp_n0 = input_fingerprint(fm), input_fingerprint(fn); snap_m = input_snapshot(fm); R["input_fingerprints_before_gate"] = dict(matched=fp_m0, native=fp_n0, snapshot_matched_sha256=hashlib.sha256(json.dumps(snap_m, sort_keys=True, default=str).encode()).hexdigest())
        # ---- the formal 12-position official gate (live environment; keyword plan identity / table)
        gate = twelve_official_gate(fm, fn, mode=("official" if formal else "smoke"), plan_identity=plan_ident, table=table)
        R["gate"] = dict(mode=gate.mode, passed=bool(gate.passed), required_failures=list(gate.required_failures), diagnostics=gate.diagnostics); G["G_gate_passed"] = bool(gate.passed and (gate.diagnostics.get("environment_source") == "live_collected")); mark("gate")
        # ---- identity stable after the gate; the same plan objects
        fp_m1, fp_n1 = input_fingerprint(fm), input_fingerprint(fn); ok_i = (fp_m1 == fp_m0 and fp_n1 == fp_n0 and fm.plans is plans and fn.plans is plans and fm.fit_plans is fplans and verify_plan_identity(fm.plans, fm.fit_plans, plan_ident, table=table, family=fam) and verify_plan_identity(fn.plans, fn.fit_plans, plan_ident, table=table, family=fam))
        G["G_identity_stable"] = bool(ok_i); R["input_fingerprints_after_gate"] = dict(matched=fp_m1, native=fp_n1)
        if not G["G_gate_passed"]: R["failures"].append("official gate failed: " + "; ".join(gate.required_failures[:5]))
        if not ok_i: R["failures"].append("input / plan identity changed across the gate")
        # ---- publication
        R["plan_identity_sha256"] = plan_ident["identity_sha256"]; G["G_record_saved"] = False; R["publication_stage"] = "plan_identity"
        rec = _publish_json(os.path.join(out, f"d3c_plan_identity_{fam}.json"), plan_doc); R["published_evidence"] = {f"d3c_plan_identity_{fam}.json": rec}; G["G_record_saved"] = True; R["publication_stage"] = "plan_identity_verified"
        return finish(0 if all(G[kk] is True for kk in REQUIRED) else 1, "complete")
    except Exception as ex:
        R["failures"].append("exception: " + repr(ex)); R["traceback"] = traceback.format_exc(); note(R["traceback"]); return finish(1, "exception")


if __name__ == "__main__": sys.exit(main())
