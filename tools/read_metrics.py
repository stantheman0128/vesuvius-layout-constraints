"""Read satisfaction_metrics_<suffix>.json and satisfied_<suffix>.json from one or more run dirs
and print the pre-registered metrics side by side (tasks/PROTOCOL.md).

Usage: python tools/read_metrics.py RUN_DIR [RUN_DIR ...] [--suffix fitted] [--ours-from 175]
Entries whose name looks like "<segment>_lineNN" or "<segment>_gapNN" are counted as "ours"; the id field in
satisfied_<suffix>.json is the fitter's strip index, not the collection id. Only unattached strips are listed there.
"""
import argparse
import glob
import json
import os
import re

OURS_PREFIX = re.compile(r"^\d{14}(-w\d{3}-\d{3})?_(line\d+|gap\d+|margin_left|margin_right)$")

SUMMARY_KEYS = [
    "satisfied_patches_fraction", "boundary_satisfied_patches_fraction",
    "satisfied_patches_area_weighted_fraction", "satisfied_area_fraction",
    "satisfied_unattached_pcls_fraction", "satisfied_unattached_pcl_points_fraction",
    "total_patches", "total_unattached_pcls", "total_unattached_pcl_points",
]


def find(run_dir, name):
    hits = glob.glob(os.path.join(run_dir, "**", name), recursive=True)
    return hits[0] if hits else None


def load(run_dir, suffix):
    m = find(run_dir, f"satisfaction_metrics_{suffix}.json")
    s = find(run_dir, f"satisfied_{suffix}.json")
    summary = json.load(open(m))["summary"] if m else {}
    detail = json.load(open(s)) if s else {"patches": [], "pcls": []}
    return summary, detail


def pcl_groups(detail, ours_from):
    groups = {}
    for e in detail.get("pcls", []):
        src = os.path.basename(str(e.get("source_file") or "?"))
        # The "id" here is the fitter's strip index, not the collection id, so classify by name:
        # our collections are named "<segment>_lineNN" or "<segment>_gapNN"; human ones "same_wrapNN", "colNN".
        name = str(e.get("name") or "")
        who = "ours" if OURS_PREFIX.match(name) else "human"
        key = f"{src}:{who}"
        g = groups.setdefault(key, [0, 0, 0, 0])
        g[0] += int(e.get("satisfied_points", 0)); g[1] += int(e.get("total_points", 0))
        g[2] += 1 if e.get("fraction", 0) >= 0.999 else 0; g[3] += 1
    return groups


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--suffix", default="fitted")
    ap.add_argument("--ours-from", type=int, default=175)
    a = ap.parse_args()
    rows = []
    for r in a.runs:
        summary, detail = load(r, a.suffix)
        rs = json.load(open(os.path.join(r, "run_summary.json"))) if os.path.exists(os.path.join(r, "run_summary.json")) else {}
        rows.append((os.path.basename(r.rstrip("/\\")), summary, pcl_groups(detail, a.ours_from), rs))
    print("| metric | " + " | ".join(n for n, *_ in rows) + " |")
    print("|---|" + "---|" * len(rows))
    for k in SUMMARY_KEYS:
        vals = []
        for _, s, _, _ in rows:
            v = s.get(k)
            vals.append(f"{v*100:.2f}%" if isinstance(v, float) and v <= 1.0 else str(v))
        print(f"| {k} | " + " | ".join(vals) + " |")
    for k in ("wall_s", "peak_rss_gib", "returncode", "steps"):
        print(f"| {k} | " + " | ".join(str(rs.get(k)) for *_, rs in rows) + " |")
    keys = sorted({g for _, _, gr, _ in rows for g in gr})
    for g in keys:
        vals = []
        for _, _, gr, _ in rows:
            v = gr.get(g)
            vals.append("n/a" if v is None else f"{(v[0]/max(v[1],1))*100:.2f}% pts ({v[0]}/{v[1]}), {v[2]}/{v[3]} fully")
        print(f"| pcl {g} | " + " | ".join(vals) + " |")


if __name__ == "__main__":
    main()
