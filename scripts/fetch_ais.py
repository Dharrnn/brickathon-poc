"""Pre-download a small, real NOAA AIS sample filtered to the port zones.

NOAA publishes one zipped CSV per day for 2024 (the full year is 116.7 GB), so
this fetches only a few days and keeps only the rows that fall inside a monitored
port zone — the exact rows the pipeline scores — then thins the ping rate. Run it
on a machine where coast.noaa.gov is reachable, then upload the output to the
Databricks Volume (ADR-003).

    uv run python scripts/fetch_ais.py --dates 2024-01-01 2024-01-02 \
        --out data/raw/ais/ais_sample.csv

NOAA 2024 AIS index: https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2024/
Schema (marinecadastre): https://hub.marinecadastre.gov/pages/vesseltraffic
"""

from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

from scdi.zones import assign_zone, load_zones

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2024"
KEEP_COLS = ["MMSI", "BaseDateTime", "LAT", "LON", "SOG", "VesselName"]


def _download_day(date: str) -> bytes:
    """Download one AIS_YYYY_MM_DD.zip (date as YYYY-MM-DD)."""
    fname = f"AIS_{date.replace('-', '_')}.zip"
    url = f"{BASE_URL}/{fname}"
    print(f"downloading {url} ...")
    resp = requests.get(url, timeout=600)
    resp.raise_for_status()
    return resp.content


def _rows_in_zones(zip_bytes: bytes, zones, sample_minutes: int) -> pd.DataFrame:
    """Read the CSV inside the zip in chunks, keep only in-zone rows, thin pings."""
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    csv_name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
    kept: list[pd.DataFrame] = []
    with zf.open(csv_name) as fh:
        for chunk in pd.read_csv(fh, usecols=KEEP_COLS, chunksize=200_000):
            chunk = chunk.dropna(subset=["LAT", "LON"])
            zone = [assign_zone(la, lo, zones) for la, lo in zip(chunk["LAT"], chunk["LON"])]
            chunk = chunk.assign(_zone=zone)
            kept.append(chunk[chunk["_zone"].notna()].drop(columns="_zone"))
    if not kept:
        return pd.DataFrame(columns=KEEP_COLS)
    df = pd.concat(kept, ignore_index=True)

    # Thin: one ping per vessel per `sample_minutes` bucket.
    df["BaseDateTime"] = pd.to_datetime(df["BaseDateTime"], errors="coerce")
    df = df.dropna(subset=["BaseDateTime"])
    df["_bucket"] = df["BaseDateTime"].dt.floor(f"{sample_minutes}min")
    df = df.drop_duplicates(subset=["MMSI", "_bucket"]).drop(columns="_bucket")
    return df.sort_values(["MMSI", "BaseDateTime"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dates", nargs="+", required=True, help="YYYY-MM-DD ...")
    parser.add_argument("--sample-minutes", type=int, default=30)
    parser.add_argument("--out", default=str(ROOT / "data" / "raw" / "ais" / "ais_sample.csv"))
    args = parser.parse_args()

    zones = load_zones(ROOT / "data" / "ports.json")
    frames = [
        _rows_in_zones(_download_day(d), zones, args.sample_minutes) for d in args.dates
    ]
    out_df = pd.concat(frames, ignore_index=True)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out, index=False)
    print(f"wrote {len(out_df)} in-zone rows across {len(args.dates)} day(s) to {out}")


if __name__ == "__main__":
    main()
