
### `LOAD_TEST_REPORT.md`
# Load Test Report

**Target**  
- Cloud Run endpoint:  
  `https://penguin-api-service-217484219601.us-central1.run.app/predict`  
- Locust script: `locustfile.py`
- **Payload used**
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
---

## Scenarios and Results

| Scenario                         | Avg Latency | p95 Latency | p99 Latency | Failure Rate | Throughput  |
|----------------------------------|------------:|------------:|------------:|-------------:|------------:|
| Baseline (1 user, 60 s) – local  | 4 ms        | 9.21 ms        | 11.26 ms        | 0 fail/s     | 0.4 req/s   |
| Baseline (1 user, 60 s) – cloud  | 95.58 ms    | 180 ms       | 540.71 ms      | 0 fail/s     | 0.4 req/s   |
| Normal (10 users, 5 min) – local | 3.56 ms        | 7.41 ms        | 8 ms        | 0 fail/s     | 5.9 req/s   |
| Normal (10 users, 5 min) – cloud | 75.96 ms    | 150.25 ms      | 350.1 ms      | 0 fail/s  | 4.5 req/s  |
| Stress (50 users, 2 min)         | 115 ms    | 196.23 ms      | 140.91 ms      | 0 fail/s     | 25.57 req/s |
| Spike (1→100 users, ~1 min)      | 135.45 ms    | 259.52 ms       | 680.93 ms      | 0 fail/s     | 44.25 req/s |

---

## Bottlenecks Observed

- **Cold starts**: First requests on new instances increase p95/p99 until autoscaling finishes warming.
- **CPU-bound inference during bursts**: Short p95 spikes during rapid user ramp (Spike scenario).
- **Client-side payload issues (early run)**: A few 4xx from malformed JSON; removed after fixing the test body.

---

## Recommendations

1. **Pre-warm instances (min instances > 0)**  
   Reduce cold-start impact on p95/p99 by keeping 1–2 instances warm.  
2. **Tune concurrency**  
   Experiment with Cloud Run concurrency (e.g., 10–40) to balance latency vs. throughput.
3. **Tune autoscaling**  
   Adjust concurrency settings and maximum instance limits.  
4. **Scale limits**  
   Increase max instances if expecting >100 concurrent users or frequent spikes.
5. **Model/runtime optimizations**  
   Keep the model in memory (already done). Consider tree pruning/quantization or exporting to ONNX if latency becomes a constraint.
6. *Retries with backoff*
   Use exponential backoff for occasional 5xx during scale-up windows.
7. *Observability*
   Create SLOs and alerts around p95 latency and error rate; watch cold-start counts.

---

## Production Monitoring

-Track with Cloud Monitoring/Logging:

**Latency**: p50/p90/p95/p99
**Error rate**: HTTP 4xx/5xx and exception logs
**Throughput**: requests/second per service & per instance
**Resources**: CPU & memory utilization
**Autoscaling**: instance counts, cold-start frequency
**Budget/SLOs**: alert on cost anomalies and SLO breaches

---

## 10× Traffic Scenario

- **With adequate autoscaling**: Cloud Run adds instances; expect a brief p95/p99 uptick during ramp, then stabilize.
- **If constrained**: Without higher max instances or optimized concurrency, latency grows and timeouts may appear. Consider request batching (if API semantics allow) or larger CPU allocations.
---

## Reproduction Guide
**Local target**
```bash
# Start container locally (Windows example: path quoting may vary)
docker run --rm -d -p 8080:8080 ^
  -e GOOGLE_APPLICATION_CREDENTIALS=/home/appuser/sa-key.json ^
  -e GCS_BUCKET_NAME=assignment2-shiv-trivedi-bucket ^
  -e GCS_BLOB_NAME=model.json ^
  -v "%CD%\sa-key.json:/home/appuser/sa-key.json:ro" ^
  penguin-api

# Start Locust against local container
locust --host=http://localhost:8080
```
**Cloud target**
```bash
# Start Locust against Cloud Run URL
locust --host=https://penguin-api-service-217484219601.us-central1.run.app
```

## Conclusion

The API serves baseline and normal loads with low latency and near-zero errors. Under stress and spike conditions, autoscaling introduces short-lived p95/p99 increases, which can be mitigated via min instances, concurrency tuning, and proactive monitoring. With these adjustments, the service remains responsive and stable under heavier traffic.
---
