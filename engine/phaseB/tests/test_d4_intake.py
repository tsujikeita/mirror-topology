# -*- coding: utf-8 -*-
"""D4-3 / D4-5 contracts: (a) integrated runner reuses a REGISTERED twelve asset by receipt with zero generator calls (unregistered receipt / non-intaken asset / SHA mismatch refused);
(b) production covariance intake re-verifies everything at load time and refuses swapped configs, edited files/sidecars, wrong receipt (pass_ flags not trusted)."""
import os, sys, json, hashlib, shutil, copy
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); MT = os.environ.get('B3_MT', '/home/claude/mt'); D1 = os.path.join(P, 'registered_assets', 'd1'); RA = os.path.join(P, 'registered_assets')
from step1_engine.errors import InputContractError
from step1_engine.grid_registry import load_registry; from step1_engine.grid_manifest import build_configuration_manifest
from step1_engine.production import intake_registered_covariance
from step1_engine import twelve_assets as ta, stage12
from step1_engine.twelve_assets import intake_registered_twelve_assets, build_twelve_assets
A7 = os.path.join(P, 'tests/assets/a7_circle_geometry.csv'); A6 = os.path.join(P, 'tests/assets/a6_observer_design_points.json')
need_mt = pytest.mark.skipif(not os.path.exists(os.path.join(MT, 't1_engine.py')), reason='frozen mirror-topology checkout not present')

@need_mt
def test_covariance_intake_reverifies_and_refuses(tmp_path):
    reg = load_registry(A7, A6); man = build_configuration_manifest(reg)
    r = intake_registered_covariance(30101, reg, D1, MT); assert r['family'] == 'E7' and r['observer_id'] == 1 and r['roots_info']['matched']['clip'] == 0 and r['S_matched'].shape == (21, 21) and r['eig']['min'] > 0
    assert r['loader']['t1_engine_sha256'] == '87bf8424073af021264b12fe312ab5255b71008bdd5fe874d164d48daf034dc8' and r['trusted_anchors']['registry_sha256'].startswith('3b32c91f')
    for bad in (30101.9, True, '30101'):
        with pytest.raises(InputContractError): intake_registered_covariance(bad, reg, D1, MT)                                          # strict integer id
    with pytest.raises(InputContractError): intake_registered_covariance(99999, reg, D1, MT)
    with pytest.raises(InputContractError): intake_registered_covariance(30101, reg, D1, MT, receipt_id='other')
    from step1_engine.grid_registry import registry_from_dict; from step1_engine import serialization as ser
    internal = registry_from_dict(ser.loads(ser.dumps(reg.as_dict())))
    with pytest.raises(InputContractError): intake_registered_covariance(30101, internal, D1, MT)                                       # internal-consistency-only registry refused
    # (A) self-consistent tampering (npy x2 + sidecar + registry + local receipt SHAs updated) is refused by the trusted anchors
    d2 = tmp_path / 'd1'; shutil.copytree(D1, d2); reg2 = json.load(open(d2 / 'd1_cov_registry.json')); f = d2 / reg2['configurations']['30101']['cov_file']; mf = str(f) + '.manifest.json'
    a = np.load(f) * 2; np.save(f, a); sh = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest(); rec = json.load(open(mf)); rec['cov_file_sha256'] = sh(f); rec['cov_array_sha256'] = hashlib.sha256(np.load(f).tobytes()).hexdigest(); json.dump(rec, open(mf, 'w'), indent=1)
    reg2['configurations']['30101']['cov_file_sha256'] = rec['cov_file_sha256']; reg2['configurations']['30101']['cov_array_sha256'] = rec['cov_array_sha256']; json.dump(reg2, open(d2 / 'd1_cov_registry.json', 'w'), indent=1)
    rc = json.load(open(d2 / 'd1_receipt.json')); rc['registered']['files'][os.path.basename(f)] = sh(f); rc['registered']['files'][os.path.basename(mf)] = sh(mf); rc['outputs']['cov_registry_sha256'] = sh(d2 / 'd1_cov_registry.json'); json.dump(rc, open(d2 / 'd1_receipt.json', 'w'), indent=1)
    with pytest.raises(InputContractError): intake_registered_covariance(30101, reg, str(d2), MT)
    d3 = tmp_path / 'd3'; shutil.copytree(D1, d3); mf3 = str(d3 / reg2['configurations']['30101']['cov_file']) + '.manifest.json'; rec3 = json.load(open(mf3)); rec3['manifest']['x0'][0] += 1e-6; json.dump(rec3, open(mf3, 'w'))
    with pytest.raises(InputContractError): intake_registered_covariance(30101, reg, str(d3), MT)                                       # edited sidecar (receipt file SHA / bytes)

@need_mt
def test_covariance_intake_refuses_substituted_loader(tmp_path, monkeypatch):
    import types, sys as _sys
    reg = load_registry(A7, A6); fake = types.ModuleType('t1_engine'); fake.__file__ = str(tmp_path / 'other' / 't1_engine.py'); fake.load_cov_full = lambda p, l: (None, 7 * np.eye(21), dict(cov_array_sha256=hashlib.sha256(np.load(p).tobytes()).hexdigest()))
    monkeypatch.setitem(_sys.modules, 't1_engine', fake)
    with pytest.raises(InputContractError): intake_registered_covariance(30101, reg, D1, MT)                                            # (B) a different already-loaded t1_engine is refused
    monkeypatch.delitem(_sys.modules, 't1_engine', raising=False)
    mt2 = tmp_path / 'mt2'; shutil.copytree(MT, mt2, ignore=shutil.ignore_patterns('.git', '__pycache__', 'results')); (mt2 / 't1_engine.py').write_text(open(os.path.join(MT, 't1_engine.py')).read() + '\n# edited\n')
    with pytest.raises(InputContractError): intake_registered_covariance(30101, reg, D1, str(mt2))                                     # loader bytes differ from the frozen SHA

