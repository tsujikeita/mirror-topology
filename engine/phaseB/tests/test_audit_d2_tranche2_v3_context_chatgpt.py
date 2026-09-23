"""Public snapshot isolation and normal cache contracts (TEST-ONLY statistical kernel).
No submitted file/registry/receipt is modified. Mutations affect objects returned by
public functions; no private cache or validator is replaced to create the failure.
The autouse fixture only resets module state BETWEEN tests for repeatability.
"""
from pathlib import Path
import os,sys,copy,json,hashlib
import numpy as np
import pytest
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'tests')); sys.path.insert(0,str(BASE))
import test_audit_d2_tranche2_review_chatgpt as prior   # adapted: the prior review module is the bundled tranche-2 review test
from step1_engine import d2_bank as db,d2_rng as dr
from step1_engine.grid_registry import load_registry
from step1_engine.grid_manifest import build_configuration_manifest
from step1_engine.errors import InputContractError
PB=prior.PB
PROBES={}
def note(name,**v):
 PROBES[name]=v
 path=os.environ.get('CLOSURE_PROBES')
 if path:Path(path).write_text(json.dumps(PROBES,indent=2,default=str))
@pytest.fixture(autouse=True)
def isolation():
 saved=copy.deepcopy(db.SHARED_NULL)
 db._CANON.clear()
 yield
 db._CANON.clear();db.SHARED_NULL.clear();db.SHARED_NULL.update(saved)

def sources():
 g=load_registry(str(PB/'tests/assets/a7_circle_geometry.csv'),str(PB/'tests/assets/a6_observer_design_points.json'))
 m=build_configuration_manifest(g);t,r=dr.load_crn_table(str(PB/'d/d2_crn_table.json'))
 p=PB/'registered_assets/d1/d1_cov_registry.json';d=prior.jread(p);d['_sha256']=prior.digest(p.read_bytes())
 roots={'model_matched':np.eye(21)*1.1,'model_native':np.eye(21)*.9,'ref_native':dr.native_reference_root(np.array([3.,2.,1.]))}
 return g,m,t,r,None,d,roots

def mutate_spec(s,name):
 c=s['configurations']['30101']
 if name=='weight':c['weight']=.123
 elif name=='cache_key':c['cache_key']='0'*64
 elif name=='covariance':c['covariance']=copy.deepcopy(s['configurations']['30102']['covariance'])
 else:raise AssertionError(name)
 # Match the producer's documented digest. Only the public returned object changes.
 s['spec_sha256']=prior.rebound(s,'spec_sha256')['spec_sha256']

@pytest.mark.parametrize('name',['weight','cache_key','covariance'])
def test_returned_context_cannot_redefine_trusted_spec(tmp_path,name):
 x=sources();c=db.canonical_context(x[2]);s=c['spec'];old_hash=s['spec_sha256'];mutate_spec(s,name)
 error=None;k=prior.ToyKernel();p=tmp_path/'bad'
 try:
  out,_,_=prior.generate(x,p,spec=s,kernel=k)
  read=db.verify_bank_dir(str(p)); accepted=True
 except (InputContractError,ValueError,KeyError,TypeError) as e:error=repr(e);accepted=False
 note('returned_context_'+name,rejected=not accepted,error=error,scan_calls=k.scan_calls,complete=(p/'COMPLETE.json').exists(),old_spec_sha=old_hash,new_spec_sha=s['spec_sha256'],disk_spec_unchanged=prior.jread(PB/'d/d2_bank_spec.json')['spec_sha256']==old_hash)
 assert error is not None and k.scan_calls==0,'Editing a public returned snapshot must not redefine the trusted canonical spec'

@pytest.mark.parametrize('name',['weight','cache_key','covariance'])
def test_copy_of_context_spec_is_rejected_before_generation(tmp_path,name):
 x=sources();s=copy.deepcopy(db.canonical_context(x[2])['spec']);mutate_spec(s,name);k=prior.ToyKernel()
 with pytest.raises(InputContractError):prior.generate(x,tmp_path/'bad',spec=s,kernel=k)
 assert k.scan_calls==0

