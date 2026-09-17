"""Tranche33 independent boundary/round-trip tests on finite synthetic banks.
W2 uses the published test-only mean-distance fixture, not exact POT/physical data.
No registered thresholds or core decision functions are changed. Mutation tests
are explicitly injected after target, before pseudo; numeric outputs are not faked.
"""
import os,sys,copy,pickle,hashlib
from pathlib import Path
import tempfile
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1])); WORK=Path(os.environ.get('AUDIT33_DIR',tempfile.mkdtemp(prefix='audit33_')))
for _d in ('cache','archives','reference'): (WORK/_d).mkdir(parents=True,exist_ok=True)
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import numpy as np
import pytest
from fixture32 import base,twelve_from_cases,multifamily_trigger_only_pseudo,diagnostic_cases
from test_b2_tranche14 import TwelveFixture
from step1_engine import integrated_runner as ir, serialization as ser
from step1_engine.threshold_evaluator import evaluate_family_full
from step1_engine.archive import Archive,ArchiveRef
from step1_engine.checkpoint import write_family_result,read_family_result
from step1_engine.formal_runner import input_fingerprint
from step1_engine.errors import InputContractError

@pytest.fixture(scope='module')
def b():return base()
@pytest.fixture(scope='module')
def ti(b):
    f=TwelveFixture(sizes=b['reg'].surviving['E7'],K=800,Kf=800,B=60)
    t=dict(size_inputs=f.inputs,position_ids=f.maps,native_position_ids=f.nmaps)
    with open(WORK/'cache/twelve.pkl','wb') as h:pickle.dump(t,h)
    return t

def evaluate(b,ti,thr=(100.,550.)):
    views={k.split('/')[1]:v for k,v in b['cases'].items()}
    par=ir.assemble_parent(b['reg'],b['man'],'E7',{s:v[:2] for s,v in views.items()})
    return evaluate_family_full(b['reg'],b['man'],'E7',par,views,b['ctx'],b['ctx'].context_sha256,*thr,ti,with_diagnostics=False)

def run(b,ti,path,target=(100.,550.),x=None,y=None,**kw):
    a=Archive(str(path));r=ir.run_first_wave(b['reg'],b['man'],b['cases'],b['ctx'],b['ctx'].context_sha256,target,
        [target[0]] if x is None else x,[target[1]] if y is None else y,a,twelve_inputs=(None if ti is None else {'E7':ti}),**kw)
    return r,a

@pytest.fixture(scope='module')
def normal(b,ti):
    r,a=run(b,ti,WORK/'archives/normal')
    g=a.get(ArchiveRef(**r.archive_refs['twelve_family_core:E7']))
    (WORK/'reference/normal12_result.json').write_text(ser.dumps(g))
    (WORK/'reference/normal_run.json').write_text(ser.dumps(r.as_dict()))
    return r,a,g

@pytest.fixture(scope='module')
def optional(b):
    t=twelve_from_cases(diagnostic_cases(b['reg'],b['man'],all_sizes_need_ci=False))
    f=evaluate(b,t,(80.,400.));(WORK/'reference/diagnostic12_resolved.json').write_text(ser.dumps(f.twelve))
    return f,t


def test_completion_records_derive_parent_state_truth_and_exact_inventory(normal,ti):
    r,a,g=normal;z=r.families['E7']['twelve']
    assert len(g['per_config'])==36 and len(g['native']['per_config'])==36
    assert set(z['completion_records'])==set(ti['size_inputs'])
    for s,c in z['completion_records'].items():
        ids=set(ti['position_ids'][s]);actual={e:g['per_config'][e]['precision']['state'] for e in ids}
        assert c['precision']['per_configuration']==actual
        assert c['truths']==g['truths']
        assert c['decision']['technical_status']==g['decision']['technical_status']
        assert c['evidence']['twelve_manifest_sha256']==g['evidence']['identity']['twelve_manifests'][s]
    assert z['family_local_completion'] is True


def test_target_full_result_archive_roundtrip_is_bit_preserving_and_referenced(normal):
    r,old,g=normal;a=Archive(old.root)
    rr=ir.RunManifest(**a.get(ArchiveRef(**r.binding['run_manifest_ref'])))
    assert rr.payload_sha()==r.payload_sha()
    back=a.get(ArchiveRef(**rr.archive_refs['twelve_family_core:E7']))
    assert ser.dumps(back)==ser.dumps(g)
    assert back['evidence']['threshold']==r.thresholds['target']
    for k in ('Q_ci_seed0','logD','per_config','native','evidence'):assert k in back
    assert 'full_result' not in rr.families['E7']['twelve']
    assert a.verify_all()['ok']


def test_full_twelve_result_also_passes_existing_semantic_checkpoint_reader(normal,tmp_path):
    r,a,g=normal;p=str(tmp_path/'complete_result.json')
    sha=write_family_result(g,p);d=read_family_result(p,sha)
    assert d['verified'].startswith('verified')
    assert ser.dumps(d['result'])==ser.dumps(g)


