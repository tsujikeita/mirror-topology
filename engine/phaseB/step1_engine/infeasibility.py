# -*- coding: utf-8 -*-
"""D4C-2a: fixed-denominator infeasibility certificate of the global calibration and the sufficient count-envelope screen (audit D4C2-probe §5; decision GO
unchanged_rule_feasibility_certificate_design_and_synthetic_tests). DESIGN + synthetic tests only; nothing here is a calibration, a partial or a sealed record.

Certificate (schema calibration_infeasibility_certificate_v1; archive identity kind 'calibration_infeasibility_certificate'):
  With the registered aggregation (calibration.calibrate: Wilson upper bound of (c + u) / n over the FIXED n = RULES.n_pseudo, compared with the registered threshold) a pseudo row
  whose eligible truth in at least one family is True or 'unknown' adds 1 to c + u whatever the non-technical outcome of the other families (calibration.any_family_truth:
  technical_fail > True > unknown > False), and a technical_fail row makes the calibration technical (no usable value at all). wilson_blocking_count(n, threshold) is the smallest
  k with wilson_upper(k, n) > threshold (n = 2000: 81 for the support threshold .05, 12 for the strong threshold .01). If the number of proven blocking rows reaches that k, then
  EVEN IF every unevaluated row were False, usable == True is impossible at that level: an ALGEBRAIC statement over the fixed denominator; the certificate carries no c / u / rate,
  claims nothing about the unevaluated rows and is not a usable == False calibration (the formal readers reject it by kind / schema). Proofs are reconciled per
  (row, family, level) and then combined over the families per row (different families' True / unknown / technical_fail combine as in any_family_truth; a row counts once);
  the thresholds are the exact registered level -> threshold mapping. Evidence AUTHENTICATION (run records, publication hashes, readers, registered identities) is the
  consumer's duty before rows are admitted: bind_screen_record (screens; canonical full N0 / N4 coverage) and evaluated_rows_from_record (partials / sub-partials through the
  existing readers) are the admission functions; check_certificate certifies only the algebra over the admitted rows.
Screen (schema position_envelope_screen_v1): a SUFFICIENT condition under which a non-E1 family's eligible truth of a row cannot be False, read off the exact hit counts without any
  bootstrap / KDE: the family has at least one size whose registered W2 decision is 'unknown' and no size whose W2 decision is True (fixed registered context, the same for every
  pseudo), and for EVERY surviving size the envelope over the three observer positions and BOTH evaluation prefixes b in {N0, N4} of the matched system's exact hit rate
  P = point_P(hits, N) (the SAME float64 computation as orchestrator._family_Q) is positive and satisfies max / min <= 2.0 in float64 (the registered event-ratio trigger is
  max(P) / min(P) > 2.0 over the three positions at the N stage each position ends at; division is monotone, so the envelope bounds every mixed choice of prefixes and the
  trigger is False whenever the precision gate passes; a precision gate not met gives 'unknown', zero hits are excluded by positivity, a technical failure gives technical_fail).
  Then every size is 'not-expanded' or 'position-unresolved', no size is position-sensitive, the family plan is provisional (or technical) and threshold_evaluator.derive_outcome
  returns unknown (or technical_fail) for every level: the row is blocking. A row that fails the screen is NOT declared False or non-blocking: it goes to the normal evaluation.
  The screen is bound to the family inputs (input_fingerprint of every size view), the registry / manifest, the W2 context SHA and decision checksums, the global pseudo column
  identity, the exact thresholds and the engine source binding; the exact counts and float values are recorded for re-checking."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple
import hashlib, math
import numpy as np
from .errors import InputContractError
from .rules_config import RULES
from .calibration import wilson_upper
from .family import point_P
from .formal_runner import input_fingerprint
from .positions import VerifiedW2Decision
from .integrated_runner import _pseudo_snapshot
from .w2_context import canonical_case_key
from .checkpoint import binding_manifest
from .truth import UNKNOWN, TECH
from . import serialization as ser
from . import __version__

SCREEN_SCHEMA = "position_envelope_screen_v1"
CERT_SCHEMA = "calibration_infeasibility_certificate_v1"
CERT_KIND = "calibration_infeasibility_certificate"
RATIO_LIMIT = 2.0                                                        # positions.event_ratio_trigger: max(ps) / min(ps) > 2.0
LEVELS = ("support", "strong")
_STAGES = ("N0", "N4")


def _is_sha(v) -> bool: return isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)


def wilson_blocking_count(n: int, threshold: float) -> int:
    """Smallest k in 0..n with wilson_upper(k, n) > threshold (n + 1 if none: the threshold cannot be exceeded)."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 1: raise InputContractError("n must be a positive int")
    if not isinstance(threshold, float) or not (0 < threshold < 1): raise InputContractError("threshold must be a float in (0, 1)")
    for k in range(n + 1):
        if wilson_upper(k, n) > threshold: return k
    return n + 1


