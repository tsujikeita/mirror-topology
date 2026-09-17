"""B-2 intake follow-ups, NOT new B-1 completion requirements.
These are restoration/configuration adversarial tests; the unmodified creators
need not have generated these malformed records. No OT or full bank work.
"""
import sys,os,math,copy
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,os.environ.get('PHASEB_ROOT',str(Path(__file__).resolve().parents[1])))
from step1_engine.w2_stop import w2_stop,w2_validate
from step1_engine.bootstrap_plan import BootstrapPlan,ClusterUID
from step1_engine.errors import InputContractError
from step1_engine import serialization as ser

def fixture():
 null={n:np.full(1000,.2) for n in (2000,5000)};obs={n:{s:.1 for s in range(3)} for n in null}
 return w2_stop(null,obs,'x')

def test_stop_reason_must_match_registered_state():
 st=fixture();st.stop_reason='UNREGISTERED'
 with pytest.raises(InputContractError):st.validate()

def test_trace_cannot_skip_first_satisfied_stop():
 null={n:np.r_[np.full(400,.1),np.full(600,.3)] for n in (2000,5000)};obs={n:{s:.2 for s in range(3)} for n in null}
 st=w2_stop(null,obs,'x');trace=[];prev=None
 for B in (200,400,600,800):
  q={n:float(np.quantile(x[:B],.99,method='higher')) for n,x in null.items()}
  ind=tuple((n,s,obs[n][s]>q[n]) for n in sorted(obs) for s in sorted(obs[n]))
  trace.append(dict(B=B,q99=q,indicator=ind,relative_change=None if prev is None else max(abs(q[n]-prev[n])/prev[n] for n in q),relative_change_state='first_level' if prev is None else 'ok'));prev=q
 st.trace=trace;st.B_final=800
 with pytest.raises(InputContractError):st.validate()

def test_plan_rng_group_must_match_UID_group():
 us=[ClusterUID(1,200,7,0,i) for i in range(4)];p=BootstrapPlan.build('a',0,{0:us},20,5)
 p.rng_keys[0][3]=888
 with pytest.raises(InputContractError):p.validate()

def test_serialized_duplicate_object_key_must_not_overwrite():
 with pytest.raises(InputContractError):ser.loads('{"audit":"fail","audit":"pass"}')
