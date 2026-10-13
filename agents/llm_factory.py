"""
Deterministic mock responder; no external LLM providers are implemented.
"""
from typing import Dict, Any, Optional
from .base import PHIGuard


class MockLLM:
    def __init__(self, system_name: str = "Homomorphic Genomic Gwas Agent"):
        self.system_name = system_name

    def invoke(self, prompt: str) -> str:
        PHIGuard.assert_no_phi(prompt)
        return f"[{self.system_name} Mock Adapter]: No language-model inference performed. Query received: '{prompt[:60]}...'."


class LLMFactory:
    """Creates a deterministic mock responder with limited identifier-pattern checks."""

    @staticmethod
    def create(provider: str = "mock", system_name: str = "Homomorphic Genomic Gwas Agent"):
        prov = str(provider).lower()
        if prov in ["mock", "deterministic", "test"]:
            return MockLLM(system_name)
        raise ValueError(
            f"Provider {provider!r} is not implemented; only the deterministic mock is available."
        )
