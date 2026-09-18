# -*- coding: utf-8 -*-
"""Checkpoint writer/loader for FamilyResult (rules §13; engine spec C). The reader reconstructs every decision input FROM VERIFIED EVIDENCE and only then compares with the
stored summary: stored Q num/den (5 seeds) -> CIs -> precision -> ratio_quantity; stored logD replicates + invalid mask -> logD CI; stored per-point / mixture sensitivity values
-> bandwidth audits -> logD_quantity; reconstructed quantities -> core predicate -> stored decision/truths. Claimed audits or quantities are never trusted as ground truth.
Mathematical boundary states (Q=+inf, unresolved) are valid and round-trip; the dedicated N-selection failure record has its own schema (all TECH, no success label, no numeric values).
Scope of 'verified': internal consistency conditional on the stored replicate values/densities — not a re-fit of banks, not a proof of physically correct covariances."""
from __future__ import annotations
import os, hashlib, math
import numpy as np
from .errors import InputContractError
from .rules_config import RULES, BINDING
from . import serialization as ser
from .ci import ci_from_replicates, CIResult
from .precision import precision_state
from .decision import CoreInputs, decide_core, logD_ci_required
from .quantity import ratio_quantity, logD_quantity
from .density import sensitivity_audit
from .truth import TECH, UNKNOWN
from . import __version__

_HERE = os.path.dirname(os.path.abspath(__file__))
MODULES = ("__init__.py", "errors.py", "types.py", "truth.py", "rules_config.py", "serialization.py", "ci.py", "precision.py", "decision.py", "family.py", "bootstrap_plan.py", "calibration.py",
           "quantity.py", "density.py", "orchestrator.py", "positions.py", "expansion.py", "w2_stop.py", "position_state.py", "registry.py", "observers12.py", "observers12_stream.py", "w2_manifest.py", "stage12.py", "coordinator.py", "twelve_eval.py", "plan_io.py", "grid_registry.py", "grid_manifest.py", "production.py", "official_gate.py", "formal_runner.py", "legacy_kernel.py", "performance.py", "w2_shared.py", "w2_context.py", "integrated_runner.py", "threshold_evaluator.py", "twelve_assets.py", "controls.py", "w2_shared_build.py", "ckpt_persist.py", "archive.py", "checkpoint.py")


def module_shas() -> dict:
    out = {}
    for m in MODULES:
        p = os.path.join(_HERE, m)
        if not os.path.exists(p): raise InputContractError(f"engine module {m} missing from the fixed inventory")
        out[m] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out


def registered_profile() -> dict: return dict(N0=RULES.N0, N_max=RULES.N_max, m=RULES.m, B=RULES.B, alpha=RULES.alpha, seeds=RULES.seeds)


def execution_profile_from_result(res: dict) -> dict:
    per = res["per_config"]; Ns = sorted({int(d["N"]) for d in per.values()}) if per and all("N" in d for d in per.values()) else []
    ci0 = res.get("Q_ci_seed0") or {}; return dict(kind=("test" if (Ns and max(Ns) < RULES.N0) else ("registered-size" if Ns else "failed-record")), N_per_config=Ns, B=ci0.get("B"), alpha=ci0.get("alpha"), seeds=len((res.get("evidence") or {}).get("cis_all_seeds", [])))


def binding_manifest(result=None) -> dict:
    rd = None if result is None else (ser.from_jsonable(result.as_dict()) if hasattr(result, "as_dict") else ser.from_jsonable(ser.to_jsonable(result)))
    return dict(engine_version=__version__, rules_document_sha256=BINDING["rules_document_sha256"], tables_sha256=BINDING["tables_sha256"], modules=module_shas(), registered_profile=registered_profile(),
                execution_profile=(execution_profile_from_result(rd) if rd is not None else None))


