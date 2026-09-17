# -*- coding: utf-8 -*-
"""BootstrapPlan (rules §6.3/§6.5/§7.1). Multiplicities are drawn from an rng keyed by (master, wave, purpose, crn_group, batch, seed_id) taken from the stratum UIDs,
so plans of different purposes/groups are independent and plans of the same group are shared. Hit tables carry UIDs and are joined to the plan by exact
(set, order, batch, group) comparison; hits are validated non-negative integers <= N; sums use int64."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import hashlib
import numpy as np
from .errors import InputContractError

BOOTSTRAP_STREAM = 4


def stratum_weights_from_tables(tables):
    """Registered stratum weights of ONE evaluation: w_b = N_b / sum_b N_b (sample-count fractions), so that the resampled statistic is the evaluation's sample mean."""
    tot = sum(t.N for t in tables.values()); return {b: t.N / tot for b, t in tables.items()}


from .types import ClusterUID, as_uid
__all__ = ['ClusterUID', 'as_uid', 'HitTable', 'BootstrapPlan', 'resample_hits', 'literal_resample_hits', 'stratum_weights_from_tables']


@dataclass
class HitTable:
    """Per-cluster integer hits of ONE evaluation, keyed by UID (order = the bank order)."""
    uids: List[ClusterUID]; hits: np.ndarray; N: int; m: int

    def __post_init__(self):
        self.uids = [as_uid(u) for u in self.uids]; h = np.asarray(self.hits)
        if h.ndim != 1 or len(h) != len(self.uids): raise InputContractError("hits/uids length mismatch")
        if not np.issubdtype(h.dtype, np.integer): raise InputContractError("hits must be integers")
        if np.any(h < 0) or np.any(h > self.m): raise InputContractError("hits must satisfy 0 <= hits <= m (cluster size)")
        if not isinstance(self.N, (int, np.integer)) or self.N <= 0 or self.N != len(self.uids) * self.m: raise InputContractError("N must equal clusters * m")
        if len(set(self.uids)) != len(self.uids): raise InputContractError("duplicate UIDs in hit table")
        self.hits = h.astype(np.int64)


