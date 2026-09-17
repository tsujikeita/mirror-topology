# -*- coding: utf-8 -*-
"""Common threshold evaluator (rules §8–§10, §9.2; audit tranche 30 §6 / 31 §9): the SAME procedure for the real target and for every pseudo threshold —
  parent family required quantities (family-mixture core; required logD CI from the family Q only)
  -> per-size position probabilities from the parent per_config + fixed replay-verified W2 decision -> case position status (E1 exempt)
  -> family transitions / coordinator (family rule over all surviving sizes; 12-position manifests from the registry anchors)
  -> when a family is expanded and 12-position inputs are supplied: 12-position family-mixture evaluation + local completion
  -> ELIGIBLE family truths: final-at-3 -> 3-position core truths; expanded & 12-position completed -> 12-position core truths; expanded without 12-position inputs
     or position-unresolved -> provisional (unknown, TECH retained); technical -> TECH.
support and strong are extracted from ONE evaluation; only the Wilson aggregation differs (calibration layer)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import numpy as np
from .errors import InputContractError
from .grid_registry import GridRegistry
from .grid_manifest import ConfigurationManifest
from .orchestrator import FamilyInput, evaluate_threshold, evaluate_family_staged, FamilyResult
from .w2_context import W2Context, canonical_case_key
from .positions import position_decision
from .stage12 import transition_after_three, generate_twelve, POSITION_STATES, after_twelve
from .coordinator import plan_family_expansion, family_completion
from .truth import TECH, UNKNOWN
from . import serialization as ser


@dataclass
class FamilyThresholdResult:
    family: str; parent: FamilyResult; case_records: Dict[str, dict]; diagnostics: Dict[str, FamilyResult]; transitions: dict; plan_status: str; expand_family: bool; required_manifests: dict
    twelve: Optional[dict]; eligible_truths: Dict[str, object]; eligibility: str; core_technical: bool
    def summary(self) -> dict:
        return dict(family=self.family, core_truths=self.parent.truths, core_technical=self.core_technical, plan_status=self.plan_status, expand_family=self.expand_family, eligible_truths=self.eligible_truths, eligibility=self.eligibility, twelve=(None if self.twelve is None else dict(evaluated=True, local_completion=self.twelve.get("family_local_completion"))))


def _case_positions(fr: FamilyResult, fm: FamilyInput, pmap: Dict[int, int]) -> dict:
    per = ser.from_jsonable(fr.as_dict())["per_config"]; ids = [c.evaluation_id for c in fm.configs]
    if any(e not in per for e in ids): raise InputContractError("parent result lacks this size's configurations")
    if set(pmap) != set(ids) or sorted(pmap.values()) != [1, 2, 3]: raise InputContractError("position map must be a bijection of this size's three configurations onto positions 1..3")
    return {pmap[e]: dict(P=per[e]["P_model"], hits=per[e]["hits_M"], N=per[e]["N"], precision=per[e]["precision"]["state"], stage=per[e]["stage"]) for e in ids}


def evaluate_family_full(reg: GridRegistry, man: ConfigurationManifest, family: str, parent: Tuple[FamilyInput, Optional[FamilyInput]], views: Dict[str, Tuple[FamilyInput, Optional[FamilyInput], Dict[int, int]]],
                         w2: Optional[W2Context], expected_context_sha256: Optional[str], t1: float, t2: float, twelve_inputs: Optional[dict] = None, with_diagnostics: bool = True, diagnostic_ref_fn=None, twelve_assets=None) -> FamilyThresholdResult:
    """views: size -> (fm, fn, pmap) for every surviving size; twelve_inputs (optional): dict(size_inputs={size: (fm12, fn12)}, position_ids={size: map}, native_position_ids={size: map}) for the expanded family."""
    if twelve_assets is not None:
        # Pin a complete asset to THIS registry before numerical evaluation.
        twelve_assets = twelve_assets.snapshot(reg)
    sizes = list(reg.surviving[family])
    if set(views) != set(sizes): raise InputContractError(f"family {family}: views must cover the surviving sizes {sizes}")
    pm_, pn_ = parent; fr = evaluate_family_staged(pm_, pn_, t1, t2); core_tech = fr.decision["technical_status"] == "technical_fail"
    diags = {}
    if with_diagnostics and family != "E1":
        keys = {f"{family}/{s}": (views[s][0], views[s][1]) for s in sizes}; maps = {f"{family}/{s}": views[s][2] for s in sizes}
        diags = evaluate_threshold(keys, t1, t2, staged=True, position_maps=maps, w2_context=w2, expected_context_sha256=expected_context_sha256) if w2 is not None else {k: evaluate_family_staged(v[0], v[1], t1, t2) for k, v in keys.items()}
    elif with_diagnostics: diags = {f"{family}/{s}": evaluate_family_staged(views[s][0], views[s][1], t1, t2) for s in sizes}
    records, trans, mans = {}, {}, {}
    for s in sizes:
        fm, fn, pmap = views[s]; key = f"{family}/{s}"
        if family == "E1": st = dict(state="not-expanded", expand=False, reason="E1 observer-homogeneous: position branch exempt", w2_trigger=None, ratio_trigger=None); P_k = {}
        else:
            if w2 is None: raise InputContractError("non-E1 family requires the W2 context")
            P_k = _case_positions(fr, fm, pmap); st = position_decision(w2.decision_for(key, expected_context_sha256), P_k, tech_fail=core_tech)
        rec = dict(family=family, size_id=s, kind="case_position_record", decision=dict(technical_status=fr.decision["technical_status"], display_label=fr.decision["display_label"]), truths=fr.truths, precision=fr.precision, position_status=st,
                   evidence=dict(coverage_ok=fm.coverage_ok, threshold=[t1, t2], position_probabilities={int(k): v for k, v in P_k.items()}, parent_family_result="family_core:" + family, w2_context=(None if family == "E1" else dict(asset_sha256=w2.asset_sha256, context_sha256=expected_context_sha256, case=key)),
                                 scope="position branch derived from the parent family's required quantities; the standalone case core is a diagnostic"))
        if diagnostic_ref_fn is not None and key in diags: rec["evidence"]["diagnostic_ref"] = diagnostic_ref_fn(key, diags[key])     # archived BEFORE the transition hashes the record
        records[key] = rec; state = st.get("state")
        if state not in POSITION_STATES: state = "technical_fail" if (state == "position_not_evaluated_due_to_N_selection_failure" or core_tech) else "position-unresolved"
        tm = None
        if family != "E1" and state == "position-sensitive": tm = (twelve_assets.get(family, s) if twelve_assets is not None else generate_twelve(family, s, np.asarray(reg.anchors[family], float))); mans[s] = tm
        trans[s] = transition_after_three(family, s, rec, dict(state=state, expand=(state == "position-sensitive")), tm)
    if family != "E1" and any(t.phase == "twelve_registered" for t in trans.values()):
        for s in sizes:
            if s not in mans: mans[s] = (twelve_assets.get(family, s) if twelve_assets is not None else generate_twelve(family, s, np.asarray(reg.anchors[family], float)))
    plan = plan_family_expansion(family, sizes, trans, manifests=(mans if mans else None))
    twelve = None; elig = None
    if core_tech: elig, truths = "technical_fail (family core)", dict(support=TECH, strong=TECH, unsupported=TECH)
    elif plan.status == "technical_fail": elig, truths = "technical_fail (position branch)", {k: TECH for k in ("support", "strong", "unsupported")}
    elif plan.expand_family:
        if twelve_inputs is None: elig, truths = "provisional: family expanded to 12 positions, 12-position inputs not supplied", {k: (TECH if v == TECH else UNKNOWN) for k, v in fr.truths.items()}
        else:
            from .twelve_eval import evaluate_twelve_family_mixture
            g = evaluate_twelve_family_mixture(twelve_inputs["size_inputs"], mans, twelve_inputs["position_ids"], {s: reg.size_prior[family][s] for s in sizes}, t1, t2, staged=True, native_position_ids=twelve_inputs.get("native_position_ids"), expected_sizes=sizes)
            # completion records derived from the 12-position PARENT (required quantities only): per-size coverage, technical status, point-precision of that size's 12 configurations;
            # the standalone per-size diagnostics (own Q/KDE/CI) are kept separately and never enter the completion condition (same design as the 3-position case records)
            per_cfg = g["per_config"]; pos_ids = twelve_inputs["position_ids"]; tech12 = g["decision"]["technical_status"] == "technical_fail"; crecs = {}
            for s in sizes:
                ids = list(pos_ids[s]); states = [per_cfg[e]["precision"]["state"] for e in ids]
                prec = "technical_fail" if any(st == "technical_fail" for st in states) else ("pass" if all(st == "pass" for st in states) else "precision-unresolved")
                if g["precision"]["state"] != "pass" and prec == "pass": prec = g["precision"]["state"]            # family-level gate (mixed Q) also applies
                crecs[s] = dict(family=family, size_id=s, kind="twelve_completion_record", decision=dict(technical_status=g["decision"]["technical_status"], display_label=g["decision"]["display_label"]), truths=g["truths"], precision=dict(state=prec, per_configuration=dict(zip(ids, states))),
                                  evidence=dict(stage="12-position", twelve_manifest_sha256=mans[s].sha256, coverage_ok=bool(twelve_inputs["size_inputs"][s][0].coverage_ok), parent="12-position-family", scope="completion record derived from the 12-position family parent's required quantities; per-size standalone diagnostics excluded"))
            comp = family_completion(plan, crecs, {s: "not-expanded" for s in sizes}, mans)
            twelve = dict(family_mixture=dict(truths=g["truths"], decision=g["decision"], precision=g["precision"], Q_point=g["Q_point"]), family_local_completion=comp["family_local_completion"], per_size=comp["per_size"], completion_records=crecs,
                          per_size_diagnostic={s: dict(truths=d["truths"], technical_status=d["decision"]["technical_status"], precision=d["precision"]["state"], Q_point=d["Q_point"]) for s, d in g["per_size_diagnostic"].items()}, twelve_manifests={s: mans[s].sha256 for s in sizes},
                          full_result=g)                                                                   # the complete evaluated 12-position family Result (36 configurations, CIs, evidence) is returned, never dropped
            if tech12: elig, truths = "technical_fail (12-position family core)", {k: TECH for k in ("support", "strong", "unsupported")}
            elif comp["family_local_completion"]: elig, truths = "eligible: 12-position family mixture (local completion passed)", dict(g["truths"])
            else: elig, truths = "provisional: 12-position local completion not passed", {k: (TECH if v == TECH else UNKNOWN) for k, v in g["truths"].items()}
    elif plan.status.startswith("provisional"): elig, truths = "provisional: position-unresolved", {k: (TECH if v == TECH else UNKNOWN) for k, v in fr.truths.items()}
    else: elig, truths = "eligible: final at 3 positions" if family != "E1" else "eligible: E1 (observer-homogeneous)", dict(fr.truths)
    return FamilyThresholdResult(family, fr, records, diags, {s: t.as_dict() for s, t in trans.items()}, plan.status, plan.expand_family, plan.required_manifests, twelve, truths, elig, core_tech)
