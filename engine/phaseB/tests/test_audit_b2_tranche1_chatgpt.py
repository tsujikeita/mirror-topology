"""Audit acceptance proposals for B2 tranche 1, not an official engine patch.
Run: PHASEB_ROOT=/path/to/phaseB OPENBLAS_NUM_THREADS=1 python -m pytest -q this_file.py
Small synthetic/fault-injection tests; no CMB, full-grid, or OT run.
"""
from pathlib import Path
import os,sys,copy,importlib.util
from unittest.mock import patch
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('audit_submitted_b2',ROOT/'tests/test_b2.py')
tb=importlib.util.module_from_spec(spec);spec.loader.exec_module(tb)
import step1_engine.orchestrator as o
from step1_engine.density import logD_with_ci, logD_at, kde_logpdf_weighted,kde_logpdf_literal
from step1_engine.ci import CIResult,ci_from_replicates
from step1_engine.quantity import ratio_quantity,logD_quantity
from step1_engine.precision import precision_state
from step1_engine.errors import InputContractError
from step1_engine.truth import TECH,UNKNOWN

@pytest.fixture(scope='module')
def baseline(): return tb.build_fixture()

def test_normal_supported_family(baseline):
 r=o.evaluate_family(*baseline['E7'],*tb.THR)
 assert r.truths['support'] is True and r.precision['state']=='pass'
 assert r.logD['ci'] is None

def test_infinite_Q_boundary_remains_unknown():
 den=np.ones(2000);den[:100]=0
 cis=[ci_from_replicates(np.ones(2000),den,mode='Q',seed_id=s) for s in range(5)]
 p=precision_state(cis[0],cis,1.,100,100);q=ratio_quantity('Q',cis[0],p,1.)
 assert q.audit=='unresolved' and q.lower is None and q.ci_math_state=='boundary'

@pytest.mark.parametrize('weights',[[1.,1.],[-.5,-.5],[.5]])
def test_prior_is_not_silently_repaired(baseline,weights):
 f=copy.deepcopy(baseline['E7'][0]);f.configs=f.configs[:len(weights)]
 for c,w in zip(f.configs,weights):c.weight=w
 with pytest.raises(InputContractError):o._family_Q(f,*tb.THR)

def test_point_KDE_audits_cannot_cancel_in_mixture(baseline):
 f=copy.deepcopy(baseline['E7'][0]);rng=np.random.default_rng(3344);K,m=60,10
 X=rng.normal(size=(K*m,2))*[40,200]+[120,600];Y=X-np.array([.9,.8])*[40,200];cid=np.repeat(np.arange(K),m);t=[39.67,259.34]
 f.fitting={f.configs[0].evaluation_id:o.FittingBank(Y,X,cid),f.configs[1].evaluation_id:o.FittingBank(X,Y,cid)}
 for c,w in zip(f.configs,[.55,.45]):c.weight=w
 for c in f.configs:
  fb=f.fitting[c.evaluation_id];p=logD_at(fb.X_model,cid,fb.X_ref,cid,t)
  assert max(abs(logD_at(fb.X_model,cid,fb.X_ref,cid,t,factor_scale=s)-p) for s in (.7,1.4))>.1
 # Existing tuple's fourth field is the audit used for the family predicate.
 assert o._family_logD(f,np.array(t),np.array([.55,.45]),False)[3] is False

def kde_fixture():
 rng=np.random.default_rng(71);K,m,B=30,4,10
 X=rng.normal(size=(K*m,2));Y=X+.2;cid=np.repeat(np.arange(K),m)
 M=np.stack([np.bincount(rng.integers(K,size=K),minlength=K) for _ in range(B)])
 return X,Y,cid,M

@pytest.mark.parametrize('bad_value',[np.nan,-1.,.5])
def test_KDE_plan_rejects_invalid_multiplicity(bad_value):
 X,Y,cid,M=kde_fixture();bad=M.astype(float);pos=int(np.flatnonzero(bad[2]>0)[0]);bad[2,pos]=bad_value
 try:r=logD_with_ci(X,cid,Y,cid,[0.,0.],bad,M)
 except InputContractError:return
 assert r.ci.math_state=='technical_fail','invalid draw must not be silently dropped/used'

