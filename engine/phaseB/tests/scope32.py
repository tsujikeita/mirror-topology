from fixture32 import *
from step1_engine.integrated_runner import run_first_wave
from step1_engine.archive import Archive
from step1_engine import serialization as ser
f=multifamily_trigger_only_pseudo(base())
with open(R/'multifamily.pkl','wb') as h:pickle.dump(f,h)
r=run_first_wave(f['reg'],f['man'],f['cases'],f['ctx'],f['ctx'].context_sha256,(200.,1000.),[80.],[400.],Archive(str(R/'work/scope32')),require_all_families=True)
out=dict(target={k:dict(status=v['status'],expand=v['expand_family'],eligible=v['eligibility']) for k,v in r.families.items()},pseudo=r.per_pseudo_family_status,calibration=r.calibration,run_scope=r.scope)
print(ser.dumps(out));(R/'evidence/references/scope32.json').write_text(ser.dumps(out))
