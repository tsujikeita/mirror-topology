# -*- coding: utf-8 -*-
"""D-3a formal partition intake / aggregation contracts (audit R-D3T2AV3-A/B): a fake run directory is built exactly like the script publishes (documents from snapshots,
published_evidence SHAs from the same bytes, output_inventory of every file incl. covariance .npy). verify_partition_run reads documents once, hashes the same bytes and binds
them to the manifest, the pins identities, the expected source and (optionally) an outer-ledger manifest SHA; aggregate_partitions accepts only VerifiedPartition. Counterexamples
from the audit: coherent rewrite of results (rel/match/status) with untouched SHAs, empty base metadata, altered cov SHA / intake fail, empty clone identity, deleted
published_evidence / inventory, env version edit with kept fingerprint, stale engine_version, extra status key, tolerance-0.25 table, case-removed table, raw dicts."""
import os, sys, json, copy, hashlib, shutil
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from step1_engine.d3_stage import verify_partition_run, aggregate_partitions, VerifiedPartition, REQUIRED_D3A_GATES, REQUIRED_ACTIONS, _env_fingerprint_of, _table_payload_sha
from step1_engine.errors import InputContractError
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); CT = json.load(open(os.path.join(P, 'd', 'd3_pc1_case_table.json'))); CM = json.load(open(os.path.join(P, 'd', 'd3_config_map.json')))
SRC = dict(engine_version='0.86.0', inventory_sha256='i' * 64, script_sha256='s' * 64, pins_sha256='p' * 64, profile='production_official')
RUN_CFG = dict(l_max=4, do_polarization=False, normalize=False, l_range=[[2, 4]], lp_range=[[2, 4]])
sha = lambda b: hashlib.sha256(b).hexdigest()

def build_run(out, family, sizes, rel=1e-8, mut=None):
    """Fake D-3a run directory publishing like the script (TEST-ONLY numbers)."""
    os.makedirs(os.path.join(out, 'cov_cache')); env = dict(schema='d3_env_lock_v1', python='3.13.15', versions=dict(numpy='2.1.3'), requirements_sha256='r' * 64, platform=dict(machine='x'), blas_lapack='b', cmbtopology_commit='0cc65e34f03df85e92f738686bff0a476132f337'); env['env_fingerprint'] = _env_fingerprint_of(env, RUN_CFG)
    new = [c for c in CT['new_point_cases'] if c['family'] == family and (sizes is None or c['size_id'] in sizes)]; anc = [c for c in CT['first_wave_anchor_cases'] if c['family'] == family and (sizes is None or c['size_id'] in sizes)]
    rng = np.random.default_rng(0); regs = {}; cases = {}; files = {}
    def npy(name):
        arr = rng.standard_normal((21, 21)); b = arr.tobytes(); p = os.path.join(out, 'cov_cache', name); np.save(p, arr); fb = open(p, 'rb').read(); files[f'cov_cache/{name}'] = fb; return sha(fb), sha(b)
    for c in {c['config_id']: c for c in new}.values():
        fs, as_ = npy(f'cov_base_{c["config_id"]}.npy'); regs[str(c['config_id'])] = dict(config_id=c['config_id'], family=family, size_id=c['size_id'], cov_file=f'cov_cache/cov_base_{c["config_id"]}.npy', cov_file_sha256=fs, cov_array_sha256=as_, intake=dict(pass_=True), bound_load=dict(file_sha256=fs, array_sha256=as_, loader_meta_sha=as_))
    tol = CT['contract']['tolerance']['match_rel_lt']
    for c in new + anc:
        fs, as_ = npy(f'cov_clone_{c["case_id"].replace(":", "_")}.npy'); cases[c['case_id']] = dict(case_id=c['case_id'], config_id=c['config_id'], action=c['action'], evaluation='EVALUATED', rel=float(rel), match=bool(rel < tol), tolerance_match_rel_lt=tol, clone_cov_file=f'cov_cache/cov_clone_{c["case_id"].replace(":", "_")}.npy', clone_identity=dict(file_sha256=fs, array_sha256=as_, loader_meta_sha=as_), D_sha256='d' * 64)
    status = {}
    for cid in {v['config_id'] for v in cases.values()}:
        rs = [v for v in cases.values() if v['config_id'] == cid]; req = REQUIRED_ACTIONS[family]; status[str(cid)] = dict(actions_required=req, actions_evaluated=sorted(x['action'] for x in rs), status=('PC1_PASS' if sorted(x['action'] for x in rs) == sorted(req) and all(x['match'] for x in rs) else 'PC1_FAIL'), max_rel=max(x['rel'] for x in rs))
    sel = dict(family=family, sizes=sizes, selftest_configs=None, selftest_skip_anchors=False)
    docs = {'d3_cov_registry.json': dict(schema='d3_cov_registry_v1', family=family, selection=sel, case_table_sha256=CT['table_sha256'], config_map_sha256=CM['map_sha256'], env_fingerprint=env['env_fingerprint'], run_config=RUN_CFG, source=dict(SRC), configurations=regs),
            'd3_pc1_results.json': dict(schema='d3_pc1_results_v1', family=family, selection=sel, case_table_sha256=CT['table_sha256'], config_map_sha256=CM['map_sha256'], env_fingerprint=env['env_fingerprint'], source=dict(SRC), cases=cases, configuration_status=status),
            'd3_partial_evidence.json': dict(schema='d3_partial_evidence_v1', family=family, status='COMPLETE', bases=regs, cases=cases, failed=[]), 'd3_env_lock.json': env}
    rm = dict(D3_PASS=True, stage='complete', failures=[], family=family, engine_version=SRC['engine_version'], source=dict(SRC), gates={g: True for g in REQUIRED_D3A_GATES}, selection=sel, pc1_status=status, env_lock=env)
    if mut: mut(docs, rm, files)
    pub = {}
    for name, doc in docs.items():
        b = json.dumps(doc, indent=1, default=str).encode(); open(os.path.join(out, name), 'wb').write(b); files[name] = b; pub[name] = dict(sha256=sha(b), bytes=len(b), value_level_readback_ok=True)
    rm['published_evidence'] = dict(documents=pub, value_level_readback_ok=True); rm['output_inventory'] = {k: dict(sha256=sha(v), bytes=len(v)) for k, v in files.items()}
    rmb = json.dumps(rm, indent=1, default=str).encode(); open(os.path.join(out, 'd3_run_manifest.json'), 'wb').write(rmb); return sha(rmb)

