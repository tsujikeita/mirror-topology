"""Independent B-3-1 v0.2 review. Synthetic arrays and in-memory faults only.
No Colab/physical input replay. Failed assertions are requested acceptance contracts.
"""
from __future__ import annotations
import ast,copy,dataclasses,hashlib,json,os,time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import pytest
from scipy.stats import gaussian_kde

import tempfile, sys
P=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1])); ROOT=Path(os.environ.get('REVIEW_ROOT',tempfile.mkdtemp(prefix='b31v02_'))); E=Path(os.environ.get('REVIEW_EVIDENCE', str(ROOT/'evidence'))); E.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(P))
from step1_engine import controls as c, bootstrap_plan as bp, orchestrator as orch
from step1_engine.types import ClusterUID
from step1_engine.decision import CoreInputs,decide_core
from step1_engine.truth import UNKNOWN,TECH
from step1_engine.errors import InputContractError
RESULTS={}
def emit(k,v):
    RESULTS[k]=v
    (E/'acceptance_probes.json').write_text(json.dumps(RESULTS,indent=2,ensure_ascii=False,default=lambda x:x.item() if isinstance(x,np.generic) else str(x)))

@pytest.fixture(scope='module')
def probe():
    K,m,B=600,10,80
    uM=[ClusterUID(1,500,2,0,i) for i in range(K)];uI=[ClusterUID(1,200,1,0,i) for i in range(K)]
    pM={s:bp.BootstrapPlan.build(f'm{s}',s,{0:uM},B,20260912) for s in range(5)};pI={s:bp.BootstrapPlan.build(f'i{s}',s,{0:uI},B,20260912) for s in range(5)}
    def bank(h):
        x=np.where((np.arange(m)[None,:]<np.asarray(h)[:,None]).ravel(),-1.,1.);return dict(T1=x,T2=x.copy())
    M=bank(np.full(K,8));I=bank(np.arange(K)%2)
    rg=np.random.default_rng(7401);KF,mf=500,4
    XM=rg.normal(0,.5,(KF*mf,2));XI=rg.normal(0,1.8,(KF*mf,2));fitM=dict(T1=XM[:,0],T2=XM[:,1]);fitI=dict(T1=XI[:,0],T2=XI[:,1]);cid=np.repeat(np.arange(KF),mf)
    fM={s:bp.FittingPlan.build(f'fm{s}',1,2,s,KF,40,20260913) for s in range(5)};fI={s:bp.FittingPlan.build(f'fi{s}',1,1,s,KF,40,20260913) for s in range(5)}
    args=(M,I,uM,uI,pM,pI,m,fitM,fitI,cid,cid,fM,fI,0.,0.)
    good=c.negative_decision(*args)
    cfg=orch.ConfigBank(100,'E7','matched',1.,M['T1'],M['T2'],I['T1'],I['T2'],uI,m,{0:(0,K*m)})
    return SimpleNamespace(**locals())

def test_original_controls_compile_and_registered_positive_definition():
    src=(P/'b3/b3_1_control.py').read_text();compile(src,'submitted','exec')
    compile((P/'step1_engine/controls.py').read_text(),'controls','exec')
    pins=json.loads((P/'b3/b3_1_pins.json').read_text())
    assert pins['controls']['positive_registered']['boost']=={'T1':.35,'T2':.35}
    assert pins['controls']['positive_mock_diagnostic']['boost']=={'T1':.6,'T2':.6}
    assert pins['controls']['negative']['n_pseudo']==200
    assert 'boosted_family("pos", 300, "matched", er' in src
    assert 'results["positive_registered"] = r_pos' in src

