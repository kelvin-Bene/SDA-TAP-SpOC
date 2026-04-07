# SDA-TAP-SpOC — DGX Spark Local Edition

A self-contained build of the UCT Benchmark application that runs entirely on a single
NVIDIA DGX Spark (ARM64 / Blackwell iGPU / Ubuntu 24.04 DGX OS). It is **additive** to
the existing Railway `master` (production) and `dev` (demo) deployments — they are
unaffected.

## What's different about this build

| Concern | Cloud build (Railway) | DGX Spark build |
|---|---|---|
| Database | Supabase Postgres | DuckDB (single file) |
| Auth | Supabase JWT | `DEMO_MODE` (single shared user, no login) |
| Sample data | Generated from UDL/ESA on demand | Bundled seed CSVs (~143 MB) populated on first run |
| Network | Always-on | Online + offline cache (UDL/ESA pulls when available, seed fallback when not) |
| Cesium 3D viewer | Cesium Ion world imagery | Bundled NaturalEarthII texture (no Ion token needed) |
| Sentry | Active | Disabled |
| Packaging | Railway services | `docker compose` orchestration |
| Architecture | linux/amd64 | linux/arm64 (multi-arch image works on both) |

## How to run (already-set-up box)

```bash
cd combined/deploy/dgx-spark
cp .env.dgx.example .env.dgx     # then optionally fill in UDL_TOKEN / ESA_TOKEN
./start-dgx.sh
```

`start-dgx.sh` brings up the compose stack, waits for the backend healthcheck, then opens
`http://localhost` in the default browser.

To stop:

```bash
docker compose -f docker-compose.dgx.yml down
```

## Delivery flow: USB thumb drive

The delivered DGX Spark is **prepared on a dev workstation** and the result is
copied to a thumb drive. The Spark itself never needs internet (or even a
GitHub clone) to come up. Two scripts coordinate this:

| Script | Where it runs | What it does |
|---|---|---|
| `prepare-package.sh` | Dev workstation with Docker + buildx | Cross-builds ARM64 images, copies the source tree, copies the seed CSVs, drops a `.env.dgx`, produces a self-contained `dgx-package/` directory |
| `install-on-spark.sh` | The DGX Spark | Reads the `dgx-package/` from the mounted USB, copies files to `~/dmr-dgx`, loads the docker images, wires the desktop launcher + systemd unit, and runs `start-dgx.sh` |

### Step 1 — On the dev workstation: prepare the thumb drive

Prerequisites: Docker Desktop (or Docker Engine) with `buildx` installed and a
qemu binfmt registration so it can build `linux/arm64` from `linux/amd64`:

```bash
docker run --privileged --rm tonistiigi/binfmt --install arm64
```

Then:

```bash
cd UCT-Benchmark-DMR/combined/deploy/dgx-spark

# (optional) override the seed source if you have it elsewhere
export SEED_SOURCE="/d/DMR/DMR(kelvinallignment)/reference-code/uct-benchmark-refactor-joncline/src/data"

./prepare-package.sh                  # writes to ./dgx-package/
# OR
./prepare-package.sh /media/$USER/MY_USB/dgx-package
```

The script:
1. Snapshots the repo via `git archive HEAD` into `dgx-package/repo/`
2. Copies the bundled `observations_.csv` and `satelliteData_Full.csv` into
   `dgx-package/seed_data/`
3. Cross-builds `local/sda-tap-spoc-backend:dgx` and
   `local/sda-tap-spoc-frontend:dgx` for `linux/arm64` (slow under qemu —
   30+ minutes the first time)
4. Saves both images via `docker save` to `dgx-package/images/*.tar`
5. Copies `.env.dgx.example` to `dgx-package/env/.env.dgx`

**Edit `dgx-package/env/.env.dgx` and fill in the service-account `UDL_TOKEN`
before burning the drive.** This is the only operator-set value.

Expected total package size: ~3-4 GB (mostly the docker images + ~143 MB seed
CSVs). Fits comfortably on any modern thumb drive.

Copy the directory to the drive and eject:

```bash
cp -r dgx-package /media/$USER/MY_USB/
sync && udisksctl unmount -b /dev/sdX1
```

### Step 2 — On the DGX Spark: install from USB

1. Boot Ubuntu, log in as `dmr` (or whichever user the box ships under).
2. Plug in the thumb drive. Ubuntu auto-mounts it under `/media/dmr/MY_USB/`.
3. Open a terminal:

   ```bash
   cd /media/dmr/MY_USB/dgx-package
   ./install-on-spark.sh
   ```

   The install script:
   - Copies the source tree to `~/dmr-dgx/`
   - Loads the docker images (`docker load -i images/*.tar`)
   - Copies the seed CSVs into `combined/deploy/dgx-spark/seed_data/`
   - Drops the pre-filled `.env.dgx` into place
   - Installs the `.desktop` launcher and `systemd --user` unit
   - Runs `start-dgx.sh` to bring everything up

4. Wait for the browser tab to open at `http://localhost`.

5. Eject the thumb drive — the Spark is now self-contained. Save the drive
   for the next box.

### Step 3 — Acceptance test on the prepared Spark

The full run-book is in `staged-shimmying-feigenbaum.md` under "Verification
(end-to-end)". Quick version:

