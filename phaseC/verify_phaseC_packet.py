#!/usr/bin/env python3
"""Read-only Phase C packet/reference-source validator (audit reference candidate).

Usage: python verify_phaseC_packet.py PACKET_DIR ENGINE_PHASEB_DIR
       [--expected-inventory-sha256 SHA]

No numerical simulations, lattice generation, OT, remote Git lookup, policy approval,
source-correspondence approval, or certification of the installed runtime is done.
The optional expected inventory SHA must come from the final outer receipt, not from
an untrusted value inside the directory. Without it this is internal consistency.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import sys

RULES_SHA = '5f02c970eb39f9b3e7f7b17b48eb2d3daa16434517cf4442bac339f5ab719615'
TABLES_SHA = '522751be134aa3ff4fdf33c6be0d7397fb7bd3c89a6c67e26a67bd32dceeb0b4'
PLAN_SHA = {
    'v0_3': 'bac9dbfe7dfb70baa4a6ca5f1d3dc8f24c65641ebf01e3693171a4022c2abfb8',   # bundled in packet v0.4 (author-supplied original; SHA as identified by the audit)
    'v0_4': '0569ae2f9cbd3003d1f08840b43f20c14e8da3e07ca7718743929ee138235371',
    'v0_5': '357e4d7d0325e3284bd3dcf062a4c5e5bf7599b14032e90ab3da6912da5e9f18',
}
CATEGORIES = {'modules':'step1_engine/', 'tests_sha256':'tests/',
              'fixtures_sha256':'tests/', 'assets_sha256':'',
              'documents_sha256':'', 'b3_sha256':'', 'registered_assets_sha256':''}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def pairs(items):
    d = {}
    for k, v in items:
        if k in d:
            raise ValueError(f'duplicate JSON key: {k}')
        d[k] = v
    return d


def load(path: Path):
    def bad(value):
        raise ValueError(f'non-standard JSON constant: {value}')
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs,
                      parse_constant=bad)


def safe(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or '\\' in name:
        raise ValueError(f'unsafe relative path: {name!r}')
    q = PurePosixPath(name)
    if q.is_absolute() or '..' in q.parts or str(q) != name:
        raise ValueError(f'unsafe relative path: {name!r}')
    p = root.joinpath(*q.parts)
    if not p.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'path escapes root: {name}')
    for part in [p, *p.parents]:
        if part == root.parent:
            break
        if part.is_symlink():
            raise ValueError(f'symlink not allowed in verified path: {name}')
    return p


def verify(pk: Path, eng: Path, expected_inventory: str | None = None) -> dict:
    pk, eng = pk.resolve(), eng.resolve()
    result = {'passed': False, 'failures': [], 'checks': {},
              'scope': 'file/source binding and parsed registered-asset consistency only; '
                       'no new physical execution, no source-correspondence or policy approval',
              'outer_inventory_pinned': expected_inventory is not None}
    def require(ok, message):
        if not ok:
            raise ValueError(message)
    try:
        inv_path = pk/'PACKET_INVENTORY.json'
        inv = load(inv_path)
        require(inv['schema'] == 'phaseC_packet_inventory_v1', 'packet inventory schema')
        if expected_inventory is not None:
            require(bool(re.fullmatch('[0-9a-f]{64}', expected_inventory)), 'invalid outer inventory SHA')
            require(sha(inv_path) == expected_inventory, 'outer inventory SHA mismatch')
        actual = {p.relative_to(pk).as_posix() for p in pk.rglob('*') if p.is_file()}
        require(actual == set(inv['files']) | {'PACKET_INVENTORY.json'}, 'packet file inventory is not exact')
        for rel, spec in inv['files'].items():
            p = safe(pk, rel)
            require(p.is_file() and sha(p) == spec['sha256'] and p.stat().st_size == spec['bytes'],
                    f'packet file SHA/size mismatch: {rel}')
        result['checks']['packet_files'] = len(inv['files'])
        result['checks']['packet_inventory_sha256'] = sha(inv_path)
        m = load(pk/'Step1_rules_v1.0_freeze_manifest.json')
        require(m['schema'] == 'step1_rules_v1.0_freeze_manifest_v1', 'freeze manifest schema')
        src = m['accepted_sources']
        require(inv['handoff_commit'] == src['handoff_commit'] and
                bool(re.fullmatch('[0-9a-f]{40}', src['handoff_commit'])), 'handoff commit cross-reference')
        ei_path = eng/'B2_completion_inventory.json'
        require(sha(ei_path) == src['handoff_inventory_sha256'], 'handoff source inventory SHA')
        ei = load(ei_path)
        require(ei['engine_version'] == src['engine_version'], 'source engine version')
        n = 0
        for cat, prefix in CATEGORIES.items():
            for rel, h in ei[cat].items():
                p = safe(eng, prefix+rel)
                require(p.is_file() and sha(p) == h, f'source SHA mismatch: {prefix+rel}')
                n += 1
        modules = {p.name for p in (eng/'step1_engine').glob('*.py')}
        require(modules == set(ei['modules']), 'source module inventory is not exact')
        result['checks']['source_sha_entries'] = n
        ar = m['adopted_rules']
        require(sha(safe(pk, ar['document'])) == ar['sha256'] == RULES_SHA, 'adopted rules SHA')
        require(sha(safe(pk, ar['tables'])) == ar['tables_sha256'] == TABLES_SHA, 'adopted tables SHA')
        tb = load(safe(pk, ar['tables']))
        require(tb['rules_document']['sha256'] == ar['sha256'] and
                Path(ar['document']).name == tb['rules_document']['name'], 'rules/tables file binding')
        require(sha(eng/tb['rules_document']['name']) == ar['sha256'] and
                sha(eng/'rules_tables_v1.json') == ar['tables_sha256'], 'source copies of adopted text/tables')
        for key, golden in PLAN_SHA.items():
            v = m['research_plan_originals'][key]
            require(sha(safe(pk,v['file'])) == v['sha256'] == v['expected'] == golden, f'original plan SHA: {key}')
        # The CLI is a fresh process. Refuse an unexpected preloaded engine when used programmatically.
        for key, module in list(sys.modules.items()):
            if key == 'step1_engine' or key.startswith('step1_engine.'):
                path = Path(getattr(module, '__file__', '')).resolve()
                require(path.is_relative_to(eng/'step1_engine'), f'preloaded source not from expected root: {key}')
        sys.path.insert(0, str(eng))
        from step1_engine import __version__
        from step1_engine.rules_config import RULES, verify_binding
        require(__version__ == src['engine_version'], 'loaded engine version')
        require(Path(RULES.path).resolve() == eng/'rules_tables_v1.json', 'rules-table environment override')
        result['checks']['rules_binding'] = verify_binding(RULES, require_document=True)
        from step1_engine.grid_registry import load_registry, registry_from_dict_bound
        from step1_engine.grid_manifest import (ConfigurationManifest, ConfigurationSpec,
                build_configuration_manifest, verify_manifest_against_a7)
        from step1_engine import serialization as ser
        g = m['first_wave_grid']
        a6, a7 = eng/'tests/assets/a6_observer_design_points.json', eng/'tests/assets/a7_circle_geometry.csv'
        require(sha(a6) == g['sources']['a6_sha256'] and sha(a7) == g['sources']['a7_sha256'], 'grid frozen source SHA')
        require(sha(safe(pk,g['registry'])) == g['registry_file_sha256'], 'registry file SHA')
        require(sha(safe(pk,g['configuration_manifest'])) == g['manifest_file_sha256'], 'grid manifest file SHA')
        reg = registry_from_dict_bound(load(safe(pk,g['registry'])), str(a7), str(a6))
        raw = ser.from_jsonable(load(safe(pk,g['configuration_manifest'])))
        parsed = dict(raw); parsed['configurations'] = [ConfigurationSpec(**v) for v in raw['configurations']]
        man = ConfigurationManifest(**parsed); man.validate()
        fresh = build_configuration_manifest(reg)
        require(man.as_dict() == fresh.as_dict(), 'stored grid differs from source-reconstructed grid')
        require(reg.registry_sha256 == g['registry_sha256'] and man.manifest_sha256 == g['manifest_sha256']
                and man.n_configurations == g['n_configurations'], 'grid declared payload/count')
        result['checks']['a7'] = verify_manifest_against_a7(man, str(a7))
        ra = m['registered_assets']
        for key in ('twelve_position','twelve_geometry','shared_w2_null'):
            require(sha(safe(pk,ra[key]['file'])) == ra[key]['file_sha256'], f'{key} file SHA')
        from step1_engine.twelve_assets import intake_registered_twelve_assets
        a = intake_registered_twelve_assets(str(safe(pk,ra['twelve_position']['file'])),reg,ra['twelve_position']['receipt'])
        require(a.sha256 == ra['twelve_position']['asset_sha256'] and a.registry_sha256 == ra['twelve_position']['registry_sha256'], 'twelve asset identity')
        raw_twelve = load(safe(pk,ra['twelve_position']['file']))
        actual_hashes = {family: {size: value['sha256'] for size, value in sizes.items()}
                         for family, sizes in raw_twelve['manifests'].items()}
        require(actual_hashes == ra['twelve_position']['manifests'], 'twelve member payload references')
        from step1_engine.w2_shared import SharedNullAsset
        s = SharedNullAsset(**ser.from_jsonable(load(safe(pk,ra['shared_w2_null']['file']))))
        require(s.validate() and s.sha256 == ra['shared_w2_null']['asset_sha256'], 'shared null payload SHA')
        wanted = ra['shared_w2_null']['identity']; live = s.identity
        for k in ('m','n_subs','B_max','distance_kind','master_seed'):
            require(wanted[k] == live[k], f'shared null identity {k}')
        require(wanted['iso_K'] == live['iso']['K'] == live['iso_f32']['K'], 'shared null K')
        require(sha(safe(pk,src['receipts'])) == src['receipts_sha256'], 'receipt file SHA')
        receipts = load(safe(pk,src['receipts']))
        for f,h in m['audits'].items():
            require(sha(safe(pk,'audits/'+f)) == h, f'audit SHA: {f}')
        for rec in receipts['receipts']:
            require(set(rec['audits']) == set(rec['audit_sha256']), 'receipt audit list/set')
            for f,h in rec['audit_sha256'].items():
                require(m['audits'].get(f) == h, f'receipt audit binding: {f}')
        rows = list(csv.DictReader(io.StringIO(safe(pk,ra['twelve_geometry']['file']).read_text())))
        require(len(rows) == ra['twelve_geometry']['rows'] == 108, 'geometry row count')
        for key,mod in list(sys.modules.items()):
            if key == 'step1_engine' or key.startswith('step1_engine.'):
                p = Path(getattr(mod,'__file__','')).resolve()
                require(p.is_relative_to(eng/'step1_engine') and p.name in ei['modules']
                        and sha(p) == ei['modules'][p.name], f'loaded source binding: {key}')
        result['checks']['registered_assets'] = {'configurations':30,'twelve_members':9,'geometry_rows':108,
                                                 'shared_null_sha256':s.sha256}
        result['passed'] = True
    except Exception as exc:
        result['failures'].append(f'{type(exc).__name__}: {exc}')
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('packet_dir',type=Path); ap.add_argument('engine_phaseB_dir',type=Path)
    ap.add_argument('--expected-inventory-sha256')
    args=ap.parse_args()
    result=verify(args.packet_dir,args.engine_phaseB_dir,args.expected_inventory_sha256)
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if result['passed'] else 1

if __name__=='__main__':
    sys.dont_write_bytecode=True
    raise SystemExit(main())
