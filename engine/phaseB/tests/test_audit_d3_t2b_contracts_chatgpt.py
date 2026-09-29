# -*- coding: utf-8 -*-
# ChatGPT audit contracts for D-3 tranche 2b 0.89.0 (R-D3T2B-A/B/C/D), bundled with path adaptation and the API adaptations marked "API adaptation" (the revised formal entries take a verified TwelveContext; refusal contracts unchanged). Original: tests/test_d3_t2b_contracts.py of the audit evidence bundle.
"""Independent D3-2b contract audit. Uses received real registration metadata and
explicit small synthetic bank arrays; no CT generation, calibration or labels.
Tests expecting rejection intentionally FAIL on an incomplete implementation.
External-loader tests use a labelled test double only, not a frozen-loader PASS.
"""
import copy, hashlib, importlib.util, io, json, os, sys
from pathlib import Path
from dataclasses import replace
import numpy as np
import pytest
P=Path(os.environ.get('AUDIT_PHASEB_ROOT',str(Path(__file__).resolve().parent.parent))).resolve()   # path adaptation (Claude): default = this phaseB tree; AUDIT_PHASEB_ROOT still honoured
sys.path.insert(0,str(P))
spec=importlib.util.spec_from_file_location('author_t2b_helpers',P/'tests/test_d3_tranche2b.py')
author=importlib.util.module_from_spec(spec);spec.loader.exec_module(author)
dp=author.dp;CM=author.CM;RC=author.RC;TABLE=author.TABLE;D2S=author.D2S;D2L=author.D2L;REG=author.REG;TA=author.TA;Fixture=author.Fixture;CTX=author.CTX   # API adaptation (Claude): the revised formal entries take the verified TwelveContext
from step1_engine.errors import InputContractError
from step1_engine.types import ClusterUID
from step1_engine import d2_bank

def stamp(d,key):
    d[key]=dp._payload_sha(d,key);return d

def inputs(fx):return {s:(fx.size_input(s,'matched'),fx.size_input(s,'native')) for s in fx.sizes}

@pytest.mark.parametrize('family',['E2','E7','E8'])
def test_normal_family_and_plan(family):
    fx=Fixture(family);fm,fn,info=fx.family_inputs()
    assert dp.verify_plan_identity(fx.plans,fx.fplans,fx.plan_identity)
    assert len(fm.configs)==len(fn.configs)==36 and all(abs(c.weight-1/36)<1e-15 for c in fm.configs+fn.configs)
    g=dp.twelve_official_gate(fm,fn,'smoke');assert g.passed
    off=dp.twelve_official_gate(fm,fn,'official',plan_identity=fx.plan_identity,table=CTX.table)   # API adaptation: the official 12-position gate now also compares the plans' content with the fixed identity
    assert not off.passed and all(c['passed'] for c in off.diagnostics['twelve_checks'])
    assert info['full_surviving_scope'] is True

def test_normal_two_batch_plan_prefix_binding():
    g=author.group_for(TABLE,'evaluation','E7')
    uid={b:[ClusterUID(1,200,g,b,i) for i in range(k)] for b,k in [(0,2),(1,6)]}
    p,f,ident=dp.fix_family_plans(TABLE,'E7',uid,3,TABLE['master_seed'],B=10,B_KDE=12)
    assert dp.verify_plan_identity(p,f,ident)
    assert all(set(v.strata)=={0,1} and v.strata[0]==uid[0] and v.strata[1]==uid[1] for v in p.values())

@pytest.mark.parametrize('field',['evaluation','fitting'])
@pytest.mark.parametrize('keep',[0,4])
def test_plan_identity_requires_every_seed_record(field,keep):
    fx=Fixture();d=copy.deepcopy(fx.plan_identity);d[field]=d[field][:keep];stamp(d,'identity_sha256')
    with pytest.raises(InputContractError):dp.verify_plan_identity(fx.plans,fx.fplans,d)

def test_zero_seed_empty_identity_is_not_registered_five_seed_plan():
    fx=Fixture();d=copy.deepcopy(fx.plan_identity);d.update(seeds=0,evaluation=[],fitting=[]);stamp(d,'identity_sha256')
    with pytest.raises(InputContractError):dp.verify_plan_identity({}, {}, d)

