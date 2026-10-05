# -*- coding: utf-8 -*-
"""D4C-1 (design Step1_PhaseD_D4_calibration_design_v0.2.md §F.2; audit R-D4DESIGN-D): family-partial calibration and the combiner.

calibrate_family_partial(...)  — ONE family (all its surviving sizes, both systems, the registered first-wave plans and, for a non-E1 family, the 12-position inputs): the
    SAME per-pseudo procedure as integrated_runner.run_first_wave(_stage='calibrate_sealed') restricted to that family (parent assembly -> fingerprints before the gate ->
    gate -> for every pseudo pair the common threshold evaluator -> archived parent / plan / position sources / 12-position full Result -> fingerprints after). It issues a
    FamilyPartialRecord (schema family_partial_calibration_v1; archive identity kind 'family_partial_calibration'): per-pseudo family status (eligible truths with the
    priority technical_fail > True > unknown > False as derived by the common evaluator), the standalone case-core diagnostic truths (kept apart; never an eligible truth),
    the gate, local fingerprints before/after, the pseudo column identity and the target commitment. It NEVER aggregates: no c/u/n, no Wilson, no usable, no calibration
    block (a partial is not a sealed calibration and load_sealed_record rejects it by archive identity).
combine_family_partials(...) — exactly one partial per registered family (missing / duplicate / foreign rejected), common identity (engine + source binding, mode, registry /
    manifest, W2 context / shared-null asset, twelve asset intake, the SAME pseudo columns (SHA and row order), target commitment, campaign) and family identity (sizes,
    fingerprints, gate) checked against the fixed family map; per pseudo p the eligible truths of ALL families are aggregated with calibration.any_family_truth and the
    Wilson upper bound over the fixed n (RULES.n_pseudo in official mode) is compared with the registered thresholds — never a per-family average / OR of usable. The
    combined RunManifest is content-identical to the single-process calibrate_sealed record except for binding['combiner'] (provenance), and is verified with
    run_reader.verify_run_references (stage / binding / position sources / plans / 12-position Results / calibration re-derivation) before it is archived as a
    'sealed_calibration' record.
verify_partial_record(...)   — reader for a partial: a transient one-family view is passed through run_reader.verify_run_references (no aggregate claim is stored).
load_combined_sealed_record  — Phase E reader: load_sealed_record (global kind) + combiner provenance (every partial resolves, same commitment / pseudo columns, statuses
    verbatim) + verify_run_references with the current source binding; a partial reference is rejected.
Archive note: partials written in separate processes are merged byte-exactly with archive.merge_archives before combining; every record is content-addressed, so the refs
of the combined record equal those of the single-process run.
Scope: no new statistic, threshold or decision rule; E1 is never treated as a 12-position family; the registered official guard of run_first_wave (all families) is untouched."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, Sequence, Tuple
import hashlib
import numpy as np
from .errors import InputContractError
from .rules_config import RULES
from .grid_registry import GridRegistry
from .grid_manifest import ConfigurationManifest
from .integrated_runner import RunManifest, assemble_parent, _pseudo_snapshot
from .calibration import calibrate, any_family_truth
from .threshold_evaluator import evaluate_family_full
from .w2_context import W2Context, canonical_case_key
from .official_gate import official_gate, require_official
from .formal_runner import input_fingerprint
from .stage12 import generate_twelve
from .archive import Archive, ArchiveRef, archive_three_position_result
from .checkpoint import binding_manifest
from .truth import UNKNOWN
from . import serialization as ser
from . import __version__

PARTIAL_SCHEMA = "family_partial_calibration_v1"
PARTIAL_KIND = "family_partial_calibration"
SEALED_KIND = "sealed_calibration"
_COMMON_BINDING = ("engine_version", "rules_document_sha256", "tables_sha256", "modules", "registered_profile")


def _is_sha(v) -> bool: return isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)


def _payload_sha(d: dict, drop=("partial_sha256", "partial_file_sha256", "partial_ref")) -> str:
    b = ser.from_jsonable(ser.to_jsonable(d)); b["binding"] = {k: v for k, v in b["binding"].items() if k not in drop}
    return hashlib.sha256(ser.dumps(b).encode()).hexdigest()


@dataclass
class FamilyPartialRecord:
    schema: str; kind: str; engine_version: str; mode: str; family: str; registry_sha256: str; manifest_sha256: str; w2_context_sha256: str; w2_asset_sha256: str
    sizes: list = field(default_factory=list); gate: dict = field(default_factory=dict); fingerprints: Dict[str, dict] = field(default_factory=dict); thresholds: dict = field(default_factory=dict)
    archive_refs: Dict[str, dict] = field(default_factory=dict); per_pseudo_status: list = field(default_factory=list); per_pseudo_diagnostics: list = field(default_factory=list)
    per_pseudo_manifest_keys: list = field(default_factory=list); w2_context_ref: dict = field(default_factory=dict); campaign: Optional[dict] = None; plan_objects: dict = field(default_factory=dict); binding: dict = field(default_factory=dict)
    scope: str = ("family partial calibration: ONE family's per-pseudo eligible truths via the common threshold evaluator (parent required quantities -> position branch -> coordinator -> 12-position "
                  "stage when supplied); standalone case-core diagnostics kept apart; NO aggregation (no c/u/n, Wilson, usable or label) — a partial is not a sealed calibration")
    def as_dict(self): return ser.to_jsonable(self.__dict__)
    def payload_sha(self) -> str: return _payload_sha(self.as_dict())


def _check_campaign(campaign, mode: str):
    if campaign is None:
        if mode == "official": raise InputContractError("official partial requires a campaign identity (dict with a non-empty 'id')")
        return None
    if not isinstance(campaign, dict) or not isinstance(campaign.get("id"), str) or not campaign["id"]: raise InputContractError("campaign must be a dict with a non-empty string 'id'")
    return ser.from_jsonable(ser.to_jsonable(campaign))


def _intake_twelve(reg, twelve_assets, expected_twelve_assets_sha256, twelve_assets_receipt):
    """Same intake contract as run_first_wave (registered receipt-bound reuse or legacy regeneration); returns (snapshot or None, pinned sha, intake mode)."""
    if twelve_assets is None and (expected_twelve_assets_sha256 is not None or twelve_assets_receipt is not None):
        raise InputContractError("expected twelve asset SHA / registered receipt supplied without an asset (an explicit reuse request is never silently ignored)")
    if twelve_assets is None: return None, None, None
    from .twelve_assets import verify_twelve_assets, REGISTERED_RECEIPTS, TwelveManifestAsset
    if twelve_assets_receipt is not None:
        if twelve_assets_receipt not in REGISTERED_RECEIPTS: raise InputContractError(f"unknown registered twelve-asset receipt {twelve_assets_receipt!r}")
        rc = REGISTERED_RECEIPTS[twelve_assets_receipt]
        if not isinstance(twelve_assets, TwelveManifestAsset) or twelve_assets.sha256 != rc["asset_sha256"] or (expected_twelve_assets_sha256 is not None and expected_twelve_assets_sha256 != rc["asset_sha256"]): raise InputContractError("twelve asset does not match the registered receipt / expected SHA")
        if getattr(twelve_assets, "_intake_sha256", None) != twelve_assets.sha256 or not str((twelve_assets.verification or {}).get("intake", "")).startswith("receipt-bound"): raise InputContractError("registered twelve asset must pass intake_registered_twelve_assets in this process before reuse (no regenerate=False bypass)")
        twelve_assets.validate(reg, rc["asset_sha256"]); pinned = twelve_assets.sha256; mode = dict(mode="registered_receipt", receipt=twelve_assets_receipt, regeneration="none (receipt)")
    else:
        verify_twelve_assets(twelve_assets, reg, expected_twelve_assets_sha256); pinned = twelve_assets.sha256; mode = dict(mode="regeneration", receipt=None, regeneration="all manifests")
    return twelve_assets.snapshot(reg, pinned), pinned, mode


def plan_object_inventory(views: Dict[str, tuple], parents: tuple, twelve_inputs: Optional[dict]) -> Dict[str, tuple]:
    """id() of the evaluation / fitting plan dictionaries carried by EVERY input object (first-wave size views, assembled parents, 12-position size views; both systems)."""
    objs = {}
    for s_, (fm, fn, _) in views.items():
        objs[f"view:{s_}/matched"] = (id(fm.plans), id(fm.fit_plans))
        if fn is not None: objs[f"view:{s_}/native"] = (id(fn.plans), id(fn.fit_plans))
    objs["parent/matched"] = (id(parents[0].plans), id(parents[0].fit_plans))
    if parents[1] is not None: objs["parent/native"] = (id(parents[1].plans), id(parents[1].fit_plans))
    for s_, pair in ((twelve_inputs or {}).get("size_inputs") or {}).items():
        objs[f"twelve:{s_}/matched"] = (id(pair[0].plans), id(pair[0].fit_plans))
        if pair[1] is not None: objs[f"twelve:{s_}/native"] = (id(pair[1].plans), id(pair[1].fit_plans))
    return objs


def plan_object_summary(objs: Dict[str, tuple]) -> dict:
    """Sharing summary (R-D4C1-C): every first-wave object (views + parents) must carry the SAME plan dictionaries (`is`), every 12-position view the same pair among
    themselves; whether the 12-position pair IS the first-wave pair is recorded (required in official mode for a non-E1 family: first-wave and added configurations share
    the registered family plans)."""
    fw = {v for k, v in objs.items() if not k.startswith("twelve:")}; tw = {v for k, v in objs.items() if k.startswith("twelve:")}
    return dict(first_wave_shared=(len(fw) == 1), twelve_shared=(len(tw) <= 1), twelve_present=bool(tw), twelve_shares_first_wave=(bool(tw) and fw == tw), n_objects=len(objs))


def calibrate_family_partial(reg: GridRegistry, man: ConfigurationManifest, family: str, cases: Dict[str, tuple], w2_context: W2Context, expected_context_sha256: str, pseudo_T1, pseudo_T2, archive: Archive, target_commitment: str, *,
                             mode: str = "smoke", campaign: Optional[dict] = None, twelve_inputs: Optional[dict] = None, twelve_assets=None, expected_twelve_assets_sha256: Optional[str] = None, twelve_assets_receipt: Optional[str] = None) -> FamilyPartialRecord:
    """ONE family's partial calibration (keyword-only options). cases: {f'{family}/{size}': (fm, fn, pmap)} for EXACTLY the surviving sizes of this family. twelve_inputs: the
    12-position inputs of this family (required in official mode for a non-E1 family; rejected for E1 in every mode). No observed target is accepted."""
    if not (isinstance(target_commitment, str) and _is_sha(target_commitment)): raise InputContractError("target commitment must be a sha256 hex string")
    if mode not in ("official", "smoke"): raise InputContractError("mode must be 'official' or 'smoke'")
    reg.validate(); man.validate()
    if man.registry_sha256 != reg.registry_sha256: raise InputContractError("manifest not bound to the registry")
    if family not in reg.surviving: raise InputContractError(f"family {family!r} is not a registered family")
    campaign = _check_campaign(campaign, mode)
    if not isinstance(cases, dict) or not cases: raise InputContractError("no cases")
    sizes = list(reg.surviving[family]); want = {f"{family}/{s}" for s in sizes}
    for key in cases:
        fam, size = canonical_case_key(key, {})
        if fam != family: raise InputContractError(f"case {key}: not a case of family {family} (a partial takes exactly one family)")
        if size not in sizes: raise InputContractError(f"case {key}: size is not a surviving size")
    if set(cases) != want: raise InputContractError(f"family {family}: a partial requires exactly the surviving sizes {sizes} (got {sorted(cases)})")
    if family == "E1" and twelve_inputs is not None: raise InputContractError("E1 is observer-homogeneous: 12-position inputs are not accepted for E1")
    if mode == "official":
        if len(np.asarray(pseudo_T1)) != RULES.n_pseudo: raise InputContractError(f"official calibration requires the fixed n_pseudo={RULES.n_pseudo} thresholds (got {len(np.asarray(pseudo_T1))})")
        if family != "E1" and twelve_inputs is None: raise InputContractError(f"official partial of {family} requires the 12-position inputs (every triggered family completes the 12-position stage for all surviving sizes)")
        if family != "E1" and (twelve_assets is None or twelve_assets_receipt is None): raise InputContractError(f"official partial of {family} requires the registered twelve-position asset (receipt-bound intake)")
    if twelve_inputs is not None:
        if not isinstance(twelve_inputs, dict) or set(twelve_inputs.get("size_inputs") or {}) != set(sizes) or set(twelve_inputs.get("position_ids") or {}) != set(sizes): raise InputContractError(f"family {family}: twelve_inputs must cover exactly the surviving sizes {sizes} (size_inputs and position_ids)")
    ps = _pseudo_snapshot(pseudo_T1, pseudo_T2)
    snap = w2_context.snapshot(); snap.validate(expected_context_sha256)
    twelve_assets, pinned_twelve_sha, twelve_intake_mode = _intake_twelve(reg, twelve_assets, expected_twelve_assets_sha256, twelve_assets_receipt)
    views = {canonical_case_key(k, {})[1]: v for k, v in cases.items()}
    pm_, pn_ = assemble_parent(reg, man, family, {s: (v[0], v[1]) for s, v in views.items()})
    rec = FamilyPartialRecord(PARTIAL_SCHEMA, PARTIAL_KIND, __version__, mode, family, reg.registry_sha256, man.manifest_sha256, expected_context_sha256, snap.asset_sha256, sizes=list(sizes),
                              binding=dict(binding_manifest(), twelve_assets_sha256=pinned_twelve_sha, twelve_assets_intake=twelve_intake_mode))
    rec.thresholds = dict(target=None, target_commitment=target_commitment, pseudo=dict(n=ps["n"], shape=ps["shape"], sha256_T1=ps["sha256_T1"], sha256_T2=ps["sha256_T2"], T1=ps["T1"].tolist(), T2=ps["T2"].tolist(), dtype="float64", note="full-precision pseudo threshold columns (float64 -> JSON repr round-trips exactly)"))
    rec.campaign = campaign
    def fps_all():
        d = {}
        if twelve_assets is not None:
            twelve_assets.validate(reg, pinned_twelve_sha); d["twelve_manifest_asset"] = dict(sha256=pinned_twelve_sha, payload_sha256=twelve_assets.payload_sha())
        d[family] = dict(matched=input_fingerprint(pm_), native=(None if pn_ is None else input_fingerprint(pn_)))
        for key, (fm, fn, pmap) in cases.items(): d[key] = dict(matched=input_fingerprint(fm), native=(None if fn is None else input_fingerprint(fn)), position_map=repr(sorted(pmap.items())))
        if twelve_inputs is not None:
            for size, pair in twelve_inputs["size_inputs"].items():
                d[f"twelve:{family}/{size}"] = dict(matched=input_fingerprint(pair[0]), native=(None if pair[1] is None else input_fingerprint(pair[1])), position_ids=repr(sorted(twelve_inputs["position_ids"][size].items())), native_position_ids=repr(sorted((twelve_inputs.get("native_position_ids") or {}).get(size, {}).items())))
        return d
    objs0 = plan_object_inventory(views, (pm_, pn_), twelve_inputs); po = plan_object_summary(objs0)
    if not po["first_wave_shared"]: raise InputContractError(f"family {family}: the first-wave size views and the assembled parents must carry the SAME evaluation / fitting plan objects (family-shared plans)")
    if not po["twelve_shared"]: raise InputContractError(f"family {family}: the 12-position size views must share one pair of plan objects")
    if mode == "official" and twelve_inputs is not None and not po["twelve_shares_first_wave"]: raise InputContractError(f"family {family}: official partial requires the 12-position views to carry the first-wave plan objects (registered family plans)")
    fp0 = fps_all(); rec.fingerprints = dict(at_gate=fp0)
    g = require_official(pm_, pn_) if mode == "official" else official_gate(pm_, pn_, "smoke")
    if not g.passed: raise InputContractError(f"family {family}: gate failed: " + "; ".join(g.required_failures[:3]))
    if mode == "official" and g.diagnostics.get("environment_source") != "live_collected": raise InputContractError("official gate must use the live collected environment")
    rec.gate = g.as_dict()
    rec.binding["partial_dependencies"] = dict(mode=mode, engine_version=__version__, registry_sha256=reg.registry_sha256, manifest_sha256=man.manifest_sha256, w2_context_sha256=expected_context_sha256, w2_asset_sha256=snap.asset_sha256, twelve_assets_sha256=pinned_twelve_sha, twelve_assets_intake=twelve_intake_mode,
                                               families=[family], sizes={family: sorted(sizes)}, require_all_families=False, pseudo=dict(n=ps["n"], sha256_T1=ps["sha256_T1"], sha256_T2=ps["sha256_T2"]), source_binding=binding_manifest(), fingerprints_at_gate=fp0, family=family, target_commitment=target_commitment, campaign=campaign)
    rec.w2_context_ref = dict(asset_sha256=snap.asset_sha256, context_sha256=expected_context_sha256, scope=snap.scope, cases=(sorted(cases) if family != "E1" else []))
    w2 = snap if family != "E1" else None
    for i, (x, y) in enumerate(zip(ps["T1"], ps["T2"])):
        f = evaluate_family_full(reg, man, family, (pm_, pn_), views, w2, expected_context_sha256, float(x), float(y), twelve_inputs, with_diagnostics=True, twelve_assets=twelve_assets)
        sm = f.summary()
        pd = ser.from_jsonable(ser.to_jsonable(f.parent.as_dict())); pd["family"] = family; pd["evidence"]["threshold"] = [float(x), float(y)]; pd["evidence"]["pseudo_index"] = i; pd["evidence"]["scope"] = "family-mixture core over all surviving sizes (3-position stage; pseudo)"
        pref = archive.put("family_result", pd, dict(family=family, stage="3-position family mixture (pseudo)", pseudo_index=i)); sm["parent_ref"] = pref.as_dict()
        plan_rec = dict(kind="pseudo_family_plan", family=family, pseudo_index=i, threshold=[float(x), float(y)], transitions=f.transitions, plan_status=f.plan_status, expand_family=(False if f.core_technical else f.expand_family), required_manifests=f.required_manifests, core_technical=f.core_technical, surviving_sizes=sorted(f.transitions))
        plan_rec["case_refs"] = {}
        for size in sorted(f.transitions):
            pos = f.case_records[f"{family}/{size}"]; pos_ref = archive_three_position_result(archive, pos, family, size)
            if pos_ref.sha256 != f.transitions[size]["three_position_result_sha256"]: raise InputContractError("pseudo position source differs from its transition")
            plan_rec["case_refs"][size] = pos_ref.as_dict()
        plref = archive.put("transition", plan_rec, dict(kind="pseudo_family_plan", family=family, pseudo_index=i)); sm["plan_ref"] = plref.as_dict()
        added = []
        if plan_rec["expand_family"] and plan_rec["plan_status"] != "technical_fail":
            for size, sha_ in (f.required_manifests or {}).items():
                key = f"twelve_manifest:{family}/{size}"
                if sha_ is None: continue
                if key not in rec.archive_refs:
                    tm = twelve_assets.get(family, size, sha_) if twelve_assets is not None else generate_twelve(family, size, np.asarray(reg.anchors[family], float)); body = ser.from_jsonable(tm.as_dict())
                    rec.archive_refs[key] = archive.put("twelve_manifest", body, dict(family=family, size_id=size, payload_sha256=tm.sha256)).as_dict()
                added.append(key)                                                                             # replay order of the single-process run (first pseudo that triggers adds the key)
        if f.twelve is not None:
            gg = ser.from_jsonable(ser.to_jsonable(f.twelve["full_result"])); gg["family"] = family; gg["evidence"]["threshold"] = [float(x), float(y)]; gg["evidence"]["pseudo_index"] = i
            ref = archive.put("family_result", gg, dict(family=family, stage="12-position family mixture (pseudo)", pseudo_index=i)); sm["twelve_full_result_ref"] = ref.as_dict(); sm["twelve_full_result_sha256"] = ref.sha256
        rec.per_pseudo_status.append(sm)
        rec.per_pseudo_diagnostics.append({k.split("/", 1)[1]: dict(support=d.truths["support"], strong=d.truths["strong"]) for k, d in sorted(f.diagnostics.items())})
        rec.per_pseudo_manifest_keys.append(added)
    if fps_all() != fp0: raise InputContractError("inputs changed during the pseudo calibration")
    if ps["sha256_T1"] != hashlib.sha256(np.ascontiguousarray(ps["T1"]).tobytes()).hexdigest() or ps["sha256_T2"] != hashlib.sha256(np.ascontiguousarray(ps["T2"]).tobytes()).hexdigest(): raise InputContractError("pseudo thresholds changed during the calibration")
    objs1 = plan_object_inventory(views, (pm_, pn_), twelve_inputs)
    if objs1 != objs0: raise InputContractError(f"family {family}: plan objects were replaced during the calibration (content-identical copies are not the registered plan objects): {sorted(k for k in objs0 if objs1.get(k) != objs0[k])}")
    if plan_object_summary(objs1) != po: raise InputContractError(f"family {family}: plan object sharing changed during the calibration")
    rec.plan_objects = dict(po, stable_after=True, checked=("first-wave size views (both systems), assembled parents (both systems)" + (", 12-position size views (both systems)" if twelve_inputs is not None else "")), rule="same objects (`is`) before the gate and after the last pseudo; content identity is covered by the fingerprints")
    rec.fingerprints["at_end"] = fps_all()
    rec.archive_refs["registry"] = archive.put("registry", reg.as_dict(), dict(registry_sha256=reg.registry_sha256)).as_dict()
    rec.binding["partial_sha256"] = rec.payload_sha()
    ref = archive.put("transition", ser.from_jsonable(rec.as_dict()), dict(kind=PARTIAL_KIND, family=family, payload_sha256=rec.binding["partial_sha256"], target_commitment=target_commitment)); rec.binding["partial_file_sha256"] = ref.sha256; rec.binding["partial_ref"] = ref.as_dict()
    archive.flush()
    return rec


# --------------------------------------------------------------------------------------------------------------------------------------------- readers
def load_partial_record(archive: Archive, ref: dict) -> dict:
    r = ArchiveRef(**ref); d = ser.from_jsonable(archive.get(r))
    if r.kind != "transition" or r.identity.get("kind") != PARTIAL_KIND: raise InputContractError("reference is not a family partial calibration record")
    _check_partial_shape(d)
    if _payload_sha(d) != d["binding"]["partial_sha256"] or r.identity.get("payload_sha256") != d["binding"]["partial_sha256"] or r.identity.get("family") != d["family"] or r.identity.get("target_commitment") != d["thresholds"]["target_commitment"]: raise InputContractError("partial record payload SHA / identity mismatch")
    return d


def _check_partial_shape(d: dict):
    if not isinstance(d, dict) or d.get("schema") != PARTIAL_SCHEMA or d.get("kind") != PARTIAL_KIND: raise InputContractError("not a family partial calibration record")
    thr = d.get("thresholds") or {}; ps = thr.get("pseudo") or {}
    if thr.get("target") is not None or not _is_sha(thr.get("target_commitment")): raise InputContractError("partial must carry no target and a target commitment")
    n = ps.get("n")
    if not isinstance(n, int) or n < 1 or len(d.get("per_pseudo_status") or []) != n or len(d.get("per_pseudo_diagnostics") or []) != n or len(d.get("per_pseudo_manifest_keys") or []) != n: raise InputContractError("partial per-pseudo inventories do not match n")
    if len(ps.get("T1") or []) != n or len(ps.get("T2") or []) != n or hashlib.sha256(np.ascontiguousarray(np.asarray(ps["T1"], float)).tobytes()).hexdigest() != ps.get("sha256_T1") or hashlib.sha256(np.ascontiguousarray(np.asarray(ps["T2"], float)).tobytes()).hexdigest() != ps.get("sha256_T2"): raise InputContractError("partial pseudo columns differ from their recorded SHA / length")
    fam = d.get("family")
    if any(s.get("family") != fam for s in d["per_pseudo_status"]): raise InputContractError("partial status family differs from the record family")
    if "calibration" in d or "families" in d or "cases" in d: raise InputContractError("a partial must not carry aggregated calibration / target results")
    pdep = (d.get("binding") or {}).get("partial_dependencies") or {}
    if pdep.get("families") != [fam] or pdep.get("require_all_families") is not False or pdep.get("target_commitment") != thr["target_commitment"]: raise InputContractError("partial dependencies do not describe a one-family partial")
    if d.get("fingerprints", {}).get("at_gate") != d.get("fingerprints", {}).get("at_end"): raise InputContractError("partial fingerprints at_gate != at_end")
    po = d.get("plan_objects")
    if not isinstance(po, dict) or po.get("stable_after") is not True or po.get("first_wave_shared") is not True or po.get("twelve_shared") is not True: raise InputContractError("partial plan-object record missing or not stable / shared")
    for k in d["fingerprints"]["at_gate"]:
        if k in ("twelve_manifest_asset", fam): continue
        if canonical_case_key(k.split(":", 1)[1] if k.startswith("twelve:") else k, {})[0] != fam: raise InputContractError(f"partial fingerprint {k!r} is not of family {fam}")


def _one_family_view(d: dict) -> dict:
    """Transient RunManifest-shaped view of ONE partial for run_reader.verify_run_references (never archived; carries a one-family diagnostic aggregation that is not a calibration)."""
    fam = d["family"]; st = [{fam: s} for s in d["per_pseudo_status"]]; cal = {}
    for lvl, thr in (("support", RULES.usable_support), ("strong", RULES.usable_strong)):
        truths = [any_family_truth([s[fam]["eligible_truths"][lvl]]) for s in st]; s_ = calibrate(truths, thr, expected_n=len(truths)); s_.w2_context = dict(d["w2_context_ref"])
        cal[lvl] = dict(summary=s_.as_dict(), truths=truths, full_procedure=False)
    missing = [dict(where=f"pseudo[{i}]", family=fam, reason="triggered 12-position stage not evaluated") for i, s in enumerate(d["per_pseudo_status"]) if s["expand_family"] and not (isinstance(s.get("twelve"), dict) and s["twelve"].get("evaluated"))]
    b = {k: v for k, v in d["binding"].items() if k not in ("partial_dependencies", "partial_sha256", "partial_file_sha256", "partial_ref")}; b["sealed_dependencies"] = dict(d["binding"]["partial_dependencies"])
    v = dict(engine_version=d["engine_version"], mode=d["mode"], registry_sha256=d["registry_sha256"], manifest_sha256=d["manifest_sha256"], w2_context_sha256=d["w2_context_sha256"], w2_asset_sha256=d["w2_asset_sha256"], families={}, cases={}, calibration=cal, gates={fam: d["gate"]},
             fingerprints=ser.from_jsonable(ser.to_jsonable(d["fingerprints"])), thresholds=ser.from_jsonable(ser.to_jsonable(d["thresholds"])), archive_refs=ser.from_jsonable(ser.to_jsonable(d["archive_refs"])), per_pseudo_family_status=st,
             branch_completeness=dict(all_registered_families=False, missing_branches=missing, note="one-family view for verification only"), binding=b, final_label_released=False, scope="transient one-family verification view of a partial (not a sealed calibration)")
    v["binding"]["run_manifest_sha256"] = _payload_sha(v, drop=("run_manifest_sha256", "run_manifest_file_sha256", "run_manifest_ref")); return v


def verify_partial_record(d: dict, archive: Archive, registered: Optional[dict] = None, current_source_binding: bool = False) -> dict:
    """Semantic re-verification of ONE partial through the run reader (position sources, plans, 12-position Results, per-pseudo eligibility re-derived from the archived records)."""
    from .run_reader import verify_run_references
    _check_partial_shape(d)
    if _payload_sha(d) != d["binding"]["partial_sha256"]: raise InputContractError("partial record payload SHA differs from its binding")
    v = verify_run_references(_one_family_view(d), archive, registered=registered, current_source_binding=current_source_binding)
    return dict(ok=bool(v.get("ok")), family=d["family"], n_pseudo=v.get("n_pseudo"), partial_sha256=d["binding"]["partial_sha256"], context_scope=v.get("context_scope"), registered_context_ok=v.get("registered_context_ok"))


# --------------------------------------------------------------------------------------------------------------------------------------------- combiner
def _common_identity(d: dict) -> dict:
    b = d["binding"]
    return dict(engine_version=d["engine_version"], mode=d["mode"], registry_sha256=d["registry_sha256"], manifest_sha256=d["manifest_sha256"], w2_context_sha256=d["w2_context_sha256"], w2_asset_sha256=d["w2_asset_sha256"],
                twelve_assets_sha256=b.get("twelve_assets_sha256"), twelve_assets_intake=b.get("twelve_assets_intake"), source_binding={k: b.get(k) for k in _COMMON_BINDING}, thresholds=d["thresholds"], campaign=d.get("campaign"),
                twelve_manifest_asset=d["fingerprints"]["at_gate"].get("twelve_manifest_asset"), registry_ref=d["archive_refs"].get("registry"), w2_scope=d["w2_context_ref"].get("scope"), pseudo_dependency=d["binding"]["partial_dependencies"].get("pseudo"), schema=d["schema"])


def combine_family_partials(reg: GridRegistry, man: ConfigurationManifest, partials: Sequence[dict], archive: Archive, *, registered: Optional[dict] = None, verify_references: bool = True) -> RunManifest:
    """Combine exactly one verified partial per registered family into the sealed calibration record (RunManifest, kind 'sealed_calibration'). The archive must already hold
    every record the partials reference (merge_archives for partials produced in other processes). Aggregation per pseudo: any_family_truth over the families' eligible
    truths; Wilson over the fixed n; registered thresholds (calibration.calibrate) — identical to run_first_wave."""
    reg.validate(); man.validate()
    if man.registry_sha256 != reg.registry_sha256: raise InputContractError("manifest not bound to the registry")
    if not isinstance(partials, (list, tuple)) or not partials: raise InputContractError("no partials")
    by_fam: Dict[str, dict] = {}
    for d in partials:
        d = ser.from_jsonable(ser.to_jsonable(d)); _check_partial_shape(d)
        if _payload_sha(d) != d["binding"]["partial_sha256"]: raise InputContractError(f"partial {d.get('family')}: payload SHA differs from its binding")
        fam = d["family"]
        if fam in by_fam: raise InputContractError(f"duplicate partial for family {fam}")
        if fam not in reg.surviving: raise InputContractError(f"partial for a family that is not registered: {fam}")
        by_fam[fam] = d
    order = list(reg.surviving)
    if set(by_fam) != set(order): raise InputContractError(f"the combiner requires exactly one partial per registered family {order}; missing {sorted(set(order) - set(by_fam))}")
    first = by_fam[order[0]]; ci0 = _common_identity(first)
    for fam in order[1:]:
        ci = _common_identity(by_fam[fam]); diff = sorted(k for k in ci0 if ci0[k] != ci.get(k))
        if diff: raise InputContractError(f"partials do not share the common identity: family {fam} differs from {order[0]} in {diff}")
    if ci0["engine_version"] != __version__ or ci0["source_binding"] != {k: binding_manifest().get(k) for k in _COMMON_BINDING}: raise InputContractError("partials were produced by a different source binding than the combining process")
    if ci0["mode"] == "official":
        if ci0["thresholds"]["pseudo"]["n"] != RULES.n_pseudo: raise InputContractError(f"official combination requires n_pseudo={RULES.n_pseudo}")
        if not isinstance(ci0["campaign"], dict): raise InputContractError("official partials require a shared campaign identity")
    for fam, d in by_fam.items():
        if d["sizes"] != list(reg.surviving[fam]): raise InputContractError(f"partial {fam}: sizes differ from the registry's surviving sizes")
        if d["binding"]["partial_dependencies"].get("sizes") != {fam: sorted(reg.surviving[fam])} or d["binding"]["partial_dependencies"].get("family") != fam: raise InputContractError(f"partial {fam}: dependencies do not describe this family")
        if fam == "E1" and any(k.startswith("twelve:") for k in d["fingerprints"]["at_gate"]): raise InputContractError("E1 partial carries 12-position inputs")
        if fam != "E1" and ci0["mode"] == "official" and not all(f"twelve:{fam}/{s}" in d["fingerprints"]["at_gate"] for s in reg.surviving[fam]): raise InputContractError(f"official partial {fam} lacks the 12-position inputs")
        if ci0["mode"] == "official" and d["gate"].get("mode") != "official": raise InputContractError(f"partial {fam}: gate mode is not official")
        if ci0["mode"] == "official" and fam != "E1" and d["plan_objects"].get("twelve_shares_first_wave") is not True: raise InputContractError(f"partial {fam}: official partial must carry the first-wave plan objects in the 12-position views")
    n = ci0["thresholds"]["pseudo"]["n"]; ps = ci0["thresholds"]["pseudo"]
    rm = RunManifest(__version__, ci0["mode"], ci0["registry_sha256"], ci0["manifest_sha256"], ci0["w2_context_sha256"], ci0["w2_asset_sha256"], binding=dict(binding_manifest(), twelve_assets_sha256=ci0["twelve_assets_sha256"], twelve_assets_intake=ci0["twelve_assets_intake"]))
    rm.thresholds = ser.from_jsonable(ser.to_jsonable(ci0["thresholds"]))
    # fingerprints in the single-process order: twelve asset, parents by family, cases by family, twelve inputs by family
    def union(which):
        d = {}
        if ci0["twelve_manifest_asset"] is not None: d["twelve_manifest_asset"] = by_fam[order[0]]["fingerprints"][which]["twelve_manifest_asset"]
        for fam in order: d[fam] = by_fam[fam]["fingerprints"][which][fam]
        for fam in order:
            for k, v in by_fam[fam]["fingerprints"][which].items():
                if k != fam and k != "twelve_manifest_asset" and not k.startswith("twelve:"): d[k] = v
        for fam in order:
            for k, v in by_fam[fam]["fingerprints"][which].items():
                if k.startswith("twelve:"): d[k] = v
        return d
    fp0 = union("at_gate"); rm.fingerprints = dict(at_gate=fp0)
    for fam in order: rm.gates[fam] = ser.from_jsonable(ser.to_jsonable(by_fam[fam]["gate"]))
    rm.binding["sealed_dependencies"] = dict(mode=ci0["mode"], engine_version=__version__, registry_sha256=ci0["registry_sha256"], manifest_sha256=ci0["manifest_sha256"], w2_context_sha256=ci0["w2_context_sha256"], w2_asset_sha256=ci0["w2_asset_sha256"], twelve_assets_sha256=ci0["twelve_assets_sha256"], twelve_assets_intake=ci0["twelve_assets_intake"],
                                             families=sorted(order), sizes={f: sorted(reg.surviving[f]) for f in order}, require_all_families=True, pseudo=dict(n=n, sha256_T1=ps["sha256_T1"], sha256_T2=ps["sha256_T2"]), source_binding=binding_manifest(), fingerprints_at_gate=fp0)
    rm.binding["combiner"] = dict(schema="d4c1_combiner_v1", partials={fam: dict(partial_sha256=by_fam[fam]["binding"]["partial_sha256"], partial_file_sha256=by_fam[fam]["binding"].get("partial_file_sha256"), partial_ref=by_fam[fam]["binding"].get("partial_ref")) for fam in order},
                                  campaign=ci0["campaign"], target_commitment=ci0["thresholds"]["target_commitment"], aggregation="per pseudo: any_family_truth over the families' eligible truths (technical_fail > True > unknown > False); Wilson upper(c+u, n) on the fixed n; registered support / strong thresholds",
                                  scope="combined from one verified partial per registered family; content-identical to the single-process calibrate_sealed record apart from this provenance block")
    ctx_cases = sorted(k for fam in order for k in by_fam[fam]["w2_context_ref"]["cases"]); ctx_ref = dict(asset_sha256=ci0["w2_asset_sha256"], context_sha256=ci0["w2_context_sha256"], scope=ci0["w2_scope"], cases=ctx_cases)
    elig, core_only, any_case, statuses = [], [], [], []
    for i in range(n):
        st_i = {fam: ser.from_jsonable(ser.to_jsonable(by_fam[fam]["per_pseudo_status"][i])) for fam in order}
        for fam in order:
            for key in by_fam[fam]["per_pseudo_manifest_keys"][i]:
                if key not in rm.archive_refs: rm.archive_refs[key] = ser.from_jsonable(ser.to_jsonable(by_fam[fam]["archive_refs"][key]))
        elig.append({lvl: any_family_truth([st_i[fam]["eligible_truths"][lvl] for fam in order]) for lvl in ("support", "strong")})
        core_only.append({lvl: any_family_truth([st_i[fam]["core_truths"][lvl] for fam in order]) for lvl in ("support", "strong")})
        any_case.append({lvl: any_family_truth([dg[lvl] for fam in order for dg in by_fam[fam]["per_pseudo_diagnostics"][i].values()] or [UNKNOWN]) for lvl in ("support", "strong")})
        statuses.append(st_i)
    rm.fingerprints["at_end"] = union("at_end")
    if rm.fingerprints["at_end"] != fp0: raise InputContractError("partial fingerprints at_end differ from at_gate")
    missing = [dict(where=f"pseudo[{i}]", family=fam, reason="triggered 12-position stage not evaluated") for i, st in enumerate(statuses) for fam, fs in st.items() if fs["expand_family"] and fs["twelve"] is None]
    complete = not missing
    rm.branch_completeness = dict(all_registered_families=True, missing_branches=missing, note="procedure completeness only: unresolved estimates after a fully executed procedure stay 'unknown' in the Wilson aggregation")
    for lvl, thr in (("support", RULES.usable_support), ("strong", RULES.usable_strong)):
        s = calibrate([t[lvl] for t in elig], thr, expected_n=n)
        s.reason = ("scope: ELIGIBLE family truths via the common threshold evaluator (parent required quantities -> position branch -> coordinator -> 12-position stage when supplied); " + ("all registered families and every triggered 12-position stage (target and every pseudo) evaluated" if complete else "NOT the registered full-procedure calibration: " + (f"12-position stage not integrated for {len(missing)} triggered branch(es) (target/pseudo; see branch_completeness)" if missing else "")))
        s.w2_context = dict(ctx_ref)
        c_only = calibrate([t[lvl] for t in core_only], thr, expected_n=n); c_only.reason = "core_only diagnostic: 3-position family core without position eligibility (never used for 'usable')"
        c_any = calibrate([t[lvl] for t in any_case], thr, expected_n=n); c_any.reason = "any_case_core_diagnostic: OR of per-size standalone cores (NOT the registered family calibration; never used for 'usable')"
        rm.calibration[lvl] = dict(summary=s.as_dict(), truths=[t[lvl] for t in elig], core_only=dict(summary=c_only.as_dict(), truths=[t[lvl] for t in core_only]), any_case_core_diagnostic=dict(summary=c_any.as_dict(), truths=[t[lvl] for t in any_case]), full_procedure=complete)
    rm.per_pseudo_family_status = statuses
    rm.archive_refs["registry"] = ser.from_jsonable(ser.to_jsonable(ci0["registry_ref"]))
    if ArchiveRef(**rm.archive_refs["registry"]).identity.get("registry_sha256") != reg.registry_sha256: raise InputContractError("partials' registry reference differs from the combining registry")
    rm.binding["run_manifest_sha256"] = rm.payload_sha()
    if verify_references:
        from .run_reader import verify_run_references
        v = verify_run_references(rm.as_dict(), archive, registered=registered, current_source_binding=True)
        if not v.get("ok"): raise InputContractError("combined record not verified by the run reader")
    ref = archive.put("transition", ser.from_jsonable(rm.as_dict()), dict(kind=SEALED_KIND, payload_sha256=rm.binding["run_manifest_sha256"])); rm.binding["run_manifest_file_sha256"] = ref.sha256; rm.binding["run_manifest_ref"] = ref.as_dict()
    archive.flush()
    return rm


def strip_provenance(rm_dict: dict) -> dict:
    """Content of a sealed record without the combiner provenance and the self-referencing binding entries (equivalence comparisons)."""
    d = ser.from_jsonable(ser.to_jsonable(rm_dict)); d["binding"] = {k: v for k, v in d["binding"].items() if k not in ("combiner", "run_manifest_sha256", "run_manifest_file_sha256", "run_manifest_ref")}; return d


def load_combined_sealed_record(archive: Archive, ref: dict, registered: Optional[dict] = None) -> dict:
    """Phase E reader for a COMBINED sealed calibration: global kind + payload (load_sealed_record), combiner provenance (every partial resolves with its recorded SHA, same
    commitment / pseudo columns / campaign, statuses copied verbatim), then the full reference chain with the current source binding. A partial reference is rejected."""
    from .calibration_first import load_sealed_record
    from .run_reader import verify_run_references
    d = load_sealed_record(archive, ref); comb = (d.get("binding") or {}).get("combiner")
    if not isinstance(comb, dict) or comb.get("schema") != "d4c1_combiner_v1": raise InputContractError("sealed record carries no combiner provenance (not a combined calibration)")
    fams = (d["binding"].get("sealed_dependencies") or {}).get("families") or []
    if sorted(comb.get("partials") or {}) != sorted(fams): raise InputContractError("combiner provenance family set differs from the sealed dependencies")
    if comb.get("target_commitment") != d["thresholds"]["target_commitment"]: raise InputContractError("combiner provenance commitment differs from the sealed record")
    for fam, p in comb["partials"].items():
        pr = load_partial_record(archive, p["partial_ref"])
        if pr["binding"]["partial_sha256"] != p["partial_sha256"] or pr["family"] != fam: raise InputContractError(f"partial {fam}: provenance SHA / family mismatch")
        if pr["thresholds"] != d["thresholds"] or pr.get("campaign") != comb.get("campaign"): raise InputContractError(f"partial {fam}: thresholds / campaign differ from the combined record")
        if pr["mode"] != d["mode"] or pr["w2_context_sha256"] != d["w2_context_sha256"] or pr["registry_sha256"] != d["registry_sha256"]: raise InputContractError(f"partial {fam}: identity differs from the combined record")
        if any(st.get(fam) != pr["per_pseudo_status"][i] for i, st in enumerate(d["per_pseudo_family_status"])): raise InputContractError(f"partial {fam}: per-pseudo status is not a verbatim copy in the combined record")
    body = {k: v for k, v in d.items() if k not in ("_sha256", "_ref")}
    v = verify_run_references(body, archive, registered=registered, current_source_binding=True)
    if not v.get("ok"): raise InputContractError("combined sealed record reference chain not verified")
    d["_verification"] = dict(v, combined=True, partials={fam: p["partial_sha256"] for fam, p in comb["partials"].items()}); return d
