"""Small contract tests for stage12 consumption; no physical 12-position evaluation.
Invalid transitions are produced with ordinary dataclass reconstruction. These
checks concern schema/internal consistency, not authenticity or arbitrary forgery.
"""
import os,sys,copy,hashlib
from pathlib import Path
from dataclasses import replace
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]));sys.path.insert(0,str(ROOT))
from step1_engine.stage12 import generate_twelve,verify_twelve,transition_after_three,after_twelve,StageTransition
from step1_engine.errors import InputContractError
from step1_engine import serialization as ser
A=np.array([[.11278702805018147],[.04504442885635738],[.17608175443077442]])
@pytest.fixture(scope='module')
def m():return generate_twelve('E7','L1.00',A)
def source(tech='ok'):
 return dict(family='E7',size_id='L1.00',decision=dict(technical_status=tech),precision=dict(state='pass'),truths=dict(support=True,strong=False,unsupported=False),evidence=dict(coverage_ok=True))
def trans(m):return transition_after_three('E7','L1.00',source(),dict(state='position-sensitive',expand=True),m)
def result(m):
 return dict(family='E7',size_id='L1.00',decision=dict(technical_status='ok'),precision=dict(state='pass'),truths=dict(support=True,strong=False,unsupported=False),evidence=dict(stage='12-position',coverage_ok=True,twelve_manifest_sha256=m.sha256))
def test_normal_transition_roundtrip(m):
 t=trans(m);d=StageTransition(**ser.loads(ser.dumps(t.as_dict())))
 assert after_twelve(d,result(m),'not-expanded')==after_twelve(t,result(m),'not-expanded')

def test_factory_phase_state_matrix(m):
 states={'position-sensitive':('twelve_registered',True),'not-expanded':('final_at_3',False),'position-unresolved':('provisional_unresolved',False),'technical_fail':('technical_fail',False)}
 for tech in ('ok','technical_fail'):
  for st,(phase,ex) in states.items():
   t=transition_after_three('E7','L1.00',source(tech),dict(state=st,expand=ex),m)
   assert t.phase==('technical_fail' if tech=='technical_fail' else phase)
   if t.phase!='twelve_registered':
    with pytest.raises(InputContractError):after_twelve(t,result(m),'not-expanded')

def test_coverage_precision_and_technical_remain_blocking(m):
 for field,value in [('coverage',False),('precision','precision-unresolved'),('precision','cv_undefined'),('precision','technical_fail'),('decision','technical_fail')]:
  r=result(m)
  if field=='coverage':r['evidence']['coverage_ok']=value
  else:r[field]['state' if field=='precision' else 'technical_status']=value
  v=after_twelve(trans(m),r,'not-expanded');assert v['final_classification_available'] is False

def test_scope_does_not_claim_calibration_usable(m):
 r=after_twelve(trans(m),result(m),'not-expanded');assert 'calibration' in r['scope'] and 'NOT verified' in r['scope']

def test_manifest_stored_fields_still_bound(m):
 for f,v in [('added',[[-999.]]*9),('min_sep_registered',999.),('min_pairwise',999.),('generator',{'kind':'random'})]:
  with pytest.raises(InputContractError):verify_twelve(replace(m,**{f:v}))

def test_original_three_result_not_modified(m):
 s=source();b=ser.dumps(s);t=transition_after_three('E7','L1.00',s,dict(state='position-sensitive',expand=True),m)
 assert ser.dumps(s)==b and t.three_position_result_sha256==hashlib.sha256(b.encode()).hexdigest()

@pytest.mark.parametrize('field,value',[
 ('expand','False'),('expand',1),('three_technical_status','technical_fail'),('three_technical_status','typo'),
 ('position_state','not-expanded'),('position_state','technical_fail'),('three_position_result_sha256',''),('three_position_result_sha256','not-a-sha')])
def test_restored_transition_schema_checked_at_consumption(m,field,value):
 t=replace(trans(m),**{field:value})
 with pytest.raises(InputContractError):after_twelve(t,result(m),'not-expanded')

@pytest.mark.parametrize('size',['',None,1.0])
def test_transition_size_is_nonempty_string(size):
 s=source();s['size_id']=size
 with pytest.raises(InputContractError):transition_after_three('E7',size,s,dict(state='not-expanded',expand=False),None)

def test_raw_transition_mapping_is_not_silently_accepted(m):
 with pytest.raises(InputContractError):after_twelve(trans(m).as_dict(),result(m),'not-expanded')
