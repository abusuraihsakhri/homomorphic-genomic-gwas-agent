"""Regressions for HMAC verification, PHI handling, CSV flags, and provider claims."""
import pytest
from agents.base import AuditTrail, SecurityException
from agents.llm_factory import LLMFactory
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor
from cli import _parse_bool, main


def test_hmac_detects_tampered_last_signature():
    audit = AuditTrail(secret_key="test-key-12345678901234567890")
    audit.log("operator", "tier", "EVENT", {"ok": True})
    assert audit.verify_integrity()
    audit.logs[-1]["current_hash"] = "0" * 64
    assert not audit.verify_integrity()


def test_hmac_detects_changed_event_type():
    audit = AuditTrail(secret_key="test-key-12345678901234567890")
    audit.log("operator", "tier", "EVENT", {"ok": True})
    audit.logs[0]["event_type"] = "REPLACED"
    assert not audit.verify_integrity()


def test_audit_snapshot_is_immutable_from_caller():
    audit = AuditTrail(secret_key="test-key-12345678901234567890")
    entry = audit.log("operator", "tier", "EVENT", {"ok": True})
    entry["event_type"] = "OUTSIDE"
    audit.get_trail()[0]["event_type"] = "OUTSIDE"
    assert audit.verify_integrity()


def test_phi_in_attributes_rejected_without_logging_raw_value(monkeypatch):
    from agents import base
    monkeypatch.setattr(base, "_GLOBAL_AUDIT", AuditTrail("test-key-12345678901234567890"))
    supervisor = SystemSupervisor()
    payload = SystemTaskPayload(task_id="TASK1", target_identifier="KEY1",
        primary_metric=10, attributes={"notes": "patient@example.com"})
    with pytest.raises(SecurityException):
        supervisor.process_task(payload)
    assert "patient@example.com" not in str(base.AuditLogger.get_trail())


@pytest.mark.parametrize("flag,expected", [
    ("false", False), ("FALSE", False), ("0", False), ("no", False),
    ("true", True), (" TRUE ", True), ("1", True), ("yes", True),
    ("", False), (False, False), (True, True)])
def test_flag_parsing(flag, expected):
    assert _parse_bool(flag) is expected


def test_bad_flag_rejected():
    with pytest.raises(ValueError, match="Invalid is_critical_flag"):
        _parse_bool("definitely")


def test_unsupported_llm_provider_is_not_silently_mocked():
    with pytest.raises(ValueError, match="not implemented"):
        LLMFactory.create("openai")


def test_gwas_cli(capsys):
    assert main(["gwas", "--case-alt", "30", "--case-ref", "70",
        "--control-alt", "15", "--control-ref", "85"]) == 0
    assert "chi_square" in capsys.readouterr().out
