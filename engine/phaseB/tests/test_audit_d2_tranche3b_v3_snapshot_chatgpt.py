"""Source/request/metadata snapshot tests of D2 3b v3.
Actual writer, reader, wrapper; external runtime, PhaseC, roots and kernel use
prior's explicit TEST-ONLY stand-ins. No Colab, physical bank or OT.
"""
from pathlib import Path
import copy,hashlib,json,os,sys,shutil,subprocess,builtins
import numpy as np
import pytest
import test_audit_d2_tranche3b_review_chatgpt as prior   # adapted: the prior review module is the bundled tranche-3b review test
PB=prior.PB; db=prior.db
HASH=lambda b:hashlib.sha256(b).hexdigest()
PROBES={}
@pytest.fixture(scope='session',autouse=True)
def record_probes():
 yield
 import tempfile; p=Path(os.environ.get('EXTRA_PROBES',os.path.join(tempfile.gettempdir(),'t3bv3_snapshot_probes.json')));p.parent.mkdir(parents=True,exist_ok=True)   # adapted
 p.write_text(json.dumps(PROBES,indent=2,default=str,allow_nan=False))
@pytest.fixture(scope='module')
def genuine(tmp_path_factory):
 work=tmp_path_factory.mktemp('genuine_producer')
 with pytest.MonkeyPatch.context() as m:rc,r,g,out=prior.run_script(work,m)
 assert r['stage']=='complete' and r['D2_PASS'] is False and len(g['directories'])==7
 return out,r,g

def rebound_bank(path,mutate):
 p=Path(path); cm=json.loads((p/'COMPLETE.json').read_text())
 for s in cm['shards']:
  f=p/s['sidecar'];obj=json.loads(f.read_text());mutate(obj)
  f.write_text(json.dumps(obj,indent=1));s['sidecar_sha256']=HASH(f.read_bytes())
 cm['manifest_sha256']=HASH(json.dumps({k:v for k,v in cm.items() if k!='manifest_sha256'},sort_keys=True).encode())
 (p/'COMPLETE.json').write_text(json.dumps(cm,indent=1))
 return cm

def test_new_producer_in_every_shard_and_independent_digest(genuine):
 out,r,g=genuine;p=r['producer'];h=HASH(json.dumps({k:v for k,v in p.items() if k!='digest'},sort_keys=True,default=str).encode())
 assert h==p['digest'];assert p['modules']==json.loads((PB/'B2_completion_inventory.json').read_text())['modules']
 assert p['script_sha256']==HASH((PB/'d/d2_bankgen.py').read_bytes())
 assert p['pins_sha256']==HASH((PB/'d/d2_pins.json').read_bytes())
 assert p['inventory_sha256']==HASH((PB/'B2_completion_inventory.json').read_bytes())
 assert p['profile']['selftest'] is True and p['profile']['skip_a10'] is True
 n=0
 for name in g['directories']:
  cm=db.verify_bank_dir(str(out/name))
  for sh in cm['shards']:
   side=json.loads((out/name/sh['sidecar']).read_text());assert side['environment']['producer']==p;n+=1
 assert n==11
 PROBES['normal_binding']={'directories':7,'sidecars':n,'digest':h,'source_keys':list(p),'selftest_pass':r['D2_PASS']}

def test_genuine_bound_cache_reuse_and_output_identity(tmp_path,monkeypatch,genuine):
 src,old,_=genuine;rc,r,g,out=prior.run_script(tmp_path,monkeypatch,reuse=src)
 assert r['stage']=='complete' and not g['calls'] and len(g['calls_reused'])==7
 assert r['producer']==old['producer']
 for name,d in r['directories'].items():
  cm=db.verify_bank_dir(d['path']);dest=Path(d['dependency_metadata'])
  for f in ['COMPLETE.json']+[s['sidecar'] for s in cm['shards']]:assert (src/name/f).read_bytes()==(dest/f).read_bytes()
  assert not d['request'].get('notes')

@pytest.mark.parametrize('field',['modules','script_sha256','pins_sha256','inventory_sha256','crn_table_sha256','spec_sha256','engine_version'])
def test_different_recorded_source_rejected_without_generation(tmp_path,monkeypatch,genuine,field):
 local=tmp_path/'cache';shutil.copytree(genuine[0],local)
 def alter(side):
  p=side['environment']['producer'];p[field]=({**p[field],'d2_rng.py':'0'*64} if field=='modules' else ('different' if field=='engine_version' else '0'*64))
  p['digest']=HASH(json.dumps({k:v for k,v in p.items() if k!='digest'},sort_keys=True,default=str).encode())
 rebound_bank(local/'ref_E7_b0',alter);db.verify_bank_dir(str(local/'ref_E7_b0'))
 before=len(prior.ScriptKernel.instances);rc,r,g,out=prior.run_script(tmp_path/'run',monkeypatch,reuse=local)
 assert r['stage']=='exception' and not r['directories']
 assert sum(k.scans for k in prior.ScriptKernel.instances[before:])==0