@pytest.mark.parametrize('field,value',[('family','E8'),('master_seed',1),('evaluation_group',999),('B_KDE',1)])
def test_plan_header_must_match_recorded_objects(field,value):
    fx=Fixture('E2');d=copy.deepcopy(fx.plan_identity);d[field]=value;stamp(d,'identity_sha256')
    with pytest.raises(InputContractError):dp.verify_plan_identity(fx.plans,fx.fplans,d)

@pytest.mark.parametrize('purpose',[300,400])
def test_fix_evaluation_plans_rejects_non_evaluation_uid_purpose(purpose):
    fx=Fixture('E7');u=[ClusterUID(1,purpose,author.group_for(TABLE,'evaluation','E7'),0,i) for i in range(40)]
    with pytest.raises(InputContractError):dp.fix_family_plans(TABLE,'E7',{0:u},60,TABLE['master_seed'],B=20,B_KDE=25)

def test_actual_multiplicity_edit_is_detected_by_existing_identity_checker():
    fx=Fixture();m=fx.plans[0].multiplicities[0];j=int(np.flatnonzero(m[0]>0)[0]);m[0,j]-=1;m[0,(j+1)%m.shape[1]]+=1
    fx.plans[0].validate()
    with pytest.raises(InputContractError):dp.verify_plan_identity(fx.plans,fx.fplans,fx.plan_identity)

@pytest.mark.parametrize('field,system_index',[('covariance_receipt_sha256',0),('covariance_receipt_sha256',1),('twelve_assets_sha256',1),('manifest_sha256',0),('registry_sha256',1)])
def test_assembly_rejects_mixed_source_before_relabelling(field,system_index):
    fx=Fixture('E2');ss=inputs(fx);f=ss['L1.20'][system_index];f.grid_identity[field]='0'*64
    # Adaptation (Claude): the revised twelve validator binds every identity to the VERIFIED receipt, so the edited view may already be refused by its own validate(); the
    # contract (refusal before any relabelling, never repaired with the first input) is asserted on the assembly either way.
    try:f.validate()
    except InputContractError:pass
    with pytest.raises(InputContractError):dp.assemble_twelve_family(CTX,'E2',ss)   # API adaptation: (ctx, family, size_inputs)

def test_builder_does_not_promote_unregistered_receipt_to_bound_profile():
    fx=Fixture();d=copy.deepcopy(RC);e=d['positions']['20104'];e['cov_file_sha256']='0'*64;stamp(d,'receipt_sha256')
    with pytest.raises(InputContractError):dp.verify_d3_covariance_receipt(d,str(P))
    ss=fx.supplies('L1.00','matched')
    for s in ss:
        if s.config_id==20104:s.cov_manifest['cov_file_sha256']='0'*64
    with pytest.raises(InputContractError):dp.build_twelve_size_input(d,'E2','L1.00','matched',ss,fx.plans,fx.fplans)   # API adaptation: a caller receipt dict in place of the verified context

@pytest.mark.parametrize('what',['origin','receipt_id'])
def test_grid_covariance_provenance_cannot_be_relabelled(what):
    fx=Fixture();fm=fx.size_input('L1.00','matched');g=copy.deepcopy(fm.grid_identity)
    if what=='origin':g['cov_bound'][20104]['origin']='first_wave_D1'
    else:g['cov_bound'][20104]['receipt']='UNREGISTERED_RECEIPT'
    with pytest.raises(InputContractError):dp.validate_twelve_grid_identity(g,'E2','matched',[c.evaluation_id for c in fm.configs],[c.weight for c in fm.configs])

def test_existing_invalid_supply_and_incomplete_scope_remain_refused():
    fx=Fixture()
    with pytest.raises(InputContractError):dp.build_twelve_size_input(CTX,'E2','L1.00','matched',fx.supplies('L1.00','matched')[:-1],fx.plans,fx.fplans)   # API adaptation
    fx=Fixture(sizes=('L1.00',));fm,fn,info=fx.family_inputs();g=dp.twelve_official_gate(fm,fn,'official')
    assert not g.passed and not info['full_surviving_scope']
    assert any(not c['passed'] and c['code'].endswith('full_surviving_scope') for c in g.diagnostics['twelve_checks'])