def write_family_result(result, path: str, extra: dict = None) -> str:
    """result: a FamilyResult, a TwelveSizeResult (archive adapter) or an already-tagged result dict (per-size / family-mixture 12-position result). Identity fields (size_id,
    manifest SHA, position maps, scope) are stored verbatim inside the result; they are never dropped by re-wrapping."""
    rd = result.as_dict() if hasattr(result, "as_dict") else ser.to_jsonable(result)
    from .twelve_eval import validate_twelve_archive
    from .production import validate_grid_archive
    validate_grid_archive(ser.from_jsonable(rd))
    validate_twelve_archive(ser.from_jsonable(rd))
    _verify_stored_gate(ser.from_jsonable(rd), extra)
    payload = dict(kind="FamilyResult", binding=binding_manifest(ser.from_jsonable(rd)), result=rd, extra=extra or {})
    body = ser.dumps(payload).encode("utf-8"); tmp = path + ".tmp"
    with open(tmp, "wb") as fh: fh.write(body); fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, path); return hashlib.sha256(body).hexdigest()


def _eq(a, b, tol=0.0):
    if a is None or b is None: return a is None and b is None
    if isinstance(a, str) or isinstance(b, str) or isinstance(a, bool) or isinstance(b, bool): return a == b
    a, b = float(a), float(b)
    if math.isnan(a) or math.isnan(b): return math.isnan(a) and math.isnan(b)
    if math.isinf(a) or math.isinf(b): return a == b
    return abs(a - b) <= tol * max(1.0, abs(b))


def _ci_from_dict(d: dict) -> CIResult: return CIResult(d["value_domain"], d["log_lower"], d["log_upper"], d["lower"], d["upper"], d["effective_method"], d["math_state"], dict(d["counts"]), d["alpha"], int(d["B"]), d.get("reason"), d.get("seed_id"))


def _check_ci_schema(d: dict, where: str, domain: str = None):
    for k in ("value_domain", "log_lower", "log_upper", "lower", "upper", "effective_method", "math_state", "counts", "alpha", "B"):
        if k not in d: raise InputContractError(f"{where}: CI lacks {k}")
    if domain and d["value_domain"] != domain: raise InputContractError(f"{where}: CI domain {d['value_domain']} != {domain}")
    if d["alpha"] != RULES.alpha: raise InputContractError(f"{where}: alpha differs from the registered value")
    if d["math_state"] == "technical_fail":
        if any(d[k] is not None for k in ("log_lower", "log_upper", "lower", "upper")): raise InputContractError(f"{where}: technical_fail CI must not carry endpoints")
        return
    L, U = d["log_lower"], d["log_upper"]
    if L is None or U is None or L > U: raise InputContractError(f"{where}: log endpoints missing or disordered")
    if d["value_domain"] in ("Q", "P"):
        for lg, nat in ((L, d["lower"]), (U, d["upper"])):
            exp_v = math.exp(lg) if math.isfinite(lg) else (0.0 if lg < 0 else math.inf)
            if nat is None or not _eq(nat, exp_v, 1e-12): raise InputContractError(f"{where}: native endpoint does not equal exp(log endpoint)")
        if d["value_domain"] == "P" and U > 0: raise InputContractError(f"{where}: probability log upper > 0")
    if int(d["B"]) <= 0 or sum(int(v) for v in d["counts"].values()) != int(d["B"]): raise InputContractError(f"{where}: counts do not sum to B")


def _ci_equal(a: CIResult, d: dict, where: str):
    ad = ser.from_jsonable(a.as_dict())
    for k in ("log_lower", "log_upper", "lower", "upper"):
        if not _eq(ad[k], d[k], 1e-12): raise InputContractError(f"{where}: stored {k} does not reproduce from the stored evidence")
    for k in ("effective_method", "math_state", "B", "value_domain"):
        if ad[k] != d[k]: raise InputContractError(f"{where}: stored {k} does not reproduce")
    if {k: int(v) for k, v in ad["counts"].items()} != {k: int(v) for k, v in d["counts"].items()}: raise InputContractError(f"{where}: stored counts do not reproduce")


def _quantity_equal(q: dict, stored: dict, where: str):
    for k in ("audit", "lower", "upper", "point"):
        if not _eq(q[k], stored.get(k), 1e-12): raise InputContractError(f"{where}: stored quantity.{k}={stored.get(k)!r} does not follow from the verified evidence ({q[k]!r})")


