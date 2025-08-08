#!/bin/sh
set -eu
GRAFANA_URL_VALUE="${GRAFANA_URL:-}"
# Write env.js so the landing page button links to Grafana
printf 'window.__GRAFANA_URL__="%s";\n' "$GRAFANA_URL_VALUE" > /usr/share/nginx/html/env.js