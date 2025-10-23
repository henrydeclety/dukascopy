# Dukascopy Price Data Manager

A comprehensive forex and commodity price data management system that downloads tick data from Dukascopy, exports to CSV, and resamples to OHLC format across multiple timeframes.

## Features

- **Multi-stage pipeline**: Download → Export → Resample
- **Dual operation modes**: Recent (2019-present) or Full (2006-present)
- **30 trading symbols**: Major forex pairs (EURUSD, GBPUSD, etc.) and commodities (XAUUSD, XAGUSD)
- **11 timeframes**: 1m, 5m, 10m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d
- **Concurrent downloads**: Multi-threaded for faster data acquisition
- **Portable architecture**: Auto-detects project directory, configurable data storage

## Quick Start

### 1. Setup

```bash
# Clone repository
git clone https://github.com/henrydeclety/dukascopy.git
cd dukascopy

# Create virtual environment
python3 -m venv myenv
source myenv/bin/activate

# Install dependencies
pip install -r dukascopy-data-manager/requirements.txt
pip install pandas

# Configure environment
cp .env.example .env
# Edit .env and set DATA_DIR=/path/to/your/data/storage
```

### 2. Run Full Pipeline

```bash
# Recent mode (2019-present, default)
bash refresh.sh

# Full mode (2006-present)
bash refresh.sh --full
```

That's it! The script will:
1. Download tick data for all 30 symbols
2. Export to CSV format
3. Resample to 11 different timeframes

## Usage

### Full Pipeline

```bash
bash refresh.sh [--recent|--full] [--reverse] [--only-absent]
```

**Options:**
- `--recent`: Download from 2019-01-01 (default)
- `--full`: Download from 2006-01-01
- `--reverse`: Process symbols in reverse order
- `--only-absent`: Skip existing files

### Individual Stages

```bash
# Download tick data only
bash run.sh download --recent

# Export to tick CSV only
bash run.sh export 1t --recent

# Resample to OHLC only
python main.py --mode=recent
```

### Single Symbol

```bash
# Activate virtual environment first
source myenv/bin/activate

# Download specific symbol
python dukascopy-data-manager/dukascopy-data-manager.py download EURUSD 2019-01-01 --mode=recent

# Export specific symbol
python dukascopy-data-manager/dukascopy-data-manager.py export EURUSD 1t 2019-01-01 --mode=recent
```

## Output Structure

```
{DATA_DIR}/dukascopy_live/
├── recent/
│   ├── download/
│   │   └── EURUSD/2024/01/15/14h_ticks.bi5
│   └── resampled/
│       └── EURUSD/
│           ├── EURUSD_1t.csv (tick data)
│           ├── EURUSD_resampled_1min.csv
│           ├── EURUSD_resampled_5min.csv
│           └── ... (9 more timeframes)
└── full/
    └── ... (same structure)
```

## Supported Symbols

Forex pairs, commodities, and indices including:
- **Majors**: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD
- **Crosses**: EURJPY, GBPJPY, EURGBP, AUDJPY, EURAUD, EURCHF, AUDNZD, NZDJPY, GBPAUD, GBPCAD
- **Commodities**: XAUUSD (Gold), XAGUSD (Silver)
- **And more**: See `symbols.txt` for complete list

## How It Works

1. **Download**: Fetches raw `.bi5` tick data from Dukascopy API
2. **Export**: Decompresses to CSV with bid/ask/volume columns
3. **Resample**: Calculates midpoint `(bid+ask)/2` and creates OHLC bars

## Requirements

- Python 3.8+
- pandas
- Dependencies from `dukascopy-data-manager/requirements.txt`

## Configuration

Edit `.env` file:
```bash
DATA_DIR=/mnt/storage/price_data  # Required: where to store data
```

Supports `~` expansion for home directory paths.

## Credits

Built on top of [dukascopy-data-manager](https://github.com/geodoomcraft/dukascopy-data-manager) by geodoomcraft.

## License

See `dukascopy-data-manager/LICENSE` for the original data manager license.
