"""
Capa de seguridad simple (bonus): detecta patrones típicos de prompt
injection / intentos de manipular las instrucciones del sistema antes de
llamar al LLM. Si se detecta un patrón sospechoso, se corta la llamada y
se devuelve una respuesta de fallback segura, registrando la decisión.

Esto es una primera capa (basada en reglas), no una solución completa de
moderación de contenido — se documenta como limitación conocida en el reporte.
"""

import csv
import re
from datetime import datetime, timezone
from pathlib import Path

SAFETY_LOG_PATH = Path(__file__).resolve().parent.parent / "metrics" / "safety_log.csv"

ADVERSARIAL_PATTERNS = [
    # Intento de anular las instrucciones del sistema (EN / ES)
    r"ignore (all|the|any) (previous|above|prior) instructions",
    r"ignor(a|á|e) (todas|las) instrucciones (anteriores|previas)",
    r"olvid[aá] (todas|las) instrucciones (anteriores|previas)",
    r"disregard (your|the) (system|previous) prompt",
    r"desestim[aá] (el|las) (prompt|instrucciones) (del sistema|anteriores)",

    # Intento de extraer el system prompt (EN / ES)
    r"reveal (your|the) (system prompt|instructions)",
    r"(muestra|revela|decime|dime) (tu|el) (prompt|instrucciones) (del sistema|inicial)",
    r"repeat (your|the) (system prompt|instructions) (verbatim|word for word)",

    # Intento de jailbreak / cambio de persona (EN / ES)
    r"you are now (dan|jailbroken|unrestricted)",
    r"(ahora sos|actua como) (dan|sin restricciones|sin filtros)",
    r"act as (if you have no|an unfiltered)",
    r"pretend (you have no|to have no) (restrictions|rules|filters)",
    r"pretend[eé]? que no ten[eé]s (restricciones|reglas|filtros)",

    # Intento de evadir políticas de seguridad/contenido (EN / ES)
    r"bypass (your|any) (safety|content) (filter|policy)",
    r"evad[ií] (el|los) (filtro|filtros) de (seguridad|contenido)",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in ADVERSARIAL_PATTERNS]


def _log_decision(question: str, matched_pattern: str | None, is_blocked: bool) -> None:
    is_new_file = not SAFETY_LOG_PATH.exists()
    with open(SAFETY_LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new_file:
            writer.writerow(["timestamp", "question", "matched_pattern", "blocked"])
        writer.writerow([
            datetime.now(timezone.utc).isoformat(),
            question,
            matched_pattern or "",
            is_blocked,
        ])


def check_prompt_safety(question: str) -> tuple[bool, str | None]:
    """Devuelve (is_safe, matched_pattern). Registra la decisión en todos los casos."""
    for pattern in _COMPILED_PATTERNS:
        match = pattern.search(question)
        if match:
            _log_decision(question, pattern.pattern, is_blocked=True)
            return False, pattern.pattern

    _log_decision(question, None, is_blocked=False)
    return True, None
