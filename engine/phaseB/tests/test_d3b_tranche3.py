# -*- coding: utf-8 -*-
"""D-3b tranche 3 contracts: the outer receipt (registered_assets/d3b/d3b_outer_receipt.json) is a deterministic re-derivation from the nine registered read-only verification
records (report / lock / final / stdout / stderr / executed notebook) bound to the verification lock constants, the generation ledger (run ids / roots / unit manifest SHAs /
NPZ file SHA + bytes) and the acceptance conditions; any edit of the receipt (re-stamped or not) or of a registered verification record is refused; the generation ledger is
NOT rewritten (array_acceptance stays PENDING there); the sealed units view reports array_accepted only through the registered receipt; the formal path of intake_twelve_bank
requires the array-verified acceptance (a ledger-only view is refused); the read-only verifier keeps using the ledger-only view."""
import os, sys, json, copy, shutil, hashlib
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine import d3b_ledger as dl
from step1_engine.d3b_ledger import build_d3b_outer_receipt, verify_d3b_outer_receipt, load_registered_d3b_outer_receipt, intake_registered_d3b_units, load_registered_d3b_ledger, VERIFICATION_LOCK, GENERATION_LOCK, ARRAY_ACCEPTANCE
from step1_engine.d3_bank import intake_twelve_bank
from step1_engine.d2_bank import CallInventory
from step1_engine.d3_profile import twelve_context
from step1_engine.errors import InputContractError
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); CTX = twelve_context(P); PINS = json.load(open(os.path.join(P, 'd', 'd3_pins.json')))
RECEIPT = json.load(open(os.path.join(P, 'registered_assets', 'd3b', 'd3b_outer_receipt.json'))); LEDGER = json.load(open(os.path.join(P, 'registered_assets', 'd3b', 'd3b_generation_ledger.json')))
PARTS = [f'{f}_{s}' for f in ('E2', 'E7', 'E8') for s in ('L1.00', 'L1.20', 'L1.50')]


def _copy_root(tmp_path):
    r = tmp_path / 'phaseB'; (r / 'registered_assets').mkdir(parents=True); shutil.copytree(os.path.join(P, 'd'), r / 'd'); shutil.copytree(os.path.join(P, 'tests', 'assets'), r / 'tests' / 'assets')
    for k in ('d1', 'd2', 'd3', 'd3b'): shutil.copytree(os.path.join(P, 'registered_assets', k), r / 'registered_assets' / k)
    shutil.copy(os.path.join(P, 'registered_assets', 'b3_2_twelve_assets.json'), r / 'registered_assets'); return str(r)


def _restamp(doc):
    d = copy.deepcopy(doc); d['receipt_sha256'] = dl._sha(json.dumps({k: v for k, v in d.items() if k != 'receipt_sha256'}, sort_keys=True, allow_nan=False, ensure_ascii=False).encode('utf-8')); return d


def test_outer_receipt_deterministic_registered_and_bound():
    R = build_d3b_outer_receipt(P, CTX); assert R == RECEIPT == build_d3b_outer_receipt(P, CTX) and R['receipt_sha256'] == PINS['d3b_outer_receipt_sha256'] and verify_d3b_outer_receipt(RECEIPT, P, CTX) == RECEIPT
    reg = load_registered_d3b_outer_receipt(P, CTX); assert reg['receipt_sha256'] == R['receipt_sha256'] and reg['_file_sha256'] == hashlib.sha256(open(os.path.join(P, 'registered_assets', 'd3b', 'd3b_outer_receipt.json'), 'rb').read()).hexdigest()
    assert R['generation']['ledger_payload_sha256'] == LEDGER['ledger_sha256'] == PINS['d3b_ledger_sha256'] and R['generation']['source_lock'] == GENERATION_LOCK and R['verification']['commit'] == VERIFICATION_LOCK['commit'] and R['array_acceptance'] == ARRAY_ACCEPTANCE
    assert list(R['partitions']) == PARTS and R['totals'] == dict(partitions=9, units=243, npz_files=405, npz_bytes=27217472580, seconds=R['totals']['seconds']) and abs(R['totals']['seconds'] - 2028.2956) < 1e-3 and len(R['verification']['environment_identity_order_independent']) == 1
    for key, p in R['partitions'].items():
        assert p['generation_run_id'] == LEDGER['partitions'][key]['run_id'] and p['npz_bytes'] == 3024163620 and p['units'] == 27 and p['npz_files'] == 45 and p['d2_reference_verified'] and set(p['d2_reference_units']) == {f'ref_{key[:2]}_b0', f'ref_{key[:2]}_b1', f'ref_{key[:2]}_fit'} and all(len(v) == 64 for v in (p['records']['report_sha256'], p['records']['lock_sha256'], p['records']['final_sha256'])) and p['verification_environment']['camb'] is None
    # the generation ledger is unchanged (array acceptance stays PENDING there; the acceptance lives in the receipt)
    assert LEDGER['array_acceptance']['status'] == 'PENDING' and load_registered_d3b_ledger(P, CTX)['ledger_sha256'] == LEDGER['ledger_sha256']
    # receipt edits are refused even when re-stamped
    for edit in ('partition_sha', 'drop_partition', 'acceptance', 'verification', 'totals', 'statement'):
        bad = copy.deepcopy(RECEIPT)
        if edit == 'partition_sha': bad['partitions']['E7_L1.20']['records']['report_sha256'] = '0' * 64
        elif edit == 'drop_partition': bad['partitions'].pop('E8_L1.50')
        elif edit == 'acceptance': bad['array_acceptance']['decision'] = 'PASS'
        elif edit == 'verification': bad['verification']['commit'] = 'a' * 40
        elif edit == 'totals': bad['totals']['npz_files'] = 404
        else: bad['statement'] = 'x'
        with pytest.raises(InputContractError): verify_d3b_outer_receipt(bad, P, CTX)
        with pytest.raises(InputContractError): verify_d3b_outer_receipt(_restamp(bad), P, CTX)
    for notctx in (dict(CTX._d), None, RECEIPT):
        with pytest.raises(InputContractError): build_d3b_outer_receipt(P, notctx)


