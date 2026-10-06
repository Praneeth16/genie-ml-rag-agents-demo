# Databricks notebook source
# MAGIC %md
# MAGIC # 02 - Deploy the Model Serving endpoint
# MAGIC Creates the endpoint if missing, otherwise updates it to the model version behind the `workshop` alias.
# MAGIC Waits until it is READY, then checks that the REST response equals the local model (bare float).
# MAGIC
# MAGIC Cost note: `scale_to_zero=false` keeps the endpoint always on and billing. Use it for live demos only.

# COMMAND ----------

import re
import time
import numpy as np
import mlflow
from mlflow import MlflowClient
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound
from databricks.sdk.service.serving import EndpointCoreConfigInput

for name, default in [("catalog", ""), ("schema", "genie_ml_rag_demo"),
                      ("endpoint_name", "campaign-propensity-demo"), ("scale_to_zero", "true")]:
    dbutils.widgets.text(name, default)

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
ENDPOINT = dbutils.widgets.get("endpoint_name")
SCALE_TO_ZERO = dbutils.widgets.get("scale_to_zero").strip().lower() == "true"
assert re.fullmatch(r"[A-Za-z0-9_-]+", ENDPOINT), ENDPOINT

NS = f"{CATALOG}.{SCHEMA}"
MODEL_NAME = f"{NS}.response_propensity"
ALIAS = "workshop"
FEATURES = ["visits_30d", "email_clicks_30d", "days_since_last_engagement", "prior_webinars"]
TIMEOUT_S = 40 * 60

mlflow.set_registry_uri("databricks-uc")
VERSION = str(MlflowClient().get_model_version_by_alias(MODEL_NAME, ALIAS).version)
w = WorkspaceClient()
print({"endpoint": ENDPOINT, "model": MODEL_NAME, "version": VERSION, "scale_to_zero": SCALE_TO_ZERO})

# COMMAND ----------

# Create or update the endpoint


def wait_ready(timeout_s=TIMEOUT_S):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        state = w.serving_endpoints.get(ENDPOINT).state
        ready, update = str(state.ready), str(state.config_update)
        print(f"ready={ready} config_update={update}")
        assert "UPDATE_FAILED" not in update, "Endpoint update failed; check the serving UI logs"
        if "NOT_READY" not in ready and "READY" in ready and "NOT_UPDATING" in update:
            return
        time.sleep(30)
    raise TimeoutError(f"Endpoint {ENDPOINT} not READY after {timeout_s // 60} minutes")


config = EndpointCoreConfigInput.from_dict({
    "served_entities": [{
        "entity_name": MODEL_NAME, "entity_version": VERSION,
        "workload_type": "CPU", "workload_size": "Small",
        "scale_to_zero_enabled": SCALE_TO_ZERO,
    }]
})

try:
    w.serving_endpoints.get(ENDPOINT)
except NotFound:
    print(f"Creating endpoint {ENDPOINT}")
    w.serving_endpoints.create(name=ENDPOINT, config=config)
else:
    wait_ready()  # an in-flight update would reject a new one
    current = w.serving_endpoints.get(ENDPOINT).config.served_entities[0]
    if (current.entity_name, str(current.entity_version), current.scale_to_zero_enabled) == (
            MODEL_NAME, VERSION, SCALE_TO_ZERO):
        print("Endpoint already serves this version with these settings")
    else:
        print(f"Updating endpoint {ENDPOINT} to version {VERSION}")
        w.serving_endpoints.update_config(name=ENDPOINT, served_entities=config.served_entities)

time.sleep(10)  # let the create/update register before polling
wait_ready()

# COMMAND ----------

# REST parity: endpoint response for C001 must equal the local model and be a bare float
record = (spark.table(f"{NS}.customer_features").where("customer_id = 'C001'")
          .select(*FEATURES).toPandas().astype("float64"))
local = float(mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}@{ALIAS}").predict(record)[0])

response = None
for attempt in range(1, 21):  # a scaled-to-zero endpoint needs a cold start on the first call
    try:
        response = w.api_client.do("POST", f"/serving-endpoints/{ENDPOINT}/invocations",
                                   body={"dataframe_records": record.to_dict(orient="records")})
        break
    except Exception as exc:
        print(f"attempt {attempt}: {str(exc)[:160]}")
        time.sleep(30)
assert response is not None, "Endpoint did not answer in time"

remote = response["predictions"][0]
assert isinstance(remote, float), f"Expected a bare float prediction, got {remote!r}"
np.testing.assert_allclose(remote, local, atol=1e-6)
print({"endpoint_score_C001": remote, "local_score_C001": local, "response": response})
