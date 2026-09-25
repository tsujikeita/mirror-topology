# -*- coding: utf-8 -*-
"""Phase D-3 tranche 2a: production covariance generation for the 12-position stage (81 new base configurations) + PC-1 physical clone verification (108 new-point cases +
36 first-wave anchor diagnostics), one family per invocation. Generator, intake, environment hard gate, trusted-input binding and fail-fast contracts are those of the accepted
D-1 script (d1_covgen.py v0.3; A11 registered generator reproduced verbatim). Inputs are bound before any generation: pins / inventory / script; Phase C members; registered
environment; D-1 receipt / registry constants; frozen loader + bridge; the D-3 config map and PC-1 case table (both re-derived from the bound registry / manifest / twelve asset /
trusted A11 + CT sources and compared for equality); CMBtopology pinned checkout.
PC-1 evaluation (contract d3_stage.PC1_CONTRACT, transcribed from A11 R2/R5): base C0 (new: generated here; anchor: the D-1 covariance by fixed SHA), clone C1 generated
INDEPENDENTLY at x0_H1 = M b - T, both loaded with the frozen real-basis transform; D(M) = (YQ*WQ)^T Ymat(DIRS @ M) (A11 cell 2, LMAX=4 quadrature); rel = ||C1 - D C0 D^T||_F /
||D C0 D^T||_F; PC1_PASS iff rel < 1e-5 for EVERY required action of the configuration; also rel_H2 (alternative x0 = M b + T; discriminating diagnostic; generated only when
--with-h2) and rel_off / rel_white diagnostics. Statuses are asset-layer; nothing is converted to position states. D3_PASS only for the formal profile with every base intake
passing and every case evaluated (PC1_FAIL cases do NOT block the run record; they block formal consumption of the affected configurations)."""
from __future__ import annotations
import os
for _k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"): os.environ.setdefault(_k, "2")
import argparse, glob, hashlib, json, shutil, subprocess, sys, time, platform, traceback
import numpy as np

REQUIRED = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_phaseC_members", "G_external_loader_sha", "G_a11_freeze_sha", "G_a11_generator_cell_sha", "G_env_lock", "G_ct_commit", "G_ct_origin", "G_ct_clean", "G_ct_dependencies_present",
            "G_registry_source_bound", "G_config_map_bound", "G_case_table_bound", "G_d1_trusted", "G_bridge_quadrature", "G_all_bases_generated", "G_all_base_intakes_pass", "G_all_cases_evaluated", "G_evidence_saved")
