"""Independent tranche3b review. Synthetic statistics + actual writer/reader/adapter.
No physical/A5/Colab/Drive execution. Script probes replace ONLY external
runtime/loader/root/calibration dependencies; request/reuse/PASS logic is real.
All changes are confined to tmp copies. Declared expected failures test contracts.
"""
from pathlib import Path
import os,sys,json,copy,io,hashlib,shutil,types,importlib.util,contextlib
import numpy as np
import pytest
BASE=Path(__file__).resolve().parents[1]
PB=Path(os.environ.get('REVIEW_PB',BASE)).resolve()
sys.path[:0]=[str(PB),str(PB/'tests')]
from step1_engine import d2_bank as db, production, official_gate, legacy_kernel
from step1_engine.d2_rng import generate_from_latent,native_reference_root
from step1_engine.errors import InputContractError
from test_d2_tranche2 import _Kern,_ctx
HASH=lambda b:hashlib.sha256(b).hexdigest()
PROBES={}

@pytest.fixture(scope='session',autouse=True)
def save_probes():
 yield
 import tempfile; p=Path(os.environ.get('T3B_PROBES',os.path.join(tempfile.gettempdir(),'t3b_review_probes.json')));p.parent.mkdir(parents=True,exist_ok=True)   # adapted: evidence dir not shipped
 p.write_text(json.dumps(PROBES,indent=2,default=str,allow_nan=False))

@pytest.fixture(scope='session')
def context():
 reg,man,t,R,d1=_ctx();spec=db.load_bank_spec(str(PB/'d/d2_bank_spec.json'),table=t)
 asset=json.loads((PB/'registered_assets/b3_2_shared_null_asset.json').read_text())
 assert HASH((PB/'registered_assets/b3_2_shared_null_asset.json').read_bytes())==db.SHARED_NULL['file_sha256']
 w=asset['identity']['whitening'];return dict(reg=reg,man=man,t=t,R=R,d1=d1,spec=spec,mu=np.array(w['mu']),W=np.array(w['W']),S=np.eye(21)*1.1)

@pytest.fixture
def wbank(context,tmp_path):
 c=context;d=tmp_path/'w2';inv=db.CallInventory();m=db.generate_w2_position_bank(_Kern(),c['R'],c['t'],c['spec'],30101,c['S'],str(d),inv,scale=.001)
 return c|dict(dir=d,manifest=m)

@pytest.mark.parametrize('family',['E2','E7','E8'])
def test_normal_all_w2_positions(context,tmp_path,family):
 c=context;ids=[int(k) for k,v in c['spec']['configurations'].items() if v['family']==family];seen=[]
 for cid in ids:
  d=tmp_path/str(cid);m=db.generate_w2_position_bank(_Kern(),c['R'],c['t'],c['spec'],cid,c['S'],str(d),db.CallInventory(),scale=.001)
  assert db.verify_bank_dir(str(d))==m
  b64,b32,info=db.intake_w2_position_bank(cid,str(d),c['S'],c['mu'],c['W'],dict(db.SHARED_NULL),formal=False)
  with np.load(d/m['shards'][0]['file'],allow_pickle=False) as z:
   for sel,b in [('float64',b64),('float32',b32)]:
    expect=(np.c_[z[f'model_matched__{sel}__T1'],z[f'model_matched__{sel}__T2']]-c['mu'])@c['W'].T
    assert np.array_equal(expect,b.Tw) and b.K==2 and b.m==100
  seen.append(HASH(b64.Tw.tobytes()))
 assert len(set(seen))==9
 PROBES['all_w2_'+family]={'positions':9,'rows_each':200,'all_paths_match':True}

