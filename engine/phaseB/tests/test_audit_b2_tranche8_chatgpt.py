"""Independent tranche8 contracts. All banks are synthetic; distance is explicitly
injected and NOT claimed to be exact OT. Run with PHASEB_ROOT pointing at package.
Changing result/manifest copies tests binding and numerical consistency, not a
cryptographic attack against an externally fixed signed digest.
"""
import os,sys,copy
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path[:0]=[str(ROOT),str(Path(__file__).resolve().parent)]
from probe_manifest import fixture
from step1_engine.positions import PositionBank,position_decision
from step1_engine.w2_manifest import build_w2_manifest,verify_w2_manifest,W2Manifest
from step1_engine import serialization as ser
from step1_engine.errors import InputContractError

@pytest.fixture(scope='module')
def base():
 ps,iso,r=fixture()
 assert r['validation']['state']=='valid' and r['trigger'] is True
 return ps,iso,r

def fresh(base):
 ps,iso,rr=base;r=copy.deepcopy(rr)
 return ps,iso,r,build_w2_manifest('E7','L1.00',ps,iso,r)

def test_normal_roundtrip(base):
 ps,iso,r,m=fresh(base)
 assert verify_w2_manifest(m,ps,iso,r)['verified']
 m2=W2Manifest(**ser.loads(ser.dumps(m.as_dict())))
 assert verify_w2_manifest(m2,ps,iso,ser.loads(ser.dumps(r)))['verified']

def test_injected_distance_is_rejected_with_registered_m(base):
 ps,iso,r,m=fresh(base);assert m.m==100
 with pytest.raises(InputContractError):verify_w2_manifest(m,ps,iso,r,require_registered_distance=True)

def test_existing_manifest_rejects_live_bank_drift(base):
 ps,iso,r,m=fresh(base)
 other=[PositionBank(p.position_id,p.Tw+1e-3,p.cid,p.m) for p in ps]
 with pytest.raises(InputContractError):verify_w2_manifest(m,other,iso,r)

def test_existing_manifest_rejects_null_array_drift(base):
 ps,iso,r,m=fresh(base);r['evidence']['null'][2000]['values'][3]+=1e-3
 with pytest.raises(InputContractError):verify_w2_manifest(m,ps,iso,r)

def test_result_without_evidence_not_bindable(base):
 ps,iso,r,m=fresh(base)
 with pytest.raises(InputContractError):build_w2_manifest('E7','L1.00',ps,iso,dict(stop=r['stop'],validation=r['validation']))

@pytest.mark.parametrize('target',['trigger','observed','observed_evidence','stop','null_q99','whitening','master_seed','bounds'])
def test_returned_result_fields_must_agree_with_manifest(base,target):
 ps,iso,r,m=fresh(base);r2=copy.deepcopy(r)
 if target=='trigger':r2['trigger']=False
 elif target=='observed':r2['observed'][2000][0]+=10.
 elif target=='observed_evidence':r2['evidence']['observed'][2000][0]['W2_max']+=10.
 elif target=='stop':r2['stop']={'corrupt':'missing'}
 elif target=='null_q99':r2['null_q99'][2000]+=.01
 elif target=='whitening':r2['evidence']['whitening']={'source':'different'}
 elif target=='master_seed':r2['evidence']['master_seed']+=1
 else:r2['evidence']['bounds']={'obs_bounds':None,'delta_q99_bound':None}
 with pytest.raises(InputContractError):verify_w2_manifest(m,ps,iso,r2)

def test_old_result_cannot_be_bound_to_other_live_banks(base):
 ps,iso,r,m=fresh(base)
 other=[PositionBank(p.position_id,p.Tw+3*(i+1),p.cid,p.m) for i,p in enumerate(ps)]
 # New manifest must compare with identity recorded AT DISTANCE EXECUTION.
 with pytest.raises(InputContractError):
  mm=build_w2_manifest('E7','L1.00',other,iso,r)
  verify_w2_manifest(mm,other,iso,r)

def test_injected_distance_cannot_be_relabelled_as_exact(base):
 ps,iso,r,m=fresh(base);m.distance_kind='exact_pot_w2'
 with pytest.raises(InputContractError):verify_w2_manifest(m,ps,iso,r,require_registered_distance=True)

def test_mutating_result_validation_does_not_mutate_manifest_approval(base):
 ps,iso,r,m=fresh(base);r['validation']['trigger']=False
 with pytest.raises(InputContractError):verify_w2_manifest(m,ps,iso,r)

def test_selection_bounds_recomputed_not_just_present(base):
 ps,iso,r,m=fresh(base);r['evidence']['bounds']['obs_bounds'][2000][0]=1000.
 with pytest.raises(InputContractError):verify_w2_manifest(m,ps,iso,r)

def test_empty_bound_dicts_cannot_support_valid_state(base):
 ps,iso,r,m=fresh(base);r['evidence']['bounds']={'obs_bounds':{},'delta_q99_bound':{}}
 with pytest.raises(InputContractError):
  mm=build_w2_manifest('E7','L1.00',ps,iso,r)
  verify_w2_manifest(mm,ps,iso,r)

@pytest.mark.parametrize('mode',['one_missing','all_missing'])
def test_null_manifest_exact_inventory(base,mode):
 ps,iso,r,m=fresh(base)
 if mode=='one_missing':m.null_sha256.pop(5000)
 else:m.null_sha256.clear()
 with pytest.raises(InputContractError):verify_w2_manifest(m,ps,iso,r)

def test_every_trace_quantile_must_reproduce_from_its_prefix(base):
 ps,iso,r,m=fresh(base);sd=m.stop
 sd['trace'][0]['q99']={n:v*.99 for n,v in sd['trace'][0]['q99'].items()}
 for i in range(1,len(sd['trace'])):
  a,b=sd['trace'][i-1],sd['trace'][i]
  b['relative_change']=max(abs(b['q99'][n]-a['q99'][n])/a['q99'][n] for n in a['q99'])
 with pytest.raises(InputContractError):verify_w2_manifest(m,ps,iso,r)

def test_null_blocks_must_remain_disjoint(base):
 ps,iso,r,m=fresh(base)
 r['evidence']['null'][2000]['blocks'][0][1]=r['evidence']['null'][2000]['blocks'][0][0]
 with pytest.raises(InputContractError):verify_w2_manifest(m,ps,iso,r)

def test_observed_pairwise_must_be_nonnegative_and_match_max(base):
 ps,iso,r,m=fresh(base);r['evidence']['observed'][2000][0]['pairwise']['P1P2']=-1.
 with pytest.raises(InputContractError):verify_w2_manifest(m,ps,iso,r)
