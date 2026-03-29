# Frontend: Multi-stage build — Node for building, nginx for serving

# Stage 1: Build
FROM node:18-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# API requests go through nginx proxy at /api/v1
ENV VITE_API_BASE_URL=/api/v1

# Demo mode flag (set to "true" for demo builds)
ARG VITE_DEMO_MODE=false
ENV VITE_DEMO_MODE=${VITE_DEMO_MODE}

RUN npm run build

# Stage 2: Serve
FROM nginx:1.25-alpine

# Default backend connection (overridable via Railway env vars)
ENV BACKEND_HOST=backend
ENV BACKEND_PORT=8000

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx config as template (nginx:alpine auto-runs envsubst on *.template files)
COPY nginx.conf /etc/nginx/templates/default.conf.template

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
