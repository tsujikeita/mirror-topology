"""Focused tests of the NEW plan_io boundary. All data are synthetic.
Run: PHASEB_ROOT=/path/to/phaseB OPENBLAS_NUM_THREADS=1 python -m pytest -q this_file.py
A malformed record is saved with its ACTUAL new file SHA. These tests check schema,
not cryptographic authenticity or resistance to a coordinated forgery.
"""
from pathlib import Path
import os,sys,copy,hashlib
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from step1_engine.bootstrap_plan import BootstrapPlan,FittingPlan
from step1_engine.plan_io import plan_to_dict,plan_from_dict,write_plans,read_plans
from step1_engine.types import ClusterUID
from step1_engine.twelve_eval import _same_evaluation_plan,_same_fit_plan,assemble_all_sizes
from step1_engine.errors import InputContractError
from step1_engine import serialization as ser

def build(kind):
 if kind=='eval':
  st={b:[ClusterUID(1,200,11,b,i) for i in range(k)] for b,k in [(0,5),(1,7)]}
  return BootstrapPlan.build('eval0',0,st,8,140028)
 return FittingPlan.build('fit0',1,21,0,5,8,140029)
def same(a,b):
 return _same_evaluation_plan(a,b) if isinstance(a,BootstrapPlan) else _same_fit_plan(a,b)
def array(d,kind):return d['multiplicities'][0] if kind=='eval' else d['multiplicities']
def encoded(p):return ser.loads(ser.dumps(plan_to_dict(p)))
def read_record(d,tmp_path):
 body=ser.dumps({'kind':'PlanSet','plans':{'p':d}}).encode('utf-8')
 p=tmp_path/'edited.json';p.write_bytes(body)
 return read_plans(str(p),hashlib.sha256(body).hexdigest())['p']

@pytest.mark.parametrize('kind',['eval','fit'])
def test_normal_roundtrip_is_content_and_dtype_preserving(kind,tmp_path):
 p=build(kind);path=str(tmp_path/'ok.json');sha=write_plans({'p':p},path)
 q=read_plans(path,sha)['p'];assert p is not q and same(p,q)
 assert encoded(p)==encoded(q)

@pytest.mark.parametrize('kind',['eval','fit'])
def test_fractional_multiplicity_is_not_rounded_back_to_valid_plan(kind,tmp_path):
 d=encoded(build(kind));a=array(d,kind);a[0][0]+=.75
 with pytest.raises(InputContractError):read_record(d,tmp_path)

@pytest.mark.parametrize('kind',['eval','fit'])
def test_negative_fractional_zero_is_not_silently_restored(kind,tmp_path):
 d=encoded(build(kind));a=array(d,kind);pos=next((r,c) for r,row in enumerate(a) for c,v in enumerate(row) if v==0);a[pos[0]][pos[1]]=-.9
 with pytest.raises(InputContractError):read_record(d,tmp_path)

@pytest.mark.parametrize('kind',['eval','fit'])
def test_boolean_multiplicity_is_not_an_integer_count(kind,tmp_path):
 d=encoded(build(kind));a=array(d,kind);r,c=next((r,c) for r,row in enumerate(a) for c,v in enumerate(row) if v==1);a[r][c]=True
 with pytest.raises(InputContractError):read_record(d,tmp_path)

@pytest.mark.parametrize('kind',['eval','fit'])
def test_fractional_seed_is_not_rounded(kind,tmp_path):
 d=encoded(build(kind));d['seed_id']=.75
 with pytest.raises(InputContractError):read_record(d,tmp_path)

@pytest.mark.parametrize('kind',['eval','fit'])
def test_fractional_rng_component_is_not_rounded(kind,tmp_path):
 d=encoded(build(kind));k=d['rng_keys'][0] if kind=='eval' else d['rng_key'];k[0]+=.75
 with pytest.raises(InputContractError):read_record(d,tmp_path)

def test_fractional_cluster_uid_is_not_rounded(tmp_path):
 d=encoded(build('eval'));d['strata'][0][0][4]=.75
 with pytest.raises(InputContractError):read_record(d,tmp_path)

