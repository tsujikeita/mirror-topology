"""Independent small contracts for the new verified decision value type.
R1-R3 baseline uses the actual replay factory. Issuer-negative tests are local
schema tests only: no claim about forging a signature or breaking arbitrary
Python object security. Use PHASEB_ROOT to point to the supplied package.
"""
import os,sys
from pathlib import Path
from dataclasses import asdict,replace,FrozenInstanceError
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from probe_manifest import fixture,cheap_dist
from step1_engine.positions import VerifiedW2Decision,W2NotEvaluated,position_decision,w2_trigger
from step1_engine.w2_manifest import build_w2_manifest,verified_w2_for_decision
from step1_engine.errors import InputContractError
from step1_engine import serialization as ser
P={i:dict(P=p,hits=int(100*p),N=100,precision='pass',stage='N0') for i,p in [(1,.2),(2,.25),(3,.2)]}
PR={i:dict(P=p,hits=int(100*p),N=100,precision='pass',stage='N0') for i,p in [(1,.2),(2,.6),(3,.2)]}
@pytest.fixture(scope='module')
def base():
 ps,iso,r=fixture();man=build_w2_manifest('E7','L1.00',ps,iso,r)
 return ps,iso,r,man,verified_w2_for_decision(man,ps,iso,r)

def issue_like(v,trigger,validation,B=None):
 return VerifiedW2Decision.issue(trigger,validation,v.B_final if B is None else B,v.observed_hash,v.distance_kind,v.scope)

def test_actual_factory_emits_valid_type(base):
 v=base[-1]
 assert isinstance(v,VerifiedW2Decision) and v.check() and v.trigger is True
 assert position_decision(v,P)['state']=='position-sensitive'

def test_not_evaluated_marker_preserves_three_valued_or():
 q=W2NotEvaluated('not evaluated')
 assert position_decision(q,P)['state']=='position-unresolved'
 assert position_decision(q,PR)['state']=='position-sensitive'

def test_frozen_field_assignment(base):
 with pytest.raises((FrozenInstanceError,AttributeError,TypeError)):
  base[-1].trigger=False

def test_stale_checksum_for_trigger_change(base):
 with pytest.raises(InputContractError):position_decision(replace(base[-1],trigger=False),P)

def test_typed_strict_json_roundtrip(base):
 v=base[-1];v2=VerifiedW2Decision(**ser.loads(ser.dumps(asdict(v))))
 assert v2.check() and position_decision(v2,P)==position_decision(v,P)

def test_explicit_technical_failure_still_dominates(base):
 assert position_decision(base[-1],PR,tech_fail=True)['state']=='technical_fail'

@pytest.mark.parametrize('B',[400.5,'400'])
def test_reconstructed_noninteger_B_is_not_covered_by_old_checksum(base,B):
 with pytest.raises(InputContractError):
  position_decision(replace(base[-1],B_final=B),P)

@pytest.mark.parametrize('state',['technical_fail','typo'])
def test_issuer_rejects_non_replay_validation_state(base,state):
 with pytest.raises(InputContractError):
  issue_like(base[-1],'unknown',{'state':state,'reason':'negative schema test'}).check()

def test_issuer_rejects_integer_as_boolean_trigger(base):
 with pytest.raises(InputContractError):
  issue_like(base[-1],1,{'state':'valid','trigger':True}).check()

def test_issuer_requires_trigger_to_agree_with_validation(base):
 with pytest.raises(InputContractError):
  issue_like(base[-1],False,{'state':'valid','trigger':True}).check()

def test_actual_unmeasured_bounds_replay_remains_unresolved(base):
 ps,iso,*_=base
 r=w2_trigger(ps,iso,100,20260914,dist=cheap_dist,whitening_identity={'source':'test'},obs_bounds=None,delta_q99_bound=None)
 m=build_w2_manifest('E7','L1.00',ps,iso,r);v=verified_w2_for_decision(m,ps,iso,r)
 assert v.check() and v.validation_state=='w2-unresolved'
 assert position_decision(v,P)['state']=='position-unresolved'
 assert position_decision(v,PR)['state']=='position-sensitive'

def test_explicit_numpy_boolean_normalization_allowed(base):
 v=issue_like(base[-1],np.bool_(True),{'state':'valid','trigger':np.bool_(True)})
 assert v.check() and position_decision(v,P)['state']=='position-sensitive'
