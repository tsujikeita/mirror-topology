# -*- coding: utf-8 -*-
"""Save / restore of resampling plans (BootstrapPlan, FittingPlan) in strict JSON with integrity: every restored plan is validated, its multiplicities are compared with a
regeneration from the stored rng keys (the plan is a deterministic function of its keys), and the file bytes are bound by SHA. A plan that cannot be regenerated from its
declared keys is rejected (no silent acceptance of edited multiplicities)."""
from __future__ import annotations
import hashlib, os, json
import numpy as np
from .errors import InputContractError
from .bootstrap_plan import BootstrapPlan, FittingPlan, BOOTSTRAP_STREAM
from .types import ClusterUID
from . import serialization as ser


def _plan_to_dict_checked_types(plan) -> dict:
    if isinstance(plan, BootstrapPlan):
        plan.validate()
        return dict(kind="BootstrapPlan", plan_id=plan.plan_id, seed_id=plan.seed_id, replicates=plan.replicates, strata={int(b): [u.as_tuple() for u in uids] for b, uids in plan.strata.items()},
                    rng_keys={int(b): list(k) for b, k in plan.rng_keys.items()}, multiplicities={int(b): np.asarray(m).tolist() for b, m in plan.multiplicities.items()},
                    multiplicities_sha256={int(b): hashlib.sha256(np.ascontiguousarray(np.asarray(m, np.int64)).tobytes()).hexdigest() for b, m in plan.multiplicities.items()})
    if isinstance(plan, FittingPlan):
        plan.validate()
        return dict(kind="FittingPlan", plan_id=plan.plan_id, wave_id=plan.wave_id, crn_group_id=plan.crn_group_id, seed_id=plan.seed_id, K=plan.K, rng_key=list(plan.rng_key), bank_sha256=plan.bank_sha256,
                    multiplicities=np.asarray(plan.multiplicities).tolist(), multiplicities_sha256=plan.multiplicities_sha256)
    raise InputContractError("unsupported plan type")


def _plan_from_dict_checked_types(d: dict):
    kind = d.get("kind")
    if kind == "BootstrapPlan":
        strata = {int(b): [ClusterUID(*map(int, u)) for u in uids] for b, uids in d["strata"].items()}
        mult = {int(b): np.asarray(m, dtype=np.int64) for b, m in d["multiplicities"].items()}
        keys = {int(b): [int(x) for x in k] for b, k in d["rng_keys"].items()}
        p = BootstrapPlan(str(d["plan_id"]), int(d["seed_id"]), strata, int(d["replicates"]), keys, mult); p.validate()
        for b, k in keys.items():                                                                           # regenerate from the declared keys and compare
            K = len(strata[b]); rng = np.random.default_rng(np.random.SeedSequence(k)); idx = rng.integers(0, K, (p.replicates, K))
            regen = np.stack([np.bincount(idx[r], minlength=K) for r in range(p.replicates)]).astype(np.int64)
            if not np.array_equal(regen, mult[b]): raise InputContractError(f"BootstrapPlan batch {b}: stored multiplicities are not the deterministic function of the stored rng key")
            if hashlib.sha256(np.ascontiguousarray(mult[b]).tobytes()).hexdigest() != d["multiplicities_sha256"][str(b) if str(b) in d["multiplicities_sha256"] else b]: raise InputContractError("BootstrapPlan multiplicity SHA mismatch")
            master = k[0]; expected = [master, strata[b][0].wave_id, strata[b][0].purpose_id, strata[b][0].crn_group_id, b, p.seed_id, BOOTSTRAP_STREAM]
            if k != expected: raise InputContractError("BootstrapPlan rng key does not match its stratum identity")
        return p
    if kind == "FittingPlan":
        M = np.asarray(d["multiplicities"], dtype=np.int64); p = FittingPlan(str(d["plan_id"]), int(d["wave_id"]), int(d["crn_group_id"]), int(d["seed_id"]), int(d["K"]), M, [int(x) for x in d["rng_key"]], d.get("bank_sha256")); p.validate()
        rng = np.random.default_rng(np.random.SeedSequence(p.rng_key)); idx = rng.integers(0, p.K, (M.shape[0], p.K)); regen = np.stack([np.bincount(idx[r], minlength=p.K) for r in range(M.shape[0])]).astype(np.int64)
        if not np.array_equal(regen, M): raise InputContractError("FittingPlan: stored multiplicities are not the deterministic function of the stored rng key")
        if p.multiplicities_sha256 != d["multiplicities_sha256"]: raise InputContractError("FittingPlan multiplicity SHA mismatch")
        return p
    raise InputContractError("unknown plan kind")



