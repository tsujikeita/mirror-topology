# -*- coding: utf-8 -*-
"""B-2 tranche 22: adopted tranche-21 gate fixes; formal runner (gate on the same inputs, fingerprint contract, gate record in evidence/checkpoint, live-only official)."""
import os, sys, copy, json
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.dirname(__file__))
from step1_engine.formal_runner import run_family_formal, input_fingerprint
from step1_engine.checkpoint import read_family_result
from step1_engine.errors import InputContractError
from step1_engine import serialization as ser
from test_b2_tranche21 import build_pair

def test_formal_runner_smoke_records_gate_and_fingerprint(tmp_path):
    reg, man, fm, fn, sm, plans, fplans = build_pair(); p = str(tmp_path / 'formal.json')
    r = run_family_formal(fm, fn, 80.0, 400.0, 'smoke', checkpoint_path=p); g = r.evidence['gate']
    assert g['mode'] == 'smoke' and g['record']['passed'] is True and g['input_fingerprint']['matched'] == input_fingerprint(fm) and g['input_fingerprint']['native'] == input_fingerprint(fn)
    got = read_family_result(p, g['checkpoint_sha256']); assert 'gate: smoke' in got['verified'] and got['result']['evidence']['gate']['record']['mode'] == 'smoke'
    with pytest.raises(InputContractError): run_family_formal(fm, fn, 80.0, 400.0, 'official')                                       # sandbox: registered profile/environment not met -> refused (live measurement)
    with pytest.raises(InputContractError): run_family_formal(fm, None, 80.0, 400.0, 'formal')
    raw = ser.loads(open(p).read()); raw['result']['evidence']['gate']['record']['passed'] = False; open(str(tmp_path / 'bad.json'), 'w').write(ser.dumps(raw))
    with pytest.raises(InputContractError): read_family_result(str(tmp_path / 'bad.json'))                                             # a failed gate cannot be stored as a verified formal result
    raw = ser.loads(open(p).read()); raw['result']['evidence']['gate']['mode'] = 'official'; open(str(tmp_path / 'bad2.json'), 'w').write(ser.dumps(raw))
    with pytest.raises(InputContractError): read_family_result(str(tmp_path / 'bad2.json'))                                            # mode relabelled after the fact

def test_fingerprint_detects_mutation_between_gate_and_evaluation(monkeypatch):
    reg, man, fm, fn, sm, plans, fplans = build_pair()
    import step1_engine.formal_runner as fr; orig = fr.evaluate_family_staged
    def mutate_then_eval(a, b, *args, **kw):
        a.configs[0].T1_model[0] += 1.0; return orig(a, b, *args, **kw)                                                                # simulated in-run mutation
    monkeypatch.setattr(fr, 'evaluate_family_staged', mutate_then_eval)
    with pytest.raises(InputContractError): run_family_formal(fm, fn, 80.0, 400.0, 'smoke')