def registered_blocking_counts(n: Optional[int] = None) -> dict:
    n = RULES.n_pseudo if n is None else n
    return {lvl: dict(threshold=thr, first_blocking_count=wilson_blocking_count(n, thr), previous_upper=(wilson_upper(wilson_blocking_count(n, thr) - 1, n) if wilson_blocking_count(n, thr) > 0 else None), blocking_upper=(wilson_upper(wilson_blocking_count(n, thr), n) if wilson_blocking_count(n, thr) <= n else None)) for lvl, thr in (("support", RULES.usable_support), ("strong", RULES.usable_strong))}


# --------------------------------------------------------------------------------------------------------------------------------------------- screen
def exact_hit_rate(c, t1: float, t2: float, stage: str) -> dict:
    """The matched-system exact hit rate of ONE configuration at the N stage: the same expression as orchestrator._family_Q (point_P over the boolean hit count)."""
    if stage == "N4" and not c.has_extension: raise InputContractError(f"configuration {c.evaluation_id}: no N4 extension")
    b = c.at_stage(stage); hits = int(((b.T1_model <= t1) & (b.T2_model <= t2)).sum()); N = int(len(b.T1_model))
    P = float(point_P(np.array([hits]), np.array([N]))[0]); return dict(hits=hits, N=N, P=P)


def _envelope_size(fm, pmap: Dict[int, int], t1: float, t2: float) -> dict:
    ids = [c.evaluation_id for c in fm.configs]
    if set(pmap) != set(ids) or sorted(pmap.values()) != [1, 2, 3]: raise InputContractError("position map must be a bijection of this size's three configurations onto positions 1..3")
    per = {}; vals = []; positive = True; complete = True
    for c in fm.configs:
        stages = {}; bank_stages = ["N0"] + (["N4"] if c.has_extension else [])
        for st in bank_stages:
            r = exact_hit_rate(c, t1, t2, st); stages[st] = r; vals.append(r["P"]); positive &= r["hits"] > 0
        complete &= (bank_stages == list(_STAGES))
        per[str(int(pmap[c.evaluation_id]))] = dict(evaluation_id=c.evaluation_id, bank_stages=bank_stages, stages=stages)
    lo, hi = min(vals), max(vals); ratio_bound = (hi / lo) if lo > 0 else None
    ok = bool(positive and ratio_bound is not None and ratio_bound <= RATIO_LIMIT)
    return dict(positions=per, min_P=lo, max_P=hi, ratio_bound=ratio_bound, all_positive=bool(positive), ok=ok, complete_coverage=bool(complete), stages_covered=sorted({st for p in per.values() for st in p["stages"]}))


def w2_triggers(family: str, sizes: Sequence[str], decisions: Dict[str, VerifiedW2Decision]) -> dict:
    out = {}
    for s in sizes:
        key = f"{family}/{s}"; w = decisions.get(key)
        if not isinstance(w, VerifiedW2Decision): raise InputContractError(f"case {key}: a replay-verified VerifiedW2Decision is required")
        w.check(); out[s] = dict(trigger=(w.trigger if isinstance(w.trigger, str) else bool(w.trigger)), validation_state=w.validation_state, B_final=w.B_final, checksum=w.checksum)
    return out


