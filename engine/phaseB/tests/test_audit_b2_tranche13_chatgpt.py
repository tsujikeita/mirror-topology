"""Audit-side tranche13 contracts. Synthetic coordinator records and small grids only.
No CMB bank, exact large OT, or official E2 lattice is used.
"""
import copy,os,sys
from pathlib import Path
from dataclasses import replace
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]));sys.path.insert(0,str(ROOT))
from step1_engine.stage12 import generate_twelve,transition_after_three,StageTransition
from step1_engine.coordinator import plan_family_expansion,family_completion,FamilyExpansionSet
from step1_engine.observers12 import lattice_1d,dist_euclid,dist_torus_halfturn,greedy_maximin,TIE_TOL
from step1_engine.observers12_stream import greedy_maximin_streamed
from step1_engine.errors import InputContractError
from step1_engine import serialization as ser
A=np.array([[.11278702805018147],[.04504442885635738],[.17608175443077442]])
S=['L1.00','L1.20','L1.50']
def source(s,f='E7',tech='ok'):
 return dict(family=f,size_id=s,decision=dict(technical_status=tech),precision=dict(state='pass'),evidence=dict(coverage_ok=True))
def transition(s,m=None,f='E7',state='not-expanded',tech='ok'):
 return transition_after_three(f,s,source(s,f,tech),dict(state=state,expand=state=='position-sensitive'),m)
def r12(s,m):
 return dict(family='E7',size_id=s,evidence=dict(stage='12-position',coverage_ok=True,twelve_manifest_sha256=m.sha256),decision=dict(technical_status='ok'),precision=dict(state='pass'))
@pytest.fixture
def normal():
 mans={s:generate_twelve('E7',s,A) for s in S}
 tr={s:transition(s,mans[s] if i==0 else None,state=['position-sensitive','not-expanded','position-unresolved'][i]) for i,s in enumerate(S)}
 plan=plan_family_expansion('E7',S,tr,mans)
 return plan,{s:r12(s,mans[s]) for s in S},{s:'not-expanded' for s in S},mans,tr

def test_normal_all_surviving_sizes_complete_and_no_label(normal):
 p,r,n,m,t=normal;out=family_completion(p,r,n,m)
 assert out['family_local_completion'] is True
 assert out['final_label_released'] is False and set(out['per_size'])==set(S)
 assert t[S[1]].position_state=='not-expanded' and t[S[2]].position_state=='position-unresolved'

def test_normal_family_plan_json_roundtrip(normal):
 p,r,n,m,_=normal;d=ser.loads(ser.dumps(p.as_dict()));d['transitions']={s:StageTransition(**t) for s,t in d['transitions'].items()}
 out=family_completion(FamilyExpansionSet(**d),r,n,m)
 assert out==family_completion(p,r,n,m)

@pytest.mark.parametrize('which',['source','position'])
def test_e1_exemption_must_not_erase_technical_failure(which):
 tr={s:transition(s,f='E1',tech='technical_fail' if i==1 and which=='source' else 'ok',state='technical_fail' if i==1 and which=='position' else 'not-expanded') for i,s in enumerate(S)}
 p=plan_family_expansion('E1',S,tr)
 assert p.status=='technical_fail' and p.expand_family is False

def test_nonexempt_technical_already_has_priority(normal):
 _,_,_,m,tr=normal;tr[S[1]]=transition(S[1],tech='technical_fail')
 assert plan_family_expansion('E7',S,tr,m).status=='technical_fail'

def test_e1_ordinary_is_exempt():
 tr={s:transition(s,f='E1') for s in S};p=plan_family_expansion('E1',S,tr)
 assert p.status=='exempt (observer-homogeneous)' and not p.expand_family

@pytest.mark.parametrize('field,value',[('family','E8'),('expand_family','False'),('status','technical_fail')])
def test_completion_validates_reconstructed_plan(normal,field,value):
 p,r,n,m,_=normal
 with pytest.raises(InputContractError):family_completion(replace(p,**{field:value}),r,n,m)

