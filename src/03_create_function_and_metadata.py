# Databricks notebook source
# MAGIC %md
# MAGIC # 03 - SQL function and table metadata
# MAGIC 1. `predict_response(customer_id)`: a Unity Catalog SQL table function that calls the serving endpoint with `ai_query`.
# MAGIC 2. Table comments, NOT NULL and informational primary/foreign keys so Genie One can find and join the assets.
# MAGIC
# MAGIC Idempotent: the function is replaced, constraints are dropped and recreated.

# COMMAND ----------

import re
import time

for name, default in [("catalog", ""), ("schema", "genie_ml_rag_demo"),
                      ("endpoint_name", "campaign-propensity-demo")]:
    dbutils.widgets.text(name, default)

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
ENDPOINT = dbutils.widgets.get("endpoint_name")
for value in (CATALOG, SCHEMA):
    assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value), value
assert re.fullmatch(r"[A-Za-z0-9_-]+", ENDPOINT), ENDPOINT
NS = f"{CATALOG}.{SCHEMA}"

# COMMAND ----------

# SQL function the Genie Agent calls
spark.sql(f"""
CREATE OR REPLACE FUNCTION {NS}.predict_response(p_customer_id STRING)
RETURNS TABLE (customer_id STRING, response_probability DOUBLE)
NOT DETERMINISTIC
COMMENT 'Synthetic CMP001 demo inference for C001-C005 only. Returns zero rows for unknown, ineligible or out-of-demo IDs. Probability is an estimate, not permission to contact the customer. Do not use for bulk scoring.'
RETURN
SELECT e.customer_id,
       ai_query(
         '{ENDPOINT}',
         named_struct(
           'visits_30d', e.visits_30d,
           'email_clicks_30d', e.email_clicks_30d,
           'days_since_last_engagement', e.days_since_last_engagement,
           'prior_webinars', e.prior_webinars
         ),
         returnType => 'DOUBLE'
       ) AS response_probability
FROM {NS}.eligible_candidates e
WHERE e.customer_id = p_customer_id
  AND e.campaign_id = 'CMP001'
  AND e.customer_id IN ('C001','C002','C003','C004','C005')
""")

# Smoke test through ai_query. A scaled-to-zero endpoint may need a cold start, so retry.
for attempt in range(1, 21):
    try:
        row = spark.sql(f"SELECT * FROM {NS}.predict_response('C001')").collect()
        break
    except Exception as exc:
        print(f"attempt {attempt}: {str(exc)[:160]}")
        time.sleep(30)
else:
    raise RuntimeError("predict_response('C001') did not succeed in time")
assert len(row) == 1 and 0.0 < row[0].response_probability < 1.0, row
print("predict_response('C001') ->", row[0].response_probability)

# COMMAND ----------

# Ontology metadata: comments, NOT NULL, informational PK/FK
fallback_version = spark.table(f"{NS}.fallback_scores").select("model_version").first()[0]

COMMENTS = {
    "training_history": "Past campaign history: outcomes of the September 2026 email campaign (synthetic, 3000 past customers with IDs like H01000). responded_14d = 1 if the customer registered within 14 days. Used to train the response_propensity model; also the source for descriptive questions about how past customers responded.",
    "customers": "Entity: Customer. 20 fictional current customers (C001-C020) for the CMP001 webinar demo, with segment (SMB, Midmarket, Enterprise) and region.",
    "campaigns": "Entity: Campaign. The one fictional campaign CMP001 (Fictional Analytics Webinar, APAC email, start 2026-10-06).",
    "customer_features": "Entity: Customer engagement features (visits_30d, email_clicks_30d, days_since_last_engagement, prior_webinars) as of 2026-10-05. One row per customer; same features the response_propensity model uses.",
    "customer_consent": "Entity: Consent. Email consent per customer: email_opt_in and suppressed flags. A customer with no row here has no consent record and is not eligible.",
    "fallback_scores": f"Offline precomputed fallback scores from response_propensity model version {fallback_version} (same version as the live endpoint {ENDPOINT}), for C001-C005. Used if live scoring is unavailable; not live inference.",
}
for table, comment in COMMENTS.items():
    spark.sql(f"COMMENT ON TABLE {NS}.{table} IS '{comment}'")

KEYS = {"customers": "customer_id", "campaigns": "campaign_id",
        "customer_features": "customer_id", "customer_consent": "customer_id",
        "fallback_scores": "customer_id"}
FOREIGN_KEYS = {"customer_features": "features_customer_fk",
                "customer_consent": "consent_customer_fk",
                "fallback_scores": "fallback_customer_fk"}

# Drop foreign keys first, then primary keys, so re-runs never collide
for table, constraint in FOREIGN_KEYS.items():
    spark.sql(f"ALTER TABLE {NS}.{table} DROP CONSTRAINT IF EXISTS {constraint}")
for table in KEYS:
    spark.sql(f"ALTER TABLE {NS}.{table} DROP CONSTRAINT IF EXISTS {table}_pk")

for table, column in KEYS.items():
    spark.sql(f"ALTER TABLE {NS}.{table} ALTER COLUMN {column} SET NOT NULL")
    spark.sql(f"ALTER TABLE {NS}.{table} ADD CONSTRAINT {table}_pk PRIMARY KEY ({column})")
for table, constraint in FOREIGN_KEYS.items():
    spark.sql(f"ALTER TABLE {NS}.{table} ADD CONSTRAINT {constraint} "
              f"FOREIGN KEY (customer_id) REFERENCES {NS}.customers(customer_id)")
print("Function and metadata ready")