def envelope_screen_family(reg, man, family: str, cases: Dict[str, tuple], w2_decisions: Dict[str, VerifiedW2Decision], expected_context_sha256: str, pseudo_T1, pseudo_T2, rows: Optional[Sequence[int]] = None, *, campaign: Optional[dict] = None, target_commitment: Optional[str] = None) -> dict:
    """cases: {f'{family}/{size}': (fm, fn, pmap)} for exactly the surviving sizes (the first-wave views used by the partial). rows: global row indices (default: all)."""
    reg.validate(); man.validate()
    if man.registry_sha256 != reg.registry_sha256: raise InputContractError("manifest not bound to the registry")
    if family not in reg.surviving: raise InputContractError(f"family {family!r} is not a registered family")
    if family == "E1": raise InputContractError("E1 is observer-homogeneous (position branch exempt): the envelope screen does not apply")
    if not _is_sha(expected_context_sha256): raise InputContractError("W2 context SHA required")
    if target_commitment is not None and not _is_sha(target_commitment): raise InputContractError("target commitment must be a sha256 hex string")
    sizes = list(reg.surviving[family]); want = {f"{family}/{s}" for s in sizes}
    if not isinstance(cases, dict) or set(cases) != want: raise InputContractError(f"family {family}: the screen requires exactly the surviving sizes {sizes}")
    for key in cases:
        fam, size = canonical_case_key(key, {})
        if fam != family or size not in sizes: raise InputContractError(f"case {key}: not a case of family {family}")
    ps = _pseudo_snapshot(pseudo_T1, pseudo_T2); n = ps["n"]
    if rows is not None and (isinstance(rows, (str, bytes, dict)) or any(isinstance(r, bool) or not isinstance(r, (int, np.integer)) for r in rows)): raise InputContractError("rows must be a sequence of ints")
    rows = list(range(n)) if rows is None else [int(r) for r in rows]
    if any(r < 0 or r >= n for r in rows) or len(set(rows)) != len(rows) or rows != sorted(rows): raise InputContractError("rows must be distinct sorted global indices in [0, n)")
    trig = w2_triggers(family, sizes, w2_decisions); tv = {s: trig[s]["trigger"] for s in sizes}
    w2_applicable = (not any(v is True for v in tv.values())) and any(v == UNKNOWN for v in tv.values())
    fps = {key: dict(matched=input_fingerprint(v[0]), native=(None if v[1] is None else input_fingerprint(v[1])), position_map=repr(sorted(v[2].items()))) for key, v in cases.items()}
    views = {canonical_case_key(k, {})[1]: v for k, v in cases.items()}
    out_rows = []
    for r in rows:
        t1, t2 = float(ps["T1"][r]), float(ps["T2"][r]); per_size = {s: _envelope_size(views[s][0], views[s][2], t1, t2) for s in sizes}
        all_ok = all(v["ok"] for v in per_size.values()); blocking = bool(w2_applicable and all_ok)
        reason = ("W2: at least one size unknown and none True; every size's envelope positive with max/min <= 2 -> no size can become position-sensitive -> family eligible truth unknown (or technical_fail)" if blocking
                  else ("W2 condition not met (a size with W2 True, or no unknown size): the screen does not apply" if not w2_applicable else "envelope condition not met for " + ", ".join(s for s in sizes if not per_size[s]["ok"]) + ": undetermined by the screen (normal evaluation required)"))
        out_rows.append(dict(row=r, threshold=[t1, t2], sizes=per_size, blocking=blocking, complete_coverage=bool(all(v["complete_coverage"] for v in per_size.values())), reason=reason))
    fp_after = {key: dict(matched=input_fingerprint(v[0]), native=(None if v[1] is None else input_fingerprint(v[1])), position_map=repr(sorted(v[2].items()))) for key, v in cases.items()}
    if fp_after != fps: raise InputContractError("inputs changed during the screen")
    rec = dict(schema=SCREEN_SCHEMA, engine_version=__version__, family=family, sizes=sizes, registry_sha256=reg.registry_sha256, manifest_sha256=man.manifest_sha256, w2_context_sha256=expected_context_sha256, w2=trig, w2_applicable=w2_applicable,
               pseudo=dict(n=n, sha256_T1=ps["sha256_T1"], sha256_T2=ps["sha256_T2"]), rows=rows, n_rows=len(rows), n_blocking=sum(1 for x in out_rows if x["blocking"]), complete_coverage=bool(all(x["complete_coverage"] for x in out_rows)), stages_required=list(_STAGES), registered=dict(N0=RULES.N0, N_max=RULES.N_max),
               config_ids={s: sorted(c.evaluation_id for c in views[s][0].configs) for s in sizes}, fingerprints=fps, results=out_rows, campaign=campaign, target_commitment=target_commitment,
               rule=dict(ratio_trigger="positions.event_ratio_trigger: max(P) / min(P) > 2.0 over the three positions at their final N stage; P = point_P(hits, N) of the matched system", envelope="max / min over every position and every available prefix (N0, N4) <= 2.0 in float64 and every hit count > 0",
                         consequence="no size position-sensitive; a size with W2 unknown stays position-unresolved; family plan provisional -> derive_outcome: eligible truths unknown for every level (technical_fail retained)", sufficient_only="a row failing the screen is undetermined, never False"),
               binding=binding_manifest())
    rec["binding"]["screen_sha256"] = hashlib.sha256(ser.dumps({k: v for k, v in rec.items() if k != "binding"}).encode()).hexdigest()
    return rec


