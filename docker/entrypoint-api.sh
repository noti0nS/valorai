#!/bin/sh
set -e

cd /app/server/python

echo "==> Applying local Cloudflare D1 migrations..."
uv run --python 3.14 pywrangler d1 migrations apply valorai-prototype --local

echo "==> Starting ValorAI Python Worker on 0.0.0.0:8787..."
exec uv run --python 3.14 pywrangler dev --ip 0.0.0.0 --port 8787
