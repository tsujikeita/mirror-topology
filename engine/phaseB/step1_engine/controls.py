# -*- coding: utf-8 -*-
"""Control-battery helpers (rules §9.3; engine spec T16; B-3-1 audit R31-A..D).
- Negative control: model and reference are INDEPENDENT samples, so numerator and denominator are resampled with INDEPENDENT plans (different CRN groups); a fixed-target negative
  succeeds only with technical ok AND a DEFINITE False for support and strong (unknown is recorded, never success). The registered false-support-rate check aggregates n independent
  pseudo thresholds with Wilson(c+u, n) <= 0.05 (unknown counted on the upper side, technical failures fail the check).
- Positive controls: the REGISTERED synthetic boost (rules §9.3 / A10c: the isotropic reference bank scaled by 0.35 in T1 and T2, same clusters -> paired) is the required gate;
  any other boosted fixture is a separate diagnostic.
- Conjunct battery: explicit support/strong bases, one condition changed per case (including audit_Q_matched fail and the logD-point-only case on the support base), and a mutant
  detector: deciders with one conjunct deliberately removed must be caught by the battery while the registered decider passes it.
- Brute-force: a pure-Python row-loop oracle (per-cluster hit vectors) compared with the ACTUAL evaluation aggregation (ConfigBank.hit_tables -> HitTable -> literal resampling sums);
  a detector self-test proves the comparison catches a corrupted aggregation path."""
from __future__ import annotations
from typing import Callable, Dict, List, Optional, Sequence
import math
import numpy as np
from .errors import InputContractError
from .rules_config import RULES
from .ci import ci_from_replicates
from .precision import precision_state
from .quantity import ratio_quantity, logD_quantity
from .decision import CoreInputs, decide_core, logD_ci_required
from .calibration import calibrate, any_family_truth
from .truth import TECH, UNKNOWN, and3, audit_truth
from .bootstrap_plan import BootstrapPlan, HitTable, resample_hits, literal_resample_hits
from .density import logD_at, kde_logpdf_replicates, sensitivity_audit, SENS_FACTORS


# ------------------------------------------------------------------------------------------------------------ negative control (independent resampling)
def independent_Q_ci(hitsM: np.ndarray, hitsI: np.ndarray, planM: BootstrapPlan, planI: BootstrapPlan, NM: int, NI: int, m: int, uidsM, uidsI, seed_id: int):
    """Numerator from planM (group of the model sample), denominator from planI (group of the reference sample): independent multiplicities."""
    if planM.rng_keys[0][3] == planI.rng_keys[0][3]: raise InputContractError("independent resampling requires different CRN groups for model and reference")
    PM, _ = resample_hits(planM, {0: HitTable(uidsM, np.asarray(hitsM, np.int64), NM, m)}); PI, _ = resample_hits(planI, {0: HitTable(uidsI, np.asarray(hitsI, np.int64), NI, m)})
    return ci_from_replicates(PM, PI, mode="Q", seed_id=seed_id), PM, PI


