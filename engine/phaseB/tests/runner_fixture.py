"""Finite test-only first-wave inputs. No CMB covariance or POT calculation.
Actual production builder, SharedNullAsset and W2Context factories are used.
Retained raw W2 records are saved in the normal fixture, and can be detached
into hash-only references for repeated contract tests, as W2Context permits.
"""
import os,sys,copy
from pathlib import Path
import numpy as np
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from step1_engine.grid_registry import load_registry
from step1_engine.production import production_manifest,build_family_input
from step1_engine.w2_shared import build_shared_null
from step1_engine.w2_context import build_w2_context
from step1_engine.positions import PositionBank
from test_b2_tranche20 import synthetic_supplies,A6,A7
from shared_fixture import make_banks,pair,cheap_dist,M,SEED,WHITE

def family_cases(reg,man,family='E7',K=150,Kf=300):
    sm,ep,fp=synthetic_supplies(man,family,'matched',K=K,Kf=Kf)
    sn,_,_=synthetic_supplies(man,family,'native',K=K,Kf=Kf)
    d={}
    for i,size in enumerate(reg.surviving[family],1):
        sel=lambda supplies:[x for x in supplies if x.config_id//100%100==i]
        fm=build_family_input(reg,man,family,'matched',sel(sm),ep,fp,size_ids=[size])
        fn=build_family_input(reg,man,family,'native',sel(sn),ep,fp,size_ids=[size])
        d[f'{family}/{size}']=(fm,fn,{c.evaluation_id:j+1 for j,c in enumerate(fm.configs)})
    return d

def build_fixture():
    reg=load_registry(A7,A6);man=production_manifest(reg);cases=family_cases(reg,man)
    pos,iso=make_banks();iso32=pair(iso,(1e-6,2e-6))
    template=np.random.default_rng(781).normal(size=(M,2))
    neg=[PositionBank(j+1,np.tile(template,(60,1))+[.003*j,0.],np.repeat(np.arange(60),M),M) for j in range(3)]
    asset=build_shared_null(iso,M,SEED,cheap_dist,iso32,WHITE)
    inputs={}
    for i,size in enumerate(reg.surviving['E7']):
        ps=copy.deepcopy(pos if i==0 else neg)
        inputs[f'E7/{size}']=dict(positions=ps,positions_f32=[pair(p,(1e-6,0.)) for p in ps])
    ctx=build_w2_context(asset,inputs,M,SEED,cheap_dist,WHITE,asset.sha256)
    return dict(reg=reg,man=man,cases=cases,ctx=ctx,asset=asset,w2_inputs=inputs)
