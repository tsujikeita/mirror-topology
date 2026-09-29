# -*- coding: utf-8 -*-
"""D-3b tranche 1: generation script contracts (d/d3_bankgen.py; external assets — frozen checkout + Phase C packet — required, skipped otherwise). Fresh-only OUT; the registered
environment HARD gate stops before generation; a self-test run (scale 0.001, one added configuration, A10 skipped) completes with D3B_PASS False (env gate False in the sandbox;
never D3B_PASS under self-test flags) and its directories re-verify against the context; first-wave ids / other sizes are refused at scope resolution (never generated);
--sizes restricts the scope; --reuse-root re-verifies and reuses completed directories (metadata snapshot exported, no new calls), refuses a valid cache of ANOTHER request
(batch / purpose / scale) with a reason, and refuses a tampered array (partial registry); --d2-ref-root refuses directories that are not the accepted D-2 ledger units."""
import os, sys, json, shutil, subprocess
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine.d3_bank import verify_twelve_bank_dir
from step1_engine.d3_profile import twelve_context
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); MT = os.environ.get('B3_MT', '/home/claude/mt'); PC = os.environ.get('PHASEC_ROOT', '/home/claude/phaseC'); SCRIPT = os.path.join(P, 'd', 'd3_bankgen.py')
need_ext = pytest.mark.skipif(not (os.path.exists(os.path.join(MT, 't1_engine.py')) and os.path.isdir(PC)), reason='external assets not present')
ST = ('--selftest-scale', '0.001', '--selftest-skip-a10', '--selftest-skip-env-lock')


def _run(out, *extra, family='E2'):
    env = dict(os.environ, PIP_BREAK_SYSTEM_PACKAGES='1', OPENBLAS_NUM_THREADS='1')
    return subprocess.run([sys.executable, SCRIPT, '--mt', MT, '--phaseb', P, '--phasec', PC, '--out', str(out), '--family', family, *extra], capture_output=True, text=True, env=env, timeout=250)


def _man(out): return json.load(open(os.path.join(out, 'd3_run_manifest.json')))


