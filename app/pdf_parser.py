"""Extracción del menú del PDF sin IA (pdfplumber).

Funciona bien con los menús típicos en forma de calendario (tabla con un
día por celda) o en forma de lista ("LUNES 6 ..."). Si el formato es raro, la
extracción con IA (ai.py) es más fiable; y en cualquier caso cada día se puede
corregir a mano desde la app.
"""
import calendar
import io
import re
from datetime import date

import pdfplumber

from .scraper import MONTHS, norm

WEEKDAYS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
DINNER_MARKERS = re.compile(r"^\s*(sugerencias?\s+(de\s+)?cena|cena\s*(sugerida|recomendada)?|para\s+cenar)\s*[:\-–]?\s*", re.I)
NOISE = re.compile(r"^(primer|segundo|postre|plato|guarnici[oó]n|pan|agua)s?\s*(plato)?\s*[:\-]?\s*$", re.I)
HOLIDAY = re.compile(r"(festivo|no lectivo|vacaciones|puente|fiesta)", re.I)


def pdf_text(pdf_bytes: bytes) -> str:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return "\n\n".join((p.extract_text() or "") for p in pdf.pages)


def detect_month(text: str, hint: str = "") -> tuple[int, int] | None:
    sources = [s for s in (hint, text[:3000], text) if s]
    for src in sources:
        n = norm(src)
        for i, m in enumerate(MONTHS):
            mm = re.search(rf"\b{m}\b[^0-9]{{0,20}}(20\d\d)", n)
            if mm:
                return int(mm.group(1)), i + 1
    for src in sources:
        n = norm(src)
        for i, m in enumerate(MONTHS):
            if re.search(rf"\b{m}\b", n):
                today = date.today()
                year = today.year + (1 if i + 1 < today.month - 6 else 0)
                return year, i + 1
    return None


def _clean_lines(cell: str) -> list[str]:
    lines = [re.sub(r"\s+", " ", l).strip(" -•·*") for l in (cell or "").split("\n")]
    return [l for l in lines if l and not NOISE.match(l)]


def _split_cell(lines: list[str]) -> tuple[list[str], str, str]:
    """Separa platos, sugerencia de cena y nota (festivo)."""
    dishes, dinner, note = [], [], ""
    in_dinner = False
    for l in lines:
        if DINNER_MARKERS.match(l):
            in_dinner = True
            rest = DINNER_MARKERS.sub("", l).strip()
            if rest:
                dinner.append(rest)
            continue
        if HOLIDAY.search(l) and len(l) < 60:
            note = l
            continue
        (dinner if in_dinner else dishes).append(l)
    # Une líneas partidas ("Lentejas estofadas con" + "verduras")
    merged = []
    for d in dishes:
        if merged and (merged[-1].endswith((" con", " de", " y", " a la", " al", ",")) or d[:1].islower()):
            merged[-1] = f"{merged[-1]} {d}"
        else:
            merged.append(d)
    return merged, ", ".join(dinner), note


def _valid(year, month, day) -> str | None:
    try:
        d = date(year, month, day)
    except ValueError:
        return None
    return d.isoformat() if d.weekday() < 5 else None


def parse_tables(pdf_bytes: bytes, year: int, month: int) -> dict[str, dict]:
    days: dict[str, dict] = {}
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                header_days: list[int | None] | None = None
                for row in table:
                    cells = [(c or "").strip() for c in row]
                    nums = [int(c) if re.fullmatch(r"\d{1,2}", c) else None for c in cells]
                    non_empty = [c for c in cells if c]
                    if non_empty and all(re.fullmatch(r"\d{1,2}", c) for c in non_empty):
                        header_days = nums          # fila solo con números de día
                        continue
                    for col, cell in enumerate(cells):
                        if not cell:
                            continue
                        lines = _clean_lines(cell)
                        if not lines:
                            continue
                        day = None
                        m = re.match(r"^(?:(?:lunes|martes|mi[eé]rcoles|jueves|viernes)\s*)?(\d{1,2})\b\.?\s*(.*)$", lines[0], re.I)
                        if m and 1 <= int(m.group(1)) <= 31:
                            day = int(m.group(1))
                            lines = ([m.group(2)] if m.group(2) else []) + lines[1:]
                        elif header_days and col < len(header_days) and header_days[col]:
                            day = header_days[col]
                        if not day:
                            continue
                        key = _valid(year, month, day)
                        if not key:
                            continue
                        dishes, dinner, note = _split_cell(lines)
                        cur = days.setdefault(key, {"dishes": [], "dinner_hint": "", "note": ""})
                        cur["dishes"] += [d for d in dishes if d not in cur["dishes"]]
                        if dinner:
                            cur["dinner_hint"] = (cur["dinner_hint"] + ", " + dinner).strip(", ")
                        if note:
                            cur["note"] = note
    return days


def parse_list(text: str, year: int, month: int) -> dict[str, dict]:
    days: dict[str, dict] = {}
    pat = re.compile(r"\b(lunes|martes|mi[eé]rcoles|jueves|viernes)\s*,?\s*(?:d[ií]a\s*)?(\d{1,2})\b", re.I)
    matches = list(pat.finditer(text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        key = _valid(year, month, int(m.group(2)))
        if not key:
            continue
        body = text[m.end():end]
        dishes, dinner, note = _split_cell(_clean_lines(body))
        days[key] = {"dishes": dishes[:6], "dinner_hint": dinner, "note": note}
    return days


def parse(pdf_bytes: bytes, title_hint: str = "") -> dict:
    text = pdf_text(pdf_bytes)
    ym = detect_month(text, title_hint) or (date.today().year, date.today().month)
    year, month = ym
    days = parse_tables(pdf_bytes, year, month)
    if len(days) < 5:
        alt = parse_list(text, year, month)
        if len(alt) > len(days):
            days = alt
    # Rellena días lectivos que falten como vacíos para poder editarlos
    _, last = calendar.monthrange(year, month)
    for d in range(1, last + 1):
        key = _valid(year, month, d)
        if key and key not in days:
            days[key] = {"dishes": [], "dinner_hint": "", "note": ""}
    return {"year": year, "month": month, "days": days, "raw_text": text, "parser": "pdf"}
