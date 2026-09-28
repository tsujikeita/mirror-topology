# -*- coding: utf-8 -*-
"""D-3a registered asset intake (step1_engine.d3_assets): (1) the REGISTERED 9 formal partition runs re-verify with arrays, re-aggregate to the registered coverage, expose the 81
new base covariances with PC-1 status, and the 2 retained incomplete attempts are reproduced by the completed runs; (2) tampering anywhere (ledger identity, run manifest, registry
entry, covariance bytes, coverage, pins binding, incomplete attempt promoted to complete, partial evidence edited, run removed) is refused; (3) mapping-free physical PC-1
recomputation from the registered NPY files alone: every unordered (file, file, action) pair with rel < 1e-5 under C1 = D(M) C0 D(M)^T is enumerated without consulting any
registry, and the pair set equals the registered case set (108 new-point + 36 anchor, anchor bases from registered_assets/d1); no registered file is unmatched."""
import os, sys, json, copy, hashlib, shutil, io
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine.d3_assets import intake_registered_d3a_assets, D3aAssets, _coverage_key
from step1_engine.errors import InputContractError
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); MT = os.environ.get('B3_MT', '/home/claude/mt'); RA = os.path.join(P, 'registered_assets', 'd3')
LEDGER = os.path.join(RA, 'd3a_generation_ledger.json'); COV = os.path.join(RA, 'd3a_family_coverage.json')
sha = lambda b: hashlib.sha256(b).hexdigest()
need_mt = pytest.mark.skipif(not os.path.exists(os.path.join(MT, 't1_engine.py')), reason='frozen mirror-topology checkout not present')


def _copy(tmp_path):
    """Copy the phaseB pieces the intake reads (d/, registered_assets/d1 + d3) into a scratch root."""
    root = tmp_path / 'phaseB'; (root / 'registered_assets').mkdir(parents=True)
    shutil.copytree(os.path.join(P, 'd'), root / 'd'); shutil.copytree(os.path.join(P, 'registered_assets', 'd3'), root / 'registered_assets' / 'd3'); shutil.copytree(os.path.join(P, 'registered_assets', 'd1'), root / 'registered_assets' / 'd1')
    return str(root)


def _rewrite(path, fn):
    d = json.load(open(path)); fn(d); json.dump(d, open(path, 'w'), indent=1)


def test_registered_d3a_assets_intake_and_exposure():
    a = intake_registered_d3a_assets(P); L = json.load(open(LEDGER)); C = json.load(open(COV))
    assert isinstance(a, D3aAssets) and a.verified and a.ledger_sha256 == sha(open(LEDGER, 'rb').read()) and a.coverage_sha256 == sha(open(COV, 'rb').read()) == L['coverage_sha256']
    assert set(a.coverage) == {'E2', 'E7', 'E8'} and all(c['family_coverage_complete'] and c['arrays_verified'] and c['outer_ledger_bound'] and c['n_pc1_fail'] == 0 for c in a.coverage.values())
    assert {f: _coverage_key(c) for f, c in a.coverage.items()} == {f: _coverage_key(c) for f, c in C['coverage'].items()}
    assert len(a.formal_runs) == 9 and sorted((r['family'], r['sizes'][0]) for r in a.formal_runs.values()) == [(f, s) for f in ('E2', 'E7', 'E8') for s in ('L1.00', 'L1.20', 'L1.50')]
    assert len(a.base_covariances) == 81 and a.n_pc1_fail == 0 and set(a.pc1_status) == set(a.base_covariances) and all(v['status'] == 'PC1_PASS' for v in a.pc1_status.values())
    ids = sorted(int(k) for k in a.base_covariances); assert ids == sorted(10000 * f + 100 * s + p for f in (2, 3, 4) for s in (1, 2, 3) for p in range(4, 13))   # FAMILY_CODES E2=2 E7=3 E8=4
    for cid, e in a.base_covariances.items():                                                                              # registered files exist, bytes and raw arrays match the exposed identities
        b = open(os.path.join(P, e['registered_file']), 'rb').read(); assert sha(b) == e['cov_file_sha256'] and sha(np.load(io.BytesIO(b), allow_pickle=False).tobytes()) == e['cov_array_sha256'] and e['config_id'] == int(cid)
    e = a.require_pc1_pass(20104); assert e['family'] == 'E2' and e['size_id'] == 'L1.00'
    for bad in (20101, '20104', 20104.0, 99999):                                                                           # anchors (D-1), non-int ids and unknown ids are refused
        with pytest.raises(InputContractError): a.require_pc1_pass(bad)
    assert set(a.incomplete_attempts) == set(a.reproduction_crosscheck) and len(a.incomplete_attempts) == 2 and all(v['script_returncode'] == -9 for v in a.reproduction_crosscheck.values())
    assert sum(v['partial_bases_reproduced'] + v['partial_cases_reproduced'] for v in a.reproduction_crosscheck.values()) == 39
    with pytest.raises(InputContractError): D3aAssets(dict(x=1))                                                           # construction outside the factory refused
    with pytest.raises(AttributeError): a.coverage = {}
    v = a.pc1_status; v['20104']['status'] = 'PC1_FAIL'; assert a.pc1_status['20104']['status'] == 'PC1_PASS'               # views are copies
    with pytest.raises(InputContractError): intake_registered_d3a_assets(P, expected_ledger_sha256='0' * 64)


