# -*- coding: utf-8 -*-
"""D4C-2a: deterministic pseudo-ROW-RANGE sub-partials of one family and their combiner (audit D4C2-probe §6 / decision GO deterministic_pseudo_range_resume_design_and_small_tests).

calibrate_family_subpartial(..., row_range=(start, stop))  — d4c1_partial.calibrate_family_partial on the GLOBAL rows [start, stop) of the FULL registered pseudo columns: the
    same per-row procedure, the same archived records (parent / plan / position sources / 12-position Result carry the GLOBAL pseudo_index), the global column identity (n and
    the SHA of the whole columns) plus the slice identity (slice SHAs); schema family_subpartial_calibration_v1, archive identity kind 'family_subpartial_calibration' with the
    row range. A sub-partial is not a family partial: it carries binding.subpartial_dependencies (not partial_dependencies), so the family partial readers / combiner reject it.
combine_family_subpartials(reg, man, subs, archive)  — EXACTLY the sub-partials that tile [0, n) of one family (sorted by start; a gap, an overlap, a duplicate range, a range
    outside [0, n), a different family / campaign / commitment / global column identity / source binding / mode / registry / W2 context / twelve asset / sizes / fingerprints /
    plan-object summary / gate identity is rejected; the concatenated slices must re-hash to the global column SHAs) -> the family partial record (schema family_partial_calibration_v1)
    whose content is IDENTICAL to the single-process calibrate_family_partial record over the whole columns (per-pseudo statuses / diagnostics concatenated in row order; the
    per-pseudo manifest keys re-derived with the single-process first-trigger rule; archive_refs in the single-process insertion order) apart from binding['subpartials']
    (provenance: ranges, sub-partial SHAs, gates); strip_subpartial_provenance gives the content for equivalence comparisons. The combined partial is verified through the run
    reader (verify_partial_record) on the merged archive before it is archived under the family-partial identity, so d4c1_partial.combine_family_partials consumes it unchanged.
verify_subpartial_record(d, archive, ...)  — the one-row-range transient view through run_reader.verify_run_references with the global row offset (pseudo_index_offset).
plan_row_ranges(n, chunk)  — the deterministic tiling [0, chunk), [chunk, 2 chunk), ... of the fixed n (the set 1..n is never changed; chunk order changes nothing: the
    bootstrap plans are registered objects, the per-row evaluation has no carried state).
Resume: every sub-partial is a durable unit (its own output directory + archive); a lost runtime loses at most the open range, which is re-run as a new attempt; the previously
published sub-partials are re-verified (payload SHA + reader) by the combiner. Nothing here aggregates: no c/u/n, Wilson, usable or label."""
from __future__ import annotations
from typing import Dict, List, Optional, Sequence, Tuple
import hashlib
import numpy as np
from .errors import InputContractError
from .rules_config import RULES
from .grid_registry import GridRegistry
from .grid_manifest import ConfigurationManifest
from .archive import Archive, ArchiveRef
from .checkpoint import binding_manifest
from .d4c1_partial import (FamilyPartialRecord, calibrate_family_partial, _payload_sha, _is_sha, _COMMON_BINDING, PARTIAL_SCHEMA, PARTIAL_KIND, SUBPARTIAL_SCHEMA, SUBPARTIAL_KIND)
from . import serialization as ser
from . import __version__

COMBINER_SCHEMA = "d4c1_subpartial_combiner_v1"
_GATE_ENV_KEYS = ("python", "numpy", "scipy", "healpy", "pot", "camb")


def plan_row_ranges(n: int, chunk: int) -> List[Tuple[int, int]]:
    if not isinstance(n, int) or isinstance(n, bool) or n < 1 or not isinstance(chunk, int) or isinstance(chunk, bool) or chunk < 1: raise InputContractError("n and chunk must be positive ints")
    return [(a, min(a + chunk, n)) for a in range(0, n, chunk)]


