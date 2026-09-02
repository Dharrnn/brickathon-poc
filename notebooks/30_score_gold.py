# Databricks notebook source
# MAGIC %md
# MAGIC # 30 · Score Gold (disruption_risk)
# MAGIC Aggregate Silver per `(mmsi, port_zone)`, join worst-case weather, and
# MAGIC apply the shared rule-based `scdi.pipeline.build_gold`. Writes the Gold
# MAGIC `disruption_risk` table that the Metric View, dashboard and Genie sit on.

# COMMAND ----------

# MAGIC %pip install /Volumes/workspace/supply_chain/raw/wheels/scdi-0.1.0-py3-none-any.whl
# MAGIC # Adjust the path if you used a different catalog/schema/volume.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "supply_chain")
# Optional: path to a custom factors.yml on the Volume to re-tune the risk model
# WITHOUT changing code (e.g. /Volumes/workspace/supply_chain/raw/factors.yml).
dbutils.widgets.text("factors_config", "")
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
FACTORS_CONFIG = dbutils.widgets.get("factors_config").strip()

# COMMAND ----------

from scdi.factors import load_model
from scdi.pipeline import build_gold

model = load_model(FACTORS_CONFIG) if FACTORS_CONFIG else None  # None = packaged default

silver_pd = spark.table(f"{CATALOG}.{SCHEMA}.vessel_positions").toPandas()
weather_pd = spark.table(f"{CATALOG}.{SCHEMA}.weather_obs").toPandas()

gold_pd = build_gold(silver_pd, weather_pd, model=model)
print("gold rows:", len(gold_pd))

# COMMAND ----------

(
    spark.createDataFrame(gold_pd)
    .write.mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{CATALOG}.{SCHEMA}.disruption_risk")
)
display(spark.table(f"{CATALOG}.{SCHEMA}.disruption_risk").orderBy("delay_score", ascending=False))
