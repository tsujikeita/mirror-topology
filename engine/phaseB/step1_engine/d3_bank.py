# -*- coding: utf-8 -*-
"""D-3b (12-position bank generation) — generator / verifier / intake for the 81 ADDED configurations, bound to the accepted tranche 2b dependency (bank spec v2, covariance
receipt, TwelveContext). The numerical path is UNCHANGED from D-2: d2_rng.generate_from_latent on the SAME family evaluation / fitting latent (same CRN table, groups, keys,
UID order) with kernel.D_batch / kernel.scan; the roots are the configuration's matched / native principal roots and its native reference root from intake_twelve_covariance
(consumption-time re-verified). What differs from d2_bank is only the binding: configurations come from bank spec v2 (mode generate_D3b; f64 only, no W2), the covariance
identity from the 108-position receipt, and the manifests / sidecars carry the v2 identities (schema d3_bank_manifest_v1 / d3_bank_shard_v1: table SHA, D-2 canonical spec v1
SHA (latent identity), spec v2 SHA, covariance receipt SHA, position index, origin). The D-2 accepted family reference banks (ref_<F>_b0/b1/fit) and the 27 first-wave banks are
NEVER regenerated: the intake consumes them as fixed inputs through d2_bank.verify_bank_dir and cross-checks their manifest SHA against the D-2 ledger identities recorded in
spec v2 (d3_d2_reuse_binding_v1). Fresh-attempt / in-memory validation / validate-then-publish / read-once consumption contracts are the D-2 ones. No plan, calibration or label."""
from __future__ import annotations
import copy, hashlib, io, json, os
from typing import Dict, Optional
import numpy as np
from .errors import InputContractError
from .grid_manifest import FAMILY_CODES
from .registry import PURPOSE, STREAM, CRNRegistry
from . import d2_rng
from .d2_rng import group_for, generate_from_latent, BATCHES, N0, N_MAX, M
from .d2_bank import (_sha, _asha, _is_int, _atomic_write, _check_arrays, expected_member_set, shard_plan, EXPECTED_MEMBERS, CallInventory, verify_bank_dir, bind_generation_inputs, FIT_K, M_FIT, N_FIT, _load_role)
from .d3_profile import TwelveContext, _require_ctx, load_registered_bank_spec_v2, BANK_SPEC_V2_SCHEMA

MANIFEST_SCHEMA = "d3_bank_manifest_v1"; SHARD_SCHEMA = "d3_bank_shard_v1"
CONFIG_ROLES = ("model_matched", "model_native", "ref_native")


def _spec2(ctx: TwelveContext) -> dict:
    """The registered bank spec v2 of the context (pins identity + re-derivation)."""
    return load_registered_bank_spec_v2(_require_ctx(ctx))


def _entry(spec2: dict, config_id) -> dict:
    if not _is_int(config_id) or str(config_id) not in spec2["configurations"]: raise InputContractError("config_id not in bank spec v2")
    c = spec2["configurations"][str(config_id)]
    if c.get("mode") != "generate_D3b": raise InputContractError(f"config {config_id}: not a D-3b generation configuration (mode {c.get('mode')}); first-wave configurations are FIXED D-2 inputs")
    if c["covariance"].get("consumption_allowed") is not True or c["covariance"].get("pc1_status") != "PC1_PASS": raise InputContractError(f"config {config_id}: covariance not consumable ({c['covariance'].get('pc1_status')})")
    return c


def _bind(ctx: TwelveContext, registry: CRNRegistry):
    ctx = _require_ctx(ctx); table = ctx._d["table"]; spec1 = ctx._d["d2_spec"]; spec2 = _spec2(ctx)
    bind_generation_inputs(registry, table, spec1)
    if spec2["crn_table_sha256"] != table["table_sha256"] or not spec2["inherits"].endswith(spec1["spec_sha256"]) or spec2["covariance_receipt_sha256"] != ctx.identities["covariance_receipt_sha256"]: raise InputContractError("bank spec v2 is not bound to the context's table / D-2 spec / receipt")
    return table, spec1, spec2


def _identity(ctx: TwelveContext, spec1: dict, spec2: dict, table: dict) -> dict:
    return dict(table_sha256=table["table_sha256"], spec_v1_sha256=spec1["spec_sha256"], spec_v2_sha256=spec2["spec_sha256"], covariance_receipt_sha256=ctx.identities["covariance_receipt_sha256"], config_map_sha256=ctx.identities["config_map_sha256"], master_seed=table["master_seed"])


