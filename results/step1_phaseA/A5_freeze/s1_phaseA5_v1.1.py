# -*- coding: utf-8 -*-
"""Step 1 Phase A-5: historical axis-selection reconstruction and selection-adjusted null.

Reproducible artifact generator (sandbox or Colab). Produces:
  a5_historical_axis_reproduction.csv   data-side reproduction of a1_axes.csv (N16/common, 10 maps)
  a5_data_selection_band.csv            data-side argmin vs selection band
  a5_null_selection.npz                 per-realization arrays (Step 0 seeds 0..999, design-discovery)
  a5_battery_3072_vs_1536.csv           +/- axis deduplication equivalence (data + fresh null)
  a5_battery_float32_vs_float64.csv     selection dtype equivalence (data + fresh null)
  a5_compensation_metrics.csv           selection-induced compensation diagnostics
  a5_provenance.json
Everything is computed with the frozen plane-excised-mirror sources at commit d36e7567.
"""
import os, sys, json, hashlib, time, datetime, platform, warnings
# 監査 §24.4：包括的な抑制はやめ，既知の deprecation のみ限定的に抑制する
warnings.filterwarnings('ignore', category=DeprecationWarning, module='healpy')
# 注：numpy / pandas / healpy は，下のブートストラップ（Colabでのpip install）の後にimportする。

IN_COLAB = os.path.isdir('/content')
WORK = '/content' if IN_COLAB else '/home/claude'
PEM = os.path.join(WORK, 'pem_step1' if IN_COLAB else 'pem_repo')
EXPECTED_COMMIT_STEP0_ = 'd36e7567e8a7869c0d7b84955b4139ab0e782af0'
if IN_COLAB:
    import subprocess as _sp
    # 注：drive.mount() はノートブックのカーネル内でのみ動作する（!python のサブプロセスでは不可）。
    #     既にマウント済みならそのまま使い，未マウントなら明示的に停止して手順を案内する。
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
    if not os.path.isdir(os.path.join(PEM, '.git')):
        _sp.run(['git', 'clone', 'https://github.com/tsujikeita/plane-excised-mirror.git', PEM],
                check=True, capture_output=True, env=_env)
    _sp.run(['git', '-C', PEM, 'checkout', '-q', '--force', EXPECTED_COMMIT_STEP0_], check=True)
    _CA = os.path.join(WORK, 'CMBanom')
    if not os.path.isdir(os.path.join(_CA, '.git')):
        _sp.run(['git', 'clone', 'https://github.com/LauraHerold/CMBanom.git', _CA],
                check=True, capture_output=True, env=_env)
    _sp.run(['git', '-C', _CA, 'checkout', '-q', '--force',
             'aaf8137427d54ce4c77e59734391aca491a4a8db'], check=True)
import numpy as np, pandas as pd            # noqa: E402  （ブートストラップ後にimport）
import healpy as hp                          # noqa: E402
EXPECTED_ENV = dict(numpy='2.1.3', healpy='1.20.0', python='3.13')   # formal（Colab）実行の凍結環境
ENV_OK = (np.__version__ == EXPECTED_ENV['numpy'] and hp.__version__ == EXPECTED_ENV['healpy']
          and sys.version.startswith(EXPECTED_ENV['python']))
if IN_COLAB:
    assert ENV_OK, ('環境gate FAIL', np.__version__, hp.__version__, sys.version.split()[0])
else:
    print(f'[warn] non-Colab environment: numpy {np.__version__} healpy {hp.__version__} '
          f'(formal gate requires {EXPECTED_ENV}); results are design-only', flush=True)
OUT = (os.path.join('/content/drive/MyDrive/mirror_topology', 'runs_step1_phaseA', 'a5_v1.1_official')
       if IN_COLAB else '/home/claude/colab_sim/runs_step1_phaseA/a5_v1.1_official')
PR4_DIR = '/content/drive/MyDrive/phase2_null/sources' if IN_COLAB else '/mnt/user-data/uploads'
os.makedirs(OUT, exist_ok=True)
os.chdir(WORK)                                   # phase2_core の cwd 相対パス（CMBanom/…）
sys.path.insert(0, os.path.join(PEM, 'src'))
import phase2_core as p2, plane_mirror as pm

