# GCP Deployment Guide

Production deployment of the Quantum + AI Intelligence Hub on Google Cloud Platform.

## Architecture

```
GitHub (jonnycarpenter/quantum-intel)
    ↓ push to master
Cloud Build (cloudbuild.yaml)
    ↓ builds Docker image → updates Cloud Run Jobs
Cloud Scheduler (cron)
    ↓ triggers
Cloud Run Jobs (17 jobs)
    ↓ reads/writes
BigQuery (quantum_ai_hub dataset, 17 tables)
    ↓ embeddings
Vertex AI text-embedding-005 → BigQuery VECTOR_SEARCH
```

**BigQuery-only:** All development and production uses BigQuery + Vertex AI. `GCP_PROJECT_ID` is required.

## CI/CD Pipeline

Every push to `master` triggers Cloud Build via a Developer Connect GitHub trigger:

1. Builds slim Docker image (production deps only — no PyTorch/CUDA/ChromaDB/Streamlit)
2. Pushes to Artifact Registry with `$SHORT_SHA` and `latest` tags
3. Updates all 17 Cloud Run Jobs to use the new image

Config: `cloudbuild.yaml` at project root.

## Deploying changes

After initial setup, deploying is just a git push:

```bash
git add -A && git commit -m "your change" && git push origin master
```

Cloud Build triggers automatically, builds the slim image, and updates all jobs.

## Prerequisites

- Google Cloud SDK (`gcloud`) installed and authenticated
- Billing enabled on the GCP project
- `gcloud auth application-default login` (for local testing with BigQuery)

## First-Time Setup

```bash
# 1. One-time infrastructure setup
chmod +x deploy/setup_infra.sh
./deploy/setup_infra.sh

# 2. Populate secrets
echo -n "sk-ant-..." | gcloud secrets versions add anthropic-api-key --data-file=- --project=gen-lang-client-0436975498
echo -n "exa-..."    | gcloud secrets versions add EXA_API_KEY       --data-file=- --project=gen-lang-client-0436975498
# Repeat for: api-ninja-key, assemblyai-api-key

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
| BigQuery Dataset | `quantum_ai_hub` | 17 tables for all pipeline data |
| Artifact Registry | `quantum-intel` | Docker images |
| Cloud Build Trigger | `quantum-intel-deploy` | GitHub push → build → deploy |
| GCS Bucket | `quantum-ai-hub-data` | Future file storage |
| Secret Manager | 4 secrets | API keys (anthropic, exa, api-ninja, assemblyai) |
| Cloud Run Jobs | 17 jobs | Pipeline execution (quantum + AI) |
| Cloud Scheduler | 17 schedules | Cron triggers |

## Environment Variables

### Required for GCP mode
| Variable | Value |
|----------|-------|
| `GCP_PROJECT_ID` | `gen-lang-client-0436975498` |
| `GCP_REGION` | `us-central1` |
| `BQ_DATASET_ID` | `quantum_ai_hub` |

## Pipeline Schedules (17 jobs, all times UTC)

### Daily
| Pipeline | UTC Time | Cloud Run Job |
|----------|----------|---------------|
| Quantum RSS | 06:00 | `quantum-rss-ingestion` |
| AI RSS | 07:00 | `ai-rss-ingestion` |
| Quantum Digest | 13:00 | `quantum-digest` |
| AI Digest | 13:30 | `ai-digest` |
| Stocks | 22:00 Mon-Fri | `quantum-stocks-ingestion` |

### Twice Weekly (Tue & Fri)
| Pipeline | UTC Time | Cloud Run Job |
|----------|----------|---------------|
| Quantum Exa Search | 08:00 | `quantum-exa-ingestion` |
| AI Exa Search | 08:30 | `ai-exa-ingestion` |

### Weekly
| Pipeline | UTC Time | Cloud Run Job |
|----------|----------|---------------|
| Quantum ArXiv | Sunday 09:00 | `quantum-arxiv-ingestion` |
| AI ArXiv | Sunday 09:30 | `ai-arxiv-ingestion` |
| Quantum Podcasts | Sunday 10:00 | `quantum-podcasts` |
| AI Podcasts | Sunday 10:30 | `ai-podcasts` |
| AI Weekly Briefing | Monday 12:00 | `ai-weekly-briefing` |
| Quantum Weekly Briefing | Monday 12:45 | `quantum-weekly-briefing` |

### Monthly
| Pipeline | UTC Time | Cloud Run Job |
|----------|----------|---------------|
| Quantum Earnings | 1st 11:00 | `quantum-earnings` |
| AI Earnings | 1st 11:30 | `ai-earnings` |
| Quantum SEC Filings | 2nd 11:00 | `quantum-sec` |
| AI SEC Filings | 2nd 11:30 | `ai-sec` |

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

All development uses BigQuery. Requires `gcloud auth application-default login`:

```bash
pip install -r requirements-local.txt

# Run locally against BigQuery
python scripts/run_ingestion.py --sources rss --max-classify 5

# Test a specific domain
python scripts/run_ingestion.py --domain ai --sources exa --max-classify 3
```

## Troubleshooting

**"BigQuery: 403 Access Denied"** — Run `gcloud auth application-default login` or check IAM roles.

**"Vertex AI: Model not found"** — Ensure the Vertex AI API is enabled and the region supports `text-embedding-005`.

**Cloud Run Job fails immediately** — Check logs: `gcloud run jobs executions describe EXECUTION_ID --region=us-central1`. Common cause: missing secret.

**Scheduler not triggering** — Verify the service account has `roles/run.invoker` on the Cloud Run jobs.
