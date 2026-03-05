"""
FastAPI Main Application
========================

Entry point for the API server. Mounts all route modules
and serves the React frontend build in production.

Run (dev):
    uvicorn api.main:app --reload --port 8000

Run (prod):
    uvicorn api.main:app --host 0.0.0.0 --port 8080
"""

import os
import sys

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes import articles, digest, stocks, papers, earnings, sec, stats, case_studies, logo, radar, patents, chat, podcasts
app = FastAPI(
    title="Quantum Intelligence Hub API",
    description="REST API for the Quantum Intelligence Hub — multi-domain intelligence platform",
    version="0.5.0",
)

# CORS — allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev
        "http://localhost:3000",   # fallback
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API Routes ───────────────────────────────────────────────
app.include_router(articles.router, prefix="/api/articles", tags=["Articles"])
app.include_router(digest.router, prefix="/api/digest", tags=["Digest"])
app.include_router(stocks.router, prefix="/api/stocks", tags=["Stocks"])
app.include_router(papers.router, prefix="/api/papers", tags=["Papers"])
app.include_router(earnings.router, prefix="/api/earnings", tags=["Earnings"])
app.include_router(sec.router, prefix="/api/sec", tags=["SEC Filings"])
app.include_router(stats.router, prefix="/api/stats", tags=["Stats"])
app.include_router(case_studies.router, prefix="/api/case-studies", tags=["Case Studies"])
app.include_router(logo.router, prefix="/api/logo", tags=["Logo"])
app.include_router(radar.router, prefix="/api/radar", tags=["Radar"])
app.include_router(patents.router, prefix="/api/patents", tags=["Patents"])
app.include_router(podcasts.router, prefix="/api/podcasts", tags=["Podcasts"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.5.0"}


# ─── Serve React build in production ─────────────────────────
# If frontend-react/dist exists, serve it as static files
frontend_dist = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend-react",
    "dist",
)
if os.path.isdir(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