def _verify_point_precisions(per_cfg: dict, where: str):
    """Rebuild point precision from saved point CIs, P and positive-cluster counts.
    This is conditional on the saved point CIs; it does not recreate their bootstrap
    distributions from the raw bank. Counts and CI schemas are checked before use.
    """
    if not isinstance(per_cfg, dict) or not per_cfg:
        raise InputContractError(f"{where}: missing point precision evidence")
    states, counts = {}, []
    for e, d in per_cfg.items():
        cds = d.get("cis_all_seeds")
        if not isinstance(cds, list) or len(cds) != RULES.seeds:
            raise InputContractError(f"{where}/{e}: point 5-seed CI inventory missing")
        cis = []
        for seed, cd in enumerate(cds):
            _check_ci_schema(cd, f"{where}/{e} seed {seed}", "Q")
            if cd.get("seed_id") != seed:
                raise InputContractError(f"{where}/{e}: point CI seed mismatch")
            cis.append(_ci_from_dict(cd))
        _check_ci_schema(d["ci_seed0"], f"{where}/{e} formal CI", "Q")
        if d["ci_seed0"].get("seed_id") != RULES.formal_seed:
            raise InputContractError(f"{where}/{e}: formal point seed mismatch")
        _ci_equal(cis[RULES.formal_seed], d["ci_seed0"], f"{where}/{e} formal CI")
        pm, pi = d["P_model"], d["P_ref"]
        if not (isinstance(pm, (float,int)) and isinstance(pi, (float,int)) and
                math.isfinite(pm) and math.isfinite(pi) and 0 <= pm <= 1 and 0 <= pi <= 1):
            raise InputContractError(f"{where}/{e}: invalid point probabilities")
        cm, cr = d["positive_clusters_model"], d["positive_clusters_ref"]
        pp = precision_state(cis[RULES.formal_seed], cis, pm / pi if pi > 0 else None, cm, cr)
        st = d["precision"]
        for k in ("state", "rel_halfwidth", "width_cv_logQ", "positive_clusters_model", "positive_clusters_ref"):
            if not _eq(getattr(pp, k), st.get(k), 1e-12):
                raise InputContractError(f"{where}/{e}: point precision.{k} does not reproduce")
        states[e] = pp.state
        counts.append((pp.positive_clusters_model, pp.positive_clusters_ref))
    return states, (min(x[0] for x in counts), min(x[1] for x in counts))


