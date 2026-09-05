"""
Security & Validation Tests for homomorphic-genomic-gwas-agent.

Covers path traversal prevention, Prometheus label sanitization,
numeric validation, and audit trail integrity.
"""
import sys
import math
import os
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.base import (
    AuditTrail,
    PHIGuard,
    SecurityException,
    assert_no_phi,
)
from agents.metrics import _sanitize_prometheus_label_value, GLOBAL_METRICS, SystemMetricsCollector
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor
from cli import _safe_resolve_path


# ---------------------------------------------------------------------------
# Path traversal prevention
# ---------------------------------------------------------------------------

class TestPathTraversalPrevention:
    def test_safe_path_within_cwd(self):
        p = _safe_resolve_path("subdir/output.csv")
        assert p is not None

    def test_safe_path_traversal_blocked(self):
        with pytest.raises(ValueError, match="Path traversal"):
            _safe_resolve_path("../../etc/passwd")

    def test_safe_path_absolute_traversal_blocked(self):
        with pytest.raises(ValueError, match="Path traversal"):
            _safe_resolve_path("/etc/passwd")

    def test_safe_path_nonexistent_input_blocked(self):
        with pytest.raises(FileNotFoundError):
            _safe_resolve_path("nonexistent_file_12345.csv", must_exist=True)

    def test_safe_path_existing_file_works(self):
        # Create a temp file inside the working directory (relative path)
        tmp_rel = "_test_temp_file_12345.csv"
        tmp_full = Path.cwd() / tmp_rel
        tmp_full.write_text("dummy")
        try:
            p = _safe_resolve_path(tmp_rel, must_exist=True)
            assert p.exists()
        finally:
            tmp_full.unlink()


# ---------------------------------------------------------------------------
# Prometheus label sanitization
# ---------------------------------------------------------------------------

class TestPrometheusSanitization:
    def test_normal_string_unchanged(self):
        assert _sanitize_prometheus_label_value("homomorphic-genomic-gwas-agent") == "homomorphic-genomic-gwas-agent"

    def test_quote_escaped(self):
        assert _sanitize_prometheus_label_value('value"inject') == 'value\\"inject'

    def test_backslash_escaped(self):
        assert _sanitize_prometheus_label_value("path\\to\\metric") == "path\\\\to\\\\metric"

    def test_newline_replaced(self):
        assert _sanitize_prometheus_label_value("line1\nline2") == "line1 line2"

    def test_cr_replaced(self):
        assert _sanitize_prometheus_label_value("line1\rline2") == "line1 line2"

    def test_export_with_safe_name(self):
        collector = SystemMetricsCollector()
        collector.record_task("ROUTINE", 0.001)
        output = collector.export_prometheus_text()
        assert 'system="homomorphic-genomic-gwas-agent"' in output

    def test_export_with_malicious_name(self):
        collector = SystemMetricsCollector()
        collector.system_name = 'evil"inject="true'
        collector.record_task("ROUTINE", 0.001)
        output = collector.export_prometheus_text()
        # The double-quotes should be escaped with a backslash in the output
        assert '\\"inject' in output
        # The raw quote that would break out of the label value must not appear
        assert '"inject="true"' not in output


# ---------------------------------------------------------------------------
# Numeric validation (NaN / Inf rejection)
# ---------------------------------------------------------------------------

class TestNumericValidation:
    def test_nan_primary_metric_rejected(self):
        supervisor = SystemSupervisor(model_provider="mock")
        payload = SystemTaskPayload(
            task_id="T-NAN",
            target_identifier="KEY-NAN",
            primary_metric=float("nan"),
            secondary_metric=5.0,
        )
        with pytest.raises(ValueError, match="finite"):
            supervisor.process_task(payload)

    def test_inf_secondary_metric_rejected(self):
        supervisor = SystemSupervisor(model_provider="mock")
        payload = SystemTaskPayload(
            task_id="T-INF",
            target_identifier="KEY-INF",
            primary_metric=5.0,
            secondary_metric=float("inf"),
        )
        with pytest.raises(ValueError, match="finite"):
            supervisor.process_task(payload)

    def test_neg_inf_rejected(self):
        supervisor = SystemSupervisor(model_provider="mock")
        payload = SystemTaskPayload(
            task_id="T-NEG-INF",
            target_identifier="KEY-NEG-INF",
            primary_metric=float("-inf"),
            secondary_metric=5.0,
        )
        with pytest.raises(ValueError, match="finite"):
            supervisor.process_task(payload)


# ---------------------------------------------------------------------------
# PHI Guard additional patterns
# ---------------------------------------------------------------------------

class TestPHIGuardExtended:
    def test_ssn_blocked(self):
        with pytest.raises(SecurityException):
            assert_no_phi("Patient SSN: 123-45-6789")

    def test_email_blocked(self):
        with pytest.raises(SecurityException):
            assert_no_phi("Contact patient@hospital.com for followup")

    def test_dob_blocked(self):
        with pytest.raises(SecurityException):
            assert_no_phi("DOB: 01/15/1985")

    def test_clean_text_passes(self):
        assert_no_phi("Genomic specimen KEY-001 analysis complete, no anomalies detected.")

    def test_redact_phi(self):
        redacted = PHIGuard.redact_phi("Patient John Doe, MRN-12345678")
        assert "REDACTED_IDENTIFIER" in redacted
        assert "John Doe" not in redacted


# ---------------------------------------------------------------------------
# Audit trail integrity
# ---------------------------------------------------------------------------

class TestAuditTrailIntegrity:
    def test_empty_trail_is_valid(self):
        trail = AuditTrail(secret_key="test-key-for-unit-tests-1234567890")
        assert trail.verify_integrity() is True

    def test_single_entry_valid(self):
        trail = AuditTrail(secret_key="test-key-for-unit-tests-1234567890")
        trail.log("actor1", "tier1", "EVENT_A", {"x": 1})
        assert trail.verify_integrity() is True

    def test_multiple_entries_valid(self):
        trail = AuditTrail(secret_key="test-key-for-unit-tests-1234567890")
        trail.log("actor1", "tier1", "EVENT_A", {"x": 1})
        trail.log("actor2", "tier2", "EVENT_B", {"y": 2})
        trail.log("actor3", "tier3", "EVENT_C", {"z": 3})
        assert trail.verify_integrity() is True
        assert len(trail.get_trail()) == 3

    def test_tampered_trail_detected(self):
        trail = AuditTrail(secret_key="test-key-for-unit-tests-1234567890")
        trail.log("actor1", "tier1", "EVENT_A", {"x": 1})
        trail.log("actor2", "tier2", "EVENT_B", {"y": 2})
        # Tamper with the prev_hash of the second entry
        trail.logs[1]["prev_hash"] = "TAMPERED_HASH_0000000000000000"
        assert trail.verify_integrity() is False

    def test_short_key_rejected(self):
        with pytest.raises(ValueError, match="at least 16"):
            AuditTrail(secret_key="short")
