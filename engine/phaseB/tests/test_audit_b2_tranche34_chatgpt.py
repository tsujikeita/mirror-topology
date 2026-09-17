"""Complete-asset vs per-manifest intake, binding and reuse.
E7 design metadata is from frozen A6/A7. W2 and numerical banks are synthetic;
W2 uses an explicit mean-distance test statistic, never labeled exact POT.
Metadata changes occur only in copies, without changing any scientific rules.
"""
import os,sys,copy,pickle
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]));sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from step1_engine import twelve_assets as ta,stage12,serialization as ser
from step1_engine.grid_registry import load_registry,registry_from_dict
from step1_engine.errors import InputContractError
from test_b2_tranche20 import A6,A7

@pytest.fixture
def reg():return load_registry(A7,A6)
@pytest.fixture
def asset(reg):return ta.build_twelve_assets(reg,['E7'])

def test_normal_manifest_reuse_no_regeneration(reg,asset,monkeypatch):
 def forbidden(*a,**k):raise AssertionError('regeneration on registered reuse')
 monkeypatch.setattr(stage12,'generate_twelve',forbidden)
 for size in reg.surviving['E7']:
  m=asset.get('E7',size,asset.manifests['E7'][size].sha256)
  assert stage12.verify_twelve_registered(m)

@pytest.mark.parametrize('field,value',[('sha256',''),('registry_sha256','0'*64),('generator',{}),('families',[])])
def test_get_checks_asset_envelope(asset,field,value):
 bad=copy.deepcopy(asset);setattr(bad,field,value)
 with pytest.raises(InputContractError):bad.get('E7','L1.00')

def test_get_checks_key_vs_member_identity(asset):
 bad=copy.deepcopy(asset);bad.manifests['E7']['L1.00']=bad.manifests['E7']['L1.50']
 with pytest.raises(InputContractError):bad.get('E7','L1.00')

def test_intake_rejects_internal_registry(reg,asset):
 internal=registry_from_dict(ser.loads(ser.dumps(reg.as_dict())))
 with pytest.raises(InputContractError):ta.verify_twelve_assets(copy.deepcopy(asset),internal,asset.sha256)

@pytest.mark.parametrize('change',['empty','duplicate','extra_mapping'])
def test_intake_exact_family_inventory(reg,asset,change):
 bad=copy.deepcopy(asset)
 if change=='empty':bad.families=[]
 elif change=='duplicate':bad.families=['E7','E7']
 else:bad.manifests['E999']={}
 bad.sha256=bad.payload_sha()
 with pytest.raises(InputContractError):ta.verify_twelve_assets(bad,reg,bad.sha256)

def test_failed_intake_cannot_issue_asset(reg,asset):
 ta._VERIFIED.clear();bad=ta.asset_from_dict(ser.loads(ser.dumps(asset.as_dict())));bad.sha256='0'*64
 with pytest.raises(InputContractError):ta.verify_twelve_assets(bad,reg)
 with pytest.raises(InputContractError):bad.get('E7','L1.00')

def test_failed_intake_does_not_publish_partial_cache(reg,asset):
 ta._VERIFIED.clear();bad=ta.asset_from_dict(ser.loads(ser.dumps(asset.as_dict())));bad.sha256='0'*64
 with pytest.raises(InputContractError):ta.verify_twelve_assets(bad,reg)
 assert not ta._VERIFIED

def test_false_switch_cannot_skip_unverified_regeneration(asset):
 m=copy.deepcopy(asset.manifests['E7']['L1.00']);m.added=m.added[::-1];m.points=m.anchors+m.added;m.sha256=stage12.payload_sha(m.payload())
 ta._VERIFIED.clear()
 with pytest.raises(InputContractError):stage12.verify_twelve(m)
 with pytest.raises(InputContractError):ta.verify_twelve_cached(m,regenerate=False)

def test_cold_restore_requires_intake_and_roundtrips(reg,asset):
 new=ta.asset_from_dict(ser.loads(ser.dumps(asset.as_dict())));ta._VERIFIED.clear()
 with pytest.raises(InputContractError):new.get('E7','L1.00')
 assert ta.verify_twelve_assets(new,reg,asset.sha256)['ok']
 for size in reg.surviving['E7']:assert new.get('E7',size).payload()==asset.manifests['E7'][size].payload()

def test_returned_manifest_does_not_mutate_asset(asset):
 before=ser.dumps(asset.as_dict());m=asset.get('E7','L1.00')
 try:m.points[3][0]+=.001
 except (AttributeError,TypeError):pass
 assert ser.dumps(asset.as_dict())==before