def check_screen_record(d: dict, *, formal: bool = False, registered_N: Optional[Tuple[int, int]] = None) -> dict:
    """Re-check a screen record's INTERNAL consistency (content SHA; W2 applicability from the recorded decisions; per position: the recorded stages == the recorded bank stages,
    P == point_P(hits, N); the envelope summaries and the blocking flags from the recorded values; counts). formal=True additionally requires the CANONICAL full coverage of a
    formal proof: every size / position carries BOTH prefixes N0 and N4 with N == RULES.N0 / RULES.N_max, hits_N4 >= hits_N0, evaluation id suffix == position, and the record
    declares complete coverage. This is an arithmetic / shape re-check; the binding to the registered identities (registry, W2 context and decisions, columns, configurations)
    is bind_screen_record."""
    if not isinstance(d, dict) or d.get("schema") != SCREEN_SCHEMA: raise InputContractError("not a screen record")
    N0_req, Nmax_req = (RULES.N0, RULES.N_max) if registered_N is None else (int(registered_N[0]), int(registered_N[1]))
    body = {k: v for k, v in d.items() if k != "binding"}
    if hashlib.sha256(ser.dumps(ser.from_jsonable(ser.to_jsonable(body))).encode()).hexdigest() != (d.get("binding") or {}).get("screen_sha256"): raise InputContractError("screen record content SHA mismatch")
    tv = {s: v["trigger"] for s, v in d["w2"].items()}
    if set(tv) != set(d["sizes"]) or d["family"] == "E1": raise InputContractError("screen W2 inventory / family")
    appl = (not any(v is True for v in tv.values())) and any(v == UNKNOWN for v in tv.values())
    if appl != d["w2_applicable"]: raise InputContractError("screen W2 applicability differs from the recorded decisions")
    if d["rows"] != sorted(set(d["rows"])) or len(d["results"]) != len(d["rows"]) or any(x["row"] != r for x, r in zip(d["results"], d["rows"])): raise InputContractError("screen rows / results inventory")
    if d.get("stages_required") != list(_STAGES) or not isinstance(d.get("registered"), dict) or not isinstance(d.get("config_ids"), dict) or set(d["config_ids"]) != set(d["sizes"]): raise InputContractError("screen record stages_required / registered / config_ids")
    nb = 0; cov_all = True
    for x in d["results"]:
        ok_all = True; cov_row = True
        for s in d["sizes"]:
            v = x["sizes"][s]; vals = []; positive = True; complete = True
            if sorted(int(k) for k in v["positions"]) != [1, 2, 3]: raise InputContractError(f"row {x['row']} {s}: positions")
            if sorted(p["evaluation_id"] for p in v["positions"].values()) != d["config_ids"][s]: raise InputContractError(f"row {x['row']} {s}: evaluation ids differ from the record's configuration inventory")
            for pos, p in v["positions"].items():
                bs = p.get("bank_stages")
                if bs not in (["N0"], ["N0", "N4"]) or list(p["stages"]) != bs: raise InputContractError(f"row {x['row']} {s} position {pos}: recorded stages {list(p['stages'])} differ from the bank stages {bs}")
                complete &= (bs == list(_STAGES))
                for st, r in p["stages"].items():
                    if st not in _STAGES or not (isinstance(r["hits"], int) and isinstance(r["N"], int) and 0 <= r["hits"] <= r["N"] and r["N"] > 0): raise InputContractError(f"row {x['row']} {s}: counts")
                    if float(point_P(np.array([r["hits"]]), np.array([r["N"]]))[0]) != r["P"]: raise InputContractError(f"row {x['row']} {s}: P != point_P(hits, N)")
                    vals.append(r["P"]); positive &= r["hits"] > 0
                if "N4" in p["stages"] and (p["stages"]["N4"]["N"] <= p["stages"]["N0"]["N"] or p["stages"]["N4"]["hits"] < p["stages"]["N0"]["hits"]): raise InputContractError(f"row {x['row']} {s} position {pos}: N4 prefix is not a superset of N0")
                if formal:
                    if bs != list(_STAGES) or p["stages"]["N0"]["N"] != N0_req or p["stages"]["N4"]["N"] != Nmax_req or int(p["evaluation_id"]) % 100 != int(pos): raise InputContractError(f"row {x['row']} {s} position {pos}: a formal proof requires both prefixes N0 ({N0_req}) and N4 ({Nmax_req}) of the registered configuration (suffix == position)")
            lo, hi = min(vals), max(vals); rb = (hi / lo) if lo > 0 else None
            if v["min_P"] != lo or v["max_P"] != hi or v["ratio_bound"] != rb or v["all_positive"] != positive or v.get("complete_coverage") != complete or v["ok"] != bool(positive and rb is not None and rb <= RATIO_LIMIT): raise InputContractError(f"row {x['row']} {s}: envelope summary differs from the recorded values")
            ok_all &= v["ok"]; cov_row &= complete
        if x["blocking"] != bool(appl and ok_all) or x.get("complete_coverage") != cov_row: raise InputContractError(f"row {x['row']}: blocking / coverage flags differ from the recorded conditions")
        nb += int(x["blocking"]); cov_all &= cov_row
    if nb != d["n_blocking"] or d["n_rows"] != len(d["rows"]) or d.get("complete_coverage") != cov_all: raise InputContractError("screen counts / coverage")
    if formal and not cov_all: raise InputContractError("a formal screen proof requires complete N0 / N4 coverage of every row")
    return dict(ok=True, family=d["family"], n_rows=d["n_rows"], n_blocking=nb, w2_applicable=appl, complete_coverage=cov_all, formal=bool(formal))


