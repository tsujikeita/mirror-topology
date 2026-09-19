"""Real caller connection using pre-existing finite synthetic fixture.
W2 fixture uses explicitly test-only mean-distance; no physical CMB/OT claim.
Registered 12-position file bytes are the real accepted asset. Regeneration of
E2/E8 is forbidden, not run; this test does not alter source files.
"""
from pathlib import Path
import os,sys,json
import pytest,numpy as np
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]));sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from fixture32 import base,twelve_from_cases
from step1_engine import twelve_assets as ta,threshold_evaluator as te,integrated_runner as ir,serialization as ser
from step1_engine.archive import Archive
P=ROOT/'registered_assets/b3_2_twelve_assets.json'
RID='B3_2A_7240c06f255c'
@pytest.fixture(scope='module')
def data():
 b=base();return b,twelve_from_cases(b['cases'])
def test_registered_asset_full_evaluator_matches_regenerating_e7(data,monkeypatch):
 b,t=data;reg=b['reg'];views={k.split('/')[1]:v for k,v in b['cases'].items()}
 parents=ir.assemble_parent(reg,b['man'],'E7',{s:v[:2] for s,v in views.items()})
 cold=te.evaluate_family_full(reg,b['man'],'E7',parents,views,b['ctx'],b['ctx'].context_sha256,100.,550.,t,with_diagnostics=False)
 a=ta.intake_registered_twelve_assets(str(P),reg,RID)
 def no(*a,**k):raise AssertionError('consumer unexpectedly regenerated lattice')
 monkeypatch.setattr(te,'generate_twelve',no)
 from step1_engine import stage12
 monkeypatch.setattr(stage12,'generate_twelve',no)
 warm=te.evaluate_family_full(reg,b['man'],'E7',parents,views,b['ctx'],b['ctx'].context_sha256,100.,550.,t,with_diagnostics=False,twelve_assets=a)
 assert ser.dumps(cold.twelve)==ser.dumps(warm.twelve)
 assert cold.eligible_truths==warm.eligible_truths and cold.required_manifests==warm.required_manifests

def test_full_runner_with_real_fixture_reenters_e2_regeneration(data,tmp_path,monkeypatch):
 b,t=data;a=ta.intake_registered_twelve_assets(str(P),b['reg'],RID);calls=[]
 class Reentered(Exception):pass
 def no(m):calls.append([m.family,m.size_id]);raise Reentered()
 monkeypatch.setattr(ta,'verify_twelve',no)
 with pytest.raises(Reentered):
  ir.run_first_wave(b['reg'],b['man'],b['cases'],b['ctx'],b['ctx'].context_sha256,(100.,550.),[100.],[550.],Archive(str(tmp_path/'ar')),twelve_inputs={'E7':t},twelve_assets=a,expected_twelve_assets_sha256=a.sha256)
 assert calls==[['E2','L1.00']]
