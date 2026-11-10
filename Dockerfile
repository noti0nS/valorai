# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim AS base
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python environment & dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_INSTALL_DIR=/root/.local/share/uv/python
ENV PATH="/root/.local/bin:$PATH"

# Install Python 3.14 to match the Pyodide/Worker runtime requirements
RUN uv python install 3.14

# --- Node Dependencies Stage ---
FROM base AS node-deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# --- Python Dependencies Stage ---
FROM base AS python-deps
WORKDIR /app/server/python
COPY server/python/pyproject.toml server/python/uv.lock server/python/pylock.toml ./
RUN uv sync --frozen --python 3.14

# --- Frontend Builder Stage (generates dist/) ---
FROM node-deps AS builder
WORKDIR /app
COPY . .
RUN npm run build

# --- API Service Stage (Python Worker + Django + D1 + Durable Objects) ---
FROM base AS api
WORKDIR /app

# Copy root node dependencies so Wrangler CLI is available
COPY --from=node-deps /app/node_modules ./node_modules
COPY --from=node-deps /app/package.json ./package.json

# Copy Python virtual environment and Python binary
COPY --from=python-deps /app/server/python/.venv ./server/python/.venv
COPY --from=python-deps /root/.local/share/uv/python /root/.local/share/uv/python

# Copy server code, migrations, tests, and assets
COPY server ./server
COPY assets ./assets
COPY shared ./shared
COPY tests ./tests
COPY package.json ./

# Copy built frontend so the worker can serve static assets directly
COPY --from=builder /app/dist ./dist

# Pre-sync Python Worker packages (Pyodide & python_modules) so container startup is instant
WORKDIR /app/server/python
RUN uv run --python 3.14 pywrangler sync
WORKDIR /app

EXPOSE 8787

COPY docker/entrypoint-api.sh /usr/local/bin/entrypoint-api.sh
RUN chmod +x /usr/local/bin/entrypoint-api.sh

ENTRYPOINT ["/usr/local/bin/entrypoint-api.sh"]

# --- Web Frontend Stage (Astro Dev Server with HMR) ---
FROM node-deps AS web
WORKDIR /app
COPY . .
EXPOSE 4321
ENV API_URL=http://api:8787
CMD ["npx", "astro", "dev", "--host", "0.0.0.0", "--port", "4321"]

