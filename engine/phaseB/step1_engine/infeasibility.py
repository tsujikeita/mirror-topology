# -*- coding: utf-8 -*-
"""D4C-2a: fixed-denominator infeasibility certificate of the global calibration and the sufficient count-envelope screen (audit D4C2-probe §5; decision GO
unchanged_rule_feasibility_certificate_design_and_synthetic_tests). DESIGN + synthetic tests only; nothing here is a calibration, a partial or a sealed record.

Certificate (schema calibration_infeasibility_certificate_v1; archive identity kind 'calibration_infeasibility_certificate'):
  With the registered aggregation (calibration.calibrate: Wilson upper bound of (c + u) / n over the FIXED n = RULES.n_pseudo, compared with the registered threshold) a pseudo row
  whose eligible truth in at least one family is True or 'unknown' adds 1 to c + u whatever the non-technical outcome of the other families (calibration.any_family_truth:
  technical_fail > True > unknown > False), and a technical_fail row makes the calibration technical (no usable value at all). wilson_blocking_count(n, threshold) is the smallest
  k with wilson_upper(k, n) > threshold (n = 2000: 81 for the support threshold .05, 12 for the strong threshold .01). If the number of proven blocking rows reaches that k, then
  EVEN IF every unevaluated row were False, usable == True is impossible at that level: an ALGEBRAIC statement over the fixed denominator; the certificate carries no c / u / rate,
  claims nothing about the unevaluated rows and is not a usable == False calibration (the formal readers reject it by kind / schema).
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
    per = {}; vals = []; positive = True
    for c in fm.configs:
        stages = {}
        for st in _STAGES:
            if st == "N4" and not c.has_extension: continue
            r = exact_hit_rate(c, t1, t2, st); stages[st] = r; vals.append(r["P"]); positive &= r["hits"] > 0
        per[str(int(pmap[c.evaluation_id]))] = dict(evaluation_id=c.evaluation_id, stages=stages)
    lo, hi = min(vals), max(vals); ratio_bound = (hi / lo) if lo > 0 else None
    ok = bool(positive and ratio_bound is not None and ratio_bound <= RATIO_LIMIT)
    return dict(positions=per, min_P=lo, max_P=hi, ratio_bound=ratio_bound, all_positive=bool(positive), ok=ok, stages_covered=sorted({st for p in per.values() for st in p["stages"]}))


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
    rows = list(range(n)) if rows is None else [int(r) for r in rows]
    if any(isinstance(r, bool) for r in rows) or any(r < 0 or r >= n for r in rows) or len(set(rows)) != len(rows) or rows != sorted(rows): raise InputContractError("rows must be distinct sorted global indices in [0, n)")
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
        out_rows.append(dict(row=r, threshold=[t1, t2], sizes=per_size, blocking=blocking, reason=reason))
    fp_after = {key: dict(matched=input_fingerprint(v[0]), native=(None if v[1] is None else input_fingerprint(v[1])), position_map=repr(sorted(v[2].items()))) for key, v in cases.items()}
    if fp_after != fps: raise InputContractError("inputs changed during the screen")
    rec = dict(schema=SCREEN_SCHEMA, engine_version=__version__, family=family, sizes=sizes, registry_sha256=reg.registry_sha256, manifest_sha256=man.manifest_sha256, w2_context_sha256=expected_context_sha256, w2=trig, w2_applicable=w2_applicable,
               pseudo=dict(n=n, sha256_T1=ps["sha256_T1"], sha256_T2=ps["sha256_T2"]), rows=rows, n_rows=len(rows), n_blocking=sum(1 for x in out_rows if x["blocking"]), fingerprints=fps, results=out_rows, campaign=campaign, target_commitment=target_commitment,
               rule=dict(ratio_trigger="positions.event_ratio_trigger: max(P) / min(P) > 2.0 over the three positions at their final N stage; P = point_P(hits, N) of the matched system", envelope="max / min over every position and every available prefix (N0, N4) <= 2.0 in float64 and every hit count > 0",
                         consequence="no size position-sensitive; a size with W2 unknown stays position-unresolved; family plan provisional -> derive_outcome: eligible truths unknown for every level (technical_fail retained)", sufficient_only="a row failing the screen is undetermined, never False"),
               binding=binding_manifest())
    rec["binding"]["screen_sha256"] = hashlib.sha256(ser.dumps({k: v for k, v in rec.items() if k != "binding"}).encode()).hexdigest()
    return rec


def check_screen_record(d: dict) -> dict:
    """Re-check a screen record's internal consistency (ratio bounds from the recorded P values; blocking from the recorded conditions; content SHA)."""
    if not isinstance(d, dict) or d.get("schema") != SCREEN_SCHEMA: raise InputContractError("not a screen record")
    body = {k: v for k, v in d.items() if k != "binding"}
    if hashlib.sha256(ser.dumps(ser.from_jsonable(ser.to_jsonable(body))).encode()).hexdigest() != (d.get("binding") or {}).get("screen_sha256"): raise InputContractError("screen record content SHA mismatch")
    tv = {s: v["trigger"] for s, v in d["w2"].items()}
    if set(tv) != set(d["sizes"]) or d["family"] == "E1": raise InputContractError("screen W2 inventory / family")
    appl = (not any(v is True for v in tv.values())) and any(v == UNKNOWN for v in tv.values())
    if appl != d["w2_applicable"]: raise InputContractError("screen W2 applicability differs from the recorded decisions")
    if d["rows"] != sorted(set(d["rows"])) or len(d["results"]) != len(d["rows"]) or any(x["row"] != r for x, r in zip(d["results"], d["rows"])): raise InputContractError("screen rows / results inventory")
    nb = 0
    for x in d["results"]:
        ok_all = True
        for s in d["sizes"]:
            v = x["sizes"][s]; vals = []; positive = True
            if sorted(int(k) for k in v["positions"]) != [1, 2, 3]: raise InputContractError(f"row {x['row']} {s}: positions")
            for p in v["positions"].values():
                for st, r in p["stages"].items():
                    if st not in _STAGES or not (isinstance(r["hits"], int) and isinstance(r["N"], int) and 0 <= r["hits"] <= r["N"] and r["N"] > 0): raise InputContractError(f"row {x['row']} {s}: counts")
                    if float(point_P(np.array([r["hits"]]), np.array([r["N"]]))[0]) != r["P"]: raise InputContractError(f"row {x['row']} {s}: P != point_P(hits, N)")
                    vals.append(r["P"]); positive &= r["hits"] > 0
            lo, hi = min(vals), max(vals); rb = (hi / lo) if lo > 0 else None
            if v["min_P"] != lo or v["max_P"] != hi or v["ratio_bound"] != rb or v["all_positive"] != positive or v["ok"] != bool(positive and rb is not None and rb <= RATIO_LIMIT): raise InputContractError(f"row {x['row']} {s}: envelope summary differs from the recorded values")
            ok_all &= v["ok"]
        if x["blocking"] != bool(appl and ok_all): raise InputContractError(f"row {x['row']}: blocking flag differs from the recorded conditions")
        nb += int(x["blocking"])
    if nb != d["n_blocking"] or d["n_rows"] != len(d["rows"]): raise InputContractError("screen counts")
    return dict(ok=True, family=d["family"], n_rows=d["n_rows"], n_blocking=nb, w2_applicable=appl)


