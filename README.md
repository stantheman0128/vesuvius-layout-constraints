# Layout constraints for the PHerc. Paris 4 spiral fit

Summary (2026-10-22). Ink layout on two segments (text lines, column gaps, margins read from ds8 ink
renders) was turned into 96 same-winding point collections in the spiral fitter's own JSON format
(slices 1, 2, 2b). An A/B fit of the team's `spiral-fitting` on CPU (z 10500..11500, 4,000 steps, one
seed, normals and fibres off; protocol pre-registered in `tasks/PROTOCOL.md`) came out **hurts** under
the pre-registered rule: verified-patch satisfaction 24.7% to 22.5%, human point satisfaction down, our
own points up from 38.5% to 57.0% (slice 3). Two follow-up measurements say what that does and does not
mean: the segment meshes coincide with the verified patches wherever both exist (no offset; a shifted
mesh scores worse), and our lines mostly run through regions with no verified patch, where the baseline
spiral is interpolated. Deciding whether the lines or the interpolation is right needs the team's full
setting (GPU, normals on, 30,000 steps), which this machine cannot run in useful time.

Turns the 2D page layout visible on a flattened PHerc. Paris 4 segment (text-line centre paths and column
margins) into point collections in the spiral fitter's JSON format, mapped back to 3D in the spiral dataset
frame. Slice 1 runs on one segment, `20230702185753`, and checks the coordinate frame. Slice 2 finds
intercolumnar gaps on the two-winding band `20260701183145-w116-117` (section at the end). Slice 3 runs the spiral fit A/B (last section).

The ScrollPrize page `docs/39_winding_annotations.md` lists ink rows/columns, intercolumnar gaps and drawn
paths under "Things we have not tried". This is a generator for that idea. It is ink-derived, like
Nicodol's `ink-constraints`. On the one CPU A/B run so far it did not help the fit (slice 3).

**See the caveat on wraps below: multi-turn chains are valid strips for the fitter.**

## Layout

```
layout_constraints/
  __init__.py   paths and constants
  extract.py    ds8 ink JPEG -> text-line centre paths + left/right margin paths, QA overlay
  project.py    ds8 pixel -> mesh grid -> bilinear xyz (rejects quads with a -1 vertex) -> /4; JSON writer
  check.py      frame sanity, agreement with human lines, shifted controls, chain stats -> data/qa/report.md
  extract_gaps.py  slice 2: ds8 ink JPEG -> text blocks -> intercolumnar gap centre paths, QA overlay
  check_gaps.py    slice 2 checks -> data/qa/report_w116.md
  band_lines.py    slice 2b: slice 1 text-line extractor on the band, seam split, checks -> report_w116_lines.md
run.py          runs slice 1 (extract, project, check)
run_w116.py     runs slice 2 (extract_gaps, project.main_band, check_gaps)
run_w116_lines.py  runs slice 2b (band_lines)
tests/          pytest for the mapping, -1 rejection, decimation and id order; gap finder on synthetic
                images; seam split on a synthetic path
data/           inputs (mesh/, human/, ink_ds8.jpg) and outputs (out/, qa/)
```

## Inputs

| file | source |
|---|---|
| `data/mesh/{meta.json,x.tif,y.tif,z.tif}` | `https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/segments/20230702185753/mesh/20230702185753-on-20260411134726-2.4um.tifxyz/` (float32, 1820 wide x 2530 high, -1 = invalid) |
| `data/ink_ds8.jpg` | the segment's ink prediction, 8x downsampled (4550 x 6325 px), `...new_canon_autoresearch_recipe-tile256-stride128-ds8.jpg` |
| `data/human/same_windings.json`, `umbilicus.json` | the PHercParis4 spiral dataset annotations |

## Recipe

1. **Extract** (`extract.py`). Ink is bright on a dark papyrus background (papyrus about 32 to 48, ink about
   224 to 240, outside the segment 0 to 16). Threshold at 125 (Otsu on the papyrus area). Smooth the binary
   ink with an anisotropic Gaussian (sigma 15 rows, 100 columns) and threshold the density at 0.3. This
   merges letters into line blobs and keeps neighbouring lines apart. A plain horizontal closing (first
   attempt) merged adjacent lines wherever tall letters touched. Keep blobs at least 400 px wide (blobs over
   1.8 x the median height would be dropped as merged lines; none were). For each blob, the density-weighted
   vertical centroid per column gives an ordered left-to-right path. Margins: for each text line, take the
   outermost piece at least 100 px wide, fit a straight line through these ends with outlier rejection (80 px),
   and keep the margin when at least 60% of lines are inliers. The path is piecewise linear through the
   inlier ends.
