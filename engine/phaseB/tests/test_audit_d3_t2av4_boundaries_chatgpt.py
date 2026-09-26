"""Independent v4 boundary tests. Actual submitted main runs use prior explicitly
TEST-ONLY CT/loader/Colab/Git/vec2ang doubles. All original source/assets stay unchanged.
Tests with republished documents isolate cross-document semantics; they do not
claim to bypass an unchanged outer run-manifest hash or cryptographic SHA.
"""
from pathlib import Path
import builtins,copy,hashlib,json,os,shutil,sys
import numpy as np,pytest
import test_audit_d3_t2av4_prior31_adapted_chatgpt as h   # adapted module name
from step1_engine import d3_stage as d
PB=h.PB; TABLE=json.loads((PB/'d/d3_pc1_case_table.json').read_text());CM=json.loads((PB/'d/d3_config_map.json').read_text())
import tempfile
E=Path(os.environ.get('D3V4_EVID',os.path.join(tempfile.gettempdir(),'d3_v4_probes')));E.mkdir(parents=True,exist_ok=True)   # adapted
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,obj):(E/(n+'.json')).write_text(json.dumps(obj,indent=1,default=str))
def state(p):return {str(f.relative_to(p)):sha(f) for f in p.rglob('*') if f.is_file()}
@pytest.fixture(scope='module')
def runs(tmp_path_factory):
 root=tmp_path_factory.mktemp('actual_v4_test_only');mp=pytest.MonkeyPatch();g=h.fx.__wrapped__(root,mp);f=next(g);r={}
 try:
  for family in ('E2','E7','E8'):
   f.family=family;r[family]=[]
   for size in ('L1.00','L1.20','L1.50'):
    assert f.invoke(['--sizes',size],out=root/f'{family}_{size}')==0
    r[family].append(f.out)
  f.family='E7';f.fault='generated_finite_nonmatch';assert f.invoke(out=root/'nonmatch')==0;r['fail']=f.out
  r['source']=json.loads((r['E7'][0]/'d3_run_manifest.json').read_text())['source'];r['before']={str(p):state(p) for ps in [r['E2'],r['E7'],r['E8'],[r['fail']]] for p in ps};save('normal_run_counts',{k:[str(p) for p in v] if isinstance(v,list) else str(v) for k,v in r.items() if k!='before'})
  yield r
  assert all(state(Path(p))==s for p,s in r['before'].items())
 finally:
  try:next(g)
  except StopIteration:pass
  mp.undo()
def intake(path,source,arrays=True,mh=None):return d.verify_partition_run(str(path),source,TABLE['table_sha256'],CM['map_sha256'],require_arrays=arrays,expected_run_manifest_sha256=mh or sha(path/'d3_run_manifest.json'))
def agg(parts,source,family='E7'):return d.aggregate_partitions(TABLE,family,parts,source,TABLE['table_sha256'])
def load_docs(p):return {n:json.loads((p/n).read_text()) for n in ['d3_run_manifest.json','d3_cov_registry.json','d3_pc1_results.json','d3_partial_evidence.json','d3_env_lock.json']}
def republish(p,docs):
 rm=docs['d3_run_manifest.json']
 for n,obj in docs.items():
  if n=='d3_run_manifest.json':continue
  b=json.dumps(obj,indent=1,default=str).encode();(p/n).write_bytes(b);h_=hashlib.sha256(b).hexdigest();rm['published_evidence']['documents'][n].update(sha256=h_,bytes=len(b));rm['output_inventory'][n]=dict(sha256=h_,bytes=len(b))
 (p/'d3_run_manifest.json').write_text(json.dumps(rm,indent=1));return sha(p/'d3_run_manifest.json')
def try_run(fn):
 try:return {'rejected':False,'result':fn()}
 except Exception as ex:return {'rejected':True,'exception':repr(ex)}
@pytest.mark.parametrize('fam,nc',[('E2',36),('E7',36),('E8',72)])
def test_normal_formal_partition_coverage(runs,fam,nc):
 ps=[intake(p,runs['source']) for p in runs[fam]];v=agg(ps,runs['source'],fam);assert v['n_bases']==27 and v['n_cases']==nc and v['family_coverage_complete'];save('normal_'+fam,v)
def test_normal_finite_fail_is_carried(runs):
 p=intake(runs['fail'],runs['source']);v=agg([p],runs['source']);assert v['n_pc1_fail']==36 and v['n_pc1_pass']==0 and v['family_coverage_complete'];save('finite_fail_preserved',v)
