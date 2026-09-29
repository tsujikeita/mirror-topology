# -*- coding: utf-8 -*-
"""Phase D-3b tranche 1: bank generation script for the 81 ADDED twelve-position configurations (one family per invocation, optionally one size; formal profile production_official).
Preflight (before any numerics; the D-2 contracts plus the tranche 2b context): d3 pins / inventory / script binding; Phase C packet members; registered numerical environment
HARD gate (rules §12.1) in this process; frozen loader by real path + SHA; verified TwelveContext (config map == re-derivation, 108-position covariance receipt == re-derivation
== pins, CRN table == D-2 pins, canonical D-2 bank spec v1 == D-2 pins, D-2 ledger bytes == trusted identity); registered bank spec v2 == pins == re-derivation; live CRNRegistry
== table (bind_generation_inputs, the D-2 latent); registered calibration bank re-generated and cross-checked against the frozen A10 checkpoint; CMBtopology is NOT needed.
Per added configuration (mode generate_D3b; fail-fast; fresh attempt per directory; completed directories from --reuse-root are accepted ONLY after verify_twelve_bank_dir
against the context AND an exact match to the current request / producer): roots from d3_profile.intake_twelve_covariance (consumption-time re-verification of the registered
D-3a covariance: bytes / raw array SHA / frozen loader / symmetry / PSD / principal roots; PC1_PASS required); evaluation batches 0 and 1 (float64 only) on the FAMILY latent of
D-2 (same CRN table / groups / keys as the family reference and the first-wave banks); fitting bank. The D-2 family reference banks and the 27 first-wave banks are FIXED inputs
recorded in bank spec v2 by their ledger identities: they are never regenerated here; --d2-ref-root (optional) re-verifies them through the reuse binding and records the result.
Registry (d3_bank_registry.json): per directory the completion manifest SHA / rows / clusters / root SHAs / formal flag; call inventory; environment lock; producer binding;
partial registry on failure. D3B_PASS only in --profile production_official with scale 1.0 and no self-test flags; the outer receipt is bound AFTER the audit."""
from __future__ import annotations
import os
for _k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"): os.environ.setdefault(_k, "2")
import argparse, hashlib, json, sys, time, traceback
import numpy as np

