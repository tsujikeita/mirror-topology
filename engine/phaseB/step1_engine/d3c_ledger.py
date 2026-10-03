# -*- coding: utf-8 -*-
"""D-3c profile ledger + outer receipt (registered_assets/d3c): the three accepted FORMAL twelve-position profile runs (E2 / E7 / E8; one attempt each; commit 7a2b1774, engine
0.99.0; Colab High-RAM CPU) whose ORIGINAL records (launcher lock, final record, launcher stdout/stderr, profile record, plan identity document, script log, inner archive,
executed notebook) were accepted by the ChatGPT post-execution acceptance (D3c_profile_runs_7a2b1774_acceptance.json: PASS_WITH_EXPLICIT_SCOPE__TRANCHE2_REGISTRATION_
IMPLEMENTATION_GO, with independently reproduced full-scale plan identities). The originals are registered byte-for-byte (the inner archives' members ARE the registered files)
and are never rewritten when the engine / pins version changes: the execution source (commit / inventory / script / pins / ledger / receipt file SHAs at 0.99.0) is a CONSTANT
of this module (EXECUTION_LOCK), not re-read from the current tree.
build_d3c_profile_ledger(root, ctx) is a DETERMINISTIC re-derivation: every registered original is re-read and bound to EXECUTION_LOCK, to the accepted attempt ids, to the
registered D-2 / D-3b ledgers (input runs, unit manifests of all 72 supplies, family reference), to the verified TwelveContext (context identities), to the registered constants
(B / B_KDE / seeds / K_fit / N0 / N_max / m / CRN groups), to the REQUIRED gate inventory, the official gate record (mode official, live_collected, 330 profile checks and
14 twelve checks all passed), the fingerprints (before == after), the plan-object identity, the plan document (payload identity, ordered UIDs, publication receipt) and to the
acceptance document (file bytes == constant SHA; its per-family entries == the re-derivation). verify_d3c_profile_ledger requires equality with that re-derivation (an edited
ledger, even re-stamped, is refused); load_registered_d3c_ledger binds the committed file to the d3 pins (d3c_ledger_sha256).
The outer receipt (build_d3c_outer_receipt) binds the ledger (payload + file SHA), the acceptance constants + file bytes and the per-family identities; it is bound to the pins
(d3c_outer_receipt_sha256). intake_registered_d3c_profiles(root, ctx) returns the sealed D3cProfiles consumed by calibration (D-4): registered plan identity / ordered UIDs /
fingerprints / gate record per family, rebuild_registered_plans (the consumer's plans are REBUILT from the registered ordered UIDs and must reproduce the accepted identity) and
verify_consumer_inputs / verify_consumer_family_inputs (a consumer's inputs are refused unless both fingerprints, the plan objects and the plan identity equal the accepted ones;
no self-asserted PASS flag or old success is accepted). Nothing here evaluates thresholds, labels, calibration, D-2W or noise."""
from __future__ import annotations
import copy, hashlib, json, os, zipfile
from typing import Dict, Optional
from .errors import InputContractError
from .d3_profile import TwelveContext, _require_ctx, load_registered_bank_spec_v2, fix_family_plans, verify_plan_identity, _payload_sha as _plan_payload_sha, PLAN_SCHEMA_V2
from .d3b_ledger import load_registered_d3b_ledger, load_registered_d3b_outer_receipt, _env_identity
from .rules_config import RULES
from .official_gate import B_KDE as REG_B_KDE, N_FIT as REG_N_FIT, M_FIT as REG_M_FIT, EXPECTED_VERS

LEDGER_SCHEMA = "d3c_profile_ledger_v1"; RECEIPT_SCHEMA = "d3c_outer_receipt_v1"
EXECUTION_LOCK = dict(commit="7a2b17749e88074834bf5bebe3ebd8ac8af5dd29", engine_version="0.99.0", inventory_sha256="c0b0333b2f4250f1498c04b30090a1449d8135983264052bf602941852e580a9",
                      script_sha256="9f243b08a5aa8ba0cc3ded42343fb8d99717dc4bd50ebf26a7cc9a519221638d", notebook_sha256="4ad3ba0ac86ff20508aa4bd32784449f5824c5fff2c19712f7c6eb464d7ff54a",
                      pins_sha256="136d238f84896d3c838b9972622076ba095486bee1cbd91f19460a4440063a46", d3b_ledger_file_sha256="bdaa8aeb9b3e591d73540c4edce482c3f59f6edcafa0f21f171332102c624837", d3b_receipt_file_sha256="ed0fbccba739f26a906da0948885d3b4205ca6c58d5aa8338a62c877b166dabb",
                      source_archive=dict(file="phaseB_D3c_tranche1_v3_0.99.0.zip", sha256="2f6a89b9d8145168e6d25dfa8487199ebcec6c4a51aa96328aba47f4b57fad22", bytes=15945925),
                      preexecution_authorization=dict(file="D3c_tranche1_v3_0.99.0_audit_decision.json", sha256="ef2e7db0a381a0d6278cc6361b16e76eff37e4927beb75a89390b6f2f4bdce93", bytes=7807, decision="PASS_WITH_EXPLICIT_SCOPE_AND_LOCKED_EXECUTION_GO"),
                      runtime="Colab High-RAM CPU (RAM total 54,750,404,608 bytes); STAGE_LOCAL=True, STAGE_ROOT=/content/stage; one family per run, E2 -> E7 -> E8")
PROFILE_ACCEPTANCE = dict(decision_file="D3c_profile_runs_7a2b1774_acceptance.json", decision_sha256="de8fa49f40a897ee74289c26fa798cad8faa142af9566e5d0a36de93a20b0f04", decision_bytes=16559,
                          audit_md="ChatGPT_audit_D3c_profile_runs_7a2b1774.md", audit_md_sha256="426c3361a5d0899b241400ef9455e5d6eb896e1c33e7a8cba6523b0cb7ad4c2e", audit_md_bytes=15845,
                          run_packet="D3c_profile_runs_7a2b1774_audit_packet.zip", run_packet_sha256="775683fd20ca3d3295cca0a287c7b6b5a7fb2f142aa52072355c619c7c0008b0", run_packet_bytes=428182,
                          decision="PASS_WITH_EXPLICIT_SCOPE__TRANCHE2_REGISTRATION_IMPLEMENTATION_GO", accepted_scope="AUDITED_COLAB_OFFICIAL_PROFILE_EXECUTION_RECORDS_AND_INDEPENDENTLY_REPRODUCED_PLAN_IDENTITIES", date_JST="2026-10-03",
                          independent_plan_reconstruction="full registered scale (B 2000 / B_KDE 2000 / seeds 5 / K0 10000 / K1 30000 / K_fit 2000): 45 multiplicity arrays and all three identities reproduced by the auditor",
                          not_approved=["tranche 2 registration API (this module) until its own review", "D-4 calibration execution", "thresholds / labels / calibration / D-2W / noise / ENGINE_VALID", "E1 twelve-position profile", "independent re-read of the production NPZ by the auditor", "remote Git full-tree comparison"])
