# Slice 3 protocol (pre-registered 2026-10-22, before any fit ran)

Question: does adding the layout-derived same-winding collections (96 collections: 32 text lines on
segment 20230702185753, 2 column gaps and 62 text lines on band w116-117) help, hurt or do nothing to a
spiral fit on z 10500..11500 of PHerc. Paris 4, compared with the human annotations alone?

## Arms

| arm | dataset dir | same_windings.json |
|---|---|---|
| A baseline | C:/Users/stans/Projects/_scratch/2026-10-22-layout-constraints/data/spiral_datasets/phercparis4 | human file as published (154 collections) |
| B layout | C:/Users/stans/Projects/_scratch/2026-10-22-layout-constraints/data/spiral_datasets/phercparis4_plus_layout (junctions to the big dirs, copies of the JSONs) | merged: human 154 + ours 96 = 250, ids renumbered by merge_pcl.py |

Everything else identical: FIT_SPIRAL_DEVICE=cpu; overrides z_begin 10500, z_end 11500,
input_use_normals false (no lasagna sidecar downloaded), input_use_fibers false (no fibres downloaded),
optimizer_random_seed 1, optimizer_num_training_steps as below. Verified patches, outer shell, umbilicus,
winding_inference, abs and relative windings on (defaults).

## Runs

1. Smoke: both arms, 300 steps. Purpose: pipeline works, seconds per step measured, inputs loaded as
   expected (the log must show our collections counted in arm B and not in arm A).
2. Main: both arms, N steps with N fixed after the smoke run by this rule: N = 10,000 if a step takes
   under 2.0 s, otherwise the largest multiple of 1,000 that keeps one arm under 6 hours. N is written
   here before the main runs start.
3. Noise check (only if the primary metric differs by less than 1 point between arms): both arms again
   with optimizer_random_seed 2.

## Fixed after the smoke run (2026-10-22, before any main run)

- Arm A smoke: 300 steps, 4.5 s per step (log: 226 steps at 16m56s), loading 5 min, evaluation 2 min, peak RSS 7.4 GiB,
  wall 1742 s. Loss 4423 at step 0, 1742 at step 200. 2,489 verified patches in the window; human pcls 171 cross-patch
  and 75 unattached; 281 human collections dropped for having under 2 points in the window.
- By the rule above, N = 4000 (4000 x 4.5 s = 5.0 h per arm; 5000 would exceed 6 h).
- Our coverage of the pre-registered window z 10500..11500: 2,403 of our 24,843 points, 16 collections with at least 2
  points inside (human unattached in the same window: 832 points, 75 collections). The window stays as pre-registered;
  other 1000-slice windows would hold up to 3,415 of our points, but we do not move it.

## Metrics (from satisfaction_metrics_fitted.json and satisfied_fitted.json, read with a script, not by eye)

- Primary: fraction of verified patches satisfied (the fitter's own evaluation input, which we did not
  touch). Also the boundary-satisfied fraction.
- Secondary: fraction of satisfied points in the HUMAN same-winding collections (ids below 175 in arm B)
  and in the relative and absolute winding collections.
- Sanity, not evidence: fraction of satisfied points in OUR collections in arm B, and the final loss
  breakdown printed by the fit.
- Cost: wall time and peak memory per arm.

## Decision rule (fixed now)

- helps: primary metric in B is at least 0.5 points higher than in A, and no secondary metric is lower by
  more than 0.5 points.
- hurts: primary or any secondary metric in B is lower than in A by more than 1.0 point.
- neutral: anything else. A neutral result with our own collections satisfied at 80% or more means the
  constraints are consistent with the fit but add nothing measurable on this window; that is reported as
  such.
- Any crash, NaN, or a run that did not reach N steps is reported as a failure, not dropped.

## Known limits, stated before the runs

- One z window, one scroll, CPU only, normals and fibres off, so the baseline is weaker than the
  published fits. The comparison is between two runs of the same weakened setting.
- Most human same-winding lines in this window are not on our two segments, so the secondary metric
  measures interference, not substitution.
- spiral_outward_sense CW comes from the team's own PHercParis4 example in 38_tutorial_spiral.md:268-272 (they say it is read off the CT by a person; no independent check here). base_shape_zyx [18946, 8174, 8174] is lucasjbyoung's value in villa PR #1925.
- The CPU path uses a different interpolant than CUDA (fit_spiral direct-lr fallback), so numbers are not
  comparable with published GPU runs.
