# Seed data for the DGX Spark local edition

This directory holds the bundled sample observations that
`backend_api/seed/seed_database.py` loads into an empty DuckDB on first boot.
It is **not committed to Git** because the CSVs total ~143 MB and are
better delivered as a release asset or via `git lfs`.

## What goes here

| File | Source | Approx. size | Required for |
|---|---|---|---|
| `observations_.csv` | reference-code/uct-benchmark-refactor-joncline/src/data/ | 54 MB | observations table seed |
| `satelliteData_Full.csv` | reference-code/uct-benchmark-refactor-joncline/src/data/ | 21 MB | satellites table seed |

The seed loader will silently skip any file that's missing — at minimum,
`observations_.csv` is required for the bundled `DGX_SEED_SAMPLE` dataset to
have any rows.

## Two ways to populate it

### Option A — copy from the existing `kelvinallignment` checkout

If you already have `D:\DMR\DMR(kelvinallignment)\reference-code\uct-benchmark-refactor-joncline\src\data\` on the same machine:

```bash
cp /d/DMR/DMR\(kelvinallignment\)/reference-code/uct-benchmark-refactor-joncline/src/data/observations_.csv .
cp /d/DMR/DMR\(kelvinallignment\)/reference-code/uct-benchmark-refactor-joncline/src/data/satelliteData_Full.csv .
```

(Or `cp -r` the whole folder — the seed loader only reads the two files
it knows about and ignores the rest.)

### Option B — fetch from a release asset

Once we publish a `seed_data.tar.gz` release asset on GitHub:

```bash
# from this directory
curl -L -o seed_data.tar.gz https://github.com/kelvin-Bene/SDA-TAP-SpOC/releases/download/dgx-seed-v1/seed_data.tar.gz
tar -xzf seed_data.tar.gz
rm seed_data.tar.gz
```

(Release does not exist as of this commit — TODO before shipping the box.)

## Verifying the seed loaded

After bringing up the stack with `./start-dgx.sh`:

```bash
docker compose -f docker-compose.dgx.yml exec backend python3 -c "
from backend_api.database import init_database
db = init_database()
print('observations:', db.execute('SELECT COUNT(*) FROM observations').fetchone()[0])
print('satellites:  ', db.execute('SELECT COUNT(*) FROM satellites').fetchone()[0])
print('datasets:    ', db.execute('SELECT COUNT(*) FROM datasets').fetchone()[0])
"
```

Or simply: open `http://localhost` in a browser and look at the Datasets page —
`DGX_SEED_SAMPLE` should appear in the list.
