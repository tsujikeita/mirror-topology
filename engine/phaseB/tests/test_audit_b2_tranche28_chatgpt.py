"""New KDE batch-path audit: finite synthetic inputs, literal/reference oracles.
No real CMB data or production calibration. PHASEB_ROOT selects the implementation.
"""
import os,sys
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(os.environ.get('PHASEB_ROOT',Path(__file__).resolve().parents[1]))
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import step1_engine.density as den
import step1_engine.orchestrator as o
from step1_engine.errors import InputContractError
from test_b2_tranche4 import make_staged_family

def sample(seed=123,K=30,m=10,B=8):
    rng=np.random.default_rng(seed);cid=np.repeat(np.arange(K),m)
    X=rng.normal(size=(K*m,2))
    M=np.stack([np.bincount(rng.integers(K,size=K),minlength=K) for _ in range(B)])
    return X,cid,M,np.array([[.2,-.4],[0.,0.]])

def reference(X,cid,M,pts,fs=1.):
    return np.stack([den.kde_logpdf_literal(X,m[cid],pts,fs) for m in M])

@pytest.mark.parametrize('fs',[.7,1.,1.4])
def test_normal_literal_and_frequency_weight_equivalence(fs):
    X,cid,M,p=sample();got=den.kde_logpdf_replicates(X,cid,p,M,factor_scale=fs)
    assert np.allclose(got,reference(X,cid,M,p,fs),rtol=1e-9,atol=1e-9)

@pytest.mark.parametrize('offset',[1e6,1e8])
def test_large_common_offset_preserves_registered_kde(offset):
    X,cid,M,p=sample();X+=offset;p+=offset
    got=den.kde_logpdf_replicates(X,cid,p,M)
    # At offset=1e8, SciPy's raw-coordinate evaluator itself loses ~1e-8
    # relative to its translated equivalent. Use the engine's registered
    # centered frequency-weight path AND an independently row-expanded,
    # translated SciPy oracle; a translation has unit Jacobian.
    weighted=np.stack([den.kde_logpdf_weighted(X,m[cid],p) for m in M])
    centered_literal=reference(X-X[0],cid,M,p-X[0])
    assert np.allclose(got,weighted,rtol=1e-9,atol=1e-9)
    assert np.allclose(got,centered_literal,rtol=1e-9,atol=1e-9)

def test_positive_determinant_is_not_a_positive_definite_covariance():
    # Current raw-moment subtraction gives a negative-definite 2x2 covariance.
    rng=np.random.default_rng(10);X=rng.normal(size=(100,2))+1e8
    cid=np.repeat(np.arange(10),10);M=np.ones((1,10),np.int64);p=np.array([[1e8,1e8]])
    # Audit31 correction to our earlier oracle, NOT a production-kernel change.
    # With a common 1e8 offset, raw-coordinate SciPy logpdf itself can differ
    # from an 80-digit direct KDE by ~3.6e-9. Translate BOTH data and target
    # (Jacobian 1), and independently check the registered frequency formula.
    # Keep exactly the same tolerance; do not clip eigenvalues or add jitter.
    got=den.kde_logpdf_replicates(X,cid,p,M)
    weighted=np.stack([den.kde_logpdf_weighted(X,m[cid],p) for m in M])
    translated=reference(X-X[0],cid,M,p-X[0])
    assert np.allclose(got,weighted,rtol=1e-9,atol=1e-9)
    assert np.allclose(got,translated,rtol=1e-9,atol=1e-9)

def test_zero_weight_nearest_rows_do_not_cause_false_underflow():
    X,cid,M,p=sample();X+=100;X[:10]=0
    M=np.ones((1,30),np.int64);M[0,0]=0;M[0,1]=2;p=np.zeros((1,2))
    ref=reference(X,cid,M,p)
    assert np.isfinite(ref).all() and ref[0,0] < -60000
    assert np.allclose(den.kde_logpdf_replicates(X,cid,p,M),ref,rtol=1e-9,atol=1e-9)

@pytest.mark.parametrize('chunk',[-1,0,True,1.5])
def test_chunk_is_positive_nonbool_integer(chunk):
    X,cid,M,p=sample()
    with pytest.raises(InputContractError):den.kde_logpdf_replicates(X,cid,p,M,chunk=chunk)

@pytest.mark.parametrize('p',[
    np.array([.2]),np.array([[.2],[.4]]),np.array([[.2,.4,.6]]),np.empty((0,2)),
    np.array([[np.nan,0.]]),np.array([[np.inf,0.]])])
def test_evaluation_points_are_nonempty_finite_pairs(p):
    X,cid,M,_=sample()
    with pytest.raises(InputContractError):den.kde_logpdf_replicates(X,cid,p,M)

