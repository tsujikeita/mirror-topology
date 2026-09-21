# -*- coding: utf-8 -*-
"""D4-4 (v2; audit RD4T2-A/B/C): reuse contract for an archived run (run manifest + content-addressed archive). Before any record of a run is REUSED, the reference chain is
resolved, byte-verified (Archive.get) AND semantically re-verified:
  root: run manifest payload SHA; fingerprints at_gate == at_end; (optional) source binding == the current process (current_source_binding=True) or a caller-supplied one;
  registry: restored with registry_from_dict (internal validation) and its SHA == manifest == the trusted registry SHA when given;
  cases: result_ref resolves and matches the family's StageTransition (identity / SHA / technical status); manifest truths + position status == record; the record's own
         evidence.diagnostic_ref (if any) MUST be present in the manifest and resolve (family / size / kind);
  families: family_core record == manifest (truths, Q_point, technical status, display label; per_config count == 3 x number of surviving sizes evaluated);
         required references derived from the family STATE: expand_family True -> every surviving size has a required manifest SHA and a resolvable twelve_manifest record whose
         RESTORED payload passes the structural checks and equals the SHA; expand_family False / E1 / technical_fail -> required_manifests must be None for every size and no
         reference is demanded; a non-expanded family with a SHA, or an expanded family with None, is inconsistent;
         twelve_stage evaluated -> twelve_family_core resolves with 36 matched per_config (and 36 native when present) and, when eligibility is the 12-position mixture, its truths
         == eligible_truths;
  pseudos: len(per_pseudo_family_status) == n pseudo; each status covers the run's families; a twelve_full_result_ref (when present) resolves with the recorded SHA, pseudo_index,
         family and evidence.threshold == the i-th pseudo pair; when 12-position eligibility is claimed the record truths == the status eligible_truths;
  calibration: for support/strong the per-pseudo any-family truth over eligible_truths re-derives calibration[lvl].truths; calibrate() over those truths re-derives the summary
         (c/u/technical, Wilson upper, usable, status); full_procedure == (all registered families and no missing branch);
  W2 context: run asset SHA / context SHA == the REGISTERED values given by the caller (else 'unregistered context', not approved for formal reuse); calibration.summary.w2_context
         SHAs == run SHAs;
  sealed order record (target runs): parent sealed record resolves, its payload SHA and commitment match, order_record.target == thresholds.target, and the target-side
         calibration / per-pseudo status are a verbatim copy of the parent's; parent dependencies (mode, registry, context, source binding) == this run's.
Raises InputContractError on the first inconsistency. Scope: no bank re-evaluation; W2 context objects are compared by registered SHA (formal reuse additionally requires the
registered context object / pre-use gates)."""
from __future__ import annotations
import hashlib
import ast
from typing import Optional
from .errors import InputContractError
from .archive import Archive, ArchiveRef, resolve_transition_archive
from .stage12 import StageTransition, TwelvePositionManifest, _structural_checks, POSITION_STATES
from .calibration import calibrate, any_family_truth
from .rules_config import RULES
from .grid_registry import registry_from_dict
from .grid_manifest import build_configuration_manifest, _integer
from .checkpoint import binding_manifest, verify_family_result_dict
from .coordinator import FamilyExpansionSet
from .threshold_evaluator import derive_outcome, completion_from_full12
from .truth import TECH, UNKNOWN
from .positions import event_ratio_trigger
from .position_state import position_state
import numpy as np
from . import serialization as ser


def _payload_sha(d: dict) -> str:
    body = dict(d); body["binding"] = {k: v for k, v in body["binding"].items() if k not in ("run_manifest_sha256", "run_manifest_file_sha256", "run_manifest_ref")}
    return hashlib.sha256(ser.dumps(body).encode()).hexdigest()


def _get(archive, ref): return ser.from_jsonable(archive.get(ArchiveRef(**ref)))


