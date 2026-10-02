# -*- coding: utf-8 -*-
"""D-3b tranche 2 contracts: (1) the generation ledger (registered_assets/d3b/d3b_generation_ledger.json) is a deterministic re-derivation from the nine registered run records
(lock / final / run manifest / registry / 27 COMPLETE + 45 sidecars / executed notebook per partition) bound to the verified context, bank spec v2 and the accepted generation
lock constants; any edit of the ledger (even with the payload SHA re-stamped) or of a registered record is refused; NPZ arrays must not be registered; (2) the sealed D3bUnits
view (243 units / 405 expected NPZ identities) and its unit / partition lookups; (3) d3_bank.intake_twelve_bank formal path requires the registered units and refuses a
directory that is not an accepted unit (a small bank that re-verifies against the context is not a registered bank); formal=False unchanged; (4) the read-only verifier
d/d3b_verify_banks.py: test mode on a synthetic 27-unit self-test run (all units ok, cid equal across the partition), accepted mode bound to the ledger (binding passes on the
registered records; units fail without the Drive NPZ), tampered records / output overlap / non-ledger D-2 reference refused, partial coverage never exit 0; (5) the verify
notebook's final pass condition (rc 0 AND all_ok AND coverage AND binding; fallback on a missing / invalid report)."""
import os, sys, json, copy, shutil, subprocess, hashlib
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine import d3b_ledger as dl
from step1_engine.d3b_ledger import build_d3b_ledger, verify_d3b_ledger, load_registered_d3b_ledger, intake_registered_d3b_units, D3bUnits, GENERATION_LOCK
from step1_engine.d3_bank import intake_twelve_bank, generate_twelve_configuration_bank, generate_twelve_fitting_bank
from step1_engine.d2_bank import generate_configuration_bank, generate_fitting_bank, CallInventory, load_bank_spec, _sha
from step1_engine.d2_rng import load_crn_table
from step1_engine.d3_profile import twelve_context
from step1_engine.errors import InputContractError
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); MT = os.environ.get('B3_MT', '/home/claude/mt'); PC = os.environ.get('PHASEC_ROOT', '/home/claude/phaseC'); VERIFY = os.path.join(P, 'd', 'd3b_verify_banks.py'); GEN = os.path.join(P, 'd', 'd3_bankgen.py')
need_ext = pytest.mark.skipif(not (os.path.exists(os.path.join(MT, 't1_engine.py')) and os.path.isdir(PC)), reason='external assets not present')
CTX = twelve_context(P); LEDGER = json.load(open(os.path.join(P, 'registered_assets', 'd3b', 'd3b_generation_ledger.json'))); PINS = json.load(open(os.path.join(P, 'd', 'd3_pins.json')))
PARTS = [f'{f}_{s}' for f in ('E2', 'E7', 'E8') for s in ('L1.00', 'L1.20', 'L1.50')]


def _copy_root(tmp_path):
    r = tmp_path / 'phaseB'; (r / 'registered_assets').mkdir(parents=True); shutil.copytree(os.path.join(P, 'd'), r / 'd'); shutil.copytree(os.path.join(P, 'tests', 'assets'), r / 'tests' / 'assets')
    for k in ('d1', 'd3', 'd3b'): shutil.copytree(os.path.join(P, 'registered_assets', k), r / 'registered_assets' / k)
    for k in ('d2',): shutil.copytree(os.path.join(P, 'registered_assets', k), r / 'registered_assets' / k)
    shutil.copy(os.path.join(P, 'registered_assets', 'b3_2_twelve_assets.json'), r / 'registered_assets'); return str(r)


def _restamp(doc):
    d = copy.deepcopy(doc); d['ledger_sha256'] = dl._payload_sha(d); return d