FAMILIES = ("E2", "E7", "E8"); SIZES = ("L1.00", "L1.20", "L1.50")
ATTEMPTS = {"E2": "20261003T083353Z_dc4ddf4f0f", "E7": "20261003T090646Z_106fe1bd17", "E8": "20261003T093536Z_cb05343c01"}
INNER_ARCHIVES = {"E2": dict(file="d3c_profile_E2_7a2b17749e88.zip", sha256="4cd9a8d0f3e6f045bc8900fdd3086cab215b82ccef0a4478b029333d94d38ee4", bytes=128233),
                  "E7": dict(file="d3c_profile_E7_7a2b17749e88.zip", sha256="4783fc1f0eac2e83410cb3262b98535bae9321d8d3759223dbcff132ead99c8e", bytes=128230),
                  "E8": dict(file="d3c_profile_E8_7a2b17749e88.zip", sha256="49b6591d5c8d0228e6356232d69dce8d15d380c683b387dc890b1f4eb5a65a81", bytes=128226)}
EXECUTED_NOTEBOOKS = {"E2": dict(file="MirrorTopology_Step1_D3c_profile_v0_1_E2_executed_7a2b17749e88.ipynb", sha256="c95b067ba1012eba7bb9408659c88c0081f9aadba088e85555e5df407d04bd82", bytes=33682),
                      "E7": dict(file="MirrorTopology_Step1_D3c_profile_v0_1_E7_executed_7a2b17749e88.ipynb", sha256="64b2a18fed15b4eb3635fc2f9093474ceb256473d6cd4e82ba911e43ebfc21b1", bytes=33682),
                      "E8": dict(file="MirrorTopology_Step1_D3c_profile_v0_1_E8_executed_7a2b17749e88.ipynb", sha256="611dae39670eeb60bd33b9ffc679852c4ffb158b3b2b0fd00c60b04a3b4f2947", bytes=33646)}
REQUIRED_GATES = ("G_pins_loaded", "G_engine_inventory", "G_script_sha", "G_phaseC_members", "G_env_lock", "G_external_loader_sha", "G_twelve_context", "G_bank_spec_v2", "G_d3b_units_accepted", "G_inputs_resolved", "G_all_supplies", "G_uids_ordered", "G_plans_fixed", "G_size_inputs", "G_family_assembled", "G_gate_passed", "G_identity_stable", "G_record_saved")
N_PROFILE_CHECKS = 330; N_TWELVE_CHECKS = 14; N_SUPPLIES = 72; N_FIRST_WAVE = 18; N_ADDED = 54
_TOKEN = object()


def _sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()


def _read(p: str) -> bytes:
    if not os.path.isfile(p): raise InputContractError(f"registered D-3c record missing: {p}")
    return open(p, "rb").read()