@pytest.mark.parametrize('change',['mu_shift','W_twice','W_zero','mu_complex','W_complex'])
def test_whitening_actual_values_must_match_registered(wbank,change):
 c=wbank;mu=c['mu'].copy();W=c['W'].copy()
 if change=='mu_shift':mu+=1
 elif change=='W_twice':W*=2
 elif change=='W_zero':W[:]=0
 elif change=='mu_complex':mu=mu.astype(complex)+1j
 else:W=W.astype(complex)+1j*np.eye(2)
 err=None;result=None
 try:result=db.intake_w2_position_bank(30101,str(c['dir']),c['S'],mu,W,dict(db.SHARED_NULL),formal=False)
 except (InputContractError,ValueError,TypeError) as ex:err=str(ex)
 PROBES['whitening_'+change]={'rejected':err is not None,'reason':err,'registered_identity_unchanged':True,'returned_all_zero':None if result is None else bool(np.all(result[0].Tw==0)),'scope':None if result is None else result[2]['scope']}
 assert err is not None,'actual mu/W differed; identifier alone was accepted'

@pytest.mark.parametrize('change',['root','formal','identity','config'])
def test_w2_previous_rejection(wbank,change):
 c=wbank;cid=30101;S=c['S'];ident=dict(db.SHARED_NULL);formal=False
 if change=='root':S=S*2
 elif change=='formal':formal=True
 elif change=='identity':ident['asset_sha256']='0'*64
 else:cid=30102
 with pytest.raises(InputContractError):db.intake_w2_position_bank(cid,str(c['dir']),S,c['mu'],c['W'],ident,formal=formal)

# Script harness: real script source, real modules/metadata/spec and bank writer/readers.
# Phase-C corpus is represented by a tiny fixture and only its *outer* SHA is
# supplied as the accepted SHA; its member set/hash/bytes verification is real.
# Runtime, external loader/physical roots, and expensive A10 calibration values
# are explicit stand-ins, NOT measured passes of those gates.
class ScriptKernel(_Kern):
 instances=[]
 def __init__(self,mt):
  super().__init__();self.C_ISO=np.eye(21);self.generations=0;self.scans=0;self.instances.append(self)
 psqrt=staticmethod(legacy_kernel.LegacyKernel.psqrt)
 def scan(self,X,selection):self.scans+=1;return super().scan(X,selection)
 def generate(self,*args,**kwargs):
  self.generations+=1
  with np.load(PB/'tests/reference_assets/a10a_calibration_official.npz',allow_pickle=False) as z:
   d={k:np.array(z[k],copy=True) for k in ('T1','T2','PL')};d['AX']=d['PL'].copy();cid=z['cid'].copy()
  return {(0,'float64'):d},cid,None

def roots_for(cid):
 return dict(S_matched=np.eye(21)*1.1,S_native=np.eye(21)*.9,c_ct=np.array([3.,2.,1.]))

def run_script(tmp_path,monkeypatch,*,family='E7',scale=.001,configs='30101',reuse=None,official=False,phaseb=None,bad_env=False,bad_root=False,mutate_before_finish=None):
 sp=importlib.util.spec_from_file_location('audit_script_'+str(id(tmp_path)),PB/'d/d2_bankgen.py');mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
 pc=tmp_path/'pc';pc.mkdir(parents=True,exist_ok=True);(pc/'member').write_bytes(b'TEST-ONLY Phase C fixture')
 obj={'files':{'member':{'sha256':HASH((pc/'member').read_bytes()),'bytes':(pc/'member').stat().st_size}}}
 (pc/'PACKET_INVENTORY.json').write_text(json.dumps(obj))
 pin=json.loads((PB/'d/d2_pins.json').read_text());origsha=mod.sha
 monkeypatch.setattr(mod,'sha',lambda p:pin['phaseC_inventory_sha256'] if Path(p)==pc/'PACKET_INVENTORY.json' else origsha(p))
 env={k:v for k,v in pin['environment'].items() if k in ('python','numpy','scipy','healpy','camb','pot')}
 env['blas_threads']=[dict(api='blas',n=2,owner='numpy',lib='openblas')]
 if bad_env:env['python']='WRONG'
 monkeypatch.setattr(official_gate,'current_env',lambda:copy.deepcopy(env));monkeypatch.setitem(sys.modules,'camb',types.SimpleNamespace(__version__=pin['environment']['camb']))
 monkeypatch.setattr(production,'_verified_frozen_loader',lambda *a:(object(),{'scope':'TEST-ONLY external-loader stand-in'}))
 def cov(cid,*a):
  v=roots_for(cid)
  if bad_root:v['S_matched']=v['S_matched']*2
  return v
 monkeypatch.setattr(production,'intake_registered_covariance',cov)
 monkeypatch.setattr(legacy_kernel,'LegacyKernel',ScriptKernel)
 out=tmp_path/'out';argv=['script','--mt',str(tmp_path/'MT_TEST_ONLY'),'--phaseb',str(phaseb or PB),'--phasec',str(pc),'--out',str(out),'--family',family]
 if not official:
  argv+=['--selftest-scale',str(scale),'--selftest-skip-a10']
  if not bad_env:argv+=['--selftest-skip-env-lock']
  if configs is not None:argv+=['--selftest-configs',configs]
 if reuse:argv+=['--reuse-root',str(reuse)]
 monkeypatch.setattr(sys,'argv',argv);before=len(ScriptKernel.instances)
 with contextlib.redirect_stdout(io.StringIO()) as cap:rc=mod.main()
 log=cap.getvalue();(tmp_path/'script.log').write_text(log)
 record=json.loads((out/'d2_run_manifest.json').read_text());registry=json.loads((out/'d2_bank_registry.json').read_text()) if (out/'d2_bank_registry.json').exists() else None
 PROBES['script_'+tmp_path.name]={'rc':rc,'stage':record['stage'],'D2_PASS':record['D2_PASS'],'gates':record['gates'],'directories':record['directories'],'actual_banks_generated':sum(k.scans for k in ScriptKernel.instances[before:]),'calls':None if registry is None else len(registry.get('calls',[]))}
 return rc,record,registry,out

