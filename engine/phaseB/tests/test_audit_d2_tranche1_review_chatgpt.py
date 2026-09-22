"""Independent D2 tranche-1 contract tests.

Synthetic numerical tests use the submitted LegacyKernel.D_batch / scan /
generate and frozen bridge bytes, but synthetic B-stacks and analytic vec2ang.
They are NOT official A5/Colab/frozen-loader integration tests.
Malformed tables are restamped ONLY in isolated test copies: expected original
payload SHA still rejects them; semantic tests deliberately reach inside that guard.
"""
import os, sys, json, hashlib, copy, types, warnings
from pathlib import Path
import numpy as np
import pytest
P=Path(os.environ.get('REVIEW_PB', Path(__file__).resolve().parents[1])).resolve()
sys.path[:0]=[str(P),str(P/'tests')]
from step1_engine import d2_rng as d2
from step1_engine.registry import CRNRegistry, PURPOSE
from step1_engine.errors import InputContractError
from step1_engine.grid_registry import load_registry
from step1_engine.grid_manifest import build_configuration_manifest
from step1_engine import legacy_kernel as lk
TABLE=P/'d/d2_crn_table.json'
PROBES={}
sha=lambda b:hashlib.sha256(b).hexdigest()

@pytest.fixture(scope='session',autouse=True)
def evidence():
 yield
 import tempfile; path=Path(os.environ.get('REVIEW_EVIDENCE', tempfile.gettempdir()))/'d2_review_probes.json'   # adapted: evidence dir not shipped
 path.write_text(json.dumps(PROBES,indent=2,ensure_ascii=False))

@pytest.fixture
def tr():return d2.load_crn_table(TABLE)

class SpyKernel:
 def __init__(self):self.d_calls=0;self.scan_calls=0
 def D_batch(self,Rs):
  self.d_calls+=1
  return np.broadcast_to(np.eye(21),(len(Rs),21,21)).copy()
 def scan(self,X,selection):
  self.scan_calls+=1;n=len(X)
  return dict(T1=np.sum(X*X,axis=1),T2=np.sum(X,axis=1),AX=np.zeros(n,np.int32),PL=np.zeros(n,np.int32))

def attempt(reg,kwargs):
 k=SpyKernel(); base=dict(kernel=k,roots={'ref_matched':np.eye(21)},registry=reg,purpose='evaluation',group=1003,batch_id=0,K=6,m=5,chunk_clusters=4)
 e=None;out=None;ws=[]
 try:
  with warnings.catch_warnings(record=True) as caught:
   warnings.simplefilter('always');out=d2.generate_from_latent(**(base|kwargs))
  ws=[str(w.message) for w in caught]
 except Exception as ex:e=ex
 rec=dict(rejected=e is not None,error=repr(e) if e else None,D_calls=k.d_calls,scan_calls=k.scan_calls,warnings=ws)
 if out is not None:
  o,c,u=out;rec.update(n_rows=len(c),uid_count=len(u),output_keys=[list(x) for x in o],shapes={str(x):{f:list(a.shape) for f,a in q.items()} for x,q in o.items()})
 return rec,e

@pytest.mark.parametrize('name,kwargs',[
 ('negative_chunk',{'chunk_clusters':-1}),('empty_selections',{'selections':()}),
 ('zero_K',{'K':0}),('zero_m',{'m':0}),
 ('complex_root',{'roots':{'ref_matched':np.eye(21)*(1+2j)}}),
 ('float_group',{'group':1003.0}),('float_batch',{'batch_id':0.0}),
 ('bool_batch',{'batch_id':False}),('fractional_batch',{'batch_id':0.9}),
 ('bool_K',{'K':True}),('bool_m',{'m':True}),
 ('uid_capacity',{'K':10001,'m':1,'chunk_clusters':2000}),
])
def test_adapter_rejects_bad_request_before_generation(tr,name,kwargs):
 _,reg=tr;rec,e=attempt(reg,kwargs);PROBES['request_'+name]=rec
 assert e is not None,'invalid request returned data / UID tuple without rejection'
 assert rec['D_calls']==rec['scan_calls']==0,'invalid request reached numerical generation'