def calibrate_family_subpartial(reg, man, family, cases, w2_context, expected_context_sha256, pseudo_T1, pseudo_T2, archive: Archive, target_commitment: str, *, row_range: Tuple[int, int], mode: str = "smoke", campaign: Optional[dict] = None,
                                twelve_inputs: Optional[dict] = None, twelve_assets=None, expected_twelve_assets_sha256: Optional[str] = None, twelve_assets_receipt: Optional[str] = None) -> FamilyPartialRecord:
    """pseudo_T1 / pseudo_T2: the FULL registered columns (official mode: n == RULES.n_pseudo); row_range = (start, stop), 0 <= start < stop <= n."""
    rec = calibrate_family_partial(reg, man, family, cases, w2_context, expected_context_sha256, pseudo_T1, pseudo_T2, archive, target_commitment, mode=mode, campaign=campaign, twelve_inputs=twelve_inputs, twelve_assets=twelve_assets,
                                   expected_twelve_assets_sha256=expected_twelve_assets_sha256, twelve_assets_receipt=twelve_assets_receipt, _rows=tuple(row_range))
    if rec.schema != SUBPARTIAL_SCHEMA or rec.kind != SUBPARTIAL_KIND or rec.rows is None: raise InputContractError("sub-partial record not issued")
    return rec


# --------------------------------------------------------------------------------------------------------------------------------------------- readers
def _sha_cols(v) -> str: return hashlib.sha256(np.ascontiguousarray(np.asarray(v, float)).tobytes()).hexdigest()


def check_subpartial_shape(d: dict):
    if not isinstance(d, dict) or d.get("schema") != SUBPARTIAL_SCHEMA or d.get("kind") != SUBPARTIAL_KIND: raise InputContractError("not a family sub-partial calibration record")
    thr = d.get("thresholds") or {}; ps = thr.get("pseudo") or {}; rows = d.get("rows") or {}
    if thr.get("target") is not None or not _is_sha(thr.get("target_commitment")): raise InputContractError("sub-partial must carry no target and a target commitment")
    n = ps.get("n"); a, b = (rows.get("start"), rows.get("stop"))
    if not isinstance(n, int) or isinstance(n, bool) or n < 1 or not all(isinstance(v, int) and not isinstance(v, bool) for v in (a, b)) or not (0 <= a < b <= n): raise InputContractError("sub-partial row range / n malformed")
    if ps.get("rows") != [a, b] or rows.get("n_total") != n or rows.get("n_rows") != b - a or ps.get("n_rows") != b - a: raise InputContractError("sub-partial row range disagrees between thresholds.pseudo and rows")
    m = b - a
    if len(d.get("per_pseudo_status") or []) != m or len(d.get("per_pseudo_diagnostics") or []) != m or len(d.get("per_pseudo_manifest_keys") or []) != m: raise InputContractError("sub-partial per-pseudo inventories do not match the row range")
    if len(ps.get("T1") or []) != m or len(ps.get("T2") or []) != m or _sha_cols(ps["T1"]) != ps.get("slice_sha256_T1") or _sha_cols(ps["T2"]) != ps.get("slice_sha256_T2"): raise InputContractError("sub-partial pseudo slice differs from its recorded SHA / length")
    if rows.get("slice_sha256_T1") != ps.get("slice_sha256_T1") or rows.get("slice_sha256_T2") != ps.get("slice_sha256_T2") or rows.get("global_sha256_T1") != ps.get("sha256_T1") or rows.get("global_sha256_T2") != ps.get("sha256_T2") or not (_is_sha(ps.get("sha256_T1")) and _is_sha(ps.get("sha256_T2"))): raise InputContractError("sub-partial column identities disagree")
    fam = d.get("family")
    if any(s.get("family") != fam for s in d["per_pseudo_status"]): raise InputContractError("sub-partial status family differs from the record family")
    if "calibration" in d or "families" in d or "cases" in d or "partial_dependencies" in (d.get("binding") or {}): raise InputContractError("a sub-partial must not carry aggregated calibration / target results / family-partial dependencies")
    sd = (d.get("binding") or {}).get("subpartial_dependencies") or {}
    if sd.get("families") != [fam] or sd.get("require_all_families") is not False or sd.get("target_commitment") != thr["target_commitment"] or sd.get("rows") != [a, b] or (sd.get("pseudo") or {}).get("n") != n or (sd.get("pseudo") or {}).get("sha256_T1") != ps["sha256_T1"] or (sd.get("pseudo") or {}).get("sha256_T2") != ps["sha256_T2"] or sd.get("slice_sha256_T1") != ps["slice_sha256_T1"] or sd.get("slice_sha256_T2") != ps["slice_sha256_T2"]: raise InputContractError("sub-partial dependencies do not describe this row range")
    if d.get("fingerprints", {}).get("at_gate") != d.get("fingerprints", {}).get("at_end"): raise InputContractError("sub-partial fingerprints at_gate != at_end")
    po = d.get("plan_objects")
    if not isinstance(po, dict) or po.get("stable_after") is not True or po.get("first_wave_shared") is not True or po.get("twelve_shared") is not True: raise InputContractError("sub-partial plan-object record missing or not stable / shared")


