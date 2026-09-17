# -*- coding: utf-8 -*-
"""12-position stage evaluation (rules §10.4 (iv), §8.1).
(a) Per-size path (diagnostic / completion management): the 12 observer positions of ONE size are 12 configurations of one FamilyInput per system, evaluated with the registered
    procedure (evaluate_family / staged) and tagged '12-position' + manifest SHA for stage12.after_twelve / coordinator.family_completion.
(b) All-size family path (the registered family statistic): all surviving sizes' positions are assembled into ONE FamilyInput per system with weights size_prior(l) x 1/12 (a view via
    dataclasses.replace, never in-place), shared evaluation/fitting plans (CRN) and globally unique evaluation ids; ONE family Q / logD / CI / predicate is computed by the same
    evaluate_family. Per-size Q/logD/CI endpoints are never averaged. Native position mapping is an explicit input (no arithmetic id offset in the formal path)."""
from __future__ import annotations
from dataclasses import dataclass, replace, asdict
from typing import Dict, Optional, Tuple
import math
import numpy as np
from .errors import InputContractError
from .rules_config import RULES
from .orchestrator import FamilyInput, evaluate_family, evaluate_family_staged, FamilyResult
from .stage12 import TwelvePositionManifest, verify_twelve_registered as verify_twelve, N_TOTAL
from . import serialization as ser


def _norm_position_map(position_ids: Dict, ids: set, what: str) -> Dict[int, int]:
    if not isinstance(position_ids, dict) or set(position_ids) != ids: raise InputContractError(f"{what}: position map must cover exactly the evaluation ids")
    out = {}
    for e, v in position_ids.items():
        if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)): raise InputContractError(f"{what}: position index must be a non-bool integer")
        out[int(e)] = int(v)
    if sorted(out.values()) != list(range(N_TOTAL)): raise InputContractError(f"{what}: position indices must be a bijection onto 0..{N_TOTAL - 1}")
    return out


def check_twelve_family_input(fam: FamilyInput, manifest: TwelvePositionManifest, position_ids: Dict[int, int]) -> Dict[int, int]:
    """One system of one size: exactly 12 configurations of the manifest's family, weights 1/12, bijective integer position map; returns the normalised map."""
    verify_twelve(manifest)
    if fam.family != manifest.family or any(c.family != manifest.family for c in fam.configs): raise InputContractError("FamilyInput family differs from the 12-position manifest")
    if len(fam.configs) != N_TOTAL: raise InputContractError(f"12-position stage requires exactly {N_TOTAL} configurations (got {len(fam.configs)})")
    ids = {c.evaluation_id for c in fam.configs}
    if len(ids) != N_TOTAL: raise InputContractError("evaluation ids must be unique")
    pm = _norm_position_map(position_ids, ids, "position_ids")
    w = np.array([c.weight for c in fam.configs], float)
    if not np.allclose(w, 1.0 / N_TOTAL, rtol=0, atol=1e-15): raise InputContractError("12-position stage weights must be exactly 1/12 per position")
    if len({c.system for c in fam.configs}) != 1 or fam.configs[0].system not in ("matched", "native"): raise InputContractError("one system per FamilyInput")
    return pm


@dataclass
class TwelveSizeResult:
    """Archive adapter for a per-size 12-position result: the tagged result dict plus its identity (size, manifest, position maps, scope)."""
    family: str; size_id: str; twelve_manifest_sha256: str; position_ids_matched: Dict[int, int]; position_ids_native: Optional[Dict[int, int]]; result: dict; scope: str
    def as_dict(self):
        # Adapter metadata must agree with an already tagged result; it is not a relabelling API.
        original = ser.from_jsonable(ser.to_jsonable(self.result))
        if self.family != original.get("family"):
            raise InputContractError("archive adapter family differs from embedded result")
        ev = original.get("evidence", {})
        if ev.get("stage") == "12-position":
            if (original.get("size_id") != self.size_id
                    or ev.get("twelve_manifest_sha256") != self.twelve_manifest_sha256
                    or ev.get("position_ids") != self.position_ids_matched
                    or ev.get("position_ids_native") != self.position_ids_native):
                raise InputContractError("archive adapter cannot relabel an already tagged size result")
        d = dict(original); d["size_id"] = self.size_id; d["evidence"] = dict(d["evidence"], stage="12-position", twelve_manifest_sha256=self.twelve_manifest_sha256, position_ids=dict(self.position_ids_matched), position_ids_native=(None if self.position_ids_native is None else dict(self.position_ids_native)), scope=self.scope)
        validate_twelve_archive(d)
        return ser.to_jsonable(d)


