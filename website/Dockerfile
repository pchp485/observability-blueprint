FROM nginx:1.27-alpine
WORKDIR /usr/share/nginx/html
COPY . .
# env.js is generated at build time by the Blueprint buildCommand
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=8s --start-period=15s --retries=3 \
  CMD wget --spider -q http://localhost || exit 1
