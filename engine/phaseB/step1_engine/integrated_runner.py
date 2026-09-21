# -*- coding: utf-8 -*-
"""Integrated first-wave runner (engine spec B4/B-3 preparation; rules §8–§10, §9.2, §13). Responsibilities (audit tranche 29 §4.3):
- family level: the FULL surviving-size FamilyInput per system (assembled from the per-size case views: shared plans/fit plans, distinct evaluation ids, registered size prior x
  position weights, grid identity over all sizes) is gated (official full-size scope) and evaluated ONCE per threshold by the registered staged procedure -> ONE family core truth;
- case level (one size, three positions): position status from that size's position probabilities and the fixed replay-verified W2 decision (E1 exempt: observer-homogeneous, no W2 case);
- family coordinator: transitions of all surviving sizes -> expansion plan (12-position manifests generated from the REGISTRY anchors only and archived; evaluation is a separate step);
- calibration: the COMMON threshold evaluator (threshold_evaluator.evaluate_family_full) for the target and every pseudo — parent required quantities -> per-size position status ->
  coordinator -> optional 12-position evaluation -> ELIGIBLE family truths; support and strong are extracted from that single evaluation and only the Wilson aggregation differs;
  `core_only` (3-position family core without eligibility) and `any_case_core_diagnostic` are recorded as diagnostics;
- fixed inputs: fingerprints of every bank/plan (parent and views) taken BEFORE the gate, re-checked after the target and after the calibration, and stored; pseudo threshold columns
  snapshotted (SHA, shape, n) before use; target threshold validated as finite shape (2,).
No label is released (final_label_released=False)."""
from __future__ import annotations
from dataclasses import dataclass, field, replace
from typing import Dict, Optional, Tuple
import hashlib
import numpy as np
from .errors import InputContractError
from .rules_config import RULES
from .grid_registry import GridRegistry
from .grid_manifest import ConfigurationManifest
from . import orchestrator as _orch
from .orchestrator import FamilyInput, evaluate_threshold, evaluate_family_staged, calibrate_pseudo
from .calibration import calibrate, any_family_truth
from .threshold_evaluator import evaluate_family_full
from .w2_context import W2Context, canonical_case_key
from .official_gate import official_gate, require_official
from .formal_runner import input_fingerprint
from .stage12 import transition_after_three, generate_twelve, POSITION_STATES
from .coordinator import plan_family_expansion
from .archive import Archive, archive_three_position_result
from .checkpoint import binding_manifest
from .truth import TECH, UNKNOWN
from . import serialization as ser
from . import __version__


@dataclass
class RunManifest:
    engine_version: str; mode: str; registry_sha256: str; manifest_sha256: str; w2_context_sha256: str; w2_asset_sha256: str
    families: Dict[str, dict] = field(default_factory=dict); cases: Dict[str, dict] = field(default_factory=dict); calibration: Dict[str, dict] = field(default_factory=dict)
    gates: Dict[str, dict] = field(default_factory=dict); fingerprints: Dict[str, dict] = field(default_factory=dict); thresholds: dict = field(default_factory=dict); archive_refs: Dict[str, dict] = field(default_factory=dict); per_pseudo_family_status: list = field(default_factory=list); branch_completeness: dict = field(default_factory=dict)
    binding: dict = field(default_factory=dict); final_label_released: bool = False
    scope: str = ("first-wave common evaluator: family-mixture core per family, case position status from the parent's quantities, family expansion plan; the 12-position stage is evaluated when its inputs are "
                  "supplied (per family, target and every pseudo) and otherwise left provisional; calibration = eligible family truths (core_only / any_case diagnostics kept separately); no label released")
    def as_dict(self): return ser.to_jsonable(self.__dict__)
    def payload_sha(self) -> str:
        """Canonical payload SHA: excludes the self-referencing binding entries (run_manifest_sha256, file SHA, archive ref) so it reproduces after they are written."""
        d = ser.from_jsonable(self.as_dict()); d["binding"] = {k: v for k, v in d["binding"].items() if k not in ("run_manifest_sha256", "run_manifest_file_sha256", "run_manifest_ref")}
        return hashlib.sha256(ser.dumps(d).encode()).hexdigest()
    def sha256(self) -> str: return self.payload_sha()


