#!/usr/bin/env bash
# start-dgx.sh — single-command boot for the SDA-TAP-SpOC DGX Spark edition.
#
# Brings up the docker compose stack, waits for the backend healthcheck to
# pass, then opens the app in the default browser. Designed to be wired into
# a .desktop launcher and a `systemd --user` unit so project managers can
# just log into the Spark, click the dock icon, and have the app open.
#
# Idempotent: rerunning while the stack is already up is harmless.

set -euo pipefail

# Resolve script directory regardless of where it's invoked from.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
cd "$SCRIPT_DIR"

COMPOSE_FILE="docker-compose.dgx.yml"
ENV_FILE=".env.dgx"
HEALTH_URL="http://localhost/health"
APP_URL="http://localhost"
HEALTH_TIMEOUT_SECONDS=300

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------

if ! command -v docker &> /dev/null; then
    echo "ERROR: docker is not installed or not on PATH." >&2
    echo "On a DGX Spark, Docker + NVIDIA Container Toolkit are preinstalled." >&2
    echo "On other Linux hosts: https://docs.docker.com/engine/install/" >&2
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "ERROR: 'docker compose' (v2) is required but was not found." >&2
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    echo "INFO: $ENV_FILE not found — creating one from .env.dgx.example."
    echo "      You can edit it later to add UDL_TOKEN / ESA_TOKEN if you have them."
    cp .env.dgx.example "$ENV_FILE"
fi

if [[ ! -d "seed_data" ]] || [[ -z "$(ls -A seed_data 2>/dev/null)" ]]; then
    echo "WARN: seed_data/ is empty. The DuckDB will start blank — see seed_data/README.md"
    echo "      for instructions on populating it from reference-code/."
fi

# ---------------------------------------------------------------------------
# Bring up the stack
# ---------------------------------------------------------------------------

echo "→ Starting SDA-TAP-SpOC (DGX local edition)..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d

# ---------------------------------------------------------------------------
# Wait for the backend healthcheck (proxied through nginx at /health)
# ---------------------------------------------------------------------------

echo "→ Waiting for the stack to become healthy (up to ${HEALTH_TIMEOUT_SECONDS}s)..."
deadline=$(( $(date +%s) + HEALTH_TIMEOUT_SECONDS ))
while true; do
    if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
        echo "✓ Backend reports healthy."
        break
    fi
    if [[ $(date +%s) -ge $deadline ]]; then
        echo "ERROR: stack failed to become healthy within ${HEALTH_TIMEOUT_SECONDS}s." >&2
        echo "       Inspect with: docker compose -f $COMPOSE_FILE logs" >&2
        exit 1
    fi
    sleep 3
done

# ---------------------------------------------------------------------------
# Open the app in the default browser (best effort)
# ---------------------------------------------------------------------------

echo "→ Opening $APP_URL"
if command -v xdg-open &> /dev/null; then
    xdg-open "$APP_URL" > /dev/null 2>&1 &
elif command -v open &> /dev/null; then
    # macOS dev box
    open "$APP_URL" &
else
    echo "  (no xdg-open available; visit $APP_URL manually)"
fi

echo
echo "SDA-TAP-SpOC is running."
echo "  Frontend: $APP_URL"
echo "  API docs: http://localhost:8000/docs"
echo "  Stop:     docker compose -f $COMPOSE_FILE down"
echo "  Logs:     docker compose -f $COMPOSE_FILE logs -f"
