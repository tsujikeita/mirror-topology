# -*- coding: utf-8 -*-
"""A10 freeze-manifest builder (schema freeze_manifest_v2). Run INSIDE the A10_freeze folder:  python build_freeze_manifest.py
Checks required files, cross-checks bytes against the provenances (status/gates, output SHAs, notebook source-only SHA, v1.2.8 FAILED history,
auditor's received-artifact hashes), then writes freeze_manifest.json (UTF-8). Exits non-zero (no manifest) on any failure."""
import os, sys, json, hashlib, datetime
root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.'); TAG = 'step1-phaseA-A10-freeze-v1.0'
def sha(p, block=8 << 20):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(block), b''): h.update(b)
    return h.hexdigest()
def canon_source(src):
    text = ''.join(src) if not isinstance(src, str) else src; lines = [ln.rstrip() for ln in text.replace('\r\n', '\n').replace('\r', '\n').split('\n')]
    while lines and lines[-1] == '': lines.pop()
    return '\n'.join(lines)
def source_only_sha(nb_bytes):
    nb = json.loads(nb_bytes.decode('utf-8')); canon = [dict(cell_type=c['cell_type'], source=canon_source(c['source'])) for c in nb.get('cells', [])]
    return hashlib.sha256(json.dumps(canon, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
CK = ['a10a_calibration.npz', 'a10b_cluster_hits.npz', 'a10b_flip_evidence.npz', 'a10b_axes.npz', 'a10b_m_sensitivity.json', 'a10c_pathway.npz', 'a10c_pathway.json', 'a10d_w2.npz', 'a10d_w2.json']
REQUIRED = ['MirrorTopology_Step1_A10_v1.2.9.ipynb', 'A10_rules_v1.0.md', 'A10_design_note_v1.0.md', 'a10_w2_benchmark.json', 'Step1_PhaseA_A10_final_report.md', 'Step1_PhaseA_A10_v1.2.9_independent_verification.md',
            'ChatGPT_audit_A10_v1.2.9_A10_VALID_FREEZE_GO.md', 'A10_v1.2.9_received_artifacts_SHA256.txt', 'history/A10_version_history.md', 'history/v1.2.8_official_FAILED/a10_provenance.json'] + \
           [f'{m}/{f}' for m in ('smoke', 'official') for f in ['a10_provenance.json', f'Console_log_of_{m}_A10_v1.2.9.txt'] + [f'checkpoints/{c}' for c in CK]] + \
           [f'official/checkpoints/a10d_w2_nsub{n}.json' for n in (2000, 5000)] + [f'smoke/checkpoints/a10d_w2_nsub{n}.json' for n in (1000, 2000)]
files = {}
for dp, _, fns in os.walk(root):
    for fn in sorted(fns):
        if fn in ('freeze_manifest.json', 'build_freeze_manifest.py', 'README_FREEZE_PROCEDURE.md') or fn.startswith('.'): continue
        rel = os.path.relpath(os.path.join(dp, fn), root).replace(os.sep, '/'); files[rel] = dict(size=os.path.getsize(os.path.join(dp, fn)), sha256=sha(os.path.join(dp, fn)))
missing = [r for r in REQUIRED if r not in files]
if missing: print('MISSING required files:'); [print('   ', m) for m in missing]; sys.exit(2)
for rel in files:
    if 'Console' in rel and b'\r\n' in open(os.path.join(root, rel), 'rb').read(): print('ERROR: CRLF console log:', rel); sys.exit(2)
J = lambda rel: json.load(open(os.path.join(root, rel), encoding='utf-8'))
po, ps, pf = J('official/a10_provenance.json'), J('smoke/a10_provenance.json'), J('history/v1.2.8_official_FAILED/a10_provenance.json'); checks = {}
checks['official_status'] = (po['status'] == 'A10_VALID' and all(po['gates'][k] for k in po['required_gates']) and len(po['required_gates']) == 61 and all(po['component_status'].values()))
checks['smoke_status'] = (ps['status'] == 'SMOKE_PASS' and all(ps['gates'][k] for k in ps['required_gates']) and len(ps['required_gates']) == 54)
checks['official_outputs_sha'] = all(files[f'official/checkpoints/{f}']['sha256'] == v for f, v in po['outputs'].items()); checks['smoke_outputs_sha'] = all(files[f'smoke/checkpoints/{f}']['sha256'] == v for f, v in ps['outputs'].items())
nb = source_only_sha(open(os.path.join(root, 'MirrorTopology_Step1_A10_v1.2.9.ipynb'), 'rb').read())
checks['notebook_source_only_sha'] = (nb == po['notebook_identity']['head_copy'] == po['notebook_identity']['live'] == ps['notebook_identity']['head_copy'] == '731cb898c777d909c1d310e66731dcb78aeb1caefbf1be5582eaf0a3c97eb0a0')
checks['notebook_file_sha'] = (files['MirrorTopology_Step1_A10_v1.2.9.ipynb']['sha256'] == 'c11c41413e33754444118401c8c102b69ca430650619d409bef568f94bba1209')
checks['provenance_sha_vs_auditor'] = (files['official/a10_provenance.json']['sha256'] == 'bf5deec02568fa5c6a0ef42dc8d9d66f51278e67a39fe9ca2dc8d1a069f801f7' and files['smoke/a10_provenance.json']['sha256'] == 'a2a5fcae64e20f403306cc19e1cebcd15c01ba1894887350223513bc313ac719')
checks['environment_expected'] = (po['environment']['mismatch'] == {} and po['repo']['commit'] == '1bdd9ea8a00891d6dc3622331f6dad5b86c16c89')
checks['m_decision'] = (po['m_sensitivity']['decision']['adopted_m'] == 100 and all(po['m_sensitivity']['decision']['equivalence_verdict_5_bootstrap_seeds']))
checks['production_path'] = (po['production_path']['primary'] == 'float64' and po['production_path']['sample_chunk'] == 2000 and po['production_path']['sensitivity'] == 'float32')
checks['v1_2_8_failed_history'] = (pf['status'] == 'FAILED' and [k for k in pf['required_gates'] if not pf['gates'][k]] == ['G_cal_control_inventory'] and 'v1.2.8' in pf['notebook'])
recv = open(os.path.join(root, 'A10_v1.2.9_received_artifacts_SHA256.txt'), encoding='utf-8').read()
checks['received_list_matches_checkpoints_and_provenances'] = all(files[rel]['sha256'] in recv for rel in files if rel.startswith(('official/checkpoints', 'smoke/checkpoints')) or rel.endswith('a10_provenance.json') and rel.startswith(('official/', 'smoke/')))
bad = [k for k, v in checks.items() if not v]
if bad: print('CROSS-CHECK FAILED:'); [print('   ', k) for k in bad]; sys.exit(3)
man = dict(schema='freeze_manifest_v2', stage='Step 1 Phase A-10 (v1.2.9) — W2 estimator / orientation-cluster m / calibration pathway — official', date=datetime.datetime.now(datetime.timezone.utc).isoformat(),
           git=dict(origin='https://github.com/tsujikeita/mirror-topology', path='results/step1_phaseA/A10_freeze/', archive_tag=TAG, archive_commit='resolved externally from the annotated tag', dependency_commit=po['repo']['commit'], notebook_commit=po['notebook_identity']),
           notebook_source_only_sha256=nb, official=dict(status=po['status'], required=len(po['required_gates']), components=po['component_status'], adopted_m=po['m_sensitivity']['decision']['adopted_m'], production_path=po['production_path'], environment=po['environment']['versions']),
           smoke=dict(status=ps['status'], required=len(ps['required_gates'])), scope='Phase A design/implementation/estimator freeze; global false-support rate and final W2 trigger threshold NOT frozen', cross_checks=checks, files=files, n_files=len(files))
out = os.path.join(root, 'freeze_manifest.json')
with open(out, 'w', encoding='utf-8', newline='\n') as fh: json.dump(man, fh, indent=1, ensure_ascii=False)
print('cross-checks: %d/%d PASS' % (len(checks), len(checks))); print('written', out, '/ files', len(files), '/ manifest SHA256', sha(out))
