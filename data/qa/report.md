# layout_constraints report: segment 20230702185753

Units are dataset voxels (9.6 um). 'Our points' are the written JSON points (10 voxel spacing). 'Dense chains' are every valid ds8 path sample before decimation (about 2 voxels apart). Human lines are densified to 1 voxel steps (gaps over 50 voxels not bridged).

## a. Frame sanity

- projected bbox min [3705.1, 2950.6, 7464.9] max [5276.2, 5931.2, 18395.3]
- mesh meta.json bbox / 4: min [3509.4, 2909.3, 7359.6] max [5305.9, 6100.2, 18479.9]
- projected points inside mesh bbox / 4: True
- 2D registration: ink image papyrus mask (gray > 20, resized to the 1820 x 2530 grid) vs mesh valid vertices: IoU 0.984 (image 0.861 of the area, mesh 0.875)
- umbilicus over z 7465..18395: x 4143..4907, y 3368..5611
- radius from umbilicus, our points (min / median / max): 165 / 421 / 723
- radius from umbilicus, human same_windings points in the same z range (n=4749, min / median / max): 133 / 781 / 2942
- radius from umbilicus, all valid mesh vertices (min / median / max): 137 / 428 / 766
- verdict a (inside bbox, min radius >= 20, max radius <= 1.2 x human max): PASS

## b/c. Agreement with human same_windings lines, and translated controls

- human points in the projected bbox expanded by 20: 3618 of 5413 (from 125 collections)

| copy | human -> our dense chains | our points -> human (all) | our points -> human (only those within 50) |
|---|---|---|---|
| unshifted | n=3618, median 253.0, within 5: 0.008, within 10: 0.014 | n=10934, median 701.9, within 5: 0.005, within 10: 0.008 | n=252, median 22.7, within 5: 0.202, within 10: 0.337 |
| x +25 | n=3618, median 256.6, within 5: 0.001, within 10: 0.002 | n=10934, median 695.3, within 5: 0.000, within 10: 0.001 | n=218, median 24.6, within 5: 0.018, within 10: 0.064 |
| y +25 | n=3618, median 253.1, within 5: 0.001, within 10: 0.002 | n=10934, median 700.0, within 5: 0.000, within 10: 0.001 | n=213, median 28.3, within 5: 0.019, within 10: 0.047 |

Closest approach of each human collection to our dense chains (human lines mostly run along z, our text lines run around the scroll, so a correct frame shows up as near-zero crossings):

| copy | collections with closest approach <= 5 | <= 10 | <= 25 | median of closest approaches under 50 |
|---|---|---|---|---|
| unshifted | 6 | 7 | 9 | 24.8 (n=17) |
| x +25 | 4 | 6 | 10 | 19.2 (n=16) |
| y +25 | 4 | 4 | 7 | 21.7 (n=12) |

Extra: human points in the bbox vs the segment surface itself (all valid mesh vertices / 4; grid spacing is 5 voxels, so a point on the surface can be up to about 3.5 voxels from the nearest vertex):

| copy | human -> mesh vertices | human collections (at least 5 points in the bbox) with at least 80% of those points within 5 of the surface |
|---|---|---|
| unshifted | n=3618, median 174.0, within 5: 0.097, within 10: 0.100 | 8 of 90 |
| x +25 | n=3618, median 175.2, within 5: 0.050, within 10: 0.082 | 0 of 90 |
| y +25 | n=3618, median 182.3, within 5: 0.043, within 10: 0.067 | 0 of 90 |

- verdict c (unshifted beats both shifted copies on 'our points -> human within 10' and on 'collections with closest approach <= 10'): PASS

## d. Chain statistics

- chains: 32 (30 text-line, 2 margin), points: 10934
- points per chain (min / median / max): 84 / 328 / 1007
- chain length in voxels (min / median / max): 845 / 3600 / 11163; total 117829
- step between consecutive written points (min / median / max): 10.0 / 10.2 / 60.2
- ds8 path samples on invalid quads: 0 / 57549 = 0.0000 (per kind [samples, invalid]: {"text_line": [46987, 0], "margin": [10562, 0]})
- angular span around the umbilicus per chain, degrees (min / median / max): 99 / 408 / 813; chains over 360 deg: 17, over the largest human same_windings span (176 deg): 22. A chain over 360 deg crosses more than one wrap, which breaks the same-wrap meaning of a same-winding collection.
  - 20230702185753_line00: 131 pts, 1445 vx, z 18072..18252, span 189 deg
  - 20230702185753_line01: 139 pts, 1506 vx, z 18016..18395, span 205 deg
  - 20230702185753_line02: 491 pts, 5273 vx, z 17446..17963, span 644 deg
  - 20230702185753_line03: 577 pts, 6446 vx, z 16874..17304, span 813 deg
  - 20230702185753_line04: 535 pts, 5924 vx, z 16352..16669, span 733 deg
  - 20230702185753_line05: 117 pts, 1248 vx, z 15738..15994, span 138 deg
  - 20230702185753_line06: 389 pts, 4094 vx, z 15751..16047, span 522 deg
  - 20230702185753_line07: 332 pts, 3715 vx, z 15013..15377, span 494 deg
  - 20230702185753_line08: 93 pts, 1087 vx, z 15057..15157, span 138 deg
  - 20230702185753_line09: 138 pts, 1536 vx, z 14535..14616, span 181 deg
  - 20230702185753_line10: 352 pts, 3702 vx, z 14496..14710, span 472 deg
  - 20230702185753_line11: 91 pts, 996 vx, z 13817..14029, span 111 deg
  - 20230702185753_line12: 400 pts, 4342 vx, z 13815..14125, span 545 deg
  - 20230702185753_line13: 84 pts, 845 vx, z 13334..13441, span 108 deg
  - 20230702185753_line14: 567 pts, 6070 vx, z 13108..13370, span 763 deg
  - 20230702185753_line15: 575 pts, 6203 vx, z 12470..12883, span 759 deg
  - 20230702185753_line16: 84 pts, 874 vx, z 11974..12079, span 105 deg
  - 20230702185753_line17: 305 pts, 3222 vx, z 11934..12270, span 431 deg
  - 20230702185753_line18: 154 pts, 1600 vx, z 11347..11846, span 174 deg
  - 20230702185753_line19: 411 pts, 4301 vx, z 11329..11705, span 563 deg
  - 20230702185753_line20: 87 pts, 895 vx, z 10957..11008, span 125 deg
  - 20230702185753_line21: 338 pts, 3681 vx, z 10808..11141, span 448 deg
  - 20230702185753_line22: 232 pts, 2480 vx, z 10786..10955, span 303 deg
  - 20230702185753_line23: 94 pts, 1015 vx, z 10291..10359, span 99 deg
  - 20230702185753_line24: 284 pts, 3184 vx, z 10241..10440, span 385 deg
  - 20230702185753_line25: 344 pts, 3685 vx, z 9465..9631, span 473 deg
  - 20230702185753_line26: 552 pts, 5835 vx, z 8753..8995, span 692 deg
  - 20230702185753_line27: 607 pts, 6369 vx, z 8086..8262, span 786 deg
  - 20230702185753_line28: 153 pts, 1601 vx, z 7539..7625, span 195 deg
  - 20230702185753_line29: 325 pts, 3519 vx, z 7465..7655, span 453 deg
  - 20230702185753_margin_left: 946 pts, 9973 vx, z 7493..16524, span 109 deg
  - 20230702185753_margin_right: 1007 pts, 11163 vx, z 7553..17555, span 129 deg
