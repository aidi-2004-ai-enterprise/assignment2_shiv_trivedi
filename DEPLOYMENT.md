# Penguin Species Classification — Deployment Guide

**Author:** Shivkumar Trivedi  
**Course:** AIDI-2004 AI in Enterprise Systems  
**Assignment:** 2 – ML Application Deployment

This document provides a comprehensive deployment guide for the FastAPI + XGBoost application, covering containerization, Artifact Registry, Cloud Run deployment, smoke tests, troubleshooting, one-command summary, and improvements.

---

## Table of Contents

1. [Containerization](#1-containerization)
2. [Push to Google Artifact Registry](#2-push-to-google-artifact-registry)
3. [Deploy to Cloud Run](#3-deploy-to-cloud-run)
4. [Smoke Testing](#4-smoke-testing)
5. [Troubleshooting](#5-troubleshooting-i-encountered)
6. [One-Command Summary](#6-one-command-summary-windows-cmd)
7. [Improvements / Next Steps](#7-improvements--next-steps)

---

## 1) Containerization

### Dockerfile (Final Version)

**Key Design Decisions:**
- **Base image:** `python:3.11-slim` (required for scientific stack like NumPy/XGBoost)
- **Security:** Run as non-root `appuser`
- **Performance:** Use Docker layer caching (install dependencies before copying source)
- **Port:** `8080` (Cloud Run default)
- **Entrypoint:** Uvicorn ASGI server

```dockerfile
FROM python:3.11-slim

# Security: non-root user
RUN useradd --create-home appuser
USER appuser
WORKDIR /home/appuser

# Layer caching: install deps first
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code last
COPY --chown=appuser:appuser . .

EXPOSE 8080
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Build & Run Locally

```bash
# Build image
docker build -t penguin-api .

# Run container (simple local run)
docker run --rm -p 8080:8080 penguin-api
```

To load the model from GCS during local container runs, mount your service-account key and pass environment variables.

**Windows (CMD):**
```cmd
docker run --rm -d -p 8080:8080 ^
  -e GOOGLE_APPLICATION_CREDENTIALS=/home/appuser/sa-key.json ^
  -e GCS_BUCKET_NAME=assignment2-shiv-trivedi-bucket ^
  -e GCS_BLOB_NAME=model.json ^
  -v "%CD%\sa-key.json:/home/appuser/sa-key.json:ro" ^
  penguin-api
```

**macOS/Linux (bash):**
```bash
docker run --rm -d -p 8080:8080 \
  -e GOOGLE_APPLICATION_CREDENTIALS=/home/appuser/sa-key.json \
  -e GCS_BUCKET_NAME=assignment2-shiv-trivedi-bucket \
  -e GCS_BLOB_NAME=model.json \
  -v "$PWD/sa-key.json:/home/appuser/sa-key.json:ro" \
  penguin-api
```

### Inspect Image

```bash
docker image ls penguin-api
docker history penguin-api
docker image inspect penguin-api --format='{{.Size}}'
```

### Issues & Fixes

- **NumPy build failure on python:3.10-slim**
  - **Fix:** Upgraded to `python:3.11-slim`; dependencies install cleanly
- **Large image (~2.1–2.2 GB) due to XGBoost/NumPy**
  - **Future work:** multi-stage builds, slimmer dependencies, wheels only, pruning unused packages

---

## 2) Push to Google Artifact Registry

**Configuration:**
- **Project:** `penguin-api-shiv`
- **Region:** `us-central1`
- **Repository:** `penguin-repo` (format: Docker)

### One-time Setup

```bash
gcloud config set project penguin-api-shiv
gcloud services enable run.googleapis.com artifacts.googleapis.com
```

Create the repository (idempotent; "already exists" is fine):

```bash
gcloud artifacts repositories create penguin-repo \
  --repository-format=docker \
  --location=us-central1 \
  --description="Penguin API Docker images"
```

Authenticate Docker to push:

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### Tag & Push

```bash
docker tag penguin-api \
  us-central1-docker.pkg.dev/penguin-api-shiv/penguin-repo/penguin-api:latest

docker push \
  us-central1-docker.pkg.dev/penguin-api-shiv/penguin-repo/penguin-api:latest
```

**Verify in Console:** Artifact Registry → us-central1 → penguin-repo should show `penguin-api:latest`

---

## 3) Deploy to Cloud Run

### Deploy Command

```bash
gcloud run deploy penguin-api-service \
  --image us-central1-docker.pkg.dev/penguin-api-shiv/penguin-repo/penguin-api:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars GCS_BUCKET_NAME=assignment2-shiv-trivedi-bucket,GCS_BLOB_NAME=model.json
```

> **Note:** The service uses Cloud Run's identity to access GCS. If you see permission errors, grant your Cloud Run service account `roles/storage.objectViewer` on the bucket.

### Get the Service URL

```bash
gcloud run services describe penguin-api-service \
  --region us-central1 \
  --format="value(status.url)"
```

**Final URL used:**
```
https://penguin-api-service-217484219601.us-central1.run.app/docs
```

---

## 4) Smoke Testing

### Swagger UI

Open in a browser:
```
https://penguin-api-service-217484219601.us-central1.run.app/docs
```

### POST /predict Test

**curl (bash/macOS/Linux):**
```bash
curl -X POST "https://penguin-api-service-217484219601.us-central1.run.app/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "bill_length_mm": 39.1,
    "bill_depth_mm": 18.7,
    "flipper_length_mm": 181,
    "body_mass_g": 3750,
    "year": 2007,
    "sex": "male",
    "island": "Biscoe"
  }'
```

**curl (Windows CMD):**
```cmd
curl -X POST "https://penguin-api-service-217484219601.us-central1.run.app/predict" ^
  -H "Content-Type: application/json" ^
  -d "{\"bill_length_mm\":39.1,\"bill_depth_mm\":18.7,\"flipper_length_mm\":181,\"body_mass_g\":3750,\"year\":2007,\"sex\":\"male\",\"island\":\"Biscoe\"}"
```

**Expected response (example):**
```json
{"prediction":"Adelie"}
```

---

## 5) Troubleshooting I Encountered

- **Container failed to start (PORT/health check):**
  - Ensured Uvicorn binds `0.0.0.0:8080` and `--port 8080` is set in Cloud Run

- **ADC/credentials error during local Docker run:**
  - Mounted `sa-key.json` and set `GOOGLE_APPLICATION_CREDENTIALS` to the mount path

- **404 at root /:**
  - Expected. Use `/docs` (Swagger) and `/predict` for inference

---

## 6) One-Command Summary (Windows CMD)

```cmd
REM Build
docker build -t penguin-api .

REM Configure & Push
gcloud config set project penguin-api-shiv
gcloud services enable run.googleapis.com artifacts.googleapis.com
gcloud auth configure-docker us-central1-docker.pkg.dev
docker tag penguin-api us-central1-docker.pkg.dev/penguin-api-shiv/penguin-repo/penguin-api:latest
docker push us-central1-docker.pkg.dev/penguin-api-shiv/penguin-repo/penguin-api:latest

REM Deploy
gcloud run deploy penguin-api-service ^
  --image us-central1-docker.pkg.dev/penguin-api-shiv/penguin-repo/penguin-api:latest ^
  --region us-central1 ^
  --platform managed ^
  --allow-unauthenticated ^
  --port 8080 ^
  --set-env-vars GCS_BUCKET_NAME=assignment2-shiv-trivedi-bucket,GCS_BLOB_NAME=model.json
```

---

## 7) Improvements / Next Steps

- **Reduce image size:** multi-stage builds, slimmer requirements, wheels-only dependencies

- **Mitigate cold starts:** set minimum instances > 0

- **CI/CD:** GitHub Actions to build/push image & deploy on merge with approvals

- **Observability:** structured logs, dashboards, alerts on p95 latency & error rate, track cold starts

- **Model/runtime optimization:** consider ONNX or pruning/quantization for lower latency at scale
