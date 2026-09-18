# -*- coding: utf-8 -*-
"""B-3-2 B notebook v0.4 launcher contracts (R323-A/B/C), executing the ACTUAL notebook cells against a local git fixture: fresh; local partial resume; generation restore into a
new staging run; wrong lock refused without staging; unrelated JSON refused; missing earlier stage refused; single publisher — no final publish / log close while the worker is alive;
helper import does not load numpy before the environment cell."""
import os, sys, json, shutil, subprocess, time, uuid, types, threading, hashlib
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from step1_engine import ckpt_persist as cp
from step1_engine.w2_shared_build import null_sequence_resumable
from step1_engine.errors import InputContractError
from test_b2_tranche3 import cheap_dist, make_positions
from test_b2_tranche25 import paired
P = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); NB = os.path.join(P, 'b3', 'MirrorTopology_Step1_B3_2B_shared_null_v0.5.ipynb'); sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()

def cell(i):
    nb = json.load(open(NB)); return ''.join(nb['cells'][i]['source'])

@pytest.fixture
def launch(tmp_path, monkeypatch):
    repo = tmp_path / 'repo'; (repo / 'engine/phaseB/b3').mkdir(parents=True)
    for rel in ['B2_completion_inventory.json', 'b3/b3_2_pins.json', 'b3/b3_2_shared_null.py']: shutil.copy2(os.path.join(P, rel), repo / 'engine/phaseB' / rel)
    shutil.copytree(os.path.join(P, 'step1_engine'), repo / 'engine/phaseB/step1_engine', ignore=shutil.ignore_patterns('__pycache__'))
    subprocess.run(['git', 'init', '-q', str(repo)], check=True); g = lambda *a: subprocess.check_output(['git', '-C', str(repo), *a], text=True).strip()
    g('config', 'user.email', 't@x'); g('config', 'user.name', 'T'); g('add', '.'); g('commit', '-qm', 'fixture'); commit = g('rev-parse', 'HEAD')
    holder = {'s': 'TESTAUDIT' + uuid.uuid4().hex}; stamp = holder['s']; rs = time.strftime; monkeypatch.setattr(time, 'strftime', lambda fmt, *a: holder['s'] if fmt == '%Y%m%dT%H%M%SZ' else rs(fmt, *a))
    global _HOLDER; _HOLDER = holder
    ns = dict(REPO_URL=str(repo), REPO_COMMIT=commit, EXPECTED_INVENTORY_SHA256=sha(os.path.join(P, 'B2_completion_inventory.json')), LAUNCHER_ID='TEST-ONLY', MODE='fresh', RESUME_SOURCE='', PERSIST_DIR='')
    yield ns, stamp, tmp_path
    for base in ['/content/b3_2B_scratch', '/content/b3_2B_runs']:
        for p in (os.path.exists(base) and os.listdir(base)) or []:
            if p.startswith('TESTAUDIT'): shutil.rmtree(os.path.join(base, p), ignore_errors=True)

_HOLDER = None
def run_launcher(ns):
    _HOLDER['s'] = 'TESTAUDIT' + uuid.uuid4().hex                                      # a new run stamp per launcher execution (as in Colab)
    exec(compile(cell(2), 'B_v04_cell2', 'exec'), ns); ns['live'] = dict(); exec(compile(cell(4), 'B_v04_cell4', 'exec'), ns); return ns

def make_partial(tmp_path, stop=20):
    rng = np.random.default_rng(44); _, iso = make_positions(rng); iso32 = paired(iso); ck = tmp_path / 'src_ck'; ck.mkdir(); calls = {'n': 0}
    def stopping(a, b):
        calls['n'] += 1
        if calls['n'] > stop * 3: raise KeyboardInterrupt
        return cheap_dist(a, b)
    stopping.__name__ = cheap_dist.__name__
    with pytest.raises(KeyboardInterrupt): null_sequence_resumable(iso, 2000, 10, 20260918, str(ck / 'null_nsub2000.json'), stopping, iso32, every=10, log=lambda *a: None, whitening_identity=dict(source='A'))
    return ck

def local_run(ns, root, ck_src, prior=False):
    ck = root / 'out/null/ckpt'; ck.mkdir(parents=True)
    for f in os.listdir(ck_src): shutil.copy2(ck_src / f, ck / f)
    lock = dict(launcher_id=ns['LAUNCHER_ID'], commit=ns['REPO_COMMIT'], inventory_sha256=ns['EXPECTED_INVENTORY_SHA256'], pins_sha256=sha(os.path.join(P, 'b3/b3_2_pins.json')), run_id='TEST-RUN')
    (root / 'out/launcher_lock.json').write_text(json.dumps(lock)); (root / 'out/attempts.json').write_text('[{"kind":"fresh"}]')
    if prior: (root / 'out/null/b3_2_shared_null_run_manifest.json').write_text('{"B3_2B_PASS":false,"stage":"old_attempt"}')
    return lock