def _verify_Q_side(ev: dict, ci0: dict, prec: dict, per_cfg: dict, cis_all: list, Q_point, stored_quantity: dict, where: str):
    """Stored num/den (5 seeds) -> CIs (seed_id = position) -> family precision -> Q point from configuration probabilities and prior -> ratio_quantity. Returns the reconstructed quantity."""
    per_seed = ev["per_seed"]
    if set(per_seed) != set(range(RULES.seeds)) or len(cis_all) != RULES.seeds: raise InputContractError(f"{where}: seed inventory invalid")
    prior = np.asarray(ev["prior"], float); ids = list(per_cfg)
    if len(prior) != len(ids) or not np.isclose(prior.sum(), 1.0, rtol=0, atol=1e-12): raise InputContractError(f"{where}: stored prior invalid")
    B = None; rec = []
    for s in range(RULES.seeds):
        num = np.asarray(per_seed[s]["num"], float); den = np.asarray(per_seed[s]["den"], float)
        if num.ndim != 1 or num.shape != den.shape or num.size == 0: raise InputContractError(f"{where}: stored seed {s} num/den shape invalid")
        if B is None: B = num.size
        elif num.size != B: raise InputContractError(f"{where}: seed {s} replicate count differs")
        if not (np.all(np.isfinite(num)) and np.all(np.isfinite(den)) and np.all((num >= 0) & (num <= 1)) and np.all((den >= 0) & (den <= 1))): raise InputContractError(f"{where}: stored seed {s} num/den out of the probability domain")
        c = ci_from_replicates(num, den, mode="Q", seed_id=s); _check_ci_schema(cis_all[s], f"{where} seed {s}", "Q")
        if cis_all[s].get("seed_id") != s: raise InputContractError(f"{where}: stored CI at position {s} carries seed_id {cis_all[s].get('seed_id')}")
        _ci_equal(c, cis_all[s], f"{where} seed {s}"); rec.append(c)
    _check_ci_schema(ci0, f"{where} seed0", "Q"); _ci_equal(rec[RULES.formal_seed], ci0, f"{where} seed0")
    PM = np.array([per_cfg[e]["P_model"] for e in ids], float); PI = np.array([per_cfg[e]["P_ref"] for e in ids], float)
    for e in ids:
        d = per_cfg[e]
        if not (0 <= d["P_model"] <= 1 and 0 <= d["P_ref"] <= 1): raise InputContractError(f"{where}: stored configuration probability outside [0,1]")
        if "hits_M" in d and "N" in d and not (_eq(d["P_model"], d["hits_M"] / d["N"], 1e-12) and _eq(d["P_ref"], d["hits_I"] / d["N"], 1e-12)): raise InputContractError(f"{where}: stored P does not equal hits/N for configuration {e}")
    num0, den0 = float(PM @ prior), float(PI @ prior); Qp = (num0 / den0) if den0 > 0 else (math.inf if num0 > 0 else None)
    state = ev.get("Q_point_math_state")
    exp_state = "finite" if (Qp is not None and math.isfinite(Qp)) else ("positive_infinite" if Qp == math.inf else "undefined")
    if state is not None and state != exp_state: raise InputContractError(f"{where}: stored Q_point_math_state {state} != reconstructed {exp_state}")
    if exp_state == "finite":
        if not _eq(Q_point, Qp, 1e-12): raise InputContractError(f"{where}: stored Q point does not reproduce from stored configuration probabilities and prior")
    elif Q_point is not None: raise InputContractError(f"{where}: non-finite Q point must be stored as None with Q_point_math_state={exp_state}")
    fam_pos = ev.get("family_min_positive_clusters")
    if fam_pos is None: raise InputContractError(f"{where}: family positive-cluster evidence missing (not verifiable)")
    cfg_states, reproduced_min = _verify_point_precisions(per_cfg, where)
    if tuple(fam_pos) != reproduced_min:
        raise InputContractError(f"{where}: family minimum positive-cluster counts differ from the points")
    fam_pos = reproduced_min
    if any(st == "technical_fail" for st in cfg_states.values()):
        if prec["state"] != "technical_fail": raise InputContractError(f"{where}: configuration technical_fail not propagated to family precision")
        p = None
    else:
        p = precision_state(rec[RULES.formal_seed], rec, Qp if exp_state == "finite" else None, int(fam_pos[0]), int(fam_pos[1]))
        exp_prec = p.state if (p.state != "pass" or all(st == "pass" for st in cfg_states.values())) else "precision-unresolved"
        if prec["state"] != exp_prec or not _eq(prec.get("rel_halfwidth"), p.rel_halfwidth, 1e-12) or not _eq(prec.get("width_cv_logQ"), p.width_cv_logQ, 1e-12): raise InputContractError(f"{where}: stored family precision does not reproduce (state/rel_halfwidth/cv)")
        if exp_prec != p.state:
            from .precision import PrecisionState
            p = PrecisionState(exp_prec, p.rel_halfwidth, p.width_cv_logQ, p.positive_clusters_model, p.positive_clusters_ref, p.reasons)
    if p is None:
        q = dict(audit="technical_fail", lower=None, upper=None, point=None)
    else:
        qs = ratio_quantity(where, rec[RULES.formal_seed], p, Qp if exp_state == "finite" else None); q = dict(audit=qs.audit, lower=qs.lower, upper=qs.upper, point=qs.point)
    if stored_quantity is not None: _quantity_equal(q, stored_quantity, f"{where} quantity")
    return q


