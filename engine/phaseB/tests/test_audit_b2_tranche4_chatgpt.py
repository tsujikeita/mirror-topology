"""Source-contract tests for tranche4. Synthetic fixtures only; no official profile/CMB or large OT.
Run: PHASEB_ROOT=/path/phaseB OPENBLAS_NUM_THREADS=1 python -m pytest -q this_file.py
"""
import os,sys,copy
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]));sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_b2_tranche3 import make_family_pair
from test_b2_tranche4 import make_staged_family
import step1_engine.orchestrator as o
from step1_engine.errors import InputContractError
from step1_engine.truth import TECH,UNKNOWN

@pytest.mark.parametrize('entry',['family','threshold','pseudo'])
def test_distinct_matched_native_ids_work_in_staged_entry(entry):
    fm,fn,_=make_family_pair(np.random.default_rng(20260914))
    assert fm.configs[0].evaluation_id==100 and fn.configs[0].evaluation_id==150
    if entry=='family': r=o.evaluate_family_staged(fm,fn,80.,400.); assert r.native is not None
    elif entry=='threshold': r=o.evaluate_threshold({'E7':(fm,fn)},80.,400.,staged=True)['E7'];assert r.native is not None
    else:
        summary,truths=o.calibrate_pseudo({'E7':(fm,fn)},[80.],[400.],staged=True)
        assert summary.n==1 and len(truths)==1

def staged_pair(easy_system):
    fm=make_staged_family(np.random.default_rng(1),n_cfg=1)
    c=fm.configs[0];fb=fm.fitting[c.evaluation_id]
    # A distinct native ID, same latent/UID; the native role has a different reference transform.
    native_cfg=o.ConfigBank(150,'E7','native',1.,c.T1_model.copy(),c.T2_model.copy(),c.T1_ref.copy(),c.T2_ref.copy(),c.cluster_uids,c.m,dict(c.batches))
    native_fit=o.FittingBank(fb.X_model.copy(),fb.X_ref.copy(),fb.cid.copy())
    fn=o.FamilyInput('E7',[native_cfg],fm.plans,{150:native_fit},fm.fit_plans)
    easy=fm if easy_system=='matched' else fn
    cc=easy.configs[0]
    for name,center,target in [('T1_model',120.,80.),('T1_ref',120.,80.),('T2_model',600.,400.),('T2_ref',600.,400.)]:
        setattr(cc,name,(getattr(cc,name)-center)*.5+target)
    ff=easy.fitting[cc.evaluation_id]
    ff.X_model=(ff.X_model-[120,600])*.5+[80,400];ff.X_ref=(ff.X_ref-[120,600])*.5+[80,400]
    return fm,fn

@pytest.mark.parametrize('easy_system',['matched','native'])
def test_stage_choice_is_per_system_not_copied_from_matched(easy_system):
    fm,fn=staged_pair(easy_system)
    before=o.evaluate_family(o._stage_family(fm,{100:'N0'}),o._stage_family(fn,{150:'N0'}),80.,400.)
    bm=before.per_config[100]['precision']['state'];bn=before.native['per_config'][150]['precision']['state']
    assert (bm=='pass')==(easy_system=='matched') and (bn=='pass')==(easy_system=='native')
    r=o.evaluate_family_staged(fm,fn,80.,400.)
    assert r.per_config[100]['stage']==('N0' if easy_system=='matched' else 'N4')
    assert r.native['per_config'][150]['stage']==('N0' if easy_system=='native' else 'N4')

def test_technical_failure_is_not_healed_by_precision_expansion(monkeypatch):
    fm=make_staged_family(np.random.default_rng(1));original=o._family_logD;calls=[]
    def fail_first(*args,**kwargs):
        calls.append(1)
        if len(calls)==1:return float('nan'),None,{},False,{'technical':True,'per_point':{},'reason':'deliberate technical-failure injection'}
        return original(*args,**kwargs)
    monkeypatch.setattr(o,'_family_logD',fail_first)
    try:r=o.evaluate_family_staged(fm,None,80.,400.)
    except InputContractError:return  # stopping is also an acceptable fail-closed policy
    assert r.decision['technical_status']=='technical_fail'
    assert r.truths['support']==TECH

@pytest.mark.parametrize('factor',[2,3,5])
def test_N4_means_four_times_the_registered_prefix(factor):
    # Tiny rows isolate the stage contract. A formal 1e6 profile is NOT imposed on unit fixtures.
    from step1_engine.types import ClusterUID
    m=2;K0=3;N0=m*K0;N=factor*N0
    uids=[ClusterUID(1,200,1,0,i) for i in range(K0)]+[ClusterUID(1,200,1,1,i) for i in range((factor-1)*K0)]
    a=np.arange(N,dtype=float)
    with pytest.raises(InputContractError):
        c=o.ConfigBank(100,'E7','matched',1.,a,a,a,a,uids,m,{0:(0,N0),1:(N0,N)})
        c.at_stage('N4')

def test_normal_fourfold_views_keep_prefix_and_full_rows():
    f=make_staged_family(np.random.default_rng(4),n_cfg=1);c=f.configs[0]
    p=c.at_stage('N0');q=c.at_stage('N4')
    assert len(q.T1_model)==4*len(p.T1_model)
    assert np.array_equal(p.T1_ref,q.T1_ref[:len(p.T1_ref)])

def test_ordinary_two_system_entry_remains_valid():
    fm,fn,_=make_family_pair(np.random.default_rng(20260914))
    assert o.evaluate_family(fm,fn,80.,400.).truths['support'] is True

def test_no_extension_is_retained_as_unknown_not_reweighted():
    fm=make_staged_family(np.random.default_rng(2));c=fm.configs[1]
    fm.configs[1]=c.at_stage('N0')
    r=o.evaluate_family_staged(fm,None,80.,400.)
    assert r.per_config[101]['stage']=='N0' and r.truths['support']==UNKNOWN
    assert r.evidence['matched']['prior']==[1/3]*3
