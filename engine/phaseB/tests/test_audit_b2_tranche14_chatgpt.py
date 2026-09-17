"""Tranche14: per-size interface/fixture contracts, small synthetic banks only.
No formal CMB bank, official E2 lattice, or full-grid calibration is run.
The requested full-family statistical aggregator is tracked as an unimplemented
integration requirement, not falsely tested as if a released API existed.
"""
from pathlib import Path
import sys,os,copy
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from step1_engine.twelve_eval import check_twelve_family_input,evaluate_twelve_size,evaluate_twelve_family
from step1_engine.stage12 import generate_twelve
from step1_engine.orchestrator import evaluate_family,evaluate_family_staged
from step1_engine.ci import ci_from_replicates
from step1_engine.errors import InputContractError
from step1_engine import serialization as ser
from test_b2_tranche14 import TwelveFixture,A7
A8=np.array([[.21609142351830096,.1388778490467109],[.10991624390681737,.06676051199330066],[.4225612190131215,.125548183938205]])

@pytest.fixture(scope='module')
def data():
 fx=TwelveFixture(sizes=('L1.00',));fm,fn=fx.inputs['L1.00'];return fm,fn,fx.manifests['L1.00'],fx.maps['L1.00'],fx.nmaps['L1.00']

def test_normal_per_size_matches_existing_q_evaluator(data):
 fm,fn,m,p,pn=data;d=evaluate_twelve_size(fm,fn,m,'L1.00',p,80.,400.,False,native_position_ids=pn);ref=evaluate_family(fm,fn,80.,400.)
 assert d['Q_point']==ref.Q_point and d['Q_ci_seed0']==ref.Q_ci_seed0
 assert d['truths']==ref.truths and len(d['per_config'])==12

def test_staged_per_size_matches_staged_base(data):
 fm,fn,m,p,pn=data;d=evaluate_twelve_size(fm,fn,m,'L1.00',p,80.,400.,True,native_position_ids=pn);ref=evaluate_family_staged(fm,fn,80.,400.)
 assert d['Q_point']==ref.Q_point and d['truths']==ref.truths
 assert d['evidence']['expansion']['matched']['stages']==ref.evidence['expansion']['matched']['stages']

def test_normal_strict_json_preserves_five_seed_evidence(data):
 fm,fn,m,p,pn=data;d=ser.loads(ser.dumps(evaluate_twelve_size(fm,fn,m,'L1.00',p,80.,400.,False,native_position_ids=pn)))
 assert d['evidence']['stage']=='12-position' and d['evidence']['twelve_manifest_sha256']==m.sha256
 for s in range(5):
  ev=d['evidence']['matched']['per_seed'][s];ci=ci_from_replicates(ev['num'],ev['den'],mode='Q',seed_id=s)
  saved=d['evidence']['cis_all_seeds'][s]
  assert ci.log_lower==saved['log_lower'] and ci.log_upper==saved['log_upper']

def test_reject_eleven_positions(data):
 fm,fn,m,p,pn=data;a=copy.deepcopy(fm);a.configs=a.configs[:11]
 with pytest.raises(InputContractError):check_twelve_family_input(a,m,{k:v for k,v in p.items() if v<11})

def test_reject_wrong_position_weights(data):
 fm,fn,m,p,pn=data;a=copy.deepcopy(fm);a.configs[0].weight=.5
 with pytest.raises(InputContractError):check_twelve_family_input(a,m,p)

def test_reject_different_requested_size(data):
 fm,fn,m,p,pn=data
 with pytest.raises(InputContractError):evaluate_twelve_size(fm,fn,m,'L1.50',p,80.,400.,False,native_position_ids=pn)

def test_reject_inventory_mismatch(data):
 fm,fn,m,p,pn=data
 with pytest.raises(InputContractError):evaluate_twelve_family({'L1.00':(fm,fn)},{'L1.00':m,'L1.20':m},{'L1.00':p},80.,400.,False,native_position_ids={'L1.00':pn})

def test_reject_empty_family():
 with pytest.raises(InputContractError):evaluate_twelve_family({}, {}, {},80.,400.,False)

def test_reject_mixed_families_at_one_family_entry(data):
 fm,fn,m,p,pn=data;gm,gn=copy.deepcopy(fm),copy.deepcopy(fn)
 for f in (gm,gn):
  f.family='E8'
  for c in f.configs:c.family='E8'
 m8=generate_twelve('E8','L1.20',A8)
 with pytest.raises(InputContractError):
  evaluate_twelve_family({'L1.00':(fm,fn),'L1.20':(gm,gn)},{'L1.00':m,'L1.20':m8},{'L1.00':p,'L1.20':p},80.,400.,False,native_position_ids={'L1.00':pn,'L1.20':pn})

@pytest.mark.parametrize('kind',['float','bool'])
def test_position_indices_are_actual_integers(data,kind):
 fm,fn,m,p,pn=data
 bad={k:(float(v) if kind=='float' else bool(v) if v<2 else v) for k,v in p.items()}
 with pytest.raises(InputContractError):check_twelve_family_input(fm,m,bad)

def test_reported_pair_fixture_shared_uids_mean_same_latent(data):
 fm,fn,m,p,pn=data
 assert fm.configs[0].cluster_uids==fn.configs[0].cluster_uids
 zm=np.c_[fm.configs[0].T1_ref-120,fm.configs[0].T2_ref-600]/[40,200]
 zn=np.c_[fn.configs[0].T1_ref-120,fn.configs[0].T2_ref-600]/[34,170]
 assert np.allclose(zm,zn,rtol=0,atol=1e-13), 'same CRN UIDs label different latent draws in the new integration fixture'

def test_reported_pair_fixture_fitting_bootstrap_is_paired(data):
 fm,fn,m,p,pn=data
 assert all(fm.fit_plans[s] is fn.fit_plans[s] for s in range(5)), 'same family fitting bootstrap must use common resampling across systems'

def test_reported_fixture_shares_latent_across_sizes():
 fx=TwelveFixture(sizes=('L1.00','L1.20'));f1,_=fx.inputs['L1.00'];f2,_=fx.inputs['L1.20']
 assert f1.configs[0].cluster_uids==f2.configs[0].cluster_uids
 assert np.array_equal(f1.configs[0].T1_ref,f2.configs[0].T1_ref), 'fixture uses identical reference transform and UIDs but independent draws across sizes'