def bind_screen_record(d: dict, *, registry_sha256: str, manifest_sha256: str, w2_context_sha256: str, w2_checksums: Dict[str, str], pseudo_identity: dict, T1, T2, config_ids: Dict[str, list], family: Optional[str] = None, campaign_id: Optional[str] = None, target_commitment: Optional[str] = None, registered_N: Optional[Tuple[int, int]] = None) -> dict:
    """Binding of a (formally checked) screen record to the CURRENT registered identities supplied by the consumer: registry / manifest SHA, W2 context SHA and the replay-verified
    decision checksum of every case, the global column identity and the exact row thresholds, the registered configuration ids per size, the family and (optionally) campaign /
    commitment. The record's own statements are never trusted alone."""
    chk = check_screen_record(d, formal=True, registered_N=registered_N)
    if family is not None and d["family"] != family: raise InputContractError("screen family differs from the requested family")
    if d["registry_sha256"] != registry_sha256 or d["manifest_sha256"] != manifest_sha256: raise InputContractError("screen registry / manifest differ from the current registered grid")
    if d["w2_context_sha256"] != w2_context_sha256: raise InputContractError("screen W2 context SHA differs from the registered context")
    for s_, v in d["w2"].items():
        key = f"{d['family']}/{s_}"
        if key not in w2_checksums or v.get("checksum") != w2_checksums[key]: raise InputContractError(f"screen W2 decision {key} is not the registered replay-verified decision")
    if d["pseudo"] != dict(n=pseudo_identity["n"], sha256_T1=pseudo_identity["sha256_T1"], sha256_T2=pseudo_identity["sha256_T2"]): raise InputContractError("screen pseudo column identity differs from the registered columns")
    T1 = np.asarray(T1, float); T2 = np.asarray(T2, float)
    if len(T1) != pseudo_identity["n"] or len(T2) != pseudo_identity["n"] or hashlib.sha256(np.ascontiguousarray(T1).tobytes()).hexdigest() != pseudo_identity["sha256_T1"] or hashlib.sha256(np.ascontiguousarray(T2).tobytes()).hexdigest() != pseudo_identity["sha256_T2"]: raise InputContractError("supplied columns do not match the pseudo identity")
    for x in d["results"]:
        if x["threshold"] != [float(T1[x["row"]]), float(T2[x["row"]])]: raise InputContractError(f"screen row {x['row']}: threshold differs from the registered column pair")
    if {s_: sorted(v) for s_, v in config_ids.items()} != {s_: sorted(v) for s_, v in d["config_ids"].items()}: raise InputContractError("screen configuration ids differ from the registered first-wave configurations of this family")
    if campaign_id is not None and (d.get("campaign") or {}).get("id") != campaign_id: raise InputContractError("screen campaign differs")
    if target_commitment is not None and d.get("target_commitment") != target_commitment: raise InputContractError("screen commitment differs")
    return dict(chk, bound=True)


# --------------------------------------------------------------------------------------------------------------------------------------------- certificate
def blocking_rows_from_screen(d: dict, *, formal: bool = False) -> Dict[int, dict]:
    """Rows proven blocking by a checked screen record (formal=True: canonical full coverage required): every level 'unknown_or_technical' = unknown unless a technical failure
    occurs in the evaluation, in which case the calibration itself is technical (no usable value); never a False."""
    check_screen_record(d, formal=formal)
    return {x["row"]: dict(kind="screen", family=d["family"], status={lvl: "unknown_or_technical" for lvl in LEVELS}, source_sha256=d["binding"]["screen_sha256"], ratio_bounds={s: x["sizes"][s]["ratio_bound"] for s in d["sizes"]}) for x in d["results"] if x["blocking"]}


def blocking_rows_from_statuses(family: str, statuses: Sequence[dict], start: int, source_sha256: str) -> Dict[int, dict]:
    """Rows proven blocking by EVALUATED per-pseudo statuses (a family partial / sub-partial record: eligible truths): per level True / unknown / technical_fail; a row whose eligible
    truth is False at a level is not blocking at that level (it may still be at the other level)."""
    if not isinstance(start, int) or isinstance(start, bool) or start < 0 or not _is_sha(source_sha256): raise InputContractError("start / source SHA")
    out = {}
    for i, s in enumerate(statuses):
        if s.get("family") != family: raise InputContractError(f"status[{i}] family")
        et = s.get("eligible_truths") or {}; st = {}
        for lvl in LEVELS:
            v = et.get(lvl)
            if v is True: st[lvl] = "True"
            elif v == UNKNOWN: st[lvl] = "unknown"
            elif v == TECH: st[lvl] = "technical_fail"
            elif v is False: st[lvl] = "False"
            else: raise InputContractError(f"status[{i}] {lvl}: eligible truth {v!r}")
        if any(st[lvl] != "False" for lvl in LEVELS): out[start + i] = dict(kind="evaluated", family=family, status=st, source_sha256=source_sha256, eligibility=s.get("eligibility"))
    return out


