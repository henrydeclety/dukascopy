import os
import pandas as pd
from tqdm import tqdm

from main import resampled_dir, get_symbols

def get_symbols():
    files = [folder for folder in os.listdir(resampled_dir) if os.path.isdir(os.path.join(resampled_dir, folder))]
    return files

if __name__ == "__main__":
    for symbol in tqdm(get_symbols()):
        fname = f"{resampled_dir}/{symbol}/{symbol}_resampled_1t.csv"
        if os.path.exists(fname):
            df = pd.read_csv(fname)
            df.rename(columns={"TIME": "ts", "ASKP": "ask", "BIDP": "bid", "ASKV": "ask_volume", "BIDV": "bid_volume"}, inplace=True)
            df = df[["ts", "bid", "ask"]]
            df.to_csv(fname, index=False)
