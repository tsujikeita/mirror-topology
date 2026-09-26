"""D3-2a audit: execute the unmodified submitted main under TEST-ONLY dependencies.
The production files are immutable. Only a temporary Phase-C policy/pins are rebound.
Real registered D3 geometry, case-table source authentication, D1 metadata and actual
LegacyKernel root math are used. CT physics, loader transform, live environment, Git,
and healpy vec2ang are explicit test doubles; no physical PC1 acceptance is claimed.
"""
from pathlib import Path
from types import SimpleNamespace, ModuleType
import ast, builtins, copy, hashlib, importlib.util, importlib.metadata, inspect, json, os, shutil, subprocess, sys
import numpy as np
import pytest
PB=Path(os.environ.get('D3_T2A_PB',Path(__file__).resolve().parents[1])).resolve()
import tempfile
EVID=Path(os.environ.get('D3_T2A_EVID',os.path.join(tempfile.gettempdir(),'d3_t2a_probes'))).resolve();EVID.mkdir(parents=True,exist_ok=True)   # adapted
sys.path.insert(0,str(PB))
from step1_engine import legacy_kernel,official_gate,production
Klass=legacy_kernel.LegacyKernel
ss=importlib.util.spec_from_file_location('d3_t2a_submitted_main',PB/'d/d3_covgen.py');d3=importlib.util.module_from_spec(ss);ss.loader.exec_module(d3)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
asha=lambda a:hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def writej(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=1));return p

def file_state(p):return {str(x.relative_to(p)):sha(x) for x in p.rglob('*') if x.is_file()}

