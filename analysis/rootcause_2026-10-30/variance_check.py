"""POST HOC, not pre-registered: can extra seed-to-seed variance alone, with no shift in the mean,
lower the satisfied-patch count? Symmetric-noise simulation on the observed fractions."""
import numpy as np
from common import FRAC, HAS, SAT

rng = np.random.default_rng(7)
for pre, label in (('g', 'GPU'), ('c', 'CPU')):
    A1, A2, B1, B2 = (FRAC[pre + x][HAS] for x in ('A1', 'A2', 'B1', 'B2'))
    mA, mB = (A1 + A2) / 2, (B1 + B2) / 2
    print(f'{label}: mean fraction A {mA.mean():.4f} B {mB.mean():.4f}; area-free mean shift B-A {np.mean(mB - mA):+.4f}')
    for lo, hi in ((0.90, 0.93), (0.93, 0.95), (0.95, 0.97), (0.97, 0.99), (0.99, 1.001)):
        print(f'   patches with A mean fraction in [{lo:.2f},{hi:.2f}): {int(((mA >= lo) & (mA < hi)).sum())}')
    # noise model: run = mu + e, e drawn from the arm's own seed-difference distribution (B1-B2)/sqrt2 with random sign
    eA = (A1 - A2) / np.sqrt(2); eB = (B1 - B2) / np.sqrt(2)
    mu = mA  # shared mean, so any count difference comes from variance only
    cnt = {'A': [], 'B': []}
    for t in range(2000):
        for arm, e in (('A', eA), ('B', eB)):
            draw = rng.choice(e, len(mu)) * rng.choice([-1, 1], len(mu))
            cnt[arm].append(np.sum(np.clip(mu + draw, 0, 1) >= 0.95))
    dA, dB = np.mean(cnt['A']), np.mean(cnt['B'])
    obsA = (SAT[pre + 'A1'][HAS].sum() + SAT[pre + 'A2'][HAS].sum()) / 2
    obsB = (SAT[pre + 'B1'][HAS].sum() + SAT[pre + 'B2'][HAS].sum()) / 2
    print(f'   simulated satisfied count, same mean, A-level noise {dA:.1f}, B-level noise {dB:.1f}: variance-only loss {dA - dB:.1f} patches'
          f' (sd of B-A over draws {np.std(np.array(cnt["A"]) - np.array(cnt["B"])):.1f}); observed mean loss {obsA - obsB:.1f}')

print('\nper-patch noise model: each patch keeps its own seed difference, only the sign is random (heteroscedastic)')
for pre, label in (('g', 'GPU'), ('c', 'CPU')):
    A1, A2, B1, B2 = (FRAC[pre + x][HAS] for x in ('A1', 'A2', 'B1', 'B2'))
    mu = (A1 + A2) / 2
    eA = np.abs(A1 - A2) / 2; eB = np.abs(B1 - B2) / 2   # run = mu +- e reproduces each arm's own seed spread
    cA = np.array([np.sum(np.clip(mu + eA * rng.choice([-1, 1], len(mu)), 0, 1) >= 0.95) for _ in range(4000)])
    cB = np.array([np.sum(np.clip(mu + eB * rng.choice([-1, 1], len(mu)), 0, 1) >= 0.95) for _ in range(4000)])
    obsA = (SAT[pre + 'A1'][HAS].sum() + SAT[pre + 'A2'][HAS].sum()) / 2
    obsB = (SAT[pre + 'B1'][HAS].sum() + SAT[pre + 'B2'][HAS].sum()) / 2
    print(f'{label}: simulated count with A-level spread {cA.mean():.1f} (observed A {obsA:.1f}), with B-level spread {cB.mean():.1f};'
          f' variance-only loss {cA.mean() - cB.mean():.1f} (sd {np.std(cA - cB):.1f}); observed loss {obsA - obsB:.1f}')
    # and the reverse attribution: B's own mean with A-level spread
    muB = (B1 + B2) / 2
    cBA = np.array([np.sum(np.clip(muB + eA * rng.choice([-1, 1], len(muB)), 0, 1) >= 0.95) for _ in range(4000)])
    print(f'      B mean with A-level spread {cBA.mean():.1f}: loss from the shift in per-patch means alone {cA.mean() - cBA.mean():.1f}')
