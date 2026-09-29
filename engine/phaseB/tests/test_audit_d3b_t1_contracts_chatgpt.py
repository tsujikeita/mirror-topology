# Path adaptation only (Claude, 2026-09-30): ChatGPT audit original `test_d3b_new_contracts.py` bundled verbatim except the fixture import (`fixture` -> `d3b_t1_audit_fixture_chatgpt`, the bundled copy of the audit `fixture.py`). Default root = this phaseB (AUDIT_PHASEB_ROOT overrides).
"""New audit tests. Rejection assertions intentionally fail for missing contracts.
Small TEST kernel/explicit external doubles only. Source and original data unmodified.
"""
import copy,io,json,hashlib,os,sys,shutil,types,contextlib,zipfile
from pathlib import Path
import numpy as np,pytest
from d3b_t1_audit_fixture_chatgpt import P,H,CTX,b3,b2,dp,install,tree,jload,dump
from step1_engine.errors import InputContractError

@pytest.mark.parametrize('fam,cid,old',[('E2',20104,20101),('E7',30104,30101),('E8',40104,40101)])
def test_same_d2_path_both_batches_fitting_and_chunk(tmp_path,fam,cid,old):
 k=H._Kern();inv=b2.CallInventory();roots,dd,df=H._gen_cfg(tmp_path,cid,k,inv)
 for b in (0,1):
  dest=tmp_path/f'd2_b{b}';m=b2.generate_configuration_bank(k,H.R,H.T,H.D2SPEC,old,roots,b,str(dest),inv,('float64',),scale=H.SCALE,chunk_clusters=3)
  n=b3.verify_twelve_bank_dir(dd[b],CTX)
  for x,y in zip(n['shards'],m['shards']):
   with np.load(Path(dd[b])/x['file']) as a,np.load(dest/y['file']) as z:
    assert set(a.files)==set(z.files) and all(np.array_equal(a[v],z[v]) for v in a.files)
 f=tmp_path/'d2_fit';fm=b2.generate_fitting_bank(k,H.R,H.T,H.D2SPEC,old,roots,str(f),inv,scale=H.SCALE,chunk_clusters=3)
 with np.load(Path(df)/f'cfg{cid}_fit_s0.npz') as a,np.load(f/fm['shards'][0]['file']) as z:assert all(np.array_equal(a[v],z[v]) for v in a.files)

@pytest.mark.parametrize('fam,cid',[('E2',20104),('E7',30104),('E8',40104)])
def test_script_normal_one_size_and_all_reuse(tmp_path,monkeypatch,fam,cid):
 script,run=install(monkeypatch,tmp_path);out=tmp_path/'normal'
 rc,m=run(out,family=fam,configs=None)
 assert rc==1 and m['stage']=='complete' and m['D3B_PASS'] is False and len(m['directories'])==27
 reg=jload(out/'d3_bank_registry.json');assert len(reg['calls'])==27 and len(reg['required_requests'])==27 and len(list(out.rglob('*.npz')))==45
 before=tree(out); rc,n=run(tmp_path/'reuse','--reuse-root',str(out),family=fam,configs=None)
 r=jload(tmp_path/'reuse/d3_bank_registry.json')
 assert n['stage']=='complete' and len(r['calls'])==0 and len(r['calls_reused'])==27 and all(v['reused'] for v in n['directories'].values()) and tree(out)==before
 assert len(list((tmp_path/'reuse/audit_dependencies').rglob('*.json')))==72

@pytest.mark.parametrize('field',['family','root_sha','complete_set','producer'])
def test_saved_registry_whole_content_must_match_computation(tmp_path,monkeypatch,field):
 script,run=install(monkeypatch,tmp_path);real=json.dump;seen=[]
 def faulty(obj,fh,*a,**kw):
  if str(getattr(fh,'name','')).endswith(('d3_bank_registry.json','d3_bank_registry.json.tmp')) and obj.get('status')!='PARTIAL_AFTER_FAILURE':
   obj=copy.deepcopy(obj)
   if field=='family':obj['family']='E8'
   elif field=='root_sha':obj['covariance_intake']['20104']['root_sha256']['model_matched']='0'*64
   elif field=='complete_set':obj['directories']={}
   else:obj['environment']['producer']['script_sha256']='0'*64
   seen.append(True)
  return real(obj,fh,*a,**kw)
 monkeypatch.setattr(json,'dump',faulty);rc,m=run(tmp_path/'o')
 assert seen
 assert m['gates']['G_registry_saved'] is not True and m['stage']!='complete', 'registry write corruption was not detected'

