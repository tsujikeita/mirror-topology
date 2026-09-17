# -*- coding: utf-8 -*-
"""Shared W2 context (rules §9.2, §10; audit tranche 26 R26-A/B/C). The W2 decision of a case (family x size) does not depend on the evaluation threshold, so it is computed
ONCE per case on the shared null asset; the real target, every pseudo evaluation and the full-procedure controls consume the SAME typed decision through this context.
Contracts: (1) case identity at the entrance — non-empty case set, canonical key 'FAMILY/SIZE' (or a registered family key with an explicit size_id; both representations must agree),
registered family, non-empty size, no duplicate canonical keys; (2) issue-time and consumption-time cross-checks — case set == manifest set == decision set, manifest identity ==
case identity, every manifest bound to the context asset SHA, decision fields (trigger, validation state/reason, B_final, observed hash, distance kind) derived from that case's
manifest, context payload SHA over the canonical manifests; (3) evidence — canonical manifest records (payload SHA) and the raw case result are retained (or archived) so the
decision is verifiable from the freeze artefacts. Only the W2 branch is fixed; event-ratio, N selection and 3->12 branching are re-evaluated per threshold by the orchestrator."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional
import copy, hashlib
from .errors import InputContractError
from .positions import PositionBank, VerifiedW2Decision, w2_exact, DISTANCE_KINDS
from .w2_shared import SharedNullAsset, w2_trigger_shared
from .w2_manifest import build_w2_manifest, verified_w2_for_decision, SharedNullAssetRef, W2Manifest
from .grid_registry import FAMILIES
from . import serialization as ser
from .truth import UNKNOWN

SCOPE_TRUSTED = "shared null asset bound to the trusted expected SHA; per-case B_final/validation/trigger; identical decisions for the real target, every pseudo and the full-procedure controls"
SCOPE_INTERNAL = "internal consistency only (no trusted expected asset SHA supplied): not a formal-intake context"


def _is_sha(v) -> bool: return isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)


def _result_sha(result: dict) -> str:
    """Hash the retained raw record, independently of the smaller decision manifest."""
    if not isinstance(result, dict): raise InputContractError("retained W2 result must be a dict")
    return hashlib.sha256(ser.dumps(result).encode()).hexdigest()


def canonical_case_key(key, spec: dict) -> tuple:
    """Return (family, size_id) from 'FAMILY/SIZE' or 'FAMILY' + explicit size_id; reject empty, extra components, unregistered families, conflicting representations."""
    if not isinstance(key, str) or not key: raise InputContractError("case key must be a non-empty string")
    parts = key.split("/")
    if len(parts) > 2 or any(p == "" for p in parts): raise InputContractError(f"case key {key!r} must be 'FAMILY/SIZE' or 'FAMILY' (with explicit size_id)")
    fam = parts[0]; size_key = parts[1] if len(parts) == 2 else None; size_spec = spec.get("size_id") if isinstance(spec, dict) else None
    if fam not in FAMILIES: raise InputContractError(f"unregistered family {fam!r} in case key")
    if size_key is None and size_spec is None: raise InputContractError(f"case {key!r}: size_id is required (key 'FAMILY/SIZE' or explicit size_id)")
    if size_key is not None and size_spec is not None and size_key != size_spec: raise InputContractError(f"case {key!r}: key size {size_key!r} conflicts with explicit size_id {size_spec!r}")
    size = size_key if size_key is not None else size_spec
    if not isinstance(size, str) or not size or "/" in size: raise InputContractError("size_id must be a non-empty string without '/'")
    return fam, size


@dataclass
class W2Context:
    asset_sha256: str; decisions: Dict[str, VerifiedW2Decision]; manifests: Dict[str, W2Manifest]; identities: Dict[str, tuple] = field(default_factory=dict)
    results: Dict[str, dict] = field(default_factory=dict); scope: str = SCOPE_TRUSTED; context_sha256: str = ""
    result_sha256: Dict[str, str] = field(default_factory=dict)  # raw record or explicit content-addressed reference, never omitted from the context payload

    def payload_sha(self) -> str:
        body = dict(asset_sha256=self.asset_sha256, cases={k: dict(identity=list(self.identities[k]), manifest_sha256=self.manifests[k].payload_sha(), decision_checksum=self.decisions[k].checksum) for k in sorted(self.decisions)}, result_sha256=self.result_sha256, scope=self.scope)
        return hashlib.sha256(ser.dumps(body).encode()).hexdigest()

    def validate(self, expected_context_sha256: Optional[str] = None) -> bool:
        if not _is_sha(self.asset_sha256): raise InputContractError("context asset SHA must be 64-hex")
        if not _is_sha(self.context_sha256): raise InputContractError("issued/restored context SHA must be 64-hex")
        if expected_context_sha256 is not None and not _is_sha(expected_context_sha256): raise InputContractError("expected context SHA must be 64-hex")
        if not self.decisions: raise InputContractError("context has no cases (an empty context is not an evaluated W2 context)")
        if set(self.decisions) != set(self.manifests) or set(self.decisions) != set(self.identities): raise InputContractError("context case set, manifest set and identity set must be identical")
        if self.results and set(self.results) != set(self.decisions): raise InputContractError("context result inventory differs from the case set")
        if set(self.result_sha256) != set(self.decisions) or not all(_is_sha(v) for v in self.result_sha256.values()):
            raise InputContractError("context requires one complete raw-result SHA reference per case")
        for k, result in self.results.items():
            if _result_sha(result) != self.result_sha256[k]:
                raise InputContractError(f"case {k}: retained result differs from its registered content SHA")
        seen = set()
        for k in sorted(self.decisions):
            identity = self.identities[k]
            if not isinstance(identity, (tuple, list)) or len(identity) != 2: raise InputContractError("case identity must be (family, size)")
            fam, size = identity
            if canonical_case_key(k, {"size_id": size}) != (fam, size): raise InputContractError("case key and identity disagree")
            if (fam, size) in seen: raise InputContractError(f"duplicate canonical case identity {(fam, size)}")
            seen.add((fam, size))
            m = self.manifests[k]
            if not isinstance(m, W2Manifest): raise InputContractError(f"case {k}: manifest type")
            if (m.family, m.size_id) != (fam, size): raise InputContractError(f"case {k}: manifest identity {(m.family, m.size_id)} differs from the case identity {(fam, size)}")
            if m.shared_null_sha256 != self.asset_sha256: raise InputContractError(f"case {k}: manifest is bound to a different shared null asset")
            d = self.decisions[k]
            if not isinstance(d, VerifiedW2Decision): raise InputContractError(f"case {k}: decision type")
            d.check()
            st = ser.from_jsonable(m.stop); val = ser.from_jsonable(m.validation)
            exp_trig = val.get("trigger") if val.get("state") == "valid" else UNKNOWN
            if d.trigger != exp_trig or d.validation_state != val.get("state") or d.validation_reason != val.get("reason") or d.B_final != int(st["B_final"]) or d.observed_hash != st["observed_hash"] or d.distance_kind != m.distance_kind:
                raise InputContractError(f"case {k}: typed decision does not correspond to this case's manifest (trigger/state/reason/B_final/observed_hash/distance_kind)")
        if self.context_sha256 != self.payload_sha(): raise InputContractError("context SHA does not match its canonical payload")
        if expected_context_sha256 is not None and self.payload_sha() != expected_context_sha256: raise InputContractError("context payload SHA differs from the trusted expected value")
        return True

    def decision_for(self, key: str, expected_context_sha256: Optional[str] = None) -> VerifiedW2Decision:
        """Consumption entry: the whole context is re-validated (membership, asset binding, manifest<->decision correspondence, context SHA) before a decision is released."""
        if key not in self.decisions: raise InputContractError(f"no W2 decision registered for case {key!r} in this context")
        self.validate(expected_context_sha256); return self.decisions[key]

    def as_dict(self) -> dict:
        self.validate()
        return dict(asset_sha256=self.asset_sha256, context_sha256=self.payload_sha(), scope=self.scope, cases={k: dict(family=self.identities[k][0], size_id=self.identities[k][1], manifest_sha256=self.manifests[k].payload_sha(), decision_checksum=self.decisions[k].checksum, trigger=self.decisions[k].trigger, result_sha256=self.result_sha256[k], has_result=(k in self.results)) for k in sorted(self.decisions)},
                    manifests={k: self.manifests[k].payload_sha() for k in sorted(self.manifests)})

    def snapshot(self) -> "W2Context":
        """Immutable-by-copy snapshot for a runner: deep copy + SHA stamp; the runner keeps the expected SHA and re-validates at every consumption."""
        self.validate(); c = copy.deepcopy(self); c.validate(self.context_sha256); return c


def build_w2_context(asset: SharedNullAsset, cases: Dict[str, dict], m: int, master_seed: int, dist: Callable = w2_exact, whitening_identity=None, expected_asset_sha256: Optional[str] = None) -> W2Context:
    """cases: key -> dict(positions=[3 PositionBank], positions_f32=[3 PositionBank] or None, obs_bounds=None, size_id=optional). One W2 decision per case (family x size)."""
    asset.validate()
    if expected_asset_sha256 is not None:
        if not _is_sha(expected_asset_sha256): raise InputContractError("expected asset SHA must be 64-hex")
        if asset.sha256 != expected_asset_sha256: raise InputContractError("shared null asset SHA differs from the trusted expected value")
    if not isinstance(cases, dict) or not cases: raise InputContractError("cases must be a non-empty dict (an empty context is not an evaluated W2 context)")
    idents = {}; seen = set()
    for key, c in cases.items():
        if not isinstance(c, dict) or "positions" not in c: raise InputContractError(f"case {key!r}: a dict with 'positions' is required")
        fam, size = canonical_case_key(key, c)
        if (fam, size) in seen: raise InputContractError(f"duplicate case identity {(fam, size)} under different keys")
        seen.add((fam, size)); idents[key] = (fam, size)
    decisions, manifests, results = {}, {}, {}
    for key, c in cases.items():
        fam, size = idents[key]
        r = w2_trigger_shared(c["positions"], asset, m, master_seed, dist=dist, case_id=f"{fam}/{size}", obs_bounds=c.get("obs_bounds"), whitening_identity=whitening_identity, positions_f32=c.get("positions_f32"))
        man = build_w2_manifest(fam, size, c["positions"], SharedNullAssetRef(asset), r)
        decisions[key] = verified_w2_for_decision(man, c["positions"], SharedNullAssetRef(asset), r); manifests[key] = man; results[key] = ser.from_jsonable(ser.to_jsonable(r))
    ctx = W2Context(asset.sha256, decisions, manifests, idents, results, SCOPE_TRUSTED if expected_asset_sha256 is not None else SCOPE_INTERNAL); ctx.result_sha256 = {k: _result_sha(r) for k, r in results.items()}; ctx.context_sha256 = ctx.payload_sha(); ctx.validate(); return ctx


def decisions_by_family(ctx: W2Context, family_of_case: Optional[Dict[str, str]] = None) -> Dict[str, Dict[str, VerifiedW2Decision]]:
    """Explicit adapter: case decisions grouped by family -> {family: {size_id: decision}} (never a silent rename of one size to the whole family)."""
    ctx.validate(); out = {}
    for k, (fam, size) in ctx.identities.items(): out.setdefault(fam, {})[size] = ctx.decisions[k]
    return out
