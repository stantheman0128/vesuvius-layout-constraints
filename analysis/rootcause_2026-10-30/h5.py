"""H5 attachment coupling and H4c (patches tied by human same-winding pcls), plus the pair geometry check."""
import json
import os

import numpy as np
import scipy.ndimage
from PIL import Image
from scipy.spatial import cKDTree
from scipy.stats import fisher_exact

from common import AREA, DS, FRAC, G, HAS, HERE, IDS, sets, theta_r, umbilicus_yx
from build_geom import point_tri_dist

struct = json.load(open(os.path.join(HERE, 'pcl_struct.json')))
d = G['d_ours']
n = len(IDS)


def patch_set(srcs, cross_only=True):
    m = np.zeros(n, bool)
    for s in struct.values():
        if s['src'] in srcs and (s['cross_patch'] or not cross_only) and len(s['patch_order']) >= 1:
            if s['src'] != 'habs' and len(s['attached_points']) < 2:
                continue
            m[s['patch_order']] = True
    return m


def paired_set(srcs):
    m = np.zeros(n, bool)
    for s in struct.values():
        if s['src'] in srcs:
            for a, b in s['pairs']:
                m[a] = m[b] = True
    return m


AP = patch_set({'ours'}); APP = paired_set({'ours'})
HS = patch_set({'hsame'}); HSP = paired_set({'hsame'})
HR = patch_set({'hrel', 'habs'})
print(f'patches attached by our cross-patch collections: {int(AP.sum())} (in an adjacent pair: {int(APP.sum())});'
      f' by human same-winding: {int(HS.sum())} (paired {int(HSP.sum())}); by human relative/abs: {int(HR.sum())}')
print(f'  our attached patches also attached by human same: {int((AP & HS).sum())}, by human rel/abs: {int((AP & HR).sum())}')
print(f'  d_ours of our attached patches: median {np.median(d[AP]):.1f}, max {d[AP].max():.0f}'
      ' (d_ours is to in-window points only; attachment uses points at any z)')


def rate(tag, test, pool):
    a = int((test & pool).sum()); b = int(pool.sum())
    return a, b


res = {}
for pre, label in (('g', 'GPU'), ('c', 'CPU')):
    st = sets(pre)
    print(f'\n=== {label}')
    dA = (FRAC[pre + 'B1'] + FRAC[pre + 'B2']) / 2 - (FRAC[pre + 'A1'] + FRAC[pre + 'A2']) / 2
    rows = [('ours attached', AP), ('ours paired', APP), ('not attached, d<100', ~AP & (d < 100)),
            ('not attached, d<300', ~AP & (d < 300)), ('not attached, all', ~AP),
            ('human same attached', HS), ('human same paired', HSP), ('human same, not ours', HS & ~AP),
            ('only human rel/abs', HR & ~HS & ~AP), ('no pcl at all', ~HR & ~HS & ~AP)]
    for name, m in rows:
        m = m & HAS
        la, lb = rate(name, st['L'], m & st['Apool']); ga, gb = rate(name, st['G'], m & st['Bpool'])
        na = int((st['NA'] & m).sum()); nb = int((st['NB'] & m).sum())
        print(f'  {name:<22} n={int(m.sum()):4d}  L {la:3d}/{lb:<4d} ({la / max(lb, 1) * 100:5.1f}%)  G {ga:3d}/{gb:<4d}'
              f' ({ga / max(gb, 1) * 100:5.1f}%)  noise-flip A {na / max(m.sum(), 1) * 100:5.1f}% B {nb / max(m.sum(), 1) * 100:5.1f}%'
              f'  mean dFrac(B-A) {dA[m].mean():+.4f}  area-wtd {np.sum(AREA[m] * dA[m]) / max(AREA[m].sum(), 1):+.4f}')
        res[f'{pre}:{name}'] = dict(L=[la, lb], G=[ga, gb], NA=na, NB=nb, n=int(m.sum()))
    for test_name, A_, B_ in (('ours attached vs not attached d<100', AP, ~AP & (d < 100)),
                              ('ours attached vs not attached all', AP, ~AP),
                              ('H4c human-same attached (not ours) vs only rel/abs or none', HS & ~AP, ~HS & ~AP)):
        a, b = rate('', st['L'], A_ & HAS & st['Apool']); c_, e = rate('', st['L'], B_ & HAS & st['Apool'])
        orr, p = fisher_exact([[a, b - a], [c_, e - c_]])
        print(f'  Fisher L rate, {test_name}: {a}/{b} vs {c_}/{e}, OR {orr:.2f}, p {p:.3g}')
        a, b = int((st['NB'] & A_ & HAS).sum()), int((A_ & HAS).sum()); c_, e = int((st['NB'] & B_ & HAS).sum()), int((B_ & HAS).sum())
        a0, c0 = int((st['NA'] & A_ & HAS).sum()), int((st['NA'] & B_ & HAS).sum())
        print(f'      noise-flip B {a}/{b} vs {c_}/{e}; noise-flip A {a0}/{b} vs {c0}/{e}')

# ---------- pair geometry: are the two patches of an adjacent pair the same sheet where they meet?
VP = f'{DS}/phercparis4/verified_patches'


