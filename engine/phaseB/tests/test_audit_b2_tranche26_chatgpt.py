"""Tranche26 context contracts, using real shared-null/replay APIs and TEST-ONLY distance.
No missing future API is counted as a failing test. The assertions concern existing
build_w2_context/decision_for/as_dict contracts and the documented case identity.
"""
import sys,copy,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent)); sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from context_fixture import *
import pytest
from dataclasses import replace
from step1_engine.errors import InputContractError
from step1_engine.w2_context import W2Context
from step1_engine.positions import position_decision

@pytest.fixture(scope='module')
def context_data():return make_context_fixture()

def test_normal_two_cases_keep_their_own_decisions(context_data):
    a,cs,c=context_data
    assert c.asset_sha256==a.sha256
    assert c.decision_for(KEY_A).trigger is True
    assert c.decision_for(KEY_B).trigger is False
    assert c.manifests[KEY_A].family=='E7' and c.manifests[KEY_A].size_id=='L1.00'

def test_repeated_consumption_never_reexecutes_distance(context_data,monkeypatch):
    import step1_engine.w2_context as wc
    def forbidden(*a,**kw):pytest.fail('distance was recomputed when reusing context')
    monkeypatch.setattr(wc,'w2_trigger_shared',forbidden)
    c=context_data[2];first=c.decision_for(KEY_A)
    for _ in range(10):assert c.decision_for(KEY_A)==first

def test_fixed_w2_branch_does_not_freeze_event_ratio(context_data):
    d=context_data[2].decision_for(KEY_B)
    assert position_decision(d,probabilities(1.25))['state']=='not-expanded'
    assert position_decision(d,probabilities(3.))['state']=='position-sensitive'

def test_bad_expected_asset_rejected(context_data):
    a,cs,c=context_data
    with pytest.raises(InputContractError):build_w2_context(a,cs,M,SEED,cheap_dist,WHITE,'0'*64)

def test_unknown_requested_case_rejected(context_data):
    with pytest.raises(InputContractError):context_data[2].decision_for('E2/L1.00')

def test_changed_decision_with_old_checksum_rejected(context_data):
    c=copy.deepcopy(context_data[2]);d=c.decisions[KEY_A]
    c.decisions[KEY_A]=replace(d,trigger=False)
    with pytest.raises(InputContractError):c.decision_for(KEY_A)

def test_content_equivalent_copy_is_accepted(context_data):
    c=copy.deepcopy(context_data[2])
    assert c.decision_for(KEY_A)==context_data[2].decision_for(KEY_A)

def test_family_key_plus_explicit_size_is_a_valid_alias(context_data):
    a,cs,c=context_data
    q=build_w2_context(a,{'E7':dict(cs[KEY_A],size_id='L1.00')},M,SEED,cheap_dist,WHITE,a.sha256)
    assert q.decision_for('E7')==c.decision_for(KEY_A)
    assert q.manifests['E7'].size_id=='L1.00'

def test_checksum_valid_other_case_decision_is_not_accepted(context_data):
    c=copy.deepcopy(context_data[2]);c.decisions[KEY_A]=c.decisions[KEY_B]
    assert c.decisions[KEY_A].check()
    with pytest.raises(InputContractError):c.decision_for(KEY_A)

@pytest.mark.parametrize('kind',['asset','manifest_missing','manifest_other_case','manifest_trigger','manifest_stop'])
def test_context_relationships_are_checked_at_consumption(context_data,kind):
    c=copy.deepcopy(context_data[2])
    if kind=='asset':c.asset_sha256='0'*64
    elif kind=='manifest_missing':del c.manifests[KEY_A]
    elif kind=='manifest_other_case':c.manifests[KEY_A]=c.manifests[KEY_B]
    elif kind=='manifest_trigger':c.manifests[KEY_A].validation['trigger']=False
    else:c.manifests[KEY_A].stop['B_final']=1000
    with pytest.raises(InputContractError):c.decision_for(KEY_A)

def test_summary_contains_real_manifest_references(context_data):
    refs=context_data[2].as_dict()['manifests']
    assert set(refs)=={KEY_A,KEY_B}
    # Full canonical manifest records are also an acceptable format.
    assert all(isinstance(v,dict) or (isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v)) for v in refs.values())

def test_empty_context_not_issued_as_evaluated(context_data):
    a,cs,c=context_data
    with pytest.raises(InputContractError):build_w2_context(a,{},M,SEED,cheap_dist,WHITE,a.sha256)

@pytest.mark.parametrize('key',['','E7','E7/L1.00/ignored','E999/L1.00'])
def test_invalid_or_ambiguous_case_identity_rejected(context_data,key):
    a,cs,c=context_data
    with pytest.raises(InputContractError):build_w2_context(a,{key:cs[KEY_A]},M,SEED,cheap_dist,WHITE,a.sha256)

def test_conflicting_size_field_is_not_silently_overridden(context_data):
    a,cs,c=context_data
    with pytest.raises(InputContractError):build_w2_context(a,{KEY_A:dict(cs[KEY_A],size_id='L1.50')},M,SEED,cheap_dist,WHITE,a.sha256)
