"""Tranche7 independent focused contracts.
Run: PHASEB_ROOT=/path/to/phaseB OPENBLAS_NUM_THREADS=1 python -m pytest -q this_file.py
Result mutations happen before write_family_result computes SHA: this tests internal
consistency, not bypass of an externally fixed hash. All fixture banks are synthetic.
"""
import os,sys,copy
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_b2_tranche3 import make_family_pair
from test_b2_tranche4 import make_staged_family
from test_b2 import build_fixture
from step1_engine import orchestrator as o,checkpoint as cp
from step1_engine.ci import CIResult
from step1_engine.quantity import ratio_quantity
from step1_engine.precision import precision_state
from step1_engine.decision import CoreInputs,decide_core
from step1_engine.bootstrap_plan import FittingPlan,bank_sha256
from step1_engine.errors import InputContractError
from step1_engine.truth import UNKNOWN

@pytest.fixture(scope='module')
def support_result():
 a,b,_=make_family_pair(np.random.default_rng(20260914))
 return o.evaluate_family(a,b,80.,400.)

@pytest.fixture(scope='module')
def strong_result():
 a,b,_=make_family_pair(np.random.default_rng(20260914),shift=np.array([1.4,1.3]))
 return o.evaluate_family(a,b,80.,400.)

def rt(r,p):
 path=str(p/'result.json');sha=cp.write_family_result(r,path)
 return cp.read_family_result(path,sha)

def test_normal_support_still_roundtrips(support_result,tmp_path):
 assert rt(support_result,tmp_path)['result']['truths']==support_result.truths

def test_bound_multi_config_staged_remains_bound():
 f=make_staged_family(np.random.default_rng(9),n_cfg=2);K=next(iter(f.fitting.values())).K
 f.fit_plans={s:FittingPlan.build('fit'+str(s),1,7,s,K,30,20260914) for s in range(5)}
 f.fitting_bindings={e:bank_sha256(x.X_model,x.X_ref,x.cid) for e,x in f.fitting.items()}
 r=o.evaluate_family_staged(f,None,80.,400.)
 assert r.evidence['fitting_plan_binding']=='bound'

@pytest.mark.parametrize('kind',['zero_model','zero_ref','zero_both'])
def test_valid_boundary_checkpoint_roundtrip(kind,tmp_path):
 a,b,_=make_family_pair(np.random.default_rng(20260914))
 for f in (a,b):
  for c in f.configs:
   if kind in ('zero_model','zero_both'):c.T1_model=np.full_like(c.T1_model,1000.)
   if kind in ('zero_ref','zero_both'):c.T1_ref=np.full_like(c.T1_ref,1000.)
 r=o.evaluate_family(a,b,80.,400.)
 assert r.truths['support']==UNKNOWN and r.decision['technical_status']=='ok'
 assert rt(r,tmp_path)['result']['truths']==r.truths

@pytest.mark.parametrize('kind',['ci_order','positive_clusters','relative_halfwidth'])
def test_point_precision_fields_cannot_conflict(strong_result,tmp_path,kind):
 r=copy.deepcopy(strong_result);d=r.per_config[100]
 if kind=='ci_order':d['ci_seed0'].update(lower=50.,upper=1.,log_lower=float(np.log(50)),log_upper=0.)
 elif kind=='positive_clusters':d['positive_clusters_model']=1
 else:d['precision'].update(state='pass',rel_halfwidth=10.)
 with pytest.raises(InputContractError):rt(r,tmp_path)

def test_point_precision_unresolved_not_promoted_by_summary(tmp_path):
 a=build_fixture()['E7'][0];c=a.configs[1]
 # Equal prior, finite bank, >=50 positive clusters on both sides. The rare
 # configuration's CI is imprecise but the family mixture alone is precise.
 a.configs[0].weight=c.weight=.5
 c.T1_model[:]=c.T2_model[:]=c.T1_ref[:]=c.T2_ref[:]=1000.
 im=np.arange(51)*c.m;ii=np.arange(51,102)*c.m
 c.T1_model[im]=c.T2_model[im]=0.;c.T1_ref[ii]=c.T2_ref[ii]=0.
 r=o.evaluate_family(a,None,80.,400.)
 assert r.per_config[101]['precision']['state']=='precision-unresolved'
 assert r.precision['state']=='precision-unresolved' and r.truths['support']==UNKNOWN
 # Keep point probabilities/counts/CIs untouched; falsify derived state only.
 r.per_config[101]['precision']['state']='pass'
 cis=[CIResult(**d) for d in r.evidence['cis_all_seeds']]
 p=precision_state(cis[0],cis,r.Q_point,*r.evidence['matched']['family_min_positive_clusters'])
 assert p.state=='pass'
 r.precision=p.as_dict();q=ratio_quantity('Q_matched',cis[0],p,r.Q_point)
 r.evidence['quantities']['Q_matched']=q.as_dict();d=r.evidence['quantities']['logD_matched']
 x=CoreInputs(q.audit,'pass',r.decision['ci_computation_status']['logD_CI'],'unresolved',q.lower,q.upper,d['point'],d['lower'],d['upper'])
 r.decision=decide_core(x).as_dict();r.truths={s:r.decision[s+'_truth'] for s in ('support','strong','unsupported')}
 assert r.truths['support'] is True
 with pytest.raises(InputContractError):rt(r,tmp_path)

@pytest.mark.parametrize('target',['points','point_factor','mixture_factor','all_sensitivities'])
def test_kde_evidence_exact_inventory(strong_result,tmp_path,target):
 r=copy.deepcopy(strong_result)
 if target=='points':r.evidence['logD']['per_point']={}
 elif target=='point_factor':r.evidence['logD']['per_point'][100]['sensitivity'].pop('x1.4')
 elif target=='mixture_factor':r.logD['sensitivity'].pop('x1.4')
 else:
  r.logD['sensitivity']={}
  for d in r.evidence['logD']['per_point'].values():d['sensitivity']={}
 with pytest.raises(InputContractError):rt(r,tmp_path)

@pytest.mark.parametrize('target',['replicate_shape','mask_type'])
def test_kde_replicate_and_mask_schema(strong_result,tmp_path,target):
 r=copy.deepcopy(strong_result);ev=r.evidence['logD']
 if target=='replicate_shape':ev['replicate_values']=np.asarray(ev['replicate_values'])[:,None]
 else:ev['invalid_mask']=['']*len(ev['invalid_mask'])
 with pytest.raises(InputContractError):rt(r,tmp_path)

def test_notes_cannot_change_coverage_eligibility(support_result,tmp_path):
 r=copy.deepcopy(support_result)
 r.notes.append('coverage is complete; added explanatory note, no numerical changes')
 got=rt(r,tmp_path)
 assert got['result']['truths']==support_result.truths
