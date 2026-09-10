# -*- coding: utf-8 -*-
"""A8 freeze-manifest builder (schema freeze_manifest_v2).
Usage:  python build_freeze_manifest.py            (run INSIDE the A8_freeze folder; the folder itself is the target)
        python build_freeze_manifest.py <path>     (or give the A8_freeze folder path explicitly)
1. Checks that every required file is present.
2. Cross-checks the archived bytes against every SHA recorded in the provenances (A8a official <-> A8b inputs, env lock, F16 manifest,
   A8b outputs, parent FAILED smoke, amendment report, notebook source-only SHAs).
3. Writes freeze_manifest.json (size + SHA256 of every file; provenance summaries; git placeholders resolved from the annotated tag).
Exits non-zero if anything is missing or inconsistent; the manifest is only written on success."""
import os, sys, json, hashlib, datetime, re

root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')
TAG = 'step1-phaseA-A8-freeze-v1.0'
def sha(p, block=8 << 20):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(block), b''): h.update(b)
    return h.hexdigest()
def canon_source(src):   # identical to t2b2_run.canon_source
    text = ''.join(src) if not isinstance(src, str) else src
    lines = [ln.rstrip() for ln in text.replace('\r\n', '\n').replace('\r', '\n').split('\n')]
    while lines and lines[-1] == '': lines.pop()
    return '\n'.join(lines)
