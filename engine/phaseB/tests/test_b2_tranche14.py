# -*- coding: utf-8 -*-
"""B-2 tranche 14/15: E2 streamed backend wiring; CRN-FAITHFUL 12-position fixture (one family latent, one fitting latent, shared plans, unique ids across sizes/systems);
per-size path; all-size family mixture path checked against a literal hit-expansion reference and the audit's arithmetic example (Q=5/3, not the mean 2.25)."""
import os, sys, copy
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from dataclasses import replace
from step1_engine.rules_config import RULES
from step1_engine import stage12
from step1_engine.stage12 import generate_twelve, verify_twelve, transition_after_three
from step1_engine.coordinator import plan_family_expansion, family_completion
from step1_engine.twelve_eval import evaluate_twelve_size, evaluate_twelve_family, check_twelve_family_input, evaluate_twelve_family_mixture, assemble_all_sizes, TwelveSizeResult
from step1_engine.orchestrator import ConfigBank, FittingBank, FamilyInput, evaluate_family
from step1_engine.bootstrap_plan import BootstrapPlan, FittingPlan, bank_sha256
from step1_engine.types import ClusterUID
from step1_engine.checkpoint import write_family_result, read_family_result
from step1_engine.errors import InputContractError
A7 = np.array([[.11278702805018147], [.04504442885635738], [.17608175443077442]])


def test_e2_backend_is_streamed_and_equivalent_on_small_box(monkeypatch):
    an2 = np.array([[0.2452274712376159, 0.3429926323318836], [0.07150075549277313, 0.24162711619922894], [0.8951290935216393, 0.2514647338918028]])
    m7 = generate_twelve('E7', 'L1.00', A7); assert m7.generator['backend'] == 'in_memory'
    import step1_engine.rules_config as rc
    monkeypatch.setattr(stage12, 'RULES', replace(rc.RULES, grid_resolution=2e-2)); monkeypatch.setattr(stage12, 'GENERATOR', dict(kind='greedy_maximin', grid_resolution=2e-2, tie_tol=RULES.tie_tol))
    m = generate_twelve('E2', 'L1.00', an2); assert m.generator['backend'] == 'streamed_two_pass' and len(m.points) == 12 and m.min_pairwise >= RULES.min_sep['E2']
    monkeypatch.setattr(stage12, 'STREAMED_FAMILIES', ()); m2 = generate_twelve('E2', 'L1.00', an2); assert m2.points == m.points
    monkeypatch.setattr(stage12, 'STREAMED_FAMILIES', ('E2',)); assert verify_twelve(m)


class TwelveFixture:
    """CRN-faithful synthetic family: ONE evaluation latent z (shared by every size, position and system), ONE fitting latent, ONE evaluation plan set and ONE fitting plan set;
    evaluation ids unique across sizes and systems (matched 1000*(si+1)+j, native = matched + 500 by explicit map, not by inference)."""
    def __init__(self, sizes=('L1.00', 'L1.20'), K=160, m=10, Kf=400, mf=10, B=60, seed=140026, shifts=None):
        self.sizes = list(sizes); rng = np.random.default_rng(seed); self.z = rng.standard_normal((K * m, 2)); self.zf = np.random.default_rng(seed + 1).standard_normal((Kf * mf, 2))
        self.uids = [ClusterUID(1, 200, 11, 0, i) for i in range(K)]; self.plans = {s: BootstrapPlan.build(f'fam-s{s}', s, {0: self.uids}, B, seed + 2) for s in range(RULES.seeds)}
        self.fplans = {s: FittingPlan.build(f'fit-s{s}', 1, 21, s, Kf, 20, seed + 3) for s in range(RULES.seeds)}; cidf = np.repeat(np.arange(Kf), mf)
        self.manifests = {s: generate_twelve('E7', s, A7) for s in self.sizes}; self.inputs = {}; self.maps = {}; self.nmaps = {}
        for si, s in enumerate(self.sizes):
            pair = []
            for system in ('matched', 'native'):
                scale = 1.0 if system == 'matched' else (0.85 + 0.12 * si); cfg, fit, bind, pmap = [], {}, {}, {}
                for j in range(12):
                    eid = 1000 * (si + 1) + j + (500 if system == 'native' else 0); sh = (np.array([.6 + .3 * si, .55 + .2 * si]) if shifts is None else shifts[s]) * (1 + .01 * j)
                    unit = np.array([40, 200]) * scale; loc = np.array([120, 600]); ref = self.z * unit + loc; mod = (self.z - sh) * unit + loc
                    cfg.append(ConfigBank(eid, 'E7', system, 1 / 12, mod[:, 0], mod[:, 1], ref[:, 0], ref[:, 1], self.uids, m, {0: (0, K * m)}))
                    fb = FittingBank((self.zf - sh) * unit + loc, self.zf * unit + loc, cidf); fit[eid] = fb; bind[eid] = bank_sha256(fb.X_model, fb.X_ref, fb.cid); pmap[eid] = j
                pair.append(FamilyInput('E7', cfg, self.plans, fit, self.fplans, True, bind))
                (self.maps if system == 'matched' else self.nmaps)[s] = pmap
            self.inputs[s] = tuple(pair)


