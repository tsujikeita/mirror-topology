"""t2b2_run v1.4 (2026-08-26e): committed analysis logic for the T2b-2 production grid.

Purpose (final pre-production review sec.4): all analysis-relevant logic (grid definition,
runner, extrapolation, refine, R2' adjacency, completion check, Git preregistration gate)
lives in this committed module, so HEAD-byte verification of {t2b2_core.py, t2b2_bridge.py,
t2b2_run.py, rules v0.3} covers the analysis; the notebook is a thin driver.

Git gate (sec.2-3): HEAD is the source of truth. Tracked-file discovery uses `git ls-files`
(never filesystem glob), content comparison uses `git show HEAD:<path>` bytes. The gate is
read-only (no pull). Untracked files therefore cannot produce a false PASS.

R2' adjacency (sec.9): S5aniso is a set of discrete anisotropic cells, not an ordered sweep;
it is excluded from adjacency and treated as isolated-candidate family (implementation freeze).

v1.1 additions (NotebookIdentity final review): head_gate records origin URL and verifies the
HEAD commit is pushed to the canonical public remote (read-only `git ls-remote`); frozen
candidate-level V7 cross-check procedure `v7_crosscheck` (existing V7 real-space validation
applied verbatim to a candidate geometry/sector; method fixed before any candidate is seen).

v1.2 (ProductionGO review sec.11, optional hardening): run_jobs skips already-done keys
per transfer tag (no duplicate rows on partial-interruption resume); completion_check counts
duplicate keys and requires zero.

v1.3 (Colab operational fix): (a) the executing notebook is written to by the host (output
autosave), so the tracked-clean test ignores the notebook path itself -- its analysis-relevant
content is verified far more strictly by the source-only SHA against HEAD; every other tracked
path must still be clean. (b) notebook identity now prefers the LIVE notebook source obtained
from the host kernel (Colab `get_ipynb`), which also covers unsaved in-browser edits; the
on-disk file is the fallback. (c) `nb_source_diff` reports where a mismatch occurs.

v1.4 (canonicalisation fix): notebook editors normalise whitespace on save (Colab strips
trailing spaces), which made a byte-identical analysis look modified. The canonical form for
source_only_sha now strips CR, trailing whitespace per line, and trailing blank lines, so the
identity check is invariant under editor whitespace normalisation while still catching every
change of actual content.
"""
import os, json, csv, time, hashlib, subprocess
import numpy as np
import pandas as pd

DSMAX = 183.4   # LCDM frozen-null based conservative mean-budget diagnostic (rules v0.3 sec.3.5)
R2_EXCLUDE_FAMILIES = ('S5aniso',)


# ---------------- grid ----------------
def build_grid(subset='full'):
    SECTORS = [(1,-1,1),(1,1,-1),(1,-1,-1),(-1,1,1),(-1,-1,1),(-1,1,-1),(-1,-1,-1)]
    KCUTS = [18.0, 22.0, 26.0, 30.0, 34.0]
    BAND = (2, 3, 4)
    GEOMS = []
    def _add(family, xval, LAx, L1y, L2z, LAy):
        GEOMS.append(dict(name=f'{family}_x{xval:g}', family=family, xval=float(xval),
                          LAx=float(LAx), L1y=float(L1y), L2z=float(L2z), LAy=float(LAy)))
    for sc in [0.75, 1.0, 1.25, 1.5]:
        _add('S1scale', sc, 0.6*sc, 1.2*sc, 1.2*sc, 0.0)
    for v in [0.3, 0.45, 0.6, 0.75, 0.9]:
        _add('S2LAx', v, v, 1.2, 1.2, 0.0)
    for v in [0.6, 0.8, 1.0, 1.2, 1.4]:
        _add('S3L1y', v, 0.6, v, 1.2, 0.0)
    for f in [0.125, 0.25, 0.375, 0.5]:
        _add('S4G1f', f, 0.6, 1.2, 1.2, f*1.2)
        _add('S4G2f', f, 0.6, 0.7, 1.2, f*0.7)
    for i, (a, b, c) in enumerate([(0.6,1.2,0.6), (0.6,0.6,1.2), (0.9,0.7,1.2)]):
        _add('S5aniso', i, a, b, c, 0.0)
    if subset == 'smoke':
        GEOMS = GEOMS[:2]; SECTORS = SECTORS[:2]; KCUTS = [10.0, 12.0, 14.0, 16.0]
    else:
        fam = {}
        for g in GEOMS:
            fam[g['family']] = fam.get(g['family'], 0) + 1
        assert len(GEOMS) == 25 and fam == dict(S1scale=4, S2LAx=5, S3L1y=5,
                                                S4G1f=4, S4G2f=4, S5aniso=3), \
            f'正式grid=25幾何と不一致: {fam}'
    return GEOMS, SECTORS, KCUTS, BAND


