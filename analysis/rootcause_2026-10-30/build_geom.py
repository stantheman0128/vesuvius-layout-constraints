"""Patch geometry, patch-to-constraint distances and a replica of the fitter's point-to-patch linking.

Streams the 2,489 in-window patches one at a time (mask.tif, the fitter's 1-cell erosion), keeps a
stride-2 subsample of in-window vertices for later distance matrices, computes exact per-patch minimum
distances to the in-window constraint points (all in-window vertices), and links every constraint point
(all z) to patches within 2.5 voxels by exact point-to-triangle distance.
Writes geom.npz, links.json and points.npz next to this script.
"""
import json
import os
import time

import numpy as np
import scipy.ndimage
from PIL import Image
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
DS = os.environ.get('SPIRAL_DS', os.path.join(HERE, '..', '..', 'data', 'spiral_datasets'))
VP = f'{DS}/phercparis4/verified_patches'
Z0, Z1 = 10500.0, 11500.0
TOL = 2.5


def imread(path):
    """Same reader as the fitter (tifxyz.py uses PIL), handles the LZW masks."""
    with Image.open(path) as im:
        return np.array(im)


def point_tri_dist(p, a, b, c):
    """Point-to-triangle distance, Ericson 5.1.5 (same as tools/patch_distance.py)."""
    ab = b - a; ac = c - a; ap = p - a
    d1 = (ab * ap).sum(1); d2 = (ac * ap).sum(1)
    bp = p - b; d3 = (ab * bp).sum(1); d4 = (ac * bp).sum(1)
    cp = p - c; d5 = (ab * cp).sum(1); d6 = (ac * cp).sum(1)
    res = np.empty_like(p); done = np.zeros(len(p), bool)

    def sd(n, d):
        return np.where(d != 0, n / np.where(d != 0, d, 1.0), 0.0)
    m = (d1 <= 0) & (d2 <= 0); res[m] = a[m]; done |= m
    m = (~done) & (d3 >= 0) & (d4 <= d3); res[m] = b[m]; done |= m
    vc = d1 * d4 - d3 * d2
    m = (~done) & (vc <= 0) & (d1 >= 0) & (d3 <= 0); v = sd(d1, d1 - d3); res[m] = a[m] + v[m, None] * ab[m]; done |= m
    m = (~done) & (d6 >= 0) & (d5 <= d6); res[m] = c[m]; done |= m
    vb = d5 * d2 - d1 * d6
    m = (~done) & (vb <= 0) & (d2 >= 0) & (d6 <= 0); w = sd(d2, d2 - d6); res[m] = a[m] + w[m, None] * ac[m]; done |= m
    va = d3 * d6 - d5 * d4
    m = (~done) & (va <= 0) & (d4 - d3 >= 0) & (d5 - d6 >= 0)
    w2 = sd(d4 - d3, (d4 - d3) + (d5 - d6)); res[m] = b[m] + w2[m, None] * (c[m] - b[m]); done |= m
    m = ~done; den = va + vb + vc; v = sd(vb, den); w = sd(vc, den)
    res[m] = a[m] + v[m, None] * ab[m] + w[m, None] * ac[m]
    return np.linalg.norm(p - res, axis=1)


def load_points():
    rows = []  # (source, collection key, collection name, point id, x, y, z)
    sw = json.load(open(f'{DS}/phercparis4_plus_layout/same_windings.json'))['collections']
    n_ours = 0
    for key, col in sw.items():
        ours = 'merged_from' in col.get('metadata', {})
        n_ours += ours
        for pid, pt in col['points'].items():
            rows.append(('ours' if ours else 'hsame', key, col['name'], int(pid), *pt['p']))
    assert n_ours == 96, n_ours
    for fn, tag in (('relative_windings.json', 'hrel'), ('abs_winding.json', 'habs')):
        cols = json.load(open(f'{DS}/phercparis4/{fn}'))['collections']
        for key, col in cols.items():
            for pid, pt in col['points'].items():
                rows.append((tag, key, col['name'], int(pid), *pt['p']))
    src = np.array([r[0] for r in rows]); ckey = np.array([r[1] for r in rows])
    cname = np.array([r[2] for r in rows]); pid = np.array([r[3] for r in rows])
    xyz = np.array([r[4:7] for r in rows], np.float64)
    return src, ckey, cname, pid, xyz


