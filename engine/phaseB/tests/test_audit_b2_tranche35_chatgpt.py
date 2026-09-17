"""Independent B-2 handoff checks. Finite synthetic banks and test-only mean-distance W2.
No physical covariance or registered-scale Monte Carlo calibration is asserted.
Locally generated pickle files are transient test caches only, not shipped results.
"""
import os,sys,copy,pickle,json,hashlib,ast
from pathlib import Path
import numpy as np
import pytest
import tempfile
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]));WORK=Path(os.environ.get('AUDIT35_WORK',tempfile.mkdtemp(prefix='audit35_')));OUT=WORK/'evidence';sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
for _d in ('cache','evidence','evidence/reference','evidence/archives','evidence/logs'): (WORK/_d).mkdir(parents=True,exist_ok=True)
from step1_engine import twelve_assets as ta,stage12,threshold_evaluator as te, integrated_runner as ir,serialization as ser
from step1_engine.errors import InputContractError
from step1_engine.archive import Archive,ArchiveRef,resolve_transition_archive
from step1_engine.checkpoint import write_family_result,read_family_result,binding_manifest
from step1_engine.grid_registry import load_registry
from test_b2_tranche20 import A6,A7
from fixture32 import multifamily_trigger_only_pseudo,twelve_from_cases
from audit_fixture30 import diagnostic_cases

@pytest.fixture(scope='module')
def fixtures():
 if (WORK/'cache/base.pkl').exists():
  with (WORK/'cache/base.pkl').open('rb') as h:b=pickle.load(h)
  with (WORK/'cache/twelve.pkl').open('rb') as h:t=pickle.load(h)
  return b,t
 from fixture32 import base
 b=base();t=twelve_from_cases(b['cases']);return b,t      # regenerated in-process (no pickle cache shipped)
@pytest.fixture
def reg():return load_registry(A7,A6)
@pytest.fixture
def asset(reg):return ta.build_twelve_assets(reg,['E7'])

def eval_full(b,t,a,thr=(100.,550.)):
 views={k.split('/')[1]:v for k,v in b['cases'].items()}
 par=ir.assemble_parent(b['reg'],b['man'],'E7',{s:v[:2] for s,v in views.items()})
 return te.evaluate_family_full(b['reg'],b['man'],'E7',par,views,b['ctx'],b['ctx'].context_sha256,*thr,t,with_diagnostics=False,twelve_assets=a)

def run(b,t,a,path,thr=(100.,550.),xs=None,ys=None,**kw):
 ar=Archive(str(path));r=ir.run_first_wave(b['reg'],b['man'],b['cases'],b['ctx'],b['ctx'].context_sha256,thr,xs or [thr[0]],ys or [thr[1]],ar,
    twelve_inputs=None if t is None else {'E7':t},twelve_assets=a,expected_twelve_assets_sha256=a.sha256,**kw)
 return r,ar

