"""Independent tranche9 audit contracts. All arrays are synthetic and distance
is explicitly injected. No physical-model, official-profile or POT claim.
Expected refusal is InputContractError/TypeError for unsupported raw inputs.
Immutable exported types may prevent mutation OR reject a changed object at intake.
"""
import os,sys,copy
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from probe_manifest import fixture,cheap_dist
from step1_engine.positions import PositionBank,w2_trigger,position_decision
from step1_engine.w2_manifest import W2Manifest,build_w2_manifest,verify_w2_manifest,verified_w2_for_decision
from step1_engine import serialization as ser
from step1_engine.errors import InputContractError
P={i:dict(P=v,hits=int(v*100),N=100,precision='pass',stage='N0') for i,v in [(1,.2),(2,.25),(3,.2)]}
@pytest.fixture(scope='module')
def base():
 ps,iso,r=fixture();m=build_w2_manifest('E7','L1.00',ps,iso,r)
 assert r['validation']['state']=='valid' and r['trigger'] is True
 return ps,iso,r,m

def new_result(base,**kw):
 ps,iso,_,_=base
 params=dict(dist=cheap_dist,obs_bounds={n:{s:0. for s in range(3)} for n in [2000,5000]},delta_q99_bound={n:0. for n in [2000,5000]},whitening_identity={'mu':[0.,0.],'W':[[1.,0.],[0.,1.]],'source':'synthetic'})
 params.update(kw)
 return w2_trigger(ps,iso,100,20260914,**params)

def test_valid_exported_decision_works(base):
 ps,iso,r,m=base;v=verified_w2_for_decision(m,ps,iso,r)
 assert position_decision(v,P)['state']=='position-sensitive'

def test_valid_strict_json_roundtrip(base):
 ps,iso,r,m=base
 assert verify_w2_manifest(W2Manifest(**ser.loads(ser.dumps(m.as_dict()))),ps,iso,ser.loads(ser.dumps(r)))['verified']

@pytest.mark.parametrize('raw',[
 {'trigger':False},
 {'trigger':False,'validation':{'state':'valid','trigger':True}},
 {'trigger':False,'validation':{'state':'technical_fail'}},
])
def test_production_consumer_rejects_unverified_raw_input(raw):
 with pytest.raises((InputContractError,TypeError)):
  position_decision(raw,P)

def test_exported_trigger_cannot_be_mutated_and_consumed(base):
 ps,iso,r,m=base;v=verified_w2_for_decision(m,ps,iso,r)
 try:v['trigger']=False
 except (TypeError,AttributeError,InputContractError):return
 with pytest.raises((InputContractError,TypeError)):
  position_decision(v,P)

def test_exported_validation_cannot_be_mutated_and_consumed(base):
 ps,iso,r,m=base;v=verified_w2_for_decision(m,ps,iso,r)
 try:v['validation']['state']='technical_fail'
 except (TypeError,AttributeError,InputContractError):return
 with pytest.raises((InputContractError,TypeError)):
  position_decision(v,P)

@pytest.mark.parametrize('extra',[0,1000])
def test_observed_cluster_index_must_be_in_live_bank(base,extra):
 ps,iso,r,m=base;q=copy.deepcopy(r)
 q['evidence']['observed'][2000][0]['subsets'][1][-1]=ps[0].K+extra
 with pytest.raises(InputContractError):verify_w2_manifest(m,ps,iso,q)

def test_numpy_whitening_identity_normalized_consistently(base):
 ps,iso,_,_=base
 q=new_result(base,whitening_identity={'mu':np.zeros(2),'W':np.eye(2),'source':'synthetic'})
 m=build_w2_manifest('E7','L1.00',ps,iso,q)
 assert verify_w2_manifest(m,ps,iso,q)['verified']
 assert verify_w2_manifest(W2Manifest(**ser.loads(ser.dumps(m.as_dict()))),ps,iso,ser.loads(ser.dumps(q)))['verified']

def test_execution_bank_mutation_is_not_snapshotted_as_origin(base):
 ps,iso,_,_=base
 pp=[PositionBank(p.position_id,p.Tw.copy(),p.cid.copy(),100) for p in ps]
 ii=PositionBank(iso.position_id,iso.Tw.copy(),iso.cid.copy(),100);calls=0
 def mutating_distance(a,b):
  nonlocal calls
  calls+=1;v=cheap_dist(a,b)
  if calls==6018:pp[0].Tw[:]+=3
  return v
 with pytest.raises(InputContractError):
  q=w2_trigger(pp,ii,100,20260914,dist=mutating_distance,obs_bounds={n:{s:0. for s in range(3)} for n in [2000,5000]},delta_q99_bound={n:0. for n in [2000,5000]})
  m=build_w2_manifest('E7','L1.00',pp,ii,q)
  verify_w2_manifest(m,pp,ii,q)

def test_unmeasured_bounds_remain_unresolved(base):
 ps,iso,_,_=base;q=new_result(base,obs_bounds=None,delta_q99_bound=None)
 m=build_w2_manifest('E7','L1.00',ps,iso,q)
 v=verified_w2_for_decision(m,ps,iso,q)
 assert position_decision(v,P)['state']=='position-unresolved'

def test_large_measured_bounds_remain_unresolved(base):
 ps,iso,_,_=base;q=new_result(base,obs_bounds={n:{s:1000. for s in range(3)} for n in [2000,5000]})
 m=build_w2_manifest('E7','L1.00',ps,iso,q)
 v=verified_w2_for_decision(m,ps,iso,q)
 assert position_decision(v,P)['state']=='position-unresolved'

def test_old_result_trigger_tamper_rejected_by_replay(base):
 ps,iso,r,m=base;q=copy.deepcopy(r);q['trigger']=False
 with pytest.raises(InputContractError):verify_w2_manifest(m,ps,iso,q)

def test_manifest_is_not_aliased_to_result(base):
 ps,iso,r,_=base;q=copy.deepcopy(r);m=build_w2_manifest('E7','L1.00',ps,iso,q)
 assert m.bounds is not q['evidence']['bounds'] and m.validation is not q['validation']
 q['validation']['trigger']=False
 assert m.validation['trigger'] is True
 with pytest.raises(InputContractError):verify_w2_manifest(m,ps,iso,q)

def test_normal_snapshot_is_detached_from_caller_whitening(base):
 ps,iso,_,_=base;wi={'mu':[0.,0.],'W':[[1.,0.],[0.,1.]],'source':'synthetic'}
 q=new_result(base,whitening_identity=wi);wi['mu'][0]=10
 assert q['evidence']['inputs']['whitening']['mu']==[0.,0.]
 m=build_w2_manifest('E7','L1.00',ps,iso,q)
 assert verify_w2_manifest(m,ps,iso,q)['verified']
