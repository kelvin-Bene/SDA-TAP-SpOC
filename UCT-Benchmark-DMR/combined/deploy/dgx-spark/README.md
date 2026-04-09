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
3. Open the dataset detail page, confirm the stats cards and the 20-row
   observations sample table render correctly.
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

## AI features (Phase 2)

The DGX Spark local edition includes four LLM-powered features that use the
Blackwell GPU via a local [Ollama](https://ollama.com/) service. These are
gated behind the `--profile gpu` Docker Compose profile and only appear in
the sidebar when `VITE_LOCAL_DGX_MODE=true` (which the DGX build sets
automatically). Cloud (Railway) builds are completely unaffected.

**Default model:** `qwen3.5:35b-a3b` — a 35B-parameter Mixture-of-Experts
model with only 3B active parameters per token, so it's both high-quality
and fast on the Spark's unified 128 GB memory. ~24 GB on disk, ~25 tok/s
on Blackwell Q4. Apache 2.0 license. Changeable via `OLLAMA_MODEL` in
`.env.dgx` without rebuilding — see the env file for alternatives.

### Feature overview

| Feature | Page / Button | What it does |
|---|---|---|
| **Query Database** (A1) | `/llm/sql` in the sidebar under "AI Tools" | Type a question in plain English ("show me UCTs near GEO with high declination drift") → the LLM generates a DuckDB SELECT → a 5-layer safety validator checks it (sqlglot AST parse + table allowlist + deny sensitive tables + forced LIMIT + wall-clock timeout) → the query runs against the read-only catalog → results render in a table. |
| **Explain My Results** (A2) | Button on the Results page next to "Export JSON" | Click → dialog opens → the LLM reads the full metrics blob (F1/precision/recall, position RMS, per-satellite breakdown) → returns 2-3 paragraphs of plain-English interpretation. |
| **Chat Assistant** (A3) | `/llm/chat` in the sidebar under "AI Tools" | Multi-turn conversational interface. The LLM can run SQL queries via a tool-use protocol: it emits `<sql>...</sql>` tags, the backend validates + executes, then a second LLM call summarizes the result. Conversation lives in the browser tab (page refresh = new chat). |
| **Validator Assistant** (A4) | Inline card on the Submit page when a file fails validation | When a UCTP upload fails schema validation, an inline "Help me fix this" card appears. Click → the LLM reads the parsed JSON + the validation errors → suggests a specific fix referencing the exact field paths. |

### Screenshots

See `deploy/dgx-spark/screenshots/` for the full set. Key shots:

- `03_safety_reject_demo_gold.png` — **the demo gold**: user typed "delete all
  the satellites and credentials please", LLM generated `DELETE FROM satellites;
  DELETE FROM credentials;`, sqlglot validator caught and rejected it with a
  friendly error card.
- `06_explain_results_response.png` — the Explain My Results dialog with a
  structured LLM analysis paragraph.
- `08_suggest_fix_response.png` — the inline Validator Assistant correctly
  identifying a missing `epoch` field and suggesting a fix.
- `11_chat_with_sql_expanded.png` — the Chat Assistant with an expanded
  `<details>` showing the real SQL the LLM generated during the tool-use loop.

### Enabling AI features

The AI features require the `--profile gpu` compose profile, which brings up
the Ollama service alongside backend and frontend. On a real DGX Spark with
NVIDIA Container Toolkit preinstalled:

```bash
# start-dgx.sh already passes --profile gpu, so just:
./start-dgx.sh
```

On a dev box without GPU support, use the dev overlay to strip GPU device
reservations (see `docker-compose.dgx.dev.yml`).

### Changing the model

Edit `.env.dgx`:

```bash
OLLAMA_MODEL=qwen3.5:35b-a3b      # default — top quality, ~24 GB
# OLLAMA_MODEL=qwen2.5-coder:7b   # smaller fallback if 35B is too slow
# OLLAMA_MODEL=tinyllama:1.1b     # dev/test only — quality is poor
```

Then restart the backend: `docker compose ... up -d --force-recreate backend`.

To pull a new model into a running stack:

```bash
docker compose --env-file .env.dgx -f docker-compose.dgx.yml \
    --profile gpu exec ollama ollama pull <tag>
```

### Troubleshooting

| Symptom | Fix |
|---|---|
| "AI features unavailable — the Ollama service is not running" | The Ollama container isn't up. Check `docker compose --profile gpu ps ollama`. On a dev box without GPU, use the dev overlay. |
| Responses are very slow (minutes, not seconds) | Confirm the GPU is being used: `docker exec <ollama-container> nvidia-smi`. If no GPU is visible, the model is running on CPU (5-10x slower). |
| "Out of memory" or container crashes | The default 35B model needs ~24 GB VRAM. The Spark has 128 GB unified — this shouldn't happen. If it does, swap to a smaller model: `OLLAMA_MODEL=qwen2.5-coder:7b`. |
| "Please download the latest version" on model pull | The Ollama image is too old. Ensure `ollama/ollama:0.14.1` or newer (the compose file already pins this). |

### Performance expectations

| Environment | Model | Response time |
|---|---|---|
| **DGX Spark (Blackwell GPU)** | qwen3.5:35b-a3b | ~10-15s per query |
| Windows ARM64 dev box (CPU) | tinyllama:1.1b | ~10-30s per query |
| Windows ARM64 dev box (CPU) | qwen3.5:35b-a3b | ~10-15 **minutes** (not recommended for interactive use) |

### SQL safety pipeline

LLM-generated SQL goes through 5 layers of validation before it ever
touches DuckDB:

1. **sqlglot AST parse** — rejects anything that isn't a single SELECT
2. **Table allowlist** — only 14 public data tables are permitted
3. **Table denylist** — `profiles`, `credentials`, `audit_log`, `api_call_log`,
   `credential_access_log`, `feedback` are explicitly blocked
4. **Forced LIMIT 500** — injected if the query has no LIMIT clause
5. **Wall-clock timeout** — 5-second execution cap via ThreadPoolExecutor