@pytest.mark.parametrize('value',[30101.9,30101.0,'30101',True,np.bool_(True)])
def test_w2_id_lookup_rejects_noninteger(tr,value):
 table,_=tr
 with pytest.raises((InputContractError,ValueError,TypeError)):
  x=d2.group_for(table,'w2_independent','E7','L1.00',value)
  PROBES['lookup_'+repr(value)]=dict(accepted_group=x)

@pytest.mark.parametrize('name',[
 'duplicate_scope_distinct_labels','wave_disagreement','fractional_seed',
 'fractional_config','E1_W2','group_alias','m_disagreement',
 'batch_disagreement','label_disagreement'])
def test_table_semantics_after_valid_outer_digest(tr,tmp_path,name):
 t,_=tr;b=copy.deepcopy(t)
 if name=='duplicate_scope_distinct_labels':b['groups']['1003']['scope']=copy.deepcopy(b['groups']['1004']['scope'])
 elif name=='wave_disagreement':b['groups']['1003']['wave_id']=2
 elif name=='fractional_seed':b['master_seed']=20260912.75
 elif name=='fractional_config':
  b['groups']['60101']['scope']['config_id']=30101.9
  b['groups']['60101']['label']=json.dumps(b['groups']['60101']['scope'],sort_keys=True)
 elif name=='E1_W2':
  b['groups']['60101']['scope'].update(family='E1',config_id=10101)
  b['groups']['60101']['label']=json.dumps(b['groups']['60101']['scope'],sort_keys=True)
 elif name=='group_alias':
  b['groups']['01003']=copy.deepcopy(b['groups']['1003']);b['groups']['01003']['label']='alias'
 elif name=='m_disagreement':b['m']=50
 elif name=='batch_disagreement':b['batches']['1']=[1000000,5000000]
 elif name=='label_disagreement':b['groups']['1003']['label']='wrong but distinct label'
 b['table_sha256']=d2._table_sha(b)
 path=tmp_path/'table.json';path.write_text(json.dumps(b))
 rejected=False;details={}
 try:
  loaded,rr=d2.load_crn_table(path,b['table_sha256'])
  details.update(table_groups=len(loaded['groups']),registry_groups=len(rr.export_groups()),table_seed=loaded['master_seed'],registry_seed=rr.master_seed)
 except (InputContractError,ValueError,TypeError,KeyError):rejected=True
 PROBES['table_'+name]=dict(rejected=rejected,**details)
 assert rejected,'outer digest valid but inconsistent table was restored as valid'

@pytest.mark.parametrize('value',[30101.9,'30101'])
def test_builder_rejects_truncating_config_id(value):
 with pytest.raises((InputContractError,TypeError,ValueError)):
  t=d2.build_crn_table(20260912,{'E7':{'L1.00':[value]}})
  PROBES['builder_'+repr(value)]=dict(accepted_scope=t['groups']['60101']['scope'])

# Positive and correctly rejected controls.
def test_original_table_against_registered_30_grid(tr):
 t,R=tr
 reg=load_registry(str(P/'tests/assets/a7_circle_geometry.csv'),str(P/'tests/assets/a6_observer_design_points.json'))
 man=build_configuration_manifest(reg)
 expected=[s for s in man.configurations if s.family!='E1']
 groups=R.export_groups()
 assert len(t['groups'])==len(groups)==44
 assert len({int(g) for g in t['groups']})==44
 for s in expected:
  g=d2.group_for(t,'w2_independent',s.family,s.size_id,s.config_id)
  assert g==30000+s.config_id
  assert t['groups'][str(g)]['scope']==dict(wave_id=1,family=s.family,size_id=s.size_id,config_id=s.config_id)
 for family,g in [('E1',1001),('E2',1002),('E7',1003),('E8',1004)]:
  assert d2.group_for(t,'evaluation',family)==g
  assert d2.group_for(t,'fitting',family)==g+1000
 assert sum(g['purpose']=='w2_independent' for g in groups.values())==27
 assert t['batches']=={'0':[0,1000000],'1':[1000000,4000000]}
 for k in ['m','N0','N_max','chunk_clusters']:assert t[k]=={'m':100,'N0':1000000,'N_max':4000000,'chunk_clusters':2000}[k]
 PROBES['canonical_table']=dict(groups=44,W2_groups=27,file_sha256=sha(TABLE.read_bytes()),payload_sha256=t['table_sha256'],grid_sha=man.manifest_sha256)