2. **Project** (`project.py`). ds8 (row, col) -> full-res (8 row, 8 col) -> grid (i, j) = (row 8/20, col 8/20)
   -> bilinear x, y, z at (i, j). A sample is invalid if it lies outside the grid or any of its quad's four
   vertices is -1. Then p = [x, y, z] / 4 (9.6 um dataset voxels). Chains are split at invalid samples,
   greedily decimated to a minimum spacing of 10 voxels, and dropped if under 2 points.
3. **Write** the version 1 point-collection JSON: `winding_is_absolute: false`, `wind_a: null`, global point
   ids that increase along each path (the fitter sorts by id and keeps the longest contiguous run), and
   provenance metadata (segment, kind, ds8 row/col range, mesh name, frame, spacing).

## Run

```
cd C:\Users\stans\Projects\vesuvius-layout-constraints
python run.py
python -m pytest -q -p no:cacheprovider tests
```

Each step also runs alone: `python -m layout_constraints.extract`, `.project`, `.check`. A full run takes
about 16 s on CPU. Outputs: `data/out/20230702185753_text_lines.json` (the collections),
`data/out/20230702185753_paths2d.json` and `_dense.npz` (intermediates), `data/qa/report.md`,
`data/qa/20230702185753_overlay.png` (red: text lines, cyan: margins, half resolution).

## Results (from `data/qa/report.md`)

- 32 chains (30 text-line, 2 margin), 10934 points, total length 117829 voxels. Zero of 57549 path samples
  fell on invalid quads.
- **Frame: PASS.** All points are inside the mesh bbox / 4. The image's papyrus mask and the mesh's valid
  vertices agree with IoU 0.984 on the grid. Radius from the umbilicus is 165 / 421 / 723 (min / median /
  max). All valid mesh vertices give 137 / 428 / 766, and human points in the same z range give
  133 / 781 / 2942.
- **Frame vs translated copies.** 8 of 90 human same_windings collections lie on this segment's surface (at
  least 80% of their points within 5 voxels of a mesh vertex). For the +25 x and +25 y copies the count is
  0 of 90.
- **Chains vs human lines (verdict c: PASS, but modest).** Of our points within 50 voxels of a human line,
  33.7% are within 10 voxels, against 6.4% (x +25) and 4.7% (y +25). Human collections whose closest approach
  to our chains is at most 10 voxels: 7, against 6 and 4. The plain medians (human -> chains 253, chains ->
  human 702) cannot discriminate. Human lines mostly run along z, our text lines run around the scroll, and
  most human points are on other wraps, so the medians measure line spacing.

## Caveats

- **Text lines cross wraps on this segment, and that is allowed by the fitter.** The segment sits close to
  the core (radius about 140 to 770 voxels, 1.3 to 7.4 mm), so a 6 cm line of text goes around the scroll
  about two times. 17 of 30 text-line chains span more than 360 degrees around the umbilicus (up to 813
  degrees); the largest human same_windings collection spans 176 degrees. The ScrollPrize docs phrase
  same-winding as "lies on the same wrap", but the fitter's strip loss works in unwrapped shifted-radius
  space: `losses.py` (spiral-fitting, lines 1216 to 1220 at commit a4979b990) says strips are "assumed to be
  locally dense enough that adjacent STRIP points have |dtheta| < pi" and gives "a fiber spanning several
  windings" as the normal case, with theta=0 crossings gathered along the walk; `sample_spiral.py:128-133`
  converts back with `theta / (2 pi) * dr_per_winding`. So a chain that follows one sheet around two turns
  is a valid same-winding strip as long as consecutive points are closer than half a turn. Our spacing is
  10 voxels at radius 165 or more (0.06 rad); the largest step, 60 voxels, is 0.36 rad. No split needed.
  What the chains assert is "all these points are on one continuous sheet", which is what following a
  text line on a flattened segment gives. The two margin chains (109 and 129 degrees) run along z.