1. Open `http://localhost` — landing page should show the **"Running locally
   on NVIDIA DGX Spark"** badge.
2. Browse to **Datasets**, confirm `DGX_SEED_SAMPLE` is listed.
3. Open it, verify the 3D Cesium viewer renders with the bundled NaturalEarthII
   imagery (no network calls to `*.cesium.com`).
4. Upload a sample UCTP JSON, watch the job score.
5. Unplug the network cable, reload — everything still works from cache.
6. Plug it back in, generate a fresh dataset — UDL pull works.
7. Power off, box the Spark, deliver to project manager.

> **Warning:** never use `docker compose down -v` — the `-v` flag deletes the named
> volumes that hold the DuckDB file and the seed data. Doing so will wipe everything
> the app has stored.

## Pre-flight: ARM64 dependency verification (M0 — completed 2026-04-07)

Before doing any work, we verified that all dependencies in `combined/pyproject.toml`
have working ARM64 wheels on PyPI for cp312 (Python 3.12). The check method:
fetch each package's `https://pypi.org/simple/<name>/` index and grep for `aarch64`.

| Package | Version | ARM64 wheel? | Notes |
|---|---|---|---|
| `orekit-jpype` | 13.1.2.1 | ✅ Pure Python (`py3-none-any.whl`) | Bridges to Java via JPype; no native code in the package itself |
| `jpype1` | 1.5.2 | ✅ `jpype1-1.5.2-cp312-cp312-manylinux_2_17_aarch64.manylinux2014_aarch64.whl` | The actual native bridge to the JVM |
| `psycopg2-binary` | 2.9.9+ | ✅ `psycopg2_binary-2.9.9-cp312-cp312-manylinux_2_17_aarch64.manylinux2014_aarch64.whl` | Kept as-is — DO NOT swap to psycopg3, the production code at `uct_benchmark/database/adapters/postgres_adapter.py` directly imports `psycopg2`/`psycopg2.extras` and the swap risks breaking Railway |
| `numpy`, `scipy`, `pandas` | latest | ✅ Standard ARM64 wheels | |
| `pyarrow` | 22.0.0+ | ✅ Standard ARM64 wheels | |
| `polars` | 1.35.1+ | ✅ Standard ARM64 wheels | |
| `cryptography` | 41.0.0+ | ✅ Rust-based, ARM64 wheels available | |
| `duckdb` | 1.0.0+ | ✅ Standard ARM64 wheels | **But:** `duckdb` is currently in `[project.optional-dependencies] dev` — see "duckdb dependency note" below |
| `customtkinter` | 5.2.2+ | n/a | **Unused in code.** Verified via `grep -r "import customtkinter\|from customtkinter" combined/uct_benchmark combined/backend_api` — zero hits. Moved to `[project.optional-dependencies] desktop` group as part of M0 cleanup so it doesn't pull Tk into the DGX image. |

### duckdb dependency note

DuckDB is the **default** database backend (`backend_api/database.py:28`) but it lives
in the `dev` extras group, not core dependencies. The existing `Dockerfile.demo`
sidesteps this by `pip install duckdb` separately. For the DGX build we add a
`local-dgx` optional-dependency group containing `duckdb` so the install command is
`pip install ".[local-dgx]"`.

### JVM heap

`combined/Dockerfile` sets `JAVA_TOOL_OPTIONS="-Xmx256m"` (sized for Railway's 512 MB
containers). The Spark has ~128 GB unified memory. Override to `-Xmx2g` in
`.env.dgx.example` only — do **not** edit the Dockerfile default (would slow Railway).

### CORS / `/docs`

`backend_api/main.py:184` reads `_is_production = bool(os.getenv("CORS_ORIGINS"))` and
disables `/docs`, `/redoc`, `/openapi.json` in production. For the DGX build we leave
`CORS_ORIGINS` **unset** in `.env.dgx.example` so the API docs UI remains available
(handy for demo Q&A and debugging from the box itself).

### Background jobs

`backend_api/jobs/workers.py` uses a `ThreadPoolExecutor` with in-process state. The
job manager persists committed state to DuckDB, but jobs *in flight* at the moment of a
container restart will be marked stale. Acceptable for a single-box demo.

### CSP / nginx

`combined/frontend/nginx.conf:19` whitelists `https://*.cesium.com` and
`https://*.up.railway.app` in `connect-src`. These are vestigial for the DGX build but
harmless (won't break offline mode).

## Implementation milestones (this directory)

- **M0** Pre-flight verification — *complete* (this README)
- **M1** Local DEMO_MODE smoke test (no Docker)
- **M2** Seed loader (`backend_api/seed/seed_database.py`)
- **M3** Offline-cache wrapper for UDL/ESA (`uct_benchmark/api/apiIntegration.py`)
- **M4** Cesium offline mode (`frontend/src/components/cesium/OrbitViewer.tsx`)
- **M5** Compose stack (`docker-compose.dgx.yml`, `.env.dgx.example`)
- **M6** Multi-arch buildx verification
- **M7** First-boot polish (`start-dgx.sh`, `.desktop`, systemd unit)
- **M8** On-Spark integration test (requires hardware)

See `C:\Users\kelvi\.claude\plans\staged-shimmying-feigenbaum.md` for the full plan.
