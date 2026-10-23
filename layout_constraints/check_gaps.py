"""Checks for the band's intercolumnar gap chains -> data/qa/report_w116.md."""
import json
from collections import Counter

import cv2
import numpy as np
from scipy.spatial import cKDTree

from . import BAND, BAND_DENSE, BAND_GAPS, BAND_GAPS2D, BAND_INK, BAND_MESH, CELL, DS, HUMAN, QA, VOXEL_DIV
from .check import BBOX_PAD, COPIES, NEAR, densify, dist_stats, load_collections, pct, radius, umbilicus_xy
from .extract import load_ink
from .project import load_mesh

ABS_NEAR = 15.0   # voxels: abs_winding points this close to a chain count for its identity
ON_SURFACE = 5.0  # voxels: a human point this close to a mesh vertex is on the band surface


def span_deg(p):
    ux, uy = umbilicus_xy(p[:, 2])
    return float(np.degrees(np.ptp(np.unwrap(np.arctan2(p[:, 1] - uy, p[:, 0] - ux)))))


def load_band():
    """Mesh bbox / 4, valid mask, valid vertices / 4, and the angle swept per mesh row."""
    mb = np.array(json.loads((BAND_MESH / "meta.json").read_text())["bbox"]) / VOXEL_DIV
    grid = load_mesh(BAND_MESH)
    gvalid = ~np.any(grid == -1, axis=2)
    mesh_pts = grid[gvalid] / VOXEL_DIV
    wraps, cols_per_turn = [], []
    for i in range(250, grid.shape[0], 250):
        j = np.flatnonzero(gvalid[i])
        p = grid[i, j] / VOXEL_DIV
        ux, uy = umbilicus_xy(p[:, 2])
        th = np.degrees(np.unwrap(np.arctan2(p[:, 1] - uy, p[:, 0] - ux)))
        wraps.append(np.ptp(th))
        cols_per_turn.append(360 * np.ptp(j) / np.ptp(th))
    del grid
    return {"mb": mb, "gvalid": gvalid, "mesh_pts": mesh_pts, "wraps": wraps, "cols_per_turn": cols_per_turn}


def frame_section(say, pts, band, hpts):
    """Section a for the points pts; returns their bbox (lo, hi)."""
    mb, gvalid, mesh_pts = band["mb"], band["gvalid"], band["mesh_pts"]
    wraps, cols_per_turn = band["wraps"], band["cols_per_turn"]
    say("## a. Frame sanity\n")
    lo, hi = pts.min(0), pts.max(0)
    say(f"- projected bbox min {np.round(lo, 1).tolist()} max {np.round(hi, 1).tolist()}")
    say(f"- mesh meta.json bbox / 4: min {np.round(mb[0], 1).tolist()} max {np.round(mb[1], 1).tolist()}")
    inside = bool(np.all(lo >= mb[0] - 1) and np.all(hi <= mb[1] + 1))
    say(f"- projected points inside mesh bbox / 4: {inside}")
    gray = load_ink(BAND_INK)
    img_on = cv2.resize(gray, (gvalid.shape[1], gvalid.shape[0]), interpolation=cv2.INTER_AREA) > 20
    del gray
    iou = (img_on & gvalid).sum() / (img_on | gvalid).sum()
    say(f"- 2D registration: ink image papyrus mask (gray > 20, resized to the {gvalid.shape[1]} x {gvalid.shape[0]} "
        f"grid) vs mesh valid vertices: IoU {iou:.3f} (image {img_on.mean():.3f} of the area, mesh {gvalid.mean():.3f}); "
        f"image papyrus on invalid mesh: {(img_on & ~gvalid).mean():.4f} of the grid, mesh valid but not rendered "
        f"in the image: {(gvalid & ~img_on).mean():.4f}")
    half = gvalid.shape[0] // 2
    lo_iou = (img_on[half:] & gvalid[half:]).sum() / (img_on[half:] | gvalid[half:]).sum()
    say(f"- the same IoU on the lower half of the grid (rows {half}..{gvalid.shape[0] - 1}): {lo_iou:.3f}")
    zlo, zhi = lo[2], hi[2]
    ux, uy = umbilicus_xy(np.linspace(zlo, zhi, 200))
    say(f"- umbilicus over z {zlo:.0f}..{zhi:.0f}: x {ux.min():.0f}..{ux.max():.0f}, y {uy.min():.0f}..{uy.max():.0f}")
    r = radius(pts)
    hz = hpts[(hpts[:, 2] >= zlo) & (hpts[:, 2] <= zhi)]
    hr = radius(hz)
    say(f"- radius from umbilicus, our points (min / median / max): {pct(r)}")
    say(f"- radius from umbilicus, human same_windings points in the same z range "
        f"(n={len(hz)}, min / median / max): {pct(hr)}")
    say(f"- radius from umbilicus, all valid mesh vertices (min / median / max): {pct(radius(mesh_pts))}")
    say(f"- angle swept around the umbilicus along each mesh row (every 250th row, {len(wraps)} rows; two windings "
        f"= 720): min / median / max {pct(wraps)} deg; grid columns per 360 deg (median) {np.median(cols_per_turn):.0f} "
        f"(= {np.median(cols_per_turn) * CELL / DS:.0f} ds8 px)")
    frame_ok = inside and r.min() >= 20 and r.max() <= 1.2 * hr.max()
    say(f"- verdict a (inside bbox, min radius >= 20, max radius <= 1.2 x human max): {'PASS' if frame_ok else 'FAIL'}\n")
    return lo, hi