def negative_decision(model: dict, ref: dict, uidsM, uidsI, plansM: Dict[int, BootstrapPlan], plansI: Dict[int, BootstrapPlan], m: int, fitM: Optional[dict], fitI: dict, cidfM, cidfI, fitplansM, fitplansI, t1: float, t2: float,
                      native: Optional[dict] = None) -> dict:
    """One negative evaluation at (t1, t2). model/ref: dict(T1, T2). Returns truths with the fixed-target gate rule and full evidence."""
    K = len(uidsM); NM, NI = len(model["T1"]), len(ref["T1"])
    hm = ((model["T1"] <= t1) & (model["T2"] <= t2)).reshape(K, m).sum(1); hi = ((ref["T1"] <= t1) & (ref["T2"] <= t2)).reshape(len(uidsI), m).sum(1)
    cis = [independent_Q_ci(hm, hi, plansM[s], plansI[s], NM, NI, m, uidsM, uidsI, s)[0] for s in range(RULES.seeds)]
    Qp = (hm.sum() / NM) / (hi.sum() / NI) if hi.sum() > 0 else (math.inf if hm.sum() > 0 else None)
    prec = precision_state(cis[0], cis, Qp if (Qp is not None and math.isfinite(Qp)) else None, int((hm > 0).sum()), int((hi > 0).sum()))
    qQ = ratio_quantity("Q_matched", cis[0], prec, Qp if (Qp is not None and math.isfinite(Qp)) else None)
    logD_pt = None; sens = {}; aud = dict(state="not_computed", pass_=False); ci = None; dpoint = "unresolved"
    # registered short circuit for the support-rate check: when the Q audit fails/unresolved or L_Q < Q_support the support truth is already decided without logD
    # (and3: False dominates; unknown audit -> unknown); the density is then not computed and the reason is recorded (never treated as a positive logD)
    need_logD = fitM is not None and qQ.audit == "pass" and qQ.lower is not None and qQ.lower >= RULES.Q_support
    logD_note = None if fitM is None else ("computed" if need_logD else f"skipped: support already decided by the Q branch (audit={qQ.audit}, L_Q={qQ.lower})")
    if need_logD:
        XM = np.c_[fitM["T1"], fitM["T2"]]; XI = np.c_[fitI["T1"], fitI["T2"]]
        logD_pt = logD_at(XM, cidfM, XI, cidfI, np.array([t1, t2])); sens = {f"x{fs}": logD_at(XM, cidfM, XI, cidfI, np.array([t1, t2]), factor_scale=fs) for fs in SENS_FACTORS}; aud = sensitivity_audit(logD_pt, sens); dpoint = "technical_fail" if aud["state"] == "technical_fail" else ("pass" if aud["pass_"] else "fail")
        if qQ.audit == "pass" and logD_ci_required(qQ.lower, qQ.upper):
            MM = fitplansM[RULES.formal_seed].multiplicities if hasattr(fitplansM[RULES.formal_seed], "multiplicities") else fitplansM[RULES.formal_seed]; MI = fitplansI[RULES.formal_seed].multiplicities if hasattr(fitplansI[RULES.formal_seed], "multiplicities") else fitplansI[RULES.formal_seed]
            lm = kde_logpdf_replicates(XM, cidfM, np.array([[t1, t2]]), MM)[:, 0]; li = kde_logpdf_replicates(XI, cidfI, np.array([[t1, t2]]), MI)[:, 0]; vals = lm - li           # independent fitting plans
            from .ci import CIResult
            ci = CIResult("logD", float(np.quantile(vals, RULES.alpha / 2)), float(np.quantile(vals, 1 - RULES.alpha / 2)), None, None, "linear_logD", "finite", dict(finite=len(vals), technical_invalid=0), RULES.alpha, len(vals), None, 0) if np.all(np.isfinite(vals)) else CIResult("logD", None, None, None, None, "none", "technical_fail", dict(technical_invalid=int(np.sum(~np.isfinite(vals)))), RULES.alpha, len(vals), "non-finite replicate", 0)
    qD = logD_quantity("logD_matched", logD_pt, ci)
    qN_audit, LN, UN = "unresolved", None, None
    if native is not None: qN_audit, LN, UN = native["audit"], native.get("lower"), native.get("upper")
    x = CoreInputs(audit_Q_matched=qQ.audit, audit_Dpoint_matched=dpoint, audit_DCI_matched=(qD.audit if (ci is not None or qD.audit == "technical_fail") else "not_computed_by_registered_short_circuit"), audit_Q_native=qN_audit, L_Q_matched=qQ.lower, U_Q_matched=qQ.upper, logD_point_matched=qD.point, L_logD_matched=qD.lower, U_logD_matched=qD.upper, L_Q_native=LN, U_Q_native=UN)
    dec = decide_core(x); truths = dict(support=dec.support_truth, strong=dec.strong_truth, unsupported=dec.unsupported_truth)
    gate = bool(dec.technical_status == "ok" and truths["support"] is False and truths["strong"] is False)                                   # unknown is NOT success
    return dict(gate=gate, truths=truths, technical_status=dec.technical_status, display_label=dec.display_label, Q_point=Qp, precision=prec.as_dict(), Q_ci_seed0=cis[0].as_dict(), logD_point=logD_pt, logD_note=logD_note, sensitivity=sens, sensitivity_audit=aud, logD_ci=(None if ci is None else ci.as_dict()), hits=dict(model=int(hm.sum()), ref=int(hi.sum())), resampling="independent numerator/denominator plans (different CRN groups)", reasons=dec.reason_codes)


def negative_rate_check(support_truths: Sequence[object], threshold: float = None) -> dict:
    """Registered false-support-rate check (rules §9.3): Wilson(c+u, n) <= 0.05 with unknown on the upper side; any technical failure fails the check."""
    thr = RULES.usable_support if threshold is None else threshold; s = calibrate(list(support_truths), thr, expected_n=len(support_truths))
    ok = bool(s.status == "ok" and s.wilson_upper_c_plus_u is not None and s.wilson_upper_c_plus_u <= thr)
    return dict(ok=ok, n=s.n, c_true=s.c_true, u_unknown=s.u_unknown, technical=s.technical_fail, wilson_upper_c_plus_u=s.wilson_upper_c_plus_u, threshold=thr, note="unknown counted as possible false support (c+u); not dropped from the denominator")


