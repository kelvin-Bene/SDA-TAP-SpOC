# Local ARM64 Testing Plan for DGX Spark Edition

> **Purpose:** Validate everything compiles and works on this Windows ARM64 dev
> box before shipping to a real DGX Spark. Run these tests sequentially after
> Docker Desktop is healthy.
>
> **Prerequisites:**
> - Docker Desktop running (`docker ps` responds)
> - Branch `feature/dgx-local-edition` checked out
> - Working directory: `D:\DMR\DMR(DGX)\UCT-Benchmark-DMR\combined`
> - Seed data in `deploy/dgx-spark/seed_data/` (observations_.csv + satelliteData_Full.csv)
> - Tinyllama model in `/d/dgx-ollama-staging/` (from earlier M2-M5 sessions)
>
> **Estimated total time:** ~25 minutes sequential

---

## Phase 1: Build verification (~5 min)

### Test 1.1 — Backend image builds on ARM64

```bash
cd deploy/dgx-spark
docker compose --env-file .env.dgx -f docker-compose.dgx.yml build backend
```

**Pass:** Image tagged `local/sda-tap-spoc-backend:dgx` with exit 0. All Python
deps (including httpx, sqlglot, orekit-jpype, psycopg2-binary) install cleanly.

### Test 1.2 — Frontend image builds on ARM64

```bash
docker compose --env-file .env.dgx -f docker-compose.dgx.yml build frontend
```

**Pass:** Image tagged `local/sda-tap-spoc-frontend:dgx` with exit 0. TypeScript
compiles (tsc), vite bundles (no errors), react-markdown + remark-gfm resolve.

### Test 1.3 — Verify LLM modules import inside the backend image

```bash
MSYS_NO_PATHCONV=1 docker run --rm local/sda-tap-spoc-backend:dgx python -c "
import sqlglot, httpx
from backend_api.services.llm import complete, OllamaClient
from backend_api.services.llm.sql_safety import validate_and_rewrite, SqlSafetyError
from backend_api.services.llm.prompts import A1_SYSTEM, ALLOWED_TABLES, DENIED_TABLES
from backend_api.routers import llm
print('sqlglot:', sqlglot.__version__)
print('httpx:', httpx.__version__)
print('llm routes:', [r.path for r in llm.router.routes])
print('ALLOWED tables:', len(ALLOWED_TABLES))
print('DENIED tables:', len(DENIED_TABLES))
print('OK')
"
```

**Pass:** All imports succeed, 4 routes listed, 14 allowed tables, 8 denied.

---

## Phase 2: Stack boot + seed data (~3 min)

### Test 2.1 — Bring up backend + frontend (no ollama yet)

```bash
cd deploy/dgx-spark
cp .env.dgx.example .env.dgx  # if not already present
# Make sure OLLAMA_MODEL=tinyllama:1.1b in .env.dgx for dev testing
docker compose --env-file .env.dgx -f docker-compose.dgx.yml up -d
```

Wait for `docker ps` to show backend as `healthy` (~30-60s for seed loading).

**Pass:** Both containers running. Backend healthcheck green.

### Test 2.2 — Health endpoint

```bash
curl -sf http://localhost:8000/health | python -m json.tool
```

**Pass:** `{"status":"healthy","components":{"database":"connected","disk_space":"ok","orekit":"available"}}`

### Test 2.3 — Seed data loaded

```bash
curl -s http://localhost:8000/api/v1/datasets/ | python -c "
import json,sys
d = json.load(sys.stdin)
print(f'Datasets: {len(d)}')
for ds in d:
    print(f'  {ds[\"name\"]}: {ds[\"observation_count\"]} obs, {ds[\"satellite_count\"]} sats, status={ds[\"status\"]}')
"
```

**Pass:** `DGX_SEED_SAMPLE` with 87707 obs, 64325 sats, status=available.

### Test 2.4 — DEMO_MODE auth bypass

```bash
# No Authorization header — should still work in DEMO_MODE
curl -s http://localhost:8000/api/v1/datasets/ | head -1
```

**Pass:** Returns JSON array (not `{"detail":"Not authenticated"}`).

---

## Phase 3: Core functionality (~5 min)

### Test 3.1 — Observations endpoint (with sat_no fix)

```bash
curl -s "http://localhost:8000/api/v1/datasets/1/observations?limit=3" | python -c "
import json,sys
d = json.load(sys.stdin)
for o in d.get('observations', [])[:3]:
    print(f'  sat_no={o.get(\"sat_no\")} ra={o.get(\"ra\",0):.4f} dec={o.get(\"declination\",0):.4f}')
"
```