- The +25 voxel controls are weak near the core, where wraps are only tens of voxels apart, so a shifted copy
  can land on a neighbouring wrap.
- Path precision inside the letter band does not matter for same-winding evidence, since every point is on
  the sheet. The centroid does jump at ragged blob ends, though: up to 30 ds8 px in 2D, which shows up as
  written steps up to 60 voxels. Trimming chain ends would remove most of these.
- The ds8 pixel is mapped by its corner (row 8/20), not its centre. The offset is at most 0.175 grid cells,
  under 1 voxel.
- Ink-derived: chains follow whatever the ink model predicts. This is the same evidence class as
  `Nicodol/ink-constraints` (villa PR #1390, closed without merge because the maintainers want to see the
  result of a fit). Nothing here has been run through a fit yet.
- The packages come from the user site-packages (the venv has `include-system-site-packages = true`), so
  `python -I` cannot be used to run this.

## What is not in this repo

Everything downloaded from the team's open data bucket and every fitter checkpoint is left out, so the
repo stays small. The sources are given where each file is first used; the sizes are what landed on disk.

| path | what | size | where it comes from |
|---|---|---|---|
| `data/mesh/`, `data/ink_ds8.jpg` | segment 20230702185753 tifxyz mesh and ds8 ink render | 55 MB | "Inputs" table above |
| `data/w116/` | band 20260701183145-w116-117 mesh and ink render | 299 MB | "Slice 2: Inputs" table |
| `data/spiral_datasets/phercparis4/` | the spiral fitter's PHerc. Paris 4 dataset (verified patches, human annotations) | 1.84 GiB, 90,698 objects | `tasks/compute-plan.md` |
| `data/spiral_datasets/phercparis4_plus_layout/` | the same with `spiral-scroll.json` path overrides pointing at our merged same_windings | | built by `merge_pcl.py` |
| `runs/*/checkpoint_fitted.ckpt` | fitter checkpoints of both arms, the cross evaluation and the smoke tests | 977 MB each | rerun per `tasks/PROTOCOL.md` |

What is in `runs/`: `fit.log`, `run_summary.json`, `satisfaction_metrics_fitted.json` and `satisfied_fitted.json`
of every run, which is all the Slice 3 numbers are computed from. `data/human/` holds the published annotations
the tests compare against (2 MB), `data/out/` our constraint files, `data/qa/` the overlays and metric tables.

## Slice 2: intercolumnar gaps on band 20260701183145-w116-117

The ScrollPrize page `39_winding_annotations.md` suggests the blank vertical spaces between columns of text
as same-winding evidence, like ink. This slice turns those corridors into point collections on the band
`20260701183145-w116-117` (PHerc. Paris 4, outer windings 116 and 117).

### Inputs

| file | source |
|---|---|
| `data/w116/mesh/{meta.json,x.tif,y.tif,z.tif}` | `.../PHercParis4/segments/20260701183145-w116-117/mesh/20260701183145-on-20260411134726-2.4um.tifxyz/` (float32, 6732 wide x 3748 high, confirmed from the TIFF headers; -1 = invalid) |
| `data/w116/ink_ds8.jpg` | the band's ink prediction, ds8, 16830 x 9370 px (16830 x 8 / 20 = 6732 and 9370 x 8 / 20 = 3748, so the slice 1 mapping applies unchanged) |
| `data/human/abs_winding.json` | `.../representations/spiral/20260411134726-spiral-dataset-20261019084150/abs_winding.json`, 20,022 bytes (not the 100 KB expected; it is the only abs_winding.json in that dataset's listing) |

### What the image and the mesh show

- Two panels side by side, one per winding. Each mesh row sweeps 718 degrees around the umbilicus
  (median over rows) and one turn is 3252 grid columns (8130 ds8 px), so a panel is one winding wide. It
  holds about two columns of text (a column is about 2500 to 3000 ds8 px, 5 to 6 cm).
- **The black seam between the panels at the top is not missing mesh.** The mesh is valid there; the ink
  render left it black. The image's papyrus is a strict subset of the valid mesh (papyrus on an invalid
  vertex: 0.0000 of the grid; valid but unrendered: 0.1329). So "connected through valid mesh" is checked
  on mesh valid AND rendered papyrus, because a corridor through unrendered area cannot be judged.
