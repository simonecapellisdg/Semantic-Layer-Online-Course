
import requests
import json
import os
import sys

# ── Config from environment variables ──────────────────────────────────────
STG_TOKEN       = os.environ["DBT_STG_TOKEN"]
PRD_TOKEN       = os.environ["DBT_PRD_TOKEN"]
STG_ACCOUNT_ID  = os.environ["DBT_STG_ACCOUNT_ID"]
PRD_ACCOUNT_ID  = os.environ["DBT_PRD_ACCOUNT_ID"]
STG_JOB_ID      = os.environ["DBT_STG_JOB_ID"]
PRD_ENV_ID      = os.environ["DBT_PRD_ENV_ID"]
PRD_JOB_ID      = os.environ.get("DBT_PRD_JOB_ID")  # Optional: if updating existing job

BASE_URL = "https://xe054.us1.dbt.com/api/v2"

STG_HEADERS = {"Authorization": f"Token {STG_TOKEN}", "Content-Type": "application/json"}
PRD_HEADERS = {"Authorization": f"Token {PRD_TOKEN}", "Content-Type": "application/json"}

# ── 1. Fetch job from STG ──────────────────────────────────────────────────
def get_stg_job():
    url = f"{BASE_URL}/accounts/{STG_ACCOUNT_ID}/jobs/{STG_JOB_ID}/"
    resp = requests.get(url, headers=STG_HEADERS)
    resp.raise_for_status()
    return resp.json()["data"]

# ── 2. Transform payload for PRD ───────────────────────────────────────────
def transform_payload(job: dict) -> dict:
    # Fields to strip (auto-managed by dbt Cloud)
    STRIP_FIELDS = ["id", "created_at", "updated_at", "account_id",
                    "state", "dbt_version_latest", "job_completion_trigger_condition"]

    payload = {k: v for k, v in job.items() if k not in STRIP_FIELDS}

    # Remap to PRD environment and account
    payload["environment_id"] = int(PRD_ENV_ID)
    payload["account_id"]     = int(PRD_ACCOUNT_ID)

    # Tag it so you know it was promoted
    payload["name"] = job["name"]  # Keep same name, or append " [PRD]" if preferred

    return payload

# ── 3a. Create new job in PRD ──────────────────────────────────────────────
def create_prd_job(payload: dict):
    url = f"{BASE_URL}/accounts/{PRD_ACCOUNT_ID}/jobs/"
    resp = requests.post(url, headers=PRD_HEADERS, json=payload)
    resp.raise_for_status()
    job = resp.json()["data"]
    print(f"✅ Created PRD job: ID={job['id']} | Name={job['name']}")
    return job

# ── 3b. Update existing job in PRD ────────────────────────────────────────
def update_prd_job(payload: dict):
    url = f"{BASE_URL}/accounts/{PRD_ACCOUNT_ID}/jobs/{PRD_JOB_ID}/"
    resp = requests.post(url, headers=PRD_HEADERS, json=payload)  # dbt uses POST for update too
    resp.raise_for_status()
    job = resp.json()["data"]
    print(f"✅ Updated PRD job: ID={job['id']} | Name={job['name']}")
    return job

# ── Main ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("📥 Fetching STG job...")
    stg_job = get_stg_job()
    print(json.dumps(stg_job, indent=2))  # Visible in pipeline logs for audit

    print("🔄 Transforming payload for PRD...")
    payload = transform_payload(stg_job)

    if PRD_JOB_ID:
        print(f"♻️  Updating existing PRD job {PRD_JOB_ID}...")
        update_prd_job(payload)
    else:
        print("🆕 Creating new job in PRD...")
        create_prd_job(payload)