@dataclass
class BootstrapPlan:
    plan_id: str; seed_id: int; strata: Dict[int, List[ClusterUID]]; replicates: int; rng_keys: Dict[int, list] = field(default_factory=dict); multiplicities: Dict[int, np.ndarray] = field(default_factory=dict)

    @classmethod
    def build(cls, plan_id: str, seed_id: int, strata: Dict[int, List[ClusterUID]], B: int, master_seed: int):
        if not isinstance(B, (int, np.integer)) or B <= 0: raise InputContractError("B must be a positive integer")
        keys, mult, seen = {}, {}, set(); strata = {int(b): [as_uid(u) for u in uids] for b, uids in strata.items()}
        for b, uids in sorted(strata.items()):
            if len(uids) == 0: raise InputContractError(f"stratum {b} empty")
            if len(set(uids)) != len(uids): raise InputContractError(f"stratum {b}: duplicate UIDs")
            if any(u in seen for u in uids): raise InputContractError("UID appears in more than one stratum")
            seen.update(uids)
            w, p, g = {u.wave_id for u in uids}, {u.purpose_id for u in uids}, {u.crn_group_id for u in uids}
            if len(w) != 1 or len(p) != 1 or len(g) != 1: raise InputContractError(f"stratum {b}: UIDs must share wave/purpose/crn_group")
            if any(u.batch_id != b for u in uids): raise InputContractError(f"stratum {b}: UID batch_id must equal the stratum key")
            key = [int(master_seed), w.pop(), p.pop(), g.pop(), int(b), int(seed_id), BOOTSTRAP_STREAM]; keys[b] = key
            rng = np.random.default_rng(np.random.SeedSequence(key)); K = len(uids); idx = rng.integers(0, K, (B, K))
            m = np.stack([np.bincount(idx[r], minlength=K) for r in range(B)]).astype(np.int64)
            assert m.shape == (B, K) and np.all(m.sum(axis=1) == K) and np.all(m >= 0); mult[b] = m
        plan = cls(plan_id, int(seed_id), strata, int(B), keys, mult); plan.validate(); return plan

    def validate(self):
        """Re-validate a (possibly restored) plan: strata/UID inventory, rng keys, multiplicity dtype/shape/non-negativity/row sums."""
        if not isinstance(self.replicates, int) or self.replicates <= 0: raise InputContractError('plan: replicates')
        if set(self.strata) != set(self.multiplicities) or set(self.strata) != set(self.rng_keys): raise InputContractError('plan: strata/multiplicity/key inventory mismatch')
        for b, uids in self.strata.items():
            m = np.asarray(self.multiplicities[b]); K = len(uids)
            if m.dtype.kind not in 'iu' or m.shape != (self.replicates, K) or np.any(m < 0) or not np.all(m.sum(axis=1) == K): raise InputContractError(f'plan: multiplicities of batch {b} invalid')
            if len(set(uids)) != K or any(as_uid(u).batch_id != b for u in uids): raise InputContractError(f'plan: UID inventory of batch {b} invalid')
            k = self.rng_keys[b]; u0 = as_uid(uids[0])
            if not (isinstance(k, (list, tuple)) and len(k) == 7 and all(isinstance(x, (int, np.integer)) and not isinstance(x, bool) for x in k)): raise InputContractError(f'plan: rng key of batch {b} malformed')
            if not (k[1] == u0.wave_id and k[2] == u0.purpose_id and k[3] == u0.crn_group_id and k[4] == b and k[5] == self.seed_id and k[6] == BOOTSTRAP_STREAM): raise InputContractError(f'plan: rng key of batch {b} does not match the stratum UIDs (wave/purpose/group/batch/seed/stream)')
            if len({(as_uid(u).wave_id, as_uid(u).purpose_id, as_uid(u).crn_group_id) for u in uids}) != 1: raise InputContractError(f'plan: batch {b} UIDs do not share wave/purpose/group')
        return True


def _check_weights(weights_by_batch, tables: Dict[int, HitTable]):
    """Stratum weights must equal the evaluation's sample-count fractions N_b / sum N (rules §6.5); None -> derived."""
    derived = stratum_weights_from_tables(tables)
    if weights_by_batch is None: return derived
    if set(weights_by_batch) != set(tables): raise InputContractError("stratum weight inventory mismatch")
    w = {b: float(weights_by_batch[b]) for b in tables}
    if any(not np.isfinite(v) or v < 0 for v in w.values()): raise InputContractError("stratum weights must be finite and non-negative")
    if not np.isclose(sum(w.values()), 1.0, rtol=0, atol=1e-12): raise InputContractError("stratum weights must sum to 1")
    if any(not np.isclose(w[b], derived[b], rtol=0, atol=1e-12) for b in tables): raise InputContractError(f"stratum weights must equal sample-count fractions {derived} (family prior weights are a different quantity)")
    return w


def _join(plan: BootstrapPlan, tables: Dict[int, HitTable]):
    plan.validate()
    if not tables: raise InputContractError("no hit tables")
    for b, t in tables.items():
        if not isinstance(t, HitTable): raise InputContractError("tables must be HitTable instances")
        if b not in plan.strata: raise InputContractError(f"batch {b} not in plan")
        if t.uids != plan.strata[b]: raise InputContractError(f"batch {b}: hit-table UID inventory/order does not match the plan stratum")


def resample_hits(plan: BootstrapPlan, tables: Dict[int, HitTable], weights_by_batch: Optional[Dict[int, float]] = None):
    """Stratified paired resampling of ONE evaluation's hit tables (dict batch -> HitTable). Returns (B,) probability estimates and per-batch int64 hit sums."""
    _join(plan, tables); w = _check_weights(weights_by_batch, tables); B = plan.replicates; P = np.zeros(B); sums = {}
    for b, t in tables.items():
        s = plan.multiplicities[b] @ t.hits; sums[b] = s.astype(np.int64); P += w[b] * s / t.N
    if not np.all(np.isfinite(P)) or np.any(P < 0) or np.any(P > 1): raise InputContractError("resampled probability not finite in [0,1]")
    return P, sums