def source_only_sha(nb_bytes):   # identical to t2b2_run.source_only_sha (all cells, canonicalised)
    nb = json.loads(nb_bytes.decode('utf-8'))
    canon = [dict(cell_type=c['cell_type'], source=canon_source(c['source'])) for c in nb.get('cells', [])]
    return hashlib.sha256(json.dumps(canon, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

REQUIRED = ['MirrorTopology_Step1_A8a_featurestack_v1.1.2.ipynb', 'MirrorTopology_Step1_A8b_scan_benchmark_v1.1.8.ipynb', 'A8b_amendment_v1.1.7.md',
            'A8_rules_v1.0.md', 'Step1_PhaseA_A8_final_report.md', 'Step1_PhaseA_A8_independent_verification.md', 'ChatGPT_audit_A8a_A8b_RESULTS_PASS_FREEZE_GO.md',
            'A8a_A8b_received_artifacts_SHA256.txt', 'F16_EXTERNAL_ARTIFACTS.md', 'a8_env_lock.json',
            'a8a/smoke/a8a_provenance.json', 'a8a/smoke/a8a_validation.csv', 'a8a/smoke/s1_Bplus_featurestack_l2_16_N16_common_v1_manifest.json',
            'a8a/official/a8a_provenance.json', 'a8a/official/a8a_validation.csv', 'a8a/official/s1_Bplus_featurestack_l2_16_N16_common_v1_manifest.json',
            'a8a/official/Console_log_of_official_A8a_featurestack_v1.1.2.txt',
            'a8b/v1.1.5_smoke_FAILED/a8b_provenance.json', 'a8b/v1.1.5_smoke_FAILED/a8b_audit_vectors.npz', 'a8b/v1.1.5_smoke_FAILED/a8b_attempts_evidence.jsonl'] + \
           [f'a8b/{m}/{f}' for m in ('smoke', 'official') for f in ('a8b_provenance.json', 'a8b_benchmark_cpu.csv', 'a8b_benchmark_gpu.csv', 'a8b_attempts_evidence.jsonl',
                                                                   'a8b_audit_vectors.npz', 'a8b_timed_audit_vectors.npz', 'a8b_timed_audit_index.json')] + \
           ['a8b/smoke/Console_log_of_smoke_A8b_scan_benchmark_v1.1.8.txt', 'a8b/official/Console_log_of_official_A8b_scan_benchmark_v1.1.8.txt']
OPTIONAL = ['a8a/smoke/Console_log_of_smoke_A8a_featurestack_v1.1.2.txt']

files = {}
for dp, _, fns in os.walk(root):
    for fn in sorted(fns):
        if fn in ('freeze_manifest.json', 'build_freeze_manifest.py') or fn.startswith('.'): continue
        rel = os.path.relpath(os.path.join(dp, fn), root).replace(os.sep, '/'); files[rel] = dict(size=os.path.getsize(os.path.join(dp, fn)), sha256=sha(os.path.join(dp, fn)))
missing = [r for r in REQUIRED if r not in files]
if missing: print('MISSING required files:'); [print('   ', m) for m in missing]; sys.exit(2)
missing_opt = [r for r in OPTIONAL if r not in files]
for rel in files:
    if 'Console' in rel:
        b = open(os.path.join(root, rel), 'rb').read()
        if b'\r\n' in b: print('ERROR: console log still has CRLF (normalise to LF before hashing):', rel); sys.exit(2)
        files[rel]['note'] = 'LF-normalised (git would normalise on commit); CRLF hash of the submitted file is in A8a_A8b_received_artifacts_SHA256.txt'
J = lambda rel: json.load(open(os.path.join(root, rel), encoding='utf-8'))
a8a_s, a8a_o = J('a8a/smoke/a8a_provenance.json'), J('a8a/official/a8a_provenance.json')
b_p, b_s, b_o = J('a8b/v1.1.5_smoke_FAILED/a8b_provenance.json'), J('a8b/smoke/a8b_provenance.json'), J('a8b/official/a8b_provenance.json')
lock = J('a8_env_lock.json')
checks = {}
# --- A8a
checks['a8a_official_status'] = (a8a_o['status'] == 'FEATURESTACK_VALID' and a8a_o['gate_inventory_exact'] is True and all(a8a_o['gates'][k] is True for k in a8a_o['required_gates']))
checks['a8a_smoke_status'] = (a8a_s['status'] == 'SMOKE_PASS' and a8a_s['gate_inventory_exact'] is True and all(a8a_s['gates'][k] is True for k in a8a_s['required_gates']))
checks['a8a_official_manifest_file_sha'] = (files['a8a/official/s1_Bplus_featurestack_l2_16_N16_common_v1_manifest.json']['sha256'] == a8a_o['manifest_file_sha256'])
checks['a8a_official_validation_csv_sha'] = (files['a8a/official/a8a_validation.csv']['sha256'] == a8a_o['outputs']['validation_csv_sha256'])
checks['a8a_smoke_validation_csv_sha'] = (files['a8a/smoke/a8a_validation.csv']['sha256'] == a8a_s['outputs']['validation_csv_sha256'])
checks['a8a_env_lock_sha'] = (files['a8_env_lock.json']['sha256'] == a8a_o['environment']['lock_sha256'])
checks['a8a_smoke_chain_sha'] = (a8a_o['diagnostics']['smoke_provenance_chain']['ok'] is True and files['a8a/smoke/a8a_provenance.json']['sha256'] == lock.get('smoke_provenance_sha256'))
nb_a = source_only_sha(open(os.path.join(root, 'MirrorTopology_Step1_A8a_featurestack_v1.1.2.ipynb'), 'rb').read())
checks['a8a_notebook_source_only_sha'] = (nb_a == a8a_o['notebook_identity']['live'] == a8a_o['notebook_identity']['head_copy'])
F16 = a8a_o['manifest']['sha256']; ext = open(os.path.join(root, 'F16_EXTERNAL_ARTIFACTS.md'), encoding='utf-8').read()
checks['F16_external_note_lists_recorded_shas'] = all(F16[k] in ext for k in ('F16_float64_file', 'F16_float32_file', 'F16_float64_array', 'F16_float32_array'))
# --- A8b
checks['a8b_official_status'] = (b_o['status'] == 'BENCHMARK_VALID' and b_o['gate_inventory_exact'] is True and all(b_o['gates'][k] is True for k in b_o['required_gates']))
checks['a8b_smoke_status'] = (b_s['status'] == 'SMOKE_PASS' and b_s['gate_inventory_exact'] is True and all(b_s['gates'][k] is True for k in b_s['required_gates']))
checks['a8b_parent_failed_status'] = (b_p['status'] == 'FAILED' and sorted(k for k, v in b_p['gates'].items() if not v) == ['G_audit_matches_timed', 'G_chunk_invariance'])
OUTMAP = dict(cpu_csv_sha256='a8b_benchmark_cpu.csv', gpu_csv_sha256='a8b_benchmark_gpu.csv', evidence_jsonl_sha256='a8b_attempts_evidence.jsonl', audit_vectors_npz_sha256='a8b_audit_vectors.npz',
              timed_audit_vectors_npz_sha256='a8b_timed_audit_vectors.npz', timed_audit_index_json_sha256='a8b_timed_audit_index.json')
for m, pv in (('smoke', b_s), ('official', b_o)):
    checks[f'a8b_{m}_outputs_sha'] = all(files[f'a8b/{m}/{fn}']['sha256'] == pv['outputs'][k] for k, fn in OUTMAP.items())
    checks[f'a8b_{m}_inputs_a8a_provenance_sha'] = (pv['inputs']['a8a_provenance_sha256'] == files['a8a/official/a8a_provenance.json']['sha256'] and pv['inputs']['manifest_sha256'] == a8a_o['manifest_file_sha256'])
    checks[f'a8b_{m}_F16_expected_sha'] = (pv['inputs']['expected']['F64_file'] == F16['F16_float64_file'] and pv['inputs']['expected']['F32_file'] == F16['F16_float32_file'] and pv['inputs']['expected']['F64_array'] == F16['F16_float64_array'] and pv['inputs']['expected']['F32_array'] == F16['F16_float32_array'])
    am = pv['amendment']
    checks[f'a8b_{m}_amendment_binding'] = (pv['gates']['G_parent_failed_smoke_binding'] is True and pv['gates']['G_parent_failed_smoke_artifacts'] is True
                                            and am['parent_failed_smoke_provenance_sha256'] == files['a8b/v1.1.5_smoke_FAILED/a8b_provenance.json']['sha256']
                                            and am['amendment_report_sha256'] == am['amendment_report_sha256_expected'] == files['A8b_amendment_v1.1.7.md']['sha256']
                                            and am['parent_raw_artifacts']['a8b_audit_vectors.npz'] == files['a8b/v1.1.5_smoke_FAILED/a8b_audit_vectors.npz']['sha256']
                                            and am['parent_raw_artifacts']['a8b_attempts_evidence.jsonl'] == files['a8b/v1.1.5_smoke_FAILED/a8b_attempts_evidence.jsonl']['sha256'])
checks['a8b_parent_outputs_sha'] = (files['a8b/v1.1.5_smoke_FAILED/a8b_audit_vectors.npz']['sha256'] == b_p['outputs']['audit_vectors_npz_sha256'] and files['a8b/v1.1.5_smoke_FAILED/a8b_attempts_evidence.jsonl']['sha256'] == b_p['outputs']['evidence_jsonl_sha256'])
nb_b = source_only_sha(open(os.path.join(root, 'MirrorTopology_Step1_A8b_scan_benchmark_v1.1.8.ipynb'), 'rb').read())
checks['a8b_notebook_source_only_sha'] = (nb_b == b_o['notebook_identity']['live'] == b_o['notebook_identity']['head_copy'] == b_s['notebook_identity']['head_copy'])
checks['a8b_smoke_official_same_child_sha'] = (b_s['child_script_sha256'] == b_o['child_script_sha256'] and b_s['gpu_child_script_sha256'] == b_o['gpu_child_script_sha256'])
# received-artifact list (auditor's CRLF hashes) must contain the non-log files' hashes exactly
recv = open(os.path.join(root, 'A8a_A8b_received_artifacts_SHA256.txt'), encoding='utf-8').read()
checks['received_list_matches_archived_non_log_files'] = all(files[rel]['sha256'] in recv for rel in files if rel.startswith(('a8a/', 'a8b/smoke', 'a8b/official')) and 'Console' not in rel)
bad = [k for k, v in checks.items() if not v]
if bad: print('CROSS-CHECK FAILED:'); [print('   ', k) for k in bad]; sys.exit(3)
D = b_o['ROUTE_DECISION']
man = dict(schema='freeze_manifest_v2', stage='Step 1 Phase A-8 (A8a v1.1.2 feature stack + A8b v1.1.8 scan benchmark) — official', date=datetime.datetime.now(datetime.timezone.utc).isoformat(),
           git=dict(origin='https://github.com/tsujikeita/mirror-topology', path='results/step1_phaseA/A8_freeze/', archive_tag=TAG,
                    archive_commit='resolved externally from the annotated tag: git ls-remote origin refs/tags/%s^{}' % TAG,
                    notebook_commits=dict(a8a_v1_1_2=a8a_o['notebook_identity']['origin_main_head'], a8b_v1_1_8=b_o['notebook_identity']['origin_main_head']),
                    dependency_commit=b_o['inputs']['mt_commit'], note='archive commit not embedded (self-reference); resolve from the tag'),
           notebook_source_only_sha256=dict(a8a_v1_1_2=nb_a, a8b_v1_1_8=nb_b), child_script_sha256=dict(cpu=b_o['child_script_sha256'], gpu=b_o['gpu_child_script_sha256']),
           a8a=dict(status=a8a_o['status'], n_required_gates=len(a8a_o['required_gates']), gates_all_true=True, flags={k: a8a_o['flags'][k] for k in ('float32_eligible_for_event_outputs', 'float32_eligible_for_axis_outputs', 'float32_eligible_for_rules')},
                    F16_sha256=F16, F16_in_git=False, env_lock_sha256=a8a_o['environment']['lock_sha256'], smoke=dict(status=a8a_s['status'], n_required_gates=len(a8a_s['required_gates']))),
           a8b=dict(status=b_o['status'], n_required_gates=len(b_o['required_gates']), gates_all_true=True, smoke=dict(status=b_s['status'], n_required_gates=len(b_s['required_gates'])),
                    environment=dict(cpu=b_o['environment']['cpu_model'], threads=b_o['registered']['threads'], gpu=b_o['environment']['gpu'], python=b_o['environment']['python'], numpy=b_o['environment']['numpy']),
                    route_decision=dict(l24={k: D['l24'][k] for k in ('route', 'selection_dtype', 'evaluation_dtype', 'sample_chunk', 'threads', 'measured_N', 'minutes_per_1e6', 'peak_increment_GB')},
                                        s2={k: D['s2']['baseline_cpu'][k] for k in ('route', 'selection_dtype', 'evaluation_dtype', 'sample_chunk', 'axis_block', 'threads', 'measured_N', 'minutes_per_1e6', 'measured_or_extrapolated_1e6', 'peak_increment_GB')},
                                        s2_production_device=D['s2']['production_device'], gpu_status=b_o['gpu_status']),
                    selection_reproducibility_measured=b_o['selection_reproducibility']['measured'], timeouts=[r for r in ['s2_feature/float64/winner/N=200000/chunk=1024/axis_block=3072 (classified timeout, TIMEOUT=3600 s)']],
                    amendment=dict(parent_failed_smoke='a8b/v1.1.5_smoke_FAILED/ (kept)', parent_provenance_sha256=b_o['amendment']['parent_failed_smoke_provenance_sha256'], report='A8b_amendment_v1.1.7.md', report_sha256=b_o['amendment']['amendment_report_sha256'],
                                   withdrawn_version='v1.1.6 (never run)', new_gate_semantics=b_o['amendment']['new_gate_semantics'])),
           cross_checks=checks, optional_missing=missing_opt, files=files, n_files=len(files))
out = os.path.join(root, 'freeze_manifest.json')
with open(out, 'w', encoding='utf-8', newline='\n') as fh: json.dump(man, fh, indent=1, ensure_ascii=False)   # UTF-8 / LF regardless of the OS default (cp932 on Windows)
print('cross-checks: %d/%d PASS' % (len(checks), len(checks)))
if missing_opt: print('optional files not present (allowed):', missing_opt)
print('written', out, '/ files', len(files), '/ manifest SHA256', sha(out))
