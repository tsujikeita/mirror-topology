"""Finite test-only fixtures. No real CMB inputs, no POT, no rule changes.
The deliberately small fitting sample has genuine singular bootstrap replicates;
all base points are finite and the full bank is full rank.
"""
import copy
import numpy as np
from step1_engine.orchestrator import FittingBank
from step1_engine.bootstrap_plan import FittingPlan
from step1_engine.production import build_family_input
from step1_engine.w2_context import build_w2_context
from test_b2_tranche20 import synthetic_supplies
from runner_fixture import M, SEED, cheap_dist, WHITE


def diagnostic_cases(reg, man, all_sizes_need_ci=False):
    sm,ep,_=synthetic_supplies(man,'E7','matched',K=1500,Kf=3)
    sn,_,_=synthetic_supplies(man,'E7','native',K=1500,Kf=3)
    fp={s:FittingPlan.build('diag-fit'+str(s),1,41,s,3,30,314159) for s in range(5)}
    z=np.column_stack([np.tile(np.linspace(-2.,2.,10),3),np.repeat([-1.,0.,1.],10)])
    ref=z*np.array([40.,200.])+np.array([100.,500.]);cid=np.repeat(np.arange(3),10)
    for supplies,scale in [(sm,1.),(sn,.9)]:
        for s in supplies:
            code=s.config_id//100%100
            shift=np.array([1.1,1.0]) if all_sizes_need_ci or code==1 else np.array([.05,.05])
            unit=np.array([40.,200.])*scale
            s.T1_model=s.T1_ref-shift[0]*unit[0];s.T2_model=s.T2_ref-shift[1]*unit[1]
            s.fitting=FittingBank(ref-np.array([4.,20.]),ref,cid)
    cases={}
    for i,size in enumerate(reg.surviving['E7'],1):
        pair=tuple(build_family_input(reg,man,'E7',role,[s for s in sup if s.config_id//100%100==i],ep,fp,size_ids=[size]) for role,sup in [('matched',sm),('native',sn)])
        cases['E7/'+size]=(*pair,{c.evaluation_id:j+1 for j,c in enumerate(pair[0].configs)})
    return cases


def negative_context(base):
    specs={k:copy.deepcopy(base['w2_inputs']['E7/L1.50']) for k in base['cases']}
    ctx=build_w2_context(base['asset'],specs,M,SEED,cheap_dist,WHITE,base['asset'].sha256)
    assert all(d.trigger is False for d in ctx.decisions.values())
    ctx.results={};ctx.validate()
    return ctx
