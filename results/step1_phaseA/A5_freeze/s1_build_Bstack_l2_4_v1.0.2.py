# -*- coding: utf-8 -*-
"""Step 1: build and validate the frozen 3072-axis B± stack for the l=2-4 evaluation band. (v1.0.2)

Outputs (in OUT):
  s1_Bstack_l2_4_N16_common_v1.npz    Bp_stack, Bm_stack (3072,21,21) float64, basis_lm, axis_pixel_ids,
                                       metadata (mask/R/valid/cnt SHA, band, normalization, dtype)
  s1_Bstack_l2_4_validation.csv        per-sample comparison: map-domain float32 (pm.scan_S) vs B-stack float64
  s1_Bstack_l2_4_provenance.json
Scope (audit 13): this makes the l2-4 evaluation and the S1 (l2-4-only) selection surrogate map-free.
Historical full-band selection and the S2 hybrid need a separate higher-dimensional stack.
"""
import os, sys, json, hashlib, time, datetime, platform, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning, module='healpy')
IN_COLAB = os.path.isdir('/content')
WORK = '/content' if IN_COLAB else '/home/claude'
PEM = os.path.join(WORK, 'pem_step1' if IN_COLAB else 'pem_repo')
MT = os.path.join(WORK, 'mt_step1') if IN_COLAB else os.environ.get('MT_REPO', '/tmp/finalchk2')
OUT = (os.path.join('/content/drive/MyDrive/mirror_topology', 'runs_step1_phaseA', 'bstack_v1.0')
       if IN_COLAB else '/home/claude/colab_sim/runs_step1_phaseA/bstack_v1.0')
PR4_DIR = '/content/drive/MyDrive/phase2_null/sources' if IN_COLAB else '/mnt/user-data/uploads'
if IN_COLAB:
    import subprocess as _sp
    if not os.path.isdir('/content/drive/MyDrive'):
        try:
            from google.colab import drive
            drive.mount('/content/drive')
        except Exception as _e:
            raise RuntimeError(
                'Google Drive が未マウントです。ノートブックのセルで次を実行してから，'
                'このスクリプトを再実行してください:\n'
                '    from google.colab import drive\n'
                "    drive.mount('/content/drive')\n"
                f'（内部エラー: {_e!r}）')
    assert os.path.isdir('/content/drive/MyDrive'), 'Driveマウント失敗：明示停止'
    _sp.run([sys.executable, '-m', 'pip', 'install', '-q', 'healpy==1.20.0'], check=True)
    _env = dict(os.environ, GIT_TERMINAL_PROMPT='0')
    for url, d, commit in [('https://github.com/tsujikeita/plane-excised-mirror.git', PEM,
                            'd36e7567e8a7869c0d7b84955b4139ab0e782af0'),
                           ('https://github.com/LauraHerold/CMBanom.git', os.path.join(WORK, 'CMBanom'),
                            'aaf8137427d54ce4c77e59734391aca491a4a8db'),
                           ('https://github.com/tsujikeita/mirror-topology.git', MT, None)]:
        if not os.path.isdir(os.path.join(d, '.git')):
            _sp.run(['git', 'clone', url, d], check=True, capture_output=True, env=_env)
        if commit:
            _sp.run(['git', '-C', d, 'checkout', '-q', '--force', commit], check=True)
import numpy as np, pandas as pd   # noqa: E402
import healpy as hp                 # noqa: E402
os.makedirs(OUT, exist_ok=True); os.chdir(WORK)
sys.path.insert(0, os.path.join(PEM, 'src')); sys.path.insert(0, MT)
import phase2_core as p2, plane_mirror as pm, t2b2_bridge as br   # noqa: E402

