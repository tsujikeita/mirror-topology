"""Bounded review of D2 tranche3b v2. No Colab / Drive / physical bank / OT.
All array values use the prior TEST-ONLY kernel. Source-identity experiment uses
an explicitly altered temporary checkout in a separate process; received files
are never edited. Reuse and gate logic are the submitted real script.
"""
from pathlib import Path
import os,sys,json,copy,hashlib,subprocess,shutil,io
import numpy as np
import pytest
import test_audit_d2_tranche3b_review_chatgpt as prior   # adapted: the prior review module is the bundled tranche-3b review test
from test_audit_d2_tranche3b_review_chatgpt import context,wbank,reuse_cache
PB=prior.PB;db=prior.db
PROBES={}
HASH=lambda b:hashlib.sha256(b).hexdigest()
@pytest.fixture(scope='session',autouse=True)
def save_new_probes():
 yield
 import tempfile; p=Path(os.environ.get('NEW_PROBES',os.path.join(tempfile.gettempdir(),'t3bv2_review_probes.json')));p.parent.mkdir(parents=True,exist_ok=True)   # adapted
 p.write_text(json.dumps(PROBES,indent=2,default=str,allow_nan=False))

def test_registered_whitening_returns_independent_snapshot(context):
 a=db.registered_whitening(); b=db.registered_whitening(); mu=b['mu'].copy(); W=b['W'].copy(); ident=copy.deepcopy(db.SHARED_NULL)
 a['mu'][:]=0;a['W'][:]=0;a['identity']['asset_sha256']='0'*64
 c=db.registered_whitening()
 assert np.array_equal(c['mu'],mu) and np.array_equal(c['W'],W) and c['identity']==ident==db.SHARED_NULL
 assert c['mu_sha256']==HASH(mu.tobytes()) and c['W_sha256']==HASH(W.tobytes())

@pytest.mark.parametrize('case',['mu_bool','mu_string','mu_nan','mu_shape','W_bool','W_object','W_inf','W_shape'])
def test_whitening_invalid_inputs_rejected_before_consuming_arrays(wbank,monkeypatch,case):
 c=wbank;mu=c['mu'].copy();W=c['W'].copy();calls=[];old=db._load_role
 def consumed(*a,**k):calls.append(1);return old(*a,**k)
 monkeypatch.setattr(db,'_load_role',consumed)
 if case=='mu_bool':mu=np.zeros(2,dtype=bool)
 elif case=='mu_string':mu=mu.astype(str)
 elif case=='mu_nan':mu[0]=np.nan
 elif case=='mu_shape':mu=mu.reshape(1,2)
 elif case=='W_bool':W=np.ones((2,2),dtype=bool)
 elif case=='W_object':W=W.astype(object)
 elif case=='W_inf':W[0,0]=np.inf
 else:W=W.ravel()
 with pytest.raises(prior.InputContractError):db.intake_w2_position_bank(30101,str(c['dir']),c['S'],mu,W,dict(db.SHARED_NULL),formal=False)
 assert calls==[]


def test_whitening_uses_registered_snapshot_after_argument_validation(wbank,monkeypatch):
 c=wbank;mu=c['mu'].copy();W=c['W'].copy();old=db._load_role
 def consume(*a,**k):
  mu[:]=0;W[:]=0
  return old(*a,**k)
 monkeypatch.setattr(db,'_load_role',consume)
 b64,b32,info=db.intake_w2_position_bank(30101,str(c['dir']),c['S'],mu,W,dict(db.SHARED_NULL),formal=False)
 with np.load(c['dir']/c['manifest']['shards'][0]['file'],allow_pickle=False) as z:
  exp=(np.c_[z['model_matched__float64__T1'],z['model_matched__float64__T2']]-c['mu'])@c['W'].T
 assert np.array_equal(exp,b64.Tw)

