"""Additional v0.2 boundary review. Synthetic arrays ONLY; real-run metadata
are read from the submitted immutable corpus. No Drive/network/full physical banks.
Expected failures express declared read-only / same-content / evidence contracts.
"""
from pathlib import Path
import os,sys,json,copy,shutil,hashlib,io,contextlib,importlib.util,types
import numpy as np
import pytest
PB=Path(os.environ.get('REVIEW_PB',Path(__file__).resolve().parents[1])).resolve()
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(PB),str(PB/'tests'),str(HERE)]
import test_audit_d2_verify_prior_adapted_chatgpt as h   # adapted module name
from step1_engine import d2_bank as db
import tempfile
E=Path(os.environ.get('EDGE_EVIDENCE',os.path.join(tempfile.gettempdir(),'d2_verify_edge_probes')))   # adapted
H=lambda b:hashlib.sha256(b).hexdigest()
def save(name,**r):
 E.mkdir(parents=True,exist_ok=True);(E/(name+'.json')).write_text(json.dumps(r,indent=2,default=str))
def loadscript():return h.load_script(PB)
def invoke(m,run,out,*extra):
 argv=sys.argv[:];buf=io.StringIO();err=io.StringIO();error=None
 try:
  sys.argv=['verify','--phaseb',str(PB),'--run-root',str(run),'--out',str(out),*map(str,extra)]
  with contextlib.redirect_stdout(buf),contextlib.redirect_stderr(err):rc=m.main()
 except Exception as x:rc=99;error=repr(x)
 finally:sys.argv=argv
 rep=None
 if out.is_dir():
  for f in out.glob('d2_verify_*.json'):
   if f.is_symlink():continue
   try:rep=json.loads(f.read_text())
   except Exception:pass
 return {'rc':rc,'report':rep,'stdout':buf.getvalue(),'stderr':err.getvalue(),'error':error}
@pytest.fixture(scope='session')
def base(tmp_path_factory):
 p=tmp_path_factory.mktemp('basefull')/'run';h.make_run(p,'E7',True);return p
@pytest.fixture
def full(tmp_path,base):
 p=tmp_path/'run';shutil.copytree(base,p);rg=json.loads((p/'d2/d2_bank_registry.json').read_text())
 for d in rg['directories'].values():d['path']=d['path'].replace(str(base),str(p))
 h.dump(p/'d2/d2_bank_registry.json',rg);h.update_final(p);return p

def test_external_mapped_bank_output_must_not_write_accepted_metadata_copy(tmp_path):
 run=tmp_path/'accepted_run';shutil.copytree(PB/'registered_assets/d2/E7',run)
 rg=json.loads((run/'d2/d2_bank_registry.json').read_text());old=rg['directories']['ref_E7_b0']['path'];store=tmp_path/'external_bank';store.mkdir();(store/'CANARY').write_bytes(b'protected input')
 out=store/'review_output';before=h.snap(store)
 r=invoke(loadscript(),run,out,'--mode','accepted','--path-map',old+'='+str(store))
 after=h.snap(store);save('accepted_external_output',result=r,changed=sorted(k for k in before if after.get(k)!=before[k]),added=sorted(after.keys()-before.keys()),original_metadata=True,npz_reads=0)
 assert before==after and not out.exists(),'output-overlap failure handler wrote into the bank it just declared protected'

def test_external_bank_output_must_not_write_test_cache(full,tmp_path):
 rg=json.loads((full/'d2/d2_bank_registry.json').read_text());name='ref_E7_b0';store=tmp_path/'external_bank';shutil.move(str(full/'d2'/name),store);rg['directories'][name]['path']=str(store);h.dump(full/'d2/d2_bank_registry.json',rg)
 before=h.snap(store);out=store/'review_output';r=invoke(loadscript(),full,out,'--mode','test');after=h.snap(store)
 save('test_external_output',result=r,added=sorted(after.keys()-before.keys()),arrays_unchanged=all(after.get(k)==v for k,v in before.items()))
 assert before==after,'output failure path modifies external protected bank tree'

def test_moved_run_path_map_preserves_original_inventory_identity(full,tmp_path):
 original=str(full);moved=tmp_path/'relocated';shutil.move(str(full),moved);before=h.snap(moved)
 r=invoke(loadscript(),moved,tmp_path/'verify','--mode','test','--path-map',original+'='+str(moved));q=r['report'] or {}
 save('moved_run',result=r,input_unchanged=h.snap(moved)==before,mode='TEST-ONLY all 39 units; original metadata and NPZ remain byte-identical')
 assert r['rc']==0 and q.get('all_ok') is True and h.snap(moved)==before,'a byte-identical relocated run fails because original file names are relativized to the new physical root'

