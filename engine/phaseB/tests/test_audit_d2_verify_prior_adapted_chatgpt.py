"""Independent pre-execution review of d2_verify_banks.py.
All generated arrays are TEST-ONLY; no Drive access, no physical covariance
or official-bank regeneration. Uploaded records / source are left unchanged.
Tests intentionally specify the requested verification contracts, not merely
that the current implementation returns zero.
"""
from pathlib import Path
import os,sys,json,hashlib,copy,shutil,importlib.util,contextlib,io,subprocess
import numpy as np
import pytest
PB=Path(os.environ.get('REVIEW_PB',Path(__file__).resolve().parents[1])).resolve()
import tempfile
ART=Path(os.environ.get('REVIEW_EVIDENCE',os.path.join(tempfile.gettempdir(),'d2_verify_review_contracts')))   # adapted: evidence dir not shipped
sys.path[:0]=[str(PB),str(PB/'tests')]
from step1_engine import d2_bank as db
from step1_engine.d2_rng import load_crn_table
from test_d2_tranche2 import _Kern
H=lambda b:hashlib.sha256(b).hexdigest()
PROBES={}

def snap(root):
 return {p.relative_to(root).as_posix():H(p.read_bytes()) for p in root.rglob('*') if p.is_file()}

def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=1))

def load_script(pb=PB):
 s=importlib.util.spec_from_file_location('new_readonly_verifier',pb/'d/d2_verify_banks.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def call(run,out,extra=(),pb=PB):
 if '--mode' not in extra: extra=('--mode','test',*extra)
 m=load_script(pb);argv=sys.argv[:];buf=io.StringIO();rc=None;error=None
 try:
  sys.argv=['d2_verify_banks.py','--phaseb',str(pb),'--run-root',str(run),'--out',str(out),*map(str,extra)]
  with contextlib.redirect_stdout(buf):rc=m.main()
 except (Exception,SystemExit) as ex:rc=getattr(ex,'code',1);error=repr(ex)
 finally:sys.argv=argv
 reports=list(out.glob('d2_verify_*.json')) if out.is_dir() else []
 # Only genuine report JSON is interpreted, never a bank NPZ symlink.
 result=None
 for p in reports:
  try:
   q=json.loads(p.read_text())
   if isinstance(q,dict) and q.get('schema')=='d2_postrun_verification_v2':result=q
  except Exception:pass
 return dict(rc=rc,error=error,stdout=buf.getvalue(),report=result)

def record(name,r,**kw):
 PROBES[name]=dict(rc=r['rc'],error=r['error'],all_ok=(r['report'] or {}).get('all_ok'),directories=len((r['report'] or {}).get('directories',{})),failures=(r['report'] or {}).get('failures'),**kw)
 ART.mkdir(parents=True,exist_ok=True);(ART/(name+'.json')).write_text(json.dumps(r|kw,indent=1,default=str,allow_nan=True))

def inventory(run):
 return {p.relative_to(run).as_posix():dict(sha256=None if p.suffix=='.npz' else H(p.read_bytes()),bytes=p.stat().st_size) for p in run.rglob('*') if p.is_file() and p.name!='d2_final_record.json'}

def update_final(run):
 p=run/'d2_final_record.json';fr=json.loads(p.read_text());fr['output_inventory']=inventory(run);dump(p,fr)

def make_run(run,fam='E7',all_configs=False):
 table,reg=load_crn_table(str(PB/'d/d2_crn_table.json'));spec=db.load_bank_spec(str(PB/'d/d2_bank_spec.json'),table=table)
 ids=[int(k) for k,c in spec['configurations'].items() if c['family']==fam];ids=ids if all_configs else ids[:1]
 roots=dict(model_matched=np.eye(21)*1.1,model_native=np.eye(21)*.9,ref_native=np.eye(21)*1.2)
 ci=db.CallInventory();dirs={};k=_Kern();run.mkdir(parents=True)
 def add(name,m):dirs[name]=dict(path=str(run/'d2'/name),manifest_sha256=m['manifest_sha256'],purpose=m['purpose'],reused=False,seconds=0.)
 for cid in [None]+ids:
  nr='ref_'+fam if cid is None else 'cfg'+str(cid);rr={'ref_matched':np.eye(21)} if cid is None else roots
  for b in [0,1]:
   sels=spec['family_reference'][fam]['selections'][str(b)] if cid is None else spec['configurations'][str(cid)]['selections']['evaluation'][str(b)]
   name=nr+'_b'+str(b);add(name,db.generate_configuration_bank(k,reg,table,spec,cid,rr,b,str(run/'d2'/name),ci,sels,scale=.0002,chunk_clusters=2,family=fam))
  name=nr+'_fit';add(name,db.generate_fitting_bank(k,reg,table,spec,cid,rr,str(run/'d2'/name),ci,scale=.001,chunk_clusters=2,family=fam))
  if cid is not None and fam!='E1':
   name=nr+'_w2';add(name,db.generate_w2_position_bank(k,reg,table,spec,cid,roots['model_matched'],str(run/'d2'/name),ci,scale=.001,chunk_clusters=2))
 rg=dict(family=fam,engine_version='0.78.0',directories=dirs,configuration_ids=ids,formal=False,calls=ci.calls)
 dump(run/'d2/d2_bank_registry.json',rg);dump(run/'d2/d2_run_manifest.json',dict(family=fam,stage='complete',D2_PASS=False,directories=dirs,failures=[]))
 dump(run/'d2_final_record.json',dict(family=fam,D2_PASS=False,output_inventory=inventory(run),scope='TEST-ONLY SYNTHETIC ARRAYS, NOT AN ACCEPTED PRODUCTION RUN'))
 return rg

@pytest.fixture(scope='session',autouse=True)
def save_probes():
 yield
 ART.mkdir(parents=True,exist_ok=True);(ART/'summary.json').write_text(json.dumps(PROBES,indent=1,default=str))

@pytest.fixture
def small(tmp_path):
 run=tmp_path/'run';rg=make_run(run,all_configs=True);return run,rg

@pytest.mark.parametrize('fam',['E1','E2','E7','E8'])
def test_normal_all_family_units_readonly(tmp_path,fam):
 run=tmp_path/'run';rg=make_run(run,fam,True);before=snap(run);r=call(run,tmp_path/'verify');record('normal_'+fam,r,expected_units=len(rg['directories']),input_unchanged=snap(run)==before)
 assert r['rc']==0 and r['report']['all_ok'] is True and set(r['report']['units'])==set(rg['directories']) and before==snap(run)

@pytest.mark.parametrize('change',['array_bytes','missing_npz','stale_registry_manifest'])
def test_existing_corruption_rejected(small,tmp_path,change):
 run,rg=small;name='cfg30101_b1';mp=run/'d2'/name/'COMPLETE.json';m=json.loads(mp.read_text());p=mp.parent/m['shards'][-1]['file']
 if change=='array_bytes':
  with np.load(p,allow_pickle=False) as z:a={k:z[k] for k in z.files}
  a['model_native__float64__T2'][0]+=1e-7;np.savez(p,**a)
 elif change=='missing_npz':p.unlink()
 else:rg['directories'][name]['manifest_sha256']='0'*64;dump(run/'d2/d2_bank_registry.json',rg)
 before=snap(run);r=call(run,tmp_path/'verify');record('old_reject_'+change,r,input_unchanged=snap(run)==before)
 assert r['rc']==1 and r['report']['failures']==[name] and before==snap(run)

def test_empty_registry_cannot_certify_real_E7_run(tmp_path):
 # Actual supplied/registered run metadata, only the local registry directory map is emptied.
 src=PB/'registered_assets/d2/E7';run=tmp_path/'run';shutil.copytree(src,run)
 p=run/'d2/d2_bank_registry.json';rg=json.loads(p.read_text());rg['directories']={};dump(p,rg)
 r=call(run,tmp_path/'verify',['--mode','accepted']);record('empty_real_E7',r,actual_registered_units=39,actual_npz_reads=0,registered_snapshot_unchanged=True)
 assert r['rc']!=0 and not (r['report'] or {}).get('all_ok',False),'zero directories passed as all_ok for a registered 39-unit run'

@pytest.mark.parametrize('change',['omit_directory','wrong_family','failed_run_record','wrong_expected_size'])
def test_scope_and_record_link_must_be_checked(small,tmp_path,change):
 run,rg=small
 if change=='omit_directory':rg['directories'].pop('cfg30101_w2');dump(run/'d2/d2_bank_registry.json',rg)
 elif change=='wrong_family':rg['family']='E8';dump(run/'d2/d2_bank_registry.json',rg)
 elif change=='failed_run_record':
  p=run/'d2/d2_run_manifest.json';rm=json.loads(p.read_text());rm['stage']='exception';rm['failures']=['TEST-ONLY interrupted'];dump(p,rm)
 else:
  fr=json.loads((run/'d2_final_record.json').read_text());n=next(n for n in fr['output_inventory'] if n.endswith('.npz'));fr['output_inventory'][n]['bytes']+=1;dump(run/'d2_final_record.json',fr)
 r=call(run,tmp_path/'verify', ['--mode','accepted'] if change=='failed_run_record' else []);record('scope_'+change,r)
 assert r['rc']!=0 and not (r['report'] or {}).get('all_ok',False),'inconsistent run/registry/family scope accepted'

@pytest.mark.parametrize('limit',['1','-1'])
def test_limited_scan_is_not_unqualified_full_success(small,tmp_path,limit):
 run,rg=small;p=run/'d2/cfg30101_w2/cfg30101_w2_s0.npz';p.unlink()
 r=call(run,tmp_path/'verify',['--max-dirs',limit]);record('limit_'+limit,r,requested=len(rg['directories']))
 report=r['report'] or {};explicit_partial=(report.get('coverage_complete') is False and report.get('verification_scope') in ('partial','test') and report.get('full_bank_pass') is not True)
 assert r['rc']!=0 or explicit_partial,'skipping a missing required bank gives an unqualified all_ok with no partial coverage status'

@pytest.mark.parametrize('where',['run_root','bank_subdir','symlink_output_file'])
def test_output_cannot_modify_bank_tree(small,tmp_path,where):
 run,rg=small;victim=run/'d2/cfg30101_b0/cfg30101_b0_s0.npz';out=tmp_path/'verify'
 if where=='run_root':out=run
 elif where=='bank_subdir':out=run/'d2/cfg30101_b0'
 else:out.mkdir();(out/'d2_verify_E7.json').symlink_to(victim)
 before=snap(run);r=call(run,out);after=snap(run)
 record('readonly_'+where,r,changed=[n for n in before if after.get(n)!=before[n]],added=sorted(after.keys()-before.keys()))
 assert before==after and r['rc']!=0,'the read-only checker wrote inside its bank input / followed an output symlink into NPZ'

# Rebinding below is confined to synthetic fixture copies. It isolates a content
# check after checksums have been made self-consistent; it does not defeat the
# fixed SHA of any accepted real-bank record.
def rebind_npz(run,name,edit):
 d=run/'d2'/name;mp=d/'COMPLETE.json';m=json.loads(mp.read_text());sh=m['shards'][0];p=d/sh['file'];sp=d/sh['sidecar']
 with np.load(p,allow_pickle=False) as z:a={k:z[k].copy() for k in z.files}
 edit(a);np.savez(p,**a);s=json.loads(sp.read_text());s['array_sha256']={k:H(np.ascontiguousarray(v).tobytes()) for k,v in a.items()};s['file_sha256']=H(p.read_bytes());s['bytes']=p.stat().st_size;dump(sp,s)
 sh['file_sha256']=s['file_sha256'];sh['sidecar_sha256']=H(sp.read_bytes());m['manifest_sha256']=db._sha(json.dumps({k:v for k,v in m.items() if k!='manifest_sha256'},sort_keys=True).encode());dump(mp,m)
 rg=json.loads((run/'d2/d2_bank_registry.json').read_text());rg['directories'][name]['manifest_sha256']=m['manifest_sha256'];dump(run/'d2/d2_bank_registry.json',rg);update_final(run)
 assert db.verify_bank_dir(str(d))['manifest_sha256']==m['manifest_sha256']
 return a

@pytest.mark.parametrize('change',['coherent_data_change','producer_change'])
def test_fixed_accepted_record_binding_is_not_replaced_by_local_self_consistency(small,tmp_path,change):
 run,rg=small
 if change=='coherent_data_change':rebind_npz(run,'cfg30101_b0',lambda a:a['model_matched__float64__T1'].__setitem__(0,a['model_matched__float64__T1'][0]+123))
 else:
  d=run/'d2/cfg30101_b0';mp=d/'COMPLETE.json';m=json.loads(mp.read_text());sh=m['shards'][0];sp=d/sh['sidecar'];s=json.loads(sp.read_text());s['producer']={'source':{'modules':{'d2_rng.py':'0'*64}},'profile':{'selftest':True}};dump(sp,s);sh['sidecar_sha256']=H(sp.read_bytes());m['manifest_sha256']=db._sha(json.dumps({k:v for k,v in m.items() if k!='manifest_sha256'},sort_keys=True).encode());dump(mp,m);rg['directories']['cfg30101_b0']['manifest_sha256']=m['manifest_sha256'];dump(run/'d2/d2_bank_registry.json',rg);update_final(run)
 r=call(run,tmp_path/'verify',['--mode','accepted']);record('unbound_'+change,r,scope='TEST-ONLY self-consistent local replacement; no trusted production SHA was bypassed')
 # A diagnostic small run may be accepted, but must never be indistinguishable
 # from an authenticated formal-bank verification.
 q=r['report'] or {};explicit=q.get('accepted_run_binding') is False and q.get('verification_scope') in ('test','unbound_diagnostic')
 assert r['rc']!=0 or explicit,'no trusted-run binding status / unbound diagnostic distinction'

@pytest.mark.parametrize('case', ['relative_small_absolute_large','relative_large_absolute_small'])
def test_near_tie_uses_registered_relative_scale(small,tmp_path,case):
 run,rg=small;name='cfg30101_b0';base,delta=(1000.,.0005) if case=='relative_small_absolute_large' else (.01,.0000005)
 def edit(a):
  for role in ('model_matched','model_native','ref_native'):
   for sel in ('float64','float32'):
    a[f'{role}__{sel}__T1'][:]=base+(delta if sel=='float32' else 0);a[f'{role}__{sel}__T2'][:]=200.;a[f'{role}__{sel}__AX'][:]=(1 if sel=='float32' else 0)
 rebind_npz(run,name,edit);r=call(run,tmp_path/'verify');s=(r['report'] or {}).get('f32_sensitivity',{}).get(name,{}).get('model_matched',{});expected=200 if delta/base<1e-6 else 0
 record('tie_'+case,r,base=base,delta=delta,registered_relative=delta/base,expected_near_tie_count=expected,reported=s)
 assert s.get('near_tie_flips_rel_lt_1e6')==expected,'absolute epsilon proxy disagrees with the registered relative selected-S+ rule'

def test_event_B_mismatch_record_not_omitted(small,tmp_path):
 run,rg=small;name='cfg30101_b0';t1=39.67178834527284;t2=259.3375006282747
 def edit(a):
  for sel,sign in [('float64',-1),('float32',1)]:
   a['model_matched__'+sel+'__T1'][:]=t1+sign*1e-8;a['model_matched__'+sel+'__T2'][:]=t2-1;a['model_matched__'+sel+'__AX'][:]=(0 if sel=='float64' else 1)
 a=rebind_npz(run,name,edit);rate=float(np.mean(((a['model_matched__float64__T1']<=t1)&(a['model_matched__float64__T2']<=t2))!=((a['model_matched__float32__T1']<=t1)&(a['model_matched__float32__T2']<=t2))))
 r=call(run,tmp_path/'verify');s=r['report']['f32_sensitivity'][name]['model_matched'];record('event_B',r,independent_mismatch_rate=rate,thresholds=[t1,t2],reported=s)
 assert s.get('event_B_mismatch_rate')==rate,'required Event B mismatch rate is not evaluated or recorded'

@pytest.mark.parametrize('bad',['-1','nan','inf'])
def test_invalid_near_tie_parameter_fails_early(small,tmp_path,bad):
 run,_=small;r=call(run,tmp_path/'verify',['--near-tie-eps',bad]);record('epsilon_'+bad,r)
 assert r['rc']!=0,'invalid threshold accepted'

def test_reference_and_config_cid_groups_are_actually_compared(small,tmp_path):
 run,rg=small;t,R=load_crn_table(str(PB/'d/d2_crn_table.json'));s=db.load_bank_spec(str(PB/'d/d2_bank_spec.json'));name='ref_E7_b0';d=run/'d2'/name;shutil.rmtree(d)
 m=db.generate_configuration_bank(_Kern(),R,t,s,None,{'ref_matched':np.eye(21)},0,str(d),db.CallInventory(),('float64','float32'),scale=.0004,chunk_clusters=2,family='E7');rg['directories'][name]['manifest_sha256']=m['manifest_sha256'];dump(run/'d2/d2_bank_registry.json',rg);update_final(run)
 r=call(run,tmp_path/'verify');record('cid_crossgroups',r,reference_rows=400,configuration_rows=200,reported=(r['report'] or {}).get('same_latent_cid'))
 assert r['rc']!=0 or (r['report'] or {}).get('cid_pairing_ok') is False,'reference and configuration cid hashes are grouped separately, never compared'

def test_verifier_source_inventory_checked_not_just_bank_engine_label(small,tmp_path):
 run,_=small;pb2=tmp_path/'pb2';shutil.copytree(PB,pb2);p=pb2/'step1_engine/d2_bank.py';p.write_bytes(p.read_bytes()+b'\n# TEST-ONLY source identity probe; no numerical changes.\n')
 out=tmp_path/'verify';env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1');cmd=[sys.executable,str(pb2/'d/d2_verify_banks.py'),'--phaseb',str(pb2),'--run-root',str(run),'--out',str(out)];p=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=45);q=json.loads((out/'d2_verify_E7.json').read_text()) if (out/'d2_verify_E7.json').exists() else None;r=dict(rc=p.returncode,error=None,stdout=p.stdout,report=q);record('source_inventory',r,actual_verifier_version='0.79.0',reported_engine=(q or {}).get('engine'))
 assert r['rc']!=0,'changed verifier module bytes passed despite unchanged expected inventory'