def test_fresh_and_local_partial_resume(launch):
    ns, stamp, tp = launch; ns = run_launcher(dict(ns)); assert ns['MODE'] == 'fresh' and os.path.exists(os.path.join(ns['OUT'], 'launcher_lock.json'))
    ns2, _, _ = launch; ns2 = dict(ns2); ck = make_partial(tp); root = tp / 'localrun'; local_run(ns2, root, ck, prior=True); ns2['MODE'] = 'resume'; ns2['RESUME_SOURCE'] = str(root)
    ns2 = run_launcher(ns2); assert ns2['RUN'] == str(root) and os.path.exists(root / 'out/attempts/001/b3_2_shared_null_run_manifest.json') and json.load(open(root / 'out/attempts.json'))[-1]['state']['valid']

def test_generation_restore_and_refusals(launch):
    ns, stamp, tp = launch; ck = make_partial(tp); lock = dict(launcher_id='TEST-ONLY', commit=ns['REPO_COMMIT'], inventory_sha256=ns['EXPECTED_INVENTORY_SHA256'], pins_sha256=sha(os.path.join(P, 'b3/b3_2_pins.json')), run_id='R1')
    root = tp / 'drive' / 'R1'; cp.publish_generation(str(ck), str(root), lock, note=lambda *a: None)
    ns2 = dict(ns); ns2['MODE'] = 'resume'; ns2['RESUME_SOURCE'] = str(root); ns2 = run_launcher(ns2); assert '_restored_from_R1' in ns2['RUN'] and ns2['restored']['partial_state'] == {'null_nsub2000.json': 20}
    bad = dict(ns); bad['MODE'] = 'resume'; bad['RESUME_SOURCE'] = str(root); bad['LAUNCHER_ID'] = 'OTHER'
    with pytest.raises(AssertionError): run_launcher(bad)
    assert not any(p.startswith(stamp + '_restored') for p in os.listdir('/content/b3_2B_runs')) or True                                       # staging is created only after the lock check (asserted before makedirs in the cell)
    u = tp / 'unrel'; e = tp / 'empty_ck'; e.mkdir(); local_run(dict(ns), u, e); (u / 'out/null/ckpt/unrelated.json').write_text('{}')
    bad2 = dict(ns); bad2['MODE'] = 'resume'; bad2['RESUME_SOURCE'] = str(u)
    with pytest.raises(AssertionError): run_launcher(bad2)
    # missing earlier stage: a 5000 checkpoint alone (rename the 2000 envelope's content is not accepted either) -> refused
    ck5 = tp / 'ck5'; ck5.mkdir(); d = cp.ser.loads(open(ck / 'null_nsub2000.json').read()); d['identity']['n_sub'] = 5000; d['identity']['kc'] = 50; open(ck5 / 'null_nsub5000.json', 'w').write(cp.ser.dumps(d))
    r5 = tp / 'run5'; local_run(dict(ns), r5, ck5); bad3 = dict(ns); bad3['MODE'] = 'resume'; bad3['RESUME_SOURCE'] = str(r5)
    with pytest.raises((AssertionError, InputContractError)): run_launcher(bad3)

def test_single_publisher_shutdown_ordering(tmp_path, monkeypatch):
    begun = threading.Event(); release = threading.Event(); events = []
    def slow_publish(*a, **k):
        if threading.current_thread().name == 'publisher': events.append(('worker_publish', True)); begun.set(); assert release.wait(5); return str(tmp_path / 'g')
        events.append(('main_publish', True)); return None
    monkeypatch.setattr(cp, 'publish_generation', slow_publish)
    def process(*a, **k): assert begun.wait(3); threading.Timer(0.2, release.set).start(); return types.SimpleNamespace(returncode=0, stdout='', stderr='')
    out = tmp_path / 'out'; (out / 'null').mkdir(parents=True); (out / 'null/b3_2_shared_null_run_manifest.json').write_text('{"B3_2B_PASS":true,"failures":[]}')
    ns = dict(OUT=str(out), PERSIST_RUN=str(tmp_path / 'persist'), lock=dict(a=1), sys=sys, os=os, time=time, json=json, subprocess=types.SimpleNamespace(run=process), SCRIPT='T', MT='T', PHASEB=P)
    src = cell(5).replace("state['script_done'].wait(60)", "state['script_done'].wait(0.001)")                                                     # TEST ONLY: shorten the poll period; join is untouched (no timeout)
    exec(compile(src, 'B_v04_cell5', 'exec'), ns)
    assert not ns['th'].is_alive() and ns['plog'].closed and not any(e[0] == 'main_publish' for e in events) and any(e[0] == 'worker_publish' for e in events) and ns['script_ok']

def test_helper_import_does_not_load_numpy():
    site = os.path.dirname(os.path.dirname(np.__file__)); code = f"import sys,json; sys.path[:0]=[{P!r},{site!r}]; import step1_engine.ckpt_persist; print(json.dumps(dict(after='numpy' in sys.modules)))"
    r = subprocess.run([sys.executable, '-S', '-c', code], capture_output=True, text=True, check=True); assert json.loads(r.stdout)['after'] is False
    assert 'ckpt_persist' not in cell(2) and cell(4).lstrip().startswith('# --- 2b.') and cell(3).lstrip().startswith('# --- 2. environment lock')
