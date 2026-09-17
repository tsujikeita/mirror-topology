import os,sys,pickle,time,json
from pathlib import Path
R=Path(os.environ.get('AUDIT_WORKDIR','/mnt/data/audit32')); P=Path(os.environ.get('PHASEB_ROOT',R/'submitted/phaseB'));sys.path[:0]=[str(P),str(P/'tests')]
from runner_fixture import build_fixture
from audit_fixture30 import negative_context
st=time.time();f=build_fixture();f['ctx'].results={};f['ctx'].validate()
with open(R/'base.pkl','wb') as h:pickle.dump(f,h)
n=negative_context(f)
with open(R/'negative.pkl','wb') as h:pickle.dump(n,h)
print(json.dumps(dict(seconds=time.time()-st,positive={k:d.trigger for k,d in f['ctx'].decisions.items()},negative={k:d.trigger for k,d in n.decisions.items()})))
