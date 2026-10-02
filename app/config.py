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
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")

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
