#!/usr/bin/env bash
# One-shot setup and run of the full-setting A/B on a rented Linux GPU pod (Ubuntu, one NVIDIA card,
# compute capability >= 8.0, at least 60 GB of disk). Idempotent: rerunning skips what is already there.
#
#   bash tools/pod_setup.sh prepare     # clone villa, build the env, fetch the dataset (about 16.4 GiB)
#   bash tools/pod_setup.sh smoke       # 300 steps of arm A on the GPU, prints s/step; abort if it is slow
#   bash tools/pod_setup.sh run         # arm A then arm B, 30,000 steps, seed 1, team defaults
#
# Differences from the CPU arms (tasks/PROTOCOL.md): normals and gradient magnitude are ON (the fitter's
# defaults), steps 30,000 (config.py default), device cuda. z window and seed unchanged. Fibres stay off:
# the published dataset has no fibers/ folder (eval_fibers/ is for scoring), so the team's own runs on
# this dataset cannot use them either.
set -euo pipefail

WORK=${WORK:-$HOME/work}
VILLA_COMMIT=${VILLA_COMMIT:-862142652}
REPO=${REPO:-$WORK/vesuvius-layout-constraints}
SPIRAL=$WORK/villa/spiral-fitting
DATA=$REPO/data/spiral_datasets
STEPS=${STEPS:-30000}
SEED=${SEED:-1}
FULL='{"input_use_normals": true, "input_use_gradient_magnitude": true, "input_use_fibers": false}'

prepare() {
    mkdir -p "$WORK"
    if [ ! -d "$REPO/.git" ]; then
        git clone -q https://github.com/stantheman0128/vesuvius-layout-constraints "$REPO"
    fi
    if [ ! -d "$WORK/villa/.git" ]; then
        git clone -q --filter=blob:none --sparse https://github.com/ScrollPrize/villa "$WORK/villa"
        (cd "$WORK/villa" && git sparse-checkout set spiral-fitting vc_object_store && git checkout -q "$VILLA_COMMIT")
    fi
    command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    # On Linux the lock already pins the CUDA torch build, so a plain uv sync is right here
    # (the opposite of tasks/LOCAL_CPU_SETUP.md, which is about Windows CPU).
    (cd "$SPIRAL" && uv sync --frozen --group dev)
    "$SPIRAL/.venv/bin/python" -c "import torch, vc_spiral.spiral_sampling; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0))"
    mkdir -p "$DATA"
    [ -f "$DATA/manifest_full.json" ] || python3 -I "$REPO/tools/list_spiral.py" "$DATA/manifest_full.json" --with-lasagna
    # The root listing also carries fibers.afv (11.1 GB) and fiber_directions.npz (2.7 GB). Neither is read
    # by this commit: the catalog's "fibers" input is a directory named fibers/ (absent on S3) and
    # fiber_directions only loads when loss_weight_fiber_directions > 0 (default 0). Skip both.
    python3 -I "$REPO/tools/fetch.py" "$DATA/manifest_full.json" "$DATA/phercparis4" --workers 32 \
        --regex '^(?!fibers\.afv$|fiber_directions\.npz$)'
    # The fitter loads normals and gradient magnitude only from the packed sidecars
    # (lasagna_data.py: "there is no other loading path"), but input validation still wants the
    # three source zarr paths to be directories (fit_session.py optional_dir), so give it empty ones.
    for z in las_008_nx.ome.zarr las_008_ny.ome.zarr las_008_grad_mag.ome.zarr; do
        mkdir -p "$DATA/phercparis4/lasagna_inputs/$z"
    done
    if [ ! -f "$DATA/phercparis4_plus_layout/same_windings.json" ]; then
        python3 "$REPO/tools/make_arm_b.py" "$DATA/phercparis4" "$DATA/phercparis4_plus_layout" \
            "$REPO"/data/out/20230702185753_text_lines.json \
            "$REPO"/data/out/20260701183145-w116-117_column_gaps.json \
            "$REPO"/data/out/20260701183145-w116-117_text_lines.json
    fi
    # make_arm_b.py overrides only the four inputs the CPU arms used; the normals and gradient zarrs are
    # found by their conventional relative path, so arm B gets a symlink to arm A's folder.
    [ -e "$DATA/phercparis4_plus_layout/lasagna_inputs" ] || ln -s "$DATA/phercparis4/lasagna_inputs" "$DATA/phercparis4_plus_layout/lasagna_inputs"
    du -sh "$DATA"/phercparis4
}

arm() {  # arm A|B steps tag
    local arm=$1 steps=$2 tag=$3 ds
    [ "$arm" = A ] && ds=$DATA/phercparis4 || ds=$DATA/phercparis4_plus_layout
    export SPIRAL_FITTING_DIR=$SPIRAL SPIRAL_FITTING_PYTHON=$SPIRAL/.venv/bin/python
    # run_arm.py needs psutil, which the spiral lock installs on Linux, so run it with the venv python
    FIT_SPIRAL_DEVICE=cuda "$SPIRAL/.venv/bin/python" "$REPO/tools/run_arm.py" --arm "$arm" --dataset "$ds" \
        --steps "$steps" --seed "$SEED" --out "$REPO/runs" --tag "$tag" --extra "$FULL" \
        2>&1 | tee "$REPO/runs/${tag}_arm${arm}.stdout"
}

case ${1:-} in
    prepare) prepare ;;
    smoke)   arm A 300 gpusmoke; grep -o 'Optimizing.*' "$REPO/runs/gpusmoke_armA_s${SEED}_n300/fit.log" | tail -1 ;;
    run)     arm A "$STEPS" gpufull; arm B "$STEPS" gpufull;
             "$SPIRAL/.venv/bin/python" "$REPO/tools/read_metrics.py" "$REPO/runs/gpufull_armA_s${SEED}_n${STEPS}" "$REPO/runs/gpufull_armB_s${SEED}_n${STEPS}" | tee "$REPO/data/qa/slice3_metrics_gpufull.md" ;;
    *) echo "usage: $0 prepare|smoke|run"; exit 2 ;;
esac
