"""Additional tranche20 contracts for actual submitted APIs.
Synthetic banks only. Production refers to identity wiring, NOT official N/m,
physical covariance, source authentication against hostile object rewriting,
or complete scientific-label release. Existing API signatures are used.
"""
import os,sys,copy
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]));sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_b2_tranche20 import synthetic_supplies,A7,A6
from step1_engine import production as p,orchestrator as o,serialization as ser
from step1_engine.errors import InputContractError
from step1_engine.grid_registry import load_registry,registry_from_dict,registry_from_dict_bound
from step1_engine.grid_manifest import cache_key,lift
from step1_engine.checkpoint import write_family_result,read_family_result
@pytest.fixture(scope='module')
def base():
 reg=load_registry(A7,A6);man=p.production_manifest(reg)
 sm,ep,fp=synthetic_supplies(man,'E7','matched');sn,_,_=synthetic_supplies(man,'E7','native')
 return reg,man,sm,sn,ep,fp

def build(b,system='matched',sup=None,reg=None,man=None,sizes=None):
 r,m,sm,sn,ep,fp=b
 return p.build_family_input(r if reg is None else reg,m if man is None else man,'E7',system,(sm if system=='matched' else sn) if sup is None else sup,ep,fp,size_ids=sizes)
@pytest.fixture(scope='module')
def result(base): return o.evaluate_family(build(base),build(base,'native'),80.,400.)

def test_normal_full_registry_wrapper(base):
 fm=build(base);fn=build(base,'native'); assert len(fm.configs)==9
 assert fm.grid_identity['evaluation_to_config']=={c.evaluation_id:c.evaluation_id for c in fm.configs}
 assert set(fn.grid_identity['evaluation_to_config'])=={c.evaluation_id+50000 for c in fm.configs}
 assert [c.weight for c in fm.configs]==[1/9]*9
 assert fm.fitting_plan_binding=='bound'

def test_internal_registry_is_rejected_by_factory(base):
 reg=registry_from_dict(ser.loads(ser.dumps(base[0].as_dict())))
 with pytest.raises(InputContractError):p.production_manifest(reg)

def test_bound_restored_registry_normal(base):
 reg=registry_from_dict_bound(ser.loads(ser.dumps(base[0].as_dict())),A7,A6)
 assert p.production_manifest(reg).manifest_sha256==base[1].manifest_sha256
 assert len(build(base,reg=reg).configs)==9

def test_valid_supply_order_does_not_change_output(base):
 a=build(base);b=build(base,sup=list(reversed(base[2])))
 assert [c.evaluation_id for c in a.configs]==[c.evaluation_id for c in b.configs]
 for c,d in zip(a.configs,b.configs): assert np.array_equal(c.T1_model,d.T1_model)

def test_declared_same_size_subset_remains_usable(base):
 fm=build(base,sup=base[2][:3],sizes=['L1.00']);fn=build(base,'native',sup=base[3][:3],sizes=['L1.00'])
 assert [c.weight for c in fm.configs]==[1/3]*3
 assert o.evaluate_family(fm,fn,80.,400.).family=='E7'

@pytest.mark.parametrize('case',['same','changed','discarded_invalid'])
def test_duplicate_supply_is_rejected_before_dict_conversion(base,case):
 extra=copy.deepcopy(base[2][0]);sup=list(base[2])
 if case=='changed':extra.T1_model-=25;extra.T2_model-=125;sup.append(extra)
 elif case=='discarded_invalid':extra.system='native';extra.cov_manifest['manifest']['x0'][1]=float('nan');sup=[extra]+sup
 else:sup.append(extra)
 with pytest.raises(InputContractError):build(base,sup=sup)

def test_missing_supply_already_rejected(base):
 with pytest.raises(InputContractError):build(base,sup=base[2][:-1])

def test_float_supply_id_rejected(base):
 sup=copy.deepcopy(base[2]);sup[0].config_id=float(sup[0].config_id)
 with pytest.raises(InputContractError):build(base,sup=sup)

def test_numpy_integer_supply_id_accepted(base):
 sup=copy.deepcopy(base[2]);sup[0].config_id=np.int64(sup[0].config_id)
 assert len(build(base,sup=sup).configs)==9

def test_duplicate_requested_size_rejected(base):
 with pytest.raises(InputContractError):build(base,sup=base[2][:3],sizes=['L1.00','L1.00'])

def test_builder_cannot_bypass_source_scope_factory(base):
 reg=registry_from_dict(ser.loads(ser.dumps(base[0].as_dict())))
 with pytest.raises(InputContractError):build(base,reg=reg)