@pytest.fixture
def fx(tmp_path,monkeypatch):
 f=SimpleNamespace(root=tmp_path,pb=tmp_path/'pb',mt=tmp_path/'mt',pc=tmp_path/'pc',ct=tmp_path/'ct',out=tmp_path/'out',calls=[],loads=[],fault=None,fault_done=False,git_fault=None,fail_call=None,fail_load=None,mutations=[],family='E7',result=None)
 shutil.copytree(PB,f.pb,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','regression_logs'))
 for x in (f.mt,f.pc,f.ct):x.mkdir()
 f.pins=json.loads((f.pb/'d/d3_pins.json').read_text())
 (f.pc/'policy.md').write_text('TEST-ONLY Phase-C fixture (not the production freeze)\n')
 writej(f.pc/'PACKET_INVENTORY.json',{'files':{'policy.md':{'sha256':sha(f.pc/'policy.md'),'bytes':(f.pc/'policy.md').stat().st_size}}})
 f.pins['phaseC_inventory_sha256']=sha(f.pc/'PACKET_INVENTORY.json')
 def repin():
  writej(f.pb/'d/d3_pins.json',f.pins);inv=json.loads((f.pb/'B2_completion_inventory.json').read_text());inv['d_sha256']['d/d3_pins.json']=sha(f.pb/'d/d3_pins.json');writej(f.pb/'B2_completion_inventory.json',inv)
 f.repin=repin;repin()
 nb=f.mt/'results/step1_phaseA/A11_freeze/MirrorTopology_Step1_A11_x0bridge_v1.4.1.ipynb';nb.parent.mkdir(parents=True)
 shutil.copyfile(PB/'registered_assets/a11/MirrorTopology_Step1_A11_x0bridge_v1.4.1.ipynb',nb)
 shutil.copytree(PB/'registered_assets/ct_pinned/topology',f.ct/'topology');(f.ct/'requirements.txt').write_text('# TEST-ONLY dependency record\n')
 f.env={k:f.pins['environment'][k] for k in ('python','numpy','scipy','healpy','pot','camb')};f.env['blas_threads']=[dict(api='blas',n=2,owner='numpy',lib='openblas'),dict(api='blas',n=1,owner='other',lib='openblas')]
 monkeypatch.setattr(official_gate,'current_env',lambda:copy.deepcopy(f.env))
 cm=ModuleType('camb');cm.__version__=f.pins['environment']['camb'];monkeypatch.setitem(sys.modules,'camb',cm)
 monkeypatch.setattr(importlib.metadata,'version',lambda n:'TEST_ONLY_installed')
 realrun=subprocess.run
 def git(args,**kw):
  if args[0]!='git':return realrun(args,**kw)
  s='';rc=0
  if 'rev-parse' in args:s=d3.EXPECTED_CMBTOPO_COMMIT+'\n'
  elif 'remote' in args:s='https://github.com/CompactCollaboration/CMBtopology.git\n'
  elif 'status' not in args:raise AssertionError(args)
  if f.git_fault and f.git_fault in args:rc=128;s=''
  return subprocess.CompletedProcess(args,rc,s,'TEST_ONLY git failure' if rc else '')
 monkeypatch.setattr(subprocess,'run',git)
 # Real submitted quadrature, with a declared analytic vec2ang substitute, not healpy.
 hp=ModuleType('healpy')
 first_angles=[]
 def vec2ang(dirs):
  v=np.asarray(dirs,float);n=np.linalg.norm(v,axis=-1)
  ans=(np.arccos(np.clip(v[...,2]/n,-1,1)), np.mod(np.arctan2(v[...,1],v[...,0]),2*np.pi))
  if not first_angles:first_angles.append(copy.deepcopy(ans))
  if f.fault=='wrong_transform_geometry':return copy.deepcopy(first_angles[0])
  return ans
 hp.vec2ang=vec2ang;monkeypatch.setitem(sys.modules,'healpy',hp)
 sp=importlib.util.spec_from_file_location('t2b2_bridge',PB/'tests/reference_assets/t2b2_bridge.py');br=importlib.util.module_from_spec(sp);sp.loader.exec_module(br);monkeypatch.setitem(sys.modules,'t2b2_bridge',br)
 A=np.diag(np.linspace(2.,4.,21)).astype(np.complex128);f.A=A
 cmapping=json.loads((PB/'d/d3_config_map.json').read_text());basecoords={tuple(r['x0_CT']) for r in cmapping['configurations'] if r['origin']=='twelve_added'}
 def gen(**kw):
  c=copy.deepcopy(kw);c['is_new_base']=tuple(c['x0']) in basecoords;f.calls.append(c)
  if f.fail_call==len(f.calls):raise RuntimeError('TEST_ONLY generator failure')
  ar=A.copy()
  if not c['is_new_base'] and f.fault=='generated_finite_nonmatch':ar*=2
  p=Path.cwd()/'runs/TEST_ONLY';p.mkdir(parents=True,exist_ok=True);np.save(p/'TT_corr_matrix_l_2_4_lp_2_4.npy',ar)
 topo=ModuleType('topology');topo.__path__=[str(f.ct/'topology')]
 rt=ModuleType('topology.run_topology');rt.run_topology=gen;rt.__file__=str(f.ct/'topology/run_topology.py')
 monkeypatch.setitem(sys.modules,'topology',topo);monkeypatch.setitem(sys.modules,'topology.run_topology',rt)
 def load(path,lmax):
  p=Path(path);f.loads.append(str(p));is_new=p.is_relative_to(f.out)
  # v2 passes a hash-checked temporary copy to its frozen file loader.
  source=p
  if p.parent.name=='bound_load':
   source=f.out/'cov_cache'/p.name
   if not source.exists():source=f.pb/'registered_assets/d1/cov_cache'/p.name
  is_new=source.is_relative_to(f.out)
  rec=json.loads(Path(str(source)+'.manifest.json').read_text()) if is_new else None
  isclone=is_new and tuple(rec['manifest']['x0']) not in basecoords
  if f.fail_load==len(f.loads):raise RuntimeError('TEST_ONLY loader failure')
  ar=np.load(p);Cr=ar.real.copy() if is_new else A.real.copy() # D1 raw identity retained; artificial transform intentionally substitutes the same fixture C0.
  meta={'cov_array_sha256':asha(ar),'TEST_ONLY_loader':True}
  if isclone and f.fault in ('bad_clone_meta','nan_clone','overflow_clone','wrong_clone_shape','zero_clone','complex_clone') and not f.fault_done:
   if f.fault=='bad_clone_meta':meta['cov_array_sha256']='0'*64
   elif f.fault=='nan_clone':Cr[0,0]=np.nan
   elif f.fault=='overflow_clone':Cr*=1e307
   elif f.fault=='wrong_clone_shape':Cr=Cr[:1,:] # broadcasts to21x21 in submitted comparison
   elif f.fault=='zero_clone':Cr[:]=0
   elif f.fault=='complex_clone':Cr=Cr.astype(complex);Cr[0,0]+=1e-7j
   f.fault_done=True
  return ar,Cr,meta
 # The prior source-byte faults are now placed just before load_bound captures
 # the ORIGINAL covariance file (not inside the new temporary loader copy).
 realopen=builtins.open
 def source_open(file,mode='r',*args,**kwargs):
  try:p=Path(file)
  except TypeError:return realopen(file,mode,*args,**kwargs)
  frame=inspect.currentframe().f_back
  if mode=='rb' and frame.f_code.co_name=='load_bound' and p.parent==f.out/'cov_cache' and f.fault in ('clone_append','clone_swap') and not f.fault_done:
   rec=json.loads(Path(str(p)+'.manifest.json').read_text())
   if tuple(rec['manifest']['x0']) not in basecoords:
    before=sha(p)
    if f.fault=='clone_append':p.write_bytes(p.read_bytes()+b'TEST_ONLY changed before snapshot')
    else:np.save(p,2*A)
    f.mutations.append(dict(file=str(p),expected=rec['cov_file_sha256'],before=before,after=sha(p)));f.fault_done=True
  return realopen(file,mode,*args,**kwargs)
 monkeypatch.setattr(builtins,'open',source_open)
 t1=SimpleNamespace(load_cov_full=load)
 def verifyloader(*_):
  if f.fault=='loader_preflight':raise RuntimeError('TEST_ONLY external loader binding failure')
  return t1,dict(scope='TEST_ONLY_external_transform',files_not_approved=True)
 monkeypatch.setattr(production,'_verified_frozen_loader',verifyloader)
 k=Klass.__new__(Klass);k.c_pr3=np.array([1064.7,504.6,286.7]);monkeypatch.setattr(legacy_kernel,'LegacyKernel',lambda _:k)
 oldpath=sys.path[:]
 def invoke(extra=(),out=None):
  if out is not None:f.out=Path(out)
  argv=['d3_covgen.py','--mt',str(f.mt),'--phaseb',str(f.pb),'--phasec',str(f.pc),'--ct',str(f.ct),'--out',str(f.out),'--family',f.family,*extra]
  monkeypatch.setattr(sys,'argv',argv);rc=d3.main();f.rc=rc
  p=f.out/'d3_run_manifest.json';f.result=json.loads(p.read_text()) if p.exists() else None
  return rc
 f.invoke=invoke
 yield f
 name=os.environ.get('PYTEST_CURRENT_TEST','unknown').split(' (')[0].split('::')[-1]
 r=f.result or {};outfiles=file_state(f.out) if f.out.exists() else {}
 data=dict(test=name,scope=__doc__,rc=getattr(f,'rc',None),stage=r.get('stage'),D3_PASS_synthetic_only=r.get('D3_PASS'),required_count=len(r.get('required_inventory',[])),gate_count=len(r.get('gates',{})),failures=r.get('failures'),n_bases=r.get('n_bases'),n_cases=r.get('n_cases'),generator_calls=len(f.calls),loader_calls=len(f.loads),mutations=f.mutations,pc1_status=r.get('pc1_status'),output_files=outfiles)
 for nm in ('d3_cov_registry.json','d3_pc1_results.json','d3_partial_evidence.json'):
  p=f.out/nm
  if p.exists():data[nm]=json.loads(p.read_text())
 writej(EVID/(name.replace('/','_')+'.json'),data)
 sys.path[:]=oldpath

@pytest.mark.parametrize('fam,nb,nc,ng',[('E2',27,36,63),('E7',27,36,63),('E8',27,72,99)])
def test_normal_full_family(fx,fam,nb,nc,ng):
 f=fx;f.family=fam;assert f.invoke()==0
 assert f.result['D3_PASS'] is True and f.result['n_bases']==nb and f.result['n_cases']==nc and len(f.calls)==ng
 assert all(x['status']=='PC1_PASS' for x in f.result['pc1_status'].values())
 for rel,item in f.result['output_inventory'].items():assert sha(f.out/rel)==item['sha256']

def test_valid_finite_nonmatch_is_not_a_technical_run_failure(fx):
 f=fx;f.fault='generated_finite_nonmatch';assert f.invoke()==0
 assert f.result['D3_PASS'] is True and all(x['status']=='PC1_FAIL' for x in f.result['pc1_status'].values())
 assert all(np.isfinite(x['max_rel']) for x in f.result['pc1_status'].values())

@pytest.mark.parametrize('fault',['clone_append','clone_swap','bad_clone_meta','nan_clone','overflow_clone','wrong_clone_shape','zero_clone','complex_clone'])
def test_clone_inputs_need_bound_valid_snapshot_before_comparison(fx,fault):
 f=fx;f.fault=fault;rc=f.invoke()
 assert f.fault_done, 'test injection was not reached'
 assert rc!=0 and f.result['D3_PASS'] is False, 'invalid/unbound clone was counted as evaluated; scope TEST_ONLY dependency injection'

@pytest.mark.parametrize('loc',['second_base_generation','second_base_loader','second_clone_generation','second_clone_loader'])
def test_interruption_preserves_completed_unit_and_failure_identity(fx,loc):
 f=fx
 if loc=='second_base_generation':f.fail_call=2
 elif loc=='second_base_loader':f.fail_load=3
 elif loc=='second_clone_generation':f.fail_call=29
 else:f.fail_load=56
 assert f.invoke()!=0 and f.result['D3_PASS'] is False
 # Either the new canonical partial-evidence file or equivalent legacy files
 # can preserve completed work. Do not require the old filenames.
 p=f.out/'d3_partial_evidence.json';assert p.exists(), 'completed bases absent from partial evidence'
 reg=json.loads(p.read_text());assert reg.get('bases'), 'previous successful base record missing'
 if 'clone' in loc:
  assert any(v.get('evaluation')=='EVALUATED' for v in reg.get('cases',{}).values()), 'previous completed PC1 comparison lost'
 assert reg.get('failed'), 'failure unit identity absent'

def test_required_gate_inventory_is_exact(fx):
 f=fx;assert f.invoke()==0
 assert set(f.result['gates'])==set(f.result['required_inventory'])

@pytest.mark.parametrize('kind',['python','numpy','pot','blas','loader_preflight','phaseC','case_pin','ct_status'])
def test_preflight_fault_rejects_before_generation(fx,kind):
 f=fx
 if kind in ('python','numpy','pot'):f.env[kind]='wrong'
 elif kind=='blas':f.env['blas_threads']=[dict(api='blas',n=8,owner='numpy',lib='openblas')]
 elif kind=='loader_preflight':f.fault=kind
 elif kind=='phaseC':(f.pc/'policy.md').write_text('changed')
 elif kind=='case_pin':f.pins['case_table_sha256']='0'*64;f.repin()
 elif kind=='ct_status':f.git_fault='status'
 assert f.invoke()!=0 and not f.calls and f.result['D3_PASS'] is False

def test_nonempty_output_preserved(fx):
 f=fx;f.out.mkdir();(f.out/'keep.txt').write_text('before');before=file_state(f.out)
 assert f.invoke()==2 and file_state(f.out)==before and not f.calls

def test_selftest_subset_is_not_formal(fx):
 f=fx;assert f.invoke(['--selftest-configs','30104'])==0
 assert f.result['D3_PASS'] is False and f.result['n_bases']==1 and f.result['n_cases']==4

def test_size_split_union_covers_required_anchor_cases(fx):
 f=fx;table=json.loads((PB/'d/d3_pc1_case_table.json').read_text());mp=json.loads((PB/'d/d3_config_map.json').read_text());got=set()
 for size in ('L1.00','L1.20','L1.50'):
  ids=[str(r['config_id']) for r in mp['configurations'] if r['family']=='E7' and r['size_id']==size and r['origin']=='twelve_added']
  assert len(ids)==9
  assert f.invoke(['--sizes',size],out=f.root/size)==0
  got.update(json.loads((f.out/'d3_pc1_results.json').read_text())['cases'])
 expected={c['case_id'] for key in ('new_point_cases','first_wave_anchor_cases') for c in table[key] if c['family']=='E7'}
 writej(EVID/'size_split_coverage.json',dict(required=sorted(expected),got=sorted(got),missing=sorted(expected-got)))
 assert got==expected,'SIZE_FILTER/selftest-configs branch omits required anchor cases in every size run'

def test_empty_selected_set_is_rejected_not_successfully_complete(fx):
 f=fx;rc=f.invoke(['--selftest-configs','99999'])
 assert rc!=0 and f.result['D3_PASS'] is False


def test_transformation_geometry_fault_is_not_hidden_by_initial_gram_gate(fx):
 f=fx;f.fault='wrong_transform_geometry';rc=f.invoke()
 # vec2ang is correct on initial quadrature grid, but wrong on transformed grids.
 # A11 direct-geometry/analytic-reflection checks reject D(M)=I for reflection.
 assert f.result['representation']['gates']['G_quadrature_orthonormal'] is True
 assert rc!=0 and f.result['D3_PASS'] is False, 'only initial YQ orthonormality checked; wrong actual D(M) not tested'

def test_original_a11_representation_battery_and_current_normal_formula(fx):
 f=fx
 nb=json.loads((PB/'registered_assets/a11/MirrorTopology_Step1_A11_x0bridge_v1.4.1.ipynb').read_text())
 from scipy.special import sph_harm_y
 ns=dict(np=np,br=sys.modules['t2b2_bridge'],hp=sys.modules['healpy'],sph_harm_y=sph_harm_y,LMAX=4,hashlib=hashlib,json=json,GATES={},DIAG={})
 exec(compile(''.join(nb['cells'][2]['source']),'A11_frozen_cell2_ISOLATED_TEST_ONLY','exec'),ns)
 assert all(v is True for v in ns['GATES'].values())
 matrices=[];oldprofile=sys.getprofile()
 def observe(frame,event,arg):
  if event=='return' and frame.f_code.co_name=='D_of' and frame.f_globals.get('__name__')==d3.__name__:
   matrices.append((np.array(frame.f_locals['Mm'],copy=True),np.array(arg,copy=True)))
 try:
  sys.setprofile(observe);assert f.invoke()==0
 finally:sys.setprofile(oldprofile)
 assert len(matrices)>0  # now includes the preflight battery and cached runtime D
 diffs=[float(np.max(np.abs(D-ns['D_of'](M)))) for M,D in matrices]
 assert max(diffs)<1e-12
 writej(EVID/'original_representation_comparison.json',dict(scope='isolated frozen A11 cell2; analytic vec2ang substitute; not healpy or physical covariance run',gates=ns['GATES'],diagnostics=ns['DIAG'],case_D_count=len(matrices),max_current_original_D_difference=max(diffs)))
