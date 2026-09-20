# -*- coding: utf-8 -*-
"""Phase D-1 v0.2 (pre-execution audit RD1-A/B/C): production covariance generation and intake for the registered first-wave grid (30 configurations; rules §4.7, §5; A11 rules R1/R6).
Generator = the A11 registered procedure (frozen notebook v1.4.1 cell 4: key_of / tag_of / ensure_cov, reproduced verbatim below with the cell SHA recorded): pinned CMBtopology
0cc65e34 (fresh clean checkout), run_config l_max=4 / TT / [2,4], tag-specific scratch, atomic cache with manifest (topology, params, x0, run_config, commit, requirements SHA,
env fingerprint), cov file SHA + array SHA. x0_CT = -r_obs from the source-bound registry / first-wave configuration manifest (A11 R1); E1 is homogeneous (no x0).
Intake per covariance (pre-use gate 'production covariance intake'): geometry binding of the cov manifest to the ConfigurationSpec (grid_manifest.verify_cov_manifest),
run profile == registered, commit / requirements / env fingerprint == this run's lock, array SHA recomputed from the file, t1_engine.load_cov_full (reality, real-basis transform,
symmetry, PSD/eigenvalue report), matched/native principal square roots (clip=0, lambda_min>0) — recorded per configuration. A11 cross-check: ONE frozen A11 official entry
(E7 tilted case) is regenerated in this environment and compared with the frozen array (rel Frobenius; bit identity recorded separately). Required gates are an exact inventory;
D1_PASS only in --profile production_official. Contracts (v0.2): (A) the registered numerical environment (rules §12.1: Python/NumPy/SciPy/healpy/POT/CAMB versions, NumPy-owned
OpenBLAS pool = 2, other pools <= 2) is a HARD gate checked in the generating process before any generation (thread env set before numpy import; threadpoolctl controller retained);
the A11-style fingerprint / lock diff is recorded separately as metadata. (B) trusted inputs are bound BEFORE generation: Phase C packet members (inventory listing re-read, every member
SHA/size/set), the saved first-wave grid (deserialised, validate(), payload SHA == rebuilt from A6/A7), frozen t1_engine / t2b2_bridge SHAs at the actual import path, the A11 freeze files,
the A11 generator cell source (extracted from the frozen notebook, full SHA == pins) and the A11 cross-check target (manifest / npy / raw array SHAs == pins). (C) fail-fast: the first intake
failure stops the run (partial registry with the failing config and reason saved; non-zero exit); OUT must be a fresh empty directory (refused before any log/record is touched).
Evidence: cov_cache (npy + manifest per configuration), d1_cov_registry.json, d1_env_lock.json, run manifest with output inventory."""
from __future__ import annotations
import os
for _k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"): os.environ.setdefault(_k, "2")   # before numpy import (registered pool sizes; verified live below)
import argparse, glob, hashlib, json, shutil, subprocess, sys, time, platform, traceback
import numpy as np

REQUIRED = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_phaseC_members", "G_external_loader_sha", "G_a11_freeze_sha", "G_a11_generator_cell_sha", "G_env_lock", "G_ct_commit", "G_ct_origin", "G_ct_clean", "G_ct_dependencies_present",
            "G_registry_source_bound", "G_grid_manifest_bound", "G_a11_cross_check_target", "G_a11_cross_check", "G_all_configurations_generated", "G_all_intakes_pass", "G_evidence_saved")
