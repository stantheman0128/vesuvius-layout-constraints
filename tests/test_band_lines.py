import numpy as np

from layout_constraints.band_lines import seam_relation, split_at_seam


def test_split_at_seam_cuts_crossing_path_and_drops_short_piece():
    cols = np.arange(0, 2001, dtype=float)
    rows = 100 + 0.01 * cols
    pieces = split_at_seam(rows, cols, 1200.0, min_width=500)
    assert [(p[1][0], p[1][-1]) for p in pieces] == [(0, 1199), (1200, 2000)]
    np.testing.assert_allclose(pieces[1][0], rows[1200:])
    assert all(seam_relation(c, 1200.0) != "cross" for _, c in pieces)
    pieces = split_at_seam(rows, cols, 1700.0, min_width=500)  # right piece only 301 px wide
    assert [(p[1][0], p[1][-1]) for p in pieces] == [(0, 1699)]
    assert seam_relation(cols, 1200.0) == "cross"
    assert seam_relation(cols[1230:], 1200.0) == "touch"
    assert seam_relation(cols[1300:], 1200.0) is None
