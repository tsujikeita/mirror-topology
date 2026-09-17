# -*- coding: utf-8 -*-
"""B-2 tranche 17: adopted plan_io schema fixes; grid registry bound to the frozen A6/A7 assets; content-addressed archive with transition resolution."""
import os, sys, copy, json, shutil
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from step1_engine.grid_registry import load_registry, registry_from_dict, registry_from_dict_bound, A6_SHA, A7_SHA
from step1_engine.archive import Archive, ArchiveRef, archive_three_position_result, resolve_transition_archive
from step1_engine.stage12 import generate_twelve, transition_after_three
from step1_engine.coordinator import plan_family_expansion
from step1_engine.errors import InputContractError
from step1_engine import serialization as ser
ASSETS = os.path.join(os.path.dirname(__file__), 'assets'); A7 = os.path.join(ASSETS, 'a7_circle_geometry.csv'); A6 = os.path.join(ASSETS, 'a6_observer_design_points.json')   # frozen A6/A7 members (SHA-checked by the loader)
frozen = pytest.mark.skipif(not (os.path.exists(A7) and os.path.exists(A6)), reason='frozen A6/A7 assets not present')

@frozen
def test_registry_from_frozen_assets(tmp_path):
    reg = load_registry(A7, A6); assert reg.validate() and reg.n_configurations == 30 and reg.surviving == {f: ['L1.00', 'L1.20', 'L1.50'] for f in ('E1', 'E2', 'E7', 'E8')}
    assert reg.size_prior['E7'] == {'L1.00': 1 / 3, 'L1.20': 1 / 3, 'L1.50': 1 / 3} and reg.anchors['E1'] == [] and len(reg.anchors['E7']) == 3 and reg.status['E7']['L1.00']['geometric_status'] == 'zero_radius_boundary'
    d = ser.loads(ser.dumps(reg.as_dict())); reg2 = registry_from_dict(d); assert reg2.registry_sha256 == reg.registry_sha256 and 'not_verified' in reg2.verification_scope
    assert registry_from_dict_bound(d, A7, A6).verification_scope.startswith('source_bound')
    d2 = copy.deepcopy(d); d2['surviving']['E7'].append('L0.85')
    with pytest.raises(InputContractError): registry_from_dict(d2)                                         # excluded size cannot be declared surviving
    d3 = copy.deepcopy(d); d3['size_prior']['E7']['L1.00'] = 0.5
    with pytest.raises(InputContractError): registry_from_dict(d3)
    bad = str(tmp_path / 'a7.csv'); shutil.copy(A7, bad); open(bad, 'a').write('\n')
    with pytest.raises(InputContractError): load_registry(bad, A6)                                            # asset SHA drift
    # anchors from the registry feed the registered 12-position generator; the registry sizes are the expected surviving set of the coordinator
    m = generate_twelve('E7', 'L1.00', np.array(reg.anchors['E7'])); assert len(m.points) == 12
    src = lambda s: dict(family='E7', size_id=s, truths=dict(support=True, strong=False, unsupported=False), decision=dict(technical_status='ok'), precision=dict(state='pass'), evidence=dict(coverage_ok=True))
    tr = {s: transition_after_three('E7', s, src(s), dict(state='not-expanded', expand=False), None) for s in reg.surviving['E7']}
    assert plan_family_expansion('E7', reg.surviving['E7'], tr).status == 'final at 3 positions'

def test_archive_put_get_and_transition_resolution(tmp_path):
    a = Archive(str(tmp_path / 'arc')); res = dict(family='E7', size_id='L1.00', truths=dict(support=True, strong=False, unsupported=False), decision=dict(technical_status='ok'), precision=dict(state='pass'), evidence=dict(coverage_ok=True))
    ref = archive_three_position_result(a, res, 'E7', 'L1.00'); t = transition_after_three('E7', 'L1.00', res, dict(state='not-expanded', expand=False), None)
    assert ref.sha256 == t.three_position_result_sha256 and resolve_transition_archive(a, t, ref)['family'] == 'E7' and a.verify_all()['entries'] == 1
    with pytest.raises(InputContractError): a.get(ArchiveRef(ref.kind, '0' * 64, ref.path, ref.identity))
    with pytest.raises(InputContractError): resolve_transition_archive(a, t, ArchiveRef('twelve_manifest', ref.sha256, ref.path, ref.identity))
    p = os.path.join(a.root, ref.path); open(p, 'a').write(' ')
    with pytest.raises(InputContractError): a.get(ref)                                                        # bytes drift behind a valid reference
    with pytest.raises(InputContractError): a.verify_all()
    with pytest.raises(InputContractError): archive_three_position_result(a, res, 'E8', 'L1.00')
    with pytest.raises(InputContractError): a.put('unknown_kind', res, {})