def test_no_replicates_rejected():
    X,cid,M,p=sample()
    with pytest.raises(InputContractError):den.kde_logpdf_replicates(X,cid,p,M[:0])

def test_empty_bank_rejected_with_contract_error():
    with pytest.raises(InputContractError):den.kde_logpdf_replicates(np.empty((0,2)),np.array([],dtype=int),[[0.,0.]],np.empty((2,0),int))

def test_numpy_integer_chunk_accepted_and_partition_invariant():
    X,cid,M,p=sample();a=den.kde_logpdf_replicates(X,cid,p,M,chunk=np.int64(3));b=den.kde_logpdf_replicates(X,cid,p,M,chunk=1)
    assert np.allclose(a,b,rtol=1e-12,atol=1e-12)

def test_unequal_cluster_sizes_and_shuffled_row_order():
    rng=np.random.default_rng(56);counts=np.array([3,5,9,4,6,10]);cid=np.repeat(np.arange(len(counts)),counts)
    X=rng.normal(size=(len(cid),2));M=np.stack([np.bincount(rng.integers(len(counts),size=len(counts)),minlength=len(counts)) for _ in range(7)])
    order=rng.permutation(len(X));X=X[order];cid=cid[order];p=np.array([[.2,.3],[-.8,-.2]])
    assert np.allclose(den.kde_logpdf_replicates(X,cid,p,M),reference(X,cid,M,p),rtol=1e-9,atol=1e-9)

def test_singular_public_array_api_still_raises():
    X,cid,M,p=sample();X[:10]=0;M[3]=0;M[3,0]=30
    with pytest.raises(InputContractError):den.kde_logpdf_replicates(X,cid,p,M)

@pytest.fixture
def family():
    return make_staged_family(np.random.default_rng(6),K0=80,K_fit=30,m_fit=10,B=20,n_cfg=1)

def logd(family,backend,monkeypatch):
    monkeypatch.setattr(o,'KDE_CI_BACKEND',backend)
    return o._family_logD(family,np.array([80.,400.]),np.ones(1),True)

def test_family_failure_inventory_preserves_one_failed_replicate(family,monkeypatch):
    family.fitting[100].X_model[:10]=0
    for s in family.fit_plans:
        family.fit_plans[s]=np.ones((30,30),np.int64)
        family.fit_plans[s][3]=0;family.fit_plans[s][3,0]=30
    family.validate()
    ref=logd(family,'per_replicate',monkeypatch);got=logd(family,'batched',monkeypatch)
    assert ref[1].counts['technical_invalid']==1
    assert got[1].math_state=='technical_fail'
    assert got[1].counts==ref[1].counts
    assert got[4]['invalid_mask']==ref[4]['invalid_mask']
    mask=~np.asarray(ref[4]['invalid_mask']);assert np.allclose(np.asarray(got[4]['replicate_values'])[mask],np.asarray(ref[4]['replicate_values'])[mask],rtol=1e-9,atol=1e-9)

def test_family_checks_finite_logD_after_finite_component_subtraction(family,monkeypatch):
    calls=[]
    def finite_extremes(X,cid,pts,M,*args,**kwargs):
        calls.append(1);return np.full((len(M),1),1e308 if len(calls)==1 else -1e308)
    monkeypatch.setattr(den,'kde_logpdf_replicates',finite_extremes)
    with np.errstate(over='ignore',invalid='ignore'):
        got=logd(family,'batched',monkeypatch)
    assert got[1].math_state=='technical_fail' and got[1].counts['technical_invalid']==30
    assert all(got[4]['invalid_mask'])

def test_nonfinite_component_not_hidden_in_mixture(family,monkeypatch):
    original=den.kde_logpdf_replicates
    def fail_one(*a,**kw):
        out=original(*a,**kw);out[2,0]=-np.inf;return out
    monkeypatch.setattr(den,'kde_logpdf_replicates',fail_one)
    got=logd(family,'batched',monkeypatch)
    assert got[1].math_state=='technical_fail' and got[4]['invalid_mask'][2]

def test_unregistered_backend_rejected(family,monkeypatch):
    with pytest.raises(InputContractError):logd(family,'batched_typo',monkeypatch)

def test_standard_family_path_keeps_ci_and_values(family,monkeypatch):
    a=logd(family,'per_replicate',monkeypatch);b=logd(family,'batched',monkeypatch)
    assert a[1].math_state==b[1].math_state=='finite'
    assert np.allclose(a[4]['replicate_values'],b[4]['replicate_values'],rtol=1e-9,atol=1e-9)
    assert abs(a[1].log_lower-b[1].log_lower)<1e-9 and abs(a[1].log_upper-b[1].log_upper)<1e-9
