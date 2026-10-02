"""Fotos de los platos: se consiguen UNA vez por plato y se guardan para siempre.

Orden para cada plato:
1. Se busca en internet (Pexels, Wikimedia Commons, Openverse). Si una foto coincide claramente
   con el plato, se usa directamente (gratis).
2. Si las candidatas son dudosas, la IA mira las miniaturas y confirma cuál muestra el plato.
3. Si no aparece ninguna adecuada, la IA crea la foto (respetando el límite de 5 imágenes/minuto de OpenAI).

- Si una foto no es correcta, desde la app se puede pedir otra (la descartada no vuelve a salir).
- Los nombres parecidos comparten foto ("Cocido completo" / "Cocido madrileño").
- Varias fotos se buscan a la vez (PHOTO_WORKERS) y primero las que se están viendo en pantalla.
- Todo el proceso queda en el registro (nivel «debug» para ver cada paso).
"""
import hashlib
import io
import re
import threading
import time

from . import ai, config, db, photo_sources
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

RETRY_ERROR = 600          # un fallo (red, IA...) se reintenta a los 10 minutos
RETRY_MISSING = 86400      # si no se encontró ni se pudo crear, se reintenta al día siguiente

# Cola con prioridad: se atiende primero el plato que se ha pedido más recientemente (el que está en pantalla)
_wanted: dict[str, list] = {}   # key -> [nombre, última vez que se pidió]
_active: set[str] = set()       # se están buscando ahora
_cv = threading.Condition()
_threads: list[threading.Thread] = []
_gen_lock = threading.Lock()    # las fotos con IA se crean de una en una


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


def _ts(s: str | None) -> float:
    try:
        return time.mktime(time.strptime(s, "%Y-%m-%d %H:%M:%S"))
    except Exception:
        return 0.0


def lookup(name: str):
    """Devuelve (ruta, estado). Estado: 'ok' | 'pending' | 'none'."""
    key = key_for(name)
    if not key:
        return None, "none"
    with db.tx() as c:
        row = c.execute("SELECT * FROM photos WHERE key=?", (key,)).fetchone()
        similar = None
        if not row or row["status"] != "ok":
            # ¿Hay una foto de un plato casi igual? Se reutiliza (gratis)
            score = 0.0
            for r in c.execute("SELECT key, file FROM photos WHERE status='ok'"):
                s = _similar(key, r["key"])
                if s > score:
                    similar, score = r, s
            if score < 0.75:
                similar = None
    if row and row["status"] == "ok":
        path = config.PHOTO_DIR / row["file"]
        if path.exists():
            return path, "ok"
        db.warn(f"Foto «{name}»: el archivo guardado no existe, se vuelve a buscar")
        row = None
    if similar is not None and (config.PHOTO_DIR / similar["file"]).exists():
        return config.PHOTO_DIR / similar["file"], "ok"
    if row and row["status"] == "pending":
        _want(key, name)
        return None, "pending"
    if row and row["status"] in ("error", "missing"):
        wait = RETRY_ERROR if row["status"] == "error" else RETRY_MISSING
        if time.time() - _ts(row["updated"] or row["created"]) < wait:
            return None, "none"
    if not enabled():
        return None, "none"
    with db.tx() as c:
        c.execute("INSERT OR REPLACE INTO photos(key, name, file, status, updated) "
                  "VALUES(?,?,?,'pending',datetime('now','localtime'))", (key, name, _file_for(key)))
    db.debug(f"Foto «{name}»: en cola")
    _want(key, name)
    return None, "pending"


def check(name: str) -> str:
    """Estado de la foto sin descargarla: 'ok' | 'pending' | 'none'."""
    return lookup(name)[1]


def reject(name: str) -> str:
    """La foto no es correcta: se descarta para siempre y se busca otra."""
    key = key_for(name)
    with db.tx() as c:
        row = c.execute("SELECT * FROM photos WHERE key=?", (key,)).fetchone()
        if row and row["url"]:
            c.execute("INSERT OR IGNORE INTO photo_block(key, url) VALUES(?,?)", (key, row["url"]))
        c.execute("INSERT OR REPLACE INTO photos(key, name, file, status, updated) "
                  "VALUES(?,?,?,'pending',datetime('now','localtime'))", (key, name, _file_for(key)))
    try:
        (config.PHOTO_DIR / _file_for(key)).unlink()
    except FileNotFoundError:
        pass
    db.info(f"Foto «{name}»: descartada por el usuario ({(row['url'] if row else '') or 'sin URL'}); se busca otra")
    _want(key, name)
    return "pending"


