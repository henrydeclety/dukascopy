import typer
from typing_extensions import Annotated
from rich.progress import track
from rich.console import Console
from rich.table import Table
import requests
import concurrent.futures
from pathlib import Path
from datetime import datetime, timedelta, timezone
import lzma
import numpy as np
import pandas as pd
import os

app = typer.Typer()

# Load environment variables from .env file
def load_env():
    """Load environment variables from .env file in parent directory"""
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()

def get_paths(mode: str = "full"):
    """Get download and export paths based on mode (recent or full)"""
    data_dir = os.environ.get('DATA_DIR')
    if not data_dir:
        raise ValueError("DATA_DIR not found in environment. Please set it in .env file")
    base_path = f"{os.path.expanduser(data_dir)}/dukascopy_live/"
    if mode == "recent":
        download_path = f"{base_path}recent/download/"
        export_path = f"{base_path}recent/resampled/"
    else:
        download_path = f"{base_path}full/download/"
        export_path = f"{base_path}full/resampled/"
    return download_path, export_path

@app.command()
def download(assets:Annotated[list[str], typer.Argument(help="Give a list of assets to download. Eg. EURUSD AUDUSD")],
             start:Annotated[str, typer.Argument(help="Start date to download in YYYY-MM-DD format. Eg. 2024-01-08")],
             end:Annotated[str, typer.Option(help="End date to download in YYYY-MM-DD format. If not provided, will download until current date Eg. 2024-01-08")]="",
             concurrent:Annotated[int, typer.Option(help="Max number of concurrent downloads (defaults to 3)")]=3,
             force:Annotated[bool, typer.Option(help="Redownload files. By default, without this flag, files that already exist will be skipped")]=False,
             mode:Annotated[str, typer.Option(help="Mode: 'recent' or 'full' - determines which directories to use")]="full"):
    """
    Download assets
    """
    download_path, _ = get_paths(mode)
    
    start_date_str = start.split("-")
    end_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
    base_url = "https://datafeed.dukascopy.com/datafeed/"

    if end != "":
        end_date = end.split("-")
        end_date = datetime(int(end_date[0]), int(end_date[1]), int(end_date[2]))

    processes = concurrent

    delta = timedelta(hours=1)
    for asset in assets:
        filenames = []
        urls = []
        forces = []

        start_date = datetime(int(start_date_str[0]), int(start_date_str[1]), int(start_date_str[2]))
        while start_date <= end_date:
            year = start_date.year
            month = start_date.month-1
            day = start_date.day
            hour = start_date.hour

            filenames.append(Path(f"{download_path}{asset}/{year}/{month:0>2}/{day:0>2}/{hour:0>2}h_ticks.bi5"))
            urls.append(f"{base_url}{asset}/{year}/{month:0>2}/{day:0>2}/{hour:0>2}h_ticks.bi5")
            forces.append(force)

            start_date += delta
        inputs = zip(filenames, urls, forces)
        download_file_parallel(inputs, asset, len(filenames), processes)
    print("Download completed")

def download_file_parallel(file_url_zip, asset:str, length:int, processes_num=None):
    with concurrent.futures.ThreadPoolExecutor(max_workers=processes_num) as executor:
        args_list = tuple(file_url_zip)
        results = [executor.submit(download_file, args) for args in args_list]
        for future in track(concurrent.futures.as_completed(results), total=length, description=f"Downloading {asset}..."):
            try:
                future.result()  # This will raise any exception that occurred
            except Exception as e:
                print(f"Warning: Download failed for one file: {e}")
                # Continue with other downloads

def download_file(args):
    filename, url, is_force = args[0], args[1], args[2]

    if filename.exists() and not is_force:
        return

    r = requests.get(url, timeout=(10, 30))  # 10s connect timeout, 30s read timeout
    if not r:
        print(f"Error: {r} for {url}")
        return
    # else:
    #     print(f"Succes: {r} for {url}")

    filename.parent.mkdir(exist_ok=True, parents=True)

    with open(filename, 'wb') as f:
        f.write(r.content)