def test_fixture_is_crn_faithful():
    fx = TwelveFixture(); f1m, f1n = fx.inputs['L1.00']; f2m, _ = fx.inputs['L1.20']
    assert f1m.configs[0].cluster_uids == f1n.configs[0].cluster_uids == f2m.configs[0].cluster_uids
    zm = np.c_[f1m.configs[0].T1_ref - 120, f1m.configs[0].T2_ref - 600] / [40, 200]; zn = np.c_[f1n.configs[0].T1_ref - 120, f1n.configs[0].T2_ref - 600] / [34, 170]
    assert np.allclose(zm, zn, rtol=0, atol=1e-12) and np.array_equal(f1m.configs[0].T1_ref, f2m.configs[0].T1_ref)                 # same latent across systems and sizes
    assert all(f1m.fit_plans[s] is f1n.fit_plans[s] is f2m.fit_plans[s] for s in range(5)) and f1m.plans is f2m.plans
    ids = [c.evaluation_id for s in fx.sizes for f in fx.inputs[s] for c in f.configs]; assert len(ids) == len(set(ids)) == 48
    assert f1m.validate() is not None and f1m.fitting_plan_binding == 'bound'


def test_per_size_and_all_size_family_mixture_against_literal_reference():
    fx = TwelveFixture(); thr = (100.0, 550.0)
    per = evaluate_twelve_family(fx.inputs, fx.manifests, fx.maps, *thr, staged=False, native_position_ids=fx.nmaps)
    for s in fx.sizes: assert per[s]['evidence']['stage'] == '12-position' and len(per[s]['per_config']) == 12 and per[s]['evidence']['position_ids_native'] is not None
    sw = {s: 0.5 for s in fx.sizes}; g = evaluate_twelve_family_mixture(fx.inputs, fx.manifests, fx.maps, sw, *thr, staged=False, native_position_ids=fx.nmaps)
    assert g['evidence']['stage'] == '12-position-family' and g['evidence']['identity']['n_configs'] == 24 and abs(sum(g['evidence']['matched']['prior']) - 1) < 1e-12 and set(g['per_size_diagnostic']) == set(fx.sizes)
    # literal hit-expansion reference for the family-mixed numerators/denominators (both systems, 5 seeds)
    gm, gn, _ = assemble_all_sizes(fx.inputs, fx.manifests, fx.maps, sw, fx.nmaps); K, m = 160, 10
    for side, fam, ev in (('matched', gm, g['evidence']['matched']), ('native', gn, g['native']['evidence'])):
        for seed, plan in fx.plans.items():
            num = np.zeros(plan.replicates); den = np.zeros(plan.replicates)
            for c in fam.configs:
                hm = ((c.T1_model <= thr[0]) & (c.T2_model <= thr[1])).reshape(K, m).sum(1); hi = ((c.T1_ref <= thr[0]) & (c.T2_ref <= thr[1])).reshape(K, m).sum(1)
                for r in range(plan.replicates):
                    cnt = plan.multiplicities[0][r]; num[r] += c.weight * np.repeat(hm, cnt).sum() / (K * m); den[r] += c.weight * np.repeat(hi, cnt).sum() / (K * m)
            assert np.allclose(num, ev['per_seed'][seed]['num'], rtol=0, atol=1e-14) and np.allclose(den, ev['per_seed'][seed]['den'], rtol=0, atol=1e-14)
    # the family value is the ratio of size-mixed probabilities (in this fixture the matched reference is identical across sizes, so it coincides with the mean of per-size Q;
    # the native reference differs per size, where the mean would be wrong — see test_audit_arithmetic_example_Q_five_thirds for the general case)
    PM = sum(0.5 * np.mean([d['P_model'] for d in per[s]['per_config'].values()]) for s in fx.sizes); PI = sum(0.5 * np.mean([d['P_ref'] for d in per[s]['per_config'].values()]) for s in fx.sizes)
    assert g['Q_point'] == pytest.approx(PM / PI, rel=1e-12)
    PMn = sum(0.5 * np.mean([d['P_model'] for d in per[s]['native']['per_config'].values()]) for s in fx.sizes); PIn = sum(0.5 * np.mean([d['P_ref'] for d in per[s]['native']['per_config'].values()]) for s in fx.sizes)
    assert g['native']['Q_point'] == pytest.approx(PMn / PIn, rel=1e-9) and g['native']['Q_point'] != pytest.approx(np.mean([per[s]['native']['Q_point'] for s in fx.sizes]), rel=1e-6)


def test_audit_arithmetic_example_Q_five_thirds():
    from step1_engine.family import mixed_numden
    num, den = mixed_numden(np.array([[.08, .02]]), np.array([[.02, .04]]), np.array([.5, .5])); assert float(num[0] / den[0]) == pytest.approx(5 / 3) and np.mean([4, .5]) == 2.25


