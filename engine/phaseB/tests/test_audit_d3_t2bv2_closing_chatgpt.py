# -*- coding: utf-8 -*-
# ChatGPT audit contracts for D-3 tranche 2b v2 0.90.0 (R-D3T2BV2-A/B closing; 28 cases), bundled with path adaptation only. Original: tests/test_d3_t2bv2_closing.py of the reference-patch bundle.
"""New D3-2b-v2 boundary checks. All numerical banks here are TEST-ONLY.
Registered map/receipts/covariances are real submitted artifacts. No CT
covariance generation, no full-sized bank, no calibration and no labels.
A returned public context view must not mutate its verified source. Five
seed records cannot substitute for nonempty evaluation plans.
"""
from pathlib import Path
import os, sys, copy, hashlib, importlib.util, json
import numpy as np
import pytest
P=Path(os.environ.get('AUDIT_PHASEB_ROOT',str(Path(__file__).resolve().parent.parent))).resolve();sys.path.insert(0,str(P))   # path adaptation (Claude): default = this phaseB tree; AUDIT_PHASEB_ROOT still honoured
spec=importlib.util.spec_from_file_location('audit_t2bv2_prior_helpers',P/'tests/test_audit_d3_t2b_contracts_chatgpt.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
d=h.dp;Fixture=h.Fixture;InputContractError=h.InputContractError

def ctx(): return d.twelve_context(str(P))
def stamp(ident):ident['identity_sha256']=d._payload_sha(ident,'identity_sha256');return ident

@pytest.mark.parametrize('resource',['registry','twelve_assets'])
def test_public_resource_view_edits_are_detached(resource):
    c=ctx();v=getattr(c,resource);before=v.as_dict();ids=c.identities
    if resource=='registry':v.surviving['E2'].pop()
    else:v.manifests['E2'].pop('L1.50')
    # These are documented public views, not edits to _d or internal tokens.
    assert getattr(c,resource).as_dict()==before
    assert c.identities==ids and c.verified
    getattr(c,resource).validate()


def test_public_registry_edit_cannot_promote_partial_scope():
    c=ctx();f=Fixture('E2',sizes=('L1.00',));ss=h.inputs(f)
    before=d.assemble_twelve_family(c,'E2',ss)[2];assert before['full_surviving_scope'] is False
    view=c.registry;view.surviving['E2']=['L1.00'];view.size_prior['E2']={'L1.00':1.0}
    fm,fn,after=d.assemble_twelve_family(c,'E2',ss)
    assert after['full_surviving_scope'] is False
    assert after==before
    gate=d.twelve_official_gate(fm,fn,'official',plan_identity=f.plan_identity,table=c.table)
    assert not gate.passed

@pytest.mark.parametrize('empty_seeds',[[0],[4],list(range(5))])
def test_every_seed_has_nonempty_evaluation_content(empty_seeds):
    f=Fixture();plans=copy.deepcopy(f.plans);ident=copy.deepcopy(f.plan_identity)
    for s in empty_seeds:
        plans[s].strata={};plans[s].rng_keys={};plans[s].multiplicities={}
        rec=next(r for r in ident['evaluation'] if r['seed_id']==s)
        rec['rng_keys']={};rec['strata_uid_sha256']={};rec['multiplicity_sha256']={}
    stamp(ident)
    # Diagnostic identity was rehashed; not a bypass of a previous fixed SHA.
    with pytest.raises(InputContractError):
        d.verify_plan_identity(plans,f.fplans,ident,table=f.plan_identity and h.TABLE,family='E2')

@pytest.mark.parametrize('family',['E2','E7','E8'])
def test_full_family_and_context_normal(family):
    c=ctx();f=Fixture(family);fm,fn,inf=d.assemble_twelve_family(c,family,h.inputs(f))
    assert inf['full_surviving_scope'] and len(fm.configs)==len(fn.configs)==36
    assert all(x.weight==1/36 for x in fm.configs+fn.configs)
    g=d.twelve_official_gate(fm,fn,'smoke',plan_identity=f.plan_identity,table=c.table)
    assert g.passed and all(x['passed'] for x in g.diagnostics['twelve_checks'])
    assert d.load_registered_bank_spec_v2(c)['counts']['generate']==81

@pytest.mark.parametrize('family',['E2','E7','E8'])
def test_nonempty_two_batch_and_reordered_seed_records(family):
    g=h.author.group_for(h.TABLE,'evaluation',family)
    u={b:[h.ClusterUID(1,200,g,b,i) for i in range(K)] for b,K in [(0,2),(1,6)]}
    p,f,ident=d.fix_family_plans(h.TABLE,family,u,3,h.TABLE['master_seed'],B=7,B_KDE=9)
    expected=copy.deepcopy(ident);ident['evaluation'].reverse();ident['fitting']=ident['fitting'][2:]+ident['fitting'][:2];stamp(ident)
    assert d.verify_plan_identity(p,f,ident,table=h.TABLE,family=family)
    assert d.verify_plan_identity(p,f,expected,table=h.TABLE,family=family)
    assert all(set(q.strata)=={0,1} for q in p.values())

@pytest.mark.parametrize('field,value',[('family','E8'),('master_seed',0),('wave_id',2),('evaluation_group',999),('fitting_group',999),('B',21),('B_KDE',26)])
def test_fixed_header_mismatch_refused(field,value):
    f=Fixture();ident=copy.deepcopy(f.plan_identity);ident[field]=value;stamp(ident)
    with pytest.raises(InputContractError):d.verify_plan_identity(f.plans,f.fplans,ident,table=h.TABLE,family='E2')

@pytest.mark.parametrize('seed',[0,4])
def test_valid_multiplicity_changes_fail_fixed_identity(seed):
    f=Fixture();m=f.plans[seed].multiplicities[0];j=int(np.flatnonzero(m[0])[0]);m[0,j]-=1;m[0,(j+1)%m.shape[1]]+=1
    f.plans[seed].validate()
    with pytest.raises(InputContractError):d.verify_plan_identity(f.plans,f.fplans,f.plan_identity)

@pytest.mark.parametrize('purpose',['evaluation','fitting'])
def test_duplicate_record_refused(purpose):
    f=Fixture();ident=copy.deepcopy(f.plan_identity);ident[purpose][4]=copy.deepcopy(ident[purpose][0]);stamp(ident)
    with pytest.raises(InputContractError):d.verify_plan_identity(f.plans,f.fplans,ident)


def test_gate_rechecks_plan_content_not_only_shared_object():
    f=Fixture();fm,fn,info=f.family_inputs()
    m=f.plans[4].multiplicities[0];j=int(np.flatnonzero(m[0])[0]);m[0,j]-=1;m[0,(j+1)%m.shape[1]]+=1
    g=d.twelve_official_gate(fm,fn,'smoke',plan_identity=f.plan_identity,table=h.TABLE)
    assert not g.passed and all(not x['passed'] for x in g.diagnostics['twelve_checks'] if x['code'].endswith('plan_identity_fixed'))


def test_remaining_context_public_dicts_are_detached():
    c=ctx();attrs=['pins','config_map','receipt','table','d2_spec','d2_ledger','identities']
    for attr in attrs:
        v=getattr(c,attr);expected=copy.deepcopy(v);v.clear();assert getattr(c,attr)==expected
    with pytest.raises(InputContractError):d.TwelveContext({})
    with pytest.raises(AttributeError):c.root='/INVALID'
    with pytest.raises(InputContractError):d.build_bank_spec_v2(c.receipt)


def test_spec_output_and_source_are_independent():
    c=ctx();expected=d.load_registered_bank_spec_v2(c);v=d.build_bank_spec_v2(c)
    v['configurations']['20104']['covariance']['cov_file_sha256']='0'*64
    assert d.build_bank_spec_v2(c)==expected
    with pytest.raises(InputContractError):d.verify_bank_spec_v2(v,c)


def test_temp_snapshot_write_failure_never_consumes_original(tmp_path,monkeypatch):
    root=h.author._copy_root(tmp_path/'root');target,raw,calls=h.loader_setup(monkeypatch,root,20104)
    temp=tmp_path/'temp';temp.mkdir();monkeypatch.setattr(d.tempfile,'mkdtemp',lambda **k:str(temp))
    realopen=open
    def faulty(file,mode='r',*a,**kw):
        if str(file).startswith(str(temp)) and 'w' in mode:raise OSError('TEST snapshot write fault')
        return realopen(file,mode,*a,**kw)
    monkeypatch.setattr('builtins.open',faulty)
    with pytest.raises((OSError,InputContractError)):d.intake_twelve_covariance(20104,root,'TEST_ONLY')
    assert not calls and not temp.exists() and target.read_bytes()==raw


def test_loader_snapshot_mutation_refused_and_cleaned(tmp_path,monkeypatch):
    root=h.author._copy_root(tmp_path/'root');target,raw,calls=h.loader_setup(monkeypatch,root,20104)
    temp=tmp_path/'temp';temp.mkdir();monkeypatch.setattr(d.tempfile,'mkdtemp',lambda **k:str(temp))
    class MutatingLoader:
        def load_cov_full(self,path,lmax):
            raw0=Path(path).read_bytes();arr=np.load(h.io.BytesIO(raw0),allow_pickle=False);U,Cr=h.raw_to_real(arr)
            Path(path).write_bytes(raw0+b'TEST_CHANGED_SNAPSHOT')
            return U,Cr,{'cov_array_sha256':hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()}
    monkeypatch.setattr(d,'_verified_frozen_loader',lambda *a:(MutatingLoader(),{'test_double':True}))
    with pytest.raises(InputContractError):d.intake_twelve_covariance(20104,root,'TEST_ONLY')
    assert not temp.exists() and target.read_bytes()==raw
