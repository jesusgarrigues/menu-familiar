"""Configuración de la app, leída de variables de entorno."""
import os
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
PDF_DIR = DATA_DIR / "pdfs"
DB_PATH = DATA_DIR / "menu.db"

# Web del cole donde se publica el PDF cada mes
SCHOOL_MENU_URL = os.getenv(
    "SCHOOL_MENU_URL",
    "https://www.colegiovillademostoles.cbvm.net/servicios-y-precios/comedor",
)
# Si hay varios PDF (basal, alergias...), se prefiere el que contenga esta palabra
SCHOOL_MENU_KEYWORD = os.getenv("SCHOOL_MENU_KEYWORD", "BASAL")

# Comprobación automática: cada cuántas horas y hasta qué día del mes
CHECK_EVERY_HOURS = float(os.getenv("CHECK_EVERY_HOURS", "6"))
CHECK_UNTIL_DAY = int(os.getenv("CHECK_UNTIL_DAY", "7"))
AUTO_FETCH = os.getenv("AUTO_FETCH", "true").lower() in ("1", "true", "yes", "si", "sí")

# IA opcional: "openai", "anthropic" o vacío (se detecta por la clave disponible)
AI_PROVIDER = os.getenv("AI_PROVIDER", "").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
# Modelo barato para proponer platos e ingredientes (el de arriba solo se usa para leer el PDF)
OPENAI_MODEL_FAST = os.getenv("OPENAI_MODEL_FAST", "gpt-5-nano")
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1-mini")
# Crear fotos con IA cuando no se encuentra ninguna en internet. Desactivado: la IA se usa para buscarlas.
AI_PHOTOS = os.getenv("AI_PHOTOS", "false").lower() in ("1", "true", "yes", "si", "sí")
# Fotos: primero se buscan en internet (gratis); la IA solo si no aparece ninguna adecuada
PHOTOS_WEB = os.getenv("PHOTOS_WEB", "true").lower() in ("1", "true", "yes", "si", "sí")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")  # opcional y gratis: mejores fotos
# Tope de gasto mensual en IA (dólares). Al llegar, la app sigue con el recetario y sin fotos nuevas.
AI_MONTHLY_BUDGET = float(os.getenv("AI_MONTHLY_BUDGET", "1"))
# Precio estimado por foto (calidad baja)
AI_IMAGE_COST = float(os.getenv("AI_IMAGE_COST", "0.006"))
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
PHOTO_DIR = DATA_DIR / "photos"

# Número de comensales para escalar la lista de la compra
SERVINGS = int(os.getenv("SERVINGS", "4"))

# Contraseña opcional para proteger la app (usuario: familia)
APP_PASSWORD = os.getenv("APP_PASSWORD", "")

TZ = os.getenv("TZ", "Europe/Madrid")


def ai_provider() -> str:
    if AI_PROVIDER in ("openai", "anthropic"):
        if AI_PROVIDER == "openai" and OPENAI_API_KEY:
            return "openai"
        if AI_PROVIDER == "anthropic" and ANTHROPIC_API_KEY:
            return "anthropic"
        return ""
    if OPENAI_API_KEY:
        return "openai"
    if ANTHROPIC_API_KEY:
        return "anthropic"
    return ""
