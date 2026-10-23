"""ds8 image paths -> 3D dataset-frame points via the tifxyz mesh, and the JSON writer."""
import json
import time

import numpy as np
import tifffile

from . import (BAND, BAND_DENSE, BAND_GAPS, BAND_GAPS2D, BAND_MESH, BAND_MESH_NAME, CELL, COLLECTIONS,
               DENSE, DS, MESH, MIN_SPACING, PATHS2D, SEG, VOXEL_DIV)

COLORS = {"text_line": [0.9, 0.2, 0.2], "margin": [0.2, 0.8, 0.9], "intercolumnar_gap": [0.3, 0.9, 0.3]}


def load_mesh(path=MESH):
    """(H, W, 3) float32 grid of 2.4 um volume coordinates; -1 marks invalid vertices."""
    return np.stack([tifffile.imread(path / f"{a}.tif") for a in "xyz"], -1)


def ds8_to_grid(rows, cols):
    """ds8 pixel -> full-res pixel (x8) -> mesh grid cell (/20)."""
    return np.asarray(rows, float) * DS / CELL, np.asarray(cols, float) * DS / CELL


def bilinear(grid, i, j):
    """Interpolate grid at fractional (i, j). Returns (points (N, 3), valid (N,)).

    A sample is invalid if it falls outside the grid or any vertex of its quad is -1.
    """
    i, j = np.atleast_1d(np.asarray(i, float)), np.atleast_1d(np.asarray(j, float))
    h, w = grid.shape[:2]
    inside = (i >= 0) & (i <= h - 1) & (j >= 0) & (j <= w - 1)
    i0 = np.clip(np.floor(i).astype(int), 0, h - 2)
    j0 = np.clip(np.floor(j).astype(int), 0, w - 2)
    fi, fj = (i - i0)[:, None], (j - j0)[:, None]
    c00, c01 = grid[i0, j0], grid[i0, j0 + 1]
    c10, c11 = grid[i0 + 1, j0], grid[i0 + 1, j0 + 1]
    valid = inside & ~np.any(np.stack([c00, c01, c10, c11]) == -1, axis=(0, 2))
    pts = (1 - fi) * ((1 - fj) * c00 + fj * c01) + fi * ((1 - fj) * c10 + fj * c11)
    return pts, valid


def valid_runs(valid):
    """(start, stop) index pairs of the maximal runs of True."""
    edges = np.diff(np.concatenate([[0], valid.astype(np.int8), [0]]))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)))


def decimate(pts, min_spacing=MIN_SPACING):
    """Greedy: keep the first point, then each point at least min_spacing from the last kept."""
    keep, last = [0], pts[0]
    for k in range(1, len(pts)):
        if np.linalg.norm(pts[k] - last) >= min_spacing:
            keep.append(k)
            last = pts[k]
    return pts[keep]


def to_collections(chains, creation_time=None):
    """chains: list of dicts with name, kind, points (N, 3), metadata. Point ids are global
    and increase along each chain, so the fitter's sort-by-id keeps path order."""
    t = int(time.time() * 1000) if creation_time is None else creation_time
    cols, pid = {}, 0
    for cid, ch in enumerate(chains):
        pts = {}
        for p in ch["points"]:
            pts[str(pid)] = {"p": [float(v) for v in p], "wind_a": None, "creation_time": t}
            pid += 1
        cols[str(cid)] = {"name": ch["name"], "color": COLORS.get(ch["kind"], [1.0, 1.0, 1.0]),
                          "metadata": {"winding_is_absolute": False, **ch["metadata"]}, "points": pts}
    return {"vc_pointcollections_json_version": "1", "collections": cols}


def project_paths(paths, grid, segment=SEG, mesh_name="20230702185753-on-20260411134726-2.4um.tifxyz"):
    """Map 2D paths to 3D, split at invalid quads, decimate, drop chains under 2 points.

    A path may carry a "meta" dict; it is added to the chain metadata."""
    chains, dense, stats = [], [], {"samples": 0, "invalid": 0, "by_kind": {}}
    for path in paths:
        i, j = ds8_to_grid(path["rows"], path["cols"])
        pts, valid = bilinear(grid, i, j)
        pts = pts / VOXEL_DIV
        k = stats["by_kind"].setdefault(path["kind"], [0, 0])
        k[0] += len(valid)
        k[1] += int((~valid).sum())
        stats["samples"] += len(valid)
        stats["invalid"] += int((~valid).sum())
        runs = valid_runs(valid)
        for n, (a, b) in enumerate(runs):
            kept = decimate(pts[a:b])
            if len(kept) < 2:
                continue
            dense.append(pts[a:b])
            chains.append({
                "name": path["name"] + (f"_run{n}" if len(runs) > 1 else ""), "kind": path["kind"],
                "points": kept,
                "metadata": {"source": "layout_constraints", "segment": segment, "kind": path["kind"],
                             "evidence": "ink-derived 2D page layout on the flattened segment",
                             "ds8_rows": [round(float(path["rows"][a]), 1), round(float(path["rows"][b - 1]), 1)],
                             "ds8_cols": [round(float(path["cols"][a]), 1), round(float(path["cols"][b - 1]), 1)],
                             "mesh": mesh_name,
                             "frame": "dataset 9.6 um voxels = mesh xyz / 4",
                             "min_spacing_vx": MIN_SPACING, **path.get("meta", {})}})
    return chains, dense, stats


def run(paths2d, mesh_dir, collections, dense_path, **kw):
    paths = json.loads(paths2d.read_text())["paths"]
    chains, dense, stats = project_paths(paths, load_mesh(mesh_dir), **kw)
    collections.write_text(json.dumps(to_collections(chains)))
    np.savez(dense_path, dense=np.concatenate(dense), chain_id=np.concatenate(
        [np.full(len(d), k) for k, d in enumerate(dense)]),
        samples=stats["samples"], invalid=stats["invalid"],
        by_kind=json.dumps(stats["by_kind"]))
    n = sum(len(c["points"]) for c in chains)
    print(f"project: {len(paths)} 2D paths -> {len(chains)} chains, {n} points; "
          f"{stats['invalid']}/{stats['samples']} path samples on invalid quads")
    print(f"wrote {collections}")


def main():
    run(PATHS2D, MESH, COLLECTIONS, DENSE)


def main_band():
    run(BAND_GAPS2D, BAND_MESH, BAND_GAPS, BAND_DENSE, segment=BAND, mesh_name=BAND_MESH_NAME)


if __name__ == "__main__":
    main()
