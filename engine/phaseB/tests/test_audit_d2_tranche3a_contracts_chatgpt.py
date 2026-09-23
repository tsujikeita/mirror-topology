"""New tranche3a contract probes. Synthetic low-cost banks; no physical/A5/Colab run.
All cache mutation is confined to per-test copies. Fault injection does not alter
verification results, expected hashes, numerical kernels, or submitted source.
"""
from pathlib import Path
import copy,hashlib,json,os,shutil,sys,warnings
import numpy as np
import pytest
PB=Path(os.environ.get('REVIEW_PB',Path(__file__).resolve().parents[1])).resolve()
sys.path[:0]=[str(PB),str(PB/'tests')]
from step1_engine import d2_bank as db
from step1_engine.errors import InputContractError
from step1_engine.orchestrator import ConfigBank
from step1_engine.production import build_family_input
from step1_engine.bootstrap_plan import BootstrapPlan,FittingPlan
from test_d2_tranche2 import _ctx,_Kern
PROBES={};SC=.0002;FS=.001
class Kernel(_Kern):
 def __init__(self):super().__init__();self.scans=0
 def scan(self,X,selection):self.scans+=1;return super().scan(X,selection)

def _sidecar(cid):
 p=PB/'registered_assets/d1';r=json.loads((p/'d1_cov_registry.json').read_text())
 return json.loads((p/(r['configurations'][str(cid)]['cov_file']+'.manifest.json')).read_text())

def _parts(base):
 return dict(eval_dirs={b:str(base/f'e{b}') for b in (0,1)},ref_dirs={b:str(base/f'r{b}') for b in (0,1)},fit_dir=str(base/'f'),ref_fit_dir=str(base/'rf'))

@pytest.fixture(scope='session')
def context(tmp_path_factory):
 reg,man,t,R,d1=_ctx();s=db.load_bank_spec(str(PB/'d/d2_bank_spec.json'));k=Kernel();inv=db.CallInventory()
 roots=dict(model_matched=np.eye(21)*1.1,model_native=np.eye(21)*.9,ref_native=np.diag(np.linspace(.7,1,21)));allroots=roots|{'ref_matched':np.eye(21)}
 base=tmp_path_factory.mktemp('baseline')
 for b in (0,1):
  db.generate_configuration_bank(k,R,t,s,30101,roots,b,str(base/f'e{b}'),inv,('float64',),scale=SC,chunk_clusters=7)
  db.generate_configuration_bank(k,R,t,s,None,{'ref_matched':allroots['ref_matched']},b,str(base/f'r{b}'),inv,('float64',),scale=SC,chunk_clusters=7,family='E7')
 db.generate_fitting_bank(k,R,t,s,30101,roots,str(base/'f'),inv,scale=FS,chunk_clusters=3)
 db.generate_fitting_bank(k,R,t,s,None,{'ref_matched':allroots['ref_matched']},str(base/'rf'),inv,scale=FS,chunk_clusters=3,family='E7')
 yield dict(reg=reg,man=man,table=t,registry=R,spec=s,roots=roots,allroots=allroots,base=base)
 import tempfile; dst=Path(os.environ.get('T3A_PROBES',os.path.join(tempfile.gettempdir(),'t3a_contract_probes.json')));dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(json.dumps(PROBES,indent=2,allow_nan=False))   # adapted: evidence dir not shipped

@pytest.fixture
def data(context,tmp_path):
 base=tmp_path/'cache';shutil.copytree(context['base'],base)
 return context|{'work':base,'kw':dict(config_id=30101,system='matched',**_parts(base),roots=copy.deepcopy(context['allroots']),cov_manifest=_sidecar(30101),formal=False)}

def call_intake(name,kw,require_reject=False):
 try:
  supply,info=db.intake_registered_bank(**kw)
  status=dict(accepted=True,rows=len(supply.T1_model),fit_rows=len(supply.fitting.cid),batches=supply.batches,
   finite_eval=bool(np.isfinite(supply.T1_model).all()),first_model_T1=str(supply.T1_model[0]),first_ref_T1=str(supply.T1_ref[0]))
  try:
   ConfigBank(30101,'E7',kw['system'],1.,supply.T1_model,supply.T2_model,supply.T1_ref,supply.T2_ref,supply.cluster_uids,supply.m,supply.batches);status['consumer_shape']='accepted'
  except Exception as ex:status['consumer_shape']=repr(ex)
  PROBES[name]=status
 except (InputContractError,ValueError,TypeError,KeyError,OSError) as ex:
  PROBES[name]={'accepted':False,'exception':type(ex).__name__,'message':str(ex)}
  if not require_reject:raise
  return None
 assert not require_reject,f'{name}: inconsistent input returned as BankSupply: {PROBES[name]}'
 return supply,info