def _json(p: str):
    b = _read(p)
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out: raise ValueError(f"duplicate key {k}")
            out[k] = v
        return out
    try: return b, json.loads(b.decode("utf-8"), object_pairs_hook=pairs, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
    except ValueError as ex: raise InputContractError(f"registered D-3c record is not strict finite JSON: {p}") from ex


def _payload_sha(doc: dict, key: str) -> str: return _sha(json.dumps({k: v for k, v in doc.items() if k != key}, sort_keys=True, allow_nan=False, ensure_ascii=False).encode("utf-8"))


def _d3c_root(root: str) -> str: return os.path.join(os.path.abspath(root), "registered_assets", "d3c")


def _fail(key: str, what: str): raise InputContractError(f"{key}: {what}")


def _check_family(root: str, ctx: TwelveContext, fam: str, d2l: dict, d3bl: dict, spec2: dict, pins_env: dict) -> dict:
    """Re-read and bind ONE family's registered originals; returns the ledger entry (raises on any inconsistency)."""
    att = ATTEMPTS[fam]; key = f"{fam}_{att}"; d = os.path.join(_d3c_root(root), "runs", key); run = os.path.join(d, f"run_{att}"); EL = EXECUTION_LOCK
    lkb, lk = _json(os.path.join(d, "profile_lock.json")); fnb, fn = _json(os.path.join(d, "profile_final_record.json")); so = _read(os.path.join(d, f"profile_stdout_{att}.txt")); se = _read(os.path.join(d, f"profile_stderr_{att}.txt"))
    rb, rec = _json(os.path.join(run, f"d3c_profile_record_{fam}.json")); pb, pdoc = _json(os.path.join(run, f"d3c_plan_identity_{fam}.json")); lg = _read(os.path.join(run, "d3c_profile_stdout.log"))
    files = {"profile_lock.json": lkb, "profile_final_record.json": fnb, f"profile_stdout_{att}.txt": so, f"profile_stderr_{att}.txt": se, f"run_{att}/d3c_profile_record_{fam}.json": rb, f"run_{att}/d3c_plan_identity_{fam}.json": pb, f"run_{att}/d3c_profile_stdout.log": lg}
    if sorted(os.listdir(d)) != sorted(["profile_lock.json", "profile_final_record.json", f"profile_stdout_{att}.txt", f"profile_stderr_{att}.txt", f"run_{att}"]) or sorted(os.listdir(run)) != sorted([f"d3c_profile_record_{fam}.json", f"d3c_plan_identity_{fam}.json", "d3c_profile_stdout.log"]): _fail(key, "registered run directory must hold exactly the seven original files of the accepted attempt (no superseded records, no other attempts)")
    # ---- launcher lock == execution lock constants + the registered input runs
    want_lock = dict(schema="d3c_launcher_lock_v2", commit=EL["commit"], inventory_sha256=EL["inventory_sha256"], script_sha256=EL["script_sha256"], inventory_script_sha256=EL["script_sha256"], ledger_file_sha256=EL["d3b_ledger_file_sha256"], ledger_sha256=d3bl["ledger_sha256"], receipt_file_sha256=EL["d3b_receipt_file_sha256"], receipt_sha256=ctx._d["pins"]["d3b_outer_receipt_sha256"], pins_sha256=EL["pins_sha256"], engine=EL["engine_version"], family=fam, stage_local=True, stage_root="/content/stage")
    if any(lk.get(k) != v for k, v in want_lock.items()): _fail(key, "launcher lock differs from the execution lock constants / registered D-3b identities")
    d2fam = d2l["families"][fam]
    if lk.get("d2_run_root") != d2fam["run_root"].rstrip("/") + "/out/d2" or lk.get("d3b_run_roots") != {s: d3bl["partitions"][f"{fam}_{s}"]["run_root"].rstrip("/") + "/d3b" for s in SIZES}: _fail(key, "launcher lock input roots are not the registered D-2 / D-3b runs")
    if lk.get("mt") != "/content/d3c_scratch" or lk.get("phaseb") != f"{lk['mt']}/engine/phaseB" or lk.get("phasec") != f"{lk['mt']}/phaseC" or lk.get("script") != f"{lk['phaseb']}/d/d3c_profile.py" or lk.get("out") != f"/content/d3c_profile_{fam}": _fail(key, "launcher lock tree layout")
    # ---- final record == this attempt; success flags; live source at precheck AND prelaunch == lock; lock bound
    want_fin = dict(schema="d3c_launcher_final_record_v3", attempt_id=att, lock_sha256=_sha(lkb), lock=lk, output_anchor=lk["out"], stage="complete", profile_pass=True, exit_code=0, D3C_PASS=True, gate_passed=True, launcher_fallback=False, bindings_ok=True, failures=[], exception=None, run_dir=f"{lk['out']}/run_{att}", plan_identity_file_ok=True, record_sha256=_sha(rb), plan_identity_sha256=pdoc.get("identity", {}).get("identity_sha256"))
    if any(fn.get(k) != v for k, v in want_fin.items()) or "superseded_previous_record" in fn: _fail(key, "launcher final record is not the accepted successful attempt bound to the lock and the profile record")
    for ph in ("precheck", "prelaunch"):
        ls = (fn.get("bindings") or {}).get(f"live_source_{ph}") or {}
        if ls.get("head") != EL["commit"] or ls.get("clean") is not True or ls.get("inventory_sha256") != EL["inventory_sha256"] or ls.get("script_sha256") != EL["script_sha256"] or ls.get("inventory_script_sha256") != EL["script_sha256"] or ls.get("ledger_file_sha256") != EL["d3b_ledger_file_sha256"] or ls.get("receipt_file_sha256") != EL["d3b_receipt_file_sha256"] or ls.get("pins_sha256") != EL["pins_sha256"] or ls.get("engine") != EL["engine_version"]: _fail(key, f"live source at {ph} differs from the execution lock")
    if fn.get("staged_inputs") != dict(d2="/content/stage/d2", d3b={s: f"/content/stage/d3b_{s}" for s in SIZES}) or (fn.get("args") or [])[-14:] != ["--d2-root", "/content/stage/d2", "--profile", "production_official", "--attempt-id", att, "--launcher-lock-sha256", _sha(lkb)] + [x for s in SIZES for x in ("--d3b-root", f"{s}=/content/stage/d3b_{s}")]: _fail(key, "staged inputs / child arguments")
    if "--selftest-small" in fn["args"] or "--selftest-skip-env-lock" in fn["args"] or "--selftest-sizes" in fn["args"] or len(se) != 0: _fail(key, "self-test flags / stderr")
    # ---- profile record
    want_rec = dict(schema="d3c_profile_record_v2", stage="complete", family=fam, selftest=False, profile="production_official", failures=[], required_inventory=list(REQUIRED_GATES), required_all_true=True, D3C_PASS=True, engine_version=EL["engine_version"], attempt=dict(attempt_id=att, launcher_lock_sha256=_sha(lkb)), out=f"{lk['out']}/run_{att}", publication_stage="plan_identity_verified", plan_identity_sha256=pdoc.get("identity", {}).get("identity_sha256"))
    if any(rec.get(k) != v for k, v in want_rec.items()): _fail(key, "profile record header / attempt binding")
    if rec.get("gates") != {g: True for g in REQUIRED_GATES}: _fail(key, "REQUIRED gates (18 named, all True)")
    src = rec.get("source") or {}
    if src.get("script_sha256") != EL["script_sha256"] or src.get("inventory_sha256") != EL["inventory_sha256"] or src.get("pins_sha256") != EL["pins_sha256"] or src.get("engine_version") != EL["engine_version"]: _fail(key, "profile record source != execution lock")
    env = rec.get("env") or {}
    if any(env.get(k) != pins_env[k] for k in ("python", "numpy", "scipy", "healpy", "pot", "camb")) or any(env.get(k) != v for k, v in EXPECTED_VERS.items()) or (rec.get("env_gate") or {}).get("versions_ok") is not True or (rec.get("env_gate") or {}).get("pools_ok") is not True: _fail(key, "registered environment")
    ident = ctx.identities
    if any(rec.get("context_identities", {}).get(k) != v for k, v in ident.items()): _fail(key, "context identities differ from the verified TwelveContext")
    d3b = rec.get("d3b") or {}
    if d3b.get("ledger_sha256") != d3bl["ledger_sha256"] or d3b.get("receipt_sha256") != ctx._d["pins"]["d3b_outer_receipt_sha256"]: _fail(key, "D-3b ledger / receipt binding")
    inp = rec.get("inputs") or {}
    if inp.get("d2_root") != "/content/stage/d2" or (inp.get("d2_ledger") or {}).get("run_id") != d2fam["run_id"] or any((inp.get("d3b_partitions") or {}).get(s, {}).get("run_id") != d3bl["partitions"][f"{fam}_{s}"]["run_id"] for s in SIZES): _fail(key, "inputs do not resolve to the registered runs")
    # ---- 72 supplies: unit manifests == spec v2 (first wave) / D-3b ledger (added); reference == family reference; cluster counts
    sup = rec.get("supplies") or {}; n_fw = n_add = 0; fr = spec2["family_reference"][fam]["units"]
    for k, v in sup.items():
        cid, system = k.split("/"); cid = int(cid); row = spec2["configurations"].get(str(cid)) or spec2["configurations"].get(cid)
        if row is None or row["family"] != fam or system not in ("matched", "native"): _fail(key, f"supply {k}: not a configuration of this family")
        m = v.get("manifests") or {}
        if v.get("origin") == "first_wave_D1":
            w = row["d2"]["units"]; n_fw += 1
            if m.get("eval", {}).get("0") != w[f"cfg{cid}_b0"]["manifest_sha256"] or m.get("eval", {}).get("1") != w[f"cfg{cid}_b1"]["manifest_sha256"] or m.get("fit") != w[f"cfg{cid}_fit"]["manifest_sha256"]: _fail(key, f"supply {k}: D-2 units")
        elif v.get("origin") == "twelve_added_D3a":
            P = d3bl["partitions"][f"{fam}_{row['size_id']}"]["units"]; n_add += 1
            if m.get("eval", {}).get("0") != P[f"cfg{cid}_b0"]["manifest_sha256"] or m.get("eval", {}).get("1") != P[f"cfg{cid}_b1"]["manifest_sha256"] or m.get("fit") != P[f"cfg{cid}_fit"]["manifest_sha256"] or v.get("d3b_ledger_sha256") != d3bl["ledger_sha256"] or v.get("d3b_receipt_sha256") != ctx._d["pins"]["d3b_outer_receipt_sha256"]: _fail(key, f"supply {k}: D-3b units")
        else: _fail(key, f"supply {k}: origin")
        if m.get("ref", {}).get("0") != fr[f"ref_{fam}_b0"]["manifest_sha256"] or m.get("ref", {}).get("1") != fr[f"ref_{fam}_b1"]["manifest_sha256"] or m.get("ref_fit") != fr[f"ref_{fam}_fit"]["manifest_sha256"] or v.get("n_clusters") != {"0": RULES.N0 // RULES.m, "1": (RULES.N_max - RULES.N0) // RULES.m}: _fail(key, f"supply {k}: reference / clusters")
    if len(sup) != N_SUPPLIES or n_fw != N_FIRST_WAVE or n_add != N_ADDED: _fail(key, "supply inventory")
    # ---- UIDs / constants; plans; fingerprints; object identity; family identity
    u = rec.get("uids") or {}; g_eval = pdoc.get("identity", {}).get("evaluation_group")
    if u.get("K0") != RULES.N0 // RULES.m or u.get("K1") != (RULES.N_max - RULES.N0) // RULES.m or u.get("m") != RULES.m or u.get("K_fit") != REG_N_FIT // REG_M_FIT or u.get("n_fit") != REG_N_FIT or u.get("evaluation_group") != g_eval: _fail(key, "UID / registered constants")
    fb, fa = rec.get("input_fingerprints_before_gate") or {}, rec.get("input_fingerprints_after_gate") or {}
    if not (isinstance(fb.get("matched"), str) and len(fb["matched"]) == 64 and isinstance(fb.get("native"), str) and len(fb["native"]) == 64 and fb["matched"] != fb["native"] and fa.get("matched") == fb["matched"] and fa.get("native") == fb["native"] and len(fb.get("snapshot_matched_sha256", "")) == 64): _fail(key, "input fingerprints (before == after, both systems)")
    poi = rec.get("plan_object_identity") or {}
    if set(poi) != {"size_inputs_before_gate", "assembled_before_gate", "size_inputs_after_gate", "assembled_after_gate"} or any(set(poi[k]) != ({f"{s}/{sy}" for s in SIZES for sy in ("matched", "native")} if "size" in k else {"family/matched", "family/native"}) or any(v != dict(plans_is_fixed=True, fit_plans_is_fixed=True) for v in poi[k].values()) for k in poi): _fail(key, "plan object identity")
    fi = rec.get("family_identity") or {}
    if fi.get("family") != fam or fi.get("full_surviving_scope") is not True or fi.get("n_configs") != 36 or fi.get("stage") != "twelve" or fi.get("registry_sha256") != ident["registry_sha256"] or fi.get("manifest_sha256") != ident["manifest_sha256"]: _fail(key, "family identity")
    # ---- official gate record
    g = rec.get("gate") or {}; dg = g.get("diagnostics") or {}
    if g.get("mode") != "official" or g.get("passed") is not True or g.get("required_failures") != [] or dg.get("environment_source") != "live_collected" or dg.get("profile_failures") != [] or dg.get("version_mismatch") != {} or dg.get("blas_threads_ok") is not True or (dg.get("rules_binding") or {}).get("ok") is not True or (dg.get("rules_binding") or {}).get("document_state") != "verified": _fail(key, "official gate flags")
    ch = dg.get("checks") or []; tw = dg.get("twelve_checks") or []
    if len(ch) != N_PROFILE_CHECKS or len({c["code"] for c in ch}) != N_PROFILE_CHECKS or not all(c.get("passed") is True and "official" in c.get("required_modes", []) for c in ch) or len(tw) != N_TWELVE_CHECKS or not all(c.get("passed") is True for c in tw) or {c["code"] for c in tw} != {f"{sy}/{c}" for sy in ("matched", "native") for c in ("stage_twelve", "twelve_per_size", "pc1_pass_all", "full_surviving_scope", "first_wave_and_added_share_plans", "plan_identity_fixed")} | {"pair/sources", "pair/positions"}: _fail(key, "official gate check inventory")
    # ---- plan identity document
    pi = pdoc.get("identity") or {}
    if pdoc.get("schema") != "d3c_plan_identity_record_v2" or pdoc.get("family") != fam or pdoc.get("formal") is not True or pdoc.get("selftest") is not False or pdoc.get("B") != RULES.B or pdoc.get("B_KDE") != REG_B_KDE or pdoc.get("seeds") != RULES.seeds or pdoc.get("K_fit") != REG_N_FIT // REG_M_FIT or pdoc.get("master_seed") != ctx.table["master_seed"] or pdoc.get("crn_table_sha256") != ctx.table["table_sha256"] or pdoc.get("engine_version") != EL["engine_version"]: _fail(key, "plan document header / constants")
    if pdoc.get("attempt") != rec["attempt"] or (pdoc.get("source_lock") or {}).get("script_sha256") != EL["script_sha256"] or pdoc["source_lock"].get("inventory_sha256") != EL["inventory_sha256"] or pdoc["source_lock"].get("pins_sha256") != EL["pins_sha256"] or any(pdoc.get("context_identities", {}).get(k) != v for k, v in ident.items()): _fail(key, "plan document binding")
    if pi.get("schema") != PLAN_SCHEMA_V2["schema"] or _plan_payload_sha(pi, "identity_sha256") != pi.get("identity_sha256") or pi.get("family") != fam or pi.get("B") != RULES.B or pi.get("B_KDE") != REG_B_KDE or pi.get("seeds") != RULES.seeds or pi.get("master_seed") != ctx.table["master_seed"]: _fail(key, "plan identity payload")
    ou = pdoc.get("ordered_uids") or {}; u0, u1 = ou.get("0") or [], ou.get("1") or []
    if len(u0) != RULES.N0 // RULES.m or len(u1) != (RULES.N_max - RULES.N0) // RULES.m or any(not (isinstance(x, list) and len(x) == 5 and x[1] == 200 and x[2] == g_eval and x[3] == b and x[4] == i) for b, lst in ((0, u0), (1, u1)) for i, x in enumerate(lst)) or len({x[0] for x in u0 + u1}) != 1: _fail(key, "ordered UIDs (batch / purpose / group / rotation order)")
    uid_sha = _sha(json.dumps(u0 + u1).encode())
    if uid_sha != u.get("ordered_uid_sha256") or u.get("first_uid") != u0[0] or u.get("last_uid") != u1[-1]: _fail(key, "ordered UID SHA")
    if rec.get("published_evidence") != {f"d3c_plan_identity_{fam}.json": dict(sha256=_sha(pb), bytes=len(pb))}: _fail(key, "plan document publication receipt")
    if b"D3C_PASS = True" not in so or b"D3C_PASS = True" in se: _fail(key, "launcher stdout")
    # ---- inner archive == the registered originals; executed notebook == constant identity and the locked cell 0
    ar = INNER_ARCHIVES[fam]; ab = _read(os.path.join(_d3c_root(root), "archives", ar["file"]))
    if _sha(ab) != ar["sha256"] or len(ab) != ar["bytes"]: _fail(key, "inner archive identity")
    with zipfile.ZipFile(os.path.join(_d3c_root(root), "archives", ar["file"])) as z:
        members = {i.filename: i for i in z.infolist() if not i.is_dir()}
        if set(members) != set(files) or any(z.read(n) != files[n] for n in files): _fail(key, "inner archive members differ from the registered originals")
    nb = EXECUTED_NOTEBOOKS[fam]; nbb = _read(os.path.join(_d3c_root(root), "notebooks", nb["file"]))
    if _sha(nbb) != nb["sha256"] or len(nbb) != nb["bytes"]: _fail(key, "executed notebook identity")
    nbj = json.loads(nbb.decode("utf-8")); code = ["".join(c["source"]) for c in nbj["cells"] if c["cell_type"] == "code"]
    if len(code) != 4 or f"FAMILY = '{fam}'" not in code[0] or f"REPO_COMMIT = '{EL['commit']}'" not in code[0] or f"EXPECTED_INVENTORY_SHA256 = '{EL['inventory_sha256']}'" not in code[0] or "STAGE_LOCAL = True" not in code[0] or "STAGE_ROOT = '/content/stage'" not in code[0] or lk["d2_run_root"] not in code[0] or any(p not in code[0] for p in lk["d3b_run_roots"].values()): _fail(key, "executed notebook lock cell")
    return dict(family=fam, attempt_id=att, registered_dir=f"registered_assets/d3c/runs/{key}", started_utc=fn["started_utc"], finished_utc=fn["finished_utc"], records={n: dict(sha256=_sha(b), bytes=len(b)) for n, b in files.items()}, inner_archive=copy.deepcopy(ar), executed_notebook=copy.deepcopy(nb),
                lock_sha256=_sha(lkb), profile_record_sha256=_sha(rb), plan_document=dict(sha256=_sha(pb), bytes=len(pb)), plan_identity=copy.deepcopy(pi), ordered_uid_sha256=uid_sha, n_uids=dict(batch0=len(u0), batch1=len(u1)), input_fingerprints=dict(matched=fb["matched"], native=fb["native"], snapshot_matched_sha256=fb["snapshot_matched_sha256"]),
                constants=dict(B=pdoc["B"], B_KDE=pdoc["B_KDE"], seeds=pdoc["seeds"], K_fit=pdoc["K_fit"], master_seed=pdoc["master_seed"], K0=u["K0"], K1=u["K1"], m=u["m"], n_fit=u["n_fit"], evaluation_group=g_eval, fitting_group=pi.get("fitting_group"), crn_table_sha256=pdoc["crn_table_sha256"]),
                gate=copy.deepcopy(g), required_gates=dict(rec["gates"]), supplies=dict(n=len(sup), first_wave=n_fw, added=n_add, digest=_sha(json.dumps(sup, sort_keys=True).encode())), inputs=dict(d2_run_id=d2fam["run_id"], d2_run_root=lk["d2_run_root"], d3b_run_ids={s: d3bl["partitions"][f"{fam}_{s}"]["run_id"] for s in SIZES}, d3b_run_roots=dict(lk["d3b_run_roots"])),
                context_identities=dict(ident), family_identity=copy.deepcopy(fi), environment=dict(python=rec["env"].get("python"), numpy=rec["env"].get("numpy"), scipy=rec["env"].get("scipy"), healpy=rec["env"].get("healpy"), camb=rec["env"].get("camb"), pot=rec["env"].get("pot")), environment_identity_order_independent=_env_identity(rec["env"]),
                resources=dict(stages_rss_mb=dict(rec["stages_rss_mb"]), stages_peak_rss_mb=dict(rec["stages_peak_rss_mb"]), timings_cumulative_s=dict(rec["timings"]), seconds_script=rec["seconds"], seconds_launcher=fn["seconds_total"], staging=dict(fn.get("staging") or {}), ram=dict(fn.get("ram") or {})),
                live_source=dict(precheck=dict(fn["bindings"]["live_source_precheck"]), prelaunch=dict(fn["bindings"]["live_source_prelaunch"])))


def build_d3c_profile_ledger(phaseb_root: str, ctx: TwelveContext) -> dict:
    """Deterministic ledger of the three accepted profile runs (module docstring). Raises on any inconsistency; never repairs a record."""
    ctx = _require_ctx(ctx); root = os.path.abspath(phaseb_root)
    if os.path.realpath(root) != os.path.realpath(ctx.root): raise InputContractError("the registered D-3c records must be read from the root of the verified context")
    d3bl = load_registered_d3b_ledger(root, ctx); d2l = ctx.d2_ledger; spec2 = load_registered_bank_spec_v2(ctx); pins_env = ctx._d["pins"]["environment"]
    runs = os.path.join(_d3c_root(root), "runs")
    if not os.path.isdir(runs) or sorted(os.listdir(runs)) != sorted(f"{f}_{ATTEMPTS[f]}" for f in FAMILIES): raise InputContractError("registered_assets/d3c/runs must hold exactly the three accepted attempts")
    ab, acc = _json(os.path.join(_d3c_root(root), "acceptance", PROFILE_ACCEPTANCE["decision_file"])); PA = PROFILE_ACCEPTANCE
    if _sha(ab) != PA["decision_sha256"] or len(ab) != PA["decision_bytes"]: raise InputContractError("registered acceptance document differs from the acceptance constants")
    mdb = _read(os.path.join(_d3c_root(root), "acceptance", PA["audit_md"])); pdb = _read(os.path.join(_d3c_root(root), "acceptance", EXECUTION_LOCK["preexecution_authorization"]["file"]))
    if _sha(mdb) != PA["audit_md_sha256"] or len(mdb) != PA["audit_md_bytes"] or _sha(pdb) != EXECUTION_LOCK["preexecution_authorization"]["sha256"] or len(pdb) != EXECUTION_LOCK["preexecution_authorization"]["bytes"]: raise InputContractError("registered audit / pre-execution documents differ from the constants")
    if acc.get("decision") != PA["decision"] or acc.get("tranche2_registration_implementation_GO") is not True or acc.get("requires_profile_rerun") is not False or (acc.get("subject") or {}).get("commit_recorded_in_run") != EXECUTION_LOCK["commit"] or acc["subject"].get("inventory_sha256") != EXECUTION_LOCK["inventory_sha256"] or (acc["subject"].get("run_packet") or {}).get("sha256") != PA["run_packet_sha256"]: raise InputContractError("acceptance document content")
    fams = {}; plan_ids = set(); fps = set()
    for fam in FAMILIES:
        e = _check_family(root, ctx, fam, d2l, d3bl, spec2, pins_env); A = (acc.get("families") or {}).get(fam) or {}
        if A.get("attempt_id") != e["attempt_id"] or (A.get("archive") or {}).get("archive_sha256") != e["inner_archive"]["sha256"] or {k: v["sha256"] for k, v in (A.get("archive") or {}).get("files", {}).items()} != {k: v["sha256"] for k, v in e["records"].items()} or (A.get("executed_notebook") or {}).get("sha256") != e["executed_notebook"]["sha256"]: raise InputContractError(f"{fam}: acceptance document does not name the registered originals")
        if A.get("plan_identity_sha256") != e["plan_identity"]["identity_sha256"] or A.get("ordered_uid_sha256") != e["ordered_uid_sha256"] or A.get("input_fingerprints") != {k: e["input_fingerprints"][k] for k in ("matched", "native")} or A.get("profile_record_sha256") != e["profile_record_sha256"] or A.get("lock_sha256") != e["lock_sha256"] or A.get("independent_full_scale_plan_reconstruction") is not True: raise InputContractError(f"{fam}: acceptance identities differ from the registered records")
        plan_ids.add(e["plan_identity"]["identity_sha256"]); fps.update((e["input_fingerprints"]["matched"], e["input_fingerprints"]["native"])); fams[fam] = e
    if len(plan_ids) != 3 or len(fps) != 6: raise InputContractError("plan identities / fingerprints must be distinct across families and systems")
    ts = [(fams[f]["started_utc"], fams[f]["finished_utc"]) for f in FAMILIES]
    if not all(ts[i][1] <= ts[i + 1][0] for i in range(2)): raise InputContractError("attempts must be sequential (E2 -> E7 -> E8, non-overlapping)")
    doc = dict(schema=LEDGER_SCHEMA, execution_lock=copy.deepcopy(EXECUTION_LOCK), acceptance=copy.deepcopy(PROFILE_ACCEPTANCE), acceptance_files=dict(decision=dict(file=PA["decision_file"], sha256=_sha(ab), bytes=len(ab)), audit_md=dict(file=PA["audit_md"], sha256=_sha(mdb), bytes=len(mdb)), preexecution=dict(file=EXECUTION_LOCK["preexecution_authorization"]["file"], sha256=_sha(pdb), bytes=len(pdb))),
               families=fams, totals=dict(families=3, attempts=3, supplies=sum(f["supplies"]["n"] for f in fams.values()), profile_checks=N_PROFILE_CHECKS * 3, twelve_checks=N_TWELVE_CHECKS * 3, seconds_script=sum(f["resources"]["seconds_script"] for f in fams.values()), seconds_launcher=sum(f["resources"]["seconds_launcher"] for f in fams.values()), peak_rss_mb_max=max(max(f["resources"]["stages_peak_rss_mb"].values()) for f in fams.values())),
               registered_d3b=dict(ledger_payload_sha256=d3bl["ledger_sha256"], ledger_file_sha256=d3bl["_file_sha256"], outer_receipt_sha256=ctx._d["pins"]["d3b_outer_receipt_sha256"]),
               statement="REGISTERED (scoped): the three accepted formal twelve-position profile runs (E2 / E7 / E8; commit 7a2b1774, engine 0.99.0) with their fixed five-seed plan identities, ordered UIDs, input fingerprints and official gate records, registered as the original bytes. The plan identities were independently reproduced at full scale by the auditor. Consumers (D-4 calibration) must rebuild their plans from the registered ordered UIDs and reproduce these identities, and their family inputs must reproduce both fingerprints; thresholds / labels / calibration / D-2W / noise remain separately gated.")
    doc["ledger_sha256"] = _payload_sha(doc, "ledger_sha256"); return doc


def verify_d3c_profile_ledger(doc: dict, phaseb_root: str, ctx: TwelveContext) -> dict:
    """The document must equal its re-derivation from the registered originals (payload SHA + full content); returns a deep copy."""
    if not isinstance(doc, dict) or doc.get("schema") != LEDGER_SCHEMA: raise InputContractError("D-3c ledger schema")
    if doc.get("ledger_sha256") != _payload_sha(doc, "ledger_sha256"): raise InputContractError("D-3c ledger payload SHA")
    fresh = build_d3c_profile_ledger(phaseb_root, ctx)
    if doc != fresh: raise InputContractError("D-3c ledger differs from its re-derivation from the registered originals")
    return copy.deepcopy(fresh)


def load_registered_d3c_ledger(phaseb_root: str, ctx: TwelveContext) -> dict:
    """The committed registered_assets/d3c/d3c_profile_ledger.json: payload identity == d3 pins (d3c_ledger_sha256) and content == re-derivation."""
    ctx = _require_ctx(ctx); root = os.path.abspath(phaseb_root)
    if os.path.realpath(root) != os.path.realpath(ctx.root): raise InputContractError("the registered D-3c ledger must be read from the root of the verified context")
    b, doc = _json(os.path.join(_d3c_root(root), "d3c_profile_ledger.json"))
    if doc.get("ledger_sha256") != ctx._d["pins"].get("d3c_ledger_sha256"): raise InputContractError("registered D-3c ledger identity differs from the pins")
    out = verify_d3c_profile_ledger(doc, root, ctx); out["_file_sha256"] = _sha(b); return out


# ------------------------------------------------------------------------------------------------------------------------------------ outer receipt
def build_d3c_outer_receipt(phaseb_root: str, ctx: TwelveContext) -> dict:
    """Deterministic outer receipt: the registered ledger (payload + file SHA) and the acceptance constants / file bytes bound together with the per-family identities
    (attempt, plan identity SHA, ordered UID SHA, both fingerprints, record SHAs, inner archive, executed notebook)."""
    ctx = _require_ctx(ctx); root = os.path.abspath(phaseb_root)
    if os.path.realpath(root) != os.path.realpath(ctx.root): raise InputContractError("the registered D-3c receipt must be read from the root of the verified context")
    ledger = load_registered_d3c_ledger(root, ctx)
    fams = {f: dict(attempt_id=e["attempt_id"], plan_identity_sha256=e["plan_identity"]["identity_sha256"], ordered_uid_sha256=e["ordered_uid_sha256"], input_fingerprints={k: e["input_fingerprints"][k] for k in ("matched", "native")}, lock_sha256=e["lock_sha256"], profile_record_sha256=e["profile_record_sha256"], plan_document_sha256=e["plan_document"]["sha256"],
                    inner_archive_sha256=e["inner_archive"]["sha256"], executed_notebook_sha256=e["executed_notebook"]["sha256"], gate_passed=e["gate"]["passed"], gate_mode=e["gate"]["mode"], registered_dir=e["registered_dir"]) for f, e in ledger["families"].items()}
    doc = dict(schema=RECEIPT_SCHEMA, ledger=dict(payload_sha256=ledger["ledger_sha256"], file_sha256=ledger["_file_sha256"], schema=LEDGER_SCHEMA), execution_lock=copy.deepcopy(EXECUTION_LOCK), acceptance=copy.deepcopy(PROFILE_ACCEPTANCE), acceptance_files=copy.deepcopy(ledger["acceptance_files"]), families=fams, totals=copy.deepcopy(ledger["totals"]),
               registered_d3b=copy.deepcopy(ledger["registered_d3b"]), pins_binding=dict(d3b_ledger_sha256=ctx._d["pins"]["d3b_ledger_sha256"], d3b_outer_receipt_sha256=ctx._d["pins"]["d3b_outer_receipt_sha256"], config_map_sha256=ctx._d["pins"]["config_map_sha256"], covariance_receipt_sha256=ctx._d["pins"]["covariance_receipt_sha256"], bank_spec_v2_sha256=ctx._d["pins"]["bank_spec_v2_sha256"]),
               statement="ACCEPTED (scoped): the three formal profile runs and their fixed plan identities are the registered inputs of calibration; this receipt is the auditor's scoped acceptance of the registered records (independently reproduced plan identities), not a re-read of the production banks; D-4 execution, thresholds, labels, D-2W and noise remain separately gated.")
    doc["receipt_sha256"] = _payload_sha(doc, "receipt_sha256"); return doc


def verify_d3c_outer_receipt(doc: dict, phaseb_root: str, ctx: TwelveContext) -> dict:
    if not isinstance(doc, dict) or doc.get("schema") != RECEIPT_SCHEMA: raise InputContractError("D-3c outer receipt schema")
    if doc.get("receipt_sha256") != _payload_sha(doc, "receipt_sha256"): raise InputContractError("D-3c outer receipt payload SHA")
    fresh = build_d3c_outer_receipt(phaseb_root, ctx)
    if doc != fresh: raise InputContractError("D-3c outer receipt differs from its re-derivation from the registered records")
    return copy.deepcopy(fresh)


def load_registered_d3c_outer_receipt(phaseb_root: str, ctx: TwelveContext) -> dict:
    """The committed registered_assets/d3c/d3c_outer_receipt.json: payload identity == d3 pins (d3c_outer_receipt_sha256) and content == re-derivation."""
    ctx = _require_ctx(ctx); root = os.path.abspath(phaseb_root)
    if os.path.realpath(root) != os.path.realpath(ctx.root): raise InputContractError("the registered D-3c receipt must be read from the root of the verified context")
    b, doc = _json(os.path.join(_d3c_root(root), "d3c_outer_receipt.json"))
    if doc.get("receipt_sha256") != ctx._d["pins"].get("d3c_outer_receipt_sha256"): raise InputContractError("registered D-3c outer receipt identity differs from the pins")
    out = verify_d3c_outer_receipt(doc, root, ctx); out["_file_sha256"] = _sha(b); return out


# ------------------------------------------------------------------------------------------------------------------------------------ consumer view
class D3cProfiles:
    """Sealed, verified view of the three accepted profile runs for consumers (D-4 calibration). Public views are deep copies; construction only by intake_registered_d3c_profiles."""
    __slots__ = ("_d", "_seal")

    def __init__(self, d: dict, *, _token=None):
        if _token is not _TOKEN: raise InputContractError("D3cProfiles must be created by intake_registered_d3c_profiles()")
        object.__setattr__(self, "_d", d); object.__setattr__(self, "_seal", _TOKEN)

    def __setattr__(self, n, v): raise AttributeError("D3cProfiles is immutable")
    def __delattr__(self, n): raise AttributeError("D3cProfiles is immutable")
    @property
    def verified(self): return self._seal is _TOKEN
    @property
    def accepted(self): return True
    @property
    def families(self): return tuple(FAMILIES)
    @property
    def ledger_sha256(self): return self._d["ledger"]["ledger_sha256"]
    @property
    def receipt_sha256(self): return self._d["receipt"]["receipt_sha256"]
    @property
    def execution_lock(self): return copy.deepcopy(EXECUTION_LOCK)
    def _fam(self, family: str) -> dict:
        if family not in self._d["ledger"]["families"]: raise InputContractError(f"{family}: not an accepted twelve-position profile family (E2 / E7 / E8 only)")
        return self._d["ledger"]["families"][family]
    def family(self, family: str) -> dict: return copy.deepcopy(self._fam(family))
    def attempt_id(self, family: str) -> str: return self._fam(family)["attempt_id"]
    def plan_identity(self, family: str) -> dict: return copy.deepcopy(self._fam(family)["plan_identity"])
    def input_fingerprints(self, family: str) -> dict: return {k: self._fam(family)["input_fingerprints"][k] for k in ("matched", "native")}
    def gate_record(self, family: str) -> dict: return copy.deepcopy(self._fam(family)["gate"])
    def constants(self, family: str) -> dict: return copy.deepcopy(self._fam(family)["constants"])
    def ordered_uids(self, family: str) -> Dict[int, list]:
        """The registered ordered cluster UIDs (batch 0: 10000, batch 1: 30000) read from the registered plan document, whose bytes must equal the ledger / publication receipt."""
        e = self._fam(family); p = os.path.join(self._d["root"], e["registered_dir"], f"run_{e['attempt_id']}", f"d3c_plan_identity_{family}.json"); b, pdoc = _json(p)
        if _sha(b) != e["plan_document"]["sha256"] or len(b) != e["plan_document"]["bytes"]: raise InputContractError(f"{family}: registered plan document bytes differ from the ledger")
        ou = pdoc["ordered_uids"]; out = {0: [tuple(x) for x in ou["0"]], 1: [tuple(x) for x in ou["1"]]}
        if _sha(json.dumps([list(x) for x in out[0] + out[1]]).encode()) != e["ordered_uid_sha256"]: raise InputContractError(f"{family}: ordered UID SHA")
        return out


def intake_registered_d3c_profiles(phaseb_root: str, ctx: TwelveContext) -> D3cProfiles:
    """Sealed view of the accepted profile runs: ledger + outer receipt must exist, verify against the registered originals and bind to the pins and to each other; the D-3b
    array-accepted receipt the runs consumed must be the registered one."""
    ctx = _require_ctx(ctx); root = os.path.abspath(phaseb_root); ledger = load_registered_d3c_ledger(root, ctx); receipt = load_registered_d3c_outer_receipt(root, ctx)
    if receipt["ledger"]["payload_sha256"] != ledger["ledger_sha256"] or receipt["ledger"]["file_sha256"] != ledger["_file_sha256"]: raise InputContractError("D-3c outer receipt is not bound to the registered ledger")
    d3b = load_registered_d3b_outer_receipt(root, ctx)
    if ledger["registered_d3b"]["outer_receipt_sha256"] != d3b["receipt_sha256"]: raise InputContractError("D-3c runs consumed a D-3b acceptance that is not the registered one")
    return D3cProfiles(dict(ledger=ledger, receipt=receipt, root=root), _token=_TOKEN)


def rebuild_registered_plans(profiles: D3cProfiles, family: str, table: dict):
    """The consumer's five-seed plans are REBUILT from the registered ordered UIDs with the registered constants and must reproduce the accepted identity exactly
    (all strata / multiplicity SHAs); returns (plans, fit_plans, identity). Never accepts plans supplied from elsewhere."""
    if not isinstance(profiles, D3cProfiles) or not profiles.verified: raise InputContractError("a verified D3cProfiles (intake_registered_d3c_profiles()) is required")
    e = profiles.family(family); c = e["constants"]; ou = profiles.ordered_uids(family)
    if table.get("table_sha256") != c["crn_table_sha256"] or table.get("master_seed") != c["master_seed"]: raise InputContractError(f"{family}: CRN table differs from the registered plan constants")
    plans, fplans, ident = fix_family_plans(table, family, {0: ou[0], 1: ou[1]}, c["K_fit"], c["master_seed"], B=c["B"], B_KDE=c["B_KDE"])
    if ident != e["plan_identity"] or not verify_plan_identity(plans, fplans, e["plan_identity"], table=table, family=family): raise InputContractError(f"{family}: rebuilt plans do not reproduce the accepted plan identity")
    return plans, fplans, ident


def verify_consumer_inputs(profiles: D3cProfiles, family: str, fingerprints: dict, plans: dict, fit_plans: dict, plan_identity: dict, table: Optional[dict] = None, gate: Optional[dict] = None) -> dict:
    """A consumer's inputs are accepted only if (i) both input fingerprints equal the accepted ones, (ii) the plan objects reproduce the accepted identity (verify_plan_identity)
    and the supplied identity document equals the accepted one, and (iii) an optional consumer gate record is an official, passed record with the accepted check inventory and
    the accepted plan identity. No PASS flag, attempt id or earlier success is accepted in place of these identities. Returns the binding record."""
    if not isinstance(profiles, D3cProfiles) or not profiles.verified: raise InputContractError("a verified D3cProfiles (intake_registered_d3c_profiles()) is required")
    e = profiles.family(family); fp = e["input_fingerprints"]
    if not isinstance(fingerprints, dict) or fingerprints.get("matched") != fp["matched"] or fingerprints.get("native") != fp["native"]: raise InputContractError(f"{family}: consumer input fingerprints differ from the accepted profile (matched / native)")
    if plan_identity != e["plan_identity"]: raise InputContractError(f"{family}: consumer plan identity differs from the accepted identity")
    if not verify_plan_identity(plans, fit_plans, e["plan_identity"], table=table, family=family): raise InputContractError(f"{family}: consumer plans do not reproduce the accepted identity")
    if gate is not None:
        G = e["gate"]; dg = gate.get("diagnostics") or {}
        if gate.get("mode") != "official" or gate.get("passed") is not True or gate.get("required_failures") != [] or dg.get("environment_source") != "live_collected" or {c["code"] for c in dg.get("checks") or []} != {c["code"] for c in G["diagnostics"]["checks"]} or {c["code"] for c in dg.get("twelve_checks") or []} != {c["code"] for c in G["diagnostics"]["twelve_checks"]} or not all(c.get("passed") is True for c in (dg.get("checks") or []) + (dg.get("twelve_checks") or [])): raise InputContractError(f"{family}: consumer gate record is not an official passed record with the accepted check inventory")
    return dict(family=family, attempt_id=e["attempt_id"], plan_identity_sha256=e["plan_identity"]["identity_sha256"], input_fingerprints={k: fp[k] for k in ("matched", "native")}, ledger_sha256=profiles.ledger_sha256, receipt_sha256=profiles.receipt_sha256, gate_checked=gate is not None)


def verify_consumer_family_inputs(profiles: D3cProfiles, family: str, fam_matched, fam_native, plan_identity: dict, table: Optional[dict] = None, gate: Optional[dict] = None) -> dict:
    """FamilyInput form: fingerprints are computed from the consumer's assembled inputs (formal_runner.input_fingerprint), the plan objects are the inputs' own (both systems must
    share them), and every configuration's cluster UIDs must be the registered ordered UIDs of its batches."""
    from .formal_runner import input_fingerprint
    if fam_matched is None or fam_native is None: raise InputContractError("both systems (matched / native) are required")
    if fam_matched.family != family or fam_native.family != family: raise InputContractError(f"{family}: consumer inputs belong to another family")
    if fam_matched.plans is not fam_native.plans or fam_matched.fit_plans is not fam_native.fit_plans: raise InputContractError(f"{family}: the two systems must share the plan objects")
    ou = profiles.ordered_uids(family)
    for f in (fam_matched, fam_native):
        for c in f.configs:
            if any([tuple(u.as_tuple()) for u in c.cluster_uids[s // c.m:e // c.m]] != ou[b] for b, (s, e) in c.batches.items()): raise InputContractError(f"{family}: configuration {c.evaluation_id} ({f.configs[0].system}) does not carry the registered ordered UIDs")
    return verify_consumer_inputs(profiles, family, dict(matched=input_fingerprint(fam_matched), native=input_fingerprint(fam_native)), fam_matched.plans, fam_matched.fit_plans, plan_identity, table=table, gate=gate)
