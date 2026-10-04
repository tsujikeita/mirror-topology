# -*- coding: utf-8 -*-
"""Phase D4C-0b: generation and sealing of the fixed isotropic PSEUDO-OBSERVATION columns (rules §9.2: n_pseudo = 2000, m = 1, independent stream) for the global false-support
calibration — the frozen LegacyKernel on the registered isotropic root with the SEPARATE pseudo table d/d4_pseudo_table.json (step1_engine.d4_pseudo; the D-2 CRN table is not
touched). Preflight: pins / inventory / script binding; Phase C members; registered numerical environment HARD gate (the columns are formal reference values and must come from
the registered environment); frozen loader (t1_engine real path + SHA); pseudo table bound to the inventory (d_sha256) and to the pins (d4_pseudo_table_sha256). Output (fresh or
empty OUT, disjoint from every source root): d4_pseudo_columns.npz (T1 / T2 float64, AX / PL int32, cid, UIDs; generation order), d4_pseudo_record.json (column identity, file
identity, root / table / kernel / source / environment, attempt + launcher lock echo) published through the verified whole-document helper. PSEUDO_PASS requires
production_official, no self-test flag, all REQUIRED gates True and rc 0. The target commitment is NOT computed here (calibration_first.commit_target, by the author, with a
private nonce). --selftest-n N (< 2000) generates a prefix only and never PSEUDO_PASS."""
from __future__ import annotations
import os
for _k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"): os.environ.setdefault(_k, "2")
import argparse, copy, hashlib, json, sys, time, traceback, resource
import numpy as np

