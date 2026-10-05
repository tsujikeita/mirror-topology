# -*- coding: utf-8 -*-
"""D4C-2a measurement instrumentation (audit D4C2-probe §6: 'first draft a measured version on the same E2 / same leading rows / same banks and plans ... separate parent
assembly, fingerprints, plan validation, hit count / table, Q resampling and CI, N selection and final re-evaluation, per-size diagnostics, KDE point / CI / sensitivity, the
12-position stage, archive / reader; record call counts and self / cumulative time; do not mix profiling overhead with production speed').

Profiler is a context manager that installs TIMING WRAPPERS around a fixed inventory of engine entry points (TARGETS) at every module attribute through which the engine looks
them up, and restores the originals on exit. A wrapper calls the original with the same arguments and returns its result unchanged: no argument, return value, exception, random
state or file is touched, so the calibration record produced under the profiler is byte-identical to the uninstrumented one (tests assert the payload SHA equality). The wrappers
measure wall time (time.perf_counter) per target: cumulative (inclusive) seconds, self seconds (inclusive minus the inclusive time of nested wrapped targets), call count; plus
a per-segment breakdown where a segment is one call of threshold_evaluator.evaluate_family_full (one pseudo threshold pair = one segment), so the per-row evaluation calls are separated from everything outside the segments (fixed costs: parent assembly, fingerprints, gate, publication — AND the per-row archive puts that
follow each evaluation; the two are not separated by this record). cProfile (optional) runs underneath and
reports the top functions by cumulative / internal time with their call counts. The report (schema d4c1_profile_record_v1) carries the instrumentation flags so that a measured
wall time is never read as the production speed; it holds no scientific quantity and is not an input of any calibration record.
Scope: measurement only — no cache, no reuse, no change of any numerical path. A target that is not importable (older source) is skipped and listed under 'missing'."""
from __future__ import annotations
import importlib, time, cProfile, pstats, io, functools, platform
from typing import Dict, List, Optional, Tuple
from .errors import InputContractError
from . import __version__

PROFILE_SCHEMA = "d4c1_profile_record_v1"
SEGMENT_TARGET = "threshold_evaluator.evaluate_family_full"

# target name -> binding sites (module, attribute); a site 'Class.method' patches the class attribute. Every site of one target shares ONE wrapper (counts aggregate).
TARGETS: Dict[str, List[Tuple[str, str]]] = {
    "integrated_runner.assemble_parent": [("integrated_runner", "assemble_parent"), ("d4c1_partial", "assemble_parent")],
    "formal_runner.input_fingerprint": [("formal_runner", "input_fingerprint"), ("d4c1_partial", "input_fingerprint")],
    "official_gate.official_gate": [("official_gate", "official_gate"), ("d4c1_partial", "official_gate"), ("formal_runner", "official_gate")],
    "official_gate.require_official": [("official_gate", "require_official"), ("d4c1_partial", "require_official"), ("formal_runner", "require_official")],
    "threshold_evaluator.evaluate_family_full": [("threshold_evaluator", "evaluate_family_full"), ("d4c1_partial", "evaluate_family_full"), ("integrated_runner", "evaluate_family_full")],
    "orchestrator.evaluate_family_staged": [("orchestrator", "evaluate_family_staged"), ("threshold_evaluator", "evaluate_family_staged"), ("twelve_eval", "evaluate_family_staged")],
    "orchestrator.evaluate_threshold": [("orchestrator", "evaluate_threshold"), ("threshold_evaluator", "evaluate_threshold")],
    "orchestrator._stage_selection": [("orchestrator", "_stage_selection")],
    "orchestrator.evaluate_family": [("orchestrator", "evaluate_family"), ("twelve_eval", "evaluate_family")],
    "orchestrator._family_Q": [("orchestrator", "_family_Q")],
    "orchestrator._family_logD": [("orchestrator", "_family_logD")],
    "orchestrator.ConfigBank.hit_tables": [("orchestrator", "ConfigBank.hit_tables")],
    "orchestrator.ConfigBank.at_stage": [("orchestrator", "ConfigBank.at_stage")],
    "bootstrap_plan.resample_hits": [("bootstrap_plan", "resample_hits"), ("orchestrator", "resample_hits")],
    "density.kde_logpdf_weighted": [("density", "kde_logpdf_weighted"), ("orchestrator", "kde_logpdf_weighted")],
    "density.sensitivity_audit": [("density", "sensitivity_audit"), ("orchestrator", "sensitivity_audit")],
    "positions.position_decision": [("positions", "position_decision"), ("threshold_evaluator", "position_decision")],
    "coordinator.plan_family_expansion": [("coordinator", "plan_family_expansion"), ("threshold_evaluator", "plan_family_expansion")],
    "twelve_eval.evaluate_twelve_family_mixture": [("twelve_eval", "evaluate_twelve_family_mixture")],
    "archive.Archive.put": [("archive", "Archive.put")],
    "archive.Archive.flush": [("archive", "Archive.flush")],
    "serialization.to_jsonable": [("serialization", "to_jsonable")],
}


