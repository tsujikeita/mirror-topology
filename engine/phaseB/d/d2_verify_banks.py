# -*- coding: utf-8 -*-
"""Phase D-2 post-run READ-ONLY verification of the stored family banks — v0.2 (audit RV-1/RV-2/RV-3).
MODES: --mode accepted (default): the run under RUN_ROOT must be one of the ACCEPTED generation runs of registered_assets/d2/d2_generation_ledger.json (family, run id, final /
registry / run-manifest / launcher SHAs, unit set with completion-manifest SHAs), and the required unit set is re-derived from the canonical bank spec (family reference b0/b1/fit +
every configuration b0/b1/fit (+w2)); anything else is refused BEFORE any array is read. --mode test: synthetic banks (accepted_run_binding=False, verification_scope='test').
VERIFIER SOURCE (RV-1.5): the verifier's own module SHA map, script SHA and the ledger bytes are checked against the phaseB inventory and recorded as verifier_source, separate
from generator_source (the accepted 0.78.0 commit) and the verification_environment. OUTPUT (RV-2): --out is resolved by realpath, must not lie inside / equal / contain RUN_ROOT or
any referenced bank directory, must be a fresh directory; every output file is created exclusively (O_EXCL; existing files / symlinks refused). Inputs are never written.
INTEGRITY: verify_bank_dir per unit (bytes, sidecar<->manifest identity, exact member set, dtype, finiteness, cid, ranges, UIDs, keys), COMPLETE manifest SHA == ledger, NPZ file
SHA == manifest (== final-record byte count), cid correspondence model<->reference per (purpose, batch) and N0 + 3N0 structure (an equality of cid arrays, not a proof of identical
R/z). COVERAGE: --max-dirs (positive int) => verification_scope='partial', coverage_complete=False, checked/unchecked lists; exit 0 only for complete + all units ok.
F32 (RV-3): for every paired f64/f32 unit (required subset batch 0; W2 banks): flip rows (AX differs) with the REGISTERED rule — relative difference of the selected S+ (T1)
< 1e-6 counts as near-tie (rules §5.2); Event B = (T1 <= T1_obs) & (T2 <= T2_obs) with the frozen target (b3 pins), mismatch rate vs the registered bound 1e-5; per-flip evidence
(row, AX/PL both paths, T1/T2 both paths, Event B both paths, antipode relation, plane angle from the A5 axis vectors). Absolute differences are reported as diagnostics only.
The result carries all_ok (file/member integrity of the checked units), coverage_complete, f32_registered_gate (candidate evaluation; formal acceptance is the auditor's) —
never a scientific support/strong statement."""
from __future__ import annotations
import os, sys, json, hashlib, time, argparse, io
import numpy as np

