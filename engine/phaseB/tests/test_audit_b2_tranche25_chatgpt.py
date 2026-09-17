"""Shared-null contracts. All distances here are TEST-ONLY; no scientific OT claims.
Failures are deliberately malformed inputs/results, not empirical run failures.
"""
import os,sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent)); sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shared_fixture import *
import pytest
from step1_engine.errors import InputContractError
from step1_engine.rules_config import RULES
from step1_engine.w2_manifest import build_w2_manifest,verify_w2_manifest,SharedNullAssetRef,verified_w2_for_decision,W2Manifest
from step1_engine.w2_shared import SharedNullAsset,delta_q99_bound_from_prefix
from step1_engine.w2_stop import w2_stop,w2_validate,StopResult
from step1_engine.positions import w2_trigger
from step1_engine import serialization as ser

@pytest.fixture(scope='module')
def base():return fixture()
@pytest.fixture(scope='module')
def large():return fixture((1.,0.))

def manifest(pos,a,r):return build_w2_manifest('E7','L1.00',pos,SharedNullAssetRef(a),r)

def test_normal_shared_manifest_roundtrip(base):
 pos,iso,ip,pp,a,r=base
 restored=SharedNullAsset(**ser.loads(ser.dumps(a.as_dict())))
 assert restored.validate()
 man=manifest(pos,restored,r);man=W2Manifest(**ser.loads(ser.dumps(man.as_dict())))
 d=verified_w2_for_decision(man,pos,SharedNullAssetRef(restored),r)
 assert d.check() and d.trigger is True

@pytest.mark.parametrize('missing',['observed','null','both'])
def test_genuine_missing_bounds_is_archivable_unknown(base,missing):
 pos,iso,ip,pp,a,_=base
 if missing in ('null','both'):
  a=copy.deepcopy(a);a.replicate_bounds=None;a.identity['iso_f32']=None;a.sha256=a.payload_sha()
 r=w2_trigger_shared(pos,a,M,SEED,cheap_dist,whitening_identity=WHITE,positions_f32=pp if missing=='null' else None)
 assert r['trigger']=='unknown'
 dec=verified_w2_for_decision(manifest(pos,a,r),pos,SharedNullAssetRef(a),r)
 assert dec.trigger=='unknown' and dec.check()

def replace_delta(r,dq):
 r=copy.deepcopy(r);r['evidence']['bounds']['delta_q99_bound']=dq
 st=StopResult(**ser.from_jsonable(r['stop']))
 r['validation']=w2_validate(st,r['spread'],r['evidence']['bounds']['obs_bounds'],dq,r['observed'])
 r['trigger']=r['validation'].get('trigger','unknown')
 return r

def test_bound_cannot_be_zeroed_to_upgrade_unresolved(large):
 pos,iso,ip,pp,a,r=large
 assert r['trigger']=='unknown'
 assert min(r['evidence']['bounds']['delta_q99_bound'].values())>1.99
 changed=replace_delta(r,{n:0. for n in RULES.n_subs})
 assert changed['trigger'] is True
 with pytest.raises(InputContractError):manifest(pos,a,changed)

def test_missing_asset_bound_cannot_be_invented_as_zero(base):
 pos,iso,ip,pp,a,_=base;a=copy.deepcopy(a)
 a.replicate_bounds=None;a.identity['iso_f32']=None;a.sha256=a.payload_sha()
 r=w2_trigger_shared(pos,a,M,SEED,cheap_dist,whitening_identity=WHITE,positions_f32=pp)
 changed=replace_delta(r,{n:0. for n in RULES.n_subs})
 assert changed['trigger'] is True
 with pytest.raises(InputContractError):manifest(pos,a,changed)

def test_prefix_bound_is_computed_from_the_actual_prefix(base):
 *_,a,r=base;a=copy.deepcopy(a)
 for n in RULES.n_subs:
  a.replicate_bounds[n]=[0.001]*400+[2.0]*600
 a.sha256=a.payload_sha()
 assert delta_q99_bound_from_prefix(a,2000,400)==.001
 assert delta_q99_bound_from_prefix(a,2000,600)==2.

def test_stop_remains_case_specific():
 vals={n:np.r_[np.ones(200),np.full(200,1.04),np.full(600,1.045)] for n in RULES.n_subs}
 obs=lambda v:{n:{s:v for s in RULES.seed_ids} for n in RULES.n_subs}
 assert w2_stop(vals,obs(.70),'same').B_final==400
 assert w2_stop(vals,obs(1.02),'same').B_final==600

def test_cold_and_shared_same_observed_and_null(base):
 pos,iso,ip,pp,a,r=base
 cold=w2_trigger(pos,iso,M,SEED,cheap_dist,null_prefix_id=f'shared:{a.sha256[:16]}',obs_bounds=r['evidence']['bounds']['obs_bounds'],delta_q99_bound=r['evidence']['bounds']['delta_q99_bound'],whitening_identity=WHITE)
 for field in ('observed','stop','spread','validation','trigger','null_q99'):assert ser.dumps(cold[field])==ser.dumps(r[field])
 assert ser.dumps(cold['evidence']['null'])==ser.dumps(r['evidence']['null'])

