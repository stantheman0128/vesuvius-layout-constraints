"""Compare every wanted object in the S3 listing against the local copy by size.

Usage: python -I verify.py LISTING.json DEST REGEX
Prints per-directory counts and bytes, then any missing or mismatched files.
Exit code 1 if anything is missing or mismatched.
"""
import os
import re
import sys
import json
import collections


def main(listing, dest, regex):
    m = json.load(open(listing))
    base = m['base']
    rx = re.compile(regex)
    per = collections.defaultdict(lambda: [0, 0])
    bad = []
    for o in m['objects']:
        rel = o['key'][len(base):]
        if not rx.search(rel):
            continue
        path = os.path.join(dest, *rel.split('/'))
        group = rel.split('/')[0] if '/' in rel else '(root)'
        if not os.path.isfile(path):
            bad.append(('missing', rel, o['size'], None))
            continue
        got = os.path.getsize(path)
        if got != o['size']:
            bad.append(('size', rel, o['size'], got))
            continue
        per[group][0] += 1
        per[group][1] += got
    for g, (n, b) in sorted(per.items()):
        print(f'{g}: {n} files ok, {b} bytes ({b / 2**30:.4f} GiB)')
    tot_n = sum(v[0] for v in per.values())
    tot_b = sum(v[1] for v in per.values())
    print(f'TOTAL ok: {tot_n} files, {tot_b} bytes ({tot_b / 2**30:.4f} GiB)')
    print(f'missing or mismatched: {len(bad)}')
    for kind, rel, want, got in bad[:50]:
        print(f'  {kind} {rel} want {want} got {got}')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main(*sys.argv[1:4])
