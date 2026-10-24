# Full-setting A/B on a rented GPU (planned 2026-10-23, run 2026-10-24)

The CPU arms (tasks/PROTOCOL.md) ran 4,000 steps with normals and gradient magnitude off, and the
baseline honoured only a quarter of the verified patches. This plan reruns both arms at the fitter's
defaults so the verdict is about the constraints and not about a weak fit. Everything is scripted in
`tools/pod_setup.sh`; this file is the budget and the stop rules.

Status: run on 2026-10-24 (GPUtw.ai RTX 3090 24 GB, machine with a Ryzen 7 9700X, NT$11.28/h, two seeds).
Results and verdict in the README section "Team defaults on a GPU"; tables in
data/qa/slice3_metrics_gpufull_s{1,2}.md. Pod time 11.0 h in all: about 1.5 h of setup and fixes, 2.5 h of
fits (smoke plus four arms), 7 h idle after the first pair; about NT$124.

## What changes against the CPU arms

| | CPU arms | GPU arms |
|---|---|---|
| steps | 4,000 | 30,000 (`config.py` default) |
| input_use_normals / gradient_magnitude | off | on (defaults) |
| input_use_fibers | off | off: the dataset has no `fibers/` folder, only `eval_fibers/` |
| z window, seed | 10500..11500, 1 | same |
| device | cpu | cuda |

## Data on the pod (downloaded there from the public bucket, nothing through the laptop)

| part | size |
|---|---|
| base dataset as fetched for the CPU arms (verified_patches, winding_inference, outer_shell, eval_fibers, JSONs) | 2.1 GiB |
| `lasagna_inputs/las_008_nx.ome.zarr.respool_g4_pair/` (normals, packed sidecar already on S3) | 9.52 GiB |
| `lasagna_inputs/las_008_grad_mag.ome.zarr.respool_g4/` | 4.76 GiB |
| total | about 16.4 GiB, plus the env (torch cu128, about 6 GB) and two checkpoints of 1 GB |

Not needed: `las_008_surf_sdt` (32.6 GiB, not in the fitter's input catalog), tracks, patch_normals, CT.

## Pod

Any Linux box with one NVIDIA card of compute capability >= 8.0, 24 GB VRAM (the fitter README calls a
1,000-slice window "a good first run on a smaller GPU"), 60 GB disk, Python 3.14 via uv. Candidates and
list prices on 2026-10-23: GPUtw.ai RTX 3090 24 GB NT$11/h, RTX 5090 32 GB NT$30/h (per-second billing,
SSH); RunPod RTX 4090 24 GB US$0.34/h community, US$0.89/h secure.

## Steps and stop rules

1. `bash tools/pod_setup.sh prepare`: clone, `uv sync`, fetch 16.4 GiB, build arm B. Expect 20 to 40 min
   depending on the pod's network. Stop if `uv sync` cannot build the nanobind modules; report, do not
   hand-patch the env on the clock.
2. `bash tools/pod_setup.sh smoke`: 300 steps of arm A on cuda. Read the s/step from the last
   `Optimizing` line. Stop and report if a step takes over 2 s (30,000 steps would then exceed 16 h per
   arm) or if the run fails on the normals inputs.
3. `bash tools/pod_setup.sh run`: arm A then arm B at 30,000 steps, then `read_metrics.py` writes
   `data/qa/slice3_metrics_gpufull.md`. Copy that file, `fit.log`, `run_summary.json`,
   `satisfaction_metrics_fitted.json` and `satisfied_fitted.json` of both arms back into the repo;
   leave the checkpoints on the pod unless they are needed for a cross evaluation.

Budget cap NT$500 (about US$15). At NT$11/h that is 45 pod hours, so the cap is not the constraint;
the smoke step's s/step is. Verdict rule for the GPU pair: the same as `tasks/PROTOCOL.md`, applied to
the GPU pair alone and reported next to the CPU pair, not pooled with it.
