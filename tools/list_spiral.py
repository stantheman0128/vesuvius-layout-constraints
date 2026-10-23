"""List the wanted parts of the PHercParis4 spiral dataset into a JSON manifest.

Usage: python -I list_spiral.py OUT_MANIFEST.json [--with-lasagna]
--with-lasagna also lists the packed normals (las_008_nx pair, 9.52 GiB) and gradient magnitude
(las_008_grad_mag, 4.76 GiB) that the fitter's default input_use_normals / input_use_gradient_magnitude
need; the CPU arms ran without them.
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s3pub

BASE = 'PHercParis4/representations/spiral/20260411134726-spiral-dataset-20261019084150/'
SUBDIRS = ['outer_shell/', 'winding_inference/', 'eval_fibers/', 'verified_patches/']
LASAGNA = ['lasagna_inputs/las_008_nx.ome.zarr.respool_g4_pair/', 'lasagna_inputs/las_008_grad_mag.ome.zarr.respool_g4/']


def main(out, with_lasagna=False):
    t0 = time.time()
    objs = []
    for key, size in s3pub.list_prefix(BASE, delimiter='/'):
        objs.append({'key': key, 'size': size})
    for sub in SUBDIRS + (LASAGNA if with_lasagna else []):
        n0 = len(objs)
        for key, size in s3pub.list_prefix(
                BASE + sub,
                progress=lambda p, s=sub: print(f'  {s} {p} pages', flush=True)):
            objs.append({'key': key, 'size': size})
        print(f'{sub}: {len(objs) - n0} objects', flush=True)
    with open(out, 'w') as f:
        json.dump({'base': BASE, 'listed_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                   'objects': objs}, f)
    print(f'{len(objs)} objects, {sum(o["size"] for o in objs)} bytes, {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main(sys.argv[1], with_lasagna='--with-lasagna' in sys.argv[2:])
