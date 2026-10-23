"""Distance from a segment's own mesh vertices (dense, not just text lines) to the nearest verified patch.

Usage: python tools/segment_patch_distance.py DATASET_DIR MESH_DIR [MESH_DIR...] [--z 10500 11500] [--div 4]

Each MESH_DIR holds x/y/z.tif in the volume frame; --div rescales to the dataset frame (9.6 um = mesh / 4).
Prints a 2-voxel histogram of vertex-to-patch distance for vertices whose z falls in the window, so a
segment that coincides with the patches shows a peak at 0..2 and a segment at a fixed offset shows the
peak at that offset.
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import tifffile
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(__file__))
from patch_distance import point_tri_dist  # noqa: E402


def load_quads(dataset, z0, z1, margin):
    root = os.path.join(dataset, 'verified_patches')
    quads = []
    n = 0
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        mp = os.path.join(d, 'meta.json')
        if not os.path.isfile(mp):
            continue
        bb = json.load(open(mp))['bbox']
        if bb[1][2] < z0 - margin or bb[0][2] > z1 + margin:
            continue
        x = tifffile.imread(os.path.join(d, 'x.tif')).astype(np.float64)
        y = tifffile.imread(os.path.join(d, 'y.tif')).astype(np.float64)
        z = tifffile.imread(os.path.join(d, 'z.tif')).astype(np.float64)
        valid = (x >= 0) & (y >= 0) & (z >= 0)
        inz = (z >= z0 - margin) & (z <= z1 + margin)
        vq = valid[:-1, :-1] & valid[1:, :-1] & valid[:-1, 1:] & valid[1:, 1:]
        zq = inz[:-1, :-1] | inz[1:, :-1] | inz[:-1, 1:] | inz[1:, 1:]
        q = vq & zq
        if not q.any():
            continue
        P = np.stack([x, y, z], -1)
        quads.append(np.stack([P[:-1, :-1][q], P[1:, :-1][q], P[:-1, 1:][q], P[1:, 1:][q]], 1))
        n += 1
    return np.concatenate(quads, 0), n


def make_dist_fn(quads, radius):
    centers = quads.mean(1)
    half_diag = float(np.linalg.norm(quads[:, 0] - quads[:, 3], axis=1).max() / 2)
    tree = cKDTree(centers)

    def dist(Q, chunk=20000):
        out = np.full(len(Q), np.inf)
        for s in range(0, len(Q), chunk):
            Qc = Q[s:s + chunk]
            lists = tree.query_ball_point(Qc, radius + half_diag)
            pairs = [(i, l) for i, l in enumerate(lists) if l]
            if not pairs:
                continue
            qi = np.concatenate([np.full(len(l), i) for i, l in pairs])
            ci = np.concatenate([np.asarray(l) for _, l in pairs])
            p = Qc[qi]
            qd = quads[ci]
            d = np.minimum(point_tri_dist(p, qd[:, 0], qd[:, 1], qd[:, 3]),
                           point_tri_dist(p, qd[:, 0], qd[:, 3], qd[:, 2]))
            o = np.full(len(Qc), np.inf)
            np.minimum.at(o, qi, d)
            out[s:s + chunk] = o
        return out
    return dist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dataset')
    ap.add_argument('meshes', nargs='+')
    ap.add_argument('--z', nargs=2, type=float, default=[10500, 11500])
    ap.add_argument('--div', type=float, default=4.0)
    ap.add_argument('--radius', type=float, default=60)
    ap.add_argument('--step', type=int, default=1, help='take every STEP-th grid vertex')
    ap.add_argument('--shift', nargs=3, type=float, default=[0, 0, 0],
                    help='control: add (dx, dy, dz) dataset-frame voxels to every mesh vertex before measuring')
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    z0, z1 = a.z
    t0 = time.time()
    quads, n = load_quads(a.dataset, z0, z1, 100)
    print(f'patches {n}, quads {len(quads)}, load {time.time() - t0:.0f}s', flush=True)
    dist = make_dist_fn(quads, a.radius)
    report = {}
    for m in a.meshes:
        x = tifffile.imread(os.path.join(m, 'x.tif')).astype(np.float64) / a.div
        y = tifffile.imread(os.path.join(m, 'y.tif')).astype(np.float64) / a.div
        z = tifffile.imread(os.path.join(m, 'z.tif')).astype(np.float64) / a.div
        valid = (x > 0) & (y > 0) & (z > 0) & (z >= z0) & (z < z1)
        V = np.stack([x[valid], y[valid], z[valid]], -1)[::a.step] + np.asarray(a.shift, np.float64)
        d = dist(V)
        fin = d[np.isfinite(d)]
        h, _ = np.histogram(fin, bins=np.arange(0, 42, 2))
        pct = (h / len(d) * 100).round(1).tolist()
        far = float(np.mean(~np.isfinite(d) | (d > 40)) * 100)
        print(f'{os.path.basename(m)}: grid {x.shape}, window vertices {len(V)}, '
              f'median {np.median(fin):.1f}, <=2.5: {np.mean(d <= 2.5) * 100:.1f}%, <=6: {np.mean(d <= 6) * 100:.1f}%, '
              f'>40 or none: {far:.1f}%', flush=True)
        print('  hist 0..40 step 2 (% of window vertices):', pct, flush=True)
        report[m] = {'n': int(len(V)), 'median': float(np.median(fin)), 'le2.5': float(np.mean(d <= 2.5)),
                     'le6': float(np.mean(d <= 6)), 'gt40_or_none': far / 100, 'hist_pct': pct}
        # distance along z: does the offset drift with z?
        zb = np.linspace(z0, z1, 6)
        rows = []
        for i in range(5):
            sel = (V[:, 2] >= zb[i]) & (V[:, 2] < zb[i + 1]) & np.isfinite(d)
            if sel.sum():
                rows.append((int(zb[i]), int(sel.sum()), round(float(np.median(d[sel])), 1), round(float(np.mean(d[sel] <= 2.5)) * 100, 1)))
        print('  by z band (z_lo, n, median, %<=2.5):', rows, flush=True)
        report[m]['by_z'] = rows
    if a.out:
        json.dump(report, open(a.out, 'w'), indent=1)
    print(f'done {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
