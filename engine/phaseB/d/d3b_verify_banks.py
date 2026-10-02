# -*- coding: utf-8 -*-
"""Phase D-3b post-run READ-ONLY verification of ONE stored partition run (family x size; 9 added configurations, 27 units, 45 NPZ) — v0.1 (structure of the accepted D-2 verifier
d2_verify_banks v0.2: RV-1 accepted-run binding, RV-1.5 verifier source, RV-2 output isolation; no f32 / W2 paths in D-3b).
MODES: --mode accepted (default): the run under RUN_ROOT must be one of the nine ACCEPTED generation runs of registered_assets/d3b/d3b_generation_ledger.json (partition, run id,
final / registry / run-manifest / launcher SHAs, unit set with completion-manifest SHAs and expected NPZ file SHAs / byte counts) and the ledger itself must equal its re-derivation
from the registered records and the d3 pins (d3b_ledger.intake_registered_d3b_units); anything else is refused BEFORE any array is read. --mode test: synthetic banks of the
generator's self-test (accepted_run_binding=False, verification_scope='test'; results are never evidence about the registered banks).
VERIFIER SOURCE: the verifier's module SHA map, script SHA and the registered ledger bytes are checked against the phaseB inventory and recorded as verifier_source, separate from
generator_source (the accepted 0.93.0 commit of the ledger) and the verification_environment. OUTPUT: --out is resolved by realpath, must not lie inside / equal / contain RUN_ROOT or
any referenced bank directory, must be a fresh directory; every output file is created exclusively (O_EXCL). Inputs are never written.
INTEGRITY (per unit, through step1_engine.d3_bank.verify_twelve_bank_dir against the verified TwelveContext): manifest schema / SHA / completeness, identities (table / spec v1 /
spec v2 / receipt / map / seed / wave), configuration identity vs spec v2, generation call keys, every shard's bytes == sidecar / manifest SHA, exact member set, dtypes, finiteness,
cid structure, contiguous ranges, UID ends, every ARRAY's SHA == sidecar; plus manifest SHA == ledger, NPZ file SHA == ledger expectation (== final-record byte count), per-array
statistics, cid equality across the 9 configurations of the partition per (purpose, batch) (same family latent), optional cid equality with the accepted D-2 family reference
(--d2-ref-root: ref_<F>_b0 / b1 / fit re-verified through the reuse binding), N0 + 3N0 structure. COVERAGE: --max-dirs (positive int) => verification_scope '*_partial',
coverage_complete=False; exit 0 only for complete + all units ok. The result carries all_ok / coverage_complete — never a scientific support / strong statement."""
from __future__ import annotations
import os, sys, json, hashlib, time, argparse, io
import numpy as np


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _excl_write(path: str, data: bytes):
    if os.path.lexists(path): raise RuntimeError(f"output exists / alias refused: {path}")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o644)
    with os.fdopen(fd, "wb") as fh: fh.write(data)


def _json_snapshot(path):
    """Authenticate and decode the same captured bytes, never separate path reads; duplicate keys and non-finite constants refused."""
    data = open(path, "rb").read()
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    def invalid(value): raise ValueError(f"nonfinite JSON constant: {value}")
    return data, json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)



