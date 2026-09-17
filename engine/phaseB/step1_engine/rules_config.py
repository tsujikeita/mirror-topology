# -*- coding: utf-8 -*-
"""Validated rules configuration loaded from rules_tables_v1.json. Every threshold/constant used by the helpers comes from here (single source of truth),
and verify_binding() compares the loaded values with the documented golden constants so that a silent JSON edit is detected at import/test time."""
from __future__ import annotations
import json, os, hashlib
from dataclasses import dataclass

_HERE = os.path.dirname(os.path.abspath(__file__)); DEFAULT_PATH = os.path.join(_HERE, '..', 'rules_tables_v1.json')


@dataclass(frozen=True)
class RulesConfig:
    Q_support: float; Q_strong: float; logD_point: float; logD_lower: float; native_lower: float
    alpha: float; B: int; seeds: int; formal_seed: int
    positive_clusters_min: int; rel_halfwidth_max: float; width_cv_max: float
    usable_support: float; usable_strong: float; n_pseudo: int
    B_levels: tuple; first_comparison: tuple; rel_tol: float; n_subs: tuple; seed_ids: tuple; seed_spread_max: float; quantile_method: str
    grid_resolution: float; min_sep: dict; tie_tol: float
    N0: int; N_max: int; m: int
    rules_document_sha256: str; tables_sha256: str; path: str


def _load(path: str) -> RulesConfig:
    raw = open(path, 'rb').read(); j = json.loads(raw.decode('utf-8'))
    t1, t1b, t3, t4, t5, w2, ob = j['table1_decision_predicates'], j['table1b_replicate_states'], j['table3_eligibility'], j['table4_expansion'], j['table5_calibration_aggregation'], j['w2_stop'], j['observers12']
    th = t1['thresholds']
    cfg = RulesConfig(float(th['Q_support']), float(th['Q_strong']), float(th['logD_point']), float(th['logD_lower']), float(th['native_lower']),
                      float(t1b['alpha']), int(t1b['B']), int(t1b['seeds']), int(t1b['formal_interval_seed']),
                      int(t3['precision']['positive_clusters_min']), float(t3['precision']['rel_halfwidth_max']), float(t3['precision']['width_cv_max']),
                      float(t3['calibration']['usable_support_value']), float(t3['calibration']['usable_strong_value']), int(t5['n_pseudo']),
                      tuple(int(b) for b in w2['B_levels']), tuple(int(b) for b in w2['first_comparison']), float(w2['rel_tol']), tuple(int(n) for n in w2['n_sub']), tuple(int(s) for s in w2['seed_ids']), float(w2['seed_spread_max']), str(w2['quantile_method']),
                      float(ob['grid_resolution']), {k: float(v) for k, v in ob['min_sep'].items()}, float(ob['tie_tol']),
                      int(t4['N0']), int(t4['N_max']), int(t4['m']),
                      str(j['rules_document']['sha256']), hashlib.sha256(raw).hexdigest(), os.path.abspath(path))
    if not (0 < cfg.alpha < 1 and cfg.B > 0 and cfg.seeds >= 1 and 0 <= cfg.formal_seed < cfg.seeds): raise ValueError('rules config: invalid alpha/B/seeds')
    if not (cfg.Q_strong > cfg.Q_support > 1 and cfg.usable_strong < cfg.usable_support): raise ValueError('rules config: threshold ordering')
    if not (cfg.N_max == 4 * cfg.N0 and cfg.N0 > 0 and cfg.m > 0): raise ValueError('rules config: N0/N_max/m')
    if tuple(sorted(cfg.B_levels)) != cfg.B_levels or cfg.first_comparison != cfg.B_levels[:2]: raise ValueError('rules config: B levels')
    return cfg



GOLDEN = dict(Q_support=3.0, Q_strong=10.0, logD_point=0.0, logD_lower=0.0, native_lower=1.0, alpha=0.05, B=2000, seeds=5, formal_seed=0, positive_clusters_min=50, rel_halfwidth_max=0.20, width_cv_max=0.20,
              usable_support=0.05, usable_strong=0.01, n_pseudo=2000, B_levels=(200, 400, 600, 800, 1000), first_comparison=(200, 400), rel_tol=0.05, n_subs=(2000, 5000), seed_ids=(0, 1, 2), seed_spread_max=0.25,
              quantile_method='higher', grid_resolution=1e-4, min_sep={'E7': 0.015, 'E2': 0.05, 'E8': 0.04}, tie_tol=1e-12, N0=1000000, N_max=4000000, m=100)


