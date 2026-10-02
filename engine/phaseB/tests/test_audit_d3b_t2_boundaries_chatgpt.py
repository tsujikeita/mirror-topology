# Path adaptation only (Claude, 2026-10-02): ChatGPT audit original `test_d3bt2_boundaries.py` (D-3b tranche 2 audit; 40 controls) bundled verbatim except the root default (AUDIT_PHASEB_ROOT, else this phaseB).
"""Independent D3b tranche2 audit. Inputs copied; no Drive, no production NPZ.
Generation fixture uses submitted TEST-ONLY kernel/external adapter. The verifier
is unmodified. Reference race tests replace ONLY the fixed-production-reference
identity gate with the real D2 validator on a small synthetic reference; this is
not an execution of the absent accepted D2 NPZs. Other accepted-mode probes use
real registered metadata without substituting the missing production arrays.
"""
import os,sys,copy,json,io,contextlib,hashlib,importlib.util,shutil,builtins
from pathlib import Path
import numpy as np,pytest
P=Path(os.environ.get('AUDIT_PHASEB_ROOT',str(Path(__file__).resolve().parent.parent))).resolve();sys.path[:0]=[str(P),str(P/'tests')]
from d3b_t1_audit_fixture_chatgpt import install,H,b2,b3,tree
from step1_engine import d3b_ledger as dl
from step1_engine.d3_profile import twelve_context
from step1_engine.errors import InputContractError

def load():
 s=importlib.util.spec_from_file_location('audited_d3b_verifier',P/'d/d3b_verify_banks.py');v=importlib.util.module_from_spec(s);s.loader.exec_module(v);return v

def invoke(root,out,*extra):
 v=load(); old=sys.argv[:];sys.argv=['verify','--phaseb',str(P),'--run-root',str(root),'--out',str(out),*extra];st=io.StringIO()
 try:
  with contextlib.redirect_stdout(st),contextlib.redirect_stderr(st):rc=v.main()
 finally:sys.argv=old
 files=list(Path(out).glob('d3b_verify_*.json')) if Path(out).is_dir() else []
 r=json.loads(files[0].read_bytes()) if files else None
 return rc,r,st.getvalue()

@pytest.fixture(scope='module')
def small(tmp_path_factory):
 base=tmp_path_factory.mktemp('synthetic_runs');data={}
 for fam in ('E2','E7','E8'):
  w=base/fam;w.mkdir();runroot=w/'run';mp=pytest.MonkeyPatch()
  try:
   _,run=install(mp,w);rc,rm=run(runroot/'d3b',family=fam,configs=None)
   assert rc==1 and rm['stage']=='complete' and rm['D3B_PASS'] is False
  finally:mp.undo()
  refs=w/'refs';refs.mkdir();H._gen_ref(refs,fam,H._Kern(),b2.CallInventory())
  data[fam]=(runroot,refs)
 return data

def clone_run(src,dst):
 shutil.copytree(src,dst);p=dst/'d3b/d3_bank_registry.json';r=json.loads(p.read_bytes())
 for d in r['directories'].values():d['path']=str(dst/'d3b'/Path(d['path']).name)
 p.write_text(json.dumps(r,indent=1));return dst

def registered(fam='E2',size='L1.00'):
 return next((P/'registered_assets/d3b/runs').glob(f'{fam}_{size}_*/out'))

@pytest.mark.parametrize('fam',['E2','E7','E8'])
def test_small_full_readonly_and_statistics(tmp_path,small,fam):
 root,_=small[fam];before=tree(root);rc,r,_=invoke(root,tmp_path/'v','--mode','test')
 assert rc==0 and r['all_ok'] is True and r['coverage_complete'] is True and r['accepted_run_binding'] is False
 assert len(r['units'])==27 and sum(len(u['shards']) for u in r['units'].values())==45
 assert r['cid_correspondence_ok'] is True and all(u['ok'] and u['arrays_verified_against_sidecar'] for u in r['units'].values())
 assert all(a['T1']['n']==a['T1']['finite'] and a['T2']['n']==a['T2']['finite'] for u in r['units'].values() for a in u['arrays'].values())
 assert tree(root)==before

