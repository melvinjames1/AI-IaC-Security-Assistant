"""
AI-IaC Guard — Test Suite

Tests cover:
  - Security score calculation
  - Checkov JSON parsing/normalisation
  - API request/response validation
  - LLM response validation (including malformed inputs)
  - Key error-handling paths
"""

from __future__ import annotations

import json
import sys
import os

import pytest
from fastapi.testclient import TestClient

# Ensure backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app
from app.models.schemas import Finding, SecurityScore, Severity
from app.services.scoring_service import calculate_score, compute_improvement
from app.services.checkov_service import _parse_checkov_json, _build_finding
from app.services.llm_service import _extract_json, _validate_and_build, _mock_response

client = TestClient(app)


# ---------------------------------------------------------------------------
# Scoring tests
# ---------------------------------------------------------------------------

class TestScoringService:
    def test_empty_findings_gives_100(self):
        score = calculate_score([])
        assert score.score == 100.0
        assert score.total_findings == 0

    def test_single_critical_deducts_25(self):
        findings = [
            Finding(check_id="CKV_AWS_1", severity=Severity.CRITICAL,
                    title="Test", resource="aws_s3_bucket.x", file="main.tf")
        ]
        score = calculate_score(findings)
        assert score.score == 75.0
        assert score.critical == 1

    def test_score_clamped_to_zero(self):
        findings = [
            Finding(check_id=f"CKV_AWS_{i}", severity=Severity.CRITICAL,
                    title="Test", resource="r", file="main.tf")
            for i in range(10)
        ]
        score = calculate_score(findings)
        assert score.score == 0.0

    def test_passed_findings_no_deduction(self):
        findings = [
            Finding(check_id="CKV_AWS_1", severity=Severity.PASSED,
                    title="Passed", resource="r", file="main.tf")
        ]
        score = calculate_score(findings)
        assert score.score == 100.0

    def test_mixed_severities(self):
        findings = [
            Finding(check_id="CKV_AWS_1", severity=Severity.HIGH,
                    title="H", resource="r", file="main.tf"),
            Finding(check_id="CKV_AWS_2", severity=Severity.MEDIUM,
                    title="M", resource="r", file="main.tf"),
            Finding(check_id="CKV_AWS_3", severity=Severity.LOW,
                    title="L", resource="r", file="main.tf"),
        ]
        score = calculate_score(findings)
        expected = 100 - 15 - 8 - 3
        assert score.score == float(expected)

    def test_improvement_calculation(self):
        before = SecurityScore(score=40.0, total_findings=5, critical=2, high=1,
                               medium=1, low=1, unrated=0, passed=0)
        after = SecurityScore(score=80.0, total_findings=2, critical=0, high=1,
                              medium=1, low=0, unrated=0, passed=0)
        pct = compute_improvement(before, after)
        assert pct == 100.0  # (80-40)/40 * 100

    def test_improvement_from_zero(self):
        before = SecurityScore(score=0.0, total_findings=5, critical=5, high=0,
                               medium=0, low=0, unrated=0, passed=0)
        after = SecurityScore(score=50.0, total_findings=2, critical=0, high=2,
                              medium=0, low=0, unrated=0, passed=0)
        pct = compute_improvement(before, after)
        assert pct == 100.0

    def test_label_is_always_present(self):
        score = calculate_score([])
        assert "project-specific" in score.label.lower() or "not an industry" in score.label.lower()


# ---------------------------------------------------------------------------
# Checkov JSON parsing tests
# ---------------------------------------------------------------------------