def literal_resample_hits(plan: BootstrapPlan, tables: Dict[int, HitTable], weights_by_batch: Optional[Dict[int, float]] = None):
    _join(plan, tables); w = _check_weights(weights_by_batch, tables); B = plan.replicates; P = np.zeros(B); sums = {}
    for b, t in tables.items():
        m = plan.multiplicities[b]; out = np.zeros(B, dtype=np.int64)
        for r in range(B):
            out[r] = int(np.sum(np.repeat(t.hits, m[r]))) if m[r].sum() > 0 else 0
        sums[b] = out; P += w[b] * out / t.N
    return P, sums


@dataclass
class FittingPlan:
    """Shared cluster-resampling plan for the fitting banks of ONE family/CRN group: identity (wave, purpose=fitting, crn_group, seed_id), K, multiplicities (+ their SHA).
    It carries NO bank array SHA: bank identity is a separate per-configuration binding table (FamilyInput.fitting_bindings), because all configurations and both systems of a
    family share the same latent order / resampling plan while their transformed arrays differ. `bank_sha256` is retained only as an optional single-bank convenience."""
    plan_id: str; wave_id: int; crn_group_id: int; seed_id: int; K: int; multiplicities: np.ndarray; rng_key: list = field(default_factory=list); bank_sha256: Optional[str] = None
    PURPOSE_ID = 300

    @classmethod
    def build(cls, plan_id: str, wave_id: int, crn_group_id: int, seed_id: int, K: int, B: int, master_seed: int, bank_sha256: Optional[str] = None):
        if not (isinstance(K, (int, np.integer)) and K > 0 and isinstance(B, (int, np.integer)) and B > 0): raise InputContractError("K and B must be positive integers")
        key = [int(master_seed), int(wave_id), cls.PURPOSE_ID, int(crn_group_id), 0, int(seed_id), BOOTSTRAP_STREAM]
        rng = np.random.default_rng(np.random.SeedSequence(key)); idx = rng.integers(0, K, (B, K)); M = np.stack([np.bincount(idx[r], minlength=K) for r in range(B)]).astype(np.int64)
        p = cls(plan_id, int(wave_id), int(crn_group_id), int(seed_id), int(K), M, key, bank_sha256); p.validate(); return p

    def validate(self):
        M = np.asarray(self.multiplicities)
        if not (isinstance(self.K, int) and self.K > 0): raise InputContractError("fitting plan K must be a positive integer")
        if M.dtype.kind not in 'iu' or M.ndim != 2 or M.shape[0] == 0 or M.shape[1] != self.K or np.any(M < 0) or not np.all(M.sum(axis=1) == self.K): raise InputContractError("fitting plan multiplicities invalid (need B>0 integer rows summing to K)")
        k = self.rng_key
        if not (isinstance(k, (list, tuple)) and len(k) == 7 and all(isinstance(x, (int, np.integer)) and not isinstance(x, bool) and int(x) >= 0 for x in k)): raise InputContractError("fitting plan rng key malformed")
        if not (k[1] == self.wave_id and k[2] == self.PURPOSE_ID and k[3] == self.crn_group_id and k[4] == 0 and k[5] == self.seed_id and k[6] == BOOTSTRAP_STREAM): raise InputContractError("fitting plan rng key does not match its identity (wave/purpose/group/batch=0/seed/stream)")
        return True

    @property
    def multiplicities_sha256(self) -> str: return hashlib.sha256(np.ascontiguousarray(self.multiplicities).tobytes()).hexdigest()


def bank_sha256(X_model: np.ndarray, X_ref: np.ndarray, cid: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(X_model).tobytes() + np.ascontiguousarray(X_ref).tobytes() + np.ascontiguousarray(cid).tobytes()).hexdigest()