@pytest.mark.parametrize('n',[1,27,99])
def test_partial_never_full_success(tmp_path,small,n):
 rc,r,_=invoke(small['E2'][0],tmp_path/'v','--mode','test','--max-dirs',str(n))
 assert rc!=0 and r['coverage_complete'] is False and r['verification_scope'].endswith('_partial')

@pytest.mark.parametrize('fam',['E2','E7','E8'])
@pytest.mark.parametrize('size',['L1.00','L1.20','L1.50'])
def test_real_accepted_metadata_binds_but_missing_npz_fails(tmp_path,fam,size):
 root=registered(fam,size);before=tree(root);rc,r,_=invoke(root,tmp_path/'v')
 assert rc==1 and r['accepted_run_binding'] is True and r['coverage_complete'] is True
 assert r['all_ok'] is False and len(r['units'])==27 and not any(u['ok'] for u in r['units'].values())
 assert tree(root)==before

@pytest.mark.parametrize('doc',['registry','run','final','lock'])
def test_changed_actual_accepted_records_stop_before_bank_read(tmp_path,doc,monkeypatch):
 r=tmp_path/'r';shutil.copytree(registered(),r)
 paths={'registry':'d3b/d3_bank_registry.json','run':'d3b/d3_run_manifest.json','final':'d3b_final_record.json','lock':'launcher_lock.json'}
 f=r/paths[doc];f.write_bytes(f.read_bytes()+b'\n')
 calls=[];real=b3.verify_twelve_bank_dir
 def check(*a,**kw):calls.append(a[0]);return real(*a,**kw)
 monkeypatch.setattr(b3,'verify_twelve_bank_dir',check)
 rc,o,_=invoke(r,tmp_path/'v');assert rc==1 and o['stage']=='binding' and not calls

@pytest.mark.parametrize('kind',['bytes','array','missing','sidecar'])
def test_corrupt_small_bank_rejected(tmp_path,small,kind):
 r=clone_run(small['E2'][0],tmp_path/'r');f=r/'d3b/cfg20104_b0/cfg20104_b0_s0.npz'
 if kind=='bytes':f.write_bytes(f.read_bytes()+b'AUDIT_CHANGED')
 elif kind=='missing':f.unlink()
 elif kind=='sidecar':p=Path(str(f)+'.sidecar.json');p.write_bytes(p.read_bytes()+b'\n')
 else:
  with np.load(f,allow_pickle=False) as z:data={k:z[k] for k in z.files}
  data['model_native__float64__T1'][0]+=1;np.savez(f,**data)
 rc,o,_=invoke(r,tmp_path/'v','--mode','test');assert rc==1 and o['all_ok'] is False and o['units']['cfg20104_b0']['ok'] is False

@pytest.mark.parametrize('kind',['same','child','parent'])
def test_run_output_overlap_refused(tmp_path,kind):
 root=tmp_path/'parent/run';shutil.copytree(registered(),root);before=tree(root.parent)
 out={'same':root,'child':root/'new_output','parent':root.parent}[kind]
 rc,r,_=invoke(root,out);assert rc!=0 and tree(root.parent)==before

@pytest.mark.parametrize('kind',['root','root_child','unit_child','symlink_unit'])
def test_d2_input_output_isolation_even_on_error(tmp_path,kind):
 """Real accepted D3b metadata, no D2 validation replacement or NPZ substitution."""
 refs=tmp_path/'references';refs.mkdir();(refs/'keep.txt').write_text('unmodified')
 external=tmp_path/'external_ref';external.mkdir();(external/'keep.txt').write_text('unmodified')
 if kind=='symlink_unit':(refs/'ref_E2_b0').symlink_to(external,target_is_directory=True);out=external/'review'
 elif kind=='unit_child':(refs/'ref_E2_b0').mkdir();out=refs/'ref_E2_b0/review'
 elif kind=='root_child':out=refs/'review'
 else:
  (refs/'keep.txt').unlink();out=refs
 before=(tree(refs),tree(external));rc,r,_=invoke(registered(),out,'--d2-ref-root',str(refs))
 assert rc!=0 and (tree(refs),tree(external))==before,'read-only verifier wrote a report into the declared D2 input'