REQUIRED = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_phaseC_members", "G_env_lock", "G_external_loader_sha", "G_pseudo_table", "G_generated", "G_columns_verified", "G_record_saved")


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


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mt", required=True); ap.add_argument("--phaseb", required=True); ap.add_argument("--phasec", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--profile", default="production_official"); ap.add_argument("--selftest-n", type=int, default=None, help="self-test only: generate a prefix of n < n_pseudo columns; never PSEUDO_PASS"); ap.add_argument("--selftest-skip-env-lock", action="store_true")
    ap.add_argument("--attempt-id", default=None); ap.add_argument("--launcher-lock-sha256", default=None)
    a = ap.parse_args(); t0 = time.time(); selftest = a.selftest_n is not None or a.selftest_skip_env_lock
    if os.path.islink(a.out): print("OUT must not be a symbolic link", file=sys.stderr); return 2
    out = os.path.realpath(a.out); out_exists = os.path.lexists(out)
    if out_exists and (not os.path.isdir(out) or os.listdir(out)): print("OUT must be a fresh (non-existent or empty) real directory", file=sys.stderr); return 2
    def inside(p, q): p, q = os.path.realpath(p), os.path.realpath(q); return p == q or p.startswith(q.rstrip(os.sep) + os.sep)
    protected = dict(mt=a.mt, phaseb=a.phaseb, phasec=a.phasec); clash = [k for k, p in protected.items() if inside(out, p) or inside(p, out)]
    if clash: print("output must be disjoint from the source roots (" + ", ".join(clash) + ")", file=sys.stderr); return 2
    if not out_exists: os.makedirs(out)
    log = open(os.path.join(out, "d4_pseudo_stdout.log"), "w"); G = {k: None for k in REQUIRED}
    R = dict(schema="d4_pseudo_record_v1", stage="init", failures=[], notes=[], selftest=bool(selftest), profile=a.profile, out=out, out_preexisting_empty=bool(out_exists), protected_roots={k: os.path.realpath(p) for k, p in protected.items()}, attempt=dict(attempt_id=a.attempt_id, launcher_lock_sha256=a.launcher_lock_sha256), stages_rss_mb={}, stages_peak_rss_mb={}, timings={})
    def note(*s):
        m = " ".join(str(x) for x in s); print(m, flush=True)
        try: log.write(m + "\n"); log.flush()
        except ValueError: pass
    def mark(stage): R["stages_rss_mb"][stage] = round(_rss_mb(), 1); R["stages_peak_rss_mb"][stage] = round(_peak_rss_mb(), 1); R["timings"][stage] = round(time.time() - t0, 3)
    def finish(code, stage="final"):
        R["stage"] = stage; R["gates"] = G; R["required_inventory"] = list(REQUIRED); R["required_all_true"] = all(G.get(k) is True for k in REQUIRED); R["PSEUDO_PASS"] = bool(R["required_all_true"] and a.profile == "production_official" and not selftest and code == 0); R["seconds"] = time.time() - t0; mark("final")
        note("run finalization | stage:", stage, "| gates:", json.dumps(G)); log.close()
        try: _publish_json(os.path.join(out, "d4_pseudo_record.json"), R)
        except Exception as write_error: print("pseudo record could not be published/verified; no PASS: " + repr(write_error), file=sys.stderr); return 1
        print("pseudo record published and verified; PSEUDO_PASS =", R["PSEUDO_PASS"]); return code
    try:
        if a.profile != "production_official": R["failures"].append("profile"); return finish(1)
        sys.path.insert(0, a.phaseb)
        pins_path = os.path.join(a.phaseb, "d", "d3_pins.json"); pins = json.load(open(pins_path)); R["pins_sha256"] = sha(pins_path); inv_path = os.path.join(a.phaseb, "B2_completion_inventory.json"); inv0 = json.load(open(inv_path))
        G["G_pins_loaded"] = bool(pins.get("schema") == "d3_pins_v1" and inv0.get("d_sha256", {}).get("d/d3_pins.json") == R["pins_sha256"])
        from step1_engine import __version__; from step1_engine.checkpoint import module_shas
        G["G_engine_inventory"] = (inv0["modules"] == module_shas() and inv0["engine_version"] == __version__ == pins["engine_version"]); me = os.path.abspath(__file__); G["G_script_sha"] = (inv0.get("d_sha256", {}).get("d/d4_pseudo.py") == sha(me)); R["engine_version"] = __version__
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
        from step1_engine.production import D1_REGISTERED_RECEIPT, _verified_frozen_loader
        try: t1, loader_id = _verified_frozen_loader(a.mt, D1_REGISTERED_RECEIPT["frozen_loaders"]); G["G_external_loader_sha"] = True; R["loader"] = loader_id
        except Exception as ex_: G["G_external_loader_sha"] = False; R["loader_error"] = repr(ex_)
        from step1_engine import d4_pseudo as dp
        from step1_engine.legacy_kernel import LegacyKernel
        tp = os.path.join(a.phaseb, "d", "d4_pseudo_table.json")
        try:
            table, reg = dp.load_pseudo_table(tp, pins.get("d4_pseudo_table_sha256")); G["G_pseudo_table"] = bool(inv0.get("d_sha256", {}).get("d/d4_pseudo_table.json") == sha(tp) and table["table_sha256"] == pins.get("d4_pseudo_table_sha256") and table["n_pseudo"] == 2000 and table["m"] == 1)
            R["pseudo_table"] = dict(table_sha256=table["table_sha256"], file_sha256=sha(tp), n_pseudo=table["n_pseudo"], m=table["m"], group=table["group"], purpose_id=table["purpose_id"], master_seed=table["master_seed"], wave_id=table["wave_id"], rng_keys=dp.pseudo_rng_keys(table, reg))
        except Exception as ex_: G["G_pseudo_table"] = False; R["pseudo_table_error"] = repr(ex_)
        if not (G["G_phaseC_members"] and G["G_external_loader_sha"] and G["G_pseudo_table"]): R["failures"].append("trusted-input binding failed"); return finish(1, "trusted_inputs")
        mark("preflight")
        k = LegacyKernel(a.mt); S_I, _ = k.psqrt(k.C_ISO); n = table["n_pseudo"] if a.selftest_n is None else int(a.selftest_n)
        if selftest and a.selftest_n is not None and n >= table["n_pseudo"]: R["failures"].append("self-test prefix must be shorter than n_pseudo"); return finish(1, "scope")
        cols = dp.generate_pseudo_columns(k, table, reg, S_I, n=n); G["G_generated"] = bool(cols["n"] == n); mark("generation")
        R["generation"] = dict(n=n, m=1, root_sha256=cols["root_sha256"], rng_keys=cols["rng_keys"], kernel=dict(mt=os.path.realpath(a.mt), loader=R.get("loader")), formal=(not selftest), note="prefix of the table order (self-test) or the full table (formal)")
        ident = dp.column_identity(cols); fid = dp.save_pseudo_columns(os.path.join(out, "d4_pseudo_columns.npz"), cols)
        back = dp.verify_pseudo_columns(os.path.join(out, "d4_pseudo_columns.npz"), ident, table, fid); G["G_columns_verified"] = bool(back["n"] == n and np.array_equal(back["T1"], cols["T1"]) and np.array_equal(back["T2"], cols["T2"])); mark("verification")
        R["columns"] = dict(identity=ident, file=fid, summary=dict(T1_min=float(cols["T1"].min()), T1_max=float(cols["T1"].max()), T2_min=float(cols["T2"].min()), T2_max=float(cols["T2"].max())))
        G["G_record_saved"] = True
        return finish(0 if all(G[kk] is True for kk in REQUIRED) else 1, "complete")
    except Exception as ex:
        R["failures"].append("exception: " + repr(ex)); R["traceback"] = traceback.format_exc(); note(R["traceback"]); return finish(1, "exception")


if __name__ == "__main__": sys.exit(main())
