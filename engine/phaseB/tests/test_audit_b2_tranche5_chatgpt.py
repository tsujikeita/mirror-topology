"""Synthetic contract tests for tranche 5 (v0.9.0), not official/CMB tests.
Run PHASEB_ROOT=/path/phaseB OPENBLAS_NUM_THREADS=1 python -m pytest -q this_file.py
A failure-injection test is not an observed scientific result.
"""
import os,sys,copy,hashlib
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]));sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_b2_tranche3 import make_family_pair
from test_b2_tranche4 import make_staged_family
import step1_engine.orchestrator as o
from step1_engine import checkpoint as cp, serialization as ser
from step1_engine.precision import PrecisionState
from step1_engine.bootstrap_plan import FittingPlan
from step1_engine.errors import InputContractError
from step1_engine.truth import TECH

@pytest.fixture(scope='module')
def pair():return make_family_pair(np.random.default_rng(20260914))[:2]
@pytest.fixture(scope='module')
def result(pair):return o.evaluate_family_staged(*pair,80.,400.)

def sha_bank(fb):return hashlib.sha256(np.ascontiguousarray(fb.X_model).tobytes()+np.ascontiguousarray(fb.X_ref).tobytes()+np.ascontiguousarray(fb.cid).tobytes()).hexdigest()
def fitted(fam,sha):
 fb=fam.fitting[fam.configs[0].evaluation_id]
 return {s:FittingPlan.build(f'fit-{s}',1,7,s,fb.K,30,20260914,sha) for s in range(5)}

def test_normal_system_stages_and_checkpoint_roundtrip(pair,result,tmp_path):
 assert result.native is not None and result.truths['support'] is True
 p=str(tmp_path/'normal.json');h=cp.write_family_result(result,p)
 got=cp.read_family_result(p,h)
 assert got['result']['truths']==result.truths
 assert got['result']['Q_ci_seed0']==ser.from_jsonable(result.Q_ci_seed0)

@pytest.mark.parametrize('failed_system',['matched','native'])
def test_N_selection_technical_failure_cannot_be_healed_by_reevaluation(pair,monkeypatch,failed_system):
 original=o._family_Q;injected=False
 def fail_first(f,*args,**kw):
  nonlocal injected
  Q,cis,prec,per,w,ev=original(f,*args,**kw)
  if not injected and f.configs[0].system==failed_system:
   injected=True
   prec=PrecisionState('technical_fail',None,None,0,0,['audit_injection'])
   per[next(iter(per))]['precision']['state']='technical_fail'
  return Q,cis,prec,per,w,ev
 monkeypatch.setattr(o,'_family_Q',fail_first)
 try:r=o.evaluate_family_staged(*pair,80.,400.)
 except InputContractError:return # fail-fast is also valid
 assert injected and r.decision['technical_status']=='technical_fail'
 assert r.truths['strong' if failed_system=='native' else 'support']==TECH

def test_N_selection_technical_failure_reaches_calibration(pair,monkeypatch):
 original=o._family_Q;calls=0
 def inj(*a,**kw):
  nonlocal calls
  ret=original(*a,**kw);calls+=1
  if calls!=1:return ret
  Q,cis,prec,per,w,ev=ret;prec=PrecisionState('technical_fail',None,None,0,0,['audit_injection']);per[next(iter(per))]['precision']['state']='technical_fail'
  return Q,cis,prec,per,w,ev
 monkeypatch.setattr(o,'_family_Q',inj)
 try:summary,truths=o.calibrate_pseudo({'E7':pair},[80.],[400.],staged=True)
 except InputContractError:return
 assert truths==[TECH] and summary.status=='technical_fail'

def test_one_bank_bound_fitting_plan_normal():
 f=make_staged_family(np.random.default_rng(9),n_cfg=1);f.fit_plans=fitted(f,sha_bank(f.fitting[100]));f.validate();assert f.fitting_plan_binding=='bound'

def test_recorded_fitting_sha_rejects_an_actual_bank_change():
 f=make_staged_family(np.random.default_rng(9),n_cfg=1);f.fit_plans=fitted(f,sha_bank(f.fitting[100]));f.fitting[100].X_model=f.fitting[100].X_model+1
 with pytest.raises(InputContractError):f.validate()

def test_optional_sha_plan_is_never_labelled_bound():
 f=make_staged_family(np.random.default_rng(9),n_cfg=2);f.fit_plans=fitted(f,None)
 try:f.validate()
 except InputContractError:return
 assert f.fitting_plan_binding!='bound'

def test_fitting_plan_checks_its_batch_component():
 f=make_staged_family(np.random.default_rng(9),n_cfg=1);p=fitted(f,None)[0];p.rng_key[4]=99
 with pytest.raises(InputContractError):p.validate()

def test_fitting_plan_rejects_zero_replicates():
 f=make_staged_family(np.random.default_rng(9),n_cfg=1);p=fitted(f,None)[0];p.multiplicities=np.zeros((0,p.K),np.int64)
 with pytest.raises(InputContractError):p.validate()

def test_checkpoint_rejects_wrong_expected_bytes(result,tmp_path):
 p=str(tmp_path/'ok.json');cp.write_family_result(result,p)
 with pytest.raises(InputContractError):cp.read_family_result(p,'0'*64)

@pytest.mark.parametrize('what',['linear_endpoint','Q_point','seed1_shape','precision_cv','native_CI','truth'])
def test_checkpoint_content_agrees_with_its_preserved_evidence(result,tmp_path,what):
 r=copy.deepcopy(result)
 if what=='linear_endpoint':r.Q_ci_seed0['lower']=1e6
 elif what=='Q_point':r.Q_point=1e6
 elif what=='seed1_shape':r.evidence['matched']['per_seed'][1]['num']=np.ones(3)
 elif what=='precision_cv':r.precision['width_cv_logQ']=999.
 elif what=='native_CI':r.native['Q_ci_seed0']['log_lower']=-100.
 elif what=='truth':r.truths['support']=not r.truths['support']
 # This is NOT a hash bypass: writer and reader use the same bytes and returned SHA.
 # The contract being tested is semantic consistency of result fields with evidence.
 with pytest.raises(InputContractError):
  p=str(tmp_path/(what+'.json'));h=cp.write_family_result(r,p);cp.read_family_result(p,h)

def test_checkpoint_checks_engine_version(result,tmp_path):
 p=str(tmp_path/'normal.json');h=cp.write_family_result(result,p);payload=cp.read_family_result(p,h)
 payload['binding']['engine_version']='foreign-version';body=ser.dumps(payload).encode();q=tmp_path/'foreign.json';q.write_bytes(body)
 with pytest.raises(InputContractError):cp.read_family_result(str(q),hashlib.sha256(body).hexdigest())

def test_checkpoint_source_inventory_includes_its_own_validator():
 # The report claims ALL module SHAs; the new loader is a module too.
 assert {'checkpoint.py','errors.py','__init__.py'} <= set(cp.module_shas())

def test_wrong_log_interval_is_already_rejected(result,tmp_path):
 r=copy.deepcopy(result);r.Q_ci_seed0['log_lower']=0.
 with pytest.raises(InputContractError):
  p=str(tmp_path/'log.json');h=cp.write_family_result(r,p);cp.read_family_result(p,h)