@pytest.mark.parametrize('field',['profile','scale'])
def test_different_producer_profile_rejected(tmp_path,monkeypatch,genuine,field):
 local=tmp_path/'cache';shutil.copytree(genuine[0],local)
 def alter(s):
  p=s['environment']['producer'];p['profile'][field]='other_profile' if field=='profile' else .5
  p['digest']=HASH(json.dumps({k:v for k,v in p.items() if k!='digest'},sort_keys=True,default=str).encode())
 rebound_bank(local/'ref_E7_b0',alter)
 rc,r,g,out=prior.run_script(tmp_path/'run',monkeypatch,reuse=local)
 assert r['stage']=='exception' and not r['directories']

def test_partial_with_real_producer_allows_completed_units(tmp_path,monkeypatch):
 old=db._atomic_write
 def fail(p,b):
  if 'cfg30101_w2' in str(p) and str(p).endswith('.sidecar.json'):raise OSError('TEST-ONLY partial unit')
  return old(p,b)
 with monkeypatch.context() as m:
  m.setattr(db,'_atomic_write',fail);rc,r,g,out=prior.run_script(tmp_path/'first',m)
 assert r['stage']=='exception' and len(r['directories'])==6
 with monkeypatch.context() as m:rc2,r2,g2,out2=prior.run_script(tmp_path/'second',m,reuse=out)
 assert r2['stage']=='complete' and len(g2['calls'])==1 and len(g2['calls_reused'])==6
 assert r['producer']==r2['producer']
 PROBES['bound_partial_reuse']={'first_stage':r['stage'],'first_units':6,'new_calls':1,'reused':6,'same_producer':True}

@pytest.fixture(scope='module')
def alternate_source(tmp_path_factory):
 root=tmp_path_factory.mktemp('alternate_source');alt=root/'phaseB';shutil.copytree(PB,alt)
 src=alt/'step1_engine/d2_rng.py';s=src.read_text();old='for kk in ("T1", "T2", "AX", "PL"): out[(r, s)][kk][sl] = d[kk]'
 new='for kk in ("T1", "T2", "AX", "PL"): out[(r, s)][kk][sl] = d[kk] * 1.125 if kk == "T1" else d[kk]'
 assert s.count(old)==1;src.write_text(s.replace(old,new))
 ip=alt/'B2_completion_inventory.json';inv=json.loads(ip.read_text());inv['modules']['d2_rng.py']=HASH(src.read_bytes());ip.write_text(json.dumps(inv,indent=1))
 helper=Path(prior.__file__).parent;res=root/'result.json'
 code="""import sys,json,pytest;from pathlib import Path
import test_audit_d2_tranche3b_review_chatgpt as p
work,result=Path(sys.argv[1]),Path(sys.argv[2])
with pytest.MonkeyPatch.context() as m:
 rc,r,g,out=p.run_script(work,m)
 result.write_text(json.dumps({'record':r,'out':str(out)},indent=1))
"""
 en=dict(os.environ,REVIEW_PB=str(alt),PYTHONPATH=os.pathsep.join(map(str,[helper,alt,alt/'tests'])))
 with (root/'alternate.log').open('w') as f:run=subprocess.run([sys.executable,'-c',code,str(root/'run'),str(res)],env=en,stdout=f,stderr=subprocess.STDOUT,timeout=90)
 assert run.returncode==0,(root/'alternate.log').read_text();obj=json.loads(res.read_text());assert obj['record']['stage']=='complete'
 return Path(obj['out']),obj['record'],root

def test_actual_alternate_source_rejected_normally(tmp_path,monkeypatch,alternate_source,genuine):
 alt,ar,_=alternate_source
 with np.load(alt/'cfg30101_b0/cfg30101_b0_s0.npz',allow_pickle=False) as z:ay=z['model_matched__float64__T1'].copy()
 with np.load(genuine[0]/'cfg30101_b0/cfg30101_b0_s0.npz',allow_pickle=False) as z:x=z['model_matched__float64__T1'].copy()
 assert np.array_equal(ay,x*1.125) and not np.array_equal(x,ay)
 rc,r,g,out=prior.run_script(tmp_path,monkeypatch,reuse=alt)
 assert r['stage']=='exception' and not r['directories']
 PROBES['alternate_normal_rejection']={'different_arrays':True,'factor':1.125,'same_version':ar['producer']['engine_version']==r['producer']['engine_version'],'producer_module_sha':ar['producer']['modules']['d2_rng.py'],'current_module_sha':r['producer']['modules']['d2_rng.py'],'stage':r['stage']}

