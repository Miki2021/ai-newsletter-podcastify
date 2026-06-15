# Programar CastAI cada madrugada

CastAI no incluye scheduler propio: ejecuta `python main.py` una vez y
sale. Para correrlo automáticamente cada madrugada usa el programador de
tu sistema operativo.

## Requisito previo: primer login OAuth

La **primera** ejecución abre el navegador para autorizar el acceso a
Gmail y genera `token.json`. Hazlo **a mano una vez** antes de programar
la tarea (un scheduler desatendido no puede abrir el navegador):

```bash
python main.py
```

A partir de ahí el token se refresca solo y las ejecuciones son silenciosas.

---

## Windows — Programador de tareas

```powershell
# Ajusta las rutas a tu instalación. Corre todos los días a las 06:00.
$python = "C:\MisProyectos\ai-newsletter-podcastify\.venv\Scripts\python.exe"
$script = "C:\MisProyectos\ai-newsletter-podcastify\main.py"
$workdir = "C:\MisProyectos\ai-newsletter-podcastify"

$action  = New-ScheduledTaskAction -Execute $python -Argument $script -WorkingDirectory $workdir
$trigger = New-ScheduledTaskTrigger -Daily -At 6:00am
Register-ScheduledTask -TaskName "CastAI" -Action $action -Trigger $trigger -Description "Podcast diario de IA"
```

> El `-WorkingDirectory` es importante: `config.py` resuelve rutas
> relativas (`.env`, `credentials.json`, `output/`) desde ahí.

---

## Linux / macOS — cron

```bash
# Editar el crontab del usuario:
crontab -e

# Añadir (06:00 cada día). Usa rutas absolutas:
0 6 * * * cd /ruta/ai-newsletter-podcastify && /ruta/.venv/bin/python main.py >> output/cron.log 2>&1
```

---

## Dependencia del sistema: ffmpeg

La exportación a `.mp3` usa **pydub**, que necesita **ffmpeg** instalado:

- Windows: `winget install ffmpeg` (o `choco install ffmpeg`)
- macOS:   `brew install ffmpeg`
- Debian/Ubuntu: `sudo apt install ffmpeg`
