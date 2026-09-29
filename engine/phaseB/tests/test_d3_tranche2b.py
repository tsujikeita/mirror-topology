# -*- coding: utf-8 -*-
"""D-3 tranche 2b contracts (step1_engine.d3_profile): (1) the 108-position covariance receipt is a deterministic re-derivation from the registered inputs (config map / D-1 /
D-3a) and any edit — even with the payload SHA recomputed — is refused; (2) consumption-time intake re-verifies bytes / arrays / loader / roots for added points, delegates
anchors to the D-1 intake, refuses E1, non-PC1_PASS entries and tampered files (frozen checkout required; skipped otherwise); (3) the formal 12-position profile: size inputs
of exactly 12 receipt-bound configurations (weight 1/12), all-size assembly through the registered size prior (1/36), twelve grid identity validated through the existing
FamilyInput / official gate dispatch, first-wave identities unchanged, 12-position gate checks; (4) plan fixation: five-seed plans built once from the family UIDs are
shared by first-wave and added configurations and reproduce the recorded identity; (5) bank spec v2 = deterministic request (81 generate, 27 reuse with D-2 ledger identities,
f64 only, no W2) bound to map / receipt / D-2 spec / ledger."""
import os, sys, json, copy, hashlib, shutil
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine import d3_profile as dp
from step1_engine.d3_profile import build_d3_covariance_receipt, verify_d3_covariance_receipt, load_registered_receipt, intake_twelve_covariance, build_twelve_size_input, assemble_twelve_family, twelve_official_gate, fix_family_plans, verify_plan_identity, build_bank_spec_v2, verify_bank_spec_v2, load_registered_bank_spec_v2, validate_twelve_grid_identity, twelve_context, TwelveContext, TWELVE_GRID_FIELDS
from step1_engine.production import BankSupply, validate_grid_identity, _GRID_FIELDS, NATIVE_OFFSET
from step1_engine.orchestrator import FittingBank, FamilyInput
from step1_engine.types import ClusterUID
from step1_engine.rules_config import RULES
from step1_engine.errors import InputContractError
from step1_engine.grid_registry import load_registry
from step1_engine.twelve_assets import intake_registered_twelve_assets
from step1_engine.d2_rng import group_for
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); MT = os.environ.get('B3_MT', '/home/claude/mt')
need_mt = pytest.mark.skipif(not os.path.exists(os.path.join(MT, 't1_engine.py')), reason='frozen mirror-topology checkout not present')
sha = lambda b: hashlib.sha256(b).hexdigest()
CM = json.load(open(os.path.join(P, 'd', 'd3_config_map.json'))); TABLE = json.load(open(os.path.join(P, 'd', 'd2_crn_table.json'))); RC = json.load(open(os.path.join(P, 'registered_assets', 'd3', 'd3_covariance_receipt.json')))
D2S = json.load(open(os.path.join(P, 'd', 'd2_bank_spec.json'))); D2L = json.load(open(os.path.join(P, 'registered_assets', 'd2', 'd2_generation_ledger.json')))
REG = load_registry(os.path.join(P, 'tests/assets/a7_circle_geometry.csv'), os.path.join(P, 'tests/assets/a6_observer_design_points.json'))
TA = intake_registered_twelve_assets(os.path.join(P, 'registered_assets', 'b3_2_twelve_assets.json'), REG, 'B3_2A_7240c06f255c')
CTX = twelve_context(P)                                                                                                  # verified context (map / receipt / table / D-2 spec / D-2 ledger)


def _copy_root(tmp_path):
    r = tmp_path / 'phaseB'; (r / 'registered_assets').mkdir(parents=True); shutil.copytree(os.path.join(P, 'd'), r / 'd'); shutil.copytree(os.path.join(P, 'tests', 'assets'), r / 'tests' / 'assets')
    for k in ('d1', 'd3'): shutil.copytree(os.path.join(P, 'registered_assets', k), r / 'registered_assets' / k)
    return str(r)


def _restamp(doc, key):
    d = copy.deepcopy(doc); d[key] = dp._payload_sha(d, key); return d


