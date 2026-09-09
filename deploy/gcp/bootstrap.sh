#!/usr/bin/env bash
# Nabd — phase 2 bootstrap for Google Cloud (run in Cloud Shell from the repo root).
#
#   bash deploy/gcp/bootstrap.sh <PROJECT_ID>
#
# Enables the APIs, creates a least-privilege runtime service account, and deploys the
# same container that runs on Railway to Cloud Run in me-central1 (Doha). On first boot the
# app provisions the BigQuery dataset from the committed synthetic HIE, then serves from it.
set -euo pipefail

PROJECT_ID="${1:-${GOOGLE_CLOUD_PROJECT:-}}"
[[ -n "$PROJECT_ID" ]] || { echo "usage: bash deploy/gcp/bootstrap.sh <PROJECT_ID>"; exit 1; }
REGION="${REGION:-me-central1}"
SERVICE="${SERVICE:-nabd}"
SA_NAME="${SA_NAME:-nabd-run}"
SA="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
DATASET="${DATASET:-nabd_hie}"
GEMINI_LOCATION="${GEMINI_LOCATION:-global}"     # Gemini 3.x is served from the global endpoint

echo "▸ project $PROJECT_ID · region $REGION · service $SERVICE"
gcloud config set project "$PROJECT_ID" >/dev/null

echo "▸ enabling APIs"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  bigquery.googleapis.com bigquerystorage.googleapis.com aiplatform.googleapis.com iam.googleapis.com \
  cloudresourcemanager.googleapis.com

echo "▸ runtime service account (least privilege)"
gcloud iam service-accounts create "$SA_NAME" --display-name "Nabd Cloud Run runtime" 2>/dev/null || true
for role in roles/bigquery.dataEditor roles/bigquery.jobUser roles/aiplatform.user roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member "serviceAccount:$SA" --role "$role" --quiet >/dev/null
done

echo "▸ build service account permissions (Cloud Build runs as the Compute Engine default SA on new projects)"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format 'value(projectNumber)')
BUILD_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
for role in roles/cloudbuild.builds.builder roles/artifactregistry.writer roles/storage.objectViewer; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member "serviceAccount:$BUILD_SA" --role "$role" --quiet >/dev/null
done

echo "▸ deploying to Cloud Run ($REGION) — Cloud Build builds the Dockerfile (trains the models at build)"
gcloud run deploy "$SERVICE" --source . --region "$REGION" \
  --service-account "$SA" --allow-unauthenticated \
  --min-instances 1 --max-instances 5 --cpu 2 --memory 2Gi --timeout 300 --concurrency 40 \
  --set-env-vars "HIE_BACKEND=bigquery,BQ_DATASET=${DATASET},BQ_LOCATION=${REGION},GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_LOCATION=${GEMINI_LOCATION},NABD_REGION=${REGION},THINKING_LEVEL=LOW"

URL=$(gcloud run services describe "$SERVICE" --region "$REGION" --format 'value(status.url)')
echo
echo "✓ Nabd is live: $URL"
echo "  health: $URL/api/health   (expect compute=cloud-run, data.loaded_from=bigquery, llm=vertex)"
echo "  first boot loads BigQuery from the csv files (~1 min); reload the page after that."
