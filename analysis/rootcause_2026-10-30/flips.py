"""Per-patch flip counts between arms and seeds. Writes flips.npz next to this script."""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, '..', '..', 'runs')
RUNS = {
    'gA1': 'gpufull_armA_s1_n30000', 'gA2': 'gpufull_armA_s2_n30000',
    'gB1': 'gpufull_armB_s1_n30000', 'gB2': 'gpufull_armB_s2_n30000',
    'cA1': 'main_armA_s1_n4000', 'cA2': 'noise_armA_s2_n4000',
    'cB1': 'main_armB_s1_n4000', 'cB2': 'noise_armB_s2_n4000',
}
THR = 0.95


def load(run):
    d = json.load(open(os.path.join(REPO, run, 'satisfied_fitted.json')))
    m = json.load(open(os.path.join(REPO, run, 'satisfaction_metrics_fitted.json')))['summary']
    return d, m


ids = None
frac, area, sat = {}, {}, {}
for key, run in RUNS.items():
    d, m = load(run)
    pts = sorted(d['patches'], key=lambda p: p['id'])
    pid = [p['id'] for p in pts]
    assert len(set(pid)) == len(pid)
    if ids is None:
        ids = pid
    assert pid == ids, f'patch set differs in {run}'
    f = np.array([p['fraction'] for p in pts])
    a = np.array([p['total_area'] for p in pts])
    sa = np.array([p['satisfied_area'] for p in pts])
    # fraction is satisfied_area / total_area where total_area > 0
    ok = a > 0
    assert np.allclose(f[ok], sa[ok] / a[ok], atol=1e-6), run
    # the fitter counts zero-area patches as satisfied (0 >= 0.95 * 0); they never flip
    s = (f >= THR) | ~ok
    s_alt = sa >= THR * a
    print(f'{key} {run}: sat {s.sum()} (alt {s_alt.sum()}) summary {m["satisfied_patches"]}/{m["total_patches"]}'
          f'  area-weighted {a[s].sum() / a.sum():.4f} summary {m["satisfied_patches_area_weighted_fraction"]:.4f}')
    frac[key], area[key], sat[key] = f, a, s

for k in area:
    assert np.array_equal(area[k], area['gA1']), f'total_area differs for {k}'
A = area['gA1']
print(f'patches {len(ids)}, with in-window area {np.sum(A > 0)}, total area {A.sum():.0f}')


def cnt(mask):
    return f'{int(mask.sum()):4d} patches, area {A[mask].sum() / A.sum() * 100:5.2f}%'


for pre in ('g', 'c'):
    a1, a2, b1, b2 = (sat[pre + x] for x in ('A1', 'A2', 'B1', 'B2'))
    print(f'\n=== {"GPU 30k" if pre == "g" else "CPU 4k"}')
    print('per seed, A sat & B not  s1:', cnt(a1 & ~b1), '| s2:', cnt(a2 & ~b2))
    print('per seed, B sat & A not  s1:', cnt(b1 & ~a1), '| s2:', cnt(b2 & ~a2))
    L = a1 & a2 & ~b1 & ~b2
    G = b1 & b2 & ~a1 & ~a2
    print('both seeds L (A sat, B not):', cnt(L))
    print('both seeds G (B sat, A not):', cnt(G))
    print('noise A1 vs A2: A1 only', cnt(a1 & ~a2), '| A2 only', cnt(a2 & ~a1))
    print('noise B1 vs B2: B1 only', cnt(b1 & ~b2), '| B2 only', cnt(b2 & ~b1))
    print('seed-consistent (sat s1 both arms, not s2 both arms):', cnt(a1 & b1 & ~a2 & ~b2))
    print('seed-consistent (sat s2 both arms, not s1 both arms):', cnt(a2 & b2 & ~a1 & ~b1))
    print('stable all four:', cnt(a1 & a2 & b1 & b2))
    # sign test on L vs G
    from scipy.stats import binomtest
    n = int(L.sum() + G.sum())
    if n:
        print(f'sign test L vs G: {int(L.sum())} vs {int(G.sum())}, p = {binomtest(int(L.sum()), n, 0.5).pvalue:.3g}')

np.savez(os.path.join(HERE, 'flips.npz'), ids=np.array(ids), area=A,
         **{f'frac_{k}': v for k, v in frac.items()})