# Audit candidate: this storage boundary explicitly accepts canonical native int64
# multiplicities. Other valid in-memory integer dtypes are rejected BEFORE writing,
# rather than silently converted or producing a file that cannot be read back.
def _integer(v, where, minimum=0):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)) or v < minimum:
        raise InputContractError(f"{where}: a non-bool integer >= {minimum} is required")
    return int(v)


def _name(v, where):
    if not isinstance(v, str) or not v.strip():
        raise InputContractError(f"{where}: a nonempty string is required")
    return v


def _sha(v, where):
    if not isinstance(v, str) or len(v) != 64 or any(x not in '0123456789abcdef' for x in v):
        raise InputContractError(f"{where}: SHA256 must be 64 lowercase hexadecimal characters")
    return v


def _batch_mapping(d, where):
    if not isinstance(d, dict) or not d:
        raise InputContractError(f"{where}: a nonempty batch mapping is required")
    out = {}
    for raw_b, value in d.items():
        # Canonical decimal strings are accepted for plain-JSON interoperation;
        # mixed spellings of the same logical batch are NEVER overwritten.
        if isinstance(raw_b, str):
            if not raw_b.isascii() or not raw_b.isdecimal() or str(int(raw_b)) != raw_b:
                raise InputContractError(f"{where}: invalid decimal batch key")
            b = int(raw_b)
        else:
            b = _integer(raw_b, where + ' key')
        if b in out:
            raise InputContractError(f"{where}: duplicate logical batch key")
        out[b] = value
    return out


def _multiplicity(v, where):
    # Validate raw scalar types before np.asarray(..., int64) can discard data.
    if isinstance(v, np.ndarray):
        if v.ndim != 2 or v.dtype.kind not in 'iu' or np.any(v < 0):
            raise InputContractError(f"{where}: non-negative integer matrix required")
        if v.size and np.max(v) > np.iinfo(np.int64).max:
            raise InputContractError(f"{where}: integer exceeds the int64 storage range")
    elif isinstance(v, (list, tuple)) and v:
        K = None
        for row in v:
            if not isinstance(row, (list, tuple)) or not row:
                raise InputContractError(f"{where}: nonempty rectangular integer matrix required")
            if K is None:
                K = len(row)
            if len(row) != K:
                raise InputContractError(f"{where}: ragged matrix")
            for x in row:
                if _integer(x, where + ' element') > np.iinfo(np.int64).max:
                    raise InputContractError(f"{where}: integer exceeds the int64 storage range")
    else:
        raise InputContractError(f"{where}: nonempty integer matrix required")
    try:
        a = np.asarray(v, dtype=np.int64)
    except (ValueError, TypeError, OverflowError) as exc:
        raise InputContractError(f"{where}: invalid integer matrix") from exc
    if a.ndim != 2 or not all(a.shape) or np.any(a < 0):
        raise InputContractError(f"{where}: invalid dimensions or count")
    K = a.shape[1]
    # Bounding cells before summing also prevents an int64 overflow passing row sums.
    if np.any(a > K) or not np.all(a.sum(axis=1) == K):
        raise InputContractError(f"{where}: every row must sum to K")
    return a


def _key(v, where):
    if not isinstance(v, (list, tuple)) or len(v) != 7:
        raise InputContractError(f"{where}: seven integer key components required")
    return [_integer(x, where) for x in v]


