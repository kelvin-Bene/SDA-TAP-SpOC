# Frontend: Multi-stage build — Node for building, nginx for serving

# Stage 1: Build
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Build-time env vars (Railway passes service variables as build args)
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_FEEDBACK_ENABLED=true
ARG VITE_DEMO_MODE=true

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_SUPABASE_URL=${VITE_SUPABASE_URL}
ENV VITE_SUPABASE_ANON_KEY=${VITE_SUPABASE_ANON_KEY}
ENV VITE_FEEDBACK_ENABLED=${VITE_FEEDBACK_ENABLED}
ENV VITE_DEMO_MODE=${VITE_DEMO_MODE}

RUN npm run build

# Stage 2: Serve
FROM nginx:1.25-alpine

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