def generate_twelve_configuration_bank(kernel, registry: CRNRegistry, ctx: TwelveContext, config_id: int, roots: Dict[str, np.ndarray], batch_id: int, out_dir: str, inventory: CallInventory, selections=("float64",), scale: float = 1.0, chunk_clusters: int = d2_rng.CHUNK_CLUSTERS, env: Optional[dict] = None) -> dict:
    """ONE evaluation batch of ONE added configuration (spec v2 mode generate_D3b) into out_dir (fresh attempt). Formal (scale 1): selections must equal the spec v2 selections
    (float64 only). Same shard plan, in-memory validation, validate-then-publish as D-2."""
    if os.path.exists(out_dir): raise InputContractError("fresh-attempt contract: output directory must not exist")
    if not (isinstance(scale, (int, float)) and not isinstance(scale, bool) and 0 < scale <= 1): raise InputContractError("scale")
    if batch_id not in BATCHES: raise InputContractError("batch_id")
    table, spec1, spec2 = _bind(ctx, registry); c = _entry(spec2, config_id); fam = c["family"]
    sel = list(selections)
    if not sel or len(set(sel)) != len(sel) or any(x not in ("float64", "float32") for x in sel): raise InputContractError("selections")
    if scale == 1.0 and sel != c["selections"]["evaluation"][str(batch_id)]: raise InputContractError(f"selections {sel} differ from bank spec v2 for batch {batch_id}: {c['selections']['evaluation'][str(batch_id)]}")
    if tuple(sorted(roots)) != tuple(sorted(CONFIG_ROLES)): raise InputContractError(f"roles must be exactly {CONFIG_ROLES}")
    group = group_for(table, "evaluation", fam)
    if group != c["crn"]["evaluation_group"]: raise InputContractError("spec v2 evaluation group differs from the CRN table")
    K_full = (BATCHES[batch_id][1] - BATCHES[batch_id][0]) // M; shards = [sh for sh in shard_plan() if sh["batch_id"] == batch_id]; K = K_full if scale == 1.0 else int(round(K_full * scale))
    if K < 1 or K % len(shards) != 0: raise InputContractError(f"unsupported cluster count {K} for {len(shards)} shard(s)")
    K_shard = K // len(shards); offset_rows = BATCHES[batch_id][0]; offset_clusters = offset_rows // M
    root_sha = {r: _asha(np.asarray(S, float)) for r, S in roots.items()}; inventory.record(registry, "evaluation", group, batch_id, 0, K, sorted(roots), sel, chunk_clusters, table["table_sha256"])
    out, cid, uids = generate_from_latent(kernel, roots, registry, "evaluation", group, batch_id, K, tuple(sel), m=M, chunk_clusters=chunk_clusters)
    members = expected_member_set(sorted(roots), sel); ident = _identity(ctx, spec1, spec2, table)
    os.makedirs(out_dir); written = []
    for i, sh in enumerate(shards):
        k0, k1 = i * K_shard, (i + 1) * K_shard; r0, r1 = k0 * M, k1 * M; arrays = {"cid": np.ascontiguousarray(cid[r0:r1])}
        for (role, s_), d in out.items():
            for kk in EXPECTED_MEMBERS: arrays[f"{role}__{s_}__{kk}"] = np.ascontiguousarray(d[kk][r0:r1])
        _check_arrays(arrays, members, r1 - r0, k0, k1)
        buf = io.BytesIO(); np.savez(buf, **arrays); data = buf.getvalue(); fname = f"cfg{config_id}_b{batch_id}_s{sh['shard']}.npz"; p = os.path.join(out_dir, fname); _atomic_write(p, data)
        side = dict(schema=SHARD_SCHEMA, family=fam, config_id=int(config_id), kind="configuration", origin="twelve_added", position_index=c["position_index"], evaluation_ids=dict(c["evaluation_ids"]), purpose="evaluation", crn_group=group, wave_id=table["wave_id"], batch_id=batch_id, shard=sh["shard"],
                    rows=[r0, r1], clusters=[k0, k1], rotation_index=[k0, k1], global_rows=[offset_rows + r0, offset_rows + r1], global_clusters=[offset_clusters + k0, offset_clusters + k1], uids=[list(uids[k0].as_tuple()), list(uids[k1 - 1].as_tuple())], m=M, roles=sorted(roots), root_sha256=root_sha, selections=sel,
                    array_sha256={k: _asha(v) for k, v in arrays.items()}, file_sha256=_sha(data), bytes=len(data), **ident, scale=scale, formal=(scale == 1.0), environment=env or {}, dtype=dict(T1="float64", T2="float64", AX="int32", PL="int32"), covariance=copy.deepcopy(c["covariance"]))
        _atomic_write(p + ".sidecar.json", json.dumps(side, indent=1).encode()); written.append(dict(file=fname, sidecar=fname + ".sidecar.json", file_sha256=side["file_sha256"], sidecar_sha256=_sha(open(p + ".sidecar.json", "rb").read()), rows=[r0, r1]))
    manifest = dict(schema=MANIFEST_SCHEMA, family=fam, config_id=int(config_id), origin="twelve_added", position_index=c["position_index"], evaluation_ids=dict(c["evaluation_ids"]), purpose="evaluation", crn_group=group, wave_id=table["wave_id"], batch_id=batch_id, shards=written, roles=sorted(roots), root_sha256=root_sha, selections=sel, n_rows=K * M, n_clusters=K, m=M, complete=True, scale=scale, formal=(scale == 1.0), **ident, calls=inventory.calls[-1:])
    manifest["manifest_sha256"] = _sha(json.dumps({k: v for k, v in manifest.items() if k != "manifest_sha256"}, sort_keys=True).encode())
    _verify_twelve_bank_contents(out_dir, manifest, ctx, expected_roles=sorted(roots)); _atomic_write(os.path.join(out_dir, "COMPLETE.json"), json.dumps(manifest, indent=1).encode()); return manifest


