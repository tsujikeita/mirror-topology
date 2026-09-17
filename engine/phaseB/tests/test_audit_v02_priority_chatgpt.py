"""Independent v0.2 priority acceptance tests. Small synthetic data only.
PHASEB_ROOT=/path/to/phaseB python -m pytest -q test_v02_priority.py
Red tests describe an unmet contract; they are not patches or runtime failure rates.
"""
import os,sys,math,copy,json
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]));sys.path.insert(0,str(ROOT))
from step1_engine.ci import ci_from_replicates,CIResult
from step1_engine.precision import precision_state
from step1_engine.truth import precision_to_audit
from step1_engine.decision import CoreInputs,decide_core
from step1_engine.calibration import calibrate
from step1_engine.bootstrap_plan import ClusterUID,HitTable,BootstrapPlan,resample_hits
from step1_engine.registry import CRNRegistry
from step1_engine.w2_stop import w2_stop,w2_validate,StopResult
from step1_engine import serialization as ser
from step1_engine.errors import InputContractError
from step1_engine.observers12 import lattice_1d

def base(**kw):
 d=dict(audit_Q_matched='pass',audit_Dpoint_matched='pass',audit_DCI_matched='pass',audit_Q_native='pass',L_Q_matched=12.,U_Q_matched=14.,logD_point_matched=.5,L_logD_matched=.1,U_logD_matched=.9,L_Q_native=1.5,U_Q_native=2.);d.update(kw);return CoreInputs(**d)
def ci5():return [ci_from_replicates(np.linspace(11,13,2000),np.ones(2000),seed_id=s) for s in range(5)]
def require_technical_or_rejection(f):
 try:r=f()
 except InputContractError:return
 assert r.technical_status=='technical_fail'

def test_closed_bool_normalisation():
 a=calibrate([True]*2000,.05);b=calibrate(np.ones(2000,dtype=bool),.05)
 assert a.c_true==b.c_true==2000 and b.usable is False

def test_closed_precision_adapter():
 c=ci5();p=precision_state(c[0],c,12.,10,10)
 assert decide_core(base(audit_Q_matched=precision_to_audit(p.state))).support_truth=='unknown'

def test_closed_other_seed_technical_failure():
 c=ci5();c[4]=ci_from_replicates([np.nan],[1.],seed_id=4)
 assert precision_state(c[0],c,12.,100,100).state=='technical_fail'

def test_closed_independent_bootstrap_groups():
 a=BootstrapPlan.build('a',0,{0:[ClusterUID(1,200,1,0,i) for i in range(6)]},20,1)
 b=BootstrapPlan.build('b',0,{0:[ClusterUID(1,500,2,0,i) for i in range(6)]},20,1)
 assert not np.array_equal(a.multiplicities[0],b.multiplicities[0])

def test_closed_CI_typed_roundtrip():
 c=ci_from_replicates(np.r_[np.zeros(80),np.full(1920,20.)],np.ones(2000))
 d=CIResult(**ser.loads(ser.dumps(c.as_dict())))
 assert d==c and d.log_lower==-math.inf

def test_closed_stop_typed_roundtrip():
 null={2000:np.full(1000,.2),5000:np.full(1000,.15)};obs={n:{s:.1 for s in range(3)} for n in null}
 st=w2_stop(null,obs,'reference');rest=StopResult(**ser.loads(ser.dumps(st.as_dict())))
 b={n:{s:0. for s in range(3)} for n in null};dq={n:0. for n in null}
 assert w2_validate(rest,0.,b,dq,obs)['state']=='valid'

def test_contract_logD_point_inf_not_valid():
 require_technical_or_rejection(lambda:decide_core(base(logD_point_matched=math.inf)))

def test_contract_logD_CI_inf_not_valid():
 require_technical_or_rejection(lambda:decide_core(base(L_logD_matched=math.inf,U_logD_matched=math.inf)))

def test_contract_reversed_Q_interval_not_valid():
 require_technical_or_rejection(lambda:decide_core(base(L_Q_matched=12.,U_Q_matched=.8)))

def test_contract_negative_Q_interval_not_valid():
 require_technical_or_rejection(lambda:decide_core(base(L_Q_matched=-2.,U_Q_matched=-1.,logD_point_matched=-.3,L_logD_matched=-.4,U_logD_matched=-.1)))

def test_contract_calibration_rejects_2D_truth():
 with pytest.raises(InputContractError):calibrate(np.zeros((1000,2),dtype=bool),.01,expected_n=2000)

def test_contract_registry_UID_composes_with_plan():
 # Recommended API: use a shared UID type, or replace this line with the specified public adapter.
 r=CRNRegistry(20260913);g=r.new_group('evaluation',1,'E7');uids=[r.cluster_uid(1,'evaluation',g,0,i) for i in range(3)]
 p=BootstrapPlan.build('evaluation',0,{0:uids},20,20260913)
 t=HitTable(uids,np.array([1,2,3]),300,100)
 assert np.isfinite(resample_hits(p,{0:t},{0:1.})[0]).all()

def test_contract_stratum_weights_equal_sample_fractions():
 u0=[ClusterUID(1,200,1,0,i) for i in range(2)];u1=[ClusterUID(1,200,1,1,i) for i in range(6)]
 p=BootstrapPlan.build('unequal-N',0,{0:u0,1:u1},20,20260913)
 t={0:HitTable(u0,np.full(2,10),20,10),1:HitTable(u1,np.zeros(6,dtype=int),60,10)}
 assert np.all(resample_hits(p,t,{0:.25,1:.75})[0]==.25)
 with pytest.raises(InputContractError):resample_hits(p,t,{0:.5,1:.5})

def test_contract_lattice_small_non_grid_offset_rejected():
 with pytest.raises(InputContractError):lattice_1d(.02,.230001)
