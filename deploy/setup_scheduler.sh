#!/bin/bash
# ============================================================================
# Cloud Scheduler — Quantum + AI Intelligence Hub
# ============================================================================
# Creates Cloud Scheduler jobs to trigger Cloud Run Jobs on cadence.
#
# Schedule (all times UTC):
#   06:00 daily     — Quantum RSS
#   07:00 daily     — AI RSS
#   08:00 Tue/Fri   — Exa web search
#   09:00 Sunday    — ArXiv papers
#   10:00 Sunday    — Podcasts
#   11:00 1st/month — Earnings transcripts
#   11:00 2nd/month — SEC filings
#   12:00 Monday    — AI weekly briefing
#   12:45 Monday    — Quantum weekly briefing
#   13:00 daily     — Digest (after RSS completes)
#   22:00 Mon-Fri   — Stocks (after US market close)
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

# Twice weekly (Tue & Fri)
create_schedule "quantum-exa-biweekly" "0 8 * * 2,5" "quantum-exa-ingestion"

# Weekly
create_schedule "quantum-arxiv-weekly"    "0 9 * * 0"   "quantum-arxiv-ingestion"
create_schedule "quantum-podcasts-weekly" "0 10 * * 0"  "quantum-podcasts"
create_schedule "ai-briefing-weekly"      "0 12 * * 1"  "ai-weekly-briefing"
create_schedule "quantum-briefing-weekly" "45 12 * * 1" "quantum-weekly-briefing"

# Monthly
create_schedule "quantum-earnings-monthly" "0 11 1 * *"  "quantum-earnings"
create_schedule "quantum-sec-monthly"      "0 11 2 * *"  "quantum-sec"

echo ""
echo "=== All schedules created! ==="
echo ""
echo "View schedules:"
echo "  gcloud scheduler jobs list --location=${REGION} --project=${PROJECT_ID}"
echo ""
echo "Trigger manually:"
echo "  gcloud scheduler jobs run quantum-rss-daily --location=${REGION} --project=${PROJECT_ID}"