- The lower half is covered in small speckles about as dense as text. No corridor there passes the filters.

### Recipe (`extract_gaps.py`)

1. Ink = gray > 125 (as slice 1; Otsu on the papyrus here gives 118). Work on 4 x 4 ds8 cells. Text density
   is the Gaussian of the ink fraction divided by the Gaussian of the papyrus fraction, zero off the papyrus.
   Two densities: sigma 600 rows x 150 cols for blocks, 600 x 40 for the gap centre. Sigma 300 x 30 (the
   first guess) kept letter-scale texture and gave fragmented blobs; 300 x 120 still fragmented.
2. Blocks: watershed of minus density from cores (density > 0.20, at least 100,000 px), inside density
   > 0.12; blocks under 1000 rows tall are dropped. Plain connected components merged the right panel's
   two columns through a low-contrast bridge, which the watershed splits.
3. Corridors: in each row, two blocks that are consecutive left to right with only unlabelled cells between
   them. A pair is kept only if the blocks share at least half the rows of the shorter one and at most 5%
   of corridor rows cross invalid mesh or unrendered area. Runs of corridor rows (breaks up to 100 rows
   bridged) shorter than 500 rows are dropped.
4. Two filters added after looking at the candidates (not in the original spec). Straight-fit slope
   |d col / d row| at most 0.35, since gaps run along z and the one rejected run followed a blob edge
   (slope 0.996). Contrast (least corridor density / flanking block density, 600 px each side) at most
   0.25, since the rejected B5 | B1 corridor (0.313) is speckle between two watershed lobes rather than a
   blank strip; the kept gaps have 0.096 and 0.152. Then the spec's width rule drops runs wider than
   1.5 x the median corridor width. With two runs left, that rule cannot reject anything.
5. Path: per row, the midpoint of the run below 0.12 around the least-density column (argmin alone wandered
   inside the wide left-panel corridor), then a median filter and Gaussian of 100 rows, resampled to every
   ds8 row, top to bottom.
6. Project with the slice 1 recipe (`project.main_band` calls the same `project_paths` with the band's
   segment and mesh name). JSON kind `intercolumnar_gap`, with panel, block ids, corridor width, slope and
   contrast in the metadata.

Run `...\python.exe run_w116.py` from the project root: 125 s wall time, peak working set 1.34 GiB.
Outputs: `data/out/20260701183145-w116-117_column_gaps.json`, `_gaps2d.json` (blocks, and every candidate
with its reason), `_gaps_dense.npz`, `data/qa/report_w116.md`, `data/qa/20260701183145-w116-117_gaps_overlay.png`
(quarter resolution; blocks red, gap paths green).

### Results (verbatim from `data/qa/report_w116.md`)

- text blocks: 5; adjacent block pairs: 5; gap paths kept: 2; seam between panels at ds8 col 8358
- 20260701183145-w116-117_gap00: left panel, blocks B1 | B4, ds8 rows 1906..5110, cols 5847..6403, corridor width 1324 ds8 px, 636 pts, 6578 vx, z 9653..15055, radius 1960 / 2231 / 2558, span 41.1 deg
- 20260701183145-w116-117_gap01: right panel, blocks B2 | B3, ds8 rows 1286..2826, cols 12967..13138, corridor width 520 ds8 px, 295 pts, 3123 vx, z 13463..16219, radius 2154 / 2817 / 3175, span 7.6 deg
- ds8 path samples on invalid quads: 0 / 4746 = 0.0000
- step between consecutive written points (min / median / max): 10.0 / 10.3 / 12.0
- projected points inside mesh bbox / 4: True
- 2D registration: ink image papyrus mask (gray > 20, resized to the 6732 x 3748 grid) vs mesh valid vertices: IoU 0.848 (image 0.743 of the area, mesh 0.876); image papyrus on invalid mesh: 0.0000 of the grid, mesh valid but not rendered in the image: 0.1329
- the same IoU on the lower half of the grid (rows 1874..3747): 0.979
- angle swept around the umbilicus along each mesh row (every 250th row, 14 rows; two windings = 720): min / median / max 198 / 718 / 720 deg; grid columns per 360 deg (median) 3252 (= 8130 ds8 px)
- verdict a (inside bbox, min radius >= 20, max radius <= 1.2 x human max): PASS
- human same_windings collections on the band surface: 0 of 125 for the unshifted, x +25 and y +25 copies
  alike (human -> mesh vertices, unshifted: n=5413, median 1058.2, within 5: 0.000, within 10: 0.000).
  Human points in the projected bbox expanded by 20: 7 of 5413, all over 1000 voxels from the chains.
