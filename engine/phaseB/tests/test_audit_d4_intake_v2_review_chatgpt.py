"""D4 t1 v2 contract review: real D1 arrays, synthetic external source files.
The real receipt/registry/file SHA anchors are never weakened. For runnable
normal paths only, frozen_loaders is explicitly bound to tiny TEST-ONLY
source files in a temporary root; LegacyKernel.__init__ supplies only frozen
PR3 c_l values. Real matched/psqrt methods and source-identity guard are used.
This is not a physical CMB generation or an authenticated real t1 run.
"""
import os,sys,json,hashlib,copy,shutil,types,inspect
from pathlib import Path
import numpy as np
import pytest
BASE=Path(__file__).resolve().parents[1]
PB=Path(os.environ.get('REVIEW_PB',Path(__file__).resolve().parents[1]))
sys.path[:0]=[str(PB),str(PB/'tests')]
from step1_engine import production as pr, serialization as ser
from step1_engine.grid_registry import load_registry,registry_from_dict
from step1_engine.grid_manifest import build_configuration_manifest
from step1_engine.legacy_kernel import LegacyKernel,ASSET_SHA,BASIS_SHA
from step1_engine.errors import InputContractError
D1=PB/'registered_assets/d1'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
asha=lambda a:hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
def save(p,x):Path(p).write_text(json.dumps(x,indent=1))
CL=np.array([1064.7171662281169,504.60627721102173,286.7042588407274])
PROBES={}
# Test source mirrors the documented projection/basis algebra only, not the
# complete frozen loader or its full scientific validation.
BRIDGE='''# TEST-ONLY explicit algebraic real-basis transform, not frozen t2b2_bridge
import numpy as np, hashlib
LM=[(l,m) for l in (2,3,4) for m in range(-l,l+1)]
IDX={v:i for i,v in enumerate(LM)}
RB=[(l,m,s) for l in (2,3,4) for m in range(l+1) for s in (('c',) if m==0 else ('c','s'))]
M=np.zeros((21,21),np.complex128)
for i,(l,m,s) in enumerate(RB):
 if not m:M[i,IDX[l,0]]=1
 elif s=='c':M[i,IDX[l,m]]=1/np.sqrt(2);M[i,IDX[l,-m]]=(-1)**m/np.sqrt(2)
 else:M[i,IDX[l,m]]=1j/np.sqrt(2);M[i,IDX[l,-m]]=-1j*(-1)**m/np.sqrt(2)
PERM=np.array([IDX[l,-m] for l,m in LM]);SIGN=np.array([(-1.)**m for l,m in LM]);SS=SIGN[:,None]*SIGN[None,:]
def convert(a):
 h=(a+a.conj().T)/2;pjt=(h+SS*h[np.ix_(PERM,PERM)].conj())/2
 return pjt,(M@pjt@M.conj().T).real
'''
LOADER='''# TEST-ONLY stand-in for the frozen loader; real Python dependency import
import numpy as np,hashlib
import t2b2_bridge as br
CALLS=[]
def load_cov_full(p,lmax=4):
 CALLS.append(str(p));a=np.load(p,allow_pickle=False);pjt,cr=br.convert(a)
 return pjt,cr,dict(cov_array_sha256=hashlib.sha256(a.tobytes()).hexdigest(),TEST_ONLY_loader=True)
'''

@pytest.fixture(scope='session',autouse=True)
def record():
 yield
 import tempfile; f=Path(os.environ.get('INTAKE_PROBES',os.path.join(tempfile.gettempdir(),'intake_v2_probes.json')));f.parent.mkdir(exist_ok=True,parents=True);save(f,PROBES)   # adapted: evidence dir not shipped
@pytest.fixture
def reg():return load_registry(str(PB/'tests/assets/a7_circle_geometry.csv'),str(PB/'tests/assets/a6_observer_design_points.json'))
@pytest.fixture
def env(tmp_path,monkeypatch):
 root=tmp_path/'test_mt';root.mkdir();(root/'t1_engine.py').write_text(LOADER);(root/'t2b2_bridge.py').write_text(BRIDGE)
 rc=copy.deepcopy(pr.D1_REGISTERED_RECEIPT);rc['frozen_loaders']={n:sha(root/(n+'.py')) for n in ('t1_engine','t2b2_bridge')};monkeypatch.setattr(pr,'D1_REGISTERED_RECEIPT',rc)
 for n in ('t1_engine','t2b2_bridge'):monkeypatch.delitem(sys.modules,n,raising=False)
 monkeypatch.setattr(sys,'path',sys.path.copy())
 def ini(k,mt):k.c_pr3=CL.copy()
 monkeypatch.setattr(LegacyKernel,'__init__',ini)
 yield root
 for n in ('t1_engine','t2b2_bridge'):sys.modules.pop(n,None)
@pytest.fixture
def copied(tmp_path):p=tmp_path/'d1';shutil.copytree(D1,p);return p

def call(reg,env,d=D1,cid=30101,receipt='D1_aa089fa492bc'):
 return pr.intake_registered_covariance(cid,reg,str(d),str(env),receipt)
