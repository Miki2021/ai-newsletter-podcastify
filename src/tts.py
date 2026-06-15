"""
tts.py
======
Paso 4 del pipeline: LOCUCIÓN (Gemini TTS).

Convierte el guion de texto en audio. Gemini TTS devuelve PCM crudo
(audio/L16, 24 kHz, mono, 16-bit); aquí lo empaquetamos y exportamos a .mp3
usando pydub (que internamente necesita ffmpeg instalado en el sistema).
"""

from __future__ import annotations

import base64
import glob
import shutil
from pathlib import Path

from google import genai
from google.genai import types
from pydub import AudioSegment

from src.utils import gemini_retry

# Parámetros del PCM que entrega Gemini TTS (fijos según la API).
_SAMPLE_RATE = 24000   # Hz
_SAMPLE_WIDTH = 2      # bytes por muestra (16 bits)
_CHANNELS = 1          # mono


def _configure_ffmpeg() -> None:
    """Asegura que pydub encuentre ffmpeg aunque no esté en el PATH del proceso.

    Orden de búsqueda:
      1. PATH estándar (shutil.which) → suficiente en shells normales.
      2. Directorio bin del paquete winget Gyan.FFmpeg → cubre el caso de
         sesiones abiertas antes de que winget actualizara el PATH del usuario.
    Si ninguno existe lanza RuntimeError con instrucciones claras.
    """
    if shutil.which("ffmpeg"):
        return  # ya visible en PATH, pydub lo encontrará solo

    # Fallback: buscar el binario instalado por winget (patrón de ruta conocido).
    import os
    winget_pattern = os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe"
    )
    candidates = glob.glob(winget_pattern)
    if candidates:
        ffmpeg_path = str(Path(candidates[0]).resolve())
        AudioSegment.converter = ffmpeg_path
        AudioSegment.ffmpeg = ffmpeg_path
        return

    raise RuntimeError(
        "ffmpeg no encontrado en PATH ni en winget. "
        "Abre una terminal nueva (para recargar el PATH) o instala ffmpeg: "
        "winget install --id Gyan.FFmpeg -e"
    )


class TextToSpeech:
    """Sintetiza voz con Gemini TTS y guarda el resultado como .mp3."""

    def __init__(self, api_key: str, tts_model: str, voice: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = tts_model
        self._voice = voice

    def synthesize(self, script: str, output_path: Path) -> Path:
        """Genera el audio del `script` y lo escribe en `output_path` (.mp3)."""
        # 1) Pedir el audio a Gemini con la voz prebuilt elegida.
        response = gemini_retry(lambda: self._client.models.generate_content(
            model=self._model,
            contents=script,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=self._voice
                        )
                    )
                ),
            ),
        ))

        # 2) Extraer los bytes PCM de la respuesta.
        pcm_bytes = self._extract_pcm(response)

        # 3) Envolver el PCM crudo en un AudioSegment y exportar a MP3.
        _configure_ffmpeg()
        audio = AudioSegment(
            data=pcm_bytes,
            sample_width=_SAMPLE_WIDTH,
            frame_rate=_SAMPLE_RATE,
            channels=_CHANNELS,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        audio.export(output_path, format="mp3")
        return output_path

    @staticmethod
    def _extract_pcm(response) -> bytes:
        """Saca los bytes de audio inline de la respuesta de Gemini."""
        try:
            part = response.candidates[0].content.parts[0]
            data = part.inline_data.data
        except (AttributeError, IndexError, TypeError) as exc:
            raise RuntimeError(
                "La respuesta de Gemini TTS no contiene audio."
            ) from exc

        if not data:
            raise RuntimeError("Gemini TTS devolvió audio vacío.")

        # El SDK puede devolver bytes directamente o base64 en str.
        if isinstance(data, str):
            return base64.b64decode(data)
        return data
