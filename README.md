# PI Soporte Asistente

Asistente de soporte al cliente que recibe una pregunta en texto libre y devuelve una respuesta estructurada en JSON (`answer`, `confidence`, `category`, `actions`, `escalate_to_human`), pensada para ser consumida por sistemas downstream sin transformaciones adicionales. Registra métricas de tokens, latencia y costo estimado por cada ejecución, e incluye una capa de seguridad básica contra prompts adversariales.

Proyecto integrador — Módulo 1, AI Engineering (Henry).

## Arquitectura (resumen)

```
pregunta del usuario
      -> safety.py        (bloquea prompt injection antes de llamar al LLM)
      -> main_prompt.txt   (few-shot + instrucciones de esquema)
      -> llm_client.py     (Gemini primario, fallback a OpenAI)
      -> schema.py         (valida el JSON contra el contrato, con Pydantic)
      -> metrics_logger.py (calcula costo y registra la ejecucion)
      -> JSON final impreso por consola
```

Detalle completo de las decisiones de diseño y la técnica de prompting en [`reports/PI_report_en.md`](reports/PI_report_en.md).

## Requisitos

- Python 3.10+
- Una API key de [Google AI Studio](https://aistudio.google.com/) (Gemini, proveedor primario)
- Una API key de [OpenAI](https://platform.openai.com/) (usada como fallback)

## Setup

```powershell
git clone <url-de-este-repo>
cd pi-soporte-asistente

python -m venv venv
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

## Variables de entorno

Copiá `.env.example` a `.env` y completá tus keys reales:

```powershell
Copy-Item .env.example .env
```

| Variable | Descripción |
|---|---|
| `LLM_PROVIDER` | Proveedor primario: `gemini` u `openai` (default: `gemini`) |
| `GEMINI_API_KEY` | API key de Google AI Studio |
| `OPENAI_API_KEY` | API key de OpenAI (usada como fallback si Gemini falla, y requerida por la consigna) |
| `GEMINI_MODEL` | Modelo de Gemini a usar (default: `gemini-2.5-flash-lite`) |
| `OPENAI_MODEL` | Modelo de OpenAI a usar (default: `gpt-4o-mini`) |

`.env` nunca se sube al repositorio (está en `.gitignore`). Verificá en tu cuenta de Google AI Studio que el modelo configurado en `GEMINI_MODEL` esté disponible para tu key antes de correr el proyecto.

## Cómo ejecutarlo

Con el entorno virtual activado:

```powershell
python src/run_query.py "El cliente dice que le llego el producto roto y quiere un reembolso"
```

Esto imprime por consola el JSON de respuesta y agrega una fila a `metrics/metrics.csv` con las métricas de esa ejecución.

Si la pregunta coincide con un patrón adversarial conocido (ver `src/safety.py`), el flujo se corta antes de llamar al LLM: se devuelve un JSON de fallback (`escalate_to_human: true`) sin consumir tokens, y la decisión queda registrada en `metrics/safety_log.csv`.

## Cómo correr los tests

```powershell
pytest tests/ -v
```

Los tests validan el contrato JSON (casos válidos e inválidos), la detección de patrones adversariales (en español e inglés) y el cálculo de costo — no requieren API key ni hacen llamadas reales, así que no consumen tokens.

## Cómo reproducir las métricas

Cada ejecución de `run_query.py` que llega a llamar al LLM agrega una fila a `metrics/metrics.csv` con: `timestamp, provider, model, tokens_prompt, tokens_completion, total_tokens, latency_ms, estimated_cost_usd`. El costo se calcula con los precios oficiales por proveedor/modelo definidos en `src/metrics_logger.py` (`PRICING_PER_MILLION_TOKENS`), verificados el 2026-09-12. Si el precio de un modelo cambia, hay que actualizar ese diccionario para que el costo estimado siga siendo preciso.

## Limitaciones conocidas

- La capa de seguridad (`src/safety.py`) es una primera línea de defensa basada en expresiones regulares. Detecta patrones conocidos de prompt injection en español e inglés, pero no es un sistema de moderación de contenido completo y puede no cubrir variaciones creativas del ataque.
- El proyecto usa el SDK `google-generativeai`, que Google marcó como deprecado en favor de `google-genai`. Sigue funcionando (se ve un `FutureWarning` al ejecutar), pero una mejora futura es migrar al SDK nuevo.
- Los precios usados para estimar costo son un snapshot verificado en una fecha puntual; no se consultan dinámicamente contra la API de cada proveedor.
- El contrato de salida se valida con Pydantic, pero si el modelo devuelve JSON malformado o con campos faltantes, se usa una respuesta de fallback genérica en lugar de reintentar la llamada.
