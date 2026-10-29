"""H1 locality (and H4a flatness): are flipped patches closer to our in-window points than the rest?"""
import json
import os

import numpy as np

from common import (AREA, FRAC, G, HAS, HERE, INWIN, SRC, CKEY, XYZ, auc_closer, patch_min_dist, sets,
                    umbilicus_yx)

rng = np.random.default_rng(20261030)
D = G['d_ours']  # exact, all in-window vertices
ours = XYZ[(SRC == 'ours') & INWIN]

# ---------- control distance sets (cached) ----------
cache = os.path.join(HERE, 'h1_controls.npz')
if os.path.exists(cache):
    C = dict(np.load(cache))
else:
    C = {'ours_sub': patch_min_dist(ours)}
    for ax, name in ((0, 'x'), (1, 'y'), (2, 'z')):
        for sgn in (+1, -1):
            sh = ours.copy(); sh[:, ax] += sgn * 40.0
            C[f'shift_{name}{"+" if sgn > 0 else "-"}40'] = patch_min_dist(sh)
    umb = umbilicus_yx()
    yx = umb(ours[:, 2])
    for deg in (30, -30, 60, -60, 90, -90):
        a = np.deg2rad(deg)
        dx, dy = ours[:, 0] - yx[:, 1], ours[:, 1] - yx[:, 0]
        ro = ours.copy()
        ro[:, 0] = yx[:, 1] + np.cos(a) * dx - np.sin(a) * dy
        ro[:, 1] = yx[:, 0] + np.sin(a) * dx + np.cos(a) * dy
        C[f'rot_{deg:+d}'] = patch_min_dist(ro)
    hum = (SRC != 'ours') & INWIN
    hkeys = sorted(set(zip(SRC[hum], CKEY[hum])))
    C['human_all'] = patch_min_dist(XYZ[hum])
    for t in range(200):
        pick = set(map(tuple, rng.choice(np.array(hkeys, dtype=object), 16, replace=False)))
        m = hum & np.array([(s, k) in pick for s, k in zip(SRC, CKEY)])
        C[f'hum16_{t:03d}'] = patch_min_dist(XYZ[m])
    np.savez(cache, **C)


def describe(name, m, d=D):
    a = AREA[m]
    return (f'{name:>5} n={int(m.sum()):4d} area={a.sum() / AREA.sum() * 100:5.2f}%  median d={np.median(d[m]):6.0f}'
            f'  <100: {np.mean(d[m] < 100) * 100:5.1f}%  <300: {np.mean(d[m] < 300) * 100:5.1f}%'
            f'  area<300: {a[d[m] < 300].sum() / max(a.sum(), 1) * 100:5.1f}%')


def matched_null(test, pool, minfrac, n_draw=10000, d=D):
    """Draws of |test| patches from pool matched on area quintile x margin bin."""
    pool_idx = np.where(pool)[0]
    q = np.quantile(AREA[pool_idx], [0.2, 0.4, 0.6, 0.8])
    abin = np.digitize(AREA, q)
    mbin = np.digitize(minfrac, [0.97, 0.99])
    key = abin * 10 + mbin
    strata = {}
    for k in np.unique(key[test]):
        need = int(np.sum(key[test] == k))
        cand = pool_idx[key[pool_idx] == k]
        strata[k] = (need, cand)
    med = np.empty(n_draw); f300 = np.empty(n_draw)
    for t in range(n_draw):
        pick = np.concatenate([rng.choice(c, n, replace=False) for n, c in strata.values()])
        med[t] = np.median(d[pick]); f300[t] = np.mean(d[pick] < 300)
    om, of = np.median(d[test]), np.mean(d[test] < 300)
    return om, of, med, f300