def grid_sha(GEOMS, SECTORS, KCUTS, BAND):
    return hashlib.sha256(json.dumps(dict(GEOMS=GEOMS, SECTORS=SECTORS, KCUTS=KCUTS,
                                          BAND=list(BAND)), sort_keys=True).encode()).hexdigest()


# ---------------- Git preregistration gate (HEAD-based, read-only) ----------------
def canon_source(src):
    """Canonical cell source: CR removed, per-line trailing whitespace stripped, trailing
    blank lines removed (invariant under editor whitespace normalisation)."""
    text = ''.join(src) if not isinstance(src, str) else src
    lines = [ln.rstrip() for ln in text.replace('\r\n', '\n').replace('\r', '\n').split('\n')]
    while lines and lines[-1] == '':
        lines.pop()
    return '\n'.join(lines)


def source_only_sha(nb_bytes):
    nb = json.loads(nb_bytes.decode('utf-8'))
    canon = [dict(cell_type=c['cell_type'], source=canon_source(c['source']))
             for c in nb.get('cells', [])]
    return hashlib.sha256(json.dumps(canon, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _git(repo, *args):
    return subprocess.run(['git', '-C', repo] + list(args), capture_output=True)


def live_notebook_source_sha():
    """source-only SHA of the notebook the kernel is actually executing (Colab host request).
    Returns None outside Colab or if the host does not answer."""
    try:
        from google.colab import _message
        nb = _message.blocking_request('get_ipynb', timeout_sec=60)['ipynb']
        return source_only_sha(json.dumps(nb).encode('utf-8'))
    except Exception:
        return None


def nb_source_diff(head_bytes, local_bytes):
    """Where do two notebooks differ in source? (for actionable gate errors)"""
    def cells(b):
        return [(c['cell_type'], canon_source(c['source']))
                for c in json.loads(b.decode('utf-8'))['cells']]
    a, b = cells(head_bytes), cells(local_bytes)
    out = dict(n_cells_head=len(a), n_cells_local=len(b), first_diff=None)
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            out['first_diff'] = dict(index=i, head_head=a[i][1][:80], local_head=b[i][1][:80])
            break
    if out['first_diff'] is None and len(a) != len(b):
        extra = (b[len(a):] if len(b) > len(a) else a[len(b):])
        out['first_diff'] = dict(index=min(len(a), len(b)), extra_cell_head=extra[0][1][:80],
                                 side='local' if len(b) > len(a) else 'head')
    return out


def head_gate(repo_dir, local_files, rules_basename, rules_sha_expected,
              notebook_basename=None, notebook_local_path=None, canonical_url=None,
              nb_live_src_sha=None):
    """local_files: {basename: local_path} to verify against HEAD bytes.
    Returns dict; ok=True only if tracked-clean AND every file is tracked in HEAD with
    byte-identical content AND the rules file in HEAD has the exact expected SHA256
    (AND, when notebook_local_path is given, its source-only SHA equals HEAD's)."""
    G = dict(ok=False, commit=None, tracked_clean=None, tracked_clean_strict=None,
             dirty_paths=[], matches={}, rules_ok=False,
             rules_relpath=None, nb_relpath=None, nb_src_sha_head=None, nb_local_match=None,
             nb_live_src_sha=nb_live_src_sha, nb_live_match=None, nb_identity_ok=False,
             nb_diff=None, origin_url=None, origin_ok=None, pushed=None)
    r = _git(repo_dir, 'rev-parse', 'HEAD')
    if r.returncode != 0:
        G['error'] = 'not a git repo'
        return G
    G['commit'] = r.stdout.decode().strip()
    ru = _git(repo_dir, 'remote', 'get-url', 'origin')
    if ru.returncode == 0:
        G['origin_url'] = ru.stdout.decode().strip()
    if canonical_url is not None:
        def _norm(u):
            return (u or '').strip().rstrip('/').removesuffix('.git')
        G['origin_ok'] = bool(G['origin_url'] and _norm(G['origin_url']) == _norm(canonical_url))
        lr = _git(repo_dir, 'ls-remote', 'origin')     # read-only network query
        if lr.returncode == 0:
            remote_shas = {ln.split('\t')[0] for ln in lr.stdout.decode().splitlines() if ln}
            G['pushed'] = bool(G['commit'] in remote_shas)
        else:
            G['pushed'] = None
    tracked = _git(repo_dir, 'ls-files').stdout.decode().splitlines()
    def _rel(basename):
        hits = [p for p in tracked if os.path.basename(p) == basename]
        return hits[0] if len(hits) == 1 else None
    def _head_bytes(relpath):
        rr = _git(repo_dir, 'show', f'HEAD:{relpath}')
        return rr.stdout if rr.returncode == 0 else None
    nb_rel_for_clean = _rel(notebook_basename) if notebook_basename else None
    st = [ln for ln in _git(repo_dir, 'status', '--porcelain', '--untracked-files=no')
          .stdout.decode().splitlines() if ln.strip()]
    G['dirty_paths'] = [ln[3:].strip().strip('"').split(' -> ')[-1] for ln in st]
    G['tracked_clean_strict'] = (len(G['dirty_paths']) == 0)
    # 実行中notebookはホストが出力を書き戻すため清潔性判定から除外（内容はsource-only SHAで厳密照合）
    G['tracked_clean'] = all(p == nb_rel_for_clean for p in G['dirty_paths'])
    for base, lpath in local_files.items():
        rel = _rel(base)
        hb = _head_bytes(rel) if rel else None
        G['matches'][base] = bool(hb is not None and os.path.exists(lpath)
                                  and hashlib.sha256(hb).hexdigest()
                                  == hashlib.sha256(open(lpath, 'rb').read()).hexdigest())
    rel = _rel(rules_basename)
    G['rules_relpath'] = rel
    if rel:
        hb = _head_bytes(rel)
        G['rules_ok'] = bool(hb is not None
                             and hashlib.sha256(hb).hexdigest() == rules_sha_expected)
    if notebook_basename:
        rel = _rel(notebook_basename)
        G['nb_relpath'] = rel
        hb = _head_bytes(rel) if rel else None
        if hb is not None:
            try:
                G['nb_src_sha_head'] = source_only_sha(hb)
            except Exception:
                G['nb_src_sha_head'] = None
        if G['nb_src_sha_head']:
            if nb_live_src_sha:
                G['nb_live_match'] = (nb_live_src_sha == G['nb_src_sha_head'])
            if notebook_local_path and os.path.exists(notebook_local_path):
                lb = open(notebook_local_path, 'rb').read()
                G['nb_local_match'] = (source_only_sha(lb) == G['nb_src_sha_head'])
                if G['nb_local_match'] is False and hb is not None:
                    try:
                        G['nb_diff'] = nb_source_diff(hb, lb)
                    except Exception:
                        pass
        # live照合が得られればそれを採用（未保存編集も検出）／無ければディスク照合
        G['nb_identity_ok'] = bool(G['nb_live_match'] if G['nb_live_match'] is not None
                                   else G['nb_local_match'])
    G['ok'] = bool(G['tracked_clean'] and all(G['matches'].values()) and G['rules_ok']
                   and (G['nb_identity_ok'] if notebook_basename else True))
    return G


def gate_selftest(workdir, files):
    """Positive/negative self-test of head_gate (review sec.2.1/sec.7 mechanism check).
    (a) untracked-only repo must FAIL (regression for the false-pass path);
    (b) properly committed repo must PASS."""
    import shutil
    res = {}
    for mode in ['untracked', 'committed']:
        d = os.path.join(workdir, f'_gate_selftest_{mode}')
        shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        subprocess.run(['git', 'init', '-q', d], capture_output=True)
        open(os.path.join(d, 'README.md'), 'w').write('selftest')
        subprocess.run(['git', '-C', d, 'add', 'README.md'], capture_output=True)
        for base, lpath in files.items():
            open(os.path.join(d, base), 'wb').write(open(lpath, 'rb').read())
        rules_b = 'T2b2_decision_rules_frozen_v0.3.md'
        rules_sha = None
        if mode == 'committed':
            subprocess.run(['git', '-C', d, 'add', '-A'], capture_output=True)
        subprocess.run(['git', '-C', d, '-c', 'user.email=t@t', '-c', 'user.name=t',
                        'commit', '-q', '-m', 'x'], capture_output=True)
        if rules_b in files:
            rules_sha = hashlib.sha256(open(files[rules_b], 'rb').read()).hexdigest()
        g = head_gate(d, {k: v for k, v in files.items() if k != rules_b},
                      rules_b, rules_sha or '0' * 64)
        res[mode] = g['ok']
        shutil.rmtree(d, ignore_errors=True)
    return res, (res.get('untracked') is False and res.get('committed') is True)


# ---------------- runner ----------------
RAW_COLS = ['key','name','family','xval','LAx','L1y','L2z','LAy','sA','s1','s2',
            'kcut','transfer','N','A2','A3','A4','Aband','Tr',
            'splus','sminus','splus_min','splus_max','sminus_min','sminus_max',
            'rho_psi_mean','rho_psi_min','rho_psi_max','frac_rho_psi_neg','sec']


def run_jobs(jobs, ctx):
    E7, F_SW, F_full, band_stats = ctx['E7Twisted'], ctx['F_SW'], ctx['F_full'], ctx['band_stats']
    br, BP, BM, OS_LIST = ctx['br'], ctx['BP'], ctx['BM'], ctx['OS_LIST']
    CKPT, BAND = ctx['CKPT'], ctx['BAND']
    done = set()
    if os.path.exists(CKPT):
        done = set(pd.read_csv(CKPT)['key'].astype(str))
        print(f'チェックポイント再開: 既存 {len(done)} 行')
    newfile = not os.path.exists(CKPT)
    fh = open(CKPT, 'a', newline=''); w = csv.writer(fh)
    if newfile:
        w.writerow(RAW_COLS)
    t0 = time.time(); ndone = 0
    for g, s, kc in jobs:
        keys = {tag: f"{g['name']}|{s[0]},{s[1]},{s[2]}|{kc:g}|{tag}" for tag in ('SW', 'full')}
        if all(k in done for k in keys.values()):
            continue
        t1 = time.time()
        M = E7(LAx=g['LAx'], L1y=g['L1y'], L2z=g['L2z'], LAy=g['LAy'],
               sA=s[0], s1=s[1], s2=s[2], kcut=kc)
        Cs, lm = M.sky_cov_q_multi([F_SW, F_full], list(BAND), chunk=ctx.get('chunk', 3000))
        dt = time.time() - t1
        for tag, Cq in zip(('SW', 'full'), Cs):
            if keys[tag] in done:      # v1.2: 部分中断からのresumeでもduplicate行を作らない
                continue
            A, Ab, Tr, rho = band_stats(M, Cq, lm, BAND)
            sr = br.s_pm_point(Cq, BP, BM, OS_LIST)   # per-point hard gates内蔵
            w.writerow([keys[tag], g['name'], g['family'], g['xval'],
                        g['LAx'], g['L1y'], g['L2z'], g['LAy'], s[0], s[1], s[2],
                        kc, tag, M.N, A[2], A[3], A[4], Ab, Tr,
                        sr['splus'], sr['sminus'], sr['splus_min'], sr['splus_max'],
                        sr['sminus_min'], sr['sminus_max'], sr['rho_psi_mean'],
                        sr['rho_psi_min'], sr['rho_psi_max'], sr['frac_rho_psi_neg'],
                        round(dt, 2)])
            done.add(keys[tag])
        fh.flush(); ndone += 1
        if ndone == 3:
            per = (time.time() - t0) / 3
            print(f'  ETA目安: {per:.1f}s/ladder点 × 残り{len(jobs)-3} ≈ {(len(jobs)-3)*per/60:.0f}分')
    fh.close()


# ---------------- extrapolation / classification (rules v0.3 sec.3.3) ----------------
def _fit_p(kc, v, p):
    x = np.asarray(kc, float) ** (-p)
    Am = np.stack([np.ones_like(x), x], 1)
    cf, *_ = np.linalg.lstsq(Am, np.asarray(v, float), rcond=None)
    return float(cf[0]), float(np.sqrt(np.mean((Am @ cf - v) ** 2)))


def run_extrapolation(CKPT, br):
    df = pd.read_csv(CKPT).drop_duplicates(subset=['key'], keep='last')
    recs = []
    for keytuple, gdf in df.groupby(['name','family','xval','sA','s1','s2','transfer']):
        name, fam, xv, sA, s1, s2, tag = keytuple
        gdf = gdf.sort_values('kcut')
        if len(gdf) < 4:
            continue
        kc = gdf['kcut'].values
        rec = dict(name=name, family=fam, xval=xv, sA=sA, s1=s1, s2=s2,
                   transfer=tag, kmax=float(kc.max()), npts=len(gdf))
        for col in ['A2','A3','A4','Aband','Tr']:   # legacy（v0.1定義：RMS込み・副次）
            v = gdf[col].values
            E1, r1 = _fit_p(kc, v, 3.0); E2, _ = _fit_p(kc, v, 2.0); E3 = float(v[-1])
            sysd = max(abs(E1-E2), abs(E1-E3), r1)
            rec[col+'_inf'] = E1; rec[col+'_sys'] = sysd
            rec[col+'_class'] = ('pos' if (E1-3*sysd > 0 and E2 > 0 and E3 > 0)
                                 else ('neg' if (E1+3*sysd < 0 and E2 < 0 and E3 < 0) else 'unc'))
        mods = {}
        for col in ['splus','sminus']:
            v = gdf[col].values
            E1, r1 = _fit_p(kc, v, 3.0); E2, _ = _fit_p(kc, v, 2.0); E3 = float(v[-1])
            mods[col] = dict(E1=E1, E2=E2, E3=E3, rms=r1)
            rec[col+'_inf'] = E1
            rec[col+'_sys'] = max(abs(E1-E2), abs(E1-E3))   # 凍結v0.3と完全一致
            rec[col+'_fitrms'] = r1
        rho_e = {}
        for e in ['E1','E2','E3']:
            den = mods['splus'][e] + mods['sminus'][e]
            rho_e[e] = (mods['splus'][e] - mods['sminus'][e]) / den if den > 0 else np.nan
        rec['rho_q_inf'] = rho_e['E1']
        rec['rho_q_sys'] = float(np.nanmax([abs(rho_e['E2']-rho_e['E1']),
                                            abs(rho_e['E3']-rho_e['E1'])]))
        rec['s_tot_inf'] = mods['splus']['E1'] + mods['sminus']['E1']
        eps_x = 1e-6 * max(mods['splus']['E3'] + mods['sminus']['E3'], 1e-300)
        unstable = False
        for e in ['E1','E2','E3']:
            den_e = mods['splus'][e] + mods['sminus'][e]
            unstable |= (mods['splus'][e] < -eps_x or mods['sminus'][e] < -eps_x or den_e <= 0
                         or (not np.isfinite(rho_e[e])) or abs(rho_e[e]) > 1 + 1e-9)
        rec['extrap_status'] = 'unstable' if unstable else 'ok'
        rec['rho_inf_legacy'] = 4*np.pi*rec['Aband_inf']/rec['Tr_inf']
        recs.append(rec)
    ext = pd.DataFrame(recs)
    if len(ext) == 0:
        return ext
    smax = {t: ext[ext.transfer == t]['s_tot_inf'].max() for t in ext.transfer.unique()}
    def _cls(r):
        if r['extrap_status'] == 'unstable':
            return 'unc'
        if not np.isfinite(r['rho_q_inf']) or r['s_tot_inf'] <= 0 \
           or r['s_tot_inf'] < br.NOSIG_REL * smax[r['transfer']]:
            return 'no-signal'
        return br.classify_rho(r['rho_q_inf'], r['rho_q_sys'])
    ext['rho_q_class'] = ext.apply(_cls, axis=1)
    ext.loc[ext.rho_q_class == 'no-signal', 'rho_q_inf'] = np.nan
    med_sm = {t: ext[ext.transfer == t]['sminus_inf'].clip(lower=0).median()
              for t in ext.transfer.unique()}
    g2s, mv_p, mv_m, flags = [], [], [], []
    for _, r in ext.iterrows():
        smv = max(r['sminus_inf'], 0.0)
        if r['sminus_inf'] <= 0:                       # minor fix（レビュー§11）
            g2s.append(np.inf); flags.append('not_constrained_by_Sminus_budget')
            mv_p.append(np.nan); mv_m.append(0.0)      # s-=0なら任意有限g_effでS-移動は0
        else:
            g2, fl = br.g2max_of(smv, DSMAX, med_sm[r['transfer']])
            g2s.append(g2); flags.append(fl)
            mv_p.append(g2 * max(r['splus_inf'], 0.0)); mv_m.append(g2 * smv)
    ext['g2eff_max_meanbudget'] = g2s; ext['g2eff_flag'] = flags
    ext['move_splus_at_g2eff'] = mv_p; ext['move_sminus_at_g2eff'] = mv_m
    return ext


def find_R2_pairs(ext, GEOMS, exclude=R2_EXCLUDE_FAMILIES):
    """final tableに対する隣接negペア判定（S5anisoは除外・isolated-candidate family扱い）"""
    fu = ext[(ext.transfer == 'full') & (ext.rho_q_class == 'neg')
             & ~ext.family.isin(exclude)]
    xv = {}
    for g in GEOMS:
        xv.setdefault(g['family'], []).append(g['xval'])
    pairs = []
    for (fam, sa, s1_, s2_), gsub in fu.groupby(['family','sA','s1','s2']):
        xs = set(gsub['xval']); seq = sorted(xv.get(fam, []))
        for a, b in zip(seq, seq[1:]):
            if a in xs and b in xs:
                pairs.append((fam, int(sa), int(s1_), int(s2_), a, b))
    return pairs


def refine_pass(ext, GEOMS, ctx, run_mode):
    """主refine trigger＝ρ_q neg/unc・unstableのみ → refine ladder → 自動再外挿 →
    final分類 → **final R2隣接判定**（レビュー§8：R2′はfinal tableのみで判定）"""
    refine_expected = set()
    if run_mode == 'smoke' or len(ext) == 0:
        print('（refineスキップ：smokeまたは外挿結果なし）')
        return ext, find_R2_pairs(ext, GEOMS) if len(ext) else [], refine_expected
    flagged = ext[(ext.transfer == 'full') & ((ext.rho_q_class.isin(['neg','unc'])) |
                                              (ext.extrap_status == 'unstable'))]
    legacy = ext[(ext.transfer == 'full') & (ext.Aband_class != 'pos')
                 & ~ext.index.isin(flagged.index)]
    if len(legacy):
        print(f'（参考）旧Aband由来candidate {len(legacy)}件：secondary legacy diagnosticのため'
              '主refineには含めない')
    cfgs = flagged[['name','sA','s1','s2']].drop_duplicates()
    print(f'精査対象構成: {len(cfgs)}')
    if len(cfgs):
        gmap = {g['name']: g for g in GEOMS}
        jobs2 = [(gmap[r['name']], (int(r['sA']), int(r['s1']), int(r['s2'])), kc)
                 for _, r in cfgs.iterrows() for kc in [38.0, 42.0]]
        for _, r in cfgs.iterrows():
            for kc in [38.0, 42.0]:
                for tag in ('SW', 'full'):
                    refine_expected.add(f"{r['name']}|{r['sA']},{r['s1']},{r['s2']}|{kc:g}|{tag}")
        run_jobs(jobs2, ctx)
        ext = run_extrapolation(ctx['CKPT'], ctx['br'])
    r2 = find_R2_pairs(ext, GEOMS)
    return ext, r2, refine_expected


def completion_check(CKPT, GEOMS, SECTORS, KCUTS, refine_expected=set()):
    """R1′完了証明用：期待keyの完全一致検査（missing=0・unexpected=0）"""
    expected = {f"{g['name']}|{s[0]},{s[1]},{s[2]}|{kc:g}|{tag}"
                for g in GEOMS for s in SECTORS for kc in KCUTS for tag in ('SW', 'full')}
    expected |= set(refine_expected)
    if os.path.exists(CKPT):
        _k = pd.read_csv(CKPT)['key'].astype(str)
        actual = set(_k)
        n_dup = int(len(_k) - len(actual))
    else:
        actual = set(); n_dup = 0
    return dict(n_expected=len(expected), n_actual=len(actual), n_duplicates=n_dup,
                missing=sorted(expected - actual)[:20], n_missing=len(expected - actual),
                unexpected=sorted(actual - expected)[:20], n_unexpected=len(actual - expected),
                ok=bool(expected == actual and n_dup == 0))


def v7_crosscheck(E7cls, F_SW, geom, sector, kcut=14.0, npts=3000, tol=1e-2):
    """Frozen candidate-level V7 cross-check (procedure fixed BEFORE any candidate is seen):
    apply the existing V7 real-space validation verbatim to the candidate (geometry, sector):
    harmonic sum_l A_l (SW transfer, l=0..30) vs real-space mean(2 D^2)/25 over a Fibonacci
    sphere; PASS iff |ratio-1| < tol."""
    i = np.arange(npts) + 0.5
    z = 1 - 2 * i / npts
    r = np.sqrt(1 - z * z)
    th = np.pi * (1 + 5 ** 0.5) * i
    pts = np.stack([r * np.cos(th), r * np.sin(th), z], 1)
    M = E7cls(LAx=geom['LAx'], L1y=geom['L1y'], L2z=geom['L2z'], LAy=geom['LAy'],
              sA=sector[0], s1=sector[1], s2=sector[2], kcut=kcut)
    C, lm = M.sky_cov_q(F_SW, list(range(0, 31)), chunk=500)
    A = M.A_refl_y(C, lm, list(range(0, 31)))
    D = M.Cphi_pairs(pts, pts * np.array([1.0, -1.0, 1.0]))
    ratio = float(sum(A.values()) / (np.mean(2 * D * D) / 25.0))
    return dict(ratio=ratio, ok=bool(abs(ratio - 1) < tol), kcut=kcut, npts=npts, tol=tol)