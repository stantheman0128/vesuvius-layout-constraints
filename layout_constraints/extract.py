"""Text-line centre paths and column margin paths from the ds8 ink image."""
import json

import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

from . import INK, OUT, PATHS2D, QA, SEG

INK_THRESHOLD = 125      # Otsu on the papyrus area of this image gives 125
SIGMA = (15, 100)        # (rows, cols): smear letters along the line, keep lines apart
DENSITY_THRESHOLD = 0.3
MIN_WIDTH = 400          # ds8 px, for text-line paths
MIN_PIECE_WIDTH = 100    # ds8 px, for line ends used by the margins (short words at line starts)
MAX_HEIGHT_RATIO = 1.8   # blobs taller than this x median are merged lines: dropped
LINE_GROUP_DY = 120      # blobs whose centroid rows differ less than this are one text line
MARGIN_TOL = 80          # ds8 px off the robust margin fit counts as an outlier
MARGIN_MIN_INLIERS = 0.6


def load_ink(path=INK):
    Image.MAX_IMAGE_PIXELS = None
    return np.asarray(Image.open(path).convert("L"))


def line_paths(gray, sigma=SIGMA, density_threshold=DENSITY_THRESHOLD, min_width=MIN_WIDTH,
               min_piece_width=MIN_PIECE_WIDTH, max_height_ratio=MAX_HEIGHT_RATIO):
    """Return (paths, pieces, dropped). Keyword defaults are the slice 1 values.

    paths: list of (rows, cols) float arrays, one per line blob, ordered left to right.
    pieces: (centroid_row, first_col, last_col) of every blob at least MIN_PIECE_WIDTH wide.
    """
    density = gaussian_filter((gray > INK_THRESHOLD).astype(np.float32), sigma)
    n, lab, st, cen = cv2.connectedComponentsWithStats((density > density_threshold).astype(np.uint8), connectivity=8)
    wide = [k for k in range(1, n) if st[k, cv2.CC_STAT_WIDTH] >= min_width]
    pieces = np.array([(cen[k][1], st[k, 0], st[k, 0] + st[k, 2] - 1)
                       for k in range(1, n) if st[k, cv2.CC_STAT_WIDTH] >= min_piece_width])
    hmed = np.median(st[wide, cv2.CC_STAT_HEIGHT])
    paths, dropped = [], 0
    for k in wide:
        x0, y0, w, h = st[k, :4]
        if h > max_height_ratio * hmed:
            dropped += 1
            continue
        wgt = np.where(lab[y0:y0 + h, x0:x0 + w] == k, density[y0:y0 + h, x0:x0 + w], 0.0)
        colsum = wgt.sum(0)
        ok = colsum > 0
        cy = (wgt * np.arange(y0, y0 + h)[:, None]).sum(0)[ok] / colsum[ok]
        paths.append((cy, np.arange(x0, x0 + w, dtype=float)[ok]))
    paths.sort(key=lambda p: (np.median(p[0]), p[1][0]))
    return paths, pieces, dropped


def margin_paths(paths, pieces):
    """Left and right margins: piecewise-linear vertical paths through text-line ends.

    For each text line, its end is the outermost piece (any blob at least MIN_PIECE_WIDTH
    wide) whose centroid row is within LINE_GROUP_DY of the line. A margin is kept only if
    at least MARGIN_MIN_INLIERS of the lines end within MARGIN_TOL of a straight fit.
    """
    rows = np.sort([np.median(p[0]) for p in paths])
    groups = [rows[0]]
    for r in rows[1:]:
        if r - groups[-1] >= LINE_GROUP_DY:
            groups.append(r)
    out, notes = {}, {}
    for side, col, pick in (("left", 1, np.argmin), ("right", 2, np.argmax)):
        ends = []
        for r in groups:
            near = pieces[np.abs(pieces[:, 0] - r) < LINE_GROUP_DY]
            k = pick(near[:, col])
            ends.append((near[k, 0], near[k, col]))
        ends = np.array(ends)
        inl = np.ones(len(ends), bool)
        for _ in range(3):  # iterated least squares with outlier rejection
            a, b = np.polyfit(ends[inl, 0], ends[inl, 1], 1)
            inl = np.abs(ends[:, 1] - (a * ends[:, 0] + b)) < MARGIN_TOL
        notes[side] = f"{inl.sum()}/{len(ends)} line ends within {MARGIN_TOL} px of the fit"
        if inl.mean() >= MARGIN_MIN_INLIERS and inl.sum() >= 2:
            e = ends[inl]
            r = np.arange(np.ceil(e[0, 0]), np.floor(e[-1, 0]) + 1)
            out[side] = (r, np.interp(r, e[:, 0], e[:, 1]))
        else:
            notes[side] += " (skipped)"
    return out, notes


def save_overlay(gray, paths, margins, path):
    img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    for rows, cols in paths:
        cv2.polylines(img, [np.stack([cols, rows], 1).round().astype(np.int32)], False, (0, 0, 255), 8)
    for rows, cols in margins.values():
        cv2.polylines(img, [np.stack([cols, rows], 1).round().astype(np.int32)], False, (255, 255, 0), 8)
    img = cv2.resize(img, (img.shape[1] // 2, img.shape[0] // 2), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(path), img)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    gray = load_ink()
    paths, pieces, dropped = line_paths(gray)
    margins, notes = margin_paths(paths, pieces)
    items = [{"name": f"{SEG}_line{k:02d}", "kind": "text_line", "rows": r.tolist(), "cols": c.tolist()}
             for k, (r, c) in enumerate(paths)]
    items += [{"name": f"{SEG}_margin_{s}", "kind": "margin", "rows": r.tolist(), "cols": c.tolist()}
              for s, (r, c) in margins.items()]
    PATHS2D.write_text(json.dumps({"image_shape": list(gray.shape), "dropped_merged_blobs": dropped,
                                   "margin_notes": notes, "paths": items}))
    save_overlay(gray, paths, margins, QA / f"{SEG}_overlay.png")
    print(f"extract: {len(paths)} text-line paths ({dropped} merged blobs dropped), margins: {notes}")
    print(f"wrote {PATHS2D} and {QA / f'{SEG}_overlay.png'}")


if __name__ == "__main__":
    main()
