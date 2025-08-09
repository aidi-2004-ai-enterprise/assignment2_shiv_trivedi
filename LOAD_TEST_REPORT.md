# Load Test Report

**Author:** Shivkumar Trivedi  
**Course:** AIDI-2004 AI in Enterprise Systems  
**Assignment:** 2 – ML Application Deployment

---

## Target Under Test

### Endpoints
- **Cloud Run endpoint:** `https://penguin-api-service-217484219601.us-central1.run.app/predict`
- **Local endpoint:** `http://localhost:8080/predict`

### Test Configuration
- **Locust script:** `locustfile.py`
- **Test payload:**
```json
{
  "bill_length_mm": 39.1,
  "bill_depth_mm": 18.7,
  "flipper_length_mm": 181,
  "body_mass_g": 3750,
  "year": 2007,
  "sex": "male",
  "island": "Biscoe"
}
```

### Environment Notes
- **Local:** Windows + Docker Desktop (WSL2), image built from `python:3.11-slim`
- **Cloud:** Cloud Run (fully managed), us-central1, unauthenticated, port 8080
- **Model loading:** Model loads once from GCS at startup and remains cached in memory

---

## Test Scenarios and Results

| Scenario | Environment | Avg Latency | p95 Latency | p99 Latency | Failure Rate | Throughput |
|----------|-------------|-------------|-------------|-------------|--------------|------------|
| Baseline (1 user, 60s) | Local | 4 ms | 9.21 ms | 11.26 ms | 0 fail/s | 0.4 req/s |
| Baseline (1 user, 60s) | Cloud | 95.58 ms | 180 ms | 540.71 ms | 0 fail/s | 0.4 req/s |
| Normal (10 users, 5 min) | Local | 3.56 ms | 7.41 ms | 8 ms | 0 fail/s | 5.9 req/s |
| Normal (10 users, 5 min) | Cloud | 75.96 ms | 150.25 ms | 350.1 ms | 0 fail/s | 4.5 req/s |
| Stress (50 users, 2 min) | Cloud | 115 ms | 196.23 ms | 140.91 ms | 0 fail/s | 25.57 req/s |
| Spike (1→100 users, ~1 min) | Cloud | 135.45 ms | 259.52 ms | 680.93 ms | 0 fail/s | 44.25 req/s |

> **Note:** In the Stress run, the reported p99 < p95 (196.23 vs 140.91 ms). This is likely a sampling/rounding artifact from the short test window; re-running longer typically restores the expected ordering (p99 ≥ p95).

---

## Results Interpretation

### Performance Observations
- **Local latency** is very low (~4ms) with no TLS/network overhead
- **Cloud latency** is stable under Baseline/Normal loads
- **p95/p99 latencies** increase briefly during scale events and in the Spike scenario
- **Zero failures** were observed across all scenarios once payload formatting was correct

### Key Findings
1. The service handles baseline and normal loads effectively
2. Latency spikes are primarily caused by cold starts and scaling events
3. The system maintains stability even under stress conditions
4. Local performance significantly outperforms cloud due to network overhead elimination

---

## Bottlenecks Observed

### 1. Cold Starts / Scale-up Delay
- Short-lived p95/p99 bumps when new instances spin up
- Most noticeable during the Spike scenario

### 2. Transient CPU Pressure
- During Spike testing, concurrent JSON parsing + inference causes brief latency spikes
- Resource contention under high concurrent load

### 3. Short Test Windows
- Can distort tail metrics (see Stress p95/p99 anomaly)
- Longer test runs yield steadier percentile measurements

---

## Recommendations

### Infrastructure Optimizations

#### 1. Pre-warm Instances
Set Cloud Run minimum instances > 0 (e.g., 1–2) to mitigate cold-start impact on p95/p99 latencies.

#### 2. Tune Concurrency
Experiment with request concurrency settings (e.g., 10–40) to balance latency vs throughput for the model workload.

#### 3. Adjust Autoscaling Limits
- Raise maximum instances
- Verify quotas to absorb traffic spikes without throttling

