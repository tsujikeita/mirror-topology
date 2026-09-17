"""Tranche21 audit: current official_gate only, no new imaginary APIs.
Small cases use the submitted fixture. Official-shape cases use real N/m/B and
real BootstrapPlan.build arrays with an INJECTED environment snapshot. They
are predicate tests, NOT an official experiment or live-environment acceptance.
All bad variants differ from an accepted input in explicitly identified fields.
"""
import os,sys,copy
from pathlib import Path
from dataclasses import replace
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]));sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from step1_engine import official_gate as g
from step1_engine.errors import InputContractError
from step1_engine.bootstrap_plan import BootstrapPlan,FittingPlan,bank_sha256
from step1_engine.production import build_family_input
from step1_engine.orchestrator import FittingBank
from test_b2_tranche21 import build_pair
from gate_fixture import build_registered_shape

@pytest.fixture(scope='module')
def small():return build_pair()
@pytest.fixture(scope='module')
def full():return build_registered_shape()

def assert_rejected(call):
    try: out=call()
    except InputContractError: return
    assert out.passed is False, 'gate accepted a contract-violating input'

def smoke(a,b):return g.official_gate(a,b,'smoke',env={})

def test_normal_small_smoke_is_allowed(small):
    _,_,fm,fn,*_=small; out=smoke(fm,fn)
    assert out.passed and out.diagnostics['profile_failures']

def test_small_official_is_rejected(small):
    _,_,fm,fn,*_=small
    assert_rejected(lambda:g.official_gate(fm,fn,'official',env=dict(g.EXPECTED_VERS,blas_threads=[dict(api='blas',owner='numpy',lib='openblas',n=2)])))

@pytest.mark.parametrize('case',['same_object','swapped','conditioning'])
def test_smoke_rejects_wrong_system_contract(small,case):
    reg,man,fm,fn,sm,ep,fp=small
    a,b=fm,fn
    if case=='same_object':b=fm
    elif case=='swapped':a,b=fn,fm
    else:a=build_family_input(reg,man,'E7','matched',sm[:3],ep,fp,size_ids=['L1.00'])
    assert_rejected(lambda:smoke(a,b))

@pytest.mark.parametrize('case',['bank_uid','native_eval_plan','native_fit_plan'])
def test_smoke_rejects_crn_contract(small,case):
    _,_,fm,fn,_,ep,fp=small
    a,b=fm,fn
    if case=='bank_uid':
        u=[replace(x,crn_group_id=98) for x in ep[0].strata[0]]
        ps={s:BootstrapPlan.build(f'foreign-{s}',s,{0:u},ep[s].replicates,90912) for s in range(5)}
        a=replace(fm,plans=ps)
    elif case=='native_eval_plan':
        ps={s:BootstrapPlan.build(ep[s].plan_id,s,ep[s].strata,ep[s].replicates,90912) for s in range(5)}
        b=replace(fn,plans=ps)
    else:
        ps={s:FittingPlan.build(fp[s].plan_id,fp[s].wave_id,fp[s].crn_group_id,s,fp[s].K,fp[s].multiplicities.shape[0],90912) for s in range(5)}
        b=replace(fn,fit_plans=ps)
    assert_rejected(lambda:smoke(a,b))

@pytest.mark.parametrize('case',['nan_T','short_T'])
def test_smoke_revalidates_consumed_T_arrays(small,case):
    _,_,fm,fn,*_=small;c=copy.copy(fm.configs[0])
    if case=='nan_T':c.T2_ref=c.T2_ref.copy();c.T2_ref[0]=np.nan
    else:c.T2_ref=c.T2_ref[:-1]
    assert_rejected(lambda:smoke(replace(fm,configs=[c]+fm.configs[1:]),fn))

def test_equivalent_plan_copies_are_accepted(small):
    _,_,fm,fn,*_=small
    b=replace(fn,plans=copy.deepcopy(fn.plans),fit_plans=copy.deepcopy(fn.fit_plans))
    assert smoke(fm,b).passed

