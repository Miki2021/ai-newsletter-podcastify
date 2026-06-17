"""
config.py
=========
Centraliza TODA la configuración del proyecto leída del entorno.

Un único punto de verdad evita esparcir os.getenv() por el código y
facilita validar al arranque que no falta nada crítico (fail-fast).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# --- Carga opcional de .env -------------------------------------------------
# python-dotenv NO es dependencia obligatoria. Si está instalado, cargamos
# el fichero .env; si no, seguimos con las variables de entorno del sistema.
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except ModuleNotFoundError:
    pass


def _split_csv(value: str) -> list[str]:
    """Convierte 'a, b ,c' en ['a', 'b', 'c'] limpiando espacios/vacíos."""
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Config:
    """Configuración inmutable de CastAI (se construye una sola vez)."""

    # --- Gemini ---
    gemini_api_key: str
    gemini_text_model: str
    gemini_tts_model: str
    gemini_tts_voice: str

    # --- Gmail ---
    gmail_credentials_path: Path
    gmail_token_path: Path
    newsletter_senders: list[str]

    # --- Salida ---
    output_dir: Path = field(default_factory=lambda: Path("podcasts_diarios"))

    @classmethod
    def from_env(cls) -> "Config":
        """Construye la config desde variables de entorno y la valida."""
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        # Fail-fast: sin API key no tiene sentido continuar.
        if not api_key:
            raise RuntimeError(
                "Falta GEMINI_API_KEY. Copia .env.example a .env y rellénala "
                "(o expórtala en tu shell)."
            )

        return cls(
            gemini_api_key=api_key,
            gemini_text_model=os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash"),
            gemini_tts_model=os.getenv(
                "GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts"
            ),
            gemini_tts_voice=os.getenv("GEMINI_TTS_VOICE", "Kore"),
            gmail_credentials_path=Path(
                os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
            ),
            gmail_token_path=Path(os.getenv("GMAIL_TOKEN_PATH", "token.json")),
            newsletter_senders=_split_csv(os.getenv("NEWSLETTER_SENDERS", "")),
            output_dir=Path(os.getenv("OUTPUT_DIR", "podcasts_diarios")),
        )