"""D2 tranche2 v2: synthetic storage/semantic tests, not official physical generation.
Local changes are deliberately re-hashed to test INTERNAL content contracts.
External accepted SHA/receipts are never overwritten or treated as re-authorized.
"""
from pathlib import Path
import sys,os,copy,json,hashlib,shutil
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests')); sys.path.insert(0,str(ROOT))
import test_audit_d2_tranche2_review_chatgpt as prior   # adapted: the prior review module is the bundled tranche-2 review test
from step1_engine import d2_bank as db,d2_rng as dr
from step1_engine.errors import InputContractError
ctx=prior.ctx
ToyKernel=prior.ToyKernel; generate=prior.generate; rebound=prior.rebound
writej=prior.writej; jread=prior.jread; digest=prior.digest
PROBES={}
def note(name,**v):
 PROBES[name]=v
 p=os.environ.get('NEW_PROBES')
 if p:Path(p).write_text(json.dumps(PROBES,indent=2,default=str))

@pytest.mark.parametrize('batch',[0,1])
def test_all30_normal_roundtrips(ctx,tmp_path,batch):
 checks=[]
 for cid,c in ctx[4]['configurations'].items():
  p=tmp_path/cid;m,_,_=generate(ctx,p,batch=batch,config=int(cid),selection=tuple(c['selections']['evaluation'][str(batch)]))
  got=db.verify_bank_dir(str(p),expected_roles=tuple(ctx[-1]));assert got==m
  assert m['n_rows']==(200 if batch==0 else 600)
  checks.append({'config_id':int(cid),'rows':m['n_rows'],'selections':m['selections']})
 note('normal30_batch'+str(batch),cases=checks)

@pytest.mark.parametrize('batch',[0,1])
def test_all4_normal_family_refs(ctx,tmp_path,batch):
 for fam in ('E1','E2','E7','E8'):
  p=tmp_path/fam;sel=tuple(ctx[4]['family_reference'][fam]['selections'][str(batch)])
  m,_,_=generate(ctx,p,batch=batch,config=None,family=fam,roots={'ref_matched':np.eye(21)},selection=sel)
  assert db.verify_bank_dir(str(p),['ref_matched'])==m
 note('normal_refs_'+str(batch),families=4)

def test_full_scale_request_matrix_without_large_generation(ctx,tmp_path,monkeypatch):
 reached=[]
 class Reached(Exception):pass
 def stop(*a,**kw):reached.append(1);raise Reached()
 monkeypatch.setattr(db,'generate_from_latent',stop)
 for cid,c in ctx[4]['configurations'].items():
  for batch in (0,1):
   ss=tuple(c['selections']['evaluation'][str(batch)])
   with pytest.raises(Reached):generate(ctx,tmp_path/f'{cid}_{batch}',batch=batch,config=int(cid),selection=ss,scale=1.)
 for fam in ('E1','E2','E7','E8'):
  for batch in (0,1):
   ss=tuple(ctx[4]['family_reference'][fam]['selections'][str(batch)])
   with pytest.raises(Reached):generate(ctx,tmp_path/f'{fam}_{batch}',batch=batch,config=None,family=fam,roots={'ref_matched':np.eye(21)},selection=ss,scale=1.)
 assert len(reached)==68
 note('formal_boundary_matrix',correct_requests_reaching_adapter=68,large_arrays_generated=0)

@pytest.mark.parametrize('when',['first_npz','second_sidecar','complete'])
def test_io_failure_does_not_publish_complete(ctx,tmp_path,monkeypatch,when):
 p=tmp_path/'bank';orig=db._atomic_write; seen=[]
 def fail(path,data):
  seen.append(Path(path).name)
  bad=(when=='first_npz' and len(seen)==1) or (when=='second_sidecar' and str(path).endswith('_s2.npz.sidecar.json')) or (when=='complete' and str(path).endswith('COMPLETE.json'))
  if bad:raise OSError('TEST-ONLY injected write failure')
  return orig(path,data)
 monkeypatch.setattr(db,'_atomic_write',fail)
 with pytest.raises(OSError):generate(ctx,p,batch=1)
 assert not (p/'COMPLETE.json').exists()
 with pytest.raises(InputContractError):db.verify_bank_dir(str(p))
 monkeypatch.setattr(db,'_atomic_write',orig)
 m,_,_=generate(ctx,tmp_path/'new_attempt',batch=1);assert db.verify_bank_dir(str(tmp_path/'new_attempt'))==m
 note('io_'+when,complete_exists=False,new_attempt_pass=True)

# Changes after the local checksums have been rebound.
def cache_change(name,m,sh,s,a):
 if name=='empty_selection_cid_only':
  m['selections']=[];s['selections']=[];m['calls'][0]['selections']=[]
  for k in list(a):
   if k!='cid':a.pop(k)
 elif name=='unknown_selection':
  m['selections']=['float16'];s['selections']=['float16'];m['calls'][0]['selections']=['float16']
  for k in list(a):
   if k!='cid':a[k.replace('__float64__','__float16__')]=a.pop(k)
 elif name=='duplicate_selection':
  m['selections']=['float64','float64'];s['selections']=m['selections'][:];m['calls'][0]['selections']=m['selections'][:]
 elif name=='promote_selftest_to_full_scale':
  m['scale']=s['scale']=1.;m['formal']=s['formal']=True
 elif name=='scale_changed_to_half':m['scale']=s['scale']=.5
 elif name=='negative_scale':m['scale']=s['scale']=-.1
 elif name=='swapped_rotation_stream':m['calls'][0]['key_rotation'][5]=0
 elif name=='swapped_gaussian_stream':m['calls'][0]['key_gaussian'][5]=1
 elif name=='unknown_stream':m['calls'][0]['key_gaussian'][5]=999
 elif name=='negative_call_chunk':m['calls'][0]['chunk_clusters']=-1
 elif name=='foreign_family':m['family']=s['family']='E2'
 elif name=='sidecar_covariance_cross_config':s['covariance']['cov_array_sha256']='0'*64
 elif name=='sidecar_dtype_declaration':s['dtype']['T1']='float32'
 elif name=='sidecar_kind':s['kind']='family_reference'
 elif name=='shorter_content_same_scale':
  for k in a:a[k]=a[k][:100]
  m['n_rows']=100;m['n_clusters']=1;m['calls'][0]['clusters']=[0,1]
  sh['rows']=[0,100];s['rows']=[0,100];s['clusters']=s['rotation_index']=[0,1]
  s['global_rows']=[0,100];s['global_clusters']=[0,1];s['uids'][1][4]=0
 else:raise AssertionError(name)
