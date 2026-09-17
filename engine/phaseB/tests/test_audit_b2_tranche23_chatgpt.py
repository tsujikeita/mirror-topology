"""Tranche23 audit. External regression TEST predicates are tested using a
controlled kernel double and a SHA-bound copy of the real A10 checkpoint. This
is not an execution of the actual external regression. Constructor tests use
synthetic assets with their own explicitly monkeypatched expected SHAs and an
analytic healpy double; never represent them as the official A5/healpy run.
"""
import os,sys,copy,hashlib,json,importlib.util,types
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]));sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import step1_engine.legacy_kernel as lk
from step1_engine.errors import InputContractError
BR=Path(os.environ.get('A10_BRIDGE',str(Path(__file__).resolve().parent/'reference_assets'/'t2b2_bridge.py')))
OFF=Path(os.environ.get('A10_CHECKPOINT',str(Path(__file__).resolve().parent/'reference_assets'/'a10a_calibration_official.npz')))
sha=lambda b:hashlib.sha256(b).hexdigest()
class AnalyticHP(types.ModuleType):
 def vec2ang(self,dirs):
  a=np.asarray(dirs).reshape(-1,3);r=np.sqrt(np.sum(a*a,axis=1))
  return np.arccos(np.clip(a[:,2]/r,-1.,1.)),np.mod(np.arctan2(a[:,1],a[:,0]),2*np.pi)
 def pix2vec(self,nside,pix):
  t=np.asarray(pix)*2*np.pi/3072
  return np.cos(t),np.sin(t),np.zeros_like(t)
 def vec2pix(self,nside,x,y,z):return np.arange(3072,dtype=np.int64)[::-1]
@pytest.fixture
def asset_bundle(tmp_path,monkeypatch):
 root=tmp_path/'mt';(root/'results/step1_phaseA/A5_freeze').mkdir(parents=True);(root/'docs').mkdir()
 # This is a unit-test asset bundle, not a replacement of frozen A5 artifacts.
 B=np.broadcast_to(np.eye(21),(3072,21,21)).copy();Bp=B.copy();Bm=2*B
 bp=root/'results/step1_phaseA/A5_freeze/s1_Bstack_l2_4_N16_common_v1.npz';np.savez_compressed(bp,Bp_stack=Bp,Bm_stack=Bm)
 cv=np.repeat([1064.7,504.6,286.7],[5,7,9]);np.savez(root/'docs/step0_frozen_Bpm_v1.npz',CVEC=cv)
 bridge=BR.read_bytes();assert sha(bridge)=='45107d1608d50816712f1aa452d9fa39af4adc9ec035fbe9279b264760d65872'
 (root/'t2b2_bridge.py').write_bytes(bridge)
 expected=dict(lk.ASSET_SHA,bstack=sha(bp.read_bytes()),bstack_array=sha(Bp.tobytes()+Bm.tobytes()),cvec_array=sha(cv.tobytes()),antipode=sha(np.arange(3072,dtype=np.int32)[::-1].tobytes()))
 monkeypatch.setattr(lk,'ASSET_SHA',expected);monkeypatch.setitem(sys.modules,'healpy',AnalyticHP('healpy'))
 # Isolate import-cache changes made by the legacy implementation itself.
 saved={name:sys.modules.get(name) for name in ('t1_engine','t2b2_bridge','t2b2_run')}
 yield root
 for name,mod in saved.items():
  if mod is None:sys.modules.pop(name,None)
  else:sys.modules[name]=mod

def test_synthetic_constructor_normal(asset_bundle):
 k=lk.LegacyKernel(str(asset_bundle));assert k.M21.shape==(21,21)
 assert np.max(np.abs(k.YQW@k.Ymat(k.DIRS)-np.eye(21)))<1e-12

def test_modified_bridge_is_not_accepted_as_frozen(asset_bundle):
 p=asset_bundle/'t2b2_bridge.py';s=p.read_text();assert 'return M, lmf, rb' in s
 p.write_text(s.replace('return M, lmf, rb','M[1] *= -1\n    return M, lmf, rb'))
 with pytest.raises((InputContractError,ValueError,AssertionError)):
  lk.LegacyKernel(str(asset_bundle))