def _verify_logD(res: dict) -> dict:
    """Stored per-point / mixture sensitivity values -> audits; stored replicates + invalid mask -> CI; -> logD_quantity and the Dpoint audit token. Returns (quantity dict, dpoint_audit, dci_audit)."""
    lg = res["logD"]; ev = res["evidence"].get("logD") or {}
    if "per_point" not in ev or "mixture_audit" not in ev: raise InputContractError("logD evidence missing (not verifiable)")
    if not isinstance(ev["per_point"], dict) or set(ev["per_point"]) != set(res["per_config"]):
        raise InputContractError("logD point evidence must cover exactly the matched configurations")
    expected_factors = {"x0.7", "x1.4"}
    tech = bool(ev.get("technical", False))
    for e, d in ev["per_point"].items():
        if d.get("point") is None:
            if d["audit"]["state"] != "technical_fail": raise InputContractError(f"logD point {e}: missing point must be technical")
            tech = True; continue
        if not isinstance(d.get("sensitivity"), dict) or set(d["sensitivity"]) != expected_factors:
            raise InputContractError(f"logD point {e}: bandwidth sensitivity inventory incomplete")
        a = sensitivity_audit(d["point"], d["sensitivity"])
        if a["state"] != d["audit"]["state"] or bool(a["pass_"]) != bool(d["audit"]["pass_"]): raise InputContractError(f"logD point {e}: stored bandwidth audit does not reproduce from the stored sensitivity values")
        if a["state"] == "technical_fail": tech = True
    point = lg["point"]
    if point is None or not (isinstance(point, (int, float)) and math.isfinite(float(point))):
        mix = dict(state="technical_fail", pass_=False)
        if not tech: raise InputContractError("non-finite mixture logD without a technical flag")
    else:
        if not isinstance(lg.get("sensitivity"), dict) or set(lg["sensitivity"]) != expected_factors:
            raise InputContractError("mixture logD bandwidth sensitivity inventory incomplete")
        mix = sensitivity_audit(point, lg["sensitivity"])
        if mix["state"] != ev["mixture_audit"]["state"]: raise InputContractError("stored mixture bandwidth audit does not reproduce")
    expected_pass = (not tech) and mix["pass_"] and all(d["audit"]["pass_"] for d in ev["per_point"].values())
    if bool(lg["sensitivity_pass"]) != expected_pass: raise InputContractError("stored sensitivity_pass does not equal the merged per-point AND mixture audit")
    ci_obj = None
    if lg.get("ci") is not None:
        cd = lg["ci"]; _check_ci_schema(cd, "logD CI", "logD"); vals = ev.get("replicate_values"); mask = ev.get("invalid_mask")
        if vals is None or mask is None or len(vals) != len(mask) or len(vals) != int(cd["B"]): raise InputContractError("logD CI stored without matching replicate values / invalid mask (not verifiable)")
        raw_vals, raw_mask = np.asarray(vals, dtype=object), np.asarray(mask)
        if raw_vals.ndim != 1 or raw_mask.ndim != 1 or raw_mask.shape != raw_vals.shape or raw_mask.dtype.kind != "b":
            raise InputContractError("logD replicate_values must be 1-D and invalid_mask must be a matching boolean array")
        vals = np.asarray([np.nan if v is None else v for v in vals], float)
        mask = raw_mask
        n_fail = int(mask.sum() + np.sum(~np.isfinite(vals) & ~mask))
        if n_fail > 0:
            if cd["math_state"] != "technical_fail" or int(cd["counts"].get("technical_invalid", 0)) != n_fail: raise InputContractError("logD CI must be technical_fail with the invalid count equal to the stored mask")
            ci_obj = _ci_from_dict(cd)
        else:
            L, U = float(np.quantile(vals, RULES.alpha / 2)), float(np.quantile(vals, 1 - RULES.alpha / 2))
            if not (_eq(cd["log_lower"], L, 1e-12) and _eq(cd["log_upper"], U, 1e-12) and cd["math_state"] == "finite" and int(cd["counts"].get("technical_invalid", 0)) == 0): raise InputContractError("stored logD CI does not reproduce from the stored replicate values")
            ci_obj = _ci_from_dict(cd)
    q = logD_quantity("logD_matched", (None if tech else point), ci_obj)
    dpoint = "technical_fail" if (tech or q.audit == "technical_fail") else ("pass" if expected_pass else "fail")
    return dict(audit=q.audit, lower=q.lower, upper=q.upper, point=q.point), dpoint, tech


