"""Synthetic contract checks for tranche6 (engine 0.10.0).
Run: PHASEB_ROOT=/path/to/phaseB OPENBLAS_NUM_THREADS=1 python -m pytest -q this_file.py
Intentional invalid Result tests write the changed Result BEFORE computing SHA.
They test semantic consistency, not bypass of an immutable external SHA.
No real CMB banks, full-grid inference or POT required.
"""
import os,sys,copy
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_b2_tranche3 import make_family_pair
from test_b2_tranche4 import make_staged_family
from test_b2 import build_fixture
from step1_engine import orchestrator as o,checkpoint as cp
from step1_engine.bootstrap_plan import FittingPlan,bank_sha256
from step1_engine.precision import PrecisionState
from step1_engine.decision import CoreInputs,decide_core
from step1_engine.errors import InputContractError
from step1_engine.truth import TECH,UNKNOWN

@pytest.fixture(scope='module')
def bound_family():
 f=make_staged_family(np.random.default_rng(9),n_cfg=2)
 K=next(iter(f.fitting.values())).K
 f.fit_plans={s:FittingPlan.build('common-fit-'+str(s),1,7,s,K,30,20260914) for s in range(5)}
 f.fitting_bindings={e:bank_sha256(x.X_model,x.X_ref,x.cid) for e,x in f.fitting.items()};f.validate();return f

@pytest.fixture(scope='module')
def support_result():
 a,b,_=make_family_pair(np.random.default_rng(20260914));return o.evaluate_family_staged(a,b,80.,400.)

@pytest.fixture(scope='module')
def strong_result():
 a,b,_=make_family_pair(np.random.default_rng(20260914),shift=np.array([1.4,1.3]));return o.evaluate_family(a,b,80.,400.)

@pytest.fixture(scope='module')
def unresolved_result():
 a,b=build_fixture(K=150)['E7'];return o.evaluate_family(a,b,80.,400.)

@pytest.fixture(scope='module')
def failed_result():
 a,b,_=make_family_pair(np.random.default_rng(20260914));orig=o._family_Q;calls=[]
 def fail_once(f,*args,**kw):
  calls.append(f.configs[0].system);Q,cis,prec,per,w,ev=orig(f,*args,**kw)
  if len(calls)==1:
   prec=PrecisionState('technical_fail',None,None,0,0,['audit_injected_Q_failure']);per[next(iter(per))]['precision']['state']='technical_fail'
  return Q,cis,prec,per,w,ev
 with patch.object(o,'_family_Q',fail_once):r=o.evaluate_family_staged(a,b,80.,400.)
 assert calls==['matched','native'] # one per system for selection, no ordinary reevaluation
 assert r.truths==dict(support=TECH,strong=TECH,unsupported=TECH)
 return r

def rt(result,tmp_path):
 p=str(tmp_path/'result.json');sha=cp.write_family_result(result,p);return cp.read_family_result(p,sha)

def test_shared_plan_can_bind_two_distinct_transformed_banks(bound_family):
 assert len(set(bound_family.fitting_bindings.values()))==2
 r=o.evaluate_family(bound_family,None,80.,400.)
 assert r.evidence['fitting_plan_binding']=='bound'

@pytest.mark.parametrize('stage',['N0','N4'])
def test_stage_view_preserves_fitting_bindings(bound_family,stage):
 view=o._stage_family(bound_family,{c.evaluation_id:stage for c in bound_family.configs})
 assert view.fitting_bindings==bound_family.fitting_bindings
 view.validate();assert view.fitting_plan_binding=='bound'

@pytest.mark.parametrize('entry',['direct','staged'])
def test_changed_bank_is_rejected_before_any_stage_evaluation(bound_family,entry):
 f=copy.deepcopy(bound_family);f.fitting[100].X_model+=1.
 with pytest.raises(InputContractError):
  (o.evaluate_family if entry=='direct' else o.evaluate_family_staged)(f,None,80.,400.)

