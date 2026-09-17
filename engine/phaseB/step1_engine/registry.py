# -*- coding: utf-8 -*-
"""RNG key / CRN group registry (rules §6.3–6.4). evaluation_id is NEVER part of the rng key; crn_group_id is globally unique across purposes and waves.
Streams are created once per key and fanned out (a second creation of the same key is refused unless reuse=True is explicit); the call log records creations."""
from __future__ import annotations
import numpy as np
from .errors import InputContractError
from .types import ClusterUID

STREAM = dict(gaussian=0, rotation=1, calibration=2, pseudo=3, bootstrap=4, w2=5)
PURPOSE = dict(calibration=100, evaluation=200, fitting=300, pseudo=400, negative_control=500, w2_independent=600, w2_crn=700, w2_isotropic=800)
TOPOLOGY = dict(E1=1, E2=2, E7=7, E8=8)


class CRNRegistry:
    def __init__(self, master_seed: int, groups: dict = None):
        self.master_seed = int(master_seed); self._groups = dict(groups or {}); self._next = (max(self._groups) + 1) if self._groups else 1; self.creations = []; self._streams = {}

    def new_group(self, purpose: str, wave_id: int, label: str) -> int:
        if purpose not in PURPOSE: raise InputContractError("unknown purpose")
        gid = self._next; self._next += 1; self._groups[gid] = dict(purpose=purpose, wave_id=int(wave_id), label=label); return gid

    def export_groups(self) -> dict: return dict(self._groups)                                      # frozen registry for later restoration (no re-numbering)

    def rng_key(self, purpose: str, wave_id: int, crn_group_id: int, batch_id: int, stream: str):
        g = self._groups.get(crn_group_id)
        if g is None or g["purpose"] != purpose or g["wave_id"] != int(wave_id): raise InputContractError("crn_group_id not registered for this purpose/wave")
        return (self.master_seed, int(wave_id), PURPOSE[purpose], int(crn_group_id), int(batch_id), STREAM[stream])

    def stream(self, purpose: str, wave_id: int, crn_group_id: int, batch_id: int, stream: str, *, reuse: bool = False):
        key = self.rng_key(purpose, wave_id, crn_group_id, batch_id, stream)
        if key in self._streams:
            if not reuse: raise InputContractError("stream already created for this key: fan out the existing generator (reuse=True to get the SAME object)")
            return self._streams[key]
        self.creations.append(key); self._streams[key] = np.random.default_rng(np.random.SeedSequence(list(key))); return self._streams[key]

    @staticmethod
    def cluster_uid(wave_id: int, purpose: str, crn_group_id: int, batch_id: int, rotation_index: int) -> ClusterUID:
        return ClusterUID(int(wave_id), PURPOSE[purpose], int(crn_group_id), int(batch_id), int(rotation_index))

    def inventory_unique(self) -> bool: return len(set(self.creations)) == len(self.creations)