class _Counter:
    __slots__ = ("calls", "inclusive", "self_")
    def __init__(self): self.calls = 0; self.inclusive = 0.0; self.self_ = 0.0
    def snapshot(self): return (self.calls, self.inclusive, self.self_)


class Profiler:
    """with Profiler(cprofile=False) as p: ...; rec = p.report()"""
    def __init__(self, cprofile: bool = False, targets: Optional[Dict[str, List[Tuple[str, str]]]] = None, top_n: int = 40):
        if not isinstance(cprofile, bool): raise InputContractError("cprofile must be bool")
        if not isinstance(top_n, int) or isinstance(top_n, bool) or top_n < 1: raise InputContractError("top_n must be a positive int")
        self.targets = dict(TARGETS if targets is None else targets); self.cprofile = cprofile; self.top_n = top_n
        self.counters: Dict[str, _Counter] = {name: _Counter() for name in self.targets}; self._stack: List[Tuple[str, float]] = []; self._installed: List[Tuple[object, str, object]] = []
        self.missing: List[str] = []; self.segments: List[dict] = []; self._open_segment: Optional[dict] = None; self._prof: Optional[cProfile.Profile] = None; self.t_enter = None; self.t_exit = None; self._active = False

    # --------------------------------------------------------------------------------------------------------------------------------- wrapping
    def _wrap(self, name: str, fn):
        prof = self; ctr = self.counters[name]; is_segment = (name == SEGMENT_TARGET)
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not prof._active: return fn(*args, **kwargs)
            seg = None
            if is_segment and prof._open_segment is None:
                seg = dict(index=len(prof.segments), before={k: c.snapshot() for k, c in prof.counters.items()}, t0=time.perf_counter()); prof._open_segment = seg
            t0 = time.perf_counter(); prof._stack.append([name, 0.0])
            try: return fn(*args, **kwargs)
            finally:
                dt = time.perf_counter() - t0; _, child = prof._stack.pop(); ctr.calls += 1; ctr.inclusive += dt; ctr.self_ += dt - child
                if prof._stack: prof._stack[-1][1] += dt
                if seg is not None:
                    seg["wall_seconds"] = time.perf_counter() - seg.pop("t0"); after = {k: c.snapshot() for k, c in prof.counters.items()}; before = seg.pop("before")
                    seg["targets"] = {k: dict(calls=after[k][0] - before[k][0], inclusive_seconds=after[k][1] - before[k][1], self_seconds=after[k][2] - before[k][2]) for k in after if after[k][0] != before[k][0]}
                    prof.segments.append(seg); prof._open_segment = None
        wrapper.__profiler_target__ = name; return wrapper

    def __enter__(self):
        if self._active or self.t_exit is not None: raise InputContractError("Profiler is single-use and not re-entrant")
        try:
            for name, sites in self.targets.items():
                resolved = []
                for mod_name, attr in sites:
                    try: mod = importlib.import_module("." + mod_name, __package__)
                    except ImportError: continue
                    if "." in attr:
                        cls_name, meth = attr.split(".", 1); holder = getattr(mod, cls_name, None)
                        if holder is None or not hasattr(holder, meth): continue
                        resolved.append((holder, meth, holder.__dict__.get(meth, getattr(holder, meth))))
                    else:
                        if not hasattr(mod, attr): continue
                        resolved.append((mod, attr, getattr(mod, attr)))
                if not resolved: self.missing.append(name); continue
                fn = resolved[0][2]; wrapper = self._wrap(name, fn)
                for holder, attr, orig in resolved:
                    if orig is not fn and getattr(orig, "__profiler_target__", None) != name: raise InputContractError(f"profiler target {name}: binding sites hold different objects ({attr})")
                    setattr(holder, attr, wrapper); self._installed.append((holder, attr, orig))
        except BaseException:
            for holder, attr, orig in reversed(self._installed): setattr(holder, attr, orig)                     # N-D4C2A-PROFILER-ENTER-CLEANUP: an entry failure leaves no wrapper installed
            self._installed = []; self.t_exit = time.perf_counter(); raise
        if self.cprofile: self._prof = cProfile.Profile(); self._prof.enable()
        self.t_enter = time.perf_counter(); self._active = True; return self

    def __exit__(self, *exc):
        self._active = False; self.t_exit = time.perf_counter()
        if self._prof is not None: self._prof.disable()
        for holder, attr, orig in reversed(self._installed): setattr(holder, attr, orig)
        self._installed = []; return False

    # --------------------------------------------------------------------------------------------------------------------------------- report
    def report(self, note: Optional[str] = None) -> dict:
        if self._active or self.t_exit is None: raise InputContractError("report() is available after the profiler context has exited")
        total = self.t_exit - self.t_enter; segs = list(self.segments); seg_wall = sum(s["wall_seconds"] for s in segs)
        inside = {k: dict(calls=0, inclusive_seconds=0.0, self_seconds=0.0) for k in self.counters}
        for s in segs:
            for k, v in s["targets"].items():
                inside[k]["calls"] += v["calls"]; inside[k]["inclusive_seconds"] += v["inclusive_seconds"]; inside[k]["self_seconds"] += v["self_seconds"]
        targets = {k: dict(calls=c.calls, inclusive_seconds=c.inclusive, self_seconds=c.self_, outside_segments=dict(calls=c.calls - inside[k]["calls"], inclusive_seconds=c.inclusive - inside[k]["inclusive_seconds"], self_seconds=c.self_ - inside[k]["self_seconds"])) for k, c in self.counters.items()}
        cp = None
        if self._prof is not None:
            st = pstats.Stats(self._prof); rows = []
            for (file, line, func), (cc, nc, tt, ct, callers) in st.stats.items(): rows.append(dict(function=func, file=file, line=line, ncalls=nc, primitive_calls=cc, tottime=tt, cumtime=ct))
            cp = dict(by_cumtime=sorted(rows, key=lambda r: -r["cumtime"])[:self.top_n], by_tottime=sorted(rows, key=lambda r: -r["tottime"])[:self.top_n], n_functions=len(rows))
        return dict(schema=PROFILE_SCHEMA, engine_version=__version__, instrumentation=dict(wrappers=True, cprofile=self.cprofile, clock="time.perf_counter (wall)", segment_target=SEGMENT_TARGET,
                    note="timing wrappers and cProfile add overhead; a measured wall time is NOT the production speed (compare with the uninstrumented probe); no numerical path is changed",
                    accounting="outside_segments = everything outside the evaluate_family_full calls: fixed costs (parent assembly, fingerprints, gate, publication) AND per-row persistence (the archive puts after each evaluation), which are NOT separated here; inclusive target times overlap (nested targets) and must not be summed to a total"),
                    python=platform.python_version(), wall_seconds_total=total, segments=dict(count=len(segs), wall_seconds=seg_wall, per_segment=[dict(index=s["index"], wall_seconds=s["wall_seconds"], targets=s["targets"]) for s in segs],
                    mean_wall_seconds=(seg_wall / len(segs) if segs else None)), outside_segments_wall_seconds=total - seg_wall, outside_segments_note="fixed costs + per-row persistence (archive.Archive.put outside the segments is per-row)", targets=targets, missing_targets=list(self.missing), cprofile=cp, note=note)


def summarize(rec: dict) -> List[str]:
    """Human-readable lines of a profile record (inclusive / self / calls per target, sorted by self time)."""
    if not isinstance(rec, dict) or rec.get("schema") != PROFILE_SCHEMA: raise InputContractError("not a profile record")
    out = [f"total {rec['wall_seconds_total']:.3f}s | segments {rec['segments']['count']} ({rec['segments']['wall_seconds']:.3f}s, mean {rec['segments']['mean_wall_seconds'] or 0:.3f}s) | outside {rec['outside_segments_wall_seconds']:.3f}s"]
    for k, v in sorted(rec["targets"].items(), key=lambda kv: -kv[1]["self_seconds"]):
        if v["calls"]: out.append(f"{k:48s} calls {v['calls']:7d} incl {v['inclusive_seconds']:9.3f}s self {v['self_seconds']:9.3f}s")
    return out