@pytest.fixture(scope='session')
def reuse_cache(context,tmp_path_factory):
 c=context;p=tmp_path_factory.mktemp('reuse');inv=db.CallInventory();k=_Kern()
 pin=json.loads((PB/'d/d2_pins.json').read_text());e={n:v for n,v in pin['environment'].items() if n in ('python','numpy','scipy','healpy','camb','pot')};e['blas_threads']=[dict(api='blas',n=2,owner='numpy',lib='openblas')]
 envrec=dict(python=e['python'],numpy=e['numpy'],scipy=e['scipy'],engine=json.loads((PB/'B2_completion_inventory.json').read_text())['engine_version'],fingerprint=HASH(json.dumps(e,sort_keys=True,default=str).encode()))
 # Complete small caches for E1 (all three configs) and E7 (30101 only).
 for fam in ('E1','E7'):
  for b in (0,1):db.generate_configuration_bank(k,c['R'],c['t'],c['spec'],None,{'ref_matched':np.eye(21)},b,str(p/f'ref_{fam}_b{b}'),inv,('float64',),scale=.001,family=fam,env=envrec)
  db.generate_fitting_bank(k,c['R'],c['t'],c['spec'],None,{'ref_matched':np.eye(21)},str(p/f'ref_{fam}_fit'),inv,scale=.001,family=fam,env=envrec)
 for cid in (10101,10201,10301,30101,30102):
  v=roots_for(cid);roots=dict(model_matched=v['S_matched'],model_native=v['S_native'],ref_native=native_reference_root(v['c_ct']))
  for b in (0,1):db.generate_configuration_bank(k,c['R'],c['t'],c['spec'],cid,roots,b,str(p/f'cfg{cid}_b{b}'),inv,('float64',),scale=.001,env=envrec)
  db.generate_fitting_bank(k,c['R'],c['t'],c['spec'],cid,roots,str(p/f'cfg{cid}_fit'),inv,scale=.001,env=envrec)
  if cid//10000!=1:db.generate_w2_position_bank(k,c['R'],c['t'],c['spec'],cid,v['S_matched'],str(p/f'cfg{cid}_w2'),inv,scale=.001,env=envrec)
 return p

@pytest.mark.parametrize('fam,cfg,n',[('E1',None,12),('E7','30101',7)])
def test_script_small_normal(tmp_path,monkeypatch,fam,cfg,n):
 rc,r,g,out=run_script(tmp_path,monkeypatch,family=fam,configs=cfg)
 assert rc==1 and r['stage']=='complete' and r['D2_PASS'] is False and len(r['directories'])==n and len(g['calls'])==n
 for v in r['directories'].values():assert db.verify_bank_dir(v['path'])['manifest_sha256']==v['manifest_sha256']

