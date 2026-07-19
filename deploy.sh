#!/usr/bin/env bash
# Deploy Bhagya to GCP Cloud Run.
#
# Usage:
#     GCP_PROJECT=my-project-id \
#     OPENAI_API_KEY=... \
#     ASTRO_AI_COOKIE_SECRET=... \
#     ADMIN_PASSWORD=... \
#     ./deploy.sh
#
# Optional env vars: GCP_REGION (default: asia-south1 / Mumbai),
# ASTRO_AI_API_BASE, ASTRO_AI_MODEL, BHAGYA_STORAGE_BUCKET (enables shared
# GCS cache for Rashifal — see README for bucket setup).
#
# Prereqs:
#   1. gcloud CLI installed + `gcloud auth login` done
#   2. GCP project created + billing enabled
#   3. Cloud Run + Cloud Build APIs enabled in that project
#
# Security note: this script passes secrets via --set-env-vars. They land in
# Cloud Run's env, are visible in the GCP console to anyone with read access
# to your project, and show in `gcloud run services describe`. Fine for solo
# dev / small team. For production, migrate to Secret Manager (see README).

set -euo pipefail

PROJECT_ID="${GCP_PROJECT:-}"
REGION="${GCP_REGION:-asia-south1}"  # Mumbai
SERVICE_NAME="bhagya"

if [[ -z "${PROJECT_ID}" ]]; then
  echo "ERROR: set GCP_PROJECT env var to your GCP project ID" >&2
  exit 1
fi

required=(OPENAI_API_KEY ASTRO_AI_COOKIE_SECRET ADMIN_PASSWORD)
for var in "${required[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    echo "ERROR: $var must be set before deploying" >&2
    exit 1
  fi
done

# Build the --set-env-vars argument; only include optional vars if set.
env_pairs=(
  "OPENAI_API_KEY=${OPENAI_API_KEY}"
  "ASTRO_AI_COOKIE_SECRET=${ASTRO_AI_COOKIE_SECRET}"
  "ADMIN_PASSWORD=${ADMIN_PASSWORD}"
)
[[ -n "${ASTRO_AI_API_BASE:-}"     ]] && env_pairs+=("ASTRO_AI_API_BASE=${ASTRO_AI_API_BASE}")
[[ -n "${ASTRO_AI_MODEL:-}"        ]] && env_pairs+=("ASTRO_AI_MODEL=${ASTRO_AI_MODEL}")
[[ -n "${BHAGYA_STORAGE_BUCKET:-}" ]] && env_pairs+=("BHAGYA_STORAGE_BUCKET=${BHAGYA_STORAGE_BUCKET}")
[[ -n "${GOOGLE_CLIENT_ID:-}"      ]] && env_pairs+=("GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}")

env_csv=$(IFS=, ; echo "${env_pairs[*]}")

echo "Deploying ${SERVICE_NAME} to ${REGION} of project ${PROJECT_ID}..."

gcloud run deploy "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --source . \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 60 \
  --concurrency 80 \
  --min-instances 0 \
  --max-instances 5 \
  --set-env-vars "${env_csv}"

echo
echo "Deployed. Service URL:"
gcloud run services describe "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" --region "${REGION}" \
  --format='value(status.url)'
