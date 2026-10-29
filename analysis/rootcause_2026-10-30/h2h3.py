"""H2 (multi-winding chains) and H3 (a few bad constraints)."""
import json
import os

import numpy as np
from scipy.stats import fisher_exact

from common import (CKEY, CNAME, G, HAS, HERE, INWIN, PID, RUNS_DIR, SRC, XYZ, Z0, Z1, sets, theta_r,
                    umbilicus_yx)

umb = umbilicus_yx()
struct = json.load(open(os.path.join(HERE, 'pcl_struct.json')))
ours_keys = sorted({str(k) for k in CKEY[SRC == 'ours']}, key=int)


def decimate(pts, spacing=16.0):
    keep = [0]; last = pts[0]
    for i in range(1, len(pts)):
        if i == len(pts) - 1 or np.linalg.norm(pts[i] - last) >= spacing:
            keep.append(i); last = pts[i]
    return np.array(keep)


chains = {}
for k in ours_keys:
    idx = np.where((SRC == 'ours') & (CKEY == k))[0]
    idx = idx[np.argsort(PID[idx])]
    p = XYZ[idx]
    th, r = theta_r(p, umb)
    u = np.unwrap(th)
    step = np.abs(np.diff(th)); step = np.minimum(step, 2 * np.pi - step)  # wrapped |dtheta| between neighbours
    lxy = np.sum(np.hypot(np.diff(p[:, 0]), np.diff(p[:, 1])))
    rec = dict(name=str(CNAME[idx[0]]), n=len(idx), span_full=float(np.degrees(u.max() - u.min())),
               net_full=float(np.degrees(u[-1] - u[0])), r_mean=float(r.mean()), r_min=float(r.min()),
               lxy=float(lxy), span_expected=float(np.degrees(lxy / r.mean())),
               max_step_raw=float(np.degrees(step.max())) if len(step) else 0.0,
               z_range=(float(p[:, 2].min()), float(p[:, 2].max())))
    # in-window strip exactly as the fitter builds it (pcl_struct strip_points), plus its spans
    s = struct.get(f'ours:{k}')
    sp = np.array(s['strip_points']) if s and s['strip_points'] else np.array([], int)
    if len(sp) >= 2:
        q = XYZ[sp]; tq, rq = theta_r(q, umb); uq = np.unwrap(tq)
        st = np.abs(np.diff(tq)); st = np.minimum(st, 2 * np.pi - st)
        rec.update(strip_n=len(sp), span_strip=float(np.degrees(uq.max() - uq.min())),
                   max_step_strip=float(np.degrees(st.max())), strip_r_min=float(rq.min()))
    rec['n_inwin'] = int(np.sum(INWIN[idx]))
    rec['cross_patch'] = bool(s['cross_patch']) if s else False
    rec['n_attached'] = len(s['attached_points']) if s else 0
    rec['n_patch_order'] = len(s['patch_order']) if s else 0
    chains[k] = rec

# ---- re-check the earlier slice-1 claim
s1 = [c for c in chains.values() if c['name'].startswith('20230702185753_line')]
s1m = [c for c in chains.values() if c['name'].startswith('20230702185753_margin')]
print(f'slice-1 text lines: {len(s1)}; span > 360: {sum(c["span_full"] > 360 for c in s1)}; max span '
      f'{max(c["span_full"] for c in s1):.0f} deg; margins: {[(c["name"][-12:], round(c["span_full"])) for c in s1m]}')
allc = list(chains.values())
print(f'all 96: span > 360: {sum(c["span_full"] > 360 for c in allc)}; max {max(c["span_full"] for c in allc):.0f};'
      f' max raw neighbour step {max(c["max_step_raw"] for c in allc):.1f} deg')
print('per chain with >= 2 in-window points (fitter strip) or cross-patch:')
print(' name                                   n   inwin  span_full  net   expected(L/r)  r_mean  r_min  maxstep_raw | strip_n span_strip maxstep_strip | attached patches')
for k, c in chains.items():
    if c['n_inwin'] >= 2 or c['cross_patch']:
        print(f' {c["name"]:<38} {c["n"]:4d} {c["n_inwin"]:5d} {c["span_full"]:9.0f} {c["net_full"]:6.0f} {c["span_expected"]:10.0f}'
              f' {c["r_mean"]:8.0f} {c["r_min"]:6.0f} {c["max_step_raw"]:8.2f} | {c.get("strip_n", 0):5d} {c.get("span_strip", 0):8.0f}'
              f' {c.get("max_step_strip", 0):8.2f} | {c["n_attached"]:4d} {c["n_patch_order"]:3d} {"X" if c["cross_patch"] else ""}')

