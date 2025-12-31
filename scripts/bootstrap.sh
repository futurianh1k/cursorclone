#!/usr/bin/env bash
set -euo pipefail

echo "[1/3] Installing JS deps (pnpm)..."
pnpm -r install

echo "[2/3] Python deps (api)..."
python -m pip install -U pip
python -m pip install -r <(python - <<'PY'
import tomllib
p=tomllib.load(open('apps/api/pyproject.toml','rb'))
print("\n".join(p['project']['dependencies']))
PY
)

echo "[3/3] Done."
echo "Run: pnpm --filter @poc/api dev"
echo "Run: pnpm --filter @poc/web dev"
