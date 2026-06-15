"""
gmail_client.py
===============
Paso 1 del pipeline: EXTRACCIÓN INTELIGENTE.

Se autentica contra Gmail vía OAuth2 (solo lectura) y devuelve las
newsletters relevantes recibidas dentro de la ventana de tiempo, ya
parseadas: asunto, remitente, texto plano y enlaces encontrados.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Permiso mínimo necesario: SOLO lectura de Gmail (principio de mínimo privilegio).
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Regex para extraer URLs http(s) del cuerpo de los correos.
_URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+")


@dataclass
class NewsletterEmail:
    """Representa una newsletter ya parseada y lista para procesar."""

    sender: str
    subject: str
    body_text: str
    links: list[str] = field(default_factory=list)


class GmailClient:
    """Cliente fino sobre la Gmail API centrado en leer newsletters."""

    def __init__(self, credentials_path: Path, token_path: Path) -> None:
        self._credentials_path = credentials_path
        self._token_path = token_path
        self._service = None  # se inicializa perezosamente en connect()

    # ------------------------------------------------------------------ #
    # Autenticación
    # ------------------------------------------------------------------ #
    def connect(self) -> None:
        """Resuelve credenciales OAuth2 (cache + refresh) y abre el servicio.

        - Si existe token.json válido, lo reutiliza.
        - Si está caducado pero es refrescable, lo refresca.
        - Si no hay token, lanza el flujo interactivo de consentimiento
          (abre el navegador una sola vez) y guarda el resultado.
        """
        creds: Credentials | None = None

        # 1) Intentar cargar token cacheado de ejecuciones anteriores.
        if self._token_path.exists():
            creds = Credentials.from_authorized_user_file(
                str(self._token_path), SCOPES
            )

        # 2) Si no sirve, refrescar o pedir login.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())  # refresco silencioso
            else:
                if not self._credentials_path.exists():
                    raise FileNotFoundError(
                        f"No existe {self._credentials_path}. Descarga el "
                        "client secret OAuth (Desktop app) desde Google Cloud."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self._credentials_path), SCOPES
                )
                # run_local_server abre el navegador y captura el callback.
                creds = flow.run_local_server(port=0)

            # 3) Persistir el token para no volver a pedir login.
            self._token_path.write_text(creds.to_json(), encoding="utf-8")

        # Servicio Gmail listo para consultas.
        self._service = build("gmail", "v1", credentials=creds)

    # ------------------------------------------------------------------ #
    # Lectura de newsletters
    # ------------------------------------------------------------------ #
    def fetch_newsletters(self, senders: list[str]) -> list[NewsletterEmail]:
        """Devuelve las newsletters de `senders` recibidas ayer (00:00–23:59 UTC)."""
        if self._service is None:
            raise RuntimeError("Llama a connect() antes de fetch_newsletters().")
        if not senders:
            return []

        query = self._build_query(senders)

        # list() solo devuelve IDs; el contenido se pide después uno a uno.
        response = (
            self._service.users()
            .messages()
            .list(userId="me", q=query)
            .execute()
        )
        message_ids = [m["id"] for m in response.get("messages", [])]

        newsletters: list[NewsletterEmail] = []
        for msg_id in message_ids:
            newsletters.append(self._get_message(msg_id))
        return newsletters

    # ------------------------------------------------------------------ #
    # Helpers privados
    # ------------------------------------------------------------------ #
    @staticmethod
    def _build_query(senders: list[str]) -> str:
        """Compone la cadena de búsqueda de Gmail."""
        # Gmail acepta 'after:'/'before:' como timestamp epoch (segundos).
        today_midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_midnight = today_midnight - timedelta(days=1)
        after_epoch = int(yesterday_midnight.timestamp())
        before_epoch = int(today_midnight.timestamp())
        from_clause = " OR ".join(f"from:{s}" for s in senders)
        return f"({from_clause}) after:{after_epoch} before:{before_epoch}"

    def _get_message(self, msg_id: str) -> NewsletterEmail:
        """Descarga un mensaje completo y lo convierte en NewsletterEmail."""
        msg = (
            self._service.users()
            .messages()
            .get(userId="me", id=msg_id, format="full")
            .execute()
        )

        payload = msg.get("payload", {})
        headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
        subject = headers.get("subject", "(sin asunto)")
        sender = headers.get("from", "(desconocido)")

        body_text = self._extract_body(payload)
        links = self._extract_links(body_text)

        return NewsletterEmail(
            sender=sender, subject=subject, body_text=body_text, links=links
        )

    def _extract_body(self, payload: dict) -> str:
        """Recorre las partes MIME y devuelve el texto del correo.

        Prioriza text/plain. Si solo hay text/html, hace un strip básico
        de etiquetas para quedarnos con el texto legible.
        """
        plain = self._find_part(payload, "text/plain")
        if plain:
            return plain

        html = self._find_part(payload, "text/html")
        if html:
            # Quitar etiquetas HTML de forma sencilla (suficiente para extraer
            # texto y enlaces; trafilatura hará el trabajo fino en las URLs).
            return re.sub(r"<[^>]+>", " ", html)

        return ""

    def _find_part(self, payload: dict, mime_type: str) -> str | None:
        """Busca recursivamente una parte MIME del tipo dado y la decodifica."""
        if payload.get("mimeType") == mime_type:
            data = payload.get("body", {}).get("data")
            if data:
                return self._decode(data)

        # Los correos multipart anidan partes dentro de 'parts'.
        for part in payload.get("parts", []):
            found = self._find_part(part, mime_type)
            if found:
                return found
        return None

    @staticmethod
    def _decode(data: str) -> str:
        """Gmail codifica el cuerpo en base64url; lo pasamos a texto UTF-8."""
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    @staticmethod
    def _extract_links(text: str) -> list[str]:
        """Extrae URLs únicas conservando el orden de aparición."""
        seen: set[str] = set()
        ordered: list[str] = []
        for url in _URL_RE.findall(text):
            if url not in seen:
                seen.add(url)
                ordered.append(url)
        return ordered