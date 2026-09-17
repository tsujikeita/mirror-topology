"""Tranche18 local archive/source-snapshot contracts. Synthetic copies and temporary
paths only. These tests do not claim cryptographic authentication, hostile-process
safety, production grid evaluation, or statistical coverage.
Run: PHASEB_ROOT=... pytest -q test_tranche18_contracts.py
"""
from pathlib import Path
from dataclasses import replace
import os,sys,copy,json,hashlib
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]));sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from step1_engine import serialization as ser
from step1_engine.errors import InputContractError
from step1_engine.archive import Archive,archive_three_position_result,resolve_transition_archive
from step1_engine.stage12 import transition_after_three
from step1_engine.grid_registry import GridRegistry,load_registry,registry_from_dict,registry_from_dict_bound,A6_SHA,A7_SHA
import step1_engine.grid_registry as grid
A6=ROOT/'tests/assets/a6_observer_design_points.json';A7=ROOT/'tests/assets/a7_circle_geometry.csv'

def source(technical=False):
 state='technical_fail' if technical else 'ok'
 return {'family':'E7','size_id':'L1.00','decision':{'technical_status':state},
         'truths':{k:'technical_fail' if technical else False for k in ('support','strong','unsupported')},
         'precision':{'state':'technical_fail' if technical else 'pass'},'evidence':{'coverage_ok':True}}
@pytest.fixture
def entry(tmp_path):
 arc=Archive(str(tmp_path/'arc'));res=source();ref=archive_three_position_result(arc,res,'E7','L1.00')
 return arc,res,ref
@pytest.fixture
def reg():return load_registry(str(A7),str(A6))
def record(reg):return ser.loads(ser.dumps(reg.as_dict()))
def rehash(d):d['registry_sha256']=GridRegistry(**d).payload_sha();return d

def test_registry_normal_scopes_and_source_reconstruction(reg):
 d=record(reg);inside=registry_from_dict(d);bound=registry_from_dict_bound(d,str(A7),str(A6))
 assert inside.registry_sha256==bound.registry_sha256==reg.registry_sha256
 assert 'not_verified' in inside.verification_scope and bound.verification_scope.startswith('source_bound')
 assert bound.n_configurations==30 and all(v==['L1.00','L1.20','L1.50'] for v in bound.surviving.values())

def test_forged_scope_does_not_promote_internal_restore(reg):
 d=record(reg);d['verification_scope']='source_bound';got=registry_from_dict(d)
 assert 'not_verified' in got.verification_scope

def test_internal_anchor_edit_is_not_source_binding(reg):
 d=record(reg);d['anchors']['E7'][0][0]+=.001;rehash(d)
 assert 'not_verified' in registry_from_dict(d).verification_scope
 with pytest.raises(InputContractError):registry_from_dict_bound(d,str(A7),str(A6))

@pytest.mark.parametrize('which',['A6','A7'])
def test_parser_uses_same_bytes_as_hash_verification(tmp_path,monkeypatch,reg,which):
 """Actual digest is never forged: change only the temp path after its original
 bytes have been read for hashing. A loader may reject drift OR parse its captured
 verified snapshot, but may not label later unverified bytes as verified."""
 p6=tmp_path/'a6.json';p7=tmp_path/'a7.csv';p6.write_bytes(A6.read_bytes());p7.write_bytes(A7.read_bytes())
 target=p6 if which=='A6' else p7;old=target.read_bytes()
 if which=='A6':
  data=json.loads(old);data['points']['E7']['points'][0][0]+=.001;new=json.dumps(data).encode()
 else:new=old.replace(b'zero_radius_boundary',b'no_nondegenerate_circles')
 real=hashlib.sha256;fired=[]
 def hash_and_change(data=b'',*args,**kwargs):
  h=real(data,*args,**kwargs)
  if not fired and data==old:target.write_bytes(new);fired.append(True)
  return h
 monkeypatch.setattr(grid.hashlib,'sha256',hash_and_change)
 try:got=load_registry(str(p7),str(p6))
 except InputContractError:
  assert fired;return
 assert fired,'fault injection must have executed'
 assert got.payload_sha()==reg.payload_sha(),'accepted data differ from the exact verified bytes'
 assert got.anchors==reg.anchors and got.status==reg.status