_BLOCKING = ("True", "unknown", "unknown_or_technical")
_RANK = {"technical_fail": 4, "True": 3, "unknown": 2, "unknown_or_technical": 1, "False": 0}


def _registered_thresholds() -> dict: return dict(support=RULES.usable_support, strong=RULES.usable_strong)


def _merge_same_family(a: str, b: str, where: str) -> str:
    """Two proofs of the SAME (row, family, level): identical, or a screen's 'unknown_or_technical' refined by an evaluated unknown / technical_fail; anything else is a contradiction."""
    if a == b: return a
    if "unknown_or_technical" in (a, b) and {a, b} <= {"unknown", "technical_fail", "unknown_or_technical"}: return a if a != "unknown_or_technical" else b
    raise InputContractError(f"{where}: conflicting proven statuses {a!r} vs {b!r}")


def aggregate_rows(rows: Dict[int, Dict[str, Dict[str, str]]]) -> Dict[int, dict]:
    """rows: row -> family -> level -> status (one proven status per family). Per row and level, over the families (calibration.any_family_truth: technical_fail > True > unknown >
    False): 'technical' if any family is technical_fail (the calibration is technical: no usable value); 'blocking' if any family is True / unknown / unknown_or_technical (the row adds
    1 to c + u whatever the other families' non-technical outcomes are; a screen's unknown_or_technical keeps its conditional meaning: unknown unless a technical failure occurs, and a
    True in another family does not remove that possibility); 'aggregate' = the highest-ranked family status. No row is counted twice."""
    out = {}
    for r, fams in rows.items():
        agg = {}
        for lvl in LEVELS:
            st = {f: fams[f][lvl] for f in fams}; top = max(st.values(), key=lambda v: _RANK[v])
            agg[lvl] = dict(aggregate=top, blocking=any(v in _BLOCKING for v in st.values()), technical=any(v == "technical_fail" for v in st.values()), possibly_technical=any(v == "unknown_or_technical" for v in st.values()))
        out[r] = agg
    return out


def evaluated_rows_from_record(published: dict, archive, *, registered: Optional[dict], pseudo_identity: dict, family: Optional[str] = None) -> dict:
    """R-D4C2A-C: admit the EVALUATED per-pseudo statuses of a published family partial / sub-partial record only through the existing readers: the archived copy (load_partial_record /
    load_subpartial_record: payload SHA + identity) equals the published document apart from the self-referencing binding entries; verify_partial_record / verify_subpartial_record
    (position sources, plans, 12-position Results, per-pseudo eligibility re-derived from the archived records; registered context; CURRENT source binding) succeed; the global column
    identity equals the registered columns. Returns dict(rows=blocking map, family, row_range, partial_sha256, verification)."""
    from .archive import ArchiveRef
    from .d4c1_partial import PARTIAL_SCHEMA, SUBPARTIAL_SCHEMA, load_partial_record, verify_partial_record
    from .d4c1_subpartial import load_subpartial_record, verify_subpartial_record
    if not isinstance(published, dict) or not isinstance(published.get("binding"), dict) or not isinstance(published["binding"].get("partial_ref"), dict): raise InputContractError("published record is not a partial / sub-partial record with an archive reference")
    schema = published.get("schema")
    if schema == PARTIAL_SCHEMA: load, verify, start = load_partial_record, verify_partial_record, 0
    elif schema == SUBPARTIAL_SCHEMA: load, verify, start = load_subpartial_record, verify_subpartial_record, int((published.get("rows") or {}).get("start", -1))
    else: raise InputContractError(f"published record schema {schema!r} is not a family partial / sub-partial")
    archived = load(archive, published["binding"]["partial_ref"])
    strip = lambda d: {**d, "binding": {k: v for k, v in d["binding"].items() if k not in ("partial_file_sha256", "partial_ref")}}
    if ser.dumps(strip(ser.from_jsonable(ser.to_jsonable(published)))) != ser.dumps(strip(archived)) or archived["binding"]["partial_sha256"] != published["binding"]["partial_sha256"]: raise InputContractError("published record differs from its archived copy")
    v = verify(archived, archive, registered=registered, current_source_binding=True)
    if not (v.get("ok") and v.get("registered_context_ok")): raise InputContractError("evaluated record not verified by the run reader with the registered context")
    ps = archived["thresholds"]["pseudo"]
    if dict(n=ps["n"], sha256_T1=ps["sha256_T1"], sha256_T2=ps["sha256_T2"]) != dict(n=pseudo_identity["n"], sha256_T1=pseudo_identity["sha256_T1"], sha256_T2=pseudo_identity["sha256_T2"]): raise InputContractError("evaluated record columns differ from the registered pseudo identity")
    if family is not None and archived["family"] != family: raise InputContractError("evaluated record family differs")
    if start < 0: raise InputContractError("sub-partial row start")
    rows = blocking_rows_from_statuses(archived["family"], archived["per_pseudo_status"], start, archived["binding"]["partial_sha256"])
    return dict(rows=rows, family=archived["family"], row_range=[start, start + len(archived["per_pseudo_status"])], partial_sha256=archived["binding"]["partial_sha256"], verification=v)


