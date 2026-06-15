"""
scriptwriter.py
===============
Paso 3 del pipeline: CURACIÓN Y GUIONIZADO (Gemini API).

Estrategia en dos pasos para evitar alucinaciones:
  1) Resumir cada newsletter por separado (contexto pequeño y controlado).
  2) Ensamblar todos los resúmenes en un único guion de podcast.
"""

from __future__ import annotations

import logging

from google import genai
from google.genai import types

from src.gmail_client import NewsletterEmail
from src.prompts import SCRIPT_SYSTEM_PROMPT, SUMMARIZE_SYSTEM_PROMPT
from src.scraper import Article
from src.utils import gemini_retry

log = logging.getLogger("castai.scriptwriter")

# Centinela que devuelve el modelo cuando un correo no aporta nada útil.
_NO_CONTENT = "SIN_CONTENIDO_RELEVANTE"


class ScriptWriter:
    """Genera el guion del podcast a partir de las newsletters y artículos."""

    def __init__(self, api_key: str, text_model: str) -> None:
        # Cliente Gemini reutilizable para todas las llamadas de texto.
        self._client = genai.Client(api_key=api_key)
        self._model = text_model

    def build_script(
        self,
        emails: list[NewsletterEmail],
        articles_by_email: list[list[Article]],
    ) -> str:
        """Orquesta los dos pasos y devuelve el guion final listo para TTS.

        `articles_by_email[i]` contiene los artículos scrapeados del correo
        `emails[i]` (mismas longitudes y orden).
        """
        # --- Paso 3a: resumen por correo ---
        summaries: list[str] = []
        for email, articles in zip(emails, articles_by_email):
            try:
                summary = self._summarize_email(email, articles)
            except Exception as exc:
                # Un correo que falla no aborta el pipeline: lo saltamos y
                # continuamos con el resto para aprovechar lo que ya tenemos.
                log.warning(
                    "Error resumiendo '%s' — se omite: %s",
                    email.subject[:60], exc,
                )
                continue
            if summary and _NO_CONTENT not in summary:
                summaries.append(summary)

        if not summaries:
            raise RuntimeError(
                "Ninguna newsletter aportó contenido relevante hoy "
                "(todas fallaron o fueron descartadas)."
            )

        # --- Paso 3b: guion final ---
        return self._assemble_script(summaries)

    # ------------------------------------------------------------------ #
    # Pasos internos
    # ------------------------------------------------------------------ #
    def _summarize_email(
        self, email: NewsletterEmail, articles: list[Article]
    ) -> str:
        """Resume un único correo + sus artículos enlazados."""
        # Concatenamos el cuerpo del correo y el texto de los artículos.
        article_blocks = "\n\n".join(
            f"[Artículo: {a.url}]\n{a.text}" for a in articles
        )
        user_content = (
            f"REMITENTE: {email.sender}\n"
            f"ASUNTO: {email.subject}\n\n"
            f"CUERPO:\n{email.body_text}\n\n"
            f"ARTÍCULOS ENLAZADOS:\n{article_blocks}"
        )

        response = gemini_retry(lambda: self._client.models.generate_content(
            model=self._model,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=SUMMARIZE_SYSTEM_PROMPT,
                temperature=0.2,
            ),
        ))
        return (response.text or "").strip()

    def _assemble_script(self, summaries: list[str]) -> str:
        """Convierte la lista de resúmenes en el guion hablado final."""
        joined = "\n\n---\n\n".join(
            f"RESUMEN {i + 1}:\n{s}" for i, s in enumerate(summaries)
        )

        response = gemini_retry(lambda: self._client.models.generate_content(
            model=self._model,
            contents=joined,
            config=types.GenerateContentConfig(
                system_instruction=SCRIPT_SYSTEM_PROMPT,
                temperature=0.7,
            ),
        ))
        script = (response.text or "").strip()
        if not script:
            raise RuntimeError("Gemini devolvió un guion vacío.")
        return script