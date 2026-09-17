# -*- coding: utf-8 -*-
"""Candidate preflight for the CURRENT first-wave FamilyInput interface.
Structural checks are required in smoke and official; registered sizes/versions
are official-only. Explicit environment snapshots are for pure gate tests and
are labelled as such. require_official samples the live environment itself.
This is NOT covariance generation/PSD verification or scientific-label release.
Checks are point-in-time: callers must not mutate an accepted input afterward.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, field, replace
from typing import Dict, List, Optional
from pathlib import Path
import copy
import platform
import numpy as np
from .errors import InputContractError
from .rules_config import RULES, BINDING
from .orchestrator import FamilyInput, ConfigBank, _check_systems
from .bootstrap_plan import FittingPlan
from .production import validate_grid_identity
from .grid_manifest import SIZE_CODES
from .density import check_bank
from .twelve_eval import _same_evaluation_plan, _same_fit_plan

EXPECTED_VERS = dict(python="3.13.15", numpy="2.1.3", scipy="1.16.3", healpy="1.20.0", camb="2.0.4", pot="0.9.7.post1")
N_FIT, M_FIT, B_KDE = 200_000, 100, 2000


def current_env() -> dict:
    import scipy
    v = dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__)
    import importlib
    for key, module in (("healpy", "healpy"), ("camb", "camb"), ("pot", "ot")):
        try: v[key] = importlib.import_module(module).__version__
        except Exception: v[key] = None
    try:
        import threadpoolctl
        numpy_home = Path(np.__file__).resolve().parent
        numpy_roots = (numpy_home, numpy_home.parent / 'numpy.libs')
        pools=[]
        for i in threadpoolctl.threadpool_info():
            if i.get('user_api') != 'blas': continue
            p=Path(i['filepath']).resolve()
            owner='numpy' if any(p.is_relative_to(r) for r in numpy_roots) else 'other'
            pools.append(dict(api='blas', n=i['num_threads'], owner=owner,
                              lib=i.get('internal_api'), filepath=str(p), version=i.get('version')))
        v['blas_threads']=pools
    except Exception: v['blas_threads']=None
    return v


@dataclass
class GateRecord:
    mode: str
    passed: bool
    required_failures: List[str]
    diagnostics: Dict[str, object] = field(default_factory=dict)
    def as_dict(self): return asdict(self)


def _integer(v):
    return isinstance(v,(int,np.integer)) and not isinstance(v,(bool,np.bool_))


def _blas_check(bt):
    """The NumPy-owned OpenBLAS pool is 2; every other BLAS pool is 1 or 2.
    No 'any pool has 2' substitute. Unknown ownership fails official closed.
    """
    if not isinstance(bt,(list,tuple)) or not bt: return False
    for i in bt:
        if (not isinstance(i,dict) or i.get('api')!='blas' or not _integer(i.get('n'))
                or not 1 <= i['n'] <= 2): return False
    numpy_pools=[i for i in bt if i.get('owner')=='numpy']
    return bool(numpy_pools) and all(i['n']==2 and i.get('lib')=='openblas' for i in numpy_pools)


def _profile_checks(fam, label):
    """Return explicit check records, not human-message substring policies."""
    checks=[]
    def add(code,passed,message,official_only=False):
        checks.append(dict(code=label+'/'+code,passed=bool(passed),message=message,
                           required_modes=['official'] if official_only else ['smoke','official']))
    if not isinstance(fam,FamilyInput): raise InputContractError(label+': FamilyInput required')
    fam.validate()
    for c in fam.configs:
        if not isinstance(c,ConfigBank): raise InputContractError(label+': ConfigBank required')
        if not _integer(c.m) or c.m<=0: raise InputContractError('cluster m must be a positive integer')
        # Re-run the construction contract without mutating the supplied object.
        replace(c)
        for a in (c.T1_model,c.T2_model,c.T1_ref,c.T2_ref):
            x=np.asarray(a)
            if x.ndim!=1 or not np.all(np.isfinite(x)):
                raise InputContractError(f'{label}/{c.evaluation_id}: T arrays must be finite 1-D vectors')
        if len(set(c.cluster_uids))!=len(c.cluster_uids):
            raise InputContractError('evaluation bank has duplicate cluster UID')
        for batch,(start,end) in c.batches.items():
            if not _integer(start) or not _integer(end): raise InputContractError('integer batch bounds required')
            uids=c.cluster_uids[start//c.m:end//c.m]
            for plan in fam.plans.values():
                if batch not in plan.strata or plan.strata[batch]!=uids:
                    raise InputContractError(f'{label}/{c.evaluation_id}: bank/plan stratum UID inventory/order mismatch')
        add(f'{c.evaluation_id}/m',c.m==RULES.m,f'{label}/{c.evaluation_id}: m={c.m} != registered {RULES.m}',True)
        add(f'{c.evaluation_id}/N0',c.N0==RULES.N0,f'{label}/{c.evaluation_id}: N0={c.N0} != registered {RULES.N0}',True)
        N=len(c.T1_model)
        add(f'{c.evaluation_id}/N',N in (RULES.N0,RULES.N_max),f'{label}/{c.evaluation_id}: N={N} not registered',True)
    for s,p in fam.plans.items():
        add(f'B/{s}',p.replicates==RULES.B,f'{label}: plan seed {s} B={p.replicates} != registered {RULES.B}',True)
    for e,fb in fam.fitting.items():
        for X in (fb.X_model,fb.X_ref): check_bank(X,fb.cid)
        cid=np.asarray(fb.cid)
        if len(cid)==0: raise InputContractError('fitting bank is empty')
        labels,counts=np.unique(cid,return_counts=True)
        if not np.array_equal(labels,np.arange(fb.K)) or not np.all(counts==counts[0]):
            raise InputContractError(f'{label}/{e}: fitting cluster populations must be equal and all labels present')
        add(f'N_fit/{e}',len(cid)==N_FIT and np.all(counts==M_FIT),
            f'{label}/{e}: fitting bank N_fit={len(cid)} and m_fit={int(counts[0])} not registered',True)
    add('fitting_bound',getattr(fam,'fitting_plan_binding','')=='bound',f'{label}: fitting plans not bound to banks')
    for s,p in fam.fit_plans.items():
        add(f'fitting_type/{s}',isinstance(p,FittingPlan),f'{label}: fitting plan type is not FittingPlan')
        rows=np.asarray(p.multiplicities if isinstance(p,FittingPlan) else p).shape[0]
        add(f'B_KDE/{s}',rows==B_KDE,f'{label}: fitting plan seed {s} B_KDE={rows} != registered {B_KDE}',True)
    gi=fam.grid_identity
    add('grid_identity',gi is not None,f'{label}: grid identity missing (production wrapper required)')
    if gi is not None:
        validate_grid_identity(gi,fam.family,fam.configs[0].system,[c.evaluation_id for c in fam.configs],prior=[c.weight for c in fam.configs])
        missing=[c.evaluation_id for c in fam.configs if c.evaluation_id not in gi['cov_bound']]
        add('cov_binding',not missing,f'{label}: covariance metadata not bound for evaluations {missing}')
        add('full_size_scope',set(gi['sizes'])==set(SIZE_CODES),
            f'{label}: conditional size subset is not the registered full-family scope',True)
    return checks


def official_gate(fam_matched: FamilyInput, fam_native: Optional[FamilyInput], mode='official', env=None) -> GateRecord:
    if mode not in ('official','smoke'): raise InputContractError("mode must be 'official' or 'smoke'")
    if not isinstance(fam_matched,FamilyInput) or (fam_native is not None and not isinstance(fam_native,FamilyInput)):
        raise InputContractError('FamilyInput types required')
    # Same role/conditioning contract as the consumer. Preserve the gate API:
    # a valid but mismatched pair is a named required failure, not a lost diagnostic.
    pair_error = None
    try: _check_systems(fam_matched,fam_native)
    except InputContractError as exc: pair_error = str(exc)
    supplied=env is not None
    if supplied and not isinstance(env,dict): raise InputContractError('env snapshot must be a dictionary')
    snapshot=copy.deepcopy(current_env() if env is None else env)
    checks=_profile_checks(fam_matched,'matched')
    checks.append(dict(code='system_conditioning', passed=pair_error is None,
                       message='matched/native conditioning or role contract: '+str(pair_error),
                       required_modes=['smoke','official']))
    if fam_native is not None:
        checks+=_profile_checks(fam_native,'native')
        # Shared latent group requires the same resampling content across systems.
        for s in range(RULES.seeds):
            if not _same_evaluation_plan(fam_matched.plans[s],fam_native.plans[s]):
                raise InputContractError('matched/native evaluation plans differ (paired CRN required)')
            if not _same_fit_plan(fam_matched.fit_plans[s],fam_native.fit_plans[s]):
                raise InputContractError('matched/native fitting plans differ (paired CRN required)')
    # Native may remain optional in legacy smoke; official always requires it.
    checks.append(dict(code='native_present',passed=fam_native is not None,message='native input missing (strong predicate requires both systems)',required_modes=['official']))
    vers={k:(snapshot.get(k),v) for k,v in EXPECTED_VERS.items() if snapshot.get(k)!=v}
    threads_ok=_blas_check(snapshot.get('blas_threads'))
    profile_failures=[x['message'] for x in checks if not x['passed']]
    checks.extend([
        dict(code='environment_versions',passed=not vers,message=f'environment versions differ from the registered lock: {vers}',required_modes=['official']),
        dict(code='BLAS_threads',passed=threads_ok,message='BLAS threads: NumPy-owned OpenBLAS must be 2; others must be 1..2',required_modes=['official'])])
    failures=[x['message'] for x in checks if not x['passed'] and mode in x['required_modes']]
    diag=dict(env=snapshot,environment_source='injected_test_snapshot' if supplied else 'live_collected',
              rules_binding=copy.deepcopy(BINDING),registered=dict(N0=RULES.N0,N_max=RULES.N_max,m=RULES.m,B=RULES.B,seeds=RULES.seeds,N_fit=N_FIT,m_fit=M_FIT,B_KDE=B_KDE,versions=copy.deepcopy(EXPECTED_VERS)),
              profile_failures=profile_failures,version_mismatch=vers,blas_threads_ok=threads_ok,checks=checks,
              scope='first-wave family input/profile preflight only; not covariance PSD, final calibration, or label release')
    return GateRecord(mode,not failures,failures,diag)


def require_official(fam_matched, fam_native, env=None) -> GateRecord:
    if env is not None:
        raise InputContractError('require_official does not authorize a supplied env snapshot; use official_gate(env=...) for pure tests')
    g=official_gate(fam_matched,fam_native,'official')
    if not g.passed: raise InputContractError('official gate failed: '+'; '.join(g.required_failures[:5]))
    return g
