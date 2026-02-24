# GCP Deployment Guide

Production deployment of the Quantum + AI Intelligence Hub on Google Cloud Platform.

## Architecture

```
Cloud Scheduler (cron)
    ↓ triggers
Cloud Run Jobs (9 jobs)
    ↓ reads/writes
BigQuery (quantum_ai_hub dataset, 12 tables)
    ↓ embeddings
Vertex AI text-embedding-005 → BigQuery VECTOR_SEARCH
```

**Local path preserved:** Set `STORAGE_BACKEND=sqlite` (or omit `GCP_PROJECT_ID`) to keep using SQLite + ChromaDB locally.

## Prerequisites

- Google Cloud SDK (`gcloud`) installed and authenticated
- Billing enabled on the GCP project
- `gcloud auth application-default login` (for local testing with BigQuery)

## Quick Start

```bash
# 1. One-time infrastructure setup
chmod +x deploy/setup_infra.sh
./deploy/setup_infra.sh

# 2. Populate secrets
echo -n "sk-ant-..." | gcloud secrets versions add anthropic-api-key --data-file=- --project=gen-lang-client-0436975498
echo -n "tvly-..."   | gcloud secrets versions add tavily-api-key    --data-file=- --project=gen-lang-client-0436975498
# Repeat for: api-ninja-key, secio-api-key, assemblyai-api-key, stocknews-api-key

# 3. Build image and create Cloud Run Jobs
chmod +x deploy/cloud_run_jobs.sh
./deploy/cloud_run_jobs.sh

# 4. Create scheduled triggers
chmod +x deploy/setup_scheduler.sh
./deploy/setup_scheduler.sh

# 5. Test a job
gcloud run jobs execute quantum-rss-ingestion --region us-central1
```

## GCP Resources

| Resource | Name | Purpose |
|----------|------|---------|
| BigQuery Dataset | `quantum_ai_hub` | 12 tables for all pipeline data |
| Artifact Registry | `quantum-intel` | Docker images |
| GCS Bucket | `quantum-ai-hub-data` | Future file storage |
| Secret Manager | 6 secrets | API keys |
| Cloud Run Jobs | 9 jobs | Pipeline execution |
| Cloud Scheduler | 9 schedules | Cron triggers |

## Environment Variables

### Required for GCP mode
| Variable | Value |
|----------|-------|
| `GCP_PROJECT_ID` | `gen-lang-client-0436975498` |
| `GCP_REGION` | `us-central1` |
| `BQ_DATASET_ID` | `quantum_ai_hub` |

### Optional overrides
| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_BACKEND` | `auto` | Force `sqlite` or `bigquery` |
| `EMBEDDINGS_BACKEND` | `auto` | Force `chromadb` or `vertex` |

## Pipeline Schedules

| Pipeline | Cadence | UTC Time | Cloud Run Job |
|----------|---------|----------|---------------|
| Quantum RSS | Daily | 06:00 | `quantum-rss-ingestion` |
| AI RSS | Daily | 07:00 | `ai-rss-ingestion` |
| Tavily Search | Tue & Fri | 08:00 | `quantum-tavily-ingestion` |
| ArXiv Papers | Sunday | 09:00 | `quantum-arxiv-ingestion` |
| Podcasts | Sunday | 10:00 | `quantum-podcasts` |
| Earnings | 1st of month | 11:00 | `quantum-earnings` |
| SEC Filings | 2nd of month | 11:00 | `quantum-sec` |
| Weekly Briefing | Monday | 12:00 | `quantum-weekly-briefing` |
| Digest | Daily | 13:00 | `quantum-digest` |

## Monitoring

```bash
# View Cloud Run Job logs
gcloud run jobs executions list --job=quantum-rss-ingestion --region=us-central1

# View latest execution logs
gcloud logging read 'resource.type="cloud_run_job" resource.labels.job_name="quantum-rss-ingestion"' \
  --limit=50 --project=gen-lang-client-0436975498

# Check scheduler status
gcloud scheduler jobs list --location=us-central1

# Query BigQuery directly
bq query --project_id=gen-lang-client-0436975498 \
  'SELECT COUNT(*) as total, domain FROM quantum_ai_hub.articles GROUP BY domain'
```

## Cost Estimate (monthly)

| Service | Estimate |
|---------|----------|
| BigQuery (on-demand) | < $5 |
| Vertex AI Embeddings | < $2 |
| Cloud Run Jobs | < $5 |
| Cloud Scheduler | Free tier |
| Secret Manager | Free tier |
| **Total** | **~$10-15** |

## Local Development

The local SQLite path is unchanged. If `GCP_PROJECT_ID` is not set, everything runs locally:

```bash
# Local mode (default)
python scripts/run_ingestion.py --sources rss --max-classify 5

# Force BigQuery locally (requires gcloud auth)
GCP_PROJECT_ID=gen-lang-client-0436975498 python scripts/run_ingestion.py --sources rss --max-classify 3
```

## Troubleshooting

**"BigQuery: 403 Access Denied"** — Run `gcloud auth application-default login` or check IAM roles.

**"Vertex AI: Model not found"** — Ensure the Vertex AI API is enabled and the region supports `text-embedding-005`.

**Cloud Run Job fails immediately** — Check logs: `gcloud run jobs executions describe EXECUTION_ID --region=us-central1`. Common cause: missing secret.

**Scheduler not triggering** — Verify the service account has `roles/run.invoker` on the Cloud Run jobs.
