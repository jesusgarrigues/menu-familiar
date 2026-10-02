"""Fotos de los platos: se generan UNA vez por plato (calidad baja) y se guardan para siempre.

- Los nombres parecidos comparten foto ("Cocido completo" / "Cocido madrileño", "Pasta integral boloñesa" /
  "Pasta a la boloñesa").
- Se generan en segundo plano y de una en una, solo cuando el plato aparece en pantalla.
- Sin clave de OpenAI, o con el límite de gasto alcanzado, la app muestra un marcador en su lugar.
"""
import hashlib
import io
import queue
import re
import threading

from . import ai, config, db
from .text import ALLERGEN_RE, norm

STOP = {"de", "del", "con", "y", "e", "a", "al", "la", "las", "el", "los", "en", "su", "o", "para", "por", "sin",
        "casero", "casera", "caseros", "caseras", "integral", "integrales", "temporada", "fresco", "fresca",
        "estilo", "jugo", "salsa", "plancha", "horno", "racion", "variado", "variada", "natural"}
SYNONYMS = [
    (r"\bcocido (completo|madrileno)\b", "cocido"),
    (r"\b(macarrones|espaguetis|tallarines|plumas|helices|lazos|tiburones)\b", "pasta"),
    (r"\bbolonesa\b", "bolonesa"),
    (r"\bfilete(s)?\b", "filete"),
    (r"\b(fruta de temporada|pieza de fruta)\b", "fruta"),
]

_q: "queue.Queue[tuple[str, str]]" = queue.Queue()
_started = False
_lock = threading.Lock()


def key_for(name: str) -> str:
    t = norm(ALLERGEN_RE.sub("", name or ""))
    for pat, rep in SYNONYMS:
        t = re.sub(pat, rep, t)
    words = []
    for w in re.findall(r"[a-zñ]+", t):
        if w in STOP or len(w) < 3:
            continue
        if len(w) > 4 and w.endswith("s"):
            w = w[:-1]
        if w not in words:
            words.append(w)
    return " ".join(sorted(words))


def _similar(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _file_for(key: str) -> str:
    return hashlib.sha1(key.encode()).hexdigest()[:20] + ".webp"


def lookup(name: str):
    """Devuelve (ruta, estado). Estado: 'ok' | 'pending' | 'none'."""
    key = key_for(name)
    if not key:
        return None, "none"
    with db.tx() as c:
        row = c.execute("SELECT * FROM photos WHERE key=?", (key,)).fetchone()
        if not row or row["status"] != "ok":
            # ¿Hay una foto de un plato casi igual? Se reutiliza (gratis)
            best, score = None, 0.0
            for r in c.execute("SELECT key, file FROM photos WHERE status='ok'"):
                s = _similar(key, r["key"])
                if s > score:
                    best, score = r, s
            if best is not None and score >= 0.75:
                path = config.PHOTO_DIR / best["file"]
                if path.exists():
                    return path, "ok"
    if row and row["status"] == "ok":
        path = config.PHOTO_DIR / row["file"]
        if path.exists():
            return path, "ok"
    if row and row["status"] == "pending":
        _ensure_worker()
        return None, "pending"
    if row and row["status"] == "error":
        return None, "none"
    if not ai.photos_available():
        return None, "none"
    with db.tx() as c:
        c.execute("INSERT OR REPLACE INTO photos(key, name, file, status) VALUES(?,?,?,'pending')",
                  (key, name, _file_for(key)))
    _q.put((key, name))
    _ensure_worker()
    return None, "pending"


def _ensure_worker():
    global _started
    with _lock:
        if _started:
            return
        _started = True
    # Recupera las fotos que quedaron pendientes (p. ej. tras reiniciar)
    with db.tx() as c:
        for r in c.execute("SELECT key, name FROM photos WHERE status='pending'").fetchall():
            _q.put((r["key"], r["name"]))
    threading.Thread(target=_worker, daemon=True, name="photo-worker").start()


def _worker():
    done: set[str] = set()
    while True:
        key, name = _q.get()
        if key in done:
            continue
        done.add(key)
        try:
            data = ai.generate_photo(name)
            data = _shrink(data)
            (config.PHOTO_DIR / _file_for(key)).write_bytes(data)
            status = "ok"
        except Exception as e:
            db.log("warn", f"No se pudo crear la foto de «{name}»: {e}")
            status = "error"
        with db.tx() as c:
            c.execute("UPDATE photos SET status=? WHERE key=?", (status, key))


def _shrink(data: bytes, size: int = 640) -> bytes:
    """Reduce la foto a tamaño móvil (carga más rápida). Si no hay Pillow, la deja como está."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data)).convert("RGB")
        im.thumbnail((size, size))
        out = io.BytesIO()
        im.save(out, "WEBP", quality=78)
        return out.getvalue()
    except Exception:
        return data


def stats() -> dict:
    with db.tx() as c:
        rows = c.execute("SELECT status, COUNT(*) n FROM photos GROUP BY status").fetchall()
    return {r["status"]: r["n"] for r in rows}