@pytest.mark.parametrize('kind',['coherent_relabel','gate_false','erase_clone_identity','change_document_hash'])
def test_verified_snapshot_cannot_be_changed_before_consumption(runs,kind):
 p=intake(runs['fail'],runs['source']);before=dict(p.document_sha256)
 def attempt():
  if kind=='coherent_relabel':
   for c in p.pc1_results['cases'].values():c.update(rel=1e-8,match=True)
   for s in p.pc1_results['configuration_status'].values():s.update(status='PC1_PASS',max_rel=1e-8)
   p.run_manifest['pc1_status']=copy.deepcopy(p.pc1_results['configuration_status'])
  elif kind=='gate_false':p.run_manifest['gates']['G_env_lock']=False
  elif kind=='erase_clone_identity':p.pc1_results['cases']['30104:glide_A']['clone_identity']={}
  else:p.document_sha256['d3_pc1_results.json']='0'*64
  return agg([p],runs['source'])
 out=try_run(attempt);save('mutable_'+kind,{'before_document_hash':before,'after_document_hash':p.document_sha256,'outcome':out})
 if not out['rejected']:
  v=out['result'];assert v['n_pc1_fail']==36 and p.document_sha256==before
  assert p.run_manifest['gates']['G_env_lock'] is True and p.pc1_results['cases']['30104:glide_A']['clone_identity']
def test_public_constructor_does_not_mint_verified_without_intake(runs):
 r=load_docs(runs['fail'])
 def attempt():
  p=d.VerifiedPartition(str(runs['fail']),r['d3_run_manifest.json'],r['d3_cov_registry.json'],r['d3_pc1_results.json'],r['d3_partial_evidence.json'],r['d3_env_lock.json'],{})
  return agg([p],runs['source'])
 out=try_run(attempt);save('public_constructor',out);assert out['rejected']
def test_metadata_only_cannot_silently_claim_array_verification(runs,tmp_path):
 p=tmp_path/'metadata';shutil.copytree(runs['fail'],p)
 for f in p.rglob('*.npy'):f.unlink()
 q=intake(p,runs['source'],arrays=False)
 def attempt():return agg([q],runs['source'])
 out=try_run(attempt);save('metadata_only',{'npy_files':len(list(p.rglob('*.npy'))),'outcome':out})
 assert out['rejected'] or out['result'].get('arrays_verified') is False or out['result'].get('verification_scope')=='metadata_only'
def test_missing_arrays_are_rejected_in_default_intake(runs,tmp_path):
 p=tmp_path/'missing';shutil.copytree(runs['fail'],p);next(p.rglob('*.npy')).unlink()
 with pytest.raises(Exception):intake(p,runs['source'])
@pytest.mark.parametrize('kind',['base_path_swap','clone_path_swap','base_array_sha','clone_array_sha','partial_case_values','partial_base_values','invalid_hash_alphabet','partial_failed_nonempty'])
def test_intake_cross_document_and_file_identity(runs,tmp_path,kind):
 p=tmp_path/kind;shutil.copytree(runs['fail'],p);r=load_docs(p);rg=r['d3_cov_registry.json'];pr=r['d3_pc1_results.json'];ev=r['d3_partial_evidence.json'];rm=r['d3_run_manifest.json'];base=rg['configurations']['30104'];c=pr['cases']['30104:glide_A']
 if kind=='base_path_swap':
  assert rm['output_inventory'][base['cov_file']]['sha256']!=rm['output_inventory'][c['clone_cov_file']]['sha256']
  base['cov_file']=c['clone_cov_file'];ev['bases']['30104']=copy.deepcopy(base)
 elif kind=='clone_path_swap':
  assert rm['output_inventory'][base['cov_file']]['sha256']!=c['clone_identity']['file_sha256']
  c['clone_cov_file']=base['cov_file'];ev['cases']['30104:glide_A']=copy.deepcopy(c)
 elif kind=='base_array_sha':
  base['cov_array_sha256']='0'*64;base['bound_load']['array_sha256']='0'*64;base['bound_load']['loader_meta_sha']='0'*64;ev['bases']['30104']=copy.deepcopy(base)
 elif kind=='clone_array_sha':
  c['clone_identity']['array_sha256']='0'*64;c['clone_identity']['loader_meta_sha']='0'*64;ev['cases']['30104:glide_A']=copy.deepcopy(c)
 elif kind=='partial_case_values':ev['cases']['30104:glide_A']['rel']=.777
 elif kind=='partial_base_values':ev['bases']['30104']['cov_file_sha256']='0'*64
 elif kind=='invalid_hash_alphabet':c['D_sha256']='z'*64;ev['cases']['30104:glide_A']=copy.deepcopy(c)
 else:ev['failed']=[dict(unit='case',case_id='30104:glide_A',error='TEST_ONLY')]
 mh=republish(p,r)
 out=try_run(lambda:agg([intake(p,runs['source'],mh=mh)],runs['source']));save('cross_'+kind,{'outcome':out,'test_outer_sha':mh,'note':'Expected digest is for this isolated diagnostic packet; not a bypass of the original outer hash.'})
 assert out['rejected'],kind+' survives file and semantic intake'
