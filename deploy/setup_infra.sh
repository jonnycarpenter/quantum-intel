#!/bin/bash
# ============================================================================
# GCP Infrastructure Setup — Quantum + AI Intelligence Hub
# ============================================================================
# Run once to create all GCP resources. Idempotent (safe to re-run).
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - Billing enabled on the project
#
# Usage:
#   chmod +x deploy/setup_infra.sh
#   ./deploy/setup_infra.sh
# ============================================================================
set -euo pipefail

PROJECT_ID="gen-lang-client-0436975498"
REGION="us-central1"
DATASET_ID="quantum_ai_hub"
BUCKET="quantum-ai-hub-data"

echo "=== Quantum + AI Intelligence Hub — GCP Setup ==="
echo "Project:  ${PROJECT_ID}"
echo "Region:   ${REGION}"
echo "Dataset:  ${DATASET_ID}"
echo ""

# ---- Enable APIs ----
echo "Enabling GCP APIs..."
gcloud services enable \
  bigquery.googleapis.com \
  bigquerystorage.googleapis.com \
  aiplatform.googleapis.com \
  run.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --project "${PROJECT_ID}"

# ---- Artifact Registry ----
echo "Creating Artifact Registry repository..."
gcloud artifacts repositories create quantum-intel \
  --repository-format=docker \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --description="Quantum AI Intelligence Hub Docker images" \
  2>/dev/null || echo "  (already exists)"

# ---- BigQuery Dataset ----
echo "Creating BigQuery dataset..."
bq --project_id="${PROJECT_ID}" mk \
  --dataset \
  --location="${REGION}" \
  --description="Quantum + AI Intelligence Hub" \
  "${DATASET_ID}" \
  2>/dev/null || echo "  (already exists)"

# ---- GCS Bucket ----
echo "Creating GCS bucket..."
gcloud storage buckets create "gs://${BUCKET}" \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --uniform-bucket-level-access \
  2>/dev/null || echo "  (already exists)"

# ---- Secrets ----
echo "Creating secrets in Secret Manager..."
for SECRET_NAME in \
  anthropic-api-key \
  EXA_API_KEY \
  api-ninja-key \
  secio-api-key \
  assemblyai-api-key \
  stocknews-api-key; do

  gcloud secrets create "${SECRET_NAME}" \
    --replication-policy="automatic" \
    --project="${PROJECT_ID}" \
    2>/dev/null || echo "  ${SECRET_NAME} (already exists)"
done

echo ""
echo "Populate each secret with:"
echo '  echo -n "YOUR_KEY" | gcloud secrets versions add SECRET_NAME --data-file=- --project='"${PROJECT_ID}"

# ---- IAM Grants ----
echo ""
echo "Granting IAM roles to default compute service account..."
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Secret access
for SECRET_NAME in \
  anthropic-api-key \
  EXA_API_KEY \
  api-ninja-key \
  secio-api-key \
  assemblyai-api-key \
  stocknews-api-key; do

  gcloud secrets add-iam-policy-binding "${SECRET_NAME}" \
    --member="serviceAccount:${SA}" \
    --role="roles/secretmanager.secretAccessor" \
    --project="${PROJECT_ID}" \
    --quiet 2>/dev/null || true
done

# BigQuery
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA}" \
  --role="roles/bigquery.dataEditor" \
  --quiet 2>/dev/null || true

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA}" \
  --role="roles/bigquery.jobUser" \
  --quiet 2>/dev/null || true

# Vertex AI
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA}" \
  --role="roles/aiplatform.user" \
  --quiet 2>/dev/null || true

echo ""
echo "=== Infrastructure setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. Populate secrets (see commands above)"
echo "  2. Run: ./deploy/cloud_run_jobs.sh"
echo "  3. Run: ./deploy/setup_scheduler.sh"