def test_registry_rejects_unknown_serialised_field(reg):
 d=record(reg);d['observer_desgin']={'typo':True}
 with pytest.raises(InputContractError):registry_from_dict(d)

@pytest.mark.parametrize('field,value',[('version',None),('seed_sequence','oops'),('lift_rule',None)])
def test_registry_metadata_has_valid_types(reg,field,value):
 d=record(reg);d['observer_design'][field]=value;rehash(d)
 with pytest.raises(InputContractError):registry_from_dict(d)

def test_archive_normal_reput_is_resolvable_and_stable(entry):
 a,r,ref=entry;p=Path(a.root)/ref.path;before=p.read_bytes();idx=Path(a.index_path).read_bytes()
 ref2=a.put(ref.kind,r,ref.identity)
 assert ref2==ref and a.get(ref2)==r and p.read_bytes()==before and Path(a.index_path).read_bytes()==idx
 assert a.verify_all()=={'entries':1,'ok':True}

@pytest.mark.parametrize('mode',['missing','appended','same_length','directory'])
def test_reput_cannot_report_success_with_unresolvable_record(entry,mode):
 a,r,ref=entry;p=Path(a.root)/ref.path
 if mode=='missing':p.unlink()
 elif mode=='appended':p.write_bytes(p.read_bytes()+b' ')
 elif mode=='same_length':p.write_bytes(p.read_bytes().replace(b'E7',b'E8'))
 else:p.unlink();p.mkdir()
 try:ref2=a.put(ref.kind,r,ref.identity)
 except InputContractError:return
 assert a.get(ref2)==r,'returning a reference requires a resolvable verified file'

def test_drift_is_still_rejected_by_get_and_verify(entry):
 a,r,ref=entry;p=Path(a.root)/ref.path;p.write_bytes(p.read_bytes()+b' ')
 with pytest.raises(InputContractError):a.get(ref)
 with pytest.raises(InputContractError):a.verify_all()

@pytest.mark.parametrize('action',['get','verify_all','put'])
def test_external_file_symlink_is_not_inside_archive(entry,tmp_path,action):
 a,r,ref=entry;p=Path(a.root)/ref.path;out=tmp_path/'external.json';out.write_bytes(p.read_bytes());p.unlink();p.symlink_to(out)
 with pytest.raises(InputContractError):
  if action=='get':a.get(ref)
  elif action=='verify_all':a.verify_all()
  else:a.put(ref.kind,r,ref.identity)

def test_fresh_put_does_not_write_through_external_directory_link(tmp_path):
 a=Archive(str(tmp_path/'arc'));external=tmp_path/'external';external.mkdir();(Path(a.root)/'three_position_result').symlink_to(external,target_is_directory=True)
 with pytest.raises(InputContractError):archive_three_position_result(a,source(),'E7','L1.00')
 assert list(external.iterdir())==[]

def test_alias_for_the_archive_root_itself_remains_usable(tmp_path):
 real=tmp_path/'real';real.mkdir();alias=tmp_path/'alias';alias.symlink_to(real,target_is_directory=True)
 a=Archive(str(alias));r=source();ref=archive_three_position_result(a,r,'E7','L1.00')
 assert a.get(ref)==r and a.verify_all()['entries']==1

def test_record_and_reference_identity_are_independent_snapshot(entry):
 a,r,ref=entry;r['family']='E8'
 assert a.get(ref)['family']=='E7'
 bad=replace(ref,identity={'family':'E8','size_id':'L1.00'})
 with pytest.raises(InputContractError):a.get(bad)

@pytest.mark.parametrize('technical',[False,True])
def test_normal_source_transition_resolution_keeps_technical_status(tmp_path,technical):
 a=Archive(str(tmp_path/'arc'));r=source(technical);ref=archive_three_position_result(a,r,'E7','L1.00')
 t=transition_after_three('E7','L1.00',r,{'state':'not-expanded','expand':False},None)
 assert resolve_transition_archive(a,t,ref)==r
 assert (t.phase=='technical_fail')==technical
