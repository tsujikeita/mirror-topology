# -*- coding: utf-8 -*-
"""D-2W (D4C-0a): the nine formal W2 CASES (E2 / E7 / E8 x L1.00 / L1.20 / L1.50; rules §10) assembled from the REGISTERED D-2 W2 position banks (27 units `cfg<id>_w2`: matched
primary, paired float64 / float32 selection paths; N_W2 = 200,000 rows = 2,000 clusters x m = 100) with the REGISTERED shared-null asset and whitening (B-3-2: mu / W, iso pool,
maximal null prefix B_max = 1000, replicate bounds), evaluated once per case by the existing `w2_context.build_w2_context` (observed exact 2-D W2 maxima for n_sub 2000 / 5000 x
3 seeds, prefix stopping rule 200 -> 1000 with the first comparison 200 vs 400, stability gate, paired same-subset float32 bound, trigger / w2-unresolved; technical failures of the
POT solver are raised by positions.w2_exact and never turned into a context) and PUBLISHED as per-case records (manifest, result, typed decision, input identities) plus a
context record. Nothing here changes the W2 mathematics; the module only (i) assembles cases from registered inputs with explicit identity binding, (ii) publishes replayable
records and (iii) RESTORES a typed W2Context from the published records WITHOUT the bank arrays (RegisteredBankIdentity stand-ins carry the execution-time bank identities;
the stop rule / validation / trigger are replayed from the stored pairwise values, blocks, subsets and bounds through the existing verify_w2_manifest; the exact OT distances are
NOT re-run at restoration — their identity is what is verified). The registered loader (load_registered_w2_context) is bound to constants that are filled only AFTER the formal
run is accepted (D2W_REGISTRATION is None until then: every registered-load attempt is refused as 'not registered')."""
from __future__ import annotations
import copy, hashlib, json, os
from typing import Dict, List, Optional, Tuple
import numpy as np
from .errors import InputContractError
from .rules_config import RULES
from .positions import PositionBank, RegisteredBankIdentity, VerifiedW2Decision, w2_exact, bank_identity
from .w2_shared import SharedNullAsset
from .w2_manifest import W2Manifest, SharedNullAssetRef, verified_w2_for_decision
from .w2_context import W2Context, build_w2_context, canonical_case_key, SCOPE_TRUSTED, _result_sha
from .d2_bank import SHARED_NULL, registered_whitening, intake_w2_position_bank, canonical_context
from . import serialization as ser

CASE_SCHEMA = "d2w_case_record_v1"; CONTEXT_SCHEMA = "d2w_context_record_v1"
FAMILIES = ("E2", "E7", "E8"); SIZES = ("L1.00", "L1.20", "L1.50")
D2W_REGISTRATION = None        # bound at the end of the module to the d4c0_registry constants (accepted formal run f3aec793); None would refuse the registered load


def _sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()


def registered_shared_null_asset(phaseb_root: str) -> SharedNullAsset:
    """The registered B-3-2 shared-null asset read from registered_assets/b3_2_shared_null_asset.json, bound to SHARED_NULL (file bytes + payload SHA) and validated."""
    p = os.path.join(os.path.abspath(phaseb_root), "registered_assets", "b3_2_shared_null_asset.json")
    if not os.path.isfile(p): raise InputContractError("registered shared-null asset missing")
    b = open(p, "rb").read()
    if _sha(b) != SHARED_NULL["file_sha256"]: raise InputContractError("registered shared-null asset file differs from SHARED_NULL.file_sha256")
    asset = SharedNullAsset(**ser.loads(b.decode("utf-8"))); asset.validate()
    if asset.sha256 != SHARED_NULL["asset_sha256"] or asset.payload_sha() != SHARED_NULL["asset_sha256"]: raise InputContractError("registered shared-null asset payload differs from SHARED_NULL.asset_sha256")
    return asset


def case_plan(table: Optional[dict] = None) -> Dict[str, dict]:
    """The nine formal cases from the canonical D-2 spec: key 'F/S' -> dict(family, size_id, config_ids (the three W2 primary positions ordered by observer_id 1..3), groups)."""
    spec = canonical_context(table)["spec"]; plan = {}
    for fam in FAMILIES:
        for s in SIZES:
            rows = sorted((c for c in spec["configurations"].values() if c["family"] == fam and c["size_id"] == s and c.get("w2_primary") is not None), key=lambda c: int(c["observer_id"]))
            if len(rows) != 3 or [int(r["observer_id"]) for r in rows] != [1, 2, 3]: raise InputContractError(f"{fam}/{s}: the spec must define exactly the three first-wave W2 primary positions (observer_id 1..3)")
            plan[f"{fam}/{s}"] = dict(family=fam, size_id=s, config_ids=[int(r["config_id"]) for r in rows], observer_ids=[int(r["observer_id"]) for r in rows], groups=[int(r["w2_primary"]["group"]) for r in rows])
    return plan


