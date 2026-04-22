#!/usr/bin/env bash
# install-on-spark.sh — runs on the DGX Spark to unpack a thumb-drive package
# prepared by prepare-package.sh on a dev workstation.
#
# Expected layout (relative to where this script lives on the thumb drive):
#
#   <usb-mount>/
#   ├── repo/                          # full source tree
#   ├── images/
#   │   ├── sda-tap-spoc-backend.tar
#   │   ├── sda-tap-spoc-frontend.tar
#   │   └── ollama.tar                 # optional (Phase 2 AI features)
#   ├── seed_data/                     # CSVs
#   ├── models/                        # optional (Phase 2 AI features)
#   │   └── ollama-models.tar          # ~24 GB of LLM weights
#   ├── env/.env.dgx                   # pre-filled env
#   └── install-on-spark.sh            # this script
#
# What it does:
#   1. Copies the source tree to ~/dmr-dgx
#   2. Loads the pre-built docker images (incl. ollama if present)
#   2.5 Restores the Ollama model volume from the tarball if present
#   3. Copies the seed CSVs into combined/deploy/dgx-spark/seed_data/
#   4. Drops the .env.dgx into combined/deploy/dgx-spark/.env.dgx
#   5. (Optional) wires up the .desktop launcher and systemd --user unit
#   6. Calls start-dgx.sh to bring everything up
#
# Idempotent — safe to rerun.

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve where the package lives
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PACKAGE_DIR="$SCRIPT_DIR"

INSTALL_HOME="${INSTALL_HOME:-$HOME/dmr-dgx}"
COMBINED_DIR="$INSTALL_HOME/UCT-Benchmark-DMR/combined"
DGX_DIR="$COMBINED_DIR/deploy/dgx-spark"

echo "→ Package directory:  $PACKAGE_DIR"
echo "→ Install destination: $INSTALL_HOME"

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------

if ! command -v docker &> /dev/null; then
    echo "ERROR: docker is not installed. On a real DGX Spark this should be" >&2
    echo "       preinstalled. Run 'sudo apt install docker.io' if not." >&2
    exit 1
fi

for required in repo images env; do
    if [[ ! -d "$PACKAGE_DIR/$required" ]]; then
        echo "ERROR: $PACKAGE_DIR/$required is missing — package looks incomplete." >&2
        exit 1
    fi
done

# ---------------------------------------------------------------------------
# Stage 1: Copy the source tree
# ---------------------------------------------------------------------------

echo
echo "→ Stage 1/6: Installing source tree to $INSTALL_HOME..."
mkdir -p "$INSTALL_HOME"

if command -v rsync &> /dev/null; then
    rsync -a --info=progress2 "$PACKAGE_DIR/repo/" "$INSTALL_HOME/"
else
    cp -a "$PACKAGE_DIR/repo/." "$INSTALL_HOME/"
fi
echo "  ✓ done"

# ---------------------------------------------------------------------------
# Stage 2: Load the docker images
# ---------------------------------------------------------------------------

