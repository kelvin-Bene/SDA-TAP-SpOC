# Frontend: Multi-stage build — Node for building, nginx for serving

# Stage 1: Build
FROM node:18-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Vite embeds VITE_* env vars at build time
# Railway passes env vars as Docker build args automatically
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_CESIUM_ION_TOKEN
ARG VITE_FEEDBACK_ENABLED

# Write .env file so Vite picks them up during build
RUN printf "VITE_API_BASE_URL=%s\nVITE_SUPABASE_URL=%s\nVITE_SUPABASE_ANON_KEY=%s\nVITE_CESIUM_ION_TOKEN=%s\nVITE_FEEDBACK_ENABLED=%s\n" \
  "$VITE_API_BASE_URL" "$VITE_SUPABASE_URL" "$VITE_SUPABASE_ANON_KEY" "$VITE_CESIUM_ION_TOKEN" "$VITE_FEEDBACK_ENABLED" > .env

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
