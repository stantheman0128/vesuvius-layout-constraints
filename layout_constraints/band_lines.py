"""Slice 2b: text-line centre paths on the band with the slice 1 extractor (retuned), split at the seam
between the two panels (windings), projected with the slice 1 recipe, and checked."""
import json

import cv2
import numpy as np
import tifffile
from scipy.spatial import cKDTree

from . import (BAND, BAND_INK, BAND_LINES, BAND_LINES2D, BAND_LINES_DENSE, BAND_MESH, BAND_MESH_NAME, HUMAN, OUT,
               QA)
from . import extract, project
from .check import load_collections, pct
from .check_gaps import frame_section, load_band, span_deg
from .extract_gaps import seam_col

# Slice 1 values except: 150 cols along the line (joins words; intercolumnar gaps of 500 px or more stay
# open) and min width 500. Line pitch is 333 to 364 ds8 rows here, about as on 20230702185753.
LINE_KW = {"sigma": (15, 150), "min_width": 500}
SEAM_TOUCH = 50   # ds8 px: a path ending this close to the seam column touches it


def split_at_seam(rows, cols, seam, min_width=LINE_KW["min_width"]):
    """Cut a left-to-right path where it crosses col = seam; drop pieces narrower than min_width."""
    rows, cols = np.asarray(rows, float), np.asarray(cols, float)
    right = cols >= seam
    cut = np.flatnonzero(right[1:] != right[:-1]) + 1
    return [(rows[i], cols[i]) for i in np.split(np.arange(len(cols)), cut)
            if cols[i][-1] - cols[i][0] + 1 >= min_width]


def seam_relation(cols, seam, tol=SEAM_TOUCH):
    """"cross" if the path spans the seam column, "touch" if it ends within tol of it, else None."""
    lo, hi = np.min(cols), np.max(cols)
    if lo < seam <= hi:
        return "cross"
    return "touch" if min(abs(lo - seam), abs(hi - seam)) <= tol else None