def test_original_expected_sha_rejects_changed_table(tr,tmp_path):
 t,_=tr;b=copy.deepcopy(t);b['m']=50;b['table_sha256']=d2._table_sha(b)
 p=tmp_path/'x.json';p.write_text(json.dumps(b))
 with pytest.raises(InputContractError):d2.load_crn_table(p,t['table_sha256'])

def test_stale_table_payload_rejected(tr,tmp_path):
 t,_=tr;b=copy.deepcopy(t);b['m']=50;p=tmp_path/'x.json';p.write_text(json.dumps(b))
 with pytest.raises(InputContractError):d2.load_crn_table(p)

@pytest.mark.parametrize('name,kwargs',[
 ('nanroot',{'roots':{'r':np.full((21,21),np.nan)}}),('shape',{'roots':{'r':np.eye(20)}}),
 ('unknownselection',{'selections':('float16',)}),('duplicateselection',{'selections':('float64','float64')}),
 ('foreigngroup',{'group':99999}),('purposegroup',{'purpose':'fitting'}),
])
def test_existing_rejections(tr,name,kwargs):
 _,R=tr;rec,e=attempt(R,kwargs);PROBES['existing_rejection_'+name]=rec
 assert e is not None and rec['D_calls']==rec['scan_calls']==0

def full_latent(R,purpose='evaluation',group=1003,batch=0,K=9,m=5,chunk=4):
 b=list(d2.iter_latent(R,purpose,group,batch,K,m=m,chunk_clusters=chunk))
 return np.concatenate([v[2] for v in b]),np.concatenate([v[3] for v in b])

def test_fresh_replay_matches_formal_key_reference(tr):
 from scipy.spatial.transform import Rotation
 _,R=tr;rs,z=full_latent(R)
 kr=(20260912,1,200,1003,0,1);kz=(20260912,1,200,1003,0,0)
 assert R.rng_key('evaluation',1,1003,0,'rotation')==kr
 assert R.rng_key('evaluation',1,1003,0,'gaussian')==kz
 rr=np.random.default_rng(np.random.SeedSequence(kr));rz=np.random.default_rng(np.random.SeedSequence(kz))
 assert np.array_equal(rs,Rotation.random(num=9,rng=rr).as_matrix())
 assert np.array_equal(z,rz.standard_normal((9,5,21)))
 # A live registry stream advances; independent replay still returns the start.
 R.stream('evaluation',1,1003,0,'gaussian').standard_normal(37)
 rs2,z2=full_latent(R);assert np.array_equal(rs,rs2) and np.array_equal(z,z2)
 PROBES['latent_reference']=dict(rotation_key=kr,gaussian_key=kz,R_sha=sha(rs.tobytes()),z_sha=sha(z.tobytes()))

@pytest.mark.parametrize('chunk',[1,2,3,9,2000])
def test_latent_chunk_and_prefix_invariance(tr,chunk):
 _,R=tr;a,z=full_latent(R,chunk=4);b,w=full_latent(R,chunk=chunk)
 assert np.array_equal(a,b) and np.array_equal(z,w)
 c,v=full_latent(R,K=4,chunk=chunk)
 assert np.array_equal(c,a[:4]) and np.array_equal(v,z[:4])

