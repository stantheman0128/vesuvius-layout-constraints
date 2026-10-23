"""Same-winding point collections from 2D page layout on a flattened segment."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "out"
QA = DATA / "qa"
SEG = "20230702185753"
INK = DATA / "ink_ds8.jpg"
MESH = DATA / "mesh"
HUMAN = DATA / "human"
PATHS2D = OUT / f"{SEG}_paths2d.json"
DENSE = OUT / f"{SEG}_dense.npz"
COLLECTIONS = OUT / f"{SEG}_text_lines.json"

DS = 8            # ds8 pixel = 8 full-res pixels
CELL = 20         # one mesh grid cell = 20 full-res pixels (meta.json scale 0.05)
VOXEL_DIV = 4     # 2.4 um mesh voxels / 4 = 9.6 um dataset voxels
MIN_SPACING = 10.0  # dataset voxels between kept points

# slice 2: two-winding band, intercolumnar gaps
BAND = "20260701183145-w116-117"
BAND_DIR = DATA / "w116"
BAND_INK = BAND_DIR / "ink_ds8.jpg"
BAND_MESH = BAND_DIR / "mesh"
BAND_MESH_NAME = "20260701183145-on-20260411134726-2.4um.tifxyz"
BAND_GAPS2D = OUT / f"{BAND}_gaps2d.json"
BAND_DENSE = OUT / f"{BAND}_gaps_dense.npz"
BAND_GAPS = OUT / f"{BAND}_column_gaps.json"
BAND_LINES2D = OUT / f"{BAND}_lines2d.json"
BAND_LINES_DENSE = OUT / f"{BAND}_lines_dense.npz"
BAND_LINES = OUT / f"{BAND}_text_lines.json"
