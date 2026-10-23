"""Intercolumnar gap centre paths from the ds8 ink image of a multi-column band.

Work is done on 4 x 4 blocks of ds8 pixels (F = 4). Text density = Gaussian-smoothed binary ink,
normalised by the smoothed papyrus fraction and zeroed off the papyrus. Text blocks (columns) are
regions of high density, split by watershed from high-density cores. Two blocks that are next to
each other in a row bound a corridor; the gap path is the midpoint of the low (finer) density run
around the least-density column in it.
"""
import json

import cv2
import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter, gaussian_filter1d, median_filter
from skimage.segmentation import watershed

from . import BAND, BAND_GAPS2D, BAND_INK, BAND_MESH, CELL, DS, OUT, QA
from .extract import INK_THRESHOLD, load_ink

F = 4                     # ds8 px per work cell, each way
PAPYRUS = 20              # gray > 20 is rendered papyrus (outside the render is 0 to 16)
SIGMA_BLOCK = (600, 150)  # ds8 px (rows, cols): density for the text blocks
SIGMA_PATH = (600, 40)    # ds8 px: finer across the corridor, for the gap centre
BLOCK_LO = 0.12           # density above this is part of a block
BLOCK_CORE = 0.20         # density above this seeds a block (watershed marker)
MIN_CORE_AREA = 100_000   # ds8 px^2
MIN_BLOCK_HEIGHT = 1000   # ds8 rows
MIN_OVERLAP = 0.5         # shared rows / rows of the shorter block
MAX_INVALID_ROWS = 0.05   # corridor rows crossing invalid mesh or unrendered area: above this, rejected
MAX_BREAK = 100           # ds8 rows; shorter breaks in a corridor (blocks touching) are bridged
MIN_GAP_LEN = 500         # ds8 rows
MAX_SLOPE = 0.35          # |d col / d row| of a straight fit (19 deg); gaps run along z, blob edges do not
MAX_CONTRAST = 0.25       # least corridor density / density of the flanking blocks; above, not blank
FLANK = 600               # ds8 px of each block next to the corridor used for the contrast
MAX_WIDTH_RATIO = 1.5     # corridors wider than this x the median width are rejected
SMOOTH = 100              # ds8 rows: median filter and Gaussian sigma on the path column