def test_independent_evaluation_literal_from_saved_keys(probe):
    p=probe;hm=np.full(p.K,8);hi=np.arange(p.K)%2
    maxdiff=0.
    for s in range(5):
        ci,PM,PI=c.independent_Q_ci(hm,hi,p.pM[s],p.pI[s],p.K*p.m,p.K*p.m,p.m,p.uM,p.uI,s)
        def replay(plan,h):
            idx=np.random.default_rng(np.random.SeedSequence(plan.rng_keys[0])).integers(0,p.K,(p.B,p.K))
            return np.array([sum(map(int,h[row])) for row in idx])/(p.K*p.m)
        rm,ri=replay(p.pM[s],hm),replay(p.pI[s],hi)
        assert np.array_equal(PM,rm) and np.array_equal(PI,ri)
        ends=np.exp(np.quantile(np.log(rm)-np.log(ri),[.025,.975]));maxdiff=max(maxdiff,float(np.max(np.abs(ends-[ci.lower,ci.upper]))))
        assert np.allclose(ends,[ci.lower,ci.upper],atol=1e-13,rtol=0)
    emit('independent_Q_literal',dict(seeds=5,integer_probability_arrays='exact',max_CI_diff=maxdiff))

def test_negative_density_ci_matches_independent_literal_fitting(probe):
    p=probe; vals=[]
    for i in range(40):
        xx=np.repeat(p.XM,p.fM[0].multiplicities[i][p.cid],axis=0)
        yy=np.repeat(p.XI,p.fI[0].multiplicities[i][p.cid],axis=0)
        vals.append(float(gaussian_kde(xx.T,bw_method='scott').logpdf([0.,0.])[0]-gaussian_kde(yy.T,bw_method='scott').logpdf([0.,0.])[0]))
    ends=np.quantile(vals,[.025,.975]);saved=np.array([p.good['logD_ci']['log_lower'],p.good['logD_ci']['log_upper']])
    diff=float(np.max(np.abs(ends-saved)));emit('independent_fitting_literal',dict(reference_endpoints=ends.tolist(),submitted_endpoints=saved.tolist(),max_abs_diff=diff))
    assert diff<1e-11
    assert p.good['truths']['support'] is True and p.good['gate'] is False and p.good['technical_status']=='ok'

def test_same_evaluation_group_is_rejected(probe):
    p=probe;h=np.arange(p.K)%2
    with pytest.raises(InputContractError):c.independent_Q_ci(h,h,p.pM[0],p.pM[0],p.K*p.m,p.K*p.m,p.m,p.uM,p.uM,0)

@pytest.mark.parametrize('extra,expect',[(False,True),(UNKNOWN,True),(TECH,False)])
def test_rate_primitive_counts_unknown_and_technical(extra,expect):
    r=c.negative_rate_check([False]*199+[extra]); assert r['ok'] is expect
    if extra==TECH:assert r['technical']==1

def rate_loop(real_record):
    """Run the exact submitted script's loop and its final aggregation on 200 fixture rows."""
    src=(P/'b3/b3_1_control.py').read_text();tree=ast.parse(src)
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    body=next(n for n in main.body if isinstance(n,ast.Try)).body
    pos=next(i for i,n in enumerate(body) if isinstance(n,ast.For) and ast.unparse(n.iter)=='range(n_neg)')
    selected=[body[pos]]
    for n in body[pos+1:]:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='bt' for t in n.targets):break
        selected.append(n)
    rows=[copy.deepcopy(real_record) for _ in range(200)]
    for r in rows[1:]:r['truths']={'support':False,'strong':False,'unsupported':False};r['technical_status']='ok'
    it=iter(rows)
    ns=dict(TECH=TECH,time=time,tt=time.time(),n_neg=200,pt=dict(T1=np.zeros(200),T2=np.zeros(200)),R={'timings':{}},G={},neg_truths=[],neg_rows=[],negative_decision=lambda *a:next(it),negative_rate_check=c.negative_rate_check)
    for n in ('ng','er','uidsN','uids','plansN','plans','m','nf','fr','cidnf','cidf','fplansN','fplans'):ns[n]=None
    exec(compile(ast.fix_missing_locations(ast.Module(body=selected,type_ignores=[])),'submitted_negative_rate_loop','exec'),ns)
    return ns

def test_normal_highQ_density_branch_rate_loop_is_usable(probe):
    ns=rate_loop(probe.good);r=ns['R']['negative_rate'];emit('healthy_rate_loop',{k:v for k,v in r.items() if k!='rows'})
    assert ns['G']['G_negative_support_rate'] and r['c_true']==1 and r['technical']==0

