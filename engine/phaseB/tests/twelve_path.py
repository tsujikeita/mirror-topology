import os,sys,pickle,copy,json,time,traceback
from pathlib import Path
R=Path(os.environ.get('AUDIT_WORKDIR','/mnt/data/audit32')); P=Path(os.environ.get('PHASEB_ROOT',R/'submitted/phaseB'));sys.path[:0]=[str(P),str(P/'tests')]
import numpy as np
from test_b2_tranche14 import TwelveFixture
from step1_engine.integrated_runner import assemble_parent,run_first_wave
from step1_engine.threshold_evaluator import evaluate_family_full
from step1_engine.twelve_eval import evaluate_twelve_family_mixture
from step1_engine.archive import Archive,ArchiveRef
from step1_engine import serialization as ser
with open(R/'base.pkl','rb') as h:b=pickle.load(h)
reg,man,ctx=b['reg'],b['man'],b['ctx'];sizes=reg.surviving['E7'];views={k.split('/')[1]:v for k,v in b['cases'].items()};parent=assemble_parent(reg,man,'E7',{s:v[:2] for s,v in views.items()})
fx=TwelveFixture(sizes=sizes,K=800,Kf=800,B=60)
ti=dict(size_inputs=fx.inputs,position_ids=fx.maps,native_position_ids=fx.nmaps)
with open(R/'twelve.pkl','wb') as h:pickle.dump(ti,h)
t=time.time()
f=evaluate_family_full(reg,man,'E7',parent,views,ctx,ctx.context_sha256,100.,550.,ti,with_diagnostics=False)
print('time',time.time()-t,'FULL',ser.dumps(f.summary()))
print('TWELVE',ser.dumps(f.twelve))
g=evaluate_twelve_family_mixture(fx.inputs,fx.manifests,fx.maps,reg.size_prior['E7'],100.,550.,native_position_ids=fx.nmaps,expected_sizes=sizes)
print('DIRECT',ser.dumps(dict(Q=g['Q_point'],truths=g['truths'],precision=g['precision'],tech=g['decision']['technical_status'],per={s:dict(Q=v['Q_point'],precision=v['precision']['state'],tech=v['decision']['technical_status']) for s,v in g['per_size_diagnostic'].items()})))
arc=Archive(str(R/'work/normal12'))
rm=run_first_wave(reg,man,b['cases'],ctx,ctx.context_sha256,(100.,550.),[100.],[550.],arc,twelve_inputs={'E7':ti})
print('RUN',ser.dumps(rm.families['E7']));print('CAL',ser.dumps(rm.calibration));print('archive',arc.verify_all());print('refs',list(rm.archive_refs))
(R/'evidence/references/normal12_result.json').write_text(ser.dumps(dict(summary=f.summary(),twelve=f.twelve,run=rm.as_dict(),archive=arc.verify_all(),direct=g)))
print('DONE')