def test_intake_and_formal_aggregation_normal_and_fail_carried(tmp_path):
    shas = {}; parts = []
    for sz in ('L1.00', 'L1.20', 'L1.50'):
        d = str(tmp_path / sz); shas[sz] = build_run(d, 'E7', [sz]); parts.append(verify_partition_run(d, SRC, CT['table_sha256'], CM['map_sha256'], expected_run_manifest_sha256=shas[sz]))
    agg = aggregate_partitions(CT, 'E7', parts, SRC, CT['table_sha256']); assert agg['family_coverage_complete'] and agg['n_cases'] == 36 and agg['n_anchor_cases'] == 9 and agg['n_bases'] == 27 and agg['n_pc1_pass'] == 36 and len(agg['partitions']) == 3
    w = str(tmp_path / 'E8'); build_run(w, 'E8', None); assert aggregate_partitions(CT, 'E8', [verify_partition_run(w, SRC, CT['table_sha256'], CM['map_sha256'])], SRC, CT['table_sha256'])['n_cases'] == 72
    f = str(tmp_path / 'fail'); build_run(f, 'E7', None, rel=1.0); agg = aggregate_partitions(CT, 'E7', [verify_partition_run(f, SRC, CT['table_sha256'], CM['map_sha256'])], SRC, CT['table_sha256']); assert agg['n_pc1_fail'] == 36 and agg['family_coverage_complete']
    with pytest.raises(InputContractError): aggregate_partitions(CT, 'E7', [json.load(open(os.path.join(f, 'd3_run_manifest.json')))], SRC, CT['table_sha256'])      # raw dict refused
    agg['configuration_status']['30104']['status'] = 'X'; assert parts[0].pc1_results['configuration_status']['30104']['status'] == 'PC1_PASS'

