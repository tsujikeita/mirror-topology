"""Audit-only small tests, not an official engine release.
Run PHASEB_ROOT=/path/to/phaseB OPENBLAS_NUM_THREADS=1 python -m pytest -q this_file.py.
No real CMB inputs; external-solver warning is deliberately injected, not a POT run.
"""
from pathlib import Path
import os,sys,copy,types,warnings,importlib.util
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(ROOT))
from step1_engine import positions as p
from step1_engine.expansion import expansion_decision,family_expansion_plan
from step1_engine.truth import TECH,UNKNOWN
from step1_engine.errors import InputContractError


def mkpos(K=60,m=2):
 rng=np.random.default_rng(382)
 return [p.PositionBank(i+1,rng.normal(size=(K*m,2)),np.repeat(np.arange(K),m)) for i in range(3)]

def cheap(a,b):return float(np.max(np.abs(a.mean(0)-b.mean(0))))

def Pbase():
 return {1:dict(P=.004,hits=40,precision='pass'),2:dict(P=.006,hits=60,precision='pass'),3:dict(P=.005,hits=50,precision='pass')}

def test_registered_expansion_states_are_preserved():
 for state in ('precision-unresolved','cv_undefined'):
  assert expansion_decision(1,'N0',state,5,3).action=='expand_to_4N0'
  assert expansion_decision(1,'N4',state,5,3).action=='precision-unresolved'
 assert expansion_decision(1,'N0','technical_fail',5,3).action=='technical_fail'
 assert expansion_decision(1,'N0','pass',500,300).action=='keep'

@pytest.mark.parametrize('state',[None,'typo'])
def test_expansion_rejects_unregistered_state(state):
 with pytest.raises(InputContractError):expansion_decision(1,'N0',state,5,3)

@pytest.mark.parametrize('bad_hit',[.9,-.9])
def test_family_expansion_does_not_truncate_bad_counts(bad_hit):
 with pytest.raises(InputContractError):family_expansion_plan({1:dict(precision=dict(state='precision-unresolved'),hits_M=bad_hit,hits_I=3)},'N0')

def test_empty_family_does_not_become_resolved():
 with pytest.raises(InputContractError):family_expansion_plan({},'N0')

@pytest.mark.parametrize('bad_P',[np.nan,np.inf,-.01,1.1])
def test_event_ratio_invalid_probability_not_boolean(bad_P):
 P=Pbase();P[2]['P']=bad_P
 try:out=p.position_decision(dict(trigger=False),P)
 except InputContractError:return
 assert out['state']=='technical_fail',out

def test_event_ratio_does_not_truncate_fractional_hits():
 P=Pbase();P[2]['hits']=.9
 with pytest.raises(InputContractError):p.event_ratio_trigger(P)

def test_event_ratio_rejects_unregistered_precision_state():
 P=Pbase();P[2]['precision']='typo'
 with pytest.raises(InputContractError):p.event_ratio_trigger(P)

def test_zero_hit_N0_is_not_yet_position_expansion():
 # A stage-aware adapter may reject this input; it must not authorize 12 positions.
 P=Pbase();P[2].update(P=0.,hits=0,precision='precision-unresolved',stage='N0')
 try:out=p.position_decision(dict(trigger=False),P)
 except InputContractError:return
 assert out['state']!='position-sensitive',out

def test_valid_event_ratio_states():
 P=Pbase();assert p.event_ratio_trigger(P)[0] is False
 P[2]['P']=.01;assert p.event_ratio_trigger(P)[0] is True
 P[2]['precision']='precision-unresolved';assert p.event_ratio_trigger(P)[0]==UNKNOWN
 P[1]['precision']='technical_fail';assert p.event_ratio_trigger(P)[0]==TECH

def test_observed_samples_really_have_registered_n_sub():
 # Banks have two rows/cluster, requested call claims m=100; do not label 40 rows as 2000.
 sizes=[]
 def spy(a,b):sizes.append((len(a),len(b)));return cheap(a,b)
 try:p.observed_w2max(mkpos(),2000,100,0,1,spy)
 except InputContractError:return
 assert sizes and all(x==(2000,2000) for x in sizes),sizes

def test_null_blocks_really_have_registered_n_sub():
 iso=mkpos(K=180,m=2)[0];sizes=[]
 def spy(a,b):sizes.append((len(a),len(b)));return cheap(a,b)
 try:p.null_max_sequence(iso,2000,100,1,spy,B_max=2)
 except InputContractError:return
 assert sizes and all(x==(2000,2000) for x in sizes),sizes

def test_gapped_ids_are_rejected_or_mapped_without_empty_clusters():
 positions=[]
 for i in range(3):positions.append(p.PositionBank(i+1,np.arange(24,dtype=float).reshape(12,2)+i,np.repeat([0,2,4,6,8,10],2)))
 sizes=[]
 def spy(a,b):sizes.append((len(a),len(b)));return cheap(a,b)
 try:p.observed_w2max(positions,4,2,0,1,spy)
 except InputContractError:return
 assert sizes and all(x==(4,4) for x in sizes),sizes

def test_duplicate_position_not_three_distinct_positions():
 a=mkpos()[0]
 with pytest.raises(InputContractError):p.observed_w2max([a,a,a],20,2,0,9,cheap)

def test_valid_subsample_cardinality():
 sizes=[]
 def spy(a,b):sizes.append((len(a),len(b)));return cheap(a,b)
 r=p.observed_w2max(mkpos(K=30,m=3),12,3,0,1,spy)
 assert all(x==(12,12) for x in sizes)
 assert set(r['pairwise'])=={'P1P2','P1P3','P2P3'}
 assert r['W2_max']==max(r['pairwise'].values())

def test_external_solver_warning_cannot_certify_exact_result(monkeypatch):
 # Stub tests error handling only; no claim that an actual POT solve failed.
 fake=types.ModuleType('ot')
 fake.dist=lambda a,b,metric:np.zeros((len(a),len(b)))
 def emd(*args,**kw):
  warnings.warn('injected non-optimal result',UserWarning)
  return (4.,dict(warning='non-optimal',result_code=3)) if kw.get('log') else 4.
 fake.emd2=emd;monkeypatch.setitem(sys.modules,'ot',fake)
 with warnings.catch_warnings():
  warnings.simplefilter('ignore')
  with pytest.raises((InputContractError,RuntimeError)):
   p.w2_exact(np.zeros((2,2)),np.ones((2,2)))
