"""FastAPI app. Run with `uvicorn filingguard.api.main:app`.

One origin serves the read-only results API under `/api` and the dashboard's static export at `/`.
Environment:
- `FILINGGUARD_WEB`: the static export folder (default `web/out`); not mounted if it is missing.
- `FILINGGUARD_LIVE_TARGET`: `1` adds the live target route (`live.py`); off by default.
"""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from filingguard.api.routes import router as results_router


def live_target_enabled() -> bool:
    """True only when `FILINGGUARD_LIVE_TARGET` is exactly `1`."""
    return os.environ.get("FILINGGUARD_LIVE_TARGET", "0").strip() == "1"


def web_dir() -> Path:
    """The static export folder served at `/`."""
    return Path(os.environ.get("FILINGGUARD_WEB", "web/out"))


def create_app(live_target: bool | None = None, static_dir: Path | None = None) -> FastAPI:
    """Build the app. Arguments override the environment (used by tests)."""
    app = FastAPI(title="FilingGuard")
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.include_router(results_router)
    if live_target_enabled() if live_target is None else live_target:
        from filingguard.api.live import router as live_router

        app.include_router(live_router)

    @app.get("/api/health")
    def health() -> dict:
        """Liveness check for a local run (the Docker image)."""
        return {"status": "ok"}

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
    def api_not_found(path: str) -> None:
        """Unknown API paths get a JSON 404, never a page from the export."""
        raise HTTPException(status_code=404, detail=f"no API route /api/{path}")

    static = web_dir() if static_dir is None else static_dir
    if static.is_dir():
        app.mount("/", StaticFiles(directory=static, html=True), name="web")
    return app


app = create_app()
