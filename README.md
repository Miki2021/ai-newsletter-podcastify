# 🎙️ CastAI

> **NoRead-JustListen:** Automatización total para transformar tus newsletters diarias de IA y Datos en un podcast personalizado de 10-15 minutos, listo para escuchar cada mañana.

---

## 📝 Descripción del Proyecto

**CastAI** es un pipeline automatizado en Python diseñado para profesionales y entusiastas del ecosistema tecnológico que quieren mantenerse al día sin sufrir de *infoxicación*. 

El script se ejecuta de forma programada cada madrugada, se conecta de forma segura a tu cuenta de Gmail, filtra las newsletters más importantes sobre Inteligencia Artificial y Ciencia de Datos, extrae la información profunda de los enlaces que contienen y destila todo ese conocimiento en un guion de podcast dinámico, fluido y libre de "paja". Finalmente, utiliza modelos avanzados de Text-to-Speech (TTS) para generar un archivo de audio de alta fidelidad (`.mp3`) listo para reproducir.

---

## ⚙️ Arquitectura del Sistema (Paso a Paso)

El proyecto está construido de manera modular para evitar la saturación de contexto de los modelos de lenguaje y garantizar la máxima precisión en la información:

1. **📥 Extracción Inteligente (Gmail API):** Escanea tu bandeja de entrada buscando remitentes específicos (*TLDR AI, TLDR Data, Towards Data Science, Dharmesh @ simple.ai, AI Breakfast, The Rundown AI*) en un rango de fechas (últimas 24 horas).
2. **🌐 Web Scraping Selectivo (trafilatura):** Entra en los enlaces principales incluidos en los correos para extraer el contenido real de los artículos y noticias, ignorando anuncios y menús.
3. **🧠 Curación y Guionizado (Gemini API):** Procesa la información correo por correo para evitar alucinaciones. Clasifica en tres niveles (crucial / mención / paja) y redacta un guion de podcast con estructura profesional (intro, cuerpo con las noticias cruciales, repaso rápido de titulares secundarios y cierre).
4. **🗣️ Locución Ultra-realista (Gemini TTS):** Convierte el guion de texto en un archivo de audio con entonación, pausas y ritmo humanos.
5. **📁 Entrega:** Guarda el archivo final en una carpeta local dedicada, listo para ser sincronizado con tu móvil.

---

## 🛠️ Tecnologías Utilizadas

*   **Lenguaje:** Python 3.11+
*   **Orquestación de Código:** Desarrollado con el asistente autónomo de terminal **Claude Code**.
*   **APIs de Google:** Gmail API (OAuth2) para la lectura segura de correos.
*   **LLM (Procesamiento de Texto):** `Gemini API` (`gemini-2.5-flash`).
*   **Audio (TTS):** `Gemini TTS` (`gemini-2.5-flash-preview-tts`).
*   **Scraping y Red:** `trafilatura` + `requests`.
*   **Empaquetado de Audio:** `pydub` (requiere `ffmpeg`).
*   **Gestión de Entorno:** Variables de entorno (`.env` opcional vía `python-dotenv`).

---

## 🚀 Puesta en Marcha

### 1. Requisitos del sistema
*   Python 3.11+
*   **ffmpeg** instalado (lo usa `pydub` para escribir el `.mp3`). Ver [docs/SCHEDULING.md](docs/SCHEDULING.md).

### 2. Instalar dependencias
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Credenciales
1.  **Gemini:** crea una API key en https://aistudio.google.com/apikey
2.  **Gmail:** en Google Cloud Console crea un *OAuth client ID* tipo **Desktop app**, habilita la **Gmail API** y descarga el JSON como `credentials.json` en la raíz del proyecto.
3.  Copia `.env.example` a `.env` y rellena los valores (API key, remitentes a filtrar, etc.).

### 4. Primer arranque (login OAuth)
La primera ejecución abre el navegador para autorizar el acceso de **solo lectura** a Gmail y guarda `token.json` para las siguientes.
```bash
python main.py
```

El guion (`.txt`) y el podcast (`.mp3`) aparecen en `podcasts_diarios/` como `podcast_IA_<FECHA>.mp3`.

> Guía detallada para activar la Gmail API y descargar `credentials.json`: ver **[INSTRUCCIONES.md](INSTRUCCIONES.md)**.

### 5. Automatizar cada madrugada
Ver [docs/SCHEDULING.md](docs/SCHEDULING.md) (Programador de tareas de Windows / cron).

---

## 📂 Estructura del Proyecto

```
ai-newsletter-podcastify/
├── main.py                 # Orquestador: encadena los 5 pasos
├── config.py               # Configuración leída del entorno (fail-fast)
├── requirements.txt
├── INSTRUCCIONES.md        # Guía: activar Gmail API + credentials.json
├── .env.example            # Plantilla de variables de entorno
├── src/
│   ├── gmail_client.py     # Paso 1: extracción de newsletters (OAuth2)
│   ├── scraper.py          # Paso 2: scraping selectivo (trafilatura)
│   ├── scriptwriter.py     # Paso 3: resumen + guion (Gemini)
│   ├── prompts.py          # Prompts de sistema del guionizado
│   └── tts.py              # Paso 4: locución a .mp3 (Gemini TTS)
├── docs/
│   └── SCHEDULING.md       # Cómo programar la ejecución diaria
└── podcasts_diarios/       # Guiones y audios generados (gitignored)
```