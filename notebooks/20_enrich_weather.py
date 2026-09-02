# Databricks notebook source
# MAGIC %md
# MAGIC # 20 · Enrich Weather
# MAGIC Load the pre-fetched Open-Meteo weather (uploaded to the Volume by
# MAGIC `scripts/fetch_weather.py`) and compute the `[0,1]` marine severity per
# MAGIC hour. No outbound calls (ADR-003).

# COMMAND ----------

# MAGIC %pip install /Volumes/workspace/supply_chain/raw/wheels/scdi-0.1.0-py3-none-any.whl
# MAGIC # Adjust the path if you used a different catalog/schema/volume.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "supply_chain")
dbutils.widgets.text("volume", "raw")
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
VOLUME = dbutils.widgets.get("volume")

# COMMAND ----------

import pandas as pd

from scdi.weather import severity

weather_path = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/weather/weather.csv"
w = pd.read_csv(weather_path)
w["severity"] = [
    severity(ws, wg, pr)
    for ws, wg, pr in zip(w["wind_speed"], w["wind_gust"], w["precipitation"])
]

spark.createDataFrame(w).write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.weather_obs")
display(spark.table(f"{CATALOG}.{SCHEMA}.weather_obs"))