def test_ledger_deterministic_registered_and_edit_refused(tmp_path):
    L = build_d3b_ledger(P, CTX); assert L == LEDGER == build_d3b_ledger(P, CTX) and L['ledger_sha256'] == PINS['d3b_ledger_sha256'] and verify_d3b_ledger(LEDGER, P, CTX) == LEDGER
    reg = load_registered_d3b_ledger(P, CTX); assert reg['ledger_sha256'] == L['ledger_sha256'] and reg['_file_sha256'] == hashlib.sha256(open(os.path.join(P, 'registered_assets', 'd3b', 'd3b_generation_ledger.json'), 'rb').read()).hexdigest()
    assert L['totals'] == dict(partitions=9, configurations=81, directories=243, npz_files=405, npz_bytes=27217472580, seconds=L['totals']['seconds'], calls=243) and abs(L['totals']['seconds'] - 74586.372) < 0.01 and list(L['partitions']) == PARTS
    assert L['source_lock'] == GENERATION_LOCK and L['array_acceptance']['status'] == 'PENDING' and len(L['environment_note']['raw_fingerprints']) == 7 and len(L['environment_note']['order_independent_identities']) == 1
    for key, p in L['partitions'].items():
        assert len(p['units']) == 27 and p['npz_files'] == 45 and p['npz_bytes'] == 3024163620 and p['configuration_ids'] == [{'E2': 2, 'E7': 3, 'E8': 4}[key[:2]] * 10000 + {'L1.00': 1, 'L1.20': 2, 'L1.50': 3}[key[3:]] * 100 + 4 + i for i in range(9)] and all(p['gates'][g] is True for g in p['gates']) and p['a10_max_rel'] == 0.0 and p['producer_digest'] == GENERATION_LOCK['producer_digest']
        assert p['environment'] == dict(python='3.13.15', numpy='2.1.3', scipy='1.16.3', healpy='1.20.0', pot='0.9.7.post1', camb='2.0.4') and p['records']['executed_notebook']['bytes'] > 0
        for name, u in p['units'].items():
            assert u['n_rows'] == (200000 if u['purpose'] == 'fitting' else (1000000 if u['batch_id'] == 0 else 3000000)) and sum(v['bytes'] for v in u['npz'].values()) in (80003636, 240010908, 16003636) and all(len(v['sha256']) == 64 for v in u['npz'].values())
    # edits of the ledger are refused even when re-stamped
    for edit in ('unit', 'partition', 'lock', 'array', 'totals'):
        bad = copy.deepcopy(LEDGER)
        if edit == 'unit': bad['partitions']['E2_L1.00']['units']['cfg20104_b0']['manifest_sha256'] = '0' * 64
        elif edit == 'partition': bad['partitions'].pop('E8_L1.50')
        elif edit == 'lock': bad['source_lock']['commit'] = 'a' * 40
        elif edit == 'array': bad['array_acceptance']['status'] = 'ACCEPTED'
        else: bad['totals']['npz_files'] = 404
        with pytest.raises(InputContractError): verify_d3b_ledger(bad, P, CTX)
        with pytest.raises(InputContractError): verify_d3b_ledger(_restamp(bad), P, CTX)
    # edits of a registered record are refused at re-derivation (and the registered file therefore no longer verifies)
    for edit in ('complete', 'sidecar', 'run_manifest', 'registry', 'npz_present', 'lock_commit'):
        root = _copy_root(tmp_path / edit); d = os.path.join(root, 'registered_assets', 'd3b', 'runs', 'E7_L1.20_20260930T163102Z', 'out')
        if edit == 'complete':
            p = os.path.join(d, 'd3b', 'cfg30205_b1', 'COMPLETE.json'); m = json.load(open(p)); m['position_index'] = 5; m['manifest_sha256'] = _sha(json.dumps({k: v for k, v in m.items() if k != 'manifest_sha256'}, sort_keys=True).encode()); open(p, 'w').write(json.dumps(m, indent=1))
        elif edit == 'sidecar':
            p = os.path.join(d, 'd3b', 'cfg30205_b1', 'cfg30205_b1_s2.npz.sidecar.json'); s = json.load(open(p)); s['bytes'] += 1; open(p, 'w').write(json.dumps(s, indent=1))
        elif edit == 'run_manifest':
            p = os.path.join(d, 'd3b', 'd3_run_manifest.json'); m = json.load(open(p)); m['gates']['G_env_lock'] = False; open(p, 'w').write(json.dumps(m, indent=1))
        elif edit == 'registry':
            p = os.path.join(d, 'd3b', 'd3_bank_registry.json'); m = json.load(open(p)); m['directories']['cfg30205_fit']['manifest_sha256'] = '0' * 64; open(p, 'w').write(json.dumps(m, indent=1))
        elif edit == 'npz_present': open(os.path.join(d, 'd3b', 'cfg30205_b0', 'cfg30205_b0_s0.npz'), 'wb').write(b'\0' * 8)
        else:
            p = os.path.join(d, 'launcher_lock.json'); m = json.load(open(p)); m['commit'] = 'b' * 40; open(p, 'w').write(json.dumps(m, indent=1))
        with pytest.raises(InputContractError): build_d3b_ledger(root, CTX)                                                 # a context of another root is refused
        cx = twelve_context(root)
        with pytest.raises(InputContractError): build_d3b_ledger(root, cx)
        with pytest.raises(InputContractError): load_registered_d3b_ledger(root, cx)
    # pins binding: a ledger whose identity differs from the pins is refused even if self-consistent
    root = _copy_root(tmp_path / 'pins'); pp = os.path.join(root, 'd', 'd3_pins.json'); pins = json.load(open(pp)); pins['d3b_ledger_sha256'] = '0' * 64; open(pp, 'w').write(json.dumps(pins, indent=1))
    cx = twelve_context(root); assert build_d3b_ledger(root, cx) == LEDGER
    with pytest.raises(InputContractError): load_registered_d3b_ledger(root, cx)
    for notctx in (dict(CTX._d), None, LEDGER):
        with pytest.raises(InputContractError): build_d3b_ledger(P, notctx)


