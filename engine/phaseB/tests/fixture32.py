"""Synthetic audit inputs; no physical covariance or exact POT.
All W2 decisions are issued by the submitted factories with explicit test-only distance.
No scientific rule or predicate is replaced. Old-position/physical-bank binding is NOT claimed.
"""
import os,sys,copy,pickle
from pathlib import Path
import numpy as np
from dataclasses import replace
R=Path(os.environ.get('AUDIT_WORKDIR', Path(__file__).resolve().parent));ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from runner_fixture import build_fixture,family_cases,M,SEED,cheap_dist,WHITE
from audit_fixture30 import diagnostic_cases
from step1_engine.orchestrator import FamilyInput
from step1_engine.w2_context import build_w2_context
from step1_engine.bootstrap_plan import bank_sha256, BootstrapPlan, FittingPlan
from step1_engine.production import build_family_input
from step1_engine.types import ClusterUID
from test_b2_tranche20 import synthetic_supplies

def base():
    p=R/'base.pkl'
    if p.exists():
        with p.open('rb') as h:return pickle.load(h)
    f=build_fixture();f['ctx'].results={};f['ctx'].validate();return f

def twelve_from_cases(cases):
    """Replicate declared synthetic distribution over twelve positions; unique evaluation IDs and common plans retained."""
    out={};maps={};nmaps={}
    for si,(key,(fm,fn,pmap)) in enumerate(sorted(cases.items()),1):
        fam,size=key.split('/'); pair=[]
        for side,f in enumerate((fm,fn)):
            if f is None:pair.append(None);continue
            cfgs=[];fit={};bind={};mp={}
            for j in range(12):
                src=f.configs[j%len(f.configs)];e=100000+si*1000+side*500+j
                c=replace(copy.deepcopy(src),evaluation_id=e,weight=1/12)
                cfgs.append(c);fit[e]=copy.deepcopy(f.fitting[src.evaluation_id]);bind[e]=bank_sha256(fit[e].X_model,fit[e].X_ref,fit[e].cid);mp[e]=j
            pair.append(FamilyInput(fam,cfgs,f.plans,fit,f.fit_plans,f.coverage_ok,bind))
            (maps if side==0 else nmaps)[size]=mp
        out[size]=tuple(pair)
    return dict(size_inputs=out,position_ids=maps,native_position_ids=(nmaps or None))

def multifamily_trigger_only_pseudo(b):
    """Target (200,1000): all positions precise + ratio<2; pseudo (80,400): E7 ratio>2. Other families have identical-position models."""
    reg,man=b['reg'],b['man'];cases={};specs={}
    for fi,fam in enumerate(reg.surviving,1):
        sm,_,_=synthetic_supplies(man,fam,'matched',K=1500,seed=99200+fi)
        sn,_,_=synthetic_supplies(man,fam,'native',K=1500,seed=99200+fi)
        uids=[ClusterUID(1,200,130+fi,0,k) for k in range(1500)]
        ep={s:BootstrapPlan.build(f'{fam}-audit32-{s}',s,{0:uids},40,99400+fi) for s in range(5)}
        fp={s:FittingPlan.build(f'{fam}-audit32fit-{s}',1,230+fi,s,300,15,99600+fi) for s in range(5)}
        for role,ss in [('matched',sm),('native',sn)]:
            unit=np.array([40,200])*(1 if role=='matched' else .9)
            for q in ss:
                q.cluster_uids=uids;obs=q.config_id%100
                shift=(0.05 if obs==1 else .55) if fam=='E7' else .2
                q.T1_model=q.T1_ref-shift*unit[0];q.T2_model=q.T2_ref-shift*unit[1]
                q.fitting.X_model=q.fitting.X_ref-shift*unit
        for i,s in enumerate(reg.surviving[fam],1):
            p=tuple(build_family_input(reg,man,fam,role,[q for q in ss if q.config_id//100%100==i],ep,fp,size_ids=[s]) for role,ss in [('matched',sm),('native',sn)])
            key=fam+'/'+s;cases[key]=(*p,{c.evaluation_id:j+1 for j,c in enumerate(p[0].configs)})
            if fam!='E1':specs[key]=copy.deepcopy(b['w2_inputs']['E7/L1.50'])
    ctx=build_w2_context(b['asset'],specs,M,SEED,cheap_dist,WHITE,b['asset'].sha256);ctx.results={};ctx.validate()
    return dict(reg=reg,man=man,cases=cases,ctx=ctx)