def test_completion_rejects_shrunken_size_list_with_original_transition_inventory(normal):
 p,r,n,m,_=normal
 with pytest.raises(InputContractError):family_completion(replace(p,surviving_sizes=S[:1]),{S[0]:r[S[0]]},{S[0]:n[S[0]]},{S[0]:m[S[0]]})

def test_completion_must_not_synthesize_over_position_technical(normal):
 p,r,n,m,_=normal;changed=copy.deepcopy(p);changed.transitions[S[1]]=transition(S[1],state='technical_fail')
 with pytest.raises(InputContractError):family_completion(changed,r,n,m)

def test_caller_transition_mutation_does_not_change_issued_plan(normal):
 p,_,_,_,tr=normal;before=p.as_dict();tr[S[1]].three_position_result_sha256='f'*64
 assert p.as_dict()==before

def test_one_size_precision_unresolved_blocks_family(normal):
 p,r,n,m,_=normal;r[S[1]]['precision']['state']='precision-unresolved'
 assert family_completion(p,r,n,m)['family_local_completion'] is False

def test_one_size_coverage_false_blocks_family(normal):
 p,r,n,m,_=normal;r[S[1]]['evidence']['coverage_ok']=False
 assert family_completion(p,r,n,m)['family_local_completion'] is False

def test_one_size_new_technical_retained(normal):
 p,r,n,m,_=normal;r[S[1]]['decision']['technical_status']='technical_fail'
 out=family_completion(p,r,n,m)
 assert out['family_local_completion'] is False and out['per_size'][S[1]]['new_stage_technical'] is True

def test_missing_completion_result_rejected(normal):
 p,r,n,m,_=normal;del r[S[1]]
 with pytest.raises(InputContractError):family_completion(p,r,n,m)

def test_streamed_tie_is_relative_to_global_maximum():
 ax=lattice_1d(.1,.2,.1);a=np.array([[.15-.75*TIE_TOL/np.sqrt(2)]*2]);grid=np.array([[x,y] for x in ax for y in ax]);d=dist_euclid(grid,a[0])
 expected=np.array([.1,.2]);actual=greedy_maximin_streamed(ax,ax,a,1,.04,dist_euclid,rows_per_block=1)[-1]
 assert np.array_equal(actual,expected)
 assert float(d.max()-dist_euclid(actual[None,:],a[0])[0])<=TIE_TOL

def test_streamed_tie_independent_of_block_size():
 ax=lattice_1d(.1,.2,.1);a=np.array([[.15-.75*TIE_TOL/np.sqrt(2)]*2])
 p1=greedy_maximin_streamed(ax,ax,a,1,.04,dist_euclid,rows_per_block=1)
 p2=greedy_maximin_streamed(ax,ax,a,1,.04,dist_euclid,rows_per_block=2)
 assert np.array_equal(p1,p2)

def test_streamed_ordinary_small_grid_equivalence():
 ax=lattice_1d(0.,1.,.1);a=np.array([[.23,.41],[.78,.15],[.65,.75]]);grid=np.array([[x,y] for x in ax for y in ax])
 expected=greedy_maximin(grid,a,4,.05,dist_euclid)
 for block in [1,3,30]:assert np.array_equal(expected,greedy_maximin_streamed(ax,ax,a,4,.05,dist_euclid,rows_per_block=block))

def test_streamed_rejects_out_of_box_anchor_like_memory_version():
 ax=lattice_1d(.1,.3,.1)
 with pytest.raises(InputContractError):greedy_maximin_streamed(ax,ax,np.array([[1.,1.]]),1,.01,dist_euclid,rows_per_block=1)

@pytest.mark.parametrize('n_add',[-1,True])
def test_streamed_n_add_is_nonnegative_nonbool_integer(n_add):
 ax=lattice_1d(.1,.3,.1)
 with pytest.raises(InputContractError):greedy_maximin_streamed(ax,ax,np.array([[.15,.15]]),n_add,.01,dist_euclid,rows_per_block=1)
