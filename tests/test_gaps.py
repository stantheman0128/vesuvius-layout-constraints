import numpy as np

from layout_constraints import CELL, DS
from layout_constraints.extract_gaps import extract_gaps

H, W = 3000, 2400                      # ds8 px
BLOCKS = ((200, 1000), (1500, 2300))   # text columns; blank corridor 1000..1500, centre 1250


def synthetic():
    """Papyrus (40) with two text columns: lines 200 rows tall every 300, dashes 80 of every 100 cols (230)."""
    g = np.full((H, W), 40, np.uint8)
    rows = np.zeros(H, bool)
    for r in range(300, 2700, 300):
        rows[r:r + 200] = True
    cols = np.zeros(W, bool)
    for c0, c1 in BLOCKS:
        cols[c0:c1] = (np.arange(c0, c1) % 100) < 80
    g[np.ix_(rows, cols)] = 230
    return g, np.ones((H * DS // CELL, W * DS // CELL), bool)


def test_one_gap_path_at_corridor_centre():
    g, valid = synthetic()
    paths, blocks, _, cands = extract_gaps(g, valid)
    assert len(blocks) == 2
    assert len(paths) == 1, cands
    p = paths[0]
    assert np.all(np.diff(p["rows"]) == 1)                      # one sample per ds8 row, top to bottom
    assert p["rows"][-1] - p["rows"][0] >= 2000
    assert np.all(np.abs(p["cols"] - 1250) < 30)
    assert p["blocks"] == [1, 2]


def test_corridor_over_invalid_mesh_is_rejected():
    g, valid = synthetic()
    valid[:, 1150 * DS // CELL:1350 * DS // CELL] = False       # a -1 strip down the corridor (a seam)
    paths, blocks, _, cands = extract_gaps(g, valid)
    assert len(blocks) == 2
    assert paths == []
    assert len(cands) == 1 and "invalid" in cands[0]["status"]


def test_corridor_over_unrendered_image_is_rejected():
    g, valid = synthetic()
    g[:, 1150:1350] = 0                                         # mesh valid but no ink render there
    paths, _, _, cands = extract_gaps(g, valid)
    assert paths == []
    assert len(cands) == 1 and "invalid" in cands[0]["status"]