def test_registered_units_sealed_view_and_formal_intake_binding(tmp_path):
    U = intake_registered_d3b_units(P, CTX); assert isinstance(U, D3bUnits) and U.verified and len(U.unit_names) == 243 and U.ledger_sha256 == PINS['d3b_ledger_sha256']
    u = U.unit('cfg40312_fit'); assert u['config_id'] == 40312 and u['purpose'] == 'fitting' and u['partition'] == 'E8_L1.50' and u['run_id'] == '20261001T132201Z' and set(u['npz']) == {'cfg40312_fit_s0.npz'} and u['manifest_sha256'] == LEDGER['partitions']['E8_L1.50']['units']['cfg40312_fit']['manifest_sha256']
    assert U.partition_of(30205)['key'] == 'E7_L1.20' and U.require_unit_manifest('cfg40312_fit', u['manifest_sha256'], 200000, 'fitting')['config_id'] == 40312
    for bad in (('cfg40312_fit', '0' * 64, 200000, 'fitting'), ('cfg40312_fit', u['manifest_sha256'], 200001, 'fitting'), ('cfg40312_fit', u['manifest_sha256'], 200000, 'evaluation'), ('cfg40301_b0', u['manifest_sha256'], 1000000, 'evaluation'), ('ref_E8_b0', u['manifest_sha256'], 1000000, 'evaluation')):
        with pytest.raises(InputContractError): U.require_unit_manifest(*bad)
    with pytest.raises(InputContractError): U.partition_of(40301)                                                       # first-wave id: not a D-3b unit
    with pytest.raises(InputContractError): D3bUnits(dict(U._d))
    with pytest.raises(AttributeError): U.ledger_sha256 = 'x'
    v = U.partitions; v['E2_L1.00']['units'].clear(); assert len(U.partitions['E2_L1.00']['units']) == 27                      # views are copies
    # formal intake: registered units required; a small bank that re-verifies against the context is NOT an accepted unit
    import importlib.util; spec = importlib.util.spec_from_file_location('t1', os.path.join(P, 'tests', 'test_d3b_tranche1.py')); H = importlib.util.module_from_spec(spec); spec.loader.exec_module(H)
    k = H._Kern(); inv = CallInventory(); cid = 20104; roots, d, df = H._gen_cfg(tmp_path, cid, k, inv); rd, rf = H._gen_ref(tmp_path, 'E2', k, inv); full = dict(roots, ref_matched=H.S_ISO)
    s, info = intake_twelve_bank(cid, 'matched', d, rd, df, rf, full, CTX, formal=False); assert s.config_id == cid and info['d3b_ledger_sha256'] is None
    s2, _ = intake_twelve_bank(cid, 'native', d, rd, df, rf, full, CTX, formal=False, registered_units=U); assert s2.system == 'native'
    with pytest.raises(InputContractError): intake_twelve_bank(cid, 'matched', d, rd, df, rf, full, CTX, formal=True)                      # registered units required
    with pytest.raises(InputContractError): intake_twelve_bank(cid, 'matched', d, rd, df, rf, full, CTX, formal=True, registered_units=LEDGER)
    with pytest.raises(InputContractError): intake_twelve_bank(cid, 'matched', d, rd, df, rf, full, CTX, formal=True, registered_units=U)   # not an accepted unit (manifest SHA)


