"""For each adjacent patch pair tied by one of our chains: what the chain says (angle travelled between the
attachments, seam crossings) against what the geometry says (radial offset between the two patches)."""
import json
import os

import numpy as np

from common import HERE, XYZ, theta_r, umbilicus_yx

umb = umbilicus_yx()
struct = json.load(open(os.path.join(HERE, 'pcl_struct.json')))
h5 = json.load(open(os.path.join(HERE, 'h5_results.json')))
geom = {(r['chain'], r['a'], r['b']): r for r in h5['pairs']}

rows = []
for s in struct.values():
    if s['src'] not in ('ours', 'hsame') or not s['pairs']:
        continue
    order = np.array(s['point_index_sorted'])
    th, r = theta_r(XYZ[order], umb)
    u = np.unwrap(th)
    seam = np.concatenate([[0], np.cumsum(np.abs(np.diff(th)) > np.pi)])  # wrapped-angle seam crossings so far
    pos = {int(j): t for t, j in enumerate(order)}
    att = np.array(s['attached_points']); patch = np.array(s['attached_patch'])
    for a, b in s['pairs']:
        ia = np.array([pos[int(j)] for j in att[patch == a]]); ib = np.array([pos[int(j)] for j in att[patch == b]])
        dth = np.degrees(u[ib][None, :] - u[ia][:, None])            # chain-unwrapped angle travelled a -> b
        cross = seam[ib][None, :] - seam[ia][:, None]
        dr = r[ib][None, :] - r[ia][:, None]
        dz = XYZ[order][ib][None, :, 2] - XYZ[order][ia][:, None, 2]
        g = geom[(s['name'], a, b)]
        rows.append(dict(src=s['src'], chain=s['name'], a=a, b=b, cls=g['cls'], dr_geom=g['dr_band'],
                         dth_med=float(np.median(dth)), dth_min=float(np.min(np.abs(dth))), dth_max=float(np.max(np.abs(dth))),
                         cross=sorted(set(cross.ravel().tolist())), dr_pts=float(np.median(dr)), dz=float(np.median(dz)),
                         n_a=len(ia), n_b=len(ib), gpu=g['gpu'], cpu=g['cpu']))
print(f'{"chain":<30} {"pair":>10} {"class":<14} {"dtheta a->b (median, |min|..|max|)":>34} {"seam x":>8} {"dr pts":>7} {"dr geom":>13} {"dz":>6}  GPU / CPU')
for r in rows:
    cls = {'overlap, same surface': 'overlap', 'parallel at 6-30 vx, no coincident overlap': 'PARALLEL',
           'touch at edge': 'edge', 'disjoint (> 30 vx apart)': 'disjoint'}[r['cls']]
    print(f"{r['chain'][-30:]:<30} {r['a']:4d}-{r['b']:<5d} {cls:<14} {r['dth_med']:+10.0f} ({r['dth_min']:5.0f}..{r['dth_max']:5.0f})"
          f"{str(r['cross']):>12} {r['dr_pts']:+7.1f} {r['dr_geom'][0]:+6.1f}/{r['dr_geom'][1]:+6.1f} {r['dz']:+6.0f}  {r['gpu']} {r['cpu']}")
json.dump(rows, open(os.path.join(HERE, 'pairs_chain.json'), 'w'), indent=1)
