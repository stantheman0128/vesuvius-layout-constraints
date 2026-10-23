#!/bin/sh
# Post-hoc noise check: seed 2 for both arms, same window and schedule as the main runs.
# Not called for by tasks/PROTOCOL.md (primary differed by 2.2 pt); run to put a bar on run-to-run spread.
cd "C:/Users/stans/Projects/_scratch/2026-10-22-layout-constraints" || exit 1
PY="C:/Users/stans/Projects/math-science-bounty-lab/experiments/vesuvius_192/.venv/Scripts/python.exe"
"$PY" tools/run_arm.py --arm A --dataset data/spiral_datasets/phercparis4 --steps 4000 --seed 2 --out runs --tag noise > runs/noise_armA.stdout 2>&1
"$PY" tools/run_arm.py --arm B --dataset data/spiral_datasets/phercparis4_plus_layout --steps 4000 --seed 2 --out runs --tag noise > runs/noise_armB.stdout 2>&1
echo "NOISE_DONE $(date -u +%Y-%m-%dT%H:%M:%SZ)"