def _man(out): return json.load(open(out))


@need_ext
def test_readonly_verifier_test_mode_and_accepted_binding(tmp_path):
    env = dict(os.environ, PIP_BREAK_SYSTEM_PACKAGES='1', OPENBLAS_NUM_THREADS='1')
    run = tmp_path / 'run'; g = subprocess.run([sys.executable, GEN, '--mt', MT, '--phaseb', P, '--phasec', PC, '--out', str(run / 'd3b'), '--family', 'E7', '--sizes', 'L1.20', '--selftest-scale', '0.001', '--selftest-skip-a10', '--selftest-skip-env-lock'], capture_output=True, text=True, env=env, timeout=200)
    assert json.load(open(run / 'd3b' / 'd3_run_manifest.json'))['stage'] == 'complete' and len(os.listdir(run / 'd3b')) == 30
    def verify(out, root, *extra): return subprocess.run([sys.executable, VERIFY, '--phaseb', P, '--run-root', str(root), '--out', str(out), *extra], capture_output=True, text=True, env=env, timeout=200)
    r = verify(tmp_path / 'v_test', run, '--mode', 'test'); v = _man(tmp_path / 'v_test' / 'd3b_verify_E7_L1.20.json')
    assert r.returncode == 0 and v['all_ok'] and v['coverage_complete'] and v['accepted_run_binding'] is False and v['verification_scope'] == 'test' and len(v['units']) == 27 and all(u['arrays_verified_against_sidecar'] and u['ok'] for u in v['units'].values()) and v['cid_correspondence_ok'] and v['verifier_source']['source_bound'] and v['verifier_source']['ledger_bound'] and v['d3b_ledger_sha256'] == PINS['d3b_ledger_sha256']
    assert all(s['matches_manifest'] and s['matches_ledger'] is None and s['inventory_bytes_match'] is None for u in v['units'].values() for s in u['shards']) and v['units']['cfg30204_b1']['n_rows'] == 3000 and v['n0_plus_3n0_structure_ok']
    # partial coverage never exits 0; output overlap refused; tampered array refused
    r2 = verify(tmp_path / 'v_part', run, '--mode', 'test', '--max-dirs', '2'); v2 = _man(tmp_path / 'v_part' / 'd3b_verify_E7_L1.20.json'); assert r2.returncode == 1 and v2['coverage_complete'] is False and v2['verification_scope'] == 'test_partial' and len(v2['checked_units']) == 2
    assert verify(run / 'd3b' / 'inside', run, '--mode', 'test').returncode == 2
    bad = tmp_path / 'bad'; shutil.copytree(run, bad); f = bad / 'd3b' / 'cfg30204_b0' / 'cfg30204_b0_s0.npz'; z = dict(np.load(f)); z['model_native__float64__T1'][0] += 1e-9; np.savez(f, **z)
    import re; rg = bad / 'd3b' / 'd3_bank_registry.json'; open(rg, 'w').write(re.sub(r'/[^"]*?/run/d3b', str(bad / 'd3b'), open(run / 'd3b' / 'd3_bank_registry.json').read()))
    r3 = verify(tmp_path / 'v_bad', bad, '--mode', 'test'); v3 = _man(tmp_path / 'v_bad' / 'd3b_verify_E7_L1.20.json'); assert r3.returncode == 1 and v3['all_ok'] is False and 'cfg30204_b0' in v3['failures'] and v3['units']['cfg30204_b0']['ok'] is False and sum(u['ok'] for u in v3['units'].values()) == 26
    # accepted mode: the registered records bind (relocated run root mapped), units fail without the Drive NPZ; tampered registry / lock refused before any array
    reg = os.path.join(P, 'registered_assets', 'd3b', 'runs', 'E7_L1.20_20260930T163102Z', 'out')
    r4 = verify(tmp_path / 'v_acc', reg, '--mode', 'accepted', '--max-dirs', '1'); v4 = _man(tmp_path / 'v_acc' / 'd3b_verify_E7_L1.20.json')
    assert r4.returncode == 1 and v4['accepted_run_binding'] is True and v4['verification_scope'] == 'accepted_full_partial' and v4['generator_source']['commit'] == GENERATION_LOCK['commit'] and v4['generator_source']['run_id'] == '20260930T163102Z' and v4['units']['cfg30204_b0']['ok'] is False and 'relocated' in json.dumps(v4['notes'])
    for edit in ('registry', 'lock', 'final'):
        t = tmp_path / ('acc_' + edit); shutil.copytree(reg, t)
        p = {'registry': t / 'd3b' / 'd3_bank_registry.json', 'lock': t / 'launcher_lock.json', 'final': t / 'd3b_final_record.json'}[edit]; m = json.load(open(p))
        if edit == 'registry': m['directories']['cfg30204_b0']['manifest_sha256'] = '0' * 64
        elif edit == 'lock': m['commit'] = 'c' * 40
        else: m['D3B_PASS'] = False
        open(p, 'w').write(json.dumps(m, indent=1))
        r5 = verify(tmp_path / ('v_' + edit), t, '--mode', 'accepted'); v5 = _man(tmp_path / ('v_' + edit) / 'd3b_verify_E7_L1.20.json'); assert r5.returncode == 1 and v5['stage'] == 'binding' and v5['accepted_run_binding'] is None and 'units' not in v5
    # a run of another partition under accepted mode with a mismatching unit set is refused; non-ledger D-2 reference refused before arrays
    import importlib.util; spec = importlib.util.spec_from_file_location('t1b', os.path.join(P, 'tests', 'test_d3b_tranche1.py')); H = importlib.util.module_from_spec(spec); spec.loader.exec_module(H)
    refroot = tmp_path / 'refs'; refroot.mkdir(); H._gen_ref(refroot, 'E7', H._Kern(), CallInventory())
    r6 = verify(tmp_path / 'v_ref', run, '--mode', 'test', '--d2-ref-root', str(refroot)); v6 = _man(tmp_path / 'v_ref' / 'd3b_verify_E7_L1.20.json'); assert r6.returncode == 1 and v6['stage'] == 'd2_reference' and v6['d2_reference']['verified'] is False and 'units' not in v6
    # R-D3BT2-A: the D-2 reference root (and its units) is a protected input — even the failure report is not written there (rc 2, no file); a relocated run whose unit is a
    # symlink to an external directory protects the resolved target after the automatic path map
    import hashlib as _h
    def tree(d): return {str(f.relative_to(d)): _h.sha256(f.read_bytes()).hexdigest() for f in __import__('pathlib').Path(d).rglob('*') if f.is_file()}
    b_ref = tree(refroot); r7 = verify(refroot / 'review', run, '--mode', 'test', '--d2-ref-root', str(refroot)); assert r7.returncode == 2 and tree(refroot) == b_ref and not (refroot / 'review').exists()
    r7b = verify(refroot / 'ref_E7_b0' / 'review', reg, '--mode', 'accepted', '--d2-ref-root', str(refroot)); assert r7b.returncode == 2 and tree(refroot) == b_ref
    reloc = tmp_path / 'reloc'; shutil.copytree(reg, reloc); ext = tmp_path / 'external_bank'; shutil.move(str(reloc / 'd3b' / 'cfg30204_b0'), str(ext)); (reloc / 'd3b' / 'cfg30204_b0').symlink_to(ext, target_is_directory=True); b_ext = tree(ext)
    r8 = verify(ext / 'review', reloc, '--mode', 'accepted', '--max-dirs', '1'); assert r8.returncode == 2 and tree(ext) == b_ext and not (ext / 'review').exists()
    # R-D3BT2-B: the D-2 reference cid is derived from bytes whose SHA equals the verified manifest; a reference changed after its verification is refused (not reported verified)
    import importlib.util as _iu; vspec = _iu.spec_from_file_location('d3b_verify_under_test', VERIFY); V = _iu.module_from_spec(vspec); vspec.loader.exec_module(V)
    from step1_engine import d2_bank as _d2
    man0 = _d2.verify_bank_dir(str(refroot / 'ref_E7_b0'), ('ref_matched',)); cid_sha, rec = V._verified_reference_cid(str(refroot / 'ref_E7_b0'), man0); assert len(cid_sha) == 64 and rec['manifest_sha256'] == man0['manifest_sha256'] and rec['n_rows'] == man0['n_rows'] and rec['shards'][0]['file_sha256'] == man0['shards'][0]['file_sha256']
    f = refroot / 'ref_E7_b0' / man0['shards'][0]['file']; z = dict(np.load(f)); z['ref_matched__float64__T1'][0] += 1000.0; np.savez(f, **z)
    with pytest.raises(ValueError): V._verified_reference_cid(str(refroot / 'ref_E7_b0'), man0)