@pytest.mark.parametrize('family',['E1','E2','E7','E8'])
def test_fitting_all_configurations_and_reference(context,tmp_path,family):
 c=context;k=Kernel();inv=db.CallInventory();cs=[int(i) for i,v in c['spec']['configurations'].items() if v['family']==family]+[None]
 for cid in cs:
  rr=c['roots'] if cid else {'ref_matched':c['allroots']['ref_matched']};p=tmp_path/str(cid)
  m=db.generate_fitting_bank(k,c['registry'],c['table'],c['spec'],cid,rr,str(p),inv,scale=FS,chunk_clusters=1,family=family)
  assert db.verify_bank_dir(str(p))==m
  from step1_engine.d2_rng import generate_from_latent
  out,ids,uids=generate_from_latent(k,rr,c['registry'],'fitting',m['crn_group'],0,2,('float64',),m=100,chunk_clusters=2)
  with np.load(p/m['shards'][0]['file']) as z:
   assert np.array_equal(z['cid'],ids)
   for (role,sel),v in out.items():
    for fld in db.EXPECTED_MEMBERS:assert np.array_equal(z[f'{role}__{sel}__{fld}'],v[fld])
  assert m['n_clusters']==2 and m['n_rows']==200 and len(m['shards'])==1 and m['selections']==['float64']
  assert all(m['calls'][0][kk][2]==300 for kk in ('key_gaussian','key_rotation'))
 PROBES[f'fitting_all_{family}']={'configurations':len(cs)-1,'reference':1,'all_arrays_replay_equal':True}

@pytest.mark.parametrize('system',['matched','native'])
def test_normal_intake_views(data,system):
 s,i=call_intake('normal_'+system,data['kw']|{'system':system})
 cb=ConfigBank(30101,'E7',system,1.,s.T1_model,s.T2_model,s.T1_ref,s.T2_ref,s.cluster_uids,s.m,s.batches)
 assert cb.N0==200 and len(cb.at_stage('N4').T1_model)==800 and len(cb.at_stage('N0').T1_model)==200
 assert s.fitting.K==2 and i['n_clusters']=={0:2,1:6}
 assert s.cluster_uids[2].as_tuple()==(1,200,1003,1,0)
 # returned data/metadata are caller-owned, not aliases to disk or supplied metadata
 s.T1_model[0]=100;s.cov_manifest['manifest'].clear();assert data['kw']['cov_manifest']['manifest']
 call_intake('after_return_edit_'+system,data['kw']|{'system':system})

@pytest.mark.parametrize('system',['matched','native'])
def test_full_surviving_family_consumer(context,tmp_path,system):
 c=context;inv=db.CallInventory();k=Kernel();refs={b:str(tmp_path/f'r{b}') for b in (0,1)};rf=str(tmp_path/'rf')
 for b in (0,1):db.generate_configuration_bank(k,c['registry'],c['table'],c['spec'],None,{'ref_matched':np.eye(21)},b,refs[b],inv,('float64',),scale=SC,family='E7')
 db.generate_fitting_bank(k,c['registry'],c['table'],c['spec'],None,{'ref_matched':np.eye(21)},rf,inv,scale=FS,family='E7')
 supplies=[]
 for cid in [int(i) for i,v in c['spec']['configurations'].items() if v['family']=='E7']:
  rr={r:a*(1+1e-4*(cid-30101)) for r,a in c['roots'].items()};ed={b:str(tmp_path/f'{cid}_{b}') for b in (0,1)};fd=str(tmp_path/f'f{cid}')
  for b in (0,1):db.generate_configuration_bank(k,c['registry'],c['table'],c['spec'],cid,rr,b,ed[b],inv,('float64',),scale=SC)
  db.generate_fitting_bank(k,c['registry'],c['table'],c['spec'],cid,rr,fd,inv,scale=FS)
  s,info=db.intake_registered_bank(cid,system,ed,refs,fd,rf,rr|{'ref_matched':np.eye(21)},_sidecar(cid),formal=False);supplies.append(s)
 uid=supplies[0].cluster_uids;ep={s:BootstrapPlan.build('small',s,{0:uid[:2],1:uid[2:]},20,20260912) for s in range(5)}
 fp={s:FittingPlan.build('smallfit',1,2003,s,2,20,20260912) for s in range(5)}
 fi=build_family_input(c['reg'],c['man'],'E7',system,supplies,ep,fp)
 assert len(fi.configs)==9 and sum(x.weight for x in fi.configs)==pytest.approx(1)
 for x in fi.configs:assert x.at_stage('N0').N0==200 and len(x.at_stage('N4').T1_model)==800
 PROBES['full_family_'+system]={'configs':9,'plans':5,'N0':200,'Nmax':800,'fit_K':2,'scope':'synthetic no Q/KDE evaluation'}