EXPECTED_CMBTOPO_COMMIT = "0cc65e34f03df85e92f738686bff0a476132f337"
LMAX = 4; RUN_CFG = dict(l_max=LMAX, do_polarization=False, normalize=False, l_range=[[2, LMAX]], lp_range=[[2, LMAX]])
PKGS = ["numpy", "scipy", "matplotlib", "healpy", "camb", "tqdm", "numba", "quaternionic", "spherical", "pandas"]


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mt", required=True); ap.add_argument("--phaseb", required=True); ap.add_argument("--phasec", required=True); ap.add_argument("--ct", required=True); ap.add_argument("--out", required=True); ap.add_argument("--family", required=True)
    ap.add_argument("--profile", default="production_official"); ap.add_argument("--with-h2", action="store_true", help="also generate the H2 alternative clone (diagnostic; doubles clone cost)")
    ap.add_argument("--sizes", default=None, help="FORMAL size partition of the family run, e.g. L1.00 or L1.00,L1.20: all new configurations AND the first-wave anchor cases of those sizes; recorded as partition (family PASS = aggregation of the registered partitions)")
    ap.add_argument("--selftest-configs", default=None); ap.add_argument("--selftest-skip-env-lock", action="store_true"); ap.add_argument("--selftest-skip-pc1", action="store_true"); ap.add_argument("--selftest-skip-anchors", action="store_true", help="SELF-TEST ONLY: omit the anchor cases of the selected sizes (never a formal partition)")
    a = ap.parse_args(); t0 = time.time()
    if os.path.exists(a.out) and os.listdir(a.out): print("OUT must be a fresh (empty) directory", file=sys.stderr); return 2
    os.makedirs(a.out, exist_ok=True); CACHE = os.path.join(a.out, "cov_cache"); os.makedirs(CACHE, exist_ok=True); SCRATCH = os.path.join(a.out, "scratch"); os.makedirs(SCRATCH, exist_ok=True)
    log = open(os.path.join(a.out, "d3_covgen_stdout.log"), "w"); G = {k: None for k in REQUIRED}; R = dict(stage="init", family=a.family, failures=[], timings={}); selftest = a.selftest_configs is not None or a.selftest_skip_env_lock or a.selftest_skip_pc1 or a.selftest_skip_anchors   # --sizes is a FORMAL partition, not a self-test
    def note(*s):
        m = " ".join(str(x) for x in s); print(m, flush=True)
        try: log.write(m + "\n"); log.flush()
        except ValueError: pass
    def finish(code, stage="final"):
        R["stage"] = stage; R["gates"] = G; R["required_inventory"] = list(REQUIRED); R["required_all_true"] = all(G.get(k) is True for k in REQUIRED); R["D3_PASS"] = bool(R["required_all_true"] and a.profile == "production_official" and not selftest and code == 0); R["seconds"] = time.time() - t0
        note("D3_PASS =", R["D3_PASS"], "| stage:", stage, "| gates:", json.dumps(G)); log.close()
        inv = {}
        for d, _, fs in os.walk(a.out):
            for f in fs:
                p = os.path.join(d, f); rel = os.path.relpath(p, a.out)
                if rel != "d3_run_manifest.json" and not rel.startswith("scratch"): inv[rel] = dict(sha256=sha(p), bytes=os.path.getsize(p))
        R["output_inventory"] = inv; tmp = os.path.join(a.out, "d3_run_manifest.json.tmp"); open(tmp, "w").write(json.dumps(R, indent=1, ensure_ascii=False, default=str)); os.replace(tmp, os.path.join(a.out, "d3_run_manifest.json")); print("run manifest written; D3_PASS =", R["D3_PASS"]); return code
    try:
        if a.profile != "production_official": R["failures"].append("profile"); return finish(1)
        sys.path.insert(0, a.phaseb); sys.path.insert(0, a.mt)
        pins_path = os.path.join(a.phaseb, "d", "d3_pins.json"); pins = json.load(open(pins_path)); R["pins_sha256"] = sha(pins_path); inv0 = json.load(open(os.path.join(a.phaseb, "B2_completion_inventory.json")))
        G["G_pins_loaded"] = bool(pins.get("schema") == "d3_pins_v1" and inv0.get("d_sha256", {}).get("d/d3_pins.json") == R["pins_sha256"])
        from step1_engine import __version__; from step1_engine.checkpoint import module_shas
        G["G_engine_inventory"] = (inv0["modules"] == module_shas() and inv0["engine_version"] == __version__ == pins["engine_version"]); me = os.path.abspath(__file__); G["G_script_sha"] = (inv0.get("d_sha256", {}).get("d/d3_covgen.py") == sha(me)); R["engine_version"] = __version__
        R["source"] = dict(engine_version=__version__, inventory_sha256=sha(os.path.join(a.phaseb, "B2_completion_inventory.json")), script_sha256=sha(me), pins_sha256=R["pins_sha256"], profile=a.profile)
        if not (G["G_pins_loaded"] and G["G_engine_inventory"] and G["G_script_sha"]): R["failures"].append("preflight binding failed"); return finish(1, "preflight")
        # ---- trusted inputs (D-1 v0.3 contracts)
        pc = json.load(open(os.path.join(a.phasec, "PACKET_INVENTORY.json"))); members = {}
        for d, _, fs in os.walk(a.phasec):
            for f in fs:
                rel = os.path.relpath(os.path.join(d, f), a.phasec)
                if rel != "PACKET_INVENTORY.json" and "__pycache__" not in rel: members[rel] = dict(sha256=sha(os.path.join(d, f)), bytes=os.path.getsize(os.path.join(d, f)))
        G["G_phaseC_members"] = bool(sha(os.path.join(a.phasec, "PACKET_INVENTORY.json")) == pins["phaseC_inventory_sha256"] and set(members) == set(pc["files"]) and all(members[k] == dict(sha256=v["sha256"], bytes=v["bytes"]) for k, v in pc["files"].items()))
        from step1_engine.production import D1_REGISTERED_RECEIPT, _verified_frozen_loader
        try: t1, loader_id = _verified_frozen_loader(a.mt, D1_REGISTERED_RECEIPT["frozen_loaders"]); G["G_external_loader_sha"] = True; R["loader"] = loader_id
        except Exception as ex_: G["G_external_loader_sha"] = False; R["loader_error"] = repr(ex_)
        from step1_engine.d3_stage import a11_attestation, TRUSTED_SOURCES, PC1_CONTRACT
        att = a11_attestation(); G["G_a11_freeze_sha"] = True
        nbp = os.path.join(a.mt, "results/step1_phaseA/A11_freeze/MirrorTopology_Step1_A11_x0bridge_v1.4.1.ipynb"); nb = json.load(open(nbp)); cell4 = "".join(nb["cells"][4]["source"]); cell4_sha = hashlib.sha256(cell4.encode()).hexdigest()
        G["G_a11_generator_cell_sha"] = (sha(nbp) == TRUSTED_SOURCES["a11_notebook"] and cell4_sha == pins["a11_generator_cell4_sha256"]); R["a11_generator_cell4_sha256"] = cell4_sha
        d1dir = os.path.join(a.phaseb, "registered_assets", "d1"); G["G_d1_trusted"] = bool(sha(os.path.join(d1dir, "d1_receipt.json")) == D1_REGISTERED_RECEIPT["receipt_file_sha256"] and sha(os.path.join(d1dir, "d1_cov_registry.json")) == D1_REGISTERED_RECEIPT["registry_sha256"]); d1reg = json.load(open(os.path.join(d1dir, "d1_cov_registry.json")))
        if not (G["G_phaseC_members"] and G["G_external_loader_sha"] and G["G_a11_freeze_sha"] and G["G_a11_generator_cell_sha"] and G["G_d1_trusted"]): R["failures"].append("trusted-input binding failed"); return finish(1, "trusted_inputs")
        # ---- environment hard gate
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
        # ---- CMBtopology (git exit codes recorded)
        def git(cmd):
            r = subprocess.run(["git", "-C", a.ct] + cmd, capture_output=True, text=True); return dict(returncode=r.returncode, stdout=r.stdout.strip(), stderr=r.stderr.strip())
        R["git"] = dict(head=git(["rev-parse", "HEAD"]), origin=git(["remote", "get-url", "origin"]), status=git(["status", "--porcelain", "--untracked-files=all"]))
        G["G_ct_commit"] = (R["git"]["head"]["returncode"] == 0 and R["git"]["head"]["stdout"] == EXPECTED_CMBTOPO_COMMIT); G["G_ct_origin"] = (R["git"]["origin"]["returncode"] == 0 and R["git"]["origin"]["stdout"].rstrip("/").removesuffix(".git") == "https://github.com/CompactCollaboration/CMBtopology"); G["G_ct_clean"] = (R["git"]["status"]["returncode"] == 0 and R["git"]["status"]["stdout"] == "")
        REQ_TXT = os.path.join(a.ct, "requirements.txt"); REQ_SHA = sha(REQ_TXT)
        from importlib.metadata import version as pkg_version, PackageNotFoundError
        def pkgver(n):
            try: return pkg_version(n)
            except PackageNotFoundError: return "MISSING"
        VERS = {n: pkgver(n) for n in PKGS}; G["G_ct_dependencies_present"] = all(v != "MISSING" for v in VERS.values()); PYV = sys.version.split()[0]
        BLAS = str({k: v.get("name") for k, v in np.show_config(mode="dicts").get("Build Dependencies", {}).items() if k in ("blas", "lapack")}); PLATFORM = dict(machine=platform.machine(), platform=platform.platform())
        ENV_FINGERPRINT = hashlib.sha256(json.dumps(dict(python=PYV, versions=VERS, requirements_sha256=REQ_SHA, platform=PLATFORM, blas_lapack=BLAS, ct_commit=EXPECTED_CMBTOPO_COMMIT, run_config=RUN_CFG), sort_keys=True).encode()).hexdigest()
        R["env_lock"] = dict(schema="d3_env_lock_v1", python=PYV, versions=VERS, requirements_sha256=REQ_SHA, platform=PLATFORM, blas_lapack=BLAS, cmbtopology_commit=EXPECTED_CMBTOPO_COMMIT, env_fingerprint=ENV_FINGERPRINT)
        json.dump(R["env_lock"], open(os.path.join(a.out, "d3_env_lock.json"), "w"), indent=1)
        if not (G["G_ct_commit"] and G["G_ct_origin"] and G["G_ct_clean"] and G["G_ct_dependencies_present"]): R["failures"].append("CMBtopology binding failed"); return finish(1, "external")
        sys.path.insert(0, a.ct); from topology.run_topology import run_topology
        # ---- bound D-3 inputs: registry / manifest / twelve asset -> config map and case table re-derived and compared
        from step1_engine.grid_registry import load_registry; from step1_engine.grid_manifest import build_configuration_manifest; from step1_engine.twelve_assets import intake_registered_twelve_assets
        from step1_engine.d3_stage import verify_config_map, verify_pc1_case_table, REQUIRED_ACTIONS
        reg = load_registry(os.path.join(a.phaseb, "tests/assets/a7_circle_geometry.csv"), os.path.join(a.phaseb, "tests/assets/a6_observer_design_points.json")); man = build_configuration_manifest(reg); G["G_registry_source_bound"] = str(reg.verification_scope).startswith(("constructed_from_verified_assets", "source_bound")) and reg.registry_sha256 == pins["registry_sha256"]
        ta = intake_registered_twelve_assets(os.path.join(a.phaseb, "registered_assets", "b3_2_twelve_assets.json"), reg, "B3_2A_7240c06f255c")
        cm = verify_config_map(json.load(open(os.path.join(a.phaseb, "d", "d3_config_map.json"))), reg, man, ta); G["G_config_map_bound"] = (cm["map_sha256"] == pins["config_map_sha256"])
        ct = verify_pc1_case_table(json.load(open(os.path.join(a.phaseb, "d", "d3_pc1_case_table.json"))), cm, reg, man, ta, a.ct, d1dir); G["G_case_table_bound"] = (ct["table_sha256"] == pins["case_table_sha256"] and ct["formal"] is True)
        if not (G["G_registry_source_bound"] and G["G_config_map_bound"] and G["G_case_table_bound"]): R["failures"].append("D-3 input binding failed"); return finish(1, "d3_inputs")
        # ---- bridge representation D(M) (A11 cell 2 quadrature)
        import t2b2_bridge as br; import healpy as hp; from scipy.special import sph_harm_y
        LM = br.lm_full(); M21 = br.M_matrix()[0]; _NT = _NP = 2 * LMAX + 2; _xg, _wg = np.polynomial.legendre.leggauss(_NT); _th = np.arccos(_xg); _ph = 2 * np.pi * np.arange(_NP) / _NP
        TH, PH = np.meshgrid(_th, _ph, indexing="ij"); WQ = (np.repeat(_wg[:, None], _NP, axis=1) * (2 * np.pi / _NP)).ravel(); DIRS = np.column_stack([np.sin(TH).ravel() * np.cos(PH).ravel(), np.sin(TH).ravel() * np.sin(PH).ravel(), np.cos(TH).ravel()])
        def Yc_at(dirs):
            th, ph = hp.vec2ang(dirs); return np.array([sph_harm_y(l, m, th, ph) for (l, m) in LM])
        def Ymat(dirs): return (M21.conj() @ Yc_at(dirs)).real.T
        YQ = Ymat(DIRS)
        def D_of(Mm): return (YQ * WQ[:, None]).T @ Ymat(DIRS @ Mm)
        # A11 cell 2 representation battery (verbatim thresholds): Gram, real-basis bridge, orthogonality / direct geometry / homomorphism over the used M set, analytic reflections
        RB = br.real_basis_lm(); asha = lambda arr: hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()
        GATES = dict(G_quadrature_orthonormal=bool(np.abs((YQ * WQ[:, None]).T @ YQ - np.eye(21)).max() < 1e-12))
        rng = np.random.default_rng(20260907); dirs_t = rng.standard_normal((100, 3)); dirs_t /= np.linalg.norm(dirs_t, axis=1, keepdims=True); th_t, ph_t = hp.vec2ang(dirs_t)
        E_explicit = np.column_stack([(sph_harm_y(l, m, th_t, ph_t).real if (cs == 'c' and m == 0) else np.sqrt(2) * sph_harm_y(l, m, th_t, ph_t).real if cs == 'c' else np.sqrt(2) * sph_harm_y(l, m, th_t, ph_t).imag) for (l, m, cs) in RB])
        GATES["G_real_basis_bridge"] = bool(np.abs(Ymat(dirs_t) - E_explicit).max() < 1e-12)
        MA = np.diag([1., -1., 1.]); MB = np.diag([-1., 1., 1.]); RZ = np.diag([-1., -1., 1.]); from scipy.spatial.transform import Rotation
        Rr1, Rr2 = Rotation.random(rng=rng).as_matrix(), Rotation.random(rng=rng).as_matrix(); worst_orth = worst_geom = 0.0
        for Mm in [MA, MB, MA @ MB, RZ, Rr1, Rr2]:
            D = D_of(Mm); worst_orth = max(worst_orth, np.abs(D.T @ D - np.eye(21)).max()); x = rng.standard_normal(21); a_vec = M21.conj().T @ x
            worst_geom = max(worst_geom, np.abs((Yc_at(dirs_t).T @ (M21.conj().T @ (D @ x))).real - (Yc_at(dirs_t @ Mm).T @ a_vec).real).max() / np.abs((Yc_at(dirs_t @ Mm).T @ a_vec).real).max())
        hom = max(np.abs(D_of(MA @ MB) - D_of(MA) @ D_of(MB)).max(), np.abs(D_of(Rr1 @ Rr2) - D_of(Rr1) @ D_of(Rr2)).max(), np.abs(D_of(MA @ Rr1) - D_of(MA) @ D_of(Rr1)).max())
        Dy_th = np.diag([(-1.0 if cs == 's' else 1.0) for (l, m, cs) in RB]); Dz_th = np.diag([(-1.0) ** (l + m) for (l, m, cs) in RB])
        GATES["G_D_orthogonal_all_used"] = bool(worst_orth < 1e-10); GATES["G_D_direct_geometry_complex_path"] = bool(worst_geom < 1e-10); GATES["G_D_homomorphism"] = bool(hom < 1e-10)
        GATES["G_reflection_D_analytic"] = bool(np.abs(D_of(MA) - Dy_th).max() < 1e-12 and np.abs(D_of(np.diag([1., 1., -1.])) - Dz_th).max() < 1e-12)
        R["representation"] = dict(gates=GATES, worst_orthogonality=float(worst_orth), worst_direct_geometry=float(worst_geom), worst_homomorphism=float(hom), quadrature_nodes_sha256=asha(DIRS), quadrature_weights_sha256=asha(WQ), M21_sha256=asha(M21), LM_sha256=hashlib.sha256(json.dumps(LM).encode()).hexdigest(), RB_sha256=hashlib.sha256(json.dumps(RB).encode()).hexdigest(), source="A11 v1.4.1 cell 2 battery (verbatim thresholds)")
        G["G_bridge_quadrature"] = all(GATES.values())
        if not G["G_bridge_quadrature"]: R["failures"].append(f"bridge representation battery failed: {GATES}"); return finish(1, "bridge")
        # per-action D(M) used by PC-1: orthogonality + analytic diagonal check where applicable; recorded per unique action
        used_D = {}
        def D_for(M):
            key = json.dumps(np.asarray(M).tolist())
            if key not in used_D:
                D = D_of(np.asarray(M, float)); orth = float(np.abs(D.T @ D - np.eye(21)).max())
                if not (np.isfinite(D).all() and orth < 1e-10): raise RuntimeError(f"D(M) for action matrix {key} failed the runtime orthogonality gate ({orth})")
                used_D[key] = dict(D=D, orthogonality=orth, D_sha256=asha(D))
            return used_D[key]["D"]
        R["used_D"] = {}
        # ---- registered generator (A11 cell 4 verbatim; as in d1_covgen)
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
                os.chdir(scratch); kw = dict(p)
                if top != "E1": kw["x0"] = np.array(x0, float)
                run_topology(topology=top, l_max=LMAX, do_polarization=False, normalize=False, l_range=np.array([[2, LMAX]]), lp_range=np.array([[2, LMAX]]), **kw)
                dirs = glob.glob("runs/*"); assert len(dirs) == 1, dirs; d = dirs[0]; src = os.path.join(d, f"TT_corr_matrix_l_2_{LMAX}_lp_2_{LMAX}.npy"); assert os.path.exists(src), src
                tmp = f + ".tmp"; shutil.copy(src, tmp)
                with open(tmp, "rb") as fh: os.fsync(fh.fileno())
                os.replace(tmp, f)
            finally: os.chdir(cwd0)
            rec = dict(tag=tag, manifest=key_of(top, p, x0), cov_file_sha256=sha(f), cov_array_sha256=hashlib.sha256(np.load(f).tobytes()).hexdigest(), source_run_dir=os.path.basename(d.rstrip("/")), seconds=time.time() - tt)
            atomic_write_json(rec, mf); note(f"  generated {tag[:20]} ({time.time()-tt:.0f}s)"); return f, tag, rec
        # ---- family selection
        fam = a.family; rows = [r for r in cm["configurations"] if r["family"] == fam and r["origin"] == "twelve_added"]; sel = None if a.selftest_configs is None else {int(x) for x in a.selftest_configs.split(",")}
        if not rows: R["failures"].append("family has no new configurations (E1?)"); return finish(1, "family")
        sizes_arg = None if a.sizes is None else [x for x in a.sizes.split(",") if x]
        if sizes_arg is not None and (not sizes_arg or len(set(sizes_arg)) != len(sizes_arg) or any(x not in {r["size_id"] for r in rows} for x in sizes_arg)): R["failures"].append(f"invalid --sizes {a.sizes} (unknown / duplicate / empty)"); return finish(2, "selection")
        if sel is not None and (not sel or any(x not in {r["config_id"] for r in rows} for x in sel)): R["failures"].append(f"invalid --selftest-configs {a.selftest_configs} (unknown ids)"); return finish(2, "selection")
        if sizes_arg is not None: rows = [r for r in rows if r["size_id"] in sizes_arg]
        rows = [r for r in rows if sel is None or r["config_id"] in sel]; new_ids = {r["config_id"] for r in rows}
        if not rows: R["failures"].append("empty configuration selection (invalid --selftest-configs / --sizes)"); return finish(2, "selection")
        R["selection"] = dict(family=fam, sizes=sizes_arg, selftest_configs=(sorted(sel) if sel else None), selftest_skip_anchors=bool(a.selftest_skip_anchors), n_new_configurations=len(rows))
        from step1_engine.legacy_kernel import LegacyKernel;         k = LegacyKernel(a.mt); registry_out = {}; n_ok = 0
        def intake(r, f, rec):
            """D-1 intake contract applied to a 12-position configuration row (geometry binding by topology / params / x0 against the verified config map)."""
            geo_ok = (rec["manifest"]["topology"] == r["family"] and [float(v) for v in rec["manifest"]["x0"]] == [float(v) for v in r["x0_CT"]] and rec["manifest"]["params"] == {kk: float(v) for kk, v in r["shape_params"].items()})
            Mx, Cr, meta = t1.load_cov_full(f, LMAX); arr_sha = hashlib.sha256(np.load(f).tobytes()).hexdigest(); ev = np.linalg.eigvalsh((Cr + Cr.T) / 2); psd = bool(ev.min() > -1e-12 * ev.max())
            C_M, c_ct = k.matched(Cr); S_M, iM = k.psqrt(C_M); S_N, iN = k.psqrt(Cr); roots_ok = all(v["clip"] == 0 and v["lambda_min"] > 0 and v["sym"] < 1e-12 and v["recon"] < 1e-10 for v in (iM, iN))
            ok = bool(geo_ok and rec["manifest"]["run_config"] == RUN_CFG and rec["manifest"]["cmbtopology_commit"] == EXPECTED_CMBTOPO_COMMIT and rec["manifest"]["env_fingerprint"] == ENV_FINGERPRINT and arr_sha == rec["cov_array_sha256"] and meta.get("cov_array_sha256") == arr_sha and Cr.shape == (21, 21) and psd and roots_ok)
            return ok, dict(pass_=ok, geometry_ok=geo_ok, psd=psd, eig_min=float(ev.min()), eig_max=float(ev.max()), c_ct=c_ct.tolist(), sqrt_matched=iM, sqrt_native=iN, array_sha_recomputed_ok=(arr_sha == rec["cov_array_sha256"])), Cr
        def load_bound(path, expected_file_sha, expected_array_sha, what):
            """Read the file ONCE: hash the bytes, decode the SAME bytes, recompute the raw array SHA, pass the decoded array through the frozen loader transform and check the
            returned metadata against the expected identities; validate the real-basis matrix (21x21, real, finite, symmetric, PSD). Technical failures raise (never a PC1 result)."""
            b = open(path, "rb").read(); fs = hashlib.sha256(b).hexdigest()
            if fs != expected_file_sha: raise RuntimeError(f"{what}: file bytes differ from the recorded identity")
            import io; raw = np.load(io.BytesIO(b), allow_pickle=False); rs = hashlib.sha256(raw.tobytes()).hexdigest()
            if rs != expected_array_sha: raise RuntimeError(f"{what}: raw array SHA differs from the recorded identity")
            tmpd = os.path.join(SCRATCH, "bound_load"); os.makedirs(tmpd, exist_ok=True); tp = os.path.join(tmpd, os.path.basename(path)); open(tp, "wb").write(b)
            Mx, Cr, meta = t1.load_cov_full(tp, LMAX)
            if not isinstance(meta, dict) or meta.get("cov_array_sha256") != rs: raise RuntimeError(f"{what}: loader metadata does not carry the loaded array identity")
            Cr = np.asarray(Cr)
            if Cr.shape != (21, 21) or np.iscomplexobj(Cr) or not np.isfinite(Cr).all(): raise RuntimeError(f"{what}: real-basis matrix invalid (shape {Cr.shape}, complex={np.iscomplexobj(Cr)}, finite={bool(np.isfinite(Cr).all()) if not np.iscomplexobj(Cr) else False})")
            if np.abs(Cr - Cr.T).max() > 1e-12 * max(1.0, np.abs(Cr).max()): raise RuntimeError(f"{what}: real-basis matrix not symmetric")
            ev = np.linalg.eigvalsh((Cr + Cr.T) / 2)
            if not (np.isfinite(ev).all() and ev.min() > -1e-12 * ev.max() and ev.max() > 0): raise RuntimeError(f"{what}: real-basis matrix not PSD / degenerate")
            return Cr, dict(file_sha256=fs, array_sha256=rs, loader_meta_sha=meta.get("cov_array_sha256"), eig_min=float(ev.min()), eig_max=float(ev.max()))
        # ---- per-unit atomic evidence (partial records survive any exception)
        pc1 = {}; failed_units = []; evidence = dict(schema="d3_partial_evidence_v1", family=fam, bases={}, cases={}, failed=failed_units, status="IN_PROGRESS")
        def save_partial(status="IN_PROGRESS", unit=None):
            """Write the partial evidence and READ IT BACK; a save failure is recorded with the unit identity in the run record and on stderr before propagating."""
            evidence["status"] = status; evidence["bases"] = registry_out; evidence["cases"] = pc1
            try:
                atomic_write_json(evidence, os.path.join(a.out, "d3_partial_evidence.json")); back = json.load(open(os.path.join(a.out, "d3_partial_evidence.json")))
                if back != json.loads(json.dumps(evidence, default=str)): raise RuntimeError("partial evidence read-back differs from the computed snapshot")
            except Exception as ex_:
                R["save_failure"] = dict(unit=unit, status=status, error=repr(ex_)); print(f"SAVE FAILURE at unit {unit}: {ex_!r}", file=sys.stderr); raise
        base_C = {}
        for r in rows:
            tt = time.time()
            try:
                f, tag, rec = ensure_cov(fam, r["shape_params"], r["x0_CT"]); ok, info, Cr = intake(r, f, rec); Cr_b, bnd = load_bound(f, rec["cov_file_sha256"], rec["cov_array_sha256"], f"base {r['config_id']}"); ok = ok and np.array_equal(Cr_b, Cr)
            except Exception as ex_:
                failed_units.append(dict(unit="base", config_id=r["config_id"], request=dict(topology=fam, params=r["shape_params"], x0=r["x0_CT"]), error=repr(ex_))); save_partial("FAILED_AT_BASE"); R["failures"].append(f"base {r['config_id']}: {ex_!r}"); G["G_all_bases_generated"] = False; G["G_evidence_saved"] = True; return finish(1, "base_failure")
            n_ok += int(ok); base_C[r["config_id"]] = Cr
            try:
              registry_out[str(r["config_id"])] = dict(config_id=r["config_id"], family=fam, size_id=r["size_id"], position_index=r["position_index"], origin="twelve_added", cache_key=r["cache_key"], tag=tag, cov_file=os.path.relpath(f, a.out), cov_file_sha256=rec["cov_file_sha256"], cov_array_sha256=rec["cov_array_sha256"], x0_CT=r["x0_CT"], shape_params=r["shape_params"], intake=info, seconds=time.time() - tt)
              registry_out[str(r["config_id"])]["bound_load"] = bnd; save_partial(unit=dict(unit="base", config_id=r["config_id"]))
            except Exception as ex_:
                failed_units.append(dict(unit="base_save", config_id=r["config_id"], error=repr(ex_))); R["failures"].append(f"base {r['config_id']}: save failure {ex_!r}"); G["G_evidence_saved"] = False; return finish(1, "save_failure")
            note(f"base {r['config_id']} {fam}/{r['size_id']}/pos{r['position_index']}: intake {'PASS' if ok else 'FAIL'} ({time.time()-tt:.0f}s)")
            if not ok:
                save_partial("STOPPED_AT_INTAKE_FAILURE"); json.dump(dict(schema="d3_cov_registry_v1", status="STOPPED_AT_INTAKE_FAILURE", configurations=registry_out), open(os.path.join(a.out, "d3_cov_registry.json"), "w"), indent=1); R["failures"].append(f"intake failed for {r['config_id']}"); G["G_all_base_intakes_pass"] = False; G["G_evidence_saved"] = True; return finish(1, "intake_failure")
        G["G_all_bases_generated"] = (len(base_C) == len(rows)); G["G_all_base_intakes_pass"] = (n_ok == len(rows))
        # ---- PC-1: clone covariances and comparison (partition-aware: the anchor cases of the selected sizes are always included)
        n_cases = 0
        if a.selftest_skip_pc1: G["G_all_cases_evaluated"] = None
        else:
            sizes_sel = {r["size_id"] for r in rows}
            cases = [c for c in ct["new_point_cases"] if c["family"] == fam and c["config_id"] in new_ids] + ([] if a.selftest_skip_anchors else [c for c in ct["first_wave_anchor_cases"] if c["family"] == fam and c["size_id"] in sizes_sel])
            for c in cases:
                tt = time.time(); cid = c["config_id"]; M = np.array(c["M"], float); res = dict(case_id=c["case_id"], config_id=cid, action=c["action"], set=c.get("set", "new_point"), base_from=("generated_here" if cid in base_C else "D1_registered"), tolerance_match_rel_lt=c["tolerance_match_rel_lt"])
                try:
                    if cid in base_C: C0 = base_C[cid]; res["base_identity"] = dict(file_sha256=registry_out[str(cid)]["cov_file_sha256"], array_sha256=registry_out[str(cid)]["cov_array_sha256"])
                    else:
                        p = os.path.join(d1dir, c["base_reused_from_D1"]["cov_file"]); C0, bnd0 = load_bound(p, c["base_reused_from_D1"]["cov_file_sha256"], c["base_reused_from_D1"]["cov_array_sha256"], f"anchor base {cid}"); res["base_identity"] = bnd0
                    gp = c["generator_params"] if fam != "E2" else c["shape_params"]; f1, tag1, rec1 = ensure_cov(fam, gp, c["clone_x0_H1"]); C1, bnd1 = load_bound(f1, rec1["cov_file_sha256"], rec1["cov_array_sha256"], f"clone {c['case_id']}")
                    D = D_for(M); target = D @ C0 @ D.T; tn = float(np.linalg.norm(target)); dn = float(np.linalg.norm(C1 - target))
                    if not (np.isfinite(tn) and tn > 0 and np.isfinite(dn)): raise RuntimeError(f"PC-1 {c['case_id']}: primary norms invalid (target {tn}, diff {dn})")
                    rel = dn / tn; off = ~np.eye(21, dtype=bool); ton = float(np.linalg.norm(target[off])); rel_off = (float(np.linalg.norm((C1 - target)[off]) / ton) if ton > 0 else None)
                    dg = np.diag(target); rel_white = None
                    if np.all(dg > 0):
                        w = 1 / np.sqrt(dg); wn = float(np.linalg.norm(w[:, None] * target * w[None, :])); rel_white = (float(np.linalg.norm(w[:, None] * (C1 - target) * w[None, :]) / wn) if wn > 0 else None)
                    res.update(clone_tag=tag1, clone_cov_file=os.path.relpath(f1, a.out), clone_identity=bnd1, D_sha256=used_D[json.dumps(M.tolist())]["D_sha256"], D_orthogonality=used_D[json.dumps(M.tolist())]["orthogonality"], rel=float(rel), rel_off=rel_off, rel_white=rel_white, diagnostics_note=(None if (rel_off is not None and rel_white is not None) else "a diagnostic denominator was zero; primary rel unaffected"), match=bool(rel < c["tolerance_match_rel_lt"]), evaluation="EVALUATED", seconds=time.time() - tt)
                    if a.with_h2:
                        f2, tag2, rec2 = ensure_cov(fam, gp, c["alt_x0_H2"]); C2, bnd2 = load_bound(f2, rec2["cov_file_sha256"], rec2["cov_array_sha256"], f"H2 {c['case_id']}"); d2n = float(np.linalg.norm(C2 - target)); rel2 = (d2n / tn) if np.isfinite(d2n) else float("inf")
                        if np.isfinite(rel2): res.update(rel_H2=float(rel2), h2_status="EVALUATED", h2_discriminates=bool(rel2 > PC1_CONTRACT["tolerance"]["discriminate_rel_gt"]), h2_tag=tag2, h2_identity=bnd2)
                        else: res.update(rel_H2=None, h2_status="INVALID_DIAGNOSTIC", h2_discriminates=None, h2_reason=f"H2 difference norm not finite ({d2n}); diagnostic only, H1 result unaffected", h2_tag=tag2, h2_identity=bnd2)
                    n_cases += 1; note(f"PC-1 {c['case_id']}: rel={rel:.3e} {'match' if res['match'] else 'NO MATCH'} ({time.time()-tt:.0f}s)")
                except Exception as ex_:
                    res.update(evaluation="TECHNICAL_FAILURE", error=repr(ex_), match=None, seconds=time.time() - tt); failed_units.append(dict(unit="pc1_case", case_id=c["case_id"], config_id=cid, action=c["action"], request=dict(topology=fam, x0_H1=c["clone_x0_H1"]), error=repr(ex_)))
                    pc1[c["case_id"]] = res; save_partial("FAILED_AT_PC1"); R["failures"].append(f"PC-1 {c['case_id']}: technical failure {ex_!r}"); G["G_all_cases_evaluated"] = False; G["G_evidence_saved"] = True
                    json.dump(dict(schema="d3_cov_registry_v1", status="STOPPED_AT_PC1_TECHNICAL_FAILURE", configurations=registry_out), open(os.path.join(a.out, "d3_cov_registry.json"), "w"), indent=1); json.dump(dict(schema="d3_pc1_results_v1", family=fam, status="PARTIAL", cases=pc1), open(os.path.join(a.out, "d3_pc1_results.json"), "w"), indent=1); return finish(1, "pc1_technical_failure")
                pc1[c["case_id"]] = res
                try: save_partial(unit=dict(unit="pc1_case", case_id=c["case_id"]))
                except Exception as ex_:
                    failed_units.append(dict(unit="pc1_case_save", case_id=c["case_id"], config_id=cid, action=c["action"], error=repr(ex_))); R["failures"].append(f"PC-1 {c['case_id']}: save failure {ex_!r}"); G["G_evidence_saved"] = False; return finish(1, "save_failure")
            R["used_D"] = {k: dict(orthogonality=v["orthogonality"], D_sha256=v["D_sha256"]) for k, v in used_D.items()}
            status = {}
            for cid in sorted({c["config_id"] for c in cases}):
                rs = [v for v in pc1.values() if v["config_id"] == cid]; req = REQUIRED_ACTIONS[fam]; ev_ok = [v for v in rs if v.get("evaluation") == "EVALUATED"]
                status[str(cid)] = dict(actions_required=req, actions_evaluated=sorted(v["action"] for v in ev_ok), status=("PC1_PASS" if len(ev_ok) == len(req) and all(v["match"] for v in ev_ok) else ("PC1_FAIL" if len(ev_ok) == len(req) else "PC1_PENDING")), max_rel=(max(v["rel"] for v in ev_ok) if ev_ok else None))
            R["pc1_status"] = status; G["G_all_cases_evaluated"] = (n_cases == len(cases) and len(cases) > 0)
            R["partition"] = dict(sizes=sorted(sizes_sel), new_point_cases=sum(1 for c in cases if c.get("set", "new_point") == "new_point"), anchor_cases=sum(1 for c in cases if c.get("set") == "first_wave_anchor_diagnostic"), required_new_point_cases_family=sum(1 for c in ct["new_point_cases"] if c["family"] == fam), required_anchor_cases_family=sum(1 for c in ct["first_wave_anchor_cases"] if c["family"] == fam))
        save_partial("COMPLETE")
        json.dump(dict(schema="d3_cov_registry_v1", family=fam, partition=R.get("partition"), selection=R.get("selection"), registry_sha256=reg.registry_sha256, config_map_sha256=cm["map_sha256"], case_table_sha256=ct["table_sha256"], env_fingerprint=ENV_FINGERPRINT, cmbtopology_commit=EXPECTED_CMBTOPO_COMMIT, run_config=RUN_CFG, configurations=registry_out, n=len(registry_out), scope=("SELFTEST subset" if sel else f"{fam}: 12-position added configurations")), open(os.path.join(a.out, "d3_cov_registry.json"), "w"), indent=1)
        json.dump(dict(schema="d3_pc1_results_v1", family=fam, partition=R.get("partition"), selection=R.get("selection"), contract=PC1_CONTRACT, case_table_sha256=ct["table_sha256"], representation=R.get("representation"), used_D=R.get("used_D"), cases=pc1, configuration_status=R.get("pc1_status", {}), with_h2=a.with_h2, scope="asset-layer PC-1 evaluation per the transcribed A11 R2/R5 contract; PC1_FAIL forbids formal consumption of the configuration; no position-state conversion"), open(os.path.join(a.out, "d3_pc1_results.json"), "w"), indent=1)
        R["n_bases"] = len(base_C); R["n_cases"] = n_cases
        # evidence saved: every published file is READ BACK and compared VALUE-LEVEL with the computed snapshots (not only key sets); bytes SHA recorded
        try:
            snap_reg = json.loads(json.dumps(registry_out, default=str)); snap_pc1 = json.loads(json.dumps(pc1, default=str)); snap_ev = json.loads(json.dumps(evidence, default=str))
            rg_chk = json.load(open(os.path.join(a.out, "d3_cov_registry.json"))); pc_chk = json.load(open(os.path.join(a.out, "d3_pc1_results.json"))); ev_chk = json.load(open(os.path.join(a.out, "d3_partial_evidence.json"))); env_chk = json.load(open(os.path.join(a.out, "d3_env_lock.json")))
            ok_ev = (rg_chk["configurations"] == snap_reg and pc_chk["cases"] == snap_pc1 and pc_chk.get("configuration_status", {}) == R.get("pc1_status", {}) and ev_chk == snap_ev and ev_chk["status"] == "COMPLETE" and env_chk["env_fingerprint"] == ENV_FINGERPRINT and rg_chk["env_fingerprint"] == ENV_FINGERPRINT and rg_chk["case_table_sha256"] == pc_chk["case_table_sha256"] == ct["table_sha256"] and pc_chk.get("representation") == R.get("representation"))
            R["published_evidence"] = dict(registry_sha256=sha(os.path.join(a.out, "d3_cov_registry.json")), pc1_results_sha256=sha(os.path.join(a.out, "d3_pc1_results.json")), partial_evidence_sha256=sha(os.path.join(a.out, "d3_partial_evidence.json")), env_lock_sha256=sha(os.path.join(a.out, "d3_env_lock.json")), value_level_readback_ok=bool(ok_ev)); G["G_evidence_saved"] = bool(ok_ev)
            if not ok_ev: R["failures"].append("published evidence differs from the computed snapshots (value-level read-back)")
        except Exception as ex_: G["G_evidence_saved"] = False; R["failures"].append(f"evidence check: {ex_!r}")
        shutil.rmtree(SCRATCH, ignore_errors=True)
        return finish(0 if all(G[kk] is True for kk in REQUIRED) else 1, "complete")
    except Exception as ex:
        R["failures"].append("exception: " + repr(ex)); R["traceback"] = traceback.format_exc(); note(R["traceback"]); return finish(1, "exception")


if __name__ == "__main__": sys.exit(main())
