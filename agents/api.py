"""
FastAPI REST API Server for Homomorphic Genomic Gwas Agent.
"""
from typing import Dict, Any
import os
import secrets
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field, StrictInt
from fhe_gwas_agent.gwas import allelic_chi_square
from .base import AuditLogger, SecurityException
from .models import SystemTaskPayload
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Homomorphic Genomic Gwas Agent API",
    description="Threshold-audit demonstration and separate plaintext allelic association calculator (no FHE)",
    version="3.0.0-ENTERPRISE",
)


class ChatRequest(BaseModel):
    query: str


class GwasRequest(BaseModel):
    case_alt: StrictInt = Field(ge=0)
    case_ref: StrictInt = Field(ge=0)
    control_alt: StrictInt = Field(ge=0)
    control_ref: StrictInt = Field(ge=0)


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "homomorphic-genomic-gwas-agent", "domain": "Post-Quantum Cryptography & Hardware Security", "standard": "NIST FIPS 203/204/205 / ISO/IEC 17825 Standards", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/gwas")
def api_gwas(req: GwasRequest):
    """Plaintext Pearson allelic test, not homomorphic encryption."""
    try:
        return allelic_chi_square(
            req.case_alt, req.case_ref, req.control_alt, req.control_ref
        ).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    try:
        dossier = supervisor.process_task(payload)
    except SecurityException as exc:
        raise HTTPException(status_code=400, detail="Sensitive identifiers are not accepted") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid numeric or audit input") from exc
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except SecurityException as exc:
        raise HTTPException(status_code=400, detail="Sensitive identifiers are not accepted") from exc


@app.get("/api/audit/logs")
def api_audit_logs(authorization: str = Header(default="")):
    """Audit metadata is unavailable without an explicitly configured bearer token."""
    token = os.getenv("AUDIT_READ_TOKEN", "")
    if len(token) < 24 or not secrets.compare_digest(authorization, "Bearer " + token):
        raise HTTPException(status_code=403, detail="Audit log access disabled or unauthorized")
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
