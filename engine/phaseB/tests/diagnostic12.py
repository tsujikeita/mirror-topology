from fixture32 import *
from step1_engine.integrated_runner import assemble_parent,run_first_wave
from step1_engine.threshold_evaluator import evaluate_family_full
from step1_engine.twelve_eval import evaluate_twelve_family_mixture
from step1_engine.stage12 import generate_twelve
from step1_engine.archive import Archive
from step1_engine import serialization as ser
import json
b=base();reg,man=b['reg'],b['man'];out={}
for name,required in [('optional_case_ci',False),('required_family_ci',True)]:
    cases=diagnostic_cases(reg,man,all_sizes_need_ci=required);views={k.split('/')[1]:v for k,v in cases.items()};p=assemble_parent(reg,man,'E7',{s:v[:2] for s,v in views.items()})
    ti=twelve_from_cases(cases);mans={s:generate_twelve('E7',s,np.array(reg.anchors['E7'])) for s in reg.surviving['E7']}
    g=evaluate_twelve_family_mixture(ti['size_inputs'],mans,ti['position_ids'],reg.size_prior['E7'],80.,400.,native_position_ids=ti['native_position_ids'])
    # Use baseline first-wave banks when testing a required twelve-stage failure so expansion is reached.
    v3={k.split('/')[1]:v for k,v in b['cases'].items()};p3=assemble_parent(reg,man,'E7',{s:v[:2] for s,v in v3.items()})
    r=evaluate_family_full(reg,man,'E7',p3,v3,b['ctx'],b['ctx'].context_sha256,80.,400.,ti,with_diagnostics=False)
    d=dict(direct=dict(Q=g['Q_point'],ci=g['Q_ci_seed0'],truths=g['truths'],precision=g['precision'],decision=g['decision'],logD=g['logD'],per={s:dict(Q=v['Q_point'],truths=v['truths'],decision=v['decision'],precision=v['precision'],logD=v['logD']) for s,v in g['per_size_diagnostic'].items()}),common=dict(summary=r.summary(),twelve=r.twelve))
    out[name]=d
    print(name,ser.dumps(dict(direct_Q=g['Q_point'],direct_truths=g['truths'],direct_tech=g['decision']['technical_status'],direct_ci=g['logD']['ci'],summary=r.summary(),twelve=r.twelve)),flush=True)
    if not required:
        with open(R/'diagnostic12.pkl','wb') as h:pickle.dump(ti,h)
(R/'evidence/references/diagnostic12.json').write_text(ser.dumps(out))
