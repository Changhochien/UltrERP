#!/usr/bin/env python3
"""FastAPI sidecar for Tauri PoC.

Exposes /api/ping and /api/domains endpoints.
Run with: uvicorn main:app --host 0.0.0.0 --port 8000
"""

import sys
import os
from datetime import datetime, timezone

# Ensure this directory is in the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="UltrERP Sidecar", version="0.1.0")

# CORS: allow webview origin during dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/ping")
def ping():
    """Health check endpoint."""
    return {
        "status": "pong",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/domains")
def domains():
    """Returns the list of ERP domain modules."""
    return {
        "domains": ["customers", "invoices", "inventory"],
    }


@app.get("/")
def root():
    return {"service": "UltrERP FastAPI Sidecar", "version": "0.1.0"}


if __name__ == "__main__":
    # Bind to all interfaces so Tauri webview on localhost can reach it
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
