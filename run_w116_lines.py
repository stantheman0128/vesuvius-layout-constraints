"""Slice 2b: text lines on band 20260701183145-w116-117 (extract, project, check)."""
import time

import psutil

from layout_constraints import band_lines

if __name__ == "__main__":
    t = time.time()
    band_lines.main()
    peak = getattr(psutil.Process().memory_info(), "peak_wset", None)
    print(f"wall time {time.time() - t:.0f} s" + (f", peak working set {peak / 2**30:.2f} GiB" if peak else ""))
