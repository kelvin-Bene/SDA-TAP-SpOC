"""Railway-compatible startup script."""
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    workers = int(os.environ.get("WEB_WORKERS", "1"))
    uvicorn.run(
        "backend_api.main:app",
        host="0.0.0.0",
        port=port,
        workers=workers,
    )
