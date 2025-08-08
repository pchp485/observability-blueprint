FROM otel/opentelemetry-collector-contrib:0.98.0
COPY aether-agent-config.yaml /etc/otelcol-contrib/config.yaml
EXPOSE 4317 4318 8889 13133
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:13133/health || exit 1
CMD ["--config=/etc/otelcol-contrib/config.yaml"]