# ------------------------------------------------------------------------------------------------------------------------------- receipt
def test_receipt_is_deterministic_registered_and_edit_refused(tmp_path):
    r = build_d3_covariance_receipt(P)
    assert r == RC and r['counts'] == dict(positions=108, first_wave_reused=27, twelve_added=81, pc1_pass=108, pc1_fail=0, consumption_allowed=108) and r['e1_first_wave_only'] == [10101, 10201, 10301]
    assert verify_d3_covariance_receipt(RC, P) == RC and load_registered_receipt(P, RC['receipt_sha256']) == RC
    ids = sorted(int(k) for k in r['positions']); assert ids == sorted(10000 * f + 100 * s + p for f in (2, 3, 4) for s in (1, 2, 3) for p in range(1, 13))
    for cid, e in r['positions'].items():
        assert e['source'] == ('first_wave_D1' if e['position_index'] < 3 else 'twelve_added_D3a') and e['pc1_status'] == 'PC1_PASS' and e['consumption_allowed'] is True and e['display_suffix'] == f"{e['position_index'] + 1:02d}"
        assert os.path.exists(os.path.join(P, e['registered_file'])) and sha(open(os.path.join(P, e['registered_file']), 'rb').read()) == e['cov_file_sha256']   # every registered file present and byte-bound
    for edit in (lambda d: d['positions']['20104'].__setitem__('pc1_status', 'PC1_FAIL'), lambda d: d['positions']['20104'].__setitem__('consumption_allowed', False), lambda d: d['positions']['20101'].__setitem__('cov_array_sha256', '0' * 64), lambda d: d['positions'].pop('40312'), lambda d: d['d3a'].__setitem__('ledger_sha256', '0' * 64)):
        bad = copy.deepcopy(RC); edit(bad); bad = _restamp(bad, 'receipt_sha256')
        with pytest.raises(InputContractError): verify_d3_covariance_receipt(bad, P)
    with pytest.raises(InputContractError): load_registered_receipt(P, '0' * 64)
    root = _copy_root(tmp_path); pins = os.path.join(root, 'd', 'd3_pins.json'); d = json.load(open(pins)); d['config_map_sha256'] = '0' * 64; json.dump(d, open(pins, 'w'))
    with pytest.raises(InputContractError): build_d3_covariance_receipt(root)                                              # config map not bound to the pins
    root = _copy_root(tmp_path / 'b'); f = os.path.join(root, RC['positions']['20104']['registered_file']); b = bytearray(open(f, 'rb').read()); b[-1] ^= 1; open(f, 'wb').write(bytes(b))
    with pytest.raises(InputContractError): build_d3_covariance_receipt(root)                                              # registered D-3a array edited -> registered intake refuses


@need_mt
def test_consumption_time_intake(tmp_path, monkeypatch):
    for name in ('t1_engine', 't2b2_bridge'): monkeypatch.delitem(sys.modules, name, raising=False)   # test-harness isolation only: a frozen-notebook test earlier in the session may leave its own t1_engine loaded; the loader's refusal to substitute is the contract under test, not this stale state
    a = intake_twelve_covariance(20104, P, MT); e = RC['positions']['20104']
    assert a['origin'] == 'twelve_added_D3a' and a['cov_array_sha256'] == e['cov_array_sha256'] and a['C_real'].shape == (21, 21) and a['eig']['min'] > 0 and a['roots_info']['matched']['clip'] == 0 and a['receipt_d3'] == RC['receipt_sha256'] and a['loader']['t1_engine_sha256'].startswith('87bf8424')
    b = intake_twelve_covariance(20101, P, MT); assert b['origin'] == 'first_wave_D1' and b['receipt'] == 'D1_aa089fa492bc' and b['cov_array_sha256'] == RC['positions']['20101']['cov_array_sha256'] and b['position_index'] == 0
    for bad in (10101, 99999, '20104', 20104.0, True):
        with pytest.raises(InputContractError): intake_twelve_covariance(bad, P, MT)
    fail = copy.deepcopy(RC); fail['positions']['20104']['pc1_status'] = 'PC1_FAIL'; fail['positions']['20104']['consumption_allowed'] = False; fail = _restamp(fail, 'receipt_sha256')
    with pytest.raises(InputContractError): intake_twelve_covariance(20104, P, MT, receipt=fail)                            # a receipt that differs from the registered derivation is refused
    root = _copy_root(tmp_path); f = os.path.join(root, RC['positions']['20305']['registered_file']); b = bytearray(open(f, 'rb').read()); b[200] ^= 1; open(f, 'wb').write(bytes(b))
    with pytest.raises(InputContractError): intake_twelve_covariance(20305, root, MT)                                      # bytes changed after registration -> refused at consumption
    with pytest.raises(InputContractError): intake_twelve_covariance(20104, P, None)


