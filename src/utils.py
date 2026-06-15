"""
utils.py
========
Utilidades compartidas entre módulos.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

log = logging.getLogger("castai")

T = TypeVar("T")

# Errores HTTP de Gemini que son transitorios y vale la pena reintentar.
_RETRYABLE_CODES = {503, 429}


def gemini_retry(fn: Callable[[], T], max_attempts: int = 4) -> T:
    """Llama a `fn` reintentando con backoff exponencial en errores transitorios.

    Reintenta ante 503 (sobrecarga) y 429 (rate-limit).
    Backoff: 5s, 10s, 20s… hasta `max_attempts`.
    Si se agotan los intentos, re-lanza la última excepción.
    """
    from google.genai import errors as genai_errors  # import tardío para no romper --dry-run

    delay = 5
    last_exc: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except genai_errors.ServerError as exc:
            # Comprobamos el código HTTP dentro del mensaje/atributos.
            code = getattr(exc, "code", None) or _parse_code(str(exc))
            if code not in _RETRYABLE_CODES:
                raise
            last_exc = exc
            log.warning(
                "Gemini %d (intento %d/%d). Reintentando en %ds…",
                code, attempt, max_attempts, delay,
            )
            time.sleep(delay)
            delay *= 2
        except genai_errors.ClientError as exc:
            # 4xx no son transitorios: falla rápido.
            raise

    raise last_exc  # type: ignore[misc]


def _parse_code(msg: str) -> int | None:
    """Extrae el código HTTP de un mensaje de error de texto si está presente."""
    import re
    m = re.search(r"\b([45]\d{2})\b", msg)
    return int(m.group(1)) if m else None