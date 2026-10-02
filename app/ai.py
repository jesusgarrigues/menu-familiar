"""IA opcional (OpenAI o Anthropic), pensada para gastar lo mínimo.

Cómo se ahorra sin que se note:
- La app usa primero el recetario local; la IA solo entra cuando no hay platos que encajen.
- Lo que crea la IA se guarda en la biblioteca (tabla `library`) y se reutiliza gratis.
- Las cenas que faltan de una semana se piden en UNA sola llamada.
- Para proponer platos se usa un modelo muy barato (OPENAI_MODEL_FAST); el normal solo lee el PDF.
- Se piden respuestas cortas; los ingredientes solo del plato elegido y en lote.
- Las instrucciones fijas van siempre delante y en el mismo orden (descuento automático por caché).
- Hay un tope de gasto mensual (AI_MONTHLY_BUDGET); al llegar, la app sigue con el recetario.
"""
import base64
import json
import re
import time

import requests

from . import config, db

SECTIONS = ["Frutería", "Carnicería", "Pescadería", "Huevos y lácteos", "Despensa", "Panadería", "Congelados", "Otros"]
GROUPS = ["verdura", "legumbre", "pescado", "carne", "huevo", "pasta", "arroz", "patata", "lacteo", "fruta"]

# Precio aproximado en dólares por millón de tokens (entrada, salida)
PRICES = {
    "gpt-5-nano": (0.05, 0.40), "gpt-5-mini": (0.25, 2.00), "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4.1-mini": (0.40, 1.60), "gpt-4o-mini": (0.15, 0.60), "claude-haiku-4-5": (1.00, 5.00),
}


class AIError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Gasto y límite mensual
# ---------------------------------------------------------------------------

def _month() -> str:
    return time.strftime("%Y-%m")


def usage() -> dict:
    with db.tx() as c:
        row = c.execute("SELECT * FROM ai_usage WHERE month=?", (_month(),)).fetchone()
    data = dict(row) if row else {"month": _month(), "cost": 0.0, "calls": 0, "images": 0}
    data["budget"] = config.AI_MONTHLY_BUDGET
    return data


def _add_usage(cost: float, calls: int = 1, images: int = 0):
    with db.tx() as c:
        c.execute("INSERT INTO ai_usage(month, cost, calls, images) VALUES(?,?,?,?) "
                  "ON CONFLICT(month) DO UPDATE SET cost=cost+excluded.cost, calls=calls+excluded.calls, "
                  "images=images+excluded.images", (_month(), cost, calls, images))


def within_budget(extra: float = 0.0) -> bool:
    return usage()["cost"] + extra <= config.AI_MONTHLY_BUDGET


def available() -> bool:
    return bool(config.ai_provider()) and within_budget()


def photos_available() -> bool:
    return config.AI_PHOTOS and bool(config.OPENAI_API_KEY) and within_budget(config.AI_IMAGE_COST)


def _cost(model: str, tokens_in: int, tokens_out: int) -> float:
    pin, pout = next((v for k, v in PRICES.items() if model.startswith(k)), (1.0, 4.0))
    return (tokens_in * pin + tokens_out * pout) / 1_000_000


# ---------------------------------------------------------------------------
# Llamada genérica que devuelve JSON
# ---------------------------------------------------------------------------

def _parse_json(text: str):
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=0)
    return json.loads(text[start:])


