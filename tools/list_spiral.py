"""List the wanted parts of the PHercParis4 spiral dataset into a JSON manifest.

Usage: python -I list_spiral.py OUT_MANIFEST.json
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s3pub

BASE = 'PHercParis4/representations/spiral/20260411134726-spiral-dataset-20261019084150/'
SUBDIRS = ['outer_shell/', 'winding_inference/', 'eval_fibers/', 'verified_patches/']


def main(out):
    t0 = time.time()
    objs = []
    for key, size in s3pub.list_prefix(BASE, delimiter='/'):
        objs.append({'key': key, 'size': size})
    for sub in SUBDIRS:
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
    main(sys.argv[1])