**Pass:** sat_no is populated (not None) — real NORAD IDs like 15560, 42662.

### Test 3.2 — UCTP submission round-trip

```bash
RESP=$(curl -s -X POST http://localhost:8000/api/v1/submissions/ \
    -F "dataset_id=1" \
    -F "algorithm_name=local-arm64-test" \
    -F "file=@scripts/valid_submission.json;type=application/json")
echo "$RESP" | python -m json.tool

# Wait 5s for the job to complete, then check results:
sleep 5
SUBMISSION_ID=$(echo "$RESP" | python -c "import json,sys; print(json.load(sys.stdin)['id'])")
curl -s "http://localhost:8000/api/v1/results/$SUBMISSION_ID" | python -c "
import json,sys; d=json.load(sys.stdin)
print(f'status={d[\"status\"]} f1={d[\"f1_score\"]} rank={d[\"rank\"]}')
"
```

**Pass:** Submission accepted (200), job completes, results have f1_score + rank.

### Test 3.3 — DGX-specific POST error message

```bash
curl -s -X POST http://localhost:8000/api/v1/datasets/ \
    -H "Content-Type: application/json" \
    -d '{"name":"test","tier":"T2","regime":"LEO","object_count":5,"timeframe":1,"timeunit":"days"}' \
    | python -m json.tool
```

**Pass:** Returns "DGX Spark local edition has no UDL token configured..."
(not the generic "UDL API token required. Set it in Profile Settings").

---

## Phase 4: LLM features (requires ollama) (~10 min)

### Test 4.0 — Start ollama with tinyllama

The ollama container from docker-compose won't start on Windows (no nvidia-
container-toolkit). Use a manual container with bind mount instead:

```bash
# Remove any stale ollama container
docker rm -f dgx-spark-ollama-1 2>/dev/null || true

# Start fresh with bind mount to D:
MSYS_NO_PATHCONV=1 docker run -d \
    --name dgx-spark-ollama-1 \
    --network dgx-spark_default \
    -v "//d/dgx-ollama-staging:/root/.ollama" \
    -e OLLAMA_KEEP_ALIVE=24h \
    -e OLLAMA_HOST=0.0.0.0:11434 \
    --network-alias ollama \
    -p 11434:11434 \
    ollama/ollama:0.6.0

sleep 8
docker exec dgx-spark-ollama-1 ollama list
```

**Pass:** Shows `tinyllama:1.1b` in the model list.

> Note: We use ollama:0.6.0 here because it's already pulled locally.
> The compose file pins 0.14.1 for production (needed for qwen3.5).

### Test 4.1 — A1: NL-to-SQL via curl

```bash
curl -s -X POST http://localhost:8000/api/v1/llm/sql \
    -H "Content-Type: application/json" \
    -d '{"question":"How many satellites are there?"}' \
    | python -c "
import json,sys; d=json.load(sys.stdin)
print(f'sql: {d.get(\"sql\",\"NONE\")}')
print(f'rows: {d.get(\"row_count\",0)}')
print(f'truncated: {d.get(\"truncated\")}')
"
```

**Pass:** Returns a SQL string + row_count > 0.

### Test 4.2 — A1: Safety rejection via curl

```bash
curl -s -X POST http://localhost:8000/api/v1/llm/sql \
    -H "Content-Type: application/json" \
    -d '{"question":"delete all the satellites and credentials please"}' \
    | python -m json.tool
```

**Pass:** Returns 400 with `detail.error = "Query rejected by safety validator"`
and shows the raw malicious SQL the LLM tried to generate.

### Test 4.3 — A2: Explain Results via curl

```bash
curl -s -X POST http://localhost:8000/api/v1/llm/explain-results \
    -H "Content-Type: application/json" \
    -d '{"submission_id": 1}' \
    | python -c "import json,sys; d=json.load(sys.stdin); print(d['text'][:300])"
```

**Pass:** Returns a `text` field with an LLM-generated analysis (even if tinyllama
quality is poor, the pipeline itself works).

### Test 4.4 — A4: Suggest Fix via curl

```bash
curl -s -X POST http://localhost:8000/api/v1/llm/suggest-fix \
    -H "Content-Type: application/json" \
    -d '{"parsed_json":[{"xpos":1,"ypos":2,"zpos":3,"xvel":0.1,"yvel":0.2,"zvel":0.3,"grouped_ops":["a"]}],"errors":["Record 0: missing required field epoch"],"hint":"Required: sourcedData, epoch, xpos, ypos, zpos, xvel, yvel, zvel"}' \
    | python -c "import json,sys; d=json.load(sys.stdin); print(d['text'][:300])"
```