@pytest.mark.parametrize('family,n',[('E1',12),('E2',39),('E7',39),('E8',39)])
def test_full_family_synthetic_normal_ledger(tmp_path,monkeypatch,family,n):
 rc,r,g,out=prior.run_script(tmp_path,monkeypatch,family=family,configs=None)
 assert r['stage']=='complete' and r['D2_PASS'] is False and len(g['directories'])==n
 assert len(g['ledger'])==len(g['calls'])==n and g['calls_reused']=={}
 assert set(g['required_requests'])==set(g['directories'])=={v['name'] for v in g['ledger']}
 assert all(x['satisfied_by']=='new_generation' for x in g['ledger'])
 PROBES['normal_'+family]={'directories':n,'new_calls':len(g['calls']),'scope':'synthetic small scale; no physical statistics evaluated'}


def test_mixed_reuse_and_new_generation_ledger(tmp_path,monkeypatch,reuse_cache):
 local=tmp_path/'old';shutil.copytree(reuse_cache,local);shutil.rmtree(local/'cfg30101_w2')
 rc,r,g,out=prior.run_script(tmp_path,monkeypatch,reuse=local)
 assert r['stage']=='complete' and len(g['calls'])==1 and len(g['calls_reused'])==6
 assert sum(e['satisfied_by']=='new_generation' for e in g['ledger'])==1
 assert sum(e['satisfied_by']=='verified_reuse' for e in g['ledger'])==6
 for n,v in r['directories'].items():
  if v['reused']:
   assert v['calls_source']==json.loads((local/n/'COMPLETE.json').read_text())['calls']


def test_completed_units_from_interrupted_attempt_remain_reusable(tmp_path,monkeypatch):
 first=tmp_path/'first';second=tmp_path/'second';write=db._atomic_write
 def fail(p,b):
  if 'cfg30101_w2' in str(p) and str(p).endswith('.sidecar.json'):raise OSError('TEST-ONLY interrupted write')
  return write(p,b)
 with monkeypatch.context() as m:
  m.setattr(db,'_atomic_write',fail)
  rc,r,g,out=prior.run_script(first,m)
 assert r['stage']=='exception' and len(r['directories'])==6
 assert not (out/'cfg30101_w2/COMPLETE.json').exists()
 with monkeypatch.context() as m:rc2,r2,g2,out2=prior.run_script(second,m,reuse=out)
 assert r2['stage']=='complete' and len(g2['calls'])==1 and len(g2['calls_reused'])==6
 PROBES['partial_then_reuse']={'first_completed_units':6,'second_new':1,'second_reused':6}


def test_complete_reuse_export_has_all_verified_dependency_metadata(tmp_path,monkeypatch,reuse_cache):
 rc,r,g,out=prior.run_script(tmp_path,monkeypatch,reuse=reuse_cache)
 assert r['stage']=='complete' and len(g['calls'])==0 and len(g['calls_reused'])==7
 count=0
 for name,x in r['directories'].items():
  src=Path(x['path']);dest=Path(x['dependency_metadata']);m=db.verify_bank_dir(str(src))
  for f in ['COMPLETE.json']+[s['sidecar'] for s in m['shards']]:
   assert (src/f).read_bytes()==(dest/f).read_bytes();count+=1
  for s in m['shards']:assert HASH((dest/s['sidecar']).read_bytes())==s['sidecar_sha256']
 assert count==18
 nbout=tmp_path/'nbout';nbout.mkdir();shutil.copytree(out,nbout/'d2')
 ns,names=prior.run_notebook_final(nbout,r,rc,tmp_path,monkeypatch)
 assert sum(n.endswith('COMPLETE.json') for n in names)==7
 assert sum(n.endswith('.sidecar.json') for n in names)==11
 assert not any(n.endswith('.npz') for n in names)
 PROBES['complete_metadata_export']={'copied_verified_files':count,'complete':7,'sidecars':11,'npz_in_zip':0}