@pytest.mark.parametrize('action',['current_producer','remove_producer'])
def test_request_match_must_use_the_validated_producer_snapshot(tmp_path,monkeypatch,alternate_source,genuine,action):
 # Actual different-source caches have coherent checksums; only a sidecar path
 # is changed AFTER real validation. No verifier result/expected hash is forged.
 local=tmp_path/'cache';shutil.copytree(alternate_source[0],local)
 old=db.verify_bank_dir;changes=[];captured={}
 def after_verify(p,*a,**k):
  m=old(p,*a,**k)
  if Path(p).parent==local:
   for sh in m['shards']:
    f=Path(p)/sh['sidecar'];captured[str(f)]=f.read_bytes();obj=json.loads(f.read_text())
    if action=='current_producer':obj['environment']['producer']=copy.deepcopy(genuine[1]['producer'])
    else:obj['environment'].pop('producer',None)
    f.write_text(json.dumps(obj,indent=1));changes.append(str(f))
  return m
 monkeypatch.setattr(db,'verify_bank_dir',after_verify)
 rc,r,g,out=prior.run_script(tmp_path/'consumer',monkeypatch,reuse=local)
 exported=[]
 for f in sorted((out/'audit_dependencies').glob('*/*.sidecar.json')):
  p=json.loads(f.read_text())['environment'].get('producer');exported.append(p['modules']['d2_rng.py'] if p else None)
 PROBES['producer_snapshot_race_'+action]={'stage':r['stage'],'D2_PASS':r['D2_PASS'],'accepted_units':len(r['directories']),'changed_paths':len(changes),'exported_producer_d2_rng_shas':sorted(set(exported)),'expected_module_sha':genuine[1]['producer']['modules']['d2_rng.py'],'actual_source_module_sha':alternate_source[1]['producer']['modules']['d2_rng.py'],'numeric_arrays_modified_by_race':False}
 assert changes
 assert r['stage']!='complete','different-source producer was checked via unverified path, but old different-source metadata was exported as accepted'
 assert not r['directories'],'rejected mismatch must not be a successful request unit'

@pytest.mark.parametrize('target',['COMPLETE.json','.sidecar.json'])
def test_metadata_write_failure_does_not_satisfy_unit(tmp_path,monkeypatch,genuine,target):
 op=builtins.open
 def fail(p,*a,**k):
  if 'audit_dependencies/ref_E7_b0/' in str(p) and str(p).endswith(target) and a and a[0]=='wb':raise OSError('TEST-ONLY audit metadata write failure')
  return op(p,*a,**k)
 monkeypatch.setattr(builtins,'open',fail)
 rc,r,g,out=prior.run_script(tmp_path,monkeypatch,reuse=genuine[0])
 assert r['stage']=='exception' and not r['directories']

def test_all_exported_sidecar_bytes_checked_after_write(tmp_path,monkeypatch,genuine):
 op=builtins.open;altered=[]
 class CorruptWriter:
  def __init__(self,f,p):self.f=f;self.p=p
  def write(self,b):
   obj=json.loads(b);obj['m']=-123;bad=json.dumps(obj,indent=1).encode();self.f.write(bad);self.f.flush();altered.append(self.p);return len(b)
  def __enter__(self):return self
  def __exit__(self,*a):return self.f.__exit__(*a)
  def __getattr__(self,n):return getattr(self.f,n)
 def open_hook(p,*a,**k):
  f=op(p,*a,**k)
  if 'audit_dependencies/ref_E7_b0/' in str(p) and str(p).endswith('.sidecar.json') and a and a[0]=='wb':return CorruptWriter(f,str(p))
  return f
 monkeypatch.setattr(builtins,'open',open_hook)
 rc,r,g,out=prior.run_script(tmp_path,monkeypatch,reuse=genuine[0])
 PROBES['export_write_corruption']={'stage':r['stage'],'accepted_units':len(r['directories']),'altered_output_paths':altered,'scope':'TEST-ONLY destination I/O fault; input metadata and NPZ unchanged'}
 assert altered
 assert r['stage']!='complete','post-write output sidecar did not match the verified input bytes'
 assert not r['directories']