def load_subpartial_record(archive: Archive, ref: dict) -> dict:
    r = ArchiveRef(**ref); d = ser.from_jsonable(archive.get(r))
    if r.kind != "transition" or r.identity.get("kind") != SUBPARTIAL_KIND: raise InputContractError("reference is not a family sub-partial calibration record")
    check_subpartial_shape(d)
    if _payload_sha(d) != d["binding"]["partial_sha256"] or r.identity.get("payload_sha256") != d["binding"]["partial_sha256"] or r.identity.get("family") != d["family"] or r.identity.get("target_commitment") != d["thresholds"]["target_commitment"] or r.identity.get("rows") != [d["rows"]["start"], d["rows"]["stop"]]: raise InputContractError("sub-partial record payload SHA / identity mismatch")
    return d


def _one_range_view(d: dict) -> dict:
    """Transient RunManifest-shaped view of ONE sub-partial (the slice as the view's pseudo columns; the archived records carry the global index -> verified with the offset)."""
    from .d4c1_partial import _one_family_view
    v = ser.from_jsonable(ser.to_jsonable(d)); ps = v["thresholds"]["pseudo"]; m = v["rows"]["n_rows"]
    v["schema"], v["kind"] = PARTIAL_SCHEMA, PARTIAL_KIND
    v["thresholds"]["pseudo"] = dict(n=m, shape=[m], sha256_T1=ps["slice_sha256_T1"], sha256_T2=ps["slice_sha256_T2"], T1=ps["T1"], T2=ps["T2"], dtype="float64", note="transient slice view")
    sd = dict(v["binding"].pop("subpartial_dependencies")); sd.pop("rows"); sd.pop("slice_sha256_T1"); sd.pop("slice_sha256_T2"); sd["pseudo"] = dict(n=m, sha256_T1=ps["slice_sha256_T1"], sha256_T2=ps["slice_sha256_T2"]); v["binding"]["partial_dependencies"] = sd
    v.pop("rows"); v["binding"]["partial_sha256"] = _payload_sha(v)
    return _one_family_view(v)


def verify_subpartial_record(d: dict, archive: Archive, registered: Optional[dict] = None, current_source_binding: bool = False) -> dict:
    from .run_reader import verify_run_references
    check_subpartial_shape(d)
    if _payload_sha(d) != d["binding"]["partial_sha256"]: raise InputContractError("sub-partial record payload SHA differs from its binding")
    v = verify_run_references(_one_range_view(d), archive, registered=registered, current_source_binding=current_source_binding, pseudo_index_offset=int(d["rows"]["start"]))
    return dict(ok=bool(v.get("ok")), family=d["family"], rows=[d["rows"]["start"], d["rows"]["stop"]], n_rows=v.get("n_pseudo"), partial_sha256=d["binding"]["partial_sha256"], context_scope=v.get("context_scope"), registered_context_ok=v.get("registered_context_ok"))


