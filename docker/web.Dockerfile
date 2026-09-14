# syntax=docker/dockerfile:1
# Frontend build stage
FROM node:22-bookworm-slim AS web-build

WORKDIR /orchardvision

COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
COPY packages/types/package.json packages/types/package.json

RUN npm ci

COPY apps/web apps/web
COPY packages packages

RUN npm run build:web

# Runtime stage: nginx serves the built SPA + reverse-proxies /api to the API
FROM nginx:1.27-alpine AS runtime

COPY docker/web.nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=web-build /orchardvision/apps/web/dist /usr/share/nginx/html

EXPOSE 80