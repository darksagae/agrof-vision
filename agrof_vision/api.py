"""HTTP API and static web app."""

from __future__ import annotations

import os
import threading
from pathlib import Path

import cv2
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .pipeline import MAX_BYTES, ImageError, analyze

WEB_DIST = Path(os.getenv("AGROF_WEB_DIST", Path(__file__).resolve().parent.parent / "web" / "dist"))
# Image processing is memory-heavy; cap how many run at once per process.
_slots = threading.BoundedSemaphore(int(os.getenv("AGROF_MAX_CONCURRENT", "4")))

CSP = (
    "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
    "script-src 'self'; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; "
    "frame-ancestors 'none'; form-action 'self'"
)

app = FastAPI(
    title="AGRON Vision", version=__version__, docs_url="/api/docs", openapi_url="/api/openapi.json"
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=()")
    if not request.url.path.startswith("/api/docs"):
        response.headers.setdefault("Content-Security-Policy", CSP)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(ImageError)
async def image_error(_: Request, error: ImageError):
    return JSONResponse({"error": str(error)}, status_code=422)


@app.exception_handler(HTTPException)
async def http_error(_: Request, error: HTTPException):
    return JSONResponse({"error": error.detail}, status_code=error.status_code)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "opencv_version": cv2.__version__}


@app.post("/api/analyze")
def analyze_image(image: UploadFile = File(...)) -> dict:
    # Read one byte past the limit so oversized uploads are rejected without
    # buffering the whole thing.
    raw = image.file.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "Images must be 10 MB or smaller.")
    if not _slots.acquire(timeout=20):
        raise HTTPException(503, "The analyser is busy. Please try again in a moment.")
    try:
        return analyze(raw)
    finally:
        _slots.release()


if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
