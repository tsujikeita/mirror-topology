"""Independent stage12 contracts. All inputs here are synthetic state fixtures.
No claim of an executed scientific 12-position family evaluation. Deferred bank
binding/calibration integration is not required by these tests.
"""
import copy, hashlib, os, sys
from pathlib import Path
from dataclasses import replace
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(ROOT))
from step1_engine.stage12 import generate_twelve,verify_twelve,TwelvePositionManifest,transition_after_three,after_twelve
from step1_engine.errors import InputContractError
from step1_engine import serialization as ser
A=np.array([[.11278702805018147],[.04504442885635738],[.17608175443077442]])
@pytest.fixture(scope='module')
def manifest():return generate_twelve('E7','L1.00',A)
def source3():
 return dict(family='E7',size_id='L1.00',truths=dict(support=True,strong=False,unsupported=False),decision=dict(technical_status='ok'),precision=dict(state='pass'),evidence=dict(coverage_ok=True))
def trans(man):return transition_after_three('E7','L1.00',source3(),dict(state='position-sensitive',expand=True),man)
def result12(man):
 return dict(family='E7',size_id='L1.00',evidence=dict(stage='12-position',coverage_ok=True,twelve_manifest_sha256=man.sha256),decision=dict(technical_status='ok',display_label='support'),precision=dict(state='pass'),truths=dict(support=True,strong=False,unsupported=False))
def no_final(fn):
 try:r=fn()
 except InputContractError:return
 assert r['final_classification_available'] is not True,r

def test_e7_generator_reference_and_roundtrip(manifest):
 assert [round(p[0],4) for p in manifest.added]==[.23,.0789,.1444,.203,.02,.062,.0958,.1286,.1602]
 assert manifest.points[:3]==A.tolist()
 assert verify_twelve(TwelvePositionManifest(**ser.loads(ser.dumps(manifest.as_dict()))))

def test_direct_points_edit_is_rejected(manifest):
 m=copy.deepcopy(manifest);m.points[5][0]+=.0001
 with pytest.raises(InputContractError):verify_twelve(m)

@pytest.mark.parametrize('field,value',[
 ('added',[[-999.]]*9),('generator',{'kind':'random','grid_resolution':1.,'distance':'wrong','candidates':1}),
 ('min_sep_registered',999.),('min_pairwise',999.)])
def test_manifest_redundant_fields_must_match_payload(manifest,field,value):
 with pytest.raises(InputContractError):verify_twelve(replace(manifest,**{field:value}))

def test_transition_preserves_original_bytes_and_hash(manifest):
 s=source3();before=ser.dumps(s)
 t=transition_after_three('E7','L1.00',s,dict(state='position-sensitive',expand=True),manifest)
 assert ser.dumps(s)==before
 assert t.three_position_result_sha256==hashlib.sha256(before.encode()).hexdigest()
 assert t.twelve_manifest_sha256==manifest.sha256

@pytest.mark.parametrize('family,size',[('E8','L1.00'),('E7','L1.50')])
def test_manifest_identity_matches_requested_transition(manifest,family,size):
 s=source3();s.update(family=family,size_id=size)
 with pytest.raises(InputContractError):transition_after_three(family,size,s,dict(state='position-sensitive',expand=True),manifest)

def test_three_result_family_matches_transition(manifest):
 s=source3();s['family']='E8'
 with pytest.raises(InputContractError):transition_after_three('E7','L1.00',s,dict(state='position-sensitive',expand=True),manifest)

def test_transition_rejects_unknown_position_state():
 with pytest.raises(InputContractError):transition_after_three('E7','L1.00',source3(),dict(state='typo',expand=False),None)

def test_transition_checks_state_expand_consistency(manifest):
 with pytest.raises(InputContractError):transition_after_three('E7','L1.00',source3(),dict(state='position-sensitive',expand=False),manifest)

def test_three_technical_failure_is_not_final_at_three():
 s=source3();s['decision']['technical_status']='technical_fail'
 try:t=transition_after_three('E7','L1.00',s,dict(state='not-expanded',expand=False),None)
 except InputContractError:return
 assert t.status=='technical_fail'

def test_after_twelve_precision_failure_remains_nonfinal(manifest):
 r=result12(manifest);r['precision']['state']='precision-unresolved'
 no_final(lambda:after_twelve(trans(manifest),r,'not-expanded'))

def test_after_twelve_core_technical_failure_remains_nonfinal(manifest):
 r=result12(manifest);r['decision']['technical_status']='technical_fail'
 no_final(lambda:after_twelve(trans(manifest),r,'not-expanded'))

def test_after_twelve_coverage_failure_remains_nonfinal(manifest):
 r=result12(manifest);r['evidence']['coverage_ok']=False
 no_final(lambda:after_twelve(trans(manifest),r,'not-expanded'))

def test_after_twelve_declared_new_technical_state_is_not_ignored(manifest):
 no_final(lambda:after_twelve(trans(manifest),result12(manifest),'technical_fail'))

def test_unregistered_twelve_transition_cannot_complete(manifest):
 t=transition_after_three('E7','L1.00',source3(),dict(state='position-unresolved',expand=False),None)
 assert t.twelve_manifest_sha256 is None
 no_final(lambda:after_twelve(t,result12(manifest),'not-expanded'))

def test_twelve_result_family_matches_transition(manifest):
 r=result12(manifest);r['family']='E8'
 with pytest.raises(InputContractError):after_twelve(trans(manifest),r,'not-expanded')

def test_twelve_result_manifest_binding_matches_transition(manifest):
 r=result12(manifest);r['evidence']['twelve_manifest_sha256']='0'*64
 with pytest.raises(InputContractError):after_twelve(trans(manifest),r,'not-expanded')
