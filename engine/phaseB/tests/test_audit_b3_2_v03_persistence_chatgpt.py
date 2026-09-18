"""Independent B-3-2B v0.3 persistence review. All data are TEST-ONLY.
Small fixture: n_sub 2000/5000 retained; B_max=4 and K=1600/m=10.
No Colab, Drive, exact POT or physical cosmological bank is executed.
Submitted files are never modified. Faults affect local test copies only.
"""
from pathlib import Path
import ast,copy,hashlib,json,os,shutil,subprocess,sys,threading,time,types,uuid
from dataclasses import replace
import numpy as np
import pytest
import tempfile
ROOT=Path(os.environ.get('B32_REVIEW_ROOT',tempfile.mkdtemp(prefix='b32v03_'))); P=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1])); (ROOT/'evidence').mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(P))
from step1_engine import ckpt_persist as cp, w2_shared_build as wb, w2_shared as ws,positions as pos,w2_manifest as wm,serialization as ser
from step1_engine.errors import InputContractError
REPORT={}
def record(k,v):
 REPORT[k]=v;(ROOT/'evidence/persistence_probes.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2,default=str))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cell(i):return ''.join(json.loads((P/'b3/MirrorTopology_Step1_B3_2B_shared_null_v0.3.ipynb').read_text())['cells'][i]['source'])
def cheap(a,b):return float(np.linalg.norm(a.mean(0)-b.mean(0)))
LOCK=dict(commit='c'*40,inventory_sha256=sha(P/'B2_completion_inventory.json'),launcher_id='TEST-ONLY',pins_sha256=sha(P/'b3/b3_2_pins.json'),engine_version='0.50.0',run_id='TEST-RUN')
@pytest.fixture
def state(tmp_path,monkeypatch):
 cfg=replace(wb.RULES,B_levels=(2,4),first_comparison=(2,4),n_subs=(2000,5000))
 for mod in [wb,ws,pos,wm]:monkeypatch.setattr(mod,'RULES',cfg)
 rng=np.random.default_rng(323); x=rng.normal(size=(16000,2)); cid=np.repeat(np.arange(1600),10)
 a=pos.PositionBank(0,x,cid);b=pos.PositionBank(0,x+.002*rng.normal(size=x.shape),cid.copy())
 ck=tmp_path/'ck';ck.mkdir();wid={'source':'TEST-ONLY-W'};prov={'inventory_sha256':LOCK['inventory_sha256'],'pins_sha256':LOCK['pins_sha256'],'profile':'TEST-ONLY'}
 calls={'n':0}
 def stopping(x,y):
  calls['n']+=1
  if calls['n']>6: raise KeyboardInterrupt('TEST-ONLY planned stop after 2 replicates')
  return cheap(x,y)
 stopping.__name__=cheap.__name__
 with pytest.raises(KeyboardInterrupt):wb.null_sequence_resumable(a,2000,10,712,str(ck/'null_nsub2000.json'),stopping,b,every=2,log=lambda *x:None,whitening_identity=wid,provenance=prov)
 partial=(ck/'null_nsub2000.json').read_bytes()
 full=wb.build_shared_null_resumable(a,10,712,str(ck),dist=cheap,iso_f32=b,whitening_identity=wid,provenance=prov,log=lambda *x:None)
 complete={f.name:f.read_bytes() for f in ck.glob('*.json')}
 return dict(ck=ck,root=tmp_path/'persist',partial=partial,complete=complete,a=a,b=b,wid=wid,prov=prov,asset=full)
def make_partial(s):
 for f in s['ck'].iterdir():f.unlink()
 (s['ck']/'null_nsub2000.json').write_bytes(s['partial'])
def gen(s):return Path(cp.publish_generation(str(s['ck']),str(s['root']),LOCK,note=lambda *x:None))

def test_normal_partial_publish_restore_resume_equals_full(state,tmp_path):
 s=state;make_partial(s);g=gen(s);st=tmp_path/'staging';r=cp.restore_generation(str(s['root']),str(st),LOCK)
 got=wb.build_shared_null_resumable(s['a'],10,712,str(st),dist=cheap,iso_f32=s['b'],whitening_identity=s['wid'],provenance=s['prov'],log=lambda *x:None)
 record('normal_partial',dict(restored=r,asset_equal=got.sha256==s['asset'].sha256,asset_sha=got.sha256))
 assert r['partial_state']=={'null_nsub2000.json':2} and got.sha256==s['asset'].sha256

def test_wrong_lock_rejected_before_staging_and_preserves_source(state,tmp_path):
 g=gen(state);before={f.name:sha(f) for f in g.iterdir()};st=tmp_path/'staging'
 with pytest.raises(InputContractError):cp.restore_generation(str(state['root']),str(st),dict(LOCK,commit='d'*40))
 assert not st.exists() and {f.name:sha(f) for f in g.iterdir()}==before
 record('wrong_lock_before_copy',{'staging_not_created':True,'source_unchanged':True})

def test_nonempty_destination_untouched(state,tmp_path):
 gen(state);st=tmp_path/'existing';st.mkdir();(st/'keep').write_text('untouched')
 with pytest.raises(InputContractError):cp.restore_generation(str(state['root']),str(st),LOCK)
 assert sorted(x.name for x in st.iterdir())==['keep'] and (st/'keep').read_text()=='untouched'

def test_unrelated_json_only_not_resumable(tmp_path):
 (tmp_path/'unrelated.json').write_text('{}');assert cp.inspect_local(str(tmp_path))['resumable'] is False

def test_copy_failure_keeps_previous_generation(state,monkeypatch):
 s=state;g=gen(s);before={f.name:sha(f) for f in g.iterdir()};time.sleep(.005)
 def broken(src,dst):Path(dst).write_bytes(Path(src).read_bytes()[:23]);raise OSError('TEST-ONLY interrupted copy')
 monkeypatch.setattr(cp.shutil,'copyfile',broken)
 with pytest.raises(OSError):gen(s)
 assert cp.latest_generation(str(s['root']))==str(g) and {f.name:sha(f) for f in g.iterdir()}==before
 record('interrupted_copy',{'previous_generation_unchanged':True,'latest_unchanged':True})

def test_truncated_checkpoint_rejected(state):
 f=state['ck']/'null_nsub2000.json';f.write_bytes(f.read_bytes()[:23])
 with pytest.raises(InputContractError):cp.inspect_local(str(state['ck']))

def test_three_generation_retention(state):
 paths=[]
 for i in range(5):time.sleep(.003);paths.append(gen(state))
 kept=sorted(g.name for g in state['root'].glob('gen_*'))
 assert kept==sorted(g.name for g in paths[-3:]);assert cp.verify_generation(str(paths[-1]))
 record('retention',dict(published=5,retained=len(kept)))

def test_second_stage_without_first_must_not_be_resumable(state,tmp_path):
 s=state;old=gen(s);before={f.name:sha(f) for f in old.iterdir()};pointer=(s['root']/'LATEST').read_text()
 (s['ck']/'null_nsub2000.json').unlink();info=cp.inspect_local(str(s['ck']))
 assert info['resumable'] is False
 for _ in range(3):
  with pytest.raises(InputContractError):gen(s)
 assert old.exists() and {f.name:sha(f) for f in old.iterdir()}==before
 assert (s['root']/'LATEST').read_text()==pointer
 assert cp.verify_generation(str(old))['resumable'] is True
 record('missing_first_stage',dict(inspect_resumable=False,publication_refused=True,old_generation_unchanged=True,latest_unchanged=True))

def test_checkpoint_filename_must_match_identity(state):
 s=state;make_partial(s);(s['ck']/'null_nsub2000.json').write_bytes(s['complete']['null_nsub5000.json'])
 try:info=cp.inspect_local(str(s['ck']));accepted=info['resumable']
 except InputContractError:info=None;accepted=False
 record('wrong_nsub_filename',dict(accepted=accepted,info=info))
 assert not accepted,'2000 filename was accepted with a 5000 checkpoint identity'

def test_done_count_must_match_payload_before_publication(state):
 s=state;make_partial(s);f=s['ck']/'null_nsub2000.json';d=ser.loads(f.read_text());d['done']=3;f.write_text(ser.dumps(d))
 try:g=gen(s);accepted=True;v=cp.verify_generation(str(g))
 except InputContractError:accepted=False;v=None
 record('edited_done',dict(accepted=accepted,done=3,actual_values=len(d['values']),manifest_done=None if v is None else v['done'],payload_digest_changed=False))
 assert not accepted,'contradictory progress header was accepted without changing any payload digest'

def test_generation_done_must_match_checkpoint(state):
 g=gen(state);m=g/'generation_manifest.json';d=json.loads(m.read_text());d['done']['null_nsub2000.json']=3;m.write_text(json.dumps(d))
 try:v=cp.verify_generation(str(g));accepted=True
 except InputContractError:accepted=False
 record('generation_header',dict(accepted=accepted,manifest_done=3,checkpoint_done=4,checkpoint_digest_changed=False))
 assert not accepted,'generation progress not checked against its checkpoint'

def test_concurrent_local_update_must_publish_consistent_progress(state,monkeypatch):
 s=state;make_partial(s);real=cp.inspect_local;trigger={'done':False}
 def race(path):
  info=real(path)
  if str(path)==str(s['ck']) and not trigger['done']:
   trigger['done']=True;tmp=s['ck']/'tmp';tmp.write_bytes(s['complete']['null_nsub2000.json']);os.replace(tmp,s['ck']/'null_nsub2000.json')
  return info
 monkeypatch.setattr(cp,'inspect_local',race);g=gen(s);man=cp.verify_generation(str(g));actual=cp.verify_checkpoint_file(str(g/'null_nsub2000.json'))['done']
 record('writer_publish_race',dict(manifest_done=man['done']['null_nsub2000.json'],actual_checkpoint_done=actual))
 assert man['done']['null_nsub2000.json']==actual,'publish progress was taken before the copied checkpoint snapshot'

def test_clean_import_does_not_preload_numpy_before_environment_install():
 site_path=str(Path(np.__file__).resolve().parents[1])
 code=f"import sys,json; sys.path[:0]=[{str(P)!r},{site_path!r}]; before='numpy' in sys.modules; import step1_engine.ckpt_persist; print(json.dumps(dict(before=before,after='numpy' in sys.modules,numpy=(sys.modules['numpy'].__version__ if 'numpy' in sys.modules else None),helper=step1_engine.ckpt_persist.__file__)))   # adapted: the version is reported only when numpy was loaded (the fixed helper does not load it)"
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1');r=subprocess.run([sys.executable,'-S','-c',code],env=env,capture_output=True,text=True,check=True)
 v=json.loads(r.stdout);v['required_numpy']='2.1.3';v['isolated_startup']='-S skips environment sitecustomize; actual installed package directory added explicitly';record('pre_environment_import',v);assert not v['before']
 assert not v['after'],'new helper imports numpy in notebook cell2 before pins install in cell3'

def test_concurrent_publish_must_not_leave_dangling_latest(state,monkeypatch):
 # Reproduces two publishers after a join timeout; actual function under test.
 s=state;old=gen(s);real_replace=os.replace;original_time=cp.time.time;events={'A':threading.Event(),'B':threading.Event(),'doneA':threading.Event()}; errors=[];results={}
 def tnow():
  name=threading.current_thread().name
  return 1700000000.1 if name=='A' else 1700000000.2 if name=='B' else original_time()
 monkeypatch.setattr(cp.time,'time',tnow)
 def repl(src,dst):
  name=threading.current_thread().name
  if str(dst).endswith('/LATEST') and name in ['A','B']:
   events[name].set()
   if name=='A':
    assert events['B'].wait(3);ret=real_replace(src,dst);events['doneA'].set();return ret
   assert events['doneA'].wait(3)
  return real_replace(src,dst)
 monkeypatch.setattr(cp.os,'replace',repl)
 def worker():
  try:results[threading.current_thread().name]=str(gen(s))
  except Exception as ex:errors.append(repr(ex))
 a=threading.Thread(target=worker,name='A');b=threading.Thread(target=worker,name='B');a.start();assert events['A'].wait(3);b.start();a.join(5);b.join(5)
 assert not a.is_alive() and not b.is_alive()
 latest=cp.latest_generation(str(s['root']));record('concurrent_publish',dict(latest=latest,pointer=(s['root']/'LATEST').read_text(),errors=errors,results=results,previous_generation_retained=old.exists()))
 assert latest is not None,'two publishers raced on LATEST.part and latest pointed to the removed losing generation'