def _verify_decision(res: dict, qQ: dict, qD: dict, dpoint: str, tech_D: bool, qN):
    need_ci = logD_ci_required(qQ["lower"], qQ["upper"]) if qQ["audit"] == "pass" else False
    stored_status = res["decision"]["ci_computation_status"].get("logD_CI"); exp_status = qD["audit"] if (need_ci or qD["audit"] == "technical_fail") else "not_computed_by_registered_short_circuit"
    if stored_status != exp_status: raise InputContractError(f"stored logD CI computation status {stored_status!r} does not follow from the registered dependency ({exp_status!r})")
    if need_ci and res["logD"].get("ci") is None and qD["audit"] != "technical_fail": raise InputContractError("logD CI required by the registered dependency but not stored")
    x = CoreInputs(audit_Q_matched=qQ["audit"], audit_Dpoint_matched=dpoint, audit_DCI_matched=exp_status, audit_Q_native=(qN["audit"] if qN else "unresolved"),
                   L_Q_matched=qQ["lower"], U_Q_matched=qQ["upper"], logD_point_matched=(float("nan") if tech_D else qD["point"]), L_logD_matched=qD["lower"], U_logD_matched=qD["upper"],
                   L_Q_native=(qN["lower"] if qN else None), U_Q_native=(qN["upper"] if qN else None))
    d2 = decide_core(x); dec = res["decision"]
    for k in ("support_truth", "strong_truth", "unsupported_truth", "technical_status", "display_label"):
        if getattr(d2, k) != dec[k]: raise InputContractError(f"stored decision.{k} does not reproduce from the verified quantities")
    exp = dict(support=d2.support_truth, strong=d2.strong_truth, unsupported=d2.unsupported_truth)
    coverage_ok = res["evidence"].get("coverage_ok")
    if type(coverage_ok) is not bool:
        raise InputContractError("structured coverage_ok boolean missing; prose notes are not a coverage contract")
    if not coverage_ok: exp = {k: (TECH if v == TECH else UNKNOWN) for k, v in exp.items()}
    if res["truths"] != exp: raise InputContractError("stored truths do not correspond to the verified decision (and coverage)")


def _verify_failed_record(res: dict) -> str:
    fr = (res.get("evidence") or {}).get("failed_record")
    if not fr or fr.get("kind") != "N_selection_technical_failure" or fr.get("reevaluated") is not False or fr.get("rescued_by_expansion") is not False: raise InputContractError("failed record lacks the registered N-selection failure schema")
    if res["truths"] != dict(support=TECH, strong=TECH, unsupported=TECH): raise InputContractError("failed record carries non-TECH truths")
    d = res["decision"]
    if d["technical_status"] != "technical_fail" or d["display_label"] in ("support", "strong", "unsupported") or any(d[k] != TECH for k in ("support_truth", "strong_truth", "unsupported_truth")): raise InputContractError("failed record carries a success decision")
    if res.get("Q_point") is not None or res.get("logD") is not None or (res["Q_ci_seed0"] or {}).get("math_state") != "technical_fail" or res["precision"]["state"] != "technical_fail": raise InputContractError("failed record must not carry numeric Q/logD values")
    if not fr.get("systems"): raise InputContractError("failed record must name the failed system(s)")
    return "technical_fail_record (N-selection failure; no numeric verification possible; not rescued)"