@pytest.mark.parametrize('scale',[0.,-1.,True,float('nan'),float('inf'),.00001])
def test_fitting_invalid_scales(context,tmp_path,scale):
 c=context;k=Kernel();p=tmp_path/'bad'
 with pytest.raises((InputContractError,ValueError,TypeError)):
  db.generate_fitting_bank(k,c['registry'],c['table'],c['spec'],30101,c['roots'],str(p),db.CallInventory(),scale=scale)
 assert k.scans==0 and not (p/'COMPLETE.json').exists()

@pytest.mark.parametrize('family',['E2','unknown'])
def test_fitting_rejects_conflicting_family(context,tmp_path,family):
 c=context;k=Kernel();p=tmp_path/'bad';err=None
 try:db.generate_fitting_bank(k,c['registry'],c['table'],c['spec'],30101,c['roots'],str(p),db.CallInventory(),scale=FS,family=family)
 except (InputContractError,ValueError) as ex:err=str(ex)
 PROBES['conflicting_family_'+family]={'rejected':err is not None,'scans':k.scans,'complete':(p/'COMPLETE.json').exists(),'reason':err}
 assert err is not None and k.scans==0 and not (p/'COMPLETE.json').exists()

@pytest.mark.parametrize('change',['empty','other_position','normalize','tag','env'])
def test_intake_covariance_sidecar(data,change):
 m=copy.deepcopy(data['kw']['cov_manifest'])
 if change=='empty':m['manifest']={}
 elif change=='other_position':m['manifest']=_sidecar(30102)['manifest']
 elif change=='normalize':m['manifest']['run_config']['normalize']=True
 elif change=='tag':m['tag']='E7_wrong'
 elif change=='env':m['manifest']['env_fingerprint']='0'*64
 call_intake('cov_'+change,data['kw']|{'cov_manifest':m},True)

@pytest.mark.parametrize('change',['complex','one_dimensional','numeric_strings'])
def test_intake_root_type_shape(data,change):
 roots=copy.deepcopy(data['allroots'])
 if change=='complex': roots['model_matched']=roots['model_matched'].astype(complex)+2j*np.eye(21)
 elif change=='one_dimensional':roots['model_matched']=roots['model_matched'].reshape(-1)
 else:roots['model_matched']=roots['model_matched'].astype(str)
 with warnings.catch_warnings(record=True) as ws:
  try:call_intake('root_'+change,data['kw']|{'roots':roots},True)
  finally:PROBES['root_'+change]['warnings']=[str(w.message) for w in ws]

@pytest.mark.parametrize('value',[None,0,[]])
def test_formal_boolean(data,value):
 call_intake('formal_'+repr(value),data['kw']|{'formal':value},True)

@pytest.mark.parametrize('scale',[.0004,.0001])
def test_two_batch_ratio(data,tmp_path,scale):
 c=data;k=Kernel();inv=db.CallInventory();ed=str(tmp_path/'new_e1');rd=str(tmp_path/'new_r1')
 db.generate_configuration_bank(k,c['registry'],c['table'],c['spec'],30101,c['roots'],1,ed,inv,('float64',),scale=scale)
 db.generate_configuration_bank(k,c['registry'],c['table'],c['spec'],None,{'ref_matched':c['allroots']['ref_matched']},1,rd,inv,('float64',),scale=scale,family='E7')
 call_intake('batch_ratio_'+str(scale),data['kw']|{'eval_dirs':{0:data['kw']['eval_dirs'][0],1:ed},'ref_dirs':{0:data['kw']['ref_dirs'][0],1:rd}},True)

