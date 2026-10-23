# layout_constraints report: band 20260701183145-w116-117, text lines (slice 2b)

Slice 1 text-line extractor on the band with {'sigma': [15, 150], 'min_width': 500} (other parameters as slice 1). Units are dataset voxels (9.6 um).

## Extraction and seam self-check

- blobs at least 500 ds8 px wide: 71; dropped as merged lines (height over 1.8 x median): 9; text-line paths: 62
- seam at ds8 col 8358: 2D paths crossing it before any filtering: 0; touching it (ending within 50 px): 2; split at the seam: 0; 2D paths crossing it after the split: 0
- written chains whose ds8 col range spans the seam: 0 of 62

## a. Frame sanity

- projected bbox min [1695.3, 1515.3, 5509.3] max [7157.5, 7028.4, 17939.8]
- mesh meta.json bbox / 4: min [1278.7, 1446.3, 3003.5] max [7533.0, 7623.5, 17998.7]
- projected points inside mesh bbox / 4: True
- 2D registration: ink image papyrus mask (gray > 20, resized to the 6732 x 3748 grid) vs mesh valid vertices: IoU 0.848 (image 0.743 of the area, mesh 0.876); image papyrus on invalid mesh: 0.0000 of the grid, mesh valid but not rendered in the image: 0.1329
- the same IoU on the lower half of the grid (rows 1874..3747): 0.979
- umbilicus over z 5509..17940: x 3893..4907, y 3297..5464
- radius from umbilicus, our points (min / median / max): 1251 / 2283 / 3099
- radius from umbilicus, human same_windings points in the same z range (n=5413, min / median / max): 133 / 706 / 2942
- radius from umbilicus, all valid mesh vertices (min / median / max): 1206 / 2303 / 3363
- angle swept around the umbilicus along each mesh row (every 250th row, 14 rows; two windings = 720): min / median / max 198 / 718 / 720 deg; grid columns per 360 deg (median) 3252 (= 8130 ds8 px)
- verdict a (inside bbox, min radius >= 20, max radius <= 1.2 x human max): PASS

## b. Human same_windings

- empty again: human points within 50 voxels of our points: 0 of 5413 (closest 162); no human collection lies on this band (report_w116.md: 0 of 125).

## c. abs_winding.json

- far again: nearest abs_winding point to any of our points is 874 voxels away (within 15: 0).

## d. Chain statistics

