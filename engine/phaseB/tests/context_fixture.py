"""Finite synthetic inputs. Mean distance is TEST-ONLY, never exact POT W2."""
import os,sys
from pathlib import Path
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'tests'))
import numpy as np
from step1_engine.positions import PositionBank
from step1_engine.w2_shared import build_shared_null
from step1_engine.w2_context import build_w2_context
from shared_fixture import make_banks,pair,cheap_dist,M,SEED,WHITE
KEY_A='E7/L1.00'; KEY_B='E7/L1.50'

def make_context_fixture():
    pos,iso=make_banks();iso32=pair(iso,(1e-6,2e-6))
    p32=[pair(p,(1e-6,0)) for p in pos]
    # Repeated finite cluster templates make observed differences stable and small.
    template=np.random.default_rng(781).normal(size=(M,2))
    neg=[PositionBank(j+1,np.tile(template,(60,1))+np.array([.003*j,0.]),np.repeat(np.arange(60),M),M) for j in range(3)]
    neg32=[pair(p,(1e-6,0)) for p in neg]
    asset=build_shared_null(iso,M,SEED,cheap_dist,iso32,WHITE)
    cases={KEY_A:dict(positions=pos,positions_f32=p32),KEY_B:dict(positions=neg,positions_f32=neg32)}
    ctx=build_w2_context(asset,cases,M,SEED,cheap_dist,WHITE,asset.sha256)
    assert ctx.decision_for(KEY_A).trigger is True
    assert ctx.decision_for(KEY_B).trigger is False
    return asset,cases,ctx

def probabilities(ratio=1.25):
    values=[.2,.2*ratio,.2]
    return {i+1:dict(P=p,hits=int(round(p*100)),N=100,precision='pass',stage='N4') for i,p in enumerate(values)}
