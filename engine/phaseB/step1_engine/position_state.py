# -*- coding: utf-8 -*-
"""Observer-position expansion trigger state machine (rules §10.2 table 6). Precedence: technical_fail > valid True > both False > unresolved."""
from __future__ import annotations
from .truth import UNKNOWN, TECH, norm_truth
from .errors import InputContractError


def position_state(w2_trigger, ratio_trigger, tech_fail: bool = False, zero_hit_expansion: bool = False) -> dict:
    w, r = norm_truth(w2_trigger), norm_truth(ratio_trigger)
    if not isinstance(tech_fail, bool) or not isinstance(zero_hit_expansion, bool): raise InputContractError("flags must be bool")
    if tech_fail or w == TECH or r == TECH: return dict(state="technical_fail", expand=False, reason="technical audit FAIL is not cancelled by the OR")
    if w is True or r is True:
        return dict(state="position-sensitive", expand=True, reason="valid True branch", expansion_due_to_zero_hits=zero_hit_expansion)
    if w is False and r is False: return dict(state="not-expanded", expand=False, reason="both False")
    return dict(state="position-unresolved", expand=False, reason="no valid True; at least one unresolved")


def after_twelve_positions(old_state: dict, new_stage_core_ok) -> dict:
    ok = norm_truth(new_stage_core_ok)
    if ok is True: avail = True
    elif ok is False: avail = False
    else: avail = ok                                                           # 'unknown' / 'technical_fail' propagate; never bool('unknown')
    return dict(old_position_status="resolved_by_registered_expansion", final_classification_available=avail, reason="12-position completion does not exempt new-stage Q precision / KDE audit / technical FAIL")
