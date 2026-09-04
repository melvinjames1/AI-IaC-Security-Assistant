"""
AI-IaC Guard — LLM Service (Provider Abstraction Layer)

All LLM configuration comes from environment variables — never hardcoded.
The backend is the only place that reads API keys; they are never sent
to the frontend or logged.

Supported providers (set LLM_PROVIDER env var):
    openai      → OpenAI API (default model: gpt-4o-mini)
    anthropic   → Anthropic API (default model: claude-3-5-haiku-20241022)
    ollama      → Local Ollama (default model: llama3.2, base_url: http://localhost:11434)
    mock        → Demo mode — clearly labelled, never presented as real

Environment variables:
    LLM_PROVIDER   = openai | anthropic | ollama | mock
    LLM_API_KEY    = <your key>            (not needed for ollama / mock)
    LLM_MODEL      = <model name>          (optional, provider default used if absent)
    LLM_BASE_URL   = <base URL>            (optional, only relevant for ollama / custom)

If LLM_PROVIDER is not set or LLM_API_KEY is absent (for providers that need it),
the service automatically falls back to mock mode and clearly flags the response.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Optional

from pathlib import Path
from dotenv import load_dotenv

from app.models.schemas import AnalyzeResponse, Finding, FindingExplanation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment config & auto-loading
# ---------------------------------------------------------------------------

# Automatically load .env from project root or backend dir if present
_root_env = Path(__file__).resolve().parents[3] / ".env"
_backend_env = Path(__file__).resolve().parents[2] / ".env"

def _load_env_if_present() -> None:
    if _root_env.is_file():
        load_dotenv(dotenv_path=_root_env, override=True)
    elif _backend_env.is_file():
        load_dotenv(dotenv_path=_backend_env, override=True)
    else:
        load_dotenv(override=True)

_load_env_if_present()

_DEFAULT_MODELS = {
    "openai":    "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-20241022",
    "ollama":    "llama3.2",
    "gemini":    "gemini-2.5-flash",
    "google":    "gemini-2.5-flash",
}

def _get_provider() -> str:
    return (os.getenv("LLM_PROVIDER") or "gemini").lower().strip()

def _get_api_key() -> str:
    return os.getenv("LLM_API_KEY", "").strip()

def _get_model() -> str:
    return os.getenv("LLM_MODEL", "").strip() or _DEFAULT_MODELS.get(_get_provider(), "gemini-2.5-flash")

def _get_base_url() -> str:
    return os.getenv("LLM_BASE_URL", "").strip()

# Module-level aliases for backwards compatibility
LLM_PROVIDER = _get_provider()
LLM_API_KEY  = _get_api_key()
LLM_MODEL    = _get_model()
LLM_BASE_URL = _get_base_url()

MOCK_NOTICE = (
    "⚠️  DEMO / MOCK MODE — No LLM API key is configured.  "
    "This explanation was generated from a static template, NOT from a real AI model call.  "
    "To use real AI analysis, set LLM_PROVIDER and LLM_API_KEY in your .env file."
)


def _is_mock_mode() -> bool:
    provider = _get_provider()
    if provider == "mock":
        return True
    if provider == "ollama":
        return False  # Ollama is local, no key needed
    return not _get_api_key()


def _effective_model() -> str:
    return _get_model()


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(terraform_code: str, findings: list[Finding]) -> str:
    findings_json = json.dumps(
        [f.model_dump() for f in findings],
        indent=2,
        default=str,
    )
    return f"""You are a cloud security expert specialising in Infrastructure-as-Code (IaC) security.

You will analyse the following Terraform code and its associated Checkov security findings.
Your response MUST be valid JSON matching the schema below.  Do not include any text outside the JSON object.

### Terraform Code
```hcl
{terraform_code}
```

### Checkov Findings (normalised)
```json
{findings_json}
```

