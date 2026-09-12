"""
Cálculo de costo estimado y registro de métricas por ejecución en metrics/metrics.csv.

Precios verificados el 2026-09-12 en las páginas oficiales de pricing de
OpenAI (https://platform.openai.com/docs/pricing) y Google AI
(https://ai.google.dev/gemini-api/docs/pricing). Los precios de los
proveedores cambian con el tiempo: si estos valores quedan desactualizados,
actualizar el diccionario PRICING_PER_MILLION_TOKENS a continuación.
"""

import csv
from datetime import datetime, timezone
from pathlib import Path

METRICS_CSV_PATH = Path(__file__).resolve().parent.parent / "metrics" / "metrics.csv"

# USD por 1,000,000 de tokens (input, output)
PRICING_PER_MILLION_TOKENS = {
    ("gemini", "gemini-2.5-flash-lite"): {"input": 0.10, "output": 0.40},
    ("openai", "gpt-4o-mini"): {"input": 0.15, "output": 0.60},
}


def estimate_cost_usd(provider: str, model: str, tokens_prompt: int, tokens_completion: int) -> float:
    prices = PRICING_PER_MILLION_TOKENS.get((provider, model))
    if prices is None:
        raise ValueError(
            f"No hay precio configurado para ({provider}, {model}). "
            "Agregalo a PRICING_PER_MILLION_TOKENS en metrics_logger.py."
        )
    cost = (tokens_prompt / 1_000_000) * prices["input"] + (tokens_completion / 1_000_000) * prices["output"]
    return round(cost, 8)


def log_metrics(provider: str, model: str, tokens_prompt: int, tokens_completion: int,
                 total_tokens: int, latency_ms: float, estimated_cost_usd: float) -> None:
    is_new_file = not METRICS_CSV_PATH.exists()

    with open(METRICS_CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new_file:
            writer.writerow([
                "timestamp", "provider", "model", "tokens_prompt", "tokens_completion",
                "total_tokens", "latency_ms", "estimated_cost_usd",
            ])
        writer.writerow([
            datetime.now(timezone.utc).isoformat(),
            provider,
            model,
            tokens_prompt,
            tokens_completion,
            total_tokens,
            round(latency_ms, 2),
            estimated_cost_usd,
        ])
