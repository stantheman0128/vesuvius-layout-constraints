"""Build the arm B dataset dir: our collections merged into same_windings.json, everything else
pointed at arm A through spiral-scroll.json path overrides (fit_session.py:577-578 allows every
non-pcl input to be overridden; pcl files must sit in the dataset root, fit_session.py:849-852).

Usage: python tools/make_arm_b.py ARM_A_DIR ARM_B_DIR GENERATED.json [GENERATED2.json ...]
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from merge_pcl import merge  # noqa: E402

OVERRIDE_KEYS = ("umbilicus", "verified_patches", "outer_shell", "winding_inference")
CONVENTIONAL = {"umbilicus": "umbilicus.json", "verified_patches": "verified_patches",
                "outer_shell": "outer_shell", "winding_inference": "winding_inference"}


def main(argv):
    arm_a, arm_b, *gens = argv[1:]
    os.makedirs(arm_b, exist_ok=True)
    for name in ("abs_winding.json", "relative_windings.json"):
        shutil.copyfile(os.path.join(arm_a, name), os.path.join(arm_b, name))
    doc, added = merge(os.path.join(arm_a, "same_windings.json"), gens)
    with open(os.path.join(arm_b, "same_windings.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f)
    with open(os.path.join(arm_a, "spiral-scroll.json"), "rb") as f:
        spec = json.load(f)
    spec["paths"] = {k: os.path.join(os.path.abspath(arm_a), CONVENTIONAL[k]).replace("\\", "/")
                     for k in OVERRIDE_KEYS}
    with open(os.path.join(arm_b, "spiral-scroll.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=1)
    n_human = len(doc["collections"]) - len(added)
    print(f"arm B at {arm_b}: same_windings human {n_human} + added {len(added)} = {len(doc['collections'])}")
    print("paths:", json.dumps(spec["paths"], indent=1))


if __name__ == "__main__":
    main(sys.argv)
