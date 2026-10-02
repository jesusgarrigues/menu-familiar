# menu-familiar

App web (en Docker) para organizar las comidas y cenas de la familia a partir del menú del comedor del cole.

- **Descarga sola el menú del cole.** Revisa cada pocas horas la [web del comedor](https://www.colegiovillademostoles.cbvm.net/servicios-y-precios/comedor). Cuando sale el PDF del mes (normalmente entre el día 1 y el 4), lo descarga y lo convierte en un calendario.
- **Lo que comen los niños.** Vista por semanas y por meses con los platos de cada día. Cada día se puede corregir a mano y la corrección se respeta aunque se vuelva a descargar el PDF.
- **Cenas recomendadas.** Si el cole recomienda un plato, aparece como primera opción. Si solo indica ingredientes ("pescado y verdura"), la app propone 3 o 4 platos concretos que cumplen esa recomendación y no repiten lo que han comido.
- **Fin de semana.** Propone la comida y la cena del sábado y del domingo para completar lo que ha faltado entre semana (pescado, legumbre, huevo, verdura…). Los días festivos también propone la comida.
- **Todo se puede cambiar.** Puedes elegir otra opción, pedir más ideas, escribir tu propio plato con sus ingredientes o marcar que coméis fuera.
- **Lista de la compra.** Se genera para la semana a partir de las comidas y cenas que se hacen en casa, agrupada por secciones (frutería, pescadería…). Suma las cantidades, deja marcar lo comprado y añadir otras cosas, y se puede compartir por WhatsApp.

## Cómo lee el PDF (¿hace falta IA?)

No es imprescindible:

| Modo | Cómo funciona | Cuándo usarlo |
|---|---|---|
| **Sin IA** (por defecto) | Un lector de PDF (`pdfplumber`) reconoce menús en forma de calendario o de lista. Las ideas de cenas salen de un recetario incluido (`app/recipes.py`, unos 45 platos con ingredientes). | Gratis y sin depender de nadie. Si algún día sale mal, se corrige con el botón *Corregir*. |
| **Con IA** (recomendado) | Si añades una clave de **OpenAI** o **Anthropic**, la IA lee el PDF directamente (también tablas raras o PDF escaneados) y propone platos más variados. | Más fiable. El coste es de unos céntimos al mes. |

Si la IA falla (sin saldo, sin conexión…), la app usa automáticamente el lector y el recetario locales.

## Instalación

Necesitas un equipo con Docker (un PC, un NAS o una Raspberry Pi; la imagen es para `amd64` y `arm64`).

```bash
mkdir menu-familiar && cd menu-familiar
curl -O https://raw.githubusercontent.com/jesusgarrigues/menu-familiar/main/docker-compose.yml
curl -o .env https://raw.githubusercontent.com/jesusgarrigues/menu-familiar/main/.env.example
# edita .env si quieres IA o contraseña
docker compose up -d
```

Abre `http://IP-DEL-EQUIPO:8000`. En el móvil puedes añadirla a la pantalla de inicio y se comporta como una app.

O con un solo comando:

```bash
docker run -d --name menu-familiar -p 8000:8000 -v $(pwd)/data:/data \
  -e OPENAI_API_KEY=sk-... ghcr.io/jesusgarrigues/menu-familiar:latest
```

Los datos (base de datos SQLite y PDFs descargados) se guardan en la carpeta `./data`.

> Si la imagen de GHCR es privada, hazla pública en GitHub (Packages → menu-familiar → Package settings → Change visibility), o inicia sesión con `docker login ghcr.io`.

## Configuración (variables de entorno)

| Variable | Por defecto | Para qué sirve |
|---|---|---|
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | — | Activa la IA (basta con una de las dos). |
| `OPENAI_MODEL` / `ANTHROPIC_MODEL` | `gpt-4.1-mini` / `claude-haiku-4-5` | Modelo que se usa. |
| `APP_PASSWORD` | — | Pide una contraseña para entrar. Recomendable si la app se puede abrir desde internet. |
| `SCHOOL_MENU_URL` | web del comedor | Página donde se publica el PDF. |
| `SCHOOL_MENU_KEYWORD` | `BASAL` | Si hay varios PDF (basal, alergias…), elige el que tenga esta palabra. |
| `CHECK_EVERY_HOURS` | `6` | Cada cuántas horas se revisa la web. |
| `CHECK_UNTIL_DAY` | `7` | Hasta qué día del mes se buscan versiones nuevas del PDF ya importado. |
| `SERVINGS` | `4` | Comensales (para las cantidades que propone la IA). |

## Si la descarga automática falla

La web del cole está hecha con Google Sites y el PDF está en Google Drive. Si cambian cómo lo publican, en **Ajustes** puedes:
- pulsar **Buscar el menú ahora** y ver el resultado en el *Registro*;
- **subir el PDF a mano** (descárgalo de la web y súbelo).

## Publicación de la imagen Docker

Cada `push` a `main` ejecuta las pruebas y publica la imagen con GitHub Actions (`.github/workflows/docker.yml`):

- **GitHub Container Registry:** `ghcr.io/jesusgarrigues/menu-familiar:latest`. Funciona sin configurar nada.
- **Docker Hub (opcional):** añade en *Settings → Secrets and variables → Actions* los secretos `DOCKERHUB_USERNAME` y `DOCKERHUB_TOKEN` (un *access token* de Docker Hub). La imagen se publicará también como `TU_USUARIO/menu-familiar`.

## Desarrollo

```bash
pip install -r requirements.txt reportlab
DATA_DIR=./data flask --app app.main run --debug     # http://localhost:5000
python -m unittest discover -s tests -v
```

Estructura:

```
app/
  main.py         API web (Flask) y servidor de la interfaz
  scraper.py      busca y descarga el PDF en la web del cole
  pdf_parser.py   lector del PDF sin IA
  ai.py           extracción y propuestas con IA (OpenAI / Anthropic)
  planner.py      cenas, fin de semana, equilibrio semanal y lista de la compra
  recipes.py      recetario local con ingredientes
  service.py      importación y comprobación automática
  static/         interfaz (HTML + CSS + JS, sin dependencias)
tests/            pruebas y generador de PDF de ejemplo
```

Para añadir tus platos habituales al recetario, edita `app/recipes.py`. El formato está explicado al principio del archivo.
