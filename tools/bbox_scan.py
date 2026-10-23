"""Scan downloaded verified_patches meta.json bboxes: axis ranges and z-window intersection.

Usage: python -I bbox_scan.py LISTING.json META_ROOT ZLO ZHI [KEEP_OUT.txt]
META_ROOT is the directory containing verified_patches/.
"""
import os
import sys
import json
import collections

import numpy as np


def main(listing, meta_root, zlo, zhi, keep_out=None):
    m = json.load(open(listing))
    base = m['base']
    size = collections.defaultdict(int)
    for o in m['objects']:
        r = o['key'][len(base):]
        if r.startswith('verified_patches/') and r.count('/') == 2:
            size[r.split('/')[1]] += o['size']
    root = os.path.join(meta_root, 'verified_patches')
    bb, nobbox, keys, shapes = {}, [], collections.Counter(), collections.Counter()
    for d in sorted(os.listdir(root)):
        p = os.path.join(root, d, 'meta.json')
        if not os.path.isfile(p):
            continue
        j = json.load(open(p))
        keys.update(j.keys())
        b = j.get('bbox')
        if b is None:
            nobbox.append(d)
            continue
        shapes[str(np.shape(b))] += 1
        bb[d] = np.array(b, dtype=float)
    print('patch dirs', len(bb) + len(nobbox), 'without bbox', len(nobbox), nobbox[:5])
    print('bbox shapes', dict(shapes))
    print('meta keys', keys.most_common(25))
    names = list(bb)
    A = np.stack([bb[d] for d in names])
    for ax in range(3):
        lo, hi = A[:, 0, ax], A[:, 1, ax]
        print(f'bbox axis{ax}: min {lo.min():.0f} p1 {np.percentile(lo, 1):.0f} '
              f'median_lo {np.median(lo):.0f} p99_hi {np.percentile(hi, 99):.0f} max {hi.max():.0f}')
    print('rows with min>max on some axis:', int((A[:, 0, :] > A[:, 1, :]).any(axis=1).sum()))
    invalid = (A == -1).all(axis=(1, 2))
    print('all -1 bboxes:', int(invalid.sum()))
    zmin, zmax = A[:, 0, 2], A[:, 1, 2]
    hit = (zmax >= zlo) & (zmin < zhi) & ~invalid
    kept = [d for d, h in zip(names, hit) if h]
    print(f'z (axis2) window [{zlo}, {zhi}): {len(kept)} patches, '
          f'{sum(size[d] for d in kept)} bytes total (all files in those dirs)')
    for ax in (0, 1):
        h = (A[:, 1, ax] >= zlo) & (A[:, 0, ax] < zhi) & ~invalid
        print(f'  (same window on axis{ax} would give {int(h.sum())})')
    print('all patches total bytes', sum(size.values()))
    if keep_out:
        with open(keep_out, 'w') as f:
            f.write('\n'.join(kept + nobbox) + '\n')
        print('wrote', keep_out, len(kept) + len(nobbox), '(kept + no-bbox dirs)')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]),
         sys.argv[5] if len(sys.argv) > 5 else None)
