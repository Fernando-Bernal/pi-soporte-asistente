"""
Capa de abstracción sobre proveedores de LLM.

Diseño: Gemini es el proveedor primario (por costo), OpenAI actúa como
fallback si Gemini falla (rate limit, error de red, modelo no disponible, etc.)
y además satisface el requisito explícito de la consigna de usar la API
de OpenAI.
"""

import os
import time
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    tokens_prompt: int
    tokens_completion: int
    total_tokens: int
    latency_ms: float


def _call_gemini(prompt: str) -> LLMResponse:
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY no configurada en .env")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)

    start = time.perf_counter()
    response = model.generate_content(
        prompt, generation_config={"temperature": 0.2}
    )
    latency_ms = (time.perf_counter() - start) * 1000

    usage = response.usage_metadata
    return LLMResponse(
        text=response.text,
        provider="gemini",
        model=GEMINI_MODEL,
        tokens_prompt=usage.prompt_token_count,
        tokens_completion=usage.candidates_token_count,
        total_tokens=usage.total_token_count,
        latency_ms=latency_ms,
    )


def _call_openai(prompt: str) -> LLMResponse:
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY no configurada en .env")

    client = OpenAI(api_key=api_key)

    start = time.perf_counter()
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    latency_ms = (time.perf_counter() - start) * 1000

    usage = response.usage
    return LLMResponse(
        text=response.choices[0].message.content,
        provider="openai",
        model=OPENAI_MODEL,
        tokens_prompt=usage.prompt_tokens,
        tokens_completion=usage.completion_tokens,
        total_tokens=usage.total_tokens,
        latency_ms=latency_ms,
    )


def call_llm(prompt: str) -> LLMResponse:
    """Llama al proveedor primario configurado; si es 'gemini' y falla,
    reintenta automáticamente con OpenAI."""
    primary = os.getenv("LLM_PROVIDER", "gemini")

    if primary == "openai":
        return _call_openai(prompt)

    try:
        return _call_gemini(prompt)
    except Exception as gemini_error:
        print(f"[llm_client] Gemini fallo ({gemini_error}); usando fallback OpenAI...")
        return _call_openai(prompt)
