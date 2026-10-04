# -*- coding: utf-8 -*-
"""Phase D4C-0a (D-2W): the nine formal W2 CASES (E2 / E7 / E8 x L1.00 / L1.20 / L1.50; rules §10) from the REGISTERED D-2 W2 position banks (27 units cfg<id>_w2; matched primary,
paired float64 / float32 paths) with the REGISTERED shared-null asset and whitening, evaluated by the existing step1_engine.w2_context.build_w2_context (exact POT W2, prefix stop
rule, stability gate, paired float32 bound, trigger / w2-unresolved) through step1_engine.w2_cases. Preflight (before any bank is read): pins / inventory / script binding; Phase C
members; registered numerical environment HARD gate (incl. POT); frozen loader; verified TwelveContext (D-2 ledger / spec / table); registered shared-null asset; input roots
resolved against the D-2 ledger (formal: run id / run root, registry family / formal, every cfg<id>_w2 manifest SHA == ledger unit); matched roots from the registered D-1
covariances (production.intake_registered_covariance). Then: assemble -> evaluate -> publish per-case records + context record -> RESTORE the context from the published
records (array-free replay) and require equality with the live context (G_records_restored) -> run record. INPUTS and SOURCE ROOTS are read-only and protected from the output.
D2W_PASS requires production_official, no self-test flag, all REQUIRED gates True and rc 0. Self-test: --selftest-small (formal=False intake of small synthetic W2 banks; subset
of cases through --selftest-cases) never D2W_PASS. A POT technical failure raises inside positions.w2_exact and ends the run at stage 'exception' (no context is published)."""
from __future__ import annotations
import os
for _k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"): os.environ.setdefault(_k, "2")
import argparse, copy, hashlib, json, sys, time, traceback, resource
import numpy as np

REQUIRED = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_phaseC_members", "G_env_lock", "G_external_loader_sha", "G_twelve_context", "G_shared_null", "G_d2_inputs_resolved", "G_cases_assembled", "G_context_built", "G_records_restored", "G_record_saved")
FAMILIES = ("E2", "E7", "E8"); SIZES = ("L1.00", "L1.20", "L1.50")


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


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