@pytest.mark.parametrize('when',['second_unit','fitting'])
def test_partial_units_are_kept_and_resume(tmp_path,monkeypatch,when):
 script,run=install(monkeypatch,tmp_path);fn=b3.generate_twelve_configuration_bank;fit=b3.generate_twelve_fitting_bank
 if when=='second_unit':
  def bad(*a,**kw):
   if a[5]==1:raise OSError('AUDIT injected second-unit generator error')
   return fn(*a,**kw)
  monkeypatch.setattr(b3,'generate_twelve_configuration_bank',bad);want=1
 else:
  monkeypatch.setattr(b3,'generate_twelve_fitting_bank',lambda *a,**kw:(_ for _ in ()).throw(OSError('AUDIT injected fitting error')));want=2
 out=tmp_path/'partial';rc,m=run(out);assert rc==1 and m['stage']=='exception' and len(m['directories'])==want
 assert len(jload(out/'d3_bank_registry.json')['directories'])==want
 monkeypatch.setattr(b3,'generate_twelve_configuration_bank',fn);monkeypatch.setattr(b3,'generate_twelve_fitting_bank',fit)
 before=tree(out);rc,n=run(tmp_path/'resume','--reuse-root',str(out));r=jload(tmp_path/'resume/d3_bank_registry.json')
 assert n['stage']=='complete' and sum(x['reused'] for x in n['directories'].values())==want and len(r['calls'])==3-want and tree(out)==before

@pytest.mark.parametrize('what',['npz','request','producer'])
def test_reuse_rejects_changed_bytes_or_valid_other_request(tmp_path,monkeypatch,what):
 script,run=install(monkeypatch,tmp_path);out=tmp_path/'normal';run(out);bad=tmp_path/'bad';shutil.copytree(out,bad)
 unit=bad/'cfg20104_b0'
 if what=='request':shutil.rmtree(unit);shutil.copytree(bad/'cfg20104_fit',unit)
 elif what=='npz':
  f=unit/'cfg20104_b0_s0.npz';f.write_bytes(f.read_bytes()+b'BAD')
 else:
  m=jload(unit/'COMPLETE.json');sh=m['shards'][0];s=jload(unit/sh['sidecar']);s['environment']['producer']['script_sha256']='0'*64;dump(unit/sh['sidecar'],s);sh['sidecar_sha256']=hashlib.sha256((unit/sh['sidecar']).read_bytes()).hexdigest();m['manifest_sha256']=b2._sha(json.dumps({k:v for k,v in m.items() if k!='manifest_sha256'},sort_keys=True).encode());dump(unit/'COMPLETE.json',m)
  b3.verify_twelve_bank_dir(str(unit),CTX) # identity verifier passes; wrapper request/producer must reject
 rc,m=run(tmp_path/'rejected','--reuse-root',str(bad));assert rc==1 and m['stage']=='exception' and m['directories']=={}

@pytest.mark.parametrize('what',['complete','sidecar'])
def test_reuse_metadata_changes_after_validation_keep_snapshot(tmp_path,monkeypatch,what):
 script,run=install(monkeypatch,tmp_path);out=tmp_path/'o';run(out);real=b3.verify_twelve_bank_dir;stored={};called=[]
 def hook(path,*a,**kw):
  m=real(path,*a,**kw)
  if Path(path).is_relative_to(out):
   f=Path(path)/('COMPLETE.json' if what=='complete' else m['shards'][0]['sidecar']);stored[str(f.relative_to(out))]=f.read_bytes();f.write_bytes(b'BROKEN_AFTER_VERIFY');called.append(str(f))
  return m
 monkeypatch.setattr(b3,'verify_twelve_bank_dir',hook)
 rc,m=run(tmp_path/'reuse','--reuse-root',str(out));assert m['stage']=='complete' and len(called)==3
 for rel,b in stored.items():assert (tmp_path/'reuse/audit_dependencies'/rel).read_bytes()==b

