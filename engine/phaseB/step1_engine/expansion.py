# -*- coding: utf-8 -*-
"""N0 -> 4N0 expansion decision (rules §6.5, table 4) with strict input contracts: registered precision states only, integer hits (NumPy ints normalised, bool rejected,
fractional/negative rejected), non-empty family inventory, 'pass' with zero hits is inconsistent (rejected). Expansion is triggered ONLY by an unmet precision gate,
ONCE (total 4N0), per configuration; unresolved points are retained (never deleted / renormalised / called unsupported)."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict
import numpy as np
from .errors import InputContractError
from .rules_config import RULES

STAGES = ("N0", "N4"); PRECISION_STATES = ("pass", "precision-unresolved", "cv_undefined", "technical_fail")


def norm_hits(h, name="hits") -> int:
    if isinstance(h, (bool, np.bool_)) or not isinstance(h, (int, np.integer)): raise InputContractError(f"{name} must be a non-negative integer (got {h!r})")
    if int(h) < 0: raise InputContractError(f"{name} must be non-negative")
    return int(h)


def norm_stage(stage: str) -> str:
    if stage not in STAGES: raise InputContractError("stage must be 'N0' or 'N4'")
    return stage


def norm_precision(state) -> str:
    if state not in PRECISION_STATES: raise InputContractError(f"unregistered precision state {state!r}")
    return state


@dataclass
class ExpansionDecision:
    evaluation_id: int; stage: str; precision_state: str; hits_model: int; hits_ref: int; action: str; reason: str
    def as_dict(self): return asdict(self)


def expansion_decision(evaluation_id: int, stage: str, precision_state: str, hits_model, hits_ref) -> ExpansionDecision:
    stage = norm_stage(stage); st = norm_precision(precision_state); hm, hr = norm_hits(hits_model, "hits_model"), norm_hits(hits_ref, "hits_ref")
    if st == "technical_fail": return ExpansionDecision(evaluation_id, stage, st, hm, hr, "technical_fail", "technical failure is not a precision shortfall; no expansion")
    if st == "pass":
        if hm == 0 or hr == 0: raise InputContractError("precision 'pass' with zero hits is inconsistent (the gate requires >= 50 positive clusters)")
        return ExpansionDecision(evaluation_id, stage, st, hm, hr, "keep", "precision gate met")
    zero = (hm == 0 or hr == 0)
    if stage == "N0": return ExpansionDecision(evaluation_id, stage, st, hm, hr, "expand_to_4N0", "precision gate not met at N0: single registered expansion" + (" (zero hits)" if zero else ""))
    return ExpansionDecision(evaluation_id, stage, st, hm, hr, "precision-unresolved", "gate not met after the single expansion" + ("; zero hits remain -> unresolved (not a proof of zero probability)" if zero else ""))


def family_expansion_plan(per_config: Dict[int, dict], stage: str, expected_ids=None) -> dict:
    """per_config: evaluation_id -> dict(precision=dict(state=...), hits_M, hits_I[, stage]). Non-empty; expected_ids (if given) must match exactly."""
    stage = norm_stage(stage)
    if not per_config: raise InputContractError("empty family: no configurations to plan")
    if expected_ids is not None and set(per_config) != set(expected_ids): raise InputContractError("configuration inventory mismatch")
    acts = {}
    for eid, d in per_config.items():
        st = d.get("stage", stage)
        if st != stage: raise InputContractError(f"configuration {eid} is at stage {st}, plan requested for {stage}")
        acts[eid] = expansion_decision(eid, stage, d["precision"]["state"], d["hits_M"], d["hits_I"])
    if any(a.action == "technical_fail" for a in acts.values()): status = "technical_fail"
    elif any(a.action == "expand_to_4N0" for a in acts.values()): status = "expansion_pending"
    elif any(a.action == "precision-unresolved" for a in acts.values()): status = "precision-unresolved"
    else: status = "resolved"
    return dict(stage=stage, family_status=status, actions={eid: a.as_dict() for eid, a in acts.items()}, N0=RULES.N0, N_max=RULES.N_max, rule="expand once, precision-only, per configuration; unresolved points retained with their weight")
