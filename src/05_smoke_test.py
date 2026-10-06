# Databricks notebook source
# MAGIC %md
# MAGIC # 05 - Smoke test
# MAGIC Known-answer SQL checks against the deployed demo. Fails the job if any check fails.

# COMMAND ----------

import re
import numpy as np

for name, default in [("catalog", ""), ("schema", "genie_ml_rag_demo")]:
    dbutils.widgets.text(name, default)
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
for value in (CATALOG, SCHEMA):
    assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value), value
NS = f"{CATALOG}.{SCHEMA}"
results = {}

# COMMAND ----------

# 1. Eligibility: 17 of 20 customers, C006/C007/C008 excluded
eligible = {r.customer_id for r in spark.sql(f"SELECT customer_id FROM {NS}.eligible_candidates").collect()}
assert len(eligible) == 17, len(eligible)
assert {"C006", "C007", "C008"}.isdisjoint(eligible)
results["eligible_customers"] = len(eligible)

# 2. Function returns zero rows for ineligible or unknown IDs
for customer_id in ("C006", "C007", "C008", "UNKNOWN"):
    n = spark.sql(f"SELECT * FROM {NS}.predict_response('{customer_id}')").count()
    assert n == 0, f"{customer_id} returned {n} rows"
results["zero_row_ids"] = "C006, C007, C008, UNKNOWN"

# 3. Live scores for C001-C005 match the offline fallback scores
live = spark.sql(" UNION ALL ".join(
    f"SELECT * FROM {NS}.predict_response('C00{i}')" for i in range(1, 6))).toPandas().set_index("customer_id")
fallback = spark.table(f"{NS}.fallback_scores").toPandas().set_index("customer_id")
assert len(live) == 5 and set(live.index) == set(fallback.index), (list(live.index), list(fallback.index))
for customer_id in live.index:
    np.testing.assert_allclose(live.loc[customer_id, "response_probability"],
                               fallback.loc[customer_id, "response_probability"], atol=1e-6)
results["live_matches_fallback"] = {k: round(float(v), 4) for k, v in
                                    live.response_probability.sort_values(ascending=False).items()}

# COMMAND ----------

# Summary
summary = {"model_version": fallback.model_version.iloc[0], **results}
for key, value in summary.items():
    print(f"{key}: {value}")
print("All smoke tests passed. Next: enable content search on the volume, open the Genie space in Agent mode.")