def test_rate_loop_must_reject_density_ci_technical_failure(probe):
    actual=c.kde_logpdf_replicates; calls=0
    def fault(*a,**kw):
        nonlocal calls
        out=actual(*a,**kw);calls+=1
        if calls==1:out[0,0]=np.nan
        return out
    with patch.object(c,'kde_logpdf_replicates',fault):r=c.negative_decision(*probe.args)
    assert r['technical_status']==TECH and r['truths']['support'] is True and r['logD_ci']['math_state']==TECH
    ns=rate_loop(r);rate=ns['R']['negative_rate'];emit('rate_lost_technical_failure',dict(record=r,aggregate={k:v for k,v in rate.items() if k!='rows'},gate=ns['G']['G_negative_support_rate'],technical_rows=sum(x['technical']!= 'ok' for x in rate['rows'])))
    assert ns['G']['G_negative_support_rate'] is False, 'A recorded technical failure was converted to a counted support and the control rate passed'

Q=dict(L_Q=19.,U_Q=21.,logD_point=2.1,L_logD=1.5,U_logD=2.7,L_Qn=10.,U_Qn=12.)
def test_normal_conjunct_cases_all_definite_false():
    out=c.conjunct_battery(Q);emit('normal_conjunct',out)
    assert out['ok'] and set(out['registered']['strong_drops'].values())=={'False'} and set(out['registered']['support_drops'].values())=={'False'}

@pytest.mark.parametrize('replace_with',[UNKNOWN,TECH])
def test_conjunct_battery_must_reject_unknown_or_tech_for_expected_false(replace_with):
    real=decide_core
    def defective(x):
        d=real(x)
        return dataclasses.replace(d,support_truth=replace_with if d.support_truth is False else d.support_truth,strong_truth=replace_with if d.strong_truth is False else d.strong_truth,technical_status=TECH if replace_with==TECH and (d.support_truth is False or d.strong_truth is False) else d.technical_status)
    with patch.object(c,'decide_core',defective):out=c.conjunct_battery(Q)
    emit('conjunct_bad_false_'+replace_with,out)
    assert out['ok'] is False, f'Expected-False tests accepted {replace_with}'

def test_real_hit_vector_and_zero_permutation_detection(probe):
    p=probe;thr=[(0.,0.),(1.,1.)]
    good=c.bruteforce_check(p.cfg,thr,p.pI[0]);det=c.bruteforce_detector_selftest(p.cfg,thr,p.pI[0]);emit('normal_hit_path',dict(good=good,detector=det))
    assert good['ok'] and det['ok']

def test_bruteforce_must_detect_bad_actual_resampling(probe):
    p=probe;calls=0
    def bad(plan,tables,weights_by_batch=None):
        nonlocal calls
        calls+=1;return np.zeros(plan.replicates),{b:np.zeros(plan.replicates,dtype=np.int64) for b in tables}
    tabs=p.cfg.hit_tables(0.,0.,'model')
    expected_raw=int(np.sum(tabs[0].hits))
    with patch.object(bp,'resample_hits',bad),patch.object(orch,'resample_hits',bad),patch.object(c,'resample_hits',bad):
        actual=orch.resample_hits(p.pI[0],tabs);calls=0
        out=c.bruteforce_check(p.cfg,[(0.,0.)],p.pI[0]);calls_in_check=calls
    emit('bad_resampling_not_detected',dict(raw_hits=expected_raw,bad_probabilities=actual[0].tolist(),gate=out,calls_of_actual_resampler=calls_in_check))
    assert out['ok'] is False, 'The actual resampler is broken but the check calls only the literal resampler on both sides'

def test_bruteforce_must_not_accept_missing_resampling_coverage(probe):
    p=probe;short=p.uI[:20];wrong=bp.BootstrapPlan.build('wrong-size',0,{0:short},20,9)
    try:out=c.bruteforce_check(p.cfg,[(0.,0.)],wrong)
    except InputContractError:return
    emit('missing_resampling_coverage',out)
    assert out['ok'] is False, 'A plan with the wrong cluster count silently skips comparison and passes'
