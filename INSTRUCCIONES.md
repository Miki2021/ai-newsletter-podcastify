# 🔑 INSTRUCCIONES — Activar la Gmail API y obtener `credentials.json`

Esta guía explica, paso a paso, cómo habilitar la **Gmail API** en Google
Cloud Console y descargar el fichero `credentials.json` (OAuth2) que CastAI
necesita para leer tus newsletters en modo **solo lectura**.

> Tiempo estimado: ~10 minutos. Solo se hace una vez.

---

## 0. Requisitos previos

- Una cuenta de Google (la misma cuenta de Gmail donde recibes las newsletters).
- Acceso a [Google Cloud Console](https://console.cloud.google.com/).
- No necesitas tarjeta de crédito: la Gmail API entra en la capa gratuita.

---

## 1. Crear (o elegir) un proyecto en Google Cloud

1. Entra en <https://console.cloud.google.com/>.
2. Arriba a la izquierda, abre el **selector de proyectos** y pulsa **"Nuevo proyecto"**.
3. Nombre sugerido: `castai-podcast`. Pulsa **"Crear"**.
4. Espera unos segundos y **selecciona el proyecto** recién creado (selector arriba).

---

## 2. Habilitar la Gmail API

1. Menú lateral (☰) → **"APIs y servicios"** → **"Biblioteca"**.
2. Busca **"Gmail API"** y entra en su ficha.
3. Pulsa **"Habilitar"**.

---

## 3. Configurar la pantalla de consentimiento OAuth

Antes de poder crear credenciales OAuth, Google exige configurar la pantalla
de consentimiento.

1. Menú lateral → **"APIs y servicios"** → **"Pantalla de consentimiento de OAuth"**.
2. Tipo de usuario: selecciona **"Externo"** y pulsa **"Crear"**.
   *(Externo es lo normal para una cuenta personal de Gmail; "Interno" solo
   aparece con Google Workspace de empresa.)*
3. Rellena los campos obligatorios:
   - **Nombre de la app:** `CastAI`
   - **Correo de asistencia al usuario:** tu email.
   - **Datos de contacto del desarrollador:** tu email.
   - El resto puede quedar en blanco. Pulsa **"Guardar y continuar"**.
4. **Permisos (scopes):** pulsa **"Guardar y continuar"** sin añadir nada
   aquí (el scope de solo lectura lo pide la app en tiempo de ejecución).
5. **Usuarios de prueba:** pulsa **"+ Add users"** y añade **tu propia
   dirección de Gmail**. Esto es imprescindible mientras la app esté en modo
   "Testing": solo los usuarios de prueba podrán autorizarla.
6. Pulsa **"Guardar y continuar"** → **"Volver al panel"**.

> ℹ️ La app queda en estado **"Testing"**. No necesitas publicarla ni pasar
> verificación de Google para uso personal. El único efecto: el token OAuth
> caduca cada 7 días y se renueva solo en la siguiente ejecución (vuelve a
> abrir el navegador una vez).

---

## 4. Crear las credenciales OAuth (Desktop app)

1. Menú lateral → **"APIs y servicios"** → **"Credenciales"**.
2. Pulsa **"+ Crear credenciales"** → **"ID de cliente de OAuth"**.
3. **Tipo de aplicación:** selecciona **"Aplicación de escritorio"**
   (*Desktop app*). Es la correcta porque CastAI corre localmente y abre un
   servidor local para el callback OAuth.
4. Nombre: `castai-desktop`. Pulsa **"Crear"**.
5. Aparece un diálogo con el Client ID. Pulsa **"Descargar JSON"**.

---

## 5. Colocar el fichero como `credentials.json`

1. Renombra el fichero descargado a **`credentials.json`**.
2. Muévelo a la **raíz del proyecto** (junto a `main.py`):

   ```
   ai-newsletter-podcastify/
   ├── credentials.json   ← AQUÍ
   ├── main.py
   └── ...
   ```

3. (Opcional) Si prefieres otra ruta/nombre, ajústalo en `.env`:

   ```dotenv
   GMAIL_CREDENTIALS_PATH=credentials.json
   GMAIL_TOKEN_PATH=token.json
   ```

> 🔒 **Seguridad:** `credentials.json` y `token.json` son secretos. Ya están
> en `.gitignore` — NUNCA los subas a git ni los compartas.

---

## 6. Primer arranque: autorizar el acceso (OAuth)

La **primera** ejecución abre el navegador para que autorices el acceso de
**solo lectura** a tu Gmail. Tras aceptar, se genera `token.json` y las
siguientes ejecuciones ya no piden login.

```bash
python main.py
```

Durante el flujo verás:

- Una pantalla de Google pidiendo elegir tu cuenta.
- Un aviso **"Google no ha verificado esta aplicación"** → pulsa
  **"Configuración avanzada"** → **"Ir a CastAI (no seguro)"**. Es normal:
  ocurre porque la app está en modo Testing y la usas tú mismo.
- La solicitud del permiso **"Ver tus correos electrónicos y su
  configuración"** (gmail.readonly) → **"Permitir"**.

Si todo va bien, la consola muestra el progreso y el guion + `.mp3` aparecen
en la carpeta **`podcasts_diarios/`** como `podcast_IA_<FECHA>.mp3`.

---

## 7. Resolución de problemas

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| `FileNotFoundError: No existe credentials.json` | El JSON no está en la ruta esperada | Revisa el paso 5 y `GMAIL_CREDENTIALS_PATH`. |
| `Error 403: access_denied` | Tu email no está en "Usuarios de prueba" | Vuelve al paso 3.5 y añádete. |
| `Token has been expired or revoked` | Token caducado (modo Testing, 7 días) | Borra `token.json` y vuelve a ejecutar `python main.py`. |
| El navegador no abre | Entorno sin GUI / servidor | Ejecuta el primer login en una máquina con navegador y copia `token.json`. |
| `redirect_uri_mismatch` | Creaste el cliente con tipo equivocado | Recréalo como **"Aplicación de escritorio"** (paso 4.3). |

---

Hecho. Con `credentials.json` en su sitio y el primer login completado,
CastAI ya puede leer tus newsletters de forma automática y desatendida.