def evaluate_twelve_size(fam_matched: FamilyInput, fam_native: Optional[FamilyInput], manifest: TwelvePositionManifest, size_id: str, position_ids: Dict[int, int], t1: float, t2: float, staged: bool = True, native_position_ids: Optional[Dict[int, int]] = None) -> dict:
    """Per-size path. native_position_ids is REQUIRED when a native input is given (explicit mapping; no id-offset inference)."""
    pm = check_twelve_family_input(fam_matched, manifest, position_ids)
    if manifest.size_id != size_id: raise InputContractError("manifest size_id differs from the requested size")
    pn = None
    if fam_native is not None:
        if native_position_ids is None: raise InputContractError("native input requires an explicit native_position_ids map")
        if {c.evaluation_id for c in fam_native.configs} & set(pm): raise InputContractError("native evaluation ids must be distinct from matched ids")
        pn = check_twelve_family_input(fam_native, manifest, native_position_ids)
    r: FamilyResult = (evaluate_family_staged if staged else evaluate_family)(fam_matched, fam_native, t1, t2)
    d = ser.from_jsonable(r.as_dict()); d["size_id"] = size_id
    ev = d["evidence"]; ev["stage"] = "12-position"; ev["twelve_manifest_sha256"] = manifest.sha256; ev["position_ids"] = pm; ev["position_ids_native"] = pn; ev["coverage_ok"] = bool(fam_matched.coverage_ok)
    ev["scope"] = "per-size 12-position mixture (weights 1/12); diagnostic / completion management; NOT the all-size family statistic"
    return d


def _check_size_inputs(size_inputs: Dict[str, Tuple[FamilyInput, Optional[FamilyInput]]], manifests: Dict[str, TwelvePositionManifest], position_ids: Dict[str, Dict[int, int]], native_position_ids: Optional[Dict[str, Dict[int, int]]], expected_sizes=None):
    if not isinstance(size_inputs, dict) or not size_inputs: raise InputContractError("size_inputs must be a non-empty dict")
    if not all(isinstance(s, str) and s for s in size_inputs): raise InputContractError("size ids must be non-empty strings")
    if set(size_inputs) != set(manifests) or set(size_inputs) != set(position_ids): raise InputContractError("size inventory of inputs, manifests and position maps must match exactly")
    if expected_sizes is not None and set(size_inputs) != set(expected_sizes): raise InputContractError("size inventory differs from the registered surviving sizes")
    fams = {manifests[s].family for s in size_inputs} | {fm.family for fm, _ in size_inputs.values()} | {fn.family for _, fn in size_inputs.values() if fn is not None}
    if len(fams) != 1: raise InputContractError(f"one family per entry required (got {sorted(fams)})")
    if any((fn is not None) != (native_position_ids is not None and s in native_position_ids) for s, (fm, fn) in size_inputs.items()): raise InputContractError("native inputs require native_position_ids for exactly the sizes that carry a native input")
    wanted_native = {s for s, (_, fn) in size_inputs.items() if fn is not None}
    if native_position_ids is not None and (not isinstance(native_position_ids, dict)
            or set(native_position_ids) != wanted_native):
        raise InputContractError("native position-map size inventory mismatch")
    for s, pair in size_inputs.items():
        if manifests[s].size_id != s:
            raise InputContractError("manifest size_id differs from its input key")
        for system, f in zip(("matched", "native"), pair):
            if f is None:
                continue
            if not isinstance(f.coverage_ok, (bool, np.bool_)):
                raise InputContractError("coverage_ok must be a boolean, not coerced text")
            if any(c.system != system for c in f.configs):
                raise InputContractError("FamilyInput role mismatch")
    return fams.pop()


