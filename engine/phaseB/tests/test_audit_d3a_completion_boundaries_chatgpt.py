# -*- coding: utf-8 -*-
# ChatGPT audit contracts for D-3a completion 0.87.0 (R-D3AC-A/B), bundled with path adaptation only (see line marked). Original: tests/test_completion_boundaries.py of the audit evidence bundle.
"""Contract checks on real registered D3a records; copies only, no generation.
Set D3_AUDIT_ROOT to the unmodified or reference-patched phaseB source tree.
"""
from pathlib import Path
import os,sys,json,hashlib,shutil,copy,builtins
import numpy as np
import pytest
ROOT=Path(os.environ.get('D3_AUDIT_ROOT',str(Path(__file__).resolve().parent.parent))).resolve()   # path adaptation only (Claude): default = this phaseB tree; D3_AUDIT_ROOT still honoured
sys.path.insert(0,str(ROOT))
from step1_engine import d3_assets as da
from step1_engine.errors import InputContractError
LP=Path('registered_assets/d3/d3a_generation_ledger.json')
SHA=hashlib.sha256((ROOT/LP).read_bytes()).hexdigest()

def j(p):return json.loads(Path(p).read_bytes())
def write(p,d):Path(p).write_text(json.dumps(d,indent=1)+'\n')
@pytest.fixture
def scratch(tmp_path):
    r=tmp_path/'phaseB';(r/'registered_assets').mkdir(parents=True)
    shutil.copytree(ROOT/'d',r/'d')
    for k in ('d1','d3'):shutil.copytree(ROOT/'registered_assets'/k,r/'registered_assets'/k)
    return r

def intake(r):return da.intake_registered_d3a_assets(str(r),expected_ledger_sha256=SHA)
def incomplete_e8(r):
    L=j(r/LP);key=next(k for k,v in L['incomplete_attempts'].items() if v['family']=='E8');rec=L['incomplete_attempts'][key]
    return key,rec,r/rec['registered_dir']

def test_normal_scope_and_identity(scratch):
    a=intake(scratch)
    assert a.verified and a.ledger_sha256==SHA and len(a.formal_runs)==9 and len(a.base_covariances)==81 and a.n_pc1_fail==0
    assert {k:v['n_cases'] for k,v in a.coverage.items()}=={'E2':36,'E7':36,'E8':72}
    assert sum(x['partial_bases_reproduced']+x['partial_cases_reproduced'] for x in a.reproduction_crosscheck.values())==39
    assert sum(x['partial_cases_reproduced'] for x in a.reproduction_crosscheck.values())==21

@pytest.mark.parametrize('which',['clone_file_sha','partial_status','partial_family','final_commit','final_stage','partial_whitespace'])
def test_incomplete_documents_bound_to_unchanged_ledger(scratch,which):
    _,rec,d=incomplete_e8(scratch)
    p=d/('d3_final_record.json' if which.startswith('final') else 'd3/d3_partial_evidence.json');obj=j(p)
    if which=='clone_file_sha':next(iter(obj['cases'].values()))['clone_identity']['file_sha256']='0'*64
    elif which=='partial_status':obj['status']='COMPLETE'
    elif which=='partial_family':obj['family']='E2'
    elif which=='final_commit':obj['launcher']['commit']='a'*40
    elif which=='final_stage':obj['stages']['stage']='complete'
    if which=='partial_whitespace':p.write_bytes(p.read_bytes()+b'\n')
    else:write(p,obj)
    # Neither ledger nor its expected outer SHA is changed.
    assert hashlib.sha256((scratch/LP).read_bytes()).hexdigest()==SHA
    with pytest.raises((InputContractError,ValueError,OSError)):intake(scratch)

@pytest.mark.parametrize('which',['base_array','case_rel'])
def test_existing_incomplete_numerical_mismatch_rejected(scratch,which):
    _,_,d=incomplete_e8(scratch);p=d/'d3/d3_partial_evidence.json';obj=j(p)
    if which=='base_array':next(iter(obj['bases'].values()))['cov_array_sha256']='0'*64
    else:next(iter(obj['cases'].values()))['rel']=0.5
    write(p,obj)
    with pytest.raises((InputContractError,ValueError,OSError)):intake(scratch)

