"""
Punto de entrada: recibe una pregunta de un agente de soporte, llama al LLM
(Gemini primario, OpenAI fallback), valida la salida contra el contrato JSON,
registra métricas de la ejecución e imprime el resultado final.

Uso:
    python src/run_query.py "El cliente dice que no le llego su pedido"
"""

import json
import sys
from pathlib import Path

from llm_client import call_llm
from metrics_logger import estimate_cost_usd, log_metrics
from safety import check_prompt_safety
from schema import AssistantResponse, ValidationError, fallback_response, validate_response

PROMPT_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "prompts" / "main_prompt.txt"


def load_prompt_template() -> str:
    return PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")


def strip_markdown_fences(text: str) -> str:
    """El modelo a veces envuelve el JSON en ```json ... ``` a pesar de la
    instrucción de no hacerlo. Esto limpia ese caso antes de parsear."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        cleaned = cleaned.removeprefix("json").strip()
    return cleaned


def get_structured_response(question: str) -> AssistantResponse:
    prompt = load_prompt_template().replace("{user_question}", question)
    llm_response = call_llm(prompt)

    try:
        raw_json = json.loads(strip_markdown_fences(llm_response.text))
        structured = validate_response(raw_json)
    except (json.JSONDecodeError, ValidationError) as exc:
        structured = fallback_response(reason=str(exc))

    cost = estimate_cost_usd(
        provider=llm_response.provider,
        model=llm_response.model,
        tokens_prompt=llm_response.tokens_prompt,
        tokens_completion=llm_response.tokens_completion,
    )
    log_metrics(
        provider=llm_response.provider,
        model=llm_response.model,
        tokens_prompt=llm_response.tokens_prompt,
        tokens_completion=llm_response.tokens_completion,
        total_tokens=llm_response.total_tokens,
        latency_ms=llm_response.latency_ms,
        estimated_cost_usd=cost,
    )

    return structured


def main() -> None:
    if len(sys.argv) < 2:
        print('Uso: python src/run_query.py "tu pregunta aca"')
        sys.exit(1)

    question = " ".join(sys.argv[1:])

    is_safe, matched_pattern = check_prompt_safety(question)
    if not is_safe:
        structured = fallback_response(
            reason=f"entrada bloqueada por capa de seguridad (patron: {matched_pattern})"
        )
    else:
        structured = get_structured_response(question)

    print(structured.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
