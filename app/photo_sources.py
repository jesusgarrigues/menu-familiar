"""Búsqueda de fotos de platos en internet (gratis) antes de recurrir a la IA.

Orden: Pexels (si hay PEXELS_API_KEY, fotos de mucha calidad) → Wikimedia Commons → Openverse.
Solo se aceptan fotos cuyo título o descripción encaja con el nombre del plato.
Se guarda el autor y la licencia de cada foto para mostrar los créditos en Ajustes.
"""
import re

import requests

from . import config
from .text import norm

UA = {"User-Agent": "menu-familiar/1.0 (https://github.com/jesusgarrigues/menu-familiar; app familiar de menús)"}
TIMEOUT = 20


def _words(text: str) -> list[str]:
    stop = {"de", "del", "con", "y", "e", "a", "al", "la", "las", "el", "los", "en", "su", "o", "para", "por", "sin",
            "casero", "casera", "integral", "integrales", "temporada", "plato", "receta", "jpg", "png", "file", "archivo"}
    return [w for w in re.findall(r"[a-zñ]+", norm(text)) if len(w) > 2 and w not in stop]


def relevance(name: str, text: str) -> float:
    """Proporción de palabras del plato que aparecen en el título/etiquetas de la foto (tolera plurales)."""
    want = _words(name)
    have = _words(text)
    if not want:
        return 0.0
    hit = sum(1 for w in want if any(h[:5] == w[:5] for h in have))
    score = hit / len(want)
    # La primera palabra suele ser la clave ("lentejas", "merluza", "crema"...)
    if not any(h[:5] == want[0][:5] for h in have):
        score *= 0.5
    return score


def queries(name: str) -> list[str]:
    words = _words(name)
    out = [name]
    if len(words) > 2:
        out.append(" ".join(words[:2]))
    return list(dict.fromkeys(q for q in out if q))


# ---------------------------------------------------------------------------
# Proveedores. Cada uno devuelve una lista de candidatos:
# {"url", "title", "credit", "credit_url", "license", "source"}
# ---------------------------------------------------------------------------

def pexels(q: str) -> list[dict]:
    if not config.PEXELS_API_KEY:
        return []
    r = requests.get("https://api.pexels.com/v1/search",
                     params={"query": q, "per_page": 8, "locale": "es-ES", "orientation": "landscape"},
                     headers={"Authorization": config.PEXELS_API_KEY, **UA}, timeout=TIMEOUT)
    if not r.ok:
        return []
    out = []
    for p in r.json().get("photos", []):
        out.append({"url": p["src"].get("large") or p["src"].get("medium"), "title": p.get("alt") or q,
                    "credit": f"{p.get('photographer', '')} (Pexels)", "credit_url": p.get("url", ""),
                    "license": "Licencia Pexels", "source": "pexels", "trusted": True})
    return out


def wikimedia(q: str) -> list[dict]:
    r = requests.get("https://commons.wikimedia.org/w/api.php", params={
        "action": "query", "format": "json", "generator": "search", "gsrsearch": f"{q} filetype:bitmap",
        "gsrnamespace": 6, "gsrlimit": 10, "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": 800}, headers=UA, timeout=TIMEOUT)
    if not r.ok:
        return []
    out = []
    pages = (r.json().get("query") or {}).get("pages", {})
    for p in sorted(pages.values(), key=lambda x: x.get("index", 99)):
        info = (p.get("imageinfo") or [{}])[0]
        if info.get("mime") not in ("image/jpeg", "image/png", "image/webp") or info.get("width", 0) < 400:
            continue
        meta = info.get("extmetadata") or {}
        artist = re.sub(r"<[^>]+>", "", (meta.get("Artist") or {}).get("value", "")).strip()
        desc = re.sub(r"<[^>]+>", "", (meta.get("ImageDescription") or {}).get("value", ""))
        out.append({"url": info.get("thumburl") or info.get("url"), "title": f"{p.get('title', '')} {desc}"[:400],
                    "credit": f"{artist or 'Autor desconocido'} (Wikimedia Commons)",
                    "credit_url": info.get("descriptionurl", ""),
                    "license": (meta.get("LicenseShortName") or {}).get("value", ""), "source": "wikimedia"})
    return out


def openverse(q: str) -> list[dict]:
    r = requests.get("https://api.openverse.org/v1/images/", params={
        "q": q, "page_size": 12, "mature": "false"}, headers=UA, timeout=TIMEOUT)
    if not r.ok:
        return []
    out = []
    for it in r.json().get("results", []):
        if (it.get("width") or 0) and it["width"] < 400:
            continue
        tags = " ".join(t.get("name", "") for t in it.get("tags") or [])
        lic = f"CC {str(it.get('license', '')).upper()} {it.get('license_version', '')}".strip()
        out.append({"url": it.get("url"), "title": f"{it.get('title', '')} {tags}"[:400],
                    "credit": f"{it.get('creator') or 'Autor desconocido'} (Openverse)",
                    "credit_url": it.get("foreign_landing_url", ""), "license": lic, "source": "openverse"})
    return out


PROVIDERS = [pexels, wikimedia, openverse]


def find_photo(name: str) -> tuple[bytes, dict] | None:
    """Busca una foto adecuada del plato. Devuelve (bytes, créditos) o None."""
    for q in queries(name):
        for provider in PROVIDERS:
            try:
                cands = provider(q)
            except requests.RequestException:
                continue
            for c in cands:
                if not c.get("url"):
                    continue
                if not c.get("trusted") and relevance(name, c["title"]) < 0.5:
                    continue
                try:
                    img = requests.get(c["url"], headers=UA, timeout=TIMEOUT)
                except requests.RequestException:
                    continue
                if img.ok and img.headers.get("content-type", "").startswith("image/") and len(img.content) < 12_000_000:
                    return img.content, {k: c.get(k, "") for k in ("source", "credit", "credit_url", "license")}
    return None