def infeasibility_certificate(n: int, blocking: Sequence[Dict[int, dict]], *, pseudo_identity: dict, campaign: Optional[dict] = None, target_commitment: Optional[str] = None, sources: Optional[list] = None, thresholds: Optional[dict] = None) -> dict:
    """blocking: a sequence of {row: evidence} maps (blocking_rows_from_screen / blocking_rows_from_statuses; every evidence names its family). Proofs are reconciled per
    (row, family, level) — the same family's proofs must agree (a screen's unknown_or_technical may be refined by an evaluated unknown / technical_fail) — and then aggregated
    over the families per row (aggregate_rows), so different families' True / unknown / technical_fail are combined, never rejected, and no global row is counted twice. thresholds
    must be EXACTLY the registered level -> threshold mapping. n is the FIXED denominator (official: RULES.n_pseudo)."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 1: raise InputContractError("n must be a positive int")
    thr = _registered_thresholds() if thresholds is None else thresholds
    if not isinstance(thr, dict) or list(thr.items()) != list(_registered_thresholds().items()): raise InputContractError("thresholds must be exactly the registered mapping {support: RULES.usable_support, strong: RULES.usable_strong}")
    thr = dict(thr)
    if not isinstance(pseudo_identity, dict) or pseudo_identity.get("n") != n or not (_is_sha(pseudo_identity.get("sha256_T1")) and _is_sha(pseudo_identity.get("sha256_T2"))): raise InputContractError("pseudo identity (n, sha256_T1, sha256_T2) must describe the fixed columns")
    if target_commitment is not None and not _is_sha(target_commitment): raise InputContractError("target commitment must be a sha256 hex string")
    fam_rows: Dict[int, Dict[str, Dict[str, str]]] = {}; evidence: Dict[int, list] = {}
    for m in blocking:
        if not isinstance(m, dict): raise InputContractError("blocking maps must be dicts row -> evidence")
        for r, ev in m.items():
            if not isinstance(r, int) or isinstance(r, bool) or not (0 <= r < n): raise InputContractError(f"row {r!r} outside [0, n)")
            if not isinstance(ev, dict) or ev.get("kind") not in ("screen", "evaluated") or not isinstance(ev.get("family"), str) or not ev["family"] or set(ev.get("status") or {}) != set(LEVELS) or any(v not in _RANK for v in ev["status"].values()): raise InputContractError(f"row {r}: evidence malformed")
            if ev["kind"] == "screen" and any(v != "unknown_or_technical" for v in ev["status"].values()): raise InputContractError(f"row {r}: a screen proves unknown_or_technical only")
            fam = ev["family"]; cur = fam_rows.setdefault(r, {}).get(fam)
            if cur is None: fam_rows[r][fam] = {lvl: ev["status"][lvl] for lvl in LEVELS}
            else:
                for lvl in LEVELS: cur[lvl] = _merge_same_family(cur[lvl], ev["status"][lvl], f"row {r} family {fam} {lvl}")
            evidence.setdefault(r, []).append(ev)
    agg = aggregate_rows(fam_rows)
    rows = {str(r): dict(families=fam_rows[r], levels=agg[r], evidence=evidence[r]) for r in sorted(fam_rows)}
    per_level = _levels_from_rows(n, thr, agg)
    rec = dict(schema=CERT_SCHEMA, kind=CERT_KIND, engine_version=__version__, n=n, pseudo=dict(pseudo_identity), thresholds=thr, levels=per_level, rows=rows, n_rows_proven=len(rows), sources=list(sources or []), campaign=campaign, target_commitment=target_commitment,
               aggregation=dict(rule="per (row, family, level) the proofs must agree (a screen's unknown_or_technical may be refined by an evaluated unknown / technical_fail); per row the families are combined as in calibration.any_family_truth (technical_fail > True > unknown > False); a row counts once",
                                blocking="any family True / unknown / unknown_or_technical -> the row adds 1 to c + u whatever the other families' non-technical outcomes", technical="any family technical_fail -> the calibration is technical (no usable value); counted apart, never as c + u",
                                unknown_or_technical="a screen row: unknown unless a technical failure occurs in its evaluation (then usable itself fails); a True in another family does not remove that possibility"),
               scope=("fixed-denominator ALGEBRAIC infeasibility statement: proven blocking rows vs the first blocking count of wilson_upper(k, n) > threshold; carries no c / u / rate, no statement about unevaluated rows, no technical-success claim for them, no usable == False "
                      "calibration; not a partial, not a sealed calibration (rejected by their readers); E1 rows enter only as evaluated statuses"), binding=binding_manifest())
    rec["binding"]["certificate_sha256"] = hashlib.sha256(ser.dumps({k: v for k, v in rec.items() if k != "binding"}).encode()).hexdigest()
    return rec


def _levels_from_rows(n: int, thr: dict, agg: Dict[int, dict]) -> dict:
    per_level = {}
    for lvl in LEVELS:
        k_block = wilson_blocking_count(n, thr[lvl])
        blocking_rows = sum(1 for a in agg.values() if a[lvl]["blocking"]); technical_rows = sum(1 for a in agg.values() if a[lvl]["technical"]); possibly = sum(1 for a in agg.values() if a[lvl]["possibly_technical"])
        cnt = {s: sum(1 for a in agg.values() if a[lvl]["aggregate"] == s) for s in ("technical_fail", "True", "unknown", "unknown_or_technical", "False")}
        per_level[lvl] = dict(threshold=thr[lvl], first_blocking_count=k_block, proven_blocking_rows=blocking_rows, technical_rows=technical_rows, possibly_technical_rows=possibly, aggregate_counts=cnt,
                              usable_true_impossible_by_wilson=bool(blocking_rows >= k_block), wilson_upper_if_remaining_all_false=wilson_upper(blocking_rows, n), technical_rows_present=bool(technical_rows > 0),
                              statement=("usable == True is impossible at this level for the fixed n: the Wilson upper bound of the proven blocking rows alone exceeds the threshold even if every other row were False" if blocking_rows >= k_block
                                         else "not proven: fewer proven blocking rows than the first blocking count (this is NOT a statement that the calibration is usable)"))
    return per_level


def check_certificate(d: dict) -> dict:
    """Internal re-derivation of a certificate: content SHA; the thresholds are exactly the registered mapping; every row's family statuses are valid and its level aggregates /
    the per-level counts / statements re-derive from them; n_rows_proven. (Evidence AUTHENTICATION — run records, publication hashes, readers, registered identities — is the
    consumer's job before the rows are admitted; this checker only certifies the algebra over the admitted rows.)"""
    if not isinstance(d, dict) or d.get("schema") != CERT_SCHEMA or d.get("kind") != CERT_KIND: raise InputContractError("not an infeasibility certificate")
    body = {k: v for k, v in d.items() if k != "binding"}
    if hashlib.sha256(ser.dumps(ser.from_jsonable(ser.to_jsonable(body))).encode()).hexdigest() != (d.get("binding") or {}).get("certificate_sha256"): raise InputContractError("certificate content SHA mismatch")
    if not isinstance(d.get("thresholds"), dict) or list(d["thresholds"].items()) != list(_registered_thresholds().items()): raise InputContractError("certificate thresholds are not the registered mapping")
    n = d["n"]
    if not isinstance(n, int) or isinstance(n, bool) or n < 1: raise InputContractError("certificate n")
    rows = {}
    for r_, v in d["rows"].items():
        r = int(r_)
        if not (0 <= r < n) or not isinstance(v.get("families"), dict) or not v["families"]: raise InputContractError(f"certificate row {r_}")
        for fam, st in v["families"].items():
            if set(st) != set(LEVELS) or any(x not in _RANK for x in st.values()): raise InputContractError(f"certificate row {r_} family {fam}: statuses")
        rows[r] = v["families"]
    if len(rows) != d["n_rows_proven"]: raise InputContractError("certificate n_rows_proven")
    agg = aggregate_rows(rows)
    for r_, v in d["rows"].items():
        if v.get("levels") != agg[int(r_)]: raise InputContractError(f"certificate row {r_}: level aggregates differ from the family statuses")
    if d["levels"] != _levels_from_rows(n, d["thresholds"], agg): raise InputContractError("certificate levels / statements differ from the re-derivation")
    return dict(ok=True, n=n, levels={lvl: d["levels"][lvl]["usable_true_impossible_by_wilson"] for lvl in LEVELS}, n_rows_proven=len(rows), technical_rows={lvl: d["levels"][lvl]["technical_rows"] for lvl in LEVELS})