def assemble_w2_cases(d2_roots: Dict[str, str], matched_roots: Dict[int, np.ndarray], table: dict, formal: bool, registered_units: Optional[Dict[str, dict]] = None, families=FAMILIES, sizes=SIZES) -> Tuple[Dict[str, dict], Dict[str, dict]]:
    """Intake the W2 position banks of every case through d2_bank.intake_w2_position_bank (directory re-verification, spec identity, root SHA == the caller's matched root, registered
    whitening VALUES) and, when registered_units is given (formal path), bind every unit's manifest SHA to the registered D-2 ledger unit of that family. Returns (cases for
    build_w2_context, info per case)."""
    regw = registered_whitening(); plan = case_plan(table); cases = {}; infos = {}
    for key, c in plan.items():
        fam, s = c["family"], c["size_id"]
        if fam not in families or s not in sizes: continue
        if fam not in d2_roots: raise InputContractError(f"{key}: no D-2 run root supplied for family {fam}")
        pos64, pos32, units = [], [], {}
        for cid in c["config_ids"]:
            d = os.path.join(d2_roots[fam], f"cfg{cid}_w2")
            if cid not in matched_roots: raise InputContractError(f"{key}: matched root for configuration {cid} not supplied")
            b64, b32, info = intake_w2_position_bank(cid, d, matched_roots[cid], regw["mu"], regw["W"], dict(SHARED_NULL), table=table, formal=formal)
            if registered_units is not None:
                u = registered_units.get(f"cfg{cid}_w2")
                if u is None or u.get("manifest_sha256") != info["manifest_sha256"]: raise InputContractError(f"{key}: cfg{cid}_w2 is not the registered D-2 W2 unit (manifest SHA)")
            pos64.append(b64); pos32.append(b32); units[f"cfg{cid}_w2"] = dict(manifest_sha256=info["manifest_sha256"], n_clusters=info["n_clusters"], bank_identity_f64=bank_identity(b64), bank_identity_f32=bank_identity(b32), root_matched_sha256=hashlib.sha256(np.ascontiguousarray(np.asarray(matched_roots[cid], float)).tobytes()).hexdigest())
        cases[key] = dict(positions=pos64, positions_f32=pos32, size_id=s)
        infos[key] = dict(family=fam, size_id=s, config_ids=list(c["config_ids"]), groups=list(c["groups"]), units=units, whitening=dict(mu_sha256=regw["mu_sha256"], W_sha256=regw["W_sha256"], identity=dict(SHARED_NULL)), formal=bool(formal))
    if not cases: raise InputContractError("no W2 cases assembled")
    return cases, infos


def evaluate_w2_cases(phaseb_root: str, cases: Dict[str, dict], table: dict) -> Tuple[W2Context, SharedNullAsset]:
    """build_w2_context on the registered shared-null asset (trusted expected SHA = SHARED_NULL) with the registered m / master_seed and the exact POT distance."""
    asset = registered_shared_null_asset(phaseb_root); idn = asset.identity
    if int(idn["m"]) != RULES.m or int(idn["master_seed"]) != int(table["master_seed"]): raise InputContractError("shared-null asset m / master_seed differ from the registered rules / CRN table")
    ctx = build_w2_context(asset, cases, RULES.m, int(table["master_seed"]), dist=w2_exact, whitening_identity=idn["whitening"], expected_asset_sha256=SHARED_NULL["asset_sha256"])
    if ctx.scope != SCOPE_TRUSTED: raise InputContractError("W2 context scope is not the trusted scope")
    return ctx, asset


def case_record(ctx: W2Context, key: str, info: dict) -> dict:
    """Replayable per-case record: canonical manifest, raw result (evidence incl. observed pairwise values / subsets, null copy, bounds, stop, validation, trigger), the typed decision
    fields and the input identities (units, roots, whitening)."""
    ctx.validate(); fam, size = ctx.identities[key]; man = ctx.manifests[key]; d = ctx.decisions[key]; res = ctx.results[key]
    return dict(schema=CASE_SCHEMA, key=key, family=fam, size_id=size, asset_sha256=ctx.asset_sha256, manifest=man.as_dict(), manifest_sha256=man.payload_sha(), result=ser.to_jsonable(res), result_sha256=ctx.result_sha256[key],
                decision=dict(trigger=d.trigger, validation_state=d.validation_state, validation_reason=d.validation_reason, B_final=int(d.B_final), observed_hash=d.observed_hash, distance_kind=d.distance_kind, scope=d.scope, checksum=d.checksum),
                inputs=copy.deepcopy(info), constants=dict(m=RULES.m, n_subs=list(RULES.n_subs), seed_ids=list(RULES.seed_ids), B_levels=list(RULES.B_levels), first_comparison=list(RULES.first_comparison), rel_tol=RULES.rel_tol, seed_spread_max=RULES.seed_spread_max, quantile_method=RULES.quantile_method))


