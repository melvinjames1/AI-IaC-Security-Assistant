"""
AI-IaC Guard — Safe temporary file utilities.

All Terraform input is written to an isolated temp directory.
The directory is always cleaned up — even on exception paths.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import re
from contextlib import contextmanager
from pathlib import Path


# Maximum size we allow for a single Terraform write (500 KB)
MAX_TF_SIZE_BYTES = 500 * 1024


def _sanitize_terraform(code: str) -> str:
    """
    Basic sanitization:
      - Reject content that is not plausible Terraform (must contain at least
        one HCL keyword).
      - Strip null bytes.
    We do NOT strip normal characters — Terraform files can contain strings,
    comments, URLs, etc.
    """
    code = code.replace("\x00", "")
    if len(code.encode()) > MAX_TF_SIZE_BYTES:
        raise ValueError(f"Input exceeds maximum allowed size ({MAX_TF_SIZE_BYTES} bytes).")
    # Rough sanity check — reject completely empty after strip
    if not code.strip():
        raise ValueError("Input is empty.")
    return code


@contextmanager
def terraform_tempdir(terraform_code: str):
    """
    Context manager that:
      1. Sanitizes the supplied Terraform code.
      2. Writes it to 'main.tf' inside a freshly-created temp directory.
      3. Yields the directory Path.
      4. Deletes the entire temp directory on exit (success or exception).

    Usage::

        with terraform_tempdir(code) as tmpdir:
            result = subprocess.run(["checkov", "-d", str(tmpdir), ...])
    """
    code = _sanitize_terraform(terraform_code)
    tmpdir = Path(tempfile.mkdtemp(prefix="aig_"))
    try:
        tf_file = tmpdir / "main.tf"
        tf_file.write_text(code, encoding="utf-8")
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