def _root_with(tmp_path, edit):
    """API adaptation (Claude): the revised build_bank_spec_v2 takes only a verified TwelveContext, so a non-canonical upstream is exercised by editing a scratch copy of the tree
    (D-2 spec / D-2 ledger / D-3 map+receipt+pins) and asking for a context from it; the contract (refusal) is unchanged."""
    import shutil
    root=author._copy_root(tmp_path);shutil.copytree(P/'registered_assets/d2',Path(root)/'registered_assets/d2');shutil.copy(P/'registered_assets/b3_2_twelve_assets.json',Path(root)/'registered_assets');edit(Path(root));return root

def _rewrite(path,fn):
    d=json.loads(Path(path).read_text());fn(d);Path(path).write_text(json.dumps(d,indent=1))

@pytest.mark.parametrize('field,value',[('N_max',2000000),('master_seed',17),('m',50)])
def test_bank_spec_v2_rejects_stale_or_noncanonical_d2_spec(tmp_path,field,value):
    old=copy.deepcopy(D2S);old[field]=value
    with pytest.raises(InputContractError):d2_bank.verify_bank_spec_content(old,TABLE)
    # Keep old spec_sha256 unchanged: actual contents no longer hash to the referenced identity.
    root=_root_with(tmp_path,lambda r:_rewrite(r/'d/d2_bank_spec.json',lambda d:d.__setitem__(field,value)))
    with pytest.raises(InputContractError):dp.build_bank_spec_v2(dp.twelve_context(root))

@pytest.mark.parametrize('unit',['ref_E2_b0','cfg20101_b0'])
def test_bank_spec_v2_rejects_altered_accepted_d2_unit_identity(tmp_path,unit):
    root=_root_with(tmp_path,lambda r:_rewrite(r/'registered_assets/d2/d2_generation_ledger.json',lambda d:d['families']['E2']['units'][unit].__setitem__('manifest_sha256','0'*64)))
    with pytest.raises(InputContractError):dp.build_bank_spec_v2(dp.twelve_context(root))

def test_bank_spec_v2_does_not_silently_lose_one_configuration(tmp_path):
    def trim(r):
        cm=json.loads((r/'d/d3_config_map.json').read_text());cm['configurations']=[x for x in cm['configurations'] if x['config_id']!=40312];cm['map_sha256']=dp._map_payload_sha(cm);(r/'d/d3_config_map.json').write_text(json.dumps(cm))
        rc=json.loads((r/'registered_assets/d3/d3_covariance_receipt.json').read_text());rc['config_map_sha256']=cm['map_sha256'];rc['positions'].pop('40312');stamp(rc,'receipt_sha256');(r/'registered_assets/d3/d3_covariance_receipt.json').write_text(json.dumps(rc))
        _rewrite(r/'d/d3_pins.json',lambda d:d.update(config_map_sha256=cm['map_sha256'],covariance_receipt_sha256=rc['receipt_sha256']))
    root=_root_with(tmp_path,trim)
    with pytest.raises(InputContractError):dp.build_bank_spec_v2(dp.twelve_context(root))

def test_normal_spec_fields_detached_and_f64_w2_scope_preserved():
    v=dp.build_bank_spec_v2(CTX)   # API adaptation
    assert v==json.loads((P/'d/d3_bank_spec.json').read_text()) and v['counts']['generate']==81 and v['counts']['reuse']==27
    for e in v['configurations'].values():
        if e['mode']=='generate_D3b':assert e['w2_primary'] is None and e['selections']['evaluation']=={'0':['float64'],'1':['float64']}
    v['plan_schema']['bootstrap']['seeds']=0
    assert dp.PLAN_SCHEMA_V2['bootstrap']['seeds']==5

# ----- Consumption-time boundary: actual raw NPY files, independent real-basis algebra,
# but a TEST DOUBLE replaces the unavailable SHA-frozen external loader/constructor.
def raw_to_real(raw):
    lm=[(l,m) for l in (2,3,4) for m in range(-l,l+1)];idx={v:i for i,v in enumerate(lm)};U=np.zeros((21,21),complex);J=np.zeros((21,21));j=0
    for l in (2,3,4):
        U[j,idx[(l,0)]]=1;j+=1
        for m in range(1,l+1):
            U[j,idx[(l,m)]]=1/np.sqrt(2);U[j,idx[(l,-m)]]=(-1)**m/np.sqrt(2);j+=1
            U[j,idx[(l,m)]]=1j/np.sqrt(2);U[j,idx[(l,-m)]]=-1j*(-1)**m/np.sqrt(2);j+=1
    for i,(l,m) in enumerate(lm):J[i,idx[(l,-m)]]=(-1)**m
    H=(raw+raw.conj().T)/2;H=(H+J@H.conj()@J.T)/2
    return U,(U@H@U.conj().T).real