A11_CELL4_SHA = "ab1fc4dc62f9cd01"   # first 16 hex of sha256 of the frozen A11 v1.4.1 notebook cell-4 source (generator); full value recorded in the run manifest
EXPECTED_CMBTOPO_COMMIT = "0cc65e34f03df85e92f738686bff0a476132f337"
LMAX = 4; RUN_CFG = dict(l_max=LMAX, do_polarization=False, normalize=False, l_range=[[2, LMAX]], lp_range=[[2, LMAX]])
PKGS = ["numpy", "scipy", "matplotlib", "healpy", "camb", "tqdm", "numba", "quaternionic", "spherical", "pandas"]


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mt", required=True); ap.add_argument("--phaseb", required=True); ap.add_argument("--phasec", required=True); ap.add_argument("--ct", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--profile", default="production_official"); ap.add_argument("--selftest-configs", default=None, help="sandbox: comma list of config_ids (never issues D1_PASS)"); ap.add_argument("--selftest-skip-cross-check", action="store_true"); ap.add_argument("--selftest-skip-env-lock", action="store_true", help="sandbox only: record G_env_lock=False and continue (never issues D1_PASS)")
    a = ap.parse_args(); t0 = time.time()
    if os.path.exists(a.out) and os.listdir(a.out): print("OUT must be a fresh (empty) directory (fresh-only contract: no reuse, no overwrite of a previous run record)", file=sys.stderr); return 2
    os.makedirs(a.out, exist_ok=True); CACHE = os.path.join(a.out, "cov_cache"); os.makedirs(CACHE, exist_ok=True); SCRATCH = os.path.join(a.out, "scratch"); os.makedirs(SCRATCH, exist_ok=True)
    log = open(os.path.join(a.out, "d1_covgen_stdout.log"), "w"); G = {k: None for k in REQUIRED}; R = dict(stage="init", failures=[], timings={}); selftest = a.selftest_configs is not None or a.selftest_skip_cross_check or a.selftest_skip_env_lock
    def note(*s):
        m = " ".join(str(x) for x in s); print(m, flush=True)
        try: log.write(m + "\n"); log.flush()
        except ValueError: pass
    def finish(code, stage="final"):
        R["stage"] = stage; R["gates"] = G; R["required_inventory"] = list(REQUIRED); R["required_all_true"] = all(G.get(k) is True for k in REQUIRED); R["D1_PASS"] = bool(R["required_all_true"] and a.profile == "production_official" and not selftest and code == 0); R["seconds"] = time.time() - t0
        note("D1_PASS =", R["D1_PASS"], "| stage:", stage, "| gates:", json.dumps(G)); log.close()
        inv = {}
        for d, _, fs in os.walk(a.out):
            for f in fs:
                p = os.path.join(d, f); rel = os.path.relpath(p, a.out)
                if rel != "d1_run_manifest.json" and not rel.startswith("scratch"): inv[rel] = dict(sha256=sha(p), bytes=os.path.getsize(p))
        R["output_inventory"] = inv; tmp = os.path.join(a.out, "d1_run_manifest.json.tmp"); open(tmp, "w").write(json.dumps(R, indent=1, ensure_ascii=False, default=str)); os.replace(tmp, os.path.join(a.out, "d1_run_manifest.json")); print("run manifest written; D1_PASS =", R["D1_PASS"]); return code
    try:
        if a.profile != "production_official": R["failures"].append("profile must be 'production_official'"); return finish(1)
        sys.path.insert(0, a.phaseb); sys.path.insert(0, a.mt)
        pins_path = os.path.join(a.phaseb, "d", "d1_pins.json"); pins = json.load(open(pins_path)); R["pins_sha256"] = sha(pins_path); inv0 = json.load(open(os.path.join(a.phaseb, "B2_completion_inventory.json")))
        G["G_pins_loaded"] = bool(pins.get("schema") == "d1_pins_v1" and inv0.get("d_sha256", {}).get("d/d1_pins.json") == R["pins_sha256"])
        from step1_engine import __version__; from step1_engine.checkpoint import module_shas
        G["G_engine_inventory"] = (inv0["modules"] == module_shas() and inv0["engine_version"] == __version__ == pins["engine_version"]); me = os.path.abspath(__file__); G["G_script_sha"] = (inv0.get("d_sha256", {}).get("d/d1_covgen.py") == sha(me)); R["engine_version"] = __version__
        if not (G["G_pins_loaded"] and G["G_engine_inventory"] and G["G_script_sha"]): R["failures"].append("preflight binding failed"); return finish(1, "preflight")
        # ---- (B) trusted inputs, all cheap, BEFORE any generation
        pc = json.load(open(os.path.join(a.phasec, "PACKET_INVENTORY.json"))); pc_ok = sha(os.path.join(a.phasec, "PACKET_INVENTORY.json")) == pins["first_wave"]["phaseC_inventory_sha256"]
        members = {}
        for d, _, fs in os.walk(a.phasec):
            for f in fs:
                rel = os.path.relpath(os.path.join(d, f), a.phasec)
                if rel != "PACKET_INVENTORY.json" and "__pycache__" not in rel: members[rel] = dict(sha256=sha(os.path.join(d, f)), bytes=os.path.getsize(os.path.join(d, f)))
        G["G_phaseC_members"] = bool(pc_ok and set(members) == set(pc["files"]) and all(members[k] == dict(sha256=v["sha256"], bytes=v["bytes"]) for k, v in pc["files"].items()) and pc.get("handoff_commit") == pins["first_wave"]["phaseC_handoff_commit"])
        R["phaseC_members"] = dict(inventory_sha_ok=pc_ok, n_listed=len(pc["files"]), n_present=len(members), all_match=G["G_phaseC_members"])
        ext = pins["external_sources"]; ext_ok = {}
        for name, e in ext.items(): p = os.path.join(a.mt, e["path"]); ext_ok[name] = (os.path.exists(p) and sha(p) == e["sha256"])
        G["G_external_loader_sha"] = all(ext_ok.values()); R["external_sources"] = ext_ok
        A11 = pins["a11_freeze"]; G["G_a11_freeze_sha"] = all(sha(os.path.join(a.mt, A11[k]["path"])) == A11[k]["sha256"] for k in ("notebook", "env_lock", "rules"))
        nb = json.load(open(os.path.join(a.mt, A11["notebook"]["path"]))); cell4 = "".join(nb["cells"][A11["generator_cell_index"]]["source"]); cell4_sha = hashlib.sha256(cell4.encode()).hexdigest()
        G["G_a11_generator_cell_sha"] = (cell4_sha == A11["generator_cell4_sha256"]); R["a11_generator_cell4_sha256"] = cell4_sha
        xc = pins["a11_cross_check"]; xmp = os.path.join(a.mt, xc["manifest"]); xnpy = os.path.join(a.mt, xc["npy"])
        G["G_a11_cross_check_target"] = bool(os.path.exists(xmp) and os.path.exists(xnpy) and sha(xmp) == xc["manifest_sha256"] and sha(xnpy) == xc["npy_sha256"] and hashlib.sha256(np.load(xnpy).tobytes()).hexdigest() == xc["array_sha256"] and json.load(open(xmp))["cov_array_sha256"] == xc["array_sha256"])
        if not (G["G_phaseC_members"] and G["G_external_loader_sha"] and G["G_a11_freeze_sha"] and G["G_a11_generator_cell_sha"] and G["G_a11_cross_check_target"]): R["failures"].append("trusted-input binding failed (Phase C members / external loader / A11 freeze / generator cell / cross-check target)"); return finish(1, "trusted_inputs")
        # ---- registry / grid manifest (source-bound) and the first-wave configurations
        from step1_engine.grid_registry import load_registry; from step1_engine.grid_manifest import build_configuration_manifest, verify_cov_manifest, ConfigurationSpec
        reg = load_registry(os.path.join(a.phaseb, "tests/assets/a7_circle_geometry.csv"), os.path.join(a.phaseb, "tests/assets/a6_observer_design_points.json")); G["G_registry_source_bound"] = reg.verification_scope.startswith("constructed_from_verified_assets") or reg.verification_scope.startswith("source_bound")
        from step1_engine.grid_manifest import ConfigurationManifest; from step1_engine import serialization as ser
        man = build_configuration_manifest(reg); fwd = ser.from_jsonable(json.load(open(os.path.join(a.phasec, "registered", "first_wave_configuration_manifest.json"))))
        saved = ConfigurationManifest(schema=fwd["schema"], registry_sha256=fwd["registry_sha256"], lift_source=fwd["lift_source"], configurations=[ConfigurationSpec(**c) for c in fwd["configurations"]], n_configurations=fwd["n_configurations"], manifest_sha256=fwd["manifest_sha256"])
        saved_ok = False
        try: saved_ok = bool(saved.validate() and saved.payload_sha() == saved.manifest_sha256 == man.manifest_sha256 == man.payload_sha() and saved.as_dict() == man.as_dict())
        except Exception as ex: R["saved_grid_error"] = repr(ex)
        G["G_grid_manifest_bound"] = bool(saved_ok and man.manifest_sha256 == pins["first_wave"]["manifest_sha256"] and man.registry_sha256 == reg.registry_sha256 == pins["first_wave"]["registry_sha256"] and saved.registry_sha256 == reg.registry_sha256)
        if not (G["G_registry_source_bound"] and G["G_grid_manifest_bound"]): R["failures"].append("registry / grid manifest binding failed"); return finish(1, "grid")
        # ---- (A) registered numerical environment: HARD gate in this process (live versions + pools), before generation
        from step1_engine.official_gate import current_env, _blas_check
        env = current_env(); ex = pins["environment"]
        try:
            import camb as _camb; env["camb"] = _camb.__version__
        except Exception: env["camb"] = None
        vers_ok = all(env.get(k) == ex[k] for k in ("python", "numpy", "scipy", "healpy", "pot", "camb")); blas_ok = bool(_blas_check(env.get("blas_threads")))
        try:
            import threadpoolctl; TPC = threadpoolctl.threadpool_limits(limits=2)                       # controller kept alive for the whole run
        except Exception: TPC = None
        G["G_env_lock"] = bool(vers_ok and blas_ok); R["env"] = env; R["env_gate"] = dict(versions_ok=vers_ok, pools_ok=blas_ok, expected=ex, threadpoolctl=(TPC is not None))
        if not G["G_env_lock"] and not a.selftest_skip_env_lock: R["failures"].append(f"registered environment gate failed: versions_ok={vers_ok} pools_ok={blas_ok} live={ {k: env.get(k) for k in ex} }"); return finish(1, "environment")
        # ---- pinned CMBtopology (fresh checkout by the launcher; verified here again)
        def git_probe(args):
            result = subprocess.run(["git", "-C", a.ct, *args], capture_output=True, text=True)
            item = dict(args=args, returncode=result.returncode,
                        stdout=result.stdout.strip(), stderr=result.stderr.strip())
            R.setdefault("ct_git_probes", []).append(item)
            return item
        ct_head = git_probe(["rev-parse", "HEAD"])
        ct_origin = git_probe(["remote", "get-url", "origin"])
        ct_status = git_probe(["status", "--porcelain", "--untracked-files=all"])
        G["G_ct_commit"] = bool(ct_head["returncode"] == 0 and ct_head["stdout"] == EXPECTED_CMBTOPO_COMMIT)
        G["G_ct_origin"] = bool(ct_origin["returncode"] == 0 and ct_origin["stdout"].rstrip("/").removesuffix(".git") == "https://github.com/CompactCollaboration/CMBtopology")
        G["G_ct_clean"] = bool(ct_status["returncode"] == 0 and ct_status["stdout"] == "")
        if not (G["G_ct_commit"] and G["G_ct_origin"] and G["G_ct_clean"]):
            R["failures"].append("CMBtopology Git query failed or checkout identity/clean-tree check failed")
            return finish(1, "external")
        REQ_TXT = os.path.join(a.ct, "requirements.txt"); REQ_SHA = sha(REQ_TXT); CT_SRC_SHA = {f: sha(os.path.join(a.ct, "topology", p)) for f, p in [("E1.py", "src/E1.py"), ("E2.py", "src/E2.py"), ("E7.py", "src/E7.py"), ("E8.py", "src/E8.py"), ("run_topology.py", "run_topology.py")]}
        from importlib.metadata import version as pkg_version, PackageNotFoundError
        def pkgver(n):
            try: return pkg_version(n)
            except PackageNotFoundError: return "MISSING"
        VERS = {n: pkgver(n) for n in PKGS}; G["G_ct_dependencies_present"] = all(v != "MISSING" for v in VERS.values()); PYV = sys.version.split()[0]
        BLAS = str({k: v.get("name") for k, v in np.show_config(mode="dicts").get("Build Dependencies", {}).items() if k in ("blas", "lapack")}); PLATFORM = dict(machine=platform.machine(), platform=platform.platform())
        ENV_FINGERPRINT = hashlib.sha256(json.dumps(dict(python=PYV, versions=VERS, requirements_sha256=REQ_SHA, platform=PLATFORM, blas_lapack=BLAS, ct_commit=EXPECTED_CMBTOPO_COMMIT, run_config=RUN_CFG), sort_keys=True).encode()).hexdigest()
        a11lock = json.load(open(os.path.join(a.mt, A11["env_lock"]["path"]))); same_env = (a11lock["python"] == PYV and a11lock["versions"] == VERS and a11lock["requirements_sha256"] == REQ_SHA and a11lock["blas_lapack"] == BLAS and a11lock["platform"] == PLATFORM)
        R["env_lock"] = dict(schema="d1_env_lock_v1", python=PYV, versions=VERS, requirements_sha256=REQ_SHA, platform=PLATFORM, blas_lapack=BLAS, cmbtopology_commit=EXPECTED_CMBTOPO_COMMIT, ct_src_sha256=CT_SRC_SHA, env_fingerprint=ENV_FINGERPRINT, identical_to_a11_lock=bool(same_env), a11_lock_diff={k: (a11lock.get(k), v) for k, v in dict(python=PYV, versions=VERS, requirements_sha256=REQ_SHA, blas_lapack=BLAS, platform=PLATFORM).items() if a11lock.get(k) != v})
        json.dump(R["env_lock"], open(os.path.join(a.out, "d1_env_lock.json"), "w"), indent=1)
        if not (G["G_ct_commit"] and G["G_ct_origin"] and G["G_ct_clean"] and G["G_ct_dependencies_present"]): R["failures"].append("CMBtopology binding failed"); return finish(1, "external")
        sys.path.insert(0, a.ct); from topology.run_topology import run_topology; import t1_engine as t1
        if sha(t1.__file__) != ext["t1_engine"]["sha256"]: R["failures"].append("imported t1_engine differs from the pinned frozen loader"); G["G_external_loader_sha"] = False; return finish(1, "external")
        assert RUN_CFG == pins["run_config"], "registered run_config differs from the script constant"
        # ---- registered generator (A11 v1.4.1 cell 4, verbatim except the SCRATCH/CACHE names)
        def key_of(top, p, x0): return dict(topology=top, params={k: float(v) for k, v in p.items()}, x0=[float(v) for v in x0], run_config=RUN_CFG, cmbtopology_commit=EXPECTED_CMBTOPO_COMMIT, requirements_sha256=REQ_SHA, env_fingerprint=ENV_FINGERPRINT)
        def tag_of(top, p, x0): return top + "_" + hashlib.sha256(json.dumps(key_of(top, p, x0), sort_keys=True).encode()).hexdigest()
        def atomic_write_json(obj, path):
            tmp = path + ".tmp"
            with open(tmp, "w") as fh: json.dump(obj, fh, indent=1); fh.flush(); os.fsync(fh.fileno())
            os.replace(tmp, path)
        def ensure_cov(top, p, x0):
            tag = tag_of(top, p, x0); f = os.path.join(CACHE, f"cov_{tag[:20]}.npy"); mf = f + ".manifest.json"
            if os.path.exists(f) != os.path.exists(mf):
                for q in (f, mf):
                    if os.path.exists(q): os.remove(q)
            if os.path.exists(f):
                rec = json.load(open(mf)); assert rec["manifest"] == key_of(top, p, x0) and rec["tag"] == tag, tag; assert sha(f) == rec["cov_file_sha256"], f"reuse SHA mismatch: {tag}"; return f, tag, rec
            scratch = os.path.join(SCRATCH, tag[:20]); shutil.rmtree(scratch, ignore_errors=True); os.makedirs(scratch); cwd0 = os.getcwd(); tt = time.time()
            try:
                os.chdir(scratch)
                kw = dict(p)
                if top != "E1": kw["x0"] = np.array(x0, float)
                run_topology(topology=top, l_max=LMAX, do_polarization=False, normalize=False, l_range=np.array([[2, LMAX]]), lp_range=np.array([[2, LMAX]]), **kw)
                dirs = glob.glob("runs/*"); assert len(dirs) == 1, dirs; d = dirs[0]
                src = os.path.join(d, f"TT_corr_matrix_l_2_{LMAX}_lp_2_{LMAX}.npy"); assert os.path.exists(src), src
                tmp = f + ".tmp"; shutil.copy(src, tmp)
                with open(tmp, "rb") as fh: os.fsync(fh.fileno())
                os.replace(tmp, f)
            finally: os.chdir(cwd0)
            rec = dict(tag=tag, manifest=key_of(top, p, x0), cov_file_sha256=sha(f), cov_array_sha256=hashlib.sha256(np.load(f).tobytes()).hexdigest(), source_run_dir=os.path.basename(d.rstrip("/")), seconds=time.time() - tt)
            atomic_write_json(rec, mf); note(f"  generated {tag[:20]} ({time.time()-tt:.0f}s)"); return f, tag, rec
        # ---- A11 cross-check (one frozen official entry regenerated here)
        xman = json.load(open(xmp))
        if a.selftest_skip_cross_check: G["G_a11_cross_check"] = None; R["a11_cross_check"] = dict(skipped="selftest")
        else:
            tt = time.time(); f_, tag_, rec_ = ensure_cov(xman["manifest"]["topology"], xman["manifest"]["params"], xman["manifest"]["x0"]); A_new = np.load(f_); A_old = np.load(xnpy); rel = float(np.linalg.norm(A_new - A_old) / np.linalg.norm(A_old))
            R["a11_cross_check"] = dict(entry=xc["manifest"], frozen_array_sha256=xman["cov_array_sha256"], regenerated_array_sha256=rec_["cov_array_sha256"], bit_identical=bool(rec_["cov_array_sha256"] == xman["cov_array_sha256"]), rel_frobenius=rel, tolerance=float(xc["rel_tolerance"]), same_env_as_a11=bool(same_env), seconds=time.time() - tt)
            G["G_a11_cross_check"] = bool(rel <= float(xc["rel_tolerance"]))
            if not G["G_a11_cross_check"]: R["failures"].append(f"A11 cross-check failed: rel={rel}"); return finish(1, "cross_check")
        specs = list(man.configurations); sel = None if a.selftest_configs is None else {int(x) for x in a.selftest_configs.split(",")}
        registry_out = {}; n_ok = 0; n_gen = 0
        for s in specs:
            if sel is not None and s.config_id not in sel: continue
            tt = time.time(); f = tag = rec = None; operation = "configuration_start"
            try:
                operation = "covariance_generation"
                f, tag, rec = ensure_cov(s.family, s.shape_params, s.x0_CT); n_gen += 1
                # ---- production intake
                operation = "geometry_binding"
                geo = verify_cov_manifest(s, rec, f)
                operation = "load_cov_full"
                Mx, Cr, meta = t1.load_cov_full(f, LMAX)
                operation = "numerical_intake"
                arr_sha = hashlib.sha256(np.load(f).tobytes()).hexdigest(); ev = np.linalg.eigvalsh((Cr + Cr.T) / 2); psd = bool(ev.min() > -1e-12 * ev.max())
                from step1_engine.legacy_kernel import LegacyKernel
                k = LegacyKernel(a.mt); C_M, c_ct = k.matched(Cr); S_M, iM = k.psqrt(C_M); S_N, iN = k.psqrt(Cr)
                roots_ok = all(v["clip"] == 0 and v["lambda_min"] > 0 and v["sym"] < 1e-12 and v["recon"] < 1e-10 for v in (iM, iN))
                ok = bool(geo["bound"] and geo["file_sha_verified"] and rec["manifest"]["run_config"] == RUN_CFG and rec["manifest"]["cmbtopology_commit"] == EXPECTED_CMBTOPO_COMMIT and rec["manifest"]["requirements_sha256"] == REQ_SHA and rec["manifest"]["env_fingerprint"] == ENV_FINGERPRINT and arr_sha == rec["cov_array_sha256"] and meta.get("cov_array_sha256") == arr_sha and Cr.shape == (21, 21) and psd and roots_ok)
                n_ok += int(ok)
                if not ok: fail_reason = dict(config_id=s.config_id, geometry=geo, run_profile_ok=(rec["manifest"]["run_config"] == RUN_CFG), env_fingerprint_ok=(rec["manifest"]["env_fingerprint"] == ENV_FINGERPRINT), array_sha_ok=(arr_sha == rec["cov_array_sha256"]), psd=psd, roots_ok=roots_ok)
                registry_out[str(s.config_id)] = dict(config_id=s.config_id, family=s.family, size_id=s.size_id, observer_id=s.observer_id, cache_key=s.cache_key, tag=tag, cov_file=os.path.relpath(f, a.out), cov_file_sha256=rec["cov_file_sha256"], cov_array_sha256=rec["cov_array_sha256"], x0_CT=list(map(float, s.x0_CT)), shape_params=s.shape_params,
                                                     intake=dict(pass_=ok, geometry=geo, run_profile_ok=(rec["manifest"]["run_config"] == RUN_CFG), env_fingerprint_ok=(rec["manifest"]["env_fingerprint"] == ENV_FINGERPRINT), array_sha_recomputed_ok=(arr_sha == rec["cov_array_sha256"]), psd=psd, eig_min=float(ev.min()), eig_max=float(ev.max()), c_ct=c_ct.tolist(), sqrt_matched=iM, sqrt_native=iN, loader_meta={kk: (vv if isinstance(vv, (int, float, str, bool, list, dict)) else str(vv)) for kk, vv in meta.items()}), seconds=time.time() - tt)
                note(f"config {s.config_id} {s.family}/{s.size_id}/obs{s.observer_id}: intake {'PASS' if ok else 'FAIL'} ({time.time()-tt:.0f}s)")
            except Exception as ex:
                detail = dict(config_id=s.config_id, family=s.family, size_id=s.size_id,
                              observer_id=s.observer_id, operation=operation,
                              error_type=type(ex).__name__, error=repr(ex),
                              traceback=traceback.format_exc())
                registry_out[str(s.config_id)] = dict(
                    config_id=s.config_id, family=s.family, size_id=s.size_id,
                    observer_id=s.observer_id, cache_key=s.cache_key,
                    shape_params=s.shape_params, x0_CT=list(map(float, s.x0_CT)),
                    cov_file=os.path.relpath(f, a.out) if f is not None else None,
                    tag=tag, intake=dict(pass_=False, failure=detail), seconds=time.time()-tt)
                atomic_write_json(dict(schema="d1_cov_registry_v1",
                                       status="STOPPED_AT_INTAKE_FAILURE",
                                       registry_sha256=reg.registry_sha256,
                                       grid_manifest_sha256=man.manifest_sha256,
                                       failed=detail, configurations=registry_out,
                                       n=len(registry_out)), os.path.join(a.out, "d1_cov_registry.json"))
                R["failures"].append(f"config {s.config_id} failed at {operation}: {ex!r}; stopped")
                R["failed_configuration"] = detail
                R["n_generated"] = n_gen; R["n_intake_pass"] = n_ok
                G["G_all_intakes_pass"] = False; G["G_all_configurations_generated"] = False
                G["G_evidence_saved"] = True
                note(detail["traceback"])
                return finish(1, "intake_exception")
            if not ok:                                                                                          # (C) fail-fast: no further expensive generation after a failed intake
                json.dump(dict(schema="d1_cov_registry_v1", status="STOPPED_AT_INTAKE_FAILURE", failed=fail_reason, configurations=registry_out, n=len(registry_out)), open(os.path.join(a.out, "d1_cov_registry.json"), "w"), indent=1)
                R["failures"].append(f"intake failed for config {s.config_id}; run stopped (fail-fast)"); R["n_generated"] = n_gen; R["n_intake_pass"] = n_ok; G["G_all_intakes_pass"] = False; G["G_all_configurations_generated"] = False; G["G_evidence_saved"] = True
                return finish(1, "intake_failure")
        expected_n = len(specs) if sel is None else len(sel); G["G_all_configurations_generated"] = (n_gen == expected_n == (30 if sel is None else expected_n)); G["G_all_intakes_pass"] = (n_ok == n_gen)
        json.dump(dict(schema="d1_cov_registry_v1", registry_sha256=reg.registry_sha256, grid_manifest_sha256=man.manifest_sha256, env_fingerprint=ENV_FINGERPRINT, cmbtopology_commit=EXPECTED_CMBTOPO_COMMIT, run_config=RUN_CFG, configurations=registry_out, n=len(registry_out), scope=("SELFTEST subset" if sel else "first-wave 30 configurations")), open(os.path.join(a.out, "d1_cov_registry.json"), "w"), indent=1)
        R["a11_cell4_sha256"] = cell4_sha; R["n_generated"] = n_gen; R["n_intake_pass"] = n_ok; G["G_evidence_saved"] = all(os.path.exists(os.path.join(a.out, f)) for f in ("d1_cov_registry.json", "d1_env_lock.json"))
        shutil.rmtree(SCRATCH, ignore_errors=True)
        return finish(0 if all(G[k] is True for k in REQUIRED) else 1, "complete")
    except Exception as ex:
        R["failures"].append("exception: " + repr(ex)); R["traceback"] = traceback.format_exc(); note(R["traceback"]); return finish(1, "exception")


if __name__ == "__main__": sys.exit(main())