def test_moved_bank_only_control_succeeds(full,tmp_path):
 name='cfg30101_w2';old=full/'d2'/name;new=tmp_path/'external_w2';shutil.move(str(old),new);before=h.snap(full)|{str(k):v for k,v in h.snap(new).items()}
 r=invoke(loadscript(),full,tmp_path/'verify','--mode','test','--path-map',str(old)+'='+str(new));save('moved_bank_control',result=r)
 assert r['rc']==0 and r['report']['all_ok']

@pytest.mark.parametrize('record',['d2/d2_bank_registry.json','d2_final_record.json'])
def test_accepted_json_same_bytes_must_be_hashed_and_decoded(tmp_path,monkeypatch,record):
 run=tmp_path/'accepted';shutil.copytree(PB/'registered_assets/d2/E7',run);p=run/record;good=p.read_bytes();bad=json.loads(good)
 # JSON initially read contains a wrong but harmless extra field; at hash time the
 # on-disk original is restored. This controls a real read/hash ordering window.
 bad['TEST_ONLY_UNAUTHENTICATED_MARKER']='not in the accepted bytes';p.write_text(json.dumps(bad,indent=1));m=loadscript();orig=m.sha;hits=[]
 def swapped(path):
  if Path(path)==p and not hits:p.write_bytes(good);hits.append(str(path))
  return orig(path)
 monkeypatch.setattr(m,'sha',swapped)
 r=invoke(m,run,tmp_path/'verify','--mode','accepted');save('json_capture_'+p.name,result=r,restored_before_hash=hits,npz_not_available=True)
 # Binding must not certify an object read before the authenticated bytes.
 assert (r['report'] or {}).get('accepted_run_binding') is not True,'hash verified new path bytes while accepting an older decoded record'

@pytest.mark.parametrize('limit',[1,39,40])
def test_partial_status_even_if_limit_covers_all(full,tmp_path,limit):
 r=invoke(loadscript(),full,tmp_path/'verify','--mode','test','--max-dirs',limit);q=r['report'];save('partial_'+str(limit),result=r)
 assert r['rc']==1 and q['coverage_complete'] is False and q['verification_scope']=='test_partial'
 assert len(q['checked_units'])==min(limit,39) and len(q['unchecked_units'])==max(39-limit,0)

@pytest.mark.parametrize('change',['empty','missing','wrong_family','failed_run','ledger_array_reference'])
def test_bound_original_metadata_rejects_changes_before_array_io(tmp_path,change):
 run=tmp_path/'accepted';shutil.copytree(PB/'registered_assets/d2/E7',run)
 if change=='failed_run':
  p=run/'d2/d2_run_manifest.json';r=json.loads(p.read_text());r['D2_PASS']=False;r['stage']='exception';r['failures']=['TEST ONLY'];h.dump(p,r)
 else:
  p=run/'d2/d2_bank_registry.json';r=json.loads(p.read_text())
  if change=='empty':r['directories']={}
  elif change=='missing':r['directories'].pop('cfg30101_w2')
  elif change=='wrong_family':r['family']='E8'
  else:r['directories']['cfg30101_b0']['manifest_sha256']='0'*64
  h.dump(p,r)
 r=invoke(loadscript(),run,tmp_path/'verify','--mode','accepted');save('accepted_reject_'+change,result=r)
 assert r['rc']==1 and r['report']['stage']=='binding' and 'units' not in r['report']

def test_unmodified_real_metadata_without_npz_is_not_success(tmp_path):
 run=tmp_path/'accepted';shutil.copytree(PB/'registered_assets/d2/E7',run)
 rg=json.loads((run/'d2/d2_bank_registry.json').read_text());orig=str(Path(rg['directories']['ref_E7_b0']['path']).parents[1])
 r=invoke(loadscript(),run,tmp_path/'verify','--mode','accepted','--path-map',orig+'='+str(run));q=r['report'];save('real_metadata_absent_npz',result=r)
 assert r['rc']==1 and q['accepted_run_binding'] is True and len(q['units'])==39 and all(not x['ok'] for x in q['units'].values())

def all_near_flips(a):
 a['model_matched__float64__T1'][:]=1000.;a['model_matched__float32__T1'][:]=1000.0005
 for sel,ax in [('float64',0),('float32',1)]:
  a['model_matched__'+sel+'__T2'][:]=100.;a['model_matched__'+sel+'__AX'][:]=ax;a['model_matched__'+sel+'__PL'][:]=ax

