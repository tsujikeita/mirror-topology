# -*- coding: utf-8 -*-
"""D4-1: calibration-first driver (rules §9.4). Two entries with an ORDER RECORD:
  1. calibrate_sealed(...): runs the registered pseudo calibration on the fixed inputs WITHOUT receiving the observed target; only a COMMITMENT to the target is recorded
     (sha256 of the canonical target bytes || nonce); the run manifest (calibration, per-pseudo status, branch completeness, fingerprints, pseudo SHAs, commitment) is archived
     content-addressed as the sealed calibration record.
  2. evaluate_sealed_target(...): receives the sealed record reference, the target and the nonce; verifies the record bytes / payload SHA, the commitment (target || nonce),
     and that the inputs are the SAME (fingerprints, pseudo SHAs) before evaluating the target; the calibration is copied verbatim from the sealed record (never recomputed);
     the target run manifest carries the sealed record SHA as its parent.
Scope: the commitment + parent reference make the dependency order INSIDE this verified driver checkable; they do not prove that no target computation happened elsewhere,
nor wall-clock order, and the Step 0 target value is public knowledge (rules §0.2)."""
from __future__ import annotations
import hashlib, json, os
from typing import Optional
import numpy as np
from .errors import InputContractError
from .archive import Archive, ArchiveRef
from .integrated_runner import run_first_wave, RunManifest, _check_threshold2
from . import serialization as ser


def commit_target(t_target, nonce: str) -> str:
    """Commitment = sha256( canonical JSON of [t1, t2] as float64 repr || '|' || nonce ). nonce: >= 16 hex chars chosen by the author and kept private until the reveal."""
    t1, t2 = _check_threshold2(t_target)
    if not isinstance(nonce, str) or len(nonce) < 16: raise InputContractError("nonce must be a string of at least 16 characters")
    return hashlib.sha256((json.dumps([t1, t2]) + "|" + nonce).encode()).hexdigest()


def calibrate_sealed(reg, man, cases, w2_context, expected_context_sha256, pseudo_T1, pseudo_T2, archive: Archive, target_commitment: str, **kw) -> RunManifest:
    if not (isinstance(target_commitment, str) and len(target_commitment) == 64): raise InputContractError("target commitment must be a sha256 hex string")
    if "t_target" in kw: raise InputContractError("calibrate_sealed does not accept the observed target")
    return run_first_wave(reg, man, cases, w2_context, expected_context_sha256, None, pseudo_T1, pseudo_T2, archive, _stage="calibrate_sealed", _commitment=target_commitment, **kw)


def load_sealed_record(archive: Archive, ref: dict) -> dict:
    r = ArchiveRef(**ref); rec = archive.get(r)
    if r.kind != "transition" or r.identity.get("kind") != "sealed_calibration": raise InputContractError("reference is not a sealed calibration record")
    d = ser.from_jsonable(rec); body = dict(d); body["binding"] = {k: v for k, v in body["binding"].items() if k not in ("run_manifest_sha256", "run_manifest_file_sha256", "run_manifest_ref")}
    if hashlib.sha256(ser.dumps(body).encode()).hexdigest() != d["binding"]["run_manifest_sha256"]: raise InputContractError("sealed record payload SHA mismatch")
    if d.get("thresholds", {}).get("target") is not None or not d["thresholds"].get("target_commitment"): raise InputContractError("sealed record must not contain a target and must carry a commitment")
    d["_sha256"] = d["binding"]["run_manifest_sha256"]; d["_ref"] = ref; d["binding"]["run_manifest_sha256"] = d["_sha256"]; return d


def evaluate_sealed_target(reg, man, cases, w2_context, expected_context_sha256, t_target, nonce: str, pseudo_T1, pseudo_T2, archive: Archive, sealed_ref: dict, **kw) -> RunManifest:
    sealed = load_sealed_record(archive, sealed_ref)
    if commit_target(t_target, nonce) != sealed["thresholds"]["target_commitment"]: raise InputContractError("target / nonce do not match the sealed commitment")
    # RD4T2-B: the sealed record's whole reference chain (pseudo full Results, registry, W2 context / shared-null identity, source binding) is verified BEFORE any target evaluation
    from .run_reader import verify_run_references
    snap = w2_context.snapshot(); snap.validate(expected_context_sha256)
    v = verify_run_references(sealed, archive, registered=dict(shared_null_asset_sha256=snap.asset_sha256, w2_context_sha256=expected_context_sha256, registry_sha256=reg.registry_sha256, twelve_assets_sha256=(sealed.get("binding") or {}).get("twelve_assets_sha256")), current_source_binding=True)
    if not v.get("ok") or not v.get("registered_context_ok"): raise InputContractError("sealed calibration reference chain / registered context not verified")
    return run_first_wave(reg, man, cases, w2_context, expected_context_sha256, t_target, pseudo_T1, pseudo_T2, archive, _stage="sealed_target", _sealed=sealed, **kw)   # the order record is written inside the runner before the manifest is bound