def _verify_stored_gate(res: dict, extra=None):
    """Recompute a saved gate's mode-specific summary from its complete check table.
    This is internal replay conditional on recorded measurements. It does NOT
    authenticate a former live runtime or re-hash absent external banks.
    Call on normal AND technical-failure records, at both write and read boundaries.
    """
    import re
    from .official_gate import EXPECTED_VERS, N_FIT, M_FIT, B_KDE, _blas_check
    ev = res.get("evidence") or {}
    gate = ev.get("gate")
    if extra is not None and not isinstance(extra, dict):
        raise InputContractError("checkpoint extra must be a dictionary")
    outer_mode = (extra or {}).get("mode")
    if gate is None:
        if outer_mode is not None:
            raise InputContractError("a mode-tagged formal checkpoint must contain its gate evidence")
        return None                         # historical core-only checkpoint, no formal claim
    if not isinstance(gate,dict): raise InputContractError("gate evidence must be a dictionary")
    mode = gate.get("mode"); rec = gate.get("record")
    if mode not in ("smoke","official") or (outer_mode is not None and outer_mode != mode):
        raise InputContractError("formal checkpoint mode declarations disagree")
    if not isinstance(rec,dict) or set(rec)!={"mode","passed","required_failures","diagnostics"}:
        raise InputContractError("stored gate record has an incomplete schema")
    if rec["mode"]!=mode or type(rec["passed"]) is not bool or not isinstance(rec["required_failures"],list):
        raise InputContractError("stored gate mode/passed/failure schema invalid")
    fp = gate.get("input_fingerprint")
    if not isinstance(fp,dict) or set(fp)!={"matched","native"}:
        raise InputContractError("stored gate requires both named fingerprint fields")
    def issha(v):return isinstance(v,str) and re.fullmatch(r"[0-9a-f]{64}",v) is not None
    native = res.get("native") is not None
    if not issha(fp["matched"]) or (native and not issha(fp["native"])) or (not native and fp["native"] is not None):
        raise InputContractError("stored gate input fingerprint is missing or malformed")
    diag=rec["diagnostics"]
    if not isinstance(diag,dict):raise InputContractError("stored gate diagnostics required")
    expected_diag={"env","environment_source","rules_binding","registered","profile_failures",
                   "version_mismatch","blas_threads_ok","checks","scope"}
    if set(diag)!=expected_diag:raise InputContractError("stored gate diagnostic inventory differs")
    if diag["environment_source"]!="live_collected":
        raise InputContractError("formal runner gate must record live-collected environment (pure injected tests are not execution receipts)")
    if ser.to_jsonable(diag["rules_binding"])!=ser.to_jsonable(BINDING):
        raise InputContractError("stored gate rules binding differs")
    expected_registered=dict(N0=RULES.N0,N_max=RULES.N_max,m=RULES.m,B=RULES.B,seeds=RULES.seeds,
                            N_fit=N_FIT,m_fit=M_FIT,B_KDE=B_KDE,versions=EXPECTED_VERS)
    if diag["registered"]!=expected_registered:raise InputContractError("stored gate registered profile differs")
    expected = {"system_conditioning":["smoke","official"],"native_present":["official"],
                "environment_versions":["official"],"BLAS_threads":["official"]}
    for label,side in (("matched",res),("native",res.get("native"))):
        if side is None:continue
        ids=list(side.get("per_config") or {})
        if not ids:raise InputContractError("gate result lacks the configuration inventory")
        for e in ids:
            for name in ("m","N0","N"):expected[f"{label}/{e}/{name}"]=["official"]
            expected[f"{label}/N_fit/{e}"]=["official"]
        for seed in range(RULES.seeds):
            for name in ("B","B_KDE"):expected[f"{label}/{name}/{seed}"]=["official"]
            expected[f"{label}/fitting_type/{seed}"]=["smoke","official"]
        for name in ("fitting_bound","grid_identity","cov_binding"):
            expected[f"{label}/{name}"]=["smoke","official"]
        expected[f"{label}/full_size_scope"]=["official"]
    checks=diag["checks"]
    if not isinstance(checks,list) or any(not isinstance(c,dict) for c in checks):
        raise InputContractError("stored gate checks must be a complete list")
    codes=[c.get("code") for c in checks]
    if any(not isinstance(c,str) for c in codes) or len(codes)!=len(set(codes)) or set(codes)!=set(expected):
        raise InputContractError("stored gate check code inventory is incomplete or duplicated")
    for c in checks:
        if set(c)!={"code","passed","required_modes","message"} or type(c["passed"]) is not bool or not isinstance(c["message"],str):
            raise InputContractError("stored individual gate check schema invalid")
        if c["required_modes"]!=expected[c["code"]]:
            raise InputContractError("stored gate required modes differ from code policy")
    bycode={c["code"]:c for c in checks}
    env=diag["env"]
    if not isinstance(env,dict):raise InputContractError("stored environment snapshot missing")
    mismatch={k:(env.get(k),v) for k,v in EXPECTED_VERS.items() if env.get(k)!=v}
    blas=_blas_check(env.get("blas_threads"))
    if bycode["environment_versions"]["passed"]!=(not mismatch) or bycode["BLAS_threads"]["passed"]!=blas:
        raise InputContractError("stored environment gate does not follow its measured snapshot")
    if ser.to_jsonable(diag["version_mismatch"])!=ser.to_jsonable(mismatch) or diag["blas_threads_ok"] is not blas:
        raise InputContractError("stored environment gate summaries disagree")
    if bycode["native_present"]["passed"]!=native:
        raise InputContractError("stored native presence check disagrees with result")
    failures=[c["message"] for c in checks if not c["passed"] and mode in expected[c["code"]]]
    if rec["required_failures"]!=failures or rec["passed"]!=(not failures):
        raise InputContractError("stored gate summary does not follow its required checks")
    if not rec["passed"]:
        raise InputContractError("a formal evaluation result cannot carry a failed preflight gate")
    return mode