def extract_main():
    gray = extract.load_ink(BAND_INK)
    grid_valid = np.all(np.stack([tifffile.imread(BAND_MESH / f"{a}.tif") != -1 for a in "xyz"]), 0)
    seam = seam_col(gray, grid_valid)
    paths, _, dropped = extract.line_paths(gray, **LINE_KW)
    rel = [seam_relation(c, seam) for _, c in paths]
    items = []
    for k, (r, c) in enumerate(paths):
        pieces = split_at_seam(r, c, seam) if rel[k] == "cross" else [(r, c)]
        for n, (pr, pc) in enumerate(pieces):
            items.append({"name": f"{BAND}_line{k:02d}" + (f"_seam{n}" if rel[k] == "cross" else ""),
                          "kind": "text_line", "rows": pr.tolist(), "cols": pc.tolist(),
                          "meta": {"panel": "left" if np.median(pc) < seam else "right"}})
    seam_info = {"seam_col_ds8": seam, "touch_tolerance_ds8": SEAM_TOUCH, "paths_before": len(paths),
                 "crossing_before": rel.count("cross"), "touching_before": rel.count("touch"),
                 "split": rel.count("cross"),
                 "crossing_after": sum(seam_relation(i["cols"], seam) == "cross" for i in items)}
    params = {k: list(v) if isinstance(v, tuple) else v for k, v in LINE_KW.items()}
    BAND_LINES2D.write_text(json.dumps({"image_shape": list(gray.shape), "params": params,
                                        "wide_blobs": len(paths) + dropped, "dropped_merged_blobs": dropped,
                                        "seam": seam_info, "paths": items}))
    img = cv2.cvtColor(cv2.resize(gray, (gray.shape[1] // 4, gray.shape[0] // 4), interpolation=cv2.INTER_AREA),
                       cv2.COLOR_GRAY2BGR)
    cv2.line(img, (int(seam / 4), 0), (int(seam / 4), img.shape[0]), (255, 255, 0), 3)
    for n, it in enumerate(items):
        pts = (np.stack([it["cols"], it["rows"]], 1) / 4).round().astype(np.int32)
        cv2.polylines(img, [pts], False, (0, 0, 255), 4)
        cv2.putText(img, str(n), (int(pts[0, 0]), int(pts[0, 1]) - 8), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
    cv2.imwrite(str(QA / f"{BAND}_lines_overlay.png"), img)
    print(f"band_lines: {len(paths)} text-line paths ({dropped} merged blobs dropped), seam {seam_info}")


def check_main():
    lines = []
    say = lines.append
    ours = load_collections(BAND_LINES)
    meta = {c["name"]: c["metadata"] for c in json.loads(BAND_LINES.read_text())["collections"].values()}
    pts = np.concatenate([p for _, p in ours])
    l2d = json.loads(BAND_LINES2D.read_text())
    dz = np.load(BAND_LINES_DENSE)
    human = load_collections(HUMAN / "same_windings.json")
    hpts = np.concatenate([p for _, p in human])
    band = load_band()
    s = l2d["seam"]
    seam = s["seam_col_ds8"]

    say(f"# layout_constraints report: band {BAND}, text lines (slice 2b)\n")
    say(f"Slice 1 text-line extractor on the band with {l2d['params']} (other parameters as slice 1). Units are "
        f"dataset voxels (9.6 um).\n")
    say("## Extraction and seam self-check\n")
    say(f"- blobs at least {l2d['params']['min_width']} ds8 px wide: {l2d['wide_blobs']}; dropped as merged lines "
        f"(height over 1.8 x median): {l2d['dropped_merged_blobs']}; text-line paths: {s['paths_before']}")
    say(f"- seam at ds8 col {seam:.0f}: 2D paths crossing it before any filtering: {s['crossing_before']}; touching it "
        f"(ending within {s['touch_tolerance_ds8']} px): {s['touching_before']}; split at the seam: {s['split']}; "
        f"2D paths crossing it after the split: {s['crossing_after']}")
    out_cross = sum(m["ds8_cols"][0] < seam <= m["ds8_cols"][1] for m in meta.values())
    say(f"- written chains whose ds8 col range spans the seam: {out_cross} of {len(ours)}\n")

    frame_section(say, pts, band, hpts)

    say("## b. Human same_windings\n")
    d = cKDTree(pts).query(hpts)[0]
    say(f"- empty again: human points within 50 voxels of our points: {(d <= 50).sum()} of {len(hpts)} "
        f"(closest {d.min():.0f}); no human collection lies on this band (report_w116.md: 0 of 125).\n")

    say("## c. abs_winding.json\n")
    ab = json.loads((HUMAN / "abs_winding.json").read_text())["collections"]
    apts = np.array([q["p"] for c in ab.values() for q in c["points"].values()], float).reshape(-1, 3)
    da = cKDTree(apts).query(pts)[0]
    say(f"- far again: nearest abs_winding point to any of our points is {da.min():.0f} voxels away "
        f"(within 15: {(da <= 15).sum()}).\n")

    say("## d. Chain statistics\n")
    npts = np.array([len(p) for _, p in ours])
    lens = np.array([np.linalg.norm(np.diff(p, axis=0), axis=1).sum() for _, p in ours])
    steps = np.concatenate([np.linalg.norm(np.diff(p, axis=0), axis=1) for _, p in ours])
    spans = np.array([span_deg(p) for _, p in ours])
    panels = [meta[n]["panel"] for n, _ in ours]
    say(f"- chains: {len(ours)} (left panel {panels.count('left')}, right panel {panels.count('right')}), "
        f"points: {npts.sum()}")
    say(f"- points per chain (min / median / max): {pct(npts)}")
    say(f"- chain length in voxels (min / median / max): {pct(lens)}; total {lens.sum():.0f}")
    say(f"- step between consecutive written points (min / median / max): "
        f"{steps.min():.1f} / {np.median(steps):.1f} / {steps.max():.1f}")
    samples, invalid = int(dz["samples"]), int(dz["invalid"])
    say(f"- ds8 path samples on invalid quads: {invalid} / {samples} = {invalid / samples:.4f}")
    say(f"- angular span around the umbilicus per chain, degrees (min / median / max): "
        f"{spans.min():.1f} / {np.median(spans):.1f} / {spans.max():.1f}; chains over 360 deg: {(spans > 360).sum()}; "
        f"over 180 deg: {(spans > 180).sum()}")
    widths = np.array([meta[n]["ds8_cols"][1] - meta[n]["ds8_cols"][0] for n, _ in ours])
    say(f"- ds8 column width per chain (min / median / max): {pct(widths)} (one turn is about 8130 ds8 px)")
    for (n, p), sp, ln in zip(ours, spans, lens):
        m = meta[n]
        say(f"  - {n}: {m['panel']}, ds8 rows {m['ds8_rows'][0]:.0f}..{m['ds8_rows'][1]:.0f}, cols "
            f"{m['ds8_cols'][0]:.0f}..{m['ds8_cols'][1]:.0f}, {len(p)} pts, {ln:.0f} vx, "
            f"z {p[:, 2].min():.0f}..{p[:, 2].max():.0f}, span {sp:.1f} deg")
    text = "\n".join(lines) + "\n"
    (QA / "report_w116_lines.md").write_text(text, encoding="utf-8")
    print(text)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    extract_main()
    project.run(BAND_LINES2D, BAND_MESH, BAND_LINES, BAND_LINES_DENSE, segment=BAND, mesh_name=BAND_MESH_NAME)
    check_main()


if __name__ == "__main__":
    main()