def verify_run_references(rm: dict, archive: Archive, registered: Optional[dict] = None, current_source_binding: bool = False) -> dict:
    d = ser.from_jsonable(rm); b = d.get("binding") or {}
    d_clean = dict(d); d_clean.pop("_sha256", None); d_clean.pop("_ref", None)
    if _payload_sha(d_clean) != b.get("run_manifest_sha256"): raise InputContractError("run manifest payload SHA differs from its binding")
    fps = d.get("fingerprints") or {}
    if fps.get("at_gate") != fps.get("at_end"): raise InputContractError("run fingerprints at_gate != at_end")
    thr = d.get("thresholds") or {}; ps = thr.get("pseudo") or {}; statuses = d.get("per_pseudo_family_status") or []; cal = d.get("calibration") or {}; bc = d.get("branch_completeness") or {}
    sd = b.get("sealed_dependencies") or {}
    stage = "sealed_target" if "order_record" in b else ("sealed_calibration" if (sd and thr.get("target") is None and thr.get("target_commitment")) else "full")
    # (R2V2-A) stage schema: required contents are never optional
    if stage in ("sealed_calibration", "sealed_target", "full"):
        for lvl in ("support", "strong"):
            if lvl not in cal or not isinstance(cal[lvl].get("summary"), dict) or "truths" not in cal[lvl]: raise InputContractError(f"{stage}: calibration level '{lvl}' missing (a run without stored calibration results is not reusable)")
        if not isinstance(ps.get("n"), int) or ps["n"] < 1 or not statuses: raise InputContractError(f"{stage}: pseudo thresholds / per-pseudo status missing")
    if stage == "sealed_calibration" and (d.get("families") or d.get("cases")): raise InputContractError("sealed calibration must not contain target results")
    if stage in ("sealed_target", "full") and not (d.get("families") and d.get("cases")): raise InputContractError(f"{stage}: target family/case results missing")
    if stage == "sealed_calibration" and thr.get("target") is not None: raise InputContractError("sealed calibration carries a target")
    # (R2V2-A) double source binding: root binding and nested snapshot must agree on every shared field, and (optionally) equal the current process
    root_sb = {k: b.get(k) for k in ("engine_version", "rules_document_sha256", "tables_sha256", "modules", "registered_profile") if k in b}
    if sd:
        nsb = sd.get("source_binding") or {}
        for k in root_sb:
            if nsb.get(k) != root_sb[k]: raise InputContractError(f"root binding and sealed_dependencies.source_binding disagree on {k}")
        if sd.get("mode") != d.get("mode") or sd.get("registry_sha256") != d.get("registry_sha256") or sd.get("manifest_sha256") != d.get("manifest_sha256") or sd.get("w2_context_sha256") != d.get("w2_context_sha256") or sd.get("w2_asset_sha256") != d.get("w2_asset_sha256") or sd.get("twelve_assets_sha256") != b.get("twelve_assets_sha256"): raise InputContractError("sealed_dependencies disagree with the root run fields")
        if (sd.get("pseudo") or {}).get("n") != ps.get("n") or (sd.get("pseudo") or {}).get("sha256_T1") != ps.get("sha256_T1") or (sd.get("pseudo") or {}).get("sha256_T2") != ps.get("sha256_T2"): raise InputContractError("sealed_dependencies pseudo columns disagree with the root thresholds")
        if sd.get("fingerprints_at_gate") != fps.get("at_gate"): raise InputContractError("sealed_dependencies fingerprints disagree with the root fingerprints")
    if current_source_binding:
        cur = binding_manifest()
        for k in ("engine_version", "rules_document_sha256", "tables_sha256", "modules", "registered_profile"):
            if root_sb.get(k) != cur.get(k): raise InputContractError(f"run source binding ({k}) differs from the current process")
    registered = registered or {}
    # registry: restore + internal validation + SHA correspondence
    rr = d["archive_refs"].get("registry")
    if rr is None: raise InputContractError("registry reference missing")
    greg = registry_from_dict(_get(archive, rr))
    if greg.registry_sha256 != d.get("registry_sha256") or (registered.get("registry_sha256") and greg.registry_sha256 != registered["registry_sha256"]): raise InputContractError("restored registry SHA differs from the run / trusted registry")
    fams = d.get("families") or {}; resolved = {}; pos_records = {}
    # cases
    for key, c in (d.get("cases") or {}).items():
        fam, size = c["family"], c["size_id"]; tr = fams[fam]["transitions"][size]; t = StageTransition(**tr)
        rec = resolve_transition_archive(archive, t, ArchiveRef(**c["result_ref"]))
        if rec.get("truths") != c.get("truths") or rec.get("position_status") != c.get("position_status") or rec.get("decision", {}).get("technical_status") != c.get("technical_status"): raise InputContractError(f"case {key}: manifest truths / position status / technical status differ from the archived position record")
        dref = (rec.get("evidence") or {}).get("diagnostic_ref")
        if dref is not None:
            if c.get("diagnostic_ref") != dref: raise InputContractError(f"case {key}: the archived position record carries a diagnostic reference that the manifest omits or changes")
            drec = _get(archive, dref)
            if drec.get("family") != fam or drec.get("size_id") != size or dref["identity"].get("kind") != "case_core_diagnostic": raise InputContractError(f"case {key}: diagnostic record identity")
            verify_family_result_dict(drec)                                                                       # (R2V2-B) case core diagnostic re-verified from its stored evidence
            ds = c.get("diagnostic") or {}                                                                            # (R2V3-A) the diagnostic is compared with ITS OWN summary, never with the parent-derived position record
            if ds.get("truths") != drec.get("truths") or ds.get("technical_status") != drec.get("decision", {}).get("technical_status") or ds.get("display_label") != drec.get("decision", {}).get("display_label"): raise InputContractError(f"case {key}: diagnostic summary differs from the archived diagnostic record")
        elif c.get("diagnostic") is not None or c.get("diagnostic_ref") is not None: raise InputContractError(f"case {key}: manifest carries a diagnostic the archived position record does not reference")
        pos_records[key] = rec
        resolved[key] = dict(result=c["result_ref"]["sha256"], diagnostic=(None if dref is None else dref["sha256"]))
    # families: coordinator restored + validated; core record re-verified from stored evidence; state-derived required references
    if fams:
        for fam, f in fams.items():
            if set(k for k, c in (d.get("cases") or {}).items() if c["family"] == fam) != {f"{fam}/{sz}" for sz in greg.surviving[fam]}: raise InputContractError(f"family {fam}: case set differs from the registry's surviving sizes")
    mans_cache = {}
    def restored_manifest(fam, size, sha):
        mref = d["archive_refs"].get(f"twelve_manifest:{fam}/{size}")
        if mref is None: raise InputContractError(f"family {fam}/{size}: required twelve manifest reference missing")
        mrec = _get(archive, mref); mrec.pop("sha256_recorded", None); man = TwelvePositionManifest(**mrec); _structural_checks(man)
        if man.sha256 != sha or mref["identity"].get("payload_sha256") != sha or man.family != fam or man.size_id != size: raise InputContractError(f"family {fam}/{size}: restored twelve manifest differs from the required SHA / identity")
        return man
    # The position table is a projection of the already validated PARENT
    # per_config evidence. Self-consistency of P=hits/N is not sufficient.
    first_wave = build_configuration_manifest(greg)
    if first_wave.manifest_sha256 != d.get("manifest_sha256"):
        raise InputContractError("position source registry-derived manifest differs from the run")

    def recorded_position_map(fam, size, where):
        text = (fps.get("at_gate", {}).get(f"{fam}/{size}") or {}).get("position_map")
        if not isinstance(text, str) or len(text) > 4096:
            raise InputContractError(f"{where}: position-map fingerprint missing or malformed")
        # Historical fingerprints use repr(sorted(pmap.items())). Decode only
        # literal list/tuple pairs and integer values; never eval executable code.
        # NumPy integer repr is accepted to preserve the existing integral API.
        integer_reprs = {"int8", "int16", "int32", "int64", "uint8", "uint16", "uint32", "uint64", "int_", "intp", "uintp"}
        def read_int(node):
            if isinstance(node, ast.Constant):
                return _integer(node.value, "position-map integer")
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name) and node.func.value.id == "np"
                    and node.func.attr in integer_reprs and len(node.args) == 1 and not node.keywords
                    and isinstance(node.args[0], ast.Constant)):
                return _integer(node.args[0].value, "position-map NumPy integer")
            raise InputContractError(f"{where}: unsupported nonliteral position-map value")
        try:
            node = ast.parse(text, mode="eval").body
        except (SyntaxError, ValueError) as ex:
            raise InputContractError(f"{where}: invalid position-map fingerprint") from ex
        if not isinstance(node, (ast.List, ast.Tuple)) or len(node.elts) != 3:
            raise InputContractError(f"{where}: position map must contain three pairs")
        pairs = []
        for pair in node.elts:
            if not isinstance(pair, (ast.List, ast.Tuple)) or len(pair.elts) != 2:
                raise InputContractError(f"{where}: malformed position-map pair")
            pairs.append((read_int(pair.elts[0]), read_int(pair.elts[1])))
        if len({e for e, _ in pairs}) != 3 or sorted(j for _, j in pairs) != [1, 2, 3]:
            raise InputContractError(f"{where}: position map is not a bijection")
        return dict(pairs)

    def check_parent_position_probabilities(fam, size, ev, parent, where):
        gi = (parent.get("evidence") or {}).get("grid_identity")
        if (not isinstance(gi, dict) or gi.get("registry_sha256") != greg.registry_sha256
                or gi.get("manifest_sha256") != first_wave.manifest_sha256):
            raise InputContractError(f"{where}: parent position grid is not bound to the run registry")
        wanted = {c.config_id for c in first_wave.configurations if c.family == fam and c.size_id == size}
        e2c = gi.get("evaluation_to_config") or {}
        ids = {e for e, c in e2c.items() if c in wanted}
        pmap = recorded_position_map(fam, size, where)
        if len(ids) != 3 or set(pmap) != ids or {e2c[e] for e in ids} != wanted:
            raise InputContractError(f"{where}: position-map configurations differ from the registered size")
        per = parent.get("per_config") or {}
        expected = {}
        for e, j in pmap.items():
            if e not in per:
                raise InputContractError(f"{where}: parent lacks a position configuration")
            q = per[e]
            expected[j] = dict(P=q["P_model"], hits=q["hits_M"], N=q["N"],
                               precision=q["precision"]["state"], stage=q["stage"])
        if ser.dumps(ev.get("position_probabilities")) != ser.dumps(expected):
            raise InputContractError(f"{where}: position probabilities do not reproduce from parent per_config and the recorded position map")

    def check_position_source(fam, size, transition, pos, parent, threshold, where):
        """Stored position evidence -> state -> transition. Not a W2 replay.
        The W2 context's physical/external replay remains a separate pre-use gate.
        """
        ev = pos.get("evidence") or {}; st = pos.get("position_status") or {}
        if (pos.get("kind") != "case_position_record" or
                pos.get("family") != fam or pos.get("size_id") != size or
                ev.get("threshold") != threshold):
            raise InputContractError(f"{where}: position source identity / threshold")
        if (pos.get("truths") != parent.get("truths") or
                pos.get("precision") != parent.get("precision") or
                pos.get("decision") != {k: parent["decision"][k] for k in ("technical_status", "display_label")}):
            raise InputContractError(f"{where}: position source differs from the parent core")
        if ev.get("parent_family_result") != "family_core:" + fam:
            raise InputContractError(f"{where}: position source parent identity")
        if fam == "E1":
            if ev.get("w2_context") is not None or ev.get("position_probabilities") != {}:
                raise InputContractError(f"{where}: E1 position exemption evidence")
            expected_state, expected_expand = "not-expanded", False
        else:
            ctx = ev.get("w2_context") or {}
            if ctx != dict(asset_sha256=d.get("w2_asset_sha256"), context_sha256=d.get("w2_context_sha256"), case=f"{fam}/{size}"):
                raise InputContractError(f"{where}: position source W2 context differs from the run")
            check_parent_position_probabilities(fam, size, ev, parent, where)
            ratio, info = event_ratio_trigger(ev.get("position_probabilities") or {})
            if st.get("ratio_trigger") != ratio or st.get("ratio_info") != info:
                raise InputContractError(f"{where}: position event-ratio evidence disagrees")
            state = position_state(st.get("w2_trigger"), ratio,
                tech_fail=parent["decision"]["technical_status"] == "technical_fail",
                zero_hit_expansion=bool(info.get("expansion_due_to_zero_hits", False)))
            expected_state, expected_expand = state["state"], state["expand"]
        if st.get("state") != expected_state or st.get("expand") is not expected_expand:
            raise InputContractError(f"{where}: position state does not follow its evidence")
        # The source can be technical even when its recorded position state is
        # nontechnical (E1). StageTransition.validate applies TECH precedence.
        if transition.position_state != expected_state:
            raise InputContractError(f"{where}: transition contradicts its position source")
        transition.validate()

    def outcome_from_records(fam, core_rec, plan_rec, twelve_rec, where):
        """(R2V3-B) eligibility / eligible truths derived from VERIFIED records: core FamilyResult dict, plan dict (transitions/status/expand/required_manifests), 12-position Result dict or None."""
        core_tech = core_rec["decision"]["technical_status"] == "technical_fail"
        fes = FamilyExpansionSet(family=fam, surviving_sizes=list(greg.surviving[fam]), transitions={sz: StageTransition(**t) for sz, t in plan_rec["transitions"].items()}, expand_family=bool(plan_rec["expand_family"]), required_manifests=dict(plan_rec.get("required_manifests") or {}), status=str(plan_rec["plan_status"]), reasons=[])
        try: fes.validate()  # technical status does not waive structural integrity
        except InputContractError as ex: raise InputContractError(f"{where}: coordinator plan inconsistent: {ex}")
        for sz, t in fes.transitions.items():
            if t.family != fam or t.size_id != sz: raise InputContractError(f"{where}: transition identity")
        # A registered but not yet evaluated branch still needs its manifests.
        mans = ({sz: restored_manifest(fam, sz, fes.required_manifests[sz])
                 for sz in fes.surviving_sizes} if fes.expand_family else {})
        tw = None
        if fes.expand_family and not core_tech and fes.status != "technical_fail" and twelve_rec is not None:
            verify_family_result_dict(twelve_rec)
            if twelve_rec.get("family") != fam or len(twelve_rec.get("per_config") or {}) != 36: raise InputContractError(f"{where}: 12-position Result identity / configuration inventory")
            if core_rec.get("native") is not None and not (twelve_rec.get("native") and len(twelve_rec["native"].get("per_config") or {}) == 36): raise InputContractError(f"{where}: 12-position Result lacks the native system present in the 3-position core")
            mans = {sz: restored_manifest(fam, sz, fes.required_manifests[sz]) for sz in fes.surviving_sizes}
            cf = completion_from_full12(fam, list(fes.surviving_sizes), twelve_rec, mans, fes); tw = dict(tech12=cf["tech12"], completion=cf["completion"]["family_local_completion"], truths=twelve_rec["truths"], per_size=cf["completion"]["per_size"], completion_records=cf["completion_records"])
        elig, truths = derive_outcome(fam, core_rec["truths"], core_tech, fes.status, fes.expand_family, (None if tw is None else dict(tech12=tw["tech12"], completion=tw["completion"], truths=tw["truths"])))
        return dict(eligibility=elig, eligible_truths=truths, core_tech=core_tech, plan=fes, twelve=tw)
    for fam, f in fams.items():
        fc = d["archive_refs"].get(f"family_core:{fam}")
        if fc is None: raise InputContractError(f"family {fam}: family_core reference missing")
        frec = _get(archive, fc); core = f["family_core"]
        verify_family_result_dict(frec)                                                                                   # (R2V2-B) Q reproduced from stored configuration probabilities + prior, CIs, decision
        if (frec.get("evidence") or {}).get("threshold") != thr.get("target"): raise InputContractError(f"family {fam}: family core record threshold differs from the run target")
        if frec.get("family") != fam or frec.get("truths") != core["truths"] or frec.get("Q_point") != core.get("Q_point") or frec.get("decision", {}).get("technical_status") != core.get("technical_status") or frec.get("decision", {}).get("display_label") != core.get("display_label"): raise InputContractError(f"family {fam}: family core record differs from the manifest")
        n_sizes = len(greg.surviving[fam]); n_pos = 1 if fam == "E1" else 3
        if len(frec.get("per_config") or {}) != n_sizes * n_pos: raise InputContractError(f"family {fam}: family core per_config count {len(frec.get('per_config') or {})} != {n_sizes * n_pos}")
        for sz in greg.surviving[fam]:                                                                                 # (R2V3-A) position records are derived from the PARENT family core
            prec_ = pos_records.get(f"{fam}/{sz}")
            if prec_ is None: raise InputContractError(f"family {fam}/{sz}: position record missing")
            check_position_source(fam, sz, StageTransition(**f["transitions"][sz]), prec_, frec, thr.get("target"), f"family {fam}/{sz}")
        plan_rec = dict(transitions=f["transitions"], plan_status=f.get("position_plan_status"), expand_family=f["expand_family"], required_manifests=f.get("required_manifests") or {})
        tc = d["archive_refs"].get(f"twelve_family_core:{fam}"); trec = _get(archive, tc) if tc is not None else None
        if trec is not None and (trec.get("evidence") or {}).get("threshold") != thr.get("target"): raise InputContractError(f"family {fam}: twelve family core record threshold differs from the run target")
        oc = outcome_from_records(fam, frec, plan_rec, trec, f"family {fam}")
        expected_status = "technical_fail" if oc["core_tech"] else oc["plan"].status
        if f.get("status") != expected_status or bool(f.get("expand_family")) != (False if oc["core_tech"] else bool(oc["plan"].expand_family)): raise InputContractError(f"family {fam}: recorded status / expand differ from the derivation over the verified records")
        if f.get("eligibility") != oc["eligibility"] or f.get("eligible_truths") != oc["eligible_truths"]: raise InputContractError(f"family {fam}: eligibility / eligible truths differ from the derivation over the verified records")
        ev12 = f.get("twelve_stage") == "evaluated in this run"
        if ev12 != (trec is not None) or (trec is None and f.get("twelve") is not None): raise InputContractError(f"family {fam}: twelve stage record / reference inconsistent")
        if trec is not None:
            tws = f.get("twelve") or {}
            if tws.get("completion_records") != oc["twelve"]["completion_records"]:
                raise InputContractError(f"family {fam}: completion records differ from the verified full Result")
            if bool(tws.get("family_local_completion")) != bool(oc["twelve"]["completion"]) or tws.get("per_size") != oc["twelve"]["per_size"] or (tws.get("family_mixture") or {}).get("truths") != trec.get("truths"): raise InputContractError(f"family {fam}: twelve completion / per-size / truths differ from the derivation over the verified 12-position Result")
        if f.get("expand_family") and not oc["core_tech"] and oc["plan"].status != "technical_fail":
            for sz in greg.surviving[fam]: restored_manifest(fam, sz, (f.get("required_manifests") or {}).get(sz))
        else:
            if any(v is not None for v in (f.get("required_manifests") or {}).values()): raise InputContractError(f"family {fam}: non-expanded family carries a required manifest SHA (inconsistent plan)")
        resolved[f"family_core:{fam}"] = fc["sha256"]
    # pseudos
    thr = d.get("thresholds") or {}; ps = thr.get("pseudo") or {}; statuses = d.get("per_pseudo_family_status") or []
    if ps.get("n") is not None and len(statuses) != ps["n"]: raise InputContractError(f"per-pseudo status count {len(statuses)} != n pseudo {ps.get('n')}")
    T1, T2 = ps.get("T1") or [], ps.get("T2") or []
    if ps.get("n") is not None and (len(T1) != ps["n"] or len(T2) != ps["n"] or hashlib.sha256(np.ascontiguousarray(np.asarray(T1, float)).tobytes()).hexdigest() != ps.get("sha256_T1") or hashlib.sha256(np.ascontiguousarray(np.asarray(T2, float)).tobytes()).hexdigest() != ps.get("sha256_T2")): raise InputContractError("pseudo threshold columns differ from their recorded SHA / length")
    decl_fams = set(sd.get("families") or []) if sd else (set(fams) if fams else None)
    if decl_fams is None and statuses: decl_fams = set(statuses[0])
    for i, st in enumerate(statuses):
        if set(st) != decl_fams: raise InputContractError(f"pseudo[{i}]: family set differs from the declared run families")
        for fam, s in st.items():
            if s.get("family") != fam or fam not in greg.surviving: raise InputContractError(f"pseudo[{i}] {fam}: family field / registry membership")
            if s.get("parent_ref") is None or s.get("plan_ref") is None: raise InputContractError(f"pseudo[{i}] {fam}: parent / plan references missing (pseudo evidence not archived)")
            prec_ = _get(archive, s["parent_ref"]); verify_family_result_dict(prec_)
            if prec_.get("family") != fam or prec_.get("evidence", {}).get("pseudo_index") != i or (T1 and prec_.get("evidence", {}).get("threshold") != [float(T1[i]), float(T2[i])]) or prec_.get("truths") != s.get("core_truths"): raise InputContractError(f"pseudo[{i}] {fam}: parent record identity / threshold / core truths")
            plrec = _get(archive, s["plan_ref"])
            if plrec.get("kind") != "pseudo_family_plan" or plrec.get("family") != fam or plrec.get("pseudo_index") != i or (T1 and plrec.get("threshold") != [float(T1[i]), float(T2[i])]): raise InputContractError(f"pseudo[{i}] {fam}: plan record identity")
            case_refs = plrec.get("case_refs")
            if not isinstance(case_refs, dict) or set(case_refs) != set(greg.surviving[fam]):
                raise InputContractError(f"pseudo[{i}] {fam}: position source reference inventory missing or incomplete")
            if set(plrec.get("transitions") or {}) != set(case_refs):
                raise InputContractError(f"pseudo[{i}] {fam}: transition / source inventories disagree")
            for size, pref in case_refs.items():
                tr = StageTransition(**plrec["transitions"][size])
                pos = resolve_transition_archive(archive, tr, ArchiveRef(**pref))
                check_position_source(fam, size, tr, pos, prec_, [float(T1[i]), float(T2[i])], f"pseudo[{i}] {fam}/{size}")
            r = s.get("twelve_full_result_ref"); tw = s.get("twelve"); trec = None
            if r is not None:
                trec = _get(archive, r)
                if r["sha256"] != s.get("twelve_full_result_sha256") or trec.get("evidence", {}).get("pseudo_index") != i or trec.get("family") != fam: raise InputContractError(f"pseudo[{i}] {fam}: full Result reference inconsistent")
                if T1 and trec.get("evidence", {}).get("threshold") != [float(T1[i]), float(T2[i])]: raise InputContractError(f"pseudo[{i}] {fam}: full Result threshold differs from the pseudo pair")
            oc = outcome_from_records(fam, prec_, plrec, trec, f"pseudo[{i}] {fam}")
            if bool(s.get("core_technical")) != oc["core_tech"] or s.get("plan_status") != oc["plan"].status or bool(s.get("expand_family")) != (False if oc["core_tech"] else bool(oc["plan"].expand_family)): raise InputContractError(f"pseudo[{i}] {fam}: core technical / plan status / expand differ from the verified records")
            if s.get("eligibility") != oc["eligibility"] or s.get("eligible_truths") != oc["eligible_truths"]: raise InputContractError(f"pseudo[{i}] {fam}: eligibility / eligible truths differ from the derivation over the verified records")
            if (trec is not None) != (isinstance(tw, dict) and bool(tw.get("evaluated"))): raise InputContractError(f"pseudo[{i}] {fam}: twelve evaluated flag / full Result reference inconsistent")
            if trec is not None and bool(tw.get("local_completion")) != bool(oc["twelve"]["completion"]): raise InputContractError(f"pseudo[{i}] {fam}: twelve local completion differs from the derivation")
    # calibration re-derivation
    cal = d.get("calibration") or {}; bc = d.get("branch_completeness") or {}
    for lvl, thr_v in (("support", RULES.usable_support), ("strong", RULES.usable_strong)):
        if lvl not in cal: continue
        exp_truths = [any_family_truth([st[fam]["eligible_truths"][lvl] for fam in st]) for st in statuses]
        if cal[lvl].get("truths") != exp_truths: raise InputContractError(f"calibration {lvl}: truths differ from the per-pseudo eligible truths")
        s = calibrate(exp_truths, thr_v, expected_n=len(exp_truths)).as_dict(); got = cal[lvl]["summary"]
        for k in s:
            if k in ("reason", "w2_context"): continue
            if got.get(k) != s.get(k): raise InputContractError(f"calibration {lvl}: summary field {k} differs from re-aggregation")
        if got.get("threshold") != thr_v: raise InputContractError(f"calibration {lvl}: threshold differs from the registered value")
        # derive completeness from the base records: family set from the statuses / dependencies / registry; missing branches from statuses (and target families when present)
        run_fam_set = decl_fams if decl_fams is not None else set(fams)
        if fams and set(fams) != run_fam_set: raise InputContractError("target family set differs from the declared run families")
        derived_all = (run_fam_set == set(greg.surviving)); derived_missing = [dict(where=f"pseudo[{i}]", family=fam, reason="triggered 12-position stage not evaluated") for i, st in enumerate(statuses) for fam, sst in st.items() if sst.get("expand_family") and not (isinstance(sst.get("twelve"), dict) and sst["twelve"].get("evaluated"))]
        tmiss = [dict(where="target", family=fam, reason="triggered 12-position stage not evaluated") for fam, f in fams.items() if f.get("expand_family") and f.get("twelve_stage") != "evaluated in this run"]
        if stage == "full": derived_missing = tmiss + derived_missing
        if stage == "sealed_target":
            if (bc.get("target_missing_branches") or []) != tmiss or bool(bc.get("full_procedure_including_target")) != bool(not tmiss and not derived_missing and derived_all): raise InputContractError("target-side branch completeness differs from the derivation over the verified records")
        if bool(bc.get("all_registered_families")) != derived_all or (bc.get("missing_branches") or []) != derived_missing: raise InputContractError("branch completeness differs from the derivation over the base records")
        if bool(cal[lvl].get("full_procedure")) != (derived_all and not derived_missing): raise InputContractError(f"calibration {lvl}: full_procedure flag inconsistent with the derived completeness")
        wc = (got.get("w2_context") or {})
        if wc and (wc.get("asset_sha256") != d.get("w2_asset_sha256") or wc.get("context_sha256") != d.get("w2_context_sha256")): raise InputContractError(f"calibration {lvl}: summary W2 context differs from the run")
    # W2 context registration
    ctx_scope = "unregistered context (NOT approved for formal reuse)"; ctx_ok = False
    if registered:
        if registered.get("shared_null_asset_sha256") and d.get("w2_asset_sha256") != registered["shared_null_asset_sha256"]: raise InputContractError("run W2 asset SHA differs from the registered shared null asset")
        if registered.get("w2_context_sha256") and d.get("w2_context_sha256") != registered["w2_context_sha256"]: raise InputContractError("run W2 context SHA differs from the registered context")
        if "twelve_assets_sha256" in registered and b.get("twelve_assets_sha256") != registered["twelve_assets_sha256"]: raise InputContractError("run twelve asset SHA differs from the registered asset")
        ctx_ok = bool(registered.get("shared_null_asset_sha256") and registered.get("w2_context_sha256")); ctx_scope = "registered context verified" if ctx_ok else "partial registration supplied (NOT approved for formal reuse)"
    # sealed order record
    order = None
    if "order_record" in b:
        o = b["order_record"]; srec = _get(archive, o["sealed_calibration_ref"])
        if _payload_sha(srec) != o["sealed_calibration_sha256"] or srec["thresholds"].get("target_commitment") != o["commitment"] or srec["thresholds"].get("target") is not None: raise InputContractError("sealed calibration parent does not match the order record")
        if o.get("target") != thr.get("target"): raise InputContractError("order record target differs from the run target")
        if srec.get("calibration") != cal or srec.get("per_pseudo_family_status") != statuses: raise InputContractError("target-side calibration / per-pseudo status is not a verbatim copy of the sealed parent")
        sd, cd = (srec.get("binding") or {}).get("sealed_dependencies") or {}, b.get("sealed_dependencies") or {}
        diff = [k for k in ("mode", "registry_sha256", "manifest_sha256", "w2_context_sha256", "w2_asset_sha256", "twelve_assets_sha256", "families", "source_binding") if sd.get(k) != cd.get(k)]
        if diff: raise InputContractError(f"sealed parent dependencies differ from the target run: {diff}")
        if sd.get("w2_context_sha256") != d.get("w2_context_sha256") or sd.get("w2_asset_sha256") != d.get("w2_asset_sha256"): raise InputContractError("W2 context of the sealed parent differs from the target run")
        order = dict(sealed_sha256=o["sealed_calibration_sha256"], commitment=o["commitment"])
    return dict(ok=True, run_manifest_sha256=b["run_manifest_sha256"], resolved=resolved, n_cases=len([k for k in resolved if not k.startswith("family_core:")]), n_pseudo=len(statuses), context_scope=ctx_scope, registered_context_ok=ctx_ok, order_record=order, scope="reference chain resolved, byte-verified and semantically re-verified against the archive (no bank re-evaluation); formal reuse additionally requires the registered context object and the pre-use gates")
