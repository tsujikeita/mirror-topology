"""Audit tests for tranche17's new grid_registry/archive boundaries.
Run with PHASEB_ROOT and TRANCHE17_ASSETS. Tests edit copies/tempfiles only.
A recomputed payload SHA tests INTERNAL consistency, not cryptographic authenticity.
"""
from pathlib import Path
from dataclasses import replace
import os,sys,copy,hashlib
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from step1_engine.grid_registry import GridRegistry,load_registry,registry_from_dict,A6_SHA,A7_SHA
from step1_engine.archive import Archive,ArchiveRef,archive_three_position_result,resolve_transition_archive
from step1_engine.stage12 import transition_after_three
from step1_engine.errors import InputContractError
from step1_engine import serialization as ser
ASSETS=Path(os.environ.get('TRANCHE17_ASSETS',str(Path(__file__).resolve().parent/'assets')))
@pytest.fixture
def registry():return load_registry(str(ASSETS/'a7_circle_geometry.csv'),str(ASSETS/'a6_observer_design_points.json'))
def raw(registry):return ser.loads(ser.dumps(registry.as_dict()))
def rehash(d):
 d['registry_sha256']=GridRegistry(**d).payload_sha();return d
@pytest.fixture
def archived(tmp_path):
 a=Archive(str(tmp_path/'archive'))
 r={'family':'E7','size_id':'L1.00','decision':{'technical_status':'ok'},'truths':{'support':True,'strong':False,'unsupported':False},'precision':{'state':'pass'},'evidence':{'coverage_ok':True}}
 ref=archive_three_position_result(a,r,'E7','L1.00')
 t=transition_after_three('E7','L1.00',r,{'state':'not-expanded','expand':False},None)
 return a,r,ref,t

def test_normal_registry_and_full_inventory(registry):
 r=registry_from_dict(raw(registry));assert r.validate()
 assert r.n_configurations==30
 assert r.surviving=={f:['L1.00','L1.20','L1.50'] for f in ('E1','E2','E7','E8')}
 assert r.status['E7']['L1.00']['geometric_status']=='zero_radius_boundary'
 assert r.registry_sha256==registry.registry_sha256

def test_raw_source_sha_drift_is_rejected(tmp_path):
 p=tmp_path/'bad.csv';p.write_bytes((ASSETS/'a7_circle_geometry.csv').read_bytes()+b'\n')
 with pytest.raises(InputContractError):load_registry(str(p),str(ASSETS/'a6_observer_design_points.json'))

def test_payload_drift_with_original_hash_is_rejected(registry):
 d=raw(registry);d['anchors']['E7'][0][0]+=.001
 with pytest.raises(InputContractError):registry_from_dict(d)

@pytest.mark.parametrize('how',['missing','empty'])
def test_restored_registry_requires_its_payload_hash(registry,how):
 d=raw(registry)
 if how=='missing':d.pop('registry_sha256')
 else:d['registry_sha256']=''
 with pytest.raises(InputContractError):registry_from_dict(d)

@pytest.mark.parametrize('mutation',['shrink','count','L','anchor_dimension','schema','extra_family'])
def test_registry_internal_invariants_with_correct_hash(registry,mutation):
 d=raw(registry)
 if mutation=='shrink':d['surviving']['E7']=['L1.00'];d['size_prior']['E7']={'L1.00':1.}
 if mutation=='count':d['n_configurations']=27
 if mutation=='L':d['status']['E7']['L1.00']['L']=1.5
 if mutation=='anchor_dimension':d['anchors']['E7']=[[.03,.04],[.10,.12],[.20,.21]]
 if mutation=='schema':d['schema']='future-or-typo'
 if mutation=='extra_family':d['anchors']['E100']=[[0.]]
 with pytest.raises(InputContractError):registry_from_dict(rehash(d))

def test_archive_normal_reopen_roundtrip_and_idempotence(archived):
 a,r,ref,t=archived
 ref2=archive_three_position_result(a,r,'E7','L1.00');b=Archive(a.root)
 assert ref2==ref and b.get(ref)==r and resolve_transition_archive(b,t,ref)==r
 assert b.verify_all()['entries']==1