def work_grids(gray):
    """Ink fraction and papyrus fraction per F x F cell."""
    h, w = gray.shape[0] // F * F, gray.shape[1] // F * F
    g = gray[:h, :w]
    ink = (g > INK_THRESHOLD).reshape(h // F, F, w // F, F).mean((1, 3), dtype=np.float32)
    on = (g > PAPYRUS).reshape(h // F, F, w // F, F).mean((1, 3), dtype=np.float32)
    return ink, on


def density(ink, on, sigma):
    s = (sigma[0] / F, sigma[1] / F)
    num, den = gaussian_filter(ink, s), gaussian_filter(on, s)
    return np.where(on > 0.5, num / np.maximum(den, 1e-6), 0.0).astype(np.float32)


def valid_map(on, grid_valid):
    """Per work cell: rendered papyrus and a mesh quad with no -1 vertex at the cell centre."""
    q = grid_valid[:-1, :-1] & grid_valid[1:, :-1] & grid_valid[:-1, 1:] & grid_valid[1:, 1:]
    centre = lambda n: ((np.arange(n) * F + (F - 1) / 2) * DS / CELL).astype(int)
    i = np.clip(centre(on.shape[0]), 0, q.shape[0] - 1)
    j = np.clip(centre(on.shape[1]), 0, q.shape[1] - 1)
    return (on > 0.5) & q[np.ix_(i, j)]


def find_blocks(d):
    """Watershed of -density from cores, inside density > BLOCK_LO. Returns (labels, blocks)."""
    n, cores, st, _ = cv2.connectedComponentsWithStats((d > BLOCK_CORE).astype(np.uint8), connectivity=8)
    big = np.zeros(n, np.int32)
    keep = [k for k in range(1, n) if st[k, cv2.CC_STAT_AREA] * F * F >= MIN_CORE_AREA]
    big[keep] = np.arange(1, len(keep) + 1)
    lab = watershed(-d, big[cores], mask=d > BLOCK_LO).astype(np.int32)
    blocks, relabel = [], np.zeros(lab.max() + 1, np.int32)
    for k in range(1, lab.max() + 1):
        rr, cc = np.nonzero(lab == k)
        if len(rr) == 0 or (rr.max() - rr.min() + 1) * F < MIN_BLOCK_HEIGHT:
            continue
        relabel[k] = len(blocks) + 1
        blocks.append({"id": len(blocks) + 1, "rows": [int(rr.min()) * F, int(rr.max() + 1) * F - 1],
                       "cols": [int(cc.min()) * F, int(cc.max() + 1) * F - 1], "area": int(len(rr)) * F * F})
    return relabel[lab], blocks


def corridors(lab):
    """{(a, b): {row: (c0, c1)}}: in each work row, consecutive blocks a, b (sorted by first column)
    with only unlabelled cells between them; (c0, c1) is that empty interval, inclusive."""
    out = {}
    for r in range(lab.shape[0]):
        row = lab[r]
        ks = np.unique(row[row > 0])
        if len(ks) < 2:
            continue
        span = {k: (np.flatnonzero(row == k)[[0, -1]]) for k in ks}
        order = sorted(ks, key=lambda k: span[k][0])
        for a, b in zip(order[:-1], order[1:]):
            c0, c1 = span[a][1] + 1, span[b][0] - 1
            if c1 >= c0 and not row[c0:c1 + 1].any():
                out.setdefault((int(a), int(b)), {})[r] = (int(c0), int(c1))
    return out


def centre_col(row, c0, c1):
    """Midpoint of the run below BLOCK_LO around the least-density column in [c0, c1] (clipped to it)."""
    c = c0 + int(np.argmin(row[c0:c1 + 1]))
    i = j = c
    while i > c0 and row[i - 1] < BLOCK_LO:
        i -= 1
    while j < c1 and row[j + 1] < BLOCK_LO:
        j += 1
    return (i + j) / 2


def runs(rows, max_break):
    """Split sorted rows into runs; gaps up to max_break rows stay inside a run."""
    rows = np.asarray(rows)
    cut = np.flatnonzero(np.diff(rows) > max_break + 1) + 1
    return np.split(rows, cut)


def extract_gaps(gray, grid_valid):
    """Returns (paths, blocks, labels, candidates). paths: dicts with ds8 rows/cols (one per ds8 row,
    top to bottom) and meta; candidates: every block pair considered, with the reason kept or not."""
    ink, on = work_grids(gray)
    d_blk, d_path = density(ink, on, SIGMA_BLOCK), density(ink, on, SIGMA_PATH)
    valid = valid_map(on, grid_valid)
    lab, blocks = find_blocks(d_blk)
    by_id = {b["id"]: b for b in blocks}
    cands = []
    for (a, b), rowmap in sorted(corridors(lab).items()):
        ba, bb = by_id[a], by_id[b]
        shared = min(ba["rows"][1], bb["rows"][1]) - max(ba["rows"][0], bb["rows"][0]) + 1
        shorter = min(ba["rows"][1] - ba["rows"][0], bb["rows"][1] - bb["rows"][0]) + 1
        c = {"blocks": [a, b], "overlap": round(shared / shorter, 3), "corridor_rows": len(rowmap) * F}
        cands.append(c)
        if shared < MIN_OVERLAP * shorter:
            c["status"] = "rejected: vertical overlap under %.1f of the shorter block" % MIN_OVERLAP
            continue
        rows = sorted(rowmap)
        bad = [r for r in rows if not valid[r, rowmap[r][0]:rowmap[r][1] + 1].all()]
        c["invalid_row_fraction"] = round(len(bad) / len(rows), 3)
        if len(bad) > MAX_INVALID_ROWS * len(rows):
            c["status"] = "rejected: corridor crosses invalid mesh or unrendered area in %d of %d rows" % (
                len(bad), len(rows))
            continue
        good = [r for r in rows if r not in set(bad)]
        c["runs"] = []
        for run in runs(good, MAX_BREAK // F):
            if (run[-1] - run[0] + 1) * F < MIN_GAP_LEN:
                continue
            cols = np.array([centre_col(d_path[r], *rowmap[r]) for r in run])
            width = float(np.median([rowmap[r][1] - rowmap[r][0] + 1 for r in run]) * F)
            slope = float(np.polyfit(run, cols, 1)[0])
            fl = FLANK // F
            contrast = float(np.median([d_path[r, rowmap[r][0]:rowmap[r][1] + 1].min() / max(np.median(np.concatenate(
                [d_blk[r, max(rowmap[r][0] - fl, 0):rowmap[r][0]], d_blk[r, rowmap[r][1] + 1:rowmap[r][1] + 1 + fl]])), 1e-6)
                for r in run]))
            info = {"ds8_rows": [int(run[0]) * F, int(run[-1] + 1) * F - 1], "width": width,
                    "slope": round(slope, 3), "contrast": round(contrast, 3)}
            if abs(slope) > MAX_SLOPE:
                info["status"] = "rejected: |slope| over %.2f" % MAX_SLOPE
            elif contrast > MAX_CONTRAST:
                info["status"] = "rejected: contrast over %.2f (corridor not blank)" % MAX_CONTRAST
            c.setdefault("run_info", []).append(info)
            if "status" not in info:
                c["runs"].append({"rows": run, "cols": cols, "width": width, "info": info})
        if not c["runs"]:
            c["status"] = "rejected: no corridor run of at least %d rows passing slope and contrast" % MIN_GAP_LEN
    widths = [r["width"] for c in cands for r in c.get("runs", [])]
    med = float(np.median(widths)) if widths else 0.0
    paths = []
    for c in cands:
        kept = []
        for run in c.pop("runs", []):
            if run["width"] > MAX_WIDTH_RATIO * med:
                run["info"]["status"] = "rejected: wider than %.1f x the median corridor width (%.0f px)" % (
                    MAX_WIDTH_RATIO, med)
                continue
            run["info"]["status"] = "kept"
            kept.append(run)
            r4 = np.arange(run["rows"][0], run["rows"][-1] + 1)
            c4 = np.interp(r4, run["rows"], run["cols"])  # bridge short breaks
            k = max(int(SMOOTH / F) | 1, 3)
            c4 = gaussian_filter1d(median_filter(c4, size=k, mode="nearest"), SMOOTH / F, mode="nearest")
            rows8 = np.arange(r4[0] * F + (F - 1) / 2, r4[-1] * F + (F - 1) / 2 + 1)
            cols8 = np.interp(rows8, r4 * F + (F - 1) / 2, c4 * F + (F - 1) / 2)
            paths.append({"rows": rows8, "cols": cols8, "blocks": c["blocks"], "width": run["width"],
                          "slope": run["info"]["slope"], "contrast": run["info"]["contrast"],
                          "bridged_rows": int(len(r4) - len(run["rows"])) * F})
        if "status" not in c:
            c["status"] = "kept %d run(s)" % len(kept) if kept else \
                "rejected: wider than %.1f x the median corridor width (%.0f px)" % (MAX_WIDTH_RATIO, med)
    return paths, blocks, lab, cands


def seam_col(gray, grid_valid):
    """Mean column of the mesh-valid but unrendered area in the middle third of the image (the seam
    between the two panels), used only to name each gap's panel."""
    ink, on = work_grids(gray)
    blank = ~(on > 0.5) & valid_map(np.ones_like(on), grid_valid)
    w = blank.shape[1]
    cols = np.nonzero(blank[:, w // 3: 2 * w // 3])[1] + w // 3
    return float(cols.mean() * F + (F - 1) / 2)


def save_overlay(gray, lab, paths, path):
    """Quarter resolution: block outlines red, block ids yellow, gap paths green."""
    img = cv2.cvtColor(cv2.resize(gray, (lab.shape[1], lab.shape[0]), interpolation=cv2.INTER_AREA),
                       cv2.COLOR_GRAY2BGR)
    for k in range(1, lab.max() + 1):
        m = (lab == k).astype(np.uint8)
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(img, cs, -1, (0, 0, 255), 3)
        rr, cc = np.nonzero(m)
        cv2.putText(img, f"B{k}", (int(cc.mean()), int(rr.mean())), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 255), 4)
    for n, p in enumerate(paths):
        pts = np.stack([p["cols"], p["rows"]], 1) / F
        cv2.polylines(img, [pts.round().astype(np.int32)], False, (0, 255, 0), 6)
        x, y = pts[len(pts) // 2]
        cv2.putText(img, f"G{n}", (int(x) + 15, int(y)), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 4)
    cv2.imwrite(str(path), img)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    gray = load_ink(BAND_INK)
    grid_valid = tifffile.imread(BAND_MESH / "z.tif") != -1
    for a in "xy":
        grid_valid &= tifffile.imread(BAND_MESH / f"{a}.tif") != -1
    exp = (gray.shape[0] * DS / CELL, gray.shape[1] * DS / CELL)
    assert exp == grid_valid.shape, f"ds8 {gray.shape} x {DS}/{CELL} = {exp} != mesh grid {grid_valid.shape}"
    paths, blocks, lab, cands = extract_gaps(gray, grid_valid)
    seam = seam_col(gray, grid_valid)
    items = []
    for n, p in enumerate(paths):
        panel = "left" if np.median(p["cols"]) < seam else "right"
        items.append({"name": f"{BAND}_gap{n:02d}", "kind": "intercolumnar_gap",
                      "rows": p["rows"].tolist(), "cols": p["cols"].tolist(),
                      "meta": {"panel": panel, "blocks": p["blocks"], "corridor_width_ds8": p["width"],
                               "slope": p["slope"], "contrast": p["contrast"],
                               "bridged_rows_ds8": p["bridged_rows"]}})
    BAND_GAPS2D.write_text(json.dumps({"image_shape": list(gray.shape), "seam_col_ds8": seam,
                                       "blocks": blocks, "candidates": cands, "paths": items}, indent=1))
    save_overlay(gray, lab, paths, QA / f"{BAND}_gaps_overlay.png")
    print(f"extract_gaps: {len(blocks)} blocks, {len(cands)} adjacent pairs, {len(items)} gap paths; "
          f"seam at ds8 col {seam:.0f}")
    for c in cands:
        print("  pair", c["blocks"], c["status"], c.get("run_info", ""))
    print(f"wrote {BAND_GAPS2D} and {QA / f'{BAND}_gaps_overlay.png'}")


if __name__ == "__main__":
    main()
