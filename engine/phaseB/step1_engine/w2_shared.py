# -*- coding: utf-8 -*-
"""Shared maximal W2 null; case-specific stopping and prefix sensitivity bounds.
Audit candidate: validation is structural and conditional on stored numeric evidence,
not a signature or an independent rerun of OT. No scientific thresholds are changed.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Callable, Dict, List, Optional
import copy, hashlib, math, re
import numpy as np
from .errors import InputContractError
from .rules_config import RULES
from .positions import (PositionBank, bank_identity, null_max_sequence, observed_w2max,
                        DISTANCE_KINDS, w2_exact, _check_positions, _kc, _norm_identity)
from .w2_stop import w2_stop, w2_validate, seed_spread
from .truth import UNKNOWN
from . import serialization as ser

RNG_RULE = "[master_seed, 5, n_sub, 999]; re-permute on exhaustion"
MISSING_BOUNDS_REASON = "selection bounds not available (observed bounds and/or shared replicate bounds missing; not treated as 0)"


def _integer(v, name, minimum=0):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)) or v < minimum:
        raise InputContractError(f"{name} must be a non-bool integer >= {minimum}")
    return int(v)


def _sha(v, name):
    if not isinstance(v, str) or re.fullmatch(r"[0-9a-f]{64}", v) is None:
        raise InputContractError(f"{name} must be a 64-hex SHA256")


def _inventory(d, expected, name):
    if not isinstance(d, dict) or any(isinstance(k, (bool, np.bool_)) or not isinstance(k, (int, np.integer)) for k in d) or set(d) != set(expected):
        raise InputContractError(f"{name}: exact integer-key inventory required")


def _finite_array(x, name, shape=None, nonnegative=False):
    try: a = np.asarray(x)
    except (TypeError, ValueError) as e: raise InputContractError(f"{name}: numeric array required") from e
    if a.dtype.kind not in "iuf" or (shape is not None and a.shape != shape) or not np.all(np.isfinite(a)) or (nonnegative and np.any(a < 0)):
        raise InputContractError(f"{name}: finite numeric array with expected shape required")
    return a


def _bank(b):
    if not isinstance(b, PositionBank): raise InputContractError("PositionBank required")
    _integer(b.position_id, "position_id")
    m = _integer(b.m, "bank.m", 1); K = _integer(b.K, "bank.K", 1)
    _finite_array(b.Tw, "bank.Tw", (K*m, 2))
    cid = np.asarray(b.cid)
    if cid.shape != (K*m,) or cid.dtype.kind not in 'iu' or np.any(cid < 0) or np.any(cid >= K):
        raise InputContractError("bank cid shape/type/range invalid")
    if not np.all(np.bincount(cid.astype(np.int64), minlength=K) == m):
        raise InputContractError("each cluster must contain exactly m rows")
    labels=np.asarray(b.cluster_labels)
    if labels.shape != (K,) or labels.dtype.kind not in 'iu' or np.any(labels < 0) or len(set(labels.tolist())) != K:
        raise InputContractError("bank original cluster label map invalid")
    return bank_identity(b)


def _bank_identity(d, name):
    keys={'position_id','K','m','rows','Tw_sha256','cid_sha256','labels_sha256'}
    if not isinstance(d,dict) or set(d)!=keys:raise InputContractError(f"{name}: bank identity schema")
    _integer(d['position_id'],name+'.position_id')
    K=_integer(d['K'],name+'.K',1);m=_integer(d['m'],name+'.m',1)
    if _integer(d['rows'],name+'.rows',1)!=K*m:raise InputContractError(f"{name}: rows != K*m")
    for k in ('Tw_sha256','cid_sha256','labels_sha256'):_sha(d[k],name+'.'+k)


def _pair(primary, sensitivity):
    p,q=_bank(primary),_bank(sensitivity)
    if any(p[k]!=q[k] for k in ('position_id','K','m','rows','cid_sha256','labels_sha256')):
        raise InputContractError("paired banks must identify the same position, rows and original cluster labels in the same order")


def _distance_kind(dist):
    if not callable(dist):raise InputContractError("distance callable required")
    return next((k for k,f in DISTANCE_KINDS.items() if f is dist), 'injected_test_callable:'+getattr(dist,'__name__','unknown'))


@dataclass
class SharedNullAsset:
    identity: dict
    null: Dict[int, dict]
    replicate_bounds: Optional[Dict[int,List[float]]]
    sha256: str = ''
    def as_dict(self):return ser.to_jsonable(asdict(self))
    def payload_sha(self):
        d=asdict(self);d.pop('sha256',None)
        return hashlib.sha256(ser.dumps(d).encode()).hexdigest()
    def validate(self):
        idn=self.identity
        keys={'iso','iso_f32','whitening','m','master_seed','n_subs','B_max','rng_key_rule','distance_kind'}
        if not isinstance(idn,dict) or set(idn)!=keys:raise InputContractError("shared identity exact schema required")
        _bank_identity(idn['iso'],'iso')
        m=_integer(idn['m'],'m',1);_integer(idn['master_seed'],'master_seed')
        if idn['iso']['m']!=m:raise InputContractError("shared m differs from bank m")
        ns=idn['n_subs']
        if not isinstance(ns,(list,tuple)) or tuple(_integer(x,'n_sub',1) for x in ns)!=tuple(RULES.n_subs):raise InputContractError("shared n_sub set differs")
        if _integer(idn['B_max'],'B_max',1)!=RULES.B_levels[-1]:raise InputContractError("shared B_max differs")
        if idn['rng_key_rule']!=RNG_RULE:raise InputContractError("shared RNG rule differs")
        kind=idn['distance_kind']
        if not isinstance(kind,str) or (kind not in DISTANCE_KINDS and not kind.startswith('injected_test_callable:')):raise InputContractError("distance kind invalid")
        if idn['whitening'] is not None and not isinstance(idn['whitening'],dict):raise InputContractError("whitening identity must be a dict or explicit None")
        if idn['iso_f32'] is not None:
            _bank_identity(idn['iso_f32'],'iso_f32')
            if any(idn['iso'][k]!=idn['iso_f32'][k] for k in ('position_id','K','m','rows','cid_sha256','labels_sha256')):raise InputContractError("paired iso identities inconsistent")
        if (idn['iso_f32'] is None)!=(self.replicate_bounds is None):raise InputContractError("paired iso identity and bounds availability inconsistent")
        _inventory(self.null,RULES.n_subs,'null')
        if self.replicate_bounds is not None:_inventory(self.replicate_bounds,RULES.n_subs,'replicate bounds')
        B=RULES.B_levels[-1]
        for n in RULES.n_subs:
            kc=_kc(n,m);e=self.null[n]
            if not isinstance(e,dict) or set(e)!= {'values','blocks','pairwise','B_max'}:raise InputContractError("null evidence schema invalid")
            if _integer(e['B_max'],'null.B_max',1)!=B:raise InputContractError("null entry B_max differs")
            _finite_array(e['values'],'null.values',(B,),True)
            if self.replicate_bounds is not None:_finite_array(self.replicate_bounds[n],'replicate bounds',(B,),True)
        # Reuse the established range, disjoint-block and pair/max replay checks.
        from .w2_manifest import _replay_null
        try:_replay_null({'null':self.null},m,idn['iso']['K'])
        except (KeyError,TypeError,ValueError) as e:
            if isinstance(e,InputContractError):raise
            raise InputContractError(f"invalid shared null evidence: {e}") from e
        _sha(self.sha256,'shared SHA')
        if self.sha256!=self.payload_sha():raise InputContractError("shared null SHA does not match its payload")
        return True


def build_shared_null(iso:PositionBank,m:int,master_seed:int,dist:Callable=w2_exact,iso_f32:Optional[PositionBank]=None,whitening_identity:Optional[dict]=None)->SharedNullAsset:
    m=_integer(m,'m',1);master_seed=_integer(master_seed,'master_seed');_bank(iso)
    if iso.m!=m:raise InputContractError("iso m differs")
    if iso_f32 is not None:_pair(iso,iso_f32)
    dkind=_distance_kind(dist)
    def snapshot():
        return _norm_identity(dict(iso=_bank(iso),iso_f32=None if iso_f32 is None else _bank(iso_f32),whitening=whitening_identity,m=m,master_seed=master_seed,n_subs=list(RULES.n_subs),B_max=RULES.B_levels[-1],rng_key_rule=RNG_RULE,distance_kind=dkind))
    ident=snapshot()  # BEFORE the first distance call, including paired inputs.
    null={};bounds={} if iso_f32 is not None else None
    for n in RULES.n_subs:
        e=null_max_sequence(iso,n,m,master_seed,dist)
        null[n]=dict(values=e['values'].tolist(),blocks=e['blocks'],pairwise=e['pairwise'],B_max=e['B_max'])
        if iso_f32 is not None:
            rb=[]
            for blocks in e['blocks']:
                eps=[float(np.sqrt(np.mean(np.sum((iso.Tw[np.isin(iso.cid,bl)]-iso_f32.Tw[np.isin(iso_f32.cid,bl)])**2,axis=1)))) for bl in blocks]
                rb.append(max(eps[i]+eps[j] for i in range(3) for j in range(i+1,3)))
            bounds[n]=rb
    if snapshot()!=ident:raise InputContractError("isotropic inputs changed during shared null construction")
    a=SharedNullAsset(ident,null,bounds);a.sha256=a.payload_sha();a.validate();return a


def delta_q99_bound_from_prefix(asset:SharedNullAsset,n_sub:int,B_final:int)->float:
    if not isinstance(asset,SharedNullAsset):raise InputContractError("SharedNullAsset required")
    asset.validate();n=_integer(n_sub,'n_sub',1);B=_integer(B_final,'B_final',1)
    if n not in RULES.n_subs or B not in RULES.B_levels:raise InputContractError("registered n_sub/B_final required")
    if asset.replicate_bounds is None:raise InputContractError("shared null has no paired selection bounds")
    return float(np.max(np.asarray(asset.replicate_bounds[n],float)[:B]))


def _observed_bounds(ob):
    if ob is None:return None
    _inventory(ob,RULES.n_subs,'observed bounds')
    for n in RULES.n_subs:
        _inventory(ob[n],RULES.seed_ids,'observed bounds seeds')
        for s in RULES.seed_ids:_finite_array(ob[n][s],'observed bound',(),True)
    return _norm_identity(ob)


def w2_trigger_shared(positions:List[PositionBank],asset:SharedNullAsset,m:int,master_seed:int,dist:Callable=w2_exact,case_id:str='case',obs_bounds=None,whitening_identity:Optional[dict]=None,positions_f32:Optional[List[PositionBank]]=None)->dict:
    if not isinstance(asset,SharedNullAsset):raise InputContractError("SharedNullAsset required")
    asset.validate();m=_integer(m,'m',1);master_seed=_integer(master_seed,'master_seed')
    _check_positions(positions,m)
    for p in positions:_bank(p)
    if positions_f32 is not None:
        _check_positions(positions_f32,m)
        for p,q in zip(positions,positions_f32):_pair(p,q)
    ob_supplied=_observed_bounds(obs_bounds)
    dkind=_distance_kind(dist);idn=asset.identity
    if idn['m']!=m or idn['master_seed']!=master_seed or idn['distance_kind']!=dkind:raise InputContractError("case m / seed / distance differ from shared identity")
    if _norm_identity(whitening_identity)!=idn['whitening']:raise InputContractError("case whitening differs from shared identity")
    def snapshot():
        return _norm_identity(dict(positions=[_bank(p) for p in positions],positions_f32=None if positions_f32 is None else [_bank(p) for p in positions_f32],shared_null_sha256=asset.sha256,m=m,master_seed=master_seed,distance_kind=dkind,whitening=whitening_identity))
    start=snapshot()
    obs_ev={n:{s:observed_w2max(positions,n,m,s,master_seed,dist) for s in RULES.seed_ids} for n in RULES.n_subs}
    observed={n:{s:obs_ev[n][s]['W2_max'] for s in RULES.seed_ids} for n in RULES.n_subs}
    null={n:np.asarray(asset.null[n]['values'],float) for n in RULES.n_subs}
    stop=w2_stop(null,observed,f'shared:{asset.sha256[:16]}');spread=max(seed_spread(observed[n]) for n in observed)
    obs_bounds=ob_supplied
    if positions_f32 is not None:
        computed={}
        for n in RULES.n_subs:
            computed[n]={}
            for s in RULES.seed_ids:
                subs=obs_ev[n][s]['subsets']
                eps=[float(np.sqrt(np.mean(np.sum((p.Tw[np.isin(p.cid,subs[p.position_id])]-q.Tw[np.isin(q.cid,subs[p.position_id])])**2,axis=1)))) for p,q in zip(positions,positions_f32)]
                computed[n][s]=max(eps[i]+eps[j] for i in range(3) for j in range(i+1,3))
        _observed_bounds(computed)
        if ob_supplied is not None and any(ob_supplied[n][s]<computed[n][s] for n in RULES.n_subs for s in RULES.seed_ids):raise InputContractError("supplied bound smaller than the paired subset bound")
        if ob_supplied is None:obs_bounds=computed
    asset.validate()
    if snapshot()!=start:raise InputContractError("W2 case inputs, including paired banks / shared asset, changed during evaluation")
    dq=None
    if obs_bounds is not None and asset.replicate_bounds is not None:
        dq={n:float(np.max(np.asarray(asset.replicate_bounds[n],float)[:stop.B_final])) for n in RULES.n_subs}
    ev=dict(inputs=start,shared_null_sha256=asset.sha256,case_id=case_id,distance_kind=dkind,whitening=start['whitening'],observed=obs_ev,null=copy.deepcopy(asset.null),bounds=dict(obs_bounds=_norm_identity(obs_bounds),delta_q99_bound=dq),m=m,master_seed=master_seed)
    val=dict(state='w2-unresolved',reason=MISSING_BOUNDS_REASON) if obs_bounds is None or dq is None else w2_validate(stop,spread,obs_bounds,dq,observed)
    trig=val['trigger'] if val['state']=='valid' else UNKNOWN
    return dict(stop=stop.as_dict(),observed=observed,validation=val,trigger=trig,spread=spread,evidence=ev,null_q99={n:float(np.quantile(null[n][:stop.B_final],.99,method=RULES.quantile_method)) for n in null})