def _check_threshold2(t) -> Tuple[float, float]:
    a = np.asarray(t, float)
    if a.shape != (2,) or not np.all(np.isfinite(a)): raise InputContractError("target threshold must be a finite (t1, t2) pair")
    return float(a[0]), float(a[1])


def _pseudo_snapshot(T1, T2) -> dict:
    a = np.array(T1, float, copy=True); b = np.array(T2, float, copy=True)
    if a.ndim != 1 or a.shape != b.shape or a.size == 0 or not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))): raise InputContractError("pseudo threshold columns must be non-empty finite 1-D of equal length")
    a.setflags(write=False); b.setflags(write=False)
    return dict(T1=a, T2=b, n=int(a.size), sha256_T1=hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest(), sha256_T2=hashlib.sha256(np.ascontiguousarray(b).tobytes()).hexdigest(), shape=list(a.shape))


def assemble_parent(reg: GridRegistry, man: ConfigurationManifest, family: str, views: Dict[str, Tuple[FamilyInput, Optional[FamilyInput]]]) -> Tuple[FamilyInput, Optional[FamilyInput]]:
    """Full surviving-size FamilyInput per system from the per-size case views (same plans / fit plans / bindings; registered size prior x position weight; identity over all sizes)."""
    sizes = list(reg.surviving[family])
    if set(views) != set(sizes): raise InputContractError(f"family {family}: views must cover exactly the surviving sizes {sizes}")
    have_native = [views[s][1] is not None for s in sizes]
    if any(have_native) and not all(have_native): raise InputContractError(f"family {family}: native supplied for {[s for s, h in zip(sizes, have_native) if h]} but missing for {[s for s, h in zip(sizes, have_native) if not h]} (partial native is rejected; supply all or none)")
    out = []
    for si in ((0, 1) if all(have_native) else (0,)):
        cfgs, fit, bind, plans, fplans, cov, e2c, keys, covb = [], {}, {}, None, None, None, {}, {}, {}
        for s in sizes:
            f = views[s][si]
            f.validate(); gi = f.grid_identity
            if gi is None or gi["registry_sha256"] != reg.registry_sha256 or gi["manifest_sha256"] != man.manifest_sha256 or gi["family"] != family or list(gi["sizes"]) != [s]: raise InputContractError(f"family {family}/{s}: view grid identity invalid")
            if plans is None: plans, fplans, cov = f.plans, f.fit_plans, f.coverage_ok
            else:
                from .twelve_eval import _same_evaluation_plan, _same_fit_plan
                if set(f.plans) != set(plans) or any(not _same_evaluation_plan(f.plans[k], plans[k]) for k in plans) or set(f.fit_plans) != set(fplans) or any(not _same_fit_plan(f.fit_plans[k], fplans[k]) for k in fplans) or f.coverage_ok != cov: raise InputContractError(f"family {family}: views do not share plans/coverage")
            npos = len(f.configs); w_size = reg.size_prior[family][s]
            for c in f.configs:
                if c.evaluation_id in fit: raise InputContractError("evaluation id reused across sizes")
                cfgs.append(replace(c, weight=w_size / npos)); fit[c.evaluation_id] = f.fitting[c.evaluation_id]
                if f.fitting_bindings: bind[c.evaluation_id] = f.fitting_bindings[c.evaluation_id]
                e2c[c.evaluation_id] = gi["evaluation_to_config"][c.evaluation_id]; keys[c.evaluation_id] = gi["cache_keys"][c.evaluation_id]
                if c.evaluation_id in (gi.get("cov_bound") or {}): covb[c.evaluation_id] = gi["cov_bound"][c.evaluation_id]
        ident = dict(registry_sha256=reg.registry_sha256, manifest_sha256=man.manifest_sha256, family=family, system=cfgs[0].system, sizes=sizes, size_weights={s: reg.size_prior[family][s] for s in sizes}, evaluation_to_config=e2c, cache_keys=keys, cov_bound=covb, id_map_rule=views[sizes[0]][0].grid_identity["id_map_rule"])
        p = FamilyInput(family, cfgs, plans, fit, fplans, bool(cov), (bind if bind else None), ident); p.validate(); out.append(p)
    if len(out) == 1: out.append(None)
    return out[0], out[1]


