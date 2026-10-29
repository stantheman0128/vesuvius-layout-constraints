"""One figure: net patches lost by distance from our points, and seed-to-seed sensitivity, GPU and CPU."""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from common import FRAC, G, HAS, HERE, SAT

d = G['d_ours']
bins = [0, 100, 300, 600, 1000, 1e9]
labels = ['0-100', '100-300', '300-600', '600-1000', '>1000']
b = np.digitize(d, bins) - 1
fig, axes = plt.subplots(2, 2, figsize=(11, 7), constrained_layout=True)
C_S1, C_S2, C_REF, C_A, C_B = '#2a6fdb', '#e07b28', '#8a8a8a', '#2a6fdb', '#c23b3b'
for row, (pre, label) in enumerate((('g', 'GPU, 30,000 steps (team defaults)'), ('c', 'CPU, 4,000 steps'))):
    a1, a2, b1, b2 = (SAT[pre + x] for x in ('A1', 'A2', 'B1', 'B2'))
    n1, n2, nA, nB, cnt = [], [], [], [], []
    sA, sB = [], []
    for i in range(len(labels)):
        m = HAS & (b == i)
        cnt.append(int(m.sum()))
        n1.append(int((a1 & ~b1 & m).sum()) - int((b1 & ~a1 & m).sum()))
        n2.append(int((a2 & ~b2 & m).sum()) - int((b2 & ~a2 & m).sum()))
        nA.append(int((a1 & ~a2 & m).sum()) - int((a2 & ~a1 & m).sum()))
        nB.append(int((b1 & ~b2 & m).sum()) - int((b2 & ~b1 & m).sum()))
        sA.append(np.abs(FRAC[pre + 'A1'] - FRAC[pre + 'A2'])[m].mean())
        sB.append(np.abs(FRAC[pre + 'B1'] - FRAC[pre + 'B2'])[m].mean())
    x = np.arange(len(labels))
    ax = axes[row, 0]
    ax.bar(x - 0.2, n1, 0.38, color=C_S1, label='arm B vs A, seed 1')
    ax.bar(x + 0.2, n2, 0.38, color=C_S2, label='arm B vs A, seed 2')
    ax.scatter(x, nA, marker='_', s=300, color=C_REF, linewidths=2, label='seed 1 vs 2 within A (noise)', zorder=3)
    ax.scatter(x, nB, marker='x', s=40, color=C_REF, label='seed 1 vs 2 within B (noise)', zorder=3)
    ax.axhline(0, color='black', lw=0.8)
    ax.set_xticks(x, [f'{l}\n(n={c})' for l, c in zip(labels, cnt)], fontsize=8)
    ax.set_ylabel('net patches lost (lost minus gained)')
    ax.set_title(f'{label}: where the patch cost sits', fontsize=10)
    ax.legend(fontsize=7, frameon=False)
    ax2 = axes[row, 1]
    ax2.plot(x, sA, 'o-', color=C_A, label='arm A (human only)')
    ax2.plot(x, sB, 's-', color=C_B, label='arm B (human + ours)')
    ax2.set_xticks(x, labels, fontsize=8)
    ax2.set_ylim(0, None)
    ax2.set_ylabel('mean |fraction seed 1 - seed 2| per patch')
    ax2.set_title(f'{label}: seed-to-seed change (post hoc)', fontsize=10)
    ax2.legend(fontsize=8, frameon=False)
for ax in axes.ravel():
    ax.set_xlabel('patch distance to nearest in-window layout point (voxels)', fontsize=8)
    ax.spines[['top', 'right']].set_visible(False)
out = os.path.join(HERE, 'rootcause_distance.png')
fig.savefig(out, dpi=130)
print(out)