def load_full(name):
    dd = os.path.join(VP, name)
    meta = json.load(open(os.path.join(dd, 'meta.json')))
    arr = [np.array(Image.open(os.path.join(dd, f'{c}.tif'))).astype(np.float64) for c in 'xyz']
    Pp = np.stack(arr, -1)
    if os.path.exists(os.path.join(dd, 'mask.tif')):
        mk = np.array(Image.open(os.path.join(dd, 'mask.tif')))
        mk = mk[..., 0] if mk.ndim == 3 else mk
        Pp[mk == 0] = -1
    valid = np.any(Pp != -1, axis=-1)
    cells = meta.get('spiral_patch_erode_cells'); cells = 1 if cells is None else int(cells)
    if cells > 0:
        valid = scipy.ndimage.binary_erosion(valid, iterations=cells, border_value=0)
    vq = valid[:-1, :-1] & valid[1:, :-1] & valid[:-1, 1:] & valid[1:, 1:]
    quads = np.stack([Pp[:-1, :-1][vq], Pp[1:, :-1][vq], Pp[:-1, 1:][vq], Pp[1:, 1:][vq]], 1)
    return Pp[valid], quads


cache = {}


def get(i):
    if i not in cache:
        cache[i] = load_full(str(IDS[i]))
    return cache[i]


umb = umbilicus_yx()


def pair_geom(i, j, max_d=30.0):
    """Vertices of j against the surface of i (and back); returns counts by distance band and radial offset."""
    out = {}
    for a, b in ((i, j), (j, i)):
        va, qa = get(a); vb, _ = get(b)
        cen = qa.mean(1)
        hd = np.max(np.linalg.norm(qa - cen[:, None, :], axis=2))
        tree = cKDTree(cen)
        dmin, _ = tree.query(vb, k=1, distance_upper_bound=max_d + hd)
        near = np.where(np.isfinite(dmin))[0]
        best = np.full(len(vb), np.inf)
        if len(near):
            lists = tree.query_ball_point(vb[near], r=max_d + hd)
            qi = np.concatenate([np.asarray(l, np.int64) for l in lists])
            pj = np.repeat(near, [len(l) for l in lists])
            dd = np.minimum(point_tri_dist(vb[pj], qa[qi, 0], qa[qi, 1], qa[qi, 2]),
                            point_tri_dist(vb[pj], qa[qi, 1], qa[qi, 3], qa[qi, 2]))
            np.minimum.at(best, pj, dd)
        # radial offset of b's vertices relative to the nearest vertex of a (umbilicus frame)
        _, nn = cKDTree(va).query(vb, k=1)
        _, rb = theta_r(vb, umb); _, ra = theta_r(va[nn], umb)
        dr = rb - ra
        m_close = best <= 3; m_band = (best > 6) & (best <= 30)
        out[(a, b)] = dict(n=len(vb), close=int(m_close.sum()), band=int(m_band.sum()),
                           dmin=float(best.min()) if np.isfinite(best).any() else float('inf'),
                           dr_band=float(np.median(dr[m_band])) if m_band.any() else float('nan'))
    r1, r2 = out[(i, j)], out[(j, i)]
    close = r1['close'] + r2['close']; band = r1['band'] + r2['band']
    dmin = min(r1['dmin'], r2['dmin'])
    if close >= 10:
        cls = 'overlap, same surface'
    elif band >= 40:
        cls = 'parallel at 6-30 vx, no coincident overlap'
    elif dmin <= 30:
        cls = 'touch at edge'
    else:
        cls = 'disjoint (> 30 vx apart)'
    return dict(cls=cls, close=close, band=band, dmin=dmin, dr_band=[r1['dr_band'], r2['dr_band']])


stg, stc = sets('g'), sets('c')


def status(i, st):
    for k in ('L', 'G', 'S'):
        if st[k][i]:
            return k
    return 'NA' if st['NA'][i] else ('NB' if st['NB'][i] else '-')


pair_rows = []
for key, s in struct.items():
    if s['src'] not in ('ours', 'hsame') or not s['pairs']:
        continue
    for a, b in s['pairs']:
        g_ = pair_geom(a, b)
        pair_rows.append(dict(src=s['src'], chain=s['name'], a=int(a), b=int(b), **g_,
                              gpu=(status(a, stg), status(b, stg)), cpu=(status(a, stc), status(b, stc)),
                              area=(float(AREA[a]), float(AREA[b]))))
print('\npair geometry, ours:')
for r in pair_rows:
    if r['src'] == 'ours':
        print(f"  {r['chain'][-28:]:<28} {r['a']:4d}-{r['b']:<4d} {r['cls']:<42} close {r['close']:5d} band {r['band']:5d}"
              f" dmin {r['dmin']:7.1f} dr {r['dr_band'][0]:+6.1f}/{r['dr_band'][1]:+6.1f}  GPU {r['gpu']} CPU {r['cpu']}")
for src in ('ours', 'hsame'):
    rr = [r for r in pair_rows if r['src'] == src]
    cl = {}
    for r in rr:
        cl[r['cls']] = cl.get(r['cls'], 0) + 1
    print(f'{src}: {len(rr)} pairs; classes {cl}')
json.dump(dict(res=res, pairs=pair_rows), open(os.path.join(HERE, 'h5_results.json'), 'w'), indent=1, default=str)