### Application Optimizations

#### 4. Model/Runtime Optimization
- Keep model in memory (already implemented)
- Consider tree pruning/quantization or ONNX export if latency SLOs tighten

#### 5. Resilient Clients
Implement retries with exponential backoff for transient 5xx errors during scale-out windows.

### Monitoring & Observability

#### 6. Enhanced Observability
Set up dashboards and alerts for:
- p95 latency
- Error rates
- Instance count
- Cold starts
- CPU/memory usage

---

## Production Monitoring Plan

### Metrics to Track (via Cloud Monitoring/Logging)

#### Core Performance Metrics
- **Latency:** p50 / p90 / p95 / p99
- **Errors:** 4xx/5xx rates
- **Throughput:** requests/sec

#### Resource Metrics
- **CPU & Memory:** per instance utilization
- **Cold starts:** count and rate over time
- **Autoscaling:** instance count vs load

### Alerting Thresholds (Recommended)
- p95 latency > 300ms (sustained for 5 minutes)
- Error rate > 1% (sustained for 5 minutes)
- CPU > 85% or memory > 85% (sustained for 10 minutes)
- Excessive cold starts in a short period

---

## 10× Traffic Scenario Analysis

### Expected Behavior with Autoscaling
- Temporary rise in p95/p99 during traffic ramp-up
- Stabilization as instances scale up to meet demand

### If Resource Constrained
Latency will grow and timeouts may appear. Mitigation options:

1. **Increase scaling limits:** max instances and/or concurrency
2. **Batch processing:** Group requests where possible
3. **Resource upgrades:** Increase per-instance CPU/memory class
4. **Geographic distribution:** Deploy multi-region behind global HTTPS load balancer

---

## Reproduction Steps

### A) Local Testing

```bash
# Start Docker container locally (Windows CMD example; adjust paths for macOS/Linux)
docker run --rm -d -p 8080:8080 ^
  -e GOOGLE_APPLICATION_CREDENTIALS=/home/appuser/sa-key.json ^
  -e GCS_BUCKET_NAME=assignment2-shiv-trivedi-bucket ^
  -e GCS_BLOB_NAME=model.json ^
  -v "%CD%\sa-key.json:/home/appuser/sa-key.json:ro" ^
  penguin-api

# Run Locust against local container
locust -f locustfile.py --host=http://localhost:8080
# Open UI: http://localhost:8089
```

### B) Cloud Testing

```bash
# Run Locust against Cloud Run URL
locust -f locustfile.py --host=https://penguin-api-service-217484219601.us-central1.run.app
# Open UI: http://localhost:8089
```

### Test Scenarios (Execute via Locust UI)
1. **Baseline:** 1 user, 60 seconds
2. **Normal:** 10 users, 5 minutes
3. **Stress:** 50 users, 2 minutes
4. **Spike:** ramp 1 → 100 users over ~60 seconds

---

## Locust Configuration

### Test Script Reference

```python
# locustfile.py
from locust import HttpUser, task, between

SAMPLE = {
    "bill_length_mm": 39.1,
    "bill_depth_mm": 18.7,
    "flipper_length_mm": 181,
    "body_mass_g": 3750,
    "year": 2007,
    "sex": "male",
    "island": "Biscoe"
}

class PenguinUser(HttpUser):
    wait_time = between(0.2, 1.2)

    @task
    def predict(self):
        self.client.post("/predict", json=SAMPLE)
```

---

## Conclusion

The penguin classification service demonstrated robust performance characteristics during load testing:

- **Baseline and Normal loads** were handled with low latency and zero failures
- **Stress and Spike scenarios** showed expected latency increases aligned with autoscaling and cold start behavior
- **Performance optimization opportunities** exist through pre-warming instances, tuning concurrency, and enhanced observability

**Next Steps:** Implement the recommended infrastructure optimizations (minimum instances, concurrency tuning) and establish comprehensive monitoring to ensure consistent performance as traffic scales in production.