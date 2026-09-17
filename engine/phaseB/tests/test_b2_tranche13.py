# -*- coding: utf-8 -*-
"""B-2 tranche 13: StageTransition.validate (adopted), family coordinator (expand all surviving sizes; family completion), streamed greedy equivalence on a small 2-D lattice."""
import os, sys, copy
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from dataclasses import replace
from step1_engine.rules_config import RULES
from step1_engine.stage12 import generate_twelve, transition_after_three, after_twelve, StageTransition
from step1_engine.coordinator import plan_family_expansion, family_completion
from step1_engine.observers12 import greedy_maximin, lattice_1d, dist_euclid, dist_torus_halfturn
from step1_engine.observers12_stream import greedy_maximin_streamed
from step1_engine.errors import InputContractError
A7 = np.array([[.11278702805018147], [.04504442885635738], [.17608175443077442]])

def src(size, tech='ok'): return dict(family='E7', size_id=size, truths=dict(support=True, strong=False, unsupported=False), decision=dict(technical_status=tech), precision=dict(state='pass'), evidence=dict(coverage_ok=True))
def r12(size, man): return dict(family='E7', size_id=size, evidence=dict(stage='12-position', coverage_ok=True, twelve_manifest_sha256=man.sha256), decision=dict(technical_status='ok'), precision=dict(state='pass'))

def test_transition_validate_on_restore():
    m = generate_twelve('E7', 'L1.00', A7); t = transition_after_three('E7', 'L1.00', src('L1.00'), dict(state='position-sensitive', expand=True), m)
    for bad in (replace(t, expand='False'), replace(t, three_technical_status='technical_fail'), replace(t, position_state='not-expanded'), replace(t, three_position_result_sha256='not-a-sha'), replace(t, size_id='')):
        with pytest.raises(InputContractError): after_twelve(bad, r12('L1.00', m), 'not-expanded')
    c = after_twelve(t, r12('L1.00', m), 'not-expanded'); assert c['local_completion_checks_passed'] is True and c['final_label_released'] is False and 'NOT a released label' in c['scope']

def test_family_coordinator_expands_all_surviving_sizes():
    sizes = ['L1.00', 'L1.20', 'L1.50']; mans = {s: generate_twelve('E7', s, A7) for s in sizes}
    tr = {'L1.00': transition_after_three('E7', 'L1.00', src('L1.00'), dict(state='position-sensitive', expand=True), mans['L1.00']),
          'L1.20': transition_after_three('E7', 'L1.20', src('L1.20'), dict(state='not-expanded', expand=False), None),
          'L1.50': transition_after_three('E7', 'L1.50', src('L1.50'), dict(state='position-unresolved', expand=False), None)}
    with pytest.raises(InputContractError): plan_family_expansion('E7', sizes, tr, manifests={'L1.00': mans['L1.00']})               # one triggered size requires manifests for ALL surviving sizes
    plan = plan_family_expansion('E7', sizes, tr, manifests=mans); assert plan.expand_family and set(plan.required_manifests) == set(sizes) and 'family rule' in plan.reasons[0]
    with pytest.raises(InputContractError): plan_family_expansion('E7', sizes, {k: v for k, v in tr.items() if k != 'L1.50'}, manifests=mans)   # exact size inventory
    comp = family_completion(plan, {s: r12(s, mans[s]) for s in sizes}, {s: 'not-expanded' for s in sizes}, mans); assert comp['family_local_completion'] is True and comp['final_label_released'] is False
    bad = {s: r12(s, mans[s]) for s in sizes}; bad['L1.20']['precision']['state'] = 'precision-unresolved'
    assert family_completion(plan, bad, {s: 'not-expanded' for s in sizes}, mans)['family_local_completion'] is False                    # one size blocks the family
    with pytest.raises(InputContractError): family_completion(plan, {s: r12(s, mans[s]) for s in sizes[:2]}, {s: 'not-expanded' for s in sizes}, mans)
    tr2 = dict(tr); tr2['L1.00'] = transition_after_three('E7', 'L1.00', src('L1.00'), dict(state='not-expanded', expand=False), None)
    p2 = plan_family_expansion('E7', sizes, tr2); assert not p2.expand_family and p2.status.startswith('provisional / position-unresolved')
    tr3 = dict(tr2); tr3['L1.50'] = transition_after_three('E7', 'L1.50', src('L1.50', 'technical_fail'), dict(state='not-expanded', expand=False), None)
    assert plan_family_expansion('E7', sizes, tr3).status == 'technical_fail'
    e1 = {s: transition_after_three('E1', s, dict(src(s), family='E1'), dict(state='not-expanded', expand=False), None) for s in sizes}; assert plan_family_expansion('E1', sizes, e1).status.startswith('exempt')

def test_streamed_greedy_equals_in_memory_on_small_lattice():
    ax0, ax1 = lattice_1d(0.03, 0.47, 5e-3), lattice_1d(0.02, 0.23, 5e-3); g = np.meshgrid(ax0, ax1, indexing='ij'); cand = np.column_stack([g[0].ravel(), g[1].ravel()])
    anchors = np.array([[0.21609142351830096, 0.1388778490467109], [0.10991624390681737, 0.06676051199330066], [0.4225612190131215, 0.125548183938205]])
    a = greedy_maximin(cand, anchors, 9, 0.04, dist_euclid); b = greedy_maximin_streamed(ax0, ax1, anchors, 9, 0.04, dist_euclid, rows_per_block=7)
    assert np.allclose(a, b, rtol=0, atol=0)
    ex = lambda blk: blk[np.all([dist_torus_halfturn(blk, f) >= 0.05 for f in np.array([[0, 0], [0, .5], [.5, 0], [.5, .5]])], axis=0)]
    t0, t1 = lattice_1d(0.0, 1.0, 2e-2), lattice_1d(0.0, 1.0, 2e-2); gg = np.meshgrid(t0, t1, indexing='ij'); cc = ex(np.column_stack([gg[0].ravel(), gg[1].ravel()]))
    an2 = np.array([[0.2452274712376159, 0.3429926323318836], [0.07150075549277313, 0.24162711619922894], [0.8951290935216393, 0.2514647338918028]])
    a2 = greedy_maximin(cc, an2, 9, 0.05, dist_torus_halfturn); b2 = greedy_maximin_streamed(t0, t1, an2, 9, 0.05, dist_torus_halfturn, exclusion=ex, rows_per_block=13); assert np.allclose(a2, b2, rtol=0, atol=0)