def complete_json(system: str, prompt: str, pdf_bytes: bytes | None = None, max_tokens: int = 4000, fast: bool = True):
    provider = config.ai_provider()
    if not provider:
        raise AIError("No hay clave de IA configurada")
    if not within_budget():
        raise AIError("Se ha alcanzado el límite de gasto de IA de este mes")
    if provider == "openai":
        model = config.OPENAI_MODEL_FAST if fast and not pdf_bytes else config.OPENAI_MODEL
        content = [{"type": "text", "text": prompt}]
        if pdf_bytes:
            content.insert(0, {"type": "file", "file": {
                "filename": "menu.pdf",
                "file_data": "data:application/pdf;base64," + base64.b64encode(pdf_bytes).decode(),
            }})
        body = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
            "response_format": {"type": "json_object"},
        }
        if model.startswith("gpt-5"):
            body["reasoning_effort"] = "minimal"  # sin "pensar": más rápido y barato
        r = requests.post(f"{config.OPENAI_BASE_URL.rstrip('/')}/chat/completions",
                          headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"}, json=body, timeout=180)
        if not r.ok:
            raise AIError(f"OpenAI {r.status_code}: {r.text[:300]}")
        data = r.json()
        u = data.get("usage") or {}
        _add_usage(_cost(model, u.get("prompt_tokens", 0), u.get("completion_tokens", 0)))
        return _parse_json(data["choices"][0]["message"]["content"])

    model = config.ANTHROPIC_MODEL
    content = [{"type": "text", "text": prompt}]
    if pdf_bytes:
        content.insert(0, {"type": "document", "source": {
            "type": "base64", "media_type": "application/pdf",
            "data": base64.b64encode(pdf_bytes).decode()}})
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": config.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"},
        json={"model": model, "max_tokens": max_tokens,
              "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
              "messages": [{"role": "user", "content": content}]},
        timeout=180,
    )
    if not r.ok:
        raise AIError(f"Anthropic {r.status_code}: {r.text[:300]}")
    data = r.json()
    u = data.get("usage") or {}
    _add_usage(_cost(model, u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) // 10,
                     u.get("output_tokens", 0)))
    return _parse_json("".join(b.get("text", "") for b in data.get("content", [])))


# Instrucciones fijas (siempre idénticas, delante: así se aprovecha la caché del proveedor)
SYSTEM = (
    "Eres un asistente de nutrición infantil y cocina casera española para una familia con niños de primaria. "
    "Propones platos sencillos (menos de 30 minutos) pensados para que los niños se los coman con gusto: "
    "formatos que les encantan (tortillas, rebozados y empanados caseros, croquetas, hamburguesitas, albóndigas, "
    "pasta, arroz, cremas suaves, pizzas y wraps caseros, quesadillas, sándwiches calientes), con la verdura "
    "integrada o camuflada en el plato (triturada, en crema, rallada o dentro de la masa). "
    "Evita platos de adulto: verdura sola como plato principal, ensaladas complejas, pescados con espinas, "
    "marisco, sabores fuertes, picante, frutos secos enteros y preparaciones laboriosas. "
    "Respondes SIEMPRE solo con JSON válido, sin texto adicional, y con nombres de plato cortos en español "
    "(primera letra en mayúscula, el resto en minúscula). "
    "Grupos de alimentos válidos: " + ", ".join(GROUPS) + ". "
    "Secciones de la compra válidas: " + ", ".join(SECTIONS) + "."
)


def extract_menu(pdf_bytes: bytes, text: str, title: str = "") -> dict:
    prompt = f"""Tarea: extraer el menú mensual del comedor escolar del PDF adjunto.
Extrae TODOS los días lectivos. Para cada día: la fecha (YYYY-MM-DD), la lista de platos en orden
(primero, segundo con guarnición, postre) tal y como aparecen (incluidos los números de alérgenos entre paréntesis),
la recomendación de cena si el menú la incluye (cópiala tal cual, aunque sea solo una lista de ingredientes)
y una nota si es festivo o especial. Si las recomendaciones de cena están en una tabla aparte, asígnalas a su día.
Formato: {{"year": 2026, "month": 10, "days": [{{"date": "2026-10-01", "dishes": ["..."], "dinner_hint": "", "note": ""}}]}}

Título del archivo: {title}
Texto extraído del PDF (puede estar desordenado, úsalo solo como apoyo):
{text[:12000]}"""
    data = complete_json(SYSTEM, prompt, pdf_bytes=pdf_bytes, max_tokens=8000, fast=False)
    days = {}
    for d in data.get("days", []):
        if not d.get("date"):
            continue
        days[d["date"]] = {
            "dishes": [str(x).strip() for x in d.get("dishes", []) if str(x).strip()],
            "dinner_hint": (d.get("dinner_hint") or "").strip(),
            "note": (d.get("note") or "").strip(),
        }
    return {"year": int(data["year"]), "month": int(data["month"]), "days": days, "parser": "ia"}