- verdict c: NOT MEASURABLE: no abs_winding point lies within 15 voxels of any gap chain

### Slice 2 caveats

- **Check b cannot discriminate on this band.** No human same_windings collection lies on it (human points
  reach radius 2942, the band goes out to 3363), so all three copies score zero. The frame evidence here is
  check a: points on the mesh, the 0.979 lower-half IoU, and the 718 degree wrap per row.
- **The absolute winding check could not be run.** abs_winding.json holds 59 points with wind_a 10 to 63,
  and the nearest one is 853 voxels from the band surface. Nothing in this slice confirms 116/117.
- Two chains, both in the upper half; no block pair in the lower half passes. gap01 stops at row 2826 where
  blocks B2 and B3 touch, though the corridor stays faintly visible below that.
- The slope and contrast thresholds were set by looking at four candidate runs. They separate those runs
  by a factor of 2 or more, but four is a small sample.
- Radius from the umbilicus swings from about 1650 to 3300 voxels within one turn of a mesh row, so radius
  is no proxy for the winding on this band, and a z-running chain changes radius a lot (gap01: 2154 to
  3175). Spans around the umbilicus are 7.6 and 41.1 degrees, far below the half turn that the fitter's
  strip loss allows between consecutive points.
- Block B5 includes an ink-model noise cloud at the top of the left panel; its only pair was rejected.

## Slice 2b: text lines on the band

`band_lines.py` runs slice 1's `extract.line_paths` on the band (now keyword-parametrized; its defaults are
the slice 1 values, and slice 1's paths reproduce exactly) with sigma 15 x 150 and min width 500 instead of
15 x 100 and 400. The other parameters stay as in slice 1. Letters are not larger in ds8 px on outer
windings: a ds8 pixel is 19.2 um wherever it is, and the line pitch is 333 to 364 rows here against roughly
290 to 380 on 20230702185753. The wider sigma joins words along a line; intercolumnar gaps of 500 px or more
stay open. No extra speckle gate is used. The 0.3 density threshold already leaves the lower half nearly
empty (lowest line at ds8 row 7506 of 9370). An interline-contrast gate (ink on the line / ink 130 to 210
rows above and below) was tried and dropped. Its lowest ratios (1.03 to 1.33) were real lines in the left
panel's second column, packed about 190 rows apart, so the off-line bands landed on the neighbouring lines.
Merged blobs are dropped as in slice 1; re-thresholding them at 0.4 to 0.6 did not split them cleanly, and 7
of the 9 lie in the right panel's ink-model cloud. Margins skipped. Each path is split at the seam column if
it crosses it. Run `...\python.exe run_w116_lines.py`: 76 s wall time, peak working set 1.72 GiB.
Outputs: `data/out/20260701183145-w116-117_text_lines.json`, `_lines2d.json`, `_lines_dense.npz`,
`data/qa/report_w116_lines.md`, `data/qa/20260701183145-w116-117_lines_overlay.png`.

From `data/qa/report_w116_lines.md`, verbatim:

- blobs at least 500 ds8 px wide: 71; dropped as merged lines (height over 1.8 x median): 9; text-line paths: 62
- seam at ds8 col 8358: 2D paths crossing it before any filtering: 0; touching it (ending within 50 px): 2; split at the seam: 0; 2D paths crossing it after the split: 0
- written chains whose ds8 col range spans the seam: 0 of 62
- chains: 62 (left panel 36, right panel 26), points: 12978
- ds8 path samples on invalid quads: 0 / 69498 = 0.0000
- angular span around the umbilicus per chain, degrees (min / median / max): 15.5 / 43.4 / 119.6; chains over 360 deg: 0; over 180 deg: 0
- ds8 column width per chain (min / median / max): 503 / 960 / 2664 (one turn is about 8130 ds8 px)
- verdict a (inside bbox, min radius >= 20, max radius <= 1.2 x human max): PASS
- empty again: human points within 50 voxels of our points: 0 of 5413 (closest 162); no human collection lies on this band (report_w116.md: 0 of 125).
- far again: nearest abs_winding point to any of our points is 874 voxels away (within 15: 0).

