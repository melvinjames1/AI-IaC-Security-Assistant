"""
AI-IaC Guard — Pydantic Models / Schemas

All request/response shapes for the FastAPI endpoints.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"
    UNRATED = "UNRATED"
    PASSED = "PASSED"


# ---------------------------------------------------------------------------
# Core domain models
# ---------------------------------------------------------------------------

class Finding(BaseModel):
    """Normalised representation of a single Checkov finding."""
    check_id: str
    severity: Severity = Severity.UNRATED
    title: str = ""
    resource: str = ""
    file: str = "main.tf"
    line: Optional[int] = None
    description: Optional[str] = ""
    guideline: Optional[str] = ""


class SecurityScore(BaseModel):
    """
    Project-specific security score (0–100).
    Formula (documented in scoring_service.py):
        base = 100
        deductions per finding:
            CRITICAL → -25
            HIGH     → -15
            MEDIUM   → -8
            LOW      → -3
            UNRATED  → -5
        score = max(0, base - sum(deductions))
        If no findings exist → score = 100
    This is NOT an industry-standard score.  It is a relative indicator
    computed solely from the Checkov findings for this specific scan.
    """
    score: float = Field(..., ge=0, le=100)
    total_findings: int
    critical: int
    high: int
    medium: int
    low: int
    unrated: int
    passed: int
    label: str = "Project-Specific Security Score (not an industry standard)"


# ---------------------------------------------------------------------------
# API request / response models
# ---------------------------------------------------------------------------

class ScanRequest(BaseModel):
    terraform_code: str = Field(..., min_length=1, max_length=500_000)


class ScanResponse(BaseModel):
    findings: list[Finding]
    score: SecurityScore
    raw_passed: int
    checkov_version: str = ""


class AnalyzeRequest(BaseModel):
    terraform_code: str = Field(..., min_length=1, max_length=500_000)
    findings: list[Finding]


class FindingExplanation(BaseModel):
    check_id: str
    title: str
    what_it_means: str
    why_it_matters: str
    severity: str
    potential_impact: str
    remediation_advice: str


class AnalyzeResponse(BaseModel):
    explanations: list[FindingExplanation]
    corrected_terraform: str
    assumptions: list[str]
    is_mock: bool = False
    mock_notice: str = ""


class VerifyRequest(BaseModel):
    corrected_terraform: str = Field(..., min_length=1, max_length=500_000)
    original_findings: list[Finding]
    original_score: SecurityScore


class VerifyResponse(BaseModel):
    new_findings: list[Finding]
    new_score: SecurityScore
    original_score: SecurityScore
    improvement_percentage: float
    resolved_count: int
    new_issues_count: int
    verdict: str  # e.g. "Passed configured security checks" — never "100% Secure"


class HealthResponse(BaseModel):
    status: str
    checkov_available: bool
    llm_provider: str
    llm_mock_mode: bool
    version: str = "1.0.0"


class ErrorResponse(BaseModel):
    error: str
    detail: str = ""
    code: str = "INTERNAL_ERROR"
