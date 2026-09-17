"""Small synthetic, explicitly injected-distance manifest contract probes. No CMB or exact POT run."""
import os,sys,copy,json,math
from pathlib import Path
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import numpy as np
from step1_engine.positions import PositionBank,w2_trigger,position_decision
from step1_engine.w2_manifest import build_w2_manifest,verify_w2_manifest,W2Manifest
from step1_engine.w2_stop import w2_validate,StopResult,seed_spread
from step1_engine import serialization as ser

def cheap_dist(a,b):return float(np.max(np.abs(a.mean(0)-b.mean(0))))
def fixture():
 rng=np.random.default_rng(20260914);m=100
 ps=[PositionBank(i+1,rng.standard_normal((60*m,2))+shift,np.repeat(np.arange(60),m),m) for i,shift in enumerate([0.,0.,.8])]
 iso=PositionBank(0,rng.standard_normal((180*m,2)),np.repeat(np.arange(180),m),m)
 r=w2_trigger(ps,iso,m,20260914,dist=cheap_dist,obs_bounds={n:{s:0. for s in [0,1,2]} for n in [2000,5000]},delta_q99_bound={n:0. for n in [2000,5000]},whitening_identity={'mu':[0.,0.],'W':[[1.,0.],[0.,1.]],'source':'synthetic_fixture'})
 return ps,iso,r

