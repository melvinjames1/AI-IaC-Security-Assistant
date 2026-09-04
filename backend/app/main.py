"""
AI-IaC Guard — FastAPI Application Entry Point
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env from the project root (two levels up from this file)
_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

from app.api.routes import router  # noqa: E402 (after dotenv load)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

app = FastAPI(
    title="AI-IaC Guard API",
    description=(
        "Generative AI for Automated Infrastructure-as-Code Security.  "
        "Detect → Explain → Remediate → Verify."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow the Vite dev server (default port 5173) and any localhost port during dev.
# In production, restrict this to the actual frontend origin.
origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
)

app.include_router(router)


@app.get("/")
async def root():
    return {
        "name": "AI-IaC Guard API",
        "version": "1.0.0",
        "docs": "/docs",
    }