def test_registered_d3a_assets_tampering_refused(tmp_path):
    root = _copy(tmp_path); intake_registered_d3a_assets(root)                                                              # pristine copy passes
    L = json.load(open(os.path.join(root, 'registered_assets', 'd3', 'd3a_generation_ledger.json'))); name, rec = next(iter(L['formal_runs'].items())); rd = os.path.join(root, rec['registered_dir'])
    def fresh():
        shutil.rmtree(root); return _copy(tmp_path)
    def refused(msg):
        with pytest.raises(InputContractError): intake_registered_d3a_assets(root)
    # (a) one covariance byte edited (file identity kept in the registry) -> array/file check fails
    reg = json.load(open(os.path.join(rd, 'd3_cov_registry.json'))); f = os.path.join(rd, next(iter(reg['configurations'].values()))['cov_file']); b = bytearray(open(f, 'rb').read()); b[-1] ^= 1; open(f, 'wb').write(bytes(b)); refused('cov bytes')
    root = fresh(); rd = os.path.join(root, rec['registered_dir'])
    # (b) run manifest rewritten (any byte) -> ledger identity binding fails
    p = os.path.join(rd, 'd3_run_manifest.json'); open(p, 'a').write('\n'); refused('manifest')
    root = fresh(); rd = os.path.join(root, rec['registered_dir'])
    # (c) ledger run-manifest identity edited to match a rewritten manifest -> coverage / document identities still differ
    open(p, 'a').write('\n'); _rewrite(os.path.join(root, 'registered_assets', 'd3', 'd3a_generation_ledger.json'), lambda d: d['formal_runs'].__getitem__(name).__setitem__('run_manifest_sha256', sha(open(p, 'rb').read()))); refused('ledger edit')
    root = fresh()
    # (d) registered coverage edited (a count) with the ledger's coverage identity updated -> re-aggregation differs
    cp = os.path.join(root, 'registered_assets', 'd3', 'd3a_family_coverage.json'); _rewrite(cp, lambda d: d['coverage']['E2'].__setitem__('n_pc1_pass', 35)); _rewrite(os.path.join(root, 'registered_assets', 'd3', 'd3a_generation_ledger.json'), lambda d: d.__setitem__('coverage_sha256', sha(open(cp, 'rb').read()))); refused('coverage')
    root = fresh()
    # (e) coverage identity stale -> refused before aggregation
    _rewrite(cp, lambda d: d.__setitem__('created', 'x')); refused('coverage identity')
    root = fresh()
    # (f) current pins case-table identity differs from the ledger -> registered assets not bound to the current table
    _rewrite(os.path.join(root, 'd', 'd3_pins.json'), lambda d: d.__setitem__('case_table_sha256', '0' * 64)); refused('pins')
    root = fresh()
    # (g) a formal run removed from the ledger -> family coverage incomplete
    _rewrite(os.path.join(root, 'registered_assets', 'd3', 'd3a_generation_ledger.json'), lambda d: d['formal_runs'].pop(name)); refused('run removed')
    root = fresh()
    # (h) incomplete attempt promoted (a run manifest copied in) -> refused; (i) partial evidence rel edited -> not reproduced -> refused
    L2 = json.load(open(os.path.join(root, 'registered_assets', 'd3', 'd3a_generation_ledger.json'))); iname, irec = next(iter(L2['incomplete_attempts'].items())); idir = os.path.join(root, irec['registered_dir'])
    shutil.copy(os.path.join(root, L2['formal_runs'][irec['completed_by']]['registered_dir'], 'd3_run_manifest.json'), os.path.join(idir, 'd3', 'd3_run_manifest.json')); refused('promoted')
    root = fresh(); idir = os.path.join(root, irec['registered_dir'])
    pe = os.path.join(idir, 'd3', 'd3_partial_evidence.json'); _rewrite(pe, lambda d: next(iter(d['bases'].values())).__setitem__('cov_array_sha256', '0' * 64)); refused('partial edited')
    root = fresh()
    # (j) launcher lock commit differs from the source lock -> refused; (k) ledger schema / source lock incomplete -> refused
    _rewrite(os.path.join(root, rec['registered_dir'], '..', 'launcher_lock.json'), lambda d: d.__setitem__('commit', 'a' * 40)); _rewrite(os.path.join(root, 'registered_assets', 'd3', 'd3a_generation_ledger.json'), lambda d: d['formal_runs'][name].__setitem__('launcher_lock_sha256', sha(open(os.path.join(root, rec['registered_dir'], '..', 'launcher_lock.json'), 'rb').read()))); refused('launcher lock')
    root = fresh()
    _rewrite(os.path.join(root, 'registered_assets', 'd3', 'd3a_generation_ledger.json'), lambda d: d['source_lock'].pop('script_sha256')); refused('source lock')