@pytest.mark.parametrize('case',['position_id','labels','extra','cid_order'])
def test_observed_pair_structure_checked_before_distance(base,case):
 pos,iso,ip,pp,a,_=base;pp=copy.deepcopy(pp)
 if case=='position_id':pp[0].position_id=101
 elif case=='labels':pp[0].cluster_labels=[x+1000 for x in pp[0].cluster_labels]
 elif case=='extra':pp.append(copy.deepcopy(pp[0]))
 elif case=='cid_order':
  perm=np.arange(len(pp[0].Tw))[::-1];pp[0].Tw=pp[0].Tw[perm];pp[0].cid=pp[0].cid[perm]
 calls=[]
 def count(a,b):calls.append(1);return cheap_dist(a,b)
 count.__name__='cheap_dist'
 with pytest.raises(InputContractError):w2_trigger_shared(pos,a,M,SEED,count,positions_f32=pp,whitening_identity=WHITE)
 assert not calls

def test_iso_pair_original_labels_must_match(base):
 pos,iso,ip,pp,a,r=base
 wrong=PositionBank(iso.position_id,ip.Tw.copy(),iso.cid+1000,iso.m)
 with pytest.raises(InputContractError):build_shared_null(iso,M,SEED,cheap_dist,wrong,WHITE)

def test_supplied_bounds_do_not_hide_nan_paired_input(base):
 pos,iso,ip,pp,a,r=base;pp=copy.deepcopy(pp);pp[0].Tw[0,0]=np.nan
 with pytest.raises(InputContractError):w2_trigger_shared(pos,a,M,SEED,cheap_dist,positions_f32=pp,obs_bounds={n:{s:0. for s in RULES.seed_ids} for n in RULES.n_subs},whitening_identity=WHITE)

def test_shared_build_checks_begin_end_bank_identity():
 pos,iso=make_banks();calls=[0]
 def changing(a,b):
  calls[0]+=1;v=cheap_dist(a,b)
  if calls[0]==6000:iso.Tw[:,0]+=3.
  return v
 with pytest.raises(InputContractError):build_shared_null(iso,M,SEED,changing,None,WHITE)
 assert calls[0]==6000

def test_shared_case_checks_paired_identity_during_distance(base):
 pos,iso,ip,pp,a,r=base;pp=copy.deepcopy(pp);calls=[0]
 def changing(x,y):
  calls[0]+=1;v=cheap_dist(x,y)
  if calls[0]==18:pp[0].Tw[:,0]+=1e-6
  return v
 changing.__name__='cheap_dist'
 with pytest.raises(InputContractError):w2_trigger_shared(pos,a,M,SEED,changing,positions_f32=pp,whitening_identity=WHITE)
 assert calls[0]==18

def test_shared_case_retains_paired_bank_identity(base):
 pos,iso,ip,pp,a,r=base
 from step1_engine.positions import bank_identity
 assert r['evidence']['inputs'].get('positions_f32')==[bank_identity(p) for p in pp]

@pytest.mark.parametrize('field',['values','blocks','pairwise'])
def test_case_result_does_not_alias_asset(base,field):
 pos,iso,ip,pp,a,r=base
 assert r['evidence']['null'][2000][field] is not a.null[2000][field]

@pytest.mark.parametrize('bad',['empty_sha','out_of_range','negative','fraction','B_entry','B_identity','extra_pair'])
def test_asset_intake_rejects_bad_schema(base,bad):
 *_,a,r=base;a=copy.deepcopy(a)
 if bad=='empty_sha':a.sha256=''
 elif bad=='out_of_range':a.null[2000]['blocks'][0][0][-1]=a.identity['iso']['K']+999
 elif bad=='negative':a.null[2000]['blocks'][0][0][0]=-1
 elif bad=='fraction':a.null[2000]['blocks'][0][0][0]=.75
 elif bad=='B_entry':a.null[2000]['B_max']=3
 elif bad=='B_identity':a.identity['B_max']=1000.75
 elif bad=='extra_pair':a.null[2000]['pairwise'][0]['extra']=1.
 if bad!='empty_sha':a.sha256=a.payload_sha()
 with pytest.raises(InputContractError):a.validate()

@pytest.mark.parametrize('corrupt',['null_values','master','whitening'])
def test_existing_rejections_are_retained(base,corrupt):
 pos,iso,ip,pp,a,r=base
 if corrupt=='null_values':
  a=copy.deepcopy(a);a.null[2000]['values'][0]+=1.
  with pytest.raises(InputContractError):a.validate()
 else:
  with pytest.raises(InputContractError):w2_trigger_shared(pos,a,M,SEED+(corrupt=='master'),cheap_dist,whitening_identity={'other':True} if corrupt=='whitening' else WHITE)
