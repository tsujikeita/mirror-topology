from fixture32 import *
import step1_engine.integrated_runner as ir
from step1_engine.archive import Archive
from step1_engine.formal_runner import input_fingerprint
from step1_engine import serialization as ser
f=base()
with open(R/'twelve.pkl','rb') as h:ti=pickle.load(h)
original=ir.evaluate_family_full;count=0;seen=[];snap0={s:[input_fingerprint(x) for x in pair] for s,pair in ti['size_inputs'].items()}
def changed(reg,man,fam,parent,views,w2,sha,x,y,*args,**kw):
    global count
    count+=1
    if count==2:
        ti['size_inputs']['L1.00'][0].configs[0].T1_model-=5.
    r=original(reg,man,fam,parent,views,w2,sha,x,y,*args,**kw);seen.append(r.twelve["family_mixture"]["Q_point"]);return r
ir.evaluate_family_full=changed
try:
    arc=Archive(str(R/'work/mutation12_v2'));r=ir.run_first_wave(f['reg'],f['man'],f['cases'],f['ctx'],f['ctx'].context_sha256,(100.,550.),[100.],[550.],arc,twelve_inputs={'E7':ti})
    snap1={s:[input_fingerprint(x) for x in pair] for s,pair in ti['size_inputs'].items()}
    # common summaries omit Q for pseudo; record it by separate evaluation at same changed input.
    p=ir.assemble_parent(f['reg'],f['man'],'E7',{k.split('/')[1]:v[:2] for k,v in f['cases'].items()});v={k.split('/')[1]:z for k,z in f['cases'].items()}
    after=original(f['reg'],f['man'],'E7',p,v,f['ctx'],f['ctx'].context_sha256,100.,550.,ti,with_diagnostics=False)
    out=dict(accepted=True,twelve_fingerprint_changed=snap0!=snap1,recorded_firstwave_fingerprints_equal=r.fingerprints['at_gate']==r.fingerprints['at_end'],target_Q=r.families['E7']['twelve']['family_mixture']['Q_point'],after_Q=after.twelve['family_mixture']['Q_point'],calls=count,actual_target_and_pseudo_Q=seen,archive=arc.verify_all(),recorded_fingerprint_keys=list(r.fingerprints['at_gate']))
except Exception as e:out=dict(accepted=False,error=repr(e))
print(ser.dumps(out));(R/'evidence/references/invariance32.json').write_text(ser.dumps(out))