@pytest.mark.parametrize('kind',['missing','invalid','list','null'])
def test_launcher_nonzero_without_valid_record_still_emits_final_zip(tmp_path,monkeypatch,kind):
 out=tmp_path/'out';do=out/'d3b';do.mkdir(parents=True)
 if kind!='missing':(do/'d3_run_manifest.json').write_text({'invalid':'{', 'list':'[]','null':'null'}[kind])
 sp=types.SimpleNamespace(run=lambda *a,**kw:types.SimpleNamespace(returncode=-9,stdout='TEST killed',stderr='TEST stderr'))
 nb=jload(P/'d/MirrorTopology_Step1_D3b_bankgen_v0.1.ipynb')
 ns=dict(sys=sys,subprocess=sp,json=json,OUT=str(out),SCRIPT='TEST_ONLY',MT='TEST_ONLY',PHASEB=str(P),PHASEC='TEST_ONLY',FAMILY='E2',SZ=['L1.00'],REUSE_ROOT='',D2_REF_ROOT='')
 with contextlib.redirect_stdout(io.StringIO()):exec(''.join(nb['cells'][4]['source']),ns)
 assert ns['script_ok'] is False and (out/'launcher_script_stdout.txt').exists()
 # Execute the final cell as well; only redirect ZIP path and download UI.
 actual=tmp_path/'audit.zip';real=zipfile.ZipFile;zmod=types.ModuleType('zipfile');zmod.ZIP_DEFLATED=zipfile.ZIP_DEFLATED;zmod.ZipFile=lambda p,*a,**kw:real(actual,*a,**kw);monkeypatch.setitem(sys.modules,'zipfile',zmod)
 c=types.ModuleType('google.colab');c.files=types.SimpleNamespace(download=lambda p:None);monkeypatch.setitem(sys.modules,'google.colab',c)
 path=types.SimpleNamespace(join=os.path.join,relpath=os.path.relpath,getsize=lambda p:actual.stat().st_size if str(p).startswith('/content/d3b_') else os.path.getsize(p))
 ns.update(os=types.SimpleNamespace(path=path,walk=os.walk),sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest(),RUN=str(out.parent),REPO_COMMIT='a'*40,lock={'sizes':['L1.00']})
 with contextlib.redirect_stdout(io.StringIO()):exec(''.join(nb['cells'][5]['source']),ns)
 assert jload(out/'d3b_final_record.json')['D3B_PASS'] is False and 'd3b_final_record.json' in real(actual).namelist()

@pytest.mark.parametrize('where',['npz','sidecar','complete'])
def test_writer_failure_never_publishes_complete(tmp_path,monkeypatch,where):
 real=b3._atomic_write
 def fail(path,data):
  if (where=='npz' and str(path).endswith('.npz')) or (where=='sidecar' and str(path).endswith('.sidecar.json')) or (where=='complete' and str(path).endswith('COMPLETE.json')):raise OSError('AUDIT write failure')
  return real(path,data)
 monkeypatch.setattr(b3,'_atomic_write',fail);out=tmp_path/'o'
 with pytest.raises(OSError):b3.generate_twelve_configuration_bank(H._Kern(),H.R,CTX,20104,H._roots(20104),0,str(out),b2.CallInventory(),scale=H.SCALE)
 assert not (out/'COMPLETE.json').exists()

# Read-side manifest hashes stay connected to the exact NPZ bytes used by _load_role.
@pytest.mark.parametrize('target',['model','reference','fitting'])
def test_intake_rejects_npz_changed_between_verify_and_consumption(tmp_path,monkeypatch,target):
 k=H._Kern();inv=b2.CallInventory();roots,dd,df=H._gen_cfg(tmp_path,20104,k,inv);rd,rf=H._gen_ref(tmp_path,'E2',k,inv)
 fn=b3._load_role;once=[]
 def hook(d,m,r,*a,**kw):
  selected=(target=='model' and d==dd[0]) or (target=='reference' and d==rd[0]) or (target=='fitting' and d==df)
  if selected and not once:
   p=Path(d)/m['shards'][0]['file'];p.write_bytes(p.read_bytes()+b'CHANGED_AFTER_VERIFY');once.append(1)
  return fn(d,m,r,*a,**kw)
 monkeypatch.setattr(b3,'_load_role',hook)
 with pytest.raises(InputContractError):b3.intake_twelve_bank(20104,'matched',dd,rd,df,rf,dict(roots,ref_matched=H.S_ISO),CTX,formal=False)
 assert once

