"""Tranche15 input/assembly/adapter contracts. Synthetic fixtures, no CMB/OT.
Set PHASEB_ROOT to the extracted submitted phaseB directory.
Negative cases change one field or create a different valid plan with the SAME name;
these are not estimates of the normal-run failure rate.
"""
from pathlib import Path
import os,sys,copy
from dataclasses import replace
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_b2_tranche14 import TwelveFixture
from step1_engine.twelve_eval import assemble_all_sizes,evaluate_twelve_family_mixture,TwelveSizeResult,check_twelve_family_input
from step1_engine.bootstrap_plan import BootstrapPlan,FittingPlan
from step1_engine.checkpoint import write_family_result,read_family_result
from step1_engine.orchestrator import evaluate_family
from step1_engine.errors import InputContractError

@pytest.fixture(scope='module')
def fx():return TwelveFixture()

def assemble(fx,inputs=None,manifests=None,maps=None,nmaps=None):
 return assemble_all_sizes(fx.inputs if inputs is None else inputs,fx.manifests if manifests is None else manifests,fx.maps if maps is None else maps,{s:1/len(fx.sizes) for s in fx.sizes},fx.nmaps if nmaps is None else nmaps,expected_sizes=fx.sizes)

@pytest.fixture(scope='module')
def result(fx):
 return evaluate_twelve_family_mixture(fx.inputs,fx.manifests,fx.maps,{s:.5 for s in fx.sizes},100.,550.,False,fx.nmaps,fx.sizes)

def test_normal_assembly_preserves_inputs_and_binding(fx):
 old=[[c.weight for c in f.configs] for pair in fx.inputs.values() for f in pair]
 gm,gn,ident=assemble(fx)
 assert len(gm.configs)==24 and len(gn.configs)==24
 assert all(c.weight==1/24 for c in gm.configs+gn.configs)
 assert old==[[c.weight for c in f.configs] for pair in fx.inputs.values() for f in pair]
 gm.validate();gn.validate();assert gm.fitting_plan_binding==gn.fitting_plan_binding=='bound'

def test_identical_independent_plan_copies_are_accepted(fx):
 inputs={s:copy.deepcopy(pair) for s,pair in fx.inputs.items()}
 gm,gn,_=assemble(fx,inputs=inputs);gm.validate();gn.validate()

def test_same_name_different_valid_resampling_rejected(fx):
 inputs=copy.deepcopy(fx.inputs);f,n=inputs['L1.20']
 alt={k:BootstrapPlan.build(f.plans[k].plan_id,k,f.plans[k].strata,60,99999) for k in range(5)}
 assert alt[0].validate() and alt[0].plan_id==f.plans[0].plan_id
 assert not np.array_equal(alt[0].multiplicities[0],f.plans[0].multiplicities[0])
 inputs['L1.20']=(replace(f,plans=alt),n)
 with pytest.raises(InputContractError):assemble(fx,inputs=inputs)

def test_corrupt_nonfirst_plan_not_discarded(fx):
 inputs=copy.deepcopy(fx.inputs);f,n=inputs['L1.20'];alt=copy.deepcopy(f.plans)
 alt[0].multiplicities[0]=np.zeros_like(alt[0].multiplicities[0])
 with pytest.raises(InputContractError):alt[0].validate()
 inputs['L1.20']=(replace(f,plans=alt),n)
 with pytest.raises(InputContractError):assemble(fx,inputs=inputs)

def test_nonfirst_plan_seed_mismatch_not_relabelled(fx):
 inputs=copy.deepcopy(fx.inputs);f,n=inputs['L1.20'];alt=copy.deepcopy(f.plans)
 alt[0].seed_id=1
 inputs['L1.20']=(replace(f,plans=alt),n)
 with pytest.raises(InputContractError):assemble(fx,inputs=inputs)

def test_cross_system_evaluation_plan_must_be_shared(fx):
 inputs=copy.deepcopy(fx.inputs)
 alt={k:BootstrapPlan.build(fx.plans[k].plan_id,k,fx.plans[k].strata,60,11111) for k in range(5)}
 for s,(fm,fn) in list(inputs.items()):inputs[s]=(fm,replace(fn,plans=alt))
 with pytest.raises(InputContractError):assemble(fx,inputs=inputs)

def test_cross_system_fitting_plan_must_be_shared(fx):
 inputs=copy.deepcopy(fx.inputs)
 alt={k:FittingPlan.build(f'fit-s{k}',1,21,k,400,20,11111) for k in range(5)}
 for s,(fm,fn) in list(inputs.items()):inputs[s]=(fm,replace(fn,fit_plans=alt))
 with pytest.raises(InputContractError):assemble(fx,inputs=inputs)