def test_archive_detects_bytes_drift(archived):
 a,r,ref,t=archived;p=Path(a.root)/ref.path;p.write_bytes(p.read_bytes()+b' ')
 with pytest.raises(InputContractError):a.get(ref)
 with pytest.raises(InputContractError):a.verify_all()

def test_archive_rejects_missing_index_entry(archived):
 a,r,ref,t=archived;d=ser.loads(Path(a.index_path).read_text());d['entries']=[];Path(a.index_path).write_text(ser.dumps(d))
 with pytest.raises(InputContractError):a.get(ref)

def test_reference_identity_must_match_stored_index(archived):
 a,r,ref,t=archived
 bad=replace(ref,identity={'family':'E8','size_id':'L1.50'})
 with pytest.raises(InputContractError):a.get(bad)

def test_duplicate_put_must_not_issue_unindexed_identity(archived):
 a,r,ref,t=archived
 # Archive may reject the conflict or return the original identity; it must not
 # silently issue a second incompatible identity unsupported by its index.
 try:got=a.put('three_position_result',r,{'family':'E8','size_id':'L1.50'})
 except InputContractError:return
 assert got.identity==ref.identity
 assert a.get(got)==r

@pytest.mark.parametrize('style',['relative','absolute'])
def test_ref_path_must_be_registered_canonical_location(archived,tmp_path,style):
 a,r,ref,t=archived;p=tmp_path/'outside.json';p.write_bytes((Path(a.root)/ref.path).read_bytes())
 bad=replace(ref,path='../outside.json' if style=='relative' else str(p))
 with pytest.raises(InputContractError):a.get(bad)

@pytest.mark.parametrize('field,value',[('identity',{'family':'E8','size_id':'L1.50'}),('bytes',0),('path','wrong/path.json')])
def test_index_metadata_disagrees_with_ref_or_body(archived,field,value):
 a,r,ref,t=archived;d=ser.loads(Path(a.index_path).read_text());d['entries'][0][field]=value;Path(a.index_path).write_text(ser.dumps(d))
 with pytest.raises(InputContractError):a.get(ref)

def test_verify_all_checks_more_than_file_sha(archived):
 a,r,ref,t=archived;d=ser.loads(Path(a.index_path).read_text());d['entries'][0]['bytes']=0;Path(a.index_path).write_text(ser.dumps(d))
 with pytest.raises(InputContractError):a.verify_all()

def test_index_duplicates_are_rejected(archived):
 a,r,ref,t=archived;d=ser.loads(Path(a.index_path).read_text());d['entries']*=2;Path(a.index_path).write_text(ser.dumps(d))
 with pytest.raises(InputContractError):a.verify_all()

def test_resolve_validates_transition_record(archived):
 a,r,ref,t=archived
 with pytest.raises(InputContractError):resolve_transition_archive(a,replace(t,expand='False'),ref)

def test_resolve_binds_source_technical_status(archived):
 a,r,ref,t=archived;r=copy.deepcopy(r);r['decision']['technical_status']='technical_fail';r['truths']={k:'technical_fail' for k in r['truths']}
 ref=archive_three_position_result(a,r,'E7','L1.00')
 t=transition_after_three('E7','L1.00',r,{'state':'not-expanded','expand':False},None)
 bad=replace(t,three_technical_status='ok',phase='final_at_3',status='final at 3 positions')
 assert bad.validate() # internally coherent, but contradicts the archived source
 with pytest.raises(InputContractError):resolve_transition_archive(a,bad,ref)

def test_normal_technical_failure_archives_without_promotion(archived):
 a,r,ref,t=archived;r=copy.deepcopy(r);r['decision']['technical_status']='technical_fail';r['truths']={k:'technical_fail' for k in r['truths']}
 ref=archive_three_position_result(a,r,'E7','L1.00');t=transition_after_three('E7','L1.00',r,{'state':'not-expanded','expand':False},None)
 assert t.phase=='technical_fail'
 assert resolve_transition_archive(a,t,ref)['decision']['technical_status']=='technical_fail'