def context_record(ctx: W2Context, case_records: Dict[str, dict]) -> dict:
    ctx.validate()
    return dict(schema=CONTEXT_SCHEMA, asset_sha256=ctx.asset_sha256, context_sha256=ctx.context_sha256, scope=ctx.scope, summary=ctx.as_dict(), case_records={k: dict(manifest_sha256=r["manifest_sha256"], result_sha256=r["result_sha256"], decision_checksum=r["decision"]["checksum"], trigger=r["decision"]["trigger"], validation_state=r["decision"]["validation_state"], B_final=r["decision"]["B_final"]) for k, r in sorted(case_records.items())},
                shared_null=dict(SHARED_NULL), n_cases=len(case_records))


def restore_w2_context(case_records: List[dict], asset: SharedNullAsset, expected_context_sha256: Optional[str] = None, require_formal: bool = True) -> W2Context:
    """Rebuild the typed context from published / registered case records WITHOUT the bank arrays: for each record the manifest is re-typed, its payload SHA re-computed, the result's
    content SHA re-computed, and the decision is RE-ISSUED by verified_w2_for_decision (replay of stop / validation / trigger from the stored evidence against the shared-null
    asset; the execution-time bank identities come from RegisteredBankIdentity stand-ins built from the record's own evidence snapshot). The stored decision fields must equal
    the re-issued decision; the restored context SHA must equal the record / expected value. Technical-failure or unresolved states are preserved as such (never promoted)."""
    asset.validate()
    if not isinstance(case_records, (list, tuple)) or not case_records: raise InputContractError("no case records")
    decisions, manifests, idents, results = {}, {}, {}, {}
    for r in case_records:
        if not isinstance(r, dict) or r.get("schema") != CASE_SCHEMA: raise InputContractError("case record schema")
        key = r.get("key"); fam, size = canonical_case_key(key, {"size_id": r.get("size_id")})
        if (fam, size) != (r.get("family"), r.get("size_id")) or key in decisions: raise InputContractError(f"case {key!r}: identity / duplicate")
        if r.get("asset_sha256") != asset.sha256: raise InputContractError(f"case {key}: record bound to another shared-null asset")
        if require_formal and (r.get("inputs") or {}).get("formal") is not True: raise InputContractError(f"case {key}: not a formal case record")
        man = W2Manifest(**ser.from_jsonable(r["manifest"]))
        if man.payload_sha() != r.get("manifest_sha256") or (man.family, man.size_id) != (fam, size) or man.shared_null_sha256 != asset.sha256: raise InputContractError(f"case {key}: manifest SHA / identity / asset binding")
        res = ser.from_jsonable(r["result"])
        if _result_sha(res) != r.get("result_sha256"): raise InputContractError(f"case {key}: result content SHA")
        snap = (res.get("evidence") or {}).get("inputs") or {}
        if not isinstance(snap.get("positions"), list) or len(snap["positions"]) != 3: raise InputContractError(f"case {key}: evidence lacks the three execution-time bank identities")
        stand_ins = [RegisteredBankIdentity(p) for p in snap["positions"]]
        if require_formal:
            for st in stand_ins:
                if st.m != RULES.m or st.K * st.m != 200000: raise InputContractError(f"case {key}: position bank identity is not the formal W2 bank (K x m)")
        d = verified_w2_for_decision(man, stand_ins, SharedNullAssetRef(asset), res, require_registered_distance=require_formal)
        sd = r.get("decision") or {}
        if sd != dict(trigger=d.trigger, validation_state=d.validation_state, validation_reason=d.validation_reason, B_final=int(d.B_final), observed_hash=d.observed_hash, distance_kind=d.distance_kind, scope=d.scope, checksum=d.checksum): raise InputContractError(f"case {key}: stored decision differs from the re-issued replay decision")
        decisions[key] = d; manifests[key] = man; idents[key] = (fam, size); results[key] = res
    ctx = W2Context(asset.sha256, decisions, manifests, idents, results, SCOPE_TRUSTED); ctx.result_sha256 = {k: _result_sha(v) for k, v in results.items()}; ctx.context_sha256 = ctx.payload_sha(); ctx.validate(expected_context_sha256)
    return ctx


def load_registered_w2_context(phaseb_root: str, ctx):
    """Formal registered load (D4C-0 registration tranche): the body lives in d4c0_registry.load_registered_w2_context — pins (acceptance / context / ledger / receipt) and the
    registered original bytes are authenticated, then the typed context is restored with expected_context_sha256 taken from the authenticated pins and every decision compared
    with the registered constants. D2W_REGISTRATION mirrors the registration constants; a None value (pre-registration) is refused."""
    if D2W_REGISTRATION is None: raise InputContractError("D-2W W2 context is not registered yet")
    from .d4c0_registry import load_registered_w2_context as _load
    return _load(phaseb_root, ctx)


def _registration_constants():
    from .d4c0_registry import D2W
    return dict(attempt=D2W["attempt"], commit=D2W["execution_lock"]["commit"], engine_version=D2W["execution_lock"]["engine_version"], context_sha256=D2W["context_sha256"], acceptance_sha256=D2W["acceptance"]["sha256"], archive_sha256=D2W["archive"]["sha256"], executed_notebook_sha256=D2W["executed_notebook"]["sha256"])


D2W_REGISTRATION = _registration_constants()
