"""Additional integration acceptance tests. Finite synthetic banks, test-only W2.
No changes to RULES, truth functions or solver results. Mutations are explicit test injections.
Set PHASEB_ROOT to the package root. Optional locally generated cache avoids fixture rebuilds;
no pickle is distributed with the evidence archive.
"""
import os,sys,copy,pickle
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parent),str(Path(__file__).resolve().parents[1])]
from fixture32 import *
import pytest
from step1_engine import integrated_runner as ir
from step1_engine.threshold_evaluator import evaluate_family_full
from step1_engine.twelve_eval import evaluate_twelve_family_mixture
from step1_engine.stage12 import generate_twelve,StageTransition
from step1_engine.archive import Archive,ArchiveRef,resolve_transition_archive
from step1_engine import serialization as ser
from step1_engine import orchestrator as orch
from step1_engine.errors import InputContractError
from audit_fixture30 import negative_context
from test_b2_tranche14 import TwelveFixture

@pytest.fixture(scope='module')
def b():return base()
@pytest.fixture(scope='module')
def ti(b):
    if (R/'twelve.pkl').exists():
        with open(R/'twelve.pkl','rb') as h:return pickle.load(h)
    f=TwelveFixture(sizes=b['reg'].surviving['E7'],K=800,Kf=800,B=60)
    return dict(size_inputs=f.inputs,position_ids=f.maps,native_position_ids=f.nmaps)
@pytest.fixture(scope='module')
def neg(b):
    if (R/'negative.pkl').exists():
        with open(R/'negative.pkl','rb') as h:return pickle.load(h)
    return negative_context(b)
def evaluate(b,ti=None,thr=(100.,550.),cases=None,ctx=None,family='E7'):
    cs=b['cases'] if cases is None else cases
    views={k.split('/')[1]:v for k,v in cs.items()}
    p=ir.assemble_parent(b['reg'],b['man'],family,{s:v[:2] for s,v in views.items()})
    w=b['ctx'] if ctx is None else ctx
    return evaluate_family_full(b['reg'],b['man'],family,p,views,w,w.context_sha256,*thr,ti,with_diagnostics=False)
def run(b,ti,path,**kw):
    opts=dict(t_target=(100.,550.),pseudo_T1=[100.],pseudo_T2=[550.],mode='smoke');opts.update(kw)
    arc=Archive(str(path))
    r=ir.run_first_wave(b['reg'],b['man'],b['cases'],b['ctx'],b['ctx'].context_sha256,archive=arc,twelve_inputs=(None if ti is None else {'E7':ti}),**opts)
    return r,arc
@pytest.fixture(scope='module')
def normal(b,ti,tmp_path_factory):
    return run(b,ti,tmp_path_factory.mktemp('normal32'))

def test_nonexpanded_uses_family_core_once_as_truth(b,neg):
    r=evaluate(b,ctx=neg)
    assert r.plan_status=='final at 3 positions'
    assert r.eligible_truths==r.parent.truths and r.twelve is None

def test_E1_exempt_retains_family_truths(b):
    cs=family_cases(b['reg'],b['man'],'E1')
    r=evaluate(b,cases=cs,family='E1')
    assert r.plan_status=='exempt (observer-homogeneous)' and r.twelve is None
    assert r.eligible_truths==r.parent.truths

def test_required_three_position_tech_is_retained(b,neg):
    cs=diagnostic_cases(b['reg'],b['man'],all_sizes_need_ci=True)
    r=evaluate(b,cases=cs,ctx=neg,thr=(80.,400.))
    assert set(r.eligible_truths.values())=={'technical_fail'}

def test_expanded_without_twelve_inputs_is_unknown(b):
    r=evaluate(b)
    assert r.expand_family and set(r.eligible_truths.values())=={'unknown'}

def test_successful_twelve_mixture_matches_direct_registered_evaluation(b,ti):
    mans={s:generate_twelve('E7',s,np.array(b['reg'].anchors['E7'])) for s in b['reg'].surviving['E7']}
    g=evaluate_twelve_family_mixture(ti['size_inputs'],mans,ti['position_ids'],b['reg'].size_prior['E7'],100.,550.,native_position_ids=ti['native_position_ids'])
    r=evaluate(b,ti)
    assert r.twelve['family_local_completion'] is True
    assert r.eligible_truths==g['truths']
    assert r.twelve['family_mixture']['Q_point']==g['Q_point']

def test_transition_and_manifest_refs_resolve_after_normal_twelve_evaluation(normal):
    r,arc=normal
    assert r.families['E7']['twelve_stage']=='evaluated in this run'
    for k,c in r.cases.items():
        tr=StageTransition(**r.families['E7']['transitions'][c['size_id']])
        assert resolve_transition_archive(arc,tr,ArchiveRef(**c['result_ref']))['size_id']==c['size_id']
    for s,sha in r.families['E7']['required_manifests'].items():
        body=arc.get(ArchiveRef(**r.archive_refs['twelve_manifest:E7/'+s]))
        assert body['sha256']==sha
    assert arc.verify_all()['ok']