res = {}
for pre, label in (('g', 'GPU 30k'), ('c', 'CPU 4k')):
    st = sets(pre)
    print(f'\n=================== {label}')
    for k in ('L', 'G', 'S', 'NA', 'NB', 'L1', 'L2', 'G1', 'G2'):
        print(describe(k, st[k]))
    print(describe('all', HAS))
    fa = np.minimum(FRAC[pre + 'A1'], FRAC[pre + 'A2'])
    fb = np.minimum(FRAC[pre + 'B1'], FRAC[pre + 'B2'])
    for test, pool, mf in (('L', 'Apool', fa), ('G', 'Bpool', fb)):
        om, of, med, f300 = matched_null(st[test], st[pool] & ~st[test] | st[test], mf)
        p_med = np.mean(med <= om); p_f = np.mean(f300 >= of)
        print(f'{test} vs matched draws from {pool}: median d {om:.0f} (null median {np.median(med):.0f},'
              f' 2.5-97.5% {np.percentile(med, 2.5):.0f}-{np.percentile(med, 97.5):.0f}), p(null<=obs) {p_med:.4f};'
              f' frac<300 {of:.3f} (null {np.median(f300):.3f}), p(null>=obs) {p_f:.4f}')
        res[f'{pre}_{test}_perm'] = dict(obs_median=float(om), null_median=float(np.median(med)), p=float(p_med),
                                          obs_f300=float(of), null_f300=float(np.median(f300)), p_f300=float(p_f))
    # AUCs with exact distances
    for t, r in (('L', 'S'), ('L', 'NA'), ('G', 'S'), ('G', 'NB'), ('NA', 'S'), ('NB', 'S')):
        print(f'AUC P({t} closer than {r}) = {auc_closer(D[st[t]], D[st[r]]):.3f}')
    # controls: AUC(L closer than S) and AUC(G closer than S) for every control point set
    rows = {}
    for name, dc in C.items():
        rows[name] = (auc_closer(dc[st['L']], dc[st['S']]), auc_closer(dc[st['G']], dc[st['S']]))
    h16 = np.array([v for k, v in rows.items() if k.startswith('hum16_')])
    print('control point sets, AUC(L closer than S) / AUC(G closer than S):')
    for name, (al, ag) in rows.items():
        if not name.startswith('hum16_'):
            print(f'  {name:>14}: {al:.3f} / {ag:.3f}')
    print(f'  hum16 x{len(h16)}: L median {np.median(h16[:, 0]):.3f} (2.5-97.5% {np.percentile(h16[:, 0], 2.5):.3f}-'
          f'{np.percentile(h16[:, 0], 97.5):.3f}), share >= ours {np.mean(h16[:, 0] >= rows["ours_sub"][0]):.3f};'
          f' G median {np.median(h16[:, 1]):.3f} ({np.percentile(h16[:, 1], 2.5):.3f}-{np.percentile(h16[:, 1], 97.5):.3f}),'
          f' share >= ours {np.mean(h16[:, 1] >= rows["ours_sub"][1]):.3f}')
    res[f'{pre}_controls'] = {k: v for k, v in rows.items() if not k.startswith('hum16_')}
    res[f'{pre}_hum16'] = h16.tolist()
    # continuous: change in fraction by distance bin, arm effect vs seed effect
    bins = [0, 100, 300, 600, 1000, 1e9]
    b = np.digitize(D, bins) - 1
    dA = (FRAC[pre + 'B1'] + FRAC[pre + 'B2']) / 2 - (FRAC[pre + 'A1'] + FRAC[pre + 'A2']) / 2
    dS = (FRAC[pre + 'A2'] + FRAC[pre + 'B2']) / 2 - (FRAC[pre + 'A1'] + FRAC[pre + 'B1']) / 2
    print('distance bin | n | mean dFrac arm (B-A) | mean dFrac seed (s2-s1) | area-wtd arm | area-wtd seed | L rate in Apool | G rate in Bpool | noise-flip rate A | B')
    for i in range(len(bins) - 1):
        m = HAS & (b == i)
        w = AREA[m]
        ap = m & st['Apool']; bp = m & st['Bpool']
        print(f'  {bins[i]:>4.0f}-{bins[i + 1]:<5.0f} | {int(m.sum()):4d} | {dA[m].mean():+.4f} | {dS[m].mean():+.4f} |'
              f' {np.sum(w * dA[m]) / w.sum():+.4f} | {np.sum(w * dS[m]) / w.sum():+.4f} |'
              f' {st["L"][ap].mean() * 100:5.1f}% ({int(st["L"][ap].sum())}/{int(ap.sum())}) |'
              f' {st["G"][bp].mean() * 100:5.1f}% ({int(st["G"][bp].sum())}/{int(bp.sum())}) |'
              f' {st["NA"][m].mean() * 100:5.1f}% | {st["NB"][m].mean() * 100:5.1f}%')
json.dump(res, open(os.path.join(HERE, 'h1_results.json'), 'w'), indent=1)