def test_missing_covariance_binding_is_rejected(small):
    _,_,fm,fn,*_=small;gi=copy.deepcopy(fm.grid_identity);gi['cov_bound'].pop(next(iter(gi['cov_bound'])))
    assert_rejected(lambda:smoke(replace(fm,grid_identity=gi),fn))

def test_normal_registered_dimensions_pure_gate(full):
    # Explicitly inject versions; no claim that this sandbox is registered.
    out=g.official_gate(full['fm'],full['fn'],'official',env=full['env'])
    assert out.passed and not out.required_failures

@pytest.mark.parametrize('case',['same_object','swapped'])
def test_official_role_checks_with_registered_dimensions(full,case):
    fm,fn=full['fm'],full['fn']
    a,b=(fm,fm) if case=='same_object' else (fn,fm)
    assert_rejected(lambda:g.official_gate(a,b,'official',env=full['env']))

def test_conditional_subset_does_not_become_full_official(full):
    r,man=full['registry'],full['manifest'];ps,fs=full['evaluation_plans'],full['fitting_plans']
    fm=build_family_input(r,man,'E1','matched',full['supplies']['matched'][:1],ps,fs,size_ids=['L1.00'])
    fn=build_family_input(r,man,'E1','native',full['supplies']['native'][:1],ps,fs,size_ids=['L1.00'])
    assert_rejected(lambda:g.official_gate(fm,fn,'official',env=full['env']))

def test_fitting_population_not_just_average(full):
    fm,fn=full['fm'],full['fn'];eid=fn.configs[0].evaluation_id;f=fn.fitting[eid]
    cid=f.cid.copy();cid[:99]=1
    assert np.bincount(cid)[:3].tolist()==[1,199,100]
    bad=FittingBank(f.X_model,f.X_ref,cid);fts=dict(fn.fitting);fts[eid]=bad;bs=dict(fn.fitting_bindings);bs[eid]=bank_sha256(bad.X_model,bad.X_ref,bad.cid)
    assert_rejected(lambda:g.official_gate(fm,replace(fn,fitting=fts,fitting_bindings=bs),'official',env=full['env']))

@pytest.mark.parametrize('case',['missing_camb','wrong_camb','numpy_pool_one','negative_pool','float_thread_count','wrong_api'])
def test_registered_environment_constraints(full,case):
    env=copy.deepcopy(full['env'])
    if case=='missing_camb':env.pop('camb',None)
    elif case=='wrong_camb':env['camb']='9.9'
    elif case=='numpy_pool_one':env['blas_threads']=[dict(api='blas',owner='numpy',lib='openblas',n=1),dict(api='blas',owner='scipy',lib='openblas',n=2)]
    elif case=='negative_pool':env['blas_threads'].append(dict(api='blas',owner='scipy',lib='openblas',n=-1))
    elif case=='float_thread_count':env['blas_threads'][0]['n']=2.0
    else:env['blas_threads'][0]['api']='openmp'
    assert_rejected(lambda:g.official_gate(full['fm'],full['fn'],'official',env=env))

def test_require_official_does_not_authorize_injected_environment(full):
    # Pure evaluation can take a snapshot; a live official authorizer must not
    # silently treat caller-supplied version strings as measurements.
    assert_rejected(lambda:g.require_official(full['fm'],full['fn'],env=full['env']))

def test_native_missing_official_rejected(full):
    assert_rejected(lambda:g.official_gate(full['fm'],None,'official',env=full['env']))

def test_live_environment_mismatch_does_not_pass(full):
    # On a genuine locked environment this test may pass and is not a defect.
    actual=g.current_env()
    if all(actual.get(k)==v for k,v in g.EXPECTED_VERS.items()):pytest.skip('live versions happen to match; mismatch case unavailable')
    assert_rejected(lambda:g.official_gate(full['fm'],full['fn'],'official'))
