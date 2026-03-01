#!/bin/bash
# ============================================================================
# Cloud Run Jobs — Quantum + AI Intelligence Hub
# ============================================================================
# Creates (or updates) all Cloud Run Jobs.
# Builds and pushes the Docker image via Cloud Build first.
#
# Usage:
#   chmod +x deploy/cloud_run_jobs.sh
#   ./deploy/cloud_run_jobs.sh
# ============================================================================
set -euo pipefail

PROJECT_ID="gen-lang-client-0436975498"
REGION="us-central1"
IMAGE="us-central1-docker.pkg.dev/${PROJECT_ID}/quantum-intel/quantum-intel:latest"

COMMON_ENV="GCP_PROJECT_ID=${PROJECT_ID},BQ_DATASET_ID=quantum_ai_hub,GCP_REGION=${REGION}"

echo "=== Building and pushing Docker image ==="
gcloud builds submit \
  --tag "${IMAGE}" \
  --project "${PROJECT_ID}" \
  --timeout=600

echo ""
echo "=== Creating Cloud Run Jobs ==="

# Helper: create or update a job
create_job() {
  local JOB_NAME=$1
  local ARGS=$2
  local SECRETS=$3
  local EXTRA_ENV=${4:-""}
  local MEMORY=${5:-"2Gi"}
  local CPU=${6:-"1"}
  local TIMEOUT=${7:-"1800"}

  local ENV_VARS="${COMMON_ENV}"
  if [ -n "${EXTRA_ENV}" ]; then
    ENV_VARS="${ENV_VARS},${EXTRA_ENV}"
  fi

  echo "Creating job: ${JOB_NAME}"
  gcloud run jobs create "${JOB_NAME}" \
    --image "${IMAGE}" \
    --args "${ARGS}" \
    --region "${REGION}" \
    --project "${PROJECT_ID}" \
    --set-secrets "${SECRETS}" \
    --set-env-vars "${ENV_VARS}" \
    --task-timeout "${TIMEOUT}" \
    --max-retries 1 \
    --memory "${MEMORY}" \
    --cpu "${CPU}" \
    2>/dev/null || \
  gcloud run jobs update "${JOB_NAME}" \
    --image "${IMAGE}" \
    --args "${ARGS}" \
    --region "${REGION}" \
    --project "${PROJECT_ID}" \
    --set-secrets "${SECRETS}" \
    --set-env-vars "${ENV_VARS}" \
    --task-timeout "${TIMEOUT}" \
    --max-retries 1 \
    --memory "${MEMORY}" \
    --cpu "${CPU}"
}

# --- Quantum RSS (daily) ---
create_job "quantum-rss-ingestion" \
  "scripts/run_ingestion.py,--sources,rss,--domain,quantum" \
  "ANTHROPIC_API_KEY=anthropic-api-key:latest"

# --- AI RSS (daily) ---
create_job "ai-rss-ingestion" \
  "scripts/run_ingestion.py,--sources,rss,--domain,ai" \
  "ANTHROPIC_API_KEY=anthropic-api-key:latest"

# --- Quantum Exa (twice weekly) ---
create_job "quantum-exa-ingestion" \
  "scripts/run_ingestion.py,--sources,exa,--domain,quantum" \
  "ANTHROPIC_API_KEY=anthropic-api-key:latest,EXA_API_KEY=EXA_API_KEY:latest" \
  "" "2Gi" "1" "3600"

# --- AI Exa (twice weekly) ---
create_job "ai-exa-ingestion" \
  "scripts/run_ingestion.py,--sources,exa,--domain,ai" \
  "ANTHROPIC_API_KEY=anthropic-api-key:latest,EXA_API_KEY=EXA_API_KEY:latest" \
  "" "2Gi" "1" "7200"

# --- Quantum ArXiv (weekly) ---
create_job "quantum-arxiv-ingestion" \
  "scripts/run_ingestion.py,--sources,arxiv,--domain,quantum" \
  "ANTHROPIC_API_KEY=anthropic-api-key:latest" \
  "" "2Gi" "1" "3600"

# --- AI ArXiv (weekly) ---
create_job "ai-arxiv-ingestion" \
  "scripts/run_ingestion.py,--sources,arxiv,--domain,ai" \
  "ANTHROPIC_API_KEY=anthropic-api-key:latest" \
  "" "2Gi" "1" "3600"

# --- Quantum Earnings (monthly) ---
create_job "quantum-earnings" \
  "scripts/run_earnings.py,--domain,quantum" \
  "ANTHROPIC_API_KEY=anthropic-api-key:latest,API_NINJA_API_KEY=api-ninja-key:latest" \
  "" "4Gi" "2" "3600"

# --- AI Earnings (monthly) ---
create_job "ai-earnings" \
  "scripts/run_earnings.py,--domain,ai" \
  "ANTHROPIC_API_KEY=anthropic-api-key:latest,API_NINJA_API_KEY=api-ninja-key:latest" \
  "" "4Gi" "2" "3600"

# --- Quantum SEC (monthly) ---
create_job "quantum-sec" \
  "scripts/run_sec.py,--domain,quantum" \
  "ANTHROPIC_API_KEY=anthropic-api-key:latest" \
  "SEC_USER_AGENT=QuantumIntelHub admin@example.com" "4Gi" "2" "3600"

# --- AI SEC (monthly) ---
create_job "ai-sec" \
  "scripts/run_sec.py,--domain,ai" \
  "ANTHROPIC_API_KEY=anthropic-api-key:latest" \
  "SEC_USER_AGENT=QuantumIntelHub admin@example.com" "4Gi" "2" "3600"

# --- Podcasts (weekly) ---
create_job "quantum-podcasts" \
  "scripts/run_podcast.py" \
  "ANTHROPIC_API_KEY=anthropic-api-key:latest,ASSEMBLYAI_API_KEY=assemblyai-api-key:latest" \
  "" "4Gi" "2" "7200"

# --- Weekly Briefing: Quantum (Monday 12:45 UTC) ---
create_job "quantum-weekly-briefing" \
  "scripts/run_weekly_briefing.py,--domain,quantum,--save" \
  "ANTHROPIC_API_KEY=anthropic-api-key:latest" \
  "" "4Gi" "2" "3600"

# --- Weekly Briefing: AI (Monday 12:00 UTC) ---
create_job "ai-weekly-briefing" \
  "scripts/run_weekly_briefing.py,--domain,ai,--save" \
  "ANTHROPIC_API_KEY=anthropic-api-key:latest" \
  "" "4Gi" "2" "3600"

# --- Stocks (daily, after market close) ---
create_job "quantum-stocks-ingestion" \
  "scripts/run_ingestion.py,--sources,stocks" \
  "ANTHROPIC_API_KEY=anthropic-api-key:latest"

# --- Quantum Digest (daily) ---
create_job "quantum-digest" \
  "scripts/run_digest.py,--domain,quantum,--use-llm,--save" \
  "ANTHROPIC_API_KEY=anthropic-api-key:latest"

# --- AI Digest (daily) ---
create_job "ai-digest" \
  "scripts/run_digest.py,--domain,ai,--use-llm,--save" \
  "ANTHROPIC_API_KEY=anthropic-api-key:latest"

echo ""
echo "=== All Cloud Run Jobs created! ==="
echo ""
echo "Test a job:"
echo "  gcloud run jobs execute quantum-rss-ingestion --region ${REGION} --project ${PROJECT_ID}"
