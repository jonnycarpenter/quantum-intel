#!/bin/bash
# ============================================================================
# Cloud Scheduler — Quantum + AI Intelligence Hub
# ============================================================================
# Creates Cloud Scheduler jobs to trigger Cloud Run Jobs on cadence.
#
# 19 Cloud Run Jobs, 19 Scheduler entries (all times UTC):
#
#   DAILY
#   06:00 daily     — Quantum RSS
#   07:00 daily     — AI RSS
#   13:00 daily     — Quantum Digest
#   13:30 daily     — AI Digest
#   22:00 Mon-Fri   — Stocks (after US market close)
#
#   TWICE WEEKLY (Tue & Fri)
#   08:00 Tue/Fri   — Quantum Exa web search
#   08:30 Tue/Fri   — AI Exa web search
#
#   WEEKLY
#   09:00 Sunday    — Quantum ArXiv papers
#   09:30 Sunday    — AI ArXiv papers
#   10:00 Sunday    — Quantum Podcasts
#   10:30 Sunday    — AI Podcasts
#   12:00 Monday    — AI weekly briefing
#   12:45 Monday    — Quantum weekly briefing
#
#   MONTHLY
#   11:00 1st/month — Quantum Earnings
#   11:30 1st/month — AI Earnings
#   11:00 2nd/month — Quantum SEC filings
#   11:30 2nd/month — AI SEC filings
#
#   WEEKLY (case studies — after source data ingested)
#   14:00 Sunday    — Quantum Case Studies
#   14:30 Sunday    — AI Case Studies
#
# Usage:
#   chmod +x deploy/setup_scheduler.sh
#   ./deploy/setup_scheduler.sh
# ============================================================================
set -euo pipefail

PROJECT_ID="gen-lang-client-0436975498"
REGION="us-central1"
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

BASE_URI="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs"

echo "=== Creating Cloud Scheduler jobs ==="

# Helper: create or update a scheduler job
create_schedule() {
  local NAME=$1
  local CRON=$2
  local JOB_NAME=$3

  echo "  ${NAME}: ${CRON} -> ${JOB_NAME}"
  gcloud scheduler jobs create http "${NAME}" \
    --schedule="${CRON}" \
    --uri="${BASE_URI}/${JOB_NAME}:run" \
    --http-method=POST \
    --location="${REGION}" \
    --oauth-service-account-email="${SA}" \
    --project="${PROJECT_ID}" \
    2>/dev/null || \
  gcloud scheduler jobs update http "${NAME}" \
    --schedule="${CRON}" \
    --uri="${BASE_URI}/${JOB_NAME}:run" \
    --http-method=POST \
    --location="${REGION}" \
    --oauth-service-account-email="${SA}" \
    --project="${PROJECT_ID}"
}

# Daily
create_schedule "quantum-rss-daily"       "0 6 * * *"     "quantum-rss-ingestion"
create_schedule "ai-rss-daily"            "0 7 * * *"     "ai-rss-ingestion"
create_schedule "quantum-stocks-daily"    "0 22 * * 1-5"  "quantum-stocks-ingestion"
create_schedule "quantum-digest-daily"    "0 13 * * *"    "quantum-digest"
create_schedule "ai-digest-daily"         "30 13 * * *"   "ai-digest"

# Twice weekly (Tue & Fri)
create_schedule "quantum-exa-biweekly"    "0 8 * * 2,5"   "quantum-exa-ingestion"
create_schedule "ai-exa-biweekly"         "30 8 * * 2,5"  "ai-exa-ingestion"

# Weekly
create_schedule "quantum-arxiv-weekly"    "0 9 * * 0"     "quantum-arxiv-ingestion"
create_schedule "ai-arxiv-weekly"         "30 9 * * 0"    "ai-arxiv-ingestion"
create_schedule "quantum-podcasts-weekly" "0 10 * * 0"    "quantum-podcasts"
create_schedule "ai-podcasts-weekly"      "30 10 * * 0"   "ai-podcasts"
create_schedule "ai-briefing-weekly"      "0 12 * * 1"    "ai-weekly-briefing"
create_schedule "quantum-briefing-weekly" "45 12 * * 1"   "quantum-weekly-briefing"

# Weekly (case studies — after other pipelines ingest source data)
create_schedule "quantum-case-studies-weekly" "0 14 * * 0"   "quantum-case-studies"
create_schedule "ai-case-studies-weekly"      "30 14 * * 0"  "ai-case-studies"

# Monthly
create_schedule "quantum-earnings-monthly" "0 11 1 * *"   "quantum-earnings"
create_schedule "ai-earnings-monthly"      "30 11 1 * *"  "ai-earnings"
create_schedule "quantum-sec-monthly"      "0 11 2 * *"   "quantum-sec"
create_schedule "ai-sec-monthly"           "30 11 2 * *"  "ai-sec"

echo ""
echo "=== All schedules created! ==="
echo ""
echo "View schedules:"
echo "  gcloud scheduler jobs list --location=${REGION} --project=${PROJECT_ID}"
echo ""
echo "Trigger manually:"
echo "  gcloud scheduler jobs run quantum-rss-daily --location=${REGION} --project=${PROJECT_ID}"
