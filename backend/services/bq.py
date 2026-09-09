"""
BigQuery as the HIE system of record (phase 2).

  load_tables()          read the 8 HIE tables from `<project>.<dataset>` into DataFrames
  upload_local_tables()  first-boot provisioning: push the csv.gz tables into BigQuery
  query()                read-only GoogleSQL for the cohort agent (guarded, capped, costed)

Nothing here is imported unless HIE_BACKEND=bigquery, so phase 1 never needs the client.
"""
from __future__ import annotations

import re
import threading
import time
from pathlib import Path

import pandas as pd

from services import platform as P

TABLES = ["facilities", "patients", "conditions", "observations",
          "medications", "encounters", "care_gaps", "patient_summary"]
DATA = Path(__file__).resolve().parent.parent / "data" / "hie"

STATUS: dict = {"backend": P.HIE_BACKEND, "project": P.PROJECT or None, "dataset": P.BQ_DATASET,
                "location": P.BQ_LOCATION, "loaded_from": None, "rows": {}, "load_ms": None,
                "provisioning": False, "provisioned_at": None, "error": None}

_client = None
_lock = threading.Lock()


def client():
    global _client
    if _client is None:
        from google.cloud import bigquery
        _client = bigquery.Client(project=P.PROJECT or None, location=P.BQ_LOCATION)
    return _client


def fq(table: str) -> str:
    return f"`{P.PROJECT}.{P.BQ_DATASET}.{table}`"


def table_rows() -> dict[str, int]:
    """Row counts from dataset metadata (free, no scan); empty dict if the dataset is missing."""
    sql = f"SELECT table_id, row_count FROM `{P.PROJECT}.{P.BQ_DATASET}.__TABLES__`"
    rows = client().query(sql).result()
    return {r.table_id: int(r.row_count) for r in rows}


def load_tables() -> dict[str, pd.DataFrame]:
    """Read every HIE table from BigQuery. Raises if any table is missing so the caller can
    fall back to the local files and start provisioning."""
    t0 = time.time()
    counts = table_rows()
    missing = [n for n in TABLES if counts.get(n, 0) == 0]
    if missing:
        raise LookupError(f"BigQuery dataset {P.BQ_DATASET} is missing tables: {missing}")
    out = {}
    for name in TABLES:
        out[name] = client().query(f"SELECT * FROM {fq(name)}").result().to_dataframe()
    STATUS.update(loaded_from="bigquery", rows={n: len(df) for n, df in out.items()},
                  load_ms=int((time.time() - t0) * 1000), error=None)
    return out


def upload_local_tables(overwrite: bool = True) -> dict[str, int]:
    """Provision the dataset from the committed csv.gz files (first boot on Google Cloud)."""
    from google.cloud import bigquery
    with _lock:
        STATUS["provisioning"] = True
        try:
            ds_id = f"{P.PROJECT}.{P.BQ_DATASET}"
            try:
                client().get_dataset(ds_id)
            except Exception:
                ds = bigquery.Dataset(ds_id)
                ds.location = P.BQ_LOCATION
                ds.description = "Nabd synthetic Qatar HIE — 8 relational tables, 36 months, zero PHI"
                client().create_dataset(ds, exists_ok=True)
            loaded = {}
            for name in TABLES:
                df = pd.read_csv(DATA / f"{name}.csv.gz")
                for col in df.columns:            # dates travel as strings in the csv; keep them typed
                    if col.endswith("_date") or col in ("date", "start", "end", "obs_date", "dob"):
                        try:
                            df[col] = pd.to_datetime(df[col]).dt.date
                        except Exception:
                            pass
                job = client().load_table_from_dataframe(
                    df, f"{ds_id}.{name}",
                    job_config=bigquery.LoadJobConfig(
                        write_disposition="WRITE_TRUNCATE" if overwrite else "WRITE_APPEND"))
                job.result()
                loaded[name] = len(df)
            STATUS.update(provisioned_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                          rows=loaded, error=None)
            return loaded
        except Exception as e:
            STATUS["error"] = f"provisioning failed: {type(e).__name__}: {str(e)[:300]}"
            raise
        finally:
            STATUS["provisioning"] = False


def provision_in_background():
    def work():
        try:
            n = upload_local_tables()
            print(f"✓ BigQuery provisioned {P.PROJECT}.{P.BQ_DATASET}: "
                  + ", ".join(f"{k}={v:,}" for k, v in n.items()), flush=True)
        except Exception as e:
            print(f"✗ BigQuery provisioning failed: {e}", flush=True)
    threading.Thread(target=work, name="nabd-bq-provision", daemon=True).start()


# ─────────────────────────── guarded read-only SQL for the agent ───────────────────────────
_FORBIDDEN = re.compile(r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|CREATE|ALTER|TRUNCATE|GRANT|REVOKE|CALL|EXPORT|LOAD|BEGIN|COMMIT|DECLARE|SET)\b", re.I)
MAX_BYTES = 2 * 1024 ** 3     # 2 GiB per query — the whole dataset is ~50 MB


def query(sql: str, max_rows: int = 200) -> dict:
    """Run one read-only SELECT against the HIE dataset. Returns rows, schema and job stats."""
    from google.cloud import bigquery
    s = re.sub(r"--[^\n]*", "", sql or "").strip().rstrip(";").strip()
    if not re.match(r"^(SELECT|WITH)\b", s, re.I):
        return {"error": "only SELECT / WITH queries are allowed"}
    if _FORBIDDEN.search(s) or ";" in s:
        return {"error": "statement contains a forbidden keyword or multiple statements"}
    if not re.search(r"\bLIMIT\s+\d+", s, re.I):
        s = f"{s}\nLIMIT {max_rows}"
    cfg = bigquery.QueryJobConfig(
        default_dataset=f"{P.PROJECT}.{P.BQ_DATASET}", maximum_bytes_billed=MAX_BYTES,
        use_query_cache=True, labels={"app": "nabd", "caller": "cohort_agent"})
    t0 = time.time()
    try:
        job = client().query(s, job_config=cfg)
        rows = [dict(r) for r in job.result(max_results=max_rows)]
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:400]}", "sql": s}
    for r in rows:                                   # JSON-safe
        for k, v in list(r.items()):
            if hasattr(v, "isoformat"):
                r[k] = v.isoformat()
            elif hasattr(v, "item"):
                r[k] = v.item()
    return {"rows": rows, "row_count": len(rows),
            "columns": [f.name for f in job.result().schema] if rows else [],
            "bytes_processed": int(job.total_bytes_processed or 0),
            "cache_hit": bool(job.cache_hit), "ms": int((time.time() - t0) * 1000),
            "job_id": job.job_id, "location": job.location,
            "dataset": f"{P.PROJECT}.{P.BQ_DATASET}", "sql": s}