def _record(d):
    if not isinstance(d, dict):
        raise InputContractError('plan payload must be a dictionary')
    kind = d.get('kind')
    common = {'kind', 'plan_id', 'seed_id'}
    extra = ({'replicates', 'strata', 'rng_keys', 'multiplicities', 'multiplicities_sha256'}
             if kind == 'BootstrapPlan' else
             {'wave_id', 'crn_group_id', 'K', 'rng_key', 'multiplicities', 'multiplicities_sha256', 'bank_sha256'}
             if kind == 'FittingPlan' else None)
    if extra is None:
        raise InputContractError('unknown plan kind')
    required = common | extra
    # bank_sha256 remains optional, as in the original API.
    missing = required - set(d) - ({'bank_sha256'} if kind == 'FittingPlan' else set())
    if missing or set(d) - required:
        raise InputContractError('plan field inventory mismatch')
    out = dict(d)
    out['plan_id'] = _name(d['plan_id'], 'plan_id')
    out['seed_id'] = _integer(d['seed_id'], 'seed_id')
    if kind == 'BootstrapPlan':
        B = _integer(d['replicates'], 'replicates', 1); out['replicates'] = B
        st = _batch_mapping(d['strata'], 'strata')
        kk = _batch_mapping(d['rng_keys'], 'rng_keys')
        mm = _batch_mapping(d['multiplicities'], 'multiplicities')
        hh = _batch_mapping(d['multiplicities_sha256'], 'multiplicities SHA')
        if not (set(st) == set(kk) == set(mm) == set(hh)):
            raise InputContractError('plan batch inventory mismatch')
        strata, keys, mats = {}, {}, {}
        for b, uids in st.items():
            if not isinstance(uids, (list, tuple)) or not uids:
                raise InputContractError('empty or malformed stratum')
            us = []
            for u in uids:
                if not isinstance(u, (list, tuple)) or len(u) != 5:
                    raise InputContractError('ClusterUID needs five non-negative integer components')
                us.append(tuple(_integer(x, 'ClusterUID') for x in u))
            a = _multiplicity(mm[b], 'multiplicities')
            if a.shape != (B, len(us)):
                raise InputContractError('multiplicity dimensions differ from declared B/K')
            strata[b] = us; keys[b] = _key(kk[b], 'rng key'); mats[b] = a
            _sha(hh[b], 'multiplicity SHA')
        out.update(strata=strata, rng_keys=keys, multiplicities=mats, multiplicities_sha256=hh)
    else:
        for k in ('wave_id', 'crn_group_id'):
            out[k] = _integer(d[k], k)
        out['K'] = _integer(d['K'], 'K', 1)
        out['rng_key'] = _key(d['rng_key'], 'rng key')
        a = _multiplicity(d['multiplicities'], 'multiplicities')
        if a.shape[1] != out['K']:
            raise InputContractError('fitting multiplicity dimension differs from K')
        out['multiplicities'] = a
        _sha(d['multiplicities_sha256'], 'multiplicity SHA')
        if d.get('bank_sha256') is not None:
            _sha(d['bank_sha256'], 'bank SHA')
    return out


def plan_to_dict(plan) -> dict:
    if not isinstance(plan, (BootstrapPlan, FittingPlan)):
        raise InputContractError('unsupported plan type')
    matrices = plan.multiplicities.values() if isinstance(plan, BootstrapPlan) else [plan.multiplicities]
    if any(np.asarray(a).dtype != np.dtype(np.int64) for a in matrices):
        raise InputContractError('PlanSet storage currently requires native int64 multiplicities; noncanonical dtype must not be silently converted')
    d = _plan_to_dict_checked_types(plan)
    _record(d)  # validate all raw identity fields before emitting a payload
    return d


def plan_from_dict(d: dict):
    return _plan_from_dict_checked_types(_record(d))


def _plans_mapping(plans):
    if not isinstance(plans, dict):
        raise InputContractError('plans must be a dictionary')
    for name in plans:
        _name(name, 'plan set name')  # do not collapse 1 and "1" via str()
    return plans

def write_plans(plans: dict, path: str) -> str:
    """plans: {name: plan}. Returns SHA256 of the written bytes."""
    plans = _plans_mapping(plans)
    body = ser.dumps(dict(kind="PlanSet", plans={k: plan_to_dict(v) for k, v in plans.items()})).encode("utf-8"); tmp = path + ".tmp"
    with open(tmp, "wb") as fh: fh.write(body); fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, path); return hashlib.sha256(body).hexdigest()



def _decode_plan_set(text):
    # The shared serializer normalises tagged integer keys. Check their raw types
    # here first, so a malformed batch label such as 0.75 cannot become batch 0.
    raw = json.loads(text, parse_constant=ser._reject_constant, object_pairs_hook=ser._pairs_hook)
    def check_tags(o):
        if isinstance(o, dict):
            if set(o) == {'__intkeys__'}:
                pairs = o['__intkeys__']
                if not isinstance(pairs, list):
                    raise InputContractError('tagged integer keys must be a list')
                seen = set()
                for pair in pairs:
                    if not isinstance(pair, list) or len(pair) != 2:
                        raise InputContractError('malformed tagged integer-key pair')
                    k = _integer(pair[0], 'tagged integer key')
                    if k in seen:
                        raise InputContractError('duplicate tagged integer key')
                    seen.add(k); check_tags(pair[1])
            else:
                for value in o.values():
                    check_tags(value)
        elif isinstance(o, list):
            for value in o:
                check_tags(value)
    check_tags(raw)
    return ser.from_jsonable(raw)

def read_plans(path: str, expected_sha256: str = None) -> dict:
    body = open(path, "rb").read()
    if expected_sha256 is not None and hashlib.sha256(body).hexdigest() != expected_sha256: raise InputContractError("plan file bytes do not match the expected SHA256")
    payload = _decode_plan_set(body.decode("utf-8"))
    if not isinstance(payload, dict): raise InputContractError("PlanSet payload must be a dictionary")
    if payload.get("kind") != "PlanSet": raise InputContractError("not a PlanSet file")
    if set(payload) != {"kind", "plans"}: raise InputContractError("PlanSet field inventory mismatch")
    return {k: plan_from_dict(v) for k, v in _plans_mapping(payload["plans"]).items()}