@app.command()
def export(assets:Annotated[list[str], typer.Argument(help="Give a list of assets to export. Use 'all' for all downloaded assets. Eg. EURUSD AUDUSD. Check export --help for more info")],
           timeframe:Annotated[str, typer.Argument(help="Timeframe to export. Format should be [Number][Unit] eg. 1h or 1t. Check export --help for more info about units.")],
           start:Annotated[str, typer.Argument(help="Start date to export in YYYY-MM-DD format. Eg. 2024-01-08")],
           end:Annotated[str, typer.Option(help="End date to export in YYYY-MM-DD format. If not provided, will export until current date Eg. 2024-01-08")]="",
           only_absent:Annotated[bool, typer.Option(help="Only export if the file does not already exist")]=False,
           mode:Annotated[str, typer.Option(help="Mode: 'recent' or 'full' - determines which directories to use")]="full"):
    """
    Export downloaded data into different timeframes/units.\n
    assets can be selected by listing multiple with a space dividing them or a single asset.\n
    Eg. export AUDUSD EURUSD\n
    Can also use all to select all downloaded assets.\n
    Available units:\n
        t: ticks (eg. 1t)\n
        s: seconds (eg. 10s)\n
        m: minutes (eg. 15m)\n
        h: hours (eg. 4h)\n
        D: days (eg. 2D)\n
        W: weeks (eg. 2W)\n
    """
    console = Console()
    download_path, export_path = get_paths(mode)
    
    asset_list = []
    if assets[0] == "all":
        dirs = Path(download_path).glob("*")
        for dir in dirs:
            parts = dir.parts
            asset_list.append(parts[1])
    else:
        asset_list = assets

    start_date_str = start.split("-")
    end_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)

    if end != "":
        end_date = end.split("-")
        end_date = datetime(int(end_date[0]), int(end_date[1]), int(end_date[2]))

    delta = timedelta(hours=1)
    for asset in asset_list:
        # Determine export filename first
        if timeframe == "1t":
            export_file = Path(f"{export_path}/{asset}/{asset}_{timeframe}.csv")
        else:
            export_file = Path(f"{export_path}/{asset}/{asset}_resampled_{timeframe}.csv")

        if only_absent and export_file.exists():
            console.print(f"Skipping {asset} - file already exists at {export_file}")
            continue

        filenames = []
        file_times = []

        start_date = datetime(int(start_date_str[0]), int(start_date_str[1]), int(start_date_str[2]))
        while start_date <= end_date:
            year = start_date.year
            month = start_date.month-1
            day = start_date.day
            hour = start_date.hour

            filenames.append(Path(f"{download_path}{asset}/{year}/{month:0>2}/{day:0>2}/{hour:0>2}h_ticks.bi5"))
            file_times.append(datetime(year, month+1, day, hour))

            start_date += delta

        df_list = []
        found_first_file = False
        missing_count = 0
        missing_start_date = None
        
        for i in track(range(len(filenames)), description=f"Reading {asset} tick files..."):
            file = filenames[i]
            if not file.is_file():
                if not found_first_file:
                    if missing_count == 0:
                        missing_start_date = file_times[i]
                    missing_count += 1
                else:
                    print(f"{file} is missing, skipping this file.")
                continue
            
            if missing_count > 0 and not found_first_file:
                print(f"{missing_count} files missing from {missing_start_date.strftime('%Y-%m-%d %H:00')} to {file_times[i-1].strftime('%Y-%m-%d %H:00')}")
                missing_count = 0
            
            found_first_file = True
            
            if file.stat().st_size == 0:
                continue
                
            dt = np.dtype([('TIME', '>i4'), ('ASKP', '>i4'), ('BIDP', '>i4'), ('ASKV', '>f4'), ('BIDV', '>f4')])
            data = np.frombuffer(lzma.open(file, mode="rb").read(),dt)
            df = pd.DataFrame(data)
            df["TIME"] = pd.to_datetime(df["TIME"], unit="ms", origin=file_times[i])
            df_list.append(df)

        # Handle case where all files are missing
        if missing_count > 0 and not found_first_file:
            print(f"{missing_count} files missing from {missing_start_date.strftime('%Y-%m-%d %H:00')} to {file_times[-1].strftime('%Y-%m-%d %H:00')}")

        if not df_list:
            print(f"No data found for {asset}")
            continue

        df = pd.concat(df_list, ignore_index=True)
        df["ASKP"] = df["ASKP"].astype(np.int32)
        df["BIDP"] = df["BIDP"].astype(np.int32)
        df["ASKV"] = df["ASKV"].astype(np.float32)
        df["BIDV"] = df["BIDV"].astype(np.float32)

        df["ASKP"] = df["ASKP"] / 100_000
        df["BIDP"] = df["BIDP"] / 100_000

        with console.status(f"Aggregating {asset} data...") as status:
            agg_df = aggregate_data(df, timeframe)
            console.print(f"{asset} data aggregated")
            status.update(f"Exporting {asset} to file...")

            export_file.parent.mkdir(exist_ok=True, parents=True)
            agg_df.to_csv(export_file, index=False)
            console.print(f"{asset} exported to {export_file}")

    print(f"Export completed. Data located at {Path(export_path).resolve()}")