def reject(name,fun):
 try:r=fun()
 except InputContractError as e:PROBES[name]={'rejected':True,'exception':str(e)};return
 PROBES[name]={'rejected':False,'config_id':r.get('config_id'),'trace':float(np.trace(r['C_real'])) if 'C_real' in r else None,'loader_claim':r.get('loader')}
 pytest.fail(name+': inconsistent input accepted')

def test_normal_all30_real_arrays_math(reg,env):
 stored=load(D1/'d1_cov_registry.json');m=build_configuration_manifest(reg);rows=[]
 for s in m.configurations:
  r=call(reg,env,cid=s.config_id);v=stored['configurations'][str(s.config_id)]['intake']
  assert r['spec'].as_dict()==s.as_dict()
  assert asha(r['C_real'])==v['loader_meta']['real_cov_projected_sha256']
  assert np.allclose(r['c_ct'],v['c_ct'],rtol=1e-13,atol=1e-13)
  assert r['trusted_anchors']['registry_sha256']==sha(D1/'d1_cov_registry.json')
  assert r['loader']['t2b2_bridge_path']==str(env/'t2b2_bridge.py')
  assert r['loader']['t1_engine_sha256']==sha(env/'t1_engine.py')
  for k in ('matched','native'):
   z=r['roots_info'][k];assert z['clip']==0 and z['lambda_min']>0 and z['sym']<1e-12 and z['recon']<1e-10
  rows.append({'config_id':s.config_id,'C_real_sha':asha(r['C_real']),'roots':r['roots_info']})
 assert asha(sys.modules['t2b2_bridge'].M)==BASIS_SHA['M21'];assert asha(np.repeat(CL,[5,7,9]))==ASSET_SHA['cvec_array']
 PROBES['normal30']={'rows':rows,'count':len(rows),'source_scope':'verified synthetic source files and real D1 arrays; not frozen t1 full execution'}

@pytest.mark.parametrize('cid',[True,np.bool_(True),30101.9,30101.0,'30101',-1,None,99999])
def test_bad_id_rejected(cid,reg,env):reject('id_'+repr(cid),lambda:call(reg,env,cid=cid))
def test_numpy_integer_accepted(reg,env):assert call(reg,env,cid=np.int64(30101))['config_id']==30101

@pytest.mark.parametrize('which',['receipt_id','receipt_commit','receipt_run','registry_only','npy_only','sidecar_only','receipt_missing','registry_missing','cov_missing','sidecar_missing'])
def test_asset_mismatch_rejected(which,reg,env,copied):
 rc=load(copied/'d1_receipt.json');g=load(copied/'d1_cov_registry.json');c=g['configurations']['30101'];p=copied/c['cov_file'];mf=Path(str(p)+'.manifest.json');rid='D1_aa089fa492bc'
 if which=='receipt_id':rid='other'
 elif which=='receipt_commit':rc['source_commit']='0'*40;save(copied/'d1_receipt.json',rc)
 elif which=='receipt_run':rc['run_id']='wrong';save(copied/'d1_receipt.json',rc)
 elif which=='registry_only':c['observer_id']=99;save(copied/'d1_cov_registry.json',g)
 elif which=='npy_only':a=np.load(p);a[0,0]+=1;np.save(p,a)
 elif which=='sidecar_only':q=load(mf);q['manifest']['x0'][0]+=.1;save(mf,q)
 elif which=='receipt_missing':(copied/'d1_receipt.json').unlink()
 elif which=='registry_missing':(copied/'d1_cov_registry.json').unlink()
 elif which=='cov_missing':p.unlink()
 else:mf.unlink()
 reject(which,lambda:call(reg,env,copied,receipt=rid))
 assert 't1_engine' not in sys.modules

def test_coherent_covariance_replacement_rejected_before_loader(reg,env,copied):
 g=load(copied/'d1_cov_registry.json');r=load(copied/'d1_receipt.json');c=g['configurations']['30101'];p=copied/c['cov_file'];mf=Path(str(p)+'.manifest.json');s=load(mf)
 a=np.load(p)*2;np.save(p,a);c['cov_file_sha256']=s['cov_file_sha256']=sha(p);c['cov_array_sha256']=s['cov_array_sha256']=asha(a);save(mf,s);save(copied/'d1_cov_registry.json',g)
 r['registered']['files'][p.name]=sha(p);r['registered']['files'][mf.name]=sha(mf);r['outputs']['cov_registry_sha256']=sha(copied/'d1_cov_registry.json');save(copied/'d1_receipt.json',r)
 reject('coherent_replacement',lambda:call(reg,env,copied));assert 't1_engine' not in sys.modules

def test_internal_registry_refused(reg,env):reject('internal_registry',lambda:call(registry_from_dict(reg.as_dict()),env))
def test_old_spec_parameter_refused(reg,env):reject('spec_as_reg',lambda:call(build_configuration_manifest(reg).by_id()[30101],env))
@pytest.mark.parametrize('field',['observer_id','position_index','L','weight','circle_status'])
def test_corrupted_old_caller_spec_cannot_enter(field,reg,env):
 s=build_configuration_manifest(reg).by_id()[30101]
 setattr(s,field,{'observational_status':'excluded_by_published_search'} if field=='circle_status' else .123 if field=='weight' else 9.)
 reject('old_spec_'+field,lambda:call(s,env));assert 't1_engine' not in sys.modules

