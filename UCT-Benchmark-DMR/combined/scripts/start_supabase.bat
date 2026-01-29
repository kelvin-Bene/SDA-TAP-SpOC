@echo off
set DATABASE_BACKEND=postgres
set DATABASE_URL=postgresql://postgres.csuqtcizjfsmkoeevyau:DMRSDATAPLABSPOC@aws-0-us-west-2.pooler.supabase.com:5432/postgres
set DATABASE_POOL_MIN=2
set DATABASE_POOL_MAX=10
cd /d C:\Users\kelvi\desktop\dmr\UCT-Benchmark-DMR\combined
.venv\Scripts\python.exe -m uvicorn backend_api.main:app --reload --port 8000
