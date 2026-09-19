# -*- coding: utf-8 -*-
"""B-3-3: registered assets produced on Colab (B-3-2 A/B, commit 7240c06f…) are bound to the packet by receipt: file SHA, asset SHA, registry binding, structural manifest checks,
shared-null validate; tampered files / wrong receipt are refused; the registered shared null re-validates (payload SHA) and carries the registered inventory."""
import os, sys, json, hashlib, copy
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine.twelve_assets import intake_registered_twelve_assets, REGISTERED_RECEIPTS
from step1_engine.grid_registry import load_registry
from step1_engine.w2_shared import SharedNullAsset
from step1_engine.rules_config import RULES
from step1_engine.errors import InputContractError
from step1_engine import serialization as ser
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); RA = os.path.join(P, 'registered_assets'); A7 = os.path.join(P, 'tests/assets/a7_circle_geometry.csv'); A6 = os.path.join(P, 'tests/assets/a6_observer_design_points.json')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
REG = dict(twelve_file='be6860ba2ffbdd798d8a300b2268281bbade1d2b7f33b5b0748dc550ef90d557', twelve_asset='1d05e6b3afc86f8da94765cebe128f2b291bc523c10599dcb6e54ff7be01d89c', geometry_csv='c0f0bf0eb7ca3fadee70d2437443e926bed65ac5a89685b7a2c712a7dffab641', null_file='cc67686744f513e3123de2fb8353d79491d4b1deaff2b8d9ecb5f93d0f95afb4', null_asset='8348d5f4733ae5a37e39f4aa88109626e5caab312b55bd108be7ec9e5daff3ba')

def test_registered_twelve_assets_by_receipt(tmp_path):
    assert sha(os.path.join(RA, 'b3_2_twelve_assets.json')) == REG['twelve_file'] and sha(os.path.join(RA, 'b3_2_twelve_geometry.csv')) == REG['geometry_csv']
    reg = load_registry(A7, A6); a = intake_registered_twelve_assets(os.path.join(RA, 'b3_2_twelve_assets.json'), reg, 'B3_2A_7240c06f255c')
    assert a.sha256 == REG['twelve_asset'] and a.verification['manifests'] == 9 and all(len(a.get(f, s).points) == 12 for f in ('E2', 'E7', 'E8') for s in reg.surviving[f])
    assert a.get('E2', 'L1.00').generator['backend'] == 'streamed_two_pass' and a.get('E2', 'L1.00').min_pairwise >= RULES.min_sep['E2']
    with pytest.raises(InputContractError): intake_registered_twelve_assets(os.path.join(RA, 'b3_2_twelve_assets.json'), reg, 'nonexistent')
    d = json.load(open(os.path.join(RA, 'b3_2_twelve_assets.json'))); d['manifests']['E7']['L1.00']['points'][5][0] += 1e-4; p = tmp_path / 'bad.json'; json.dump(d, open(p, 'w'))
    with pytest.raises(InputContractError): intake_registered_twelve_assets(str(p), reg, 'B3_2A_7240c06f255c')                     # bytes differ from the receipt
    rows = [l for l in open(os.path.join(RA, 'b3_2_twelve_geometry.csv'))]; assert len(rows) == 109 and all('no_nondegenerate_circles' in l for l in rows[1:])

def test_registered_shared_null_validates():
    assert sha(os.path.join(RA, 'b3_2_shared_null_asset.json')) == REG['null_file']
    d = ser.loads(open(os.path.join(RA, 'b3_2_shared_null_asset.json')).read()); s = SharedNullAsset(**d); assert s.validate() and s.sha256 == REG['null_asset'] == d['sha256']
    assert set(s.null) == {2000, 5000} and all(len(s.null[n]['values']) == 1000 for n in s.null) and s.identity['distance_kind'] == 'exact_pot_w2' and s.identity['m'] == 100 and s.identity['iso']['K'] == 6000
    assert s.replicate_bounds is not None and all(len(s.replicate_bounds[n]) == 1000 for n in s.null)
    bad = copy.deepcopy(d); bad['null'][2000]['values'][0] += 1e-9
    with pytest.raises(InputContractError): SharedNullAsset(**bad).validate()
