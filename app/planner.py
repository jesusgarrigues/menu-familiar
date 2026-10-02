"""Lógica de planificación: cenas recomendadas, menú de fin de semana y lista de la compra."""
import hashlib
import random
import re
from datetime import date, timedelta

from . import ai, db
from .recipes import RECIPES, find
from .scraper import norm

KEYWORDS = {
    "pescado": ["pescado", "merluza", "bacalao", "salmon", "atun", "pescadilla", "gallo", "lenguado", "rape",
                "dorada", "lubina", "sardina", "boqueron", "caballa", "abadejo", "calamar", "sepia", "gamba",
                "langostino", "marisco", "mejillon", "almeja", "palometa", "panga", "bonito", "fletan", "emperador"],
    "carne": ["carne", "pollo", "pavo", "ternera", "cerdo", "lomo", "albondiga", "hamburguesa", "filete",
              "cordero", "conejo", "chorizo", "jamon", "salchicha", "muslo", "pechuga", "cocido", "magro", "longaniza",
              "san jacobo", "escalope", "carrillada", "costilla", "morcilla"],
    "huevo": ["huevo", "tortilla", "revuelto", "quiche", "frittata"],
    "legumbre": ["lenteja", "garbanzo", "alubia", "judion", "frijol", "habas", "hummus", "legumbre", "fabada", "potaje"],
    "pasta": ["pasta", "macarron", "espagueti", "fideo", "tallarin", "lasana", "canelon", "tortellini", "ravioli",
              "fideua", "estrellitas", "plumas", "tiburones", "hélices", "helices", "lazos"],
    "arroz": ["arroz", "paella", "risotto"],
    "patata": ["patata", "pure de patata", "ensaladilla"],
    "verdura": ["verdura", "ensalada", "crema", "pure", "menestra", "judias verdes", "brocoli", "coliflor",
                "calabacin", "calabaza", "zanahoria", "espinaca", "acelga", "pisto", "tomate", "lechuga",
                "pimiento", "berenjena", "puerro", "champinon", "guisante", "alcachofa", "vegetal", "hortaliza",
                "sopa", "gazpacho", "salmorejo", "repollo", "col", "boniato"],
    "lacteo": ["yogur", "queso", "leche", "natillas", "flan", "cuajada", "lacteo", "kefir", "bechamel"],
    "fruta": ["fruta", "manzana", "pera", "platano", "naranja", "mandarina", "melon", "sandia", "kiwi", "uva", "piña"],
}

# Raciones orientativas por semana (comidas + cenas) para niños en edad escolar
WEEK_TARGETS = {"pescado": 4, "legumbre": 3, "huevo": 3, "carne": 3, "verdura": 12, "arroz": 1, "pasta": 1}

GENERIC = {"pescado", "pescado blanco", "pescado azul", "carne", "carne blanca", "carne roja", "huevo", "huevos",
           "verdura", "verduras", "hortalizas", "legumbre", "legumbres", "fruta", "lacteo", "lacteos", "ensalada",
           "cereales", "proteina", "pasta", "arroz", "patata", "verdura cocida", "verdura cruda"}

DISH_HINT_WORDS = re.compile(r"\b(con|al|a la|de|en|rellen[oa]s?|gratinad[oa]|plancha|horno|guisad[oa]|asad[oa]|frit[oa]|salsa)\b")


def classify(text: str) -> set[str]:
    t = norm(text)
    found = set()
    for group, words in KEYWORDS.items():
        if any(re.search(rf"\b{re.escape(w)}", t) for w in words):
            found.add(group)
    return found


def hint_is_dish(hint: str) -> bool:
    """¿La recomendación de cena del cole es un plato concreto o solo ingredientes?"""
    h = norm(hint).strip()
    if not h:
        return False
    if find(hint):
        return True
    first = re.split(r",|\by\b|\be\b|\+|/|\bcon\b", h)[0].strip()
    if first in GENERIC:
        return False  # "Pescado y puré de verduras", "Carne blanca con ensalada"
    # "Verdura y pescado", "Ensalada, huevo y fruta" -> ingredientes
    parts = [p.strip() for p in re.split(r",|\by\b|\be\b|\+|/", h) if p.strip()]
    if len(parts) >= 2 and all(len(p.split()) <= 2 for p in parts):
        return False
    return bool(DISH_HINT_WORDS.search(h))


def _rng(*keys) -> random.Random:
    seed = int(hashlib.md5("|".join(map(str, keys)).encode()).hexdigest()[:8], 16)
    return random.Random(seed)


def _dish(recipe: dict, source="recetario") -> dict:
    return {"name": recipe["name"], "groups": recipe["groups"], "ingredients": recipe["ingredients"], "source": source}