The two touching paths (line44, cols 8367..8963, and line52, cols 8385..9177) start just right of the seam
in the lower half. There the papyrus is rendered and the mesh is continuous across the seam column
(consecutive grid steps 5.2 to 5.6 voxels), so the seam rule is a conservative choice there, not a
geometric break. Written steps reach 60.2 voxels at ragged blob ends, as on slice 1.

## Slice 3: does the fitter want these constraints? (A/B fit on CPU)

Protocol, fixed before any fit ran: `tasks/PROTOCOL.md`. Two fits of the team's own spiral fitter
(`villa/spiral-fitting` at 862142652, CPU build, see `tasks/compute-plan.md`) on z 10500..11500 of PHerc.
Paris 4, 4,000 steps, seed 1, normals and fibres off. Arm A uses the published human annotations. Arm B adds
our 96 same-winding collections (`merge_pcl.py`, ids renumbered from 175). Of our 24,843 points, 2,403 fall
in the window, in 16 collections. Both arms load the same 2,489 verified patches and the same abs (6) and
relative (300) collections; the load logs differ only where our collections enter: same_windings 154 vs
250 collections, unattached groups 22 vs 38, cross-patch groups 40 vs 62, pcls 171/75 vs 193/91, and
"dropped ... with <2 points in z-roi" 281 vs 361.

Numbers from `data/qa/slice3_metrics.md` (written by `tools/read_metrics.py`, not by eye):

| metric | A human | B human + ours |
|---|---|---|
| verified patches satisfied (primary) | 24.71% (615/2489) | 22.50% (560/2489) |
| boundary satisfied patches | 27.12% | 25.27% |
| satisfied patches, area weighted | 18.39% | 12.39% |
| satisfied area fraction | 54.53% | 57.58% |
| human relative_windings points satisfied | 71.15% (185/260) | 57.69% (150/260) |
| human same_windings points satisfied | 75.00% (429/572) | 69.41% (397/572) |
| our same_windings points satisfied | n/a | 57.01% (683/1198) |
| wall / peak RSS | 15,671 s / 7.23 GiB | 15,568 s / 7.48 GiB |
| final loss (step 3800) | 40.4 | 42.1 |

Verdict under the pre-registered rule: **hurts** (primary down 2.2 points, over the 1.0 threshold; human
secondaries down 5.6 and 13.5 points). The noise check (seed 2) is not triggered by the rule, which only
calls for it when the primary differs by under 1 point; so this is one seed per arm and the run-to-run
spread is unmeasured. Satisfied area went up 3 points while satisfied patches went down; the two
disagree, and the rule names the patch fraction as primary.

Where the human losses are (`satisfied_fitted.json` of both arms, per collection, window points only): 21
human collections lost points, 13 gained, 41 unchanged, net loss 67 points. The two largest same-winding
losers (same_wrap63 32 of 32, same_wrap42 20 of 39) and the three largest gainers (same_wrap61 +15,
same_wrap55 +11, same_wrap51 +9) sit at z 10604 within 61 to 666 voxels of our points; same_wrap139
(10 of 19, z 10517 to 10852) is 65 voxels away. The largest relative-winding loser, col235 (18 of 18), is
at z 11432 and 791 voxels from our nearest point, so not every loss is local. Split at 300 voxels from our
points (by collection centroid): about 30 collections near with net loss 50, about 45 far with net loss
17. The effect is mostly where our constraints are, with some loss far from them.

Our own collections in B: 3 of 16 fully satisfied, 3 at zero (20230702185753_line20 0/44,
20230702185753_margin_right 0/54, w116-117_line41 0/35). A point counts as satisfied only if it is within
0.45 winding and 6 voxels of the sheet at the strip's median winding (`satisfaction_metrics.py:29-30`),
so a zero means the fitted spiral does not pass through that chain at all, even with the constraint on.
margin_left on the same segment is 52/52.

