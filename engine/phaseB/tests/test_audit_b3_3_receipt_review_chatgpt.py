"""Independent B-3-3 contract checks.
The real, already accepted asset bytes are used. No lattice regeneration,
CMB generation, or OT calculation is performed. Injection tests change only
process-local functions to expose callers and atomicity; original files remain unchanged.
"""
from pathlib import Path
import os,sys,copy,json,hashlib,types
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from step1_engine import twelve_assets as ta,stage12,serialization as ser
from step1_engine.grid_registry import load_registry,registry_from_dict,registry_from_dict_bound
from step1_engine.errors import InputContractError
P=ROOT/'registered_assets/b3_2_twelve_assets.json';RID='B3_2A_7240c06f255c'
import tempfile
OUT=Path(os.environ.get('B33_PROBES',os.path.join(tempfile.mkdtemp(prefix='b33_'),'probes.json')))
PROBES={}
def record(k,v):
 PROBES[k]=v;OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(PROBES,ensure_ascii=False,indent=2))
@pytest.fixture(autouse=True)
def cache_isolation():
 saved=set(ta._VERIFIED);ta._VERIFIED.clear();yield;ta._VERIFIED.clear();ta._VERIFIED.update(saved)
@pytest.fixture
def reg():return load_registry(str(ROOT/'tests/assets/a7_circle_geometry.csv'),str(ROOT/'tests/assets/a6_observer_design_points.json'))
def forbid(*a,**kw):raise AssertionError('unexpected lattice regeneration')

def test_registered_intake_and_all_members_need_no_regeneration(reg,monkeypatch):
 monkeypatch.setattr(stage12,'generate_twelve',forbid);monkeypatch.setattr(ta,'verify_twelve',forbid)
 a=ta.intake_registered_twelve_assets(str(P),reg,RID)
 assert a.validate(reg,a.sha256) and a.verification['manifests']==9
 assert len(ta._VERIFIED)==9
 for f in a.families:
  for s in reg.surviving[f]:assert len(a.get(f,s).points)==12
 b=a.snapshot(reg,a.sha256);assert b.payload_sha()==a.payload_sha()
 record('direct_reuse',{'members':9,'regeneration_calls':0,'asset_sha256':a.sha256})

def test_unknown_receipt_rejected_without_cache(reg):
 with pytest.raises(InputContractError):ta.intake_registered_twelve_assets(str(P),reg,'not-registered')
 assert not ta._VERIFIED

def test_same_json_different_file_bytes_rejected(reg,tmp_path):
 q=tmp_path/'pretty.json';q.write_text(json.dumps(json.loads(P.read_text()),indent=4))
 with pytest.raises(InputContractError):ta.intake_registered_twelve_assets(str(q),reg,RID)
 assert not ta._VERIFIED

def test_modified_member_rejected_without_cache(reg,tmp_path):
 d=json.loads(P.read_text());d['manifests']['E7']['L1.00']['points'][5][0]+=.001;q=tmp_path/'modified.json';q.write_text(json.dumps(d))
 with pytest.raises(InputContractError):ta.intake_registered_twelve_assets(str(q),reg,RID)
 assert not ta._VERIFIED

def test_changed_registry_with_consistent_hash_rejected(reg):
 reg.anchors['E7'][0][0]+=.001;reg.registry_sha256=reg.payload_sha();assert reg.validate()
 with pytest.raises(InputContractError):ta.intake_registered_twelve_assets(str(P),reg,RID)
 assert not ta._VERIFIED

def test_member_return_is_detached(reg):
 a=ta.intake_registered_twelve_assets(str(P),reg,RID);old=copy.deepcopy(a.manifests['E7']['L1.00'].points)
 m=a.get('E7','L1.00');m.points[5][0]+=.001
 assert a.get('E7','L1.00').points==old

def test_mutated_live_asset_rejected(reg):
 a=ta.intake_registered_twelve_assets(str(P),reg,RID);a.manifests['E7']['L1.00'].points[5][0]+=.001
 with pytest.raises(InputContractError):a.get('E7','L1.00')

def test_ordinary_deserialization_does_not_issue_whole_receipt(reg):
 a=ta.intake_registered_twelve_assets(str(P),reg,RID);b=ta.asset_from_dict(a.as_dict())
 with pytest.raises(InputContractError):b.get('E7','L1.00')

