# layout_constraints report: band 20260701183145-w116-117, intercolumnar gaps

Units are dataset voxels (9.6 um). 'Our points' are the written JSON points (10 voxel spacing). 'Dense chains' are every valid ds8 path sample before decimation (one per ds8 row, about 1.6 voxels apart in z). Human lines are densified to 1 voxel steps (gaps over 50 voxels not bridged).

## Gap finder

- text blocks: 5; adjacent block pairs: 5; gap paths kept: 2; seam between panels at ds8 col 8358
  - block B1: ds8 rows 416..7519, cols 2920..5919
  - block B2: ds8 rows 436..7655, cols 10056..13479
  - block B3: ds8 rows 1284..4783, cols 13172..15779
  - block B4: ds8 rows 1900..5111, cols 6552..7683
  - block B5: ds8 rows 1468..4951, cols 1500..3395
  - pair B1 | B2: overlap 0.997, corridor rows 3872: rejected: corridor crosses invalid mesh or unrendered area in 419 of 968 rows
  - pair B1 | B4: overlap 1.0, corridor rows 3212: kept 1 run(s) (run rows 1904..5111, width 1324, slope 0.175, contrast 0.096: kept)
  - pair B2 | B3: overlap 1.0, corridor rows 2296: kept 1 run(s) (run rows 1284..2827, width 520, slope 0.125, contrast 0.152: kept; run rows 4032..4783, width 374, slope 0.996, contrast 0.645: rejected: |slope| over 0.35)
  - pair B4 | B2: overlap 1.0, corridor rows 3212: rejected: corridor crosses invalid mesh or unrendered area in 803 of 803 rows
  - pair B5 | B1: overlap 1.0, corridor rows 1584: rejected: no corridor run of at least 500 rows passing slope and contrast (run rows 3584..4951, width 596, slope -0.052, contrast 0.313: rejected: contrast over 0.25 (corridor not blank))

## a. Frame sanity

- projected bbox min [1716.3, 5673.1, 9652.6] max [5515.8, 6766.2, 16219.4]
- mesh meta.json bbox / 4: min [1278.7, 1446.3, 3003.5] max [7533.0, 7623.5, 17998.7]
- projected points inside mesh bbox / 4: True
- 2D registration: ink image papyrus mask (gray > 20, resized to the 6732 x 3748 grid) vs mesh valid vertices: IoU 0.848 (image 0.743 of the area, mesh 0.876); image papyrus on invalid mesh: 0.0000 of the grid, mesh valid but not rendered in the image: 0.1329
- the same IoU on the lower half of the grid (rows 1874..3747): 0.979
- umbilicus over z 9653..16219: x 4144..4908, y 3368..4873
- radius from umbilicus, our points (min / median / max): 1960 / 2372 / 3175
- radius from umbilicus, human same_windings points in the same z range (n=2167, min / median / max): 133 / 920 / 2942
- radius from umbilicus, all valid mesh vertices (min / median / max): 1206 / 2303 / 3363
- angle swept around the umbilicus along each mesh row (every 250th row, 14 rows; two windings = 720): min / median / max 198 / 718 / 720 deg; grid columns per 360 deg (median) 3252 (= 8130 ds8 px)
- verdict a (inside bbox, min radius >= 20, max radius <= 1.2 x human max): PASS

## b. Agreement with human same_windings lines, and translated controls

- human points in the projected bbox expanded by 20: 7 of 5413 (from 125 collections)

| copy | human -> our dense chains | our points -> human (all) | our points -> human (only those within 50) |
|---|---|---|---|
| unshifted | n=7, median 1037.2, within 5: 0.000, within 10: 0.000 | n=931, median 1376.2, within 5: 0.000, within 10: 0.000 | n=0 |
| x +25 | n=7, median 1019.9, within 5: 0.000, within 10: 0.000 | n=931, median 1379.6, within 5: 0.000, within 10: 0.000 | n=0 |
| y +25 | n=7, median 1055.2, within 5: 0.000, within 10: 0.000 | n=931, median 1394.1, within 5: 0.000, within 10: 0.000 | n=0 |

Closest approach of each human collection to our dense chains:

| copy | collections with closest approach <= 5 | <= 10 | <= 25 | median of closest approaches under 50 |
|---|---|---|---|---|
| unshifted | 0 | 0 | 0 | n=0 |
| x +25 | 0 | 0 | 0 | n=0 |
| y +25 | 0 | 0 | 0 | n=0 |

Human points vs the band surface (all valid mesh vertices / 4, 5 voxel grid spacing). Uses the human points inside the mesh bbox / 4 expanded by 20 (5413 points; 125 collections with at least 5 of them). Shifting the human points by -d is the same test as shifting the mesh by +d:

| copy | human -> mesh vertices | collections with at least 80% of those points within 5 of the surface |
|---|---|---|
| unshifted | n=5413, median 1058.2, within 5: 0.000, within 10: 0.000 | 0 of 125 |
| x +25 | n=5413, median 1064.4, within 5: 0.000, within 10: 0.000 | 0 of 125 |
| y +25 | n=5413, median 1042.2, within 5: 0.000, within 10: 0.000 | 0 of 125 |

## c. Absolute winding identity (abs_winding.json)

- abs_winding.json: 59 points in 6 collections, wind_a 10..63, z 8459..15976, radius from umbilicus (min / median / max) 152 / 897 / 1382
- distance from each abs_winding point to the band surface (min / median / max): 853 / 1275 / 1913; points within 15 of the surface: 0
- 20260701183145-w116-117_gap00 (left panel): no abs_winding point within 15; nearest is 1560 voxels away (wind_a 37)
- 20260701183145-w116-117_gap01 (right panel): no abs_winding point within 15; nearest is 1583 voxels away (wind_a 63)
- verdict c: NOT MEASURABLE: no abs_winding point lies within 15 voxels of any gap chain

## d. Chain statistics

- chains: 2, points: 931
- points per chain (min / median / max): 295 / 466 / 636
- chain length in voxels (min / median / max): 3123 / 4850 / 6578; total 9701
- step between consecutive written points (min / median / max): 10.0 / 10.3 / 12.0
- ds8 path samples on invalid quads: 0 / 4746 = 0.0000
- angular span around the umbilicus per chain, degrees (min / median / max): 7.6 / 24.3 / 41.1
  - 20260701183145-w116-117_gap00: left panel, blocks B1 | B4, ds8 rows 1906..5110, cols 5847..6403, corridor width 1324 ds8 px, 636 pts, 6578 vx, z 9653..15055, radius 1960 / 2231 / 2558, span 41.1 deg
  - 20260701183145-w116-117_gap01: right panel, blocks B2 | B3, ds8 rows 1286..2826, cols 12967..13138, corridor width 520 ds8 px, 295 pts, 3123 vx, z 13463..16219, radius 2154 / 2817 / 3175, span 7.6 deg
