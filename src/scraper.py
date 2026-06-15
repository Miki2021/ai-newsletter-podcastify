"""
scraper.py
==========
Paso 2 del pipeline: WEB SCRAPING SELECTIVO.

Para cada enlace de una newsletter descarga la página y extrae SOLO el
contenido principal del artículo (texto), descartando menús, anuncios y
boilerplate. Usa trafilatura, que está especializado en esta tarea.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests
import trafilatura

log = logging.getLogger("castai.scraper")

# Límites defensivos para no inflar el contexto del LLM ni colgarnos.
_MAX_LINKS_PER_EMAIL = 100       # cuántos enlaces seguir por correo
_MAX_CHARS_PER_ARTICLE = 6000   # recorte del texto extraído por artículo
_FETCH_TIMEOUT = 15             # segundos máx. de espera por descarga

# Headers de navegador real para reducir bloqueos por bot-detection.
# No bypasea paywalls (WSJ, NYT…): devuelven HTML de paywall sin artículo,
# trafilatura no extrae nada útil y el enlace se descarta limpiamente.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}


@dataclass
class Article:
    """Artículo extraído de un enlace de la newsletter."""

    url: str
    text: str


def scrape_links(links: list[str]) -> list[Article]:
    """Descarga y extrae el texto de una lista de enlaces.

    Es tolerante a fallos: un enlace roto o sin contenido se ignora y se
    continúa con el resto (no debe tumbar el pipeline diario).
    """
    articles: list[Article] = []

    # Solo seguimos los primeros N enlaces para acotar coste y tiempo.
    for url in links[:_MAX_LINKS_PER_EMAIL]:
        text = _extract_one(url)
        if text:
            articles.append(Article(url=url, text=text))

    return articles


def _fetch_html(url: str) -> str | None:
    """Descarga HTML con headers de browser real. Fallback a trafilatura si falla."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_FETCH_TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:
        log.debug("requests falló para %s (%s), reintentando con trafilatura", url, exc)

    # Fallback: trafilatura con su propio fetch (último recurso).
    try:
        return trafilatura.fetch_url(url)
    except Exception:
        return None


def _extract_one(url: str) -> str | None:
    """Descarga una URL y devuelve su texto principal, o None si falla."""
    html = _fetch_html(url)
    if not html:
        return None

    text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        favor_precision=True,
    )
    if not text:
        log.debug("Sin contenido extraíble en %s (posible paywall o JS)", url)
    return text