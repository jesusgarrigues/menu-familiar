"""Búsqueda de fotos de platos en internet (Pexels si hay PEXELS_API_KEY, Wikimedia Commons y Openverse).

1. Se busca con términos sencillos. Si una foto coincide claramente con el plato, se usa sin gastar IA.
2. Si las candidatas son dudosas, la IA (modelo barato) propone términos mejores y mira miniaturas
   pequeñas para confirmar cuál muestra el plato (así se evitan errores como «Melón», que también es un pueblo).
3. Sin IA se usa un filtro por palabras. Se guardan autor y licencia para los créditos.
"""
import base64
import io
import re

import requests

from . import ai, config, db
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


# Palabras que indican que la foto es de comida (en títulos, descripciones o categorías)
FOOD = re.compile(r"\b(food|dish|cuisine|meal|recipe|cooking|cooked|fruit|vegetable|dessert|soup|salad|stew|breakfast|lunch|dinner|"
                  r"comida|plato|platos|cocina|receta|gastronom\w*|aliment\w*|fruta|frutas|verdura|verduras|postre|sopa|ensalada|"
                  r"guiso|estofado|guisado|tapa|menu|men[uú])\b", re.I)
# Palabras que indican que NO es comida (pueblos, edificios, mapas...)
NOT_FOOD = re.compile(r"\b(ayuntamiento|concello|casa do concello|town ?hall|municipality|municipio|village|aldea|iglesia|"
                      r"church|igrexa|map|mapa|escudo|coat of arms|bandera|flag|street|calle|r[uú]a|station|estaci[oó]n|"
                      r"building|edificio|bridge|puente|river|r[ií]o|mountain|monta[nñ]a|portrait|retrato|football|f[uú]tbol|"
                      r"logo|sign|cartel|aerial|panor[aá]mica|skyline|castle|castillo)\b", re.I)

# Alimentos sueltos con nombre ambiguo: se buscan con un término más claro
SIMPLE = {
    "melon": "melon fruit", "sandia": "watermelon fruit", "naranja": "orange fruit", "platano": "banana fruit",
    "pera": "pear fruit", "manzana": "apple fruit", "kiwi": "kiwifruit", "mandarina": "mandarin orange fruit",
    "uva": "grapes fruit", "uvas": "grapes fruit", "pina": "pineapple fruit", "fresa": "strawberries fruit",
    "fresas": "strawberries fruit", "melocoton": "peach fruit", "yogur": "yogurt bowl", "natillas": "natillas custard dessert",
    "flan": "flan caramel dessert", "fruta": "fresh fruit bowl", "fruta temporada": "fresh fruit bowl",
    "pan": "bread loaf", "arroz con leche": "arroz con leche dessert", "cuajada": "cuajada dessert",
}


def queries(name: str) -> list[str]:
    words = _words(name)
    out = []
    simple = SIMPLE.get(" ".join(words))
    if simple:
        out.append(simple)
    out.append(name)
    if len(words) > 2:
        out.append(" ".join(words[:2]))
    return list(dict.fromkeys(q for q in out if q))


def looks_like_food(name: str, text: str, query: str) -> bool:
    """Evita fotos que no son de comida (p. ej. «Melón», que también es un pueblo de Ourense)."""
    if NOT_FOOD.search(text or ""):
        return False
    if relevance(name, text) >= 0.5 and len(_words(name)) >= 2 and FOOD.search(text or ""):
        return True
    if query in SIMPLE.values():
        eng = query.split()[0]
        return eng[:5].lower() in norm(text) and not NOT_FOOD.search(text)
    # Platos de varias palabras muy específicas ("lentejas estofadas") o con contexto de comida
    if relevance(name, text) >= 0.5 and (len(_words(name)) >= 2 or FOOD.search(text or "")):
        return True
    return False


def is_clear(name: str, c: dict) -> bool:
    """Coincidencia clara: el título habla del plato (casi todas sus palabras) y es comida. Se usa sin consultar a la IA."""
    text = c.get("title", "")
    if NOT_FOOD.search(text) or len(_words(name)) < 2:
        return False  # los nombres de una sola palabra («Melón») siempre son dudosos
    return relevance(name, text) >= 0.75 and bool(FOOD.search(text))


class ProviderError(RuntimeError):
    pass


def _get(url: str, **kw):
    r = requests.get(url, timeout=TIMEOUT, **kw)
    if not r.ok:
        raise ProviderError(f"HTTP {r.status_code} {r.text[:120]!r}")
    return r.json()


# ---------------------------------------------------------------------------
# Proveedores. Cada uno devuelve una lista de candidatos:
# {"url", "thumb", "title", "credit", "credit_url", "license", "source"}
# ---------------------------------------------------------------------------