REQUIRED = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_phaseC_members", "G_env_lock", "G_external_loader_sha", "G_twelve_context", "G_bank_spec_v2", "G_registry_bound", "G_calibration_bank_matches_a10", "G_scope_resolved", "G_all_configurations", "G_registry_saved")
SIZES = ("L1.00", "L1.20", "L1.50")


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mt", required=True); ap.add_argument("--phaseb", required=True); ap.add_argument("--phasec", required=True); ap.add_argument("--out", required=True); ap.add_argument("--family", required=True)
    ap.add_argument("--sizes", default=None, help="comma-separated size ids (subset of L1.00,L1.20,L1.50) to generate in this run; default all three (27 configurations)")
    ap.add_argument("--profile", default="production_official"); ap.add_argument("--reuse-root", default=None, help="a previous attempt's OUT: completed directories are re-verified against the context and reused; partial ones regenerated in fresh directories")
    ap.add_argument("--d2-ref-root", default=None, help="optional: directory holding the D-2 accepted family reference units ref_<F>_b0 / _b1 / _fit; re-verified through the reuse binding (identity recorded; never regenerated)")
    ap.add_argument("--selftest-scale", type=float, default=1.0); ap.add_argument("--selftest-skip-env-lock", action="store_true"); ap.add_argument("--selftest-configs", default=None); ap.add_argument("--selftest-skip-a10", action="store_true")
    a = ap.parse_args(); t0 = time.time()
    if os.path.exists(a.out) and os.listdir(a.out): print("OUT must be a fresh (empty) directory", file=sys.stderr); return 2
    os.makedirs(a.out, exist_ok=True); log = open(os.path.join(a.out, "d3_bankgen_stdout.log"), "w"); G = {k: None for k in REQUIRED}; G["G_d2_reference_dirs"] = None
    R = dict(stage="init", family=a.family, sizes=None, failures=[], timings={}, directories={}); selftest = a.selftest_scale != 1.0 or a.selftest_skip_env_lock or a.selftest_configs is not None or a.selftest_skip_a10
    def note(*s):
        m = " ".join(str(x) for x in s); print(m, flush=True)
        try: log.write(m + "\n"); log.flush()
        except ValueError: pass
    def finish(code, stage="final"):
        R["stage"] = stage; R["gates"] = G; R["required_inventory"] = list(REQUIRED); R["required_all_true"] = all(G.get(k) is True for k in REQUIRED); R["D3B_PASS"] = bool(R["required_all_true"] and a.profile == "production_official" and not selftest and code == 0); R["seconds"] = time.time() - t0
        note("D3B_PASS =", R["D3B_PASS"], "| stage:", stage, "| gates:", json.dumps(G)); log.close()
        tmp = os.path.join(a.out, "d3_run_manifest.json.tmp"); open(tmp, "w").write(json.dumps(R, indent=1, ensure_ascii=False, default=str)); os.replace(tmp, os.path.join(a.out, "d3_run_manifest.json")); print("run manifest written; D3B_PASS =", R["D3B_PASS"]); return code
    try:
        if a.profile != "production_official": R["failures"].append("profile"); return finish(1)
        sys.path.insert(0, a.phaseb)
        pins_path = os.path.join(a.phaseb, "d", "d3_pins.json"); pins = json.load(open(pins_path)); R["pins_sha256"] = sha(pins_path); inv_path = os.path.join(a.phaseb, "B2_completion_inventory.json"); inv0 = json.load(open(inv_path))
        G["G_pins_loaded"] = bool(pins.get("schema") == "d3_pins_v1" and inv0.get("d_sha256", {}).get("d/d3_pins.json") == R["pins_sha256"])
        from step1_engine import __version__; from step1_engine.checkpoint import module_shas
        G["G_engine_inventory"] = (inv0["modules"] == module_shas() and inv0["engine_version"] == __version__ == pins["engine_version"]); me = os.path.abspath(__file__); G["G_script_sha"] = (inv0.get("d_sha256", {}).get("d/d3_bankgen.py") == sha(me)); R["engine_version"] = __version__
        if not (G["G_pins_loaded"] and G["G_engine_inventory"] and G["G_script_sha"]): R["failures"].append("preflight binding failed"); return finish(1, "preflight")
        pc = json.load(open(os.path.join(a.phasec, "PACKET_INVENTORY.json"))); members = {}
        for d, _, fs in os.walk(a.phasec):
            for f in fs:
                rel = os.path.relpath(os.path.join(d, f), a.phasec)
                if rel != "PACKET_INVENTORY.json" and "__pycache__" not in rel: members[rel] = dict(sha256=sha(os.path.join(d, f)), bytes=os.path.getsize(os.path.join(d, f)))
        G["G_phaseC_members"] = bool(sha(os.path.join(a.phasec, "PACKET_INVENTORY.json")) == pins["phaseC_inventory_sha256"] and set(members) == set(pc["files"]) and all(members[k] == dict(sha256=v["sha256"], bytes=v["bytes"]) for k, v in pc["files"].items()))
        from step1_engine.official_gate import current_env, _blas_check
        env = current_env(); ex = pins["environment"]
        try:
            import camb as _camb; env["camb"] = _camb.__version__
        except Exception: env["camb"] = None
        vers_ok = all(env.get(k) == ex[k] for k in ("python", "numpy", "scipy", "healpy", "pot", "camb")); blas_ok = bool(_blas_check(env.get("blas_threads")))
        try:
            import threadpoolctl; TPC = threadpoolctl.threadpool_limits(limits=2)
        except Exception: TPC = None
        G["G_env_lock"] = bool(vers_ok and blas_ok); R["env"] = env; R["env_gate"] = dict(versions_ok=vers_ok, pools_ok=blas_ok, expected=ex)
        if not G["G_env_lock"] and not a.selftest_skip_env_lock: R["failures"].append("registered environment gate failed"); return finish(1, "environment")
        from step1_engine.production import D1_REGISTERED_RECEIPT, _verified_frozen_loader
        try: t1, loader_id = _verified_frozen_loader(a.mt, D1_REGISTERED_RECEIPT["frozen_loaders"]); G["G_external_loader_sha"] = True; R["loader"] = loader_id
        except Exception as ex_: G["G_external_loader_sha"] = False; R["loader_error"] = repr(ex_)
        # verified context (tranche 2b): map / receipt / table / D-2 spec v1 / D-2 ledger; bank spec v2 == pins == re-derivation; live registry == table (D-2 latent)
        from step1_engine.d3_profile import twelve_context, load_registered_bank_spec_v2, intake_twelve_covariance
        from step1_engine.d2_rng import load_crn_table, group_for, native_reference_root
        from step1_engine.d2_bank import bind_generation_inputs, CallInventory, M as _M, M_FIT as _MF, BATCHES as _B, FIT_K as _FK, _asha as _root_sha
        from step1_engine.d3_bank import generate_twelve_configuration_bank, generate_twelve_fitting_bank, verify_twelve_bank_dir, verify_reused_reference_dir, CONFIG_ROLES
        ctx = twelve_context(a.phaseb); ident = ctx.identities; G["G_twelve_context"] = bool(ctx.verified and ident["config_map_sha256"] == pins["config_map_sha256"] and ident["covariance_receipt_sha256"] == pins["covariance_receipt_sha256"] and ident["registry_sha256"] == pins["registry_sha256"]); R["context_identities"] = dict(ident)
        spec2 = load_registered_bank_spec_v2(ctx); G["G_bank_spec_v2"] = bool(spec2["spec_sha256"] == pins["bank_spec_v2_sha256"] and spec2["counts"]["generate"] == 81 and spec2["counts"]["reuse"] == 27)
        table, registry = load_crn_table(os.path.join(a.phaseb, "d", "d2_crn_table.json"), spec2["crn_table_sha256"]); spec1 = ctx.d2_spec
        bind_generation_inputs(registry, table, spec1); G["G_registry_bound"] = bool(table["table_sha256"] == ident["crn_table_sha256"] and spec1["spec_sha256"] == ident["d2_spec_sha256"] and spec2["inherits"].endswith(spec1["spec_sha256"]) and registry.master_seed == table["master_seed"] == spec2["master_seed"])
        if not (G["G_phaseC_members"] and G["G_external_loader_sha"] and G["G_twelve_context"] and G["G_bank_spec_v2"] and G["G_registry_bound"]): R["failures"].append("trusted-input binding failed"); return finish(1, "trusted_inputs")
        # registered calibration bank cross-checked against A10 official (same kernel / stream registry as the D-2 generation)
        from step1_engine.legacy_kernel import LegacyKernel, GEN_NS; k = LegacyKernel(a.mt); S_I, iI = k.psqrt(k.C_ISO)
        if a.selftest_skip_a10: G["G_calibration_bank_matches_a10"] = None
        else:
            tt = time.time(); ref = os.path.join(a.phaseb, "tests", "reference_assets", "a10a_calibration_official.npz"); rb = open(ref, "rb").read(); exp_ref = inv0.get("assets_sha256", {}).get("tests/reference_assets/a10a_calibration_official.npz")
            if exp_ref is None or hashlib.sha256(rb).hexdigest() != exp_ref: R["failures"].append("frozen A10 reference NPZ bytes differ from the inventory"); G["G_calibration_bank_matches_a10"] = False; return finish(1, "a10_reference_identity")
            import io; z = np.load(io.BytesIO(rb), allow_pickle=False); R["a10_reference_sha256"] = exp_ref
            out, cid, _ = k.generate(200_000, 100, (GEN_NS["calibration"], 0), [S_I], ("float64",)); d64 = out[(0, "float64")]
            rel = float(max(np.max(np.abs(d64["T1"] - z["T1"]) / np.abs(z["T1"])), np.max(np.abs(d64["T2"] - z["T2"]) / np.abs(z["T2"])))); G["G_calibration_bank_matches_a10"] = bool(rel < 1e-9 and np.array_equal(cid, z["cid"]) and float(np.mean(d64["PL"] == z["PL"])) == 1.0); R["a10_cross_check"] = dict(max_rel=rel, seconds=time.time() - tt)
            if not G["G_calibration_bank_matches_a10"]: R["failures"].append("calibration bank does not reproduce A10"); return finish(1, "a10_cross_check")
        # scope: this family, the requested sizes, mode generate_D3b only (first-wave ids are FIXED D-2 inputs; refused by the generator)
        fam = a.family; sizes = SIZES if a.sizes is None else tuple(s.strip() for s in a.sizes.split(","))
        if fam not in ("E2", "E7", "E8") or any(s not in SIZES for s in sizes) or len(set(sizes)) != len(sizes): R["failures"].append("unknown family / sizes"); return finish(1, "scope")
        cfgs = [c for c in sorted(spec2["configurations"].values(), key=lambda c: c["config_id"]) if c["family"] == fam and c["size_id"] in sizes and c["mode"] == "generate_D3b"]; sel_ids = None if a.selftest_configs is None else {int(x) for x in a.selftest_configs.split(",")}
        fixed = [c["config_id"] for c in sorted(spec2["configurations"].values(), key=lambda c: c["config_id"]) if c["family"] == fam and c["size_id"] in sizes and c["mode"] != "generate_D3b"]
        G["G_scope_resolved"] = bool(len(cfgs) == 9 * len(sizes) and len(fixed) == 3 * len(sizes) and all(c["covariance"]["pc1_status"] == "PC1_PASS" and c["covariance"]["consumption_allowed"] is True for c in cfgs)); R["sizes"] = list(sizes); R["scope"] = dict(generate=[c["config_id"] for c in cfgs], fixed_first_wave=fixed, selftest_subset=(sorted(sel_ids) if sel_ids else None))
        if not G["G_scope_resolved"]: R["failures"].append("scope does not resolve to 9 added + 3 fixed per size"); return finish(1, "scope")
        if sel_ids is not None and not sel_ids <= {c["config_id"] for c in cfgs}: G["G_scope_resolved"] = False; R["failures"].append(f"--selftest-configs outside the generate scope of this run (first-wave / other family / other size): {sorted(sel_ids - {c['config_id'] for c in cfgs})}"); return finish(1, "scope")
        # D-2 family reference: FIXED input by ledger identity (recorded); optional directory re-verification through the reuse binding
        fr = spec2["family_reference"][fam]; R["d2_family_reference"] = dict(units=fr["units"], d2_run_id=fr["d2_run_id"], d2_producer_digest=fr["d2_producer_digest"], d2_ledger_commit=spec2["d2_ledger_commit"], d2_ledger_file_sha256=spec2["d2_ledger_file_sha256"], ref_matched_root_sha256=_root_sha(np.asarray(S_I, float)))
        if a.d2_ref_root:
            try:
                vr = {u: verify_reused_reference_dir(os.path.join(a.d2_ref_root, u), ctx, fam, u) for u in (f"ref_{fam}_b0", f"ref_{fam}_b1", f"ref_{fam}_fit")}
                G["G_d2_reference_dirs"] = all(m_["root_sha256"]["ref_matched"] == R["d2_family_reference"]["ref_matched_root_sha256"] for m_ in vr.values()); R["d2_family_reference"]["verified_dirs"] = {u: dict(path=os.path.join(a.d2_ref_root, u), manifest_sha256=m_["manifest_sha256"], n_rows=m_["n_rows"]) for u, m_ in vr.items()}
            except Exception as ex_: G["G_d2_reference_dirs"] = False; R["d2_family_reference"]["verify_error"] = repr(ex_)
            if not G["G_d2_reference_dirs"]: R["failures"].append("--d2-ref-root does not hold the accepted D-2 family reference units"); return finish(1, "d2_reference")
        inv = CallInventory(); scale = a.selftest_scale
        # producer binding (as D-2 RD2T3B-B): the EXACT source that generates (module SHA map, script, pins, inventory), the context identities, the generation profile and the
        # pre-generation gate results are fixed here, digested, and written into every sidecar's environment; reuse requires equality with the CURRENT producer.
        producer = dict(engine_version=__version__, modules=module_shas(), script_sha256=sha(me), pins_sha256=R["pins_sha256"], inventory_sha256=sha(inv_path), crn_table_sha256=table["table_sha256"], spec_v1_sha256=spec1["spec_sha256"], spec_v2_sha256=spec2["spec_sha256"], covariance_receipt_sha256=ident["covariance_receipt_sha256"], config_map_sha256=ident["config_map_sha256"],
                        profile=dict(profile=a.profile, scale=scale, selftest=bool(selftest), skip_env_lock=bool(a.selftest_skip_env_lock), skip_a10=bool(a.selftest_skip_a10), configs=a.selftest_configs), gates_before_generation={kk: G[kk] for kk in REQUIRED if G[kk] is not None})
        producer["digest"] = hashlib.sha256(json.dumps(producer, sort_keys=True, default=str).encode()).hexdigest(); R["producer"] = producer
        env_rec = dict(python=env.get("python"), numpy=env.get("numpy"), scipy=env.get("scipy"), engine=__version__, fingerprint=hashlib.sha256(json.dumps(env, sort_keys=True, default=str).encode()).hexdigest(), producer=producer)
        ledger = []; cr = tuple(sorted(CONFIG_ROLES))
        def expected_request(name, c_, purpose, batch_id, root_arrays):
            if purpose == "evaluation": K_full = (_B[batch_id][1] - _B[batch_id][0]) // _M; mm = _M; group = group_for(table, "evaluation", fam)
            else: K_full = _FK; mm = _MF; group = group_for(table, "fitting", fam)
            K = K_full if scale == 1.0 else int(round(K_full * scale))
            return dict(name=name, kind="configuration", origin="twelve_added", family=fam, config_id=c_["config_id"], position_index=c_["position_index"], evaluation_ids=c_["evaluation_ids"], purpose=purpose, crn_group=group, wave_id=table["wave_id"], batch_id=batch_id, roles=list(cr), selections=["float64"], n_clusters=K, n_rows=K * mm, m=mm, scale=scale, formal=(scale == 1.0),
                        root_sha256={r: _root_sha(np.asarray(v, float)) for r, v in root_arrays.items()}, covariance=c_["covariance"], table_sha256=table["table_sha256"], spec_v1_sha256=spec1["spec_sha256"], spec_v2_sha256=spec2["spec_sha256"], covariance_receipt_sha256=ident["covariance_receipt_sha256"], config_map_sha256=ident["config_map_sha256"], master_seed=table["master_seed"], environment_fingerprint=env_rec["fingerprint"], engine=__version__)
        def capture_metadata(dir_):
            cb = open(os.path.join(dir_, "COMPLETE.json"), "rb").read(); mc = json.loads(cb.decode("utf-8"))
            sb = {sh["sidecar"]: open(os.path.join(dir_, sh["sidecar"]), "rb").read() for sh in mc.get("shards", [])}; return cb, mc, sb
        def check_metadata_snapshot(name, m_, cb, mc, side_bytes):
            payload = {kk: vv for kk, vv in mc.items() if kk != "manifest_sha256"}
            if mc.get("manifest_sha256") != m_["manifest_sha256"] or hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest() != m_["manifest_sha256"]: raise RuntimeError(f"cache {name}: captured completion manifest differs from the validated one")
            if set(side_bytes) != {sh["sidecar"] for sh in m_["shards"]}: raise RuntimeError(f"cache {name}: captured sidecar set differs from the validated manifest")
            for sh in m_["shards"]:
                if hashlib.sha256(side_bytes[sh["sidecar"]]).hexdigest() != sh["sidecar_sha256"]: raise RuntimeError(f"cache {name}: captured sidecar {sh['sidecar']} differs from the validated manifest")
        def export_metadata_snapshot(name, cb, side_bytes):
            dep = os.path.join(a.out, "audit_dependencies", name); os.makedirs(dep, exist_ok=True)
            for rel, data in {"COMPLETE.json": cb, **side_bytes}.items():
                dest = os.path.join(dep, rel)
                with open(dest, "wb") as fh: fh.write(data)
                if hashlib.sha256(open(dest, "rb").read()).hexdigest() != hashlib.sha256(data).hexdigest(): raise RuntimeError(f"cache {name}: exported dependency metadata {rel} differs from the captured bytes")
            return dep
        def match_request(m_, req, side_bytes):
            """The completed cache must be THIS request: identity, position, ranges, roots, selections, scale/formal, table / spec v1 / spec v2 / receipt / map, and the generation environment / engine / producer of every shard."""
            keys = ("origin", "family", "config_id", "position_index", "evaluation_ids", "purpose", "crn_group", "wave_id", "batch_id", "roles", "selections", "n_clusters", "n_rows", "m", "scale", "formal", "root_sha256", "table_sha256", "spec_v1_sha256", "spec_v2_sha256", "covariance_receipt_sha256", "config_map_sha256", "master_seed")
            diff = [k_ for k_ in keys if m_.get(k_) != req[k_]]
            if diff: raise RuntimeError(f"cache {req['name']}: differs from the current request on {diff}")
            for sh in m_["shards"]:
                side = json.loads(side_bytes[sh["sidecar"]].decode("utf-8")); e_ = side.get("environment") or {}
                if e_.get("fingerprint") != req["environment_fingerprint"] or e_.get("engine") != req["engine"]: raise RuntimeError(f"cache {req['name']}: generated under another environment / engine ({e_.get('engine')}, {str(e_.get('fingerprint'))[:12]}) than the current run")
                if side.get("covariance") != req["covariance"]: raise RuntimeError(f"cache {req['name']}: covariance metadata differs")
                pr = e_.get("producer")
                if not isinstance(pr, dict):
                    if not selftest: raise RuntimeError(f"cache {req['name']}: no producer binding recorded (a cache without a producer record is never used for a formal run)")
                    req.setdefault("notes", []).append("self-test reuse of a cache without a producer record (never promotable to formal)"); continue
                for kk in ("modules", "script_sha256", "pins_sha256", "inventory_sha256", "crn_table_sha256", "spec_v1_sha256", "spec_v2_sha256", "covariance_receipt_sha256", "config_map_sha256", "engine_version"):
                    if pr.get(kk) != producer[kk]: raise RuntimeError(f"cache {req['name']}: produced by a different exact source ({kk} differs; engine version strings alone are not a source binding)")
                pp = pr.get("profile") or {}
                if pp.get("profile") != a.profile or pp.get("scale") != scale or (not selftest and (pp.get("selftest") or pp.get("skip_env_lock") or pp.get("skip_a10"))): raise RuntimeError(f"cache {req['name']}: produced under a different generation profile / self-test flags")
                gb = pr.get("gates_before_generation") or {}
                if not selftest and any(gb.get(kk) is not True for kk in ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_phaseC_members", "G_env_lock", "G_external_loader_sha", "G_twelve_context", "G_bank_spec_v2", "G_registry_bound", "G_calibration_bank_matches_a10", "G_scope_resolved")): raise RuntimeError(f"cache {req['name']}: produced without the required pre-generation gates")
        def reuse_or_generate(req, gen):
            """Completed directory from --reuse-root (fully re-verified against the context AND matched to the expected request) or a fresh generation in OUT/name; every unit is entered in the ledger."""
            name = req["name"]
            if a.reuse_root and os.path.exists(os.path.join(a.reuse_root, name, "COMPLETE.json")):
                src = os.path.join(a.reuse_root, name); cb, mc, side_bytes = capture_metadata(src); m_ = verify_twelve_bank_dir(src, ctx, list(cr)); check_metadata_snapshot(name, m_, cb, mc, side_bytes); match_request(m_, req, side_bytes); dep = export_metadata_snapshot(name, cb, side_bytes)
                R["directories"][name] = dict(path=src, reused=True, dependency_metadata=dep, manifest_sha256=m_["manifest_sha256"], n_rows=m_["n_rows"], n_clusters=m_["n_clusters"], formal=m_["formal"], purpose=m_["purpose"], calls_source=m_["calls"], request=req); ledger.append(dict(name=name, satisfied_by="verified_reuse", manifest_sha256=m_["manifest_sha256"])); note(f"  reused {name} ({m_['n_rows']} rows; matched to the current request)"); return m_
            tt = time.time(); dest = os.path.join(a.out, name); m_ = gen(dest); cb, mc, side_bytes = capture_metadata(dest); check_metadata_snapshot(name, m_, cb, mc, side_bytes); match_request(m_, req, side_bytes)
            R["directories"][name] = dict(path=dest, reused=False, manifest_sha256=m_["manifest_sha256"], n_rows=m_["n_rows"], n_clusters=m_["n_clusters"], formal=m_["formal"], purpose=m_["purpose"], seconds=time.time() - tt, request=req); ledger.append(dict(name=name, satisfied_by="new_generation", manifest_sha256=m_["manifest_sha256"])); note(f"  generated {name} ({m_['n_rows']} rows, {time.time()-tt:.0f}s)"); return m_
        n_done = 0; R["covariance_intake"] = {}
        for c in cfgs:
            cid = c["config_id"]
            if sel_ids is not None and cid not in sel_ids: continue
            tt = time.time(); cov = intake_twelve_covariance(cid, a.phaseb, a.mt)
            if cov["cov_file_sha256"] != c["covariance"]["cov_file_sha256"] or cov["cov_array_sha256"] != c["covariance"]["cov_array_sha256"] or cov["receipt"] != c["covariance"]["receipt"] or cov["receipt_d3"] != ident["covariance_receipt_sha256"] or cov["origin"] != "twelve_added_D3a" or cov["position_index"] != c["position_index"]: raise RuntimeError(f"config {cid}: consumption-time covariance intake differs from bank spec v2 / the receipt")
            roots = dict(model_matched=cov["S_matched"], model_native=cov["S_native"], ref_native=native_reference_root(cov["c_ct"]))
            R["covariance_intake"][str(cid)] = dict(cov_file_sha256=cov["cov_file_sha256"], cov_array_sha256=cov["cov_array_sha256"], receipt=cov["receipt"], origin=cov["origin"], pc1_status=cov["pc1_status"], loader=cov["loader"], roots_info=cov["roots_info"], eig=cov["eig"], root_sha256={r: _root_sha(np.asarray(v, float)) for r, v in roots.items()}, seconds=time.time() - tt)
            for b in (0, 1): reuse_or_generate(expected_request(f"cfg{cid}_b{b}", c, "evaluation", b, roots), lambda d, b=b: generate_twelve_configuration_bank(k, registry, ctx, cid, roots, b, d, inv, ("float64",), scale=scale, env=env_rec))
            reuse_or_generate(expected_request(f"cfg{cid}_fit", c, "fitting", 0, roots), lambda d: generate_twelve_fitting_bank(k, registry, ctx, cid, roots, d, inv, scale=scale, env=env_rec))
            R["timings"][str(cid)] = time.time() - tt; n_done += 1; note(f"config {cid} ({c['size_id']} position {c['position_index']}) done ({time.time()-tt:.0f}s)")
        required = [f"cfg{c['config_id']}_{x}" for c in cfgs if sel_ids is None or c["config_id"] in sel_ids for x in ("b0", "b1", "fit")]
        done = {e["name"] for e in ledger}; all_formal = all(R["directories"][n_]["formal"] is True for n_ in done)
        G["G_all_configurations"] = bool(set(required) == done and (all_formal or scale < 1.0)); R["ledger"] = ledger; R["required_requests"] = required
        regj = dict(schema="d3_bank_registry_v1", family=fam, sizes=list(sizes), scale=scale, formal=(scale == 1.0 and not selftest and all_formal and set(required) == done), table_sha256=table["table_sha256"], spec_v1_sha256=spec1["spec_sha256"], spec_v2_sha256=spec2["spec_sha256"], covariance_receipt_sha256=ident["covariance_receipt_sha256"], config_map_sha256=ident["config_map_sha256"], registry_sha256=ident["registry_sha256"],
                    scope=R["scope"], d2_family_reference=R["d2_family_reference"], covariance_intake=R["covariance_intake"], directories=R["directories"], required_requests=required, ledger=ledger, calls=inv.calls, calls_reused={n_: v.get("calls_source") for n_, v in R["directories"].items() if v.get("reused")}, environment=env_rec, engine_version=__version__, loader=R.get("loader"), a10_reference_sha256=R.get("a10_reference_sha256"))
        json.dump(regj, open(os.path.join(a.out, "d3_bank_registry.json"), "w"), indent=1, default=str); G["G_registry_saved"] = True
        return finish(0 if all(G[kk] is True for kk in REQUIRED) else 1, "complete")
    except Exception as ex:
        R["failures"].append("exception: " + repr(ex)); R["traceback"] = traceback.format_exc(); note(R["traceback"])
        try: json.dump(dict(schema="d3_bank_registry_v1", status="PARTIAL_AFTER_FAILURE", family=a.family, directories=R["directories"]), open(os.path.join(a.out, "d3_bank_registry.json"), "w"), indent=1, default=str)
        except Exception: pass
        return finish(1, "exception")


if __name__ == "__main__": sys.exit(main())
