# -*- coding: utf-8 -*-
"""Phase D-2 tranche 3b: first-wave bank generation script (one family per invocation; formal profile production_official).
Preflight (before any numerics, same contracts as D-1 v0.3): pins / inventory / script binding; Phase C packet members; registered numerical environment HARD gate (rules §12.1)
in this process; D-1 receipt / registry bytes == trusted constants; frozen loader / bridge by real path + SHA; CRN table + bank spec == committed (payload SHA) and == canonical
re-derivation; live CRNRegistry == table (bind_generation_inputs); registered calibration bank re-generated and cross-checked against the frozen A10 checkpoint (whitening mu / W
for the W2 intake; identity recorded, not used to generate); CMBtopology is NOT needed (no covariance generation here).
Per configuration (family loop; fail-fast; fresh attempt per directory; completed directories from --reuse-root are accepted ONLY after verify_bank_dir):
  roots from production.intake_registered_covariance (re-verified at load); evaluation batches 0 (+float32 for the required subset) and 1 (float64) on the family latent;
  fitting bank; W2 position bank (E2/E7/E8). Family reference: evaluation batches 0/1 + fitting on the same latent with the PR3 isotropic root.
Registry (d2_bank_registry.json): per directory the completion manifest SHA / rows / clusters / root SHAs / formal flag; call inventory; environment lock; partial registry on
failure. D2_PASS only in --profile production_official with scale 1.0 and no self-test flags; the outer receipt (source commit / inventory / audit) is bound AFTER the audit."""
from __future__ import annotations
import os
for _k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"): os.environ.setdefault(_k, "2")
import argparse, hashlib, json, sys, time, traceback, subprocess
import numpy as np