@need_ext
def test_generation_script_preflight_scope_and_selftest_run(tmp_path):
    o = tmp_path / 'o'; o.mkdir(); (o / 'x').write_text('x'); assert _run(o).returncode == 2                                                          # fresh-only OUT
    r = _run(tmp_path / 'env', '--selftest-scale', '0.001', '--selftest-configs', '20104', '--selftest-skip-a10'); m = _man(tmp_path / 'env')
    assert r.returncode == 1 and m['stage'] == 'environment' and m['directories'] == {} and m['D3B_PASS'] is False                                  # env hard gate stops before generation (sandbox)
    r = _run(tmp_path / 'fw', *ST, '--selftest-configs', '20101'); m = _man(tmp_path / 'fw')
    assert r.returncode == 1 and m['stage'] == 'scope' and m['gates']['G_scope_resolved'] is False and m['directories'] == {} and 'first-wave' in json.dumps(m)   # first-wave id: FIXED D-2 input, never generated
    r = _run(tmp_path / 'sz', *ST, '--sizes', 'L1.20', '--selftest-configs', '20104'); m = _man(tmp_path / 'sz')
    assert m['stage'] == 'scope' and m['scope']['generate'] == [20204 + i for i in range(9)] and m['scope']['fixed_first_wave'] == [20201, 20202, 20203]         # 20104 is L1.00: outside the L1.20 run
    r = _run(tmp_path / 'bad_size', *ST, '--sizes', 'L2.00'); assert _man(tmp_path / 'bad_size')['stage'] == 'scope'
    r = _run(tmp_path / 'e1', *ST, family='E1'); assert _man(tmp_path / 'e1')['stage'] == 'scope'
    # self-test run: one added configuration, scale 0.001 -> 10 / 30 / 2 clusters
    r = _run(tmp_path / 'ok', *ST, '--selftest-configs', '20104'); m = _man(tmp_path / 'ok')
    assert m['stage'] == 'complete' and m['D3B_PASS'] is False and m['gates']['G_all_configurations'] is True and m['gates']['G_calibration_bank_matches_a10'] is None and r.returncode == 1   # env gate False (sandbox) -> exit 1; never D3B_PASS under self-test
    assert set(m['directories']) == {'cfg20104_b0', 'cfg20104_b1', 'cfg20104_fit'} and m['scope']['generate'] == [20104 + i for i in range(9)] + [20204 + i for i in range(9)] + [20304 + i for i in range(9)] and m['sizes'] == ['L1.00', 'L1.20', 'L1.50']
    ci = m['covariance_intake']['20104']; assert ci['origin'] == 'twelve_added_D3a' and ci['pc1_status'] == 'PC1_PASS' and set(ci['root_sha256']) == {'model_matched', 'model_native', 'ref_native'} and ci['roots_info']['matched']['clip'] == 0
    regj = json.load(open(tmp_path / 'ok' / 'd3_bank_registry.json')); ctx = twelve_context(P)
    assert regj['schema'] == 'd3_bank_registry_v1' and regj['formal'] is False and len(regj['calls']) == 3 and all(c['key_gaussian'][0] == 20260912 for c in regj['calls']) and len(regj['ledger']) == 3 and set(regj['required_requests']) == set(m['directories'])
    assert regj['spec_v2_sha256'] == ctx.pins['bank_spec_v2_sha256'] and regj['covariance_receipt_sha256'] == ctx.identities['covariance_receipt_sha256'] and regj['d2_family_reference']['units']['ref_E2_b0']['n_rows'] == 1000000 and len(regj['d2_family_reference']['ref_matched_root_sha256']) == 64
    for name, v in m['directories'].items():
        mm = verify_twelve_bank_dir(v['path'], ctx); assert mm['manifest_sha256'] == v['manifest_sha256'] and mm['formal'] is False and mm['origin'] == 'twelve_added' and v['request']['root_sha256'] == mm['root_sha256'] == ci['root_sha256']
        side = json.load(open(os.path.join(v['path'], mm['shards'][0]['sidecar']))); assert side['environment']['producer']['digest'] == m['producer']['digest'] and side['environment']['producer']['spec_v2_sha256'] == regj['spec_v2_sha256']
    assert m['directories']['cfg20104_b0']['n_clusters'] == 10 and m['directories']['cfg20104_b1']['n_clusters'] == 30 and m['directories']['cfg20104_fit']['n_clusters'] == 2
    # R-D3BT1-A: the registry is published as a whole-document snapshot; the receipt (SHA / bytes of the read-back bytes) is bound into the run manifest and equals the file
    import hashlib; rb = open(tmp_path / 'ok' / 'd3_bank_registry.json', 'rb').read(); rec = m['published_evidence']['d3_bank_registry.json']
    assert rec == dict(sha256=hashlib.sha256(rb).hexdigest(), bytes=len(rb)) and m['publication_stage'] == 'bank_registry_verified' and json.loads(rb) == regj and not (tmp_path / 'ok' / 'd3_bank_registry.json.tmp').exists()
    mb = open(tmp_path / 'ok' / 'd3_run_manifest.json', 'rb').read(); assert json.loads(mb) == m and not (tmp_path / 'ok' / 'd3_run_manifest.json.tmp').exists()
    # reuse-root: completed directories are re-verified against the context and reused (no regeneration; metadata snapshot exported; no new calls)
    r2 = _run(tmp_path / 'reuse', *ST, '--selftest-configs', '20104', '--reuse-root', str(tmp_path / 'ok')); m2 = _man(tmp_path / 'reuse')
    assert m2['stage'] == 'complete' and all(v['reused'] for v in m2['directories'].values()) and m2['directories']['cfg20104_b0']['manifest_sha256'] == m['directories']['cfg20104_b0']['manifest_sha256']
    assert all(os.path.exists(os.path.join(v['dependency_metadata'], 'COMPLETE.json')) for v in m2['directories'].values()) and json.load(open(tmp_path / 'reuse' / 'd3_bank_registry.json'))['calls'] == []
    # a valid cache of ANOTHER request (batch / purpose) is refused with a reason; another scale is refused
    for name, src in (('cfg20104_b0', 'cfg20104_b1'), ('cfg20104_b0', 'cfg20104_fit')):
        mm_ = tmp_path / ('mm_' + src); shutil.copytree(tmp_path / 'ok', mm_); shutil.rmtree(mm_ / name); shutil.copytree(mm_ / src, mm_ / name)
        _run(tmp_path / ('o_' + src), *ST, '--selftest-configs', '20104', '--reuse-root', str(mm_)); m4 = _man(tmp_path / ('o_' + src)); assert m4['stage'] != 'complete' and 'differs from the current request' in json.dumps(m4)
    _run(tmp_path / 'o_scale', '--selftest-scale', '0.002', '--selftest-skip-a10', '--selftest-skip-env-lock', '--selftest-configs', '20104', '--reuse-root', str(tmp_path / 'ok')); assert _man(tmp_path / 'o_scale')['stage'] != 'complete'
    # tampered array in the reuse root -> refused (exception stage; partial registry)
    bad = tmp_path / 'bad'; shutil.copytree(tmp_path / 'ok', bad); f = bad / 'cfg20104_b1' / 'cfg20104_b1_s2.npz'; z = dict(np.load(f)); z['model_native__float64__T1'][0] += 1e-9; np.savez(f, **z)
    r3 = _run(tmp_path / 'reuse_bad', *ST, '--selftest-configs', '20104', '--reuse-root', str(bad)); m3 = _man(tmp_path / 'reuse_bad')
    assert r3.returncode == 1 and m3['stage'] == 'exception' and json.load(open(tmp_path / 'reuse_bad' / 'd3_bank_registry.json'))['status'] == 'PARTIAL_AFTER_FAILURE'
    # --d2-ref-root: directories that are not the accepted D-2 ledger units are refused before any generation
    r6 = _run(tmp_path / 'ref', *ST, '--selftest-configs', '20104', '--d2-ref-root', str(tmp_path / 'ok')); m6 = _man(tmp_path / 'ref')
    assert r6.returncode == 1 and m6['stage'] == 'd2_reference' and m6['gates']['G_d2_reference_dirs'] is False and m6['directories'] == {}


