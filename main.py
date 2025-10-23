import os
import pandas as pd
from tqdm import tqdm
import argparse
from pathlib import Path

# Load environment variables from .env file
def load_env():
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()

def get_paths(mode: str = "recent"):
    """Get paths based on mode (recent or full)"""
    data_dir = os.environ.get('DATA_DIR')
    if not data_dir:
        raise ValueError("DATA_DIR not found in environment. Please set it in .env file")
    dukascopy_storage = f"{os.path.expanduser(data_dir)}/dukascopy_live"
    if mode == "recent":
        resampled_dir = f'{dukascopy_storage}/recent/resampled'
    else:
        resampled_dir = f'{dukascopy_storage}/full/resampled'
    return resampled_dir

# Default to recent mode since that's where the data exists
resampled_dir = get_paths("recent")

def resolve_existing_mode(preferred_mode: str = "recent"):
    """Return a tuple of (resolved_mode, resampled_dir) that actually exists on disk.

    Falls back to the alternate mode if the preferred one does not exist.
    Raises FileNotFoundError if neither exists.
    """
    preferred_dir = get_paths(preferred_mode)
    if os.path.exists(preferred_dir):
        return preferred_mode, preferred_dir

    alternate_mode = "recent" if preferred_mode == "full" else "full"
    alternate_dir = get_paths(alternate_mode)
    if os.path.exists(alternate_dir):
        print(f"Warning: Directory {preferred_dir} does not exist. Using '{alternate_mode}' mode instead.")
        return alternate_mode, alternate_dir

    raise FileNotFoundError(
        f"Neither {preferred_dir} nor {alternate_dir} exist. Please check your data directory.")


def get_symbols(mode: str = "recent"):
    resolved_mode, resampled_dir = resolve_existing_mode(mode)
    files = [folder for folder in os.listdir(resampled_dir) if os.path.isdir(os.path.join(resampled_dir, folder))]
    return files

def get_price_df(symbol, verbose=True, mode: str = "full"):
    resolved_mode, resampled_dir = resolve_existing_mode(mode)
    if symbol is not None:
        all_symbols = get_symbols(resolved_mode)
        if symbol not in all_symbols:
            raise Exception(f"Symbol {symbol} not found in mode '{resolved_mode}'")

    # Read the tick data file
    csv_path = f"{resampled_dir}/{symbol}/{symbol}_1t.csv"
    if not os.path.exists(csv_path):
        # Last-resort: try alternate mode once in case the symbol exists only there
        alternate_mode, alternate_dir = resolve_existing_mode("recent" if resolved_mode == "full" else "full")
        alt_csv_path = f"{alternate_dir}/{symbol}/{symbol}_1t.csv"
        if os.path.exists(alt_csv_path):
            print(f"Warning: File not found at {csv_path}. Using {alt_csv_path} instead.")
            csv_path = alt_csv_path
        else:
            raise FileNotFoundError(f"Tick CSV not found for {symbol}: {csv_path}")

    price_df = pd.read_csv(csv_path)
    price_df.set_index("date", inplace=True)
    price_df.index = pd.to_datetime(price_df.index, errors='coerce')

    unreadable_count = len(price_df[price_df.index.isnull()])
    if verbose and unreadable_count > 0:
        print(f"dropping {unreadable_count} ({unreadable_count/len(price_df):.5%}) unreadable indexes")
    price_df = price_df[~price_df.index.isnull()]
    nan_count = len(price_df) - len(price_df.dropna())
    if verbose and nan_count > 0:
        print(f"dropping {nan_count} ({nan_count/len(price_df):.5%}) nan rows")
    
    # Convert bid/ask data to OHLC format using the midpoint
    clean_df = price_df.dropna().sort_index()
    clean_df['price'] = (clean_df['bid'] + clean_df['ask']) / 2
    
    # Create OHLC data for 1-minute resampling
    ohlc_df = clean_df['price'].resample('1min').agg({
        'open': 'first',
        'high': 'max', 
        'low': 'min',
        'close': 'last'
    }).dropna()
    
    return ohlc_df

def get_price_df_resampled(timeframe, symbol=None, verbose=True, nocache=False, mode: str = "full"):
    resolved_mode, resampled_dir = resolve_existing_mode(mode)
    path = f"{resampled_dir}/{symbol}/{symbol}_resampled_{timeframe}.csv"
    if os.path.exists(path) and not nocache:
        return pd.read_csv(path).set_index("date")
    else:
        df = get_price_df(symbol, verbose, resolved_mode).resample(timeframe).agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
        })
        # Ensure the directory exists before saving
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_csv(path)
        return df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process price data for different timeframes')
    parser.add_argument('--symbol', type=str, help='Specific symbol to process. If not provided, processes all symbols.')
    parser.add_argument('--mode', type=str, choices=['recent', 'full'], default='recent', 
                       help='Mode: recent or full - determines which directories to use')
    parser.add_argument('--reverse', action='store_true', 
                       help='Reverse the order of symbols processing')
    args = parser.parse_args()

    mytqdm = tqdm(["1min", "5min", "10min", "15min", "30min", "1h", "2h", "4h", "6h", "12h", "1d"])
    for timeframe in mytqdm:
        mytqdm.set_description(timeframe)
        symbols = [args.symbol] if args.symbol else get_symbols(args.mode)
        if args.reverse and not args.symbol:
            symbols = list(reversed(symbols))
        for symbol in symbols:
            _ = get_price_df_resampled(timeframe, symbol, nocache=True, mode=args.mode)