# ------------------------------------------------------------------------------------------------------------------------------- profile fixture (TEST-ONLY numbers)
class Fixture:
    """CRN-faithful synthetic banks for one family on the REAL config map / receipt: one evaluation latent per family (all positions, sizes, systems), one fitting latent;
    plans fixed once from the family UIDs (family evaluation group of the CRN table)."""
    def __init__(self, family='E2', sizes=('L1.00', 'L1.20', 'L1.50'), K=40, m=5, Kf=60, mf=5, B=20, seed=2026):
        self.family, self.sizes = family, list(sizes); rng = np.random.default_rng(seed); self.z = rng.standard_normal((K * m, 2)); self.zf = np.random.default_rng(seed + 1).standard_normal((Kf * mf, 2))
        g = group_for(TABLE, 'evaluation', family); self.uids = [ClusterUID(1, 200, g, 0, i) for i in range(K)]
        self.plans, self.fplans, self.plan_identity = fix_family_plans(TABLE, family, {0: self.uids}, Kf, TABLE['master_seed'], B=B, B_KDE=25); self.cidf = np.repeat(np.arange(Kf), mf); self.K, self.m = K, m

    def supplies(self, size, system, ids=None, cov_override=None):
        rows = [r for r in CM['configurations'] if r['family'] == self.family and r['size_id'] == size]; out = []
        for r in rows:
            cid = r['config_id']
            if ids is not None and cid not in ids: continue
            e = RC['positions'][str(cid)]; sh = np.array([.5 + .01 * r['position_index'], .4]) * (1.0 if system == 'matched' else 1.1); unit = np.array([40, 200]); loc = np.array([120, 600])
            ref = self.z * unit + loc; mod = (self.z - sh) * unit + loc; fb = FittingBank((self.zf - sh) * unit + loc, self.zf * unit + loc, self.cidf)
            cov = dict(cov_file_sha256=e['cov_file_sha256'], cov_array_sha256=e['cov_array_sha256']) if cov_override is None else cov_override
            out.append(BankSupply(cid, system, mod[:, 0], mod[:, 1], ref[:, 0], ref[:, 1], list(self.uids), self.m, {0: (0, self.K * self.m)}, fb, cov, None))
        return out

    def size_input(self, size, system, **kw): return build_twelve_size_input(CTX, self.family, size, system, self.supplies(size, system, **kw), self.plans, self.fplans)
    def family_inputs(self): return assemble_twelve_family(CTX, self.family, {s: (self.size_input(s, 'matched'), self.size_input(s, 'native')) for s in self.sizes})


