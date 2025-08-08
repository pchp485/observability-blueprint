FROM grafana/grafana:10.4.1
COPY provisioning /etc/grafana/provisioning
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:3000/api/health || exit 1
