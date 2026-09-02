# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Ingest Bronze (robust)
# MAGIC Reads the pre-uploaded NOAA AIS CSV(s) from the Volume into a raw Delta
# MAGIC table. It first prints the whole Volume tree and fails with a clear
# MAGIC message if the AIS file isn't in `raw/ais/`, so path mistakes are obvious
# MAGIC instead of surfacing as a cryptic schema error.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "supply_chain")
dbutils.widgets.text("volume", "raw")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
VOLUME = dbutils.widgets.get("volume")

# Idempotent: safe whether or not you already created these in the UI / SQL.
# (No CREATE CATALOG — `workspace` already exists in Free Edition.)
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.{VOLUME}")

VOL = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"
AIS_PATH = f"{VOL}/ais/"
print("Volume root:", VOL)
print("AIS path:   ", AIS_PATH)

# COMMAND ----------

# Show exactly what is in the Volume, so a misplaced file is easy to spot.
def _tree(path: str, indent: str = "") -> None:
    try:
        entries = dbutils.fs.ls(path)
    except Exception as e:  # noqa: BLE001 - surface any listing error inline
        print(f"{indent}(cannot list {path}: {str(e)[:90]})")
        return
    for f in entries:
        print(indent + f.name + ("/" if f.isDir() else ""))
        if f.isDir():
            _tree(f.path, indent + "  ")


print("Contents of", VOL)
_tree(VOL)

# COMMAND ----------

# Fail early with a clear message if the AIS CSV isn't where we read from.
csv_files: list[str] = []
try:
    csv_files = [f.path for f in dbutils.fs.ls(AIS_PATH) if f.name.lower().endswith(".csv")]
except Exception:  # noqa: BLE001 - folder may not exist yet
    pass

if not csv_files:
    raise Exception(  # noqa: TRY002
        f"No .csv found in {AIS_PATH}. Upload your AIS file there — e.g. "
        f"{AIS_PATH}ais_sample.csv. See the Volume tree printed above to find "
        f"where the file actually landed, then move it into the ais/ folder."
    )
print("AIS CSV files:", csv_files)

# COMMAND ----------

# Raw ingest: every column as string, stamp provenance. Reading only *.csv from
# ais/ avoids picking up weather.csv or ports.json. Cleaning/validation happens
# in Silver (10_build_silver), so Bronze stays a faithful copy of source.
from pyspark.sql import functions as F

bronze = (
    spark.read.option("header", True)
    .option("inferSchema", False)
    .option("pathGlobFilter", "*.csv")
    .csv(AIS_PATH)
    .withColumn("_ingest_ts", F.current_timestamp())
    .withColumn("_source_file", F.input_file_name())
)

bronze.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"{CATALOG}.{SCHEMA}.ais_raw"
)
print("ais_raw rows:", spark.table(f"{CATALOG}.{SCHEMA}.ais_raw").count())
display(spark.table(f"{CATALOG}.{SCHEMA}.ais_raw").limit(5))