@pytest.mark.parametrize('rc,report', [(0, 'ok'), (0, 'not_ok'), (1, 'ok'), (0, 'partial'), (0, 'unbound'), (-9, 'missing'), (0, 'invalid'), (0, 'list')])
def test_verify_notebook_final_pass_requires_all(tmp_path, monkeypatch, rc, report):
    import types, io, contextlib
    out = tmp_path / 'out'; (out / 'report').mkdir(parents=True)
    base = dict(stage='complete', all_ok=True, coverage_complete=True, accepted_run_binding=True, verification_scope='accepted_full', cid_correspondence_ok=True, failures=[], seconds=1.0)
    if report == 'not_ok': base['all_ok'] = False
    elif report == 'partial': base['coverage_complete'] = False
    elif report == 'unbound': base['accepted_run_binding'] = False
    if report in ('ok', 'not_ok', 'partial', 'unbound'): (out / 'report' / 'd3b_verify_E2_L1.00.json').write_text(json.dumps(base))
    elif report != 'missing': (out / 'report' / 'd3b_verify_E2_L1.00.json').write_text({'invalid': '{', 'list': '[]'}[report])
    import subprocess as _sp; monkeypatch.setattr(_sp, 'run', lambda *a, **k: types.SimpleNamespace(returncode=rc, stdout='TEST_ONLY', stderr=''))
    nb = json.load(open(os.path.join(P, 'd', 'MirrorTopology_Step1_D3b_verify_v0.1.ipynb'))); src = ''.join(nb['cells'][3]['source']).replace("assert not os.path.exists(f'{OUT}/report'); ", '')
    ns = dict(sys=sys, os=os, json=json, subprocess=_sp, OUT=str(out), SCRIPT='TEST_ONLY', PHASEB=P, RUN_ROOT='TEST_ONLY', FAMILY='E2', SIZE='L1.00', D2_REF_ROOT='', lock={})
    with contextlib.redirect_stdout(io.StringIO()): exec(compile(src, 'nb_cell3', 'exec'), ns)
    fin = json.load(open(out / 'verify_final_record.json')); expect = (rc == 0 and report == 'ok')
    assert ns['final_ok'] is expect and fin['verify_pass'] is expect and fin['launcher_fallback'] is (report in ('missing', 'invalid', 'list')) and (out / 'verify_stdout.txt').exists()
