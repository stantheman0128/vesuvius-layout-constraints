"""Merge generated point collections into a copy of the fitter's same_windings.json.

The fitter reads constraints only from four fixed file names in the dataset root
(spiral-fitting/fit_session.py:418-423) and keys collections by the JSON dict key
(point_collection.py:145-171), so generated collections must get ids above the
human ones. Point ids are per collection and are left alone.

Usage: python merge_pcl.py HUMAN.json OUT.json GENERATED.json [GENERATED2.json ...]
"""
import json
import sys


def merge(human_path, generated_paths):
    with open(human_path, "rb") as f:
        doc = json.load(f)
    if doc.get("vc_pointcollections_json_version") != "1":
        raise SystemExit(f"unsupported version in {human_path}")
    cols = doc["collections"]
    next_id = max((int(k) for k in cols), default=-1) + 1
    added = []
    for path in generated_paths:
        with open(path, "rb") as f:
            gen = json.load(f)
        if gen.get("vc_pointcollections_json_version") != "1":
            raise SystemExit(f"unsupported version in {path}")
        for old_key in sorted(gen["collections"], key=int):
            col = gen["collections"][old_key]
            if any(p.get("wind_a") is not None for p in col["points"].values()):
                raise SystemExit(f"{path} collection {old_key} has wind_a set; not a same-winding collection")
            col = dict(col)
            col["metadata"] = dict(col.get("metadata", {}))
            col["metadata"]["merged_from"] = {"file": path, "collection_id": int(old_key)}
            cols[str(next_id)] = col
            added.append((path, int(old_key), next_id, len(col["points"])))
            next_id += 1
    return doc, added


def main(argv):
    if len(argv) < 4:
        raise SystemExit(__doc__)
    human, out, *gens = argv[1:]
    doc, added = merge(human, gens)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f)
    n_human = len(doc["collections"]) - len(added)
    print(f"human collections: {n_human}; added: {len(added)}; total: {len(doc['collections'])}")
    for path, old, new, npts in added:
        print(f"  {path} #{old} -> #{new} ({npts} points)")


if __name__ == "__main__":
    main(sys.argv)
