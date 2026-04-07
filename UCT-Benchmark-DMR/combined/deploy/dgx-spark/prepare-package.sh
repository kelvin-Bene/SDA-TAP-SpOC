#!/usr/bin/env bash
# prepare-package.sh — build a self-contained DGX Spark deliverable.
#
# Run this on a dev workstation that has Docker (with buildx + qemu for ARM64
# emulation), git, and access to the seed data CSVs. It produces a
# `dgx-package/` directory that contains everything needed to bring up the
# stack on a DGX Spark with no internet access:
#
#   dgx-package/
#   ├── repo/                          # full SDA-TAP-SpOC source tree
#   ├── images/
#   │   ├── sda-tap-spoc-backend.tar   # arm64 backend image (docker save)
#   │   └── sda-tap-spoc-frontend.tar  # arm64 frontend image
#   ├── seed_data/                     # the 143 MB observation/satellite CSVs
#   ├── env/
#   │   └── .env.dgx                   # filled-in env (with service-account token)
#   └── install-on-spark.sh            # the script the operator runs on the Spark
#
# Copy the entire `dgx-package/` directory onto a thumb drive and you're done.
#
# Usage:
#   ./prepare-package.sh [output_dir]
#
# Defaults to `./dgx-package` next to this script. Pass an explicit path
# (e.g. `/media/usb/dgx-package`) to write directly to a thumb drive.

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
COMBINED_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"  # combined/
REPO_ROOT="$(cd "$COMBINED_DIR/../.." && pwd)"   # repo root (SDA-TAP-SpOC)
OUT_DIR="${1:-$SCRIPT_DIR/dgx-package}"

# Source for the bundled seed CSVs. Override with $SEED_SOURCE if your copy
# lives elsewhere.
SEED_SOURCE="${SEED_SOURCE:-/d/DMR/DMR(kelvinallignment)/reference-code/uct-benchmark-refactor-joncline/src/data}"

BACKEND_IMAGE="local/sda-tap-spoc-backend:dgx"
FRONTEND_IMAGE="local/sda-tap-spoc-frontend:dgx"

echo "→ Output directory: $OUT_DIR"
echo "→ Repo root:        $REPO_ROOT"
echo "→ Seed source:      $SEED_SOURCE"

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------

if ! command -v docker &> /dev/null; then
    echo "ERROR: docker not on PATH." >&2
    exit 1
fi
if ! docker buildx version &> /dev/null; then
    echo "ERROR: docker buildx is required for ARM64 cross-builds." >&2
    echo "       Install Docker Desktop or run: docker buildx install" >&2
    exit 1
fi
if [[ ! -d "$SEED_SOURCE" ]]; then
    echo "WARN: SEED_SOURCE does not exist: $SEED_SOURCE"
    echo "      Skipping seed_data copy. The package will have an empty seed_data/."
    echo "      Set SEED_SOURCE=<path> to override."
    SEED_SOURCE=""
fi

mkdir -p "$OUT_DIR/repo" "$OUT_DIR/images" "$OUT_DIR/seed_data" "$OUT_DIR/env"

# ---------------------------------------------------------------------------
# Stage 1: Copy the source tree
# ---------------------------------------------------------------------------

echo
echo "→ Stage 1/4: Copying repo source tree..."
# Use git archive when in a clean tree (faster + skips .venv etc.)
# Fall back to rsync.
if git -C "$REPO_ROOT" rev-parse &> /dev/null; then
    git -C "$REPO_ROOT" archive --format=tar HEAD | tar -x -C "$OUT_DIR/repo"
    echo "  ✓ git archive HEAD into repo/"
else
    rsync -a --exclude='.git' --exclude='.venv*' --exclude='node_modules' \
          --exclude='__pycache__' --exclude='*.duckdb' --exclude='dist' \
          "$REPO_ROOT/" "$OUT_DIR/repo/"
    echo "  ✓ rsync into repo/"
