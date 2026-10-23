"""Distance from point-collection points to the nearest verified-patch surface.

Usage: python tools/patch_distance.py DATASET_DIR MERGED_SAME_WINDINGS.json [--z 10500 11500] [--out report.json]

Loads every verified patch whose meta.json bbox overlaps the z window (with margin), keeps each valid quad
as two triangles, builds a KD-tree on quad centres to find candidate quads near each query point, then
computes exact point-to-triangle distances. Reports distributions for our collections (name matches the
layout regex) and for the human relative/same collections as controls.
"""
import argparse
import json
import os
import re
import time

import numpy as np
import tifffile
from scipy.spatial import cKDTree

OURS = re.compile(r"^\d{14}(-w\d{3}-\d{3})?_(line\d+|gap\d+|margin_left|margin_right)$")


def load_points(path):
    d = json.load(open(path))['collections']
    out = {}
    for c in d.values():
        out[c['name']] = np.array([pt['p'] for pt in c['points'].values()], np.float64).reshape(-1, 3)
    return out


def point_tri_dist(p, a, b, c):
    """Vectorised point-to-triangle distance (Ericson, Real-Time Collision Detection 5.1.5).
    p: (N,3) points; a,b,c: (N,3) triangle vertices paired with each point. Returns (N,) distances."""
    ab = b - a
    ac = c - a
    ap = p - a
    d1 = (ab * ap).sum(1)
    d2 = (ac * ap).sum(1)
    bp = p - b
    d3 = (ab * bp).sum(1)
    d4 = (ac * bp).sum(1)
    cp = p - c
    d5 = (ab * cp).sum(1)
    d6 = (ac * cp).sum(1)
    res = np.empty_like(p)
    done = np.zeros(len(p), bool)

    def safe_div(num, den):
        return np.where(den != 0, num / np.where(den != 0, den, 1.0), 0.0)

    m = (d1 <= 0) & (d2 <= 0)
    res[m] = a[m]
    done |= m
    m = (~done) & (d3 >= 0) & (d4 <= d3)
    res[m] = b[m]
    done |= m
    vc = d1 * d4 - d3 * d2
    m = (~done) & (vc <= 0) & (d1 >= 0) & (d3 <= 0)
    v = safe_div(d1, d1 - d3)
    res[m] = a[m] + v[m, None] * ab[m]
    done |= m
    m = (~done) & (d6 >= 0) & (d5 <= d6)
    res[m] = c[m]
    done |= m
    vb = d5 * d2 - d1 * d6
    m = (~done) & (vb <= 0) & (d2 >= 0) & (d6 <= 0)
    w = safe_div(d2, d2 - d6)
    res[m] = a[m] + w[m, None] * ac[m]
    done |= m
    va = d3 * d6 - d5 * d4
    m = (~done) & (va <= 0) & (d4 - d3 >= 0) & (d5 - d6 >= 0)
    w2 = safe_div(d4 - d3, (d4 - d3) + (d5 - d6))
    res[m] = b[m] + w2[m, None] * (c[m] - b[m])
    done |= m
    m = ~done
    denom = va + vb + vc
    v = safe_div(vb, denom)
    w = safe_div(vc, denom)
    res[m] = a[m] + v[m, None] * ab[m] + w[m, None] * ac[m]
    return np.linalg.norm(p - res, axis=1)