def test_twelve_profile_size_inputs_assembly_and_gate():
    fx = Fixture('E2'); fm1 = fx.size_input('L1.00', 'matched'); gi = fm1.grid_identity
    assert len(fm1.configs) == 12 and all(abs(c.weight - 1 / 12) < 1e-15 for c in fm1.configs) and set(gi) == TWELVE_GRID_FIELDS and gi['stage'] == 'twelve' and gi['covariance_receipt_sha256'] == RC['receipt_sha256'] and gi['config_map_sha256'] == CM['map_sha256']
    assert sorted(gi['evaluation_to_config'].values()) == list(range(20101, 20113)) and {gi['position_index'][e] for e in gi['position_index']} == set(range(12)) and all(v['pc1_status'] == 'PC1_PASS' for v in gi['cov_bound'].values())
    fn1 = fx.size_input('L1.00', 'native'); assert sorted(fn1.grid_identity['evaluation_to_config']) == [70101 + i for i in range(12)]
    fm, fn, ident = fx.family_inputs()
    assert len(fm.configs) == 36 and len(fn.configs) == 36 and all(abs(c.weight - 1 / 36) < 1e-15 for c in fm.configs + fn.configs) and ident['stage'] == 'twelve' and ident['full_surviving_scope'] is True and ident['size_weights'] == {s: REG.size_prior['E2'][s] for s in fx.sizes}
    assert fm.grid_identity['sizes'] == fx.sizes and set(fm.grid_identity['cov_bound']) == {c.evaluation_id for c in fm.configs} and {v['origin'] for v in fm.grid_identity['cov_bound'].values()} == {'first_wave_D1', 'twelve_added_D3a'}
    fm.validate(); fn.validate()                                                                                            # dispatch: FamilyInput.validate -> production.validate_grid_identity -> twelve validator
    g = twelve_official_gate(fm, fn, 'smoke')
    assert g.passed and g.mode == 'smoke' and all(c['passed'] for c in g.diagnostics['twelve_checks'] if not c['code'].endswith('plan_identity_fixed')) and 'twelve_checks' in g.diagnostics   # no plan identity supplied -> official-only failure recorded
    go = twelve_official_gate(fm, fn, 'official')                                                                         # small synthetic banks fail the registered-scale checks, never the 12-position ones
    assert not go.passed and all(c['passed'] for c in go.diagnostics['twelve_checks'] if not c['code'].endswith('plan_identity_fixed')) and any('N0' in f or 'm=' in f for f in go.required_failures)
    go2 = twelve_official_gate(fm, fn, 'official', plan_identity=fx.plan_identity, table=CTX.table); assert not go2.passed and all(c['passed'] for c in go2.diagnostics['twelve_checks'])
    # single-size family (conditional scope) assembles but is not the formal full-size scope
    fm2, fn2, ident2 = assemble_twelve_family(CTX, 'E2', {'L1.00': (fm1, fn1)})
    assert ident2['full_surviving_scope'] is False and abs(fm2.configs[0].weight - 1 / 12) < 1e-15 and not twelve_official_gate(fm2, fn2, 'official', plan_identity=fx.plan_identity, table=CTX.table).passed and twelve_official_gate(fm2, fn2, 'smoke').passed
    # refusals: 11 supplies / duplicate / wrong system / covariance identity not the receipt's / receipt with a PC1_FAIL position / weight tamper / first-wave field set on a twelve identity
    with pytest.raises(InputContractError): build_twelve_size_input(CTX, 'E2', 'L1.00', 'matched', fx.supplies('L1.00', 'matched')[:11], fx.plans, fx.fplans)
    sup = fx.supplies('L1.00', 'matched'); sup[0] = sup[1]
    with pytest.raises(InputContractError): build_twelve_size_input(CTX, 'E2', 'L1.00', 'matched', sup, fx.plans, fx.fplans)
    with pytest.raises(InputContractError): build_twelve_size_input(CTX, 'E2', 'L1.00', 'native', fx.supplies('L1.00', 'matched'), fx.plans, fx.fplans)
    with pytest.raises(InputContractError): build_twelve_size_input(CTX, 'E2', 'L1.00', 'matched', fx.supplies('L1.00', 'matched', cov_override=dict(cov_file_sha256='0' * 64, cov_array_sha256='0' * 64)), fx.plans, fx.fplans)
    for notctx in (RC, CM, dict(CTX._d), None):                                                                             # R-D3T2B-B: caller dicts (even self-hashed receipts) are never a verified context
        with pytest.raises(InputContractError): build_twelve_size_input(notctx, 'E2', 'L1.00', 'matched', fx.supplies('L1.00', 'matched'), fx.plans, fx.fplans)
    with pytest.raises(InputContractError): TwelveContext(dict(CTX._d))
    with pytest.raises(AttributeError): CTX.root = '/x'
    # R-D3T2B-B: mixed source identities across sizes / systems are refused BEFORE assembly (never relabelled with the first input)
    for field, si in (('covariance_receipt_sha256', 1), ('twelve_assets_sha256', 1), ('manifest_sha256', 0), ('registry_sha256', 1), ('config_map_sha256', 0)):
        ss = {s: (fx.size_input(s, 'matched'), fx.size_input(s, 'native')) for s in fx.sizes}; ss['L1.20'][si].grid_identity[field] = '0' * 64
        with pytest.raises(InputContractError): assemble_twelve_family(CTX, 'E2', ss)
    # R-D3T2B-B: provenance relabelling in a grid identity is refused against the verified receipt (origin, receipt id, SHA, status)
    for edit in (lambda g: g['cov_bound'][20104].__setitem__('origin', 'first_wave_D1'), lambda g: g['cov_bound'][20104].__setitem__('receipt', 'UNREGISTERED_RECEIPT'), lambda g: g['cov_bound'][20104].__setitem__('cov_file_sha256', '0' * 64), lambda g: g.__setitem__('covariance_receipt_sha256', '1' * 64), lambda g: g.__setitem__('twelve_assets_sha256', '1' * 64)):
        bad = copy.deepcopy(fm1.grid_identity); edit(bad)
        with pytest.raises(InputContractError): validate_twelve_grid_identity(bad, 'E2', 'matched', [c.evaluation_id for c in fm1.configs], [c.weight for c in fm1.configs])
    bad = copy.deepcopy(fm.grid_identity); bad['cov_bound'][20104]['pc1_status'] = 'PC1_FAIL'
    with pytest.raises(InputContractError): validate_twelve_grid_identity(bad, 'E2', 'matched', [c.evaluation_id for c in fm.configs], [c.weight for c in fm.configs])
    with pytest.raises(InputContractError): validate_twelve_grid_identity(fm.grid_identity, 'E2', 'matched', [c.evaluation_id for c in fm.configs], [c.weight * (1.01 if i == 0 else 1) for i, c in enumerate(fm.configs)])
    with pytest.raises(InputContractError): validate_grid_identity({k: v for k, v in fm.grid_identity.items() if k in _GRID_FIELDS}, 'E2', 'matched', [c.evaluation_id for c in fm.configs], None)   # 12 ids do not fit the first-wave schema
    with pytest.raises(InputContractError): validate_twelve_grid_identity(dict(fm.grid_identity, stage='first_wave'), 'E2', 'matched', [c.evaluation_id for c in fm.configs], None)
    with pytest.raises(InputContractError): assemble_twelve_family(CTX, 'E2', {'L1.00': (fm1, None), 'L1.20': (fx.size_input('L1.20', 'matched'), fx.size_input('L1.20', 'native'))})   # partial native
    with pytest.raises(InputContractError): assemble_twelve_family(CTX, 'E7', {'L1.00': (fm1, fn1)})              # family mismatch
    # plan identity connection (R-D3T2B-A): official requires the fixed identity; a different fixed identity fails the check
    gp = twelve_official_gate(fm, fn, 'smoke', plan_identity=fx.plan_identity, table=CTX.table); assert gp.passed and all(c['passed'] for c in gp.diagnostics['twelve_checks'] if c['code'].endswith('plan_identity_fixed'))
    other = fix_family_plans(CTX.table, 'E2', {0: fx.uids}, 60, CTX.table['master_seed'] + 1, B=20, B_KDE=25)[2]
    assert not twelve_official_gate(fm, fn, 'smoke', plan_identity=other, table=CTX.table).passed and any(c['code'].endswith('plan_identity_fixed') and not c['passed'] for c in go.diagnostics['twelve_checks'])