# ---- H2 rate test: A-satisfied-both patches within 300 voxels, by class of the nearest chain
near_pt = G['nearest_ours_pt']
near_key = np.array([str(CKEY[j]) if j >= 0 else '' for j in near_pt])
d = G['d_ours']
res = {'chains': chains}
for pre, label in (('g', 'GPU'), ('c', 'CPU')):
    st = sets(pre)
    for field in ('span_full', 'span_strip'):
        big = np.array([chains[k].get(field, 0) > 360 if k else False for k in near_key])
        pool = st['Apool'] & (d < 300)
        a = int((st['L'] & pool & big).sum()); b = int((pool & big).sum())
        c_ = int((st['L'] & pool & ~big).sum()); e = int((pool & ~big).sum())
        ga = int((st['G'] & st['Bpool'] & (d < 300) & big).sum()); gb = int((st['Bpool'] & (d < 300) & big).sum())
        gc = int((st['G'] & st['Bpool'] & (d < 300) & ~big).sum()); ge = int((st['Bpool'] & (d < 300) & ~big).sum())
        if b and e:
            orr, p = fisher_exact([[a, b - a], [c_, e - c_]])
        else:
            orr, p = float('nan'), float('nan')
        print(f'{label} H2 [{field} > 360]: L rate near big-span chains {a}/{b} = {a / max(b, 1) * 100:.1f}%, '
              f'near small-span {c_}/{e} = {c_ / max(e, 1) * 100:.1f}%, Fisher OR {orr:.2f} p {p:.3g};'
              f'  G rate big {ga}/{gb}, small {gc}/{ge}')
        res[f'{pre}_{field}'] = dict(L_big=[a, b], L_small=[c_, e], G_big=[ga, gb], G_small=[gc, ge], p=p)

# ---- H3: per-collection satisfaction of our strips in B, and concentration of L patches by nearest chain
sat_by = {}
for run in ('gpufull_armB_s1_n30000', 'gpufull_armB_s2_n30000', 'main_armB_s1_n4000', 'noise_armB_s2_n4000'):
    pc = json.load(open(os.path.join(RUNS_DIR, run, 'satisfied_fitted.json')))['pcls']
    sat_by[run] = {p['name']: (p['satisfied_points'], p['total_points']) for p in pc
                   if p['name'].startswith(('20230702185753', '20260701183145'))}
names = sorted(set().union(*[set(v) for v in sat_by.values()]))
print('\nH3 our collections in the pcls output (satisfied/total strip points):')
for nm in names:
    print(f'  {nm:<38}', '  '.join(f'{sat_by[r].get(nm, ("-", "-"))[0]}/{sat_by[r].get(nm, ("-", "-"))[1]}' for r in sat_by))
key_of = {c['name']: k for k, c in chains.items()}
for pre, runs in (('g', ('gpufull_armB_s1_n30000', 'gpufull_armB_s2_n30000')),
                  ('c', ('main_armB_s1_n4000', 'noise_armB_s2_n4000'))):
    st = sets(pre)
    imperfect = {key_of[nm] for nm in names if any(sat_by[r].get(nm, (1, 1))[0] < sat_by[r].get(nm, (1, 1))[1] for r in runs)}
    print(f'{pre}: imperfect collections {sorted(chains[k]["name"] for k in imperfect)}')
    imp = np.array([k in imperfect for k in near_key])
    pool = st['Apool'] & (d < 300)
    a = int((st['L'] & pool & imp).sum()); b = int((pool & imp).sum())
    c_ = int((st['L'] & pool & ~imp).sum()); e = int((pool & ~imp).sum())
    orr, p = fisher_exact([[a, b - a], [c_, e - c_]]) if b and e else (float('nan'), float('nan'))
    print(f'{pre} H3: L rate near imperfect {a}/{b}, near perfect {c_}/{e}, Fisher OR {orr:.2f} p {p:.3g}')
    # concentration: L patches within 300 voxels by nearest chain, with the pool size per chain
    Lk = near_key[st['L'] & (d < 300)]
    Gk = near_key[st['G'] & (d < 300)]
    tab = []
    for k in sorted(set(near_key[pool]) | set(Lk)):
        tab.append((int(np.sum(Lk == k)), int(np.sum(Gk == k)), int(np.sum(near_key[pool] == k)), chains[k]['name']))
    tab.sort(reverse=True)
    nL = len(Lk)
    print(f'{pre} L patches within 300 voxels: {nL}; by nearest chain (L, G, A-sat pool, name):')
    for row in tab[:8]:
        print('   ', row)
    if nL:
        print(f'   top-1 share {tab[0][0] / nL:.2f}, top-2 share {(tab[0][0] + tab[1][0]) / nL:.2f}')
    res[f'{pre}_H3'] = dict(imperfect=sorted(imperfect), L_imp=[a, b], L_perf=[c_, e], p=p, table=tab)
json.dump(res, open(os.path.join(HERE, 'h2h3_results.json'), 'w'), indent=1, default=str)