def test_runner_registered_twelve_asset_reuse_without_regeneration(monkeypatch, tmp_path):
    from fixture32 import base; from step1_engine import integrated_runner as ir; from step1_engine.archive import Archive
    b = base(); reg = b['reg']; ta._VERIFIED.clear()
    asset = intake_registered_twelve_assets(os.path.join(RA, 'b3_2_twelve_assets.json'), reg, 'B3_2A_7240c06f255c')
    calls = []; orig = stage12.generate_twelve; monkeypatch.setattr(stage12, 'generate_twelve', lambda *a, **k: (calls.append(a), orig(*a, **k))[1]); monkeypatch.setattr(ir, 'generate_twelve', stage12.generate_twelve)
    rm = ir.run_first_wave(reg, b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, (80., 400.), np.array([80.]), np.array([400.]), Archive(str(tmp_path / 'a')), 'smoke', twelve_assets=asset, expected_twelve_assets_sha256=asset.sha256, twelve_assets_receipt='B3_2A_7240c06f255c')
    assert calls == [] and rm.binding['twelve_assets_intake']['mode'] == 'registered_receipt' and rm.binding['twelve_assets_sha256'] == asset.sha256
    with pytest.raises(InputContractError): ir.run_first_wave(reg, b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, (80., 400.), np.array([80.]), np.array([400.]), Archive(str(tmp_path / 'b')), 'smoke', twelve_assets=asset, expected_twelve_assets_sha256=asset.sha256, twelve_assets_receipt='nonexistent')
    with pytest.raises(InputContractError): ir.run_first_wave(reg, b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, (80., 400.), np.array([80.]), np.array([400.]), Archive(str(tmp_path / 'd')), 'smoke', twelve_assets=None, twelve_assets_receipt='unknown-receipt-without-asset')   # RD4T1-D
    fresh = build_twelve_assets(reg, families=['E7']); ta._VERIFIED.clear(); fresh._intake_sha256 = None
    with pytest.raises(InputContractError): ir.run_first_wave(reg, b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, (80., 400.), np.array([80.]), np.array([400.]), Archive(str(tmp_path / 'c')), 'smoke', twelve_assets=fresh, expected_twelve_assets_sha256=fresh.sha256, twelve_assets_receipt='B3_2A_7240c06f255c')   # not the registered asset

def test_pseudo_full_twelve_results_are_archived_and_restorable(tmp_path):
    from fixture32 import base, twelve_from_cases; from step1_engine import integrated_runner as ir; from step1_engine.archive import Archive, ArchiveRef; from step1_engine import serialization as ser
    b = base(); ti = twelve_from_cases(b['cases']); arc = Archive(str(tmp_path / 'a'))
    rm = ir.run_first_wave(b['reg'], b['man'], b['cases'], b['ctx'], b['ctx'].context_sha256, (200., 1000.), np.array([100.]), np.array([550.]), arc, 'smoke', twelve_inputs={'E7': ti})
    st = rm.per_pseudo_family_status[0]['E7']
    if st['twelve'] is not None:                                                                            # pseudo triggered the 12-position stage: the full Result must be archived and restorable
        assert 'twelve_full_result_ref' in st; g = arc.get(ArchiveRef(**st['twelve_full_result_ref'])); assert g['family'] == 'E7' and len(g['per_config']) == 36 and g['evidence']['pseudo_index'] == 0
        assert hashlib.sha256(ser.dumps(g).encode()).hexdigest() == st['twelve_full_result_sha256'] or st['twelve_full_result_ref']['sha256'] == st['twelve_full_result_sha256']
    else: pytest.skip('fixture pseudo did not trigger the 12-position stage')

@need_mt
def test_bridge_from_another_search_path_is_refused(tmp_path, monkeypatch):
    """RD4T1-B (v3): with mt_root already LATER in sys.path and a foreign t2b2_bridge earlier, a normal import would bind t1.br to the foreign bridge; the helper must promote mt_root and verify the bridge actually referenced."""
    import sys as _sys; reg = load_registry(A7, A6); other = tmp_path / 'other'; other.mkdir(); (other / 't2b2_bridge.py').write_text('# TEST-ONLY foreign bridge\nEXPECTED = {}\n')
    for n in ('t1_engine', 't2b2_bridge'): monkeypatch.delitem(_sys.modules, n, raising=False)
    monkeypatch.setattr(_sys, 'path', [str(other), MT] + [p for p in _sys.path if p not in (str(other), MT)])
    r = intake_registered_covariance(30101, reg, D1, MT); assert os.path.realpath(r['loader']['t2b2_bridge_path']) == os.path.realpath(os.path.join(MT, 't2b2_bridge.py'))   # bridge verified from the actual module, not the foreign one