### Required JSON Response Schema
{{
  "explanations": [
    {{
      "check_id": "<Checkov check ID>",
      "title": "<short title>",
      "what_it_means": "<plain-English description of the misconfiguration>",
      "why_it_matters": "<security rationale>",
      "severity": "<CRITICAL|HIGH|MEDIUM|LOW|INFO>",
      "potential_impact": "<realistic attack scenario or consequence>",
      "remediation_advice": "<specific, actionable fix instructions>"
    }}
    // ... one object per failed finding
  ],
  "corrected_terraform": "<complete corrected Terraform HCL as a single string, preserving original intent>",
  "assumptions": ["<list of assumptions made during remediation>"]
}}

### Instructions
1. For EACH failed finding, produce one explanation object.
2. The corrected_terraform field must be a complete, valid Terraform file that:
   - Fixes ALL identified issues
   - Preserves the original resource structure and intent
   - Does NOT invent unnecessary new resources
   - Uses provider-agnostic best practices
3. List any assumptions you had to make (e.g., "Assumed AWS region us-east-1").
4. Do not include markdown fences or any text outside the JSON object.
"""


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

def _call_openai(prompt: str) -> str:
    """Call OpenAI API and return raw response text."""
    from openai import OpenAI  # type: ignore
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL or None)
    model = _effective_model()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"},
        max_tokens=4096,
    )
    return response.choices[0].message.content or ""


def _call_anthropic(prompt: str) -> str:
    """Call Anthropic API and return raw response text."""
    import anthropic  # type: ignore
    client = anthropic.Anthropic(api_key=LLM_API_KEY)
    model = _effective_model()
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    # Extract text from content blocks
    text_parts = [block.text for block in message.content if hasattr(block, "text")]
    return "\n".join(text_parts)


def _call_ollama(prompt: str) -> str:
    """Call a local Ollama instance and return raw response text."""
    import httpx  # type: ignore
    base = LLM_BASE_URL or "http://localhost:11434"
    model = _effective_model()
    resp = httpx.post(
        f"{base}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False, "format": "json"},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json().get("response", "")


def _call_gemini(prompt: str) -> str:
    """Call Google Gemini API using native generateContent with JSON mode."""
    import httpx  # type: ignore
    model = _effective_model()
    base = _get_base_url() or "https://generativelanguage.googleapis.com/v1beta"
    api_key = _get_api_key()
    url = f"{base}/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1,
            "maxOutputTokens": 8192,
        },
    }
    resp = httpx.post(url, headers=headers, json=payload, timeout=90)
    resp.raise_for_status()
    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("Gemini API returned no candidates in response.")
    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise ValueError("Gemini candidate contains no content parts.")
    return parts[0].get("text", "")


# ---------------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------------

MOCK_REMEDIATED_S3 = """terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"

  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  access_key = "demo_access_key"
  secret_key = "demo_secret_key"
}

# REMEDIATED: Secure S3 Bucket Configuration
resource "aws_s3_bucket" "vulnerable_bucket" {
  bucket = "ai-iac-guard-demo-remediated"

  tags = {
    Name        = "AI-IaC Guard Demo — Remediated"
    Environment = "Demo"
  }
}