def retry_missing() -> int:
    """Vuelve a buscar ya las fotos que no se encontraron o fallaron."""
    with db.tx() as c:
        rows = c.execute("SELECT key, name FROM photos WHERE status IN ('missing','error')").fetchall()
        c.execute("UPDATE photos SET status='pending', updated=datetime('now','localtime') "
                  "WHERE status IN ('missing','error')")
    for r in rows:
        _want(r["key"], r["name"])
    db.info(f"Fotos: {len(rows)} sin foto vuelven a buscarse")
    return len(rows)


def migrate():
    """Ajustes de una sola vez para bases de datos de versiones anteriores."""
    rev = db.get_setting("photos_rev")
    if rev not in ("2", "3"):
        # Vuelve a buscar las fotos elegidas con el método antiguo (sin revisión de la IA)
        with db.tx() as c:
            rows = c.execute("SELECT key, file FROM photos WHERE status!='ok' OR source IN ('wikimedia','openverse')").fetchall()
            c.execute("DELETE FROM photos WHERE status!='ok' OR source IN ('wikimedia','openverse')")
        for r in rows:
            try:
                (config.PHOTO_DIR / r["file"]).unlink()
            except (FileNotFoundError, TypeError):
                pass
    if rev != "3":
        # La versión anterior marcaba muchos platos como «no encontrados» durante 3 días: se reintentan ya
        with db.tx() as c:
            c.execute("UPDATE photos SET status='pending' WHERE status IN ('missing','error')")
        db.set_setting("photos_rev", "3")


# ---------------------------------------------------------------------------
# Trabajadores en segundo plano
# ---------------------------------------------------------------------------

def _want(key: str, name: str):
    with _cv:
        if key not in _active:
            _wanted[key] = [name, time.time()]
            _cv.notify()
    _ensure_workers()


def _take() -> tuple[str, str]:
    with _cv:
        while True:
            ready = [k for k in _wanted if k not in _active]
            if ready:
                key = max(ready, key=lambda k: _wanted[k][1])
                name = _wanted.pop(key)[0]
                _active.add(key)
                return key, name
            _cv.wait(60)


def _ensure_workers():
    """Arranca los trabajadores (y los vuelve a arrancar si alguno se hubiera parado)."""
    with _cv:
        _threads[:] = [t for t in _threads if t.is_alive()]
        first = not _threads and not getattr(_ensure_workers, "_done", False)
        missing = max(1, config.PHOTO_WORKERS) - len(_threads)
        for i in range(missing):
            t = threading.Thread(target=_worker, daemon=True, name=f"photo-worker-{len(_threads) + 1}")
            _threads.append(t)
            t.start()
        _ensure_workers._done = True
    if first:
        # Recupera las fotos que quedaron pendientes (p. ej. tras reiniciar)
        try:
            with db.tx() as c:
                rows = c.execute("SELECT key, name FROM photos WHERE status='pending'").fetchall()
            with _cv:
                for r in rows:
                    if r["key"] not in _active:
                        _wanted.setdefault(r["key"], [r["name"], 0.0])
                _cv.notify_all()
            if rows:
                db.info(f"Fotos: {len(rows)} pendientes de buscar")
        except Exception as e:
            db.error(f"Fotos: no se pudieron recuperar las pendientes ({e})")


def _worker():
    while True:
        key, name = _take()
        try:
            with db.tx() as c:
                row = c.execute("SELECT status FROM photos WHERE key=?", (key,)).fetchone()
            if row and row["status"] == "pending":
                _worker_once(key, name)
        except Exception as e:  # el trabajador nunca se para
            db.error(f"Foto «{name}»: error inesperado ({type(e).__name__}: {e})")
            try:
                with db.tx() as c:
                    c.execute("UPDATE photos SET status='error', updated=datetime('now','localtime') "
                              "WHERE key=? AND status='pending'", (key,))
            except Exception:
                pass
        finally:
            with _cv:
                _active.discard(key)


