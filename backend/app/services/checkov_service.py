"""
AI-IaC Guard — Checkov Integration Service

Executes Checkov as a subprocess against a temporary Terraform directory,
parses the machine-readable JSON output, and normalises every result into
the internal Finding model.

Architecture:
    Terraform code → terraform_tempdir() context manager
                   → checkov subprocess (fixed arg set, JSON output)
                   → parse JSON → list[Finding]

Security notes:
  • Checkov is invoked with a fixed argument list — user input is NEVER
    interpolated into a shell command string.
  • The temp directory is always cleaned up by the context manager.
  • Checkov output is parsed from JSON, never from terminal text.
  • stderr from Checkov is captured and discarded (never forwarded raw).
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from app.models.schemas import Finding, Severity
from app.utils.file_utils import terraform_tempdir

logger = logging.getLogger(__name__)

# Timeout (seconds) for a single Checkov invocation
CHECKOV_TIMEOUT = 120

# Mapping from Checkov severity strings to internal Severity enum
_SEVERITY_MAP: dict[str, Severity] = {
    "CRITICAL": Severity.CRITICAL,
    "HIGH":     Severity.HIGH,
    "MEDIUM":   Severity.MEDIUM,
    "LOW":      Severity.LOW,
    "INFO":     Severity.INFO,
}


def _find_checkov() -> Optional[str]:
    """Return the path to the checkov binary, or None if not installed."""
    return shutil.which("checkov")


def checkov_available() -> bool:
    return _find_checkov() is not None


def checkov_version() -> str:
    """Return checkov version string, or empty string if unavailable."""
    bin_path = _find_checkov()
    if not bin_path:
        return ""
    try:
        result = subprocess.run(
            [bin_path, "--version"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() or result.stderr.strip()
    except Exception:
        return ""


def _parse_severity(raw: str) -> Severity:
    if not raw:
        return Severity.UNRATED
    return _SEVERITY_MAP.get(raw.upper(), Severity.UNRATED)


def _normalize_result(check: dict, relative_file: str) -> Finding:
    """Convert a single Checkov result dict into a Finding."""
    check_id = check.get("check_id", "UNKNOWN")
    check_type = check.get("check_type", "")

    # Checkov result_configuration has file info
    file_abs = check.get("file_path", relative_file)
    # We only show the base filename for cleanliness
    file_display = Path(file_abs).name if file_abs else relative_file

    # Line range
    file_line_range = check.get("file_line_range", [None, None])
    line_num = file_line_range[0] if file_line_range else None

    # Severity: may come from check_result_evaluated.severity or check.severity
    raw_sev = (
        check.get("severity")
        or check.get("check_result", {}).get("result", "")
    )
    severity = _parse_severity(str(raw_sev)) if raw_sev else Severity.UNRATED

    return Finding(
        check_id=check_id,
        severity=severity,
        title=check.get("check_type", check_id),  # filled better below
        resource=check.get("resource", ""),
        file=file_display,
        line=line_num,
        description=check.get("description", ""),
        guideline=check.get("guideline", ""),
    )


def _parse_checkov_json(raw_json: str, tf_filename: str = "main.tf") -> tuple[list[Finding], list[Finding]]:
    """
    Parse Checkov's JSON output (--output json).

    Returns (failed_findings, passed_findings).
    Handles both single-framework dicts and multi-framework lists.
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        logger.warning("Checkov JSON parse error: %s", exc)
        return [], []

    # Checkov can return a list (multi-framework) or a single dict
    if isinstance(data, list):
        results = data
    else:
        results = [data]

    failed: list[Finding] = []
    passed: list[Finding] = []

    for framework_result in results:
        if not isinstance(framework_result, dict):
            continue

        checks = framework_result.get("results", {})

        # ---- FAILED checks ------------------------------------------------
        for check in checks.get("failed_checks", []):
            f = _build_finding(check, Severity.UNRATED)
            failed.append(f)

        # ---- PASSED checks ------------------------------------------------
        for check in checks.get("passed_checks", []):
            f = _build_finding(check, Severity.PASSED)
            passed.append(f)

    return failed, passed


def _build_finding(check: dict, default_severity: Severity) -> Finding:
    """Build a Finding from a Checkov check dict."""
    check_id = check.get("check_id", "UNKNOWN")

    file_abs = check.get("file_path", "main.tf")
    file_display = Path(file_abs).name

    file_line_range = check.get("file_line_range") or [None, None]
    line_num = file_line_range[0] if file_line_range else None

    # Severity can be at the check level or inside check_result
    raw_sev = check.get("severity") or ""
    severity = _parse_severity(str(raw_sev)) if raw_sev else default_severity

    title = check.get("check_name") or check.get("check_type") or check.get("check_id") or check_id
    check_name = str(title) if title else check_id

    return Finding(
        check_id=check_id,
        severity=severity,
        title=check_name,
        resource=check.get("resource") or "",
        file=file_display or "main.tf",
        line=line_num,
        description=check.get("description") or "",
        guideline=check.get("guideline") or "",
    )


def run_checkov(terraform_code: str) -> tuple[list[Finding], list[Finding], str]:
    """
    Main entry point.  Runs Checkov against the given Terraform code.

    Returns:
        (failed_findings, passed_findings, checkov_version_str)

    Raises:
        RuntimeError if Checkov is not installed.
        ValueError  if Terraform input is invalid/empty.
        TimeoutError if Checkov exceeds CHECKOV_TIMEOUT seconds.
    """
    bin_path = _find_checkov()
    if not bin_path:
        raise RuntimeError(
            "Checkov is not installed.  Install it with: pip install checkov"
        )

    version = checkov_version()

    with terraform_tempdir(terraform_code) as tmpdir:
        cmd = [
            bin_path,
            "--directory", str(tmpdir),
            "--output", "json",
            "--framework", "terraform",
            "--quiet",
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=CHECKOV_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            raise TimeoutError(
                f"Checkov scan timed out after {CHECKOV_TIMEOUT} seconds."
            )

        stdout = proc.stdout or ""
        stderr = proc.stderr or ""

        # Checkov exits with 1 when there are failures — that is expected
        if proc.returncode not in (0, 1):
            logger.warning("Checkov exited with code %d: %s", proc.returncode, stderr[:500])

        if not stdout.strip():
            # No JSON output — could be Checkov error or no .tf found
            logger.warning("Checkov produced no JSON output. stderr: %s", stderr[:500])
            return [], [], version

        failed, passed = _parse_checkov_json(stdout)
        return failed, passed, version
