"""Independent B-3-2B v0.4 audit. Local filesystem/thread only, no Google Drive or Colab.
Real submitted builder creates TEST-ONLY inputs with n_sub=2000/5000,
B_max=4 and K=1600, m=10; distance is a cheap mean difference, not exact OT.
Submission is read-only. Corruptions affect temporary copies only.
"""
from pathlib import Path
from dataclasses import replace
import copy,hashlib,json,os,shutil,subprocess,sys,threading,time,types
import numpy as np
import pytest
import tempfile
ROOT=Path(os.environ.get('B32_REVIEW_ROOT',tempfile.mkdtemp(prefix='b32v04_'))); (ROOT/'evidence').mkdir(parents=True,exist_ok=True)
P=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(P))
from step1_engine import ckpt_persist as cp,w2_shared_build as wb,w2_shared as ws,positions as pos,w2_manifest as wm,serialization as ser
from step1_engine.errors import InputContractError
ROOT.mkdir(parents=True,exist_ok=True);R={}
def rec(k,v):
 R[k]=v;(ROOT/'probes.json').write_text(json.dumps(R,indent=2,ensure_ascii=False,default=str))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cell(i):return ''.join(json.loads((P/'b3/MirrorTopology_Step1_B3_2B_shared_null_v0.5.ipynb').read_text())['cells'][i]['source'])
def cheap(a,b):return float(np.linalg.norm(a.mean(0)-b.mean(0)))
LOCK=dict(commit='c'*40,inventory_sha256=sha(P/'B2_completion_inventory.json'),launcher_id='TEST_ONLY',pins_sha256=sha(P/'b3/b3_2_pins.json'),run_id='audit_run')
@pytest.fixture
def s(tmp_path,monkeypatch):
 cfg=replace(wb.RULES,B_levels=(2,4),first_comparison=(2,4),n_subs=(2000,5000))
 for mod in (wb,ws,pos,wm):monkeypatch.setattr(mod,'RULES',cfg)
 rng=np.random.default_rng(324);cid=np.repeat(np.arange(1600),10);x=rng.normal(size=(16000,2));y=x+.002*rng.normal(size=x.shape)
 a,b=pos.PositionBank(0,x,cid),pos.PositionBank(0,y,cid.copy());ck=tmp_path/'ck';ck.mkdir();wid=dict(source='TEST_ONLY_W');prov=dict(profile='TEST_ONLY',inventory_sha256=LOCK['inventory_sha256'])
 cnt=[0]
 def partial(a,b):
  cnt[0]+=1
  if cnt[0]>6:raise KeyboardInterrupt('TEST_ONLY stop after 2')
  return cheap(a,b)
 partial.__name__=cheap.__name__
 with pytest.raises(KeyboardInterrupt):wb.null_sequence_resumable(a,2000,10,712,str(ck/'null_nsub2000.json'),partial,b,every=2,log=lambda *a:None,whitening_identity=wid,provenance=prov)
 pb=(ck/'null_nsub2000.json').read_bytes()
 asset=wb.build_shared_null_resumable(a,10,712,str(ck),dist=cheap,iso_f32=b,whitening_identity=wid,provenance=prov,log=lambda *a:None)
 return dict(ck=ck,root=tmp_path/'persist',a=a,b=b,wid=wid,prov=prov,partial=pb,asset=asset)
def pub(s):return cp.publish_generation(str(s['ck']),str(s['root']),LOCK,note=lambda *a:None)
def make_partial(s):
 (s['ck']/'null_nsub5000.json').unlink();(s['ck']/'null_nsub2000.json').write_bytes(s['partial'])

def test_real_partial_roundtrip(s,tmp_path):
 make_partial(s);g=pub(s);st=tmp_path/'restore';r=cp.restore_generation(str(s['root']),str(st),LOCK)
 a=wb.build_shared_null_resumable(s['a'],10,712,str(st),dist=cheap,iso_f32=s['b'],whitening_identity=s['wid'],provenance=s['prov'],log=lambda *a:None)
 rec('normal_partial',dict(restore=r,asset_equal=a.sha256==s['asset'].sha256))
 assert r['resumable'] and a.sha256==s['asset'].sha256

def test_complete_resume_avoids_distance_recomputation(s,tmp_path):
 g=pub(s);st=tmp_path/'restore';cp.restore_generation(str(s['root']),str(st),LOCK);calls=[]
 def counted(a,b):calls.append(1);return cheap(a,b)
 counted.__name__=cheap.__name__
 a=wb.build_shared_null_resumable(s['a'],10,712,str(st),dist=counted,iso_f32=s['b'],whitening_identity=s['wid'],provenance=s['prov'],log=lambda *a:None)
 rec('normal_complete',dict(calls=len(calls),asset_equal=a.sha256==s['asset'].sha256));assert not calls and a.sha256==s['asset'].sha256