def main():
    t0 = time.time()
    fl = np.load(os.path.join(HERE, 'flips.npz'))
    ids = list(fl['ids']); total_area = fl['area']
    lim = int(os.environ.get('LIMIT', 0))
    if lim:
        ids = ids[:lim]; total_area = total_area[:lim]
    src, ckey, cname, pid, xyz = load_points()
    np.savez(os.path.join(HERE, 'points.npz'), src=src, ckey=ckey, cname=cname, pid=pid, xyz=xyz)
    inwin = (xyz[:, 2] >= Z0) & (xyz[:, 2] < Z1)
    print({s: (int((src == s).sum()), int(((src == s) & inwin).sum())) for s in np.unique(src)}, flush=True)
    all_tree = cKDTree(xyz)
    win_trees = {s: (cKDTree(xyz[(src == s) & inwin]), np.where((src == s) & inwin)[0])
                 for s in ('ours', 'hsame', 'hrel')}

    n = len(ids)
    out = {k: np.full(n, np.nan) for k in (
        'area_full', 'nq_all4', 'nq_any', 'nq_centre', 'cx', 'cy', 'cz', 'zmin', 'zmax',
        'd_ours', 'd_hsame', 'd_hrel', 'max_half_diag')}
    nearest_ours_pt = np.full(n, -1, np.int64)
    sub_xyz, sub_off = [], [0]
    link_cands = []  # (point index, patch index, distance)
    for i, name in enumerate(ids):
        d = os.path.join(VP, name)
        meta = json.load(open(os.path.join(d, 'meta.json')))
        z = imread(os.path.join(d, 'z.tif')).astype(np.float64)
        y = imread(os.path.join(d, 'y.tif')).astype(np.float64)
        x = imread(os.path.join(d, 'x.tif')).astype(np.float64)
        P = np.stack([x, y, z], -1)
        if os.path.exists(os.path.join(d, 'mask.tif')):
            m = imread(os.path.join(d, 'mask.tif'))
            if m.ndim == 3:
                m = m[..., 0]
            P[m == 0] = -1.0
        valid = np.any(P != -1, axis=-1)
        cells = int(meta.get('spiral_patch_erode_cells', 1) if meta.get('spiral_patch_erode_cells') is not None else 1)
        if cells > 0:
            valid = scipy.ndimage.binary_erosion(valid, iterations=cells, border_value=0)
        P[~valid] = -1.0
        vq = valid[:-1, :-1] & valid[1:, :-1] & valid[:-1, 1:] & valid[1:, 1:]
        sc = np.asarray(meta['scale'], float)
        out['area_full'][i] = vq.sum() * np.prod(1 / sc)
        zz = P[..., 2]
        inz = valid & (zz >= Z0) & (zz < Z1)
        q4 = inz[:-1, :-1] & inz[1:, :-1] & inz[:-1, 1:] & inz[1:, 1:]
        qa = inz[:-1, :-1] | inz[1:, :-1] | inz[:-1, 1:] | inz[1:, 1:]
        zc = (zz[:-1, :-1] + zz[1:, :-1] + zz[:-1, 1:] + zz[1:, 1:]) / 4
        qc = (zc >= Z0) & (zc < Z1)
        out['nq_all4'][i] = (vq & q4).sum(); out['nq_any'][i] = (vq & qa).sum(); out['nq_centre'][i] = (vq & qc).sum()
        V = P[inz]
        if len(V):
            out['cx'][i], out['cy'][i], out['cz'][i] = V.mean(0)
            out['zmin'][i], out['zmax'][i] = V[:, 2].min(), V[:, 2].max()
            for s, (tr, idx) in win_trees.items():
                dd, jj = tr.query(V, k=1)
                k = int(np.argmin(dd))
                out[f'd_{s}'][i] = dd[k]
                if s == 'ours':
                    nearest_ours_pt[i] = idx[jj[k]]
        inz2 = inz.copy(); inz2[1::2, :] = False; inz2[:, 1::2] = False
        S = P[inz2]
        if len(S) == 0 and len(V):
            S = V[:1]
        sub_xyz.append(S.astype(np.float32)); sub_off.append(sub_off[-1] + len(S))
        # linking: every valid quad of the full (eroded) patch against all constraint points
        if vq.any():
            c00 = P[:-1, :-1][vq]; c10 = P[1:, :-1][vq]; c01 = P[:-1, 1:][vq]; c11 = P[1:, 1:][vq]
            cen = (c00 + c10 + c01 + c11) / 4
            hd = np.max(np.stack([np.linalg.norm(c - cen, axis=1) for c in (c00, c10, c01, c11)]), 0)
            out['max_half_diag'][i] = hd.max()
            # cheap prefilter: quads whose centre is within max(hd)+TOL of any point
            dmin, _ = all_tree.query(cen, k=1, distance_upper_bound=float(hd.max()) + TOL)
            near = np.where(np.isfinite(dmin))[0]
            if len(near):
                lists = all_tree.query_ball_point(cen[near], r=hd[near] + TOL)
                qi = np.repeat(near, [len(l) for l in lists]); pj = np.concatenate([np.asarray(l, np.int64) for l in lists])
                if len(pj):
                    p = xyz[pj]
                    d1 = point_tri_dist(p, c00[qi], c10[qi], c01[qi])
                    d2 = point_tri_dist(p, c10[qi], c11[qi], c01[qi])
                    dq = np.minimum(d1, d2)
                    ok = dq <= TOL
                    if ok.any():
                        # keep the minimum distance per point for this patch
                        pts, inv = np.unique(pj[ok], return_inverse=True)
                        best = np.full(len(pts), np.inf); np.minimum.at(best, inv, dq[ok])
                        link_cands.extend((int(a), i, float(b)) for a, b in zip(pts, best))
        if i % 250 == 0:
            print(f'{i}/{n} patches, {time.time() - t0:.0f}s, link candidates {len(link_cands)}', flush=True)
    np.savez(os.path.join(HERE, 'geom.npz'), ids=np.array(ids), total_area=total_area,
             nearest_ours_pt=nearest_ours_pt, sub_xyz=np.concatenate(sub_xyz), sub_off=np.array(sub_off),
             **out)
    json.dump(link_cands, open(os.path.join(HERE, 'link_cands.json'), 'w'))
    qa = total_area / 400.0
    for k in ('nq_all4', 'nq_any', 'nq_centre'):
        print(k, 'exact match with total_area/400:', int(np.sum(out[k] == qa)), 'of', n)
    print(f'done {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