@need_ext
def test_registry_publication_detects_write_faults(tmp_path, monkeypatch):
    """R-D3BT1-A (in-process, TEST-ONLY fault injection on json.dump): a registry whose written bytes differ from the computed snapshot (one field changed on the way to disk)
    is never certified — G_registry_saved stays False, the stage is 'exception', the run manifest carries the failure, no .tmp is left behind."""
    import importlib.util, io, contextlib, copy
    spec = importlib.util.spec_from_file_location('d3_bankgen_under_test', SCRIPT); S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
    real = json.dump
    def faulty(obj, fh, *a, **kw):
        if str(getattr(fh, 'name', '')).endswith(('d3_bank_registry.json', 'd3_bank_registry.json.tmp')) and isinstance(obj, dict) and obj.get('status') != 'PARTIAL_AFTER_FAILURE':
            obj = copy.deepcopy(obj); obj['family'] = 'E8'
        return real(obj, fh, *a, **kw)
    monkeypatch.setattr(json, 'dump', faulty)
    out = tmp_path / 'o'; monkeypatch.setattr(sys, 'argv', ['d3_bankgen.py', '--mt', MT, '--phaseb', P, '--phasec', PC, '--out', str(out), '--family', 'E2', *ST, '--selftest-configs', '20104'])
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()): rc = S.main()
    m = _man(out); assert rc == 1 and m['stage'] == 'exception' and m['gates']['G_registry_saved'] is False and m['publication_stage'] == 'bank_registry' and any('differs from the computed snapshot' in f for f in m['failures'])
    assert not (out / 'd3_bank_registry.json.tmp').exists() and json.load(open(out / 'd3_run_manifest.json')) == m
    # the partial registry written on the failure path is itself published through the verified helper (family field intact there)
    pr = json.load(open(out / 'd3_bank_registry.json')); assert pr['status'] == 'PARTIAL_AFTER_FAILURE' and pr['family'] == 'E2' and 'partial_registry_publication' in m