def test_plan_fixation_shared_by_first_wave_and_added_configurations():
    fx = Fixture('E7', sizes=('L1.00',)); assert verify_plan_identity(fx.plans, fx.fplans, fx.plan_identity)
    again = fix_family_plans(TABLE, 'E7', {0: fx.uids}, 60, TABLE['master_seed'], B=20, B_KDE=25); assert again[2] == fx.plan_identity and all(np.array_equal(again[0][s].multiplicities[0], fx.plans[s].multiplicities[0]) for s in range(RULES.seeds))
    fm = fx.size_input('L1.00', 'matched')
    old = [c for c in fm.configs if c.evaluation_id <= 30103]; new = [c for c in fm.configs if c.evaluation_id > 30103]
    assert len(old) == 3 and len(new) == 9 and all(c.cluster_uids == fx.plans[0].strata[0] for c in old + new)               # same family latent -> same UID order -> one plan set
    with pytest.raises(InputContractError): fix_family_plans(TABLE, 'E7', {0: [ClusterUID(1, 200, group_for(TABLE, 'evaluation', 'E2'), 0, i) for i in range(40)]}, 60, TABLE['master_seed'], B=20, B_KDE=25)   # UIDs on another family's latent
    tam = copy.deepcopy(fx.plan_identity); tam['evaluation'][0]['multiplicity_sha256']['0'] = '0' * 64; tam['identity_sha256'] = dp._payload_sha(tam, 'identity_sha256')
    with pytest.raises(InputContractError): verify_plan_identity(fx.plans, fx.fplans, tam)
    other = fix_family_plans(TABLE, 'E7', {0: fx.uids}, 60, TABLE['master_seed'] + 1, B=20, B_KDE=25)
    with pytest.raises(InputContractError): verify_plan_identity(other[0], other[1], fx.plan_identity)                     # different master seed -> different plans -> refused against the fixed identity
    assert dp.PLAN_SCHEMA_V2['bootstrap']['seeds'] == RULES.seeds and dp.PLAN_SCHEMA_V2['bootstrap']['B'] == RULES.B
    # R-D3T2B-A: every seed record required (no zip truncation), header must match the objects, evaluation UIDs must be purpose 200
    for edit in (lambda d: d.__setitem__('evaluation', d['evaluation'][:4]), lambda d: d.__setitem__('fitting', []), lambda d: d.update(seeds=0, evaluation=[], fitting=[]), lambda d: d.__setitem__('family', 'E8'), lambda d: d.__setitem__('master_seed', 1), lambda d: d.__setitem__('evaluation_group', 999), lambda d: d.__setitem__('B_KDE', 1), lambda d: d.__setitem__('B', 21), lambda d: d['evaluation'].append(dict(d['evaluation'][0])), lambda d: d['fitting'][0].__setitem__('seed_id', 1)):
        d = copy.deepcopy(fx.plan_identity); edit(d); d['identity_sha256'] = dp._payload_sha(d, 'identity_sha256')
        with pytest.raises(InputContractError): verify_plan_identity(fx.plans, fx.fplans, d)
    with pytest.raises(InputContractError): verify_plan_identity({}, {}, dict(copy.deepcopy(fx.plan_identity), seeds=0, evaluation=[], fitting=[], identity_sha256='0' * 64))
    with pytest.raises(InputContractError): verify_plan_identity(fx.plans, fx.fplans, fx.plan_identity, family='E2')
    with pytest.raises(InputContractError): verify_plan_identity(fx.plans, fx.fplans, dict(copy.deepcopy(fx.plan_identity), evaluation_group=group_for(TABLE, 'evaluation', 'E2'), identity_sha256=None), table=TABLE)
    assert verify_plan_identity(fx.plans, fx.fplans, fx.plan_identity, table=TABLE, family='E7')
    for purpose in (300, 400):
        with pytest.raises(InputContractError): fix_family_plans(TABLE, 'E7', {0: [ClusterUID(1, purpose, group_for(TABLE, 'evaluation', 'E7'), 0, i) for i in range(40)]}, 60, TABLE['master_seed'], B=20, B_KDE=25)
    with pytest.raises(InputContractError): fix_family_plans(TABLE, 'E7', {0: [ClusterUID(1, 200, group_for(TABLE, 'evaluation', 'E7'), 1, i) for i in range(40)]}, 60, TABLE['master_seed'], B=20, B_KDE=25)   # batch key / UID batch mismatch