@pytest.mark.parametrize('location',['argument_table','returned_table'])
def test_context_does_not_retain_or_export_caller_table_alias(tmp_path,location):
 x=sources();t=x[2];c=db.canonical_context(t)
 modified=t if location=='argument_table' else c['table']
 modified['groups']['1003']['label']='TEST-ONLY edit in caller-owned metadata'
 error=None
 try:
  # Correct unchanged specification and default committed table must still load.
  s=db.load_bank_spec(str(PB/'d/d2_bank_spec.json'));ok=True
 except Exception as e:error=repr(e);ok=False
 note('table_alias_'+location,normal_spec_still_loads=ok,error=error)
 assert ok,'A caller-owned table edit poisoned subsequent reads of the unmodified committed spec'

@pytest.mark.parametrize('key',['asset_sha256','pools_npz_file_sha256'])
def test_builder_whitening_is_not_a_mutable_module_constant(tmp_path,key):
 x=sources();before=copy.deepcopy(db.SHARED_NULL)
 # Do not call canonical_context first. This is an ordinary public builder call.
 s=db.build_bank_spec(x[1],x[2],x[5],x[2]['master_seed'])
 s['w2']['whitening'][key]='0'*64
 s['spec_sha256']=prior.rebound(s,'spec_sha256')['spec_sha256']
 k=prior.ToyKernel();err=None;p=tmp_path/'bad'
 try:out,_,_=prior.generate(x,p,spec=s,kernel=k);accepted=True
 except (InputContractError,ValueError,TypeError,KeyError) as e:accepted=False;err=repr(e)
 note('builder_whitening_'+key,global_changed=db.SHARED_NULL!=before,rejected=not accepted,scan_calls=k.scan_calls,complete=(p/'COMPLETE.json').exists(),error=err)
 assert db.SHARED_NULL==before and not accepted and k.scan_calls==0,'Builder output aliases the module constant used for canonical verification'

@pytest.mark.parametrize('batch',[0,1])
def test_independent_valid_contexts_make_identical_banks(tmp_path,batch):
 x=sources();a=db.canonical_context(x[2]);b=db.canonical_context()
 assert a['spec']==b['spec']==prior.jread(PB/'d/d2_bank_spec.json')
 for i,c in enumerate([a,b]):
  p=tmp_path/str(i);m,_,_=prior.generate(x,p,spec=c['spec'],batch=batch)
  assert db.verify_bank_dir(str(p))==m
 with np.load(tmp_path/'0'/m['shards'][0]['file']) as z,np.load(tmp_path/'1'/m['shards'][0]['file']) as zz:
  assert z.files==zz.files
  for k in z.files:np.testing.assert_array_equal(z[k],zz[k])
 note('normal_independent_context_'+str(batch),rows=m['n_rows'],spec_sha=m['spec_sha256'])

@pytest.mark.parametrize('batch',[0,1])
def test_cache_directory_relocation_is_normal(tmp_path,batch):
 import shutil
 x=list(sources());x[4]=db.load_bank_spec(str(PB/'d/d2_bank_spec.json'))
 a=tmp_path/'first';m,_,_=prior.generate(x,a,batch=batch)
 dest=tmp_path/'relocated';shutil.copytree(a,dest)
 assert db.verify_bank_dir(str(dest))==m

@pytest.mark.parametrize('stream,value',[('key_rotation',True),('key_gaussian',.0),('key_gaussian','0')])
def test_key_type_refused_after_container_rehash(tmp_path,stream,value):
 x=list(sources());x[4]=db.load_bank_spec(str(PB/'d/d2_bank_spec.json'));p=tmp_path/'bank';prior.generate(x,p)
 prior.rewrite_cache(p,lambda m,sh,s,a:m['calls'][0][stream].__setitem__(5,value))
 with pytest.raises(InputContractError):db.verify_bank_dir(str(p))

@pytest.mark.parametrize('field,value',[('formal',1),('scale',True),('scale',float('inf')),('scale',float('nan'))])
def test_scale_and_formal_types_are_refused(tmp_path,field,value):
 x=list(sources());x[4]=db.load_bank_spec(str(PB/'d/d2_bank_spec.json'));p=tmp_path/'bank';prior.generate(x,p)
 def mut(m,sh,s,a):m[field]=s[field]=value
 prior.rewrite_cache(p,mut)
 with pytest.raises(InputContractError):db.verify_bank_dir(str(p))
