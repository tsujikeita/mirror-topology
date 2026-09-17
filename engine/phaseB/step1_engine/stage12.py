# -*- coding: utf-8 -*-
"""12-position stage (rules §10.4): nested design (frozen 3 anchors + 9 registered greedy-maximin points), equal weights 1/12, a full-precision manifest with ONE canonical
payload used for generation, storage, restoration and verification, and typed transition / completion records with identity (family, size, manifest SHA), registered state
enum, state/expand consistency and TECH precedence. Completion of the 12-position stage resolves ONLY the old position status; whether a final label may be issued is a
separate eligibility (new-stage coverage, precision, core technical status, declared position state) and the calibration 'usable' condition is NOT verified here
(scope is stated in the returned record). The 3-position truths are never modified. No additional W2 trigger is defined for the 12-position stage (rules: the 3-position
W2/ratio decides the expansion; the 12-position stage is a mixture evaluation)."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Optional
import hashlib, json, math
import numpy as np
from .errors import InputContractError
from .rules_config import RULES
from .observers12 import greedy_maximin, lattice_1d, dist_euclid, dist_torus_halfturn, min_pairwise
from . import serialization as ser

BOX = {"E7": [[0.02, 0.23]], "E2": [[0.0, 1.0], [0.0, 1.0]], "E8": [[0.03, 0.47], [0.02, 0.23]]}
N_TOTAL = 12; N_ANCHORS = 3
POSITION_STATES = ("position-sensitive", "not-expanded", "position-unresolved", "technical_fail")
GENERATOR = dict(kind="greedy_maximin", grid_resolution=RULES.grid_resolution, tie_tol=RULES.tie_tol)


def _candidates(family: str) -> np.ndarray:
    axes = [lattice_1d(lo, hi, RULES.grid_resolution) for lo, hi in BOX[family]]
    if len(axes) == 1: return axes[0][:, None]
    g = np.meshgrid(*axes, indexing="ij"); return np.column_stack([a.ravel() for a in g])


def _exclusion(family: str, cand: np.ndarray) -> np.ndarray:
    if family != "E2": return cand
    fixed = np.array([[0, 0], [0, .5], [.5, 0], [.5, .5]]); keep = np.ones(len(cand), bool)
    for f in fixed: keep &= dist_torus_halfturn(cand, f) >= 0.05
    return cand[keep]


def canonical_payload(family, size_id, anchors, added, weights, min_sep, min_pairwise_val, generator) -> dict:
    """The single canonical payload: every stored field is part of it (no unhashed duplicate fields)."""
    return dict(family=family, size_id=size_id, anchors=[[float(x) for x in a] for a in anchors], added=[[float(x) for x in a] for a in added], weights=[float(w) for w in weights], min_sep=float(min_sep),
                min_pairwise=float(min_pairwise_val), generator=dict(generator))


def payload_sha(payload: dict) -> str: return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


@dataclass
class TwelvePositionManifest:
    family: str; size_id: str; anchors: List[List[float]]; added: List[List[float]]; points: List[List[float]]; weights: List[float]; min_sep_registered: float; min_pairwise: float
    generator: dict; sha256: str = ""
    def as_dict(self): return ser.to_jsonable(asdict(self))
    def payload(self) -> dict: return canonical_payload(self.family, self.size_id, self.anchors, self.added, self.weights, self.min_sep_registered, self.min_pairwise, self.generator)


STREAMED_FAMILIES = ("E2",)   # the registered 1e-4 lattice of E2 (10001 x 10001 candidates) is generated block-wise; the selection rule is identical (two-pass global maximum, TIE_TOL lexicographic)


def _n_candidates(family: str) -> int:
    n = 1
    for lo, hi in BOX[family]: n *= len(lattice_1d(lo, hi, RULES.grid_resolution))
    return n


def _select(family: str, A: np.ndarray, ms: float, dist):
    if family in STREAMED_FAMILIES:
        from .observers12_stream import greedy_maximin_streamed
        ax = [lattice_1d(lo, hi, RULES.grid_resolution) for lo, hi in BOX[family]]
        pts = greedy_maximin_streamed(ax[0], ax[1], A, N_TOTAL - N_ANCHORS, ms, dist, exclusion=(lambda blk: _exclusion(family, blk)), rows_per_block=200)
        return pts, dict(backend="streamed_two_pass", candidates_lattice=int(_n_candidates(family)))
    cand = _exclusion(family, _candidates(family)); return greedy_maximin(cand, A, N_TOTAL - N_ANCHORS, ms, dist), dict(backend="in_memory", candidates=int(len(cand)))


def generate_twelve(family: str, size_id: str, anchors: np.ndarray) -> TwelvePositionManifest:
    if family not in BOX: raise InputContractError(f"family {family} has no registered 12-position design (E1 is observer-homogeneous)")
    if not isinstance(size_id, str) or not size_id: raise InputContractError("size_id must be a non-empty string")
    A = np.asarray(anchors, float)
    if A.shape != (N_ANCHORS, len(BOX[family])): raise InputContractError("anchors must be the frozen 3 reduced-coordinate points of this family")
    dist = dist_torus_halfturn if family == "E2" else dist_euclid; ms = RULES.min_sep[family]
    pts, binfo = _select(family, A, ms, dist); mp = float(min_pairwise(pts, dist))
    if len(pts) != N_TOTAL or mp < ms: raise InputContractError("generator post-check failed")
    gen = dict(GENERATOR, distance=("torus_halfturn" if family == "E2" else "euclid"), candidates=int(binfo.get("candidates", binfo.get("candidates_lattice"))), backend=binfo["backend"])
    pl = canonical_payload(family, size_id, A.tolist(), pts[N_ANCHORS:].tolist(), [1.0 / N_TOTAL] * N_TOTAL, ms, mp, gen)
    return TwelvePositionManifest(family, size_id, pl["anchors"], pl["added"], pl["anchors"] + pl["added"], pl["weights"], ms, mp, gen, payload_sha(pl))


def _structural_checks(man: TwelvePositionManifest) -> bool:
    """(1) structural identities of the stored object; (2) stored SHA == SHA of the canonical payload rebuilt from the stored fields."""
    if not isinstance(man, TwelvePositionManifest): raise InputContractError("manifest type")
    if man.family not in BOX or not isinstance(man.size_id, str) or not man.size_id: raise InputContractError("manifest family/size invalid")
    A, D, P = man.anchors, man.added, man.points
    if len(A) != N_ANCHORS or len(D) != N_TOTAL - N_ANCHORS or len(P) != N_TOTAL or P != A + D: raise InputContractError("points must equal anchors + added (3 + 9 = 12)")
    if len(man.weights) != N_TOTAL or any(not math.isclose(w, 1.0 / N_TOTAL, rel_tol=0, abs_tol=1e-15) for w in man.weights): raise InputContractError("weights must be 1/12 each")
    if man.min_sep_registered != RULES.min_sep[man.family]: raise InputContractError("min_sep_registered differs from the registered value")
    dist = dist_torus_halfturn if man.family == "E2" else dist_euclid; mp = float(min_pairwise(np.asarray(P, float), dist))
    if not math.isclose(mp, float(man.min_pairwise), rel_tol=0, abs_tol=1e-15) or mp < man.min_sep_registered: raise InputContractError("stored min_pairwise does not equal the value recomputed from the points (or violates min_sep)")
    exp_gen = dict(GENERATOR, distance=("torus_halfturn" if man.family == "E2" else "euclid"), backend=("streamed_two_pass" if man.family in STREAMED_FAMILIES else "in_memory"))
    if not isinstance(man.generator, dict) or any(man.generator.get(k) != v for k, v in exp_gen.items()) or not isinstance(man.generator.get("candidates"), int) or man.generator["candidates"] <= 0: raise InputContractError("generator settings differ from the registered generator")
    if payload_sha(man.payload()) != man.sha256: raise InputContractError("stored SHA does not equal the SHA of the canonical payload rebuilt from the stored fields")
    return True


def verify_twelve(man: TwelvePositionManifest) -> bool:
    """Full verification: structural checks + (3) regeneration from the stored anchors reproduces the same canonical payload (determinism / drift)."""
    _structural_checks(man)
    again = generate_twelve(man.family, man.size_id, np.asarray(man.anchors, float))
    if again.payload() != man.payload() or again.sha256 != man.sha256: raise InputContractError("12-position manifest does not reproduce from its anchors (drift or edited manifest)")
    return True


def verify_twelve_registered(man: TwelvePositionManifest) -> bool:
    """Consumer entry: reuse the intake-verified asset (no regeneration) when the manifest SHA was verified in this process, else the full regeneration check."""
    from .twelve_assets import verify_twelve_cached
    return verify_twelve_cached(man)


def _check_position_decision(pd: dict) -> tuple:
    if not isinstance(pd, dict) or pd.get("state") not in POSITION_STATES: raise InputContractError(f"position decision state must be one of {POSITION_STATES}")
    ex = pd.get("expand")
    if not isinstance(ex, bool): raise InputContractError("position decision expand must be bool")
    if (pd["state"] == "position-sensitive") != ex: raise InputContractError("state/expand inconsistency (position-sensitive <=> expand=True)")
    return pd["state"], ex


def _result_identity(res: dict, family: str, size_id: str, what: str):
    if not isinstance(res, dict): raise InputContractError(f"{what} must be a result dict")
    if res.get("family") != family or res.get("size_id") != size_id: raise InputContractError(f"{what} family/size_id do not match the transition ({family}, {size_id})")
    return res


@dataclass
class StageTransition:
    """Typed transition record for one family x size after the 3-position stage (identity-bound; phase is machine-readable)."""
    family: str; size_id: str; three_position_result_sha256: str; three_technical_status: str; position_state: str; expand: bool
    phase: str                      # 'final_at_3' | 'twelve_registered' | 'provisional_unresolved' | 'technical_fail'
    status: str; twelve_manifest_sha256: Optional[str]; note: str
    def as_dict(self): return asdict(self)

    def validate(self) -> bool:
        """Validate an issued or restored record before consuming it.

        This is a schema/internal-state check, not proof of issuance or a
        replacement for external archive/manifest binding. Display text is
        deliberately not parsed as a machine state.
        """
        if not isinstance(self.family, str) or self.family not in (*BOX, "E1"):
            raise InputContractError("transition family unregistered")
        if not isinstance(self.size_id, str) or not self.size_id:
            raise InputContractError("transition size_id must be a non-empty string")
        if not isinstance(self.expand, bool):
            raise InputContractError("transition expand must be bool")
        if self.three_technical_status not in ("ok", "technical_fail"):
            raise InputContractError("transition three_technical_status unregistered")
        if self.position_state not in POSITION_STATES:
            raise InputContractError("transition position_state unregistered")
        if not isinstance(self.phase, str):
            raise InputContractError("transition phase must be str")
        expected = ("technical_fail" if self.three_technical_status == "technical_fail"
                    or self.position_state == "technical_fail" else
                    {"position-sensitive": "twelve_registered",
                     "not-expanded": "final_at_3",
                     "position-unresolved": "provisional_unresolved"}[self.position_state])
        if self.phase != expected or self.expand != (expected == "twelve_registered"):
            raise InputContractError("transition source/state/phase/expand inconsistent")
        def valid_sha(value):
            return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
        if not valid_sha(self.three_position_result_sha256):
            raise InputContractError("transition archive SHA must be a lowercase SHA256")
        if expected == "twelve_registered":
            if self.family == "E1" or not valid_sha(self.twelve_manifest_sha256):
                raise InputContractError("registered twelve transition requires an applicable family and manifest SHA256")
        elif self.twelve_manifest_sha256 is not None:
            raise InputContractError("non-twelve transition must not bind a twelve manifest")
        return True


def _issue_transition(*args) -> StageTransition:
    out = StageTransition(*args)
    out.validate()
    return out


def transition_after_three(family: str, size_id: str, three_position_result: dict, position_decision: dict, twelve: Optional[TwelvePositionManifest]) -> StageTransition:
    """Archive the 3-position result (hash of its strict-JSON bytes) and combine: source technical status (TECH precedence) + registered position state + manifest identity."""
    if family not in BOX and family != "E1": raise InputContractError("unknown family")
    src = _result_identity(three_position_result, family, size_id, "three_position_result"); sha = hashlib.sha256(ser.dumps(src).encode()).hexdigest()
    tech_src = (src.get("decision") or {}).get("technical_status")
    if tech_src not in ("ok", "technical_fail"): raise InputContractError("three_position_result.decision.technical_status must be 'ok' or 'technical_fail'")
    st, ex = _check_position_decision(position_decision)
    if tech_src == "technical_fail" or st == "technical_fail":
        return _issue_transition(family, size_id, sha, tech_src, st, False, "technical_fail", "technical_fail", None, "3-position result archived; technical failure has precedence over any position status")
    if st == "position-sensitive":
        if twelve is None: raise InputContractError("position-sensitive family requires the registered 12-position manifest before the final classification")
        verify_twelve_registered(twelve)
        if twelve.family != family or twelve.size_id != size_id: raise InputContractError(f"12-position manifest identity ({twelve.family}, {twelve.size_id}) does not match the transition ({family}, {size_id})")
        return _issue_transition(family, size_id, sha, tech_src, st, True, "twelve_registered", "provisional / position-sensitive (final classification after the 12-position stage)", twelve.sha256, "3-position result archived; 12-position stage registered (mixture evaluation; no new W2 trigger)")
    if st == "not-expanded": return _issue_transition(family, size_id, sha, tech_src, st, False, "final_at_3", "final at 3 positions", None, "3-position result archived")
    return _issue_transition(family, size_id, sha, tech_src, st, False, "provisional_unresolved", "provisional / position-unresolved", None, "3-position result archived; position status unresolved")


def after_twelve(transition: StageTransition, twelve_result: dict, new_position_state: str) -> dict:
    """Completion record of the registered 12-position stage. Resolves ONLY the old position status. `final_classification_available` is True only when: the transition is a
    registered 12-position transition (expand=True, manifest present), the 12-position result is identity-bound to the same family/size and manifest, its coverage is True,
    its core decision is not technical, its precision passes, and the declared new position state is a registered non-technical state. Calibration 'usable' is NOT checked
    here (scope field). Detected technical states are retained, never converted."""
    if not isinstance(transition, StageTransition): raise InputContractError("transition type")
    transition.validate()
    if transition.phase != "twelve_registered" or not transition.expand or transition.twelve_manifest_sha256 is None: raise InputContractError("no registered 12-position transition (completion undefined)")
    res = _result_identity(twelve_result, transition.family, transition.size_id, "twelve_result"); ev = res.get("evidence") or {}
    if ev.get("stage") != "12-position": raise InputContractError("twelve_result must be tagged as a 12-position stage evaluation")
    if ev.get("twelve_manifest_sha256") != transition.twelve_manifest_sha256: raise InputContractError("twelve_result is not bound to the registered 12-position manifest")
    if new_position_state not in POSITION_STATES: raise InputContractError(f"new_position_state must be one of {POSITION_STATES}")
    cov = ev.get("coverage_ok")
    if not isinstance(cov, bool): raise InputContractError("twelve_result.evidence.coverage_ok (bool) required")
    tech = (res.get("decision") or {}).get("technical_status")
    if tech not in ("ok", "technical_fail"): raise InputContractError("twelve_result.decision.technical_status must be 'ok' or 'technical_fail'")
    prec = (res.get("precision") or {}).get("state")
    if prec not in ("pass", "precision-unresolved", "cv_undefined", "technical_fail"): raise InputContractError("twelve_result.precision.state unregistered")
    technical = (tech == "technical_fail") or (prec == "technical_fail") or (new_position_state == "technical_fail")
    reasons = []
    if technical: reasons.append("technical_fail retained (core/precision/declared position state)")
    if not cov: reasons.append("coverage_ok=False")
    if prec != "pass": reasons.append(f"precision {prec}")
    final_ok = (not technical) and cov and prec == "pass"
    return dict(old_position_status="resolved_by_registered_expansion", new_stage_position_state=new_position_state, new_stage_technical=technical, local_completion_checks_passed=bool(final_ok), final_classification_available=bool(final_ok), final_label_released=False, blocking_reasons=reasons,
                three_position_archive=transition.three_position_result_sha256, twelve_manifest=transition.twelve_manifest_sha256, scope="LOCAL completion checks of one family x size 12-position result (non-technical, coverage, precision); 'final_classification_available' is an alias of local_completion_checks_passed and NOT a released label: full Q/D predicates, all surviving sizes, position-unresolved/inconclusive display, and calibration 'usable' are NOT verified here (decided by the family coordinator / evaluation / calibration layers)",
                reason="12-position completion does not exempt new-stage coverage / Q precision / KDE audit / technical FAIL")
