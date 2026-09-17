# -*- coding: utf-8 -*-
"""Strict-JSON encoder/decoder for helper results: non-finite floats become tagged objects, integer dict keys become tagged pairs, NumPy scalars/arrays become
Python/list. Technical-failure values are None + reason (never a fake ±inf). Decoding restores floats, int keys and tuples of ints where tagged."""
from __future__ import annotations
import math, json
import numpy as np
from .errors import InputContractError

_NF = {"inf": math.inf, "-inf": -math.inf, "nan": math.nan}


def to_jsonable(o):
    if isinstance(o, dict):
        kinds = {("int" if (isinstance(k, (int, np.integer)) and not isinstance(k, (bool, np.bool_))) else "str" if isinstance(k, str) else "other") for k in o}
        if "other" in kinds or len(kinds) > 1: raise InputContractError("dict keys must be all-int or all-str for strict serialisation")
        if kinds == {"int"}: return {"__intkeys__": [[int(k), to_jsonable(v)] for k, v in o.items()]}
        return {str(k): to_jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [to_jsonable(v) for v in o]
    if isinstance(o, np.ndarray): return to_jsonable(o.tolist())
    if isinstance(o, (bool, np.bool_)): return bool(o)
    if isinstance(o, (int, np.integer)): return int(o)
    if isinstance(o, (float, np.floating)):
        f = float(o)
        if math.isnan(f): return {"__float__": "nan"}
        if math.isinf(f): return {"__float__": "inf" if f > 0 else "-inf"}
        return f
    return o


def from_jsonable(o):
    if isinstance(o, dict):
        if set(o) == {"__float__"}: return _NF[o["__float__"]]
        if set(o) == {"__intkeys__"}:
            ks = [int(k) for k, _ in o["__intkeys__"]]
            if len(set(ks)) != len(ks): raise InputContractError("duplicate tagged integer key")
            return {int(k): from_jsonable(v) for k, v in o["__intkeys__"]}
        return {k: from_jsonable(v) for k, v in o.items()}
    if isinstance(o, list): return [from_jsonable(v) for v in o]
    return o


def dumps(o) -> str: return json.dumps(to_jsonable(o), allow_nan=False, ensure_ascii=False)
def _reject_constant(c): raise InputContractError(f"bare {c} is not allowed in strict JSON")
def _pairs_hook(pairs):
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys): raise InputContractError("duplicate object key in strict JSON")
    return dict(pairs)
def loads(s: str): return from_jsonable(json.loads(s, parse_constant=_reject_constant, object_pairs_hook=_pairs_hook))