@pytest.mark.parametrize('kind',['filename','done_bool','done_mismatch','digest'])
def test_checkpoint_structure_refusal(s,kind):
 f=s['ck']/'null_nsub2000.json';d=ser.loads(f.read_text())
 if kind=='filename':f.write_bytes((s['ck']/'null_nsub5000.json').read_bytes())
 else:
  if kind=='done_bool':d['done']=True
  if kind=='done_mismatch':d['done']=3
  if kind=='digest':d['values'][0]*=2
  f.write_text(ser.dumps(d))
 with pytest.raises(InputContractError):cp.inspect_local(str(s['ck']))
 rec('refused_'+kind,True)

@pytest.mark.parametrize('kind',['missing_earlier','common_identity'])
def test_invalid_snapshot_must_preserve_last_resumable_generation(s,kind):
 old=Path(pub(s));oldhash={p.name:sha(p) for p in old.iterdir()};ptr=(s['root']/'LATEST').read_text()
 if kind=='missing_earlier':(s['ck']/'null_nsub2000.json').unlink()
 else:
  f=s['ck']/'null_nsub5000.json';d=ser.loads(f.read_text());d['identity']['whitening']={'source':'DIFFERENT_TEST_W'};f.write_text(ser.dumps(d))
 assert cp.inspect_local(str(s['ck']))['resumable'] is False
 outcomes=[]
 for _ in range(3):
  try:g=pub(s);outcomes.append(dict(path=g,returned=True))
  except InputContractError as e:outcomes.append(dict(rejected=True,error=str(e)))
 latest=cp.latest_generation(str(s['root']));m=cp.verify_generation(latest) if latest else None
 v=dict(old_retained=old.exists(),old_bytes_unchanged=old.exists() and {p.name:sha(p) for p in old.iterdir()}==oldhash,pointer_unchanged=(s['root']/'LATEST').read_text()==ptr,latest_resumable=(m or {}).get('resumable'),outcomes=outcomes,retained_generations=len(list(s['root'].glob('gen_*'))))
 rec('invalid_publication_'+kind,v)
 assert v['old_retained'] and v['old_bytes_unchanged'] and v['pointer_unchanged'] and v['latest_resumable'],'invalid snapshots replaced/pruned the last resumable generation'

@pytest.mark.parametrize('field',['done','complete','stage_state'])
def test_manifest_progress_fields_match_copied_checkpoint(s,field):
 g=Path(pub(s));f=g/'generation_manifest.json';d=json.loads(f.read_text())
 if field=='done':d[field]['null_nsub2000.json']=3
 if field=='complete':d[field]['null_nsub2000.json']=False
 if field=='stage_state':d[field]['2000']='partial:3'
 f.write_text(json.dumps(d))
 try:r=cp.verify_generation(str(g));accepted=True
 except InputContractError:accepted=False
 rec('manifest_'+field,dict(accepted=accepted,checkpoint_changed=False,field=field))
 assert not accepted,f'{field} contradicts checkpoint but was accepted'

def test_copy_source_updated_before_copy_uses_copied_progress(s,monkeypatch):
 full=(s['ck']/'null_nsub2000.json').read_bytes();make_partial(s);original=cp.inspect_local;done=[False]
 def inspect(path):
  d=original(path)
  if str(path)==str(s['ck']) and not done[0]:done[0]=True;tmp=s['ck']/'x.tmp';tmp.write_bytes(full);os.replace(tmp,s['ck']/'null_nsub2000.json')
  return d
 monkeypatch.setattr(cp,'inspect_local',inspect);g=pub(s);man=cp.verify_generation(g)
 actual=cp.verify_checkpoint_file(str(Path(g)/'null_nsub2000.json'))['done'];rec('copied_progress',dict(manifest=man['done'],actual=actual));assert man['done']['null_nsub2000.json']==actual==4

def test_mid_copy_failure_keeps_good_generation(s,monkeypatch):
 old=Path(pub(s));before={p.name:sha(p) for p in old.iterdir()};ptr=(s['root']/'LATEST').read_text()
 def fail(src,dst):Path(dst).write_bytes(Path(src).read_bytes()[:23]);raise OSError('TEST_ONLY copy interrupt')
 monkeypatch.setattr(cp.shutil,'copyfile',fail)
 with pytest.raises(OSError):pub(s)
 assert old.exists() and before=={p.name:sha(p) for p in old.iterdir()} and ptr==(s['root']/'LATEST').read_text();rec('copy_interrupted',{'old_unchanged':True,'pointer_unchanged':True})