def generate_twelve_fitting_bank(kernel, registry: CRNRegistry, ctx: TwelveContext, config_id: int, roots: Dict[str, np.ndarray], out_dir: str, inventory: CallInventory, scale: float = 1.0, chunk_clusters: int = d2_rng.CHUNK_CLUSTERS, env: Optional[dict] = None) -> dict:
    """Fitting bank of ONE added configuration: purpose fitting, family fitting group, batch 0, K = N_fit / m_fit, float64, one shard."""
    if os.path.exists(out_dir): raise InputContractError("fresh-attempt contract: output directory must not exist")
    if not (isinstance(scale, (int, float)) and not isinstance(scale, bool) and 0 < scale <= 1): raise InputContractError("scale")
    table, spec1, spec2 = _bind(ctx, registry); c = _entry(spec2, config_id); fam = c["family"]
    if tuple(sorted(roots)) != tuple(sorted(CONFIG_ROLES)): raise InputContractError(f"roles must be exactly {CONFIG_ROLES}")
    group = group_for(table, "fitting", fam)
    if group != c["crn"]["fitting_group"] or c["fitting"]["N"] != N_FIT or c["fitting"]["m"] != M_FIT: raise InputContractError("spec v2 fitting identity differs from the registered constants")
    K = FIT_K if scale == 1.0 else int(round(FIT_K * scale))
    if K < 1: raise InputContractError("cluster count")
    root_sha = {r: _asha(np.asarray(S, float)) for r, S in roots.items()}; inventory.record(registry, "fitting", group, 0, 0, K, sorted(roots), ["float64"], chunk_clusters, table["table_sha256"])
    out, cid, uids = generate_from_latent(kernel, roots, registry, "fitting", group, 0, K, ("float64",), m=M_FIT, chunk_clusters=chunk_clusters)
    members = expected_member_set(sorted(roots), ["float64"]); arrays = {"cid": np.ascontiguousarray(cid)}
    for (role, s_), d in out.items():
        for kk in EXPECTED_MEMBERS: arrays[f"{role}__{s_}__{kk}"] = np.ascontiguousarray(d[kk])
    _check_arrays(arrays, members, K * M_FIT, 0, K, M_FIT); ident = _identity(ctx, spec1, spec2, table)
    os.makedirs(out_dir); buf = io.BytesIO(); np.savez(buf, **arrays); data = buf.getvalue(); fname = f"cfg{config_id}_fit_s0.npz"; p = os.path.join(out_dir, fname); _atomic_write(p, data)
    side = dict(schema=SHARD_SCHEMA, family=fam, config_id=int(config_id), kind="configuration", origin="twelve_added", position_index=c["position_index"], evaluation_ids=dict(c["evaluation_ids"]), purpose="fitting", crn_group=group, wave_id=table["wave_id"], batch_id=0, shard=0, rows=[0, K * M_FIT], clusters=[0, K], rotation_index=[0, K], global_rows=[0, K * M_FIT], global_clusters=[0, K],
                uids=[list(uids[0].as_tuple()), list(uids[K - 1].as_tuple())], m=M_FIT, roles=sorted(roots), root_sha256=root_sha, selections=["float64"], array_sha256={k: _asha(v) for k, v in arrays.items()}, file_sha256=_sha(data), bytes=len(data), **ident, scale=scale, formal=(scale == 1.0), environment=env or {}, dtype=dict(T1="float64", T2="float64", AX="int32", PL="int32"), covariance=copy.deepcopy(c["covariance"]))
    _atomic_write(p + ".sidecar.json", json.dumps(side, indent=1).encode())
    manifest = dict(schema=MANIFEST_SCHEMA, family=fam, config_id=int(config_id), origin="twelve_added", position_index=c["position_index"], evaluation_ids=dict(c["evaluation_ids"]), purpose="fitting", crn_group=group, wave_id=table["wave_id"], batch_id=0, shards=[dict(file=fname, sidecar=fname + ".sidecar.json", file_sha256=side["file_sha256"], sidecar_sha256=_sha(open(p + ".sidecar.json", "rb").read()), rows=[0, K * M_FIT])],
                    roles=sorted(roots), root_sha256=root_sha, selections=["float64"], n_rows=K * M_FIT, n_clusters=K, m=M_FIT, complete=True, scale=scale, formal=(scale == 1.0), **ident, calls=inventory.calls[-1:])
    manifest["manifest_sha256"] = _sha(json.dumps({k: v for k, v in manifest.items() if k != "manifest_sha256"}, sort_keys=True).encode())
    _verify_twelve_bank_contents(out_dir, manifest, ctx, expected_roles=sorted(roots)); _atomic_write(os.path.join(out_dir, "COMPLETE.json"), json.dumps(manifest, indent=1).encode()); return manifest


