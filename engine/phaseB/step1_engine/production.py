# -*- coding: utf-8 -*-
"""Production wrapper (rules §4.7, §13): the only registered way to build FamilyInputs for formal evaluation. It takes a source-bound GridRegistry, builds/validates the
ConfigurationManifest, fixes the evaluation-id map (config_id for matched, config_id + NATIVE_OFFSET for native — an explicit registered table, not an inference), binds every
supplied bank to its configuration (cache key / covariance manifest verified when supplied), sets configuration weights from the manifest and carries the identity
(registry SHA, manifest SHA, evaluation_id -> config_id) into FamilyInput.grid_identity so that evaluate_family stores it in evidence. Nothing here generates banks."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import hashlib, json
import numpy as np
from .errors import InputContractError
from .grid_registry import GridRegistry
from .grid_manifest import ConfigurationManifest, ConfigurationSpec, build_configuration_manifest, verify_cov_manifest, FAMILY_CODES, SIZE_CODES, _sha_field, _integer
from .grid_registry import POSITIONS, FAMILIES
from .orchestrator import ConfigBank, FittingBank, FamilyInput
from .bootstrap_plan import BootstrapPlan, bank_sha256
from . import serialization as ser

NATIVE_OFFSET = 50000
SYSTEMS = ("matched", "native")


@dataclass
class EvaluationIdMap:
    manifest_sha256: str; matched: Dict[int, int]; native: Dict[int, int]     # config_id -> evaluation_id
    def as_dict(self): return ser.to_jsonable(asdict(self))
    def validate(self, man: ConfigurationManifest):
        if not isinstance(man, ConfigurationManifest): raise InputContractError("configuration manifest type")
        man.validate()
        if not isinstance(self.matched, dict) or not isinstance(self.native, dict): raise InputContractError("id maps must be mappings")
        for table in (self.matched, self.native):
            for k, v in table.items():
                _integer(k, "config id"); _integer(v, "evaluation id")
        ids = {c.config_id for c in man.configurations}
        if set(self.matched) != ids or set(self.native) != ids: raise InputContractError("evaluation id map must cover exactly the manifest configurations")
        if any(self.matched[c] != c for c in ids) or any(self.native[c] != c + NATIVE_OFFSET for c in ids): raise InputContractError("registered id map: matched = config_id, native = config_id + NATIVE_OFFSET")
        if set(self.matched.values()) & set(self.native.values()): raise InputContractError("matched/native evaluation ids overlap")
        if self.manifest_sha256 != man.manifest_sha256: raise InputContractError("id map is bound to a different manifest")
        return True


def registered_id_map(man: ConfigurationManifest) -> EvaluationIdMap:
    if not isinstance(man, ConfigurationManifest): raise InputContractError("configuration manifest type")
    man.validate()
    m = EvaluationIdMap(man.manifest_sha256, {c.config_id: c.config_id for c in man.configurations}, {c.config_id: c.config_id + NATIVE_OFFSET for c in man.configurations}); m.validate(man); return m


def _production_context(reg: GridRegistry, man: Optional[ConfigurationManifest] = None):
    """Revalidate the supplied source-bound object and its derived metadata.
    Scope labels are NOT signatures. Caller-side source authentication remains
    the SHA-verified asset loader / source-bound restoration contract.
    """
    if not isinstance(reg, GridRegistry): raise InputContractError("production registry type")
    reg.validate()
    if reg.verification_scope not in ("constructed_from_verified_assets", "source_bound (re-derived from SHA-verified A6/A7)"):
        raise InputContractError("production requires a source-bound registry")
    expected = build_configuration_manifest(reg)
    if man is not None:
        if not isinstance(man, ConfigurationManifest): raise InputContractError("configuration manifest type")
        man.validate()
        if man.as_dict() != expected.as_dict():
            raise InputContractError("configuration manifest is not the derivation of the supplied registry")
    return expected


def production_manifest(reg: GridRegistry) -> ConfigurationManifest:
    return _production_context(reg)


@dataclass
class BankSupply:
    """Per-configuration realisation banks supplied to the wrapper (produced elsewhere; identity verified here)."""
    config_id: int; system: str; T1_model: np.ndarray; T2_model: np.ndarray; T1_ref: np.ndarray; T2_ref: np.ndarray; cluster_uids: list; m: int; batches: dict
    fitting: FittingBank; cov_manifest: Optional[dict] = None; cov_npy_path: Optional[str] = None


def build_family_input(reg: GridRegistry, man: ConfigurationManifest, family: str, system: str, supplies: List[BankSupply], plans: Dict[int, BootstrapPlan], fit_plans: dict, size_ids: Optional[List[str]] = None) -> FamilyInput:
    """FamilyInput for ONE family and ONE system: exact configuration inventory (all surviving configurations of the family, or the given sizes), weights from the manifest
    (renormalised over the selected sizes ONLY through the registered size prior, never ad hoc), evaluation ids from the registered map, covariance metadata bound when supplied."""
    if system not in SYSTEMS: raise InputContractError("system")
    if family not in FAMILIES: raise InputContractError("family")
    _production_context(reg, man)
    if size_ids is not None:
        if (not isinstance(size_ids, (list, tuple)) or not size_ids or
                any(not isinstance(v, str) or not v for v in size_ids) or len(set(size_ids)) != len(size_ids)):
            raise InputContractError("size_ids must be a non-empty unique list of size strings")
    if not isinstance(supplies, (list, tuple)) or not supplies: raise InputContractError("bank supplies must be a non-empty sequence")
    supply_ids = []
    for supply in supplies:
        if not isinstance(supply, BankSupply): raise InputContractError("bank supply type")
        supply_ids.append(_integer(supply.config_id, "supply config_id"))
    if len(set(supply_ids)) != len(supply_ids): raise InputContractError("duplicate supply configuration: no last-wins conversion is allowed")
    idmap = registered_id_map(man)
    if man.registry_sha256 != reg.registry_sha256: raise InputContractError("manifest is not bound to the supplied registry")
    want = [c for c in man.configurations if c.family == family and (size_ids is None or c.size_id in size_ids)]
    if not want: raise InputContractError("no registered configurations for the requested family/sizes")
    if size_ids is not None and set(size_ids) - set(reg.surviving[family]): raise InputContractError("requested sizes are not surviving sizes of the registry")
    by_id = {c.config_id: c for c in want}; got = {s.config_id: s for s in supplies}
    if set(got) != set(by_id): raise InputContractError(f"bank supply inventory must equal the configuration inventory {sorted(by_id)}")
    sizes = sorted({c.size_id for c in want}); size_w = {s: reg.size_prior[family][s] for s in sizes}; tot = sum(size_w.values())
    if size_ids is not None and len(sizes) != len(reg.surviving[family]): size_w = {s: w / tot for s, w in size_w.items()}   # registered size prior conditioned on the selected sizes (recorded)
    cfgs, fit, bind, id2cfg, cov = [], {}, {}, {}, {}
    for cid, spec in by_id.items():
        s = got[cid]
        if s.system != system: raise InputContractError(f"supply {cid} is for system {s.system}, requested {system}")
        eid = (idmap.matched if system == "matched" else idmap.native)[cid]; npos = sum(1 for c in want if c.size_id == spec.size_id)
        w = size_w[spec.size_id] / npos
        cfgs.append(ConfigBank(eid, family, system, w, s.T1_model, s.T2_model, s.T1_ref, s.T2_ref, s.cluster_uids, s.m, s.batches)); fit[eid] = s.fitting; bind[eid] = bank_sha256(s.fitting.X_model, s.fitting.X_ref, s.fitting.cid); id2cfg[eid] = cid
        if s.cov_manifest is not None: cov[eid] = verify_cov_manifest(spec, s.cov_manifest, s.cov_npy_path)
    ident = dict(registry_sha256=reg.registry_sha256, manifest_sha256=man.manifest_sha256, family=family, system=system, sizes=sizes, size_weights=size_w, evaluation_to_config={int(k): int(v) for k, v in id2cfg.items()}, cache_keys={int(e): by_id[c].cache_key for e, c in id2cfg.items()}, cov_bound={int(e): v for e, v in cov.items()}, id_map_rule=f"matched=config_id; native=config_id+{NATIVE_OFFSET}")
    fam = FamilyInput(family, cfgs, plans, fit, fit_plans, True, bind, ident); fam.validate(); return fam


_GRID_FIELDS = {"registry_sha256", "manifest_sha256", "family", "system", "sizes", "size_weights", "evaluation_to_config", "cache_keys", "cov_bound", "id_map_rule"}


def validate_grid_identity(gi, family, system, evaluation_ids, prior=None):
    """Internal correspondence only; not physical-bank or external-source authentication.
    A None identity denotes the unchanged legacy/synthetic path.
    Conditional size subsets remain diagnostic inputs, not formal full-family release.
    """
    if gi is None: return True
    if not isinstance(gi, dict) or set(gi) != _GRID_FIELDS:
        raise InputContractError("grid identity field inventory")
    if family not in FAMILIES or system not in SYSTEMS or gi["family"] != family or gi["system"] != system:
        raise InputContractError("grid identity family/system mismatch")
    for key in ("registry_sha256", "manifest_sha256"): _sha_field(gi[key], key)
    sizes = gi["sizes"]
    if (not isinstance(sizes, list) or not sizes or any(not isinstance(v, str) for v in sizes)
            or len(set(sizes)) != len(sizes) or not set(sizes) <= set(SIZE_CODES)):
        raise InputContractError("grid identity size inventory")
    sw = gi["size_weights"]
    if not isinstance(sw, dict) or set(sw) != set(sizes): raise InputContractError("grid identity size weights inventory")
    for v in sw.values():
        if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int,float,np.integer,np.floating)) or not np.isfinite(v) or abs(float(v)-1/len(sizes))>1e-15:
            raise InputContractError("grid identity size weights differ from the selected registered equal prior")
    npos=POSITIONS[family]; offset=0 if system=="matched" else NATIVE_OFFSET
    conf_to_size={10000*FAMILY_CODES[family]+100*SIZE_CODES[z]+j+1:z for z in sizes for j in range(npos)}
    expected={cid+offset:cid for cid in conf_to_size}
    mp=gi["evaluation_to_config"]
    if not isinstance(mp,dict): raise InputContractError("grid identity evaluation mapping")
    for k,v in mp.items(): _integer(k,"evaluation id"); _integer(v,"config id")
    ids=[_integer(v,"evaluation id") for v in evaluation_ids]
    if len(set(ids))!=len(ids) or set(ids)!=set(expected) or mp!=expected:
        raise InputContractError("grid identity mapping does not describe the evaluated configurations")
    if gi["id_map_rule"] != f"matched=config_id; native=config_id+{NATIVE_OFFSET}":
        raise InputContractError("grid identity id rule mismatch")
    keys=gi["cache_keys"]
    if not isinstance(keys,dict) or set(keys)!=set(expected): raise InputContractError("grid identity cache-key inventory")
    for key in keys.values(): _sha_field(key,"geometry key")
    cb=gi["cov_bound"]
    if not isinstance(cb,dict) or not set(cb)<=set(expected): raise InputContractError("grid identity covariance inventory")
    for e,v in cb.items():
        if not isinstance(v,dict) or v.get("config_id")!=expected[e] or v.get("cache_key")!=keys[e] or v.get("bound") is not True:
            raise InputContractError("grid identity covariance binding mismatch")
        _sha_field(v.get("cov_array_sha256"),"covariance array SHA")
    if prior is not None:
        arr=np.asarray(prior,dtype=float); want=np.asarray([sw[conf_to_size[expected[e]]]/npos for e in ids])
        if arr.shape!=want.shape or not np.all(np.isfinite(arr)) or not np.allclose(arr,want,rtol=0,atol=1e-15):
            raise InputContractError("grid identity does not reproduce the actual numerical prior")
    return True


def validate_grid_pair(gm, gn):
    if gm is None and gn is None: return True
    if gm is None or gn is None: raise InputContractError("paired registered inputs require both grid identities")
    for key in ("registry_sha256", "manifest_sha256", "family", "size_weights"):
        if gm[key] != gn[key]: raise InputContractError(f"matched/native grid identities disagree: {key}")
    if set(gm["sizes"]) != set(gn["sizes"]): raise InputContractError("matched/native are conditioned on different sizes")
    return True


def validate_grid_archive(res):
    """Cheap content validation of new grid fields, conditional on stored evidence.
    Does not claim that metadata caused the supplied T arrays, nor revalidate
    external covariance, source assets, or formal execution profile.
    """
    ev=res.get("evidence") or {}; gm=ev.get("grid_identity")
    nv=res.get("native"); ne=(nv.get("evidence") or {}) if isinstance(nv,dict) else {}; gn=ne.get("grid_identity")
    if gm is None and gn is None: return True
    validate_grid_identity(gm,res.get("family"),"matched",res.get("per_config",{}), (ev.get("matched") or {}).get("prior"))
    if nv is not None:
        validate_grid_identity(gn,res.get("family"),"native",nv.get("per_config",{}),ne.get("prior"))
        validate_grid_pair(gm,gn)
    return True