def test_intake_refuses_rewritten_or_incomplete_runs(tmp_path):
    base = str(tmp_path / 'ok'); mh = build_run(base, 'E7', None, rel=1.0)
    # coherent rewrite of the results AFTER publication (rel / match / status) with untouched manifest identities -> bytes differ from published_evidence -> refused
    r1 = str(tmp_path / 'rw'); shutil.copytree(base, r1); pr = json.load(open(os.path.join(r1, 'd3_pc1_results.json')))
    for v in pr['cases'].values(): v['rel'] = 1e-8; v['match'] = True
    for v in pr['configuration_status'].values(): v.update(status='PC1_PASS', max_rel=1e-8)
    json.dump(pr, open(os.path.join(r1, 'd3_pc1_results.json'), 'w'), indent=1)
    with pytest.raises(InputContractError): verify_partition_run(r1, SRC, CT['table_sha256'], CM['map_sha256'])
    # rewriting the run manifest as well (published SHAs re-stamped) is refused by the outer-ledger manifest SHA
    rm = json.load(open(os.path.join(r1, 'd3_run_manifest.json'))); b = open(os.path.join(r1, 'd3_pc1_results.json'), 'rb').read(); rm['published_evidence']['documents']['d3_pc1_results.json'] = dict(sha256=sha(b), bytes=len(b), value_level_readback_ok=True); rm['output_inventory']['d3_pc1_results.json'] = dict(sha256=sha(b), bytes=len(b)); rm['pc1_status'] = pr['configuration_status']; json.dump(rm, open(os.path.join(r1, 'd3_run_manifest.json'), 'w'), indent=1)
    with pytest.raises(InputContractError): verify_partition_run(r1, SRC, CT['table_sha256'], CM['map_sha256'], expected_run_manifest_sha256=mh)
    muts = {
        'empty_base_meta': lambda d, rm, f: [d['d3_cov_registry.json']['configurations'].__setitem__(k, {}) for k in list(d['d3_cov_registry.json']['configurations'])],
        'cov_sha': lambda d, rm, f: d['d3_cov_registry.json']['configurations']['30104'].update(cov_file_sha256='0' * 64), 'intake_fail': lambda d, rm, f: d['d3_cov_registry.json']['configurations']['30104']['intake'].update(pass_=False),
        'empty_clone_identity': lambda d, rm, f: d['d3_pc1_results.json']['cases']['30104:glide_A'].update(clone_identity={}), 'gate_false': lambda d, rm, f: rm['gates'].update(G_env_lock=False),
        'env_version_edit': lambda d, rm, f: d['d3_env_lock.json']['versions'].update(numpy='TEST_WRONG'), 'stale_engine': lambda d, rm, f: rm.update(engine_version='0.85.0'),
        'extra_status': lambda d, rm, f: (d['d3_pc1_results.json']['configuration_status'].__setitem__('99999', dict(status='PC1_PASS')), rm['pc1_status'].__setitem__('99999', dict(status='PC1_PASS'))),
        'other_source': lambda d, rm, f: rm['source'].update(pins_sha256='q' * 64), 'selftest': lambda d, rm, f: rm['selection'].update(selftest_configs=[30104]),
        'table_sha': lambda d, rm, f: d['d3_pc1_results.json'].update(case_table_sha256='0' * 64), 'family_swap': lambda d, rm, f: rm.update(family='E8'),
        'npy_tamper': lambda d, rm, f: f.__setitem__('cov_cache/cov_base_30104.npy', f['cov_cache/cov_base_30104.npy'] + b'x'),
    }
    for name, mut in muts.items():
        d = str(tmp_path / ('m_' + name)); build_run(d, 'E7', None, mut=mut)
        if name == 'npy_tamper': open(os.path.join(d, 'cov_cache', 'cov_base_30104.npy'), 'ab').write(b'y')                                                # file changed after inventory
        with pytest.raises(InputContractError): verify_partition_run(d, SRC, CT['table_sha256'], CM['map_sha256'])
    # deleted published_evidence / inventory
    d = str(tmp_path / 'noinv'); build_run(d, 'E7', None); rm = json.load(open(os.path.join(d, 'd3_run_manifest.json'))); rm.pop('output_inventory'); json.dump(rm, open(os.path.join(d, 'd3_run_manifest.json'), 'w'))
    with pytest.raises(InputContractError): verify_partition_run(d, SRC, CT['table_sha256'], CM['map_sha256'])
    # a self-consistent but non-registered case table (tolerance 0.25 / case removed) is refused at aggregation
    t2 = copy.deepcopy(CT); t2['contract']['tolerance']['match_rel_lt'] = 0.25; t2['table_sha256'] = _table_payload_sha(t2)
    good = verify_partition_run(base, SRC, CT['table_sha256'], CM['map_sha256'])
    with pytest.raises(InputContractError): aggregate_partitions(t2, 'E7', [good], SRC, CT['table_sha256'])
    with pytest.raises(InputContractError): aggregate_partitions(t2, 'E7', [good], SRC, t2['table_sha256'])
    t3 = copy.deepcopy(CT); t3['new_point_cases'] = [c for c in t3['new_point_cases'] if c['config_id'] != 30104]; t3['table_sha256'] = _table_payload_sha(t3)
    with pytest.raises(InputContractError): aggregate_partitions(t3, 'E7', [good], SRC, t3['table_sha256'])
    # partition scope: moved case / missing size / overlap
    a = str(tmp_path / 'pa'); build_run(a, 'E7', ['L1.00']); b_ = str(tmp_path / 'pb'); build_run(b_, 'E7', ['L1.20'])
    va, vb = verify_partition_run(a, SRC, CT['table_sha256'], CM['map_sha256']), verify_partition_run(b_, SRC, CT['table_sha256'], CM['map_sha256'])
    with pytest.raises(InputContractError): aggregate_partitions(CT, 'E7', [va, vb], SRC, CT['table_sha256'])
    with pytest.raises(InputContractError): aggregate_partitions(CT, 'E7', [va, va, vb], SRC, CT['table_sha256'])
    with pytest.raises(InputContractError): aggregate_partitions(CT, 'E1', [], SRC, CT['table_sha256'])
