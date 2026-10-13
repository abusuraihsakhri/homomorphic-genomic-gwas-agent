"""FastAPI plaintext GWAS endpoint and audit-log access control tests."""
import pytest
from fastapi.testclient import TestClient
from agents.api import app


def test_plaintext_gwas_endpoint():
    client = TestClient(app)
    r = client.post("/api/gwas", json={
        "case_alt": 30, "case_ref": 70, "control_alt": 15, "control_ref": 85
    })
    assert r.status_code == 200, r.text
    assert r.json()["chi_square"] == pytest.approx(6.451612903225806)
    assert r.json()["p_value"] == pytest.approx(0.011085166380602699)


@pytest.mark.parametrize("payload", [
    {"case_alt": -1, "case_ref": 70, "control_alt": 15, "control_ref": 85},
    {"case_alt": True, "case_ref": 70, "control_alt": 15, "control_ref": 85},
    {"case_alt": 0, "case_ref": 0, "control_alt": 15, "control_ref": 85},
])
def test_bad_gwas_input_is_unprocessable(payload):
    assert TestClient(app).post("/api/gwas", json=payload).status_code == 422


def test_audit_trail_requires_secret_token(monkeypatch):
    client = TestClient(app)
    monkeypatch.delenv("AUDIT_READ_TOKEN", raising=False)
    assert client.get("/api/audit/logs").status_code == 403
    token = "secure-sample-token-for-testing-12345678"
    monkeypatch.setenv("AUDIT_READ_TOKEN", token)
    assert client.get("/api/audit/logs", headers={"Authorization": "Bearer wrong"}).status_code == 403
    assert client.get("/api/audit/logs", headers={"Authorization": "Bearer " + token}).status_code == 200