def resolve_d2_inputs(d2_roots, d2l, plan, keys, selftest):
    """Resolve the supplied D-2 roots against the registered D-2 generation ledger. Returns (ok, info_per_family, registered_w2_units, reasons).
    Formal path (not selftest): every family of the requested cases must be supplied (and the three formal families for the formal run); each root must hold the
    accepted run's `d2_bank_registry.json` BYTE-IDENTICAL to the registered copy (file SHA == ledger families[F].records.bank_registry_sha256; the registry itself carries
    no run id), with family == F and formal True; every `cfg<id>_w2` unit of the ledger must appear in the registry `directories` with the same manifest SHA and with its
    registered path under the ledger run root (this binds the run id); every W2 unit directory of the requested cases must hold COMPLETE.json. Self-test path: only the
    presence of the roots and of the unit directories is required (the synthetic banks carry no registry). Reasons are recorded verbatim in the run record."""
    import os
    fams = sorted({plan[k]["family"] for k in keys}); reasons = []; info = {}; reg_units = {}
    if set(d2_roots) != set(fams): reasons.append(f"supplied roots {sorted(d2_roots)} != families of the requested cases {fams}")
    if not selftest and set(fams) != set(FAMILIES): reasons.append(f"formal run requires the families {list(FAMILIES)}")
    for f in fams:
        root = os.path.realpath(d2_roots.get(f, "")); info[f] = root; rp = os.path.join(root, "d2_bank_registry.json")
        if not os.path.isdir(root): reasons.append(f"{f}: root is not a directory"); continue
        if not selftest:
            fam_l = (d2l.get("families") or {}).get(f)
            if fam_l is None: reasons.append(f"{f}: family not in the registered D-2 ledger"); continue
            if not os.path.isfile(rp) or os.path.islink(rp): reasons.append(f"{f}: d2_bank_registry.json missing"); continue
            want = ((fam_l.get("records") or {}).get("bank_registry_sha256"))
            if sha(rp) != want: reasons.append(f"{f}: d2_bank_registry.json bytes differ from the registered run record (ledger bank_registry_sha256)"); continue
            _, d2reg = _json_snapshot(rp)
            if d2reg.get("family") != f or d2reg.get("formal") is not True: reasons.append(f"{f}: registry family / formal flag")
            units = {u: v for u, v in fam_l["units"].items() if u.endswith("_w2")}; dirs = d2reg.get("directories") or {}
            for u, v in units.items():
                e = dirs.get(u) or {}
                if e.get("manifest_sha256") != v["manifest_sha256"]: reasons.append(f"{f}: {u} manifest SHA differs from the ledger unit")
                if not (isinstance(e.get("path"), str) and e["path"].rstrip("/") == v["path"].rstrip("/") and e["path"].startswith(fam_l["run_root"].rstrip("/") + "/")): reasons.append(f"{f}: {u} registered path is not under the ledger run root")
            reg_units.update(units); info[f] = dict(root=root, run_id=fam_l["run_id"], run_root=fam_l["run_root"], registry_sha256=sha(rp), w2_units=len(units))
        for k in keys:
            if plan[k]["family"] == f:
                for cid in plan[k]["config_ids"]:
                    if not os.path.isfile(os.path.join(root, f"cfg{cid}_w2", "COMPLETE.json")): reasons.append(f"{k}: cfg{cid}_w2/COMPLETE.json missing")
    return (not reasons), info, reg_units, reasons


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mt", required=True); ap.add_argument("--phaseb", required=True); ap.add_argument("--phasec", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--d2-root", action="append", default=[], help="FAMILY=PATH: the accepted D-2 run of that family (its out/d2 directory holding cfg<id>_w2); E2, E7 and E8 for the formal run")
    ap.add_argument("--profile", default="production_official"); ap.add_argument("--selftest-small", action="store_true"); ap.add_argument("--selftest-skip-env-lock", action="store_true"); ap.add_argument("--selftest-cases", default=None, help="self-test only: comma-separated subset of case keys F/S")
    ap.add_argument("--attempt-id", default=None); ap.add_argument("--launcher-lock-sha256", default=None)
    a = ap.parse_args(); t0 = time.time(); selftest = a.selftest_small or a.selftest_skip_env_lock or a.selftest_cases is not None
    if os.path.islink(a.out): print("OUT must not be a symbolic link", file=sys.stderr); return 2
    out = os.path.realpath(a.out); out_exists = os.path.lexists(out)
    if out_exists and (not os.path.isdir(out) or os.listdir(out)): print("OUT must be a fresh (non-existent or empty) real directory", file=sys.stderr); return 2
    def inside(p, q): p, q = os.path.realpath(p), os.path.realpath(q); return p == q or p.startswith(q.rstrip(os.sep) + os.sep)
    d2_roots = {}
    for x in a.d2_root:
        if "=" not in x: print("--d2-root must be FAMILY=PATH", file=sys.stderr); return 2
        f, p = x.split("=", 1); d2_roots[f] = p
    protected = dict(mt=a.mt, phaseb=a.phaseb, phasec=a.phasec, **{f"d2_root_{f}": p for f, p in d2_roots.items()}); clash = [k for k, p in protected.items() if inside(out, p) or inside(p, out)]
    if clash: print("output must be disjoint from the inputs and the source roots (" + ", ".join(clash) + ")", file=sys.stderr); return 2
    if not out_exists: os.makedirs(out)
    log = open(os.path.join(out, "d2w_stdout.log"), "w"); G = {k: None for k in REQUIRED}
    R = dict(schema="d2w_run_record_v1", stage="init", failures=[], notes=[], selftest=bool(selftest), profile=a.profile, out=out, out_preexisting_empty=bool(out_exists), protected_roots={k: os.path.realpath(p) for k, p in protected.items()}, attempt=dict(attempt_id=a.attempt_id, launcher_lock_sha256=a.launcher_lock_sha256), stages_rss_mb={}, stages_peak_rss_mb={}, timings={})
    def note(*s):
        m = " ".join(str(x) for x in s); print(m, flush=True)
        try: log.write(m + "\n"); log.flush()
        except ValueError: pass
    def mark(stage): R["stages_rss_mb"][stage] = round(_rss_mb(), 1); R["stages_peak_rss_mb"][stage] = round(_peak_rss_mb(), 1); R["timings"][stage] = round(time.time() - t0, 3)
    def finish(code, stage="final"):
        R["stage"] = stage; R["gates"] = G; R["required_inventory"] = list(REQUIRED); R["required_all_true"] = all(G.get(k) is True for k in REQUIRED); R["D2W_PASS"] = bool(R["required_all_true"] and a.profile == "production_official" and not selftest and code == 0); R["seconds"] = time.time() - t0; mark("final")
        note("run finalization | stage:", stage, "| gates:", json.dumps(G)); log.close()
        try: _publish_json(os.path.join(out, "d2w_run_record.json"), R)
        except Exception as write_error: print("run record could not be published/verified; no PASS: " + repr(write_error), file=sys.stderr); return 1
        print("run record published and verified; D2W_PASS =", R["D2W_PASS"]); return code
    try:
        if a.profile != "production_official": R["failures"].append("profile"); return finish(1)
        sys.path.insert(0, a.phaseb)
        pins_path = os.path.join(a.phaseb, "d", "d3_pins.json"); pins = json.load(open(pins_path)); R["pins_sha256"] = sha(pins_path); inv_path = os.path.join(a.phaseb, "B2_completion_inventory.json"); inv0 = json.load(open(inv_path))
        G["G_pins_loaded"] = bool(pins.get("schema") == "d3_pins_v1" and inv0.get("d_sha256", {}).get("d/d3_pins.json") == R["pins_sha256"])
        from step1_engine import __version__; from step1_engine.checkpoint import module_shas
        G["G_engine_inventory"] = (inv0["modules"] == module_shas() and inv0["engine_version"] == __version__ == pins["engine_version"]); me = os.path.abspath(__file__); G["G_script_sha"] = (inv0.get("d_sha256", {}).get("d/d2w_cases.py") == sha(me)); R["engine_version"] = __version__
        R["source"] = dict(script_sha256=sha(me), inventory_sha256=sha(inv_path), pins_sha256=R["pins_sha256"], engine_version=__version__, phaseb=os.path.realpath(a.phaseb), mt=os.path.realpath(a.mt))
        if not (G["G_pins_loaded"] and G["G_engine_inventory"] and G["G_script_sha"]): R["failures"].append("preflight binding failed"); return finish(1, "preflight")
        pc = json.load(open(os.path.join(a.phasec, "PACKET_INVENTORY.json"))); members = {}
        for d, _, fs in os.walk(a.phasec):
            for f in fs:
                rel = os.path.relpath(os.path.join(d, f), a.phasec)
                if rel != "PACKET_INVENTORY.json" and "__pycache__" not in rel: members[rel] = dict(sha256=sha(os.path.join(d, f)), bytes=os.path.getsize(os.path.join(d, f)))
        G["G_phaseC_members"] = bool(sha(os.path.join(a.phasec, "PACKET_INVENTORY.json")) == pins["phaseC_inventory_sha256"] and set(members) == set(pc["files"]) and all(members[k] == dict(sha256=v["sha256"], bytes=v["bytes"]) for k, v in pc["files"].items()))
        from step1_engine.official_gate import current_env, _blas_check, EXPECTED_VERS
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
        from step1_engine.production import D1_REGISTERED_RECEIPT, _verified_frozen_loader, intake_registered_covariance
        try: t1, loader_id = _verified_frozen_loader(a.mt, D1_REGISTERED_RECEIPT["frozen_loaders"]); G["G_external_loader_sha"] = True; R["loader"] = loader_id
        except Exception as ex_: G["G_external_loader_sha"] = False; R["loader_error"] = repr(ex_)
        from step1_engine.d3_profile import twelve_context
        from step1_engine import w2_cases as wc
        from step1_engine.grid_registry import load_registry
        from step1_engine.rules_config import RULES
        ctx = twelve_context(a.phaseb); ident = ctx.identities; G["G_twelve_context"] = bool(ctx.verified and ident["config_map_sha256"] == pins["config_map_sha256"] and ident["covariance_receipt_sha256"] == pins["covariance_receipt_sha256"]); R["context_identities"] = dict(ident); table = ctx.table
        try: asset = wc.registered_shared_null_asset(a.phaseb); G["G_shared_null"] = bool(asset.sha256 == wc.SHARED_NULL["asset_sha256"] and int(asset.identity["m"]) == RULES.m and int(asset.identity["master_seed"]) == int(table["master_seed"])); R["shared_null"] = dict(wc.SHARED_NULL, m=asset.identity["m"], master_seed=asset.identity["master_seed"], iso_K=asset.identity["iso"]["K"], distance_kind=asset.identity["distance_kind"], replicate_bounds=asset.replicate_bounds is not None)
        except Exception as ex_: G["G_shared_null"] = False; R["shared_null_error"] = repr(ex_)
        if not (G["G_phaseC_members"] and G["G_external_loader_sha"] and G["G_twelve_context"] and G["G_shared_null"]): R["failures"].append("trusted-input binding failed"); return finish(1, "trusted_inputs")
        # ---- inputs resolved against the D-2 ledger
        plan = wc.case_plan(table); keys = sorted(plan) if a.selftest_cases is None else [k.strip() for k in a.selftest_cases.split(",")]
        if any(k not in plan for k in keys) or len(set(keys)) != len(keys): R["failures"].append("--selftest-cases must name formal case keys"); return finish(1, "inputs")
        fams = sorted({plan[k]["family"] for k in keys}); d2l = ctx.d2_ledger
        ok_in, inputs_info, reg_units, reasons = resolve_d2_inputs(d2_roots, d2l, plan, keys, selftest); R["inputs"] = dict(d2_roots=inputs_info, cases=keys, resolution_failures=reasons)
        G["G_d2_inputs_resolved"] = bool(ok_in)
        if not ok_in: R["failures"].append("inputs do not resolve to the accepted D-2 runs / W2 units: " + "; ".join(reasons)); return finish(1, "inputs")
        mark("preflight")
        # ---- matched roots from the registered D-1 covariances; case assembly (strong W2 intake; ledger binding when formal)
        reg = load_registry(os.path.join(a.phaseb, "tests/assets/a7_circle_geometry.csv"), os.path.join(a.phaseb, "tests/assets/a6_observer_design_points.json")); d1dir = os.path.join(a.phaseb, "registered_assets", "d1")
        roots = {}; R["covariances"] = {}
        for k in keys:
            for cid in plan[k]["config_ids"]:
                if cid in roots: continue
                cov = intake_registered_covariance(cid, reg, d1dir, a.mt); roots[cid] = cov["S_matched"]; R["covariances"][str(cid)] = dict(receipt=cov["receipt"], cov_file_sha256=cov["cov_file_sha256"], cov_array_sha256=cov["cov_array_sha256"])
        formal = not a.selftest_small
        cases, infos = wc.assemble_w2_cases({f: d2_roots[f] for f in fams}, roots, table, formal, registered_units=(reg_units if formal else None), families=tuple(fams), sizes=tuple(sorted({plan[k]["size_id"] for k in keys})))
        cases = {k: cases[k] for k in keys}; infos = {k: infos[k] for k in keys}
        G["G_cases_assembled"] = bool(set(cases) == set(keys) and all(len(c["positions"]) == 3 and len(c["positions_f32"]) == 3 for c in cases.values())); mark("intake")
        if not G["G_cases_assembled"]: R["failures"].append("case assembly"); return finish(1, "intake")
        # ---- evaluation (exact W2; the only numerical work) and publication
        tt = time.time(); w2ctx, asset = wc.evaluate_w2_cases(a.phaseb, cases, table); R["timings"]["evaluation_seconds"] = round(time.time() - tt, 1)
        G["G_context_built"] = bool(w2ctx.scope == wc.SCOPE_TRUSTED and set(w2ctx.decisions) == set(keys) and w2ctx.asset_sha256 == asset.sha256); mark("evaluation")
        os.makedirs(os.path.join(out, "cases")); recs = {}; pub = {}
        for k in keys:
            rec = wc.case_record(w2ctx, k, infos[k]); fn = f"d2w_case_{k.replace('/', '_')}.json"; pub[fn] = _publish_json(os.path.join(out, "cases", fn), rec); recs[k] = rec
            d = w2ctx.decisions[k]; note(f"  case {k}: trigger={d.trigger} state={d.validation_state} B_final={d.B_final} reason={d.validation_reason}")
        crec = wc.context_record(w2ctx, recs); pub["d2w_context_record.json"] = _publish_json(os.path.join(out, "d2w_context_record.json"), crec)
        R["context"] = dict(context_sha256=w2ctx.context_sha256, asset_sha256=w2ctx.asset_sha256, cases={k: dict(trigger=w2ctx.decisions[k].trigger, validation_state=w2ctx.decisions[k].validation_state, B_final=int(w2ctx.decisions[k].B_final), manifest_sha256=recs[k]["manifest_sha256"], result_sha256=recs[k]["result_sha256"]) for k in keys}); R["published_evidence"] = pub
        # ---- restore from the published records (array-free replay) and require equality with the live context
        back = [wc.restore_w2_context([json.load(open(os.path.join(out, "cases", f"d2w_case_{k.replace('/', '_')}.json"))) for k in keys], asset, expected_context_sha256=w2ctx.context_sha256, require_formal=formal)]
        G["G_records_restored"] = bool(back[0].context_sha256 == w2ctx.context_sha256 and all(back[0].decisions[k] == w2ctx.decisions[k] for k in keys)); mark("restore")
        if not G["G_records_restored"]: R["failures"].append("published records do not restore the live context")
        G["G_record_saved"] = True
        return finish(0 if all(G[kk] is True for kk in REQUIRED) else 1, "complete")
    except Exception as ex:
        R["failures"].append("exception: " + repr(ex)); R["traceback"] = traceback.format_exc(); note(R["traceback"]); return finish(1, "exception")


if __name__ == "__main__": sys.exit(main())