@pytest.mark.parametrize('kind',['support','strong','unresolved','technical_fail'])
def test_normal_result_states_roundtrip(request,tmp_path,kind):
 name={'support':'support_result','strong':'strong_result','unresolved':'unresolved_result','technical_fail':'failed_result'}[kind]
 r=request.getfixturevalue(name);got=rt(r,tmp_path)
 assert got['result']['truths']==r.truths
 if kind=='technical_fail':assert got['result']['truths']==dict(support=TECH,strong=TECH,unsupported=TECH)


def test_valid_extended_Q_is_not_rejected_as_corrupt(tmp_path):
 a,b,_=make_family_pair(np.random.default_rng(20260914))
 for fa in (a,b):
  for c in fa.configs:
   c.T1_ref=np.full_like(c.T1_ref,1000.);c.T2_ref=np.full_like(c.T2_ref,1000.)
 r=o.evaluate_family(a,b,80.,400.)
 assert r.Q_ci_seed0['math_state']=='boundary' and r.precision['state']!='pass'
 assert r.truths['support']==UNKNOWN and r.decision['technical_status']=='ok'
 got=rt(r,tmp_path)
 assert got['result']['truths']==r.truths


def test_failed_result_must_not_contain_success_truths(failed_result,tmp_path):
 r=copy.deepcopy(failed_result);r.truths=dict(support=True,strong=True,unsupported=False)
 r.decision.update(support_truth=True,strong_truth=True,unsupported_truth=False,technical_status='ok',display_label='strong')
 with pytest.raises(InputContractError):rt(r,tmp_path)

@pytest.mark.parametrize('field',['point','ci_order','replicate_values','invalid_mask','point_audit'])
def test_checkpoint_logD_fields_agree_with_saved_evidence(strong_result,tmp_path,field):
 r=copy.deepcopy(strong_result)
 if field=='point':r.logD['point']=-10.
 elif field=='ci_order':r.logD['ci'].update(log_lower=1.,log_upper=-1.)
 elif field=='replicate_values':r.evidence['logD']['replicate_values']=[-1.]*len(r.evidence['logD']['replicate_values'])
 elif field=='invalid_mask':r.evidence['logD']['invalid_mask'][0]=True
 elif field=='point_audit':r.evidence['logD']['per_point'][100]['audit'].update(state='fail',pass_=False)
 with pytest.raises(InputContractError):rt(r,tmp_path)


def test_checkpoint_reconstructs_quantity_audits_from_precision(unresolved_result,tmp_path):
 r=copy.deepcopy(unresolved_result);assert r.precision['state']=='precision-unresolved'
 q=r.evidence['quantities']
 for field,ci in [('Q_matched',r.Q_ci_seed0),('Q_native',r.native['Q_ci_seed0'])]:q[field].update(audit='pass',lower=ci['lower'],upper=ci['upper'])
 qm,qd,qn=q['Q_matched'],q['logD_matched'],q['Q_native']
 x=CoreInputs(qm['audit'],'pass' if r.logD['sensitivity_pass'] else 'fail',r.decision['ci_computation_status']['logD_CI'],qn['audit'],qm['lower'],qm['upper'],qd['point'],qd['lower'],qd['upper'],qn['lower'],qn['upper'])
 r.decision=decide_core(x).as_dict();r.truths=dict(support=r.decision['support_truth'],strong=r.decision['strong_truth'],unsupported=r.decision['unsupported_truth'])
 assert r.truths['support'] is True
 with pytest.raises(InputContractError):rt(r,tmp_path)


def test_checkpoint_native_quantity_matches_native_seed0(strong_result,tmp_path):
 r=copy.deepcopy(strong_result);r.evidence['quantities']['Q_native'].update(lower=1000.,upper=1001.)
 with pytest.raises(InputContractError):rt(r,tmp_path)


def test_checkpoint_seed_id_not_just_list_position(strong_result,tmp_path):
 r=copy.deepcopy(strong_result);r.evidence['cis_all_seeds'][1]['seed_id']=0
 with pytest.raises(InputContractError):rt(r,tmp_path)