# --------------------------------------------------------------------------------------------------------------------------------------------- combiner
def gate_identity(g: dict) -> dict:
    diag = g.get("diagnostics") or {}; env = diag.get("env") or {}
    return dict(mode=g.get("mode"), passed=g.get("passed"), required_failures=list(g.get("required_failures") or []), registered=diag.get("registered"), rules_binding=diag.get("rules_binding"), profile_failures=diag.get("profile_failures"), version_mismatch=diag.get("version_mismatch"),
                blas_threads_ok=diag.get("blas_threads_ok"), environment_source=diag.get("environment_source"), env_versions={k: env.get(k) for k in _GATE_ENV_KEYS}, scope=diag.get("scope"))


def _common_identity(d: dict) -> dict:
    b = d["binding"]; sd = b["subpartial_dependencies"]; ps = d["thresholds"]["pseudo"]
    return dict(engine_version=d["engine_version"], mode=d["mode"], family=d["family"], sizes=d["sizes"], registry_sha256=d["registry_sha256"], manifest_sha256=d["manifest_sha256"], w2_context_sha256=d["w2_context_sha256"], w2_asset_sha256=d["w2_asset_sha256"],
                twelve_assets_sha256=b.get("twelve_assets_sha256"), twelve_assets_intake=b.get("twelve_assets_intake"), source_binding={k: b.get(k) for k in _COMMON_BINDING}, target_commitment=d["thresholds"]["target_commitment"], campaign=d.get("campaign"),
                pseudo_global=dict(n=ps["n"], shape=ps["shape"], sha256_T1=ps["sha256_T1"], sha256_T2=ps["sha256_T2"]), fingerprints_at_gate=d["fingerprints"]["at_gate"], plan_objects=d["plan_objects"], w2_context_ref=d["w2_context_ref"], gate=gate_identity(d["gate"]),
                registry_ref=d["archive_refs"].get("registry"), dependencies={k: v for k, v in sd.items() if k not in ("rows", "slice_sha256_T1", "slice_sha256_T2")}, scope_kind=d["kind"])