@pytest.mark.parametrize('kind,field,value',[('eval','replicates',8.75),('fit','K',5.75)])
def test_declared_dimensions_not_truncated(kind,field,value,tmp_path):
 d=encoded(build(kind));d[field]=value
 with pytest.raises(InputContractError):read_record(d,tmp_path)

@pytest.mark.parametrize('kind',['eval','fit'])
def test_none_plan_name_not_made_into_string(kind,tmp_path):
 d=encoded(build(kind));d['plan_id']=None
 with pytest.raises(InputContractError):read_record(d,tmp_path)

@pytest.mark.parametrize('kind',['eval','fit'])
def test_integer_row_edit_detected_even_with_matching_recomputed_array_sha(kind,tmp_path):
 d=encoded(build(kind));a=array(d,kind)
 r,c=next((r,c) for r,row in enumerate(a) for c,v in enumerate(row) if v>0);j=(c+1)%len(a[r]);a[r][c]-=1;a[r][j]+=1
 sh=hashlib.sha256(np.asarray(a,np.int64).tobytes()).hexdigest()
 if kind=='eval':d['multiplicities_sha256'][0]=sh
 else:d['multiplicities_sha256']=sh
 with pytest.raises(InputContractError):read_record(d,tmp_path)

def test_file_sha_mismatch_is_rejected(tmp_path):
 path=str(tmp_path/'ok.json');write_plans({'p':build('eval')},path)
 with pytest.raises(InputContractError):read_plans(path,'0'*64)

def test_distinct_keys_never_collapsed_by_writer(tmp_path):
 path=str(tmp_path/'collision.json')
 try:sha=write_plans({1:build('eval'),'1':build('fit')},path)
 except InputContractError:return  # explicit rejection is an acceptable policy
 got=read_plans(path,sha)
 assert len(got)==2,'writer silently lost one of two plans'

@pytest.mark.parametrize('kind',['eval','fit'])
def test_noncanonical_integer_dtype_roundtrips_or_is_rejected_before_writing(kind,tmp_path):
 p=build(kind)
 if kind=='eval':p.multiplicities={b:a.astype(np.int32) for b,a in p.multiplicities.items()}
 else:p.multiplicities=p.multiplicities.astype(np.int32)
 assert p.validate() is True
 path=str(tmp_path/'int32.json')
 try:sha=write_plans({'p':p},path)
 except InputContractError:
  assert not Path(path).exists()
  return  # a declared int64-only storage contract is also valid
 q=read_plans(path,sha)['p']
 assert same(p,q),'accepted writer output must preserve dtype-sensitive plan identity'

def test_restored_shared_five_seed_plans_connect_to_full_family(tmp_path):
 from dataclasses import replace
 from test_b2_tranche14 import TwelveFixture
 fx=TwelveFixture(K=20,m=2,Kf=10,mf=3,B=12)
 ps={f'e{s}':p for s,p in fx.plans.items()}|{f'f{s}':p for s,p in fx.fplans.items()}
 path=str(tmp_path/'full.json');sh=write_plans(ps,path);rest=read_plans(path,sh)
 inputs={}
 for sz,pair in fx.inputs.items():
  inputs[sz]=tuple(replace(f,plans={s:copy.deepcopy(rest[f'e{s}']) for s in range(5)},fit_plans={s:copy.deepcopy(rest[f'f{s}']) for s in range(5)}) for f in pair)
 fm,fn,i=assemble_all_sizes(inputs,fx.manifests,fx.maps,{s:.5 for s in fx.sizes},fx.nmaps,expected_sizes=fx.sizes)
 assert i['n_configs']==24
 fm.validate();fn.validate()
 assert all(same(fm.plans[s],fx.plans[s]) and same(fn.fit_plans[s],fx.fplans[s]) for s in range(5))

def test_fractional_tagged_batch_key_rejected_before_generic_decoder(tmp_path):
 import json
 d=plan_to_dict(build('eval'))
 raw=json.loads(ser.dumps({'kind':'PlanSet','plans':{'p':d}}))
 raw['plans']['p']['strata']['__intkeys__'][0][0]=.75
 body=json.dumps(raw,allow_nan=False).encode();p=tmp_path/'badtag.json';p.write_bytes(body)
 with pytest.raises(InputContractError):read_plans(str(p),hashlib.sha256(body).hexdigest())
