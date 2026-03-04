#!/bin/bash
# ============================================================================
# Cloud Run Service — Quantum + AI Intelligence Hub Frontend
# ============================================================================
# Builds the UI Docker image and deploys it as a public Cloud Run Service.
#
# Usage:
#   chmod +x deploy/cloud_run_frontend.sh
#   ./deploy/cloud_run_frontend.sh
# ============================================================================
set -euo pipefail

PROJECT_ID="gen-lang-client-0436975498"
REGION="us-central1"
SERVICE_NAME="quantum-intel-frontend"
IMAGE="us-central1-docker.pkg.dev/${PROJECT_ID}/quantum-intel/quantum-intel-frontend:latest"

COMMON_ENV="GCP_PROJECT_ID=${PROJECT_ID},BQ_DATASET_ID=quantum_ai_hub,GCP_REGION=${REGION},STORAGE_BACKEND=bigquery"

echo "=== Building and pushing UI Docker image ==="
gcloud builds submit . \
  --project "${PROJECT_ID}" \
  --config cloudbuild-ui.yaml \
  --timeout=1200

echo ""
echo "=== Deploying Cloud Run Service ==="

# We need the API keys for the backend agents to work
SECRETS="ANTHROPIC_API_KEY=anthropic-api-key:latest,EXA_API_KEY=EXA_API_KEY:latest,LOGO_DEV_TOKEN=LOGO_DEV_TOKEN:latest"

gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --allow-unauthenticated \
  --set-secrets "${SECRETS}" \
  --set-env-vars "${COMMON_ENV}" \
  --memory "2Gi" \
  --cpu "1" \
  --min-instances "0" \
  --max-instances "10" \
  --port 8080

echo ""
echo "=== Frontend Deployed Successfully! ==="