@pytest.mark.parametrize('purpose,group,batch',[
 ('fitting',2003,0),('evaluation',1003,1),('evaluation',1004,0),
 ('w2_independent',60101,0),('w2_independent',60102,0),('w2_independent',60201,0),
])
def test_distinct_stream_scope_differs(tr,purpose,group,batch):
 _,R=tr;a,z=full_latent(R);b,w=full_latent(R,purpose,group,batch)
 assert not np.array_equal(a,b) and not np.array_equal(z,w)
 # This checks deterministic separation, not statistical independence.

@pytest.fixture
def synthetic_kernel(tmp_path,monkeypatch):
 # Constructor, D_batch, scan and generate are actual submitted code. Only external
 # observational assets and healpy angular conversion are a TEST-ONLY replacement.
 root=tmp_path/'synthetic_mt';(root/'results/step1_phaseA/A5_freeze').mkdir(parents=True);(root/'docs').mkdir()
 bridge=P/'tests/reference_assets/t2b2_bridge.py';body=bridge.read_bytes()
 assert sha(body)==lk.BRIDGE_SHA;(root/'t2b2_bridge.py').write_bytes(body)
 rng=np.random.default_rng(471)
 # Full 3072 axes; varied positive definite symmetric matrices, not all identical.
 a=rng.standard_normal((3072,21,3));Bp=np.einsum('aik,ajk->aij',a,a)+np.eye(21)
 b=rng.standard_normal((3072,21,2));Bm=np.einsum('aik,ajk->aij',b,b)+2*np.eye(21)
 bp=root/'results/step1_phaseA/A5_freeze/s1_Bstack_l2_4_N16_common_v1.npz';np.savez(bp,Bp_stack=Bp,Bm_stack=Bm)
 cv=np.repeat([1064.7171662281169,504.60627721102173,286.7042588407274],[5,7,9]);np.savez(root/'docs/step0_frozen_Bpm_v1.npz',CVEC=cv)
 class AnalyticHP(types.ModuleType):
  def vec2ang(self,dirs):
   x=np.asarray(dirs).reshape(-1,3);r=np.sqrt(np.sum(x*x,axis=1));return np.arccos(np.clip(x[:,2]/r,-1,1)),np.mod(np.arctan2(x[:,1],x[:,0]),2*np.pi)
  def pix2vec(self,ns,pix):
   ph=np.asarray(pix)*2*np.pi/3072;return np.cos(ph),np.sin(ph),np.zeros_like(ph)
  def vec2pix(self,ns,x,y,z):return np.arange(3072,dtype=np.int64)[::-1]
 monkeypatch.setitem(sys.modules,'healpy',AnalyticHP('healpy'))
 monkeypatch.setattr(lk,'ASSET_SHA',dict(lk.ASSET_SHA,bstack=sha(bp.read_bytes()),bstack_array=sha(Bp.tobytes()+Bm.tobytes()),cvec_array=sha(cv.tobytes()),antipode=sha(np.arange(3072,dtype=np.int32)[::-1].tobytes())))
 return lk.LegacyKernel(str(root))

