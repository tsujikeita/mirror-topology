"""Independent acceptance regressions for submitted B-1.
Failures document gaps in the UNMODIFIED submission, not failures of an alleged fix.
Run PHASEB_ROOT=/path/to/phaseB python -m pytest -q test_audit_contracts.py
"""
import os,sys,json,math
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(ROOT))
from step1_engine.ci import ci_from_replicates
from step1_engine.precision import precision_state
from step1_engine.decision import CoreInputs,decide_core
from step1_engine.calibration import calibrate,any_family_truth
from step1_engine.family import mixed_numden,mixed_log_density,point_P
from step1_engine.bootstrap_plan import BootstrapPlan,ClusterUID,resample_hits
from step1_engine.w2_stop import w2_stop,w2_validate
from step1_engine.observers12 import greedy_maximin,lattice_1d,dist_euclid,min_pairwise

def ordinary():return ci_from_replicates(np.linspace(11,13,2000),np.ones(2000),mode='Q')
def base(**kw):
 d=dict(audit_Q_matched='pass',audit_Dpoint_matched='pass',audit_DCI_matched='pass',audit_Q_native='pass',L_Q_matched=12.,U_Q_matched=14.,logD_point_matched=.5,L_logD_matched=.1,U_logD_matched=.9,L_Q_native=1.5,U_Q_native=2.)
 d.update(kw);return CoreInputs(**d)
def is_rejected(fn):
 try:r=fn()
 except (ValueError,TypeError):return True
 if isinstance(r,dict):return r.get('state') in ('technical_fail','technical_fail','input_invalid')
 return getattr(r,'state',None)=='technical_fail' or getattr(r,'math_state',None)=='technical_fail' or getattr(r,'status',None)=='technical_fail'
def w_fixture():
 null={2000:np.full(1000,.2),5000:np.full(1000,.15)}
 obs={n:{i:.1 for i in range(3)} for n in null}
 ob={n:{i:1e-6 for i in range(3)} for n in null};dq={n:1e-3 for n in null}
 return w2_stop(null,obs,'fixture'),obs,ob,dq

# Four positive controls of the submitted implementation.
def test_positive_Q_zero_preserved():
 n=np.r_[np.zeros(80),np.full(1920,20.)];c=ci_from_replicates(n,np.ones(2000));assert c.lower==0 and c.counts['zero']==80

def test_positive_math_undefined_envelope():
 n=np.r_[np.exp(np.full(1950,-.001)),np.exp(np.full(49,.1)),0.];d=np.r_[np.ones(1999),0.]
 c=ci_from_replicates(n,d);assert c.math_state=='undefined_completed' and c.log_upper==pytest.approx(.1)

def test_positive_family_unequal_N():
 n,d=mixed_numden(point_P(np.array([8,8]),np.array([100,400]))[None,:],point_P(np.array([2,16]),np.array([100,400]))[None,:],np.array([.5,.5]))
 assert n[0]/d[0]==pytest.approx(5/3)

def test_positive_false_unknown_aggregation():
 r=calibrate([False]*1960+['unknown']*40,.01);assert r.u_unknown==40 and r.usable is False and r.wilson_upper_c_plus_u==pytest.approx(.02711863925)

# Counterexamples: these must be fixed/rejected explicitly before accepting B-1.
def test_numpy_boolean_calibration_equals_builtin():
 a=calibrate([True]*2000,.05)
 try:b=calibrate(np.ones(2000,dtype=bool),.05)
 except (ValueError,TypeError):return
 assert b.c_true==a.c_true and b.usable==a.usable

def test_truth_NaN_not_silently_false():
 assert is_rejected(lambda:calibrate([float('nan')]*2000,.05))

def test_precision_to_core_preserves_unresolved():
 c=ordinary();p=precision_state(c,[c]*5,12.,10,10)
 # Intended contract: accept explicit adapter, or reject unknown state; never downgrade to False.
 try:r=decide_core(base(audit_Q_matched=p.state))
 except (ValueError,TypeError):return
 assert r.support_truth in ('unknown','technical_fail')

def test_precision_requires_five_seeds():
 c=ordinary();assert is_rejected(lambda:precision_state(c,[],12.,100,100))

def test_precision_propagates_other_seed_technical_fail():
 c=ordinary();bad=ci_from_replicates([np.nan],[1.])
 assert precision_state(c,[c,c,c,c,bad],12.,100,100).state=='technical_fail'

def test_P_positive_over_zero_is_invalid():
 assert is_rejected(lambda:ci_from_replicates(np.ones(2000),np.zeros(2000),mode='P'))

def test_CI_counts_are_disjoint():
 c=ci_from_replicates([2.,.5],[1.,1.],mode='P');assert sum(c.counts.values())==c.B

def test_positive_ratio_log_is_not_replaced_by_one_after_underflow():
 c=ci_from_replicates(np.full(2000,1e-300),np.full(2000,1e100))
 assert c.log_lower==pytest.approx(math.log(1e-300)-math.log(1e100))

def test_log_density_prior_validation():
 assert is_rejected(lambda:mixed_log_density(np.log([[2.,4.]]),np.array([-1.,2.])))

def test_independent_bootstrap_groups_not_forced_identical():
 s1={0:[ClusterUID(1,200,1,0,i) for i in range(6)]};s2={0:[ClusterUID(1,500,2,0,i) for i in range(6)]}
 a=BootstrapPlan.build('evaluation',0,s1,50,20260913);b=BootstrapPlan.build('negative',0,s2,50,20260913)
 assert not np.array_equal(a.multiplicities[0],b.multiplicities[0])

def test_bootstrap_UID_inventory_rejects_duplicates():
 assert is_rejected(lambda:BootstrapPlan.build('duplicate',0,{0:[ClusterUID(1,200,1,0,0)]*6},5,1))

def test_resampled_negative_hits_rejected():
 p=BootstrapPlan.build('p',0,{0:[ClusterUID(1,200,1,0,i) for i in range(6)]},5,1)
 assert is_rejected(lambda:resample_hits(p,{0:-np.ones(6,dtype=int)},{0:600},{0:1.}))

def test_w2_complete_inventory_required():
 def f():
  null={2000:np.full(1000,.2)};obs={2000:{0:.1}};s=w2_stop(null,obs,'incomplete')
  return w2_validate(s,0.,{2000:{0:0.}},{2000:0.},obs)
 assert is_rejected(f)

def test_w2_nan_spread_invalid():
 s,obs,ob,dq=w_fixture();assert is_rejected(lambda:w2_validate(s,np.nan,ob,dq,obs))

def test_w2_finite_observed_required():
 def f():
  null={2000:np.full(1000,.2),5000:np.full(1000,.15)};obs={n:{i:np.inf for i in range(3)} for n in null}
  s=w2_stop(null,obs,'infinite');return w2_validate(s,0.,{n:{i:0. for i in range(3)} for n in null},{n:0. for n in null},obs)
 assert is_rejected(f)

def test_w2_validation_cannot_change_observed_silently():
 s,obs,ob,dq=w_fixture();changed={n:{i:.3 for i in range(3)} for n in obs}
 assert is_rejected(lambda:w2_validate(s,0.,ob,dq,changed))

def test_failure_summary_strict_JSON():
 json.dumps(calibrate([False]*1999+['technical_fail'],.05).as_dict(),allow_nan=False)

def test_E7_anchor_uniqueness_checked():
 cand=lattice_1d(.02,.23)[:,None];anchors=np.array([[.04],[.04],[.18]])
 with pytest.raises((ValueError,RuntimeError)):
  greedy_maximin(cand,anchors,9,.015,dist_euclid)