def test_KDE_rejects_negative_cluster_index():
 X,Y,cid,M=kde_fixture();cid=cid.copy();cid[0]=-1
 with pytest.raises(InputContractError):logD_with_ci(X,cid,Y,cid,[0.,0.],M,M)

def test_KDE_single_singular_draw_is_fail_closed():
 X,Y,cid,M=kde_fixture();X[cid==0]=0;M[2]=0;M[2,0]=30
 r=logD_with_ci(X,cid,Y,cid,[0.,0.],M,M)
 assert r.ci.math_state=='technical_fail' and r.ci.log_lower is None

def test_KDE_failure_count_is_number_of_unique_failed_draws():
 X,Y,cid,M=kde_fixture();X[cid==0]=0;M[2]=0;M[2,0]=30
 r=logD_with_ci(X,cid,Y,cid,[0.,0.],M,M)
 assert r.n_failed==1 and r.ci.counts['technical_invalid']==1

def test_plan_seed_identity_must_match_mapping_keys(baseline):
 f=copy.deepcopy(baseline['E7'][0]);f.plans={s:f.plans[0] for s in range(5)}
 with pytest.raises(InputContractError):o._family_Q(f,*tb.THR)

def test_individual_positive_counts_are_not_family_minima(baseline):
 f=copy.deepcopy(baseline['E7'][0]);c=f.configs[1]
 for a in (c.T1_model,c.T2_model,c.T1_ref,c.T2_ref):a[:]=2000;a[:10*c.m]=0
 r=o._family_Q(f,*tb.THR)
 for c in f.configs:
  p=r[3][c.evaluation_id]['precision']
  for which,key in [('model','positive_clusters_model'),('ref','positive_clusters_ref')]:
   actual=sum(int((h.hits>0).sum()) for h in c.hit_tables(*tb.THR,which).values())
   assert p[key]==actual

def test_configuration_CI_technical_failure_dominates(baseline):
 original=o.ci_from_replicates;calls=0
 def inject(*args,**kw):
  nonlocal calls
  calls+=1
  if calls==1:return CIResult('Q',None,None,None,None,'none','technical_fail',{'technical_invalid':1},.05,len(args[0]),'injected failure',kw.get('seed_id'))
  return original(*args,**kw)
 with patch.object(o,'ci_from_replicates',side_effect=inject):r=o._family_Q(baseline['E7'][0],*tb.THR)
 assert r[3][100]['precision']['state']=='technical_fail'
 assert r[2].state=='technical_fail'

def test_coverage_does_not_hide_core_technical_failure(baseline):
 f=copy.deepcopy(baseline['E7'][0]);f.coverage_ok=False
 with patch.object(o,'_family_logD',return_value=(np.nan,None,{'x0.7':np.nan,'x1.4':np.nan},False)):
  r=o.evaluate_family(f,None,*tb.THR)
 assert r.decision['technical_status']=='technical_fail'
 assert r.truths['support']==TECH

def test_pseudo_vectors_must_have_same_length(baseline):
 with pytest.raises(InputContractError):o.calibrate_pseudo(baseline,np.array([80.]),np.array([400.,np.nan]))

def test_logD_adapter_rejects_Q_domain_CI():
 ci=ci_from_replicates(np.linspace(11,13,2000),np.ones(2000),mode='Q')
 with pytest.raises(InputContractError):logD_quantity('D',.3,ci)

def test_logD_adapter_retains_existing_technical_failure():
 ci=CIResult('logD',None,None,None,None,'none','technical_fail',{'technical_invalid':1},.05,10,'failure',0)
 assert logD_quantity('D',None,ci).audit==TECH

def test_KDE_valid_integer_draw_matches_literal():
 X,Y,cid,M=kde_fixture()
 for f in (.7,1.,1.4):
  a=kde_logpdf_weighted(X,M[0][cid],np.array([[0.,0.],[1.,1.]]),f)
  b=kde_logpdf_literal(X,M[0][cid],np.array([[0.,0.],[1.,1.]]),f)
  np.testing.assert_allclose(a,b,rtol=0,atol=1e-12)