def test_bank_spec_v2_deterministic_and_bound(tmp_path):
    spec = build_bank_spec_v2(CTX); reg = json.load(open(os.path.join(P, 'd', 'd3_bank_spec.json')))
    assert spec == reg and verify_bank_spec_v2(reg, CTX) == reg and load_registered_bank_spec_v2(CTX) == reg and spec['counts'] == dict(configurations=108, generate=81, reuse=27, generation_units=243, generation_rows_evaluation=81 * D2S['N_max'], generation_rows_fitting=81 * 200000)
    assert spec['d2_ledger_file_sha256'] == dp.D2_REGISTERED_LEDGER['ledger_file_sha256'] == sha(open(os.path.join(P, 'registered_assets', 'd2', 'd2_generation_ledger.json'), 'rb').read()) and spec['inherits'].endswith(D2S['spec_sha256']) and spec['covariance_receipt_sha256'] == RC['receipt_sha256']
    gen = [v for v in spec['configurations'].values() if v['mode'] == 'generate_D3b']; reuse = [v for v in spec['configurations'].values() if v['mode'] == 'reuse_D2_fixed_input']
    assert all(v['selections']['evaluation'] == {'0': ['float64'], '1': ['float64']} and v['selections']['required_f32_subset'] is False and v['w2_primary'] is None and v['covariance']['pc1_status'] == 'PC1_PASS' and v['position_index'] >= 3 and v['batches']['1']['rows'] == [D2S['N0'], D2S['N_max']] for v in gen)
    assert all(set(v['d2']['units']) == {f"cfg{v['config_id']}_b0", f"cfg{v['config_id']}_b1", f"cfg{v['config_id']}_fit"} and v['position_index'] < 3 and v['covariance']['receipt'] == 'D1_aa089fa492bc' for v in reuse)
    assert all(len(spec['family_reference'][f]['units']) == 3 for f in ('E2', 'E7', 'E8')) and spec['e1_first_wave_only'] == [10101, 10201, 10301]
    for edit in (lambda d: d['configurations']['20104'].__setitem__('w2_primary', {}), lambda d: d['configurations']['20104']['selections']['evaluation'].__setitem__('0', ['float64', 'float32']), lambda d: d['configurations'].pop('40312'), lambda d: d.__setitem__('N_max', 2000000)):
        bad = copy.deepcopy(reg); edit(bad); bad = _restamp(bad, 'spec_sha256')
        with pytest.raises(InputContractError): verify_bank_spec_v2(bad, CTX)
    for notctx in (CM, RC, D2S, None):                                                                                          # R-D3T2B-C: caller dicts are not a verified context
        with pytest.raises(InputContractError): build_bank_spec_v2(notctx)
    # R-D3T2B-C: the context itself refuses non-canonical upstream (stale D-2 spec / altered D-2 ledger / trimmed map+receipt / stale pins)
    counter = [0]
    def broken(edit):
        counter[0] += 1; root = _copy_root(tmp_path / f'b{counter[0]}'); shutil.copytree(os.path.join(P, 'registered_assets', 'd2'), os.path.join(root, 'registered_assets', 'd2')); shutil.copy(os.path.join(P, 'registered_assets', 'b3_2_twelve_assets.json'), os.path.join(root, 'registered_assets')); edit(root)
        with pytest.raises(InputContractError): twelve_context(root)
    def rewrite(path, fn):
        d = json.load(open(path)); fn(d); json.dump(d, open(path, 'w'), indent=1)
    broken(lambda r: rewrite(os.path.join(r, 'd', 'd2_bank_spec.json'), lambda d: d.__setitem__('N_max', 2000000)))                                       # stale D-2 spec (old spec_sha256 kept)
    broken(lambda r: rewrite(os.path.join(r, 'd', 'd2_bank_spec.json'), lambda d: d.__setitem__('master_seed', 17)))
    broken(lambda r: rewrite(os.path.join(r, 'registered_assets', 'd2', 'd2_generation_ledger.json'), lambda d: d['families']['E2']['units']['cfg20101_b0'].__setitem__('manifest_sha256', '0' * 64)))   # ledger bytes != trusted identity
    def trim(r):
        cmp_, rcp = os.path.join(r, 'd', 'd3_config_map.json'), os.path.join(r, 'registered_assets', 'd3', 'd3_covariance_receipt.json'); cm = json.load(open(cmp_)); cm['configurations'] = [x for x in cm['configurations'] if x['config_id'] != 40312]; cm['map_sha256'] = dp._map_payload_sha(cm); json.dump(cm, open(cmp_, 'w'))
        rc = json.load(open(rcp)); rc['config_map_sha256'] = cm['map_sha256']; rc['positions'].pop('40312'); rc = _restamp(rc, 'receipt_sha256'); json.dump(rc, open(rcp, 'w')); rewrite(os.path.join(r, 'd', 'd3_pins.json'), lambda d: d.update(config_map_sha256=cm['map_sha256'], covariance_receipt_sha256=rc['receipt_sha256']))
    broken(trim)                                                                                                                                             # 107-row map + matching receipt + matching pins: still not the canonical map
    broken(lambda r: rewrite(os.path.join(r, 'd', 'd3_pins.json'), lambda d: d.__setitem__('covariance_receipt_sha256', '0' * 64)))
    # a verified context is required by the registered-spec reader; pins' spec identity must match
    root = _copy_root(tmp_path / 'p'); shutil.copytree(os.path.join(P, 'registered_assets', 'd2'), os.path.join(root, 'registered_assets', 'd2')); shutil.copy(os.path.join(P, 'registered_assets', 'b3_2_twelve_assets.json'), os.path.join(root, 'registered_assets'))
    rewrite(os.path.join(root, 'd', 'd3_pins.json'), lambda d: d.__setitem__('bank_spec_v2_sha256', '0' * 64)); c2 = twelve_context(root)
    with pytest.raises(InputContractError): load_registered_bank_spec_v2(c2)
