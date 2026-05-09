# Debian slim — tránh lỗi npm/native binary trên Alpine khi build Next.js trên một số host (EC2)
FROM node:20-bookworm-slim AS builder
WORKDIR /app

# DNS/network ít timeout trên EC2
RUN npm config set fetch-retries 5 && npm config set fetch-retry-mintimeout 20000

COPY package*.json ./

# npm ci bắt buộc lockfile — trên EC2 nếu clone thiếu package-lock.json thì dùng npm install
RUN if [ -f package-lock.json ]; then \
      npm ci --no-audit --no-fund; \
    else \
      echo "WARN: package-lock.json missing — run npm install locally and commit lockfile for reproducible builds" && \
      npm install --no-audit --no-fund; \
    fi

COPY . .

# BACKEND_URL được nhúng vào next.config.mjs lúc build (rewrites destination)
ARG BACKEND_URL=http://localhost:4000
ENV BACKEND_URL=${BACKEND_URL}

ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:20-bookworm-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
