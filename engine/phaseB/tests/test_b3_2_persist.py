# -*- coding: utf-8 -*-
"""B-3-2 persistence (R322-A/B/C): generation publish/restore with verification, interrupted copy keeps the previous generation, lock mismatch refused BEFORE touching staging,
unrelated JSON is not a resume basis, partial (one n_sub) state is a legitimate resumable state, no merge into a non-empty staging dir."""
import os, sys, json, shutil
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from step1_engine.ckpt_persist import publish_generation, restore_generation, inspect_local, latest_generation, verify_generation
from step1_engine.w2_shared_build import null_sequence_resumable
from step1_engine.errors import InputContractError
from test_b2_tranche3 import cheap_dist, make_positions
from test_b2_tranche25 import paired

def _partial(tmp_path, stop_after=20):
    rng = np.random.default_rng(41); _, iso = make_positions(rng); iso32 = paired(iso); ck = str(tmp_path / 'local'); os.makedirs(ck); calls = {'n': 0}
    def stopping(a, b):
        calls['n'] += 1
        if calls['n'] > stop_after * 3: raise KeyboardInterrupt
        return cheap_dist(a, b)
    stopping.__name__ = cheap_dist.__name__
    with pytest.raises(KeyboardInterrupt): null_sequence_resumable(iso, 2000, 10, 20260918, os.path.join(ck, 'null_nsub2000.json'), stopping, iso32, every=10, log=lambda *a: None, whitening_identity=dict(source='A'))
    return ck, iso, iso32

def test_publish_restore_partial_and_refusals(tmp_path):
    ck, iso, iso32 = _partial(tmp_path); lock = dict(commit='c' * 40, inventory_sha256='i' * 64, launcher_id='L', pins_sha256='p' * 64); root = str(tmp_path / 'drive' / 'run1')
    info = inspect_local(ck); assert info['resumable'] and info['present']['null_nsub2000.json']['done'] == 20 and 'null_nsub5000.json' not in info['present']   # legitimate partial state
    g1 = publish_generation(ck, root, lock, note=lambda *a: None); assert latest_generation(root) == g1 and verify_generation(g1)['done'] == {'null_nsub2000.json': 20}
    st = str(tmp_path / 'staging'); r = restore_generation(root, st, lock); assert r['partial_state'] == {'null_nsub2000.json': 20} and os.path.exists(os.path.join(st, 'null_nsub2000.json'))
    with pytest.raises(InputContractError): restore_generation(root, st, lock)                                                       # non-empty staging: no merge
    st2 = str(tmp_path / 'staging2')
    with pytest.raises(InputContractError): restore_generation(root, st2, dict(lock, commit='d' * 40))                              # lock mismatch refused before any copy
    assert not os.path.exists(st2) or not os.listdir(st2)
    # unrelated JSON only -> not resumable
    u = str(tmp_path / 'unrel'); os.makedirs(u); open(os.path.join(u, 'unrelated.json'), 'w').write('{}'); assert inspect_local(u)['resumable'] is False
    # corrupted local checkpoint -> inspect refuses
    bad = str(tmp_path / 'bad'); os.makedirs(bad); open(os.path.join(bad, 'null_nsub2000.json'), 'w').write(open(os.path.join(ck, 'null_nsub2000.json')).read()[:23])
    with pytest.raises(InputContractError): inspect_local(bad)

def test_interrupted_publish_keeps_previous_generation(tmp_path, monkeypatch):
    ck, iso, iso32 = _partial(tmp_path); lock = dict(commit='c' * 40, inventory_sha256='i' * 64, launcher_id='L', pins_sha256='p' * 64); root = str(tmp_path / 'drive' / 'run1')
    g1 = publish_generation(ck, root, lock, note=lambda *a: None); good = verify_generation(g1)
    import step1_engine.ckpt_persist as cp
    def broken_copy(src, dst):
        open(dst, 'wb').write(open(src, 'rb').read()[:23]); raise OSError('simulated I/O failure mid-copy')
    monkeypatch.setattr(cp.shutil, 'copyfile', broken_copy)
    with pytest.raises(OSError): publish_generation(ck, root, lock, note=lambda *a: None)
    assert latest_generation(root) == g1 and verify_generation(g1) == good                                                         # previous generation intact, pointer unchanged
    monkeypatch.undo(); g2 = publish_generation(ck, root, lock, note=lambda *a: None); assert latest_generation(root) == g2 and os.path.exists(g1)   # old generation retained
