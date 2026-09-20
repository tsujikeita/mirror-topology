"""TEST-ONLY D1 v0.2 contract audit.
Run the unmodified submitted main() with synthetic external files/process metadata.
Use the real registered 30-configuration geometry and principal-root math.
No Colab, CMBtopology physics, live A11 or real-version approval is claimed.
Pins that name artificial external inputs are explicitly rebound inside temporary
fixture copies. Submitted production files and rules remain unchanged.
"""
from pathlib import Path
from types import ModuleType, SimpleNamespace
import copy, hashlib, importlib.util, importlib.metadata, json, os, shutil, subprocess, sys, ast
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
PB=Path(os.environ.get('D1_PB',ROOT)).resolve()
sys.path.insert(0,str(PB))
from step1_engine.grid_registry import load_registry
from step1_engine.grid_manifest import build_configuration_manifest
from step1_engine import legacy_kernel, official_gate
OriginalKernel=legacy_kernel.LegacyKernel
SRC=PB/'d/d1_covgen.py'
ss=importlib.util.spec_from_file_location('d1_v02_under_audit',SRC); d1=importlib.util.module_from_spec(ss);ss.loader.exec_module(d1)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
PROBES={}

def writej(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=1));return p

@pytest.fixture(scope='session',autouse=True)
def save_probes():
 yield
 import tempfile; p=Path(os.environ.get('D1_PROBES', os.path.join(tempfile.gettempdir(),'d1_independent_probes.json')));p.write_text(json.dumps(PROBES,indent=2,ensure_ascii=False,default=str))   # adapted: evidence dir not shipped