def suggest_week(items: list[dict], n: int = 3, avoid: list[str] | None = None) -> dict[str, list[dict]]:
    """Cenas para varios días en UNA llamada. items: [{date, lunch, hint}] -> {date: [{name, groups}]}."""
    lines = "\n".join(f"- {it['date']}: comida del cole: {', '.join(it['lunch']) or 'desconocida'}; "
                      f"recomendación de cena: {it['hint'] or 'ninguna'}" for it in items)
    prompt = f"""Tarea: proponer cenas.
Para cada día, propón {n} cenas distintas para niños que cumplan la recomendación del cole (si solo indica ingredientes
o grupos, conviértelos en platos concretos que gusten a los niños) y complementen la comida sin repetirla.
No repitas platos entre días.
Formato: {{"days": {{"YYYY-MM-DD": [{{"name": "...", "groups": ["..."]}}]}}}}
Evita: {', '.join(avoid or []) or 'nada'}
Días:
{lines}"""
    data = complete_json(SYSTEM, prompt, max_tokens=1500)
    out = {}
    for k, dishes in (data.get("days") or {}).items():
        out[k] = [{"name": str(d.get("name", "")).strip(), "groups": [g for g in d.get("groups", []) if g in GROUPS]}
                  for d in dishes if d.get("name")][:n]
    return out


def ingredients(names: list[str]) -> dict[str, list[dict]]:
    """Ingredientes de varios platos en UNA llamada (solo de los elegidos)."""
    prompt = f"""Tarea: lista de ingredientes para la compra.
Para cada plato, ingredientes principales con cantidad para {config.SERVINGS} personas (sin sal, agua ni especias básicas).
Formato: {{"dishes": {{"nombre del plato": [{{"name": "...", "qty": "...", "section": "..."}}]}}}}
Platos:
""" + "\n".join(f"- {n}" for n in names)
    data = complete_json(SYSTEM, prompt, max_tokens=2500)
    out = {}
    for name, ings in (data.get("dishes") or {}).items():
        out[name.strip().lower()] = [
            {"name": str(i.get("name", "")).strip(), "qty": str(i.get("qty", "")).strip(),
             "section": i.get("section") if i.get("section") in SECTIONS else "Otros"}
            for i in ings if i.get("name")]
    return out


def generate_photo(name: str) -> bytes:
    """Foto del plato en calidad baja (la más barata). Devuelve los bytes de la imagen."""
    if not photos_available():
        raise AIError("Fotos con IA no disponibles (sin clave de OpenAI o límite alcanzado)")
    prompt = (f"Fotografía gastronómica realista de un plato casero español para niños: {name}. "
              "Ración familiar servida en un plato blanco sencillo sobre una mesa de madera clara, luz natural, "
              "vista ligeramente cenital, apetecible, estilo foto de app de comida a domicilio. "
              "Sin texto, sin logotipos, sin personas, sin manos.")
    r = requests.post(
        f"{config.OPENAI_BASE_URL.rstrip('/')}/images/generations",
        headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
        json={"model": config.OPENAI_IMAGE_MODEL, "prompt": prompt, "size": "1024x1024", "quality": "low",
              "output_format": "webp", "output_compression": 80, "n": 1},
        timeout=180,
    )
    if not r.ok:
        raise AIError(f"OpenAI imágenes {r.status_code}: {r.text[:300]}")
    _add_usage(config.AI_IMAGE_COST, calls=1, images=1)
    return base64.b64decode(r.json()["data"][0]["b64_json"])