def test_coverage_text_not_silently_promoted_to_true(fx):
 inputs=copy.deepcopy(fx.inputs)
 for pair in inputs.values():
  for f in pair:f.coverage_ok='False'
 with pytest.raises(InputContractError):assemble(fx,inputs=inputs)

def test_actual_false_coverage_is_preserved(fx):
 inputs=copy.deepcopy(fx.inputs)
 for pair in inputs.values():
  for f in pair:f.coverage_ok=False
 gm,gn,_=assemble(fx,inputs=inputs);r=evaluate_family(gm,gn,100.,550.)
 assert not gm.coverage_ok and not gn.coverage_ok
 assert all(x=='unknown' for x in r.truths.values())

def test_assembly_checks_manifest_size_before_return(fx):
 man=dict(fx.manifests);man['L1.20']=man['L1.00']
 with pytest.raises(InputContractError):assemble(fx,manifests=man)

def test_expected_inventory_rejects_missing_registered_size(fx):
 with pytest.raises(InputContractError):
  assemble_all_sizes(fx.inputs,fx.manifests,fx.maps,{'L1.00':.5,'L1.20':.5},fx.nmaps,expected_sizes=['L1.00','L1.20','L1.50'])

def test_size_prior_not_renormalised(fx):
 with pytest.raises(InputContractError):assemble_all_sizes(fx.inputs,fx.manifests,fx.maps,{'L1.00':.6,'L1.20':.6},fx.nmaps)

def test_normal_result_Q_equals_probability_mixture(result):
 per=result['per_size_diagnostic'];pm=sum(.5*np.mean([c['P_model'] for c in r['per_config'].values()]) for r in per.values());pi=sum(.5*np.mean([c['P_ref'] for c in r['per_config'].values()]) for r in per.values())
 assert result['Q_point']==pytest.approx(pm/pi,abs=1e-12)
 assert len(result['per_config'])==24 and result['evidence']['stage']=='12-position-family'

def test_normal_adapter_roundtrip(fx,result,tmp_path):
 s='L1.00';r=result['per_size_diagnostic'][s]
 a=TwelveSizeResult('E7',s,fx.manifests[s].sha256,fx.maps[s],fx.nmaps[s],r,r['evidence']['scope'])
 p=str(tmp_path/'ok.json');sh=write_family_result(a,p);rest=read_family_result(p,sh)
 assert rest['result']['size_id']==s and set(rest['result']['evidence']['position_ids'])==set(rest['result']['per_config'])

def test_adapter_refuses_retagging_already_tagged_size(fx,result,tmp_path):
 a=TwelveSizeResult('E7','L1.20',fx.manifests['L1.20'].sha256,fx.maps['L1.20'],fx.nmaps['L1.20'],result['per_size_diagnostic']['L1.00'],'per-size diagnostic')
 with pytest.raises(InputContractError):write_family_result(a,str(tmp_path/'bad.json'))

def test_adapter_family_must_match_embedded_result(fx,result,tmp_path):
 s='L1.00';a=TwelveSizeResult('E8',s,fx.manifests[s].sha256,fx.maps[s],fx.nmaps[s],result['per_size_diagnostic'][s],'per-size diagnostic')
 with pytest.raises(InputContractError):write_family_result(a,str(tmp_path/'badfamily.json'))

def test_reader_checks_position_ids_against_config_inventory(fx,result,tmp_path):
 r=copy.deepcopy(result['per_size_diagnostic']['L1.00']);r['evidence']['position_ids']=dict(fx.maps['L1.20'])
 p=str(tmp_path/'wrongids.json')
 with pytest.raises(InputContractError):
  sh=write_family_result(r,p);read_family_result(p,sh)

def test_reader_checks_identity_family(result,tmp_path):
 r=copy.deepcopy(result);r['evidence']['identity']['family']='E8'
 p=str(tmp_path/'wrongfamily.json')
 with pytest.raises(InputContractError):sh=write_family_result(r,p);read_family_result(p,sh)

def test_reader_checks_identity_size_prior_against_saved_prior(result,tmp_path):
 r=copy.deepcopy(result);r['evidence']['identity']['size_weights']={'L1.00':.9,'L1.20':.1}
 p=str(tmp_path/'wrongprior.json')
 with pytest.raises(InputContractError):sh=write_family_result(r,p);read_family_result(p,sh)