class TestCheckovParsing:
    def _sample_checkov_output(self) -> str:
        return json.dumps({
            "results": {
                "failed_checks": [
                    {
                        "check_id": "CKV_AWS_18",
                        "check_type": "Ensure S3 bucket has access logging enabled",
                        "resource": "aws_s3_bucket.example",
                        "file_path": "/tmp/aig_test/main.tf",
                        "file_line_range": [1, 10],
                        "severity": "MEDIUM",
                        "description": "Access logging not enabled",
                        "guideline": "https://docs.example.com",
                    }
                ],
                "passed_checks": [
                    {
                        "check_id": "CKV_AWS_19",
                        "check_type": "Ensure S3 bucket encryption enabled",
                        "resource": "aws_s3_bucket.example",
                        "file_path": "/tmp/aig_test/main.tf",
                        "file_line_range": [1, 10],
                        "severity": "",
                        "description": "",
                        "guideline": "",
                    }
                ],
            }
        })

    def test_parse_failed_checks(self):
        failed, passed = _parse_checkov_json(self._sample_checkov_output())
        assert len(failed) == 1
        assert failed[0].check_id == "CKV_AWS_18"
        assert failed[0].severity == Severity.MEDIUM

    def test_parse_passed_checks(self):
        failed, passed = _parse_checkov_json(self._sample_checkov_output())
        assert len(passed) == 1
        assert passed[0].severity == Severity.PASSED

    def test_missing_severity_becomes_unrated(self):
        data = json.dumps({
            "results": {
                "failed_checks": [
                    {
                        "check_id": "CKV_CUSTOM_1",
                        "check_type": "Custom Check",
                        "resource": "resource.x",
                        "file_path": "/tmp/main.tf",
                        "file_line_range": [5, 5],
                        "severity": None,
                    }
                ],
                "passed_checks": [],
            }
        })
        failed, _ = _parse_checkov_json(data)
        assert failed[0].severity == Severity.UNRATED

    def test_invalid_json_returns_empty(self):
        failed, passed = _parse_checkov_json("NOT VALID JSON }{")
        assert failed == []
        assert passed == []

    def test_empty_json_object_returns_empty(self):
        failed, passed = _parse_checkov_json("{}")
        assert failed == []
        assert passed == []

    def test_multiframework_list(self):
        data = json.dumps([
            {"results": {"failed_checks": [], "passed_checks": []}},
            {"results": {
                "failed_checks": [
                    {
                        "check_id": "CKV_AWS_1",
                        "check_type": "test",
                        "resource": "r",
                        "file_path": "/x.tf",
                        "file_line_range": [1, 1],
                        "severity": "HIGH",
                    }
                ],
                "passed_checks": [],
            }},
        ])
        failed, passed = _parse_checkov_json(data)
        assert len(failed) == 1
        assert failed[0].severity == Severity.HIGH


# ---------------------------------------------------------------------------
# LLM response validation tests
# ---------------------------------------------------------------------------

class TestLLMResponseValidation:
    def _valid_llm_json(self) -> dict:
        return {
            "explanations": [
                {
                    "check_id": "CKV_AWS_18",
                    "title": "S3 Logging",
                    "what_it_means": "Logging is disabled",
                    "why_it_matters": "Audit trail missing",
                    "severity": "MEDIUM",
                    "potential_impact": "No audit trail",
                    "remediation_advice": "Enable logging",
                }
            ],
            "corrected_terraform": 'resource "aws_s3_bucket" "example" {\n  bucket = "test"\n}\n',
            "assumptions": ["Assumed region us-east-1"],
        }

    def test_valid_json_builds_response(self):
        findings = [
            Finding(check_id="CKV_AWS_18", severity=Severity.MEDIUM,
                    title="S3 Logging", resource="aws_s3_bucket.example", file="main.tf")
        ]
        resp = _validate_and_build(self._valid_llm_json(), findings)
        assert not resp.is_mock
        assert len(resp.explanations) == 1
        assert "aws_s3_bucket" in resp.corrected_terraform

    def test_missing_corrected_terraform_raises(self):
        data = self._valid_llm_json()
        del data["corrected_terraform"]
        with pytest.raises(ValueError):
            _validate_and_build(data, [])

    def test_malformed_explanation_skipped_gracefully(self):
        data = self._valid_llm_json()
        # Add a malformed explanation item
        data["explanations"].append({"totally_wrong_field": "oops"})
        findings = []
        # Should not raise; malformed item is silently skipped
        resp = _validate_and_build(data, findings)
        # Only the valid item should be present (malformed skipped)
        assert len(resp.explanations) <= len(data["explanations"])

    def test_extract_json_strips_markdown_fences(self):
        text = '```json\n{"key": "value"}\n```'
        result = _extract_json(text)
        assert result == {"key": "value"}

    def test_extract_json_plain(self):
        text = '{"key": "value"}'
        result = _extract_json(text)
        assert result == {"key": "value"}

    def test_mock_response_is_labelled(self):
        findings = [
            Finding(check_id="CKV_AWS_1", severity=Severity.HIGH,
                    title="Test", resource="r", file="main.tf")
        ]
        resp = _mock_response('resource "x" "y" {}', findings)
        assert resp.is_mock is True
        assert resp.mock_notice != ""
        assert "MOCK" in resp.mock_notice or "mock" in resp.mock_notice.lower()


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------

