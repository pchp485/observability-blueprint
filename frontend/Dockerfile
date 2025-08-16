FROM node:18-alpine AS build
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile
COPY . .
RUN yarn build
FROM nginx:1.27-alpine
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=8s --start-period=15s --retries=3 \
  CMD wget --spider -q http://localhost || exit 1
CMD ["nginx","-g","daemon off;"]