def run_first_wave(reg: GridRegistry, man: ConfigurationManifest, cases: Dict[str, Tuple[FamilyInput, Optional[FamilyInput], Dict[int, int]]], w2_context: W2Context, expected_context_sha256: str,
                   t_target, pseudo_T1, pseudo_T2, archive: Archive, mode: str = "smoke", twelve_anchors: Optional[dict] = None, require_all_families: bool = False, twelve_inputs: Optional[dict] = None, twelve_assets=None, expected_twelve_assets_sha256: Optional[str] = None, twelve_assets_receipt: Optional[str] = None, _stage: str = "full", _commitment: Optional[str] = None, _sealed: Optional[dict] = None) -> RunManifest:
    """_stage: 'full' (target then calibration; development/smoke order), 'calibrate_sealed' (D4-1: NO target; t_target must be None; calibration only, sealed with the target
    commitment), 'sealed_target' (D4-1: target only, after verifying the sealed calibration record and the commitment; calibration copied from the sealed record). Use the
    calibration_first module for the D4-1 entries; do not call the private stages directly."""
    if mode not in ("official", "smoke"): raise InputContractError("mode must be 'official' or 'smoke'")
    if _stage not in ("full", "calibrate_sealed", "sealed_target"): raise InputContractError("stage")
    if _stage == "calibrate_sealed" and (t_target is not None or _commitment is None): raise InputContractError("calibrate_sealed takes no target; a target commitment is required")
    if _stage == "sealed_target" and _sealed is None: raise InputContractError("sealed_target requires the sealed calibration record")
    if mode == "official":
        if _stage == "full": raise InputContractError("mode='official' is only reachable through the calibration-first driver (calibrate_sealed -> evaluate_sealed_target); the target-first stage is development/smoke only")
        require_all_families = True                                                                          # formal scope: all registered families
        if _stage == "calibrate_sealed" and len(np.asarray(pseudo_T1)) != RULES.n_pseudo: raise InputContractError(f"official calibration requires the fixed n_pseudo={RULES.n_pseudo} thresholds (got {len(np.asarray(pseudo_T1))})")
    reg.validate(); man.validate()
    if man.registry_sha256 != reg.registry_sha256: raise InputContractError("manifest not bound to the registry")
    if not isinstance(cases, dict) or not cases: raise InputContractError("no cases")
    t1, t2 = (None, None) if _stage == "calibrate_sealed" else _check_threshold2(t_target); ps = _pseudo_snapshot(pseudo_T1, pseudo_T2)
    if twelve_anchors is not None:
        for fam, A in twelve_anchors.items():
            if fam not in reg.anchors or not np.array_equal(np.asarray(A, float), np.asarray(reg.anchors[fam], float)): raise InputContractError(f"twelve_anchors for {fam} differ from the registry anchors (the registry is the only anchor source)")
    snap = w2_context.snapshot(); snap.validate(expected_context_sha256)
    if twelve_assets is None and (expected_twelve_assets_sha256 is not None or twelve_assets_receipt is not None):
        raise InputContractError("expected twelve asset SHA / registered receipt supplied without an asset (an explicit reuse request is never silently ignored)")   # RD4T1-D
    pinned_twelve_sha = None; twelve_intake_mode = None
    if twelve_assets is not None:
        from .twelve_assets import verify_twelve_assets, REGISTERED_RECEIPTS, TwelveManifestAsset
        if twelve_assets_receipt is not None:
            # D4-3: REGISTERED asset reuse — the asset object must already have passed the receipt-bound intake (intake_registered_twelve_assets) in this process,
            # its SHA must equal the registered receipt's asset SHA and the caller's expected SHA; no regeneration is performed here (regeneration proof = receipt).
            if twelve_assets_receipt not in REGISTERED_RECEIPTS: raise InputContractError(f"unknown registered twelve-asset receipt {twelve_assets_receipt!r}")
            rc = REGISTERED_RECEIPTS[twelve_assets_receipt]
            if not isinstance(twelve_assets, TwelveManifestAsset) or twelve_assets.sha256 != rc["asset_sha256"] or (expected_twelve_assets_sha256 is not None and expected_twelve_assets_sha256 != rc["asset_sha256"]): raise InputContractError("twelve asset does not match the registered receipt / expected SHA")
            if getattr(twelve_assets, "_intake_sha256", None) != twelve_assets.sha256 or not str((twelve_assets.verification or {}).get("intake", "")).startswith("receipt-bound"): raise InputContractError("registered twelve asset must pass intake_registered_twelve_assets in this process before reuse (no regenerate=False bypass)")
            twelve_assets.validate(reg, rc["asset_sha256"])                                               # whole-asset validate against the source-bound registry (no regeneration)
            pinned_twelve_sha = twelve_assets.sha256; twelve_intake_mode = dict(mode="registered_receipt", receipt=twelve_assets_receipt, regeneration="none (receipt)")
        else:
            verify_twelve_assets(twelve_assets, reg, expected_twelve_assets_sha256)                       # legacy path: regeneration intake (kept for unregistered assets)
            pinned_twelve_sha = twelve_assets.sha256; twelve_intake_mode = dict(mode="regeneration", receipt=None, regeneration="all manifests")
        twelve_assets = twelve_assets.snapshot(reg, pinned_twelve_sha)
    rm = RunManifest(__version__, mode, reg.registry_sha256, man.manifest_sha256, expected_context_sha256, snap.asset_sha256, binding=dict(binding_manifest(), twelve_assets_sha256=(None if twelve_assets is None else twelve_assets.sha256), twelve_assets_intake=twelve_intake_mode))
    rm.thresholds = dict(target=(None if _stage == "calibrate_sealed" else [t1, t2]), target_commitment=_commitment, pseudo=dict(n=ps["n"], shape=ps["shape"], sha256_T1=ps["sha256_T1"], sha256_T2=ps["sha256_T2"], T1=ps["T1"].tolist(), T2=ps["T2"].tolist(), dtype="float64", note="full-precision pseudo threshold columns (float64 -> JSON repr round-trips exactly)"))
    # (1) case identity, per-family views, parents
    by_fam: Dict[str, Dict[str, tuple]] = {}
    for key, (fm, fn, pmap) in cases.items():
        fam, size = canonical_case_key(key, {})
        if size not in reg.surviving[fam]: raise InputContractError(f"case {key}: size is not a surviving size")
        by_fam.setdefault(fam, {})[size] = (fm, fn, pmap)
    if require_all_families and set(by_fam) != set(reg.surviving): raise InputContractError(f"formal scope requires all registered families {sorted(reg.surviving)}")
    parents, fams_parent = {}, {}
    for fam, views in by_fam.items():
        pm_, pn_ = assemble_parent(reg, man, fam, {s: (v[0], v[1]) for s, v in views.items()}); parents[fam] = (pm_, pn_); fams_parent[fam] = (pm_, pn_)
    # (2) fingerprints BEFORE the gate (parents + views), gate on the parents (full-size scope)
    def fps_all():
        d = {}
        if twelve_assets is not None:
            twelve_assets.validate(reg, pinned_twelve_sha)
            d["twelve_manifest_asset"] = dict(sha256=pinned_twelve_sha, payload_sha256=twelve_assets.payload_sha())
        for fam, (pm_, pn_) in parents.items(): d[fam] = dict(matched=input_fingerprint(pm_), native=(None if pn_ is None else input_fingerprint(pn_)))
        for key, (fm, fn, pmap) in cases.items(): d[key] = dict(matched=input_fingerprint(fm), native=(None if fn is None else input_fingerprint(fn)), position_map=repr(sorted(pmap.items())))
        for fam, ti in (twelve_inputs or {}).items():                                                          # 12-position inputs are fixed too (banks, plans, maps, expected manifests)
            for size, pair in ti["size_inputs"].items():
                d[f"twelve:{fam}/{size}"] = dict(matched=input_fingerprint(pair[0]), native=(None if pair[1] is None else input_fingerprint(pair[1])), position_ids=repr(sorted(ti["position_ids"][size].items())), native_position_ids=repr(sorted((ti.get("native_position_ids") or {}).get(size, {}).items())))
        return d
    fp0 = fps_all(); rm.fingerprints = dict(at_gate=fp0)
    for fam, (pm_, pn_) in parents.items():
        g = require_official(pm_, pn_) if mode == "official" else official_gate(pm_, pn_, "smoke")
        if not g.passed: raise InputContractError(f"family {fam}: gate failed: " + "; ".join(g.required_failures[:3]))
        rm.gates[fam] = g.as_dict()
    # (3)+(4) target via the COMMON threshold evaluator: parent required quantities -> case position records -> transitions / coordinator -> optional 12-position stage -> eligible truths
    from .positions import W2NotEvaluated
    views_by_fam = {fam: {s: v for s, v in views.items()} for fam, views in by_fam.items()}
    def _archive_diag(key, diag):
        fam, size = canonical_case_key(key, {}); dd = ser.from_jsonable(diag.as_dict()); dd["size_id"] = size; dd["family"] = fam
        return archive.put("family_result", dd, dict(family=fam, size_id=size, kind="case_core_diagnostic")).as_dict()
    deps = dict(mode=mode, engine_version=__version__, registry_sha256=reg.registry_sha256, manifest_sha256=man.manifest_sha256, w2_context_sha256=expected_context_sha256, w2_asset_sha256=snap.asset_sha256, twelve_assets_sha256=pinned_twelve_sha, twelve_assets_intake=twelve_intake_mode, families=sorted(by_fam), sizes={f: sorted(v) for f, v in by_fam.items()}, require_all_families=bool(require_all_families), pseudo=dict(n=ps["n"], sha256_T1=ps["sha256_T1"], sha256_T2=ps["sha256_T2"]), source_binding=binding_manifest(), fingerprints_at_gate=fp0)
    rm.binding["sealed_dependencies"] = deps
    if _stage == "sealed_target":                                                                              # D4-1 (RD4T2-B): EVERY dependency of the sealed calibration must be identical at the target stage
        sd = _sealed.get("binding", {}).get("sealed_dependencies")
        if not isinstance(sd, dict): raise InputContractError("sealed calibration lacks the dependency snapshot")
        diff = {k: (sd.get(k), deps.get(k)) for k in deps if k not in ("fingerprints_at_gate",) and sd.get(k) != deps.get(k)}
        if diff: raise InputContractError(f"sealed calibration dependencies differ from the target run: {sorted(diff)}")
        if _sealed.get("fingerprints", {}).get("at_end") != fp0: raise InputContractError("sealed calibration was made on different inputs (fingerprint mismatch)")
        if _sealed.get("thresholds", {}).get("pseudo", {}).get("sha256_T1") != ps["sha256_T1"] or _sealed["thresholds"]["pseudo"].get("sha256_T2") != ps["sha256_T2"]: raise InputContractError("sealed calibration used different pseudo thresholds")
        if _sealed.get("mode") != mode: raise InputContractError("sealed calibration mode differs from the target mode")
    full = {} if _stage == "calibrate_sealed" else {fam: evaluate_family_full(reg, man, fam, parents[fam], views_by_fam[fam], (snap if fam != "E1" else None), expected_context_sha256, t1, t2, (twelve_inputs or {}).get(fam), with_diagnostics=True, diagnostic_ref_fn=_archive_diag, twelve_assets=twelve_assets) for fam in by_fam}
    fam_res = {fam: fr.parent for fam, fr in full.items()}; case_status = {}
    for fam, fr in full.items():
        for key, rec in fr.case_records.items():
            size = rec["size_id"]; diag = fr.diagnostics.get(key); dref = rec["evidence"].get("diagnostic_ref")
            ref = archive_three_position_result(archive, rec, fam, size); case_status[key] = (rec, rec["position_status"])
            rm.cases[key] = dict(family=fam, size_id=size, threshold=[t1, t2], result_ref=ref.as_dict(), diagnostic_ref=dref, truths=fr.parent.truths, position_status=rec["position_status"], display_label=fr.parent.decision["display_label"], technical_status=fr.parent.decision["technical_status"],
                                 diagnostic=(None if diag is None else dict(truths=diag.truths, technical_status=diag.decision["technical_status"], display_label=diag.decision["display_label"])), scope="case = one size, three positions: position branch from the parent family's quantities; case core diagnostic archived separately")
    if fps_all() != fp0: raise InputContractError("inputs changed during the target evaluation")
    for fam, fr in full.items():
        surviving = list(reg.surviving[fam])
        if fr.expand_family and fam != "E1":
            for size, sha in fr.required_manifests.items():
                tm = twelve_assets.get(fam, size, sha) if twelve_assets is not None else generate_twelve(fam, size, np.asarray(reg.anchors[fam], float)); body = ser.from_jsonable(tm.as_dict()); ref = archive.put("twelve_manifest", body, dict(family=fam, size_id=size, payload_sha256=tm.sha256)); rm.archive_refs[f"twelve_manifest:{fam}/{size}"] = ref.as_dict()
        if fr.twelve is not None:                                                                            # persist the complete evaluated 12-position family Result (target)
            g = ser.from_jsonable(ser.to_jsonable(fr.twelve["full_result"])); g["family"] = fam; g["evidence"]["threshold"] = [t1, t2]
            rm.archive_refs[f"twelve_family_core:{fam}"] = archive.put("family_result", g, dict(family=fam, stage="12-position family mixture")).as_dict()
        status = "technical_fail" if fr.core_technical else fr.plan_status
        rm.families[fam] = dict(status=status, expand_family=(False if fr.core_technical else fr.expand_family), required_manifests=fr.required_manifests, transitions=fr.transitions, twelve_stage=("evaluated in this run" if fr.twelve is not None else ("registered, not evaluated in this run" if (fr.expand_family and not fr.core_technical) else None)),
                                position_plan_status=fr.plan_status, eligibility=fr.eligibility, eligible_truths=fr.eligible_truths, twelve=(None if fr.twelve is None else {k: v for k, v in fr.twelve.items() if k != "full_result"}),
                                family_core=dict(truths=fr.parent.truths, Q_point=fr.parent.Q_point, display_label=fr.parent.decision["display_label"], technical_status=fr.parent.decision["technical_status"], precision=fr.parent.precision["state"]),
                                note=("family-mixture core technical failure: position plan retained for the record but not actionable" if fr.core_technical else None))
        d = ser.from_jsonable(fr.parent.as_dict()); d["family"] = fam; d["evidence"]["threshold"] = [t1, t2]; d["evidence"]["scope"] = "family-mixture core over all surviving sizes (3-position stage)"
        rm.archive_refs[f"family_core:{fam}"] = archive.put("family_result", d, dict(family=fam, stage="3-position family mixture")).as_dict()
    # (5) calibration: ONE common evaluation per pseudo (same procedure as the target; W2 branch fixed by the context); support/strong extracted from that evaluation;
    #     diagnostics: core_only (3-position family core, no eligibility) and any_case_core_diagnostic (OR of per-size standalone cores)
    ctx_ref = dict(asset_sha256=snap.asset_sha256, context_sha256=expected_context_sha256, scope=snap.scope, cases=sorted(k for k in cases if canonical_case_key(k, {})[0] != "E1"))
    elig, core_only, any_case, statuses = [], [], [], []
    if _stage == "sealed_target":
        rm.calibration = ser.from_jsonable(_sealed["calibration"]); rm.per_pseudo_family_status = ser.from_jsonable(_sealed["per_pseudo_family_status"]); rm.branch_completeness = ser.from_jsonable(_sealed["branch_completeness"])
        # Reusing calibration includes every manifest referenced ONLY by pseudo
        # branches. Target and pseudo need not choose the same position branch.
        for key, ref in _sealed.get("archive_refs", {}).items():
            if key.startswith("twelve_manifest:"):
                if key in rm.archive_refs and rm.archive_refs[key] != ref:
                    raise InputContractError("target and sealed calibration disagree on " + key)
                rm.archive_refs[key] = ser.from_jsonable(ser.to_jsonable(ref))
        rm.binding["sealed_calibration"] = dict(sha256=_sealed["_sha256"], commitment=_sealed["thresholds"]["target_commitment"], copied="calibration / per-pseudo status / branch completeness copied verbatim from the sealed record; not recomputed")
    for x, y in (zip(ps["T1"], ps["T2"]) if _stage != "sealed_target" else ()):
        fx = {fam: evaluate_family_full(reg, man, fam, parents[fam], views_by_fam[fam], (snap if fam != "E1" else None), expected_context_sha256, float(x), float(y), (twelve_inputs or {}).get(fam), with_diagnostics=True, twelve_assets=twelve_assets) for fam in by_fam}
        elig.append({lvl: any_family_truth([f.eligible_truths[lvl] for f in fx.values()]) for lvl in ("support", "strong")})
        core_only.append({lvl: any_family_truth([f.parent.truths[lvl] for f in fx.values()]) for lvl in ("support", "strong")})
        any_case.append({lvl: any_family_truth([d.truths[lvl] for f in fx.values() for d in f.diagnostics.values()] or [UNKNOWN]) for lvl in ("support", "strong")})
        st_i = {}
        for fam, f in fx.items():
            sm = f.summary()
            # D4-4 v4 (R2V3-B): pseudo-side EVIDENCE archived content-addressed: the 3-position parent FamilyResult and the position plan (transitions / status / expand / manifests)
            pd = ser.from_jsonable(ser.to_jsonable(f.parent.as_dict())); pd["family"] = fam; pd["evidence"]["threshold"] = [float(x), float(y)]; pd["evidence"]["pseudo_index"] = len(statuses); pd["evidence"]["scope"] = "family-mixture core over all surviving sizes (3-position stage; pseudo)"
            pref = archive.put("family_result", pd, dict(family=fam, stage="3-position family mixture (pseudo)", pseudo_index=len(statuses))); sm["parent_ref"] = pref.as_dict()
            plan_rec = dict(kind="pseudo_family_plan", family=fam, pseudo_index=len(statuses), threshold=[float(x), float(y)], transitions=f.transitions, plan_status=f.plan_status, expand_family=(False if f.core_technical else f.expand_family), required_manifests=f.required_manifests, core_technical=f.core_technical, surviving_sizes=sorted(f.transitions))
            # Archive the EXACT records already hashed by the transitions. Do
            # not add a pseudo index to their bytes; the plan binds the index.
            plan_rec["case_refs"] = {}
            for size in sorted(f.transitions):
                pos = f.case_records[f"{fam}/{size}"]
                pos_ref = archive_three_position_result(archive, pos, fam, size)
                if pos_ref.sha256 != f.transitions[size]["three_position_result_sha256"]:
                    raise InputContractError("pseudo position source differs from its transition")
                plan_rec["case_refs"][size] = pos_ref.as_dict()
            plref = archive.put("transition", plan_rec, dict(kind="pseudo_family_plan", family=fam, pseudo_index=len(statuses))); sm["plan_ref"] = plref.as_dict()
            if plan_rec["expand_family"] and plan_rec["plan_status"] != "technical_fail":                                # the registered 12-position manifests referenced by the pseudo plan are archived too (content-addressed; idempotent)
                for size, sha_ in (f.required_manifests or {}).items():
                    if sha_ is None or f"twelve_manifest:{fam}/{size}" in rm.archive_refs: continue
                    tm = twelve_assets.get(fam, size, sha_) if twelve_assets is not None else generate_twelve(fam, size, np.asarray(reg.anchors[fam], float)); body = ser.from_jsonable(tm.as_dict()); mref = archive.put("twelve_manifest", body, dict(family=fam, size_id=size, payload_sha256=tm.sha256)); rm.archive_refs[f"twelve_manifest:{fam}/{size}"] = mref.as_dict()
            if f.twelve is not None:                                                                        # D4-2: pseudo-side FULL 12-position Result archived (content-addressed), not only the summary
                g = ser.from_jsonable(ser.to_jsonable(f.twelve["full_result"])); g["family"] = fam; g["evidence"]["threshold"] = [float(x), float(y)]; g["evidence"]["pseudo_index"] = len(statuses)
                ref = archive.put("family_result", g, dict(family=fam, stage="12-position family mixture (pseudo)", pseudo_index=len(statuses))); sm["twelve_full_result_ref"] = ref.as_dict(); sm["twelve_full_result_sha256"] = ref.sha256
            st_i[fam] = sm
        statuses.append(st_i)
    if fps_all() != fp0: raise InputContractError("inputs changed during the pseudo calibration")
    if ps["sha256_T1"] != hashlib.sha256(np.ascontiguousarray(ps["T1"]).tobytes()).hexdigest() or ps["sha256_T2"] != hashlib.sha256(np.ascontiguousarray(ps["T2"]).tobytes()).hexdigest(): raise InputContractError("pseudo thresholds changed during the calibration")
    rm.fingerprints["at_end"] = fps_all()
    if _stage == "sealed_target":
        tmiss = [dict(where="target", family=fam, reason="triggered 12-position stage not evaluated") for fam, f in rm.families.items() if f["expand_family"] and f.get("twelve_stage") != "evaluated in this run"]
        rm.branch_completeness = dict(rm.branch_completeness, target_missing_branches=tmiss, full_procedure_including_target=bool(not tmiss and not rm.branch_completeness.get("missing_branches") and rm.branch_completeness.get("all_registered_families")), note_target="target-side accounting added at the sealed target stage; the sealed calibration itself is unchanged")
        rm.binding["order_record"] = dict(sealed_calibration_ref=_sealed.get("_ref"), sealed_calibration_sha256=_sealed["_sha256"], commitment=_sealed["thresholds"]["target_commitment"], target=[t1, t2], scope="dependency order inside this verified driver; not a proof about computations outside it")
        rm.archive_refs["registry"] = archive.put("registry", reg.as_dict(), dict(registry_sha256=reg.registry_sha256)).as_dict(); rm.binding["run_manifest_sha256"] = rm.payload_sha()
        ref = archive.put("transition", ser.from_jsonable(rm.as_dict()), dict(kind="sealed_target_run", payload_sha256=rm.binding["run_manifest_sha256"], sealed_calibration_sha256=_sealed["_sha256"])); rm.binding["run_manifest_file_sha256"] = ref.sha256; rm.binding["run_manifest_ref"] = ref.as_dict()
        return rm
    # full-procedure accounting: target AND every pseudo — every triggered 12-position stage must have been supplied and evaluated; missing branches are listed
    missing = []
    for fam, f in rm.families.items():
        if f["expand_family"] and f.get("twelve_stage") != "evaluated in this run": missing.append(dict(where="target", family=fam, reason="triggered 12-position stage not evaluated"))
    for i, st in enumerate(statuses):
        for fam, fs in st.items():
            if fs["expand_family"] and fs["twelve"] is None: missing.append(dict(where=f"pseudo[{i}]", family=fam, reason="triggered 12-position stage not evaluated"))
    all_fams = set(by_fam) == set(reg.surviving); complete = all_fams and not missing
    rm.branch_completeness = dict(all_registered_families=all_fams, missing_branches=missing, note="procedure completeness only: unresolved estimates after a fully executed procedure stay 'unknown' in the Wilson aggregation")
    for lvl, thr in (("support", RULES.usable_support), ("strong", RULES.usable_strong)):
        s = calibrate([t[lvl] for t in elig], thr, expected_n=ps["n"])
        s.reason = ("scope: ELIGIBLE family truths via the common threshold evaluator (parent required quantities -> position branch -> coordinator -> 12-position stage when supplied); " + ("all registered families and every triggered 12-position stage (target and every pseudo) evaluated" if complete else "NOT the registered full-procedure calibration: " + ("some families not supplied; " if not all_fams else "") + (f"12-position stage not integrated for {len(missing)} triggered branch(es) (target/pseudo; see branch_completeness)" if missing else "")))
        s.w2_context = dict(ctx_ref)
        c_only = calibrate([t[lvl] for t in core_only], thr, expected_n=ps["n"]); c_only.reason = "core_only diagnostic: 3-position family core without position eligibility (never used for 'usable')"
        c_any = calibrate([t[lvl] for t in any_case], thr, expected_n=ps["n"]); c_any.reason = "any_case_core_diagnostic: OR of per-size standalone cores (NOT the registered family calibration; never used for 'usable')"
        rm.calibration[lvl] = dict(summary=s.as_dict(), truths=[t[lvl] for t in elig], core_only=dict(summary=c_only.as_dict(), truths=[t[lvl] for t in core_only]), any_case_core_diagnostic=dict(summary=c_any.as_dict(), truths=[t[lvl] for t in any_case]), full_procedure=complete)
    rm.per_pseudo_family_status = statuses
    rm.archive_refs["registry"] = archive.put("registry", reg.as_dict(), dict(registry_sha256=reg.registry_sha256)).as_dict()
    rm.binding["run_manifest_sha256"] = rm.payload_sha()
    kind = "sealed_calibration" if _stage == "calibrate_sealed" else "run_manifest"
    ref = archive.put("transition", ser.from_jsonable(rm.as_dict()), dict(kind=kind, payload_sha256=rm.binding["run_manifest_sha256"])); rm.binding["run_manifest_file_sha256"] = ref.sha256; rm.binding["run_manifest_ref"] = ref.as_dict()
    return rm