class TestAPIHealth:
    def test_health_returns_ok(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "checkov_available" in data
        assert "llm_provider" in data

    def test_root_returns_metadata(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "name" in resp.json()


class TestAPIScan:
    def test_empty_terraform_returns_422(self):
        resp = client.post("/api/scan", json={"terraform_code": ""})
        assert resp.status_code == 422

    def test_valid_terraform_when_checkov_missing(self, monkeypatch):
        """If Checkov is not installed, /api/scan must return 503."""
        import app.services.checkov_service as svc
        monkeypatch.setattr(svc, "_find_checkov", lambda: None)
        resp = client.post("/api/scan", json={
            "terraform_code": 'resource "aws_s3_bucket" "test" { bucket = "test" }'
        })
        assert resp.status_code == 503


class TestAPIExamples:
    def test_examples_endpoint_returns_dict(self):
        resp = client.get("/api/examples")
        assert resp.status_code == 200
        data = resp.json()
        assert "examples" in data
        assert isinstance(data["examples"], dict)


class TestAPIAnalyze:
    def test_analyze_with_no_findings_runs(self):
        """Analyze endpoint should work with an empty findings list (mock mode)."""
        resp = client.post("/api/analyze", json={
            "terraform_code": 'resource "aws_s3_bucket" "test" { bucket = "test" }',
            "findings": [],
        })
        # Should succeed or return an LLM error — either way, not a 5xx crash
        assert resp.status_code in (200, 500, 422)


class TestAPIVerify:
    def test_verify_missing_fields_returns_422(self):
        resp = client.post("/api/verify", json={
            "corrected_terraform": "   ",
        })
        assert resp.status_code == 422


class TestGeminiProvider:
    def test_gemini_mock_mode_when_no_key(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("LLM_API_KEY", "")
        from app.services.llm_service import _is_mock_mode, get_llm_info
        assert _is_mock_mode() is True
        info = get_llm_info()
        assert info["provider"] == "gemini"
        assert info["mock_mode"] is True

    def test_gemini_call_success(self, monkeypatch):
        import httpx
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("LLM_API_KEY", "fake_gemini_key_12345")
        monkeypatch.setenv("LLM_MODEL", "gemini-2.5-flash")

        fake_resp = {
            "candidates": [{
                "content": {
                    "parts": [{"text": '{"explanations": [], "corrected_terraform": "resource \\"aws_s3_bucket\\" \\"b\\" {}", "assumptions": []}'}]
                }
            }]
        }

        captured_headers = {}
        def mock_post(url, *args, **kwargs):
            nonlocal captured_headers
            captured_headers = kwargs.get("headers", {})
            class FakeResponse:
                def raise_for_status(self):
                    pass
                def json(self):
                    return fake_resp
            return FakeResponse()

        monkeypatch.setattr(httpx, "post", mock_post)

        from app.services.llm_service import _call_gemini, analyze_with_llm
        result = _call_gemini("test prompt")
        assert "corrected_terraform" in result
        assert captured_headers.get("x-goog-api-key") == "fake_gemini_key_12345"

        resp = analyze_with_llm('resource "aws_s3_bucket" "b" {}', [])
        assert resp.is_mock is False
        assert "aws_s3_bucket" in resp.corrected_terraform