@need_mt
def test_registered_arrays_mapping_free_pc1_recomputation():
    """Physical re-verification from arrays only: no registry / manifest is read. D(M) from the A11 cell-2 quadrature bridge (t2b2_bridge); anchor bases from registered_assets/d1."""
    sys.path.insert(0, MT); import t1_engine as t1, t2b2_bridge as br; from scipy.special import sph_harm_y
    LMAX = 4; TOL = 1e-5; CT = json.load(open(os.path.join(P, 'd', 'd3_pc1_case_table.json'))); actions = {}
    for c in CT['new_point_cases'] + CT['first_wave_anchor_cases']: actions.setdefault(c['family'], {})[c['action']] = np.array(c['M'], float)
    LM = br.lm_full(); M21 = br.M_matrix()[0]; n = 2 * LMAX + 2; xg, wg = np.polynomial.legendre.leggauss(n); th = np.arccos(xg); ph = 2 * np.pi * np.arange(n) / n
    TH, PH = np.meshgrid(th, ph, indexing='ij'); WQ = (np.repeat(wg[:, None], n, axis=1) * (2 * np.pi / n)).ravel(); DIRS = np.column_stack([np.sin(TH).ravel() * np.cos(PH).ravel(), np.sin(TH).ravel() * np.sin(PH).ravel(), np.cos(TH).ravel()])
    def Ymat(d):
        t = np.arccos(np.clip(d[:, 2], -1, 1)); p = np.mod(np.arctan2(d[:, 1], d[:, 0]), 2 * np.pi); return (M21.conj() @ np.array([sph_harm_y(l, m, t, p) for (l, m) in LM])).real.T
    YQ = Ymat(DIRS); assert np.abs((YQ * WQ[:, None]).T @ YQ - np.eye(21)).max() < 1e-12
    D_of = lambda M: (YQ * WQ[:, None]).T @ Ymat(DIRS @ M)
    def load_dir(d): return {f: t1.load_cov_full(os.path.join(d, f), LMAX)[1] for f in sorted(os.listdir(d)) if f.endswith('.npy')}
    d1 = load_dir(os.path.join(P, 'registered_assets', 'd1', 'cov_cache')); L = json.load(open(LEDGER)); total = 0
    for name, rec in L['formal_runs'].items():
        fam = rec['family']; mats = load_dir(os.path.join(P, rec['registered_dir'], 'cov_cache')); Ds = {a: D_of(M) for a, M in actions[fam].items()}
        for C in mats.values(): ev = np.linalg.eigvalsh((C + C.T) / 2); assert np.isfinite(C).all() and np.abs(C - C.T).max() == 0 and ev.min() > -1e-12 * ev.max()
        pairs = {}
        for cf, Cc in mats.items():
            for act, D in Ds.items():
                for bf, Cb in list(mats.items()) + [(k, v) for k, v in d1.items() if k.startswith('cov_' + fam + '_')]:
                    if bf == cf: continue
                    tgt = D @ Cb @ D.T; rel = float(np.linalg.norm(Cc - tgt) / np.linalg.norm(tgt))
                    if rel < TOL: pairs[(tuple(sorted((cf, bf))), act)] = min(rel, pairs.get((tuple(sorted((cf, bf))), act), 1.0))
        within = sum(1 for (fs, a) in pairs if all(f in mats for f in fs)); anchor = len(pairs) - within; n_act = len(Ds)
        assert within == 9 * n_act and anchor == 3 * n_act and len(mats) == 9 + 12 * n_act and max(pairs.values()) < 1e-6                     # 9 new base-clone pairs and 3 anchor clones per action
        assert {f for fs, _ in pairs for f in fs if f in mats} == set(mats)                                                                    # no registered file is unmatched
        total += len(pairs)
    assert total == 144
