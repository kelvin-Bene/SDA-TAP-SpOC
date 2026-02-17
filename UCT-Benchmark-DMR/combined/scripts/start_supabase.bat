@echo off
REM SECURITY: Do NOT hardcode credentials here. Use .env file or set environment variables.
REM
REM Before running this script, set DATABASE_URL in your environment or .env file:
REM   set DATABASE_URL=postgresql://postgres.[PROJECT_REF]:[YOUR_PASSWORD]@aws-0-us-west-2.pooler.supabase.com:5432/postgres
REM
REM Or create a .env file in the project root with:
REM   DATABASE_URL=postgresql://...

set DATABASE_BACKEND=postgres

REM Check if DATABASE_URL is set
if "%DATABASE_URL%"=="" (
    echo ERROR: DATABASE_URL environment variable is not set.
    echo Please set it before running this script:
    echo   set DATABASE_URL=postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-us-west-2.pooler.supabase.com:5432/postgres
    exit /b 1
)

set DATABASE_POOL_MIN=2
set DATABASE_POOL_MAX=10
cd /d C:\Users\kelvi\desktop\dmr\UCT-Benchmark-DMR\combined
.venv\Scripts\python.exe -m uvicorn backend_api.main:app --reload --port 8000