REL_NEAR_TIE = 1e-6; EVENT_B_MISMATCH_BOUND = 1e-5; T1_OBS = 39.67178834527284; T2_OBS = 259.3375006282747


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _excl_write(path: str, data: bytes):
    if os.path.lexists(path): raise RuntimeError(f"output exists / alias refused: {path}")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o644)
    with os.fdopen(fd, "wb") as fh: fh.write(data)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--phaseb", required=True); ap.add_argument("--run-root", required=True); ap.add_argument("--out", required=True); ap.add_argument("--mode", choices=("accepted", "test"), default="accepted"); ap.add_argument("--max-dirs", type=int, default=None); ap.add_argument("--path-map", action="append", default=[], help="OLD=NEW physical path mapping for moved caches (recorded)")
    a = ap.parse_args(); t0 = time.time()
    if a.max_dirs is not None and (a.max_dirs < 1): print("--max-dirs must be a positive integer", file=sys.stderr); return 2
    run_root = os.path.realpath(a.run_root); out = os.path.realpath(a.out)
    def inside(p, q): p, q = os.path.realpath(p), os.path.realpath(q); return p == q or p.startswith(q.rstrip(os.sep) + os.sep)
    if inside(out, run_root) or inside(run_root, out): print("output must be disjoint from the run root", file=sys.stderr); return 2
    if os.path.lexists(out) and (not os.path.isdir(out) or os.path.islink(out) or os.listdir(out)): print("output must be a fresh (non-existent or empty) real directory", file=sys.stderr); return 2
    sys.path.insert(0, a.phaseb); R = dict(schema="d2_postrun_verification_v2", mode=a.mode, run_root=run_root, out=out, stage="init", failures=[], notes=[], accepted_run_binding=None, verification_scope=None)
    def finish(code):
        R["seconds"] = time.time() - t0; R["exit_code"] = code; os.makedirs(out, exist_ok=True)
        _excl_write(os.path.join(out, f"d2_verify_{R.get('family', 'unknown')}.json"), json.dumps(R, indent=1, default=str).encode()); print("all_ok =", R.get("all_ok"), "| coverage_complete =", R.get("coverage_complete"), "| stage:", R["stage"], "| failures:", R["failures"][:5]); return code
    try:
        # ---- verifier source (separate from the generator source)
        from step1_engine import __version__; from step1_engine.checkpoint import module_shas; from step1_engine.official_gate import current_env
        inv = json.load(open(os.path.join(a.phaseb, "B2_completion_inventory.json"))); me = os.path.abspath(__file__)
        vs_ok = (inv["modules"] == module_shas() and inv["engine_version"] == __version__ and inv.get("d_sha256", {}).get("d/d2_verify_banks.py") == sha(me))
        ledger_p = os.path.join(a.phaseb, "registered_assets", "d2", "d2_generation_ledger.json"); ledger_ok = (inv.get("registered_assets_sha256", {}).get("registered_assets/d2/d2_generation_ledger.json") == sha(ledger_p))
        R["verifier_source"] = dict(engine=__version__, inventory_sha256=sha(os.path.join(a.phaseb, "B2_completion_inventory.json")), script_sha256=sha(me), modules_digest=hashlib.sha256(json.dumps(module_shas(), sort_keys=True).encode()).hexdigest(), source_bound=bool(vs_ok), ledger_bound=bool(ledger_ok)); R["verification_environment"] = current_env()
        if not (vs_ok and ledger_ok): R["failures"].append("verifier source / ledger not bound to the inventory"); R["stage"] = "verifier_source"; return finish(1)
        from step1_engine.d2_bank import verify_bank_dir, load_bank_spec, EXPECTED_MEMBERS; from step1_engine.d2_rng import load_crn_table
        table, _ = load_crn_table(os.path.join(a.phaseb, "d", "d2_crn_table.json")); spec = load_bank_spec(os.path.join(a.phaseb, "d", "d2_bank_spec.json"), table=table); ledger = json.load(open(ledger_p))
        # ---- inputs (read only)
        rg_p = os.path.join(run_root, "d2", "d2_bank_registry.json"); rm_p = os.path.join(run_root, "d2", "d2_run_manifest.json"); fr_p = os.path.join(run_root, "d2_final_record.json"); lk_p = os.path.join(run_root, "launcher_lock.json")
        rg = json.load(open(rg_p)); rm = json.load(open(rm_p)); fr = json.load(open(fr_p)); fam = rg.get("family"); R["family"] = fam
        if fam not in spec["family_reference"]: R["failures"].append("unknown family"); R["stage"] = "inputs"; return finish(1)
        required = [f"ref_{fam}_b0", f"ref_{fam}_b1", f"ref_{fam}_fit"] + [f"cfg{cid}_{x}" for cid, c in sorted(spec["configurations"].items(), key=lambda kv: int(kv[0])) if c["family"] == fam for x in (["b0", "b1", "fit"] + (["w2"] if c["w2_primary"] is not None else []))]
        R["required_units"] = required
        pmap = dict(x.split("=", 1) for x in a.path_map); R["path_map"] = pmap
        def phys(p):
            for old, new in pmap.items():
                if p.startswith(old): return new + p[len(old):]
            return p
        # ---- accepted-run binding (RV-1)
        if a.mode == "accepted":
            L = ledger["families"].get(fam)
            if L is None: R["failures"].append("family not in the ledger"); R["stage"] = "binding"; return finish(1)
            exp = L["records"]; got = dict(final_record_sha256=sha(fr_p), bank_registry_sha256=sha(rg_p), run_manifest_sha256=sha(rm_p), launcher_lock_sha256=sha(lk_p) if os.path.exists(lk_p) else None)
            diff = [k for k in exp if exp[k] != got.get(k)]
            if diff: R["failures"].append(f"run records differ from the accepted ledger: {diff}"); R["record_sha256"] = dict(expected=exp, got=got); R["stage"] = "binding"; return finish(1)
            if not (rm.get("stage") == "complete" and rm.get("D2_PASS") is True and not rm.get("failures") and rg.get("formal") is True): R["failures"].append("accepted run record is not a complete formal D2_PASS run"); R["stage"] = "binding"; return finish(1)
            if set(L["units"]) != set(required) or set(rg["directories"]) != set(required): R["failures"].append("unit set differs from the ledger / canonical spec"); R["stage"] = "binding"; return finish(1)
            for n_ in required:
                if rg["directories"][n_]["manifest_sha256"] != L["units"][n_]["manifest_sha256"]: R["failures"].append(f"{n_}: registry manifest SHA differs from the ledger"); R["stage"] = "binding"; return finish(1)
            R["accepted_run_binding"] = True; R["generator_source"] = dict(engine=L["engine_version"], commit=L["commit"], inventory_sha256=L["inventory_sha256"], run_id=L["run_id"], environment_fingerprint=L["environment_fingerprint"], producer_digest=L["producer_digest"]); R["verification_scope"] = "accepted_full"
        else:
            R["accepted_run_binding"] = False; R["verification_scope"] = "test"; R["generator_source"] = dict(engine=rg.get("engine_version"), note="test mode: unbound synthetic banks"); R["notes"].append("test mode: no accepted-run binding; results are not evidence about the registered banks")
            if set(rg["directories"]) != set(required): R["failures"].append("unit set differs from the canonical spec for this family"); R["stage"] = "binding"; return finish(1)
        # ---- output must be disjoint from every referenced bank directory (RV-2)
        for n_ in required:
            p = os.path.realpath(phys(rg["directories"][n_]["path"]))
            if inside(out, p) or inside(p, out): R["failures"].append(f"output overlaps bank directory {n_}"); R["stage"] = "output"; return finish(2)
        # ---- per-unit integrity
        names = required if a.max_dirs is None else required[: a.max_dirs]; R["verification_scope"] = R["verification_scope"] if a.max_dirs is None else (R["verification_scope"] + "_partial"); R["coverage_complete"] = (a.max_dirs is None); R["checked_units"] = names; R["unchecked_units"] = [n_ for n_ in required if n_ not in names]
        inv_files = fr.get("output_inventory", {}); R["units"] = {}; cid_hash = {}; per_unit_arrays = {}
        from step1_engine.legacy_kernel import LegacyKernel
        try:
            import healpy as hp; AXV = np.array(hp.pix2vec(16, np.arange(3072))).T; ANTI = hp.vec2pix(16, -AXV[:, 0], -AXV[:, 1], -AXV[:, 2])
        except Exception: AXV = None; ANTI = None
        def stats(x): return dict(n=int(x.size), finite=int(np.isfinite(x).sum()), mean=float(np.mean(x)), std=float(np.std(x)), min=float(np.min(x)), max=float(np.max(x)))
        for name in names:
            d = rg["directories"][name]; p = phys(d["path"]); rec = dict(path=p, purpose=d.get("purpose"), tt=time.time())
            try:
                man = verify_bank_dir(p); rec["manifest_sha256"] = man["manifest_sha256"]; rec["manifest_sha256_ok"] = (man["manifest_sha256"] == d["manifest_sha256"]); rec["n_rows"] = man["n_rows"]; rec["formal"] = man["formal"]; rec["roles"] = man["roles"]; rec["selections"] = man["selections"]
                shards = []; cids = []; per = {}
                for sh in man["shards"]:
                    fp = os.path.join(p, sh["file"]); b = open(fp, "rb").read(); fsha = hashlib.sha256(b).hexdigest(); rel = os.path.relpath(os.path.join(d["path"], sh["file"]), run_root)
                    shards.append(dict(file=sh["file"], file_sha256=fsha, matches_manifest=(fsha == sh["file_sha256"]), inventory_bytes_match=(inv_files.get(rel, {}).get("bytes") == len(b))))
                    with np.load(io.BytesIO(b), allow_pickle=False) as z:
                        cids.append(np.asarray(z["cid"]))
                        for k in z.files:
                            if k == "cid": continue
                            role, sel, kk = k.split("__"); per.setdefault((role, sel), {}).setdefault(kk, []).append(np.asarray(z[k]))
                rec["shards"] = shards; cid = np.concatenate(cids); rec["cid"] = dict(n=int(cid.size), unique=int(len(np.unique(cid))), monotone=bool(np.all(np.diff(cid) >= 0)), sha256=hashlib.sha256(np.ascontiguousarray(cid).tobytes()).hexdigest())
                cid_hash[(man["purpose"], man["batch_id"], man["config_id"] is None, man["config_id"])] = rec["cid"]["sha256"]
                rec["arrays"] = {}
                for (role, sel), dd in per.items():
                    arr = {kk: np.concatenate(v) for kk, v in dd.items()}; per[(role, sel)] = arr; rec["arrays"][f"{role}__{sel}"] = dict(T1=stats(arr["T1"]), T2=stats(arr["T2"]), AX=dict(min=int(arr["AX"].min()), max=int(arr["AX"].max())), PL=dict(min=int(arr["PL"].min()), max=int(arr["PL"].max())))
                per_unit_arrays[name] = (man, per)
                rec["ok"] = bool(rec["manifest_sha256_ok"] and all(s["matches_manifest"] and s["inventory_bytes_match"] for s in shards) and man["formal"] == (a.mode == "accepted" or man["formal"]))
                if a.mode == "accepted" and not man["formal"]: rec["ok"] = False
            except Exception as ex: rec["ok"] = False; rec["error"] = repr(ex)
            rec["seconds"] = time.time() - rec.pop("tt"); R["units"][name] = rec
            if not rec["ok"]: R["failures"].append(name)
            print(f"{name}: {'ok' if rec['ok'] else 'FAIL'} ({rec['seconds']:.0f}s)", flush=True)
        # ---- cid correspondence model <-> reference per (purpose, batch); N0 + 3N0 structure
        corr = {}
        for (purpose, batch, is_ref, cid_), h in cid_hash.items():
            if is_ref or purpose == "w2_independent": continue                                                  # W2 position banks have no shared reference (position-specific latent)
            ref = cid_hash.get((purpose, batch, True, None)); corr[f"{purpose}/b{batch}/cfg{cid_}"] = dict(reference_present=(ref is not None), cid_equal=(ref == h))
        R["cid_correspondence"] = corr; R["cid_correspondence_ok"] = bool(corr) and all(v["cid_equal"] for v in corr.values()) if a.max_dirs is None else None
        struct_ok = True
        for name, (man, per) in per_unit_arrays.items():
            if man["purpose"] == "evaluation":
                want = spec["N0"] if man["batch_id"] == 0 else spec["N_max"] - spec["N0"]
                if a.mode == "accepted" and man["n_rows"] != want: struct_ok = False; R["failures"].append(f"{name}: rows {man['n_rows']} != N0/3N0 structure")
        R["n0_plus_3n0_structure_ok"] = struct_ok
        # ---- f32 sensitivity (registered rule; candidate evaluation)
        f32 = {}; gate_ok = True; any_pair = False; req_subset = spec["required_f32_subset"][fam]["config_id"]
        for name, (man, per) in per_unit_arrays.items():
            for role in man["roles"]:
                if (role, "float64") not in per or (role, "float32") not in per: continue
                any_pair = True; A, B = per[(role, "float64")], per[(role, "float32")]; flips = np.nonzero(A["AX"] != B["AX"])[0]
                sel64 = A["T1"]; rel = np.abs(A["T1"] - B["T1"]) / np.maximum(np.abs(A["T1"]), 1e-300)
                near = rel[flips] < REL_NEAR_TIE; ev64 = (A["T1"] <= T1_OBS) & (A["T2"] <= T2_OBS); ev32 = (B["T1"] <= T1_OBS) & (B["T2"] <= T2_OBS); mism = float(np.mean(ev64 != ev32)) if len(ev64) else 0.0
                evidence = []
                for i in flips[:2000]:
                    e = dict(row=int(i), AX=[int(A["AX"][i]), int(B["AX"][i])], PL=[int(A["PL"][i]), int(B["PL"][i])], T1=[float(A["T1"][i]), float(B["T1"][i])], T2=[float(A["T2"][i]), float(B["T2"][i])], event_B=[bool(ev64[i]), bool(ev32[i])], rel_dT1=float(rel[i]), near_tie=bool(rel[i] < REL_NEAR_TIE))
                    if ANTI is not None: e["antipode"] = bool(ANTI[A["AX"][i]] == B["AX"][i]); v1, v2 = AXV[A["AX"][i]], AXV[B["AX"][i]]; e["plane_angle_deg"] = float(np.degrees(np.arccos(np.clip(abs(float(v1 @ v2)), 0, 1))))
                    evidence.append(e)
                rec = dict(rows=int(len(sel64)), flips=int(len(flips)), flip_rate=float(len(flips) / max(1, len(sel64))), near_tie_flips_rel_lt_1e6=int(near.sum()), flips_rel_ge_1e6=int((~near).sum()), event_B_mismatch_rate=mism, event_B_mismatch_count=int(np.sum(ev64 != ev32)), plane_flip_rate=float(np.mean(A["PL"] != B["PL"])), registered_rule=dict(near_tie_relative=REL_NEAR_TIE, event_B_mismatch_bound=EVENT_B_MISMATCH_BOUND, target=[T1_OBS, T2_OBS]), passes_registered_rule=bool((~near).sum() == 0 and mism <= EVENT_B_MISMATCH_BOUND), evidence_truncated=(len(flips) > 2000), flip_evidence=evidence, diagnostics=dict(abs_dT1_max=float(np.abs(A["T1"] - B["T1"]).max()) if len(sel64) else 0.0, abs_dT2_max=float(np.abs(A["T2"] - B["T2"]).max()) if len(sel64) else 0.0, note="absolute differences are diagnostics only; the registered rule uses the relative selected-S+ difference"))
                if man["purpose"] == "evaluation" and man["config_id"] != req_subset: rec["note"] = "paired paths outside the required subset (diagnostic)"
                f32.setdefault(name, {})[role] = rec; gate_ok = gate_ok and rec["passes_registered_rule"]
        R["f32_sensitivity"] = f32; R["f32_registered_gate"] = dict(status=("CANDIDATE_EVALUATED" if any_pair else "NOT_EVALUATED"), all_pairs_pass_registered_rule=(bool(gate_ok) if any_pair else None), required_subset_config=req_subset, required_subset_checked=any(n_ == f"cfg{req_subset}_b0" for n_ in per_unit_arrays), w2_units_checked=sorted(n_ for n_ in per_unit_arrays if n_.endswith("_w2")), scope="candidate evaluation of the registered rule on the stored paired paths; formal acceptance is a separate audit decision; not a scientific statement")
        R["all_ok"] = (not R["failures"]) and all(u["ok"] for u in R["units"].values()) and (R["cid_correspondence_ok"] is not False) and struct_ok; R["stage"] = "complete"
        return finish(0 if (R["all_ok"] and R["coverage_complete"]) else 1)
    except Exception as ex:
        import traceback; R["failures"].append("exception: " + repr(ex)); R["traceback"] = traceback.format_exc(); R["stage"] = "exception"; return finish(1)


if __name__ == "__main__": sys.exit(main())