def sha(p):
    with open(p, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()
SCRIPT_SHA = sha(os.path.abspath(__file__)) if '__file__' in dir() else 'inline'
def asha(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def run(cmd):
    import subprocess
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
G = {}
G['G_pem_commit'] = (run(['git', '-C', PEM, 'rev-parse', 'HEAD']) == 'd36e7567e8a7869c0d7b84955b4139ab0e782af0')
G['G_pem_clean'] = (run(['git', '-C', PEM, 'status', '--porcelain', '--untracked-files=no']) == '')
assert G['G_pem_commit'] and G['G_pem_clean']
BRIDGE_SHA = sha(os.path.join(MT, 't2b2_bridge.py'))
G['G_bridge_sha'] = (BRIDGE_SHA == '45107d1608d50816712f1aa452d9fa39af4adc9ec035fbe9279b264760d65872')
assert G['G_bridge_sha'], BRIDGE_SHA

LMAX, NSIDE = 128, 16
NPIX = hp.nside2npix(NSIDE)
ms = pm.with_mask(p2.MirrorStat(NSIDE, p2.make_mask(NSIDE, 'full')), p2.make_mask(NSIDE, 'common'))
FL = p2.transfer(NSIDE, 'planck', LMAX); ELL = np.arange(LMAX + 1)
W_EVAL = ((ELL >= 2) & (ELL <= 4)).astype(float) * FL
CL = p2.load_fid_cl()
# 入力検証は2層（A4の知見）：bit-level は整数/論理配列のみ，float は許容差で比較しない
# （B-stack 自体の妥当性は §validation battery で pm.scan_S と直接比較して担保する）
INPUT_SHA = dict(processed_mask=asha(ms.mask.astype(np.uint8)), reflection_table=asha(ms.R),
                 valid_table=asha(ms.valid), cnt=asha(ms.cnt),
                 fl=asha(FL), eval_window=asha(W_EVAL), cl_array=asha(CL))
# 凍結期待値（Colab formal run 2026-09-03 の実測・A5 v1.1 official provenance と一致）
EXPECTED_BITLEVEL = dict(
    processed_mask='2b46cf1b46268cf3e7c119ec7c29de90a80fbb6e0c239572da51369da68b3305',
    reflection_table='e06b97febbaae48ac1c5bbc358637d2f3a7f874bca54de83d6ce9d630a0741f5',
    valid_table='4da781e5fa5bd46246f14b01d4e0dd41475a3f6bdae5071123bd983ac6c83cf3',
    cnt='6e62038586601ce4ac70f6a96ad0df7cc6e5c5681511723ea58f73cdb9b18686')
_bl = {k: (INPUT_SHA[k] == v) for k, v in EXPECTED_BITLEVEL.items()}     # 4項目すべてを gate
G['G_input_bitlevel'] = all(_bl.values())
if not G['G_input_bitlevel']:
    print('入力gate 内訳:', json.dumps(_bl), flush=True)
    print('  actual:', json.dumps({k: INPUT_SHA[k] for k in _bl}), flush=True)
assert G['G_input_bitlevel'], '入力gate FAIL（processed_mask / reflection_table / valid_table / cnt）'

LM = br.lm_full(); M21 = br.M_matrix()[0]; IDX = {t: k for k, t in enumerate(LM)}
RB = br.real_basis_lm()
def x_to_T(x):
    a = x @ np.conj(M21); alm = np.zeros(hp.Alm.getsize(LMAX), complex)
    for (l, m) in LM:
        if m >= 0: alm[hp.Alm.getidx(LMAX, l, m)] = a[IDX[(l, m)]]
    mb = hp.alm2map(hp.almxfl(alm, W_EVAL), NSIDE)
    return np.where(ms.mask, np.asarray(hp.remove_dipole(hp.ma(np.where(ms.mask, mb, hp.UNSEEN)))), 0.0)
def alm_to_x(alm):
    a = np.zeros(21, complex)
    for (l, m) in LM:
        a[IDX[(l, m)]] = (alm[hp.Alm.getidx(LMAX, l, m)] if m >= 0
                          else ((-1) ** m) * np.conj(alm[hp.Alm.getidx(LMAX, l, -m)]))
    return (a @ M21.T).real

# ---- 1. build ----
t0 = time.time()
Yeff = np.column_stack([x_to_T(np.eye(21)[i]) for i in range(21)])          # (NPIX, 21)
Bp = np.empty((NPIX, 21, 21)); Bm = np.empty((NPIX, 21, 21))
for a in range(NPIX):
    Yr = Yeff[ms.R[a]]; v = ms.valid[a].astype(float); c = float(ms.cnt[a])
    Ap = 0.5 * (Yeff + Yr); Am = 0.5 * (Yeff - Yr)
    Bp[a] = (Ap * v[:, None]).T @ Ap / c; Bm[a] = (Am * v[:, None]).T @ Am / c
Bp = 0.5 * (Bp + Bp.transpose(0, 2, 1)); Bm = 0.5 * (Bm + Bm.transpose(0, 2, 1))   # exact symmetry
T_BUILD = time.time() - t0
BSTACK_SHA = hashlib.sha256(np.ascontiguousarray(Bp).tobytes() + np.ascontiguousarray(Bm).tobytes()).hexdigest()
# frozen pix1134 B± (T2b-2 / Step 0)
_z = np.load(os.path.join(MT, 'docs', 'step0_frozen_Bpm_v1.npz'), allow_pickle=True)
G['G_bpm_1134_match'] = bool(np.abs(Bp[1134] - _z['Bp']).max() < 1e-14 and np.abs(Bm[1134] - _z['Bm']).max() < 1e-14)
G['G_bstack_symmetric'] = bool(np.abs(Bp - Bp.transpose(0, 2, 1)).max() == 0 and np.abs(Bm - Bm.transpose(0, 2, 1)).max() == 0)
_evmin = min(np.linalg.eigvalsh(Bp).min(), np.linalg.eigvalsh(Bm).min())
G['G_bstack_psd'] = bool(_evmin > -1e-14)
print(f'[1] build {T_BUILD:.1f}s  sha={BSTACK_SHA[:16]}  1134 match={G["G_bpm_1134_match"]}  psd_min={_evmin:.2e}', flush=True)

# ---- 2. validation battery: map-domain float32 (pm.scan_S) vs B-stack float64 ----
T1o, T2o = 39.67178834527284, 259.3375006282747
def compare(alm, label):
    m_eval = hp.alm2map(hp.almxfl(alm.copy(), W_EVAL), NSIDE)
    Sp_ref, Sm_ref = pm.scan_S(ms, m_eval)                                  # historical float32
    x = alm_to_x(alm)
    Sp_q = np.einsum('i,aij,j->a', x, Bp, x); Sm_q = np.einsum('i,aij,j->a', x, Bm, x)
    a_ref, a_q = int(np.argmin(Sp_ref)), int(np.argmin(Sp_q))
    a_q32 = int(np.argmin(Sp_q.astype(np.float32)))
    return dict(sample=label, axis_ref=a_ref, axis_bstack=a_q, axis_bstack_f32cast=a_q32,
                same_axis=(a_ref == a_q), same_axis_f32cast=(a_ref == a_q32),
                sep_deg=float(pm.axis_sep_deg(NSIDE, a_ref, a_q)),
                T1_ref=float(Sp_ref[a_ref]), T1_bstack=float(Sp_q[a_q]),
                T2_ref=float(Sm_ref[a_ref]), T2_bstack=float(Sm_q[a_q]),
                max_rel_Sp=float(np.abs(Sp_q - Sp_ref).max() / Sp_ref.max()),
                max_rel_Sm=float(np.abs(Sm_q - Sm_ref).max() / Sm_ref.max()),
                EB_ref=bool(Sp_ref[a_ref] <= T1o and Sm_ref[a_ref] <= T2o),
                EB_bstack=bool(Sp_q[a_q] <= T1o and Sm_q[a_q] <= T2o))
rows = []
T_SRC = hp.gauss_beam(np.radians(1.0), lmax=LMAX) * p2.pixwin_pad(128, LMAX)
cm = {'PR3_Commander': 'commander', 'PR3_NILC': 'nilc', 'PR3_SEVEM': 'sevem', 'PR3_SMICA': 'smica',
      'Nofi_70GHz': 'cleaned_70GHz_v9', 'Nofi_94GHz': 'cleaned_94GHz_v9',
      'Nofi_100GHz': 'cleaned_100GHz_v9', 'Nofi_143GHz': 'cleaned_143GHz_v9'}
PATHS = {k: f'CMBanom/data/real/map_{v}_nside_128.fits' for k, v in cm.items()}
for m in ['sevem', 'commander']:
    p = os.path.join(PR4_DIR, f'npipe_{m}_128.fits')
    if os.path.exists(p): PATHS[f'PR4_{m.capitalize()}'] = p
for k, p in PATHS.items():
    alm = hp.almxfl(hp.map2alm(hp.read_map(p), lmax=LMAX), 1.0 / np.maximum(T_SRC, 1e-12))
    rows.append(compare(alm, k))
N_NULL = int(os.environ.get('BS_NNULL', '1000')); N_FRESH = int(os.environ.get('BS_NFRESH', '2000'))
t0 = time.time()
for s in range(N_NULL):
    np.random.seed(s); rows.append(compare(hp.synalm(CL, lmax=LMAX), f'null_{s}'))
    if (s + 1) % 250 == 0: print(f'    null {s+1}/{N_NULL} ({time.time()-t0:.0f}s)', flush=True)
fresh_seeds = np.random.default_rng(20260903).integers(2**31 - 1, size=N_FRESH)
for i in range(N_FRESH):
    np.random.seed(int(fresh_seeds[i])); rows.append(compare(hp.synalm(CL, lmax=LMAX), f'fresh_{i}'))
    if (i + 1) % 500 == 0: print(f'    fresh {i+1}/{N_FRESH} ({time.time()-t0:.0f}s)', flush=True)
df = pd.DataFrame(rows)
df.to_csv(os.path.join(OUT, 's1_Bstack_l2_4_validation.csv'), index=False)
V = dict(n=len(df), same_axis_frac=float(df.same_axis.mean()), same_axis_f32cast_frac=float(df.same_axis_f32cast.mean()),
         n_axis_mismatch=int((~df.same_axis).sum()), sep_deg_p90=float(np.percentile(df.sep_deg, 90)),
         max_rel_Sp=float(df.max_rel_Sp.max()), max_rel_Sm=float(df.max_rel_Sm.max()),
         T1_rel_at_selected_max=float((np.abs(df.T1_bstack - df.T1_ref) / df.T1_ref).max()),
         EB_indicator_mismatch=int((df.EB_ref != df.EB_bstack).sum()),
         data_same_axis_all=bool(df[~df['sample'].str.contains('null|fresh')].same_axis.all()))
G['G_bstack_data_same_axis'] = V['data_same_axis_all']
G['G_bstack_EB_indicator'] = (V['EB_indicator_mismatch'] == 0)
G['G_bstack_quadform_equiv'] = (V['max_rel_Sp'] < 1e-5 and V['max_rel_Sm'] < 1e-5)   # float32 ref vs float64
G['G_bstack_all_same_axis'] = bool(df.same_axis.all())
G['G_bstack_f32cast_all_same_axis'] = bool(df.same_axis_f32cast.all())
assert all(G.values()), G                                                            # final all-gate assert
print('[2] validation:', {k: (f'{v:.3e}' if isinstance(v, float) else v) for k, v in V.items()}, flush=True)

# ---- 3. save ----
NPZ = os.path.join(OUT, 's1_Bstack_l2_4_N16_common_v1.npz')
np.savez_compressed(NPZ, Bp_stack=Bp, Bm_stack=Bm, axis_pixel_ids=np.arange(NPIX),
                    basis_lm=np.array([[str(l), str(m), cs] for (l, m, cs) in RB], dtype='U8'),
                    meta=np.array(json.dumps(dict(nside=NSIDE, ordering='ring', mask='common',
                                                  band=[2, 4], normalization='S = x^T B x  (mean over valid pairs, /cnt)',
                                                  dtype='float64', input_sha=INPUT_SHA))))
prov = dict(script=os.path.basename(__file__) if '__file__' in dir() else 'inline', script_sha256=SCRIPT_SHA,
            date=str(datetime.date.today()),
            scope=('map-free evaluation of the frozen l=2-4 statistic on all 3072 axes; enables S1 (l2-4-only) '
                   'selection surrogate. Historical full-band selection and S2 hybrid need a higher-dimensional stack.'),
            pem_commit='d36e7567e8a7869c0d7b84955b4139ab0e782af0', bridge_sha=BRIDGE_SHA,
            input_sha=INPUT_SHA, expected_bitlevel=EXPECTED_BITLEVEL,
            input_gate_note='bit-level gate on processed_mask, reflection_table, valid_table and cnt; '
                            'float arrays validated through the pm.scan_S comparison battery', build_seconds=T_BUILD,
            bstack_array_sha256=BSTACK_SHA, npz_sha256=sha(NPZ), gates=G, validation=V,
            validation_design='reference = pm.scan_S (historical float32 map-domain); B-stack = float64 quadratic forms; '
                              'samples = 10 maps + Step0 null seeds 0..N-1 + fresh stream default_rng(20260903)',
            versions=dict(python=sys.version.split()[0], numpy=np.__version__, healpy=hp.__version__,
                          platform=platform.platform()))
json.dump(prov, open(os.path.join(OUT, 's1_Bstack_l2_4_provenance.json'), 'w'), indent=1, ensure_ascii=False)
print('[3] saved', NPZ); print('    gates:', G)
