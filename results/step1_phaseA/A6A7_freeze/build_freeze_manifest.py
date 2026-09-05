# -*- coding: utf-8 -*-
"""Generic freeze-manifest builder: python build_freeze_manifest.py <folder> <stage_label> <tag>
Records SHA256 of every file in the folder (scripts / outputs / reports), git placeholders, and gate summaries from any *provenance.json."""
import os, sys, json, hashlib, datetime, glob
root, label, tag = sys.argv[1], sys.argv[2], sys.argv[3]
def sha(p):
    with open(p, 'rb') as fh: return hashlib.sha256(fh.read()).hexdigest()
files = {}
for dp, _, fns in os.walk(root):
    for fn in sorted(fns):
        if fn == 'freeze_manifest.json': continue
        files[os.path.relpath(os.path.join(dp, fn), root)] = sha(os.path.join(dp, fn))
provs = {}
for p in glob.glob(os.path.join(root, '**', '*provenance*.json'), recursive=True):
    j = json.load(open(p)); provs[os.path.relpath(p, root)] = dict(script=j.get('script'), script_sha256=j.get('script_sha256'),
        gates_all_true=all(v is True for v in j.get('gates', {}).values()), n_gates=len(j.get('gates', {})), OFFICIAL=j.get('OFFICIAL'))
man = dict(schema='freeze_manifest_v1', stage=label, date=datetime.datetime.now(datetime.timezone.utc).isoformat(),
           git=dict(commit='(fill after commit)', tag=tag),
           scripts={k: v for k, v in files.items() if k.endswith('.py')},
           reports={k: v for k, v in files.items() if k.endswith('.md')},
           outputs={k: v for k, v in files.items() if not k.endswith(('.py', '.md'))},
           provenance_summary=provs)
out = os.path.join(root, 'freeze_manifest.json'); json.dump(man, open(out, 'w'), indent=1, ensure_ascii=False)
print('written', out, '/ files', len(files), '/ manifest SHA256', sha(out))
