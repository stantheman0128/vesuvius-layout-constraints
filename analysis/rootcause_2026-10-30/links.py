"""Resolve point-to-patch links (largest-area policy) and rebuild the fitter's pcl classification.

Checks the replica against the counts printed in fit.log, then writes pcl_struct.json: per collection
the attached points, the patch order, the adjacent pairs used by the rel_winding loss, and the
in-window unattached strip (longest id-sorted run in the window, decimated at 16 voxels).
"""
import json
import os
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
Z0, Z1 = 10500.0, 11500.0

P = np.load(os.path.join(HERE, 'points.npz'))
src, ckey, cname, pid, xyz = P['src'], P['ckey'], P['cname'], P['pid'], P['xyz']
G = np.load(os.path.join(HERE, 'geom.npz'))
ids, area_full = list(G['ids']), G['area_full']
cands = json.load(open(os.path.join(HERE, 'link_cands.json')))

by_point = defaultdict(list)
for pi, pa, d in cands:
    by_point[pi].append((pa, d))
link = np.full(len(xyz), -1, np.int64)
link_d = np.full(len(xyz), np.nan)
n_multi = 0
for pi, lst in by_point.items():
    n_multi += len(lst) > 1
    pa, d = sorted(lst, key=lambda t: (-area_full[t[0]], t[1]))[0]
    link[pi], link_d[pi] = pa, d
print(f'points attached: {int((link >= 0).sum())} of {len(xyz)}; with >1 candidate patch: {n_multi}')
for s in np.unique(src):
    m = src == s
    print(f'  {s}: attached {int((link[m] >= 0).sum())} of {int(m.sum())}')


def decimate(pts, spacing=16.0):
    keep = [0]; last = pts[0]
    for i in range(1, len(pts)):
        if i == len(pts) - 1 or np.linalg.norm(pts[i] - last) >= spacing:
            keep.append(i); last = pts[i]
    return keep


struct = {}
groups = defaultdict(list)
for i in range(len(xyz)):
    groups[(str(src[i]), str(ckey[i]))].append(i)

for arm in ('A', 'B'):
    cross = defaultdict(int); unatt = defaultdict(int); dropped = 0
    for (s, k), idx in groups.items():
        if arm == 'A' and s == 'ours':
            continue
        fam = {'hsame': 'same_windings', 'ours': 'same_windings', 'hrel': 'relative_windings', 'habs': 'abs_winding'}[s]
        idx = sorted(idx, key=lambda j: pid[j])
        att = [j for j in idx if link[j] >= 0]
        n_un = len(idx) - len(att)
        if s == 'habs':
            cross[fam] += 1
            continue
        if len(att) >= 2:
            cross[fam] += 1
        if n_un >= 1:
            # longest contiguous id-sorted run of points in [Z0, Z1) (z margin 0)
            best, run_start, bs, be = 0, 0, 0, 0
            for t, j in enumerate(idx):
                if Z0 <= xyz[j, 2] < Z1:
                    if t + 1 - run_start > be - bs:
                        bs, be = run_start, t + 1
                else:
                    run_start = t + 1
            run = idx[bs:be]
            if len(run) < 2:
                dropped += 1
            else:
                unatt[fam] += 1
        if arm == 'B':
            order = []
            for j in att:
                if link[j] not in order:
                    order.append(int(link[j]))
            strip = []
            if n_un >= 1 and len(run) >= 2:
                strip = [run[t] for t in decimate(xyz[run])]
            struct[f'{s}:{k}'] = {
                'src': s, 'key': k, 'name': str(cname[idx[0]]), 'n_points': len(idx),
                'n_inwin': int(sum(Z0 <= xyz[j, 2] < Z1 for j in idx)),
                'attached_points': [int(j) for j in att], 'attached_patch': [int(link[j]) for j in att],
                'patch_order': order, 'pairs': list(zip(order, order[1:])) if len(att) >= 2 else [],
                'cross_patch': len(att) >= 2 or s == 'habs', 'strip_points': [int(j) for j in strip],
                'point_index_sorted': [int(j) for j in idx],
            }
    print(f'arm {arm}: cross-patch {sum(cross.values())} {dict(cross)}; unattached {sum(unatt.values())} {dict(unatt)};'
          f' dropped unattached with <2 points in z-roi {dropped}')

json.dump(struct, open(os.path.join(HERE, 'pcl_struct.json'), 'w'))
np.savez(os.path.join(HERE, 'link.npz'), link=link, link_d=link_d)
