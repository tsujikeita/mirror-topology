"""Focused audit proposals for B-2 tranche2 (not an official engine release).
Run PHASEB_ROOT=/path/to/phaseB OPENBLAS_NUM_THREADS=1 python -m pytest -q this_file.py.
Small artificial banks and explicit fault injection; no CMB/OT/full-grid run.
"""
from pathlib import Path
import os,sys,copy,importlib.util,json
from unittest.mock import patch
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(ROOT))
s=importlib.util.spec_from_file_location('audit_b2_fixture',ROOT/'tests/test_b2.py')
tb=importlib.util.module_from_spec(s);s.loader.exec_module(tb)
import step1_engine.orchestrator as o
from step1_engine.errors import InputContractError
from step1_engine.density import logD_with_ci
from step1_engine.truth import TECH,UNKNOWN
from step1_engine.serialization import loads,dumps

@pytest.fixture(scope='module')
def baseline():return tb.build_fixture()
@pytest.fixture(scope='module')
def strong():return tb.build_fixture(shift=np.array([1.4,1.3]))

def test_baseline_support_remains_valid(baseline):
 r=o.evaluate_family(*baseline['E7'],*tb.THR)
 assert r.precision['state']=='pass' and r.truths['support'] is True
 assert r.logD['ci'] is None

def test_baseline_strong_remains_valid(strong):
 r=o.evaluate_family(*strong['E7'],*tb.THR)
 assert r.truths['strong'] is True and r.logD['ci']['counts']['technical_invalid']==0

def test_native_absent_does_not_become_strong(strong):
 r=o.evaluate_family(strong['E7'][0],None,*tb.THR)
 assert r.truths['support'] is True and r.truths['strong']==UNKNOWN

@pytest.mark.parametrize('variant',['same_matched_object','wrong_family','wrong_role'])
def test_native_identity_checked_before_strong(strong,variant):
 a,b=copy.deepcopy(strong['E7'])
 if variant=='same_matched_object':b=a
 elif variant=='wrong_family':
  b.family='E8'
  for c in b.configs:c.family='E8'
 else:
  for c in b.configs:c.system='matched'
 with pytest.raises(InputContractError):o.evaluate_family(a,b,*tb.THR)

def test_native_unresolved_coverage_cannot_certify_strong(strong):
 a,b=copy.deepcopy(strong['E7']);b.coverage_ok=False
 try:r=o.evaluate_family(a,b,*tb.THR)
 except InputContractError:return  # inconsistent matched/native coverage may be rejected at intake
 assert r.truths['strong'] in (UNKNOWN,TECH), 'native coverage unavailable must not certify strong'

def test_component_nonfinite_bootstrap_density_not_hidden_by_mixture(strong):
 f=copy.deepcopy(strong['E7'][0]);w=f.validate()
 target=f.fitting[f.configs[0].evaluation_id].X_model;orig=o.kde_logpdf_weighted;injected=False
 def fail_one(X,rows,pts,fs=1.):
  nonlocal injected
  if X is target and not np.all(np.asarray(rows)==1) and not injected:
   injected=True;return np.array([-np.inf])
  return orig(X,rows,pts,fs)
 try:
  with patch.object(o,'kde_logpdf_weighted',side_effect=fail_one):
   r=o._family_logD(f,np.array(tb.THR),w,True)
 except InputContractError:
  assert injected;return
 assert injected
 assert r[1].math_state=='technical_fail', 'a failed required component cannot be dropped as zero density'
 assert r[1].counts['technical_invalid']==1 and sum(r[4]['invalid_mask'])==1

@pytest.mark.parametrize('impl',['weighted','literal'])
def test_logD_one_coordinate_threshold_rejected(impl):
 rng=np.random.default_rng(77);K,m,B=30,4,10
 X=rng.normal(size=(K*m,2));Y=X+.2;cid=np.repeat(np.arange(K),m)
 M=np.stack([np.bincount(rng.integers(K,size=K),minlength=K) for _ in range(B)])
 with pytest.raises(InputContractError):logD_with_ci(X,cid,Y,cid,[0.],M,M,impl=impl)

def test_logD_multiple_thresholds_not_silently_first_only():
 rng=np.random.default_rng(77);K,m,B=30,4,10
 X=rng.normal(size=(K*m,2));Y=X+.2;cid=np.repeat(np.arange(K),m)
 M=np.stack([np.bincount(rng.integers(K,size=K),minlength=K) for _ in range(B)])
 with pytest.raises(InputContractError):logD_with_ci(X,cid,Y,cid,[[0.,0.],[1.,1.]],M,M)

def test_normal_result_evidence_strict_json_roundtrip(strong):
 r=o.evaluate_family(*strong['E7'],*tb.THR)
 d=loads(dumps(r.as_dict()))
 assert set(d['evidence']['matched']['per_seed'])==set(range(5))
 assert len(d['evidence']['cis_all_seeds'])==5
 assert len(d['evidence']['logD']['replicate_values'])==r.logD['ci']['B']
 assert d['truths']==r.truths
 for seed in range(5):
  a=r.evidence['matched']['per_seed'][seed];b=d['evidence']['matched']['per_seed'][seed]
  np.testing.assert_array_equal(a['num'],b['num']);np.testing.assert_array_equal(a['den'],b['den'])