def main():
 ps,iso,r=fixture();m=build_w2_manifest('E7','L1.00',ps,iso,r);out=[]
 def record(name,fn):
  try:v=fn();out.append({'name':name,'outcome':'accepted','value':ser.to_jsonable(v)})
  except Exception as e:out.append({'name':name,'outcome':'rejected','exception':type(e).__name__,'message':str(e)})
 record('baseline',lambda:{'verify':verify_w2_manifest(m,ps,iso,r),'B_final':r['stop']['B_final'],'validation':r['validation'],'q99':r['null_q99'],'observed':r['observed']})
 record('strict_roundtrip',lambda:verify_w2_manifest(W2Manifest(**ser.loads(ser.dumps(m.as_dict()))),ps,iso,ser.loads(ser.dumps(r))))
 record('registered_guard_injected_m100',lambda:verify_w2_manifest(m,ps,iso,r,True))
 r1=copy.deepcopy(r);r1['trigger']=False
 P={1:dict(P=.2,hits=20,N=100,precision='pass',stage='N0'),2:dict(P=.25,hits=25,N=100,precision='pass',stage='N0'),3:dict(P=.2,hits=20,N=100,precision='pass',stage='N0')}
 record('top_trigger_drift',lambda:{'verify':verify_w2_manifest(m,ps,iso,r1),'position_original':position_decision(r,P),'position_changed':position_decision(r1,P),'stored_validation':r1['validation']})
 r2=copy.deepcopy(r);r2['observed'][2000][0]+=10
 record('top_observed_drift',lambda:verify_w2_manifest(m,ps,iso,r2))
 r3=copy.deepcopy(r);r3['evidence']['observed'][2000][0]['W2_max']+=10
 record('observed_evidence_drift',lambda:verify_w2_manifest(m,ps,iso,r3))
 r4=copy.deepcopy(r);r4['evidence']['whitening']={'source':'other_whitener'}
 record('whitening_drift',lambda:verify_w2_manifest(m,ps,iso,r4))
 r5=copy.deepcopy(r);r5['evidence']['master_seed']+=1
 record('master_seed_drift',lambda:verify_w2_manifest(m,ps,iso,r5))
 r6=copy.deepcopy(r);r6['stop']={'corrupt':'missing'}
 record('result_stop_replaced',lambda:verify_w2_manifest(m,ps,iso,r6))
 mm=copy.deepcopy(m);mm.distance_kind='exact_pot_w2'
 record('distance_label_spoof_same_m100',lambda:verify_w2_manifest(mm,ps,iso,r,True))
 changed=[PositionBank(p.position_id,p.Tw+3*(i+1),p.cid,p.m) for i,p in enumerate(ps)]
 record('existing_manifest_live_drift',lambda:verify_w2_manifest(m,changed,iso,r))
 record('old_result_bind_to_new_banks',lambda:verify_w2_manifest(build_w2_manifest('E7','L1.00',changed,iso,r),changed,iso,r))
 rr=copy.deepcopy(r);mm=build_w2_manifest('E7','L1.00',ps,iso,rr)
 alias=mm.validation is rr['validation'];rr['validation']['trigger']=False
 record('validation_alias',lambda:{'same_object':alias,'verify':verify_w2_manifest(mm,ps,iso,rr),'actual_stop_indicator':mm.stop['trace'][-1]['indicator'],'validation_now':mm.validation})
 rr=copy.deepcopy(r);mm=build_w2_manifest('E7','L1.00',ps,iso,rr)
 alias=mm.bounds is rr['evidence']['bounds'];rr['evidence']['bounds']['obs_bounds'][2000][0]=1000.
 sd=ser.from_jsonable(mm.stop);st=StopResult(**sd)
 record('bounds_alias_and_no_revalidation',lambda:{'same_object':alias,'verify':verify_w2_manifest(mm,ps,iso,rr),'recomputed':w2_validate(st,rr['spread'],mm.bounds['obs_bounds'],mm.bounds['delta_q99_bound'],rr['observed'])})
 mm=copy.deepcopy(m);mm.null_sha256.pop(5000)
 record('missing_null_manifest_entry',lambda:verify_w2_manifest(mm,ps,iso,r))
 mm=copy.deepcopy(m);mm.null_sha256.clear()
 record('empty_null_manifest_inventory',lambda:verify_w2_manifest(mm,ps,iso,r))
 mm=copy.deepcopy(m);sd=mm.stop;sd['trace'][0]['q99']={n:v*.99 for n,v in sd['trace'][0]['q99'].items()}
 for i in range(1,len(sd['trace'])):
  a,b=sd['trace'][i-1],sd['trace'][i]
  b['relative_change']=max(abs(b['q99'][n]-a['q99'][n])/a['q99'][n] for n in a['q99'])
 record('wrong_earlier_trace_quantile',lambda:verify_w2_manifest(mm,ps,iso,r))
 rr=copy.deepcopy(r)
 for n in rr['evidence']['null']:
  rr['evidence']['null'][n]['blocks'][0][1]=rr['evidence']['null'][n]['blocks'][0][0]
 record('overlap_null_blocks',lambda:verify_w2_manifest(m,ps,iso,rr))
 rr=copy.deepcopy(r);rr['evidence']['observed'][2000][0]['pairwise']['P1P2']=-1.
 record('negative_observed_pair',lambda:verify_w2_manifest(m,ps,iso,rr))
 rr=copy.deepcopy(r);rr['evidence']['bounds']={'obs_bounds':None,'delta_q99_bound':None}
 record('lost_result_bounds',lambda:verify_w2_manifest(m,ps,iso,rr))
 rr=copy.deepcopy(r);rr['evidence']['null'][2000]['values'][9]+=1e-4
 record('null_bytes_drift',lambda:verify_w2_manifest(m,ps,iso,rr))
 rr=copy.deepcopy(r);rr['null_q99'][2000]+=.01
 record('top_q99_drift',lambda:verify_w2_manifest(m,ps,iso,rr))
 rr=copy.deepcopy(r);rr['evidence']['bounds']={'obs_bounds':{},'delta_q99_bound':{}}
 record('build_empty_bound_maps',lambda:verify_w2_manifest(build_w2_manifest('E7','L1.00',ps,iso,rr),ps,iso,rr))
 dest=Path(os.environ.get('AUDIT_OUTPUT',str(Path(__file__).parent/'manifest_probes.json')))
 dest.write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False))
 # Save a real (synthetic) normal bank/result packet so reference checks use the SAME data, not hand-made stop summaries.
 np.savez_compressed(dest.with_name('manifest_fixture_banks.npz'),**{f'p{i}':p.Tw for i,p in enumerate(ps)},iso=iso.Tw)
 dest.with_name('manifest_fixture_result.json').write_text(ser.dumps(r))
 print('\n'.join(f"{d['name']}: {d['outcome']} {d.get('message','')}" for d in out))
 print('Baseline',out[0])
if __name__=='__main__': main()