def summary(dv):
    dv = np.asarray(dv)
    fin = dv[np.isfinite(dv)]
    if len(fin) == 0:
        return {'n': int(len(dv)), 'none_within_radius': int(len(dv))}
    return {
        'n': int(len(dv)),
        'none_within_radius': int((~np.isfinite(dv)).sum()),
        'median': float(np.median(fin)),
        'p25': float(np.percentile(fin, 25)),
        'p75': float(np.percentile(fin, 75)),
        'p90': float(np.percentile(fin, 90)),
        'le2.5': float((dv <= 2.5).mean()),
        'le6': float((dv <= 6).mean()),
        'le10': float((dv <= 10).mean()),
        'le20': float((dv <= 20).mean()),
        'gt50': float(((dv > 50) | ~np.isfinite(dv)).mean()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dataset')
    ap.add_argument('merged_same')
    ap.add_argument('--z', nargs=2, type=float, default=[10500, 11500])
    ap.add_argument('--margin', type=float, default=100)
    ap.add_argument('--radius', type=float, default=60, help='candidate search radius (voxels)')
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    z0, z1 = a.z
    t0 = time.time()
    root = os.path.join(a.dataset, 'verified_patches')
    quads = []
    n_patches = 0
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        mp = os.path.join(d, 'meta.json')
        if not os.path.isfile(mp):
            continue
        try:
            bb = json.load(open(mp))['bbox']
        except Exception:
            continue
        if bb[1][2] < z0 - a.margin or bb[0][2] > z1 + a.margin:
            continue
        x = tifffile.imread(os.path.join(d, 'x.tif')).astype(np.float64)
        y = tifffile.imread(os.path.join(d, 'y.tif')).astype(np.float64)
        z = tifffile.imread(os.path.join(d, 'z.tif')).astype(np.float64)
        valid = (x >= 0) & (y >= 0) & (z >= 0)
        inz = (z >= z0 - a.margin) & (z <= z1 + a.margin)
        vq = valid[:-1, :-1] & valid[1:, :-1] & valid[:-1, 1:] & valid[1:, 1:]
        zq = inz[:-1, :-1] | inz[1:, :-1] | inz[:-1, 1:] | inz[1:, 1:]
        q = vq & zq
        if not q.any():
            continue
        P = np.stack([x, y, z], -1)
        c00 = P[:-1, :-1][q]
        c10 = P[1:, :-1][q]
        c01 = P[:-1, 1:][q]
        c11 = P[1:, 1:][q]
        quads.append(np.stack([c00, c10, c01, c11], 1))
        n_patches += 1
    quads = np.concatenate(quads, 0)
    print(f'patches used {n_patches}, quads {len(quads)}, load {time.time() - t0:.0f}s', flush=True)
    centers = quads.mean(1)
    half_diag = float(np.linalg.norm(quads[:, 0] - quads[:, 3], axis=1).max() / 2)
    print(f'max half diagonal {half_diag:.1f} voxels', flush=True)
    tree = cKDTree(centers)

    def dist_to_patches(Q):
        out = np.full(len(Q), np.inf)
        lists = tree.query_ball_point(Q, a.radius + half_diag)
        pairs = [(i, l) for i, l in enumerate(lists) if l]
        if not pairs:
            return out
        qi = np.concatenate([np.full(len(l), i) for i, l in pairs])
        ci = np.concatenate([np.asarray(l) for _, l in pairs])
        p = Q[qi]
        qd = quads[ci]
        d = np.minimum(point_tri_dist(p, qd[:, 0], qd[:, 1], qd[:, 3]),
                       point_tri_dist(p, qd[:, 0], qd[:, 3], qd[:, 2]))
        np.minimum.at(out, qi, d)
        return out

    report = {}
    merged = load_points(a.merged_same)
    ours = {n: P for n, P in merged.items() if OURS.match(n)}
    human_same = {n: P for n, P in merged.items() if not OURS.match(n)}
    human_rel = load_points(os.path.join(a.dataset, 'relative_windings.json'))
    for label, cols in [('ours', ours), ('human_same', human_same), ('human_rel', human_rel)]:
        allP = []
        per = {}
        for n, P in cols.items():
            W = P[(P[:, 2] >= z0) & (P[:, 2] < z1)]
            if len(W) == 0:
                continue
            dv = dist_to_patches(W)
            per[n] = summary(dv)
            un = dv[dv > 2.5]
            per[n]['unattached'] = summary(un) if len(un) else None
            allP.append(dv)
        allv = np.concatenate(allP)
        report[label] = {'all': summary(allv), 'unattached_only': summary(allv[allv > 2.5]), 'per_collection': per}
        s = report[label]['all']
        u = report[label]['unattached_only']
        print(f"{label}: n={s['n']} attached(<=2.5)={s['le2.5']:.3f} | unattached n={u['n']} "
              f"median={u.get('median', float('nan')):.1f} p75={u.get('p75', float('nan')):.1f} "
              f"p90={u.get('p90', float('nan')):.1f} <=6:{u.get('le6', 0):.2f} <=10:{u.get('le10', 0):.2f} "
              f"<=20:{u.get('le20', 0):.2f} >50:{u.get('gt50', 0):.2f}", flush=True)
    if a.out:
        json.dump(report, open(a.out, 'w'), indent=1)
        raw = {}
        for label, cols in [('ours', ours), ('human_same', human_same), ('human_rel', human_rel)]:
            for n, P in cols.items():
                W = P[(P[:, 2] >= z0) & (P[:, 2] < z1)]
                if len(W):
                    raw[f'{label}/{n}'] = dist_to_patches(W)
        np.savez_compressed(os.path.splitext(a.out)[0] + '_raw.npz', **raw)
    print(f'done {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
