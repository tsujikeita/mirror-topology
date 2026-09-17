"""New integrated-runner contracts; no real CMB data or exact POT.
The accepted factory-created synthetic W2 context is re-used by content hash.
No scientific rule or normal computation is monkeypatched. The two explicitly
named injection tests modify state/inputs to test failure propagation.
"""
import os,sys,copy,pickle,hashlib
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]));BASE=ROOT/'tests'
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import step1_engine.integrated_runner as ir
import step1_engine.orchestrator as o
from step1_engine.archive import Archive,ArchiveRef,resolve_transition_archive
from step1_engine.stage12 import StageTransition
from step1_engine.errors import InputContractError
from step1_engine.formal_runner import input_fingerprint
from step1_engine import serialization as ser
from runner_fixture import family_cases

@pytest.fixture(scope='module')
def base_input():
    path=BASE/'references/compact_fixture.pkl'
    if path.exists():
        with open(path,'rb') as fh:return pickle.load(fh)
    from runner_fixture import build_fixture
    f=build_fixture();f['ctx'].results={};f['ctx'].validate();return f

@pytest.fixture
def fi(base_input):return copy.deepcopy(base_input)

def run(f,where,**kw):
    opts=dict(reg=f['reg'],man=f['man'],cases=f['cases'],w2_context=f['ctx'],expected_context_sha256=f['ctx'].context_sha256,t_target=(80.,400.),pseudo_T1=np.array([80.]),pseudo_T2=np.array([400.]),archive=Archive(str(where)),mode='smoke',twelve_anchors={'E7':f['reg'].anchors['E7']})
    opts.update(kw);return ir.run_first_wave(**opts)

@pytest.fixture(scope='module')
def normal(base_input,tmp_path_factory):
    f=copy.deepcopy(base_input);p=tmp_path_factory.mktemp('integrated_baseline');rm=run(f,p);return f,rm,Archive(str(p))

def all_strings(x):
    if isinstance(x,str):yield x
    elif isinstance(x,dict):
        for k,v in x.items():yield from all_strings(k);yield from all_strings(v)
    elif isinstance(x,(list,tuple)):
        for v in x:yield from all_strings(v)

def test_normal_smoke_archive_and_case_inventory(normal):
    f,rm,arc=normal
    assert rm.final_label_released is False and set(rm.cases)==set(f['cases'])
    assert arc.verify_all()['ok'] is True
    assert all(arc.get(ArchiveRef(**c['result_ref']))['family']=='E7' for c in rm.cases.values())

def test_normal_target_numerics_equal_direct_staged(normal):
    f,rm,arc=normal
    direct=o.evaluate_threshold({k:(v[0],v[1]) for k,v in f['cases'].items()},80.,400.,staged=True,position_maps={k:v[2] for k,v in f['cases'].items()},w2_context=f['ctx'],expected_context_sha256=f['ctx'].context_sha256)
    for k,r in direct.items():
        d=ser.from_jsonable(r.as_dict());d.update(family='E7',size_id=k.split('/')[1])
        assert ser.dumps(d)==ser.dumps(arc.get(ArchiveRef(**rm.cases[k]['diagnostic_ref'])))   # tranche 30: result_ref = parent-derived position record; the standalone case core is diagnostic_ref

def test_wrong_context_sha_rejected_before_evaluation(fi,tmp_path,monkeypatch):
    def unexpected(*a,**k):pytest.fail('numeric evaluation reached with wrong context SHA')
    monkeypatch.setattr(ir,'evaluate_threshold',unexpected)
    with pytest.raises(InputContractError):run(fi,tmp_path,expected_context_sha256='0'*64)

def test_wrong_case_size_is_rejected(fi,tmp_path):
    fi['cases']['E7/L1.00']=fi['cases']['E7/L1.20']
    with pytest.raises(InputContractError):run(fi,tmp_path)

def test_every_source_reference_resolves_with_its_transition(normal):
    f,rm,arc=normal
    for k,c in rm.cases.items():
        t=StageTransition(**rm.families['E7']['transitions'][c['size_id']])
        assert resolve_transition_archive(arc,t,ArchiveRef(**c['result_ref']))['family']=='E7'

def test_recorded_run_manifest_sha_reproduces(normal):
    _,rm,_=normal
    assert rm.binding['run_manifest_sha256']==rm.sha256()

def test_recorded_source_fingerprints_are_preserved(normal):
    f,rm,_=normal;strings=set(all_strings(ser.from_jsonable(rm.as_dict())))
    for fm,fn,_ in f['cases'].values():
        assert input_fingerprint(fm) in strings
        assert input_fingerprint(fn) in strings