def test_foreign_earlier_sys_path_cannot_replace_requested_bridge(asset_bundle,tmp_path,monkeypatch):
 rogue=tmp_path/'rogue';rogue.mkdir();s=(asset_bundle/'t2b2_bridge.py').read_text();(rogue/'t2b2_bridge.py').write_text(s.replace('return M, lmf, rb','M[1] *= -1\n    return M, lmf, rb'))
 monkeypatch.setattr(sys,'path',[str(rogue)]+[x for x in sys.path if x!=str(asset_bundle)]+[str(asset_bundle)])
 try:k=lk.LegacyKernel(str(asset_bundle))
 except (InputContractError,ValueError,AssertionError):return
 # Canonical real c mode coefficient (l=2,m=1) is positive 1/sqrt(2).
 assert k.M21[1,3].real>0,'a foreign bridge was silently used'

def test_bstack_drift_still_rejected(asset_bundle):
 p=asset_bundle/'results/step1_phaseA/A5_freeze/s1_Bstack_l2_4_N16_common_v1.npz';p.write_bytes(p.read_bytes()+b' ')
 with pytest.raises((InputContractError,ValueError,AssertionError)):lk.LegacyKernel(str(asset_bundle))

@pytest.fixture
def cross_checker(monkeypatch,tmp_path):
 assert sha(OFF.read_bytes())=='6a8c87889ec1d7a5d35336a3cdc30f9537376f2b3878ac9d1ee12cc34319c5df'
 z=np.load(OFF);out={name:np.array(z[name][:20000],copy=True) for name in ('T1','T2','AX','PL')};cid=np.array(z['cid'][:20000],copy=True)
 sp=importlib.util.spec_from_file_location('_audit_cross_test',ROOT/'tests/test_b2_tranche23.py');t=importlib.util.module_from_spec(sp);sp.loader.exec_module(t)
 t.OFFICIAL=str(OFF)
 class CheckpointDouble:
  def __init__(self,unused):self.C_ISO=np.eye(21)
  def psqrt(self,C):return np.eye(21),{}
  def generate(self,*args,**kwargs):return {(0,'float64'):out},cid,{}
 monkeypatch.setattr(lk,'LegacyKernel',CheckpointDouble)
 return t,out

def test_cross_checker_control(cross_checker):
 t,out=cross_checker;t.test_legacy_kernel_cross_environment_agreement_with_a10_official()

@pytest.mark.parametrize('mutation',['raw_axis','masked_nan','masked_large_error','reference_bytes_drift'])
def test_cross_checker_rejects_unverified_or_uncompared_output(cross_checker,mutation,tmp_path):
 t,out=cross_checker
 if mutation=='raw_axis':out['AX']=(out['AX']+1)%3072
 elif mutation=='masked_nan':out['PL'][0]=(out['PL'][0]+1)%3072;out['T1'][0]=np.nan;out['T2'][0]=np.nan
 elif mutation=='masked_large_error':out['PL'][0]=(out['PL'][0]+1)%3072;out['T1'][0]=1e100;out['T2'][0]=1e100
 else:
  f=tmp_path/'drift.npz';f.write_bytes(OFF.read_bytes()+b' modified after freeze');t.OFFICIAL=str(f)
 with pytest.raises((AssertionError,InputContractError,ValueError)):
  t.test_legacy_kernel_cross_environment_agreement_with_a10_official()

@pytest.mark.parametrize('mutation',['negative_chunk','empty_selections','fractional_stream'])
def test_legacy_generator_rejects_before_empty_or_silently_rekeyed_output(mutation):
 k=lk.LegacyKernel.__new__(lk.LegacyKernel);k.calls=[]
 # Only structural validation is at issue. No rotation or scan should run.
 def forbidden(*a,**kw):pytest.fail('invalid request reached numerical generation')
 k.D_batch=forbidden;k.scan=forbidden
 args=dict(N=100,m=100,stream_ids=(lk.GEN_NS['calibration'],0),S_list=[np.eye(21)])
 if mutation=='negative_chunk':args['chunk_clusters']=-1
 elif mutation=='empty_selections':args['selections']=()
 else:args['stream_ids']=(lk.GEN_NS['calibration'],0.75)
 with pytest.raises((InputContractError,ValueError,TypeError)):k.generate(**args)

def test_normal_rng_matches_original_formula():
 a=lk.LegacyKernel.rng_for('gaussian',100,0).standard_normal(20)
 b=np.random.default_rng(np.random.SeedSequence([20260912,11,0,100,0])).standard_normal(20)
 assert np.array_equal(a,b)

@pytest.mark.parametrize('value',[0.75,True,'0'])
def test_rng_does_not_repair_invalid_namespace_component(value):
 with pytest.raises((InputContractError,ValueError,TypeError)):lk.LegacyKernel.rng_for('gaussian',100,value)