@pytest.mark.parametrize('fam,base',[('E2',20100),('E7',30100),('E8',40100)])
def test_all_twelve_real_small_intakes_old3_new9_no_synthetic_supplies(tmp_path,fam,base):
 """All supplies from actual small TEST banks. This exercises structural old/new
 connection, NOT the old production ledger's NPZ arrays (not supplied here)."""
 k=H._Kern();inv=b2.CallInventory();rd,rf=H._gen_ref(tmp_path,fam,k,inv);sup={'matched':[],'native':[]}
 d1=json.loads((P/'registered_assets/d1/d1_cov_registry.json').read_text()) if (P/'registered_assets/d1/d1_cov_registry.json').exists() else b2.canonical_context()['d1_registry']
 for j in range(1,13):
  cid=base+j;roots=H._roots(cid)
  if j<=3:
   dd={b:str(tmp_path/f'cfg{cid}_b{b}') for b in (0,1)};df=str(tmp_path/f'cfg{cid}_fit')
   for b in (0,1):b2.generate_configuration_bank(k,H.R,H.T,H.D2SPEC,cid,roots,b,dd[b],inv,('float64',),scale=H.SCALE)
   b2.generate_fitting_bank(k,H.R,H.T,H.D2SPEC,cid,roots,df,inv,scale=H.SCALE)
   covpath=P/'registered_assets/d1'/d1['configurations'][str(cid)]['cov_file'];cm=jload(str(covpath)+'.manifest.json')
   for system in sup:s,info=b2.intake_registered_bank(cid,system,dd,rd,df,rf,dict(roots,ref_matched=H.S_ISO),cm,H.T,formal=False);sup[system].append(s)
  else:
   roots,dd,df=H._gen_cfg(tmp_path,cid,k,inv)
   for system in sup:s,info=b3.intake_twelve_bank(cid,system,dd,rd,df,rf,dict(roots,ref_matched=H.S_ISO),CTX,formal=False);sup[system].append(s)
 u=sup['matched'][0].cluster_uids;p,f,i=dp.fix_family_plans(H.T,fam,{0:u[:20],1:u[20:]},4,H.T['master_seed'],B=20,B_KDE=25)
 fm=dp.build_twelve_size_input(CTX,fam,'L1.00','matched',sup['matched'],p,f);fn=dp.build_twelve_size_input(CTX,fam,'L1.00','native',sup['native'],p,f)
 assert len(fm.configs)==len(fn.configs)==12 and all(c.cluster_uids==u for c in fm.configs+fn.configs)
 assert all(c.weight==1/12 for c in fm.configs+fn.configs)
 fm.validate();fn.validate()
 # The family reference is deliberately NOT a production ledger unit.
 with pytest.raises(InputContractError):b3.verify_reused_reference_dir(rd[0],CTX,fam,f'ref_{fam}_b0')

@pytest.mark.parametrize('family,sizes,cid',[('E2','L1.00','20101'),('E2','L1.20','20104'),('E2','L1.00','30104'),('E1','L1.00','10101'),('E2','L2.00','20104'),('E2','L1.00,L1.00','20104')])
def test_scope_errors_stop_before_bank_generation(tmp_path,monkeypatch,family,sizes,cid):
 script,run=install(monkeypatch,tmp_path);rc,m=run(tmp_path/'bad',family=family,sizes=sizes,configs=cid)
 assert rc==1 and m['stage']=='scope' and not m['directories'] and not list((tmp_path/'bad').rglob('*.npz'))

def test_optional_d2_reference_rejects_non_ledger_bank(tmp_path,monkeypatch):
 script,run=install(monkeypatch,tmp_path);refroot=tmp_path/'refs';refroot.mkdir();H._gen_ref(refroot,'E2',H._Kern(),b2.CallInventory())
 before=tree(refroot);rc,m=run(tmp_path/'out','--d2-ref-root',str(refroot))
 assert rc==1 and m['stage']=='d2_reference' and m['gates']['G_d2_reference_dirs'] is False and not m['directories'] and tree(refroot)==before
