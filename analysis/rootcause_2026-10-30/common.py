"""Shared loading for the root-cause analysis scripts."""
import json
import os

import numpy as np
import scipy.interpolate
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
# Spiral dataset root (the folder holding phercparis4/); see tasks/LOCAL_CPU_SETUP.md.
DS = os.environ.get('SPIRAL_DS', os.path.join(HERE, '..', '..', 'data', 'spiral_datasets'))
RUNS_DIR = os.path.join(HERE, '..', '..', 'runs')
Z0, Z1 = 10500.0, 11500.0
THR = 0.95

fl = np.load(os.path.join(HERE, 'flips.npz'))
IDS = fl['ids']
AREA = fl['area']
FRAC = {k[5:]: fl[k] for k in fl.files if k.startswith('frac_')}
HAS = AREA > 0
SAT = {k: (v >= THR) | ~HAS for k, v in FRAC.items()}

G = np.load(os.path.join(HERE, 'geom.npz'))
assert list(G['ids']) == list(IDS)
P = np.load(os.path.join(HERE, 'points.npz'))
SRC, CKEY, CNAME, PID, XYZ = P['src'], P['ckey'], P['cname'], P['pid'], P['xyz']
INWIN = (XYZ[:, 2] >= Z0) & (XYZ[:, 2] < Z1)
LINK = np.load(os.path.join(HERE, 'link.npz'))['link']


def sets(pre):
    """Flip sets for 'g' (GPU) or 'c' (CPU)."""
    a1, a2, b1, b2 = (SAT[pre + x] for x in ('A1', 'A2', 'B1', 'B2'))
    return {
        'L': HAS & a1 & a2 & ~b1 & ~b2,
        'G': HAS & b1 & b2 & ~a1 & ~a2,
        'S': HAS & a1 & a2 & b1 & b2,
        'Apool': HAS & a1 & a2,            # pool for L
        'Bpool': HAS & b1 & b2,            # pool for G
        'NA': HAS & (a1 != a2),            # within-arm noise flips, arm A
        'NB': HAS & (b1 != b2),
        'L1': HAS & a1 & ~b1, 'L2': HAS & a2 & ~b2,
        'G1': HAS & b1 & ~a1, 'G2': HAS & b2 & ~a2,
    }


def umbilicus_yx():
    data = json.load(open(f'{DS}/phercparis4/umbilicus.json'))
    pts = sorted(data['control_points'], key=lambda p: p['z'])
    zs = np.asarray([p['z'] for p in pts], dtype=np.float64)
    yxs = np.asarray([(p['y'], p['x']) for p in pts], dtype=np.float64)
    return scipy.interpolate.interp1d(zs, yxs, axis=0, fill_value='extrapolate')


def theta_r(xyz, umb=None):
    umb = umb or umbilicus_yx()
    yx = umb(xyz[:, 2])
    dy = xyz[:, 1] - yx[:, 0]
    dx = xyz[:, 0] - yx[:, 1]
    return np.arctan2(dy, dx), np.hypot(dx, dy)


def patch_min_dist(points):
    """Per-patch min distance from the stride-2 in-window vertex subsample to a point set."""
    sub, off = G['sub_xyz'], G['sub_off']
    if len(points) == 0:
        return np.full(len(off) - 1, np.inf)
    d, _ = cKDTree(points).query(sub, k=1)
    out = np.minimum.reduceat(d, off[:-1])
    out[np.diff(off) == 0] = np.inf
    return out


def auc_closer(d_test, d_ref):
    """P(random test patch is closer than random reference patch), ties count half."""
    from scipy.stats import mannwhitneyu
    u = mannwhitneyu(d_ref, d_test, alternative='two-sided').statistic
    return u / (len(d_test) * len(d_ref))
