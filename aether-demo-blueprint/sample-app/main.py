from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
import time
import random
import psutil
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry

registry = CollectorRegistry()

REQ_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'], registry=registry)
REQ_DURATION = Histogram('http_request_duration_seconds', 'Duration seconds', ['method', 'endpoint'], registry=registry)
CPU = Gauge('system_cpu_usage_percent', 'CPU percent', registry=registry)
MEM = Gauge('system_memory_usage_bytes', 'Memory bytes', registry=registry)

app = FastAPI(title="Sample Observability App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    CPU.set(psutil.cpu_percent())
    MEM.set(psutil.virtual_memory().used)

    try:
        response = await call_next(request)
        status = str(response.status_code)
    except Exception:
        status = "500"
        raise
    finally:
        dur = time.time() - start
        REQ_COUNT.labels(request.method, request.url.path, status).inc()
        REQ_DURATION.labels(request.method, request.url.path).observe(dur)
    return response

@app.get("/")
async def root():
    return {"message": "Sample app up"}

@app.get("/health")
async def health():
    return {"status": "healthy", "ts": time.time(), "cpu": psutil.cpu_percent()}

@app.get("/api/simulate/load")
async def simulate_load():
    d = random.uniform(0.1, 1.0)
    time.sleep(d)
    return {"simulated_seconds": d}

@app.get("/api/simulate/error")
async def simulate_error():
    if random.random() &lt; 0.4:
        raise HTTPException(status_code=500, detail="simulated error")
    return {"ok": True}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)