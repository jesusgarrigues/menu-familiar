"""API web (Flask) y servidor de la interfaz."""
import base64
import calendar
import functools
import json
import os
import secrets
from datetime import date, timedelta
from pathlib import Path

from flask import Flask, abort, jsonify, redirect, request, send_file, send_from_directory, session

from . import ai, config, db, photos, planner, service
from .text import ALLERGENS, clean_title

STATIC = os.path.join(os.path.dirname(__file__), "static")
app = Flask(__name__, static_folder=STATIC, static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024

db.init()
photos.migrate()


def _secret_key() -> bytes:
    path = config.DATA_DIR / "secret.key"
    try:
        return path.read_bytes()
    except FileNotFoundError:
        key = secrets.token_bytes(32)
        path.write_bytes(key)
        return key


app.secret_key = _secret_key()
app.config.update(
    PERMANENT_SESSION_LIFETIME=timedelta(days=365),
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_HTTPONLY=True,
)

# Rutas que no necesitan contraseña (el navegador las pide sin sesión al instalar la app)
PUBLIC = ("/healthz", "/login", "/manifest.webmanifest", "/sw.js", "/static/icons/", "/static/login.css",
          "/apple-touch-icon", "/favicon")


@app.before_request
def auth():
    if not config.APP_PASSWORD or request.path.startswith(PUBLIC):
        return None
    if session.get("ok") == _pw_tag():
        return None
    a = request.authorization  # compatibilidad con acceso por usuario/contraseña básico
    if a and secrets.compare_digest(a.password or "", config.APP_PASSWORD):
        return None
    if request.path.startswith("/api/"):
        return jsonify({"error": "Inicia sesión"}), 401
    return redirect("/login")


def _pw_tag() -> str:
    import hashlib
    return hashlib.sha256(config.APP_PASSWORD.encode()).hexdigest()[:16]


LOGIN_HTML = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Menú familiar</title><link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="{apple_icon}">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="theme-color" content="#FFFFFF">
<style>
:root{color-scheme:light dark}body{margin:0;min-height:100vh;display:grid;place-items:center;font:16px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#fff;color:#000}
@media (prefers-color-scheme:dark){body{background:#0B0B0B;color:#fff}input{background:#1C1C1C!important;color:#fff}}
form{width:min(360px,calc(100vw - 32px));text-align:center}img{width:84px;height:84px;border-radius:20px}
h1{font-size:1.7rem;margin:14px 0 4px;letter-spacing:-.02em}p{color:#6B6B6B;margin:0 0 22px}
input{width:100%;box-sizing:border-box;border:0;background:#F3F3F3;border-radius:12px;padding:14px;font:inherit;margin-bottom:12px}
button{width:100%;border:0;border-radius:999px;background:#06C167;color:#fff;font:700 1rem inherit;padding:14px;cursor:pointer}
.e{color:#E8590C;font-weight:700;margin:-8px 0 12px}
</style></head><body><form method="post"><img src="/static/icons/icon-192.png" alt="">
<h1>Menú familiar</h1><p>Introduce la contraseña de la familia</p>{error}
<input type="password" name="password" placeholder="Contraseña" autocomplete="current-password" autofocus required>
<button>Entrar</button></form></body></html>"""


@app.route("/login", methods=["GET", "POST"])
def login():
    if not config.APP_PASSWORD:
        return redirect("/")
    error = ""
    if request.method == "POST":
        if secrets.compare_digest(request.form.get("password", ""), config.APP_PASSWORD):
            session.permanent = True
            session["ok"] = _pw_tag()
            return redirect("/")
        error = '<p class="e">Contraseña incorrecta</p>'
    return LOGIN_HTML.replace("{error}", error).replace("{apple_icon}", _data_uri("apple-touch-icon.png"))


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.get("/manifest.webmanifest")
def manifest():
    # Los iconos van incrustados: así se ven aunque un proxy (p. ej. Cloudflare Access) bloquee su descarga
    data = json.loads((Path(STATIC) / "manifest.webmanifest").read_text(encoding="utf-8"))
    for icon in data.get("icons", []):
        if icon["src"].endswith(".png"):
            icon["src"] = _data_uri(icon["src"].rsplit("/", 1)[-1])
    r = app.response_class(json.dumps(data, ensure_ascii=False), mimetype="application/manifest+json")
    r.headers["Cache-Control"] = "no-cache"
    return r


@functools.lru_cache(maxsize=8)
def _data_uri(filename: str) -> str:
    raw = (Path(STATIC) / "icons" / filename).read_bytes()
    return "data:image/png;base64," + base64.b64encode(raw).decode()


@app.get("/apple-touch-icon.png")
@app.get("/apple-touch-icon-precomposed.png")
@app.get("/apple-touch-icon-180x180.png")
def apple_icon():
    return send_from_directory(Path(STATIC) / "icons", "apple-touch-icon.png", mimetype="image/png", max_age=86400)


@app.get("/favicon.ico")
def favicon():
    return send_from_directory(Path(STATIC) / "icons", "favicon-32.png", mimetype="image/png", max_age=86400)


@app.get("/sw.js")
def service_worker():
    r = send_from_directory(STATIC, "sw.js", mimetype="application/javascript")
    r.headers["Cache-Control"] = "no-cache"
    r.headers["Service-Worker-Allowed"] = "/"
    return r


def parse_day(s: str | None) -> date:
    try:
        return date.fromisoformat(s) if s else date.today()
    except ValueError:
        abort(400, "Fecha no válida")


def err(msg, code=400):
    return jsonify({"error": msg}), code


@app.get("/")
def index():
    # El icono del iPhone va incrustado en la página: iOS lo guarda al «Añadir a pantalla de inicio»
    # aunque Cloudflare Access u otro proxy bloquee la descarga del archivo del icono.
    html = (Path(STATIC) / "index.html").read_text(encoding="utf-8")
    html = html.replace('href="/static/icons/apple-touch-icon.png"', f'href="{_data_uri("apple-touch-icon.png")}"')
    r = app.response_class(html, mimetype="text/html")
    r.headers["Cache-Control"] = "no-cache"
    return r


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/status")
def status():
    with db.tx() as c:
        menus = [dict(r) for r in c.execute(
            "SELECT year, month, title, source_url, parser, fetched_at FROM menus ORDER BY year DESC, month DESC").fetchall()]
        logs = [dict(r) for r in c.execute("SELECT at, level, message FROM log ORDER BY id DESC LIMIT 15").fetchall()]
    for m in menus:
        m["title"] = clean_title(m["title"])
    return {
        "menus": menus,
        "ai": config.ai_provider() or None,
        "source": config.SCHOOL_MENU_URL,
        "auto_fetch": config.AUTO_FETCH,
        "last_check": db.get_setting("last_check"),
        "last_check_result": db.get_setting("last_check_result"),
        "logs": logs,
        "servings": config.SERVINGS,
        "auth": bool(config.APP_PASSWORD),
        "usage": ai.usage(),
        "photos": {"enabled": photos.enabled(), "web": config.PHOTOS_WEB, "pexels": bool(config.PEXELS_API_KEY),
                   "ai": ai.photos_available(), **photos.stats()},
    }


@app.get("/api/photo")
def photo():
    name = request.args.get("name", "")
    path, status = photos.lookup(name)
    if path:
        r = send_file(path, mimetype="image/webp", max_age=30 * 24 * 3600)
        return r
    if status == "pending":
        return jsonify({"status": "pending"}), 202
    return jsonify({"status": "none"}), 404


@app.post("/api/photo/reject")
def photo_reject():
    name = (request.get_json(force=True) or {}).get("name", "")
    if not name:
        return err("Falta el plato")
    return {"status": photos.reject(name)}


@app.get("/api/photo-credits")
def photo_credits():
    return {"credits": photos.credits()}


@app.get("/api/allergens")
def allergens():
    return {"allergens": ALLERGENS}


@app.post("/api/fetch")
def fetch_now():
    try:
        return service.check_and_fetch(force=bool(request.args.get("force")))
    except Exception as e:
        db.log("error", f"Descarga manual fallida: {e}")
        return err(f"No se pudo descargar el menú: {e}", 502)


@app.post("/api/upload")
def upload():
    f = request.files.get("pdf")
    if not f:
        return err("Falta el archivo PDF")
    try:
        return service.import_pdf(f.read(), title=f.filename or "")
    except Exception as e:
        return err(str(e))


@app.get("/api/menus/<int:year>/<int:month>/pdf")
def menu_pdf(year, month):
    return send_from_directory(config.PDF_DIR, f"menu-{year}-{month:02d}.pdf", mimetype="application/pdf")


@app.get("/api/month")
def month_view():
    today = date.today()
    year = int(request.args.get("year", today.year))
    month = int(request.args.get("month", today.month))
    _, last = calendar.monthrange(year, month)
    first = date(year, month, 1)
    # Prepara las propuestas de todas las semanas del mes (recetario primero: casi siempre gratis)
    monday = planner.monday_of(first)
    while monday <= date(year, month, last):
        planner.ensure_week(monday)
        monday += timedelta(days=7)
    days = []
    with db.tx() as c:
        menu = c.execute("SELECT title, parser FROM menus WHERE year=? AND month=?", (year, month)).fetchone()
        for d in range(1, last + 1):
            day = date(year, month, d)
            sd = planner.school_day(c, day)
            plan = {}
            for meal in ("comida", "cena"):
                p = planner.get_plan(c, day, meal)
                if p is not None:
                    plan[meal] = p["choice"]["name"] if p["choice"] else None
            days.append({
                "date": day.isoformat(),
                "dishes": sd["dishes"] if sd else [],
                "dinner_hint": sd["dinner_hint"] if sd else "",
                "note": sd["note"] if sd else "",
                "plan": plan,
            })
    menu = dict(menu) if menu else None
    if menu:
        menu["title"] = clean_title(menu["title"])
    return {"year": year, "month": month, "menu": menu, "days": days}


def week_payload(monday: date):
    planner.ensure_week(monday)
    out = []
    with db.tx() as c:
        for d in planner.week_dates(monday):
            out.append({
                "date": d.isoformat(),
                "weekday": d.weekday(),
                "school": planner.school_day(c, d),
                "comida": planner.get_plan(c, d, "comida"),
                "cena": planner.get_plan(c, d, "cena"),
            })
    counts = planner.week_counts(monday, include_weekend=True)
    return {
        "monday": monday.isoformat(),
        "days": out,
        "counts": counts,
        "counts_weekdays": planner.week_counts(monday),
        "targets": planner.WEEK_TARGETS,
        "deficits": planner.weekend_deficits(monday),
    }


@app.get("/api/week")
def week():
    return week_payload(planner.monday_of(parse_day(request.args.get("date"))))


@app.put("/api/school/<day>")
def edit_school(day):
    d = parse_day(day)
    body = request.get_json(force=True)
    dishes = [s.strip() for s in body.get("dishes", []) if s and s.strip()]
    with db.tx() as c:
        c.execute(
            "INSERT INTO school_days(date, dishes, dinner_hint, note, edited) VALUES(?,?,?,?,1) "
            "ON CONFLICT(date) DO UPDATE SET dishes=excluded.dishes, dinner_hint=excluded.dinner_hint, "
            "note=excluded.note, edited=1",
            (d.isoformat(), db.dumps(dishes), body.get("dinner_hint", ""), body.get("note", "")),
        )
        c.execute("DELETE FROM plan WHERE date=? AND edited=0", (d.isoformat(),))
    return week_payload(planner.monday_of(d))


def check_meal(meal):
    if meal not in ("comida", "cena"):
        abort(400, "Comida no válida")


@app.post("/api/plan/<day>/<meal>/choose")
def choose(day, meal):
    check_meal(meal)
    d = parse_day(day)
    body = request.get_json(force=True)
    planner.ensure_week(planner.monday_of(d))
    with db.tx() as c:
        cur = planner.get_plan(c, d, meal) or {"options": [], "choice": None}
    if "index" in body:
        try:
            dish = cur["options"][int(body["index"])]
        except (IndexError, ValueError):
            return err("Opción no válida")
    else:
        name = (body.get("name") or "").strip()
        if not name:
            return err("Escribe el nombre del plato")
        ings = body.get("ingredients")
        if ings is not None:
            ings = [{"name": i.get("name", "").strip(), "qty": i.get("qty", "").strip(),
                     "section": i.get("section") or "Otros"} for i in ings if i.get("name", "").strip()]
        dish = planner.make_dish(name, ingredients=ings)
        if not any(o["name"].lower() == dish["name"].lower() for o in cur["options"]):
            cur["options"] = cur["options"] + [dish]
        else:
            cur["options"] = [dish if o["name"].lower() == dish["name"].lower() else o for o in cur["options"]]
    planner.save_plan(d, meal, options=cur["options"], choice=dish, edited=True)
    return week_payload(planner.monday_of(d))


@app.post("/api/plan/<day>/<meal>/ingredients")
def fill_ingredients(day, meal):
    check_meal(meal)
    d = parse_day(day)
    planner.ensure_ingredients(planner.monday_of(d), only=(d, meal))
    return week_payload(planner.monday_of(d))


@app.delete("/api/plan/<day>/<meal>")
def clear_meal(day, meal):
    """Marca que esa comida no se hace en casa (se come fuera)."""
    check_meal(meal)
    d = parse_day(day)
    planner.ensure_week(planner.monday_of(d))
    with db.tx() as c:
        cur = planner.get_plan(c, d, meal) or {"options": []}
        c.execute(
            "INSERT INTO plan(date, meal, options, choice, edited) VALUES(?,?,?,?,1) "
            "ON CONFLICT(date, meal) DO UPDATE SET choice=excluded.choice, edited=1",
            (d.isoformat(), meal, db.dumps(cur["options"]), "null"),
        )
    return week_payload(planner.monday_of(d))


@app.post("/api/plan/<day>/<meal>/regenerate")
def regenerate(day, meal):
    check_meal(meal)
    d = parse_day(day)
    with db.tx() as c:
        sd = planner.school_day(c, d)
        cur = planner.get_plan(c, d, meal) or {"options": []}
    avoid = [o["name"] for o in cur["options"]]
    salt = secrets.token_hex(4)
    if meal == "cena" and d.weekday() < 5:
        opts = planner.recommend_dinners(d, sd["dishes"] if sd else [], sd["dinner_hint"] if sd else "",
                                         avoid=avoid, salt=salt)
    else:
        picks = planner._pick_weekend(planner.monday_of(d), [meal] * 4, salt=salt)
        opts = [planner._dish(r) for r in picks if r["name"] not in avoid][:4] or [planner._dish(r) for r in picks]
    planner.save_plan(d, meal, options=opts, choice=opts[0] if opts else None, edited=False)
    return week_payload(planner.monday_of(d))


@app.post("/api/week/<day>/weekend")
def regenerate_weekend(day):
    monday = planner.monday_of(parse_day(day))
    sat, sun = monday + timedelta(days=5), monday + timedelta(days=6)
    with db.tx() as c:
        c.execute("DELETE FROM plan WHERE date IN (?,?)", (sat.isoformat(), sun.isoformat()))
    planner.ensure_weekend(monday, force=True)
    return week_payload(monday)


@app.get("/api/shopping")
def shopping():
    monday = planner.monday_of(parse_day(request.args.get("date")))
    planner.ensure_week(monday)
    return planner.shopping_list(monday)


@app.post("/api/shopping")
def shopping_add():
    b = request.get_json(force=True)
    monday = planner.monday_of(parse_day(b.get("date")))
    name = (b.get("name") or "").strip()
    if not name:
        return err("Escribe qué hay que comprar")
    planner.shopping_set(monday, name, qty=b.get("qty", ""), section=b.get("section") or "Otros",
                         manual=1, hidden=0, checked=0)
    return planner.shopping_list(monday)


@app.patch("/api/shopping")
def shopping_update():
    b = request.get_json(force=True)
    monday = planner.monday_of(parse_day(b.get("date")))
    fields = {k: int(bool(b[k])) for k in ("checked", "hidden") if k in b}
    planner.shopping_set(monday, b.get("name", ""), **fields)
    return planner.shopping_list(monday)


@app.post("/api/shopping/clear-checked")
def shopping_clear():
    b = request.get_json(force=True)
    monday = planner.monday_of(parse_day(b.get("date")))
    with db.tx() as c:
        c.execute("UPDATE shopping SET hidden=1 WHERE week=? AND checked=1", (monday.isoformat(),))
    return planner.shopping_list(monday)


@app.get("/api/recipes")
def recipes():
    return {"recipes": [{"name": r["name"], "groups": r["groups"], "when": r.get("when", "cena")}
                        for r in planner.all_recipes()]}


@app.get("/api/recipe")
def recipe():
    return planner.find_any(request.args.get("name", "")) or {}


service.start_scheduler() if os.getenv("DISABLE_SCHEDULER") != "1" else None