@pytest.mark.parametrize('which',['npy_changed','npy_missing','bad_ledger_sha'])
def test_formal_integrity_still_rejects(scratch,which):
    if which=='bad_ledger_sha':
        with pytest.raises(InputContractError):da.intake_registered_d3a_assets(str(scratch),'0'*64)
        return
    L=j(scratch/LP);p=next((scratch/next(iter(L['formal_runs'].values()))['registered_dir']/'cov_cache').glob('*.npy'))
    if which=='npy_missing':p.unlink()
    else:b=bytearray(p.read_bytes());b[-1]^=1;p.write_bytes(b)
    with pytest.raises((InputContractError,ValueError,OSError)):intake(scratch)

@pytest.mark.parametrize('bad',[True,20104.0,'20104',20101,99999])
def test_require_pass_strict_ids(scratch,bad):
    a=intake(scratch)
    with pytest.raises(InputContractError):a.require_pc1_pass(bad)

def test_views_are_detached_and_constructor_is_sealed(scratch):
    a=intake(scratch);baseline=a.base_covariances
    for v in (a.coverage,a.pc1_status,a.source_lock,a.formal_runs,a.incomplete_attempts,a.reproduction_crosscheck,a.base_covariances):v.clear()
    e=a.require_pc1_pass(20104);e['x0_CT'][0]=999
    assert a.base_covariances==baseline and a.require_pc1_pass(20104)==baseline['20104']
    with pytest.raises(InputContractError):da.D3aAssets({})
    with pytest.raises(AttributeError):a.coverage={}
    with pytest.raises(AttributeError):del a._payload

class Reader:
    def __init__(self,fh,callback):self.fh=fh;self.callback=callback
    def __enter__(self):self.fh.__enter__();return self
    def __exit__(self,*a):return self.fh.__exit__(*a)
    def __getattr__(self,n):return getattr(self.fh,n)
    def read(self,*a,**kw):
        b=self.fh.read(*a,**kw);self.callback();return b

def test_ledger_hash_and_consumed_dict_are_same_bytes(scratch,monkeypatch):
    path=scratch/LP;original=path.read_bytes();obj=json.loads(original);obj['incomplete_attempts']={};write(path,obj)
    # The actual read captures modified bytes. Only then restore the old bytes.
    # A correct same-bytes verifier must reject under the unchanged outer SHA.
    realopen=builtins.open;did=[]
    def hook(file,*a,**kw):
        fh=realopen(file,*a,**kw)
        if not did and isinstance(file,(str,os.PathLike)) and Path(file).resolve()==path.resolve() and (a[0] if a else kw.get('mode','r'))=='rb':
            def restore():
                if not did:did.append(True);path.write_bytes(original)
            return Reader(fh,restore)
        return fh
    monkeypatch.setattr(builtins,'open',hook)
    with pytest.raises((InputContractError,ValueError,OSError)):intake(scratch)
    assert did and hashlib.sha256(path.read_bytes()).hexdigest()==SHA

def test_correct_ledger_snapshot_survives_change_after_capture(scratch,monkeypatch):
    path=scratch/LP;original=path.read_bytes();obj=json.loads(original);obj['incomplete_attempts']={};altered=json.dumps(obj).encode();realopen=builtins.open;did=[]
    def hook(file,*a,**kw):
        fh=realopen(file,*a,**kw)
        if not did and isinstance(file,(str,os.PathLike)) and Path(file).resolve()==path.resolve() and (a[0] if a else kw.get('mode','r'))=='rb':
            def mutate():
                if not did:did.append(True);path.write_bytes(altered)
            return Reader(fh,mutate)
        return fh
    monkeypatch.setattr(builtins,'open',hook)
    try:a=intake(scratch)
    except (InputContractError,ValueError,OSError):return  # Safe rejection is also valid.
    assert a.ledger_sha256==SHA and len(a.incomplete_attempts)==2 and len(a.reproduction_crosscheck)==2

def test_incomplete_reference_consistency_even_with_new_diagnostic_digest(scratch):
    # Not a bypass of the old outer SHA: an explicitly re-bound DIAGNOSTIC record
    # still has contradictory clone file identity and should not claim reproduction.
    _,rec,d=incomplete_e8(scratch);p=d/'d3/d3_partial_evidence.json';obj=j(p)
    next(iter(obj['cases'].values()))['clone_identity']['file_sha256']='0'*64;write(p,obj)
    L=j(scratch/LP);key=next(k for k,v in L['incomplete_attempts'].items() if v['family']=='E8')
    L['incomplete_attempts'][key]['partial_evidence_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();write(scratch/LP,L)
    outer=hashlib.sha256((scratch/LP).read_bytes()).hexdigest()
    with pytest.raises((InputContractError,ValueError,OSError)):da.intake_registered_d3a_assets(str(scratch),outer)
