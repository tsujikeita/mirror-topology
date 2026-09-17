# -*- coding: utf-8 -*-
"""Formal runner (rules §13; audit tranche 21 §10): the registered entry that (1) runs the official gate on the SAME FamilyInputs that are evaluated, (2) freezes an input
fingerprint before the gate and re-checks it after the evaluation (inputs are never modified after inspection), (3) evaluates with the registered staged procedure,
(4) stores the gate record and the fingerprint in the result evidence, and (5) writes the checkpoint. In 'official' mode the gate measures the live environment itself
(require_official refuses injected snapshots); in 'smoke' mode structural contracts are required and sizes/versions are recorded as diagnostics."""
from __future__ import annotations
import hashlib
import numpy as np
from .errors import InputContractError
from .orchestrator import FamilyInput, evaluate_family_staged, FamilyResult
from .official_gate import official_gate, require_official, GateRecord
from .checkpoint import write_family_result
from . import serialization as ser


def _array_identity(a):
    """Preserve dtype and shape; do not cast an invalid input back to its old value."""
    x = np.asarray(a)
    if x.dtype.hasobject:
        raise InputContractError("object arrays cannot be fingerprinted as numeric bank data")
    return dict(dtype=x.dtype.str, shape=list(x.shape),
                sha256=hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest())


def input_snapshot(fam: FamilyInput) -> dict:
    """A metadata snapshot of every FamilyInput field consumed by the evaluator.
    Array bytes are represented by dtype/shape/SHA, not copied into JSON. This is
    an execution-integrity check, not an authentication of the physical bank.
    """
    import copy
    if not isinstance(fam, FamilyInput):
        raise InputContractError("FamilyInput required for input snapshot")
    configs = []
    for c in fam.configs:
        configs.append(dict(evaluation_id=c.evaluation_id, family=c.family,
            system=c.system, weight=c.weight, m=c.m,
            batches=sorted(c.batches.items()),
            uids=[u.as_tuple() for u in c.cluster_uids],
            arrays={name:_array_identity(getattr(c,name)) for name in
                    ("T1_model","T2_model","T1_ref","T2_ref")}))
    ep = {}
    for seed,p in sorted(fam.plans.items()):
        ep[seed] = dict(plan_id=p.plan_id, seed_id=p.seed_id, replicates=p.replicates,
            strata={b:[u.as_tuple() for u in uu] for b,uu in sorted(p.strata.items())},
            rng_keys={b:k for b,k in sorted(p.rng_keys.items())},
            multiplicities={b:_array_identity(m) for b,m in sorted(p.multiplicities.items())})
    fb = {e:dict(X_model=_array_identity(f.X_model),X_ref=_array_identity(f.X_ref),
                 cid=_array_identity(f.cid)) for e,f in sorted(fam.fitting.items())}
    fp = {}
    for seed,p in sorted(fam.fit_plans.items()):
        if hasattr(p,"multiplicities"):
            fp[seed] = dict(plan_id=p.plan_id, wave_id=p.wave_id,
                purpose_id=p.PURPOSE_ID, crn_group_id=p.crn_group_id,
                seed_id=p.seed_id, K=p.K, rng_key=p.rng_key,
                bank_sha256=p.bank_sha256, multiplicities=_array_identity(p.multiplicities))
        else:
            fp[seed] = dict(test_only_array=_array_identity(p))
    out = dict(schema="FamilyInputFingerprint-v2",family=fam.family, configs=configs,
        evaluation_plans=ep,fitting_banks=fb,fitting_plans=fp,
        coverage_ok=fam.coverage_ok,fitting_bindings=fam.fitting_bindings,
        grid_identity=fam.grid_identity)
    return copy.deepcopy(ser.from_jsonable(ser.to_jsonable(out)))


def input_fingerprint(fam: FamilyInput) -> str:
    return hashlib.sha256(ser.dumps(input_snapshot(fam)).encode("utf-8")).hexdigest()


def run_family_formal(fam_matched: FamilyInput, fam_native, t1: float, t2: float, mode: str, checkpoint_path: str = None, position_of=None, w2_result=None) -> FamilyResult:
    if mode not in ("official", "smoke"): raise InputContractError("mode must be 'official' or 'smoke'")
    fp_before = dict(matched=input_fingerprint(fam_matched), native=(None if fam_native is None else input_fingerprint(fam_native)))
    gate: GateRecord = require_official(fam_matched, fam_native) if mode == "official" else official_gate(fam_matched, fam_native, "smoke")
    if not gate.passed: raise InputContractError("gate failed: " + "; ".join(gate.required_failures[:5]))
    r = evaluate_family_staged(fam_matched, fam_native, float(t1), float(t2), position_of=position_of, w2_result=w2_result)
    fp_after = dict(matched=input_fingerprint(fam_matched), native=(None if fam_native is None else input_fingerprint(fam_native)))
    if fp_after != fp_before: raise InputContractError("inputs changed between the gate and the end of the evaluation (contract violation; result discarded)")
    r.evidence["gate"] = dict(record=gate.as_dict(), mode=mode, input_fingerprint=fp_before, contract="gate and evaluation used the same FamilyInput objects; fingerprint re-checked after evaluation")
    r.notes.append(f"formal runner: mode={mode}; gate passed; fingerprint verified")
    if checkpoint_path is not None: r.evidence["gate"]["checkpoint_sha256"] = write_family_result(r, checkpoint_path, extra=dict(mode=mode))
    return r
