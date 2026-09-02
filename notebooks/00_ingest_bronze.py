# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Ingest Bronze
# MAGIC Load pre-staged NOAA AIS CSVs from a Unity Catalog Volume into a raw Delta
# MAGIC table. Data is pre-uploaded (ADR-003) — no outbound calls here.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "supply_chain")
dbutils.widgets.text("volume", "raw")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
VOLUME = dbutils.widgets.get("volume")

spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.{VOLUME}")

AIS_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/ais/"
print("Reading AIS from", AIS_PATH)

# COMMAND ----------

# Raw ingest: keep every column as string, stamp provenance. Cleaning/validation
# happens in Silver (10_build_silver) so Bronze stays a faithful copy of source.
from pyspark.sql import functions as F

bronze = (
    spark.read.option("header", True).option("inferSchema", False).csv(AIS_PATH)
    .withColumn("_ingest_ts", F.current_timestamp())
    .withColumn("_source_file", F.input_file_name())
)

bronze.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.ais_raw")
print("ais_raw rows:", spark.table(f"{CATALOG}.{SCHEMA}.ais_raw").count())