def test_optional_diagnostic_tech_kept_without_vetoing_parent_completion(optional):
    f,ti=optional;g=f.twelve['full_result'];d=g['per_size_diagnostic']['L1.00']
    assert d['logD']['ci']['counts']=={'finite':28,'technical_invalid':2}
    assert d['decision']['technical_status']=='technical_fail'
    assert g['decision']['technical_status']=='ok' and g['logD']['ci'] is None
    assert f.eligible_truths['support'] is True
    assert all(c['decision']['technical_status']=='ok' for c in f.twelve['completion_records'].values())


def test_optional_diagnostic_failure_survives_semantic_roundtrip(optional,tmp_path):
    f,t=optional;p=str(tmp_path/'diagnostic_tech_parent_ok.json');g=f.twelve['full_result']
    sha=write_family_result(g,p);d=read_family_result(p,sha)['result']
    assert d['truths']['support'] is True
    assert d['per_size_diagnostic']['L1.00']['logD']['ci']['math_state']=='technical_fail'


def test_genuinely_required_parent_ci_tech_reaches_completion_and_eligibility(b):
    t=twelve_from_cases(diagnostic_cases(b['reg'],b['man'],all_sizes_need_ci=True))
    f=evaluate(b,t,(80.,400.))
    assert set(f.eligible_truths.values())=={'technical_fail'}
    assert f.twelve['family_local_completion'] is False
    assert all(c['decision']['technical_status']=='technical_fail' for c in f.twelve['completion_records'].values())
    (WORK/'reference/required12_tech.json').write_text(ser.dumps(f.twelve))


def test_coverage_unknown_is_not_reported_as_an_unexecuted_branch(b,ti,tmp_path):
    t=copy.deepcopy(ti)
    for pair in t['size_inputs'].values():
        for f in pair:f.coverage_ok=False
    r,a=run(b,t,tmp_path)
    assert r.branch_completeness['missing_branches']==[]
    assert r.families['E7']['twelve']['family_local_completion'] is False
    assert set(r.families['E7']['eligible_truths'].values())=={'unknown'}
    assert r.calibration['support']['truths']==['unknown']
    assert r.calibration['support']['full_procedure'] is False # only E7 supplied


@pytest.mark.parametrize('side',['matched','native'])
def test_each_position_mapping_locked_through_pseudo(b,ti,tmp_path,monkeypatch,side):
    t=copy.deepcopy(ti);old=ir.evaluate_family_full;calls=0
    def wrapped(*args,**kw):
        nonlocal calls
        calls+=1
        if calls==2:
            mp=t['position_ids' if side=='matched' else 'native_position_ids']['L1.00'];e=list(mp)
            mp[e[0]],mp[e[1]]=mp[e[1]],mp[e[0]] # still a valid permutation
        return old(*args,**kw)
    monkeypatch.setattr(ir,'evaluate_family_full',wrapped)
    with pytest.raises(InputContractError):run(b,t,tmp_path)


def test_twelve_fingerprints_and_maps_survive_saved_run(normal,ti):
    r,a,g=normal; rr=a.get(ArchiveRef(**r.binding['run_manifest_ref']))
    assert rr['fingerprints']['at_gate']==rr['fingerprints']['at_end']
    for s,pair in ti['size_inputs'].items():
        row=rr['fingerprints']['at_gate']['twelve:E7/'+s]
        assert row['matched']==input_fingerprint(pair[0]);assert row['native']==input_fingerprint(pair[1])
        assert row['position_ids']==repr(sorted(ti['position_ids'][s].items()))
        assert row['native_position_ids']==repr(sorted(ti['native_position_ids'][s].items()))

@pytest.fixture(scope='module')
def multi(b):
    f=multifamily_trigger_only_pseudo(b)
    with open(WORK/'cache/multifamily.pkl','wb') as h:pickle.dump(f,h)
    return f


def test_missing_branches_enumerate_pseudo_index_and_family(multi,tmp_path):
    r,a=run(multi,None,tmp_path,target=(200.,1000.),x=[80.,200.],y=[400.,1000.],require_all_families=True)
    assert r.branch_completeness['all_registered_families'] is True
    assert r.branch_completeness['missing_branches']==[{'where':'pseudo[0]','family':'E7','reason':'triggered 12-position stage not evaluated'}]
    for lv in ('support','strong'):
        assert r.calibration[lv]['full_procedure'] is False
        assert 'NOT the registered full-procedure calibration' in r.calibration[lv]['summary']['reason']
    saved=a.get(ArchiveRef(**r.binding['run_manifest_ref']))
    assert saved['branch_completeness']==r.branch_completeness
    (WORK/'reference/pseudo_missing_scope.json').write_text(ser.dumps(r.as_dict()))


def test_pseudo_only_twelve_branch_counts_as_completed_when_executed(multi,ti,tmp_path):
    r,a=run(multi,ti,tmp_path,target=(200.,1000.),x=[80.,200.],y=[400.,1000.],require_all_families=True)
    assert not any(z['expand_family'] for z in r.families.values())
    st=r.per_pseudo_family_status[0]['E7'];assert st['expand_family'] and st['twelve']['evaluated']
    assert r.branch_completeness['missing_branches']==[]
    for lv in ('support','strong'):assert r.calibration[lv]['full_procedure'] is True
    assert r.final_label_released is False
    (WORK/'reference/pseudo_completed_scope.json').write_text(ser.dumps(r.as_dict()))