@pytest.mark.parametrize('field',['size_prior','anchors'])
def test_stale_registry_is_checked_at_bank_construction(base,field):
 reg=copy.deepcopy(base[0])
 if field=='size_prior':reg.size_prior['E7']={'L1.00':.8,'L1.20':.1,'L1.50':.1}
 else:reg.anchors['E7'][0][0]+=.001
 # SHA deliberately remains the trusted old value: this is an ordinary stale object.
 with pytest.raises(InputContractError):build(base,reg=reg)

def test_self_consistent_manifest_must_match_supplied_registry(base):
 man=copy.deepcopy(base[1]);c=next(c for c in man.configurations if c.config_id==30101)
 c.reduced_coords[0]+=.001;c.r_obs=lift(c.family,c.reduced_coords,c.shape_params);c.x0_CT=[-v for v in c.r_obs];c.cache_key=cache_key(c.family,c.shape_params,c.x0_CT)
 man.manifest_sha256=man.payload_sha();assert man.validate()
 sup,_,_=synthetic_supplies(man,'E7','matched')
 with pytest.raises(InputContractError):build(base,man=man,sup=sup)

def test_empty_manifest_cannot_issue_registered_id_map(base):
 man=copy.deepcopy(base[1]);man.configurations=[]
 with pytest.raises(InputContractError):p.registered_id_map(man)

def test_id_map_restored_float_values_rejected(base):
 m=p.registered_id_map(base[1]);m.native[30101]=float(m.native[30101])
 with pytest.raises(InputContractError):m.validate(base[1])

def test_native_grid_identity_survives_evaluation(base,result):
 assert result.native['evidence'].get('grid_identity')==build(base,'native').grid_identity

def test_staged_matched_grid_identity_survives(base):
 fm=build(base);r=o.evaluate_family_staged(fm,None,80.,400.)
 assert r.evidence['grid_identity']==fm.grid_identity

def test_failed_result_keeps_both_grid_identities(base,monkeypatch):
 fm=build(base);fn=build(base,'native');orig=o._stage_selection;count=[0]
 def failed_once(f,*args,**kwargs):
  s=orig(f,*args,**kwargs);count[0]+=1
  if count[0]==1:s['technical']=True
  return s
 monkeypatch.setattr(o,'_stage_selection',failed_once)
 r=o.evaluate_family_staged(fm,fn,80.,400.)
 assert r.decision['technical_status']=='technical_fail'
 assert r.evidence.get('grid_identity')==fm.grid_identity
 assert (r.native.get('evidence') or {}).get('grid_identity')==fn.grid_identity

def test_different_conditioned_size_domains_are_not_paired(base):
 fm=build(base,sup=base[2][:3],sizes=['L1.00']);fn=build(base,'native',sup=base[3][-3:],sizes=['L1.50'])
 with pytest.raises(InputContractError):o.evaluate_family(fm,fn,80.,400.)

def test_grid_identity_is_checked_against_family_input(base):
 f=build(base);f.grid_identity['evaluation_to_config'][30101]=30102
 with pytest.raises(InputContractError):f.validate()

@pytest.mark.parametrize('field',['family','mapping','size_weights','registry_sha'])
def test_new_identity_not_reused_if_it_contradicts_result(base,result,tmp_path,field):
 # Writer or reader may reject. This is internal consistency, not external authentication.
 d=copy.deepcopy(result);g=d.evidence['grid_identity']
 if field=='family':g['family']='E8'
 elif field=='mapping':g['evaluation_to_config'][30101]=30102
 elif field=='size_weights':g['size_weights']={'L1.00':.8,'L1.20':.1,'L1.50':.1}
 else:g['registry_sha256']='not-a-sha'
 with pytest.raises(InputContractError):
  path=str(tmp_path/'bad.json');sha=write_family_result(d,path);read_family_result(path,sha)

def test_normal_checkpoint_preserves_identity_and_snapshot(base,result,tmp_path):
 f=build(base);r=o.evaluate_family(f,None,80.,400.);saved=copy.deepcopy(r.evidence['grid_identity']);f.grid_identity['family']='E8'
 assert r.evidence['grid_identity']==saved
 path=str(tmp_path/'ok.json');sha=write_family_result(r,path);d=read_family_result(path,sha)
 assert d['result']['evidence']['grid_identity']==saved

def test_optional_covariance_sidecar_not_claimed_verified(base):
 sup=copy.deepcopy(base[2]);
 for s in sup:s.cov_manifest=None
 f=build(base,sup=sup)
 assert f.grid_identity['cov_bound']=={}

def test_legacy_unbound_fixture_remains_available():
 from test_b2 import build_fixture,THR
 fm,fn=build_fixture()['E7'];assert o.evaluate_family(fm,fn,*THR).family=='E7'