def pexels(q: str) -> list[dict] | None:
    if not config.PEXELS_API_KEY:
        return None  # sin clave no se consulta
    data = _get("https://api.pexels.com/v1/search",
                params={"query": q, "per_page": 8, "locale": "es-ES", "orientation": "landscape"},
                headers={"Authorization": config.PEXELS_API_KEY, **UA})
    out = []
    for p in data.get("photos", []):
        out.append({"url": p["src"].get("large") or p["src"].get("medium"), "thumb": p["src"].get("medium"),
                    "title": p.get("alt") or q,
                    "credit": f"{p.get('photographer', '')} (Pexels)", "credit_url": p.get("url", ""),
                    "license": "Licencia Pexels", "source": "pexels", "trusted": True})
    return out


def wikimedia(q: str) -> list[dict]:
    data = _get("https://commons.wikimedia.org/w/api.php", params={
        "action": "query", "format": "json", "generator": "search", "gsrsearch": f"{q} filetype:bitmap",
        "gsrnamespace": 6, "gsrlimit": 10, "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": 800}, headers=UA)
    out = []
    pages = (data.get("query") or {}).get("pages", {})
    for p in sorted(pages.values(), key=lambda x: x.get("index", 99)):
        info = (p.get("imageinfo") or [{}])[0]
        if info.get("mime") not in ("image/jpeg", "image/png", "image/webp") or info.get("width", 0) < 400:
            continue
        meta = info.get("extmetadata") or {}
        artist = re.sub(r"<[^>]+>", "", (meta.get("Artist") or {}).get("value", "")).strip()
        desc = re.sub(r"<[^>]+>", "", (meta.get("ImageDescription") or {}).get("value", ""))
        cats = (meta.get("Categories") or {}).get("value", "").replace("|", " ")
        thumb = (info.get("thumburl") or "").replace("/800px-", "/320px-") or None
        out.append({"url": info.get("thumburl") or info.get("url"), "thumb": thumb,
                    "title": f"{p.get('title', '')} {desc} {cats}"[:800],
                    "credit": f"{artist or 'Autor desconocido'} (Wikimedia Commons)",
                    "credit_url": info.get("descriptionurl", ""),
                    "license": (meta.get("LicenseShortName") or {}).get("value", ""), "source": "wikimedia"})
    return out


def openverse(q: str) -> list[dict]:
    data = _get("https://api.openverse.org/v1/images/", params={"q": q, "page_size": 12, "mature": "false"}, headers=UA)
    out = []
    for it in data.get("results", []):
        if (it.get("width") or 0) and it["width"] < 400:
            continue
        tags = " ".join(t.get("name", "") for t in it.get("tags") or [])
        lic = f"CC {str(it.get('license', '')).upper()} {it.get('license_version', '')}".strip()
        out.append({"url": it.get("url"), "thumb": it.get("thumbnail"), "title": f"{it.get('title', '')} {tags}"[:400],
                    "credit": f"{it.get('creator') or 'Autor desconocido'} (Openverse)",
                    "credit_url": it.get("foreign_landing_url", ""), "license": lic, "source": "openverse"})
    return out


PROVIDERS = [pexels, wikimedia, openverse]


def _thumb_jpeg(url: str) -> bytes | None:
    """Descarga una miniatura y la reduce (para que la IA la mire gastando muy poco)."""
    try:
        r = requests.get(url, headers=UA, timeout=TIMEOUT)
        if not r.ok or not r.headers.get("content-type", "").startswith("image/"):
            db.debug(f"Miniatura no disponible ({getattr(r, 'status_code', '?')}): {url[:120]}")
            return None
        from PIL import Image
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
        im.thumbnail((256, 256))
        out = io.BytesIO()
        im.save(out, "JPEG", quality=70)
        return out.getvalue()
    except Exception as e:
        db.debug(f"Miniatura no disponible ({type(e).__name__}): {url[:120]}")
        return None


def _candidates(name: str, qs: list[str], blocked: set[str], seen: set[str] | None = None) -> list[dict]:
    cands, seen = [], seen if seen is not None else set()
    answered = failed = 0
    for q in qs:
        for provider in PROVIDERS:
            pname = provider.__name__
            try:
                res = provider(q)
            except (requests.RequestException, ProviderError, ValueError) as e:
                db.warn(f"Foto «{name}»: {pname} no responde para «{q}» ({type(e).__name__}: {str(e)[:160]})")
                failed += 1
                continue
            if res is None:
                continue
            answered += 1
            kept = 0
            for c in res:
                url = c.get("url")
                if not url or url in blocked or url in seen:
                    continue
                if NOT_FOOD.search(c.get("title", "")):
                    db.debug(f"Foto «{name}»: descartada por no ser comida: {c.get('title', '')[:80]}")
                    continue
                seen.add(url)
                cands.append(dict(c, query=q))
                kept += 1
            db.debug(f"Foto «{name}»: {pname} «{q}» → {len(res)} resultados, {kept} útiles")
        if len(cands) >= 16:
            break
    if failed and not answered:
        raise ProviderError("ninguna web de fotos responde (¿sin conexión a internet?)")
    return cands


