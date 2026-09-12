"""
Contrato de salida del asistente. Cualquier respuesta del LLM se valida
contra este esquema antes de ser considerada válida para consumo downstream.
"""

from typing import Literal

from pydantic import BaseModel, ValidationError


class AssistantResponse(BaseModel):
    model_config = {"extra": "forbid"}

    answer: str
    confidence: Literal["high", "medium", "low"]
    category: Literal["billing", "technical", "account", "shipping", "other"]
    actions: list[str]
    escalate_to_human: bool


def validate_response(raw_json: dict) -> AssistantResponse:
    """Lanza pydantic.ValidationError si raw_json no cumple el contrato."""
    return AssistantResponse(**raw_json)


def fallback_response(reason: str) -> AssistantResponse:
    """Respuesta segura usada cuando el modelo no respeta el contrato
    (JSON inválido, campos faltantes, tipos incorrectos, etc.)."""
    return AssistantResponse(
        answer=f"No pude generar una respuesta estructurada válida ({reason}). Se recomienda revisión humana.",
        confidence="low",
        category="other",
        actions=["Revisar la consulta manualmente"],
        escalate_to_human=True,
    )


__all__ = ["AssistantResponse", "validate_response", "fallback_response", "ValidationError"]