@pytest.mark.parametrize('returncode,scriptpass', [(0, True), (0, False), (1, True), (1, False), (-9, 'missing'), (-9, 'invalid'), (0, 'list'), (0, 'null')])
def test_notebook_launcher_final_pass_requires_both(tmp_path, monkeypatch, returncode, scriptpass):
    """The Colab launcher (cells 3 / 4 of d/MirrorTopology_Step1_D3b_bankgen_v0.1.ipynb, executed here with stubs; no external process): D3B_PASS of the final record requires
    BOTH script return code 0 AND the run manifest's D3B_PASS; the audit zip carries the non-NPZ metadata (completion manifests / sidecars / registry), never the arrays."""
    import types, io, contextlib, zipfile, hashlib
    out = tmp_path / 'nbout'; do = out / 'd3b'; (do / 'cfg20104_b0').mkdir(parents=True)
    fallback = isinstance(scriptpass, str)                                                                                # R-D3BT1-B: child record missing / malformed / wrong type
    rm = {'D3B_PASS': scriptpass, 'gates': {}, 'directories': {}, 'scope': {}}
    if not fallback: (do / 'd3_run_manifest.json').write_text(json.dumps(rm))
    elif scriptpass != 'missing': (do / 'd3_run_manifest.json').write_text({'invalid': '{', 'list': '[]', 'null': 'null'}[scriptpass])
    (do / 'cfg20104_b0' / 'COMPLETE.json').write_text('{}'); (do / 'cfg20104_b0' / 'cfg20104_b0_s0.npz').write_bytes(b'\0' * 10)
    import subprocess as _sp; monkeypatch.setattr(_sp, 'run', lambda *a, **k: types.SimpleNamespace(returncode=returncode, stdout='TEST_ONLY', stderr=''))
    nb = json.load(open(os.path.join(P, 'd', 'MirrorTopology_Step1_D3b_bankgen_v0.1.ipynb'))); src = lambda i: ''.join(nb['cells'][i]['source'])
    ns = dict(sys=sys, subprocess=_sp, json=json, OUT=str(out), SCRIPT='TEST_ONLY', MT='TEST_ONLY', PHASEB=P, PHASEC='TEST_ONLY', FAMILY='E2', SZ=['L1.00'], REUSE_ROOT='', D2_REF_ROOT='')
    with contextlib.redirect_stdout(io.StringIO()): exec(compile(src(4), 'nb_cell4', 'exec'), ns)
    expect = (returncode == 0 and scriptpass is True); assert ns['script_ok'] is expect and (out / 'launcher_script_stdout.txt').exists()
    if fallback: assert ns['rm']['launcher_fallback'] is True and ns['rm']['D3B_PASS'] is False and ns['rm']['stage'] == 'RECORD_MISSING_OR_INVALID' and any(f'script returncode {returncode}' == f for f in ns['rm']['failures'])
    actual = tmp_path / 'audit.zip'; real_zip = zipfile.ZipFile; fake = types.ModuleType('zipfile'); fake.ZIP_DEFLATED = zipfile.ZIP_DEFLATED; fake.ZipFile = lambda _p, *a, **k: real_zip(actual, *a, **k); monkeypatch.setitem(sys.modules, 'zipfile', fake)
    colab = types.ModuleType('google.colab'); colab.files = types.SimpleNamespace(download=lambda p: None); monkeypatch.setitem(sys.modules, 'google.colab', colab)
    nsos = types.SimpleNamespace(walk=os.walk, path=types.SimpleNamespace(join=os.path.join, relpath=os.path.relpath, getsize=lambda p: actual.stat().st_size if str(p).startswith('/content/d3b_') else os.path.getsize(p)))
    ns2 = dict(os=nsos, json=json, sha=lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest(), OUT=str(out), RUN=str(out.parent), FAMILY='E2', SZ=['L1.00'], REPO_COMMIT='a' * 40, lock={'sizes': ['L1.00']}, rc=types.SimpleNamespace(returncode=returncode, stderr=''), rm=ns['rm'], script_ok=ns['script_ok'])
    with contextlib.redirect_stdout(io.StringIO()): exec(compile(src(5), 'nb_cell5', 'exec'), ns2)
    final = json.load(open(out / 'd3b_final_record.json')); names = real_zip(actual).namelist()
    assert final['D3B_PASS'] is expect and final['stages']['launcher_fallback'] is fallback and final['stages']['stage'] == ns['rm'].get('stage') and final['sizes'] == ['L1.00'] and 'd3b/cfg20104_b0/COMPLETE.json' in names and not any(n.endswith('.npz') for n in names) and final['output_inventory']['d3b/cfg20104_b0/cfg20104_b0_s0.npz']['sha256'] is None