def _verify_twelve_bank_contents(out_dir: str, man: dict, ctx: TwelveContext, expected_roles=None) -> None:
    """Writer/reader validator of an ADDED-configuration bank (mirror of d2_bank._verify_bank_contents bound to spec v2 / receipt instead of spec v1 / D-1): manifest schema / SHA /
    completeness; request schema (purpose, batch, K from batch + scale, selections vs spec v2 for formal, roles, identities vs the context: table / spec v1 / spec v2 / receipt /
    map / seed / wave; configuration identity, group, position, evaluation ids, covariance vs spec v2); one generation call with full six-element keys; every shard: bytes,
    sidecar <-> manifest identity, ranges, UID ends, member set, arrays (dtype / finiteness / cid structure / SHA)."""
    ctx = _require_ctx(ctx); table = ctx._d["table"]; spec1 = ctx._d["d2_spec"]; spec2 = _spec2(ctx); ident = _identity(ctx, spec1, spec2, table)
    body = {k: v for k, v in man.items() if k != "manifest_sha256"}
    if man.get("schema") != MANIFEST_SCHEMA or _sha(json.dumps(body, sort_keys=True).encode()) != man.get("manifest_sha256") or man.get("complete") is not True: raise InputContractError("D-3 bank manifest schema / SHA / completeness")
    roles, sels = man.get("roles"), man.get("selections")
    if not (isinstance(sels, list) and sels and len(set(sels)) == len(sels) and all(x in ("float64", "float32") for x in sels)): raise InputContractError("manifest selections")
    if not (isinstance(roles, list) and roles == sorted(CONFIG_ROLES)): raise InputContractError("D-3 bank roles must be exactly the configuration roles")
    if expected_roles is not None and sorted(roles) != sorted(expected_roles): raise InputContractError("bank roles differ")
    scale = man.get("scale")
    if not (isinstance(scale, (int, float)) and not isinstance(scale, bool) and np.isfinite(scale) and 0 < scale <= 1) or not isinstance(man.get("formal"), bool) or man["formal"] != (scale == 1.0): raise InputContractError("manifest scale / formal flag")
    purpose = man.get("purpose"); batch_id = man.get("batch_id")
    if purpose not in ("evaluation", "fitting") or batch_id not in BATCHES or man.get("m") != (M if purpose == "evaluation" else M_FIT): raise InputContractError("manifest constants")
    if purpose == "evaluation": K_full = (BATCHES[batch_id][1] - BATCHES[batch_id][0]) // M; n_sh = len([sh for sh in shard_plan() if sh["batch_id"] == batch_id]); mm = M
    else:
        if batch_id != 0 or sels != ["float64"]: raise InputContractError("fitting banks are batch 0 / float64 only")
        K_full = FIT_K; n_sh = 1; mm = M_FIT
    K_req = K_full if scale == 1.0 else int(round(K_full * scale))
    if not _is_int(man.get("n_clusters")) or man["n_clusters"] != K_req or K_req < 1 or K_req % n_sh != 0 or man.get("n_rows") != K_req * mm: raise InputContractError(f"manifest cluster count {man.get('n_clusters')} does not follow from purpose {purpose} / batch {batch_id} / scale {scale} (expected {K_req})")
    if any(man.get(k) != v for k, v in ident.items()) or man.get("wave_id") != table["wave_id"]: raise InputContractError("manifest identities (table / spec v1 / spec v2 / receipt / map / seed / wave) differ from the verified context")
    cid_ = man.get("config_id"); c = _entry(spec2, cid_) if _is_int(cid_) else None
    if c is None or man.get("family") != c["family"] or man.get("evaluation_ids") != c["evaluation_ids"] or man.get("origin") != "twelve_added" or man.get("position_index") != c["position_index"] or man.get("crn_group") != c["crn"]["evaluation_group" if purpose == "evaluation" else "fitting_group"]: raise InputContractError("manifest configuration identity / group / position differ from bank spec v2")
    if man["formal"] and purpose == "evaluation" and sels != c["selections"]["evaluation"][str(batch_id)]: raise InputContractError("formal manifest selections differ from bank spec v2")
    if not isinstance(man.get("root_sha256"), dict) or set(man["root_sha256"]) != set(roles) or any(not (isinstance(v, str) and len(v) == 64) for v in man["root_sha256"].values()): raise InputContractError("manifest root SHA table")
    calls = man.get("calls") or []
    if len(calls) != 1: raise InputContractError("manifest must carry exactly one generation call")
    call = calls[0]
    if call.get("purpose") != purpose or call.get("group") != man.get("crn_group") or call.get("batch_id") != batch_id or call.get("clusters") != [0, man["n_clusters"]] or sorted(call.get("roles") or []) != roles or list(call.get("selections") or []) != sels or call.get("table_sha256") != man.get("table_sha256"): raise InputContractError("generation call differs from the manifest identity")
    for key, stream in (("key_rotation", "rotation"), ("key_gaussian", "gaussian")):
        k = call.get(key); want = [man.get("master_seed"), man.get("wave_id"), PURPOSE[purpose], man["crn_group"], batch_id, STREAM[stream]]
        if not (isinstance(k, list) and len(k) == 6 and all(_is_int(x) for x in k) and k == want): raise InputContractError(f"generation call {key} differs from the manifest identity")
    if not _is_int(call.get("chunk_clusters")) or call["chunk_clusters"] < 1: raise InputContractError("generation call chunk must be a positive integer")
    members = expected_member_set(roles, sels); r_expect = 0; k_expect = 0; shards = man.get("shards") or []
    plan = [sh for sh in shard_plan() if sh["batch_id"] == batch_id] if purpose == "evaluation" else [dict(shard=0, batch_id=0)]
    if len(shards) != len(plan): raise InputContractError("shard count differs from the plan")
    for sh, pl in zip(shards, plan):
        p = os.path.join(out_dir, sh["file"]); sp = os.path.join(out_dir, sh["sidecar"])
        if not (os.path.exists(p) and os.path.exists(sp)): raise InputContractError(f"shard {sh['file']}: missing")
        data = open(p, "rb").read(); sbytes = open(sp, "rb").read()
        if _sha(data) != sh["file_sha256"] or _sha(sbytes) != sh["sidecar_sha256"]: raise InputContractError(f"shard {sh['file']}: bytes differ from the manifest")
        side = json.loads(sbytes.decode("utf-8"))
        for k in ("family", "config_id", "origin", "position_index", "evaluation_ids", "purpose", "crn_group", "wave_id", "batch_id", "roles", "selections", "scale", "formal", "root_sha256") + tuple(ident):
            if side.get(k) != man.get(k): raise InputContractError(f"shard {sh['file']}: sidecar field {k} differs from the manifest")
        if side.get("schema") != SHARD_SCHEMA or side.get("kind") != "configuration" or side.get("dtype") != dict(T1="float64", T2="float64", AX="int32", PL="int32") or side.get("covariance") != c["covariance"]: raise InputContractError(f"shard {sh['file']}: sidecar schema / kind / dtype / covariance identity")
        if side.get("shard") != pl["shard"] or side.get("m") != mm or side.get("file_sha256") != sh["file_sha256"] or side.get("rows") != sh["rows"] or side.get("bytes") != len(data): raise InputContractError(f"shard {sh['file']}: shard identity")
        r0, r1 = side["rows"]; k0, k1 = side["clusters"]
        if r0 != r_expect or k0 != k_expect or r1 - r0 != (k1 - k0) * mm or k1 <= k0 or side.get("rotation_index") != [k0, k1]: raise InputContractError(f"shard {sh['file']}: ranges not contiguous / consistent")
        off_r, off_k = (BATCHES[batch_id][0], BATCHES[batch_id][0] // M) if purpose == "evaluation" else (0, 0)
        if side.get("global_rows") != [off_r + r0, off_r + r1] or side.get("global_clusters") != [off_k + k0, off_k + k1]: raise InputContractError(f"shard {sh['file']}: global ranges")
        exp_u0 = [man["wave_id"], PURPOSE[purpose], man["crn_group"], batch_id, k0]; exp_u1 = exp_u0[:4] + [k1 - 1]
        if side.get("uids") != [exp_u0, exp_u1]: raise InputContractError(f"shard {sh['file']}: UID ends differ from the batch / rotation range")
        if set(side.get("array_sha256") or {}) != members: raise InputContractError(f"shard {sh['file']}: sidecar member set")
        with np.load(io.BytesIO(data), allow_pickle=False) as z:
            if set(z.files) != members: raise InputContractError(f"shard {sh['file']}: NPZ member set")
            arrays = {k: z[k] for k in z.files}
        _check_arrays(arrays, members, r1 - r0, k0, k1, mm)
        for k, s_ in side["array_sha256"].items():
            if _asha(arrays[k]) != s_: raise InputContractError(f"shard {sh['file']}: array {k} differs from its sidecar")
        r_expect, k_expect = r1, k1
    if r_expect != man["n_rows"] or k_expect != man["n_clusters"]: raise InputContractError("shards do not cover the manifest rows / clusters")


def verify_twelve_bank_dir(out_dir: str, ctx: TwelveContext, expected_roles=None) -> dict:
    """Full re-verification of a COMPLETED added-configuration bank directory (the ONLY route to reuse): manifest, every shard's bytes / sidecar / arrays / ranges / identity vs the context."""
    mp = os.path.join(out_dir, "COMPLETE.json")
    if not os.path.exists(mp): raise InputContractError("bank directory is not complete (no completion manifest)")
    man = json.load(open(mp)); _verify_twelve_bank_contents(out_dir, man, ctx, expected_roles); return man


def verify_reused_reference_dir(dir_: str, ctx: TwelveContext, family: str, unit: str) -> dict:
    """A D-2 accepted family reference directory consumed as a FIXED input: re-verified by the D-2 verifier (canonical spec v1) AND its completion manifest SHA / rows / purpose must
    equal the D-2 ledger identity recorded in bank spec v2 (d3_d2_reuse_binding_v1: never re-stamped, never regenerated)."""
    ctx = _require_ctx(ctx); spec2 = _spec2(ctx)
    if family not in ("E2", "E7", "E8") or unit not in (f"ref_{family}_b0", f"ref_{family}_b1", f"ref_{family}_fit"): raise InputContractError("reference unit name")
    want = spec2["family_reference"][family]["units"][unit]; man = verify_bank_dir(dir_, ("ref_matched",))
    if man["manifest_sha256"] != want["manifest_sha256"] or man["n_rows"] != want["n_rows"] or man["purpose"] != want["purpose"] or man["family"] != family or man["config_id"] is not None or not man["formal"]: raise InputContractError(f"{unit}: directory is not the accepted D-2 reference unit recorded in bank spec v2")
    return man


def intake_twelve_bank(config_id: int, system: str, eval_dirs: Dict[int, str], ref_dirs: Dict[int, str], fit_dir: str, ref_fit_dir: str, roots: Dict[str, np.ndarray], ctx: TwelveContext, formal: bool = True, registered_units=None):
    """STRONG intake of ONE added configuration for the 12-position profile: configuration directories re-verified against the context (verify_twelve_bank_dir), the D-2 family
    reference directories re-verified by the D-2 verifier and bound to the ledger identities of spec v2 (fixed inputs), roots == the caller's intake_twelve_covariance roots /
    PR3 isotropic root, reference and configuration on the same latent (identical cid per batch), fitting paired, formal flags. Returns (BankSupply, info); the BankSupply's
    cov_manifest is the receipt identity (file / array SHA, receipt, PC-1 status) so that d3_profile.build_twelve_size_input can bind it.
    formal=True additionally requires registered_units (d3b_ledger.intake_registered_d3b_units): each consumed configuration directory must be one of the ACCEPTED D-3b units
    (manifest SHA / rows / purpose equal to the generation ledger) — a directory that merely re-verifies against the context is not a registered bank."""
    from .production import BankSupply; from .orchestrator import FittingBank
    ctx = _require_ctx(ctx); table = ctx._d["table"]; spec2 = _spec2(ctx)
    if system not in ("matched", "native"): raise InputContractError("system")
    if not isinstance(formal, (bool, np.bool_)): raise InputContractError("formal must be a boolean")
    formal = bool(formal); c = _entry(spec2, config_id); fam = c["family"]; model_role = f"model_{system}"
    required_roots = ("model_matched", "model_native", "ref_native", "ref_matched")
    if not isinstance(roots, dict) or any(r not in roots for r in required_roots): raise InputContractError("caller must supply the four roots (intake_twelve_covariance + PR3 isotropic)")
    want = {}
    for r in required_roots:
        a = np.asarray(roots[r])
        if a.shape != (21, 21) or a.dtype.kind not in "iuf" or not np.isfinite(a).all(): raise InputContractError(f"root {r}: expected a finite real numeric 21x21 matrix")
        want[r] = _asha(np.array(a, dtype=np.float64, order="C", copy=True))
    if set(eval_dirs) != {0, 1} or set(ref_dirs) != {0, 1}: raise InputContractError("evaluation / reference batches {0, 1} are both required")
    if formal:
        from .d3b_ledger import D3bUnits
        if not isinstance(registered_units, D3bUnits) or not registered_units.verified: raise InputContractError("formal intake requires the registered D-3b units (d3b_ledger.intake_registered_d3b_units)")
        if registered_units.array_accepted is not True: raise InputContractError("formal intake requires the array-verified acceptance (registered outer receipt bound to the ledger)")
    mans = {b: verify_twelve_bank_dir(eval_dirs[b], ctx, sorted(CONFIG_ROLES)) for b in (0, 1)}; fman = verify_twelve_bank_dir(fit_dir, ctx, sorted(CONFIG_ROLES))
    if formal:
        for b in (0, 1): registered_units.require_unit_manifest(f"cfg{config_id}_b{b}", mans[b]["manifest_sha256"], mans[b]["n_rows"], "evaluation")
        registered_units.require_unit_manifest(f"cfg{config_id}_fit", fman["manifest_sha256"], fman["n_rows"], "fitting")
        rmans = {b: verify_reused_reference_dir(ref_dirs[b], ctx, fam, f"ref_{fam}_b{b}") for b in (0, 1)}; rfman = verify_reused_reference_dir(ref_fit_dir, ctx, fam, f"ref_{fam}_fit")
    else:
        rmans = {b: verify_bank_dir(ref_dirs[b], ("ref_matched",)) for b in (0, 1)}; rfman = verify_bank_dir(ref_fit_dir, ("ref_matched",))
    for b in (0, 1):
        m_ = mans[b]
        if m_["batch_id"] != b or m_["purpose"] != "evaluation" or m_["config_id"] != config_id or (formal and not m_["formal"]): raise InputContractError(f"evaluation batch {b}: identity / formal")
        r_ = rmans[b]
        if r_["batch_id"] != b or r_["purpose"] != "evaluation" or r_["family"] != fam or r_["crn_group"] != c["crn"]["evaluation_group"] or r_["table_sha256"] != table["table_sha256"] or (formal and not r_["formal"]): raise InputContractError(f"reference batch {b}: identity differs from the configuration / table")
        if m_["n_clusters"] != r_["n_clusters"] or m_["scale"] != r_["scale"]: raise InputContractError(f"batch {b}: reference and configuration banks are not on the same latent range")
    if mans[1]["n_clusters"] != 3 * mans[0]["n_clusters"] or mans[1]["n_rows"] != 3 * mans[0]["n_rows"] or mans[1]["scale"] != mans[0]["scale"]: raise InputContractError("evaluation batches must be one common-scale N0 prefix plus a 3*N0 extension")
    if fman["purpose"] != "fitting" or fman["config_id"] != config_id or (formal and not fman["formal"]) or rfman["purpose"] != "fitting" or rfman["family"] != fam or rfman["crn_group"] != c["crn"]["fitting_group"] or fman["n_clusters"] != rfman["n_clusters"]: raise InputContractError("fitting banks are not paired for this configuration")
    for m_ in (mans[0], mans[1], fman):
        if any(m_["root_sha256"][r] != want[r] for r in CONFIG_ROLES): raise InputContractError("stored configuration roots differ from the caller's intake roots")
    for m_ in (rmans[0], rmans[1], rfman):
        if m_["root_sha256"]["ref_matched"] != want["ref_matched"]: raise InputContractError("stored reference root differs from the caller's isotropic root")
    T1m, T2m, T1r, T2r, uids, batches = [], [], [], [], [], {}; off = 0
    for b in (0, 1):
        em = _load_role(eval_dirs[b], mans[b], model_role); rr = _load_role(ref_dirs[b], rmans[b], "ref_matched") if system == "matched" else _load_role(eval_dirs[b], mans[b], "ref_native")
        if not np.array_equal(em["cid"], rr["cid"]): raise InputContractError(f"batch {b}: model / reference cluster structure differ")
        n = len(em["cid"]); T1m.append(em["T1"]); T2m.append(em["T2"]); T1r.append(rr["T1"]); T2r.append(rr["T2"]); batches[b] = (off, off + n); off += n
        uids += [CRNRegistry.cluster_uid(table["wave_id"], "evaluation", c["crn"]["evaluation_group"], b, i) for i in range(mans[b]["n_clusters"])]
    fm = _load_role(fit_dir, fman, model_role); fr = _load_role(ref_fit_dir, rfman, "ref_matched") if system == "matched" else _load_role(fit_dir, fman, "ref_native")
    if not np.array_equal(fm["cid"], fr["cid"]): raise InputContractError("fitting model / reference cluster structure differ")
    fit = FittingBank(np.c_[fm["T1"], fm["T2"]], np.c_[fr["T1"], fr["T2"]], fm["cid"].astype(np.int64))
    cov = dict(cov_file_sha256=c["covariance"]["cov_file_sha256"], cov_array_sha256=c["covariance"]["cov_array_sha256"], receipt=c["covariance"]["receipt"], pc1_status=c["covariance"]["pc1_status"], registered_file=c["covariance"]["registered_file"], covariance_receipt_sha256=ctx.identities["covariance_receipt_sha256"])
    supply = BankSupply(int(config_id), system, np.concatenate(T1m), np.concatenate(T2m), np.concatenate(T1r), np.concatenate(T2r), uids, M, batches, fit, cov_manifest=cov, cov_npy_path=None)
    return supply, dict(scope="strong intake: added-configuration directories re-verified against the context (spec v2 / receipt / table) and bound to the D-3b generation ledger (formal), D-2 reference directories re-verified and ledger-bound (formal), roots == caller's, same latent, fitting paired; formal=%s" % formal, d3b_ledger_sha256=(registered_units.ledger_sha256 if formal else None), d3b_receipt_sha256=(registered_units.receipt_sha256 if formal else None), batches=batches, n_clusters={b: mans[b]["n_clusters"] for b in (0, 1)}, fitting_clusters=fman["n_clusters"], manifests=dict(eval={b: mans[b]["manifest_sha256"] for b in (0, 1)}, ref={b: rmans[b]["manifest_sha256"] for b in (0, 1)}, fit=fman["manifest_sha256"], ref_fit=rfman["manifest_sha256"]))