def combine_family_subpartials(reg: GridRegistry, man: ConfigurationManifest, subs: Sequence[dict], archive: Archive, *, registered: Optional[dict] = None, verify_references: bool = True) -> FamilyPartialRecord:
    """Exactly the sub-partials tiling [0, n) of ONE family -> the family partial record (archived under the family-partial identity on the given archive, which must already hold every
    sub-partial's records: merge_archives first)."""
    reg.validate(); man.validate()
    if man.registry_sha256 != reg.registry_sha256: raise InputContractError("manifest not bound to the registry")
    if not isinstance(subs, (list, tuple)) or not subs: raise InputContractError("no sub-partials")
    recs = []
    for d in subs:
        d = ser.from_jsonable(ser.to_jsonable(d)); check_subpartial_shape(d)
        if _payload_sha(d) != d["binding"]["partial_sha256"]: raise InputContractError(f"sub-partial {d.get('family')} rows {d['rows']['start']}..{d['rows']['stop']}: payload SHA differs from its binding")
        recs.append(d)
    ci0 = _common_identity(recs[0]); fam = ci0["family"]
    if fam not in reg.surviving: raise InputContractError(f"sub-partials of a family that is not registered: {fam}")
    if recs[0]["sizes"] != list(reg.surviving[fam]): raise InputContractError(f"sub-partial {fam}: sizes differ from the registry's surviving sizes")
    for d in recs[1:]:
        ci = _common_identity(d); diff = sorted(k for k in ci0 if ci0[k] != ci.get(k))
        if diff: raise InputContractError(f"sub-partials do not share the common identity: rows {d['rows']['start']}..{d['rows']['stop']} differ from rows {recs[0]['rows']['start']}..{recs[0]['rows']['stop']} in {diff}")
    if ci0["engine_version"] != __version__ or ci0["source_binding"] != {k: binding_manifest().get(k) for k in _COMMON_BINDING}: raise InputContractError("sub-partials were produced by a different source binding than the combining process")
    if ci0["gate"]["passed"] is not True or ci0["gate"]["required_failures"]: raise InputContractError("sub-partial gate not passed")
    n = ci0["pseudo_global"]["n"]
    if ci0["mode"] == "official":
        if n != RULES.n_pseudo: raise InputContractError(f"official combination requires n_pseudo={RULES.n_pseudo}")
        if not isinstance(ci0["campaign"], dict): raise InputContractError("official sub-partials require a shared campaign identity")
    # ---- the tiling of [0, n): sorted by start; contiguous; no duplicate / overlap / gap
    recs.sort(key=lambda d: (d["rows"]["start"], d["rows"]["stop"])); ranges = [(d["rows"]["start"], d["rows"]["stop"]) for d in recs]
    if len(set(ranges)) != len(ranges): raise InputContractError(f"duplicate sub-partial row range(s): {sorted(r for r in set(ranges) if ranges.count(r) > 1)}")
    pos = 0
    for a, b in ranges:
        if a < pos: raise InputContractError(f"sub-partial row ranges overlap at row {a} (previous range ends at {pos})")
        if a > pos: raise InputContractError(f"sub-partial row ranges leave a gap: rows {pos}..{a} missing")
        pos = b
    if pos != n: raise InputContractError(f"sub-partial row ranges end at {pos} but n = {n} (rows {pos}..{n} missing)")
    T1 = [float(v) for d in recs for v in d["thresholds"]["pseudo"]["T1"]]; T2 = [float(v) for d in recs for v in d["thresholds"]["pseudo"]["T2"]]
    if len(T1) != n or _sha_cols(T1) != ci0["pseudo_global"]["sha256_T1"] or _sha_cols(T2) != ci0["pseudo_global"]["sha256_T2"]: raise InputContractError("the concatenated pseudo slices do not re-hash to the global column SHAs")
    # ---- the family partial content in the single-process order
    rec = FamilyPartialRecord(PARTIAL_SCHEMA, PARTIAL_KIND, __version__, ci0["mode"], fam, ci0["registry_sha256"], ci0["manifest_sha256"], ci0["w2_context_sha256"], ci0["w2_asset_sha256"], sizes=list(recs[0]["sizes"]),
                              binding=dict(binding_manifest(), twelve_assets_sha256=ci0["twelve_assets_sha256"], twelve_assets_intake=ci0["twelve_assets_intake"]))
    rec.thresholds = dict(target=None, target_commitment=ci0["target_commitment"], pseudo=dict(n=n, shape=ci0["pseudo_global"]["shape"], sha256_T1=ci0["pseudo_global"]["sha256_T1"], sha256_T2=ci0["pseudo_global"]["sha256_T2"], T1=T1, T2=T2, dtype="float64", note="full-precision pseudo threshold columns (float64 -> JSON repr round-trips exactly)"))
    rec.campaign = ser.from_jsonable(ser.to_jsonable(ci0["campaign"])); rec.fingerprints = dict(at_gate=ser.from_jsonable(ser.to_jsonable(ci0["fingerprints_at_gate"]))); rec.gate = ser.from_jsonable(ser.to_jsonable(recs[0]["gate"]))
    rec.binding["partial_dependencies"] = ser.from_jsonable(ser.to_jsonable(dict(ci0["dependencies"], source_binding=binding_manifest())))
    rec.w2_context_ref = ser.from_jsonable(ser.to_jsonable(ci0["w2_context_ref"]))
    seen = set(); keys_all = []
    for d in recs:
        for i, added in enumerate(d["per_pseudo_manifest_keys"]):
            st = d["per_pseudo_status"][i]; plan_keys = []
            if st.get("expand_family"):
                for key in added:
                    if key not in d["archive_refs"]: raise InputContractError(f"sub-partial rows {d['rows']['start']}..{d['rows']['stop']}: manifest key {key} added by a pseudo but not archived")
            for k in added:                                                                                         # single-process rule: every triggering pseudo lists its required keys; the archive ref is inserted at the FIRST (global order) occurrence
                if k not in seen: rec.archive_refs[k] = ser.from_jsonable(ser.to_jsonable(d["archive_refs"][k])); seen.add(k)
            keys_all.append(list(added))
            rec.per_pseudo_status.append(ser.from_jsonable(ser.to_jsonable(st))); rec.per_pseudo_diagnostics.append(ser.from_jsonable(ser.to_jsonable(d["per_pseudo_diagnostics"][i])))
    rec.per_pseudo_manifest_keys = keys_all
    for d in recs:
        for k, v in d["archive_refs"].items():
            if k == "registry": continue
            if k not in rec.archive_refs: raise InputContractError(f"sub-partial rows {d['rows']['start']}..{d['rows']['stop']}: archived key {k} is not attributed to any triggering pseudo")
            if rec.archive_refs[k] != v: raise InputContractError(f"sub-partials disagree on the archived manifest {k}")
    rec.plan_objects = ser.from_jsonable(ser.to_jsonable(ci0["plan_objects"])); rec.fingerprints["at_end"] = ser.from_jsonable(ser.to_jsonable(ci0["fingerprints_at_gate"]))
    if ci0["registry_ref"] is None: raise InputContractError("sub-partials carry no registry reference")
    rec.archive_refs["registry"] = ser.from_jsonable(ser.to_jsonable(ci0["registry_ref"]))
    if ArchiveRef(**rec.archive_refs["registry"]).identity.get("registry_sha256") != reg.registry_sha256: raise InputContractError("sub-partials' registry reference differs from the combining registry")
    rec.binding["subpartials"] = dict(schema=COMBINER_SCHEMA, n=n, ranges=[list(r) for r in ranges], subpartials=[dict(rows=[d["rows"]["start"], d["rows"]["stop"]], partial_sha256=d["binding"]["partial_sha256"], partial_file_sha256=d["binding"].get("partial_file_sha256"), partial_ref=d["binding"].get("partial_ref"), gate=gate_identity(d["gate"])) for d in recs],
                                      rule="rows [0, n) tiled exactly once by sorted contiguous ranges; per-pseudo statuses / diagnostics / manifest keys concatenated in row order; archive refs inserted at the first triggering pseudo in global order (registry last); content identical to the single-process family partial apart from this block")
    rec.binding["partial_sha256"] = rec.payload_sha()
    if verify_references:
        from .d4c1_partial import verify_partial_record
        v = verify_partial_record(rec.as_dict(), archive, registered=registered, current_source_binding=True)
        if not v.get("ok"): raise InputContractError("combined family partial not verified by the run reader")
    ref = archive.put("transition", ser.from_jsonable(rec.as_dict()), dict(kind=PARTIAL_KIND, family=fam, payload_sha256=rec.binding["partial_sha256"], target_commitment=ci0["target_commitment"])); rec.binding["partial_file_sha256"] = ref.sha256; rec.binding["partial_ref"] = ref.as_dict()
    archive.flush()
    return rec


def strip_subpartial_provenance(d: dict) -> dict:
    """Content of a family partial without the sub-partial provenance and the self-referencing binding entries (equivalence comparisons with a single-process partial)."""
    d = ser.from_jsonable(ser.to_jsonable(d)); d["binding"] = {k: v for k, v in d["binding"].items() if k not in ("subpartials", "partial_sha256", "partial_file_sha256", "partial_ref")}; return d