def test_packet_module_hashes_and_function_counts():
 inv=json.loads((ROOT/'B2_completion_inventory.json').read_text());mods={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (ROOT/'step1_engine').glob('*.py')}
 assert inv['modules']==mods==binding_manifest()['modules']
 counts={f.name:sum(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test_') for n in ast.walk(ast.parse(f.read_text()))) for f in (ROOT/'tests').glob('test*.py')}
 assert inv['tests']==counts and inv['total_test_functions']==sum(counts.values())
 assert set(mods)==set(binding_manifest()['modules']) # counts are recorded, not frozen for future tranches

def test_warm_restore_cannot_self_issue_intake_receipt(reg,asset):
 restored=ta.asset_from_dict(ser.loads(ser.dumps(asset.as_dict())))
 assert ta._VERIFIED # warm per-member cache does not authorize whole-asset restore
 with pytest.raises(InputContractError):restored.get('E7','L1.00')
 ta.verify_twelve_assets(restored,reg,asset.sha256)
 assert restored.snapshot(reg,asset.sha256).payload_sha()==asset.sha256

def test_late_member_failure_is_atomic(reg,asset,monkeypatch):
 restored=ta.asset_from_dict(ser.loads(ser.dumps(asset.as_dict())));ta._VERIFIED.clear();calls=[];orig=ta.verify_twelve
 def reject_third(m):
  calls.append(m.size_id)
  if len(calls)==3:raise InputContractError('audit: third member re-generation failure')
  return orig(m)
 monkeypatch.setattr(ta,'verify_twelve',reject_third)
 with pytest.raises(InputContractError):ta.verify_twelve_assets(restored,reg,asset.sha256)
 assert len(calls)==3 and not ta._VERIFIED and restored._intake_sha256 is None

def test_snapshot_is_independent_without_changing_payload(reg,asset):
 s=asset.snapshot(reg,asset.sha256);old=ser.dumps(s.as_dict());asset.manifests['E7']['L1.00'].points[3][0]+=.001
 assert ser.dumps(s.as_dict())==old and s.validate(reg,s.sha256)
 with pytest.raises(InputContractError):asset.validate(reg)

def test_e7_points_agree_with_independent_global_greedy(reg,asset):
 axis=np.arange(200,2301,dtype=np.int64)*1e-4;selected=list(np.array(reg.anchors['E7']).ravel())
 for _ in range(9):
  dd=np.min(np.abs(axis[:,None]-np.array(selected)[None,:]),axis=1);maximum=max(dd)
  selected.append(axis[np.flatnonzero(dd>=maximum-1e-12)[0]])
 for size in reg.surviving['E7']:assert np.array_equal(np.array(asset.get('E7',size).points).ravel(),selected)
 assert min(abs(a-b) for i,a in enumerate(selected) for b in selected[i+1:])>=.015
 (OUT/'reference/e7_greedy.json').write_text(ser.dumps(dict(points=selected,asset_sha=asset.sha256)))

@pytest.fixture(scope='module')
def normal(fixtures):
 b,t=fixtures;a=ta.build_twelve_assets(b['reg'],['E7']);r,ar=run(b,t,a,OUT/'archives/normal')
 g=ar.get(ArchiveRef(**r.archive_refs['twelve_family_core:E7']))
 (OUT/'reference/normal12_result.json').write_text(ser.dumps(g));(OUT/'reference/normal_run.json').write_text(ser.dumps(r.as_dict()))
 return r,ar,g,a

def test_normal_full_result_archive_and_semantic_reader(normal,tmp_path):
 r,ar,g,a=normal; reopened=Archive(ar.root);rr=ir.RunManifest(**reopened.get(ArchiveRef(**r.binding['run_manifest_ref'])))
 assert rr.payload_sha()==r.payload_sha() and rr.binding['twelve_assets_sha256']==a.sha256
 assert len(g['per_config'])==36 and len(g['native']['per_config'])==36
 assert ser.dumps(reopened.get(ArchiveRef(**rr.archive_refs['twelve_family_core:E7'])))==ser.dumps(g)
 path=str(tmp_path/'12.json');sha=write_family_result(g,path);res=read_family_result(path,sha)
 assert ser.dumps(res['result'])==ser.dumps(g) and reopened.verify_all()['ok']
 for key,c in r.cases.items():
  fam,size=key.split('/'); tr=stage12.StageTransition(**r.families[fam]['transitions'][size])
  assert resolve_transition_archive(reopened,tr,ArchiveRef(**c['result_ref']))['size_id']==size

def test_consumer_reuse_matches_regeneration_without_generator_calls(fixtures,monkeypatch):
 b,t=fixtures;a=ta.build_twelve_assets(b['reg'],['E7']);cold=eval_full(b,t,None)
 def forbidden(*x,**kw):raise AssertionError('regeneration on successful reuse')
 monkeypatch.setattr(stage12,'generate_twelve',forbidden);monkeypatch.setattr(te,'generate_twelve',forbidden)
 warm=eval_full(b,t,a)
 assert ser.dumps(cold.twelve)==ser.dumps(warm.twelve) and cold.eligible_truths==warm.eligible_truths

def test_wrong_external_asset_sha_prevents_numeric_entry(fixtures,tmp_path,monkeypatch):
 b,t=fixtures;a=ta.build_twelve_assets(b['reg'],['E7'])
 def forbidden(*x,**kw):raise AssertionError('numeric evaluator entered')
 monkeypatch.setattr(ir,'evaluate_family_full',forbidden)
 with pytest.raises(InputContractError):
  ir.run_first_wave(b['reg'],b['man'],b['cases'],b['ctx'],b['ctx'].context_sha256,(100.,550.),[100.],[550.],Archive(str(tmp_path)),twelve_inputs={'E7':t},twelve_assets=a,expected_twelve_assets_sha256='0'*64)

def test_original_caller_asset_edit_does_not_change_consumed_snapshot(fixtures,tmp_path,monkeypatch):
 b,t=fixtures;a=ta.build_twelve_assets(b['reg'],['E7']);sha=a.sha256;old=ir.evaluate_family_full;seen=[]
 def wrapped(*args,**kw):
  seen.append(kw['twelve_assets']);out=old(*args,**kw)
  if len(seen)==1:a.manifests['E7']['L1.00'].points[3][0]+=.001
  return out
 monkeypatch.setattr(ir,'evaluate_family_full',wrapped);r,ar=run(b,t,a,tmp_path)
 assert len(seen)==2 and seen[0] is seen[1] and seen[0] is not a
 assert r.binding['twelve_assets_sha256']==sha and r.fingerprints['at_gate']==r.fingerprints['at_end']
 assert ar.verify_all()['ok']

@pytest.fixture(scope='module')
def multi(fixtures):return multifamily_trigger_only_pseudo(fixtures[0])

def test_nonexpansion_e1_and_pseudo_only_expansion_with_asset(multi,fixtures):
 _,t=fixtures;a=ta.build_twelve_assets(multi['reg'],['E7'])
 r,ar=run(multi,t,a,OUT/'archives/multifamily',(200.,1000.),[80.,200.],[400.,1000.],require_all_families=True)
 assert len(r.cases)==12 and set(r.families)=={'E1','E2','E7','E8'}
 assert not any(f['expand_family'] for f in r.families.values())
 assert r.families['E1']['eligibility'].startswith('eligible: E1')
 assert r.per_pseudo_family_status[0]['E7']['twelve']['evaluated']
 assert not r.per_pseudo_family_status[1]['E7']['expand_family']
 assert r.branch_completeness['missing_branches']==[]
 assert all(r.calibration[k]['full_procedure'] for k in ('support','strong')) and not r.final_label_released
 assert ar.verify_all()['ok'];(OUT/'reference/multifamily_asset.json').write_text(ser.dumps(r.as_dict()))

def test_optional_diagnostic_tech_not_a_veto_with_asset(fixtures):
 b,_=fixtures;t=twelve_from_cases(diagnostic_cases(b['reg'],b['man'],False));a=ta.build_twelve_assets(b['reg'],['E7'])
 r=eval_full(b,t,a,(80.,400.));g=r.twelve['full_result']
 assert g['per_size_diagnostic']['L1.00']['decision']['technical_status']=='technical_fail'
 assert g['decision']['technical_status']=='ok' and g['logD']['ci'] is None
 assert r.eligible_truths['support'] is True and r.twelve['family_local_completion']
 (OUT/'reference/optional_diagnostic_tech.json').write_text(ser.dumps(r.summary()))

def test_required_parent_tech_preserved_with_asset(fixtures):
 b,_=fixtures;t=twelve_from_cases(diagnostic_cases(b['reg'],b['man'],True));a=ta.build_twelve_assets(b['reg'],['E7'])
 r=eval_full(b,t,a,(80.,400.))
 assert set(r.eligible_truths.values())=={'technical_fail'} and not r.twelve['family_local_completion']
 (OUT/'reference/required_parent_tech.json').write_text(ser.dumps(r.summary()))