@pytest.mark.parametrize('automatic',[False,True])
def test_relocated_symlink_bank_output_isolation(tmp_path,automatic):
 root=tmp_path/'run';shutil.copytree(registered(),root);external=tmp_path/'external_bank';bank=root/'d3b/cfg20104_b0';shutil.move(str(bank),external);bank.symlink_to(external,target_is_directory=True)
 before=tree(external);extra=[]
 if not automatic:
  lock=json.loads((root/'launcher_lock.json').read_bytes());extra=['--path-map',lock['run_dir']+'/out='+str(root)]
 rc,r,_=invoke(root,external/'review','--max-dirs','1',*extra)
 assert rc!=0 and tree(external)==before,'mapped input bank was changed by output publication'

@pytest.mark.parametrize('fam',['E2','E7','E8'])
def test_small_reference_connection_explicit_fixed_identity_double(tmp_path,small,monkeypatch,fam):
 """Full D2 file/member validator on synthetic input, not production ledger acceptance."""
 monkeypatch.setattr(b3,'verify_reused_reference_dir',lambda p,ctx,fam,unit:b2.verify_bank_dir(p,('ref_matched',)))
 root,refs=small[fam];before=tree(refs);rc,r,_=invoke(root,tmp_path/'v','--mode','test','--d2-ref-root',str(refs))
 assert rc==0 and r['d2_reference']['verified'] and r['cid_correspondence_ok'] and tree(refs)==before

@pytest.mark.parametrize('unit',['b0','b1','fit'])
def test_reference_reread_uses_verified_bytes(tmp_path,small,monkeypatch,unit):
 """After real D2 validation, replace only T1 (cid unchanged). No fixed SHA forged.
 Sole TEST DOUBLE: production-ledger identity gate is replaced by real validation
 of a small D2 bank, because production D2 NPZ files are not attached.
 """
 refs=tmp_path/'refs';shutil.copytree(small['E2'][1],refs);seen=[]
 def validate_then_change(p,ctx,fam,name):
  m=b2.verify_bank_dir(p,('ref_matched',))
  if name==f'ref_E2_{unit}':
   f=Path(p)/m['shards'][0]['file']
   with np.load(f,allow_pickle=False) as z:data={k:z[k] for k in z.files}
   data['ref_matched__float64__T1'][0]+=1000.;np.savez(f,**data);seen.append(True)
  return m
 monkeypatch.setattr(b3,'verify_reused_reference_dir',validate_then_change)
 rc,r,_=invoke(small['E2'][0],tmp_path/'v','--mode','test','--d2-ref-root',str(refs))
 assert seen and rc!=0 and r['d2_reference']['verified'] is False,'changed reference was reported verified after a second unbound NPZ read'

def test_nonledger_reference_is_rejected_without_doubles(tmp_path,small):
 rc,r,_=invoke(small['E2'][0],tmp_path/'v','--mode','test','--d2-ref-root',str(small['E2'][1]))
 assert rc==1 and r['stage']=='d2_reference' and r['d2_reference']['verified'] is False and 'units' not in r

def test_sealed_units_and_view_isolation():
 c=twelve_context(str(P));u=dl.intake_registered_d3b_units(str(P),c);d=u.partitions;d['E2_L1.00']['units'].clear();assert len(u.partitions['E2_L1.00']['units'])==27
 v=u.unit('cfg20104_b0');v['npz'].clear();assert len(u.unit('cfg20104_b0')['npz'])==1
 with pytest.raises(InputContractError):dl.D3bUnits({})
 with pytest.raises(AttributeError):u.verified=False
