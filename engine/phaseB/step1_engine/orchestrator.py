# -*- coding: utf-8 -*-
"""evaluate_threshold orchestrator (rules §1.4, §7, §8, §9.2; engine spec R7). Applies the SAME procedure to the real target and to every pseudo threshold.
Contracts enforced at entry (no silent repair): registered prior weights (finite, non-negative, sum to 1, one per configuration; never renormalised), exact 5-seed
plan inventory with plan.seed_id == key, validated fitting banks/plans, finite thresholds. State precedence: technical_fail > (unresolved/unknown) > definite.
Evidence needed for the archive (5-seed Q bootstrap inputs, native family state, per-point and mixed KDE audits, logD replicates + invalid mask, prior, plan ids) is kept
in FamilyResult.evidence rather than discarded at the function exit."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
import math, hashlib, copy
import numpy as np
from scipy.special import logsumexp
from .errors import InputContractError
from .rules_config import RULES
from .ci import ci_from_replicates, CIResult
from .precision import precision_state, PrecisionState
from .family import mixed_numden, point_P
from .bootstrap_plan import BootstrapPlan, HitTable, resample_hits, FittingPlan, bank_sha256
from .types import ClusterUID
from .decision import CoreInputs, decide_core, logD_ci_required
from .quantity import ratio_quantity, logD_quantity
from .density import kde_logpdf_weighted, check_bank, check_multiplicities, sensitivity_audit, check_threshold, SENS_FACTORS
from .calibration import any_family_truth, calibrate
from .truth import TECH, UNKNOWN
KDE_CI_BACKEND = "per_replicate"   # registered reference path; "batched" is the equivalence-tested accelerated path (opt-in until audited)


@dataclass
class ConfigBank:
    evaluation_id: int; family: str; system: str; weight: float
    T1_model: np.ndarray; T2_model: np.ndarray; T1_ref: np.ndarray; T2_ref: np.ndarray
    cluster_uids: List[ClusterUID]; m: int; batches: Dict[int, Tuple[int, int]]
    def __post_init__(self):
        n = len(self.T1_model)
        for a in (self.T2_model, self.T1_ref, self.T2_ref):
            if len(a) != n: raise InputContractError("bank arrays must have equal length")
        if n != len(self.cluster_uids) * self.m: raise InputContractError("N must equal clusters * m")
        if not all(np.all(np.isfinite(a)) for a in (self.T1_model, self.T2_model, self.T1_ref, self.T2_ref)): raise InputContractError("bank contains non-finite T values (technical invalid)")
        if not (isinstance(self.weight, (int, float)) and math.isfinite(float(self.weight)) and float(self.weight) >= 0): raise InputContractError("configuration weight must be finite and non-negative")
        # stage contract (rules §6.5 / table 4): batch 0 = N0 prefix; if an extension is registered it must be exactly batch 1 = 3*N0 rows so that the full bank is 4*N0.
        # batch bounds must be a contiguous partition on cluster boundaries. 'No extension' (single batch) is allowed (-> precision-unresolved if the gate fails); a malformed extension is a contract violation.
        if set(self.batches) not in ({0}, {0, 1}): raise InputContractError("batches must be {0} (N0 only) or {0, 1} (N0 prefix + 3*N0 extension)")
        s0, e0 = self.batches[0]
        if s0 != 0 or e0 <= 0 or e0 % self.m != 0: raise InputContractError("batch 0 must start at row 0 and end on a cluster boundary")
        if 1 in self.batches:
            s1, e1 = self.batches[1]
            if s1 != e0 or e1 != n or e1 % self.m != 0: raise InputContractError("extension batch must start where the prefix ends and end at the bank end on a cluster boundary")
            if n != 4 * e0: raise InputContractError(f"N4 requires exactly 4 x N0 rows (N0={e0}, bank={n}); a {n / e0:.3g}x bank is not the registered single expansion")
        elif e0 != n: raise InputContractError("single-batch bank must cover all rows")

    @property
    def has_extension(self) -> bool: return 1 in self.batches
    @property
    def N0(self) -> int: return self.batches[0][1]

    def at_stage(self, stage: str) -> "ConfigBank":
        """N0 view = prefix batch 0 only; N4 view = all registered batches (requires the extension to exist)."""
        if stage == "N0":
            s, e = self.batches[0]; return ConfigBank(self.evaluation_id, self.family, self.system, self.weight, self.T1_model[s:e], self.T2_model[s:e], self.T1_ref[s:e], self.T2_ref[s:e], self.cluster_uids[s // self.m:e // self.m], self.m, {0: (0, e - s)})
        if stage == "N4":
            if not self.has_extension: raise InputContractError(f"configuration {self.evaluation_id}: N4 stage requested but no extension batch is registered")
            return self
        raise InputContractError("stage must be 'N0' or 'N4'")

    def hit_tables(self, t1: float, t2: float, which: str) -> Dict[int, HitTable]:
        T1, T2 = (self.T1_model, self.T2_model) if which == "model" else (self.T1_ref, self.T2_ref); hit = (T1 <= t1) & (T2 <= t2); out = {}
        for b, (s, e) in self.batches.items():
            ks, ke = s // self.m, e // self.m; out[b] = HitTable(self.cluster_uids[ks:ke], hit[s:e].reshape(-1, self.m).sum(axis=1).astype(np.int64), e - s, self.m)
        return out

    def positive_clusters(self, t1, t2, which) -> int: return int(sum((h.hits > 0).sum() for h in self.hit_tables(t1, t2, which).values()))
    def total_hits(self, t1, t2, which) -> int: return int(sum(int(h.hits.sum()) for h in self.hit_tables(t1, t2, which).values()))


@dataclass
class FittingBank:
    X_model: np.ndarray; X_ref: np.ndarray; cid: np.ndarray
    def __post_init__(self):
        self.X_model, self.cid = check_bank(self.X_model, self.cid); self.X_ref, cid2 = check_bank(self.X_ref, self.cid)
        if self.X_model.shape != self.X_ref.shape: raise InputContractError("model/reference fitting banks must be paired (same shape)")
    @property
    def K(self): return int(self.cid.max()) + 1


@dataclass
class FamilyInput:
    family: str; configs: List[ConfigBank]; plans: Dict[int, BootstrapPlan]; fitting: Dict[int, FittingBank]; fit_plans: Dict[int, np.ndarray]; coverage_ok: bool = True
    fitting_bindings: Optional[Dict[int, str]] = None        # evaluation_id -> expected bank SHA256 (per-configuration bank identity; separate from the shared resampling plan)
    grid_identity: Optional[dict] = None                     # production wrapper: registry SHA, manifest SHA, evaluation_id -> config_id map (carried into evidence, never inferred)

    def validate(self):
        if self.grid_identity is not None:
            from .production import validate_grid_identity
            if any(c.family != self.family or c.system != self.grid_identity.get("system") for c in self.configs):
                raise InputContractError("grid identity configuration family/system mismatch")
            validate_grid_identity(self.grid_identity, self.family, self.grid_identity.get("system"), [c.evaluation_id for c in self.configs], [c.weight for c in self.configs])
        if not self.configs: raise InputContractError("family has no configurations")
        w = np.array([c.weight for c in self.configs], float)
        if w.ndim != 1 or not np.all(np.isfinite(w)) or np.any(w < 0) or not np.isclose(w.sum(), 1.0, rtol=0, atol=1e-12): raise InputContractError(f"registered prior weights must be finite, non-negative and sum to 1 (got {w.tolist()}); weights are never renormalised")
        if set(self.plans) != set(range(RULES.seeds)): raise InputContractError(f"plans must be keyed by the exact seed inventory {list(range(RULES.seeds))}")
        for s, p in self.plans.items():
            if p.seed_id != s: raise InputContractError(f"plan under key {s} has seed_id {p.seed_id} (relabelling a plan as another seed is not allowed)")
            if p.replicates != self.plans[0].replicates: raise InputContractError("plans must share the replicate count")
            p.validate()
        if set(self.fitting) != {c.evaluation_id for c in self.configs}: raise InputContractError("fitting banks must be present for exactly the family's configurations")
        for e, fb in self.fitting.items():
            if not isinstance(fb, FittingBank): raise InputContractError("fitting entries must be FittingBank")
        if set(self.fit_plans) != set(range(RULES.seeds)): raise InputContractError("fit_plans must be keyed by the exact seed inventory")
        Ks = {fb.K for fb in self.fitting.values()}
        all_fp = all(isinstance(p, FittingPlan) for p in self.fit_plans.values()); groups = set()
        for s, M in self.fit_plans.items():
            if isinstance(M, FittingPlan):
                if M.seed_id != s: raise InputContractError(f"fitting plan under key {s} has seed_id {M.seed_id}")
                M.validate(); groups.add((M.wave_id, M.crn_group_id))
                if len(Ks) != 1 or M.K != next(iter(Ks)): raise InputContractError("fitting plan K must equal the (common) number of fitting clusters of the family")
            else:
                for K in Ks: check_multiplicities(M, K, f"fit plan seed {s}")
        if all_fp and len(groups) != 1: raise InputContractError("all fitting plans of a family must share one (wave, crn_group)")
        # per-configuration bank identity: bound only when an expected SHA exists for EVERY configuration and matches the actual arrays
        actual = {e: bank_sha256(fb.X_model, fb.X_ref, fb.cid) for e, fb in self.fitting.items()}; expected = dict(self.fitting_bindings or {})
        if all_fp and not expected and len(self.configs) == 1 and all(p.bank_sha256 is not None for p in self.fit_plans.values()):
            expected = {self.configs[0].evaluation_id: self.fit_plans[0].bank_sha256}                                      # single-bank convenience form
            if len({p.bank_sha256 for p in self.fit_plans.values()}) != 1: raise InputContractError("single-bank fitting plans must carry one common bank SHA")
        if expected:
            if set(expected) != set(actual): raise InputContractError("fitting_bindings must cover exactly the family's configurations")
            bad = [e for e in actual if expected[e] != actual[e]]
            if bad: raise InputContractError(f"fitting bank identity mismatch for configurations {bad} (plan/binding refers to a different bank)")
        elif all_fp and any(p.bank_sha256 is not None for p in self.fit_plans.values()):
            raise InputContractError("fitting plans carry a bank SHA but the family has several configurations: supply fitting_bindings per configuration")
        self.fitting_bank_sha256 = actual
        self.fitting_plan_binding = "bound" if (all_fp and expected) else ("unbound_plan_no_bank_binding (test-only)" if all_fp else "unbound_array (test-only; formal runs require FittingPlan + fitting_bindings)")
        if not isinstance(self.coverage_ok, bool): raise InputContractError("coverage_ok must be bool")
        return w


@dataclass
class FamilyResult:
    family: str; Q_point: Optional[float]; Q_ci_seed0: dict; precision: dict; per_config: dict; logD: Optional[dict]; native: Optional[dict]; decision: dict; truths: dict
    notes: List[str] = field(default_factory=list); evidence: dict = field(default_factory=dict); position_status: Optional[dict] = None
    def as_dict(self):
        from .serialization import to_jsonable
        return to_jsonable(asdict(self))


def _family_Q(fam: FamilyInput, t1: float, t2: float):
    """Family-mixed Q per seed: resample each configuration's P (stratified by batch) per replicate, mix with the REGISTERED prior weights, then ratio.
    Returns (Q_point, cis_per_seed, family_precision, per_config, w, evidence)."""
    w = fam.validate(); J = len(fam.configs)
    PM_pt = np.array([point_P(np.array([int(((c.T1_model <= t1) & (c.T2_model <= t2)).sum())]), np.array([len(c.T1_model)]))[0] for c in fam.configs])
    PI_pt = np.array([point_P(np.array([int(((c.T1_ref <= t1) & (c.T2_ref <= t2)).sum())]), np.array([len(c.T1_ref)]))[0] for c in fam.configs])
    num_pt, den_pt = mixed_numden(PM_pt[None, :], PI_pt[None, :], w); Q_pt = float(num_pt[0] / den_pt[0]) if den_pt[0] > 0 else (np.inf if num_pt[0] > 0 else np.nan)
    pos = {c.evaluation_id: (c.positive_clusters(t1, t2, "model"), c.positive_clusters(t1, t2, "ref")) for c in fam.configs}; fam_pos = (min(v[0] for v in pos.values()), min(v[1] for v in pos.values()))
    cis, per_cfg, boot = [], {c.evaluation_id: dict(P_model=float(PM_pt[i]), P_ref=float(PI_pt[i]), positive_clusters_model=pos[c.evaluation_id][0], positive_clusters_ref=pos[c.evaluation_id][1], hits_M=c.total_hits(t1, t2, "model"), hits_I=c.total_hits(t1, t2, "ref"), N=int(len(c.T1_model)), stage=("N4" if c.has_extension else "N0"), cis=[]) for i, c in enumerate(fam.configs)}, {}
    for s in range(RULES.seeds):
        plan = fam.plans[s]; PM = np.zeros((plan.replicates, J)); PI = np.zeros_like(PM)
        for i, c in enumerate(fam.configs):
            PM[:, i], _ = resample_hits(plan, c.hit_tables(t1, t2, "model")); PI[:, i], _ = resample_hits(plan, c.hit_tables(t1, t2, "ref"))
            per_cfg[c.evaluation_id]["cis"].append(ci_from_replicates(PM[:, i], PI[:, i], mode="Q", seed_id=s))
        num, den = mixed_numden(PM, PI, w); cis.append(ci_from_replicates(num, den, mode="Q", seed_id=s)); boot[s] = dict(plan_id=plan.plan_id, num=num, den=den)
    for eid, d in per_cfg.items():
        pp = d["cis"]; d["precision"] = precision_state(pp[0], pp, (d["P_model"] / d["P_ref"]) if d["P_ref"] > 0 else None, d["positive_clusters_model"], d["positive_clusters_ref"]).as_dict(); d["ci_seed0"] = pp[0].as_dict(); d["cis_all_seeds"] = [c.as_dict() for c in pp]; del d["cis"]
    states = {eid: d["precision"]["state"] for eid, d in per_cfg.items()}
    if any(st == "technical_fail" for st in states.values()):
        prec = PrecisionState("technical_fail", None, None, fam_pos[0], fam_pos[1], [f"configuration {eid} technical_fail" for eid, st in states.items() if st == "technical_fail"])
    else:
        prec = precision_state(cis[0], cis, Q_pt if np.isfinite(Q_pt) else None, fam_pos[0], fam_pos[1])
        if any(st != "pass" for st in states.values()) and prec.state == "pass":
            prec = PrecisionState("precision-unresolved", prec.rel_halfwidth, prec.width_cv_logQ, fam_pos[0], fam_pos[1], prec.reasons + [f"configuration {eid} {st} (family not renormalised)" for eid, st in states.items() if st != "pass"])
    ev = dict(prior=w.tolist(), family_min_positive_clusters=fam_pos, per_seed=boot, thresholds=(t1, t2), plan_ids=[fam.plans[s].plan_id for s in range(RULES.seeds)], Q_point_math_state=("finite" if np.isfinite(Q_pt) else ("positive_infinite" if Q_pt == np.inf else "undefined")))
    return Q_pt, cis, prec, per_cfg, w, ev


def _family_logD(fam: FamilyInput, t_eval: np.ndarray, w: np.ndarray, with_ci: bool):
    """Family-mixed logD and the merged bandwidth audit: every configuration's point audit AND the mixture audit must pass (rules §7.2).
    Returns (point, ci, sens_mixture, audit_pass, details) — details carry per-point values, audits, replicate values and the invalid mask."""
    if KDE_CI_BACKEND not in ("per_replicate", "batched"):
        raise InputContractError("unregistered KDE_CI_BACKEND")
    backend_requested = KDE_CI_BACKEND
    batch_fallback_reason = None
    ids = [c.evaluation_id for c in fam.configs]
    t_eval = check_threshold(t_eval)
    def lp(e, which, mult=None, fs=1.0):
        fb = fam.fitting[e]; X = fb.X_model if which == "model" else fb.X_ref; rows = np.ones(len(fb.cid)) if mult is None else np.asarray(mult, float)[fb.cid]
        v = float(kde_logpdf_weighted(X, rows, t_eval, fs)[0])
        if not math.isfinite(v): raise InputContractError(f"non-finite component log density: evaluation={e}, role={which}")   # a required component never enters the mixture as zero density
        return v
    per_point = {}
    for e in ids:
        try:
            pt = lp(e, "model") - lp(e, "ref"); sens = {f"x{fs}": (lp(e, "model", None, fs) - lp(e, "ref", None, fs)) for fs in SENS_FACTORS}; per_point[e] = dict(point=float(pt), sensitivity=sens, audit=sensitivity_audit(pt, sens))
        except InputContractError as ex: per_point[e] = dict(point=None, sensitivity={}, audit=dict(state="technical_fail", pass_=False, reason=str(ex)))
    def mixed(mult=None, fs=1.0):
        lm = np.array([lp(e, "model", mult, fs) for e in ids]); li = np.array([lp(e, "ref", mult, fs) for e in ids]); return float(logsumexp(lm + np.log(w)) - logsumexp(li + np.log(w)))
    try:
        point = mixed(); sens = {f"x{fs}": mixed(None, fs) for fs in SENS_FACTORS}; mix_aud = sensitivity_audit(point, sens)
    except InputContractError as ex: point = float("nan"); sens = {}; mix_aud = dict(state="technical_fail", pass_=False, reason=str(ex))
    tech = mix_aud["state"] == "technical_fail" or any(d["audit"]["state"] == "technical_fail" for d in per_point.values())
    audit_pass = (not tech) and mix_aud["pass_"] and all(d["audit"]["pass_"] for d in per_point.values())
    ci = None; vals = None; invalid = None
    if with_ci:
        fp = fam.fit_plans[RULES.formal_seed]; mults = fp.multiplicities if isinstance(fp, FittingPlan) else fp; B = mults.shape[0]; vals = np.full(B, np.nan); invalid = np.zeros(B, dtype=bool)
        if KDE_CI_BACKEND == "batched":
            # batched replicate log densities per configuration and role (same estimator; equivalence to the per-replicate reference is a registered test)
            from .density import kde_logpdf_replicates
            try:
                LM = np.column_stack([kde_logpdf_replicates(fam.fitting[e].X_model, fam.fitting[e].cid, t_eval[None, :], mults)[:, 0] for e in ids]); LI = np.column_stack([kde_logpdf_replicates(fam.fitting[e].X_ref, fam.fitting[e].cid, t_eval[None, :], mults)[:, 0] for e in ids])
                fin = np.isfinite(LM).all(1) & np.isfinite(LI).all(1); invalid[~fin] = True
                vals[fin] = logsumexp(LM[fin] + np.log(w), axis=1) - logsumexp(LI[fin] + np.log(w), axis=1)
            except InputContractError as ex:
                # Re-evaluate exactly the same registered replicates, not fresh RNG
                # draws. A batch-level exception does not prove every slot failed.
                batch_fallback_reason = str(ex)
                vals[:] = np.nan; invalid[:] = False
                for b in range(B):
                    try:
                        v = mixed(mults[b])
                        if math.isfinite(v): vals[b] = v
                        else: invalid[b] = True
                    except InputContractError: invalid[b] = True
        else:
            for b in range(B):
                try:
                    v = mixed(mults[b]); vals[b] = v
                    if not math.isfinite(v): invalid[b] = True
                except InputContractError: invalid[b] = True
        invalid |= ~np.isfinite(vals)
        vals[invalid] = np.nan
        n_fail = int(invalid.sum())
        if n_fail > 0: ci = CIResult("logD", None, None, None, None, "none", "technical_fail", dict(finite=B - n_fail, technical_invalid=n_fail), RULES.alpha, B, "KDE replicate failure (fail-closed)", RULES.formal_seed)
        else: ci = CIResult("logD", float(np.quantile(vals, RULES.alpha / 2)), float(np.quantile(vals, 1 - RULES.alpha / 2)), None, None, "linear_logD", "finite", dict(finite=B, technical_invalid=0), RULES.alpha, B, None, RULES.formal_seed)
    details = dict(ci_backend=(backend_requested if with_ci else "not_computed_by_registered_short_circuit"), batch_fallback_reason=batch_fallback_reason, per_point=per_point, mixture_audit=mix_aud, technical=tech, replicate_values=(None if vals is None else vals.tolist()), invalid_mask=(None if invalid is None else invalid.tolist()))
    return point, ci, sens, bool(audit_pass), details


def _check_systems(fam_matched: FamilyInput, fam_native: Optional[FamilyInput]):
    """matched/native identity (rules §1.4 strong: 'both systems checked' must bind to real inputs): roles, same family, distinct objects, coverage consistency."""
    if any(c.system != "matched" or c.family != fam_matched.family for c in fam_matched.configs): raise InputContractError("matched FamilyInput must contain configurations with system='matched' of the same family")
    if fam_native is None: return
    from .production import validate_grid_pair
    validate_grid_pair(fam_matched.grid_identity, fam_native.grid_identity)
    if fam_native is fam_matched: raise InputContractError("native input must be a distinct FamilyInput (the matched object was passed twice)")
    if fam_native.family != fam_matched.family: raise InputContractError("native input belongs to a different family")
    if any(c.system != "native" or c.family != fam_matched.family for c in fam_native.configs): raise InputContractError("native FamilyInput must contain configurations with system='native' of the same family")
    if {c.evaluation_id for c in fam_native.configs} & {c.evaluation_id for c in fam_matched.configs}: raise InputContractError("evaluation_ids must be distinct across systems")
    if fam_native.coverage_ok != fam_matched.coverage_ok: raise InputContractError("matched/native coverage flags disagree (geometric coverage is a property of the family)")


def evaluate_family(fam_matched: FamilyInput, fam_native: Optional[FamilyInput], t1: float, t2: float) -> FamilyResult:
    _check_systems(fam_matched, fam_native)
    notes = []; Qm, cis_m, prec_m, per_m, w, ev_m = _family_Q(fam_matched, t1, t2)
    qQm = ratio_quantity("Q_matched", cis_m[0], prec_m, Qm if np.isfinite(Qm) else None)
    need_ci = logD_ci_required(qQm.lower, qQm.upper) if qQm.audit == "pass" else False
    out = _family_logD(fam_matched, np.array([t1, t2]), w, with_ci=need_ci); logD_pt, logD_ci, sens, audit_pass = out[0], out[1], out[2], out[3]; details = out[4] if len(out) > 4 else {}
    tech_D = bool(details.get("technical", False)) or not (isinstance(logD_pt, (int, float)) and math.isfinite(float(logD_pt)))
    qD = logD_quantity("logD_matched", (None if tech_D else logD_pt), logD_ci); dpoint_audit = "technical_fail" if (tech_D or qD.audit == "technical_fail") else ("pass" if audit_pass else "fail")
    notes.append(f"logD_CI={'computed' if need_ci else 'not_computed_by_registered_short_circuit'}")
    native = None; qQn = None
    if fam_native is not None:
        Qn, cis_n, prec_n, per_n, _, ev_n = _family_Q(fam_native, t1, t2); qQn = ratio_quantity("Q_native", cis_n[0], prec_n, Qn if np.isfinite(Qn) else None)
        if fam_native.grid_identity is not None: ev_n["grid_identity"] = copy.deepcopy(fam_native.grid_identity)
        ev_n = dict(ev_n, cis_all_seeds=[c.as_dict() for c in cis_n]); native = dict(Q_point=(Qn if np.isfinite(Qn) else None), Q_ci_seed0=cis_n[0].as_dict(), precision=prec_n.as_dict(), per_config=per_n, quantity=qQn.as_dict(), evidence=ev_n)
    x = CoreInputs(audit_Q_matched=qQm.audit, audit_Dpoint_matched=dpoint_audit, audit_DCI_matched=(qD.audit if (need_ci or qD.audit == "technical_fail") else "not_computed_by_registered_short_circuit"),
                   audit_Q_native=(qQn.audit if qQn else "unresolved"), L_Q_matched=qQm.lower, U_Q_matched=qQm.upper, logD_point_matched=(None if tech_D else qD.point), L_logD_matched=qD.lower, U_logD_matched=qD.upper,
                   L_Q_native=(qQn.lower if qQn else None), U_Q_native=(qQn.upper if qQn else None))
    if tech_D: x.logD_point_matched = float("nan")                                                       # explicit technical marker for the decision layer
    dec = decide_core(x); truths = dict(support=dec.support_truth, strong=dec.strong_truth, unsupported=dec.unsupported_truth)
    if not fam_matched.coverage_ok:
        truths = {k: (TECH if v == TECH else UNKNOWN) for k, v in truths.items()}; notes.append("coverage: family not evaluable (undetermined mass); detected technical failures are retained")
    fp_ev = [dict(plan_id=p.plan_id, wave_id=p.wave_id, crn_group_id=p.crn_group_id, seed_id=p.seed_id, K=p.K, B=int(np.asarray(p.multiplicities).shape[0]), multiplicities_sha256=p.multiplicities_sha256) if isinstance(p, FittingPlan) else dict(unbound_array_sha256=hashlib.sha256(np.ascontiguousarray(p).tobytes()).hexdigest(), shape=list(np.asarray(p).shape)) for s, p in sorted(fam_matched.fit_plans.items())]
    evidence = dict(coverage_ok=fam_matched.coverage_ok, grid_identity=(copy.deepcopy(fam_matched.grid_identity) if fam_matched.grid_identity is not None else None), matched=ev_m, logD=details, fitting_plan_binding=getattr(fam_matched, 'fitting_plan_binding', None), fitting_plans=fp_ev, fitting_bindings=dict(fam_matched.fitting_bindings or {}), fitting_bank_sha256=getattr(fam_matched, 'fitting_bank_sha256', None), quantities=dict(Q_matched=qQm.as_dict(), logD_matched=qD.as_dict(), Q_native=(qQn.as_dict() if qQn else None)), cis_all_seeds=[c.as_dict() for c in cis_m])
    return FamilyResult(fam_matched.family, Qm if np.isfinite(Qm) else None, cis_m[0].as_dict(), prec_m.as_dict(), per_m, dict(point=logD_pt, ci=(logD_ci.as_dict() if logD_ci else None), sensitivity=sens, sensitivity_pass=audit_pass, per_point_audits={e: d["audit"] for e, d in details.get("per_point", {}).items()}), native, dec.as_dict(), truths, notes, evidence)


def _stage_family(fam: FamilyInput, stages: Dict[int, str]) -> FamilyInput:
    """Stage view changes ONLY the evaluation prefix of each configuration; plans, fitting banks, fitting plans, coverage and the fitting bank bindings are preserved."""
    from dataclasses import replace
    return replace(fam, configs=[c.at_stage(stages[c.evaluation_id]) for c in fam.configs])


def _stage_selection(fam: FamilyInput, t1: float, t2: float):
    """N-selection uses Q and the precision gate ONLY (rules §6.5): evaluate every configuration on its N0 prefix, decide the single expansion per configuration.
    KDE/core are not evaluated here (recorded as not_evaluated_in_N_selection); technical failure of the Q layer at N0 stops the selection (fail-closed)."""
    from .expansion import family_expansion_plan
    ids = [c.evaluation_id for c in fam.configs]; st0 = {e: "N0" for e in ids}
    Q0, cis0, prec0, per0, w0, ev0 = _family_Q(_stage_family(fam, st0), t1, t2)
    if prec0.state == "technical_fail": return dict(stages=st0, plan=None, technical=True, N0=dict(Q=Q0, precision=prec0.as_dict(), per_config=per0), kde="not_evaluated_in_N_selection")
    plan0 = family_expansion_plan(per0, "N0", expected_ids=ids)
    st1 = {e: ("N4" if (plan0["actions"][e]["action"] == "expand_to_4N0" and next(c for c in fam.configs if c.evaluation_id == e).has_extension) else "N0") for e in ids}
    notes = {e: "expansion required but no extension registered -> precision-unresolved" for e in ids if plan0["actions"][e]["action"] == "expand_to_4N0" and st1[e] == "N0"}
    return dict(stages=st1, plan=plan0, technical=False, N0=dict(Q=Q0, precision=prec0.as_dict(), per_config=per0), notes=notes, kde="not_evaluated_in_N_selection")


def _failed_result(fam_matched, fam_native, sel_m, sel_n, t1, t2) -> FamilyResult:
    """Explicit fail-closed result when the Q layer of the N-selection is technical: no re-evaluation, every truth TECH, decision technical, evidence retained."""
    from .decision import CoreDecision
    which = ("matched" if sel_m["technical"] else "") + (" native" if (sel_n is not None and sel_n["technical"]) else "")
    dec = CoreDecision(TECH, TECH, TECH, "technical_fail", "inconclusive", [f"N-selection technical failure ({which.strip()}); fail-closed, no expansion, no re-evaluation"], {}, {}, None)
    prec = dict(state="technical_fail", rel_halfwidth=None, width_cv_logQ=None, positive_clusters_model=0, positive_clusters_ref=0, reasons=["N-selection technical failure"])
    per = {e: dict(d, stage="N0") for e, d in sel_m["N0"]["per_config"].items()}
    native = None if sel_n is None else dict(Q_point=None, Q_ci_seed0=None, precision=dict(state="technical_fail" if sel_n["technical"] else "not_evaluated", reasons=[]), per_config=sel_n["N0"]["per_config"], quantity=None, evidence=None)
    r = FamilyResult(fam_matched.family, None, dict(value_domain="Q", log_lower=None, log_upper=None, lower=None, upper=None, effective_method="none", math_state="technical_fail", counts={}, alpha=RULES.alpha, B=0, reason="N-selection technical", seed_id=0),
                        prec, per, None, native, dec.as_dict(), dict(support=TECH, strong=TECH, unsupported=TECH), ["stage: technical failure in N-selection (fail-closed; no expansion; no re-evaluation)"],
                        dict(failed_record=dict(kind="N_selection_technical_failure", systems=which.split(), reevaluated=False, rescued_by_expansion=False), expansion=dict(matched=sel_m, native=sel_n), thresholds=(t1, t2)), dict(state="position_not_evaluated_due_to_N_selection_failure"))

    if fam_matched.grid_identity is not None: r.evidence["grid_identity"] = copy.deepcopy(fam_matched.grid_identity)
    if fam_native is not None and fam_native.grid_identity is not None:
        r.native["evidence"] = {"grid_identity": copy.deepcopy(fam_native.grid_identity)}
    return r


def evaluate_family_staged(fam_matched: FamilyInput, fam_native: Optional[FamilyInput], t1: float, t2: float, position_of: Optional[Dict[int, int]] = None, w2_result=None) -> FamilyResult:
    """Registered staging: (1) per-SYSTEM N-selection on Q/precision only (matched and native keep their own evaluation IDs, stages and expansion evidence);
    (2) ONE final evaluate_family at the selected stages (KDE/core computed once; technical failures of the final evaluation are retained, never healed by the expansion);
    (3) optional position status (rules §10 table 6) from the final per-config results when a position map is supplied — recorded in the result, core truths are preserved for the 3-position stage."""
    _check_systems(fam_matched, fam_native)
    sel_m = _stage_selection(fam_matched, t1, t2); sel_n = _stage_selection(fam_native, t1, t2) if fam_native is not None else None
    if sel_m["technical"] or (sel_n is not None and sel_n["technical"]):
        return _failed_result(fam_matched, fam_native, sel_m, sel_n, t1, t2)
    r = evaluate_family(_stage_family(fam_matched, sel_m["stages"]), (None if fam_native is None else _stage_family(fam_native, sel_n["stages"])), t1, t2)
    for e, note in sel_m.get("notes", {}).items(): r.per_config[e]["stage_note"] = note
    if sel_n is not None:
        for e, note in sel_n.get("notes", {}).items(): r.native["per_config"][e]["stage_note"] = note
    r.notes.append("stage: matched " + ",".join(f"{e}:{s}" for e, s in sel_m["stages"].items()) + ("" if sel_n is None else " | native " + ",".join(f"{e}:{s}" for e, s in sel_n["stages"].items())))
    r.evidence["expansion"] = dict(matched=sel_m, native=sel_n, rule="per-system single expansion on Q precision only; KDE/core evaluated once at the final stages")
    if position_of is not None:
        from .positions import position_decision, VerifiedW2Decision, W2NotEvaluated
        P = position_probabilities(r, position_of)
        if w2_result is None: w2 = W2NotEvaluated("W2 assets not supplied")
        elif isinstance(w2_result, (VerifiedW2Decision, W2NotEvaluated)): w2 = w2_result
        else: raise InputContractError("w2_result must be a replay-verified VerifiedW2Decision or an explicit W2NotEvaluated marker (raw dicts are not accepted)")
        st = position_decision(w2, P, tech_fail=(r.decision["technical_status"] == "technical_fail")); r.evidence["position"] = dict(P=P, w2=(asdict(w2) if hasattr(w2, "__dataclass_fields__") else w2), decision=st)
        r.notes.append(f"position status: {st['state']} (3-position core truths preserved; final label after the registered 12-position stage if expanded)")
        r.position_status = st
    else: r.position_status = dict(state="not-integrated", reason="no position map supplied")
    return r


def position_probabilities(result: FamilyResult, position_of: Dict[int, int]) -> Dict[int, dict]:
    """Build the PositionProbability inputs (P, hits, precision, stage) from the per-config results, mapping evaluation_id -> position id (three positions of one shape)."""
    out = {}
    for e, pos in position_of.items():
        d = result.per_config[e]; out[pos] = dict(P=d["P_model"], hits=d["hits_M"], N=d["N"], precision=d["precision"]["state"], stage=d["stage"])
    return out


def _w2_from_context(w2_context, expected_context_sha256, keys):
    """Formal W2 intake: a validated W2Context snapshot (expected SHA required) supplies one typed decision per case key; missing cases are an error, never a silent W2NotEvaluated."""
    from .w2_context import W2Context
    if not isinstance(w2_context, W2Context): raise InputContractError("w2_context must be a W2Context")
    if expected_context_sha256 is None: raise InputContractError("formal W2 intake requires the trusted expected context SHA")
    w2_context.validate(expected_context_sha256)
    out = {}
    for k in keys:
        if k not in w2_context.decisions: raise InputContractError(f"case {k!r} has no decision in the bound W2 context (missing cases are not evaluated as W2NotEvaluated)")
        out[k] = w2_context.decision_for(k, expected_context_sha256)
    return out, dict(asset_sha256=w2_context.asset_sha256, context_sha256=expected_context_sha256, scope=w2_context.scope)



def _w2_context_for_inputs(families, staged, position_maps, w2_context, expected_context_sha256):
    """Current scope is one 3-position case per key. Fail before evaluation when the
    case request disagrees with supplied FamilyInput metadata or cannot be consumed.
    This does not infer a physical bank/observer binding absent from input metadata.
    """
    if staged is not True:
        raise InputContractError("w2_context requires staged=True; it must not be silently ignored")
    if not isinstance(families, dict) or not families:
        raise InputContractError("W2 context evaluation requires a non-empty case input dict")
    if not isinstance(position_maps, dict) or set(position_maps) != set(families):
        raise InputContractError("every requested W2 case requires an explicit position map (exact inventory)")
    decisions, binding = _w2_from_context(w2_context, expected_context_sha256, list(families))
    case_info = {}
    for key, pair in families.items():
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise InputContractError("each W2 case input must be (matched, native-or-None)")
        fm, fn = pair
        fam, size = w2_context.identities[key]
        for f in (fm, fn):
            if f is None: continue
            if not isinstance(f, FamilyInput) or f.family != fam:
                raise InputContractError("W2 case family differs from the evaluated FamilyInput")
            if f.grid_identity is not None:
                gi = f.grid_identity
                if not isinstance(gi, dict) or gi.get("sizes") != [size]:
                    raise InputContractError("W2 case size differs from the evaluated input's declared single-size scope")
        if fm is None: raise InputContractError("matched input is required")
        pm = position_maps[key]
        is_int = lambda x: isinstance(x, (int, np.integer)) and not isinstance(x, (bool, np.bool_))
        if not isinstance(pm, dict) or not all(is_int(x) for x in list(pm) + list(pm.values())):
            raise InputContractError("position map must contain non-bool integer IDs")
        ids = [c.evaluation_id for c in fm.configs]
        pos_ids = {p["position_id"] for p in w2_context.manifests[key].positions}
        if len(ids) != 3 or set(pm) != set(ids) or len(pm) != len(ids) or set(pm.values()) != pos_ids or len(set(pm.values())) != 3:
            raise InputContractError("one-case position map must cover all three evaluated configurations and the W2 manifest positions")
        case_info[key] = dict(family=fam, size_id=size,
            manifest_sha256=w2_context.manifests[key].payload_sha(),
            decision_checksum=decisions[key].checksum,
            input_identity_scope=("family and declared grid size" if fm.grid_identity is not None else "family and caller-declared test case; physical size binding not verified"))
    return decisions, dict(binding, cases=case_info, evaluation_scope="case-level W2/ratio status; family coordinator and 12-position eligibility not integrated")


def evaluate_threshold(families: Dict[str, Tuple[FamilyInput, Optional[FamilyInput]]], t1: float, t2: float, staged: bool = False, position_maps: Optional[Dict[str, Dict[int, int]]] = None, w2_results: Optional[Dict[str, dict]] = None, w2_context=None, expected_context_sha256: Optional[str] = None) -> Dict[str, FamilyResult]:
    if not (isinstance(t1, (int, float)) and isinstance(t2, (int, float)) and math.isfinite(float(t1)) and math.isfinite(float(t2))): raise InputContractError("threshold must be finite")
    binding = None
    if w2_context is not None:
        if w2_results is not None: raise InputContractError("pass either w2_results (explicit typed decisions) or w2_context, not both")
        w2_results, binding = _w2_context_for_inputs(families, staged, position_maps, w2_context, expected_context_sha256)
    out = {}
    for name, (fm, fn) in families.items():
        if staged:
            r = evaluate_family_staged(fm, fn, float(t1), float(t2), (position_maps or {}).get(name), (w2_results or {}).get(name))
            if binding is not None and name in (position_maps or {}): r.evidence["w2_context"] = dict(binding, case=name)
            out[name] = r
        else: out[name] = evaluate_family(fm, fn, float(t1), float(t2))
    return out


def calibrate_pseudo(families, pseudo_T1, pseudo_T2, level: str = "support", expected_n: Optional[int] = None, staged: bool = False, position_maps=None, w2_results=None, w2_context=None, expected_context_sha256: Optional[str] = None):
    """Scope: with position_maps/w2_results absent the aggregated truths are CORE-ONLY (position eligibility not integrated) and the summary says so; this is not the registered full-procedure calibration."""
    if level not in ("support", "strong"): raise InputContractError("level must be 'support' or 'strong'")
    a = np.asarray(pseudo_T1, float); b = np.asarray(pseudo_T2, float)
    if a.ndim != 1 or b.ndim != 1 or a.shape != b.shape or a.size == 0 or not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))): raise InputContractError("pseudo T1/T2 must be non-empty, finite, 1-D and of equal length")
    thr = RULES.usable_support if level == "support" else RULES.usable_strong; truths = []; scopes = set(); binding = None
    if w2_context is not None:
        if w2_results is not None: raise InputContractError("pass either w2_results or w2_context, not both")
        _, binding = _w2_context_for_inputs(families, staged, position_maps, w2_context, expected_context_sha256); w2_ctx_snapshot = w2_context.snapshot()   # fixed at the start; re-validated against the same expected SHA at every pseudo
    for x, y in zip(a, b):
        res = evaluate_threshold(families, float(x), float(y), staged=staged, position_maps=position_maps, w2_results=w2_results, w2_context=(w2_ctx_snapshot if w2_context is not None else None), expected_context_sha256=expected_context_sha256); truths.append(any_family_truth([r.truths[level] for r in res.values()]))
        for r in res.values():
            ps = (r.position_status or {}).get("state", "not-integrated"); scopes.add("core-only / position-not-integrated" if ps in ("not-integrated", "position_not_evaluated_due_to_N_selection_failure") else "core + 3-position status recorded (12-position stage not integrated)")
    if w2_context is not None: w2_ctx_snapshot.validate(expected_context_sha256)
    summ = calibrate(truths, thr, expected_n=(len(a) if expected_n is None else expected_n)); summ.w2_context = copy.deepcopy(binding); summ.reason = "scope: " + " | ".join(sorted(scopes)) + ("" if binding is None else f" | w2_context asset={binding['asset_sha256'][:16]} context={binding['context_sha256'][:16]} ({binding['scope']})"); return summ, truths