@pytest.mark.parametrize('which',['COMPLETE.json','ref_b0_s0.npz.sidecar.json'])
def test_dependency_metadata_captured_after_validation_must_be_verified(tmp_path,monkeypatch,reuse_cache,which):
 local=tmp_path/'old';shutil.copytree(reuse_cache,local)
 target=local/'ref_E7_b0'/which;original=target.read_bytes();verify=db.verify_bank_dir;changed=[]
 def change_after_real_validation(path,*args,**kwargs):
  result=verify(path,*args,**kwargs)
  if Path(path).resolve()==(local/'ref_E7_b0').resolve() and not changed:
   obj=json.loads(target.read_text());obj['n_rows' if which=='COMPLETE.json' else 'm']=-123
   target.write_text(json.dumps(obj,indent=1));changed.append(str(target))
  return result
 monkeypatch.setattr(db,'verify_bank_dir',change_after_real_validation)
 rc,r,g,out=prior.run_script(tmp_path,monkeypatch,reuse=local)
 dest=out/'audit_dependencies/ref_E7_b0'/which
 copied=json.loads(dest.read_text()) if dest.is_file() else None
 PROBES['metadata_race_'+which]={'changed':changed,'stage':r['stage'],'D2_PASS':r['D2_PASS'],'ledger_len':len(g.get('ledger',[])),'copied_changed_value':None if copied is None else copied.get('n_rows' if which=='COMPLETE.json' else 'm'),'verified_original_sha256':HASH(original),'copied_sha256':HASH(dest.read_bytes()) if dest.is_file() else None}
 assert changed
 # A reader may reject the new bytes OR export the correctly captured snapshot.
 # Requiring every mutation to raise would wrongly reject the snapshot solution.
 if r['stage']=='complete':
  assert copied==json.loads(original),'unverified changed metadata exported under the old verified manifest identity'
  if which!='COMPLETE.json':assert HASH(dest.read_bytes())==HASH(original)


def test_fixed_a10_mutation_rejected_before_generate(tmp_path,monkeypatch,reuse_cache):
 cp=tmp_path/'phaseB';shutil.copytree(PB,cp);ref=cp/'tests/reference_assets/a10a_calibration_official.npz'
 b=bytearray(ref.read_bytes());b[-1]^=1;ref.write_bytes(b)
 before=len(prior.ScriptKernel.instances)
 rc,r,g,out=prior.run_script(tmp_path,monkeypatch,official=True,family='E1',reuse=reuse_cache,phaseb=cp)
 assert r['stage']=='a10_reference_identity' and not r['directories']
 assert sum(k.generations for k in prior.ScriptKernel.instances[before:])==0


def test_a10_consumes_same_verified_bytes_after_path_replacement(tmp_path,monkeypatch,reuse_cache):
 cp=tmp_path/'phaseB';shutil.copytree(PB,cp);ref=cp/'tests/reference_assets/a10a_calibration_official.npz'
 original=ref.read_bytes();old=prior.ScriptKernel.generate;did=[]
 def altered_path_after_capture(self,*a,**k):
  ref.write_bytes(b'REPLACED_AFTER_CAPTURE');did.append(1);return old(self,*a,**k)
 monkeypatch.setattr(prior.ScriptKernel,'generate',altered_path_after_capture)
 rc,r,g,out=prior.run_script(tmp_path,monkeypatch,official=True,family='E1',reuse=reuse_cache,phaseb=cp)
 assert did and r['gates']['G_calibration_bank_matches_a10'] is True
 assert r['a10_reference_sha256']==HASH(original)
 assert r['D2_PASS'] is False # later small cache properly rejected; no full-size generation


