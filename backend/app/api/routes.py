"""
AI-IaC Guard — API Routes

Endpoints:
    GET  /api/health   → health check
    POST /api/scan     → run Checkov, return findings + score
    POST /api/analyze  → LLM explanation + corrected Terraform
    POST /api/verify   → re-scan corrected Terraform, before/after comparison
    GET  /api/examples → list bundled vulnerable Terraform examples
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ErrorResponse,
    HealthResponse,
    ScanRequest,
    ScanResponse,
    VerifyRequest,
    VerifyResponse,
)
from app.services.checkov_service import checkov_available, checkov_version
from app.services.llm_service import get_llm_info
from app.services.remediation_service import (
    analyse_terraform,
    scan_terraform,
    verify_remediation,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# Path to the bundled example Terraform files
EXAMPLES_DIR = Path(__file__).resolve().parents[3] / "examples"


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    llm = get_llm_info()
    return HealthResponse(
        status="ok",
        checkov_available=checkov_available(),
        llm_provider=llm["provider"],
        llm_mock_mode=llm["mock_mode"],
    )


# ---------------------------------------------------------------------------
# Examples
# ---------------------------------------------------------------------------

@router.get("/examples")
async def list_examples():
    """Return the names and contents of bundled vulnerable Terraform examples."""
    examples = {}
    if EXAMPLES_DIR.exists():
        for example_dir in sorted(EXAMPLES_DIR.iterdir()):
            tf_file = example_dir / "main.tf"
            if tf_file.exists():
                examples[example_dir.name] = tf_file.read_text(encoding="utf-8")
    return {"examples": examples}


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

@router.post("/scan", response_model=ScanResponse)
async def scan(req: ScanRequest) -> ScanResponse:
    """Run Checkov on the submitted Terraform code."""
    try:
        return scan_terraform(req.terraform_code)
    except RuntimeError as exc:
        # Checkov not installed
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Unexpected error in /api/scan")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during scanning.  Check server logs.",
        )


# ---------------------------------------------------------------------------
# Analyse
# ---------------------------------------------------------------------------

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    """Send Terraform code + findings to the LLM for explanation + remediation."""
    try:
        return analyse_terraform(req.terraform_code, req.findings)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Unexpected error in /api/analyze")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during AI analysis.  Check server logs.",
        )


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------

@router.post("/verify", response_model=VerifyResponse)
async def verify(req: VerifyRequest) -> VerifyResponse:
    """Re-scan AI-corrected Terraform and return before/after comparison."""
    try:
        return verify_remediation(
            req.corrected_terraform,
            req.original_findings,
            req.original_score,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Unexpected error in /api/verify")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during verification.  Check server logs.",
        )
