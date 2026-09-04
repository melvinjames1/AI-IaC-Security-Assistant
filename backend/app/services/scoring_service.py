"""
AI-IaC Guard — Security Scoring Service

Computes a 0–100 project-specific score from a list of Checkov findings.

FORMULA (documented here and in README):
-----------------------------------------
Start with a base of 100 points.
Apply deductions per failed finding:
    CRITICAL → -25 points
    HIGH     → -15 points
    MEDIUM   → -8  points
    LOW      → -3  points
    UNRATED  → -5  points   (conservative — we don't know severity)
    INFO     → -1  point
Clamp result to [0, 100].

PASSED findings do not incur any deduction.
If there are zero failing findings the score is 100.

IMPORTANT CAVEAT (always displayed in the UI and README):
    This is a PROJECT-SPECIFIC metric computed solely from Checkov results
    for this particular scan.  It is NOT an industry-standard security rating,
    does NOT account for runtime configuration, network posture, or human
    procedures, and a score of 100 does NOT mean "100% secure."
"""

from __future__ import annotations

from app.models.schemas import Finding, SecurityScore, Severity

# Deduction per failed finding, keyed by severity
SEVERITY_DEDUCTIONS: dict[Severity, int] = {
    Severity.CRITICAL: 25,
    Severity.HIGH:     15,
    Severity.MEDIUM:   8,
    Severity.LOW:      3,
    Severity.UNRATED:  5,
    Severity.INFO:     1,
    Severity.PASSED:   0,  # passed → no deduction
}


def calculate_score(findings: list[Finding]) -> SecurityScore:
    """
    Given a normalised list of Finding objects, return a SecurityScore.
    """
    counts: dict[Severity, int] = {s: 0 for s in Severity}
    total_deduction = 0

    for f in findings:
        counts[f.severity] += 1
        total_deduction += SEVERITY_DEDUCTIONS.get(f.severity, 5)

    raw_score = 100 - total_deduction
    score = max(0.0, min(100.0, float(raw_score)))

    failing = sum(
        counts[s] for s in (Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.UNRATED, Severity.INFO)
    )

    return SecurityScore(
        score=score,
        total_findings=len(findings),
        critical=counts[Severity.CRITICAL],
        high=counts[Severity.HIGH],
        medium=counts[Severity.MEDIUM],
        low=counts[Severity.LOW],
        unrated=counts[Severity.UNRATED],
        passed=counts[Severity.PASSED],
        label="Project-Specific Security Score (not an industry standard)",
    )


def compute_improvement(before: SecurityScore, after: SecurityScore) -> float:
    """
    Returns improvement percentage relative to the before score.
    Positive means the score improved; negative means it regressed.
    """
    if before.score == 0:
        return 100.0 if after.score > 0 else 0.0
    return round(((after.score - before.score) / before.score) * 100, 1)
