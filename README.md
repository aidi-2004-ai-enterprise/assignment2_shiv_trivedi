# `Penguin Species Classification & Deployment`

![Demo](assets/demo.gif)

**Author:** Shivkumar Trivedi
**Course:** AIDI-2004 AI in Enterprise Systems
**Assignment:** 2 – ML Application Deployment
---

## Overview

This repository implements a full ML deployment workflow:

1. **Unit Testing**: comprehensive pytest suite for model & API validation.
2. **Containerization**: production-grade Dockerfile & .dockerignore.
3. **Artifact Registry**: secure storage of your container in GCP Artifact Registry.
4. **Cloud Run**: managed deployment with service account-based GCS access.
5. **Load Testing**: realistic traffic simulations using Locust.

Key technologies: XGBoost, FastAPI, Pydantic, Docker, Google Cloud (GCS, Artifact Registry, Cloud Run), Locust.

---

## Project Structure

```
assignment2_shiv_trivedi/
├── app/
│   ├── main.py                # FastAPI application
│   ├── data/
│   │   ├── label_map.json     # species mapping
│   │   └── model.json         # trained XGBoost model
├── tests/
│   └── test_api.py            # pytest suite
├── locustfile.py              # Locust load test script
├── Dockerfile                 # Docker image definition
├── .dockerignore              # excludes for Docker build
├── requirements.txt           # Python dependencies
├── sa-key.json                # GCP service account key (ignored in Git)
├── .env                       # environment variables
├── DEPLOYMENT.md              # container build & deployment notes
├── LOAD_TEST_REPORT.md        # load testing results & analysis
└── README.md                  # project overview & quick start
```

---

## Quick Start

### 1. Local Development (venv)

```bash
cd assignment2_shiv_trivedi
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
pip install -r requirements.txt
```

Train model & serve locally:

```bash
python train.py            # produces model.json
uvicorn app.main:app --reload
```

Test with curl:

```bash
curl -X POST http://127.0.0.1:8000/predict \
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

---

### 2. Docker Container

```bash
docker build -t penguin-api .
docker run -p 8080:8080 penguin-api
```

Verify:

```bash
curl http://localhost:8080/predict ...
```

---

### 3. Push to Artifact Registry

```bash
gcloud config set project penguin-api-shiv
gcloud artifacts repositories create penguin-repo --repository-format=docker --location=us-central1
gcloud auth configure-docker us-central1-docker.pkg.dev
docker tag penguin-api us-central1-docker.pkg.dev/penguin-api-shiv/penguin-repo/penguin-api:latest
docker push us-central1-docker.pkg.dev/penguin-api-shiv/penguin-repo/penguin-api:latest
```

---

### 4. Deploy to Cloud Run

```bash
gcloud run deploy penguin-api-service \
  --image us-central1-docker.pkg.dev/penguin-api-shiv/penguin-repo/penguin-api:latest \
  --region us-central1 --platform managed \
  --allow-unauthenticated \
  --set-env-vars GCS_BUCKET_NAME=assignment2-shiv-trivedi-bucket,GCS_BLOB_NAME=model.json
```

Test endpoint on the provided URL via Swagger UI or curl.

---

### 5. Load Testing with Locust

```bash
locust -f locustfile.py --host=http://localhost:8080 --web-host=0.0.0.0
```

Open [http://localhost:8089](http://localhost:8089) and run Baseline, Normal, Stress, and Spike scenarios. Results are documented in `LOAD_TEST_REPORT.md`.

---

## Assignment Questions

### 1. What edge cases might break your model in production that aren't in your training data?

* **Out-of-distribution species**: Penguins not represented (e.g., a new species) will confuse the classifier.
* **Missing or null fields**: If an input record omits features like `flipper_length_mm` or `sex`, prediction logic must catch and handle these.
* **Non-numeric values**: Corrupted or misformatted CSV entries (e.g. strings in numeric fields).
* **Extreme values**: Measurements outside realistic ranges (e.g. negative lengths, zero mass) must be validated.
* **Different data distributions**: Seasonal or regional shifts in average sizes not seen in the original Palmer dataset.

### 2. What happens if your model file becomes corrupted?

* The application will fail during startup or at inference time when attempting to load the model JSON.
* We catch `ValueError` or I/O errors in `main.py` and return a `500 Internal Server Error` or trigger an alert.
* As a mitigation, implement a health check endpoint that verifies model loading and fallback to a last-known-good backup.

### 3. What's a realistic load for a penguin classification service?

* In an ecological research app, perhaps tens of requests per minute per user.
* At scale, maybe 100–200 req/s peak if integrated into a real-time monitoring dashboard.
* We determined \~10 concurrent users (2 users/sec) is a typical “normal” load for testing.

### 4. How would you optimize if response times are too slow?

* **Keep the model in memory**: Avoid reloading from GCS on each inference.
* **Batch predictions**: Group multiple records per API call to leverage vectorized operations.
* **Increase CPU/memory**: Allocate more resources in Cloud Run or switch to a faster machine type.
* **Use GPU or optimized inference runtime**: Convert the model to ONNX and use a dedicated inference server.
* **Enable caching**: Cache common predictions (e.g. identical inputs) in Redis.

### 5. What metrics matter most for ML inference APIs?

* **Latency (p50, p90, p99)**: How long each request takes.
* **Throughput (requests/sec)**: How many inferences per second.
* **Error rate**: Percentage of failed predictions.
* **Resource utilization**: CPU, memory, and GPU usage.
* **Cold-start time**: Time to spin up a new instance.

### 6. Why is Docker layer caching important for build speed? (Did you leverage it?)

* **Layer caching** avoids re-running unchanged steps (e.g., `pip install`), speeding up builds.
* We copied `requirements.txt` before application code, so dependencies only reinstall when they change.

### 7. What security risks exist with running containers as root?

* If an attacker exploits the application, they gain root privileges inside the container.
* They could escape the container and affect the host or other containers.
* Mitigation: we created a non-root `appuser` in the Dockerfile.

### 8. How does cloud auto-scaling affect your load test results?

* **Cold starts**: New instances take time to spin up, increasing latency during sudden load spikes.
* **Scale-up delay**: Under heavy load, there’s a gap before new instances are ready, causing throttling or errors.
* **Warm instance reuse**: Once scaled, subsequent requests are faster.

### 9. What would happen with 10× more traffic?

* Without scaling, the single instance would saturate CPU/memory and start failing or queueing requests.
* With auto-scaling, Cloud Run would spin up more instances—but might hit concurrency or quota limits, requiring increased quotas or multi-region deployment.

### 10. How would you monitor performance in production?

* Use **Cloud Monitoring** and **Cloud Logging** to collect metrics (latency, error rates, CPU/memory).
* Set up alerts for high error rates or latency spikes.
* Integrate with Grafana or DataDog for dashboards.

### 11. How would you implement blue-green deployment?

* Deploy a new version to a **“green”** service while the old **“blue”** continues to serve traffic.
* Run smoke tests against green; when ready, switch the traffic split from blue → green in Cloud Run’s traffic settings.
* Roll back to blue if any issues.

### 12. What would you do if deployment fails in production?

* **Rollback**: Re-route traffic back to the last healthy revision (Cloud Run supports revision rollout).
* **Inspect logs**: Examine Cloud Logging for errors.
* **Fix & redeploy**: Patch the bug, rebuild, and re-release.

### 13. What happens if your container uses too much memory?

* Cloud Run will **OOM-kill** the container, returning 5xx errors.
* Mitigation: allocate more memory, optimize model size, or use memory profiling to pinpoint leaks.