def evaluate_twelve_family(size_inputs, manifests, position_ids, t1: float, t2: float, staged: bool = True, native_position_ids=None, expected_sizes=None) -> Dict[str, dict]:
    """Per-size results for all surviving sizes (diagnostic / completion). Exact size inventory; single family; explicit native maps."""
    _check_size_inputs(size_inputs, manifests, position_ids, native_position_ids, expected_sizes)
    if not (isinstance(t1, (int, float)) and isinstance(t2, (int, float)) and math.isfinite(float(t1)) and math.isfinite(float(t2))): raise InputContractError("threshold must be finite")
    return {s: evaluate_twelve_size(fm, fn, manifests[s], s, position_ids[s], float(t1), float(t2), staged, (native_position_ids or {}).get(s)) for s, (fm, fn) in size_inputs.items()}


def assemble_all_sizes(size_inputs, manifests, position_ids, size_weights: Dict[str, float], native_position_ids=None, expected_sizes=None) -> Tuple[FamilyInput, Optional[FamilyInput], dict]:
    """Build ONE FamilyInput per system over all surviving sizes: configuration weight = size_weight(l) x 1/12 (view via replace), shared plans/fit_plans (must be the same objects or
    equal plan ids across sizes: CRN), globally unique evaluation ids, coverage identical across sizes, fitting bindings merged. Returns (matched, native, identity)."""
    family = _check_size_inputs(size_inputs, manifests, position_ids, native_position_ids, expected_sizes)
    if not isinstance(size_weights, dict) or set(size_weights) != set(size_inputs): raise InputContractError("size_weights must cover exactly the sizes")
    native_presence = {fn is not None for _, fn in size_inputs.values()}
    if len(native_presence) != 1:
        raise InputContractError("partial native prior: full-family native mixture is not available")
    # Validate every supplied resource BEFORE selecting shared resources or constructing views.
    reference = None
    for fm, fn in size_inputs.values():
        for f in (fm, fn):
            if f is None:
                continue
            f.validate()
            if reference is None:
                reference = f
            else:
                if set(f.plans) != set(reference.plans) or any(
                    not _same_evaluation_plan(f.plans[k], reference.plans[k]) for k in reference.plans):
                    raise InputContractError("evaluation resampling plans differ within the family CRN group")
                if set(f.fit_plans) != set(reference.fit_plans) or any(
                    not _same_fit_plan(f.fit_plans[k], reference.fit_plans[k]) for k in reference.fit_plans):
                    raise InputContractError("fitting resampling plans differ within the family CRN group")
    sw = np.array([float(size_weights[s]) for s in size_inputs], float)
    if not np.all(np.isfinite(sw)) or np.any(sw < 0) or not np.isclose(sw.sum(), 1.0, rtol=0, atol=1e-12): raise InputContractError("size prior weights must be finite, non-negative and sum to 1")
    out = {}
    for system in ("matched", "native"):
        cfgs, fit, bind, plans, fplans, cov = [], {}, {}, None, None, None
        for s, (fm, fn) in size_inputs.items():
            f = fm if system == "matched" else fn
            if f is None:
                if system == "native": continue
                raise InputContractError("matched input missing")
            pm = check_twelve_family_input(f, manifests[s], position_ids[s] if system == "matched" else native_position_ids[s])
            if plans is None: plans, fplans, cov = f.plans, f.fit_plans, f.coverage_ok
            else:
                if any(f.plans[k].plan_id != plans[k].plan_id or f.plans[k].strata != plans[k].strata for k in plans) or set(f.plans) != set(plans): raise InputContractError("evaluation plans must be shared across sizes (CRN group)")
                if set(f.fit_plans) != set(fplans) or any(not _same_fit_plan(f.fit_plans[k], fplans[k]) for k in fplans): raise InputContractError("fitting plans must be shared across sizes")
                if f.coverage_ok != cov: raise InputContractError("coverage flags differ across sizes of one family")
            for c in f.configs:
                if c.evaluation_id in fit: raise InputContractError(f"evaluation id {c.evaluation_id} reused across sizes/systems")
                cfgs.append(replace(c, weight=float(size_weights[s]) / N_TOTAL)); fit[c.evaluation_id] = f.fitting[c.evaluation_id]
                if f.fitting_bindings: bind[c.evaluation_id] = f.fitting_bindings[c.evaluation_id]
        if system == "native" and not cfgs: out["native"] = None; continue
        out[system] = FamilyInput(family, cfgs, plans, fit, fplans, bool(cov), (bind if bind else None))
    if out["native"] is not None and ({c.evaluation_id for c in out["native"].configs} & {c.evaluation_id for c in out["matched"].configs}): raise InputContractError("native/matched evaluation ids overlap")
    identity = dict(family=family, sizes=list(size_inputs), size_weights={s: float(size_weights[s]) for s in size_inputs}, twelve_manifests={s: manifests[s].sha256 for s in size_inputs}, n_configs=len(out["matched"].configs))
    return out["matched"], out["native"], identity


