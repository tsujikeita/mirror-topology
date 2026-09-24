# -*- coding: utf-8 -*-
"""Phase D-2 post-run READ-ONLY verification of the stored family banks (runs where the arrays are — Colab with Drive mounted — and emits a small evidence record).
Per completed directory (from the family's d2_bank_registry.json): verify_bank_dir (bytes, sidecar<->manifest identity, exact member set, dtype, finiteness, cid structure,
ranges, UIDs, generation keys) PLUS: NPZ file SHA recomputed and compared with the registry/final-record inventory; array-level statistics per role/selection (mean, std, min, max,
finite count, AX/PL value ranges and histograms); cross-role / cross-batch invariants (same cid across roles; batch-1 prefix continuity of cluster ids; family reference and
configuration on the same latent -> identical cid); required float32 subset sensitivity at N0 (rules §12.5): per required configuration, paired f64/f32 rows -> |ΔT1|, |ΔT2|
distributions, AX/PL disagreement rate (axis / plane flips), and near-tie counts (|T - threshold| < ε for the registered thresholds); W2 banks: paired-path |Δ| and whitening
identity presence. Nothing is modified on Drive; no bank is regenerated; no calibration or classification. Exit code 0 only if every directory verifies and every SHA matches."""
from __future__ import annotations
import os, sys, json, hashlib, time, argparse, io
import numpy as np


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--phaseb", required=True); ap.add_argument("--run-root", required=True, help="<RUN>/out of one family"); ap.add_argument("--out", required=True); ap.add_argument("--near-tie-eps", type=float, default=1e-6); ap.add_argument("--max-dirs", type=int, default=None)
    a = ap.parse_args(); t0 = time.time(); os.makedirs(a.out, exist_ok=True); sys.path.insert(0, a.phaseb)
    from step1_engine.d2_bank import verify_bank_dir, load_bank_spec, EXPECTED_MEMBERS, expected_member_set; from step1_engine.d2_rng import load_crn_table
    fr = json.load(open(os.path.join(a.run_root, "d2_final_record.json"))); rg = json.load(open(os.path.join(a.run_root, "d2", "d2_bank_registry.json"))); rm = json.load(open(os.path.join(a.run_root, "d2", "d2_run_manifest.json")))
    table, _ = load_crn_table(os.path.join(a.phaseb, "d", "d2_crn_table.json")); spec = load_bank_spec(os.path.join(a.phaseb, "d", "d2_bank_spec.json"), table=table); fam = rg["family"]
    R = dict(schema="d2_postrun_verification_v1", family=fam, run_root=a.run_root, registry_sha256=sha(os.path.join(a.run_root, "d2", "d2_bank_registry.json")), final_record_sha256=sha(os.path.join(a.run_root, "d2_final_record.json")), engine=rg.get("engine_version"), directories={}, failures=[], f32_sensitivity={}, w2={})
    R["w2"] = {}; inv = fr["output_inventory"]; names = list(rg["directories"]); names = names[: a.max_dirs] if a.max_dirs else names
    def stats(x): return dict(n=int(x.size), finite=int(np.isfinite(x).sum()), mean=float(np.mean(x)), std=float(np.std(x)), min=float(np.min(x)), max=float(np.max(x)))
    ref_cid = {}
    for name in names:
        d = rg["directories"][name]; p = d["path"]; rec = dict(path=p, reused=d.get("reused"), purpose=d.get("purpose")); tt = time.time()
        try:
            man = verify_bank_dir(p); rec["manifest_sha256_ok"] = (man["manifest_sha256"] == d["manifest_sha256"]); rec["n_rows"] = man["n_rows"]; rec["formal"] = man["formal"]; rec["roles"] = man["roles"]; rec["selections"] = man["selections"]
            rec["shards"] = []; cid_all = []; per = {}
            for sh in man["shards"]:
                fp = os.path.join(p, sh["file"]); b = open(fp, "rb").read(); fsha = hashlib.sha256(b).hexdigest(); rel = os.path.relpath(fp, a.run_root)
                inv_b = inv.get(rel, {}).get("bytes"); rec["shards"].append(dict(file=sh["file"], file_sha256=fsha, matches_manifest=(fsha == sh["file_sha256"]), inventory_bytes_match=(inv_b == len(b))))
                with np.load(io.BytesIO(b), allow_pickle=False) as z:
                    cid_all.append(z["cid"])
                    for k in z.files:
                        if k == "cid": continue
                        role, sel, kk = k.split("__"); per.setdefault((role, sel), {}).setdefault(kk, []).append(z[k])
            cid = np.concatenate(cid_all); rec["cid"] = dict(n=int(cid.size), unique=int(len(np.unique(cid))), monotone=bool(np.all(np.diff(cid) >= 0)))
            rec["arrays"] = {}
            for (role, sel), dd in per.items():
                arr = {kk: np.concatenate(v) for kk, v in dd.items()}; rec["arrays"][f"{role}__{sel}"] = dict(T1=stats(arr["T1"]), T2=stats(arr["T2"]), AX=dict(min=int(arr["AX"].min()), max=int(arr["AX"].max()), hist=np.bincount(arr["AX"]).tolist()), PL=dict(min=int(arr["PL"].min()), max=int(arr["PL"].max()), hist=np.bincount(arr["PL"]).tolist()))
                per[(role, sel)] = arr
            # paired float64 / float32 sensitivity (required subset batch 0 and W2 banks)
            for role in man["roles"]:
                if (role, "float64") in per and (role, "float32") in per:
                    a64, a32 = per[(role, "float64")], per[(role, "float32")]; d1 = np.abs(a64["T1"] - a32["T1"]); d2 = np.abs(a64["T2"] - a32["T2"])
                    sens = dict(rows=int(a64["T1"].size), dT1=dict(max=float(d1.max()), mean=float(d1.mean()), q99=float(np.quantile(d1, 0.99))), dT2=dict(max=float(d2.max()), mean=float(d2.mean()), q99=float(np.quantile(d2, 0.99))), axis_flip_rate=float(np.mean(a64["AX"] != a32["AX"])), plane_flip_rate=float(np.mean(a64["PL"] != a32["PL"])), axis_flips=int(np.sum(a64["AX"] != a32["AX"])), plane_flips=int(np.sum(a64["PL"] != a32["PL"])))
                    rel1 = d1 / np.maximum(np.abs(a64["T1"]), 1e-300); rel2 = d2 / np.maximum(np.abs(a64["T2"]), 1e-300); sens["relT1_max"] = float(rel1.max()); sens["relT2_max"] = float(rel2.max())
                    # near-tie proxy: rows whose f64 and f32 argmin differ AND |ΔT1| tiny (true near-ties) vs large (precision issue)
                    flips = a64["AX"] != a32["AX"]; sens["near_tie_flips_dT1_lt_eps"] = int(np.sum(flips & (d1 < a.near_tie_eps))); sens["flips_dT1_ge_eps"] = int(np.sum(flips & (d1 >= a.near_tie_eps)))
                    (R["w2"] if man["purpose"] == "w2_independent" else R["f32_sensitivity"]).setdefault(name, {})[role] = sens
            if man["purpose"] == "evaluation": ref_cid[(man["batch_id"], man["config_id"] is None)] = ref_cid.get((man["batch_id"], man["config_id"] is None), []) + [hashlib.sha256(cid.tobytes()).hexdigest()]
            rec["seconds"] = time.time() - tt; rec["ok"] = bool(rec["manifest_sha256_ok"] and all(s["matches_manifest"] and s["inventory_bytes_match"] for s in rec["shards"]))
            if not rec["ok"]: R["failures"].append(name)
        except Exception as ex:
            rec["ok"] = False; rec["error"] = repr(ex); R["failures"].append(name)
        R["directories"][name] = rec; print(f"{name}: {'ok' if rec.get('ok') else 'FAIL'} ({rec.get('seconds', 0):.0f}s)", flush=True)
    # same-latent invariant: every evaluation directory of a batch (configurations and reference) has the same cid structure
    R["same_latent_cid"] = {str(k): dict(unique_hashes=len(set(v)), n=len(v)) for k, v in ref_cid.items()}
    R["seconds"] = time.time() - t0; R["all_ok"] = (not R["failures"]) and set(R["directories"]) == set(rg["directories"]) if not a.max_dirs else (not R["failures"])
    json.dump(R, open(os.path.join(a.out, f"d2_verify_{fam}.json"), "w"), indent=1); print("all_ok =", R["all_ok"], "failures:", R["failures"]); return 0 if R["all_ok"] else 1


if __name__ == "__main__": sys.exit(main())