@pytest.fixture
def fixture(tmp_path,monkeypatch):
 f=SimpleNamespace(root=tmp_path,pb=tmp_path/'pb',mt=tmp_path/'mt',pc=tmp_path/'pc',ct=tmp_path/'ct',out=tmp_path/'out',calls=[],loads=[],returns=[],fault=None,exit_git_status=False)
 shutil.copytree(PB,f.pb,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','regression_logs'))
 p=copy.deepcopy(json.loads((PB/'d/d1_pins.json').read_text())); f.pins=p
 for b in (f.mt,f.pc,f.ct):b.mkdir()
 # Real registered geometry; the fixture Phase C inventory is not the real final freeze.
 reg=load_registry(str(PB/'tests/assets/a7_circle_geometry.csv'),str(PB/'tests/assets/a6_observer_design_points.json'))
 f.grid=build_configuration_manifest(reg)
 writej(f.pc/'registered/first_wave_configuration_manifest.json',f.grid.as_dict())
 (f.pc/'policy.md').write_text('TEST-ONLY pinned policy')
 writej(f.pc/'PACKET_INVENTORY.json',{'handoff_commit':p['first_wave']['phaseC_handoff_commit'],'files':{str(x.relative_to(f.pc)):{'sha256':sha(x),'bytes':x.stat().st_size} for x in f.pc.rglob('*') if x.is_file()}})
 p['first_wave']['phaseC_inventory_sha256']=sha(f.pc/'PACKET_INVENTORY.json')
 for e in p['external_sources'].values():
  q=f.mt/e['path']; q.write_text('# TEST-ONLY external loader placeholder\n'); e['sha256']=sha(q)
 a11=p['a11_freeze']; cell='# TEST-ONLY A11 generator identity fixture\n'
 writej(f.mt/a11['notebook']['path'],{'cells':[{'source':[]}]*4+[{'source':[cell]}]})
 a11['generator_cell4_sha256']=hashlib.sha256(cell.encode()).hexdigest()
 writej(f.mt/a11['env_lock']['path'],dict(python='3.13.15',versions={k:'fixture' for k in d1.PKGS},requirements_sha256='a'*64,blas_lapack='fixture',platform={}))
 q=f.mt/a11['rules']['path'];q.write_text('TEST-ONLY rules identity fixture')
 for key in ('notebook','env_lock','rules'): a11[key]['sha256']=sha(f.mt/a11[key]['path'])
 # Synthetic diagonal reference, deliberately not a physical A11 covariance.
 A=np.diag(np.linspace(2,4,21)).astype(np.complex128); xc=p['a11_cross_check'];q=f.mt/xc['npy'];q.parent.mkdir(parents=True,exist_ok=True);np.save(q,A)
 rec={'manifest':{'topology':'E7','params':{'LAx':1.0,'LAy':.25,'L1y':1.0,'L2x':.5,'L2z':1.0},'x0':[1.31,.04,.42]},'cov_file_sha256':sha(q),'cov_array_sha256':hashlib.sha256(A.tobytes()).hexdigest()}
 writej(f.mt/xc['manifest'],rec)
 xc.update(manifest_sha256=sha(f.mt/xc['manifest']),npy_sha256=sha(q),array_sha256=rec['cov_array_sha256'])
 for path in ['requirements.txt','topology/src/E1.py','topology/src/E2.py','topology/src/E7.py','topology/src/E8.py','topology/run_topology.py']:
  q=f.ct/path;q.parent.mkdir(parents=True,exist_ok=True);q.write_text('# TEST-ONLY CT source fixture\n')
 def persist_pins():
  writej(f.pb/'d/d1_pins.json',p);iv=json.loads((f.pb/'B2_completion_inventory.json').read_text());iv['d_sha256']['d/d1_pins.json']=sha(f.pb/'d/d1_pins.json');writej(f.pb/'B2_completion_inventory.json',iv)
 f.persist_pins=persist_pins;persist_pins()
 f.env={k:p['environment'][k] for k in ('python','numpy','scipy','healpy','pot','camb')};f.env['blas_threads']=[{'api':'blas','n':2,'owner':'numpy','lib':'openblas'},{'api':'blas','n':1,'owner':'other','lib':'openblas'}]
 monkeypatch.setattr(official_gate,'current_env',lambda:copy.deepcopy(f.env))
 fake_camb=ModuleType('camb');fake_camb.__version__=p['environment']['camb'];monkeypatch.setitem(sys.modules,'camb',fake_camb)
 monkeypatch.setattr(importlib.metadata,'version',lambda n:'fixture-installed')
 real_run=subprocess.run
 def fake_git(args,**kwargs):
  if args[0]!="git":return real_run(args,**kwargs)
  if 'rev-parse' in args:r=subprocess.CompletedProcess(args,0,d1.EXPECTED_CMBTOPO_COMMIT+'\n','')
  elif 'remote' in args:r=subprocess.CompletedProcess(args,0,'https://github.com/CompactCollaboration/CMBtopology.git\n','')
  elif 'status' in args:r=subprocess.CompletedProcess(args,128 if f.exit_git_status else 0,'','fatal: TEST-ONLY status failure' if f.exit_git_status else '')
  else:raise AssertionError(args)
  f.returns.append({'args':args,'rc':r.returncode});return r
 monkeypatch.setattr(subprocess,'run',fake_git)
 def fake_gen(**kwargs):
  f.calls.append(copy.deepcopy(kwargs));folder=Path.cwd()/'runs/fixture';folder.mkdir(parents=True,exist_ok=True)
  np.save(folder/'TT_corr_matrix_l_2_4_lp_2_4.npy',A.copy())
 m=ModuleType('topology.run_topology');m.__file__=str(f.ct/'topology/run_topology.py');m.run_topology=fake_gen
 pkg=ModuleType('topology');pkg.__path__=[str(f.ct/'topology')]
 monkeypatch.setitem(sys.modules,'topology',pkg);monkeypatch.setitem(sys.modules,'topology.run_topology',m)
 def loader(path,lmax):
  f.loads.append(path)
  if f.fault=='loader_exception' and len(f.loads)==2:raise RuntimeError('TEST-ONLY: PSD hard gate failed')
  ar=np.load(path);Cr=ar.real.copy()
  if f.fault=='zero_root' and len(f.loads)==1:Cr[0,0]=0
  return ar,Cr,{'cov_array_sha256':hashlib.sha256(ar.tobytes()).hexdigest(),'fixture_loader':True}
 t1=ModuleType('t1_engine');t1.__file__=str(f.mt/'t1_engine.py');t1.load_cov_full=loader;monkeypatch.setitem(sys.modules,'t1_engine',t1)
 k=OriginalKernel.__new__(OriginalKernel);k.c_pr3=np.array([1064.7,504.6,286.7]);monkeypatch.setattr(legacy_kernel,'LegacyKernel',lambda _:k)
 oldpath=sys.path[:]
 def invoke(extra=()):
  monkeypatch.setattr(sys,'argv',['d1_covgen.py','--mt',str(f.mt),'--phaseb',str(f.pb),'--phasec',str(f.pc),'--ct',str(f.ct),'--out',str(f.out),*extra])
  rc=d1.main();f.result=json.loads((f.out/'d1_run_manifest.json').read_text()) if (f.out/'d1_run_manifest.json').exists() else None
  PROBES[os.environ.get('PYTEST_CURRENT_TEST','unknown').split(' (')[0]]={'rc':rc,'stage':f.result and f.result.get('stage'),'D1_PASS_synthetic_only':f.result and f.result.get('D1_PASS'),'n_generator_calls':len(f.calls),'n_loader_calls':len(f.loads),'gates':f.result and f.result.get('gates'),'failures':f.result and f.result.get('failures'),'has_registry':(f.out/'d1_cov_registry.json').exists()}
  return rc
 f.invoke=invoke
 yield f
 sys.path[:]=oldpath


def test_normal_full_control_flow_30_intakes(fixture):
 f=fixture;assert f.invoke()==0;assert len(f.calls)==31 and len(f.loads)==30
 assert f.result['D1_PASS'] is True # artificial control flow, NEVER a scientific receipt
 out=json.loads((f.out/'d1_cov_registry.json').read_text());assert out['n']==30 and all(x['intake']['pass_'] is True for x in out['configurations'].values())
 # E1 never receives x0; all nonhomogeneous specs retain x0.
 for call in f.calls[1:]: assert ('x0' not in call) == (call['topology']=='E1')
 assert set(f.result['gates'])==set(d1.REQUIRED) and len(d1.REQUIRED)==19

@pytest.mark.parametrize('key,value',[('python','3.13.5'),('numpy','2.3.5'),('pot',None),('blas_threads',[{'api':'blas','n':8,'owner':'numpy','lib':'openblas'}]),('blas_threads',[{'api':'blas','n':2,'owner':'other','lib':'openblas'}])],ids=['python','numpy','missing_pot','threads_8','no_numpy_owner'])
def test_wrong_environment_stops_before_physics(fixture,key,value):
 f=fixture;f.env[key]=value;assert f.invoke()==1 and f.result['stage']=='environment' and not f.calls

def test_selftest_can_diagnose_wrong_environment_but_never_official(fixture):
 f=fixture;f.env['python']='3.13.5';assert f.invoke(['--selftest-skip-env-lock','--selftest-configs','10101','--selftest-skip-cross-check'])==1
 assert len(f.calls)==1 and f.result['D1_PASS'] is False and f.result['gates']['G_env_lock'] is False

@pytest.mark.parametrize('kind',['phaseC_member','external_loader','a11_cell','cross_manifest','cross_file','cross_array_expected'])
def test_changed_trusted_inputs_stop_before_physics(fixture,kind):
 f=fixture;p=f.pins
 if kind=='phaseC_member':q=f.pc/'policy.md';q.write_text('changed policy')
 elif kind=='external_loader':(f.mt/'t1_engine.py').write_text('changed loader')
 elif kind=='a11_cell':
  q=f.mt/p['a11_freeze']['notebook']['path'];n=json.loads(q.read_text());n['cells'][4]['source']=['# changed\n'];writej(q,n)
  p['a11_freeze']['notebook']['sha256']=sha(q);f.persist_pins()
 elif kind=='cross_manifest':q=f.mt/p['a11_cross_check']['manifest'];q.write_text(q.read_text()+'\n')
 elif kind=='cross_file':q=f.mt/p['a11_cross_check']['npy'];q.write_bytes(q.read_bytes()+b'changed')
 elif kind=='cross_array_expected':p['a11_cross_check']['array_sha256']='0'*64;f.persist_pins()
 assert f.invoke()==1 and f.result['stage']=='trusted_inputs' and not f.calls


def test_normal_grid_validation_passes_without_cross(fixture):
 f=fixture;assert f.invoke(['--selftest-skip-cross-check','--selftest-configs','10101'])==1
 assert f.result['gates']['G_grid_manifest_bound'] is True and len(f.calls)==1 and f.result['D1_PASS'] is False


def edit_grid_rebind_only_file_hashes(f):
 q=f.pc/'registered/first_wave_configuration_manifest.json';x=json.loads(q.read_text());x['configurations'][0]['weight']=.123;writej(q,x)
 iv=json.loads((f.pc/'PACKET_INVENTORY.json').read_text());iv['files'][str(q.relative_to(f.pc))]={'sha256':sha(q),'bytes':q.stat().st_size};writej(f.pc/'PACKET_INVENTORY.json',iv)
 f.pins['first_wave']['phaseC_inventory_sha256']=sha(f.pc/'PACKET_INVENTORY.json');f.persist_pins()


def test_saved_grid_semantic_error_is_rejected(fixture):
 f=fixture;edit_grid_rebind_only_file_hashes(f);assert f.invoke(['--selftest-skip-cross-check'])==1 and f.result['stage']=='grid'
 assert not f.calls


def test_grid_rejection_precedes_cross_check_generation(fixture):
 f=fixture;edit_grid_rebind_only_file_hashes(f);assert f.invoke()==1 and f.result['stage']=='grid'
 assert not f.calls, 'saved-grid preflight occurs AFTER expensive cross-check generation'


def test_first_false_intake_stops_saves_config_and_prior(fixture):
 f=fixture;f.fault='zero_root';assert f.invoke()==1 and f.result['stage']=='intake_failure';assert len(f.calls)==2 and len(f.loads)==1
 x=json.loads((f.out/'d1_cov_registry.json').read_text());assert x['failed']['config_id']==10101 and x['n']==1
 assert x['configurations']['10101']['intake']['pass_'] is False


def test_loader_exception_stops_saves_failing_config_and_previous(fixture):
 f=fixture;f.fault='loader_exception';assert f.invoke()==1 and f.result['D1_PASS'] is False
 assert len(f.calls)==3 and len(f.loads)==2 # cross-check + 2 first-wave configs
 p=f.out/'d1_cov_registry.json'
 assert p.exists(), 'actual loader/geometry exceptions bypass the per-config failure/partial-registry writer'
 x=json.loads(p.read_text());assert x['failed']['config_id']==10201
 assert x['configurations']['10101']['intake']['pass_'] is True


def test_git_status_failure_is_not_clean_tree(fixture):
 f=fixture;f.exit_git_status=True;assert f.invoke()==1
 assert f.result['gates']['G_ct_clean'] is False and not f.calls


def test_nonempty_out_rejected_before_touching_records(fixture):
 f=fixture;f.out.mkdir();q=f.out/'d1_run_manifest.json';q.write_text('{"prior":true}');before=sha(q)
 assert f.invoke(['--profile','bogus'])==2 and sha(q)==before
 assert sorted(x.name for x in f.out.iterdir())==['d1_run_manifest.json'] and not f.calls
