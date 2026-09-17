"""Tranche19 audit contracts for EXISTING entry points.
Scope: configuration metadata consistency and finite geometry/cache fields only.
Not a test of physical covariance, cache generation, official environment, or full
production source authentication. No submission is modified.
Run with PHASEB_ROOT set to the submitted phaseB directory.
"""
from pathlib import Path
from dataclasses import replace
import os,sys,copy,hashlib
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]));sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from step1_engine import serialization as ser
from step1_engine.errors import InputContractError
from step1_engine.grid_registry import load_registry
from step1_engine.grid_manifest import (build_configuration_manifest,verify_manifest_against_a7,verify_cov_manifest,ConfigurationSpec,ConfigurationManifest,cache_key)
A6=ROOT/'tests/assets/a6_observer_design_points.json'; A7=ROOT/'tests/assets/a7_circle_geometry.csv'
@pytest.fixture
def man(): return build_configuration_manifest(load_registry(str(A7),str(A6)))
def c7(man): return next(x for x in man.configurations if x.family=='E7' and x.size_id=='L1.00' and x.position_index==0)
def sidecar(c):return {'manifest':{'topology':c.family,'params':copy.deepcopy(c.shape_params),'x0':list(c.x0_CT)},'cov_array_sha256':'a'*64,'cov_file_sha256':'b'*64}

def test_normal_manifest_matches_a7_and_registered_count(man):
 assert man.n_configurations==30 and len(man.by_id())==30
 assert verify_manifest_against_a7(man,str(A7))=={'checked':30,'ok':True}
 for c in man.configurations:
  assert c.x0_CT==[-x for x in c.r_obs]
  assert c.cache_key==cache_key(c.family,c.shape_params,c.x0_CT)
  assert c.weight==pytest.approx(1/3 if c.family=='E1' else 1/9)

def test_normal_manifest_strict_json_roundtrip(man):
 d=ser.loads(ser.dumps(man.as_dict()));d['configurations']=[ConfigurationSpec(**x) for x in d['configurations']]
 restored=ConfigurationManifest(**d)
 assert restored.payload_sha()==man.manifest_sha256
 assert verify_manifest_against_a7(restored,str(A7))['checked']==30

def test_existing_coordinate_drift_rejection(man):
 c7(man).r_obs[0]+=.001
 with pytest.raises(InputContractError): verify_manifest_against_a7(man,str(A7))

@pytest.mark.parametrize('case',['empty','one_only','duplicate_id','missing_sha','wrong_x0_sign','short_r_obs','nan_r_obs','negative_weight','wrong_cache_key','wrong_geometric_status'])
def test_inconsistent_full_configuration_manifest_is_not_verified(man,case):
 c=c7(man)
 if case=='empty':man.configurations=[]
 elif case=='one_only':man.configurations=man.configurations[:1]
 elif case=='duplicate_id':man.configurations[1].config_id=man.configurations[0].config_id
 elif case=='missing_sha':man.manifest_sha256=''
 elif case=='wrong_x0_sign':c.x0_CT=c.r_obs.copy()
 elif case=='short_r_obs':c.r_obs=c.r_obs[:1]
 elif case=='nan_r_obs':c.r_obs[0]=float('nan')
 elif case=='negative_weight':c.weight=-1.
 elif case=='wrong_cache_key':c.cache_key='0'*64
 elif case=='wrong_geometric_status':c.circle_status['geometric_status']='circles_geometrically_present'
 with pytest.raises(InputContractError): verify_manifest_against_a7(man,str(A7))

def test_normal_covariance_metadata_match(man):
 c=c7(man);assert verify_cov_manifest(c,sidecar(c))['bound']

@pytest.mark.parametrize('where,value',[('param',float('nan')),('x0',float('nan')),('param',float('inf')),('x0',float('inf'))])
def test_nonfinite_covariance_geometry_is_rejected(man,where,value):
 c=c7(man);d=sidecar(c)
 if where=='param':d['manifest']['params']['LAy']=value
 else:d['manifest']['x0'][1]=value
 with pytest.raises(InputContractError): verify_cov_manifest(c,d)

@pytest.mark.parametrize('field',['cov_array_sha256','cov_file_sha256'])
def test_covariance_sha_must_be_hex(man,field):
 c=c7(man);d=sidecar(c);d[field]='z'*64
 with pytest.raises(InputContractError): verify_cov_manifest(c,d)

@pytest.mark.parametrize('case',['short_x0','bad_cache_key'])
def test_configuration_spec_is_checked_before_cache_matching(man,case):
 c=c7(man);d=sidecar(c)
 if case=='short_x0':c.x0_CT=c.x0_CT[:1]
 else:c.cache_key='wrong'
 with pytest.raises(InputContractError): verify_cov_manifest(c,d)

@pytest.mark.parametrize('field',['topology','params','x0'])
def test_normal_geometry_mismatch_is_rejected(man,field):
 c=c7(man);d=sidecar(c)
 if field=='topology':d['manifest'][field]='E8'
 elif field=='params':d['manifest']['params']['LAy']=.3
 else:d['manifest']['x0'][1]+=.1
 with pytest.raises(InputContractError): verify_cov_manifest(c,d)

def test_supplied_covariance_file_sha_checked(man,tmp_path):
 c=c7(man);d=sidecar(c);p=tmp_path/'synthetic.npy';x=np.eye(21,dtype=np.complex128);np.save(p,x)
 d['cov_file_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();d['cov_array_sha256']=hashlib.sha256(x.tobytes()).hexdigest()
 assert verify_cov_manifest(c,d,str(p))['bound']
 p.write_bytes(p.read_bytes()+b'drift')
 with pytest.raises(InputContractError): verify_cov_manifest(c,d,str(p))

def test_generic_diagnostic_spec_is_not_forced_into_firstwave_slice(man):
 # The submitted API explicitly permits a diagnostic spec derived from an A11 entry.
 c=copy.deepcopy(c7(man));c.config_id=0;c.size_id='tilt';c.shape_params['LAy']=.3;c.reduced_coords=[];c.weight=0.;c.circle_status={}
 c.cache_key=cache_key(c.family,c.shape_params,c.x0_CT)
 assert verify_cov_manifest(c,sidecar(c))['bound']
 with pytest.raises(InputContractError):verify_cov_manifest(c7(man),sidecar(c))
