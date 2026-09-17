"""B-1 v0.3: a small current-scope acceptance battery.
PHASEB_ROOT=/absolute/path/to/phaseB python -m pytest -q test_v03_current_priority.py
Only 'interval_invalidity_propagates' is unmet on the submitted v0.3.
"""
from pathlib import Path
import os,sys,math
import numpy as np
import pytest
sys.path.insert(0,os.environ.get('PHASEB_ROOT',str(Path(__file__).resolve().parents[1])))
from step1_engine.decision import CoreInputs,decide_core
from step1_engine.calibration import calibrate
from step1_engine.registry import CRNRegistry
from step1_engine.bootstrap_plan import BootstrapPlan,HitTable,resample_hits,literal_resample_hits
from step1_engine.types import ClusterUID
from step1_engine.errors import InputContractError
from step1_engine.observers12 import lattice_1d
from step1_engine.w2_stop import w2_stop,w2_validate,StopResult
from step1_engine import serialization as ser

def base(**kw):
 d=dict(audit_Q_matched='pass',audit_Dpoint_matched='pass',audit_DCI_matched='pass',audit_Q_native='pass',L_Q_matched=12.,U_Q_matched=14.,logD_point_matched=.5,L_logD_matched=.1,U_logD_matched=.9,L_Q_native=1.5,U_Q_native=2.);d.update(kw);return CoreInputs(**d)

def test_normal_strong_and_finite_D_crossing():
 assert decide_core(base()).strong_truth is True
 r=decide_core(base(L_logD_matched=-.1,U_logD_matched=.9))
 assert r.support_truth is True and r.strong_truth is False and r.technical_status=='ok'

def test_interval_invalidity_propagates_to_needed_predicates():
 # Check the interval as ONE quantity; an invalid unused endpoint must not
 # leave the other endpoint authoritative for support/strong/unsupported.
 cases=[
  ('native upper NaN',dict(U_Q_native=math.nan),('strong_truth',)),
  ('native upper Inf with pass audit',dict(U_Q_native=math.inf),('strong_truth',)),
  ('matched upper NaN',dict(U_Q_matched=math.nan),('support_truth','strong_truth')),
  ('DCI upper NaN',dict(U_logD_matched=math.nan),('strong_truth',)),
  ('DCI lower NaN',dict(L_Q_matched=.5,U_Q_matched=.8,logD_point_matched=-.5,L_logD_matched=math.nan,U_logD_matched=-.1),('unsupported_truth',)),
 ]
 errors=[]
 for name,kw,fields in cases:
  try:r=decide_core(base(**kw))
  except InputContractError:continue
  if r.technical_status!='technical_fail' or any(getattr(r,f) is True for f in fields):errors.append((name,r.as_dict()))
 assert not errors, errors

def test_calibration_strict_axis_and_numpy_truths():
 with pytest.raises(InputContractError):calibrate(np.zeros((1000,2),bool),.01,expected_n=2000)
 with pytest.raises(InputContractError):calibrate([[False]*2]*1000,.01,expected_n=2000)
 r=calibrate(np.ones(2000,bool),.05,expected_n=2000)
 assert r.c_true==2000 and r.usable is False

def test_registry_UID_plan_HitTable_live_composition():
 r=CRNRegistry(20260913);g=r.new_group('evaluation',1,'family');u=[r.cluster_uid(1,'evaluation',g,0,i) for i in range(3)]
 assert all(isinstance(x,ClusterUID) for x in u)
 p=BootstrapPlan.build('a',0,{0:u},20,20260913);t=HitTable(u,np.array([1,2,3]),300,100)
 p1,s1=resample_hits(p,{0:t});p2,s2=literal_resample_hits(p,{0:t})
 assert np.array_equal(p1,p2) and np.array_equal(s1[0],s2[0])

def test_registered_stratum_weights_and_refusal():
 u0=[ClusterUID(1,200,1,0,i) for i in range(2)];u1=[ClusterUID(1,200,1,1,i) for i in range(6)]
 p=BootstrapPlan.build('a',0,{0:u0,1:u1},20,17)
 ts={0:HitTable(u0,np.full(2,10),20,10),1:HitTable(u1,np.zeros(6,int),60,10)}
 assert np.all(resample_hits(p,ts)[0]==.25)
 with pytest.raises(InputContractError):resample_hits(p,ts,{0:.5,1:.5})

def test_non_grid_endpoint_refusal():
 with pytest.raises(InputContractError):lattice_1d(.02,.230001)
 assert len(lattice_1d(.02,.23))==2101

def test_saved_stop_roundtrip_and_previous_corruption_refusal():
 null={n:np.full(1000,.2) for n in (2000,5000)};obs={n:{s:.1 for s in range(3)} for n in null}
 st=w2_stop(null,obs,'x');st=StopResult(**ser.loads(ser.dumps(st.as_dict())))
 b={n:{s:0. for s in range(3)} for n in null};dq={n:0. for n in null}
 assert w2_validate(st,0.,b,dq,obs)['state']=='valid'
 st.trace=st.trace[1:]
 with pytest.raises(InputContractError):st.validate()

def test_strict_serializer_rejects_bad_forms():
 with pytest.raises(InputContractError):ser.dumps({1:'a','1':'b'})
 with pytest.raises(InputContractError):ser.loads('{"a":NaN}')
