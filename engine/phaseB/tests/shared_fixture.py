"""Small finite synthetic pools; mean-distance is TEST-ONLY, not exact W2."""
import os,sys,copy
from pathlib import Path
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]));sys.path.insert(0,str(ROOT))
import numpy as np
from step1_engine.positions import PositionBank
from step1_engine.w2_shared import build_shared_null,w2_trigger_shared
SEED=20260914; M=100; WHITE={'source':'synthetic whitening; already transformed coordinates'}
def cheap_dist(a,b):return float(np.max(np.abs(a.mean(axis=0)-b.mean(axis=0))))
def make_banks():
 rng=np.random.default_rng(11)
 pos=[PositionBank(i+1,rng.standard_normal((6000,2))+s,np.repeat(np.arange(60),100)) for i,s in enumerate((0.,0.,.8))]
 iso=PositionBank(0,rng.standard_normal((18000,2)),np.repeat(np.arange(180),100))
 return pos,iso

def pair(b,delta):
 return PositionBank(b.position_id,b.Tw+np.array(delta),b.cid.copy(),b.m)

def fixture(delta=(1e-6,2e-6)):
 pos,iso=make_banks();ip=pair(iso,delta);pp=[pair(p,(1e-6,0.)) for p in pos]
 a=build_shared_null(iso,M,SEED,cheap_dist,ip,WHITE)
 r=w2_trigger_shared(pos,a,M,SEED,cheap_dist,case_id='E7/L1.00',whitening_identity=WHITE,positions_f32=pp)
 return pos,iso,ip,pp,a,r