def _same_evaluation_plan(a, b) -> bool:
    a.validate(); b.validate()
    if (a.plan_id != b.plan_id or a.seed_id != b.seed_id or a.replicates != b.replicates
            or a.strata != b.strata or a.rng_keys != b.rng_keys
            or set(a.multiplicities) != set(b.multiplicities)):
        return False
    return all(np.asarray(a.multiplicities[k]).dtype == np.asarray(b.multiplicities[k]).dtype
               and np.array_equal(a.multiplicities[k], b.multiplicities[k]) for k in a.multiplicities)


def _same_fit_plan(a, b) -> bool:
    if type(a) != type(b):
        return False
    if hasattr(a, "multiplicities_sha256"):
        a.validate(); b.validate()
        fields = ("plan_id", "wave_id", "crn_group_id", "seed_id", "K", "rng_key")
        return (all(getattr(a, k) == getattr(b, k) for k in fields)
                and np.asarray(a.multiplicities).dtype == np.asarray(b.multiplicities).dtype
                and np.array_equal(a.multiplicities, b.multiplicities))
    return np.array_equal(np.asarray(a), np.asarray(b))


def validate_twelve_archive(d: dict) -> bool:
    """Internal consistency of added twelve-stage identity fields only.
    Does NOT verify external coordinates/physical manifests or release final labels.
    """
    ev = d.get("evidence", {}); stage = ev.get("stage")
    if stage not in ("12-position", "12-position-family"):
        return True  # legacy/core result keeps its existing reader contract
    def check_sha(v):
        if not isinstance(v, str) or len(v) != 64 or any(c not in "0123456789abcdef" for c in v):
            raise InputContractError("12-position archive: invalid manifest SHA")
    if stage == "12-position":
        if not isinstance(d.get("size_id"), str) or not d["size_id"]:
            raise InputContractError("12-position archive: invalid size_id")
        check_sha(ev.get("twelve_manifest_sha256"))
        ids = set(d["per_config"])
        if len(ids) != N_TOTAL:
            raise InputContractError("12-position archive: configuration inventory")
        _norm_position_map(ev.get("position_ids"), ids, "archive matched")
        native = d.get("native")
        if native is not None:
            nids = set(native["per_config"])
            if len(nids) != N_TOTAL or nids & ids:
                raise InputContractError("12-position archive: native configuration inventory")
            _norm_position_map(ev.get("position_ids_native"), nids, "archive native")
        elif ev.get("position_ids_native") is not None:
            raise InputContractError("12-position archive: native map without native result")
        return True
    ident = ev.get("identity", {})
    if ident.get("family") != d.get("family"):
        raise InputContractError("12-position-family archive: family identity mismatch")
    sizes = ident.get("sizes")
    if not isinstance(sizes, list) or not sizes or any(not isinstance(s, str) or not s for s in sizes) or len(set(sizes)) != len(sizes):
        raise InputContractError("12-position-family archive: sizes")
    sw = ident.get("size_weights", {}); mans = ident.get("twelve_manifests", {}); per = d.get("per_size_diagnostic", {})
    if set(sw) != set(sizes) or set(mans) != set(sizes) or set(per) != set(sizes):
        raise InputContractError("12-position-family archive: size inventory mismatch")
    weights = np.array([sw[s] for s in sizes], float)
    if not np.all(np.isfinite(weights)) or np.any(weights < 0) or not np.isclose(weights.sum(),1,rtol=0,atol=1e-12):
        raise InputContractError("12-position-family archive: invalid prior")
    expected = {"matched": {}, "native": {}}
    for s in sizes:
        p = per[s];check_sha(mans[s]);validate_twelve_archive(p)
        if (p.get("family") != d.get("family") or p.get("size_id") != s
                or p.get("evidence", {}).get("stage") != "12-position"
                or p["evidence"].get("twelve_manifest_sha256") != mans[s]):
            raise InputContractError("12-position-family archive: per-size identity mismatch")
        for side, part in (("matched",p),("native",p.get("native"))):
            if part is None:continue
            for eid in part["per_config"]:
                if eid in expected[side]:raise InputContractError("configuration id reused across sizes")
                expected[side][eid]=float(sw[s])/N_TOTAL
    if ident.get("n_configs") != len(sizes)*N_TOTAL:
        raise InputContractError("12-position-family archive: n_configs mismatch")
    for side, part in (("matched",d),("native",d.get("native"))):
        if part is None:
            if expected[side]:raise InputContractError("native diagnostics without native family")
            continue
        ids = list(part["per_config"])
        if set(ids) != set(expected[side]):raise InputContractError("family and per-size configuration inventories differ")
        saved = ev["matched"]["prior"] if side=="matched" else part["evidence"]["prior"]
        desired = [expected[side][e] for e in ids]
        if np.asarray(saved).shape != (len(ids),) or not np.allclose(saved,desired,rtol=0,atol=1e-15):
            raise InputContractError("family numeric prior differs from tagged size prior")
    return True