# ------------------------------------------------------------------------------------------------------------ conjunct battery with mutant detection
def _strong_base(q):
    return dict(audit_Q_matched="pass", audit_Dpoint_matched="pass", audit_DCI_matched="pass", audit_Q_native="pass", L_Q_matched=q["L_Q"], U_Q_matched=q["U_Q"], logD_point_matched=q["logD_point"], L_logD_matched=q["L_logD"], U_logD_matched=q["U_logD"], L_Q_native=q["L_Qn"], U_Q_native=q["U_Qn"])


def conjunct_cases(q: dict) -> dict:
    """q: the positive control's actual quantities (L_Q, U_Q, logD_point, L_logD, U_logD, L_Qn, U_Qn). One condition changed per case."""
    b = _strong_base(q); sb = dict(b, audit_DCI_matched="not_computed_by_registered_short_circuit", L_logD_matched=None, U_logD_matched=None, audit_Q_native="unresolved", L_Q_native=None, U_Q_native=None)
    strong = {"audit_Q_matched_fail": dict(audit_Q_matched="fail"), "audit_Dpoint_fail": dict(audit_Dpoint_matched="fail"), "audit_DCI_fail": dict(audit_DCI_matched="fail"), "audit_Q_native_fail": dict(audit_Q_native="fail"),
              "L_Q_below_10": dict(L_Q_matched=9.9, U_Q_matched=max(b["U_Q_matched"], 9.95)), "L_logD_nonpositive": dict(L_logD_matched=-0.01), "native_neutral": dict(L_Q_native=0.99, U_Q_native=max(b["U_Q_native"], 1.0))}
    support = {"audit_Q_matched_fail": dict(audit_Q_matched="fail"), "audit_Dpoint_fail": dict(audit_Dpoint_matched="fail"), "L_Q_below_3": dict(L_Q_matched=2.9, U_Q_matched=max(sb["U_Q_matched"], 2.95)), "logD_point_nonpositive": dict(logD_point_matched=0.0)}
    return dict(strong_base=b, support_base=sb, strong_drops=strong, support_drops=support)


def _mutants():
    """Deciders with ONE registered conjunct deliberately removed (for detector self-test only)."""
    def wrap(skip):
        def dec(x: CoreInputs):
            d = decide_core(x); ge, gt = (lambda a, b: a >= b), (lambda a, b: a > b)
            def cmpv(v, op, thr): return UNKNOWN if v is None else (TECH if (isinstance(v, float) and math.isnan(v)) else bool(op(v, thr)))
            aQ = True if skip == "audit_Q" else audit_truth(x.audit_Q_matched); aD = audit_truth(x.audit_Dpoint_matched); aDCI = audit_truth(x.audit_DCI_matched); aQn = True if skip == "audit_native" else audit_truth(x.audit_Q_native)
            support = and3(aQ, aD, cmpv(x.L_Q_matched, ge, RULES.Q_support), True if skip == "logD_point" else cmpv(x.logD_point_matched, gt, 0.0))
            strong = and3(support, aDCI, True if skip == "L_Q10" else cmpv(x.L_Q_matched, ge, RULES.Q_strong), True if skip == "L_logD" else cmpv(x.L_logD_matched, gt, 0.0), aQn, True if skip == "native_pos" else cmpv(x.L_Q_native, gt, 1.0))
            return dict(support=support, strong=strong)
        return dec
    return {k: wrap(k) for k in ("audit_Q", "logD_point", "audit_native", "L_Q10", "L_logD", "native_pos")}


def conjunct_battery(q: dict) -> dict:
    """Bases must be definitely True; ordinary one-conjunct drops must be
    definitely False with technical_status=ok. Unknown/TECH is not success.
    Deliberately removed-conjunct mutants must violate a tested False case.
    """
    cs = conjunct_cases(q)
    def reg(x):
        d = decide_core(CoreInputs(**x))
        return dict(support=d.support_truth, strong=d.strong_truth,
                    technical_status=d.technical_status)
    rb = reg(cs["strong_base"]); rs = reg(cs["support_base"])
    sd = {k: reg(dict(cs["strong_base"], **kw)) for k, kw in cs["strong_drops"].items()}
    pd = {k: reg(dict(cs["support_base"], **kw)) for k, kw in cs["support_drops"].items()}
    strong_res = {k: d["strong"] for k, d in sd.items()}
    support_res = {k: d["support"] for k, d in pd.items()}
    registered_ok = bool(
        rb["strong"] is True and rs["support"] is True
        and all(d["technical_status"] == "ok" for d in [rb, rs, *sd.values(), *pd.values()])
        and all(v is False for v in strong_res.values())
        and all(v is False for v in support_res.values()))
    detect = {}
    for name, mut in _mutants().items():
        caught = False
        for k, kw in cs["strong_drops"].items():
            if mut(CoreInputs(**dict(cs["strong_base"], **kw)))["strong"] is True and strong_res[k] is False:
                caught = True
        for k, kw in cs["support_drops"].items():
            if mut(CoreInputs(**dict(cs["support_base"], **kw)))["support"] is True and support_res[k] is False:
                caught = True
        detect[name] = caught
    return dict(ok=bool(registered_ok and all(detect.values())),
                registered=dict(strong_base=str(rb["strong"]), support_base=str(rs["support"]),
                                strong_drops={k: str(v) for k, v in strong_res.items()},
                                support_drops={k: str(v) for k, v in support_res.items()}),
                technical_statuses=dict(strong_base=rb["technical_status"], support_base=rs["technical_status"],
                                        strong_drops={k: d["technical_status"] for k, d in sd.items()},
                                        support_drops={k: d["technical_status"] for k, d in pd.items()}),
                mutants_detected=detect)


