"""Frame sanity, agreement with human same-winding lines, shifted controls, chain stats."""
import json

import cv2
import numpy as np
from scipy.spatial import cKDTree

from . import COLLECTIONS, DENSE, HUMAN, MESH, QA, VOXEL_DIV
from .extract import load_ink
from .project import load_mesh

SHIFT = 25.0            # voxels, control translation
BBOX_PAD = 20.0         # voxels
NEAR = 50.0             # voxels, "near a human line" for the reverse direction
DENSIFY_MAX_GAP = 50.0  # voxels; human polyline segments longer than this are not bridged
COPIES = (("unshifted", (0, 0, 0)), (f"x +{SHIFT:.0f}", (SHIFT, 0, 0)), (f"y +{SHIFT:.0f}", (0, SHIFT, 0)))


def load_collections(path):
    """[(name, (N, 3) points sorted by integer point id)]; empty collections are skipped."""
    out = []
    for c in json.loads(path.read_text())["collections"].values():
        ids = sorted(c["points"], key=int)
        if not ids:
            continue
        out.append((c["name"], np.array([c["points"][k]["p"] for k in ids], float)))
    return out


def densify(points, step=1.0, max_gap=DENSIFY_MAX_GAP):
    """Resample one polyline at about `step` voxels, without bridging gaps over max_gap."""
    out = [points[:1]]
    for a, b in zip(points[:-1], points[1:]):
        d = np.linalg.norm(b - a)
        if d <= max_gap:
            t = np.linspace(0, 1, max(int(np.ceil(d / step)), 1) + 1)[1:, None]
            out.append(a + t * (b - a))
        else:
            out.append(b[None])
    return np.concatenate(out)


def umbilicus_xy(z):
    cp = sorted(json.loads((HUMAN / "umbilicus.json").read_text())["control_points"], key=lambda c: c["z"])
    zs = np.array([c["z"] for c in cp], float)
    return np.interp(z, zs, [c["x"] for c in cp]), np.interp(z, zs, [c["y"] for c in cp])


def radius(p):
    ux, uy = umbilicus_xy(p[:, 2])
    return np.hypot(p[:, 0] - ux, p[:, 1] - uy)


def pct(a, q=(0, 50, 100)):
    return " / ".join(f"{v:.0f}" for v in np.percentile(a, q))


def dist_stats(d):
    if len(d) == 0:
        return "n=0"
    return f"n={len(d)}, median {np.median(d):.1f}, within 5: {np.mean(d <= 5):.3f}, within 10: {np.mean(d <= 10):.3f}"


