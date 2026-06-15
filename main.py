"""
main.py
=======
Orquestador de CastAI. Encadena los 5 pasos del pipeline:

  1. Gmail  -> extraer newsletters de IA/Datos de las últimas N horas.
  2. Scrape -> seguir los enlaces y extraer el texto de los artículos.
  3. Gemini -> resumir correo a correo y redactar el guion del podcast.
  4. TTS    -> convertir el guion en audio .mp3.
  5. Entrega-> guardar guion + audio en la carpeta de salida.

Ejecutar:  python main.py
Pensado para correr programado cada madrugada (ver docs/SCHEDULING.md).
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime


from config import Config
from src.gmail_client import GmailClient
from src.scraper import scrape_links
from src.scriptwriter import ScriptWriter
from src.tts import TextToSpeech

# Log con timestamp para diagnosticar las ejecuciones desatendidas.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("castai")


def run(dry_run: bool = False) -> int:
    """Ejecuta el pipeline completo. Devuelve un exit code (0 = éxito).

    Si `dry_run` es True solo se ejecutan los pasos de LECTURA (Gmail +
    scraping): se informa de qué newsletters y artículos se procesarían y
    se aborta antes de llamar a Gemini y al TTS. Útil para validar la
    autenticación, la query y el scraping sin gastar cuota de API ni
    escribir ficheros.
    """
    # --- Configuración (fail-fast si falta algo crítico) ---
    config = Config.from_env()
    if dry_run:
        log.info("== MODO DRY-RUN: sin llamadas a Gemini/TTS ni ficheros ==")

    # --- Paso 1: Gmail ---
    log.info("Conectando a Gmail...")
    gmail = GmailClient(config.gmail_credentials_path, config.gmail_token_path)
    gmail.connect()

    log.info(
        "Buscando newsletters de %d remitentes recibidas ayer...",
        len(config.newsletter_senders),
    )
    emails = gmail.fetch_newsletters(config.newsletter_senders)
    if not emails:
        log.warning("No se encontraron newsletters. Nada que procesar hoy.")
        return 0
    log.info("Encontradas %d newsletters.", len(emails))

    # --- Paso 2: Scraping de los enlaces de cada correo ---
    articles_by_email = []
    for email in emails:
        articles = scrape_links(email.links)
        log.info(
            "  · %s -> %d artículos extraídos", email.subject, len(articles)
        )
        articles_by_email.append(articles)

    # --- Corte dry-run: informar y salir antes de Gemini/TTS ---
    if dry_run:
        total_articles = sum(len(a) for a in articles_by_email)
        total_chars = sum(
            len(art.text) for arts in articles_by_email for art in arts
        )
        log.info("--- Resumen dry-run ---")
        log.info("Newsletters: %d", len(emails))
        log.info("Artículos scrapeados: %d", total_articles)
        log.info("Caracteres totales a enviar a Gemini: ~%d", total_chars)
        for email, articles in zip(emails, articles_by_email):
            log.info(
                "  · [%s] %s | %d links -> %d artículos",
                email.sender,
                email.subject[:60],
                len(email.links),
                len(articles),
            )
        log.info("Dry-run OK. No se ha llamado a Gemini ni al TTS.")
        return 0

    # --- Paso 3: Guionizado con Gemini ---
    log.info("Generando guion con Gemini (%s)...", config.gemini_text_model)
    writer = ScriptWriter(config.gemini_api_key, config.gemini_text_model)
    script = writer.build_script(emails, articles_by_email)

    # --- Paso 5a: guardar el guion (texto) ---
    timestamp = datetime.now().strftime("%Y-%m-%d")
    config.output_dir.mkdir(parents=True, exist_ok=True)
    script_path = config.output_dir / f"podcast_IA_{timestamp}.txt"
    script_path.write_text(script, encoding="utf-8")
    log.info("Guion guardado en %s", script_path)

    # --- Paso 4: Locución TTS ---
    log.info("Sintetizando audio con %s (voz: %s)...",
             config.gemini_tts_model, config.gemini_tts_voice)
    tts = TextToSpeech(
        config.gemini_api_key, config.gemini_tts_model, config.gemini_tts_voice
    )
    audio_path = config.output_dir / f"podcast_IA_{timestamp}.mp3"
    try:
        tts.synthesize(script, audio_path)
        log.info("✅ Podcast listo: %s", audio_path)
    except Exception as exc:
        # TTS falló pero el guion ya está guardado: entrega parcial.
        log.error(
            "TTS falló (%s). El guion de texto está disponible en: %s",
            exc, script_path,
        )
        log.warning("Sin audio hoy. Puedes relanzar solo el TTS más tarde.")
        return 1

    return 0


def _parse_args() -> argparse.Namespace:
    """Parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="CastAI — genera un podcast diario desde tus newsletters."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo Gmail + scraping: informa qué se procesaría y sale "
        "antes de llamar a Gemini/TTS (sin coste ni ficheros).",
    )
    return parser.parse_args()


def main() -> None:
    """Punto de entrada con manejo de errores de alto nivel."""
    args = _parse_args()
    try:
        sys.exit(run(dry_run=args.dry_run))
    except Exception as exc:
        # Cualquier fallo no controlado: log claro y exit code != 0 para que
        # el scheduler (cron / Programador de tareas) lo detecte como error.
        log.error("Pipeline abortado: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
