"""Audit of D2 tranche2: TEST-ONLY banks, no CMB/official generation.
Changed cache/spec probes rehash the changed files and outer containers, not
trusted release pins. They isolate internal semantic/association contracts.
"""
from pathlib import Path
import sys, os, copy, json, hashlib
import numpy as np
import pytest
PB=Path(os.environ.get('REVIEW_PB',Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0,str(PB))
from step1_engine import d2_bank as db, d2_rng as dr
from step1_engine.registry import CRNRegistry
from step1_engine.grid_registry import load_registry
from step1_engine.grid_manifest import build_configuration_manifest
from step1_engine.errors import InputContractError
PROBES={}

def digest(b):return hashlib.sha256(b).hexdigest()
def jread(p):return json.loads(Path(p).read_text())
def writej(p,d):Path(p).write_text(json.dumps(d,indent=1))
def rebound(d,key):
 d=copy.deepcopy(d); d[key]=digest(json.dumps({k:v for k,v in d.items() if k!=key},sort_keys=True).encode());return d

def note(name,**d):
 PROBES[name]=d
 target=os.environ.get('REVIEW_PROBES')
 if target: Path(target).write_text(json.dumps(PROBES,indent=2,default=str))

class ToyKernel:
 """Cheap deterministic TEST-ONLY linear observables; counts actual calls."""
 def __init__(self,nan=False):self.d_calls=0;self.scan_calls=0;self.nan=nan
 def D_batch(self,Rs):
  self.d_calls+=1
  # retain some dependence on R in a 21D orthogonal block, unlike identity-only stub
  D=np.broadcast_to(np.eye(21),(len(Rs),21,21)).copy();D[:,:3,:3]=Rs;return D
 def scan(self,X,selection):
  self.scan_calls+=1; xx=X if selection=='float64' else X.astype(np.float32).astype(float)
  a=xx.argmin(1).astype(np.int32)
  t1=xx[np.arange(len(xx)),a].astype(float);t2=np.sum(xx*xx,axis=1).astype(float)
  if self.nan:t1[0]=np.nan
  return dict(T1=t1,T2=t2,AX=a,PL=(a%3).astype(np.int32))

@pytest.fixture
def ctx():
 gr=load_registry(str(PB/'tests/assets/a7_circle_geometry.csv'),str(PB/'tests/assets/a6_observer_design_points.json'))
 man=build_configuration_manifest(gr)
 t,R=dr.load_crn_table(str(PB/'d/d2_crn_table.json'))
 s=db.load_bank_spec(str(PB/'d/d2_bank_spec.json'))
 p=PB/'registered_assets/d1/d1_cov_registry.json'; d1=jread(p);d1['_sha256']=digest(p.read_bytes())
 roots=dict(model_matched=np.eye(21)*1.1,model_native=np.eye(21)*.9,ref_native=dr.native_reference_root(np.array([3.,2.,1.])))
 return gr,man,t,R,s,d1,roots

def generate(ctx,p,*,batch=0,scale=.0002,selection=('float64',),registry=None,spec=None,kernel=None,config=30101,family=None,roots=None):
 gr,man,t,R,s,d1,rr=ctx; inv=db.CallInventory(); k=kernel or ToyKernel()
 m=db.generate_configuration_bank(k,registry or R,t,spec or s,config,roots or rr,batch,str(p),inv,selection,scale=scale,chunk_clusters=2,family=family)
 return m,inv,k

def rewrite_cache(p,mutate):
 """Change one shard/manifest semantically, rebuild all local checksums."""
 m=jread(p/'COMPLETE.json'); sh=m['shards'][0]; side=jread(p/sh['sidecar'])
 with np.load(p/sh['file'],allow_pickle=False) as z: arr={k:z[k].copy() for k in z.files}
 mutate(m,sh,side,arr)
 with open(p/sh['file'],'wb') as f: np.savez(f,**arr)
 side['file_sha256']=digest((p/sh['file']).read_bytes());side['bytes']=(p/sh['file']).stat().st_size
 side['array_sha256']={k:digest(np.ascontiguousarray(v).tobytes()) for k,v in arr.items()}
 writej(p/sh['sidecar'],side);sh['file_sha256']=side['file_sha256'];sh['sidecar_sha256']=digest((p/sh['sidecar']).read_bytes())
 m=rebound(m,'manifest_sha256');writej(p/'COMPLETE.json',m);return m,side,arr

@pytest.mark.parametrize('batch', [0,1])
def test_normal_roundtrip_and_full_batch_slices(ctx,tmp_path,batch):
 p=tmp_path/'normal';m,inv,k=generate(ctx,p,batch=batch,selection=('float64','float32'))
 assert db.verify_bank_dir(str(p),expected_roles=tuple(ctx[-1]))==m
 out,cid,uids=dr.generate_from_latent(ToyKernel(),ctx[-1],ctx[3],'evaluation',1003,batch,m['n_clusters'],('float64','float32'),m=100,chunk_clusters=2)
 n=0
 for sh in m['shards']:
  side=jread(p/sh['sidecar']);a,b=side['rows']
  with np.load(p/sh['file'],allow_pickle=False) as z:
   assert np.array_equal(z['cid'],cid[a:b])
   assert set(z.files)=={'cid'}|{f'{r}__{s}__{key}' for (r,s),d in out.items() for key in d}
   for (r,s),d in out.items():
    for key,x in d.items():assert np.array_equal(z[f'{r}__{s}__{key}'],x[a:b])
  assert side['uids']==[list(uids[a//100].as_tuple()),list(uids[b//100-1].as_tuple())]
  n+=b-a
 assert n==m['n_rows'] and m['formal'] is False
 note(f'normal_b{batch}',shards=len(m['shards']),rows=n,clusters=m['n_clusters'],key=inv.calls[0]['key_gaussian'])

def test_normal_family_reference_same_latent(ctx,tmp_path):
 p=tmp_path/'c';q=tmp_path/'r';a,_,_=generate(ctx,p);b,_,_=generate(ctx,q,config=None,family='E7',roots={'ref_matched':ctx[-1]['model_matched']})
 with np.load(p/a['shards'][0]['file']) as x,np.load(q/b['shards'][0]['file']) as y:
  assert np.array_equal(x['model_matched__float64__T1'],y['ref_matched__float64__T1'])
 assert db.verify_bank_dir(str(q),['ref_matched'])['complete'] is True

def test_spec_rebuild_matches_original(ctx):
 x=db.build_bank_spec(ctx[1],ctx[2],ctx[5],20260912)
 assert x==ctx[4]
 note('spec_identity',spec_payload=x['spec_sha256'],nconfig=len(x['configurations']),f32=x['required_f32_subset'])

def test_formal_subset_extension_must_allow_float64_only(ctx,tmp_path,monkeypatch):
 class Reached(Exception):pass
 calls=[]
 def stop(*a,**kw):calls.append('adapter');raise Reached()
 monkeypatch.setattr(db,'generate_from_latent',stop)
 try:generate(ctx,tmp_path/'extension',batch=1,scale=1.,selection=('float64',))
 except Reached:pass
 except Exception as e:note('f32_correct_extension',reached=len(calls),error=repr(e))
 assert calls==['adapter'],'N0-only sensitivity spec incorrectly refuses formal batch1 float64-only'

@pytest.mark.parametrize('config', [10101,20101,30101,40101])
def test_formal_subset_extension_must_not_demand_fullrange_f32(ctx,tmp_path,monkeypatch,config):
 calls=[]
 class Reached(Exception):pass
 def stop(*a,**kw):calls.append('adapter');raise Reached()
 monkeypatch.setattr(db,'generate_from_latent',stop)
 rejected=False
 try:generate(ctx,tmp_path/'extension',batch=1,scale=1.,selection=('float64','float32'),config=config)
 except InputContractError:rejected=True
 except Reached:pass
 note(f'f32_extension_{config}',refused=rejected,reached=len(calls))
 assert rejected and not calls,'subset-only release sends extension f32 to generator'

def test_registry_seed_must_agree_with_spec_and_table(ctx,tmp_path):
 bad=CRNRegistry(ctx[3].master_seed+1,ctx[3].export_groups()); k=ToyKernel();error=None
 try:
  m,inv,k=generate(ctx,tmp_path/'bad',registry=bad,kernel=k)
  v=db.verify_bank_dir(str(tmp_path/'bad'))
  note('registry_seed',table_seed=ctx[2]['master_seed'],spec_seed=ctx[4]['master_seed'],actual_key=inv.calls[0]['key_gaussian'],complete=m['complete'],reader_accepted=v==m,calls=k.scan_calls)
 except InputContractError as e:error=str(e)
 assert error is not None and k.scan_calls==0,'different seed is used under the unchanged table/spec identity'

def test_current_spec_payload_is_checked_at_generation(ctx,tmp_path):
 s=copy.deepcopy(ctx[4]);s['configurations']['30101']['evaluation_ids']['native']=42;k=ToyKernel();error=None
 try:m,_,_=generate(ctx,tmp_path/'bad',spec=s,kernel=k);note('unrebound_spec',complete=m['complete'],reader_ok=db.verify_bank_dir(str(tmp_path/'bad'))==m)
 except InputContractError as e:error=str(e)
 assert error is not None and k.scan_calls==0

SPEC_MUTATIONS={
 'native_evaluation_id':lambda s:s['configurations']['30101']['evaluation_ids'].__setitem__('native',42),
 'duplicate_configuration_id':lambda s:s['configurations']['30102'].__setitem__('config_id',30101),
 'batch_extension_end':lambda s:s['configurations']['30101']['batches']['1']['rows'].__setitem__(1,5_000_000),
 'missing_shard':lambda s:s['configurations']['30101']['shards'].pop(),
 'wrong_crn_group':lambda s:s['configurations']['30101']['crn'].__setitem__('evaluation_group',1002),
 'missing_required_subset_family':lambda s:s['required_f32_subset'].pop('E8'),
 'pseudo_not_2000':lambda s:s['pseudo_column'].__setitem__('n',1),
 'e1_w2':lambda s:s['configurations']['10101'].__setitem__('w2_primary',copy.deepcopy(s['configurations']['30101']['w2_primary'])),
}
@pytest.mark.parametrize('name',list(SPEC_MUTATIONS))
def test_spec_semantics_after_local_rehash(ctx,tmp_path,name):
 s=copy.deepcopy(ctx[4]);SPEC_MUTATIONS[name](s);s=rebound(s,'spec_sha256');p=tmp_path/'s.json';writej(p,s)
 rejected=False
 try:db.load_bank_spec(str(p),s['spec_sha256'])
 except InputContractError:rejected=True
 note('spec_'+name,rejected=rejected)
 assert rejected,'locally checksum-valid but inconsistent specification accepted'

@pytest.mark.parametrize('scale',[.00014,.00004])
def test_writer_never_completes_with_uncovered_rows(ctx,tmp_path,scale):
 p=tmp_path/'bank'; k=ToyKernel()
 try:m,_,_=generate(ctx,p,batch=1,scale=scale,kernel=k)
 except InputContractError:
  assert not (p/'COMPLETE.json').exists();return
 covered=sum(sh['rows'][1]-sh['rows'][0] for sh in m['shards']);er=None
 try:db.verify_bank_dir(str(p))
 except Exception as e:er=repr(e)
 note('coverage_'+str(scale),scale=scale,declared_rows=m['n_rows'],covered_rows=covered,complete=m['complete'],reader_error=er)
 assert covered==m['n_rows'],'valid scale request returned COMPLETE with rows missing'


def test_nonfinite_generation_not_published_complete(ctx,tmp_path):
 p=tmp_path/'bank';k=ToyKernel(nan=True)
 try:m,_,_=generate(ctx,p,kernel=k)
 except (InputContractError,ValueError):
  assert not (p/'COMPLETE.json').exists();return
 er=None
 try:db.verify_bank_dir(str(p))
 except Exception as e:er=repr(e)
 note('nonfinite_complete',complete=m['complete'],marker=(p/'COMPLETE.json').exists(),reader_error=er)
 assert not (p/'COMPLETE.json').exists(),'invalid T values already published as complete'

CACHE_MUTATIONS={
 'missing_t2':lambda m,sh,s,a:a.pop('model_native__float64__T2'),
 'missing_cid':lambda m,sh,s,a:a.pop('cid'),
 'duplicate_cid':lambda m,sh,s,a:a.__setitem__('cid',np.zeros_like(a['cid'])),
 'fractional_cid':lambda m,sh,s,a:a.__setitem__('cid',a['cid'].astype(float)+.5),
 'two_dimensional_t1':lambda m,sh,s,a:a.__setitem__('model_native__float64__T1',np.column_stack([a['model_native__float64__T1']]*2)),
 'sidecar_config_mismatch':lambda m,sh,s,a:s.__setitem__('config_id',40101),
 'sidecar_root_mismatch':lambda m,sh,s,a:s['root_sha256'].__setitem__('model_native','0'*64),
 'sidecar_uid_mismatch':lambda m,sh,s,a:s['uids'][1].__setitem__(4,999),
 'manifest_cluster_mismatch':lambda m,sh,s,a:m.__setitem__('n_clusters',999),
 'sidecar_shape_role_identity':lambda m,sh,s,a:s.__setitem__('evaluation_ids',{'matched':0,'native':1}),
 'sidecar_formal_promotion':lambda m,sh,s,a:s.__setitem__('formal',True),
 'call_key_mismatch':lambda m,sh,s,a:m['calls'][0]['key_gaussian'].__setitem__(3,1002),
 'sidecar_schema':lambda m,sh,s,a:s.__setitem__('schema','unrelated_record'),
 'cid_only':lambda m,sh,s,a:[a.pop(k) for k in list(a) if k!='cid'],
}
@pytest.mark.parametrize('name',list(CACHE_MUTATIONS))
def test_cache_semantics_after_local_rehash(ctx,tmp_path,name):
 p=tmp_path/'bank';generate(ctx,p);m,s,a=rewrite_cache(p,CACHE_MUTATIONS[name]);rej=False
 try:db.verify_bank_dir(str(p),expected_roles=tuple(ctx[-1]))
 except (InputContractError,ValueError,KeyError):rej=True
 note('cache_'+name,rejected=rej,keys=sorted(a),nrows=m['n_rows'],ncluster=m['n_clusters'])
 assert rej,'checksum-valid internal inconsistency accepted by cache verifier'

@pytest.mark.parametrize('kind',['raw_bytes','sidecar_bytes','no_completion'])
def test_existing_byte_and_partial_rejection(ctx,tmp_path,kind):
 p=tmp_path/'bank';m,_,_=generate(ctx,p)
 if kind=='raw_bytes':
  f=p/m['shards'][0]['file'];f.write_bytes(f.read_bytes()+b'changed')
 elif kind=='sidecar_bytes':
  f=p/m['shards'][0]['sidecar'];f.write_text(f.read_text()+' ')
 else:(p/'COMPLETE.json').unlink()
 with pytest.raises((InputContractError,ValueError)):db.verify_bank_dir(str(p))


def test_existing_output_is_not_changed(ctx,tmp_path):
 p=tmp_path/'bank';generate(ctx,p);before={f.name:digest(f.read_bytes()) for f in p.iterdir()}
 with pytest.raises(InputContractError):generate(ctx,p)
 assert before=={f.name:digest(f.read_bytes()) for f in p.iterdir()}

def test_exception_leaves_no_complete(ctx,tmp_path):
 class BadKernel(ToyKernel):
  def scan(self,*a):raise RuntimeError('TEST-ONLY scan failure')
 p=tmp_path/'bank'
 with pytest.raises(RuntimeError):generate(ctx,p,kernel=BadKernel())
 assert not (p/'COMPLETE.json').exists()