CACHE_NAMES=['empty_selection_cid_only','unknown_selection','duplicate_selection','promote_selftest_to_full_scale','scale_changed_to_half','negative_scale','swapped_rotation_stream','swapped_gaussian_stream','unknown_stream','negative_call_chunk','foreign_family','sidecar_covariance_cross_config','sidecar_dtype_declaration','sidecar_kind','shorter_content_same_scale']
@pytest.mark.parametrize('name',CACHE_NAMES)
def test_cache_internal_contract_after_rehash(ctx,tmp_path,name):
 p=tmp_path/'bank'
 # The promoted example already contains both required selection paths.
 sel=('float64','float32') if name=='promote_selftest_to_full_scale' else ('float64',)
 original,_,_=generate(ctx,p,selection=sel)
 m,s,a=prior.rewrite_cache(p,lambda mm,sh,ss,aa:cache_change(name,mm,sh,ss,aa))
 err=None
 try:v=db.verify_bank_dir(str(p),expected_roles=tuple(ctx[-1]))
 except (InputContractError,ValueError,KeyError,TypeError) as e:err=repr(e);v=None
 note('cache_'+name,rejected=err is not None,error=err,keys=sorted(a),rows=m['n_rows'],clusters=m['n_clusters'],scale=m['scale'],formal=m['formal'],call=m['calls'][0],spec_sha=m['spec_sha256'])
 assert err is not None, 'cache checksum valid but internal content contradicts declared generation/metadata'

def change_spec(name,s):
 c=s['configurations']['30101']
 if name=='wrong_prior':c['weight']=.123
 elif name=='wrong_cache_key':c['cache_key']='0'*64
 elif name=='cross_configuration_covariance':c['covariance']=copy.deepcopy(s['configurations']['30102']['covariance'])
 elif name=='missing_source_binding':s.pop('registry_sha256');s.pop('manifest_sha256');s.pop('d1_registry_sha256')
 elif name=='fitting_role_missing':c['fitting']['roles']=['model_matched']
 elif name=='plan_fitting_n_mismatch':s['plan_schema']['fitting']['N']=1
 elif name=='w2_summary_n_mismatch':s['w2']['N']=1
 elif name=='e1_unknown_config':
  c=s['configurations'].pop('10101');c['config_id']=10199;c['evaluation_ids']={'matched':10199,'native':60199};s['configurations']['10199']=c
  s['required_f32_subset']['E1'].update(config_id=10199,matched=10199,native=60199)
 else:raise AssertionError(name)
SPEC_NAMES=['wrong_prior','wrong_cache_key','cross_configuration_covariance','missing_source_binding','fitting_role_missing','plan_fitting_n_mismatch','w2_summary_n_mismatch','e1_unknown_config']
@pytest.mark.parametrize('name',SPEC_NAMES)
def test_spec_content_and_generation_after_rehash(ctx,tmp_path,name):
 s=copy.deepcopy(ctx[4]);change_spec(name,s);s=rebound(s,'spec_sha256');p=tmp_path/'spec.json';writej(p,s)
 load_error=gen_error=None;k=ToyKernel()
 try:db.load_bank_spec(str(p),s['spec_sha256'],ctx[2])
 except (InputContractError,ValueError,KeyError,TypeError) as e:load_error=repr(e)
 try:
  m,inv,_=generate(ctx,tmp_path/'bank',spec=s,kernel=k,config=10199 if name=='e1_unknown_config' else 30101)
  complete=(tmp_path/'bank/COMPLETE.json').exists();v=db.verify_bank_dir(str(tmp_path/'bank'))
 except (InputContractError,ValueError,KeyError,TypeError) as e:gen_error=repr(e);complete=False
 note('spec_'+name,loader_refused=bool(load_error),loader_error=load_error,generator_refused=bool(gen_error),generator_error=gen_error,scan_calls=k.scan_calls,complete=complete,manifest_sha=s.get('manifest_sha256'),d1_registry_sha=s.get('d1_registry_sha256'))
 assert load_error and gen_error and k.scan_calls==0,'self-consistent checksum is not a source-bound/consistent first-wave specification'


def test_table_metadata_must_still_be_rejected(ctx,tmp_path):
 t=copy.deepcopy(ctx[2]);t['m']=50;t['table_sha256']=dr._table_sha(t)
 s=copy.deepcopy(ctx[4]);s['crn_table_sha256']=t['table_sha256'];s=rebound(s,'spec_sha256')
 with pytest.raises(InputContractError):db.bind_generation_inputs(ctx[3],t,s)
 note('table_metadata_old_guard',rejected=True)
