# Frontend: Multi-stage build — Node for building, nginx for serving

# Stage 1: Build
FROM node:18-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# API requests go through nginx proxy at /api/v1
ENV VITE_API_BASE_URL=/api/v1
ENV VITE_DEMO_MODE=true
ENV VITE_FEEDBACK_ENABLED=true

RUN npm run build

# Stage 2: Serve
FROM nginx:1.25-alpine

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx config template
COPY nginx.conf.template /etc/nginx/nginx.conf.template
RUN rm -f /etc/nginx/conf.d/default.conf

ENV PORT=80
ENV BACKEND_URL=http://backend:8000
ENV BACKEND_HOST=backend

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["sh", "-c", "envsubst '${PORT} ${BACKEND_URL} ${BACKEND_HOST}' < /etc/nginx/nginx.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
