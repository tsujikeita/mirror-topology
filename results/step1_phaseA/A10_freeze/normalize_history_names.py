# -*- coding: utf-8 -*-
"""Rename the 16 history files whose Japanese filenames were mangled by the Windows ZIP extraction (UTF-8 read as Shift-JIS) to ASCII names.
Files are identified by SHA256 (content unchanged). Run INSIDE results/step1_phaseA/A10_freeze:  python normalize_history_names.py
Then: python build_freeze_manifest.py  ->  git add -A results/step1_phaseA/A10_freeze  ->  commit."""
import os, hashlib, subprocess, re
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(8 << 20), b''): h.update(b)
    return h.hexdigest()
def ascii_name(fn):
    m = re.match(r'ChatGPT.*_Step1_PhaseA_A10_v(\d(?:_\d)*)_.*\.md$', fn)
    if m: return f'ChatGPT_audit_A10_v{m.group(1).replace("_", ".")}.md'
    m = re.match(r'Step1_PhaseA_A10_v(\d+(?:\.\d+)*)_', fn)          # the mangled names may have lost the '.' of '.md' (e.g. '...蜻・md'), so do not require a '.md' suffix
    if m: return f'Step1_PhaseA_A10_v{m.group(1)}_implementation_report.md'
    if fn.startswith('Step1_PhaseA_A10_') and 'v1.0' in fn: return 'Step1_PhaseA_A10_v1.0_implementation_report.md'
    return None
n = 0
for sub in ('history/audits', 'history/implementation_reports'):
    for fn in sorted(os.listdir(sub)):
        if all(ord(c) < 128 for c in fn): continue
        new = ascii_name(fn); assert new, fn; src, dst = os.path.join(sub, fn), os.path.join(sub, new); assert not os.path.exists(dst), dst
        h = sha(src); r = subprocess.run(['git', 'mv', src, dst], capture_output=True, text=True)
        if r.returncode != 0: os.rename(src, dst)
        assert sha(dst) == h; print(f'{sub}/{new}  <-  (renamed, sha {h[:12]})'); n += 1
print('renamed', n, 'files this run (16 in total over all runs: 8 audits + 8 implementation reports)')
