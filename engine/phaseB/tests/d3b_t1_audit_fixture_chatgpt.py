# Bundled copy of the ChatGPT audit `tests/fixture.py` (D-3b tranche 1 audit; renamed only). Explicit TEST DOUBLES; see the docstring.
"""Audit fixture: actual registered context/arrays and production root algebra.
Explicit TEST DOUBLES: Phase-C external file digest, live environment, frozen
loader authentication/complex-to-real adapter, kernel D_batch/scan. No CT,
A10 reproduction, official bank, observed target, or scientific label claimed.
"""
from pathlib import Path
import os,sys,json,hashlib,importlib.util,io,types,copy,contextlib
import numpy as np
P=Path(os.environ.get('AUDIT_PHASEB_ROOT',str(Path(__file__).resolve().parent.parent))).resolve()
sys.path.insert(0,str(P))
from step1_engine import d3_bank as b3,d2_bank as b2,d3_profile as dp,production,legacy_kernel as lk,official_gate as og

def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
H=load('submitted_d3b_helper',P/'tests/test_d3b_tranche1.py')
CTX=H.CTX
ORIGINAL_K=lk.LegacyKernel
class KernelDouble(H._Kern):
 def __init__(self,*a):
  super().__init__();self.C_ISO=np.eye(21)*200.;self.c_pr3=np.array([200.,200.,200.])
 psqrt=staticmethod(ORIGINAL_K.psqrt)
 matched=ORIGINAL_K.matched

def raw_real(raw):
 lm=[(l,m) for l in (2,3,4) for m in range(-l,l+1)];idx={v:i for i,v in enumerate(lm)};U=np.zeros((21,21),complex);J=np.zeros((21,21));j=0
 for l in (2,3,4):
  U[j,idx[(l,0)]]=1;j+=1
  for m in range(1,l+1):
   U[j,idx[(l,m)]]=1/np.sqrt(2);U[j,idx[(l,-m)]]=(-1)**m/np.sqrt(2);j+=1
   U[j,idx[(l,m)]]=1j/np.sqrt(2);U[j,idx[(l,-m)]]=-1j*(-1)**m/np.sqrt(2);j+=1
 for i,(l,m) in enumerate(lm):J[i,idx[(l,-m)]]=(-1)**m
 C=(raw+raw.conj().T)/2;C=(C+J@C.conj()@J.T)/2
 return U,(U@C@U.conj().T).real
class LoaderDouble:
 @staticmethod
 def load_cov_full(path,lmax=4):
  raw=np.load(path,allow_pickle=False);U,C=raw_real(raw)
  return U,C,{'cov_array_sha256':b2._asha(raw)}

def tree(p):return {str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in Path(p).rglob('*') if f.is_file()}
def jload(p):return json.loads(Path(p).read_bytes())
def dump(p,d):Path(p).write_text(json.dumps(d,indent=1))

def install(mp,base):
 pc=Path(base)/'TEST_ONLY_phaseC';pc.mkdir(exist_ok=True);(pc/'PACKET_INVENTORY.json').write_text('{"files":{}}')
 script=load('submitted_d3b_script',P/'d/d3_bankgen.py');orig_sha=script.sha
 pins=jload(P/'d/d3_pins.json'); ex=pins['environment']
 # The external Phase-C response is a test double; all engine/script/pins SHA
 # checks continue to read and verify the unchanged submitted source.
 mp.setattr(script,'sha',lambda p:pins['phaseC_inventory_sha256'] if Path(p)==pc/'PACKET_INVENTORY.json' else orig_sha(p))
 env={k:ex[k] for k in ('python','numpy','scipy','healpy','pot','camb')};env['blas_threads']=[dict(user_api='blas',internal_api='openblas',num_threads=2,filepath='/TEST_ONLY/numpy.libs/libopenblas.so')]
 mp.setattr(og,'current_env',lambda:copy.deepcopy(env));mp.setattr(og,'_blas_check',lambda v:True)
 mp.setitem(sys.modules,'camb',types.SimpleNamespace(__version__=ex['camb']))
 loader=lambda *a:(LoaderDouble(),{'test_double':True,'scope':'TEST_ONLY frozen authentication and algebra adapter'})
 mp.setattr(production,'_verified_frozen_loader',loader);mp.setattr(dp,'_verified_frozen_loader',loader);mp.setattr(lk,'LegacyKernel',KernelDouble)
 def run(out,*extra,family='E2',sizes='L1.00',configs='20104',scale='0.002'):
  args=['d3_bankgen.py','--mt','TEST_ONLY_EXTERNAL','--phaseb',str(P),'--phasec',str(pc),'--out',str(out),'--family',family,'--sizes',sizes,'--selftest-scale',scale,'--selftest-skip-a10']
  if configs is not None:args+=['--selftest-configs',configs]
  args+=list(extra);mp.setattr(sys,'argv',args)
  text=io.StringIO()
  with contextlib.redirect_stdout(text),contextlib.redirect_stderr(text):rc=script.main()
  Path(out).parent.mkdir(parents=True,exist_ok=True);Path(str(out)+'.captured.log').write_text(text.getvalue())
  return rc,jload(Path(out)/'d3_run_manifest.json') if (Path(out)/'d3_run_manifest.json').exists() else None
 return script,run
