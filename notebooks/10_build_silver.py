# Databricks notebook source
# MAGIC %md
# MAGIC # 10 · Build Silver (clean + quarantine)
# MAGIC Applies the shared `scdi.clean.split` — validates rows, quarantines bad
# MAGIC ones, de-dupes, assigns port zone + slowdown flag. The sample is small
# MAGIC (2–3 days, ADR-003) so a `toPandas()` round-trip is fine; for the full
# MAGIC archive port `scdi.clean` to native Spark.

# COMMAND ----------

# MAGIC %pip install /Volumes/workspace/supply_chain/raw/wheels/scdi-0.1.0-py3-none-any.whl
# MAGIC # Adjust the path if you used a different catalog/schema/volume.
# MAGIC # (In a Git folder instead of manual upload, swap this for: sys.path.insert(0, "../src"))

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "supply_chain")
dbutils.widgets.text("volume", "raw")
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
VOLUME = dbutils.widgets.get("volume")

# COMMAND ----------

from scdi.clean import split
from scdi.zones import load_zones

zones = load_zones(f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/ports.json")

bronze_pd = spark.table(f"{CATALOG}.{SCHEMA}.ais_raw").toPandas()
silver_pd, quarantine_pd = split(bronze_pd, zones)

print(f"silver: {len(silver_pd)}   quarantined: {len(quarantine_pd)}")

# COMMAND ----------

spark.createDataFrame(silver_pd).write.mode("overwrite").saveAsTable(
    f"{CATALOG}.{SCHEMA}.vessel_positions"
)
if len(quarantine_pd):
    spark.createDataFrame(
        quarantine_pd.astype({"ts": "string"})  # keep quarantine schema simple
    ).write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.vessel_positions_quarantine")

display(spark.table(f"{CATALOG}.{SCHEMA}.vessel_positions"))