def test_late_failure_does_not_publish_partial_cache(reg,monkeypatch):
 orig=stage12._structural_checks;seen=[]
 def fail_late(m):
  seen.append((m.family,m.size_id))
  if len(seen)==18:raise InputContractError('TEST-ONLY late validation failure')
  return orig(m)
 monkeypatch.setattr(stage12,'_structural_checks',fail_late)
 with pytest.raises(InputContractError):ta.intake_registered_twelve_assets(str(P),reg,RID)
 assert len(seen)==18 and not ta._VERIFIED

def test_source_bound_restoration_is_accepted(reg):
 b=registry_from_dict_bound(reg.as_dict(),str(ROOT/'tests/assets/a7_circle_geometry.csv'),str(ROOT/'tests/assets/a6_observer_design_points.json'))
 a=ta.intake_registered_twelve_assets(str(P),b,RID);assert a.validate(b)

def test_internal_only_registry_must_not_receive_source_bound_intake(reg):
 internal=registry_from_dict(reg.as_dict());assert internal.registry_sha256==reg.registry_sha256
 old_rejected=False
 try:ta._registry(internal)
 except InputContractError:old_rejected=True
 accepted=False;get_ok=False;downstream_rejected=False
 try:
  a=ta.intake_registered_twelve_assets(str(P),internal,RID);accepted=True;get_ok=len(a.get('E7','L1.00').points)==12
  try:a.snapshot(internal)
  except InputContractError:downstream_rejected=True
 except InputContractError:pass
 record('source_bound_contract',{'scope':internal.verification_scope,'old_guard_rejected':old_rejected,'new_intake_accepted':accepted,'get_succeeded':get_ok,'later_snapshot_rejected':downstream_rejected,'original_asset_and_registry_payload_unmodified':True})
 assert old_rejected and not accepted

def test_non_grid_registry_must_be_rejected(reg):
 fake=types.SimpleNamespace(validate=lambda:True,registry_sha256=reg.registry_sha256,anchors=reg.anchors,surviving=reg.surviving)
 with pytest.raises(InputContractError):ta.intake_registered_twelve_assets(str(P),fake,RID)

@pytest.mark.parametrize('mutation',['done','asset','filesha'])
def test_no_fabricated_authority_from_verification_field(reg,tmp_path,mutation):
 # Verification fields are not part of the asset payload, but raw file binding still covers them.
 d=json.loads(P.read_text());d['verification']={'intake':mutation};q=tmp_path/'verification.json';q.write_text(json.dumps(d))
 with pytest.raises(InputContractError):ta.intake_registered_twelve_assets(str(q),reg,RID)
 assert not ta._VERIFIED

def test_runner_currently_reenters_regeneration_characterization(reg,monkeypatch,tmp_path):
 from step1_engine.production import production_manifest
 from step1_engine import integrated_runner as ir
 # The tested early runner path does not consume case values or call any W2 math.
 # Context stub models ONLY a successfully validated context for this control-flow probe.
 ctx=types.SimpleNamespace(validate=lambda *a:True)
 ctx.snapshot=lambda:ctx
 a=ta.intake_registered_twelve_assets(str(P),reg,RID);man=production_manifest(reg);calls=[]
 class EnteredRegeneration(Exception):pass
 def hit(m):calls.append((m.family,m.size_id));raise EnteredRegeneration()
 monkeypatch.setattr(ta,'verify_twelve',hit)
 with pytest.raises(EnteredRegeneration):
  ir.run_first_wave(reg,man,{'E7/L1.00':None},ctx,'TEST-ONLY',(100.,550.),[100.],[550.],None,twelve_assets=a,expected_twelve_assets_sha256=a.sha256)
 assert calls==[('E2','L1.00')]
 record('runner_regeneration',{'receipt_intake_completed':True,'runner_entered_regeneration_for':calls,'test_only_context_stub':True,'actual_heavy_regeneration_performed':False})

def test_rules_document_annotation_requires_binding_update(tmp_path):
 from step1_engine import rules_config as rc
 j=json.loads((ROOT/'rules_tables_v1.json').read_text());doc=j['rules_document']['name']
 tp=tmp_path/'rules_tables_v1.json';tp.write_bytes((ROOT/'rules_tables_v1.json').read_bytes())
 dp=tmp_path/doc;dp.write_bytes((ROOT/doc).read_bytes())
 cfg=rc._load(str(tp));assert rc.verify_binding(cfg)['ok']
 dp.write_text(dp.read_text()+'\n<!-- TEST-ONLY registration reference, constants unchanged -->\n')
 with pytest.raises(ValueError,match='rules document bytes'):rc.verify_binding(cfg)
 record('document_binding',{'original_pair_valid':True,'document_only_annotation_rejected':True,'numerical_constants_changed':False})