- chains: 62 (left panel 36, right panel 26), points: 12978
- points per chain (min / median / max): 90 / 176 / 485
- chain length in voxels (min / median / max): 1026 / 1979 / 5340; total 140974
- step between consecutive written points (min / median / max): 10.0 / 10.4 / 60.2
- ds8 path samples on invalid quads: 0 / 69498 = 0.0000
- angular span around the umbilicus per chain, degrees (min / median / max): 15.5 / 43.4 / 119.6; chains over 360 deg: 0; over 180 deg: 0
- ds8 column width per chain (min / median / max): 503 / 960 / 2664 (one turn is about 8130 ds8 px)
  - 20260701183145-w116-117_line00: right, ds8 rows 517..600, cols 12071..12720, 110 pts, 1198 vx, z 17643..17930, span 27.7 deg
  - 20260701183145-w116-117_line01: left, ds8 rows 592..638, cols 4082..4841, 131 pts, 1435 vx, z 17532..17772, span 31.3 deg
  - 20260701183145-w116-117_line02: right, ds8 rows 770..724, cols 11355..12700, 228 pts, 2562 vx, z 17370..17900, span 63.1 deg
  - 20260701183145-w116-117_line03: left, ds8 rows 798..839, cols 3308..4702, 240 pts, 2741 vx, z 17124..17940, span 63.9 deg
  - 20260701183145-w116-117_line04: right, ds8 rows 1062..1102, cols 10990..12397, 249 pts, 2843 vx, z 16751..17785, span 66.4 deg
  - 20260701183145-w116-117_line05: left, ds8 rows 1082..1152, cols 3018..4554, 273 pts, 3079 vx, z 16614..17620, span 71.6 deg
  - 20260701183145-w116-117_line06: right, ds8 rows 1438..1476, cols 11379..12366, 190 pts, 2040 vx, z 16163..16858, span 44.0 deg
  - 20260701183145-w116-117_line07: left, ds8 rows 1456..1600, cols 3032..4899, 361 pts, 3827 vx, z 15645..16997, span 75.1 deg
  - 20260701183145-w116-117_line08: left, ds8 rows 1764..1710, cols 2036..2561, 106 pts, 1081 vx, z 16505..16679, span 24.2 deg
  - 20260701183145-w116-117_line09: right, ds8 rows 1846..1808, cols 10998..12694, 326 pts, 3513 vx, z 15307..16407, span 73.9 deg
  - 20260701183145-w116-117_line10: left, ds8 rows 1772..2000, cols 2950..4969, 378 pts, 4135 vx, z 14886..16454, span 82.0 deg
  - 20260701183145-w116-117_line11: right, ds8 rows 1962..1970, cols 13524..14182, 132 pts, 1351 vx, z 14891..15043, span 32.0 deg
  - 20260701183145-w116-117_line12: right, ds8 rows 2166..2239, cols 10567..12729, 408 pts, 4422 vx, z 14575..15996, span 88.4 deg
  - 20260701183145-w116-117_line13: left, ds8 rows 2226..2296, cols 3373..5102, 332 pts, 3513 vx, z 14362..15426, span 74.8 deg
  - 20260701183145-w116-117_line14: right, ds8 rows 2204..2250, cols 13386..14998, 324 pts, 3328 vx, z 14509..14718, span 78.3 deg
  - 20260701183145-w116-117_line15: right, ds8 rows 2550..2545, cols 14959..15590, 123 pts, 1280 vx, z 14138..14528, span 35.3 deg
  - 20260701183145-w116-117_line16: left, ds8 rows 2543..2677, cols 6701..7513, 154 pts, 1715 vx, z 14092..14452, span 42.7 deg
  - 20260701183145-w116-117_line17: right, ds8 rows 2466..2665, cols 9973..12637, 485 pts, 5340 vx, z 13839..15429, span 113.6 deg
  - 20260701183145-w116-117_line18: right, ds8 rows 2636..2646, cols 13370..14940, 316 pts, 3257 vx, z 13674..13945, span 78.3 deg
  - 20260701183145-w116-117_line19: left, ds8 rows 2575..2689, cols 2547..3277, 147 pts, 1498 vx, z 14654..15010, span 26.6 deg
  - 20260701183145-w116-117_line20: left, ds8 rows 2630..2667, cols 6490..7037, 105 pts, 1094 vx, z 13835..14066, span 25.8 deg
  - 20260701183145-w116-117_line21: left, ds8 rows 2829..2833, cols 6836..7456, 119 pts, 1255 vx, z 13644..14063, span 32.7 deg
  - 20260701183145-w116-117_line22: right, ds8 rows 2835..2838, cols 10616..11802, 216 pts, 2387 vx, z 14185..14692, span 43.8 deg
  - 20260701183145-w116-117_line23: left, ds8 rows 2784..2912, cols 3369..4903, 304 pts, 3117 vx, z 13258..14427, span 65.4 deg
  - 20260701183145-w116-117_line24: right, ds8 rows 2951..2951, cols 11024..12813, 335 pts, 3643 vx, z 13254..14458, span 74.7 deg
  - 20260701183145-w116-117_line25: left, ds8 rows 3064..3060, cols 6708..7644, 176 pts, 2003 vx, z 13146..13748, span 43.0 deg
  - 20260701183145-w116-117_line26: left, ds8 rows 3058..3070, cols 4797..5602, 160 pts, 1714 vx, z 12885..13074, span 42.3 deg
  - 20260701183145-w116-117_line27: left, ds8 rows 3196..3170, cols 6693..7320, 129 pts, 1309 vx, z 12897..13350, span 32.0 deg
  - 20260701183145-w116-117_line28: right, ds8 rows 3304..3272, cols 13459..14442, 192 pts, 1992 vx, z 12515..12613, span 52.7 deg
  - 20260701183145-w116-117_line29: left, ds8 rows 3516..3594, cols 2456..3069, 123 pts, 1247 vx, z 13105..13247, span 21.7 deg
  - 20260701183145-w116-117_line30: left, ds8 rows 3709..3816, cols 4308..5520, 227 pts, 2506 vx, z 11573..12155, span 60.8 deg
  - 20260701183145-w116-117_line31: right, ds8 rows 3868..3896, cols 10981..11507, 100 pts, 1055 vx, z 12439..12742, span 15.5 deg
  - 20260701183145-w116-117_line32: left, ds8 rows 3880..3870, cols 2526..3064, 111 pts, 1161 vx, z 12462..12568, span 18.7 deg
  - 20260701183145-w116-117_line33: left, ds8 rows 3942..3975, cols 7118..7685, 96 pts, 1116 vx, z 11891..12113, span 27.0 deg
  - 20260701183145-w116-117_line34: left, ds8 rows 4170..4078, cols 5052..6468, 259 pts, 2879 vx, z 11036..11334, span 67.8 deg
  - 20260701183145-w116-117_line35: right, ds8 rows 4252..4194, cols 15327..15848, 93 pts, 1035 vx, z 11225..11560, span 24.3 deg
  - 20260701183145-w116-117_line36: left, ds8 rows 4208..4284, cols 6719..7520, 141 pts, 1577 vx, z 11173..11427, span 36.2 deg
  - 20260701183145-w116-117_line37: right, ds8 rows 4359..4309, cols 13767..15465, 292 pts, 3360 vx, z 10764..11168, span 76.3 deg
  - 20260701183145-w116-117_line38: left, ds8 rows 4384..4364, cols 3614..4134, 91 pts, 1099 vx, z 11067..11412, span 23.9 deg
  - 20260701183145-w116-117_line39: left, ds8 rows 4508..4576, cols 6918..7640, 126 pts, 1489 vx, z 10639..10928, span 32.7 deg
  - 20260701183145-w116-117_line40: left, ds8 rows 4601..4724, cols 3580..4500, 177 pts, 1880 vx, z 10365..11040, span 38.3 deg
  - 20260701183145-w116-117_line41: right, ds8 rows 4726..4788, cols 11954..12531, 107 pts, 1146 vx, z 10361..10727, span 27.4 deg
  - 20260701183145-w116-117_line42: left, ds8 rows 5048..5066, cols 4698..5328, 108 pts, 1239 vx, z 9870..10134, span 28.0 deg
  - 20260701183145-w116-117_line43: left, ds8 rows 5043..5067, cols 3461..4182, 138 pts, 1457 vx, z 10233..10436, span 25.4 deg
  - 20260701183145-w116-117_line44: right, ds8 rows 5314..5322, cols 8367..8963, 120 pts, 1270 vx, z 9833..9953, span 23.4 deg
  - 20260701183145-w116-117_line45: left, ds8 rows 5367..5403, cols 3708..5614, 355 pts, 3872 vx, z 9296..9776, span 82.5 deg
  - 20260701183145-w116-117_line46: right, ds8 rows 5520..5468, cols 11904..13358, 258 pts, 2954 vx, z 9301..9579, span 61.8 deg
  - 20260701183145-w116-117_line47: left, ds8 rows 5666..5684, cols 3866..6358, 481 pts, 5080 vx, z 8859..9173, span 119.6 deg
  - 20260701183145-w116-117_line48: right, ds8 rows 5824..5706, cols 12019..13973, 367 pts, 3951 vx, z 8833..8967, span 95.9 deg
  - 20260701183145-w116-117_line49: left, ds8 rows 6094..6085, cols 3815..5827, 370 pts, 4111 vx, z 8159..8326, span 99.4 deg
  - 20260701183145-w116-117_line50: left, ds8 rows 6247..6212, cols 2168..2904, 124 pts, 1440 vx, z 7916..8057, span 31.1 deg
  - 20260701183145-w116-117_line51: left, ds8 rows 6409..6420, cols 4811..5921, 207 pts, 2240 vx, z 7553..7646, span 58.2 deg
  - 20260701183145-w116-117_line52: right, ds8 rows 6454..6456, cols 8385..9177, 160 pts, 1697 vx, z 7550..7644, span 37.4 deg
  - 20260701183145-w116-117_line53: right, ds8 rows 6476..6494, cols 12137..13303, 201 pts, 2329 vx, z 7496..7641, span 63.7 deg
  - 20260701183145-w116-117_line54: left, ds8 rows 6622..6648, cols 1799..3109, 261 pts, 2699 vx, z 7182..7325, span 62.1 deg
  - 20260701183145-w116-117_line55: right, ds8 rows 6830..6814, cols 12402..12992, 100 pts, 1159 vx, z 6905..6937, span 33.0 deg
  - 20260701183145-w116-117_line56: left, ds8 rows 6840..6784, cols 4875..6275, 261 pts, 2864 vx, z 6832..6937, span 66.9 deg
  - 20260701183145-w116-117_line57: left, ds8 rows 6860..6934, cols 3703..4206, 90 pts, 1026 vx, z 6628..6824, span 18.0 deg
  - 20260701183145-w116-117_line58: left, ds8 rows 6928..6894, cols 1648..2962, 261 pts, 2710 vx, z 6570..6752, span 67.1 deg
  - 20260701183145-w116-117_line59: right, ds8 rows 7130..7194, cols 12314..13310, 172 pts, 1966 vx, z 6207..6384, span 56.9 deg
  - 20260701183145-w116-117_line60: right, ds8 rows 7499..7430, cols 10128..10861, 150 pts, 1538 vx, z 5744..5871, span 40.5 deg
  - 20260701183145-w116-117_line61: left, ds8 rows 7496..7506, cols 1766..2377, 102 pts, 1150 vx, z 5509..5561, span 33.1 deg
