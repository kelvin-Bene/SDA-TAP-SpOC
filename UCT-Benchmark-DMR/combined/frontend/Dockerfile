# Frontend: Multi-stage build — Node for building, nginx for serving

# Stage 1: Build
FROM node:18-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# API requests go through nginx proxy at /api/v1
ENV VITE_API_BASE_URL=/api/v1

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
