# -*- coding: utf-8 -*-
"""D-1 registered covariances (Colab run aa089fa4…, accepted): every cached file matches the registry file SHA and the receipt; array SHA recomputed from bytes; sidecar manifests
bind topology/params/x0/run_config/commit; 30 configurations map 1:1 onto the source-bound first-wave grid (cache_key, x0_CT); the A11 cross-check entry is present and NOT one
of the 30 (31 npy total); downstream intake re-verifies everything (pass_ flags alone are not trusted)."""
import os, sys, json, hashlib
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); R = os.path.join(P, 'registered_assets', 'd1'); sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
from step1_engine.grid_registry import load_registry; from step1_engine.grid_manifest import build_configuration_manifest, verify_cov_manifest

def test_d1_cache_registry_receipt_and_grid_binding():
    reg = json.load(open(os.path.join(R, 'd1_cov_registry.json'))); rc = json.load(open(os.path.join(R, 'd1_receipt.json'))); files = sorted(os.listdir(os.path.join(R, 'cov_cache')))
    assert rc['registered']['files'] == {f: sha(os.path.join(R, 'cov_cache', f)) for f in files} and len([f for f in files if f.endswith('.npy')]) == 31 and rc['registered']['n_configurations'] == 30 == len(reg['configurations'])
    greg = load_registry(os.path.join(P, 'tests/assets/a7_circle_geometry.csv'), os.path.join(P, 'tests/assets/a6_observer_design_points.json')); man = build_configuration_manifest(greg); assert man.manifest_sha256 == reg['grid_manifest_sha256'] and greg.registry_sha256 == reg['registry_sha256']
    by_id = man.by_id(); used = set()
    for cid, c in reg['configurations'].items():
        s = by_id[int(cid)]; p = os.path.join(R, c['cov_file']); rec = json.load(open(p + '.manifest.json'))
        assert c['cache_key'] == s.cache_key and list(map(float, c['x0_CT'])) == list(map(float, s.x0_CT)) and c['cov_file_sha256'] == sha(p) == rec['cov_file_sha256']
        assert hashlib.sha256(np.load(p).tobytes()).hexdigest() == rec['cov_array_sha256'] == c['cov_array_sha256'] and np.load(p).shape == (21, 21)
        geo = verify_cov_manifest(s, rec, p); assert geo['bound'] and geo['file_sha_verified'] and rec['manifest']['run_config'] == reg['run_config'] and rec['manifest']['cmbtopology_commit'] == reg['cmbtopology_commit'] and rec['manifest']['env_fingerprint'] == reg['env_fingerprint']
        assert c['intake']['pass_'] is True and c['intake']['psd'] and c['intake']['sqrt_matched']['clip'] == 0 and c['intake']['sqrt_native']['clip'] == 0; used.add(os.path.basename(p))
    extra = [f for f in files if f.endswith('.npy') and f not in used]; assert len(extra) == 1 and extra[0].startswith('cov_E7_')                     # the A11 cross-check regeneration, not a first-wave member
    assert rc['a11_cross_check']['rel_frobenius'] <= 1e-10 and rc['a11_cross_check']['regenerated_array_sha256'] == hashlib.sha256(np.load(os.path.join(R, 'cov_cache', extra[0])).tobytes()).hexdigest()