def test_support_strong_extracted_from_same_pseudo_evaluation(b,tmp_path,monkeypatch):
    f=copy.deepcopy(b);old=ir.evaluate_family_full;seen=[]
    def observed(*a,**kw):
        r=old(*a,**kw);seen.append(dict(r.eligible_truths));return r
    monkeypatch.setattr(ir,'evaluate_family_full',observed)
    r,arc=run(f,None,tmp_path)
    assert len(seen)==2
    assert r.calibration['support']['truths']==[seen[1]['support']]
    assert r.calibration['strong']['truths']==[seen[1]['strong']]

def test_twelve_coverage_unresolved_not_rescued(b,ti):
    bad=copy.deepcopy(ti)
    for pair in bad['size_inputs'].values():
        for f in pair:f.coverage_ok=False
    r=evaluate(b,bad)
    assert r.twelve['family_local_completion'] is False
    assert set(r.eligible_truths.values())=={'unknown'}

def test_necessary_twelve_family_ci_tech_is_retained(b):
    ti2=twelve_from_cases(diagnostic_cases(b['reg'],b['man'],all_sizes_need_ci=True))
    r=evaluate(b,ti2,thr=(80.,400.))
    assert set(r.eligible_truths.values())=={'technical_fail'}
    assert r.twelve['family_mixture']['decision']['technical_status']=='technical_fail'

def test_optional_size_ci_does_not_veto_valid_twelve_parent(b):
    ti2=twelve_from_cases(diagnostic_cases(b['reg'],b['man'],all_sizes_need_ci=False))
    r=evaluate(b,ti2,thr=(80.,400.))
    assert r.twelve['family_mixture']['truths']['support'] is True
    assert r.twelve['family_mixture']['decision']['technical_status']=='ok'
    assert r.eligible_truths['support'] is True, 'an optional per-size diagnostic CI must not veto the required family evaluation'

@pytest.mark.parametrize('kind',['bank','fit_plan_identity'])
def test_active_twelve_inputs_fixed_through_pseudo(b,ti,tmp_path,monkeypatch,kind):
    f=copy.deepcopy(b);supply=copy.deepcopy(ti);old=ir.evaluate_family_full;count=0
    def injected(*a,**kw):
        nonlocal count
        count+=1
        if count==2:
            fam=supply['size_inputs']['L1.00'][0]
            if kind=='bank':fam.configs[0].T1_model-=5.
            else:
                for plan in fam.fit_plans.values():plan.plan_id+='-modified-after-gate'
        return old(*a,**kw)
    monkeypatch.setattr(ir,'evaluate_family_full',injected)
    with pytest.raises(InputContractError):run(f,supply,tmp_path)

def test_full_procedure_flag_accounts_for_pseudo_trigger_not_just_target(b,tmp_path):
    if (R/'multifamily.pkl').exists():
        with open(R/'multifamily.pkl','rb') as h:f=pickle.load(h)
    else:f=multifamily_trigger_only_pseudo(b)
    a=Archive(str(tmp_path))
    r=ir.run_first_wave(f['reg'],f['man'],f['cases'],f['ctx'],f['ctx'].context_sha256,(200.,1000.),[80.],[400.],a,require_all_families=True)
    assert not any(z['expand_family'] for z in r.families.values())
    assert r.per_pseudo_family_status[0]['E7']['expand_family'] is True
    assert r.per_pseudo_family_status[0]['E7']['twelve'] is None
    assert r.calibration['support']['truths']==['unknown']
    assert r.calibration['support']['full_procedure'] is False
    assert 'NOT the registered full-procedure calibration' in r.calibration['support']['summary']['reason']

def test_evaluated_twelve_parent_evidence_is_persisted_or_resolvably_referenced(normal):
    r,arc=normal
    assert r.families['E7']['twelve_stage']=='evaluated in this run'
    blobs=[]
    for p in Path(arc.root).rglob('*.json'):
        blobs.append(ser.loads(p.read_text()))
    def has_full_result(d):
        if isinstance(d,dict):
            if d.get('evidence',{}).get('stage')=='12-position-family' and len(d.get('per_config',{}))==36 and 'Q_ci_seed0' in d and 'logD' in d:return True
            return any(has_full_result(v) for v in d.values())
        if isinstance(d,list):return any(has_full_result(v) for v in d)
        return False
    assert any(has_full_result(d) for d in blobs), 'evaluated twelve-stage family evidence should survive the common evaluator/runner boundary'
