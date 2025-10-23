#!/usr/bin/env bash

# Dynamically detect project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Determine mode. Prefer explicit flag; default to recent to match available data.
if [[ "$*" == *"--full"* ]]; then
    MODE="full"
elif [[ "$*" == *"--recent"* ]]; then
    MODE="recent"
else
    MODE="recent"
fi

# Build mode flag for downstream scripts
if [[ "$MODE" == "recent" ]]; then
    MODE_FLAG="--recent"
else
    MODE_FLAG=""
fi

# Check for --reverse flag to determine if symbols should be reversed
if [[ "$*" == *"--reverse"* ]]; then
    REVERSE="--reverse"
else
    REVERSE=""
fi

echo "Debug: Arguments passed to refresh.sh: $*"
echo "Debug: Resolved MODE=$MODE (MODE_FLAG='${MODE_FLAG}')"

# 1) Download ticks for the chosen mode
bash "${PROJECT_DIR}/run.sh" download $MODE_FLAG $REVERSE

# 2) Export 1t for the same mode (and propagate --only-absent if present)
if [[ "$*" == *"--only-absent"* ]]; then
    echo "Debug: --only-absent flag detected in refresh.sh"
    bash "${PROJECT_DIR}/run.sh" export 1t $MODE_FLAG --only-absent
else
    echo "Debug: --only-absent flag NOT detected in refresh.sh"
    bash "${PROJECT_DIR}/run.sh" export 1t $MODE_FLAG
fi

# 3) Resample via Python with the same mode
"${PROJECT_DIR}/myenv/bin/python" "${PROJECT_DIR}/main.py" --mode=$MODE