def test_script_environment_fails_before_bank_generation(tmp_path,monkeypatch):
 rc,r,g,out=run_script(tmp_path,monkeypatch,bad_env=True)
 assert r['stage']=='environment' and not r['directories'] and r['D2_PASS'] is False

def test_script_normal_same_scope_reuse(tmp_path,monkeypatch,reuse_cache):
 rc,r,g,out=run_script(tmp_path,monkeypatch,reuse=reuse_cache)
 assert r['stage']=='complete' and r['D2_PASS'] is False and len(g['calls'])==0 and all(x['reused'] for x in r['directories'].values())

def test_script_official_must_not_promote_small_cache(tmp_path,monkeypatch,reuse_cache):
 rc,r,g,out=run_script(tmp_path,monkeypatch,family='E1',reuse=reuse_cache,official=True)
 PROBES['official_small_cache']={'rc':rc,'D2_PASS':r['D2_PASS'],'registry_formal':g.get('formal'),'bank_formals':[v['formal'] for v in r['directories'].values()],'rows':[v['n_rows'] for v in r['directories'].values()],'calls':len(g.get('calls',[])),'scope':'Gate assumptions supplied by TEST-ONLY runtime/loader/calibration. No real official gate success claimed.'}
 assert not r['D2_PASS'],'small nonformal caches promoted to D2_PASS'

@pytest.mark.parametrize('mismatch',['config','purpose','batch','root','scale','environment'])
def test_reuse_must_match_current_request(tmp_path,monkeypatch,reuse_cache,mismatch,context):
 local=tmp_path/'reuse';shutil.copytree(reuse_cache,local)
 if mismatch in ('config','purpose','batch'):
  dst=local/'cfg30101_b0';shutil.rmtree(dst)
  src=local/({'config':'cfg30102_b0','purpose':'cfg30101_fit','batch':'cfg30101_b1'}[mismatch]);shutil.copytree(src,dst)
 if mismatch=='environment':
  dst=local/'cfg30101_b0';shutil.rmtree(dst);c=context;v=roots_for(30101);rs=dict(model_matched=v['S_matched'],model_native=v['S_native'],ref_native=native_reference_root(v['c_ct']))
  db.generate_configuration_bank(_Kern(),c['R'],c['t'],c['spec'],30101,rs,0,str(dst),db.CallInventory(),('float64',),scale=.001,env={'python':'OTHER_GENERATION_ENV','fingerprint':'0'*64})
 rc,r,g,out=run_script(tmp_path,monkeypatch,reuse=local,scale=.002 if mismatch=='scale' else .001,bad_root=mismatch=='root')
 assert r['stage']!='complete','valid cache accepted for a different generation request: '+mismatch


def run_notebook_final(out,rm,returncode,tmp_path,monkeypatch):
 import zipfile
 actual=tmp_path/'actual_return.zip';real_zip=zipfile.ZipFile
 fakezip=types.ModuleType('zipfile');fakezip.ZIP_DEFLATED=zipfile.ZIP_DEFLATED
 fakezip.ZipFile=lambda _p,*a,**k:real_zip(actual,*a,**k)
 monkeypatch.setitem(sys.modules,'zipfile',fakezip)
 colab=types.ModuleType('google.colab');colab.files=types.SimpleNamespace(download=lambda p:None)
 monkeypatch.setitem(sys.modules,'google.colab',colab)
 nb=json.loads((PB/'d/MirrorTopology_Step1_D2_bankgen_v0.1.ipynb').read_text())
 nsos=types.SimpleNamespace(walk=os.walk,path=types.SimpleNamespace(join=os.path.join,relpath=os.path.relpath,getsize=lambda p:actual.stat().st_size if str(p).startswith('/content/d2_') else os.path.getsize(p)))
 ns=dict(os=nsos,json=json,sha=lambda p:HASH(Path(p).read_bytes()),OUT=str(out),RUN=str(out.parent),FAMILY='E7',REPO_COMMIT='a'*40,lock={'scope':'TEST_ONLY notebook fixture'},rc=types.SimpleNamespace(returncode=returncode),rm=rm,script_ok=(returncode==0 and rm.get('D2_PASS') is True))
 with contextlib.redirect_stdout(io.StringIO()):exec(compile(''.join(nb['cells'][5]['source']),'submitted_notebook_cell5','exec'),ns)
 with real_zip(actual) as z:names=z.namelist()
 return ns,names