def test_unknown_sha_falls_back_to_full_regeneration(reg,monkeypatch):
 m=stage12.generate_twelve('E7','L1.00',np.asarray(reg.anchors['E7']));ta._VERIFIED.clear();calls=[];real=stage12.generate_twelve
 def wrapped(*a,**kw):calls.append(1);return real(*a,**kw)
 monkeypatch.setattr(stage12,'generate_twelve',wrapped)
 assert stage12.verify_twelve_registered(m);assert calls==[1]
 assert stage12.verify_twelve_registered(m);assert calls==[1]

def test_asset_expected_sha_mismatch_rejected(reg,asset):
 with pytest.raises(InputContractError):ta.verify_twelve_assets(asset,reg,'0'*64)

def test_changed_points_keep_old_sha_rejected(asset):
 bad=copy.deepcopy(asset);bad.manifests['E7']['L1.00'].points[3][0]+=.001
 with pytest.raises(InputContractError):bad.get('E7','L1.00')

@pytest.fixture(scope='module')
def fixture():
 cache=Path(os.environ.get('AUDIT34_CACHE','')) if os.environ.get('AUDIT34_CACHE') else None
 if cache is not None and (cache/'base.pkl').exists():
  with (cache/'base.pkl').open('rb') as h:b=pickle.load(h)
  with (cache/'twelve.pkl').open('rb') as h:t=pickle.load(h)
  return b,t
 from fixture32 import base,twelve_from_cases          # regenerate the audit fixture in-process (no pickle cache distributed)
 b=base();t=twelve_from_cases(b['cases']);return b,t

def full_eval(b,t,asset=None):
 from step1_engine import integrated_runner as ir,threshold_evaluator as te
 views={k.split('/')[1]:v for k,v in b['cases'].items()}
 parents=ir.assemble_parent(b['reg'],b['man'],'E7',{s:v[:2] for s,v in views.items()})
 return te.evaluate_family_full(b['reg'],b['man'],'E7',parents,views,b['ctx'],b['ctx'].context_sha256,100.,550.,t,with_diagnostics=False,twelve_assets=asset)

def test_evaluator_rejects_wrong_registry_asset(fixture):
 b,t=fixture;bad=ta.build_twelve_assets(b['reg'],['E7']);bad.registry_sha256='0'*64
 with pytest.raises(InputContractError):full_eval(b,t,bad)

def test_evaluator_rejects_another_verified_anchor_design(fixture):
 b,t=fixture;bad=ta.build_twelve_assets(b['reg'],['E7']);A=np.array(b['reg'].anchors['E7']);A[0,0]+=.001
 other=stage12.generate_twelve('E7','L1.00',A);stage12.verify_twelve_registered(other)
 bad.manifests['E7']['L1.00']=other
 with pytest.raises(InputContractError):full_eval(b,t,bad)

def test_normal_evaluator_full_result_matches_cold(fixture,monkeypatch):
 b,t=fixture;a=ta.build_twelve_assets(b['reg'],['E7']);r0=full_eval(b,t)
 from step1_engine import threshold_evaluator as te
 def forbidden(*a,**k):raise AssertionError('unexpected generator after intake')
 monkeypatch.setattr(stage12,'generate_twelve',forbidden);monkeypatch.setattr(te,'generate_twelve',forbidden)
 r1=full_eval(b,t,a)
 assert ser.dumps(r0.twelve)==ser.dumps(r1.twelve)
 assert r0.required_manifests==r1.required_manifests and r0.eligible_truths==r1.eligible_truths

def test_runner_pins_manifest_asset_through_pseudos(fixture,tmp_path,monkeypatch):
 from step1_engine import integrated_runner as ir
 from step1_engine.archive import Archive
 b,t=fixture;a=ta.build_twelve_assets(b['reg'],['E7']);A=np.array(b['reg'].anchors['E7']);A[0,0]+=.001
 other=stage12.generate_twelve('E7','L1.00',A);stage12.verify_twelve_registered(other)
 original=ir.evaluate_family_full;seen=[]
 def wrap(*args,**kw):
  # Alter the actually consumed object, not an unused original caller copy.
  if seen:kw['twelve_assets'].manifests['E7']['L1.00']=copy.deepcopy(other)
  out=original(*args,**kw);seen.append(out.required_manifests.get('L1.00'));return out
 monkeypatch.setattr(ir,'evaluate_family_full',wrap)
 with pytest.raises(InputContractError):
  ir.run_first_wave(b['reg'],b['man'],b['cases'],b['ctx'],b['ctx'].context_sha256,(100.,550.),[100.],[550.],Archive(str(tmp_path/'run')),twelve_inputs={'E7':t},twelve_assets=a)
