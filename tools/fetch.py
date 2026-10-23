"""Download objects from an S3 listing manifest into DEST, mirroring keys relative to the base.

Usage: python -I fetch.py MANIFEST.json DEST [--regex REGEX] [--keys KEYFILE] [--workers 32]
Files whose local size already equals the listed size are not re-downloaded.
"""
import os
import re
import sys
import json
import time
import argparse
import concurrent.futures

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s3pub


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('manifest')
    ap.add_argument('dest')
    ap.add_argument('--regex')
    ap.add_argument('--keys', help='file with one relative key per line')
    ap.add_argument('--workers', type=int, default=32)
    a = ap.parse_args()
    m = json.load(open(a.manifest))
    base = m['base']
    objs = [o for o in m['objects'] if o['key'].startswith(base)]
    if a.regex:
        rx = re.compile(a.regex)
        objs = [o for o in objs if rx.search(o['key'][len(base):])]
    if a.keys:
        want = set(line.strip() for line in open(a.keys) if line.strip())
        objs = [o for o in objs if o['key'][len(base):] in want]
    total = sum(o['size'] for o in objs)
    print(f'{len(objs)} objects, {total} bytes', flush=True)
    t0 = time.time()
    counts = {'get': 0, 'skip': 0, 'fail': 0}
    failures = []

    def job(o):
        rel = o['key'][len(base):]
        return s3pub.download(o['key'], os.path.join(a.dest, *rel.split('/')), o['size'])

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, a.workers)) as ex:
        futs = {ex.submit(job, o): o for o in objs}
        for i, f in enumerate(concurrent.futures.as_completed(futs), 1):
            try:
                counts[f.result()] += 1
            except Exception as e:
                counts['fail'] += 1
                failures.append((futs[f]['key'], str(e)))
            if i % 2000 == 0:
                print(f'  {i}/{len(objs)} {counts} {time.time() - t0:.0f}s', flush=True)
    print(f'done {counts} in {time.time() - t0:.0f}s', flush=True)
    for k, e in failures[:20]:
        print('FAIL', k, e)
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
