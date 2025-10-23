#!/bin/bash

# Dynamically detect project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# File containing the symbols
SYMBOLS_FILE="${PROJECT_DIR}/symbols.txt"

# Debug output
echo "Debug: Arguments passed to run.sh: $*"

# Check for --recent flag
if [[ "$*" == *"--recent"* ]]; then
    START_DATE="2019-01-01"
    MODE="recent"
else
    START_DATE="2006-01-01"
    MODE="full"
fi

# Check for --reverse flag
if [[ "$*" == *"--reverse"* ]]; then
    REVERSE_SYMBOLS=true
else
    REVERSE_SYMBOLS=false
fi

source "${PROJECT_DIR}/myenv/bin/activate"

# Process each symbol individually
if [ "$1" == "download" ] && [ "$REVERSE_SYMBOLS" = true ]; then
    # Reverse the symbols for download
    tac "$SYMBOLS_FILE" | while read -r symbol; do
        echo "Processing symbol: $symbol"
        python "${PROJECT_DIR}/dukascopy-data-manager/dukascopy-data-manager.py" $1 "$symbol" $START_DATE --concurrent=5 --mode=$MODE
    done
else
    # Normal processing (original order)
    while read -r symbol; do
        echo "Processing symbol: $symbol"
        # Check if the first argument is 'download' and include --concurrent=10 if true
        if [ "$1" == "download" ]; then
            python "${PROJECT_DIR}/dukascopy-data-manager/dukascopy-data-manager.py" $1 "$symbol" $START_DATE --concurrent=5 --mode=$MODE
        else
            # Check for --only-absent flag and pass it to export command if present
            echo "Debug: Checking for --only-absent in: $*"
            if [[ "$*" == *"--only-absent"* ]]; then
                echo "Debug: --only-absent flag detected in run.sh"
                python "${PROJECT_DIR}/dukascopy-data-manager/dukascopy-data-manager.py" $1 "$symbol" $2 $START_DATE --only-absent --mode=$MODE
            else
                echo "Debug: --only-absent flag NOT detected in run.sh"
                python "${PROJECT_DIR}/dukascopy-data-manager/dukascopy-data-manager.py" $1 "$symbol" $2 $START_DATE --mode=$MODE
            fi
        fi
    done < "$SYMBOLS_FILE"
fi
