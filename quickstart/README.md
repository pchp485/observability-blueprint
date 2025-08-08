# AetherCollect Quick Start (Local)

This gets you metrics in minutes on your laptop.

## 1) Install Docker
- Docker Desktop (Mac/Windows) or Docker Engine (Linux)

## 2) Save these files
- docker-compose.yml
- aether-agent-config.yaml
- prometheus.yml

## 3) Point the agent at your app
Edit aether-agent-config.yaml:

```
receivers:
  prometheus_simple:
    endpoint: "APP_METRICS_ENDPOINT"   # e.g., host.docker.internal:8000
    metrics_path: "/metrics"
```

If your app exposes OTLP, you can skip prometheus_simple and send to localhost:4317.

## 4) Launch the stack
```
docker compose up -d
```

- Grafana: http://localhost:3000 (admin/admin on first login)
- Prometheus: http://localhost:9090
- Agent Prometheus exporter: http://localhost:8889/metrics

## 5) Verify in Grafana
- Add Prometheus datasource: http://prometheus:9090 (in Compose network) or http://localhost:9090
- Query: `up` and `http_requests_total` (if your app exposes that)

## 6) Traces & Logs (next)
- Traces: instrument your app with OpenTelemetry and point OTLP to localhost:4317
- Logs: add `filelog` receiver and exporters in the agent config