def loader_setup(monkeypatch, root, cid, edit=None):
    from step1_engine import legacy_kernel as lk
    target=Path(root)/RC['positions'][str(cid)]['registered_file'];orig=target.read_bytes();calls=[]
    class LoaderDouble:
        @staticmethod
        def load_cov_full(path,lmax=4):
            b=Path(path).read_bytes();a=np.load(io.BytesIO(b),allow_pickle=False);U,C=raw_to_real(a);calls.append({'path':str(path),'sha256':hashlib.sha256(b).hexdigest()})
            return U,C,{'cov_array_sha256':hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()}
    def verified_double(*args):
        if edit=='append':target.write_bytes(orig+b'AUDIT_TRAILING_BYTES')
        elif edit=='array':
            a=np.load(io.BytesIO(orig),allow_pickle=False);np.save(target,2*a)
        return LoaderDouble(),{'test_double':True,'scope':'identity/consume boundary, not fixed loader authentication'}
    # Match and psqrt are the unchanged production algorithms. Constructor external assets are not invoked.
    k=lk.LegacyKernel.__new__(lk.LegacyKernel);k.c_pr3=np.array([200.,200.,200.]);k.C_ISO=np.eye(21)*200.
    monkeypatch.setattr(dp,'_verified_frozen_loader',verified_double);monkeypatch.setattr(lk,'LegacyKernel',lambda *_:k)
    return target,orig,calls

def test_consumer_normal_real_array_boundary_with_test_loader(tmp_path,monkeypatch):
    root=author._copy_root(tmp_path);p,orig,calls=loader_setup(monkeypatch,root,20104)
    out=dp.intake_twelve_covariance(20104,root,'TEST_ONLY_NO_EXTERNAL_CHECKOUT')
    assert out['cov_file_sha256']==hashlib.sha256(orig).hexdigest() and out['C_real'].shape==(21,21) and out['roots_info']['native']['clip']==0
    assert p.read_bytes()==orig and len(calls)==1

def test_consumer_changed_array_is_refused_by_loader_identity(tmp_path,monkeypatch):
    root=author._copy_root(tmp_path);p,orig,calls=loader_setup(monkeypatch,root,20104,'array')
    # Adaptation (Claude; closing contract R-D3T2B-D 'correct snapshot or safe refusal'): the revised intake hands the AUTHENTICATED snapshot to the loader, so an array replaced
    # on the original path after authentication is either refused or never consumed (the loader must have read exactly the authenticated bytes); the NEXT intake of the changed path is refused.
    try:out=dp.intake_twelve_covariance(20104,root,'TEST_ONLY_NO_EXTERNAL_CHECKOUT')
    except InputContractError:return
    assert calls and all(c['sha256']==out['cov_file_sha256']==hashlib.sha256(orig).hexdigest() for c in calls) and p.read_bytes()!=orig
    monkeypatch.setattr(dp,'_verified_frozen_loader',lambda *a:(type('L',(),{'load_cov_full':staticmethod(lambda path,lmax=4:(lambda b:(lambda a:(raw_to_real(a)[0],raw_to_real(a)[1],{'cov_array_sha256':hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()}))(np.load(io.BytesIO(b),allow_pickle=False)))(Path(path).read_bytes()))})(),{'test_double':True}))
    with pytest.raises(InputContractError):dp.intake_twelve_covariance(20104,root,'TEST_ONLY_NO_EXTERNAL_CHECKOUT')

def test_consumer_actual_bytes_equal_authenticated_bytes_or_refusal(tmp_path,monkeypatch):
    root=author._copy_root(tmp_path);p,orig,calls=loader_setup(monkeypatch,root,20104,'append')
    try:out=dp.intake_twelve_covariance(20104,root,'TEST_ONLY_NO_EXTERNAL_CHECKOUT')
    except InputContractError:return
    # A safe old snapshot is allowed; must be the bytes the file-loader actually read.
    assert calls and all(c['sha256']==out['cov_file_sha256'] for c in calls), 'loader consumed different file bytes than returned verified file identity'
