# Local CPU setup for spiral-fitting (Windows, 2026-10-22)

Untracked note. Listed in `.git/info/exclude`, not in `.gitignore`.

## Checkout

- Branch `spiral-run`, created with `git checkout -B spiral-run origin/main`
- Commit `86214265244c9328bbcaa4ebc8891c0055656eff` ("spiral-fitting: faster track satisfaction scoring (#2218)")
- Sparse checkout: `git sparse-checkout add vc_object_store` (track_crossings compiles `vc_object_store/src/TrackCrossings.cpp`)

## Why not `uv sync`

`[tool.uv.sources]` pins torch to the cu128 index on win32, and `uv.lock` records
`torch==2.11.0+cu128`. The `cpu` extra only adds kimimaro, which Windows gets anyway.
So `uv sync` and a plain `uv run` would install the CUDA build. This env follows the
README's ROCm recipe instead, with the CPU index, and pins every other package to
the versions in `uv.lock`.

**Always use `uv run --no-sync ...` or `.venv/Scripts/python.exe`.** A plain `uv run`
or `uv sync` replaces the CPU torch with the cu128 one.

## Exact commands (Git Bash, from `spiral-fitting/`)

```sh
# 1. venv on the installed CPython 3.14.2, no Python download
uv venv --python 3.14 --no-python-downloads .venv

# 2. CPU torch 2.11.0, the same base version as uv.lock
uv pip install --python .venv/Scripts/python.exe \
  --index-url https://download.pytorch.org/whl/cpu "torch==2.11.0+cpu"

# 3. cmake into the venv (gave cmake 4.4.4)
uv pip install --python .venv/Scripts/python.exe cmake

# 4. lock pins as constraints, torch swapped for the CPU build
#    (a copy of the result is at .venv/cpu-constraints.txt)
uv export --frozen --no-hashes --no-emit-project --no-group cuda --group dev \
  --no-annotate --no-header --format requirements.txt -o lock-export.txt
grep -v -E '^torch==' lock-export.txt > cpu-constraints.txt
echo 'torch==2.11.0+cpu' >> cpu-constraints.txt

# 5. editable install, builds the four nanobind modules with MSVC
export PATH="$PWD/.venv/Scripts:$PATH"      # so scikit-build-core finds the venv cmake
export CMAKE_GENERATOR="Visual Studio 17 2022"
uv pip install --python .venv/Scripts/python.exe --no-sources \
  -c cpu-constraints.txt -e . --group dev
```

`--no-sources` keeps step 5 from pulling torch from the cu128 index. No vcvars64.bat
was needed: the Visual Studio generator finds BuildTools 2022 (MSVC 14.44.35207)
by itself. Build backend: scikit-build-core 1.1.1, nanobind 3.1.0.

After a change to anything under `cpp/` or `vc_object_store/`, rerun step 5. The
editable install does not rebuild on import.

## Result

- Python 3.14.2, torch `2.11.0+cpu`, `torch.cuda.is_available()` is False
- Compiled, all as `.cp314-win_amd64.pyd` in `.venv/Lib/site-packages/vc_spiral/`:
  `vc_spiral.spiral_sampling`, `vc_spiral.track_crossings`,
  `vc_spiral.track_store`, `vc_spiral.surface_index`
- The repo loaders (`spiral_sampling.load_spiral_sampling`,
  `tracks._load_native_track_crossings`, `tracks._load_native_track_store`,
  `point_collection._load_surface_index_backend`) return the compiled modules, not None
- `fit_spiral.py --help` prints usage
- Quick tests: 101 passed, 6 skipped (MPS only)
- venv size: 1.6 GB (uv hardlinks files from its cache, so much of it is shared)

## Serial and optional parts

- The C++ kernels are serial on MSVC by design (`cpp/CMakeLists.txt` skips OpenMP
  for MSVC). dumpbin shows no OpenMP runtime linked into any `.pyd`. Torch itself
  still uses its own OpenMP threads.
- Triton kernels are CUDA only. `triton-windows` is installed because pyproject
  requires it on win32, but CPU fits use the PyTorch paths.
- Set `FIT_SPIRAL_DEVICE=cpu` to make the device explicit (README "Running without CUDA").
- Expected warnings: torch says `torch.jit.script` is unsupported on Python 3.14+;
  pyro prints a SyntaxWarning for an escape sequence. Neither failed a test.

## Activate

```sh
# Git Bash
source .venv/Scripts/activate
# PowerShell
.venv\Scripts\Activate.ps1
# or, without activating
uv run --no-sync python fit_spiral.py --help
```

Tests (from `spiral-fitting/`):

```sh
AGENTS_AGENT_MODE=1 PYTHONPATH=. uv run --no-sync python -m pytest -q \
  tests/test_spiral_sampling.py tests/test_surface_index.py \
  tests/test_track_crossing_cache.py tests/test_tracks_sqlite_dbm.py \
  tests/test_point_collection.py tests/test_devices.py tests/test_config.py \
  tests/test_cuda_startup.py tests/test_cpu_thread_limits.py
```
