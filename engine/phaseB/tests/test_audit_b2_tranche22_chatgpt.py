"""Tranche22 audit: formal runner's execution boundary and checkpoint gate replay.
Synthetic production-supplied bank only; no official numerical run, no OT.
Restore tests deliberately use the new bytes' TRUE SHA: they test semantic
contradictions, not cryptographic authenticity or a claimed hash collision.
"""
import os,sys,copy,hashlib
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_b2_tranche21 import build_pair
import step1_engine.formal_runner as fr
import step1_engine.orchestrator as orch
from step1_engine.checkpoint import read_family_result,write_family_result
from step1_engine.errors import InputContractError
from step1_engine import serialization as ser

@pytest.fixture(scope='module')
def records(tmp_path_factory):
 d=tmp_path_factory.mktemp('formal_baseline');_,_,fm,fn,*_=build_pair()
 r=fr.run_family_formal(fm,fn,80.,400.,'smoke',str(d/'normal.json'))
 return fm,fn,r,ser.loads((d/'normal.json').read_text())

def reread(payload,tmp_path):
 body=ser.dumps(payload).encode();p=tmp_path/'copy.json';p.write_bytes(body)
 return read_family_result(str(p),hashlib.sha256(body).hexdigest())

def test_normal_smoke_roundtrip(records,tmp_path):
 fm,fn,r,p=records;x=reread(p,tmp_path)
 assert x['result']['Q_point']==r.Q_point
 assert x['result']['evidence']['gate']['input_fingerprint']==dict(matched=fr.input_fingerprint(fm),native=fr.input_fingerprint(fn))
 assert x['result']['evidence']['gate']['record']['passed'] is True

def test_no_checkpoint_is_valid(records):
 fm,fn,*_=records;r=fr.run_family_formal(fm,fn,80.,400.,'smoke')
 assert r.evidence['gate']['mode']=='smoke'

def test_legacy_without_gate_stays_core_only(records,tmp_path):
 _,_,r,_=records;r=copy.deepcopy(r);r.evidence.pop('gate');r.notes=[]
 p=str(tmp_path/'legacy.json');h=write_family_result(r,p);x=read_family_result(p,h)
 assert x['result']['evidence'].get('gate') is None

@pytest.mark.parametrize('mutation',['fit_plan_id','fit_key_wave','evaluation_strata','multiplicity_dtype','T_shape'])
def test_fingerprint_covers_claimed_inputs(records,mutation):
 fm,_,*_=records;f=copy.deepcopy(fm);before=fr.input_fingerprint(f)
 if mutation=='fit_plan_id':f.fit_plans[0].plan_id+='-other'
 elif mutation=='fit_key_wave':
  for p in f.fit_plans.values():p.wave_id+=1;p.rng_key[1]=p.wave_id
 elif mutation=='evaluation_strata':f.plans[0].strata[0].reverse()
 elif mutation=='multiplicity_dtype':f.plans[0].multiplicities[0]=f.plans[0].multiplicities[0].astype(np.int32)
 elif mutation=='T_shape':f.configs[0].T1_model=f.configs[0].T1_model.reshape(-1,1)
 assert fr.input_fingerprint(f)!=before, 'a claimed input changed but the fingerprint did not'

@pytest.mark.parametrize('mutation',['T_value','fit_key_wave'])
def test_inrun_mutation_is_rejected(monkeypatch,mutation):
 _,_,fm,fn,*_=build_pair();orig=fr.evaluate_family_staged
 def changing(a,b,*args,**kw):
  if mutation=='T_value':a.configs[0].T1_model[0]+=1.
  else:
   for p in a.fit_plans.values():p.wave_id+=1;p.rng_key[1]=p.wave_id
  return orig(a,b,*args,**kw)
 monkeypatch.setattr(fr,'evaluate_family_staged',changing)
 with pytest.raises(InputContractError):fr.run_family_formal(fm,fn,80.,400.,'smoke')

@pytest.mark.parametrize('mutation',[
 'required_false','empty_checks','missing_check','missing_diagnostics','missing_gate',
 'bad_fingerprint','missing_native_fingerprint','extra_mode','two_modes','all_modes',
 'passed_false','passed_integer','required_modes_changed'])
def test_gate_content_not_just_passed_summary(records,tmp_path,mutation):
 d=copy.deepcopy(records[3]);g=d['result']['evidence']['gate'];rec=g['record'];checks=rec['diagnostics']['checks']
 if mutation=='required_false':next(x for x in checks if x['code']=='system_conditioning')['passed']=False
 elif mutation=='empty_checks':rec['diagnostics']['checks']=[]
 elif mutation=='missing_check':rec['diagnostics']['checks']=[x for x in checks if x['code']!='system_conditioning']
 elif mutation=='missing_diagnostics':rec.pop('diagnostics')
 elif mutation=='missing_gate':d['result']['evidence'].pop('gate')
 elif mutation=='bad_fingerprint':g['input_fingerprint']['matched']='not-a-sha'
 elif mutation=='missing_native_fingerprint':g['input_fingerprint'].pop('native')
 elif mutation=='extra_mode':d['extra']['mode']='official'
 elif mutation=='two_modes':g['mode']=rec['mode']='official'
 elif mutation=='all_modes':g['mode']=rec['mode']=d['extra']['mode']='official'
 elif mutation=='passed_false':rec['passed']=False
 elif mutation=='passed_integer':rec['passed']=1
 elif mutation=='required_modes_changed':next(x for x in checks if x['code']=='system_conditioning')['required_modes']=[]
 with pytest.raises(InputContractError):reread(d,tmp_path)

@pytest.fixture
def failed_record(monkeypatch,tmp_path):
 _,_,fm,fn,*_=build_pair();orig=orch._stage_selection
 def failed(f,t1,t2):
  x=orig(f,t1,t2)
  if f is fm:x['technical']=True
  return x
 monkeypatch.setattr(orch,'_stage_selection',failed)
 r=fr.run_family_formal(fm,fn,80.,400.,'smoke',str(tmp_path/'failed.json'))
 return r,ser.loads((tmp_path/'failed.json').read_text())

def test_actual_technical_failure_with_passed_preflight_is_saved(failed_record,tmp_path):
 _,d=failed_record;x=reread(d,tmp_path)
 assert x['result']['truths']['support']=='technical_fail'
 assert x['result']['evidence']['gate']['record']['passed'] is True

@pytest.mark.parametrize('mutation',['passed_false','mode_mismatch','missing_gate'])
def test_failed_result_does_not_skip_gate_validation(failed_record,tmp_path,mutation):
 _,d=failed_record;d=copy.deepcopy(d);g=d['result']['evidence']['gate']
 if mutation=='passed_false':g['record']['passed']=False;g['record']['required_failures']=['injected failure']
 elif mutation=='mode_mismatch':g['mode']='official'
 else:d['result']['evidence'].pop('gate')
 with pytest.raises(InputContractError):reread(d,tmp_path)

def test_writer_does_not_issue_passed_formal_provenance_for_failed_gate(records,tmp_path):
 r=copy.deepcopy(records[2]);r.evidence['gate']['record']['passed']=False
 with pytest.raises(InputContractError):write_family_result(r,str(tmp_path/'bad.json'),extra={'mode':'smoke'})
