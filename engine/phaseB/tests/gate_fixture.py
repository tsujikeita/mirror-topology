"""Actual registered array sizes and genuinely generated plans, synthetic T only.
This tests official_gate with an INJECTED lock snapshot. It is NOT an official
engine run, physical-bank validation, statistical test, or live-env certification.
No scan, covariance or OT is performed. No rules constants are monkeypatched.
"""
from pathlib import Path
from dataclasses import replace
import os,sys,json,copy,time,gc
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]));sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import numpy as np
from step1_engine import official_gate as g
from step1_engine.grid_registry import load_registry
from step1_engine.production import production_manifest,build_family_input,BankSupply
from step1_engine.orchestrator import FittingBank
from step1_engine.bootstrap_plan import BootstrapPlan,FittingPlan,bank_sha256
from step1_engine.types import ClusterUID
from test_b2_tranche20 import A6,A7

def build_registered_shape():
 start=time.time()
 r=load_registry(A7,A6);man=production_manifest(r);K,m,B=10000,100,2000;Kf,mf=2000,100
 uid=[ClusterUID(1,200,31,0,i) for i in range(K)]
 ep={}
 for s in range(5):
  ep[s]=BootstrapPlan.build(f'gate-E1-{s}',s,{0:uid},B,882211)
 
 fp={s:FittingPlan.build(f'gate-fit-{s}',1,41,s,Kf,B,882212) for s in range(5)}
 z=np.random.default_rng(882213).standard_normal((K*m,2));zf=np.random.default_rng(882214).standard_normal((Kf*mf,2));cid=np.repeat(np.arange(Kf),mf)
 specs=[c for c in man.configurations if c.family=='E1'];sup={};families={}
 for system in ['matched','native']:
  arr=[];scale=1. if system=='matched' else .9
  for j,c in enumerate(specs):
   a=(z-[.5+.05*j,.4])*[40.,200.]+[120.,600.];ref=z*[40.,200.]*scale+[120.,600.]
   fit=FittingBank((zf-[.5+.05*j,.4])*[40.,200.]+[120.,600.],zf*[40.,200.]*scale+[120.,600.],cid)
   cm=dict(manifest=dict(topology=c.family,params=c.shape_params,x0=c.x0_CT),cov_array_sha256='a'*64,cov_file_sha256='b'*64)
   arr.append(BankSupply(c.config_id,system,a[:,0],a[:,1],ref[:,0],ref[:,1],uid,m,{0:(0,K*m)},fit,cm))
  sup[system]=arr;families[system]=build_family_input(r,man,'E1',system,arr,ep,fp)
 fm,fn=families['matched'],families['native']
 lock=dict(g.EXPECTED_VERS,camb='2.0.4',blas_threads=[dict(api='blas',owner='numpy',lib='openblas',file='/example/numpy.libs/libscipy_openblas64_.so',n=2)])
 return dict(registry=r,manifest=man,fm=fm,fn=fn,supplies=sup,evaluation_plans=ep,fitting_plans=fp,env=lock,seconds=time.time()-start)