def test_modified_registry_without_rehash_refused(reg,env):
 reg.anchors['E7'][0][0]+=.001;reject('changed_registry',lambda:call(reg,env))

@pytest.mark.parametrize('name',['t1_engine','t2b2_bridge'])
def test_already_loaded_other_module_refused(name,reg,env,monkeypatch,tmp_path):
 m=types.ModuleType(name);m.__file__=str(tmp_path/'untrusted'/f'{name}.py');m.load_cov_full=lambda *a:pytest.fail('must not invoke substitute')
 monkeypatch.setitem(sys.modules,name,m);reject('loaded_other_'+name,lambda:call(reg,env))
@pytest.mark.parametrize('name',['t1_engine','t2b2_bridge'])
def test_disk_source_change_refused(name,reg,env):
 f=env/(name+'.py');f.write_text(f.read_text()+'\n# changed source\n');reject('edited_'+name,lambda:call(reg,env));assert 't1_engine' not in sys.modules

@pytest.mark.parametrize('name',['t1_engine','t2b2_bridge'])
def test_missing_source_refused(name,reg,env):
 (env/(name+'.py')).unlink();reject('missing_'+name,lambda:call(reg,env))

@pytest.mark.parametrize('mode',['root_absent','root_first','root_already_later'])
def test_unloaded_bridge_shadowing_cannot_be_used(mode,reg,env,monkeypatch,tmp_path):
 """No injected sys.modules/importlib: ordinary imports select a shadow bridge.
 Only frozen_loaders SHA is TEST-ONLY bound to our synthetic legitimate files.
 """
 shadow=tmp_path/'other_path';shadow.mkdir();(shadow/'t2b2_bridge.py').write_text('# TEST-ONLY competing bridge\nimport numpy as np\ndef convert(a):return a,np.eye(21)*7.\n')
 rest=[p for p in sys.path if p not in (str(env),str(shadow))]
 if mode=='root_absent':sys.path[:]=[str(shadow)]+rest
 elif mode=='root_first':sys.path[:]=[str(env),str(shadow)]+rest
 else:sys.path[:]=[str(shadow),str(env)]+rest
 assert 't1_engine' not in sys.modules and 't2b2_bridge' not in sys.modules
 try:r=call(reg,env)
 except InputContractError as e:
  PROBES['shadow_'+mode]={'rejected':True,'exception':str(e)};return
 real=load(D1/'d1_cov_registry.json')['configurations']['30101']['intake']['loader_meta']['real_cov_projected_sha256']
 actual=str(Path(sys.modules['t1_engine'].br.__file__).resolve())
 PROBES['shadow_'+mode]={'rejected':False,'actual_bridge':actual,'claimed_bridge':r['loader']['t2b2_bridge_path'],'native_trace':float(np.trace(r['C_real'])),'c_ct':r['c_ct'].tolist(),'C_real_matches_saved':asha(r['C_real'])==real,'loader_calls':sys.modules['t1_engine'].CALLS.copy()}
 assert actual==r['loader']['t2b2_bridge_path'],'unverified shadow bridge used while provenance claims mt_root frozen bridge'
 assert asha(r['C_real'])==real

def test_cached_t1_keeps_wrong_dependency_after_bridge_cache_replaced(reg,env,monkeypatch,tmp_path):
 """Ordinary imports create t1 with a wrong dependency; another import then
 restores sys.modules['t2b2_bridge'] without changing t1.br. Not a wrong-path
 t1 module, nor an in-memory altered load_cov_full function.
 """
 import importlib
 shadow=tmp_path/'shadow';shadow.mkdir();(shadow/'t2b2_bridge.py').write_text('# TEST-ONLY wrong bridge\nimport numpy as np\ndef convert(a):return a,np.eye(21)*7.\n')
 rest=[x for x in sys.path if x not in (str(env),str(shadow))]
 sys.path[:]=[str(shadow),str(env)]+rest
 t1=importlib.import_module('t1_engine');wrong=t1.br
 del sys.modules['t2b2_bridge'];sys.path[:]=[str(env)]+rest
 right=importlib.import_module('t2b2_bridge')
 assert t1.br is wrong and right is not wrong
 assert Path(t1.__file__).resolve()==env/'t1_engine.py'
 assert Path(right.__file__).resolve()==env/'t2b2_bridge.py'
 reject('cached_stale_dependency',lambda:call(reg,env))
 assert not t1.CALLS,'reject must happen before numerical use of stale loader dependency'

def test_repeat_intake_returns_independent_numeric_values(reg,env):
 a=call(reg,env);a['C_real'][0,0]=-999.;a['spec'].observer_id=99
 b=call(reg,env);assert b['C_real'][0,0]>0 and b['spec'].observer_id==1
