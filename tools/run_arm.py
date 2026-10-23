"""Run one spiral fit arm on CPU, log everything, record wall time and peak RSS.

Usage: python tools/run_arm.py --arm A --dataset DIR --steps 300 --seed 1 --out RUNS_DIR [--tag smoke]
Runs <villa>/spiral-fitting/fit_spiral.py with the spiral venv python directly (no uv run, which
would re-sync torch to the CUDA lock; see tasks/LOCAL_CPU_SETUP.md).
"""
import argparse
import json
import os
import subprocess
import sys
import threading
import time

import psutil

SPIRAL = os.environ.get("SPIRAL_FITTING_DIR", r"C:\Users\stans\Projects\villa\spiral-fitting")
PY = os.environ.get("SPIRAL_FITTING_PYTHON", os.path.join(SPIRAL, ".venv", "Scripts", "python.exe"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--steps", type=int, required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default="run")
    ap.add_argument("--z", default="10500,11500")
    ap.add_argument("--extra", default="{}", help="extra JSON config overrides")
    a = ap.parse_args()
    z0, z1 = (int(v) for v in a.z.split(","))
    overrides = {"z_begin": z0, "z_end": z1, "optimizer_num_training_steps": a.steps,
                 "optimizer_random_seed": a.seed, "input_use_normals": False,
                 "input_use_fibers": False}
    overrides.update(json.loads(a.extra))
    run_name = f"{a.tag}_arm{a.arm}_s{a.seed}_n{a.steps}"
    run_dir = os.path.join(os.path.abspath(a.out), run_name)
    os.makedirs(run_dir, exist_ok=True)
    env = dict(os.environ)
    env.update({
        "FIT_SPIRAL_DEVICE": "cpu",
        "FIT_SPIRAL_CONFIG_OVERRIDES": json.dumps(overrides),
        "FIT_SPIRAL_RUN_DIR": run_dir,
        "FIT_SPIRAL_RUN_TAG": run_name,
        "FIT_SPIRAL_CACHE_DIR": os.path.join(os.path.abspath(a.out), "_cache"),
        "WANDB_MODE": "disabled",
        "PYTHONUNBUFFERED": "1",
    })
    log_path = os.path.join(run_dir, "fit.log")
    cmd = [PY, "fit_spiral.py", "--dataset", os.path.abspath(a.dataset)]
    print("run_dir:", run_dir)
    print("overrides:", json.dumps(overrides))
    t0 = time.time()
    peak = {"rss": 0}
    with open(log_path, "wb") as log:
        proc = subprocess.Popen(cmd, cwd=SPIRAL, env=env, stdout=log, stderr=subprocess.STDOUT)
        ps = psutil.Process(proc.pid)

        def watch():
            while proc.poll() is None:
                try:
                    rss = ps.memory_info().rss
                    for c in ps.children(recursive=True):
                        try:
                            rss += c.memory_info().rss
                        except psutil.Error:
                            pass
                    peak["rss"] = max(peak["rss"], rss)
                except psutil.Error:
                    pass
                time.sleep(2)

        th = threading.Thread(target=watch, daemon=True)
        th.start()
        rc = proc.wait()
    wall = time.time() - t0
    summary = {"arm": a.arm, "dataset": os.path.abspath(a.dataset), "steps": a.steps, "seed": a.seed,
               "overrides": overrides, "run_dir": run_dir, "returncode": rc, "wall_s": round(wall, 1),
               "peak_rss_gib": round(peak["rss"] / 2**30, 2), "cmd": cmd}
    with open(os.path.join(run_dir, "run_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary, indent=1))
    sys.exit(rc)


if __name__ == "__main__":
    main()