def _worker_once(key: str, name: str):
    """Consigue la foto de un plato: internet primero, la IA confirma las dudosas y, si no hay, la crea."""
    started = time.time()
    with db.tx() as c:
        c.execute("INSERT OR IGNORE INTO photos(key, name, file, status) VALUES(?,?,?,'pending')",
                  (key, name, _file_for(key)))
        blocked = {r["url"] for r in c.execute("SELECT url FROM photo_block WHERE key=?", (key,))}
    db.debug(f"Foto «{name}»: empieza la búsqueda (clave «{key}», {len(blocked)} descartadas)")
    status, credit, data, failed = "missing", {}, None, False
    try:
        if config.PHOTOS_WEB:
            found = photo_sources.find_photo(name, blocked)
            if found:
                data, credit = found
        else:
            db.debug(f"Foto «{name}»: búsqueda en internet desactivada (PHOTOS_WEB=false)")
    except Exception as e:
        failed = True
        db.error(f"Foto «{name}»: fallo al buscar en internet ({type(e).__name__}: {e})")
    if not data and not failed:  # si las webs no responden no se gasta IA: se reintenta más tarde
        if ai.photos_available():
            try:
                data = _generate(name)
                credit = {"source": "ia", "credit": "Imagen creada con IA"}
            except Exception as e:
                failed = True
                db.error(f"Foto «{name}»: no se pudo crear con IA ({e})")
        else:
            db.info(f"Foto «{name}»: sin foto adecuada en internet y sin IA para crearla "
                    f"({_why_no_ai()})")
    if data:
        try:
            (config.PHOTO_DIR / _file_for(key)).write_bytes(_shrink(data))
            status = "ok"
        except Exception as e:
            failed, data = True, None
            db.error(f"Foto «{name}»: no se pudo guardar ({e})")
    if status != "ok" and failed:
        status = "error"
    with db.tx() as c:
        c.execute("UPDATE photos SET status=?, source=?, credit=?, credit_url=?, license=?, url=?, "
                  "updated=datetime('now','localtime') WHERE key=?",
                  (status, credit.get("source"), credit.get("credit"), credit.get("credit_url"),
                   credit.get("license"), credit.get("url"), key))
    secs = time.time() - started
    if status == "ok":
        db.info(f"Foto «{name}»: lista ({credit.get('source')}, {secs:.0f} s)")
    elif status == "error":
        db.warn(f"Foto «{name}»: fallo; se reintentará en {RETRY_ERROR // 60} min")
    else:
        db.info(f"Foto «{name}»: sin foto; se reintentará mañana")


def _why_no_ai() -> str:
    if not config.AI_PHOTOS:
        return "AI_PHOTOS=false"
    if not config.OPENAI_API_KEY:
        return "hace falta OPENAI_API_KEY"
    return "límite de gasto del mes alcanzado"


def _generate(name: str) -> bytes:
    """Crea la foto con IA, de una en una. Si OpenAI pide esperar (429), espera y repite una vez."""
    with _gen_lock:
        db.info(f"Foto «{name}»: no hay foto adecuada en internet, se crea con IA")
        try:
            return ai.generate_photo(name)
        except ai.AIError as e:
            if " 429" not in str(e):
                raise
            db.warn(f"Foto «{name}»: OpenAI pide esperar (límite de imágenes por minuto); reintento en 65 s")
            time.sleep(65)
            return ai.generate_photo(name)


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


def enabled() -> bool:
    return config.PHOTOS_WEB or ai.photos_available()


def stats() -> dict:
    with db.tx() as c:
        rows = c.execute("SELECT status, COUNT(*) n FROM photos GROUP BY status").fetchall()
        src = c.execute("SELECT source, COUNT(*) n FROM photos WHERE status='ok' GROUP BY source").fetchall()
    out = {r["status"]: r["n"] for r in rows}
    out["by_source"] = {(r["source"] or "ia"): r["n"] for r in src}
    with _cv:
        out["working"] = len(_active)
        out["queued"] = len(_wanted)
    return out


def credits() -> list[dict]:
    with db.tx() as c:
        rows = c.execute("SELECT name, source, credit, credit_url, license FROM photos "
                         "WHERE status='ok' AND source IS NOT NULL AND source!='ia' ORDER BY name").fetchall()
    return [dict(r) for r in rows]
