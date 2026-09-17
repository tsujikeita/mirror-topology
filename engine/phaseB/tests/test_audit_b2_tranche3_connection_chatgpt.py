"""New-stage connection contract: not a test of the already validated low-level Q arithmetic."""
from pathlib import Path
import os,sys,importlib.util
import numpy as np
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(ROOT))
sp=importlib.util.spec_from_file_location('t3fixture',ROOT/'tests/test_b2_tranche3.py');f=importlib.util.module_from_spec(sp);sp.loader.exec_module(f)
from step1_engine.orchestrator import _family_Q
from step1_engine.expansion import family_expansion_plan

def test_actual_point_results_connect_to_expansion_plan():
 fm,fn,z=f.make_family_pair(np.random.default_rng(20260914))
 Q,cis,precision,per_config,w,ev=_family_Q(fm,80.,400.)
 result=family_expansion_plan(per_config,'N0')
 assert result['family_status']=='resolved'
 assert result['actions'][100]['action']=='keep'
