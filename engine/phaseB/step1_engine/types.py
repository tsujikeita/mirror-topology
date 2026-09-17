# -*- coding: utf-8 -*-
"""Shared identity types (rules §6.3). ClusterUID is the single UID type used by registry, bootstrap plans and hit tables; as_uid() adapts tuples."""
from __future__ import annotations
from dataclasses import dataclass
from .errors import InputContractError


@dataclass(frozen=True)
class ClusterUID:
    wave_id: int; purpose_id: int; crn_group_id: int; batch_id: int; rotation_index: int

    def as_tuple(self): return (self.wave_id, self.purpose_id, self.crn_group_id, self.batch_id, self.rotation_index)


def as_uid(u) -> ClusterUID:
    if isinstance(u, ClusterUID): return u
    if isinstance(u, (tuple, list)) and len(u) == 5 and all(isinstance(x, int) and not isinstance(x, bool) for x in u): return ClusterUID(*u)
    raise InputContractError(f"cannot interpret {u!r} as ClusterUID")