def evaluate_twelve_family_mixture(size_inputs, manifests, position_ids, size_weights, t1: float, t2: float, staged: bool = True, native_position_ids=None, expected_sizes=None) -> dict:
    """The all-size family statistic at the 12-position stage: ONE family Q / logD / CI / predicate over all surviving sizes x 12 positions (registered prior), same procedure as the
    3-position stage. Per-size results are attached as diagnostics only (never averaged into the family value)."""
    gm, gn, ident = assemble_all_sizes(size_inputs, manifests, position_ids, size_weights, native_position_ids, expected_sizes)
    if not (isinstance(t1, (int, float)) and isinstance(t2, (int, float)) and math.isfinite(float(t1)) and math.isfinite(float(t2))): raise InputContractError("threshold must be finite")
    r: FamilyResult = (evaluate_family_staged if staged else evaluate_family)(gm, gn, float(t1), float(t2))
    d = ser.from_jsonable(r.as_dict()); ev = d["evidence"]; ev["stage"] = "12-position-family"; ev["identity"] = ident
    ev["scope"] = "all-size family mixture at the 12-position stage: P/f mixed with size_prior x 1/12 before the ratio; per-size values are diagnostics; calibration 'usable' and position eligibility decided elsewhere"
    d["final_label_released"] = False                                                                      # explicit bool: this result never releases a formal label by itself
    d["per_size_diagnostic"] = evaluate_twelve_family(size_inputs, manifests, position_ids, t1, t2, staged, native_position_ids, expected_sizes)
    return d