def test_entry_contracts_and_explicit_native_map():
    fx = TwelveFixture(); s = 'L1.00'; fm, fn = fx.inputs[s]; m = fx.manifests[s]; pm = fx.maps[s]
    with pytest.raises(InputContractError): evaluate_twelve_family({}, {}, {}, 80., 400., staged=False)
    with pytest.raises(InputContractError): evaluate_twelve_size(fm, fn, m, s, pm, 80., 400., False)                                       # native input without an explicit native map
    with pytest.raises(InputContractError): check_twelve_family_input(fm, m, {k: float(v) for k, v in pm.items()})
    with pytest.raises(InputContractError): check_twelve_family_input(fm, m, {k: (bool(v) if v < 2 else v) for k, v in pm.items()})
    npm = {k: int(v) for k, v in pm.items()}; assert check_twelve_family_input(fm, m, {k: np.int64(v) for k, v in npm.items()}) == npm      # NumPy ints normalised
    gm, gn = copy.deepcopy(fm), copy.deepcopy(fn)
    for f in (gm, gn):
        f.family = 'E8'
        for c in f.configs: c.family = 'E8'
    A8 = np.array([[.21609142351830096, .1388778490467109], [.10991624390681737, .06676051199330066], [.4225612190131215, .125548183938205]]); m8 = generate_twelve('E8', 'L1.20', A8)
    with pytest.raises(InputContractError): evaluate_twelve_family({s: (fm, fn), 'L1.20': (gm, gn)}, {s: m, 'L1.20': m8}, {s: pm, 'L1.20': pm}, 80., 400., staged=False, native_position_ids={s: fx.nmaps[s], 'L1.20': fx.nmaps[s]})
    with pytest.raises(InputContractError): evaluate_twelve_family(fx.inputs, fx.manifests, fx.maps, 80., 400., staged=False, native_position_ids=fx.nmaps, expected_sizes=['L1.00', 'L1.20', 'L1.50'])
    with pytest.raises(InputContractError): assemble_all_sizes(fx.inputs, fx.manifests, fx.maps, {'L1.00': .6, 'L1.20': .6}, fx.nmaps)
    bad = copy.deepcopy(fx.inputs); bad['L1.20'] = (replace(bad['L1.20'][0], plans={k: BootstrapPlan.build(f'other-s{k}', k, {0: fx.uids}, 60, 999) for k in range(5)}), bad['L1.20'][1])
    with pytest.raises(InputContractError): assemble_all_sizes(bad, fx.manifests, fx.maps, {'L1.00': .5, 'L1.20': .5}, fx.nmaps)               # plans not shared across sizes
    a = copy.deepcopy(fm); a.configs = a.configs[:11]
    with pytest.raises(InputContractError): check_twelve_family_input(a, m, {k: v for k, v in pm.items() if v < 11})
    fx2 = TwelveFixture(sizes=('L1.00', 'L1.20')); fx2.inputs['L1.20'] = fx2.inputs['L1.00']                                                    # id reuse across sizes
    with pytest.raises(InputContractError): assemble_all_sizes(fx2.inputs, fx2.manifests, fx2.maps, {'L1.00': .5, 'L1.20': .5}, fx2.nmaps)


def test_twelve_results_archive_roundtrip_and_completion(tmp_path):
    fx = TwelveFixture(); per = evaluate_twelve_family(fx.inputs, fx.manifests, fx.maps, 100., 550., staged=False, native_position_ids=fx.nmaps)
    rec = TwelveSizeResult('E7', 'L1.00', fx.manifests['L1.00'].sha256, fx.maps['L1.00'], fx.nmaps['L1.00'], per['L1.00'], 'per-size diagnostic'); p = str(tmp_path / 'size.json')
    sha = write_family_result(rec, p); got = read_family_result(p, sha); assert got['result']['size_id'] == 'L1.00' and got['result']['evidence']['twelve_manifest_sha256'] == fx.manifests['L1.00'].sha256 and got['verified'].startswith('verified')
    g = evaluate_twelve_family_mixture(fx.inputs, fx.manifests, fx.maps, {s: .5 for s in fx.sizes}, 100., 550., staged=False, native_position_ids=fx.nmaps)
    p2 = str(tmp_path / 'fam.json'); sha2 = write_family_result(g, p2); got2 = read_family_result(p2, sha2); assert got2['result']['evidence']['stage'] == '12-position-family' and got2['verified'].startswith('verified')
    src = lambda s: dict(family='E7', size_id=s, truths=dict(support=True, strong=False, unsupported=False), decision=dict(technical_status='ok'), precision=dict(state='pass'), evidence=dict(coverage_ok=True))
    tr = {'L1.00': transition_after_three('E7', 'L1.00', src('L1.00'), dict(state='position-sensitive', expand=True), fx.manifests['L1.00']), 'L1.20': transition_after_three('E7', 'L1.20', src('L1.20'), dict(state='not-expanded', expand=False), None)}
    plan = plan_family_expansion('E7', fx.sizes, tr, manifests=fx.manifests); comp = family_completion(plan, per, {s: 'not-expanded' for s in fx.sizes}, fx.manifests)
    assert set(comp['per_size']) == set(fx.sizes) and comp['final_label_released'] is False
