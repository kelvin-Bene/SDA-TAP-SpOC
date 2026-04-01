# Frontend: Multi-stage build — Node for building, nginx for serving

# Stage 1: Build
FROM node:18-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Vite embeds VITE_* env vars at build time, so we pass them as build args
# Railway automatically converts env vars to build args for Docker builds
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_CESIUM_ION_TOKEN
ARG VITE_FEEDBACK_ENABLED

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_SUPABASE_URL=$VITE_SUPABASE_URL
ENV VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY
ENV VITE_CESIUM_ION_TOKEN=$VITE_CESIUM_ION_TOKEN
ENV VITE_FEEDBACK_ENABLED=$VITE_FEEDBACK_ENABLED

RUN npm run build

# Stage 2: Serve
FROM nginx:1.25-alpine

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx template (uses $PORT for Railway compatibility)
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# Default port (Railway overrides via $PORT env var)
ENV PORT=80
ENV BACKEND_URL=http://localhost:8000

EXPOSE 80

CMD ["/bin/sh", "-c", "envsubst '$$PORT $$BACKEND_URL' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