@pytest.mark.parametrize('where,field',[('e0','finite'),('e1','finite'),('r0','finite'),('f','finite'),('rf','finite'),('e0','nan')])
def test_byte_change_after_verification(data,monkeypatch,where,field):
 kw=data['kw'];p=data['work']/where;man=db.verify_bank_dir(str(p));npz=p/man['shards'][0]['file'];orig=db.verify_bank_dir;changes=[]
 def verify_then_external_write(d,*args,**kws):
  answer=orig(d,*args,**kws)
  if str(d)==kw['ref_fit_dir'] and not changes:
   with np.load(npz,allow_pickle=False) as z:ar={n:z[n] for n in z.files}
   key=('ref_matched' if where.startswith('r') else 'model_matched')+'__float64__T1';old=str(ar[key][0]);ar[key][0]=(ar[key][0]+1234 if field=='finite' else np.nan)
   with npz.open('wb') as f:np.savez(f,**ar)
   changes.append({'verified_file_sha':man['shards'][0]['file_sha256'],'new_file_sha':hashlib.sha256(npz.read_bytes()).hexdigest(),'old':old,'new':str(ar[key][0])})
  return answer
 monkeypatch.setattr(db,'verify_bank_dir',verify_then_external_write)
 name='byte_race_'+where+'_'+field
 try:call_intake(name,kw,True)
 finally:PROBES[name]['file_change_after_real_validation']=changes


def test_identical_replacement_after_verification(data,monkeypatch):
 kw=data['kw'];p=data['work']/'e0';man=db.verify_bank_dir(str(p));npz=p/man['shards'][0]['file'];raw=npz.read_bytes();orig=db.verify_bank_dir
 def wrapper(d,*a,**kwr):
  v=orig(d,*a,**kwr)
  if str(d)==kw['ref_fit_dir']:npz.write_bytes(raw)
  return v
 monkeypatch.setattr(db,'verify_bank_dir',wrapper);call_intake('same_bytes_replacement',kw)

@pytest.mark.parametrize('point',['npz','sidecar','COMPLETE'])
def test_fitting_io_failure_no_complete(context,tmp_path,monkeypatch,point):
 c=context;k=Kernel();orig=db._atomic_write;p=tmp_path/'fail'
 def failing(path,body):
  if (point=='npz' and path.endswith('.npz')) or (point=='sidecar' and path.endswith('.sidecar.json')) or (point=='COMPLETE' and path.endswith('COMPLETE.json')):raise OSError('injected write error')
  return orig(path,body)
 monkeypatch.setattr(db,'_atomic_write',failing)
 with pytest.raises(OSError):db.generate_fitting_bank(k,c['registry'],c['table'],c['spec'],30101,c['roots'],str(p),db.CallInventory(),scale=FS)
 assert not (p/'COMPLETE.json').exists();monkeypatch.setattr(db,'_atomic_write',orig)
 good=tmp_path/'retry';m=db.generate_fitting_bank(k,c['registry'],c['table'],c['spec'],30101,c['roots'],str(good),db.CallInventory(),scale=FS);assert db.verify_bank_dir(str(good))==m

@pytest.mark.parametrize('bad',['nan','missing_T2','bad_cid','bad_shape'])
def test_fitting_bad_result_no_complete(context,tmp_path,monkeypatch,bad):
 c=context;orig=db.generate_from_latent;p=tmp_path/'bad'
 def invalid(*a,**kw):
  out,cid,uid=orig(*a,**kw);v=out[('model_matched','float64')]
  if bad=='nan':v['T1'][0]=np.nan
  elif bad=='missing_T2':del v['T2']
  elif bad=='bad_cid':cid[:]=0
  else:v['T1']=v['T1'][:,None]
  return out,cid,uid
 monkeypatch.setattr(db,'generate_from_latent',invalid)
 with pytest.raises((InputContractError,KeyError)):db.generate_fitting_bank(Kernel(),c['registry'],c['table'],c['spec'],30101,c['roots'],str(p),db.CallInventory(),scale=FS)
 assert not (p/'COMPLETE.json').exists()
