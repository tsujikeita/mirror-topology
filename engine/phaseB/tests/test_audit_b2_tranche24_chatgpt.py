"""Timing-helper contract tests, NOT exact OT correctness or official runtime.
Fake solver outputs deliberately exercise whether a failed solve may be timed
as a successful exact solve. E2 uses registered axis length with fake distance
and a deterministic clock, to verify how many lattice rows are measured.
"""
import os,sys,types,warnings
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]));sys.path.insert(0,str(ROOT))
from step1_engine import performance as perf
from step1_engine import observers12 as ob, stage12
from step1_engine.errors import InputContractError

@pytest.mark.parametrize('failure',['warning','nonoptimal'])
def test_ot_timing_requires_successful_exact_solve(monkeypatch,failure):
 ot=types.ModuleType('ot');ot.dist=lambda a,b,metric:np.zeros((len(a),len(b)))
 def emd2(a,b,c,**kw):
  if failure=='warning':warnings.warn('synthetic iteration limit',UserWarning)
  val=[4.,{'warning':None,'result_code':3 if failure=='nonoptimal' else 1}]
  return val if kw.get('log') else 4.
 ot.emd2=emd2;monkeypatch.setitem(sys.modules,'ot',ot)
 with pytest.raises((InputContractError,FloatingPointError)):
  perf.measure_ot_unit(12,1)

def test_ot_timing_accepts_normal_control(monkeypatch):
 ot=types.ModuleType('ot');ot.dist=lambda a,b,metric:np.zeros((len(a),len(b)))
 ot.emd2=lambda a,b,c,**kw: [4.,{'warning':None,'result_code':1}] if kw.get('log') else 4.
 monkeypatch.setitem(sys.modules,'ot',ot)
 assert perf.measure_ot_unit(12,1)>=0

@pytest.mark.parametrize('rows',[1,250,400])
def test_e2_times_exactly_requested_rows(monkeypatch,rows):
 sizes=[]
 def excl(a):sizes.append(len(a));return a
 monkeypatch.setattr(stage12,'_exclusion',lambda fam,a:excl(a))
 monkeypatch.setattr(ob,'dist_torus_halfturn',lambda a,p:np.zeros(len(a)))
 clock=iter([0.,2.]);monkeypatch.setattr(perf.time,'perf_counter',lambda:next(clock))
 out=perf.measure_e2_pass_unit(rows)
 assert sum(sizes)==rows*10001,('measured_candidates',sum(sizes),'requested',rows*10001)
 assert np.isclose(out,2.*10001/rows)
