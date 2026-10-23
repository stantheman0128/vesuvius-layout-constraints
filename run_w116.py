"""Slice 2: intercolumnar gaps on band 20260701183145-w116-117 (extract, project, check)."""
import time

import psutil

from layout_constraints import check_gaps, extract_gaps, project

if __name__ == "__main__":
    t = time.time()
    extract_gaps.main()
    project.main_band()
    check_gaps.main()
    mem = psutil.Process().memory_info()
    peak = getattr(mem, "peak_wset", None)
    print(f"wall time {time.time() - t:.0f} s" + (f", peak working set {peak / 2**30:.2f} GiB" if peak else ""))
