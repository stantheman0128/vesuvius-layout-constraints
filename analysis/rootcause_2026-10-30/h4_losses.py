"""H4b: fit.log loss terms, A vs B, mean over the last 5,000 logged steps, with the seed spread as noise."""
import os
import re

import numpy as np

from common import RUNS_DIR

RUNS = {'gA1': 'gpufull_armA_s1_n30000', 'gA2': 'gpufull_armA_s2_n30000',
        'gB1': 'gpufull_armB_s1_n30000', 'gB2': 'gpufull_armB_s2_n30000',
        'cA1': 'main_armA_s1_n4000', 'cA2': 'noise_armA_s2_n4000',
        'cB1': 'main_armB_s1_n4000', 'cB2': 'noise_armB_s2_n4000'}
pat = re.compile(r'^step (\d+): (.*)$')


def parse(path):
    rows = {}
    for line in open(path, encoding='utf-8', errors='replace'):
        m = pat.match(line.strip())
        if not m:
            continue
        step = int(m.group(1))
        terms = dict((k.strip(), float(v)) for k, v in (kv.split('=') for kv in m.group(2).split(',')))
        rows[step] = terms
    return rows


data = {k: parse(os.path.join(RUNS_DIR, r, 'fit.log')) for k, r in RUNS.items()}
for k, rows in data.items():
    steps = sorted(rows)
    print(f'{k}: {len(steps)} logged steps, first {steps[0]}, last {steps[-1]}')

for pre, last, window in (('g', 30000, 5000), ('c', 4000, 1000)):
    print(f'\n=== {"GPU" if pre == "g" else "CPU"}: mean of logged values over steps >= {last - window}')
    keys = list(data[pre + 'A1'][min(data[pre + 'A1'])].keys())
    print(f'{"term":<40} {"A1":>9} {"A2":>9} {"B1":>9} {"B2":>9} | {"B-A mean":>9} {"seed spread A":>13} {"seed spread B":>13}  sd/sqrt(n) per run')
    for t in keys:
        vals, ses = {}, {}
        for r in ('A1', 'A2', 'B1', 'B2'):
            rows = data[pre + r]
            v = np.array([rows[s][t] for s in sorted(rows) if s >= last - window and t in rows[s]])
            vals[r] = v.mean(); ses[r] = v.std(ddof=1) / np.sqrt(len(v))
        dab = (vals['B1'] + vals['B2']) / 2 - (vals['A1'] + vals['A2']) / 2
        sa = abs(vals['A1'] - vals['A2']); sb = abs(vals['B1'] - vals['B2'])
        flag = ' <-- B-A beyond both seed spreads' if abs(dab) > max(sa, sb) and abs(dab) > 2 * max(ses.values()) else ''
        print(f'{t:<40} {vals["A1"]:9.3f} {vals["A2"]:9.3f} {vals["B1"]:9.3f} {vals["B2"]:9.3f} | {dab:+9.3f} {sa:13.3f} {sb:13.3f}'
              f'  {max(ses.values()):.3f}{flag}')
