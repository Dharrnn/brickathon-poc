"""Run the full Bronze->Silver->Gold pipeline locally on the sample data.

No Databricks, no Spark — proves the transform/scoring logic end-to-end and
writes the curated tables to data/out/ as CSV + Parquet. The Databricks notebooks
do the same thing but read from a Unity Catalog Volume and persist Delta tables.

    uv run python scripts/run_local.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from scdi.clean import split
from scdi.pipeline import build_gold
from scdi.zones import load_zones

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample"
OUT = ROOT / "data" / "out"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    zones = load_zones(ROOT / "data" / "ports.json")

    bronze = pd.read_csv(SAMPLE / "ais_sample.csv")
    weather = pd.read_csv(SAMPLE / "weather_sample.csv")

    silver, quarantine = split(bronze, zones)
    gold = build_gold(silver, weather)

    for name, df in {"silver": silver, "quarantine": quarantine, "gold": gold}.items():
        df.to_csv(OUT / f"{name}.csv", index=False)
        df.to_parquet(OUT / f"{name}.parquet", index=False)

    print(f"Bronze rows:      {len(bronze)}")
    print(f"Silver rows:      {len(silver)}  (quarantined: {len(quarantine)})")
    print(f"Gold rows:        {len(gold)}")
    print("\n--- Gold: disruption_risk (sorted by delay_score) ---")
    with pd.option_context("display.max_columns", None, "display.width", 240):
        print(
            gold[
                ["vessel_name", "port_zone", "avg_sog", "weather_severity",
                 "delay_score", "risk_band", "top_factor"]
            ].to_string(index=False)
        )
    print("\n--- Reasoning (why each vessel is flagged) ---")
    for row in gold.itertuples(index=False):
        print(f"  {row.vessel_name} [{row.risk_band}, {row.delay_score:.0f}]: {row.reasoning}")
    print(f"\nWrote curated tables to {OUT}")


if __name__ == "__main__":
    main()