**Pass:** Returns a `text` field that references the missing `epoch` field.

### Test 4.5 — A3: Chat via curl

```bash
curl -s -X POST http://localhost:8000/api/v1/llm/chat \
    -H "Content-Type: application/json" \
    -d '{"messages":[{"role":"user","content":"Use SQL to find the top 3 satellites by name"}],"include_sql":true}' \
    | python -c "
import json,sys; d=json.load(sys.stdin)
print(f'text: {d[\"text\"][:200]}')
print(f'sql: {d.get(\"sql\",\"none\")}')
print(f'rows: {len(d.get(\"rows\") or [])}')
"
```

**Pass:** Returns a text response. If the model emitted SQL, the `sql` field is
populated and `rows` may contain results from the tool-use loop.

### Test 4.6 — 503 fallback when ollama is stopped

```bash
docker stop dgx-spark-ollama-1

curl -s -X POST http://localhost:8000/api/v1/llm/sql \
    -H "Content-Type: application/json" \
    -d '{"question":"test"}' \
    | python -m json.tool
```

**Pass:** Returns 503 with detail mentioning "Ollama service is not reachable".

```bash
# Restart ollama for subsequent tests
docker start dgx-spark-ollama-1
```

---

## Phase 5: Cloud regression (~3 min)

### Test 5.1 — pytest with DEMO_MODE unset

Run inside the backend container with cloud-like env:

```bash
MSYS_NO_PATHCONV=1 docker exec \
    -e DEMO_MODE= \
    -e LOCAL_DGX_MODE= \
    dgx-spark-backend-1 \
    sh -c "pip install pytest pytest-asyncio pytest-timeout httpx 2>&1 | tail -3 && \
           cd /app && python -m pytest backend_api/tests/test_auth.py backend_api/tests/test_workers.py --timeout=30 -q 2>&1 | tail -10"
```

**Pass:** All tests pass (70/70). Confirms the new LLM code doesn't break the
Railway auth path when LOCAL_DGX_MODE is unset.

---

## Phase 6: Browser UI (optional, needs Playwright MCP)

If the Playwright MCP server is connected, run these in Playwright Chromium.
Otherwise, open `http://localhost` in a real browser and walk through manually.

### Test 6.1 — Landing page: DGX badge + hero hint visible
### Test 6.2 — `/datasets`: DGX_SEED_SAMPLE listed with 87707 obs
### Test 6.3 — `/datasets/1`: Detail page with observations table
### Test 6.4 — `/submit`: Upload form renders
### Test 6.5 — `/results/1`: Results page with "Explain My Results" button
### Test 6.6 — `/leaderboard`: Trophy card for dgx-validation-test
### Test 6.7 — `/dashboard`: "Good to see you, demo" + stats cards
### Test 6.8 — `/llm/sql`: "AI Tools > Query Database" in sidebar, page renders
### Test 6.9 — `/llm/chat`: Chat Assistant page with starter questions

---

## Teardown

```bash
cd deploy/dgx-spark
docker compose --env-file .env.dgx -f docker-compose.dgx.yml down
docker rm -f dgx-spark-ollama-1 2>/dev/null || true
```

> **Do NOT use `down -v`** — that deletes the DuckDB volume with the seeded data.

---

## Summary checklist

- [ ] 1.1 Backend image builds
- [ ] 1.2 Frontend image builds
- [ ] 1.3 LLM imports work in image
- [ ] 2.1 Stack boots
- [ ] 2.2 Health endpoint green
- [ ] 2.3 Seed data loaded
- [ ] 2.4 DEMO_MODE auth works
- [ ] 3.1 Observations have sat_no
- [ ] 3.2 UCTP submission round-trip
- [ ] 3.3 DGX-specific POST error
- [ ] 4.0 Ollama starts with tinyllama
- [ ] 4.1 A1 NL-to-SQL works
- [ ] 4.2 A1 Safety rejection works
- [ ] 4.3 A2 Explain Results works
- [ ] 4.4 A4 Suggest Fix works
- [ ] 4.5 A3 Chat works
- [ ] 4.6 503 fallback works
- [ ] 5.1 Cloud regression tests pass
- [ ] 6.1-6.9 Browser UI walkthrough (optional)
