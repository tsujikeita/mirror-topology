# -*- coding: utf-8 -*-
"""Family coordinator for the 12-position stage (rules §10.4 (vii), §8.4): expansion is decided per FAMILY — if any surviving size of a family is position-sensitive at the
3-position stage, ALL surviving sizes of that family are expanded to 12 positions (weights (1/3)·(1/12) per configuration when three sizes survive). Family completion requires
a registered transition + a completion record with local checks passed for EVERY surviving size; a single completed size never completes the family. E1 is exempt.
The coordinator only releases the family-level 'eligible for final classification' flag; the label itself still requires the core predicates and calibration 'usable'."""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional
import copy
from .errors import InputContractError
from .stage12 import StageTransition, TwelvePositionManifest, verify_twelve_registered as verify_twelve, after_twelve

EXEMPT = ("E1",)


@dataclass
class FamilyExpansionSet:
    family: str; surviving_sizes: List[str]; transitions: Dict[str, StageTransition]; expand_family: bool; required_manifests: Dict[str, Optional[str]]; status: str; reasons: List[str] = field(default_factory=list)
    def as_dict(self): return dict(family=self.family, surviving_sizes=list(self.surviving_sizes), transitions={k: v.as_dict() for k, v in self.transitions.items()}, expand_family=self.expand_family, required_manifests=dict(self.required_manifests), status=self.status, reasons=list(self.reasons))

    def validate(self):
        """Internal schema only; does not authenticate the external size registry."""
        if self.family not in ("E1", "E2", "E7", "E8"):
            raise InputContractError("unregistered family")
        if (not isinstance(self.surviving_sizes, list) or not self.surviving_sizes
                or not all(isinstance(s, str) and s for s in self.surviving_sizes)
                or len(set(self.surviving_sizes)) != len(self.surviving_sizes)):
            raise InputContractError("nonempty unique surviving size list required")
        if not isinstance(self.expand_family, bool):
            raise InputContractError("expand_family must be bool")
        ids = set(self.surviving_sizes)
        if (not isinstance(self.transitions, dict) or set(self.transitions) != ids
                or not isinstance(self.required_manifests, dict) or set(self.required_manifests) != ids):
            raise InputContractError("family plan inventory mismatch")
        for size, t in self.transitions.items():
            if not isinstance(t, StageTransition):
                raise InputContractError("transition type")
            t.validate()
            if (t.family, t.size_id) != (self.family, size):
                raise InputContractError("family plan transition identity mismatch")
        phases = [t.phase for t in self.transitions.values()]
        if "technical_fail" in phases:
            expected, expand = "technical_fail", False
        elif self.family in EXEMPT:
            expected, expand = "exempt (observer-homogeneous)", False
        elif "twelve_registered" in phases:
            expected, expand = "expansion_registered (all surviving sizes)", True
        else:
            expected, expand = ("provisional / position-unresolved" if "provisional_unresolved" in phases else "final at 3 positions"), False
        if self.status != expected or self.expand_family != expand:
            raise InputContractError("family plan state/expand/source inconsistent")
        def is_sha(x):
            return isinstance(x, str) and len(x) == 64 and all(c in "0123456789abcdef" for c in x)
        for size, sha in self.required_manifests.items():
            if expand:
                if not is_sha(sha):
                    raise InputContractError("family expansion requires a manifest SHA for each size")
                t = self.transitions[size]
                if t.phase == "twelve_registered" and sha != t.twelve_manifest_sha256:
                    raise InputContractError("triggered size manifest mismatch")
            elif sha is not None:
                raise InputContractError("nonexpansion family plan must not register twelve manifests")
        return True


def _issue_family_plan(*args):
    # Snapshot caller-owned mutable StageTransition records.
    plan = FamilyExpansionSet(*copy.deepcopy(args))
    plan.validate()
    return plan