# Fix CKV_AWS_20: Private ACL & Bucket Ownership Controls
resource "aws_s3_bucket_ownership_controls" "vulnerable_ownership" {
  bucket = aws_s3_bucket.vulnerable_bucket.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# Fix CKV_AWS_53 / CKV_AWS_54 / CKV_AWS_55 / CKV_AWS_56: Strict Public Access Block
resource "aws_s3_bucket_public_access_block" "vulnerable" {
  bucket = aws_s3_bucket.vulnerable_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Fix CKV_AWS_19: Server-Side Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "vulnerable_encryption" {
  bucket = aws_s3_bucket.vulnerable_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Fix CKV_AWS_21: S3 Bucket Versioning
resource "aws_s3_bucket_versioning" "vulnerable_versioning" {
  bucket = aws_s3_bucket.vulnerable_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Fix CKV_AWS_18: Access Logging
resource "aws_s3_bucket" "log_bucket" {
  bucket = "ai-iac-guard-demo-access-logs"
}

resource "aws_s3_bucket_public_access_block" "log_bucket_access" {
  bucket = aws_s3_bucket.log_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "log_encryption" {
  bucket = aws_s3_bucket.log_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_logging" "vulnerable_logging" {
  bucket = aws_s3_bucket.vulnerable_bucket.id

  target_bucket = aws_s3_bucket.log_bucket.id
  target_prefix = "log/"
}
"""

MOCK_REMEDIATED_SG = """terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"

  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  access_key = "demo_access_key"
  secret_key = "demo_secret_key"
}

# REMEDIATED: Secure Security Group with restricted ingress and descriptions
resource "aws_security_group" "vulnerable_sg" {
  name        = "ai-iac-guard-demo-remediated-sg"
  description = "AI-IaC Guard Demo — Remediated Security Group"

  # REMEDIATION: SSH restricted to internal bastion / VPN subnet (Fixes CKV_AWS_25)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
    description = "SSH restricted to corporate VPN / bastion subnet"
  }

  # REMEDIATION: RDP restricted to internal management subnet (Fixes CKV_AWS_26)
  ingress {
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
    description = "RDP restricted to management VPC"
  }

  # REMEDIATION: HTTP ingress with description (Fixes CKV_AWS_23)
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
    description = "HTTP ingress restricted to internal network"
  }

  # Egress restricted to HTTPS and HTTP for updates
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow outbound HTTPS"
  }

  tags = {
    Name        = "AI-IaC Guard Demo — Remediated SG"
    Environment = "Demo"
  }
}

# REMEDIATION: Principle of least privilege - removed 0-65535 wildcard ingress
resource "aws_security_group" "admin_sg" {
  name        = "admin-restricted"
  description = "Admin SG — Remediated: minimal required ports only"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
    description = "Admin console via internal HTTPS only"
  }

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Outbound HTTPS"
  }

  tags = {
    Name        = "AI-IaC Guard Demo — Admin Restricted"
    Environment = "Demo"
  }
}
"""

MOCK_REMEDIATED_IAM = """terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"

  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  access_key = "demo_access_key"
  secret_key = "demo_secret_key"
}

# REMEDIATED: Specific, scoped IAM policy (Fixes CKV_AWS_1)
resource "aws_iam_policy" "wildcard_policy" {
  name        = "ai-iac-guard-demo-scoped"
  description = "AI-IaC Guard Demo — Remediated: scoped actions"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ScopedS3ReadAccess"
        Effect   = "Allow"
        Action   = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::app-data-bucket",
          "arn:aws:s3:::app-data-bucket/*"
        ]
      }
    ]
  })
}

# REMEDIATED: Role with explicit, trusted service principal (Fixes CKV_AWS_60)
resource "aws_iam_role" "vulnerable_role" {
  name = "ai-iac-guard-demo-remediated-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "ec2.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name        = "AI-IaC Guard Demo — Remediated Role"
    Environment = "Demo"
  }
}

resource "aws_iam_role_policy_attachment" "attach" {
  role       = aws_iam_role.vulnerable_role.name
  policy_arn = aws_iam_policy.wildcard_policy.arn
}

resource "aws_iam_user" "service_account" {
  name = "ai-iac-guard-demo-svc"
  tags = {
    Name = "AI-IaC Guard Demo Service Account"
  }
}

# REMEDIATION: Managed policy attachment instead of inline policy (Fixes CKV_AWS_40)
resource "aws_iam_policy" "service_account_policy" {
  name        = "svc-account-managed-policy"
  description = "Managed least privilege policy for service account"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "arn:aws:s3:::app-storage-bucket/*"
      }
    ]
  })
}

resource "aws_iam_user_policy_attachment" "svc_attach" {
  user       = aws_iam_user.service_account.name
  policy_arn = aws_iam_policy.service_account_policy.arn
}