@pytest.mark.parametrize('batch',[0,1])
def test_unchanged_numerical_path_and_multi_root_order(tr,synthetic_kernel,monkeypatch,batch):
 _,R=tr;k=synthetic_kernel;K=7;m=5
 S=k.psqrt(k.C_ISO)[0];rng=np.random.default_rng(12);a=rng.standard_normal((21,21));C=a@a.T+30*np.eye(21);SN=k.psqrt(C)[0];SM,c=k.matched(C)
 roots={'model_matched':k.psqrt(SM)[0],'ref_matched':S,'model_native':SN,'ref_native':d2.native_reference_root(c)}
 keys={s:R.rng_key('evaluation',1,1003,batch,s) for s in ['rotation','gaussian']}
 monkeypatch.setattr(k,'rng_for',lambda stream,*ignored:np.random.default_rng(np.random.SeedSequence(keys[stream])))
 old,cid,_=k.generate(K*m,m,(lk.GEN_NS['calibration'],0),list(roots.values()),('float64','float32'),chunk_clusters=4)
 new,ncid,u=d2.generate_from_latent(k,roots,R,'evaluation',1003,batch,K,('float64','float32'),m=m,chunk_clusters=4)
 for i,r in enumerate(roots):
  for s in ['float64','float32']:
   for f in ['T1','T2','AX','PL']:assert np.array_equal(old[(i,s)][f],new[(r,s)][f])
 assert np.array_equal(cid,ncid) and len(u)==K
 perm,pcid,pu=d2.generate_from_latent(k,dict(reversed(list(roots.items()))),R,'evaluation',1003,batch,K,('float32','float64'),m=m,chunk_clusters=4)
 for key in new:
  for f in new[key]:assert np.array_equal(new[key][f],perm[key][f])
 for r,root in roots.items():
  solo,_,_=d2.generate_from_latent(k,{r:root},R,'evaluation',1003,batch,K,('float64',),m=m,chunk_clusters=4)
  for f in solo[(r,'float64')]:assert np.array_equal(solo[(r,'float64')][f],new[(r,'float64')][f])
 assert new[('ref_matched','float32')]['T1'].dtype==np.float64
 assert new[('ref_matched','float32')]['AX'].dtype==np.int32
 PROBES['synthetic_math_'+str(batch)]=dict(equal_fields=32,rows=K*m,roles=4,paths=2,root_order_invariant=True,solo_equals_shared=True,source='submitted D_batch/scan/generate; synthetic Bp/Bm and angular helper')

def test_native_reference_from_all_saved_D1_entries():
 registry=json.loads((P/'registered_assets/d1/d1_cov_registry.json').read_text())
 # Schema inspected, not guessed from a title.
 entries=registry['configurations'].values()
 values=[]
 for row in entries:
  c=np.asarray(row['intake']['c_ct'],float)
  S=d2.native_reference_root(c)
  assert np.allclose(S@S.T,np.diag(np.repeat(c,[5,7,9])),rtol=1e-15,atol=1e-12)
  values.append(tuple(c))
 assert len(values)==30 and len(set(values))==30
 PROBES['native_references']=dict(n=30,distinct=30)

@pytest.mark.parametrize('seed',range(5))
def test_generated_two_batches_supply_and_bootstrap(tr,seed):
 from step1_engine.orchestrator import ConfigBank
 from step1_engine.bootstrap_plan import BootstrapPlan,HitTable,resample_hits,literal_resample_hits
 _,R=tr;k=SpyKernel();m=5
 results=[]
 for b,K in [(0,4),(1,12)]:
  o,c,u=d2.generate_from_latent(k,{'model':np.eye(21),'ref':2*np.eye(21)},R,'evaluation',1003,b,K,m=m,chunk_clusters=4)
  results.append((o,u))
 model=np.concatenate([o[('model','float64')]['T1'] for o,u in results]);ref=np.concatenate([o[('ref','float64')]['T1'] for o,u in results]);uids=results[0][1]+results[1][1]
 bnk=ConfigBank(30101,'E7','matched',1/9,model,model,ref,ref,uids,m,{0:(0,20),1:(20,80)})
 assert bnk.N0==20 and len(bnk.at_stage('N0').T1_model)==20
 strata={b:results[b][1] for b in [0,1]};plan=BootstrapPlan.build('audit-d2',seed,strata,20,20260912)
 hits=((model<20)).reshape(16,m).sum(axis=1)
 tables={0:HitTable(strata[0],hits[:4],20,m),1:HitTable(strata[1],hits[4:],60,m)}
 for subset in [tables,{0:tables[0]}]:
  prob,sums=resample_hits(plan,subset);literal,lsums=literal_resample_hits(plan,subset)
  assert np.array_equal(prob,literal)
  assert all(np.array_equal(sums[b],lsums[b]) for b in subset)
 assert len(set(uids))==16

@pytest.mark.parametrize('c',[[-1,2,3],[1,np.nan,3],[1,np.inf,3],[1,0,3],[1,2]])
def test_invalid_native_root(c):
 with pytest.raises((InputContractError,ValueError)):d2.native_reference_root(np.asarray(c))