def read_family_result(path: str, expected_sha256: str = None) -> dict:
    body = open(path, "rb").read()
    if expected_sha256 is not None and hashlib.sha256(body).hexdigest() != expected_sha256: raise InputContractError("checkpoint bytes do not match the expected SHA256")
    payload = ser.loads(body.decode("utf-8"))
    if payload.get("kind") != "FamilyResult": raise InputContractError("not a FamilyResult checkpoint")
    b = payload["binding"]; cur = binding_manifest()
    for k in ("engine_version", "rules_document_sha256", "tables_sha256"):
        if b.get(k) != cur[k]: raise InputContractError(f"checkpoint {k} differs from the current binding")
    if b.get("modules") != cur["modules"]: raise InputContractError("checkpoint module SHAs differ from the current engine modules (full fixed inventory)")
    if b.get("registered_profile") != cur["registered_profile"]: raise InputContractError("checkpoint registered profile differs from the registered rules profile")
    res = payload["result"]
    from .production import validate_grid_archive
    validate_grid_archive(res)
    from .twelve_eval import validate_twelve_archive
    validate_twelve_archive(res)
    for k in ("family", "Q_point", "Q_ci_seed0", "precision", "per_config", "logD", "decision", "truths", "evidence"):
        if k not in res: raise InputContractError(f"checkpoint result lacks '{k}'")
    if b.get("execution_profile") != execution_profile_from_result(res): raise InputContractError("stored execution profile does not describe the stored result")
    _verify_stored_gate(res, payload.get("extra"))
    if (res.get("evidence") or {}).get("failed_record") or (res["Q_ci_seed0"] or {}).get("math_state") == "technical_fail":
        return payload | dict(verified=_verify_failed_record(res))
    ev = res["evidence"]
    for k in ("matched", "cis_all_seeds", "quantities"):
        if k not in ev: raise InputContractError(f"evidence lacks '{k}' (not verifiable)")
    qQ = _verify_Q_side(ev["matched"], res["Q_ci_seed0"], res["precision"], res["per_config"], ev["cis_all_seeds"], res["Q_point"], ev["quantities"].get("Q_matched"), "matched")
    qN = None
    if res.get("native"):
        nv = res["native"]
        if not (nv.get("evidence") and nv.get("per_config") and nv["evidence"].get("cis_all_seeds")): raise InputContractError("native evidence missing (not verifiable)")
        qN = _verify_Q_side(nv["evidence"], nv["Q_ci_seed0"], nv["precision"], nv["per_config"], nv["evidence"]["cis_all_seeds"], nv["Q_point"], ev["quantities"].get("Q_native"), "native")
    qD, dpoint, tech_D = _verify_logD(res); _quantity_equal(qD, ev["quantities"]["logD_matched"], "logD quantity")
    _verify_decision(res, qQ, qD, dpoint, tech_D, qN)
    if res.get("position_status") and "position" in ev:
        w2 = ev["position"].get("w2") or {}
        if "stop" in w2:
            from .w2_stop import StopResult
            StopResult(**{k: w2["stop"][k] for k in ("B_final", "stop_reason", "trace", "null_prefix_id", "state", "observed_hash", "observed")}).validate()
    gate = ev.get("gate")
    ps = (res.get("position_status") or {}).get("state", "not-integrated")
    return payload | dict(verified="verified (core, conditional on stored replicate values/densities; position scope: %s; gate: %s)" % (ps, (gate or {}).get("mode", "none")))