REQUIRED = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_phaseC_members", "G_env_lock", "G_d1_trusted", "G_external_loader_sha", "G_crn_table", "G_bank_spec", "G_registry_bound", "G_calibration_bank_matches_a10", "G_family_reference", "G_all_configurations", "G_registry_saved")


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mt", required=True); ap.add_argument("--phaseb", required=True); ap.add_argument("--phasec", required=True); ap.add_argument("--out", required=True); ap.add_argument("--family", required=True)
    ap.add_argument("--profile", default="production_official"); ap.add_argument("--reuse-root", default=None, help="a previous attempt's OUT: completed directories are re-verified and reused; partial ones regenerated in fresh directories")
    ap.add_argument("--selftest-scale", type=float, default=1.0); ap.add_argument("--selftest-skip-env-lock", action="store_true"); ap.add_argument("--selftest-configs", default=None); ap.add_argument("--selftest-skip-a10", action="store_true")
    a = ap.parse_args(); t0 = time.time()
    if os.path.exists(a.out) and os.listdir(a.out): print("OUT must be a fresh (empty) directory", file=sys.stderr); return 2
    os.makedirs(a.out, exist_ok=True); log = open(os.path.join(a.out, "d2_bankgen_stdout.log"), "w"); G = {k: None for k in REQUIRED}; R = dict(stage="init", family=a.family, failures=[], timings={}, directories={}); selftest = a.selftest_scale != 1.0 or a.selftest_skip_env_lock or a.selftest_configs is not None or a.selftest_skip_a10
    def note(*s):
        m = " ".join(str(x) for x in s); print(m, flush=True)
        try: log.write(m + "\n"); log.flush()
        except ValueError: pass
    def finish(code, stage="final"):
        R["stage"] = stage; R["gates"] = G; R["required_inventory"] = list(REQUIRED); R["required_all_true"] = all(G.get(k) is True for k in REQUIRED); R["D2_PASS"] = bool(R["required_all_true"] and a.profile == "production_official" and not selftest and code == 0); R["seconds"] = time.time() - t0
        note("D2_PASS =", R["D2_PASS"], "| stage:", stage, "| gates:", json.dumps(G)); log.close()
        tmp = os.path.join(a.out, "d2_run_manifest.json.tmp"); open(tmp, "w").write(json.dumps(R, indent=1, ensure_ascii=False, default=str)); os.replace(tmp, os.path.join(a.out, "d2_run_manifest.json")); print("run manifest written; D2_PASS =", R["D2_PASS"]); return code
    try:
        if a.profile != "production_official": R["failures"].append("profile"); return finish(1)
        sys.path.insert(0, a.phaseb)
        pins_path = os.path.join(a.phaseb, "d", "d2_pins.json"); pins = json.load(open(pins_path)); R["pins_sha256"] = sha(pins_path); inv0 = json.load(open(os.path.join(a.phaseb, "B2_completion_inventory.json")))
        G["G_pins_loaded"] = bool(pins.get("schema") == "d2_pins_v1" and inv0.get("d_sha256", {}).get("d/d2_pins.json") == R["pins_sha256"])
        from step1_engine import __version__; from step1_engine.checkpoint import module_shas
        G["G_engine_inventory"] = (inv0["modules"] == module_shas() and inv0["engine_version"] == __version__ == pins["engine_version"]); me = os.path.abspath(__file__); G["G_script_sha"] = (inv0.get("d_sha256", {}).get("d/d2_bankgen.py") == sha(me)); R["engine_version"] = __version__
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
        from step1_engine.production import D1_REGISTERED_RECEIPT, intake_registered_covariance, _verified_frozen_loader; d1dir = os.path.join(a.phaseb, "registered_assets", "d1")
        G["G_d1_trusted"] = bool(sha(os.path.join(d1dir, "d1_receipt.json")) == D1_REGISTERED_RECEIPT["receipt_file_sha256"] and sha(os.path.join(d1dir, "d1_cov_registry.json")) == D1_REGISTERED_RECEIPT["registry_sha256"])
        try: t1, loader_id = _verified_frozen_loader(a.mt, D1_REGISTERED_RECEIPT["frozen_loaders"]); G["G_external_loader_sha"] = True; R["loader"] = loader_id
        except Exception as ex_: G["G_external_loader_sha"] = False; R["loader_error"] = repr(ex_)
        from step1_engine.d2_rng import load_crn_table; from step1_engine.d2_bank import load_bank_spec, bind_generation_inputs, canonical_context, generate_configuration_bank, generate_fitting_bank, generate_w2_position_bank, verify_bank_dir, CallInventory
        table, registry = load_crn_table(os.path.join(a.phaseb, "d", "d2_crn_table.json"), pins["crn_table_sha256"]); G["G_crn_table"] = True
        spec = load_bank_spec(os.path.join(a.phaseb, "d", "d2_bank_spec.json"), pins["bank_spec_sha256"], table); G["G_bank_spec"] = True
        bind_generation_inputs(registry, table, spec); ctx = canonical_context(table); reg = ctx["registry"]; G["G_registry_bound"] = bool(reg.registry_sha256 == spec["registry_sha256"] == pins["registry_sha256"])
        if not (G["G_phaseC_members"] and G["G_d1_trusted"] and G["G_external_loader_sha"] and G["G_registry_bound"]): R["failures"].append("trusted-input binding failed"); return finish(1, "trusted_inputs")
        # registered calibration bank (whitening identity for the W2 intake) cross-checked against A10 official
        from step1_engine.legacy_kernel import LegacyKernel, GEN_NS; k = LegacyKernel(a.mt); S_I, iI = k.psqrt(k.C_ISO)
        if a.selftest_skip_a10: G["G_calibration_bank_matches_a10"] = None
        else:
            tt = time.time(); ref = os.path.join(a.phaseb, "tests", "reference_assets", "a10a_calibration_official.npz"); rb = open(ref, "rb").read(); exp_ref = inv0.get("assets_sha256", {}).get("tests/reference_assets/a10a_calibration_official.npz")
            if exp_ref is None or hashlib.sha256(rb).hexdigest() != exp_ref: R["failures"].append("frozen A10 reference NPZ bytes differ from the inventory"); G["G_calibration_bank_matches_a10"] = False; return finish(1, "a10_reference_identity")
            import io; z = np.load(io.BytesIO(rb), allow_pickle=False); R["a10_reference_sha256"] = exp_ref
            out, cid, _ = k.generate(200_000, 100, (GEN_NS["calibration"], 0), [S_I], ("float64",)); d64 = out[(0, "float64")]
            rel = float(max(np.max(np.abs(d64["T1"] - z["T1"]) / np.abs(z["T1"])), np.max(np.abs(d64["T2"] - z["T2"]) / np.abs(z["T2"])))); G["G_calibration_bank_matches_a10"] = bool(rel < 1e-9 and np.array_equal(cid, z["cid"]) and float(np.mean(d64["PL"] == z["PL"])) == 1.0); R["a10_cross_check"] = dict(max_rel=rel, seconds=time.time() - tt)
            if not G["G_calibration_bank_matches_a10"]: R["failures"].append("calibration bank does not reproduce A10"); return finish(1, "a10_cross_check")
        fam = a.family; man = ctx["manifest"]; cfgs = [c for c in man.configurations if c.family == fam]; sel_ids = None if a.selftest_configs is None else {int(x) for x in a.selftest_configs.split(",")}
        if not cfgs: R["failures"].append("unknown family"); return finish(1, "family")
        inv = CallInventory(); scale = a.selftest_scale
        # producer binding (RD2T3B-B): the EXACT source that generates (module SHA map, script, pins, inventory), the generation profile (official/selftest, scale, skip flags) and the
        # pre-generation gate results are fixed here, digested, and written into every sidecar's environment; reuse requires equality with the CURRENT producer (no version-string proxy).
        producer = dict(engine_version=__version__, modules=module_shas(), script_sha256=sha(me), pins_sha256=R["pins_sha256"], inventory_sha256=sha(os.path.join(a.phaseb, "B2_completion_inventory.json")), crn_table_sha256=table["table_sha256"], spec_sha256=spec["spec_sha256"],
                        profile=dict(profile=a.profile, scale=scale, selftest=bool(selftest), skip_env_lock=bool(a.selftest_skip_env_lock), skip_a10=bool(a.selftest_skip_a10), configs=a.selftest_configs), gates_before_generation={kk: G[kk] for kk in REQUIRED if G[kk] is not None})
        producer["digest"] = hashlib.sha256(json.dumps(producer, sort_keys=True, default=str).encode()).hexdigest(); R["producer"] = producer
        env_rec = dict(python=env.get("python"), numpy=env.get("numpy"), scipy=env.get("scipy"), engine=__version__, fingerprint=hashlib.sha256(json.dumps(env, sort_keys=True, default=str).encode()).hexdigest(), producer=producer)
        from step1_engine.d2_bank import M as _M, M_FIT as _MF, M_W2 as _MW, BATCHES as _B, FIT_K as _FK, W2_K as _WK, _asha as _root_sha
        ledger = []; new_calls_before = 0
        def expected_request(name, kind, config_id, purpose, batch_id, roles, selections, root_arrays, family_):
            c_ = None if config_id is None else spec["configurations"][str(config_id)]
            if purpose == "evaluation": K_full = (_B[batch_id][1] - _B[batch_id][0]) // _M; mm = _M; group = group_for(table, "evaluation", family_)
            elif purpose == "fitting": K_full = _FK; mm = _MF; group = group_for(table, "fitting", family_)
            else: K_full = _WK; mm = _MW; group = c_["w2_primary"]["group"]
            K = K_full if scale == 1.0 else int(round(K_full * scale))
            return dict(name=name, kind=kind, family=family_, config_id=config_id, evaluation_ids=(None if c_ is None else c_["evaluation_ids"]), purpose=purpose, crn_group=group, wave_id=table["wave_id"], batch_id=batch_id, roles=sorted(roles), selections=list(selections), n_clusters=K, n_rows=K * mm, m=mm, scale=scale, formal=(scale == 1.0), root_sha256={r: _root_sha(np.asarray(v, float)) for r, v in root_arrays.items()}, covariance=(None if c_ is None else c_["covariance"]), table_sha256=table["table_sha256"], spec_sha256=spec["spec_sha256"], master_seed=table["master_seed"], environment_fingerprint=env_rec["fingerprint"], engine=__version__)
        def capture_metadata(dir_):
            # Caller-owned snapshot; validation below binds these exact bytes to
            # the real verifier/writer manifest before any request comparison.
            cb = open(os.path.join(dir_, "COMPLETE.json"), "rb").read()
            mc = json.loads(cb.decode("utf-8"))
            sb = {sh["sidecar"]: open(os.path.join(dir_, sh["sidecar"]), "rb").read() for sh in mc.get("shards", [])}
            return cb, mc, sb
        def check_metadata_snapshot(name, m_, cb, mc, side_bytes):
            payload = {kk: vv for kk, vv in mc.items() if kk != "manifest_sha256"}
            if mc.get("manifest_sha256") != m_["manifest_sha256"] or hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest() != m_["manifest_sha256"]:
                raise RuntimeError(f"cache {name}: captured completion manifest differs from the validated one")
            if set(side_bytes) != {sh["sidecar"] for sh in m_["shards"]}:
                raise RuntimeError(f"cache {name}: captured sidecar set differs from the validated manifest")
            for sh in m_["shards"]:
                if hashlib.sha256(side_bytes[sh["sidecar"]]).hexdigest() != sh["sidecar_sha256"]:
                    raise RuntimeError(f"cache {name}: captured sidecar {sh['sidecar']} differs from the validated manifest")
        def export_metadata_snapshot(name, cb, side_bytes):
            dep = os.path.join(a.out, "audit_dependencies", name); os.makedirs(dep, exist_ok=True)
            for rel, data in {"COMPLETE.json": cb, **side_bytes}.items():
                dest = os.path.join(dep, rel)
                with open(dest, "wb") as fh: fh.write(data)
                if hashlib.sha256(open(dest, "rb").read()).hexdigest() != hashlib.sha256(data).hexdigest():
                    raise RuntimeError(f"cache {name}: exported dependency metadata {rel} differs from the captured bytes")
            return dep
        def match_request(m_, req, side_bytes):
            """The completed cache must be THIS request: identity, ranges, roots, selections, scale/formal, table/spec, and the generation environment/engine of every shard."""
            keys = ("family", "config_id", "evaluation_ids", "purpose", "crn_group", "wave_id", "batch_id", "roles", "selections", "n_clusters", "n_rows", "m", "scale", "formal", "root_sha256", "table_sha256", "spec_sha256", "master_seed")
            diff = [k_ for k_ in keys if m_.get(k_) != req[k_]]
            if diff: raise RuntimeError(f"cache {req['name']}: differs from the current request on {diff}")
            for sh in m_["shards"]:
                side = json.loads(side_bytes[sh["sidecar"]].decode("utf-8")); e_ = side.get("environment") or {}
                if e_.get("fingerprint") != req["environment_fingerprint"] or e_.get("engine") != req["engine"]: raise RuntimeError(f"cache {req['name']}: generated under another environment / engine ({e_.get('engine')}, {str(e_.get('fingerprint'))[:12]}) than the current run")
                if req["covariance"] is not None and side.get("covariance") != req["covariance"]: raise RuntimeError(f"cache {req['name']}: covariance metadata differs")
                pr = e_.get("producer")
                if not isinstance(pr, dict):
                    if not selftest: raise RuntimeError(f"cache {req['name']}: no producer binding recorded (a cache without a producer record is never used for a formal run)")
                    req.setdefault("notes", []).append("self-test reuse of a cache without a producer record (never promotable to formal)"); continue
                for kk in ("modules", "script_sha256", "pins_sha256", "inventory_sha256", "crn_table_sha256", "spec_sha256", "engine_version"):
                    if pr.get(kk) != producer[kk]: raise RuntimeError(f"cache {req['name']}: produced by a different exact source ({kk} differs; engine version strings alone are not a source binding)")
                pp = pr.get("profile") or {}
                if pp.get("profile") != a.profile or pp.get("scale") != scale or (not selftest and (pp.get("selftest") or pp.get("skip_env_lock") or pp.get("skip_a10"))): raise RuntimeError(f"cache {req['name']}: produced under a different generation profile / self-test flags")
                gb = pr.get("gates_before_generation") or {}
                if not selftest and any(gb.get(kk) is not True for kk in ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_phaseC_members", "G_env_lock", "G_d1_trusted", "G_external_loader_sha", "G_crn_table", "G_bank_spec", "G_registry_bound", "G_calibration_bank_matches_a10")): raise RuntimeError(f"cache {req['name']}: produced without the required pre-generation gates")
        def reuse_or_generate(req, gen):
            """Completed directory from --reuse-root (fully re-verified AND matched to the expected request) or a fresh generation in OUT/name; every unit is entered in the ledger."""
            name = req["name"]
            if a.reuse_root and os.path.exists(os.path.join(a.reuse_root, name, "COMPLETE.json")):
                src = os.path.join(a.reuse_root, name)
                cb, mc, side_bytes = capture_metadata(src)
                m_ = verify_bank_dir(src)
                check_metadata_snapshot(name, m_, cb, mc, side_bytes)
                match_request(m_, req, side_bytes)
                dep = export_metadata_snapshot(name, cb, side_bytes)
                R["directories"][name] = dict(path=src, reused=True, dependency_metadata=dep, manifest_sha256=m_["manifest_sha256"], n_rows=m_["n_rows"], n_clusters=m_["n_clusters"], formal=m_["formal"], purpose=m_["purpose"], calls_source=m_["calls"], request=req); ledger.append(dict(name=name, satisfied_by="verified_reuse", manifest_sha256=m_["manifest_sha256"])); note(f"  reused {name} ({m_['n_rows']} rows; matched to the current request)"); return m_
            tt = time.time(); dest = os.path.join(a.out, name); m_ = gen(dest)
            cb, mc, side_bytes = capture_metadata(dest)
            check_metadata_snapshot(name, m_, cb, mc, side_bytes)
            match_request(m_, req, side_bytes)
            R["directories"][name] = dict(path=os.path.join(a.out, name), reused=False, manifest_sha256=m_["manifest_sha256"], n_rows=m_["n_rows"], n_clusters=m_["n_clusters"], formal=m_["formal"], purpose=m_["purpose"], seconds=time.time() - tt, request=req); ledger.append(dict(name=name, satisfied_by="new_generation", manifest_sha256=m_["manifest_sha256"])); note(f"  generated {name} ({m_['n_rows']} rows, {time.time()-tt:.0f}s)"); return m_
        from step1_engine.d2_rng import group_for
        # family reference (same latent as the configurations)
        fr = spec["family_reference"][fam]; ref_roots = dict(ref_matched=S_I)
        for b in (0, 1):
            sel_ = tuple(fr["selections"][str(b)]) if scale == 1.0 else ("float64",)
            reuse_or_generate(expected_request(f"ref_{fam}_b{b}", "family_reference", None, "evaluation", b, ("ref_matched",), sel_, ref_roots, fam), lambda d, b=b, sel_=sel_: generate_configuration_bank(k, registry, table, spec, None, ref_roots, b, d, inv, sel_, scale=scale, env=env_rec, family=fam))
        reuse_or_generate(expected_request(f"ref_{fam}_fit", "family_reference", None, "fitting", 0, ("ref_matched",), ("float64",), ref_roots, fam), lambda d: generate_fitting_bank(k, registry, table, spec, None, ref_roots, d, inv, scale=scale, env=env_rec, family=fam)); G["G_family_reference"] = True
        n_done = 0
        for c in cfgs:
            if sel_ids is not None and c.config_id not in sel_ids: continue
            tt = time.time(); cov = intake_registered_covariance(c.config_id, reg, d1dir, a.mt); from step1_engine.d2_rng import native_reference_root
            roots = dict(model_matched=cov["S_matched"], model_native=cov["S_native"], ref_native=native_reference_root(cov["c_ct"])); sc = spec["configurations"][str(c.config_id)]; cr = ("model_matched", "model_native", "ref_native")
            for b in (0, 1):
                sel_ = tuple(sc["selections"]["evaluation"][str(b)]) if scale == 1.0 else ("float64",)
                reuse_or_generate(expected_request(f"cfg{c.config_id}_b{b}", "configuration", c.config_id, "evaluation", b, cr, sel_, roots, fam), lambda d, b=b, sel_=sel_: generate_configuration_bank(k, registry, table, spec, c.config_id, roots, b, d, inv, sel_, scale=scale, env=env_rec))
            reuse_or_generate(expected_request(f"cfg{c.config_id}_fit", "configuration", c.config_id, "fitting", 0, cr, ("float64",), roots, fam), lambda d: generate_fitting_bank(k, registry, table, spec, c.config_id, roots, d, inv, scale=scale, env=env_rec))
            if sc["w2_primary"] is not None: reuse_or_generate(expected_request(f"cfg{c.config_id}_w2", "configuration", c.config_id, "w2_independent", 0, ("model_matched",), ("float64", "float32"), dict(model_matched=cov["S_matched"]), fam), lambda d: generate_w2_position_bank(k, registry, table, spec, c.config_id, cov["S_matched"], d, inv, scale=scale, env=env_rec))
            R["timings"][str(c.config_id)] = time.time() - tt; n_done += 1; note(f"config {c.config_id} done ({time.time()-tt:.0f}s)")
        # required request set (this family, selected configurations) vs the ledger: every unit satisfied by a new generation or a verified reuse, with formal == official scope
        required = [f"ref_{fam}_b0", f"ref_{fam}_b1", f"ref_{fam}_fit"] + [f"cfg{c.config_id}_{x}" for c in cfgs if sel_ids is None or c.config_id in sel_ids for x in (["b0", "b1", "fit"] + (["w2"] if spec["configurations"][str(c.config_id)]["w2_primary"] is not None else []))]
        done = {e["name"] for e in ledger}; all_formal = all(R["directories"][n_]["formal"] is True for n_ in done)
        G["G_all_configurations"] = bool(set(required) == done and (all_formal or scale < 1.0)); R["ledger"] = ledger; R["required_requests"] = required
        regj = dict(schema="d2_bank_registry_v1", family=fam, scale=scale, formal=(scale == 1.0 and not selftest and all_formal and set(required) == done), table_sha256=table["table_sha256"], spec_sha256=spec["spec_sha256"], registry_sha256=reg.registry_sha256, directories=R["directories"], required_requests=required, ledger=ledger, calls=inv.calls, calls_reused={n_: v.get("calls_source") for n_, v in R["directories"].items() if v.get("reused")}, environment=env_rec, engine_version=__version__, d1_receipt_sha256=D1_REGISTERED_RECEIPT["receipt_file_sha256"], loader=R.get("loader"), a10_reference_sha256=R.get("a10_reference_sha256"))
        json.dump(regj, open(os.path.join(a.out, "d2_bank_registry.json"), "w"), indent=1, default=str); G["G_registry_saved"] = True
        return finish(0 if all(G[kk] is True for kk in REQUIRED) else 1, "complete")
    except Exception as ex:
        R["failures"].append("exception: " + repr(ex)); R["traceback"] = traceback.format_exc(); note(R["traceback"])
        try: json.dump(dict(schema="d2_bank_registry_v1", status="PARTIAL_AFTER_FAILURE", family=a.family, directories=R["directories"]), open(os.path.join(a.out, "d2_bank_registry.json"), "w"), indent=1, default=str)
        except Exception: pass
        return finish(1, "exception")


if __name__ == "__main__": sys.exit(main())
