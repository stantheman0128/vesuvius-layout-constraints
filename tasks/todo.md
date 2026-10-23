# layout-constraints: todo (2026-10-22)

Goal: same-winding point collections for the villa spiral fitter from 2D page layout
(text-line paths, column margins, intercolumnar gaps) on flattened PHerc. Paris 4 surfaces.

- [x] Slice 1: segment 20230702185753, ds8 ink raster -> text-line chains -> 3D (2.4um mesh /4) -> same_windings JSON
- [x] Slice 1 checks: frame sanity vs umbilicus + human same_windings; translated-copy control; chain stats
- [x] Slice 2: band w116-117 (multi-column): intercolumnar gap paths -> data/out/20260701183145-w116-117_column_gaps.json, data/qa/report_w116.md
- [x] Slice 2b: band w116-117 text lines (slice 1 extractor, sigma 15 x 150, min width 500), seam split -> data/out/20260701183145-w116-117_text_lines.json, data/qa/report_w116_lines.md
- [x] Slice 3 compute plan written: tasks/compute-plan.md (12 GiB default / 2 GiB no-normals, Py3.14+cmake, CPU 2.5-5 h per 10k-step arm)
- [x] merge_pcl.py: renumber and merge generated collections into a copy of same_windings.json (154 + 96 = 250 with the band text lines, human untouched)
- [ ] Slice 3 (needs Stan's compute approval): fit with/without on a z window, satisfaction metrics, windaudit
- [ ] Write-up + decide villa PR vs standalone repo

## Slice 1 review (2026-10-22)

- Frame PASS (IoU 0.984 image vs mesh mask; 8 of 90 human lines on the surface vs 0 for +25 shifts). Chains vs human: modest PASS.
- Wraps: 17 of 30 text-line chains span over 360 deg (up to 813) because the segment is near the core.
  Resolved 2026-10-22 by reading the fitter: the strip loss uses unwrapped shifted radius and explicitly
  handles "a fiber spanning several windings" (losses.py:1216-1220, sample_spiral.py:128-133), so no split.
- Verifier (2026-10-22): all 6 claims CONFIRMED (own bilinear recompute within 4e-12; IoU 0.9837 vs flipped-image controls 0.88; 8/0/0 of 90; spans 813/431 reproduced).
  Notes kept: the 8-of-90 test checks the mesh frame against human points, not the 2D->3D mapping (the 0.337 vs 0.064 chain test does); umbilicus control points stop at z 18240 while line00/line01 reach 18395 (np.interp clamps); creation_time makes the JSON non byte-identical between runs.
  Action for slice 3: renumber collection ids before merging into same_windings.json (see compute-plan.md).
- Next: verifier done, then slice 2 on band w116-117 (intercolumnar gaps, about 366 MB download).

## Slice 2 review (2026-10-22)

- 2 gap chains (931 points), one per panel, both in the upper half; 0 of 4746 samples on invalid quads.
- Frame a: PASS (on the mesh, lower-half IoU 0.979, 718 deg per mesh row = two windings).
- The black seam between panels is unrendered ink, not missing mesh (the mesh is valid there). The corridor
  check uses mesh valid AND rendered papyrus and rejected both seam-crossing pairs.
- Check b is empty: no human same_windings collection lies on this band (0 of 125, all copies).
- Check c not measurable: abs_winding.json has 59 points (wind_a 10..63), nearest 853 voxels from the band.
  The 116/117 identity is unconfirmed.
- Added slope and contrast filters after looking at the candidates (documented in README).

## Slice 2b review (2026-10-22)

- 62 text-line chains (36 left, 26 right), 12978 points; 0 of 69498 samples on invalid quads; 76 s.
- Seam: 0 paths crossing before filtering, 2 touching (within 50 px), 0 crossing in the output.
- Spans 15.5 / 43.4 / 119.6 deg (min / median / max), none over 180. Frame a PASS; b empty; abs_winding 874 voxels away.
- No speckle gate beyond the 0.3 density threshold; the interline-contrast gate was tried and rejected (it
  flagged real, tightly spaced lines). If merge_pcl.py is used for these, ids need renumbering as before.

## Slice 3 review (2026-10-22)

- [x] CPU env, 1.84 GiB dataset, arm B via scroll-spec path overrides, smoke runs (300 steps) both arms.
- [x] Main runs, 4,000 steps, seed 1: A 15,671 s / 7.23 GiB, B 15,568 s / 7.48 GiB, both exit 0.
- [x] Verdict under tasks/PROTOCOL.md: hurts (patches 24.71 -> 22.50%, human rel 71.2 -> 57.7%, human same 75.0 -> 69.4%; ours 57.0%).
- [x] Cross-eval (A checkpoint, B inputs, 0 steps): human metrics within 0.3 pt of arm A; ours 38.5% under A.
- [x] Point-to-patch distance: ours 20% on patches vs human 65% / 52%; segment meshes coincide with patches where both exist (peak at 0..2, no offset peak).
- [ ] Decision for Stan: publish as a pre-registered negative result plus tooling, or run the team's setting (GPU, normals, 30k steps; 37 h per arm here).
- Lessons: the fitter's "unattached" strip is per collection, not per point (fit_spiral.py:816-840, 914-921); I first read 1,198 as an off-patch subset and had to retract it. The baseline itself honours only 24.7% of patches in this setting, so any A/B here is between two weak fits.
- Verifier (2026-10-23): 6 of 7 CONFIRMED; the strip-construction citation was wrong (real path fit_spiral.py:1818-1880, longest in-window run then decimate; 1,198 matches exactly). Five wording claims corrected in README: col235 is a far loser; a 12 to 14 voxel bump exists in both segment histograms (also in human points); our distance bins are 4 to 5.5% only out to 16 voxels; cross-eval differs from arm A on 1,197 patch fractions (cause untraced); four of our collections got worse in B.