def main():
    QA.mkdir(parents=True, exist_ok=True)
    lines = []
    say = lines.append
    ours = load_collections(BAND_GAPS)
    meta = {c["name"]: c["metadata"] for c in json.loads(BAND_GAPS.read_text())["collections"].values()}
    pts = np.concatenate([p for _, p in ours])
    dz = np.load(BAND_DENSE)
    dense, dense_id = dz["dense"], dz["chain_id"]
    gaps2d = json.loads(BAND_GAPS2D.read_text())
    human = load_collections(HUMAN / "same_windings.json")
    hpts = np.concatenate([p for _, p in human])
    hid_all = np.concatenate([np.full(len(p), k) for k, (_, p) in enumerate(human)])
    hcols = [densify(p) for _, p in human]
    htree = cKDTree(np.concatenate(hcols))
    band = load_band()
    mb, gvalid, mesh_pts = band["mb"], band["gvalid"], band["mesh_pts"]

    say(f"# layout_constraints report: band {BAND}, intercolumnar gaps\n")
    say("Units are dataset voxels (9.6 um). 'Our points' are the written JSON points (10 voxel spacing). "
        "'Dense chains' are every valid ds8 path sample before decimation (one per ds8 row, about 1.6 voxels "
        "apart in z). Human lines are densified to 1 voxel steps (gaps over 50 voxels not bridged).\n")

    # gap finder summary
    say("## Gap finder\n")
    say(f"- text blocks: {len(gaps2d['blocks'])}; adjacent block pairs: {len(gaps2d['candidates'])}; "
        f"gap paths kept: {len(gaps2d['paths'])}; seam between panels at ds8 col {gaps2d['seam_col_ds8']:.0f}")
    for b in gaps2d["blocks"]:
        say(f"  - block B{b['id']}: ds8 rows {b['rows'][0]}..{b['rows'][1]}, cols {b['cols'][0]}..{b['cols'][1]}")
    for c in gaps2d["candidates"]:
        runs = "; ".join(f"run rows {r['ds8_rows'][0]}..{r['ds8_rows'][1]}, width {r['width']:.0f}, "
                         f"slope {r['slope']}, contrast {r['contrast']}: {r['status']}" for r in c.get("run_info", []))
        say(f"  - pair B{c['blocks'][0]} | B{c['blocks'][1]}: overlap {c['overlap']}, "
            f"corridor rows {c['corridor_rows']}: {c['status']}" + (f" ({runs})" if runs else ""))
    say("")

    lo, hi = frame_section(say, pts, band, hpts)

    # b. agreement with humans, translated controls
    say("## b. Agreement with human same_windings lines, and translated controls\n")
    sel = np.all((hpts >= lo - BBOX_PAD) & (hpts <= hi + BBOX_PAD), axis=1)
    hsel = hpts[sel]
    say(f"- human points in the projected bbox expanded by {BBOX_PAD:.0f}: {len(hsel)} of {len(hpts)} "
        f"(from {len(human)} collections)\n")
    say("| copy | human -> our dense chains | our points -> human (all) | our points -> human (only those within 50) |")
    say("|---|---|---|---|")
    for label, off in COPIES:
        off = np.array(off)
        a = cKDTree(dense + off).query(hsel)[0] if len(hsel) else np.array([])
        b = htree.query(pts + off)[0]
        say(f"| {label} | {dist_stats(a)} | {dist_stats(b)} | {dist_stats(b[b <= NEAR])} |")
    say("")
    say("Closest approach of each human collection to our dense chains:\n")
    say("| copy | collections with closest approach <= 5 | <= 10 | <= 25 | median of closest approaches under 50 |")
    say("|---|---|---|---|---|")
    for label, off in COPIES:
        t = cKDTree(dense + np.array(off))
        m = np.array([t.query(p)[0].min() for p in hcols])
        u = m[m < 50]
        med = f"{np.median(u):.1f} (n={len(u)})" if len(u) else "n=0"
        say(f"| {label} | {(m <= 5).sum()} | {(m <= 10).sum()} | {(m <= 25).sum()} | {med} |")
    say("")
    mtree = cKDTree(mesh_pts)
    insel = np.all((hpts >= mb[0] - BBOX_PAD) & (hpts <= mb[1] + BBOX_PAD), axis=1)
    hb, hidb = hpts[insel], hid_all[insel]
    ks = [k for k in np.unique(hidb) if (hidb == k).sum() >= 5]
    say(f"Human points vs the band surface (all valid mesh vertices / 4, 5 voxel grid spacing). Uses the human "
        f"points inside the mesh bbox / 4 expanded by {BBOX_PAD:.0f} ({len(hb)} points; {len(ks)} collections with "
        f"at least 5 of them). Shifting the human points by -d is the same test as shifting the mesh by +d:\n")
    say("| copy | human -> mesh vertices | collections with at least 80% of those points within 5 of the surface |")
    say("|---|---|---|")
    on_names = {}
    for label, off in COPIES:
        d = mtree.query(hb - np.array(off))[0]
        on = [k for k in ks if np.mean(d[hidb == k] <= ON_SURFACE) >= 0.8]
        on_names[label] = on
        say(f"| {label} | {dist_stats(d)} | {len(on)} of {len(ks)} |")
    say("")
    if on_names["unshifted"]:
        say("Human collections on the band surface (unshifted): " + ", ".join(
            f"{human[k][0]} ({len(human[k][1])} pts, z {human[k][1][:, 2].min():.0f}..{human[k][1][:, 2].max():.0f})"
            for k in on_names["unshifted"]) + "\n")

    # c. absolute winding identity
    say("## c. Absolute winding identity (abs_winding.json)\n")
    ab = json.loads((HUMAN / "abs_winding.json").read_text())["collections"]
    apts = np.array([q["p"] for c in ab.values() for q in c["points"].values()], float).reshape(-1, 3)
    awind = np.array([q["wind_a"] for c in ab.values() for q in c["points"].values()], float)
    say(f"- abs_winding.json: {len(apts)} points in {len(ab)} collections, wind_a {awind.min():.0f}..{awind.max():.0f}, "
        f"z {apts[:, 2].min():.0f}..{apts[:, 2].max():.0f}, radius from umbilicus (min / median / max) {pct(radius(apts))}")
    dm = mtree.query(apts)[0]
    say(f"- distance from each abs_winding point to the band surface (min / median / max): {pct(dm)}; "
        f"points within {ABS_NEAR:.0f} of the surface: {(dm <= ABS_NEAR).sum()}"
        + (f" (wind_a {sorted(Counter(awind[dm <= ABS_NEAR].astype(int)).items())})" if (dm <= ABS_NEAR).any() else ""))
    atree = cKDTree(apts)
    any_near = False
    for k, (name, _) in enumerate(ours):
        dch = dense[dense_id == k]
        d, _ = atree.query(dch)
        near = sorted(set(j for js in atree.query_ball_point(dch, ABS_NEAR) for j in js))
        if not near:
            say(f"- {name} ({meta[name]['panel']} panel): no abs_winding point within {ABS_NEAR:.0f}; "
                f"nearest is {d.min():.0f} voxels away (wind_a {awind[atree.query(dch[np.argmin(d)])[1]]:.0f})")
            continue
        any_near = True
        cnt = Counter(awind[near].astype(int))
        dom, n_dom = cnt.most_common(1)[0]
        split = " SUSPECT: split between values" if len(cnt) > 1 else ""
        say(f"- {name} ({meta[name]['panel']} panel): {len(near)} points, wind_a {dict(cnt)}, dominant {dom}, "
            f"agreeing {n_dom / len(near):.2f}{split}")
    say(f"- verdict c: {'identity measured (see lines above)' if any_near else 'NOT MEASURABLE: no abs_winding point lies within %.0f voxels of any gap chain' % ABS_NEAR}\n")

    # d. chain statistics
    say("## d. Chain statistics\n")
    npts = np.array([len(p) for _, p in ours])
    lens = np.array([np.linalg.norm(np.diff(p, axis=0), axis=1).sum() for _, p in ours])
    steps = np.concatenate([np.linalg.norm(np.diff(p, axis=0), axis=1) for _, p in ours])
    spans = np.array([span_deg(p) for _, p in ours])
    say(f"- chains: {len(ours)}, points: {npts.sum()}")
    say(f"- points per chain (min / median / max): {pct(npts)}")
    say(f"- chain length in voxels (min / median / max): {pct(lens)}; total {lens.sum():.0f}")
    say(f"- step between consecutive written points (min / median / max): "
        f"{steps.min():.1f} / {np.median(steps):.1f} / {steps.max():.1f}")
    samples, invalid = int(dz["samples"]), int(dz["invalid"])
    say(f"- ds8 path samples on invalid quads: {invalid} / {samples} = {invalid / samples:.4f}")
    say(f"- angular span around the umbilicus per chain, degrees (min / median / max): "
        f"{spans.min():.1f} / {np.median(spans):.1f} / {spans.max():.1f}")
    for (n, p), s, ln in zip(ours, spans, lens):
        m = meta[n]
        say(f"  - {n}: {m['panel']} panel, blocks B{m['blocks'][0]} | B{m['blocks'][1]}, ds8 rows "
            f"{m['ds8_rows'][0]:.0f}..{m['ds8_rows'][1]:.0f}, cols {m['ds8_cols'][0]:.0f}..{m['ds8_cols'][1]:.0f}, "
            f"corridor width {m['corridor_width_ds8']:.0f} ds8 px, {len(p)} pts, {ln:.0f} vx, "
            f"z {p[:, 2].min():.0f}..{p[:, 2].max():.0f}, radius {pct(radius(p))}, span {s:.1f} deg")
    text = "\n".join(lines) + "\n"
    (QA / "report_w116.md").write_text(text, encoding="utf-8")
    print(text)
    print(f"wrote {QA / 'report_w116.md'}")


if __name__ == "__main__":
    main()
