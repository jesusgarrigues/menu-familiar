"""Importación del menú mensual y comprobación automática de la web del cole."""
import threading
import time
from datetime import date, timedelta

from . import ai, config, db, pdf_parser, planner, scraper


def import_pdf(pdf_bytes: bytes, title: str = "", source_url: str = "", source_id: str = "") -> dict:
    if pdf_bytes[:5] != b"%PDF-":
        raise ValueError("El archivo no es un PDF")
    text = pdf_parser.pdf_text(pdf_bytes)
    result = None
    if ai.available():
        try:
            result = ai.extract_menu(pdf_bytes, text, title)
            if len([d for d in result["days"].values() if d["dishes"]]) < 3:
                raise ValueError("la IA devolvió muy pocos días")
        except Exception as e:
            db.log("warn", f"Extracción con IA fallida ({e}); uso el lector de PDF")
            result = None
    if result is None:
        result = pdf_parser.parse(pdf_bytes, title)
    year, month = result["year"], result["month"]

    fname = f"menu-{year}-{month:02d}.pdf"
    (config.PDF_DIR / fname).write_bytes(pdf_bytes)

    with db.tx() as c:
        c.execute(
            "INSERT INTO menus(year, month, title, source_url, source_id, pdf_file, parser, raw_text, fetched_at) "
            "VALUES(?,?,?,?,?,?,?,?,datetime('now','localtime')) "
            "ON CONFLICT(year, month) DO UPDATE SET title=excluded.title, source_url=excluded.source_url, "
            "source_id=excluded.source_id, pdf_file=excluded.pdf_file, parser=excluded.parser, "
            "raw_text=excluded.raw_text, fetched_at=excluded.fetched_at",
            (year, month, title, source_url, source_id, fname, result["parser"], text),
        )
        for d, info in result["days"].items():
            if not d.startswith(f"{year}-{month:02d}"):
                continue
            row = c.execute("SELECT edited FROM school_days WHERE date=?", (d,)).fetchone()
            if row and row["edited"]:
                continue  # respeta las correcciones hechas a mano
            c.execute(
                "INSERT INTO school_days(date, dishes, dinner_hint, note, edited) VALUES(?,?,?,?,0) "
                "ON CONFLICT(date) DO UPDATE SET dishes=excluded.dishes, dinner_hint=excluded.dinner_hint, note=excluded.note",
                (d, db.dumps(info["dishes"]), info.get("dinner_hint", ""), info.get("note", "")),
            )
            # Las cenas no editadas se recalcularán con el menú nuevo
            c.execute("DELETE FROM plan WHERE date=? AND edited=0", (d,))
    filled = sum(1 for v in result["days"].values() if v["dishes"])
    db.log("info", f"Menú {month:02d}/{year} importado ({result['parser']}): {filled} días con platos")
    return {"year": year, "month": month, "days": filled, "parser": result["parser"]}


def _months_to_check(today: date) -> list[tuple[int, int]]:
    out = [(today.year, today.month)]
    if today.day >= 25:  # a veces publican el del mes siguiente a final de mes
        nxt = (today.replace(day=1) + timedelta(days=32))
        out.append((nxt.year, nxt.month))
    return out


def check_and_fetch(force: bool = False) -> dict:
    today = date.today()
    page = scraper.fetch_page()
    results = []
    for year, month in _months_to_check(today):
        with db.tx() as c:
            existing = c.execute("SELECT * FROM menus WHERE year=? AND month=?", (year, month)).fetchone()
        if existing and not force and today.day > config.CHECK_UNTIL_DAY and (year, month) == (today.year, today.month):
            results.append(f"{month:02d}/{year}: ya importado")
            continue
        best = scraper.find_best(year, month, page)
        if not best or best.score < 4:  # el nombre del mes no aparece -> aún no publicado
            results.append(f"{month:02d}/{year}: todavía no publicado")
            continue
        if existing and existing["source_id"] == best.ident and not force:
            results.append(f"{month:02d}/{year}: sin cambios")
            continue
        pdf = scraper.download_pdf(best)
        info = import_pdf(pdf, title=scraper.guess_title(best) or f"Menú {scraper.MONTHS[month-1]} {year}",
                          source_url=best.url, source_id=best.ident)
        results.append(f"{info['month']:02d}/{info['year']}: importado ({info['days']} días)")
    db.set_setting("last_check", time.strftime("%Y-%m-%d %H:%M"))
    db.set_setting("last_check_result", "; ".join(results))
    return {"results": results}


def _loop():
    time.sleep(15)
    while True:
        try:
            check_and_fetch()
        except Exception as e:
            db.log("error", f"Comprobación automática fallida: {e}")
            db.set_setting("last_check", time.strftime("%Y-%m-%d %H:%M"))
            db.set_setting("last_check_result", f"error: {e}")
        time.sleep(max(0.25, config.CHECK_EVERY_HOURS) * 3600)


def start_scheduler():
    if config.AUTO_FETCH:
        threading.Thread(target=_loop, daemon=True, name="menu-checker").start()

