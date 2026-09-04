"""
AI-IaC Guard — Remediation Service

Orchestrates: scan (Checkov) → analyse (LLM) → return combined result.
Also used for the verify step (re-scan corrected Terraform).
"""

from __future__ import annotations

from app.models.schemas import (
    AnalyzeResponse,
    Finding,
    ScanResponse,
    SecurityScore,
    VerifyResponse,
)
from app.services.checkov_service import run_checkov
from app.services.llm_service import analyze_with_llm
from app.services.scoring_service import calculate_score, compute_improvement


def scan_terraform(terraform_code: str) -> ScanResponse:
    """
    Run Checkov on the given Terraform code and return findings + score.
    """
    failed, passed, version = run_checkov(terraform_code)
    all_findings = failed + passed
    score = calculate_score(failed)  # Score is based only on failures

    return ScanResponse(
        findings=all_findings,
        score=score,
        raw_passed=len(passed),
        checkov_version=version,
    )


def analyse_terraform(
    terraform_code: str,
    findings: list[Finding],
) -> AnalyzeResponse:
    """
    Send Terraform code + findings to the LLM and return explanations +
    corrected code.  Only failed findings (non-PASSED) are sent to LLM.
    """
    failed_findings = [f for f in findings if f.severity.value != "PASSED"]
    return analyze_with_llm(terraform_code, failed_findings)


def verify_remediation(
    corrected_terraform: str,
    original_findings: list[Finding],
    original_score: SecurityScore,
) -> VerifyResponse:
    """
    Re-scan the AI-corrected Terraform, compute new score, and produce
    a before/after comparison.

    The verdict string is deliberately conservative — we never say "100% secure."
    """
    failed, passed, _ = run_checkov(corrected_terraform)
    all_new = failed + passed
    new_score = calculate_score(failed)

    improvement_pct = compute_improvement(original_score, new_score)

    # Count how many original failures are now resolved
    original_failed_ids = {
        f.check_id for f in original_findings if f.severity.value != "PASSED"
    }
    new_failed_ids = {f.check_id for f in failed}
    resolved_count = len(original_failed_ids - new_failed_ids)
    new_issues_count = len(new_failed_ids - original_failed_ids)

    # Honest verdict
    if len(failed) == 0:
        verdict = "Passed all configured Checkov security checks for this scan."
    elif improvement_pct > 0:
        verdict = (
            f"Improvement detected: {improvement_pct:+.1f}% score change.  "
            f"{resolved_count} issue(s) resolved, {len(failed)} remaining."
        )
    elif improvement_pct == 0:
        verdict = (
            f"No score change detected.  {len(failed)} issue(s) remain.  "
            "Review the AI suggestions and consider manual remediation."
        )
    else:
        verdict = (
            f"Score regressed by {abs(improvement_pct):.1f}%.  "
            f"{new_issues_count} new issue(s) introduced.  Review carefully."
        )

    return VerifyResponse(
        new_findings=all_new,
        new_score=new_score,
        original_score=original_score,
        improvement_percentage=improvement_pct,
        resolved_count=resolved_count,
        new_issues_count=new_issues_count,
        verdict=verdict,
    )