import re as _re
_PRED_NUM = {"L_Q_matched >= 3": "Q_support", "L_Q_matched >= 10": "Q_strong", "logD_point_matched > 0": "logD_point", "L_logD_matched > 0": "logD_lower", "L_Q_native > 1": "native_lower", "U_Q_matched < 1": None, "U_logD_matched <= 0": None}


REQUIRED_TERMS = {
    "support_core": ["audit_Q_matched", "audit_Dpoint_matched", "L_Q_matched >= {Q_support}", "logD_point_matched > {logD_point}"],
    "strong_core": ["support_core", "audit_DCI_matched", "L_Q_matched >= {Q_strong}", "L_logD_matched > {logD_lower}", "audit_Q_native", "L_Q_native > {native_lower}"],
    "unsupported_core": ["audit_Q_matched", "audit_Dpoint_matched", "audit_DCI_matched", "U_Q_matched < 1", "U_logD_matched <= 0"],
}
_LIT = _re.compile(r'^-?\d+(?:\.\d+)?$')


def _fmt(x: float) -> str: return str(int(x)) if float(x).is_integer() else repr(float(x))


def _check_predicates(j: dict, cfg: RulesConfig):
    """Strict limited-grammar schema for table 1: each label must contain exactly the registered term multiset (thresholds rendered from the numeric fields);
    unknown terms, missing terms, extra terms, duplicates, or unregistered numeric spellings (e.g. 3e1) are rejected. No eval."""
    t1 = j['table1_decision_predicates']; th = t1['thresholds']
    for label, req in REQUIRED_TERMS.items():
        got = list(t1[label]['and']); expected = [s.format(Q_support=_fmt(th['Q_support']), Q_strong=_fmt(th['Q_strong']), logD_point=_fmt(th['logD_point']), logD_lower=_fmt(th['logD_lower']), native_lower=_fmt(th['native_lower'])) for s in req]
        norm = [' '.join(g.split()) for g in got]
        for g in norm:
            m = _re.match(r'^(\w+)\s*(>=|<=|>|<)\s*(\S+)$', g)
            if m and not _LIT.match(m.group(3)): raise ValueError(f'unregistered numeric spelling in predicate {g!r}')
        if sorted(norm) != sorted(expected): raise ValueError(f'table1 {label}: AND terms {norm} != registered {expected}')
    if list(t1['display_priority']) != ['strong', 'support', 'unsupported', 'inconclusive']: raise ValueError('display priority mismatch')


def verify_binding(cfg: RulesConfig = None, require_document: bool = True) -> dict:
    """Binding check: (1) loaded numeric values == documented golden constants; (2) predicate strings == numeric thresholds; (3) the rules document named in the JSON
    exists next to the JSON and its file bytes hash to the recorded SHA256 (if require_document). Raises ValueError on any mismatch."""
    cfg = cfg or RULES; mism = {k: (getattr(cfg, k), v) for k, v in GOLDEN.items() if getattr(cfg, k) != v}
    if mism: raise ValueError(f'rules_tables binding mismatch: {mism}')
    j = json.loads(open(cfg.path, 'rb').read().decode('utf-8')); _check_predicates(j, cfg)
    doc = os.path.join(os.path.dirname(cfg.path), j['rules_document']['name']); doc_state = 'not_present'
    if os.path.exists(doc):
        actual = hashlib.sha256(open(doc, 'rb').read()).hexdigest()
        if actual != cfg.rules_document_sha256: raise ValueError('rules document bytes do not match rules_document.sha256')
        doc_state = 'verified'
    elif require_document: raise ValueError('rules document not present next to the tables (cannot verify document SHA)')
    return dict(ok=True, tables_sha256=cfg.tables_sha256, rules_document_sha256=cfg.rules_document_sha256, document_state=doc_state)


RULES = _load(os.environ.get('STEP1_RULES_TABLES', DEFAULT_PATH))
BINDING = verify_binding(RULES, require_document=(os.environ.get('STEP1_RULES_REQUIRE_DOC', '1') == '1'))   # executed at import: a mismatching JSON/document cannot be used silently
