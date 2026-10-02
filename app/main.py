"""API web (Flask) y servidor de la interfaz."""
import calendar
import os
import secrets
from datetime import date, timedelta
from functools import wraps

from flask import Flask, Response, abort, jsonify, request, send_from_directory

from . import ai, config, db, planner, service
from .recipes import RECIPES

STATIC = os.path.join(os.path.dirname(__file__), "static")
app = Flask(__name__, static_folder=STATIC, static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024

db.init()


@app.before_request
def auth():
    if not config.APP_PASSWORD or request.path == "/healthz":
        return None
    a = request.authorization
    if a and secrets.compare_digest(a.password or "", config.APP_PASSWORD):
        return None
    return Response("Acceso restringido", 401, {"WWW-Authenticate": 'Basic realm="Menu familiar"'})


def parse_day(s: str | None) -> date:
    try:
        return date.fromisoformat(s) if s else date.today()
    except ValueError:
        abort(400, "Fecha no válida")


def err(msg, code=400):
    return jsonify({"error": msg}), code


@app.get("/")
def index():
    return send_from_directory(STATIC, "index.html")


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/status")
def status():
    with db.tx() as c:
        menus = [dict(r) for r in c.execute(
            "SELECT year, month, title, source_url, parser, fetched_at FROM menus ORDER BY year DESC, month DESC").fetchall()]
        logs = [dict(r) for r in c.execute("SELECT at, level, message FROM log ORDER BY id DESC LIMIT 15").fetchall()]
    return {
        "menus": menus,
        "ai": config.ai_provider() or None,
        "source": config.SCHOOL_MENU_URL,
        "auto_fetch": config.AUTO_FETCH,
        "last_check": db.get_setting("last_check"),
        "last_check_result": db.get_setting("last_check_result"),
        "logs": logs,
        "servings": config.SERVINGS,
    }


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
    prefix = f"{year}-{month:02d}-"
    with db.tx() as c:
        rows = {r["date"]: r for r in c.execute("SELECT * FROM school_days WHERE date LIKE ?", (prefix + "%",))}
        plans = {}
        for r in c.execute("SELECT date, meal, choice FROM plan WHERE date LIKE ?", (prefix + "%",)):
            ch = db.loads(r["choice"], None)
            plans.setdefault(r["date"], {})[r["meal"]] = ch["name"] if ch else None
        menu = c.execute("SELECT title, parser FROM menus WHERE year=? AND month=?", (year, month)).fetchone()
    days = []
    for d in range(1, last + 1):
        key = f"{prefix}{d:02d}"
        r = rows.get(key)
        days.append({
            "date": key,
            "dishes": db.loads(r["dishes"], []) if r else [],
            "dinner_hint": r["dinner_hint"] if r else "",
            "note": r["note"] if r else "",
            "plan": plans.get(key, {}),
        })
    return {"year": year, "month": month, "menu": dict(menu) if menu else None, "days": days}


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
    return {"recipes": [{"name": r["name"], "groups": r["groups"], "when": r["when"]} for r in RECIPES]}


@app.get("/api/recipe")
def recipe():
    from .recipes import find
    r = find(request.args.get("name", ""))
    return r or {}


service.start_scheduler() if os.getenv("DISABLE_SCHEDULER") != "1" else None
