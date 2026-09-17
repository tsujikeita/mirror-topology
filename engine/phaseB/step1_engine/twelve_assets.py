# -*- coding: utf-8 -*-
"""Fixed designs: full source-bound asset intake, then content-checked reuse.

A manifest's regeneration receipt and an enclosing asset's intake receipt have
separate meanings. Receipts are process-local integrity metadata, not signatures.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional
import copy, hashlib, json
import numpy as np
from .errors import InputContractError
from .grid_registry import GridRegistry
from . import stage12
from .stage12 import TwelvePositionManifest, generate_twelve, verify_twelve, N_TOTAL
from . import serialization as ser

_VERIFIED: set = set()

def _sha(value):
    return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)

def _registry(reg):
    if not isinstance(reg,GridRegistry): raise InputContractError('twelve assets require GridRegistry')
    reg.validate(); scope=reg.verification_scope
    if not isinstance(scope,str) or not (scope.startswith('source_bound') or scope=='constructed_from_verified_assets'):
        raise InputContractError('twelve assets require a source-bound registry')

def verify_twelve_cached(man: TwelvePositionManifest, regenerate: Optional[bool]=None) -> bool:
    """False is reuse-only, not disable-verification: a cache miss is rejected."""
    if regenerate is not None and type(regenerate) is not bool: raise InputContractError('regenerate must be None or bool')
    stage12._structural_checks(man)
    if regenerate is not True and man.sha256 in _VERIFIED: return True
    if regenerate is False: raise InputContractError('manifest has no successful regeneration receipt')
    verify_twelve(man); _VERIFIED.add(man.sha256); return True

@dataclass
class TwelveManifestAsset:
    registry_sha256: str
    generator: dict
    manifests: Dict[str,Dict[str,TwelvePositionManifest]]
    families: list
    sha256: str=''
    verification: dict=field(default_factory=dict)
    _intake_sha256: Optional[str]=field(default=None,init=False,repr=False,compare=False)

    def payload_sha(self) -> str:
        body=dict(registry_sha256=self.registry_sha256,generator=self.generator,families=list(self.families),
            manifests={f:{s:m.payload() for s,m in sorted(sz.items())} for f,sz in sorted(self.manifests.items())},
            manifest_sha={f:{s:m.sha256 for s,m in sorted(sz.items())} for f,sz in sorted(self.manifests.items())})
        return hashlib.sha256(json.dumps(ser.to_jsonable(body),sort_keys=True).encode()).hexdigest()

    def as_dict(self):
        return ser.to_jsonable(dict(registry_sha256=self.registry_sha256,generator=self.generator,families=list(self.families),
            manifests={f:{s:m.as_dict() for s,m in sz.items()} for f,sz in self.manifests.items()},sha256=self.sha256,verification=self.verification))

    def validate(self,reg:Optional[GridRegistry]=None,expected_sha256:Optional[str]=None,*,require_intake=True) -> bool:
        if not _sha(self.registry_sha256) or not _sha(self.sha256): raise InputContractError('asset requires registry and payload SHA256')
        if expected_sha256 is not None and (not _sha(expected_sha256) or self.sha256!=expected_sha256): raise InputContractError('twelve asset SHA differs from the expected value')
        if not isinstance(self.families,list) or not self.families or any(not isinstance(f,str) or f not in stage12.BOX for f in self.families):
            raise InputContractError('asset families must be a nonempty list of registered non-E1 families')
        if len(set(self.families))!=len(self.families): raise InputContractError('duplicate family in asset')
        if not isinstance(self.manifests,dict) or set(self.manifests)!=set(self.families): raise InputContractError('asset family mapping inventory differs from families')
        if self.generator!=dict(stage12.GENERATOR,streamed_families=list(stage12.STREAMED_FAMILIES)):
            raise InputContractError('asset generator settings differ from registered settings')
        if reg is not None:
            _registry(reg)
            if self.registry_sha256!=reg.registry_sha256: raise InputContractError('twelve asset is bound to a different registry')
        for f in self.families:
            sizes=self.manifests[f]
            if not isinstance(sizes,dict) or not sizes or any(not isinstance(s,str) or not s for s in sizes): raise InputContractError('asset sizes must be nonempty string-keyed mappings')
            if reg is not None and set(sizes)!=set(reg.surviving[f]): raise InputContractError(f'asset {f}: surviving size inventory differs')
            for s,m in sizes.items():
                if not isinstance(m,TwelvePositionManifest) or (m.family,m.size_id)!=(f,s): raise InputContractError(f'asset {f}/{s}: manifest identity differs')
                stage12._structural_checks(m)
                if reg is not None and m.anchors!=[[float(x) for x in p] for p in reg.anchors[f]]: raise InputContractError(f'asset {f}/{s}: anchors differ from registry')
        if self.sha256!=self.payload_sha(): raise InputContractError('twelve asset SHA does not match its payload')
        if require_intake:
            if self._intake_sha256!=self.sha256: raise InputContractError('asset has not successfully passed whole-asset intake in this process')
            if any(m.sha256 not in _VERIFIED for sz in self.manifests.values() for m in sz.values()): raise InputContractError('asset manifest has not been regeneration-verified in this process')
        return True

    def snapshot(self,reg:Optional[GridRegistry]=None,expected_sha256:Optional[str]=None):
        self.validate(reg,expected_sha256);out=copy.deepcopy(self);out.validate(reg,self.sha256);return out

    def get(self,family:str,size:str,expected_sha256:Optional[str]=None) -> TwelvePositionManifest:
        """Return an independent member; expected_sha256 here is the MEMBER SHA."""
        self.validate()
        if family not in self.manifests or size not in self.manifests[family]: raise InputContractError(f'asset has no manifest for {family}/{size}')
        m=self.manifests[family][size]
        if expected_sha256 is not None and m.sha256!=expected_sha256: raise InputContractError(f'{family}/{size}: manifest SHA differs from expected value')
        verify_twelve_cached(m,regenerate=False);return copy.deepcopy(m)

def build_twelve_assets(reg:GridRegistry,families=None) -> TwelveManifestAsset:
    _registry(reg)
    if families is not None and (not isinstance(families,(list,tuple)) or not families): raise InputContractError('families must be a nonempty list/tuple when supplied')
    fams=[f for f in (list(reg.surviving) if families is None else families) if f!='E1']
    if not fams or any(not isinstance(f,str) or f not in stage12.BOX for f in fams) or len(set(fams))!=len(fams): raise InputContractError('invalid or duplicate non-E1 family inventory')
    mans={f:{s:generate_twelve(f,s,np.asarray(reg.anchors[f],float)) for s in reg.surviving[f]} for f in fams}
    out=TwelveManifestAsset(reg.registry_sha256,dict(stage12.GENERATOR,streamed_families=list(stage12.STREAMED_FAMILIES)),mans,fams)
    out.sha256=out.payload_sha();verify_twelve_assets(out,reg,out.sha256);return out

def verify_twelve_assets(asset:TwelveManifestAsset,reg:GridRegistry,expected_sha256:Optional[str]=None) -> dict:
    """Validate the complete asset before work; publish receipts only on success."""
    _registry(reg)
    if not isinstance(asset,TwelveManifestAsset): raise InputContractError('asset type must be TwelveManifestAsset')
    asset.validate(reg,expected_sha256,require_intake=False);pinned=asset.sha256;pending=[]
    for f in asset.families:
        for m in asset.manifests[f].values():
            verify_twelve(m);pending.append(m.sha256)
    asset.validate(reg,pinned,require_intake=False)
    _VERIFIED.update(pending);asset._intake_sha256=pinned
    asset.verification=dict(intake='regeneration-verified',manifests=len(pending),registry_sha256=reg.registry_sha256)
    return dict(ok=True,manifests=len(pending),asset_sha256=pinned)

def asset_from_dict(d:dict) -> TwelveManifestAsset:
    d=ser.from_jsonable(d);required={'registry_sha256','generator','manifests','families','sha256'}
    if not isinstance(d,dict) or not required<=set(d) or set(d)-required-{'verification'}: raise InputContractError('invalid serialized twelve asset schema')
    if not isinstance(d['manifests'],dict) or not isinstance(d['families'],list): raise InputContractError('invalid serialized asset inventory')
    try:
        mans={f:{s:TwelvePositionManifest(**md) for s,md in sz.items()} for f,sz in d['manifests'].items()}
        out=TwelveManifestAsset(d['registry_sha256'],d['generator'],mans,d['families'],d['sha256'])
    except (TypeError,AttributeError) as e: raise InputContractError('invalid serialized manifest') from e
    out.validate(require_intake=False);return out  # no process receipt is deserialized