def test_reuse_different_exact_source_same_engine_version_is_rejected(tmp_path,monkeypatch):
 """A real alternate checkout builds the small cache in a separate process.
 Only the test copy of d2_rng changes T1 *=1.125; its local inventory is updated
 to describe that different source (not to claim approval). The current checkout
 and its source inventory, version, spec, RNG table, and roots stay untouched.
 External runtime/physical inputs remain prior's explicitly synthetic stand-ins.
 """
 alt=tmp_path/'alternate_phaseB';shutil.copytree(PB,alt)
 source=alt/'step1_engine/d2_rng.py';s=source.read_text()
 old='for kk in ("T1", "T2", "AX", "PL"): out[(r, s)][kk][sl] = d[kk]'
 new='for kk in ("T1", "T2", "AX", "PL"): out[(r, s)][kk][sl] = d[kk] * 1.125 if kk == "T1" else d[kk]'
 assert s.count(old)==1;source.write_text(s.replace(old,new))
 ip=alt/'B2_completion_inventory.json';inv=json.loads(ip.read_text());inv['modules']['d2_rng.py']=HASH(source.read_bytes());ip.write_text(json.dumps(inv,indent=1))
 helper=Path(prior.__file__).resolve().parent
 code="""import sys,json,pytest;from pathlib import Path
import test_audit_d2_tranche3b_review_chatgpt as p
work,result=Path(sys.argv[1]),Path(sys.argv[2])
with pytest.MonkeyPatch.context() as m:
 rc,r,g,out=p.run_script(work,m)
 result.write_text(json.dumps({'rc':rc,'record':r,'registry':g,'out':str(out)},indent=1))
"""
 ee=dict(os.environ,REVIEW_PB=str(alt),PYTHONPATH=os.pathsep.join([str(helper),str(alt),str(alt/'tests')]))
 res=tmp_path/'alternate_record.json';log=tmp_path/'alternate_process.log'
 with log.open('w') as f:proc=subprocess.run([sys.executable,'-c',code,str(tmp_path/'alternate_run'),str(res)],env=ee,stdout=f,stderr=subprocess.STDOUT,timeout=90)
 assert proc.returncode==0,log.read_text();a=json.loads(res.read_text());assert a['record']['stage']=='complete' and a['record']['gates']['G_engine_inventory'] is True
 # A baseline from the unchanged submitted code, then reuse the alternate cache.
 with monkeypatch.context() as m:rc0,r0,g0,out0=prior.run_script(tmp_path/'baseline',m)
 with monkeypatch.context() as m:rc,r,g,out=prior.run_script(tmp_path/'consumer',m,reuse=Path(a['out']))
 basepath=out0/'cfg30101_b0';altpath=Path(a['out'])/'cfg30101_b0'
 bm=db.verify_bank_dir(str(basepath));am=db.verify_bank_dir(str(altpath))
 with np.load(basepath/bm['shards'][0]['file'],allow_pickle=False) as z:x=z['model_matched__float64__T1'].copy()
 with np.load(altpath/am['shards'][0]['file'],allow_pickle=False) as z:y=z['model_matched__float64__T1'].copy()
 assert np.array_equal(y,x*1.125) and not np.array_equal(x,y)
 PROBES['source_mismatch']={'current_inventory_sha':HASH((PB/'B2_completion_inventory.json').read_bytes()),'producer_inventory_sha':HASH(ip.read_bytes()),'current_d2_rng_sha':HASH((PB/'step1_engine/d2_rng.py').read_bytes()),'producer_d2_rng_sha':HASH(source.read_bytes()),'both_engine_versions':inv['engine_version'],'producer_preflight_source_ok':a['record']['gates']['G_engine_inventory'],'consumer_stage':r['stage'],'consumer_D2_PASS':r['D2_PASS'],'new_calls':len(g.get('calls',[])),'reused':sum(v.get('reused') is True for v in r['directories'].values()),'T1_alternate_to_baseline_factor':1.125,'T1_first_baseline':float(x[0]),'T1_first_alternate':float(y[0]),'same_environment_declared':g0['environment']==a['registry']['environment'],'source_fingerprint_present_in_cache':any('source' in k or 'inventory' in k for k in am),'scope':'two separate real source copies; synthetic external gate inputs; neither physical nor formal run'}
 assert r['stage']!='complete','different exact producer source accepted because engine version alone matches'