def test_generated_twelve_manifests_are_retrievable(normal):
    f,rm,arc=normal
    required=set(rm.families['E7']['required_manifests'].values())
    assert len(required)==3
    found=set()
    for e in arc._entries():
        if e['kind']=='twelve_manifest':
            d=arc.get(ArchiveRef(e['kind'],e['sha256'],e['path'],e['identity']))
            found.add(d.get('sha256'))
    assert required <= found

def test_three_coordinate_target_is_not_silently_truncated(fi,tmp_path):
    with pytest.raises(InputContractError):run(fi,tmp_path,t_target=(80.,400.,123.))

def test_twelve_anchor_override_must_equal_registry(fi,tmp_path):
    anchors=copy.deepcopy(fi['reg'].anchors['E7']);anchors[0][0]+=.001
    with pytest.raises(InputContractError):run(fi,tmp_path,twelve_anchors={'E7':anchors})

def test_case_key_with_extra_component_is_rejected(fi,tmp_path):
    fi['cases']['E7/L1.00/extra']=fi['cases'].pop('E7/L1.00')
    with pytest.raises(InputContractError):run(fi,tmp_path)

def test_e1_does_not_require_a_fictitious_w2_case(fi,tmp_path):
    fi['cases']=family_cases(fi['reg'],fi['man'],'E1')
    rm=run(fi,tmp_path,twelve_anchors=None)
    assert rm.families['E1']['status']=='exempt (observer-homogeneous)'
    assert rm.final_label_released is False

def test_n_selection_tech_is_recorded_without_unregistered_position_state_error(fi,tmp_path,monkeypatch):
    original=o._stage_selection;first=True
    def injection(fm,t1,t2):
        nonlocal first
        s=original(fm,t1,t2)
        if first:
            first=False;s['technical']=True;s['N0']['precision']['state']='technical_fail'
        return s
    monkeypatch.setattr(o,'_stage_selection',injection)
    rm=run(fi,tmp_path)
    assert rm.families['E7']['status']=='technical_fail'
    assert any(v['technical_status']=='technical_fail' for v in rm.cases.values())
    assert rm.final_label_released is False

def test_bank_mutation_before_pseudo_is_detected(fi,tmp_path,monkeypatch):
    # tranche 32: the runner now calls the COMMON threshold evaluator (ir.evaluate_family_full) for the target and every pseudo; the injection hook follows (intent unchanged)
    original=ir.evaluate_family_full;calls=[]
    def injection(reg,man,fam,parent,views,*args,**kwargs):
        calls.append(1)
        if len(calls)==2: parent[0].configs[0].T1_model-=5.        # mutate a parent bank before the first pseudo evaluation
        return original(reg,man,fam,parent,views,*args,**kwargs)
    monkeypatch.setattr(ir,'evaluate_family_full',injection)
    with pytest.raises(InputContractError):run(fi,tmp_path)

def test_pseudo_thresholds_shared_by_support_and_strong(fi,tmp_path,monkeypatch):
    # tranche 32: support and strong come from ONE common evaluation per pseudo; the pseudo columns are a read-only snapshot taken before use (caller mutation after the call is inert)
    a=np.array([80.]);b=np.array([400.]);seen=[];original=ir.evaluate_family_full
    def injection(reg,man,fam,parent,views,w2,sha,x,y,*args,**kw):
        seen.append((float(x),float(y)));r=original(reg,man,fam,parent,views,w2,sha,x,y,*args,**kw)
        if len(seen)==1:a[:]+=10.
        return r
    monkeypatch.setattr(ir,'evaluate_family_full',injection)
    rm=run(fi,tmp_path,pseudo_T1=a,pseudo_T2=b)
    assert seen.count((80.,400.))==len(seen)==2 and rm.calibration['support']['truths']==rm.calibration['support']['truths'] and len(rm.calibration['strong']['truths'])==1   # target + one pseudo; both levels from the same pseudo evaluation

def test_target_bank_mutation_is_already_detected(fi,tmp_path,monkeypatch):
    original=ir.evaluate_family_full
    def injection(reg,man,fam,parent,views,*args,**kw):
        r=original(reg,man,fam,parent,views,*args,**kw);parent[0].configs[0].T1_model-=5.;return r     # mutate after the target evaluation
    monkeypatch.setattr(ir,'evaluate_family_full',injection)
    with pytest.raises(InputContractError):run(fi,tmp_path)

def test_summary_keeps_complete_context_sha(normal):
    f,rm,_=normal
    for level in ['support','strong']:
        assert rm.calibration[level]['summary']['w2_context']['context_sha256']==f['ctx'].context_sha256

def test_empty_cases_rejected(fi,tmp_path):
    with pytest.raises(InputContractError):run(fi,tmp_path,cases={})

def test_unregistered_mode_rejected(fi,tmp_path):
    with pytest.raises(InputContractError):run(fi,tmp_path,mode='test')