echo
echo "→ Stage 2/6: Loading docker images (this can take a minute)..."
for tar in "$PACKAGE_DIR/images"/*.tar; do
    [[ -f "$tar" ]] || continue
    echo "  Loading $(basename "$tar")..."
    docker load -i "$tar"
done
echo "  ✓ done. Images present:"
docker images | grep -E "sda-tap-spoc|ollama|REPOSITORY" || true

# Try to pull the latest ollama image so gemma4 and other recent models
# work reliably. This is the preferred path when the Spark has internet
# (~3 GB one-time download). If pull fails (offline install), fall back to
# tagging the bundled 0.14.1 as :latest so docker compose can find it —
# this fallback MAY not run gemma4 at runtime (see compose file comment).
echo
echo "→ Stage 2a: Ensuring ollama:latest is available..."
if docker pull ollama/ollama:latest 2>/dev/null; then
    echo "  ✓ pulled ollama/ollama:latest (gemma4 will work)"
else
    echo "  WARN: could not pull ollama/ollama:latest (no internet?)"
    echo "        Tagging bundled 0.14.1 as :latest for offline install."
    echo "        NOTE: 0.14.1 may not run gemma4:e4b — if LLM features fail,"
    echo "        connect to internet and rerun install-on-spark.sh."
    docker tag ollama/ollama:0.14.1 ollama/ollama:latest
fi

# ---------------------------------------------------------------------------
# Stage 2.5: Restore the Ollama model volume (Phase 2 AI features)
# ---------------------------------------------------------------------------
#
# The model weights live in a Docker named volume called dgx_ollama_models
# (declared in docker-compose.dgx.yml). prepare-package.sh tarred the staging
# directory into models/ollama-models.tar; here we untar it into the volume
# using the already-loaded local/sda-tap-spoc-backend:dgx image as the tar
# conduit (backend is eclipse-temurin:17-jre-jammy which ships with tar).
# This avoids needing to pull alpine from Docker Hub — fully offline.
#
# The model is OPTIONAL — if the package doesn't include a models/ tarball,
# the AI features will return 503 from the LLM endpoints but the rest of
# the stack works normally.

echo
echo "→ Stage 2.5/6: Restoring Ollama model volume (Phase 2)..."
if [[ -f "$PACKAGE_DIR/models/ollama-models.tar" ]]; then
    docker volume create dgx_ollama_models >/dev/null
    echo "  → untarring $(du -h "$PACKAGE_DIR/models/ollama-models.tar" 2>/dev/null | cut -f1) into dgx_ollama_models volume..."
    # Use local/sda-tap-spoc-backend:dgx (already loaded in Stage 2) as the tar
    # conduit. The backend image is eclipse-temurin:17-jre-jammy-based (Ubuntu)
    # which ships with tar. This avoids needing to pull alpine:latest from
    # Docker Hub — keeps the install fully offline-capable.
    docker run --rm \
        -v dgx_ollama_models:/dst \
        -v "$PACKAGE_DIR/models:/src:ro" \
        --entrypoint tar \
        local/sda-tap-spoc-backend:dgx \
        -C /dst -xf /src/ollama-models.tar
    echo "  ✓ Ollama model restored to dgx_ollama_models volume"
else
    echo "  WARN: no models/ollama-models.tar in package — AI features will not work"
    echo "        (the rest of the stack will run; LLM endpoints will return 503)"
fi

# ---------------------------------------------------------------------------
# Stage 3: Copy the seed data into place
# ---------------------------------------------------------------------------

echo
echo "→ Stage 3/6: Copying seed data..."
mkdir -p "$DGX_DIR/seed_data"
if [[ -d "$PACKAGE_DIR/seed_data" ]]; then
    cp -v "$PACKAGE_DIR/seed_data/"*.csv "$DGX_DIR/seed_data/" 2>/dev/null || \
        echo "  (no .csv files found in $PACKAGE_DIR/seed_data — DuckDB will start empty)"
fi

# ---------------------------------------------------------------------------
# Stage 4: Drop the .env.dgx into place
# ---------------------------------------------------------------------------

echo
echo "→ Stage 4/6: Installing .env.dgx..."
if [[ -f "$PACKAGE_DIR/env/.env.dgx" ]]; then
    cp "$PACKAGE_DIR/env/.env.dgx" "$DGX_DIR/.env.dgx"
    echo "  ✓ $DGX_DIR/.env.dgx written (review this file to confirm UDL token)"
else
    echo "  WARN: no env/.env.dgx in package — using .env.dgx.example as the default"
    cp "$DGX_DIR/.env.dgx.example" "$DGX_DIR/.env.dgx"
fi

# ---------------------------------------------------------------------------
# Stage 5: Optional — wire desktop launcher + systemd unit
# ---------------------------------------------------------------------------

echo
echo "→ Stage 5/6: Wiring autostart..."

# Desktop launcher (Activities overview / dock)
if command -v update-desktop-database &> /dev/null; then
    mkdir -p "$HOME/.local/share/applications"
    cp "$DGX_DIR/sda-tap-spoc.desktop" "$HOME/.local/share/applications/"
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    echo "  ✓ Desktop launcher installed"
fi

# Systemd --user unit
if command -v systemctl &> /dev/null; then
    mkdir -p "$HOME/.config/systemd/user"
    cp "$DGX_DIR/systemd/sda-tap-spoc.service" "$HOME/.config/systemd/user/"
    systemctl --user daemon-reload
    systemctl --user enable sda-tap-spoc.service || true
    # `loginctl enable-linger` so the user unit can start before login.
    # Won't fail the script if the user can't run it.
    loginctl enable-linger "$USER" 2>/dev/null || \
        echo "  (could not enable lingering for $USER — autostart at login still works)"
    echo "  ✓ systemd --user unit installed"
fi

# ---------------------------------------------------------------------------
# Stage 6: Bring it up
# ---------------------------------------------------------------------------

echo
echo "→ Stage 6/6: Starting the stack..."
chmod +x "$DGX_DIR/start-dgx.sh"
"$DGX_DIR/start-dgx.sh"

echo
echo "✓ Install complete."
echo "  App URL:  http://localhost"
echo "  API docs: http://localhost:8000/docs"
echo "  Manage:   cd $DGX_DIR && docker compose -f docker-compose.dgx.yml [up|down|logs]"