fi

# ---------------------------------------------------------------------------
# Stage 2: Copy the seed data
# ---------------------------------------------------------------------------

echo
echo "→ Stage 2/4: Copying seed data..."
if [[ -n "$SEED_SOURCE" ]]; then
    for csv in observations_.csv satelliteData_Full.csv; do
        if [[ -f "$SEED_SOURCE/$csv" ]]; then
            cp -v "$SEED_SOURCE/$csv" "$OUT_DIR/seed_data/"
        else
            echo "  WARN: $SEED_SOURCE/$csv not found, skipping"
        fi
    done
else
    echo "  (skipped — no SEED_SOURCE)"
fi

# ---------------------------------------------------------------------------
# Stage 3: Build the ARM64 docker images
# ---------------------------------------------------------------------------

echo
echo "→ Stage 3/4: Building ARM64 docker images (this is slow under qemu)..."

# Make sure a buildx builder exists
if ! docker buildx inspect dgx-builder &> /dev/null; then
    docker buildx create --name dgx-builder --use
else
    docker buildx use dgx-builder
fi

# Build the backend (linux/arm64 only — keeps the tarball small).
docker buildx build \
    --platform linux/arm64 \
    --build-arg PIP_INSTALL_TARGET=".[local-dgx]" \
    -f "$COMBINED_DIR/Dockerfile" \
    -t "$BACKEND_IMAGE" \
    --load \
    "$COMBINED_DIR"

# Build the frontend (linux/arm64 only).
docker buildx build \
    --platform linux/arm64 \
    --build-arg VITE_API_BASE_URL=/api/v1 \
    --build-arg VITE_DEMO_MODE=true \
    --build-arg VITE_LOCAL_DGX_MODE=true \
    -f "$COMBINED_DIR/frontend/Dockerfile" \
    -t "$FRONTEND_IMAGE" \
    --load \
    "$COMBINED_DIR/frontend"

echo "→ Saving images to tarballs..."
docker save -o "$OUT_DIR/images/sda-tap-spoc-backend.tar" "$BACKEND_IMAGE"
docker save -o "$OUT_DIR/images/sda-tap-spoc-frontend.tar" "$FRONTEND_IMAGE"
ls -lh "$OUT_DIR/images/"

# ---------------------------------------------------------------------------
# Stage 4: Generate .env.dgx and install script
# ---------------------------------------------------------------------------

echo
echo "→ Stage 4/4: Generating env file + install script..."

# Start from the example. Operator should edit this file BEFORE shipping the
# thumb drive to fill in the service-account UDL/ESA tokens.
cp "$SCRIPT_DIR/.env.dgx.example" "$OUT_DIR/env/.env.dgx"

cat <<'EOF' >> "$OUT_DIR/env/.env.dgx"

# ---------------------------------------------------------------------------
# Service-account credentials (set by prepare-package.sh operator before
# burning the thumb drive). Leave empty to ship as offline-only.
# ---------------------------------------------------------------------------
# UDL_TOKEN=...
# ESA_TOKEN=...
EOF

cp "$SCRIPT_DIR/install-on-spark.sh" "$OUT_DIR/install-on-spark.sh" 2>/dev/null || \
    echo "  WARN: install-on-spark.sh not found in $SCRIPT_DIR, skipping copy"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

echo
echo "✓ Package ready at: $OUT_DIR"
echo
echo "Total size:"
du -sh "$OUT_DIR" 2>/dev/null || echo "  (du not available)"
echo
echo "Next steps:"
echo "  1. Edit $OUT_DIR/env/.env.dgx and add the service-account UDL_TOKEN"
echo "  2. Copy the entire $OUT_DIR directory to a thumb drive:"
echo "       cp -r $OUT_DIR /media/<your-user>/<thumb-drive-label>/"
echo "  3. On the DGX Spark: plug in USB, run install-on-spark.sh from the drive"
