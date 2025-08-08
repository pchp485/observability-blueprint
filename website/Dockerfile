FROM nginx:1.27-alpine
WORKDIR /usr/share/nginx/html
COPY . .
# Generate env.js at container start from $GRAFANA_URL
COPY entrypoint.sh /docker-entrypoint.d/99-grafana-url.sh
RUN chmod +x /docker-entrypoint.d/99-grafana-url.sh
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=8s --start-period=15s --retries=3 \
  CMD wget --spider -q http://localhost || exit 1
CMD ["nginx","-g","daemon off;"]