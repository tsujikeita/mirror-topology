# -*- coding: utf-8 -*-
"""B-2 tranche 21: adopted tranche-20 audit fixes; official-entry hard gate (registered profile, identity conditioning, environment lock, threads) — smoke vs official semantics."""
import os, sys, copy
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from step1_engine.rules_config import RULES
from step1_engine.grid_registry import load_registry
from step1_engine.production import production_manifest, build_family_input
from step1_engine.official_gate import official_gate, require_official, EXPECTED_VERS, current_env
from step1_engine.errors import InputContractError
from test_b2_tranche20 import synthetic_supplies, A7, A6

def build_pair():
    reg = load_registry(A7, A6); man = production_manifest(reg); sm, plans, fplans = synthetic_supplies(man, 'E7', 'matched'); sn, _, _ = synthetic_supplies(man, 'E7', 'native')
    return reg, man, build_family_input(reg, man, 'E7', 'matched', sm, plans, fplans), build_family_input(reg, man, 'E7', 'native', sn, plans, fplans), sm, plans, fplans

def test_official_gate_rejects_test_profile_and_records_diagnostics():
    reg, man, fm, fn, sm, plans, fplans = build_pair(); lock = dict(EXPECTED_VERS, blas_threads=[dict(api='blas', n=2)])
    g = official_gate(fm, fn, 'official', env=lock); assert g.passed is False and any('m=' in x for x in g.required_failures) and any('N0=' in x for x in g.required_failures) and any('B=' in x for x in g.required_failures) and any('N_fit' in x for x in g.required_failures)
    assert not any('grid identity' in x for x in g.required_failures) and not any('covariance metadata' in x for x in g.required_failures)   # identity and cov binding are fine in this fixture
    with pytest.raises(InputContractError): require_official(fm, fn, env=lock)
    s = official_gate(fm, fn, 'smoke', env=current_env()); assert s.passed is True and s.diagnostics['profile_failures'] and 'version_mismatch' in s.diagnostics   # smoke: structural only, sizes/versions recorded

def test_official_gate_environment_threads_and_conditioning():
    reg, man, fm, fn, sm, plans, fplans = build_pair(); lock = dict(EXPECTED_VERS, blas_threads=[dict(api='blas', n=2)])
    bad_env = dict(lock, numpy='2.4.0'); g = official_gate(fm, fn, 'official', env=bad_env); assert any('environment versions' in x for x in g.required_failures)
    g2 = official_gate(fm, fn, 'official', env=dict(lock, blas_threads=[dict(api='blas', n=4)])); assert any('BLAS threads' in x for x in g2.required_failures)
    g3 = official_gate(fm, None, 'official', env=lock); assert any('native input missing' in x for x in g3.required_failures)
    f2 = build_family_input(reg, man, 'E7', 'matched', [s for s in sm if s.config_id // 100 % 100 in (1, 2)], plans, fplans, size_ids=['L1.00', 'L1.20'])
    g4 = official_gate(f2, fn, 'official', env=lock); assert any('conditioning' in x for x in g4.required_failures)                       # matched L1.00+L1.20 vs native all sizes
    from dataclasses import replace
    g5 = official_gate(replace(fm, grid_identity=None), fn, 'smoke'); assert g5.passed is False and any('grid identity missing' in x for x in g5.required_failures)   # even smoke requires the wrapper identity
    with pytest.raises(InputContractError): official_gate(fm, fn, 'formal')
