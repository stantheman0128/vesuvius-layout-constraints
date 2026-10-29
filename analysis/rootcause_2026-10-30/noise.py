"""Noise floor of the primary metric, net-loss decomposition by distance, area-weighted drivers,
and the (post hoc, not pre-registered) seed-sensitivity comparison between arms."""
import numpy as np
from scipy import stats

from common import AREA, FRAC, G, HAS, IDS, SAT, sets

d = G['d_ours']
for pre, label in (('g', 'GPU'), ('c', 'CPU')):
    a1, a2, b1, b2 = (SAT[pre + x] for x in ('A1', 'A2', 'B1', 'B2'))
    cA = np.array([a1.sum(), a2.sum()]); cB = np.array([b1.sum(), b2.sum()])
    w = stats.ttest_ind(cA, cB, equal_var=False)
    pr = stats.ttest_rel(cA, cB)
    print(f'\n=== {label}: satisfied counts A {cA.tolist()} B {cB.tolist()}; Welch t {w.statistic:.2f} p {w.pvalue:.3f};'
          f' paired-by-seed t {pr.statistic:.2f} p {pr.pvalue:.3f}')
    # per-seed churn sign tests, arm pairs and within-arm pairs
    for nm, x, y in (('A1 vs B1', a1, b1), ('A2 vs B2', a2, b2), ('A1 vs A2', a1, a2), ('B1 vs B2', b1, b2)):
        lo, hi = int((x & ~y).sum()), int((~x & y).sum())
        print(f'  {nm}: {lo} lost, {hi} gained, net {lo - hi:+d}, churn {lo + hi}, sign-test p {stats.binomtest(lo, lo + hi, 0.5).pvalue:.3f}')
    # net loss by distance bin, per seed, with the within-arm seed difference as reference
    bins = [0, 100, 300, 1e9]
    b = np.digitize(d, bins) - 1
    print('  net patches lost by distance bin (lost - gained):')
    for i in range(len(bins) - 1):
        m = HAS & (b == i)
        n1 = int((a1 & ~b1 & m).sum()) - int((b1 & ~a1 & m).sum())
        n2 = int((a2 & ~b2 & m).sum()) - int((b2 & ~a2 & m).sum())
        nA = int((a1 & ~a2 & m).sum()) - int((a2 & ~a1 & m).sum())
        nB = int((b1 & ~b2 & m).sum()) - int((b2 & ~b1 & m).sum())
        ch1 = int((a1 != b1)[m].sum()); ch2 = int((a2 != b2)[m].sum())
        print(f'    {bins[i]:>4.0f}-{bins[i + 1]:<5.0f} patches {int(m.sum()):4d}: arm net s1 {n1:+4d} (churn {ch1}), s2 {n2:+4d} (churn {ch2});'
              f' seed net within A {nA:+4d}, within B {nB:+4d}')
    # area-weighted: the largest patches among per-seed flips
    for s in ('1', '2'):
        x, y = SAT[pre + 'A' + s], SAT[pre + 'B' + s]
        lost = np.where(HAS & x & ~y)[0]; gained = np.where(HAS & y & ~x)[0]
        tot = AREA.sum()
        lo = lost[np.argsort(-AREA[lost])][:5]; ga = gained[np.argsort(-AREA[gained])][:5]
        print(f'  seed {s}: area lost {AREA[lost].sum() / tot * 100:.2f} pts, gained {AREA[gained].sum() / tot * 100:.2f} pts;'
              f' top-5 lost = {AREA[lo].sum() / tot * 100:.2f} pts, top-5 gained = {AREA[ga].sum() / tot * 100:.2f} pts')
        for j in lo[:3]:
            print(f'      lost  {str(IDS[j])[:40]:<40} area {AREA[j] / tot * 100:.2f} pts d_ours {d[j]:6.0f}'
                  f'  frac A1 {FRAC[pre + "A1"][j]:.3f} A2 {FRAC[pre + "A2"][j]:.3f} B1 {FRAC[pre + "B1"][j]:.3f} B2 {FRAC[pre + "B2"][j]:.3f}')
    # post hoc: is arm B more seed-sensitive? paired per patch
    fA, fB = a1 != a2, b1 != b2
    onlyB, onlyA = int((fB & ~fA & HAS).sum()), int((fA & ~fB & HAS).sum())
    dA = np.abs(FRAC[pre + 'A1'] - FRAC[pre + 'A2'])[HAS]; dB = np.abs(FRAC[pre + 'B1'] - FRAC[pre + 'B2'])[HAS]
    wil = stats.wilcoxon(dB, dA)
    print(f'  POST HOC seed sensitivity: patches flipping between seeds only in B {onlyB}, only in A {onlyA},'
          f' sign-test p {stats.binomtest(onlyB, onlyB + onlyA, 0.5).pvalue:.2g}; |frac s1 - s2| mean A {dA.mean():.4f}'
          f' B {dB.mean():.4f}, Wilcoxon p {wil.pvalue:.2g}')
    for lo_, hi_ in ((0, 100), (100, 300), (300, 1e9)):
        m = HAS & (d >= lo_) & (d < hi_)
        print(f'      d {lo_:>4}-{hi_:<6}: mean |s1-s2| A {np.abs(FRAC[pre + "A1"] - FRAC[pre + "A2"])[m].mean():.4f}'
              f' B {np.abs(FRAC[pre + "B1"] - FRAC[pre + "B2"])[m].mean():.4f}')
    # within 100 voxels: L vs G sign test
    st = sets(pre)
    nl, ng = int((st['L'] & (d < 100)).sum()), int((st['G'] & (d < 100)).sum())
    print(f'  both-seed L vs G within 100 voxels: {nl} vs {ng}, sign-test p {stats.binomtest(nl, nl + ng, 0.5).pvalue:.3f};'
          f' beyond 100: {int((st["L"] & (d >= 100)).sum())} vs {int((st["G"] & (d >= 100)).sum())}')
