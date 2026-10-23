"""Minimal public-S3 helpers for the Vesuvius open-data bucket (no auth, stdlib only)."""
import os
import time
import random
import http.client
import threading
import urllib.parse
import xml.etree.ElementTree as ET

HOST = 'vesuvius-challenge-open-data.s3.amazonaws.com'
NS = '{http://s3.amazonaws.com/doc/2006-03-01/}'
_local = threading.local()


def _conn():
    c = getattr(_local, 'conn', None)
    if c is None:
        c = http.client.HTTPSConnection(HOST, timeout=60)
        _local.conn = c
    return c


def _drop_conn():
    c = getattr(_local, 'conn', None)
    if c is not None:
        try:
            c.close()
        except Exception:
            pass
    _local.conn = None


def request(path, attempts=8):
    """GET path; returns body bytes. Retries 5xx and connection errors with backoff."""
    last = None
    for i in range(attempts):
        try:
            c = _conn()
            c.request('GET', path, headers={'Connection': 'keep-alive'})
            r = c.getresponse()
            body = r.read()
            if r.status == 200:
                return body
            if r.status >= 500 or r.status == 429:
                last = RuntimeError(f'HTTP {r.status} for {path}')
                _drop_conn()
            else:
                raise RuntimeError(f'HTTP {r.status} for {path}: {body[:200]!r}')
        except (OSError, http.client.HTTPException) as e:
            last = e
            _drop_conn()
        time.sleep(min(30.0, 0.5 * 2 ** i) * (0.5 + random.random()))
    raise RuntimeError(f'giving up on {path}: {last}')


def list_prefix(prefix, delimiter=None, progress=None):
    """Yield (key, size) for every object under prefix (ListObjectsV2)."""
    token = None
    pages = 0
    while True:
        q = {'list-type': '2', 'prefix': prefix, 'max-keys': '1000'}
        if delimiter:
            q['delimiter'] = delimiter
        if token:
            q['continuation-token'] = token
        root = ET.fromstring(request('/?' + urllib.parse.urlencode(q)))
        for c in root.iter(NS + 'Contents'):
            yield c.find(NS + 'Key').text, int(c.find(NS + 'Size').text)
        pages += 1
        if progress and pages % 25 == 0:
            progress(pages)
        if root.findtext(NS + 'IsTruncated') != 'true':
            return
        token = root.findtext(NS + 'NextContinuationToken')


def download(key, dest, size):
    """Download key to dest unless dest already has the expected size. Returns 'skip' or 'get'."""
    if os.path.exists(dest) and os.path.getsize(dest) == size:
        return 'skip'
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    for attempt in range(3):
        body = request('/' + urllib.parse.quote(key))
        if len(body) == size:
            break
    else:
        raise RuntimeError(f'size mismatch for {key}: got {len(body)} want {size}')
    tmp = dest + '.part'
    with open(tmp, 'wb') as f:
        f.write(body)
    os.replace(tmp, dest)
    return 'get'