Cross-evaluation (`runs/xeval_Ackpt_Bdata`): arm A's checkpoint loaded with arm B's point collections and
zero training steps (`FIT_SPIRAL_RESUME_PATH`; `fit_spiral.py:5437` iterates `range(4000, 4000)`), so the
fitter evaluates our collections against the baseline spiral. Human metrics reproduce arm A within 0.32
points (patches 25.03%, relative 71.5%, same 74.8%). The evaluated spiral is not identical to arm A's own
final evaluation (1,197 of 2,489 patch fractions differ, one from 0 to 1) and the cause was not traced, so
0.3 points is the floor below which this comparison cannot resolve a difference. The
baseline spiral passes through 38.5% of our points (461/1198, 0 of 16 collections fully); arm B moved
that to 57.0%. So the constraints did not bend a fit that already agreed with them: about six in ten of our
points sit off the sheet the fitter builds from the human annotations and the verified patches, and arm B
pulled the spiral toward them in aggregate at the cost of patches and human points (four of our
collections got worse in B than under the baseline: line20 8 to 0, w116-117_line41 20 to 0, line35 35 to
23, line36 50 to 26). (Counting note: an "unattached pcl"
strip in the fitter is any collection with at least one point farther than 2.5 voxels from every verified
patch (`fit_spiral.py:1818`); its strip holds that collection's longest contiguous id-sorted run inside
[z_begin, z_end) (`:1822-1843`, z margin 0), decimated at 16 voxels (`:1866-1880`). Decimating the
longest runs of our 16 collections gives exactly 1,198; decimating all window points would give 1,217
(line19 has two runs, 136 and 38 points). The strip fraction is therefore over nearly all our window
points, not over an off-patch subset.)

Where our points are relative to the verified patches (`tools/patch_distance.py`, exact point-to-triangle
distance against the 2,928 patches whose bbox touches the window, 4.3 M quads; raw distances in
`data/qa/slice3_patch_distance_raw.npz`): 20.1% of our window points lie within 2.5 voxels of a patch,
against 65.0% of the human same-winding points and 52.4% of the human relative-winding points in the same
window. The shapes differ: human points are 63% in the 0 to 2 voxel bin and then fall off (people
annotate on patches); ours are 17% in that bin, 4 to 5.5% per 2-voxel bin from 4 to 16 voxels, then 2 to
4% per bin out to 30. Per collection, line18 has 82% of its points on patches and arm A already satisfied 90% of it;
line20 (median 65 voxels), margin_left (27) and line38 (36) run through regions with no patch at all.

Is that an offset or a coverage gap? `tools/segment_patch_distance.py` takes every vertex of the two
whole segment meshes, rather than the text lines alone, inside the window and measures the same distance:
20230702185753, 355,949 vertices, median 15.2 voxels, 25.8% within 2.5, 32.2% within 6; band w116-117,
1,493,929 vertices, median 19.6, 11.3% within 2.5. Both histograms have their peak in the 0 to 2 bin
(22.9% and 9.6%), a dip at 6 to 8, and a small bump at 12 to 14 voxels (4.7% and 3.6%) that the human
points show too and that looks like the distance to the neighbouring wrap; there is no peak at any other
single offset. So where a verified patch exists next to the segment the segment coincides with it; the
long tails are regions the verified patches do not cover. Control (`--shift`, every
4th vertex of 20230702185753): moving the mesh by 8 voxels drops the 0 to 2 bin from 22.9% to 5.8% (+x),
7.8% (+y), 12.3% (+z) and 9.3% (-x), and the within-2.5 fraction from 25.7% to 7.5 to 15.2%; the
unshifted mesh is the best alignment of the five. The segment-to-patch mapping is not offset. Our constraints mostly sit where the patches are absent, which is also where the
spiral is least constrained and where moving it costs the most elsewhere.

Reading of Slice 3, then: on this weakened CPU setting (4,000 steps, normals and fibres off, one seed) the
baseline honours only 24.7% of the verified patches, and adding our 16 in-window collections lowered that
to 22.5% while raising our own points from 38.5% to 57.0%. The pre-registered verdict is "hurts". What it
does not show is that the lines are wrong: the segments agree with the patches wherever both exist, and the
disagreement is between our lines and a spiral interpolated across patch-free regions. Settling that needs
the team's own setting (GPU, normals on, the 30,000-step default in `config.py:408`), which this machine
cannot run in useful time (about 37 hours per arm at 4.5 s per step).