def test_full_flip_evidence_not_silently_capped(full,tmp_path):
 table,reg=h.load_crn_table(str(PB/'d/d2_crn_table.json'));spec=db.load_bank_spec(str(PB/'d/d2_bank_spec.json'),table=table);name='cfg30101_w2';p=full/'d2'/name;shutil.rmtree(p)
 man=db.generate_w2_position_bank(h._Kern(),reg,table,spec,30101,np.eye(21)*1.1,str(p),db.CallInventory(),scale=.0105,chunk_clusters=7)
 rg=json.loads((full/'d2/d2_bank_registry.json').read_text());rg['directories'][name]['manifest_sha256']=man['manifest_sha256'];h.dump(full/'d2/d2_bank_registry.json',rg);h.update_final(full);h.rebind_npz(full,name,all_near_flips)
 r=invoke(loadscript(),full,tmp_path/'verify','--mode','test');q=r['report']['f32_sensitivity'][name]['model_matched'];save('evidence_truncation',rc=r['rc'],all_ok=r['report']['all_ok'],gate=r['report']['f32_registered_gate'],flips=q['flips'],evidence_rows=len(q['flip_evidence']),truncated=q['evidence_truncated'])
 assert q['flips']==2100
 assert len(q['flip_evidence'])==2100 or q.get('full_flip_evidence_ref'),'registered per-flip evidence stops at row 2000 with no complete artifact'

def test_missing_axis_dependency_marks_incomplete_geometry(full,tmp_path,monkeypatch):
 h.rebind_npz(full,'cfg30101_w2',all_near_flips);monkeypatch.setitem(sys.modules,'healpy',None)
 r=invoke(loadscript(),full,tmp_path/'verify','--mode','test');g=r['report']['f32_registered_gate'];s=r['report']['f32_sensitivity']['cfg30101_w2']['model_matched'];save('missing_axis_dependency',gate=g,flips=s['flips'],first_evidence=s['flip_evidence'][0],all_ok=r['report']['all_ok'])
 assert 'plane_angle_deg' not in s['flip_evidence'][0]
 assert g.get('evidence_complete') is False or g.get('axis_geometry_status') in ('NOT_EVALUATED','UNAVAILABLE') or g['status']!='CANDIDATE_EVALUATED','candidate status lacks an explicit missing-geometry qualifier'

def test_failed_unit_not_registered_f32_candidate(full,tmp_path):
 h.rebind_npz(full,'cfg30101_w2',all_near_flips);rg=json.loads((full/'d2/d2_bank_registry.json').read_text());rg['directories']['cfg30101_w2']['manifest_sha256']='0'*64;h.dump(full/'d2/d2_bank_registry.json',rg)
 r=invoke(loadscript(),full,tmp_path/'verify','--mode','test');q=r['report'];save('failed_unit_candidate',rc=r['rc'],unit=q['units']['cfg30101_w2'],gate=q['f32_registered_gate'])
 assert r['rc']==1 and q['units']['cfg30101_w2']['ok'] is False
 assert ('cfg30101_w2' not in q['f32_sensitivity']) or q['f32_registered_gate'].get('integrity_complete') is False,'an integrity-failed unit still contributes a registered candidate without an integrity qualifier'

def test_notebook_execution_writes_stdout_stderr(tmp_path,monkeypatch):
 n=json.loads((PB/'d/MirrorTopology_Step1_D2_verify_v0.2.ipynb').read_text());cell=''.join(n['cells'][3]['source']);out=tmp_path/'launch';(out/'report').mkdir(parents=True)
 q={'schema':'d2_postrun_verification_v2','family':'E7','stage':'complete','all_ok':True,'coverage_complete':True,'accepted_run_binding':True,'f32_registered_gate':{'status':'CANDIDATE_EVALUATED','all_pairs_pass_registered_rule':True},'failures':[],'seconds':1.}
 h.dump(out/'report/d2_verify_E7.json',q)
 cp=types.SimpleNamespace(returncode=0,stdout='TEST-ONLY stdout evidence\n',stderr='TEST-ONLY stderr evidence\n')
 ns={'OUT':str(out),'FAMILY':'E7','SCRIPT':str(PB/'d/d2_verify_banks.py'),'PHASEB':str(PB),'RUN_ROOT':'TEST-ONLY','lock':{'test_only':True},'os':os,'sys':sys,'json':json,'subprocess':types.SimpleNamespace(run=lambda *a,**k:cp)}
 exec(compile(cell,'actual_verification_cell','exec'),ns)
 files={p.relative_to(out).as_posix():p.read_text() for p in out.rglob('*') if p.is_file()};save('notebook_logs',files=files,scope='exact cell, subprocess return only is TEST-ONLY')
 assert (out/'verify_stdout.txt').read_text()==cp.stdout and (out/'verify_stderr.txt').read_text()==cp.stderr,'stdout/stderr writes are inside an inline comment'