def test_serialized_concurrent_publishers_both_complete(s,monkeypatch):
 pub(s);started=threading.Event();release=threading.Event();second_copy=threading.Event();orig=cp.shutil.copyfile;events=[];errs=[];out={}
 def copyfile(src,dst):
  name=threading.current_thread().name;events.append(name)
  if name=='audit-A' and not started.is_set():started.set();assert release.wait(5)
  if name=='audit-B':second_copy.set()
  return orig(src,dst)
 monkeypatch.setattr(cp.shutil,'copyfile',copyfile)
 def target():
  try:out[threading.current_thread().name]=pub(s)
  except BaseException as e:errs.append(repr(e))
 a=threading.Thread(target=target,name='audit-A');b=threading.Thread(target=target,name='audit-B');a.start();assert started.wait(4);b.start();early=second_copy.wait(.12);release.set();a.join(5);b.join(5)
 latest=cp.latest_generation(str(s['root']));rec('serialized_concurrent',dict(second_entered_early=early,events=events,errors=errs,completed=list(out),latest=latest))
 assert not early and not a.is_alive() and not b.is_alive() and not errs and len(out)==2 and latest in out.values() and cp.verify_generation(latest)['resumable']

def test_wrong_restore_lock_preserves_source_and_destination(s,tmp_path):
 g=Path(pub(s));before={p.name:sha(p) for p in g.iterdir()};st=tmp_path/'must_not_exist'
 with pytest.raises(InputContractError):cp.restore_generation(str(s['root']),str(st),dict(LOCK,commit='d'*40))
 assert not st.exists() and before=={p.name:sha(p) for p in g.iterdir()}

def test_numpy_free_import_and_environment_order():
 code=f'import sys,json;sys.path.insert(0,{str(P)!r});import step1_engine.ckpt_persist;print(json.dumps({{"numpy_loaded":"numpy" in sys.modules}}))'
 r=subprocess.run([sys.executable,'-S','-c',code],capture_output=True,text=True,check=True);v=json.loads(r.stdout);rec('clean_import',v)
 assert not v['numpy_loaded'] and 'ckpt_persist' not in cell(2) and 'ckpt_persist' in cell(4) and "pip','install" in cell(3)

def test_numpy_free_serializer_matches_real_checkpoint_digest(s):
 for p in s['ck'].glob('*.json'):
  raw=p.read_text();assert cp.ser.loads(raw)==ser.loads(raw);d=ser.loads(raw)
  assert cp._payload_digest(d['values'],d['blocks'],d['pairwise'],d['bounds'])==d['payload_digest']
 assert cp.ser.dumps({'x':float('inf'),'y':{1:[float('-inf'),True]}})==ser.dumps({'x':float('inf'),'y':{1:[float('-inf'),True]}})

@pytest.mark.parametrize('status',['ok','subprocess_error','publish_error'])
def test_actual_worker_joins_before_log_close(tmp_path,monkeypatch,status):
 started=threading.Event();release=threading.Event();records=[]
 def pubstub(*a,**kw):
  records.append(dict(thread=threading.current_thread().name,closed=ns['plog'].closed));started.set();assert release.wait(3)
  if status=='publish_error':raise OSError('TEST_ONLY publisher failure')
  return '/TEST_ONLY/generation'
 monkeypatch.setattr(cp,'publish_generation',pubstub)
 def proc(*a,**k):
  assert started.wait(3);threading.Timer(.15,release.set).start()
  if status=='subprocess_error':raise RuntimeError('TEST_ONLY subprocess failure')
  return types.SimpleNamespace(returncode=0,stdout='TEST_ONLY',stderr='')
 out=tmp_path/'out';(out/'null').mkdir(parents=True);(out/'null/b3_2_shared_null_run_manifest.json').write_text('{"B3_2B_PASS":true,"failures":[]}')
 ns=dict(OUT=str(out),PERSIST_RUN=str(tmp_path/'persist'),lock=LOCK,sys=sys,os=os,time=time,json=json,subprocess=types.SimpleNamespace(run=proc),SCRIPT='TEST_ONLY',MT='TEST_ONLY',PHASEB=str(P))
 # Only shorten the poll interval; actual join and close logic is unchanged.
 code=cell(5).replace("state['script_done'].wait(60)","state['script_done'].wait(.001)")
 if status=='subprocess_error':
  with pytest.raises(RuntimeError):exec(compile(code,'actual_B_v04_cell5','exec'),ns)
 else:exec(compile(code,'actual_B_v04_cell5','exec'),ns)
 rec('worker_'+status,dict(records=records,alive=ns['th'].is_alive(),log_closed=ns['plog'].closed,failures=ns['state']['failures'],script_ok=ns.get('script_ok')))
 assert not ns['th'].is_alive() and ns['plog'].closed and records and all(r['thread']=='publisher' and not r['closed'] for r in records)
 if status=='publish_error':assert ns['state']['failures']>=1
