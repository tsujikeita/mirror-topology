# Path adaptation only (Claude, 2026-09-30): ChatGPT audit original `test_reference_publication.py` bundled verbatim except the fixture import (`fixture` -> `d3b_t1_audit_fixture_chatgpt`, the bundled copy of the audit `fixture.py`). Default root = this phaseB (AUDIT_PHASEB_ROOT overrides).
"""Reference-only direct tests for whole-document publication and I/O failure."""
import io,json,os,copy,hashlib
from pathlib import Path
import pytest
from d3b_t1_audit_fixture_chatgpt import P,load,jload
S=load('candidate_publication',P/'d/d3_bankgen.py')

def test_normal_whole_document_publication_receipt(tmp_path):
 p=tmp_path/'r.json';doc={'unicode':'記録','nested':{'keys':[1,2,3]},'value':True}
 receipt=S._publish_json(str(p),doc);raw=p.read_bytes()
 assert receipt=={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} and jload(p)==doc and not (tmp_path/'r.json.tmp').exists()

@pytest.mark.parametrize('where',['json','replace','readback'])
def test_publication_io_errors_cannot_return_receipt(tmp_path,monkeypatch,where):
 p=tmp_path/'r.json'
 if where=='json':monkeypatch.setattr(json,'dump',lambda *a,**kw:(_ for _ in ()).throw(OSError('TEST write fault')))
 elif where=='replace':monkeypatch.setattr(os,'replace',lambda *a,**kw:(_ for _ in ()).throw(OSError('TEST replace fault')))
 else:
  real=os.replace
  def bad(src,dst):real(src,dst);Path(dst).write_text('{"wrong":true}')
  monkeypatch.setattr(os,'replace',bad)
 with pytest.raises((OSError,RuntimeError)):S._publish_json(str(p),{'ok':True})
 assert not (tmp_path/'r.json.tmp').exists()
