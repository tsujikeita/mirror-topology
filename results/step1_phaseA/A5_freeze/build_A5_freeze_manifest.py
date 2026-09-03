# -*- coding: utf-8 -*-
"""Build A5_freeze_manifest.json for the A5_freeze/ package (audit §19-20)."""
import os, sys, json, hashlib, datetime
root = sys.argv[1] if len(sys.argv) > 1 else '.'
def sha(p):
    with open(p, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()
files = {}
for dp, _, fns in os.walk(root):
    for fn in sorted(fns):
        if fn == 'A5_freeze_manifest.json': continue
        rel = os.path.relpath(os.path.join(dp, fn), root)
        files[rel] = sha(os.path.join(dp, fn))
required = ['s1_phaseA5_v1.1.py', 'a5_input_manifest_v2.json', 'a5_provenance.json',
            'a5_null_selection.npz', 's1_Bstack_l2_4_N16_common_v1.npz', 's1_Bstack_l2_4_provenance.json']
missing = [r for r in required if not any(k.endswith(r) for k in files)]
assert not missing, ('欠落', missing)
bprov = [k for k in files if k.endswith('s1_Bstack_l2_4_provenance.json')][0]
bp = json.load(open(os.path.join(root, bprov)))
a5p = json.load(open(os.path.join(root, [k for k in files if k.endswith('a5_provenance.json')][0])))
man = dict(
    schema='A5_freeze_manifest_v1', date=str(datetime.date.today()),
    git=dict(commit='(fill after commit)', tag='step1-phaseA-A5-v1.0'),
    scripts={k: v for k, v in files.items() if k.endswith('.py')},
    input_manifest={k: v for k, v in files.items() if 'a5_input_manifest_v2' in k},
    outputs={k: v for k, v in files.items() if not k.endswith(('.py', '.md')) and 'a5_input_manifest_v2' not in k},
    reports={k: v for k, v in files.items() if k.endswith('.md')},
    provenance_links=dict(a5_script_sha256=a5p.get('script_sha256'),
                          bstack_script=bp.get('script'), bstack_script_sha256=bp.get('script_sha256'),
                          bstack_array_sha256=bp.get('bstack_array_sha256'),
                          a5_gates_all_true=all(v for v in a5p['gates'].values() if v is not None),
                          bstack_gates_all_true=all(bp['gates'].values())),
    science_decisions=dict(
        primary_event='E_B = {T1 <= T1_obs and T2 <= T2_obs}; mechanism decomposition Q_joint = Q_T1 x Q_noncomp',
        axis_grid=3072, pm_dedup=False, argmin='first occurrence',
        selection_dtype='float32 (primary); float64 audited-equivalent alternate',
        evaluation='float64 quadratic forms (B-stack)',
        bstack_scope='l2-4 evaluator on all 3072 axes; S1 (l2-4-only) selection surrogate',
        historical_selection='full-band Planck-smoothed N16/common map, argmin S+ over 3072 axes; '
                             'consensus rule = signal-only equivalent in simulation',
        S2_hybrid_status='HOLD (pending A8 benchmark and A11 S4 validation set)',
        design_discovery_null='N=1000 Step 0 seeds; official probabilities require a fresh stream'),
    lessons=['input manifest must be generated in the formal (Colab) environment; sandbox float references are not authoritative',
             'float input arrays compared by max|cur-ref|/max|ref| <= 1e-12; elementwise relative differences on beam-suppressed entries are diagnostics only',
             'formal run stops if the input manifest is missing (no silent manifest-generation mode)'])
out = os.path.join(root, 'A5_freeze_manifest.json')
json.dump(man, open(out, 'w'), indent=1, ensure_ascii=False)
print('written', out, '/ files:', len(files))
print('manifest SHA256 =', sha(out))
