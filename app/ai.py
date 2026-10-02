"""IA opcional (OpenAI o Anthropic) para leer el PDF y proponer platos.

Sin clave de API la app sigue funcionando con el lector de PDF y el recetario
locales; con clave, la extracción es más fiable y las propuestas más variadas.
"""
import base64
import json
import re

import requests

from . import config

SECTIONS = ["Frutería", "Carnicería", "Pescadería", "Huevos y lácteos", "Despensa", "Panadería", "Congelados", "Otros"]
GROUPS = ["verdura", "legumbre", "pescado", "carne", "huevo", "pasta", "arroz", "patata", "lacteo", "fruta"]

DISH_SCHEMA = (
    '{"name": "nombre del plato", "groups": [grupos de: ' + ", ".join(GROUPS) + '], '
    '"ingredients": [{"name": "ingrediente", "qty": "cantidad para ' + str(config.SERVINGS) +
    ' personas", "section": una de: ' + ", ".join(SECTIONS) + '}]}'
)


class AIError(RuntimeError):
    pass


def available() -> bool:
    return bool(config.ai_provider())


def _parse_json(text: str):
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=0)
    return json.loads(text[start:])


def complete_json(system: str, prompt: str, pdf_bytes: bytes | None = None, max_tokens: int = 8000):
    provider = config.ai_provider()
    if not provider:
        raise AIError("No hay clave de IA configurada")
    if provider == "openai":
        content = [{"type": "text", "text": prompt}]
        if pdf_bytes:
            content.insert(0, {"type": "file", "file": {
                "filename": "menu.pdf",
                "file_data": "data:application/pdf;base64," + base64.b64encode(pdf_bytes).decode(),
            }})
        r = requests.post(
            f"{config.OPENAI_BASE_URL.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
            json={
                "model": config.OPENAI_MODEL,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
                "response_format": {"type": "json_object"},
            },
            timeout=180,
        )
        if not r.ok:
            raise AIError(f"OpenAI {r.status_code}: {r.text[:300]}")
        return _parse_json(r.json()["choices"][0]["message"]["content"])

    content = [{"type": "text", "text": prompt}]
    if pdf_bytes:
        content.insert(0, {"type": "document", "source": {
            "type": "base64", "media_type": "application/pdf",
            "data": base64.b64encode(pdf_bytes).decode()}})
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": config.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"},
        json={"model": config.ANTHROPIC_MODEL, "max_tokens": max_tokens, "system": system,
              "messages": [{"role": "user", "content": content}]},
        timeout=180,
    )
    if not r.ok:
        raise AIError(f"Anthropic {r.status_code}: {r.text[:300]}")
    text = "".join(b.get("text", "") for b in r.json().get("content", []))
    return _parse_json(text)


SYSTEM = ("Eres un asistente de nutrición infantil y cocina casera española. "
          "Respondes SIEMPRE solo con JSON válido, sin texto adicional.")


def extract_menu(pdf_bytes: bytes, text: str, title: str = "") -> dict:
    prompt = f"""Este PDF es el menú mensual del comedor escolar ({title}).
Extrae TODOS los días lectivos. Para cada día: la fecha (YYYY-MM-DD), la lista de platos
en orden (primero, segundo con guarnición, postre), la recomendación de cena si el menú la incluye
(cópiala tal cual, aunque sea solo una lista de ingredientes) y una nota si es festivo o especial.
Si las recomendaciones de cena están en una tabla aparte por semanas o por días, asígnalas a su día.
Devuelve:
{{"year": 2026, "month": 10, "days": [{{"date": "2026-10-01", "dishes": ["..."], "dinner_hint": "", "note": ""}}]}}

Texto extraído del PDF (puede estar desordenado, úsalo solo como apoyo):
{text[:12000]}"""
    data = complete_json(SYSTEM, prompt, pdf_bytes=pdf_bytes)
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


def suggest_dinners(lunch: list[str], hint: str, n: int = 4, avoid: list[str] | None = None) -> list[dict]:
    prompt = f"""Los niños han comido hoy en el cole: {', '.join(lunch) or 'desconocido'}.
El menú del cole recomienda para la cena: "{hint or 'sin recomendación'}".
Propón {n} platos de cena distintos, sencillos (menos de 30 minutos), que gusten a niños y que
cumplan esa recomendación (si solo indica ingredientes o grupos de alimentos, conviértelos en platos concretos)
y complementen la comida sin repetirla. Evita: {', '.join(avoid or []) or 'nada'}.
Devuelve {{"dishes": [{DISH_SCHEMA}]}}"""
    data = complete_json(SYSTEM, prompt, max_tokens=3000)
    return data.get("dishes", [])[:n]


def weekend_menu(week_summary: str, deficits: list[str], avoid: list[str]) -> dict:
    prompt = f"""Esta semana la familia ha comido:
{week_summary}
Grupos de alimentos que han faltado o han salido poco: {', '.join(deficits) or 'ninguno'}.
Diseña la comida y la cena del sábado y del domingo para una familia con niños, que complementen
la semana (priorizando lo que ha faltado y sin repetir platos), con un plato apetecible de fin de semana.
Evita: {', '.join(avoid) or 'nada'}.
Devuelve {{"sabado": {{"comida": {DISH_SCHEMA}, "cena": {{...}}}}, "domingo": {{"comida": {{...}}, "cena": {{...}}}}}}"""
    return complete_json(SYSTEM, prompt, max_tokens=4000)