def _download(name: str, c: dict):
    try:
        img = requests.get(c["url"], headers=UA, timeout=TIMEOUT)
    except requests.RequestException as e:
        db.warn(f"Foto «{name}»: no se pudo descargar {c['url'][:120]} ({type(e).__name__})")
        return None
    if img.ok and img.headers.get("content-type", "").startswith("image/") and len(img.content) < 12_000_000:
        return img.content, {k: c.get(k, "") for k in ("source", "credit", "credit_url", "license", "url")}
    db.warn(f"Foto «{name}»: descarga no válida (HTTP {img.status_code}, {img.headers.get('content-type', '')}) "
            f"{c['url'][:120]}")
    return None


def _ai_confirm(name: str, cands: list[dict]):
    """La IA mira miniaturas de las candidatas dudosas (tandas de 6, máximo 2) y confirma cuál es el plato.

    Devuelve (bytes, créditos) si confirma una; None si ha visto las candidatas y ninguna sirve.
    Lanza excepción si la IA no ha podido responder.
    """
    from concurrent.futures import ThreadPoolExecutor
    for start in (0, 6):
        batch = cands[start:start + 6]
        if not batch:
            break
        with ThreadPoolExecutor(max_workers=6) as ex:
            thumbs = list(ex.map(lambda c: _thumb_jpeg(c.get("thumb") or c["url"]), batch))
        pool = [(c, t) for c, t in zip(batch, thumbs) if t]
        if not pool:
            db.debug(f"Foto «{name}»: ninguna miniatura de la tanda {start // 6 + 1} se pudo descargar")
            continue
        best = ai.pick_photo(name, [t for _, t in pool])
        if best is None or not 0 <= best < len(pool):
            db.debug(f"Foto «{name}»: la IA no ve el plato en ninguna de las {len(pool)} fotos de la tanda {start // 6 + 1}")
            continue
        c = pool[best][0]
        db.debug(f"Foto «{name}»: la IA confirma la foto {best} ({c['source']}: {c.get('title', '')[:80]})")
        got = _download(name, c)
        if got:
            return got
    return None


def find_photo(name: str, blocked: set[str] | None = None) -> tuple[bytes, dict] | None:
    """Busca una foto adecuada del plato. Devuelve (bytes, créditos) o None.

    1. Búsqueda con términos sencillos. Si alguna candidata coincide claramente, se usa (sin IA).
    2. Si hay IA: propone términos mejores y confirma, mirando miniaturas, cuál de las dudosas es el plato.
    3. Sin IA (o si falla): filtro por palabras.
    """
    blocked = blocked or set()
    qs = queries(name)
    seen: set[str] = set()
    cands = _candidates(name, qs, blocked, seen)
    db.debug(f"Foto «{name}»: {len(cands)} candidatas con {qs}")
    for c in cands:
        if is_clear(name, c):
            db.debug(f"Foto «{name}»: coincidencia clara en {c['source']} ({c.get('title', '')[:80]})")
            got = _download(name, c)
            if got:
                return got

    if ai.available():
        try:
            ai_qs = [q for q in ai.photo_queries(name) if q not in qs]
            db.debug(f"Foto «{name}»: la IA propone buscar {ai_qs}")
            more = _candidates(name, ai_qs, blocked, seen)
            for c in more:
                if is_clear(name, c):
                    got = _download(name, c)
                    if got:
                        return got
            # Primero las más prometedoras: bancos de fotos de comida y títulos que se parecen al plato
            pool = sorted(more + cands, key=lambda c: (not c.get("trusted"), -relevance(name, c.get("title", "")),
                                                       not FOOD.search(c.get("title", ""))))
            if not pool:
                db.info(f"Foto «{name}»: ninguna candidata en internet")
                return None
            got = _ai_confirm(name, pool)
            if got:
                return got
            db.info(f"Foto «{name}»: la IA ha revisado {min(len(pool), 12)} fotos de internet y ninguna muestra el plato")
            return None
        except Exception as e:
            db.warn(f"Foto «{name}»: la IA no ha podido revisar las fotos ({type(e).__name__}: {str(e)[:200]}); "
                    f"se usa el filtro por palabras")
    else:
        db.debug(f"Foto «{name}»: IA no disponible, se usa el filtro por palabras")

    for c in cands:
        if c.get("trusted") or looks_like_food(name, c.get("title", ""), c.get("query", "")):
            got = _download(name, c)
            if got:
                return got
    db.info(f"Foto «{name}»: ninguna de las {len(cands)} candidatas encaja con el plato")
    return None