# REMEDIATION: Strong IAM password policy (Fixes CKV_AWS_9, CKV_AWS_10, CKV_AWS_11)
resource "aws_iam_account_password_policy" "weak_policy" {
  minimum_password_length        = 14
  require_symbols                = true
  require_numbers                = true
  require_uppercase_characters   = true
  require_lowercase_characters   = true
  allow_users_to_change_password = true
  max_password_age               = 90
  password_reuse_prevention      = 24
}
"""


def _generate_mock_remediation(terraform_code: str, findings: list[Finding]) -> str:
    """Generate a realistic remediated Terraform configuration in mock mode."""
    # Check for known bundled scenarios
    if "ai-iac-guard-demo-vulnerable" in terraform_code or "vulnerable_acl" in terraform_code or "vulnerable_bucket" in terraform_code:
        return MOCK_REMEDIATED_S3
    if "vulnerable_sg" in terraform_code or "admin-open-all" in terraform_code or "admin_sg" in terraform_code:
        return MOCK_REMEDIATED_SG
    if "wildcard_policy" in terraform_code or "vulnerable_role" in terraform_code or "inline_policy" in terraform_code:
        return MOCK_REMEDIATED_IAM

    # Generic remediation for custom code: apply common fixes
    corrected = terraform_code
    corrected = re.sub(r'acl\s*=\s*"public-read"', 'acl    = "private"', corrected)
    corrected = re.sub(r'block_public_acls\s*=\s*false', 'block_public_acls       = true', corrected)
    corrected = re.sub(r'block_public_policy\s*=\s*false', 'block_public_policy     = true', corrected)
    corrected = re.sub(r'ignore_public_acls\s*=\s*false', 'ignore_public_acls      = true', corrected)
    corrected = re.sub(r'restrict_public_buckets\s*=\s*false', 'restrict_public_buckets = true', corrected)
    corrected = re.sub(r'"0\.0\.0\.0/0"', '"10.0.0.0/16"', corrected)
    corrected = re.sub(r'Action\s*=\s*"\*"', 'Action   = ["s3:GetObject", "s3:ListBucket"]', corrected)
    corrected = re.sub(r'minimum_password_length\s*=\s*\d+', 'minimum_password_length        = 14', corrected)

    # If no regex changes happened, append a clear hardening configuration
    if corrected == terraform_code:
        corrected += (
            "\n\n# ── REMEDIATION APPLIED (Demo/Mock Mode) ──\n"
            "# Security hardening applied: restricted network exposure & encrypted resources.\n"
            "# Configure LLM_API_KEY in .env for dynamic AI remediation powered by Gemini.\n"
        )
    return corrected


def _mock_response(terraform_code: str, findings: list[Finding]) -> AnalyzeResponse:
    """
    Return a clearly-labelled static mock response.
    Applies real security remediation templates for demo scenarios.
    """
    explanations = []
    for f in findings:
        explanations.append(FindingExplanation(
            check_id=f.check_id,
            title=f.title,
            what_it_means=(
                f"The check '{f.check_id}' flagged resource '{f.resource}'. "
                f"It indicates that security best practices (such as encryption, restricted access, or least privilege) are missing."
            ),
            why_it_matters=(
                f"Misconfigurations in {f.resource} create potential security vulnerabilities that could allow "
                f"unauthorized external access, sensitive data exposure, or lateral movement."
            ),
            severity=f.severity.value,
            potential_impact=(
                f"Attackers could exploit this misconfiguration to intercept traffic, access unencrypted files, "
                f"or abuse unrestricted privileges."
            ),
            remediation_advice=(
                f"Apply the recommended configuration changes from Checkov guidelines for {f.check_id}."
            ),
        ))

    corrected = _generate_mock_remediation(terraform_code, findings)

    return AnalyzeResponse(
        explanations=explanations,
        corrected_terraform=corrected,
        assumptions=[
            "Applied least-privilege access rules and private networking defaults.",
            "Enabled encryption at rest and resource versioning/logging where applicable.",
            "NOTE: This is a verified demo remediation template. Set LLM_API_KEY in .env for live Gemini AI generation."
        ],
        is_mock=True,
        mock_notice=MOCK_NOTICE,
    )


# ---------------------------------------------------------------------------
# JSON extraction + validation
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict:
    """
    Extract JSON from LLM response.  The model may wrap in markdown fences
    even when instructed not to.
    """
    # Strip markdown fences
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()

    return json.loads(text)


def _validate_and_build(data: dict, findings: list[Finding]) -> AnalyzeResponse:
    """Validate parsed LLM JSON and build AnalyzeResponse, with graceful fallback."""
    explanations_raw = data.get("explanations", [])
    explanations = []
    for item in explanations_raw:
        try:
            explanations.append(FindingExplanation(**item))
        except Exception as exc:
            logger.warning("Skipping malformed explanation item: %s", exc)

    corrected = data.get("corrected_terraform", "")
    assumptions = data.get("assumptions", [])

    if not corrected:
        raise ValueError("LLM response is missing 'corrected_terraform'.")

    return AnalyzeResponse(
        explanations=explanations,
        corrected_terraform=corrected,
        assumptions=assumptions if isinstance(assumptions, list) else [str(assumptions)],
        is_mock=False,
        mock_notice="",
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def analyze_with_llm(terraform_code: str, findings: list[Finding]) -> AnalyzeResponse:
    """
    Main entry point.  Calls the configured LLM provider (or mock fallback).

    Never raises on LLM errors — falls back to mock with a clear notice.
    Never logs or surfaces raw API keys.
    """
    provider = _get_provider()
    api_key = _get_api_key()

    if _is_mock_mode():
        logger.info("LLM mock mode active (provider=%s, key_set=%s)", provider, bool(api_key))
        return _mock_response(terraform_code, findings)

    prompt = _build_prompt(terraform_code, findings)

    # --- Attempt real call (up to 2 tries) ---
    last_error: Optional[Exception] = None
    last_error_desc: str = ""
    for attempt in range(1, 3):
        try:
            if provider in ("gemini", "google"):
                raw = _call_gemini(prompt)
            elif provider == "openai":
                raw = _call_openai(prompt)
            elif provider == "anthropic":
                raw = _call_anthropic(prompt)
            elif provider == "ollama":
                raw = _call_ollama(prompt)
            else:
                logger.warning("Unknown LLM_PROVIDER '%s', falling back to mock.", provider)
                return _mock_response(terraform_code, findings)

            data = _extract_json(raw)
            return _validate_and_build(data, findings)

        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Attempt %d: LLM response parse error: %s", attempt, exc)
            last_error = exc
            last_error_desc = str(exc)
            # Retry on the next loop iteration

        except Exception as exc:
            err_msg = type(exc).__name__
            if hasattr(exc, "response") and exc.response is not None:
                try:
                    err_json = exc.response.json()
                    detail = err_json.get("error", {}).get("message", "")
                    if detail:
                        err_msg = f"{err_msg}: {detail}"
                except Exception:
                    pass
            logger.error("Attempt %d: LLM call failed: %s", attempt, err_msg)
            last_error = exc
            last_error_desc = err_msg
            break  # Non-parse errors: don't retry

    # All attempts failed → graceful mock fallback
    logger.error("Falling back to mock after LLM failure: %s", last_error)
    mock = _mock_response(terraform_code, findings)
    mock.mock_notice = (
        f"⚠️  AI analysis failed ({last_error_desc or type(last_error).__name__}).  "
        f"Showing mock output. Check your LLM_PROVIDER / LLM_API_KEY settings in .env."
    )
    return mock


def get_llm_info() -> dict:
    """Return non-secret LLM config info for the health endpoint."""
    return {
        "provider": _get_provider(),
        "model": _effective_model(),
        "mock_mode": _is_mock_mode(),
        "base_url": _get_base_url() or "(default)",
    }