def _verified_reference_cid(directory, manifest):
    """Extract cid only from bytes matching the previously verified manifest.

    The full D-2 validator checks file/member/array contracts before this helper.
    Re-reading a live path is permitted only when these captured bytes match the
    exact file identity that passed that validator. Decode the SAME bytes used
    for this check; a later filesystem change cannot change this snapshot.
    """
    cids = []; files = []
    for shard in manifest["shards"]:
        path = os.path.join(directory, shard["file"])
        data = open(path, "rb").read()
        digest = hashlib.sha256(data).hexdigest()
        if digest != shard["file_sha256"]:
            raise ValueError(f"D-2 reference changed after verification: {path}")
        with np.load(io.BytesIO(data), allow_pickle=False) as z:
            cids.append(np.array(z["cid"], copy=True))
        files.append(dict(file=shard["file"], file_sha256=digest, bytes=len(data)))
    if not cids:
        raise ValueError("D-2 reference has no verified cid shards")
    cid = np.concatenate(cids)
    return hashlib.sha256(np.ascontiguousarray(cid).tobytes()).hexdigest(), dict(
        manifest_sha256=manifest["manifest_sha256"], n_rows=int(cid.size), shards=files)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--phaseb", required=True); ap.add_argument("--run-root", required=True, help="the partition run's OUT directory (…/<FAMILY>_<SIZE>_<run id>/out)"); ap.add_argument("--out", required=True); ap.add_argument("--mode", choices=("accepted", "test"), default="accepted")
    ap.add_argument("--max-dirs", type=int, default=None); ap.add_argument("--path-map", action="append", default=[], help="OLD=NEW physical path mapping for relocated caches (recorded; logical names stay those of the accepted record)")
    ap.add_argument("--d2-ref-root", default=None, help="optional: directory holding the accepted D-2 family reference units ref_<F>_b0 / _b1 / _fit (re-verified through the reuse binding; cid equality with every configuration unit)")
    a = ap.parse_args(); t0 = time.time()
    if a.max_dirs is not None and (a.max_dirs < 1): print("--max-dirs must be a positive integer", file=sys.stderr); return 2
    run_root = os.path.realpath(a.run_root); out = os.path.realpath(a.out)
    if os.path.islink(os.path.abspath(a.out)): print("symlink output directory refused", file=sys.stderr); return 2
    def inside(p, q): p, q = os.path.realpath(p), os.path.realpath(q); return p == q or p.startswith(q.rstrip(os.sep) + os.sep)
    if inside(out, run_root) or inside(run_root, out): print("output must be disjoint from the run root", file=sys.stderr); return 2
    if os.path.lexists(out) and (not os.path.isdir(out) or os.path.islink(out) or os.listdir(out)): print("output must be a fresh (non-existent or empty) real directory", file=sys.stderr); return 2
    sys.path.insert(0, a.phaseb); R = dict(schema="d3b_postrun_verification_v1", mode=a.mode, run_root=run_root, out=out, stage="init", failures=[], notes=[], accepted_run_binding=None, verification_scope=None)
    output_safe = False; protected = []
    def finish(code):
        R["seconds"] = time.time() - t0; R["exit_code"] = code
        if not output_safe or any(inside(out, p) or inside(p, out) for p in protected):
            print(json.dumps(R, indent=1, default=str), file=sys.stderr); return code if code else 2
        os.makedirs(out, exist_ok=True); _excl_write(os.path.join(out, f"d3b_verify_{R.get('family', 'unknown')}_{R.get('size_id', 'unknown')}.json"), json.dumps(R, indent=1, default=str).encode())
        print("all_ok =", R.get("all_ok"), "| coverage_complete =", R.get("coverage_complete"), "| stage:", R["stage"], "| failures:", R["failures"][:5]); return code
    try:
        pmap = dict(x.split("=", 1) for x in a.path_map); R["path_map"] = pmap
        if len(pmap) != len(a.path_map) or any(not old or not new for old, new in pmap.items()): raise ValueError("empty or duplicate path-map prefix")
        def phys(p):
            for old, new in sorted(pmap.items(), key=lambda x: len(x[0]), reverse=True):
                old = old.rstrip(os.sep)
                if p == old or p.startswith(old + os.sep): return new.rstrip(os.sep) + p[len(old):]
            return p
        rg_p = os.path.join(run_root, "d3b", "d3_bank_registry.json"); rm_p = os.path.join(run_root, "d3b", "d3_run_manifest.json"); fr_p = os.path.join(run_root, "d3b_final_record.json"); lk_p = os.path.join(run_root, "launcher_lock.json")
        rgb, rg = _json_snapshot(rg_p); rmb, rm = _json_snapshot(rm_p)
        frb, fr = _json_snapshot(fr_p) if os.path.isfile(fr_p) else (None, None); lkb, lk = _json_snapshot(lk_p) if os.path.isfile(lk_p) else (None, None)
        fam = rg.get("family"); sizes = rg.get("sizes"); R["family"] = fam if fam in ("E2", "E7", "E8") else "unknown"; R["size_id"] = sizes[0] if isinstance(sizes, list) and len(sizes) == 1 and sizes[0] in ("L1.00", "L1.20", "L1.50") else "unknown"
        # Protect every input, including D-2 references and targets of symlinked
        # units in a relocated run, BEFORE even failure reports may be written.
        # Retain paths rather than only their resolved targets so finish() also
        # checks the current resolution at the publication boundary.
        protected = [run_root, os.path.abspath(a.phaseb)]
        protected += [phys(d["path"]) for d in rg["directories"].values()]
        protected += [os.path.join(run_root, "d3b", name) for name in rg["directories"]]
        if a.d2_ref_root:
            protected.append(os.path.abspath(a.d2_ref_root))
            protected += [os.path.join(a.d2_ref_root, f"ref_{fam}_{suffix}") for suffix in ("b0", "b1", "fit")]
        if any(inside(out, p) or inside(p, out) for p in protected): R["stage"] = "output"; R["failures"].append("output overlaps a referenced bank"); return finish(2)
        output_safe = True
        # ---- verifier source (separate from the generator source)
        from step1_engine import __version__; from step1_engine.checkpoint import module_shas; from step1_engine.official_gate import current_env
        invb, inv = _json_snapshot(os.path.join(a.phaseb, "B2_completion_inventory.json")); me = os.path.abspath(__file__)
        vs_ok = (inv["modules"] == module_shas() and inv["engine_version"] == __version__ and inv.get("d_sha256", {}).get("d/d3b_verify_banks.py") == sha(me))
        ledger_p = os.path.join(a.phaseb, "registered_assets", "d3b", "d3b_generation_ledger.json"); ledger_ok = os.path.isfile(ledger_p) and (inv.get("registered_assets_sha256", {}).get("registered_assets/d3b/d3b_generation_ledger.json") == sha(ledger_p))
        R["verifier_source"] = dict(engine=__version__, inventory_sha256=hashlib.sha256(invb).hexdigest(), script_sha256=sha(me), modules_digest=hashlib.sha256(json.dumps(module_shas(), sort_keys=True).encode()).hexdigest(), source_bound=bool(vs_ok), ledger_bound=bool(ledger_ok)); R["verification_environment"] = current_env()
        if not (vs_ok and ledger_ok): R["failures"].append("verifier source / ledger not bound to the inventory"); R["stage"] = "verifier_source"; return finish(1)
        from step1_engine.d3_profile import twelve_context, load_registered_bank_spec_v2
        from step1_engine.d3_bank import verify_twelve_bank_dir, verify_reused_reference_dir, CONFIG_ROLES
        from step1_engine.d3b_ledger import intake_registered_d3b_units
        ctx = twelve_context(a.phaseb); spec2 = load_registered_bank_spec_v2(ctx); units_reg = intake_registered_d3b_units(a.phaseb, ctx); R["context_identities"] = dict(ctx.identities); R["d3b_ledger_sha256"] = units_reg.ledger_sha256
        if R["family"] == "unknown" or R["size_id"] == "unknown": R["failures"].append("registry family / size"); R["stage"] = "inputs"; return finish(1)
        cfgs = sorted(c["config_id"] for c in spec2["configurations"].values() if c["family"] == fam and c["size_id"] == R["size_id"] and c["mode"] == "generate_D3b"); required = [f"cfg{c}_{x}" for c in cfgs for x in ("b0", "b1", "fit")]; R["required_units"] = required
        # ---- accepted-run binding (RV-1)
        if a.mode == "accepted":
            key = f"{fam}_{R['size_id']}"; parts = units_reg.partitions; L = parts.get(key)
            if L is None: R["failures"].append("partition not in the ledger"); R["stage"] = "binding"; return finish(1)
            if frb is None or lkb is None: R["failures"].append("final record / launcher lock missing"); R["stage"] = "binding"; return finish(1)
            exp = {k: L["records"][k] for k in ("final_record_sha256", "bank_registry_sha256", "run_manifest_sha256", "launcher_lock_sha256")}; got = dict(final_record_sha256=hashlib.sha256(frb).hexdigest(), bank_registry_sha256=hashlib.sha256(rgb).hexdigest(), run_manifest_sha256=hashlib.sha256(rmb).hexdigest(), launcher_lock_sha256=hashlib.sha256(lkb).hexdigest())
            diff = [k for k in exp if exp[k] != got.get(k)]
            if diff: R["failures"].append(f"run records differ from the accepted ledger: {diff}"); R["record_sha256"] = dict(expected=exp, got=got); R["stage"] = "binding"; return finish(1)
            if not (rm.get("stage") == "complete" and rm.get("D3B_PASS") is True and not rm.get("failures") and rg.get("formal") is True and fr.get("D3B_PASS") is True): R["failures"].append("accepted run record is not a complete formal D3B_PASS run"); R["stage"] = "binding"; return finish(1)
            if set(L["units"]) != set(required) or set(rg["directories"]) != set(required): R["failures"].append("unit set differs from the ledger / bank spec v2"); R["stage"] = "binding"; return finish(1)
            for n_ in required:
                if rg["directories"][n_]["manifest_sha256"] != L["units"][n_]["manifest_sha256"]: R["failures"].append(f"{n_}: registry manifest SHA differs from the ledger"); R["stage"] = "binding"; return finish(1)
            R["accepted_run_binding"] = True; R["generator_source"] = dict(engine=units_reg.source_lock["engine_version"], commit=units_reg.source_lock["commit"], inventory_sha256=units_reg.source_lock["inventory_sha256"], run_id=L["run_id"], environment_fingerprint=L["environment_fingerprint"], producer_digest=L["producer_digest"]); R["verification_scope"] = "accepted_full"; expected_units = L["units"]
        else:
            R["accepted_run_binding"] = False; R["verification_scope"] = "test"; R["generator_source"] = dict(engine=rg.get("engine_version"), note="test mode: unbound synthetic banks"); R["notes"].append("test mode: no accepted-run binding; results are not evidence about the registered banks"); expected_units = None
            if set(rg["directories"]) != set(required): R["failures"].append("unit set differs from bank spec v2 for this partition"); R["stage"] = "binding"; return finish(1)
        for n_ in required:
            p = os.path.realpath(phys(rg["directories"][n_]["path"]))
            if inside(out, p) or inside(p, out): R["failures"].append(f"output overlaps bank directory {n_}"); R["stage"] = "output"; return finish(2)
        logical_root = L["run_root"] if a.mode == "accepted" else None; R["logical_run_root"] = logical_root
        if logical_root is not None and os.path.realpath(logical_root) != run_root and not any(logical_root == o.rstrip(os.sep) for o in pmap):
            pmap[logical_root] = run_root; R["path_map"] = pmap; R["notes"].append("accepted run relocated: logical run root mapped to RUN_ROOT (names stay those of the accepted record)")
        # Automatic relocation may have changed the physical paths. Confirm
        # the final mapping, not just the original logical Drive locations.
        protected += [phys(rg["directories"][name]["path"]) for name in required]
        if any(inside(out, p) or inside(p, out) for p in protected):
            output_safe = False; R["stage"] = "output"
            R["failures"].append("output overlaps a resolved input after relocation")
            return finish(2)
        def inventory_name(name, shard_file):
            original = os.path.join(rg["directories"][name]["path"], shard_file)
            if logical_root is not None: return os.path.relpath(original, logical_root)
            canonical = os.path.join("d3b", name, shard_file)
            if fr is not None and canonical in fr.get("output_inventory", {}): return canonical
            return os.path.relpath(original, run_root)
        # ---- optional D-2 family reference (fixed input; cid correspondence)
        ref_cid = {}
        if a.d2_ref_root:
            try:
                reference_units = {}
                for b in (0, 1):
                    name = f"ref_{fam}_b{b}"; directory = os.path.join(a.d2_ref_root, name)
                    rman = verify_reused_reference_dir(directory, ctx, fam, name)
                    ref_cid[("evaluation", b)], reference_units[name] = _verified_reference_cid(directory, rman)
                name = f"ref_{fam}_fit"; directory = os.path.join(a.d2_ref_root, name)
                rman = verify_reused_reference_dir(directory, ctx, fam, name)
                ref_cid[("fitting", 0)], reference_units[name] = _verified_reference_cid(directory, rman)
                R["d2_reference"] = dict(root=a.d2_ref_root, verified=True, cid_sha256={f"{k[0]}/b{k[1]}": v for k, v in ref_cid.items()}, units=reference_units)
            except Exception as ex_:
                R["d2_reference"] = dict(root=a.d2_ref_root, verified=False, error=repr(ex_)); R["failures"].append("--d2-ref-root does not hold the accepted D-2 family reference units"); R["stage"] = "d2_reference"; return finish(1)
        else: R["d2_reference"] = None
        # ---- per-unit integrity
        names = required if a.max_dirs is None else required[: a.max_dirs]; R["verification_scope"] = R["verification_scope"] if a.max_dirs is None else (R["verification_scope"] + "_partial"); R["coverage_complete"] = (a.max_dirs is None); R["checked_units"] = names; R["unchecked_units"] = [n_ for n_ in required if n_ not in names]
        inv_files = fr.get("output_inventory", {}) if fr is not None else None; R["units"] = {}; cid_hash = {}; rows_by_unit = {}
        def stats(x): return dict(n=int(x.size), finite=int(np.isfinite(x).sum()), mean=float(np.mean(x)), std=float(np.std(x)), min=float(np.min(x)), max=float(np.max(x)))
        for name in names:
            d = rg["directories"][name]; p = phys(d["path"]); rec = dict(path=p, purpose=d.get("purpose"), tt=time.time())
            try:
                man = verify_twelve_bank_dir(p, ctx, sorted(CONFIG_ROLES)); rec["manifest_sha256"] = man["manifest_sha256"]; rec["manifest_sha256_ok"] = (man["manifest_sha256"] == d["manifest_sha256"] and (expected_units is None or expected_units[name]["manifest_sha256"] == man["manifest_sha256"]))
                rec["n_rows"] = man["n_rows"]; rec["formal"] = man["formal"]; rec["roles"] = man["roles"]; rec["selections"] = man["selections"]; rec["config_id"] = man["config_id"]; rec["batch_id"] = man["batch_id"]; rec["arrays_verified_against_sidecar"] = True
                shards = []; cids = []; per = {}
                for sh in man["shards"]:
                    fp = os.path.join(p, sh["file"]); b = open(fp, "rb").read(); fsha = hashlib.sha256(b).hexdigest(); rel = inventory_name(name, sh["file"])
                    exp_npz = expected_units[name]["npz"][sh["file"]] if expected_units is not None else None
                    shards.append(dict(file=sh["file"], file_sha256=fsha, bytes=len(b), matches_manifest=(fsha == sh["file_sha256"]), matches_ledger=(None if exp_npz is None else (fsha == exp_npz["sha256"] and len(b) == exp_npz["bytes"])), inventory_bytes_match=(None if inv_files is None else (inv_files.get(rel, {}).get("bytes") == len(b)))))
                    with np.load(io.BytesIO(b), allow_pickle=False) as z:
                        cids.append(np.asarray(z["cid"]))
                        for k in z.files:
                            if k == "cid": continue
                            role, sel, kk = k.split("__"); per.setdefault((role, sel), {}).setdefault(kk, []).append(np.asarray(z[k]))
                rec["shards"] = shards; cid = np.concatenate(cids); rec["cid"] = dict(n=int(cid.size), unique=int(len(np.unique(cid))), monotone=bool(np.all(np.diff(cid) >= 0)), sha256=hashlib.sha256(np.ascontiguousarray(cid).tobytes()).hexdigest())
                cid_hash[(man["purpose"], man["batch_id"], man["config_id"])] = rec["cid"]["sha256"]; rows_by_unit[name] = (man["purpose"], man["batch_id"], man["n_rows"])
                rec["arrays"] = {}
                for (role, sel), dd in per.items():
                    arr = {kk: np.concatenate(v) for kk, v in dd.items()}; rec["arrays"][f"{role}__{sel}"] = dict(T1=stats(arr["T1"]), T2=stats(arr["T2"]), AX=dict(min=int(arr["AX"].min()), max=int(arr["AX"].max())), PL=dict(min=int(arr["PL"].min()), max=int(arr["PL"].max())))
                rec["ok"] = bool(rec["manifest_sha256_ok"] and all(s["matches_manifest"] and s["matches_ledger"] is not False and s["inventory_bytes_match"] is not False for s in shards) and (man["formal"] or a.mode == "test"))
            except Exception as ex: rec["ok"] = False; rec["error"] = repr(ex)
            rec["seconds"] = time.time() - rec.pop("tt"); R["units"][name] = rec
            if not rec["ok"]: R["failures"].append(name)
            print(f"{name}: {'ok' if rec['ok'] else 'FAIL'} ({rec['seconds']:.0f}s)", flush=True)
        # ---- cid correspondence across the partition's configurations (same family latent) and with the D-2 reference (if supplied)
        corr = {}
        for (purpose, batch, cid_), h in cid_hash.items():
            peers = {h2 for (p2, b2, c2), h2 in cid_hash.items() if p2 == purpose and b2 == batch}
            corr[f"{purpose}/b{batch}/cfg{cid_}"] = dict(equal_across_partition=(len(peers) == 1), reference_present=((purpose, batch) in ref_cid), equal_to_d2_reference=(None if (purpose, batch) not in ref_cid else ref_cid[(purpose, batch)] == h))
        R["cid_correspondence"] = corr; R["cid_correspondence_ok"] = (bool(corr) and all(v["equal_across_partition"] and v["equal_to_d2_reference"] is not False for v in corr.values())) if a.max_dirs is None else None
        struct_ok = True
        for name, (purpose, batch, n) in rows_by_unit.items():
            want = 200_000 if purpose == "fitting" else (spec2["N0"] if batch == 0 else spec2["N_max"] - spec2["N0"])
            if a.mode == "accepted" and n != want: struct_ok = False; R["failures"].append(f"{name}: rows {n} != N0/3N0/N_fit structure")
        R["n0_plus_3n0_structure_ok"] = struct_ok
        R["all_ok"] = (not R["failures"]) and all(u["ok"] for u in R["units"].values()) and (R["cid_correspondence_ok"] is not False) and struct_ok; R["stage"] = "complete"
        return finish(0 if (R["all_ok"] and R["coverage_complete"]) else 1)
    except Exception as ex:
        import traceback; R["failures"].append("exception: " + repr(ex)); R["traceback"] = traceback.format_exc(); R["stage"] = "exception"; return finish(1)


if __name__ == "__main__": sys.exit(main())