def plan_family_expansion(family: str, surviving_sizes: List[str], transitions: Dict[str, StageTransition], manifests: Optional[Dict[str, TwelvePositionManifest]] = None) -> FamilyExpansionSet:
    """Inputs: the 3-position transitions of EVERY surviving size (exact inventory) and, when the family expands, a verified 12-position manifest for every surviving size."""
    if not isinstance(family, str) or not family: raise InputContractError("family")
    if not surviving_sizes or len(set(surviving_sizes)) != len(surviving_sizes) or not all(isinstance(s, str) and s for s in surviving_sizes): raise InputContractError("surviving_sizes must be a non-empty list of distinct non-empty strings")
    if set(transitions) != set(surviving_sizes): raise InputContractError(f"transitions must cover exactly the surviving sizes {sorted(surviving_sizes)}")
    for s, t in transitions.items():
        if not isinstance(t, StageTransition): raise InputContractError("transition type"); 
        t.validate()
        if t.family != family or t.size_id != s: raise InputContractError(f"transition identity mismatch for size {s}")
    tech = [s for s, t in transitions.items() if t.phase == "technical_fail"]
    if tech: return _issue_family_plan(family, list(surviving_sizes), dict(transitions), False, {s: None for s in surviving_sizes}, "technical_fail", [f"size {s} technical_fail" for s in tech])
    if family in EXEMPT:
        if any(t.phase == "twelve_registered" for t in transitions.values()): raise InputContractError("E1 is observer-homogeneous: no 12-position transition may be registered")
        return _issue_family_plan(family, list(surviving_sizes), dict(transitions), False, {s: None for s in surviving_sizes}, "exempt (observer-homogeneous)", [])
    trig = [s for s, t in transitions.items() if t.phase == "twelve_registered"]
    if not trig:
        unres = [s for s, t in transitions.items() if t.phase == "provisional_unresolved"]
        return _issue_family_plan(family, list(surviving_sizes), dict(transitions), False, {s: None for s in surviving_sizes}, ("provisional / position-unresolved" if unres else "final at 3 positions"), [f"size {s} position-unresolved" for s in unres])
    # family expands: every surviving size needs a verified 12-position manifest (nested design, same family)
    req = {}
    for s in surviving_sizes:
        m = (manifests or {}).get(s)
        if m is None: raise InputContractError(f"family {family} expands (triggered by {trig}); size {s} lacks a 12-position manifest")
        verify_twelve(m)
        if m.family != family or m.size_id != s: raise InputContractError(f"manifest identity mismatch for size {s}")
        t = transitions[s]
        if t.phase == "twelve_registered" and t.twelve_manifest_sha256 != m.sha256: raise InputContractError(f"size {s}: registered transition manifest differs from the supplied manifest")
        req[s] = m.sha256
    return _issue_family_plan(family, list(surviving_sizes), dict(transitions), True, req, "expansion_registered (all surviving sizes)", [f"triggered by size(s) {trig}; non-triggered sizes expanded by the family rule"])


def family_completion(plan: FamilyExpansionSet, twelve_results: Dict[str, dict], new_position_states: Dict[str, str], manifests: Dict[str, TwelvePositionManifest]) -> dict:
    """Family-level completion: every surviving size must have a 12-position result bound to its registered manifest with local completion checks passed.
    Sizes whose 3-position transition was 'final_at_3'/'provisional_unresolved' but were expanded by the family rule are completed against their family-rule manifest."""
    if not isinstance(plan, FamilyExpansionSet): raise InputContractError("family plan type")
    plan.validate()
    if not plan.expand_family: raise InputContractError("family completion requires a registered family expansion")
    if set(twelve_results) != set(plan.surviving_sizes) or set(new_position_states) != set(plan.surviving_sizes) or set(manifests) != set(plan.surviving_sizes): raise InputContractError("completion inputs must cover exactly the surviving sizes")
    per = {}; ok_all = True
    for s in plan.surviving_sizes:
        t = plan.transitions[s]; m = manifests[s]; verify_twelve(m)
        if (m.family, m.size_id) != (plan.family, s): raise InputContractError("completion manifest identity mismatch")
        if m.sha256 != plan.required_manifests[s]: raise InputContractError(f"size {s}: manifest differs from the registered expansion set")
        if t.phase != "twelve_registered":
            # An intact, nontechnical source is expanded administratively by the
            # family rule; the original position state remains in plan.transitions.
            t = StageTransition(t.family, t.size_id, t.three_position_result_sha256,
                t.three_technical_status, "position-sensitive", True, "twelve_registered",
                "provisional / expanded by family rule", m.sha256,
                f"family-rule expansion (3-position state was {t.position_state})")
            t.validate()
        c = after_twelve(t, twelve_results[s], new_position_states[s]); per[s] = c; ok_all &= bool(c["local_completion_checks_passed"])
    return dict(family=plan.family, per_size=per, family_local_completion=ok_all, final_label_released=False, scope="family-level local completion (all surviving sizes); core predicates on the 12-position mixture and calibration 'usable' are decided by the evaluation/calibration layers")