def make_dish(name: str, ingredients=None, source="manual") -> dict:
    r = find(name)
    if r and ingredients is None:
        return _dish(r, source)
    return {"name": name.strip(), "groups": sorted(classify(name)), "ingredients": ingredients or [], "source": source}


def _recent_names(day: date, days_back=7) -> set[str]:
    start = (day - timedelta(days=days_back)).isoformat()
    with db.tx() as c:
        rows = c.execute("SELECT choice FROM plan WHERE date>=? AND date<?", (start, day.isoformat())).fetchall()
    return {(db.loads(r["choice"], None) or {}).get("name", "").lower() for r in rows}


def rule_dinners(lunch: list[str], hint: str, day: date, n=4, avoid=None, salt="") -> list[dict]:
    lunch_groups = classify(" ".join(lunch))
    hint_groups = classify(hint) - {"fruta"}
    recent = _recent_names(day) | {a.lower() for a in (avoid or [])}
    rng = _rng(day.isoformat(), salt)
    scored = []
    for r in RECIPES:
        if r["when"] not in ("cena", "ambas"):
            continue
        g = set(r["groups"])
        s = rng.random()
        if hint_groups:
            s += 3 * len(g & hint_groups) - 1.5 * len(g - hint_groups - {"verdura", "lacteo"})
        else:
            # Sin recomendación: complementar la comida (regla AESAN)
            if "verdura" in g:
                s += 2
            for prot in ("pescado", "carne", "huevo"):
                if prot in g and prot in lunch_groups:
                    s -= 3
            if {"legumbre", "pasta", "arroz"} & lunch_groups and {"pasta", "arroz", "legumbre"} & g:
                s -= 2
            if "carne" in lunch_groups and g & {"pescado", "huevo"}:
                s += 1.5
            if "pescado" in lunch_groups and g & {"huevo", "carne"}:
                s += 1.5
        if r["name"].lower() in recent:
            s -= 4
        scored.append((s, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [_dish(r) for _, r in scored[:n]]


def recommend_dinners(day: date, lunch: list[str], hint: str, avoid=None, salt="") -> list[dict]:
    options: list[dict] = []
    if hint and hint_is_dish(hint):
        options.append(make_dish(hint, source="cole"))
    n = 4 - len(options)
    if ai.available():
        try:
            options += [dict(d, source="ia") for d in ai.suggest_dinners(lunch, hint, n=n, avoid=avoid)]
            return options
        except Exception as e:  # sin conexión, cuota agotada...
            db.log("warn", f"IA no disponible para cenas ({e}); uso el recetario")
    return options + rule_dinners(lunch, hint, day, n=n, avoid=avoid, salt=salt)


# ---------------------------------------------------------------------------
# Semana
# ---------------------------------------------------------------------------

def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_dates(monday: date) -> list[date]:
    return [monday + timedelta(days=i) for i in range(7)]


def school_day(c, d: date):
    row = c.execute("SELECT * FROM school_days WHERE date=?", (d.isoformat(),)).fetchone()
    if not row:
        return None
    return {"date": row["date"], "dishes": db.loads(row["dishes"], []), "dinner_hint": row["dinner_hint"] or "",
            "note": row["note"] or "", "edited": bool(row["edited"])}


def get_plan(c, d: date, meal: str):
    row = c.execute("SELECT * FROM plan WHERE date=? AND meal=?", (d.isoformat(), meal)).fetchone()
    if not row:
        return None
    return {"options": db.loads(row["options"], []), "choice": db.loads(row["choice"], None), "edited": bool(row["edited"])}


def save_plan(d: date, meal: str, options=None, choice=None, edited=None):
    with db.tx() as c:
        cur = get_plan(c, d, meal) or {"options": [], "choice": None, "edited": False}
        options = cur["options"] if options is None else options
        choice = cur["choice"] if choice is None else choice
        edited = cur["edited"] if edited is None else edited
        c.execute(
            "INSERT INTO plan(date, meal, options, choice, edited) VALUES(?,?,?,?,?) "
            "ON CONFLICT(date, meal) DO UPDATE SET options=excluded.options, choice=excluded.choice, edited=excluded.edited",
            (d.isoformat(), meal, db.dumps(options), db.dumps(choice), int(bool(edited))),
        )


def _home_lunch(sd) -> bool:
    """Entre semana se come en casa si no hay cole ese día (festivo o sin menú)."""
    if sd is None:
        return False  # sin datos de ese mes: no sabemos si hay cole
    return not sd["dishes"] or bool(re.search(r"festivo|no lectivo|vacaciones", norm(sd["note"])))


def ensure_week(monday: date, force=False):
    """Genera las propuestas que falten para la semana (no pisa lo que el usuario ha editado)."""
    with db.tx() as c:
        school = {d: school_day(c, d) for d in week_dates(monday)}
        has_menu = any(sd and sd["dishes"] for sd in school.values())
    for d in week_dates(monday)[:5]:
        sd = school[d]
        if not has_menu and sd is None:
            continue
        with db.tx() as c:
            cur = get_plan(c, d, "cena")
        if force or not cur or (not cur["edited"] and not cur["options"]):
            lunch = sd["dishes"] if sd else []
            opts = recommend_dinners(d, lunch, sd["dinner_hint"] if sd else "")
            save_plan(d, "cena", options=opts, choice=opts[0] if opts else None, edited=False)
        if _home_lunch(sd):
            with db.tx() as c:
                cur = get_plan(c, d, "comida")
            if force or not cur or (not cur["edited"] and not cur["options"]):
                opts = [_dish(r) for r in _pick_weekend(monday, ["comida"] * 3, salt=d.isoformat())]
                save_plan(d, "comida", options=opts, choice=opts[0] if opts else None, edited=False)
    ensure_weekend(monday, force=force)


def week_counts(monday: date, include_weekend=False) -> dict[str, int]:
    counts = {g: 0 for g in WEEK_TARGETS}
    days = week_dates(monday)[: 7 if include_weekend else 5]
    with db.tx() as c:
        for d in days:
            sd = school_day(c, d)
            if sd and sd["dishes"] and not _home_lunch(sd):
                for g in classify(" ".join(sd["dishes"])):
                    counts[g] = counts.get(g, 0) + 1
            for meal in ("comida", "cena"):
                p = get_plan(c, d, meal)
                if p and p["choice"]:
                    for g in p["choice"].get("groups") or classify(p["choice"].get("name", "")):
                        counts[g] = counts.get(g, 0) + 1
    return counts


def _pick_weekend(monday: date, slots: list[str], salt="") -> list[dict]:
    counts = week_counts(monday)
    deficit = {g: WEEK_TARGETS[g] - counts.get(g, 0) for g in WEEK_TARGETS}
    rng = _rng(monday.isoformat(), "finde", salt)
    used = _recent_names(monday + timedelta(days=5), days_back=12)
    chosen = []
    for slot in slots:
        best, best_s = None, -1e9
        for r in RECIPES:
            if r["when"] not in (slot, "ambas") or r["name"].lower() in used:
                continue
            s = sum(max(deficit.get(g, 0), -1) for g in r["groups"]) + rng.random() * 1.5
            if slot == "cena" and "verdura" in r["groups"]:
                s += 1
            if s > best_s:
                best, best_s = r, s
        if best:
            chosen.append(best)
            used.add(best["name"].lower())
            for g in best["groups"]:
                if g in deficit:
                    deficit[g] -= 1
    return chosen


def weekend_deficits(monday: date) -> list[str]:
    counts = week_counts(monday)
    return [g for g, t in WEEK_TARGETS.items() if counts.get(g, 0) < t]


def week_summary(monday: date) -> str:
    lines = []
    with db.tx() as c:
        for d in week_dates(monday)[:5]:
            sd = school_day(c, d)
            cena = get_plan(c, d, "cena")
            cena_name = cena["choice"]["name"] if cena and cena["choice"] else "—"
            lunch = ", ".join(sd["dishes"]) if sd and sd["dishes"] else "en casa / sin datos"
            lines.append(f"{d.isoformat()}: comida cole: {lunch}; cena: {cena_name}")
    return "\n".join(lines)


def ensure_weekend(monday: date, force=False):
    sat, sun = monday + timedelta(days=5), monday + timedelta(days=6)
    slots = [(sat, "comida"), (sat, "cena"), (sun, "comida"), (sun, "cena")]
    with db.tx() as c:
        current = {s: get_plan(c, *s) for s in slots}
    todo = [s for s in slots if force or not current[s] or (not current[s]["edited"] and not current[s]["choice"])]
    if not todo:
        return
    proposal: dict = {}
    if ai.available():
        try:
            data = ai.weekend_menu(week_summary(monday), weekend_deficits(monday), avoid=[])
            proposal = {(sat, "comida"): data["sabado"]["comida"], (sat, "cena"): data["sabado"]["cena"],
                        (sun, "comida"): data["domingo"]["comida"], (sun, "cena"): data["domingo"]["cena"]}
            proposal = {k: dict(v, source="ia") for k, v in proposal.items()}
        except Exception as e:
            db.log("warn", f"IA no disponible para el fin de semana ({e}); uso el recetario")
            proposal = {}
    if not proposal:
        picks = _pick_weekend(monday, [m for _, m in slots], salt="v2" if force else "")
        proposal = {s: _dish(r) for s, r in zip(slots, picks)}
    for s in todo:
        if s in proposal:
            alt = [_dish(r) for r in _pick_weekend(monday, [s[1]] * 3, salt=s[0].isoformat() + s[1])]
            opts = [proposal[s]] + [a for a in alt if a["name"] != proposal[s]["name"]][:2]
            save_plan(s[0], s[1], options=opts, choice=proposal[s], edited=False)


# ---------------------------------------------------------------------------
# Lista de la compra
# ---------------------------------------------------------------------------

SECTION_ORDER = ["Frutería", "Carnicería", "Pescadería", "Huevos y lácteos", "Panadería", "Despensa", "Congelados", "Otros"]


def shopping_list(monday: date) -> dict:
    items: dict[str, dict] = {}
    with db.tx() as c:
        for d in week_dates(monday):
            for meal in ("comida", "cena"):
                p = get_plan(c, d, meal)
                if not p or not p["choice"]:
                    continue
                dish = p["choice"]
                for ing in dish.get("ingredients") or []:
                    name = (ing.get("name") or "").strip()
                    if not name:
                        continue
                    key = name.lower()
                    it = items.setdefault(key, {"name": name, "qty": [], "section": ing.get("section") or "Otros",
                                                "for": [], "manual": False})
                    if ing.get("qty"):
                        it["qty"].append(ing["qty"])
                    it["for"].append(dish["name"])
        state = {r["name"].lower(): dict(r) for r in
                 c.execute("SELECT * FROM shopping WHERE week=?", (monday.isoformat(),)).fetchall()}
    out = []
    for key, it in items.items():
        st = state.pop(key, None)
        if st and st["hidden"]:
            continue
        out.append({"name": it["name"], "qty": sum_qty(it["qty"]), "section": it["section"],
                    "for": sorted(set(it["for"])), "checked": bool(st and st["checked"]), "manual": False})
    for st in state.values():
        if st["manual"] and not st["hidden"]:
            out.append({"name": st["name"], "qty": st["qty"] or "", "section": st["section"] or "Otros",
                        "for": [], "checked": bool(st["checked"]), "manual": True})
    out.sort(key=lambda x: (SECTION_ORDER.index(x["section"]) if x["section"] in SECTION_ORDER else 99, x["name"].lower()))
    return {"week": monday.isoformat(), "items": out}


UNIT_ALIASES = {"g": "g", "gr": "g", "kg": "kg", "ml": "ml", "l": "l", "litro": "l", "litros": "l"}


def sum_qty(qtys: list[str]) -> str:
    """Suma cantidades compatibles: ["2", "1", "500 g", "1 kg"] -> "3 + 1,5 kg"."""
    totals: dict[str, float] = {}
    order: list[str] = []
    rest: list[str] = []
    for q in qtys:
        m = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?|\d+/\d+)\s*([a-záéíóúñ ]*)\s*", q.lower())
        if not m:
            rest.append(q)
            continue
        num = m.group(1)
        val = (int(num.split("/")[0]) / int(num.split("/")[1])) if "/" in num else float(num.replace(",", "."))
        unit = m.group(2).strip()
        unit = UNIT_ALIASES.get(unit, unit)
        w = unit.split(" ")
        if unit not in ("g", "kg", "ml", "l") and w[0].endswith("s") and len(w[0]) > 3:
            w[0] = w[0][:-1]  # latas -> lata
            unit = " ".join(w)
        if unit == "kg":
            unit, val = "g", val * 1000
        if unit == "l":
            unit, val = "ml", val * 1000
        if unit not in totals:
            order.append(unit)
            totals[unit] = 0
        totals[unit] += val
    parts = []
    for u in order:
        v = totals[u]
        if u == "g" and v >= 1000:
            u, v = "kg", v / 1000
        if u == "ml" and v >= 1000:
            u, v = "l", v / 1000
        txt = (f"{v:.2f}".rstrip("0").rstrip(".")).replace(".", ",")
        if u and u not in ("g", "kg", "ml", "l") and v > 1:
            u = " ".join([u.split(" ")[0] + "s"] + u.split(" ")[1:])
        parts.append(f"{txt} {u}".strip())
    return " + ".join(parts + sorted(set(rest)))


def shopping_set(monday: date, name: str, **fields):
    with db.tx() as c:
        row = c.execute("SELECT id FROM shopping WHERE week=? AND lower(name)=lower(?)", (monday.isoformat(), name)).fetchone()
        if not row:
            c.execute("INSERT INTO shopping(week, name) VALUES(?,?)", (monday.isoformat(), name))
        sets = ", ".join(f"{k}=?" for k in fields)
        if sets:
            c.execute(f"UPDATE shopping SET {sets} WHERE week=? AND lower(name)=lower(?)",
                      (*fields.values(), monday.isoformat(), name))