# ------------------------------------------------------------------------------------------------------------ brute-force against the actual aggregation path
def row_loop_oracle(T1: np.ndarray, T2: np.ndarray, m: int, t1: float, t2: float) -> np.ndarray:
    """Independent pure-Python oracle: per-cluster hit counts by an explicit row loop (no NumPy reductions)."""
    K = len(T1) // m; out = [0] * K
    for i in range(len(T1)):
        if float(T1[i]) <= t1 and float(T2[i]) <= t2: out[i // m] += 1
    return np.asarray(out, np.int64)


def bruteforce_check(cfg, thresholds: Sequence[tuple], plan: BootstrapPlan, hit_tables_fn: Optional[Callable] = None) -> dict:
    """Compare the oracle per-cluster vectors with the ACTUAL path (ConfigBank.hit_tables -> HitTable.hits, UIDs, N) for model and reference, and the literal resampling sums
    (plan) of the actual tables with the oracle vectors. hit_tables_fn may be injected (detector self-test); default = the real cfg.hit_tables."""
    fn = hit_tables_fn or cfg.hit_tables; rows = []; ok = True
    for (a1, a2) in thresholds:
        for which, T1, T2 in (("model", cfg.T1_model, cfg.T2_model), ("ref", cfg.T1_ref, cfg.T2_ref)):
            tabs = fn(a1, a2, which)
            for b, (s, e) in cfg.batches.items():
                orc = row_loop_oracle(T1[s:e], T2[s:e], cfg.m, a1, a2); tab = tabs[b]
                same_vec = bool(np.array_equal(orc, tab.hits)) and tab.uids == cfg.cluster_uids[s // cfg.m:e // cfg.m] and tab.N == e - s
                if b in plan.strata and len(plan.strata[b]) == len(orc):
                    P_actual, sums_actual = resample_hits(plan, {b: HitTable(tab.uids, tab.hits, tab.N, cfg.m)}, {b: 1.0}); P_oracle, sums_oracle = literal_resample_hits(plan, {b: HitTable(cfg.cluster_uids[s // cfg.m:e // cfg.m], orc, e - s, cfg.m)}, {b: 1.0})
                    same_sums = bool(np.array_equal(sums_actual[b], sums_oracle[b]) and np.array_equal(P_actual, P_oracle))
                else: raise InputContractError("brute-force: every tested batch requires a matching resampling plan")
                ok &= same_vec and same_sums; rows.append(dict(thr=[a1, a2], role=which, batch=b, oracle_total=int(orc.sum()), actual_total=int(tab.hits.sum()), vector_equal=same_vec, resampled_sums_equal=same_sums))
    return dict(ok=bool(ok), rows=rows)


def bruteforce_detector_selftest(cfg, thresholds, plan) -> dict:
    """The comparison must FAIL for (a) an aggregation that zeroes hits and (b) one that permutes clusters while preserving totals; and PASS for the real path."""
    def zeroed(a1, a2, which):
        tabs = cfg.hit_tables(a1, a2, which); return {b: HitTable(t.uids, np.zeros_like(t.hits), t.N, t.m) for b, t in tabs.items()}
    def permuted(a1, a2, which):
        tabs = cfg.hit_tables(a1, a2, which); return {b: HitTable(t.uids, t.hits[::-1].copy(), t.N, t.m) for b, t in tabs.items()}
    real = bruteforce_check(cfg, thresholds, plan)["ok"]; z = bruteforce_check(cfg, thresholds, plan, zeroed)["ok"]; p = bruteforce_check(cfg, thresholds, plan, permuted)["ok"]
    return dict(ok=bool(real and not z and not p), real_path=real, zeroed_detected=(not z), permuted_detected=(not p))