def test_reused_dependency_metadata_is_in_return_tree(tmp_path,monkeypatch,reuse_cache):
 rc,r,g,out=run_script(tmp_path,monkeypatch,reuse=reuse_cache)
 assert r['stage']=='complete'
 nbout=tmp_path/'notebook_out';nbout.mkdir();shutil.copytree(out,nbout/'d2')
 ns,emitted=run_notebook_final(nbout,r,rc,tmp_path,monkeypatch)
 PROBES['reuse_return_packet']={'emitted_metadata_files':emitted,'directory_refs':len(r['directories']),'included_complete_manifests':sum(p.endswith('COMPLETE.json') for p in emitted),'actual_notebook_cell5_executed':True}
 assert any(p.endswith('COMPLETE.json') for p in emitted),'reuse-only audit export has no completion manifests or sidecars'

@pytest.mark.parametrize('returncode,scriptpass',[(0,True),(0,False),(1,True),(1,False)])
def test_notebook_final_pass_requires_both(tmp_path,monkeypatch,returncode,scriptpass):
 import subprocess
 out=tmp_path/'nbout';do=out/'d2';do.mkdir(parents=True)
 rm={'D2_PASS':scriptpass,'gates':{},'directories':{}}
 (do/'d2_run_manifest.json').write_text(json.dumps(rm))
 monkeypatch.setattr(subprocess,'run',lambda *a,**k:types.SimpleNamespace(returncode=returncode,stdout='TEST_ONLY',stderr=''))
 nb=json.loads((PB/'d/MirrorTopology_Step1_D2_bankgen_v0.1.ipynb').read_text())
 ns=dict(sys=sys,subprocess=subprocess,json=json,OUT=str(out),SCRIPT='TEST_ONLY_NO_EXTERNAL_PROCESS',MT='TEST_ONLY',PHASEB=str(PB),PHASEC='TEST_ONLY',FAMILY='E7',REUSE_ROOT='')
 with contextlib.redirect_stdout(io.StringIO()):exec(compile(''.join(nb['cells'][4]['source']),'submitted_notebook_cell4','exec'),ns)
 assert ns['script_ok'] is (returncode==0 and scriptpass)
 final,names=run_notebook_final(out,rm,returncode,tmp_path,monkeypatch)
 assert final['final']['D2_PASS'] is (returncode==0 and scriptpass)
 assert 'd2_final_record.json' in names


def test_a10_fixed_reference_is_verified_before_reproduction(tmp_path,monkeypatch,reuse_cache):
 # Same supplied source/inventory; alter only the *fixed reference* NPZ copy.
 cp=tmp_path/'phaseB';shutil.copytree(PB,cp)
 ref=cp/'tests/reference_assets/a10a_calibration_official.npz'
 with np.load(ref,allow_pickle=False) as z:d={k:z[k].copy() for k in z.files}
 d['T1']*=1+1e-12
 np.savez(ref,**d)
 inv=json.loads((cp/'B2_completion_inventory.json').read_text())
 assert inv['assets_sha256']['tests/reference_assets/a10a_calibration_official.npz']!=HASH(ref.read_bytes())
 rc,r,g,out=run_script(tmp_path,monkeypatch,family='E1',reuse=reuse_cache,official=True,phaseb=cp)
 PROBES['changed_A10_reference']={'modified_file_sha':HASH(ref.read_bytes()),'expected_file_sha':inv['assets_sha256']['tests/reference_assets/a10a_calibration_official.npz'],'D2_PASS':r['D2_PASS'],'a10':r.get('a10_cross_check')}
 assert not r['gates']['G_calibration_bank_matches_a10'],'changed frozen reference was not rejected by file identity before numerics'
