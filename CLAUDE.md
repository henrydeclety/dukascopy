# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a forex/commodity price data management system that downloads tick data from Dukascopy, exports it to various timeframes, and resamples it into OHLC format. The system uses a multi-stage pipeline architecture with two operational modes: `recent` (2019-present) and `full` (2006-present).

## Environment Configuration

**CRITICAL**: The `.env` file is REQUIRED and must contain:
- `DATA_DIR`: Path where price data is stored (e.g., `/mnt/storage/price_data`)
  - Scripts will fail with `ValueError` if this is not set
  - Use `.env.example` as template
  - Supports `~` expansion for home directory paths

The project directory is auto-detected using `${BASH_SOURCE[0]}` in bash scripts and `Path(__file__).parent` in Python, making the project fully portable.

## Architecture

### Three-Stage Pipeline

1. **Download Stage** (`dukascopy-data-manager.py download`)
   - Downloads raw tick data from Dukascopy API as `.bi5` files
   - Stores in `{DATA_DIR}/dukascopy_live/{mode}/download/{SYMBOL}/YYYY/MM/DD/HHh_ticks.bi5`
   - Supports concurrent downloads (default 5 workers)

2. **Export Stage** (`dukascopy-data-manager.py export`)
   - Decompresses `.bi5` files and exports to CSV
   - Outputs tick data (`1t`) with columns: timestamp, bid, ask, bid_volume, ask_volume
   - Stores in `{DATA_DIR}/dukascopy_live/{mode}/resampled/{SYMBOL}/{SYMBOL}_1t.csv`

3. **Resample Stage** (`main.py`)
   - Reads tick CSVs and creates OHLC data at multiple timeframes
   - Computes midpoint: `(bid + ask) / 2`
   - Resamples to: 1min, 5min, 10min, 15min, 30min, 1h, 2h, 4h, 6h, 12h, 1d
   - Outputs: `{DATA_DIR}/dukascopy_live/{mode}/resampled/{SYMBOL}/{SYMBOL}_resampled_{TIMEFRAME}.csv`

### Mode System

The system operates in two modes that affect directory structure and date ranges:

- **recent**: Data from 2019-01-01 onwards (default)
- **full**: Data from 2006-01-01 onwards

Mode is specified via `--mode={recent|full}` or `--recent`/`--full` flags. All three stages must use the same mode for consistency.

### Symbol Management

Trading symbols are defined in `symbols.txt` (one per line). The system processes 30 symbols including major forex pairs (EURUSD, GBPUSD, etc.) and commodities (XAUUSD, XAGUSD).

## Common Commands

### Full Pipeline Execution

```bash
# Recent mode (2019-present, default)
bash refresh.sh

# Full mode (2006-present)
bash refresh.sh --full

# With reverse symbol processing
bash refresh.sh --reverse

# Only export missing files
bash refresh.sh --only-absent
```

The `refresh.sh` orchestrator runs all three stages sequentially with proper mode propagation.

### Individual Stage Commands

```bash
# Download tick data
bash run.sh download [--recent|--full] [--reverse]

# Export to tick CSV
bash run.sh export 1t [--recent|--full] [--only-absent]

# Resample to OHLC timeframes
python main.py --mode=recent [--symbol EURUSD] [--reverse]
```

### Direct Data Manager Usage

```bash
# Activate virtual environment first
source myenv/bin/activate

# Download specific symbol
python dukascopy-data-manager/dukascopy-data-manager.py download EURUSD 2019-01-01 --mode=recent

# Export with custom timeframe (t=ticks, s=seconds, m=minutes, h=hours, D=days, W=weeks)
python dukascopy-data-manager/dukascopy-data-manager.py export EURUSD 5m 2019-01-01 --mode=recent

# Export all downloaded symbols
python dukascopy-data-manager/dukascopy-data-manager.py export all 1t 2019-01-01 --mode=recent
```

## Key Implementation Details

### Path Resolution Strategy

- **Project paths**: Auto-detected via `PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`
- **Data paths**: Loaded from `.env` file, no defaults provided (fail-fast)
- **Mode-based directories**: Functions like `get_paths(mode)` return different subdirectories based on mode

### Data Processing Flow

1. `run.sh` iterates through `symbols.txt` and processes each symbol individually
2. Tick data (bid/ask) is converted to OHLC using midpoint calculation
3. `main.py` uses pandas resample with aggregations: `first`, `max`, `min`, `last`
4. All CSV files use pandas with `date` column as index

### Error Handling

- Missing `.env` or `DATA_DIR`: Raises `ValueError` immediately
- Mode mismatch: `resolve_existing_mode()` attempts fallback between recent/full modes
- Missing symbols: Validated against available directories before processing
- Download failures: Logged but don't halt batch processing (concurrent.futures exception handling)

## File Structure

```
dukas_prices/
├── .env                    # Required: DATA_DIR configuration
├── symbols.txt             # Trading symbols list
├── run.sh                  # Stage executor (download/export)
├── refresh.sh              # Pipeline orchestrator
├── main.py                 # OHLC resampling
└── dukascopy-data-manager/
    └── dukascopy-data-manager.py  # Download & export logic
```

Data directory structure (external to project):
```
{DATA_DIR}/dukascopy_live/
├── recent/
│   ├── download/{SYMBOL}/YYYY/MM/DD/HHh_ticks.bi5
│   └── resampled/{SYMBOL}/{SYMBOL}_{1t|resampled_TIMEFRAME}.csv
└── full/
    ├── download/...
    └── resampled/...
```

## Development Notes

- Virtual environment: `myenv/` (activated automatically by scripts)
- The system uses simple `.env` parsing (no python-dotenv dependency)
- Concurrent downloads use ThreadPoolExecutor with configurable workers
- Date ranges are exclusive of the most recent hour to avoid incomplete data
- Symbol processing order can be reversed with `--reverse` flag for resuming interrupted downloads