def test_registered_verification_record_edits_refused(tmp_path):
    for edit in ('report_flag', 'report_npz_sha', 'report_cid', 'report_d2', 'lock_commit', 'final_pass', 'stderr', 'notebook_missing', 'pins'):
        root = _copy_root(tmp_path / edit); d = os.path.join(root, 'registered_assets', 'd3b', 'verify', 'E2_L1.20'); rp = os.path.join(d, 'report', 'd3b_verify_E2_L1.20.json')
        if edit.startswith('report'):
            r = json.load(open(rp))
            if edit == 'report_flag': r['all_ok'] = False
            elif edit == 'report_npz_sha': r['units']['cfg20205_b1']['shards'][1]['file_sha256'] = '0' * 64
            elif edit == 'report_cid': r['cid_correspondence']['evaluation/b0/cfg20205']['equal_to_d2_reference'] = False
            else: r['d2_reference']['units']['ref_E2_fit']['manifest_sha256'] = '0' * 64
            open(rp, 'w').write(json.dumps(r, indent=1))
        elif edit == 'lock_commit':
            p = os.path.join(d, 'verify_lock.json'); m = json.load(open(p)); m['commit'] = 'b' * 40; open(p, 'w').write(json.dumps(m, indent=1))
        elif edit == 'final_pass':
            p = os.path.join(d, 'verify_final_record.json'); m = json.load(open(p)); m['verify_pass'] = False; open(p, 'w').write(json.dumps(m, indent=1))
        elif edit == 'stderr': open(os.path.join(d, 'verify_stderr.txt'), 'w').write('Traceback')
        elif edit == 'notebook_missing': os.remove(os.path.join(root, 'registered_assets', 'd3b', 'verify_notebooks', 'MirrorTopology_Step1_D3b_verify_v0_1_E2_L1.20_executed_269c6d56fb75.ipynb'))
        else:
            pp = os.path.join(root, 'd', 'd3_pins.json'); pins = json.load(open(pp)); pins['d3b_outer_receipt_sha256'] = '0' * 64; open(pp, 'w').write(json.dumps(pins, indent=1))
        cx = twelve_context(root)
        if edit == 'pins':
            assert build_d3b_outer_receipt(root, cx) == RECEIPT
            with pytest.raises(InputContractError): load_registered_d3b_outer_receipt(root, cx)
            with pytest.raises(InputContractError): intake_registered_d3b_units(root, cx)
            assert intake_registered_d3b_units(root, cx, require_array_acceptance=False).array_accepted is False
        else:
            with pytest.raises(InputContractError): build_d3b_outer_receipt(root, cx)
            with pytest.raises(InputContractError): intake_registered_d3b_units(root, cx)
        with pytest.raises(InputContractError): build_d3b_outer_receipt(root, CTX)


def test_units_array_acceptance_and_formal_intake_gate(tmp_path):
    U = intake_registered_d3b_units(P, CTX); U0 = intake_registered_d3b_units(P, CTX, require_array_acceptance=False)
    assert U.array_accepted is True and U.receipt_sha256 == PINS['d3b_outer_receipt_sha256'] and U.outer_receipt['receipt_sha256'] == U.receipt_sha256 and U0.array_accepted is False and U0.receipt_sha256 is None and U0.outer_receipt is None and U.unit_names == U0.unit_names
    v = U.outer_receipt; v['partitions'].clear(); assert len(U.outer_receipt['partitions']) == 9
    with pytest.raises(AttributeError): U.array_accepted = False
    import importlib.util; spec = importlib.util.spec_from_file_location('t1', os.path.join(P, 'tests', 'test_d3b_tranche1.py')); H = importlib.util.module_from_spec(spec); spec.loader.exec_module(H)
    k = H._Kern(); inv = CallInventory(); cid = 30204; roots, d, df = H._gen_cfg(tmp_path, cid, k, inv); rd, rf = H._gen_ref(tmp_path, 'E7', k, inv); full = dict(roots, ref_matched=H.S_ISO)
    s, info = intake_twelve_bank(cid, 'matched', d, rd, df, rf, full, CTX, formal=False, registered_units=U); assert s.config_id == cid and info['d3b_receipt_sha256'] is None
    with pytest.raises(InputContractError): intake_twelve_bank(cid, 'matched', d, rd, df, rf, full, CTX, formal=True, registered_units=U0)    # ledger-only view: no array acceptance
    with pytest.raises(InputContractError): intake_twelve_bank(cid, 'matched', d, rd, df, rf, full, CTX, formal=True, registered_units=U)     # accepted units, but this small bank is not one of them