EXPECTED_COMMIT_STEP0 = 'd36e7567e8a7869c0d7b84955b4139ab0e782af0'
def sha(p):
    with open(p, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()
SCRIPT_SHA = hashlib.sha256(open(os.path.abspath(__file__), 'rb').read()).hexdigest() \
    if '__file__' in dir() else 'inline'
def run(cmd):
    import subprocess
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
PEM_COMMIT = run(['git', '-C', PEM, 'rev-parse', 'HEAD'])
assert PEM_COMMIT == EXPECTED_COMMIT_STEP0, PEM_COMMIT
assert run(['git', '-C', PEM, 'status', '--porcelain', '--untracked-files=no']) == ''
EXPECTED_CMBANOM_COMMIT = 'aaf8137427d54ce4c77e59734391aca491a4a8db'
_CAdir = os.path.join(WORK, 'CMBanom')
CANOM_COMMIT = run(['git', '-C', _CAdir, 'rev-parse', 'HEAD'])
CANOM_ORIGIN = run(['git', '-C', _CAdir, 'remote', 'get-url', 'origin'])
G0 = {}
G0['G_cmbanom_commit'] = (CANOM_COMMIT == EXPECTED_CMBANOM_COMMIT)
G0['G_cmbanom_clean'] = (run(['git', '-C', _CAdir, 'status', '--porcelain',
                              '--untracked-files=no']) == '')
G0['G_cmbanom_origin'] = (CANOM_ORIGIN.rstrip('/').removesuffix('.git')
                          == 'https://github.com/LauraHerold/CMBanom')
G0['G_pem_origin'] = (run(['git', '-C', PEM, 'remote', 'get-url', 'origin'])
                      .rstrip('/').removesuffix('.git')
                      == 'https://github.com/tsujikeita/plane-excised-mirror')
for _k, _v in G0.items():
    assert _v, _k

LMAX = 128
NSIDE = 16
T_SRC = hp.gauss_beam(np.radians(1.0), lmax=LMAX) * p2.pixwin_pad(128, LMAX)
FL = p2.transfer(NSIDE, 'planck', LMAX)
_pwc = os.path.join(p2.PIXWIN_CACHE, f'pixel_window_n{NSIDE:04d}.fits')
PIXWIN_SOURCE = ('local_cache:' + os.path.abspath(_pwc)) if os.path.exists(_pwc) else 'healpy_download'
print('pixwin source:', PIXWIN_SOURCE, flush=True)
ELL = np.arange(LMAX + 1)
CL = p2.load_fid_cl()
def band_w(lo, hi):
    return ((ELL >= lo) & (ELL <= hi)).astype(float) * FL
W_FULL = FL.copy()
W_EVAL = band_w(2, 4)
SEL_BANDS = {'full': W_FULL, 'l32': band_w(2, 32), 'l24': band_w(2, 24),
             'l16': band_w(2, 16), 'l8': band_w(2, 8), 'l2_4': W_EVAL}

# ---- frozen pipeline objects ----
ms = pm.with_mask(p2.MirrorStat(NSIDE, p2.make_mask(NSIDE, 'full')), p2.make_mask(NSIDE, 'common'))
NPIX = hp.nside2npix(NSIDE)
assert ms.R.shape == (NPIX, NPIX)
PROC_MASK_SHA = hashlib.sha256(ms.mask.astype(np.uint8).tobytes()).hexdigest()
R_SHA = hashlib.sha256(np.ascontiguousarray(ms.R).tobytes()).hexdigest()
VALID_SHA = hashlib.sha256(np.ascontiguousarray(ms.valid).tobytes()).hexdigest()
CNT_SHA = hashlib.sha256(np.ascontiguousarray(ms.cnt).tobytes()).hexdigest()
MASK_SRC_SHA = sha(p2.COMMON_MASK_128)
CL_FILE_SHA = sha(p2.FID_CL_FILE)
CL_ARR_SHA = hashlib.sha256(np.ascontiguousarray(CL).tobytes()).hexdigest()
FL_SHA = hashlib.sha256(np.ascontiguousarray(FL).tobytes()).hexdigest()
SEL_WIN_SHA = {k: hashlib.sha256(np.ascontiguousarray(w).tobytes()).hexdigest()
               for k, w in SEL_BANDS.items()}
A1_CSV_SHA = sha(os.path.join(PEM, 'data', 'a1_axes.csv'))
# 入力の検証は2層（A4の知見：計算由来のfloat配列は環境間でbit一致しない）
#   Tier1 = bit-level（ファイル・整数/論理配列）／Tier2 = 数値許容差（float配列）
ACTUAL_BITLEVEL = dict(mask_source=MASK_SRC_SHA, cl_file=CL_FILE_SHA, a1_axes_csv=A1_CSV_SHA,
                       processed_mask=PROC_MASK_SHA, reflection_table=R_SHA,
                       valid_table=VALID_SHA, cnt=CNT_SHA)
ACTUAL_FLOAT = dict(fl=FL, cl_array=CL, **{f'selwin_{k}': w for k, w in SEL_BANDS.items()})
ACTUAL_FLOAT_SHA = {k: hashlib.sha256(np.ascontiguousarray(v).tobytes()).hexdigest()
                    for k, v in ACTUAL_FLOAT.items()}
_MANIFEST = os.environ.get('A5_INPUT_MANIFEST', 'a5_input_manifest_v2.json')
EXPECTED_INPUT = json.load(open(_MANIFEST)) if os.path.exists(_MANIFEST) else None
FLOAT_RTOL = 1e-12
if EXPECTED_INPUT is None:
    print(f'[manifest generation mode] 入力manifest ({_MANIFEST}) が指定位置にないため，'
          '現在の入力から新しいmanifestを生成します（入力gateは評価されません）。'
          f'\n  生成先: {os.path.join(OUT, "a5_actual_input_manifest.json")}'
          '\n  凍結済みの入力に対して検証したい場合は，配布されたmanifestを'
          'カレントディレクトリに置くか，環境変数 A5_INPUT_MANIFEST でパスを指定してください。', flush=True)
    json.dump(dict(schema='a5_input_manifest_v2', generated_in=('colab' if IN_COLAB else 'sandbox'),
                   pixwin_source=PIXWIN_SOURCE, numpy=np.__version__, healpy=hp.__version__,
                   bitlevel=ACTUAL_BITLEVEL,
                   float_ref={k: [float(x) for x in np.asarray(v).ravel()]
                              for k, v in ACTUAL_FLOAT.items()},
                   float_sha=ACTUAL_FLOAT_SHA, float_rtol=FLOAT_RTOL),
              open(os.path.join(OUT, 'a5_actual_input_manifest.json'), 'w'), indent=1)
    G0['G_input_bitlevel'] = None; G0['G_input_float'] = None
    if os.environ.get('A5_MANIFEST_ONLY', '') == '1':
        print('[manifest-only] manifest を生成して終了します（pixwin source: ' + PIXWIN_SOURCE + '）', flush=True)
        raise SystemExit(0)
    if IN_COLAB and os.environ.get('A5_ALLOW_NO_MANIFEST', '') != '1':
        raise SystemExit(
            '\n[停止] formal run では入力manifestが必須です。'
            f'\n  {_MANIFEST} を作業ディレクトリ（現在: {os.getcwd()}）に置いて再実行してください。'
            '\n  manifest生成モードとして意図的に走らせる場合は A5_ALLOW_NO_MANIFEST=1 を指定してください。')
else:
    assert EXPECTED_INPUT.get('schema') == 'a5_input_manifest_v2', (
        'manifest schema が古い（v2 を使ってください）', EXPECTED_INPUT.get('schema'))
    _bl = {k: (ACTUAL_BITLEVEL[k] == EXPECTED_INPUT['bitlevel'].get(k)) for k in ACTUAL_BITLEVEL}
    G0['G_input_bitlevel'] = all(_bl.values())
    # float 配列の比較基準（A4/A5 の知見）：
    #   主判定 = 配列の最大絶対値に対する相対差 max|cur-ref| / max|ref| ≤ FLOAT_RTOL
    #   （要素ごとの相対差は，ビームで 1e-15〜1e-23 に抑圧された高ℓ要素で exp 実装差により
    #    大きく見えるが，統計への寄与は無視できるため主判定に使わない。診断として記録する）
    _fl_diff = {}; _fl_diag = {}
    for k, v in ACTUAL_FLOAT.items():
        ref = np.asarray(EXPECTED_INPUT['float_ref'][k], float); cur = np.asarray(v, float).ravel()
        assert ref.shape == cur.shape, (k, ref.shape, cur.shape)
        scale = max(float(np.abs(ref).max()), np.finfo(float).tiny)
        absd = np.abs(cur - ref)
        _fl_diff[k] = float(absd.max() / scale)                      # 主判定
        i = int(absd.argmax())
        sig = np.abs(ref) > 1e-6 * scale                              # 有意要素（max の 1e-6 以上）
        elem_rel = float(np.max(absd[sig] / np.abs(ref[sig]))) if sig.any() else 0.0
        _fl_diag[k] = dict(scaled_maxdiff=_fl_diff[k], argmax_index=i, ref_at_argmax=float(ref[i]),
                           cur_at_argmax=float(cur[i]), elementwise_rel_on_significant=elem_rel)
    G0['G_input_float'] = all(d <= FLOAT_RTOL for d in _fl_diff.values())
    if not (G0['G_input_bitlevel'] and G0['G_input_float']):
        print('入力gate 内訳（bit-level）:', json.dumps(_bl, ensure_ascii=False), flush=True)
        print('入力gate 内訳（float：max|cur−ref|/max|ref|）:',
              json.dumps({k: f'{d:.3e}' for k, d in _fl_diff.items()}, ensure_ascii=False), flush=True)
        for k, dg in _fl_diag.items():
            if dg['scaled_maxdiff'] > FLOAT_RTOL:
                print(f"    {k}: 最大差の位置 index={dg['argmax_index']} ref={dg['ref_at_argmax']:.6e} "
                      f"cur={dg['cur_at_argmax']:.6e}", flush=True)
        print(f'  float許容差 rtol={FLOAT_RTOL:.0e}（配列最大値に対する相対）', flush=True)
    assert G0['G_input_bitlevel'], '入力gate FAIL（bit-level：ファイル/整数/論理配列）'
    assert G0['G_input_float'], '入力gate FAIL（float：許容差超過）'
    FLOAT_MAXDIFF = _fl_diag
EXPECTED_MAP_SHA = {
 'PR3_Commander': '2f88c2d385e3c96a8ead4d98254e8b92ad4f460c58810697ad61132f2ff0020b',
 'PR3_NILC': '63f3b41ea5a0e934d2d425ccb7c51b12539e4fb147e75e18a92e18e003bee352',
 'PR3_SEVEM': 'c395a7fcf955560a62d7b8404eb3ff19e868d6c03c0ad83dbf99571951e12ab9',
 'PR3_SMICA': '1fda86de628c43820e999ad1564960cb5350c972c7f820b4132d6c6d149a8272',
 'Nofi_70GHz': 'bac5d05118d1044c07910283a31e20d712a5f55190a3258e12c6c53fc1cc2665',
 'Nofi_94GHz': '6a24e2867e4f4aefd4f2cff7e0b591912f8f4690e5cccb24cec99f95c2047266',
 'Nofi_100GHz': 'b30cb4cacb104ca1e705c320f9f4b867c0a03e4130248cca54f007a57e87b867',
 'Nofi_143GHz': 'ad95a5135470d3f297267d75c5323ad30aaf454d1bf0f8a1aae076142ba0c6eb',
 'PR4_Sevem': '94b6647a220590e82162786c02a10a81d6e4421cc3949e247cdd4486cf280a1e',
 'PR4_Commander': 'e9dfe38bc25d7ba22294161ffa709c1fc11914a3019eb1deaf3ed0e646dae40a'}
VEC = np.array(hp.pix2vec(NSIDE, np.arange(NPIX))).T
ANTIPODE = hp.vec2pix(NSIDE, -VEC[:, 0], -VEC[:, 1], -VEC[:, 2])
DEDUP = np.where(np.arange(NPIX) < ANTIPODE)[0]           # pixel_id < antipode_id
assert len(DEDUP) == NPIX // 2 and (ANTIPODE[ANTIPODE] == np.arange(NPIX)).all()

def prep(mp, mondip=True):
    if mondip:
        mp = np.asarray(hp.remove_dipole(hp.ma(np.where(ms.mask, mp, hp.UNSEEN))))
    return np.where(ms.mask, mp, 0.0)

def scan_all(T, dtype=np.float32):
    """Per-axis loop identical in arithmetic to pm.scan_S (verified: max|diff|=0, same argmin);
    dtype selectable for the float32/float64 battery. T must already be prep()'d."""
    T = T.astype(dtype)
    nd = ms.R.shape[0]
    Sp = np.empty(nd, dtype); Sm = np.empty(nd, dtype)
    half = dtype(0.5)
    for d in range(nd):
        v = ms.valid[d]; Tr = T[ms.R[d]]
        Sp[d] = np.sum(v * (half * (T + Tr)) ** 2) / ms.cnt[d]
        Sm[d] = np.sum(v * (half * (T - Tr)) ** 2) / ms.cnt[d]
    return Sp, Sm

def argmin_rule(Sp):
    """Historical rule: np.argmin over all 3072 axes (first occurrence on ties)."""
    return int(np.argmin(Sp))

def sky_from_alm(alm, w):
    return hp.alm2map(hp.almxfl(alm.copy(), w), NSIDE)

prov = dict(script=os.path.basename(__file__) if '__file__' in dir() else 'inline',
            date=str(datetime.date.today()), formal_env_gate=bool(ENV_OK), expected_env=EXPECTED_ENV,
            pem=dict(commit=PEM_COMMIT, src_sha={f: sha(os.path.join(PEM, f)) for f in
                                               ['src/plane_mirror.py', 'src/phase2_core.py']}),
            cmbanom_commit=CANOM_COMMIT, nside=NSIDE, lmax=LMAX, mask='common',
            processed_mask_sha256=PROC_MASK_SHA, reflection_table_sha256=R_SHA,
            axis_grid=dict(n_axes=NPIX, dedup_rule='pixel_id < antipode_id', n_dedup=len(DEDUP)),
            argmin_rule='np.argmin over 3072 axes (first occurrence)', selection_dtype='float32',
            evaluation_band=[2, 4], selection_bands={k: (int(np.nonzero(w)[0].min()), int(np.nonzero(w)[0].max()))
                                                     for k, w in SEL_BANDS.items()},
            versions=dict(python=sys.version.split()[0], numpy=np.__version__, healpy=hp.__version__,
                          platform=platform.platform()))
t_all = time.time()

# ======================================================================
# 1. data-side reproduction of a1_axes.csv (N16/common) and selection-band dependence
# ======================================================================
cm = {'PR3_Commander': 'commander', 'PR3_NILC': 'nilc', 'PR3_SEVEM': 'sevem', 'PR3_SMICA': 'smica',
      'Nofi_70GHz': 'cleaned_70GHz_v9', 'Nofi_94GHz': 'cleaned_94GHz_v9',
      'Nofi_100GHz': 'cleaned_100GHz_v9', 'Nofi_143GHz': 'cleaned_143GHz_v9'}
PATHS = {k: f'CMBanom/data/real/map_{v}_nside_128.fits' for k, v in cm.items()}
for m in ['sevem', 'commander']:
    p = os.path.join(PR4_DIR, f'npipe_{m}_128.fits')
    if os.path.exists(p): PATHS[f'PR4_{m.capitalize()}'] = p
MAP_SHA = {k: sha(p) for k, p in PATHS.items()}
G0['G_maps_sha_all_known'] = (set(MAP_SHA) == set(EXPECTED_MAP_SHA))
G0['G_maps_sha_match'] = all(MAP_SHA[k] == EXPECTED_MAP_SHA[k] for k in MAP_SHA)
assert G0['G_maps_sha_all_known'] and G0['G_maps_sha_match'], MAP_SHA
DATA_ALM = {k: hp.almxfl(hp.map2alm(hp.read_map(p), lmax=LMAX), 1.0 / np.maximum(T_SRC, 1e-12))
            for k, p in PATHS.items()}
ref = pd.read_csv(os.path.join(PEM, 'data', 'a1_axes.csv'))
ref = ref[(ref.nside == NSIDE) & (ref['mask'] == 'common')].set_index('map')

rows = []; band_rows = []
for name, alm in DATA_ALM.items():
    T = prep(sky_from_alm(alm, W_FULL))
    Sp_h, Sm_h = pm.scan_S(ms, sky_from_alm(alm, W_FULL))          # historical function, verbatim
    Sp_v, Sm_v = scan_all(T)                                          # vectorised equivalent
    d = argmin_rule(Sp_h); l, b = pm.axis_lb(NSIDE, d)
    r = dict(map=name, axis_pix=d, l=l, b=b, S_min=float(Sp_h.min()), S_med=float(np.median(Sp_h)),
             width5=float((Sp_h < 1.05 * Sp_h.min()).mean()),
             vectorised_max_absdiff=float(np.abs(Sp_h - Sp_v).max()),
             vectorised_argmin_same=bool(argmin_rule(Sp_v) == d))
    if name in ref.index:
        q = ref.loc[name]
        r.update(axis_pix_ref=int(q.axis_pix), S_min_ref=float(q.S_min), S_med_ref=float(q.S_med),
                 width5_ref=float(q.width5),
                 rel_S_min=abs(r['S_min'] - q.S_min) / q.S_min, rel_S_med=abs(r['S_med'] - q.S_med) / q.S_med)
    rows.append(r)
    for bname, w in SEL_BANDS.items():
        Sp, _ = scan_all(prep(sky_from_alm(alm, w)))
        a = argmin_rule(Sp)
        band_rows.append(dict(map=name, selection_band=bname, axis_pix=a,
                              sep_from_1134_deg=pm.axis_sep_deg(NSIDE, 1134, a),
                              S_min=float(Sp.min()), S_at_1134=float(Sp[1134])))
df_rep = pd.DataFrame(rows); df_band = pd.DataFrame(band_rows)
# consensus rule (PR3 x N16/common unit-vector mean, +/- identified)
sel = df_rep[df_rep['map'].str.startswith('PR3')]
v0 = VEC[int(sel.axis_pix.iloc[0])]
vc = np.mean([VEC[int(a)] if VEC[int(a)] @ v0 >= 0 else -VEC[int(a)] for a in sel.axis_pix], axis=0)
vc /= np.linalg.norm(vc); CONSENSUS = int(hp.vec2pix(NSIDE, *vc))
df_rep.to_csv(os.path.join(OUT, 'a5_historical_axis_reproduction.csv'), index=False)
df_band.to_csv(os.path.join(OUT, 'a5_data_selection_band.csv'), index=False)
ok8 = df_rep.dropna(subset=['axis_pix_ref'])
G = {}
G['G_a5_axes_reproduced'] = bool((ok8.axis_pix == ok8.axis_pix_ref).all())
G['G_a5_values_reproduced'] = bool(ok8.rel_S_min.max() < 1e-6 and ok8.rel_S_med.max() < 1e-6)
G['G_a5_consensus_1134'] = (CONSENSUS == 1134)
G['G_a5_vectorised_scan_equiv'] = bool(df_rep.vectorised_argmin_same.all()
                                       and df_rep.vectorised_max_absdiff.max() < 1e-3)
print(f'[1] data-side reproduction done ({time.time()-t_all:.0f}s): consensus={CONSENSUS}', G)

# ======================================================================
# 2. null (Step 0 seeds 0..999) : per-realization selection under several bands
#    NOTE: design-discovery sample; official probabilities use a fresh independent stream.
# ======================================================================
N0 = int(os.environ.get('A5_N0', '1000'))
keys = ['seed'] + [f'axis_{b}' for b in SEL_BANDS] + ['T1_fixed', 'T2_fixed'] + \
       [f'T1_{b}' for b in SEL_BANDS] + [f'T2_{b}' for b in SEL_BANDS] + \
       ['tot_cv_axis', 'tot_maxmin_axis', 'corr_axis_T1T2']
CKPT2 = os.path.join(OUT, 'a5_null_selection_ckpt.npz')
BINDING = dict(script_sha256=SCRIPT_SHA, pem_commit=PEM_COMMIT, cmbanom_commit=CANOM_COMMIT,
               map_sha=MAP_SHA, cl_arr_sha=ACTUAL_FLOAT_SHA['cl_array'], mask_src_sha=MASK_SRC_SHA,
               proc_mask_sha=PROC_MASK_SHA, R_sha=R_SHA, fl_sha=ACTUAL_FLOAT_SHA['fl'],
               sel_windows={k: ACTUAL_FLOAT_SHA[f'selwin_{k}'] for k in SEL_BANDS}, dtype='float32', n_axes=int(NPIX),
               seed_recipe='np.random.seed(s); hp.synalm(fid_cl, lmax=128)')
BIND_SHA = hashlib.sha256(json.dumps(BINDING, sort_keys=True).encode()).hexdigest()
rec = {k: [] for k in keys}
if os.path.exists(CKPT2):
    _z = np.load(CKPT2, allow_pickle=True)
    _prev = str(_z['binding_sha']) if 'binding_sha' in _z.files else ''
    assert _prev == BIND_SHA, ('checkpoint binding不一致：resume禁止', _prev, BIND_SHA)
    rec = {k: list(_z[k]) for k in keys}
    _L = {len(v) for v in rec.values()}
    assert len(_L) == 1, ('checkpoint配列長不一致', _L)
    assert list(rec['seed']) == list(range(len(rec['seed']))) and len(rec['seed']) <= N0, 'checkpoint seed列不正'
START = len(rec['seed']); STAGE_BUDGET = float(os.environ.get('A5_BUDGET_S', '99999' if IN_COLAB else '420'))
t0 = time.time()
for s in range(START, N0):
    if time.time() - t0 > STAGE_BUDGET:
        np.savez_compressed(CKPT2, binding_sha=np.array(BIND_SHA),
                            **{k: np.array(v) for k, v in rec.items()})
        print(f'    [checkpoint] null {len(rec["seed"])}/{N0} saved; rerun to continue'); sys.exit(0)
    np.random.seed(s); alm = hp.synalm(CL, lmax=LMAX)
    Sp_e, Sm_e = scan_all(prep(sky_from_alm(alm, W_EVAL)))     # evaluation band l2-4, all axes
    rec['seed'].append(s)
    rec['T1_fixed'].append(float(Sp_e[1134])); rec['T2_fixed'].append(float(Sm_e[1134]))
    for b, w in SEL_BANDS.items():
        Sp_s, _ = (Sp_e, None) if b == 'l2_4' else scan_all(prep(sky_from_alm(alm, w)))
        a = argmin_rule(Sp_s)
        rec[f'axis_{b}'].append(a); rec[f'T1_{b}'].append(float(Sp_e[a])); rec[f'T2_{b}'].append(float(Sm_e[a]))
    tot = (Sp_e + Sm_e).astype(np.float64)
    rec['tot_cv_axis'].append(float(tot.std() / tot.mean()))
    rec['tot_maxmin_axis'].append(float(tot.max() / tot.min()))
    rec['corr_axis_T1T2'].append(float(np.corrcoef(Sp_e.astype(np.float64), Sm_e.astype(np.float64))[0, 1]))
    if (s + 1) % 100 == 0: print(f'    null {s+1}/{N0} ({time.time()-t0:.0f}s)', flush=True)
NULL = {k: np.array(v) for k, v in rec.items()}
np.savez_compressed(CKPT2, binding_sha=np.array(BIND_SHA), **NULL)
np.savez_compressed(os.path.join(OUT, 'a5_null_selection.npz'), **NULL)
print(f'[2] null selection done ({time.time()-t0:.0f}s)')
T1o, T2o = 39.67178834527284, 259.3375006282747
summ = {}
for b in ['fixed'] + list(SEL_BANDS):
    t1, t2 = NULL[f'T1_{b}'], NULL[f'T2_{b}']
    summ[b] = dict(T1_med=float(np.median(t1)), P_T1_le_obs=float(np.mean(t1 <= T1o)),
                   n_T1_le_obs=int(np.sum(t1 <= T1o)),
                   T2_med=float(np.median(t2)), T2_q16=float(np.quantile(t2, .16)), T2_q84=float(np.quantile(t2, .84)),
                   P_T2_le_obs=float(np.mean(t2 <= T2o)),
                   P_EB=float(np.mean((t1 <= T1o) & (t2 <= T2o))), n_EB=int(np.sum((t1 <= T1o) & (t2 <= T2o))),
                   rho_med=float(np.median((t1 - t2) / (t1 + t2))))
comp = dict(tot_cv_axis_median=float(np.median(NULL['tot_cv_axis'])),
            tot_maxmin_axis_median=float(np.median(NULL['tot_maxmin_axis'])),
            corr_axis_T1T2_median=float(np.median(NULL['corr_axis_T1T2'])))
pd.DataFrame([dict(metric=k, value=v) for k, v in comp.items()]).to_csv(
    os.path.join(OUT, 'a5_compensation_metrics.csv'), index=False)
agree = {b: float(np.mean(NULL[f'axis_{b}'] == NULL['axis_full'])) for b in SEL_BANDS if b != 'full'}
sepmed = {b: float(np.median([pm.axis_sep_deg(NSIDE, int(x), int(y))
                              for x, y in zip(NULL['axis_full'], NULL[f'axis_{b}'])]))
          for b in SEL_BANDS if b != 'full'}

# ======================================================================
# 3. batteries: 3072 vs 1536 dedup, float32 vs float64 (data + fresh null, independent stream)
# ======================================================================
N_FRESH = int(os.environ.get('A5_NFRESH', '2000'))
rng_fresh = np.random.default_rng(20260902)
CKPT3 = os.path.join(OUT, 'a5_battery_ckpt.json')
b_rows = []; f_rows = []; done_fresh = 0
N_DATA = len(DATA_ALM)
if os.path.exists(CKPT3):
    _c = json.load(open(CKPT3))
    assert _c.get('binding_sha') == BIND_SHA, ('battery checkpoint binding不一致：resume禁止')
    b_rows, f_rows, done_fresh = _c['b'], _c['f'], _c['done_fresh']
    assert len(b_rows) == len(f_rows) == N_DATA + done_fresh and 0 <= done_fresh <= N_FRESH
    _lab = [r['sample'] for r in f_rows]
    assert len(set(_lab)) == len(_lab), 'duplicate sample labels'
    assert _lab[N_DATA:] == [f'fresh_{i}' for i in range(done_fresh)], 'fresh label列不正'
def battery_on(alm, label):
    Tf = prep(sky_from_alm(alm, W_FULL))
    Sp32, _ = scan_all(Tf, np.float32); Sp64, _ = scan_all(Tf, np.float64)
    a32 = argmin_rule(Sp32); a64 = argmin_rule(Sp64)
    # dedup: restrict argmin to DEDUP set; compare plane (a or antipode)
    a32_d = int(DEDUP[np.argmin(Sp32[DEDUP])])
    same_plane = (a32_d == a32) or (a32_d == ANTIPODE[a32])
    b_rows.append(dict(sample=label, axis_3072=int(a32), axis_1536=int(a32_d), antipode_of_3072=int(ANTIPODE[a32]),
                       same_plane=bool(same_plane), Sp_diff_axis_vs_antipode=float(abs(Sp32[a32] - Sp32[ANTIPODE[a32]])),
                       S_min_3072=float(Sp32[a32]), S_min_1536=float(Sp32[a32_d])))
    f_rows.append(dict(sample=label, axis_f32=int(a32), axis_f64=int(a64), same_axis=bool(a32 == a64),
                       same_plane=bool((a32 == a64) or (a64 == ANTIPODE[a32])),
                       sep_deg=float(pm.axis_sep_deg(NSIDE, a32, a64)), Smin_f32=float(Sp32[a32]), Smin_f64=float(Sp64[a64])))
if done_fresh == 0 and not b_rows:
    for name, alm in DATA_ALM.items(): battery_on(alm, name)
t0 = time.time()
fresh_seeds = rng_fresh.integers(2**31 - 1, size=N_FRESH)      # 決定論的な独立stream（再開しても同一）
for i in range(done_fresh, N_FRESH):
    if time.time() - t0 > STAGE_BUDGET:
        json.dump(dict(binding_sha=BIND_SHA, b=b_rows, f=f_rows, done_fresh=i), open(CKPT3, 'w'))
        print(f'    [checkpoint] battery {i}/{N_FRESH} saved; rerun to continue'); sys.exit(0)
    np.random.seed(int(fresh_seeds[i]))
    battery_on(hp.synalm(CL, lmax=LMAX), f'fresh_{i}')
    if (i + 1) % 200 == 0: print(f'    battery {i+1}/{N_FRESH} ({time.time()-t0:.0f}s)', flush=True)
df_b = pd.DataFrame(b_rows); df_f = pd.DataFrame(f_rows)
df_b.to_csv(os.path.join(OUT, 'a5_battery_3072_vs_1536.csv'), index=False)
df_f.to_csv(os.path.join(OUT, 'a5_battery_float32_vs_float64.csv'), index=False)
G['G_a5_dedup_same_plane'] = bool(df_b.same_plane.all())
G['G_a5_f32_f64_same_plane_data'] = bool(df_f[~df_f['sample'].str.startswith('fresh')].same_plane.all())
f_null = df_f[df_f['sample'].str.startswith('fresh')]
print(f'[3] batteries done ({time.time()-t0:.0f}s)')

# ======================================================================
# 3b. antipodal reflection diagnostic (audit 25)
# ======================================================================
_diff = np.array([int(np.sum(ms.R[i] != ms.R[ANTIPODE[i]])) for i in range(NPIX)])
_pairs = sorted({(int(min(i, ANTIPODE[i])), int(max(i, ANTIPODE[i])))
                 for i in np.nonzero(_diff)[0]})
pd.DataFrame(dict(axis_a=[a for a, _ in _pairs], axis_b=[b for _, b in _pairs],
                  n_pixel_mismatch=[int(_diff[a]) for a, _ in _pairs])).to_csv(
    os.path.join(OUT, 'a5_antipodal_reflection_diagnostic.csv'), index=False)
ANTI_DIAG = dict(n_antipodal_R_rows_different=int((_diff > 0).sum()),
                 max_antipodal_R_pixel_mismatches=int(_diff.max()),
                 n_mismatching_axis_pairs=len(_pairs),
                 axis_antipode_Sp_max_diff=float(df_b.Sp_diff_axis_vs_antipode.max()),
                 pairs_sha256=hashlib.sha256(json.dumps(_pairs).encode()).hexdigest())
print('[3b] antipodal diagnostic:', ANTI_DIAG)

# ======================================================================
# 4. provenance
# ======================================================================
G.update(G0)
G['G_dedup_battery_completed'] = True          # 監査 §15：gate と診断フラグを分離
dedup_equivalent = bool(G.pop('G_a5_dedup_same_plane'))
FLAGS = dict(F_dedup_equivalent=dedup_equivalent,
             F_historical_3072_selected=True, F_selection_dtype_primary='float32')
prov.update(maps=MAP_SHA, expected_maps=EXPECTED_MAP_SHA, consensus_axis=CONSENSUS,
            gates=G, flags=FLAGS, script_sha256=SCRIPT_SHA,
            script_origin='https://github.com/tsujikeita/mirror-topology (Step 1 Phase A)',
            cmbanom_origin=CANOM_ORIGIN, antipodal_diagnostic=ANTI_DIAG,
            input_bitlevel_sha=ACTUAL_BITLEVEL, input_float_sha=ACTUAL_FLOAT_SHA, pixwin_source=PIXWIN_SOURCE,
            manifest_generated_in=(EXPECTED_INPUT.get('generated_in') if EXPECTED_INPUT else None),
            input_float_maxdiff=(FLOAT_MAXDIFF if EXPECTED_INPUT is not None else None),
            input_float_rtol=FLOAT_RTOL, input_manifest=os.path.basename(_MANIFEST),
            input_gate_note=('bit-level = files and integer/boolean arrays; float arrays (fl, cl, selection '
                             'windows) are compared by max|cur-ref|/max|ref| <= rtol because they are computed '
                             'and are not bit-identical across environments; elementwise relative differences '
                             'on beam-suppressed high-l entries (~1e-15..1e-23) are recorded as diagnostics only'),
            note_T_arrays='values are float32-derived (stored in float64 containers)',
            checkpoint_binding_sha=BIND_SHA,
            null=dict(n=N0, seed_recipe='np.random.seed(s); hp.synalm(fid_cl, lmax=128), s=0..N-1 (Step 0 seeds)',
                      status='design-discovery sample; official probabilities require fresh stream',
                      summary=summ, axis_agreement_with_full=agree, axis_sep_median_deg=sepmed,
                      compensation=comp),
            battery=dict(fresh_n=N_FRESH, fresh_seed_stream='default_rng(20260902) -> np.random.seed per draw',
                         dedup_same_plane_all=dedup_equivalent,
                         dedup_max_Sp_axis_vs_antipode=float(df_b.Sp_diff_axis_vs_antipode.max()),
                         f32_f64_same_axis_frac_null=float(f_null.same_axis.mean()),
                         f32_f64_same_plane_frac_null=float(f_null.same_plane.mean()),
                         f32_f64_sep_deg_p90_null=float(np.percentile(f_null.sep_deg, 90)),
                         f32_f64_same_plane_data=G['G_a5_f32_f64_same_plane_data']),
            consensus_rule_in_simulation='signal-only equivalent (single latent sky argmin; '
                                         'no correlated component-separation ensemble)',
            outputs={f: sha(os.path.join(OUT, f)) for f in
                     ['a5_historical_axis_reproduction.csv', 'a5_data_selection_band.csv',
                      'a5_null_selection.npz', 'a5_battery_3072_vs_1536.csv',
                      'a5_battery_float32_vs_float64.csv', 'a5_compensation_metrics.csv',
                      'a5_antipodal_reflection_diagnostic.csv']},
            elapsed_s=float(time.time() - t_all))
json.dump(prov, open(os.path.join(OUT, 'a5_provenance.json'), 'w'), indent=1, ensure_ascii=False)
print('\n=== SUMMARY ===')
print('gates:', G)
for b, v in summ.items():
    print(f"  {b:6s} T1med={v['T1_med']:6.1f} P(T1<=obs)={v['P_T1_le_obs']:.4f} ({v['n_T1_le_obs']})  "
          f"T2med={v['T2_med']:6.1f} q16/84=({v['T2_q16']:.0f},{v['T2_q84']:.0f})  P(E_B)={v['P_EB']:.4f} ({v['n_EB']})")
print('axis agreement w/ full:', {k: round(v, 3) for k, v in agree.items()})
print('compensation:', {k: round(v, 3) for k, v in comp.items()})
print('dedup same plane (all):', dedup_equivalent, '| f32/f64 same-plane frac (fresh null):',
      round(float(f_null.same_plane.mean()), 4), '| p90 sep', round(float(np.percentile(f_null.sep_deg, 90)), 2), 'deg')
print('elapsed', round(time.time() - t_all), 's')
