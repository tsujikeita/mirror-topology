"""Candidate-only checks of newly added complete JSONL and notebook failure logs.
All values are synthetic, not a validation of the user's scientific bank data.
"""
import os,json,hashlib,sys,types
from pathlib import Path
import numpy as np
import pytest
import test_audit_d2_verify_v02_edges_chatgpt as h   # adapted module name
base=h.base
full=h.full

def test_all_flip_rows_have_hashed_complete_artifact(full,tmp_path,monkeypatch):
    # This scope deliberately lacks real healpy. Geometry must be marked incomplete.
    monkeypatch.setitem(sys.modules,'healpy',None)
    table,reg=h.h.load_crn_table(str(h.PB/'d/d2_crn_table.json'));spec=h.db.load_bank_spec(str(h.PB/'d/d2_bank_spec.json'),table=table)
    name='cfg30101_w2';p=full/'d2'/name;h.shutil.rmtree(p)
    man=h.db.generate_w2_position_bank(h.h._Kern(),reg,table,spec,30101,np.eye(21)*1.1,str(p),h.db.CallInventory(),scale=.0105,chunk_clusters=7)
    rg=json.loads((full/'d2/d2_bank_registry.json').read_text());rg['directories'][name]['manifest_sha256']=man['manifest_sha256'];h.h.dump(full/'d2/d2_bank_registry.json',rg);h.h.update_final(full);h.h.rebind_npz(full,name,h.all_near_flips)
    out=tmp_path/'out';r=h.invoke(h.loadscript(),full,out,'--mode','test');q=r['report'];s=q['f32_sensitivity'][name]['model_matched'];ref=s['full_flip_evidence_ref'];raw=(out/ref['file']).read_bytes();rows=[json.loads(x) for x in raw.splitlines()]
    assert r['rc']==0 and q['all_ok'] is True and len(rows)==2100 and ref['rows']==2100
    assert ref['bytes']==len(raw) and ref['sha256']==hashlib.sha256(raw).hexdigest()
    assert [x['row'] for x in rows]==list(range(2100)) and len(s['flip_evidence'])==2000 and s['inline_evidence_is_preview'] is True
    assert q['f32_registered_gate']['evidence_complete'] is False and q['f32_registered_gate']['axis_geometry_status']=='NOT_EVALUATED'
    h.save('candidate_complete_jsonl',rows=len(rows),sha256=ref['sha256'],bytes=len(raw),inline_preview=2000,integrity=q['all_ok'],scope=q['f32_registered_gate'])

@pytest.mark.parametrize('rc,has_report',[(0,True),(2,True),(2,False)])
def test_notebook_logs_and_final_failure(tmp_path,rc,has_report):
    n=json.loads((h.PB/'d/MirrorTopology_Step1_D2_verify_v0.2.ipynb').read_text());cell=''.join(n['cells'][3]['source']);out=tmp_path/'out';(out/'report').mkdir(parents=True)
    if has_report:h.h.dump(out/'report/d2_verify_E7.json',{'all_ok':True,'coverage_complete':True,'accepted_run_binding':True,'f32_registered_gate':{},'failures':[]})
    cp=types.SimpleNamespace(returncode=rc,stdout='preserved stdout\n',stderr='preserved stderr\n')
    ns={'OUT':str(out),'FAMILY':'E7','SCRIPT':'TEST_ONLY','PHASEB':str(h.PB),'RUN_ROOT':'TEST_ONLY','lock':{},'os':os,'sys':sys,'json':json,'subprocess':types.SimpleNamespace(run=lambda *a,**k:cp)}
    exec(compile(cell,'candidate_execution_cell','exec'),ns)
    assert (out/'verify_stdout.txt').read_text()==cp.stdout and (out/'verify_stderr.txt').read_text()==cp.stderr
    f=json.loads((out/'verify_final_record.json').read_text());assert f['exit_code']==rc and f['all_ok'] is has_report
    assert bool(f['exit_code']==0 and f['all_ok'] is True and f['coverage_complete'] is True and f['accepted_run_binding'] is True) is (rc==0 and has_report)
    h.save(f'candidate_notebook_{rc}_{has_report}',record=f,logs_preserved=True)