# --------------------------------------------------------------------------------------------------------------------------------------------- certificate
def blocking_rows_from_screen(d: dict) -> Dict[int, dict]:
    """Rows proven blocking by a verified screen record: every level unknown-or-technical (never a False)."""
    check_screen_record(d)
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


def infeasibility_certificate(n: int, blocking: Sequence[Dict[int, dict]], *, pseudo_identity: dict, campaign: Optional[dict] = None, target_commitment: Optional[str] = None, sources: Optional[list] = None, thresholds: Optional[dict] = None) -> dict:
    """blocking: a sequence of {row: evidence} maps (from blocking_rows_from_screen / blocking_rows_from_statuses, possibly several families). The same row may be proven by several
    sources; a conflicting status for one row and level is rejected; the per-level count takes the strongest proven status (technical_fail > True > unknown). n is the FIXED
    denominator (official: RULES.n_pseudo)."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 1: raise InputContractError("n must be a positive int")
    thr = dict(support=RULES.usable_support, strong=RULES.usable_strong) if thresholds is None else dict(thresholds)
    if set(thr) != set(LEVELS) or any(k not in (RULES.usable_support, RULES.usable_strong) for k in thr.values()): raise InputContractError("thresholds must be the registered support / strong usable thresholds")
    if not isinstance(pseudo_identity, dict) or pseudo_identity.get("n") != n or not (_is_sha(pseudo_identity.get("sha256_T1")) and _is_sha(pseudo_identity.get("sha256_T2"))): raise InputContractError("pseudo identity (n, sha256_T1, sha256_T2) must describe the fixed columns")
    if target_commitment is not None and not _is_sha(target_commitment): raise InputContractError("target commitment must be a sha256 hex string")
    rows: Dict[int, dict] = {}
    for m in blocking:
        if not isinstance(m, dict): raise InputContractError("blocking maps must be dicts row -> evidence")
        for r, ev in m.items():
            if not isinstance(r, int) or isinstance(r, bool) or not (0 <= r < n): raise InputContractError(f"row {r!r} outside [0, n)")
            if not isinstance(ev, dict) or ev.get("kind") not in ("screen", "evaluated") or set(ev.get("status") or {}) != set(LEVELS): raise InputContractError(f"row {r}: evidence malformed")
            cur = rows.get(r)
            if cur is None: rows[r] = dict(evidence=[ev], status={lvl: ev["status"][lvl] for lvl in LEVELS}); continue
            for lvl in LEVELS:
                a, b = cur["status"][lvl], ev["status"][lvl]
                if a == b: continue
                if "unknown_or_technical" in (a, b) and (a in ("unknown", "technical_fail", "unknown_or_technical") and b in ("unknown", "technical_fail", "unknown_or_technical")): cur["status"][lvl] = a if a != "unknown_or_technical" else b; continue
                raise InputContractError(f"row {r} {lvl}: conflicting proven statuses {a!r} vs {b!r}")
            cur["evidence"].append(ev)
    per_level = {}
    for lvl in LEVELS:
        k_block = wilson_blocking_count(n, thr[lvl]); cnt = {s: sum(1 for v in rows.values() if v["status"][lvl] == s) for s in ("True", "unknown", "unknown_or_technical", "technical_fail")}
        wilson_count = cnt["True"] + cnt["unknown"] + cnt["unknown_or_technical"]                                     # rows that add 1 to c + u whatever the other families do (technical rows counted separately)
        per_level[lvl] = dict(threshold=thr[lvl], first_blocking_count=k_block, proven_blocking_rows=wilson_count, technical_rows=cnt["technical_fail"], counts=cnt,
                              usable_true_impossible_by_wilson=bool(wilson_count >= k_block), wilson_upper_if_remaining_all_false=wilson_upper(wilson_count, n),
                              technical_rows_present=bool(cnt["technical_fail"] > 0), statement=("usable == True is impossible at this level for the fixed n: the Wilson upper bound of the proven rows alone exceeds the threshold even if every other row were False" if wilson_count >= k_block
                                                                                                   else "not proven: fewer proven blocking rows than the first blocking count (this is NOT a statement that the calibration is usable)"))
    rec = dict(schema=CERT_SCHEMA, kind=CERT_KIND, engine_version=__version__, n=n, pseudo=dict(pseudo_identity), thresholds=thr, levels=per_level, rows={str(r): v for r, v in sorted(rows.items())}, n_rows_proven=len(rows), sources=list(sources or []), campaign=campaign, target_commitment=target_commitment,
               scope=("fixed-denominator ALGEBRAIC infeasibility statement: proven blocking rows vs the first blocking count of wilson_upper(k, n) > threshold; carries no c / u / rate, no statement about unevaluated rows, no technical-success claim for them, no usable == False "
                      "calibration; not a partial, not a sealed calibration (rejected by their readers); E1 rows enter only as evaluated statuses"), binding=binding_manifest())
    rec["binding"]["certificate_sha256"] = hashlib.sha256(ser.dumps({k: v for k, v in rec.items() if k != "binding"}).encode()).hexdigest()
    return rec


def check_certificate(d: dict) -> dict:
    if not isinstance(d, dict) or d.get("schema") != CERT_SCHEMA or d.get("kind") != CERT_KIND: raise InputContractError("not an infeasibility certificate")
    body = {k: v for k, v in d.items() if k != "binding"}
    if hashlib.sha256(ser.dumps(ser.from_jsonable(ser.to_jsonable(body))).encode()).hexdigest() != (d.get("binding") or {}).get("certificate_sha256"): raise InputContractError("certificate content SHA mismatch")
    n = d["n"]; rows = {int(r): v for r, v in d["rows"].items()}
    if any(not (0 <= r < n) for r in rows) or len(rows) != d["n_rows_proven"]: raise InputContractError("certificate rows")
    for lvl in LEVELS:
        L = d["levels"][lvl]; cnt = {s: sum(1 for v in rows.values() if v["status"][lvl] == s) for s in ("True", "unknown", "unknown_or_technical", "technical_fail")}
        wc = cnt["True"] + cnt["unknown"] + cnt["unknown_or_technical"]
        if L["counts"] != cnt or L["proven_blocking_rows"] != wc or L["first_blocking_count"] != wilson_blocking_count(n, L["threshold"]) or L["usable_true_impossible_by_wilson"] != (wc >= L["first_blocking_count"]) or L["wilson_upper_if_remaining_all_false"] != wilson_upper(wc, n): raise InputContractError(f"certificate {lvl}: counts / statement differ from the rows")
    return dict(ok=True, n=n, levels={lvl: d["levels"][lvl]["usable_true_impossible_by_wilson"] for lvl in LEVELS}, n_rows_proven=len(rows))