def test_same_document_bytes_used_for_all_checks(runs,monkeypatch):
 p=runs['E7'][0];orig=builtins.open;counts={};names={'d3_cov_registry.json','d3_pc1_results.json','d3_partial_evidence.json','d3_env_lock.json'}
 def op(file,mode='r',*a,**kw):
  try:path=Path(file)
  except TypeError:return orig(file,mode,*a,**kw)
  if path.parent==p and path.name in names and mode in ('r','rb'):
   counts[path.name]=counts.get(path.name,0)+1
   if counts[path.name]>1:raise OSError('TEST_ONLY: no second path read after metadata snapshot')
  return orig(file,mode,*a,**kw)
 monkeypatch.setattr(builtins,'open',op);out=try_run(lambda:intake(p,runs['source']));save('single_document_snapshot',{'counts':counts,'rejected':out['rejected'],'exception':out.get('exception')});assert out['rejected'] or all(n==1 for n in counts.values())  # refusing a changed/unavailable path is also safe
def test_intake_after_file_corruption_refuses(runs,tmp_path):
 p=tmp_path/'changed';shutil.copytree(runs['fail'],p);q=next(p.rglob('*.npy'));q.write_bytes(q.read_bytes()+b'TEST')
 with pytest.raises(Exception):intake(p,runs['source'])
def test_explicit_outer_manifest_hash_rejects_coherent_republication(runs,tmp_path):
 p=tmp_path/'repub';shutil.copytree(runs['fail'],p);old=sha(p/'d3_run_manifest.json');r=load_docs(p);r['d3_run_manifest.json']['note']='TEST_ONLY';republish(p,r)
 with pytest.raises(Exception):intake(p,runs['source'],mh=old)
def test_aggregate_output_edit_does_not_mutate_partitions(runs):
 p=intake(runs['fail'],runs['source']);before=copy.deepcopy(p.pc1_results);v=agg([p],runs['source']);v['configuration_status']['30104']['status']='X';assert p.pc1_results==before


def test_publication_and_inventory_cannot_authenticate_different_snapshots(runs,tmp_path,monkeypatch):
 p=tmp_path/'split_snapshot';shutil.copytree(runs['fail'],p)
 path=p/'d3_pc1_results.json';original=path.read_bytes();altered=json.loads(original);altered['audit_test_note']='DIFFERENT_SNAPSHOT'
 other=json.dumps(altered,indent=1).encode();rm=json.loads((p/'d3_run_manifest.json').read_text())
 rm['output_inventory']['d3_pc1_results.json']=dict(sha256=hashlib.sha256(other).hexdigest(),bytes=len(other))
 (p/'d3_run_manifest.json').write_text(json.dumps(rm,indent=1));mh=sha(p/'d3_run_manifest.json')
 real=builtins.open;hit=[]
 class Switch:
  def __init__(self,fh):self.fh=fh
  def __getattr__(self,k):return getattr(self.fh,k)
  def __enter__(self):return self
  def __exit__(self,*a):return self.fh.__exit__(*a)
  def read(self,*a):
   b=self.fh.read(*a)
   if not hit:path.write_bytes(other);hit.append(True)
   return b
 def op(file,mode='r',*a,**kw):
  fh=real(file,mode,*a,**kw)
  try:pp=Path(file)
  except TypeError:return fh
  return Switch(fh) if pp==path and mode=='rb' and not hit else fh
 monkeypatch.setattr(builtins,'open',op)
 result=try_run(lambda:agg([intake(p,runs['source'],mh=mh)],runs['source']))
 save('split_pub_inventory_snapshot',{'rejected':result['rejected'],'exception':result.get('exception'),'publication_sha':hashlib.sha256(original).hexdigest(),'inventory_sha':hashlib.sha256(other).hexdigest(),'switch_count':len(hit),'note':'Isolated diagnostic manifest has inconsistent publication/inventory; its new expected hash is explicit, not an unchanged outer-ledger bypass.'})
 assert result['rejected'], 'same document accepted against two inconsistent byte identities'
