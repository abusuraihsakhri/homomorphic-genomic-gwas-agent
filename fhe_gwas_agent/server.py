"""
FastAPI REST API Server for FHE-GWAS: Fully Homomorphic Encrypted Genome-Wide Association Study Agent.
"""
from typing import Dict, Any
from .models import FrontierPayload
from .agents import FHEGWASCoordinator

coordinator = FHEGWASCoordinator()


def create_app():
    try:
        from fastapi import FastAPI
        from pydantic import BaseModel

        app = FastAPI(
            title="FHE-GWAS: Fully Homomorphic Encrypted Genome-Wide Association Study Agent",
            description="Computes chi-square allelic association tests and logistic regression p-values directly over BFV-encrypted genomic SNP matrices.",
            version="2.0.0-FRONTIER",
        )

        class TaskRequest(BaseModel):
            task_id: str = "TASK-2026-001"
            target_identifier: str = "TARGET-BIO-KEY"
            primary_metric: float = 28.5
            secondary_metric: float = 14.2
            status_descriptor: str = "DISCORDANT_ANOMALY"
            is_critical_flag: bool = True
            attributes: Dict[str, Any] = {}

        class ChatRequest(BaseModel):
            query: str

        @app.get("/health")
        def health():
            return {"status": "HEALTHY", "system": "homomorphic-genomic-gwas-agent", "domain": "Privacy-Preserving Federated Healthcare & FHE", "version": "2.0.0-FRONTIER"}

        @app.post("/api/audit")
        def api_audit(req: TaskRequest):
            payload = FrontierPayload(
                task_id=req.task_id,
                target_identifier=req.target_identifier,
                primary_metric=req.primary_metric,
                secondary_metric=req.secondary_metric,
                status_descriptor=req.status_descriptor,
                is_critical_flag=req.is_critical_flag,
                attributes=req.attributes,
            )
            return coordinator.process(payload)

        @app.post("/api/chat")
        def api_chat(req: ChatRequest):
            return {"response": coordinator.query_supervisory_chat(req.query)}

        return app
    except ImportError:
        return None