def main():
    QA.mkdir(parents=True, exist_ok=True)
    lines = []
    say = lines.append
    ours = load_collections(COLLECTIONS)
    pts = np.concatenate([p for _, p in ours])
    dz = np.load(DENSE)
    dense = dz["dense"]
    human = load_collections(HUMAN / "same_windings.json")
    hpts = np.concatenate([p for _, p in human])
    hcols = [densify(p) for _, p in human]
    htree = cKDTree(np.concatenate(hcols))
    mb = np.array(json.loads((MESH / "meta.json").read_text())["bbox"]) / VOXEL_DIV
    grid = load_mesh()
    gvalid = ~np.any(grid == -1, axis=2)
    mesh_pts = grid[gvalid] / VOXEL_DIV

    say("# layout_constraints report: segment 20230702185753\n")
    say("Units are dataset voxels (9.6 um). 'Our points' are the written JSON points (10 voxel spacing). "
        "'Dense chains' are every valid ds8 path sample before decimation (about 2 voxels apart). "
        "Human lines are densified to 1 voxel steps (gaps over 50 voxels not bridged).\n")

    # a. frame sanity
    say("## a. Frame sanity\n")
    lo, hi = pts.min(0), pts.max(0)
    say(f"- projected bbox min {np.round(lo, 1).tolist()} max {np.round(hi, 1).tolist()}")
    say(f"- mesh meta.json bbox / 4: min {np.round(mb[0], 1).tolist()} max {np.round(mb[1], 1).tolist()}")
    inside = bool(np.all(lo >= mb[0] - 1) and np.all(hi <= mb[1] + 1))
    say(f"- projected points inside mesh bbox / 4: {inside}")
    gray = load_ink()
    img_on = cv2.resize(gray, (grid.shape[1], grid.shape[0]), interpolation=cv2.INTER_AREA) > 20
    iou = (img_on & gvalid).sum() / (img_on | gvalid).sum()
    say(f"- 2D registration: ink image papyrus mask (gray > 20, resized to the {grid.shape[1]} x {grid.shape[0]} "
        f"grid) vs mesh valid vertices: IoU {iou:.3f} (image {img_on.mean():.3f} of the area, mesh {gvalid.mean():.3f})")
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
    frame_ok = inside and r.min() >= 20 and r.max() <= 1.2 * hr.max()
    say(f"- verdict a (inside bbox, min radius >= 20, max radius <= 1.2 x human max): {'PASS' if frame_ok else 'FAIL'}\n")

    # b, c. agreement with humans, and translated controls
    sel = np.all((hpts >= lo - BBOX_PAD) & (hpts <= hi + BBOX_PAD), axis=1)
    hsel = hpts[sel]
    say("## b/c. Agreement with human same_windings lines, and translated controls\n")
    say(f"- human points in the projected bbox expanded by {BBOX_PAD:.0f}: {len(hsel)} of {len(hpts)} "
        f"(from {len(human)} collections)\n")
    say("| copy | human -> our dense chains | our points -> human (all) | our points -> human (only those within 50) |")
    say("|---|---|---|---|")
    o2h = {}
    for label, off in COPIES:
        off = np.array(off)
        a = cKDTree(dense + off).query(hsel)[0]
        b = htree.query(pts + off)[0]
        o2h[label] = b
        say(f"| {label} | {dist_stats(a)} | {dist_stats(b)} | {dist_stats(b[b <= NEAR])} |")
    say("")
    say("Closest approach of each human collection to our dense chains (human lines mostly run along z, "
        "our text lines run around the scroll, so a correct frame shows up as near-zero crossings):\n")
    say("| copy | collections with closest approach <= 5 | <= 10 | <= 25 | median of closest approaches under 50 |")
    say("|---|---|---|---|---|")
    ca = {}
    for label, off in COPIES:
        t = cKDTree(dense + np.array(off))
        m = np.array([t.query(p)[0].min() for p in hcols])
        ca[label] = m
        u = m[m < 50]
        med = f"{np.median(u):.1f} (n={len(u)})" if len(u) else "n=0"
        say(f"| {label} | {(m <= 5).sum()} | {(m <= 10).sum()} | {(m <= 25).sum()} | {med} |")
    say("")
    say("Extra: human points in the bbox vs the segment surface itself (all valid mesh vertices / 4; grid spacing "
        "is 5 voxels, so a point on the surface can be up to about 3.5 voxels from the nearest vertex):\n")
    say("| copy | human -> mesh vertices | human collections (at least 5 points in the bbox) with at least 80% "
        "of those points within 5 of the surface |")
    say("|---|---|---|")
    hid = np.concatenate([np.full(len(p), k) for k, (_, p) in enumerate(human)])[sel]
    for label, off in COPIES:
        d = cKDTree(mesh_pts + np.array(off)).query(hsel)[0]
        ks = [k for k in np.unique(hid) if (hid == k).sum() >= 5]
        on = sum(np.mean(d[hid == k] <= 5) >= 0.8 for k in ks)
        say(f"| {label} | {dist_stats(d)} | {on} of {len(ks)} |")
    say("")
    better = all(np.mean(o2h["unshifted"] <= 10) > np.mean(o2h[k] <= 10) for k in o2h if k != "unshifted") and \
        all((ca["unshifted"] <= 10).sum() > (ca[k] <= 10).sum() for k in ca if k != "unshifted")
    say(f"- verdict c (unshifted beats both shifted copies on 'our points -> human within 10' and on "
        f"'collections with closest approach <= 10'): {'PASS' if better else 'FAIL'}\n")

    # d. chain statistics
    say("## d. Chain statistics\n")
    names = [n for n, _ in ours]
    npts = np.array([len(p) for _, p in ours])
    lens = np.array([np.linalg.norm(np.diff(p, axis=0), axis=1).sum() for _, p in ours])
    steps = np.concatenate([np.linalg.norm(np.diff(p, axis=0), axis=1) for _, p in ours])
    n_margin = sum("_margin_" in n for n in names)
    say(f"- chains: {len(ours)} ({len(ours) - n_margin} text-line, {n_margin} margin), points: {npts.sum()}")
    say(f"- points per chain (min / median / max): {pct(npts)}")
    say(f"- chain length in voxels (min / median / max): {pct(lens)}; total {lens.sum():.0f}")
    say(f"- step between consecutive written points (min / median / max): "
        f"{steps.min():.1f} / {np.median(steps):.1f} / {steps.max():.1f}")
    samples, invalid = int(dz["samples"]), int(dz["invalid"])
    say(f"- ds8 path samples on invalid quads: {invalid} / {samples} = {invalid / samples:.4f} "
        f"(per kind [samples, invalid]: {dz['by_kind']})")
    spans = []
    for _, p in ours:
        ux, uy = umbilicus_xy(p[:, 2])
        spans.append(np.degrees(np.ptp(np.unwrap(np.arctan2(p[:, 1] - uy, p[:, 0] - ux)))))
    hspan = max(np.degrees(np.ptp(np.unwrap(np.arctan2(p[:, 1] - umbilicus_xy(p[:, 2])[1],
                                                         p[:, 0] - umbilicus_xy(p[:, 2])[0])))) for _, p in human)
    spans_a = np.array(spans)
    say(f"- angular span around the umbilicus per chain, degrees (min / median / max): {pct(spans)}; "
        f"chains over 360 deg: {(spans_a > 360).sum()}, over the largest human same_windings span "
        f"({hspan:.0f} deg): {(spans_a > hspan).sum()}. A chain over 360 deg crosses more than one wrap, "
        f"which breaks the same-wrap meaning of a same-winding collection.")
    for n, (_, p), s, ln in zip(names, ours, spans, lens):
        say(f"  - {n}: {len(p)} pts, {ln:.0f} vx, z {p[:, 2].min():.0f}..{p[:, 2].max():.0f}, span {s:.0f} deg")
    text = "\n".join(lines) + "\n"
    (QA / "report.md").write_text(text, encoding="utf-8")
    print(text)
    print(f"wrote {QA / 'report.md'}")


if __name__ == "__main__":
    main()
