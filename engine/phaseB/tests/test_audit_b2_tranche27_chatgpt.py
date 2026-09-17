"""Tranche27 audit: existing context / intake / summary contracts.
Finite synthetic banks. W2 fixture uses TEST-ONLY mean distance, never production OT.
Expected SHA values come from each original factory-issued fixture, not modified data.
"""
import os,sys,copy,json
from pathlib import Path
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import numpy as np
import pytest
from dataclasses import replace,asdict
from context_fixture import make_context_fixture,KEY_A,KEY_B
from test_b2_tranche4 import make_staged_family
from test_b2_tranche20 import synthetic_supplies,A7,A6
from step1_engine import orchestrator as o,serialization as ser
from step1_engine.w2_context import W2Context
from step1_engine.w2_manifest import W2Manifest
from step1_engine.positions import VerifiedW2Decision
from step1_engine.production import production_manifest,build_family_input
from step1_engine.grid_registry import load_registry
from step1_engine.errors import InputContractError

@pytest.fixture(scope='module')
def sample():
    asset,cases,ctx=make_context_fixture()
    fm=make_staged_family(np.random.default_rng(5))
    return asset,cases,ctx,fm,{100:1,101:2,102:3}

@pytest.fixture(scope='module')
def production():
    reg=load_registry(A7,A6);man=production_manifest(reg)
    supplies,plans,fplans=synthetic_supplies(man,'E7','matched')
    one=build_family_input(reg,man,'E7','matched',[s for s in supplies if s.config_id//100%100==3],plans,fplans,size_ids=['L1.50'])
    full=build_family_input(reg,man,'E7','matched',supplies,plans,fplans)
    return one,full

def evaluate(sample,*,fam=None,key=KEY_A,pm='default',staged=True,ctx=None):
    a,cs,c,f,m=sample
    c=c if ctx is None else ctx
    fam=f if fam is None else fam
    if pm=='default':pm={key:m}
    return o.evaluate_threshold({key:(fam,None)},80.,400.,staged=staged,position_maps=pm,w2_context=c,expected_context_sha256=sample[2].context_sha256)

def test_normal_intake_matches_explicit_typed_decision(sample):
    a,cs,c,f,m=sample
    got=evaluate(sample)[KEY_A]
    ref=o.evaluate_threshold({KEY_A:(f,None)},80.,400.,staged=True,position_maps={KEY_A:m},w2_results={KEY_A:c.decision_for(KEY_A)})[KEY_A]
    gd=got.as_dict(); rd=ref.as_dict(); gd['evidence'].pop('w2_context')
    assert ser.dumps(gd)==ser.dumps(rd)

def test_production_correct_size_accepted(sample,production):
    f,_=production; pm={KEY_B:{c.evaluation_id:i+1 for i,c in enumerate(f.configs)}}
    r=evaluate(sample,fam=f,key=KEY_B,pm=pm)[KEY_B]
    assert r.evidence['grid_identity']['sizes']==['L1.50']
    assert r.position_status['w2_trigger'] is False

def test_wrong_actual_family_rejected(sample):
    f=sample[3];other=replace(f,family='E8',configs=[replace(c,family='E8') for c in f.configs]);other.validate()
    with pytest.raises(InputContractError):evaluate(sample,fam=other)

def test_wrong_declared_size_rejected(sample,production):
    f,_=production;pm={KEY_A:{c.evaluation_id:i+1 for i,c in enumerate(f.configs)}}
    with pytest.raises(InputContractError):evaluate(sample,fam=f,pm=pm)

def test_full_multisize_bank_not_a_single_case_input(sample,production):
    _,f=production;pm={KEY_A:{c.evaluation_id:i+1 for i,c in enumerate(f.configs[:3])}}
    with pytest.raises(InputContractError):evaluate(sample,fam=f,pm=pm)

@pytest.mark.parametrize('call,staged,pm_mode',[
    ('target',True,'missing'),('target',False,'present'),
    ('calibration',True,'missing'),('calibration',False,'present')])
def test_context_request_is_not_silently_unused(sample,call,staged,pm_mode):
    a,cs,c,f,m=sample;pm=None if pm_mode=='missing' else {KEY_A:m}
    with pytest.raises(InputContractError):
        if call=='target':evaluate(sample,staged=staged,pm=pm)
        else:o.calibrate_pseudo({KEY_A:(f,None)},[80.],[400.],staged=staged,position_maps=pm,w2_context=c,expected_context_sha256=c.context_sha256)

def test_missing_map_does_not_hide_missing_context_case(sample):
    with pytest.raises(InputContractError):evaluate(sample,key='E2/L1.00',pm=None)

def test_position_ids_match_the_w2_manifest(sample):
    with pytest.raises(InputContractError):evaluate(sample,pm={KEY_A:{100:91,101:92,102:93}})

@pytest.mark.parametrize('change',['case_swap','null_nan','subset_out_of_range'])
def test_present_raw_evidence_is_bound_to_context(sample,change):
    c=copy.deepcopy(sample[2]); expected=sample[2].context_sha256
    if change=='case_swap':c.results[KEY_A]=copy.deepcopy(c.results[KEY_B])
    elif change=='null_nan':c.results[KEY_A]['evidence']['null'][2000]['values'][0]=float('nan')
    else:c.results[KEY_A]['evidence']['observed'][2000][0]['subsets'][1][0]=999999
    with pytest.raises(InputContractError):c.validate(expected)

def test_summary_retains_full_asset_and_context_references(sample):
    a,cs,c,f,m=sample
    summary,truths=o.calibrate_pseudo({KEY_A:(f,None)},[80.,200.],[400.,900.],staged=True,position_maps={KEY_A:m},w2_context=c,expected_context_sha256=c.context_sha256)
    text=ser.dumps(summary.as_dict())
    assert c.context_sha256 in text and a.sha256 in text

def test_snapshot_checks_the_existing_stamp_before_restamping(sample):
    c=copy.deepcopy(sample[2]);c.context_sha256='0'*64
    with pytest.raises(InputContractError):c.snapshot()

def test_consumer_rejects_missing_context_stamp(sample):
    c=copy.deepcopy(sample[2]);c.context_sha256=''
    with pytest.raises(InputContractError):c.decision_for(KEY_A)

def test_restored_case_key_is_checked_not_only_identity_values(sample):
    c=copy.deepcopy(sample[2]);bad='E999/L1.00'
    for name in ('decisions','manifests','identities','results'):
        mapping=getattr(c,name);mapping[bad]=mapping.pop(KEY_A)
    # Any explicit per-result digest table introduced by a fix must follow the same ordinary key rename.
    for name in ('result_sha256','result_sha256s'):
        if hasattr(c,name):
            mapping=getattr(c,name);mapping[bad]=mapping.pop(KEY_A)
    c.context_sha256=c.payload_sha()
    with pytest.raises(InputContractError):c.validate()

def test_whole_dataclass_roundtrip_preserves_reference_and_decisions(sample):
    c=sample[2];d=ser.loads(ser.dumps(asdict(c)))
    d['decisions']={k:VerifiedW2Decision(**v) for k,v in d['decisions'].items()}
    d['manifests']={k:W2Manifest(**v) for k,v in d['manifests'].items()}
    back=W2Context(**d)
    assert back.validate(c.context_sha256)
    assert back.decision_for(KEY_A)==c.decision_for(KEY_A)

def test_caller_mutation_does_not_change_fixed_consumed_snapshot(sample,monkeypatch):
    a,cs,c0,f,m=sample;c=copy.deepcopy(c0);expected=c.context_sha256
    original=o.evaluate_threshold;seen=[]
    def wrapper(*args,**kwargs):
        result=original(*args,**kwargs)
        seen.append(result[KEY_A].evidence['position']['w2']['trigger'])
        c.decisions[KEY_A]=c.decisions[KEY_B]
        return result
    monkeypatch.setattr(o,'evaluate_threshold',wrapper)
    o.calibrate_pseudo({KEY_A:(f,None)},[80.,80.],[400.,400.],staged=True,position_maps={KEY_A:m},w2_context=c,expected_context_sha256=expected)
    assert seen==[True,True]

def test_consumed_snapshot_mutation_before_next_pseudo_is_rejected(sample,monkeypatch):
    a,cs,c,f,m=sample;original=o.evaluate_threshold;calls=[0]
    def wrapper(*args,**kwargs):
        calls[0]+=1
        if calls[0]==2:
            snap=kwargs['w2_context'];snap.decisions[KEY_A]=snap.decisions[KEY_B]
        return original(*args,**kwargs)
    monkeypatch.setattr(o,'evaluate_threshold',wrapper)
    with pytest.raises(InputContractError):
        o.calibrate_pseudo({KEY_A:(f,None)},[80.,80.],[400.,400.],staged=True,position_maps={KEY_A:m},w2_context=c,expected_context_sha256=c.context_sha256)

def test_bad_expected_sha_is_rejected(sample):
    a,cs,c,f,m=sample
    with pytest.raises(InputContractError):o.evaluate_threshold({KEY_A:(f,None)},80.,400.,staged=True,position_maps={KEY_A:m},w2_context=c,expected_context_sha256='0'*64)

def test_core_only_without_context_remains_available(sample):
    f=sample[3];r=o.evaluate_threshold({'E7':(f,None)},80.,400.,staged=True)['E7']
    assert r.position_status['state']=='not-integrated' and 'w2_context' not in r.evidence