def aggregate_data(df:pd.DataFrame, tf:str):
    if "t" in tf:
        tick_num = int(tf.split("t")[0])
        if tick_num == 1:
            return df.rename(columns={
                "TIME": "date",
                "BIDP": "bid",
                "ASKP": "ask", 
                "BIDV": "bid_volume", 
                "ASKV": "ask_volume"
            })[["date", "bid", "ask", "bid_volume", "ask_volume"]]
        
        df_group = df.groupby(df.index // tick_num)
        agg_df = pd.DataFrame()
        agg_df["date"] = df_group["TIME"].first()
        agg_df["open"] = df_group["BIDP"].first()
        agg_df["high"] = df_group["BIDP"].max()
        agg_df["low"] = df_group["BIDP"].min()
        agg_df["close"] = df_group["BIDP"].last()
        agg_df["vol"] = df_group["BIDV"].sum()

        # extra insights
        agg_df["ao"] = df_group["ASKP"].first()
        agg_df["ah"] = df_group["ASKP"].max()
        agg_df["al"] = df_group["ASKP"].min()
        agg_df["ac"] = df_group["ASKP"].last()
        agg_df["av"] = df_group["ASKV"].sum()
        agg_df["tv"] = df_group["ASKV"].count()

        return agg_df

    agg_time = pd.Timedelta(tf)

    df = df.set_index("TIME")
    df_group = df.resample(agg_time)

    agg_df = pd.DataFrame()
    agg_df["open"] = df_group["BIDP"].first()
    agg_df["high"] = df_group["BIDP"].max()
    agg_df["low"] = df_group["BIDP"].min()
    agg_df["close"] = df_group["BIDP"].last()
    agg_df["vol"] = df_group["BIDV"].sum()

    # extra insights
    agg_df["ao"] = df_group["ASKP"].first()
    agg_df["ah"] = df_group["ASKP"].max()
    agg_df["al"] = df_group["ASKP"].min()
    agg_df["ac"] = df_group["ASKP"].last()
    agg_df["av"] = df_group["ASKV"].sum()
    agg_df["tv"] = df_group["ASKV"].count()

    agg_df = agg_df.reset_index(names="date")

    agg_df = agg_df.dropna()
    return agg_df

@app.command("list")
def list_command(mode:Annotated[str, typer.Option(help="Mode: 'recent' or 'full' - determines which directories to use")]="full"):
    """
    List all downloaded assets
    """
    assets = grab_asset_dirs(mode)

    table = Table(title="Downloaded Data")

    table.add_column("Asset")
    table.add_column("Start Date (YYYY-MM-DD)")
    table.add_column("End Date (YYYY-MM-DD)")

    for asset in assets:
        table.add_row(asset, min(assets[asset]).strftime("%Y-%m-%d"), max(assets[asset]).strftime("%Y-%m-%d"))

    console = Console()
    console.print(table)
    console.print(f"Total Number of Assets: {len(assets)}")

@app.command()
def update(assets:Annotated[list[str], typer.Argument(help="Give a list of assets to update. Use 'all' for all downloaded assets. Eg. EURUSD AUDUSD. Check update --help for more info")],
           start:Annotated[str, typer.Option(help="Start date to update from in YYYY-MM-DD format. This overrides the default which uses the latest downloaded file as the start date. Eg. 2024-01-08")]="",
           concurrent:Annotated[int, typer.Option(help="Max number of concurrent downloads (defaults to 3)")]=3,
           force:Annotated[bool, typer.Option(help="Redownload files. By default, without this flag, files that already exist will be skipped. This can be used with --start to force redownload.")]=False,
           mode:Annotated[str, typer.Option(help="Mode: 'recent' or 'full' - determines which directories to use")]="full"):
    """
    Update downloaded assets to latest date.\n
    assets can be selected by listing multiple with a space dividing them or a single asset.\n
    Eg. export AUDUSD EURUSD\n
    Can also use all to select all downloaded assets.\n
    Eg. export all\n
    """
    assets_dict = grab_asset_dirs(mode)
    if assets[0] != "all":
        for asset in assets:
            start_date = max(assets_dict[asset])
            if start != "":
                start_split = start.split("-")
                start_date = datetime(int(start_split[0]), int(start_split[1]), int(start_split[2]))
            download([asset], start_date.strftime("%Y-%m-%d"), concurrent=concurrent, force=force, mode=mode)
        return

    for asset in assets_dict:
        start_date = max(assets_dict[asset])
        if start != "":
            start_split = start.split("-")
            start_date = datetime(int(start_split[0]), int(start_split[1]), int(start_split[2]))
        download([asset], start_date.strftime("%Y-%m-%d"), concurrent=concurrent, force=force, mode=mode)


def grab_asset_dirs(mode: str = "full"):
    download_path, _ = get_paths(mode)
    dirs = Path(download_path).glob("*/*/*/*")
    assets = {}
    for dir in dirs:
        parts = dir.parts
        asset = parts[1]
        if asset not in assets:
            assets[asset] = []
        assets[asset].append(datetime(int(parts[2]), int(parts[3])+1, int(parts[4])))
    return assets

if __name__ == "__main__":
    app()
